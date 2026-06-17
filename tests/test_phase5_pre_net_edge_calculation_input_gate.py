"""tests/test_phase5_pre_net_edge_calculation_input_gate.py — pins the atomic offline/TDD
implementation of `PreNetEdgeCalculationInputGate` V1 / `net_edge_input_preflight`.

The gate is a pure, offline, deterministic cross-object preflight over exactly one
`PreNetEdgeCalculationInput`. It is not a carrier, calculator, parser, adapter, cost aggregator, unit
converter, FX/oracle, or trading/reporting component. It performs no IO/network/env/time/datetime/
random/subprocess and no economic/cost/net-edge arithmetic; the only arithmetic it performs is local
integer timestamp comparison plus the single addition `gross_observed + gross_staleness`, on ints
parsed (via `int()`) only after exact `^\\d+$` validation, with the carrier fields never mutated.

It returns the identical `PreNetEdgeCalculationInput` on pass, a `BlockedPacket` for contract/data
contradiction or evidence/applicability failure, and a `NoEligibleHaltPacket` only for gross-snapshot
staleness — with no new wrapper / union / shared base / polymorphic halt hierarchy. Unit checks are
case-sensitive exact-string checks (exact match, or exact-uppercase proportional vocabulary); no
normalization. `evaluation_epoch_ms` must be an explicit exact integer string with no clock fallback.
Static hardcoded values only; no IO.
"""
import re

import pytest

from phase5.pre_net_edge_calculation_input_boundary import (
    PreNetEdgeCalculationInput,
    make_pre_net_edge_calculation_input,
    ObservableCostValidityContext,
    make_observable_cost_validity_context,
    PreNetEdgeCalculationInputGate,
    net_edge_input_preflight,
    PreNetEdgeCalculationInputGateTypeError,
    MisroutedHaltCarrierError,
    PRE_NET_EDGE_GATE_COMPONENT_NAME,
    PRE_NET_EDGE_GATE_BOUNDARY_VERSION,
    PRE_NET_EDGE_GATE_SOURCE_CONTRACT,
    PRE_NET_EDGE_GATE_SOURCE_ARTIFACT,
    PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_TIME_CAUSALITY,
    PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_INVALID_COST_INTERVAL,
    PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_GROSS_TIME,
    PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_EVALUATION_TIME,
    PRE_NET_EDGE_GATE_BLOCKED_UNSUPPORTED_UNIT_COMPATIBILITY,
    PRE_NET_EDGE_GATE_NO_ELIGIBLE_GROSS_SNAPSHOT_STALE,
)
from phase5.gross_edge_observation_boundary import (
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

MODULE_PATH = "phase5/pre_net_edge_calculation_input_boundary.py"


# ---- builders (string timestamps; carrier requires ^\d+$) ----
def _gross(observed="1000", staleness="500", unit="bps", **overrides):
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
        observed_at_epoch_ms=observed,
        staleness_threshold_ms=staleness,
        gross_edge_value="12.34",
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


def _observation(unit="bps"):
    return make_observable_cost_observation(
        component_name="phase5_observable_cost_friction_boundary",
        origin_component="phase5_observed_cost_source_component",
        origin_result_status="OBSERVED",
        status="OBSERVABLE_COST_OBSERVED",
        cost_component_type="TAKER_FEE",
        signed_decimal_value="12.34",
        unit=unit,
        source_contract="phase5_observable_cost_friction_boundary_implementation_planning.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="fees.taker_fee_bps",
        zero_cost_evidence=OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
        boundary_version="phase5.observable_cost_friction_boundary.v0",
    )


def _ctx(valid_from="900", valid_until="2000", unit="bps"):
    return make_observable_cost_validity_context(
        cost_observation=_observation(unit=unit),
        valid_from_epoch_ms=valid_from,
        valid_until_epoch_ms=valid_until,
        validity_source_contract="phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md",
        validity_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        validity_source_field="validity.fee_schedule_window",
        validity_assertion_type="DECLARED_VALIDITY_INTERVAL",
        boundary_version="phase5.pre_net_edge_calculation_input_boundary.v0",
    )


def _calc_input(gross=None, ctxs=None):
    return make_pre_net_edge_calculation_input(
        gross_observation=gross if gross is not None else _gross(),
        cost_validity_contexts=ctxs if ctxs is not None else (_ctx(),),
        boundary_version="phase5.pre_net_edge_calculation_input_boundary.v0",
    )


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


# ---- API / constants ----
def test_public_api_symbols_exported():
    assert PreNetEdgeCalculationInputGate is not None
    assert callable(net_edge_input_preflight)
    assert issubclass(PreNetEdgeCalculationInputGateTypeError, TypeError)


def test_reason_constants_exact_values():
    assert PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_TIME_CAUSALITY == "PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_TIME_CAUSALITY"
    assert PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_INVALID_COST_INTERVAL == "PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_INVALID_COST_INTERVAL"
    assert PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_GROSS_TIME == "PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_GROSS_TIME"
    assert PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_EVALUATION_TIME == "PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_EVALUATION_TIME"
    assert PRE_NET_EDGE_GATE_BLOCKED_UNSUPPORTED_UNIT_COMPATIBILITY == "PRE_NET_EDGE_GATE_BLOCKED_UNSUPPORTED_UNIT_COMPATIBILITY"
    assert PRE_NET_EDGE_GATE_NO_ELIGIBLE_GROSS_SNAPSHOT_STALE == "PRE_NET_EDGE_GATE_NO_ELIGIBLE_GROSS_SNAPSHOT_STALE"


def test_other_constants_exact_values():
    assert PRE_NET_EDGE_GATE_COMPONENT_NAME == "phase5_pre_net_edge_calculation_input_gate"
    assert PRE_NET_EDGE_GATE_BOUNDARY_VERSION == "phase5.pre_net_edge_calculation_input_gate.v0"
    assert PRE_NET_EDGE_GATE_SOURCE_CONTRACT == "phase5_pre_net_edge_calculation_input_gate_implementation_planning.md"
    assert PRE_NET_EDGE_GATE_SOURCE_ARTIFACT == "docs/handoff/phase5_pre_net_edge_calculation_input_gate_implementation_planning.md"


# ---- pass / identity ----
def test_pass_returns_identical_input_object():
    ci = _calc_input()
    result = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="1200")
    assert result is ci
    assert type(result) is PreNetEdgeCalculationInput


def test_gate_class_is_stateless_callable_path():
    ci = _calc_input()
    # The class exposes the same pure preflight without requiring carrier construction/state.
    result = PreNetEdgeCalculationInputGate.preflight(calculation_input=ci, evaluation_epoch_ms="1200")
    assert result is ci


# ---- programmatic wrong path / wrong type ----
def test_wrong_calculation_input_type_rejected():
    for bad in [object(), "ci", 123, 4.5, True, (), [], {"k": "v"}, {1}, None]:
        with pytest.raises(PreNetEdgeCalculationInputGateTypeError):
            net_edge_input_preflight(calculation_input=bad, evaluation_epoch_ms="1200")


def test_calculation_input_subclass_rejected():
    class _Sub(PreNetEdgeCalculationInput):
        pass
    sub = object.__new__(_Sub)
    with pytest.raises(PreNetEdgeCalculationInputGateTypeError):
        net_edge_input_preflight(calculation_input=sub, evaluation_epoch_ms="1200")


def test_hostile_calculation_input_rejected_without_introspection():
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
    with pytest.raises(PreNetEdgeCalculationInputGateTypeError):
        net_edge_input_preflight(calculation_input=_Hostile(), evaluation_epoch_ms="1200")


def test_exact_halt_carrier_as_calculation_input_misrouted():
    for halt in [_valid_blocked_packet(), _valid_no_eligible_packet()]:
        with pytest.raises(MisroutedHaltCarrierError):
            net_edge_input_preflight(calculation_input=halt, evaluation_epoch_ms="1200")


def test_exact_halt_carrier_as_evaluation_epoch_misrouted():
    ci = _calc_input()
    for halt in [_valid_blocked_packet(), _valid_no_eligible_packet()]:
        with pytest.raises(MisroutedHaltCarrierError):
            net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms=halt)


def test_evaluation_epoch_must_be_exact_str():
    ci = _calc_input()
    class _StrSub(str):
        pass
    for bad in [None, 1200, 1200.0, True, (), [], {"k": "v"}, {1}, object(), _StrSub("1200")]:
        with pytest.raises(PreNetEdgeCalculationInputGateTypeError):
            net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms=bad)


def test_evaluation_epoch_format_rejected():
    ci = _calc_input()
    for bad in ["", " ", "   ", "\t", "-1", "+1", "1.0", "1e3", " 1", "1 ", "1_000",
                "0x1", "1,000", "NaN", "abc", "12.", ".12", "-"]:
        with pytest.raises(PreNetEdgeCalculationInputGateTypeError):
            net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms=bad)


def test_evaluation_epoch_accepts_leading_zero_integer_strings():
    ci = _calc_input(gross=_gross(observed="0", staleness="5000"),
                     ctxs=(_ctx(valid_from="0", valid_until="100000"),))
    result = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="0001000")
    assert result is ci


# ---- contract / data contradictions (BlockedPacket) ----
def test_evaluation_before_gross_observed_blocked():
    ci = _calc_input(gross=_gross(observed="2000", staleness="5000"),
                     ctxs=(_ctx(valid_from="0", valid_until="100000"),))
    r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="1000")
    assert type(r) is BlockedPacket
    assert r.status == "PLANNING_GATE_CONTRACT_VIOLATION"
    assert r.blocked_status is None
    assert r.reason_code == PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_TIME_CAUSALITY
    assert r.missing_or_invalid_field == "evaluation_epoch_ms"
    assert r.deterministic_next_action == "HALT_FAIL_CLOSED"
    assert r.human_review_required is True
    assert r.may_retry_after_evidence is False
    assert r.component_name == PRE_NET_EDGE_GATE_COMPONENT_NAME
    assert r.origin_component == PRE_NET_EDGE_GATE_COMPONENT_NAME
    assert r.source_contract == PRE_NET_EDGE_GATE_SOURCE_CONTRACT
    assert r.source_artifact == PRE_NET_EDGE_GATE_SOURCE_ARTIFACT
    assert r.source_field == PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_TIME_CAUSALITY
    assert r.boundary_version == PRE_NET_EDGE_GATE_BOUNDARY_VERSION
    assert r.created_from_contract == PRE_NET_EDGE_GATE_SOURCE_CONTRACT


def test_invalid_cost_interval_blocked():
    ci = _calc_input(gross=_gross(observed="1000", staleness="5000"),
                     ctxs=(_ctx(valid_from="2000", valid_until="1000"),))
    r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="1200")
    assert type(r) is BlockedPacket
    assert r.status == "PLANNING_GATE_CONTRACT_VIOLATION"
    assert r.blocked_status is None
    assert r.reason_code == PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_INVALID_COST_INTERVAL
    assert r.missing_or_invalid_field == "cost_validity_interval"
    assert r.deterministic_next_action == "HALT_FAIL_CLOSED"
    assert r.human_review_required is True
    assert r.may_retry_after_evidence is False
    assert r.source_field == PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_INVALID_COST_INTERVAL


# ---- evidence / applicability failures (BlockedPacket) ----
def test_cost_validity_does_not_cover_gross_time_blocked():
    # gross_observed=1000 not within [1100, 5000]
    ci = _calc_input(gross=_gross(observed="1000", staleness="5000"),
                     ctxs=(_ctx(valid_from="1100", valid_until="5000"),))
    r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="1200")
    assert type(r) is BlockedPacket
    assert r.status == "PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE"
    assert r.blocked_status == "BLOCKED_NEEDS_EVIDENCE"
    assert r.reason_code == PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_GROSS_TIME
    assert r.missing_or_invalid_field == "cost_validity_interval_for_gross_observed_time"
    assert r.deterministic_next_action == "OBTAIN_REQUIRED_EVIDENCE_THEN_REEVALUATE"
    assert r.human_review_required is True
    assert r.may_retry_after_evidence is True
    assert r.source_field == PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_GROSS_TIME


def test_cost_validity_does_not_cover_evaluation_time_blocked():
    # gross_observed=1000 within [900, 1100]; evaluation_time=1050 within; make eval outside.
    ci = _calc_input(gross=_gross(observed="1000", staleness="5000"),
                     ctxs=(_ctx(valid_from="900", valid_until="1010"),))
    r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="1005")
    # gross_observed=1000 in [900,1010] ok; evaluation_time=1005 in [900,1010] ok -> passes? choose eval outside
    # redo with eval clearly outside but >= gross_observed and <= staleness window
    ci2 = _calc_input(gross=_gross(observed="950", staleness="5000"),
                      ctxs=(_ctx(valid_from="900", valid_until="1000"),))
    r2 = net_edge_input_preflight(calculation_input=ci2, evaluation_epoch_ms="1500")
    assert type(r2) is BlockedPacket
    assert r2.status == "PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE"
    assert r2.blocked_status == "BLOCKED_NEEDS_EVIDENCE"
    assert r2.reason_code == PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_EVALUATION_TIME
    assert r2.missing_or_invalid_field == "cost_validity_interval_for_evaluation_time"
    assert r2.deterministic_next_action == "OBTAIN_REQUIRED_EVIDENCE_THEN_REEVALUATE"
    assert r2.may_retry_after_evidence is True
    assert r2.source_field == PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_EVALUATION_TIME


def test_unsupported_unit_blocked():
    gross = _gross(observed="1000", staleness="5000", unit="USD")
    ci = _calc_input(gross=gross, ctxs=(_ctx(valid_from="0", valid_until="100000", unit="USDT"),))
    r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="1200")
    assert type(r) is BlockedPacket
    assert r.status == "PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE"
    assert r.blocked_status == "BLOCKED_NEEDS_EVIDENCE"
    assert r.reason_code == PRE_NET_EDGE_GATE_BLOCKED_UNSUPPORTED_UNIT_COMPATIBILITY
    assert r.missing_or_invalid_field == "cost_observation.unit"
    assert r.deterministic_next_action == "OBTAIN_REQUIRED_EVIDENCE_THEN_REEVALUATE"
    assert r.may_retry_after_evidence is True
    assert r.source_field == PRE_NET_EDGE_GATE_BLOCKED_UNSUPPORTED_UNIT_COMPATIBILITY


# ---- no-eligible (gross snapshot stale) ----
def test_gross_snapshot_stale_no_eligible():
    # evaluation_time=2000 > gross_observed(1000) + gross_staleness(500) = 1500
    ci = _calc_input(gross=_gross(observed="1000", staleness="500"),
                     ctxs=(_ctx(valid_from="0", valid_until="100000"),))
    r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="2000")
    assert type(r) is NoEligibleHaltPacket
    assert r.status == "NO_ELIGIBLE"
    assert r.origin_result_status == "NO_ELIGIBLE"
    assert r.no_eligible_reason == PRE_NET_EDGE_GATE_NO_ELIGIBLE_GROSS_SNAPSHOT_STALE
    assert r.deterministic_next_action == "HALT_BYPASS_NO_ELIGIBLE"
    assert r.component_name == PRE_NET_EDGE_GATE_COMPONENT_NAME
    assert r.source_contract == PRE_NET_EDGE_GATE_SOURCE_CONTRACT
    assert r.source_artifact == PRE_NET_EDGE_GATE_SOURCE_ARTIFACT
    assert r.source_field == PRE_NET_EDGE_GATE_NO_ELIGIBLE_GROSS_SNAPSHOT_STALE
    assert r.boundary_version == PRE_NET_EDGE_GATE_BOUNDARY_VERSION


def test_stale_boundary_is_strict_greater_than():
    # evaluation_time == gross_observed + gross_staleness is NOT stale (<=), so it passes.
    ci = _calc_input(gross=_gross(observed="1000", staleness="500"),
                     ctxs=(_ctx(valid_from="0", valid_until="100000"),))
    r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="1500")
    assert r is ci


# ---- precedence ----
def test_blocked_precedence_over_no_eligible():
    # Both a cost-evidence failure (eval not covered) AND gross-stale are true; Blocked must win.
    # gross_observed=1000, staleness=100 -> stale window 1100; eval=5000 (stale).
    # cost interval [0, 2000] covers gross(1000) but NOT eval(5000) -> evidence failure first.
    ci = _calc_input(gross=_gross(observed="1000", staleness="100"),
                     ctxs=(_ctx(valid_from="0", valid_until="2000"),))
    r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="5000")
    assert type(r) is BlockedPacket
    assert r.reason_code == PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_EVALUATION_TIME


def test_category_precedence_invalid_interval_beats_cover_failure_regardless_of_tuple_order():
    # context[0] fails cover-gross (category 4); context[1] has invalid interval (category 3).
    # Category 3 is scanned across all contexts before category 4 -> invalid-interval wins.
    c0 = _ctx(valid_from="1100", valid_until="5000")   # does not cover gross_observed=1000
    c1 = _ctx(valid_from="2000", valid_until="1000")   # invalid interval
    ci = _calc_input(gross=_gross(observed="1000", staleness="5000"), ctxs=(c0, c1))
    r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="1200")
    assert type(r) is BlockedPacket
    assert r.reason_code == PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_INVALID_COST_INTERVAL


# ---- unit policy ----
def test_exact_unit_match_passes_even_if_not_proportional():
    gross = _gross(observed="1000", staleness="5000", unit="USD")
    ci = _calc_input(gross=gross, ctxs=(_ctx(valid_from="0", valid_until="100000", unit="USD"),))
    r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="1200")
    assert r is ci


def test_proportional_units_pass_without_conversion():
    for unit in ["BPS", "BASIS_POINTS", "RATE", "PERCENT", "PERCENTAGE"]:
        gross = _gross(observed="1000", staleness="5000", unit="USD")
        ci = _calc_input(gross=gross, ctxs=(_ctx(valid_from="0", valid_until="100000", unit=unit),))
        r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="1200")
        assert r is ci, f"proportional unit should pass: {unit}"


def test_lowercase_or_mixedcase_unit_does_not_pass_by_normalization():
    for unit in ["bps", "Bps", "percent", "Percent", "basis_points", "rate"]:
        gross = _gross(observed="1000", staleness="5000", unit="USD")
        ci = _calc_input(gross=gross, ctxs=(_ctx(valid_from="0", valid_until="100000", unit=unit),))
        r = net_edge_input_preflight(calculation_input=ci, evaluation_epoch_ms="1200")
        assert type(r) is BlockedPacket, f"non-canonical unit must not pass: {unit}"
        assert r.reason_code == PRE_NET_EDGE_GATE_BLOCKED_UNSUPPORTED_UNIT_COMPATIBILITY


# ---- output discipline / no wrapper ----
def test_outputs_use_only_existing_packet_types():
    pass_r = net_edge_input_preflight(calculation_input=_calc_input(), evaluation_epoch_ms="1200")
    assert type(pass_r) is PreNetEdgeCalculationInput
    blocked_r = net_edge_input_preflight(
        calculation_input=_calc_input(gross=_gross(observed="2000", staleness="5000"),
                                      ctxs=(_ctx(valid_from="0", valid_until="100000"),)),
        evaluation_epoch_ms="1000")
    assert type(blocked_r) is BlockedPacket
    noelig_r = net_edge_input_preflight(
        calculation_input=_calc_input(gross=_gross(observed="1000", staleness="500"),
                                      ctxs=(_ctx(valid_from="0", valid_until="100000"),)),
        evaluation_epoch_ms="2000")
    assert type(noelig_r) is NoEligibleHaltPacket


# ---- source scans: no clock, no float/Decimal, no normalization, no forbidden symbols ----
def test_module_has_no_clock_float_or_normalization():
    # Scan for actual code-usage forms (not descriptive prose, which legitimately names these tokens
    # while documenting their absence).
    with open(MODULE_PATH, encoding="utf-8") as f:
        src = f.read()
    for forbidden in ["import time", "time.time(", "import datetime", "from datetime",
                      "datetime.", "monotonic(", "perf_counter(", "import random", "random.",
                      "import subprocess", "subprocess.", "Decimal(", "float(",
                      ".upper(", ".lower(", ".casefold("]:
        assert forbidden not in src, f"forbidden code usage in gate module source: {forbidden}"


def test_no_calculator_or_aggregation_symbols_exported():
    import phase5.pre_net_edge_calculation_input_boundary as mod
    for banned in ["compute_net_edge", "net_edge", "aggregate_cost", "total_cost", "sum_cost",
                   "compute_freshness", "compute_valid_until", "convert_unit",
                   "CostApplicabilityContext"]:
        assert not hasattr(mod, banned), f"forbidden symbol exported: {banned}"
