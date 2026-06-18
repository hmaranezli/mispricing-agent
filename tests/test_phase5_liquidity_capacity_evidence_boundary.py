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


# --- Slice 1 negative runtime-symbol / purity guards ---

def test_gate_and_preflight_symbols_absent_from_runtime_module():
    import phase5.liquidity_capacity_evidence_boundary as mod
    assert not hasattr(mod, "LiquidityCapacityGate"), "Slice 1 must not define the gate class"
    assert not hasattr(mod, "liquidity_capacity_preflight"), "Slice 1 must not define the preflight"


def test_carrier_has_no_decision_helper_methods_or_properties():
    for name in ["is_tradable", "is_eligible", "is_sufficient", "is_stale", "can_pass",
                 "capacity_ok", "order_ready", "actionable", "executable", "preflight"]:
        assert not hasattr(LiquidityCapacityEvidenceContext, name), \
            f"carrier must not expose decision helper: {name}"


def test_source_scan_no_gate_envelope_packet_or_decision_logic():
    import phase5.liquidity_capacity_evidence_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        src = f.read()
    low = src.lower()
    # gate / preflight slice not implemented here
    assert "class LiquidityCapacityGate" not in src
    assert "def liquidity_capacity_preflight" not in src
    assert "preflight" not in low
    # upstream envelope and halt carriers not imported / referenced
    assert "PostProfitabilityEvidenceEnvelope" not in src
    assert "BlockedPacket" not in src
    assert "NoEligibleHaltPacket" not in src
    assert "make_blocked_packet" not in low
    assert "make_no_eligible_halt_packet" not in low
    # decision helper names absent
    for name in ["is_tradable", "is_eligible", "is_sufficient", "is_stale", "can_pass",
                 "capacity_ok", "order_ready", "actionable", "executable"]:
        assert name not in low, f"decision helper name present: {name}"


def test_source_scan_no_arithmetic_clock_network_or_routing_debris():
    import phase5.liquidity_capacity_evidence_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        src = f.read()
    low = src.lower()
    for forbidden in [
        "float(", "decimal", "import re", "<=", ">=", "abs(",
        "import os", "import time", "import datetime", "datetime.", "time.time(", ".now(",
        "utcnow", "monotonic", "import socket", "urllib", "requests.", "import json",
        "subprocess.", "open(", "fetch", "polling", "retry",
        "slippage model", "slippage_model", "order quantity", "order_quantity",
        "routing", "allocation", "partial fill", "sizing", "net_edge", "threshold", "profitab",
    ]:
        assert forbidden not in low, f"forbidden debris token present: {forbidden}"


def test_source_scan_no_banned_output_names():
    import phase5.liquidity_capacity_evidence_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        src = f.read()
    for banned in ["ActionableCandidate", "TradeCandidate", "ReadyEnvelope", "ExecutableSignal",
                   "Opportunity", "ExecutionPayload", "OrderIntent", "Fillable", "Tradable"]:
        assert banned not in src, f"banned output/actionability name present in runtime: {banned}"
