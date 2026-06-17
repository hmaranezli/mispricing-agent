"""phase5/halt_propagation_integration_boundary.py — exact-type halt-carrier routing slice for the
`phase5_halt_propagation_integration_boundary` component.

This implements ONLY exact-type halt-carrier routing, per the component planning artifact
(`phase5_halt_propagation_integration_boundary_implementation_planning.md`):

- an exact :class:`~phase5.blocked_result_boundary.BlockedPacket` is returned identically;
- an exact :class:`~phase5.no_eligible_halt_propagation_boundary.NoEligibleHaltPacket` is returned
  identically;
- anything else raises :class:`HaltPropagationTypeError` (a ``TypeError`` subclass).

It is NOT a calculator/parser/adapter/reporting engine and performs no IO/network/env/datetime/
random/subprocess. It implements no actionable / success-path payload handling yet; that payload type
and the calculator input schema are deferred to a later, separately authorized task.

Routing uses EXACT type checks only (``type(payload) is BlockedPacket`` / ``... is
NoEligibleHaltPacket``) so subclasses and look-alikes are rejected — never an isinstance branch, never
a shared/generic/union halt type. The two carriers are kept semantically separate and are never
cross-converted: a BlockedPacket is never re-emitted as NoEligibleHaltPacket and vice versa. On
rejection the message uses only ``type(payload).__name__`` or a fixed phrase; the offending object is
never coerced (no bool/len/int/float/str/bytes), never repr'd, and never introspected.
"""
from phase5.blocked_result_boundary import BlockedPacket
from phase5.no_eligible_halt_propagation_boundary import NoEligibleHaltPacket

BOUNDARY_COMPONENT_NAME = "phase5_halt_propagation_integration_boundary"
BOUNDARY_VERSION = "phase5.halt_propagation_integration_boundary.v0"
BOUNDARY_CREATED_FROM_CONTRACT = (
    "phase5_halt_propagation_integration_boundary_implementation_planning.md"
)


class HaltPropagationTypeError(TypeError):
    """Raised when the integration boundary receives anything other than an exact halt carrier.

    Unknown / raw / arbitrary / subclass / attribute-guessed input is a contract/integration misuse
    path, not NO_ELIGIBLE; it is never masked as a halt carrier.
    """


def route_halt_carrier(payload):
    """Route an already-typed halt carrier forward unchanged, or fail closed for any other input.

    - Exact :class:`BlockedPacket` → the identical object (``is`` identity); never mutated, never
      downgraded, never re-emitted as a NoEligibleHaltPacket.
    - Exact :class:`NoEligibleHaltPacket` → the identical object (``is`` identity); never mutated,
      never upgraded, never re-emitted as a BlockedPacket.
    - Anything else → :class:`HaltPropagationTypeError`. Subclasses are rejected (exact type only);
      the offending object is never coerced, str/repr'd, or introspected — only its type name is used.
    """
    # Exact-type checks only: a subclass could carry hidden state or override behavior, so it must not
    # route as a valid carrier. No isinstance, no shared/generic/union halt type, no cross-conversion.
    if type(payload) is BlockedPacket:
        return payload
    if type(payload) is NoEligibleHaltPacket:
        return payload
    raise HaltPropagationTypeError(
        "halt-propagation integration boundary requires an exact BlockedPacket or "
        "NoEligibleHaltPacket, not " + type(payload).__name__
    )
