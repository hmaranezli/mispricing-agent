"""tests/test_phase5_net_edge_calculator_boundary.py — pins the atomic offline/TDD implementation of
the Phase 5 `phase5_net_edge_calculator_boundary`: `NetEdgeCalculationResult` /
`calculate_net_edge` / `NetEdgeCalculator`.

The calculator is a pure, offline, deterministic algebra boundary over exactly one
`PreNetEdgeCalculationInput` (already passed `net_edge_input_preflight`). It is NOT a gate, parser,
adapter, unit converter, cost-applicability policy, FX/oracle, profitability/readiness/actionability
gate, or trading/paper-live component. It computes `net_edge = gross_edge - sum(cost_i)` with signed
cost/rebate algebra, retaining and counting zero-cost components; negative/zero/positive results are
all successful (non-actionable) `NetEdgeCalculationResult`s. It uses Decimal locally from canonical
decimal strings only (no float/NaN/Infinity), serializes results to canonical decimal strings (no
exponent, no leading plus, minus preserved, zero canonicalized to "0"), and never mutates carriers.
Dimensional compatibility is case-sensitive exact-token only; mismatches return a `BlockedPacket`
with the pinned reason vocabulary; the calculator never returns `NoEligibleHaltPacket`. Static
hardcoded values only; no IO.
"""
import dataclasses

import pytest

from phase5.net_edge_calculator_boundary import (
    NetEdgeCalculationResult,
    calculate_net_edge,
    NetEdgeCalculator,
    NetEdgeCalculatorTypeError,
    NetEdgeCalculationResultTruthinessError,
    NetEdgeCalculationResultCoercionError,
    MisroutedHaltCarrierError,
    NET_EDGE_CALCULATOR_COMPONENT_NAME,
    NET_EDGE_CALCULATOR_BOUNDARY_VERSION,
    NET_EDGE_CALCULATOR_SOURCE_CONTRACT,
    NET_EDGE_CALCULATOR_SOURCE_ARTIFACT,
    NET_EDGE_CALCULATION_METHOD,
    NET_EDGE_CALCULATOR_STATUS_CALCULATED,
    NET_EDGE_CALCULATOR_BLOCKED_MISSING_NOTIONAL_FOR_PROPORTIONAL_COST,
    NET_EDGE_CALCULATOR_BLOCKED_MISSING_CONVERSION_BASIS_FOR_ABSOLUTE_COST,
    NET_EDGE_CALCULATOR_BLOCKED_MIXED_PROPORTIONAL_UNITS,
    NET_EDGE_CALCULATOR_BLOCKED_INCOMPATIBLE_ABSOLUTE_UNITS,
    NET_EDGE_CALCULATOR_BLOCKED_UNSUPPORTED_UNIT_VOCABULARY,
    NET_EDGE_CALCULATOR_CONTRACT_VIOLATION_MALFORMED_INPUT_STATE,
)
from phase5.pre_net_edge_calculation_input_boundary import (
    PreNetEdgeCalculationInput,
    make_pre_net_edge_calculation_input,
    make_observable_cost_validity_context,
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

RESULT_FIELDS = [
    "component_name", "origin_component", "origin_result_status", "status",
    "gross_edge_value", "gross_edge_unit", "total_cost_value", "total_cost_unit",
    "net_edge_value", "net_edge_unit", "cost_component_count",
    "source_contract", "source_artifact", "source_field", "calculation_method",
    "boundary_version",
]

BANNED_RESULT_NAMES = [
    "NetEdgeObservation", "ActionableCandidate", "TradeCandidate", "Signal",
    "Opportunity", "ReadyCandidate", "ExecutableCandidate", "Payload",
]


# ---- builders ----
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
    # A numerically-zero value needs explicit (non-sentinel) zero-cost evidence.
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


# ---- API / result shape ----
def test_public_api_symbols():
    assert callable(calculate_net_edge)
    assert NetEdgeCalculator is not None
    assert issubclass(NetEdgeCalculatorTypeError, TypeError)


def test_result_canonical_name_and_not_banned():
    assert NetEdgeCalculationResult.__name__ == "NetEdgeCalculationResult"
    for banned in BANNED_RESULT_NAMES:
        assert NetEdgeCalculationResult.__name__ != banned


def test_result_exact_fields():
    r = calculate_net_edge(calculation_input=_calc_input())
    names = [f.name for f in dataclasses.fields(r)]
    assert set(names) == set(RESULT_FIELDS)
    assert len(names) == len(RESULT_FIELDS)


def test_result_frozen():
    r = calculate_net_edge(calculation_input=_calc_input())
    assert dataclasses.is_dataclass(r)
    assert r.__dataclass_params__.frozen is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.status = "MUTATED"


def test_result_fields_all_str():
    r = calculate_net_edge(calculation_input=_calc_input())
    for name in RESULT_FIELDS:
        assert type(getattr(r, name)) is str


# ---- programmatic wrong-path / misroute ----
def test_wrong_input_type_rejected():
    for bad in [object(), "ci", 123, 4.5, True, (), [], {"k": "v"}, {1}, None]:
        with pytest.raises(NetEdgeCalculatorTypeError):
            calculate_net_edge(calculation_input=bad)


def test_input_subclass_rejected():
    class _Sub(PreNetEdgeCalculationInput):
        pass
    sub = object.__new__(_Sub)
    with pytest.raises(NetEdgeCalculatorTypeError):
        calculate_net_edge(calculation_input=sub)


def test_hostile_input_rejected_without_introspection():
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
    with pytest.raises(NetEdgeCalculatorTypeError):
        calculate_net_edge(calculation_input=_Hostile())


def test_exact_halt_carriers_misrouted():
    for halt in [_valid_blocked_packet(), _valid_no_eligible_packet()]:
        with pytest.raises(MisroutedHaltCarrierError):
            calculate_net_edge(calculation_input=halt)


# ---- algebra (compatible compute) ----
def test_simple_same_unit_net_edge():
    ci = _calc_input(gross=_gross(value="12.34", unit="bps"),
                     ctxs=(_ctx("2.00", "bps"), _ctx("-0.50", "bps")))
    r = calculate_net_edge(calculation_input=ci)
    assert type(r) is NetEdgeCalculationResult
    assert r.status == NET_EDGE_CALCULATOR_STATUS_CALCULATED
    assert r.gross_edge_value == "12.34"
    assert r.gross_edge_unit == "bps"
    assert r.total_cost_value == "1.50"        # 2.00 + (-0.50)
    assert r.total_cost_unit == "bps"
    assert r.net_edge_value == "10.84"         # 12.34 - 1.50
    assert r.net_edge_unit == "bps"
    assert r.cost_component_count == "2"
    assert r.component_name == NET_EDGE_CALCULATOR_COMPONENT_NAME
    assert r.calculation_method == NET_EDGE_CALCULATION_METHOD
    assert r.source_contract == NET_EDGE_CALCULATOR_SOURCE_CONTRACT
    assert r.source_artifact == NET_EDGE_CALCULATOR_SOURCE_ARTIFACT
    assert r.boundary_version == NET_EDGE_CALCULATOR_BOUNDARY_VERSION


def test_negative_net_edge_is_success():
    ci = _calc_input(gross=_gross(value="1", unit="bps"), ctxs=(_ctx("5", "bps"),))
    r = calculate_net_edge(calculation_input=ci)
    assert type(r) is NetEdgeCalculationResult
    assert r.net_edge_value == "-4"
    assert r.cost_component_count == "1"


def test_zero_net_edge_is_success_and_canonicalized():
    ci = _calc_input(gross=_gross(value="10", unit="bps"), ctxs=(_ctx("10", "bps"),))
    r = calculate_net_edge(calculation_input=ci)
    assert type(r) is NetEdgeCalculationResult
    assert r.net_edge_value == "0"   # explicit zero canonicalization, no exponent, no sign


def test_positive_net_edge_is_success_but_not_actionable():
    ci = _calc_input(gross=_gross(value="10", unit="bps"), ctxs=(_ctx("2", "bps"),))
    r = calculate_net_edge(calculation_input=ci)
    assert type(r) is NetEdgeCalculationResult
    assert r.net_edge_value == "8"
    # not actionable: no readiness/actionability fields present
    names = {f.name for f in dataclasses.fields(r)}
    for forbidden in ["actionable", "eligible", "ready", "executable", "trade", "order",
                      "allocation", "paper_live", "live", "readiness", "profitability"]:
        assert forbidden not in names


def test_rebate_increases_net_edge():
    ci = _calc_input(gross=_gross(value="10", unit="bps"), ctxs=(_ctx("-2", "bps"),))
    r = calculate_net_edge(calculation_input=ci)
    assert r.net_edge_value == "12"   # 10 - (-2)


def test_zero_cost_retained_and_counted():
    ci = _calc_input(gross=_gross(value="10", unit="bps"),
                     ctxs=(_ctx("2", "bps"), _ctx("0.0", "bps"), _ctx("1", "bps")))
    r = calculate_net_edge(calculation_input=ci)
    assert r.cost_component_count == "3"      # zero cost not discarded
    assert r.total_cost_value == "3.0"        # 2 + 0.0 + 1 (scale preserved from operands)
    assert r.net_edge_value == "7.0"


def test_exact_match_absolute_unit_computes():
    ci = _calc_input(gross=_gross(value="100", unit="USD"), ctxs=(_ctx("10", "USD"),))
    r = calculate_net_edge(calculation_input=ci)
    assert type(r) is NetEdgeCalculationResult
    assert r.net_edge_value == "90"
    assert r.net_edge_unit == "USD"


def test_proportional_same_token_computes():
    for unit in ["BPS", "BASIS_POINTS", "RATE", "PERCENT", "PERCENTAGE"]:
        ci = _calc_input(gross=_gross(value="5", unit=unit), ctxs=(_ctx("2", unit),))
        r = calculate_net_edge(calculation_input=ci)
        assert type(r) is NetEdgeCalculationResult, f"same proportional unit should compute: {unit}"
        assert r.net_edge_value == "3"


def test_input_not_mutated_by_calculation():
    gross = _gross(value="12.34", unit="bps")
    ctxs = (_ctx("2.00", "bps"),)
    ci = _calc_input(gross=gross, ctxs=ctxs)
    calculate_net_edge(calculation_input=ci)
    # carriers unchanged and tuple identity preserved
    assert ci.gross_observation is gross
    assert ci.cost_validity_contexts is ctxs
    assert gross.gross_edge_value == "12.34"


# ---- dimensional incompatibility (BlockedPacket) ----
def _assert_blocked(r, reason):
    assert type(r) is BlockedPacket
    assert r.reason_code == reason
    assert r.source_field == reason
    assert r.component_name == NET_EDGE_CALCULATOR_COMPONENT_NAME
    assert r.source_contract == NET_EDGE_CALCULATOR_SOURCE_CONTRACT
    assert r.boundary_version == NET_EDGE_CALCULATOR_BOUNDARY_VERSION


def test_mixed_proportional_units_blocked():
    ci = _calc_input(gross=_gross(value="10", unit="BPS"), ctxs=(_ctx("1", "PERCENT"),))
    r = calculate_net_edge(calculation_input=ci)
    _assert_blocked(r, NET_EDGE_CALCULATOR_BLOCKED_MIXED_PROPORTIONAL_UNITS)
    assert r.status == "PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE"
    assert r.blocked_status == "BLOCKED_NEEDS_EVIDENCE"


def test_absolute_gross_proportional_cost_blocks_missing_notional():
    ci = _calc_input(gross=_gross(value="100", unit="USD"), ctxs=(_ctx("5", "BPS"),))
    r = calculate_net_edge(calculation_input=ci)
    _assert_blocked(r, NET_EDGE_CALCULATOR_BLOCKED_MISSING_NOTIONAL_FOR_PROPORTIONAL_COST)


def test_proportional_gross_absolute_cost_blocks_missing_conversion_basis():
    ci = _calc_input(gross=_gross(value="10", unit="BPS"), ctxs=(_ctx("5", "USD"),))
    r = calculate_net_edge(calculation_input=ci)
    _assert_blocked(r, NET_EDGE_CALCULATOR_BLOCKED_MISSING_CONVERSION_BASIS_FOR_ABSOLUTE_COST)


def test_different_absolute_units_blocked():
    ci = _calc_input(gross=_gross(value="100", unit="USD"), ctxs=(_ctx("5", "USDT"),))
    r = calculate_net_edge(calculation_input=ci)
    _assert_blocked(r, NET_EDGE_CALCULATOR_BLOCKED_INCOMPATIBLE_ABSOLUTE_UNITS)


def test_unsupported_unit_vocabulary_blocked():
    # A non-recognized unit token (not proportional, not an identifier-shaped token) that differs.
    ci = _calc_input(gross=_gross(value="100", unit="USD"), ctxs=(_ctx("5", "us$d"),))
    r = calculate_net_edge(calculation_input=ci)
    _assert_blocked(r, NET_EDGE_CALCULATOR_BLOCKED_UNSUPPORTED_UNIT_VOCABULARY)


def test_lowercase_proportional_against_absolute_does_not_normalize():
    # "bps" (lowercase) is not the proportional vocabulary token; with absolute gross it must block,
    # never be normalized to BPS.
    ci = _calc_input(gross=_gross(value="100", unit="USD"), ctxs=(_ctx("5", "bps"),))
    r = calculate_net_edge(calculation_input=ci)
    assert type(r) is BlockedPacket
    assert r.reason_code in (
        NET_EDGE_CALCULATOR_BLOCKED_INCOMPATIBLE_ABSOLUTE_UNITS,
        NET_EDGE_CALCULATOR_BLOCKED_UNSUPPORTED_UNIT_VOCABULARY,
    )


# ---- malformed carrier state discovered during calculation ----
def test_malformed_carrier_state_blocked_not_exception():
    # Bypass the factory to corrupt the gross decimal string; calculator must return BlockedPacket.
    bad_gross = object.__new__(GrossEdgeObservation)
    object.__setattr__(bad_gross, "gross_edge_value", "not-a-decimal")
    object.__setattr__(bad_gross, "gross_edge_unit", "bps")
    corrupt = object.__new__(PreNetEdgeCalculationInput)
    object.__setattr__(corrupt, "gross_observation", bad_gross)
    object.__setattr__(corrupt, "cost_validity_contexts", (_ctx("1", "bps"),))
    object.__setattr__(corrupt, "boundary_version", "phase5.pre_net_edge_calculation_input_boundary.v0")
    r = calculate_net_edge(calculation_input=corrupt)
    _assert_blocked(r, NET_EDGE_CALCULATOR_CONTRACT_VIOLATION_MALFORMED_INPUT_STATE)
    assert r.status == "PLANNING_GATE_CONTRACT_VIOLATION"
    assert r.blocked_status is None


# ---- never returns NoEligible ----
def test_calculator_never_returns_no_eligible():
    results = [
        calculate_net_edge(calculation_input=_calc_input(
            gross=_gross(value="1", unit="bps"), ctxs=(_ctx("100", "bps"),))),   # very negative
        calculate_net_edge(calculation_input=_calc_input(
            gross=_gross(value="100", unit="USD"), ctxs=(_ctx("5", "BPS"),))),   # blocked
        calculate_net_edge(calculation_input=_calc_input()),                     # positive
    ]
    for r in results:
        assert type(r) is not NoEligibleHaltPacket


# ---- anti-truthiness / anti-coercion / decimal discipline ----
def test_result_anti_truthiness_and_coercion():
    r = calculate_net_edge(calculation_input=_calc_input())
    assert issubclass(NetEdgeCalculationResultTruthinessError, TypeError)
    assert issubclass(NetEdgeCalculationResultCoercionError, TypeError)
    with pytest.raises(NetEdgeCalculationResultTruthinessError):
        bool(r)
    with pytest.raises(NetEdgeCalculationResultTruthinessError):
        len(r)
    for fn in (int, float, complex, str, bytes):
        with pytest.raises(NetEdgeCalculationResultCoercionError):
            fn(r)


def test_result_decimal_strings_have_no_exponent_or_leading_plus():
    ci = _calc_input(gross=_gross(value="12.34", unit="bps"), ctxs=(_ctx("2.00", "bps"),))
    r = calculate_net_edge(calculation_input=ci)
    for value in [r.gross_edge_value, r.total_cost_value, r.net_edge_value]:
        assert "e" not in value.lower()
        assert "+" not in value
        assert value == value.strip()


def test_module_has_no_float_construction():
    with open("phase5/net_edge_calculator_boundary.py", encoding="utf-8") as f:
        src = f.read()
    for forbidden in ["float(", "import time", "datetime.", "import random", "subprocess.",
                      ".upper(", ".lower(", ".casefold("]:
        assert forbidden not in src, f"forbidden code usage in calculator module: {forbidden}"


def test_static_wrapper_path_matches_function():
    ci = _calc_input()
    r1 = calculate_net_edge(calculation_input=ci)
    r2 = NetEdgeCalculator.calculate(calculation_input=ci)
    assert type(r1) is NetEdgeCalculationResult
    assert type(r2) is NetEdgeCalculationResult
    assert r1.net_edge_value == r2.net_edge_value
