"""phase5/venue_instrument_readiness_boundary.py — atomic implementation of the
`phase5_venue_instrument_readiness_boundary` component: `VenueInstrumentReadinessStateContext`
(Slice 1) and `VenueInstrumentReadinessGate` / `venue_instrument_readiness_preflight` (Slice 2).

Per the component planning artifact
(`phase5_venue_instrument_readiness_implementation_planning.md`), Slice 1 is a frozen, repr-safe,
anti-truthiness, anti-coercion, factory-only carrier that wraps exactly the explicitly supplied
venue/instrument readiness-state evidence, and Slice 2 is a pure/offline/deterministic readiness-state
gate over one exact upstream evidence envelope and one exact readiness-state carrier. The Slice 1
carrier below is unchanged by Slice 2.

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

from phase5.blocked_result_boundary import BlockedPacket, make_blocked_packet
from phase5.no_eligible_halt_propagation_boundary import (
    NoEligibleHaltPacket,
    make_no_eligible_halt_packet,
)
from phase5.post_profitability_evidence_envelope_boundary import (
    PostProfitabilityEvidenceEnvelope,
)
from phase5.const import (
    PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
    BLOCKED_NEEDS_EVIDENCE,
    NEXT_ACTION_OBTAIN_EVIDENCE,
)

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


# ---------------------------------------------------------------------------
# Slice 2: VenueInstrumentReadinessGate / venue_instrument_readiness_preflight
#
# A pure, offline, deterministic venue/instrument readiness-state gate over exactly one
# PostProfitabilityEvidenceEnvelope and one VenueInstrumentReadinessStateContext. Outputs are exactly:
# the identical envelope (active + identity match), an existing BlockedPacket (missing / malformed /
# unrecognized readiness evidence, or identity mismatch), or an existing NoEligibleHaltPacket (a valid
# explicit non-active state). A programmatic wrong-path / misroute raises and never produces a packet.
# The gate reads only already-explicit fields; it performs no normalization, parsing, inference,
# defaulting, clock, network, or arithmetic, mutates neither input, and never broadens
# VENUE_INSTRUMENT_STATE_ACTIVE into a tradable / executable / actionable / ready claim.
# ---------------------------------------------------------------------------

GATE_SOURCE_CONTRACT = "phase5_venue_instrument_readiness_implementation_planning.md"

# Pinned reason vocabulary (planning-fixed; no aliases).
VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MISSING_READINESS_STATE = "VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MISSING_READINESS_STATE"
VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MALFORMED_READINESS_STATE = "VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MALFORMED_READINESS_STATE"
VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_IDENTITY_MISMATCH = "VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_IDENTITY_MISMATCH"
VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_UNRECOGNIZED_STATE_VOCABULARY = "VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_UNRECOGNIZED_STATE_VOCABULARY"
VENUE_INSTRUMENT_READINESS_GATE_NO_ELIGIBLE_STATE_NOT_ACTIVE = "VENUE_INSTRUMENT_READINESS_GATE_NO_ELIGIBLE_STATE_NOT_ACTIVE"

# NoEligible packet literals (a valid explicit non-active state is the only V1 no-eligible fact here).
_NO_ELIGIBLE_STATUS = "NO_ELIGIBLE"
_NO_ELIGIBLE_NEXT_ACTION = "HALT_BYPASS_NO_ELIGIBLE"

# The four explicit identity fields compared by exact, case-sensitive equality (no normalization).
_IDENTITY_FIELDS = ("venue", "instrument_id", "base_asset", "quote_asset")

# Distinct from None: lets the gate tell a truly-absent attribute apart from an explicit None value.
_MISSING = object()


class VenueInstrumentReadinessGateTypeError(TypeError):
    """Raised for a programmatic wrong-path / wrong-type input to the readiness gate."""


class MisroutedHaltCarrierError(TypeError):
    """Raised when a halt carrier is misrouted into the venue/instrument readiness gate boundary."""


def reject_misrouted_halt_carrier(payload):
    """Fail closed if a halt carrier is misrouted into the readiness gate boundary.

    - Exact :class:`BlockedPacket` or exact :class:`NoEligibleHaltPacket` → raise
      :class:`MisroutedHaltCarrierError` (a routing/integration bug, not a readiness input).
    - Anything else → return ``None``; subclasses are NOT exact halt carriers.

    Exact-type checks only (no isinstance). An already-halted input is never converted into a new
    BlockedPacket/NoEligibleHaltPacket output; only its type name is used in the message.
    """
    if type(payload) is BlockedPacket:
        raise MisroutedHaltCarrierError(
            "venue/instrument readiness gate boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    if type(payload) is NoEligibleHaltPacket:
        raise MisroutedHaltCarrierError(
            "venue/instrument readiness gate boundary must not receive a halt carrier; got "
            + type(payload).__name__
        )
    return None


def _gate_blocked(*, evidence_envelope, reason_code, missing_or_invalid_field):
    """Build a gate BlockedPacket via the existing factory — provenance from the evidence envelope."""
    return make_blocked_packet(
        component_name=VENUE_INSTRUMENT_READINESS_BOUNDARY_COMPONENT_NAME,
        origin_component=VENUE_INSTRUMENT_READINESS_BOUNDARY_COMPONENT_NAME,
        origin_result_status=PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
        status=PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE,
        blocked_status=BLOCKED_NEEDS_EVIDENCE,
        reason_code=reason_code,
        missing_or_invalid_field=missing_or_invalid_field,
        source_contract=evidence_envelope.source_contract,
        source_artifact=evidence_envelope.source_artifact,
        source_field=evidence_envelope.source_field,
        deterministic_next_action=NEXT_ACTION_OBTAIN_EVIDENCE,
        human_review_required=True,
        may_retry_after_evidence=True,
        created_from_contract=GATE_SOURCE_CONTRACT,
        boundary_version=BOUNDARY_VERSION,
    )


def _gate_no_eligible(*, evidence_envelope):
    """Build the gate NoEligibleHaltPacket via the existing factory — provenance from the envelope.

    The rejected-opportunity lineage (source_contract/source_artifact/source_field) is preserved from
    the :class:`PostProfitabilityEvidenceEnvelope`, never from the readiness-state carrier.
    """
    return make_no_eligible_halt_packet(
        component_name=VENUE_INSTRUMENT_READINESS_BOUNDARY_COMPONENT_NAME,
        origin_component=VENUE_INSTRUMENT_READINESS_BOUNDARY_COMPONENT_NAME,
        origin_result_status=_NO_ELIGIBLE_STATUS,
        status=_NO_ELIGIBLE_STATUS,
        no_eligible_reason=VENUE_INSTRUMENT_READINESS_GATE_NO_ELIGIBLE_STATE_NOT_ACTIVE,
        source_contract=evidence_envelope.source_contract,
        source_artifact=evidence_envelope.source_artifact,
        source_field=evidence_envelope.source_field,
        deterministic_next_action=_NO_ELIGIBLE_NEXT_ACTION,
        boundary_version=BOUNDARY_VERSION,
    )


def venue_instrument_readiness_preflight(*, evidence_envelope, readiness_state):
    """Pure venue/instrument readiness-state gate over one evidence envelope and one state carrier.

    Returns the identical ``evidence_envelope`` on pass (explicit ``VENUE_INSTRUMENT_STATE_ACTIVE``
    with an exact, case-sensitive identity match); an existing :class:`BlockedPacket` for missing /
    malformed / unrecognized readiness-state evidence or an identity mismatch; and an existing
    :class:`NoEligibleHaltPacket` for a valid explicit non-active state. Programmatic wrong-path /
    wrong-type inputs raise :class:`VenueInstrumentReadinessGateTypeError` or
    :class:`MisroutedHaltCarrierError` and never produce a packet. See
    ``phase5_venue_instrument_readiness_implementation_planning.md`` for the pinned contract.

    The exact carrier instance is zero-trusted: defensive attribute access only distinguishes a truly
    absent ``readiness_status`` (→ MISSING) from an unreadable/malformed one (→ MALFORMED); it never
    becomes parsing, defaulting, coercion, or normalization.
    """
    # --- programmatic wrong-path / wrong-type first ---
    reject_misrouted_halt_carrier(evidence_envelope)
    reject_misrouted_halt_carrier(readiness_state)
    if type(evidence_envelope) is not PostProfitabilityEvidenceEnvelope:
        raise VenueInstrumentReadinessGateTypeError(
            "venue_instrument_readiness_preflight requires an exact PostProfitabilityEvidenceEnvelope, not "
            + type(evidence_envelope).__name__
        )
    if type(readiness_state) is not VenueInstrumentReadinessStateContext:
        raise VenueInstrumentReadinessGateTypeError(
            "venue_instrument_readiness_preflight requires an exact VenueInstrumentReadinessStateContext, not "
            + type(readiness_state).__name__
        )

    # --- zero-trust the exact readiness_state instance's decision variable (no .strip/.upper/etc.) ---
    status = getattr(readiness_state, "readiness_status", _MISSING)
    if status is _MISSING:
        return _gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MISSING_READINESS_STATE,
            missing_or_invalid_field="readiness_status",
        )
    if type(status) is not str or status == "" or status.isspace():
        return _gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MALFORMED_READINESS_STATE,
            missing_or_invalid_field="readiness_status",
        )
    if status not in _ALLOWED_READINESS_STATUSES:
        return _gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_UNRECOGNIZED_STATE_VOCABULARY,
            missing_or_invalid_field="readiness_status",
        )

    # --- identity comparison: exact, case-sensitive equality on the four explicit identity fields ---
    for name in _IDENTITY_FIELDS:
        envelope_value = getattr(evidence_envelope, name, _MISSING)
        state_value = getattr(readiness_state, name, _MISSING)
        if envelope_value is _MISSING or state_value is _MISSING or envelope_value != state_value:
            return _gate_blocked(
                evidence_envelope=evidence_envelope,
                reason_code=VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_IDENTITY_MISMATCH,
                missing_or_invalid_field=name,
            )

    # --- status evaluation (status already validated to be in the closed vocabulary) ---
    if status == VENUE_INSTRUMENT_STATE_ACTIVE:
        # pass-through identity: the identical envelope object (no wrap, no copy, no mutate)
        return evidence_envelope
    # a valid explicit non-active state (suspended/maintenance/closed/unsupported)
    return _gate_no_eligible(evidence_envelope=evidence_envelope)


class VenueInstrumentReadinessGate:
    """Stateless, non-carrier namespace for the venue/instrument readiness gate.

    Carries no state and requires no construction; the runtime entrypoint is the pure function
    :func:`venue_instrument_readiness_preflight`, exposed here as a static method.
    """

    __slots__ = ()

    preflight = staticmethod(venue_instrument_readiness_preflight)
