"""
Gate G8 — Proxy-Basis Evidence, Slice 2 (OFFLINE, RED-first).

Per-source RAW reference evidence (HL window-strike, HL current, Kraken spot, Coinbase spot)
captured at ENTRY for a G8 PAPER_OPEN, so a later analysis can diagnose whether the
Polymarket-vs-Hyperliquid model edge is distorted by reference-source basis.

HARD BOUNDARIES exercised here:
  * No order, wallet, signing, capital, G9, Outcome Enrichment.
  * ENTRY phase only; four reference kinds; atomic four-row group (all-or-zero).
  * No blend / consensus / midpoint / persisted delta. Every value raw + source-specific.
  * HL rows reuse in-memory G8 values (zero extra HL request); spot rows carry NO source-event ts.
  * Injected fakes only; zero live network.
"""
import sqlite3
import uuid
from decimal import Decimal

import pytest

from analysis.forensic import gateg7_paper_pnl as pp
from analysis.forensic import gateg8_proxy_basis as pb
from tools import gateg8_paper_forward_capture as fwd

NOW_MS = 1_900_000_000_000


def _ident(**over):
    base = {"condition_id": "cid-1", "slug": "btc-updown-15m-1000", "asset": "BTC", "window": "1000"}
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# pure builders
# ---------------------------------------------------------------------------
def _hl_rows(capture_run_id="run-1", source_ledger_id=5):
    return pb.build_hl_reference_rows(
        capture_run_id=capture_run_id, source_ledger_id=source_ledger_id,
        entry_ledger_id=source_ledger_id, market_ident=_ident(),
        window_strike=Decimal("59000"), window_strike_ts_ms=1000,
        window_strike_started_ms=1001, window_strike_completed_ms=1002,
        current_price=Decimal("60000.5"), current_ts_ms=2000,
        current_started_ms=2001, current_completed_ms=2002)


def _ok_tick(pair, price):
    return {"source_name": pair, "pair": pair, "price_raw": price,
            "price_decimal_text": price, "reject_reason": None}


def _spot_row(reference_kind, tick, capture_run_id="run-1", source_ledger_id=5):
    return pb.build_spot_reference_row(
        reference_kind=reference_kind, tick=tick, capture_started_ms=10,
        capture_completed_ms=20, capture_run_id=capture_run_id,
        source_ledger_id=source_ledger_id, entry_ledger_id=source_ledger_id,
        market_ident=_ident())


def _group(capture_run_id="run-1", source_ledger_id=5):
    rows = list(_hl_rows(capture_run_id, source_ledger_id))
    rows.append(_spot_row(pb.REF_COINBASE_SPOT, _ok_tick("BTC-USD", "60050"),
                          capture_run_id, source_ledger_id))
    rows.append(_spot_row(pb.REF_KRAKEN_SPOT, _ok_tick("XBTUSD", "60010"),
                          capture_run_id, source_ledger_id))
    return rows


def test_hl_reference_rows_value_and_timestamp_semantics():
    by = {r["reference_kind"]: r for r in _hl_rows()}
    s, c = by[pb.REF_HL_WINDOW_STRIKE], by[pb.REF_HL_CURRENT]
    assert s["value_raw"] is None and c["value_raw"] is None
    assert s["value_decimal_text"] == "59000" and c["value_decimal_text"] == "60000.5"
    assert s["source_event_ts_ms"] == 1000 and c["source_event_ts_ms"] == 2000
    assert s["timestamp_semantic"] == "CANDLE_START_FOR_CLOSE_VALUE"
    assert c["timestamp_semantic"] == "CANDLE_START_FOR_CLOSE_VALUE"
    assert s["capture_started_ms"] == 1001 and s["capture_completed_ms"] == 1002
    assert c["capture_started_ms"] == 2001 and c["capture_completed_ms"] == 2002
    assert s["capture_status"] == "OK" and c["capture_status"] == "OK"
    assert s["instrument"] == "hl-1m-candle-close:BTC"
    assert s["phase"] == "ENTRY" and c["phase"] == "ENTRY"
    assert s["capture_run_id"] == "run-1" and s["source_ledger_id"] == 5


def test_spot_reference_row_ok_no_source_event_ts():
    row = _spot_row(pb.REF_COINBASE_SPOT, _ok_tick("BTC-USD", "60050.5"))
    assert row["source_event_ts_ms"] is None
    assert row["timestamp_semantic"] == "NO_SOURCE_EVENT_TS_CAPTURE_BRACKET_ONLY"
    assert row["value_raw"] == "60050.5" and row["value_decimal_text"] == "60050.5"
    assert row["capture_started_ms"] == 10 and row["capture_completed_ms"] == 20
    assert row["capture_status"] == "OK" and row["failure_provenance"] is None
    assert row["instrument"] == "coinbase-v2-spot:BTC-USD"
    assert row["phase"] == "ENTRY"


def test_spot_reference_row_rejected_becomes_complete_dict():
    tick = {"source_name": "kraken", "pair": "XBTUSD", "price_raw": None,
            "price_decimal_text": None,
            "reject_reason": "URLError timed out https://api.kraken.com/0/x 0xabcdef1234567890"}
    row = _spot_row(pb.REF_KRAKEN_SPOT, tick)
    assert row["capture_status"] == "REJECTED"
    assert row["value_raw"] is None and row["value_decimal_text"] is None
    assert row["source_event_ts_ms"] is None
    assert row["timestamp_semantic"] == "NO_SOURCE_EVENT_TS_CAPTURE_BRACKET_ONLY"
    assert row["failure_provenance"]
    assert "[URL]" in row["failure_provenance"]        # sanitized
    assert row["instrument"] == "kraken:XBTUSD"


def test_sanitizer_redacts_and_caps():
    s = pb._sanitize("boom https://x.com/a?token=1 0x" + "a" * 20 + " " + "1" * 20 + " " + "z" * 400)
    assert "[URL]" in s and "[HEX]" in s and "[ID]" in s
    assert len(s) <= 220


# ---------------------------------------------------------------------------
# atomic group writer
# ---------------------------------------------------------------------------
def test_group_writer_records_four_rows_atomically(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "w.sqlite3"))
    pb.init_proxy_basis_table(conn)
    assert pb.write_proxy_basis_group(conn, _group()) == "RECORDED"
    assert conn.execute("SELECT COUNT(*) FROM gateg8_proxy_basis").fetchone()[0] == 4
    conn.close()


def test_group_writer_idempotent_complete_batch(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "i.sqlite3"))
    pb.init_proxy_basis_table(conn)
    assert pb.write_proxy_basis_group(conn, _group()) == "RECORDED"
    assert pb.write_proxy_basis_group(conn, _group()) == "ALREADY_RECORDED"
    assert conn.execute("SELECT COUNT(*) FROM gateg8_proxy_basis").fetchone()[0] == 4
    conn.close()


def test_group_writer_conflict_zero_mutation(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "c.sqlite3"))
    pb.init_proxy_basis_table(conn)
    pb.write_proxy_basis_group(conn, _group())
    conflict = _group()
    conflict[3]["value_decimal_text"] = "99999"        # differing payload on one row
    with pytest.raises(pb.ProxyBasisConflictError):
        pb.write_proxy_basis_group(conn, conflict)
    assert conn.execute("SELECT COUNT(*) FROM gateg8_proxy_basis").fetchone()[0] == 4
    # original untouched
    got = conn.execute("SELECT value_decimal_text FROM gateg8_proxy_basis "
                       "WHERE reference_kind=?", (pb.REF_KRAKEN_SPOT,)).fetchone()[0]
    assert got == "60010"
    conn.close()


def test_group_writer_partial_pre_existing_fail_fast(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "p.sqlite3"))
    pb.init_proxy_basis_table(conn)
    # pre-seed only two of the four rows for the same (capture_run_id, source_ledger_id)
    seed = _group()[:2]
    cols = [c for c in seed[0].keys()]
    for r in seed:
        conn.execute(f"INSERT INTO gateg8_proxy_basis({','.join(cols)}) "
                     f"VALUES ({','.join('?' for _ in cols)})", tuple(r[c] for c in cols))
    conn.commit()
    with pytest.raises(pb.ProxyBasisConflictError):
        pb.write_proxy_basis_group(conn, _group())
    assert conn.execute("SELECT COUNT(*) FROM gateg8_proxy_basis").fetchone()[0] == 2
    conn.close()


class _InsertFailer:
    """Wraps a real connection; raises on the Nth INSERT to prove savepoint atomicity."""
    def __init__(self, conn, fail_on):
        self._c = conn
        self._n = 0
        self._fail_on = fail_on

    def execute(self, sql, *args):
        if sql.strip().upper().startswith("INSERT"):
            self._n += 1
            if self._n == self._fail_on:
                raise RuntimeError("injected mid-batch insert failure")
        return self._c.execute(sql, *args)

    def commit(self):
        return self._c.commit()

    def __getattr__(self, name):
        return getattr(self._c, name)


def test_group_writer_atomic_rollback_on_insert_failure(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    conn = sqlite3.connect(db)
    pb.init_proxy_basis_table(conn)
    failer = _InsertFailer(conn, fail_on=3)
    with pytest.raises(RuntimeError):
        pb.write_proxy_basis_group(failer, _group())
    conn.close()
    verify = sqlite3.connect(db)                        # fresh conn: only committed data visible
    assert verify.execute("SELECT COUNT(*) FROM gateg8_proxy_basis").fetchone()[0] == 0
    verify.close()


def test_unique_constraint_capture_run_source_kind(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "u.sqlite3"))
    pb.init_proxy_basis_table(conn)
    pb.write_proxy_basis_group(conn, _group())
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO gateg8_proxy_basis"
                     "(capture_run_id, source_ledger_id, reference_kind) VALUES (?,?,?)",
                     ("run-1", 5, pb.REF_KRAKEN_SPOT))
    conn.close()


def test_schema_no_real_or_blend_columns(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "s.sqlite3"))
    pb.init_proxy_basis_table(conn)
    info = conn.execute("PRAGMA table_info(gateg8_proxy_basis)").fetchall()
    conn.close()
    types = {r[1]: (r[2] or "").upper() for r in info}
    assert all(t in ("TEXT", "INTEGER") for t in types.values()), types
    for banned in ("blend", "midpoint", "consensus", "delta", "spread", "agreement"):
        assert not any(banned in c.lower() for c in types), (banned, list(types))
    for required in ("capture_run_id", "source_ledger_id", "entry_ledger_id", "reference_kind",
                     "value_raw", "value_decimal_text", "source_event_ts_ms",
                     "timestamp_semantic", "capture_status", "failure_provenance", "phase"):
        assert required in types, required


# ===========================================================================
# run-level integration (injected fakes; zero live network)
# ===========================================================================
class _Clock:
    def __init__(self, start=NOW_MS):
        self.now = start

    def read(self):
        self.now += 1
        return self.now


class _SpotClient:
    """Injected async http client for the public spot fetchers (records calls; no network)."""
    def __init__(self, cb="60050.5", kr="60010.1", fail_kraken=False):
        self.calls = []
        self.cb, self.kr, self.fail_kraken = cb, kr, fail_kraken

    async def __call__(self, url):
        self.calls.append(url)
        if "coinbase.com" in url:
            return {"data": {"amount": self.cb, "base": "BTC", "currency": "USD"}}
        if "kraken.com" in url:
            if self.fail_kraken:
                raise RuntimeError("kraken transport down")
            return {"error": [], "result": {"XXBTZUSD": {"c": [self.kr, "0.1"]}}}
        raise AssertionError(f"unexpected url {url}")


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
        ask = "0.30" if tid == "tokUp" else "0.65"     # cheap YES -> PAPER_OPEN YES/tokUp
        return {"asks": [{"price": ask, "size": "1000"}],
                "bids": [{"price": "0.20", "size": "1000"}], "timestamp": clock.now}
    return pg


def _pg_two(clock):
    """Two distinct conditions in the SAME current window -> two PAPER_OPEN events per run."""
    def pg(url, params=None):
        if url == fwd.runner.GAMMA_MARKETS:
            slug = params["slug"]
            ep = int(slug.rsplit("-", 1)[1])
            base = _gamma(slug)
            return [dict(base, conditionId=f"0xcidA-{ep}"), dict(base, conditionId=f"0xcidB-{ep}")]
        tid = params["token_id"]
        ask = "0.30" if tid == "tokUp" else "0.65"
        return {"asks": [{"price": ask, "size": "1000"}],
                "bids": [{"price": "0.20", "size": "1000"}], "timestamp": clock.now}
    return pg


def _pg_no_open(clock):
    def pg(url, params=None):
        if url == fwd.runner.GAMMA_MARKETS:
            return [_gamma(params["slug"])]
        return {"asks": [{"price": "0.99", "size": "1000"}],
                "bids": [{"price": "0.01", "size": "1000"}], "timestamp": clock.now}
    return pg


def _hl():
    def pf(coin, ts_ms):
        if ts_ms < NOW_MS - 1000:                      # window-open strike query (past)
            return Decimal("59000"), ts_ms
        return Decimal("60000"), ts_ms - 30_000
    return pf, (lambda coin, now_ms: 0.8)


def _hl_flat():
    """Strike == current -> fair ~0.5, so an expensive book yields NO edge (no PAPER_OPEN)."""
    def pf(coin, ts_ms):
        if ts_ms < NOW_MS - 1000:
            return Decimal("60000"), ts_ms
        return Decimal("60000"), ts_ms - 30_000
    return pf, (lambda coin, now_ms: 0.8)


def _run(db, monkeypatch, max_obs, *, proxy, spot_client, pf, sig, pg, clock):
    _run_env(monkeypatch, max_obs)
    if proxy:
        monkeypatch.setenv(pb.PROXY_ARM_ENV, pb.PROXY_ARM_TOKEN)
    return fwd.run(db, now_ms_provider=clock.read, monotonic_provider=lambda: 0.0,
                   public_get=pg, hl_price_feedts=pf, hl_sigma_annual=sig,
                   spot_http_client=spot_client)


def test_unarmed_inertness_no_proxy_table_or_calls(monkeypatch, tmp_path):
    clock = _Clock(); pf, sig = _hl(); sc = _SpotClient()
    db = str(tmp_path / "i.sqlite3")
    _run(db, monkeypatch, 1, proxy=False, spot_client=sc, pf=pf, sig=sig,
         pg=_pg_factory(clock), clock=clock)
    conn = sqlite3.connect(db)
    t = conn.execute("SELECT name FROM sqlite_master WHERE type='table' "
                     "AND name='gateg8_proxy_basis'").fetchone()
    conn.close()
    assert t is None
    assert sc.calls == []


def test_non_paper_open_no_spot_calls_no_rows(monkeypatch, tmp_path):
    clock = _Clock(); pf, sig = _hl_flat(); sc = _SpotClient()
    db = str(tmp_path / "n.sqlite3")
    _run(db, monkeypatch, 2, proxy=True, spot_client=sc, pf=pf, sig=sig,
         pg=_pg_no_open(clock), clock=clock)
    conn = sqlite3.connect(db)
    npo = conn.execute("SELECT COUNT(*) FROM gateg8_paper_ledger WHERE status='PAPER_OPEN'").fetchone()[0]
    pr = conn.execute("SELECT COUNT(*) FROM gateg8_proxy_basis").fetchone()[0]
    conn.close()
    assert npo == 0 and pr == 0
    assert sc.calls == []


def test_paper_open_creates_exactly_four_entry_rows(monkeypatch, tmp_path):
    clock = _Clock(); pf, sig = _hl(); sc = _SpotClient()
    db = str(tmp_path / "p.sqlite3")
    _run(db, monkeypatch, 1, proxy=True, spot_client=sc, pf=pf, sig=sig,
         pg=_pg_factory(clock), clock=clock)
    conn = sqlite3.connect(db)
    po = conn.execute("SELECT rowid FROM gateg8_paper_ledger WHERE status='PAPER_OPEN'").fetchone()[0]
    rows = conn.execute("SELECT reference_kind, phase, source_ledger_id, entry_ledger_id "
                        "FROM gateg8_proxy_basis").fetchall()
    conn.close()
    assert len(rows) == 4
    assert {r[0] for r in rows} == {pb.REF_HL_WINDOW_STRIKE, pb.REF_HL_CURRENT,
                                    pb.REF_KRAKEN_SPOT, pb.REF_COINBASE_SPOT}
    assert all(r[1] == "ENTRY" for r in rows)
    assert all(r[2] == po and r[3] == po for r in rows)


def test_single_uuidv4_reused_across_run(monkeypatch, tmp_path):
    clock = _Clock(); pf, sig = _hl(); sc = _SpotClient()
    db = str(tmp_path / "u2.sqlite3")
    _run(db, monkeypatch, 5, proxy=True, spot_client=sc, pf=pf, sig=sig,
         pg=_pg_two(clock), clock=clock)
    conn = sqlite3.connect(db)
    opens = conn.execute("SELECT COUNT(*) FROM gateg8_paper_ledger WHERE status='PAPER_OPEN'").fetchone()[0]
    ids = [r[0] for r in conn.execute("SELECT DISTINCT capture_run_id FROM gateg8_proxy_basis")]
    total = conn.execute("SELECT COUNT(*) FROM gateg8_proxy_basis").fetchone()[0]
    conn.close()
    assert opens == 2                                  # two PAPER_OPEN events this run
    assert total == 8                                  # 4 rows per event
    assert len(ids) == 1                               # ONE run id reused across both events
    assert uuid.UUID(ids[0]).version == 4              # genuine UUIDv4, not timestamp-derived


def test_no_extra_hl_request_when_proxy_on(monkeypatch, tmp_path):
    def counting_pf():
        n = {"c": 0}
        base_pf, _ = _hl()

        def pf(coin, ts):
            n["c"] += 1
            return base_pf(coin, ts)
        return pf, n

    _, sig = _hl()
    c1 = _Clock(); pf1, n1 = counting_pf()
    _run(str(tmp_path / "off.sqlite3"), monkeypatch, 1, proxy=False, spot_client=_SpotClient(),
         pf=pf1, sig=sig, pg=_pg_factory(c1), clock=c1)
    c2 = _Clock(); pf2, n2 = counting_pf()
    _run(str(tmp_path / "on.sqlite3"), monkeypatch, 1, proxy=True, spot_client=_SpotClient(),
         pf=pf2, sig=sig, pg=_pg_factory(c2), clock=c2)
    assert n1["c"] == n2["c"]                           # proxy path adds ZERO HL requests


def test_hl_rows_match_injected_in_memory_values(monkeypatch, tmp_path):
    clock = _Clock(); sc = _SpotClient()
    holder = {}

    def pf(coin, ts):
        if ts < NOW_MS - 1000:
            holder["strike_ft"] = ts
            return Decimal("59000"), ts
        holder["cur_ft"] = ts - 30_000
        return Decimal("60000"), holder["cur_ft"]

    db = str(tmp_path / "h.sqlite3")
    _run(db, monkeypatch, 1, proxy=True, spot_client=sc, pf=pf, sig=(lambda c, n: 0.8),
         pg=_pg_factory(clock), clock=clock)
    conn = sqlite3.connect(db)
    s = conn.execute("SELECT value_decimal_text, source_event_ts_ms, value_raw, timestamp_semantic "
                     "FROM gateg8_proxy_basis WHERE reference_kind=?", (pb.REF_HL_WINDOW_STRIKE,)).fetchone()
    c = conn.execute("SELECT value_decimal_text, source_event_ts_ms, value_raw, timestamp_semantic "
                     "FROM gateg8_proxy_basis WHERE reference_kind=?", (pb.REF_HL_CURRENT,)).fetchone()
    conn.close()
    assert s[0] == "59000" and s[1] == holder["strike_ft"] and s[2] is None
    assert s[3] == "CANDLE_START_FOR_CLOSE_VALUE"
    assert c[0] == "60000" and c[1] == holder["cur_ft"] and c[2] is None


def test_spot_rejected_leg_inside_complete_atomic_group(monkeypatch, tmp_path):
    clock = _Clock(); pf, sig = _hl(); sc = _SpotClient(fail_kraken=True)
    db = str(tmp_path / "r.sqlite3")
    _run(db, monkeypatch, 1, proxy=True, spot_client=sc, pf=pf, sig=sig,
         pg=_pg_factory(clock), clock=clock)
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT reference_kind, capture_status, value_decimal_text, "
                        "failure_provenance FROM gateg8_proxy_basis").fetchall()
    conn.close()
    assert len(rows) == 4                               # full group still committed atomically
    by = {r[0]: r for r in rows}
    assert by[pb.REF_KRAKEN_SPOT][1] == "REJECTED"
    assert by[pb.REF_KRAKEN_SPOT][2] is None and by[pb.REF_KRAKEN_SPOT][3]
    assert by[pb.REF_COINBASE_SPOT][1] == "OK" and by[pb.REF_COINBASE_SPOT][2] == "60050.5"


def test_proxy_capture_after_ledger_and_slice1(monkeypatch, tmp_path):
    seq = []
    orig_ledger = fwd.write_paper_ledger
    orig_ee = fwd.ee.write_exit_evidence
    orig_grp = fwd.pb.write_proxy_basis_group

    def wl(conn, d):
        r = orig_ledger(conn, d)
        if d.get("status") == pp.PAPER_OPEN:
            seq.append("ledger")
        return r

    def we(conn, r):
        seq.append("slice1")
        return orig_ee(conn, r)

    def wg(conn, rows):
        seq.append("proxy")
        return orig_grp(conn, rows)

    monkeypatch.setattr(fwd, "write_paper_ledger", wl)
    monkeypatch.setattr(fwd.ee, "write_exit_evidence", we)
    monkeypatch.setattr(fwd.pb, "write_proxy_basis_group", wg)
    clock = _Clock(); pf, sig = _hl()
    _run(str(tmp_path / "o.sqlite3"), monkeypatch, 1, proxy=True, spot_client=_SpotClient(),
         pf=pf, sig=sig, pg=_pg_factory(clock), clock=clock)
    assert seq == ["ledger", "slice1", "proxy"]


def test_ledger_and_slice1_non_interference(monkeypatch, tmp_path):
    def dump(db, table):
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
        conn.close()
        return rows

    c1 = _Clock(); pf1, sig1 = _hl()
    _run(str(tmp_path / "off.sqlite3"), monkeypatch, 1, proxy=False, spot_client=_SpotClient(),
         pf=pf1, sig=sig1, pg=_pg_factory(c1), clock=c1)
    c2 = _Clock(); pf2, sig2 = _hl()
    _run(str(tmp_path / "on.sqlite3"), monkeypatch, 1, proxy=True, spot_client=_SpotClient(),
         pf=pf2, sig=sig2, pg=_pg_factory(c2), clock=c2)
    assert dump(str(tmp_path / "off.sqlite3"), "gateg8_paper_ledger") == \
        dump(str(tmp_path / "on.sqlite3"), "gateg8_paper_ledger")
    assert dump(str(tmp_path / "off.sqlite3"), "gateg8_exit_evidence") == \
        dump(str(tmp_path / "on.sqlite3"), "gateg8_exit_evidence")


def test_integrity_failure_propagates_and_stops(monkeypatch, tmp_path):
    def boom(conn, rows):
        raise fwd.pb.ProxyBasisConflictError("injected integrity failure")

    monkeypatch.setattr(fwd.pb, "write_proxy_basis_group", boom)
    clock = _Clock(); pf, sig = _hl()
    with pytest.raises(fwd.pb.ProxyBasisConflictError):
        _run(str(tmp_path / "e.sqlite3"), monkeypatch, 1, proxy=True, spot_client=_SpotClient(),
             pf=pf, sig=sig, pg=_pg_factory(clock), clock=clock)


def test_no_wallet_or_order_path_in_new_and_touched_modules():
    import ast
    import inspect
    for mod in (pb, fwd):
        tree = ast.parse(inspect.getsource(mod))
        imported = set()
        calls = set()
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
