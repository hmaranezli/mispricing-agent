"""tests/test_phase5_no_eligible_handling_schema_contract.py — pins the Phase 5 no-eligible
handling schema contract document (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data, builds no calculator. Asserts the
contract defines no-eligible as an observed STATE (not a calculation/cost), forbids it from updating
edge/net-edge/profitability/readiness/trading-authority, requires the full field set and the
observed|blocked status vocabulary, enumerates the valid no-eligible state categories, anchors
provenance to Phase 4C Observation #3, fails closed to BLOCKED_NEEDS_EVIDENCE on missing
provenance/accounting, forbids zero-filling (cost=0/edge=0/profitability=0), declares no live
execution connection, frames no-eligible as VALID_EVIDENCE / observed-state material (not a stage
failure by default), carries the standard no-claims block (incl. idle-cost / opportunity-cost), and
lists the required Open Backlog / Deferred Decisions items — while asserting no forbidden over-claim
wording appears anywhere and forbidden positive-claim phrases appear only inside the explicit
framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase5_no_eligible_handling_schema_contract.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

PROVENANCE_TOKENS = [
    "phase4c_batch_1781637248",
    "gross_edge_no_eligible_snapshots",
    "phase4b_no_eligible_records",
    "eligible_pairs=0",
    "one_sided_book",
    "spread_too_wide",
]

REQUIRED_FIELDS = [
    "state_name",
    "status",
    "source_artifact",
    "source_field",
    "observation_id",
    "batch_id",
    "run_id",
    "candidate_pairs",
    "eligible_pairs",
    "ineligible_reasons",
    "request_count",
    "discovery_requests",
    "book_requests",
    "deterministic_interpretation",
    "blocked_reason_if_missing",
]

STATE_CATEGORIES = [
    "spread_too_wide",
    "one_sided_book",
    "no_complement_token",
    "data_void",
    "request_cap_blocked",
    "unknown_requires_evidence",
]

BACKLOG_ITEMS = [
    "exact representation of no-eligible state records in future implementation",
    "exact verifier integration status labels",
    "exact mapping from Phase 4C ineligible reasons to Phase 5 state categories",
    "whether request/accounting cost joins friction schema later",
    "no-eligible aggregation rules deferred",
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

# Over-claim wordings that must NOT appear anywhere (case-insensitive).
FORBIDDEN_WORDING = [
    "technical debt is eliminated", "risk is zero", "reduced by",
    "guarantees correctness", "proves determinism", "is a mathematical proof",
    "validates the model", "is now justified", "begin automatically",
    "correctness is guaranteed", "system stability is proven",
    "net edge is positive", "edge is confirmed", "eliminates all risk",
    "works by nature",
]


def _read():
    assert os.path.isfile(DOC), f"no-eligible contract doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "no-eligible contract doc is empty"


def test_contract_cross_references_present():
    text = _read()
    assert "phase5_interface_contract.md" in text
    assert "phase5_planning_gate.md" in text


def test_no_eligible_is_a_state_not_a_calculation():
    low = _read().lower()
    assert "state, not a calculation" in low


def test_provenance_tokens_present():
    low = _read().lower()
    missing = [t for t in PROVENANCE_TOKENS if t not in low]
    assert not missing, f"provenance tokens missing: {missing}"


def test_all_required_fields_present():
    low = _read().lower()
    missing = [f for f in REQUIRED_FIELDS if f not in low]
    assert not missing, f"required fields missing: {missing}"


def test_status_vocabulary_present():
    low = _read().lower()
    assert "observed | blocked" in low
    assert "observed" in low and "blocked" in low


def test_all_state_categories_present():
    low = _read().lower()
    missing = [c for c in STATE_CATEGORIES if c not in low]
    assert not missing, f"state categories missing: {missing}"


def test_must_not_update_edge_or_authority():
    low = _read().lower()
    assert "must not update edge, net-edge, profitability, readiness, or trading authority" in low


def test_records_observation_and_provenance_only():
    low = _read().lower()
    assert "observation and discovery accounting and provenance only" in low


def test_missing_provenance_blocks():
    low = _read().lower()
    assert "missing provenance" in low
    assert "blocked_needs_evidence" in low


def test_no_zero_filling():
    low = _read().lower()
    assert "no zero-filling" in low
    assert "must not become cost=0, edge=0, or profitability=0" in low


def test_no_live_execution_connection():
    low = _read().lower()
    assert "no live order" in low
    assert "no execution connection" in low


def test_verifier_language_valid_evidence_not_stage_failure():
    low = _read().lower()
    assert "valid_evidence" in low
    assert "observed-state" in low
    assert "not a stage failure by default" in low


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
                 "no idle-cost", "no opportunity-cost"]:
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
