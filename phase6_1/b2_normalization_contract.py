"""phase6_1/b2_normalization_contract.py — Phase 6.1 B2 typed structural contract.

Implements ONLY the narrow B1/B2 seam contract: three frozen, slotted, init-blocked carriers and their
keyword-only, exact-type, fail-fast factories. Authored under
`docs/handoff/phase6_1_b2_normalization_boundary_charter.md`.

Carriers:
  - PublicRawSnapshotRecord    — the immutable, provenance-tagged raw snapshot (B1 -> B2 input);
  - UnitBoundMagnitude         — a magnitude bound atomically to its unit (a magnitude alone cannot
                                 exist);
  - NormalizedEvidenceMaterial — the B2 output; references the raw snapshot BY IDENTITY and carries
                                 only tuple-bound unit/magnitude values plus an epoch tolerance.

This slice pins SHAPE ONLY. It performs no field mapping, no magnitude comparison, no chain wiring. It
imports nothing from Phase 5, instantiates no Slice-0 carrier, writes no output, reads no environment,
and does no network or file access. Exact-type discipline only (`type(value) is ExactType`); no silent
coercion; no default fallbacks; missing/malformed fields fail fast.
"""
from dataclasses import dataclass, fields as dataclass_fields


B2_NORMALIZATION_CONTRACT_COMPONENT_NAME = "phase6_1_b2_normalization_contract"
B2_NORMALIZATION_CONTRACT_BOUNDARY_VERSION = "phase6_1.b2_normalization_contract.v0"


class B2NormalizationTypeError(TypeError):
    """Raised for direct construction or a wrong-typed field value at a factory."""


class B2NormalizationValueError(ValueError):
    """Raised for a correctly-typed but out-of-contract value (empty, whitespace, or negative)."""


class B2NormalizationTruthinessError(TypeError):
    """Raised when a B2 carrier is used in a truthiness/length context."""


class B2NormalizationCoercionError(TypeError):
    """Raised when a B2 carrier is coerced to a number, string, or bytes."""


# --- shared anti-coercion behavior (no metaclass; one mixin of dunders) ---------------------------

class _AntiCoercion:
    __slots__ = ()

    def __bool__(self):
        raise B2NormalizationTruthinessError("B2 carrier must not be evaluated for truthiness.")

    def __len__(self):
        raise B2NormalizationTruthinessError("B2 carrier has no length; inspect fields instead.")

    def __int__(self):
        raise B2NormalizationCoercionError("B2 carrier must not be coerced to int.")

    def __float__(self):
        raise B2NormalizationCoercionError("B2 carrier must not be coerced to a real number.")

    def __complex__(self):
        raise B2NormalizationCoercionError("B2 carrier must not be coerced to complex.")

    def __index__(self):
        raise B2NormalizationCoercionError("B2 carrier must not be coerced to an index.")

    def __str__(self):
        raise B2NormalizationCoercionError("B2 carrier must not be coerced to str.")

    def __bytes__(self):
        raise B2NormalizationCoercionError("B2 carrier must not be coerced to bytes.")


@dataclass(frozen=True, repr=False, init=False, slots=True, eq=False)
class PublicRawSnapshotRecord(_AntiCoercion):
    """Immutable, provenance-tagged raw snapshot. Construct only through
    :func:`make_public_raw_snapshot_record`; direct construction is physically blocked."""

    component_name: object
    boundary_version: object
    source_artifact: object
    source_field: object
    venue: object
    pair: object
    retrieval_epoch_ms: object
    raw_snapshot_identity: object
    field_payload: object

    def __init__(self, *args, **kwargs):
        raise B2NormalizationTypeError(
            "PublicRawSnapshotRecord cannot be constructed directly; use "
            "make_public_raw_snapshot_record(...)."
        )

    def __repr__(self):
        return "PublicRawSnapshotRecord(raw_snapshot_identity={!r})".format(
            object.__getattribute__(self, "raw_snapshot_identity")
        )


@dataclass(frozen=True, repr=False, init=False, slots=True, eq=False)
class UnitBoundMagnitude(_AntiCoercion):
    """A magnitude bound atomically to its unit. Construct only through
    :func:`make_unit_bound_magnitude`; a magnitude can never exist apart from its unit."""

    component_name: object
    boundary_version: object
    magnitude: object
    unit: object

    def __init__(self, *args, **kwargs):
        raise B2NormalizationTypeError(
            "UnitBoundMagnitude cannot be constructed directly; use make_unit_bound_magnitude(...)."
        )

    def __repr__(self):
        return "UnitBoundMagnitude(unit={!r})".format(object.__getattribute__(self, "unit"))


@dataclass(frozen=True, repr=False, init=False, slots=True, eq=False)
class NormalizedEvidenceFieldBinding(_AntiCoercion):
    """One normalized evidence value bound explicitly to its semantic field name and raw source field.
    Construct only through :func:`make_normalized_evidence_field_binding`. Carrying the names on the
    binding removes any reliance on tuple position to infer meaning."""

    component_name: object
    boundary_version: object
    normalized_field_name: object
    source_field: object
    unit_bound_magnitude: object

    def __init__(self, *args, **kwargs):
        raise B2NormalizationTypeError(
            "NormalizedEvidenceFieldBinding cannot be constructed directly; use "
            "make_normalized_evidence_field_binding(...)."
        )

    def __repr__(self):
        return "NormalizedEvidenceFieldBinding(normalized_field_name={!r})".format(
            object.__getattribute__(self, "normalized_field_name")
        )


@dataclass(frozen=True, repr=False, init=False, slots=True, eq=False)
class NormalizedEvidenceMaterial(_AntiCoercion):
    """B2 output. References the raw snapshot BY IDENTITY; carries a tuple of explicitly named
    field bindings plus an epoch tolerance. Construct only through
    :func:`make_normalized_evidence_material`."""

    component_name: object
    boundary_version: object
    raw_snapshot: object
    normalized_field_bindings: object
    evidence_epoch_tolerance_ms: object

    def __init__(self, *args, **kwargs):
        raise B2NormalizationTypeError(
            "NormalizedEvidenceMaterial cannot be constructed directly; use "
            "make_normalized_evidence_material(...)."
        )

    def __repr__(self):
        return "NormalizedEvidenceMaterial(boundary_version={!r})".format(
            object.__getattribute__(self, "boundary_version")
        )


# --- validation helpers (exact-type, fail-fast, no coercion) --------------------------------------

def _require_str(name, value):
    if type(value) is not str:
        raise B2NormalizationTypeError(
            "field {!r} must be a str, not {}".format(name, type(value).__name__)
        )
    if value.strip() == "":
        raise B2NormalizationValueError(
            "field {!r} must be a non-empty, non-whitespace string".format(name)
        )


def _require_non_negative_int(name, value):
    # bool is rejected because ``type(True) is bool`` (not int).
    if type(value) is not int:
        raise B2NormalizationTypeError(
            "field {!r} must be an exact int, not {}".format(name, type(value).__name__)
        )
    if value < 0:
        raise B2NormalizationValueError(
            "field {!r} must be a non-negative integer".format(name)
        )


_REJECTED_CONTAINER_TYPES = (list, dict, set, frozenset, bytearray)


def _require_tuple_only(name, value):
    """Top-level must be a tuple; no list/dict/set may appear anywhere within. Scalars and nested
    tuples are permitted. Performs no derivation — a pure shape check."""
    if type(value) is not tuple:
        raise B2NormalizationTypeError(
            "field {!r} must be a tuple, not {}".format(name, type(value).__name__)
        )
    stack = [value]
    while stack:
        current = stack.pop()
        for element in current:
            if type(element) is tuple:
                stack.append(element)
            elif type(element) in _REJECTED_CONTAINER_TYPES:
                raise B2NormalizationTypeError(
                    "field {!r} must contain tuples and scalars only; a mutable container was "
                    "found".format(name)
                )


# --- keyword-only factories -----------------------------------------------------------------------

def make_public_raw_snapshot_record(
    *,
    source_artifact,
    source_field,
    venue,
    pair,
    retrieval_epoch_ms,
    raw_snapshot_identity,
    field_payload,
):
    """Build one :class:`PublicRawSnapshotRecord`. All provenance fields are exact non-empty strings;
    ``retrieval_epoch_ms`` is an exact non-negative UTC millisecond int; ``field_payload`` is tuple-only
    replay material. Nothing is mapped or derived."""
    _require_str("source_artifact", source_artifact)
    _require_str("source_field", source_field)
    _require_str("venue", venue)
    _require_str("pair", pair)
    _require_non_negative_int("retrieval_epoch_ms", retrieval_epoch_ms)
    _require_str("raw_snapshot_identity", raw_snapshot_identity)
    _require_tuple_only("field_payload", field_payload)

    record = object.__new__(PublicRawSnapshotRecord)
    object.__setattr__(record, "component_name", B2_NORMALIZATION_CONTRACT_COMPONENT_NAME)
    object.__setattr__(record, "boundary_version", B2_NORMALIZATION_CONTRACT_BOUNDARY_VERSION)
    object.__setattr__(record, "source_artifact", source_artifact)
    object.__setattr__(record, "source_field", source_field)
    object.__setattr__(record, "venue", venue)
    object.__setattr__(record, "pair", pair)
    object.__setattr__(record, "retrieval_epoch_ms", retrieval_epoch_ms)
    object.__setattr__(record, "raw_snapshot_identity", raw_snapshot_identity)
    object.__setattr__(record, "field_payload", field_payload)
    return record


def make_unit_bound_magnitude(*, magnitude, unit):
    """Build one :class:`UnitBoundMagnitude`. Both ``magnitude`` and ``unit`` are required exact
    non-empty strings; omitting ``unit`` is a missing required argument (a magnitude alone is rejected)."""
    _require_str("magnitude", magnitude)
    _require_str("unit", unit)

    bound = object.__new__(UnitBoundMagnitude)
    object.__setattr__(bound, "component_name", B2_NORMALIZATION_CONTRACT_COMPONENT_NAME)
    object.__setattr__(bound, "boundary_version", B2_NORMALIZATION_CONTRACT_BOUNDARY_VERSION)
    object.__setattr__(bound, "magnitude", magnitude)
    object.__setattr__(bound, "unit", unit)
    return bound


def make_normalized_evidence_field_binding(*, normalized_field_name, source_field, unit_bound_magnitude):
    """Build one :class:`NormalizedEvidenceFieldBinding`. ``normalized_field_name`` and ``source_field``
    are exact non-empty strings; ``unit_bound_magnitude`` is an exact :class:`UnitBoundMagnitude`
    referenced by identity. All three are required — a magnitude is never carried without its names."""
    _require_str("normalized_field_name", normalized_field_name)
    _require_str("source_field", source_field)
    if type(unit_bound_magnitude) is not UnitBoundMagnitude:
        raise B2NormalizationTypeError(
            "unit_bound_magnitude must be an exact UnitBoundMagnitude, not {}".format(
                type(unit_bound_magnitude).__name__
            )
        )

    binding = object.__new__(NormalizedEvidenceFieldBinding)
    object.__setattr__(binding, "component_name", B2_NORMALIZATION_CONTRACT_COMPONENT_NAME)
    object.__setattr__(binding, "boundary_version", B2_NORMALIZATION_CONTRACT_BOUNDARY_VERSION)
    object.__setattr__(binding, "normalized_field_name", normalized_field_name)
    object.__setattr__(binding, "source_field", source_field)
    object.__setattr__(binding, "unit_bound_magnitude", unit_bound_magnitude)
    return binding


def _require_field_binding_tuple(name, value):
    """Exact tuple of exact NormalizedEvidenceFieldBinding, with unique normalized_field_name values.
    Meaning is carried on each binding, never inferred from tuple position."""
    if type(value) is not tuple:
        raise B2NormalizationTypeError(
            "field {!r} must be a tuple, not {}".format(name, type(value).__name__)
        )
    seen_field_names = set()
    for element in value:
        if type(element) is not NormalizedEvidenceFieldBinding:
            raise B2NormalizationTypeError(
                "field {!r} must contain only exact NormalizedEvidenceFieldBinding values, not "
                "{}".format(name, type(element).__name__)
            )
        field_name = element.normalized_field_name
        if field_name in seen_field_names:
            raise B2NormalizationValueError(
                "field {!r} has a duplicate normalized_field_name {!r}".format(name, field_name)
            )
        seen_field_names.add(field_name)


def make_normalized_evidence_material(
    *, raw_snapshot, normalized_field_bindings, evidence_epoch_tolerance_ms
):
    """Build one :class:`NormalizedEvidenceMaterial`. ``raw_snapshot`` is referenced by identity (exact
    :class:`PublicRawSnapshotRecord`); ``normalized_field_bindings`` is a tuple of exact
    :class:`NormalizedEvidenceFieldBinding` with unique ``normalized_field_name`` values;
    ``evidence_epoch_tolerance_ms`` is an exact non-negative int where ``0`` is a valid strict match and
    ``None``/negative/wrong-type is malformed. Nothing is derived."""
    if type(raw_snapshot) is not PublicRawSnapshotRecord:
        raise B2NormalizationTypeError(
            "raw_snapshot must be an exact PublicRawSnapshotRecord, not {}".format(
                type(raw_snapshot).__name__
            )
        )
    _require_field_binding_tuple("normalized_field_bindings", normalized_field_bindings)
    _require_non_negative_int("evidence_epoch_tolerance_ms", evidence_epoch_tolerance_ms)

    material = object.__new__(NormalizedEvidenceMaterial)
    object.__setattr__(material, "component_name", B2_NORMALIZATION_CONTRACT_COMPONENT_NAME)
    object.__setattr__(material, "boundary_version", B2_NORMALIZATION_CONTRACT_BOUNDARY_VERSION)
    object.__setattr__(material, "raw_snapshot", raw_snapshot)
    object.__setattr__(material, "normalized_field_bindings", normalized_field_bindings)
    object.__setattr__(material, "evidence_epoch_tolerance_ms", evidence_epoch_tolerance_ms)
    return material


# Defensive guards: the declared field sets must remain closed contracts.
assert tuple(f.name for f in dataclass_fields(PublicRawSnapshotRecord)) == (
    "component_name", "boundary_version", "source_artifact", "source_field", "venue", "pair",
    "retrieval_epoch_ms", "raw_snapshot_identity", "field_payload",
)
assert tuple(f.name for f in dataclass_fields(UnitBoundMagnitude)) == (
    "component_name", "boundary_version", "magnitude", "unit",
)
assert tuple(f.name for f in dataclass_fields(NormalizedEvidenceFieldBinding)) == (
    "component_name", "boundary_version", "normalized_field_name", "source_field",
    "unit_bound_magnitude",
)
assert tuple(f.name for f in dataclass_fields(NormalizedEvidenceMaterial)) == (
    "component_name", "boundary_version", "raw_snapshot", "normalized_field_bindings",
    "evidence_epoch_tolerance_ms",
)
