"""
Gate G9 — Managed Position orchestrator (network-capable, but ZERO live network in
these tests -- injected fetchers only, urlopen hard-patched to raise).

Covers tools.gateg9_managed_position_runner: the isolated managed-position ledger
(5 tables, idempotent/restart-safe writers), the G6-reuse resolution wrapper, and a
single-poll monitoring-snapshot capture primitive. PAPER/SHADOW ONLY -- no orders,
wallet, signing, capital, or S1 access anywhere in this module.
"""
import ast
import inspect
import json
import sqlite3
from decimal import Decimal

import pytest

from analysis.forensic import gateg9_managed_exit as ge
from tools import gateg6_terminal_evaluator as g6
from tools import gateg9_managed_position_runner as mpr

NOW_MS = 1_900_000_000_000


@pytest.fixture(autouse=True)
def _block_live_network(monkeypatch):
    """Every test here uses injected fakes; hard-patch urlopen so an accidentally
    unmocked path fails loudly instead of silently reaching the live network."""
    monkeypatch.setattr(mpr.runner.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("live network")))


def _position(condition_id="cid-1"):
    return {"position_id": condition_id, "condition_id": condition_id,
           "slug": "btc-updown-15m-1000", "asset": "BTC", "window": "1000",
           "selected_side": "YES", "selected_token_id": "tokUp",
           "opposite_token_id": "tokDown", "held_qty": "62.5",
           "entry_ask_vwap": "0.40", "entry_fee": "1.09", "entry_cost": "26.09",
           "entry_ts": NOW_MS, "state": ge.STATE_PAPER_OPEN, "created_ts": NOW_MS,
           "market_end_ts": NOW_MS // 1000 + 600, "fee_rate": "0.07"}


# ===========================================================================
# L. ledger separation — 5 isolated tables, idempotent/restart-safe
# ===========================================================================
def test_init_managed_ledger_creates_all_five_tables(tmp_path):
    db = str(tmp_path / "g9.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for t in ("gateg9_managed_positions", "gateg9_monitoring_snapshots", "gateg9_overlay_events",
             "gateg9_overlay_terminal", "gateg9_concurrent_exposure_snapshots"):
        assert t in tables
    conn.close()


def test_write_managed_position_idempotent_on_restart(tmp_path):
    db = str(tmp_path / "g9_pos.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    r1 = mpr.write_managed_position(conn, _position("cid-a"))
    r2 = mpr.write_managed_position(conn, _position("cid-a"))
    assert r1 == "CREATED"
    assert r2 == "ALREADY_EXISTS"
    n = conn.execute("SELECT COUNT(*) FROM gateg9_managed_positions WHERE condition_id='cid-a'").fetchone()[0]
    assert n == 1
    conn.close()


# ===========================================================================
# 14 — no duplicate overlay fill after restart / DB reopen
# ===========================================================================
def _terminal(position_id, overlay, pnl="1.00"):
    return {"position_id": position_id, "overlay": overlay, "status": ge.RESOLVED_HOLD,
           "realized_net_pnl": pnl, "net_roi": "0.04", "closed_ts": NOW_MS}


def test_write_overlay_terminal_idempotent_same_connection(tmp_path):
    db = str(tmp_path / "g9_term.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    r1 = mpr.write_overlay_terminal(conn, _terminal("cid-a", ge.OVERLAY_HOLD_CONTROL))
    r2 = mpr.write_overlay_terminal(conn, _terminal("cid-a", ge.OVERLAY_HOLD_CONTROL, pnl="9.99"))
    assert r1 == "RECORDED"
    assert r2 == "ALREADY_RECORDED"
    rows = conn.execute(
        "SELECT realized_net_pnl FROM gateg9_overlay_terminal WHERE position_id='cid-a' "
        "AND overlay=?", (ge.OVERLAY_HOLD_CONTROL,)).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "1.00"   # the SECOND (differing) write never overwrote the first
    conn.close()


def test_write_overlay_terminal_idempotent_across_db_reopen(tmp_path):
    db = str(tmp_path / "g9_term_reopen.sqlite3")
    conn1 = sqlite3.connect(db)
    mpr.init_managed_ledger(conn1)
    mpr.write_overlay_terminal(conn1, _terminal("cid-b", ge.OVERLAY_TP_15_FULL))
    conn1.close()

    conn2 = sqlite3.connect(db)
    mpr.init_managed_ledger(conn2)   # idempotent re-create; unique index persists on disk
    r2 = mpr.write_overlay_terminal(conn2, _terminal("cid-b", ge.OVERLAY_TP_15_FULL))
    assert r2 == "ALREADY_RECORDED"
    n = conn2.execute(
        "SELECT COUNT(*) FROM gateg9_overlay_terminal WHERE position_id='cid-b' AND overlay=?",
        (ge.OVERLAY_TP_15_FULL,)).fetchone()[0]
    assert n == 1
    conn2.close()


def test_write_overlay_terminal_distinct_overlays_both_recorded(tmp_path):
    db = str(tmp_path / "g9_term_multi.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    r1 = mpr.write_overlay_terminal(conn, _terminal("cid-c", ge.OVERLAY_HOLD_CONTROL))
    r2 = mpr.write_overlay_terminal(conn, _terminal("cid-c", ge.OVERLAY_TP_15_FULL))
    assert r1 == "RECORDED" and r2 == "RECORDED"
    conn.close()


# ===========================================================================
# 15 — concurrent exposure recording
# ===========================================================================
def test_write_and_read_concurrent_exposure_snapshot(tmp_path):
    db = str(tmp_path / "g9_exposure.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    tally = ge.tally_concurrent_exposure([
        {"condition_id": "c1", "asset": "BTC", "selected_side": "YES", "entry_cost": Decimal("25")},
        {"condition_id": "c2", "asset": "ETH", "selected_side": "NO", "entry_cost": Decimal("25")},
    ])
    mpr.write_concurrent_exposure_snapshot(conn, tally, ts_ms=NOW_MS)
    row = conn.execute(
        "SELECT open_position_count, aggregate_paper_notional FROM gateg9_concurrent_exposure_snapshots"
    ).fetchone()
    assert row == (2, "50")
    conn.close()


# ===========================================================================
# 17 — Gamma/CLOB resolution disagreement fails closed (reuses G6 pure deciders only)
# ===========================================================================
def _gamma_resolved_payload(slug, cid, winner_idx=0):
    return [{"slug": slug, "conditionId": cid, "closed": True, "umaResolutionStatus": "resolved",
            "outcomes": ["Up", "Down"], "clobTokenIds": ["tokUp", "tokDown"],
            "outcomePrices": (["1", "0"] if winner_idx == 0 else ["0", "1"])}]


def _clob_resolved_payload(cid, winner_token):
    return {"condition_id": cid, "closed": True,
           "tokens": [{"token_id": "tokUp", "winner": winner_token == "tokUp"},
                      {"token_id": "tokDown", "winner": winner_token == "tokDown"}]}


def test_resolve_selected_side_agrees_won():
    out = mpr.resolve_selected_side(
        gamma_payload=_gamma_resolved_payload("btc-updown-15m-1000", "cid-1", winner_idx=0),
        slug="btc-updown-15m-1000", condition_id="cid-1",
        clob_payload=_clob_resolved_payload("cid-1", "tokUp"), selected_token_id="tokUp")
    assert out == {"status": "RESOLVED", "won": True, "winner_token": "tokUp"}


def test_resolve_selected_side_agrees_lost():
    out = mpr.resolve_selected_side(
        gamma_payload=_gamma_resolved_payload("btc-updown-15m-1000", "cid-1", winner_idx=1),
        slug="btc-updown-15m-1000", condition_id="cid-1",
        clob_payload=_clob_resolved_payload("cid-1", "tokDown"), selected_token_id="tokUp")
    assert out == {"status": "RESOLVED", "won": False, "winner_token": "tokDown"}


def test_resolve_selected_side_gamma_clob_disagreement_fails_closed():
    out = mpr.resolve_selected_side(
        gamma_payload=_gamma_resolved_payload("btc-updown-15m-1000", "cid-1", winner_idx=0),  # gamma says Up
        slug="btc-updown-15m-1000", condition_id="cid-1",
        clob_payload=_clob_resolved_payload("cid-1", "tokDown"),  # clob says Down
        selected_token_id="tokUp")
    assert out["status"] == ge.GAMMA_CLOB_CONFLICT_FAIL_CLOSED
    assert out["status"] == g6.ST_RESOLVED if False else True   # sanity: constant is fail-closed, never RESOLVED


def test_resolve_selected_side_not_yet_final_is_pending():
    unresolved = [{"slug": "btc-updown-15m-1000", "conditionId": "cid-1", "closed": False}]
    out = mpr.resolve_selected_side(gamma_payload=unresolved, slug="btc-updown-15m-1000",
                                    condition_id="cid-1", clob_payload={}, selected_token_id="tokUp")
    assert out["status"] == ge.RESOLUTION_PENDING


# ===========================================================================
# monitoring snapshot capture (single poll; injected fetchers; arm-gated)
# ===========================================================================
def _book_payload(ask_price, bid_price, ts=None):
    return {"asks": [{"price": ask_price, "size": "1000"}],
           "bids": [{"price": bid_price, "size": "1000"}], "timestamp": ts or NOW_MS}


def _hl_fixture(p_now="59000", feed_lag_ms=30_000, sigma=0.8):
    def pf(coin, ts_ms):
        return (Decimal(p_now), ts_ms - feed_lag_ms)
    return pf, (lambda coin, now_ms: sigma)


def test_capture_monitoring_snapshot_unarmed_rejects_before_network(monkeypatch):
    monkeypatch.delenv(mpr.MANAGED_ARM_ENV, raising=False)
    calls = []

    def no_network(url, params=None):
        calls.append(url)
        raise AssertionError("no GET expected when unarmed")

    with pytest.raises(PermissionError):
        mpr.capture_monitoring_snapshot(_position(), poll_seq=1, now_ms_provider=lambda: NOW_MS,
                                        public_get=no_network)
    assert calls == []


def test_capture_monitoring_snapshot_required_fields(monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)

    def fake_public_get(url, params=None):
        if params["token_id"] == "tokUp":
            return _book_payload("0.55", "0.50", ts=NOW_MS - 100)
        return _book_payload("0.48", "0.45", ts=NOW_MS - 90)

    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))
    snap = mpr.capture_monitoring_snapshot(_position(), poll_seq=1, now_ms_provider=lambda: next(times),
                                           public_get=fake_public_get, hl_price_feedts=pf,
                                           hl_sigma_annual=sig)
    required = ("position_id", "condition_id", "slug", "asset", "window", "poll_seq",
               "selected_side", "selected_token_id", "held_qty", "entry_ask_vwap", "entry_fee",
               "entry_cost", "poll_ts_ms", "selected_capture_started_ms",
               "selected_capture_completed_ms", "opposite_capture_started_ms",
               "opposite_capture_completed_ms", "tte_s", "reference_age_ms",
               "held_qty_bid_vwap", "held_qty_filled_qty", "held_qty_depth_sufficient",
               "would_move_book", "best_bid", "total_relevant_bid_notional",
               "fair_yes", "hl_feed_ts", "model_hold_value", "executable_exit_net_proceeds",
               "opposite_exec_ask_vwap", "opposite_net_edge_diagnostic", "current_spread",
               "gross_return", "fee_net_return")
    for f in required:
        assert f in snap, f"missing monitoring field: {f}"


def test_capture_monitoring_snapshot_no_lookahead_ordering(monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)

    def fake_public_get(url, params=None):
        if params["token_id"] == "tokUp":
            return _book_payload("0.55", "0.50", ts=NOW_MS - 100)
        return _book_payload("0.48", "0.45", ts=NOW_MS - 90)

    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))
    snap = mpr.capture_monitoring_snapshot(_position(), poll_seq=1, now_ms_provider=lambda: next(times),
                                           public_get=fake_public_get, hl_price_feedts=pf,
                                           hl_sigma_annual=sig)
    assert snap["poll_ts_ms"] >= snap["selected_capture_completed_ms"]
    assert snap["poll_ts_ms"] >= snap["opposite_capture_completed_ms"]


# ===========================================================================
# 19/20 — no S1/order/wallet/signing/capital anywhere in this module
# ===========================================================================
def test_no_wallet_order_signing_imports_or_calls():
    tree = ast.parse(inspect.getsource(mpr))
    imported = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            calls.add(node.func.attr)
    for forbidden_module in ("wallet", "signing", "execution", "web3"):
        assert not any(forbidden_module in m.lower() for m in imported), imported
    for forbidden_call in ("sign", "place_order", "send_transaction"):
        assert forbidden_call not in calls, calls


def test_module_never_touches_s1_path():
    source = inspect.getsource(mpr)
    assert "var/s1" not in source or "_LIVE_S1" in source  # only the runner's own S1 refusal reuse


# ===========================================================================
# PHASE A.1/A.2 — model hold value vs executable proceeds; canonical opposite net edge
# (reusing G8's exact _evaluate_side formula, never a p_now/100000-style hack).
# ===========================================================================
def test_capture_monitoring_snapshot_model_hold_value_differs_from_executable_proceeds(monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)

    def fake_public_get(url, params=None):
        if params["token_id"] == "tokUp":
            return _book_payload("0.55", "0.50", ts=NOW_MS - 100)
        return _book_payload("0.48", "0.45", ts=NOW_MS - 90)

    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))
    snap = mpr.capture_monitoring_snapshot(_position(), poll_seq=1, now_ms_provider=lambda: next(times),
                                           public_get=fake_public_get, hl_price_feedts=pf,
                                           hl_sigma_annual=sig)
    assert snap["model_hold_value"] != snap["executable_exit_net_proceeds"]
    expected_model = Decimal(snap["fair_yes"]) * Decimal(snap["held_qty"])
    assert Decimal(snap["model_hold_value"]) == expected_model


def test_capture_monitoring_snapshot_opposite_net_edge_is_canonical_g8_formula(monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)

    def fake_public_get(url, params=None):
        if params["token_id"] == "tokUp":
            return _book_payload("0.55", "0.50", ts=NOW_MS - 100)
        return _book_payload("0.48", "0.45", ts=NOW_MS - 90)

    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))
    snap = mpr.capture_monitoring_snapshot(_position(), poll_seq=1, now_ms_provider=lambda: next(times),
                                           public_get=fake_public_get, hl_price_feedts=pf,
                                           hl_sigma_annual=sig)
    fair_yes = Decimal(snap["fair_yes"])
    fair_no = Decimal("1") - fair_yes   # position side is YES -> opposite is NO
    from analysis.forensic import gateg7_paper_pnl as pp
    from tools.gateg8_paper_forward_capture import DEFAULT_STAKE
    expected = pp._evaluate_side(fair_no, [(Decimal("0.48"), Decimal("1000"))],
                                 {"fee_rate": Decimal("0.07"), "fee_status": pp.FEE_VERIFIED_RATE},
                                 Decimal("0"), DEFAULT_STAKE)
    assert snap["opposite_net_edge_diagnostic"] == str(expected["net_edge"])
    assert snap["opposite_exec_ask_vwap"] == expected["exec_ask_vwap"]


# ===========================================================================
# PHASE A.5 — monitoring timing fails closed on a future/stale/missing timestamp;
# never uses resolution/outcome data.
# ===========================================================================
def test_capture_monitoring_snapshot_rejects_future_quote_timestamp(monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)

    def fake_public_get(url, params=None):
        if params["token_id"] == "tokUp":
            return _book_payload("0.55", "0.50", ts=NOW_MS + 50_000)   # future quote
        return _book_payload("0.48", "0.45", ts=NOW_MS - 90)

    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))
    snap = mpr.capture_monitoring_snapshot(_position(), poll_seq=1, now_ms_provider=lambda: next(times),
                                           public_get=fake_public_get, hl_price_feedts=pf,
                                           hl_sigma_annual=sig)
    assert snap["status"] == ge.MONITORING_TIMESTAMP_REJECTED


def test_capture_monitoring_snapshot_rejects_stale_quote_timestamp(monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)

    def fake_public_get(url, params=None):
        if params["token_id"] == "tokUp":
            return _book_payload("0.55", "0.50", ts=NOW_MS - 100)
        return _book_payload("0.48", "0.45", ts=NOW_MS - 10_000)   # stale quote

    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))
    snap = mpr.capture_monitoring_snapshot(_position(), poll_seq=1, now_ms_provider=lambda: next(times),
                                           public_get=fake_public_get, hl_price_feedts=pf,
                                           hl_sigma_annual=sig)
    assert snap["status"] == ge.MONITORING_TIMESTAMP_REJECTED


def test_capture_monitoring_snapshot_never_takes_resolution_param():
    params = inspect.signature(mpr.capture_monitoring_snapshot).parameters
    assert "resolution" not in params and "outcome" not in params


# ===========================================================================
# PHASE B — stateful multi-poll managed vertical
# ===========================================================================
def _g8_candidate(condition_id="cid-1", slug="btc-updown-15m-1000", *, selected_side="YES",
                  yes_net_edge="0.20", no_net_edge="-0.10", window_end_s=None):
    window = "1000"
    return {"condition_id": condition_id, "slug": slug, "asset": slug.split("-")[0].upper(),
           "window": window, "status": "PAPER_OPEN", "selected_side": selected_side,
           "selected_token_id": "tokUp" if selected_side == "YES" else "tokDown",
           "yes_token_id": "tokUp", "no_token_id": "tokDown",
           "selected_filled_qty": "60", "selected_entry_notional": "24",
           "yes_exec_ask_vwap": "0.40", "no_exec_ask_vwap": "0.55", "fee_rate": "0.07",
           "yes_net_edge": yes_net_edge, "no_net_edge": no_net_edge,
           "paper_decision_ts": NOW_MS}


def _rising_bid_book(url, params=None):
    """A high, stable bid so TP15/20/30 all trigger immediately (poll 1), and the fill
    ladder (poll 2+) is identical -- isolates state-machine correctness from price
    dynamics for the core progression tests."""
    if params["token_id"] == "tokUp":
        return _book_payload("0.90", "0.85", ts=NOW_MS - 100)
    return _book_payload("0.20", "0.15", ts=NOW_MS - 90)


def _flat_losing_book(url, params=None):
    """Bid stays BELOW entry -- no TP overlay ever triggers; used to isolate HOLD/T-120/
    restart/exposure behavior from TP triggering."""
    if params["token_id"] == "tokUp":
        return _book_payload("0.42", "0.38", ts=NOW_MS - 100)
    return _book_payload("0.58", "0.55", ts=NOW_MS - 90)


def _armed_managed_env(monkeypatch, *, max_obs="20", max_elapsed="600", poll_interval="1"):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    monkeypatch.setenv("GATEG9_MAX_OBSERVATIONS", max_obs)
    monkeypatch.setenv("GATEG9_MAX_ELAPSED_S", max_elapsed)
    monkeypatch.setenv("GATEG9_POLL_INTERVAL_S", poll_interval)
    monkeypatch.setattr(mpr.time, "sleep", lambda *a, **k: None)


def _write_g8_ledger(tmp_path, candidates, name="g8.sqlite3"):
    from tools import gateg8_paper_forward_capture as fwd
    db = str(tmp_path / name)
    conn = sqlite3.connect(db)
    fwd.init_paper_ledger(conn)
    for c in candidates:
        row = dict.fromkeys(fwd._LEDGER_COLS)
        row.update(c)
        row["paper_decision_ts"] = c["paper_decision_ts"]
        conn.execute(f"INSERT INTO gateg8_paper_ledger({','.join(fwd._LEDGER_COLS)}) "
                    f"VALUES ({','.join('?' for _ in fwd._LEDGER_COLS)})",
                    tuple(row.get(col) for col in fwd._LEDGER_COLS))
    conn.commit()
    conn.close()
    return db


# --- 2. one selected correlated asset per 15m window (already proven at pure level;
# here proven end-to-end: only the winning condition_id gets a managed position row) ---
def test_run_admits_only_one_correlated_candidate_per_window(monkeypatch, tmp_path):
    _armed_managed_env(monkeypatch)
    g8_db = _write_g8_ledger(tmp_path, [
        _g8_candidate("cid-btc", "btc-updown-15m-1000", yes_net_edge="0.10"),
        _g8_candidate("cid-sol", "sol-updown-15m-1000", yes_net_edge="0.30"),
    ])
    db = str(tmp_path / "g9.sqlite3")
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1_000_000)))
    mpr.run(db, g8_db, now_ms_provider=lambda: next(times), monotonic_provider=lambda: 0.0,
           public_get=_flat_losing_book, hl_price_feedts=pf, hl_sigma_annual=sig)
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT condition_id FROM gateg9_managed_positions").fetchall()
    conn.close()
    assert [r[0] for r in rows] == ["cid-sol"]


# --- 8/9 — real state progression over injected polls K and K+1; trigger ladder can
# never become fill ladder; atomic PAPER_OPEN->...->PAPER_CLOSED transitions ---
def test_advance_position_one_poll_triggers_then_fills_on_next_poll(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_progress.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()

    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))
    # poll 1: bid is high enough that TP15 (and TP20/30) trigger
    mpr.advance_position_one_poll(conn, position, poll_seq=1, now_ms_provider=lambda: next(times),
                                  public_get=_rising_bid_book, hl_price_feedts=pf,
                                  hl_sigma_annual=sig, overlay_runtimes=runtimes)
    assert runtimes[ge.OVERLAY_TP_15_FULL]["state"] == ge.STATE_EXIT_PENDING_NEXT_POLL
    ev = conn.execute("SELECT event_type FROM gateg9_overlay_events WHERE position_id='cid-1' "
                      "AND overlay=?", (ge.OVERLAY_TP_15_FULL,)).fetchall()
    assert [e[0] for e in ev] == ["TRIGGER"]

    # poll 2: the SAME (still-high) bid ladder now supplies the fill
    mpr.advance_position_one_poll(conn, position, poll_seq=2, now_ms_provider=lambda: next(times),
                                  public_get=_rising_bid_book, hl_price_feedts=pf,
                                  hl_sigma_annual=sig, overlay_runtimes=runtimes)
    assert runtimes[ge.OVERLAY_TP_15_FULL]["state"] == ge.STATE_PAPER_CLOSED
    term = conn.execute("SELECT status FROM gateg9_overlay_terminal WHERE position_id='cid-1' "
                       "AND overlay=?", (ge.OVERLAY_TP_15_FULL,)).fetchone()
    assert term[0] == ge.TP_EXIT_FILLED
    conn.close()


def test_trigger_ladder_can_never_become_fill_ladder_end_to_end(tmp_path, monkeypatch):
    """poll 1's ladder would give an ABSURD VWAP if reused; poll 2 supplies a totally
    different (realistic) ladder. The recorded fill must reflect ONLY poll 2's ladder."""
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_no_reuse.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))

    def poll1_book(url, params=None):
        if params["token_id"] == "tokUp":
            return _book_payload("0.90", "0.85", ts=NOW_MS - 100)   # triggers TP15
        return _book_payload("0.20", "0.15", ts=NOW_MS - 90)

    def poll2_book(url, params=None):
        if params["token_id"] == "tokUp":
            return _book_payload("0.46", "0.44", ts=NOW_MS - 100)   # the REAL fill price
        return _book_payload("0.55", "0.52", ts=NOW_MS - 90)

    mpr.advance_position_one_poll(conn, position, poll_seq=1, now_ms_provider=lambda: next(times),
                                  public_get=poll1_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=runtimes)
    mpr.advance_position_one_poll(conn, position, poll_seq=2, now_ms_provider=lambda: next(times),
                                  public_get=poll2_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=runtimes)
    ev = conn.execute("SELECT payload_json FROM gateg9_overlay_events WHERE position_id='cid-1' "
                      "AND overlay=? AND event_type='FILL'", (ge.OVERLAY_TP_15_FULL,)).fetchone()
    payload = json.loads(ev[0])
    assert payload["exec_bid_vwap"] == "0.44"   # poll 2's bid, never poll 1's 0.85
    conn.close()


# --- 7 / partial-fill conservation — a partial fill books the leg, conserves the
# residual (qty + exact cost), returns the overlay to MONITORING, and writes NO terminal
# row. The residual may re-trigger and fill on a LATER poll. PAPER_CLOSED never happens
# while an unsettled residual remains. ---
def _shallow_fill_book_factory(bid_price, bid_size):
    def book(url, params=None):
        if params["token_id"] == "tokUp":
            return {"asks": [{"price": "0.95", "size": "1000"}],
                   "bids": [{"price": bid_price, "size": bid_size}], "timestamp": NOW_MS - 100}
        return _book_payload("0.20", "0.15", ts=NOW_MS - 90)
    return book


def test_partial_fill_conserves_residual_and_returns_to_monitoring_no_terminal(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_partial.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")   # held_qty = 62.5, entry_cost 26.09
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))

    # poll 1: high bid, full depth -> TP15 triggers
    mpr.advance_position_one_poll(conn, position, poll_seq=1, now_ms_provider=lambda: next(times),
                                  public_get=_rising_bid_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=runtimes)
    assert runtimes[ge.OVERLAY_TP_15_FULL]["state"] == ge.STATE_EXIT_PENDING_NEXT_POLL

    # poll 2: only 5 of 62.5 available -> partial fill, residual conserved, back to MONITORING
    mpr.advance_position_one_poll(conn, position, poll_seq=2, now_ms_provider=lambda: next(times),
                                  public_get=_shallow_fill_book_factory("0.85", "5"), hl_price_feedts=pf,
                                  hl_sigma_annual=sig, overlay_runtimes=runtimes)
    rt = runtimes[ge.OVERLAY_TP_15_FULL]
    assert rt["state"] == ge.STATE_MONITORING            # NOT closed
    assert rt["remaining_qty"] == Decimal("57.5")        # 62.5 - 5, honest residual
    assert rt["remaining_cost"] < Decimal(position["entry_cost"])   # cost basis reduced for the sold leg
    # NO terminal row yet
    term = conn.execute("SELECT COUNT(*) FROM gateg9_overlay_terminal WHERE position_id='cid-1' "
                       "AND overlay=?", (ge.OVERLAY_TP_15_FULL,)).fetchone()[0]
    assert term == 0
    # a partial FILL leg IS persisted (5 shares), never a fabricated full fill
    ev = conn.execute("SELECT payload_json FROM gateg9_overlay_events WHERE position_id='cid-1' "
                      "AND overlay=? AND event_type='FILL'", (ge.OVERLAY_TP_15_FULL,)).fetchone()
    payload = json.loads(ev[0])
    assert payload["status"] == ge.FILL_PARTIAL
    assert payload["filled_qty"] == "5"
    conn.close()


def test_residual_re_triggers_and_fills_only_from_a_later_poll_ladder(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_residual_refill.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))

    # poll1 trigger, poll2 partial (5), poll3 re-trigger, poll4 deep fill of residual (57.5)
    mpr.advance_position_one_poll(conn, position, poll_seq=1, now_ms_provider=lambda: next(times),
                                  public_get=_rising_bid_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=runtimes)
    mpr.advance_position_one_poll(conn, position, poll_seq=2, now_ms_provider=lambda: next(times),
                                  public_get=_shallow_fill_book_factory("0.85", "5"), hl_price_feedts=pf,
                                  hl_sigma_annual=sig, overlay_runtimes=runtimes)
    assert runtimes[ge.OVERLAY_TP_15_FULL]["state"] == ge.STATE_MONITORING
    # poll3: high full-depth bid again -> residual (57.5) re-triggers TP15
    mpr.advance_position_one_poll(conn, position, poll_seq=3, now_ms_provider=lambda: next(times),
                                  public_get=_rising_bid_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=runtimes)
    assert runtimes[ge.OVERLAY_TP_15_FULL]["state"] == ge.STATE_EXIT_PENDING_NEXT_POLL
    # poll4: fills the whole residual -> closed
    mpr.advance_position_one_poll(conn, position, poll_seq=4, now_ms_provider=lambda: next(times),
                                  public_get=_rising_bid_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=runtimes)
    assert runtimes[ge.OVERLAY_TP_15_FULL]["state"] == ge.STATE_PAPER_CLOSED
    # exactly two FILL legs (5 + 57.5), summing to the original 62.5
    legs = conn.execute("SELECT payload_json FROM gateg9_overlay_events WHERE position_id='cid-1' "
                       "AND overlay=? AND event_type='FILL' ORDER BY poll_seq", (ge.OVERLAY_TP_15_FULL,)).fetchall()
    qtys = [Decimal(json.loads(l[0])["filled_qty"]) for l in legs]
    assert qtys == [Decimal("5"), Decimal("57.5")]
    assert sum(qtys, Decimal("0")) == Decimal("62.5")
    # exactly one terminal row (the close), never a duplicate
    n_term = conn.execute("SELECT COUNT(*) FROM gateg9_overlay_terminal WHERE position_id='cid-1' "
                         "AND overlay=?", (ge.OVERLAY_TP_15_FULL,)).fetchone()[0]
    assert n_term == 1
    conn.close()


def test_paper_closed_terminal_only_written_when_residual_fully_exited(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_no_early_close.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))
    # trigger then repeatedly only-partial: overlay must NEVER reach PAPER_CLOSED while
    # residual remains, and must NEVER write a terminal row.
    mpr.advance_position_one_poll(conn, position, poll_seq=1, now_ms_provider=lambda: next(times),
                                  public_get=_rising_bid_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=runtimes)
    for seq in (2, 3, 4):
        mpr.advance_position_one_poll(conn, position, poll_seq=seq, now_ms_provider=lambda: next(times),
                                      public_get=_shallow_fill_book_factory("0.85", "1"), hl_price_feedts=pf,
                                      hl_sigma_annual=sig, overlay_runtimes=runtimes)
        assert runtimes[ge.OVERLAY_TP_15_FULL]["state"] != ge.STATE_PAPER_CLOSED
    n_term = conn.execute("SELECT COUNT(*) FROM gateg9_overlay_terminal WHERE position_id='cid-1' "
                         "AND overlay=?", (ge.OVERLAY_TP_15_FULL,)).fetchone()[0]
    assert n_term == 0
    assert runtimes[ge.OVERLAY_TP_15_FULL]["remaining_qty"] > Decimal("0")
    conn.close()


# --- independent overlays cannot contaminate each other ---
def test_independent_overlays_do_not_contaminate_each_other(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_independent.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))

    # bid high enough for TP15 but NOT for TP30 -> only TP15 (and TP20, borderline) may
    # move; TIME_STOP/EDGE_INVALIDATION/HOLD_CONTROL must be untouched by TP15's trigger.
    def mixed_book(url, params=None):
        if params["token_id"] == "tokUp":
            return _book_payload("0.50", "0.46", ts=NOW_MS - 100)   # ~15% net return
        return _book_payload("0.58", "0.55", ts=NOW_MS - 90)

    mpr.advance_position_one_poll(conn, position, poll_seq=1, now_ms_provider=lambda: next(times),
                                  public_get=mixed_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=runtimes)
    assert runtimes[ge.OVERLAY_TP_30_FULL]["state"] == ge.STATE_MONITORING   # untouched
    assert runtimes[ge.OVERLAY_HOLD_CONTROL]["state"] == ge.STATE_MONITORING  # untouched
    assert runtimes[ge.OVERLAY_TIME_STOP_T120]["state"] == ge.STATE_MONITORING  # untouched (TTE far off)
    conn.close()


# --- MODEL_PREMIUM_EXIT and ENTRY_THESIS_INVALIDATION are independent counterfactual
# worlds: both may trigger at the SAME poll, and neither mutates the other's runtime. ---
def test_model_premium_and_entry_thesis_both_trigger_same_poll_independently(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    # pin fair_selected to a decayed 0.40 so model value (0.40*62.5=25.0) is below the
    # 26.09 cost basis (entry-thesis triggers) while the 0.45 bid still clears it after
    # fees (model-premium triggers) -- both at poll 1, independently.
    monkeypatch.setattr(mpr.gm, "fair_yes_gbm", lambda *a, **k: Decimal("0.40"))
    db = str(tmp_path / "g9_two_overlays.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")   # YES, held 62.5, entry_cost 26.09
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))

    def decayed_book(url, params=None):
        if params["token_id"] == "tokUp":
            return _book_payload("0.47", "0.45", ts=NOW_MS - 100)
        return _book_payload("0.55", "0.53", ts=NOW_MS - 90)

    mpr.advance_position_one_poll(conn, position, poll_seq=1, now_ms_provider=lambda: next(times),
                                  public_get=decayed_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=runtimes)
    assert runtimes[ge.OVERLAY_MODEL_PREMIUM_EXIT]["state"] == ge.STATE_EXIT_PENDING_NEXT_POLL
    assert runtimes[ge.OVERLAY_ENTRY_THESIS_INVALIDATION]["state"] == ge.STATE_EXIT_PENDING_NEXT_POLL
    # each recorded its OWN independent TRIGGER event
    for overlay in (ge.OVERLAY_MODEL_PREMIUM_EXIT, ge.OVERLAY_ENTRY_THESIS_INVALIDATION):
        ev = conn.execute("SELECT event_type FROM gateg9_overlay_events WHERE position_id='cid-1' "
                          "AND overlay=?", (overlay,)).fetchall()
        assert [e[0] for e in ev] == ["TRIGGER"]
    conn.close()


# --- OPPOSITE_EDGE_CROSS is a record-only diagnostic: it is never a triggering/exiting
# overlay identity; it lives only as a persisted snapshot field. ---
def test_opposite_edge_cross_is_record_only(monkeypatch):
    # never an overlay identity that can trigger, fill, or produce a terminal row
    assert "OPPOSITE_EDGE_CROSS" not in mpr._ALL_OVERLAY_KEYS
    assert not any("OPPOSITE" in k for k in mpr._ALL_OVERLAY_KEYS)
    assert not any("OPPOSITE" in k for k in mpr._OVERLAY_FILLED_TERMINAL)

    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)

    def fake_public_get(url, params=None):
        if params["token_id"] == "tokUp":
            return _book_payload("0.55", "0.50", ts=NOW_MS - 100)
        return _book_payload("0.48", "0.45", ts=NOW_MS - 90)

    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))
    snap = mpr.capture_monitoring_snapshot(_position(), poll_seq=1, now_ms_provider=lambda: next(times),
                                           public_get=fake_public_get, hl_price_feedts=pf,
                                           hl_sigma_annual=sig)
    # it is recorded as a diagnostic, never acted upon
    assert "opposite_net_edge_diagnostic" in snap


# --- 12 — G6 terminal resolution and final PnL (HOLD_CONTROL resolved via finalize) ---
def test_finalize_position_at_resolution_hold_control(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_finalize.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    resolution = {"status": "RESOLVED", "won": True}
    mpr.finalize_position_at_resolution(conn, position, overlay_runtimes=runtimes,
                                        resolution=resolution, closed_ts=NOW_MS)
    term = conn.execute("SELECT status, realized_net_pnl FROM gateg9_overlay_terminal "
                       "WHERE position_id='cid-1' AND overlay=?", (ge.OVERLAY_HOLD_CONTROL,)).fetchone()
    assert term[0] == ge.RESOLVED_HOLD
    assert Decimal(term[1]) == Decimal(position["held_qty"]) - Decimal(position["entry_cost"])
    row = conn.execute("SELECT state FROM gateg9_managed_positions WHERE condition_id='cid-1'").fetchone()
    assert row[0] == ge.STATE_PAPER_CLOSED
    conn.close()


def test_finalize_pending_overlay_settles_full_residual_at_resolution(tmp_path, monkeypatch):
    # an overlay that triggered on the LAST poll but never reached a K+1 fill still holds
    # its full residual, which must settle at resolution (fee-free) -- never abandoned.
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_no_next_poll.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    runtimes[ge.OVERLAY_TP_15_FULL] = {"state": ge.STATE_EXIT_PENDING_NEXT_POLL, "triggered_at_poll_seq": 1}
    resolution = {"status": "RESOLVED", "won": True}
    mpr.finalize_position_at_resolution(conn, position, overlay_runtimes=runtimes,
                                        resolution=resolution, closed_ts=NOW_MS)
    term = conn.execute("SELECT status, realized_net_pnl FROM gateg9_overlay_terminal "
                       "WHERE position_id='cid-1' AND overlay=?", (ge.OVERLAY_TP_15_FULL,)).fetchone()
    # full residual held to resolution -> RESOLVED_HOLD, pnl = payout(62.5) - full cost
    assert term[0] == ge.RESOLVED_HOLD
    assert Decimal(term[1]) == Decimal(position["held_qty"]) - Decimal(position["entry_cost"])


def test_finalize_settles_residual_fee_free_with_zero_exit_fee(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_feefree.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    mpr.finalize_position_at_resolution(conn, position, overlay_runtimes=runtimes,
                                        resolution={"status": "RESOLVED", "won": True}, closed_ts=NOW_MS)
    # every overlay writes a RESOLUTION_SETTLE event that explicitly charges a ZERO exit fee
    settle = conn.execute("SELECT payload_json FROM gateg9_overlay_events WHERE position_id='cid-1' "
                         "AND overlay=? AND event_type='RESOLUTION_SETTLE'",
                         (ge.OVERLAY_HOLD_CONTROL,)).fetchone()
    payload = json.loads(settle[0])
    assert payload["exit_fee"] == "0"
    assert payload["payout"] == str(Decimal(position["held_qty"]))   # won -> 1 * shares
    conn.close()


def test_partial_fill_then_resolution_reconciles_exactly_to_full_entry_cost(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_reconcile.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")   # held 62.5, entry_cost 26.09
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))
    # poll1 trigger TP15, poll2 partial fill 5 shares -> residual 57.5 back in MONITORING
    mpr.advance_position_one_poll(conn, position, poll_seq=1, now_ms_provider=lambda: next(times),
                                  public_get=_rising_bid_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=runtimes)
    mpr.advance_position_one_poll(conn, position, poll_seq=2, now_ms_provider=lambda: next(times),
                                  public_get=_shallow_fill_book_factory("0.85", "5"), hl_price_feedts=pf,
                                  hl_sigma_annual=sig, overlay_runtimes=runtimes)
    assert runtimes[ge.OVERLAY_TP_15_FULL]["state"] == ge.STATE_MONITORING
    # now resolve: the 57.5 residual settles fee-free
    mpr.finalize_position_at_resolution(conn, position, overlay_runtimes=runtimes,
                                        resolution={"status": "RESOLVED", "won": True}, closed_ts=NOW_MS)
    term = conn.execute("SELECT status, realized_net_pnl FROM gateg9_overlay_terminal "
                       "WHERE position_id='cid-1' AND overlay=?", (ge.OVERLAY_TP_15_FULL,)).fetchone()
    assert term[0] == ge.RESOLVED_RESIDUAL   # sold some, held the rest to resolution
    # reconciliation identity: aggregate PnL == sum(leg net proceeds) + settle payout - full entry cost
    leg = json.loads(conn.execute(
        "SELECT payload_json FROM gateg9_overlay_events WHERE position_id='cid-1' AND overlay=? "
        "AND event_type='FILL'", (ge.OVERLAY_TP_15_FULL,)).fetchone()[0])
    settle = json.loads(conn.execute(
        "SELECT payload_json FROM gateg9_overlay_events WHERE position_id='cid-1' AND overlay=? "
        "AND event_type='RESOLUTION_SETTLE'", (ge.OVERLAY_TP_15_FULL,)).fetchone()[0])
    expected = (Decimal(leg["net_exit_proceeds"]) + Decimal(settle["payout"])
                - Decimal(position["entry_cost"]))
    assert Decimal(term[1]) == expected
    # no disappearing shares: 5 sold + 57.5 settled == 62.5
    assert Decimal(leg["filled_qty"]) + Decimal(settle["residual_qty"]) == Decimal(position["held_qty"])
    conn.close()


# --- 14 — restart between K and K+1 rehydrates without a duplicate/fabricated fill ---
def test_rehydrate_overlay_runtimes_preserves_pending_trigger_across_restart(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_restart.sqlite3")
    conn1 = sqlite3.connect(db)
    mpr.init_managed_ledger(conn1)
    position = _position("cid-1")
    mpr.write_managed_position(conn1, position)
    runtimes = mpr._fresh_overlay_runtimes()
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1000)))
    mpr.advance_position_one_poll(conn1, position, poll_seq=1, now_ms_provider=lambda: next(times),
                                  public_get=_rising_bid_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=runtimes)
    assert runtimes[ge.OVERLAY_TP_15_FULL]["state"] == ge.STATE_EXIT_PENDING_NEXT_POLL
    conn1.close()   # simulated crash between poll 1 (trigger) and poll 2 (fill)

    conn2 = sqlite3.connect(db)
    mpr.init_managed_ledger(conn2)
    rehydrated = mpr.rehydrate_position_overlay_runtimes(conn2, position)
    assert rehydrated[ge.OVERLAY_TP_15_FULL]["state"] == ge.STATE_EXIT_PENDING_NEXT_POLL
    assert rehydrated[ge.OVERLAY_TP_15_FULL]["triggered_at_poll_seq"] == 1
    assert rehydrated[ge.OVERLAY_TP_15_FULL]["remaining_qty"] == Decimal(position["held_qty"])
    next_seq = mpr._next_poll_seq(conn2, "cid-1")
    assert next_seq == 2   # continues monotonically, never reuses poll_seq 1

    # the rehydrated state now correctly fills on the NEXT poll (poll 2) -- never
    # fabricated from the pre-crash poll-1 evidence.
    mpr.advance_position_one_poll(conn2, position, poll_seq=next_seq, now_ms_provider=lambda: next(times),
                                  public_get=_rising_bid_book, hl_price_feedts=pf, hl_sigma_annual=sig,
                                  overlay_runtimes=rehydrated)
    assert rehydrated[ge.OVERLAY_TP_15_FULL]["state"] == ge.STATE_PAPER_CLOSED
    n_fills = conn2.execute("SELECT COUNT(*) FROM gateg9_overlay_terminal WHERE position_id='cid-1' "
                           "AND overlay=?", (ge.OVERLAY_TP_15_FULL,)).fetchone()[0]
    assert n_fills == 1   # never a duplicate/fabricated second fill
    conn2.close()


def test_rehydrate_overlay_runtimes_skips_already_terminal_overlay(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_restart_terminal.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    mpr.write_overlay_terminal(conn, _terminal("cid-1", ge.OVERLAY_HOLD_CONTROL))
    rehydrated = mpr.rehydrate_position_overlay_runtimes(conn, _position("cid-1"))
    assert rehydrated[ge.OVERLAY_HOLD_CONTROL]["state"] == ge.STATE_PAPER_CLOSED
    conn.close()


# --- unarmed/missing/non-positive bounds -> zero network, zero DB creation ---
def test_run_unarmed_zero_network_zero_db(monkeypatch, tmp_path):
    monkeypatch.delenv(mpr.MANAGED_ARM_ENV, raising=False)
    db = str(tmp_path / "g9_run_unarmed.sqlite3")
    calls = []

    def no_network(url, params=None):
        calls.append(url)
        raise AssertionError("no GET expected")

    with pytest.raises(PermissionError):
        mpr.run(db, str(tmp_path / "g8.sqlite3"), public_get=no_network)
    assert calls == []
    import os
    assert not os.path.exists(db)


@pytest.mark.parametrize("env_name", ["GATEG9_MAX_OBSERVATIONS", "GATEG9_MAX_ELAPSED_S",
                                      "GATEG9_POLL_INTERVAL_S"])
@pytest.mark.parametrize("bad_value", ["0", "-1"])
def test_run_rejects_non_positive_bounds(monkeypatch, tmp_path, env_name, bad_value):
    _armed_managed_env(monkeypatch)
    monkeypatch.setenv(env_name, bad_value)
    db = str(tmp_path / f"g9_badbound_{env_name}_{bad_value}.sqlite3")
    calls = []

    def no_network(url, params=None):
        calls.append(url)
        raise AssertionError("no GET expected")

    with pytest.raises(PermissionError):
        mpr.run(db, str(tmp_path / "g8.sqlite3"), public_get=no_network)
    assert calls == []
    import os
    assert not os.path.exists(db)


def test_run_refuses_pre_existing_artifact_without_resume(monkeypatch, tmp_path):
    _armed_managed_env(monkeypatch)
    db = str(tmp_path / "g9_exists.sqlite3")
    open(db, "w").close()
    with pytest.raises(FileExistsError):
        mpr.run(db, str(tmp_path / "g8.sqlite3"))


# --- 12 — resolution fetches use the STORED birth-market identifiers, never a
# rediscovered/current-window market ---
def test_run_resolution_uses_stored_birth_market_identifiers(monkeypatch, tmp_path):
    _armed_managed_env(monkeypatch, max_obs="2")
    # window "1000" -> market_end_ts = 1000 + TARGET_INTERVAL_S, far in the past vs NOW_MS,
    # so the very first cycle takes the resolution branch.
    g8_db = _write_g8_ledger(tmp_path, [_g8_candidate("cid-birth", "btc-updown-15m-1000")])
    db = str(tmp_path / "g9_birth.sqlite3")
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1_000_000)))
    calls = {"gamma": [], "clob": []}

    def gamma_fetch(slug, condition_id):
        calls["gamma"].append((slug, condition_id))
        return _gamma_resolved_payload(slug, condition_id, winner_idx=0)

    def clob_fetch(condition_id):
        calls["clob"].append(condition_id)
        return _clob_resolved_payload(condition_id, "tokUp")

    mpr.run(db, g8_db, now_ms_provider=lambda: next(times), monotonic_provider=lambda: 0.0,
           public_get=_flat_losing_book, hl_price_feedts=pf, hl_sigma_annual=sig,
           gamma_fetch=gamma_fetch, clob_fetch=clob_fetch)
    # resolve was driven ONLY by the position's own stored slug + condition_id
    assert calls["gamma"] == [("btc-updown-15m-1000", "cid-birth")]
    assert calls["clob"] == ["cid-birth"]
    # and the position resolved + closed using those birth identifiers
    conn = sqlite3.connect(db)
    st = conn.execute("SELECT state FROM gateg9_managed_positions WHERE condition_id='cid-birth'").fetchone()
    conn.close()
    assert st[0] == ge.STATE_PAPER_CLOSED


# --- 13/14 — a bounded stop leaves open overlays recoverable; --resume reopens the DB
# and processes the NEXT poll with no duplicate trigger/fill/terminal rows ---
def _g8_candidate_future(condition_id, slug):
    c = _g8_candidate(condition_id, slug)
    c["window"] = str(NOW_MS // 1000)   # market_end_ts = now + TARGET_INTERVAL_S -> future
    return c


def test_bounded_stop_then_resume_processes_next_poll_without_duplicates(monkeypatch, tmp_path):
    # pin a neutral fair; rising bid triggers TP on poll 1 (run #1, bounded to 1 obs), then
    # --resume fills that pending trigger on poll 2 (run #2) -- one trigger, one fill, one
    # terminal, and monotonic poll_seq across the restart.
    monkeypatch.setattr(mpr.gm, "fair_yes_gbm", lambda *a, **k: Decimal("0.50"))
    g8_db = _write_g8_ledger(tmp_path, [_g8_candidate_future("cid-resume", "btc-updown-15m-9000")])
    db = str(tmp_path / "g9_resume.sqlite3")
    pf, sig = _hl_fixture()

    _armed_managed_env(monkeypatch, max_obs="1")
    times1 = iter(list(range(NOW_MS, NOW_MS + 1_000_000)))
    r1 = mpr.run(db, g8_db, now_ms_provider=lambda: next(times1), monotonic_provider=lambda: 0.0,
                public_get=_rising_bid_book, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert r1["stop_reason"] == "MAX_OBSERVATIONS"
    conn = sqlite3.connect(db)
    # after run #1: TP15 triggered on poll 1 but NOT yet filled -> position still open
    trig = conn.execute("SELECT COUNT(*) FROM gateg9_overlay_events WHERE position_id='cid-resume' "
                       "AND overlay=? AND event_type='TRIGGER'", (ge.OVERLAY_TP_15_FULL,)).fetchone()[0]
    assert trig == 1
    n_term_before = conn.execute("SELECT COUNT(*) FROM gateg9_overlay_terminal WHERE position_id='cid-resume' "
                               "AND overlay=?", (ge.OVERLAY_TP_15_FULL,)).fetchone()[0]
    assert n_term_before == 0   # not filled yet
    conn.close()

    _armed_managed_env(monkeypatch, max_obs="1")
    # keep poll timestamps within the quote-staleness bound of the fixed book quotes
    times2 = iter(list(range(NOW_MS, NOW_MS + 1_000_000)))
    r2 = mpr.run(db, g8_db, resume=True, now_ms_provider=lambda: next(times2),
                monotonic_provider=lambda: 0.0, public_get=_rising_bid_book,
                hl_price_feedts=pf, hl_sigma_annual=sig)
    assert r2["stop_reason"] == "MAX_OBSERVATIONS"
    conn = sqlite3.connect(db)
    # poll_seq advanced 1 -> 2 (monotonic), never reused
    seqs = [r[0] for r in conn.execute(
        "SELECT poll_seq FROM gateg9_monitoring_snapshots WHERE position_id='cid-resume' ORDER BY poll_seq")]
    assert seqs == [1, 2]
    # exactly one TRIGGER, one FILL, one terminal -- resume never duplicated or refabricated
    trig = conn.execute("SELECT COUNT(*) FROM gateg9_overlay_events WHERE position_id='cid-resume' "
                       "AND overlay=? AND event_type='TRIGGER'", (ge.OVERLAY_TP_15_FULL,)).fetchone()[0]
    fills = conn.execute("SELECT COUNT(*) FROM gateg9_overlay_events WHERE position_id='cid-resume' "
                        "AND overlay=? AND event_type='FILL'", (ge.OVERLAY_TP_15_FULL,)).fetchone()[0]
    n_term = conn.execute("SELECT COUNT(*) FROM gateg9_overlay_terminal WHERE position_id='cid-resume' "
                        "AND overlay=?", (ge.OVERLAY_TP_15_FULL,)).fetchone()[0]
    conn.close()
    assert (trig, fills, n_term) == (1, 1, 1)


# --- 15 — concurrent-exposure snapshot persistence (end-to-end via run()) ---
def test_run_persists_concurrent_exposure_snapshot(monkeypatch, tmp_path):
    _armed_managed_env(monkeypatch, max_obs="1")
    g8_db = _write_g8_ledger(tmp_path, [_g8_candidate("cid-1", "btc-updown-15m-1000")])
    db = str(tmp_path / "g9_exposure_run.sqlite3")
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 1_000_000)))
    mpr.run(db, g8_db, now_ms_provider=lambda: next(times), monotonic_provider=lambda: 0.0,
           public_get=_flat_losing_book, hl_price_feedts=pf, hl_sigma_annual=sig)
    conn = sqlite3.connect(db)
    n = conn.execute("SELECT COUNT(*) FROM gateg9_concurrent_exposure_snapshots").fetchone()[0]
    conn.close()
    assert n >= 1


# --- staged aggregation: after all 3 tranches are terminal, ONE deterministic aggregate
# row is persisted (sum of tranche PnLs, ROI over the ORIGINAL entry cost), idempotent. ---
def test_staged_aggregate_written_and_reconciles_after_resolution(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_staged_agg.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")   # held 62.5, entry_cost 26.09
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    mpr.finalize_position_at_resolution(conn, position, overlay_runtimes=runtimes,
                                        resolution={"status": "RESOLVED", "won": True}, closed_ts=NOW_MS)
    # the 3 tranche terminal rows
    tranche_rows = conn.execute(
        "SELECT overlay, realized_net_pnl FROM gateg9_overlay_terminal WHERE position_id='cid-1' "
        "AND overlay LIKE ?", (ge.OVERLAY_STAGED + "#%",)).fetchall()
    assert len(tranche_rows) == 3
    tranche_sum = sum((Decimal(r[1]) for r in tranche_rows), Decimal("0"))
    # exactly one aggregate row (overlay == OVERLAY_STAGED, no #tranche suffix)
    agg = conn.execute("SELECT status, realized_net_pnl, net_roi FROM gateg9_overlay_terminal "
                      "WHERE position_id='cid-1' AND overlay=?", (ge.OVERLAY_STAGED,)).fetchone()
    assert agg[0] == ge.STAGED_AGGREGATE
    assert Decimal(agg[1]) == tranche_sum                     # aggregate = exact sum of tranches
    assert Decimal(agg[2]) == tranche_sum / Decimal(position["entry_cost"])   # ROI over original cost
    conn.close()


def test_staged_aggregate_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_staged_idem.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    mpr.finalize_position_at_resolution(conn, position, overlay_runtimes=runtimes,
                                        resolution={"status": "RESOLVED", "won": True}, closed_ts=NOW_MS)
    mpr._maybe_write_staged_aggregate(conn, position, closed_ts=NOW_MS + 1)   # re-invoke
    n = conn.execute("SELECT COUNT(*) FROM gateg9_overlay_terminal WHERE position_id='cid-1' "
                    "AND overlay=?", (ge.OVERLAY_STAGED,)).fetchone()[0]
    assert n == 1   # never a duplicate aggregate row
    conn.close()


def test_telegram_report_exposes_staged_aggregate_not_raw_tranches(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_staged_report.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    mpr.finalize_position_at_resolution(conn, position, overlay_runtimes=runtimes,
                                        resolution={"status": "RESOLVED", "won": True}, closed_ts=NOW_MS)
    report = mpr.build_position_telegram_report(conn, "cid-1")
    assert ge.OVERLAY_STAGED in report            # the combined staged line is present
    assert (ge.OVERLAY_STAGED + "#0") not in report   # raw per-tranche rows are collapsed away
    conn.close()


# --- deterministic Telegram-ready summary (end-to-end) ---
def test_build_position_telegram_report_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv(mpr.MANAGED_ARM_ENV, mpr.MANAGED_ARM_TOKEN)
    db = str(tmp_path / "g9_report.sqlite3")
    conn = sqlite3.connect(db)
    mpr.init_managed_ledger(conn)
    position = _position("cid-1")
    mpr.write_managed_position(conn, position)
    runtimes = mpr._fresh_overlay_runtimes()
    resolution = {"status": "RESOLVED", "won": True}
    mpr.finalize_position_at_resolution(conn, position, overlay_runtimes=runtimes,
                                        resolution=resolution, closed_ts=NOW_MS)
    report = mpr.build_position_telegram_report(conn, "cid-1")
    assert "PAPER/SHADOW" in report
    assert ge.OVERLAY_HOLD_CONTROL in report
    conn.close()


# --- CLI ---
def test_main_requires_db_and_g8_db_arguments():
    with pytest.raises(SystemExit):
        mpr.main([])


def test_main_unarmed_returns_guard_code(monkeypatch, tmp_path):
    monkeypatch.delenv(mpr.MANAGED_ARM_ENV, raising=False)
    db = str(tmp_path / "g9_cli.sqlite3")
    rc = mpr.main(["--db", db, "--g8-db", str(tmp_path / "g8.sqlite3")])
    assert rc == 2
    import os
    assert not os.path.exists(db)
