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
