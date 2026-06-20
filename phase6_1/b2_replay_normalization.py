"""phase6_1/b2_replay_normalization.py — Phase 6.1 B2 replay-artifact-only normalizer.

Implements ONLY `normalize_replay_snapshot_to_evidence_material`: a deterministic function that consumes
one exact :class:`PublicRawSnapshotRecord` and returns one :class:`NormalizedEvidenceMaterial`, built
from the existing B2 contract carriers. Authored under
`docs/handoff/phase6_1_b2_normalization_boundary_charter.md`.

Each field-entry in ``raw_snapshot.field_payload`` is a tuple of exact two-item label/value pairs.
Meaning is carried by the explicit labels (normalized_field_name, source_field, binding_role, magnitude,
unit) and by the binding fields — never by tuple position. ``binding_role`` is passed through verbatim
to the contract factory, which enforces its exact vocabulary; it is never inferred here. The optional
``zero_cost_evidence`` label is likewise passed through verbatim (None when absent) and never derived
from the magnitude. Magnitudes are carried verbatim as exact strings: no Decimal/float/int parsing, no
unit conversion, and no magnitude comparison happens here.

It imports nothing from Phase 5, builds no Slice-0 carrier, writes no output, reads no environment, and
performs no network or file access. Exact-type discipline only; no silent coercion; no default
fallbacks; missing/malformed input fails fast.
"""
from phase6_1.b2_normalization_contract import (
    PublicRawSnapshotRecord,
    make_unit_bound_magnitude,
    make_normalized_evidence_field_binding,
    make_normalized_evidence_material,
    B2NormalizationTypeError,
    B2NormalizationValueError,
)


_REQUIRED_LABELS = frozenset(
    ("normalized_field_name", "source_field", "binding_role", "magnitude", "unit")
)
# Optional labels may be present or absent. ``zero_cost_evidence`` is carrier-only metadata passed
# through verbatim (None when the label is absent); it is never inferred from any other label.
_OPTIONAL_LABELS = frozenset(("zero_cost_evidence",))
_ALLOWED_LABELS = _REQUIRED_LABELS | _OPTIONAL_LABELS


def _require_nonempty_str(name, value):
    if type(value) is not str:
        raise B2NormalizationTypeError(
            "{} must be a str, not {}".format(name, type(value).__name__)
        )
    if value.strip() == "":
        raise B2NormalizationValueError("{} must be a non-empty, non-whitespace string".format(name))


def _binding_from_entry(entry):
    """Project one field-entry (a tuple of exact two-item label/value pairs) into one
    NormalizedEvidenceFieldBinding. Labels address meaning; tuple position is ignored."""
    if type(entry) is not tuple:
        raise B2NormalizationTypeError(
            "each field-entry must be a tuple, not {}".format(type(entry).__name__)
        )
    extracted = {}
    for pair in entry:
        if type(pair) is not tuple or len(pair) != 2:
            raise B2NormalizationTypeError(
                "each field-entry item must be an exact two-item label/value tuple"
            )
        label = pair[0]
        value = pair[1]
        _require_nonempty_str("label", label)
        _require_nonempty_str("value", value)
        if label in extracted:
            raise B2NormalizationValueError(
                "duplicate label {!r} inside one field-entry".format(label)
            )
        if label not in _ALLOWED_LABELS:
            raise B2NormalizationValueError(
                "unknown label {!r} inside one field-entry".format(label)
            )
        extracted[label] = value

    if not _REQUIRED_LABELS <= frozenset(extracted):
        raise B2NormalizationValueError(
            "field-entry must carry exactly the required labels: normalized_field_name, "
            "source_field, binding_role, magnitude, unit"
        )

    unit_bound = make_unit_bound_magnitude(
        magnitude=extracted["magnitude"], unit=extracted["unit"]
    )
    # binding_role and the optional zero_cost_evidence are passed through verbatim (the latter is None
    # when its label is absent); the contract factory enforces vocabulary and role consistency.
    return make_normalized_evidence_field_binding(
        normalized_field_name=extracted["normalized_field_name"],
        source_field=extracted["source_field"],
        binding_role=extracted["binding_role"],
        unit_bound_magnitude=unit_bound,
        zero_cost_evidence=extracted.get("zero_cost_evidence"),
    )


def normalize_replay_snapshot_to_evidence_material(
    *, raw_snapshot, evidence_epoch_tolerance_ms, depth_source_reference=None
):
    """Normalize one exact :class:`PublicRawSnapshotRecord` into one
    :class:`NormalizedEvidenceMaterial`.

    ``evidence_epoch_tolerance_ms`` is validated FIRST — before any ``field_payload`` traversal, label
    extraction, binding construction, or material construction. ``0`` is a valid strict match;
    ``None``/negative/wrong-type is malformed. ``raw_snapshot`` must be exact; ``field_payload`` must be
    a non-empty tuple of field-entries. The raw snapshot is referenced by identity in the result.

    ``depth_source_reference`` is optional: ``None`` when absent (no fabricated stand-in), or an exact
    reader-produced depth-evidence record supplied by an explicit caller. It is threaded through
    verbatim by identity to the material contract, which validates its exact type and holds it by
    reference. Its fields are never inspected here, and no artifact is read here.
    """
    # --- tolerance validated FIRST (fail-fast ordering invariant) ---
    if type(evidence_epoch_tolerance_ms) is not int:
        raise B2NormalizationTypeError(
            "evidence_epoch_tolerance_ms must be an exact int, not {}".format(
                type(evidence_epoch_tolerance_ms).__name__
            )
        )
    if evidence_epoch_tolerance_ms < 0:
        raise B2NormalizationValueError(
            "evidence_epoch_tolerance_ms must be a non-negative integer"
        )

    if type(raw_snapshot) is not PublicRawSnapshotRecord:
        raise B2NormalizationTypeError(
            "raw_snapshot must be an exact PublicRawSnapshotRecord, not {}".format(
                type(raw_snapshot).__name__
            )
        )

    field_payload = raw_snapshot.field_payload
    if len(field_payload) == 0:
        raise B2NormalizationValueError("field_payload must contain at least one field-entry")

    bindings = []
    for entry in field_payload:
        bindings.append(_binding_from_entry(entry))

    return make_normalized_evidence_material(
        raw_snapshot=raw_snapshot,
        normalized_field_bindings=tuple(bindings),
        evidence_epoch_tolerance_ms=evidence_epoch_tolerance_ms,
        depth_source_reference=depth_source_reference,
    )
