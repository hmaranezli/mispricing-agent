"""tests/test_phase5_friction_component_schema_contract.py — pins the Phase 5 friction-component
schema contract document (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data, builds no net-edge calculator.
Asserts the contract enumerates every required friction component placeholder, requires the full
per-component field set and the observed|derived|blocked status vocabulary, forbids binary-float
authority for money/edge math, fixes costs as non-negative deductions from gross edge, requires
provenance (source_artifact + source_field) and fails closed to BLOCKED_NEEDS_EVIDENCE (never zero)
on missing component/source/formula, forbids fixed/default/floor/guessed/baseline costs, keeps
aggregation contract-only (blocked unless every component is observed/derived with evidence), allows
uncertainty_buffer to remain blocked, declares no live execution connection, carries the standard
no-claims block, and lists the required Open Backlog / Deferred Decisions items — while asserting no
forbidden over-claim wording appears anywhere and forbidden positive-claim phrases appear only inside
the explicit framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase5_friction_component_schema_contract.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

REQUIRED_COMPONENTS = [
    "spread_cost",
    "fee_cost",
    "slippage_cost",
    "depth_cost",
    "discovery_cost",
    "latency_or_staleness_cost",
    "uncertainty_buffer",
]

REQUIRED_COMPONENT_FIELDS = [
    "name",
    "unit",
    "numeric_representation",
    "sign_convention",
    "source_artifact",
    "source_field",
    "deterministic_formula_or_blocked_reason",
    "status",
]

STATUS_VOCAB = ["observed", "derived", "blocked"]

BACKLOG_ITEMS = [
    "exact deterministic formula for uncertainty_buffer",
    "exact units/scaling for final implementation",
    "evidence source for fee_cost",
    "evidence source for slippage_cost",
    "evidence source for depth_cost",
    "aggregation implementation is deferred",
    "production/live usage is blocked until separate authorization",
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
    "net edge is positive", "edge is confirmed",
]


def _read():
    assert os.path.isfile(DOC), f"friction-component contract doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "friction-component contract doc is empty"


def test_interface_contract_reference_present():
    text = _read()
    assert "phase5_interface_contract.md" in text
    assert "phase5_planning_gate.md" in text


def test_observation_and_planning_only():
    low = _read().lower()
    assert "observation and planning only" in low


def test_all_required_components_present():
    low = _read().lower()
    missing = [c for c in REQUIRED_COMPONENTS if c not in low]
    assert not missing, f"required friction components missing: {missing}"


def test_all_required_component_fields_present():
    low = _read().lower()
    missing = [f for f in REQUIRED_COMPONENT_FIELDS if f not in low]
    assert not missing, f"required per-component fields missing: {missing}"


def test_status_vocabulary_present():
    low = _read().lower()
    missing = [s for s in STATUS_VOCAB if s not in low]
    assert not missing, f"status vocabulary missing: {missing}"
    assert "observed | derived | blocked" in low


def test_numeric_representation_forbids_binary_float():
    low = _read().lower()
    assert "binary floating-point" in low
    assert "decimal" in low
    assert "integer-scaled" in low


def test_sign_convention_non_negative_deduction():
    low = _read().lower()
    assert "non-negative deduction" in low
    assert "gross edge" in low


def test_provenance_required_blocks_when_missing():
    low = _read().lower()
    assert "missing provenance" in low
    assert "blocked_needs_evidence" in low


def test_fail_closed_never_zero():
    low = _read().lower()
    assert "never zero" in low
    assert "fail closed" in low or "fail-closed" in low


def test_no_fixed_default_floor_or_guessed_cost():
    low = _read().lower()
    for term in ["fixed cost", "default cost", "floor cost", "guessed constant", "baseline overhead"]:
        assert term in low, f"missing cost-disclaimer term: {term}"
    assert "is authorized" in low


def test_aggregation_contract_only_and_blocked_without_evidence():
    low = _read().lower()
    assert "no net-edge aggregation may proceed unless every required component is observed or derived with evidence" in low


def test_uncertainty_buffer_may_remain_blocked():
    low = _read().lower()
    assert "uncertainty_buffer" in low
    assert "may remain blocked" in low


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
    block = low
    assert NO_CLAIMS_START.lower() in block and NO_CLAIMS_END.lower() in block
    for term in ["no edge", "no pnl", "no profitability", "no alpha",
                 "no live readiness", "no paper readiness", "no economics readiness"]:
        assert term in block, f"no-claims term missing: {term}"


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
