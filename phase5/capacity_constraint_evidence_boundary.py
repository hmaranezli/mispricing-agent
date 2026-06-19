"""phase5/capacity_constraint_evidence_boundary.py — Slice 1 atomic implementation of the
`phase5_capacity_constraint_evidence_boundary` component: `CapacityConstraintEvidenceContext`.

Per the component planning artifact
(`phase5_capacity_constraint_evidence_boundary_implementation_planning.md`, §6A), this implements ONLY
a frozen, repr-safe, anti-truthiness, anti-coercion, factory-only, slotted carrier that wraps exactly
the explicitly supplied per-source provenance references for the four upstream Phase 5 carriers. The
structural multi-source join auditor (Slice 0) is a separate, separately authorized task and is
deliberately NOT implemented in this module: this carrier audits nothing, joins nothing, compares
nothing, derives nothing, and decides nothing. It is strictly a supplied-evidence descriptor.

Every caller-supplied field is an exact, non-empty, non-whitespace ``str`` (exact-type only —
``type(value) is str``, so str subclasses, ``None``, ``bool``, ``int``, ``float``, ``complex``,
``bytes``, dicts, lists, tuples, and duck-typed string-like objects are rejected), stored verbatim.
The two identity fields ``component_name`` and ``boundary_version`` are NOT caller parameters: the
factory sets them internally from the module constants below, so they cannot be spoofed, overridden,
or injected by the caller.

Direct construction is physically blocked: the carrier is built only through
``make_capacity_constraint_evidence_context`` via ``object.__new__`` + ``object.__setattr__``; calling
the class itself raises. Instances are slotted (no ``__dict__``), so dynamic attribute injection is
rejected. This module reads no environment, configuration, files, database, network, or clock. NO
ORDER EXISTS at this carrier.
"""
from dataclasses import dataclass, fields as dataclass_fields

# Slice 0B references (exact input type guard + misroute halt-carrier guard). These are imported for
# identity comparison via `type(x) is ...` only; no attribute of these types other than `source_*` is
# read on the pass path, and no method of them is invoked.
from phase5.post_profitability_evidence_envelope_boundary import PostProfitabilityEvidenceEnvelope
from phase5.venue_instrument_readiness_boundary import VenueInstrumentReadinessStateContext
from phase5.liquidity_capacity_evidence_boundary import LiquidityCapacityEvidenceContext
from phase5.capital_margin_evidence_boundary import CapitalMarginEvidenceContext
from phase5.blocked_result_boundary import BlockedPacket
from phase5.no_eligible_halt_propagation_boundary import NoEligibleHaltPacket

CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME = "phase5_capacity_constraint_evidence_boundary"
BOUNDARY_VERSION = "phase5.capacity_constraint_evidence_boundary.v0"

# The twelve caller-supplied string fields (the four per-source provenance triplets). The identity
# fields component_name and boundary_version are fixed by the factory, not parameters.
_CALLER_SUPPLIED_FIELDS = (
    "post_profitability_source_contract",
    "post_profitability_source_artifact",
    "post_profitability_source_field",
    "venue_readiness_source_contract",
    "venue_readiness_source_artifact",
    "venue_readiness_source_field",
    "liquidity_capacity_source_contract",
    "liquidity_capacity_source_artifact",
    "liquidity_capacity_source_field",
    "capital_margin_source_contract",
    "capital_margin_source_artifact",
    "capital_margin_source_field",
)


class CapacityConstraintEvidenceContextTruthinessError(TypeError):
    """Raised when a CapacityConstraintEvidenceContext is used in a truthiness/length context."""


class CapacityConstraintEvidenceContextCoercionError(TypeError):
    """Raised when a CapacityConstraintEvidenceContext is coerced to a number, string, or bytes."""


class CapacityConstraintEvidenceContextTypeError(TypeError):
    """Raised for direct construction or for a wrong-typed field value at the factory."""


@dataclass(frozen=True, repr=False, init=False, slots=True, eq=False)
class CapacityConstraintEvidenceContext:
    """A frozen, slotted, anti-coercion carrier wrapping explicitly supplied per-source provenance.

    Construct only through :func:`make_capacity_constraint_evidence_context`. Direct construction
    (no-arg, positional, or keyword) is physically blocked. The carrier holds only the explicitly
    supplied per-source provenance references plus the internally fixed identity fields; it audits
    nothing, joins nothing, compares nothing, derives nothing, and decides nothing.
    """

    component_name: object
    boundary_version: object
    post_profitability_source_contract: object
    post_profitability_source_artifact: object
    post_profitability_source_field: object
    venue_readiness_source_contract: object
    venue_readiness_source_artifact: object
    venue_readiness_source_field: object
    liquidity_capacity_source_contract: object
    liquidity_capacity_source_artifact: object
    liquidity_capacity_source_field: object
    capital_margin_source_contract: object
    capital_margin_source_artifact: object
    capital_margin_source_field: object

    # --- direct construction is physically blocked (no-arg, positional, keyword) ---
    def __init__(self, *args, **kwargs):
        raise CapacityConstraintEvidenceContextTypeError(
            "CapacityConstraintEvidenceContext cannot be constructed directly; use "
            "make_capacity_constraint_evidence_context(...)."
        )

    # --- anti-truthiness ---
    def __bool__(self):
        raise CapacityConstraintEvidenceContextTruthinessError(
            "CapacityConstraintEvidenceContext must not be evaluated for truthiness; inspect fields."
        )

    def __len__(self):
        raise CapacityConstraintEvidenceContextTruthinessError(
            "CapacityConstraintEvidenceContext has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise CapacityConstraintEvidenceContextCoercionError(
            "CapacityConstraintEvidenceContext must not be coerced to int."
        )

    def __float__(self):
        raise CapacityConstraintEvidenceContextCoercionError(
            "CapacityConstraintEvidenceContext must not be coerced to a real number."
        )

    def __complex__(self):
        raise CapacityConstraintEvidenceContextCoercionError(
            "CapacityConstraintEvidenceContext must not be coerced to complex."
        )

    def __index__(self):
        raise CapacityConstraintEvidenceContextCoercionError(
            "CapacityConstraintEvidenceContext must not be coerced to an index."
        )

    def __str__(self):
        raise CapacityConstraintEvidenceContextCoercionError(
            "CapacityConstraintEvidenceContext must not be coerced to str."
        )

    def __bytes__(self):
        raise CapacityConstraintEvidenceContextCoercionError(
            "CapacityConstraintEvidenceContext must not be coerced to bytes."
        )

    # --- safe debug repr only (component_name + boundary_version; no provenance leak) ---
    def __repr__(self):
        return (
            "CapacityConstraintEvidenceContext(component_name={!r}, boundary_version={!r})".format(
                self.component_name, self.boundary_version
            )
        )


def _require_str_field(name, value):
    """Validate one field: exact str (TypeError), non-empty/non-whitespace (ValueError). Verbatim.

    Error messages use only the field name and ``type(value).__name__`` — never the value itself.
    """
    if type(value) is not str:
        raise CapacityConstraintEvidenceContextTypeError(
            "field {!r} must be a str, not {}".format(name, type(value).__name__)
        )
    if value.strip() == "":
        raise ValueError(
            "field {!r} must be a non-empty, non-whitespace string".format(name)
        )


def make_capacity_constraint_evidence_context(
    *,
    post_profitability_source_contract,
    post_profitability_source_artifact,
    post_profitability_source_field,
    venue_readiness_source_contract,
    venue_readiness_source_artifact,
    venue_readiness_source_field,
    liquidity_capacity_source_contract,
    liquidity_capacity_source_artifact,
    liquidity_capacity_source_field,
    capital_margin_source_contract,
    capital_margin_source_artifact,
    capital_margin_source_field,
):
    """Keyword-only constructor for a single :class:`CapacityConstraintEvidenceContext`.

    Accepts exactly the twelve per-source provenance triplet parameters. ``component_name`` and
    ``boundary_version`` are NOT parameters — they are set internally from the module constants and
    may not be supplied by the caller (passing either raises ``TypeError`` as an unexpected keyword).
    Every supplied field must be an exact, non-empty, non-whitespace ``str`` (``type(value) is str`` —
    str subclasses rejected), preserved verbatim. The carrier performs no audit, no join, no
    comparison, and no derivation. Error messages use only field names and ``type(value).__name__`` —
    never the value itself.
    """
    supplied = {
        "post_profitability_source_contract": post_profitability_source_contract,
        "post_profitability_source_artifact": post_profitability_source_artifact,
        "post_profitability_source_field": post_profitability_source_field,
        "venue_readiness_source_contract": venue_readiness_source_contract,
        "venue_readiness_source_artifact": venue_readiness_source_artifact,
        "venue_readiness_source_field": venue_readiness_source_field,
        "liquidity_capacity_source_contract": liquidity_capacity_source_contract,
        "liquidity_capacity_source_artifact": liquidity_capacity_source_artifact,
        "liquidity_capacity_source_field": liquidity_capacity_source_field,
        "capital_margin_source_contract": capital_margin_source_contract,
        "capital_margin_source_artifact": capital_margin_source_artifact,
        "capital_margin_source_field": capital_margin_source_field,
    }
    for name in _CALLER_SUPPLIED_FIELDS:
        _require_str_field(name, supplied[name])

    ctx = object.__new__(CapacityConstraintEvidenceContext)
    object.__setattr__(
        ctx, "component_name", CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME
    )
    object.__setattr__(ctx, "boundary_version", BOUNDARY_VERSION)
    for name in _CALLER_SUPPLIED_FIELDS:
        object.__setattr__(ctx, name, supplied[name])
    return ctx


# Defensive guard: the declared dataclass field set must remain the closed 14-field contract.
_EXPECTED_FIELD_NAMES = (
    "component_name",
    "boundary_version",
    "post_profitability_source_contract",
    "post_profitability_source_artifact",
    "post_profitability_source_field",
    "venue_readiness_source_contract",
    "venue_readiness_source_artifact",
    "venue_readiness_source_field",
    "liquidity_capacity_source_contract",
    "liquidity_capacity_source_artifact",
    "liquidity_capacity_source_field",
    "capital_margin_source_contract",
    "capital_margin_source_artifact",
    "capital_margin_source_field",
)
assert tuple(f.name for f in dataclass_fields(CapacityConstraintEvidenceContext)) == \
    _EXPECTED_FIELD_NAMES


# ===================================================================================================
# Slice 0A — gate scaffolding ONLY: blocked-reason constants, gate error classes, the stateless
# `CapacityConstraintGate` namespace, and an EXACT keyword-only `capacity_constraint_preflight`
# fail-fast stub. This batch deliberately implements NO pass path, NO blocked-branch logic, NO
# parsing/comparison, NO `make_blocked_packet` call, and NO full structural-join boundary class.
# The structural multi-source join (Slice 0B+) is a separate, separately authorized task. NO ORDER
# EXISTS at this gate.
# ===================================================================================================

# Branch-to-reason tokens (each constant's value equals its own name). Slice 0A only declares them;
# no branch emits any of them yet.
CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE"
CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE"
CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE"
CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH = "CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH"
CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH = "CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH"
CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE"


class CapacityConstraintGateTypeError(TypeError):
    """Raised when a preflight input is of a wrong (non-halt-carrier) type. No branch behavior yet."""


class CapacityConstraintMisroutedHaltCarrierError(TypeError):
    """Raised when an upstream halt packet is misrouted into a preflight evidence slot. No behavior yet."""


def capacity_constraint_preflight(
    *,
    evidence_envelope,
    venue_readiness,
    liquidity_evidence,
    capital_evidence,
):
    """Exact keyword-only preflight entrypoint — Slice 0B (type guard + misroute guard + pass path).

    This slice implements ONLY: (1) an exact input type guard (``type(x) is T`` — no ``isinstance``,
    no truthiness, no duck typing); (2) a misroute halt-carrier guard that rejects an exact
    ``BlockedPacket`` / ``NoEligibleHaltPacket`` supplied to any slot; and (3) the all-agree pass path
    that returns a :class:`CapacityConstraintEvidenceContext` built via
    :func:`make_capacity_constraint_evidence_context` with VERBATIM ``source_*`` transfer.

    BOUNDARY: this is NOT final boundary pass readiness. The fail-closed structural convergence checks
    (identity / unit / staleness / size magnitude) and every blocked branch are Slice 0C and are NOT
    implemented here; therefore this preflight is NOT live-wirable until Slice 0C lands. No blocked
    packet is emitted, no scalar is parsed, and no clock is read. **NO ORDER EXISTS.**

    Provenance transfer is strictly verbatim: each ``source_*`` value is read directly off its carrier
    and passed unchanged to the factory — no ``str()``, no formatting, no ``join``, no defaulting, no
    trimming, no normalization, and no synthetic provenance. ``component_name`` and ``boundary_version``
    are never passed (the factory sets them internally).
    """
    supplied_inputs = (
        ("evidence_envelope", evidence_envelope),
        ("venue_readiness", venue_readiness),
        ("liquidity_evidence", liquidity_evidence),
        ("capital_evidence", capital_evidence),
    )
    # Misroute guard first: an upstream halt packet in any slot is a programmatic routing error, never
    # a blocked token and never a returned packet.
    for slot_name, value in supplied_inputs:
        if type(value) is BlockedPacket or type(value) is NoEligibleHaltPacket:
            raise CapacityConstraintMisroutedHaltCarrierError(
                "halt carrier {} misrouted into preflight slot {!r}".format(
                    type(value).__name__, slot_name
                )
            )
    # Exact input type guard (exact type only — never isinstance, never truthiness).
    if type(evidence_envelope) is not PostProfitabilityEvidenceEnvelope:
        raise CapacityConstraintGateTypeError(
            "evidence_envelope must be PostProfitabilityEvidenceEnvelope, not {}".format(
                type(evidence_envelope).__name__
            )
        )
    if type(venue_readiness) is not VenueInstrumentReadinessStateContext:
        raise CapacityConstraintGateTypeError(
            "venue_readiness must be VenueInstrumentReadinessStateContext, not {}".format(
                type(venue_readiness).__name__
            )
        )
    if type(liquidity_evidence) is not LiquidityCapacityEvidenceContext:
        raise CapacityConstraintGateTypeError(
            "liquidity_evidence must be LiquidityCapacityEvidenceContext, not {}".format(
                type(liquidity_evidence).__name__
            )
        )
    if type(capital_evidence) is not CapitalMarginEvidenceContext:
        raise CapacityConstraintGateTypeError(
            "capital_evidence must be CapitalMarginEvidenceContext, not {}".format(
                type(capital_evidence).__name__
            )
        )
    # All-agree pass path: verbatim per-source provenance transfer into the 12-param factory. (Slice 0C
    # will insert the fail-closed structural convergence checks before this return.)
    return make_capacity_constraint_evidence_context(
        post_profitability_source_contract=evidence_envelope.source_contract,
        post_profitability_source_artifact=evidence_envelope.source_artifact,
        post_profitability_source_field=evidence_envelope.source_field,
        venue_readiness_source_contract=venue_readiness.source_contract,
        venue_readiness_source_artifact=venue_readiness.source_artifact,
        venue_readiness_source_field=venue_readiness.source_field,
        liquidity_capacity_source_contract=liquidity_evidence.source_contract,
        liquidity_capacity_source_artifact=liquidity_evidence.source_artifact,
        liquidity_capacity_source_field=liquidity_evidence.source_field,
        capital_margin_source_contract=capital_evidence.source_contract,
        capital_margin_source_artifact=capital_evidence.source_artifact,
        capital_margin_source_field=capital_evidence.source_field,
    )


class CapacityConstraintGate:
    """Stateless namespace exposing the capacity-constraint preflight as a static method.

    Carries no state and needs no construction state (``__slots__ = ()``). ``preflight`` is the
    module-level :func:`capacity_constraint_preflight` exposed as a static method.
    """

    __slots__ = ()

    preflight = staticmethod(capacity_constraint_preflight)
