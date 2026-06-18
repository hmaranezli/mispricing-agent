"""tests/test_phase5_net_edge_profitability_gate.py — pins the atomic offline/TDD implementation of
the `NetEdgeProfitabilityGate` / `net_edge_profitability_preflight` gate slice of the
`phase5_net_edge_profitability_gate_boundary` component.

The gate is a pure, offline, deterministic profitability-threshold gate over exactly one
`NetEdgeCalculationResult` plus exactly one `ProfitabilityThresholdPolicyContext`. It is NOT a
calculator/comparator-of-anything-else, parser, adapter, unit converter, FX/oracle, readiness or
actionability gate, or trading/paper-live component. It performs no IO/network/env/time/datetime/
random/subprocess and no float arithmetic. The only arithmetic is a single local `Decimal` comparison
(`net_edge_value >= threshold_value`) from already-canonical strings. Unit policy is case-sensitive
exact match. It returns the identical `NetEdgeCalculationResult` on pass (equality passes), a
`BlockedPacket` for missing/malformed/unit-mismatch policy evidence, and a `NoEligibleHaltPacket` only
for below-threshold; programmatic wrong-path/misroute raise `NetEdgeProfitabilityGateTypeError` /
`MisroutedHaltCarrierError`, never a packet. Static hardcoded values only; no IO.
"""
import pytest

from phase5.net_edge_profitability_gate_boundary import (
    ProfitabilityThresholdPolicyContext,
    make_profitability_threshold_policy_context,
    NetEdgeProfitabilityGate,
    net_edge_profitability_preflight,
    NetEdgeProfitabilityGateTypeError,
    MisroutedHaltCarrierError,
    NET_EDGE_PROFITABILITY_GATE_BLOCKED_MISSING_THRESHOLD_POLICY,
    NET_EDGE_PROFITABILITY_GATE_BLOCKED_MALFORMED_THRESHOLD_POLICY,
    NET_EDGE_PROFITABILITY_GATE_BLOCKED_UNIT_MISMATCH,
    NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD,
)
from phase5.net_edge_calculator_boundary import NetEdgeCalculationResult
from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
)

PROFIT_GATE_REASONS = [
    NET_EDGE_PROFITABILITY_GATE_BLOCKED_MISSING_THRESHOLD_POLICY,
    NET_EDGE_PROFITABILITY_GATE_BLOCKED_MALFORMED_THRESHOLD_POLICY,
    NET_EDGE_PROFITABILITY_GATE_BLOCKED_UNIT_MISMATCH,
    NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD,
]


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


def _policy(threshold_value="1.25", threshold_unit="bps"):
    return make_profitability_threshold_policy_context(
        component_name="phase5_net_edge_profitability_gate_boundary",
        threshold_value=threshold_value,
        threshold_unit=threshold_unit,
        source_contract="phase5_net_edge_profitability_gate_implementation_planning.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="policy.min_net_edge_bps",
        policy_id="POLICY_MIN_NET_EDGE_V1",
        boundary_version="phase5.net_edge_profitability_gate_boundary.v0",
    )


def _bypassed_policy(**set_fields):
    p = object.__new__(ProfitabilityThresholdPolicyContext)
    for k, v in set_fields.items():
        object.__setattr__(p, k, v)
    return p


def _full_bypassed_policy(**overrides):
    fields = dict(
        component_name="phase5_net_edge_profitability_gate_boundary",
        threshold_value="1.25",
        threshold_unit="bps",
        source_contract="phase5_net_edge_profitability_gate_implementation_planning.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="policy.min_net_edge_bps",
        policy_id="POLICY_MIN_NET_EDGE_V1",
        boundary_version="phase5.net_edge_profitability_gate_boundary.v0",
    )
    fields.update(overrides)
    return _bypassed_policy(**fields)


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


# ---- API ----
def test_public_api_symbols():
    assert callable(net_edge_profitability_preflight)
    assert NetEdgeProfitabilityGate is not None
    assert issubclass(NetEdgeProfitabilityGateTypeError, TypeError)


def test_reason_constants_exact_values():
    assert NET_EDGE_PROFITABILITY_GATE_BLOCKED_MISSING_THRESHOLD_POLICY == "NET_EDGE_PROFITABILITY_GATE_BLOCKED_MISSING_THRESHOLD_POLICY"
    assert NET_EDGE_PROFITABILITY_GATE_BLOCKED_MALFORMED_THRESHOLD_POLICY == "NET_EDGE_PROFITABILITY_GATE_BLOCKED_MALFORMED_THRESHOLD_POLICY"
    assert NET_EDGE_PROFITABILITY_GATE_BLOCKED_UNIT_MISMATCH == "NET_EDGE_PROFITABILITY_GATE_BLOCKED_UNIT_MISMATCH"
    assert NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD == "NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD"


# ---- pass / identity ----
def test_above_threshold_passes_identity():
    r = _result(net_value="8", net_unit="bps")
    out = net_edge_profitability_preflight(calculation_result=r, threshold_policy=_policy("1.25", "bps"))
    assert out is r
    assert type(out) is NetEdgeCalculationResult


def test_equality_passes_identity():
    r = _result(net_value="1.25", net_unit="bps")
    out = net_edge_profitability_preflight(calculation_result=r, threshold_policy=_policy("1.25", "bps"))
    assert out is r


def test_static_wrapper_path():
    r = _result(net_value="8", net_unit="bps")
    out = NetEdgeProfitabilityGate.preflight(calculation_result=r, threshold_policy=_policy("1.25", "bps"))
    assert out is r


# ---- below threshold -> NoEligible ----
def test_below_threshold_no_eligible():
    r = _result(net_value="1.00", net_unit="bps")
    out = net_edge_profitability_preflight(calculation_result=r, threshold_policy=_policy("1.25", "bps"))
    assert type(out) is NoEligibleHaltPacket
    assert out.status == "NO_ELIGIBLE"
    assert out.origin_result_status == "NO_ELIGIBLE"
    assert out.no_eligible_reason == NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD
    assert out.deterministic_next_action == "HALT_BYPASS_NO_ELIGIBLE"
    assert out.source_field == NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD


# ---- sign-neutral Decimal algebra ----
def test_negative_thresholds_no_sign_morality():
    # -1 >= -2 -> pass
    r_pass = _result(net_value="-1", net_unit="bps")
    assert net_edge_profitability_preflight(calculation_result=r_pass,
                                            threshold_policy=_policy("-2", "bps")) is r_pass
    # -3 < -2 -> below threshold
    r_below = _result(net_value="-3", net_unit="bps")
    out = net_edge_profitability_preflight(calculation_result=r_below, threshold_policy=_policy("-2", "bps"))
    assert type(out) is NoEligibleHaltPacket


def test_zero_threshold_boundary():
    r_eq = _result(net_value="0", net_unit="bps")
    assert net_edge_profitability_preflight(calculation_result=r_eq,
                                            threshold_policy=_policy("0", "bps")) is r_eq
    r_below = _result(net_value="-0.5", net_unit="bps")
    out = net_edge_profitability_preflight(calculation_result=r_below, threshold_policy=_policy("0", "bps"))
    assert type(out) is NoEligibleHaltPacket


# ---- programmatic wrong-path / misroute ----
def test_wrong_calculation_result_type_rejected():
    for bad in [None, object(), "r", 123, 4.5, True, (), [], {"k": "v"}]:
        with pytest.raises(NetEdgeProfitabilityGateTypeError):
            net_edge_profitability_preflight(calculation_result=bad, threshold_policy=_policy())


def test_wrong_threshold_policy_type_rejected():
    r = _result()
    for bad in [None, object(), "p", 123, {"k": "v"}]:
        with pytest.raises(NetEdgeProfitabilityGateTypeError):
            net_edge_profitability_preflight(calculation_result=r, threshold_policy=bad)


def test_calculation_result_subclass_rejected():
    class _Sub(NetEdgeCalculationResult):
        pass
    sub = object.__new__(_Sub)
    with pytest.raises(NetEdgeProfitabilityGateTypeError):
        net_edge_profitability_preflight(calculation_result=sub, threshold_policy=_policy())


def test_threshold_policy_subclass_rejected():
    class _Sub(ProfitabilityThresholdPolicyContext):
        pass
    sub = object.__new__(_Sub)
    with pytest.raises(NetEdgeProfitabilityGateTypeError):
        net_edge_profitability_preflight(calculation_result=_result(), threshold_policy=sub)


def test_halt_carrier_as_either_argument_misrouted():
    r = _result()
    for halt in [_valid_blocked_packet(), _valid_no_eligible_packet()]:
        with pytest.raises(MisroutedHaltCarrierError):
            net_edge_profitability_preflight(calculation_result=halt, threshold_policy=_policy())
        with pytest.raises(MisroutedHaltCarrierError):
            net_edge_profitability_preflight(calculation_result=r, threshold_policy=halt)


def test_hostile_arguments_rejected_without_introspection():
    class _Hostile:
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __str__(self):
            raise AssertionError("str must not be called")
        def __bool__(self):
            raise AssertionError("bool must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0
        def __getattr__(self, name):
            raise AssertionError("introspection must not happen")
    with pytest.raises(NetEdgeProfitabilityGateTypeError):
        net_edge_profitability_preflight(calculation_result=_Hostile(), threshold_policy=_policy())
    with pytest.raises(NetEdgeProfitabilityGateTypeError):
        net_edge_profitability_preflight(calculation_result=_result(), threshold_policy=_Hostile())


# ---- policy evidence failures -> BlockedPacket ----
def _assert_blocked(out, reason):
    assert type(out) is BlockedPacket
    assert out.reason_code == reason
    assert out.source_field == reason
    assert out.status == "PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE"
    assert out.blocked_status == "BLOCKED_NEEDS_EVIDENCE"
    assert out.component_name == "phase5_net_edge_profitability_gate_boundary"


def test_missing_threshold_policy_field_blocked():
    # Exact ProfitabilityThresholdPolicyContext but factory bypassed leaving threshold_value unset.
    policy = _full_bypassed_policy()
    object.__delattr__(policy, "threshold_value")
    out = net_edge_profitability_preflight(calculation_result=_result(), threshold_policy=policy)
    _assert_blocked(out, NET_EDGE_PROFITABILITY_GATE_BLOCKED_MISSING_THRESHOLD_POLICY)


def test_malformed_threshold_value_blocked():
    policy = _full_bypassed_policy(threshold_value="0x1")
    out = net_edge_profitability_preflight(calculation_result=_result(), threshold_policy=policy)
    _assert_blocked(out, NET_EDGE_PROFITABILITY_GATE_BLOCKED_MALFORMED_THRESHOLD_POLICY)


def test_unit_mismatch_blocked():
    r = _result(net_value="8", net_unit="USD")
    out = net_edge_profitability_preflight(calculation_result=r, threshold_policy=_policy("1.25", "bps"))
    _assert_blocked(out, NET_EDGE_PROFITABILITY_GATE_BLOCKED_UNIT_MISMATCH)


# ---- malformed result internal state -> gate TypeError (not packet) ----
def test_malformed_result_net_edge_value_is_type_error_not_packet():
    bad = _result(net_value="not-a-decimal", net_unit="bps")
    with pytest.raises(NetEdgeProfitabilityGateTypeError):
        net_edge_profitability_preflight(calculation_result=bad, threshold_policy=_policy("1.25", "bps"))


# ---- output discipline ----
def test_no_wrapper_or_result_carrier_exported():
    import phase5.net_edge_profitability_gate_boundary as mod
    for banned in ["ProfitabilityPassedResult", "ActionableCandidate", "TradeCandidate", "Signal",
                   "Opportunity", "ReadyCandidate", "ExecutableCandidate", "Payload",
                   "compare_net_edge", "evaluate_profitability", "net_edge_threshold_evaluation"]:
        assert not hasattr(mod, banned), f"forbidden symbol exported: {banned}"


def test_module_has_no_float_clock_or_normalization():
    with open("phase5/net_edge_profitability_gate_boundary.py", encoding="utf-8") as f:
        src = f.read()
    for forbidden in ["float(", "import time", "time.time(", "datetime.", "import os",
                      "import random", "subprocess.", "open(", "import json",
                      ".upper(", ".lower(", ".casefold("]:
        assert forbidden not in src, f"forbidden code usage in gate module: {forbidden}"
