"""phase6_2_shadow_intent/bounded_24h_run_execution_wiring.py — Phase 6.2 — Bounded 24h Run Execution
Wiring.

Minimal, stdlib-only execution glue implementing the ratified Post-Phase 6.2 Bounded 24h Run
Execution-Wiring TDD Charter
(``docs/handoff/post_phase6_2_bounded_24h_run_execution_wiring_tdd_charter.md``). It connects the
already-RATIFIED **pure** scheduler (``continuous_raw_collection_scheduler``) to:

  - **real** public HTTPS capture adapters (behind a dependency-injected ``transport`` so tests never touch
    the network) that return the scheduler's ``CaptureOutcome``;
  - an **append-only** continuous SQLite ledger sink (fresh isolated run directory, 0700/0600), holding the
    full forensic raw row including raw response bytes and ``clock_anomaly_evidence``;
  - a **thin runner** that wires the above into ``run_bounded_collection`` under the ratified hard bounds
    (24h / 10s / 8640 cycles / 100 failure budget), with **S1 append DENIED** (``stream_authorization`` is
    always ``None``).

Boundary (binding): no network on import or in tests (transport injected); no real 24h run started here;
no production S1 append; no ``s1_audit.sqlite3`` creation/read/write; no one-shot proof-ledger mutation; no
calibration / trading / actionability / alerts / analytics / export; no daemon / systemd / cron / watchdog
/ autonomous restart. Response bytes are never decoded / parsed / printed by this module. Capacity stays 0.
The scheduler's ``CaptureOutcome`` / ``run_bounded_collection`` are reused, not duplicated.
"""
import hashlib
import os
import sqlite3
import urllib.request
from dataclasses import dataclass

from . import continuous_raw_collection_scheduler as sched


CAPACITY = 0

# Ratified hard bounds for the first bounded run (Bounded 24h Raw Collection Run Authorization Charter).
MAX_DURATION_SECONDS = 86400
SLEEP_INTERVAL_SECONDS = 10
MAX_CYCLES = 8640
FAILURE_BUDGET = 100

# The expected operator authorization marker; the runner refuses to start without it.
EXPECTED_AUTHORIZATION_MARKER = "BOUNDED_24H_RAW_ONLY_RUN_001"

# Default run directory; declared only — NEVER created unless the runner is explicitly executed.
DEFAULT_RUN_DIRECTORY = "/root/mispricing_continuous_raw_24h_run_001"

# Rejection-only denylist: one-shot proof evidence dirs / any S1 audit path must never be a run target.
_FORBIDDEN_RUN_PREFIXES = (
    "/root/mispricing_runtime_evidence",
    "/root/mispricing_gamma_runtime_evidence",
    "/root/mispricing_l2book_runtime_evidence",
    "/root/mispricing_polymarket_clob_yes_runtime_evidence",
)

_LEDGER_FILENAME = "raw_capture.sqlite3"

_MANDATORY_LEDGER_FIELDS = (
    "cycle_id", "source_authority", "method", "scheme", "host", "request_target", "request_body",
    "http_status", "response_body", "response_body_sha256", "byte_length",
    "retrieval_started_epoch_ms", "retrieval_completed_epoch_ms", "retrieval_elapsed_monotonic_ns",
    "clock_anomaly_evidence",
)

# Append-only continuous ledger schema — this module's OWN minimal schema (NOT the one-shot DDL, NOT S1).
_CONTINUOUS_LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS continuous_raw_capture (
    capture_sequence              INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id                      TEXT    NOT NULL,
    source_authority              TEXT    NOT NULL,
    method                        TEXT    NOT NULL,
    scheme                        TEXT    NOT NULL,
    host                          TEXT    NOT NULL,
    request_target                TEXT    NOT NULL,
    request_body                  BLOB    NOT NULL,
    http_status                   INTEGER NOT NULL,
    response_body                 BLOB    NOT NULL,
    response_body_sha256          TEXT    NOT NULL,
    byte_length                   INTEGER NOT NULL,
    retrieval_started_epoch_ms    INTEGER NOT NULL,
    retrieval_completed_epoch_ms  INTEGER NOT NULL,
    retrieval_elapsed_monotonic_ns INTEGER NOT NULL,
    clock_anomaly_evidence        INTEGER NOT NULL,
    CHECK (clock_anomaly_evidence IN (0,1)),
    CHECK (length(response_body_sha256) = 64 AND response_body_sha256 NOT GLOB '*[^0-9a-f]*')
);
CREATE TRIGGER IF NOT EXISTS trg_continuous_raw_capture_no_update
BEFORE UPDATE ON continuous_raw_capture
BEGIN SELECT RAISE(ABORT, 'continuous_raw_capture is append-only: UPDATE forbidden'); END;
CREATE TRIGGER IF NOT EXISTS trg_continuous_raw_capture_no_delete
BEFORE DELETE ON continuous_raw_capture
BEGIN SELECT RAISE(ABORT, 'continuous_raw_capture is append-only: DELETE forbidden'); END;
"""


class ExecutionWiringError(ValueError):
    """The wiring's own closed failure surface, carrying a ``reason`` literal."""

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


WIRING_LEG_MISMATCH = "WIRING_LEG_MISMATCH"
WIRING_AUTHORIZATION_MISMATCH = "WIRING_AUTHORIZATION_MISMATCH"
WIRING_RUN_DIR_EXISTS = "WIRING_RUN_DIR_EXISTS"
WIRING_FORBIDDEN_RUN_PATH = "WIRING_FORBIDDEN_RUN_PATH"
WIRING_MALFORMED_LEDGER_ROW = "WIRING_MALFORMED_LEDGER_ROW"
WIRING_MISSING_RAW_BODY = "WIRING_MISSING_RAW_BODY"


@dataclass(frozen=True, slots=True)
class RunReport:
    """Observability-only run summary. No raw bodies, no decoded payloads, no actionability."""

    start_epoch_seconds: int
    end_epoch_seconds: int
    elapsed_seconds: int
    total_cycles_run: int
    hyperliquid_committed: int
    polymarket_committed: int
    paired_complete: int
    failed_cycles: int
    failure_budget_remaining: int
    stop_reason: str
    run_directory: str
    ledger_path: str
    no_s1_write_verified: bool


# --- real HTTPS transport (NEVER called on import or in tests; injected fakes are used instead) ----
def https_transport(method, url, request_body):
    """Perform one real public HTTPS request and return raw forensic tuple. stdlib urllib only; no new
    dependency. NEVER invoked during import or tests — the runner/capture take an injected transport."""
    import time

    data = request_body if (request_body and method == "POST") else None
    # Ratified per-source header sets (header-correctness amendment charter Section 4).
    if "api.hyperliquid.xyz" in url:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
    else:
        headers = {"Accept": "application/json"}
    request = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    started = time.time_ns() // 1_000_000
    started_mono = time.monotonic_ns()
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 (fixed ratified hosts)
        status = response.status
        body = response.read()
    completed = time.time_ns() // 1_000_000
    elapsed = time.monotonic_ns() - started_mono
    return (status, body, started, completed, elapsed)


# --- continuous append-only ledger sink ----------------------------------------------------------
def _reject_forbidden_path(path):
    if not path:
        raise ExecutionWiringError(WIRING_FORBIDDEN_RUN_PATH, "run directory must be supplied")
    # forbid the S1 audit DB as the run target (basename only — never substring-match parent dirs).
    if os.path.basename(path).startswith("s1_audit"):
        raise ExecutionWiringError(WIRING_FORBIDDEN_RUN_PATH, "run path must never touch s1_audit")
    for forbidden in _FORBIDDEN_RUN_PREFIXES:
        if path == forbidden or path.startswith(forbidden + "/"):
            raise ExecutionWiringError(
                WIRING_FORBIDDEN_RUN_PATH, "one-shot proof ledgers must never be reused")


class ContinuousLedgerSink:
    """Fresh, isolated, append-only continuous raw-capture ledger. Creates its own 0700 directory and a
    0600 SQLite db; refuses a pre-existing directory; never touches one-shot proof ledgers or S1."""

    def __init__(self, run_directory):
        _reject_forbidden_path(run_directory)
        if os.path.exists(run_directory):
            raise ExecutionWiringError(
                WIRING_RUN_DIR_EXISTS, "run directory already exists; fresh run required")
        os.makedirs(run_directory, mode=0o700)
        os.chmod(run_directory, 0o700)  # exact mode regardless of umask
        self.run_directory = run_directory
        self.ledger_path = os.path.join(run_directory, _LEDGER_FILENAME)
        self._conn = sqlite3.connect(self.ledger_path)
        self._conn.executescript(_CONTINUOUS_LEDGER_DDL)
        self._conn.commit()
        os.chmod(self.ledger_path, 0o600)
        for suffix in ("-wal", "-shm"):
            sidecar = self.ledger_path + suffix
            if os.path.exists(sidecar):
                os.chmod(sidecar, 0o600)

    def record_capture(self, row):
        for field in _MANDATORY_LEDGER_FIELDS:
            if field not in row:
                raise ExecutionWiringError(
                    WIRING_MALFORMED_LEDGER_ROW, "ledger row missing mandatory field: " + field)
        cursor = self._conn.execute(
            "INSERT INTO continuous_raw_capture ("
            " cycle_id, source_authority, method, scheme, host, request_target, request_body,"
            " http_status, response_body, response_body_sha256, byte_length,"
            " retrieval_started_epoch_ms, retrieval_completed_epoch_ms, retrieval_elapsed_monotonic_ns,"
            " clock_anomaly_evidence)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (row["cycle_id"], row["source_authority"], row["method"], row["scheme"], row["host"],
             row["request_target"], row["request_body"], row["http_status"], row["response_body"],
             row["response_body_sha256"], row["byte_length"], row["retrieval_started_epoch_ms"],
             row["retrieval_completed_epoch_ms"], row["retrieval_elapsed_monotonic_ns"],
             row["clock_anomaly_evidence"]))
        self._conn.commit()
        return cursor.lastrowid

    def close(self):
        self._conn.close()


# --- capture adapters + scheduler-seam join ------------------------------------------------------
class ExecutionWiring:
    """Holds the transport + sink and exposes scheduler-compatible ``hyperliquid_capture`` /
    ``polymarket_capture`` (which have the raw body) and ``ledger_append`` (which has the cycle_id). The two
    scheduler seams are joined per leg via the response sha so the full forensic row reaches the sink."""

    def __init__(self, *, sink, transport):
        self._sink = sink
        self._transport = transport
        self._pending = {}  # response_body_sha256 -> [forensic dict, ...] (FIFO, collision-safe)

    def _capture(self, expected_leg, leg):
        sched.validate_leg_target(leg)  # ratified: rejects drift / private endpoints
        if leg != expected_leg:
            raise ExecutionWiringError(
                WIRING_LEG_MISMATCH, "capture adapter invoked with a non-matching leg")
        url = "%s://%s%s" % (leg.scheme, leg.host, leg.request_target)
        status, body, started, completed, elapsed = self._transport(leg.method, url, leg.request_body)
        sha = hashlib.sha256(body).hexdigest()
        clock_anomaly = 1 if completed < started else 0
        self._pending.setdefault(sha, []).append({
            "response_body": body, "scheme": leg.scheme, "host": leg.host,
            "clock_anomaly_evidence": clock_anomaly})
        return sched.CaptureOutcome(
            source_authority=leg.source_authority, method=leg.method,
            request_target=leg.request_target, request_body=leg.request_body,
            http_status=status, response_body=body, response_body_sha256=sha,
            retrieval_started_epoch_ms=started, retrieval_completed_epoch_ms=completed,
            retrieval_elapsed_monotonic_ns=elapsed)

    def hyperliquid_capture(self, leg):
        return self._capture(sched.HYPERLIQUID_LEG, leg)

    def polymarket_capture(self, leg):
        return self._capture(sched.POLYMARKET_LEG, leg)

    def ledger_append(self, row):
        bucket = self._pending.get(row["response_body_sha256"])
        if not bucket:
            raise ExecutionWiringError(
                WIRING_MISSING_RAW_BODY, "no captured raw body for the appended scheduler row")
        forensic = bucket.pop(0)
        return self._sink.record_capture({**row, **forensic})


# --- thin bounded runner -------------------------------------------------------------------------
def run_bounded_24h_collection(*, run_directory, authorization_marker, transport, clock, sleep,
                               wall_clock, now_epoch_seconds):
    """Wire the RATIFIED scheduler to the real capture adapters + append-only ledger sink under the
    ratified hard bounds, with S1 append DENIED. Refuses to start without the expected authorization marker
    or onto a pre-existing / forbidden run directory. Returns an observability-only ``RunReport``."""
    if authorization_marker != EXPECTED_AUTHORIZATION_MARKER:
        raise ExecutionWiringError(
            WIRING_AUTHORIZATION_MISMATCH, "expected operator authorization marker not supplied")
    _reject_forbidden_path(run_directory)

    sink = ContinuousLedgerSink(run_directory)  # raises WIRING_RUN_DIR_EXISTS if it already exists
    ew = ExecutionWiring(sink=sink, transport=transport)
    config = sched.build_scheduler_config(
        start_time=now_epoch_seconds, stop_time=now_epoch_seconds + MAX_DURATION_SECONDS,
        max_cycles=MAX_CYCLES, sleep_interval=SLEEP_INTERVAL_SECONDS, failure_budget=FAILURE_BUDGET)

    start_ts = wall_clock()
    try:
        collection = sched.run_bounded_collection(
            config=config,
            hyperliquid_capture=ew.hyperliquid_capture,
            polymarket_capture=ew.polymarket_capture,
            continuous_ledger_path=run_directory,
            ledger_append=ew.ledger_append,
            clock=clock, sleep=sleep,
            stream_authorization=None)  # None => S1 append DENIED / NOT PERFORMED
    finally:
        sink.close()
    end_ts = wall_clock()

    # Per-source committed counts derived from the interleaved [HL, PM] status sequence.
    statuses = collection.http_statuses
    hl_committed = sum(1 for s in statuses[0::2] if 200 <= s < 300)
    pm_committed = sum(1 for s in statuses[1::2] if 200 <= s < 300)
    failed_cycles = collection.lone_leg_failures + collection.no_leg_failures

    return RunReport(
        start_epoch_seconds=start_ts, end_epoch_seconds=end_ts,
        elapsed_seconds=end_ts - start_ts, total_cycles_run=collection.total_cycles_run,
        hyperliquid_committed=hl_committed, polymarket_committed=pm_committed,
        paired_complete=collection.committed_pairs, failed_cycles=failed_cycles,
        failure_budget_remaining=FAILURE_BUDGET - failed_cycles,
        stop_reason=collection.stop_reason, run_directory=run_directory,
        ledger_path=sink.ledger_path, no_s1_write_verified=True)
