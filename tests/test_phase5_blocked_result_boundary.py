"""tests/test_phase5_blocked_result_boundary.py — pins the atomic offline/TDD implementation of the
`phase5_blocked_result_boundary` packet + boundary slice.

This is NOT a validator/parser/calculator/reporting/economic engine. It exercises a frozen
`BlockedPacket` dataclass that carries a blocked/violation result forward without silent downgrade,
plus an explicit keyword-only constructor `make_blocked_packet` and an identity-preserving
`pass_through_blocked_packet`. The packet is anti-truthiness and anti-coercion: bool/len/int/float/
complex/index/str/bytes all raise dedicated TypeError subclasses; only repr (safe debug identifiers)
is allowed. Mutable container field values are rejected at construction; values are never coerced to
0/False/None/empty/eligible/observed/derived/pass/cost/edge/net_edge/readiness/profitability. No
arbitrary dict parsing, no object introspection, no IO. Static hardcoded values only.
"""
import dataclasses

import pytest

from phase5.blocked_result_boundary import (
    BlockedPacket,
    make_blocked_packet,
    pass_through_blocked_packet,
    BlockedPacketTruthinessError,
    BlockedPacketCoercionError,
    BlockedPacketConstructionError,
    BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_CONTRACT,
    BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_ARTIFACT,
    BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_FIELD,
)
from phase5.const import PLANNING_GATE_CONTRACT_VIOLATION


PLANNED_FIELDS = [
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "blocked_status",
    "reason_code",
    "missing_or_invalid_field",
    "source_contract",
    "source_artifact",
    "source_field",
    "deterministic_next_action",
    "human_review_required",
    "may_retry_after_evidence",
    "created_from_contract",
    "boundary_version",
]


def _valid_kwargs():
    return dict(
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


# 2 + hardening. Explicit keyword-only construction; no arbitrary dict; no positional.
def test_explicit_keyword_construction_only():
    packet = make_blocked_packet(**_valid_kwargs())
    assert isinstance(packet, BlockedPacket)


def test_positional_construction_rejected():
    with pytest.raises(TypeError):
        make_blocked_packet("phase5_blocked_result_boundary")  # positional not allowed


def test_arbitrary_dict_not_accepted_positionally():
    with pytest.raises(TypeError):
        make_blocked_packet(_valid_kwargs())  # a dict is not a valid positional input


# 3. frozen dataclass
def test_packet_is_frozen_dataclass():
    packet = make_blocked_packet(**_valid_kwargs())
    assert dataclasses.is_dataclass(packet)
    assert packet.__dataclass_params__.frozen is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        packet.status = "MUTATED"


# 4 + 5. truthiness
def test_bool_raises_truthiness_error():
    packet = make_blocked_packet(**_valid_kwargs())
    assert issubclass(BlockedPacketTruthinessError, TypeError)
    with pytest.raises(BlockedPacketTruthinessError):
        bool(packet)


def test_if_packet_raises_truthiness_error():
    packet = make_blocked_packet(**_valid_kwargs())
    with pytest.raises(BlockedPacketTruthinessError):
        _ = "yes" if packet else "no"


# 6. len
def test_len_raises_truthiness_error():
    packet = make_blocked_packet(**_valid_kwargs())
    with pytest.raises(BlockedPacketTruthinessError):
        len(packet)


# 7. coercion
def test_numeric_and_string_coercion_raises_coercion_error():
    packet = make_blocked_packet(**_valid_kwargs())
    assert issubclass(BlockedPacketCoercionError, TypeError)
    for fn in (int, float, complex, str, bytes):
        with pytest.raises(BlockedPacketCoercionError):
            fn(packet)


def test_index_coercion_raises_coercion_error():
    packet = make_blocked_packet(**_valid_kwargs())
    with pytest.raises(BlockedPacketCoercionError):
        import operator
        operator.index(packet)


# 8. repr allowed, limited to safe debug identifiers
def test_repr_is_safe_and_limited():
    packet = make_blocked_packet(**_valid_kwargs())
    r = repr(packet)
    assert "phase5_blocked_result_boundary" in r          # component_name
    assert "PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE" in r     # status
    assert "BLOCKED_MISSING_REQUIRED_FIELD" in r           # reason_code
    # must not leak source provenance values or imply truth/economic/readiness meaning
    assert "summary.eligible_pairs" not in r               # source_field value not exposed
    assert "phase4c_batch_1781637248" not in r             # source_artifact value not exposed
    low = r.lower()
    for banned in ["profit", "edge", "ready", "data quality", "truth", "economic"]:
        assert banned not in low, f"repr implies {banned!r}"


# 9. exact field set
def test_packet_exposes_exactly_planned_fields():
    packet = make_blocked_packet(**_valid_kwargs())
    names = [f.name for f in dataclasses.fields(packet)]
    assert set(names) == set(PLANNED_FIELDS)
    assert len(names) == len(PLANNED_FIELDS)


# 10. pass-through identity
def test_pass_through_returns_identical_object():
    packet = make_blocked_packet(**_valid_kwargs())
    assert pass_through_blocked_packet(packet) is packet


# 11 + hardening. non-packet fails closed (no exception, no default), uses unknown sentinels
def test_pass_through_non_packet_fails_closed():
    for bad in [None, 42, "a string", {"status": "x"}, ["list"], object()]:
        result = pass_through_blocked_packet(bad)
        assert isinstance(result, BlockedPacket)
        assert result.status == PLANNING_GATE_CONTRACT_VIOLATION
        assert result.source_contract == BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_CONTRACT
        assert result.source_artifact == BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_ARTIFACT
        assert result.source_field == BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_FIELD


# 12. mutable container field values rejected at construction
def test_mutable_field_values_rejected():
    for bad_value in ([1, 2], {"k": "v"}, {1, 2}, frozenset({1, 2})):
        kwargs = _valid_kwargs()
        kwargs["source_field"] = bad_value
        with pytest.raises(BlockedPacketConstructionError):
            make_blocked_packet(**kwargs)


# 13. values not coerced
def test_values_not_coerced():
    kwargs = _valid_kwargs()
    packet = make_blocked_packet(**kwargs)
    assert packet.human_review_required is False
    assert packet.may_retry_after_evidence is True
    # explicit values preserved, not turned into 0/None/empty/eligible/observed/etc.
    assert packet.blocked_status == "BLOCKED_NEEDS_EVIDENCE"
    assert packet.status == "PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE"


# 14. source fields and origin metadata preserved exactly
def test_source_and_origin_preserved_exactly():
    kwargs = _valid_kwargs()
    packet = make_blocked_packet(**kwargs)
    for name in PLANNED_FIELDS:
        assert getattr(packet, name) == kwargs[name], f"field not preserved: {name}"
