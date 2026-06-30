"""
Gate G.5 — Offline synthetic dual-replay fixture tests (NO RUNNER).

Pure, deterministic, in-memory fixtures exercising the dual-replay engine:
  * NO runner launch, NO GATEG5_ARM, NO detached process, NO watcher.
  * NO API polling, NO live DB root, NO Live S1 access, NO wallet/capital.
  * Offline only. Repo code untouched. Read-only import of the forensic engine.

Run with:  pytest -q tests/test_gateg5_offline_replay.py
"""

import inspect
from decimal import Decimal

import pytest

from analysis.forensic import gateg5_forensic_engine as engine


# ---------------------------------------------------------------------------
# fixture builders (cost held at 25 by zeroing realized costs => clean math)
# ---------------------------------------------------------------------------
def make_signal(signal_id, condition_id, fill_decision, **over):
    base = dict(
        signal_id=signal_id,
        ts_signal_ms=1000,
        knowable_ts=1000,
        asset="BTC",
        side="NO",                 # NO/Down wins when resolved_yes == '0'
        condition_id=condition_id,
        token_id="tok-1",
        outcome_index=1,
        outcome_label="Down",
        market_end_ts=5000,
        intended_stake="25",
        exec_ask_vwap="0.50",
        exec_fill_qty_avail="50",  # 50 shares
        decision_cost_buffer="999",  # must NEVER enter PnL
        realized_entry_cost="0",
        realized_fee_cost="0",     # => cost == 25
        fill_decision=fill_decision,
        edge_bucket="0.15_0.25",
        tte_bucket="3m_7m",
    )
    base.update(over)
    return engine.Signal(**base)


def mk(signal_id, seq, ts, status, vwap, ladder='[]', execf=0, knowable=None,
       elapsed=None):
    return engine.Mark(
        signal_id=signal_id,
        seq=seq,
        ts_mark_ms=ts,
        knowable_ts=ts if knowable is None else knowable,
        bid_ladder_json=ladder,
        exit_mark_status=status,
        exit_mark_vwap=vwap,
        executable_flag=execf,
        liquidity_class="DEEP_EXECUTABLE" if execf else "THIN_FILL",
        tte_s=60,
        elapsed_ms_since_signal=(ts - 1000) if elapsed is None else elapsed,
    )


def clean(signal_id, seq, ts, vwap, elapsed=None):
    """A clean executable mark with a deep ladder at `vwap`."""
    return mk(signal_id, seq, ts, engine.ExitMarkStatus.COMPUTED_EXECUTABLE,
              vwap, ladder=f'[["{vwap}","100"]]', execf=1, elapsed=elapsed)


def finalized_resolution(resolved_yes):
    return {
        "resolved_yes": resolved_yes,
        "resolution_finalized": 1,
        "resolution_source": "clob.polymarket.com/markets/<cid>",
        "resolution_fetch_ts": 6000,
    }


def pnl(d):
    return Decimal(d["pnl_pct"])


# ===========================================================================
# A. FILLED_ACTIVE_TP — path reaches TP50
# ===========================================================================
def test_A_filled_active_tp():
    sig = make_signal("A", "condA", engine.FillDecision.FILLED_ACTIVE)
    marks = [clean("A", 1, 1500, "0.55"),   # +10%, no trigger
             clean("A", 2, 2500, "0.80")]   # 40 proceeds vs 25 => +60% => TP
    out = engine.exit_ev(sig, marks)
    assert out["outcome"] == "TAKE_PROFIT_50"
    assert pnl(out) >= Decimal("50")


# ===========================================================================
# B. FILLED_ACTIVE_SL — path reaches SL30
# ===========================================================================
def test_B_filled_active_sl():
    sig = make_signal("B", "condB", engine.FillDecision.FILLED_ACTIVE)
    marks = [clean("B", 1, 1500, "0.45"),   # -10%, no trigger
             clean("B", 2, 2500, "0.30")]   # 15 proceeds vs 25 => -40% => SL
    out = engine.exit_ev(sig, marks)
    assert out["outcome"] == "STOP_LOSS_30"
    assert pnl(out) <= Decimal("-30")


# ===========================================================================
# C. VALID_HOLDOUT_SHADOW_WIN_RESOLUTION — hold_ev positive
# ===========================================================================
def test_C_holdout_win_resolution():
    sig = make_signal("C", "condC", engine.FillDecision.VALID_HOLDOUT_SHADOW)
    res = finalized_resolution("0")  # NO/Down wins
    out = engine.hold_ev(sig, res)
    assert out["outcome"] == "WON"
    assert pnl(out) > Decimal("0")


# ===========================================================================
# D. VALID_HOLDOUT_SHADOW_DRAWDOWN_THEN_WIN — hold wins, exit bleeds
# ===========================================================================
def test_D_holdout_drawdown_then_win():
    sig = make_signal("D", "condD", engine.FillDecision.VALID_HOLDOUT_SHADOW)
    # exit path: severe drawdown hits SL30 before market_end_ts
    marks = [clean("D", 1, 1500, "0.45"),
             clean("D", 2, 2500, "0.28")]   # -44% => SL
    res = finalized_resolution("0")          # but resolution WINS

    hold = engine.hold_ev(sig, res)
    exit_ = engine.exit_ev(sig, marks)

    assert hold["outcome"] == "WON"
    assert pnl(hold) > Decimal("0")
    assert exit_["outcome"] == "STOP_LOSS_30"
    assert pnl(exit_) < Decimal("0")

    exit_bleed = pnl(hold) - pnl(exit_)
    assert exit_bleed > Decimal("0")  # engine distinguishes terminal-win from path-exit-loss


# ===========================================================================
# E. BLOCKED_NO_LIQUIDITY_TERMINAL — conservative terminal accounting
# ===========================================================================
def test_E_blocked_terminal_conservative():
    sig = make_signal("E", "condE", engine.FillDecision.FILLED_ACTIVE)
    # never cleanly exits: thin/unexecutable then blocked at the end
    marks = [mk("E", 1, 1500, engine.ExitMarkStatus.COMPUTED_THIN_PARTIAL, "0.50",
                ladder='[["0.50","5"]]', execf=0),
             mk("E", 2, 4800, engine.ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY,
                engine.ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY)]
    out = engine.exit_ev(sig, marks)
    assert out["outcome"] in (engine.TerminalStatus.BLOCKED_NEVER_CLEAN,
                              engine.TerminalStatus.END_TS_FORCED)
    assert out["outcome"] == engine.TerminalStatus.BLOCKED_NEVER_CLEAN
    assert Decimal(out["residual_value"]) == Decimal("0")
    assert Decimal(out["residual_shares"]) == Decimal("50")
    # conservative: pnl is a near-total loss (proceeds 0 vs cost 25)
    assert pnl(out) <= Decimal("-99")


# ===========================================================================
# 3. Dual-replay aggregate assertions (four arms + exit_bleed + cap bias)
# ===========================================================================
def _build_universe():
    """A filled signal and a comparable valid-holdout signal for bias contrast."""
    filled = make_signal("F", "condF", engine.FillDecision.FILLED_ACTIVE)
    holdout = make_signal("H", "condH", engine.FillDecision.VALID_HOLDOUT_SHADOW)
    # filled: exit hits SL but resolution wins  => exit_bleed positive
    marks_by_sig = {
        "F": [clean("F", 1, 2500, "0.30")],   # SL
        "H": [clean("H", 1, 2500, "0.30")],   # SL
    }
    resolutions = {
        "condF": finalized_resolution("0"),   # win
        "condH": finalized_resolution("0"),   # win
    }
    return [filled, holdout], marks_by_sig, resolutions


def test_four_arms_dispatch():
    signals, marks_by_sig, resolutions = _build_universe()
    arms = engine.run_four_arms(signals, marks_by_sig, resolutions)
    assert len(arms["hold_ev_FILLED"]) == 1
    assert len(arms["exit_ev_FILLED"]) == 1
    assert len(arms["hold_ev_HOLDOUT"]) == 1
    assert len(arms["exit_ev_HOLDOUT"]) == 1


def test_exit_bleed_filled():
    signals, marks_by_sig, resolutions = _build_universe()
    arms = engine.run_four_arms(signals, marks_by_sig, resolutions)
    hold = pnl(arms["hold_ev_FILLED"][0])
    exit_ = pnl(arms["exit_ev_FILLED"][0])
    exit_bleed = hold - exit_
    assert hold > Decimal("0")          # hold wins
    assert exit_ < Decimal("0")         # exit stopped out
    assert exit_bleed > Decimal("0")    # exit_ev = hold_ev(FILLED) - exit_ev(FILLED)


def test_cap_selection_bias_now_implemented():
    # diag_cap_selection_bias() is now implemented (was a stub previously).
    signals, marks_by_sig, resolutions = _build_universe()
    arms = engine.run_four_arms(signals, marks_by_sig, resolutions)
    bias = engine.diag_cap_selection_bias(arms)
    # both cohorts win => hold_ev equal => cap_selection_bias == 0
    assert bias["cap_selection_bias"] == Decimal("0")
    assert isinstance(bias["path_cap_selection_bias"], Decimal)


# ===========================================================================
# Aggregate EV arms + delta diagnostics + dual-axis classification
# ===========================================================================
def test_aggregate_arms_means_and_n():
    signals, marks_by_sig, resolutions = _build_universe()
    arms = engine.run_four_arms(signals, marks_by_sig, resolutions)
    agg = engine.aggregate_arms(arms)
    # FILLED hold wins (+100), exit SL (-40); each arm has exactly 1 numeric sample
    assert agg["n"]["hold_ev_FILLED"] == 1
    assert agg["n"]["exit_ev_FILLED"] == 1
    assert agg["hold_ev_FILLED"] == Decimal("100")
    assert agg["exit_ev_FILLED"] == Decimal("-40")


def test_delta_diagnostics():
    signals, marks_by_sig, resolutions = _build_universe()
    arms = engine.run_four_arms(signals, marks_by_sig, resolutions)
    deltas = engine.delta_diagnostics(arms)
    assert deltas["exit_bleed"] == Decimal("140")     # 100 - (-40)
    assert deltas["toxicity"] == Decimal("0")          # filled hold == holdout hold
    assert deltas["path_toxicity"] == Decimal("0")     # filled exit == holdout exit


def test_dual_axis_schema_pass_with_insufficient_n_coexist():
    signals, marks_by_sig, resolutions = _build_universe()
    arms = engine.run_four_arms(signals, marks_by_sig, resolutions)
    summary = engine.build_dual_axis_summary(signals, arms)
    # Axis 1: integrity sound -> SCHEMA_PASS
    assert summary.axis1 == engine.Forensic.SCHEMA_PASS
    # Axis 2: only BTC + 2 windows -> INSUFFICIENT_EFFECTIVE_N (coexists)
    assert summary.axis2 == engine.Forensic.INSUFFICIENT_EFFECTIVE_N


def test_effective_n_warning_logic():
    signals, _, _ = _build_universe()
    eff = engine.diag_effective_n(signals)
    assert eff["unique_underlying_assets"] == 1   # BTC only
    assert eff["statistical_independence_warning"] is True
    assert eff["effective_n_ok"] is False


# ===========================================================================
# HOLDOUT_DRAWDOWN_THEN_LOSS — must not double-penalize
# ===========================================================================
def test_holdout_drawdown_then_loss_no_double_penalty():
    sig = make_signal("DL", "condDL", engine.FillDecision.VALID_HOLDOUT_SHADOW)
    marks_by_sig = {"DL": [clean("DL", 1, 2500, "0.28")]}   # SL drawdown
    resolutions = {"condDL": finalized_resolution("1")}     # NO side LOSES (yes=1)
    arms = engine.run_four_arms([sig], marks_by_sig, resolutions)

    hold = arms["hold_ev_HOLDOUT"][0]
    exit_ = arms["exit_ev_HOLDOUT"][0]
    assert hold["outcome"] == "LOST"
    assert exit_["outcome"] == "STOP_LOSS_30"

    agg = engine.aggregate_arms(arms)
    # the single holdout signal appears exactly once per arm, never summed together
    assert agg["n"]["hold_ev_HOLDOUT"] == 1
    assert agg["n"]["exit_ev_HOLDOUT"] == 1
    # hold loss is -100% (payoff 0), counted once; not added to the exit -44%
    assert agg["hold_ev_HOLDOUT"] == Decimal("-100")
    assert agg["exit_ev_HOLDOUT"] < Decimal("0")


# ===========================================================================
# STALE_QUOTE_TERMINAL — aggregation must not numeric-math sentinel strings
# ===========================================================================
def test_stale_quote_terminal_aggregation_sentinel_safe():
    sig = make_signal("SQ", "condSQ", engine.FillDecision.FILLED_ACTIVE)
    marks = [mk("SQ", 1, 1500, engine.ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE,
                engine.ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE),
             mk("SQ", 2, 4800, engine.ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE,
                engine.ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE)]
    arms = engine.run_four_arms([sig], {"SQ": marks},
                            {"condSQ": finalized_resolution("0")})
    exit_row = arms["exit_ev_FILLED"][0]
    assert exit_row["outcome"] == engine.TerminalStatus.BLOCKED_NEVER_CLEAN
    assert Decimal(exit_row["residual_value"]) == Decimal("0")
    # aggregation reads only numeric pnl_pct; sentinel strings never coerced
    agg = engine.aggregate_arms(arms)
    assert agg["exit_ev_FILLED"] <= Decimal("-99")   # conservative total loss, numeric


# ===========================================================================
# Causality: exit replay cannot read resolution; resolution join is condition_id
# ===========================================================================
def test_exit_ev_signature_has_no_resolution_param():
    params = list(inspect.signature(engine.exit_ev).parameters)
    assert "resolution" not in params
    assert params == ["sig", "marks"]   # only signal + mark_path


def test_exit_ev_runs_without_any_resolution():
    # exit_ev given only marks (no resolution object exists) still produces a result
    sig = make_signal("NR", "condNR", engine.FillDecision.FILLED_ACTIVE)
    out = engine.exit_ev(sig, [clean("NR", 1, 2500, "0.80")])
    assert out["arm"] == "exit_ev"


def test_exit_ev_lookahead_guard_raises():
    sig = make_signal("LA", "condLA", engine.FillDecision.FILLED_ACTIVE)
    bad = clean("LA", 1, 1500, "0.80")
    bad.knowable_ts = bad.ts_mark_ms + 100   # field knowable AFTER the tick
    with pytest.raises(engine.LookaheadError):
        engine.exit_ev(sig, [bad])


def test_resolution_join_is_condition_id_only():
    # resolutions keyed by condition_id => hold_ev resolves; keyed by slug => miss
    sig = make_signal("J", "condJ", engine.FillDecision.FILLED_ACTIVE)
    by_condition = {"condJ": finalized_resolution("0")}
    by_slug = {"some-slug": finalized_resolution("0")}

    hit = engine.run_four_arms([sig], {"J": []}, by_condition)
    miss = engine.run_four_arms([sig], {"J": []}, by_slug)
    assert hit["hold_ev_FILLED"][0]["outcome"] == "WON"
    assert miss["hold_ev_FILLED"][0]["outcome"] == "EXCLUDED_UNFINALIZED"


# ===========================================================================
# Toxic Flow Trap — high edge, adverse first-30s drift, eventual SL30
# ===========================================================================
def test_toxic_flow_trap():
    tx = make_signal("TX", "condTX", engine.FillDecision.FILLED_ACTIVE,
                     entry_edge="0.25", fair_yes="0.70", reference_age_ms=200,
                     tte_s=600, ask_spread_pct="0.01", ask_depth_avail="100",
                     market_end_ts=100000)
    # one clean mark 20s post-entry: price collapsed 0.50 -> 0.30 (drift -40%, SL)
    marks_by_sig = {"TX": [clean("TX", 1, 21000, "0.30", elapsed=20000)]}
    resolutions = {"condTX": finalized_resolution("1")}  # NO side LOSES at resolution
    arms = engine.run_four_arms([tx], marks_by_sig, resolutions)

    assert arms["exit_ev_FILLED"][0]["outcome"] == "STOP_LOSS_30"
    assert arms["hold_ev_FILLED"][0]["outcome"] == "LOST"

    drift = engine.diag_first_30s_mark_drift([tx], marks_by_sig)
    gap = engine.diag_edge_realization_gap([tx], arms)
    # adverse immediate post-entry move exposed
    assert drift["per_signal"]["TX"] == Decimal("-0.4")
    # modeled edge 0.25 totally failed to realize (hold -100% => gap 1.25 > 0)
    assert gap["per_signal"]["TX"] == Decimal("1.25")
    assert gap["per_signal"]["TX"] > Decimal("0")


# ===========================================================================
# Stale Oracle Mirage — stale ref feed + thin depth isolates bad cohort
# ===========================================================================
def test_stale_oracle_mirage():
    stale = make_signal("ST", "condST", engine.FillDecision.FILLED_ACTIVE,
                        entry_edge="0.30", fair_yes="0.65", reference_age_ms=6000,
                        tte_s=600, ask_spread_pct="0.10", ask_depth_avail="0.5")
    fresh = make_signal("FR", "condFR", engine.FillDecision.FILLED_ACTIVE,
                        entry_edge="0.18", fair_yes="0.55", reference_age_ms=100,
                        tte_s=600, ask_spread_pct="0.01", ask_depth_avail="100")
    resolutions = {
        "condST": finalized_resolution("1"),  # NO loses -> -100%
        "condFR": finalized_resolution("0"),  # NO wins  -> +100%
    }
    arms = engine.run_four_arms([stale, fresh], {"ST": [], "FR": []}, resolutions)

    ref = engine.diag_reference_age_buckets([stale, fresh], arms)
    sdt = engine.diag_spread_depth_tte_buckets([stale, fresh], arms)

    # reference-age bucket isolates the stale cohort as the loser
    assert ref["ge_5000ms"]["mean_hold_pnl_pct"] == Decimal("-100")
    assert ref["lt_500ms"]["mean_hold_pnl_pct"] == Decimal("100")
    assert ref["ge_5000ms"]["mean_hold_pnl_pct"] < ref["lt_500ms"]["mean_hold_pnl_pct"]

    # spread/depth/tte bucket isolates the wide-spread / thin-depth loser
    stale_key = "wide_ge5pct|thin_lt10|7m_12m"
    fresh_key = "tight_lt2pct|deep_ge50|7m_12m"
    assert sdt[stale_key]["mean_hold_pnl_pct"] == Decimal("-100")
    assert sdt[fresh_key]["mean_hold_pnl_pct"] == Decimal("100")


# ===========================================================================
# Telemetry isolation — diagnostics must not alter routing/execution
# ===========================================================================
def test_diagnostics_do_not_alter_execution():
    signals, marks_by_sig, resolutions = _build_universe()
    arms_before = engine.run_four_arms(signals, marks_by_sig, resolutions)
    outcomes_before = {k: [r.get("outcome") for r in v] for k, v in arms_before.items()}

    # run the full diagnostics suite (pure reads)
    engine.diag_calibration_curve(signals, resolutions)
    engine.diag_modeled_edge_vs_hold_pnl(signals, arms_before)
    engine.diag_edge_realization_gap(signals, arms_before)
    engine.diag_first_30s_mark_drift(signals, marks_by_sig)
    engine.diag_reference_age_buckets(signals, arms_before)
    engine.diag_spread_depth_tte_buckets(signals, arms_before)
    engine.diag_cap_selection_bias(arms_before)

    arms_after = engine.run_four_arms(signals, marks_by_sig, resolutions)
    outcomes_after = {k: [r.get("outcome") for r in v] for k, v in arms_after.items()}

    assert outcomes_before == outcomes_after          # routing/execution unchanged
    assert engine.TP_PCT == Decimal("50")                 # TP threshold untouched
    assert engine.SL_PCT == Decimal("-30")                # SL threshold untouched
