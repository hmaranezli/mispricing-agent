"""tests/test_phase5_planning_gate.py — pins the Phase 5 Planning-Only Protocol / Design Gate
(docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data. Asserts the planning-gate doc
defines scope, allowed/prohibited inputs, planning questions, required future contracts, prohibited
and allowed outputs, and the epistemic framing — while making NO readiness/profitability/edge claim
outside the explicit no-claims / prohibited-output sections, and asserting none of the forbidden
over-claims (floor cost, mechanical efficiency proven, architectural debt eliminated, guaranteed
correctness, automatic implementation) appear anywhere.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase5_planning_gate.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

SECTION_HEADERS = [
    "Allowed inputs",
    "Prohibited inputs",
    "Phase 5 planning questions",
    "Required future contracts",
    "Prohibited outputs",
    "Allowed outputs",
]

REQUIRED_CONTRACTS = [
    "input schema contract",
    "friction component schema contract",
    "no-eligible handling contract",
    "observation/discovery cost contract",
    "artifact provenance contract",
    "no-claims/reporting contract",
    "offline fixture contract",
    "fail-closed behavior contract",
]

OBSERVATION_MARKERS = [
    "12/12/12",          # request_count
    "4/4/4",             # discovery_requests
    "8/8/8",             # book_requests
    "eligible_pairs 4",
    "eligible_pairs 0",
]

# Positive claim phrases that must NEVER appear outside framing / no-claims / prohibited-output blocks.
FORBIDDEN_CLAIM_PHRASES = [
    "ready-to-fly", "ready to fly", "system-ready", "system ready",
    "is ready", "are ready", "production ready", "paper ready",
    "execution ready", "live ready", "economics ready", "ready for live",
    "is profitable", "profit confirmed", "profitable strategy",
    "edge confirmed", "positive edge", "tradeable edge", "alpha confirmed",
]

# Over-claim wordings that must NOT appear anywhere in the doc (case-insensitive).
FORBIDDEN_WORDING = [
    "most valuable data", "floor cost", "cost floor", "mechanical efficiency",
    "execution determinism is proven", "mechanical determinism is certified",
    "system stability is proven", "system health is certified", "calibration certificate",
    "phase 5 is now justified", "phase 5 can now begin automatically",
    "phase 5 correctness is guaranteed", "correctness is guaranteed",
    "architectural debt is eliminated", "merely execute", "begin automatically",
    "cost model reliability is determined", "low-variance model is established",
    "three runs prove stability", "three runs prove drift",
    "prove market-dependent behavior", "prove mechanical instability",
]


def _read():
    assert os.path.isfile(DOC), f"planning-gate doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    if start in text and end in text:
        s = text.index(start)
        e = text.index(end) + len(end)
        return text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "planning-gate doc is empty"


def test_planning_only_status_present():
    low = _read().lower()
    assert "planning only" in low, "missing planning-only status"


def test_no_implementation_authorized_present():
    low = _read().lower()
    assert "no implementation authorized" in low


def test_phase4c_observations_summary_present():
    text = _read()
    missing = [m for m in OBSERVATION_MARKERS if m not in text]
    assert not missing, f"observation summary markers missing: {missing}"


def test_obs3_no_eligible_operator_attention_signal_present():
    low = _read().lower()
    assert "no-eligible" in low or "no eligible" in low, "missing no-eligible reference"
    assert "operator-attention signal" in low or "operator attention signal" in low


def test_observation_discovery_cost_planning_input_present():
    low = _read().lower()
    assert "observation/discovery cost" in low, "missing observation/discovery cost planning input"


def test_section_headers_present():
    text = _read()
    missing = [h for h in SECTION_HEADERS if h not in text]
    assert not missing, f"section headers missing: {missing}"


def test_required_future_contracts_present():
    text = _read()
    missing = [c for c in REQUIRED_CONTRACTS if c not in text]
    assert not missing, f"required contracts missing: {missing}"


def test_no_readiness_profitability_edge_framing_present():
    text = _read()
    assert NO_CLAIMS_START in text and NO_CLAIMS_END in text
    block = text[text.index(NO_CLAIMS_START):text.index(NO_CLAIMS_END)].lower()
    for term in ["readiness", "profitability", "edge"]:
        assert term in block, f"no-claims framing missing term: {term}"


def test_does_not_authorize_phase5():
    low = _read().lower()
    assert ("does not authorize phase 5 implementation, trading, paper deployment, "
            "or readiness claims") in low, "missing Phase 5 non-authorization statement"


def test_obs3_does_not_prove_stability_etc():
    low = _read().lower()
    assert "does not prove stability, determinism, stationarity, or economic value" in low


def test_no_eligible_is_planning_input_not_economic_inference():
    low = _read().lower()
    assert "planning input" in low
    assert "not an economic inference" in low


def test_reduces_ambiguity_not_guarantee():
    low = _read().lower()
    assert "reduces ambiguity" in low or "reduce ambiguity" in low
    assert "does not guarantee" in low, "must state planning does not guarantee outcomes"


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
