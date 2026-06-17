"""tests/test_phase5_observable_cost_friction_boundary.py — pins the atomic offline/TDD implementation
of the `phase5_observable_cost_friction_boundary` single observed-cost carrier slice.

This implements ONLY the atomic `ObservableCostObservation` — a frozen, scalar-only, anti-truthiness,
anti-coercion carrier of exactly one explicitly observed cost/friction fact — plus a misrouted
halt-carrier guard. It is not a calculator/aggregate/parser/loader/adapter and exposes no
total/net/effective/edge/profit/readiness/eligibility field. Construction is keyword-only via
make_observable_cost_observation; positional construction is rejected (init=False); every field is an
exact non-empty str; signed_decimal_value is a canonical exact decimal string (no float parsing, no
arithmetic); missing-as-zero and default-zero are impossible (zero requires explicit evidence).
reject_misrouted_halt_carrier raises for exact BlockedPacket / NoEligibleHaltPacket only, without
str/repr/introspection of the offending object. Static hardcoded values only; no IO.
"""
import dataclasses

import pytest

from phase5.observable_cost_friction_boundary import (
    ObservableCostObservation,
    make_observable_cost_observation,
    reject_misrouted_halt_carrier,
    OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
    ObservableCostTruthinessError,
    ObservableCostCoercionError,
    ObservableCostConstructionError,
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
        source_contract="phase5_observable_cost_friction_boundary_implementation_planning.md",
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


# ---- identity / shape ----
def test_canonical_name():
    assert ObservableCostObservation.__name__ == "ObservableCostObservation"


def test_keyword_construction_works():
    p = make_observable_cost_observation(**_valid_kwargs())
    assert isinstance(p, ObservableCostObservation)


def test_exact_fields():
    p = make_observable_cost_observation(**_valid_kwargs())
    names = [f.name for f in dataclasses.fields(p)]
    assert set(names) == set(PLANNED_FIELDS)
    assert len(names) == len(PLANNED_FIELDS)


def test_no_aggregate_or_economic_fields():
    names = {f.name for f in dataclasses.fields(ObservableCostObservation)}
    for banned in FORBIDDEN_AGGREGATE_FIELDS:
        assert banned not in names, f"forbidden aggregate/economic field present: {banned}"


def test_frozen_dataclass():
    p = make_observable_cost_observation(**_valid_kwargs())
    assert dataclasses.is_dataclass(p)
    assert p.__dataclass_params__.frozen is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.status = "MUTATED"


def test_factory_positional_rejected():
    with pytest.raises(TypeError):
        make_observable_cost_observation("phase5_observable_cost_friction_boundary")


def test_direct_positional_construction_rejected():
    with pytest.raises(TypeError):
        ObservableCostObservation("phase5_observable_cost_friction_boundary")


# ---- exact-str / None / container / numeric enforcement ----
def test_none_rejected_for_every_field():
    assert issubclass(ObservableCostConstructionError, TypeError)
    for name in PLANNED_FIELDS:
        with pytest.raises(ObservableCostConstructionError):
            make_observable_cost_observation(**_valid_kwargs(**{name: None}))


def test_container_values_rejected():
    for bad in [(), ("a",), ["1"], {"k": "v"}, {1, 2}, frozenset({1})]:
        with pytest.raises(ObservableCostConstructionError):
            make_observable_cost_observation(**_valid_kwargs(unit=bad))


def test_non_string_scalars_rejected():
    for bad in [0, 1, False, True, 3.14, 12, -1]:
        with pytest.raises(ObservableCostConstructionError):
            make_observable_cost_observation(**_valid_kwargs(cost_component_type=bad))


def test_decimal_value_must_be_string_not_number():
    for bad in [0, 0.0, 12, 12.34, -1, True]:
        with pytest.raises(ObservableCostConstructionError):
            make_observable_cost_observation(**_valid_kwargs(signed_decimal_value=bad))


def test_str_subclass_rejected_exact_type():
    class _StrSub(str):
        pass
    with pytest.raises(ObservableCostConstructionError):
        make_observable_cost_observation(**_valid_kwargs(unit=_StrSub("bps")))


def test_empty_and_whitespace_strings_rejected():
    for bad in ["", " ", "   ", "\t", "\n", "  \t\n "]:
        with pytest.raises(ObservableCostConstructionError):
            make_observable_cost_observation(**_valid_kwargs(unit=bad))


def test_hostile_field_value_rejected_without_str_repr_eq():
    class _Hostile:
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __str__(self):
            raise AssertionError("str must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0
    with pytest.raises(ObservableCostConstructionError):
        make_observable_cost_observation(**_valid_kwargs(source_field=_Hostile()))


# ---- canonical decimal string ----
def test_decimal_value_accepts_canonical_strings():
    for good in ["0", "0.0", "12", "12.34", "-0.25", "100", "-100", "00.000"]:
        ev = (OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE
              if good.replace("-", "").replace(".", "").strip("0") != ""
              else "explicitly observed zero from fees.maker_fee_bps")
        p = make_observable_cost_observation(**_valid_kwargs(signed_decimal_value=good,
                                                             zero_cost_evidence=ev))
        assert p is not None


def test_decimal_value_rejects_noncanonical_strings():
    for bad in ["1e-3", "+1", " 1", "1 ", "1.", ".1", "NaN", "Infinity", "-Infinity",
                "", "   ", "1,234", "0x1", "--1", "1.2.3", "1.", "-"]:
        with pytest.raises(ObservableCostConstructionError):
            make_observable_cost_observation(**_valid_kwargs(
                signed_decimal_value=bad,
                zero_cost_evidence="explicitly observed zero from fees.maker_fee_bps"))


# ---- zero-cost evidence ----
def test_zero_value_requires_explicit_evidence_not_sentinel():
    for zero in ["0", "0.0", "00.000", "-0", "-0.0"]:
        with pytest.raises(ObservableCostConstructionError):
            make_observable_cost_observation(**_valid_kwargs(
                signed_decimal_value=zero,
                zero_cost_evidence=OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE))


def test_zero_value_with_explicit_evidence_is_accepted():
    p = make_observable_cost_observation(**_valid_kwargs(
        signed_decimal_value="0.0",
        zero_cost_evidence="explicitly observed zero maker fee from fees.maker_fee_bps"))
    assert p.signed_decimal_value == "0.0"
    assert p.zero_cost_evidence != OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE


def test_nonzero_value_allows_sentinel_evidence():
    p = make_observable_cost_observation(**_valid_kwargs(
        signed_decimal_value="12.34",
        zero_cost_evidence=OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE))
    assert p.zero_cost_evidence == OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE


def test_zero_cost_evidence_empty_rejected_even_for_zero():
    with pytest.raises(ObservableCostConstructionError):
        make_observable_cost_observation(**_valid_kwargs(
            signed_decimal_value="0", zero_cost_evidence=""))


# ---- sign preservation ----
def test_negative_rebate_preserved_exactly():
    p = make_observable_cost_observation(**_valid_kwargs(
        cost_component_type="MAKER_REBATE", signed_decimal_value="-0.25"))
    assert p.signed_decimal_value == "-0.25"  # not clipped, not absolutized, not converted


# ---- anti-truthiness / anti-coercion ----
def test_anti_truthiness():
    p = make_observable_cost_observation(**_valid_kwargs())
    assert issubclass(ObservableCostTruthinessError, TypeError)
    with pytest.raises(ObservableCostTruthinessError):
        bool(p)
    with pytest.raises(ObservableCostTruthinessError):
        len(p)
    with pytest.raises(ObservableCostTruthinessError):
        _ = "y" if p else "n"


def test_anti_coercion():
    p = make_observable_cost_observation(**_valid_kwargs())
    assert issubclass(ObservableCostCoercionError, TypeError)
    for fn in (int, float, complex, str, bytes):
        with pytest.raises(ObservableCostCoercionError):
            fn(p)
    with pytest.raises(ObservableCostCoercionError):
        import operator
        operator.index(p)


# ---- safe repr ----
def test_repr_safe_and_limited():
    p = make_observable_cost_observation(**_valid_kwargs(
        signed_decimal_value="-0.25",
        source_field="fees.taker_fee_bps",
        zero_cost_evidence=OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE))
    r = repr(p)
    assert "phase5_observable_cost_friction_boundary" in r   # component_name
    assert "OBSERVABLE_COST_OBSERVED" in r                   # status
    assert "TAKER_FEE" in r                                  # cost_component_type
    assert "bps" in r                                        # unit
    # value/provenance/evidence must NOT leak through repr
    assert "-0.25" not in r
    assert "fees.taker_fee_bps" not in r
    assert "phase4c_batch_1781637248" not in r
    assert OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE not in r
    low = r.lower()
    for banned in ["profit", "edge", "ready", "data quality", "truth"]:
        assert banned not in low


# ---- misrouted halt carrier protection ----
def test_misroute_rejects_exact_blocked_packet():
    assert issubclass(MisroutedHaltCarrierError, TypeError)
    with pytest.raises(MisroutedHaltCarrierError):
        reject_misrouted_halt_carrier(_valid_blocked_packet())


def test_misroute_rejects_exact_no_eligible_packet():
    with pytest.raises(MisroutedHaltCarrierError):
        reject_misrouted_halt_carrier(_valid_no_eligible_packet())


def test_misroute_message_uses_type_name_only():
    with pytest.raises(MisroutedHaltCarrierError) as exc:
        reject_misrouted_halt_carrier(_valid_blocked_packet())
    assert "BlockedPacket" in str(exc.value)


def test_misroute_subclass_not_treated_as_exact_halt_carrier():
    class _BSub(BlockedPacket):
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0

    class _NSub(NoEligibleHaltPacket):
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0

    # Subclasses are NOT exact halt carriers; they must not raise MisroutedHaltCarrierError
    # (exact-type only) and must be returned as a non-halt no-op.
    assert reject_misrouted_halt_carrier(object.__new__(_BSub)) is None
    assert reject_misrouted_halt_carrier(object.__new__(_NSub)) is None


def test_misroute_returns_none_for_non_halt_without_introspection():
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

    for benign in [None, 0, "x", object(), _Hostile()]:
        assert reject_misrouted_halt_carrier(benign) is None
