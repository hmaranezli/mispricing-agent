"""phase5/observable_cost_source_result_adapter.py — typed source-result carrier + typed-to-typed
adapter slice for the `phase5_observable_cost_source_result_adapter` component.

This implements ONLY:

- a frozen, scalar-only `ObservableCostSourceResult` carrier with the same 12 fields and the same
  construction discipline as `ObservableCostObservation` (exact non-empty `str` fields, canonical
  exact decimal `signed_decimal_value`, and the same zero-cost evidence epistemology); and
- `adapt_observable_cost_source_result_to_observation(result)`, which maps exactly one source result
  1:1 into exactly one `ObservableCostObservation` via the observation factory.

Per the component planning artifact
(`phase5_observable_cost_source_result_adapter_implementation_planning.md`): it is NOT a raw/JSON/
exchange parser, loader, endpoint reader, fee/slippage model, aggregator, or calculator, and performs
no IO/network/env/datetime/random/subprocess. The adapter accepts only the exact source-result type
(no isinstance; subclasses rejected), rejects exact halt carriers as a misroute (reusing the
observation boundary's guard), never reads attributes/coerces/repr's a wrong-typed object, maps every
field 1:1 with explicit keyword arguments (no hardcoding, no inference, no normalization, no invented
zero evidence), delegates all value validation to the observation factory without weakening it, and
never silently returns ``None``. It asserts no market truth, cost correctness, source truth,
profitability, or readiness, and authorizes no calculator/net-edge work.
"""
import re

from dataclasses import dataclass

from phase5.observable_cost_friction_boundary import (
    ObservableCostObservation,
    make_observable_cost_observation,
    reject_misrouted_halt_carrier,
    OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE,
)

BOUNDARY_VERSION = "phase5.observable_cost_source_result_adapter.v0"

# Canonical exact decimal string: optional leading '-', one or more digits, optional '.' + digits.
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


class ObservableCostSourceResultConstructionError(TypeError):
    """Raised when an ObservableCostSourceResult is constructed with a rejected/missing field value."""


class ObservableCostSourceResultTypeError(TypeError):
    """Raised when the adapter receives anything other than an exact ObservableCostSourceResult."""


class ObservableCostSourceResultStateError(ValueError):
    """Raised when an ObservableCostSourceResult carries an unusable state for adaptation."""


@dataclass(frozen=True, repr=False, init=False)
class ObservableCostSourceResult:
    """A frozen, scalar-only typed source-result carrying one observed cost/friction fact.

    Construct only through :func:`make_observable_cost_source_result`. Direct/positional construction
    is not supported. Its fields mirror :class:`ObservableCostObservation` exactly so the adapter can
    map them 1:1 without inference or transformation.
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

    # --- safe debug repr only (no value/provenance/evidence; no economic/readiness/truth meaning) ---
    def __repr__(self):
        return (
            "ObservableCostSourceResult(component_name={!r}, status={!r}, cost_component_type={!r}, "
            "unit={!r})".format(
                self.component_name, self.status, self.cost_component_type, self.unit
            )
        )


def _is_numeric_zero(canonical_value):
    """True iff a *canonical* decimal string denotes numeric zero, by string inspection only.

    No float parsing and no arithmetic: a canonical value is zero iff every digit is ``0``.
    """
    digits = canonical_value.lstrip("-").replace(".", "")
    return set(digits) <= {"0"}


def make_observable_cost_source_result(
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
    """Keyword-only constructor for a single :class:`ObservableCostSourceResult`.

    Enforces the same discipline as the observation factory: every field is an exact, non-empty,
    non-whitespace ``str`` (``type(value) is str``); ``signed_decimal_value`` is a canonical exact
    decimal string preserved verbatim; a numerically zero value requires explicit ``zero_cost_evidence``
    (never the not-applicable sentinel). Error messages use only field names and ``type(value).__name__``.
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
            raise ObservableCostSourceResultConstructionError(
                "required field {!r} must not be None".format(name)
            )
        if type(value) is not str:
            raise ObservableCostSourceResultConstructionError(
                "field {!r} must be a str, not {}".format(name, type(value).__name__)
            )
        if value.strip() == "":
            raise ObservableCostSourceResultConstructionError(
                "field {!r} must be a non-empty, non-whitespace string".format(name)
            )

    if _CANONICAL_DECIMAL.fullmatch(signed_decimal_value) is None:
        raise ObservableCostSourceResultConstructionError(
            "field 'signed_decimal_value' must be a canonical exact decimal string"
        )

    if _is_numeric_zero(signed_decimal_value):
        if zero_cost_evidence == OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE:
            raise ObservableCostSourceResultConstructionError(
                "field 'zero_cost_evidence' must carry explicit evidence when signed_decimal_value "
                "is numerically zero"
            )

    result = object.__new__(ObservableCostSourceResult)
    for name, value in provided.items():
        object.__setattr__(result, name, value)
    return result


def adapt_observable_cost_source_result_to_observation(result):
    """Map exactly one :class:`ObservableCostSourceResult` into one :class:`ObservableCostObservation`.

    - Exact halt carriers (``BlockedPacket`` / ``NoEligibleHaltPacket``) are rejected as a misroute
      via the observation boundary's guard (``MisroutedHaltCarrierError``); halt carriers are never
      converted into cost observations and ``route_halt_carrier`` is not duplicated.
    - Only an exact ``ObservableCostSourceResult`` is accepted (``type(result) is ...``; no isinstance,
      so subclasses are rejected). Any other input raises :class:`ObservableCostSourceResultTypeError`
      using only ``type(result).__name__`` — no attribute access, no ``str``/``repr``, no duck typing.
    - Every field is mapped 1:1 with explicit keyword arguments; nothing is hardcoded, inferred,
      normalized, or invented. All value validation is delegated to ``make_observable_cost_observation``
      and its exceptions are never caught or downgraded. The function never silently returns ``None``.
    """
    # Misroute guard first: raises MisroutedHaltCarrierError for an exact halt carrier, else no-op.
    reject_misrouted_halt_carrier(result)

    # Exact-type only — a subclass could carry hidden state or override behavior. No attribute read,
    # no str/repr of the offending object; only its type name appears in the message.
    if type(result) is not ObservableCostSourceResult:
        raise ObservableCostSourceResultTypeError(
            "adapter requires an exact ObservableCostSourceResult, not " + type(result).__name__
        )

    # Defensive state guard (construction already guarantees an exact non-empty str status); never
    # silently return None or fall through.
    if type(result.status) is not str:
        raise ObservableCostSourceResultStateError(
            "ObservableCostSourceResult.status must be a str for adaptation"
        )

    return make_observable_cost_observation(
        component_name=result.component_name,
        origin_component=result.origin_component,
        origin_result_status=result.origin_result_status,
        status=result.status,
        cost_component_type=result.cost_component_type,
        signed_decimal_value=result.signed_decimal_value,
        unit=result.unit,
        source_contract=result.source_contract,
        source_artifact=result.source_artifact,
        source_field=result.source_field,
        zero_cost_evidence=result.zero_cost_evidence,
        boundary_version=result.boundary_version,
    )
