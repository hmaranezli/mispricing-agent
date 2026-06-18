"""tests/test_phase5_net_edge_profitability_gate_implementation_planning.py — pins the
implementation-planning artifact for the future `phase5_net_edge_profitability_gate_boundary`
component (docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation; jointly designs two future components —
`ProfitabilityThresholdPolicyContext` (a frozen, factory-only, explicit-threshold carrier) and the
`NetEdgeProfitabilityGate` / `net_edge_profitability_preflight` pure threshold gate with shape
`net_edge_profitability_preflight(*, calculation_result, threshold_policy)`; pins the exact input
contract and wrong-type/misroute taxonomy; pins local Decimal-comparison-only arithmetic from
canonical strings (no float); pins the `net_edge_value >= threshold_value` rule (equality passes, no
sign morality); pins the case-sensitive exact unit-match policy; pins the Blocked-vs-NoEligible
taxonomy (missing/malformed/unit-mismatch policy evidence → BlockedPacket; valid-but-below-threshold
→ NoEligibleHaltPacket; at-or-above → input identity pass-through); pins the reason vocabulary; bars
venue/asset/instrument/source parsing, threshold defaults, clock checks, sizing/liquidity/paper-live
and any actionability/readiness claim; states no runtime edit and no central handoff/memory edit;
restates the future-implementation gate; carries the standard no-claims block; and asserts no
forbidden over-claim wording appears anywhere while forbidden positive-claim phrases appear only
inside the explicit framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_net_edge_profitability_gate_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

POLICY_FIELDS = [
    "component_name",
    "threshold_value",
    "threshold_unit",
    "source_contract",
    "source_artifact",
    "source_field",
    "policy_id",
    "boundary_version",
]

BANNED_RESULT_NAMES = [
    "ProfitabilityPassedResult", "ActionableCandidate", "TradeCandidate", "Signal",
    "Opportunity", "ReadyCandidate", "ExecutableCandidate", "Payload",
]

REASON_VOCAB = [
    "NET_EDGE_PROFITABILITY_GATE_BLOCKED_MISSING_THRESHOLD_POLICY",
    "NET_EDGE_PROFITABILITY_GATE_BLOCKED_MALFORMED_THRESHOLD_POLICY",
    "NET_EDGE_PROFITABILITY_GATE_BLOCKED_UNIT_MISMATCH",
    "NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD",
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
    assert os.path.isfile(DOC), f"net-edge profitability gate planning doc missing: {DOC}"
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
    assert "phase5_net_edge_profitability_gate_boundary" in _read()


def test_future_names_and_function_shape_pinned():
    text = _read()
    low = text.lower()
    assert "ProfitabilityThresholdPolicyContext" in text
    assert "make_profitability_threshold_policy_context" in low
    assert "NetEdgeProfitabilityGate" in text
    assert "net_edge_profitability_preflight" in low
    assert "net_edge_profitability_preflight(*, calculation_result, threshold_policy)" in low
    assert "this planning task must not implement" in low


def test_dual_component_design_pinned():
    low = _read().lower()
    assert "jointly design two future components" in low
    assert "profitabilitythresholdpolicycontext" in low
    assert "netedgeprofitabilitygate / net_edge_profitability_preflight" in low


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_gate_role():
    low = _read().lower()
    assert "it is a pure/offline/deterministic profitability threshold gate" in low
    assert "it consumes exact netedgecalculationresult plus exact profitabilitythresholdpolicycontext" in low
    assert "it is not a calculator" in low
    assert "it is not a parser" in low
    assert "it is not an adapter" in low
    assert "it is not a unit converter" in low
    assert "it is not an fx/oracle" in low
    assert "it is not a cost-applicability policy" in low
    assert "it is not a readiness gate" in low
    assert "it is not an actionability gate" in low
    assert "it is not a liquidity/depth/slippage/balance/margin/order-sizing/execution/trading/reporting/paper-live component" in low
    assert "it must not decide whether to trade" in low
    assert "it must not produce order size, allocation, readiness, actionability, paper/live authority, or execution instruction" in low


def test_policy_carrier_contract():
    text = _read()
    low = text.lower()
    assert "future carrier wraps only explicit threshold policy data needed by the gate" in low
    assert "it must be frozen, repr-safe, anti-truthiness, anti-coercion, factory-only" in low
    assert "it must not read env/config/files/db/network/time" in low
    assert "it must not compute or infer a threshold" in low
    assert "no hardcoded/default threshold" in low
    assert "no source_artifact parsing" in low
    for field in POLICY_FIELDS:
        assert field in low, f"policy field missing: {field}"
    assert "threshold_value must be a canonical signed decimal string in the future implementation" in low
    assert "threshold_unit must be exact non-empty str and case-sensitive" in low
    assert "negative, zero, and positive threshold values are all policy data; the gate must not impose sign morality" in low
    assert "if a non-negative threshold rule is ever desired, it is deferred to a future policy factory/governance layer, not this v1 gate" in low


def test_input_contract():
    low = _read().lower()
    assert "net_edge_profitability_preflight accepts exact type(calculation_result) is netedgecalculationresult" in low
    assert "subclasses rejected" in low
    assert "raw dict/mapping/json/duck-typed objects rejected" in low
    assert "exact blockedpacket or exact noeligiblehaltpacket received as calculation_result is a misroute and must be rejected as a programmatic routing bug" in low
    assert "threshold_policy must be exact profitabilitythresholdpolicycontext" in low
    assert "wrong type/misroute must be typeerror / misroutedhaltcarriererror, never a market packet" in low
    assert "missing/malformed exact policy evidence is blockedpacket, not noeligible" in low


def test_allowed_local_math():
    low = _read().lower()
    assert "decimal comparison only after canonical decimal string validation" in low
    assert "use decimal locally only from already-canonical strings" in low
    assert "no float, no decimal from float, no rounding, no quantize" in low
    assert "no net-edge recalculation" in low
    assert "no cost summing" in low
    assert "no mutation, copy, wrapping, transformation, sorting, filtering, or enrichment of calculation_result" in low
    assert "success returns the exact same calculation_result object identity" in low


def test_comparison_rule():
    low = _read().lower()
    assert "gate compares net_edge_value >= threshold_value" in low
    assert "equality passes" in low
    assert "no special sign logic" in low
    assert "no profitability score" in low
    assert "no ranking" in low
    assert "no statistical inference" in low


def test_unit_policy():
    low = _read().lower()
    assert "calculation_result.net_edge_unit must exactly equal threshold_policy.threshold_unit" in low
    assert "case-sensitive exact match only" in low
    assert "no .upper(), .lower(), .casefold(), alias mapping, spelling repair, normalization, conversion, fx/oracle, or proportional/absolute conversion" in low
    assert "unit mismatch is evidence failure -> blockedpacket" in low
    assert "do not inspect gross_edge_unit, total_cost_unit, or any upstream cost units for additional policy" in low
    assert "do not infer units from source fields" in low


def test_failure_taxonomy():
    low = _read().lower()
    assert "programmatic wrong-path / wrong-type" in low
    assert "typeerror / misroutedhaltcarriererror" in low
    assert "never blockedpacket or noeligiblehaltpacket" in low
    assert "exact result + missing/malformed/unsupported threshold evidence" in low
    assert "this means system blindness / missing policy evidence, not market unprofitability" in low
    assert "exact result + exact policy + unit match + net_edge_value < threshold_value" in low
    assert "noeligiblehaltpacket" in low
    assert "this means mathematically valid but below profitability threshold" in low
    assert "exact result + exact policy + unit match + net_edge_value >= threshold_value" in low
    assert "pass-through identity: return the exact same netedgecalculationresult object" in low
    assert "this is not actionable and not trade-ready" in low


def test_reason_vocabulary_pinned():
    text = _read()
    for token in REASON_VOCAB:
        assert token in text, f"reason vocabulary token missing: {token}"


def test_output_contract():
    text = _read()
    low = text.lower()
    assert "success must return input identity, not a new carrier" in low
    for banned in BANNED_RESULT_NAMES:
        assert banned in text, f"banned result name must be pinned as prohibited: {banned}"
    assert "no wrapper, no union carrier, no shared base hierarchy, no cross-conversion, no downgrade, no masking" in low
    assert "passing this gate means only" in low
    assert "passing this gate does not mean actionable, ready, executable, safe, paper-ready, live-ready, or trade-authorized" in low


def test_prohibited_v1_checks():
    low = _read().lower()
    for token in [
        "no venue/base/quote/instrument validation",
        "no source_artifact/source_field parsing",
        "no regex extraction from provenance",
        "no threshold defaults from env/config/file/db",
        "no clock/staleness/evaluation time checks",
        "no order sizing",
        "no balance/margin/capital checks",
        "no liquidity/depth/slippage checks",
        "no paper/live/trading/reporting/execution",
        "no profitability inference beyond the single decimal comparison",
    ]:
        assert token in low, f"prohibited-check line missing: {token}"


def test_deferred_decisions():
    low = _read().lower()
    for token in [
        "venue/asset/instrument applicability policy",
        "threshold governance/factory rules",
        "non-negative threshold policy",
        "strategy-specific threshold selection",
        "dynamic threshold model",
        "readiness/actionability gate",
        "liquidity/depth/slippage gate",
        "balance/capital gate",
        "paper/live execution",
        "performance benchmark/microbenchmark",
    ]:
        assert token in low, f"deferred decision missing: {token}"


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
    for term in ["no edge", "no pnl", "no alpha", "no actionability", "no readiness",
                 "no paper readiness", "no live readiness", "no execution readiness",
                 "no safety guarantee", "no data-quality guarantee", "no source-truth guarantee"]:
        assert term in low, f"no-claims term missing: {term}"
    assert "a passed profitability gate is still only a threshold-filtered mathematical result" in low


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
