"""phase5/gross_edge_observation_boundary.py — atomic observed gross-edge carrier slice for the
`phase5_gross_edge_observation_boundary` component.

This implements ONLY the atomic `GrossEdgeObservation` — a frozen, scalar-only, anti-truthiness,
anti-coercion carrier of exactly ONE explicitly observed gross-edge fact — plus a misrouted
halt-carrier guard. Per the component planning artifact
(`phase5_gross_edge_observation_boundary_implementation_planning.md`):

- it is an observation carrier, NOT a decision carrier; not actionable; not a calculator input
  implementation; not a raw/exchange parser, loader, endpoint reader, order-book/venue/sizing/risk/
  execution model, trading, or reporting component, and performs no IO/network/env/datetime/random/
  subprocess;
- it carries one atomic observed gross-edge fact only and exposes no aggregate/economic/decision
  field (no net_edge/total_cost/profit/readiness/eligibility/order_size/allocation/valid_until);
- every field is an exact, non-empty `str`; `gross_edge_value` and `observed_size` are canonical exact
  decimal strings (no float parsing, no binary-float arithmetic, no rounding/normalization);
  `observed_at_epoch_ms` and `staleness_threshold_ms` are exact integer strings (no freshness/
  valid_until computation here); `venue_scope` is a fixed enum with explicit buy/sell relationships;
- gross edge is pre-friction and pre-net-edge: a positive gross edge does not imply positive net edge,
  and an observed size is a depth/liquidity fact only — not trade size, allocation, or readiness.

It asserts no market truth, price/liquidity correctness, source truth, profitability, readiness, or
tradeability, and authorizes no calculator/net-edge work.
"""
import re

from dataclasses import dataclass

from phase5.blocked_result_boundary import BlockedPacket
from phase5.no_eligible_halt_propagation_boundary import NoEligibleHaltPacket

# Venue scope enum (descriptive provenance labels only; not a trading authorization).
GROSS_EDGE_VENUE_SCOPE_SINGLE = "SINGLE_VENUE"
GROSS_EDGE_VENUE_SCOPE_CROSS = "CROSS_VENUE"

BOUNDARY_VERSION = "phase5.gross_edge_observation_boundary.v0"

# Canonical exact decimal string: optional leading '-', digits, optional '.' + digits.
_CANONICAL_DECIMAL = re.compile(r"-?\d+(\.\d+)?")
# Exact unsigned integer string: digits only (no sign, no point, no exponent).
_EXACT_INTEGER = re.compile(r"\d+")

_ALLOWED_VENUE_SCOPES = frozenset({GROSS_EDGE_VENUE_SCOPE_SINGLE, GROSS_EDGE_VENUE_SCOPE_CROSS})
# Descriptive direction labels only — never a trade side / order / execution authorization.
_ALLOWED_DIRECTIONS = frozenset({"LONG", "SHORT", "CROSS_VENUE"})
# Sentinel/placeholder venue values are forbidden (case-insensitive); venue identity must be explicit.
_FORBIDDEN_VENUE_TOKENS = frozenset({"NOT_APPLICABLE", "NONE", "N/A", "NULL"})

_DECIMAL_FIELDS = ("gross_edge_value", "observed_size")
_INTEGER_FIELDS = ("observed_at_epoch_ms", "staleness_threshold_ms")

_FIELD_NAMES = (
    "component_name",
    "origin_component",
    "origin_result_status",
    "status",
    "edge_direction",
    "base_asset",
    "quote_asset",
    "instrument_id",
    "venue_scope",
    "venue_buy",
    "venue_sell",
    "observed_at_epoch_ms",
    "staleness_threshold_ms",
    "gross_edge_value",
    "gross_edge_unit",
    "gross_edge_source_contract",
    "gross_edge_source_artifact",
    "gross_edge_source_field",
    "observed_size",
    "size_unit",
    "depth_source_contract",
    "depth_source_artifact",
    "depth_source_field",
    "boundary_version",
)


class GrossEdgeTruthinessError(TypeError):
    """Raised when a GrossEdgeObservation is used in a truthiness/length context."""


class GrossEdgeCoercionError(TypeError):
    """Raised when a GrossEdgeObservation is coerced to a number, string, or bytes."""


class GrossEdgeConstructionError(TypeError):
    """Raised when a GrossEdgeObservation is constructed with a rejected/missing field value."""


class GrossEdgeVenueScopeError(TypeError):
    """Raised when venue scope / buy / sell fields violate the venue-identity rules."""


class MisroutedHaltCarrierError(TypeError):
    """Raised when a halt carrier is misrouted into the gross-edge observation boundary."""


@dataclass(frozen=True, repr=False, init=False)
class GrossEdgeObservation:
    """A frozen, scalar-only, anti-coercion carrier of exactly one observed gross-edge fact.

    Construct only through :func:`make_gross_edge_observation`. Direct/positional construction is not
    supported.
    """

    component_name: object
    origin_component: object
    origin_result_status: object
    status: object
    edge_direction: object
    base_asset: object
    quote_asset: object
    instrument_id: object
    venue_scope: object
    venue_buy: object
    venue_sell: object
    observed_at_epoch_ms: object
    staleness_threshold_ms: object
    gross_edge_value: object
    gross_edge_unit: object
    gross_edge_source_contract: object
    gross_edge_source_artifact: object
    gross_edge_source_field: object
    observed_size: object
    size_unit: object
    depth_source_contract: object
    depth_source_artifact: object
    depth_source_field: object
    boundary_version: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise GrossEdgeTruthinessError(
            "GrossEdgeObservation must not be evaluated for truthiness; inspect fields instead."
        )

    def __len__(self):
        raise GrossEdgeTruthinessError(
            "GrossEdgeObservation has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise GrossEdgeCoercionError("GrossEdgeObservation must not be coerced to int.")

    def __float__(self):
        raise GrossEdgeCoercionError("GrossEdgeObservation must not be coerced to float.")

    def __complex__(self):
        raise GrossEdgeCoercionError("GrossEdgeObservation must not be coerced to complex.")

    def __index__(self):
        raise GrossEdgeCoercionError("GrossEdgeObservation must not be coerced to an index.")

    def __str__(self):
        raise GrossEdgeCoercionError("GrossEdgeObservation must not be coerced to str.")

    def __bytes__(self):
        raise GrossEdgeCoercionError("GrossEdgeObservation must not be coerced to bytes.")

    # --- safe debug repr only (no value/size/timestamp/provenance; no economic/readiness meaning) ---
    def __repr__(self):
        return (
            "GrossEdgeObservation(component_name={!r}, status={!r}, edge_direction={!r}, "
            "base_asset={!r}, quote_asset={!r}, instrument_id={!r}, venue_scope={!r})".format(
                self.component_name, self.status, self.edge_direction, self.base_asset,
                self.quote_asset, self.instrument_id, self.venue_scope
            )
        )


def make_gross_edge_observation(
    *,
    component_name,
    origin_component,
    origin_result_status,
    status,
    edge_direction,
    base_asset,
    quote_asset,
    instrument_id,
    venue_scope,
    venue_buy,
    venue_sell,
    observed_at_epoch_ms,
    staleness_threshold_ms,
    gross_edge_value,
    gross_edge_unit,
    gross_edge_source_contract,
    gross_edge_source_artifact,
    gross_edge_source_field,
    observed_size,
    size_unit,
    depth_source_contract,
    depth_source_artifact,
    depth_source_field,
    boundary_version,
):
    """Keyword-only constructor for a single :class:`GrossEdgeObservation`.

    Every field must be an exact, non-empty, non-whitespace ``str`` (``type(value) is str``).
    ``gross_edge_value`` and ``observed_size`` are canonical exact decimal strings preserved verbatim;
    ``observed_size`` may not be negative. ``observed_at_epoch_ms`` and ``staleness_threshold_ms`` are
    exact integer strings. ``edge_direction`` and ``venue_scope`` are fixed label sets with explicit
    buy/sell venue relationships. Error messages use only field names and ``type(value).__name__``.
    """
    provided = {
        "component_name": component_name,
        "origin_component": origin_component,
        "origin_result_status": origin_result_status,
        "status": status,
        "edge_direction": edge_direction,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "instrument_id": instrument_id,
        "venue_scope": venue_scope,
        "venue_buy": venue_buy,
        "venue_sell": venue_sell,
        "observed_at_epoch_ms": observed_at_epoch_ms,
        "staleness_threshold_ms": staleness_threshold_ms,
        "gross_edge_value": gross_edge_value,
        "gross_edge_unit": gross_edge_unit,
        "gross_edge_source_contract": gross_edge_source_contract,
        "gross_edge_source_artifact": gross_edge_source_artifact,
        "gross_edge_source_field": gross_edge_source_field,
        "observed_size": observed_size,
        "size_unit": size_unit,
        "depth_source_contract": depth_source_contract,
        "depth_source_artifact": depth_source_artifact,
        "depth_source_field": depth_source_field,
        "boundary_version": boundary_version,
    }
    for name, value in provided.items():
        if value is None:
            raise GrossEdgeConstructionError(
                "required field {!r} must not be None".format(name)
            )
        if type(value) is not str:
            raise GrossEdgeConstructionError(
                "field {!r} must be a str, not {}".format(name, type(value).__name__)
            )
        if value.strip() == "":
            raise GrossEdgeConstructionError(
                "field {!r} must be a non-empty, non-whitespace string".format(name)
            )

    # Canonical exact decimal strings — no float parsing, no normalization.
    for name in _DECIMAL_FIELDS:
        if _CANONICAL_DECIMAL.fullmatch(provided[name]) is None:
            raise GrossEdgeConstructionError(
                "field {!r} must be a canonical exact decimal string".format(name)
            )
    # Observed depth/liquidity size cannot be negative (a depth fact, never a sizing decision).
    if observed_size.startswith("-"):
        raise GrossEdgeConstructionError("field 'observed_size' must not be negative")

    # Exact unsigned integer strings for the observed time and staleness threshold.
    for name in _INTEGER_FIELDS:
        if _EXACT_INTEGER.fullmatch(provided[name]) is None:
            raise GrossEdgeConstructionError(
                "field {!r} must be an exact unsigned integer string".format(name)
            )

    # Descriptive direction label only — fixed allowed set.
    if edge_direction not in _ALLOWED_DIRECTIONS:
        raise GrossEdgeConstructionError(
            "field 'edge_direction' must be one of the allowed direction labels"
        )

    # Venue identity rules.
    if venue_scope not in _ALLOWED_VENUE_SCOPES:
        raise GrossEdgeVenueScopeError(
            "field 'venue_scope' must be SINGLE_VENUE or CROSS_VENUE"
        )
    if venue_buy.upper() in _FORBIDDEN_VENUE_TOKENS or venue_sell.upper() in _FORBIDDEN_VENUE_TOKENS:
        raise GrossEdgeVenueScopeError(
            "venue_buy/venue_sell must be explicit venues, not a sentinel/placeholder"
        )
    if venue_scope == GROSS_EDGE_VENUE_SCOPE_SINGLE and venue_buy != venue_sell:
        raise GrossEdgeVenueScopeError(
            "SINGLE_VENUE requires venue_buy to equal venue_sell"
        )
    if venue_scope == GROSS_EDGE_VENUE_SCOPE_CROSS and venue_buy == venue_sell:
        raise GrossEdgeVenueScopeError(
            "CROSS_VENUE requires distinct venue_buy and venue_sell"
        )

    packet = object.__new__(GrossEdgeObservation)
    for name, value in provided.items():
        object.__setattr__(packet, name, value)
    return packet


def reject_misrouted_halt_carrier(payload):
    """Fail closed if a halt carrier is misrouted into the gross-edge observation boundary.

    - Exact :class:`BlockedPacket` or exact :class:`NoEligibleHaltPacket` → raise
      :class:`MisroutedHaltCarrierError` (a routing/integration bug, not a gross-edge observation).
    - Anything else → return ``None`` (a non-halt no-op); subclasses are NOT exact halt carriers.

    Exact-type checks only (no isinstance). The offending object is never routed, passed through,
    converted, unwrapped, serialized, or reinterpreted, and is never coerced (bool/len/int/float/str/
    bytes), repr'd, equality-compared, or introspected — only its type name is used in the message.
    """
    if type(payload) is BlockedPacket:
        raise MisroutedHaltCarrierError(
            "gross-edge observation boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    if type(payload) is NoEligibleHaltPacket:
        raise MisroutedHaltCarrierError(
            "gross-edge observation boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    return None
