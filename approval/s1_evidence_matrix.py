"""approval/s1_evidence_matrix.py — passive S1 Stream Authorization Evidence Matrix construction.

This builds the S1 stream authorization evidence matrix as a REVIEWABLE object ONLY, per the already
ratified S1 Stream Authorization Evidence Matrix Construction Boundary Charter. It is a pure,
deterministic, side-effect-free constructor:

  * 18 row classes × 18 columns = 324 cells, with stable deterministic IDs.
  * The matrix may become ``REVIEWABLE`` only — never ``AUTHORIZED``. Every cell is passive evidence.
  * Missing required evidence ⇒ ``BLOCKED_INCOMPLETE``. Unknown row/column/evidence key, duplicate
    row/column id, non-18 counts, audit summary not PASS/COMPLETE, or missing approval-ledger
    reference ⇒ ``FAILED`` (fail closed).
  * A clean audit summary is REQUIRED but NOT SUFFICIENT; approval-ledger references are REQUIRED but
    NOT SUFFICIENT.
  * The output hard-codes false authority flags: ``s1_append_authorized=False``,
    ``production_stream_authorized=False``, ``trading_authorized=False``, ``capacity_enabled=False``.

It reads no DB, opens no file, makes no network call, and authorizes nothing.
"""
from __future__ import annotations

from dataclasses import dataclass

# 18 row classes (stable, deterministic order) — from the ratified construction boundary charter.
ROW_CLASSES = (
    "clean_audit_proof",
    "frozen_ledger_proof",
    "source_parity_proof",
    "http_integrity_proof",
    "cycle_contiguity_proof",
    "timestamp_order_proof",
    "clock_anomaly_proof",
    "provenance_hash_proof",
    "permission_proof",
    "s1_absence_proof",
    "raw_body_non_read_proof",
    "no_export_proof",
    "no_runtime_touch_proof",
    "no_capacity_proof",
    "no_paper_live_proof",
    "human_approval_blocker_proof",
    "eligible_is_not_trigger_proof",
    "future_command_shape_proof",
)

# 18 columns (stable, deterministic order) — from the ratified construction boundary charter.
COLUMNS = (
    "requirement_id",
    "requirement_name",
    "source_evidence_reference",
    "evidence_value",
    "provenance_binding",
    "audit_section_binding",
    "frozen_ledger_binding",
    "pass_fail_state",
    "fail_closed_reason",
    "reviewer_identity_class",
    "operator_command_reference",
    "s1_target_reference",
    "body_payload_dependency",
    "runtime_dependency",
    "capacity_dependency",
    "activation_authority_state",
    "immutable_record_requirement",
    "notes_boundary",
)

# Passive evidence-status vocabulary. PRESENT / NOT_APPLICABLE satisfy a cell; the rest do not.
_SATISFIED = frozenset({"EVIDENCE_PRESENT", "EVIDENCE_NOT_APPLICABLE"})
_KNOWN_STATUS = _SATISFIED | frozenset({"EVIDENCE_MISSING", "EVIDENCE_BLOCKED"})


@dataclass(frozen=True)
class S1EvidenceMatrix:
    """Passive, immutable evidence matrix. Reviewable at most; authorizes nothing."""

    state: str  # "REVIEWABLE" | "BLOCKED_INCOMPLETE" | "FAILED"
    reason: str
    row_ids: tuple = ()
    column_ids: tuple = ()
    cell_count: int = 0
    cells: tuple = ()
    s1_append_authorized: bool = False
    production_stream_authorized: bool = False
    trading_authorized: bool = False
    capacity_enabled: bool = False


def _failed(reason: str) -> S1EvidenceMatrix:
    return S1EvidenceMatrix(state="FAILED", reason=reason)


def construct_s1_evidence_matrix(
    *,
    audit_summary,
    approval_ledger_refs,
    evidence,
    row_ids=ROW_CLASSES,
    column_ids=COLUMNS,
) -> S1EvidenceMatrix:
    """Construct a passive, reviewable S1 evidence matrix. Pure and fail-closed."""
    row_ids = tuple(row_ids)
    column_ids = tuple(column_ids)

    # Shape gates.
    if len(row_ids) != 18:
        return _failed("row_count_must_be_18")
    if len(column_ids) != 18:
        return _failed("column_count_must_be_18")
    if len(set(row_ids)) != len(row_ids):
        return _failed("duplicate_row_id")
    if len(set(column_ids)) != len(column_ids):
        return _failed("duplicate_column_id")

    # Required-but-not-sufficient inputs.
    if not isinstance(audit_summary, dict):
        return _failed("missing_audit_summary")
    if audit_summary.get("status") != "PASS_COMPLETE":
        return _failed("audit_summary_not_pass_complete")
    if not approval_ledger_refs:
        return _failed("missing_approval_ledger_reference")

    row_set = set(row_ids)
    col_set = set(column_ids)

    # Unknown keys / statuses fail closed.
    if not isinstance(evidence, dict):
        return _failed("unknown_evidence_key")
    for r, cols in evidence.items():
        if r not in row_set or not isinstance(cols, dict):
            return _failed("unknown_evidence_key")
        for c, status in cols.items():
            if c not in col_set or status not in _KNOWN_STATUS:
                return _failed("unknown_evidence_key")

    # Completeness: every of the 324 cells must be present and satisfied.
    cells = []
    complete = True
    for r in row_ids:
        for c in column_ids:
            status = evidence.get(r, {}).get(c)
            if status is None or status not in _SATISFIED:
                complete = False
            cells.append((r, c, status if status is not None else "EVIDENCE_MISSING"))

    if not complete:
        return S1EvidenceMatrix(
            state="BLOCKED_INCOMPLETE",
            reason="incomplete_matrix",
            row_ids=row_ids,
            column_ids=column_ids,
            cell_count=sum(1 for _, _, s in cells if s in _SATISFIED),
            cells=tuple(cells),
        )

    return S1EvidenceMatrix(
        state="REVIEWABLE",
        reason="",
        row_ids=row_ids,
        column_ids=column_ids,
        cell_count=len(cells),
        cells=tuple(cells),
    )
