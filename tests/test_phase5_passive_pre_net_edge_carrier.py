"""tests/test_phase5_passive_pre_net_edge_carrier.py — Phase 5 passive pre-net-edge carriers + Union entry.

Locks the two Phase-5-owned, non-actionable sibling carriers (PassiveGrossEdgeMagnitude,
PassivePreNetEdgeCalculationInput) and the additive exact-typed Union at the existing
``calculate_net_edge`` entry. Authored under
``docs/handoff/phase6_1_phase5_passive_pre_net_edge_carrier_shape_entry_mechanism_design_charter.md``.

Proves: the actionable path is unchanged; the passive path reuses the SAME calculate_net_edge math;
a malformed passive carrier blocks consistently; there is no second math engine; and the passive
carriers neither require nor accept any actionability field (no edge_direction).
"""
import ast
import inspect

import pytest

import phase5.net_edge_calculator_boundary as nec
from phase5.net_edge_calculator_boundary import (
    calculate_net_edge,
    NetEdgeCalculationResult,
    NetEdgeCalculatorTypeError,
    NET_EDGE_CALCULATOR_STATUS_CALCULATED,
    PassiveGrossEdgeMagnitude,
    PassivePreNetEdgeCalculationInput,
    make_passive_gross_edge_magnitude,
    make_passive_pre_net_edge_calculation_input,
    PassiveGrossEdgeMagnitudeConstructionError,
    PassivePreNetEdgeCalculationInputConstructionError,
)
from phase5.pre_net_edge_calculation_input_boundary import (
    make_pre_net_edge_calculation_input,
    make_observable_cost_validity_context,
)
from phase5.gross_edge_observation_boundary import (
    make_gross_edge_observation,
    GROSS_EDGE_VENUE_SCOPE_SINGLE,
)
from phase5.observable_cost_friction_boundary import (
    make_observable_cost_observation,
    OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
)
from phase5.blocked_result_boundary import BlockedPacket


# ---- shared builders (mirroring the actionable boundary test fixtures) ----
def _gross(value="12.34", unit="bps", **overrides):
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
        gross_edge_value=value,
        gross_edge_unit=unit,
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


def _observation(value="2.00", unit="bps"):
    digits = value.lstrip("-").replace(".", "")
    is_zero = set(digits) <= {"0"}
    evidence = ("explicitly observed zero cost from fees.maker_fee_bps" if is_zero
                else OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE)
    return make_observable_cost_observation(
        component_name="phase5_observable_cost_friction_boundary",
        origin_component="phase5_observed_cost_source_component",
        origin_result_status="OBSERVED",
        status="OBSERVABLE_COST_OBSERVED",
        cost_component_type="TAKER_FEE",
        signed_decimal_value=value,
        unit=unit,
        source_contract="phase5_observable_cost_friction_boundary_implementation_planning.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="fees.taker_fee_bps",
        zero_cost_evidence=evidence,
        boundary_version="phase5.observable_cost_friction_boundary.v0",
    )


def _ctx(value="2.00", unit="bps"):
    return make_observable_cost_validity_context(
        cost_observation=_observation(value=value, unit=unit),
        valid_from_epoch_ms="0",
        valid_until_epoch_ms="100000000000000",
        validity_source_contract="phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md",
        validity_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        validity_source_field="validity.fee_schedule_window",
        validity_assertion_type="DECLARED_VALIDITY_INTERVAL",
        boundary_version="phase5.pre_net_edge_calculation_input_boundary.v0",
    )


def _actionable_input(value="12.34", unit="bps", ctxs=None):
    return make_pre_net_edge_calculation_input(
        gross_observation=_gross(value=value, unit=unit),
        cost_validity_contexts=ctxs if ctxs is not None else (_ctx(),),
        boundary_version="phase5.pre_net_edge_calculation_input_boundary.v0",
    )


def _passive_input(value="12.34", unit="bps", ctxs=None):
    return make_passive_pre_net_edge_calculation_input(
        gross_observation=make_passive_gross_edge_magnitude(
            gross_edge_value=value, gross_edge_unit=unit
        ),
        cost_validity_contexts=ctxs if ctxs is not None else (_ctx(),),
    )


_ECONOMIC_RESULT_FIELDS = (
    "gross_edge_value", "gross_edge_unit", "total_cost_value", "total_cost_unit",
    "net_edge_value", "net_edge_unit", "cost_component_count", "status", "calculation_method",
)


# ---- PassiveGrossEdgeMagnitude: shape + integrity (no actionability) ----
def test_passive_gross_edge_magnitude_carries_value_and_unit():
    m = make_passive_gross_edge_magnitude(gross_edge_value="12.34", gross_edge_unit="bps")
    assert m.gross_edge_value == "12.34"
    assert m.gross_edge_unit == "bps"


@pytest.mark.parametrize("bad", ["", "  ", "abc", "1.2.3", "1e3", "+1", "0x1f"])
def test_passive_gross_edge_magnitude_rejects_non_canonical_value(bad):
    with pytest.raises(PassiveGrossEdgeMagnitudeConstructionError):
        make_passive_gross_edge_magnitude(gross_edge_value=bad, gross_edge_unit="bps")


@pytest.mark.parametrize("bad", ["", "   "])
def test_passive_gross_edge_magnitude_rejects_empty_unit(bad):
    with pytest.raises(PassiveGrossEdgeMagnitudeConstructionError):
        make_passive_gross_edge_magnitude(gross_edge_value="1", gross_edge_unit=bad)


@pytest.mark.parametrize("bad", [12.34, 1234, None, ["1"], {"v": 1}])
def test_passive_gross_edge_magnitude_rejects_non_str_value(bad):
    with pytest.raises(PassiveGrossEdgeMagnitudeConstructionError):
        make_passive_gross_edge_magnitude(gross_edge_value=bad, gross_edge_unit="bps")


def test_passive_gross_edge_magnitude_has_no_actionability_fields():
    m = make_passive_gross_edge_magnitude(gross_edge_value="1", gross_edge_unit="bps")
    for forbidden in ("edge_direction", "venue_scope", "venue_buy", "venue_sell",
                      "staleness_threshold_ms", "observed_at_epoch_ms"):
        assert not hasattr(m, forbidden), forbidden


def test_passive_gross_edge_magnitude_factory_rejects_edge_direction_kwarg():
    with pytest.raises(TypeError):
        make_passive_gross_edge_magnitude(
            gross_edge_value="1", gross_edge_unit="bps", edge_direction="LONG"
        )


# ---- PassivePreNetEdgeCalculationInput: shape + integrity ----
def test_passive_input_holds_passive_gross_and_contexts():
    m = make_passive_gross_edge_magnitude(gross_edge_value="5", gross_edge_unit="bps")
    ctxs = (_ctx(),)
    pin = make_passive_pre_net_edge_calculation_input(
        gross_observation=m, cost_validity_contexts=ctxs
    )
    assert pin.gross_observation is m
    assert pin.cost_validity_contexts is ctxs


def test_passive_input_rejects_actionable_gross_observation():
    # an exact GrossEdgeObservation (actionable) must NOT satisfy the passive gross slot
    with pytest.raises(PassivePreNetEdgeCalculationInputConstructionError):
        make_passive_pre_net_edge_calculation_input(
            gross_observation=_gross(), cost_validity_contexts=(_ctx(),)
        )


def test_passive_input_rejects_empty_cost_contexts():
    # zero-cost is a zero-VALUED cost context, never an empty tuple
    m = make_passive_gross_edge_magnitude(gross_edge_value="5", gross_edge_unit="bps")
    with pytest.raises(PassivePreNetEdgeCalculationInputConstructionError):
        make_passive_pre_net_edge_calculation_input(
            gross_observation=m, cost_validity_contexts=()
        )


@pytest.mark.parametrize("bad", [[_ctx()], "ctx", None, {"c": 1}])
def test_passive_input_rejects_non_tuple_contexts(bad):
    m = make_passive_gross_edge_magnitude(gross_edge_value="5", gross_edge_unit="bps")
    with pytest.raises(PassivePreNetEdgeCalculationInputConstructionError):
        make_passive_pre_net_edge_calculation_input(
            gross_observation=m, cost_validity_contexts=bad
        )


def test_passive_input_is_frozen():
    pin = _passive_input()
    with pytest.raises(Exception):
        pin.gross_observation = make_passive_gross_edge_magnitude(
            gross_edge_value="9", gross_edge_unit="bps"
        )


# ---- Union entry: passive path reuses the SAME calculate_net_edge math ----
def test_passive_path_produces_same_result_as_actionable():
    actionable = calculate_net_edge(calculation_input=_actionable_input(value="12.34", unit="bps"))
    passive = calculate_net_edge(calculation_input=_passive_input(value="12.34", unit="bps"))
    assert type(actionable) is NetEdgeCalculationResult
    assert type(passive) is NetEdgeCalculationResult
    for f in _ECONOMIC_RESULT_FIELDS:
        assert getattr(passive, f) == getattr(actionable, f), f


def test_passive_path_net_edge_is_gross_minus_cost():
    r = calculate_net_edge(calculation_input=_passive_input(value="12.34", unit="bps",
                                                            ctxs=(_ctx(value="2.00"),)))
    assert r.status == NET_EDGE_CALCULATOR_STATUS_CALCULATED
    assert r.net_edge_value == "10.34"
    assert r.total_cost_value == "2.00"


def test_passive_path_zero_valued_cost_context_keeps_net_equal_gross():
    r = calculate_net_edge(calculation_input=_passive_input(value="7", unit="bps",
                                                            ctxs=(_ctx(value="0"),)))
    assert r.net_edge_value == "7"
    assert r.total_cost_value == "0"
    assert r.cost_component_count == "1"


def test_passive_malformed_gross_blocks_consistently():
    # a passive carrier whose gross value is non-canonical must hit the same defensive
    # malformed branch and return a BlockedPacket (never raise, never compute)
    bad_gross = object.__new__(PassiveGrossEdgeMagnitude)
    object.__setattr__(bad_gross, "component_name", "phase5_passive_pre_net_edge_calculation_input")
    object.__setattr__(bad_gross, "boundary_version", "phase5.net_edge_calculator_boundary.passive.v0")
    object.__setattr__(bad_gross, "gross_edge_value", "not-a-decimal")
    object.__setattr__(bad_gross, "gross_edge_unit", "bps")
    pin = make_passive_pre_net_edge_calculation_input(
        gross_observation=bad_gross, cost_validity_contexts=(_ctx(),)
    )
    r = calculate_net_edge(calculation_input=pin)
    assert type(r) is BlockedPacket


# ---- backward compatibility + type safety + no second engine ----
def test_actionable_path_unchanged():
    r = calculate_net_edge(calculation_input=_actionable_input(value="12.34", unit="bps"))
    assert type(r) is NetEdgeCalculationResult
    assert r.status == NET_EDGE_CALCULATOR_STATUS_CALCULATED
    assert r.net_edge_value == "10.34"


@pytest.mark.parametrize("bad", [123, "x", {"a": 1}, [1], 1.5, None])
def test_calculate_net_edge_rejects_unknown_input_type(bad):
    with pytest.raises(NetEdgeCalculatorTypeError):
        calculate_net_edge(calculation_input=bad)


def test_no_second_math_engine_symbol():
    assert not hasattr(nec, "calculate_passive_net_edge")


def test_runtime_uses_no_isinstance_protocol_or_any():
    tree = ast.parse(inspect.getsource(nec))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance", "isinstance broadens typing"
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    assert "Protocol" not in names
    assert "Any" not in names


def test_union_entry_is_exact_type_discriminated():
    # the entry accepts exactly PreNetEdgeCalculationInput and PassivePreNetEdgeCalculationInput,
    # discriminated by exact type (type(x) is ...) — no isinstance, no structural check.
    fn_tree = ast.parse(inspect.getsource(nec.calculate_net_edge))
    referenced = {n.id for n in ast.walk(fn_tree) if isinstance(n, ast.Name)}
    assert "PreNetEdgeCalculationInput" in referenced
    assert "PassivePreNetEdgeCalculationInput" in referenced
    # exact-type discrimination only: at least one `type(...)` call, and no isinstance call
    type_calls = [
        n for n in ast.walk(fn_tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "type"
    ]
    assert len(type_calls) >= 2
    for n in ast.walk(fn_tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            assert n.func.id != "isinstance"
