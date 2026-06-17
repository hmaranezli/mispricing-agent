"""tests/test_phase5_pre_net_edge_calculation_input.py — pins the atomic offline/TDD implementation
of the SECOND carrier slice of the `phase5_pre_net_edge_calculation_input_boundary` component:
`PreNetEdgeCalculationInput`.

This implements ONLY the atomic `PreNetEdgeCalculationInput` — a frozen, anti-truthiness,
anti-coercion carrier that wraps exactly ONE `GrossEdgeObservation` together with a non-empty exact
tuple of exact `ObservableCostValidityContext` items, plus a `boundary_version`. Per the planning
artifact (`phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md`) it is NOT a
gate/preflight, NOT a calculator, NOT a cost aggregator, NOT a unit converter, NOT a freshness
validator, and NOT a parser/adapter/loader/order-book/trading/reporting/paper-live component, and it
performs no IO/network/env/datetime/random/subprocess. It carries declared structure only: it does
NOT compare gross observed time to cost validity intervals, does NOT compare valid_from to
valid_until, does NOT compare units/instruments/venues/size/depth across objects, and does NOT
compute freshness/valid_until/aggregate cost/net_edge. The tuple is preserved exactly (order, no
copy-to-list, no sort/dedup/filter/aggregate). Construction is keyword-only via
make_pre_net_edge_calculation_input; positional construction is rejected (init=False); the wrapped
gross observation must be an exact GrossEdgeObservation; the container must be an exact non-empty
tuple of exact ObservableCostValidityContext; boundary_version must be an exact non-empty str.
Static hardcoded values only; no IO.
"""
import dataclasses

import pytest

from phase5.pre_net_edge_calculation_input_boundary import (
    PreNetEdgeCalculationInput,
    make_pre_net_edge_calculation_input,
    ObservableCostValidityContext,
    make_observable_cost_validity_context,
    reject_misrouted_halt_carrier,
    PreNetEdgeCalculationInputTruthinessError,
    PreNetEdgeCalculationInputCoercionError,
    PreNetEdgeCalculationInputConstructionError,
    PreNetEdgeCalculationInputTypeError,
    MisroutedHaltCarrierError,
)
from phase5.gross_edge_observation_boundary import (
    GrossEdgeObservation,
    make_gross_edge_observation,
    GROSS_EDGE_VENUE_SCOPE_SINGLE,
)
from phase5.observable_cost_friction_boundary import (
    make_observable_cost_observation,
    OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
)
from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
)


PLANNED_FIELDS = ["gross_observation", "cost_validity_contexts", "boundary_version"]

INPUT_BOUNDARY_VERSION = "phase5.pre_net_edge_calculation_input_boundary.v0"


def _gross(**overrides):
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
        gross_edge_source_contract="phase5_gross_edge_observation_boundary_implementation_planning.md",
        gross_edge_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        gross_edge_source_field="signals.gross_edge_bps",
        observed_size="100",
        size_unit="base_amount",
        depth_source_contract="phase5_gross_edge_observation_boundary_implementation_planning.md",
        depth_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        depth_source_field="book.top_depth_base",
        boundary_version="phase5.gross_edge_observation_boundary.v0",
    )
    kwargs.update(overrides)
    return make_gross_edge_observation(**kwargs)


def _observation(**overrides):
    kwargs = dict(
        component_name="phase5_observable_cost_friction_boundary",
        origin_component="phase5_observed_cost_source_component",
        origin_result_status="OBSERVED",
        status="OBSERVABLE_COST_OBSERVED",
        cost_component_type="TAKER_FEE",
        signed_decimal_value="12.34",
        unit="bps",
        source_contract="phase5_observable_cost_friction_boundary_implementation_planning.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="fees.taker_fee_bps",
        zero_cost_evidence=OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
        boundary_version="phase5.observable_cost_friction_boundary.v0",
    )
    kwargs.update(overrides)
    return make_observable_cost_observation(**kwargs)


def _validity_context(**overrides):
    kwargs = dict(
        cost_observation=_observation(),
        valid_from_epoch_ms="1781637248000",
        valid_until_epoch_ms="1781723648000",
        validity_source_contract="phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md",
        validity_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        validity_source_field="validity.fee_schedule_window",
        validity_assertion_type="DECLARED_VALIDITY_INTERVAL",
        boundary_version="phase5.pre_net_edge_calculation_input_boundary.v0",
    )
    kwargs.update(overrides)
    return make_observable_cost_validity_context(**kwargs)


def _valid_kwargs(**overrides):
    kwargs = dict(
        gross_observation=_gross(),
        cost_validity_contexts=(_validity_context(),),
        boundary_version=INPUT_BOUNDARY_VERSION,
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


# ---- identity / shape ----
def test_canonical_name():
    assert PreNetEdgeCalculationInput.__name__ == "PreNetEdgeCalculationInput"


def test_keyword_construction_works():
    i = make_pre_net_edge_calculation_input(**_valid_kwargs())
    assert isinstance(i, PreNetEdgeCalculationInput)


def test_exact_fields():
    i = make_pre_net_edge_calculation_input(**_valid_kwargs())
    names = [f.name for f in dataclasses.fields(i)]
    assert set(names) == set(PLANNED_FIELDS)
    assert len(names) == len(PLANNED_FIELDS)


def test_frozen_dataclass():
    i = make_pre_net_edge_calculation_input(**_valid_kwargs())
    assert dataclasses.is_dataclass(i)
    assert i.__dataclass_params__.frozen is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        i.boundary_version = "MUTATED"


def test_factory_positional_rejected():
    with pytest.raises(TypeError):
        make_pre_net_edge_calculation_input(_gross())


def test_direct_positional_construction_rejected():
    with pytest.raises(TypeError):
        PreNetEdgeCalculationInput(_gross())


# ---- gross_observation exact-type enforcement ----
def test_gross_observation_exact_accepted():
    i = make_pre_net_edge_calculation_input(**_valid_kwargs())
    assert type(i.gross_observation) is GrossEdgeObservation


def test_gross_observation_none_rejected():
    assert issubclass(PreNetEdgeCalculationInputConstructionError, TypeError)
    with pytest.raises(PreNetEdgeCalculationInputConstructionError):
        make_pre_net_edge_calculation_input(**_valid_kwargs(gross_observation=None))


def test_gross_observation_subclass_rejected():
    class _GrossSub(GrossEdgeObservation):
        pass
    sub = object.__new__(_GrossSub)
    with pytest.raises(PreNetEdgeCalculationInputConstructionError):
        make_pre_net_edge_calculation_input(**_valid_kwargs(gross_observation=sub))


def test_gross_observation_wrong_type_rejected():
    # An ObservableCostValidityContext is not a GrossEdgeObservation.
    for bad in [object(), "GROSS_EDGE_OBSERVED", 123, _validity_context(), {"x": "y"}]:
        with pytest.raises(PreNetEdgeCalculationInputConstructionError):
            make_pre_net_edge_calculation_input(**_valid_kwargs(gross_observation=bad))


def test_hostile_gross_observation_rejected_without_introspection():
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
    with pytest.raises(PreNetEdgeCalculationInputConstructionError):
        make_pre_net_edge_calculation_input(**_valid_kwargs(gross_observation=_Hostile()))


# ---- tuple container discipline ----
def test_non_empty_tuple_accepted():
    ctxs = (_validity_context(), _validity_context())
    i = make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=ctxs))
    assert type(i.cost_validity_contexts) is tuple
    assert len(i.cost_validity_contexts) == 2


def test_empty_tuple_rejected():
    with pytest.raises(PreNetEdgeCalculationInputConstructionError):
        make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=()))


def test_tuple_none_rejected():
    with pytest.raises(PreNetEdgeCalculationInputConstructionError):
        make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=None))


def test_tuple_order_and_identity_preserved():
    a = _validity_context(validity_source_field="validity.window_a")
    b = _validity_context(validity_source_field="validity.window_b")
    ctxs = (a, b)
    i = make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=ctxs))
    # The exact tuple object is preserved (no copy-to-list, no rebuild, order intact).
    assert i.cost_validity_contexts is ctxs
    assert type(i.cost_validity_contexts) is tuple
    assert i.cost_validity_contexts[0] is a
    assert i.cost_validity_contexts[1] is b


def test_duplicate_contexts_not_deduplicated():
    c = _validity_context()
    ctxs = (c, c, c)
    i = make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=ctxs))
    assert len(i.cost_validity_contexts) == 3
    assert i.cost_validity_contexts is ctxs


def test_non_tuple_containers_rejected():
    one = _validity_context()
    bad_containers = [
        [one],
        {one},
        frozenset({one}),
        {"k": one},
        (x for x in (one,)),
        iter((one,)),
    ]
    for bad in bad_containers:
        with pytest.raises(PreNetEdgeCalculationInputConstructionError):
            make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=bad))


def test_tuple_item_subclass_rejected():
    class _CtxSub(ObservableCostValidityContext):
        pass
    sub = object.__new__(_CtxSub)
    ctxs = (_validity_context(), sub)
    with pytest.raises(PreNetEdgeCalculationInputConstructionError):
        make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=ctxs))


def test_tuple_item_wrong_type_rejected():
    for bad_item in [object(), "ctx", 123, None, _gross(), {"x": "y"}]:
        ctxs = (_validity_context(), bad_item)
        with pytest.raises(PreNetEdgeCalculationInputConstructionError):
            make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=ctxs))


def test_hostile_tuple_item_rejected_without_introspection():
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
    ctxs = (_validity_context(), _Hostile())
    with pytest.raises(PreNetEdgeCalculationInputConstructionError):
        make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=ctxs))


# ---- boundary_version exact-str discipline ----
def test_boundary_version_none_rejected():
    with pytest.raises(PreNetEdgeCalculationInputConstructionError):
        make_pre_net_edge_calculation_input(**_valid_kwargs(boundary_version=None))


def test_boundary_version_must_be_exact_str():
    for bad in [0, 1, False, True, 3.14, (), [], {"k": "v"}, {1}]:
        with pytest.raises(PreNetEdgeCalculationInputConstructionError):
            make_pre_net_edge_calculation_input(**_valid_kwargs(boundary_version=bad))


def test_boundary_version_str_subclass_rejected():
    class _StrSub(str):
        pass
    with pytest.raises(PreNetEdgeCalculationInputConstructionError):
        make_pre_net_edge_calculation_input(
            **_valid_kwargs(boundary_version=_StrSub(INPUT_BOUNDARY_VERSION)))


def test_boundary_version_empty_and_whitespace_rejected():
    for bad in ["", " ", "   ", "\t", "\n", "  \t\n "]:
        with pytest.raises(PreNetEdgeCalculationInputConstructionError):
            make_pre_net_edge_calculation_input(**_valid_kwargs(boundary_version=bad))


# ---- no cross-validation: mismatched-looking content still constructs ----
def test_no_cross_validation_units_instruments_venues():
    # The gross observation says ETH/cross-venue/percent while the cost context says BTC/bps; the
    # carrier must NOT compare them — it only checks intra-object types/formats.
    gross = _gross(
        base_asset="ETH",
        quote_asset="USDT",
        instrument_id="ETH-USDT-PERP",
        gross_edge_unit="percent",
        venue_buy="HYPERLIQUID",
        venue_sell="HYPERLIQUID",
    )
    i = make_pre_net_edge_calculation_input(
        **_valid_kwargs(gross_observation=gross, cost_validity_contexts=(_validity_context(),)))
    assert type(i.gross_observation) is GrossEdgeObservation


def test_no_valid_from_until_comparison():
    # Reversed validity interval in the context — carrier must still construct (no comparison here).
    ctx = _validity_context(
        valid_from_epoch_ms="1781723648000", valid_until_epoch_ms="1781637248000")
    i = make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=(ctx,)))
    assert len(i.cost_validity_contexts) == 1


def test_no_time_alignment_between_gross_and_cost():
    # Gross observed far from cost validity window — no freshness/coverage check is performed.
    gross = _gross(observed_at_epoch_ms="999999999999")
    i = make_pre_net_edge_calculation_input(**_valid_kwargs(gross_observation=gross))
    assert type(i.gross_observation) is GrossEdgeObservation


# ---- anti-truthiness / anti-coercion ----
def test_anti_truthiness():
    i = make_pre_net_edge_calculation_input(**_valid_kwargs())
    assert issubclass(PreNetEdgeCalculationInputTruthinessError, TypeError)
    with pytest.raises(PreNetEdgeCalculationInputTruthinessError):
        bool(i)
    with pytest.raises(PreNetEdgeCalculationInputTruthinessError):
        len(i)
    with pytest.raises(PreNetEdgeCalculationInputTruthinessError):
        _ = "y" if i else "n"


def test_anti_coercion():
    i = make_pre_net_edge_calculation_input(**_valid_kwargs())
    assert issubclass(PreNetEdgeCalculationInputCoercionError, TypeError)
    for fn in (int, float, complex, str, bytes):
        with pytest.raises(PreNetEdgeCalculationInputCoercionError):
            fn(i)
    with pytest.raises(PreNetEdgeCalculationInputCoercionError):
        import operator
        operator.index(i)


# ---- safe repr ----
def test_repr_safe_and_limited():
    i = make_pre_net_edge_calculation_input(**_valid_kwargs())
    r = repr(i)
    assert INPUT_BOUNDARY_VERSION in r  # boundary_version only
    # No gross/cost values, timestamps, provenance, units, venues, or wrapped carriers leak.
    assert "12.34" not in r
    assert "1781637248000" not in r
    assert "1781723648000" not in r
    assert "HYPERLIQUID" not in r
    assert "BTC-USD-PERP" not in r
    assert "bps" not in r
    assert "GrossEdgeObservation" not in r
    assert "ObservableCostValidityContext" not in r
    assert "phase4c_batch_1781637248" not in r
    # The class name "PreNetEdgeCalculationInput" and the boundary_version value legitimately
    # contain "edge"; strip both known-safe tokens, then assert no OTHER economic/readiness wording.
    residual = r.replace(INPUT_BOUNDARY_VERSION, "").replace("PreNetEdgeCalculationInput", "").lower()
    for banned in ["profit", "edge", "ready", "fresh", "net edge", "valid until",
                   "data quality", "truth"]:
        assert banned not in residual


# ---- misrouted halt carrier protection ----
def test_reused_misroute_guard_rejects_exact_halt_carriers():
    assert issubclass(MisroutedHaltCarrierError, TypeError)
    with pytest.raises(MisroutedHaltCarrierError):
        reject_misrouted_halt_carrier(_valid_blocked_packet())
    with pytest.raises(MisroutedHaltCarrierError):
        reject_misrouted_halt_carrier(_valid_no_eligible_packet())


def test_halt_carrier_as_gross_observation_misrouted():
    for halt in [_valid_blocked_packet(), _valid_no_eligible_packet()]:
        with pytest.raises((MisroutedHaltCarrierError,
                            PreNetEdgeCalculationInputConstructionError)):
            make_pre_net_edge_calculation_input(**_valid_kwargs(gross_observation=halt))


def test_halt_carrier_as_tuple_item_misrouted():
    for halt in [_valid_blocked_packet(), _valid_no_eligible_packet()]:
        ctxs = (_validity_context(), halt)
        with pytest.raises((MisroutedHaltCarrierError,
                            PreNetEdgeCalculationInputConstructionError)):
            make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=ctxs))


def test_halt_carrier_as_whole_container_rejected():
    # A halt carrier handed in where the tuple belongs is not a tuple → rejected.
    for halt in [_valid_blocked_packet(), _valid_no_eligible_packet()]:
        with pytest.raises((MisroutedHaltCarrierError,
                            PreNetEdgeCalculationInputConstructionError)):
            make_pre_net_edge_calculation_input(**_valid_kwargs(cost_validity_contexts=halt))


# ---- no gate / calculator / net-edge symbols exported ----
def test_no_gate_or_calculator_symbols_exported():
    import phase5.pre_net_edge_calculation_input_boundary as mod
    for banned in [
        "compute_net_edge",
        "net_edge",
        "aggregate_cost",
        "total_cost",
        "sum_cost",
        "compute_freshness",
        "compute_valid_until",
        "convert_unit",
    ]:
        assert not hasattr(mod, banned), f"forbidden symbol exported: {banned}"
