"""tests/test_phase5_capital_margin_evidence_boundary.py — pins both slices of the
`phase5_capital_margin_evidence_boundary` component.

Slice 1: `CapitalMarginEvidenceContext` is a frozen, repr-safe, anti-truthiness, anti-coercion,
factory-only, slotted carrier that wraps only explicitly supplied capital/margin evidence. Every
user-supplied field is an exact, non-empty, non-whitespace ``str`` stored verbatim — the carrier
performs NO numeric / magnitude / epoch parsing or validation, NO comparison, NO derivation, and NO
decision. It is strictly a supplied-evidence descriptor; the capital/margin boundary is a ledger
auditor, and that audit belongs entirely to the gate.

Slice 2: `CapitalMarginGate` / `capital_margin_preflight` is a pure/offline/deterministic capital
sufficiency ledger auditor over exactly one `PostProfitabilityEvidenceEnvelope`, one
`CapitalMarginEvidenceContext`, and one `expected_capital_scope_id` control scalar. Outputs are
exactly: the identical envelope (valid + identity-bound + unit-bound + fresh + sufficient), an existing
`BlockedPacket` (missing / malformed / identity-mismatch / unit-mismatch / stale supplied evidence), or
an existing `NoEligibleHaltPacket` (valid bound fresh evidence whose free capital is zero or below the
required capital). A programmatic wrong-path / misroute raises and never produces a packet. The Slice 1
carrier surface is unchanged by Slice 2.
"""
import operator

import pytest

from phase5.capital_margin_evidence_boundary import (
    CapitalMarginEvidenceContext,
    make_capital_margin_evidence_context,
    CapitalMarginEvidenceContextTypeError,
    CAPITAL_MARGIN_EVIDENCE_BOUNDARY_COMPONENT_NAME,
    BOUNDARY_VERSION,
)

EXPECTED_COMPONENT = "phase5_capital_margin_evidence_boundary"

EXPECTED_FIELDS = (
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
)

# the 20 user-supplied fields the factory accepts (every field except component_name)
USER_SUPPLIED_FIELDS = tuple(f for f in EXPECTED_FIELDS if f != "component_name")


def _kwargs(**overrides):
    base = dict(
        venue="HYPERLIQUID",
        instrument_id="BTC-PERP",
        base_asset="BTC",
        quote_asset="USD",
        side="LONG",
        observed_size="1.5",
        observed_size_unit="BTC",
        required_capital="1500",
        required_capital_unit="USD",
        available_free_capital="5000",
        available_free_capital_unit="USD",
        required_capital_epoch_ms="1781637248000",
        available_free_capital_snapshot_epoch_ms="1781637248000",
        evidence_epoch_tolerance_ms="60000",
        capital_scope_id="ACCOUNT-MAIN",
        source_contract="phase5_capital_margin_evidence_boundary_implementation_planning.md",
        source_artifact="docs/handoff/phase5_capital_margin_evidence_boundary_implementation_planning.md",
        source_field="capital_evidence.free_capital",
        capital_evidence_id="CAP-001",
        boundary_version=BOUNDARY_VERSION,
    )
    base.update(overrides)
    return base


def _make(**overrides):
    return make_capital_margin_evidence_context(**_kwargs(**overrides))


def _src():
    import phase5.capital_margin_evidence_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        return f.read()


# --- constants / shape ---

def test_component_constant_and_boundary_version():
    assert CAPITAL_MARGIN_EVIDENCE_BOUNDARY_COMPONENT_NAME == EXPECTED_COMPONENT
    assert BOUNDARY_VERSION == "phase5.capital_margin_evidence_boundary.v0"


def test_factory_builds_carrier_with_exact_field_set_and_component_name():
    ctx = _make()
    assert type(ctx) is CapitalMarginEvidenceContext
    assert ctx.component_name == EXPECTED_COMPONENT
    for f in EXPECTED_FIELDS:
        assert hasattr(ctx, f), f"missing field {f}"


def test_declared_field_order_is_the_closed_21_set():
    from dataclasses import fields as dataclass_fields
    assert tuple(f.name for f in dataclass_fields(CapitalMarginEvidenceContext)) == EXPECTED_FIELDS
    assert len(EXPECTED_FIELDS) == 21


def test_field_values_preserved_verbatim():
    kw = _kwargs()
    ctx = make_capital_margin_evidence_context(**kw)
    for f in USER_SUPPLIED_FIELDS:
        assert getattr(ctx, f) == kw[f]


# --- factory discipline ---

def test_factory_is_keyword_only():
    with pytest.raises(TypeError):
        make_capital_margin_evidence_context("HYPERLIQUID")  # positional → TypeError


def test_component_name_is_not_a_factory_parameter():
    with pytest.raises(TypeError):
        make_capital_margin_evidence_context(**_kwargs(component_name="x"))


# --- direct construction is physically blocked (all forms) ---

def test_direct_no_arg_construction_blocked():
    with pytest.raises(TypeError):
        CapitalMarginEvidenceContext()


def test_direct_positional_construction_blocked():
    with pytest.raises(TypeError):
        CapitalMarginEvidenceContext("HYPERLIQUID")


def test_direct_keyword_construction_blocked():
    with pytest.raises(TypeError):
        CapitalMarginEvidenceContext(component_name="x")


# --- strict memory discipline: slots, no __dict__, no dynamic attribute injection ---

def test_instance_has_no_dict():
    ctx = _make()
    assert not hasattr(ctx, "__dict__"), "carrier must be slotted with no instance __dict__"


def test_dynamic_attribute_injection_rejected():
    ctx = _make()
    with pytest.raises((AttributeError, TypeError)):
        ctx.injected_attr = "x"


# --- string field discipline (uniform: exact non-empty non-whitespace str, verbatim) ---

def test_all_user_fields_must_be_exact_str_type_error():
    for f in USER_SUPPLIED_FIELDS:
        for bad in [None, 1, 1.0, 1j, b"x", {}, [], (), object(), True, False]:
            with pytest.raises(CapitalMarginEvidenceContextTypeError):
                _make(**{f: bad})


def test_string_fields_reject_str_subclass():
    class _S(str):
        pass
    for f in USER_SUPPLIED_FIELDS:
        with pytest.raises(CapitalMarginEvidenceContextTypeError):
            _make(**{f: _S("X")})


def test_string_fields_reject_duck_typed_string_like():
    class _DuckStr:
        def __str__(self):
            return "looks-like-a-string"
    for f in USER_SUPPLIED_FIELDS:
        with pytest.raises(CapitalMarginEvidenceContextTypeError):
            _make(**{f: _DuckStr()})


def test_empty_or_whitespace_string_fields_value_error():
    for f in USER_SUPPLIED_FIELDS:
        for bad in ["", "   ", "\t", "\n", " \t\n "]:
            with pytest.raises(ValueError):
                _make(**{f: bad})


def test_carrier_does_no_numeric_or_epoch_validation_stores_verbatim():
    # Slice 1 carrier performs NO numeric/magnitude/epoch parsing: any non-empty, non-whitespace str is
    # accepted and preserved verbatim (all validation belongs to the gate, not the carrier).
    for f in ("observed_size", "required_capital", "available_free_capital",
              "required_capital_epoch_ms", "available_free_capital_snapshot_epoch_ms",
              "evidence_epoch_tolerance_ms"):
        for weird in ["abc", "1.0e3", "-5", "0", "NaN", "1,000", "01", "banana", "Infinity"]:
            ctx = _make(**{f: weird})
            assert getattr(ctx, f) == weird, f"{f}={weird!r} must be stored verbatim"


# --- immutability ---

def test_carrier_is_frozen():
    ctx = _make()
    with pytest.raises(Exception):
        ctx.venue = "OTHER"
    with pytest.raises(Exception):
        ctx.component_name = "x"


# --- anti-truthiness / anti-coercion ---

def test_anti_truthiness():
    ctx = _make()
    with pytest.raises(TypeError):
        bool(ctx)
    with pytest.raises(TypeError):
        len(ctx)


def test_anti_coercion():
    ctx = _make()
    for op in (int, float, complex, str, bytes):
        with pytest.raises(TypeError):
            op(ctx)
    with pytest.raises(TypeError):
        operator.index(ctx)


# --- safe repr ---

def test_repr_exposes_only_safe_identifier_fields():
    ctx = _make(
        venue="SECRETVENUE",
        instrument_id="SECRETINSTR",
        base_asset="SECRETBASE",
        quote_asset="SECRETQUOTE",
        side="SECRETSIDE",
        observed_size="SECRETSIZE",
        observed_size_unit="SECRETSZUNIT",
        required_capital="SECRETREQCAP",
        required_capital_unit="SECRETREQUNIT",
        available_free_capital="SECRETFREECAP",
        available_free_capital_unit="SECRETFREEUNIT",
        required_capital_epoch_ms="SECRETREQEPOCH",
        available_free_capital_snapshot_epoch_ms="SECRETFREEEPOCH",
        evidence_epoch_tolerance_ms="SECRETTOL",
        capital_scope_id="SECRETSCOPE",
        source_contract="SECRETCONTRACT.md",
        source_artifact="docs/handoff/SECRETARTIFACT.md",
        source_field="SECRETFIELD",
        capital_evidence_id="SECRETCAPID",
    )
    text = repr(ctx)
    assert EXPECTED_COMPONENT in text
    for leak in ["SECRETVENUE", "SECRETINSTR", "SECRETBASE", "SECRETQUOTE", "SECRETSIDE",
                 "SECRETSIZE", "SECRETSZUNIT", "SECRETREQCAP", "SECRETREQUNIT", "SECRETFREECAP",
                 "SECRETFREEUNIT", "SECRETREQEPOCH", "SECRETFREEEPOCH", "SECRETTOL", "SECRETSCOPE",
                 "SECRETCONTRACT", "SECRETARTIFACT", "SECRETFIELD", "SECRETCAPID"]:
        assert leak not in text, f"repr leaked sensitive value: {leak}"


def test_error_messages_do_not_leak_raw_field_values():
    class _Leaky:
        def __repr__(self):
            return "LEAKYVALUE-XYZ"
        def __str__(self):
            return "LEAKYVALUE-XYZ"
    try:
        _make(venue=_Leaky())
        assert False, "expected a type error"
    except CapitalMarginEvidenceContextTypeError as e:
        assert "LEAKYVALUE-XYZ" not in str(e), "type-error message must not leak the raw value"
        assert "venue" in str(e)


# ===========================================================================================
# Slice 2 — CapitalMarginGate / capital_margin_preflight
# ===========================================================================================
import ast

from phase5.capital_margin_evidence_boundary import (
    CapitalMarginGate,
    capital_margin_preflight,
    CapitalMarginGateTypeError,
    MisroutedHaltCarrierError,
    CAPITAL_MARGIN_GATE_BLOCKED_MISSING_CAPITAL_EVIDENCE,
    CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE,
    CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH,
    CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH,
    CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE,
    CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL,
)
from phase5.post_profitability_evidence_envelope_boundary import (
    PostProfitabilityEvidenceEnvelope,
)
from phase5.blocked_result_boundary import BlockedPacket
from phase5.no_eligible_halt_propagation_boundary import NoEligibleHaltPacket


_GATE_MARKER = "# ===PHASE5-SLICE2-GATE-BOUNDARY==="

_GATE_DEF_NAMES = frozenset({
    "reject_misrouted_capital_halt_carrier",
    "_capital_gate_blocked",
    "_capital_gate_no_eligible",
    "_capital_is_canonical_unsigned_decimal",
    "_capital_is_canonical_unsigned_int",
    "capital_margin_preflight",
    "CapitalMarginGate",
})

REASON_TOKENS = (
    "CAPITAL_MARGIN_GATE_BLOCKED_MISSING_CAPITAL_EVIDENCE",
    "CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE",
    "CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH",
    "CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH",
    "CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE",
    "CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL",
)


def _carrier_region():
    return _src().split(_GATE_MARKER)[0]


def _gate_region():
    parts = _src().split(_GATE_MARKER)
    assert len(parts) == 2, "the Slice 2 gate boundary marker must appear exactly once"
    return parts[1]


def _gate_def_nodes():
    tree = ast.parse(_src())
    return [n for n in tree.body if getattr(n, "name", None) in _GATE_DEF_NAMES]


# --- symbol presence + the gate namespace ---

def test_gate_and_preflight_symbols_present_in_runtime_module():
    import phase5.capital_margin_evidence_boundary as mod
    assert hasattr(mod, "CapitalMarginGate"), "Slice 2 must define the gate class"
    assert hasattr(mod, "capital_margin_preflight"), "Slice 2 must define the preflight"
    # the gate is a stateless namespace whose static method IS the preflight function
    assert mod.CapitalMarginGate.preflight is mod.capital_margin_preflight
    assert getattr(mod.CapitalMarginGate, "__slots__", None) == ()


def test_preflight_is_keyword_only():
    with pytest.raises(TypeError):
        capital_margin_preflight(_env(), _cap(), "ACCOUNT-MAIN")  # positional → TypeError


# --- exactly the six reason tokens, no extras ---

def test_exactly_six_reason_tokens_no_extras():
    import phase5.capital_margin_evidence_boundary as mod
    present = {n for n in dir(mod) if n.startswith("CAPITAL_MARGIN_GATE_")}
    assert present == set(REASON_TOKENS), f"reason token set drift: {present}"


def test_reason_token_values_are_their_own_names():
    assert CAPITAL_MARGIN_GATE_BLOCKED_MISSING_CAPITAL_EVIDENCE == \
        "CAPITAL_MARGIN_GATE_BLOCKED_MISSING_CAPITAL_EVIDENCE"
    assert CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE == \
        "CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE"
    assert CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH == \
        "CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH"
    assert CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH == "CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH"
    assert CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE == "CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE"
    assert CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL == \
        "CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL"


# --- Slice 1 carrier backward-compatibility lock (Slice 2 must not weaken the carrier) ---

def test_carrier_surface_unchanged_after_gate_added():
    from dataclasses import fields as dataclass_fields
    assert tuple(f.name for f in dataclass_fields(CapitalMarginEvidenceContext)) == EXPECTED_FIELDS
    assert len(EXPECTED_FIELDS) == 21
    # still frozen, slotted, factory-only, verbatim, anti-coercion
    ctx = _make(required_capital="banana", available_free_capital="-9")
    assert ctx.required_capital == "banana"          # verbatim, no validation in carrier
    assert ctx.available_free_capital == "-9"
    assert not hasattr(ctx, "__dict__")              # slotted
    with pytest.raises(Exception):
        ctx.venue = "OTHER"                          # frozen
    with pytest.raises(TypeError):
        bool(ctx)                                    # anti-truthiness
    with pytest.raises(TypeError):
        int(ctx)                                     # anti-coercion
    with pytest.raises(TypeError):
        CapitalMarginEvidenceContext(venue="x")      # direct construction blocked


def test_carrier_component_name_still_fixed_internally():
    with pytest.raises(TypeError):
        make_capital_margin_evidence_context(**_kwargs(component_name="x"))
    assert _make().component_name == EXPECTED_COMPONENT


def test_carrier_repr_still_safe_only_component_name_and_boundary_version():
    text = repr(_make(venue="SECRETV", required_capital="SECRETRC",
                      available_free_capital="SECRETFC", capital_scope_id="SECRETSCOPE"))
    assert EXPECTED_COMPONENT in text
    for leak in ("SECRETV", "SECRETRC", "SECRETFC", "SECRETSCOPE"):
        assert leak not in text


def test_carrier_has_no_decision_helper_methods_or_properties():
    for name in ["is_sufficient", "is_valid", "has_funds", "has_capital", "is_stale", "is_eligible",
                 "is_tradable", "can_pass", "can_trade", "order_ready", "actionable", "executable",
                 "preflight", "to_dict", "as_dict", "model_dump"]:
        assert not hasattr(CapitalMarginEvidenceContext, name), \
            f"carrier must not expose decision/serialization helper: {name}"


# --- region purity locks ---

def test_runtime_uses_no_isinstance_validation():
    assert "isinstance(" not in _src(), "module must use exact type(value) is ..., never isinstance"


def test_carrier_region_has_no_packet_envelope_or_decision_logic():
    # everything BEFORE the Slice 2 marker stays a pure supplied-evidence descriptor
    carrier = _carrier_region()
    low = carrier.lower()
    assert "make_blocked_packet" not in low
    assert "make_no_eligible_halt_packet" not in low
    assert "BlockedPacket" not in carrier
    assert "NoEligibleHaltPacket" not in carrier
    assert "PostProfitabilityEvidenceEnvelope" not in carrier
    assert "preflight" not in low
    assert "class CapitalMarginGate" not in carrier
    assert "CAPITAL_MARGIN_GATE_" not in carrier


def test_carrier_region_has_no_arithmetic_clock_or_network_debris():
    low = _carrier_region().lower()
    for forbidden in [
        "float(", "decimal", "import re", "<=", ">=", ">", "abs(",
        "import os", "import time", "import datetime", "datetime.", "time.time(", ".now(",
        "utcnow", "monotonic", "import socket", "urllib", "requests.", "import json",
        "subprocess.", "open(", "fetch", "polling",
    ]:
        assert forbidden not in low, f"carrier region debris token present: {forbidden}"


def test_source_scan_no_banned_output_names():
    src = _src()
    for banned in ["ActionableCandidate", "TradeCandidate", "ReadyEnvelope", "ExecutableSignal",
                   "Opportunity", "ExecutionPayload", "OrderIntent", "Fillable", "Tradable"]:
        assert banned not in src, f"banned output/actionability name present in runtime: {banned}"


def test_gate_does_not_read_carrier_provenance_id_or_boundary_version():
    gate = _gate_region()
    for banned_attr in [".source_contract", ".source_artifact", ".source_field",
                        ".capital_evidence_id", ".boundary_version"]:
        assert "capital_evidence" + banned_attr not in gate, \
            f"gate must not read capital_evidence{banned_attr} for packet provenance"


def test_gate_region_has_no_clock_network_fetch_retry_polling():
    gate = _gate_region().lower()
    for forbidden in ["import os", "import time", "import datetime", "datetime.", "time.time(",
                      ".now(", "utcnow", "monotonic", "perf_counter", "import socket", "urllib",
                      "requests.", "import http", "import json", "subprocess.", "import random",
                      "fetch", "polling", "sleep(", "wallet", "balance("]:
        assert forbidden not in gate, f"gate clock/network debris token present: {forbidden}"


def test_gate_region_has_no_sizing_routing_execution_actionability():
    gate = _gate_region().lower()
    for forbidden in ["partial fill", "partial_fill", "reduced size", "reduced_size",
                      "allocation", "order quantity", "order_quantity", "order_intent",
                      "order intent", "order_ready", "routing", "route(", "execution",
                      "executable", "paper", "canary", "sizing", "actionable", "reservation",
                      "notional", "leverage", "margin formula", "margin_formula"]:
        assert forbidden not in gate, f"gate sizing/routing/execution debris token present: {forbidden}"


def test_gate_region_has_no_net_edge_profitability_or_threshold_arithmetic():
    # bare "profitability" is NOT banned (the upstream-envelope import carries it); only decisioning
    # forms are forbidden
    gate = _gate_region().lower()
    for forbidden in ["net_edge", "net edge", "threshold", "malformed_threshold",
                      "pnl", "kelly", "fee(", "price(", "float("]:
        assert forbidden not in gate, f"gate net-edge/profitability/threshold token present: {forbidden}"


def test_gate_uses_only_allowed_comparison_and_arithmetic_operators():
    lte = lt = gt = gte = 0
    binops = []
    abs_calls = 0
    for gn in _gate_def_nodes():
        for node in ast.walk(gn):
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    if isinstance(op, ast.LtE):
                        lte += 1
                    elif isinstance(op, ast.Lt):
                        lt += 1
                    elif isinstance(op, ast.Gt):
                        gt += 1
                    elif isinstance(op, ast.GtE):
                        gte += 1
            elif isinstance(node, ast.BinOp):
                binops.append(type(node.op))
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                  and node.func.id == "abs"):
                abs_calls += 1
    assert gt == 0 and gte == 0, "gate must use no > or >= comparisons"
    assert lte == 5, f"gate must use exactly five <= equations, found {lte}"
    assert lt == 1, f"gate must use exactly one < comparison (available_free_capital < 0), found {lt}"
    assert binops == [ast.Sub, ast.Sub], f"gate arithmetic is limited to two subtractions, found {binops}"
    assert abs_calls == 2, f"gate must call abs() exactly twice (two staleness axes), found {abs_calls}"


# --- Slice 2 behaviour: helpers ---

def _env(**overrides):
    """An exact PostProfitabilityEvidenceEnvelope built low-level (the gate reads only its explicit
    allow-listed fields; calculation_result is never inspected)."""
    fields = dict(
        component_name="phase5_post_profitability_evidence_envelope_boundary",
        calculation_result=object(),
        venue="HYPERLIQUID",
        instrument_id="BTC-PERP",
        base_asset="BTC",
        quote_asset="USD",
        side="LONG",
        observed_size="1.5",
        size_unit="BTC",
        observed_at_epoch_ms="1781637248000",
        staleness_threshold_ms="60000",
        source_contract="ENV_C",
        source_artifact="docs/handoff/ENV_A.md",
        source_field="evidence_envelope.market_topology",
        boundary_version="phase5.post_profitability_evidence_envelope_boundary.v0",
    )
    fields.update(overrides)
    env = object.__new__(PostProfitabilityEvidenceEnvelope)
    for k, v in fields.items():
        object.__setattr__(env, k, v)
    return env


def _cap(**overrides):
    """A valid CapitalMarginEvidenceContext via its real factory (bound to the default envelope)."""
    return _make(**overrides)


def _bypassed_cap(drop=None, **overrides):
    """An exact carrier via object.__new__ (factory bypassed) so a decision field can be omitted or
    set to an empty/malformed value the real factory would reject."""
    fields = dict(
        component_name=EXPECTED_COMPONENT,
        venue="HYPERLIQUID",
        instrument_id="BTC-PERP",
        base_asset="BTC",
        quote_asset="USD",
        side="LONG",
        observed_size="1.5",
        observed_size_unit="BTC",
        required_capital="1500",
        required_capital_unit="USD",
        available_free_capital="5000",
        available_free_capital_unit="USD",
        required_capital_epoch_ms="1781637248000",
        available_free_capital_snapshot_epoch_ms="1781637248000",
        evidence_epoch_tolerance_ms="60000",
        capital_scope_id="ACCOUNT-MAIN",
        source_contract="CAP_C",
        source_artifact="docs/handoff/CAP_A.md",
        source_field="capital_evidence.free_capital",
        capital_evidence_id="CAP-001",
        boundary_version=BOUNDARY_VERSION,
    )
    fields.update(overrides)
    if drop is not None:
        del fields[drop]
    obj = object.__new__(CapitalMarginEvidenceContext)
    for k, v in fields.items():
        object.__setattr__(obj, k, v)
    return obj


def _call(**overrides):
    env_over = overrides.pop("env", {})
    cap_over = overrides.pop("cap", {})
    scope = overrides.pop("expected_capital_scope_id", "ACCOUNT-MAIN")
    return capital_margin_preflight(
        evidence_envelope=_env(**env_over),
        capital_evidence=_cap(**cap_over),
        expected_capital_scope_id=scope,
    )


# --- branch priority 1: misroute ---

def test_misrouted_halt_carrier_as_envelope_raises():
    for halt in (object.__new__(BlockedPacket), object.__new__(NoEligibleHaltPacket)):
        with pytest.raises(MisroutedHaltCarrierError):
            capital_margin_preflight(evidence_envelope=halt, capital_evidence=_cap(),
                                     expected_capital_scope_id="ACCOUNT-MAIN")


def test_misrouted_halt_carrier_as_capital_evidence_raises():
    for halt in (object.__new__(BlockedPacket), object.__new__(NoEligibleHaltPacket)):
        with pytest.raises(MisroutedHaltCarrierError):
            capital_margin_preflight(evidence_envelope=_env(), capital_evidence=halt,
                                     expected_capital_scope_id="ACCOUNT-MAIN")


def test_misroute_takes_priority_over_wrong_type():
    with pytest.raises(MisroutedHaltCarrierError):
        capital_margin_preflight(evidence_envelope=object.__new__(BlockedPacket),
                                 capital_evidence=object(),
                                 expected_capital_scope_id="ACCOUNT-MAIN")


# --- branch priority 2: exact-type + control-scalar checks ---

def test_wrong_type_envelope_raises_gate_type_error():
    for bad in (object(), {}, None, 5, "x", _cap()):
        with pytest.raises(CapitalMarginGateTypeError):
            capital_margin_preflight(evidence_envelope=bad, capital_evidence=_cap(),
                                     expected_capital_scope_id="ACCOUNT-MAIN")


def test_wrong_type_capital_evidence_raises_gate_type_error():
    for bad in (object(), {}, None, 5, "x", _env()):
        with pytest.raises(CapitalMarginGateTypeError):
            capital_margin_preflight(evidence_envelope=_env(), capital_evidence=bad,
                                     expected_capital_scope_id="ACCOUNT-MAIN")


def test_wrong_type_control_scalar_raises_gate_type_error():
    for bad in (None, 5, 1.0, b"x", {}, [], object(), True):
        with pytest.raises(CapitalMarginGateTypeError):
            capital_margin_preflight(evidence_envelope=_env(), capital_evidence=_cap(),
                                     expected_capital_scope_id=bad)


def test_empty_or_whitespace_control_scalar_raises_gate_type_error():
    for bad in ("", "   ", "\t", "\n"):
        with pytest.raises(CapitalMarginGateTypeError):
            capital_margin_preflight(evidence_envelope=_env(), capital_evidence=_cap(),
                                     expected_capital_scope_id=bad)


def test_control_scalar_str_subclass_rejected():
    class _S(str):
        pass
    with pytest.raises(CapitalMarginGateTypeError):
        capital_margin_preflight(evidence_envelope=_env(), capital_evidence=_cap(),
                                 expected_capital_scope_id=_S("ACCOUNT-MAIN"))


def test_envelope_subclass_rejected():
    class _EnvSub(PostProfitabilityEvidenceEnvelope):
        pass
    sub = object.__new__(_EnvSub)
    with pytest.raises(CapitalMarginGateTypeError):
        capital_margin_preflight(evidence_envelope=sub, capital_evidence=_cap(),
                                 expected_capital_scope_id="ACCOUNT-MAIN")


def test_capital_evidence_subclass_rejected():
    class _CapSub(CapitalMarginEvidenceContext):
        pass
    sub = object.__new__(_CapSub)
    with pytest.raises(CapitalMarginGateTypeError):
        capital_margin_preflight(evidence_envelope=_env(), capital_evidence=sub,
                                 expected_capital_scope_id="ACCOUNT-MAIN")


# --- branch priority 3: missing allow-listed capital evidence ---

def test_missing_capital_decision_field_blocks_missing():
    for field in ("venue", "instrument_id", "base_asset", "quote_asset", "side",
                  "observed_size", "observed_size_unit", "required_capital", "required_capital_unit",
                  "available_free_capital", "available_free_capital_unit",
                  "required_capital_epoch_ms", "available_free_capital_snapshot_epoch_ms",
                  "evidence_epoch_tolerance_ms", "capital_scope_id"):
        out = capital_margin_preflight(evidence_envelope=_env(),
                                       capital_evidence=_bypassed_cap(drop=field),
                                       expected_capital_scope_id="ACCOUNT-MAIN")
        assert type(out) is BlockedPacket, f"missing {field} should block"
        assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_MISSING_CAPITAL_EVIDENCE


# --- branch priority 4: malformed grammar / positivity ---

def test_malformed_observed_size_blocks_malformed():
    for bad in ["abc", "-5", "1e3", "1E3", "NaN", "Infinity", "-Infinity", "1_000", "1,000",
                "", "   ", "01", "1.", ".5", "+1", "0", "0.0"]:
        out = capital_margin_preflight(evidence_envelope=_env(),
                                       capital_evidence=_bypassed_cap(observed_size=bad),
                                       expected_capital_scope_id="ACCOUNT-MAIN")
        assert type(out) is BlockedPacket, f"observed_size={bad!r} should block"
        assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE


def test_malformed_or_nonpositive_required_capital_blocks_malformed():
    for bad in ["abc", "-1", "1e3", "NaN", "Infinity", "1_000", "1,000", "", "  ", "0", "0.0", "00"]:
        out = capital_margin_preflight(evidence_envelope=_env(),
                                       capital_evidence=_bypassed_cap(required_capital=bad),
                                       expected_capital_scope_id="ACCOUNT-MAIN")
        assert type(out) is BlockedPacket, f"required_capital={bad!r} should block as malformed"
        assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE


def test_malformed_or_negative_available_free_capital_blocks_malformed():
    # negative or malformed free capital is malformed (NOT NoEligible); "0" is handled separately
    for bad in ["abc", "-1", "-0.01", "1e3", "NaN", "Infinity", "1_000", "1,000", "", "  ", "01"]:
        out = capital_margin_preflight(evidence_envelope=_env(),
                                       capital_evidence=_bypassed_cap(available_free_capital=bad),
                                       expected_capital_scope_id="ACCOUNT-MAIN")
        assert type(out) is BlockedPacket, f"available_free_capital={bad!r} should block as malformed"
        assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE


def test_malformed_epoch_or_tolerance_blocks_malformed():
    for field in ("required_capital_epoch_ms", "available_free_capital_snapshot_epoch_ms",
                  "evidence_epoch_tolerance_ms"):
        for bad in ["abc", "-1", "1.0", "1e3", "", "  ", "1_000", "1,000", "+1", "01"]:
            out = capital_margin_preflight(evidence_envelope=_env(),
                                           capital_evidence=_bypassed_cap(**{field: bad}),
                                           expected_capital_scope_id="ACCOUNT-MAIN")
            assert type(out) is BlockedPacket, f"{field}={bad!r} should block"
            assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE


def test_tolerance_zero_is_valid_grammar_not_malformed():
    # tolerance "0" is valid; with identical epochs the diff is 0 <= 0 -> fresh -> proceeds to pass
    out = _call(cap={"evidence_epoch_tolerance_ms": "0"})
    assert type(out) is PostProfitabilityEvidenceEnvelope


def test_malformed_takes_priority_over_identity_mismatch():
    out = _call(cap={"required_capital": "abc", "venue": "OTHER"})
    assert type(out) is BlockedPacket
    assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE


# --- branch priority 5: identity mismatch (incl. side + size magnitude + scope) ---

def test_identity_string_mismatch_blocks_identity():
    for field in ("venue", "instrument_id", "base_asset", "quote_asset", "side"):
        out = _call(cap={field: "OTHER"})
        assert type(out) is BlockedPacket, f"{field} mismatch should block identity"
        assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH


def test_side_mismatch_is_identity_mismatch():
    out = capital_margin_preflight(evidence_envelope=_env(side="LONG"),
                                   capital_evidence=_cap(side="SHORT"),
                                   expected_capital_scope_id="ACCOUNT-MAIN")
    assert type(out) is BlockedPacket
    assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH


def test_observed_size_magnitude_mismatch_is_identity_mismatch():
    out = capital_margin_preflight(evidence_envelope=_env(observed_size="1.5"),
                                   capital_evidence=_cap(observed_size="1.7"),
                                   expected_capital_scope_id="ACCOUNT-MAIN")
    assert type(out) is BlockedPacket
    assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH


def test_observed_size_magnitude_compared_as_decimal_not_string():
    # "1.50" == "1.5" as a magnitude: NOT an identity mismatch
    out = capital_margin_preflight(evidence_envelope=_env(observed_size="1.5"),
                                   capital_evidence=_cap(observed_size="1.50"),
                                   expected_capital_scope_id="ACCOUNT-MAIN")
    assert type(out) is PostProfitabilityEvidenceEnvelope


def test_scope_mismatch_is_identity_mismatch():
    out = _call(cap={"capital_scope_id": "ACCOUNT-MAIN"},
                expected_capital_scope_id="ACCOUNT-OTHER")
    assert type(out) is BlockedPacket
    assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH


def test_identity_mismatch_takes_priority_over_unit_mismatch():
    out = _call(cap={"venue": "OTHER", "observed_size_unit": "ETH"})
    assert type(out) is BlockedPacket
    assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH


# --- branch priority 6: unit mismatch ---

def test_size_unit_vs_observed_size_unit_mismatch_blocks_unit():
    out = _call(env={"size_unit": "BTC"}, cap={"observed_size_unit": "ETH"})
    assert type(out) is BlockedPacket
    assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH


def test_required_unit_vs_free_unit_mismatch_blocks_unit():
    out = _call(cap={"required_capital_unit": "USD", "available_free_capital_unit": "USDC"})
    assert type(out) is BlockedPacket
    assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH


def test_unit_mismatch_takes_priority_over_stale():
    out = _call(env={"observed_at_epoch_ms": "1000"},
                cap={"required_capital_unit": "USD", "available_free_capital_unit": "USDC",
                     "required_capital_epoch_ms": "999999",
                     "available_free_capital_snapshot_epoch_ms": "999999",
                     "evidence_epoch_tolerance_ms": "1"})
    assert type(out) is BlockedPacket
    assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH


# --- branch priority 7: staleness (two independent axes) ---

def test_required_capital_epoch_stale_blocks_stale():
    out = _call(env={"observed_at_epoch_ms": "1000"},
                cap={"required_capital_epoch_ms": "100000",
                     "available_free_capital_snapshot_epoch_ms": "1000",
                     "evidence_epoch_tolerance_ms": "50"})
    assert type(out) is BlockedPacket
    assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE


def test_free_capital_snapshot_epoch_stale_blocks_stale():
    out = _call(env={"observed_at_epoch_ms": "1000"},
                cap={"required_capital_epoch_ms": "1000",
                     "available_free_capital_snapshot_epoch_ms": "100000",
                     "evidence_epoch_tolerance_ms": "50"})
    assert type(out) is BlockedPacket
    assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE


def test_fresh_at_exact_tolerance_is_not_stale():
    # |1000 - 1100| == 100 == tolerance -> inclusive, fresh -> proceeds to a sufficient pass
    out = _call(env={"observed_at_epoch_ms": "1000"},
                cap={"required_capital_epoch_ms": "1100",
                     "available_free_capital_snapshot_epoch_ms": "900",
                     "evidence_epoch_tolerance_ms": "100"})
    assert type(out) is PostProfitabilityEvidenceEnvelope


def test_stale_takes_priority_over_insufficient_capital():
    out = _call(env={"observed_at_epoch_ms": "1000"},
                cap={"required_capital": "5000", "available_free_capital": "10",
                     "required_capital_epoch_ms": "100000",
                     "available_free_capital_snapshot_epoch_ms": "1000",
                     "evidence_epoch_tolerance_ms": "50"})
    assert type(out) is BlockedPacket
    assert out.reason_code == CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE


# --- branch priority 8/9: insufficient vs sufficient capital ---

def test_zero_free_capital_is_no_eligible_not_blocked():
    out = _call(cap={"available_free_capital": "0"})
    assert type(out) is NoEligibleHaltPacket
    assert out.no_eligible_reason == CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL


def test_insufficient_positive_capital_is_no_eligible():
    out = _call(cap={"required_capital": "5000", "available_free_capital": "10"})
    assert type(out) is NoEligibleHaltPacket
    assert out.no_eligible_reason == CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL


def test_equal_capital_is_sufficient_and_passes_by_identity():
    env = _env()
    out = capital_margin_preflight(evidence_envelope=env,
                                   capital_evidence=_cap(required_capital="5000",
                                                         available_free_capital="5000"),
                                   expected_capital_scope_id="ACCOUNT-MAIN")
    assert out is env  # inclusive: equal capital is sufficient


def test_sufficient_capital_returns_same_envelope_by_identity():
    env = _env()
    out = capital_margin_preflight(evidence_envelope=env, capital_evidence=_cap(),
                                   expected_capital_scope_id="ACCOUNT-MAIN")
    assert out is env


def test_capital_compared_as_decimal_not_string():
    # "1000.0" required <= "1000" free as Decimal magnitudes -> sufficient
    env = _env()
    out = capital_margin_preflight(evidence_envelope=env,
                                   capital_evidence=_cap(required_capital="1000.0",
                                                         available_free_capital="1000"),
                                   expected_capital_scope_id="ACCOUNT-MAIN")
    assert out is env


# --- packet provenance (envelope-only) + no raw value leakage ---

def test_blocked_packet_provenance_comes_only_from_envelope():
    env = _env(source_contract="ENV_ALPHA_C", source_artifact="ENV_ALPHA_A",
               source_field="ENV_ALPHA_F")
    out = capital_margin_preflight(
        evidence_envelope=env,
        capital_evidence=_cap(venue="OTHER", source_contract="CARRIER_BETA_C",
                              source_artifact="CARRIER_BETA_A", source_field="CARRIER_BETA_F"),
        expected_capital_scope_id="ACCOUNT-MAIN")
    assert type(out) is BlockedPacket
    assert (out.source_contract, out.source_artifact, out.source_field) == \
        ("ENV_ALPHA_C", "ENV_ALPHA_A", "ENV_ALPHA_F")


def test_no_eligible_provenance_comes_only_from_envelope():
    env = _env(source_contract="ENV_ALPHA_C", source_artifact="ENV_ALPHA_A",
               source_field="ENV_ALPHA_F")
    out = capital_margin_preflight(
        evidence_envelope=env,
        capital_evidence=_cap(required_capital="5000", available_free_capital="10",
                              source_contract="CARRIER_BETA_C", source_artifact="CARRIER_BETA_A",
                              source_field="CARRIER_BETA_F"),
        expected_capital_scope_id="ACCOUNT-MAIN")
    assert type(out) is NoEligibleHaltPacket
    assert (out.source_contract, out.source_artifact, out.source_field) == \
        ("ENV_ALPHA_C", "ENV_ALPHA_A", "ENV_ALPHA_F")


def test_carrier_provenance_sentinel_never_leaks_into_packets():
    env = _env(source_contract="ENV_ALPHA_C", source_artifact="ENV_ALPHA_A",
               source_field="ENV_ALPHA_F")
    # NoEligible: required magnitude sentinel huge, free tiny
    out = capital_margin_preflight(
        evidence_envelope=env,
        capital_evidence=_cap(required_capital="999888.777", available_free_capital="55.5",
                              source_contract="CARRIER_BETA", source_artifact="CARRIER_BETA",
                              source_field="CARRIER_BETA", capital_evidence_id="CARRIER_BETA",
                              capital_scope_id="ACCOUNT-MAIN"),
        expected_capital_scope_id="ACCOUNT-MAIN")
    assert type(out) is NoEligibleHaltPacket
    blob = " ".join([
        repr(out),
        str(out.no_eligible_reason),
        str(out.source_contract), str(out.source_artifact), str(out.source_field),
        str(out.deterministic_next_action),
    ])
    for leak in ("999888.777", "55.5", "CARRIER_BETA"):
        assert leak not in blob, f"packet leaked raw/carrier value: {leak}"


def test_blocked_packet_does_not_leak_raw_values():
    out = capital_margin_preflight(
        evidence_envelope=_env(),
        capital_evidence=_bypassed_cap(required_capital="999888.777", venue="CARRIER_VENUE_BETA"),
        expected_capital_scope_id="ACCOUNT-MAIN")
    assert type(out) is BlockedPacket
    blob = " ".join([
        repr(out),
        str(out.reason_code), str(out.missing_or_invalid_field),
        str(out.source_contract), str(out.source_artifact), str(out.source_field),
    ])
    for leak in ("999888.777", "CARRIER_VENUE_BETA"):
        assert leak not in blob, f"blocked packet leaked raw value: {leak}"


# --- inputs are never mutated ---

def test_inputs_are_not_mutated_on_pass():
    env = _env()
    cap = _cap()
    env_before = {f: getattr(env, f) for f in
                  ("venue", "instrument_id", "base_asset", "quote_asset", "side", "observed_size",
                   "size_unit", "observed_at_epoch_ms")}
    cap_before = {f: getattr(cap, f) for f in USER_SUPPLIED_FIELDS}
    out = capital_margin_preflight(evidence_envelope=env, capital_evidence=cap,
                                   expected_capital_scope_id="ACCOUNT-MAIN")
    assert out is env
    for f, v in env_before.items():
        assert getattr(env, f) == v, f"envelope.{f} mutated"
    for f, v in cap_before.items():
        assert getattr(cap, f) == v, f"capital_evidence.{f} mutated"


def test_inputs_are_not_mutated_on_block():
    cap = _cap(venue="OTHER")
    cap_before = {f: getattr(cap, f) for f in USER_SUPPLIED_FIELDS}
    out = capital_margin_preflight(evidence_envelope=_env(), capital_evidence=cap,
                                   expected_capital_scope_id="ACCOUNT-MAIN")
    assert type(out) is BlockedPacket
    for f, v in cap_before.items():
        assert getattr(cap, f) == v, f"capital_evidence.{f} mutated on block"
