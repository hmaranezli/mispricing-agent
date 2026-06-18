"""phase5/liquidity_capacity_evidence_boundary.py — Slice 1 atomic implementation of the
`phase5_liquidity_capacity_evidence_boundary` component: `LiquidityCapacityEvidenceContext`.

Per the component planning artifact
(`phase5_liquidity_capacity_evidence_boundary_implementation_planning.md`), this implements ONLY a
frozen, repr-safe, anti-truthiness, anti-coercion, factory-only carrier that wraps exactly the
explicitly supplied liquidity/depth capacity evidence. The gate slice is a separate, separately
authorized task and is deliberately NOT implemented in this module.

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
