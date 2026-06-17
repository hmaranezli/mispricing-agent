"""tests/test_phase5_input_provenance_preflight.py — pins the offline/TDD implementation of the
`phase5_input_provenance_preflight` component (pure in-memory preflight evaluator, offline).

This is NOT a validator and asserts no market truth, data quality, source truth, source reliability,
economic validity, numeric correctness, profitability, readiness, or edge. It exercises a pure
function `evaluate_input_provenance_preflight(record)` that takes a plain dict-like Mapping input,
performs no IO/network/env/datetime/random, never mutates the input, and returns a deterministic
frozen dataclass result whose `status` is exactly one of PLANNING_GATE_OBSERVED /
PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE / PLANNING_GATE_CONTRACT_VIOLATION.

Static hardcoded record constants only; no conftest fixture, no fixture generator/factory/loader/
parser, no artifact read, no SHA256, no verifier call.
"""
import copy
import dataclasses

from phase5.input_provenance_preflight import (
    evaluate_input_provenance_preflight,
    PreflightResult,
    PLANNING_GATE_OBSERVED,
    PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
    PLANNING_GATE_CONTRACT_VIOLATION,
    BLOCKED_NEEDS_EVIDENCE,
)


def _valid_record():
    """A minimal, fully-declared static record (fresh dict per call)."""
    return {
        "record_identity": {
            "input_schema_version": "phase5.input.v0",
            "input_record_type": "phase5_input_provenance_preflight_record",
            "batch_id": "phase4c_batch_1781637248",
            "run_id": "run-static-0001",
            "observation_id": "obs-static-0003",
            "source_contract": "phase5_input_schema_refinement_contract.md",
        },
        "gross_edge_fields": {"declared": "shape-only"},
        "eligibility_state": {"declared": "shape-only"},
        "no_eligible_state": {"declared": "shape-only"},
        "friction_component_placeholders": {"declared": "shape-only"},
        "mechanical_metadata": {"declared": "shape-only"},
        "provenance_fields": {
            "source_artifact": "phase4c_batch_1781637248 (read-only provenance reference)",
            "source_field": "summary.eligible_pairs",
            "artifact_type_or_blocked_reason": "batch_summary_record",
            "artifact_phase_or_blocked_reason": "phase4c",
            "provenance_status": "observed",
            "source_sha256_or_blocked_reason": "a3f1c9d2e4b6a8c0f1234567890abcdef1234567890abcdef1234567890abcde",
            "parser_version_or_blocked_reason": "parser.v0",
            "verifier_result_or_blocked_reason": "PASS",
        },
        "reporting_boundary_fields": {"declared": "shape-only"},
        "blocked_state_fields": {"declared": "shape-only"},
    }


# 1. observed minimal valid Mapping input -> OBSERVED
def test_observed_minimal_valid_input():
    result = evaluate_input_provenance_preflight(_valid_record())
    assert result.status == PLANNING_GATE_OBSERVED
    assert result.blocked_status is None
    assert result.blocked_reason is None
    assert result.human_review_required is False
    assert result.may_retry_after_evidence is False


# 2. missing top-level category -> BLOCKED
def test_missing_top_level_category_blocked():
    rec = _valid_record()
    del rec["mechanical_metadata"]
    result = evaluate_input_provenance_preflight(rec)
    assert result.status == PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE
    assert result.blocked_status == BLOCKED_NEEDS_EVIDENCE
    assert result.missing_or_invalid_field == "mechanical_metadata"
    assert result.may_retry_after_evidence is True


# 3. missing source_artifact -> BLOCKED
def test_missing_source_artifact_blocked():
    rec = _valid_record()
    del rec["provenance_fields"]["source_artifact"]
    result = evaluate_input_provenance_preflight(rec)
    assert result.status == PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE
    assert result.blocked_status == BLOCKED_NEEDS_EVIDENCE
    assert result.missing_or_invalid_field == "source_artifact"


# 4. missing source_field -> BLOCKED
def test_missing_source_field_blocked():
    rec = _valid_record()
    del rec["provenance_fields"]["source_field"]
    result = evaluate_input_provenance_preflight(rec)
    assert result.status == PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE
    assert result.missing_or_invalid_field == "source_field"


# 5. missing source_contract -> BLOCKED
def test_missing_source_contract_blocked():
    rec = _valid_record()
    del rec["record_identity"]["source_contract"]
    result = evaluate_input_provenance_preflight(rec)
    assert result.status == PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE
    assert result.missing_or_invalid_field == "source_contract"


# 6. unsupported source_contract -> CONTRACT_VIOLATION
def test_unsupported_source_contract_violation():
    rec = _valid_record()
    rec["record_identity"]["source_contract"] = "not_a_phase5_contract.md"
    result = evaluate_input_provenance_preflight(rec)
    assert result.status == PLANNING_GATE_CONTRACT_VIOLATION
    assert result.blocked_status is None
    assert result.human_review_required is True
    assert result.may_retry_after_evidence is False


# 7. missing source_sha256_or_blocked_reason -> BLOCKED
def test_missing_sha256_blocked_reason_field_blocked():
    rec = _valid_record()
    del rec["provenance_fields"]["source_sha256_or_blocked_reason"]
    result = evaluate_input_provenance_preflight(rec)
    assert result.status == PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE
    assert result.missing_or_invalid_field == "source_sha256_or_blocked_reason"


# 8. explicit source_sha256 blocked reason -> BLOCKED, not OBSERVED
def test_explicit_blocked_reason_is_blocked_not_observed():
    rec = _valid_record()
    rec["provenance_fields"]["source_sha256_or_blocked_reason"] = BLOCKED_NEEDS_EVIDENCE
    result = evaluate_input_provenance_preflight(rec)
    assert result.status == PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE
    assert result.status != PLANNING_GATE_OBSERVED
    assert result.missing_or_invalid_field == "source_sha256_or_blocked_reason"
    assert result.may_retry_after_evidence is True


# 9. forbidden source-truth/data-quality/reliability claim -> CONTRACT_VIOLATION
def test_forbidden_source_truth_claim_violation():
    rec = _valid_record()
    rec["source_truth_guaranteed"] = True
    result = evaluate_input_provenance_preflight(rec)
    assert result.status == PLANNING_GATE_CONTRACT_VIOLATION
    assert result.human_review_required is True


def test_forbidden_data_quality_claim_in_provenance_violation():
    rec = _valid_record()
    rec["provenance_fields"]["data_quality_guaranteed"] = True
    result = evaluate_input_provenance_preflight(rec)
    assert result.status == PLANNING_GATE_CONTRACT_VIOLATION


# 10. malformed non-Mapping input -> CONTRACT_VIOLATION, no exception
def test_non_mapping_input_violation_no_exception():
    for bad in [None, 42, "a string", ["not", "a", "mapping"], 3.14, object()]:
        result = evaluate_input_provenance_preflight(bad)
        assert result.status == PLANNING_GATE_CONTRACT_VIOLATION
        assert result.blocked_status is None


def test_malformed_required_container_violation():
    rec = _valid_record()
    rec["provenance_fields"] = "not-a-mapping"
    result = evaluate_input_provenance_preflight(rec)
    assert result.status == PLANNING_GATE_CONTRACT_VIOLATION


# 11. function does not mutate input
def test_does_not_mutate_input():
    rec = _valid_record()
    before = copy.deepcopy(rec)
    evaluate_input_provenance_preflight(rec)
    assert rec == before


# 12. result is immutable / frozen
def test_result_is_frozen():
    result = evaluate_input_provenance_preflight(_valid_record())
    assert isinstance(result, PreflightResult)
    assert dataclasses.is_dataclass(result)
    fields = dataclasses.fields(result)
    assert fields  # has declared fields
    params = result.__dataclass_params__
    assert params.frozen is True
    try:
        result.status = "MUTATED"
        raised = False
    except dataclasses.FrozenInstanceError:
        raised = True
    assert raised, "result must be frozen/immutable"


def test_result_exposes_all_required_fields():
    result = evaluate_input_provenance_preflight(_valid_record())
    for name in [
        "status",
        "blocked_status",
        "blocked_reason",
        "missing_or_invalid_field",
        "source_contract",
        "source_artifact",
        "source_field",
        "deterministic_next_action",
        "human_review_required",
        "may_retry_after_evidence",
    ]:
        assert hasattr(result, name), f"missing result field: {name}"


# 13. no IO/network/env/datetime/random dependency is required
def test_pure_function_no_external_dependency():
    """The module source must not import IO/network/env/time/random machinery, and a call must
    succeed under a stripped environment with no filesystem cwd dependence."""
    import phase5.input_provenance_preflight as mod
    import inspect

    src = inspect.getsource(mod)
    for banned in [
        "import os", "import sys", "import socket", "import requests",
        "import urllib", "import subprocess", "import random", "import time",
        "import datetime", "open(", "Path(", "getenv", "environ",
        "datetime.now", "time.time", "random.",
    ]:
        assert banned not in src, f"banned external dependency in module source: {banned}"

    # deterministic: same input -> identical result twice
    r1 = evaluate_input_provenance_preflight(_valid_record())
    r2 = evaluate_input_provenance_preflight(_valid_record())
    assert r1 == r2
