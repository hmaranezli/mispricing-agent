"""tests/test_phase5_halt_propagation_integration_boundary.py — pins the atomic offline/TDD
implementation of the `phase5_halt_propagation_integration_boundary` exact-type halt-carrier routing
slice.

This implements ONLY exact-type halt-carrier routing:
- an exact BlockedPacket is returned identically (``is`` identity);
- an exact NoEligibleHaltPacket is returned identically (``is`` identity);
- anything else raises HaltPropagationTypeError (a TypeError subclass).

It is not a calculator/parser/adapter/reporting engine and performs no IO/network/env/time/random/
subprocess. It implements no actionable / success-path payload handling yet. Routing uses exact type
checks only (``type(x) is BlockedPacket`` / ``type(x) is NoEligibleHaltPacket``) so subclasses and
look-alikes are rejected; the rejection message uses only ``type(payload).__name__`` or a fixed
phrase and never calls bool/len/int/float/str/bytes/repr/equality or introspects the offending object.
Static hardcoded values only; no IO; no cross-conversion between BLOCKED/CONTRACT_VIOLATION and
NO_ELIGIBLE.
"""
import pytest

from phase5.halt_propagation_integration_boundary import (
    route_halt_carrier,
    HaltPropagationTypeError,
)
from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
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


# error type discipline
def test_error_is_typeerror_subclass():
    assert issubclass(HaltPropagationTypeError, TypeError)


# exact BlockedPacket identity
def test_blocked_packet_identity():
    p = _valid_blocked_packet()
    assert route_halt_carrier(p) is p


# exact NoEligibleHaltPacket identity
def test_no_eligible_packet_identity():
    p = _valid_no_eligible_packet()
    assert route_halt_carrier(p) is p


# no cross-conversion: a routed BlockedPacket stays the exact same BlockedPacket object/type
def test_blocked_not_converted_to_no_eligible():
    p = _valid_blocked_packet()
    out = route_halt_carrier(p)
    assert out is p
    assert type(out) is BlockedPacket
    assert not isinstance(out, NoEligibleHaltPacket)


# no cross-conversion: a routed NoEligibleHaltPacket stays the exact same NoEligibleHaltPacket
def test_no_eligible_not_converted_to_blocked():
    p = _valid_no_eligible_packet()
    out = route_halt_carrier(p)
    assert out is p
    assert type(out) is NoEligibleHaltPacket
    assert not isinstance(out, BlockedPacket)


# BlockedPacket subclass rejected (exact type only)
def test_blocked_subclass_rejected():
    class _Sub(BlockedPacket):
        def __repr__(self):
            raise AssertionError("repr must not be called on subclass")
        def __eq__(self, other):
            raise AssertionError("eq must not be called on subclass")
        def __hash__(self):
            return 0

    sub = object.__new__(_Sub)
    assert isinstance(sub, BlockedPacket)
    with pytest.raises(HaltPropagationTypeError):
        route_halt_carrier(sub)


# NoEligibleHaltPacket subclass rejected (exact type only)
def test_no_eligible_subclass_rejected():
    class _Sub(NoEligibleHaltPacket):
        def __repr__(self):
            raise AssertionError("repr must not be called on subclass")
        def __eq__(self, other):
            raise AssertionError("eq must not be called on subclass")
        def __hash__(self):
            return 0

    sub = object.__new__(_Sub)
    assert isinstance(sub, NoEligibleHaltPacket)
    with pytest.raises(HaltPropagationTypeError):
        route_halt_carrier(sub)


# raw dict / Mapping / arbitrary inputs rejected
def test_raw_and_arbitrary_inputs_rejected():
    import collections.abc

    class _Mapping(collections.abc.Mapping):
        def __getitem__(self, k):
            raise AssertionError("item access must not happen")
        def __iter__(self):
            raise AssertionError("iteration must not happen")
        def __len__(self):
            raise AssertionError("len must not be called")

    for bad in [None, 0, 1, False, True, "x", b"x", 3.14, [], (), {}, set(),
                {"status": "NO_ELIGIBLE"}, object(), _Mapping()]:
        with pytest.raises(HaltPropagationTypeError):
            route_halt_carrier(bad)


# hostile object rejected without str/repr/introspection/coercion
def test_hostile_object_rejected_without_str_repr_introspect():
    class _Hostile:
        def __repr__(self):
            raise AssertionError("repr must not be called")
        def __str__(self):
            raise AssertionError("str must not be called")
        def __bool__(self):
            raise AssertionError("bool must not be called")
        def __len__(self):
            raise AssertionError("len must not be called")
        def __int__(self):
            raise AssertionError("int must not be called")
        def __eq__(self, other):
            raise AssertionError("eq must not be called")
        def __hash__(self):
            return 0
        def __getattr__(self, name):
            raise AssertionError("introspection must not happen")

    with pytest.raises(HaltPropagationTypeError):
        route_halt_carrier(_Hostile())


# rejection message exposes only the type name, not the value
def test_rejection_message_uses_type_name_only():
    class _Marker:
        pass

    with pytest.raises(HaltPropagationTypeError) as exc:
        route_halt_carrier(_Marker())
    assert "_Marker" in str(exc.value)


# carriers are never coerced on the success path (identity, no bool/len evaluation)
def test_carrier_pass_through_does_not_coerce():
    # The carriers themselves fail closed on bool()/len(); routing must not trigger that.
    for p in (_valid_blocked_packet(), _valid_no_eligible_packet()):
        out = route_halt_carrier(p)
        assert out is p
