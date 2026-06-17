"""phase5/observable_cost_friction_boundary.py — atomic observed-cost carrier slice for the
`phase5_observable_cost_friction_boundary` component.

This implements ONLY the atomic `ObservableCostObservation` — a frozen, scalar-only, anti-truthiness,
anti-coercion carrier of exactly ONE explicitly observed cost/friction fact — plus a misrouted
halt-carrier guard. Per the component planning artifact
(`phase5_observable_cost_friction_boundary_implementation_planning.md`):

- it is NOT a calculator, aggregate, parser, loader, endpoint reader, adapter, fee/slippage model,
  reporting, trading, or net-edge component, and performs no IO/network/env/datetime/random/
  subprocess;
- it carries one atomic observed component only and exposes no total/net/effective/edge/profit/
  readiness/eligibility field;
- every field is an exact, non-empty `str`; `signed_decimal_value` is a canonical exact decimal
  string (no float parsing, no binary-float arithmetic, no rounding/normalization);
- missing-as-zero and default-zero are impossible: a numerically zero value requires explicit
  `zero_cost_evidence` (never the not-applicable sentinel);
- sign is preserved exactly (negative = rebate/credit; never clipped, absolutized, or converted);
- it asserts no market truth, cost correctness, source truth, source reliability, liquidity,
  profitability, readiness, or trade eligibility, and authorizes no downstream calculator.
"""
import re

from phase5.blocked_result_boundary import BlockedPacket
from phase5.no_eligible_halt_propagation_boundary import NoEligibleHaltPacket

from dataclasses import dataclass

# Sentinel for "no zero-cost evidence applies" — only valid when the value is NOT numerically zero.
OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE = "OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE"

BOUNDARY_VERSION = "phase5.observable_cost_friction_boundary.v0"

# Canonical exact decimal string: optional leading '-', one or more digits, optional '.' + digits.
# No exponent, no sign other than a single leading '-', no surrounding whitespace, no bare '.'.
_CANONICAL_DECIMAL = re.compile(r"-?\d+(\.\d+)?")

_FIELD_NAMES = (
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "cost_component_type",
    "signed_decimal_value",
    "unit",
    "source_contract",
    "source_artifact",
    "source_field",
    "zero_cost_evidence",
    "boundary_version",
)


class ObservableCostTruthinessError(TypeError):
    """Raised when an ObservableCostObservation is used in a truthiness/length context."""


class ObservableCostCoercionError(TypeError):
    """Raised when an ObservableCostObservation is coerced to a number, string, or bytes."""


class ObservableCostConstructionError(TypeError):
    """Raised when an ObservableCostObservation is constructed with a rejected/missing field value."""


class MisroutedHaltCarrierError(TypeError):
    """Raised when a halt carrier is misrouted into the observable-cost/friction boundary."""


@dataclass(frozen=True, repr=False, init=False)
class ObservableCostObservation:
    """A frozen, scalar-only, anti-coercion carrier of exactly one observed cost/friction fact.

    Construct only through :func:`make_observable_cost_observation`. Direct/positional construction is
    not supported.
    """

    component_name: object
    origin_component: object
    origin_result_status: object
    status: object
    cost_component_type: object
    signed_decimal_value: object
    unit: object
    source_contract: object
    source_artifact: object
    source_field: object
    zero_cost_evidence: object
    boundary_version: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise ObservableCostTruthinessError(
            "ObservableCostObservation must not be evaluated for truthiness; inspect fields instead."
        )

    def __len__(self):
        raise ObservableCostTruthinessError(
            "ObservableCostObservation has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise ObservableCostCoercionError("ObservableCostObservation must not be coerced to int.")

    def __float__(self):
        raise ObservableCostCoercionError("ObservableCostObservation must not be coerced to float.")

    def __complex__(self):
        raise ObservableCostCoercionError(
            "ObservableCostObservation must not be coerced to complex."
        )

    def __index__(self):
        raise ObservableCostCoercionError(
            "ObservableCostObservation must not be coerced to an index."
        )

    def __str__(self):
        raise ObservableCostCoercionError("ObservableCostObservation must not be coerced to str.")

    def __bytes__(self):
        raise ObservableCostCoercionError("ObservableCostObservation must not be coerced to bytes.")

    # --- safe debug repr only (no value/provenance/evidence; no economic/readiness/truth meaning) ---
    def __repr__(self):
        return (
            "ObservableCostObservation(component_name={!r}, status={!r}, cost_component_type={!r}, "
            "unit={!r})".format(
                self.component_name, self.status, self.cost_component_type, self.unit
            )
        )


def _is_numeric_zero(canonical_value):
    """True iff a *canonical* decimal string denotes numeric zero, by string inspection only.

    No float parsing and no arithmetic: a canonical value is zero iff every digit is ``0`` (the sign
    and decimal point are irrelevant). The canonical form guarantees at least one digit.
    """
    digits = canonical_value.lstrip("-").replace(".", "")
    return set(digits) <= {"0"}


def make_observable_cost_observation(
    *,
    component_name,
    origin_component,
    origin_result_status,
    status,
    cost_component_type,
    signed_decimal_value,
    unit,
    source_contract,
    source_artifact,
    source_field,
    zero_cost_evidence,
    boundary_version,
):
    """Keyword-only constructor for a single :class:`ObservableCostObservation`.

    Every field must be an exact, non-empty, non-whitespace ``str`` (``type(value) is str`` — str
    subclasses and non-str scalars/containers are rejected). ``signed_decimal_value`` must be a
    canonical exact decimal string; a numerically zero value requires explicit ``zero_cost_evidence``
    (never the not-applicable sentinel). Error messages use only field names and
    ``type(value).__name__`` — never ``str(value)`` or ``repr(value)``.
    """
    provided = {
        "component_name": component_name,
        "origin_component": origin_component,
        "origin_result_status": origin_result_status,
        "status": status,
        "cost_component_type": cost_component_type,
        "signed_decimal_value": signed_decimal_value,
        "unit": unit,
        "source_contract": source_contract,
        "source_artifact": source_artifact,
        "source_field": source_field,
        "zero_cost_evidence": zero_cost_evidence,
        "boundary_version": boundary_version,
    }
    for name, value in provided.items():
        if value is None:
            raise ObservableCostConstructionError(
                "required field {!r} must not be None".format(name)
            )
        # Exact-type check (not isinstance): str subclasses, bool/int/float/Decimal, containers, and
        # arbitrary objects are all rejected. Never call str/repr/eq on the value.
        if type(value) is not str:
            raise ObservableCostConstructionError(
                "field {!r} must be a str, not {}".format(name, type(value).__name__)
            )
        if value.strip() == "":
            raise ObservableCostConstructionError(
                "field {!r} must be a non-empty, non-whitespace string".format(name)
            )

    # Canonical exact decimal string only — no float parsing, no exponent, no surrounding whitespace.
    if _CANONICAL_DECIMAL.fullmatch(signed_decimal_value) is None:
        raise ObservableCostConstructionError(
            "field 'signed_decimal_value' must be a canonical exact decimal string"
        )

    # Missing-as-zero / default-zero are impossible: a numerically zero value must carry explicit,
    # non-sentinel evidence that zero was actively observed.
    if _is_numeric_zero(signed_decimal_value):
        if zero_cost_evidence == OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE:
            raise ObservableCostConstructionError(
                "field 'zero_cost_evidence' must carry explicit evidence when signed_decimal_value "
                "is numerically zero"
            )

    packet = object.__new__(ObservableCostObservation)
    for name, value in provided.items():
        object.__setattr__(packet, name, value)
    return packet


def reject_misrouted_halt_carrier(payload):
    """Fail closed if a halt carrier is misrouted into the observable-cost/friction boundary.

    - Exact :class:`BlockedPacket` or exact :class:`NoEligibleHaltPacket` → raise
      :class:`MisroutedHaltCarrierError` (a routing/integration bug, not a cost observation).
    - Anything else → return ``None`` (a non-halt no-op); subclasses are NOT exact halt carriers.

    Exact-type checks only (no isinstance). The offending object is never routed, passed through,
    converted, unwrapped, serialized, or reinterpreted, and is never coerced (bool/len/int/float/str/
    bytes), repr'd, equality-compared, or introspected — only its type name is used in the message.
    """
    if type(payload) is BlockedPacket:
        raise MisroutedHaltCarrierError(
            "observable-cost/friction boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    if type(payload) is NoEligibleHaltPacket:
        raise MisroutedHaltCarrierError(
            "observable-cost/friction boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    return None
