"""tests/test_phase5_post_profitability_evidence_envelope_boundary.py — pins the atomic
implementation of the `phase5_post_profitability_evidence_envelope_boundary` component.

`PostProfitabilityEvidenceEnvelope` is a frozen, repr-safe, anti-truthiness, anti-coercion,
factory-only explicit evidence aggregation carrier. It wraps exactly one `NetEdgeCalculationResult`
(by identity) alongside explicitly supplied market-topology / size / time / provenance evidence. It
is NOT a profitability pass certificate, NOT proof that NetEdgeProfitabilityGate evaluated the
result, NOT actionable, NOT trade-ready, NOT executable, NOT paper-ready, NOT live-ready, and NOT an
order/signal/candidate. It performs no derivation, no parsing, no inference, no defaulting, no clock,
no network, and no case/unit normalization, and it returns no halt carrier and runs no market or
economic evaluation.
"""
import re

import pytest

from phase5.post_profitability_evidence_envelope_boundary import (
    PostProfitabilityEvidenceEnvelope,
    make_post_profitability_evidence_envelope,
    PostProfitabilityEvidenceEnvelopeTypeError,
    MisroutedHaltCarrierError,
    POST_PROFITABILITY_EVIDENCE_ENVELOPE_COMPONENT_NAME,
    BOUNDARY_VERSION,
)
from phase5.net_edge_calculator_boundary import NetEdgeCalculationResult
from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
)

EXPECTED_COMPONENT = "phase5_post_profitability_evidence_envelope_boundary"

EXPECTED_FIELDS = (
    "component_name",
    "calculation_result",
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "side",
    "observed_size",
    "size_unit",
    "observed_at_epoch_ms",
    "staleness_threshold_ms",
    "source_contract",
    "source_artifact",
    "source_field",
    "boundary_version",
)

# string fields supplied to the factory that are plain non-empty exact str (no numeric pattern)
PLAIN_STR_FIELDS = (
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "side",
    "size_unit",
    "source_contract",
    "source_artifact",
    "source_field",
    "boundary_version",
)


def _result(net_value="8", net_unit="bps"):
    r = object.__new__(NetEdgeCalculationResult)
    fields = dict(
        component_name="phase5_net_edge_calculator_boundary",
        origin_component="phase5_net_edge_calculator_boundary",
        origin_result_status="PRE_NET_EDGE_CALCULATION_INPUT_ACCEPTED",
        status="NET_EDGE_CALCULATED",
        gross_edge_value="10",
        gross_edge_unit=net_unit,
        total_cost_value="2",
        total_cost_unit=net_unit,
        net_edge_value=net_value,
        net_edge_unit=net_unit,
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


def _kwargs(**overrides):
    base = dict(
        calculation_result=_result(),
        venue="HYPERLIQUID",
        instrument_id="BTC-PERP",
        base_asset="BTC",
        quote_asset="USD",
        side="LONG",
        observed_size="0.5",
        size_unit="BTC",
        observed_at_epoch_ms="1781637248000",
        staleness_threshold_ms="60000",
        source_contract="phase5_post_profitability_evidence_envelope_implementation_planning.md",
        source_artifact="docs/handoff/phase5_post_profitability_evidence_envelope_implementation_planning.md",
        source_field="evidence_envelope.market_topology",
        boundary_version=BOUNDARY_VERSION,
    )
    base.update(overrides)
    return base


def _make(**overrides):
    return make_post_profitability_evidence_envelope(**_kwargs(**overrides))


def _blocked():
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


def _no_eligible():
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


# --- construction / shape ---

def test_component_constant_and_boundary_version():
    assert POST_PROFITABILITY_EVIDENCE_ENVELOPE_COMPONENT_NAME == EXPECTED_COMPONENT
    assert BOUNDARY_VERSION == "phase5.post_profitability_evidence_envelope_boundary.v0"


def test_factory_builds_envelope_with_exact_field_set_and_component_name():
    env = _make()
    assert type(env) is PostProfitabilityEvidenceEnvelope
    assert env.component_name == EXPECTED_COMPONENT
    for f in EXPECTED_FIELDS:
        assert hasattr(env, f), f"missing field {f}"


def test_field_values_preserved_verbatim():
    kw = _kwargs()
    env = make_post_profitability_evidence_envelope(**kw)
    for f in PLAIN_STR_FIELDS:
        assert getattr(env, f) == kw[f]
    assert env.observed_size == kw["observed_size"]
    assert env.observed_at_epoch_ms == kw["observed_at_epoch_ms"]
    assert env.staleness_threshold_ms == kw["staleness_threshold_ms"]


def test_factory_is_keyword_only():
    with pytest.raises(TypeError):
        make_post_profitability_evidence_envelope(_result())  # positional → TypeError


def test_direct_positional_construction_unsupported():
    with pytest.raises(TypeError):
        PostProfitabilityEvidenceEnvelope(_result())


# --- calculation_result type / identity / misroute ---

def test_calculation_result_stored_by_identity():
    r = _result()
    env = _make(calculation_result=r)
    assert env.calculation_result is r


def test_calculation_result_must_be_exact_netedgecalculationresult():
    for bad in [None, {}, 1.0, "x", object(), 7]:
        with pytest.raises(PostProfitabilityEvidenceEnvelopeTypeError):
            _make(calculation_result=bad)


def test_calculation_result_subclass_rejected():
    class _Sub(NetEdgeCalculationResult):
        pass
    sub = object.__new__(_Sub)
    for k, v in vars(_result()).items():
        object.__setattr__(sub, k, v)
    with pytest.raises(PostProfitabilityEvidenceEnvelopeTypeError):
        _make(calculation_result=sub)


def test_misrouted_blocked_packet_rejected():
    with pytest.raises(MisroutedHaltCarrierError):
        _make(calculation_result=_blocked())


def test_misrouted_no_eligible_packet_rejected():
    with pytest.raises(MisroutedHaltCarrierError):
        _make(calculation_result=_no_eligible())


# --- string field discipline ---

def test_string_fields_must_be_exact_str_type_error():
    for f in PLAIN_STR_FIELDS + ("observed_size", "observed_at_epoch_ms", "staleness_threshold_ms"):
        for bad in [None, 1, 1.0, b"x", {}, [], object(), True]:
            with pytest.raises(PostProfitabilityEvidenceEnvelopeTypeError):
                _make(**{f: bad})


def test_string_fields_reject_str_subclass():
    class _S(str):
        pass
    for f in PLAIN_STR_FIELDS:
        with pytest.raises(PostProfitabilityEvidenceEnvelopeTypeError):
            _make(**{f: _S("X")})
    # numeric-pattern fields are also exact-str only
    with pytest.raises(PostProfitabilityEvidenceEnvelopeTypeError):
        _make(observed_size=_S("5"))
    with pytest.raises(PostProfitabilityEvidenceEnvelopeTypeError):
        _make(observed_at_epoch_ms=_S("5"))


def test_empty_or_whitespace_string_fields_value_error():
    for f in PLAIN_STR_FIELDS:
        for bad in ["", "   ", "\t", "\n"]:
            with pytest.raises(ValueError):
                _make(**{f: bad})


# --- observed_size canonical unsigned decimal ---

def test_observed_size_accepts_valid_canonical_decimals():
    for good in ["0", "5", "12", "0.5", "12.34", "100.001"]:
        env = _make(observed_size=good)
        assert env.observed_size == good


def test_observed_size_rejects_malformed():
    for bad in ["01", "00", "007", "00.5", "-1", "+1", "1e3", "1E3", "NaN", "nan",
                "inf", ".5", "1.", "1.0.0", "1,000", " 5", "5 ", "0x5"]:
        with pytest.raises(ValueError):
            _make(observed_size=bad)


# --- epoch / staleness canonical unsigned integer ---

def test_epoch_and_staleness_accept_canonical_unsigned_integers():
    for good in ["0", "5", "1234", "1781637248000"]:
        env = _make(observed_at_epoch_ms=good, staleness_threshold_ms=good)
        assert env.observed_at_epoch_ms == good
        assert env.staleness_threshold_ms == good


def test_epoch_and_staleness_reject_malformed():
    for bad in ["01", "007", "-1", "+1", "1.0", "1e3", ".5", "NaN", "1,000", " 5", "5 "]:
        with pytest.raises(ValueError):
            _make(observed_at_epoch_ms=bad)
        with pytest.raises(ValueError):
            _make(staleness_threshold_ms=bad)


# --- carrier immutability ---

def test_carrier_is_frozen():
    env = _make()
    with pytest.raises(Exception):
        env.venue = "OTHER"
    with pytest.raises(Exception):
        env.component_name = "x"


# --- anti-truthiness / anti-coercion ---

def test_anti_truthiness():
    env = _make()
    with pytest.raises(TypeError):
        bool(env)
    with pytest.raises(TypeError):
        len(env)


def test_anti_coercion():
    env = _make()
    for op in (int, float, complex, str, bytes):
        with pytest.raises(TypeError):
            op(env)
    with pytest.raises(TypeError):
        import operator
        operator.index(env)


# --- safe repr ---

def test_repr_exposes_only_safe_identifier_fields():
    env = _make(
        venue="SECRETVENUE",
        instrument_id="SECRETINSTR",
        base_asset="SECRETBASE",
        quote_asset="SECRETQUOTE",
        side="SECRETSIDE",
        observed_size="123.456",
        size_unit="SECRETUNIT",
        observed_at_epoch_ms="999999999",
        staleness_threshold_ms="888888",
        source_artifact="docs/handoff/SECRETARTIFACT.md",
        source_field="SECRETFIELD",
    )
    text = repr(env)
    assert EXPECTED_COMPONENT in text
    for leak in ["SECRETVENUE", "SECRETINSTR", "SECRETBASE", "SECRETQUOTE", "SECRETSIDE",
                 "123.456", "SECRETUNIT", "999999999", "888888", "SECRETARTIFACT", "SECRETFIELD"]:
        assert leak not in text, f"repr leaked sensitive value: {leak}"


# --- never returns a halt carrier; never evaluates ---

def test_factory_returns_envelope_not_halt_carrier():
    env = _make()
    assert type(env) is PostProfitabilityEvidenceEnvelope
    assert not isinstance(env, BlockedPacket)
    assert not isinstance(env, NoEligibleHaltPacket)


# --- source-scan invariants (code-usage forms + banned semantics/names) ---

def test_source_scan_no_io_clock_normalization_or_recovery_language():
    import phase5.post_profitability_evidence_envelope_boundary as mod
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


def test_source_scan_no_banned_output_names_and_never_constructs_halt_carrier():
    import phase5.post_profitability_evidence_envelope_boundary as mod
    with open(mod.__file__, encoding="utf-8") as f:
        src = f.read()
    # Banned CamelCase output/actionability symbol names must never appear in runtime code.
    for banned in ["ActionableCandidate", "TradeCandidate", "ReadyEnvelope", "ExecutableSignal",
                   "Opportunity", "ExecutionPayload", "OrderIntent", "Fillable", "Tradable"]:
        assert banned not in src, f"banned output/actionability name present in runtime: {banned}"
    # Code-usage proof that no halt carrier is ever constructed/returned by this component.
    assert "make_blocked_packet(" not in src, "must not construct a BlockedPacket"
    assert "make_no_eligible_halt_packet(" not in src, "must not construct a NoEligibleHaltPacket"
