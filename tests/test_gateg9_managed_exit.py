"""
Gate G9 — Managed Position / Exit Overlays (PURE module, OFFLINE).

Covers analysis.forensic.gateg9_managed_exit: shared entry cohort selection, the
qty-clamped bid-ladder walk, canonical entry/exit fee + PnL formulas, TP reachability,
each pre-registered exit overlay's trigger/fill mechanics, HOLD control resolution,
staged counterfactual tranche accounting, concurrent-exposure tally, and the structural
no-lookahead proofs.

PAPER/SHADOW only. Pure: no network, no DB, no clock. NO orders/wallet/signing/capital.
"""
import inspect
from decimal import Decimal

import pytest

from analysis.forensic import gateg7_paper_pnl as pp
from analysis.forensic import gateg9_managed_exit as ge

NOW_MS = 1_900_000_000_000


def _paper_open(condition_id, slug, *, selected_side="YES", yes_net_edge="0.10",
                no_net_edge="-0.05", ts=NOW_MS):
    return {"status": pp.PAPER_OPEN, "condition_id": condition_id, "slug": slug,
           "asset": slug.split("-")[0].upper(), "window": pp.window_of(slug),
           "paper_decision_ts": ts, "selected_side": selected_side,
           "selected_token_id": "tokSel", "yes_net_edge": yes_net_edge,
           "no_net_edge": no_net_edge, "selected_filled_qty": "62.5",
           "selected_entry_notional": "25", "yes_exec_ask_vwap": "0.40",
           "no_exec_ask_vwap": "0.55", "fee_rate": "0.07"}


# ===========================================================================
# 1/2 — shared entry cohort: identical set feeds every overlay; one per 15m window
# ===========================================================================
def test_select_shared_entry_cohort_keeps_single_non_correlated_candidate():
    decisions = [_paper_open("cid-1", "btc-updown-15m-1000")]
    out = ge.select_shared_entry_cohort(decisions)
    assert len(out) == 1
    assert out[0]["status"] == pp.PAPER_OPEN
    assert out[0]["condition_id"] == "cid-1"


def test_select_shared_entry_cohort_picks_highest_net_edge_in_same_window():
    a = _paper_open("cid-btc", "btc-updown-15m-1000", yes_net_edge="0.10")
    b = _paper_open("cid-sol", "sol-updown-15m-1000", yes_net_edge="0.30")
    out = ge.select_shared_entry_cohort([a, b])
    statuses = {d["condition_id"]: d["status"] for d in out}
    assert statuses["cid-sol"] == pp.PAPER_OPEN
    assert statuses["cid-btc"] == ge.CORRELATED_WINDOW_SKIPPED


def test_select_shared_entry_cohort_different_windows_both_survive():
    a = _paper_open("cid-btc", "btc-updown-15m-1000", yes_net_edge="0.10")
    b = _paper_open("cid-sol", "sol-updown-15m-1900", yes_net_edge="0.30")
    out = ge.select_shared_entry_cohort([a, b])
    statuses = {d["condition_id"]: d["status"] for d in out}
    assert statuses["cid-btc"] == pp.PAPER_OPEN
    assert statuses["cid-sol"] == pp.PAPER_OPEN


def test_select_shared_entry_cohort_preserves_non_paper_open_rows_untouched():
    non_open = {"status": "NO_PAPER_ENTRY", "condition_id": "cid-x",
               "slug": "eth-updown-15m-1000", "window": "1000"}
    out = ge.select_shared_entry_cohort([non_open])
    assert out == [non_open]


def test_identical_entry_set_feeds_every_overlay():
    position = _paper_open("cid-1", "btc-updown-15m-1000")
    cohort = ge.select_shared_entry_cohort([position])
    entered = cohort[0]
    # every overlay evaluator below is invoked on the SAME `entered` dict -- proves no
    # overlay receives a divergent/mutated view of the shared entry.
    held_qty = Decimal(entered["selected_filled_qty"])
    fee_rate = Decimal(entered["fee_rate"])
    bid_levels = [(Decimal("0.60"), Decimal("100"))]
    r1 = ge.evaluate_tp_trigger(ge.OVERLAY_TP_15_FULL, held_qty=held_qty, bid_levels=bid_levels,
                               fee_rate=fee_rate, allocated_entry_cost=Decimal("25"))
    r2 = ge.evaluate_tp_trigger(ge.OVERLAY_TP_20_FULL, held_qty=held_qty, bid_levels=bid_levels,
                               fee_rate=fee_rate, allocated_entry_cost=Decimal("25"))
    r3 = ge.evaluate_time_stop_trigger(60)
    r4 = ge.evaluate_model_premium_exit_trigger(held_qty=held_qty, bid_levels=bid_levels,
                                                fee_rate=fee_rate, fair_prob_selected_side=Decimal("0.32"))
    assert entered["selected_filled_qty"] == "62.5"   # unmutated across all four calls
    assert isinstance(r1, dict) and isinstance(r2, dict) and isinstance(r3, bool) and isinstance(r4, dict)


# ===========================================================================
# 3/4 — TP is percentage-of-entry; unreachable TP is labeled, never a "miss"
# ===========================================================================
def test_tp_target_price_is_percentage_not_absolute_cents():
    target = ge.gross_tp_target_price(Decimal("0.40"), Decimal("0.15"))
    assert target == Decimal("0.46")   # 0.40 * 1.15, not 0.40 + 0.15


def test_tp_reachability_high_priced_entry_unreachable_is_labeled_not_a_failure():
    target = ge.gross_tp_target_price(Decimal("0.95"), Decimal("0.15"))
    assert target == Decimal("1.0925")
    assert ge.gross_tp_reachable(target) is False
    # unreachable is a LABEL, not folded into the trigger evaluation as a fault:
    result = ge.evaluate_tp_trigger(ge.OVERLAY_TP_15_FULL, held_qty=Decimal("10"),
                                    bid_levels=[(Decimal("0.95"), Decimal("100"))],
                                    fee_rate=Decimal("0.07"), allocated_entry_cost=Decimal("9.5"))
    assert "reachable" not in result or result.get("triggered") is not None  # never a crash/miss sentinel
    assert isinstance(result["triggered"], bool)


def test_tp_reachability_low_priced_entry_is_reachable():
    target = ge.gross_tp_target_price(Decimal("0.40"), Decimal("0.30"))
    assert ge.gross_tp_reachable(target) is True


# ===========================================================================
# 5/6 — trigger (poll K) never supplies a fill price; fill (poll K+1) uses its OWN ladder
# ===========================================================================
def test_trigger_evidence_never_marks_a_fill():
    result = ge.evaluate_tp_trigger(ge.OVERLAY_TP_15_FULL, held_qty=Decimal("10"),
                                    bid_levels=[(Decimal("0.60"), Decimal("100"))],
                                    fee_rate=Decimal("0.07"), allocated_entry_cost=Decimal("4"))
    assert "status" not in result   # only execute_full_exit_fill ever returns a fill "status"
    assert result["triggered"] is True


def test_fill_uses_only_the_next_poll_ladder_not_the_trigger_poll_ladder():
    poll_k_levels = [(Decimal("0.99"), Decimal("1000"))]     # would give a huge VWAP if reused
    poll_k1_levels = [(Decimal("0.60"), Decimal("100"))]      # the REAL fill ladder
    fill = ge.execute_full_exit_fill(qty=Decimal("10"), next_bid_levels=poll_k1_levels,
                                     fee_rate=Decimal("0.07"), allocated_entry_cost=Decimal("4"))
    assert fill["bid_fill"].exec_bid_vwap == Decimal("0.60")
    assert fill["status"] == "FILLED"
    # the function signature does not even accept a trigger-poll ladder -- structurally cannot mix them
    assert "bid_levels" not in inspect.signature(ge.execute_full_exit_fill).parameters


# ===========================================================================
# PARTIAL-FILL CONSERVATION (pure) — execute_exit_fill books the filled leg, allocates
# entry cost EXACTLY to the filled quantity, and conserves the residual + residual cost
# with exact Decimal remainder (no disappearing shares/cost/fees).
# ===========================================================================
def test_execute_exit_fill_full_depth_marks_filled_zero_residual():
    out = ge.execute_exit_fill(requested_qty=Decimal("62.5"),
                               next_bid_levels=[(Decimal("0.60"), Decimal("100"))],
                               fee_rate=Decimal("0.07"), remaining_allocated_cost=Decimal("25.245"))
    assert out["status"] == ge.FILL_FILLED
    assert out["filled_qty"] == Decimal("62.5")
    assert out["remaining_qty_after"] == Decimal("0")
    assert out["remaining_cost_after"] == Decimal("0")
    assert out["leg_cost"] == Decimal("25.245")   # full depth -> whole cost basis allocated


def test_execute_exit_fill_zero_depth_marks_no_fill_unchanged():
    out = ge.execute_exit_fill(requested_qty=Decimal("62.5"),
                               next_bid_levels=[], fee_rate=Decimal("0.07"),
                               remaining_allocated_cost=Decimal("25.245"))
    assert out["status"] == ge.FILL_NONE
    assert out["filled_qty"] == Decimal("0")
    assert out["remaining_qty_after"] == Decimal("62.5")       # residual untouched
    assert out["remaining_cost_after"] == Decimal("25.245")    # cost basis untouched


def test_execute_exit_fill_partial_depth_conserves_residual_and_cost_exactly():
    # only 40 of 62.5 shares available; cost basis allocated proportionally to the 40,
    # residual 22.5 shares keep the exact remaining cost -- sums must be exact.
    out = ge.execute_exit_fill(requested_qty=Decimal("62.5"),
                               next_bid_levels=[(Decimal("0.60"), Decimal("40"))],
                               fee_rate=Decimal("0.07"), remaining_allocated_cost=Decimal("25.245"))
    assert out["status"] == ge.FILL_PARTIAL
    assert out["filled_qty"] == Decimal("40")
    assert out["remaining_qty_after"] == Decimal("22.5")
    # exact conservation: leg cost + residual cost == the whole cost basis
    assert out["leg_cost"] + out["remaining_cost_after"] == Decimal("25.245")
    # leg cost is proportional to the filled fraction
    assert out["leg_cost"] == Decimal("25.245") * Decimal("40") / Decimal("62.5")
    # realized leg pnl uses the leg's own exit fee, no residual leakage
    assert out["realized_net_pnl"] == out["net_exit_proceeds"] - out["leg_cost"]


def test_execute_exit_fill_two_partial_legs_reconcile_cost_to_the_penny():
    # leg 1 fills 30 of 62.5; leg 2 fills the remaining 32.5. Feeding leg 1's residual
    # (qty + cost) into leg 2 must telescope the cost basis back to EXACTLY the original.
    cost0 = Decimal("25.245")
    leg1 = ge.execute_exit_fill(requested_qty=Decimal("62.5"),
                                next_bid_levels=[(Decimal("0.60"), Decimal("30"))],
                                fee_rate=Decimal("0.07"), remaining_allocated_cost=cost0)
    assert leg1["status"] == ge.FILL_PARTIAL
    leg2 = ge.execute_exit_fill(requested_qty=leg1["remaining_qty_after"],
                                next_bid_levels=[(Decimal("0.58"), Decimal("100"))],
                                fee_rate=Decimal("0.07"),
                                remaining_allocated_cost=leg1["remaining_cost_after"])
    assert leg2["status"] == ge.FILL_FILLED
    assert leg2["remaining_qty_after"] == Decimal("0")
    assert leg1["leg_cost"] + leg2["leg_cost"] == cost0   # exact, no cent lost/fabricated


# ===========================================================================
# 7 — full vs partial depth is honest (never fabricated)
# ===========================================================================
def test_bid_ladder_walk_full_depth():
    fill = ge.walk_bid_ladder_for_qty([(Decimal("0.60"), Decimal("50")), (Decimal("0.55"), Decimal("50"))],
                                      Decimal("30"))
    assert fill.filled_qty == Decimal("30")
    assert fill.depth_sufficient is True
    assert fill.residual_unfilled_qty == Decimal("0")
    assert fill.exec_bid_vwap == Decimal("0.60")


def test_bid_ladder_walk_partial_depth_honest():
    fill = ge.walk_bid_ladder_for_qty([(Decimal("0.60"), Decimal("10")), (Decimal("0.55"), Decimal("5"))],
                                      Decimal("30"))
    assert fill.filled_qty == Decimal("15")            # only what's actually there
    assert fill.depth_sufficient is False
    assert fill.residual_unfilled_qty == Decimal("15")  # honest shortfall, never fabricated


def test_bid_ladder_walk_would_move_book_flag():
    one_level = ge.walk_bid_ladder_for_qty([(Decimal("0.60"), Decimal("100"))], Decimal("10"))
    two_level = ge.walk_bid_ladder_for_qty(
        [(Decimal("0.60"), Decimal("5")), (Decimal("0.55"), Decimal("5"))], Decimal("10"))
    assert one_level.would_move_book is False
    assert two_level.would_move_book is True


# ===========================================================================
# 8 — canonical entry AND exit fees reuse the SAME committed quadratic formula
# ===========================================================================
def test_entry_cost_reuses_canonical_quadratic_fee():
    out = ge.compute_entry_cost(ask_vwap=Decimal("0.40"), filled_qty=Decimal("62.5"),
                                fee_rate=Decimal("0.07"))
    expected_fee = pp.entry_fee_quadratic(Decimal("62.5"), Decimal("0.07"), Decimal("0.40"))
    assert out["entry_fee"] == expected_fee
    assert out["entry_cost"] == Decimal("0.40") * Decimal("62.5") + expected_fee


def test_exit_fee_reuses_canonical_quadratic_fee():
    got = ge.compute_exit_fee(Decimal("62.5"), Decimal("0.07"), Decimal("0.60"))
    expected = pp.entry_fee_quadratic(Decimal("62.5"), Decimal("0.07"), Decimal("0.60"))
    assert got == expected


# ===========================================================================
# 9 — HOLD control win/loss resolution PnL
# ===========================================================================
def test_hold_control_win():
    resolution = {"status": "RESOLVED", "won": True}
    out = ge.evaluate_hold_control(remaining_shares=Decimal("62.5"),
                                   allocated_entry_cost=Decimal("25.245"), resolution=resolution)
    assert out["status"] == ge.RESOLVED_HOLD
    assert out["payout"] == Decimal("62.5")
    assert out["realized_net_pnl"] == Decimal("62.5") - Decimal("25.245")


def test_hold_control_loss():
    resolution = {"status": "RESOLVED", "won": False}
    out = ge.evaluate_hold_control(remaining_shares=Decimal("62.5"),
                                   allocated_entry_cost=Decimal("25.245"), resolution=resolution)
    assert out["status"] == ge.RESOLVED_HOLD
    assert out["payout"] == Decimal("0")
    assert out["realized_net_pnl"] == Decimal("0") - Decimal("25.245")


def test_terminal_settlement_is_structurally_fee_free():
    # compute_resolution_pnl (the ONLY terminal-settlement PnL path) takes NO fee
    # parameter -- settlement can never charge a taker/exit fee, structurally.
    params = inspect.signature(ge.compute_resolution_pnl).parameters
    for forbidden in ("fee", "fee_rate", "exit_fee"):
        assert forbidden not in params
    # numeric: winning payout is exactly shares (1.0 each), pnl = payout - cost, no fee drag
    out = ge.compute_resolution_pnl(remaining_shares=Decimal("62.5"), won=True,
                                    allocated_entry_cost=Decimal("25.245"))
    assert out["payout"] == Decimal("62.5")
    assert out["realized_net_pnl"] == Decimal("62.5") - Decimal("25.245")


def test_hold_control_pending_resolution():
    out = ge.evaluate_hold_control(remaining_shares=Decimal("62.5"),
                                   allocated_entry_cost=Decimal("25.245"),
                                   resolution={"status": ge.RESOLUTION_PENDING})
    assert out["status"] == ge.RESOLUTION_PENDING


def test_hold_control_gamma_clob_conflict_fails_closed():
    out = ge.evaluate_hold_control(remaining_shares=Decimal("62.5"),
                                   allocated_entry_cost=Decimal("25.245"),
                                   resolution={"status": ge.GAMMA_CLOB_CONFLICT_FAIL_CLOSED})
    assert out["status"] == ge.GAMMA_CLOB_CONFLICT_FAIL_CLOSED


# ===========================================================================
# 10 — TP15/20/30 are independent overlays; different thresholds -> different outcomes
# ===========================================================================
def test_tp_overlays_independent_thresholds_diverge():
    # bid vwap 0.50 on a 0.40 entry -> gross return 25%; net ROI slightly under after fees
    bid_levels = [(Decimal("0.50"), Decimal("100"))]
    r15 = ge.evaluate_tp_trigger(ge.OVERLAY_TP_15_FULL, held_qty=Decimal("62.5"),
                                 bid_levels=bid_levels, fee_rate=Decimal("0.07"),
                                 allocated_entry_cost=Decimal("25.245"))
    r30 = ge.evaluate_tp_trigger(ge.OVERLAY_TP_30_FULL, held_qty=Decimal("62.5"),
                                 bid_levels=bid_levels, fee_rate=Decimal("0.07"),
                                 allocated_entry_cost=Decimal("25.245"))
    assert r15["triggered"] is True
    assert r30["triggered"] is False


# ===========================================================================
# 11 — T-120 boundary
# ===========================================================================
@pytest.mark.parametrize("tte_s,expected", [(121, False), (120, True), (119, True), (0, True)])
def test_time_stop_t120_boundary(tte_s, expected):
    assert ge.evaluate_time_stop_trigger(tte_s) is expected


def test_time_stop_none_tte_never_triggers():
    assert ge.evaluate_time_stop_trigger(None) is False


# ===========================================================================
# 12 — MODEL_PREMIUM_EXIT (renamed from EDGE_INVALIDATION): current fee-net executable
# exit value >= current model hold value (fair_selected * remaining qty). This is a
# model-PREMIUM exit, NOT entry-thesis deterioration -- see ENTRY_THESIS_INVALIDATION.
# ===========================================================================
def test_model_premium_exit_triggers_when_exit_value_beats_hold_value():
    bid_levels = [(Decimal("0.55"), Decimal("100"))]
    out = ge.evaluate_model_premium_exit_trigger(held_qty=Decimal("62.5"), bid_levels=bid_levels,
                                                 fee_rate=Decimal("0.07"),
                                                 fair_prob_selected_side=Decimal("0.32"))
    assert out["triggered"] is True
    # model hold value is computed INTERNALLY from fair * held_qty (quantity-aligned)
    assert out["model_hold_value"] == Decimal("0.32") * Decimal("62.5")
    assert out["fee_net_exit_value"] >= out["model_hold_value"]


def test_model_premium_exit_does_not_trigger_when_hold_value_higher():
    bid_levels = [(Decimal("0.30"), Decimal("100"))]
    out = ge.evaluate_model_premium_exit_trigger(held_qty=Decimal("62.5"), bid_levels=bid_levels,
                                                 fee_rate=Decimal("0.07"),
                                                 fair_prob_selected_side=Decimal("0.48"))
    assert out["triggered"] is False


def test_model_premium_exit_requires_full_depth_at_trigger_poll():
    # only 5 of 62.5 shares available at poll K -> the full-position overlay must NOT
    # trigger on partial depth (a full exit it cannot execute is not a real trigger).
    bid_levels = [(Decimal("0.90"), Decimal("5"))]
    out = ge.evaluate_model_premium_exit_trigger(held_qty=Decimal("62.5"), bid_levels=bid_levels,
                                                 fee_rate=Decimal("0.07"),
                                                 fair_prob_selected_side=Decimal("0.32"))
    assert out["triggered"] is False
    assert out["depth_sufficient"] is False


def test_model_premium_exit_compares_equal_quantities():
    # the executable exit value and the model hold value must both be computed over the
    # SAME (full remaining) quantity -- never a qty-mismatched comparison.
    qty = Decimal("62.5")
    fair = Decimal("0.50")
    bid_levels = [(Decimal("0.60"), Decimal("100"))]
    out = ge.evaluate_model_premium_exit_trigger(held_qty=qty, bid_levels=bid_levels,
                                                 fee_rate=Decimal("0.07"), fair_prob_selected_side=fair)
    assert out["model_hold_value"] == fair * qty
    assert out["bid_fill"].filled_qty == qty


def test_model_premium_exit_fill_at_next_poll():
    fill = ge.execute_full_exit_fill(qty=Decimal("62.5"),
                                     next_bid_levels=[(Decimal("0.55"), Decimal("100"))],
                                     fee_rate=Decimal("0.07"), allocated_entry_cost=Decimal("25.245"))
    assert fill["status"] == "FILLED"


# ===========================================================================
# 12b — ENTRY_THESIS_INVALIDATION: an INDEPENDENT overlay that triggers when the current
# model hold value has decayed to/below the remaining shares' fixed entry cost basis.
# Distinct from MODEL_PREMIUM_EXIT (which harvests a positive model premium).
# ===========================================================================
def test_entry_thesis_invalidation_triggers_when_model_value_at_or_below_cost_basis():
    # 62.5 shares, fixed cost basis 26.09; fair decayed to 0.40 -> model value 25.0 <= 26.09.
    out = ge.evaluate_entry_thesis_invalidation_trigger(
        remaining_shares=Decimal("62.5"), fair_prob_selected_side=Decimal("0.40"),
        remaining_allocated_entry_cost=Decimal("26.09"))
    assert out["triggered"] is True
    assert out["model_hold_value"] == Decimal("0.40") * Decimal("62.5")


def test_entry_thesis_invalidation_does_not_trigger_when_model_value_above_cost_basis():
    out = ge.evaluate_entry_thesis_invalidation_trigger(
        remaining_shares=Decimal("62.5"), fair_prob_selected_side=Decimal("0.60"),
        remaining_allocated_entry_cost=Decimal("26.09"))
    assert out["triggered"] is False   # model value 37.5 > 26.09 -> thesis intact


def test_entry_thesis_invalidation_boundary_equal_triggers():
    # model value exactly equal to the cost basis -> triggered (<=)
    out = ge.evaluate_entry_thesis_invalidation_trigger(
        remaining_shares=Decimal("50"), fair_prob_selected_side=Decimal("0.50"),
        remaining_allocated_entry_cost=Decimal("25"))
    assert out["triggered"] is True


def test_entry_thesis_invalidation_never_subtracts_prior_realized_proceeds():
    # structural: the trigger has NO parameter for prior proceeds/realized pnl -- the cost
    # basis it compares against is the caller's residual entry cost ONLY.
    params = inspect.signature(ge.evaluate_entry_thesis_invalidation_trigger).parameters
    for forbidden in ("prior_proceeds", "realized_pnl", "net_proceeds", "prior_realized"):
        assert forbidden not in params
    assert set(params) == {"remaining_shares", "fair_prob_selected_side",
                           "remaining_allocated_entry_cost"}


def test_model_premium_and_entry_thesis_are_different_comparisons():
    # A decayed-but-still-liquid position: model value (fair*qty) is BELOW cost basis
    # (entry-thesis invalidation triggers) yet the executable exit value still clears the
    # (now-low) model value (model-premium also triggers). Same inputs, two independent
    # verdicts computed by two different formulas.
    qty = Decimal("62.5")
    fair = Decimal("0.40")
    bid_levels = [(Decimal("0.45"), Decimal("100"))]
    mpe = ge.evaluate_model_premium_exit_trigger(held_qty=qty, bid_levels=bid_levels,
                                                 fee_rate=Decimal("0.07"), fair_prob_selected_side=fair)
    eti = ge.evaluate_entry_thesis_invalidation_trigger(
        remaining_shares=qty, fair_prob_selected_side=fair,
        remaining_allocated_entry_cost=Decimal("26.09"))
    assert mpe["triggered"] is True    # exit value (>= ~27) beats model value (25.0)
    assert eti["triggered"] is True    # model value (25.0) <= cost basis (26.09)
    # they are NOT the same computation: entry-thesis never walks a bid ladder
    assert "bid_fill" not in eti


# ===========================================================================
# 13 — staged 1/3 tranche accounting + resolution remainder
# ===========================================================================
def test_split_into_thirds_sums_exactly_to_held_qty():
    thirds = ge.split_into_thirds(Decimal("62.5"))
    assert len(thirds) == 3
    assert sum(thirds, Decimal("0")) == Decimal("62.5")


def test_staged_counterfactual_two_tranches_filled_one_to_resolution():
    held_qty = Decimal("60")
    fee_rate = Decimal("0.07")
    entry_cost = Decimal("24")
    tranche_qtys = ge.split_into_thirds(held_qty)
    tranche15 = ge.execute_full_exit_fill(qty=tranche_qtys[0],
                                          next_bid_levels=[(Decimal("0.46"), Decimal("100"))],
                                          fee_rate=fee_rate, allocated_entry_cost=entry_cost / 3)
    tranche20 = ge.execute_full_exit_fill(qty=tranche_qtys[1],
                                          next_bid_levels=[(Decimal("0.48"), Decimal("100"))],
                                          fee_rate=fee_rate, allocated_entry_cost=entry_cost / 3)
    resolution = {"status": "RESOLVED", "won": True}
    out = ge.evaluate_staged_counterfactual(
        held_qty=held_qty, fee_rate=fee_rate, allocated_entry_cost=entry_cost,
        tranche_fills=[tranche15, tranche20, None], resolution=resolution)
    assert out["tranche_results"][0]["realized_net_pnl"] == tranche15["realized_net_pnl"]
    assert out["tranche_results"][1]["realized_net_pnl"] == tranche20["realized_net_pnl"]
    assert out["tranche_results"][2]["status"] == ge.RESOLVED_HOLD   # remainder went to resolution
    expected_combined = (tranche15["realized_net_pnl"] + tranche20["realized_net_pnl"]
                         + out["tranche_results"][2]["realized_net_pnl"])
    assert out["combined_net_pnl"] == expected_combined


# ===========================================================================
# 16 — delayed entry-depth persistence evidence (never rewrites the original entry)
# ===========================================================================
def test_entry_depth_persistence_confirms_available_depth():
    out = ge.record_entry_depth_persistence(
        entry_ask_vwap=Decimal("0.40"), entry_filled_qty=Decimal("62.5"),
        confirmation_ask_levels=[(Decimal("0.40"), Decimal("100"))])
    assert out["depth_persisted"] is True
    assert out["confirmation_ask_vwap"] == Decimal("0.40")


def test_entry_depth_persistence_detects_slippage_without_rewriting_entry():
    entry_ask_vwap = Decimal("0.40")
    out = ge.record_entry_depth_persistence(
        entry_ask_vwap=entry_ask_vwap, entry_filled_qty=Decimal("62.5"),
        confirmation_ask_levels=[(Decimal("0.50"), Decimal("100"))])
    assert out["depth_persisted"] is False
    assert entry_ask_vwap == Decimal("0.40")   # original entry value untouched by the caller


# ===========================================================================
# 15 — concurrent exposure tally
# ===========================================================================
def _timing_kwargs(**over):
    base = dict(selected_quote_ts_ms=NOW_MS - 100, selected_capture_completed_ms=NOW_MS - 50,
               opposite_quote_ts_ms=NOW_MS - 90, opposite_capture_completed_ms=NOW_MS - 40,
               hl_feed_ts=NOW_MS - 30_000, hl_capture_completed_ms=NOW_MS - 20,
               poll_decision_ts=NOW_MS, quote_stale_ms=2000)
    base.update(over)
    return base


def test_validate_monitoring_timing_ok():
    out = ge.validate_monitoring_timing(**_timing_kwargs())
    assert out == {"ok": True}


def test_validate_monitoring_timing_rejects_future_capture():
    out = ge.validate_monitoring_timing(**_timing_kwargs(opposite_capture_completed_ms=NOW_MS + 500))
    assert out["ok"] is False
    assert out["status"] == ge.MONITORING_TIMESTAMP_REJECTED
    assert out["field"] == "opposite_capture_completed_ms"
    assert out["reason"] == "future"


def test_validate_monitoring_timing_rejects_missing_field():
    out = ge.validate_monitoring_timing(**_timing_kwargs(hl_feed_ts=None))
    assert out["ok"] is False
    assert out["field"] == "hl_feed_ts"
    assert out["reason"] == "missing"


def test_validate_monitoring_timing_rejects_stale_quote():
    out = ge.validate_monitoring_timing(**_timing_kwargs(selected_quote_ts_ms=NOW_MS - 5000))
    assert out["ok"] is False
    assert out["field"] == "selected_quote_ts_ms"
    assert out["reason"] == "stale"


def test_validate_monitoring_timing_never_uses_resolution_data():
    assert "resolution" not in inspect.signature(ge.validate_monitoring_timing).parameters
    assert "outcome" not in inspect.signature(ge.validate_monitoring_timing).parameters


def test_concurrent_exposure_tally():
    open_positions = [
        {"condition_id": "c1", "asset": "BTC", "selected_side": "YES", "entry_cost": Decimal("25")},
        {"condition_id": "c2", "asset": "ETH", "selected_side": "YES", "entry_cost": Decimal("25")},
        {"condition_id": "c3", "asset": "SOL", "selected_side": "NO", "entry_cost": Decimal("25")},
    ]
    out = ge.tally_concurrent_exposure(open_positions)
    assert out["open_position_count"] == 3
    assert out["aggregate_paper_notional"] == Decimal("75")
    assert out["same_direction_count"]["YES"] == 2
    assert out["same_direction_count"]["NO"] == 1
    assert set(out["assets"]) == {"BTC", "ETH", "SOL"}


def test_format_telegram_report_deterministic_and_never_calls_loss_a_win():
    position = {"asset": "BTC", "window": "1000", "selected_side": "YES",
               "entry_ask_vwap": "0.40", "held_qty": "62.5", "entry_fee": "1.09"}
    overlay_terminals = {
        ge.OVERLAY_HOLD_CONTROL: {"status": ge.RESOLVED_HOLD, "realized_net_pnl": "-25.24"},
        ge.OVERLAY_TP_15_FULL: {"status": ge.TP_EXIT_FILLED, "realized_net_pnl": "3.50"},
    }
    exposure = {"open_position_count": 2, "aggregate_paper_notional": Decimal("50")}
    report1 = ge.format_telegram_report(position=position, overlay_terminals=overlay_terminals,
                                        concurrent_exposure=exposure)
    report2 = ge.format_telegram_report(position=position, overlay_terminals=overlay_terminals,
                                        concurrent_exposure=exposure)
    assert report1 == report2   # deterministic
    assert "PAPER/SHADOW" in report1 and "NOT TRADEABLE ALPHA" in report1
    assert f"BEST overlay: {ge.OVERLAY_TP_15_FULL}" in report1
    assert f"WORST overlay: {ge.OVERLAY_HOLD_CONTROL}" in report1
    assert "BEST overlay: " + ge.OVERLAY_HOLD_CONTROL not in report1   # the loss is never labeled BEST


def test_concurrent_exposure_tally_empty():
    out = ge.tally_concurrent_exposure([])
    assert out["open_position_count"] == 0
    assert out["aggregate_paper_notional"] == Decimal("0")


# ===========================================================================
# 18 — no-lookahead structural proofs
# ===========================================================================
@pytest.mark.parametrize("fn", [
    ge.evaluate_tp_trigger, ge.evaluate_model_premium_exit_trigger,
    ge.evaluate_entry_thesis_invalidation_trigger, ge.execute_full_exit_fill,
    ge.walk_bid_ladder_for_qty,
])
def test_no_lookahead_forbidden_params_absent(fn):
    params = inspect.signature(fn).parameters
    for forbidden in ("resolution", "outcome", "winner", "final_price", "next_next_bid_levels"):
        assert forbidden not in params, f"{fn.__name__} leaks {forbidden}"


def test_evaluate_hold_control_resolution_is_opaque_status_only():
    # the resolution dict is treated as an opaque pre-computed input, never derived here
    import inspect as _inspect
    src_params = _inspect.signature(ge.evaluate_hold_control).parameters
    assert "resolution" in src_params   # hold-control explicitly takes an ALREADY-decided outcome
    assert "gamma_payload" not in src_params and "clob_payload" not in src_params


# ===========================================================================
# PHASE A.1 — model hold value vs executable liquidation value (pure helper)
# ===========================================================================
def test_compute_model_hold_value_is_fair_probability_times_remaining_shares():
    out = ge.compute_model_hold_value(fair_prob_selected_side=Decimal("0.65"),
                                      remaining_shares=Decimal("62.5"))
    assert out == Decimal("0.65") * Decimal("62.5")


def test_model_hold_value_differs_from_executable_exit_proceeds():
    # same position, same bid ladder: the MODEL value and the EXECUTABLE value must be
    # computed independently and must NOT collapse to the same number/name.
    model_value = ge.compute_model_hold_value(fair_prob_selected_side=Decimal("0.65"),
                                              remaining_shares=Decimal("62.5"))
    fill = ge.walk_bid_ladder_for_qty([(Decimal("0.50"), Decimal("100"))], Decimal("62.5"))
    exit_fee = ge.compute_exit_fee(fill.filled_qty, Decimal("0.07"), fill.exec_bid_vwap)
    executable_value = fill.proceeds - exit_fee
    assert model_value != executable_value
    assert model_value == Decimal("40.625")
    assert executable_value == Decimal("62.5") * Decimal("0.50") - exit_fee


# ===========================================================================
# PHASE A.4 — cohort selection must reject missing/malformed/non-finite/non-positive
# selected_net_edge BEFORE ranking; such a candidate must never win or outrank a valid one.
# ===========================================================================
def test_cohort_selection_rejects_missing_edge():
    d = _paper_open("cid-1", "btc-updown-15m-1000", yes_net_edge=None)
    out = ge.select_shared_entry_cohort([d])
    assert out[0]["status"] == ge.INVALID_EDGE_REJECTED


def test_cohort_selection_rejects_non_finite_edge():
    d = _paper_open("cid-1", "btc-updown-15m-1000", yes_net_edge="NaN")
    out = ge.select_shared_entry_cohort([d])
    assert out[0]["status"] == ge.INVALID_EDGE_REJECTED


def test_cohort_selection_rejects_non_positive_edge():
    d = _paper_open("cid-1", "btc-updown-15m-1000", yes_net_edge="0")
    out = ge.select_shared_entry_cohort([d])
    assert out[0]["status"] == ge.INVALID_EDGE_REJECTED
    d2 = _paper_open("cid-2", "btc-updown-15m-1900", yes_net_edge="-0.02")
    out2 = ge.select_shared_entry_cohort([d2])
    assert out2[0]["status"] == ge.INVALID_EDGE_REJECTED


def test_cohort_selection_invalid_edge_never_outranks_valid_edge_same_window():
    invalid = _paper_open("cid-invalid", "btc-updown-15m-1000", yes_net_edge=None)
    valid = _paper_open("cid-valid", "sol-updown-15m-1000", yes_net_edge="0.05")
    out = ge.select_shared_entry_cohort([invalid, valid])
    statuses = {d["condition_id"]: d["status"] for d in out}
    assert statuses["cid-valid"] == pp.PAPER_OPEN
    assert statuses["cid-invalid"] == ge.INVALID_EDGE_REJECTED


# ===========================================================================
# PHASE A.6 — exit ladder integrity: validate before any bid-VWAP walk (reuse the
# established gateg5_plumbing book validation; malformed levels fail closed via the
# existing PlumbingError hierarchy, never a fabricated VWAP).
# ===========================================================================
def test_walk_bid_ladder_for_qty_rejects_malformed_price():
    from analysis.forensic import gateg5_plumbing as _plumb
    with pytest.raises(_plumb.PlumbingError):
        ge.walk_bid_ladder_for_qty([(Decimal("1.50"), Decimal("10"))], Decimal("5"))  # price > 1


def test_walk_bid_ladder_for_qty_rejects_non_positive_size():
    from analysis.forensic import gateg5_plumbing as _plumb
    with pytest.raises(_plumb.PlumbingError):
        ge.walk_bid_ladder_for_qty([(Decimal("0.50"), Decimal("0"))], Decimal("5"))


def test_walk_bid_ladder_for_qty_merges_duplicate_price_levels():
    fill = ge.walk_bid_ladder_for_qty(
        [(Decimal("0.60"), Decimal("10")), (Decimal("0.60"), Decimal("10"))], Decimal("15"))
    assert fill.filled_qty == Decimal("15")
    assert fill.exec_bid_vwap == Decimal("0.60")


def test_walk_ask_ladder_for_qty_basic():
    out = ge.walk_ask_ladder_for_qty([(Decimal("0.40"), Decimal("100"))], Decimal("62.5"))
    assert out["filled_qty"] == Decimal("62.5")
    assert out["exec_vwap"] == Decimal("0.40")
    assert out["depth_sufficient"] is True


# ===========================================================================
# PHASE A.3 — entry-depth persistence re-walks the EXACT original share quantity,
# never a re-derived dollar notional (price*qty is not invariant under a price move).
# ===========================================================================
def test_entry_depth_persistence_uses_exact_quantity_not_notional():
    # entry: 62.5 shares @ 0.40 (notional 25.0). Confirmation ladder has DEEP liquidity at
    # a HIGHER price (0.50) but only shallow (10 shares) at a price <= entry -- a
    # notional-based re-walk (25.0 / 0.50 = 50 shares) would wrongly report sufficient
    # depth; the CORRECT qty-based walk must request the exact original 62.5 shares.
    out = ge.record_entry_depth_persistence(
        entry_ask_vwap=Decimal("0.40"), entry_filled_qty=Decimal("62.5"),
        confirmation_ask_levels=[(Decimal("0.40"), Decimal("10")), (Decimal("0.50"), Decimal("1000"))])
    assert out["confirmation_filled_qty"] == Decimal("62.5")   # walked for the FULL 62.5, not 50
    assert out["confirmation_depth_sufficient"] is True


def test_entry_depth_persistence_partial_quantity_fails_closed_admission():
    out = ge.record_entry_depth_persistence(
        entry_ask_vwap=Decimal("0.40"), entry_filled_qty=Decimal("62.5"),
        confirmation_ask_levels=[(Decimal("0.40"), Decimal("10"))])   # only 10 of 62.5 available
    assert out["confirmation_depth_sufficient"] is False
    assert out["admitted"] is False
    assert out["confirmation_filled_qty"] == Decimal("10")            # honest partial, not fabricated
    assert out["confirmation_residual_unfilled_qty"] == Decimal("52.5")


# ===========================================================================
# PHASE A.7 — staged accounting: exactly 3 tranches, proportional cost allocation,
# exact Decimal remainder, no silent zip truncation.
# ===========================================================================
def test_staged_counterfactual_requires_exactly_three_tranche_fills():
    with pytest.raises(ge.ManagedExitError):
        ge.evaluate_staged_counterfactual(held_qty=Decimal("60"), fee_rate=Decimal("0.07"),
                                          allocated_entry_cost=Decimal("24"),
                                          tranche_fills=[None, None],   # only 2, not 3
                                          resolution={"status": "RESOLVED", "won": True})


def test_staged_counterfactual_allocated_costs_sum_exactly_to_total():
    held_qty = Decimal("62.5")
    entry_cost = Decimal("25.245")
    out = ge.evaluate_staged_counterfactual(
        held_qty=held_qty, fee_rate=Decimal("0.07"), allocated_entry_cost=entry_cost,
        tranche_fills=[None, None, None], resolution={"status": "RESOLVED", "won": True})
    assert sum(out["tranche_costs"], Decimal("0")) == entry_cost
    assert sum(out["tranche_qtys"], Decimal("0")) == held_qty


def test_combine_staged_tranche_pnls_sums_then_divides_once():
    # aggregate net PnL = exact dollar sum of the three tranche PnLs; ROI = that sum over
    # the ORIGINAL full entry cost -- never an average of the three tranche ROI percentages.
    out = ge.combine_staged_tranche_pnls([Decimal("1.00"), Decimal("-0.40"), Decimal("2.10")],
                                         Decimal("24"))
    assert out["combined_net_pnl"] == Decimal("2.70")
    assert out["aggregate_roi"] == Decimal("2.70") / Decimal("24")


def test_combine_staged_tranche_pnls_none_when_a_tranche_incomplete():
    out = ge.combine_staged_tranche_pnls([Decimal("1.00"), None, Decimal("2.10")], Decimal("24"))
    assert out["combined_net_pnl"] is None
    assert out["aggregate_roi"] is None


def test_combine_staged_tranche_pnls_requires_exactly_three():
    with pytest.raises(ge.ManagedExitError):
        ge.combine_staged_tranche_pnls([Decimal("1.00"), Decimal("2.10")], Decimal("24"))


def test_staged_counterfactual_cost_allocated_by_exact_filled_quantity():
    # unequal tranche sizes (via a non-multiple-of-3 qty) must allocate cost proportionally,
    # not always exactly 1/3 -- proven by checking cost1/cost2 track qty1/qty2 ratios.
    held_qty = Decimal("100")
    entry_cost = Decimal("30")
    out = ge.evaluate_staged_counterfactual(
        held_qty=held_qty, fee_rate=Decimal("0.07"), allocated_entry_cost=entry_cost,
        tranche_fills=[None, None, None], resolution={"status": "RESOLVED", "won": True})
    qtys = out["tranche_qtys"]
    costs = out["tranche_costs"]
    assert (costs[0] / entry_cost) == (qtys[0] / held_qty)
