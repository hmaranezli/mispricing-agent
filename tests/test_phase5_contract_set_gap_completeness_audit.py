"""tests/test_phase5_contract_set_gap_completeness_audit.py — pins the Phase 5 contract-set
gap/completeness audit artifact (docs-only audit, offline, read-only).

This suite does two things, both offline and read-only:
  1. Pins the audit doc's invariants (result vocabulary, exact inspected HEAD, scope list, closeout
     coverage, no-claims, scoped-result disclaimer, next-step boundary, backlog).
  2. Independently verifies the repo facts the audit asserts within its checked scope: every required
     Phase 5 contract doc exists, every required contract test exists, the interface contract links to
     each contract doc, the handoff records each committed closeout slice, and no stale hash-free
     backlog pointer remains. This grounds the audit's OBSERVED_NO_GAP_WITHIN_CHECKED_SCOPE result in
     actual repo state rather than assertion.

No batch, no endpoint, no live/market data, no calculator, no fixture engine.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff", "phase5_contract_set_gap_completeness_audit.md")
INTERFACE = os.path.join(REPO, "docs", "protocols", "phase5_interface_contract.md")
HANDOFF = os.path.join(REPO, "docs", "handoff", "phase4c_state_pre_phase5.md")

NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"
FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"

INSPECTED_HEAD = "f0151fcfa2f00cf8fee4cf76d82b0229a6e0d0dc"

RESULT_VOCAB = [
    "OBSERVED_NO_GAP_WITHIN_CHECKED_SCOPE",
    "GAP_OBSERVED",
    "BLOCKED_NEEDS_EVIDENCE",
]

PROTOCOL_DOCS = [
    "phase5_planning_gate.md",
    "phase5_interface_contract.md",
    "phase5_friction_component_schema_contract.md",
    "phase5_no_eligible_handling_schema_contract.md",
    "phase5_artifact_provenance_contract.md",
    "phase5_fail_closed_blocked_state_contract.md",
    "phase5_observation_discovery_cost_schema_contract.md",
    "phase5_no_claims_reporting_schema_contract.md",
    "phase5_input_schema_refinement_contract.md",
    "phase5_offline_fixture_contract.md",
]

# Contract docs the interface contract must link to (the 8 refining contracts).
LINKED_CONTRACTS = [
    "phase5_friction_component_schema_contract.md",
    "phase5_no_eligible_handling_schema_contract.md",
    "phase5_artifact_provenance_contract.md",
    "phase5_fail_closed_blocked_state_contract.md",
    "phase5_observation_discovery_cost_schema_contract.md",
    "phase5_no_claims_reporting_schema_contract.md",
    "phase5_input_schema_refinement_contract.md",
    "phase5_offline_fixture_contract.md",
]

CONTRACT_TESTS = [
    "test_phase5_planning_gate.py",
    "test_phase5_interface_contract.py",
    "test_phase5_friction_component_schema_contract.py",
    "test_phase5_no_eligible_handling_schema_contract.py",
    "test_phase5_artifact_provenance_contract.py",
    "test_phase5_fail_closed_blocked_state_contract.py",
    "test_phase5_observation_discovery_cost_schema_contract.py",
    "test_phase5_no_claims_reporting_schema_contract.py",
    "test_phase5_input_schema_refinement_contract.py",
    "test_phase5_offline_fixture_contract.py",
]

CLOSEOUT_HASHES = [
    "6b2e577",  # friction component schema
    "f032bf2",  # no-eligible handling
    "37159b5",  # artifact provenance
    "65eaac8",  # fail-closed blocked-state
    "cb71d01",  # observation/discovery cost
    "f9e6260",  # no-claims/reporting
    "ebe5d16",  # input-schema refinement
    "eb2b6a9",  # offline fixture
]

CLOSEOUT_SLICES = [
    "friction component schema",
    "no-eligible handling",
    "artifact provenance",
    "fail-closed blocked-state",
    "observation/discovery cost",
    "no-claims/reporting",
    "input-schema refinement",
    "offline fixture",
]

BACKLOG_ITEMS = [
    "future implementation-planning gate entrance criteria",
    "exact component-by-component implementation order",
    "exact test boundary between contract tests and implementation tests",
    "exact verifier expansion policy",
    "exact policy for when net-edge work may be proposed",
    "exact policy for when public-data or artifact-backed runtime work may be proposed",
    "production/live usage blocked until separate authorization",
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


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _read_doc():
    assert os.path.isfile(DOC), f"audit doc missing: {DOC}"
    return _read(DOC)


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


# ---- audit doc invariants ----

def test_doc_exists():
    assert _read_doc().strip(), "audit doc is empty"


def test_read_only_framing():
    low = _read_doc().lower()
    assert "read-only" in low
    assert "docs/tests only" in low or "docs + tests only" in low
    assert "not implementation" in low


def test_inspected_head_recorded():
    assert INSPECTED_HEAD in _read_doc()


def test_result_vocabulary_present():
    text = _read_doc()
    missing = [v for v in RESULT_VOCAB if v not in text]
    assert not missing, f"audit result vocabulary missing: {missing}"


def test_audit_result_declared():
    assert "Audit result: OBSERVED_NO_GAP_WITHIN_CHECKED_SCOPE" in _read_doc()


def test_scope_lists_all_docs():
    text = _read_doc()
    missing = [d for d in PROTOCOL_DOCS if d not in text]
    assert not missing, f"scope is missing protocol docs: {missing}"
    assert "phase4c_state_pre_phase5.md" in text


def test_contract_test_matrix_present():
    text = _read_doc()
    assert "Checked contract/test matrix" in text
    missing = [t for t in CONTRACT_TESTS if t not in text]
    assert not missing, f"contract/test matrix missing tests: {missing}"


def test_closeout_slices_named():
    low = _read_doc().lower()
    missing = [s for s in CLOSEOUT_SLICES if s not in low]
    assert not missing, f"closeout slices missing: {missing}"


def test_scoped_result_disclaimer():
    low = _read_doc().lower()
    assert "scoped only to checked" in low
    assert "does not mean ready, complete, safe, profitable, or implementation-authorized" in low


def test_next_step_boundary():
    low = _read_doc().lower()
    assert "separately authorized implementation-planning gate entrance-criteria task" in low
    assert "not implementation" in low


def test_not_authorized_restatements():
    low = _read_doc().lower()
    for term in ["net-edge engine remains not authorized",
                 "calculator remains not authorized",
                 "friction engine remains not authorized"]:
        assert term in low, f"missing not-authorized restatement: {term}"
    assert "parser/loader/fixture engine" in low


def test_backlog_section_present_with_items():
    text = _read_doc()
    assert "Open Backlog / Deferred Decisions" in text
    low = text.lower()
    missing = [b for b in BACKLOG_ITEMS if b.lower() not in low]
    assert not missing, f"backlog items missing: {missing}"


def test_no_claims_block_present():
    low = _read_doc().lower()
    assert NO_CLAIMS_START.lower() in low and NO_CLAIMS_END.lower() in low
    for term in ["no edge", "no pnl", "no profitability", "no alpha",
                 "no live readiness", "no paper readiness", "no economics readiness",
                 "no safety guarantee", "no data-quality guarantee", "no data-integrity guarantee"]:
        assert term in low, f"no-claims term missing: {term}"


def test_no_forbidden_overclaim_wording_anywhere():
    low = _read_doc().lower()
    hits = [w for w in FORBIDDEN_WORDING if w in low]
    assert not hits, f"forbidden over-claim wording present: {hits}"


def test_forbidden_claims_only_in_framing_no_claims_or_prohibited_outputs():
    text = _read_doc()
    body = _strip_block(text, FRAMING_START, FRAMING_END)
    body = _strip_block(body, NO_CLAIMS_START, NO_CLAIMS_END)
    body = _strip_block(body, PROHIBITED_OUT_START, PROHIBITED_OUT_END).lower()
    hits = [p for p in FORBIDDEN_CLAIM_PHRASES if p in body]
    assert not hits, f"forbidden positive claim(s) outside allowed sections: {hits}"


# ---- repo-fact verification (grounds OBSERVED_NO_GAP_WITHIN_CHECKED_SCOPE) ----

def test_all_protocol_docs_exist():
    missing = [d for d in PROTOCOL_DOCS
               if not os.path.isfile(os.path.join(REPO, "docs", "protocols", d))]
    assert not missing, f"protocol docs missing on disk: {missing}"


def test_all_contract_tests_exist():
    missing = [t for t in CONTRACT_TESTS
               if not os.path.isfile(os.path.join(REPO, "tests", t))]
    assert not missing, f"contract tests missing on disk: {missing}"


def test_interface_links_to_each_contract():
    itext = _read(INTERFACE)
    missing = [c for c in LINKED_CONTRACTS if c not in itext]
    assert not missing, f"interface contract does not link: {missing}"


def test_handoff_records_each_closeout():
    htext = _read(HANDOFF)
    missing = [h for h in CLOSEOUT_HASHES if h not in htext]
    assert not missing, f"handoff missing closeout hashes: {missing}"


def test_handoff_has_no_stale_backlog_pointer():
    htext = _read(HANDOFF)
    assert "backlog pointer" not in htext.lower(), "stale hash-free backlog pointer remains in handoff"
