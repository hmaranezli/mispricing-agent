"""tests/test_phase5_input_provenance_preflight_implementation_planning.py — pins the first
component-scoped implementation-planning artifact for `phase5_input_provenance_preflight`
(docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine. Asserts the planning
artifact authorizes no implementation; scopes the component to declared input-shape and provenance
requirements only (no market-truth / data-quality / economic / profitability / readiness / source-
reliability validation); references the seven required source contracts; declares the full entry
packet; enumerates the planned input checks (incl. source_sha256 / parser_version / verifier_result
blocked-reason fields and chain-break fail conditions); fixes the deterministic
OBSERVED / BLOCKED_NEEDS_EVIDENCE / CONTRACT_VIOLATION status mapping; bars silent defaults; keeps
no-claims continuity; bounds fixtures to static offline diagnostic examples; restates the later-
implementation requirements; carries the standard no-claims block; and avoids ready/complete/safe/
absolute-risk and source-trust framing — while asserting no forbidden over-claim wording appears
anywhere and forbidden positive-claim phrases appear only inside the explicit framing / no-claims /
prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_input_provenance_preflight_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

GATE_STATUSES = [
    "PLANNING_GATE_OBSERVED",
    "PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
    "PLANNING_GATE_CONTRACT_VIOLATION",
]

SOURCE_CONTRACTS = [
    "phase5_implementation_planning_gate_entrance_criteria.md",
    "phase5_input_schema_refinement_contract.md",
    "phase5_artifact_provenance_contract.md",
    "phase5_fail_closed_blocked_state_contract.md",
    "phase5_no_claims_reporting_schema_contract.md",
    "phase5_offline_fixture_contract.md",
    "phase5_interface_contract.md",
]

ENTRY_PACKET_FIELDS = [
    "component_name",
    "source_contracts",
    "source_artifacts",
    "source_fields",
    "required_input_schema_fields",
    "expected observed/derived/blocked outputs",
    "blocked_reason",
    "deterministic_next_action",
    "required failing tests",
    "no-claims/reporting boundary",
    "proof that no execution/trading authority is introduced",
]

PLANNED_CHECKS = [
    "record identity fields are declared",
    "provenance fields are declared",
    "source_contract is known and allowed",
    "source_artifact is declared as a read-only provenance reference",
    "source_field is declared and mapped to the source contract",
    "required input-schema categories are present as shape declarations",
    "blocked semantics are declared for missing/unknown/mismatched evidence",
    "source_sha256_or_blocked_reason is declared for the source artifact",
    "parser_version_or_blocked_reason is declared",
    "verifier_result_or_blocked_reason is declared",
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
    "final phase 5 contract", "last critical piece", "is complete", "is perfect",
    "is now safe", "fully complete", "the last piece",
    "source is trusted", "data is valid",
]


def _read():
    assert os.path.isfile(DOC), f"component planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "component planning doc is empty"


def test_component_name_present():
    assert "phase5_input_provenance_preflight" in _read()


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_component_does_not_validate_truth():
    low = _read().lower()
    assert "does not validate market truth, data quality, economic validity, profitability, readiness, or source reliability" in low


def test_component_scope_statement():
    low = _read().lower()
    assert "only checks declared input shape and provenance requirements before any downstream phase 5 component may be planned" in low


def test_source_contracts_referenced():
    text = _read()
    missing = [c for c in SOURCE_CONTRACTS if c not in text]
    assert not missing, f"source contracts missing: {missing}"


def test_entry_packet_fields_present():
    low = _read().lower()
    missing = [f for f in ENTRY_PACKET_FIELDS if f.lower() not in low]
    assert not missing, f"entry packet fields missing: {missing}"


def test_planned_input_checks_present():
    low = _read().lower()
    missing = [c for c in PLANNED_CHECKS if c not in low]
    assert not missing, f"planned input checks missing: {missing}"


def test_not_implemented_fields_explicit_blocked():
    low = _read().lower()
    assert "must be explicit blocked fields with blocked reasons, not omitted" in low


def test_chain_break_fail_conditions():
    low = _read().lower()
    assert "chain-break fail conditions" in low
    assert "missing source_artifact, unknown source_artifact, missing source_field, source_field mismatch, missing source_sha256_or_blocked_reason, missing parser_version_or_blocked_reason, and missing verifier_result_or_blocked_reason" in low


def test_status_mapping_present():
    text = _read()
    missing = [s for s in GATE_STATUSES if s not in text]
    assert not missing, f"gate statuses missing: {missing}"
    low = text.lower()
    assert "evidence present within checked scope" in low
    assert "missing or unknown source_artifact/source_field/source_contract evidence" in low
    assert "malformed field declaration, forbidden field mapping, unsupported source contract assertion, or claim that planning authorizes implementation" in low
    assert "missing source_sha256_or_blocked_reason, parser_version_or_blocked_reason, or verifier_result_or_blocked_reason" in low
    assert "claiming source truth, data validity, source reliability, or data-quality/data-integrity guarantee" in low


def test_no_silent_defaults():
    low = _read().lower()
    assert "must not become zero, false, pass, default, floor, baseline, assumed, guessed, eligible, executable, tradable, ready, profitable, or net-edge input" in low


def test_no_claims_continuity():
    low = _read().lower()
    assert "must not output or imply alpha, pnl, edge, net-edge, profitability, readiness, trading instruction, execution authority, safety guarantee, data-quality guarantee, data-integrity guarantee, or source-truth guarantee" in low


def test_fixture_boundary():
    low = _read().lower()
    assert "future tests must use static offline diagnostic fixtures only" in low
    assert "no fixture generator/factory/loader/parser" in low


def test_later_implementation_requirements():
    low = _read().lower()
    assert "any later implementation of this component requires separate explicit authorization, failing tests first, declared provenance, and offline/tdd scope" in low


def test_no_claims_block_present():
    low = _read().lower()
    assert NO_CLAIMS_START.lower() in low and NO_CLAIMS_END.lower() in low
    for term in ["no edge", "no pnl", "no profitability", "no alpha",
                 "no live readiness", "no paper readiness", "no economics readiness",
                 "no safety guarantee", "no data-quality guarantee", "no data-integrity guarantee"]:
        assert term in low, f"no-claims term missing: {term}"


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
