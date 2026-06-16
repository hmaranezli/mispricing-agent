"""tests/test_phase5_artifact_provenance_contract.py — pins the Phase 5 artifact provenance
contract document (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data, builds no calculator. Asserts the
contract defines provenance as a chain-of-custody / evidence-contract input (not a data-quality or
data-integrity guarantee), requires provenance before any observed/derived status is accepted,
requires the full provenance field set, enumerates valid artifact_type and artifact_phase values,
fails closed to BLOCKED_NEEDS_EVIDENCE on missing provenance / unknown source / source-field
mismatch, forbids hand-entered values without a source chain, forbids provenance from authorizing
execution/trading/readiness/profitability/net-edge, restricts classification to observed|derived|
blocked, keeps not-yet-implemented fields as explicit blocked fields, references the dependent
friction and no-eligible contracts, carries the standard no-claims block (incl. safety / data-quality
/ data-integrity guarantees), and lists the required Open Backlog / Deferred Decisions items — while
asserting no forbidden over-claim wording appears anywhere and forbidden positive-claim phrases
appear only inside the explicit framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase5_artifact_provenance_contract.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

REQUIRED_FIELDS = [
    "source_artifact",
    "source_field",
    "artifact_type",
    "artifact_phase",
    "batch_id",
    "run_id",
    "observation_id",
    "stage_name",
    "verdict_or_status",
    "utc_timestamp_ms_or_blocked_reason",
    "request_count_or_blocked_reason",
    "source_sha256_or_blocked_reason",
    "parser_version_or_blocked_reason",
    "verifier_result_or_blocked_reason",
    "blocked_reason_if_missing",
]

ARTIFACT_TYPES = [
    "json",
    "jsonl",
    "manifest",
    "summary",
    "audit_doc",
    "protocol_doc",
    "test_report",
]

ARTIFACT_PHASES = [
    "phase3d5",
    "phase4a",
    "phase4b",
    "phase4c",
    "phase5_contract",
]

DEPENDENT_CONTRACTS = [
    "phase5_friction_component_schema_contract.md",
    "phase5_no_eligible_handling_schema_contract.md",
]

BACKLOG_ITEMS = [
    "exact source_sha256 generation method",
    "exact parser_version naming/versioning scheme",
    "exact verifier_result vocabulary",
    "manifest-to-artifact join rules",
    "source_field path syntax",
    "handling for missing timestamps",
    "production/live usage blocked until separate authorization",
]

# Positive claim phrases that must NEVER appear outside framing / no-claims / prohibited-output blocks.
FORBIDDEN_CLAIM_PHRASES = [
    "ready-to-fly", "ready to fly", "system-ready", "system ready",
    "is ready", "are ready", "production ready", "paper ready",
    "execution ready", "live ready", "economics ready", "ready for live",
    "is profitable", "profit confirmed", "profitable strategy",
    "edge confirmed", "positive edge", "tradeable edge", "alpha confirmed",
]

# Over-claim / false-assurance wordings that must NOT appear anywhere (case-insensitive). Chosen so
# they do not collide with required negations ("does not guarantee correctness", "no data-quality
# guarantee", "safety guarantee", "zero-trust").
FORBIDDEN_WORDING = [
    "eliminates all risk", "zero risk", "tamper-proof", "tamper proof",
    "verified truth", "clean data", "trusted data", "is immutable",
    "guarantees correctness", "guarantees integrity", "guarantees data quality",
    "proves integrity", "data is verified", "integrity is guaranteed",
    "quality is guaranteed", "is now safe",
]


def _read():
    assert os.path.isfile(DOC), f"artifact-provenance contract doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "artifact-provenance contract doc is empty"


def test_contract_cross_references_present():
    text = _read()
    assert "phase5_interface_contract.md" in text
    assert "phase5_planning_gate.md" in text


def test_dependent_contracts_referenced():
    text = _read()
    missing = [c for c in DEPENDENT_CONTRACTS if c not in text]
    assert not missing, f"dependent contracts not referenced: {missing}"


def test_chain_of_custody_framing():
    low = _read().lower()
    assert "chain-of-custody" in low or "chain of custody" in low
    assert "evidence-contract" in low or "evidence contract" in low


def test_provenance_required_before_status_accepted():
    low = _read().lower()
    assert "provenance is required before any" in low
    assert "observed" in low and "derived" in low


def test_link_to_evidence_not_assumptions():
    low = _read().lower()
    assert "evidence, not assumptions" in low


def test_all_required_fields_present():
    low = _read().lower()
    missing = [f for f in REQUIRED_FIELDS if f not in low]
    assert not missing, f"required provenance fields missing: {missing}"


def test_all_artifact_types_present():
    low = _read().lower()
    missing = [t for t in ARTIFACT_TYPES if t not in low]
    assert not missing, f"artifact_type values missing: {missing}"


def test_all_artifact_phases_present():
    low = _read().lower()
    missing = [p for p in ARTIFACT_PHASES if p not in low]
    assert not missing, f"artifact_phase values missing: {missing}"


def test_status_vocabulary_present():
    low = _read().lower()
    assert "observed | derived | blocked" in low


def test_blocked_triggers_present():
    low = _read().lower()
    assert "blocked_needs_evidence" in low
    assert "missing required provenance" in low
    assert "unknown artifact source" in low
    assert "source field mismatch" in low


def test_no_hand_entered_values_without_chain():
    low = _read().lower()
    assert "hand-entered values" in low
    assert "source_artifact/source_field chain" in low


def test_provenance_does_not_authorize_action():
    low = _read().lower()
    assert "must not authorize execution, trading, readiness, profitability, or net-edge calculation" in low


def test_classification_only_observed_derived_blocked():
    low = _read().lower()
    assert "may only classify evidence status as observed | derived | blocked" in low


def test_not_yet_implemented_fields_are_explicit_blocked():
    low = _read().lower()
    assert "explicit blocked fields, not omitted" in low
    for f in ["source_sha256", "parser_version", "verifier_result"]:
        assert f in low, f"missing not-yet-implemented field: {f}"


def test_zero_trust_stance_without_guarantee_claims():
    low = _read().lower()
    assert "zero-trust" in low
    # The contract must explicitly disclaim security/correctness/integrity/quality guarantees.
    assert "no data-quality guarantee" in low
    assert "no data-integrity guarantee" in low


def test_no_live_execution_connection():
    low = _read().lower()
    assert "no live order" in low
    assert "no execution connection" in low


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
