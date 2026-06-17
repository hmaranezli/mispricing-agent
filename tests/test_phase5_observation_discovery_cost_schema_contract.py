"""tests/test_phase5_observation_discovery_cost_schema_contract.py — pins the Phase 5
observation/discovery cost schema contract document (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data, builds no calculator/parser/loader.
Asserts the contract represents mechanical observation activity as evidence-bearing metadata ONLY
(a representation schema, not a cost calculation), distinguishes mechanical metadata from
market-content observations, anchors to the audited Phase 4C obs #1/#2/#3 mechanical facts, refuses
to convert counts into dollars/bps/edge/net-edge/profitability/readiness, treats obs #3 no-eligible
as not-a-cost, fails closed to BLOCKED_NEEDS_EVIDENCE on missing provenance/accounting, forbids
fixed/default/floor/baseline/assumed/guessed cost, references the four dependent contracts, declares
no live execution connection, carries the standard no-claims block (incl. safety / data-quality /
data-integrity guarantees), avoids "final/last/complete/perfect/ready" framing, and lists the
required Open Backlog / Deferred Decisions items — while asserting no forbidden over-claim wording
appears anywhere and forbidden positive-claim phrases appear only inside the explicit framing /
no-claims / prohibited-output blocks.

Fixture discipline: the Phase 4C obs facts are used ONLY as audited doc-contract string constants;
no generated artifact is read, no parser/loader/fixture engine is built.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase5_observation_discovery_cost_schema_contract.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

REQUIRED_FIELDS = [
    "request_count",
    "discovery_requests",
    "book_requests",
    "stage_order",
    "artifact_count",
    "log_count",
    "candidate_pairs",
    "eligible_pairs",
    "ineligible_reasons",
    "batch_id",
    "run_id",
    "observation_id",
    "source_artifact",
    "source_field",
    "provenance_status",
    "blocked_reason_if_missing",
]

DEPENDENT_CONTRACTS = [
    "phase5_artifact_provenance_contract.md",
    "phase5_fail_closed_blocked_state_contract.md",
    "phase5_no_eligible_handling_schema_contract.md",
    "phase5_friction_component_schema_contract.md",
]

OBS_FACT_TOKENS = [
    "obs #1", "obs #2", "obs #3",
    "request_count 12", "discovery_requests 4", "book_requests 8",
    "eligible_pairs 4", "eligible_pairs 0",
]

BACKLOG_ITEMS = [
    "exact serialization of observation/discovery cost records",
    "exact source_field path syntax for mechanical fields",
    "exact request-count cap integration",
    "exact mapping, if ever authorized, from mechanical counts to friction component values",
    "exact verifier vocabulary for observed vs blocked mechanical accounting",
    "exact interaction with no-eligible state records",
    "exact fixture shape for eligible and no-eligible examples",
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

# Over-claim / false-assurance / finality wordings that must NOT appear anywhere (case-insensitive).
# Chosen so they do not collide with required negations ("no safety guarantee", "does not guarantee
# correctness", "no economics readiness").
FORBIDDEN_WORDING = [
    "eliminates all risk", "zero risk", "tamper-proof", "verified truth",
    "clean data", "trusted data", "is immutable", "guarantees correctness",
    "is impossible", "cannot happen", "final phase 5 contract", "last critical piece",
    "is complete", "is perfect", "is now safe", "fully complete",
    "the last piece", "is guaranteed",
]


def _read():
    assert os.path.isfile(DOC), f"observation/discovery cost contract doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "observation/discovery cost contract doc is empty"


def test_contract_cross_references_present():
    text = _read()
    assert "phase5_interface_contract.md" in text
    assert "phase5_planning_gate.md" in text


def test_dependent_contracts_referenced():
    text = _read()
    missing = [c for c in DEPENDENT_CONTRACTS if c not in text]
    assert not missing, f"dependent contracts not referenced: {missing}"


def test_representation_schema_only():
    low = _read().lower()
    assert "representation schema only" in low


def test_mechanical_vs_market_content_distinction():
    low = _read().lower()
    assert "distinguish mechanical observation metadata from market-content observations" in low


def test_all_required_fields_present():
    low = _read().lower()
    missing = [f for f in REQUIRED_FIELDS if f not in low]
    assert not missing, f"required mechanical fields missing: {missing}"


def test_obs_facts_anchored():
    low = _read().lower()
    missing = [t for t in OBS_FACT_TOKENS if t not in low]
    assert not missing, f"obs facts missing: {missing}"


def test_obs3_no_eligible_is_not_a_cost():
    low = _read().lower()
    assert "not a cost, not zero cost, not opportunity cost, not idle cost, and not profitability evidence" in low


def test_missing_provenance_blocks():
    low = _read().lower()
    assert "blocked_needs_evidence" in low
    assert "missing provenance" in low


def test_no_assumed_or_guessed_cost_authorized():
    low = _read().lower()
    assert "must not authorize fixed cost, default cost, floor cost, baseline overhead, assumed request cost, or guessed mapping" in low


def test_no_conversion_into_money_or_edge():
    low = _read().lower()
    assert "must not convert request counts into dollars, bps, edge, net-edge, profitability, or readiness" in low


def test_future_mapping_requires_separate_authorization():
    low = _read().lower()
    assert "requires a separate explicitly authorized tdd/offline task with evidence provenance" in low


def test_no_live_execution_connection():
    low = _read().lower()
    assert "no live order" in low
    assert "no execution connection" in low


def test_slice_framing_not_final():
    low = _read().lower()
    assert "closes only the observation/discovery cost schema slice" in low
    assert "remaining phase 5 gaps still require separate authorization" in low


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
