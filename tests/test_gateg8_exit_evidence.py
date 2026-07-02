"""
Gate G8 — Exit-Bid Evidence, Slice 1 (OFFLINE, RED-first).

SIMULATED held-token exit-liquidation evidence for a G8 PAPER_OPEN holding. No order
executes; every economic field is a simulated mark, never a real fill or realized PnL.
Injected fakes only; zero live network. No G9 orchestration, no wallet/signing/capital.
"""
import sqlite3
from decimal import Decimal

import pytest

from analysis.forensic import gateg7_paper_pnl as pp
from analysis.forensic import gateg8_exit_evidence as ee
from tools import gateg8_paper_forward_capture as fwd

NOW_MS = 1_900_000_000_000


# ---------------------------------------------------------------------------
# helpers — a simulated original PAPER_OPEN holding + held-token book fixtures
# ---------------------------------------------------------------------------
def _entry_row(**over):
    base = dict(condition_id="cid-1", slug="btc-updown-15m-1000", asset="BTC", window="1000",
                selected_side="YES", selected_token_id="tokUp",
                yes_token_id="tokUp", no_token_id="tokDown",
                selected_filled_qty="100", yes_exec_ask_vwap="0.40", no_exec_ask_vwap="0.60",
                fee_rate="0.07", selected_entry_notional="40", paper_decision_ts=NOW_MS)
    base.update(over)
    return base


def _mk_book(bids, asks, *, qts=NOW_MS - 1, cs=NOW_MS - 3, cc=NOW_MS - 2):
    return {"bids": bids, "asks": asks, "quote_ts_ms": qts,
            "capture_started_ms": cs, "capture_completed_ms": cc}


def _build(entry_row, books, *, source_ledger_id=9, entry_ledger_id=7,
           obs_ts_ms=NOW_MS, poll_ledger_status="PAPER_OPEN"):
    return ee.build_exit_evidence(entry_row=entry_row, entry_ledger_id=entry_ledger_id,
                                  source_ledger_id=source_ledger_id, obs_ts_ms=obs_ts_ms,
                                  poll_ledger_status=poll_ledger_status, books_by_token=books)


# --- A. original held-token fixity across a later opposite-side selection ---
def test_held_token_fixity_ignores_current_poll_side():
    er = _entry_row(selected_side="YES", selected_token_id="tokUp", selected_filled_qty="100")
    books = {"tokUp": _mk_book([["0.50", "100"]], [["0.40", "1000"]]),
             "tokDown": _mk_book([["0.90", "100"]], [["0.95", "1000"]])}
    # poll_ledger_status simulates a LATER poll that selected NO -- must be ignored
    row = _build(er, books, poll_ledger_status="NO_PAPER_ENTRY", source_ledger_id=5)
    assert row["held_token_id"] == "tokUp"
    assert Decimal(row["full_qty_exec_bid_vwap"]) == Decimal("0.50")   # tokUp, never tokDown 0.90
    assert Decimal(row["best_bid"]) == Decimal("0.50")


# --- B. exact full-quantity multi-level bid walk with hand-computed Decimals ---
def test_full_qty_bid_walk_exact_values():
    er = _entry_row(selected_filled_qty="100", yes_exec_ask_vwap="0.40",
                    selected_entry_notional="40", fee_rate="0.07")
    books = {"tokUp": _mk_book([["0.50", "60"], ["0.48", "40"]], [["0.40", "1000"]]),
             "tokDown": _mk_book([["0.30", "10"]], [["0.60", "10"]])}
    row = _build(er, books)
    assert row["evidence_status"] == "OK"
    assert row["bid_depth_sufficient"] == 1
    assert row["levels_used"] == 2 and row["would_move_book"] == 1
    assert Decimal(row["full_qty_exec_bid_vwap"]) == Decimal("0.492")
    assert Decimal(row["simulated_gross_liquidation_value"]) == Decimal("49.2")
    assert Decimal(row["exit_fee"]) == Decimal("1.74955")
    assert Decimal(row["simulated_net_liquidation_value"]) == Decimal("47.45045")
    assert Decimal(row["entry_fee"]) == Decimal("1.68000")
    assert Decimal(row["entry_cost"]) == Decimal("41.68000")
    assert Decimal(row["simulated_mark_to_exit_pnl"]) == Decimal("5.77045")


# --- C/M. insufficient depth: partial simulated evidence, full-position fields NULL ---
def test_insufficient_depth_partial_only_no_full_fabrication():
    er = _entry_row(selected_filled_qty="100")
    books = {"tokUp": _mk_book([["0.50", "60"]], [["0.40", "1000"]]),
             "tokDown": _mk_book([["0.30", "10"]], [["0.60", "10"]])}
    row = _build(er, books)
    assert row["evidence_status"] == "BID_DEPTH_INSUFFICIENT"
    assert row["bid_depth_sufficient"] == 0
    assert Decimal(row["walkable_bid_qty"]) == Decimal("60")
    assert Decimal(row["residual_unwalkable_qty"]) == Decimal("40")
    assert Decimal(row["simulated_walkable_bid_vwap"]) == Decimal("0.50")
    assert Decimal(row["simulated_walkable_gross_liquidation_value"]) == Decimal("30")
    for f in ("full_qty_exec_bid_vwap", "exit_fee", "simulated_gross_liquidation_value",
              "simulated_net_liquidation_value", "simulated_mark_to_exit_pnl"):
        assert row[f] is None, f


# --- D. entry and exit fee separation; exact PnL identity ---
def test_entry_and_exit_fee_separate_identity():
    er = _entry_row(selected_filled_qty="100", yes_exec_ask_vwap="0.40",
                    selected_entry_notional="40", fee_rate="0.07")
    books = {"tokUp": _mk_book([["0.50", "100"]], [["0.40", "1000"]]),
             "tokDown": _mk_book([["0.30", "10"]], [["0.60", "10"]])}
    row = _build(er, books)
    entry_fee = Decimal(row["entry_fee"]); exit_fee = Decimal(row["exit_fee"])
    gross = Decimal(row["simulated_gross_liquidation_value"])
    net = Decimal(row["simulated_net_liquidation_value"])
    cost = Decimal(row["entry_cost"])
    assert entry_fee != exit_fee                                   # distinct legs, distinct prices
    assert net == gross - exit_fee
    assert cost == Decimal(row["entry_notional"]) + entry_fee      # entry fee charged exactly once
    assert Decimal(row["simulated_mark_to_exit_pnl"]) == net - cost


# --- E. original entry basis immutable when later poll asks change ---
def test_entry_basis_immutable_under_later_ask_change():
    er = _entry_row(selected_filled_qty="100", yes_exec_ask_vwap="0.40", selected_entry_notional="40")
    b1 = {"tokUp": _mk_book([["0.50", "100"]], [["0.40", "1000"]]),
          "tokDown": _mk_book([["0.3", "10"]], [["0.6", "10"]])}
    b2 = {"tokUp": _mk_book([["0.50", "100"]], [["0.99", "1000"]]),
          "tokDown": _mk_book([["0.3", "10"]], [["0.6", "10"]])}
    r1 = _build(er, b1, source_ledger_id=10, poll_ledger_status="PAPER_OPEN")
    r2 = _build(er, b2, source_ledger_id=11, obs_ts_ms=NOW_MS + 1,
                poll_ledger_status="DUPLICATE_CONDITION_SKIPPED")
    assert r1["entry_ask_vwap"] == r2["entry_ask_vwap"] == "0.40"
    assert r1["entry_cost"] == r2["entry_cost"]
    assert r1["simulated_mark_to_exit_pnl"] == r2["simulated_mark_to_exit_pnl"]   # identical bids/entry
    assert r1["best_ask"] != r2["best_ask"]                                       # only current ask moved


# --- F. writer idempotency + conflict fails closed ---
def test_writer_idempotent_and_conflict(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "ev.sqlite3"))
    ee.init_exit_evidence_table(conn)
    er = _entry_row()
    books = {"tokUp": _mk_book([["0.50", "100"]], [["0.40", "1000"]]),
             "tokDown": _mk_book([["0.3", "10"]], [["0.6", "10"]])}
    row = _build(er, books, source_ledger_id=100)
    assert ee.write_exit_evidence(conn, row) == "RECORDED"
    assert ee.write_exit_evidence(conn, dict(row)) == "ALREADY_RECORDED"
    conflict = dict(row); conflict["best_bid"] = "0.51"
    with pytest.raises(ee.ExitEvidenceConflictError):
        ee.write_exit_evidence(conn, conflict)
    got = conn.execute("SELECT best_bid FROM gateg8_exit_evidence WHERE source_ledger_id=100").fetchone()[0]
    assert got == "0.50"                                            # existing row unchanged
    assert conn.execute("SELECT COUNT(*) FROM gateg8_exit_evidence").fetchone()[0] == 1
    conn.close()


# --- H. known open holding + unavailable book -> BOOK_UNAVAILABLE, book/money NULL ---
def test_book_unavailable_holding_known_money_null():
    er = _entry_row()
    books = {"tokUp": None, "tokDown": _mk_book([["0.3", "10"]], [["0.6", "10"]])}
    row = _build(er, books, source_ledger_id=4, poll_ledger_status="NO_PAPER_ENTRY")
    assert row["evidence_status"] == "BOOK_UNAVAILABLE"
    assert row["held_token_id"] == "tokUp" and row["held_side"] == "YES"
    for f in ("best_bid", "best_ask", "walkable_bid_qty", "full_qty_exec_bid_vwap", "exit_fee",
              "simulated_gross_liquidation_value", "simulated_net_liquidation_value",
              "simulated_mark_to_exit_pnl", "simulated_walkable_bid_vwap"):
        assert row[f] is None, f


# --- N. FEE_UNAVAILABLE: walk persists, full-position money NULL, no default fee ---
def test_fee_unavailable_walk_persists_money_null():
    er = _entry_row(fee_rate=None)
    books = {"tokUp": _mk_book([["0.50", "100"]], [["0.40", "1000"]]),
             "tokDown": _mk_book([["0.3", "10"]], [["0.6", "10"]])}
    row = _build(er, books, source_ledger_id=8)
    assert row["evidence_status"] == "FEE_UNAVAILABLE"
    assert Decimal(row["walkable_bid_qty"]) == Decimal("100")
    assert Decimal(row["best_bid"]) == Decimal("0.50")
    for f in ("entry_fee", "entry_cost", "exit_fee", "full_qty_exec_bid_vwap",
              "simulated_gross_liquidation_value", "simulated_net_liquidation_value",
              "simulated_mark_to_exit_pnl"):
        assert row[f] is None, f


# --- O. malformed ladder fails closed via committed plumbing validation ---
def test_malformed_ladder_fails_closed():
    er = _entry_row(selected_filled_qty="100")
    books = {"tokUp": _mk_book([["1.5", "100"]], [["0.40", "1000"]]),   # price > 1 -> out of domain
             "tokDown": _mk_book([["0.3", "10"]], [["0.6", "10"]])}
    row = _build(er, books, source_ledger_id=12)
    assert row["evidence_status"] == "LADDER_MALFORMED"
    assert row["failure_provenance"]
    for f in ("full_qty_exec_bid_vwap", "exit_fee", "simulated_mark_to_exit_pnl",
              "simulated_walkable_bid_vwap"):
        assert row[f] is None, f


# --- L. best_bid/best_ask from the held token's exact fixture ---
def test_best_bid_ask_from_held_token_fixture():
    er = _entry_row(selected_side="YES", selected_token_id="tokUp", selected_filled_qty="10")
    books = {"tokUp": _mk_book([["0.55", "100"], ["0.54", "50"]], [["0.60", "100"], ["0.62", "50"]]),
             "tokDown": _mk_book([["0.11", "100"]], [["0.12", "100"]])}
    row = _build(er, books, source_ledger_id=6, poll_ledger_status="DUPLICATE_CONDITION_SKIPPED")
    assert Decimal(row["best_bid"]) == Decimal("0.55")               # highest bid of held token
    assert Decimal(row["best_ask"]) == Decimal("0.60")               # lowest ask of held token


# --- I. AST/source scan: no wallet/signing/capital/order path in new + touched modules ---
def test_no_wallet_or_order_path_in_new_and_touched_modules():
    import ast
    import inspect
    for mod in (ee, fwd):
        tree = ast.parse(inspect.getsource(mod))
        imported = set(); calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        for forbidden in ("wallet", "signing", "web3", "execution"):
            assert not any(forbidden in m.lower() for m in imported), (mod.__name__, imported)
        for c in ("sign", "place_order", "send_transaction", "submit_order"):
            assert c not in calls, (mod.__name__, c)


# ===========================================================================
# run-level integration (injected fakes; zero live network)
# ===========================================================================
class _Clock:
    def __init__(self, start=NOW_MS):
        self.now = start

    def read(self):
        self.now += 1
        return self.now


def _run_env(monkeypatch, max_obs):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    monkeypatch.setenv("GATEG8_MAX_OBSERVATIONS", str(max_obs))
    monkeypatch.setenv("GATEG8_MAX_ELAPSED_S", "600")
    monkeypatch.setenv("GATEG8_MAX_SKEW_MS", "1500")
    monkeypatch.setattr(fwd.time, "sleep", lambda *a, **k: None)


def _gamma(slug):
    import datetime as dt
    ep = int(slug.rsplit("-", 1)[1])
    end = dt.datetime.fromtimestamp(ep + fwd.TARGET_INTERVAL_S,
                                    dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"conditionId": f"0xcid-{ep}", "slug": slug, "outcomes": ["Up", "Down"],
            "clobTokenIds": ["tokUp", "tokDown"], "endDate": end, "feesEnabled": True,
            "feeSchedule": {"exponent": 1, "rate": 0.07, "takerOnly": True}}


def _pg_factory(clock):
    def pg(url, params=None):
        if url == fwd.runner.GAMMA_MARKETS:
            return [_gamma(params["slug"])]
        tid = params["token_id"]
        ask = "0.30" if tid == "tokUp" else "0.65"       # cheap YES -> PAPER_OPEN YES/tokUp
        return {"asks": [{"price": ask, "size": "1000"}],
                "bids": [{"price": "0.20", "size": "1000"}], "timestamp": clock.now}
    return pg


def _hl():
    def pf(coin, ts_ms):
        if ts_ms < NOW_MS - 1000:                        # window-open strike query (past)
            return Decimal("59000"), ts_ms
        return Decimal("60000"), ts_ms - 30_000
    return pf, (lambda coin, now_ms: 0.8)


# --- K. opening PAPER_OPEN poll itself creates exit evidence (source == entry) ---
def test_run_opening_poll_creates_exit_evidence(monkeypatch, tmp_path):
    _run_env(monkeypatch, max_obs=1)
    clock = _Clock(); pf, sig = _hl()
    db = str(tmp_path / "k.sqlite3")
    fwd.run(db, now_ms_provider=clock.read, monotonic_provider=lambda: 0.0,
            public_get=_pg_factory(clock), hl_price_feedts=pf, hl_sigma_annual=sig)
    conn = sqlite3.connect(db)
    po = conn.execute("SELECT rowid, selected_side, selected_token_id "
                      "FROM gateg8_paper_ledger WHERE status='PAPER_OPEN'").fetchone()
    ev = conn.execute("SELECT source_ledger_id, entry_ledger_id, held_token_id, held_side, "
                      "evidence_status, full_qty_exec_bid_vwap FROM gateg8_exit_evidence").fetchall()
    conn.close()
    assert po is not None
    po_rowid, side, tok = po
    assert len(ev) == 1
    src, ent, htok, hside, status, fvwap = ev[0]
    assert src == ent == po_rowid                        # opening poll: source_ledger_id == entry
    assert htok == tok == "tokUp" and hside == side == "YES"
    assert status == "OK" and fvwap is not None          # full held qty walkable on deep bids


# --- J. at-most-one PAPER_OPEN invariant holds with hook active; later poll also gets evidence ---
def test_run_invariant_one_paper_open_and_later_poll_evidence(monkeypatch, tmp_path):
    _run_env(monkeypatch, max_obs=3)
    clock = _Clock(); pf, sig = _hl()
    db = str(tmp_path / "j.sqlite3")
    fwd.run(db, now_ms_provider=clock.read, monotonic_provider=lambda: 0.0,
            public_get=_pg_factory(clock), hl_price_feedts=pf, hl_sigma_annual=sig)
    conn = sqlite3.connect(db)
    opens = conn.execute("SELECT condition_id, COUNT(*) FROM gateg8_paper_ledger "
                         "WHERE status='PAPER_OPEN' GROUP BY condition_id").fetchall()
    assert opens and all(c == 1 for _, c in opens)       # invariant preserved
    cid = opens[0][0]
    ev = conn.execute("SELECT COUNT(*) FROM gateg8_exit_evidence WHERE condition_id=?",
                      (cid,)).fetchone()[0]
    conn.close()
    assert ev >= 2                                        # opening PAPER_OPEN + later DUPLICATE poll


# --- G. evidence-writer failure after ledger commit stops the loop; orphan detectable; no retry ---
def test_run_evidence_writer_failure_stops_loop_no_orphan_completion(monkeypatch, tmp_path):
    _run_env(monkeypatch, max_obs=2)
    clock = _Clock(); pf, sig = _hl()
    calls = {"n": 0}

    def boom(conn, row):
        calls["n"] += 1
        raise RuntimeError("injected evidence-writer failure")

    monkeypatch.setattr(fwd.ee, "write_exit_evidence", boom)
    db = str(tmp_path / "g.sqlite3")
    with pytest.raises(RuntimeError):
        fwd.run(db, now_ms_provider=clock.read, monotonic_provider=lambda: 0.0,
                public_get=_pg_factory(clock), hl_price_feedts=pf, hl_sigma_annual=sig)
    assert calls["n"] == 1                                # fail-fast: no retry
    conn = sqlite3.connect(db)
    po = conn.execute("SELECT rowid FROM gateg8_paper_ledger WHERE status='PAPER_OPEN'").fetchone()
    orphan = conn.execute(
        "SELECT l.rowid FROM gateg8_paper_ledger l "
        "LEFT JOIN gateg8_exit_evidence e ON e.source_ledger_id=l.rowid "
        "WHERE e.source_ledger_id IS NULL AND l.status='PAPER_OPEN'").fetchone()
    conn.close()
    assert po is not None                                 # ledger row committed
    assert orphan is not None                             # missing evidence is auditable, not hidden
