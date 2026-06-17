"""tests/test_phase5_preflight_to_blocked_packet_adapter.py — pins the offline/TDD implementation of
the `phase5_preflight_to_blocked_packet_adapter` format-boundary adapter.

This adapter converts ONLY a typed/frozen `PreflightResult` in a blocked or contract-violation state
into a `BlockedPacket`, via `make_blocked_packet` with explicit keyword mapping. It is not a
validator/parser and asserts no source-truth/data-quality/economic/readiness/edge property. It must
reject non-PreflightResult inputs (dict/Mapping/arbitrary/attribute-guessed) with a TypeError
subclass, reject success-like / unknown / NO_ELIGIBLE typed inputs with a ValueError subclass, never
return None / empty / default, and never stringify/introspect/coerce/mutate the input. Static
hardcoded PreflightResult values only.
"""
import dataclasses

import pytest

from phase5.input_provenance_preflight import PreflightResult
from phase5.const import (
    PLANNING_GATE_OBSERVED,
    PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
    PLANNING_GATE_CONTRACT_VIOLATION,
)
from phase5.blocked_result_boundary import (
    BlockedPacket,
    BlockedPacketTruthinessError,
    BlockedPacketCoercionError,
)
from phase5.preflight_to_blocked_packet_adapter import (
    adapt_preflight_result_to_blocked_packet,
    PreflightToBlockedPacketTypeError,
    PreflightToBlockedPacketStateError,
    ADAPTER_COMPONENT_NAME,
    ADAPTER_ORIGIN_COMPONENT,
    ADAPTER_CREATED_FROM_CONTRACT,
    ADAPTER_BOUNDARY_VERSION,
)


def _blocked_result():
    return PreflightResult(
        status=PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
        blocked_status="BLOCKED_NEEDS_EVIDENCE",
        blocked_reason="BLOCKED_MISSING_REQUIRED_FIELD",
        missing_or_invalid_field="source_artifact",
        source_contract="phase5_input_schema_refinement_contract.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="summary.eligible_pairs",
        deterministic_next_action="OBTAIN_REQUIRED_EVIDENCE_THEN_REEVALUATE",
        human_review_required=False,
        may_retry_after_evidence=True,
    )


def _violation_result():
    return PreflightResult(
        status=PLANNING_GATE_CONTRACT_VIOLATION,
        blocked_status=None,
        blocked_reason="CONTRACT_VIOLATION_UNSUPPORTED_SOURCE_CONTRACT",
        missing_or_invalid_field="source_contract",
        source_contract="not_a_phase5_contract.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="summary.eligible_pairs",
        deterministic_next_action="HALT_FAIL_CLOSED",
        human_review_required=True,
        may_retry_after_evidence=False,
    )


def _observed_result():
    return PreflightResult(
        status=PLANNING_GATE_OBSERVED,
        blocked_status=None,
        blocked_reason=None,
        missing_or_invalid_field=None,
        source_contract="phase5_input_schema_refinement_contract.md",
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="summary.eligible_pairs",
        deterministic_next_action="NONE_REQUIRED_WITHIN_CHECKED_SCOPE",
        human_review_required=False,
        may_retry_after_evidence=False,
    )


# 1. BLOCKED -> exact field mapping
def test_blocked_result_maps_exactly():
    r = _blocked_result()
    p = adapt_preflight_result_to_blocked_packet(r)
    assert isinstance(p, BlockedPacket)
    assert p.component_name == ADAPTER_COMPONENT_NAME
    assert p.origin_component == ADAPTER_ORIGIN_COMPONENT
    assert p.origin_result_status == r.status
    assert p.status == r.status
    assert p.blocked_status == r.blocked_status
    assert p.reason_code == r.blocked_reason
    assert p.missing_or_invalid_field == r.missing_or_invalid_field
    assert p.source_contract == r.source_contract
    assert p.source_artifact == r.source_artifact
    assert p.source_field == r.source_field
    assert p.deterministic_next_action == r.deterministic_next_action
    assert p.human_review_required == r.human_review_required
    assert p.may_retry_after_evidence == r.may_retry_after_evidence
    assert p.created_from_contract == ADAPTER_CREATED_FROM_CONTRACT
    assert p.boundary_version == ADAPTER_BOUNDARY_VERSION


# 2. CONTRACT_VIOLATION -> exact field mapping
def test_violation_result_maps_exactly():
    r = _violation_result()
    p = adapt_preflight_result_to_blocked_packet(r)
    assert isinstance(p, BlockedPacket)
    assert p.status == PLANNING_GATE_CONTRACT_VIOLATION
    assert p.origin_result_status == PLANNING_GATE_CONTRACT_VIOLATION
    assert p.blocked_status is None
    assert p.reason_code == r.blocked_reason
    assert p.source_contract == r.source_contract
    assert p.source_artifact == r.source_artifact
    assert p.source_field == r.source_field


# 3. OBSERVED typed -> ValueError subclass
def test_observed_typed_raises_state_error():
    assert issubclass(PreflightToBlockedPacketStateError, ValueError)
    with pytest.raises(PreflightToBlockedPacketStateError):
        adapt_preflight_result_to_blocked_packet(_observed_result())


# 4. raw dict -> TypeError subclass
def test_raw_dict_raises_type_error():
    assert issubclass(PreflightToBlockedPacketTypeError, TypeError)
    payload = dict(
        status=PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
        blocked_status="BLOCKED_NEEDS_EVIDENCE",
        blocked_reason="BLOCKED_MISSING_REQUIRED_FIELD",
        missing_or_invalid_field="source_artifact",
        source_contract="phase5_input_schema_refinement_contract.md",
        source_artifact="x",
        source_field="y",
        deterministic_next_action="z",
        human_review_required=False,
        may_retry_after_evidence=True,
    )
    with pytest.raises(PreflightToBlockedPacketTypeError):
        adapt_preflight_result_to_blocked_packet(payload)


# 5. generic Mapping -> TypeError subclass
def test_generic_mapping_raises_type_error():
    import types
    proxy = types.MappingProxyType({"status": PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE})
    with pytest.raises(PreflightToBlockedPacketTypeError):
        adapt_preflight_result_to_blocked_packet(proxy)


# 6. arbitrary object -> TypeError subclass
def test_arbitrary_object_raises_type_error():
    for bad in [None, 42, "a string", object(), [1, 2, 3]]:
        with pytest.raises(PreflightToBlockedPacketTypeError):
            adapt_preflight_result_to_blocked_packet(bad)


# 7. attribute-guessed object -> TypeError subclass with NO attribute introspection
def test_attribute_guessed_object_raises_without_introspection():
    class _LooksLikeResult:
        def __getattr__(self, name):
            raise AssertionError("adapter must not introspect attributes of a non-PreflightResult")

    with pytest.raises(PreflightToBlockedPacketTypeError):
        adapt_preflight_result_to_blocked_packet(_LooksLikeResult())


# 8. NO_ELIGIBLE / unknown status -> ValueError subclass, not encoded as BlockedPacket
def test_no_eligible_or_unknown_status_raises_state_error():
    for status in ["PLANNING_GATE_NO_ELIGIBLE", "NO_ELIGIBLE", "SOMETHING_ELSE"]:
        r = dataclasses.replace(_blocked_result(), status=status)
        with pytest.raises(PreflightToBlockedPacketStateError):
            adapt_preflight_result_to_blocked_packet(r)


# 9. never None / empty / default for allowed inputs
def test_allowed_inputs_never_return_none():
    for r in (_blocked_result(), _violation_result()):
        p = adapt_preflight_result_to_blocked_packet(r)
        assert p is not None
        assert isinstance(p, BlockedPacket)


# 10. anti-truthiness / anti-coercion intact on adapter output
def test_output_packet_anti_truthiness_and_coercion():
    p = adapt_preflight_result_to_blocked_packet(_blocked_result())
    with pytest.raises(BlockedPacketTruthinessError):
        bool(p)
    for fn in (int, float, str, bytes):
        with pytest.raises(BlockedPacketCoercionError):
            fn(p)


# 11. exact component_name and origin_component stamps
def test_exact_stamps():
    assert ADAPTER_COMPONENT_NAME == "phase5_preflight_to_blocked_packet_adapter"
    assert ADAPTER_ORIGIN_COMPONENT == "phase5_input_provenance_preflight"
    p = adapt_preflight_result_to_blocked_packet(_blocked_result())
    assert p.component_name == "phase5_preflight_to_blocked_packet_adapter"
    assert p.origin_component == "phase5_input_provenance_preflight"


# 12. no downgrade / no upgrade / no default conversion
def test_no_downgrade_no_upgrade():
    pb = adapt_preflight_result_to_blocked_packet(_blocked_result())
    assert pb.status == PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE  # not upgraded to OBSERVED
    pv = adapt_preflight_result_to_blocked_packet(_violation_result())
    assert pv.status == PLANNING_GATE_CONTRACT_VIOLATION       # not downgraded to BLOCKED


# 13. source fields carried exactly
def test_source_fields_carried_exactly():
    r = _blocked_result()
    p = adapt_preflight_result_to_blocked_packet(r)
    assert p.source_contract == r.source_contract
    assert p.source_artifact == r.source_artifact
    assert p.source_field == r.source_field


# 14. created_from_contract and boundary_version constants exact
def test_created_from_and_boundary_version_exact():
    assert ADAPTER_CREATED_FROM_CONTRACT == \
        "phase5_preflight_to_blocked_packet_adapter_implementation_planning.md"
    assert ADAPTER_BOUNDARY_VERSION == "phase5.preflight_to_blocked_packet_adapter.v0"
    p = adapt_preflight_result_to_blocked_packet(_violation_result())
    assert p.created_from_contract == ADAPTER_CREATED_FROM_CONTRACT
    assert p.boundary_version == ADAPTER_BOUNDARY_VERSION
