"""tests/test_phase5_liquidity_capacity_evidence_boundary.py — pins the atomic implementation of
Slice 1 of the `phase5_liquidity_capacity_evidence_boundary` component:
`LiquidityCapacityEvidenceContext`.

`LiquidityCapacityEvidenceContext` is a frozen, repr-safe, anti-truthiness, anti-coercion,
factory-only carrier that wraps only explicitly supplied liquidity/depth capacity evidence. Every
user-supplied field is an exact, non-empty, non-whitespace ``str`` stored verbatim — the carrier
performs NO numeric/decimal/epoch parsing, NO comparison, NO derivation, and NO decision. It is
strictly a supplied-evidence descriptor. `estimated_slippage_bps` is passive metadata only.

Slice 1 scope: ONLY the carrier and its factory exist in the runtime module. The gate
(`LiquidityCapacityGate` / `liquidity_capacity_preflight`) is explicitly NOT implemented here, and no
upstream envelope or halt-carrier is imported, constructed, or referenced.
"""
import pytest

from phase5.liquidity_capacity_evidence_boundary import (
    LiquidityCapacityEvidenceContext,
    make_liquidity_capacity_evidence_context,
    LiquidityCapacityEvidenceContextTypeError,
    LIQUIDITY_CAPACITY_EVIDENCE_BOUNDARY_COMPONENT_NAME,
    BOUNDARY_VERSION,
)

EXPECTED_COMPONENT = "phase5_liquidity_capacity_evidence_boundary"

EXPECTED_FIELDS = (
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
)

# the 16 user-supplied fields the factory accepts (every field except component_name)
USER_SUPPLIED_FIELDS = tuple(f for f in EXPECTED_FIELDS if f != "component_name")


def _kwargs(**overrides):
    base = dict(
        venue="HYPERLIQUID",
        instrument_id="BTC-PERP",
        base_asset="BTC",
        quote_asset="USD",
        observed_size="1.5",
        observed_size_unit="BTC",
        available_capacity="10",
        capacity_unit="BTC",
        liquidity_snapshot_epoch_ms="1781637248000",
        evidence_epoch_tolerance_ms="60000",
        source_contract="phase5_liquidity_capacity_evidence_boundary_implementation_planning.md",
        source_artifact="docs/handoff/phase5_liquidity_capacity_evidence_boundary_implementation_planning.md",
        source_field="liquidity_evidence.capacity",
        liquidity_evidence_id="LIQ-001",
        boundary_version=BOUNDARY_VERSION,
        estimated_slippage_bps="2.5",
    )
    base.update(overrides)
    return base


def _make(**overrides):
    return make_liquidity_capacity_evidence_context(**_kwargs(**overrides))


# --- constants / shape ---

def test_component_constant_and_boundary_version():
    assert LIQUIDITY_CAPACITY_EVIDENCE_BOUNDARY_COMPONENT_NAME == EXPECTED_COMPONENT
    assert BOUNDARY_VERSION == "phase5.liquidity_capacity_evidence_boundary.v0"


def test_factory_builds_carrier_with_exact_field_set_and_component_name():
    ctx = _make()
    assert type(ctx) is LiquidityCapacityEvidenceContext
    assert ctx.component_name == EXPECTED_COMPONENT
    for f in EXPECTED_FIELDS:
        assert hasattr(ctx, f), f"missing field {f}"


def test_declared_field_order_is_the_closed_17_set():
    from dataclasses import fields as dataclass_fields
    assert tuple(f.name for f in dataclass_fields(LiquidityCapacityEvidenceContext)) == EXPECTED_FIELDS
    assert len(EXPECTED_FIELDS) == 17


def test_field_values_preserved_verbatim():
    kw = _kwargs()
    ctx = make_liquidity_capacity_evidence_context(**kw)
    for f in USER_SUPPLIED_FIELDS:
        assert getattr(ctx, f) == kw[f]


def test_factory_is_keyword_only():
    with pytest.raises(TypeError):
        make_liquidity_capacity_evidence_context("HYPERLIQUID")  # positional → TypeError


def test_component_name_is_not_a_factory_parameter():
    with pytest.raises(TypeError):
        make_liquidity_capacity_evidence_context(**_kwargs(component_name="x"))


def test_direct_positional_construction_unsupported():
    with pytest.raises(TypeError):
        LiquidityCapacityEvidenceContext("HYPERLIQUID")


# --- string field discipline (uniform: exact non-empty non-whitespace str, verbatim) ---

def test_all_user_fields_must_be_exact_str_type_error():
    for f in USER_SUPPLIED_FIELDS:
        for bad in [None, 1, 1.0, b"x", {}, [], object(), True]:
            with pytest.raises(LiquidityCapacityEvidenceContextTypeError):
                _make(**{f: bad})


def test_string_fields_reject_str_subclass():
    class _S(str):
        pass
    for f in USER_SUPPLIED_FIELDS:
        with pytest.raises(LiquidityCapacityEvidenceContextTypeError):
            _make(**{f: _S("X")})


def test_empty_or_whitespace_string_fields_value_error():
    for f in USER_SUPPLIED_FIELDS:
        for bad in ["", "   ", "\t", "\n"]:
            with pytest.raises(ValueError):
                _make(**{f: bad})


def test_carrier_does_no_numeric_validation_stores_magnitudes_verbatim():
    # Slice 1 carrier performs NO numeric/decimal/epoch parsing: any non-empty, non-whitespace str is
    # accepted and preserved verbatim (format validation belongs to the future gate, not the carrier).
    for f in ("observed_size", "available_capacity", "estimated_slippage_bps",
              "liquidity_snapshot_epoch_ms", "evidence_epoch_tolerance_ms"):
        for weird in ["abc", "1.0e3", "-5", "0", "NaN", "1,000", "01"]:
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
        import operator
        operator.index(ctx)


# --- safe repr ---

def test_repr_exposes_only_safe_identifier_fields():
    ctx = _make(
        venue="SECRETVENUE",
        instrument_id="SECRETINSTR",
        base_asset="SECRETBASE",
        quote_asset="SECRETQUOTE",
        observed_size="SECRETSIZE",
        observed_size_unit="SECRETSZUNIT",
        available_capacity="SECRETCAP",
        capacity_unit="SECRETCAPUNIT",
        liquidity_snapshot_epoch_ms="SECRETEPOCH",
        evidence_epoch_tolerance_ms="SECRETTOL",
        source_contract="SECRETCONTRACT.md",
        source_artifact="docs/handoff/SECRETARTIFACT.md",
        source_field="SECRETFIELD",
        liquidity_evidence_id="SECRETLIQID",
        estimated_slippage_bps="SECRETSLIP",
    )
    text = repr(ctx)
    assert EXPECTED_COMPONENT in text
    for leak in ["SECRETVENUE", "SECRETINSTR", "SECRETBASE", "SECRETQUOTE", "SECRETSIZE",
                 "SECRETSZUNIT", "SECRETCAP", "SECRETCAPUNIT", "SECRETEPOCH", "SECRETTOL",
                 "SECRETCONTRACT", "SECRETARTIFACT", "SECRETFIELD", "SECRETLIQID", "SECRETSLIP"]:
        assert leak not in text, f"repr leaked sensitive value: {leak}"


# --- estimated_slippage_bps is passive: stored verbatim, never interpreted ---

def test_estimated_slippage_bps_stored_verbatim_as_passive_metadata():
    ctx = _make(estimated_slippage_bps="7.25")
    assert ctx.estimated_slippage_bps == "7.25"


# --- carrier/gate separation guards (the carrier stays pure; the gate is now present) ---

import ast

from phase5.liquidity_capacity_evidence_boundary import (
    LiquidityCapacityGate,
    liquidity_capacity_preflight,
    LiquidityCapacityGateTypeError,
    MisroutedHaltCarrierError,
    LIQUIDITY_CAPACITY_GATE_BLOCKED_MISSING_LIQUIDITY_EVIDENCE,
    LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE,
    LIQUIDITY_CAPACITY_GATE_BLOCKED_IDENTITY_MISMATCH,
    LIQUIDITY_CAPACITY_GATE_BLOCKED_UNIT_MISMATCH,
    LIQUIDITY_CAPACITY_GATE_BLOCKED_STALE_EVIDENCE,
    LIQUIDITY_CAPACITY_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPACITY,
)
from phase5.post_profitability_evidence_envelope_boundary import (
    PostProfitabilityEvidenceEnvelope,
)
from phase5.blocked_result_boundary import BlockedPacket
from phase5.no_eligible_halt_propagation_boundary import NoEligibleHaltPacket


_GATE_MARKER = "# ===PHASE5-SLICE2-GATE-BOUNDARY==="

_GATE_DEF_NAMES = frozenset({
    "reject_misrouted_halt_carrier",
    "_gate_blocked",
    "_gate_no_eligible",
    "_is_canonical_unsigned_decimal",
    "_is_canonical_unsigned_int",
    "liquidity_capacity_preflight",
    "LiquidityCapacityGate",
})


def _module_source():
    import phase5.liquidity_capacity_evidence_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        return f.read()


def _carrier_region():
    return _module_source().split(_GATE_MARKER)[0]


def _gate_region():
    parts = _module_source().split(_GATE_MARKER)
    assert len(parts) == 2, "the Slice 2 gate boundary marker must appear exactly once"
    return parts[1]


def _gate_def_nodes():
    tree = ast.parse(_module_source())
    return [n for n in tree.body if getattr(n, "name", None) in _GATE_DEF_NAMES]


def test_gate_and_preflight_symbols_present_in_runtime_module():
    import phase5.liquidity_capacity_evidence_boundary as mod
    assert hasattr(mod, "LiquidityCapacityGate"), "Slice 2 must define the gate class"
    assert hasattr(mod, "liquidity_capacity_preflight"), "Slice 2 must define the preflight"
    # the gate is a stateless namespace whose static method IS the preflight function
    assert mod.LiquidityCapacityGate.preflight is mod.liquidity_capacity_preflight
    assert getattr(mod.LiquidityCapacityGate, "__slots__", None) == ()


def test_carrier_surface_unchanged_after_gate_added():
    # the closed 17-field contract, factory, and verbatim/passive storage are untouched by Slice 2
    from dataclasses import fields as dataclass_fields
    assert tuple(f.name for f in dataclass_fields(LiquidityCapacityEvidenceContext)) == EXPECTED_FIELDS
    ctx = _make(observed_size="1.5", available_capacity="10", estimated_slippage_bps="banana")
    assert ctx.observed_size == "1.5"
    assert ctx.available_capacity == "10"
    assert ctx.estimated_slippage_bps == "banana"  # carrier still stores verbatim, no validation


def test_carrier_has_no_decision_helper_methods_or_properties():
    for name in ["is_tradable", "is_eligible", "is_sufficient", "is_stale", "can_pass",
                 "capacity_ok", "order_ready", "actionable", "executable", "preflight"]:
        assert not hasattr(LiquidityCapacityEvidenceContext, name), \
            f"carrier must not expose decision helper: {name}"


def test_carrier_region_has_no_packet_envelope_or_decision_logic():
    # everything BEFORE the Slice 2 marker must remain a pure supplied-evidence descriptor
    carrier = _carrier_region()
    low = carrier.lower()
    assert "make_blocked_packet" not in low
    assert "make_no_eligible_halt_packet" not in low
    assert "BlockedPacket" not in carrier
    assert "NoEligibleHaltPacket" not in carrier
    assert "PostProfitabilityEvidenceEnvelope" not in carrier
    assert "preflight" not in low
    assert "class LiquidityCapacityGate" not in carrier
    for name in ["is_tradable", "is_eligible", "is_sufficient", "is_stale", "can_pass",
                 "capacity_ok", "order_ready", "actionable", "executable"]:
        assert name not in low, f"carrier region leaked decision helper name: {name}"


def test_carrier_region_has_no_arithmetic_clock_or_network_debris():
    # the carrier itself performs no arithmetic / comparison / clock / network / parsing
    carrier = _carrier_region()
    low = carrier.lower()
    for forbidden in [
        "float(", "decimal", "import re", "<=", ">=", ">", "abs(",
        "import os", "import time", "import datetime", "datetime.", "time.time(", ".now(",
        "utcnow", "monotonic", "import socket", "urllib", "requests.", "import json",
        "subprocess.", "open(", "fetch", "polling",
    ]:
        assert forbidden not in low, f"carrier region debris token present: {forbidden}"


def test_source_scan_no_banned_output_names():
    # whole module: the gate introduces no actionability/output-naming debris
    src = _module_source()
    for banned in ["ActionableCandidate", "TradeCandidate", "ReadyEnvelope", "ExecutableSignal",
                   "Opportunity", "ExecutionPayload", "OrderIntent", "Fillable", "Tradable"]:
        assert banned not in src, f"banned output/actionability name present in runtime: {banned}"


# --- Slice 2 gate purity locks (AST + scoped source scans) ---

def test_gate_body_does_not_read_estimated_slippage_bps():
    # AST proof: nowhere in the module is `.estimated_slippage_bps` dereferenced (passive metadata)
    tree = ast.parse(_module_source())
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr != "estimated_slippage_bps", \
                "gate must not read estimated_slippage_bps (passive, non-decisioning metadata)"


def test_gate_does_not_read_non_decision_liquidity_fields():
    # the gate must never dereference the carrier's provenance / id / boundary_version / slippage
    gate = _gate_region()
    for banned_attr in [".source_contract", ".source_artifact", ".source_field",
                        ".liquidity_evidence_id", ".boundary_version", ".estimated_slippage_bps"]:
        assert "liquidity_evidence" + banned_attr not in gate, \
            f"gate must not read liquidity_evidence{banned_attr} for decisioning"


def test_gate_region_has_no_clock_network_fetch_retry_polling():
    gate = _gate_region().lower()
    for forbidden in ["import os", "import time", "import datetime", "datetime.", "time.time(",
                      ".now(", "utcnow", "monotonic", "perf_counter", "import socket", "urllib",
                      "requests.", "import http", "import json", "subprocess.", "import random",
                      "fetch", "polling", "sleep("]:
        assert forbidden not in gate, f"gate clock/network debris token present: {forbidden}"


def test_gate_region_has_no_sizing_routing_execution_actionability():
    gate = _gate_region().lower()
    for forbidden in ["partial fill", "partial_fill", "reduced size", "reduced_size",
                      "max tradable", "max_tradable", "allocation", "order quantity",
                      "order_quantity", "order_intent", "order intent", "order_ready",
                      "routing", "route(", "execution", "executable", "paper", "live",
                      "canary", "sizing", "actionable"]:
        assert forbidden not in gate, f"gate sizing/routing/execution debris token present: {forbidden}"


def test_gate_region_has_no_net_edge_profitability_or_threshold_arithmetic():
    # bare "profitability" is NOT banned (the legitimate upstream-envelope import carries it);
    # only the decisioning forms are forbidden
    gate = _gate_region().lower()
    for forbidden in ["net_edge", "net edge", "threshold", "malformed_threshold",
                      "slippage model", "slippage_model", "pnl", "kelly"]:
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
    assert gt == 0 and gte == 0 and lt == 0, "gate must use no >, >=, or < comparisons"
    assert lte == 2, f"gate must use exactly two <= equations (staleness + capacity), found {lte}"
    assert binops == [ast.Sub], f"gate arithmetic is limited to one subtraction, found {binops}"
    assert abs_calls == 1, f"gate must call abs() exactly once (staleness), found {abs_calls}"


# --- Slice 2 gate behaviour: helpers ---

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
        observed_size="0.5",
        size_unit="BTC",
        observed_at_epoch_ms="1781637248000",
        staleness_threshold_ms="60000",
        source_contract="ENVELOPE_CONTRACT.md",
        source_artifact="docs/handoff/ENVELOPE_ARTIFACT.md",
        source_field="evidence_envelope.market_topology",
        boundary_version="phase5.post_profitability_evidence_envelope_boundary.v0",
    )
    fields.update(overrides)
    env = object.__new__(PostProfitabilityEvidenceEnvelope)
    for k, v in fields.items():
        object.__setattr__(env, k, v)
    return env


def _liq(**overrides):
    """A valid LiquidityCapacityEvidenceContext via its real factory (size bound to the envelope)."""
    kw = _kwargs(
        observed_size="0.5",
        observed_size_unit="BTC",
        available_capacity="10",
        capacity_unit="BTC",
        liquidity_snapshot_epoch_ms="1781637248000",
        evidence_epoch_tolerance_ms="60000",
        source_contract="LIQ_CONTRACT.md",
        source_artifact="docs/handoff/LIQ_ARTIFACT.md",
        source_field="liquidity_evidence.capacity",
    )
    kw.update(overrides)
    return make_liquidity_capacity_evidence_context(**kw)


def _bypassed_liq(drop=None, **overrides):
    """An exact carrier via object.__new__ (factory bypassed) so a decision field can be omitted."""
    fields = dict(
        component_name=EXPECTED_COMPONENT,
        venue="HYPERLIQUID",
        instrument_id="BTC-PERP",
        base_asset="BTC",
        quote_asset="USD",
        observed_size="0.5",
        observed_size_unit="BTC",
        available_capacity="10",
        capacity_unit="BTC",
        liquidity_snapshot_epoch_ms="1781637248000",
        evidence_epoch_tolerance_ms="60000",
        source_contract="LIQ_CONTRACT.md",
        source_artifact="docs/handoff/LIQ_ARTIFACT.md",
        source_field="liquidity_evidence.capacity",
        liquidity_evidence_id="LIQ-001",
        boundary_version=BOUNDARY_VERSION,
        estimated_slippage_bps="2.5",
    )
    fields.update(overrides)
    if drop is not None:
        del fields[drop]
    obj = object.__new__(LiquidityCapacityEvidenceContext)
    for k, v in fields.items():
        object.__setattr__(obj, k, v)
    return obj


def _call(**overrides):
    env_over = overrides.pop("env", {})
    liq_over = overrides.pop("liq", {})
    return liquidity_capacity_preflight(evidence_envelope=_env(**env_over),
                                        liquidity_evidence=_liq(**liq_over))


# --- branch priority 1: misroute ---

def test_misrouted_halt_carrier_as_envelope_raises():
    for halt in (object.__new__(BlockedPacket), object.__new__(NoEligibleHaltPacket)):
        with pytest.raises(MisroutedHaltCarrierError):
            liquidity_capacity_preflight(evidence_envelope=halt, liquidity_evidence=_liq())


def test_misrouted_halt_carrier_as_liquidity_raises():
    for halt in (object.__new__(BlockedPacket), object.__new__(NoEligibleHaltPacket)):
        with pytest.raises(MisroutedHaltCarrierError):
            liquidity_capacity_preflight(evidence_envelope=_env(), liquidity_evidence=halt)


def test_misroute_takes_priority_over_wrong_type():
    # a misrouted halt carrier raises Misrouted even when the other arg is also the wrong type
    with pytest.raises(MisroutedHaltCarrierError):
        liquidity_capacity_preflight(evidence_envelope=object.__new__(BlockedPacket),
                                     liquidity_evidence=object())


# --- branch priority 2: exact-type checks ---

def test_wrong_type_envelope_raises_gate_type_error():
    for bad in (object(), {}, None, 5, "x", _liq()):
        with pytest.raises(LiquidityCapacityGateTypeError):
            liquidity_capacity_preflight(evidence_envelope=bad, liquidity_evidence=_liq())


def test_wrong_type_liquidity_raises_gate_type_error():
    for bad in (object(), {}, None, 5, "x", _env()):
        with pytest.raises(LiquidityCapacityGateTypeError):
            liquidity_capacity_preflight(evidence_envelope=_env(), liquidity_evidence=bad)


def test_envelope_subclass_rejected():
    class _EnvSub(PostProfitabilityEvidenceEnvelope):
        pass
    sub = object.__new__(_EnvSub)
    with pytest.raises(LiquidityCapacityGateTypeError):
        liquidity_capacity_preflight(evidence_envelope=sub, liquidity_evidence=_liq())


def test_liquidity_subclass_rejected():
    class _LiqSub(LiquidityCapacityEvidenceContext):
        pass
    sub = object.__new__(_LiqSub)
    with pytest.raises(LiquidityCapacityGateTypeError):
        liquidity_capacity_preflight(evidence_envelope=_env(), liquidity_evidence=sub)


# --- branch priority 3: missing allow-listed liquidity evidence ---

def test_missing_liquidity_decision_field_blocks_missing():
    for field in ("observed_size", "observed_size_unit", "available_capacity", "capacity_unit",
                  "liquidity_snapshot_epoch_ms", "evidence_epoch_tolerance_ms"):
        out = liquidity_capacity_preflight(evidence_envelope=_env(),
                                           liquidity_evidence=_bypassed_liq(drop=field))
        assert type(out) is BlockedPacket
        assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_MISSING_LIQUIDITY_EVIDENCE


# --- branch priority 4: malformed grammar / positivity ---

def test_malformed_liquidity_observed_size_blocks_malformed():
    # the carrier stores verbatim (no grammar validation), so malformed magnitudes reach the gate via
    # a factory-bypassed carrier; empty/whitespace would be rejected by the real factory, so use bypass
    for bad in ["abc", "-5", "1e3", "1E3", "NaN", "Infinity", "-Infinity", "1_000", "1,000",
                "", "   ", "01", "1.", ".5", "+1", "0", "0.0"]:
        out = liquidity_capacity_preflight(evidence_envelope=_env(),
                                           liquidity_evidence=_bypassed_liq(observed_size=bad))
        assert type(out) is BlockedPacket, f"observed_size={bad!r} should block"
        assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE


def test_malformed_or_zero_available_capacity_blocks_malformed_not_no_eligible():
    for bad in ["abc", "-1", "1e3", "NaN", "Infinity", "1_000", "1,000", "", "  ", "0", "0.0", "00"]:
        out = liquidity_capacity_preflight(evidence_envelope=_env(),
                                           liquidity_evidence=_bypassed_liq(available_capacity=bad))
        assert type(out) is BlockedPacket, f"available_capacity={bad!r} should block as malformed"
        assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE


def test_malformed_epoch_or_tolerance_blocks_malformed():
    for field in ("liquidity_snapshot_epoch_ms", "evidence_epoch_tolerance_ms"):
        for bad in ["abc", "-1", "1.0", "1e3", "", "  ", "1_000", "1,000", "+1", "01"]:
            out = liquidity_capacity_preflight(evidence_envelope=_env(),
                                               liquidity_evidence=_bypassed_liq(**{field: bad}))
            assert type(out) is BlockedPacket, f"{field}={bad!r} should block"
            assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE


def test_tolerance_zero_is_valid_grammar_not_malformed():
    # tolerance "0" is valid; with identical epochs the diff is 0 <= 0 -> fresh -> proceeds to pass
    out = _call(liq={"evidence_epoch_tolerance_ms": "0"})
    assert type(out) is PostProfitabilityEvidenceEnvelope


def test_malformed_takes_priority_over_identity_mismatch():
    # malformed liquidity evidence wins over an identity mismatch (priority 4 before 5)
    out = _call(liq={"observed_size": "abc", "venue": "OTHER"})
    assert type(out) is BlockedPacket
    assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE


# --- branch priority 5: identity mismatch (incl. size magnitude binding) ---

def test_identity_string_mismatch_blocks_identity():
    for field in ("venue", "instrument_id", "base_asset", "quote_asset"):
        out = _call(liq={field: "OTHER"})
        assert type(out) is BlockedPacket
        assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_IDENTITY_MISMATCH


def test_observed_size_magnitude_mismatch_is_identity_mismatch():
    # both valid positive decimals, units aligned, but magnitudes differ -> identity mismatch
    out = liquidity_capacity_preflight(
        evidence_envelope=_env(observed_size="0.5"),
        liquidity_evidence=_liq(observed_size="0.7"),
    )
    assert type(out) is BlockedPacket
    assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_IDENTITY_MISMATCH


def test_observed_size_magnitude_compared_as_decimal_not_string():
    # "0.50" == "0.5" as a magnitude: this must NOT be an identity mismatch
    out = liquidity_capacity_preflight(
        evidence_envelope=_env(observed_size="0.5"),
        liquidity_evidence=_liq(observed_size="0.50"),
    )
    assert type(out) is PostProfitabilityEvidenceEnvelope


def test_identity_mismatch_takes_priority_over_unit_mismatch():
    out = _call(liq={"venue": "OTHER", "observed_size_unit": "ETH", "capacity_unit": "ETH"})
    assert type(out) is BlockedPacket
    assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_IDENTITY_MISMATCH


# --- branch priority 6: unit mismatch ---

def test_size_unit_vs_observed_size_unit_mismatch_blocks_unit():
    out = _call(env={"size_unit": "BTC"}, liq={"observed_size_unit": "ETH", "capacity_unit": "ETH"})
    assert type(out) is BlockedPacket
    assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_UNIT_MISMATCH


def test_observed_size_unit_vs_capacity_unit_mismatch_blocks_unit():
    out = _call(liq={"observed_size_unit": "BTC", "capacity_unit": "ETH"})
    assert type(out) is BlockedPacket
    assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_UNIT_MISMATCH


def test_unit_mismatch_takes_priority_over_stale():
    out = _call(env={"observed_at_epoch_ms": "1000"},
                liq={"observed_size_unit": "ETH", "capacity_unit": "ETH",
                     "liquidity_snapshot_epoch_ms": "999999", "evidence_epoch_tolerance_ms": "1"})
    assert type(out) is BlockedPacket
    assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_UNIT_MISMATCH


# --- branch priority 7: staleness ---

def test_stale_evidence_blocks_stale():
    out = _call(env={"observed_at_epoch_ms": "1000"},
                liq={"liquidity_snapshot_epoch_ms": "100000", "evidence_epoch_tolerance_ms": "50"})
    assert type(out) is BlockedPacket
    assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_STALE_EVIDENCE


def test_fresh_at_exact_tolerance_is_not_stale():
    # |1000 - 1100| == 100 == tolerance -> inclusive, fresh -> proceeds to a sufficient pass
    out = _call(env={"observed_at_epoch_ms": "1000"},
                liq={"liquidity_snapshot_epoch_ms": "1100", "evidence_epoch_tolerance_ms": "100"})
    assert type(out) is PostProfitabilityEvidenceEnvelope


def test_stale_takes_priority_over_insufficient_capacity():
    out = _call(env={"observed_at_epoch_ms": "1000", "observed_size": "20"},
                liq={"observed_size": "20", "available_capacity": "10",
                     "liquidity_snapshot_epoch_ms": "100000", "evidence_epoch_tolerance_ms": "50"})
    assert type(out) is BlockedPacket
    assert out.reason_code == LIQUIDITY_CAPACITY_GATE_BLOCKED_STALE_EVIDENCE


# --- branch priority 8/9: insufficient vs sufficient capacity ---

def test_insufficient_positive_capacity_is_no_eligible():
    out = _call(env={"observed_size": "20"}, liq={"observed_size": "20", "available_capacity": "10"})
    assert type(out) is NoEligibleHaltPacket
    assert out.no_eligible_reason == LIQUIDITY_CAPACITY_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPACITY


def test_equal_capacity_is_sufficient_and_passes():
    env = _env(observed_size="10")
    out = liquidity_capacity_preflight(evidence_envelope=env,
                                       liquidity_evidence=_liq(observed_size="10",
                                                               available_capacity="10"))
    assert out is env  # inclusive: equal capacity is sufficient, returns the same envelope by identity


def test_sufficient_capacity_returns_same_envelope_by_identity():
    env = _env()
    out = liquidity_capacity_preflight(evidence_envelope=env, liquidity_evidence=_liq())
    assert out is env


def test_slippage_banana_still_passes_when_all_else_valid_and_sufficient():
    env = _env()
    out = liquidity_capacity_preflight(
        evidence_envelope=env,
        liquidity_evidence=_liq(estimated_slippage_bps="banana"),
    )
    assert out is env  # passive metadata is never read, so a junk value cannot affect the decision


# --- packet provenance + static reason tokens (no value leakage) ---

def test_blocked_packet_provenance_comes_only_from_envelope():
    env = _env(source_contract="ENV_C", source_artifact="ENV_A", source_field="ENV_F")
    out = liquidity_capacity_preflight(evidence_envelope=env,
                                       liquidity_evidence=_liq(venue="OTHER"))
    assert type(out) is BlockedPacket
    assert out.source_contract == "ENV_C"
    assert out.source_artifact == "ENV_A"
    assert out.source_field == "ENV_F"


def test_no_eligible_provenance_comes_only_from_envelope():
    env = _env(observed_size="20", source_contract="ENV_C", source_artifact="ENV_A",
               source_field="ENV_F")
    out = liquidity_capacity_preflight(
        evidence_envelope=env,
        liquidity_evidence=_liq(observed_size="20", available_capacity="10",
                                source_contract="LIQ_C", source_artifact="LIQ_A",
                                source_field="LIQ_F"),
    )
    assert type(out) is NoEligibleHaltPacket
    assert (out.source_contract, out.source_artifact, out.source_field) == ("ENV_C", "ENV_A", "ENV_F")


def test_packets_do_not_leak_raw_magnitudes_into_reason_or_field():
    out = _call(env={"observed_size": "20"}, liq={"observed_size": "20", "available_capacity": "10"})
    assert type(out) is NoEligibleHaltPacket
    # only the static reason token, never a raw magnitude / epoch / slippage value
    assert out.no_eligible_reason == LIQUIDITY_CAPACITY_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPACITY
    for leak in ("20", "10", "1781637248000", "60000", "2.5", "banana"):
        assert leak not in out.no_eligible_reason
