"""tests/test_phase5_fail_closed_blocked_state_contract.py — pins the Phase 5 fail-closed
blocked-state contract document (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data, builds no calculator. Asserts the
contract makes BLOCKED_NEEDS_EVIDENCE the canonical blocked status for missing/unknown/mismatched
evidence, defines blocked as a deterministic state (not an exception escape hatch), forbids
converting blocked into zero/false/pass/observed/derived/eligible/executable/tradable/ready/
profitable/net-edge, requires the full blocked-record field set and blocked-reason categories,
requires blocked to preserve provenance context without inventing fields, makes blocked terminal,
forbids blocked from authorizing action, constrains retry to new-evidence/authorization (TDD/offline
first), bars human judgment from substituting for source evidence, references the three dependent
contracts, carries the standard no-claims block (incl. safety / data-quality / data-integrity
guarantees), and lists the required Open Backlog / Deferred Decisions items — while asserting no
forbidden over-claim wording appears anywhere and forbidden positive-claim phrases appear only inside
the explicit framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase5_fail_closed_blocked_state_contract.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

REQUIRED_FIELDS = [
    "blocked_status",
    "blocked_reason",
    "blocked_source_contract",
    "missing_or_invalid_field",
    "source_artifact_or_blocked_reason",
    "source_field_or_blocked_reason",
    "deterministic_next_action",
    "human_review_required",
    "may_retry_after_evidence",
    "created_utc_timestamp_ms_or_blocked_reason",
]

BLOCKED_REASON_CATEGORIES = [
    "missing_provenance",
    "unknown_artifact_source",
    "source_field_mismatch",
    "missing_component",
    "missing_formula",
    "missing_numeric_representation",
    "missing_no_eligible_accounting",
    "missing_timestamp",
    "missing_verifier_result",
    "unsupported_artifact_type",
    "implementation_not_authorized",
]

DEPENDENT_CONTRACTS = [
    "phase5_friction_component_schema_contract.md",
    "phase5_no_eligible_handling_schema_contract.md",
    "phase5_artifact_provenance_contract.md",
]

BACKLOG_ITEMS = [
    "exact blocked-state record serialization",
    "exact deterministic_next_action vocabulary",
    "exact human_review_required policy",
    "exact retry policy and retry evidence requirements",
    "exact verifier integration for BLOCKED_NEEDS_EVIDENCE",
    "exact mapping from provenance/no-eligible/friction failures into blocked reasons",
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
# they do not collide with required negations ("does not guarantee correctness", "no safety
# guarantee", "no data-quality guarantee").
FORBIDDEN_WORDING = [
    "eliminates all risk", "zero risk", "tamper-proof", "tamper proof",
    "verified truth", "clean data", "trusted data", "is immutable",
    "guarantees correctness", "guarantees integrity", "is impossible",
    "cannot happen", "never fails", "is foolproof", "is now safe",
]


def _read():
    assert os.path.isfile(DOC), f"fail-closed blocked-state contract doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "fail-closed blocked-state contract doc is empty"


def test_contract_cross_references_present():
    text = _read()
    assert "phase5_interface_contract.md" in text
    assert "phase5_planning_gate.md" in text


def test_dependent_contracts_referenced():
    text = _read()
    missing = [c for c in DEPENDENT_CONTRACTS if c not in text]
    assert not missing, f"dependent contracts not referenced: {missing}"


def test_canonical_blocked_status():
    low = _read().lower()
    assert "blocked_needs_evidence is the canonical blocked status" in low


def test_blocked_is_deterministic_not_exception_hatch():
    low = _read().lower()
    assert "deterministic state" in low
    assert "not an exception-handling escape hatch" in low


def test_blocked_must_not_be_converted():
    low = _read().lower()
    assert "must not be converted into zero, false, pass, observed, derived, eligible, executable, tradable, ready, profitable, or net-edge input" in low


def test_all_required_fields_present():
    low = _read().lower()
    missing = [f for f in REQUIRED_FIELDS if f not in low]
    assert not missing, f"required blocked-record fields missing: {missing}"


def test_boolean_fields_declare_true_false():
    low = _read().lower()
    assert "human_review_required: true | false" in low
    assert "may_retry_after_evidence: true | false" in low


def test_all_blocked_reason_categories_present():
    low = _read().lower()
    missing = [c for c in BLOCKED_REASON_CATEGORIES if c not in low]
    assert not missing, f"blocked reason categories missing: {missing}"


def test_preserve_context_without_inventing():
    low = _read().lower()
    assert "must not invent missing fields" in low
    assert "preserve" in low and "provenance" in low


def test_blocked_is_terminal():
    low = _read().lower()
    assert "terminal for the current deterministic decision path" in low


def test_blocked_does_not_authorize_action():
    low = _read().lower()
    assert "must not authorize execution, trading, readiness, profitability, edge, net-edge, or paper/live progression" in low


def test_retry_requires_new_evidence_or_authorization():
    low = _read().lower()
    assert "retry" in low
    assert "new evidence or explicit authorization" in low
    assert "tdd/offline first" in low


def test_human_review_cannot_substitute_for_evidence():
    low = _read().lower()
    assert "human review alone must not convert blocked evidence into observed/derived without source evidence" in low
    assert "human/operator judgment must not substitute for source_artifact/source_field evidence" in low


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
