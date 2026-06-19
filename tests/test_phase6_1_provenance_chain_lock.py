"""tests/test_phase6_1_provenance_chain_lock.py — Phase 6.1 Slice 0C.

Pins a passive provenance-chain lock over the existing 0A/0B chain:
`NetEdgeCalculationResult -> PassiveShadowInput -> ShadowObservation`.

The lock reads already-present fields only (O(1), no mutation, no computation), proves the chain is the
exact original objects BY IDENTITY, and fails loudly (type/provenance boundary errors) for dicts, raw
Phase 5 objects, halt carriers, subclasses, or a structurally-corrupted chain. It is NOT an
actionability gate. Replay-first: every input here is static and deterministic — no network/clock/IO.

The `_FORBIDDEN_TOKENS` list and the trigger strings here are the EXPLICIT test fixtures permitted by
the Slice 0C charter; they must NOT appear in the Phase 6.1 runtime source.
"""
import os

import pytest

from phase5.net_edge_calculator_boundary import _make_net_edge_result
from phase5.blocked_result_boundary import make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import make_no_eligible_halt_packet
from phase6_1.passive_shadow_input import make_passive_shadow_input
from phase6_1.shadow_observation import ShadowObservation, make_shadow_observation
from phase6_1.provenance_chain_lock import (
    verify_provenance_chain,
    ShadowProvenanceTypeError,
    ShadowProvenanceChainError,
)


# --- deterministic, replay-first builders (no network / clock / IO) --------------------------------

def _net_edge_result():
    return _make_net_edge_result(
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


def _passive_shadow_input(necr):
    return make_passive_shadow_input(
        net_edge_calculation_result=necr,
        source_venue="hyperliquid",
        source_pair="BTC-USD",
        observed_at_epoch_ms=1_750_000_000_000,
    )


def _observation(psi):
    return make_shadow_observation(
        source=psi,
        replay_artifact_id="replay-fixture-0001",
        replay_sequence_index=0,
        diagnostic_recorded_at_ms=1_750_000_000_500,
    )


def _full_chain():
    necr = _net_edge_result()
    psi = _passive_shadow_input(necr)
    obs = _observation(psi)
    return necr, psi, obs


def _blocked_packet():
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


def _no_eligible_packet():
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


# --- 1. provenance chain identity lock ------------------------------------------------------------

def test_chain_refs_are_the_original_objects_by_identity():
    necr, psi, obs = _full_chain()
    ref_necr, ref_psi, ref_obs = verify_provenance_chain(obs)
    assert ref_obs is obs
    assert ref_psi is psi
    assert ref_necr is necr


def test_nested_net_edge_calculation_result_is_original_by_id():
    necr, psi, obs = _full_chain()
    ref_necr, _, _ = verify_provenance_chain(obs)
    assert id(ref_necr) == id(necr)
    # the source link is the exact same PassiveShadowInput too
    assert id(obs.source) == id(psi)
    assert id(obs.source.net_edge_calculation_result) == id(necr)


# --- 2. exact type chain; reject dict/Any/raw/subclass --------------------------------------------

def test_rejects_dict_chain_input():
    with pytest.raises(ShadowProvenanceTypeError):
        verify_provenance_chain({"source": "x"})


def test_rejects_raw_net_edge_calculation_result_input():
    with pytest.raises(ShadowProvenanceTypeError):
        verify_provenance_chain(_net_edge_result())


def test_rejects_raw_passive_shadow_input_input():
    necr = _net_edge_result()
    with pytest.raises(ShadowProvenanceTypeError):
        verify_provenance_chain(_passive_shadow_input(necr))


def test_rejects_shadow_observation_subclass_instance():
    class _SubObs(ShadowObservation):
        pass

    sub = object.__new__(_SubObs)
    assert isinstance(sub, ShadowObservation)
    with pytest.raises(ShadowProvenanceTypeError):
        verify_provenance_chain(sub)


# --- 3. halt carrier fail-fast (type/provenance boundary, NOT actionability) -----------------------

def test_rejects_blocked_packet_loudly():
    with pytest.raises(ShadowProvenanceTypeError):
        verify_provenance_chain(_blocked_packet())


def test_rejects_no_eligible_halt_packet_loudly():
    with pytest.raises(ShadowProvenanceTypeError):
        verify_provenance_chain(_no_eligible_packet())


def test_corrupted_chain_with_non_passive_source_fails_as_chain_error():
    # craft a structurally-corrupted observation whose source link is not a PassiveShadowInput
    corrupted = object.__new__(ShadowObservation)
    object.__setattr__(corrupted, "component_name", "phase6_1_shadow_observation")
    object.__setattr__(corrupted, "boundary_version", "phase6_1.shadow_observation.v0")
    object.__setattr__(corrupted, "source", {"not": "a passive shadow input"})
    object.__setattr__(corrupted, "replay_artifact_id", "replay-fixture-0001")
    object.__setattr__(corrupted, "replay_sequence_index", 0)
    object.__setattr__(corrupted, "diagnostic_recorded_at_ms", 1_750_000_000_500)
    object.__setattr__(corrupted, "diagnostic_passive_value", None)
    with pytest.raises(ShadowProvenanceChainError):
        verify_provenance_chain(corrupted)


# --- 4./6. no calculation/lazy/scoring/readiness/actionability methods in runtime ------------------

def test_runtime_module_has_no_calculation_or_actionability_callables():
    import phase6_1.provenance_chain_lock as mod

    banned = (
        "calculate", "compute", "derive", "score", "readiness",
        "actionable", "verdict", "lazy",
    )
    for name in dir(mod):
        low = name.lower()
        assert not any(tok in low for tok in banned), name


# --- 5. provenance reads are field access only and do not mutate ----------------------------------

def test_verify_does_not_mutate_chain_objects():
    necr, psi, obs = _full_chain()
    before = (
        obs.replay_artifact_id,
        obs.replay_sequence_index,
        obs.diagnostic_recorded_at_ms,
        psi.source_venue,
        psi.source_pair,
        psi.observed_at_epoch_ms,
    )
    verify_provenance_chain(obs)
    after = (
        obs.replay_artifact_id,
        obs.replay_sequence_index,
        obs.diagnostic_recorded_at_ms,
        psi.source_venue,
        psi.source_pair,
        psi.observed_at_epoch_ms,
    )
    assert before == after
    # no attribute injection happened on any chain object (slotted, no __dict__)
    assert not hasattr(obs, "__dict__")
    assert not hasattr(psi, "__dict__")
    # identity of the links is unchanged
    assert obs.source is psi
    assert obs.source.net_edge_calculation_result is necr


# --- 7. forbidden actionability/trigger tokens absent from Phase 6.1 runtime (fixtures excepted) ---

_FORBIDDEN_TOKENS = (
    "json", "ledger", "serialize", "wallet", "balance",
    "order", "routing", "route", "execution", "execute", "allocation",
    "signal", "candidate", "trade", "paper", "live",
)


def test_forbidden_tokens_absent_from_phase6_1_runtime_source():
    import phase6_1.provenance_chain_lock as runtime_mod

    runtime_path = runtime_mod.__file__
    assert os.path.basename(runtime_path) == "provenance_chain_lock.py"
    with open(runtime_path, "r", encoding="utf-8") as fh:
        source_low = fh.read().lower()
    present = [tok for tok in _FORBIDDEN_TOKENS if tok in source_low]
    assert present == [], "forbidden trigger tokens leaked into runtime: %r" % present
