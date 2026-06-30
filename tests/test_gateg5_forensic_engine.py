"""
Gate G.5 — Pure deterministic unit tests for the offline forensic engine.

These exercise pure functions in isolation:
  * NO runner launch, NO detached process, NO watcher, NO active wait.
  * NO API polling, NO DB live root, NO Live S1 access, NO wallet/capital.
  * Offline only. Repo code untouched.

Run with:  pytest -q tests/test_gateg5_forensic_engine.py
"""

import re
from decimal import Decimal

import pytest

from analysis.forensic import gateg5_forensic_engine as engine


# ---------------------------------------------------------------------------
# helpers to build fixture rows
# ---------------------------------------------------------------------------
def make_mark(seq, ts_mark_ms, status, vwap, ladder="[]", executable=0,
              liquidity="THIN_FILL", knowable_ts=None):
    return engine.Mark(
        signal_id="sig-1",
        seq=seq,
        ts_mark_ms=ts_mark_ms,
        knowable_ts=ts_mark_ms if knowable_ts is None else knowable_ts,
        bid_ladder_json=ladder,
        exit_mark_status=status,
        exit_mark_vwap=vwap,
        executable_flag=executable,
        liquidity_class=liquidity,
        tte_s=60,
    )


def make_signal(**over):
    base = dict(
        signal_id="sig-1",
        ts_signal_ms=1000,
        knowable_ts=1000,
        asset="BTC",
        side="NO",
        condition_id="cond-1",
        token_id="tok-1",
        outcome_index=1,
        outcome_label="Down",
        market_end_ts=2000,
        intended_stake="25",
        exec_ask_vwap="0.50",
        exec_fill_qty_avail="50",
        decision_cost_buffer="999",
        realized_entry_cost="0.50",
        realized_fee_cost="0.25",
        fill_decision=engine.FillDecision.FILLED_ACTIVE,
        edge_bucket="0.15_0.25",
        tte_bucket="3m_7m",
    )
    base.update(over)
    return engine.Signal(**base)


# ===========================================================================
# 1. Sentinel math
# ===========================================================================
def test_exit_mark_value_executable_returns_decimal():
    v = engine.exit_mark_value(engine.ExitMarkStatus.COMPUTED_EXECUTABLE, "0.42")
    assert isinstance(v, Decimal)
    assert v == Decimal("0.42")


def test_exit_mark_value_blocked_raises():
    with pytest.raises(engine.SentinelMathError):
        engine.exit_mark_value(
            engine.ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY,
            engine.ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY,
        )


def test_exit_mark_value_stale_raises():
    with pytest.raises(engine.SentinelMathError):
        engine.exit_mark_value(
            engine.ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE,
            engine.ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE,
        )


@pytest.mark.parametrize("sentinel", [
    "NOT_COMPUTED_BLOCKED_NO_LIQUIDITY",
    "NOT_COMPUTED_STALE_QUOTE",
])
def test_D_refuses_sentinels(sentinel):
    with pytest.raises(engine.SentinelMathError):
        engine.D(sentinel)


# ===========================================================================
# 2. terminal_conservative empty / stale
# ===========================================================================
def test_terminal_no_marks_blocked():
    r = engine.terminal_conservative([], market_end_ts=2000,
                                 held_shares=Decimal("50"), cost=Decimal("25"))
    assert r.status == engine.TerminalStatus.BLOCKED_NEVER_CLEAN
    assert r.filled_shares == Decimal("0")
    assert r.residual_shares == Decimal("50")
    assert r.realized_value == Decimal("0")
    assert r.residual_value == Decimal("0")


def test_terminal_blocked_no_liquidity():
    m = make_mark(1, 1500, engine.ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY,
                  engine.ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY)
    r = engine.terminal_conservative([m], 2000, Decimal("50"), Decimal("25"))
    assert r.status == engine.TerminalStatus.BLOCKED_NEVER_CLEAN
    assert r.filled_shares == Decimal("0")
    assert r.residual_shares == Decimal("50")
    assert r.realized_value == Decimal("0")
    assert r.residual_value == Decimal("0")


def test_terminal_stale_quote():
    m = make_mark(1, 1500, engine.ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE,
                  engine.ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE)
    r = engine.terminal_conservative([m], 2000, Decimal("50"), Decimal("25"))
    assert r.status == engine.TerminalStatus.BLOCKED_NEVER_CLEAN
    assert r.residual_shares == Decimal("50")
    assert r.realized_value == Decimal("0")
    assert r.residual_value == Decimal("0")


# ===========================================================================
# 3. terminal_conservative partial FAK
# ===========================================================================
def test_terminal_partial_fak():
    # ladder can absorb only 30 of 50 held shares at 0.40
    m = make_mark(1, 1500, engine.ExitMarkStatus.COMPUTED_THIN_PARTIAL, "0.40",
                  ladder='[["0.40","30"]]', executable=0)
    r = engine.terminal_conservative([m], 2000, Decimal("50"), Decimal("25"))
    assert r.status == engine.TerminalStatus.END_TS_FORCED
    assert r.filled_shares == Decimal("30")
    assert r.residual_shares == Decimal("20")
    assert r.realized_value == Decimal("30") * Decimal("0.40")  # 12.00
    assert r.residual_value == Decimal("0")


# ===========================================================================
# 4. terminal_conservative time selection (never reuse earlier favorable mark)
# ===========================================================================
def test_terminal_time_selection_ignores_earlier_favorable():
    earlier_good = make_mark(1, 1100, engine.ExitMarkStatus.COMPUTED_EXECUTABLE, "0.95",
                             ladder='[["0.95","100"]]', executable=1,
                             liquidity="DEEP_EXECUTABLE")
    later_blocked = make_mark(2, 1900, engine.ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY,
                              engine.ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY)
    r = engine.terminal_conservative([earlier_good, later_blocked], 2000,
                                 Decimal("50"), Decimal("25"))
    # must pick the LATER (blocked) mark, NOT the earlier favorable one
    assert r.status == engine.TerminalStatus.BLOCKED_NEVER_CLEAN
    assert r.filled_shares == Decimal("0")
    assert r.realized_value == Decimal("0")


# ===========================================================================
# 5. Holdout deterministic routing
# ===========================================================================
def test_holdout_deterministic_repeatable():
    a = engine.deterministic_holdout_decision("sig-xyz", "BTC|NO|0.15_0.25|3m_7m",
                                          Decimal("0.2"), 0, 100)
    b = engine.deterministic_holdout_decision("sig-xyz", "BTC|NO|0.15_0.25|3m_7m",
                                          Decimal("0.2"), 0, 100)
    assert a == b  # no wall-clock / no random dependency


def test_holdout_cap_reached():
    # holdout_fraction=1.0 forces diversion; cap reached -> cap-reached sentinel
    d = engine.deterministic_holdout_decision("sig-cap", "S", Decimal("1.0"),
                                          stratum_admitted_count=5, stratum_cap=5)
    assert d == engine.FillDecision.UNFILLED_SHADOW_CAP_REACHED


def test_holdout_filled_active_when_bucket_ge_fraction():
    # holdout_fraction=0 => bucket(>=0) always >= fraction => FILLED_ACTIVE
    d = engine.deterministic_holdout_decision("sig-any", "S", Decimal("0"), 0, 100)
    assert d == engine.FillDecision.FILLED_ACTIVE


def test_holdout_valid_shadow_when_diverted_under_cap():
    d = engine.deterministic_holdout_decision("sig-h", "S", Decimal("1.0"),
                                          stratum_admitted_count=0, stratum_cap=5)
    assert d == engine.FillDecision.VALID_HOLDOUT_SHADOW


# ===========================================================================
# 6. Active executable criteria
# ===========================================================================
def _crit(**over):
    base = dict(depth_ok=True, entry_edge="0.20", quote_age_ms=500, sellback_ok=True)
    base.update(over)
    return base


def test_criteria_all_pass():
    assert engine.passes_active_executable_criteria(_crit()) is True


def test_criteria_depth_fail():
    assert engine.passes_active_executable_criteria(_crit(depth_ok=False)) is False


def test_criteria_edge_below_floor():
    assert engine.passes_active_executable_criteria(_crit(entry_edge="0.10")) is False


def test_criteria_stale_quote():
    assert engine.passes_active_executable_criteria(_crit(quote_age_ms=5000)) is False


def test_criteria_sellback_fail():
    assert engine.passes_active_executable_criteria(_crit(sellback_ok=False)) is False


# ===========================================================================
# 7. Cost accounting
# ===========================================================================
def test_realized_cost_excludes_buffer():
    sig = make_signal()  # buffer=999, stake=25, entry=0.50, fee=0.25
    assert engine.realized_cost(sig) == Decimal("25.75")  # buffer NOT included


def test_assert_buffer_not_in_pnl_raises():
    with pytest.raises(engine.CostAccountingError):
        engine.assert_buffer_not_in_pnl({"decision_cost_buffer": "1.00", "stake": "25"})


def test_assert_buffer_not_in_pnl_ok():
    # no raise when buffer absent
    engine.assert_buffer_not_in_pnl({"realized_entry_cost": "0.50"})


# ===========================================================================
# 8. Schema checks
# ===========================================================================
def test_no_standalone_real_columns():
    for ddl in engine.ALL_SCHEMAS:
        assert not re.search(r"\b(REAL|FLOAT|DOUBLE)\b", ddl, re.IGNORECASE)


def test_signal_log_has_binding_fields():
    for col in ("outcome_index", "outcome_label", "token_id", "condition_id"):
        assert col in engine.SCHEMA_SIGNAL_LOG


def test_mark_path_has_exit_mark_status():
    assert "exit_mark_status" in engine.SCHEMA_MARK_PATH


def test_resolution_has_finalized_and_binding_assert():
    assert "resolution_finalized" in engine.SCHEMA_RESOLUTION
    assert "token_outcome_assert" in engine.SCHEMA_RESOLUTION


# ===========================================================================
# 9. Replay safety helpers
# ===========================================================================
def test_exit_ev_sl_triggers():
    # vwap 0.30 * 50 = 15 proceeds vs cost 25.75 -> ~-41% <= -30 => STOP_LOSS
    sig = make_signal()
    m = make_mark(1, 1500, engine.ExitMarkStatus.COMPUTED_EXECUTABLE, "0.30",
                  ladder='[["0.30","100"]]', executable=1,
                  liquidity="DEEP_EXECUTABLE")
    out = engine.exit_ev(sig, [m])
    assert out["outcome"] == "STOP_LOSS_30"


def test_exit_ev_tp_triggers():
    # vwap 0.80 * 50 = 40 proceeds vs cost 25.75 -> ~+55% >= +50 => TAKE_PROFIT
    sig = make_signal()
    m = make_mark(1, 1500, engine.ExitMarkStatus.COMPUTED_EXECUTABLE, "0.80",
                  ladder='[["0.80","100"]]', executable=1,
                  liquidity="DEEP_EXECUTABLE")
    out = engine.exit_ev(sig, [m])
    assert out["outcome"] == "TAKE_PROFIT_50"


def test_exit_ev_sl_precedence_structural():
    # SL is checked before TP in source; a single scalar VWAP mark cannot satisfy
    # both barriers simultaneously, so SL-first ordering enforces worst-case-first.
    src = open(engine.__file__).read()
    sl_idx = src.index("if pnl <= SL_PCT")
    tp_idx = src.index("if pnl >= TP_PCT")
    assert sl_idx < tp_idx


def test_assert_no_lookahead_raises():
    with pytest.raises(engine.LookaheadError):
        engine.assert_no_lookahead(field_knowable_ts=100, decision_tick=50)


def test_assert_no_lookahead_ok():
    engine.assert_no_lookahead(field_knowable_ts=40, decision_tick=50)  # no raise


def test_token_outcome_binding_mismatch_raises():
    meta = {
        "condition_id": "cond-1",
        "clobTokenIds": ["tokA", "tokB"],
        "outcomes": ["Up", "Down"],
    }
    with pytest.raises(engine.ForensicError) as ei:
        engine.assert_token_outcome_binding("cond-1", "WRONG_TOKEN", 1, "Down", meta)
    assert "FORENSIC_FAIL_TOKEN_OUTCOME_BINDING" in str(ei.value)


def test_token_outcome_binding_pass():
    meta = {
        "condition_id": "cond-1",
        "clobTokenIds": ["tokA", "tokB"],
        "outcomes": ["Up", "Down"],
    }
    assert engine.assert_token_outcome_binding("cond-1", "tokB", 1, "Down", meta) == "PASS"
