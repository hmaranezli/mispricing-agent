"""tests/test_phase5_observable_cost_validity_context.py — pins the atomic offline/TDD implementation
of the FIRST carrier slice of the `phase5_pre_net_edge_calculation_input_boundary` component:
`ObservableCostValidityContext`.

This implements ONLY the atomic `ObservableCostValidityContext` — a frozen, anti-truthiness,
anti-coercion carrier that wraps exactly one `ObservableCostObservation` plus explicit, declared
validity-interval metadata and provenance — plus a misrouted halt-carrier guard. Per the planning
artifact (`phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md`) it is NOT
`PreNetEdgeCalculationInput`, NOT a gate/preflight, NOT a calculator, NOT a parser/adapter/loader,
and it performs no IO/network/env/datetime/random/subprocess. It carries declared validity metadata
only: it does not compare `valid_from`/`valid_until`, does not compute freshness/TTL/valid_until,
does not infer from the wrapped observation's source_* fields, and proves no validity, no market
truth, no cost truth, no profitability, and no readiness. Construction is keyword-only via
`make_observable_cost_validity_context`; positional construction is rejected (`init=False`); the
wrapped observation must be an exact `ObservableCostObservation`; every metadata field is an exact
non-empty `str`; `valid_from_epoch_ms`/`valid_until_epoch_ms` are exact integer strings (`^\\d+$`).
Static hardcoded values only; no IO.
"""
import dataclasses

import pytest

from phase5.pre_net_edge_calculation_input_boundary import (
    ObservableCostValidityContext,
    make_observable_cost_validity_context,
    reject_misrouted_halt_carrier,
    ObservableCostValidityTruthinessError,
    ObservableCostValidityCoercionError,
    ObservableCostValidityConstructionError,
    ObservableCostValidityTypeError,
    MisroutedHaltCarrierError,
)
from phase5.observable_cost_friction_boundary import (
    ObservableCostObservation,
    make_observable_cost_observation,
    OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
)
from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
)


PLANNED_FIELDS = [
    "cost_observation",
    "valid_from_epoch_ms",
    "valid_until_epoch_ms",
    "validity_source_contract",
    "validity_source_artifact",
    "validity_source_field",
    "validity_assertion_type",
    "boundary_version",
]

FORBIDDEN_FIELDS = [
    "duration", "ttl", "computed_valid_until", "validity_duration_ms",
    "current_time", "now", "freshness", "net_edge", "total_cost", "sum_cost",
    "effective_cost", "profitability", "readiness", "eligibility",
]

METADATA_STR_FIELDS = [
    "valid_from_epoch_ms",
    "valid_until_epoch_ms",
    "validity_source_contract",
    "validity_source_artifact",
    "validity_source_field",
    "validity_assertion_type",
    "boundary_version",
]


def _valid_observation(**overrides):
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


def _valid_kwargs(**overrides):
    kwargs = dict(
        cost_observation=_valid_observation(),
        valid_from_epoch_ms="1781637248000",
        valid_until_epoch_ms="1781723648000",
        validity_source_contract="phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md",
        validity_source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        validity_source_field="validity.fee_schedule_window",
        validity_assertion_type="DECLARED_VALIDITY_INTERVAL",
        boundary_version="phase5.pre_net_edge_calculation_input_boundary.v0",
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
    assert ObservableCostValidityContext.__name__ == "ObservableCostValidityContext"


def test_keyword_construction_works():
    c = make_observable_cost_validity_context(**_valid_kwargs())
    assert isinstance(c, ObservableCostValidityContext)


def test_exact_fields():
    c = make_observable_cost_validity_context(**_valid_kwargs())
    names = [f.name for f in dataclasses.fields(c)]
    assert set(names) == set(PLANNED_FIELDS)
    assert len(names) == len(PLANNED_FIELDS)


def test_no_forbidden_fields():
    names = {f.name for f in dataclasses.fields(ObservableCostValidityContext)}
    for banned in FORBIDDEN_FIELDS:
        assert banned not in names, f"forbidden field present: {banned}"


def test_frozen_dataclass():
    c = make_observable_cost_validity_context(**_valid_kwargs())
    assert dataclasses.is_dataclass(c)
    assert c.__dataclass_params__.frozen is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.validity_assertion_type = "MUTATED"


def test_factory_positional_rejected():
    with pytest.raises(TypeError):
        make_observable_cost_validity_context(_valid_observation())


def test_direct_positional_construction_rejected():
    with pytest.raises(TypeError):
        ObservableCostValidityContext(_valid_observation())


# ---- cost_observation exact-type enforcement ----
def test_cost_observation_must_be_exact_observation():
    c = make_observable_cost_validity_context(**_valid_kwargs())
    assert type(c.cost_observation) is ObservableCostObservation


def test_cost_observation_none_rejected():
    assert issubclass(ObservableCostValidityConstructionError, TypeError)
    with pytest.raises(ObservableCostValidityConstructionError):
        make_observable_cost_validity_context(**_valid_kwargs(cost_observation=None))


def test_cost_observation_subclass_rejected():
    class _ObsSub(ObservableCostObservation):
        pass
    sub = object.__new__(_ObsSub)
    with pytest.raises(ObservableCostValidityConstructionError):
        make_observable_cost_validity_context(**_valid_kwargs(cost_observation=sub))


def test_cost_observation_raw_dict_and_mapping_rejected():
    import collections
    for bad in [{"status": "x"}, collections.OrderedDict(status="x")]:
        with pytest.raises(ObservableCostValidityConstructionError):
            make_observable_cost_validity_context(**_valid_kwargs(cost_observation=bad))


def test_cost_observation_arbitrary_or_duck_typed_rejected():
    class _Duck:
        component_name = "x"
        status = "OBSERVABLE_COST_OBSERVED"
        cost_component_type = "TAKER_FEE"
        unit = "bps"
        signed_decimal_value = "12.34"
    for bad in [object(), "OBSERVABLE_COST_OBSERVED", 123, _Duck()]:
        with pytest.raises(ObservableCostValidityConstructionError):
            make_observable_cost_validity_context(**_valid_kwargs(cost_observation=bad))


def test_hostile_cost_observation_rejected_without_str_repr_introspection():
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
    with pytest.raises(ObservableCostValidityConstructionError):
        make_observable_cost_validity_context(**_valid_kwargs(cost_observation=_Hostile()))


# ---- exact-str / None / container / numeric enforcement on metadata ----
def test_none_rejected_for_every_metadata_field():
    for name in METADATA_STR_FIELDS:
        with pytest.raises(ObservableCostValidityConstructionError):
            make_observable_cost_validity_context(**_valid_kwargs(**{name: None}))


def test_container_metadata_values_rejected():
    for bad in [(), ("a",), ["1"], {"k": "v"}, {1, 2}, frozenset({1})]:
        with pytest.raises(ObservableCostValidityConstructionError):
            make_observable_cost_validity_context(**_valid_kwargs(validity_source_field=bad))


def test_non_string_scalar_metadata_rejected():
    for bad in [0, 1, False, True, 3.14, 12, -1]:
        with pytest.raises(ObservableCostValidityConstructionError):
            make_observable_cost_validity_context(**_valid_kwargs(validity_assertion_type=bad))


def test_str_subclass_metadata_rejected_exact_type():
    class _StrSub(str):
        pass
    with pytest.raises(ObservableCostValidityConstructionError):
        make_observable_cost_validity_context(
            **_valid_kwargs(validity_assertion_type=_StrSub("DECLARED_VALIDITY_INTERVAL")))


def test_empty_and_whitespace_metadata_rejected():
    for bad in ["", " ", "   ", "\t", "\n", "  \t\n "]:
        with pytest.raises(ObservableCostValidityConstructionError):
            make_observable_cost_validity_context(**_valid_kwargs(validity_source_field=bad))


def test_decimal_for_metadata_value_must_be_string_not_number():
    for bad in [1781637248000, 1781637248000.0, True]:
        with pytest.raises(ObservableCostValidityConstructionError):
            make_observable_cost_validity_context(**_valid_kwargs(valid_from_epoch_ms=bad))


# ---- exact integer timestamp strings ----
def test_timestamp_accepts_exact_integer_strings():
    for good in ["0", "1", "1781637248000", "00", "000123"]:
        c = make_observable_cost_validity_context(
            **_valid_kwargs(valid_from_epoch_ms=good, valid_until_epoch_ms=good))
        assert c.valid_from_epoch_ms == good
        assert c.valid_until_epoch_ms == good


def test_timestamp_rejects_non_integer_strings():
    for bad in ["-1", "+1", "1.0", "1e3", " 1", "1 ", "1_000", "0x1", "1,000",
                "NaN", "Infinity", "", "   ", "abc", "12.", ".12", "-"]:
        with pytest.raises(ObservableCostValidityConstructionError):
            make_observable_cost_validity_context(**_valid_kwargs(valid_from_epoch_ms=bad))
        with pytest.raises(ObservableCostValidityConstructionError):
            make_observable_cost_validity_context(**_valid_kwargs(valid_until_epoch_ms=bad))


def test_timestamp_value_preserved_verbatim():
    c = make_observable_cost_validity_context(
        **_valid_kwargs(valid_from_epoch_ms="000123", valid_until_epoch_ms="0"))
    assert c.valid_from_epoch_ms == "000123"  # not normalized, not stripped, not coerced
    assert c.valid_until_epoch_ms == "0"


# ---- no cross-validation: reversed/equal intervals accepted as format-only carrier ----
def test_reversed_interval_accepted_as_format_only_carrier():
    # valid_from > valid_until — the carrier must NOT compare; only formats are checked here.
    c = make_observable_cost_validity_context(
        **_valid_kwargs(valid_from_epoch_ms="1781723648000",
                        valid_until_epoch_ms="1781637248000"))
    assert c.valid_from_epoch_ms == "1781723648000"
    assert c.valid_until_epoch_ms == "1781637248000"


def test_equal_interval_accepted_as_format_only_carrier():
    c = make_observable_cost_validity_context(
        **_valid_kwargs(valid_from_epoch_ms="1781637248000",
                        valid_until_epoch_ms="1781637248000"))
    assert c.valid_from_epoch_ms == c.valid_until_epoch_ms


# ---- no inference from wrapped observation's source fields ----
def test_validity_metadata_not_inferred_from_observation_source_fields():
    obs = _valid_observation(
        source_contract="UNRELATED_CONTRACT.md",
        source_artifact="UNRELATED_ARTIFACT",
        source_field="unrelated.field",
    )
    c = make_observable_cost_validity_context(**_valid_kwargs(cost_observation=obs))
    # Validity provenance is carried as declared, never copied/inferred from the observation.
    assert c.validity_source_contract != obs.source_contract
    assert c.validity_source_artifact != obs.source_artifact
    assert c.validity_source_field != obs.source_field


# ---- anti-truthiness / anti-coercion ----
def test_anti_truthiness():
    c = make_observable_cost_validity_context(**_valid_kwargs())
    assert issubclass(ObservableCostValidityTruthinessError, TypeError)
    with pytest.raises(ObservableCostValidityTruthinessError):
        bool(c)
    with pytest.raises(ObservableCostValidityTruthinessError):
        len(c)
    with pytest.raises(ObservableCostValidityTruthinessError):
        _ = "y" if c else "n"


def test_anti_coercion():
    c = make_observable_cost_validity_context(**_valid_kwargs())
    assert issubclass(ObservableCostValidityCoercionError, TypeError)
    for fn in (int, float, complex, str, bytes):
        with pytest.raises(ObservableCostValidityCoercionError):
            fn(c)
    with pytest.raises(ObservableCostValidityCoercionError):
        import operator
        operator.index(c)


# ---- safe repr ----
def test_repr_safe_and_limited():
    c = make_observable_cost_validity_context(**_valid_kwargs())
    r = repr(c)
    assert "DECLARED_VALIDITY_INTERVAL" in r                          # validity_assertion_type
    assert "phase5.pre_net_edge_calculation_input_boundary.v0" in r   # boundary_version
    # interval values / provenance / wrapped observation must NOT leak through repr
    assert "1781637248000" not in r
    assert "1781723648000" not in r
    assert "validity.fee_schedule_window" not in r
    assert "phase4c_batch_1781637248" not in r
    assert "ObservableCostObservation" not in r
    # The two allowed debug fields (validity_assertion_type, boundary_version) are legitimately
    # present; the boundary_version naturally contains the component name "...net_edge...". Strip the
    # known-safe values, then assert no OTHER economic/readiness wording leaked in.
    residual = r.replace("DECLARED_VALIDITY_INTERVAL", "").replace(
        "phase5.pre_net_edge_calculation_input_boundary.v0", "").lower()
    for banned in ["profit", "edge", "ready", "fresh", "valid until", "data quality", "truth"]:
        assert banned not in residual


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


def test_halt_carrier_rejected_as_cost_observation():
    # An exact halt carrier handed in as the wrapped observation is a misroute, not a valid cost obs.
    for halt in [_valid_blocked_packet(), _valid_no_eligible_packet()]:
        with pytest.raises((MisroutedHaltCarrierError, ObservableCostValidityConstructionError)):
            make_observable_cost_validity_context(**_valid_kwargs(cost_observation=halt))


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


# ---- no calculator / no gate / no net-edge behavior ----
def test_no_calculator_or_gate_symbols_exported():
    import phase5.pre_net_edge_calculation_input_boundary as mod
    for banned in [
        "PreNetEdgeCalculationInput",
        "make_pre_net_edge_calculation_input",
        "PreNetEdgeCalculationInputGate",
        "net_edge_input_preflight",
        "compute_net_edge",
        "net_edge",
        "total_cost",
        "compute_freshness",
        "compute_valid_until",
    ]:
        assert not hasattr(mod, banned), f"forbidden symbol exported: {banned}"
