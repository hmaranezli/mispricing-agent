"""tests/test_phase5_venue_instrument_readiness_implementation_planning.py — pins the
implementation-planning artifact for the future `phase5_venue_instrument_readiness_boundary`
component (docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation; jointly designs two future components —
`VenueInstrumentReadinessStateContext` (a frozen, factory-only, explicit-supplied venue/instrument
readiness-state carrier) and the `VenueInstrumentReadinessGate` / `venue_instrument_readiness_preflight`
pure state gate with shape `venue_instrument_readiness_preflight(*, evidence_envelope, readiness_state)`;
pins the exact input contract and wrong-type/misroute taxonomy; pins exact-type / exact-str field
rules; pins the case-sensitive identity-equality comparison (venue/instrument_id/base_asset/quote_asset);
pins the explicit status vocabulary; pins the Blocked-vs-NoEligible taxonomy (missing/malformed/
ambiguous/mismatched evidence → BlockedPacket; valid-but-non-active explicit state → NoEligibleHaltPacket;
active+identity-match → input identity pass-through); pins the reason vocabulary; bars
network/api/ping/clock/parser/inference/default/case-normalization/status-broadening and any
liquidity/balance/sizing/trading/paper-live scope and any actionability/trade-readiness/execution-safety
claim; states no runtime edit and no central handoff/memory edit; restates the future-implementation
gate; carries the standard no-claims block; and asserts no forbidden over-claim wording appears anywhere
while forbidden positive-claim phrases appear only inside the explicit framing / no-claims /
prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_venue_instrument_readiness_implementation_planning.md")
RUNTIME_FILE = os.path.join(REPO, "phase5", "venue_instrument_readiness_boundary.py")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"
PROHIBITED_OUT_START = "<!-- PROHIBITED-OUTPUTS-START -->"
PROHIBITED_OUT_END = "<!-- PROHIBITED-OUTPUTS-END -->"

CARRIER_FIELDS = [
    "component_name",
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "readiness_status",
    "source_contract",
    "source_artifact",
    "source_field",
    "state_id",
    "boundary_version",
]

STATUS_VOCAB = [
    "VENUE_INSTRUMENT_STATE_ACTIVE",
    "VENUE_INSTRUMENT_STATE_SUSPENDED",
    "VENUE_INSTRUMENT_STATE_MAINTENANCE",
    "VENUE_INSTRUMENT_STATE_CLOSED",
    "VENUE_INSTRUMENT_STATE_UNSUPPORTED",
]

REASON_VOCAB = [
    "VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MISSING_READINESS_STATE",
    "VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MALFORMED_READINESS_STATE",
    "VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_IDENTITY_MISMATCH",
    "VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_UNRECOGNIZED_STATE_VOCABULARY",
    "VENUE_INSTRUMENT_READINESS_GATE_NO_ELIGIBLE_STATE_NOT_ACTIVE",
]

BANNED_NAMES = [
    "ActionableCandidate", "TradeCandidate", "ReadyEnvelope", "ExecutableSignal",
    "Opportunity", "ExecutionPayload", "Signal", "OrderIntent", "Fillable",
    "Tradable", "Candidate",
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
    assert os.path.isfile(DOC), f"venue/instrument readiness planning doc missing: {DOC}"
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
    assert "phase5_venue_instrument_readiness_boundary" in _read()


def test_future_names_and_function_shape_pinned():
    text = _read()
    low = text.lower()
    assert "VenueInstrumentReadinessStateContext" in text
    assert "make_venue_instrument_readiness_state_context" in low
    assert "VenueInstrumentReadinessGate" in text
    assert "venue_instrument_readiness_preflight" in low
    assert "venue_instrument_readiness_preflight(*, evidence_envelope, readiness_state)" in low
    assert "this planning task must not implement" in low


def test_dual_component_design_pinned():
    low = _read().lower()
    assert "jointly design two future components" in low
    assert "venueinstrumentreadinessstatecontext" in low
    assert "venueinstrumentreadinessgate / venue_instrument_readiness_preflight" in low


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_gate_role():
    low = _read().lower()
    assert "it is a pure/offline/deterministic venue/instrument readiness-state gate" in low
    assert ("it consumes exact postprofitabilityevidenceenvelope plus exact "
            "venueinstrumentreadinessstatecontext" in low)
    assert "it is not a calculator" in low
    assert "it is not a parser" in low
    assert "it is not an adapter" in low
    assert "it is not a unit converter" in low
    assert "it is not an fx/oracle" in low
    assert "it is not a liquidity/orderbook/depth/slippage gate" in low
    assert "it is not a balance/capital/margin gate" in low
    assert "it is not an order-sizing/execution/trading/reporting/paper-live component" in low
    assert "it must not decide whether to trade" in low
    assert ("it must not produce order size, allocation, readiness-to-trade, actionability, "
            "paper/live authority, or execution instruction" in low)


def test_semantic_boundary():
    low = _read().lower()
    assert ("readiness here means only: explicit venue/instrument state evidence permits or halts "
            "this boundary" in low)
    assert ("passing this future boundary must not imply safe-to-trade, executable, actionable, "
            "paper-ready, live-ready, order-ready, or candidate status" in low)
    assert "this is not trade readiness" in low
    assert "this is not actionability" in low
    assert "this is not execution safety" in low
    assert "this is not liquidity readiness" in low
    assert "this is not balance/margin readiness" in low
    assert "this is not proof an order can be placed" in low


def test_carrier_contract():
    text = _read()
    low = text.lower()
    assert ("future carrier wraps only explicit supplied venue/instrument readiness-state data "
            "needed by the gate" in low)
    assert "it must be frozen, repr-safe, anti-truthiness, anti-coercion, factory-only" in low
    assert "it must not read env/config/files/db/network/time" in low
    assert "it must not compute or infer venue/instrument readiness" in low
    assert "no api calls, no network probes, no retries, no ping checks, no time fetching" in low
    assert "no parsing or inferring venue/instrument/status from strings" in low
    assert "no source_artifact parsing" in low
    for field in CARRIER_FIELDS:
        assert field in low, f"carrier field missing: {field}"
    assert ("readiness_status must be an exact, case-sensitive token from the planned status "
            "vocabulary" in low)
    assert "all carrier fields must be exact, non-empty, non-whitespace str" in low


def test_status_vocabulary_pinned():
    text = _read()
    for token in STATUS_VOCAB:
        assert token in text, f"status vocabulary token missing: {token}"


def test_input_contract():
    low = _read().lower()
    assert ("venue_instrument_readiness_preflight accepts exact type(evidence_envelope) is "
            "postprofitabilityevidenceenvelope" in low)
    assert "subclasses rejected" in low
    assert "raw dict/mapping/json/duck-typed objects rejected" in low
    assert ("exact blockedpacket or exact noeligiblehaltpacket received on either argument is a "
            "misroute and must be rejected as a programmatic routing bug" in low)
    assert "readiness_state must be exact venueinstrumentreadinessstatecontext" in low
    assert "wrong type/misroute must be typeerror / misroutedhaltcarriererror, never a market packet" in low
    assert ("missing/malformed/wrong-type/mixed-provenance/ambiguous readiness evidence is "
            "blockedpacket, not noeligible" in low)


def test_identity_comparison_rule():
    low = _read().lower()
    assert ("the gate compares the envelope's explicit venue, instrument_id, base_asset, and "
            "quote_asset to the readiness_state's by exact, case-sensitive equality" in low)
    assert "identity mismatch is a blockedpacket, not noeligible" in low
    assert ("no case normalization, no alias mapping, no spelling repair, no semantic broadening "
            "of status" in low)
    assert "no reach-back beyond the explicit envelope and the explicit readiness state" in low
    assert "do not parse or infer venue/instrument/status from any string field" in low


def test_status_evaluation_rule():
    low = _read().lower()
    assert "an explicit active state with matching identity passes" in low
    assert "an explicit suspended/maintenance/closed/unsupported state halts as no-eligible" in low
    assert "an unrecognized status token is blockedpacket, not noeligible" in low
    assert "success returns the exact same postprofitabilityevidenceenvelope object identity" in low
    assert ("no new wrapper, no union carrier, no shared base hierarchy, no cross-conversion, no "
            "downgrade, no masking" in low)


def test_failure_taxonomy():
    low = _read().lower()
    assert "programmatic wrong-path / wrong-type" in low
    assert "typeerror / misroutedhaltcarriererror" in low
    assert "never blockedpacket or noeligiblehaltpacket" in low
    assert "exact inputs + missing/malformed/ambiguous/mismatched readiness evidence" in low
    assert ("this means system blindness / missing or non-corresponding state evidence, not "
            "market unreadiness" in low)
    assert "exact inputs + identity match + explicit non-active state" in low
    assert "noeligiblehaltpacket" in low
    assert "this means a valid explicit state that is not active, not missing evidence" in low
    assert "exact inputs + identity match + explicit active state" in low
    assert "pass-through identity: return the exact same postprofitabilityevidenceenvelope object" in low
    assert "this is not actionable and not trade-ready" in low


def test_reason_vocabulary_pinned():
    text = _read()
    for token in REASON_VOCAB:
        assert token in text, f"reason vocabulary token missing: {token}"


def test_prohibited_v1_checks():
    low = _read().lower()
    for token in [
        "no liquidity/orderbook/depth/slippage checks",
        "no balance/capital/margin checks",
        "no order sizing",
        "no network/api probe, ping, or reachability check",
        "no clock/time/datetime/now",
        "no defaults",
        "no case or unit normalization",
        "no source_artifact/source_field parsing",
        "no regex extraction from provenance",
        "no semantic broadening of status",
        "no paper/live/trading/reporting/execution",
    ]:
        assert token in low, f"prohibited-check line missing: {token}"


def test_banned_output_names_pinned():
    text = _read()
    for banned in BANNED_NAMES:
        assert banned in text, f"banned output name must be pinned as prohibited: {banned}"


def test_deferred_decisions():
    low = _read().lower()
    for token in [
        "liquidity/orderbook/depth/slippage gate",
        "balance/capital/margin gate",
        "order sizing / allocation",
        "trade-readiness / actionability gate",
        "dynamic venue/instrument status source",
        "multi-venue / multi-provenance readiness aggregation",
        "paper/live execution",
    ]:
        assert token in low, f"deferred decision missing: {token}"


def test_no_runtime_and_no_central_handoff_edit():
    low = _read().lower()
    assert "this task makes no phase5 runtime code edits" in low
    assert ("this task does not edit the central handoff/memory file and performs no memory "
            "closeout" in low)


def test_no_runtime_implementation_created():
    assert not os.path.isfile(RUNTIME_FILE), \
        "planning task must not create the runtime venue/instrument readiness module"
    src = _read()
    assert "class VenueInstrumentReadinessStateContext" not in src, \
        "planning doc must not define the runtime carrier"
    assert "class VenueInstrumentReadinessGate" not in src, \
        "planning doc must not define the runtime gate"
    assert "def venue_instrument_readiness_preflight" not in src, \
        "planning doc must not define the runtime gate function"
    assert "def make_venue_instrument_readiness_state_context" not in src, \
        "planning doc must not define the runtime factory"


def test_future_implementation_gate():
    low = _read().lower()
    assert ("future implementation must be separately authorized, component-scoped, offline, "
            "tdd-first, and declared-provenance" in low)
    assert "this planning artifact does not authorize implementation" in low


def test_no_claims_block_present():
    low = _read().lower()
    assert NO_CLAIMS_START.lower() in low and NO_CLAIMS_END.lower() in low
    for term in ["no edge", "no pnl", "no alpha", "no actionability", "no readiness",
                 "no paper readiness", "no live readiness", "no execution readiness",
                 "no safety guarantee", "no data-quality guarantee", "no source-truth guarantee"]:
        assert term in low, f"no-claims term missing: {term}"
    assert ("a passed venue/instrument readiness-state gate is still only an "
            "explicit-state-filtered result" in low)


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
