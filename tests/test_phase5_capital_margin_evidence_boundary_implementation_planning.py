"""tests/test_phase5_capital_margin_evidence_boundary_implementation_planning.py — pins the
implementation-planning artifact for the future `phase5_capital_margin_evidence_boundary` component
(docs-only planning, offline).

Runs no batch, fetches no endpoint, parses no artifact, builds no engine, edits no runtime code.
Asserts the planning artifact authorizes no implementation; jointly designs two future components —
`CapitalMarginEvidenceContext` (a frozen, factory-only, explicit-supplied capital/margin evidence
carrier) and the `CapitalMarginGate` / `capital_margin_preflight` pure capital-sufficiency ledger
auditor with shape
`capital_margin_preflight(*, evidence_envelope, capital_evidence, expected_capital_scope_id)`; pins
the ledger-auditor (not calculator) principle; pins the exact input/control-scalar contract and the
wrong-type/misroute taxonomy; pins exact-str / verbatim / no-numeric-parsing carrier rules; pins the
case-sensitive identity-equality comparison (venue/instrument_id/base_asset/quote_asset/side + size
magnitude + capital_scope_id); pins the capital-unit binding; pins the two separate deterministic
supplied-scalar staleness checks (no clock); pins the inclusive capital-sufficiency rule with
zero-free-capital as NoEligible and negative-free-capital / non-positive required_capital as malformed;
pins the Blocked-vs-NoEligible taxonomy; pins the reason vocabulary; pins envelope-sourced packet
provenance with no raw value leakage; bars network/api/clock/parser and any
price/notional/fee/leverage/margin-formula/sizing/allocation/routing/execution/PnL/profitability/
net-edge scope and any actionability/trade-readiness claim; states no runtime edit and no central
handoff/memory edit; carries the standard no-claims block; and asserts no forbidden over-claim wording
appears anywhere while forbidden positive-claim phrases appear only inside the explicit framing /
no-claims / prohibited-output blocks.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff",
                   "phase5_capital_margin_evidence_boundary_implementation_planning.md")
RUNTIME = os.path.join(REPO, "phase5", "capital_margin_evidence_boundary.py")

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
    "side",
    "observed_size",
    "observed_size_unit",
    "required_capital",
    "required_capital_unit",
    "available_free_capital",
    "available_free_capital_unit",
    "required_capital_epoch_ms",
    "available_free_capital_snapshot_epoch_ms",
    "evidence_epoch_tolerance_ms",
    "capital_scope_id",
    "source_contract",
    "source_artifact",
    "source_field",
    "capital_evidence_id",
    "boundary_version",
]

REASON_VOCAB = [
    "CAPITAL_MARGIN_GATE_BLOCKED_MISSING_CAPITAL_EVIDENCE",
    "CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE",
    "CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH",
    "CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH",
    "CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE",
    "CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL",
]

ORDERED_PRIORITY = [
    "1. exact blockedpacket or noeligiblehaltpacket in any argument -> misroutedhaltcarriererror",
    "2. exact type checks",
    "3. missing allow-listed capital evidence field -> capital_margin_gate_blocked_missing_capital_evidence",
    "4. malformed grammar / scalar validity -> capital_margin_gate_blocked_malformed_capital_evidence",
    "5. identity mismatch -> capital_margin_gate_blocked_identity_mismatch",
    "6. unit mismatch -> capital_margin_gate_blocked_unit_mismatch",
    "7. stale evidence -> capital_margin_gate_blocked_stale_evidence",
    "8. insufficient capital -> capital_margin_gate_no_eligible_insufficient_capital",
    "9. sufficient -> same evidence_envelope by identity",
]

BANNED_NAMES = [
    "ActionableCandidate", "TradeCandidate", "ReadyEnvelope", "ExecutableSignal",
    "Opportunity", "ExecutionPayload", "Signal", "OrderIntent", "Fillable",
    "Tradable", "Candidate",
]

# Prior-boundary reason tokens / symbols that must NOT be copied into this boundary's plan.
FORBIDDEN_DEBRIS_TOKENS = [
    "LIQUIDITY_CAPACITY_GATE",
    "NET_EDGE_PROFITABILITY_GATE",
    "BELOW_THRESHOLD",
    "MALFORMED_THRESHOLD",
    "PROFITABILITY_THRESHOLD",
    "net_edge_profitability_preflight",
    "calculate_net_edge",
]

FORBIDDEN_CLAIM_PHRASES = [
    "ready-to-fly", "ready to fly", "system-ready", "system ready",
    "is ready", "are ready", "production ready", "paper ready",
    "execution ready", "live ready", "economics ready", "ready for live",
    "is profitable", "profit confirmed", "profitable strategy",
    "edge confirmed", "positive edge", "tradeable edge", "alpha confirmed",
    "is solvent", "solvency confirmed",
]

FORBIDDEN_WORDING = [
    "eliminates all risk", "eliminates risk", "zero risk", "tamper-proof",
    "verified truth", "clean data", "trusted data", "is immutable",
    "guarantees correctness", "is impossible", "cannot happen",
    "final phase 5 contract", "last critical piece", "is complete", "is perfect",
    "is now safe", "fully complete", "the last piece",
    "source is trusted", "data is valid",
    "funds guaranteed", "capital guaranteed", "balance is certain",
]


def _read():
    assert os.path.isfile(DOC), f"capital/margin planning doc missing: {DOC}"
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


def test_runtime_module_is_absent():
    assert not os.path.isfile(RUNTIME), \
        "planning-only task must not create phase5/capital_margin_evidence_boundary.py"


def test_component_name_present():
    assert "phase5_capital_margin_evidence_boundary" in _read()


def test_future_names_and_function_shape_pinned():
    text = _read()
    low = text.lower()
    assert "CapitalMarginEvidenceContext" in text
    assert "make_capital_margin_evidence_context" in low
    assert "CapitalMarginGate" in text
    assert "capital_margin_preflight" in low
    assert ("capital_margin_preflight(*, evidence_envelope, capital_evidence, "
            "expected_capital_scope_id)" in low)
    assert "this planning task must not implement" in low


def test_dual_component_design_pinned():
    low = _read().lower()
    assert "jointly design two future components" in low
    assert "capitalmarginevidencecontext" in low
    assert "capitalmargingate / capital_margin_preflight" in low


def test_planning_only_not_implementation():
    low = _read().lower()
    assert "implementation-planning only" in low or "implementation planning only" in low
    assert "not implementation" in low
    assert "no implementation is authorized" in low or "authorizes no implementation" in low


def test_planning_doc_contains_no_runtime_implementation():
    # Durable docs-only guard: the planning artifact pins names in prose but must never carry a
    # runtime class/function definition.
    src = _read()
    assert "class CapitalMarginEvidenceContext" not in src
    assert "class CapitalMarginGate" not in src
    assert "def capital_margin_preflight" not in src
    assert "def make_capital_margin_evidence_context" not in src


def test_ledger_auditor_role_not_calculator():
    low = _read().lower()
    assert "the capital/margin boundary is a ledger auditor, not a calculator" in low
    assert "required_capital and available_free_capital are supplied evidence scalars" in low
    for phrase in [
        "it must not compute price",
        "it must not compute notional",
        "it must not compute leverage",
        "it must not compute fee",
        "it must not compute a margin requirement",
        "it must not compute capital reservation",
        "it must not compute sizing",
        "it must not compute allocation",
        "it must not compute pnl, profitability, or net edge",
    ]:
        assert phrase in low, f"ledger-auditor prohibition missing: {phrase}"
    assert "it is not a sizing engine" in low
    assert "it is not an order router" in low
    assert "it is not an execution component" in low
    assert "it is not a reporting component" in low


def test_semantic_boundary():
    low = _read().lower()
    assert ("passing this future boundary must not imply safe-to-trade, executable, actionable, "
            "order-ready, paper-ready, live-ready, or candidate status" in low)
    assert "do not broaden sufficient capital into execution readiness" in low


def test_carrier_contract_and_field_set():
    text = _read()
    low = text.lower()
    assert "it must be frozen, repr-safe, anti-truthiness, anti-coercion, factory-only" in low
    assert "it must not read env/config/files/db/network/time" in low
    assert "no parsing of source_artifact" in low
    for field in CARRIER_FIELDS:
        assert field in low, f"carrier field missing: {field}"
    assert "the field set is exact and closed" in low
    assert ("all carrier fields must be exact, non-empty, non-whitespace str" in low)
    assert "str subclasses rejected" in low
    assert "preserved verbatim" in low
    assert "no decimal/int parsing in the carrier" in low
    assert "no numeric validation in the carrier" in low
    assert "no bool/truthiness/coercion" in low
    assert "safe repr exposes only component_name and boundary_version" in low
    assert "component_name is fixed by the factory" in low


def test_input_and_control_scalar_contract():
    low = _read().lower()
    assert ("capital_margin_preflight accepts exact type(evidence_envelope) is "
            "postprofitabilityevidenceenvelope" in low)
    assert "subclasses rejected" in low
    assert "raw dict/mapping/json/duck-typed objects rejected" in low
    assert ("exact blockedpacket or exact noeligiblehaltpacket received on any argument is a "
            "misroute and must be rejected as a programmatic routing bug" in low)
    assert "capital_evidence must be exact capitalmarginevidencecontext" in low
    assert ("expected_capital_scope_id must be an exact, non-empty, non-whitespace str" in low)
    assert ("wrong type/misroute must be typeerror / misroutedhaltcarriererror, never a market "
            "packet" in low)
    assert "a wrong-type control scalar is a capitalmargingatetypeerror" in low


def test_identity_comparison_rule():
    low = _read().lower()
    assert ("the gate compares the envelope's explicit venue, instrument_id, base_asset, "
            "quote_asset, and side to the capital evidence's by exact, case-sensitive equality" in low)
    assert ("side binding is an identity comparison" in low)
    assert ("decimal(evidence_envelope.observed_size) != decimal(capital_evidence.observed_size) "
            "is an identity mismatch" in low)
    assert ("expected_capital_scope_id != capital_evidence.capital_scope_id is an identity "
            "mismatch" in low)
    assert "identity mismatch is a blockedpacket, not noeligible" in low
    assert "no case normalization, no alias mapping, no semantic broadening" in low


def test_unit_binding_rule():
    low = _read().lower()
    assert ("evidence_envelope.size_unit must equal capital_evidence.observed_size_unit" in low)
    assert ("capital_evidence.required_capital_unit must equal "
            "capital_evidence.available_free_capital_unit" in low)
    assert "unit mismatch returns a blockedpacket" in low


def test_two_separate_deterministic_staleness_checks():
    low = _read().lower()
    assert "no internal clock" in low
    assert ("no time.time(), datetime.now(), utcnow(), monotonic(), or runtime clock import" in low)
    assert ("staleness is a deterministic comparison of supplied scalar fields only" in low)
    assert "there are two separate staleness checks" in low
    assert ("abs(int(evidence_envelope.observed_at_epoch_ms) - int(required_capital_epoch_ms)) <= "
            "int(evidence_epoch_tolerance_ms)" in low)
    assert ("abs(int(evidence_envelope.observed_at_epoch_ms) - "
            "int(available_free_capital_snapshot_epoch_ms)) <= int(evidence_epoch_tolerance_ms)" in low)
    assert "if either staleness check fails the gate returns a blockedpacket" in low
    assert "missing or malformed epoch or tolerance fields fail closed" in low
    assert "stale capital evidence returns a blockedpacket, not a noeligiblehaltpacket" in low


def test_capital_sufficiency_rule():
    low = _read().lower()
    assert ("the gate compares only supplied scalars: required_capital <= available_free_capital" in low)
    assert "the inequality is inclusive: equal capital is sufficient" in low
    assert ("required_capital that is zero, negative, or malformed is malformed capital evidence "
            "and returns a blockedpacket" in low)
    assert ("negative available_free_capital is malformed capital evidence and returns a "
            "blockedpacket" in low)
    assert ("available_free_capital of \"0\" is a valid explicit insufficiency and returns a "
            "noeligiblehaltpacket, not a blockedpacket" in low)
    assert ("insufficient positive capital with valid identity/unit/staleness returns a "
            "noeligiblehaltpacket" in low)
    assert ("sufficient capital with valid identity/unit/staleness returns the exact same upstream "
            "evidence envelope object by identity" in low)
    assert ("no partial sizing, no allocation, no order quantity, no order intent, no routing, and "
            "no execution" in low)


def test_decimal_conversion_is_local_ephemeral_only():
    low = _read().lower()
    assert ("the gate may convert decimal strings to decimal only in local ephemeral comparison "
            "variables" in low)
    assert ("decimal conversion must never mutate evidence_envelope or capitalmarginevidencecontext "
            "attributes" in low)
    assert "no float arithmetic" in low


def test_branch_priority_documented_in_order():
    low = _read().lower()
    last = -1
    for marker in ORDERED_PRIORITY:
        idx = low.find(marker)
        assert idx != -1, f"branch-priority line missing: {marker}"
        assert idx > last, f"branch-priority line out of order: {marker}"
        last = idx


def test_reason_vocabulary_pinned():
    text = _read()
    for token in REASON_VOCAB:
        assert token in text, f"reason vocabulary token missing: {token}"


def test_provenance_rule_and_no_value_leakage():
    low = _read().lower()
    assert ("packet source_contract/source_artifact/source_field must come from the upstream "
            "postprofitabilityevidenceenvelope, not from capitalmarginevidencecontext" in low)
    assert ("capital_evidence.source_contract, capital_evidence.source_artifact, "
            "capital_evidence.source_field, capital_evidence_id, and boundary_version must not be "
            "used as packet provenance" in low)
    assert "do not invent new packet fields, schemas, factories, or reason builders" in low
    assert ("packet reasons and details must not leak raw observed_size, required_capital, "
            "available_free_capital, epoch, tolerance, or scope values" in low)


def test_prohibited_v1_checks():
    low = _read().lower()
    for token in [
        "no position sizing",
        "no allocation",
        "no order quantity",
        "no order routing",
        "no execution",
        "no wallet fetch",
        "no network",
        "no clock",
        "no pnl",
        "no profitability",
        "no threshold",
        "no net-edge",
        "no price",
        "no notional",
        "no fee",
        "no leverage",
        "no margin formula",
    ]:
        assert token in low, f"prohibited-check line missing: {token}"


def test_no_prior_boundary_debris_carryover():
    text = _read()
    for token in FORBIDDEN_DEBRIS_TOKENS:
        assert token not in text, f"prior-boundary reason/symbol debris carried over: {token}"
    for token in REASON_VOCAB:
        assert token.startswith("CAPITAL_MARGIN_GATE_"), token


def test_banned_output_names_pinned():
    text = _read()
    for banned in BANNED_NAMES:
        assert banned in text, f"banned output name must be pinned as prohibited: {banned}"


def test_deferred_decisions():
    low = _read().lower()
    for token in [
        "order sizing / allocation",
        "order routing / execution",
        "margin requirement modelling",
        "leverage / notional / fee computation",
        "multi-account / cross-margin netting",
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
                 "no solvency guarantee", "no capital-correctness guarantee",
                 "no balance-truth guarantee", "no margin-correctness guarantee"]:
        assert term in low, f"no-claims term missing: {term}"
    assert ("a passed capital sufficiency gate is still only an explicit-evidence-filtered "
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
