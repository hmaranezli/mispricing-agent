"""tests/test_expiry_snipe_calculator.py — TDD for MIAMI v3 Expiry Sniping Calculator.

Pure offline calculator: static snapshot dict in -> one flat Decision Log row dict out.
No network, no DB, no execution. trade_allowed always False; operator decides stake/bet.

First RED: module analysis.expiry_snipe_calculator does not exist -> ImportError.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.expiry_snipe_calculator import (
    CANDIDATE_THRESHOLD,
    DEFAULT_STALENESS_MS,
    DEFAULT_PIN_RISK_BPS,
    normal_cdf,
    sigma_t_of,
    fair_probability_yes,
    implied_probabilities,
    compute_distance_and_pin,
    liquidity_status,
    classify_snipe_window,
    decide_candidate,
    compute_decision_row,
)


# ---------------------------------------------------------------------------
# Base valid inputs / config
# ---------------------------------------------------------------------------

def _inputs(**over):
    d = dict(
        timestamp="2026-06-26T05:00:00Z",
        asset="BTC", timeframe="5m", market_slug_or_label="btc-updown-5m-1",
        expiry="2026-06-26T05:02:00Z", time_to_expiry_seconds=120,
        strike=100000.0, spot_reference=100100.0,
        reference_source="hyperliquid", reference_staleness_ms=50,
        yes_bid=0.55, yes_ask=0.57, no_bid=0.43, no_ask=0.45,
        yes_available_size=1000.0, no_available_size=1000.0,
        intended_stake_usd=30.0, volatility_sigma=0.0005, tie_resolves_to="UP",
    )
    d.update(over)
    return d


def _config(**over):
    d = dict(fee_cost=0.0, slippage_base=0.0)
    d.update(over)
    return d


# ===========================================================================
# 1. fair_probability_yes monotonic increasing in S
# ===========================================================================

def test_fair_probability_yes_monotonic_in_spot():
    st = sigma_t_of(0.0005, 120)
    probs = [fair_probability_yes(s, 100000.0, st, "UP")[0]
             for s in (99000.0, 99800.0, 100000.0001, 100200.0, 101000.0)]
    assert all(b > a for a, b in zip(probs, probs[1:]))


# ===========================================================================
# 2. sigma_t -> 0 saturates safely, no overflow
# ===========================================================================

def test_sigma_t_tiny_saturates_no_overflow():
    tiny = 1e-12
    above, _ = fair_probability_yes(100100.0, 100000.0, tiny, "UP")
    below, _ = fair_probability_yes(99900.0, 100000.0, tiny, "UP")
    assert above > 0.999999
    assert below < 0.000001


# ===========================================================================
# 3. invalid S/K/T/sigma <= 0 raises ValueError
# ===========================================================================

@pytest.mark.parametrize("bad", [
    {"strike": 0.0}, {"strike": -1.0}, {"spot_reference": 0.0}, {"spot_reference": -5.0},
    {"time_to_expiry_seconds": 0}, {"time_to_expiry_seconds": -10},
    {"volatility_sigma": 0.0}, {"volatility_sigma": -0.1},
])
def test_invalid_inputs_raise_value_error(bad):
    with pytest.raises(ValueError):
        compute_decision_row(_inputs(**bad), _config())


# ===========================================================================
# 4. tie rule UP/DOWN/NONE
# ===========================================================================

def test_tie_rule_up():
    yf, applied = fair_probability_yes(100000.0, 100000.0, 0.01, "UP")
    assert yf == 1.0 and applied is True


def test_tie_rule_down():
    yf, applied = fair_probability_yes(100000.0, 100000.0, 0.01, "DOWN")
    assert yf == 0.0 and applied is True


def test_tie_rule_none_flags_pin():
    row = compute_decision_row(_inputs(spot_reference=100000.0, strike=100000.0,
                                       tie_resolves_to="NONE"), _config())
    assert row["yes_fair_probability"] == 0.5
    assert row["tie_rule_applied"] is True
    assert row["is_pin_risk"] is True
    assert row["pin_risk_reason"] == "tie_rule_none"


# ===========================================================================
# 5. distance / pin metrics
# ===========================================================================

def test_distance_metrics_and_pin_band():
    st = sigma_t_of(0.0005, 120)
    # spot 10 bps above strike -> not pin (default 5 bps)
    d = compute_distance_and_pin(100100.0, 100000.0, st,
                                 pin_risk_bps_threshold=DEFAULT_PIN_RISK_BPS, tie_resolves_to="UP")
    assert d["distance_to_strike"] == pytest.approx(100.0)
    assert d["distance_to_strike_bps"] == pytest.approx(10.0)
    assert d["noise_band_bps"] == pytest.approx(st * 10000)
    assert d["is_pin_risk"] is False and d["pin_risk_reason"] is None
    # spot 0.2 bps above strike -> pin
    d2 = compute_distance_and_pin(100002.0, 100000.0, st,
                                  pin_risk_bps_threshold=DEFAULT_PIN_RISK_BPS, tie_resolves_to="UP")
    assert d2["is_pin_risk"] is True and d2["pin_risk_reason"] == "within_pin_band"


# ===========================================================================
# 6. implied de-vig sums YES+NO to 1
# ===========================================================================

def test_implied_probabilities_devig_sums_to_one():
    yes_imp, no_imp = implied_probabilities(yes_bid=0.55, yes_ask=0.57, no_bid=0.46, no_ask=0.48)
    assert yes_imp + no_imp == pytest.approx(1.0)
    # YES mid 0.56 > NO mid 0.47 -> yes_imp larger
    assert yes_imp > no_imp


# ===========================================================================
# 7. per-side market_edge and spread_cost for both sides
# ===========================================================================

def test_per_side_market_edge_and_spread_cost():
    row = compute_decision_row(_inputs(), _config())
    assert row["yes_market_edge"] == pytest.approx(
        row["yes_fair_probability"] - row["yes_implied_probability"])
    assert row["no_market_edge"] == pytest.approx(
        row["no_fair_probability"] - row["no_implied_probability"])
    assert row["yes_spread_cost"] == pytest.approx((0.57 - 0.55) / 2)
    assert row["no_spread_cost"] == pytest.approx((0.45 - 0.43) / 2)


# ===========================================================================
# 8. fee_cost changes adjusted_edge exactly
# ===========================================================================

def test_fee_cost_changes_adjusted_edge_exactly():
    r0 = compute_decision_row(_inputs(), _config(fee_cost=0.0))
    r1 = compute_decision_row(_inputs(), _config(fee_cost=0.02))
    assert r1["yes_fee_cost"] == pytest.approx(0.02)
    assert (r0["yes_adjusted_edge"] - r1["yes_adjusted_edge"]) == pytest.approx(0.02)
    assert (r0["no_adjusted_edge"] - r1["no_adjusted_edge"]) == pytest.approx(0.02)


# ===========================================================================
# 9. adjusted_edge formula exact, both sides
# ===========================================================================

def test_adjusted_edge_formula_exact_both_sides():
    row = compute_decision_row(_inputs(), _config(fee_cost=0.01))
    for side in ("yes", "no"):
        assert row[f"{side}_adjusted_edge"] == pytest.approx(
            row[f"{side}_market_edge"] - row[f"{side}_spread_cost"]
            - row[f"{side}_slippage_buffer"] - row[f"{side}_latency_buffer"]
            - row[f"{side}_fee_cost"])


# ===========================================================================
# 10. flat YES/NO columns always populated
# ===========================================================================

def test_flat_yes_no_columns_always_populated():
    row = compute_decision_row(_inputs(), _config())
    for side in ("yes", "no"):
        for field in ("fair_probability", "implied_probability", "market_edge", "spread_cost",
                      "slippage_buffer", "latency_buffer", "fee_cost", "adjusted_edge"):
            assert isinstance(row[f"{side}_{field}"], float)


# ===========================================================================
# 11. candidate threshold 0.03 inclusive; 0.0299 false
# ===========================================================================

def test_candidate_threshold_inclusive():
    cand, sel = decide_candidate(0.03, 0.0, threshold=CANDIDATE_THRESHOLD, stale=False, pin=False)
    assert cand is True and sel == "YES"
    cand2, _ = decide_candidate(0.0299, 0.0, threshold=CANDIDATE_THRESHOLD, stale=False, pin=False)
    assert cand2 is False


# ===========================================================================
# 12. side selection argmax; exact tie none
# ===========================================================================

def test_side_selection_argmax_and_exact_tie_none():
    _, sel_yes = decide_candidate(0.10, 0.04, threshold=0.03, stale=False, pin=False)
    _, sel_no = decide_candidate(0.04, 0.10, threshold=0.03, stale=False, pin=False)
    _, sel_tie = decide_candidate(0.05, 0.05, threshold=0.03, stale=False, pin=False)
    assert sel_yes == "YES" and sel_no == "NO" and sel_tie == "none"


# ===========================================================================
# 13. liquidity status at $1 / $30 / $100 (stake-relative)
# ===========================================================================

def test_liquidity_status_stake_relative():
    # available 45 contracts, price 0.5 -> needed = 2*stake
    s1, _ = liquidity_status(1.0, 45.0, 0.5)
    s30, _ = liquidity_status(30.0, 45.0, 0.5)
    s100, _ = liquidity_status(100.0, 45.0, 0.5)
    assert s1 == "enough_for_stake"
    assert s30 == "weak_fill"
    assert s100 == "insufficient"


# ===========================================================================
# 14. staleness override for 5m/15m/1h/4h defaults
# ===========================================================================

@pytest.mark.parametrize("tf", ["5m", "15m", "1h", "4h"])
def test_staleness_override_forces_no_candidate(tf):
    assert DEFAULT_STALENESS_MS[tf] in (100, 500, 1000, 2000)
    stale_ms = DEFAULT_STALENESS_MS[tf] + 1
    # use a comfortably-in-window ttx for each timeframe
    ttx = {"5m": 120, "15m": 120, "1h": 600, "4h": 600}[tf]
    row = compute_decision_row(
        _inputs(timeframe=tf, time_to_expiry_seconds=ttx, reference_staleness_ms=stale_ms),
        _config())
    assert row["candidate"] is False
    assert "stale_reference" in row["notes"]


# ===========================================================================
# 15. pin-risk override forces candidate=false
# ===========================================================================

def test_pin_risk_override_forces_no_candidate():
    # spot essentially at strike -> pin risk; even a large nominal edge must not be a candidate
    row = compute_decision_row(
        _inputs(spot_reference=100000.5, strike=100000.0,
                yes_bid=0.10, yes_ask=0.11, no_bid=0.10, no_ask=0.11),
        _config())
    assert row["is_pin_risk"] is True
    assert row["candidate"] is False


# ===========================================================================
# 16. snipe-window classification incl 4h calibration
# ===========================================================================

def test_snipe_window_classification():
    lbl5, doc5 = classify_snipe_window("5m", 120)
    lbl15, doc15 = classify_snipe_window("15m", 120)
    lbl1h, doc1h = classify_snipe_window("1h", 600)
    lbl4h, doc4h = classify_snipe_window("4h", 600)
    lbl_out, doc_out = classify_snipe_window("5m", 100000)
    assert doc5 is False           # 5m: own window, doctrine N/A
    assert doc15 is True and doc1h is True
    assert lbl4h == "4h_calibration" and doc4h is False
    assert lbl_out == "outside_window" and doc_out is False


# ===========================================================================
# 17. expected_hold_seconds == time_to_expiry_seconds
# ===========================================================================

def test_expected_hold_equals_time_to_expiry():
    row = compute_decision_row(_inputs(time_to_expiry_seconds=95), _config())
    assert row["expected_hold_seconds"] == 95


# ===========================================================================
# 18. governance hard-fixed
# ===========================================================================

def test_governance_hard_fixed():
    row = compute_decision_row(_inputs(), _config())
    assert row["trade_allowed"] is False
    assert row["operator_decision_required"] is True


# ===========================================================================
# 19. exact schema completeness: no missing / no extra keys
# ===========================================================================

_EXPECTED_KEYS = {
    # identity / snapshot
    "timestamp", "asset", "timeframe", "market_slug_or_label", "expiry",
    "time_to_expiry_seconds", "strike", "spot_reference", "reference_source",
    "reference_staleness_ms",
    # raw book
    "yes_bid", "yes_ask", "no_bid", "no_ask",
    # tie / pin
    "tie_resolves_to", "tie_rule_applied", "distance_to_strike", "distance_to_strike_bps",
    "noise_band_bps", "is_pin_risk", "pin_risk_reason",
    # yes side
    "yes_fair_probability", "yes_implied_probability", "yes_market_edge", "yes_spread_cost",
    "yes_slippage_buffer", "yes_latency_buffer", "yes_fee_cost", "yes_adjusted_edge",
    # no side
    "no_fair_probability", "no_implied_probability", "no_market_edge", "no_spread_cost",
    "no_slippage_buffer", "no_latency_buffer", "no_fee_cost", "no_adjusted_edge",
    # decision
    "selected_side_candidate", "candidate_threshold", "candidate", "intended_stake_usd",
    "liquidity_status",
    # doctrine
    "expected_hold_seconds", "is_in_doctrine_window", "snipe_window_label",
    # governance
    "operator_decision_required", "trade_allowed", "notes",
}


def test_schema_completeness_exact():
    row = compute_decision_row(_inputs(), _config())
    assert set(row.keys()) == _EXPECTED_KEYS


# ===========================================================================
# 20. source scan: no network/execution/wallet/signing/order/submit/hedge/perp
# ===========================================================================

def test_source_scan_no_forbidden_surfaces():
    import analysis.expiry_snipe_calculator as m
    src = open(m.__file__, "r", encoding="utf-8").read()
    low = src.lower()
    for banned in ("aiohttp", "requests", "socket", "websocket", "kelly",
                   "hedge", "perp", "funding", "margin", "signing", "wallet",
                   "order_submit", "submit_order", "place_order"):
        assert banned not in low, f"forbidden term {banned!r} present"
    import_lines = "\n".join(ln for ln in src.splitlines()
                             if ln.strip().startswith(("import ", "from "))).lower()
    for forbidden in ("execution", "council", "scout", "wallet", "signing",
                      "aiohttp", "requests", "socket", "db.", "sqlite"):
        assert forbidden not in import_lines, f"must not import {forbidden!r}"
