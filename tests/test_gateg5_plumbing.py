"""
Gate G.5 — Live→Offline plumbing mock integration + hardening tests (NO RUNNER).

  * Static mocked payloads only. NO API polling, NO wall clock in normalization.
  * Mock SQLite under /tmp only. NO live DB, NO Live S1, NO wallet/capital.

Run with:  pytest -q tests/test_gateg5_plumbing.py
"""

import shutil
import sqlite3
import tempfile
import time
from decimal import Decimal

import pytest

from analysis.forensic import gateg5_plumbing as plumb

engine = plumb.engine
ExitMarkStatus = engine.ExitMarkStatus
FillDecision = engine.FillDecision

CAPTURE_TS_MS = 1_000_000_000_000
CAPTURE_SEC = CAPTURE_TS_MS // 1000


# ---------------------------------------------------------------------------
# mock payload builders
# ---------------------------------------------------------------------------
def market_valid(**over):
    base = dict(
        asset="BTC", side="NO", condition_id="cond-1", token_id="tokDown",
        outcome_index=1, outcome_label="Down", slug="btc-updown-15m-1000000000",
        market_end_ts=CAPTURE_SEC + 600,
        clobTokenIds=["tokUp", "tokDown"], outcomes=["Up", "Down"],
    )
    base.update(over)
    return base


def book_valid(**over):
    base = dict(
        asks=[["0.50", "200"], ["0.51", "200"]],   # whole-book notional 202
        bids=[["0.48", "500"]],
        quote_ts_ms=CAPTURE_TS_MS - 100,
    )
    base.update(over)
    return base


def context_valid(**over):
    base = dict(
        reference_feed_ts=CAPTURE_TS_MS - 300, intended_stake="25",
        decision_cost_buffer="999", realized_entry_cost="0", realized_fee_cost="0",
        fair_yes="0.40", fair_yes_sigma="0.05", fair_model_version="g4b-frozen",
        strike="60000", reference_price="60010", underlying_spot_price="60010",
        entry_edge="0.20",
    )
    base.update(over)
    return base


def mark_snapshot(ts_mark_ms, bids, quote_ts_ms, **over):
    base = dict(
        ts_mark_ms=ts_mark_ms, bids=bids, quote_ts_ms=quote_ts_ms,
        spot_price="60010", spot_age_ms=120, fair_yes_t="0.41", fair_yes_sigma_t="0.05",
    )
    base.update(over)
    return base


@pytest.fixture
def mock_db():
    d = tempfile.mkdtemp(prefix="gateg5-plumbing-", dir="/tmp")
    conn = sqlite3.connect(f"{d}/mock.sqlite3")
    plumb.init_mock_db(conn)
    yield conn
    conn.close()
    shutil.rmtree(d, ignore_errors=True)


def _ns(market=None, book=None, ctx=None):
    return plumb.normalize_signal(market or market_valid(), book or book_valid(),
                                  ctx or context_valid(), capture_ts_ms=CAPTURE_TS_MS)


# ===========================================================================
# 1. valid / executable case
# ===========================================================================
def test_valid_signal_exact_fields():
    s = _ns().signal
    assert (s.asset, s.side, s.condition_id, s.token_id) == ("BTC", "NO", "cond-1", "tokDown")
    assert s.outcome_index == 1 and s.outcome_label == "Down"
    assert s.market_end_ts == CAPTURE_SEC + 600
    assert s.fill_decision == FillDecision.FILLED_ACTIVE
    assert Decimal(s.exec_ask_vwap) == Decimal("0.50")
    assert Decimal(s.exec_fill_qty_avail) == Decimal("50")


def test_reference_age_from_injected_not_wallclock():
    assert _ns().signal.reference_age_ms == 300
    ns2 = _ns(ctx=context_valid(reference_feed_ts=CAPTURE_TS_MS - 1500))
    assert ns2.signal.reference_age_ms == 1500


def test_normalizer_does_not_call_wall_clock(monkeypatch):
    monkeypatch.setattr(time, "time", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("wall clock used")))
    assert _ns().signal.reference_age_ms == 300


def test_total_book_ask_notional_diagnostic_decimal_safe():
    ns = _ns()
    assert Decimal(ns.signal.ask_depth_avail) == Decimal("202")   # whole-book notional
    depth = plumb.total_book_ask_notional(ns.row["ask_ladder_json"])
    assert isinstance(depth, Decimal) and depth == Decimal("202")
    assert Decimal(ns.signal.ask_spread_pct) == Decimal("0.02") / Decimal("0.49")


def test_valid_mark_executable():
    ns = _ns()
    nm = plumb.normalize_mark(
        mark_snapshot(CAPTURE_TS_MS + 30_000, [["0.55", "100"]],
                      quote_ts_ms=CAPTURE_TS_MS + 29_900), ns.signal, seq=1)
    assert nm.mark.exit_mark_status == ExitMarkStatus.COMPUTED_EXECUTABLE
    assert nm.mark.executable_flag == 1 and nm.mark.liquidity_class == "DEEP_EXECUTABLE"
    assert Decimal(nm.mark.exit_mark_vwap) == Decimal("0.55")


# ===========================================================================
# 1b. stake-clamped ask walk: partial mid-level fill + insufficient depth
# ===========================================================================
def test_stake_clamped_walk_stops_mid_level():
    # asks: 0.50x10 (notional 5) then 0.60x100; stake 25 -> 5 fills L0, 20 left
    # 20 USD / 0.60 = 33.333... shares partial on L1 (mid-level stop)
    levels = plumb.parse_ask_ladder('[["0.50","10"],["0.60","100"]]')
    fill = plumb.walk_ask_ladder_for_stake(levels, Decimal("25"))
    assert fill.depth_sufficient is True
    assert fill.fill_cost == Decimal("25")
    assert fill.residual_unfilled_stake == Decimal("0")
    assert fill.filled_qty == Decimal("10") + Decimal("20") / Decimal("0.60")
    assert fill.exec_ask_vwap == Decimal("25") / fill.filled_qty


def test_insufficient_ask_depth_marks_fill_decision():
    # only 0.50x10 = 5 USD of depth vs 25 intended -> depth_fail, residual 20
    ns = _ns(book=book_valid(asks=[["0.50", "10"]]))
    assert ns.ask_fill.depth_sufficient is False
    assert ns.ask_fill.residual_unfilled_stake == Decimal("20")
    assert ns.signal.fill_decision == FillDecision.UNFILLED_ENTRY_DEPTH_FAIL


# ===========================================================================
# 2. thin / stale / blocked marks (sentinel-safe)
# ===========================================================================
def test_thin_mark_partial():
    ns = _ns()
    nm = plumb.normalize_mark(
        mark_snapshot(CAPTURE_TS_MS + 10_000, [["0.48", "20"]],
                      quote_ts_ms=CAPTURE_TS_MS + 9_900), ns.signal, seq=1)
    assert nm.mark.exit_mark_status == ExitMarkStatus.COMPUTED_THIN_PARTIAL
    assert nm.mark.executable_flag == 0 and nm.mark.liquidity_class == "THIN_FILL"
    assert Decimal(nm.mark.exit_mark_vwap) == Decimal("0.48")


def test_stale_mark_sentinel():
    ns = _ns()
    nm = plumb.normalize_mark(
        mark_snapshot(CAPTURE_TS_MS + 60_000, [["0.48", "500"]],
                      quote_ts_ms=CAPTURE_TS_MS + 55_000), ns.signal, seq=1)
    assert nm.mark.exit_mark_status == ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE
    assert nm.mark.exit_mark_vwap == "NOT_COMPUTED_STALE_QUOTE"
    with pytest.raises(engine.SentinelMathError):
        engine.D(nm.mark.exit_mark_vwap)


def test_blocked_empty_book_sentinel():
    ns = _ns()
    nm = plumb.normalize_mark(
        mark_snapshot(CAPTURE_TS_MS + 90_000, [], quote_ts_ms=CAPTURE_TS_MS + 89_900),
        ns.signal, seq=1)
    assert nm.mark.exit_mark_status == ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY
    assert nm.mark.exit_mark_vwap == "NOT_COMPUTED_BLOCKED_NO_LIQUIDITY"
    assert nm.mark.liquidity_class == "BLOCKED_NO_LIQUIDITY"
    with pytest.raises(engine.SentinelMathError):
        engine.D(nm.mark.exit_mark_vwap)


# ===========================================================================
# 3. structural / Decimal anomalies — fail closed
# ===========================================================================
def test_token_outcome_mismatch_raises():
    with pytest.raises(engine.ForensicError) as ei:
        _ns(market=market_valid(token_id="tokUp"))
    assert "FORENSIC_FAIL_TOKEN_OUTCOME_BINDING" in str(ei.value)


def test_crossed_locked_book_rejected():
    # best_bid 0.60 >= best_ask 0.55
    with pytest.raises(plumb.CrossedBookError):
        _ns(book=book_valid(asks=[["0.55", "100"]], bids=[["0.60", "100"]]))


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity", None, "abc"])
def test_malformed_price_rejected(bad):
    with pytest.raises(plumb.MalformedLevelError):
        _ns(book=book_valid(asks=[[bad, "100"]]))


@pytest.mark.parametrize("bad", ["NaN", "Infinity", None, "abc"])
def test_malformed_size_rejected(bad):
    with pytest.raises(plumb.MalformedLevelError):
        _ns(book=book_valid(asks=[["0.50", bad]]))


@pytest.mark.parametrize("price", ["0", "-0.1", "1.5", "2"])
def test_invalid_price_bounds_rejected(price):
    with pytest.raises(plumb.MalformedLevelError):
        _ns(book=book_valid(asks=[[price, "100"]]))


@pytest.mark.parametrize("size", ["0", "-5"])
def test_nonpositive_size_rejected(size):
    with pytest.raises(plumb.MalformedLevelError):
        _ns(book=book_valid(asks=[["0.50", size]]))


def test_missing_token_id_smooth_reject():
    m = market_valid()
    del m["token_id"]
    with pytest.raises(plumb.IdentityError):
        _ns(market=m)


def test_missing_market_end_ts_smooth_reject():
    m = market_valid()
    del m["market_end_ts"]
    with pytest.raises(plumb.IdentityError):
        _ns(market=m)


def test_ambiguous_outcome_mapping_rejected():
    # token_id appears at two positions -> not uniquely placed
    with pytest.raises(plumb.IdentityError):
        _ns(market=market_valid(clobTokenIds=["tokDown", "tokDown"],
                                outcomes=["Up", "Down"]))


def test_outcomes_length_mismatch_rejected():
    with pytest.raises(plumb.IdentityError):
        _ns(market=market_valid(outcomes=["Up"]))   # len 1 vs clobTokenIds len 2


def test_quote_after_market_end_rejected():
    # quote_ts_ms after market_end_ts (ms) -> timestamp disorder
    with pytest.raises(plumb.TimestampError):
        _ns(book=book_valid(quote_ts_ms=(CAPTURE_SEC + 600) * 1000 + 5000))


def test_negative_reference_age_rejected():
    with pytest.raises(plumb.TimestampError):
        _ns(ctx=context_valid(reference_feed_ts=CAPTURE_TS_MS + 500))


def test_duplicate_unsorted_ladder_normalizes_deterministically():
    # unsorted + duplicate 0.50 -> merged (150) and sorted ascending
    ns = _ns(book=book_valid(asks=[["0.51", "100"], ["0.50", "100"], ["0.50", "50"]]))
    assert ns.row["ask_ladder_json"] == '[["0.50","150"],["0.51","100"]]'
    # whole-book notional = 0.50*150 + 0.51*100 = 126
    assert plumb.total_book_ask_notional(ns.row["ask_ladder_json"]) == Decimal("126")


# ===========================================================================
# 4. DB writer boundary
# ===========================================================================
def test_db_writer_commits_signal_and_marks(mock_db):
    conn = mock_db
    ns = _ns()
    sig_hash = plumb.write_signal(conn, ns, prev_hash="GENESIS")
    prev = "GENESIS"
    for i, snap in enumerate([
        mark_snapshot(CAPTURE_TS_MS + 10_000, [["0.55", "100"]], quote_ts_ms=CAPTURE_TS_MS + 9_900),
        mark_snapshot(CAPTURE_TS_MS + 60_000, [], quote_ts_ms=CAPTURE_TS_MS + 59_900),
    ], start=1):
        prev = plumb.write_mark(conn, plumb.normalize_mark(snap, ns.signal, seq=i), prev_hash=prev)
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM signal_log").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM mark_path").fetchone()[0] == 2
    assert isinstance(sig_hash, str) and len(sig_hash) == 64
    blocked = conn.execute(
        "SELECT exit_mark_vwap FROM mark_path WHERE exit_mark_status=?",
        (ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY,)).fetchone()[0]
    assert blocked == "NOT_COMPUTED_BLOCKED_NO_LIQUIDITY"


def _write_condition(conn, condition_id, token_id, outcome_index, outcome_label,
                     n_marks, prev_seed="GENESIS"):
    """Write one signal + n marks for a condition on its OWN chain; return last hash + signal_id."""
    m = market_valid(condition_id=condition_id, token_id=token_id,
                     outcome_index=outcome_index, outcome_label=outcome_label)
    ns = _ns(market=m)
    plumb.write_signal(conn, ns, prev_hash=prev_seed)
    prev = "GENESIS"
    for i in range(1, n_marks + 1):
        snap = mark_snapshot(CAPTURE_TS_MS + i * 10_000, [["0.50", "100"]],
                             quote_ts_ms=CAPTURE_TS_MS + i * 10_000 - 100)
        prev = plumb.write_mark(conn, plumb.normalize_mark(snap, ns.signal, seq=i), prev_hash=prev)
    return prev, ns.signal.signal_id


def _marks_for(conn, signal_id):
    rows = conn.execute(
        f"SELECT {','.join(plumb._MARK_COLS)} FROM mark_path WHERE signal_id=? ORDER BY seq",
        (signal_id,)).fetchall()
    return [dict(zip(plumb._MARK_COLS, r)) for r in rows]


def test_multi_insert_hash_chain_continuity(mock_db):
    conn = mock_db
    ids = []
    # 3 distinct signals (distinct condition_ids), each with a multi-row mark path
    specs = [("condA", "tokDown", 1, "Down"), ("condB", "tokUp", 0, "Up"),
             ("condC", "tokDown", 1, "Down")]
    for cid, tok, idx, lbl in specs:
        _, sid = _write_condition(conn, cid, tok, idx, lbl, n_marks=3)
        ids.append(sid)
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM signal_log").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM mark_path").fetchone()[0] == 9
    for sid in ids:
        assert engine.verify_hash_chain(_marks_for(conn, sid)) is True


def test_hash_chain_tamper_detected(mock_db):
    conn = mock_db
    _, sid = _write_condition(conn, "condT", "tokDown", 1, "Down", n_marks=3)
    conn.commit()
    # mutate a MIDDLE row's payload directly in the DB
    conn.execute("UPDATE mark_path SET exit_mark_vwap=? WHERE signal_id=? AND seq=2",
                 ("0.99999", sid))
    conn.commit()
    assert engine.verify_hash_chain(_marks_for(conn, sid)) is False


def test_multi_condition_isolation(mock_db):
    conn = mock_db
    _, sid_a = _write_condition(conn, "condA", "tokDown", 1, "Down", n_marks=2)
    _, sid_b = _write_condition(conn, "condB", "tokUp", 0, "Up", n_marks=3)
    conn.commit()
    # each condition's marks form an independent valid chain; counts isolated
    assert len(_marks_for(conn, sid_a)) == 2
    assert len(_marks_for(conn, sid_b)) == 3
    assert engine.verify_hash_chain(_marks_for(conn, sid_a)) is True
    assert engine.verify_hash_chain(_marks_for(conn, sid_b)) is True
    # tampering one condition does NOT break the other (no cross-contamination)
    conn.execute("UPDATE mark_path SET exit_mark_vwap=? WHERE signal_id=? AND seq=1",
                 ("0.123", sid_a))
    conn.commit()
    assert engine.verify_hash_chain(_marks_for(conn, sid_a)) is False
    assert engine.verify_hash_chain(_marks_for(conn, sid_b)) is True


# ===========================================================================
# 5. causality + schema integrity
# ===========================================================================
def test_no_lookahead_fields():
    ns = _ns()
    assert ns.signal.knowable_ts <= ns.signal.ts_signal_ms
    nm = plumb.normalize_mark(
        mark_snapshot(CAPTURE_TS_MS + 10_000, [["0.50", "100"]],
                      quote_ts_ms=CAPTURE_TS_MS + 9_900), ns.signal, seq=1)
    assert nm.mark.knowable_ts <= nm.mark.ts_mark_ms


def test_schema_has_no_real_columns(mock_db):
    conn = mock_db
    engine.assert_no_real_columns(conn)
    for table in ("signal_log", "mark_path", "resolution"):
        for row in conn.execute(f"PRAGMA table_info({table})"):
            ct = (row[2] or "").upper()
            assert "REAL" not in ct and "FLOAT" not in ct and "DOUBLE" not in ct
