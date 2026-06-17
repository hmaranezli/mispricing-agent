"""phase5/no_eligible_halt_propagation_boundary.py — atomic carrier + pass-through slice for the
`phase5_no_eligible_halt_propagation_boundary` component.

This implements ONLY the atomic `NoEligibleHaltPacket` and its identity pass-through. NO_ELIGIBLE is a
non-error halt/bypass signal kept semantically separate from `BlockedPacket`; this module does not
reuse `BlockedPacket`, exposes no numeric/economic field, and performs no upstream source-result
conversion. It is not a calculator/parser/adapter and performs no IO/network/env/datetime/random/
subprocess. It asserts no source truth, data quality, source reliability, safety, readiness,
profitability, alpha, edge, net-edge, execution, trading, or paper/live property; it authorizes no
downstream calculation or next component.

The packet is frozen, scalar-only, anti-truthiness, and anti-coercion. It is constructed only through
the keyword-only factory `make_no_eligible_halt_packet`; positional construction (factory or direct)
is rejected. `pass_through_no_eligible_halt_packet` returns the identical packet for a
`NoEligibleHaltPacket`, and otherwise raises `NoEligibleTypeError` without str/repr/introspection of
the offending object (system/type errors are never masked as NO_ELIGIBLE).
"""
from dataclasses import dataclass

# Container field values rejected at construction (scalar-only fields; no silent conversion).
_REJECTED_FIELD_TYPES = (tuple, list, dict, set, frozenset)

# Every field is required and explicitly non-None in this atomic slice.
_FIELD_NAMES = (
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
)


class NoEligibleTruthinessError(TypeError):
    """Raised when a NoEligibleHaltPacket is used in a truthiness/length context."""


class NoEligibleCoercionError(TypeError):
    """Raised when a NoEligibleHaltPacket is coerced to a number, string, or bytes."""


class NoEligibleConstructionError(TypeError):
    """Raised when a NoEligibleHaltPacket is constructed with a rejected or missing field value."""


class NoEligibleTypeError(TypeError):
    """Raised when pass-through receives something other than a NoEligibleHaltPacket."""


@dataclass(frozen=True, repr=False, init=False)
class NoEligibleHaltPacket:
    """A frozen, scalar-only, anti-coercion carrier of a non-error no-eligible halt signal.

    Construct only through :func:`make_no_eligible_halt_packet`. Direct/positional construction is
    not supported.
    """

    component_name: object
    origin_component: object
    origin_result_status: object
    status: object
    no_eligible_reason: object
    source_contract: object
    source_artifact: object
    source_field: object
    deterministic_next_action: object
    boundary_version: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise NoEligibleTruthinessError(
            "NoEligibleHaltPacket must not be evaluated for truthiness; inspect status instead."
        )

    def __len__(self):
        raise NoEligibleTruthinessError(
            "NoEligibleHaltPacket has no length; inspect status instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise NoEligibleCoercionError("NoEligibleHaltPacket must not be coerced to int.")

    def __float__(self):
        raise NoEligibleCoercionError("NoEligibleHaltPacket must not be coerced to float.")

    def __complex__(self):
        raise NoEligibleCoercionError("NoEligibleHaltPacket must not be coerced to complex.")

    def __index__(self):
        raise NoEligibleCoercionError("NoEligibleHaltPacket must not be coerced to an index.")

    def __str__(self):
        raise NoEligibleCoercionError("NoEligibleHaltPacket must not be coerced to str.")

    def __bytes__(self):
        raise NoEligibleCoercionError("NoEligibleHaltPacket must not be coerced to bytes.")

    # --- safe debug repr only (no numeric/economic/readiness/truth meaning) ---
    def __repr__(self):
        return (
            "NoEligibleHaltPacket(component_name={!r}, status={!r}, no_eligible_reason={!r})".format(
                self.component_name, self.status, self.no_eligible_reason
            )
        )


def make_no_eligible_halt_packet(
    *,
    component_name,
    origin_component,
    origin_result_status,
    status,
    no_eligible_reason,
    source_contract,
    source_artifact,
    source_field,
    deterministic_next_action,
    boundary_version,
):
    """Keyword-only constructor for a :class:`NoEligibleHaltPacket`.

    Rejects None for any required field and rejects mutable/sequence container field values rather
    than silently converting them. Preserves every provided value exactly.
    """
    provided = {
        "component_name": component_name,
        "origin_component": origin_component,
        "origin_result_status": origin_result_status,
        "status": status,
        "no_eligible_reason": no_eligible_reason,
        "source_contract": source_contract,
        "source_artifact": source_artifact,
        "source_field": source_field,
        "deterministic_next_action": deterministic_next_action,
        "boundary_version": boundary_version,
    }
    for name, value in provided.items():
        if value is None:
            raise NoEligibleConstructionError("required field {!r} must not be None".format(name))
        if isinstance(value, _REJECTED_FIELD_TYPES):
            raise NoEligibleConstructionError(
                "field {!r} rejects a container value in this atomic slice".format(name)
            )
        # Every field must be an explicit non-empty string. Use exact-type check (not isinstance) so
        # str subclasses and non-string scalars are rejected; never call str/repr/eq on the value.
        if type(value) is not str:
            raise NoEligibleConstructionError(
                "field {!r} must be a str, not {}".format(name, type(value).__name__)
            )
        if value.strip() == "":
            raise NoEligibleConstructionError(
                "field {!r} must be a non-empty, non-whitespace string".format(name)
            )
    packet = object.__new__(NoEligibleHaltPacket)
    for name, value in provided.items():
        object.__setattr__(packet, name, value)
    return packet


def pass_through_no_eligible_halt_packet(packet):
    """Carry a no-eligible halt signal forward unchanged.

    Returns the identical object for a :class:`NoEligibleHaltPacket`. For any other input it raises
    :class:`NoEligibleTypeError` — it never returns a packet, never masks a system/type error as
    NO_ELIGIBLE, and never calls str/repr or introspects the offending object (only its type name is
    used in the message).
    """
    # Exact-type check (not isinstance): the packet is an atomic sealed carrier, so a subclass — which
    # could carry hidden state or override behavior — must not pass through as a valid packet.
    if type(packet) is NoEligibleHaltPacket:
        return packet
    raise NoEligibleTypeError(
        "pass-through requires an exact NoEligibleHaltPacket, not " + type(packet).__name__
    )
