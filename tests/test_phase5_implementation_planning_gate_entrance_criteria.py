"""tests/test_phase5_implementation_planning_gate_entrance_criteria.py — pins the Phase 5
implementation-planning gate entrance-criteria contract (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data, builds no calculator/engine. Asserts
the contract authorizes no implementation, keeps the scoped audit-language disclaimer, defines the
three planning-gate statuses, preserves BLOCKED_NEEDS_EVIDENCE as canonical, enforces a
component-by-component lock with a per-component preflight gate, keeps no-claims continuity, bars
silent defaults, requires the full future implementation-planning entry packet, restates that later
implementation needs separate authorization / failing-tests-first / declared provenance /
component-scoped work, references the ten dependent contracts, carries the standard no-claims block,
and avoids ready/complete/safe/absolute-risk framing — while asserting no forbidden over-claim wording
appears anywhere and forbidden positive-claim phrases appear only inside the explicit framing /
no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase5_implementation_planning_gate_entrance_criteria.md")

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

DEPENDENT_CONTRACTS = [
    "phase5_interface_contract.md",
    "phase5_friction_component_schema_contract.md",
    "phase5_no_eligible_handling_schema_contract.md",
    "phase5_artifact_provenance_contract.md",
    "phase5_fail_closed_blocked_state_contract.md",
    "phase5_observation_discovery_cost_schema_contract.md",
    "phase5_no_claims_reporting_schema_contract.md",
    "phase5_input_schema_refinement_contract.md",
    "phase5_offline_fixture_contract.md",
    "phase5_contract_set_gap_completeness_audit.md",
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
]


def _read():
    assert os.path.isfile(DOC), f"entrance-criteria contract doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "entrance-criteria contract doc is empty"


def test_contract_planning_only_and_no_implementation():
    low = _read().lower()
    assert "contract/planning artifact only" in low or "contract/planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no phase 5 implementation" in low
    assert "implementation still requires separate tdd" in low


def test_scoped_audit_language_disclaimer():
    low = _read().lower()
    assert "observed_no_gap_within_checked_scope does not mean ready, complete, safe, profitable, implementation-authorized, paper-ready, live-ready, or net-edge authorized" in low


def test_gate_statuses_present():
    text = _read()
    missing = [s for s in GATE_STATUSES if s not in text]
    assert not missing, f"gate statuses missing: {missing}"


def test_blocked_needs_evidence_canonical():
    low = _read().lower()
    assert "blocked_needs_evidence remains canonical for missing/unknown/mismatched evidence" in low


def test_component_by_component_lock():
    low = _read().lower()
    assert "future implementation planning must be component-scoped" in low
    assert "no global phase 5 implementation plan may bundle multiple components unless separately authorized" in low
    assert "each component must declare source contracts, source artifacts, source fields, blocked behavior, and tests before planning" in low


def test_component_planning_preflight():
    low = _read().lower()
    assert "each component must have a scoped preflight/audit gate before implementation planning" in low
    assert "the preflight must verify provenance, fail-closed behavior, no-claims continuity, fixture/test scope, and no stale backlog pointers" in low
    assert "if the component lacks evidence, source fields, or blocked semantics, the planning gate must block" in low


def test_no_claims_continuity():
    low = _read().lower()
    assert "planning documents must not convert observed/derived/blocked states into alpha, pnl, edge, net-edge, profitability, readiness, trading instruction, execution authority, safety guarantee, data-quality guarantee, or data-integrity guarantee" in low
    assert "planning must not assume that future implementation will produce economic value" in low


def test_no_silent_defaults():
    low = _read().lower()
    assert "must not become zero, false, pass, default, floor, baseline, assumed, guessed, eligible, executable, tradable, ready, profitable, or net-edge input" in low


def test_entry_packet_fields_present():
    low = _read().lower()
    missing = [f for f in ENTRY_PACKET_FIELDS if f.lower() not in low]
    assert not missing, f"entry packet fields missing: {missing}"


def test_later_implementation_requirements():
    low = _read().lower()
    assert "any later implementation still requires a separate explicit authorization, failing tests first, declared provenance, and component-scoped work" in low


def test_dependent_contracts_referenced():
    text = _read()
    missing = [c for c in DEPENDENT_CONTRACTS if c not in text]
    assert not missing, f"dependent contracts not referenced: {missing}"


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
