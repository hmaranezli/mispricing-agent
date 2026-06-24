"""approval/s1_append_execution_db_writer.py — isolated S1 Append Execution & DB Writer.

This is the FIRST physical append writer described by the ratified S1 Append Execution & DB Writer
Boundary Charter. It is deliberately constrained to a LIBRARY/TEST seam:

  * It writes ONLY to a caller-supplied SQLite ``db_path`` (tempfile / test path). There is NO
    default / production DB path and NO auto-run entrypoint.
  * It performs NO production S1 append, creates NO production stream, mutates NO approval ledger,
    and infers NO trade / order / capacity. Every authority flag on its result is hard-coded
    ``False`` — even an ``APPENDED`` row to a test DB authorizes nothing in production.
  * Freshness is NEVER a bare caller boolean. It is a ``freshness_binding_digest`` derived from the
    immutable snapshot reference plus the bound content digests, and the request's snapshot ref must
    equal the caller-supplied accepted immutable snapshot reference. No TTL / config / env /
    wall-clock is consulted.
  * Append is atomic-or-fail-closed (BEGIN IMMEDIATE / single COMMIT, rollback on any error). A
    schema-level ``UNIQUE(evidence_digest, s1_target)`` enforces "one evidence_digest + one s1_target
    -> at most one append". Duplicate/replay returns ``BLOCKED_DUPLICATE`` and writes zero rows.
  * Suspect recovery state (hot rollback journal, orphan WAL/SHM, lock residue) returns
    ``BLOCKED_RECOVERY_REQUIRED`` and performs NO cleanup/delete/auto-recovery.
  * REVIEWABLE_FOR_S1_APPEND is NOT AUTHORIZED; the writer invents no authority and exposes no
    scheduler/hook/callback/queue/worker/observer auto-promotion and no trade/order/capacity surface.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from dataclasses import dataclass

_REVIEWABLE = "REVIEWABLE_FOR_S1_APPEND"
_SIDE_CAR_SUFFIXES = ("-journal", "-wal", "-shm", "-lock")
_REQUIRED_TEXT_FIELDS = (
    "evidence_digest",
    "s1_target",
    "canonical_payload_digest",
    "approval_row_digest",
    "freshness_binding_digest",
    "immutable_snapshot_ref",
    "operator_command_id",
)


@dataclass(frozen=True)
class S1AppendRequest:
    """Immutable, explicit, caller-supplied append request. No bare freshness boolean exists."""

    decision_status: str
    evidence_digest: str
    s1_target: str
    canonical_payload_digest: str
    approval_row_digest: str
    freshness_binding_digest: str
    immutable_snapshot_ref: str
    operator_command_id: str


@dataclass(frozen=True)
class S1AppendResult:
    """Passive, immutable writer outcome. Authorizes nothing in production."""

    status: str  # APPENDED | BLOCKED | BLOCKED_DUPLICATE | BLOCKED_RECOVERY_REQUIRED
    reason: str
    result_digest: str
    append_seq: int = -1
    production_s1_append_authorized: bool = False
    production_stream_authorized: bool = False
    trading_authorized: bool = False
    capacity_enabled: bool = False
    wallet_authorized: bool = False


def compute_freshness_binding_digest(
    *,
    immutable_snapshot_ref: str,
    evidence_digest: str,
    s1_target: str,
    canonical_payload_digest: str,
    approval_row_digest: str,
) -> str:
    """Deterministic freshness binding: ties freshness to immutable refs/digests, never a boolean."""
    parts = [
        f"immutable_snapshot_ref={immutable_snapshot_ref}",
        f"evidence_digest={evidence_digest}",
        f"s1_target={s1_target}",
        f"canonical_payload_digest={canonical_payload_digest}",
        f"approval_row_digest={approval_row_digest}",
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _result_digest(status: str, reason: str, request: S1AppendRequest) -> str:
    parts = [
        f"status={status}",
        f"reason={reason}",
        f"decision_status={request.decision_status}",
        f"evidence_digest={request.evidence_digest}",
        f"s1_target={request.s1_target}",
        f"canonical_payload_digest={request.canonical_payload_digest}",
        f"approval_row_digest={request.approval_row_digest}",
        f"freshness_binding_digest={request.freshness_binding_digest}",
        f"immutable_snapshot_ref={request.immutable_snapshot_ref}",
        f"operator_command_id={request.operator_command_id}",
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _blocked(status: str, reason: str, request: S1AppendRequest) -> S1AppendResult:
    return S1AppendResult(status=status, reason=reason, result_digest=_result_digest(status, reason, request))


def init_s1_append_db(db_path: str) -> None:
    """Create the isolated append-only S1 log schema at a caller-supplied path. Idempotent."""
    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA journal_mode=DELETE")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS s1_append_log (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_digest TEXT NOT NULL,
                s1_target TEXT NOT NULL,
                canonical_payload_digest TEXT NOT NULL,
                approval_row_digest TEXT NOT NULL,
                freshness_binding_digest TEXT NOT NULL,
                immutable_snapshot_ref TEXT NOT NULL,
                operator_command_id TEXT NOT NULL,
                result_digest TEXT NOT NULL,
                UNIQUE(evidence_digest, s1_target)
            )
            """
        )
        # append-only: forbid in-place mutation / deletion of recorded evidence
        con.execute(
            "CREATE TRIGGER IF NOT EXISTS s1_append_no_update "
            "BEFORE UPDATE ON s1_append_log BEGIN "
            "SELECT RAISE(ABORT, 's1_append_log is append-only'); END"
        )
        con.execute(
            "CREATE TRIGGER IF NOT EXISTS s1_append_no_delete "
            "BEFORE DELETE ON s1_append_log BEGIN "
            "SELECT RAISE(ABORT, 's1_append_log is append-only'); END"
        )
        con.commit()
    finally:
        con.close()


def _validate(request: S1AppendRequest, accepted_snapshot_ref: str) -> str:
    """Pure, fail-closed validation. Returns '' if the request may proceed, else a block reason."""
    for field in _REQUIRED_TEXT_FIELDS:
        if not getattr(request, field):
            return "missing_required_field"
    if not accepted_snapshot_ref:
        return "stale_or_unbound_freshness"
    if request.decision_status == "AUTHORIZED":
        return "decision_treated_as_authorized"
    if request.decision_status != _REVIEWABLE:
        return "decision_not_reviewable"
    expected = compute_freshness_binding_digest(
        immutable_snapshot_ref=request.immutable_snapshot_ref,
        evidence_digest=request.evidence_digest,
        s1_target=request.s1_target,
        canonical_payload_digest=request.canonical_payload_digest,
        approval_row_digest=request.approval_row_digest,
    )
    if request.freshness_binding_digest != expected:
        return "freshness_binding_mismatch"
    if request.immutable_snapshot_ref != accepted_snapshot_ref:
        return "stale_or_unbound_freshness"
    return ""


def _suspect_recovery(db_path: str) -> bool:
    """Detect hot journal / orphan WAL/SHM / lock residue. Detection only — never deletes."""
    return any(os.path.exists(db_path + suffix) for suffix in _SIDE_CAR_SUFFIXES)


def _atomic_append(db_path: str, request: S1AppendRequest) -> S1AppendResult:
    """Single atomic transaction. Commit the exact reviewed row, or roll back leaving nothing."""
    result_digest = _result_digest("APPENDED", "", request)
    try:
        con = sqlite3.connect(db_path, isolation_level=None)
    except Exception:
        return _blocked("BLOCKED", "write_failed", request)
    try:
        con.execute("PRAGMA journal_mode=DELETE")
        con.execute("BEGIN IMMEDIATE")
        try:
            cur = con.execute(
                "INSERT INTO s1_append_log ("
                "evidence_digest, s1_target, canonical_payload_digest, approval_row_digest, "
                "freshness_binding_digest, immutable_snapshot_ref, operator_command_id, result_digest"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    request.evidence_digest,
                    request.s1_target,
                    request.canonical_payload_digest,
                    request.approval_row_digest,
                    request.freshness_binding_digest,
                    request.immutable_snapshot_ref,
                    request.operator_command_id,
                    result_digest,
                ),
            )
            seq = cur.lastrowid
            con.execute("COMMIT")
        except sqlite3.IntegrityError:
            con.execute("ROLLBACK")
            return _blocked("BLOCKED_DUPLICATE", "duplicate_append", request)
        except Exception:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
            return _blocked("BLOCKED", "write_failed", request)
        return S1AppendResult(status="APPENDED", reason="", result_digest=result_digest, append_seq=seq)
    except Exception:
        return _blocked("BLOCKED", "write_failed", request)
    finally:
        try:
            con.close()
        except Exception:
            pass


def execute_s1_append(
    db_path: str,
    *,
    request: S1AppendRequest,
    accepted_snapshot_ref: str,
    single_flight: "threading.Lock | None" = None,
) -> S1AppendResult:
    """Gated, atomic, fail-closed append into a caller-supplied SQLite path. Authorizes nothing."""
    reason = _validate(request, accepted_snapshot_ref)
    if reason:
        return _blocked("BLOCKED", reason, request)

    lock = single_flight if single_flight is not None else threading.Lock()
    if not lock.acquire(blocking=False):
        return _blocked("BLOCKED", "race_lock_unavailable", request)
    try:
        # Recovery detection runs UNDER the single-flight lock: only a quiescent DB is observed, so a
        # concurrent live transaction's transient rollback journal is never misread as orphan/suspect
        # residue. A genuinely orphaned journal/WAL/SHM/lock (e.g. from a crashed process) is still
        # caught on first acquisition and fails closed with no cleanup.
        if _suspect_recovery(db_path):
            return _blocked("BLOCKED_RECOVERY_REQUIRED", "recovery_required", request)
        return _atomic_append(db_path, request)
    finally:
        lock.release()
