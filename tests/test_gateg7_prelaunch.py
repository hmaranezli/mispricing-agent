"""
Gate G7-lite — pre-launch observability / accounting / classification tooling (OFFLINE).

  * Request-attempt counters (counted immediately before each network call; failed attempts
    count once; no retry; never influence the core decision path; persisted to a SEPARATE
    additive table with failure-isolated writes).
  * Pure terminal classifier (MECHANICAL_PASS / INSUFFICIENT_PROXY_COVERAGE / MECHANICAL_FAIL
    / EXTERNAL_TIMEOUT_FAIL).
  * Pure proxy-accounting auditor (exactly one proxy row XOR one PROXY_DIAG per committed signal).
  * Pure heartbeat-staleness classifier (stale threshold 420s; HEARTBEAT_EVERY_S=300).
  * Truthful dynamic banner + import-time GATEG5_MAX_ELAPSED_S enforcement.

ZERO NETWORK: urllib hard-patched / injected mocks only. Temp SQLite only; no S1.

Run with:  pytest -q tests/test_gateg7_prelaunch.py
"""

import asyncio
import importlib.util
import sqlite3
import urllib.error
from decimal import Decimal

import pytest

from analysis.forensic import gateg5_plumbing as plumb
from analysis.forensic import gateg7_prelaunch as pre

engine = plumb.engine
RUNNER_PATH = "/root/mispricing_agent/tools/gateg5_telemetry_runner.py"


def _load_runner(name="gateg5_telemetry_runner"):
    spec = importlib.util.spec_from_file_location(name, RUNNER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


runner = _load_runner()


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------
class _FakeResp:
    def __init__(self, body: bytes):
        self._b = body

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _ok_urlopen(body: bytes):
    return lambda req, timeout=None: _FakeResp(body)


class FakeAsyncClient:
    def __init__(self):
        self.calls = 0

    async def __call__(self, url):
        self.calls += 1
        if "coinbase.com" in url:
            return {"data": {"amount": "60020", "currency": "USD"}}
        if "kraken.com" in url:
            return {"error": [], "result": {"XXBTZUSD": {"c": ["60040", "0.1"]}}}
        raise AssertionError(url)


def _reset_counters(mod=runner):
    mod._REQUEST_COUNTERS = pre.RequestCounters()
    return mod._REQUEST_COUNTERS


# ===========================================================================
# 1. Request-attempt counters
# ===========================================================================
def test_gamma_counter_increments_once(monkeypatch):
    c = _reset_counters()
    monkeypatch.setattr(runner.urllib.request, "urlopen", _ok_urlopen(b"[]"))
    runner._public_get(runner.GAMMA_MARKETS, {"slug": "x"})
    assert c.gamma_get_attempts == 1
    assert c.clob_book_get_attempts == 0 and c.hl_post_attempts == 0


def test_book_counter_increments_once(monkeypatch):
    c = _reset_counters()
    monkeypatch.setattr(runner.urllib.request, "urlopen", _ok_urlopen(b'{"asks":[],"bids":[]}'))
    runner._public_get(runner.CLOB_BOOK, {"token_id": "t"})
    assert c.clob_book_get_attempts == 1 and c.gamma_get_attempts == 0


def test_hl_counter_increments_once(monkeypatch):
    c = _reset_counters()
    monkeypatch.setattr(runner.urllib.request, "urlopen", _ok_urlopen(b"{}"))
    runner._hl_post({"type": "candleSnapshot"})
    assert c.hl_post_attempts == 1


def test_proxy_leg_counters_increment_once():
    c = _reset_counters()
    asyncio.run(runner._capture_proxy_legs("BTC", client=FakeAsyncClient()))
    assert c.coinbase_get_attempts == 1 and c.kraken_get_attempts == 1


def test_failed_attempt_counts_once_no_retry(monkeypatch):
    c = _reset_counters()

    def _boom(req, timeout=None):
        raise urllib.error.URLError("injected")

    monkeypatch.setattr(runner.urllib.request, "urlopen", _boom)
    with pytest.raises(runner.TransportError):
        runner._public_get(runner.GAMMA_MARKETS, {"slug": "x"})
    assert c.gamma_get_attempts == 1            # counted once, even though it failed; no retry


def test_proxy_off_zero_proxy_attempts():
    c = _reset_counters()
    out = runner.proxy_context("BTC", "60000", 1000, enabled=False,
                               client=FakeAsyncClient(), clock=lambda: 1,
                               spread_bps_threshold="50")
    assert out is None
    assert c.coinbase_get_attempts == 0 and c.kraken_get_attempts == 0


def test_counters_do_not_alter_core_projection(monkeypatch):
    now = 1_900_000_000_000

    def fake_pf(coin, ts_ms):
        return (Decimal("59000"), now - 30_000) if ts_ms == now else (Decimal("60000"), ts_ms)

    monkeypatch.setattr(runner, "_hl_price_feedts", fake_pf)
    monkeypatch.setattr(runner, "_hl_sigma_annual", lambda c, n: 0.8)
    market = dict(asset="BTC", side="NO", condition_id="c1", token_id="tokDown",
                  outcome_index=1, outcome_label="Down", slug="btc-updown-15m-1",
                  market_end_ts=now // 1000 + 600, clobTokenIds=["tokUp", "tokDown"],
                  outcomes=["Up", "Down"])
    book = {"asks": [["0.10", "1000"]], "bids": [["0.05", "1000"]], "quote_ts_ms": now - 100}

    _reset_counters()
    ns1 = plumb.normalize_signal(market, book, runner._model_context("BTC", market, book, now),
                                 capture_ts_ms=now)
    proj1 = runner.core_decision_projection(ns1)
    # bump every counter; recompute identical frozen inputs
    runner._REQUEST_COUNTERS.gamma_get_attempts += 99
    runner._REQUEST_COUNTERS.coinbase_get_attempts += 99
    ns2 = plumb.normalize_signal(market, book, runner._model_context("BTC", market, book, now),
                                 capture_ts_ms=now)
    assert runner.core_decision_projection(ns2) == proj1


# ===========================================================================
# 1b. Counter persistence — separate additive table, failure-isolated
# ===========================================================================
def test_counters_snapshot_persisted(tmp_path):
    db = str(tmp_path / "ctr.sqlite3")
    conn = sqlite3.connect(db)
    runner._init_counters_table(conn)
    _reset_counters()
    runner._REQUEST_COUNTERS.gamma_get_attempts = 7
    runner._write_counters_snapshot(conn, "final", observations=3, now_ms=123)
    row = conn.execute(
        "SELECT note, gamma_get_attempts, observations FROM gateg5_request_counters").fetchone()
    assert row == ("final", 7, 3)
    conn.close()


def test_counters_snapshot_failure_isolated():
    class _BrokenConn:
        def execute(self, *a, **k):
            raise sqlite3.OperationalError("boom")

        def commit(self):
            raise sqlite3.OperationalError("boom")

    _reset_counters()
    # must NOT raise — counter persistence failure cannot halt the telemetry path
    runner._write_counters_snapshot(_BrokenConn(), "final", observations=0, now_ms=0)


# ===========================================================================
# 2. Pure terminal classifier
# ===========================================================================
_ASSETS = ("BTC", "SOL", "ETH", "XRP")


def _clf(**over):
    base = dict(external_exit_code=None, external_terminated=False, stop_reason="MAX_OBSERVATIONS",
                signal_chain_ok=True, mark_chain_ok=True, proxy_accounting_ok=True,
                unexpected_count=0, core_isolation_ok=True, target_assets=_ASSETS,
                covered_assets=_ASSETS)
    base.update(over)
    return pre.classify_terminal(**base)


def test_classify_mechanical_pass():
    assert _clf() == pre.MECHANICAL_PASS


def test_classify_insufficient_proxy_coverage():
    assert _clf(covered_assets=("BTC", "SOL", "ETH")) == pre.INSUFFICIENT_PROXY_COVERAGE


def test_classify_mechanical_fail_hashchain():
    assert _clf(signal_chain_ok=False) == pre.MECHANICAL_FAIL
    assert _clf(mark_chain_ok=False) == pre.MECHANICAL_FAIL


def test_classify_mechanical_fail_accounting_unexpected_isolation():
    assert _clf(proxy_accounting_ok=False) == pre.MECHANICAL_FAIL
    assert _clf(unexpected_count=1) == pre.MECHANICAL_FAIL
    assert _clf(core_isolation_ok=False) == pre.MECHANICAL_FAIL


def test_classify_external_timeout_fail_priority():
    assert _clf(external_exit_code=124) == pre.EXTERNAL_TIMEOUT_FAIL
    assert _clf(external_terminated=True) == pre.EXTERNAL_TIMEOUT_FAIL
    # external timeout outranks even integrity failures (never PASS)
    assert _clf(external_exit_code=124, signal_chain_ok=False) == pre.EXTERNAL_TIMEOUT_FAIL


def test_classify_abnormal_stop_is_mechanical_fail():
    assert _clf(stop_reason="UNSET") == pre.MECHANICAL_FAIL


# ===========================================================================
# 3. Pure proxy accounting
# ===========================================================================
def test_accounting_pass():
    r = pre.audit_proxy_accounting(["s1", "s2", "s3"], ["s1", "s2"], ["s3"])
    assert r["ok"] is True


def test_accounting_missing():
    r = pre.audit_proxy_accounting(["s1", "s2"], ["s1"], [])
    assert r["ok"] is False and r["missing"] == ["s2"]


def test_accounting_duplicate_row():
    r = pre.audit_proxy_accounting(["s1"], ["s1", "s1"], [])
    assert r["ok"] is False and r["duplicate_rows"] == ["s1"]


def test_accounting_multi_diag():
    r = pre.audit_proxy_accounting(["s1"], [], ["s1", "s1"])
    assert r["ok"] is False and r["multi_diag"] == ["s1"]


def test_accounting_orphan_row():
    r = pre.audit_proxy_accounting(["s1"], ["s1", "ghost"], [])
    assert r["ok"] is False and r["orphan_rows"] == ["ghost"]


def test_accounting_double_counted_row_and_diag():
    r = pre.audit_proxy_accounting(["s1"], ["s1"], ["s1"])
    assert r["ok"] is False and r["double_counted"] == ["s1"]


def test_proxy_accounting_reader_roundtrip(tmp_path, monkeypatch):
    db = str(tmp_path / "acct.sqlite3")
    conn = sqlite3.connect(db)
    plumb.init_mock_db(conn)
    runner._init_proxy_table(conn)
    runner._init_telemetry_tables(conn)
    now = 1_900_000_000_000

    def fake_pf(coin, ts_ms):
        return (Decimal("59000"), now - 30_000) if ts_ms == now else (Decimal("60000"), ts_ms)

    monkeypatch.setattr(runner, "_hl_price_feedts", fake_pf)
    monkeypatch.setattr(runner, "_hl_sigma_annual", lambda c, n: 0.8)
    # signal A -> a proxy row; signal B -> a PROXY_DIAG (carrying its signal_id)
    for tok in ("tokDownA", "tokDownB"):
        market = dict(asset="BTC", side="NO", condition_id="c-" + tok, token_id=tok,
                      outcome_index=1, outcome_label="Down", slug="btc-updown-15m-1",
                      market_end_ts=now // 1000 + 600, clobTokenIds=["tokUp", tok],
                      outcomes=["Up", "Down"])
        book = {"asks": [["0.10", "1000"]], "bids": [["0.05", "1000"]], "quote_ts_ms": now - 100}
        ns = plumb.normalize_signal(market, book, runner._model_context("BTC", market, book, now),
                                    capture_ts_ms=now)
        plumb.write_signal(conn, ns, prev_hash="GENESIS")
        if tok == "tokDownA":
            diag = runner.g7.compute_post_signal_proxy_diagnostic(
                hl_reference_price="60010", ts_signal_ms=now, coinbase="60020", kraken="60040",
                capture_started_ts_ms=now + 1, capture_completed_ts_ms=now + 2,
                spread_bps_threshold="50")
            runner._write_proxy_basis(conn, ns.signal.signal_id, "BTC", diag)
        else:
            runner._record_rejection(conn, "PROXY_DIAG", "boom", now, digest=ns.signal.signal_id)
    conn.commit()
    r = runner.read_proxy_accounting(conn)
    assert r["ok"] is True
    conn.close()


# ===========================================================================
# 4. Heartbeat staleness classifier
# ===========================================================================
def test_heartbeat_below_threshold_healthy():
    r = pre.classify_heartbeat(pid_alive=True, last_heartbeat_ts_ms=0, now_ts_ms=419_000)
    assert r["status"] == pre.HEALTHY_OR_NOT_RUNNING and r["heartbeat_age_ms"] == 419_000


def test_heartbeat_equal_threshold_healthy():
    r = pre.classify_heartbeat(pid_alive=True, last_heartbeat_ts_ms=0, now_ts_ms=420_000)
    assert r["status"] == pre.HEALTHY_OR_NOT_RUNNING       # age == threshold is not > threshold


def test_heartbeat_above_threshold_stuck():
    r = pre.classify_heartbeat(pid_alive=True, last_heartbeat_ts_ms=0, now_ts_ms=420_001)
    assert r["status"] == pre.STUCK_OR_BLOCKED_PROCESS
    assert r["stale_threshold_ms"] == 420_000


def test_heartbeat_pid_dead_never_stuck():
    r = pre.classify_heartbeat(pid_alive=False, last_heartbeat_ts_ms=0, now_ts_ms=10 ** 9)
    assert r["status"] == pre.HEALTHY_OR_NOT_RUNNING


# ===========================================================================
# 5. Dynamic banner + 6. env override enforcement
# ===========================================================================
def test_banner_reports_actual_bounds(monkeypatch):
    monkeypatch.setattr(runner, "MAX_OBSERVATIONS", 100)
    monkeypatch.setattr(runner, "MAX_ELAPSED_S", 7200)
    b = runner._banner()
    assert "100" in b and "7200" in b
    assert "6h" not in b                       # no hardcoded 6h
    assert "2.0" in b or "2.00" in b           # readable hours of 7200s


def test_env_override_uses_7200(monkeypatch):
    monkeypatch.setenv("GATEG5_MAX_ELAPSED_S", "7200")
    m = _load_runner("g7_runner_7200")
    assert m.MAX_ELAPSED_S == 7200
    assert "7200" in m._banner() and "21600" not in m._banner()


def test_default_without_env_is_6h(monkeypatch):
    monkeypatch.delenv("GATEG5_MAX_ELAPSED_S", raising=False)
    m = _load_runner("g7_runner_default")
    assert m.MAX_ELAPSED_S == 21600


def test_runner_stops_on_overridden_elapsed(tmp_path, monkeypatch):
    monkeypatch.setenv("GATEG5_MAX_ELAPSED_S", "7200")
    m = _load_runner("g7_runner_stop")
    monkeypatch.setattr(m, "_target_slugs", lambda now_ms: iter(()))   # no markets
    monkeypatch.setattr(m.time, "sleep", lambda *a, **k: None)
    times = iter([0, 7_300_000, 7_300_000, 7_300_000, 7_300_000])
    result = m.run(str(tmp_path / "stop.sqlite3"), now_ms_provider=lambda: next(times))
    assert result["stop_reason"] == "MAX_ELAPSED"
    assert result["observations"] == 0


# ===========================================================================
# 7. zero live network for pure tooling
# ===========================================================================
def test_pure_tooling_makes_no_network(monkeypatch):
    monkeypatch.setattr(runner.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("live network")))
    # pure classifiers/auditor never touch the network
    assert _clf() == pre.MECHANICAL_PASS
    assert pre.audit_proxy_accounting(["s1"], ["s1"], [])["ok"] is True
    assert pre.classify_heartbeat(pid_alive=True, last_heartbeat_ts_ms=0,
                                  now_ts_ms=1)["status"] == pre.HEALTHY_OR_NOT_RUNNING
