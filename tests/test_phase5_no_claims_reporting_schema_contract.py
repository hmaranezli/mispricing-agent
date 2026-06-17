"""tests/test_phase5_no_claims_reporting_schema_contract.py — pins the Phase 5 no-claims/reporting
schema contract document (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data, builds no calculator/parser/loader.
Asserts the contract defines reporting as an output-vocabulary boundary only (it authorizes no
computation/aggregation/execution/trading/readiness), restricts reporting states to observed /
derived / blocked with BLOCKED_NEEDS_EVIDENCE canonical, requires the full reporting-record field
set, forbids blocked reports from emitting derived/fallback/zero/guessed values, forbids converting
states into economic/readiness/execution/net-edge/guarantee claims, requires the no-claims block and
contract-planning framing on every report, bars human review from converting blocked into
observed/derived, fails closed on missing no-claims/provenance/unknown source/forbidden wording,
references the six dependent contracts, carries the standard no-claims block, avoids
final/complete/ready framing, and lists the required Open Backlog / Deferred Decisions items — while
asserting no forbidden over-claim wording appears anywhere and forbidden positive-claim phrases
appear only inside the explicit framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase5_no_claims_reporting_schema_contract.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

REQUIRED_FIELDS = [
    "report_schema_version",
    "report_scope",
    "report_status",
    "source_contract",
    "source_artifact_or_blocked_reason",
    "source_field_or_blocked_reason",
    "provenance_status",
    "observed_or_derived_value_or_blocked_reason",
    "blocked_reason_if_any",
    "deterministic_next_action_if_blocked",
    "no_claims_block_present",
    "created_utc_timestamp_ms_or_blocked_reason",
]

ALLOWED_STATES = ["observed", "derived", "blocked"]

DEPENDENT_CONTRACTS = [
    "phase5_interface_contract.md",
    "phase5_friction_component_schema_contract.md",
    "phase5_no_eligible_handling_schema_contract.md",
    "phase5_artifact_provenance_contract.md",
    "phase5_fail_closed_blocked_state_contract.md",
    "phase5_observation_discovery_cost_schema_contract.md",
]

BACKLOG_ITEMS = [
    "exact report record serialization",
    "exact report_schema_version policy",
    "exact source_contract vocabulary",
    "exact allowed human-readable summary template",
    "exact verifier integration for forbidden reporting claims",
    "exact blocked-report rendering policy",
    "exact aggregation/report composition policy if multiple records include mixed observed/derived/blocked states",
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
# Chosen so they do not collide with required negations or with the prohibited-claims list.
FORBIDDEN_WORDING = [
    "eliminates all risk", "zero risk", "tamper-proof", "verified truth",
    "clean data", "trusted data", "is immutable", "guarantees correctness",
    "is impossible", "cannot happen", "final phase 5 contract", "last critical piece",
    "is complete", "is perfect", "is now safe", "fully complete", "the last piece",
]


def _read():
    assert os.path.isfile(DOC), f"no-claims/reporting contract doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "no-claims/reporting contract doc is empty"


def test_contract_planning_only_framing():
    low = _read().lower()
    assert "contract/planning artifact only" in low or "contract/planning only" in low
    assert "not implementation" in low


def test_dependent_contracts_referenced():
    text = _read()
    missing = [c for c in DEPENDENT_CONTRACTS if c not in text]
    assert not missing, f"dependent contracts not referenced: {missing}"


def test_output_vocabulary_only():
    low = _read().lower()
    assert "output-vocabulary only" in low
    assert "does not authorize computation, aggregation, execution, trading, or readiness" in low


def test_allowed_states_and_canonical_blocked():
    low = _read().lower()
    for s in ALLOWED_STATES:
        assert s in low, f"allowed state missing: {s}"
    assert "blocked_needs_evidence as the canonical blocked status" in low


def test_all_required_fields_present():
    low = _read().lower()
    missing = [f for f in REQUIRED_FIELDS if f not in low]
    assert not missing, f"required reporting fields missing: {missing}"


def test_blocked_report_emits_no_synthetic_values():
    low = _read().lower()
    assert "must not output derived estimates, fallback values, zero values, or guessed values" in low


def test_no_conversion_into_unauthorized_claims():
    low = _read().lower()
    assert "must not convert observed/derived/blocked states into alpha, pnl, edge, profitability, readiness, paper readiness, live readiness, execution authority, trading instruction, net-edge, economic inference, safety guarantee, data-quality guarantee, or data-integrity guarantee" in low


def test_reports_may_state_only_evidence_backed():
    low = _read().lower()
    assert "may state only evidence-backed observations, derived values with explicit source chain, or blocked status with blocked reason" in low


def test_every_report_carries_no_claims_and_framing():
    low = _read().lower()
    assert "every future phase 5 report must carry the no-claims block" in low
    assert "contract-planning framing" in low


def test_human_review_cannot_convert_blocked():
    low = _read().lower()
    assert "human review must not convert blocked evidence into observed or derived reporting" in low


def test_fail_closed_on_missing_or_forbidden():
    low = _read().lower()
    assert "must fail closed" in low
    assert "blocked_needs_evidence" in low
    assert "unknown source contract" in low
    assert "forbidden claim wording" in low


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
