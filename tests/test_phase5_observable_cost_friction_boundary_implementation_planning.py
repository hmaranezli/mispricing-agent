"""tests/test_phase5_observable_cost_friction_boundary_implementation_planning.py — pins the
implementation-planning artifact for the `phase5_observable_cost_friction_boundary` component
(docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation and keeps net-edge calculator work
unauthorized; fixes the boundary role (not a calculator/parser/loader/trading component, carries
explicitly observed atomic cost/friction components only, never infers/enriches/aggregates/nets);
pins the epistemology of zero (missing != zero, no default-zero, fail closed on unproven zero); pins
the sign convention (positive=cost, negative=rebate, zero=explicitly observed only, no clipping, the
boundary itself does not compute gross-minus-friction); requires explicit unit/scale + provenance and
bars bare/unitless numbers; prohibits binary-float arithmetic and requires exact decimal semantics
later; restricts to atomic observations and bars total_cost/net_cost/net_edge-style aggregate fields;
requires strict halt-carrier misroute rejection (no pass-through/coercion/introspection here);
enforces strict typed/frozen input (no raw dict/Mapping/JSON-blob/heuristic key guessing, no exchange
payload parsing); makes no market-truth/economic claims; keeps halt propagation separate (no
duplicate route_halt_carrier, no conversion of BLOCKED/CONTRACT_VIOLATION/NO_ELIGIBLE into cost
observations); states no runtime edit and no central handoff/memory edit; restates the future-
implementation gate; carries the standard no-claims block; and avoids ready/complete/safe/absolute-
risk and source-trust framing — while asserting no forbidden over-claim wording appears anywhere and
forbidden positive-claim phrases appear only inside the explicit framing / no-claims / prohibited-
output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_observable_cost_friction_boundary_implementation_planning.md")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

FORBIDDEN_AGGREGATE_FIELDS = [
    "total_cost", "net_cost", "effective_cost", "gross_edge", "net_edge",
    "profit", "expected_profit", "readiness", "trade_score", "eligibility",
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
    assert os.path.isfile(DOC), f"observable-cost/friction planning doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    while start in text and end in text and text.index(start) < text.index(end):
        s = text.index(start)
        e = text.index(end) + len(end)
        text = text[:s] + text[e:]
    return text


def test_doc_exists():
    assert _read().strip(), "observable-cost/friction planning doc is empty"


def test_component_name_present():
    assert "phase5_observable_cost_friction_boundary" in _read()


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low
    assert "net-edge calculator work remains unauthorized" in low


def test_boundary_scope():
    low = _read().lower()
    assert "observable-cost / friction planning boundary only, not a calculator" in low


def test_boundary_role():
    low = _read().lower()
    assert "the observable-cost / friction boundary is not a calculator" in low
    assert "it is not an exchange parser, fee schedule parser, slippage model, loader, endpoint reader, artifact reader, or trading component" in low
    assert "it may only define future contracts for carrying explicitly observed atomic cost/friction components" in low
    assert "it must not infer, enrich, repair, normalize, aggregate, net, sum, subtract, annualize, rank, score, or decide" in low


def test_epistemology_of_zero():
    low = _read().lower()
    assert "missing cost data and zero cost are not equivalent" in low
    assert "must never be treated as zero cost" in low
    assert "omitted, default, fallback, parse failure, unavailable field, or unknown field" in low
    assert "a true zero cost is valid only when actively and explicitly observed from a declared source field" in low
    assert "fail closed on unproven zero" in low
    assert "no default-zero behavior is allowed anywhere" in low


def test_sign_convention():
    low = _read().lower()
    assert "positive value = cost / penalty / friction debit" in low
    assert "negative value = rebate / credit, such as maker rebate" in low
    assert "zero value = explicitly observed zero only" in low
    assert "negative observed values must not be clipped, absolutized, rejected by default, or silently converted to positive cost" in low
    assert "the boundary itself does not compute gross-edge-minus-friction; it only preserves sign semantics for a future calculator" in low
    assert "no downgrade from rebate to cost and no upgrade from unknown to rebate/zero" in low


def test_unit_scale_source_requirement():
    low = _read().lower()
    assert "bare numeric values are prohibited" in low
    assert "every future observable-cost component must carry an explicit unit/scale and explicit source provenance" in low
    assert "the planning doc must not implement a parser or conversion table" in low
    assert "every observation must be traceable to declared source_contract, source_artifact, and source_field" in low
    assert "unitless numbers are invalid and must be fail-closed in future implementation" in low


def test_binary_float_prohibition():
    low = _read().lower()
    assert "binary float arithmetic is prohibited for cost/friction semantics" in low
    assert "planning must require exact decimal representation in future implementation" in low
    assert "no float-derived rounding, epsilon comparison, approximate equality, binary-float normalization, or float defaulting" in low
    assert "this planning task must not choose final implementation mechanics beyond requiring exact decimal semantics later" in low


def test_atomic_observations_only():
    low = _read().lower()
    assert "the future boundary must carry atomic observed components only" in low
    assert "it must not include or authorize fields like total_cost, net_cost, effective_cost, gross_edge, net_edge, profit, expected_profit, readiness, trade_score, or eligibility" in low
    assert "aggregation and arithmetic belong to a separately authorized future calculator, not this boundary" in low
    for field in FORBIDDEN_AGGREGATE_FIELDS:
        assert field in low, f"forbidden aggregate field not explicitly banned: {field}"


def test_halt_carrier_misroute_protection():
    low = _read().lower()
    assert "blockedpacket and noeligiblehaltpacket must not be processed by the observable-cost / friction boundary" in low
    assert "if a halt carrier reaches this boundary, that is a routing/integration bug, not a cost observation" in low
    assert "misroutedhaltcarriererror" in low
    assert "do not pass through, convert, unwrap, serialize, or reinterpret halt carriers here" in low
    assert "do not call bool/len/int/float/str/bytes/repr/equality/introspection on offending halt or hostile objects" in low


def test_input_discipline():
    low = _read().lower()
    assert "the future input must be explicitly typed/frozen or otherwise strictly defined" in low
    assert "raw dicts, generic mapping, arbitrary objects, attribute-guessed records, json-like blobs, and heuristic key guessing are prohibited" in low
    assert "the boundary must not parse exchange/api/raw-market payloads" in low
    assert "adapter/parser work, if needed, must be a separate future slice" in low


def test_no_market_truth_claims():
    low = _read().lower()
    assert "the boundary does not prove a market exists" in low
    assert "the boundary does not prove cost correctness, source truth, source reliability, liquidity, profitability, readiness, or trade eligibility" in low
    assert "it only defines the contract for carrying explicitly observed cost/friction facts with provenance" in low


def test_relationship_to_halt_propagation():
    low = _read().lower()
    assert "halt propagation remains separate and already implemented" in low
    assert "this boundary must not duplicate route_halt_carrier" in low
    assert "this boundary must not convert blocked / contract_violation / no_eligible into cost observations" in low
    assert "it must state that halted payloads bypass cost/friction planning and calculation paths" in low


def test_no_runtime_and_no_central_handoff_edit():
    low = _read().lower()
    assert "this task makes no phase5 runtime code edits" in low
    assert "this task does not edit the central handoff/memory file and performs no memory closeout" in low


def test_future_implementation_gate():
    low = _read().lower()
    assert "future implementation must be separately authorized, component-scoped, offline, tdd-first, and declared-provenance" in low
    assert "no net-edge calculator work is authorized by this planning artifact" in low
    assert "does not authorize implementation or selecting the next component" in low


def test_no_parser_loader_endpoint_trading_paperlive_authorization():
    low = _read().lower()
    assert "authorizes no parser, loader, endpoint reader, exchange fee model, slippage model, calculator, reporting, trading, or paper/live work" in low


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
