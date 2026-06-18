"""phase5/venue_instrument_readiness_boundary.py — Slice 1 atomic implementation of the
`phase5_venue_instrument_readiness_boundary` component: `VenueInstrumentReadinessStateContext`.

Per the component planning artifact
(`phase5_venue_instrument_readiness_implementation_planning.md`), this implements ONLY a frozen,
repr-safe, anti-truthiness, anti-coercion, factory-only carrier that wraps exactly the explicitly
supplied venue/instrument readiness-state evidence. Slice 2 (the gate and its preflight function) is
a separate, separately authorized task and is deliberately NOT implemented in this module.

This carrier is strictly a supplied venue/instrument state descriptor. It is NOT trade readiness, NOT
actionability, NOT execution safety, NOT liquidity readiness, NOT balance/margin readiness, NOT
paper-ready or live-ready, NOT order-placement proof, and NOT an order / signal / candidate. An
explicit ``VENUE_INSTRUMENT_STATE_ACTIVE`` value is a state-evidence fact only; it does not mean
trade-ready and is not interpreted semantically beyond exact vocabulary membership.

Discipline:

- every field is explicitly supplied by the caller (``component_name`` is fixed by the factory); the
  carrier derives nothing and reads nothing from any upstream object;
- every user-supplied field is an exact, non-empty, non-whitespace ``str`` (``type(value) is str`` —
  no isinstance, so str subclasses, ``None``, ``bool``, ``int``, ``float``, dicts, bytes, and
  duck-typed string-likes are rejected), preserved verbatim;
- ``readiness_status`` must additionally be an exact, case-sensitive token from the closed status
  vocabulary — it is not trimmed, normalized, broadened, aliased, or inferred;
- no parsing of provenance strings, no inference, no defaulting, no clock/time, no network, and no
  case/unit normalization;
- it evaluates no gate, compares against no envelope, performs no pass/fail decision, and constructs
  no halt carrier.
"""
from dataclasses import dataclass, fields as dataclass_fields

VENUE_INSTRUMENT_READINESS_BOUNDARY_COMPONENT_NAME = (
    "phase5_venue_instrument_readiness_boundary"
)
BOUNDARY_VERSION = "phase5.venue_instrument_readiness_boundary.v0"

# Closed, explicit, case-sensitive readiness-status vocabulary. ACTIVE is the only state the future
# gate will treat as permitting; this carrier ascribes no semantic meaning beyond exact membership.
VENUE_INSTRUMENT_STATE_ACTIVE = "VENUE_INSTRUMENT_STATE_ACTIVE"
VENUE_INSTRUMENT_STATE_SUSPENDED = "VENUE_INSTRUMENT_STATE_SUSPENDED"
VENUE_INSTRUMENT_STATE_MAINTENANCE = "VENUE_INSTRUMENT_STATE_MAINTENANCE"
VENUE_INSTRUMENT_STATE_CLOSED = "VENUE_INSTRUMENT_STATE_CLOSED"
VENUE_INSTRUMENT_STATE_UNSUPPORTED = "VENUE_INSTRUMENT_STATE_UNSUPPORTED"

_ALLOWED_READINESS_STATUSES = frozenset(
    {
        VENUE_INSTRUMENT_STATE_ACTIVE,
        VENUE_INSTRUMENT_STATE_SUSPENDED,
        VENUE_INSTRUMENT_STATE_MAINTENANCE,
        VENUE_INSTRUMENT_STATE_CLOSED,
        VENUE_INSTRUMENT_STATE_UNSUPPORTED,
    }
)

# The 10 caller-supplied string fields (component_name is fixed by the factory, not a parameter).
_USER_SUPPLIED_FIELDS = (
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "readiness_status",
    "source_contract",
    "source_artifact",
    "source_field",
    "state_id",
    "boundary_version",
)


class VenueInstrumentReadinessStateContextTruthinessError(TypeError):
    """Raised when a VenueInstrumentReadinessStateContext is used in a truthiness/length context."""


class VenueInstrumentReadinessStateContextCoercionError(TypeError):
    """Raised when a VenueInstrumentReadinessStateContext is coerced to a number, string, or bytes."""


class VenueInstrumentReadinessStateContextTypeError(TypeError):
    """Raised when the factory receives a wrong-typed field value."""


@dataclass(frozen=True, repr=False, init=False)
class VenueInstrumentReadinessStateContext:
    """A frozen, anti-coercion carrier wrapping explicitly supplied venue/instrument state evidence.

    Construct only through :func:`make_venue_instrument_readiness_state_context`. Direct/positional
    construction is not supported. The carrier asserts no trade readiness, no actionability, and no
    execution safety; it only holds the explicitly supplied venue/instrument identity, the explicit
    readiness-status token, and the provenance of that state evidence.
    """

    component_name: object
    venue: object
    instrument_id: object
    base_asset: object
    quote_asset: object
    readiness_status: object
    source_contract: object
    source_artifact: object
    source_field: object
    state_id: object
    boundary_version: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise VenueInstrumentReadinessStateContextTruthinessError(
            "VenueInstrumentReadinessStateContext must not be evaluated for truthiness; "
            "inspect fields."
        )

    def __len__(self):
        raise VenueInstrumentReadinessStateContextTruthinessError(
            "VenueInstrumentReadinessStateContext has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise VenueInstrumentReadinessStateContextCoercionError(
            "VenueInstrumentReadinessStateContext must not be coerced to int."
        )

    def __float__(self):
        raise VenueInstrumentReadinessStateContextCoercionError(
            "VenueInstrumentReadinessStateContext must not be coerced to float."
        )

    def __complex__(self):
        raise VenueInstrumentReadinessStateContextCoercionError(
            "VenueInstrumentReadinessStateContext must not be coerced to complex."
        )

    def __index__(self):
        raise VenueInstrumentReadinessStateContextCoercionError(
            "VenueInstrumentReadinessStateContext must not be coerced to an index."
        )

    def __str__(self):
        raise VenueInstrumentReadinessStateContextCoercionError(
            "VenueInstrumentReadinessStateContext must not be coerced to str."
        )

    def __bytes__(self):
        raise VenueInstrumentReadinessStateContextCoercionError(
            "VenueInstrumentReadinessStateContext must not be coerced to bytes."
        )

    # --- safe debug repr only (component_name + boundary_version; no venue/instrument identity, no
    #     readiness_status, no provenance, no state_id; no readiness/actionability meaning) ---
    def __repr__(self):
        return (
            "VenueInstrumentReadinessStateContext(component_name={!r}, boundary_version={!r})".format(
                self.component_name, self.boundary_version
            )
        )


def _require_str_field(name, value):
    """Validate one string field: exact str (TypeError), non-empty/non-whitespace (ValueError)."""
    if type(value) is not str:
        raise VenueInstrumentReadinessStateContextTypeError(
            "field {!r} must be a str, not {}".format(name, type(value).__name__)
        )
    if value.strip() == "":
        raise ValueError(
            "field {!r} must be a non-empty, non-whitespace string".format(name)
        )


def make_venue_instrument_readiness_state_context(
    *,
    venue,
    instrument_id,
    base_asset,
    quote_asset,
    readiness_status,
    source_contract,
    source_artifact,
    source_field,
    state_id,
    boundary_version,
):
    """Keyword-only constructor for a single :class:`VenueInstrumentReadinessStateContext`.

    Every field must be an exact, non-empty, non-whitespace ``str`` (``type(value) is str`` — str
    subclasses rejected), preserved verbatim with no trimming or normalization. ``readiness_status``
    must additionally be an exact, case-sensitive token from the closed status vocabulary, else
    :class:`ValueError`. Nothing is derived, parsed, inferred, defaulted, clocked, or normalized.
    Error messages use only field names and ``type(value).__name__`` — never the value itself.
    """
    supplied = {
        "venue": venue,
        "instrument_id": instrument_id,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "readiness_status": readiness_status,
        "source_contract": source_contract,
        "source_artifact": source_artifact,
        "source_field": source_field,
        "state_id": state_id,
        "boundary_version": boundary_version,
    }
    for name in _USER_SUPPLIED_FIELDS:
        _require_str_field(name, supplied[name])

    # readiness_status: exact, case-sensitive membership in the closed vocabulary (no broadening).
    if readiness_status not in _ALLOWED_READINESS_STATUSES:
        raise ValueError(
            "field 'readiness_status' must be an exact token from the venue/instrument readiness "
            "status vocabulary"
        )

    ctx = object.__new__(VenueInstrumentReadinessStateContext)
    object.__setattr__(
        ctx, "component_name", VENUE_INSTRUMENT_READINESS_BOUNDARY_COMPONENT_NAME
    )
    for name in _USER_SUPPLIED_FIELDS:
        object.__setattr__(ctx, name, supplied[name])
    return ctx


# Defensive guard: the declared dataclass field set must remain the closed 11-field contract.
_EXPECTED_FIELD_NAMES = (
    "component_name",
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "readiness_status",
    "source_contract",
    "source_artifact",
    "source_field",
    "state_id",
    "boundary_version",
)
assert tuple(f.name for f in dataclass_fields(VenueInstrumentReadinessStateContext)) == \
    _EXPECTED_FIELD_NAMES
