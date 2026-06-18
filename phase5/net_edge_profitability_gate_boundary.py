"""phase5/net_edge_profitability_gate_boundary.py — FIRST carrier slice of the
`phase5_net_edge_profitability_gate_boundary` component: `ProfitabilityThresholdPolicyContext`.

This implements ONLY the atomic `ProfitabilityThresholdPolicyContext` — a frozen, anti-truthiness,
anti-coercion carrier of explicit threshold policy data and provenance — plus a misrouted halt-carrier
guard. Per the planning artifact (`phase5_net_edge_profitability_gate_implementation_planning.md`):

- it is NOT `NetEdgeProfitabilityGate`, NOT `net_edge_profitability_preflight`, NOT a comparator/
  calculator, and performs no IO/network/env/datetime/random/subprocess;
- it carries declared threshold metadata only: it does NOT compare `threshold_value` to zero, does
  NOT interpret profitability, does NOT compare `threshold_unit` to any result unit, does NOT parse
  provenance, and does NOT compute/infer/default a threshold (no hardcoded/env/config/file/db value);
- every field is an exact, non-empty, non-whitespace `str` (`type(value) is str`; str subclasses
  rejected); `threshold_value` is a canonical signed decimal string (no leading zeros, no exponent,
  no surrounding whitespace), preserved verbatim — negative, zero, and positive are all valid policy
  data (no sign morality);
- it asserts no edge, no profitability, no readiness, no actionability, and no source truth.
"""
import re

from dataclasses import dataclass

from phase5.blocked_result_boundary import BlockedPacket
from phase5.no_eligible_halt_propagation_boundary import NoEligibleHaltPacket

PROFITABILITY_THRESHOLD_POLICY_COMPONENT_NAME = "phase5_net_edge_profitability_gate_boundary"
BOUNDARY_VERSION = "phase5.net_edge_profitability_gate_boundary.v0"

# Canonical signed decimal string: optional leading '-', integer part with no leading zeros
# (a lone '0' or a non-zero-leading run of digits), optional '.' + one-or-more digits. No exponent,
# no leading '+', no surrounding whitespace, no bare '.'.
_CANONICAL_SIGNED_DECIMAL = re.compile(r"-?(0|[1-9]\d*)(\.\d+)?")

_FIELD_NAMES = (
    "component_name",
    "threshold_value",
    "threshold_unit",
    "source_contract",
    "source_artifact",
    "source_field",
    "policy_id",
    "boundary_version",
)


class ProfitabilityThresholdPolicyTruthinessError(TypeError):
    """Raised when a ProfitabilityThresholdPolicyContext is used in a truthiness/length context."""


class ProfitabilityThresholdPolicyCoercionError(TypeError):
    """Raised when a ProfitabilityThresholdPolicyContext is coerced to a number, string, or bytes."""


class ProfitabilityThresholdPolicyConstructionError(TypeError):
    """Raised when a ProfitabilityThresholdPolicyContext is constructed with a rejected/missing value."""


class MisroutedHaltCarrierError(TypeError):
    """Raised when a halt carrier is misrouted into the net-edge profitability gate boundary."""


@dataclass(frozen=True, repr=False, init=False)
class ProfitabilityThresholdPolicyContext:
    """A frozen, anti-coercion carrier of explicit profitability-threshold policy data and provenance.

    Construct only through :func:`make_profitability_threshold_policy_context`. Direct/positional
    construction is not supported. This context carries the declared threshold value/unit and its
    provenance; it proves no profitability and is not a comparator.
    """

    component_name: object
    threshold_value: object
    threshold_unit: object
    source_contract: object
    source_artifact: object
    source_field: object
    policy_id: object
    boundary_version: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise ProfitabilityThresholdPolicyTruthinessError(
            "ProfitabilityThresholdPolicyContext must not be evaluated for truthiness; inspect fields."
        )

    def __len__(self):
        raise ProfitabilityThresholdPolicyTruthinessError(
            "ProfitabilityThresholdPolicyContext has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to int."
        )

    def __float__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to float."
        )

    def __complex__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to complex."
        )

    def __index__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to an index."
        )

    def __str__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to str."
        )

    def __bytes__(self):
        raise ProfitabilityThresholdPolicyCoercionError(
            "ProfitabilityThresholdPolicyContext must not be coerced to bytes."
        )

    # --- safe debug repr only (safe identifiers; no threshold value or sensitive provenance leak) ---
    def __repr__(self):
        return (
            "ProfitabilityThresholdPolicyContext(component_name={!r}, policy_id={!r})".format(
                self.component_name, self.policy_id
            )
        )


def make_profitability_threshold_policy_context(
    *,
    component_name,
    threshold_value,
    threshold_unit,
    source_contract,
    source_artifact,
    source_field,
    policy_id,
    boundary_version,
):
    """Keyword-only constructor for a single :class:`ProfitabilityThresholdPolicyContext`.

    Every field must be an exact, non-empty, non-whitespace ``str`` (``type(value) is str`` — str
    subclasses and non-str scalars/containers are rejected). ``threshold_value`` must additionally be a
    canonical signed decimal string (no leading zeros, no exponent) and is preserved verbatim; negative,
    zero, and positive values are all valid (no sign comparison, no zero check, no normalization). No
    provenance parsing, no unit/threshold inference, and no defaulting are performed. Error messages use
    only field names and ``type(value).__name__`` — never ``str(value)`` or ``repr(value)``.
    """
    provided = {
        "component_name": component_name,
        "threshold_value": threshold_value,
        "threshold_unit": threshold_unit,
        "source_contract": source_contract,
        "source_artifact": source_artifact,
        "source_field": source_field,
        "policy_id": policy_id,
        "boundary_version": boundary_version,
    }
    for name, value in provided.items():
        if value is None:
            raise ProfitabilityThresholdPolicyConstructionError(
                "required field {!r} must not be None".format(name)
            )
        # Exact-type check (not isinstance): str subclasses, bool/int/float/Decimal, containers, and
        # arbitrary objects are all rejected. Never call str/repr/eq on the value.
        if type(value) is not str:
            raise ProfitabilityThresholdPolicyConstructionError(
                "field {!r} must be a str, not {}".format(name, type(value).__name__)
            )
        if value.strip() == "":
            raise ProfitabilityThresholdPolicyConstructionError(
                "field {!r} must be a non-empty, non-whitespace string".format(name)
            )

    # Canonical signed decimal string only — preserved verbatim; no Decimal/float, no normalization,
    # no zero/sign comparison.
    if _CANONICAL_SIGNED_DECIMAL.fullmatch(threshold_value) is None:
        raise ProfitabilityThresholdPolicyConstructionError(
            "field 'threshold_value' must be a canonical signed decimal string"
        )

    context = object.__new__(ProfitabilityThresholdPolicyContext)
    for name, value in provided.items():
        object.__setattr__(context, name, value)
    return context


def reject_misrouted_halt_carrier(payload):
    """Fail closed if a halt carrier is misrouted into the net-edge profitability gate boundary.

    - Exact :class:`BlockedPacket` or exact :class:`NoEligibleHaltPacket` → raise
      :class:`MisroutedHaltCarrierError` (a routing/integration bug, not a threshold policy).
    - Anything else → return ``None`` (a non-halt no-op); subclasses are NOT exact halt carriers.

    Exact-type checks only (no isinstance). The offending object is never routed, converted, unwrapped,
    serialized, or reinterpreted, and is never coerced (bool/len/int/float/str/bytes), repr'd,
    equality-compared, or introspected — only its type name is used in the message.
    """
    if type(payload) is BlockedPacket:
        raise MisroutedHaltCarrierError(
            "net-edge profitability gate boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    if type(payload) is NoEligibleHaltPacket:
        raise MisroutedHaltCarrierError(
            "net-edge profitability gate boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    return None
