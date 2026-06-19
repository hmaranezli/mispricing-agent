"""tests/test_phase5_capacity_constraint_evidence_boundary.py — pins Slice 1 (carrier-only) of the
`phase5_capacity_constraint_evidence_boundary` component.

Slice 1: `CapacityConstraintEvidenceContext` is a frozen, repr-safe, anti-truthiness, anti-coercion,
factory-only, slotted carrier that wraps only explicitly supplied per-source provenance references.
Every caller-supplied field is an exact, non-empty, non-whitespace ``str`` stored verbatim — the
carrier performs NO audit, NO join, NO comparison, NO derivation, and NO decision. It is strictly a
supplied-evidence descriptor; the structural multi-source join auditor (Slice 0) is a separate,
separately authorized task and is deliberately NOT implemented in this module. NO ORDER EXISTS.

The factory accepts exactly the twelve per-source provenance triplet parameters; ``component_name``
and ``boundary_version`` are NOT caller parameters — they are set internally from module constants and
cannot be spoofed, overridden, or injected by the caller.
"""
import operator

import pytest

from phase5.capacity_constraint_evidence_boundary import (
    CapacityConstraintEvidenceContext,
    make_capacity_constraint_evidence_context,
    CapacityConstraintEvidenceContextTypeError,
    CapacityConstraintEvidenceContextTruthinessError,
    CapacityConstraintEvidenceContextCoercionError,
    CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME,
    BOUNDARY_VERSION,
)

EXPECTED_COMPONENT = "phase5_capacity_constraint_evidence_boundary"

# The closed 14-field stored set in exact dataclass field order.
EXPECTED_FIELDS = (
    "component_name",
    "boundary_version",
    "post_profitability_source_contract",
    "post_profitability_source_artifact",
    "post_profitability_source_field",
    "venue_readiness_source_contract",
    "venue_readiness_source_artifact",
    "venue_readiness_source_field",
    "liquidity_capacity_source_contract",
    "liquidity_capacity_source_artifact",
    "liquidity_capacity_source_field",
    "capital_margin_source_contract",
    "capital_margin_source_artifact",
    "capital_margin_source_field",
)

# The exactly-twelve caller-supplied keyword-only factory parameters (component_name and
# boundary_version are set internally, not supplied by the caller).
FACTORY_PARAMS = tuple(
    f for f in EXPECTED_FIELDS if f not in ("component_name", "boundary_version")
)

# Fields/tokens the carrier must never declare or store (status / computed / runtime / record-id).
FORBIDDEN_FIELD_TOKENS = (
    "join_status", "binding_status", "identity_status", "freshness_status", "unit_status",
    "audited_evidence_count", "observed_size", "available_capacity", "required_capital",
    "final_capacity", "computed_min", "order_size", "allocation", "exposure", "balance",
    "route", "reservation", "wallet", "batch_id", "run_id", "observation_id", "provenance_status",
)

# Symbols / imports that must NOT appear in the Slice 1 carrier-only module (Slice 0 boundary scope).
FORBIDDEN_RUNTIME_SYMBOLS = (
    "CapacityConstraintEvidenceBoundary",
    "preflight",
    "BlockedPacket",
    "NoEligibleHaltPacket",
    "PostProfitabilityEvidenceEnvelope",
    "VenueInstrumentReadinessStateContext",
    "LiquidityCapacityEvidenceContext",
    "CapitalMarginEvidenceContext",
)


def _kwargs(**overrides):
    base = dict(
        post_profitability_source_contract="phase5_post_profitability_evidence_envelope.md",
        post_profitability_source_artifact="docs/handoff/post_profitability.md",
        post_profitability_source_field="post_profitability.net_edge",
        venue_readiness_source_contract="phase5_venue_instrument_readiness.md",
        venue_readiness_source_artifact="docs/handoff/venue_readiness.md",
        venue_readiness_source_field="venue_readiness.state",
        liquidity_capacity_source_contract="phase5_liquidity_capacity_evidence_boundary.md",
        liquidity_capacity_source_artifact="docs/handoff/liquidity_capacity.md",
        liquidity_capacity_source_field="liquidity_capacity.depth",
        capital_margin_source_contract="phase5_capital_margin_evidence_boundary.md",
        capital_margin_source_artifact="docs/handoff/capital_margin.md",
        capital_margin_source_field="capital_margin.free_capital",
    )
    base.update(overrides)
    return base


def _make(**overrides):
    return make_capacity_constraint_evidence_context(**_kwargs(**overrides))


def _src():
    import phase5.capacity_constraint_evidence_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        return f.read()


# --- constants / shape ---

def test_component_constant_and_boundary_version():
    assert CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME == EXPECTED_COMPONENT
    assert BOUNDARY_VERSION == "phase5.capacity_constraint_evidence_boundary.v0"


def test_factory_builds_carrier_with_exact_field_set():
    ctx = _make()
    assert type(ctx) is CapacityConstraintEvidenceContext
    for f in EXPECTED_FIELDS:
        assert hasattr(ctx, f), f"missing field {f}"


def test_declared_field_order_is_the_closed_14_set():
    from dataclasses import fields as dataclass_fields
    assert tuple(f.name for f in dataclass_fields(CapacityConstraintEvidenceContext)) == \
        EXPECTED_FIELDS
    assert len(EXPECTED_FIELDS) == 14


def test_expected_field_names_guard_matches_dataclass_order():
    import phase5.capacity_constraint_evidence_boundary as mod
    assert mod._EXPECTED_FIELD_NAMES == EXPECTED_FIELDS


def test_factory_param_count_is_exactly_twelve():
    assert len(FACTORY_PARAMS) == 12


def test_field_values_preserved_verbatim():
    kw = _kwargs()
    ctx = make_capacity_constraint_evidence_context(**kw)
    for f in FACTORY_PARAMS:
        assert getattr(ctx, f) == kw[f]


# --- factory discipline ---

def test_factory_is_keyword_only():
    with pytest.raises(TypeError):
        make_capacity_constraint_evidence_context("phase5_post_profitability.md")  # positional


def test_factory_requires_all_twelve_params():
    kw = _kwargs()
    for f in FACTORY_PARAMS:
        partial = {k: v for k, v in kw.items() if k != f}
        with pytest.raises(TypeError):
            make_capacity_constraint_evidence_context(**partial)


def test_component_name_is_not_a_factory_parameter():
    with pytest.raises(TypeError):
        make_capacity_constraint_evidence_context(**_kwargs(component_name="x"))


def test_boundary_version_is_not_a_factory_parameter():
    with pytest.raises(TypeError):
        make_capacity_constraint_evidence_context(**_kwargs(boundary_version="x"))


def test_factory_sets_identity_fields_internally_from_constants():
    ctx = _make()
    assert ctx.component_name == CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME
    assert ctx.component_name == EXPECTED_COMPONENT
    assert ctx.boundary_version == BOUNDARY_VERSION
    assert ctx.boundary_version == "phase5.capacity_constraint_evidence_boundary.v0"


def test_factory_rejects_unexpected_keyword():
    with pytest.raises(TypeError):
        make_capacity_constraint_evidence_context(**_kwargs(surprise_kw="x"))


# --- direct construction is physically blocked (all forms) ---

def test_direct_no_arg_construction_blocked():
    with pytest.raises(CapacityConstraintEvidenceContextTypeError):
        CapacityConstraintEvidenceContext()


def test_direct_positional_construction_blocked():
    with pytest.raises(CapacityConstraintEvidenceContextTypeError):
        CapacityConstraintEvidenceContext("x")


def test_direct_keyword_construction_blocked():
    with pytest.raises(CapacityConstraintEvidenceContextTypeError):
        CapacityConstraintEvidenceContext(component_name="x")


# --- strict memory discipline: slots, no __dict__, no dynamic attribute injection ---

def test_instance_has_no_dict():
    ctx = _make()
    assert not hasattr(ctx, "__dict__"), "carrier must be slotted with no instance __dict__"


def test_dynamic_attribute_injection_rejected():
    ctx = _make()
    with pytest.raises((AttributeError, TypeError)):
        ctx.injected_attr = "x"


# --- string field discipline (uniform: exact non-empty non-whitespace str, verbatim) ---

def test_all_caller_fields_must_be_exact_str_type_error():
    for f in FACTORY_PARAMS:
        for bad in [None, 1, 1.0, 1j, b"x", {}, [], (), object(), True, False]:
            with pytest.raises(CapacityConstraintEvidenceContextTypeError):
                _make(**{f: bad})


def test_string_fields_reject_str_subclass():
    class _S(str):
        pass
    for f in FACTORY_PARAMS:
        with pytest.raises(CapacityConstraintEvidenceContextTypeError):
            _make(**{f: _S("X")})


def test_string_fields_reject_duck_typed_string_like():
    class _DuckStr:
        def __str__(self):
            return "looks-like-a-string"
    for f in FACTORY_PARAMS:
        with pytest.raises(CapacityConstraintEvidenceContextTypeError):
            _make(**{f: _DuckStr()})


def test_empty_or_whitespace_string_fields_value_error():
    for f in FACTORY_PARAMS:
        for bad in ["", "   ", "\t", "\n", " \t\n "]:
            with pytest.raises(ValueError):
                _make(**{f: bad})


def test_carrier_does_no_validation_stores_verbatim():
    # Slice 1 carrier performs NO grammar/semantic validation: any non-empty, non-whitespace str is
    # accepted and preserved verbatim (all auditing belongs to the future Slice 0 join, not here).
    for f in FACTORY_PARAMS:
        for weird in ["abc", "1.0e3", "-5", "0", "NaN", "1,000", "banana", "../etc"]:
            ctx = _make(**{f: weird})
            assert getattr(ctx, f) == weird, f"{f}={weird!r} must be stored verbatim"


# --- immutability ---

def test_carrier_is_frozen():
    ctx = _make()
    with pytest.raises(Exception):
        ctx.post_profitability_source_contract = "OTHER"
    with pytest.raises(Exception):
        ctx.component_name = "x"
    with pytest.raises(Exception):
        ctx.boundary_version = "x"


# --- anti-truthiness / anti-coercion ---

def test_anti_truthiness():
    ctx = _make()
    with pytest.raises(CapacityConstraintEvidenceContextTruthinessError):
        bool(ctx)
    with pytest.raises(CapacityConstraintEvidenceContextTruthinessError):
        len(ctx)


def test_anti_coercion():
    ctx = _make()
    for op in (int, float, complex, str, bytes):
        with pytest.raises(CapacityConstraintEvidenceContextCoercionError):
            op(ctx)
    with pytest.raises(CapacityConstraintEvidenceContextCoercionError):
        operator.index(ctx)


# --- safe repr ---

def test_repr_exposes_only_safe_identifier_fields():
    ctx = _make(
        post_profitability_source_contract="SECRETPPC",
        post_profitability_source_artifact="SECRETPPA",
        post_profitability_source_field="SECRETPPF",
        venue_readiness_source_contract="SECRETVRC",
        venue_readiness_source_artifact="SECRETVRA",
        venue_readiness_source_field="SECRETVRF",
        liquidity_capacity_source_contract="SECRETLCC",
        liquidity_capacity_source_artifact="SECRETLCA",
        liquidity_capacity_source_field="SECRETLCF",
        capital_margin_source_contract="SECRETCMC",
        capital_margin_source_artifact="SECRETCMA",
        capital_margin_source_field="SECRETCMF",
    )
    r = repr(ctx)
    assert "CapacityConstraintEvidenceContext(" in r
    assert EXPECTED_COMPONENT in r
    assert BOUNDARY_VERSION in r
    for secret in ("SECRETPPC", "SECRETPPA", "SECRETPPF", "SECRETVRC", "SECRETVRA", "SECRETVRF",
                   "SECRETLCC", "SECRETLCA", "SECRETLCF", "SECRETCMC", "SECRETCMA", "SECRETCMF"):
        assert secret not in r, f"provenance value leaked in repr: {secret}"


def test_error_message_does_not_leak_raw_value():
    class _S(str):
        pass
    with pytest.raises(CapacityConstraintEvidenceContextTypeError) as exc:
        _make(post_profitability_source_field=_S("SUPERSECRETVALUE"))
    assert "SUPERSECRETVALUE" not in str(exc.value)


# --- forbidden runtime scope: this is a carrier-only module, not the Slice 0 boundary ---

def test_no_slice0_boundary_or_gate_symbols():
    src = _src()
    for sym in FORBIDDEN_RUNTIME_SYMBOLS:
        assert sym not in src, f"forbidden Slice 0 / cross-carrier symbol present: {sym}"


def test_no_forbidden_field_tokens_present():
    src = _src()
    for tok in FORBIDDEN_FIELD_TOKENS:
        assert tok not in src, f"forbidden field token present in carrier module: {tok}"


def test_no_io_or_time_imports():
    src = _src()
    for banned in ("import os", "import time", "import socket", "import datetime",
                   "import requests", "urllib", "open("):
        assert banned not in src, f"carrier module must not reference {banned!r}"
