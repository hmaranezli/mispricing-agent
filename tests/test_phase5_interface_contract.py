"""tests/test_phase5_interface_contract.py — pins the Phase 5 offline interface-contract
document (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data. Asserts the interface-contract doc
defines each required schema/section, frames itself as offline interface-contract only (no
implementation authorized, no guarantee of correctness, not a mathematical proof), keeps no-eligible
and observation/discovery cost economically unclaimed, and confines forbidden
readiness/profitability/edge claims to the explicit no-claims / prohibited-output sections — while
asserting none of the forbidden over-claim wordings appear anywhere.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase5_interface_contract.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

SECTION_HEADERS = [
    "Gross-edge input schema",
    "Friction component schema",
    "No-eligible handling schema",
    "Observation/discovery cost schema",
    "Artifact provenance schema",
    "Reporting / no-claims schema",
    "Fail-closed behavior contract",
    "Offline fixture requirements",
    "Forbidden outputs",
    "Next allowed step",
]

FRAMING_STATEMENTS = [
    "is not a mathematical proof",
    "does not guarantee correctness",
    "defines testable interface expectations",
    "reduces ambiguity before implementation",
    "makes schema drift easier to detect",
    "economic treatment remains unclaimed",
    "future implementation must be separately authorized and tdd/offline first",
]

# Positive claim phrases that must NEVER appear outside framing / no-claims / prohibited-output blocks.
FORBIDDEN_CLAIM_PHRASES = [
    "ready-to-fly", "ready to fly", "system-ready", "system ready",
    "is ready", "are ready", "production ready", "paper ready",
    "execution ready", "live ready", "economics ready", "ready for live",
    "is profitable", "profit confirmed", "profitable strategy",
    "edge confirmed", "positive edge", "tradeable edge", "alpha confirmed",
]

# Over-claim wordings that must NOT appear anywhere (case-insensitive). Chosen so they do not
# collide with required negated phrasings (e.g. "is not a mathematical proof",
# "does not guarantee correctness", "no floor cost ... is authorized").
FORBIDDEN_WORDING = [
    "technical debt is eliminated", "risk is zero", "reduced by",
    "guarantees correctness", "proves determinism", "is a mathematical proof",
    "merely mechanical", "validates the model", "is now justified",
    "begin automatically", "correctness is guaranteed", "system stability is proven",
    "mechanical efficiency",
]


def _read():
    assert os.path.isfile(DOC), f"interface-contract doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    if start in text and end in text:
        s = text.index(start)
        e = text.index(end) + len(end)
        return text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "interface-contract doc is empty"


def test_planning_gate_reference_present():
    assert "phase5_planning_gate.md" in _read()


def test_required_section_headers_present():
    text = _read()
    missing = [h for h in SECTION_HEADERS if h not in text]
    assert not missing, f"section headers missing: {missing}"


def test_offline_interface_contract_only():
    low = _read().lower()
    assert "offline" in low
    assert "interface-contract only" in low or "interface contract only" in low


def test_no_implementation_authorized():
    low = _read().lower()
    assert "no implementation is authorized" in low or "does not authorize implementation" in low


def test_future_implementation_separately_authorized():
    low = _read().lower()
    assert "future implementation must be separately authorized and tdd/offline first" in low


def test_framing_statements_present():
    low = _read().lower()
    missing = [s for s in FRAMING_STATEMENTS if s not in low]
    assert not missing, f"framing statements missing: {missing}"


def test_no_eligible_economic_treatment_unclaimed():
    low = _read().lower()
    assert "no-eligible" in low or "no eligible" in low
    assert "economic treatment remains unclaimed" in low


def test_no_fixed_or_floor_cost_authorized():
    low = _read().lower()
    for term in ["fixed cost", "floor cost", "baseline overhead"]:
        assert term in low, f"missing cost-disclaimer term: {term}"
    assert "is authorized here" in low or "authorized here" in low


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
    assert "git add ." not in text, "must not reference 'git add .'"
