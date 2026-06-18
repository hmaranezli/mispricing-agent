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
    # --- Slice 2: gate / preflight ---
    VenueInstrumentReadinessGate,
    venue_instrument_readiness_preflight,
    VenueInstrumentReadinessGateTypeError,
    MisroutedHaltCarrierError,
    VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MISSING_READINESS_STATE,
    VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MALFORMED_READINESS_STATE,
    VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_IDENTITY_MISMATCH,
    VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_UNRECOGNIZED_STATE_VOCABULARY,
    VENUE_INSTRUMENT_READINESS_GATE_NO_ELIGIBLE_STATE_NOT_ACTIVE,
)
from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
)
from phase5.post_profitability_evidence_envelope_boundary import (
    PostProfitabilityEvidenceEnvelope,
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


# ===========================================================================
# Slice 2: VenueInstrumentReadinessGate / venue_instrument_readiness_preflight
# ===========================================================================

_OMIT = object()  # sentinel: in a bypassed carrier, do NOT set this attribute at all


def _envelope(**overrides):
    """An exact PostProfitabilityEvidenceEnvelope built low-level (the gate reads only its explicit
    identity + provenance fields; calculation_result is never inspected by the gate)."""
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


def _state(**overrides):
    """A valid VenueInstrumentReadinessStateContext via its real factory."""
    kw = dict(
        venue="HYPERLIQUID",
        instrument_id="BTC-PERP",
        base_asset="BTC",
        quote_asset="USD",
        readiness_status="VENUE_INSTRUMENT_STATE_ACTIVE",
        source_contract="STATE_CONTRACT.md",
        source_artifact="docs/handoff/STATE_ARTIFACT.md",
        source_field="venue_instrument.readiness_state",
        state_id="STATE-001",
        boundary_version=BOUNDARY_VERSION,
    )
    kw.update(overrides)
    return make_venue_instrument_readiness_state_context(**kw)


def _bypassed_state(**overrides):
    """An exact VenueInstrumentReadinessStateContext built via object.__new__ (factory bypassed),
    so we can omit or corrupt readiness_status to exercise the gate's zero-trust branches."""
    fields = dict(
        component_name=VENUE_INSTRUMENT_READINESS_BOUNDARY_COMPONENT_NAME,
        venue="HYPERLIQUID",
        instrument_id="BTC-PERP",
        base_asset="BTC",
        quote_asset="USD",
        readiness_status="VENUE_INSTRUMENT_STATE_ACTIVE",
        source_contract="STATE_CONTRACT.md",
        source_artifact="docs/handoff/STATE_ARTIFACT.md",
        source_field="venue_instrument.readiness_state",
        state_id="STATE-001",
        boundary_version=BOUNDARY_VERSION,
    )
    fields.update(overrides)
    st = object.__new__(VenueInstrumentReadinessStateContext)
    for k, v in fields.items():
        if v is _OMIT:
            continue
        object.__setattr__(st, k, v)
    return st


def _blocked():
    return make_blocked_packet(
        component_name="x", origin_component="x", origin_result_status="s", status="s",
        blocked_status=None, reason_code="r", missing_or_invalid_field=None,
        source_contract="c", source_artifact="a", source_field="f",
        deterministic_next_action="HALT_FAIL_CLOSED", human_review_required=True,
        may_retry_after_evidence=True, created_from_contract="c", boundary_version="v",
    )


def _no_eligible():
    return make_no_eligible_halt_packet(
        component_name="x", origin_component="x", origin_result_status="NO_ELIGIBLE",
        status="NO_ELIGIBLE", no_eligible_reason="R", source_contract="c", source_artifact="a",
        source_field="f", deterministic_next_action="HALT_BYPASS_NO_ELIGIBLE", boundary_version="v",
    )


# --- group 1: exact type enforcement for both inputs ---

def test_preflight_rejects_wrong_evidence_envelope_type():
    st = _state()
    for bad in [None, {}, [], "x", 1, 1.0, True, b"x", object()]:
        with pytest.raises(VenueInstrumentReadinessGateTypeError):
            venue_instrument_readiness_preflight(evidence_envelope=bad, readiness_state=st)


def test_preflight_rejects_wrong_readiness_state_type():
    env = _envelope()
    for bad in [None, {}, [], "x", 1, 1.0, True, b"x", object()]:
        with pytest.raises(VenueInstrumentReadinessGateTypeError):
            venue_instrument_readiness_preflight(evidence_envelope=env, readiness_state=bad)


def test_preflight_rejects_envelope_subclass():
    class _Sub(PostProfitabilityEvidenceEnvelope):
        pass
    sub = object.__new__(_Sub)
    for k, v in vars(_envelope()).items():
        object.__setattr__(sub, k, v)
    with pytest.raises(VenueInstrumentReadinessGateTypeError):
        venue_instrument_readiness_preflight(evidence_envelope=sub, readiness_state=_state())


def test_preflight_rejects_readiness_state_subclass():
    class _Sub(VenueInstrumentReadinessStateContext):
        pass
    sub = object.__new__(_Sub)
    for k, v in vars(_state()).items():
        object.__setattr__(sub, k, v)
    with pytest.raises(VenueInstrumentReadinessGateTypeError):
        venue_instrument_readiness_preflight(evidence_envelope=_envelope(), readiness_state=sub)


def test_preflight_is_keyword_only():
    with pytest.raises(TypeError):
        venue_instrument_readiness_preflight(_envelope(), _state())


# --- group 2: misrouted halt carriers on either argument ---

def test_misrouted_blocked_packet_as_envelope():
    with pytest.raises(MisroutedHaltCarrierError):
        venue_instrument_readiness_preflight(evidence_envelope=_blocked(), readiness_state=_state())


def test_misrouted_no_eligible_as_envelope():
    with pytest.raises(MisroutedHaltCarrierError):
        venue_instrument_readiness_preflight(evidence_envelope=_no_eligible(), readiness_state=_state())


def test_misrouted_blocked_packet_as_readiness_state():
    with pytest.raises(MisroutedHaltCarrierError):
        venue_instrument_readiness_preflight(evidence_envelope=_envelope(), readiness_state=_blocked())


def test_misrouted_no_eligible_as_readiness_state():
    with pytest.raises(MisroutedHaltCarrierError):
        venue_instrument_readiness_preflight(evidence_envelope=_envelope(), readiness_state=_no_eligible())


# --- group 3: identity mismatch → BlockedPacket BLOCKED_IDENTITY_MISMATCH ---

def test_identity_mismatch_returns_blocked_identity_mismatch():
    env = _envelope()
    for field in ("venue", "instrument_id", "base_asset", "quote_asset"):
        st = _state(**{field: "DIFFERENT_VALUE"})
        result = venue_instrument_readiness_preflight(evidence_envelope=env, readiness_state=st)
        assert type(result) is BlockedPacket, field
        assert result.reason_code == VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_IDENTITY_MISMATCH, field


def test_identity_comparison_is_case_sensitive():
    env = _envelope(venue="HYPERLIQUID")
    st = _state(venue="hyperliquid")
    result = venue_instrument_readiness_preflight(evidence_envelope=env, readiness_state=st)
    assert type(result) is BlockedPacket
    assert result.reason_code == VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_IDENTITY_MISMATCH


# --- group 4: ACTIVE + identity match → same envelope object by identity ---

def test_active_with_identity_match_returns_same_envelope_identity():
    env = _envelope()
    st = _state(readiness_status="VENUE_INSTRUMENT_STATE_ACTIVE")
    assert venue_instrument_readiness_preflight(evidence_envelope=env, readiness_state=st) is env


# --- group 5: each non-active known status → NoEligibleHaltPacket NO_ELIGIBLE_STATE_NOT_ACTIVE ---

def test_non_active_statuses_return_no_eligible_state_not_active():
    env = _envelope()
    for status in (VENUE_INSTRUMENT_STATE_SUSPENDED, VENUE_INSTRUMENT_STATE_MAINTENANCE,
                   VENUE_INSTRUMENT_STATE_CLOSED, VENUE_INSTRUMENT_STATE_UNSUPPORTED):
        st = _state(readiness_status=status)
        result = venue_instrument_readiness_preflight(evidence_envelope=env, readiness_state=st)
        assert type(result) is NoEligibleHaltPacket, status
        assert result.no_eligible_reason == \
            VENUE_INSTRUMENT_READINESS_GATE_NO_ELIGIBLE_STATE_NOT_ACTIVE, status


# --- group 6: bypassed exact carrier missing readiness_status → BLOCKED_MISSING_READINESS_STATE ---

def test_missing_readiness_status_returns_blocked_missing():
    env = _envelope()
    st = _bypassed_state(readiness_status=_OMIT)
    assert not hasattr(st, "readiness_status")
    result = venue_instrument_readiness_preflight(evidence_envelope=env, readiness_state=st)
    assert type(result) is BlockedPacket
    assert result.reason_code == VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MISSING_READINESS_STATE


# --- group 7: exact carrier malformed readiness_status → BLOCKED_MALFORMED_READINESS_STATE ---

def test_malformed_readiness_status_returns_blocked_malformed():
    env = _envelope()

    class _S(str):
        pass
    for bad in [5, 1.0, None, True, b"x", {}, [], object(), "", "   ", "\t", "\n",
                _S("VENUE_INSTRUMENT_STATE_ACTIVE")]:
        st = _bypassed_state(readiness_status=bad)
        result = venue_instrument_readiness_preflight(evidence_envelope=env, readiness_state=st)
        assert type(result) is BlockedPacket, repr(bad)
        assert result.reason_code == \
            VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MALFORMED_READINESS_STATE, repr(bad)


# --- group 8: exact non-empty str outside the vocabulary → BLOCKED_UNRECOGNIZED_STATE_VOCABULARY ---

def test_unrecognized_readiness_status_returns_blocked_unrecognized():
    env = _envelope()
    for bad in ["VENUE_INSTRUMENT_STATE_FROZEN", "ACTIVE", "OPEN",
                "venue_instrument_state_active", "VENUE_INSTRUMENT_STATE_ACTIVE "]:
        st = _bypassed_state(readiness_status=bad)
        result = venue_instrument_readiness_preflight(evidence_envelope=env, readiness_state=st)
        assert type(result) is BlockedPacket, repr(bad)
        assert result.reason_code == \
            VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_UNRECOGNIZED_STATE_VOCABULARY, repr(bad)


# --- group 9: NoEligible provenance comes from the envelope, not the readiness_state ---

def test_no_eligible_provenance_comes_from_envelope_not_readiness_state():
    env = _envelope(
        source_contract="ENVELOPE_CONTRACT.md",
        source_artifact="docs/handoff/ENVELOPE_ARTIFACT.md",
        source_field="evidence_envelope.market_topology",
    )
    st = _state(
        readiness_status="VENUE_INSTRUMENT_STATE_SUSPENDED",
        source_contract="STATE_CONTRACT.md",
        source_artifact="docs/handoff/STATE_ARTIFACT.md",
        source_field="venue_instrument.readiness_state",
    )
    result = venue_instrument_readiness_preflight(evidence_envelope=env, readiness_state=st)
    assert type(result) is NoEligibleHaltPacket
    assert result.source_contract == env.source_contract
    assert result.source_artifact == env.source_artifact
    assert result.source_field == env.source_field
    assert result.source_contract != st.source_contract
    assert result.source_artifact != st.source_artifact
    assert result.source_field != st.source_field


def test_blocked_provenance_comes_from_envelope_not_readiness_state():
    env = _envelope(source_contract="ENVELOPE_CONTRACT.md")
    st = _state(venue="DIFFERENT_VALUE", source_contract="STATE_CONTRACT.md")
    result = venue_instrument_readiness_preflight(evidence_envelope=env, readiness_state=st)
    assert type(result) is BlockedPacket
    assert result.source_contract == env.source_contract
    assert result.source_contract != st.source_contract


def test_inputs_not_mutated_by_gate():
    env = _envelope()
    st = _state()
    before_env = dict(vars(env))
    before_st = dict(vars(st))
    venue_instrument_readiness_preflight(evidence_envelope=env, readiness_state=st)
    assert dict(vars(env)) == before_env
    assert dict(vars(st)) == before_st


# --- group 10: gate present + carrier purity intact + no threshold/profitability debris ---

def test_gate_symbols_present_and_carrier_surface_unchanged():
    import phase5.venue_instrument_readiness_boundary as mod
    assert hasattr(mod, "VenueInstrumentReadinessGate")
    assert hasattr(mod, "venue_instrument_readiness_preflight")
    assert callable(mod.venue_instrument_readiness_preflight)
    assert VenueInstrumentReadinessGate.preflight is venue_instrument_readiness_preflight
    # the Slice 1 carrier surface must remain present and unchanged in name
    assert hasattr(mod, "VenueInstrumentReadinessStateContext")
    assert hasattr(mod, "make_venue_instrument_readiness_state_context")


def test_source_scan_gate_has_no_threshold_or_profitability_or_arithmetic_debris():
    import phase5.venue_instrument_readiness_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        low = f.read().lower()
    # No threshold / net-edge / decimal arithmetic debris copied from the profitability gate.
    # (Bare "profitability" is intentionally NOT banned: the legitimate upstream-envelope import
    # references the `post_profitability_evidence_envelope_boundary` module.)
    for debris in ["threshold", "net_edge", "decimal", "below_threshold",
                   "profitabilitythreshold", "net_edge_profitability", "gross_edge",
                   "calculate_net_edge", "localcontext"]:
        assert debris not in low, f"threshold/profitability/arithmetic debris present: {debris}"


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
