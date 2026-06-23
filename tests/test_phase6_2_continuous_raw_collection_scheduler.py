"""RED→GREEN tests for the ratified Post-Phase 6.2 Continuous Raw Collection / Scheduler TDD Charter
(``docs/handoff/post_phase6_2_continuous_raw_collection_scheduler_tdd_charter.md``).

Boundary: pure, stdlib-only, ZERO real network. Capture callables, the clock, sleep, the ledger-append
sink, and the S1 ingest call are all dependency-injected fakes. No real ``/root`` ledger, no real S1 DB,
no daemon / loop, no 24h run. The scheduler only plans bounded cycles and, behind an explicit
stream-authorization boundary, delegates to the RATIFIED S1 ingestion adapter. Capacity stays 0.
"""
import hashlib
import inspect
import sqlite3

import pytest

from phase6_2_shadow_intent import continuous_raw_collection_scheduler as sched
from phase6_2_shadow_intent import s1_production_ingestion_adapter as adapter
from phase6_2_shadow_intent import s1_paired_projection as proj


_START = 1_000_000
_STOP = _START + 3600  # 1h window (<= 24h)


# --- fakes ---------------------------------------------------------------------------------------

class _FakeLedger:
    """Append-only capture sink. Exposes ONLY append (no update/delete)."""

    def __init__(self):
        self.rows = []

    def append(self, capture_row):
        capture_id = len(self.rows) + 1
        self.rows.append(dict(capture_row))
        return capture_id


def _fixed_clock(value=_START):
    return lambda: value


def _stepping_clock(values):
    it = iter(values)
    return lambda: next(it)


def _recording_sleep():
    calls = []
    return calls, (lambda seconds: calls.append(seconds))


def _outcome(leg, *, body=b'{"ok":1}', status=200, sha=None,
            started=10, completed=20, elapsed=1):
    return sched.CaptureOutcome(
        source_authority=leg.source_authority, method=leg.method,
        request_target=leg.request_target, request_body=leg.request_body,
        http_status=status, response_body=body,
        response_body_sha256=hashlib.sha256(body).hexdigest() if sha is None else sha,
        retrieval_started_epoch_ms=started, retrieval_completed_epoch_ms=completed,
        retrieval_elapsed_monotonic_ns=elapsed)


def _commit_capture(outcome_factory=_outcome):
    return lambda leg: outcome_factory(leg)


def _config(**over):
    kw = dict(start_time=_START, stop_time=_STOP, max_cycles=3, sleep_interval=5, failure_budget=0)
    kw.update(over)
    return sched.build_scheduler_config(**kw)


def _run(**over):
    ledger = over.pop("ledger", None) or _FakeLedger()
    kw = dict(
        config=_config(),
        hyperliquid_capture=_commit_capture(),
        polymarket_capture=_commit_capture(),
        continuous_ledger_path="/tmp/continuous_evidence/raw.sqlite3",
        ledger_append=ledger.append,
        clock=_fixed_clock(),
        sleep=_recording_sleep()[1],
        stream_authorization=None,
    )
    kw.update(over)
    return sched.run_bounded_collection(**kw), ledger


def _reason(excinfo):
    return excinfo.value.reason


# --- Group A: target lock ------------------------------------------------------------------------

def test_plan_cycle_locks_hyperliquid_leg():
    leg = sched.plan_cycle(0).hyperliquid_leg
    assert leg.source_authority == "HYPERLIQUID_L2_BOOK_BY_COIN_V1"
    assert leg.method == "POST"
    assert leg.host == "api.hyperliquid.xyz"
    assert leg.request_target == "/info"
    assert leg.request_body == b'{"type":"l2Book","coin":"BTC"}'


def test_plan_cycle_locks_polymarket_leg():
    leg = sched.plan_cycle(0).polymarket_leg
    assert leg.source_authority == "POLYMARKET_CLOB_BOOK_BY_TOKEN_V1"
    assert leg.method == "GET"
    assert leg.host == "clob.polymarket.com"
    assert leg.request_target == "/book?token_id=" + proj.RATIFIED_POLYMARKET_TOKEN_ID
    assert leg.request_body == b""


def test_ratified_legs_validate():
    sched.validate_leg_target(sched.HYPERLIQUID_LEG)
    sched.validate_leg_target(sched.POLYMARKET_LEG)


def test_reject_no_token_leg():
    bad = sched.LegTarget(
        source_authority="POLYMARKET_CLOB_BOOK_BY_TOKEN_V1", method="GET", scheme="https",
        host="clob.polymarket.com",
        request_target="/book?token_id=68320692409850091190490975441025843632582876963922128660910974326175304515755",
        request_body=b"")
    with pytest.raises(sched.SchedulerError) as e:
        sched.validate_leg_target(bad)
    assert _reason(e) == "SCHED_TARGET_DRIFT"


def test_reject_alternate_coin_leg():
    bad = sched.LegTarget(
        source_authority="HYPERLIQUID_L2_BOOK_BY_COIN_V1", method="POST", scheme="https",
        host="api.hyperliquid.xyz", request_target="/info",
        request_body=b'{"type":"l2Book","coin":"ETH"}')
    with pytest.raises(sched.SchedulerError) as e:
        sched.validate_leg_target(bad)
    assert _reason(e) == "SCHED_TARGET_DRIFT"


def test_reject_gamma_fallback_leg():
    bad = sched.LegTarget(
        source_authority="POLYMARKET_GAMMA_MARKET_BY_SLUG_V1", method="GET", scheme="https",
        host="gamma-api.polymarket.com", request_target="/markets?slug=btc", request_body=b"")
    with pytest.raises(sched.SchedulerError) as e:
        sched.validate_leg_target(bad)
    assert _reason(e) == "SCHED_TARGET_DRIFT"


def test_reject_method_mutation():
    bad = sched.LegTarget(
        source_authority="POLYMARKET_CLOB_BOOK_BY_TOKEN_V1", method="POST", scheme="https",
        host="clob.polymarket.com",
        request_target="/book?token_id=" + proj.RATIFIED_POLYMARKET_TOKEN_ID, request_body=b"")
    with pytest.raises(sched.SchedulerError) as e:
        sched.validate_leg_target(bad)
    assert _reason(e) == "SCHED_TARGET_DRIFT"


def test_reject_private_authenticated_endpoint():
    bad = sched.LegTarget(
        source_authority="POLYMARKET_CLOB_BOOK_BY_TOKEN_V1", method="GET", scheme="https",
        host="clob.polymarket.com", request_target="/auth/api-key/balance", request_body=b"")
    with pytest.raises(sched.SchedulerError) as e:
        sched.validate_leg_target(bad)
    assert _reason(e) == "SCHED_PRIVATE_ENDPOINT_FORBIDDEN"


# --- Group B: bounded configuration --------------------------------------------------------------

def test_valid_config_builds():
    cfg = _config()
    assert cfg.max_cycles == 3


@pytest.mark.parametrize("field", ["start_time", "stop_time", "max_cycles", "sleep_interval",
                                   "failure_budget"])
def test_missing_bound_fails_closed(field):
    with pytest.raises(sched.SchedulerError) as e:
        _config(**{field: None})
    assert _reason(e) == "SCHED_CONFIG_INCOMPLETE"


def test_stop_not_after_start_fails_closed():
    with pytest.raises(sched.SchedulerError) as e:
        _config(stop_time=_START)
    assert _reason(e) == "SCHED_CONFIG_INVALID_WINDOW"


def test_window_over_24h_fails_closed():
    with pytest.raises(sched.SchedulerError) as e:
        _config(stop_time=_START + 86401)
    assert _reason(e) == "SCHED_CONFIG_INVALID_WINDOW"


def test_window_exactly_24h_ok():
    cfg = _config(stop_time=_START + 86400)
    assert cfg.stop_time - cfg.start_time == 86400


@pytest.mark.parametrize("sleep_interval", [0, -1])
def test_nonpositive_sleep_fails_closed(sleep_interval):
    with pytest.raises(sched.SchedulerError) as e:
        _config(sleep_interval=sleep_interval)
    assert _reason(e) == "SCHED_CONFIG_INVALID_SLEEP"


@pytest.mark.parametrize("max_cycles", [0, -3])
def test_nonpositive_max_cycles_fails_closed(max_cycles):
    with pytest.raises(sched.SchedulerError) as e:
        _config(max_cycles=max_cycles)
    assert _reason(e) == "SCHED_CONFIG_INVALID_MAX_CYCLES"


def test_negative_failure_budget_fails_closed():
    with pytest.raises(sched.SchedulerError) as e:
        _config(failure_budget=-1)
    assert _reason(e) == "SCHED_CONFIG_INVALID_FAILURE_BUDGET"


def test_no_unbounded_daemon_attributes():
    for banned in ("daemon", "watchdog", "restart", "cron", "systemd", "serve_forever",
                   "run_forever", "main_loop"):
        assert not hasattr(sched, banned)


def test_module_has_no_infinite_loop_source():
    src = inspect.getsource(sched)
    assert "while True" not in src
    assert "while 1" not in src


# --- Group C: pair-cycle atomicity ---------------------------------------------------------------

def test_cycle_id_is_deterministic():
    assert sched.plan_cycle(0).cycle_id == sched.plan_cycle(0).cycle_id
    assert sched.plan_cycle(0).cycle_id != sched.plan_cycle(1).cycle_id


def test_cycle_attempts_both_legs_and_records_metadata():
    report, ledger = _run()
    # 3 cycles x 2 legs = 6 append rows
    assert len(ledger.rows) == 6
    row = ledger.rows[0]
    for key in ("source_authority", "method", "request_target", "request_body", "http_status",
                "response_body_sha256", "byte_length", "cycle_id",
                "retrieval_started_epoch_ms", "retrieval_completed_epoch_ms"):
        assert key in row


def test_retrieval_timestamps_are_forensic_only():
    # the scheduler records retrieval_* as ledger forensic metadata, and exposes NO event-time field.
    _report, ledger = _run()
    assert "retrieval_completed_epoch_ms" in ledger.rows[0]
    assert not any("event_time" in f for f in sched.CollectionReport.__dataclass_fields__)


def test_lone_leg_never_projects(monkeypatch):
    calls = {"n": 0}

    def spy(**kwargs):
        calls["n"] += 1
        return adapter.IngestResult(written=True, idempotency_key="x", projection=None)

    # Polymarket leg transport-fails (status 0) every cycle -> lone HL leg -> never project.
    auth = sched.StreamAuthorization(
        raw_ledger_path="/tmp/x", destination_connection=object(), destination_table="t")
    report, _ = _run(
        config=_config(failure_budget=10),
        polymarket_capture=lambda leg: _outcome(leg, status=0, body=b""),
        stream_authorization=auth, s1_ingest=spy)
    assert calls["n"] == 0
    assert report.s1_written == 0


# --- Group D: raw ledger isolation ---------------------------------------------------------------

def test_oneshot_proof_ledger_path_rejected():
    with pytest.raises(sched.SchedulerError) as e:
        _run(continuous_ledger_path="/root/mispricing_l2book_runtime_evidence/raw_capture.sqlite3")
    assert _reason(e) == "SCHED_ONESHOT_LEDGER_FORBIDDEN"


def test_empty_ledger_path_rejected():
    with pytest.raises(sched.SchedulerError) as e:
        _run(continuous_ledger_path="")
    assert _reason(e) == "SCHED_ONESHOT_LEDGER_FORBIDDEN"


def test_capture_rows_carry_cycle_id_and_provenance():
    _report, ledger = _run()
    cycle_ids = {row["cycle_id"] for row in ledger.rows}
    assert len(cycle_ids) == 3
    assert all(row["source_authority"] for row in ledger.rows)
    assert all(len(row["response_body_sha256"]) == 64 for row in ledger.rows)


def test_no_real_root_evidence_default_target_constant():
    src = inspect.getsource(sched)
    # a denylist may name one-shot dirs for REJECTION, but no real path may be a default write target.
    assert "DEFAULT_LEDGER_PATH" not in src
    assert "= \"/root/mispricing" not in src


# --- Group E: S1 stream firewall -----------------------------------------------------------------

def test_absent_stream_authorization_never_appends_s1(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(adapter, "ingest_paired_s1_projection",
                        lambda **k: calls.__setitem__("n", calls["n"] + 1))
    report, _ = _run(stream_authorization=None)
    assert calls["n"] == 0
    assert report.s1_written == 0 and report.s1_noop == 0


def test_default_s1_ingest_is_ratified_adapter():
    assert sched.DEFAULT_S1_INGEST is adapter.ingest_paired_s1_projection


def test_stream_authorization_routes_through_injected_adapter():
    seen = {"kwargs": None, "n": 0}

    def spy(**kwargs):
        seen["kwargs"] = kwargs
        seen["n"] += 1
        return adapter.IngestResult(written=True, idempotency_key="k", projection=None)

    auth = sched.StreamAuthorization(
        raw_ledger_path="/tmp/cont/raw.sqlite3", destination_connection=object(),
        destination_table="s1_projection_audit")
    report, _ = _run(config=_config(max_cycles=1), stream_authorization=auth, s1_ingest=spy)
    assert seen["n"] == 1
    assert seen["kwargs"]["destination_table"] == "s1_projection_audit"
    assert report.s1_written == 1


def test_scheduler_success_does_not_activate_production_stream():
    report, _ = _run()  # no authorization
    assert report.stop_reason in ("MAX_CYCLES", "STOP_TIME")
    assert report.s1_written == 0


# --- Group F: failure / stop conditions ----------------------------------------------------------

def test_target_drift_fails_closed():
    drift = sched.LegTarget(
        source_authority="HYPERLIQUID_L2_BOOK_BY_COIN_V1", method="POST", scheme="https",
        host="api.hyperliquid.xyz", request_target="/info",
        request_body=b'{"type":"l2Book","coin":"ETH"}')
    with pytest.raises(sched.SchedulerError) as e:
        _run(hyperliquid_capture=lambda leg: _outcome(drift))
    assert _reason(e) == "SCHED_TARGET_DRIFT"


def test_sha_mismatch_fails_closed():
    with pytest.raises(sched.SchedulerError) as e:
        _run(hyperliquid_capture=lambda leg: _outcome(leg, sha="a" * 64))
    assert _reason(e) == "SCHED_SHA_MISMATCH"


def test_malformed_capture_fails_closed():
    with pytest.raises(sched.SchedulerError) as e:
        _run(hyperliquid_capture=lambda leg: _outcome(leg, sha="not-64-hex"))
    assert _reason(e) == "SCHED_MALFORMED_CAPTURE"


def test_failure_budget_exceeded_fails_closed():
    # both legs transport-fail; budget 0 -> first failure exceeds budget.
    with pytest.raises(sched.SchedulerError) as e:
        _run(config=_config(failure_budget=0),
             hyperliquid_capture=lambda leg: _outcome(leg, status=0, body=b""),
             polymarket_capture=lambda leg: _outcome(leg, status=0, body=b""))
    assert _reason(e) == "SCHED_FAILURE_BUDGET_EXCEEDED"


def test_non_2xx_within_budget_does_not_project():
    auth = sched.StreamAuthorization(
        raw_ledger_path="/tmp/x", destination_connection=object(), destination_table="t")
    calls = {"n": 0}
    report, _ = _run(
        config=_config(failure_budget=5),
        hyperliquid_capture=lambda leg: _outcome(leg, status=503),
        stream_authorization=auth, s1_ingest=lambda **k: calls.__setitem__("n", calls["n"] + 1))
    assert calls["n"] == 0


def test_max_cycles_bounds_the_run():
    report, ledger = _run(config=_config(max_cycles=2), clock=_fixed_clock())
    assert report.total_cycles_run == 2
    assert report.stop_reason == "MAX_CYCLES"


def test_stop_time_bounds_the_run():
    # clock: first two cycles before stop, third call past stop -> terminate.
    clock = _stepping_clock([_START, _START + 1, _STOP + 5, _STOP + 5])
    report, _ = _run(config=_config(max_cycles=10), clock=clock)
    assert report.total_cycles_run == 2
    assert report.stop_reason == "STOP_TIME"


def test_projection_validation_failure_propagates_ratified_literal():
    def bad_ingest(**kwargs):
        raise proj.S1PairedProjectionError(
            proj.S1_PROVENANCE_SHA_MISMATCH, "bad")

    auth = sched.StreamAuthorization(
        raw_ledger_path="/tmp/x", destination_connection=object(), destination_table="t")
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _run(config=_config(max_cycles=1), stream_authorization=auth, s1_ingest=bad_ingest)
    assert _reason(e) == "S1_PROVENANCE_SHA_MISMATCH"


def test_s1_append_failure_fails_closed():
    def boom(**kwargs):
        raise sqlite3.OperationalError("no such table")

    auth = sched.StreamAuthorization(
        raw_ledger_path="/tmp/x", destination_connection=object(), destination_table="t")
    with pytest.raises(sched.SchedulerError) as e:
        _run(config=_config(max_cycles=1), stream_authorization=auth, s1_ingest=boom)
    assert _reason(e) == "SCHED_S1_APPEND_FAILED"


# --- Group G: observability / no actionability ---------------------------------------------------

def test_report_fields_are_observability_only():
    banned = ("edge", "profit", "rank", "advice", "alert", "size", "paper", "live",
              "signal", "calibrat", "position", "pnl")
    for name in sched.CollectionReport.__dataclass_fields__:
        assert not any(token in name for token in banned)


def test_report_carries_only_allowed_summaries():
    report, _ = _run()
    assert report.total_cycles_run == 3
    assert report.committed_pairs == 3
    assert len(report.cycle_ids) == 3
    assert isinstance(report.failure_literals, tuple)


# --- Group H: no real network --------------------------------------------------------------------

def test_scheduler_module_has_no_network_imports():
    import ast

    tree = ast.parse(inspect.getsource(sched))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    forbidden = {"socket", "http", "urllib", "requests", "aiohttp", "asyncio", "httpx", "websocket"}
    assert roots.isdisjoint(forbidden)


def test_capture_layer_is_dependency_injected():
    params = inspect.signature(sched.run_bounded_collection).parameters
    assert "hyperliquid_capture" in params
    assert "polymarket_capture" in params


# --- Group I: capacity firewall ------------------------------------------------------------------

def test_capacity_is_zero():
    assert sched.CAPACITY == 0


def test_no_trading_or_actionability_api():
    for banned in ("trade", "order", "place_order", "balance", "position", "calibrate",
                   "paper", "live", "signal", "rank", "edge", "size_position"):
        assert not hasattr(sched, banned)


def test_scheduler_success_does_not_upgrade_capacity():
    _run()
    assert sched.CAPACITY == 0
