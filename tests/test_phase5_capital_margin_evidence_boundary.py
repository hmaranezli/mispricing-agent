"""tests/test_phase5_capital_margin_evidence_boundary.py — pins the atomic implementation of Slice 1
of the `phase5_capital_margin_evidence_boundary` component: `CapitalMarginEvidenceContext`.

`CapitalMarginEvidenceContext` is a frozen, repr-safe, anti-truthiness, anti-coercion, factory-only,
slotted carrier that wraps only explicitly supplied capital/margin evidence. Every user-supplied field
is an exact, non-empty, non-whitespace ``str`` stored verbatim — the carrier performs NO numeric /
magnitude / epoch parsing or validation, NO comparison, NO derivation, and NO decision. It is strictly
a supplied-evidence descriptor; the capital/margin boundary is a ledger auditor, and that audit belongs
entirely to the future gate.

Slice 1 scope: ONLY the carrier and its factory exist in the runtime module. The gate
(`CapitalMarginGate` / `capital_margin_preflight`) and the `CAPITAL_MARGIN_GATE_*` reason tokens are
explicitly NOT implemented here, and no upstream envelope or halt-carrier is imported, constructed, or
referenced.
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
    # accepted and preserved verbatim (all validation belongs to the future gate, not the carrier).
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


# --- Slice 1 negative runtime-symbol / purity guards ---

def test_gate_and_preflight_symbols_absent_from_runtime_module():
    import phase5.capital_margin_evidence_boundary as mod
    assert not hasattr(mod, "CapitalMarginGate"), "Slice 1 must not define the gate class"
    assert not hasattr(mod, "capital_margin_preflight"), "Slice 1 must not define the preflight"


def test_no_capital_margin_gate_reason_tokens_in_runtime():
    src = _src()
    assert "CAPITAL_MARGIN_GATE_" not in src, "Slice 1 carrier must not carry gate reason tokens"


def test_carrier_has_no_decision_helper_methods_or_properties():
    for name in ["is_sufficient", "is_valid", "has_funds", "has_capital", "is_stale", "is_eligible",
                 "is_tradable", "can_pass", "can_trade", "order_ready", "actionable", "executable",
                 "preflight", "to_dict", "as_dict", "model_dump"]:
        assert not hasattr(CapitalMarginEvidenceContext, name), \
            f"carrier must not expose decision/serialization helper: {name}"


def test_runtime_uses_no_isinstance_validation():
    assert "isinstance(" not in _src(), "carrier must use exact type(value) is str, never isinstance"


def test_source_scan_no_gate_envelope_packet_or_decision_logic():
    src = _src()
    low = src.lower()
    # gate / preflight slice not implemented here
    assert "class CapitalMarginGate" not in src
    assert "def capital_margin_preflight" not in src
    assert "preflight" not in low
    # upstream envelope and halt carriers not imported / referenced
    assert "PostProfitabilityEvidenceEnvelope" not in src
    assert "BlockedPacket" not in src
    assert "NoEligibleHaltPacket" not in src
    assert "make_blocked_packet" not in low
    assert "make_no_eligible_halt_packet" not in low
    # decision / serialization helper names absent
    for name in ["is_sufficient", "is_valid", "has_funds", "has_capital", "is_stale", "is_eligible",
                 "is_tradable", "can_pass", "can_trade", "order_ready", "actionable", "executable",
                 "to_dict", "as_dict", "model_dump"]:
        assert name not in low, f"decision/serialization helper name present: {name}"


def test_source_scan_no_forbidden_imports_or_calculator_debris():
    low = _src().lower()
    for forbidden in [
        "import os", "import re", "import time", "import datetime", "datetime", "from decimal",
        "import decimal", "decimal", "import json", "import socket", "urllib", "requests",
        "import http", "pathlib", "import random", "subprocess.",
        "<=", ">=", "abs(", "float(",
        ".now(", "utcnow", "monotonic", "fetch", "polling", "wallet", "balance(",
        "net_edge", "threshold", "profitab", "notional", "leverage",
    ]:
        assert forbidden not in low, f"forbidden import/calculator debris token present: {forbidden}"


def test_source_scan_no_banned_output_names():
    src = _src()
    for banned in ["ActionableCandidate", "TradeCandidate", "ReadyEnvelope", "ExecutableSignal",
                   "Opportunity", "ExecutionPayload", "OrderIntent", "Fillable", "Tradable"]:
        assert banned not in src, f"banned output/actionability name present in runtime: {banned}"
