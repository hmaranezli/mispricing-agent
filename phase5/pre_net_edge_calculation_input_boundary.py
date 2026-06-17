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
from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
)
from phase5.const import (
    PLANNING_GATE_CONTRACT_VIOLATION,
    PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
    BLOCKED_NEEDS_EVIDENCE,
    NEXT_ACTION_HALT,
    NEXT_ACTION_OBTAIN_EVIDENCE,
)

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


# ---------------------------------------------------------------------------
# PreNetEdgeCalculationInputGate V1 / net_edge_input_preflight
#
# A pure, offline, deterministic cross-object preflight over exactly one
# PreNetEdgeCalculationInput. It is NOT a carrier, calculator, parser, adapter, cost aggregator, unit
# converter, FX/oracle, or trading/reporting component. It performs no IO/network/env/time/datetime/
# random/subprocess and no economic/cost/net-edge arithmetic. The only arithmetic is local integer
# timestamp comparison plus the single addition gross_observed + gross_staleness, on ints parsed via
# int() only after exact ^\d+$ validation; carrier fields are never mutated/re-emitted. Outputs are
# exactly: input identity (pass), an existing BlockedPacket, or an existing NoEligibleHaltPacket —
# no new wrapper / union / shared base / polymorphic halt hierarchy.
# ---------------------------------------------------------------------------

PRE_NET_EDGE_GATE_COMPONENT_NAME = "phase5_pre_net_edge_calculation_input_gate"
PRE_NET_EDGE_GATE_BOUNDARY_VERSION = "phase5.pre_net_edge_calculation_input_gate.v0"
PRE_NET_EDGE_GATE_SOURCE_CONTRACT = "phase5_pre_net_edge_calculation_input_gate_implementation_planning.md"
PRE_NET_EDGE_GATE_SOURCE_ARTIFACT = "docs/handoff/phase5_pre_net_edge_calculation_input_gate_implementation_planning.md"

# Exact reason vocabulary — character-for-character; no shorter aliases.
PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_TIME_CAUSALITY = "PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_TIME_CAUSALITY"
PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_INVALID_COST_INTERVAL = "PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_INVALID_COST_INTERVAL"
PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_GROSS_TIME = "PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_GROSS_TIME"
PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_EVALUATION_TIME = "PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_EVALUATION_TIME"
PRE_NET_EDGE_GATE_BLOCKED_UNSUPPORTED_UNIT_COMPATIBILITY = "PRE_NET_EDGE_GATE_BLOCKED_UNSUPPORTED_UNIT_COMPATIBILITY"
PRE_NET_EDGE_GATE_NO_ELIGIBLE_GROSS_SNAPSHOT_STALE = "PRE_NET_EDGE_GATE_NO_ELIGIBLE_GROSS_SNAPSHOT_STALE"

# No-eligible packet literals (gross-snapshot staleness is the only V1 no-eligible market fact).
_NO_ELIGIBLE_STATUS = "NO_ELIGIBLE"
_NO_ELIGIBLE_NEXT_ACTION = "HALT_BYPASS_NO_ELIGIBLE"

# Exact, case-sensitive proportional cost-unit vocabulary admissible without conversion.
_PRE_NET_EDGE_GATE_PROPORTIONAL_UNITS = frozenset(
    {"BPS", "BASIS_POINTS", "RATE", "PERCENT", "PERCENTAGE"}
)


class PreNetEdgeCalculationInputGateTypeError(TypeError):
    """Raised for a programmatic wrong-path / wrong-type input to the pre-net-edge gate."""


def _gate_parse_epoch_int(value, field_name):
    """Parse an exact integer string into a local int, ONLY after exact ^\\d+$ validation.

    No int() is ever called before validation; values that are not exact integer strings are a
    programmatic/corrupted-carrier-state condition and raise the gate type error using only the field
    name and ``type(value).__name__`` (never ``str(value)``/``repr(value)``).
    """
    if type(value) is not str or _EXACT_INTEGER.fullmatch(value) is None:
        raise PreNetEdgeCalculationInputGateTypeError(
            "field {!r} must be an exact integer string, not {}".format(
                field_name, type(value).__name__
            )
        )
    return int(value)


def _gate_blocked(*, status, blocked_status, reason_code, missing_or_invalid_field,
                  deterministic_next_action, may_retry_after_evidence):
    """Build a gate BlockedPacket via the existing factory — no new packet class, no wrapper."""
    return make_blocked_packet(
        component_name=PRE_NET_EDGE_GATE_COMPONENT_NAME,
        origin_component=PRE_NET_EDGE_GATE_COMPONENT_NAME,
        origin_result_status=status,
        status=status,
        blocked_status=blocked_status,
        reason_code=reason_code,
        missing_or_invalid_field=missing_or_invalid_field,
        source_contract=PRE_NET_EDGE_GATE_SOURCE_CONTRACT,
        source_artifact=PRE_NET_EDGE_GATE_SOURCE_ARTIFACT,
        source_field=reason_code,
        deterministic_next_action=deterministic_next_action,
        human_review_required=True,
        may_retry_after_evidence=may_retry_after_evidence,
        created_from_contract=PRE_NET_EDGE_GATE_SOURCE_CONTRACT,
        boundary_version=PRE_NET_EDGE_GATE_BOUNDARY_VERSION,
    )


def _gate_no_eligible():
    """Build the gate NoEligibleHaltPacket via the existing factory — gross-snapshot staleness only."""
    return make_no_eligible_halt_packet(
        component_name=PRE_NET_EDGE_GATE_COMPONENT_NAME,
        origin_component=PRE_NET_EDGE_GATE_COMPONENT_NAME,
        origin_result_status=_NO_ELIGIBLE_STATUS,
        status=_NO_ELIGIBLE_STATUS,
        no_eligible_reason=PRE_NET_EDGE_GATE_NO_ELIGIBLE_GROSS_SNAPSHOT_STALE,
        source_contract=PRE_NET_EDGE_GATE_SOURCE_CONTRACT,
        source_artifact=PRE_NET_EDGE_GATE_SOURCE_ARTIFACT,
        source_field=PRE_NET_EDGE_GATE_NO_ELIGIBLE_GROSS_SNAPSHOT_STALE,
        deterministic_next_action=_NO_ELIGIBLE_NEXT_ACTION,
        boundary_version=PRE_NET_EDGE_GATE_BOUNDARY_VERSION,
    )


def net_edge_input_preflight(*, calculation_input, evaluation_epoch_ms):
    """Pure cross-object preflight over exactly one :class:`PreNetEdgeCalculationInput`.

    Returns the identical ``calculation_input`` object on pass; an existing :class:`BlockedPacket` for
    a contract/data contradiction or an evidence/applicability failure; or an existing
    :class:`NoEligibleHaltPacket` only for gross-snapshot staleness. Programmatic wrong-path / wrong-
    type inputs raise :class:`PreNetEdgeCalculationInputGateTypeError` or
    :class:`MisroutedHaltCarrierError` and never produce a packet. See the planning artifact
    ``phase5_pre_net_edge_calculation_input_gate_implementation_planning.md`` for the pinned contract.
    """
    # --- A. Programmatic wrong-path / wrong-type (before any semantic gate result) ---
    # Exact halt carriers at this boundary are a misroute (routing/integration bug), not inputs.
    reject_misrouted_halt_carrier(calculation_input)
    reject_misrouted_halt_carrier(evaluation_epoch_ms)

    # Exact-type only (no isinstance); a wrong/subclass/duck-typed/hostile input is rejected without
    # attribute access, coercion, or repr — only its type name is used in the message.
    if type(calculation_input) is not PreNetEdgeCalculationInput:
        raise PreNetEdgeCalculationInputGateTypeError(
            "net_edge_input_preflight requires an exact PreNetEdgeCalculationInput, not "
            + type(calculation_input).__name__
        )

    # evaluation_epoch_ms must be an explicit exact integer string — no clock/default fallback.
    if evaluation_epoch_ms is None:
        raise PreNetEdgeCalculationInputGateTypeError(
            "required field 'evaluation_epoch_ms' must not be None"
        )
    if type(evaluation_epoch_ms) is not str:
        raise PreNetEdgeCalculationInputGateTypeError(
            "field 'evaluation_epoch_ms' must be a str, not " + type(evaluation_epoch_ms).__name__
        )
    if evaluation_epoch_ms.strip() == "":
        raise PreNetEdgeCalculationInputGateTypeError(
            "field 'evaluation_epoch_ms' must be a non-empty, non-whitespace string"
        )
    if _EXACT_INTEGER.fullmatch(evaluation_epoch_ms) is None:
        raise PreNetEdgeCalculationInputGateTypeError(
            "field 'evaluation_epoch_ms' must be an exact integer string"
        )

    gross = calculation_input.gross_observation
    contexts = calculation_input.cost_validity_contexts

    # Local integer temporaries only — int() strictly after ^\d+$ validation; carrier fields untouched.
    gross_observed = _gate_parse_epoch_int(gross.observed_at_epoch_ms, "observed_at_epoch_ms")
    gross_staleness = _gate_parse_epoch_int(gross.staleness_threshold_ms, "staleness_threshold_ms")
    evaluation_time = int(evaluation_epoch_ms)

    # --- B. Causal time contradiction (contract violation) ---
    if evaluation_time < gross_observed:
        return _gate_blocked(
            status=PLANNING_GATE_CONTRACT_VIOLATION,
            blocked_status=None,
            reason_code=PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_TIME_CAUSALITY,
            missing_or_invalid_field="evaluation_epoch_ms",
            deterministic_next_action=NEXT_ACTION_HALT,
            may_retry_after_evidence=False,
        )

    # --- C. Invalid cost interval (contract violation), tuple order ---
    for context in contexts:
        cost_from = _gate_parse_epoch_int(context.valid_from_epoch_ms, "valid_from_epoch_ms")
        cost_until = _gate_parse_epoch_int(context.valid_until_epoch_ms, "valid_until_epoch_ms")
        if cost_from > cost_until:
            return _gate_blocked(
                status=PLANNING_GATE_CONTRACT_VIOLATION,
                blocked_status=None,
                reason_code=PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_INVALID_COST_INTERVAL,
                missing_or_invalid_field="cost_validity_interval",
                deterministic_next_action=NEXT_ACTION_HALT,
                may_retry_after_evidence=False,
            )

    # --- D. Cost validity does not cover gross observed time (needs evidence), tuple order ---
    for context in contexts:
        cost_from = _gate_parse_epoch_int(context.valid_from_epoch_ms, "valid_from_epoch_ms")
        cost_until = _gate_parse_epoch_int(context.valid_until_epoch_ms, "valid_until_epoch_ms")
        if not (cost_from <= gross_observed <= cost_until):
            return _gate_blocked(
                status=PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
                blocked_status=BLOCKED_NEEDS_EVIDENCE,
                reason_code=PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_GROSS_TIME,
                missing_or_invalid_field="cost_validity_interval_for_gross_observed_time",
                deterministic_next_action=NEXT_ACTION_OBTAIN_EVIDENCE,
                may_retry_after_evidence=True,
            )

    # --- E. Cost validity does not cover evaluation time (needs evidence), tuple order ---
    for context in contexts:
        cost_from = _gate_parse_epoch_int(context.valid_from_epoch_ms, "valid_from_epoch_ms")
        cost_until = _gate_parse_epoch_int(context.valid_until_epoch_ms, "valid_until_epoch_ms")
        if not (cost_from <= evaluation_time <= cost_until):
            return _gate_blocked(
                status=PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
                blocked_status=BLOCKED_NEEDS_EVIDENCE,
                reason_code=PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_EVALUATION_TIME,
                missing_or_invalid_field="cost_validity_interval_for_evaluation_time",
                deterministic_next_action=NEXT_ACTION_OBTAIN_EVIDENCE,
                may_retry_after_evidence=True,
            )

    # --- F. Unsupported unit compatibility (needs evidence), tuple order ---
    # Case-sensitive exact checks only: exact match, or exact-uppercase proportional vocabulary.
    gross_unit = gross.gross_edge_unit
    for context in contexts:
        cost_unit = context.cost_observation.unit
        if cost_unit != gross_unit and cost_unit not in _PRE_NET_EDGE_GATE_PROPORTIONAL_UNITS:
            return _gate_blocked(
                status=PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
                blocked_status=BLOCKED_NEEDS_EVIDENCE,
                reason_code=PRE_NET_EDGE_GATE_BLOCKED_UNSUPPORTED_UNIT_COMPATIBILITY,
                missing_or_invalid_field="cost_observation.unit",
                deterministic_next_action=NEXT_ACTION_OBTAIN_EVIDENCE,
                may_retry_after_evidence=True,
            )

    # --- G. Gross snapshot stale (the only V1 no-eligible market fact) ---
    if evaluation_time > gross_observed + gross_staleness:
        return _gate_no_eligible()

    # --- H. Pass: return the identical input object by identity (no copy/wrap/enrich/mutate) ---
    return calculation_input


class PreNetEdgeCalculationInputGate:
    """Stateless, non-carrier namespace for the pre-net-edge calculation-input preflight gate.

    It carries no market state and requires no construction for normal use; the runtime entrypoint is
    the pure function :func:`net_edge_input_preflight`, exposed here as a static method.
    """

    __slots__ = ()

    preflight = staticmethod(net_edge_input_preflight)
