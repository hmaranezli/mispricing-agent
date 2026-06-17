"""tests/test_phase5_no_eligible_halt_propagation_boundary.py — pins the atomic offline/TDD
implementation of the `phase5_no_eligible_halt_propagation_boundary` carrier + pass-through slice.

This implements ONLY the atomic `NoEligibleHaltPacket` (a frozen, scalar-only, anti-truthiness,
anti-coercion carrier of a non-error no-eligible halt signal) and an identity pass-through. It is not
a calculator/parser/adapter and exposes no numeric/economic field. NO_ELIGIBLE is kept semantically
separate from BlockedPacket and is never reused from it. Construction is keyword-only via
make_no_eligible_halt_packet; positional construction (factory or direct) is rejected; container and
None field values are rejected. Wrong-type pass-through raises a strict NoEligibleTypeError without
str/repr/introspection. Static hardcoded values only; no IO.
"""
import dataclasses

import pytest

from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
    pass_through_no_eligible_halt_packet,
    NoEligibleTruthinessError,
    NoEligibleCoercionError,
    NoEligibleConstructionError,
    NoEligibleTypeError,
)
from phase5.blocked_result_boundary import BlockedPacket


PLANNED_FIELDS = [
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "no_eligible_reason",
    "source_contract",
    "source_artifact",
    "source_field",
    "deterministic_next_action",
    "boundary_version",
]


def _valid_kwargs():
    return dict(
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


# canonical name
def test_canonical_name():
    assert NoEligibleHaltPacket.__name__ == "NoEligibleHaltPacket"


# keyword construction
def test_keyword_construction_works():
    p = make_no_eligible_halt_packet(**_valid_kwargs())
    assert isinstance(p, NoEligibleHaltPacket)


# positional construction rejected via factory
def test_factory_positional_rejected():
    with pytest.raises(TypeError):
        make_no_eligible_halt_packet("phase5_no_eligible_halt_propagation_boundary")


# direct positional dataclass construction rejected
def test_direct_positional_construction_rejected():
    with pytest.raises(TypeError):
        NoEligibleHaltPacket("phase5_no_eligible_halt_propagation_boundary")


# frozen dataclass
def test_frozen_dataclass():
    p = make_no_eligible_halt_packet(**_valid_kwargs())
    assert dataclasses.is_dataclass(p)
    assert p.__dataclass_params__.frozen is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.status = "MUTATED"


# exact field set
def test_exact_fields():
    p = make_no_eligible_halt_packet(**_valid_kwargs())
    names = [f.name for f in dataclasses.fields(p)]
    assert set(names) == set(PLANNED_FIELDS)
    assert len(names) == len(PLANNED_FIELDS)


# anti-truthiness
def test_anti_truthiness():
    p = make_no_eligible_halt_packet(**_valid_kwargs())
    assert issubclass(NoEligibleTruthinessError, TypeError)
    with pytest.raises(NoEligibleTruthinessError):
        bool(p)
    with pytest.raises(NoEligibleTruthinessError):
        len(p)
    with pytest.raises(NoEligibleTruthinessError):
        _ = "y" if p else "n"


# anti-coercion
def test_anti_coercion():
    p = make_no_eligible_halt_packet(**_valid_kwargs())
    assert issubclass(NoEligibleCoercionError, TypeError)
    for fn in (int, float, complex, str, bytes):
        with pytest.raises(NoEligibleCoercionError):
            fn(p)
    with pytest.raises(NoEligibleCoercionError):
        import operator
        operator.index(p)


# safe repr only
def test_repr_safe_and_limited():
    p = make_no_eligible_halt_packet(**_valid_kwargs())
    r = repr(p)
    assert "phase5_no_eligible_halt_propagation_boundary" in r   # component_name
    assert "NO_ELIGIBLE" in r                                    # status
    assert "NO_ELIGIBLE_CANDIDATE_WITHIN_CHECKED_SCOPE" in r     # no_eligible_reason
    assert "summary.eligible_pairs" not in r                     # source value not exposed
    assert "phase4c_batch_1781637248" not in r
    low = r.lower()
    for banned in ["profit", "edge", "ready", "data quality", "truth"]:
        assert banned not in low


# container values rejected
def test_container_field_values_rejected():
    for bad in [(), ("a",), [1], {"k": "v"}, {1, 2}, frozenset({1})]:
        kwargs = _valid_kwargs()
        kwargs["source_field"] = bad
        with pytest.raises(NoEligibleConstructionError):
            make_no_eligible_halt_packet(**kwargs)


# None rejected for required fields
def test_none_rejected_for_required_fields():
    for name in PLANNED_FIELDS:
        kwargs = _valid_kwargs()
        kwargs[name] = None
        with pytest.raises(NoEligibleConstructionError):
            make_no_eligible_halt_packet(**kwargs)


# pass-through identity
def test_pass_through_identity():
    p = make_no_eligible_halt_packet(**_valid_kwargs())
    assert pass_through_no_eligible_halt_packet(p) is p


# wrong-type pass-through raises NoEligibleTypeError (NOT a packet, no masking)
def test_pass_through_wrong_type_raises():
    assert issubclass(NoEligibleTypeError, TypeError)
    for bad in [None, 42, "x", {"status": "NO_ELIGIBLE"}, ["l"], object()]:
        with pytest.raises(NoEligibleTypeError):
            pass_through_no_eligible_halt_packet(bad)


def test_pass_through_wrong_type_no_stringify_or_introspect():
    class _Hostile:
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __str__(self):
            raise AssertionError("str must not be called")
        def __getattr__(self, name):
            raise AssertionError("introspection must not happen")

    with pytest.raises(NoEligibleTypeError):
        pass_through_no_eligible_halt_packet(_Hostile())


# no BlockedPacket reuse
def test_not_blocked_packet():
    p = make_no_eligible_halt_packet(**_valid_kwargs())
    assert not isinstance(p, BlockedPacket)
    assert not issubclass(NoEligibleHaltPacket, BlockedPacket)


# no numeric / economic fields
def test_no_numeric_or_economic_fields():
    names = {f.name for f in dataclasses.fields(NoEligibleHaltPacket)}
    for banned in ["gross_edge", "net_edge", "cost", "spread", "profitability", "pnl",
                   "sizing", "execution", "edge", "tradeability", "readiness", "size"]:
        assert banned not in names, f"forbidden numeric/economic field: {banned}"
