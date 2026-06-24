"""approval/approval_ledger_db.py — isolated, append-only, passive Human Approval Ledger DB.

This ledger persists ONLY passive evidence records derived from the ratified verification slices
(Human Approval Package Verification + Day-Zero Trust Anchor / Production Verifier Wiring). It is
fully independent of S1: it imports no S1 / raw-ledger / network / wallet / signing / trading /
paper-live / capacity module, and stores nothing that means "approved to execute", "S1 authorized",
"trade authorized", or "capacity enabled".

Append-only at the application API level: there is NO update / delete / mutation function, and the
table carries SQLite UPDATE / DELETE triggers that abort. Every stored record hard-codes its
non-authority flags to ``False``. Two honesty fields are recorded on every row:

  * ``ceremony_evidence_kind = "recorded_claim_not_physical_proof"`` — the ceremony marker is a
    recorded claim, never a mathematical proof that a physical ceremony truly occurred.
  * ``fingerprint_entropy_claim = "shape_only_not_entropy_proof"`` — a sha256-shaped fingerprint is
    a shape, never a proof of key entropy or genuineness.

All outputs are passive frozen dataclasses with a deterministic fail-closed ``reason``.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

PASSIVE_STATUS = "PASSIVE_EVIDENCE_RECORDED"
_ALLOWED_STATUSES = frozenset({PASSIVE_STATUS})

_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")

_CEREMONY_EVIDENCE_KIND = "recorded_claim_not_physical_proof"
_FINGERPRINT_ENTROPY_CLAIM = "shape_only_not_entropy_proof"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS approval_ledger (
    append_sequence            INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_record_id         TEXT NOT NULL,
    command_scope              TEXT NOT NULL,
    status                     TEXT NOT NULL,
    verifier_identity          TEXT NOT NULL,
    trust_anchor_fingerprint   TEXT NOT NULL,
    ceremony_evidence_marker   TEXT NOT NULL,
    ceremony_evidence_kind     TEXT NOT NULL,
    fingerprint_entropy_claim  TEXT NOT NULL,
    s1_append_authorized       INTEGER NOT NULL DEFAULT 0,
    s1_matrix_authorized       INTEGER NOT NULL DEFAULT 0,
    trading_authorized         INTEGER NOT NULL DEFAULT 0,
    paper_live_authorized      INTEGER NOT NULL DEFAULT 0,
    capacity_authorized        INTEGER NOT NULL DEFAULT 0
);
CREATE TRIGGER IF NOT EXISTS approval_ledger_no_update
BEFORE UPDATE ON approval_ledger
BEGIN
    SELECT RAISE(ABORT, 'approval_ledger is append-only');
END;
CREATE TRIGGER IF NOT EXISTS approval_ledger_no_delete
BEFORE DELETE ON approval_ledger
BEGIN
    SELECT RAISE(ABORT, 'approval_ledger is append-only');
END;
"""


@dataclass(frozen=True)
class AppendResult:
    """Passive, immutable append outcome."""

    valid: bool
    reason: str
    append_sequence: int = -1


@dataclass(frozen=True)
class StoredApprovalRecord:
    """Passive, immutable stored record. All authority flags are constant False."""

    append_sequence: int
    approval_record_id: str
    command_scope: str
    status: str
    verifier_identity: str
    trust_anchor_fingerprint: str
    ceremony_evidence_marker: str
    ceremony_evidence_kind: str
    fingerprint_entropy_claim: str
    s1_append_authorized: bool
    s1_matrix_authorized: bool
    trading_authorized: bool
    paper_live_authorized: bool
    capacity_authorized: bool


def init_approval_ledger(db_path: str) -> None:
    """Create the isolated append-only approval ledger at an explicit path (no implicit/live path)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _fingerprint_reason(fp) -> str:
    """Return a deterministic fail-closed reason for a fingerprint, or '' if acceptable."""
    if not isinstance(fp, str) or not _FINGERPRINT_RE.match(fp):
        return "malformed_fingerprint"
    if fp == "0" * 64:
        return "placeholder_all_zero_fingerprint"
    if len(set(fp)) == 1:
        return "placeholder_repeated_char_fingerprint"
    return ""


def append_passive_record(
    db_path: str,
    *,
    verifier_result,
    trust_anchor_result,
    approval_record_id: str,
    command_scope: str,
    public_key_fingerprint: str,
    ceremony_evidence_marker: str,
    status: str,
) -> AppendResult:
    """Append one passive approval-evidence record. Fails closed on any missing/invalid input.

    A successful append records passive evidence ONLY; it authorizes nothing.
    """
    if status not in _ALLOWED_STATUSES:
        return AppendResult(False, "ambiguous_approval_status")
    if verifier_result is None:
        return AppendResult(False, "missing_verifier_provenance")
    if trust_anchor_result is None:
        return AppendResult(False, "missing_trust_anchor_provenance")
    if getattr(verifier_result, "valid", False) is not True:
        return AppendResult(False, "invalid_verifier_result")
    if getattr(trust_anchor_result, "valid", False) is not True:
        return AppendResult(False, "invalid_trust_anchor_result")
    if not approval_record_id:
        return AppendResult(False, "missing_approval_record_id")
    if not command_scope:
        return AppendResult(False, "missing_command_scope")
    if not ceremony_evidence_marker:
        return AppendResult(False, "missing_ceremony_evidence")

    fp_reason = _fingerprint_reason(public_key_fingerprint)
    if fp_reason:
        return AppendResult(False, fp_reason)

    verifier_identity = getattr(verifier_result, "identity", "")
    if not verifier_identity:
        return AppendResult(False, "missing_verifier_identity")

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO approval_ledger (
                approval_record_id, command_scope, status, verifier_identity,
                trust_anchor_fingerprint, ceremony_evidence_marker, ceremony_evidence_kind,
                fingerprint_entropy_claim
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_record_id,
                command_scope,
                status,
                verifier_identity,
                public_key_fingerprint,
                ceremony_evidence_marker,
                _CEREMONY_EVIDENCE_KIND,
                _FINGERPRINT_ENTROPY_CLAIM,
            ),
        )
        conn.commit()
        seq = int(cur.lastrowid)
    finally:
        conn.close()
    return AppendResult(True, "", seq)


def fetch_record(db_path: str, append_sequence: int):
    """Read one passive record (read-only). Returns None if absent."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT append_sequence, approval_record_id, command_scope, status,
                   verifier_identity, trust_anchor_fingerprint, ceremony_evidence_marker,
                   ceremony_evidence_kind, fingerprint_entropy_claim,
                   s1_append_authorized, s1_matrix_authorized, trading_authorized,
                   paper_live_authorized, capacity_authorized
            FROM approval_ledger WHERE append_sequence = ?
            """,
            (append_sequence,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return StoredApprovalRecord(
        append_sequence=row[0],
        approval_record_id=row[1],
        command_scope=row[2],
        status=row[3],
        verifier_identity=row[4],
        trust_anchor_fingerprint=row[5],
        ceremony_evidence_marker=row[6],
        ceremony_evidence_kind=row[7],
        fingerprint_entropy_claim=row[8],
        s1_append_authorized=bool(row[9]),
        s1_matrix_authorized=bool(row[10]),
        trading_authorized=bool(row[11]),
        paper_live_authorized=bool(row[12]),
        capacity_authorized=bool(row[13]),
    )


def record_count(db_path: str) -> int:
    """Number of passive records (read-only)."""
    conn = sqlite3.connect(db_path)
    try:
        return int(conn.execute("SELECT COUNT(*) FROM approval_ledger").fetchone()[0])
    finally:
        conn.close()


def list_sequences(db_path: str):
    """Deterministic ascending list of append_sequence values (read-only)."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT append_sequence FROM approval_ledger ORDER BY append_sequence ASC"
        ).fetchall()
    finally:
        conn.close()
    return [int(r[0]) for r in rows]
