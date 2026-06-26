"""analysis/expiry_snipe_calculator.py — MIAMI v3 Expiry Sniping Calculator (pure, offline).

Static snapshot dict in -> one flat Decision Log row dict out. This is an OPERATOR AID only:
it computes a structured prior and per-side adjusted edges; it never selects markets, never
places orders, and never claims actionability. ``trade_allowed`` is always False and
``operator_decision_required`` is always True. Hasan chooses the bet and the stake.

Modelling notes:
  * Settlement is binary Up/Down: YES (Up) wins if final spot >= strike (tie -> per tie_resolves_to).
  * fair_probability_yes uses a zero-drift GBM prior Phi(ln(S/K)/sigma_T). This prior was previously
    measured weak for the directional thesis; its value here is the expiry-proximate regime where
    sigma_T -> 0 makes it a near-step function of (spot - strike). It is a prior, not a proven predictor.
  * No network, no DB, no order placement, no reference-venue execution. Reference is observation only.
"""
from __future__ import annotations

import math

CANDIDATE_THRESHOLD = 0.03
DEFAULT_PIN_RISK_BPS = 5.0

DEFAULT_STALENESS_MS = {"5m": 100, "15m": 500, "1h": 1000, "4h": 2000}
SNIPE_WINDOW_SECONDS = {"5m": 180, "15m": 300, "1h": 900, "4h": 900}
DOCTRINE_TIMEFRAMES = frozenset({"15m", "1h"})

_Z_MAX = 8.0  # clip for numerical saturation when sigma_T -> 0


# ---------------------------------------------------------------------------
# Pure math helpers
# ---------------------------------------------------------------------------

def normal_cdf(z: float) -> float:
    """Standard normal CDF via erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def sigma_t_of(volatility_sigma: float, time_to_expiry_seconds: float) -> float:
    """Volatility scaled to the horizon: sigma * sqrt(T)."""
    return volatility_sigma * math.sqrt(time_to_expiry_seconds)


def fair_probability_yes(spot: float, strike: float, sigma_t: float, tie_resolves_to: str):
    """Return (yes_fair_probability, tie_rule_applied). Tie handled explicitly, never hardcoded 0.5."""
    if spot == strike:
        if tie_resolves_to == "UP":
            return 1.0, True
        if tie_resolves_to == "DOWN":
            return 0.0, True
        return 0.5, True  # NONE -> explicit pin uncertainty (flagged elsewhere)
    z = math.log(spot / strike) / sigma_t
    z = max(-_Z_MAX, min(_Z_MAX, z))
    return normal_cdf(z), False


def implied_probabilities(*, yes_bid: float, yes_ask: float, no_bid: float, no_ask: float):
    """De-vigged YES/NO implied probabilities from PM mids (sum to 1)."""
    yes_mid = (yes_bid + yes_ask) / 2.0
    no_mid = (no_bid + no_ask) / 2.0
    total = yes_mid + no_mid
    if total <= 0:
        raise ValueError("degenerate PM mids: yes_mid + no_mid must be > 0")
    return yes_mid / total, no_mid / total


def compute_distance_and_pin(spot: float, strike: float, sigma_t: float, *,
                             pin_risk_bps_threshold: float, tie_resolves_to: str) -> dict:
    """Distance-to-strike metrics and pin-risk flag."""
    distance = spot - strike
    distance_bps = (distance / strike) * 10_000.0
    noise_band_bps = sigma_t * 10_000.0
    if spot == strike and tie_resolves_to == "NONE":
        reason = "tie_rule_none"
    elif abs(distance_bps) < pin_risk_bps_threshold:
        reason = "within_pin_band"
    else:
        reason = None
    return {
        "distance_to_strike": distance,
        "distance_to_strike_bps": distance_bps,
        "noise_band_bps": noise_band_bps,
        "is_pin_risk": reason is not None,
        "pin_risk_reason": reason,
    }


def liquidity_status(intended_stake_usd: float, available_size: float, price: float, *,
                     weak_floor_fraction: float = 0.5):
    """Stake-relative liquidity classification. Returns (status, fill_ratio)."""
    if price <= 0:
        raise ValueError("price must be > 0")
    contracts_needed = intended_stake_usd / price
    fill_ratio = float("inf") if contracts_needed == 0 else available_size / contracts_needed
    if fill_ratio >= 1.0:
        status = "enough_for_stake"
    elif fill_ratio >= weak_floor_fraction:
        status = "weak_fill"
    else:
        status = "insufficient"
    return status, fill_ratio


def classify_snipe_window(timeframe: str, time_to_expiry_seconds: float):
    """Return (snipe_window_label, is_in_doctrine_window)."""
    window = SNIPE_WINDOW_SECONDS.get(timeframe)
    in_window = window is not None and 0 < time_to_expiry_seconds <= window
    if not in_window:
        return "outside_window", False
    if timeframe == "4h":
        return "4h_calibration", False  # calibration only
    return f"{timeframe}_snipe", timeframe in DOCTRINE_TIMEFRAMES


def decide_candidate(yes_adjusted: float, no_adjusted: float, *, threshold: float,
                     stale: bool, pin: bool):
    """Return (candidate, selected_side_candidate)."""
    if yes_adjusted > no_adjusted:
        selected, best = "YES", yes_adjusted
    elif no_adjusted > yes_adjusted:
        selected, best = "NO", no_adjusted
    else:
        selected, best = "none", yes_adjusted
    candidate = (best >= threshold) and (not stale) and (not pin)
    return candidate, selected


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_decision_row(inputs: dict, config: dict) -> dict:
    """Compute one flat Decision Log row from a static snapshot. Pure; no side effects."""
    # ---- validation (fail fast) ----------------------------------------------
    strike = float(inputs["strike"])
    spot = float(inputs["spot_reference"])
    ttx = inputs["time_to_expiry_seconds"]
    sigma = float(inputs["volatility_sigma"])
    if strike <= 0:
        raise ValueError("strike must be > 0")
    if spot <= 0:
        raise ValueError("spot_reference must be > 0")
    if ttx <= 0:
        raise ValueError("time_to_expiry_seconds must be > 0")
    if sigma <= 0:
        raise ValueError("volatility_sigma must be > 0")

    timeframe = inputs["timeframe"]
    tie_resolves_to = inputs["tie_resolves_to"]
    if tie_resolves_to not in ("UP", "DOWN", "NONE"):
        raise ValueError("tie_resolves_to must be UP, DOWN, or NONE")

    # ---- config defaults -----------------------------------------------------
    fee_cost = float(config.get("fee_cost", 0.0))
    slippage_base = float(config.get("slippage_base", 0.0))
    slippage_shortfall_coef = float(config.get("slippage_shortfall_coef", 0.05))
    latency_base = float(config.get("latency_base", 0.005))
    pin_bps = float(config.get("pin_risk_bps_threshold", DEFAULT_PIN_RISK_BPS))
    threshold = float(config.get("candidate_threshold", CANDIDATE_THRESHOLD))
    staleness_map = config.get("staleness_ms_by_timeframe", DEFAULT_STALENESS_MS)
    weak_floor = float(config.get("weak_floor_fraction", 0.5))

    # ---- fair / implied ------------------------------------------------------
    sigma_t = sigma_t_of(sigma, ttx)
    yes_fair, tie_applied = fair_probability_yes(spot, strike, sigma_t, tie_resolves_to)
    no_fair = 1.0 - yes_fair

    yes_imp, no_imp = implied_probabilities(
        yes_bid=float(inputs["yes_bid"]), yes_ask=float(inputs["yes_ask"]),
        no_bid=float(inputs["no_bid"]), no_ask=float(inputs["no_ask"]))

    pin = compute_distance_and_pin(spot, strike, sigma_t,
                                   pin_risk_bps_threshold=pin_bps, tie_resolves_to=tie_resolves_to)

    # ---- per-side timing/cost components -------------------------------------
    staleness_ms = inputs["reference_staleness_ms"]
    staleness_threshold = staleness_map.get(timeframe, DEFAULT_STALENESS_MS.get(timeframe, 1000))
    latency_buffer = latency_base * (staleness_ms / staleness_threshold) if staleness_threshold else latency_base

    def _side(fair, imp, bid, ask, available):
        market_edge = fair - imp
        spread_cost = (ask - bid) / 2.0
        price = ask  # executable buy price for that side
        if price > 0:
            needed = float(inputs["intended_stake_usd"]) / price
            fill_ratio = float("inf") if needed == 0 else available / needed
        else:
            fill_ratio = 0.0
        slippage = slippage_base if fill_ratio >= 1.0 else slippage_base + slippage_shortfall_coef * (1.0 - min(fill_ratio, 1.0))
        adjusted = market_edge - spread_cost - slippage - latency_buffer - fee_cost
        return {
            "fair_probability": fair, "implied_probability": imp, "market_edge": market_edge,
            "spread_cost": spread_cost, "slippage_buffer": slippage, "latency_buffer": latency_buffer,
            "fee_cost": fee_cost, "adjusted_edge": adjusted,
        }

    yes = _side(yes_fair, yes_imp, float(inputs["yes_bid"]), float(inputs["yes_ask"]),
                float(inputs["yes_available_size"]))
    no = _side(no_fair, no_imp, float(inputs["no_bid"]), float(inputs["no_ask"]),
               float(inputs["no_available_size"]))

    # ---- decision ------------------------------------------------------------
    stale = staleness_ms > staleness_threshold
    candidate, selected = decide_candidate(yes["adjusted_edge"], no["adjusted_edge"],
                                           threshold=threshold, stale=stale, pin=pin["is_pin_risk"])

    notes = []
    if stale:
        notes.append("stale_reference")
    if pin["is_pin_risk"]:
        notes.append(f"pin_risk:{pin['pin_risk_reason']}")
    notes.append(f"yes_adj={yes['adjusted_edge']:.4f};no_adj={no['adjusted_edge']:.4f}")
    notes.append("gbm_prior_is_weak_directionally")

    # ---- liquidity for the side an operator would act on ---------------------
    if selected == "NO":
        liq_price, liq_avail = float(inputs["no_ask"]), float(inputs["no_available_size"])
    else:
        liq_price, liq_avail = float(inputs["yes_ask"]), float(inputs["yes_available_size"])
    liq_status, _ = liquidity_status(float(inputs["intended_stake_usd"]), liq_avail, liq_price,
                                     weak_floor_fraction=weak_floor)

    label, in_doctrine = classify_snipe_window(timeframe, ttx)

    row = {
        # identity / snapshot
        "timestamp": inputs["timestamp"], "asset": inputs["asset"], "timeframe": timeframe,
        "market_slug_or_label": inputs["market_slug_or_label"], "expiry": inputs["expiry"],
        "time_to_expiry_seconds": ttx, "strike": strike, "spot_reference": spot,
        "reference_source": inputs["reference_source"], "reference_staleness_ms": staleness_ms,
        # raw book
        "yes_bid": float(inputs["yes_bid"]), "yes_ask": float(inputs["yes_ask"]),
        "no_bid": float(inputs["no_bid"]), "no_ask": float(inputs["no_ask"]),
        # tie / pin
        "tie_resolves_to": tie_resolves_to, "tie_rule_applied": tie_applied,
        "distance_to_strike": pin["distance_to_strike"],
        "distance_to_strike_bps": pin["distance_to_strike_bps"],
        "noise_band_bps": pin["noise_band_bps"], "is_pin_risk": pin["is_pin_risk"],
        "pin_risk_reason": pin["pin_risk_reason"],
        # yes side
        "yes_fair_probability": yes["fair_probability"], "yes_implied_probability": yes["implied_probability"],
        "yes_market_edge": yes["market_edge"], "yes_spread_cost": yes["spread_cost"],
        "yes_slippage_buffer": yes["slippage_buffer"], "yes_latency_buffer": yes["latency_buffer"],
        "yes_fee_cost": yes["fee_cost"], "yes_adjusted_edge": yes["adjusted_edge"],
        # no side
        "no_fair_probability": no["fair_probability"], "no_implied_probability": no["implied_probability"],
        "no_market_edge": no["market_edge"], "no_spread_cost": no["spread_cost"],
        "no_slippage_buffer": no["slippage_buffer"], "no_latency_buffer": no["latency_buffer"],
        "no_fee_cost": no["fee_cost"], "no_adjusted_edge": no["adjusted_edge"],
        # decision
        "selected_side_candidate": selected, "candidate_threshold": threshold,
        "candidate": candidate, "intended_stake_usd": float(inputs["intended_stake_usd"]),
        "liquidity_status": liq_status,
        # doctrine
        "expected_hold_seconds": ttx, "is_in_doctrine_window": in_doctrine,
        "snipe_window_label": label,
        # governance (hard-fixed)
        "operator_decision_required": True, "trade_allowed": False, "notes": " | ".join(notes),
    }
    return row
