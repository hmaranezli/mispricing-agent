"""tests/test_phase6_1_shadow_observation.py — Phase 6.1 Slice 0B.

Pins the atomic offline/TDD implementation of `ShadowObservation`: a passive, frozen, slotted,
anti-coercion replay-artifact carrier that references exactly one `PassiveShadowInput` BY IDENTITY,
plus immutable replay-identity fields and a required UTC epoch-millisecond recorded time. It performs
NO calculation/scoring/readiness, has NO serialization/ledger/persistence methods, and constructs
nothing live. Replay-first only: every input here is static and deterministic — no network, clock, IO.

The `_FORBIDDEN_TOKENS` list and the actionability-token strings here are the EXPLICIT test fixtures
permitted by the Slice 0B charter; they must NOT appear in the Phase 6.1 runtime source.
"""
import datetime
import math
import os

import pytest

from phase5.net_edge_calculator_boundary import _make_net_edge_result
from phase5.blocked_result_boundary import make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import make_no_eligible_halt_packet
from phase6_1.passive_shadow_input import make_passive_shadow_input
from phase6_1.shadow_observation import (
    ShadowObservation,
    make_shadow_observation,
    ShadowObservationTypeError,
    ShadowObservationValueError,
    ShadowObservationTruthinessError,
    ShadowObservationCoercionError,
)


# --- deterministic, replay-first builders (no network / clock / IO) --------------------------------

def _real_passive_shadow_input():
    necr = _make_net_edge_result(
        component_name="phase5_net_edge_calculator_boundary",
        origin_component="phase5_net_edge_calculator_boundary",
        origin_result_status="OBSERVED",
        status="CALCULATED",
        gross_edge_value="0.010",
        gross_edge_unit="proportion",
        total_cost_value="0.004",
        total_cost_unit="proportion",
        net_edge_value="0.006",
        net_edge_unit="proportion",
        cost_component_count="2",
        source_contract="phase5_net_edge_calculator_boundary_implementation_planning.md",
        source_artifact="docs/handoff/phase5_net_edge_calculator_boundary_implementation_planning.md",
        source_field="net_edge.calculated_value",
        calculation_method="gross_minus_costs",
        boundary_version="phase5.net_edge_calculator_boundary.v0",
    )
    return make_passive_shadow_input(
        net_edge_calculation_result=necr,
        source_venue="hyperliquid",
        source_pair="BTC-USD",
        observed_at_epoch_ms=1_750_000_000_000,
    )


def _real_blocked_packet():
    return make_blocked_packet(
        component_name="phase5_blocked_result_boundary",
        origin_component="phase5_input_provenance_preflight",
        origin_result_status="PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
        status="PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE",
        blocked_status="BLOCKED_NEEDS_EVIDENCE",
        reason_code="BLOCKED_MISSING_REQUIRED_FIELD",
        missing_or_invalid_field="source_artifact",
        source_contract="phase5_input_schema_refinement_contract.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="summary.eligible_pairs",
        deterministic_next_action="OBTAIN_REQUIRED_EVIDENCE_THEN_REEVALUATE",
        human_review_required=False,
        may_retry_after_evidence=True,
        created_from_contract="phase5_blocked_result_boundary_implementation_planning.md",
        boundary_version="phase5.blocked_result_boundary.v0",
    )


def _real_no_eligible_packet():
    return make_no_eligible_halt_packet(
        component_name="phase5_no_eligible_halt_propagation_boundary",
        origin_component="phase5_net_edge_profitability_gate_boundary",
        origin_result_status="NO_ELIGIBLE",
        status="NO_ELIGIBLE",
        no_eligible_reason="NET_EDGE_BELOW_THRESHOLD",
        source_contract="phase5_no_eligible_halt_propagation_boundary_implementation_planning.md",
        source_artifact="docs/handoff/phase5_no_eligible_halt_propagation_boundary_implementation_planning.md",
        source_field="net_edge.threshold_decision",
        deterministic_next_action="HALT_NO_ELIGIBLE",
        boundary_version="phase5.no_eligible_halt_propagation_boundary.v0",
    )


def _make(**overrides):
    kwargs = dict(
        source=_real_passive_shadow_input(),
        replay_artifact_id="replay-fixture-0001",
        replay_sequence_index=0,
        diagnostic_recorded_at_ms=1_750_000_000_500,
    )
    kwargs.update(overrides)
    return make_shadow_observation(**kwargs)


# --- 1. accepts only exact PassiveShadowInput source ----------------------------------------------

def test_accepts_and_holds_passive_shadow_input_by_identity():
    psi = _real_passive_shadow_input()
    obs = _make(source=psi)
    assert obs.source is psi


# --- 2. rejects dict/raw/NetEdgeCalculationResult/BlockedPacket/NoEligibleHaltPacket bypass --------

def test_rejects_dict_source_bypass():
    with pytest.raises(ShadowObservationTypeError):
        _make(source={"net_edge": "0.006"})


def test_rejects_raw_net_edge_calculation_result_bypass():
    necr = _real_passive_shadow_input().net_edge_calculation_result
    with pytest.raises(ShadowObservationTypeError):
        _make(source=necr)


def test_rejects_blocked_packet_bypass():
    with pytest.raises(ShadowObservationTypeError):
        _make(source=_real_blocked_packet())


def test_rejects_no_eligible_halt_packet_bypass():
    with pytest.raises(ShadowObservationTypeError):
        _make(source=_real_no_eligible_packet())


# --- 3. diagnostic_recorded_at_ms exact non-negative int ------------------------------------------

def test_accepts_non_negative_int_recorded_at():
    obs = _make(diagnostic_recorded_at_ms=0)
    assert obs.diagnostic_recorded_at_ms == 0


@pytest.mark.parametrize("bad", [True, False])
def test_rejects_bool_recorded_at(bad):
    with pytest.raises(ShadowObservationTypeError):
        _make(diagnostic_recorded_at_ms=bad)


@pytest.mark.parametrize("bad", [1.0, "1750000000500", 1750000000500.0])
def test_rejects_non_int_recorded_at(bad):
    with pytest.raises(ShadowObservationTypeError):
        _make(diagnostic_recorded_at_ms=bad)


def test_rejects_naive_datetime_recorded_at():
    with pytest.raises(ShadowObservationTypeError):
        _make(diagnostic_recorded_at_ms=datetime.datetime(2026, 6, 19, 12, 0, 0))


def test_rejects_negative_recorded_at():
    with pytest.raises(ShadowObservationValueError):
        _make(diagnostic_recorded_at_ms=-1)


# --- 4. rejects mutable field values --------------------------------------------------------------

@pytest.mark.parametrize("bad", [{"id": 1}, ["replay"], {"replay"}])
def test_rejects_mutable_replay_artifact_id(bad):
    with pytest.raises(ShadowObservationTypeError):
        _make(replay_artifact_id=bad)


@pytest.mark.parametrize("bad", [{"i": 0}, [0], {0}])
def test_rejects_mutable_replay_sequence_index(bad):
    with pytest.raises(ShadowObservationTypeError):
        _make(replay_sequence_index=bad)


def test_rejects_bool_replay_sequence_index():
    with pytest.raises(ShadowObservationTypeError):
        _make(replay_sequence_index=True)


# --- 5. float diagnostic field rejects NaN / Infinity ---------------------------------------------

def test_accepts_finite_float_diagnostic():
    obs = _make(diagnostic_passive_value=0.0036)
    assert obs.diagnostic_passive_value == 0.0036


def test_diagnostic_passive_value_defaults_absent_none():
    obs = _make()
    assert obs.diagnostic_passive_value is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_rejects_nan_or_infinity_float_diagnostic(bad):
    with pytest.raises(ShadowObservationValueError):
        _make(diagnostic_passive_value=bad)


@pytest.mark.parametrize("bad", [1, True, "0.0036"])
def test_rejects_non_float_diagnostic_coercion(bad):
    with pytest.raises(ShadowObservationTypeError):
        _make(diagnostic_passive_value=bad)


# --- 6. no serialization / ledger / persistence methods -------------------------------------------

def test_no_serialization_or_persistence_methods_exist():
    obs = _make()
    banned = (
        "to_dict", "to_json", "asdict", "json", "serialize", "deserialize",
        "save", "write", "dump", "ledger", "persist", "flush",
    )
    for name in dir(obs):
        low = name.lower()
        assert not any(tok in low for tok in banned), name


# --- 7. zero calculation / no derived scoring or readiness ----------------------------------------

def test_closed_field_set_and_no_calculation_methods():
    obs = _make()
    public_attrs = [n for n in dir(obs) if not n.startswith("_")]
    expected_fields = {
        "component_name",
        "boundary_version",
        "source",
        "replay_artifact_id",
        "replay_sequence_index",
        "diagnostic_recorded_at_ms",
        "diagnostic_passive_value",
    }
    assert set(public_attrs) == expected_fields
    for name in public_attrs:
        assert not callable(getattr(obs, name))
    banned = ("calculate", "compute", "derive", "score", "readiness", "actionable", "verdict")
    for name in dir(obs):
        low = name.lower()
        assert not any(tok in low for tok in banned), name


# --- 8. frozen / slotted / no dynamic attribute injection -----------------------------------------

def test_frozen_blocks_attribute_set():
    obs = _make()
    with pytest.raises(Exception):
        obs.replay_artifact_id = "tampered"


def test_slotted_blocks_dynamic_attribute_injection():
    obs = _make()
    assert not hasattr(obs, "__dict__")
    with pytest.raises(AttributeError):
        object.__setattr__(obs, "injected_attr", 1)


def test_direct_construction_is_blocked():
    with pytest.raises(ShadowObservationTypeError):
        ShadowObservation()


# --- 9. anti-coercion dunders ---------------------------------------------------------------------

def test_anti_coercion_dunders_raise():
    obs = _make()
    with pytest.raises(ShadowObservationTruthinessError):
        bool(obs)
    with pytest.raises(ShadowObservationTruthinessError):
        len(obs)
    for fn in (int, float, complex):
        with pytest.raises(ShadowObservationCoercionError):
            fn(obs)
    with pytest.raises(ShadowObservationCoercionError):
        str(obs)
    with pytest.raises(ShadowObservationCoercionError):
        bytes(obs)


# --- 10. forbidden actionability tokens absent from Phase 6.1 runtime (test fixtures excepted) -----

_FORBIDDEN_TOKENS = (
    "wallet", "balance", "private account", "api secret", "secret",
    "order intent", "orderintent", "order", "routing", "route",
    "execution", "execute", "allocation", "sizing",
    "tradecandidate", "signal", "candidate",
    "live_trade", "live trade", "paper_trade", "paper trade",
)


def test_forbidden_tokens_absent_from_phase6_1_runtime_source():
    import phase6_1.shadow_observation as runtime_mod

    runtime_path = runtime_mod.__file__
    assert os.path.basename(runtime_path) == "shadow_observation.py"
    with open(runtime_path, "r", encoding="utf-8") as fh:
        source_low = fh.read().lower()
    present = [tok for tok in _FORBIDDEN_TOKENS if tok in source_low]
    assert present == [], "forbidden actionability tokens leaked into runtime: %r" % present
