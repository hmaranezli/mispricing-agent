"""approval/s1_append_execution_db_writer.py — isolated S1 Append Execution & DB Writer.

This is the physical append writer described by the ratified S1 Append Execution & DB Writer Boundary
Charter, UNIFIED (Schema & Journal Unification) onto the single canonical container:

  * The ONE canonical append-only table is ``s1_appends`` (provisioned by the shared genesis in
    ``approval.live_s1_db_initialization``); the legacy ``s1_append`` + ``_log`` table is NOT used.
    There is NO dual-write, NO shadow-write, and NO compatibility shim.
  * The ONE canonical journal mode is **WAL**; the durability floor is **synchronous=FULL**. Both are
    set and verified by the writer preflight before any append.
  * It writes ONLY to a caller-supplied SQLite ``db_path`` (tempfile / test path). There is NO
    default / production DB path and NO auto-run entrypoint.
  * It performs NO production S1 append, creates NO production stream, mutates NO approval ledger,
    and infers NO trade / order / capacity. Every authority flag on its result is hard-coded
    ``False`` — even an ``APPENDED`` row to a test DB authorizes nothing in production.
  * Freshness is NEVER a bare caller boolean. It is a ``freshness_binding_digest`` derived from the
    immutable snapshot reference plus the bound content digests, and the request's snapshot ref must
    equal the caller-supplied accepted immutable snapshot reference. No TTL / config / env /
    wall-clock is consulted.
  * Append is atomic-or-fail-closed (BEGIN IMMEDIATE / single COMMIT, rollback on any error). The
    canonical ``UNIQUE(evidence_digest, s1_target)`` enforces "one evidence_digest + one s1_target ->
    at most one append". Duplicate/replay returns ``BLOCKED_DUPLICATE`` and writes zero rows.
  * Suspect recovery state (hot rollback journal, lock residue) returns ``BLOCKED_RECOVERY_REQUIRED``
    and performs NO cleanup / delete / checkpoint / vacuum / migration. WAL/SHM are expected
    companions of a WAL container, not suspect.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from dataclasses import dataclass

from approval import live_s1_db_initialization as _init

_REVIEWABLE = "REVIEWABLE_FOR_S1_APPEND"
# WAL/SHM are expected companions of the canonical WAL container; only a hot rollback journal or lock
# residue (or any sidecar when the DB is absent) is treated as suspect.
_RECOVERY_SUFFIXES_ANY = ("-journal", "-wal", "-shm", "-lock")
_RECOVERY_SUFFIXES_WITH_DB = ("-journal", "-lock")
_REQUIRED_TEXT_FIELDS = (
    "evidence_digest",
    "s1_target",
    "canonical_payload_digest",
    "approval_row_digest",
    "freshness_binding_digest",
    "immutable_snapshot_ref",
    "operator_command_id",
    "created_at_utc",
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
    created_at_utc: str


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
        f"created_at_utc={request.created_at_utc}",
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _blocked(status: str, reason: str, request: S1AppendRequest) -> S1AppendResult:
    return S1AppendResult(status=status, reason=reason, result_digest=_result_digest(status, reason, request))


def init_s1_append_db(db_path: str) -> None:
    """Provision the canonical append-only ``s1_appends`` container at a caller path (test genesis)."""
    con = sqlite3.connect(db_path)
    try:
        _init.create_canonical_schema(con)
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
    """Detect hot journal / lock residue (or any orphan sidecar without a DB). Never deletes."""
    db_exists = os.path.exists(db_path)
    suffixes = _RECOVERY_SUFFIXES_WITH_DB if db_exists else _RECOVERY_SUFFIXES_ANY
    return any(os.path.exists(db_path + suffix) for suffix in suffixes)


def _atomic_append(db_path: str, request: S1AppendRequest) -> S1AppendResult:
    """Single atomic transaction into canonical s1_appends. Commit the exact row, or roll back."""
    result_digest = _result_digest("APPENDED", "", request)
    try:
        con = sqlite3.connect(db_path, isolation_level=None)
    except Exception:
        return _blocked("BLOCKED", "write_failed", request)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
        con.execute("BEGIN IMMEDIATE")
        try:
            cur = con.execute(
                "INSERT INTO s1_appends ("
                "evidence_digest, s1_target, canonical_payload_digest, approval_row_digest, "
                "freshness_binding_digest, immutable_snapshot_ref, operator_command_id, created_at_utc"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    request.evidence_digest,
                    request.s1_target,
                    request.canonical_payload_digest,
                    request.approval_row_digest,
                    request.freshness_binding_digest,
                    request.immutable_snapshot_ref,
                    request.operator_command_id,
                    request.created_at_utc,
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
    """Gated, atomic, fail-closed append into the canonical s1_appends container. Authorizes nothing."""
    reason = _validate(request, accepted_snapshot_ref)
    if reason:
        return _blocked("BLOCKED", reason, request)

    lock = single_flight if single_flight is not None else threading.Lock()
    if not lock.acquire(blocking=False):
        return _blocked("BLOCKED", "race_lock_unavailable", request)
    try:
        # Recovery detection runs UNDER the single-flight lock: only a quiescent DB is observed.
        if _suspect_recovery(db_path):
            return _blocked("BLOCKED_RECOVERY_REQUIRED", "recovery_required", request)
        # Canonical preflight: WAL + synchronous=FULL floor + shared schema/journal fingerprints.
        preflight = _init.verify_canonical_container(db_path)
        if preflight:
            return _blocked("BLOCKED", preflight, request)
        return _atomic_append(db_path, request)
    finally:
        lock.release()
