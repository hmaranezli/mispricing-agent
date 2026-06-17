"""tests/test_phase5_pre_net_edge_calculation_input_boundary_implementation_planning.py — pins the
implementation-planning artifact for the `phase5_pre_net_edge_calculation_input_boundary` component
(docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation and keeps net-edge calculator work
unauthorized; pins the future carrier names `ObservableCostValidityContext` and
`PreNetEdgeCalculationInput` (neither implemented here) and names the deferred future gate
`PreNetEdgeCalculationInputGate` / `net_edge_input_preflight`; sharply separates carrier contracts
(intra-object shape/type/format only) from a future validation gate (cross-object compatibility) and a
future calculator (arithmetic/net-edge math); bars cross-validation in carrier factories (no
valid_from<=valid_until comparison, no gross-time-vs-cost-interval comparison, no unit/instrument/venue/
size comparison, no freshness/valid_until/aggregate-cost/net_edge computation); pins the validity-
context contract (wraps exactly one ObservableCostObservation, explicit integer-string validity
interval + provenance, no TTL/duration/current-time/computed valid_until); pins the calculation-input
contract (exactly one GrossEdgeObservation + a non-empty exact tuple of exact ObservableCostValidity
Context items, no list/set/dict/generator, no sort/dedup/aggregate); defers unit compatibility and
asymmetric freshness to a future gate; requires strict halt-carrier rejection; enforces strict typed/
frozen input; bars arithmetic/calculator behavior; makes no market-truth/readiness claims; keeps
existing carriers separate and unaltered; states no runtime edit and no central handoff/memory edit;
restates the future-implementation gate; carries the standard no-claims block; and avoids ready/
complete/safe/absolute-risk and source-trust framing — while asserting no forbidden over-claim wording
appears anywhere and forbidden positive-claim phrases appear only inside the explicit framing /
no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

VALIDITY_CONTEXT_FIELDS = [
    "valid_from_epoch_ms",
    "valid_until_epoch_ms",
    "validity_source_contract",
    "validity_source_artifact",
    "validity_source_field",
    "validity_assertion_type",
    "boundary_version",
]

FORBIDDEN_ECONOMIC_TOKENS = [
    "net_edge", "gross_edge_minus_cost", "total_cost", "net_cost", "effective_cost",
    "sum_cost", "profitability", "expected_profit", "readiness", "trade_score",
    "eligibility", "order_size", "allocation", "execution", "valid_until", "freshness",
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
    assert os.path.isfile(DOC), f"pre-net-edge calculation input planning doc missing: {DOC}"
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
    assert "phase5_pre_net_edge_calculation_input_boundary" in _read()


def test_future_names_pinned():
    text = _read()
    low = text.lower()
    assert "ObservableCostValidityContext" in text
    assert "PreNetEdgeCalculationInput" in text
    assert "PreNetEdgeCalculationInputGate" in text
    assert "net_edge_input_preflight" in low
    assert "this task must not implement" in low


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low
    assert "no net-edge calculator work is authorized" in low
    assert "no next component implementation is authorized" in low


def test_boundary_scope():
    low = _read().lower()
    assert "carrier-contract planning only, not a validation gate and not a calculator" in low


def test_boundary_role():
    low = _read().lower()
    assert "this boundary plans carrier contracts only" in low
    assert "it is not a validation gate" in low
    assert "it is not a calculator" in low
    assert "it is not a raw parser, exchange/api parser, loader, endpoint reader, order-book model, venue model, cost aggregator, unit converter, freshness calculator, risk model, sizing model, execution model, trading component, or reporting component" in low
    assert "it must not infer, enrich, repair, normalize, round, parse, aggregate, net, sum, subtract, compare, score, decide, size, allocate, route orders, or trade" in low


def test_carrier_vs_gate_separation():
    low = _read().lower()
    assert "observablecostvaliditycontext and prenetedgecalculationinput are future carriers only" in low
    assert "they must enforce only intra-object shape/type/format rules" in low
    assert "they must not validate cross-object compatibility" in low
    assert "cross-object checks are deferred to a future separately authorized prenetedgecalculationinputgate / net_edge_input_preflight" in low
    assert "cost validity interval covers gross observed time" in low
    assert "cost units are compatible or convertible with gross-edge units" in low
    assert "instrument/base/quote context compatibility" in low
    assert "venue context compatibility" in low
    assert "depth/size context compatibility" in low
    assert "those checks are not implemented here" in low


def test_no_cross_validation_in_carrier_factories():
    low = _read().lower()
    assert "future make_pre_net_edge_calculation_input must not" in low
    assert "compare gross observed time to cost validity intervals" in low
    assert "compare valid_from_epoch_ms to valid_until_epoch_ms" in low
    assert "compare gross units to cost units" in low
    assert "compare instruments across gross and cost" in low
    assert "compare venues across gross and cost" in low
    assert "compare sizes/depth across gross and cost" in low
    assert "compute freshness" in low
    assert "compute valid_until" in low
    assert "compute aggregate cost" in low
    assert "compute net_edge" in low
    assert "future make_observable_cost_validity_context must not compare valid_from_epoch_ms <= valid_until_epoch_ms" in low
    assert "comparison/coercion is gate behavior, not carrier behavior" in low


def test_validity_context_contract():
    low = _read().lower()
    assert "future observablecostvaliditycontext wraps exactly one observablecostobservation" in low
    for token in VALIDITY_CONTEXT_FIELDS:
        assert token in low, f"validity-context field missing: {token}"
    assert "cost_observation must be exact type(cost_observation) is observablecostobservation" in low
    assert "subclasses must not be accepted" in low
    assert "no inference from observablecostobservation.source_" in low
    assert "no default ttl" in low
    assert "no current-time / wall-clock / system-time / monotonic-time substitution" in low
    assert "no duration field" in low
    assert "no computed valid_until" in low
    assert "no fee-schedules-are-usually-daily assumption" in low
    assert "validity metadata must be provided by a separately authorized upstream/orchestrator/validity-source adapter as exact strings with provenance" in low
    assert "this context does not prove validity; it only carries the declared validity interval and provenance" in low


def test_cost_validity_timestamp_discipline():
    low = _read().lower()
    assert "valid_from_epoch_ms and valid_until_epoch_ms must be exact integer strings in future implementation" in low
    assert "no int coercion in carrier" in low
    assert "no string comparison in carrier" in low
    assert "no valid_from <= valid_until comparison in carrier" in low
    assert "no current-time fallback" in low
    assert "no derived timestamp" in low


def test_calculation_input_contract():
    low = _read().lower()
    assert "future prenetedgecalculationinput wraps exactly one grossedgeobservation and a non-empty tuple of observablecostvaliditycontext" in low
    assert "gross_observation must be exact type(gross_observation) is grossedgeobservation" in low
    assert "cost_validity_contexts must be exact tuple" in low
    assert "the tuple must be non-empty" in low
    assert "every tuple item must be exact type(item) is observablecostvaliditycontext" in low
    assert "list, set, dict, frozenset, mapping, raw json-like containers, generator, iterator, or arbitrary collection must be rejected" in low
    assert "no mutation, no append, no sorting, no deduplication, no aggregation" in low


def test_strict_tuple_discipline():
    low = _read().lower()
    assert "the tuple is used only as an immutable carrier structure" in low
    assert "tuple membership order must be preserved" in low
    assert "the carrier must not sort, rank, group, deduplicate, merge, filter, or aggregate cost contexts" in low
    assert "duplicate cost contexts are not interpreted here; any duplicate-detection or semantic validation is deferred to a future gate" in low
    assert "an empty tuple is invalid" in low


def test_unit_compatibility_deferred():
    low = _read().lower()
    assert "gross-edge units and cost units may differ" in low
    assert "the carrier must not convert bps/rate/quote/base units" in low
    assert "the carrier must not decide convertibility" in low
    assert "unit compatibility declaration/checking belongs to a future gate" in low
    assert "no unit inference" in low
    assert "no unit normalization" in low
    assert "no conversion table" in low
    assert "no arithmetic" in low


def test_asymmetric_freshness_deferred():
    low = _read().lower()
    assert "the gross-edge observation is a fast market snapshot" in low
    assert "cost validity may be slower-moving metadata" in low
    assert "the carrier must not require equal timestamps" in low
    assert "the carrier must not require symmetric freshness windows" in low
    assert "the future gate, not this carrier, must decide whether a cost validity interval covers the gross observation time" in low
    assert "no freshness calculation in this planning task" in low


def test_halt_carrier_and_wrong_path_handling():
    low = _read().lower()
    assert "exact blockedpacket and exact noeligiblehaltpacket must not be accepted as gross observations, cost observations, validity contexts, or calculation inputs" in low
    assert "if a halt carrier reaches this boundary, that is a routing/integration bug" in low
    assert "future implementation must reject exact halt carriers with strict error behavior, not pass-through and not conversion" in low
    assert "it must not duplicate route_halt_carrier" in low
    assert "it must not convert blocked / contract_violation / no_eligible into gross, cost, validity, or calculation-input carriers" in low
    assert "it must not call bool/len/int/float/str/bytes/repr/equality/introspection on offending halt or hostile objects" in low


def test_input_discipline():
    low = _read().lower()
    assert "future inputs must be explicitly typed/frozen or otherwise strictly defined" in low
    assert "raw dicts, generic mapping, json-like blobs, arbitrary objects, attribute-guessed records, duck-typed records, heuristic key guessing, and generic containers are prohibited" in low
    assert "no parser behavior is authorized" in low
    assert "no adapter behavior is authorized in this planning task" in low


def test_no_arithmetic_or_calculator_behavior():
    low = _read().lower()
    assert "the future carriers must not compute net_edge, gross_edge_minus_cost, total_cost, net_cost, effective_cost, sum_cost, profitability, expected_profit, readiness, trade_score, eligibility, order_size, allocation, execution, valid_until, or freshness" in low
    assert "the future carriers must not iterate over the cost tuple to sum or convert values" in low
    assert "they must not call int, float, decimal, or arithmetic operators to compare or compute semantic relationships" in low
    assert "tuple traversal is allowed only for exact item type checking in future implementation" in low
    for token in FORBIDDEN_ECONOMIC_TOKENS:
        assert token in low, f"economic token not explicitly banned: {token}"


def test_no_market_truth_readiness_claims():
    low = _read().lower()
    assert "this boundary proves no market truth, no cost truth, no gross-edge truth, no validity truth, no source truth, no source reliability, no data-quality guarantee, no profitability, no readiness, no paper/live readiness, and no safety guarantee" in low
    assert "it only plans carrier contracts for a future gate/calculator path" in low


def test_relationship_to_existing_components():
    low = _read().lower()
    assert "grossedgeobservation remains separate and already implemented" in low
    assert "observablecostobservation remains separate and already implemented" in low
    assert "gross-edge and cost source-result adapters remain separate and already implemented" in low
    assert "this boundary must not reuse or subclass those carriers" in low
    assert "this boundary must not alter those carriers" in low
    assert "this boundary must not retroactively add ttl to observablecostobservation" in low
    assert "this boundary must not retroactively add calculator fields to grossedgeobservation" in low


def test_no_runtime_and_no_central_handoff_edit():
    low = _read().lower()
    assert "this task makes no phase5 runtime code edits" in low
    assert "this task does not edit the central handoff/memory file and performs no memory closeout" in low


def test_future_implementation_gate():
    low = _read().lower()
    assert "future implementation must be separately authorized, component-scoped, offline, tdd-first, and declared-provenance" in low
    assert "implementation should likely be split into separate slices" in low
    assert "does not authorize implementation or selecting the next component" in low


def test_no_claims_block_present():
    low = _read().lower()
    assert NO_CLAIMS_START.lower() in low and NO_CLAIMS_END.lower() in low
    for term in ["no edge", "no pnl", "no profitability", "no alpha",
                 "no live readiness", "no paper readiness", "no economics readiness",
                 "no safety guarantee", "no data-quality guarantee", "no data-integrity guarantee"]:
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
