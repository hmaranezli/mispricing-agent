"""approval/s1_matrix_review.py — read-only S1 matrix evaluation + non-executable operator review
package.

This evaluator reads a passive REVIEWABLE S1 evidence matrix and compiles a NON-EXECUTABLE operator
review package. It is read-only and authorizes nothing:

  * Cell criticality comes from a STATIC, in-code policy (``CRITICAL_COLUMNS`` / ``NON_CRITICAL_
    COLUMNS``) — never from caller input. An unknown column criticality fails closed.
  * Only matrix ``state == "REVIEWABLE"`` is evaluable; ``BLOCKED_INCOMPLETE`` / ``FAILED`` /
    anything else fails closed.
  * A missing CRITICAL cell fails closed; a missing NON-CRITICAL cell becomes a visible warning only
    (no implicit waiver, no auto-downgrade).
  * The package carries a deterministic matrix digest bound INTO the visible summary, so a later
    UI/signature layer cannot show one thing while signing another.
  * It creates NO signing payload and NO execution token; it exposes no append/write/execute/sign/
    stream/trade/capacity surface. Every authority flag is hard-coded ``False``.

Output is a frozen ``ReviewPackage``. ``REVIEWABLE is not AUTHORIZED``.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

# Static, in-code criticality policy (per column, applied to all rows). Disjoint, covers all 18.
CRITICAL_COLUMNS = frozenset(
    {
        "source_evidence_reference",
        "evidence_value",
        "provenance_binding",
        "audit_section_binding",
        "frozen_ledger_binding",
        "pass_fail_state",
        "fail_closed_reason",
        "s1_target_reference",
        "activation_authority_state",
        "immutable_record_requirement",
    }
)
NON_CRITICAL_COLUMNS = frozenset(
    {
        "requirement_id",
        "requirement_name",
        "reviewer_identity_class",
        "operator_command_reference",
        "body_payload_dependency",
        "runtime_dependency",
        "capacity_dependency",
        "notes_boundary",
    }
)

_SATISFIED = frozenset({"EVIDENCE_PRESENT", "EVIDENCE_NOT_APPLICABLE"})
_REVIEWABLE_NOT_AUTHORIZED = "REVIEWABLE is not AUTHORIZED"


@dataclass(frozen=True)
class ReviewPackage:
    """Passive, immutable, NON-EXECUTABLE operator review package. Authorizes nothing."""

    status: str  # "OPERATOR_REVIEW_READY" | "BLOCKED"
    reason: str
    matrix_digest: str
    summary: str
    warnings: tuple = ()
    reviewable_not_authorized_statement: str = _REVIEWABLE_NOT_AUTHORIZED
    s1_append_authorized: bool = False
    production_stream_authorized: bool = False
    signing_payload_created: bool = False
    execution_token_created: bool = False
    trading_authorized: bool = False
    capacity_enabled: bool = False


def _matrix_digest(matrix) -> str:
    parts = [
        "ROWS:" + ",".join(matrix.row_ids),
        "COLS:" + ",".join(matrix.column_ids),
        "CELLS:" + "|".join(f"{r}:{c}:{s}" for (r, c, s) in matrix.cells),
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _blocked(reason: str, digest: str) -> ReviewPackage:
    summary = (
        f"{_REVIEWABLE_NOT_AUTHORIZED}\nstatus=BLOCKED reason={reason} matrix_digest={digest}"
    )
    return ReviewPackage(status="BLOCKED", reason=reason, matrix_digest=digest, summary=summary)


def compile_operator_review_package(matrix) -> ReviewPackage:
    """Read-only evaluate a passive matrix; compile a non-executable operator review package."""
    digest = _matrix_digest(matrix)

    if matrix.state != "REVIEWABLE":
        if matrix.state == "BLOCKED_INCOMPLETE":
            return _blocked("matrix_blocked_incomplete", digest)
        if matrix.state == "FAILED":
            return _blocked("matrix_failed", digest)
        return _blocked("matrix_not_reviewable", digest)

    # Every column must be classified by the static policy.
    policy_cols = CRITICAL_COLUMNS | NON_CRITICAL_COLUMNS
    for c in matrix.column_ids:
        if c not in policy_cols:
            return _blocked("unknown_cell_criticality", digest)

    warnings = []
    for (r, c, status) in matrix.cells:
        if status in _SATISFIED:
            continue
        if c in CRITICAL_COLUMNS:
            return _blocked("missing_critical_cell", digest)
        # statically non-critical → visible warning only (no implicit waiver)
        warnings.append(f"non_critical_missing:{r}:{c}")

    summary_lines = [
        _REVIEWABLE_NOT_AUTHORIZED,
        "status=OPERATOR_REVIEW_READY",
        f"matrix_digest={digest}",
        f"warnings={len(warnings)}",
    ] + warnings
    return ReviewPackage(
        status="OPERATOR_REVIEW_READY",
        reason="",
        matrix_digest=digest,
        summary="\n".join(summary_lines),
        warnings=tuple(warnings),
    )
