"""tests/test_phase5_gross_edge_source_result_adapter_implementation_planning.py — pins the
implementation-planning artifact for the `phase5_gross_edge_source_result_adapter` component
(docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation and keeps net-edge calculator work
unauthorized; pins the future input type name `GrossEdgeSourceResult` (not implemented here) and the
future adapter name `adapt_gross_edge_source_result_to_observation`; fixes the typed-to-typed adapter
role (not a raw/JSON/exchange/order-book parser/model, loader, endpoint reader, venue/sizing model,
aggregator, or calculator); requires strict typed/frozen input with strict rejection (no raw dict/
Mapping/JSON-blob/duck-typed/heuristic key guessing; subclasses rejected; never None/empty/pass-
through/default); requires explicit 1:1 keyword mapping into every `GrossEdgeObservation` destination
field via make_gross_edge_observation(*, ...) with no hardcoding; delegates validation to the
observation factory without weakening it; enforces float/decimal discipline (no float->string, no
exponent normalization, no Decimal repair); bars time/freshness creation (no observed_at_epoch_ms /
staleness_threshold_ms creation, no current-time substitution, no valid_until/freshness compute); bars
direction/asset/venue/depth/unit/source inference and sentinel insertion; requires strict halt-carrier
misroute rejection; requires fail-closed state handling with no silent None; bars arithmetic/aggregate/
list/batch/economic output; makes no market-truth/readiness claims; keeps the observable-cost adapter
separate (no reuse, no cross-conversion); states no runtime edit and no central handoff/memory edit;
restates the future-implementation gate; carries the standard no-claims block; and avoids ready/
complete/safe/absolute-risk and source-trust framing — while asserting no forbidden over-claim wording
appears anywhere and forbidden positive-claim phrases appear only inside the explicit framing /
no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_gross_edge_source_result_adapter_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

DESTINATION_FIELDS = [
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "edge_direction",
    "base_asset",
    "quote_asset",
    "instrument_id",
    "venue_scope",
    "venue_buy",
    "venue_sell",
    "observed_at_epoch_ms",
    "staleness_threshold_ms",
    "gross_edge_value",
    "gross_edge_unit",
    "gross_edge_source_contract",
    "gross_edge_source_artifact",
    "gross_edge_source_field",
    "observed_size",
    "size_unit",
    "depth_source_contract",
    "depth_source_artifact",
    "depth_source_field",
    "boundary_version",
]

FORBIDDEN_ECONOMIC_TOKENS = [
    "net_edge", "total_cost", "net_cost", "effective_cost", "profitability",
    "expected_profit", "readiness", "trade_score", "eligibility", "order_size",
    "allocation", "execution", "valid_until", "freshness",
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
    assert os.path.isfile(DOC), f"gross-edge source-result adapter planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "adapter planning doc is empty"


def test_component_name_present():
    assert "phase5_gross_edge_source_result_adapter" in _read()


def test_future_type_and_function_names_pinned():
    text = _read()
    low = text.lower()
    assert "GrossEdgeSourceResult" in text
    assert "adapt_gross_edge_source_result_to_observation(result)" in text
    assert "this task must not implement grossedgesourceresult" in low
    assert "this task must not define its full runtime class or parser" in low


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low
    assert "no net-edge calculator work is authorized" in low
    assert "no next component implementation is authorized" in low


def test_adapter_scope():
    low = _read().lower()
    assert "typed-to-typed adapter planning only, not a parser and not a calculator" in low


def test_adapter_role():
    low = _read().lower()
    assert "the future adapter is a typed-to-typed adapter only" in low
    assert "it converts exactly one grossedgesourceresult into exactly one grossedgeobservation" in low
    assert "it is not a raw parser, not a json parser, not an exchange/api parser, not a loader, not an endpoint reader, not an order-book model, not a venue model, not a sizing model, not an aggregator, and not a calculator" in low
    assert "it must not infer, enrich, repair, normalize, round, parse, aggregate, net, sum, subtract, score, decide, size, allocate, route orders, or trade" in low


def test_strict_input_type():
    low = _read().lower()
    assert "the future adapter must accept only the finalized typed/frozen grossedgesourceresult" in low
    assert "raw dicts, generic mapping, json-like blobs, arbitrary objects, attribute-guessed records, duck-typed records, and heuristic key guessing are prohibited" in low
    assert "planning must require strict type rejection for wrong input" in low
    assert "wrong input must be a programmatic error, not none, not empty, not pass-through, and not a default observation" in low
    assert "subclasses must not be accepted" in low


def test_forward_declared_source_result_contract():
    low = _read().lower()
    assert "grossedgesourceresult must be documented as a future typed/frozen source-result object" in low
    assert "it must carry already-canonical string fields required by make_gross_edge_observation" in low
    assert "it must not rely on the adapter for conversion from float, exponent notation, nullable values, direction inference, venue inference, base/quote inference, source inference, timestamp substitution, staleness calculation, or depth/size inference" in low
    assert "the planning doc must require enough future source fields to map 1:1 into every grossedgeobservation destination field" in low


def test_explicit_one_to_one_keyword_mapping():
    low = _read().lower()
    missing = [f for f in DESTINATION_FIELDS if f not in low]
    assert not missing, f"destination fields missing: {missing}"
    assert "the future adapter must call make_gross_edge_observation(*, ...) using explicit keyword arguments only" in low
    assert "no positional construction" in low
    assert "no dict unpacking from raw or generic mappings" in low
    assert "no automatic defaults" in low
    assert "no fallback values" in low
    assert "no field guessing" in low
    assert "no renaming by heuristic" in low
    assert "no lossy transformation" in low
    assert "no hardcoded component_name, direction, venue, timestamp, staleness, unit, source, size, or boundary_version" in low


def test_validation_delegation_without_weakening():
    low = _read().lower()
    assert "the adapter must not reimplement or weaken make_gross_edge_observation validation" in low
    assert "exact-str enforcement, canonical decimal discipline, integer-string time/staleness discipline, direction allowed-set, venue_scope rules, venue buy/sell rules, sentinel rejection, non-negative observed_size, and provenance rules remain enforced by the observation factory" in low
    assert "the adapter may only pass already-declared source fields through explicitly" in low
    assert "it must not catch factory exceptions and downgrade them to none, empty observations, default observations, or no-op" in low


def test_float_decimal_discipline():
    low = _read().lower()
    assert "the future adapter must not convert float to string" in low
    assert "it must not accept binary floats" in low
    assert "it must not normalize 1e-3 into 0.001" in low
    assert "it must not use decimal to repair input" in low
    assert "it must not round, epsilon-compare, approximate, or canonicalize values" in low
    assert "if upstream source-result fields are not already canonical strings, future implementation must fail closed" in low


def test_time_freshness_discipline():
    low = _read().lower()
    assert "the future adapter must not create observed_at_epoch_ms" in low
    assert "it must not substitute current time, wall-clock time, system time, or monotonic time" in low
    assert "it must not create or compute staleness_threshold_ms" in low
    assert "it must not compute valid_until" in low
    assert "it must not calculate freshness/staleness" in low
    assert "time and staleness fields must be carried only from explicit typed source-result fields" in low


def test_direction_asset_venue_discipline():
    low = _read().lower()
    assert "the future adapter must not infer edge_direction" in low
    assert "it must not infer base_asset, quote_asset, or instrument_id" in low
    assert "it must not infer venue_scope, venue_buy, or venue_sell" in low
    assert "it must not normalize symbols, venue names, or instruments" in low
    assert "it must not convert single/cross venue states" in low
    assert "it must not insert sentinel values" in low
    assert "all direction, asset, instrument, and venue fields must be carried from explicit typed source-result fields" in low


def test_depth_liquidity_discipline():
    low = _read().lower()
    assert "the future adapter must not infer observed_size" in low
    assert "it must not compute trade size, order size, max tradable size, allocation, or liquidity decision" in low
    assert "it must not convert missing depth into zero" in low
    assert "it must not aggregate depth across venues/order books" in low
    assert "depth fields must be carried from explicit typed source-result fields only" in low


def test_unit_source_discipline():
    low = _read().lower()
    assert "the future adapter must not infer units" in low
    assert "it must not infer source_contract, source_artifact, or source_field values" in low
    assert "bare values without unit/provenance are invalid" in low
    assert "gross-edge and depth provenance must be carried from explicit typed source-result fields" in low
    assert "no exchange/api/raw-market parsing is authorized" in low


def test_halt_carrier_and_wrong_path_handling():
    low = _read().lower()
    assert "if the adapter is invoked with exact blockedpacket or exact noeligiblehaltpacket, planning must require strict misroute rejection, not pass-through and not conversion" in low
    assert "it must not duplicate route_halt_carrier" in low
    assert "it must not convert blocked / contract_violation / no_eligible into gross-edge observations" in low
    assert "it must not call bool/len/int/float/str/bytes/repr/equality/introspection on offending halt or hostile objects" in low
    assert "subclasses are not valid halt carriers and not valid source results; they must not be accepted as either" in low


def test_status_state_handling():
    low = _read().lower()
    assert "the adapter should convert only source-result states that represent an explicitly observed gross-edge fact" in low
    assert "success-like or observed-like state must be explicitly named in planning, but implementation is deferred" in low
    assert "unknown, missing, failure, blocked, no-eligible, stale, malformed, or non-observed states must fail closed" in low
    assert "it must never silently return none" in low


def test_no_arithmetic_or_economic_output():
    low = _read().lower()
    assert "the adapter must not compute net_edge, total_cost, net_cost, effective_cost, profitability, expected_profit, readiness, trade_score, eligibility, order_size, allocation, execution, valid_until, or freshness" in low
    assert "it must not aggregate multiple observations" in low
    assert "it must not produce list/collection/batch observations" in low
    assert "it must not authorize net-edge or calculator behavior" in low
    for token in FORBIDDEN_ECONOMIC_TOKENS:
        assert token in low, f"economic token not explicitly banned: {token}"


def test_no_market_truth_readiness_claims():
    low = _read().lower()
    assert "the adapter proves no market truth, no price correctness, no liquidity correctness, no source truth, no source reliability, no data-quality guarantee, no profitability, no readiness, no paper/live readiness, and no safety guarantee" in low
    assert "it only plans a typed-to-typed mapping contract" in low


def test_relationship_to_observable_cost_side():
    low = _read().lower()
    assert "the gross-edge adapter mirrors the already established observable-cost typed-to-typed adapter discipline" in low
    assert "it must not reuse the observable-cost adapter" in low
    assert "it must not convert cost observations into gross-edge observations" in low
    assert "it must not convert gross-edge observations into cost observations" in low
    assert "calculator-input behavior remains deferred" in low


def test_no_runtime_and_no_central_handoff_edit():
    low = _read().lower()
    assert "this task makes no phase5 runtime code edits" in low
    assert "this task does not edit the central handoff/memory file and performs no memory closeout" in low


def test_future_implementation_gate():
    low = _read().lower()
    assert "future implementation must be separately authorized, component-scoped, offline, tdd-first, and declared-provenance" in low
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
