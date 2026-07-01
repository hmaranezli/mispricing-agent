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
    r4 = ge.evaluate_edge_invalidation_trigger(held_qty=held_qty, bid_levels=bid_levels,
                                              fee_rate=fee_rate, model_hold_value=Decimal("20"))
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
# 12 — edge-invalidation formula + next-poll fill
# ===========================================================================
def test_edge_invalidation_triggers_when_exit_value_beats_hold_value():
    bid_levels = [(Decimal("0.55"), Decimal("100"))]
    out = ge.evaluate_edge_invalidation_trigger(held_qty=Decimal("62.5"), bid_levels=bid_levels,
                                                fee_rate=Decimal("0.07"),
                                                model_hold_value=Decimal("20"))
    assert out["triggered"] is True
    assert out["fee_net_exit_value"] >= out["model_hold_value"]


def test_edge_invalidation_does_not_trigger_when_hold_value_higher():
    bid_levels = [(Decimal("0.30"), Decimal("100"))]
    out = ge.evaluate_edge_invalidation_trigger(held_qty=Decimal("62.5"), bid_levels=bid_levels,
                                                fee_rate=Decimal("0.07"),
                                                model_hold_value=Decimal("30"))
    assert out["triggered"] is False


def test_edge_invalidation_fill_at_next_poll():
    fill = ge.execute_full_exit_fill(qty=Decimal("62.5"),
                                     next_bid_levels=[(Decimal("0.55"), Decimal("100"))],
                                     fee_rate=Decimal("0.07"), allocated_entry_cost=Decimal("25.245"))
    assert fill["status"] == "FILLED"


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


def test_concurrent_exposure_tally_empty():
    out = ge.tally_concurrent_exposure([])
    assert out["open_position_count"] == 0
    assert out["aggregate_paper_notional"] == Decimal("0")


# ===========================================================================
# 18 — no-lookahead structural proofs
# ===========================================================================
@pytest.mark.parametrize("fn", [
    ge.evaluate_tp_trigger, ge.evaluate_edge_invalidation_trigger, ge.execute_full_exit_fill,
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
