"""phase6_2_shadow_intent/continuous_raw_collection_scheduler.py — Phase 6.2 — Bounded Continuous Raw
Collection / Scheduler.

Minimal, pure, stdlib-only bounded scheduler implementing the ratified Post-Phase 6.2 Continuous Raw
Collection / Scheduler TDD Charter
(``docs/handoff/post_phase6_2_continuous_raw_collection_scheduler_tdd_charter.md``) and its RATIFIED
boundary charter.

It validates an **explicitly bounded** run configuration, plans **deterministic** collection cycles for the
**ratified BTC pair only** (Hyperliquid l2Book + Polymarket CLOB YES-token), and executes them through
**dependency-injected** capture callables, clock, sleep, and ledger-append sink. Each leg's raw response is
recorded append-only with forensic metadata. Projection / durable S1 append occurs **only** behind an
explicit ``StreamAuthorization`` boundary and **only** through the RATIFIED S1 ingestion adapter (never a
bypass). The run is bounded by ``max_cycles`` and ``stop_time`` — there is **no** infinite loop, daemon,
cron, watchdog, restart, or background persistence.

Boundary (binding): no real network (capture is injected), no real ``/root`` evidence path as a write
target, no real-or-prod S1 DB, no real 24h run, no production-stream activation, no calibration, no
trading / actionability, no alerts / analytics / export. Capacity stays 0. The scheduler owns its own
closed ``SchedulerError`` reason surface for config / target / stop conditions; it re-raises the RATIFIED
``S1PairedProjectionError`` literals untouched when the adapter rejects a pair.
"""
import hashlib
import re
from dataclasses import dataclass

from . import s1_production_ingestion_adapter as adapter
from . import s1_paired_projection as projection
from .s1_paired_projection import S1PairedProjectionError


CONTINUOUS_RAW_COLLECTION_SCHEDULER_COMPONENT_NAME = (
    "phase6_2_shadow_intent_continuous_raw_collection_scheduler")

# Capacity is structurally pinned at 0; no scheduler outcome upgrades it.
CAPACITY = 0

MAX_RUN_WINDOW_SECONDS = 86400  # 24h ceiling on the observation window

# Default S1 ingest is the RATIFIED adapter; the scheduler never bypasses it.
DEFAULT_S1_INGEST = adapter.ingest_paired_s1_projection

_SHA256_HEX = re.compile(r"\A[0-9a-f]{64}\Z")
_PRIVATE_TARGET = re.compile(r"(auth|api-key|order|balance|position|account|private|secret|wallet)",
                             re.IGNORECASE)

# Rejection-only denylist: prior one-shot proof evidence directories must never be a continuous target.
_FORBIDDEN_LEDGER_PREFIXES = (
    "/root/mispricing_runtime_evidence",
    "/root/mispricing_gamma_runtime_evidence",
    "/root/mispricing_l2book_runtime_evidence",
    "/root/mispricing_polymarket_clob_yes_runtime_evidence",
)


# --- closed scheduler failure surface ------------------------------------------------------------
SCHED_CONFIG_INCOMPLETE = "SCHED_CONFIG_INCOMPLETE"
SCHED_CONFIG_INVALID_WINDOW = "SCHED_CONFIG_INVALID_WINDOW"
SCHED_CONFIG_INVALID_SLEEP = "SCHED_CONFIG_INVALID_SLEEP"
SCHED_CONFIG_INVALID_MAX_CYCLES = "SCHED_CONFIG_INVALID_MAX_CYCLES"
SCHED_CONFIG_INVALID_FAILURE_BUDGET = "SCHED_CONFIG_INVALID_FAILURE_BUDGET"
SCHED_TARGET_DRIFT = "SCHED_TARGET_DRIFT"
SCHED_PRIVATE_ENDPOINT_FORBIDDEN = "SCHED_PRIVATE_ENDPOINT_FORBIDDEN"
SCHED_MALFORMED_CAPTURE = "SCHED_MALFORMED_CAPTURE"
SCHED_SHA_MISMATCH = "SCHED_SHA_MISMATCH"
SCHED_FAILURE_BUDGET_EXCEEDED = "SCHED_FAILURE_BUDGET_EXCEEDED"
SCHED_ONESHOT_LEDGER_FORBIDDEN = "SCHED_ONESHOT_LEDGER_FORBIDDEN"
SCHED_S1_APPEND_FAILED = "SCHED_S1_APPEND_FAILED"


class SchedulerError(ValueError):
    """The scheduler's own closed failure surface (config / target / stop), carrying a ``reason`` literal.
    Distinct from the RATIFIED S1 ``S1PairedProjectionError`` surface, which is re-raised untouched."""

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class LegTarget:
    source_authority: str
    method: str
    scheme: str
    host: str
    request_target: str
    request_body: bytes


@dataclass(frozen=True, slots=True)
class CaptureOutcome:
    source_authority: str
    method: str
    request_target: str
    request_body: bytes
    http_status: int
    response_body: bytes
    response_body_sha256: str
    retrieval_started_epoch_ms: int
    retrieval_completed_epoch_ms: int
    retrieval_elapsed_monotonic_ns: int


@dataclass(frozen=True, slots=True)
class SchedulerConfig:
    start_time: int
    stop_time: int
    max_cycles: int
    sleep_interval: int
    failure_budget: int


@dataclass(frozen=True, slots=True)
class StreamAuthorization:
    raw_ledger_path: str
    destination_connection: object
    destination_table: str


@dataclass(frozen=True, slots=True)
class CyclePlan:
    cycle_id: str
    hyperliquid_leg: LegTarget
    polymarket_leg: LegTarget


@dataclass(frozen=True, slots=True)
class CollectionReport:
    total_cycles_run: int
    committed_pairs: int
    lone_leg_failures: int
    no_leg_failures: int
    s1_written: int
    s1_noop: int
    stop_reason: str
    cycle_ids: tuple
    capture_ids: tuple
    http_statuses: tuple
    byte_lengths: tuple
    sha_summaries: tuple
    failure_literals: tuple
    timing_metadata: tuple


# --- ratified target locks (BTC pair only) -------------------------------------------------------
HYPERLIQUID_LEG = LegTarget(
    source_authority="HYPERLIQUID_L2_BOOK_BY_COIN_V1", method="POST", scheme="https",
    host="api.hyperliquid.xyz", request_target="/info",
    request_body=b'{"type":"l2Book","coin":"BTC"}')

POLYMARKET_LEG = LegTarget(
    source_authority="POLYMARKET_CLOB_BOOK_BY_TOKEN_V1", method="GET", scheme="https",
    host="clob.polymarket.com",
    request_target="/book?token_id=" + projection.RATIFIED_POLYMARKET_TOKEN_ID, request_body=b"")


def validate_leg_target(leg):
    """Accept ONLY the two ratified leg locks. Any drift fails closed; a private/authenticated target
    raises the dedicated private-endpoint literal."""
    if leg == HYPERLIQUID_LEG or leg == POLYMARKET_LEG:
        return
    if _PRIVATE_TARGET.search(leg.request_target or ""):
        raise SchedulerError(
            SCHED_PRIVATE_ENDPOINT_FORBIDDEN, "private/authenticated endpoint is forbidden")
    raise SchedulerError(SCHED_TARGET_DRIFT, "leg target is not a ratified BTC-pair lock")


def plan_cycle(cycle_index):
    """Deterministic cycle plan: stable ``cycle_id`` + the two ratified leg locks. No randomness, no
    wall-clock dependence."""
    return CyclePlan(
        cycle_id="CYCLE-%06d" % cycle_index,
        hyperliquid_leg=HYPERLIQUID_LEG, polymarket_leg=POLYMARKET_LEG)


def build_scheduler_config(*, start_time, stop_time, max_cycles, sleep_interval, failure_budget):
    """Validate an explicitly bounded configuration; every missing or invalid bound fails closed."""
    if None in (start_time, stop_time, max_cycles, sleep_interval, failure_budget):
        raise SchedulerError(SCHED_CONFIG_INCOMPLETE, "all bounds are required")
    if stop_time <= start_time or (stop_time - start_time) > MAX_RUN_WINDOW_SECONDS:
        raise SchedulerError(
            SCHED_CONFIG_INVALID_WINDOW, "run window must be positive and <= 24h")
    if sleep_interval <= 0:
        raise SchedulerError(SCHED_CONFIG_INVALID_SLEEP, "sleep_interval must be positive")
    if max_cycles <= 0:
        raise SchedulerError(SCHED_CONFIG_INVALID_MAX_CYCLES, "max_cycles must be positive")
    if failure_budget < 0:
        raise SchedulerError(
            SCHED_CONFIG_INVALID_FAILURE_BUDGET, "failure_budget must be non-negative")
    return SchedulerConfig(
        start_time=start_time, stop_time=stop_time, max_cycles=max_cycles,
        sleep_interval=sleep_interval, failure_budget=failure_budget)


def _validate_ledger_path(continuous_ledger_path):
    if not continuous_ledger_path:
        raise SchedulerError(
            SCHED_ONESHOT_LEDGER_FORBIDDEN, "continuous ledger path must be explicitly supplied")
    for forbidden in _FORBIDDEN_LEDGER_PREFIXES:
        if continuous_ledger_path == forbidden or continuous_ledger_path.startswith(forbidden + "/"):
            raise SchedulerError(
                SCHED_ONESHOT_LEDGER_FORBIDDEN, "one-shot proof ledgers must never be reused")


def _evaluate_leg(planned_leg, outcome):
    """Validate one capture outcome against the locked leg. Returns ``True`` when RAW_COMMITTED, ``False``
    for a soft (non-2xx / transport) failure. Hard contract violations fail closed."""
    # identity / drift (hard)
    if (outcome.source_authority != planned_leg.source_authority
            or outcome.method != planned_leg.method
            or outcome.request_target != planned_leg.request_target
            or outcome.request_body != planned_leg.request_body):
        if _PRIVATE_TARGET.search(outcome.request_target or ""):
            raise SchedulerError(
                SCHED_PRIVATE_ENDPOINT_FORBIDDEN, "capture used a private/authenticated endpoint")
        raise SchedulerError(SCHED_TARGET_DRIFT, "capture drifted from the ratified leg lock")
    # shape / malformed (hard)
    if (type(outcome.response_body) is not bytes
            or type(outcome.response_body_sha256) is not str
            or _SHA256_HEX.match(outcome.response_body_sha256) is None
            or outcome.retrieval_started_epoch_ms < 0
            or outcome.retrieval_completed_epoch_ms < 0
            or outcome.retrieval_elapsed_monotonic_ns < 0):
        raise SchedulerError(SCHED_MALFORMED_CAPTURE, "capture row is malformed")
    # integrity (hard)
    if hashlib.sha256(outcome.response_body).hexdigest() != outcome.response_body_sha256:
        raise SchedulerError(SCHED_SHA_MISMATCH, "recomputed sha256 != reported sha256")
    # commit status (soft)
    return 200 <= outcome.http_status < 300


def _capture_row(planned_leg, outcome, cycle_id):
    return {
        "cycle_id": cycle_id,
        "source_authority": outcome.source_authority,
        "method": outcome.method,
        "request_target": outcome.request_target,
        "request_body": outcome.request_body,
        "http_status": outcome.http_status,
        "response_body_sha256": outcome.response_body_sha256,
        "byte_length": len(outcome.response_body),
        # retrieval timestamps are FORENSIC metadata only; never source event time.
        "retrieval_started_epoch_ms": outcome.retrieval_started_epoch_ms,
        "retrieval_completed_epoch_ms": outcome.retrieval_completed_epoch_ms,
        "retrieval_elapsed_monotonic_ns": outcome.retrieval_elapsed_monotonic_ns,
    }


def run_bounded_collection(*, config, hyperliquid_capture, polymarket_capture,
                           continuous_ledger_path, ledger_append, clock, sleep,
                           stream_authorization=None, s1_ingest=DEFAULT_S1_INGEST):
    """Run a bounded collection: at most ``max_cycles`` deterministic cycles, terminating early at
    ``stop_time``. Each cycle attempts both ratified legs through injected capture callables, appends
    forensic capture rows, and — only behind ``stream_authorization`` — projects the committed pair through
    the RATIFIED S1 adapter. Fail-closed on every contract violation; never an infinite loop."""
    _validate_ledger_path(continuous_ledger_path)

    committed_pairs = lone_leg_failures = no_leg_failures = 0
    s1_written = s1_noop = 0
    soft_failures = 0
    cycle_ids = []
    capture_ids = []
    http_statuses = []
    byte_lengths = []
    sha_summaries = []
    failure_literals = []
    timing_metadata = []
    stop_reason = "MAX_CYCLES"
    total_cycles_run = 0

    for cycle_index in range(config.max_cycles):
        if clock() >= config.stop_time:
            stop_reason = "STOP_TIME"
            break
        total_cycles_run += 1
        plan = plan_cycle(cycle_index)
        cycle_ids.append(plan.cycle_id)

        hl_outcome = hyperliquid_capture(plan.hyperliquid_leg)
        pm_outcome = polymarket_capture(plan.polymarket_leg)
        hl_committed = _evaluate_leg(plan.hyperliquid_leg, hl_outcome)
        pm_committed = _evaluate_leg(plan.polymarket_leg, pm_outcome)

        for planned_leg, outcome in (
                (plan.hyperliquid_leg, hl_outcome), (plan.polymarket_leg, pm_outcome)):
            row = _capture_row(planned_leg, outcome, plan.cycle_id)
            capture_ids.append(ledger_append(row))
            http_statuses.append(outcome.http_status)
            byte_lengths.append(row["byte_length"])
            sha_summaries.append(outcome.response_body_sha256[:12])
            timing_metadata.append(outcome.retrieval_elapsed_monotonic_ns)

        if hl_committed and pm_committed:
            committed_pairs += 1
            if stream_authorization is not None:
                try:
                    result = s1_ingest(
                        raw_ledger_path=stream_authorization.raw_ledger_path,
                        destination_connection=stream_authorization.destination_connection,
                        destination_table=stream_authorization.destination_table)
                except S1PairedProjectionError:
                    raise  # re-raise the RATIFIED literal untouched (projection validation failure)
                except Exception as exc:
                    raise SchedulerError(
                        SCHED_S1_APPEND_FAILED, "durable S1 append failed") from exc
                if result.written:
                    s1_written += 1
                else:
                    s1_noop += 1
        else:
            if hl_committed or pm_committed:
                lone_leg_failures += 1
                failure_literals.append("SCHED_LONE_LEG")
            else:
                no_leg_failures += 1
                failure_literals.append("SCHED_NO_LEG")
            soft_failures += 1
            if soft_failures > config.failure_budget:
                raise SchedulerError(
                    SCHED_FAILURE_BUDGET_EXCEEDED, "soft failures exceeded the explicit failure budget")

        if cycle_index < config.max_cycles - 1:
            sleep(config.sleep_interval)

    return CollectionReport(
        total_cycles_run=total_cycles_run, committed_pairs=committed_pairs,
        lone_leg_failures=lone_leg_failures, no_leg_failures=no_leg_failures,
        s1_written=s1_written, s1_noop=s1_noop, stop_reason=stop_reason,
        cycle_ids=tuple(cycle_ids), capture_ids=tuple(capture_ids),
        http_statuses=tuple(http_statuses), byte_lengths=tuple(byte_lengths),
        sha_summaries=tuple(sha_summaries), failure_literals=tuple(failure_literals),
        timing_metadata=tuple(timing_metadata))
