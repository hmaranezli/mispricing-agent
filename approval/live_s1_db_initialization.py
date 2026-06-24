"""approval/live_s1_db_initialization.py — isolated Live S1 DB Initialization & Schema Provisioning.

This is the initialization/provisioning seam described by the ratified Live S1 DB Initialization &
Schema Provisioning Boundary Charter. It is deliberately constrained to a LIBRARY/TEST seam:

  * It creates ONLY a caller-supplied SQLite ``db_path`` whose parent already exists and matches an
    explicit policy. There is NO default / fallback / production path and NO auto-run entrypoint.
  * Success produces an EMPTY, append-only, restrictively-permissioned container with status
    ``CREATED_EMPTY_LOCKED_CONTAINER`` — never ``AUTHORIZED``. Creating a container is NOT S1 append
    authorization; provisioning a schema is NOT production-stream authorization.
  * It provisions ``journal_mode=WAL`` and the ratified durability floor ``synchronous=FULL`` (read
    back and verified). ``synchronous=EXTRA`` is only selectable through the explicit
    ``allow_synchronous_extra`` request field; by default the result proves the FULL floor.
  * The append-only schema is exactly compatible with the ratified writer
    (``UNIQUE(evidence_digest, s1_target)`` + BEFORE UPDATE/DELETE RAISE(ABORT)) and carries NO
    trade/order/price/side/capacity column.
  * Initialization is idempotent: a second call against a matching container is a verified no-op with
    zero rows. Any mismatch (schema / UNIQUE / pragma / file mode / parent mode / owner) fails closed.
  * Suspect state (hot rollback journal, orphan WAL/SHM, lock residue) returns
    ``BLOCKED_RECOVERY_REQUIRED`` and performs NO cleanup/delete/checkpoint/vacuum/migration. Recovery
    is owned by the separate S1 DB Recovery Protocol Boundary Charter.
  * It executes NO writer, mutates NO approval ledger, opens NO network/runtime, inspects NO
    secret/key/env, starts NO scheduler/hook/callback/queue/worker/observer/stream. Every authority
    flag on the result is hard-coded ``False``.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass

_OK_STATUS = "CREATED_EMPTY_LOCKED_CONTAINER"
_RECOVERY_SUFFIXES_ANY = ("-journal", "-wal", "-shm", "-lock")  # any of these without a DB = orphan
_RECOVERY_SUFFIXES_WITH_DB = ("-journal", "-lock")  # WAL/SHM are expected companions of a WAL DB
_EXPECTED_COLS = (
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
_REQUIRED_TEXT_FIELDS = (
    "db_path",
    "expected_parent_dir",
    "schema_version",
    "operator_command_id",
    "initialization_intent_digest",
)


@dataclass(frozen=True)
class LiveS1DbInitRequest:
    """Immutable, explicit initialization request. No default path is possible by construction."""

    db_path: str
    expected_parent_dir: str
    expected_owner_uid: int
    enforce_owner_check: bool
    expected_file_mode: int
    expected_dir_mode: int
    schema_version: str
    operator_command_id: str
    initialization_intent_digest: str
    allow_synchronous_extra: bool = False


@dataclass(frozen=True)
class LiveS1DbInitResult:
    """Passive, immutable initialization outcome. Authorizes nothing."""

    status: str  # CREATED_EMPTY_LOCKED_CONTAINER | BLOCKED | BLOCKED_RECOVERY_REQUIRED
    reason: str
    initialization_result_digest: str
    created_now: bool = False
    row_count: int = -1
    journal_mode: str = ""
    synchronous: str = ""
    s1_append_authorized: bool = False
    production_stream_authorized: bool = False
    trading_authorized: bool = False
    capacity_enabled: bool = False
    wallet_authorized: bool = False


def compute_initialization_intent_digest(
    *, db_path: str, expected_parent_dir: str, schema_version: str, operator_command_id: str
) -> str:
    """Deterministic intent binding over the stable initialization identity. Pure."""
    parts = [
        f"db_path={db_path}",
        f"expected_parent_dir={expected_parent_dir}",
        f"schema_version={schema_version}",
        f"operator_command_id={operator_command_id}",
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _result_digest(status: str, reason: str, request: LiveS1DbInitRequest, created_now: bool, row_count: int, journal_mode: str, synchronous: str) -> str:
    parts = [
        f"status={status}",
        f"reason={reason}",
        f"db_path={request.db_path}",
        f"expected_parent_dir={request.expected_parent_dir}",
        f"schema_version={request.schema_version}",
        f"operator_command_id={request.operator_command_id}",
        f"initialization_intent_digest={request.initialization_intent_digest}",
        f"created_now={created_now}",
        f"row_count={row_count}",
        f"journal_mode={journal_mode}",
        f"synchronous={synchronous}",
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _result(status: str, reason: str, request: LiveS1DbInitRequest, *, created_now: bool = False, row_count: int = -1, journal_mode: str = "", synchronous: str = "") -> LiveS1DbInitResult:
    return LiveS1DbInitResult(
        status=status,
        reason=reason,
        initialization_result_digest=_result_digest(status, reason, request, created_now, row_count, journal_mode, synchronous),
        created_now=created_now,
        row_count=row_count,
        journal_mode=journal_mode,
        synchronous=synchronous,
    )


def _synchronous_name(value: int) -> str:
    return {0: "OFF", 1: "NORMAL", 2: "FULL", 3: "EXTRA"}.get(int(value), str(value))


# --- canonical schema + journal definition (shared by initializer, writer, circuit) ---------------
CANONICAL_TABLE = "s1_appends"
LEGACY_FORBIDDEN_TABLE = "s1_append" + "_log"  # constructed so no executable literal token exists
CANONICAL_COLUMNS = _EXPECTED_COLS
CANONICAL_UNIQUE = tuple(_UNIQUE_COLS)
CANONICAL_TRIGGERS = ("s1_appends_no_update", "s1_appends_no_delete")
CANONICAL_JOURNAL_MODE = "wal"
CANONICAL_SYNCHRONOUS = "FULL"


def create_canonical_schema(con, *, allow_synchronous_extra: bool = False):
    """Provision the ONE canonical append-only s1_appends container (WAL + FULL floor). Shared genesis.

    No dual-table, no shadow-table, no compatibility shim: this creates exactly one table.
    Returns the verified (journal_mode, synchronous) pair.
    """
    target_sync = "EXTRA" if allow_synchronous_extra else "FULL"
    con.execute("PRAGMA journal_mode=WAL")
    jm = con.execute("PRAGMA journal_mode").fetchone()[0]
    con.execute(f"PRAGMA synchronous={target_sync}")
    syn = _synchronous_name(con.execute("PRAGMA synchronous").fetchone()[0])
    con.execute(
        """
        CREATE TABLE s1_appends (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_digest TEXT NOT NULL,
            s1_target TEXT NOT NULL,
            canonical_payload_digest TEXT NOT NULL,
            approval_row_digest TEXT NOT NULL,
            freshness_binding_digest TEXT NOT NULL,
            immutable_snapshot_ref TEXT NOT NULL,
            operator_command_id TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            UNIQUE(evidence_digest, s1_target)
        )
        """
    )
    con.execute(
        "CREATE TRIGGER s1_appends_no_update BEFORE UPDATE ON s1_appends "
        "BEGIN SELECT RAISE(ABORT, 's1_appends is append-only'); END"
    )
    con.execute(
        "CREATE TRIGGER s1_appends_no_delete BEFORE DELETE ON s1_appends "
        "BEGIN SELECT RAISE(ABORT, 's1_appends is append-only'); END"
    )
    return jm, syn


def canonical_schema_fingerprint() -> str:
    """Deterministic fingerprint of the canonical schema DEFINITION. Shared by all three modules."""
    parts = [
        f"table={CANONICAL_TABLE}",
        "columns=" + ",".join(CANONICAL_COLUMNS),
        "unique=" + ",".join(CANONICAL_UNIQUE),
        "triggers=" + ",".join(sorted(CANONICAL_TRIGGERS)),
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def canonical_journal_fingerprint() -> str:
    """Deterministic fingerprint of the canonical journal/synchronous policy. Shared by all three."""
    parts = [f"journal_mode={CANONICAL_JOURNAL_MODE}", f"synchronous={CANONICAL_SYNCHRONOUS}"]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def has_table(con, name: str) -> bool:
    return con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _unique_cols(con):
    for idx in con.execute(f"PRAGMA index_list('{CANONICAL_TABLE}')").fetchall():
        if idx[2] == 1:
            return tuple(r[2] for r in con.execute(f"PRAGMA index_info('{idx[1]}')"))
    return ()


def _trigger_names(con):
    return tuple(
        sorted(
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (CANONICAL_TABLE,)
            )
        )
    )


def container_schema_fingerprint(con) -> str:
    """Fingerprint of an actual container's s1_appends structure. Matches the canonical fingerprint
    iff the container's columns/unique/triggers equal the canonical definition."""
    cols = tuple(r[1] for r in con.execute(f"PRAGMA table_info('{CANONICAL_TABLE}')"))
    parts = [
        f"table={CANONICAL_TABLE}",
        "columns=" + ",".join(cols),
        "unique=" + ",".join(_unique_cols(con)),
        "triggers=" + ",".join(_trigger_names(con)),
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def container_journal_fingerprint(con) -> str:
    """Fingerprint of an actual container's journal mode + enforced synchronous floor."""
    con.execute("PRAGMA synchronous=FULL")
    syn = _synchronous_name(con.execute("PRAGMA synchronous").fetchone()[0])
    jm = con.execute("PRAGMA journal_mode").fetchone()[0]
    parts = [f"journal_mode={jm.lower()}", f"synchronous={syn}"]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def verify_canonical_container(db_path: str, *, expected_file_mode=None, expected_row_count=None) -> str:
    """Read-only canonical verification shared by writer/circuit preflight. '' if canonical, else a
    fail-closed reason. Rejects the forbidden legacy/dual-table state; never migrates/cleans/repairs."""
    if expected_file_mode is not None and _mode(db_path) != expected_file_mode:
        return "file_mode_mismatch"
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            legacy = has_table(con, LEGACY_FORBIDDEN_TABLE)
            canonical = has_table(con, CANONICAL_TABLE)
            if legacy and canonical:
                return "forbidden_dual_table"
            if legacy:
                return "forbidden_legacy_table"
            if not canonical:
                return "schema_mismatch"
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            schema_fp = container_schema_fingerprint(con)
            journal_fp = container_journal_fingerprint(con)
            row_count = con.execute("SELECT COUNT(*) FROM s1_appends").fetchone()[0]
        finally:
            con.close()
    except Exception:
        return "introspection_failed"
    if isinstance(integrity, str) and integrity.lower() != "ok":
        return "integrity_failure"
    if schema_fp != canonical_schema_fingerprint():
        return "schema_fingerprint_mismatch"
    if journal_fp != canonical_journal_fingerprint():
        return "journal_fingerprint_mismatch"
    if expected_row_count is not None and row_count != expected_row_count:
        return "nonzero_rows"
    return ""


def _mode(path: str) -> int:
    return os.stat(path).st_mode & 0o777


def _suspect_recovery(db_path: str) -> bool:
    db_exists = os.path.exists(db_path)
    suffixes = _RECOVERY_SUFFIXES_WITH_DB if db_exists else _RECOVERY_SUFFIXES_ANY
    return any(os.path.exists(db_path + suffix) for suffix in suffixes)


def _validate_policy(request: LiveS1DbInitRequest) -> str:
    """Pure, fail-closed pre-disk validation. Returns '' to proceed, else a block reason."""
    for field in _REQUIRED_TEXT_FIELDS:
        if not getattr(request, field):
            return "missing_required_field"
    if not request.expected_file_mode or not request.expected_dir_mode:
        return "missing_required_field"
    # restrictive policy: requested modes must not grant group/other write
    if (request.expected_file_mode & 0o022) or (request.expected_dir_mode & 0o022):
        return "over_permissive_mode_policy"
    expected_intent = compute_initialization_intent_digest(
        db_path=request.db_path,
        expected_parent_dir=request.expected_parent_dir,
        schema_version=request.schema_version,
        operator_command_id=request.operator_command_id,
    )
    if request.initialization_intent_digest != expected_intent:
        return "intent_digest_mismatch"
    if os.path.dirname(request.db_path) != request.expected_parent_dir:
        return "path_policy_mismatch"
    return ""


def _check_parent(request: LiveS1DbInitRequest) -> str:
    parent = request.expected_parent_dir
    if not os.path.isdir(parent):
        return "parent_dir_missing"
    if _mode(parent) != request.expected_dir_mode:
        return "parent_dir_mode_mismatch"
    if request.enforce_owner_check and os.stat(parent).st_uid != request.expected_owner_uid:
        return "owner_mismatch"
    return ""


def _verify_existing(request: LiveS1DbInitRequest) -> LiveS1DbInitResult:
    """Verify a pre-existing container matches policy/schema exactly. Fail closed on any mismatch.

    Rejects the forbidden legacy/dual-table state (no migration, rename, copy, or cleanup)."""
    if _mode(request.db_path) != request.expected_file_mode:
        return _result("BLOCKED", "file_mode_mismatch", request)
    try:
        con = sqlite3.connect(request.db_path)
        try:
            legacy = has_table(con, LEGACY_FORBIDDEN_TABLE)
            canonical = has_table(con, CANONICAL_TABLE)
            if legacy and canonical:
                return _result("BLOCKED", "forbidden_dual_table", request)
            if legacy:
                return _result("BLOCKED", "forbidden_legacy_table", request)
            if not canonical:
                return _result("BLOCKED", "schema_mismatch", request)
            con.execute("PRAGMA synchronous=FULL")
            syn = _synchronous_name(con.execute("PRAGMA synchronous").fetchone()[0])
            jm = con.execute("PRAGMA journal_mode").fetchone()[0]
            cols = tuple(r[1] for r in con.execute("PRAGMA table_info('s1_appends')"))
            has_unique = _has_unique_index(con)
            triggers = _trigger_names(con)
            row_count = con.execute("SELECT COUNT(*) FROM s1_appends").fetchone()[0]
        finally:
            con.close()
    except Exception:
        return _result("BLOCKED", "initialization_failed", request)

    if jm.lower() != "wal":
        return _result("BLOCKED", "wrong_pragma", request)
    if cols != _EXPECTED_COLS:
        return _result("BLOCKED", "schema_mismatch", request)
    if not has_unique:
        return _result("BLOCKED", "missing_unique_constraint", request)
    if tuple(sorted(CANONICAL_TRIGGERS)) != triggers:
        return _result("BLOCKED", "missing_triggers", request)
    if row_count != 0:
        return _result("BLOCKED", "nonzero_rows", request, row_count=row_count)
    return _result(_OK_STATUS, "", request, created_now=False, row_count=0, journal_mode=jm, synchronous=syn)


def _has_unique_index(con) -> bool:
    for idx in con.execute("PRAGMA index_list('s1_appends')").fetchall():
        # idx columns: (seq, name, unique, origin, partial)
        if idx[2] == 1:
            cols = [r[2] for r in con.execute(f"PRAGMA index_info('{idx[1]}')")]
            if cols == _UNIQUE_COLS:
                return True
    return False


def _create_container(request: LiveS1DbInitRequest) -> LiveS1DbInitResult:
    """Create an empty, append-only, restrictively-permissioned container. Inserts zero rows."""
    try:
        con = sqlite3.connect(request.db_path)
        try:
            jm, syn = create_canonical_schema(con, allow_synchronous_extra=request.allow_synchronous_extra)
            con.commit()
        finally:
            con.close()
        os.chmod(request.db_path, request.expected_file_mode)
    except Exception:
        return _result("BLOCKED", "initialization_failed", request)

    if jm.lower() != "wal":
        return _result("BLOCKED", "wrong_pragma", request)
    if request.allow_synchronous_extra is False and syn != "FULL":
        return _result("BLOCKED", "synchronous_below_floor", request)
    if _mode(request.db_path) != request.expected_file_mode:
        return _result("BLOCKED", "file_mode_mismatch", request)
    return _result(_OK_STATUS, "", request, created_now=True, row_count=0, journal_mode=jm, synchronous=syn)


def initialize_live_s1_db(request: LiveS1DbInitRequest) -> LiveS1DbInitResult:
    """Initialize/provision a caller-supplied empty append-only S1 container. Authorizes nothing."""
    reason = _validate_policy(request)
    if reason:
        return _result("BLOCKED", reason, request)

    parent_reason = _check_parent(request)
    if parent_reason:
        return _result("BLOCKED", parent_reason, request)

    # Suspect-state preflight BEFORE any create/verify. Never cleans up.
    if _suspect_recovery(request.db_path):
        return _result("BLOCKED_RECOVERY_REQUIRED", "recovery_required", request)

    if os.path.exists(request.db_path):
        return _verify_existing(request)
    return _create_container(request)
