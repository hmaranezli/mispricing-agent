"""approval/production_s1_append_circuit.py — isolated Production S1 Append Execution Wiring/Circuit.

This is the wiring seam described by the ratified Production S1 Append Execution Wiring/Circuit
Boundary Charter, UNIFIED (Schema & Journal Unification) onto the single canonical container. It is a
LIBRARY-ONLY composition of three ratified passive modules — the passive S1 append authorization
decision, the live S1 DB initializer, and the S1 append DB writer — operating ONLY on caller-supplied
(pytest tmp_path / test) SQLite containers.

Hard constraints honoured by construction:
  * No CLI / REST / API / network / daemon / listener / scheduler / queue / worker / observer /
    callback-hook entrypoint. No ``__main__``. No auth/ingress implementation (authentication is
    deferred to a future separate boundary; an external-trigger or auth attempt fails closed).
  * No default / production DB path; the exact ``db_path`` is supplied per command. No production
    append, no production stream, no approval-ledger mutation, no secret/key/env access.
  * ``wiring is not execution``: importing/constructing this module performs no DB/file/network/ledger
    side effect. ``REVIEWABLE_FOR_S1_APPEND`` is not ``AUTHORIZED``; ``CREATED_EMPTY_LOCKED_CONTAINER``
    is not ``AUTHORIZED`` and not stream-ready.
  * A successful TEST-scope append yields ``APPEND_RECORDED_IN_TEST_CONTAINER`` — never
    ``PRODUCTION_APPEND_AUTHORIZED``. Every production authority flag is hard-coded ``False``.

Unified seam: the initializer, writer, and this circuit now agree on ONE canonical append-only table
``s1_appends`` in WAL mode with the synchronous=FULL floor, sharing the deterministic schema and
journal-mode fingerprints from ``approval.live_s1_db_initialization``. The circuit verifies the
canonical container (via the shared ``verify_canonical_container``) and runs the idempotency pre-check
and the atomic append against that same table. No dual-table, no shadow-write, no compatibility shim;
it never cleans up / checkpoints / vacuums / migrates / deletes any artifact.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass

from approval import live_s1_db_initialization as _init
from approval import s1_append_execution_db_writer as _writer

_REVIEWABLE = "REVIEWABLE_FOR_S1_APPEND"
_CONTAINER_OK = "CREATED_EMPTY_LOCKED_CONTAINER"
_APPEND_OK = "APPEND_RECORDED_IN_TEST_CONTAINER"
_CONTAINER_TABLE = _init.CANONICAL_TABLE
_RECOVERY_SUFFIXES_WITH_DB = ("-journal", "-lock")  # WAL/SHM are expected companions of a WAL DB
_REQUIRED_TEXT_FIELDS = (
    "operator_command_id",
    "db_path",
    "s1_target",
    "evidence_digest",
    "canonical_payload_digest",
    "approval_row_digest",
    "freshness_binding_digest",
    "immutable_snapshot_ref",
    "created_at_utc",
    "decision_result_digest",
    "initializer_result_digest",
    "writer_request_digest",
    "schema_version",
    "expected_container_fingerprint",
)


@dataclass(frozen=True)
class S1AppendCircuitCommand:
    """Immutable, explicit production append command. No auto-trigger / no ingress by construction."""

    operator_command_id: str
    db_path: str
    s1_target: str
    evidence_digest: str
    canonical_payload_digest: str
    approval_row_digest: str
    freshness_binding_digest: str
    immutable_snapshot_ref: str
    created_at_utc: str
    decision_result_digest: str
    initializer_result_digest: str
    writer_request_digest: str
    schema_version: str
    expected_container_fingerprint: str
    expected_pre_append_row_count: int = 0
    external_trigger: str = ""
    auth_not_implemented_and_required_for_any_external_trigger: bool = True


@dataclass(frozen=True)
class S1AppendCircuitResult:
    """Passive, immutable circuit outcome. Authorizes nothing in production."""

    status: str  # APPEND_RECORDED_IN_TEST_CONTAINER | BLOCKED | BLOCKED_DUPLICATE | BLOCKED_RECOVERY_REQUIRED | BLOCKED_TAMPER_SUSPECT
    reason: str
    circuit_result_digest: str
    append_seq: int = -1
    container_fingerprint: str = ""
    production_s1_append_authorized: bool = False
    production_stream_authorized: bool = False
    trading_authorized: bool = False
    capacity_enabled: bool = False
    wallet_authorized: bool = False


def compute_writer_request_digest(
    *,
    decision_status: str,
    evidence_digest: str,
    s1_target: str,
    canonical_payload_digest: str,
    approval_row_digest: str,
    freshness_binding_digest: str,
    immutable_snapshot_ref: str,
    operator_command_id: str,
    created_at_utc: str,
) -> str:
    """Deterministic digest over the exact writer request the circuit would build. Pure."""
    parts = [
        f"decision_status={decision_status}",
        f"evidence_digest={evidence_digest}",
        f"s1_target={s1_target}",
        f"canonical_payload_digest={canonical_payload_digest}",
        f"approval_row_digest={approval_row_digest}",
        f"freshness_binding_digest={freshness_binding_digest}",
        f"immutable_snapshot_ref={immutable_snapshot_ref}",
        f"operator_command_id={operator_command_id}",
        f"created_at_utc={created_at_utc}",
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def compute_container_fingerprint(db_path: str) -> str:
    """Deterministic canonical schema fingerprint of the s1_appends container. Read-only.

    Delegates to the SHARED fingerprint in live_s1_db_initialization so initializer, writer, and
    circuit all agree on one fingerprint definition."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return _init.container_schema_fingerprint(con)
    finally:
        con.close()


def _circuit_result_digest(status: str, reason: str, command: S1AppendCircuitCommand, container_fingerprint: str) -> str:
    parts = [
        f"status={status}",
        f"reason={reason}",
        f"operator_command_id={command.operator_command_id}",
        f"db_path={command.db_path}",
        f"s1_target={command.s1_target}",
        f"evidence_digest={command.evidence_digest}",
        f"decision_result_digest={command.decision_result_digest}",
        f"initializer_result_digest={command.initializer_result_digest}",
        f"writer_request_digest={command.writer_request_digest}",
        f"container_fingerprint={container_fingerprint}",
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _result(status: str, reason: str, command: S1AppendCircuitCommand, *, append_seq: int = -1, container_fingerprint: str = "") -> S1AppendCircuitResult:
    return S1AppendCircuitResult(
        status=status,
        reason=reason,
        circuit_result_digest=_circuit_result_digest(status, reason, command, container_fingerprint),
        append_seq=append_seq,
        container_fingerprint=container_fingerprint,
    )


def _validate_command(command: S1AppendCircuitCommand) -> str:
    for field in _REQUIRED_TEXT_FIELDS:
        if not getattr(command, field):
            return "missing_required_field"
    if command.external_trigger:
        return "external_ingress_forbidden"
    if command.auth_not_implemented_and_required_for_any_external_trigger is not True:
        return "auth_required_not_implemented"
    return ""


def _bind(command: S1AppendCircuitCommand, decision_result, initializer_request, initializer_result) -> str:
    """Cross-bind command to the ratified decision/initializer objects and the writer request."""
    if decision_result.status == "AUTHORIZED":
        return "decision_treated_as_authorized"
    if decision_result.status != _REVIEWABLE:
        return "decision_not_reviewable"
    if command.decision_result_digest != decision_result.evidence_digest:
        return "decision_digest_mismatch"

    if initializer_result.status != _CONTAINER_OK:
        return "container_not_created"
    if command.initializer_result_digest != initializer_result.initialization_result_digest:
        return "initializer_digest_mismatch"

    if command.db_path != initializer_request.db_path:
        return "db_path_mismatch"
    if command.schema_version != initializer_request.schema_version:
        return "schema_version_mismatch"

    expected_fresh = _writer.compute_freshness_binding_digest(
        immutable_snapshot_ref=command.immutable_snapshot_ref,
        evidence_digest=command.evidence_digest,
        s1_target=command.s1_target,
        canonical_payload_digest=command.canonical_payload_digest,
        approval_row_digest=command.approval_row_digest,
    )
    if command.freshness_binding_digest != expected_fresh:
        return "freshness_binding_mismatch"

    expected_wrd = compute_writer_request_digest(
        decision_status=_REVIEWABLE,
        evidence_digest=command.evidence_digest,
        s1_target=command.s1_target,
        canonical_payload_digest=command.canonical_payload_digest,
        approval_row_digest=command.approval_row_digest,
        freshness_binding_digest=command.freshness_binding_digest,
        immutable_snapshot_ref=command.immutable_snapshot_ref,
        operator_command_id=command.operator_command_id,
        created_at_utc=command.created_at_utc,
    )
    if command.writer_request_digest != expected_wrd:
        return "writer_request_digest_mismatch"
    return ""


def _suspect_recovery(db_path: str) -> bool:
    if not os.path.exists(db_path):
        return True  # no container at the exact path: any sidecar or absence is unsafe
    return any(os.path.exists(db_path + suffix) for suffix in _RECOVERY_SUFFIXES_WITH_DB)


def _existing_append(db_path: str, evidence_digest: str, s1_target: str) -> bool:
    """Idempotency pre-check against the canonical s1_appends table. Read-only; tolerant if absent."""
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            if not _init.has_table(con, _CONTAINER_TABLE):
                return False
            row = con.execute(
                "SELECT 1 FROM s1_appends WHERE evidence_digest=? AND s1_target=?",
                (evidence_digest, s1_target),
            ).fetchone()
            return row is not None
        finally:
            con.close()
    except Exception:
        return False  # unreadable -> tamper battery will classify it


def _execute_db_phase(command: S1AppendCircuitCommand, initializer_request) -> S1AppendCircuitResult:
    """Read-verify the canonical container, fingerprint-bind it, then delegate the atomic append.

    Runs under the circuit single-flight guard (when supplied), so verify→fingerprint→append form one
    coherent, serialized critical section — the atomic-or-fail-closed boundary the charter requires."""
    # Suspect-state preflight (recovery is owned by the separate recovery charter; never clean up).
    if _suspect_recovery(command.db_path):
        return _result("BLOCKED_RECOVERY_REQUIRED", "recovery_required", command)

    # Idempotency pre-check BEFORE the strict tamper battery: a legitimate prior append (now in the
    # same canonical table) is reported as a duplicate rather than a nonzero-rows tamper.
    if _existing_append(command.db_path, command.evidence_digest, command.s1_target):
        return _result("BLOCKED_DUPLICATE", "duplicate_append", command)

    # Shared canonical tamper battery: file mode, legacy/dual-table rejection, integrity, schema
    # fingerprint, journal fingerprint (WAL + synchronous=FULL floor), and empty-row expectation.
    reason = _init.verify_canonical_container(
        command.db_path,
        expected_file_mode=initializer_request.expected_file_mode,
        expected_row_count=command.expected_pre_append_row_count,
    )
    if reason:
        return _result("BLOCKED_TAMPER_SUSPECT", reason, command)

    try:
        fingerprint = compute_container_fingerprint(command.db_path)
    except Exception:
        return _result("BLOCKED_TAMPER_SUSPECT", "introspection_failed", command)
    if fingerprint != command.expected_container_fingerprint:
        return _result("BLOCKED_TAMPER_SUSPECT", "fingerprint_mismatch", command, container_fingerprint=fingerprint)

    # All gates clean: delegate the atomic append to the ratified writer (same canonical s1_appends).
    writer_request = _writer.S1AppendRequest(
        decision_status=_REVIEWABLE,
        evidence_digest=command.evidence_digest,
        s1_target=command.s1_target,
        canonical_payload_digest=command.canonical_payload_digest,
        approval_row_digest=command.approval_row_digest,
        freshness_binding_digest=command.freshness_binding_digest,
        immutable_snapshot_ref=command.immutable_snapshot_ref,
        operator_command_id=command.operator_command_id,
        created_at_utc=command.created_at_utc,
    )
    try:
        wr = _writer.execute_s1_append(
            command.db_path,
            request=writer_request,
            accepted_snapshot_ref=command.immutable_snapshot_ref,
            single_flight=None,
        )
    except Exception:
        return _result("BLOCKED", "writer_contention", command, container_fingerprint=fingerprint)

    if wr.status == "APPENDED":
        return _result(_APPEND_OK, "", command, append_seq=wr.append_seq, container_fingerprint=fingerprint)
    if wr.status == "BLOCKED_DUPLICATE":
        return _result("BLOCKED_DUPLICATE", wr.reason or "duplicate_append", command, container_fingerprint=fingerprint)
    if wr.status == "BLOCKED_RECOVERY_REQUIRED":
        return _result("BLOCKED_RECOVERY_REQUIRED", wr.reason or "recovery_required", command, container_fingerprint=fingerprint)
    return _result("BLOCKED", wr.reason or "writer_blocked", command, container_fingerprint=fingerprint)


def run_production_s1_append_circuit(
    *,
    command: S1AppendCircuitCommand,
    decision_result,
    initializer_request,
    initializer_result,
    single_flight=None,
) -> S1AppendCircuitResult:
    """Compose the ratified decision/initializer/writer into one explicitly-commanded test append.

    Pure-until-writer: every gate before the DB phase is read-only/binding. The DB phase (verify →
    fingerprint → atomic append) runs under the single-flight guard. Authorizes nothing; a successful
    append is recorded in the caller-supplied TEST container only.
    """
    reason = _validate_command(command)
    if reason:
        return _result("BLOCKED", reason, command)

    reason = _bind(command, decision_result, initializer_request, initializer_result)
    if reason:
        return _result("BLOCKED", reason, command)

    # Hold the single-flight guard across the WHOLE DB-touching phase so concurrent attempts neither
    # interleave reads with the append nor knock the lock-winner out. Losers fail closed.
    if single_flight is not None and not single_flight.acquire(blocking=False):
        return _result("BLOCKED", "race_lock_unavailable", command)
    try:
        return _execute_db_phase(command, initializer_request)
    finally:
        if single_flight is not None:
            try:
                single_flight.release()
            except RuntimeError:
                pass
