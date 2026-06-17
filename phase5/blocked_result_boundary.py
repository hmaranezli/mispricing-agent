"""phase5/blocked_result_boundary.py — atomic packet + boundary slice for the
`phase5_blocked_result_boundary` component.

This module implements ONLY the atomic frozen `BlockedPacket` and the boundary enforcement rules
defined by the planning artifact:

- explicit, keyword-only construction (no arbitrary dict parsing, no object introspection);
- immutable packet fields (frozen dataclass);
- anti-truthiness and anti-coercion (bool/len/int/float/complex/index/str/bytes all fail closed);
- identity pass-through, or a fail-closed contract-violation packet for a non-packet input.

It is NOT a validator, parser, calculator, reporting/economic engine, or runtime integration. It
performs no IO/network/env/datetime/random/subprocess. It asserts no market truth, data quality,
source truth, source reliability, economic validity, profitability, readiness, or edge. The blocked
packet is a carried error/state record only; it authorizes no downstream or implementation work.
"""
from dataclasses import dataclass, fields as _dataclass_fields

from phase5.const import (
    PLANNING_GATE_CONTRACT_VIOLATION,
    NEXT_ACTION_HALT,
)

# --- Boundary-local constants (not source evidence, not source truth, not data quality, not a
#     readiness/economic claim; unknown-provenance placeholders only). ---
CV_MALFORMED_BOUNDARY_PACKET = "CONTRACT_VIOLATION_MALFORMED_BOUNDARY_PACKET"
BOUNDARY_VERSION = "phase5.blocked_result_boundary.v0"
BOUNDARY_CREATED_FROM_CONTRACT = "phase5_blocked_result_boundary_implementation_planning.md"

BLOCKED_RESULT_BOUNDARY_UNKNOWN_ORIGIN = "BLOCKED_RESULT_BOUNDARY_UNKNOWN_ORIGIN"
BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_CONTRACT = "BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_CONTRACT"
BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_ARTIFACT = "BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_ARTIFACT"
BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_FIELD = "BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_FIELD"

# Container field values rejected at construction in this atomic slice (no silent conversion).
# Packet fields are scalar-only, so every container type — including tuple — is rejected; a rejected
# top-level container also blocks any nested container before it can be carried.
_REJECTED_FIELD_TYPES = (tuple, list, dict, set, frozenset)

# Fields explicitly documented as nullable; every other field must be explicitly non-None.
_NULLABLE_FIELDS = frozenset({"blocked_status", "missing_or_invalid_field"})


class BlockedPacketTruthinessError(TypeError):
    """Raised when a BlockedPacket is used in a truthiness/length context."""


class BlockedPacketCoercionError(TypeError):
    """Raised when a BlockedPacket is coerced to a number, string, or bytes."""


class BlockedPacketConstructionError(TypeError):
    """Raised when a BlockedPacket is constructed with a rejected (mutable container) field value."""


@dataclass(frozen=True, repr=False)
class BlockedPacket:
    """A frozen, anti-coercion record carrying a blocked/violation result forward unchanged.

    Construct only through :func:`make_blocked_packet`. The packet exposes exactly the planned
    fields and refuses to be interpreted by truthiness or coercion.
    """

    component_name: object
    origin_component: object
    origin_result_status: object
    status: object
    blocked_status: object
    reason_code: object
    missing_or_invalid_field: object
    source_contract: object
    source_artifact: object
    source_field: object
    deterministic_next_action: object
    human_review_required: object
    may_retry_after_evidence: object
    created_from_contract: object
    boundary_version: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise BlockedPacketTruthinessError(
            "BlockedPacket must not be evaluated for truthiness; inspect status/reason_code instead."
        )

    def __len__(self):
        raise BlockedPacketTruthinessError(
            "BlockedPacket has no length; inspect status/reason_code instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise BlockedPacketCoercionError("BlockedPacket must not be coerced to int.")

    def __float__(self):
        raise BlockedPacketCoercionError("BlockedPacket must not be coerced to float.")

    def __complex__(self):
        raise BlockedPacketCoercionError("BlockedPacket must not be coerced to complex.")

    def __index__(self):
        raise BlockedPacketCoercionError("BlockedPacket must not be coerced to an index.")

    def __str__(self):
        raise BlockedPacketCoercionError("BlockedPacket must not be coerced to str.")

    def __bytes__(self):
        raise BlockedPacketCoercionError("BlockedPacket must not be coerced to bytes.")

    # --- safe debug repr only (no truth/data-quality/economic/readiness meaning) ---
    def __repr__(self):
        return (
            "BlockedPacket(component_name={!r}, status={!r}, reason_code={!r})".format(
                self.component_name, self.status, self.reason_code
            )
        )


def make_blocked_packet(
    *,
    component_name,
    origin_component,
    origin_result_status,
    status,
    blocked_status,
    reason_code,
    missing_or_invalid_field,
    source_contract,
    source_artifact,
    source_field,
    deterministic_next_action,
    human_review_required,
    may_retry_after_evidence,
    created_from_contract,
    boundary_version,
):
    """Explicit, keyword-only constructor for a :class:`BlockedPacket`.

    Accepts only named field values — never an arbitrary dict, never object attribute inspection.
    Rejects mutable container field values (list/dict/set/frozenset) rather than silently converting
    them. Preserves every provided value exactly.
    """
    provided = {
        "component_name": component_name,
        "origin_component": origin_component,
        "origin_result_status": origin_result_status,
        "status": status,
        "blocked_status": blocked_status,
        "reason_code": reason_code,
        "missing_or_invalid_field": missing_or_invalid_field,
        "source_contract": source_contract,
        "source_artifact": source_artifact,
        "source_field": source_field,
        "deterministic_next_action": deterministic_next_action,
        "human_review_required": human_review_required,
        "may_retry_after_evidence": may_retry_after_evidence,
        "created_from_contract": created_from_contract,
        "boundary_version": boundary_version,
    }
    for name, value in provided.items():
        if value is None and name not in _NULLABLE_FIELDS:
            raise BlockedPacketConstructionError(
                "required field {!r} must not be None".format(name)
            )
        if isinstance(value, _REJECTED_FIELD_TYPES):
            raise BlockedPacketConstructionError(
                "field {!r} rejects a container value in this atomic slice".format(name)
            )
    return BlockedPacket(**provided)


def _fail_closed_boundary_packet(*, origin_result_status):
    """A deterministic fail-closed contract-violation packet for a non-packet boundary input."""
    return make_blocked_packet(
        component_name="phase5_blocked_result_boundary",
        origin_component=BLOCKED_RESULT_BOUNDARY_UNKNOWN_ORIGIN,
        origin_result_status=origin_result_status,
        status=PLANNING_GATE_CONTRACT_VIOLATION,
        blocked_status=None,
        reason_code=CV_MALFORMED_BOUNDARY_PACKET,
        missing_or_invalid_field=None,
        source_contract=BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_CONTRACT,
        source_artifact=BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_ARTIFACT,
        source_field=BLOCKED_RESULT_BOUNDARY_UNKNOWN_SOURCE_FIELD,
        deterministic_next_action=NEXT_ACTION_HALT,
        human_review_required=True,
        may_retry_after_evidence=False,
        created_from_contract=BOUNDARY_CREATED_FROM_CONTRACT,
        boundary_version=BOUNDARY_VERSION,
    )


def pass_through_blocked_packet(packet):
    """Carry a blocked/violation packet forward unchanged, or fail closed for a non-packet input.

    - If ``packet`` is a :class:`BlockedPacket`, the identical object is returned (``is`` identity);
      its status, reason code, source fields, and origin metadata are never mutated or downgraded.
    - If ``packet`` is not a :class:`BlockedPacket`, a new fail-closed contract-violation packet is
      returned — never an exception, never a default/empty value.
    """
    if isinstance(packet, BlockedPacket):
        return packet
    # Sanitized class name only: no str()/repr() of the object, no attribute introspection.
    sanitized_type = type(packet).__name__
    return _fail_closed_boundary_packet(origin_result_status=sanitized_type)
