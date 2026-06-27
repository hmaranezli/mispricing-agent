"""Pure diagnostic economics calculator over a GOLDEN_SAMPLE_OK record.

This module is DIAGNOSTIC MATH ONLY. It consumes one GOLDEN_SAMPLE_OK record plus explicit inert
operator/config inputs and returns a diagnostic economic report. It never emits a trading instruction,
intent, routing, sizing recommendation, or any actionability signal.

Purity: no network, no database, no cache, no file access, no clock, no account access, no hidden
state. Arithmetic is 100% Decimal (no binary floats). All numeric output leaves are fixed-point
strings via format(d, "f"). Programmer-contract violations raise; data/economic problems fail closed
with a stable fail_closed_reason and null diagnostic fields.

Probability/price scale: Polymarket prices sit in the open interval (0, 1) as probability-equivalent
value per unit-payoff share. The fair probability is in [0, 1]. Per-share costs (fee/slippage/safety
margin) are pre-converted probability-point units, so the diagnostic subtraction is unit-consistent.

Reference boundary: the Hyperliquid reference is a PERP REFERENCE PROXY only, never spot/truth/
settlement; the fair-probability model is a diagnostic model, never an oracle.
"""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext

_SCHEMA = "gs-econ-v0"
_OK = "DIAGNOSTIC_OK"
_FAILED = "CALC_FAILED_CLOSED"
_MODEL_VERSION = "gbm-digital-v0"
_MS_PER_YEAR = Decimal("31536000000")   # 365 * 24 * 3600 * 1000
_ZERO = Decimal(0)
_ONE = Decimal(1)
_HALF = Decimal("0.5")
_MARKERS = ("not_actionable", "diagnostic_model_not_oracle",
            "perp_reference_not_spot_truth_settlement", "stake_adjusted_vwap_not_top_of_book")


class _FailClosed(Exception):
    """Internal fail-closed signal carrying a stable reason; never escapes the entry function."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _fc(reason):
    raise _FailClosed(reason)


def _strict_decimal(value, *, on_bad):
    """Coerce a permitted scalar to Decimal. float/bool/NaN/Inf -> unsafe_numeric; bad -> on_bad."""
    t = type(value)
    if t is bool or t is float:
        _fc("unsafe_numeric")
    if isinstance(value, Decimal):
        if value.is_nan() or value.is_infinite():
            _fc("unsafe_numeric")
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        try:
            d = Decimal(value)
        except InvalidOperation:
            _fc(on_bad)
        if d.is_nan() or d.is_infinite():
            _fc("unsafe_numeric")
        return d
    _fc(on_bad)


def _erf_nonneg(x):
    """Abramowitz & Stegun 7.1.26 erf approximation for x >= 0 (max abs error ~1.5e-7), pure Decimal."""
    p = Decimal("0.3275911")
    a1 = Decimal("0.254829592")
    a2 = Decimal("-0.284496736")
    a3 = Decimal("1.421413741")
    a4 = Decimal("-1.453152027")
    a5 = Decimal("1.061405429")
    t = _ONE / (_ONE + p * x)
    poly = ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t
    return _ONE - poly * (-(x * x)).exp()


def _normal_cdf(z):
    """Deterministic Decimal standard-normal CDF; uses the active Decimal context. Clamped to [0,1]."""
    inv_sqrt2 = _ONE / Decimal(2).sqrt()
    if z >= _ZERO:
        cdf = _HALF * (_ONE + _erf_nonneg(z * inv_sqrt2))
    else:
        cdf = _ONE - _HALF * (_ONE + _erf_nonneg((-z) * inv_sqrt2))
    if cdf < _ZERO:
        return _ZERO
    if cdf > _ONE:
        return _ONE
    return cdf


def _require(mapping, key, *, missing_reason):
    if key not in mapping:
        _fc(missing_reason)
    return mapping[key]


def _load_levels(raw_levels, *, side_key):
    """Parse and validate one side ([{price,size}]) into ascending-by-price [(price, size)]."""
    if not isinstance(raw_levels, list):
        _fc("book_malformed")
    out = []
    for lvl in raw_levels:
        if not isinstance(lvl, dict) or "price" not in lvl or "size" not in lvl:
            _fc("book_malformed")
        price = _strict_decimal(lvl["price"], on_bad="book_malformed")
        size = _strict_decimal(lvl["size"], on_bad="book_malformed")
        if not (_ZERO < price < _ONE):
            _fc("book_malformed")
        if size <= _ZERO:
            _fc("book_malformed")
        out.append((price, size))
    out.sort(key=lambda pair: pair[0])   # ascending by price; do not trust the source array sequence
    return out


def _walk_ask_depth_vwap(asks_ascending, stake):
    """Stake-adjusted volume-weighted average price across ask depth (lowest price first).

    Returns (vwap, filled_shares, filled_cost). Fails closed if depth cannot satisfy the stake.
    Never uses top-of-book or midpoint.
    """
    cost = _ZERO
    shares = _ZERO
    for price, size in asks_ascending:
        level_cost = price * size
        if cost + level_cost >= stake:
            remaining = stake - cost
            take_shares = remaining / price
            shares += take_shares
            cost = stake
            return cost / shares, shares, cost
        cost += level_cost
        shares += size
    _fc("insufficient_depth")


def _spread_metrics(asks_ascending, bids_ascending, max_spread):
    if not asks_ascending or not bids_ascending:
        _fc("empty_book")
    best_ask = asks_ascending[0][0]
    best_bid = bids_ascending[-1][0]
    if best_bid >= best_ask:
        _fc("crossed_or_locked_book")
    spread = best_ask - best_bid
    if spread > max_spread:
        _fc("spread_guard_exceeded")
    return best_bid, best_ask, spread


def _book_for_side(record, slot_key, expected_token_id):
    slot = record.get(slot_key)
    if not isinstance(slot, dict):
        _fc("book_evidence_missing")
    if slot.get("expected_token_id") != expected_token_id:
        _fc("identity_mismatch")
    evidence = slot.get("evidence")
    if not isinstance(evidence, dict):
        _fc("book_evidence_missing")
    parsed = evidence.get("parsed_safe_book")
    if not isinstance(parsed, dict):
        _fc("book_evidence_missing")
    asks = _load_levels(parsed.get("asks"), side_key="asks")
    bids = _load_levels(parsed.get("bids"), side_key="bids")
    return asks, bids


def _fmt(d):
    return None if d is None else format(d, "f")


def _leg_report(*, vwap, shares, cost, best_bid, best_ask, spread, edge, sufficient):
    return {
        "pm_stake_adjusted_vwap": _fmt(vwap),
        "filled_shares": _fmt(shares),
        "filled_cost_usd": _fmt(cost),
        "sufficient_depth": sufficient,
        "best_bid": _fmt(best_bid),
        "best_ask": _fmt(best_ask),
        "spread": _fmt(spread),
        "diagnostic_net_edge": _fmt(edge),
    }


def _null_leg():
    return {"pm_stake_adjusted_vwap": None, "filled_shares": None, "filled_cost_usd": None,
            "sufficient_depth": False, "best_bid": None, "best_ask": None, "spread": None,
            "diagnostic_net_edge": None}


def _report(*, status, reason, identity, model, yes_leg, no_leg, costs, stake_str):
    return {
        "schema_version": _SCHEMA,
        "status": status,
        "fail_closed_reason": reason,
        "identity": identity,
        "model": model,
        "yes_leg": yes_leg,
        "no_leg": no_leg,
        "costs": costs,
        "intended_stake_usd": stake_str,
        "markers": list(_MARKERS),
    }


def _null_model():
    return {"model_version": _MODEL_VERSION, "model_fair_probability_up": None,
            "time_to_expiry_years": None, "reference_price": None, "strike_price": None,
            "sigma_annual": None, "drift_annual": None,
            "model_note": "diagnostic_model_not_oracle"}


def _failed(reason, *, identity=None, stake_str=None, costs=None):
    return _report(status=_FAILED, reason=reason,
                   identity=identity or {"condition_id": None, "yes_token_id": None,
                                         "no_token_id": None},
                   model=_null_model(), yes_leg=_null_leg(), no_leg=_null_leg(),
                   costs=costs or {"fee_per_share": None, "slippage_allowance": None,
                                   "safety_margin": None},
                   stake_str=stake_str)


def compute_diagnostic_edge_report(*, golden_sample_record, intended_stake_usd, config) -> dict:
    """Pure, deterministic diagnostic economic report for one GOLDEN_SAMPLE_OK record.

    Programmer-contract violations raise TypeError. Data/economic problems return a fail-closed report.
    """
    if not isinstance(golden_sample_record, dict):
        raise TypeError("golden_sample_record must be a dict")
    if not isinstance(config, Mapping):
        raise TypeError("config must be a Mapping")

    try:
        return _compute(golden_sample_record, intended_stake_usd, config)
    except _FailClosed as exc:
        return _failed(exc.reason)


def _compute(record, intended_stake_usd, config):
    # ---- config precision first (sets the arithmetic context) ----
    precision = config.get("decimal_precision")
    if not (isinstance(precision, int) and not isinstance(precision, bool) and precision > 0):
        _fc("invalid_config")

    with localcontext() as ctx:
        ctx.prec = precision
        ctx.rounding = ROUND_HALF_EVEN
        return _compute_in_context(record, intended_stake_usd, config)


def _compute_in_context(record, intended_stake_usd, config):
    # ---- costs / spread guard (config) ----
    fee = _strict_decimal(_require(config, "fee_per_share", missing_reason="invalid_config"),
                          on_bad="invalid_config")
    slippage = _strict_decimal(_require(config, "slippage_allowance", missing_reason="invalid_config"),
                               on_bad="invalid_config")
    margin = _strict_decimal(_require(config, "safety_margin", missing_reason="invalid_config"),
                             on_bad="invalid_config")
    max_spread = _strict_decimal(_require(config, "max_spread", missing_reason="invalid_config"),
                                 on_bad="invalid_config")
    if fee < _ZERO or slippage < _ZERO or margin < _ZERO or max_spread <= _ZERO:
        _fc("invalid_config")
    costs = {"fee_per_share": _fmt(fee), "slippage_allowance": _fmt(slippage),
             "safety_margin": _fmt(margin)}

    # ---- intended stake ----
    stake = _strict_decimal(intended_stake_usd, on_bad="invalid_stake")
    if stake <= _ZERO:
        _fc("invalid_stake")
    stake_str = _fmt(stake)

    # ---- golden sample status ----
    if record.get("status") != "GOLDEN_SAMPLE_OK" or record.get("error_code") is not None:
        _fc("golden_sample_not_ok")

    onboarding = record.get("onboarding")
    if not isinstance(onboarding, dict):
        _fc("golden_sample_not_ok")
    gamma = onboarding.get("gamma")
    binance = onboarding.get("binance")
    if not isinstance(gamma, dict) or not isinstance(binance, dict):
        _fc("golden_sample_not_ok")

    # ---- identity ----
    condition_id = onboarding.get("condition_id")
    tmap = gamma.get("outcome_token_map")
    if not isinstance(tmap, list) or len(tmap) != 2:
        _fc("identity_mismatch")
    try:
        yes_tok = tmap[0]["token_id"]
        no_tok = tmap[1]["token_id"]
    except (KeyError, TypeError, IndexError):
        _fc("identity_mismatch")
    if not (isinstance(condition_id, str) and condition_id
            and isinstance(yes_tok, str) and yes_tok and isinstance(no_tok, str) and no_tok):
        _fc("identity_mismatch")
    expected_condition_id = config.get("expected_condition_id")
    if expected_condition_id is not None and expected_condition_id != condition_id:
        _fc("identity_mismatch")
    identity = {"condition_id": condition_id, "yes_token_id": yes_tok, "no_token_id": no_tok}

    # ---- model inputs ----
    sigma = _strict_decimal(_require(config, "sigma_annual", missing_reason="missing_model_inputs"),
                            on_bad="invalid_config")
    drift = _strict_decimal(_require(config, "drift_annual", missing_reason="missing_model_inputs"),
                            on_bad="invalid_config")
    valuation_ms = _require(config, "valuation_time_ms", missing_reason="missing_model_inputs")
    if not (isinstance(valuation_ms, int) and not isinstance(valuation_ms, bool)):
        _fc("invalid_config")
    if sigma <= _ZERO:
        _fc("invalid_config")

    end_ms = gamma.get("end_date_ms")
    if not (isinstance(end_ms, int) and not isinstance(end_ms, bool)):
        _fc("golden_sample_not_ok")
    elapsed_ms = end_ms - valuation_ms
    if elapsed_ms <= 0:
        _fc("expired_or_nonpositive_tte")
    tte = Decimal(elapsed_ms) / _MS_PER_YEAR

    strike = _strict_decimal(binance.get("strike_price"), on_bad="nonpositive_reference_or_strike")
    hl = record.get("hl_reference")
    hl_ev = hl.get("evidence") if isinstance(hl, dict) else None
    if not isinstance(hl_ev, dict):
        _fc("golden_sample_not_ok")
    reference = _strict_decimal(hl_ev.get("reference_price"),
                                on_bad="nonpositive_reference_or_strike")
    if strike <= _ZERO or reference <= _ZERO:
        _fc("nonpositive_reference_or_strike")

    # ---- fair probability (BTC Up) ----
    d2 = ((reference / strike).ln() + (drift - sigma * sigma / Decimal(2)) * tte) \
        / (sigma * tte.sqrt())
    p_up = _normal_cdf(d2)

    model = {"model_version": _MODEL_VERSION, "model_fair_probability_up": _fmt(p_up),
             "time_to_expiry_years": _fmt(tte), "reference_price": _fmt(reference),
             "strike_price": _fmt(strike), "sigma_annual": _fmt(sigma), "drift_annual": _fmt(drift),
             "model_note": "diagnostic_model_not_oracle"}

    # ---- both books (identity-checked) ----
    yes_asks, yes_bids = _book_for_side(record, "yes_book", yes_tok)
    no_asks, no_bids = _book_for_side(record, "no_book", no_tok)
    yes_bid, yes_ask, yes_spread = _spread_metrics(yes_asks, yes_bids, max_spread)
    no_bid, no_ask, no_spread = _spread_metrics(no_asks, no_bids, max_spread)

    yes_vwap, yes_shares, yes_cost = _walk_ask_depth_vwap(yes_asks, stake)
    no_vwap, no_shares, no_cost = _walk_ask_depth_vwap(no_asks, stake)

    # ---- diagnostic edge (parallel legs; no ranking, no selection) ----
    yes_edge = p_up - yes_vwap - fee - slippage - margin
    no_edge = (_ONE - p_up) - no_vwap - fee - slippage - margin

    yes_leg = _leg_report(vwap=yes_vwap, shares=yes_shares, cost=yes_cost, best_bid=yes_bid,
                          best_ask=yes_ask, spread=yes_spread, edge=yes_edge, sufficient=True)
    no_leg = _leg_report(vwap=no_vwap, shares=no_shares, cost=no_cost, best_bid=no_bid,
                         best_ask=no_ask, spread=no_spread, edge=no_edge, sufficient=True)

    return _report(status=_OK, reason=None, identity=identity, model=model,
                   yes_leg=yes_leg, no_leg=no_leg, costs=costs, stake_str=stake_str)
