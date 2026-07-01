"""
Paper Edge/PnL Vertical — pure evaluator tests (OFFLINE, no network).

Covers: lookahead-free candidate selection (entry-time fields only), $25 quantity
clamp, fee formula (quadratic, no double-counted spread), win/loss payout,
dedup-to-earliest, threshold-bucket shadow reporting, and cohort aggregation.

This is a DIAGNOSTIC/PAPER evaluation, NOT tradeable alpha.
"""
from decimal import Decimal

import pytest

from analysis.forensic import gateg7_paper_pnl as pp

NOW_MS = 1_900_000_000_000


def _row(**over):
    base = dict(signal_id="sigA", asset="BTC", side="NO", slug="btc-updown-15m-1000",
                condition_id="cid-1", token_id="tokDown", outcome_index=1, outcome_label="Down",
                ts_signal="2026-06-30T00:00:00.000Z", ts_signal_ms=NOW_MS,
                market_end_ts=NOW_MS // 1000 + 600, exec_ask_vwap="0.40",
                exec_fill_qty_avail="60", entry_edge="0.10", fill_decision="UNFILLED_EDGE_LOST")
    base.update(over)
    return base


# ===========================================================================
# candidate selection — no lookahead (entry-time fields only)
# ===========================================================================
def test_select_eligible_accepts_filled_active_and_edge_lost():
    rows = [_row(fill_decision="FILLED_ACTIVE"), _row(signal_id="s2", fill_decision="UNFILLED_EDGE_LOST")]
    out = pp.select_eligible_candidates(rows)
    assert len(out) == 2


def test_select_eligible_rejects_stale_and_depth_fail():
    rows = [_row(fill_decision="UNFILLED_QUOTE_STALE"), _row(fill_decision="UNFILLED_ENTRY_DEPTH_FAIL")]
    assert pp.select_eligible_candidates(rows) == []


def test_select_eligible_rejects_nonpositive_ask_or_qty():
    rows = [_row(exec_ask_vwap="0"), _row(exec_fill_qty_avail="0")]
    assert pp.select_eligible_candidates(rows) == []


def test_select_eligible_never_relabels_fill_decision():
    rows = [_row(fill_decision="UNFILLED_EDGE_LOST")]
    out = pp.select_eligible_candidates(rows)
    assert out[0]["fill_decision"] == "UNFILLED_EDGE_LOST"   # untouched


def test_select_eligible_takes_no_resolution_input():
    # structural no-lookahead proof: the function signature has no resolution/outcome param
    import inspect
    params = inspect.signature(pp.select_eligible_candidates).parameters
    assert "resolution" not in params and "outcome" not in params and "winner" not in params


# ===========================================================================
# dedup to earliest per condition_id
# ===========================================================================
def test_dedup_earliest_by_condition_picks_earliest_ts():
    early = _row(signal_id="early", condition_id="cid-1", ts_signal_ms=NOW_MS)
    late = _row(signal_id="late", condition_id="cid-1", ts_signal_ms=NOW_MS + 100_000)
    other = _row(signal_id="other", condition_id="cid-2", ts_signal_ms=NOW_MS)
    out = pp.dedup_earliest_by_condition([late, early, other])
    ids = {r["signal_id"] for r in out}
    assert ids == {"early", "other"}


# ===========================================================================
# effective-N (unique condition_ids + unique 15m windows)
# ===========================================================================
def test_effective_n_windows():
    rows = [_row(condition_id="cid-1", slug="btc-updown-15m-1000"),
            _row(condition_id="cid-2", slug="sol-updown-15m-1000"),
            _row(condition_id="cid-3", slug="eth-updown-15m-2000")]
    n = pp.effective_n_windows(rows)
    assert n["unique_condition_ids"] == 3
    assert n["unique_windows"] == 2


# ===========================================================================
# shadow threshold buckets
# ===========================================================================
def test_shadow_buckets_thresholds():
    rows = [_row(signal_id="a", entry_edge="0.01"), _row(signal_id="b", entry_edge="0.04"),
            _row(signal_id="c", entry_edge="0.06"), _row(signal_id="d", entry_edge="-0.01")]
    buckets = pp.shadow_buckets(rows)
    assert {r["signal_id"] for r in buckets[">0"]} == {"a", "b", "c"}
    assert {r["signal_id"] for r in buckets[">=0.03"]} == {"b", "c"}
    assert {r["signal_id"] for r in buckets[">=0.05"]} == {"c"}
    assert buckets[">=0.10"] == [] and buckets[">=0.15"] == [] and buckets[">=0.25"] == []


def test_shadow_buckets_thresholds_keys_exact():
    assert list(pp.shadow_buckets([]).keys()) == [">0", ">=0.03", ">=0.05", ">=0.10", ">=0.15", ">=0.25"]


# ===========================================================================
# $25 quantity clamp
# ===========================================================================
def test_clamp_fill_qty_uses_available_when_stake_buys_more():
    # 25/0.40 = 62.5 shares the stake could buy, but only 60 are available -> clamp to 60
    qty = pp.clamp_fill_qty(Decimal("60"), Decimal("0.40"))
    assert qty == Decimal("60")


def test_clamp_fill_qty_uses_stake_when_depth_is_abundant():
    # 25/0.40 = 62.5 < 1000 available -> clamp to what the stake buys
    qty = pp.clamp_fill_qty(Decimal("1000"), Decimal("0.40"))
    assert qty == Decimal("25") / Decimal("0.40")


def test_clamp_fill_qty_zero_ask_is_zero():
    assert pp.clamp_fill_qty(Decimal("100"), Decimal("0")) == Decimal("0")


# ===========================================================================
# fee config parsing — feeSchedule is AUTHORITATIVE; takerBaseFee never used
# ===========================================================================
def test_parse_fee_config_verified_zero_when_fees_disabled():
    cfg = pp.parse_fee_config({"feesEnabled": False, "takerBaseFee": 1000})
    assert cfg["fee_status"] == pp.FEE_VERIFIED_ZERO
    assert cfg["fee_rate"] == Decimal("0")


def test_parse_fee_config_verified_rate_from_fee_schedule():
    cfg = pp.parse_fee_config({"feesEnabled": True, "takerBaseFee": 1000,
                               "feeSchedule": {"exponent": 1, "rate": 0.07,
                                              "takerOnly": True, "rebateRate": 0.2}})
    assert cfg["fee_status"] == pp.FEE_VERIFIED_RATE
    assert cfg["fee_rate"] == Decimal("0.07")


def test_parse_fee_config_never_uses_taker_base_fee_when_schedule_present():
    # feeSchedule.rate (0.07) must win, NEVER takerBaseFee/50000 (0.02)
    cfg = pp.parse_fee_config({"feesEnabled": True, "takerBaseFee": 1000,
                               "feeSchedule": {"exponent": 1, "rate": 0.07, "takerOnly": True}})
    assert cfg["fee_rate"] != Decimal("1000") / Decimal("50000")
    assert cfg["fee_rate"] == Decimal("0.07")


def test_parse_fee_config_rebate_rate_never_reduces_taker_fee():
    with_rebate = pp.parse_fee_config({"feesEnabled": True,
                                       "feeSchedule": {"exponent": 1, "rate": 0.07,
                                                       "takerOnly": True, "rebateRate": 0.5}})
    no_rebate = pp.parse_fee_config({"feesEnabled": True,
                                     "feeSchedule": {"exponent": 1, "rate": 0.07, "takerOnly": True}})
    assert with_rebate["fee_rate"] == no_rebate["fee_rate"] == Decimal("0.07")


def test_parse_fee_config_missing_schedule_is_unsupported_no_takerbase_fallback():
    cfg = pp.parse_fee_config({"feesEnabled": True, "takerBaseFee": 1000})
    assert cfg["fee_status"] == pp.FEE_UNSUPPORTED_SCHEDULE
    assert cfg["fee_rate"] is None


def test_parse_fee_config_unsupported_exponent():
    cfg = pp.parse_fee_config({"feesEnabled": True,
                               "feeSchedule": {"exponent": 2, "rate": 0.07, "takerOnly": True}})
    assert cfg["fee_status"] == pp.FEE_UNSUPPORTED_SCHEDULE
    assert cfg["fee_rate"] is None


def test_parse_fee_config_not_taker_only_is_unsupported():
    cfg = pp.parse_fee_config({"feesEnabled": True,
                               "feeSchedule": {"exponent": 1, "rate": 0.07, "takerOnly": False}})
    assert cfg["fee_status"] == pp.FEE_UNSUPPORTED_SCHEDULE
    assert cfg["fee_rate"] is None


def test_parse_fee_config_missing_fees_enabled_is_unverifiable():
    cfg = pp.parse_fee_config({"takerBaseFee": 1000})
    assert cfg["fee_status"] == pp.FEE_METADATA_MISSING
    assert cfg["fee_rate"] is None


def test_parse_fee_config_never_silently_zero_when_unverifiable():
    cfg = pp.parse_fee_config({})
    assert cfg["fee_rate"] is None
    assert cfg["fee_status"] != pp.FEE_VERIFIED_ZERO


def test_parse_fee_config_none_market_is_unverifiable():
    cfg = pp.parse_fee_config(None)
    assert cfg["fee_status"] == pp.FEE_METADATA_MISSING


def test_parse_fee_config_real_sol_eth_market_recompute():
    """Recompute proof: the real SOL/ETH markets from the smoke-DB audit."""
    real_market = {"feesEnabled": True, "takerBaseFee": 1000, "makerBaseFee": 1000,
                   "feeSchedule": {"exponent": 1, "rate": 0.07, "takerOnly": True, "rebateRate": 0.2}}
    cfg = pp.parse_fee_config(real_market)
    assert cfg["fee_rate"] == Decimal("0.07")
    sol_fee = pp.entry_fee_quadratic(
        Decimal("29.069767441860465116279069767441860465116279069767"), cfg["fee_rate"],
        Decimal("0.86000000000000000000000000000000000000000000000001"))
    eth_fee = pp.entry_fee_quadratic(
        Decimal("56.818181818181818181818181818181818181818181818182"), cfg["fee_rate"],
        Decimal("0.44000000000000000000000000000000000000000000000000"))
    assert sol_fee == Decimal("0.24500")
    assert eth_fee == Decimal("0.98000")
    sol_net = pp.compute_pnl(filled_qty=Decimal("29.069767441860465116279069767441860465116279069767"),
                             exec_ask_vwap=Decimal("0.86000000000000000000000000000000000000000000000001"),
                             won=False, fee=sol_fee)["net_pnl"]
    eth_net = pp.compute_pnl(filled_qty=Decimal("56.818181818181818181818181818181818181818181818182"),
                             exec_ask_vwap=Decimal("0.44000000000000000000000000000000000000000000000000"),
                             won=False, fee=eth_fee)["net_pnl"]
    assert sol_net == Decimal("-25.24500")
    assert eth_net == Decimal("-25.98000")
    assert sol_net + eth_net == Decimal("-51.22500")


# ===========================================================================
# realized effective-N — resolved windows only; correlated assets flagged
# ===========================================================================
def test_realized_effective_n_counts_resolved_windows_only():
    resolved = [{"asset": "SOL", "slug": "sol-updown-15m-1782862200"},
               {"asset": "ETH", "slug": "eth-updown-15m-1782862200"}]
    out = pp.realized_effective_n(resolved)
    assert out["resolved_unique_windows"] == 1
    assert out["correlated_windows"] == {"1782862200": ["ETH", "SOL"]}


def test_realized_effective_n_independent_windows_not_flagged():
    resolved = [{"asset": "SOL", "slug": "sol-updown-15m-1000"},
               {"asset": "SOL", "slug": "sol-updown-15m-2000"}]
    out = pp.realized_effective_n(resolved)
    assert out["resolved_unique_windows"] == 2
    assert out["correlated_windows"] == {}


# ===========================================================================
# wording — never "best win" when there are no wins
# ===========================================================================
def test_aggregate_bucket_all_losses_has_no_best_win_but_has_least_loss():
    results = [{"status": "RESOLVED", "matched": False, "net_pnl": Decimal("-25.245"),
               "slug": "sol-updown-15m-1"},
              {"status": "RESOLVED", "matched": False, "net_pnl": Decimal("-25.98"),
               "slug": "eth-updown-15m-1"}]
    agg = pp.aggregate_bucket(results)
    assert agg["wins"] == 0
    assert agg["best_win"] is None            # never mislabel a loss as a win
    assert agg["least_loss"] == Decimal("-25.245")   # smallest-magnitude loss
    assert agg["worst_loss"] == Decimal("-25.98")


# ===========================================================================
# bidirectional entry — no lookahead; YES/NO selection; ties; fee turning net negative
# ===========================================================================
def _ladder(price, size="1000"):
    return [[price, size]]


def test_bidirectional_no_lookahead_signature():
    import inspect
    params = inspect.signature(pp.evaluate_bidirectional_entry).parameters
    for forbidden in ("resolution", "outcome", "winner", "won", "matched"):
        assert forbidden not in params


def test_bidirectional_yes_wins_when_yes_net_edge_larger():
    fee_cfg = {"fee_rate": Decimal("0.07"), "fee_status": pp.FEE_VERIFIED_RATE}
    # fair_yes=0.70: YES gross edge=0.70-0.40=0.30 (big); NO gross edge=0.30-0.55=-0.25
    r = pp.evaluate_bidirectional_entry(
        fair_yes=Decimal("0.70"), yes_ask_levels=_ladder("0.40"), no_ask_levels=_ladder("0.55"),
        yes_fee_config=fee_cfg, no_fee_config=fee_cfg)
    assert r["selected_side"] == "YES"
    assert r["no_entry_reason"] is None
    assert Decimal(r["yes"]["net_edge"]) > 0


def test_bidirectional_no_wins_when_no_net_edge_larger():
    fee_cfg = {"fee_rate": Decimal("0.07"), "fee_status": pp.FEE_VERIFIED_RATE}
    # fair_yes=0.20: NO gross edge=0.80-0.40=0.40 (big); YES gross edge=0.20-0.55=-0.35
    r = pp.evaluate_bidirectional_entry(
        fair_yes=Decimal("0.20"), yes_ask_levels=_ladder("0.55"), no_ask_levels=_ladder("0.40"),
        yes_fee_config=fee_cfg, no_fee_config=fee_cfg)
    assert r["selected_side"] == "NO"
    assert r["no_entry_reason"] is None


def test_bidirectional_never_defaults_to_no_when_yes_is_better():
    # explicit regression guard against the fixed "Down/NO-only" defect
    fee_cfg = {"fee_rate": Decimal("0"), "fee_status": pp.FEE_VERIFIED_ZERO}
    r = pp.evaluate_bidirectional_entry(
        fair_yes=Decimal("0.90"), yes_ask_levels=_ladder("0.10"), no_ask_levels=_ladder("0.95"),
        yes_fee_config=fee_cfg, no_fee_config=fee_cfg)
    assert r["selected_side"] == "YES"


def test_bidirectional_both_negative_no_entry():
    fee_cfg = {"fee_rate": Decimal("0.07"), "fee_status": pp.FEE_VERIFIED_RATE}
    r = pp.evaluate_bidirectional_entry(
        fair_yes=Decimal("0.50"), yes_ask_levels=_ladder("0.90"), no_ask_levels=_ladder("0.90"),
        yes_fee_config=fee_cfg, no_fee_config=fee_cfg)
    assert r["selected_side"] is None
    assert r["no_entry_reason"] == pp.NO_PAPER_ENTRY


def test_bidirectional_exact_tie_fails_closed():
    fee_cfg = {"fee_rate": Decimal("0"), "fee_status": pp.FEE_VERIFIED_ZERO}
    # symmetric market at fair_yes=0.5 with identical asks -> identical positive net edges
    r = pp.evaluate_bidirectional_entry(
        fair_yes=Decimal("0.50"), yes_ask_levels=_ladder("0.40"), no_ask_levels=_ladder("0.40"),
        yes_fee_config=fee_cfg, no_fee_config=fee_cfg)
    assert r["selected_side"] is None
    assert r["no_entry_reason"] == pp.EDGE_TIE_NO_ENTRY


def test_bidirectional_fee_turns_gross_positive_into_net_negative_no_entry():
    # gross edge is positive on both sides but a large fee wipes it out -> no entry
    fee_cfg = {"fee_rate": Decimal("0.9"), "fee_status": pp.FEE_VERIFIED_RATE}
    r = pp.evaluate_bidirectional_entry(
        fair_yes=Decimal("0.51"), yes_ask_levels=_ladder("0.50"), no_ask_levels=_ladder("0.48"),
        yes_fee_config=fee_cfg, no_fee_config=fee_cfg)
    assert Decimal(r["yes"]["gross_edge"]) > 0 or Decimal(r["no"]["gross_edge"]) > 0
    assert r["selected_side"] is None
    assert r["no_entry_reason"] == pp.NO_PAPER_ENTRY


def test_bidirectional_unsupported_fee_not_admitted_falls_back_to_other_side():
    admitted = {"fee_rate": Decimal("0"), "fee_status": pp.FEE_VERIFIED_ZERO}
    unsupported = {"fee_rate": None, "fee_status": pp.FEE_UNSUPPORTED_SCHEDULE}
    r = pp.evaluate_bidirectional_entry(
        fair_yes=Decimal("0.70"), yes_ask_levels=_ladder("0.40"), no_ask_levels=_ladder("0.20"),
        yes_fee_config=unsupported, no_fee_config=admitted)
    assert r["yes"]["admitted"] is False
    assert r["yes"]["not_admitted_reason"] == pp.FEE_UNSUPPORTED_SCHEDULE
    assert r["no"]["admitted"] is True
    assert r["selected_side"] == "NO"        # only the admitted side could be evaluated


def test_bidirectional_both_unsupported_fee_not_admitted():
    unsupported = {"fee_rate": None, "fee_status": pp.FEE_UNSUPPORTED_SCHEDULE}
    r = pp.evaluate_bidirectional_entry(
        fair_yes=Decimal("0.70"), yes_ask_levels=_ladder("0.40"), no_ask_levels=_ladder("0.20"),
        yes_fee_config=unsupported, no_fee_config=unsupported)
    assert r["selected_side"] is None
    assert r["no_entry_reason"] == pp.NOT_ADMITTED_UNSUPPORTED_FEE


def test_bidirectional_records_diagnostics_and_ladders():
    fee_cfg = {"fee_rate": Decimal("0.07"), "fee_status": pp.FEE_VERIFIED_RATE}
    r = pp.evaluate_bidirectional_entry(
        fair_yes=Decimal("0.70"), yes_ask_levels=_ladder("0.40"), no_ask_levels=_ladder("0.55"),
        yes_fee_config=fee_cfg, no_fee_config=fee_cfg, reference_age_ms=5000, tte_s=300,
        cost_buffer=Decimal("0"))
    assert r["reference_age_ms"] == 5000 and r["tte_s"] == 300
    assert r["fair_yes"] == "0.70"
    for side in ("yes", "no"):
        for key in ("exec_ask_vwap", "filled_qty", "gross_edge", "fee_per_share", "net_edge"):
            assert key in r[side]


# ===========================================================================
# fee formula — quadratic, no double-counted spread, rounded to 5dp
# ===========================================================================
def test_entry_fee_quadratic_formula():
    # filled_qty=60, fee_rate=0.02, p=0.40 -> 60*0.02*0.40*0.60 = 0.288
    fee = pp.entry_fee_quadratic(Decimal("60"), Decimal("0.02"), Decimal("0.40"))
    assert fee == Decimal("0.288") or fee == Decimal("0.28800")


def test_entry_fee_quadratic_rounds_to_5dp():
    fee = pp.entry_fee_quadratic(Decimal("1"), Decimal("0.0233333"), Decimal("0.333333"))
    assert fee == fee.quantize(Decimal("0.00001"))


def test_entry_fee_quadratic_zero_rate_is_zero():
    assert pp.entry_fee_quadratic(Decimal("60"), Decimal("0"), Decimal("0.40")) == Decimal("0")


def test_entry_fee_quadratic_no_spread_term():
    # the formula depends ONLY on (filled_qty, fee_rate, p) — never on bid/spread inputs
    import inspect
    params = list(inspect.signature(pp.entry_fee_quadratic).parameters)
    assert params == ["filled_qty", "fee_rate", "p"]
    assert "spread" not in params and "bid" not in params


# ===========================================================================
# PnL computation — win/loss payout, gross/net
# ===========================================================================
def test_compute_pnl_win_payout():
    r = pp.compute_pnl(filled_qty=Decimal("60"), exec_ask_vwap=Decimal("0.40"),
                       won=True, fee=Decimal("0.288"))
    assert r["entry_notional"] == Decimal("24")          # 60*0.40
    assert r["payout"] == Decimal("60")                  # 60*1
    assert r["gross_pnl"] == Decimal("36")               # 60-24
    assert r["net_pnl"] == Decimal("36") - Decimal("0.288")


def test_compute_pnl_loss_payout():
    r = pp.compute_pnl(filled_qty=Decimal("60"), exec_ask_vwap=Decimal("0.40"),
                       won=False, fee=Decimal("0.288"))
    assert r["payout"] == Decimal("0")
    assert r["gross_pnl"] == Decimal("-24")
    assert r["net_pnl"] == Decimal("-24") - Decimal("0.288")


def test_compute_pnl_fee_none_yields_not_computed_net():
    r = pp.compute_pnl(filled_qty=Decimal("60"), exec_ask_vwap=Decimal("0.40"),
                       won=True, fee=None)
    assert r["gross_pnl"] == Decimal("36")
    assert r["net_pnl"] == pp.FEE_METADATA_MISSING        # sentinel, never a silent number


# ===========================================================================
# cohort aggregation
# ===========================================================================
def test_aggregate_bucket_win_rate_and_totals():
    results = [
        {"status": "RESOLVED", "matched": True, "net_pnl": Decimal("36"), "slug": "btc-updown-15m-1"},
        {"status": "RESOLVED", "matched": False, "net_pnl": Decimal("-24"), "slug": "sol-updown-15m-1"},
        {"status": "RESOLUTION_NOT_FINAL", "matched": None, "net_pnl": None, "slug": "eth-updown-15m-2"},
    ]
    agg = pp.aggregate_bucket(results)
    assert agg["candidates"] == 3
    assert agg["resolved"] == 2
    assert agg["wins"] == 1 and agg["losses"] == 1
    assert agg["win_rate"] == "1/2"
    assert agg["total_net_pnl"] == Decimal("12")
    assert agg["mean_net_pnl"] == Decimal("6")
    assert agg["worst_loss"] == Decimal("-24")
    assert agg["best_win"] == Decimal("36")
    assert agg["unique_windows"] == 2


def test_aggregate_bucket_empty_is_zero_safe():
    agg = pp.aggregate_bucket([])
    assert agg["candidates"] == 0 and agg["resolved"] == 0
    assert agg["total_net_pnl"] == Decimal("0")
    assert agg["win_rate"] == "0/0"


def test_aggregate_bucket_excludes_not_computed_net_from_totals():
    results = [{"status": "RESOLVED", "matched": True, "net_pnl": pp.FEE_METADATA_MISSING,
               "slug": "btc-updown-15m-1"}]
    agg = pp.aggregate_bucket(results)
    assert agg["resolved"] == 1
    assert agg["net_pnl_computable"] == 0      # net excluded, but resolved/win counted
    assert agg["wins"] == 1
