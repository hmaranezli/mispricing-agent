"""tests/test_phase5_net_edge_calculator_boundary_implementation_planning.py — pins the
implementation-planning artifact for the future `phase5_net_edge_calculator_boundary` component
(docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation; pins the future result carrier
`NetEdgeCalculationResult`, the future function `calculate_net_edge` and its shape
`calculate_net_edge(*, calculation_input)`, and the optional stateless wrapper `NetEdgeCalculator`;
pins the calculator role (deterministic algebra over an input that already passed
`net_edge_input_preflight`, not a gate/parser/adapter/unit-converter/FX-oracle/profitability/
readiness/actionability/trading/paper-live component); pins the exact input contract and the
wrong-type/misroute taxonomy; allows local Decimal arithmetic from canonical decimal strings only and
forbids float/NaN/Infinity; pins the formula `net_edge = gross_edge - sum(cost_i)` with signed
cost/rebate algebra, zero-cost retention/counting, and negative/zero/positive results all being
successful (non-actionable) calculated results; pins the exact dimensional-compatibility policy and
case-sensitive proportional vocabulary; pins the blocked reason vocabulary and that NoEligible is
never returned by the calculator; pins the deferred decisions; states no runtime edit and no central
handoff/memory edit; restates the future-implementation gate; carries the standard no-claims block;
and asserts no forbidden over-claim wording appears anywhere while forbidden positive-claim phrases
appear only inside the explicit framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_net_edge_calculator_boundary_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

RESULT_FIELDS = [
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "gross_edge_value",
    "gross_edge_unit",
    "total_cost_value",
    "total_cost_unit",
    "net_edge_value",
    "net_edge_unit",
    "cost_component_count",
    "source_contract",
    "source_artifact",
    "source_field",
    "calculation_method",
    "boundary_version",
]

BANNED_RESULT_NAMES = [
    "NetEdgeObservation", "ActionableCandidate", "TradeCandidate", "Signal",
    "Opportunity", "ReadyCandidate", "ExecutableCandidate", "Payload",
]

PROPORTIONAL_UNITS = ["BPS", "BASIS_POINTS", "RATE", "PERCENT", "PERCENTAGE"]

REASON_VOCAB = [
    "NET_EDGE_CALCULATOR_BLOCKED_MISSING_NOTIONAL_FOR_PROPORTIONAL_COST",
    "NET_EDGE_CALCULATOR_BLOCKED_MISSING_CONVERSION_BASIS_FOR_ABSOLUTE_COST",
    "NET_EDGE_CALCULATOR_BLOCKED_MIXED_PROPORTIONAL_UNITS",
    "NET_EDGE_CALCULATOR_BLOCKED_INCOMPATIBLE_ABSOLUTE_UNITS",
    "NET_EDGE_CALCULATOR_BLOCKED_UNSUPPORTED_UNIT_VOCABULARY",
    "NET_EDGE_CALCULATOR_CONTRACT_VIOLATION_MALFORMED_INPUT_STATE",
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
    "source is trusted", "data is valid",
]


def _read():
    assert os.path.isfile(DOC), f"net-edge calculator planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "planning doc is empty"


def test_component_name_present():
    assert "phase5_net_edge_calculator_boundary" in _read()


def test_future_names_and_function_shape_pinned():
    text = _read()
    low = text.lower()
    assert "NetEdgeCalculationResult" in text
    assert "NetEdgeCalculator" in text
    assert "calculate_net_edge" in low
    assert "calculate_net_edge(*, calculation_input)" in low
    assert "this planning task must not implement" in low


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_calculator_role():
    low = _read().lower()
    assert "it is a deterministic algebra/calculation boundary" in low
    assert "it consumes only exact prenetedgecalculationinput that has already passed the future net_edge_input_preflight gate" in low
    assert "it is not a gate/preflight" in low
    assert "it is not a parser" in low
    assert "it is not an adapter" in low
    assert "it is not a unit converter" in low
    assert "it is not a cost-applicability policy" in low
    assert "it is not an fx/oracle" in low
    assert "it is not a profitability gate" in low
    assert "it is not a readiness gate" in low
    assert "it is not an actionability gate" in low
    assert "it is not a paper/live/trading/reporting/execution component" in low
    assert "it must not decide whether to trade" in low
    assert "it must not return noeligiblehaltpacket" in low
    assert "it must not produce order size, allocation, execution instruction, readiness, profitability verdict, or paper/live authority" in low


def test_input_contract():
    low = _read().lower()
    assert "future calculate_net_edge accepts exact type(calculation_input) is prenetedgecalculationinput" in low
    assert "subclasses rejected" in low
    assert "raw dict/mapping/json-like object/duck-typed object rejected" in low
    assert "exact blockedpacket / exact noeligiblehaltpacket received at this boundary is a misroute and must be rejected as a programmatic routing bug" in low
    assert "wrong type/misroute is typeerror / misroutedhaltcarriererror, never blockedpacket or noeligiblehaltpacket" in low


def test_output_contract():
    text = _read()
    low = text.lower()
    assert "future success output is netedgecalculationresult" in low
    assert "netedgecalculationresult is a calculated result, not an observation" in low
    for banned in BANNED_RESULT_NAMES:
        assert "must not be named {}".format(banned).lower() in low or banned in text
    assert "it is not actionable" in low
    assert "it proves no profitability, no readiness, no safety, no source truth, no paper/live readiness" in low
    assert "negative, zero, and positive net values are all successful calculated results if dimensionally valid" in low
    assert "negative net edge is not a failure" in low
    assert "zero net edge is not a failure" in low
    assert "positive net edge is not actionable" in low


def test_result_fields_pinned():
    low = _read().lower()
    for field in RESULT_FIELDS:
        assert field in low, f"result field missing: {field}"


def test_result_field_discipline():
    low = _read().lower()
    assert "all result fields must be exact str in future implementation" in low
    assert "decimal outputs must be canonical decimal strings with no exponent notation" in low
    assert "no float" in low
    assert "no nan" in low
    assert "no infinity" in low
    assert "no none" in low
    assert "cost_component_count must be exact unsigned integer string" in low
    assert "result must be frozen, repr-safe, anti-truthiness, anti-coercion, and constructed only by the calculator/factory in future implementation" in low


def test_core_algebra_pinned():
    low = _read().lower()
    assert "net_edge = gross_edge - sum(cost_i)" in low
    assert "positive cost reduces net edge" in low
    assert "negative cost/rebate increases net edge via subtraction of a negative value" in low
    assert "zero cost is valid if carried by observablecostobservation zero-cost evidence" in low
    assert "calculator must not discard zero costs" in low
    assert "calculator must preserve cost_component_count including zero-cost components" in low
    assert "calculator must not mutate the input or any carrier" in low
    assert "calculator must not sort, deduplicate, filter, or reinterpret cost contexts" in low
    assert "cost tuple order must be traversed only to accumulate algebraic total cost in future implementation" in low


def test_decimal_discipline_pinned():
    low = _read().lower()
    assert "calculator v1 may use decimal locally for arithmetic" in low
    assert "decimal must be constructed only from already-canonical decimal strings" in low
    assert "no float construction" in low
    assert "no decimal from float" in low
    assert "no float arithmetic" in low
    assert "no binary floating point" in low
    assert "no rounding unless a future explicitly planned precision policy exists" in low
    assert "no quantize policy in v1 unless separately authorized" in low
    assert "no exponent notation" in low
    assert "no leading plus" in low
    assert "minus preserved for negative results" in low
    assert "zero canonicalization must be planned explicitly" in low
    assert "do not normalize values in a way that changes economic meaning" in low


def test_dimensional_compatibility_policy_pinned():
    text = _read()
    low = text.lower()
    assert "calculator v1 only computes when gross and all costs are dimensionally compatible without inference" in low
    assert "cost.unit == gross.gross_edge_unit" in low
    assert "if gross_edge_unit and all cost units are the same exact proportional unit, calculator may compute in that proportional unit" in low
    for unit in PROPORTIONAL_UNITS:
        assert unit in text, f"proportional unit token missing (exact uppercase): {unit}"
    assert "no case normalization" in low
    assert "no .upper(), .lower(), .casefold(), alias mapping, or spelling repair" in low
    assert "mixed proportional units are not compatible unless an explicit future policy exists" in low
    assert "do not convert 100 bps to 1 percent" in low
    assert "absolute gross unit with proportional cost unit requires explicit notional/reference-price evidence, which current prenetedgecalculationinput does not carry" in low
    assert "proportional gross unit with absolute cost unit requires explicit conversion basis, which current input does not carry" in low
    assert "different absolute units are incompatible" in low
    assert "unsupported/mixed units must block, not infer" in low


def test_blocked_conditions_pinned():
    low = _read().lower()
    assert "future calculator must return blockedpacket, not exception, for exact valid calculation_input with" in low
    assert "proportional cost against absolute gross unit without explicit notional/reference-price evidence" in low
    assert "absolute cost against proportional gross unit without explicit conversion basis" in low
    assert "mixed proportional units" in low
    assert "different absolute units" in low
    assert "unsupported unit vocabulary" in low
    assert "malformed exact carrier state discovered during calculation" in low
    assert "any dimensional incompatibility that prevents algebra" in low


def test_reason_vocabulary_pinned():
    text = _read()
    for token in REASON_VOCAB:
        assert token in text, f"reason vocabulary token missing: {token}"


def test_no_noeligible_pinned():
    low = _read().lower()
    assert "calculator v1 must never return noeligiblehaltpacket" in low
    assert "unprofitable, negative, zero, or positive results are all mathematical outputs, not no-eligible states" in low
    assert "market staleness and eligibility are upstream/downstream gates, not calculator behavior" in low
    assert "profitability filtering is deferred to a future profitabilitygate / readinessgate, not this calculator" in low


def test_no_actionability_pinned():
    low = _read().lower()
    assert "netedgecalculationresult must not contain actionable, eligible, ready, executable, trade, order, allocation, paper_live, live, or readiness fields" in low
    assert "positive net_edge_value must not imply readiness" in low
    assert "no order-size calculation" in low
    assert "no balance/capital check" in low
    assert "no slippage/model update" in low
    assert "no source-truth claim" in low
    assert "no paper/live readiness claim" in low


def test_source_provenance_policy_pinned():
    low = _read().lower()
    assert "result must carry calculation provenance fields" in low
    assert "it must not claim source truth or data quality" in low
    assert "it must not parse source_artifact/source_field to infer missing values" in low
    assert "it must not fabricate missing notional/reference price" in low
    assert "it must not invent applicability fields" in low


def test_deferred_decisions_pinned():
    low = _read().lower()
    for token in [
        "notional/reference-price carrier or policy",
        "costapplicabilitycontext",
        "unit conversion policy",
        "precision/rounding/quantization policy",
        "proportional-to-absolute conversion",
        "mixed proportional unit conversion",
        "profit threshold policy",
        "readiness/actionability gate",
        "paper/live connection",
        "performance benchmark/microbenchmark",
    ]:
        assert token in low, f"deferred decision missing: {token}"


def test_failure_taxonomy_pinned():
    low = _read().lower()
    assert "programmatic wrong-path / wrong-type" in low
    assert "exact input but dimensional/evidence failure" in low
    assert "exact input and dimensionally compatible" in low
    assert "regardless of negative/zero/positive net edge" in low
    assert "never returned by calculator v1" in low


def test_no_runtime_and_no_central_handoff_edit():
    low = _read().lower()
    assert "this task makes no phase5 runtime code edits" in low
    assert "this task does not edit the central handoff/memory file and performs no memory closeout" in low


def test_future_implementation_gate():
    low = _read().lower()
    assert "future implementation must be separately authorized, component-scoped, offline, tdd-first, and declared-provenance" in low
    assert "this planning artifact does not authorize implementation" in low


def test_no_claims_block_present():
    low = _read().lower()
    assert NO_CLAIMS_START.lower() in low and NO_CLAIMS_END.lower() in low
    for term in ["no edge", "no net-edge", "no pnl", "no profitability",
                 "no paper readiness", "no live readiness", "no execution readiness",
                 "no safety guarantee", "no data-quality guarantee", "no source-truth guarantee"]:
        assert term in low, f"no-claims term missing: {term}"


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
