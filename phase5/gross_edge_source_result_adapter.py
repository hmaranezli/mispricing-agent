"""phase5/gross_edge_source_result_adapter.py — typed source-result carrier + typed-to-typed adapter
slice for the `phase5_gross_edge_source_result_adapter` component.

This implements ONLY:

- a frozen, scalar-only `GrossEdgeSourceResult` carrier with the same 24 fields and the same
  construction discipline as `GrossEdgeObservation` (exact non-empty `str` fields; canonical exact
  decimal `gross_edge_value` (negative allowed) and `observed_size` (non-negative); exact integer
  `observed_at_epoch_ms`/`staleness_threshold_ms`; fixed `edge_direction`/`venue_scope` sets with
  buy/sell venue rules and sentinel rejection); and
- `adapt_gross_edge_source_result_to_observation(result)`, which maps exactly one source result 1:1
  into exactly one `GrossEdgeObservation` via the observation factory.

Per the component planning artifact
(`phase5_gross_edge_source_result_adapter_implementation_planning.md`): it is NOT a raw/JSON/exchange
parser, loader, endpoint reader, order-book/venue/sizing model, aggregator, or calculator, and
performs no IO/network/env/datetime/random/subprocess. The adapter accepts only the exact source-result
type (no isinstance; subclasses rejected), rejects exact halt carriers as a misroute (reusing the
observation boundary's guard), never reads attributes/coerces/repr's a wrong-typed object, maps every
field 1:1 with explicit keyword arguments (no hardcoding, no inference, no normalization, no timestamp
substitution, no freshness computation), delegates all value validation to the observation factory
without weakening it, and never silently returns ``None``. It asserts no market truth, price/liquidity
correctness, source truth, profitability, readiness, or tradeability, and authorizes no calculator/
net-edge work.
"""
import re

from dataclasses import dataclass

from phase5.gross_edge_observation_boundary import (
    GrossEdgeObservation,
    make_gross_edge_observation,
    reject_misrouted_halt_carrier,
    GROSS_EDGE_VENUE_SCOPE_SINGLE,
    GROSS_EDGE_VENUE_SCOPE_CROSS,
)

BOUNDARY_VERSION = "phase5.gross_edge_source_result_adapter.v0"

# Canonical exact decimal string and exact unsigned integer string (mirrors the observation factory).
_CANONICAL_DECIMAL = re.compile(r"-?\d+(\.\d+)?")
_EXACT_INTEGER = re.compile(r"\d+")

_ALLOWED_VENUE_SCOPES = frozenset({GROSS_EDGE_VENUE_SCOPE_SINGLE, GROSS_EDGE_VENUE_SCOPE_CROSS})
_ALLOWED_DIRECTIONS = frozenset({"LONG", "SHORT", "CROSS_VENUE"})
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


class GrossEdgeSourceResultConstructionError(TypeError):
    """Raised when a GrossEdgeSourceResult is constructed with a rejected/missing field value."""


class GrossEdgeSourceResultTypeError(TypeError):
    """Raised when the adapter receives anything other than an exact GrossEdgeSourceResult."""


class GrossEdgeSourceResultStateError(ValueError):
    """Raised when a GrossEdgeSourceResult carries an unusable state for adaptation."""


@dataclass(frozen=True, repr=False, init=False)
class GrossEdgeSourceResult:
    """A frozen, scalar-only typed source-result carrying one observed gross-edge fact.

    Construct only through :func:`make_gross_edge_source_result`. Direct/positional construction is not
    supported. Its fields mirror :class:`GrossEdgeObservation` exactly so the adapter can map them 1:1
    without inference or transformation.
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

    # --- safe debug repr only (no value/size/timestamp/provenance; no economic/readiness meaning) ---
    def __repr__(self):
        return (
            "GrossEdgeSourceResult(component_name={!r}, status={!r}, edge_direction={!r}, "
            "base_asset={!r}, quote_asset={!r}, instrument_id={!r}, venue_scope={!r})".format(
                self.component_name, self.status, self.edge_direction, self.base_asset,
                self.quote_asset, self.instrument_id, self.venue_scope
            )
        )


def make_gross_edge_source_result(
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
    """Keyword-only constructor for a single :class:`GrossEdgeSourceResult`.

    Mirrors the observation factory discipline exactly so a valid source result maps 1:1 to a valid
    observation: every field is an exact, non-empty, non-whitespace ``str``; ``gross_edge_value`` and
    ``observed_size`` are canonical exact decimal strings (``observed_size`` non-negative); the time
    and staleness fields are exact integer strings; ``edge_direction`` and ``venue_scope`` are fixed
    label sets with explicit buy/sell venue relationships and sentinel rejection. Error messages use
    only field names and ``type(value).__name__``.
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
            raise GrossEdgeSourceResultConstructionError(
                "required field {!r} must not be None".format(name)
            )
        if type(value) is not str:
            raise GrossEdgeSourceResultConstructionError(
                "field {!r} must be a str, not {}".format(name, type(value).__name__)
            )
        if value.strip() == "":
            raise GrossEdgeSourceResultConstructionError(
                "field {!r} must be a non-empty, non-whitespace string".format(name)
            )

    for name in _DECIMAL_FIELDS:
        if _CANONICAL_DECIMAL.fullmatch(provided[name]) is None:
            raise GrossEdgeSourceResultConstructionError(
                "field {!r} must be a canonical exact decimal string".format(name)
            )
    if observed_size.startswith("-"):
        raise GrossEdgeSourceResultConstructionError("field 'observed_size' must not be negative")

    for name in _INTEGER_FIELDS:
        if _EXACT_INTEGER.fullmatch(provided[name]) is None:
            raise GrossEdgeSourceResultConstructionError(
                "field {!r} must be an exact unsigned integer string".format(name)
            )

    if edge_direction not in _ALLOWED_DIRECTIONS:
        raise GrossEdgeSourceResultConstructionError(
            "field 'edge_direction' must be one of the allowed direction labels"
        )

    if venue_scope not in _ALLOWED_VENUE_SCOPES:
        raise GrossEdgeSourceResultConstructionError(
            "field 'venue_scope' must be SINGLE_VENUE or CROSS_VENUE"
        )
    if venue_buy.upper() in _FORBIDDEN_VENUE_TOKENS or venue_sell.upper() in _FORBIDDEN_VENUE_TOKENS:
        raise GrossEdgeSourceResultConstructionError(
            "venue_buy/venue_sell must be explicit venues, not a sentinel/placeholder"
        )
    if venue_scope == GROSS_EDGE_VENUE_SCOPE_SINGLE and venue_buy != venue_sell:
        raise GrossEdgeSourceResultConstructionError(
            "SINGLE_VENUE requires venue_buy to equal venue_sell"
        )
    if venue_scope == GROSS_EDGE_VENUE_SCOPE_CROSS and venue_buy == venue_sell:
        raise GrossEdgeSourceResultConstructionError(
            "CROSS_VENUE requires distinct venue_buy and venue_sell"
        )

    result = object.__new__(GrossEdgeSourceResult)
    for name, value in provided.items():
        object.__setattr__(result, name, value)
    return result


def adapt_gross_edge_source_result_to_observation(result):
    """Map exactly one :class:`GrossEdgeSourceResult` into one :class:`GrossEdgeObservation`.

    - Exact halt carriers (``BlockedPacket`` / ``NoEligibleHaltPacket``) are rejected as a misroute
      via the observation boundary's guard (``MisroutedHaltCarrierError``); halt carriers are never
      converted into gross-edge observations and ``route_halt_carrier`` is not duplicated.
    - Only an exact ``GrossEdgeSourceResult`` is accepted (``type(result) is ...``; no isinstance, so
      subclasses are rejected). Any other input raises :class:`GrossEdgeSourceResultTypeError` using
      only ``type(result).__name__`` — no attribute access, no ``str``/``repr``, no duck typing.
    - Every field is mapped 1:1 with explicit keyword arguments; nothing is hardcoded, inferred,
      normalized, timestamp-substituted, or freshness-computed. All value validation is delegated to
      ``make_gross_edge_observation`` and its exceptions are never caught or downgraded. The function
      never silently returns ``None``.
    """
    # Misroute guard first: raises MisroutedHaltCarrierError for an exact halt carrier, else no-op.
    reject_misrouted_halt_carrier(result)

    # Exact-type only — a subclass could carry hidden state or override behavior. No attribute read,
    # no str/repr of the offending object; only its type name appears in the message.
    if type(result) is not GrossEdgeSourceResult:
        raise GrossEdgeSourceResultTypeError(
            "adapter requires an exact GrossEdgeSourceResult, not " + type(result).__name__
        )

    # Defensive state guard (construction already guarantees an exact non-empty str status); never
    # silently return None or fall through.
    if type(result.status) is not str:
        raise GrossEdgeSourceResultStateError(
            "GrossEdgeSourceResult.status must be a str for adaptation"
        )

    return make_gross_edge_observation(
        component_name=result.component_name,
        origin_component=result.origin_component,
        origin_result_status=result.origin_result_status,
        status=result.status,
        edge_direction=result.edge_direction,
        base_asset=result.base_asset,
        quote_asset=result.quote_asset,
        instrument_id=result.instrument_id,
        venue_scope=result.venue_scope,
        venue_buy=result.venue_buy,
        venue_sell=result.venue_sell,
        observed_at_epoch_ms=result.observed_at_epoch_ms,
        staleness_threshold_ms=result.staleness_threshold_ms,
        gross_edge_value=result.gross_edge_value,
        gross_edge_unit=result.gross_edge_unit,
        gross_edge_source_contract=result.gross_edge_source_contract,
        gross_edge_source_artifact=result.gross_edge_source_artifact,
        gross_edge_source_field=result.gross_edge_source_field,
        observed_size=result.observed_size,
        size_unit=result.size_unit,
        depth_source_contract=result.depth_source_contract,
        depth_source_artifact=result.depth_source_artifact,
        depth_source_field=result.depth_source_field,
        boundary_version=result.boundary_version,
    )
