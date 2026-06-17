"""tests/test_phase5_input_schema_refinement_contract.py — pins the Phase 5 input-schema refinement
contract document (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data, builds no calculator/parser/loader.
Asserts the contract defines input SHAPE only (presence is not evidence quality/truth/readiness),
separates inputs into the required categories, requires the record_identity and provenance field
sets, keeps gross-edge fields read-only (never recomputed/refreshed/fetched/live), represents
eligible/ineligible/no-eligible explicitly without downgrading no-eligible, treats friction
placeholders as non-value / non-computable slots that fail closed to BLOCKED_NEEDS_EVIDENCE, keeps
mechanical metadata separate from market-content with no count→cost conversion, preserves the
observed/derived/blocked reporting vocabulary, fails closed on missing/malformed/unknown inputs,
forbids downgrading blocked input, bars human review from substituting for source evidence,
references the seven dependent contracts, carries the standard no-claims block, avoids
final/complete/ready and absolute-risk framing, and lists the required Open Backlog / Deferred
Decisions items — while asserting no forbidden over-claim wording appears anywhere and forbidden
positive-claim phrases appear only inside the explicit framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase5_input_schema_refinement_contract.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

INPUT_CATEGORIES = [
    "record_identity",
    "gross_edge_fields",
    "eligibility_state",
    "no_eligible_state",
    "friction_component_placeholders",
    "mechanical_observation_metadata",
    "provenance_fields",
    "reporting_boundary_fields",
    "blocked_state_fields",
]

RECORD_IDENTITY_FIELDS = [
    "input_schema_version",
    "input_record_type",
    "batch_id",
    "run_id",
    "observation_id",
    "source_contract",
]

PROVENANCE_FIELDS = [
    "source_artifact",
    "source_field",
    "artifact_type_or_blocked_reason",
    "artifact_phase_or_blocked_reason",
    "provenance_status",
    "source_sha256_or_blocked_reason",
    "parser_version_or_blocked_reason",
    "verifier_result_or_blocked_reason",
]

DEPENDENT_CONTRACTS = [
    "phase5_interface_contract.md",
    "phase5_friction_component_schema_contract.md",
    "phase5_no_eligible_handling_schema_contract.md",
    "phase5_artifact_provenance_contract.md",
    "phase5_fail_closed_blocked_state_contract.md",
    "phase5_observation_discovery_cost_schema_contract.md",
    "phase5_no_claims_reporting_schema_contract.md",
]

BACKLOG_ITEMS = [
    "exact input record serialization",
    "exact input_schema_version policy",
    "exact input_record_type vocabulary",
    "exact source_contract vocabulary",
    "exact source_field path syntax",
    "exact gross-edge field allowlist from audited artifacts",
    "exact blocked-input rendering policy",
    "exact non-value placeholder serialization for friction component placeholders",
    "exact rule for distinguishing placeholder, blocked, observed, and derived input fields",
    "exact fixture shape to be handled by the later offline fixture contract",
    "verifier integration for malformed/missing/unknown input fields",
    "production/live usage blocked until separate authorization",
    "exact placeholder vocabulary, including whether labels like PENDING_SOURCE_FIELD or BLOCKED_PLACEHOLDER are canonical",
]

# Positive claim phrases that must NEVER appear outside framing / no-claims / prohibited-output blocks.
FORBIDDEN_CLAIM_PHRASES = [
    "ready-to-fly", "ready to fly", "system-ready", "system ready",
    "is ready", "are ready", "production ready", "paper ready",
    "execution ready", "live ready", "economics ready", "ready for live",
    "is profitable", "profit confirmed", "profitable strategy",
    "edge confirmed", "positive edge", "tradeable edge", "alpha confirmed",
]

# Over-claim / false-assurance / finality / absolute-risk wordings that must NOT appear anywhere.
FORBIDDEN_WORDING = [
    "eliminates all risk", "eliminates risk", "zero risk", "tamper-proof",
    "verified truth", "clean data", "trusted data", "is immutable",
    "guarantees correctness", "is impossible", "cannot happen",
    "final phase 5 contract", "last critical piece", "is complete", "is perfect",
    "is now safe", "fully complete", "the last piece",
]


def _read():
    assert os.path.isfile(DOC), f"input-schema refinement contract doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "input-schema refinement contract doc is empty"


def test_contract_planning_only_framing():
    low = _read().lower()
    assert "contract/planning artifact only" in low or "contract/planning only" in low
    assert "not implementation" in low


def test_dependent_contracts_referenced():
    text = _read()
    missing = [c for c in DEPENDENT_CONTRACTS if c not in text]
    assert not missing, f"dependent contracts not referenced: {missing}"


def test_shape_only_not_evidence_quality():
    low = _read().lower()
    assert "describes shape only" in low
    assert "input presence must not be treated as evidence quality, source truth, readiness, or economic validity" in low


def test_all_input_categories_present():
    low = _read().lower()
    missing = [c for c in INPUT_CATEGORIES if c not in low]
    assert not missing, f"input categories missing: {missing}"


def test_record_identity_fields_present():
    low = _read().lower()
    missing = [f for f in RECORD_IDENTITY_FIELDS if f not in low]
    assert not missing, f"record_identity fields missing: {missing}"


def test_provenance_fields_present():
    low = _read().lower()
    missing = [f for f in PROVENANCE_FIELDS if f not in low]
    assert not missing, f"provenance fields missing: {missing}"


def test_gross_edge_read_only():
    low = _read().lower()
    assert "must not be recomputed, refreshed, fetched, or treated as live data" in low


def test_no_eligible_not_downgraded():
    low = _read().lower()
    assert "no-eligible must not be converted into error, zero value, opportunity cost, idle cost, profitability evidence, or readiness signal" in low


def test_friction_placeholder_non_value():
    low = _read().lower()
    assert "must not be represented as 0, null, false, empty string, default value, floor value, baseline value, assumed value, guessed value, or usable numeric input" in low


def test_friction_placeholder_presence_not_evidence():
    low = _read().lower()
    assert "must not be treated as cost evidence, zero cost, usable friction value, net-edge input, economic inference, readiness evidence, or implementation authority" in low


def test_placeholder_non_computable_semantics():
    low = _read().lower()
    assert "non-value placeholder semantics" in low
    assert "pending_source_field" in low and "blocked_placeholder" in low
    assert "must be non-computable" in low
    assert "must not consume a placeholder as a numeric, boolean, empty, default, floor, baseline, assumed, guessed, or usable friction value" in low


def test_placeholder_unresolved_outcome():
    low = _read().lower()
    assert "must not silently impute, coerce, cast, or default the value" in low
    assert "placeholder resolution requires a separate explicitly authorized tdd/offline task with evidence provenance" in low


def test_mechanical_metadata_no_conversion():
    low = _read().lower()
    assert "must not be converted into dollars, bps, edge, net-edge, profitability, readiness, idle cost, opportunity cost, or any cost figure" in low


def test_reporting_boundary_vocabulary_preserved():
    low = _read().lower()
    assert "observed/derived/blocked" in low or "observed / derived / blocked" in low


def test_fail_closed_on_bad_input():
    low = _read().lower()
    assert "missing/malformed/unknown input fields, missing provenance, unknown source contract, source-field mismatch, or forbidden claim wording must fail closed" in low
    assert "blocked_needs_evidence" in low


def test_blocked_input_not_downgraded():
    low = _read().lower()
    assert "must not be downgraded into zero, false, pass, observed, derived, eligible, executable, tradable, ready, profitable, or net-edge input" in low


def test_human_review_not_substitute():
    low = _read().lower()
    assert "human/operator review must not substitute for source_artifact/source_field evidence" in low


def test_backlog_section_present_with_items():
    text = _read()
    assert "Open Backlog / Deferred Decisions" in text
    low = text.lower()
    missing = [b for b in BACKLOG_ITEMS if b.lower() not in low]
    assert not missing, f"backlog items missing: {missing}"


def test_no_claims_block_present():
    low = _read().lower()
    assert NO_CLAIMS_START.lower() in low and NO_CLAIMS_END.lower() in low
    for term in ["no edge", "no pnl", "no profitability", "no alpha",
                 "no live readiness", "no paper readiness", "no economics readiness",
                 "no safety guarantee", "no data-quality guarantee", "no data-integrity guarantee"]:
        assert term in low, f"no-claims term missing: {term}"


def test_authorizes_no_implementation():
    low = _read().lower()
    assert "no implementation is authorized" in low or "authorizes no phase 5 implementation" in low
    assert "implementation still requires separate tdd" in low


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


def test_generated_artifacts_not_referenced_as_tracked():
    text = _read()
    low = text.lower()
    assert "untracked" in low, "must state generated artifacts are untracked"
    assert "git add ." not in text, "must not reference blanket staging"
