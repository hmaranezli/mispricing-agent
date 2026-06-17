"""phase5/input_provenance_preflight.py — pure, offline preflight evaluator for the
`phase5_input_provenance_preflight` component.

This is NOT a validator. It checks only the *declared input shape and provenance fields* of a plain
dict-like record. It does not validate market truth, data quality, source truth, source reliability,
economic validity, numeric correctness, profitability, readiness, or edge. It reads no artifact,
computes no SHA256, runs no parser, calls no verifier, performs no IO/network/env/datetime/random,
and authorizes no downstream or implementation work.

`evaluate_input_provenance_preflight(record)` accepts a Mapping (plain dict-like record), never
mutates it, and returns a deterministic frozen `PreflightResult`. Missing/unknown/mismatched evidence
is reported as BLOCKED_NEEDS_EVIDENCE (canonical); structural/illegal-claim defects are reported as a
contract violation. Missing fields are never coerced to zero/false/pass/default/eligible/ready/etc.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional

from phase5.const import (
    PLANNING_GATE_OBSERVED,
    PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
    PLANNING_GATE_CONTRACT_VIOLATION,
    BLOCKED_NEEDS_EVIDENCE,
    NEXT_ACTION_NONE_WITHIN_SCOPE,
    NEXT_ACTION_OBTAIN_EVIDENCE,
    NEXT_ACTION_HALT,
    REQUIRED_TOP_LEVEL_CATEGORIES,
    REQUIRED_MAPPING_CATEGORIES,
    REQUIRED_RECORD_IDENTITY_FIELDS,
    REQUIRED_PROVENANCE_FIELDS,
    BLOCKED_REASON_BEARING_FIELDS,
    BLOCKED_REASON_PREFIX,
    ALLOWED_SOURCE_CONTRACTS,
    FORBIDDEN_CLAIM_KEYS,
    CV_NON_MAPPING_INPUT,
    CV_MALFORMED_CONTAINER,
    CV_UNSUPPORTED_SOURCE_CONTRACT,
    CV_FORBIDDEN_CLAIM,
    BLOCKED_MISSING_CATEGORY,
    BLOCKED_MISSING_FIELD,
    BLOCKED_EXPLICIT_BLOCKED_REASON,
)


@dataclass(frozen=True)
class PreflightResult:
    """Deterministic, immutable result of an input-provenance preflight evaluation."""

    status: str
    blocked_status: Optional[str]
    blocked_reason: Optional[str]
    missing_or_invalid_field: Optional[str]
    source_contract: Optional[object]
    source_artifact: Optional[object]
    source_field: Optional[object]
    deterministic_next_action: str
    human_review_required: bool
    may_retry_after_evidence: bool


def _declared(value) -> bool:
    """True only if a value is explicitly, non-emptily declared. No coercion of missing values."""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    if isinstance(value, (list, tuple, set, dict, frozenset)) and len(value) == 0:
        return False
    return True


def _is_blocked_reason(value) -> bool:
    """True if a provenance value is an explicit blocked reason rather than a resolved value."""
    return isinstance(value, str) and value.strip().upper().startswith(BLOCKED_REASON_PREFIX)


def _observed(source_contract, source_artifact, source_field) -> PreflightResult:
    return PreflightResult(
        status=PLANNING_GATE_OBSERVED,
        blocked_status=None,
        blocked_reason=None,
        missing_or_invalid_field=None,
        source_contract=source_contract,
        source_artifact=source_artifact,
        source_field=source_field,
        deterministic_next_action=NEXT_ACTION_NONE_WITHIN_SCOPE,
        human_review_required=False,
        may_retry_after_evidence=False,
    )


def _blocked(reason, field, source_contract, source_artifact, source_field) -> PreflightResult:
    return PreflightResult(
        status=PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
        blocked_status=BLOCKED_NEEDS_EVIDENCE,
        blocked_reason=reason,
        missing_or_invalid_field=field,
        source_contract=source_contract,
        source_artifact=source_artifact,
        source_field=source_field,
        deterministic_next_action=NEXT_ACTION_OBTAIN_EVIDENCE,
        human_review_required=False,
        may_retry_after_evidence=True,
    )


def _violation(reason, field, source_contract, source_artifact, source_field) -> PreflightResult:
    return PreflightResult(
        status=PLANNING_GATE_CONTRACT_VIOLATION,
        blocked_status=None,
        blocked_reason=reason,
        missing_or_invalid_field=field,
        source_contract=source_contract,
        source_artifact=source_artifact,
        source_field=source_field,
        deterministic_next_action=NEXT_ACTION_HALT,
        human_review_required=True,
        may_retry_after_evidence=False,
    )


def _forbidden_claim_in(mapping) -> Optional[str]:
    """Return the first truthy forbidden-claim key found in a mapping, else None."""
    if not isinstance(mapping, Mapping):
        return None
    for key in mapping:
        if key in FORBIDDEN_CLAIM_KEYS and bool(mapping[key]):
            return key
    return None


def evaluate_input_provenance_preflight(record) -> PreflightResult:
    """Evaluate declared input-shape + provenance fields of a record. Pure and deterministic."""
    # 1. Input must be a Mapping; never raise for the contract-covered malformed cases.
    if not isinstance(record, Mapping):
        return _violation(CV_NON_MAPPING_INPUT, None, None, None, None)

    # Best-effort echo values (only read, never coerced).
    identity = record.get("record_identity")
    provenance = record.get("provenance_fields")
    src_contract = identity.get("source_contract") if isinstance(identity, Mapping) else None
    src_artifact = provenance.get("source_artifact") if isinstance(provenance, Mapping) else None
    src_field = provenance.get("source_field") if isinstance(provenance, Mapping) else None

    # 2. Forbidden claims anywhere in the scanned scope -> contract violation.
    for scope in (record, identity, provenance):
        hit = _forbidden_claim_in(scope)
        if hit is not None:
            return _violation(CV_FORBIDDEN_CLAIM, hit, src_contract, src_artifact, src_field)

    # 3. Required mapping categories, when present, must be mapping containers.
    for cat in REQUIRED_MAPPING_CATEGORIES:
        if cat in record and not isinstance(record[cat], Mapping):
            return _violation(CV_MALFORMED_CONTAINER, cat, src_contract, src_artifact, src_field)

    # 4. All required top-level categories must be declared.
    for cat in REQUIRED_TOP_LEVEL_CATEGORIES:
        if cat not in record or not _declared(record[cat]):
            return _blocked(BLOCKED_MISSING_CATEGORY, cat, src_contract, src_artifact, src_field)

    # 5. record_identity must declare each required field; then source_contract must be allowed.
    for field in REQUIRED_RECORD_IDENTITY_FIELDS:
        if field not in identity or not _declared(identity[field]):
            return _blocked(BLOCKED_MISSING_FIELD, field, src_contract, src_artifact, src_field)
    if src_contract not in ALLOWED_SOURCE_CONTRACTS:
        return _violation(
            CV_UNSUPPORTED_SOURCE_CONTRACT, "source_contract",
            src_contract, src_artifact, src_field,
        )

    # 6. provenance_fields must declare each required field.
    for field in REQUIRED_PROVENANCE_FIELDS:
        if field not in provenance or not _declared(provenance[field]):
            return _blocked(BLOCKED_MISSING_FIELD, field, src_contract, src_artifact, src_field)

    # 7. An explicit blocked reason is blocked evidence, never observed.
    for field in BLOCKED_REASON_BEARING_FIELDS:
        if _is_blocked_reason(provenance[field]):
            return _blocked(
                BLOCKED_EXPLICIT_BLOCKED_REASON, field,
                src_contract, src_artifact, src_field,
            )
    if _is_blocked_reason(provenance.get("provenance_status")):
        return _blocked(
            BLOCKED_EXPLICIT_BLOCKED_REASON, "provenance_status",
            src_contract, src_artifact, src_field,
        )

    # 8. All declarations present, allowed, non-empty, no blocked reason, no forbidden claim.
    return _observed(src_contract, src_artifact, src_field)
