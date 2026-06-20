"""tests/test_phase6_1_passive_producer.py — Phase 6.1 passive producer slice.

Locks the deterministic passive producer: it constructs ONLY the ratified passive socket carriers,
calls ONLY the existing calculate_net_edge, passes a NetEdgeCalculationResult by identity into the
already-built make_passive_shadow_input, and surfaces a defensive BlockedPacket by identity without
wrapping it. Authored under docs/handoff/phase6_1_passive_producer_implementation_charter.md.

Fixtures are built from scratch and are passive-only: no GrossEdgeObservation fixture is imported,
reused, or stripped. The producer is proven clock-blind and free of actionable imports by AST.
"""
import ast
import inspect

import pytest

import phase6_1.passive_producer as pp
from phase6_1.passive_producer import produce_passive_shadow_input
from phase6_1.passive_shadow_input import PassiveShadowInput
from phase5.net_edge_calculator_boundary import (
    calculate_net_edge,
    NetEdgeCalculationResult,
    make_passive_gross_edge_magnitude,
    make_passive_pre_net_edge_calculation_input,
    PassivePreNetEdgeCalculationInputConstructionError,
)
from phase5.pre_net_edge_calculation_input_boundary import make_observable_cost_validity_context
from phase5.observable_cost_friction_boundary import (
    make_observable_cost_observation,
    OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
)
from phase5.blocked_result_boundary import BlockedPacket


# ---- passive-only fixtures (built from scratch; no actionable carrier used) ----
def _cost_obs(value="2.00", unit="bps"):
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
        cost_observation=_cost_obs(value=value, unit=unit),
        valid_from_epoch_ms="0",
        valid_until_epoch_ms="100000000000000",
        validity_source_contract="phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md",
        validity_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        validity_source_field="validity.fee_schedule_window",
        validity_assertion_type="DECLARED_VALIDITY_INTERVAL",
        boundary_version="phase5.pre_net_edge_calculation_input_boundary.v0",
    )


def _produce(value="12.34", unit="bps", ctxs=None, venue="HYPERLIQUID", pair="BTC-USD",
             epoch=1781637248000):
    return produce_passive_shadow_input(
        gross_edge_value=value,
        gross_edge_unit=unit,
        cost_validity_contexts=ctxs if ctxs is not None else (_ctx(),),
        source_venue=venue,
        source_pair=pair,
        observed_at_epoch_ms=epoch,
    )


def _real_net_edge_result():
    pin = make_passive_pre_net_edge_calculation_input(
        gross_observation=make_passive_gross_edge_magnitude(
            gross_edge_value="12.34", gross_edge_unit="bps"
        ),
        cost_validity_contexts=(_ctx(value="2.00", unit="bps"),),
    )
    r = calculate_net_edge(calculation_input=pin)
    assert type(r) is NetEdgeCalculationResult
    return r


def _real_blocked_packet():
    # incompatible units (bps vs usd) -> defensive BlockedPacket
    pin = make_passive_pre_net_edge_calculation_input(
        gross_observation=make_passive_gross_edge_magnitude(
            gross_edge_value="12.34", gross_edge_unit="bps"
        ),
        cost_validity_contexts=(_ctx(value="2.00", unit="usd"),),
    )
    r = calculate_net_edge(calculation_input=pin)
    assert type(r) is BlockedPacket
    return r


# ---- happy path: result wrapped into PassiveShadowInput ----
def test_happy_path_returns_passive_shadow_input():
    out = _produce(value="12.34", unit="bps", ctxs=(_ctx(value="2.00", unit="bps"),))
    assert type(out) is PassiveShadowInput
    assert type(out.net_edge_calculation_result) is NetEdgeCalculationResult
    assert out.net_edge_calculation_result.net_edge_value == "10.34"
    assert out.source_venue == "HYPERLIQUID"
    assert out.source_pair == "BTC-USD"
    assert out.observed_at_epoch_ms == 1781637248000
    assert out.capacity_pass_reference is None


def test_happy_path_zero_valued_cost_context_keeps_net_equal_gross():
    out = _produce(value="7", unit="bps", ctxs=(_ctx(value="0", unit="bps"),))
    assert type(out) is PassiveShadowInput
    assert out.net_edge_calculation_result.net_edge_value == "7"
    assert out.net_edge_calculation_result.total_cost_value == "0"


def test_empty_cost_tuple_remains_invalid():
    with pytest.raises(PassivePreNetEdgeCalculationInputConstructionError):
        _produce(value="7", unit="bps", ctxs=())


# ---- defensive path: BlockedPacket surfaced by identity, handoff not called ----
def test_defensive_path_returns_blocked_packet_not_wrapped():
    out = _produce(value="12.34", unit="bps", ctxs=(_ctx(value="2.00", unit="usd"),))
    assert type(out) is BlockedPacket
    assert type(out) is not PassiveShadowInput


# ---- identity pass-through (controlled return is unavoidable to prove identity) ----
def test_result_passed_into_handoff_by_identity(monkeypatch):
    sentinel = _real_net_edge_result()
    monkeypatch.setattr(pp, "calculate_net_edge", lambda *, calculation_input: sentinel)
    out = _produce()
    assert type(out) is PassiveShadowInput
    assert out.net_edge_calculation_result is sentinel


def test_blocked_carrier_surfaced_by_identity_and_handoff_not_called(monkeypatch):
    sentinel = _real_blocked_packet()
    monkeypatch.setattr(pp, "calculate_net_edge", lambda *, calculation_input: sentinel)

    def _forbidden_handoff(**kwargs):
        raise AssertionError("make_passive_shadow_input must not be called on the defensive path")

    monkeypatch.setattr(pp, "make_passive_shadow_input", _forbidden_handoff)
    out = _produce()
    assert out is sentinel


# ---- AST / import locks ----
def _producer_tree():
    return ast.parse(inspect.getsource(pp))


def test_producer_signature_is_keyword_only_no_var_args():
    params = inspect.signature(produce_passive_shadow_input).parameters.values()
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params)


def test_producer_uses_no_isinstance():
    for node in ast.walk(_producer_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance"


def test_producer_has_no_protocol_any_or_duck_typing_names():
    names = set()
    for node in ast.walk(_producer_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    assert names & {"Protocol", "Any", "isinstance"} == set()


def test_producer_is_clock_blind():
    tree = _producer_tree()
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots & {"time", "datetime", "calendar"} == set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"now", "utcnow", "today", "monotonic", "time", "perf_counter"}


def test_producer_has_no_toxic_actionable_imports():
    imported = set()
    for node in ast.walk(_producer_tree()):
        if isinstance(node, ast.Import):
            for a in node.names:
                imported.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            for a in node.names:
                imported.add(a.name)
    blob = " ".join(imported).lower()
    for toxic in ("grossedgeobservation", "edge_direction", "shadowintent", "shadow_intent",
                  "capacity", "staleness", "gross_edge_observation"):
        assert toxic not in blob, toxic


def test_producer_constructs_only_passive_carriers():
    referenced = set()
    for node in ast.walk(_producer_tree()):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
    assert "make_passive_gross_edge_magnitude" in referenced
    assert "make_passive_pre_net_edge_calculation_input" in referenced
    assert "make_gross_edge_observation" not in referenced
    assert "GrossEdgeObservation" not in referenced
