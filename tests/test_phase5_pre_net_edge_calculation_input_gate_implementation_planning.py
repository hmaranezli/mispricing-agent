"""tests/test_phase5_pre_net_edge_calculation_input_gate_implementation_planning.py — pins the
implementation-planning artifact for the future `phase5_pre_net_edge_calculation_input_gate`
component (docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation; pins the future gate name
`PreNetEdgeCalculationInputGate`, the future function `net_edge_input_preflight` and its shape
`net_edge_input_preflight(*, calculation_input, evaluation_epoch_ms)`; pins the exact input contract
(exact PreNetEdgeCalculationInput, subclasses/raw-container/duck-typed rejected, exact halt carriers
are a misroute); requires an explicitly-provided exact integer-string `evaluation_epoch_ms` with no
clock fallback; allows local integer parsing only inside the gate (never in carriers) and bars
Decimal/float/economic/cost/net-edge arithmetic; pins the five exact time equations; pins the
failure taxonomy (programmatic / contract-violation / blocked-needs-evidence / no-eligible / pass)
and precedence; reserves NoEligible for gross-snapshot staleness only in V1; returns the input
identity on pass; pins the case-sensitive unit policy and proportional vocabulary with no
FX/oracle/conversion/normalization; defers instrument/venue/size/depth and any source-field parsing;
pins the planned blocked/no-eligible reason vocabulary; reuses existing BlockedPacket /
NoEligibleHaltPacket with no union wrapper / no polymorphic halt base; states no runtime edit and no
central handoff/memory edit; restates the future-implementation gate; carries the standard no-claims
block; and asserts no forbidden over-claim wording appears anywhere while forbidden positive-claim
phrases appear only inside the explicit framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_pre_net_edge_calculation_input_gate_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

REASON_VOCAB = [
    "PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_TIME_CAUSALITY",
    "PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_INVALID_COST_INTERVAL",
    "PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_GROSS_TIME",
    "PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_EVALUATION_TIME",
    "PRE_NET_EDGE_GATE_BLOCKED_UNSUPPORTED_UNIT_COMPATIBILITY",
    "PRE_NET_EDGE_GATE_NO_ELIGIBLE_GROSS_SNAPSHOT_STALE",
]

PROPORTIONAL_UNITS = ["BPS", "BASIS_POINTS", "RATE", "PERCENT", "PERCENTAGE"]

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
    assert os.path.isfile(DOC), f"pre-net-edge input gate planning doc missing: {DOC}"
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
    assert "phase5_pre_net_edge_calculation_input_gate" in _read()


def test_future_names_and_function_shape_pinned():
    text = _read()
    low = text.lower()
    assert "PreNetEdgeCalculationInputGate" in text
    assert "net_edge_input_preflight" in low
    assert "net_edge_input_preflight(*, calculation_input, evaluation_epoch_ms)" in low
    assert "this planning task must not implement" in low


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low
    assert "no net-edge calculator work is authorized" in low


def test_gate_role():
    low = _read().lower()
    assert "it is a cross-object validation gate / preflight" in low
    assert "it is not a carrier" in low
    assert "it is not a calculator" in low
    assert "it is not a parser" in low
    assert "it is not an adapter" in low
    assert "it is not a cost aggregator" in low
    assert "it is not a unit converter" in low
    assert "it is not a price/fx oracle" in low
    assert "it is not a trading, reporting, paper-live, or execution component" in low
    assert "it decides only whether an exact prenetedgecalculationinput can proceed toward the future calculator" in low
    assert "it produces no net-edge, no total-cost, no profitability, no readiness, no order size, no execution instruction" in low


def test_input_contract():
    low = _read().lower()
    assert "future net_edge_input_preflight accepts exact type(calculation_input) is prenetedgecalculationinput" in low
    assert "subclasses rejected" in low
    assert "raw dict/mapping/json-like object/duck-typed object rejected" in low
    assert "exact blockedpacket / exact noeligiblehaltpacket received at this boundary is a misroute and must be rejected as a programmatic routing bug" in low


def test_evaluation_epoch_explicit_no_clock_fallback():
    low = _read().lower()
    assert "evaluation_epoch_ms must be provided explicitly by the caller/orchestrator" in low
    assert "evaluation_epoch_ms must be exact str, non-empty, non-whitespace, and match ^\\d+$" in low
    assert "str subclasses, none, bool/int/float/decimal/containers/objects rejected" in low
    assert "no current-time, wall-clock, system-time, monotonic-time, datetime, or fallback time source is allowed" in low
    assert "no default evaluation time" in low


def test_allowed_local_math_only_in_gate():
    low = _read().lower()
    assert "gate may locally parse exact integer strings with int() only after exact ^\\d+$ validation" in low
    assert "gate may perform integer timestamp comparisons and the single timestamp addition gross_observed_at_epoch_ms + gross_staleness_threshold_ms" in low
    assert "parsed ints are local temporaries only" in low
    assert "the original carrier fields remain exact strings and must never be mutated, rewritten, normalized, or re-emitted as ints" in low
    assert "no decimal, float, economic arithmetic, cost arithmetic, gross-minus-cost, total-cost, or net-edge arithmetic" in low


def test_time_equations_pinned():
    low = _read().lower()
    assert "gross_observed = int(calculation_input.gross_observation.observed_at_epoch_ms)" in low
    assert "gross_staleness = int(calculation_input.gross_observation.staleness_threshold_ms)" in low
    assert "evaluation_time = int(evaluation_epoch_ms)" in low
    assert "cost_from = int(context.valid_from_epoch_ms)" in low
    assert "cost_until = int(context.valid_until_epoch_ms)" in low
    assert "evaluation_time >= gross_observed" in low
    assert "cost_from <= cost_until" in low
    assert "cost_from <= gross_observed <= cost_until" in low
    assert "cost_from <= evaluation_time <= cost_until" in low
    assert "evaluation_time <= gross_observed + gross_staleness" in low


def test_failure_taxonomy_pinned():
    low = _read().lower()
    # 1 programmatic wrong path
    assert "programmatic wrong path / wrong type" in low
    assert "future behavior: typeerror / misroutedhaltcarriererror" in low
    assert "never blockedpacket or noeligiblehaltpacket" in low
    # 2 contract / data contradiction
    assert "contract/data contradiction" in low
    assert "evaluation_time < gross_observed" in low
    assert "cost_from > cost_until" in low
    assert "future behavior: blockedpacket with planning_gate_contract_violation semantics" in low
    # 3 evidence / applicability failure
    assert "evidence/applicability failure" in low
    assert "cost validity interval does not cover gross_observed" in low
    assert "cost validity interval does not cover evaluation_time" in low
    assert "unsupported unit compatibility evidence" in low
    assert "future behavior: blockedpacket with planning_gate_blocked_needs_evidence / blocked_needs_evidence semantics" in low
    # 4 market no-eligible
    assert "market no-eligible" in low
    assert "evaluation_time > gross_observed + gross_staleness" in low
    assert "future behavior: noeligiblehaltpacket" in low
    assert "this is the only v1 no-eligible market-fact failure" in low
    # 5 pass
    assert "return the identical prenetedgecalculationinput object by identity" in low
    assert "no copy, no wrapping, no enrichment, no mutation" in low


def test_precedence_pinned():
    low = _read().lower()
    assert "programmatic wrong-path errors happen before semantic gate results" in low
    assert "contract/data contradictions and evidence/applicability failures must not be masked as noeligible" in low
    assert "blocked outcomes take precedence over noeligible if both could be observed" in low
    assert "noeligible is reserved for gross market snapshot staleness only in v1" in low
    assert "success returns input identity" in low


def test_unit_policy_pinned():
    low = _read().lower()
    text = _read()
    assert "gate v1 must not convert units" in low
    assert "gate v1 must not normalize case" in low
    assert "gate v1 must not call .upper(), .lower(), strip-for-normalization, or map aliases" in low
    assert "unit checks are case-sensitive exact string checks" in low
    assert "exact match passes: cost_observation.unit == gross_observation.gross_edge_unit" in low
    assert "static proportional cost units are admissible without conversion only if cost_observation.unit is exactly one of" in low
    for unit in PROPORTIONAL_UNITS:
        assert unit in text, f"proportional unit token missing (must be exact uppercase): {unit}"
    assert "any other non-matching absolute unit is blocked as missing/unsupported unit compatibility evidence" in low
    assert "no fx rate, no oracle, no conversion table, no quote/base conversion, no decimal math" in low


def test_deferred_checks_pinned():
    low = _read().lower()
    for token in [
        "instrument/base/quote compatibility",
        "venue compatibility",
        "size/depth compatibility",
        "volume tier / applicable size range",
        "cost duplicate detection",
        "cost ordering interpretation",
        "cost aggregation",
        "gross observed_size > 0 eligibility",
        "gross_edge_value positive/negative/profitability interpretation",
        "source_artifact/source_field parsing",
        "regex extraction from provenance strings",
        "source_contract semantics inference",
        "any inference from file names, artifact names, or source fields",
    ]:
        assert token in low, f"deferred check missing: {token}"


def test_reason_for_deferral_pinned():
    low = _read().lower()
    assert "does not carry explicit base_asset, quote_asset, instrument_id, venue, applicable_size_range, or volume-tier fields" in low
    assert "gate v1 must not invent missing applicability data" in low
    assert "missing applicability policy may require a future costapplicabilitycontext or separately authorized policy object" in low


def test_output_planning_pinned():
    low = _read().lower()
    assert "future pass output is exact same prenetedgecalculationinput identity" in low
    assert "future blocked output uses existing blockedpacket / make_blocked_packet" in low
    assert "future no-eligible output uses existing noeligiblehaltpacket / make_no_eligible_halt_packet" in low
    assert "no new generic union wrapper" in low
    assert "no shared base class" in low
    assert "no polymorphic halt hierarchy" in low
    assert "no conversion between blockedpacket and noeligiblehaltpacket" in low
    assert "no downgrading contract_violation to no_eligible" in low
    assert "no masking missing evidence as no_eligible" in low


def test_reason_vocabulary_pinned():
    text = _read()
    for token in REASON_VOCAB:
        assert token in text, f"reason vocabulary token missing: {token}"


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
