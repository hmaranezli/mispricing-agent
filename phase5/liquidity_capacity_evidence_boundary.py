"""phase5/liquidity_capacity_evidence_boundary.py — Slice 1 atomic implementation of the
`phase5_liquidity_capacity_evidence_boundary` component: `LiquidityCapacityEvidenceContext`.

Per the component planning artifact
(`phase5_liquidity_capacity_evidence_boundary_implementation_planning.md`), Slice 1 is a frozen,
repr-safe, anti-truthiness, anti-coercion, factory-only carrier that wraps exactly the explicitly
supplied liquidity/depth capacity evidence, and Slice 2 is a pure/offline/deterministic
liquidity-capacity sufficiency gate over one exact upstream evidence envelope and one exact
capacity-evidence carrier. The Slice 1 carrier below is unchanged by Slice 2.

This carrier is strictly a supplied-evidence descriptor. Every user-supplied field is an exact,
non-empty, non-whitespace ``str`` (``type(value) is str`` — no isinstance, so str subclasses, ``None``,
``bool``, ``int``, ``float``, dicts, bytes, and duck-typed string-likes are rejected), stored
verbatim. The carrier performs NO numeric or format validation, NO comparison, NO derivation, and NO
decision: quantity-like fields (``observed_size``, ``available_capacity``, ``estimated_slippage_bps``)
and the scalar epoch fields (``liquidity_snapshot_epoch_ms``, ``evidence_epoch_tolerance_ms``) are kept
as exact strings only, with their format/validity left entirely to the future gate. The
``estimated_slippage_bps`` field is passive metadata only — it is stored verbatim and never
interpreted here.
"""
from dataclasses import dataclass, fields as dataclass_fields

LIQUIDITY_CAPACITY_EVIDENCE_BOUNDARY_COMPONENT_NAME = (
    "phase5_liquidity_capacity_evidence_boundary"
)
BOUNDARY_VERSION = "phase5.liquidity_capacity_evidence_boundary.v0"

# The 16 caller-supplied string fields (component_name is fixed by the factory, not a parameter).
_USER_SUPPLIED_FIELDS = (
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "observed_size",
    "observed_size_unit",
    "available_capacity",
    "capacity_unit",
    "liquidity_snapshot_epoch_ms",
    "evidence_epoch_tolerance_ms",
    "source_contract",
    "source_artifact",
    "source_field",
    "liquidity_evidence_id",
    "boundary_version",
    "estimated_slippage_bps",
)


class LiquidityCapacityEvidenceContextTruthinessError(TypeError):
    """Raised when a LiquidityCapacityEvidenceContext is used in a truthiness/length context."""


class LiquidityCapacityEvidenceContextCoercionError(TypeError):
    """Raised when a LiquidityCapacityEvidenceContext is coerced to a number, string, or bytes."""


class LiquidityCapacityEvidenceContextTypeError(TypeError):
    """Raised when the factory receives a wrong-typed field value."""


@dataclass(frozen=True, repr=False, init=False)
class LiquidityCapacityEvidenceContext:
    """A frozen, anti-coercion carrier wrapping explicitly supplied liquidity/depth capacity evidence.

    Construct only through :func:`make_liquidity_capacity_evidence_context`. Direct/positional
    construction is not supported. The carrier holds only the explicitly supplied identity, observed
    size, available capacity, snapshot/tolerance scalars, provenance, and passive metadata; it makes
    no comparison, no derivation, and no decision.
    """

    component_name: object
    venue: object
    instrument_id: object
    base_asset: object
    quote_asset: object
    observed_size: object
    observed_size_unit: object
    available_capacity: object
    capacity_unit: object
    liquidity_snapshot_epoch_ms: object
    evidence_epoch_tolerance_ms: object
    source_contract: object
    source_artifact: object
    source_field: object
    liquidity_evidence_id: object
    boundary_version: object
    estimated_slippage_bps: object

    # --- anti-truthiness ---
    def __bool__(self):
        raise LiquidityCapacityEvidenceContextTruthinessError(
            "LiquidityCapacityEvidenceContext must not be evaluated for truthiness; inspect fields."
        )

    def __len__(self):
        raise LiquidityCapacityEvidenceContextTruthinessError(
            "LiquidityCapacityEvidenceContext has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise LiquidityCapacityEvidenceContextCoercionError(
            "LiquidityCapacityEvidenceContext must not be coerced to int."
        )

    def __float__(self):
        raise LiquidityCapacityEvidenceContextCoercionError(
            "LiquidityCapacityEvidenceContext must not be coerced to a real number."
        )

    def __complex__(self):
        raise LiquidityCapacityEvidenceContextCoercionError(
            "LiquidityCapacityEvidenceContext must not be coerced to complex."
        )

    def __index__(self):
        raise LiquidityCapacityEvidenceContextCoercionError(
            "LiquidityCapacityEvidenceContext must not be coerced to an index."
        )

    def __str__(self):
        raise LiquidityCapacityEvidenceContextCoercionError(
            "LiquidityCapacityEvidenceContext must not be coerced to str."
        )

    def __bytes__(self):
        raise LiquidityCapacityEvidenceContextCoercionError(
            "LiquidityCapacityEvidenceContext must not be coerced to bytes."
        )

    # --- safe debug repr only (component_name + boundary_version; no identity/size/capacity/epoch/
    #     provenance/metadata leak; no sufficiency/readiness meaning) ---
    def __repr__(self):
        return (
            "LiquidityCapacityEvidenceContext(component_name={!r}, boundary_version={!r})".format(
                self.component_name, self.boundary_version
            )
        )


def _require_str_field(name, value):
    """Validate one field: exact str (TypeError), non-empty/non-whitespace (ValueError). Verbatim."""
    if type(value) is not str:
        raise LiquidityCapacityEvidenceContextTypeError(
            "field {!r} must be a str, not {}".format(name, type(value).__name__)
        )
    if value.strip() == "":
        raise ValueError(
            "field {!r} must be a non-empty, non-whitespace string".format(name)
        )


def make_liquidity_capacity_evidence_context(
    *,
    venue,
    instrument_id,
    base_asset,
    quote_asset,
    observed_size,
    observed_size_unit,
    available_capacity,
    capacity_unit,
    liquidity_snapshot_epoch_ms,
    evidence_epoch_tolerance_ms,
    source_contract,
    source_artifact,
    source_field,
    liquidity_evidence_id,
    boundary_version,
    estimated_slippage_bps,
):
    """Keyword-only constructor for a single :class:`LiquidityCapacityEvidenceContext`.

    Every field must be an exact, non-empty, non-whitespace ``str`` (``type(value) is str`` — str
    subclasses rejected), preserved verbatim. The carrier performs no numeric or format validation,
    no comparison, and no derivation; quantity-like and scalar epoch fields are kept as exact strings
    only. ``estimated_slippage_bps`` is passive metadata, stored verbatim and never interpreted. Error
    messages use only field names and ``type(value).__name__`` — never the value itself.
    """
    supplied = {
        "venue": venue,
        "instrument_id": instrument_id,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "observed_size": observed_size,
        "observed_size_unit": observed_size_unit,
        "available_capacity": available_capacity,
        "capacity_unit": capacity_unit,
        "liquidity_snapshot_epoch_ms": liquidity_snapshot_epoch_ms,
        "evidence_epoch_tolerance_ms": evidence_epoch_tolerance_ms,
        "source_contract": source_contract,
        "source_artifact": source_artifact,
        "source_field": source_field,
        "liquidity_evidence_id": liquidity_evidence_id,
        "boundary_version": boundary_version,
        "estimated_slippage_bps": estimated_slippage_bps,
    }
    for name in _USER_SUPPLIED_FIELDS:
        _require_str_field(name, supplied[name])

    ctx = object.__new__(LiquidityCapacityEvidenceContext)
    object.__setattr__(
        ctx, "component_name", LIQUIDITY_CAPACITY_EVIDENCE_BOUNDARY_COMPONENT_NAME
    )
    for name in _USER_SUPPLIED_FIELDS:
        object.__setattr__(ctx, name, supplied[name])
    return ctx


# Defensive guard: the declared dataclass field set must remain the closed 17-field contract.
_EXPECTED_FIELD_NAMES = (
    "component_name",
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "observed_size",
    "observed_size_unit",
    "available_capacity",
    "capacity_unit",
    "liquidity_snapshot_epoch_ms",
    "evidence_epoch_tolerance_ms",
    "source_contract",
    "source_artifact",
    "source_field",
    "liquidity_evidence_id",
    "boundary_version",
    "estimated_slippage_bps",
)
assert tuple(f.name for f in dataclass_fields(LiquidityCapacityEvidenceContext)) == \
    _EXPECTED_FIELD_NAMES


# ===PHASE5-SLICE2-GATE-BOUNDARY===
# Slice 2: LiquidityCapacityGate / liquidity_capacity_preflight
#
# A pure, offline, deterministic liquidity-capacity sufficiency gate over exactly one
# PostProfitabilityEvidenceEnvelope and one LiquidityCapacityEvidenceContext. Outputs are exactly:
# the identical envelope (valid + size-bound + fresh + sufficient), an existing BlockedPacket
# (missing / malformed / identity-mismatch / unit-mismatch / stale supplied evidence), or an existing
# NoEligibleHaltPacket (valid bound fresh evidence whose positive capacity is below the observed
# size). A programmatic wrong-path / misroute raises and never produces a packet. The gate reads only
# the allow-listed decision fields, parses magnitudes/epochs into LOCAL ephemeral values only, mutates
# neither input, builds no new packet schema, and never broadens sufficient capacity into a
# trade-ready or order-placement claim. estimated_slippage_bps is passive and is never read.
import re as _re
from decimal import Decimal as _Decimal

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

# Canonical unsigned decimal: integer part "0" or a non-zero-leading run, optional fractional part
# (no sign, no exponent, no underscores, no commas, no leading zeros beyond a single "0").
_GATE_UNSIGNED_DECIMAL = _re.compile(r"(0|[1-9]\d*)(\.\d+)?")
# Canonical unsigned integer: "0" or a non-zero-leading run (no sign, no decimal, no exponent).
_GATE_UNSIGNED_INT = _re.compile(r"0|[1-9]\d*")

GATE_SOURCE_CONTRACT = (
    "phase5_liquidity_capacity_evidence_boundary_implementation_planning.md"
)

# Pinned reason vocabulary (planning-fixed; LIQUIDITY_CAPACITY_GATE_ prefix only; no aliases).
LIQUIDITY_CAPACITY_GATE_BLOCKED_MISSING_LIQUIDITY_EVIDENCE = "LIQUIDITY_CAPACITY_GATE_BLOCKED_MISSING_LIQUIDITY_EVIDENCE"
LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE = "LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE"
LIQUIDITY_CAPACITY_GATE_BLOCKED_IDENTITY_MISMATCH = "LIQUIDITY_CAPACITY_GATE_BLOCKED_IDENTITY_MISMATCH"
LIQUIDITY_CAPACITY_GATE_BLOCKED_UNIT_MISMATCH = "LIQUIDITY_CAPACITY_GATE_BLOCKED_UNIT_MISMATCH"
LIQUIDITY_CAPACITY_GATE_BLOCKED_STALE_EVIDENCE = "LIQUIDITY_CAPACITY_GATE_BLOCKED_STALE_EVIDENCE"
LIQUIDITY_CAPACITY_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPACITY = "LIQUIDITY_CAPACITY_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPACITY"

# NoEligible packet literals (insufficient positive capacity is the only V1 no-eligible fact here).
_NO_ELIGIBLE_STATUS = "NO_ELIGIBLE"
_NO_ELIGIBLE_NEXT_ACTION = "HALT_BYPASS_NO_ELIGIBLE"

# The four explicit identity fields compared by exact, case-sensitive equality (no normalization).
_IDENTITY_FIELDS = ("venue", "instrument_id", "base_asset", "quote_asset")

# Distinct from None: lets the gate tell a truly-absent attribute apart from an explicit None value.
_MISSING = object()


class LiquidityCapacityGateTypeError(TypeError):
    """Raised for a programmatic wrong-path / wrong-type input to the liquidity-capacity gate."""


class MisroutedHaltCarrierError(TypeError):
    """Raised when a halt carrier is misrouted into the liquidity-capacity gate boundary."""


def reject_misrouted_halt_carrier(payload):
    """Fail closed if a halt carrier is misrouted into the liquidity-capacity gate boundary.

    - Exact :class:`BlockedPacket` or exact :class:`NoEligibleHaltPacket` → raise
      :class:`MisroutedHaltCarrierError` (a misroute / integration bug, not a gate input).
    - Anything else → return ``None``; subclasses are NOT exact halt carriers.

    Exact-type checks only (no isinstance). An already-halted input is never converted into a new
    BlockedPacket/NoEligibleHaltPacket output; only its type name is used in the message.
    """
    if type(payload) is BlockedPacket:
        raise MisroutedHaltCarrierError(
            f"liquidity capacity gate boundary must not receive a halt carrier; "
            f"got {type(payload).__name__}"
        )
    if type(payload) is NoEligibleHaltPacket:
        raise MisroutedHaltCarrierError(
            f"liquidity capacity gate boundary must not receive a halt carrier; "
            f"got {type(payload).__name__}"
        )
    return None


def _is_canonical_unsigned_decimal(value):
    """True only for an exact ``str`` matching the canonical unsigned decimal grammar (verbatim)."""
    return type(value) is str and _GATE_UNSIGNED_DECIMAL.fullmatch(value) is not None


def _is_canonical_unsigned_int(value):
    """True only for an exact ``str`` matching the canonical unsigned integer grammar (verbatim)."""
    return type(value) is str and _GATE_UNSIGNED_INT.fullmatch(value) is not None


def _gate_blocked(*, evidence_envelope, reason_code, missing_or_invalid_field):
    """Build a gate BlockedPacket via the existing factory — provenance from the evidence envelope."""
    return make_blocked_packet(
        component_name=LIQUIDITY_CAPACITY_EVIDENCE_BOUNDARY_COMPONENT_NAME,
        origin_component=LIQUIDITY_CAPACITY_EVIDENCE_BOUNDARY_COMPONENT_NAME,
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
    the :class:`PostProfitabilityEvidenceEnvelope`, never from the capacity-evidence carrier.
    """
    return make_no_eligible_halt_packet(
        component_name=LIQUIDITY_CAPACITY_EVIDENCE_BOUNDARY_COMPONENT_NAME,
        origin_component=LIQUIDITY_CAPACITY_EVIDENCE_BOUNDARY_COMPONENT_NAME,
        origin_result_status=_NO_ELIGIBLE_STATUS,
        status=_NO_ELIGIBLE_STATUS,
        no_eligible_reason=LIQUIDITY_CAPACITY_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPACITY,
        source_contract=evidence_envelope.source_contract,
        source_artifact=evidence_envelope.source_artifact,
        source_field=evidence_envelope.source_field,
        deterministic_next_action=_NO_ELIGIBLE_NEXT_ACTION,
        boundary_version=BOUNDARY_VERSION,
    )


def liquidity_capacity_preflight(*, evidence_envelope, liquidity_evidence):
    """Pure liquidity-capacity sufficiency gate over one evidence envelope and one capacity carrier.

    Returns the identical ``evidence_envelope`` on pass (valid, size-bound, fresh, and with
    inclusive-sufficient positive capacity); an existing :class:`BlockedPacket` for missing /
    malformed / identity-mismatch / unit-mismatch / stale supplied evidence; and an existing
    :class:`NoEligibleHaltPacket` when valid bound fresh evidence has positive capacity below the
    observed size. Programmatic wrong-path / wrong-type inputs raise
    :class:`LiquidityCapacityGateTypeError` or :class:`MisroutedHaltCarrierError` and never produce a
    packet. See ``phase5_liquidity_capacity_evidence_boundary_implementation_planning.md``.

    The exact carrier instance is zero-trusted: defensive attribute access distinguishes a truly
    absent decision field (→ MISSING) from a present-but-malformed one (→ MALFORMED); it never becomes
    parsing tolerance, defaulting, coercion, or normalization. Magnitudes and epochs are parsed into
    LOCAL ephemeral values only; neither input is mutated. ``estimated_slippage_bps`` and the carrier's
    provenance/id/boundary_version are never read.
    """
    # --- branch priority 1: programmatic wrong-path / misroute first ---
    reject_misrouted_halt_carrier(evidence_envelope)
    reject_misrouted_halt_carrier(liquidity_evidence)

    # --- branch priority 2: exact-type checks (subclasses rejected) ---
    if type(evidence_envelope) is not PostProfitabilityEvidenceEnvelope:
        raise LiquidityCapacityGateTypeError(
            "liquidity_capacity_preflight requires an exact PostProfitabilityEvidenceEnvelope, "
            f"not {type(evidence_envelope).__name__}"
        )
    if type(liquidity_evidence) is not LiquidityCapacityEvidenceContext:
        raise LiquidityCapacityGateTypeError(
            "liquidity_capacity_preflight requires an exact LiquidityCapacityEvidenceContext, "
            f"not {type(liquidity_evidence).__name__}"
        )

    # --- branch priority 3: zero-trust the allow-listed liquidity decision fields ---
    liq_observed_size = getattr(liquidity_evidence, "observed_size", _MISSING)
    liq_observed_size_unit = getattr(liquidity_evidence, "observed_size_unit", _MISSING)
    liq_available_capacity = getattr(liquidity_evidence, "available_capacity", _MISSING)
    liq_capacity_unit = getattr(liquidity_evidence, "capacity_unit", _MISSING)
    liq_snapshot = getattr(liquidity_evidence, "liquidity_snapshot_epoch_ms", _MISSING)
    liq_tolerance = getattr(liquidity_evidence, "evidence_epoch_tolerance_ms", _MISSING)
    for fname, value in (
        ("observed_size", liq_observed_size),
        ("observed_size_unit", liq_observed_size_unit),
        ("available_capacity", liq_available_capacity),
        ("capacity_unit", liq_capacity_unit),
        ("liquidity_snapshot_epoch_ms", liq_snapshot),
        ("evidence_epoch_tolerance_ms", liq_tolerance),
    ):
        if value is _MISSING:
            return _gate_blocked(
                evidence_envelope=evidence_envelope,
                reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_MISSING_LIQUIDITY_EVIDENCE,
                missing_or_invalid_field=fname,
            )

    # --- branch priority 4: malformed grammar / strict positivity (fail closed; no exceptions) ---
    env_observed_size = evidence_envelope.observed_size
    env_observed_at = evidence_envelope.observed_at_epoch_ms
    if not _is_canonical_unsigned_decimal(liq_observed_size):
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE,
                             missing_or_invalid_field="observed_size")
    if not _is_canonical_unsigned_decimal(liq_available_capacity):
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE,
                             missing_or_invalid_field="available_capacity")
    if not _is_canonical_unsigned_int(liq_snapshot):
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE,
                             missing_or_invalid_field="liquidity_snapshot_epoch_ms")
    if not _is_canonical_unsigned_int(liq_tolerance):
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE,
                             missing_or_invalid_field="evidence_epoch_tolerance_ms")
    if not _is_canonical_unsigned_decimal(env_observed_size):
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE,
                             missing_or_invalid_field="observed_size")
    if not _is_canonical_unsigned_int(env_observed_at):
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE,
                             missing_or_invalid_field="observed_at_epoch_ms")

    # local ephemeral magnitudes (grammar guarantees Decimal/int never raise); inputs never mutated
    local_liq_size = _Decimal(liq_observed_size)
    local_liq_capacity = _Decimal(liq_available_capacity)
    local_env_size = _Decimal(env_observed_size)
    if local_liq_size == 0:
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE,
                             missing_or_invalid_field="observed_size")
    if local_liq_capacity == 0:
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE,
                             missing_or_invalid_field="available_capacity")
    if local_env_size == 0:
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE,
                             missing_or_invalid_field="observed_size")

    # --- branch priority 5: identity match (exact strings + size-magnitude binding) ---
    for name in _IDENTITY_FIELDS:
        env_value = getattr(evidence_envelope, name, _MISSING)
        liq_value = getattr(liquidity_evidence, name, _MISSING)
        if env_value is _MISSING or liq_value is _MISSING or env_value != liq_value:
            return _gate_blocked(evidence_envelope=evidence_envelope,
                                 reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_IDENTITY_MISMATCH,
                                 missing_or_invalid_field=name)
    if local_env_size != local_liq_size:
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_IDENTITY_MISMATCH,
                             missing_or_invalid_field="observed_size")

    # --- branch priority 6: unit binding (envelope size unit == size unit == capacity unit) ---
    if evidence_envelope.size_unit != liq_observed_size_unit:
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_UNIT_MISMATCH,
                             missing_or_invalid_field="size_unit")
    if liq_observed_size_unit != liq_capacity_unit:
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_UNIT_MISMATCH,
                             missing_or_invalid_field="capacity_unit")

    # --- branch priority 7: deterministic staleness (no clock; local int magnitudes only) ---
    if not (abs(int(env_observed_at) - int(liq_snapshot)) <= int(liq_tolerance)):
        return _gate_blocked(evidence_envelope=evidence_envelope,
                             reason_code=LIQUIDITY_CAPACITY_GATE_BLOCKED_STALE_EVIDENCE,
                             missing_or_invalid_field="liquidity_snapshot_epoch_ms")

    # --- branch priority 8/9: inclusive capacity sufficiency ---
    if local_env_size <= local_liq_capacity:
        # sufficient (equal capacity is sufficient): the identical envelope (no wrap, copy, or mutate)
        return evidence_envelope
    # valid, bound, fresh, positive capacity below the observed size
    return _gate_no_eligible(evidence_envelope=evidence_envelope)


class LiquidityCapacityGate:
    """Stateless, non-carrier namespace for the liquidity-capacity gate.

    Carries no state and requires no construction; the runtime entrypoint is the pure function
    :func:`liquidity_capacity_preflight`, exposed here as a static method.
    """

    __slots__ = ()

    preflight = staticmethod(liquidity_capacity_preflight)
