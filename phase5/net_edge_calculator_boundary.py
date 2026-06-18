"""phase5/net_edge_calculator_boundary.py — Phase 5 deterministic net-edge algebra boundary.

Implements ONLY `NetEdgeCalculationResult`, `calculate_net_edge(*, calculation_input)`, and a
stateless `NetEdgeCalculator` wrapper, per the planning artifact
(`phase5_net_edge_calculator_boundary_implementation_planning.md`). The calculator:

- consumes only an exact `PreNetEdgeCalculationInput` (already passed `net_edge_input_preflight`);
  subclasses/raw-container/duck-typed inputs are rejected with `NetEdgeCalculatorTypeError`, and exact
  halt carriers are a misroute (`MisroutedHaltCarrierError`) — never a packet;
- computes `net_edge = gross_edge - sum(cost_i)` with signed cost/rebate algebra, retaining and
  counting zero-cost components, never mutating/sorting/deduplicating/filtering the cost tuple;
- uses `Decimal` locally, constructed only from already-canonical decimal strings (no float, no
  Decimal-from-float, no binary float, no rounding/quantize), and serializes results back to canonical
  decimal strings (no exponent, no leading plus, minus preserved, zero canonicalized to "0");
- is dimensionally case-sensitive exact-token only: it computes only when gross and every cost share
  the exact same unit token (proportional vocabulary or an identical absolute token); any mismatch
  returns a `BlockedPacket` with the pinned reason vocabulary;
- never returns `NoEligibleHaltPacket`; negative/zero/positive net edge are all successful (non-
  actionable) results; it produces no profitability/readiness/actionability/order/paper-live output.
"""
import re

from dataclasses import dataclass
from decimal import Decimal, localcontext

from phase5.pre_net_edge_calculation_input_boundary import (
    PreNetEdgeCalculationInput,
    reject_misrouted_halt_carrier,
    MisroutedHaltCarrierError,
)
from phase5.blocked_result_boundary import make_blocked_packet
from phase5.const import (
    PLANNING_GATE_CONTRACT_VIOLATION,
    PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
    BLOCKED_NEEDS_EVIDENCE,
    NEXT_ACTION_HALT,
    NEXT_ACTION_OBTAIN_EVIDENCE,
)

NET_EDGE_CALCULATOR_COMPONENT_NAME = "phase5_net_edge_calculator_boundary"
NET_EDGE_CALCULATOR_BOUNDARY_VERSION = "phase5.net_edge_calculator_boundary.v0"
NET_EDGE_CALCULATOR_SOURCE_CONTRACT = "phase5_net_edge_calculator_boundary_implementation_planning.md"
NET_EDGE_CALCULATOR_SOURCE_ARTIFACT = "docs/handoff/phase5_net_edge_calculator_boundary_implementation_planning.md"
NET_EDGE_CALCULATION_METHOD = "NET_EDGE_V1_GROSS_MINUS_SUM_COSTS_SAME_UNIT"
NET_EDGE_CALCULATOR_STATUS_CALCULATED = "NET_EDGE_CALCULATED"
NET_EDGE_CALCULATOR_ORIGIN_RESULT_STATUS = "PRE_NET_EDGE_CALCULATION_INPUT_ACCEPTED"
NET_EDGE_CALCULATOR_SUCCESS_SOURCE_FIELD = "net_edge.calculated_value"

# Blocked reason vocabulary (pinned by the planning artifact; character-for-character).
NET_EDGE_CALCULATOR_BLOCKED_MISSING_NOTIONAL_FOR_PROPORTIONAL_COST = "NET_EDGE_CALCULATOR_BLOCKED_MISSING_NOTIONAL_FOR_PROPORTIONAL_COST"
NET_EDGE_CALCULATOR_BLOCKED_MISSING_CONVERSION_BASIS_FOR_ABSOLUTE_COST = "NET_EDGE_CALCULATOR_BLOCKED_MISSING_CONVERSION_BASIS_FOR_ABSOLUTE_COST"
NET_EDGE_CALCULATOR_BLOCKED_MIXED_PROPORTIONAL_UNITS = "NET_EDGE_CALCULATOR_BLOCKED_MIXED_PROPORTIONAL_UNITS"
NET_EDGE_CALCULATOR_BLOCKED_INCOMPATIBLE_ABSOLUTE_UNITS = "NET_EDGE_CALCULATOR_BLOCKED_INCOMPATIBLE_ABSOLUTE_UNITS"
NET_EDGE_CALCULATOR_BLOCKED_UNSUPPORTED_UNIT_VOCABULARY = "NET_EDGE_CALCULATOR_BLOCKED_UNSUPPORTED_UNIT_VOCABULARY"
NET_EDGE_CALCULATOR_CONTRACT_VIOLATION_MALFORMED_INPUT_STATE = "NET_EDGE_CALCULATOR_CONTRACT_VIOLATION_MALFORMED_INPUT_STATE"

# Exact, case-sensitive proportional unit vocabulary.
_PROPORTIONAL_UNITS = frozenset({"BPS", "BASIS_POINTS", "RATE", "PERCENT", "PERCENTAGE"})

# Canonical exact decimal string: optional leading '-', digits, optional '.' + digits. No exponent.
_CANONICAL_DECIMAL = re.compile(r"-?\d+(\.\d+)?")
# Exact unsigned integer string (for cost_component_count).
_EXACT_UNSIGNED_INT = re.compile(r"\d+")
# Recognized unit-vocabulary token shape (identifier-like). Not a conversion — a recognition gate.
_RECOGNIZED_UNIT_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_]*")

_RESULT_FIELDS = (
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "gross_edge_value",
    "gross_edge_unit",
    "total_cost_value",
    "total_cost_unit",
    "net_edge_value",
    "net_edge_unit",
    "cost_component_count",
    "source_contract",
    "source_artifact",
    "source_field",
    "calculation_method",
    "boundary_version",
)


class NetEdgeCalculatorTypeError(TypeError):
    """Raised for a programmatic wrong-path / wrong-type input to the net-edge calculator."""


class NetEdgeCalculationResultTruthinessError(TypeError):
    """Raised when a NetEdgeCalculationResult is used in a truthiness/length context."""


class NetEdgeCalculationResultCoercionError(TypeError):
    """Raised when a NetEdgeCalculationResult is coerced to a number, string, or bytes."""


class NetEdgeCalculationResultConstructionError(TypeError):
    """Raised when a NetEdgeCalculationResult is constructed with a rejected/missing field value."""


@dataclass(frozen=True, repr=False, init=False)
class NetEdgeCalculationResult:
    """A frozen, anti-coercion carrier of a calculated net edge — a calculated result, not an
    observation, and not actionable.

    Constructed only by the calculator/factory. It proves no profitability, no readiness, no safety,
    no source truth, and no paper/live readiness; a negative, zero, or positive ``net_edge_value`` is
    a mathematical output only.
    """

    component_name: object
    origin_component: object
    origin_result_status: object
    status: object
    gross_edge_value: object
    gross_edge_unit: object
    total_cost_value: object
    total_cost_unit: object
    net_edge_value: object
    net_edge_unit: object
    cost_component_count: object
    source_contract: object
    source_artifact: object
    source_field: object
    calculation_method: object
    boundary_version: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise NetEdgeCalculationResultTruthinessError(
            "NetEdgeCalculationResult must not be evaluated for truthiness; inspect fields instead."
        )

    def __len__(self):
        raise NetEdgeCalculationResultTruthinessError(
            "NetEdgeCalculationResult has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise NetEdgeCalculationResultCoercionError(
            "NetEdgeCalculationResult must not be coerced to int."
        )

    def __float__(self):
        raise NetEdgeCalculationResultCoercionError(
            "NetEdgeCalculationResult must not be coerced to float."
        )

    def __complex__(self):
        raise NetEdgeCalculationResultCoercionError(
            "NetEdgeCalculationResult must not be coerced to complex."
        )

    def __index__(self):
        raise NetEdgeCalculationResultCoercionError(
            "NetEdgeCalculationResult must not be coerced to an index."
        )

    def __str__(self):
        raise NetEdgeCalculationResultCoercionError(
            "NetEdgeCalculationResult must not be coerced to str."
        )

    def __bytes__(self):
        raise NetEdgeCalculationResultCoercionError(
            "NetEdgeCalculationResult must not be coerced to bytes."
        )

    # --- safe debug repr only (no economic values; no profitability/readiness/actionability meaning) ---
    def __repr__(self):
        return (
            "NetEdgeCalculationResult(component_name={!r}, status={!r}, "
            "calculation_method={!r})".format(
                self.component_name, self.status, self.calculation_method
            )
        )


def _make_net_edge_result(**fields):
    """Factory for a single :class:`NetEdgeCalculationResult`; every field must be an exact non-empty str."""
    for name in _RESULT_FIELDS:
        value = fields[name]
        if type(value) is not str:
            raise NetEdgeCalculationResultConstructionError(
                "field {!r} must be a str, not {}".format(name, type(value).__name__)
            )
        if value.strip() == "":
            raise NetEdgeCalculationResultConstructionError(
                "field {!r} must be a non-empty, non-whitespace string".format(name)
            )
    if _EXACT_UNSIGNED_INT.fullmatch(fields["cost_component_count"]) is None:
        raise NetEdgeCalculationResultConstructionError(
            "field 'cost_component_count' must be an exact unsigned integer string"
        )
    for name in ("gross_edge_value", "total_cost_value", "net_edge_value"):
        if _CANONICAL_DECIMAL.fullmatch(fields[name]) is None:
            raise NetEdgeCalculationResultConstructionError(
                "field {!r} must be a canonical decimal string".format(name)
            )
    result = object.__new__(NetEdgeCalculationResult)
    for name in _RESULT_FIELDS:
        object.__setattr__(result, name, fields[name])
    return result


def _calculator_blocked(*, status, blocked_status, reason_code, missing_or_invalid_field,
                        deterministic_next_action, may_retry_after_evidence):
    """Build a calculator BlockedPacket via the existing factory — no new packet class, no wrapper."""
    return make_blocked_packet(
        component_name=NET_EDGE_CALCULATOR_COMPONENT_NAME,
        origin_component=NET_EDGE_CALCULATOR_COMPONENT_NAME,
        origin_result_status=status,
        status=status,
        blocked_status=blocked_status,
        reason_code=reason_code,
        missing_or_invalid_field=missing_or_invalid_field,
        source_contract=NET_EDGE_CALCULATOR_SOURCE_CONTRACT,
        source_artifact=NET_EDGE_CALCULATOR_SOURCE_ARTIFACT,
        source_field=reason_code,
        deterministic_next_action=deterministic_next_action,
        human_review_required=True,
        may_retry_after_evidence=may_retry_after_evidence,
        created_from_contract=NET_EDGE_CALCULATOR_SOURCE_CONTRACT,
        boundary_version=NET_EDGE_CALCULATOR_BOUNDARY_VERSION,
    )


def _blocked_needs_evidence(*, reason_code, missing_or_invalid_field):
    return _calculator_blocked(
        status=PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
        blocked_status=BLOCKED_NEEDS_EVIDENCE,
        reason_code=reason_code,
        missing_or_invalid_field=missing_or_invalid_field,
        deterministic_next_action=NEXT_ACTION_OBTAIN_EVIDENCE,
        may_retry_after_evidence=True,
    )


def _blocked_malformed():
    return _calculator_blocked(
        status=PLANNING_GATE_CONTRACT_VIOLATION,
        blocked_status=None,
        reason_code=NET_EDGE_CALCULATOR_CONTRACT_VIOLATION_MALFORMED_INPUT_STATE,
        missing_or_invalid_field="calculation_input_carrier_state",
        deterministic_next_action=NEXT_ACTION_HALT,
        may_retry_after_evidence=False,
    )


def _is_proportional(unit):
    return unit in _PROPORTIONAL_UNITS


def _is_recognized_unit_token(unit):
    return type(unit) is str and _RECOGNIZED_UNIT_TOKEN.fullmatch(unit) is not None


def _unit_compatibility_block(gross_unit, cost_units):
    """Return a blocked reason_code if (gross_unit, cost_units) are not exact-token compatible, else None.

    V1 computes only when gross and every cost share the exact same unit token. Otherwise the reason is
    selected deterministically; no normalization, conversion, FX, oracle, or inference is performed.
    """
    all_units = [gross_unit] + list(cost_units)

    # Exact-token compatibility: every unit is the identical token (proportional or absolute).
    if all(u == gross_unit for u in cost_units):
        return None

    # Not all identical → a recognition gate first (units must be identifier-shaped vocabulary tokens).
    if not all(_is_recognized_unit_token(u) for u in all_units):
        return NET_EDGE_CALCULATOR_BLOCKED_UNSUPPORTED_UNIT_VOCABULARY

    gross_prop = _is_proportional(gross_unit)
    any_cost_prop = any(_is_proportional(u) for u in cost_units)
    all_cost_prop = all(_is_proportional(u) for u in cost_units)

    if gross_prop and all_cost_prop:
        # All proportional but not identical → mixed proportional units.
        return NET_EDGE_CALCULATOR_BLOCKED_MIXED_PROPORTIONAL_UNITS
    if not gross_prop and any_cost_prop:
        # Absolute gross with a proportional cost → needs notional/reference-price evidence.
        return NET_EDGE_CALCULATOR_BLOCKED_MISSING_NOTIONAL_FOR_PROPORTIONAL_COST
    if gross_prop and not all_cost_prop:
        # Proportional gross with an absolute cost → needs an explicit conversion basis.
        return NET_EDGE_CALCULATOR_BLOCKED_MISSING_CONVERSION_BASIS_FOR_ABSOLUTE_COST
    # Gross absolute, all costs absolute, not identical → incompatible absolute units.
    return NET_EDGE_CALCULATOR_BLOCKED_INCOMPATIBLE_ABSOLUTE_UNITS


def _to_canonical_decimal_string(dec):
    """Serialize a Decimal to a canonical decimal string: no exponent, no leading plus, minus
    preserved, and any zero canonicalized explicitly to "0"."""
    if dec.is_zero():
        return "0"
    return format(dec, "f")


def calculate_net_edge(*, calculation_input):
    """Compute net edge for exactly one :class:`PreNetEdgeCalculationInput`.

    Returns a :class:`NetEdgeCalculationResult` (negative/zero/positive, all successful) when gross and
    every cost share the exact same unit token; an existing ``BlockedPacket`` for a dimensional/evidence
    failure or a malformed carrier state discovered during calculation; and never a
    ``NoEligibleHaltPacket``. Programmatic wrong-path / wrong-type inputs raise
    :class:`NetEdgeCalculatorTypeError` or :class:`MisroutedHaltCarrierError`.
    """
    # --- Programmatic wrong-path / wrong-type first ---
    reject_misrouted_halt_carrier(calculation_input)
    if type(calculation_input) is not PreNetEdgeCalculationInput:
        raise NetEdgeCalculatorTypeError(
            "calculate_net_edge requires an exact PreNetEdgeCalculationInput, not "
            + type(calculation_input).__name__
        )

    gross = calculation_input.gross_observation
    contexts = calculation_input.cost_validity_contexts

    gross_value = gross.gross_edge_value
    gross_unit = gross.gross_edge_unit

    # --- Malformed carrier state discovered during calculation → BlockedPacket (not exception) ---
    if type(gross_value) is not str or _CANONICAL_DECIMAL.fullmatch(gross_value) is None:
        return _blocked_malformed()
    if type(gross_unit) is not str or gross_unit.strip() == "":
        return _blocked_malformed()

    cost_values = []
    cost_units = []
    for context in contexts:
        observation = context.cost_observation
        value = observation.signed_decimal_value
        unit = observation.unit
        if type(value) is not str or _CANONICAL_DECIMAL.fullmatch(value) is None:
            return _blocked_malformed()
        if type(unit) is not str or unit.strip() == "":
            return _blocked_malformed()
        cost_values.append(value)
        cost_units.append(unit)

    # --- Dimensional compatibility (exact-token only); mismatch → BlockedPacket ---
    block_reason = _unit_compatibility_block(gross_unit, cost_units)
    if block_reason is not None:
        if block_reason == NET_EDGE_CALCULATOR_BLOCKED_MISSING_NOTIONAL_FOR_PROPORTIONAL_COST:
            field = "notional_or_reference_price"
        elif block_reason == NET_EDGE_CALCULATOR_BLOCKED_MISSING_CONVERSION_BASIS_FOR_ABSOLUTE_COST:
            field = "conversion_basis"
        elif block_reason == NET_EDGE_CALCULATOR_BLOCKED_UNSUPPORTED_UNIT_VOCABULARY:
            field = "unit_vocabulary"
        else:
            field = "cost_observation.unit"
        return _blocked_needs_evidence(reason_code=block_reason, missing_or_invalid_field=field)

    # --- Algebra: net_edge = gross_edge - sum(cost_i); Decimal from canonical strings only ---
    # Compatibility guarantees every unit equals gross_unit; that token is the result unit.
    result_unit = gross_unit
    with localcontext() as ctx:
        ctx.prec = 60  # generous fixed precision; no rounding/quantize of realistic inputs
        gross_dec = Decimal(gross_value)
        total_cost_dec = Decimal("0")
        for value in cost_values:  # tuple order; accumulate only, never sort/dedup/filter
            total_cost_dec = total_cost_dec + Decimal(value)
        net_dec = gross_dec - total_cost_dec
        total_cost_str = _to_canonical_decimal_string(total_cost_dec)
        net_str = _to_canonical_decimal_string(net_dec)

    return _make_net_edge_result(
        component_name=NET_EDGE_CALCULATOR_COMPONENT_NAME,
        origin_component=NET_EDGE_CALCULATOR_COMPONENT_NAME,
        origin_result_status=NET_EDGE_CALCULATOR_ORIGIN_RESULT_STATUS,
        status=NET_EDGE_CALCULATOR_STATUS_CALCULATED,
        gross_edge_value=gross_value,
        gross_edge_unit=gross_unit,
        total_cost_value=total_cost_str,
        total_cost_unit=result_unit,
        net_edge_value=net_str,
        net_edge_unit=result_unit,
        cost_component_count=str(len(contexts)),
        source_contract=NET_EDGE_CALCULATOR_SOURCE_CONTRACT,
        source_artifact=NET_EDGE_CALCULATOR_SOURCE_ARTIFACT,
        source_field=NET_EDGE_CALCULATOR_SUCCESS_SOURCE_FIELD,
        calculation_method=NET_EDGE_CALCULATION_METHOD,
        boundary_version=NET_EDGE_CALCULATOR_BOUNDARY_VERSION,
    )


class NetEdgeCalculator:
    """Stateless, non-carrier namespace for the net-edge calculation boundary.

    Carries no state and requires no construction; the runtime entrypoint is the pure function
    :func:`calculate_net_edge`, exposed here as a static method.
    """

    __slots__ = ()

    calculate = staticmethod(calculate_net_edge)
