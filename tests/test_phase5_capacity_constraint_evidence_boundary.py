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
import ast
import inspect
import operator
import re

import pytest

from phase5.capacity_constraint_evidence_boundary import (
    CapacityConstraintEvidenceContext,
    make_capacity_constraint_evidence_context,
    CapacityConstraintEvidenceContextTypeError,
    CapacityConstraintEvidenceContextTruthinessError,
    CapacityConstraintEvidenceContextCoercionError,
    CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME,
    BOUNDARY_VERSION,
    # --- Slice 0A: gate namespace, blocked-reason constants, errors, preflight stub ---
    CapacityConstraintGate,
    capacity_constraint_preflight,
    CapacityConstraintGateTypeError,
    CapacityConstraintMisroutedHaltCarrierError,
    CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE,
    CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE,
    CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE,
    CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH,
    CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH,
    CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE,
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

# Symbols that must STILL not appear after Slice 0B. The full structural-join boundary class
# (`CapacityConstraintEvidenceBoundary`) remains out of scope. NOTE: the four upstream carrier types
# and the two halt-packet types (`BlockedPacket`, `NoEligibleHaltPacket`) are now legitimately
# referenced by Slice 0B (exact type guard + misroute guard), so they are deliberately NOT forbidden.
FORBIDDEN_RUNTIME_SYMBOLS = (
    "CapacityConstraintEvidenceBoundary",
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
    # Precise tripwire: a forbidden concept token is a violation only when it appears as a whole
    # underscore-delimited identifier word (e.g. a field/variable named `route` or `final_capacity`),
    # NOT as a CamelCase substring of an unrelated required symbol such as the spec-mandated
    # `CapacityConstraintMisroutedHaltCarrierError` (which contains "route" inside "Misrouted").
    # Identifier-word granularity matches this snake_case codebase.
    src = _src()
    identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", src))
    for tok in FORBIDDEN_FIELD_TOKENS:
        needle = "_" + tok + "_"
        for ident in identifiers:
            assert needle not in ("_" + ident + "_"), \
                f"forbidden field token used as identifier word: {tok!r} (in {ident!r})"


def test_no_io_or_time_imports():
    src = _src()
    for banned in ("import os", "import time", "import socket", "import datetime",
                   "import requests", "urllib", "open("):
        assert banned not in src, f"carrier module must not reference {banned!r}"


# ===================================================================================================
# Slice 0A: stateless CapacityConstraintGate namespace + blocked-reason constants + gate error
# classes + an EXACT keyword-only `capacity_constraint_preflight` fail-fast stub (NotImplementedError
# only) + AST/operator/import lock. Slice 0A deliberately implements NO pass path, NO blocked-branch
# logic, NO parsing/comparison, NO make_blocked_packet call, and NO CapacityConstraintEvidenceBoundary.
# ===================================================================================================

_BLOCKED_REASON_CONSTANTS = (
    CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE,
    CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE,
    CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE,
    CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH,
    CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH,
    CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE,
)

PREFLIGHT_PARAM_ORDER = (
    "evidence_envelope",
    "venue_readiness",
    "liquidity_evidence",
    "capital_evidence",
)

STUB_MESSAGE = "Slice 0 structural join and branch logic not yet implemented"

# AST lock vocabularies (Slice 0A).
FORBIDDEN_CALL_NAMES = ("float", "min", "max", "sum", "round", "sorted")
FORBIDDEN_OPERATOR_NODES = (
    ast.Add, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.MatMult, ast.USub,
)
FORBIDDEN_IMPORT_ROOTS = (
    "math", "statistics", "numpy", "pandas", "datetime", "time", "os", "socket",
    "requests", "urllib", "subprocess", "json",
)


def _ast_tree():
    import phase5.capacity_constraint_evidence_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        return ast.parse(f.read())


# --- blocked-reason constants (name == value, exact str) ---

def test_blocked_reason_constants_name_equals_value():
    assert CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE == "CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE"
    assert CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE == "CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE"
    assert CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE == "CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE"
    assert CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH == "CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH"
    assert CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH == "CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH"
    assert CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE == "CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE"


def test_blocked_reason_constants_are_exact_str():
    for c in _BLOCKED_REASON_CONSTANTS:
        assert type(c) is str


def test_blocked_reason_constants_are_distinct():
    assert len(set(_BLOCKED_REASON_CONSTANTS)) == 6


# --- gate error classes ---

def test_gate_type_error_is_typeerror_subclass():
    assert issubclass(CapacityConstraintGateTypeError, TypeError)


def test_misrouted_halt_carrier_error_is_typeerror_subclass():
    assert issubclass(CapacityConstraintMisroutedHaltCarrierError, TypeError)


def test_gate_error_classes_are_distinct():
    assert CapacityConstraintGateTypeError is not CapacityConstraintMisroutedHaltCarrierError
    assert not issubclass(CapacityConstraintGateTypeError, CapacityConstraintMisroutedHaltCarrierError)
    assert not issubclass(CapacityConstraintMisroutedHaltCarrierError, CapacityConstraintGateTypeError)


# --- stateless gate namespace ---

def test_gate_is_stateless_empty_slots():
    assert CapacityConstraintGate.__slots__ == ()


def test_gate_instance_has_no_dict():
    g = CapacityConstraintGate()
    assert not hasattr(g, "__dict__")
    with pytest.raises((AttributeError, TypeError)):
        g.injected = "x"


def test_gate_preflight_is_staticmethod_resolving_to_the_function():
    assert isinstance(inspect.getattr_static(CapacityConstraintGate, "preflight"), staticmethod)
    assert CapacityConstraintGate.preflight is capacity_constraint_preflight


# --- preflight stub: exact keyword-only signature ---

def test_preflight_signature_is_exact_keyword_only_no_defaults():
    sig = inspect.signature(capacity_constraint_preflight)
    params = list(sig.parameters.values())
    assert tuple(p.name for p in params) == PREFLIGHT_PARAM_ORDER
    for p in params:
        assert p.kind is inspect.Parameter.KEYWORD_ONLY, f"{p.name} must be keyword-only"
        assert p.default is inspect.Parameter.empty, f"{p.name} must have no default"
        assert p.annotation is inspect.Parameter.empty or p.annotation is not None


def test_preflight_rejects_positional_args():
    with pytest.raises(TypeError):
        capacity_constraint_preflight(object(), object(), object(), object())


def test_preflight_rejects_extra_kwargs():
    with pytest.raises(TypeError):
        capacity_constraint_preflight(
            evidence_envelope=object(),
            venue_readiness=object(),
            liquidity_evidence=object(),
            capital_evidence=object(),
            surprise_kw=object(),
        )


def test_preflight_requires_all_four_kwargs():
    full = dict(
        evidence_envelope=object(),
        venue_readiness=object(),
        liquidity_evidence=object(),
        capital_evidence=object(),
    )
    for missing in PREFLIGHT_PARAM_ORDER:
        partial = {k: v for k, v in full.items() if k != missing}
        with pytest.raises(TypeError):
            capacity_constraint_preflight(**partial)


# NOTE: the Slice 0A `NotImplementedError`-only stub assertions (preflight raised the stub message,
# inspected no inputs, built no carrier) were intentionally SUPERSEDED by Slice 0B. The live contract
# — exact type guard, misroute guard, and all-agree verbatim pass path — is pinned by the Slice 0B
# test section near the end of this file. `STUB_MESSAGE` is retained only as historical documentation.


# --- AST / operator / import lock (inspects AST nodes, not raw text) ---

def test_ast_forbids_dangerous_builtin_calls():
    tree = _ast_tree()
    offenders = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in FORBIDDEN_CALL_NAMES
    ]
    assert offenders == [], f"forbidden builtin call(s) present: {offenders}"


def test_ast_forbids_arithmetic_operator_nodes():
    tree = _ast_tree()
    offenders = [
        type(node).__name__
        for node in ast.walk(tree)
        if isinstance(node, FORBIDDEN_OPERATOR_NODES)
    ]
    assert offenders == [], f"forbidden operator node(s) present: {offenders}"


def test_ast_forbids_forbidden_imports():
    tree = _ast_tree()
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                    offenders.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                offenders.append(module)
    assert offenders == [], f"forbidden import(s) present: {offenders}"


def test_ast_lock_does_not_flag_dunder_methods_or_docstrings():
    # The carrier defines __float__/__int__/__str__/__bytes__ and carries docstrings that mention
    # words like "join"/"audit". The AST lock keys on Call->Name nodes and operator/import nodes, so
    # method definitions and string literals must never be treated as forbidden calls/operators.
    tree = _ast_tree()
    method_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert {"__float__", "__int__", "__str__", "__bytes__"} <= method_names
    # And the three locks above must still hold given those definitions exist:
    offenders = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in FORBIDDEN_CALL_NAMES
    ]
    assert offenders == []


# --- Slice 0A scope guard: the full structural-join boundary remains unimplemented ---

def test_capacity_constraint_evidence_boundary_remains_unimplemented():
    import phase5.capacity_constraint_evidence_boundary as mod
    assert not hasattr(mod, "CapacityConstraintEvidenceBoundary")


# ===================================================================================================
# Slice 0B: capacity_constraint_preflight gains (1) an EXACT input type guard, (2) a misroute
# halt-carrier guard, and (3) the all-agree pass path that returns a CapacityConstraintEvidenceContext
# built via the existing 12-param factory with VERBATIM source_* transfer.
#
# BOUNDARY (named per spec): Slice 0B is NOT final boundary pass readiness. It is NOT live-wirable
# until Slice 0C adds fail-closed structural convergence checks (identity / unit / stale / size). This
# batch deliberately implements and tests NEITHER pass NOR block behavior for structurally divergent
# carriers — that is exclusively Slice 0C. No blocked packet, no Decimal parsing, no epoch/tolerance
# parsing, no make_blocked_packet here.
# ===================================================================================================

from phase5.post_profitability_evidence_envelope_boundary import (
    make_post_profitability_evidence_envelope,
    BOUNDARY_VERSION as _PPE_BV,
)
from phase5.venue_instrument_readiness_boundary import (
    make_venue_instrument_readiness_state_context,
    BOUNDARY_VERSION as _VEN_BV,
)
from phase5.liquidity_capacity_evidence_boundary import (
    make_liquidity_capacity_evidence_context,
    BOUNDARY_VERSION as _LIQ_BV,
)
from phase5.capital_margin_evidence_boundary import (
    make_capital_margin_evidence_context,
    BOUNDARY_VERSION as _CAP_BV,
)
from phase5.blocked_result_boundary import make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import make_no_eligible_halt_packet
from phase5.net_edge_calculator_boundary import NetEdgeCalculationResult


# Shared structurally all-agree identity for the four carriers (real, valid values).
_AGREE = dict(
    venue="HYPERLIQUID",
    instrument_id="BTC-PERP",
    base_asset="BTC",
    quote_asset="USD",
)


def _net_edge_calculated():
    # The post-profitability envelope requires a real NetEdgeCalculationResult. There is no public
    # factory (it is produced by the calculator), so we build it exactly as the post-profitability
    # boundary test does: object.__new__ + object.__setattr__ with the canonical valid field set.
    r = object.__new__(NetEdgeCalculationResult)
    fields = dict(
        component_name="phase5_net_edge_calculator_boundary",
        origin_component="phase5_net_edge_calculator_boundary",
        origin_result_status="PRE_NET_EDGE_CALCULATION_INPUT_ACCEPTED",
        status="NET_EDGE_CALCULATED",
        gross_edge_value="10",
        gross_edge_unit="bps",
        total_cost_value="2",
        total_cost_unit="bps",
        net_edge_value="8",
        net_edge_unit="bps",
        cost_component_count="1",
        source_contract="phase5_net_edge_calculator_boundary_implementation_planning.md",
        source_artifact="docs/handoff/phase5_net_edge_calculator_boundary_implementation_planning.md",
        source_field="net_edge.calculated_value",
        calculation_method="NET_EDGE_V1_GROSS_MINUS_SUM_COSTS_SAME_UNIT",
        boundary_version="phase5.net_edge_calculator_boundary.v0",
    )
    for k, v in fields.items():
        object.__setattr__(r, k, v)
    return r


def _make_ppe():
    return make_post_profitability_evidence_envelope(
        calculation_result=_net_edge_calculated(),
        side="LONG",
        observed_size="1.5",
        size_unit="BTC",
        observed_at_epoch_ms="1781637248000",
        staleness_threshold_ms="60000",
        source_contract="phase5_post_profitability_evidence_envelope_implementation_planning.md",
        source_artifact="docs/handoff/phase5_post_profitability_evidence_envelope_implementation_planning.md",
        source_field="evidence_envelope.market_topology",
        boundary_version=_PPE_BV,
        **_AGREE,
    )


def _make_ven():
    return make_venue_instrument_readiness_state_context(
        readiness_status="VENUE_INSTRUMENT_STATE_ACTIVE",
        source_contract="phase5_venue_instrument_readiness_implementation_planning.md",
        source_artifact="docs/handoff/phase5_venue_instrument_readiness_implementation_planning.md",
        source_field="venue_instrument.readiness_state",
        state_id="STATE-001",
        boundary_version=_VEN_BV,
        **_AGREE,
    )


def _make_liq():
    return make_liquidity_capacity_evidence_context(
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
        boundary_version=_LIQ_BV,
        estimated_slippage_bps="2.5",
        **_AGREE,
    )


def _make_cap():
    return make_capital_margin_evidence_context(
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
        boundary_version=_CAP_BV,
        **_AGREE,
    )


def _all_agree_inputs():
    return dict(
        evidence_envelope=_make_ppe(),
        venue_readiness=_make_ven(),
        liquidity_evidence=_make_liq(),
        capital_evidence=_make_cap(),
    )


def _blocked_packet():
    return make_blocked_packet(
        component_name="x",
        origin_component="x",
        origin_result_status="s",
        status="s",
        blocked_status=None,
        reason_code="r",
        missing_or_invalid_field=None,
        source_contract="c",
        source_artifact="a",
        source_field="f",
        deterministic_next_action="HALT_FAIL_CLOSED",
        human_review_required=True,
        may_retry_after_evidence=True,
        created_from_contract="c",
        boundary_version="v",
    )


def _no_eligible_packet():
    return make_no_eligible_halt_packet(
        component_name="x",
        origin_component="x",
        origin_result_status="NO_ELIGIBLE",
        status="NO_ELIGIBLE",
        no_eligible_reason="R",
        source_contract="c",
        source_artifact="a",
        source_field="f",
        deterministic_next_action="HALT_BYPASS_NO_ELIGIBLE",
        boundary_version="v",
    )


# The exact 12 (factory_param -> (input_slot, carrier_attr)) verbatim mapping the pass path must honor.
_PASS_MAPPING = {
    "post_profitability_source_contract": ("evidence_envelope", "source_contract"),
    "post_profitability_source_artifact": ("evidence_envelope", "source_artifact"),
    "post_profitability_source_field": ("evidence_envelope", "source_field"),
    "venue_readiness_source_contract": ("venue_readiness", "source_contract"),
    "venue_readiness_source_artifact": ("venue_readiness", "source_artifact"),
    "venue_readiness_source_field": ("venue_readiness", "source_field"),
    "liquidity_capacity_source_contract": ("liquidity_evidence", "source_contract"),
    "liquidity_capacity_source_artifact": ("liquidity_evidence", "source_artifact"),
    "liquidity_capacity_source_field": ("liquidity_evidence", "source_field"),
    "capital_margin_source_contract": ("capital_evidence", "source_contract"),
    "capital_margin_source_artifact": ("capital_evidence", "source_artifact"),
    "capital_margin_source_field": ("capital_evidence", "source_field"),
}


# --- Slice 0B happy / pass path (all-agree fixture only) ---

def test_pass_returns_capacity_constraint_evidence_context():
    inputs = _all_agree_inputs()
    ctx = capacity_constraint_preflight(**inputs)
    assert type(ctx) is CapacityConstraintEvidenceContext


def test_pass_via_gate_namespace_staticmethod():
    inputs = _all_agree_inputs()
    ctx = CapacityConstraintGate.preflight(**inputs)
    assert type(ctx) is CapacityConstraintEvidenceContext


def test_pass_transfers_all_twelve_source_fields_verbatim():
    inputs = _all_agree_inputs()
    ctx = capacity_constraint_preflight(**inputs)
    for factory_param, (slot, attr) in _PASS_MAPPING.items():
        expected = getattr(inputs[slot], attr)
        assert getattr(ctx, factory_param) == expected, f"{factory_param} not verbatim from {slot}.{attr}"


def test_pass_sets_identity_fields_internally_not_from_inputs():
    inputs = _all_agree_inputs()
    ctx = capacity_constraint_preflight(**inputs)
    assert ctx.component_name == EXPECTED_COMPONENT
    assert ctx.boundary_version == BOUNDARY_VERSION


def test_pass_provenance_distinct_per_carrier_not_cross_wired():
    # Each carrier carries a distinct source_contract; verify the pass path routes each carrier's
    # provenance into its OWN factory slot (no cross-wiring between carriers).
    inputs = _all_agree_inputs()
    ctx = capacity_constraint_preflight(**inputs)
    assert ctx.post_profitability_source_contract == inputs["evidence_envelope"].source_contract
    assert ctx.venue_readiness_source_contract == inputs["venue_readiness"].source_contract
    assert ctx.liquidity_capacity_source_contract == inputs["liquidity_evidence"].source_contract
    assert ctx.capital_margin_source_contract == inputs["capital_evidence"].source_contract
    # cross-check: they are genuinely different strings (otherwise the verbatim test is vacuous)
    contracts = {
        ctx.post_profitability_source_contract,
        ctx.venue_readiness_source_contract,
        ctx.liquidity_capacity_source_contract,
        ctx.capital_margin_source_contract,
    }
    assert len(contracts) == 4


# --- Slice 0B exact type guard (any wrong type -> CapacityConstraintGateTypeError, never a result) ---

def test_each_slot_rejects_plain_wrong_type_with_gate_type_error():
    base = _all_agree_inputs()
    for slot in ("evidence_envelope", "venue_readiness", "liquidity_evidence", "capital_evidence"):
        bad = dict(base)
        bad[slot] = object()
        with pytest.raises(CapacityConstraintGateTypeError):
            capacity_constraint_preflight(**bad)


def test_type_guard_rejects_carrier_in_wrong_slot():
    # A real-but-wrong carrier placed in the wrong slot must be rejected by exact type(x) is T.
    base = _all_agree_inputs()
    swapped = dict(base)
    swapped["evidence_envelope"] = base["venue_readiness"]  # VEN where PPE is required
    with pytest.raises(CapacityConstraintGateTypeError):
        capacity_constraint_preflight(**swapped)


def test_type_guard_rejects_string_and_none():
    base = _all_agree_inputs()
    for bad_value in (None, "PostProfitabilityEvidenceEnvelope", 0):
        bad = dict(base)
        bad["capital_evidence"] = bad_value
        with pytest.raises(CapacityConstraintGateTypeError):
            capacity_constraint_preflight(**bad)


def test_gate_type_error_path_returns_no_context():
    base = _all_agree_inputs()
    base["liquidity_evidence"] = object()
    try:
        capacity_constraint_preflight(**base)
    except CapacityConstraintGateTypeError:
        pass
    else:
        pytest.fail("wrong type must raise CapacityConstraintGateTypeError, not return")


# --- Slice 0B misroute guard (exact halt packet in any slot -> MisroutedHaltCarrierError) ---

def test_blocked_packet_in_any_slot_raises_misroute():
    base = _all_agree_inputs()
    for slot in ("evidence_envelope", "venue_readiness", "liquidity_evidence", "capital_evidence"):
        bad = dict(base)
        bad[slot] = _blocked_packet()
        with pytest.raises(CapacityConstraintMisroutedHaltCarrierError):
            capacity_constraint_preflight(**bad)


def test_no_eligible_packet_in_any_slot_raises_misroute():
    base = _all_agree_inputs()
    for slot in ("evidence_envelope", "venue_readiness", "liquidity_evidence", "capital_evidence"):
        bad = dict(base)
        bad[slot] = _no_eligible_packet()
        with pytest.raises(CapacityConstraintMisroutedHaltCarrierError):
            capacity_constraint_preflight(**bad)


def test_misroute_takes_precedence_over_generic_type_error():
    # A halt packet is a wrong type, but it must surface as the SPECIFIC misroute error, never the
    # generic gate type error.
    base = _all_agree_inputs()
    base["venue_readiness"] = _blocked_packet()
    with pytest.raises(CapacityConstraintMisroutedHaltCarrierError):
        capacity_constraint_preflight(**base)


def test_misroute_path_returns_no_context_or_packet():
    base = _all_agree_inputs()
    base["evidence_envelope"] = _no_eligible_packet()
    result = None
    try:
        result = capacity_constraint_preflight(**base)
    except CapacityConstraintMisroutedHaltCarrierError:
        pass
    else:
        pytest.fail("misroute must raise, not return a context/packet")
    assert result is None


# --- Slice 0B boundary: divergent behavior deferred to 0C; 0C machinery must remain absent ---

def test_slice0b_is_not_final_pass_readiness_no_0c_machinery():
    # NAMED BOUNDARY: Slice 0B is NOT final pass readiness and is NOT live-wirable before Slice 0C.
    # Enforce that no structural-convergence / blocked-packet machinery has leaked in early. Tokens
    # are chosen to detect actual usage (call form / type name), not prose mentions in comments:
    # `make_blocked_packet(` is a call, `Decimal(` is a parse, `.compare(` is a size comparison.
    src = _src()
    for absent in ("make_blocked_packet(", "Decimal(", ".compare(", "_epoch_ms", "tolerance_ms"):
        assert absent not in src, f"0C-only machinery leaked into Slice 0B runtime: {absent!r}"


def test_no_isinstance_used_in_runtime():
    # The contract requires exact type(x) is T; isinstance (subclass-permissive) is forbidden as an
    # actual CALL. AST-based so prose mentions of "isinstance" in docstrings/comments don't trip it.
    tree = _ast_tree()
    offenders = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "isinstance"
    ]
    assert offenders == [], "isinstance call(s) present in runtime"
