"""phase5/preflight_to_blocked_packet_adapter.py — format-boundary adapter from a typed/frozen
`PreflightResult` to a `BlockedPacket`.

This adapter converts ONLY a `PreflightResult` whose status is `PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE`
or `PLANNING_GATE_CONTRACT_VIOLATION` into a `BlockedPacket`, by calling `make_blocked_packet` with an
explicit keyword field map. It does not validate, parse, repair, enrich, infer, downgrade, or
interpret source data; it reads no artifact, builds no engine, performs no IO/network/env/datetime/
random/subprocess, and asserts no market-truth/data-quality/source-reliability/economic/readiness/edge
property. It authorizes no downstream calculation or next component.

Input discipline (fail-closed, never silent):
- a non-`PreflightResult` input raises `PreflightToBlockedPacketTypeError` (TypeError subclass) — the
  type is checked by `isinstance` before any attribute is read, so no attribute introspection,
  stringify, repr, coercion, or mutation of the input ever happens;
- a typed `PreflightResult` in a success-like (`PLANNING_GATE_OBSERVED`) or any other / unknown /
  NO_ELIGIBLE state raises `PreflightToBlockedPacketStateError` (ValueError subclass);
- the adapter never returns None and never returns an empty/default packet.
"""
from phase5.input_provenance_preflight import PreflightResult
from phase5.const import (
    PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
    PLANNING_GATE_CONTRACT_VIOLATION,
)
from phase5.blocked_result_boundary import make_blocked_packet

ADAPTER_COMPONENT_NAME = "phase5_preflight_to_blocked_packet_adapter"
ADAPTER_ORIGIN_COMPONENT = "phase5_input_provenance_preflight"
ADAPTER_CREATED_FROM_CONTRACT = (
    "phase5_preflight_to_blocked_packet_adapter_implementation_planning.md"
)
ADAPTER_BOUNDARY_VERSION = "phase5.preflight_to_blocked_packet_adapter.v0"

# The only preflight statuses this adapter converts into a BlockedPacket.
_CONVERTIBLE_STATUSES = (
    PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
    PLANNING_GATE_CONTRACT_VIOLATION,
)


class PreflightToBlockedPacketTypeError(TypeError):
    """Raised when the adapter input is not a typed PreflightResult."""


class PreflightToBlockedPacketStateError(ValueError):
    """Raised when a typed PreflightResult carries a state this adapter must not convert."""


def adapt_preflight_result_to_blocked_packet(result):
    """Convert a blocked / contract-violation `PreflightResult` into a `BlockedPacket`.

    Pure and deterministic. The type guard runs first; only a confirmed `PreflightResult` has its
    declared fields read, and only via attribute access of the frozen dataclass (no dict parsing, no
    key guessing, no introspection of arbitrary objects).
    """
    if not isinstance(result, PreflightResult):
        raise PreflightToBlockedPacketTypeError(
            "adapter input must be a phase5 PreflightResult, not "
            + type(result).__name__
        )

    if result.status not in _CONVERTIBLE_STATUSES:
        raise PreflightToBlockedPacketStateError(
            "adapter converts only blocked/contract-violation results; refusing status "
            + repr(result.status)
        )

    return make_blocked_packet(
        component_name=ADAPTER_COMPONENT_NAME,
        origin_component=ADAPTER_ORIGIN_COMPONENT,
        origin_result_status=result.status,
        status=result.status,
        blocked_status=result.blocked_status,
        reason_code=result.blocked_reason,
        missing_or_invalid_field=result.missing_or_invalid_field,
        source_contract=result.source_contract,
        source_artifact=result.source_artifact,
        source_field=result.source_field,
        deterministic_next_action=result.deterministic_next_action,
        human_review_required=result.human_review_required,
        may_retry_after_evidence=result.may_retry_after_evidence,
        created_from_contract=ADAPTER_CREATED_FROM_CONTRACT,
        boundary_version=ADAPTER_BOUNDARY_VERSION,
    )
