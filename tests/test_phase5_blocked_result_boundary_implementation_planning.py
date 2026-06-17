"""tests/test_phase5_blocked_result_boundary_implementation_planning.py — pins the
implementation-planning artifact for the `phase5_blocked_result_boundary` component (docs-only
planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine. Asserts the planning
artifact authorizes no implementation; scopes the component to a blocked/violation result-propagation
boundary (not a validator/parser/calculator/reporting/economic engine); requires the future
frozen/immutable blocked packet field set; fixes the BLOCKED vs CONTRACT_VIOLATION status semantics
with BLOCKED_NEEDS_EVIDENCE canonical; enumerates the hard prohibitions (no truthiness/coercion, no
downgrade, no try/except masking, no mutation, no human-review substitution); enumerates the allowed
pass-through-or-fail-closed handling; keeps the component-specific no-claims boundary; references the
required dependency artifacts; restates the future-implementation gate; carries the standard
no-claims block; and avoids ready/complete/safe/absolute-risk and source-trust framing — while
asserting no forbidden over-claim wording appears anywhere and forbidden positive-claim phrases
appear only inside the explicit framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_blocked_result_boundary_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

GATE_STATUSES = [
    "PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
    "PLANNING_GATE_CONTRACT_VIOLATION",
]

PACKET_FIELDS = [
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "blocked_status",
    "reason_code",
    "missing_or_invalid_field",
    "source_contract",
    "source_artifact",
    "source_field",
    "deterministic_next_action",
    "human_review_required",
    "may_retry_after_evidence",
    "created_from_contract",
    "boundary_version",
]

DEPENDENCY_REFERENCES = [
    "phase5_input_provenance_preflight",
    "phase5_implementation_planning_gate_entrance_criteria.md",
    "phase5_fail_closed_blocked_state_contract.md",
    "phase5_artifact_provenance_contract.md",
    "phase5_input_schema_refinement_contract.md",
    "phase5_no_claims_reporting_schema_contract.md",
    "phase5_contract_set_gap_completeness_audit.md",
    "phase5_interface_contract.md",
]

HARD_PROHIBITIONS = [
    "must not use truthiness handling of a packet",
    "must not use bool/int/float/string coercion to interpret a packet",
    "must not be converted to 0, false, none, empty dict/list, eligible, observed, derived, pass, cost, edge, net_edge, readiness, profitability, or economic value",
    "no try/except masking may convert a blocked or violation result into default values",
    "must not mutate packet status, reason code, source fields, or origin metadata",
    "no downgrade from blocked or violation to observed, derived, or eligible is permitted",
    "human or operator review must not substitute for source evidence",
]

ALLOWED_HANDLING = [
    "explicit boundary api or a declared frozen packet type only",
    "passed through unchanged or fails closed to a contract violation when it is malformed or semantically downgraded",
    "deterministic next action must remain non-execution authority",
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
    assert os.path.isfile(DOC), f"blocked-result-boundary planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "blocked-result-boundary planning doc is empty"


def test_component_name_present():
    assert "phase5_blocked_result_boundary" in _read()


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_boundary_scope_statement():
    low = _read().lower()
    assert "error/state propagation boundary" in low or "result-propagation boundary" in low
    assert "not a validator, not a parser, not a calculator, not a reporting/economic engine" in low


def test_consumes_by_declared_fields():
    low = _read().lower()
    assert "this component consumes upstream preflight-style result records only by declared fields, not by truthiness, numeric coercion, exception side effects, or ad hoc dict guessing" in low


def test_plans_frozen_packet_not_implemented():
    low = _read().lower()
    assert "this task plans a future frozen/immutable blocked packet but does not implement it" in low


def test_packet_fields_present():
    low = _read().lower()
    missing = [f for f in PACKET_FIELDS if f.lower() not in low]
    assert not missing, f"planned packet fields missing: {missing}"


def test_status_semantics():
    text = _read()
    missing = [s for s in GATE_STATUSES if s not in text]
    assert not missing, f"gate statuses missing: {missing}"
    low = text.lower()
    assert "planning_gate_blocked_needs_evidence stays distinct from planning_gate_contract_violation" in low
    assert "blocked_needs_evidence remains canonical for missing/unknown/mismatched evidence" in low
    assert "contract_violation remains the fail-closed class for malformed structure, forbidden claims, unsupported source contract, cycle/depth guard, or unauthorized semantic downgrade" in low


def test_hard_prohibitions_present():
    low = _read().lower()
    missing = [p for p in HARD_PROHIBITIONS if p not in low]
    assert not missing, f"hard prohibitions missing: {missing}"


def test_allowed_handling_present():
    low = _read().lower()
    missing = [a for a in ALLOWED_HANDLING if a not in low]
    assert not missing, f"allowed handling missing: {missing}"


def test_no_claims_continuity():
    low = _read().lower()
    assert "the blocked packet is not evidence quality, not source truth, not data quality, not readiness, not safety, not economic validity, not profitability evidence, not edge, not net-edge input, not trading instruction, and not execution authority" in low


def test_dependency_references_present():
    text = _read()
    missing = [d for d in DEPENDENCY_REFERENCES if d not in text]
    assert not missing, f"dependency references missing: {missing}"


def test_future_implementation_gate():
    low = _read().lower()
    assert "any implementation requires separate explicit authorization, failing tests first, declared provenance, component-scoped work, and offline/tdd scope" in low
    assert "does not authorize implementation or selecting the next component" in low


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
