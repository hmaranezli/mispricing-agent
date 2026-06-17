"""tests/test_phase5_observable_cost_source_result_adapter_implementation_planning.py — pins the
implementation-planning artifact for the `phase5_observable_cost_source_result_adapter` component
(docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation and keeps net-edge calculator work
unauthorized; pins the future input type name `ObservableCostSourceResult` (not implemented here) and
the future adapter name `adapt_observable_cost_source_result_to_observation`; fixes the typed-to-typed
adapter role (not a raw/JSON/exchange parser, loader, endpoint reader, fee/slippage model, aggregator,
or calculator; never infer/enrich/repair/normalize/round/parse/aggregate); requires strict typed/frozen
input (no raw dict/Mapping/JSON-blob/duck-typed/heuristic key guessing) with strict rejection (not
None/empty/pass-through/default); requires explicit 1:1 keyword mapping into every
`ObservableCostObservation` destination field via make_observable_cost_observation(*, ...); delegates
validation to the observation factory without weakening it (no exception downgrade to None/default/
no-op); enforces float/decimal discipline (no float->string, no exponent normalization, no Decimal
repair); bars zero-evidence invention and missing-as-zero; bars unit/source inference and raw-market
parsing; requires strict halt-carrier misroute rejection (no duplicate route_halt_carrier, no
conversion of BLOCKED/CONTRACT_VIOLATION/NO_ELIGIBLE, no coercion/introspection); requires fail-closed
state handling with no silent None; bars arithmetic/aggregate/list/batch/economic output; makes no
market-truth/readiness claims; states no runtime edit and no central handoff/memory edit; restates the
future-implementation gate; carries the standard no-claims block; and avoids ready/complete/safe/
absolute-risk and source-trust framing — while asserting no forbidden over-claim wording appears
anywhere and forbidden positive-claim phrases appear only inside the explicit framing / no-claims /
prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_observable_cost_source_result_adapter_implementation_planning.md")

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
    "cost_component_type",
    "signed_decimal_value",
    "unit",
    "source_contract",
    "source_artifact",
    "source_field",
    "zero_cost_evidence",
    "boundary_version",
]

FORBIDDEN_ECONOMIC_TOKENS = [
    "total_cost", "net_cost", "effective_cost", "gross_edge", "net_edge",
    "profit", "expected_profit", "readiness", "eligibility", "trade_score",
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
    assert os.path.isfile(DOC), f"observable-cost source-result adapter planning doc missing: {DOC}"
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
    assert "phase5_observable_cost_source_result_adapter" in _read()


def test_future_type_and_function_names_pinned():
    text = _read()
    low = text.lower()
    assert "ObservableCostSourceResult" in text
    assert "adapt_observable_cost_source_result_to_observation(result)" in text
    assert "this task must not implement observablecostsourceresult" in low
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
    assert "it converts exactly one observablecostsourceresult into exactly one observablecostobservation" in low
    assert "it is not a raw parser, not a json parser, not an exchange/api parser, not a loader, not an endpoint reader, not a fee model, not a slippage model, not an aggregator, and not a calculator" in low
    assert "it must not infer, enrich, repair, normalize, round, parse, aggregate, net, sum, subtract, score, decide, or trade" in low


def test_strict_input_type():
    low = _read().lower()
    assert "the future adapter must accept only the finalized typed/frozen observablecostsourceresult" in low
    assert "raw dicts, generic mapping, json-like blobs, arbitrary objects, attribute-guessed records, duck-typed records, and heuristic key guessing are prohibited" in low
    assert "planning must require strict type rejection for wrong input" in low
    assert "wrong input must be a programmatic error, not none, not empty, not pass-through, and not a default observation" in low


def test_forward_declared_source_result_contract():
    low = _read().lower()
    assert "observablecostsourceresult must be documented as a future typed/frozen source-result object" in low
    assert "it must carry already-canonical string fields required by make_observable_cost_observation" in low
    assert "it must not rely on the adapter for conversion from float, exponent notation, nullable values, unit inference, source inference, or zero evidence construction" in low
    assert "the planning doc must require enough future source fields to map 1:1 into every observablecostobservation destination field" in low


def test_explicit_one_to_one_keyword_mapping():
    low = _read().lower()
    missing = [f for f in DESTINATION_FIELDS if f not in low]
    assert not missing, f"destination fields missing: {missing}"
    assert "the future adapter must call make_observable_cost_observation(*, ...) using explicit keyword arguments only" in low
    assert "no positional construction" in low
    assert "no dict unpacking from raw or generic mappings" in low
    assert "no automatic defaults" in low
    assert "no fallback values" in low
    assert "no field guessing" in low
    assert "no renaming by heuristic" in low
    assert "no lossy transformation" in low


def test_validation_delegation_without_weakening():
    low = _read().lower()
    assert "the adapter must not reimplement or weaken make_observable_cost_observation validation" in low
    assert "decimal string canonicality, exact-str enforcement, unit/source non-empty rules, zero-cost evidence rules, and anti-float discipline remain enforced by the observation factory" in low
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


def test_zero_cost_evidence_discipline():
    low = _read().lower()
    assert "the future adapter must not invent zero_cost_evidence" in low
    assert "it must not treat missing evidence as zero" in low
    assert "it must not insert observable_cost_zero_evidence_not_applicable unless that exact value is already present in the typed source result or explicitly specified by a future typed source-result contract" in low
    assert "it must not convert missing/none/empty/false/0 into zero evidence" in low
    assert "zero-cost epistemology remains owned by observablecostobservation construction rules" in low


def test_unit_source_discipline():
    low = _read().lower()
    assert "the future adapter must not infer unit" in low
    assert "it must not infer source_contract, source_artifact, or source_field" in low
    assert "bare values without unit/provenance are invalid" in low
    assert "all provenance must be carried from explicit typed source-result fields" in low
    assert "no exchange/api/raw-market parsing is authorized" in low


def test_halt_carrier_and_wrong_path_handling():
    low = _read().lower()
    assert "if the adapter is invoked with exact blockedpacket or exact noeligiblehaltpacket, planning must require strict misroute rejection, not pass-through and not conversion" in low
    assert "it must not duplicate route_halt_carrier" in low
    assert "it must not convert blocked / contract_violation / no_eligible into cost observations" in low
    assert "it must not call bool/len/int/float/str/bytes/repr/equality/introspection on offending halt or hostile objects" in low
    assert "subclasses are not valid halt carriers and not valid source results; they must not be accepted as either" in low


def test_status_state_handling():
    low = _read().lower()
    assert "the adapter should convert only source-result states that represent an explicitly observed cost/friction fact" in low
    assert "success-like or observed-like state must be explicitly named in planning, but implementation is deferred" in low
    assert "unknown, missing, failure, blocked, no-eligible, or malformed states must fail closed" in low
    assert "it must never silently return none" in low


def test_no_arithmetic_or_economic_output():
    low = _read().lower()
    assert "the adapter must not compute total_cost, net_cost, effective_cost, gross_edge, net_edge, profit, expected_profit, readiness, eligibility, or trade_score" in low
    assert "it must not aggregate multiple observations" in low
    assert "it must not produce list/collection/batch observations" in low
    assert "it must not authorize net-edge or calculator behavior" in low
    for token in FORBIDDEN_ECONOMIC_TOKENS:
        assert token in low, f"economic token not explicitly banned: {token}"


def test_no_market_truth_readiness_claims():
    low = _read().lower()
    assert "the adapter proves no market truth, no cost correctness, no source truth, no source reliability, no data-quality guarantee, no profitability, no readiness, no paper/live readiness, and no safety guarantee" in low
    assert "it only plans a typed-to-typed mapping contract" in low


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
