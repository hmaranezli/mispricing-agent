"""tests/test_phase5_liquidity_capacity_evidence_boundary_implementation_planning.py — pins the
implementation-planning artifact for the future `phase5_liquidity_capacity_evidence_boundary`
component (docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation; jointly designs two future components —
`LiquidityCapacityEvidenceContext` (a frozen, factory-only, explicit-supplied liquidity/depth capacity
evidence carrier) and the `LiquidityCapacityGate` / `liquidity_capacity_preflight` pure capacity
sufficiency gate with shape `liquidity_capacity_preflight(*, evidence_envelope, liquidity_evidence)`;
pins the exact input contract and wrong-type/misroute taxonomy; pins exact-type / exact-str /
decimal-string / unsigned-integer-epoch field rules; pins the case-sensitive identity-equality
comparison (venue/instrument_id/base_asset/quote_asset); pins the deterministic supplied-scalar
staleness comparison (no clock); pins the inclusive capacity-sufficiency rule; pins the
Blocked-vs-NoEligible taxonomy; pins the reason vocabulary; pins envelope-sourced packet provenance;
pins slippage passivity; bars network/api/clock/parser/inference/default/normalization and any
sizing/balance/margin/order-routing/execution/paper-live scope and any actionability/trade-readiness
claim and any threshold/profitability/net-edge debris carry-over; states no runtime edit and no
central handoff/memory edit; carries the standard no-claims block; and asserts no forbidden over-claim
wording appears anywhere while forbidden positive-claim phrases appear only inside the explicit
framing / no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_liquidity_capacity_evidence_boundary_implementation_planning.md")

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
    "observed_size",
    "observed_size_unit",
    "available_capacity",
    "capacity_unit",
    "liquidity_snapshot_epoch_ms",
    "evidence_epoch_tolerance_ms",
    "source_contract",
    "source_artifact",
    "source_field",
    "liquidity_evidence_id",
    "boundary_version",
    "estimated_slippage_bps",
]

REASON_VOCAB = [
    "LIQUIDITY_CAPACITY_GATE_BLOCKED_MISSING_LIQUIDITY_EVIDENCE",
    "LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE",
    "LIQUIDITY_CAPACITY_GATE_BLOCKED_IDENTITY_MISMATCH",
    "LIQUIDITY_CAPACITY_GATE_BLOCKED_UNIT_MISMATCH",
    "LIQUIDITY_CAPACITY_GATE_BLOCKED_STALE_EVIDENCE",
    "LIQUIDITY_CAPACITY_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPACITY",
]

BANNED_NAMES = [
    "ActionableCandidate", "TradeCandidate", "ReadyEnvelope", "ExecutableSignal",
    "Opportunity", "ExecutionPayload", "Signal", "OrderIntent", "Fillable",
    "Tradable", "Candidate",
]

# Prior-gate reason tokens / symbols that must NOT be copied into this boundary's plan.
FORBIDDEN_DEBRIS_TOKENS = [
    "NET_EDGE_PROFITABILITY_GATE",
    "BELOW_THRESHOLD",
    "MALFORMED_THRESHOLD",
    "PROFITABILITY_THRESHOLD",
    "net_edge_profitability_preflight",
    "calculate_net_edge",
    "ProfitabilityThresholdPolicyContext",
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
    "fill guaranteed", "fills guaranteed", "slippage-free", "fill is certain",
]


def _read():
    assert os.path.isfile(DOC), f"liquidity capacity planning doc missing: {DOC}"
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


def test_component_name_present_and_has_no_slippage_token():
    text = _read()
    assert "phase5_liquidity_capacity_evidence_boundary" in text
    assert "slippage" not in "phase5_liquidity_capacity_evidence_boundary"


def test_future_names_and_function_shape_pinned():
    text = _read()
    low = text.lower()
    assert "LiquidityCapacityEvidenceContext" in text
    assert "make_liquidity_capacity_evidence_context" in low
    assert "LiquidityCapacityGate" in text
    assert "liquidity_capacity_preflight" in low
    assert "liquidity_capacity_preflight(*, evidence_envelope, liquidity_evidence)" in low
    assert "this planning task must not implement" in low


def test_dual_component_design_pinned():
    low = _read().lower()
    assert "jointly design two future components" in low
    assert "liquiditycapacityevidencecontext" in low
    assert "liquiditycapacitygate / liquidity_capacity_preflight" in low


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_no_runtime_implementation_created():
    # Durable docs-only guard: planning artifact pins names in prose but never carries a runtime
    # class/function definition, and the runtime module must not be created by this planning task.
    assert not os.path.isfile(os.path.join(REPO, "phase5", "liquidity_capacity_evidence_boundary.py")), \
        "planning task must not create the runtime liquidity capacity module"
    src = _read()
    assert "class LiquidityCapacityEvidenceContext" not in src
    assert "class LiquidityCapacityGate" not in src
    assert "def liquidity_capacity_preflight" not in src
    assert "def make_liquidity_capacity_evidence_context" not in src


def test_capacity_sufficiency_boundary_role():
    low = _read().lower()
    assert "it is a capacity sufficiency boundary only" in low
    assert "it is not a slippage calculator" in low
    assert "it is not a net-edge calculator" in low
    assert "it is not a sizing engine" in low
    assert "it is not an order router" in low
    assert "it is not an execution component" in low
    assert "it is not a balance/capital/margin component" in low
    assert "it is not a reporting component" in low
    assert "it is not paper/live readiness" in low


def test_semantic_boundary():
    low = _read().lower()
    assert ("passing this future boundary must not imply safe-to-trade, executable, actionable, "
            "order-ready, paper-ready, live-ready, or candidate status" in low)
    assert "do not broaden sufficient capacity into execution readiness" in low


def test_carrier_contract_and_field_set():
    text = _read()
    low = text.lower()
    assert "it must be frozen, repr-safe, anti-truthiness, anti-coercion, factory-only" in low
    assert "it must not read env/config/files/db/network/time" in low
    assert "no parsing of source_artifact" in low
    for field in CARRIER_FIELDS:
        assert field in low, f"carrier field missing: {field}"
    assert ("all identity/provenance/string fields must be exact, non-empty, non-whitespace str" in low)
    assert "str subclasses rejected" in low


def test_decimal_string_discipline():
    low = _read().lower()
    assert ("numeric magnitude fields must be exact, non-empty decimal strings, preserved verbatim" in low)
    assert ("decimal strings reject float objects, int objects, decimal objects, bool, none, bytes, "
            "dicts, exponent notation, nan, infinity, signed infinity, empty, whitespace, and "
            "malformed decimal text" in low)
    assert ("liquidity_snapshot_epoch_ms and evidence_epoch_tolerance_ms are canonical unsigned "
            "integer strings" in low)


def test_decimal_conversion_is_local_ephemeral_only():
    low = _read().lower()
    assert ("the gate may convert decimal strings to decimal only in local ephemeral comparison "
            "variables" in low)
    assert ("decimal conversion must never mutate evidence_envelope or liquiditycapacityevidencecontext "
            "attributes" in low)


def test_slippage_is_passive_metadata_only():
    low = _read().lower()
    assert "estimated_slippage_bps is passive evidence/audit metadata only" in low
    assert "the gate must not read estimated_slippage_bps for decisioning" in low
    assert "the gate must not compute net-edge minus slippage" in low
    assert "the gate must not compute a slippage model" in low
    assert "the gate must not compare slippage against profitability or any threshold" in low


def test_input_contract():
    low = _read().lower()
    assert ("liquidity_capacity_preflight accepts exact type(evidence_envelope) is "
            "postprofitabilityevidenceenvelope" in low)
    assert "subclasses rejected" in low
    assert "raw dict/mapping/json/duck-typed objects rejected" in low
    assert ("exact blockedpacket or exact noeligiblehaltpacket received on either argument is a "
            "misroute and must be rejected as a programmatic routing bug" in low)
    assert "liquidity_evidence must be exact liquiditycapacityevidencecontext" in low
    assert ("wrong type/misroute must be typeerror / misroutedhaltcarriererror, never a market "
            "packet" in low)


def test_identity_comparison_rule():
    low = _read().lower()
    assert ("the gate compares the envelope's explicit venue, instrument_id, base_asset, and "
            "quote_asset to the liquidity evidence's by exact, case-sensitive equality" in low)
    assert "identity mismatch is a blockedpacket, not noeligible" in low
    assert "no case normalization, no alias mapping, no semantic broadening" in low


def test_deterministic_staleness_rule():
    low = _read().lower()
    assert "no internal clock" in low
    assert ("no time.time(), datetime.now(), utcnow(), monotonic(), or runtime clock import" in low)
    assert ("staleness is a deterministic comparison of supplied scalar fields only" in low)
    assert ("abs(evidence_envelope.observed_at_epoch_ms - liquidity_snapshot_epoch_ms) <= "
            "evidence_epoch_tolerance_ms" in low)
    assert "missing or malformed epoch or tolerance fields fail closed" in low
    assert "negative epoch tolerance fails closed" in low
    assert "stale liquidity evidence returns a blockedpacket, not a noeligiblehaltpacket" in low


def test_capacity_sufficiency_rule():
    low = _read().lower()
    assert "the gate compares only supplied magnitudes: observed_size <= available_capacity" in low
    assert "the inequality is inclusive: equal capacity is sufficient" in low
    assert ("available_capacity of \"0\" or negative is malformed liquidity evidence and returns a "
            "blockedpacket, not a noeligiblehaltpacket" in low)
    assert ("observed_size that is zero, negative, or malformed fails closed per the upstream "
            "envelope contract and is never silently reinterpreted" in low)
    assert "unit mismatch between observed_size_unit and capacity_unit returns a blockedpacket" in low
    assert ("insufficient positive capacity with valid identity/unit/staleness returns a "
            "noeligiblehaltpacket" in low)
    assert ("sufficient capacity with valid identity/unit/staleness returns the exact same upstream "
            "evidence envelope object by identity" in low)
    assert ("no partial fill, no reduced size, no max tradable size, no allocation, no order "
            "quantity, no order intent, and no routing" in low)


def test_failure_taxonomy():
    low = _read().lower()
    assert "programmatic wrong-path / wrong-type" in low
    assert "typeerror / misroutedhaltcarriererror" in low
    assert "never blockedpacket or noeligiblehaltpacket" in low
    assert "this means a valid explicit insufficiency, not missing evidence" in low


def test_reason_vocabulary_pinned():
    text = _read()
    for token in REASON_VOCAB:
        assert token in text, f"reason vocabulary token missing: {token}"


def test_provenance_rule():
    low = _read().lower()
    assert ("packet source_contract/source_artifact/source_field must come from the upstream "
            "postprofitabilityevidenceenvelope, not from liquiditycapacityevidencecontext" in low)
    assert ("liquidity evidence provenance must not overwrite the upstream envelope provenance" in low)
    assert "do not invent new packet fields, schemas, factories, or reason builders" in low


def test_prohibited_v1_checks():
    low = _read().lower()
    for token in [
        "no position sizing",
        "no balance/capital/margin",
        "no wallet/custody",
        "no order routing",
        "no order quantity",
        "no fill probability",
        "no orderbook simulation",
        "no slippage model",
        "no net-edge recalculation",
        "no profitability recalculation",
        "no threshold copying",
        "no clock/time/datetime/now",
        "no network/api/db/file/env/config",
        "no source_artifact parsing",
    ]:
        assert token in low, f"prohibited-check line missing: {token}"


def test_no_threshold_or_profitability_debris_carryover():
    text = _read()
    for token in FORBIDDEN_DEBRIS_TOKENS:
        assert token not in text, f"prior-gate reason/symbol debris carried over: {token}"
    # this boundary's own reason tokens all carry the LIQUIDITY_CAPACITY_GATE prefix
    for token in REASON_VOCAB:
        assert token.startswith("LIQUIDITY_CAPACITY_GATE_"), token


def test_banned_output_names_pinned():
    text = _read()
    for banned in BANNED_NAMES:
        assert banned in text, f"banned output name must be pinned as prohibited: {banned}"


def test_deferred_decisions():
    low = _read().lower()
    for token in [
        "slippage modelling",
        "order sizing / allocation",
        "balance/capital/margin gate",
        "order routing / execution",
        "fill-probability / orderbook simulation",
        "paper/live execution",
    ]:
        assert token in low, f"deferred decision missing: {token}"


def test_no_runtime_and_no_central_handoff_edit():
    low = _read().lower()
    assert "this task makes no phase5 runtime code edits" in low
    assert ("this task does not edit the central handoff/memory file and performs no memory "
            "closeout" in low)


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
                 "no fill certainty", "no liquidity-correctness guarantee",
                 "no source-truth guarantee", "no price-correctness guarantee"]:
        assert term in low, f"no-claims term missing: {term}"
    assert ("a passed capacity sufficiency gate is still only an explicit-evidence-filtered "
            "result" in low)


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
