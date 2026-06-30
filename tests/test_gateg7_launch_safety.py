"""
Gate G7-lite — launch-safety blockers (OFFLINE). Four scoped patches:

  1. Monotonic elapsed: the internal 7200s bound derives from an injected monotonic source;
     persisted timestamps stay UTC wall-clock ms. Wall-clock jumps must not move the stop.
  2. Graceful SIGTERM / OPERATOR_ABORT: handler sets a flag only; the loop stops at a safe
     synchronous boundary with intact hash chains; OPERATOR_ABORT never PASS; exit 124 overrides.
  3. Fresh artifact/path/PID safety: refuse existing DB/log/PID, enforce resolved /tmp + S1
     refusal, atomic PID ownership + safe cleanup, never append a new GENESIS to an existing DB.
  4. Deterministic wrapper exit code: exit-code helper preserves 0/1/124/137/143; 124 -> external.

ZERO NETWORK: injected mocks only; urllib hard-patched to raise. Temp SQLite only; no S1.
"""

import importlib.util
import os
import sqlite3
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
NOW = 1_900_000_000_000


# ---------------------------------------------------------------------------
# network-mock harness (real run() loop, no network)
# ---------------------------------------------------------------------------
def _gamma_market(slug):
    import datetime
    end_s = NOW // 1000 + 600
    return {"conditionId": "cond-" + slug, "clobTokenIds": ["tokUp-" + slug, "tokDown-" + slug],
            "outcomes": ["Up", "Down"], "slug": slug,
            "endDate": datetime.datetime.fromtimestamp(
                end_s, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def _fake_public_get(url, params=None):
    if url == runner.GAMMA_MARKETS:
        return [_gamma_market(params["slug"])]
    if url == runner.CLOB_BOOK:
        return {"asks": [{"price": "0.10", "size": "1000"}],
                "bids": [{"price": "0.05", "size": "1000"}], "timestamp": NOW}
    raise AssertionError(url)


def _wire_net(monkeypatch):
    monkeypatch.setattr(runner, "_public_get", _fake_public_get)
    monkeypatch.setattr(runner, "_hl_price_feedts",
                        lambda c, ts: (Decimal("59000"), NOW - 30_000) if ts == NOW
                        else (Decimal("60000"), ts))
    monkeypatch.setattr(runner, "_hl_sigma_annual", lambda c, n: 0.8)
    monkeypatch.setattr(runner.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(runner.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("live network")))


def _read_signals(conn):
    return [dict(zip(plumb._SIGNAL_COLS, r)) for r in
            conn.execute(f"SELECT {','.join(plumb._SIGNAL_COLS)} FROM signal_log "
                         "ORDER BY rowid").fetchall()]


# ===========================================================================
# 1. Monotonic elapsed
# ===========================================================================
def test_monotonic_elapsed_ignores_wall_clock_jumps(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "_target_slugs", lambda now_ms: iter(()))   # no markets
    monkeypatch.setattr(runner.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(runner, "MAX_ELAPSED_S", 7200)
    monkeypatch.setattr(runner, "MAX_OBSERVATIONS", 100)
    # wall clock jumps BACKWARD then FORWARD; monotonic advances normally past 7200
    wall = iter([1_000_000_000_000, 1, 9_000_000_000_000, 1])
    mono = iter([0.0, 0.0, 7300.0])

    def w():
        try:
            return next(wall)
        except StopIteration:
            return 9_000_000_000_000

    def m():
        try:
            return next(mono)
        except StopIteration:
            return 7300.0

    result = runner.run(str(tmp_path / "mono.sqlite3"), now_ms_provider=w, monotonic_provider=m)
    assert result["stop_reason"] == "MAX_ELAPSED"   # stop comes solely from monotonic elapsed
    assert result["observations"] == 0


# ===========================================================================
# 2. Graceful SIGTERM / OPERATOR_ABORT
# ===========================================================================
def test_sigterm_handler_only_sets_flag():
    runner._ABORT_REQUESTED = False
    runner._sigterm_handler(15, None)
    assert runner._ABORT_REQUESTED is True
    runner._ABORT_REQUESTED = False


def test_clean_mid_cycle_operator_abort(tmp_path, monkeypatch):
    _wire_net(monkeypatch)
    monkeypatch.setattr(runner, "MAX_OBSERVATIONS", 100)
    monkeypatch.setattr(runner, "TARGET_ASSETS", ("BTC",))     # 2 slugs/cycle
    monkeypatch.delenv(runner.PROXY_ARM_ENV, raising=False)
    calls = {"n": 0}

    def abort_check():
        calls["n"] += 1
        return calls["n"] > 2          # False at while-top + slug1; True at slug2 (after obs1)

    db = str(tmp_path / "abort.sqlite3")
    result = runner.run(db, now_ms_provider=lambda: NOW, monotonic_provider=lambda: 0.0,
                        abort_check=abort_check)
    assert result["stop_reason"] == "OPERATOR_ABORT"
    conn = sqlite3.connect(db)
    sigs = _read_signals(conn)
    assert len(sigs) == 1                                   # obs1 finished+committed
    assert engine.verify_hash_chain(sigs)                   # signal chain intact
    assert engine.verify_hash_chain(runner._marks_for(conn, sigs[0]["signal_id"]))
    assert conn.execute("SELECT COUNT(*) FROM gateg7_proxy_basis").fetchone()[0] == 0  # no partial
    conn.close()


_ASSETS = ("BTC", "SOL", "ETH", "XRP")


def _clf(**over):
    base = dict(external_exit_code=None, external_terminated=False, stop_reason="MAX_OBSERVATIONS",
                signal_chain_ok=True, mark_chain_ok=True, proxy_accounting_ok=True,
                unexpected_count=0, core_isolation_ok=True, target_assets=_ASSETS,
                covered_assets=_ASSETS)
    base.update(over)
    return pre.classify_terminal(**base)


def test_classify_operator_abort_alone():
    assert _clf(stop_reason="OPERATOR_ABORT") == pre.OPERATOR_ABORT


def test_classify_operator_abort_never_pass():
    assert _clf(stop_reason="OPERATOR_ABORT") != pre.MECHANICAL_PASS


def test_classify_operator_abort_plus_integrity_is_mechanical_fail():
    assert _clf(stop_reason="OPERATOR_ABORT", signal_chain_ok=False) == pre.MECHANICAL_FAIL


def test_classify_operator_abort_plus_external_is_timeout():
    assert _clf(stop_reason="OPERATOR_ABORT", external_exit_code=124) == pre.EXTERNAL_TIMEOUT_FAIL


# ===========================================================================
# 3. Fresh artifact / path / PID safety
# ===========================================================================
def test_refuse_existing_db(tmp_path):
    db = tmp_path / "exists.sqlite3"
    db.write_text("preexisting")
    with pytest.raises(FileExistsError):
        runner.run(str(db))


def test_refuse_non_tmp_path():
    with pytest.raises(PermissionError):
        runner.run("/root/not_tmp.sqlite3")


def test_refuse_s1_path():
    with pytest.raises(PermissionError):
        runner.run("/root/mispricing_agent/var/s1/x.sqlite3")


def test_refuse_symlink_escape(tmp_path):
    target = tmp_path / "outside"          # we will point a /tmp symlink at a non-/tmp dir
    link = tmp_path / "link"
    os.symlink("/root", str(link))
    with pytest.raises(PermissionError):
        runner.run(str(link / "x.sqlite3"))


def test_refuse_existing_pid(tmp_path):
    db = str(tmp_path / "fresh.sqlite3")
    pid = tmp_path / "run.pid"
    pid.write_text("99999")
    with pytest.raises(FileExistsError):
        runner.run(db, pid_path=str(pid))


def test_claim_pid_writes_own_pid(tmp_path):
    pid = str(tmp_path / "claim.pid")
    runner._claim_pid(pid)
    assert open(pid).read().strip() == str(os.getpid())


def test_release_pid_only_when_owned(tmp_path):
    own = tmp_path / "own.pid"
    own.write_text(str(os.getpid()))
    runner._release_pid_if_owned(str(own))
    assert not own.exists()                       # owned -> removed
    foreign = tmp_path / "foreign.pid"
    foreign.write_text("123456")
    runner._release_pid_if_owned(str(foreign))
    assert foreign.exists()                       # foreign -> preserved as evidence


def test_normal_run_claims_and_releases_pid(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "MAX_OBSERVATIONS", 0)        # stop immediately, no network
    db = str(tmp_path / "n.sqlite3")
    pid = str(tmp_path / "n.pid")
    runner.run(db, pid_path=pid, now_ms_provider=lambda: NOW, monotonic_provider=lambda: 0.0)
    assert not os.path.exists(pid)                # released on normal stop


def test_graceful_abort_releases_pid(tmp_path):
    db = str(tmp_path / "ga.sqlite3")
    pid = str(tmp_path / "ga.pid")
    runner.run(db, pid_path=pid, abort_check=lambda: True,
               now_ms_provider=lambda: NOW, monotonic_provider=lambda: 0.0)
    assert not os.path.exists(pid)


def test_claim_exclusive_refuses_existing(tmp_path):
    p = tmp_path / "log"
    p.write_text("x")
    with pytest.raises(FileExistsError):
        runner._claim_exclusive(str(p))


def test_legacy_migration_still_works_offline(tmp_path):
    # live fresh-run refusal must NOT break offline/audit legacy-schema migration
    db = str(tmp_path / "legacy.sqlite3")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE gateg5_telemetry_rejections("
                 " id INTEGER PRIMARY KEY, ts_ms INTEGER, kind TEXT, reason TEXT, payload_digest TEXT)")
    conn.commit()
    runner._init_telemetry_tables(conn)            # migration path intact (called outside run())
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gateg5_telemetry_rejections)").fetchall()}
    assert "signal_id" in cols
    conn.close()


# ===========================================================================
# 4. Deterministic wrapper exit code
# ===========================================================================
@pytest.mark.parametrize("code", [0, 1, 124, 137, 143])
def test_exit_code_record_read_preserved(tmp_path, code):
    p = str(tmp_path / "rc")
    pre.record_exit_code(p, code)
    assert pre.read_exit_code(p) == code           # exact preservation; 124 never becomes 0


def test_is_external_termination():
    assert pre.is_external_termination(124)
    assert pre.is_external_termination(137) and pre.is_external_termination(143)
    assert not pre.is_external_termination(0) and not pre.is_external_termination(1)


def test_exit124_plus_operator_abort_classifies_external():
    out = pre.classify_terminal(
        external_exit_code=124, external_terminated=pre.is_external_termination(124),
        stop_reason="OPERATOR_ABORT", signal_chain_ok=True, mark_chain_ok=True,
        proxy_accounting_ok=True, unexpected_count=0, core_isolation_ok=True,
        target_assets=_ASSETS, covered_assets=_ASSETS)
    assert out == pre.EXTERNAL_TIMEOUT_FAIL


# ===========================================================================
# core-decision projection unchanged by the launch-safety patches
# ===========================================================================
def test_core_projection_unchanged(monkeypatch):
    monkeypatch.setattr(runner, "_hl_price_feedts",
                        lambda c, ts: (Decimal("59000"), NOW - 30_000) if ts == NOW
                        else (Decimal("60000"), ts))
    monkeypatch.setattr(runner, "_hl_sigma_annual", lambda c, n: 0.8)
    market = dict(asset="BTC", side="NO", condition_id="c1", token_id="tokDown",
                  outcome_index=1, outcome_label="Down", slug="btc-updown-15m-1",
                  market_end_ts=NOW // 1000 + 600, clobTokenIds=["tokUp", "tokDown"],
                  outcomes=["Up", "Down"])
    book = {"asks": [["0.10", "1000"]], "bids": [["0.05", "1000"]], "quote_ts_ms": NOW - 100}
    ns = plumb.normalize_signal(market, book, runner._model_context("BTC", market, book, NOW),
                                capture_ts_ms=NOW)
    proj = runner.core_decision_projection(ns)
    assert proj["fill_decision"] == "FILLED_ACTIVE" and proj["side"] == "NO"
