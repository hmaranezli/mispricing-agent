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
