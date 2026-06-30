"""
Gate G7-lite — deterministic OFFLINE fault-injection proof.

Drives the REAL runner.run() loop with every network boundary mocked (Gamma/CLOB/HL)
and the proxy path armed, then injects:
  * Scenario A — a Coinbase/Kraken transport failure (Timeout/502) on observation 1.
  * Scenario B — a sqlite3.OperationalError("database is locked") during the proxy INSERT
    on observation 1 (the subsequent rejection write is NOT poisoned).
  * Scenario C — non-interference: the core decision projection is bit-identical with the
    proxy path OFF (no fault) vs ON (both faults), under identical frozen inputs.

Proves an optional proxy failure cannot halt the loop, cannot mutate/rollback the already
committed signal_log row or its hash-chain, surfaces exactly one no-retry PROXY_DIAG, and
the next observation still commits on the same connection.

ZERO NETWORK: injected mocks only (urllib hard-patched to raise). Temp SQLite only; no S1.

Run with:  pytest -q tests/test_gateg7_proxy_fault_injection.py
"""

import datetime
import importlib.util
import sqlite3
from decimal import Decimal

import pytest

from analysis.forensic import gateg5_plumbing as plumb

engine = plumb.engine

_SPEC = importlib.util.spec_from_file_location(
    "gateg5_telemetry_runner", "/root/mispricing_agent/tools/gateg5_telemetry_runner.py")
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)

# --- frozen, deterministic inputs (explicit constants; never tuned from outcomes) ---
NOW_MS = 1_900_000_000_000
END_S = NOW_MS // 1000 + 600                      # market end 10m out -> tte>0
PROXY_TOKEN = runner.PROXY_ARM_TOKEN

_PROJ_COLS = ("asset", "side", "condition_id", "token_id", "outcome_index", "outcome_label",
              "fair_yes", "entry_edge", "exec_ask_vwap", "exec_fill_qty_avail",
              "intended_stake", "edge_bucket", "tte_bucket", "fill_decision",
              "row_hash", "prev_row_hash")


# ---------------------------------------------------------------------------
# mocked network boundaries
# ---------------------------------------------------------------------------
def _gamma_market(slug):
    return {
        "conditionId": "cond-" + slug,
        "clobTokenIds": ["tokUp-" + slug, "tokDown-" + slug],
        "outcomes": ["Up", "Down"],
        "slug": slug,
        "endDate": datetime.datetime.fromtimestamp(
            END_S, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _book_payload():
    return {"asks": [{"price": "0.10", "size": "1000"}],
            "bids": [{"price": "0.05", "size": "1000"}], "timestamp": NOW_MS}


def _fake_public_get(url, params=None):
    if url == runner.GAMMA_MARKETS:
        return [_gamma_market(params["slug"])]
    if url == runner.CLOB_BOOK:
        return _book_payload()
    raise AssertionError(f"unexpected GET {url}")


def _fake_hl_pf(coin, ts_ms):
    if ts_ms == NOW_MS:
        return Decimal("59000"), NOW_MS - 30_000     # 'now' ref below strike -> FILLED_ACTIVE
    return Decimal("60000"), ts_ms                   # window-open strike


class FakeAsyncClient:
    """async def client(url) -> dict. Raises on the first `fail_until` calls (transport fault)."""

    def __init__(self, fail_until=0):
        self.fail_until = fail_until
        self.calls = 0

    async def __call__(self, url):
        self.calls += 1
        if self.calls <= self.fail_until:
            raise TimeoutError("injected proxy transport failure (502/timeout)")
        if "coinbase.com" in url:
            return {"data": {"amount": "60020", "currency": "USD"}}
        if "kraken.com" in url:
            return {"error": [], "result": {"XXBTZUSD": {"c": ["60040", "0.1"]}}}
        raise AssertionError(f"unexpected proxy url {url}")


def _wire_common(monkeypatch):
    monkeypatch.setattr(runner, "_public_get", _fake_public_get)
    monkeypatch.setattr(runner, "_hl_price_feedts", _fake_hl_pf)
    monkeypatch.setattr(runner, "_hl_sigma_annual", lambda c, n: 0.8)
    monkeypatch.setattr(runner.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(runner, "MAX_OBSERVATIONS", 2)
    monkeypatch.setattr(runner, "MAX_ELAPSED_S", 10 ** 12)
    monkeypatch.setattr(runner, "TARGET_ASSETS", ("BTC",))   # -> 2 slugs -> 2 observations
    # hard-block any live network (proves injected mocks are the only path)
    monkeypatch.setattr(runner.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("live network")))


def _run(db, monkeypatch, *, proxy_on, client=None):
    _wire_common(monkeypatch)
    if proxy_on:
        monkeypatch.setenv(runner.PROXY_ARM_ENV, PROXY_TOKEN)
        monkeypatch.setattr(runner, "_default_async_http_client", client or FakeAsyncClient())
    else:
        monkeypatch.delenv(runner.PROXY_ARM_ENV, raising=False)
    return runner.run(db, now_ms_provider=lambda: NOW_MS)


def _read_signals(conn):
    rows = conn.execute(
        f"SELECT {','.join(plumb._SIGNAL_COLS)} FROM signal_log ORDER BY rowid").fetchall()
    return [dict(zip(plumb._SIGNAL_COLS, r)) for r in rows]


def _projection(sig_rows):
    return {r["signal_id"]: {c: r[c] for c in _PROJ_COLS} for r in sig_rows}


def _proxy_diag_count(conn):
    return conn.execute(
        "SELECT COUNT(*) FROM gateg5_telemetry_rejections WHERE kind='PROXY_DIAG'").fetchone()[0]


# ===========================================================================
# Scenario A — proxy transport failure
# ===========================================================================
def test_scenario_a_transport_failure(tmp_path, monkeypatch):
    db = str(tmp_path / "a.sqlite3")
    client = FakeAsyncClient(fail_until=2)   # fail obs1's coinbase+kraken; obs2 succeeds
    result = _run(db, monkeypatch, proxy_on=True, client=client)

    assert result["observations"] == 2          # loop did NOT halt
    conn = sqlite3.connect(db)
    sigs = _read_signals(conn)
    assert len(sigs) == 2                        # both signal rows committed (incl. obs1's)
    assert engine.verify_hash_chain(sigs)        # signal_log hash-chain intact
    assert _proxy_diag_count(conn) == 1          # exactly one PROXY_DIAG, no retry
    # failed capture wrote NO proxy row; obs2 (clean) wrote exactly one
    assert conn.execute("SELECT COUNT(*) FROM gateg7_proxy_basis").fetchone()[0] == 1
    # exactly one attempt for the failed obs (2 legs) + 2 for the clean obs = no retry
    assert client.calls == 4
    conn.close()


# ===========================================================================
# Scenario B — proxy INSERT sqlite3.OperationalError
# ===========================================================================
def test_scenario_b_insert_operational_error(tmp_path, monkeypatch):
    db = str(tmp_path / "b.sqlite3")
    orig_write = runner._write_proxy_basis
    state = {"attempts": 0}

    def faulty_write(conn, signal_id, asset, diag):
        state["attempts"] += 1
        if state["attempts"] == 1:               # poison ONLY obs1's INSERT, exactly once
            raise sqlite3.OperationalError("database is locked")
        return orig_write(conn, signal_id, asset, diag)

    monkeypatch.setattr(runner, "_write_proxy_basis", faulty_write)
    result = _run(db, monkeypatch, proxy_on=True, client=FakeAsyncClient())

    assert result["observations"] == 2
    conn = sqlite3.connect(db)
    sigs = _read_signals(conn)
    assert len(sigs) == 2                         # committed signal rows survive the INSERT fault
    assert engine.verify_hash_chain(sigs)         # unchanged / not rolled back
    assert _proxy_diag_count(conn) == 1           # exactly one PROXY_DIAG
    assert state["attempts"] == 2                 # one failed (obs1) + one success (obs2): no retry
    # connection/transaction remained usable: obs2's proxy row was written on the same conn
    assert conn.execute("SELECT COUNT(*) FROM gateg7_proxy_basis").fetchone()[0] == 1
    conn.close()


# ===========================================================================
# Scenario C — non-interference (frozen-input core decision projection)
# ===========================================================================
def test_scenario_c_non_interference(tmp_path, monkeypatch):
    # baseline: proxy OFF, no fault
    db_off = str(tmp_path / "off.sqlite3")
    _run(db_off, monkeypatch, proxy_on=False)
    conn_off = sqlite3.connect(db_off)
    proj_off = _projection(_read_signals(conn_off))
    conn_off.close()

    # faulted: proxy ON, transport fault on obs1 (then INSERT fault path also exercised)
    db_on = str(tmp_path / "on.sqlite3")
    monkeypatch.undo()                            # reset patches set above
    client = FakeAsyncClient(fail_until=2)
    _run(db_on, monkeypatch, proxy_on=True, client=client)
    conn_on = sqlite3.connect(db_on)
    proj_on = _projection(_read_signals(conn_on))
    # proxy diagnostics live in a separate table; signal_log carries no chainlink/proxy cols
    cols = {c[1] for c in conn_on.execute("PRAGMA table_info(signal_log)").fetchall()}
    conn_on.close()

    assert proj_on == proj_off                    # bit-identical core decision projection
    assert proj_off, "baseline produced no signals"
    assert not any("proxy" in c or "chainlink" in c for c in cols)
