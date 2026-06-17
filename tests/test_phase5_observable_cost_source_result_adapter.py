"""tests/test_phase5_observable_cost_source_result_adapter.py — pins the atomic offline/TDD
implementation of the `phase5_observable_cost_source_result_adapter` slice.

This implements ONLY a typed/frozen `ObservableCostSourceResult` carrier (same 12 fields and same
construction discipline as `ObservableCostObservation`) and a typed-to-typed adapter
`adapt_observable_cost_source_result_to_observation(result)` that maps exactly one source result 1:1
into exactly one `ObservableCostObservation` via make_observable_cost_observation(*, ...). It is not a
parser/loader/aggregator/calculator and produces no list/batch/economic output. The adapter accepts
only the exact source-result type (no isinstance, subclasses rejected), rejects exact halt carriers as
a misroute, never introspects/coerces offending objects, never hardcodes fields, never normalizes
decimals or invents zero evidence, and never silently returns None. Static hardcoded values only; no
IO.
"""
import dataclasses

import pytest

from phase5.observable_cost_source_result_adapter import (
    ObservableCostSourceResult,
    make_observable_cost_source_result,
    adapt_observable_cost_source_result_to_observation,
    ObservableCostSourceResultConstructionError,
    ObservableCostSourceResultTypeError,
    ObservableCostSourceResultStateError,
)
from phase5.observable_cost_friction_boundary import (
    ObservableCostObservation,
    OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
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
    "cost_component_type",
    "signed_decimal_value",
    "unit",
    "source_contract",
    "source_artifact",
    "source_field",
    "zero_cost_evidence",
    "boundary_version",
]

FORBIDDEN_AGGREGATE_FIELDS = [
    "total_cost", "net_cost", "effective_cost", "gross_edge", "net_edge",
    "profit", "expected_profit", "readiness", "trade_score", "eligibility",
]


def _valid_kwargs(**overrides):
    kwargs = dict(
        component_name="phase5_observable_cost_friction_boundary",
        origin_component="phase5_observed_cost_source_component",
        origin_result_status="OBSERVED",
        status="OBSERVABLE_COST_OBSERVED",
        cost_component_type="TAKER_FEE",
        signed_decimal_value="12.34",
        unit="bps",
        source_contract="phase5_observable_cost_source_result_adapter_implementation_planning.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="fees.taker_fee_bps",
        zero_cost_evidence=OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
        boundary_version="phase5.observable_cost_friction_boundary.v0",
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
    assert ObservableCostSourceResult.__name__ == "ObservableCostSourceResult"


def test_source_result_keyword_construction_works():
    r = make_observable_cost_source_result(**_valid_kwargs())
    assert isinstance(r, ObservableCostSourceResult)


def test_source_result_exact_fields():
    r = make_observable_cost_source_result(**_valid_kwargs())
    names = [f.name for f in dataclasses.fields(r)]
    assert set(names) == set(PLANNED_FIELDS)
    assert len(names) == len(PLANNED_FIELDS)


def test_source_result_no_aggregate_or_economic_fields():
    names = {f.name for f in dataclasses.fields(ObservableCostSourceResult)}
    for banned in FORBIDDEN_AGGREGATE_FIELDS:
        assert banned not in names, f"forbidden aggregate/economic field present: {banned}"


def test_source_result_frozen_and_direct_construction_rejected():
    r = make_observable_cost_source_result(**_valid_kwargs())
    assert dataclasses.is_dataclass(r)
    assert r.__dataclass_params__.frozen is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.status = "MUTATED"
    with pytest.raises(TypeError):
        ObservableCostSourceResult("phase5_observable_cost_friction_boundary")


def test_source_result_factory_positional_rejected():
    with pytest.raises(TypeError):
        make_observable_cost_source_result("phase5_observable_cost_friction_boundary")


# ---- source-result field validation ----
def test_source_result_none_rejected_for_every_field():
    assert issubclass(ObservableCostSourceResultConstructionError, TypeError)
    for name in PLANNED_FIELDS:
        with pytest.raises(ObservableCostSourceResultConstructionError):
            make_observable_cost_source_result(**_valid_kwargs(**{name: None}))


def test_source_result_container_values_rejected():
    for bad in [(), ("a",), ["1"], {"k": "v"}, {1, 2}, frozenset({1})]:
        with pytest.raises(ObservableCostSourceResultConstructionError):
            make_observable_cost_source_result(**_valid_kwargs(unit=bad))


def test_source_result_non_string_scalars_rejected():
    for bad in [0, 1, False, True, 3.14, 12, -1]:
        with pytest.raises(ObservableCostSourceResultConstructionError):
            make_observable_cost_source_result(**_valid_kwargs(cost_component_type=bad))


def test_source_result_decimal_must_be_string_not_number():
    for bad in [0, 0.0, 12, 12.34, -1, True]:
        with pytest.raises(ObservableCostSourceResultConstructionError):
            make_observable_cost_source_result(**_valid_kwargs(signed_decimal_value=bad))


def test_source_result_str_subclass_rejected_exact_type():
    class _StrSub(str):
        pass
    with pytest.raises(ObservableCostSourceResultConstructionError):
        make_observable_cost_source_result(**_valid_kwargs(unit=_StrSub("bps")))


def test_source_result_empty_and_whitespace_rejected():
    for bad in ["", " ", "   ", "\t", "\n", "  \t\n "]:
        with pytest.raises(ObservableCostSourceResultConstructionError):
            make_observable_cost_source_result(**_valid_kwargs(unit=bad))


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
    with pytest.raises(ObservableCostSourceResultConstructionError):
        make_observable_cost_source_result(**_valid_kwargs(source_field=_Hostile()))


def test_source_result_decimal_accepts_canonical():
    for good in ["0", "0.0", "12", "12.34", "-0.25", "100", "-100", "00.000"]:
        ev = (OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE
              if good.replace("-", "").replace(".", "").strip("0") != ""
              else "explicitly observed zero from fees.maker_fee_bps")
        r = make_observable_cost_source_result(**_valid_kwargs(signed_decimal_value=good,
                                                               zero_cost_evidence=ev))
        assert r.signed_decimal_value == good  # preserved exactly


def test_source_result_decimal_rejects_noncanonical():
    for bad in ["1e-3", "+1", " 1", "1 ", "1.", ".1", "NaN", "Infinity", "-Infinity",
                "", "   ", "1,234", "0x1", "--1", "1.2.3", "-"]:
        with pytest.raises(ObservableCostSourceResultConstructionError):
            make_observable_cost_source_result(**_valid_kwargs(
                signed_decimal_value=bad,
                zero_cost_evidence="explicitly observed zero from fees.maker_fee_bps"))


def test_source_result_zero_requires_explicit_evidence():
    for zero in ["0", "0.0", "00.000", "-0", "-0.0"]:
        with pytest.raises(ObservableCostSourceResultConstructionError):
            make_observable_cost_source_result(**_valid_kwargs(
                signed_decimal_value=zero,
                zero_cost_evidence=OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE))


def test_source_result_zero_with_evidence_accepted():
    r = make_observable_cost_source_result(**_valid_kwargs(
        signed_decimal_value="0.0",
        zero_cost_evidence="explicitly observed zero maker fee from fees.maker_fee_bps"))
    assert r.signed_decimal_value == "0.0"


def test_source_result_nonzero_allows_sentinel():
    r = make_observable_cost_source_result(**_valid_kwargs(
        signed_decimal_value="12.34",
        zero_cost_evidence=OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE))
    assert r.zero_cost_evidence == OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE


def test_source_result_negative_rebate_preserved():
    r = make_observable_cost_source_result(**_valid_kwargs(
        cost_component_type="MAKER_REBATE", signed_decimal_value="-0.25"))
    assert r.signed_decimal_value == "-0.25"


def test_source_result_repr_does_not_leak_value_or_provenance():
    r = make_observable_cost_source_result(**_valid_kwargs(
        signed_decimal_value="-0.25", source_field="fees.taker_fee_bps"))
    rep = repr(r)
    assert "-0.25" not in rep
    assert "fees.taker_fee_bps" not in rep
    assert "phase4c_batch_1781637248" not in rep


# ---- adapter behavior ----
def test_adapter_returns_observation_and_maps_all_fields_1to1():
    kwargs = _valid_kwargs(
        component_name="custom_component_marker",      # prove component_name is NOT hardcoded
        origin_component="custom_origin_marker",
        origin_result_status="OBSERVED_MARKER",
        status="OBSERVABLE_COST_OBSERVED",
        cost_component_type="MAKER_REBATE",
        signed_decimal_value="-0.25",
        unit="decimal_rate",
        source_contract="custom_contract.md",
        source_artifact="custom_artifact_ref",
        source_field="fees.maker_rebate",
        zero_cost_evidence=OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
        boundary_version="phase5.observable_cost_friction_boundary.v0",
    )
    r = make_observable_cost_source_result(**kwargs)
    obs = adapt_observable_cost_source_result_to_observation(r)
    assert type(obs) is ObservableCostObservation
    for name in PLANNED_FIELDS:
        assert getattr(obs, name) == kwargs[name], f"field not mapped 1:1: {name}"


def test_adapter_does_not_normalize_decimal_or_invent_zero_evidence():
    r = make_observable_cost_source_result(**_valid_kwargs(
        signed_decimal_value="0.0",
        zero_cost_evidence="explicitly observed zero maker fee from fees.maker_fee_bps"))
    obs = adapt_observable_cost_source_result_to_observation(r)
    assert obs.signed_decimal_value == "0.0"  # not normalized to "0"
    assert obs.zero_cost_evidence == "explicitly observed zero maker fee from fees.maker_fee_bps"


def test_adapter_rejects_wrong_type_with_type_error():
    assert issubclass(ObservableCostSourceResultTypeError, TypeError)
    for bad in [None, 0, "x", 3.14, {"status": "OBSERVABLE_COST_OBSERVED"}, ["l"], object()]:
        with pytest.raises(ObservableCostSourceResultTypeError):
            adapt_observable_cost_source_result_to_observation(bad)


def test_adapter_state_error_is_valueerror_subclass():
    assert issubclass(ObservableCostSourceResultStateError, ValueError)


def test_adapter_rejects_subclass_source_result():
    class _Sub(ObservableCostSourceResult):
        def __repr__(self):
            raise AssertionError("repr must not be called on subclass")
        def __eq__(self, other):
            raise AssertionError("eq must not be called on subclass")
        def __hash__(self):
            return 0
    sub = object.__new__(_Sub)
    assert isinstance(sub, ObservableCostSourceResult)
    with pytest.raises(ObservableCostSourceResultTypeError):
        adapt_observable_cost_source_result_to_observation(sub)


def test_adapter_rejects_exact_halt_carriers_as_misroute():
    assert issubclass(MisroutedHaltCarrierError, TypeError)
    with pytest.raises(MisroutedHaltCarrierError):
        adapt_observable_cost_source_result_to_observation(_valid_blocked_packet())
    with pytest.raises(MisroutedHaltCarrierError):
        adapt_observable_cost_source_result_to_observation(_valid_no_eligible_packet())


def test_adapter_wrong_type_message_uses_type_name_only():
    class _Marker:
        pass
    with pytest.raises(ObservableCostSourceResultTypeError) as exc:
        adapt_observable_cost_source_result_to_observation(_Marker())
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
    with pytest.raises(ObservableCostSourceResultTypeError):
        adapt_observable_cost_source_result_to_observation(_Hostile())
