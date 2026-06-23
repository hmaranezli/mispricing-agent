"""RED→GREEN tests for the ratified Post-Phase 6.2 Bounded 24h Run Execution-Wiring TDD Charter
(``docs/handoff/post_phase6_2_bounded_24h_run_execution_wiring_tdd_charter.md``).

Boundary: ZERO real network. The HTTPS transport, clock, sleep, and wall-clock are all dependency-injected
fakes. The continuous ledger sink is created only under ``tmp_path`` (never ``/root/...run_001``). No S1
append, no ``s1_audit.sqlite3``, no real 24h run. The wiring only connects the RATIFIED pure scheduler to
real capture adapters + an append-only continuous ledger + a thin runner.
"""
import hashlib
import os
import sqlite3
import stat
import unittest.mock
import urllib.request

import pytest

from phase6_2_shadow_intent import bounded_24h_run_execution_wiring as wiring
from phase6_2_shadow_intent import continuous_raw_collection_scheduler as sched
from phase6_2_shadow_intent import s1_production_ingestion_adapter as adapter


_HL_BODY = b'{"coin":"BTC","time":1782189645000,"levels":[[],[]]}'
_PM_BODY = b'{"market":"0x","timestamp":"1782189645000"}'


def _transport(hl_status=200, pm_status=200, hl_body=_HL_BODY, pm_body=_PM_BODY):
    calls = []

    def transport(method, url, body):
        calls.append((method, url, body))
        if "api.hyperliquid.xyz" in url:
            return (hl_status, hl_body, 10, 20, 5)
        return (pm_status, pm_body, 11, 21, 6)

    return transport, calls


def _bounded_clock(now, run_cycles):
    state = {"n": 0}

    def clock():
        state["n"] += 1
        return now if state["n"] <= run_cycles else now + 10 ** 9

    return clock


def _wall_clock(values=(1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000)):
    it = iter(values)
    return lambda: next(it)


def _no_sleep():
    return lambda seconds: None


def _run_dir(tmp_path, name="run_001"):
    return str(tmp_path / name)


def _reason(excinfo):
    return excinfo.value.reason


# --- Group A: capture adapter interface ----------------------------------------------------------

def test_hyperliquid_capture_returns_outcome():
    transport, _ = _transport()
    ew = wiring.ExecutionWiring(sink=None, transport=transport)
    outcome = ew.hyperliquid_capture(sched.HYPERLIQUID_LEG)
    assert isinstance(outcome, sched.CaptureOutcome)
    assert outcome.source_authority == "HYPERLIQUID_L2_BOOK_BY_COIN_V1"
    assert outcome.method == "POST"
    assert outcome.request_target == "/info"
    assert outcome.response_body == _HL_BODY


def test_polymarket_capture_returns_outcome():
    transport, _ = _transport()
    ew = wiring.ExecutionWiring(sink=None, transport=transport)
    outcome = ew.polymarket_capture(sched.POLYMARKET_LEG)
    assert outcome.source_authority == "POLYMARKET_CLOB_BOOK_BY_TOKEN_V1"
    assert outcome.method == "GET"
    assert outcome.response_body == _PM_BODY


def test_sha256_computed_over_raw_bytes():
    transport, _ = _transport()
    ew = wiring.ExecutionWiring(sink=None, transport=transport)
    outcome = ew.hyperliquid_capture(sched.HYPERLIQUID_LEG)
    assert outcome.response_body_sha256 == hashlib.sha256(_HL_BODY).hexdigest()


def test_retrieval_timings_carried_as_forensic():
    transport, _ = _transport()
    ew = wiring.ExecutionWiring(sink=None, transport=transport)
    outcome = ew.polymarket_capture(sched.POLYMARKET_LEG)
    assert outcome.retrieval_started_epoch_ms == 11
    assert outcome.retrieval_completed_epoch_ms == 21
    assert outcome.retrieval_elapsed_monotonic_ns == 6


def test_capture_rejects_leg_mismatch():
    transport, _ = _transport()
    ew = wiring.ExecutionWiring(sink=None, transport=transport)
    with pytest.raises(wiring.ExecutionWiringError) as e:
        ew.hyperliquid_capture(sched.POLYMARKET_LEG)  # wrong leg for the HL adapter
    assert _reason(e) == "WIRING_LEG_MISMATCH"


def test_capture_rejects_private_endpoint_leg():
    transport, _ = _transport()
    ew = wiring.ExecutionWiring(sink=None, transport=transport)
    private = sched.LegTarget(
        source_authority="POLYMARKET_CLOB_BOOK_BY_TOKEN_V1", method="GET", scheme="https",
        host="clob.polymarket.com", request_target="/auth/balance", request_body=b"")
    with pytest.raises(sched.SchedulerError) as e:
        ew.polymarket_capture(private)
    assert _reason(e) == "SCHED_PRIVATE_ENDPOINT_FORBIDDEN"


def test_capture_does_not_invoke_network_on_import():
    # importing the module + constructing wiring must not have called the real transport.
    transport, calls = _transport()
    wiring.ExecutionWiring(sink=None, transport=transport)
    assert calls == []


# --- Group B: continuous ledger sink -------------------------------------------------------------

def test_sink_creates_fresh_dir_mode_0700(tmp_path):
    sink = wiring.ContinuousLedgerSink(_run_dir(tmp_path))
    mode = stat.S_IMODE(os.stat(sink.run_directory).st_mode)
    assert mode == 0o700
    sink.close()


def test_sink_db_mode_0600(tmp_path):
    sink = wiring.ContinuousLedgerSink(_run_dir(tmp_path))
    mode = stat.S_IMODE(os.stat(sink.ledger_path).st_mode)
    assert mode == 0o600
    sink.close()


def test_sink_rejects_existing_dir(tmp_path):
    path = _run_dir(tmp_path)
    os.makedirs(path)
    with pytest.raises(wiring.ExecutionWiringError) as e:
        wiring.ContinuousLedgerSink(path)
    assert _reason(e) == "WIRING_RUN_DIR_EXISTS"


def test_sink_rejects_oneshot_proof_path():
    with pytest.raises(wiring.ExecutionWiringError) as e:
        wiring.ContinuousLedgerSink("/root/mispricing_l2book_runtime_evidence")
    assert _reason(e) == "WIRING_FORBIDDEN_RUN_PATH"


def test_sink_rejects_s1_audit_path(tmp_path):
    with pytest.raises(wiring.ExecutionWiringError) as e:
        wiring.ContinuousLedgerSink(str(tmp_path / "s1_audit.sqlite3"))
    assert _reason(e) == "WIRING_FORBIDDEN_RUN_PATH"


def _full_row(**over):
    row = dict(
        cycle_id="CYCLE-000000", source_authority="HYPERLIQUID_L2_BOOK_BY_COIN_V1",
        method="POST", scheme="https", host="api.hyperliquid.xyz", request_target="/info",
        request_body=b'{"type":"l2Book","coin":"BTC"}', http_status=200,
        response_body=_HL_BODY, response_body_sha256=hashlib.sha256(_HL_BODY).hexdigest(),
        byte_length=len(_HL_BODY), retrieval_started_epoch_ms=10,
        retrieval_completed_epoch_ms=20, retrieval_elapsed_monotonic_ns=5, clock_anomaly_evidence=0)
    row.update(over)
    return row


def test_sink_records_all_mandatory_fields(tmp_path):
    sink = wiring.ContinuousLedgerSink(_run_dir(tmp_path))
    cid = sink.record_capture(_full_row())
    assert cid == 1
    got = sink._conn.execute(
        "SELECT cycle_id, source_authority, method, request_target, http_status,"
        " response_body, response_body_sha256, clock_anomaly_evidence"
        " FROM continuous_raw_capture WHERE capture_sequence=1").fetchone()
    assert got[0] == "CYCLE-000000"
    assert got[5] == _HL_BODY
    assert got[7] == 0
    sink.close()


def test_sink_is_append_only(tmp_path):
    sink = wiring.ContinuousLedgerSink(_run_dir(tmp_path))
    sink.record_capture(_full_row())
    sink.close()
    conn = sqlite3.connect(sink.ledger_path)
    with pytest.raises(sqlite3.Error):
        conn.execute("UPDATE continuous_raw_capture SET http_status=500")
    with pytest.raises(sqlite3.Error):
        conn.execute("DELETE FROM continuous_raw_capture")
    conn.close()


def test_sink_rejects_malformed_row(tmp_path):
    sink = wiring.ContinuousLedgerSink(_run_dir(tmp_path))
    with pytest.raises(wiring.ExecutionWiringError) as e:
        sink.record_capture({"cycle_id": "CYCLE-000000"})  # missing mandatory fields
    assert _reason(e) == "WIRING_MALFORMED_LEDGER_ROW"
    sink.close()


def test_sink_creates_only_its_own_ledger(tmp_path):
    sink = wiring.ContinuousLedgerSink(_run_dir(tmp_path))
    sink.close()
    names = os.listdir(sink.run_directory)
    assert "s1_audit.sqlite3" not in names
    assert any(n.startswith("raw_capture.sqlite3") for n in names)


# --- Group C: runner wiring ----------------------------------------------------------------------

def _smoke(tmp_path, *, run_cycles=2, transport=None, marker=None, name="run_001"):
    transport = transport or _transport()[0]
    return wiring.run_bounded_24h_collection(
        run_directory=_run_dir(tmp_path, name),
        authorization_marker=wiring.EXPECTED_AUTHORIZATION_MARKER if marker is None else marker,
        transport=transport,
        clock=_bounded_clock(1_000_000, run_cycles),
        sleep=_no_sleep(),
        wall_clock=_wall_clock(),
        now_epoch_seconds=1_000_000)


def test_runner_refuses_wrong_authorization(tmp_path):
    with pytest.raises(wiring.ExecutionWiringError) as e:
        _smoke(tmp_path, marker="WRONG")
    assert _reason(e) == "WIRING_AUTHORIZATION_MISMATCH"


def test_runner_refuses_existing_dir(tmp_path):
    os.makedirs(_run_dir(tmp_path))
    with pytest.raises(wiring.ExecutionWiringError) as e:
        _smoke(tmp_path)
    assert _reason(e) == "WIRING_RUN_DIR_EXISTS"


def test_runner_refuses_s1_audit_path(tmp_path):
    with pytest.raises(wiring.ExecutionWiringError) as e:
        _smoke(tmp_path, name="s1_audit.sqlite3")
    assert _reason(e) == "WIRING_FORBIDDEN_RUN_PATH"


def test_runner_enforces_charter_bounds():
    assert wiring.MAX_CYCLES == 8640
    assert wiring.SLEEP_INTERVAL_SECONDS == 10
    assert wiring.MAX_DURATION_SECONDS == 86400
    assert wiring.FAILURE_BUDGET == 100


def test_runner_smoke_writes_rows(tmp_path):
    report = _smoke(tmp_path, run_cycles=2)
    assert report.total_cycles_run == 2
    assert report.paired_complete == 2
    # 2 cycles * 2 legs = 4 rows persisted in the continuous ledger
    conn = sqlite3.connect(report.ledger_path)
    assert conn.execute("SELECT COUNT(*) FROM continuous_raw_capture").fetchone()[0] == 4
    conn.close()


def test_runner_uses_injected_transport_not_real_network(tmp_path):
    transport, calls = _transport()
    _smoke(tmp_path, transport=transport, run_cycles=2)
    assert len(calls) == 4  # 2 cycles * 2 legs, all via the injected fake transport


# --- Group D: no-S1 firewall ---------------------------------------------------------------------

def test_no_s1_audit_created(tmp_path):
    report = _smoke(tmp_path, run_cycles=2)
    assert "s1_audit.sqlite3" not in os.listdir(report.run_directory)
    assert report.no_s1_write_verified is True


def test_runner_never_invokes_s1_adapter(tmp_path, monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(adapter, "ingest_paired_s1_projection",
                        lambda **k: calls.__setitem__("n", calls["n"] + 1))
    _smoke(tmp_path, run_cycles=2)
    assert calls["n"] == 0


def test_report_is_dry_run_only(tmp_path):
    report = _smoke(tmp_path, run_cycles=2)
    assert report.paired_complete == 2
    assert not hasattr(report, "s1_written")


# --- Group E: stop / failure / reporting ---------------------------------------------------------

def test_non_2xx_leg_never_projects_and_counts_failure(tmp_path):
    transport, _ = _transport(hl_status=503)
    report = _smoke(tmp_path, transport=transport, run_cycles=2)
    assert report.paired_complete == 0
    assert report.failed_cycles == 2
    assert report.hyperliquid_committed == 0
    assert report.polymarket_committed == 2


def test_failure_budget_exceeded_fails_closed(tmp_path):
    transport, _ = _transport(hl_status=500, pm_status=500)
    # both legs fail every cycle; budget 100 -> exceeds after 101 cycles within max_cycles.
    with pytest.raises(sched.SchedulerError) as e:
        wiring.run_bounded_24h_collection(
            run_directory=_run_dir(tmp_path), authorization_marker=wiring.EXPECTED_AUTHORIZATION_MARKER,
            transport=transport, clock=_bounded_clock(1_000_000, 10_000), sleep=_no_sleep(),
            wall_clock=lambda: 1000, now_epoch_seconds=1_000_000)
    assert _reason(e) == "SCHED_FAILURE_BUDGET_EXCEEDED"


def test_stop_reason_recorded(tmp_path):
    report = _smoke(tmp_path, run_cycles=2)
    assert report.stop_reason in ("STOP_TIME", "MAX_CYCLES")


def test_report_has_required_fields(tmp_path):
    report = _smoke(tmp_path, run_cycles=2)
    for field in ("elapsed_seconds", "total_cycles_run", "hyperliquid_committed",
                  "polymarket_committed", "paired_complete", "failed_cycles",
                  "failure_budget_remaining", "ledger_path", "stop_reason",
                  "no_s1_write_verified"):
        assert hasattr(report, field)


def test_report_has_no_raw_body_fields(tmp_path):
    report = _smoke(tmp_path, run_cycles=2)
    for name in report.__dataclass_fields__:
        value = getattr(report, name)
        assert not isinstance(value, (bytes, bytearray))


# --- Group F: capacity / actionability firewall --------------------------------------------------

def test_capacity_is_zero():
    assert wiring.CAPACITY == 0


def test_no_trading_or_actionability_api():
    for banned in ("trade", "order", "place_order", "balance", "position", "calibrate",
                   "paper", "live", "signal", "rank", "edge"):
        assert not hasattr(wiring, banned)


# --- Group H: https_transport per-leg header correctness (header-correctness amendment) ----------

_HL_TRANSPORT_URL = "https://api.hyperliquid.xyz/info"
_HL_TRANSPORT_BODY = b'{"type":"l2Book","coin":"BTC"}'
_POLY_TRANSPORT_URL = (
    "https://clob.polymarket.com/book?token_id="
    "13433573766910980267981622064090484781359464703732825845886677588040916221533"
)


def _fake_urlopen(captured, status=200, body=b'{"ok":true}'):
    """Returns a fake urlopen callable that records the Request object and acts as a context mgr."""
    mock_resp = unittest.mock.MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s  # context manager returns itself (as urlopen does)
    mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)

    def _open(req, timeout=None):
        captured.append(req)
        return mock_resp

    return _open


def test_hl_post_request_carries_accept_header():
    captured = []
    with unittest.mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen(captured)):
        wiring.https_transport("POST", _HL_TRANSPORT_URL, _HL_TRANSPORT_BODY)
    assert captured[0].get_header("Accept") == "application/json"


def test_hl_post_request_carries_content_type_header():
    captured = []
    with unittest.mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen(captured)):
        wiring.https_transport("POST", _HL_TRANSPORT_URL, _HL_TRANSPORT_BODY)
    # urllib.request.Request normalises Content-Type to Content-type via .capitalize()
    assert captured[0].get_header("Content-type") == "application/json"


def test_poly_get_request_carries_accept_header():
    captured = []
    with unittest.mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen(captured)):
        wiring.https_transport("GET", _POLY_TRANSPORT_URL, b"")
    assert captured[0].get_header("Accept") == "application/json"


def test_poly_get_request_has_no_content_type():
    """GET must not carry Content-Type — amendment pins Accept only for Polymarket."""
    captured = []
    with unittest.mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen(captured)):
        wiring.https_transport("GET", _POLY_TRANSPORT_URL, b"")
    assert captured[0].get_header("Content-type") is None


def test_https_transport_still_returns_five_tuple():
    """Fixed transport must preserve the (status, body, started_ms, completed_ms, elapsed_ns) contract."""
    captured = []
    with unittest.mock.patch("urllib.request.urlopen",
                             side_effect=_fake_urlopen(captured, status=200, body=b'{"r":1}')):
        result = wiring.https_transport("POST", _HL_TRANSPORT_URL, _HL_TRANSPORT_BODY)
    assert isinstance(result, tuple) and len(result) == 5
    status, body, started, completed, elapsed = result
    assert status == 200
    assert body == b'{"r":1}'
    assert isinstance(started, int) and started >= 0
    assert isinstance(completed, int) and completed >= 0
    assert isinstance(elapsed, int) and elapsed >= 0
