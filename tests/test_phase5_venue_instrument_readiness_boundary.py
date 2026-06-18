"""tests/test_phase5_venue_instrument_readiness_boundary.py — pins the atomic implementation of
Slice 1 of the `phase5_venue_instrument_readiness_boundary` component:
`VenueInstrumentReadinessStateContext`.

`VenueInstrumentReadinessStateContext` is a frozen, repr-safe, anti-truthiness, anti-coercion,
factory-only carrier that wraps only explicitly supplied venue/instrument readiness-state evidence.
It is strictly a supplied venue/instrument state descriptor. It is NOT trade readiness, NOT
actionability, NOT execution safety, NOT liquidity readiness, NOT balance/margin readiness, NOT
paper-ready or live-ready, NOT order-placement proof, and NOT an order / signal / candidate. It
performs no derivation, no parsing, no inference, no defaulting, no clock, no network, and no
case/unit normalization, and it never evaluates a gate.

Slice 1 scope: ONLY the carrier and its factory exist in the runtime module. The gate
(`VenueInstrumentReadinessGate`) and the preflight function are explicitly NOT implemented here, and
no halt carrier is imported, constructed, or returned.
"""
import pytest

from phase5.venue_instrument_readiness_boundary import (
    VenueInstrumentReadinessStateContext,
    make_venue_instrument_readiness_state_context,
    VenueInstrumentReadinessStateContextTypeError,
    VENUE_INSTRUMENT_READINESS_BOUNDARY_COMPONENT_NAME,
    BOUNDARY_VERSION,
    VENUE_INSTRUMENT_STATE_ACTIVE,
    VENUE_INSTRUMENT_STATE_SUSPENDED,
    VENUE_INSTRUMENT_STATE_MAINTENANCE,
    VENUE_INSTRUMENT_STATE_CLOSED,
    VENUE_INSTRUMENT_STATE_UNSUPPORTED,
)

EXPECTED_COMPONENT = "phase5_venue_instrument_readiness_boundary"

EXPECTED_FIELDS = (
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
)

# the 10 user-supplied fields the factory accepts (every field except component_name)
USER_SUPPLIED_FIELDS = (
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
)

ALLOWED_STATUSES = (
    VENUE_INSTRUMENT_STATE_ACTIVE,
    VENUE_INSTRUMENT_STATE_SUSPENDED,
    VENUE_INSTRUMENT_STATE_MAINTENANCE,
    VENUE_INSTRUMENT_STATE_CLOSED,
    VENUE_INSTRUMENT_STATE_UNSUPPORTED,
)


def _kwargs(**overrides):
    base = dict(
        venue="HYPERLIQUID",
        instrument_id="BTC-PERP",
        base_asset="BTC",
        quote_asset="USD",
        readiness_status="VENUE_INSTRUMENT_STATE_ACTIVE",
        source_contract="phase5_venue_instrument_readiness_implementation_planning.md",
        source_artifact="docs/handoff/phase5_venue_instrument_readiness_implementation_planning.md",
        source_field="venue_instrument.readiness_state",
        state_id="STATE-001",
        boundary_version=BOUNDARY_VERSION,
    )
    base.update(overrides)
    return base


def _make(**overrides):
    return make_venue_instrument_readiness_state_context(**_kwargs(**overrides))


# --- constants / shape ---

def test_component_constant_and_boundary_version():
    assert VENUE_INSTRUMENT_READINESS_BOUNDARY_COMPONENT_NAME == EXPECTED_COMPONENT
    assert BOUNDARY_VERSION == "phase5.venue_instrument_readiness_boundary.v0"


def test_status_vocabulary_constants_exact_values():
    assert VENUE_INSTRUMENT_STATE_ACTIVE == "VENUE_INSTRUMENT_STATE_ACTIVE"
    assert VENUE_INSTRUMENT_STATE_SUSPENDED == "VENUE_INSTRUMENT_STATE_SUSPENDED"
    assert VENUE_INSTRUMENT_STATE_MAINTENANCE == "VENUE_INSTRUMENT_STATE_MAINTENANCE"
    assert VENUE_INSTRUMENT_STATE_CLOSED == "VENUE_INSTRUMENT_STATE_CLOSED"
    assert VENUE_INSTRUMENT_STATE_UNSUPPORTED == "VENUE_INSTRUMENT_STATE_UNSUPPORTED"


def test_factory_builds_carrier_with_exact_field_set_and_component_name():
    ctx = _make()
    assert type(ctx) is VenueInstrumentReadinessStateContext
    assert ctx.component_name == EXPECTED_COMPONENT
    for f in EXPECTED_FIELDS:
        assert hasattr(ctx, f), f"missing field {f}"


def test_declared_field_order_is_the_closed_set():
    from dataclasses import fields as dataclass_fields
    assert tuple(f.name for f in dataclass_fields(VenueInstrumentReadinessStateContext)) == \
        EXPECTED_FIELDS


def test_field_values_preserved_verbatim():
    kw = _kwargs()
    ctx = make_venue_instrument_readiness_state_context(**kw)
    for f in USER_SUPPLIED_FIELDS:
        assert getattr(ctx, f) == kw[f]


def test_factory_is_keyword_only():
    with pytest.raises(TypeError):
        make_venue_instrument_readiness_state_context("HYPERLIQUID")  # positional → TypeError


def test_component_name_is_not_a_factory_parameter():
    with pytest.raises(TypeError):
        make_venue_instrument_readiness_state_context(
            **_kwargs(component_name="x")
        )


def test_direct_positional_construction_unsupported():
    with pytest.raises(TypeError):
        VenueInstrumentReadinessStateContext("HYPERLIQUID")


# --- string field discipline ---

def test_string_fields_must_be_exact_str_type_error():
    for f in USER_SUPPLIED_FIELDS:
        for bad in [None, 1, 1.0, b"x", {}, [], object(), True]:
            with pytest.raises(VenueInstrumentReadinessStateContextTypeError):
                _make(**{f: bad})


def test_string_fields_reject_str_subclass():
    class _S(str):
        pass
    for f in USER_SUPPLIED_FIELDS:
        # use an allowed-status value for readiness_status so only the subclass-ness can fail it
        val = "VENUE_INSTRUMENT_STATE_ACTIVE" if f == "readiness_status" else "X"
        with pytest.raises(VenueInstrumentReadinessStateContextTypeError):
            _make(**{f: _S(val)})


def test_empty_or_whitespace_string_fields_value_error():
    for f in USER_SUPPLIED_FIELDS:
        for bad in ["", "   ", "\t", "\n"]:
            with pytest.raises(ValueError):
                _make(**{f: bad})


# --- readiness_status vocabulary discipline ---

def test_readiness_status_accepts_each_allowed_token():
    for token in ALLOWED_STATUSES:
        ctx = _make(readiness_status=token)
        assert ctx.readiness_status == token


def test_readiness_status_rejects_unknown_token_value_error():
    for bad in ["VENUE_INSTRUMENT_STATE_FROZEN", "WHATEVER", "STATE_ACTIVE", "ACTIVE_STATE"]:
        with pytest.raises(ValueError):
            _make(readiness_status=bad)


def test_readiness_status_rejects_case_variants_value_error():
    for bad in ["venue_instrument_state_active", "Venue_Instrument_State_Active",
                "VENUE_INSTRUMENT_STATE_Active"]:
        with pytest.raises(ValueError):
            _make(readiness_status=bad)


def test_readiness_status_rejects_synonyms_value_error():
    for bad in ["OPEN", "ENABLED", "AVAILABLE", "READY", "TRADABLE", "HALTED", "PAUSED", "DISABLED"]:
        with pytest.raises(ValueError):
            _make(readiness_status=bad)


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
        readiness_status="VENUE_INSTRUMENT_STATE_SUSPENDED",
        source_contract="SECRETCONTRACT.md",
        source_artifact="docs/handoff/SECRETARTIFACT.md",
        source_field="SECRETFIELD",
        state_id="SECRETSTATEID",
    )
    text = repr(ctx)
    assert EXPECTED_COMPONENT in text
    for leak in ["SECRETVENUE", "SECRETINSTR", "SECRETBASE", "SECRETQUOTE",
                 "VENUE_INSTRUMENT_STATE_SUSPENDED", "SECRETCONTRACT", "SECRETARTIFACT",
                 "SECRETFIELD", "SECRETSTATEID"]:
        assert leak not in text, f"repr leaked sensitive value: {leak}"


# --- Slice 1 negative runtime-symbol guards (gate NOT implemented here) ---

def test_gate_symbols_absent_from_runtime_module():
    import phase5.venue_instrument_readiness_boundary as mod
    assert not hasattr(mod, "VenueInstrumentReadinessGate"), \
        "Slice 1 must not define the gate class"
    assert not hasattr(mod, "venue_instrument_readiness_preflight"), \
        "Slice 1 must not define the preflight function"


def test_source_scan_no_gate_or_halt_carrier_or_evaluation():
    import phase5.venue_instrument_readiness_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        src = f.read()
    # gate slice not implemented in this module
    assert "class VenueInstrumentReadinessGate" not in src
    assert "def venue_instrument_readiness_preflight" not in src
    # halt carriers are unnecessary for Slice 1 → not imported / constructed / referenced
    assert "BlockedPacket" not in src, "Slice 1 carrier must not reference BlockedPacket"
    assert "NoEligibleHaltPacket" not in src, "Slice 1 carrier must not reference NoEligibleHaltPacket"
    assert "make_blocked_packet(" not in src, "must not construct a BlockedPacket"
    assert "make_no_eligible_halt_packet(" not in src, "must not construct a NoEligibleHaltPacket"
    # no comparison against the upstream envelope (that is the gate slice's job, not Slice 1)
    assert "PostProfitabilityEvidenceEnvelope" not in src, \
        "Slice 1 carrier must not reference the upstream envelope"


def test_source_scan_no_io_clock_normalization_or_recovery_language():
    import phase5.venue_instrument_readiness_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        src = f.read()
    low = src.lower()
    for forbidden in [
        "import os", "import time", "import datetime", "datetime.", "time.time(",
        ".now(", "import random", "subprocess.", "open(", "import json", "import socket",
        "urllib", "requests.", "float(",
        ".upper(", ".lower(", ".casefold(",
        "re-attach", "reattach", "recover", "reconstruct", "hydrate", "enrich", "resolve",
    ]:
        assert forbidden not in low, f"forbidden code-usage/semantic token present: {forbidden}"


def test_source_scan_no_banned_output_names():
    import phase5.venue_instrument_readiness_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        src = f.read()
    for banned in ["ActionableCandidate", "TradeCandidate", "ReadyEnvelope", "ExecutableSignal",
                   "Opportunity", "ExecutionPayload", "OrderIntent", "Fillable", "Tradable"]:
        assert banned not in src, f"banned output/actionability name present in runtime: {banned}"
