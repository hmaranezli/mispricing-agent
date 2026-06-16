"""tests/test_council_inventory_derisk_gate.py — pins the Council Inventory and LLM Decision
De-Risk audit gate doc (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data, removes/refactors no council code.
Asserts the audit doc is inventory-only, enumerates the council inventory and decision-authority
classification, states the LLM/council red lines, the allowed future role, a single de-risk
recommendation token, and a future removal/bypass gate — while confining forbidden
readiness/profitability/edge claims to the explicit red-line / no-claims sections and asserting none
of the forbidden over-claim wordings appear anywhere.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "council_inventory_derisk_gate.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
REDLINES_START = "<!-- RED-LINES-START -->"
REDLINES_END = "<!-- RED-LINES-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"

SECTION_HEADERS = [
    "Current status",
    "Council inventory",
    "Decision-authority classification",
    "Required red lines",
    "Allowed future role",
    "De-risk recommendation",
    "Future removal/bypass gate",
]

RED_LINE_STATEMENTS = [
    "cannot approve trades",
    "cannot approve edge",
    "cannot create order intent",
    "cannot override",          # deterministic risk
    "cannot authorize paper/live readiness",
    "cannot authorize Phase 5 implementation",
]

RECOMMENDATION_TOKENS = [
    "NO_ACTION_READ_ONLY_ONLY",
    "FOLLOW_UP_REMOVE_OR_BYPASS",
    "BLOCKED_NEEDS_EVIDENCE",
]

# Positive over-claim phrases that must NEVER appear outside framing / red-lines / no-claims blocks.
FORBIDDEN_CLAIM_PHRASES = [
    "ready-to-fly", "ready to fly", "system-ready", "system ready",
    "is ready", "are ready", "production ready", "paper ready",
    "execution ready", "live ready", "economics ready", "ready for live",
    "is profitable", "profit confirmed", "profitable strategy",
    "edge confirmed", "positive edge", "tradeable edge", "alpha confirmed",
]

# Over-claim wordings that must NOT appear anywhere (case-insensitive).
FORBIDDEN_WORDING = [
    "100% safety", "verifier becomes the system authority",
    "control is fully handed to the verifier", "fully autonomous", "fully deterministic",
    "must be removed before evidence", "council existence alone is a failure",
    "read-only usage is dangerous", "docs-only usage is dangerous",
    "proves there is no llm risk", "guarantees phase 5 safety",
    "authorizes phase 5 implementation",
]


def _read():
    assert os.path.isfile(DOC), f"audit doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "audit doc is empty"


def test_inventory_only():
    low = _read().lower()
    assert "inventory" in low and "audit only" in low


def test_no_code_removal_authorized():
    low = _read().lower()
    assert "no code removal" in low


def test_no_phase5_implementation_authorized():
    low = _read().lower()
    assert "no phase 5 implementation" in low


def test_required_section_headers_present():
    text = _read()
    missing = [h for h in SECTION_HEADERS if h not in text]
    assert not missing, f"section headers missing: {missing}"


def test_red_line_statements_present():
    text = _read()
    missing = [s for s in RED_LINE_STATEMENTS if s not in text]
    assert not missing, f"red-line statements missing: {missing}"


def test_recommendation_token_present():
    text = _read()
    present = [t for t in RECOMMENDATION_TOKENS if t in text]
    assert present, "no de-risk recommendation token present"


def test_allowed_future_role_constrained():
    low = _read().lower()
    assert "read-only report summarizer" in low
    assert "outside" in low and ("deterministic" in low)


def test_future_removal_bypass_gate_present():
    low = _read().lower()
    assert "remove-or-bypass" in low or "removal/bypass" in low or "remove or bypass" in low


def test_no_forbidden_overclaim_wording_anywhere():
    low = _read().lower()
    hits = [w for w in FORBIDDEN_WORDING if w in low]
    assert not hits, f"forbidden over-claim wording present: {hits}"


def test_forbidden_claims_only_in_redline_or_noclaims():
    text = _read()
    body = _strip(text, FRAMING_START, FRAMING_END)
    body = _strip(body, REDLINES_START, REDLINES_END)
    body = _strip(body, NO_CLAIMS_START, NO_CLAIMS_END).lower()
    hits = [p for p in FORBIDDEN_CLAIM_PHRASES if p in body]
    assert not hits, f"forbidden positive claim(s) outside allowed sections: {hits}"


def test_generated_artifacts_not_referenced_as_tracked():
    text = _read()
    assert "git add ." not in text, "must not reference 'git add .'"
