"""phase5/const.py — centralized status / field constants for Phase 5 components.

Status and field-name constants live here so they are not scattered as raw string literals across
modules. These are vocabulary constants only; they encode no economic, profitability, readiness, or
net-edge meaning.
"""

# --- Planning-gate status vocabulary (exactly one is reported per evaluation) ---
PLANNING_GATE_OBSERVED = "PLANNING_GATE_OBSERVED"
PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE = "PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE"
PLANNING_GATE_CONTRACT_VIOLATION = "PLANNING_GATE_CONTRACT_VIOLATION"

# Canonical blocked vocabulary for missing/unknown/mismatched evidence.
BLOCKED_NEEDS_EVIDENCE = "BLOCKED_NEEDS_EVIDENCE"

# --- Deterministic next-action vocabulary (neutral; authorizes no downstream work) ---
NEXT_ACTION_NONE_WITHIN_SCOPE = "NONE_REQUIRED_WITHIN_CHECKED_SCOPE"
NEXT_ACTION_OBTAIN_EVIDENCE = "OBTAIN_REQUIRED_EVIDENCE_THEN_REEVALUATE"
NEXT_ACTION_HALT = "HALT_FAIL_CLOSED"

# --- Required top-level input-schema categories (declaration / shape only) ---
REQUIRED_TOP_LEVEL_CATEGORIES = (
    "record_identity",
    "gross_edge_fields",
    "eligibility_state",
    "no_eligible_state",
    "friction_component_placeholders",
    "mechanical_metadata",
    "provenance_fields",
    "reporting_boundary_fields",
    "blocked_state_fields",
)

# Categories that must themselves be mapping containers when present.
REQUIRED_MAPPING_CATEGORIES = ("record_identity", "provenance_fields")

REQUIRED_RECORD_IDENTITY_FIELDS = (
    "input_schema_version",
    "input_record_type",
    "batch_id",
    "run_id",
    "observation_id",
    "source_contract",
)

REQUIRED_PROVENANCE_FIELDS = (
    "source_artifact",
    "source_field",
    "artifact_type_or_blocked_reason",
    "artifact_phase_or_blocked_reason",
    "provenance_status",
    "source_sha256_or_blocked_reason",
    "parser_version_or_blocked_reason",
    "verifier_result_or_blocked_reason",
)

# The three provenance fields that may legitimately carry an explicit blocked reason instead of a
# resolved value; an explicit blocked reason is blocked evidence, never observed.
BLOCKED_REASON_BEARING_FIELDS = (
    "source_sha256_or_blocked_reason",
    "parser_version_or_blocked_reason",
    "verifier_result_or_blocked_reason",
)

# A provenance value is treated as an explicit blocked reason if it begins with this prefix.
BLOCKED_REASON_PREFIX = "BLOCKED"

# Known/allowed Phase 5 source contracts for this component (the planning artifact's source set).
ALLOWED_SOURCE_CONTRACTS = frozenset({
    "phase5_implementation_planning_gate_entrance_criteria.md",
    "phase5_input_schema_refinement_contract.md",
    "phase5_artifact_provenance_contract.md",
    "phase5_fail_closed_blocked_state_contract.md",
    "phase5_no_claims_reporting_schema_contract.md",
    "phase5_offline_fixture_contract.md",
    "phase5_interface_contract.md",
})

# Forbidden claim keys: presence with a truthy value is a contract violation. These would assert
# source truth, data validity, source reliability, a data-quality/data-integrity guarantee, or that
# this component authorizes downstream/implementation work — none of which this component may claim.
FORBIDDEN_CLAIM_KEYS = frozenset({
    "source_truth",
    "source_truth_guaranteed",
    "source_is_trusted",
    "data_is_valid",
    "data_quality_guaranteed",
    "data_integrity_guaranteed",
    "source_reliability_guaranteed",
    "authorizes_downstream",
    "authorizes_implementation",
    "readiness_confirmed",
    "profitability_claimed",
})

# Deterministic maximum container depth for the structural forbidden-claim scan. Legitimate records
# are shallow (category -> field -> scalar); anything deeper fails closed rather than recursing
# unboundedly. This is a fixed structural guard, not an economic or readiness threshold.
MAX_SCAN_DEPTH = 64

# --- Contract-violation / blocked reason codes ---
CV_NON_MAPPING_INPUT = "CONTRACT_VIOLATION_NON_MAPPING_INPUT"
CV_MALFORMED_CONTAINER = "CONTRACT_VIOLATION_MALFORMED_REQUIRED_CONTAINER"
CV_UNSUPPORTED_SOURCE_CONTRACT = "CONTRACT_VIOLATION_UNSUPPORTED_SOURCE_CONTRACT"
CV_FORBIDDEN_CLAIM = "CONTRACT_VIOLATION_FORBIDDEN_CLAIM"
CV_CYCLIC_STRUCTURE = "CONTRACT_VIOLATION_CYCLIC_STRUCTURE"
CV_MAX_DEPTH_EXCEEDED = "CONTRACT_VIOLATION_MAX_DEPTH_EXCEEDED"

BLOCKED_MISSING_CATEGORY = "BLOCKED_MISSING_TOP_LEVEL_CATEGORY"
BLOCKED_MISSING_FIELD = "BLOCKED_MISSING_REQUIRED_FIELD"
BLOCKED_EXPLICIT_BLOCKED_REASON = "BLOCKED_EXPLICIT_BLOCKED_REASON_PRESENT"
