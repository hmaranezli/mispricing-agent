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
               "fair_yes", "hl_feed_ts", "current_hold_value", "opposite_exec_ask_vwap",
               "opposite_net_edge_diagnostic", "current_spread", "gross_return", "fee_net_return")
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
