"""tests/test_phase5_offline_fixture_contract.py — pins the Phase 5 offline fixture contract
document (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data, builds no calculator/parser/loader/
fixture engine/generator/factory. Asserts the contract scopes offline fixtures to synthetic
diagnostic examples only, bars fixture presence from being treated as truth/quality/readiness/
economic validity, enforces static read-only constants discipline (no dynamic construction /
generator / factory / mutation / randomization / timestamp-now / env / network dependence), names the
six required fixture cases with their per-case fail-closed invariants, preserves the input-schema
categories / observed-derived-blocked vocabulary / provenance requirements, forbids downgrading
blocked, bars forbidden claims from fixture expected outputs, references the eight dependent
contracts, carries the standard no-claims block, avoids final/complete/ready and absolute-risk
framing, and lists the required Open Backlog / Deferred Decisions items — while asserting no forbidden
over-claim wording appears anywhere and forbidden positive-claim phrases appear only inside the
explicit framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase5_offline_fixture_contract.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

FIXTURE_CASES = [
    "eligible_minimal_fixture",
    "no_eligible_fixture",
    "blocked_missing_provenance_fixture",
    "blocked_unresolved_friction_placeholder_fixture",
    "malformed_or_unknown_field_fixture",
    "forbidden_claim_reporting_fixture",
]

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

DEPENDENT_CONTRACTS = [
    "phase5_interface_contract.md",
    "phase5_friction_component_schema_contract.md",
    "phase5_no_eligible_handling_schema_contract.md",
    "phase5_artifact_provenance_contract.md",
    "phase5_fail_closed_blocked_state_contract.md",
    "phase5_observation_discovery_cost_schema_contract.md",
    "phase5_no_claims_reporting_schema_contract.md",
    "phase5_input_schema_refinement_contract.md",
]

STATIC_DISCIPLINE = [
    "no dynamic fixture construction",
    "no constructor/generator/factory invocation",
    "no runtime mutation",
    "no randomization",
    "no timestamp-now behavior",
    "no environment-dependent fixture content",
    "no network-dependent fixture content",
]

BACKLOG_ITEMS = [
    "exact fixture record serialization",
    "exact fixture_schema_version policy",
    "exact static constant location policy",
    "exact fixture case vocabulary",
    "exact fixture naming convention",
    "exact expected-output schema for blocked fixture cases",
    "exact rule for separating fixture constants from production inputs",
    "exact verifier integration for fixture contract invariants",
    "exact policy for adding future fixture cases",
    "exact fixture provenance placeholder policy",
    "exact synthetic timestamp policy",
    "exact no-random/no-network/no-env dependency policy",
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
    "final phase 5 contract", "last critical piece", "is complete", "is perfect",
    "is now safe", "fully complete", "the last piece",
]


def _read():
    assert os.path.isfile(DOC), f"offline fixture contract doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "offline fixture contract doc is empty"


def test_contract_planning_only_framing():
    low = _read().lower()
    assert "contract/planning artifact only" in low or "contract/planning only" in low
    assert "not implementation" in low


def test_dependent_contracts_referenced():
    text = _read()
    missing = [c for c in DEPENDENT_CONTRACTS if c not in text]
    assert not missing, f"dependent contracts not referenced: {missing}"


def test_synthetic_diagnostic_only():
    low = _read().lower()
    assert "synthetic diagnostic examples only" in low


def test_fixture_presence_not_truth():
    low = _read().lower()
    assert "fixture presence must not be treated as market truth, evidence quality, source truth, readiness, economic validity, profitability evidence, paper/live evidence, or net-edge input" in low


def test_boundary_invariants_only():
    low = _read().lower()
    assert "pin boundary-case invariants only" in low
    assert "do not prove schema validity, correctness, stationarity, or economic value" in low


def test_test_doc_scoped_not_production():
    low = _read().lower()
    assert "test/doc-contract scoped only" in low
    assert "must not be production inputs" in low


def test_fixture_source_prohibitions():
    low = _read().lower()
    assert "must not copy generated artifacts" in low
    assert "must not be derived from public-data fetches" in low
    assert "must not contain private auth, secrets, balances, orders, live clob data, or real trading data" in low
    assert "must not create or require runtime data/output artifacts" in low
    assert "must not authorize parser, loader, fixture engine, fixture factory, fixture generator, data-fetch, computation, or aggregation" in low


def test_static_constants_discipline():
    low = _read().lower()
    assert "static, read-only constants" in low
    missing = [d for d in STATIC_DISCIPLINE if d not in low]
    assert not missing, f"static discipline items missing: {missing}"


def test_tests_use_static_constants_only():
    low = _read().lower()
    assert "if tests need fixture examples, they must use static constants or doc-pinned examples, not generators/factories/loaders/parsers" in low


def test_implementing_engine_is_contract_violation():
    low = _read().lower()
    assert "out of scope" in low
    assert "must be treated as contract violation for this task" in low


def test_all_fixture_cases_present():
    low = _read().lower()
    missing = [c for c in FIXTURE_CASES if c not in low]
    assert not missing, f"fixture cases missing: {missing}"


def test_eligible_minimal_case_invariant():
    low = _read().lower()
    assert "minimal syntactic success shape only" in low
    assert "must not imply economic validity, readiness, profitability, execution, or net-edge" in low


def test_no_eligible_case_invariant():
    low = _read().lower()
    assert "must not become error, zero value, zero cost, opportunity cost, idle cost, profitability evidence, readiness signal, or net-edge input" in low


def test_blocked_missing_provenance_case_invariant():
    low = _read().lower()
    assert "blocked_needs_evidence" in low
    assert "blocked_missing_provenance_fixture" in low


def test_blocked_placeholder_case_invariant():
    low = _read().lower()
    assert "must not be 0, null, false, empty string, default, floor, baseline, assumed, guessed, or usable numeric values" in low
    assert "must not be treated as cost evidence, zero cost, usable friction value, net-edge input, economic inference, readiness evidence, or implementation authority" in low


def test_malformed_case_invariant():
    low = _read().lower()
    assert "must not be silently ignored, coerced, cast, defaulted, or treated as valid observed/derived input" in low


def test_forbidden_claim_case_invariant():
    low = _read().lower()
    assert "must represent forbidden claim wording as contract violation or blocked reporting behavior, not as valid output" in low


def test_fixture_expected_outputs_clean():
    low = _read().lower()
    assert "fixture expected outputs must not contain alpha, pnl, edge, profitability, readiness, paper/live readiness, execution authority, trading instruction, net-edge, economic inference, safety guarantee, data-quality guarantee, or data-integrity guarantee" in low


def test_input_categories_preserved():
    low = _read().lower()
    missing = [c for c in INPUT_CATEGORIES if c not in low]
    assert not missing, f"input categories missing: {missing}"


def test_vocabulary_and_provenance_preserved():
    low = _read().lower()
    assert "observed/derived/blocked" in low
    assert "blocked_needs_evidence semantics" in low
    assert "source_artifact/source_field provenance" in low


def test_blocked_not_downgraded():
    low = _read().lower()
    assert "must not downgrade blocked into zero, false, pass, observed, derived, eligible, executable, tradable, ready, profitable, or net-edge input" in low


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
