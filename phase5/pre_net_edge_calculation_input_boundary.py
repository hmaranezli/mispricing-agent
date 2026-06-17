"""phase5/pre_net_edge_calculation_input_boundary.py — FIRST carrier slice of the
`phase5_pre_net_edge_calculation_input_boundary` component: `ObservableCostValidityContext`.

This implements ONLY the atomic `ObservableCostValidityContext` — a frozen, anti-truthiness,
anti-coercion carrier that wraps exactly ONE `ObservableCostObservation` plus explicit, declared
validity-interval metadata and provenance — plus a misrouted halt-carrier guard. Per the component
planning artifact (`phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md`):

- it is NOT `PreNetEdgeCalculationInput`, NOT a gate/preflight, NOT a calculator, NOT a parser/
  adapter/loader/endpoint reader/order-book model/cost aggregator/reporting/trading/paper-live/
  net-edge component, and performs no IO/network/env/datetime/random/subprocess;
- it carries declared validity metadata only: it does NOT compare `valid_from_epoch_ms` to
  `valid_until_epoch_ms`, does NOT compare the interval to any gross observation time, does NOT
  compute freshness/TTL/duration/valid_until, and does NOT infer validity from the wrapped
  observation's source_* fields (a reversed or equal interval is accepted as a format-only carrier);
- the wrapped `cost_observation` must be an exact `ObservableCostObservation` (no isinstance;
  subclasses rejected); every metadata field is an exact, non-empty, non-whitespace `str`
  (`type(value) is str`); `valid_from_epoch_ms`/`valid_until_epoch_ms` are exact integer strings
  (``^\\d+$`` — no sign, no decimal point, no exponent), preserved verbatim;
- it proves no validity, no market truth, no cost truth, no source truth, no profitability, and no
  readiness, and authorizes no downstream gate/calculator/net-edge work.
"""
import re

from dataclasses import dataclass

from phase5.observable_cost_friction_boundary import ObservableCostObservation
from phase5.gross_edge_observation_boundary import GrossEdgeObservation
from phase5.blocked_result_boundary import BlockedPacket
from phase5.no_eligible_halt_propagation_boundary import NoEligibleHaltPacket

BOUNDARY_VERSION = "phase5.pre_net_edge_calculation_input_boundary.v0"

# Exact integer string: one or more digits, no sign, no decimal point, no exponent, no whitespace.
_EXACT_INTEGER = re.compile(r"\d+")

# Metadata fields that must be exact, non-empty `str` (validated uniformly).
_STR_FIELDS = (
    "valid_from_epoch_ms",
    "valid_until_epoch_ms",
    "validity_source_contract",
    "validity_source_artifact",
    "validity_source_field",
    "validity_assertion_type",
    "boundary_version",
)

# Metadata fields that, in addition to the str rules, must be exact integer strings.
_INTEGER_STRING_FIELDS = (
    "valid_from_epoch_ms",
    "valid_until_epoch_ms",
)


class ObservableCostValidityTruthinessError(TypeError):
    """Raised when an ObservableCostValidityContext is used in a truthiness/length context."""


class ObservableCostValidityCoercionError(TypeError):
    """Raised when an ObservableCostValidityContext is coerced to a number, string, or bytes."""


class ObservableCostValidityConstructionError(TypeError):
    """Raised when an ObservableCostValidityContext is constructed with a rejected/missing value."""


class ObservableCostValidityTypeError(TypeError):
    """Raised when an operation receives anything other than an exact ObservableCostValidityContext."""


class MisroutedHaltCarrierError(TypeError):
    """Raised when a halt carrier is misrouted into the pre-net-edge calculation-input boundary."""


@dataclass(frozen=True, repr=False, init=False)
class ObservableCostValidityContext:
    """A frozen, anti-coercion carrier wrapping one observed cost fact plus declared validity metadata.

    Construct only through :func:`make_observable_cost_validity_context`. Direct/positional
    construction is not supported. This carrier asserts no validity truth; it only carries the
    declared validity interval and its provenance alongside exactly one
    :class:`ObservableCostObservation`.
    """

    cost_observation: object
    valid_from_epoch_ms: object
    valid_until_epoch_ms: object
    validity_source_contract: object
    validity_source_artifact: object
    validity_source_field: object
    validity_assertion_type: object
    boundary_version: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise ObservableCostValidityTruthinessError(
            "ObservableCostValidityContext must not be evaluated for truthiness; inspect fields instead."
        )

    def __len__(self):
        raise ObservableCostValidityTruthinessError(
            "ObservableCostValidityContext has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise ObservableCostValidityCoercionError(
            "ObservableCostValidityContext must not be coerced to int."
        )

    def __float__(self):
        raise ObservableCostValidityCoercionError(
            "ObservableCostValidityContext must not be coerced to float."
        )

    def __complex__(self):
        raise ObservableCostValidityCoercionError(
            "ObservableCostValidityContext must not be coerced to complex."
        )

    def __index__(self):
        raise ObservableCostValidityCoercionError(
            "ObservableCostValidityContext must not be coerced to an index."
        )

    def __str__(self):
        raise ObservableCostValidityCoercionError(
            "ObservableCostValidityContext must not be coerced to str."
        )

    def __bytes__(self):
        raise ObservableCostValidityCoercionError(
            "ObservableCostValidityContext must not be coerced to bytes."
        )

    # --- safe debug repr only (no interval/provenance/observation; no freshness/validity/economic
    #     meaning) ---
    def __repr__(self):
        return (
            "ObservableCostValidityContext(validity_assertion_type={!r}, "
            "boundary_version={!r})".format(
                self.validity_assertion_type, self.boundary_version
            )
        )


def make_observable_cost_validity_context(
    *,
    cost_observation,
    valid_from_epoch_ms,
    valid_until_epoch_ms,
    validity_source_contract,
    validity_source_artifact,
    validity_source_field,
    validity_assertion_type,
    boundary_version,
):
    """Keyword-only constructor for a single :class:`ObservableCostValidityContext`.

    ``cost_observation`` must be an exact :class:`ObservableCostObservation` (``type(...) is ...`` —
    no isinstance, so subclasses, halt carriers, dicts/Mappings, duck-typed records, and arbitrary
    objects are all rejected without reading attributes/coercing/repr'ing them). Every metadata field
    must be an exact, non-empty, non-whitespace ``str`` (``type(value) is str``); ``valid_from_epoch_ms``
    and ``valid_until_epoch_ms`` must additionally be exact integer strings (``^\\d+$``) and are
    preserved verbatim. No comparison of the interval bounds, no inference from the observation's
    source_* fields, and no freshness/TTL/valid_until computation are performed. Error messages use
    only field names and ``type(value).__name__`` — never ``str(value)`` or ``repr(value)``.
    """
    # Wrapped observation: exact-type only. A halt carrier here is a misroute, not a cost observation;
    # the exact-type check rejects it as a construction error without coercion/introspection.
    if cost_observation is None:
        raise ObservableCostValidityConstructionError(
            "required field 'cost_observation' must not be None"
        )
    if type(cost_observation) is not ObservableCostObservation:
        raise ObservableCostValidityConstructionError(
            "field 'cost_observation' must be an exact ObservableCostObservation, not "
            + type(cost_observation).__name__
        )

    provided_strs = {
        "valid_from_epoch_ms": valid_from_epoch_ms,
        "valid_until_epoch_ms": valid_until_epoch_ms,
        "validity_source_contract": validity_source_contract,
        "validity_source_artifact": validity_source_artifact,
        "validity_source_field": validity_source_field,
        "validity_assertion_type": validity_assertion_type,
        "boundary_version": boundary_version,
    }
    for name, value in provided_strs.items():
        if value is None:
            raise ObservableCostValidityConstructionError(
                "required field {!r} must not be None".format(name)
            )
        # Exact-type check (not isinstance): str subclasses, bool/int/float/Decimal, containers, and
        # arbitrary objects are all rejected. Never call str/repr/eq on the value.
        if type(value) is not str:
            raise ObservableCostValidityConstructionError(
                "field {!r} must be a str, not {}".format(name, type(value).__name__)
            )
        if value.strip() == "":
            raise ObservableCostValidityConstructionError(
                "field {!r} must be a non-empty, non-whitespace string".format(name)
            )

    # Exact integer strings only — no sign, no decimal point, no exponent. No int/float coercion, no
    # comparison of bounds (a reversed or equal interval is accepted; comparison is gate behavior).
    for name in _INTEGER_STRING_FIELDS:
        if _EXACT_INTEGER.fullmatch(provided_strs[name]) is None:
            raise ObservableCostValidityConstructionError(
                "field {!r} must be an exact integer string".format(name)
            )

    context = object.__new__(ObservableCostValidityContext)
    object.__setattr__(context, "cost_observation", cost_observation)
    for name, value in provided_strs.items():
        object.__setattr__(context, name, value)
    return context


def reject_misrouted_halt_carrier(payload):
    """Fail closed if a halt carrier is misrouted into the pre-net-edge calculation-input boundary.

    - Exact :class:`BlockedPacket` or exact :class:`NoEligibleHaltPacket` → raise
      :class:`MisroutedHaltCarrierError` (a routing/integration bug, not a validity context).
    - Anything else → return ``None`` (a non-halt no-op); subclasses are NOT exact halt carriers.

    Exact-type checks only (no isinstance). The offending object is never routed, passed through,
    converted, unwrapped, serialized, or reinterpreted, and is never coerced (bool/len/int/float/str/
    bytes), repr'd, equality-compared, or introspected — only its type name is used in the message.
    """
    if type(payload) is BlockedPacket:
        raise MisroutedHaltCarrierError(
            "pre-net-edge calculation-input boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    if type(payload) is NoEligibleHaltPacket:
        raise MisroutedHaltCarrierError(
            "pre-net-edge calculation-input boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    return None


class PreNetEdgeCalculationInputTruthinessError(TypeError):
    """Raised when a PreNetEdgeCalculationInput is used in a truthiness/length context."""


class PreNetEdgeCalculationInputCoercionError(TypeError):
    """Raised when a PreNetEdgeCalculationInput is coerced to a number, string, or bytes."""


class PreNetEdgeCalculationInputConstructionError(TypeError):
    """Raised when a PreNetEdgeCalculationInput is constructed with a rejected/missing value."""


class PreNetEdgeCalculationInputTypeError(TypeError):
    """Raised when an operation receives anything other than an exact PreNetEdgeCalculationInput."""


@dataclass(frozen=True, repr=False, init=False)
class PreNetEdgeCalculationInput:
    """A frozen, anti-coercion carrier bundling one gross-edge observation with declared cost-validity
    contexts, for a future, separately authorized net-edge gate/calculator path.

    Construct only through :func:`make_pre_net_edge_calculation_input`. Direct/positional construction
    is not supported. This carrier performs NO cross-object validation: it does not compare the gross
    observed time to any cost validity interval, does not compare ``valid_from``/``valid_until``, does
    not compare units/instruments/venues/size/depth across objects, and computes no
    freshness/valid_until/aggregate-cost/net_edge. It only carries an exact :class:`GrossEdgeObservation`
    and a preserved, non-empty exact tuple of exact :class:`ObservableCostValidityContext` items.
    """

    gross_observation: object
    cost_validity_contexts: object
    boundary_version: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise PreNetEdgeCalculationInputTruthinessError(
            "PreNetEdgeCalculationInput must not be evaluated for truthiness; inspect fields instead."
        )

    def __len__(self):
        raise PreNetEdgeCalculationInputTruthinessError(
            "PreNetEdgeCalculationInput has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise PreNetEdgeCalculationInputCoercionError(
            "PreNetEdgeCalculationInput must not be coerced to int."
        )

    def __float__(self):
        raise PreNetEdgeCalculationInputCoercionError(
            "PreNetEdgeCalculationInput must not be coerced to float."
        )

    def __complex__(self):
        raise PreNetEdgeCalculationInputCoercionError(
            "PreNetEdgeCalculationInput must not be coerced to complex."
        )

    def __index__(self):
        raise PreNetEdgeCalculationInputCoercionError(
            "PreNetEdgeCalculationInput must not be coerced to an index."
        )

    def __str__(self):
        raise PreNetEdgeCalculationInputCoercionError(
            "PreNetEdgeCalculationInput must not be coerced to str."
        )

    def __bytes__(self):
        raise PreNetEdgeCalculationInputCoercionError(
            "PreNetEdgeCalculationInput must not be coerced to bytes."
        )

    # --- safe debug repr only (no gross/cost values, timestamps, provenance, units, venues, or
    #     wrapped carriers; no freshness/validity/net-edge/economic meaning) ---
    def __repr__(self):
        return "PreNetEdgeCalculationInput(boundary_version={!r})".format(self.boundary_version)


def make_pre_net_edge_calculation_input(
    *,
    gross_observation,
    cost_validity_contexts,
    boundary_version,
):
    """Keyword-only constructor for a single :class:`PreNetEdgeCalculationInput`.

    ``gross_observation`` must be an exact :class:`GrossEdgeObservation` (``type(...) is ...`` — no
    isinstance, so subclasses, halt carriers, dicts/Mappings, duck-typed records, and arbitrary
    objects are rejected without reading attributes/coercing/repr'ing them). ``cost_validity_contexts``
    must be an exact, non-empty ``tuple`` (lists/sets/dicts/frozensets/Mappings/generators/iterators
    are rejected); the exact tuple object is preserved verbatim — order intact, never copied to a
    list, sorted, deduplicated, filtered, or aggregated — and every item must be an exact
    :class:`ObservableCostValidityContext`. ``boundary_version`` must be an exact, non-empty,
    non-whitespace ``str``. No cross-object comparison and no freshness/valid_until/aggregate/net_edge
    computation are performed (tuple traversal is for exact item-type checks only). Error messages use
    only field names and ``type(value).__name__`` — never ``str(value)`` or ``repr(value)``.
    """
    # Gross observation: exact-type only. A halt carrier here is a misroute, not a gross observation;
    # the exact-type check rejects it as a construction error without coercion/introspection.
    if gross_observation is None:
        raise PreNetEdgeCalculationInputConstructionError(
            "required field 'gross_observation' must not be None"
        )
    if type(gross_observation) is not GrossEdgeObservation:
        raise PreNetEdgeCalculationInputConstructionError(
            "field 'gross_observation' must be an exact GrossEdgeObservation, not "
            + type(gross_observation).__name__
        )

    # Container: exact tuple only (no isinstance) — lists/sets/dicts/frozensets/Mappings/generators/
    # iterators and arbitrary collections are rejected without iterating or coercing them.
    if cost_validity_contexts is None:
        raise PreNetEdgeCalculationInputConstructionError(
            "required field 'cost_validity_contexts' must not be None"
        )
    if type(cost_validity_contexts) is not tuple:
        raise PreNetEdgeCalculationInputConstructionError(
            "field 'cost_validity_contexts' must be a tuple, not "
            + type(cost_validity_contexts).__name__
        )
    if len(cost_validity_contexts) == 0:
        raise PreNetEdgeCalculationInputConstructionError(
            "field 'cost_validity_contexts' must be a non-empty tuple"
        )
    # Traverse only for exact item-type checks; never coerce/repr/compare item contents and never
    # sort/dedup/filter/aggregate. The tuple object itself is preserved verbatim below.
    for item in cost_validity_contexts:
        if type(item) is not ObservableCostValidityContext:
            raise PreNetEdgeCalculationInputConstructionError(
                "every item of 'cost_validity_contexts' must be an exact "
                "ObservableCostValidityContext, not " + type(item).__name__
            )

    if boundary_version is None:
        raise PreNetEdgeCalculationInputConstructionError(
            "required field 'boundary_version' must not be None"
        )
    if type(boundary_version) is not str:
        raise PreNetEdgeCalculationInputConstructionError(
            "field 'boundary_version' must be a str, not " + type(boundary_version).__name__
        )
    if boundary_version.strip() == "":
        raise PreNetEdgeCalculationInputConstructionError(
            "field 'boundary_version' must be a non-empty, non-whitespace string"
        )

    calc_input = object.__new__(PreNetEdgeCalculationInput)
    object.__setattr__(calc_input, "gross_observation", gross_observation)
    object.__setattr__(calc_input, "cost_validity_contexts", cost_validity_contexts)
    object.__setattr__(calc_input, "boundary_version", boundary_version)
    return calc_input
