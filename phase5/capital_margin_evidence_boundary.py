"""phase5/capital_margin_evidence_boundary.py — Slice 1 atomic implementation of the
`phase5_capital_margin_evidence_boundary` component: `CapitalMarginEvidenceContext`.

Per the component planning artifact
(`phase5_capital_margin_evidence_boundary_implementation_planning.md`), this implements ONLY a frozen,
repr-safe, anti-truthiness, anti-coercion, factory-only, slotted carrier that wraps exactly the
explicitly supplied capital/margin evidence. The gate slice is a separate, separately authorized task
and is deliberately NOT implemented in this module.

The capital/margin boundary is a ledger auditor, and that audit belongs entirely to the future gate;
this carrier audits nothing. It is strictly a supplied-evidence descriptor. Every user-supplied field
is an exact, non-empty, non-whitespace ``str`` (exact-type only — ``type(value) is str``, so str
subclasses, ``None``, ``bool``, ``int``, ``float``, ``complex``, ``bytes``, dicts, lists, tuples,
mappings, and duck-typed string-like objects are rejected), stored verbatim. The carrier performs NO
numeric, magnitude, or epoch parsing, NO grammar validation, NO comparison, NO derivation, and NO
decision: magnitude-like fields (``observed_size``, ``required_capital``, ``available_free_capital``)
and the scalar epoch fields (``required_capital_epoch_ms``,
``available_free_capital_snapshot_epoch_ms``, ``evidence_epoch_tolerance_ms``) are kept as exact
strings only, with their validity left entirely to the future gate.

Direct construction is physically blocked: the carrier is built only through
``make_capital_margin_evidence_context`` via ``object.__new__`` + ``object.__setattr__``; calling the
class itself raises. Instances are slotted (no ``__dict__``), so dynamic attribute injection is
rejected.
"""
from dataclasses import dataclass, fields as dataclass_fields

CAPITAL_MARGIN_EVIDENCE_BOUNDARY_COMPONENT_NAME = "phase5_capital_margin_evidence_boundary"
BOUNDARY_VERSION = "phase5.capital_margin_evidence_boundary.v0"

# The 20 caller-supplied string fields (component_name is fixed by the factory, not a parameter).
_USER_SUPPLIED_FIELDS = (
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "side",
    "observed_size",
    "observed_size_unit",
    "required_capital",
    "required_capital_unit",
    "available_free_capital",
    "available_free_capital_unit",
    "required_capital_epoch_ms",
    "available_free_capital_snapshot_epoch_ms",
    "evidence_epoch_tolerance_ms",
    "capital_scope_id",
    "source_contract",
    "source_artifact",
    "source_field",
    "capital_evidence_id",
    "boundary_version",
)


class CapitalMarginEvidenceContextTruthinessError(TypeError):
    """Raised when a CapitalMarginEvidenceContext is used in a truthiness/length context."""


class CapitalMarginEvidenceContextCoercionError(TypeError):
    """Raised when a CapitalMarginEvidenceContext is coerced to a number, string, or bytes."""


class CapitalMarginEvidenceContextTypeError(TypeError):
    """Raised for direct construction or for a wrong-typed field value at the factory."""


@dataclass(frozen=True, repr=False, init=False, slots=True, eq=False)
class CapitalMarginEvidenceContext:
    """A frozen, slotted, anti-coercion carrier wrapping explicitly supplied capital/margin evidence.

    Construct only through :func:`make_capital_margin_evidence_context`. Direct construction (no-arg,
    positional, or keyword) is physically blocked. The carrier holds only the explicitly supplied
    identity, size, capital scalars, snapshot/tolerance scalars, scope, and provenance; it audits
    nothing, compares nothing, derives nothing, and decides nothing.
    """

    component_name: object
    venue: object
    instrument_id: object
    base_asset: object
    quote_asset: object
    side: object
    observed_size: object
    observed_size_unit: object
    required_capital: object
    required_capital_unit: object
    available_free_capital: object
    available_free_capital_unit: object
    required_capital_epoch_ms: object
    available_free_capital_snapshot_epoch_ms: object
    evidence_epoch_tolerance_ms: object
    capital_scope_id: object
    source_contract: object
    source_artifact: object
    source_field: object
    capital_evidence_id: object
    boundary_version: object

    # --- direct construction is physically blocked (no-arg, positional, keyword) ---
    def __init__(self, *args, **kwargs):
        raise CapitalMarginEvidenceContextTypeError(
            "CapitalMarginEvidenceContext cannot be constructed directly; use "
            "make_capital_margin_evidence_context(...)."
        )

    # --- anti-truthiness ---
    def __bool__(self):
        raise CapitalMarginEvidenceContextTruthinessError(
            "CapitalMarginEvidenceContext must not be evaluated for truthiness; inspect fields."
        )

    def __len__(self):
        raise CapitalMarginEvidenceContextTruthinessError(
            "CapitalMarginEvidenceContext has no length; inspect fields instead."
        )

    # --- anti-coercion ---
    def __int__(self):
        raise CapitalMarginEvidenceContextCoercionError(
            "CapitalMarginEvidenceContext must not be coerced to int."
        )

    def __float__(self):
        raise CapitalMarginEvidenceContextCoercionError(
            "CapitalMarginEvidenceContext must not be coerced to a real number."
        )

    def __complex__(self):
        raise CapitalMarginEvidenceContextCoercionError(
            "CapitalMarginEvidenceContext must not be coerced to complex."
        )

    def __index__(self):
        raise CapitalMarginEvidenceContextCoercionError(
            "CapitalMarginEvidenceContext must not be coerced to an index."
        )

    def __str__(self):
        raise CapitalMarginEvidenceContextCoercionError(
            "CapitalMarginEvidenceContext must not be coerced to str."
        )

    def __bytes__(self):
        raise CapitalMarginEvidenceContextCoercionError(
            "CapitalMarginEvidenceContext must not be coerced to bytes."
        )

    # --- safe debug repr only (component_name + boundary_version; no identity/size/capital/epoch/
    #     scope/provenance leak; no sufficiency/readiness meaning) ---
    def __repr__(self):
        return (
            "CapitalMarginEvidenceContext(component_name={!r}, boundary_version={!r})".format(
                self.component_name, self.boundary_version
            )
        )


def _require_str_field(name, value):
    """Validate one field: exact str (TypeError), non-empty/non-whitespace (ValueError). Verbatim.

    Error messages use only the field name and ``type(value).__name__`` — never the value itself.
    """
    if type(value) is not str:
        raise CapitalMarginEvidenceContextTypeError(
            "field {!r} must be a str, not {}".format(name, type(value).__name__)
        )
    if value.strip() == "":
        raise ValueError(
            "field {!r} must be a non-empty, non-whitespace string".format(name)
        )


def make_capital_margin_evidence_context(
    *,
    venue,
    instrument_id,
    base_asset,
    quote_asset,
    side,
    observed_size,
    observed_size_unit,
    required_capital,
    required_capital_unit,
    available_free_capital,
    available_free_capital_unit,
    required_capital_epoch_ms,
    available_free_capital_snapshot_epoch_ms,
    evidence_epoch_tolerance_ms,
    capital_scope_id,
    source_contract,
    source_artifact,
    source_field,
    capital_evidence_id,
    boundary_version,
):
    """Keyword-only constructor for a single :class:`CapitalMarginEvidenceContext`.

    Every field must be an exact, non-empty, non-whitespace ``str`` (``type(value) is str`` — str
    subclasses rejected), preserved verbatim. The carrier performs no numeric, magnitude, or epoch
    parsing, no grammar validation, no comparison, and no derivation; magnitude-like and scalar epoch
    fields are kept as exact strings only. Error messages use only field names and
    ``type(value).__name__`` — never the value itself.
    """
    supplied = {
        "venue": venue,
        "instrument_id": instrument_id,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "side": side,
        "observed_size": observed_size,
        "observed_size_unit": observed_size_unit,
        "required_capital": required_capital,
        "required_capital_unit": required_capital_unit,
        "available_free_capital": available_free_capital,
        "available_free_capital_unit": available_free_capital_unit,
        "required_capital_epoch_ms": required_capital_epoch_ms,
        "available_free_capital_snapshot_epoch_ms": available_free_capital_snapshot_epoch_ms,
        "evidence_epoch_tolerance_ms": evidence_epoch_tolerance_ms,
        "capital_scope_id": capital_scope_id,
        "source_contract": source_contract,
        "source_artifact": source_artifact,
        "source_field": source_field,
        "capital_evidence_id": capital_evidence_id,
        "boundary_version": boundary_version,
    }
    for name in _USER_SUPPLIED_FIELDS:
        _require_str_field(name, supplied[name])

    ctx = object.__new__(CapitalMarginEvidenceContext)
    object.__setattr__(
        ctx, "component_name", CAPITAL_MARGIN_EVIDENCE_BOUNDARY_COMPONENT_NAME
    )
    for name in _USER_SUPPLIED_FIELDS:
        object.__setattr__(ctx, name, supplied[name])
    return ctx


# Defensive guard: the declared dataclass field set must remain the closed 21-field contract.
_EXPECTED_FIELD_NAMES = (
    "component_name",
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "side",
    "observed_size",
    "observed_size_unit",
    "required_capital",
    "required_capital_unit",
    "available_free_capital",
    "available_free_capital_unit",
    "required_capital_epoch_ms",
    "available_free_capital_snapshot_epoch_ms",
    "evidence_epoch_tolerance_ms",
    "capital_scope_id",
    "source_contract",
    "source_artifact",
    "source_field",
    "capital_evidence_id",
    "boundary_version",
)
assert tuple(f.name for f in dataclass_fields(CapitalMarginEvidenceContext)) == \
    _EXPECTED_FIELD_NAMES


# ===PHASE5-SLICE2-GATE-BOUNDARY===
# Slice 2: CapitalMarginGate / capital_margin_preflight
#
# A pure, offline, deterministic capital-sufficiency ledger auditor over exactly one
# PostProfitabilityEvidenceEnvelope, one CapitalMarginEvidenceContext, and one exact
# expected_capital_scope_id control scalar. It is an auditor, not a calculator: required_capital and
# available_free_capital are supplied evidence scalars that the gate only audits — it re-derives,
# models, and recomputes nothing by any economic formula. Outputs are exactly: the identical envelope
# (valid + identity-bound + unit-bound + fresh + inclusive-sufficient), an existing BlockedPacket
# (missing / malformed / identity-mismatch / unit-mismatch / stale supplied evidence), or an existing
# NoEligibleHaltPacket (valid bound fresh evidence whose free capital is zero or below the required
# capital). A programmatic wrong-path / misroute raises and never produces a packet. The gate reads
# only the allow-listed decision fields, parses magnitudes/epochs into LOCAL ephemeral values only,
# mutates neither input, builds no new packet schema, and never broadens sufficient capital into a
# trade-ready or order-placement claim. The carrier's source_*/capital_evidence_id/boundary_version
# are never used as packet provenance.
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
# (no sign, no exponent, no underscores, no commas, no leading zeros beyond a single "0"). NaN and
# Infinity never match, so non-finite magnitudes fail closed as malformed.
_GATE_UNSIGNED_DECIMAL = _re.compile(r"(0|[1-9]\d*)(\.\d+)?")
# Canonical unsigned integer: "0" or a non-zero-leading run (no sign, no decimal, no exponent).
_GATE_UNSIGNED_INT = _re.compile(r"0|[1-9]\d*")

GATE_SOURCE_CONTRACT = (
    "phase5_capital_margin_evidence_boundary_implementation_planning.md"
)

# Pinned reason vocabulary (planning-fixed; CAPITAL_MARGIN_GATE_ prefix only; exactly six; no aliases).
CAPITAL_MARGIN_GATE_BLOCKED_MISSING_CAPITAL_EVIDENCE = "CAPITAL_MARGIN_GATE_BLOCKED_MISSING_CAPITAL_EVIDENCE"
CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE = "CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE"
CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH = "CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH"
CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH = "CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH"
CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE = "CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE"
CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL = "CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL"

# NoEligible packet literals (explicit zero-or-shortfall free capital is the only V1 no-eligible fact).
_NO_ELIGIBLE_STATUS = "NO_ELIGIBLE"
_NO_ELIGIBLE_NEXT_ACTION = "HALT_BYPASS_NO_ELIGIBLE"

# The five explicit identity fields compared by exact, case-sensitive equality (no normalization);
# side is an identity comparison, so a side mismatch is an identity mismatch.
_CAPITAL_IDENTITY_FIELDS = ("venue", "instrument_id", "base_asset", "quote_asset", "side")

# The allow-listed capital-evidence decision fields the gate dereferences (zero-trust).
_CAPITAL_DECISION_FIELDS = (
    "venue",
    "instrument_id",
    "base_asset",
    "quote_asset",
    "side",
    "observed_size",
    "observed_size_unit",
    "required_capital",
    "required_capital_unit",
    "available_free_capital",
    "available_free_capital_unit",
    "required_capital_epoch_ms",
    "available_free_capital_snapshot_epoch_ms",
    "evidence_epoch_tolerance_ms",
    "capital_scope_id",
)

# Distinct from None: lets the gate tell a truly-absent attribute apart from an explicit None value.
_MISSING = object()


class CapitalMarginGateTypeError(TypeError):
    """Raised for a programmatic wrong-path / wrong-type input to the capital-margin gate."""


class MisroutedHaltCarrierError(TypeError):
    """Raised when a halt carrier is misrouted into the capital-margin gate boundary."""


def reject_misrouted_capital_halt_carrier(payload):
    """Fail closed if a halt carrier is misrouted into the capital-margin gate boundary.

    - Exact :class:`BlockedPacket` or exact :class:`NoEligibleHaltPacket` → raise
      :class:`MisroutedHaltCarrierError` (a misroute / integration bug, not a gate input).
    - Anything else → return ``None``; subclasses are NOT exact halt carriers.

    Exact-type checks only (no isinstance). An already-halted input is never converted into a new
    BlockedPacket/NoEligibleHaltPacket output; only its type name is used in the message.
    """
    if type(payload) is BlockedPacket:
        raise MisroutedHaltCarrierError(
            f"capital margin gate boundary must not receive a halt carrier; "
            f"got {type(payload).__name__}"
        )
    if type(payload) is NoEligibleHaltPacket:
        raise MisroutedHaltCarrierError(
            f"capital margin gate boundary must not receive a halt carrier; "
            f"got {type(payload).__name__}"
        )
    return None


def _capital_is_canonical_unsigned_decimal(value):
    """True only for an exact ``str`` matching the canonical unsigned decimal grammar (verbatim)."""
    return type(value) is str and _GATE_UNSIGNED_DECIMAL.fullmatch(value) is not None


def _capital_is_canonical_unsigned_int(value):
    """True only for an exact ``str`` matching the canonical unsigned integer grammar (verbatim)."""
    return type(value) is str and _GATE_UNSIGNED_INT.fullmatch(value) is not None


def _capital_gate_blocked(*, evidence_envelope, reason_code, missing_or_invalid_field):
    """Build a gate BlockedPacket via the existing factory — provenance from the evidence envelope."""
    return make_blocked_packet(
        component_name=CAPITAL_MARGIN_EVIDENCE_BOUNDARY_COMPONENT_NAME,
        origin_component=CAPITAL_MARGIN_EVIDENCE_BOUNDARY_COMPONENT_NAME,
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


def _capital_gate_no_eligible(*, evidence_envelope):
    """Build the gate NoEligibleHaltPacket via the existing factory — provenance from the envelope.

    The rejected-opportunity lineage (source_contract/source_artifact/source_field) is preserved from
    the :class:`PostProfitabilityEvidenceEnvelope`, never from the capital-evidence carrier.
    """
    return make_no_eligible_halt_packet(
        component_name=CAPITAL_MARGIN_EVIDENCE_BOUNDARY_COMPONENT_NAME,
        origin_component=CAPITAL_MARGIN_EVIDENCE_BOUNDARY_COMPONENT_NAME,
        origin_result_status=_NO_ELIGIBLE_STATUS,
        status=_NO_ELIGIBLE_STATUS,
        no_eligible_reason=CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL,
        source_contract=evidence_envelope.source_contract,
        source_artifact=evidence_envelope.source_artifact,
        source_field=evidence_envelope.source_field,
        deterministic_next_action=_NO_ELIGIBLE_NEXT_ACTION,
        boundary_version=BOUNDARY_VERSION,
    )


def capital_margin_preflight(*, evidence_envelope, capital_evidence, expected_capital_scope_id):
    """Pure capital-sufficiency ledger auditor over one envelope, one carrier, and one scope scalar.

    Returns the identical ``evidence_envelope`` on pass (valid identity/unit/staleness and inclusive
    sufficient capital); an existing :class:`BlockedPacket` for missing / malformed / identity-mismatch
    / unit-mismatch / stale supplied evidence; and an existing :class:`NoEligibleHaltPacket` when valid
    bound fresh evidence has zero free capital or required capital above the free capital. Programmatic
    wrong-path / wrong-type inputs raise :class:`CapitalMarginGateTypeError` or
    :class:`MisroutedHaltCarrierError` and never produce a packet. See
    ``phase5_capital_margin_evidence_boundary_implementation_planning.md``.

    The exact carrier instance is zero-trusted: defensive attribute access distinguishes a truly absent
    decision field (→ MISSING) from a present-but-malformed one (→ MALFORMED); it never becomes parsing
    tolerance, defaulting, coercion, or normalization. Magnitudes and epochs are parsed into LOCAL
    ephemeral values only; neither input is mutated. The carrier's provenance/id/boundary_version are
    never read.
    """
    # --- branch priority 1: programmatic wrong-path / misroute first ---
    reject_misrouted_capital_halt_carrier(evidence_envelope)
    reject_misrouted_capital_halt_carrier(capital_evidence)

    # --- branch priority 2: exact-type checks + control scalar (subclasses rejected) ---
    if type(evidence_envelope) is not PostProfitabilityEvidenceEnvelope:
        raise CapitalMarginGateTypeError(
            "capital_margin_preflight requires an exact PostProfitabilityEvidenceEnvelope, "
            f"not {type(evidence_envelope).__name__}"
        )
    if type(capital_evidence) is not CapitalMarginEvidenceContext:
        raise CapitalMarginGateTypeError(
            "capital_margin_preflight requires an exact CapitalMarginEvidenceContext, "
            f"not {type(capital_evidence).__name__}"
        )
    if type(expected_capital_scope_id) is not str:
        raise CapitalMarginGateTypeError(
            "capital_margin_preflight requires an exact str expected_capital_scope_id, "
            f"not {type(expected_capital_scope_id).__name__}"
        )
    if expected_capital_scope_id.strip() == "":
        raise CapitalMarginGateTypeError(
            "capital_margin_preflight requires a non-empty, non-whitespace expected_capital_scope_id"
        )

    # --- branch priority 3: zero-trust the allow-listed capital decision fields ---
    fields = {name: getattr(capital_evidence, name, _MISSING) for name in _CAPITAL_DECISION_FIELDS}
    for name in _CAPITAL_DECISION_FIELDS:
        if fields[name] is _MISSING:
            return _capital_gate_blocked(
                evidence_envelope=evidence_envelope,
                reason_code=CAPITAL_MARGIN_GATE_BLOCKED_MISSING_CAPITAL_EVIDENCE,
                missing_or_invalid_field=name,
            )

    cap_observed_size = fields["observed_size"]
    cap_required_capital = fields["required_capital"]
    cap_available_free_capital = fields["available_free_capital"]
    cap_required_epoch = fields["required_capital_epoch_ms"]
    cap_free_snapshot = fields["available_free_capital_snapshot_epoch_ms"]
    cap_tolerance = fields["evidence_epoch_tolerance_ms"]
    cap_observed_size_unit = fields["observed_size_unit"]
    cap_required_capital_unit = fields["required_capital_unit"]
    cap_available_free_capital_unit = fields["available_free_capital_unit"]
    cap_scope = fields["capital_scope_id"]

    env_observed_size = evidence_envelope.observed_size
    env_observed_at = evidence_envelope.observed_at_epoch_ms

    # --- branch priority 4: malformed grammar / scalar validity (fail closed; no exceptions) ---
    for fname, val in (
        ("observed_size", cap_observed_size),
        ("required_capital", cap_required_capital),
        ("available_free_capital", cap_available_free_capital),
    ):
        if not _capital_is_canonical_unsigned_decimal(val):
            return _capital_gate_blocked(
                evidence_envelope=evidence_envelope,
                reason_code=CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE,
                missing_or_invalid_field=fname,
            )
    for fname, val in (
        ("required_capital_epoch_ms", cap_required_epoch),
        ("available_free_capital_snapshot_epoch_ms", cap_free_snapshot),
        ("evidence_epoch_tolerance_ms", cap_tolerance),
    ):
        if not _capital_is_canonical_unsigned_int(val):
            return _capital_gate_blocked(
                evidence_envelope=evidence_envelope,
                reason_code=CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE,
                missing_or_invalid_field=fname,
            )
    if not _capital_is_canonical_unsigned_decimal(env_observed_size):
        return _capital_gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE,
            missing_or_invalid_field="observed_size",
        )
    if not _capital_is_canonical_unsigned_int(env_observed_at):
        return _capital_gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE,
            missing_or_invalid_field="observed_at_epoch_ms",
        )

    # local ephemeral magnitudes (grammar guarantees Decimal never raises); inputs never mutated
    local_observed_size = _Decimal(cap_observed_size)
    local_required = _Decimal(cap_required_capital)
    local_free = _Decimal(cap_available_free_capital)
    local_env_size = _Decimal(env_observed_size)

    # positivity: observed_size and required_capital must be strictly positive; free must be >= 0
    if local_observed_size <= 0:
        return _capital_gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE,
            missing_or_invalid_field="observed_size",
        )
    if local_required <= 0:
        return _capital_gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE,
            missing_or_invalid_field="required_capital",
        )
    if local_free < 0:
        return _capital_gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE,
            missing_or_invalid_field="available_free_capital",
        )

    # --- branch priority 5: identity match (exact strings incl. side + size magnitude + scope) ---
    for name in _CAPITAL_IDENTITY_FIELDS:
        env_value = getattr(evidence_envelope, name, _MISSING)
        cap_value = fields[name]
        if env_value is _MISSING or cap_value is _MISSING or env_value != cap_value:
            return _capital_gate_blocked(
                evidence_envelope=evidence_envelope,
                reason_code=CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH,
                missing_or_invalid_field=name,
            )
    if local_env_size != local_observed_size:
        return _capital_gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH,
            missing_or_invalid_field="observed_size",
        )
    if expected_capital_scope_id != cap_scope:
        return _capital_gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH,
            missing_or_invalid_field="capital_scope_id",
        )

    # --- branch priority 6: unit binding (envelope size unit == size unit; required unit == free) ---
    if evidence_envelope.size_unit != cap_observed_size_unit:
        return _capital_gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH,
            missing_or_invalid_field="observed_size_unit",
        )
    if cap_required_capital_unit != cap_available_free_capital_unit:
        return _capital_gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH,
            missing_or_invalid_field="required_capital_unit",
        )

    # --- branch priority 7: two independent deterministic staleness axes (no clock) ---
    if not (abs(int(env_observed_at) - int(cap_required_epoch)) <= int(cap_tolerance)):
        return _capital_gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE,
            missing_or_invalid_field="required_capital_epoch_ms",
        )
    if not (abs(int(env_observed_at) - int(cap_free_snapshot)) <= int(cap_tolerance)):
        return _capital_gate_blocked(
            evidence_envelope=evidence_envelope,
            reason_code=CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE,
            missing_or_invalid_field="available_free_capital_snapshot_epoch_ms",
        )

    # --- branch priority 8/9: explicit zero free capital, then inclusive sufficiency ---
    if local_free == 0:
        # explicit shortfall (free capital is zero while required capital is positive)
        return _capital_gate_no_eligible(evidence_envelope=evidence_envelope)
    if local_required <= local_free:
        # sufficient (equal capital is sufficient): the identical envelope (no wrap, copy, or mutate)
        return evidence_envelope
    # valid, bound, fresh, positive free capital below the required capital
    return _capital_gate_no_eligible(evidence_envelope=evidence_envelope)


class CapitalMarginGate:
    """Stateless, non-carrier namespace for the capital-margin gate.

    Carries no state and requires no construction; the runtime entrypoint is the pure function
    :func:`capital_margin_preflight`, exposed here as a static method.
    """

    __slots__ = ()

    preflight = staticmethod(capital_margin_preflight)
