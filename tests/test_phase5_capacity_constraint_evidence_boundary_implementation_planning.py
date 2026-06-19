"""tests/test_phase5_capacity_constraint_evidence_boundary_implementation_planning.py — pins the
implementation-planning artifact for the future `phase5_capacity_constraint_evidence_boundary`
component (docs-only planning, offline, read-only).

This boundary, if ever authorized, is framed as a passive **constitutional safety barrier / airgap**,
NOT a downstream Phase 6 component and NOT an actionable decision engine. Slice 0 is a structural
multi-source join auditor over exactly four already-implemented Phase 5 carriers; it computes no
min(), no final capacity, no order size, no allocation, and no exposure. Runs no batch, fetches no
endpoint, builds no engine, edits no runtime code, and asserts the planning artifact itself contains
no runtime implementation code. (Whether the separately authorized runtime module exists is governed
by the implementation test suite, not this planning artifact.)
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_capacity_constraint_evidence_boundary_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"
CARRIER_CONTRACT_START = "<!-- CARRIER-CONTRACT-START -->"
CARRIER_CONTRACT_END = "<!-- CARRIER-CONTRACT-END -->"

EXPECTED_COMPONENT = "phase5_capacity_constraint_evidence_boundary"

# The exact pinned factory name for the future carrier-only slice.
FACTORY_NAME = "make_capacity_constraint_evidence_context"

# The exact closed field set for CapacityConstraintEvidenceContext (exactly these, no others).
CARRIER_FIELD_SET = [
    "component_name",
    "boundary_version",
    "post_profitability_source_contract",
    "post_profitability_source_artifact",
    "post_profitability_source_field",
    "venue_readiness_source_contract",
    "venue_readiness_source_artifact",
    "venue_readiness_source_field",
    "liquidity_capacity_source_contract",
    "liquidity_capacity_source_artifact",
    "liquidity_capacity_source_field",
    "capital_margin_source_contract",
    "capital_margin_source_artifact",
    "capital_margin_source_field",
]

# Fields/tokens the carrier must explicitly NOT store (computed / status / runtime tokens).
CARRIER_EXCLUDED_FIELDS = [
    "join_status", "binding_status", "identity_status", "freshness_status", "unit_status",
    "audited_evidence_count", "observed_size", "available_capacity", "required_capital",
    "final_capacity", "computed_min", "order_size", "allocation", "exposure", "balance",
    "route", "reservation", "wallet",
]

# The exactly-twelve caller-supplied keyword-only factory parameters (the four provenance triplets;
# component_name and boundary_version are NOT parameters — they are set internally from constants).
FACTORY_PARAMS = [
    "post_profitability_source_contract",
    "post_profitability_source_artifact",
    "post_profitability_source_field",
    "venue_readiness_source_contract",
    "venue_readiness_source_artifact",
    "venue_readiness_source_field",
    "liquidity_capacity_source_contract",
    "liquidity_capacity_source_artifact",
    "liquidity_capacity_source_field",
    "capital_margin_source_contract",
    "capital_margin_source_artifact",
    "capital_margin_source_field",
]
# These two stored fields must NOT be factory parameters (set internally from constants).
FACTORY_FORBIDDEN_PARAMS = ["component_name", "boundary_version"]

# Exact pinned internal module constants (verbatim single-line forms).
COMPONENT_NAME_CONST_LINE = (
    'CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME = '
    '"phase5_capacity_constraint_evidence_boundary"'
)
BOUNDARY_VERSION_CONST_LINE = (
    'BOUNDARY_VERSION = "phase5.capacity_constraint_evidence_boundary.v0"'
)

# The exactly-four source carriers Slice 0 consumes (already implemented Phase 5 carriers).
SOURCE_CARRIERS = [
    "PostProfitabilityEvidenceEnvelope",
    "VenueInstrumentReadinessStateContext",
    "LiquidityCapacityEvidenceContext",
    "CapitalMarginEvidenceContext",
]

# Other Phase 5 carriers that must NOT be named as sources (enforces "exactly four").
NON_SOURCE_CARRIERS = [
    "GrossEdgeObservation",
    "GrossEdgeSourceResult",
    "ObservableCostObservation",
    "ObservableCostSourceResult",
    "ObservableCostValidityContext",
    "NetEdgeCalculationResult",
    "ProfitabilityThresholdPolicyContext",
    "PreNetEdgeCalculationInput",
]

# External input-schema record-identity / provenance tokens that MUST NOT be declared as carrier
# source fields (they live only in phase5/const.py for the input-provenance preflight).
FORBIDDEN_CARRIER_FIELDS = ["batch_id", "run_id", "observation_id", "provenance_status"]

PINNED_PHRASES = [
    "NO ORDER EXISTS",
    "no order size, no allocation, no routing, no execution preparation",
    "no Phase 6 bridge",
    "not an actionable decision engine",
    "no sizing",
    "no exposure runtime",
    "no balance runtime",
    "no wallet reservation",
    "no paper/live readiness",
    "no min()",
    "no final capacity",
]

CAPACITY_REASON_TOKENS = [
    "CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE",
    "CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE",
    "CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE",
    "CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH",
    "CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH",
    "CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE",
]

FORBIDDEN_CLAIM_PHRASES = [
    "ready-to-fly", "ready to fly", "system-ready", "system ready",
    "is ready", "are ready", "production ready", "paper ready",
    "execution ready", "live ready", "economics ready", "ready for live",
    "is profitable", "profit confirmed", "profitable strategy",
    "edge confirmed", "positive edge", "tradeable edge", "alpha confirmed",
]

FORBIDDEN_WORDING = [
    "eliminates all risk", "eliminates risk", "zero risk", "tamper-proof",
    "verified truth", "clean data", "trusted data", "is immutable",
    "guarantees correctness", "is impossible", "cannot happen",
    "is complete", "is perfect", "is now safe", "fully complete", "the last piece",
]

# ---- Slice 0 structural-auditor hardening (charter amendment) ----

GATE_CONTRACT_START = "<!-- GATE-CONTRACT-START -->"
GATE_CONTRACT_END = "<!-- GATE-CONTRACT-END -->"

SLICE0_RUNTIME_NAMES = [
    "CapacityConstraintGate",
    "capacity_constraint_preflight",
    "CapacityConstraintGateTypeError",
    "CapacityConstraintMisroutedHaltCarrierError",
]

GATE_PREFLIGHT_PARAMS = [
    "evidence_envelope",
    "venue_readiness",
    "liquidity_evidence",
    "capital_evidence",
]

PREFLIGHT_INPUT_TYPE_LINES = [
    "type(evidence_envelope) is PostProfitabilityEvidenceEnvelope",
    "type(venue_readiness) is VenueInstrumentReadinessStateContext",
    "type(liquidity_evidence) is LiquidityCapacityEvidenceContext",
    "type(capital_evidence) is CapitalMarginEvidenceContext",
]

PASS_SOURCE_MAPPING_LINES = [
    "post_profitability_source_contract = evidence_envelope.source_contract",
    "post_profitability_source_artifact = evidence_envelope.source_artifact",
    "post_profitability_source_field = evidence_envelope.source_field",
    "venue_readiness_source_contract = venue_readiness.source_contract",
    "venue_readiness_source_artifact = venue_readiness.source_artifact",
    "venue_readiness_source_field = venue_readiness.source_field",
    "liquidity_capacity_source_contract = liquidity_evidence.source_contract",
    "liquidity_capacity_source_artifact = liquidity_evidence.source_artifact",
    "liquidity_capacity_source_field = liquidity_evidence.source_field",
    "capital_margin_source_contract = capital_evidence.source_contract",
    "capital_margin_source_artifact = capital_evidence.source_artifact",
    "capital_margin_source_field = capital_evidence.source_field",
]

BLOCKED_PACKET_FIELD_LINES = [
    "component_name = CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME",
    "origin_component = CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME",
    "origin_result_status = PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
    "status = PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
    "blocked_status = BLOCKED_NEEDS_EVIDENCE",
    "source_contract = evidence_envelope.source_contract",
    "source_artifact = evidence_envelope.source_artifact",
    "source_field = evidence_envelope.source_field",
    "deterministic_next_action = NEXT_ACTION_OBTAIN_EVIDENCE",
    "human_review_required = True",
    "may_retry_after_evidence = True",
    "created_from_contract = GATE_SOURCE_CONTRACT",
    "boundary_version = BOUNDARY_VERSION",
]

SLICE0_BLOCKED_CONSTANT_LINES = [
    'CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE"',
    'CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE"',
    'CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE"',
    'CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH = "CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH"',
    'CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH = "CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH"',
    'CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE"',
]

SLICE0_FORBIDDEN_LOGIC = [
    "no min()", "no max()", "no final capacity", "no computed capacity value",
    "no tradable size", "no order size", "no allocation", "no exposure value",
    "no exposure runtime", "no balance runtime", "no wallet reservation", "no routing",
    "no execution preparation", "no paper/live readiness", "no PnL", "no net edge",
    "no alpha/edge claim", "no economic actionability", "NO ORDER EXISTS",
]


def _read():
    assert os.path.isfile(DOC), f"capacity-constraint planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


# ---- existence / framing ----

def test_doc_exists():
    assert _read().strip(), "planning doc is empty"


def test_read_only_planning_framing():
    low = _read().lower()
    assert "implementation-planning only, not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_constitutional_safety_barrier_airgap_framing():
    low = _read().lower()
    assert "constitutional safety barrier" in low
    assert "airgap" in low


def test_flat_phase5_naming_no_phase_5_5():
    text = _read()
    assert EXPECTED_COMPONENT in text
    assert "phase5.5" not in text.lower()
    assert "phase 5.5" not in text.lower()
    assert "phase6" not in text.lower().replace("phase 6 bridge", "")  # "no Phase 6 bridge" is allowed


def test_component_and_context_names_present():
    text = _read()
    assert "CapacityConstraintEvidenceBoundary" in text
    assert "CapacityConstraintEvidenceContext" in text


# ---- source carriers (exactly four) ----

def test_exactly_four_source_carriers_named():
    text = _read()
    for c in SOURCE_CARRIERS:
        assert c in text, f"source carrier missing: {c}"
    for c in NON_SOURCE_CARRIERS:
        assert c not in text, f"non-source carrier must not be named as a source: {c}"


def test_forbidden_invented_carrier_fields_absent():
    # The four external record-identity / provenance tokens must never be DECLARED as carrier
    # fields. They may appear only inside the explicit carrier-contract exclusions block, which
    # pins them as never-stored. Anywhere outside that block they remain forbidden.
    text = _read()
    body = _strip_block(text, CARRIER_CONTRACT_START, CARRIER_CONTRACT_END)
    for f in FORBIDDEN_CARRIER_FIELDS:
        assert f not in body, f"forbidden invented carrier field declared outside exclusions: {f}"


# ---- slice 0 structural-join scope ----

def test_slice0_structural_multi_source_join_only():
    low = _read().lower()
    assert "slice 0" in low
    assert "structural multi-source join" in low
    assert "auditor" in low


def test_passive_context_has_no_computed_capacity():
    low = _read().lower()
    assert "no computed capacity value" in low


# ---- binding rules over proven-present fields ----

def test_binding_rules_documented():
    text = _read()
    low = text.lower()
    # 4-way identity convergence
    assert "venue" in low and "instrument_id" in low and "base_asset" in low and "quote_asset" in low
    assert "identity convergence" in low
    # side binding only PostProfitability <-> CapitalMargin
    assert "side binding" in low
    # size binding across the three size-bearing carriers
    assert "size binding" in low
    # unit binding
    assert "unit binding" in low
    # time/freshness binding only for liquidity/capital epoch+tolerance fields
    assert "time" in low and ("freshness" in low or "staleness" in low)
    assert "liquidity_snapshot_epoch_ms" in text
    assert "evidence_epoch_tolerance_ms" in text
    assert "required_capital_epoch_ms" in text
    assert "available_free_capital_snapshot_epoch_ms" in text
    assert "observed_at_epoch_ms" in text


# ---- fail-closed taxonomy + reason vocabulary ----

def test_fail_closed_branch_priority_and_taxonomy():
    low = _read().lower()
    assert "fail closed" in low or "fail-closed" in low
    assert "branch priority" in low
    for term in ["missing", "malformed", "stale", "identity-mismatch", "unit-mismatch", "undefined"]:
        assert term in low, f"blocked taxonomy term missing: {term}"


def test_reason_tokens_pinned_doc_only():
    text = _read()
    for token in CAPACITY_REASON_TOKENS:
        assert token in text, f"capacity reason token missing: {token}"
        assert token.startswith("CAPACITY_CONSTRAINT_"), token


def test_blocked_reuses_existing_packet_semantics_no_new_schema():
    text = _read()
    low = text.lower()
    assert "BlockedPacket" in text
    assert "BLOCKED_NEEDS_EVIDENCE" in text
    assert "no new packet" in low


# ---- pinned no-go phrases ----

def test_pinned_no_go_phrases_present():
    text = _read()
    for phrase in PINNED_PHRASES:
        assert phrase in text, f"pinned no-go phrase missing: {phrase!r}"


def test_distinguishes_passive_constraint_from_exposure_and_balance_runtime():
    low = _read().lower()
    assert "passive" in low
    assert "exposure runtime" in low
    assert "balance runtime" in low


# ---- marker blocks ----

def test_no_claims_block_present():
    text = _read()
    assert NO_CLAIMS_START in text and NO_CLAIMS_END in text


def test_prohibited_outputs_block_present():
    text = _read()
    assert PROHIBITED_OUT_START in text and PROHIBITED_OUT_END in text


def test_marker_pairs_balanced():
    text = _read()
    assert text.count(NO_CLAIMS_START) == text.count(NO_CLAIMS_END) == 1
    assert text.count(PROHIBITED_OUT_START) == text.count(PROHIBITED_OUT_END) == 1
    assert text.count(FRAMING_START) == text.count(FRAMING_END) == 1


def test_no_forbidden_overclaim_wording_anywhere():
    low = _read().lower()
    hits = [w for w in FORBIDDEN_WORDING if w in low]
    assert not hits, f"forbidden over-claim wording present: {hits}"


def test_forbidden_claims_only_in_framing_no_claims_or_prohibited_outputs():
    text = _read()
    body = _strip_block(text, FRAMING_START, FRAMING_END)
    body = _strip_block(body, NO_CLAIMS_START, NO_CLAIMS_END)
    body = _strip_block(body, PROHIBITED_OUT_START, PROHIBITED_OUT_END).lower()
    hits = [p for p in FORBIDDEN_CLAIM_PHRASES if p in body]
    assert not hits, f"forbidden positive claim(s) outside allowed sections: {hits}"


# ---- charter amendment: carrier-only slice, factory, closed field set ----

def test_carrier_contract_block_present_and_balanced():
    text = _read()
    assert text.count(CARRIER_CONTRACT_START) == text.count(CARRIER_CONTRACT_END) == 1


def test_carrier_only_implementation_slice_pinned():
    low = _read().lower()
    assert "carrier-only implementation slice" in low
    assert "tdd sequencing unit" in low
    # the carrier-only slice does not authorize the Slice 0 join auditor / gate / preflight
    assert "not authorization for the slice 0" in low
    assert "gate" in low and "preflight" in low
    # not a bridge, not a downstream component
    assert "no phase 6 bridge" in low
    assert "not a downstream component" in low


def test_factory_name_and_signature_pinned():
    text = _read()
    low = text.lower()
    assert FACTORY_NAME in text, f"factory name not pinned: {FACTORY_NAME}"
    assert "keyword-only" in low
    assert "direct construction" in low and "blocked" in low
    assert "verbatim" in low
    assert "non-empty" in low and "non-whitespace" in low
    assert "exact str" in low or "exactly str" in low
    assert "no implicit coercion" in low or "no coercion" in low


def test_carrier_closed_field_set_pinned_exactly():
    text = _read()
    for f in CARRIER_FIELD_SET:
        assert f in text, f"closed carrier field missing: {f}"
    low = text.lower()
    assert "exactly" in low
    assert "fourteen" in low or "14" in text
    assert "and no others" in low
    # audited_evidence_count must NOT be a stored carrier field (allowed only in exclusions block)
    body = _strip_block(text, CARRIER_CONTRACT_START, CARRIER_CONTRACT_END)
    assert "audited_evidence_count" not in body


def test_exactly_four_rule_is_invariant_not_stored_data():
    low = _read().lower()
    assert "doc/test invariant" in low
    assert "not stored data" in low


def test_carrier_excludes_status_and_computed_fields():
    text = _read()
    for f in CARRIER_EXCLUDED_FIELDS:
        assert f in text, f"carrier exclusion not documented: {f}"
    assert "*_status" in text


def test_repr_exposure_pinned_to_two_fields_only():
    text = _read()
    low = text.lower()
    assert "component_name" in text and "boundary_version" in text
    assert "repr" in low
    assert "only" in low


def test_carrier_safety_properties_pinned():
    low = _read().lower()
    for prop in ["frozen", "repr-safe", "anti-truthiness", "anti-coercion", "factory-only"]:
        assert prop in low, f"carrier safety property missing: {prop}"
    assert "no env" in low
    for src in ["config", "files", "db", "network", "time"]:
        assert src in low, f"missing no-IO source: {src}"
    for verb in ["derives", "computes", "compares", "audits", "validates", "infers", "decides"]:
        assert verb in low, f"missing nothing-verb: {verb}"


# ---- charter amendment 2: 12-param factory, internal constants, slotted hardening ----

def test_factory_accepts_exactly_twelve_caller_params():
    text = _read()
    low = text.lower()
    assert "twelve" in low, "factory caller-param count not pinned as twelve"
    for p in FACTORY_PARAMS:
        assert p in text, f"factory caller param missing: {p}"


def test_factory_rejects_component_name_and_boundary_version_as_params():
    text = _read()
    low = text.lower()
    assert "must not accept" in low
    assert "typeerror" in low
    for p in FACTORY_FORBIDDEN_PARAMS:
        assert p in text, f"forbidden factory param not named: {p}"


def test_internal_constants_pinned_exactly():
    text = _read()
    assert COMPONENT_NAME_CONST_LINE in text, "component-name constant line not pinned verbatim"
    assert BOUNDARY_VERSION_CONST_LINE in text, "boundary-version constant line not pinned verbatim"


def test_factory_sets_identity_fields_internally_from_constants():
    low = _read().lower()
    assert "component_name internally" in low
    assert "boundary_version internally" in low
    assert "capacity_constraint_evidence_boundary_component_name" in low


def test_slotted_no_instance_dict_and_no_dynamic_attribute():
    text = _read()
    low = text.lower()
    assert "slotted" in low
    assert "__dict__" in text
    assert "no-instance-dict" in low or "no instance dict" in low or "no `__dict__`" in text
    assert "dynamic attribute injection" in low
    assert "physically blocked" in low


# ---- docs-only guard: the planning artifact carries no runtime implementation code ----

def test_planning_doc_contains_no_runtime_implementation():
    # Durable docs-only guard: the planning artifact pins names in prose but must never carry a
    # runtime class/function definition. (Whether the separately authorized runtime module exists is
    # governed by the implementation test suite, not this planning artifact.)
    src = _read()
    assert "class CapacityConstraintEvidenceContext" not in src
    assert "class CapacityConstraintEvidenceBoundary" not in src
    assert "class CapacityConstraintGate" not in src
    assert "def make_capacity_constraint_evidence_context" not in src
    assert "def capacity_constraint_preflight" not in src


# ---- Slice 0 structural-auditor hardening (charter amendment) ----

def test_gate_contract_block_present_and_balanced():
    text = _read()
    assert text.count(GATE_CONTRACT_START) == text.count(GATE_CONTRACT_END) == 1


def test_slice0_runtime_names_pinned():
    text = _read()
    for n in SLICE0_RUNTIME_NAMES:
        assert n in text, f"Slice 0 runtime name not pinned: {n}"


def test_gate_is_stateless_namespace():
    text = _read()
    low = text.lower()
    assert "stateless" in low
    assert "__slots__ = ()" in text
    assert "preflight = staticmethod(capacity_constraint_preflight)" in text


def test_preflight_signature_pinned_keyword_only():
    text = _read()
    low = text.lower()
    assert "capacity_constraint_preflight(" in text
    for p in GATE_PREFLIGHT_PARAMS:
        assert p in text, f"preflight param missing: {p}"
    assert "keyword-only" in low
    assert "no positional parameters" in low
    assert "no defaults" in low
    assert "no extra keyword parameters" in low
    assert "CapacityConstraintEvidenceContext is NOT an input" in text


def test_preflight_required_input_types_pinned():
    text = _read()
    for line in PREFLIGHT_INPUT_TYPE_LINES:
        assert line in text, f"preflight input-type line missing: {line}"


def test_misroute_and_typeerror_pinned():
    text = _read()
    low = text.lower()
    assert "CapacityConstraintMisroutedHaltCarrierError" in text
    assert "CapacityConstraintGateTypeError" in text
    assert "BlockedPacket" in text and "NoEligibleHaltPacket" in text
    assert "never produce a packet" in low


def test_pass_return_contract_pinned():
    text = _read()
    low = text.lower()
    assert "pass returns" in low and "CapacityConstraintEvidenceContext" in text
    assert "make_capacity_constraint_evidence_context" in text
    assert "output certificate" in low
    assert "never an input carrier" in low
    assert "12 caller-supplied provenance parameters" in text or \
        "twelve caller-supplied provenance parameters" in low


def test_pass_source_mapping_pinned():
    text = _read()
    for line in PASS_SOURCE_MAPPING_LINES:
        assert line in text, f"pass source mapping line missing: {line}"


def test_canonical_identity_is_post_profitability():
    text = _read()
    low = text.lower()
    assert "canonical" in low
    assert "PostProfitabilityEvidenceEnvelope" in text
    assert "evidence_envelope.source_contract" in text
    assert "evidence_envelope.source_artifact" in text
    assert "evidence_envelope.source_field" in text
    assert "no blocked packet may use" in low


def test_blocked_packet_contract_pinned():
    text = _read()
    assert "make_blocked_packet" in text
    for line in BLOCKED_PACKET_FIELD_LINES:
        assert line in text, f"blocked packet field mapping missing: {line}"
    assert "reason_code" in text
    assert "missing_or_invalid_field" in text
    assert 'GATE_SOURCE_CONTRACT = "phase5_capacity_constraint_evidence_boundary_implementation_planning.md"' \
        in text


def test_slice0_blocked_constant_values_pinned():
    text = _read()
    for line in SLICE0_BLOCKED_CONSTANT_LINES:
        assert line in text, f"blocked constant value line missing: {line}"


def test_branch_to_token_mapping_pinned():
    low = _read().lower()
    assert "missing carrier or missing required field" in low
    assert "malformed scalar grammar" in low
    assert "identity mismatch" in low
    assert "unit mismatch" in low
    assert "stale epoch comparison" in low
    assert "not resolvable within the checked scope" in low


def test_missing_malformed_undefined_classification_pinned():
    low = _read().lower()
    assert "not exact str" in low
    assert "nan or infinity" in low
    assert "base-10 integer string" in low
    assert "do not use undefined for missing fields" in low


def test_decimal_size_rules_pinned():
    text = _read()
    low = text.lower()
    assert "Decimal" in text
    assert "no float coercion" in low
    assert "reject nan and infinity" in low
    assert "reject scientific notation" in low
    assert '"1E+3"' in text
    assert 'Decimal(size_a).compare(Decimal(size_b)) == Decimal("0")' in text


def test_epoch_tolerance_rules_and_formula_pinned():
    text = _read()
    low = text.lower()
    assert "abs(int(epoch_a) - int(epoch_b)) <= int(tolerance)" in text
    assert "missing tolerance is missing evidence" in low
    assert "malformed tolerance is malformed evidence" in low
    assert "no default tolerance" in low
    assert "no clock reads" in low


def test_slice0_forbidden_logic_pinned():
    text = _read()
    for phrase in SLICE0_FORBIDDEN_LOGIC:
        assert phrase in text, f"forbidden-logic phrase missing: {phrase}"
    assert "no float" in _read().lower()
