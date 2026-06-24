"""approval/production_s1_append_circuit.py — isolated Production S1 Append Execution Wiring/Circuit.

This is the wiring seam described by the ratified Production S1 Append Execution Wiring/Circuit
Boundary Charter. It is a LIBRARY-ONLY composition of three ratified passive modules — the passive S1
append authorization decision, the live S1 DB initializer, and the S1 append DB writer — operating
ONLY on caller-supplied (pytest tmp_path / test) SQLite containers.

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

Structural note (honest seam): the ratified initializer provisions an append-only WAL container table
``s1_appends``; the ratified writer appends to its own append-only table ``s1_append_log`` (rollback
journal mode). The circuit therefore verifies the initialized ``s1_appends`` container (schema /
triggers / UNIQUE / PRAGMA=WAL / row-count / integrity / deterministic fingerprint) as the
precondition, runs the idempotency pre-check against the writer's ``s1_append_log``, and only then
delegates the atomic append to the ratified writer. It mutates neither module's invariants and never
cleans up / checkpoints / vacuums / deletes any artifact.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass

from approval import s1_append_execution_db_writer as _writer

_REVIEWABLE = "REVIEWABLE_FOR_S1_APPEND"
_CONTAINER_OK = "CREATED_EMPTY_LOCKED_CONTAINER"
_APPEND_OK = "APPEND_RECORDED_IN_TEST_CONTAINER"
_CONTAINER_TABLE = "s1_appends"
_WRITER_TABLE = "s1_append_log"
_CONTAINER_COLS = (
    "seq",
    "evidence_digest",
    "s1_target",
    "canonical_payload_digest",
    "approval_row_digest",
    "freshness_binding_digest",
    "immutable_snapshot_ref",
    "operator_command_id",
    "created_at_utc",
)
_UNIQUE_COLS = ["evidence_digest", "s1_target"]
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
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def compute_container_fingerprint(db_path: str) -> str:
    """Deterministic fingerprint of the s1_appends container (schema sql + ordered rows). Read-only."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        schema = con.execute(
            "SELECT type, name, sql FROM sqlite_master WHERE tbl_name=? ORDER BY type, name",
            (_CONTAINER_TABLE,),
        ).fetchall()
        rows = con.execute(
            "SELECT evidence_digest, s1_target, canonical_payload_digest, approval_row_digest, "
            "freshness_binding_digest, immutable_snapshot_ref, operator_command_id, created_at_utc "
            "FROM s1_appends ORDER BY seq"
        ).fetchall()
    finally:
        con.close()
    blob = repr(schema) + "\n" + repr(rows)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


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
    )
    if command.writer_request_digest != expected_wrd:
        return "writer_request_digest_mismatch"
    return ""


def _suspect_recovery(db_path: str) -> bool:
    if not os.path.exists(db_path):
        return True  # no container at the exact path: any sidecar or absence is unsafe
    return any(os.path.exists(db_path + suffix) for suffix in _RECOVERY_SUFFIXES_WITH_DB)


def _existing_append(db_path: str, evidence_digest: str, s1_target: str) -> bool:
    """Idempotency pre-check against the writer's append-only log. Read-only; tolerant if absent."""
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            t = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (_WRITER_TABLE,)
            ).fetchone()
            if not t:
                return False
            row = con.execute(
                "SELECT 1 FROM s1_append_log WHERE evidence_digest=? AND s1_target=?",
                (evidence_digest, s1_target),
            ).fetchone()
            return row is not None
        finally:
            con.close()
    except Exception:
        return False  # unreadable -> tamper battery will classify it


def _has_unique_index(con) -> bool:
    for idx in con.execute(f"PRAGMA index_list('{_CONTAINER_TABLE}')").fetchall():
        if idx[2] == 1:
            cols = [r[2] for r in con.execute(f"PRAGMA index_info('{idx[1]}')")]
            if cols == _UNIQUE_COLS:
                return True
    return False


def _has_append_only_triggers(con) -> bool:
    names = {
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (_CONTAINER_TABLE,)
        )
    }
    return "s1_appends_no_update" in names and "s1_appends_no_delete" in names


def _tamper_check(command: S1AppendCircuitCommand, initializer_request) -> str:
    """Read-only pre-append tamper battery on the s1_appends container. '' if clean, else a reason."""
    if os.stat(command.db_path).st_mode & 0o777 != initializer_request.expected_file_mode:
        return "file_mode_mismatch"
    try:
        con = sqlite3.connect(f"file:{command.db_path}?mode=ro", uri=True)
        try:
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            jm = con.execute("PRAGMA journal_mode").fetchone()[0]
            cols = tuple(r[1] for r in con.execute(f"PRAGMA table_info('{_CONTAINER_TABLE}')"))
            has_unique = _has_unique_index(con)
            has_triggers = _has_append_only_triggers(con)
            row_count = con.execute("SELECT COUNT(*) FROM s1_appends").fetchone()[0]
        finally:
            con.close()
    except Exception:
        return "introspection_failed"

    if isinstance(integrity, str) and integrity.lower() != "ok":
        return "integrity_failure"
    if cols != _CONTAINER_COLS:
        return "schema_mismatch"
    if not has_unique:
        return "missing_unique_constraint"
    if not has_triggers:
        return "missing_triggers"
    if jm.lower() != "wal":
        return "wrong_pragma"
    if row_count != command.expected_pre_append_row_count:
        return "nonzero_rows"
    return ""


def _execute_db_phase(command: S1AppendCircuitCommand, initializer_request) -> S1AppendCircuitResult:
    """Read-verify the container, fingerprint it, then delegate the atomic append. DB-touching only.

    Runs under the circuit single-flight guard (when supplied), so verify→fingerprint→append form one
    coherent, serialized critical section (no reader/writer interleave) — exactly the
    atomic-or-fail-closed boundary the charter requires.
    """
    # Suspect-state preflight (recovery is owned by the separate recovery charter; never clean up).
    if _suspect_recovery(command.db_path):
        return _result("BLOCKED_RECOVERY_REQUIRED", "recovery_required", command)

    # Idempotency pre-check BEFORE the strict container tamper battery, so a legitimate prior append
    # (which leaves the writer's own append-only log) is reported as a duplicate rather than tamper.
    if _existing_append(command.db_path, command.evidence_digest, command.s1_target):
        return _result("BLOCKED_DUPLICATE", "duplicate_append", command)

    reason = _tamper_check(command, initializer_request)
    if reason:
        return _result("BLOCKED_TAMPER_SUSPECT", reason, command)

    try:
        fingerprint = compute_container_fingerprint(command.db_path)
    except Exception:
        return _result("BLOCKED_TAMPER_SUSPECT", "introspection_failed", command)
    if fingerprint != command.expected_container_fingerprint:
        return _result("BLOCKED_TAMPER_SUSPECT", "fingerprint_mismatch", command, container_fingerprint=fingerprint)

    # All gates clean: delegate the atomic append to the ratified writer (its own append-only log).
    writer_request = _writer.S1AppendRequest(
        decision_status=_REVIEWABLE,
        evidence_digest=command.evidence_digest,
        s1_target=command.s1_target,
        canonical_payload_digest=command.canonical_payload_digest,
        approval_row_digest=command.approval_row_digest,
        freshness_binding_digest=command.freshness_binding_digest,
        immutable_snapshot_ref=command.immutable_snapshot_ref,
        operator_command_id=command.operator_command_id,
    )
    try:
        _writer.init_s1_append_db(command.db_path)
        wr = _writer.execute_s1_append(
            command.db_path,
            request=writer_request,
            accepted_snapshot_ref=command.immutable_snapshot_ref,
            single_flight=None,
        )
    except Exception:
        # Any writer-layer error (incl. transient "database is locked" contention) fails closed.
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
    # interleave reads with the exclusive append nor knock the lock-winner out. Losers fail closed.
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
