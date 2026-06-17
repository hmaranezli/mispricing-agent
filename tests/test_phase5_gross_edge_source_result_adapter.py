"""tests/test_phase5_gross_edge_source_result_adapter.py — pins the atomic offline/TDD implementation
of the `phase5_gross_edge_source_result_adapter` slice.

This implements ONLY a typed/frozen `GrossEdgeSourceResult` carrier (same 24 fields and same
construction discipline as `GrossEdgeObservation`) and a typed-to-typed adapter
`adapt_gross_edge_source_result_to_observation(result)` that maps exactly one source result 1:1 into
exactly one `GrossEdgeObservation` via make_gross_edge_observation(*, ...). It is not a parser/loader/
order-book model/aggregator/calculator and produces no list/batch/economic output. The adapter accepts
only the exact source-result type (no isinstance; subclasses rejected), rejects exact halt carriers as
a misroute, never introspects/coerces offending objects, never hardcodes fields, never normalizes
decimals or infers direction/venue/time/source/size, and never silently returns None. Static hardcoded
values only; no IO.
"""
import dataclasses

import pytest

from phase5.gross_edge_source_result_adapter import (
    GrossEdgeSourceResult,
    make_gross_edge_source_result,
    adapt_gross_edge_source_result_to_observation,
    GrossEdgeSourceResultConstructionError,
    GrossEdgeSourceResultTypeError,
    GrossEdgeSourceResultStateError,
)
from phase5.gross_edge_observation_boundary import (
    GrossEdgeObservation,
    GROSS_EDGE_VENUE_SCOPE_SINGLE,
    GROSS_EDGE_VENUE_SCOPE_CROSS,
    MisroutedHaltCarrierError,
)
from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
)


PLANNED_FIELDS = [
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "edge_direction",
    "base_asset",
    "quote_asset",
    "instrument_id",
    "venue_scope",
    "venue_buy",
    "venue_sell",
    "observed_at_epoch_ms",
    "staleness_threshold_ms",
    "gross_edge_value",
    "gross_edge_unit",
    "gross_edge_source_contract",
    "gross_edge_source_artifact",
    "gross_edge_source_field",
    "observed_size",
    "size_unit",
    "depth_source_contract",
    "depth_source_artifact",
    "depth_source_field",
    "boundary_version",
]

FORBIDDEN_FIELDS = [
    "total_cost", "net_cost", "effective_cost", "net_edge", "profit", "expected_profit",
    "readiness", "trade_score", "eligibility", "trade_size", "order_size", "allocation",
    "valid_until",
]


def _valid_kwargs(**overrides):
    kwargs = dict(
        component_name="phase5_gross_edge_observation_boundary",
        origin_component="phase5_gross_edge_source_component",
        origin_result_status="OBSERVED",
        status="GROSS_EDGE_OBSERVED",
        edge_direction="LONG",
        base_asset="BTC",
        quote_asset="USD",
        instrument_id="BTC-USD-PERP",
        venue_scope=GROSS_EDGE_VENUE_SCOPE_SINGLE,
        venue_buy="HYPERLIQUID",
        venue_sell="HYPERLIQUID",
        observed_at_epoch_ms="1781637248000",
        staleness_threshold_ms="60000",
        gross_edge_value="12.34",
        gross_edge_unit="bps",
        gross_edge_source_contract="phase5_gross_edge_source_result_adapter_implementation_planning.md",
        gross_edge_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        gross_edge_source_field="signals.gross_edge_bps",
        observed_size="100",
        size_unit="base_amount",
        depth_source_contract="phase5_gross_edge_source_result_adapter_implementation_planning.md",
        depth_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        depth_source_field="book.top_depth_base",
        boundary_version="phase5.gross_edge_observation_boundary.v0",
    )
    kwargs.update(overrides)
    return kwargs


def _valid_blocked_packet():
    return make_blocked_packet(
        component_name="phase5_blocked_result_boundary",
        origin_component="phase5_input_provenance_preflight",
        origin_result_status="PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
        status="PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
        blocked_status="BLOCKED_NEEDS_EVIDENCE",
        reason_code="BLOCKED_MISSING_REQUIRED_PROVENANCE_FIELD",
        missing_or_invalid_field="provenance.source_artifact",
        source_contract="phase5_fail_closed_blocked_state_contract.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="provenance.source_artifact",
        deterministic_next_action="HALT_FAIL_CLOSED",
        human_review_required=True,
        may_retry_after_evidence=True,
        created_from_contract="phase5_blocked_result_boundary_implementation_planning.md",
        boundary_version="phase5.blocked_result_boundary.v0",
    )


def _valid_no_eligible_packet():
    return make_no_eligible_halt_packet(
        component_name="phase5_no_eligible_halt_propagation_boundary",
        origin_component="phase5_eligibility_source_component",
        origin_result_status="NO_ELIGIBLE",
        status="NO_ELIGIBLE",
        no_eligible_reason="NO_ELIGIBLE_CANDIDATE_WITHIN_CHECKED_SCOPE",
        source_contract="phase5_no_eligible_handling_schema_contract.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="summary.eligible_pairs",
        deterministic_next_action="HALT_BYPASS_NO_ELIGIBLE",
        boundary_version="phase5.no_eligible_halt_propagation_boundary.v0",
    )


# ---- source-result identity / shape ----
def test_source_result_canonical_name():
    assert GrossEdgeSourceResult.__name__ == "GrossEdgeSourceResult"


def test_source_result_keyword_construction_works():
    r = make_gross_edge_source_result(**_valid_kwargs())
    assert isinstance(r, GrossEdgeSourceResult)


def test_source_result_exact_fields():
    r = make_gross_edge_source_result(**_valid_kwargs())
    names = [f.name for f in dataclasses.fields(r)]
    assert set(names) == set(PLANNED_FIELDS)
    assert len(names) == len(PLANNED_FIELDS)


def test_source_result_no_forbidden_fields():
    names = {f.name for f in dataclasses.fields(GrossEdgeSourceResult)}
    for banned in FORBIDDEN_FIELDS:
        assert banned not in names, f"forbidden field present: {banned}"


def test_source_result_frozen_and_direct_construction_rejected():
    r = make_gross_edge_source_result(**_valid_kwargs())
    assert dataclasses.is_dataclass(r)
    assert r.__dataclass_params__.frozen is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.status = "MUTATED"
    with pytest.raises(TypeError):
        GrossEdgeSourceResult("phase5_gross_edge_observation_boundary")


def test_source_result_factory_positional_rejected():
    with pytest.raises(TypeError):
        make_gross_edge_source_result("phase5_gross_edge_observation_boundary")


# ---- source-result field validation ----
def test_source_result_none_rejected_for_every_field():
    assert issubclass(GrossEdgeSourceResultConstructionError, TypeError)
    for name in PLANNED_FIELDS:
        with pytest.raises(GrossEdgeSourceResultConstructionError):
            make_gross_edge_source_result(**_valid_kwargs(**{name: None}))


def test_source_result_container_values_rejected():
    for bad in [(), ("a",), ["1"], {"k": "v"}, {1, 2}, frozenset({1})]:
        with pytest.raises(GrossEdgeSourceResultConstructionError):
            make_gross_edge_source_result(**_valid_kwargs(base_asset=bad))


def test_source_result_non_string_scalars_rejected():
    for bad in [0, 1, False, True, 3.14, 12, -1]:
        with pytest.raises(GrossEdgeSourceResultConstructionError):
            make_gross_edge_source_result(**_valid_kwargs(base_asset=bad))


def test_source_result_str_subclass_rejected_exact_type():
    class _StrSub(str):
        pass
    with pytest.raises(GrossEdgeSourceResultConstructionError):
        make_gross_edge_source_result(**_valid_kwargs(base_asset=_StrSub("BTC")))


def test_source_result_empty_and_whitespace_rejected():
    for bad in ["", " ", "   ", "\t", "\n", "  \t\n "]:
        with pytest.raises(GrossEdgeSourceResultConstructionError):
            make_gross_edge_source_result(**_valid_kwargs(base_asset=bad))


def test_source_result_hostile_value_rejected_without_str_repr_eq():
    class _Hostile:
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __str__(self):
            raise AssertionError("str must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0
    with pytest.raises(GrossEdgeSourceResultConstructionError):
        make_gross_edge_source_result(**_valid_kwargs(gross_edge_source_field=_Hostile()))


# ---- canonical decimal ----
def test_source_result_gross_edge_value_accepts_canonical_including_negative():
    for good in ["0", "0.0", "12", "12.34", "-0.25", "-100", "100"]:
        r = make_gross_edge_source_result(**_valid_kwargs(gross_edge_value=good))
        assert r.gross_edge_value == good


def test_source_result_gross_edge_value_rejects_noncanonical():
    for bad in ["1e-3", "+1", " 1", "1.", ".1", "NaN", "Infinity", "", "   ", "--1", "-"]:
        with pytest.raises(GrossEdgeSourceResultConstructionError):
            make_gross_edge_source_result(**_valid_kwargs(gross_edge_value=bad))


def test_source_result_gross_edge_value_rejects_numeric_type():
    for bad in [0, 0.0, 12.34, -1, True]:
        with pytest.raises(GrossEdgeSourceResultConstructionError):
            make_gross_edge_source_result(**_valid_kwargs(gross_edge_value=bad))


def test_source_result_observed_size_accepts_nonnegative():
    for good in ["0", "0.0", "12", "12.34", "100"]:
        r = make_gross_edge_source_result(**_valid_kwargs(observed_size=good))
        assert r.observed_size == good


def test_source_result_observed_size_rejects_negative():
    for bad in ["-0.25", "-100", "-0", "-0.0"]:
        with pytest.raises(GrossEdgeSourceResultConstructionError):
            make_gross_edge_source_result(**_valid_kwargs(observed_size=bad))


# ---- integer string fields ----
def test_source_result_epoch_and_staleness_accept_integer_strings():
    r = make_gross_edge_source_result(**_valid_kwargs(
        observed_at_epoch_ms="0", staleness_threshold_ms="123456789"))
    assert r.observed_at_epoch_ms == "0"
    assert r.staleness_threshold_ms == "123456789"


def test_source_result_epoch_and_staleness_reject_non_integer():
    for field in ("observed_at_epoch_ms", "staleness_threshold_ms"):
        for bad in ["-1", "1.0", "1e3", "+1", " 1", "", "NaN", "12.34"]:
            with pytest.raises(GrossEdgeSourceResultConstructionError):
                make_gross_edge_source_result(**_valid_kwargs(**{field: bad}))


# ---- direction / venue ----
def test_source_result_edge_direction_allowed_set():
    for good in ["LONG", "SHORT", "CROSS_VENUE"]:
        r = make_gross_edge_source_result(**_valid_kwargs(edge_direction=good))
        assert r.edge_direction == good


def test_source_result_edge_direction_rejects_unknown():
    for bad in ["BUY", "SELL", "long", "", "UP"]:
        with pytest.raises(GrossEdgeSourceResultConstructionError):
            make_gross_edge_source_result(**_valid_kwargs(edge_direction=bad))


def test_source_result_single_venue_requires_equal_buy_sell():
    r = make_gross_edge_source_result(**_valid_kwargs(
        venue_scope=GROSS_EDGE_VENUE_SCOPE_SINGLE, venue_buy="HL", venue_sell="HL"))
    assert r.venue_scope == "SINGLE_VENUE"
    with pytest.raises(Exception):
        make_gross_edge_source_result(**_valid_kwargs(
            venue_scope=GROSS_EDGE_VENUE_SCOPE_SINGLE, venue_buy="HL", venue_sell="BINANCE"))


def test_source_result_cross_venue_requires_distinct_buy_sell():
    r = make_gross_edge_source_result(**_valid_kwargs(
        venue_scope=GROSS_EDGE_VENUE_SCOPE_CROSS, venue_buy="HYPERLIQUID", venue_sell="BINANCE"))
    assert r.venue_scope == "CROSS_VENUE"
    with pytest.raises(Exception):
        make_gross_edge_source_result(**_valid_kwargs(
            venue_scope=GROSS_EDGE_VENUE_SCOPE_CROSS, venue_buy="HL", venue_sell="HL"))


def test_source_result_rejects_venue_sentinels():
    for bad in ["NOT_APPLICABLE", "NONE", "N/A", "null", "none"]:
        with pytest.raises(Exception):
            make_gross_edge_source_result(**_valid_kwargs(
                venue_scope=GROSS_EDGE_VENUE_SCOPE_CROSS, venue_buy="HYPERLIQUID", venue_sell=bad))


def test_source_result_rejects_unknown_venue_scope():
    for bad in ["NOT_A_SCOPE", "single_venue", "SINGLE", "CROSS"]:
        with pytest.raises(Exception):
            make_gross_edge_source_result(**_valid_kwargs(venue_scope=bad))


def test_source_result_repr_does_not_leak_value_or_provenance():
    r = make_gross_edge_source_result(**_valid_kwargs(
        gross_edge_value="-0.25", observed_at_epoch_ms="1781637248000",
        gross_edge_source_field="signals.gross_edge_bps"))
    rep = repr(r)
    assert "-0.25" not in rep
    assert "1781637248000" not in rep
    assert "signals.gross_edge_bps" not in rep


# ---- adapter behavior ----
def test_adapter_returns_observation_and_maps_all_fields_1to1():
    kwargs = _valid_kwargs(
        component_name="custom_component_marker",     # prove component_name is NOT hardcoded
        origin_component="custom_origin_marker",
        edge_direction="CROSS_VENUE",
        base_asset="ETH",
        quote_asset="USDC",
        instrument_id="ETH-USDC-XV",
        venue_scope=GROSS_EDGE_VENUE_SCOPE_CROSS,
        venue_buy="HYPERLIQUID",
        venue_sell="BINANCE",
        observed_at_epoch_ms="1700000000000",
        staleness_threshold_ms="30000",
        gross_edge_value="-0.25",
        observed_size="42.5",
    )
    r = make_gross_edge_source_result(**kwargs)
    obs = adapt_gross_edge_source_result_to_observation(r)
    assert type(obs) is GrossEdgeObservation
    for name in PLANNED_FIELDS:
        assert getattr(obs, name) == kwargs[name], f"field not mapped 1:1: {name}"


def test_adapter_does_not_normalize_decimal_or_timestamp():
    r = make_gross_edge_source_result(**_valid_kwargs(
        gross_edge_value="0.0", observed_size="0", observed_at_epoch_ms="0"))
    obs = adapt_gross_edge_source_result_to_observation(r)
    assert obs.gross_edge_value == "0.0"   # not normalized to "0"
    assert obs.observed_size == "0"
    assert obs.observed_at_epoch_ms == "0"


def test_adapter_rejects_wrong_type_with_type_error():
    assert issubclass(GrossEdgeSourceResultTypeError, TypeError)
    for bad in [None, 0, "x", 3.14, {"status": "GROSS_EDGE_OBSERVED"}, ["l"], object()]:
        with pytest.raises(GrossEdgeSourceResultTypeError):
            adapt_gross_edge_source_result_to_observation(bad)


def test_adapter_state_error_is_valueerror_subclass():
    assert issubclass(GrossEdgeSourceResultStateError, ValueError)


def test_adapter_rejects_subclass_source_result():
    class _Sub(GrossEdgeSourceResult):
        def __repr__(self):
            raise AssertionError("repr must not be called on subclass")
        def __eq__(self, other):
            raise AssertionError("eq must not be called on subclass")
        def __hash__(self):
            return 0
    sub = object.__new__(_Sub)
    assert isinstance(sub, GrossEdgeSourceResult)
    with pytest.raises(GrossEdgeSourceResultTypeError):
        adapt_gross_edge_source_result_to_observation(sub)


def test_adapter_rejects_exact_halt_carriers_as_misroute():
    assert issubclass(MisroutedHaltCarrierError, TypeError)
    with pytest.raises(MisroutedHaltCarrierError):
        adapt_gross_edge_source_result_to_observation(_valid_blocked_packet())
    with pytest.raises(MisroutedHaltCarrierError):
        adapt_gross_edge_source_result_to_observation(_valid_no_eligible_packet())


def test_adapter_wrong_type_message_uses_type_name_only():
    class _Marker:
        pass
    with pytest.raises(GrossEdgeSourceResultTypeError) as exc:
        adapt_gross_edge_source_result_to_observation(_Marker())
    assert "_Marker" in str(exc.value)


def test_adapter_does_not_introspect_or_coerce_hostile_input():
    class _Hostile:
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __str__(self):
            raise AssertionError("str must not be called")
        def __bool__(self):
            raise AssertionError("bool must not be called")
        def __len__(self):
            raise AssertionError("len must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0
        def __getattr__(self, name):
            raise AssertionError("introspection must not happen")
    with pytest.raises(GrossEdgeSourceResultTypeError):
        adapt_gross_edge_source_result_to_observation(_Hostile())
