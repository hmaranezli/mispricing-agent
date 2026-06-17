"""tests/test_phase5_gross_edge_observation_boundary_implementation_planning.py — pins the
implementation-planning artifact for the `phase5_gross_edge_observation_boundary` component
(docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation and keeps net-edge calculator work
unauthorized; pins the future atomic carrier name `GrossEdgeObservation` and bars actionable/
candidate/signal naming (nothing is actionable before net-edge/risk/output/paper-live gates); fixes
the observation-not-decision boundary role; pins gross-edge != net-edge/profitability/readiness
semantics; keeps the carrier separate from ObservableCostObservation with no shared base/generic/
polymorphic hierarchy and exact-type routing; requires canonical decimal strings and bars binary
float; pins explicit direction / asset / venue / time / value+unit+provenance / depth fields with no
inference, no valid_until / freshness computation, and no current-time substitution; bars sizing /
allocation / order decisions; restricts to one atomic observation (no list/batch/aggregate); requires
strict halt-carrier misroute rejection; enforces strict typed/frozen input (no raw dict/Mapping/JSON
parsing); bars calculator/economic output; makes no market-truth/readiness claims; keeps observable
cost separate; states no runtime edit and no central handoff/memory edit; restates the future-
implementation gate; carries the standard no-claims block; and avoids ready/complete/safe/absolute-
risk and source-trust framing — while asserting no forbidden over-claim wording appears anywhere and
forbidden positive-claim phrases appear only inside the explicit framing / no-claims / prohibited-
output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_gross_edge_observation_boundary_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

FORBIDDEN_CARRIER_NAMES = [
    "ActionableCandidate", "TradeCandidate", "ExecutableCandidate", "ReadyCandidate",
    "Opportunity", "Signal",
]

PLANNED_FIELD_TOKENS = [
    "edge_direction",
    "base_asset", "quote_asset", "instrument_id",
    "venue_scope", "venue_buy", "venue_sell",
    "observed_at_epoch_ms", "staleness_threshold_ms",
    "gross_edge_value", "gross_edge_unit",
    "gross_edge_source_contract", "gross_edge_source_artifact", "gross_edge_source_field",
    "observed_size", "size_unit",
    "depth_source_contract", "depth_source_artifact", "depth_source_field",
]

FORBIDDEN_ECONOMIC_TOKENS = [
    "net_edge", "total_cost", "net_cost", "effective_cost", "profitability",
    "expected_profit", "readiness", "trade_score", "eligibility", "order_size",
    "allocation", "execution",
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
    assert os.path.isfile(DOC), f"gross-edge observation planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "gross-edge observation planning doc is empty"


def test_component_name_present():
    assert "phase5_gross_edge_observation_boundary" in _read()


def test_carrier_name_and_forbidden_names():
    text = _read()
    low = text.lower()
    assert "GrossEdgeObservation" in text
    assert "it must not be named actionablecandidate, tradecandidate, executablecandidate, readycandidate, opportunity, or signal, because nothing is actionable before net-edge, risk, output, and paper/live gates" in low
    for name in FORBIDDEN_CARRIER_NAMES:
        assert name.lower() in low, f"forbidden carrier name not explicitly banned: {name}"


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low
    assert "no net-edge calculator work is authorized" in low
    assert "no next component implementation is authorized" in low


def test_boundary_scope():
    low = _read().lower()
    assert "gross-edge observation planning boundary only, not a calculator and not a decision carrier" in low


def test_boundary_role():
    low = _read().lower()
    assert "grossedgeobservation is an observation carrier, not a decision carrier" in low
    assert "it is not an actionable payload" in low
    assert "it is not a calculator input implementation" in low
    assert "it is not a raw parser, exchange/api parser, loader, endpoint reader, order-book model, venue model, sizing model, risk model, execution model, trading component, or reporting component" in low
    assert "it may only define future contracts for carrying explicitly observed gross-edge facts with provenance" in low
    assert "it must not infer, enrich, repair, normalize, aggregate, net, sum, subtract, annualize, rank, score, decide, size, allocate, route orders, or trade" in low


def test_gross_edge_semantics():
    low = _read().lower()
    assert "gross edge is pre-friction and pre-net-edge" in low
    assert "gross edge is not net edge" in low
    assert "gross edge is not profitability" in low
    assert "gross edge is not readiness" in low
    assert "gross edge is not a trade recommendation" in low
    assert "a positive gross edge must not imply positive net edge" in low
    assert "a gross-edge observation must not authorize order placement or paper/live action" in low


def test_name_and_semantic_separation():
    low = _read().lower()
    assert "grossedgeobservation is separate from observablecostobservation" in low
    assert "it must not reuse observablecostobservation" in low
    assert "it must not subclass or share a generic base observation carrier" in low
    assert "no shared baseobservation, genericobservation, edgepacket, candidatepacket, or polymorphic hierarchy" in low
    assert "future routing must use exact type checks only" in low
    assert "no isinstance acceptance for boundary carriers" in low


def test_canonical_decimal_discipline():
    low = _read().lower()
    assert "gross-edge numeric values must be represented as canonical exact decimal strings in future implementation" in low
    assert "binary float arithmetic is prohibited" in low
    assert "no float parsing, no float-to-string conversion, no binary-float rounding, no epsilon comparison, no approximate equality, no exponent normalization" in low


def test_direction_discipline():
    low = _read().lower()
    assert "direction must be an explicit exact string field in future implementation" in low
    assert "edge_direction" in low
    assert "direction values may be planned as exact labels such as long, short, or cross_venue" in low
    assert "direction is descriptive only" in low
    assert "direction must not authorize trading, order side, execution, readiness, or paper/live action" in low
    assert "unknown, empty, inferred, or default direction is prohibited" in low


def test_asset_instrument_identity():
    low = _read().lower()
    assert "future gross-edge observation must carry explicit base/quote/instrument identity as exact string fields" in low
    for token in ["base_asset", "quote_asset", "instrument_id"]:
        assert token in low
    assert "unitless or instrumentless gross-edge is invalid" in low
    assert "the boundary must not infer base/quote from symbols, filenames, venue names, or raw strings" in low
    assert "no parser or symbol-normalizer is authorized" in low


def test_venue_identity():
    low = _read().lower()
    assert "future gross-edge observation must carry exact string venue fields" in low
    for token in ["venue_scope", "venue_buy", "venue_sell"]:
        assert token in low
    assert "venue_scope may distinguish single_venue from cross_venue" in low
    assert "no tuple/list/container venue representation" in low
    assert "no venue inference" in low
    assert "for non-applicable venue fields, future implementation may use explicit sentinel strings, but no none/empty/default values" in low
    assert "cross-venue identity must remain explicit and provenance-backed" in low


def test_time_freshness_discipline():
    low = _read().lower()
    assert "future gross-edge observation must carry explicit observed time and staleness threshold fields" in low
    for token in ["observed_at_epoch_ms", "staleness_threshold_ms"]:
        assert token in low
    assert "these should be exact integer strings in future implementation" in low
    assert "the boundary must not compute valid_until" in low
    assert "the boundary must not calculate freshness/staleness in this planning component" in low
    assert "freshness calculation belongs to a separately authorized future calculator/input gate" in low
    assert "missing, inferred, default, current-time, wall-clock, or system-time substitution is prohibited" in low


def test_value_unit_provenance():
    low = _read().lower()
    for token in ["gross_edge_value", "gross_edge_unit", "gross_edge_source_contract",
                  "gross_edge_source_artifact", "gross_edge_source_field"]:
        assert token in low
    assert "bare numeric gross-edge values are prohibited" in low
    assert "unitless values are prohibited" in low
    assert "source-less values are prohibited" in low
    assert "unit/source must be explicit, not inferred" in low
    assert "no market-truth, source-truth, or data-quality claim is made by carrying these fields" in low


def test_liquidity_depth_observation():
    low = _read().lower()
    assert "future gross-edge observation must carry observed liquidity/depth capacity as observation, not sizing decision" in low
    for token in ["observed_size", "size_unit", "depth_source_contract",
                  "depth_source_artifact", "depth_source_field"]:
        assert token in low
    assert "observed_size should be a canonical exact decimal string in future implementation" in low
    assert "this is not trade_size" in low
    assert "this is not allocation" in low
    assert "this is not order sizing" in low
    assert "this is not a max tradable size decision" in low
    assert "this is only an observed depth/liquidity fact with provenance" in low
    assert "no sizing decision is authorized" in low


def test_atomic_observation_only():
    low = _read().lower()
    assert "the future boundary must carry one atomic gross-edge observation only" in low
    assert "no list, collection, set, batch, basket, portfolio, aggregation, ranking, or selection behavior" in low
    assert "no aggregation across venues, instruments, timestamps, or observations" in low
    assert "no arithmetic output" in low


def test_halt_carrier_misroute_protection():
    low = _read().lower()
    assert "blockedpacket and noeligiblehaltpacket must not be processed by the gross-edge observation boundary" in low
    assert "if a halt carrier reaches this boundary, that is a routing/integration bug, not a gross-edge observation" in low
    assert "planning must require strict misroute rejection, not pass-through and not conversion" in low
    assert "it must not duplicate route_halt_carrier" in low
    assert "it must not convert blocked / contract_violation / no_eligible into gross-edge observations" in low
    assert "it must not call bool/len/int/float/str/bytes/repr/equality/introspection on offending halt or hostile objects" in low


def test_input_discipline():
    low = _read().lower()
    assert "the future input/source for gross-edge observation must be explicitly typed/frozen or otherwise strictly defined" in low
    assert "raw dicts, generic mapping, json-like blobs, arbitrary objects, attribute-guessed records, duck-typed records, and heuristic key guessing are prohibited" in low
    assert "no exchange/api/raw-market parsing is authorized" in low
    assert "parser/adapter work, if needed, must be a separate future slice" in low


def test_no_calculator_or_economic_output():
    low = _read().lower()
    assert "the boundary must not compute or authorize net_edge, total_cost, net_cost, effective_cost, profitability, expected_profit, readiness, trade_score, eligibility, order_size, allocation, or execution" in low
    assert "gross edge and observed size do not imply net edge or tradability" in low
    assert "net-edge calculator work remains unauthorized" in low
    for token in FORBIDDEN_ECONOMIC_TOKENS:
        assert token in low, f"economic token not explicitly banned: {token}"


def test_no_market_truth_readiness_claims():
    low = _read().lower()
    assert "the boundary proves no market truth, no price correctness, no liquidity correctness, no source truth, no source reliability, no data-quality guarantee, no profitability, no readiness, no paper/live readiness, and no safety guarantee" in low
    assert "it only plans a future atomic observation contract" in low


def test_relationship_to_observable_cost():
    low = _read().lower()
    assert "the observable-cost/friction boundary remains separate and already implemented" in low
    assert "gross-edge observation must not include cost/friction observations" in low
    assert "gross-edge observation must not compute with costs" in low
    assert "cost collection/set behavior remains deferred" in low
    assert "calculator-input behavior remains deferred" in low


def test_no_runtime_and_no_central_handoff_edit():
    low = _read().lower()
    assert "this task makes no phase5 runtime code edits" in low
    assert "this task does not edit the central handoff/memory file and performs no memory closeout" in low


def test_future_implementation_gate():
    low = _read().lower()
    assert "future implementation must be separately authorized, component-scoped, offline, tdd-first, and declared-provenance" in low
    assert "does not authorize implementation or selecting the next component" in low


def test_all_planned_field_tokens_present():
    low = _read().lower()
    missing = [t for t in PLANNED_FIELD_TOKENS if t not in low]
    assert not missing, f"planned field tokens missing: {missing}"


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
