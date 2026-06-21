"""phase6_2_shadow_intent/logical_model.py — Phase 6.2 Slice A logical model.

Frozen, methodless logical types plus closed structural validation for the sealed scenario-definition
artifact, exactly per the ratified Gate A field-shape charter
(``docs/handoff/phase6_2_shadow_intent_definition_artifact_field_shape_charter.md``, ``5dc757c``) as
corrected by the predecessor option-sum charter
(``docs/handoff/phase6_2_gate_a_predecessor_option_sum_targeted_correction_charter.md``, ``1071067``),
with field spellings cross-checked against the Gate B canonical-encoding charter (``474cc6f``), and the
closed lifecycle-state vocabulary from the lifecycle charter (``e9995e7`` §4, reaffirmed through
``457d279``).

Scope (Slice A of ``docs/handoff/phase6_2_reconstruction_runtime_tdd_planning_slice_charter.md``): frozen
exact types, keyword-only constructors, and closed structural validation **only**. There are no bytes, no
digest, no file I/O, no S1 parsing, no predicates, no replay step, and no reconstruction fold (those are
Slices B–F). Opaque values are preserved **verbatim** — no normalization, inference, semantic parsing,
identity invention, observed S1 facts, actionability, or shared mutable state.

The shadow-intent *slot* / *snapshot* CONTAINER shape is deliberately absent: no ratified charter pins its
exact field set, so per Slice A's "invent nothing" rule only the source-proven closed lifecycle-state
**vocabulary** value type is provided here; the container DTO awaits its own field-shape charter.
"""
import decimal
from dataclasses import dataclass, fields as _dataclass_fields
from types import MappingProxyType


LOGICAL_MODEL_COMPONENT_NAME = "phase6_2_shadow_intent_logical_model"

# --- closed orientation vocabulary (5dc757c §7) --------------------------------------------------
POSITIVE_EXPOSURE = "POSITIVE_EXPOSURE"
NEGATIVE_EXPOSURE = "NEGATIVE_EXPOSURE"
INERT_STATE = "INERT_STATE"
_DIRECTIONAL_ORIENTATIONS = frozenset({POSITIVE_EXPOSURE, NEGATIVE_EXPOSURE})

# --- closed lifecycle-state vocabulary (e9995e7 §4) ----------------------------------------------
AUDIT_REPLAYED = "AUDIT_REPLAYED"
INTENT_RECORDED = "INTENT_RECORDED"
HYPOTHETICAL_CONDITION_MET = "HYPOTHETICAL_CONDITION_MET"
INTENT_EXPIRED = "INTENT_EXPIRED"
INTENT_RETIRED = "INTENT_RETIRED"
CLOSED_LIFECYCLE_STATES = frozenset({
    AUDIT_REPLAYED, INTENT_RECORDED, HYPOTHETICAL_CONDITION_MET, INTENT_EXPIRED, INTENT_RETIRED,
})


class LogicalModelError(ValueError):
    """Raised for any closed structural-validation failure in the Phase 6.2 logical model.

    A single closed error surface keeps the (type vs value) distinction internal: callers assert a
    structural rejection, not a Python error taxonomy (which a later slice may refine).
    """


def _require_opaque_text(name, value):
    """An opaque text scalar is exactly a ``str``, preserved verbatim (no normalization/inference)."""
    if type(value) is not str:
        raise LogicalModelError(
            "field {!r} must be opaque text (str), not {}".format(name, type(value).__name__)
        )
    return value


def _require_non_negative_int_ms(name, value):
    """Exact non-negative integer milliseconds; ``bool`` is not an integer here (``type(True) is bool``)."""
    if type(value) is not int:
        raise LogicalModelError(
            "field {!r} must be an exact int (milliseconds), not {}".format(name, type(value).__name__)
        )
    if value < 0:
        raise LogicalModelError("field {!r} must be a non-negative integer".format(name))
    return value


def _require_finite_decimal(name, value):
    """Exact-decimal semantics: a finite ``decimal.Decimal`` (binary float, NaN, and infinity rejected)."""
    if type(value) is not decimal.Decimal:
        raise LogicalModelError(
            "field {!r} must be an exact decimal.Decimal, not {}".format(name, type(value).__name__)
        )
    if not value.is_finite():
        raise LogicalModelError("field {!r} must be a finite decimal (no NaN/Infinity)".format(name))
    return value


def validate_lifecycle_state(value):
    """Return ``value`` if it is exactly one of the closed lifecycle states, else raise."""
    if type(value) is not str or value not in CLOSED_LIFECYCLE_STATES:
        raise LogicalModelError("invalid lifecycle state: {!r}".format(value))
    return value


# --- OpaqueSilverPairKey (5dc757c §2 / 474cc6f §2) -----------------------------------------------
@dataclass(frozen=True)
class OpaqueSilverPairKey:
    """The two opaque text components of the borrowed S1 Silver pair, carried verbatim.

    Frozen and hashable so it can key the definitions map. The position component stays opaque text and is
    never decoded as an integer (``b06d7ed`` §6).
    """

    silver_artifact_locator_text: object
    silver_physical_record_position_text: object


def make_opaque_silver_pair_key(*, silver_artifact_locator_text, silver_physical_record_position_text):
    _require_opaque_text("silver_artifact_locator_text", silver_artifact_locator_text)
    _require_opaque_text("silver_physical_record_position_text", silver_physical_record_position_text)
    return OpaqueSilverPairKey(
        silver_artifact_locator_text=silver_artifact_locator_text,
        silver_physical_record_position_text=silver_physical_record_position_text,
    )


# --- predecessor option-sum (1071067 §4) ---------------------------------------------------------
@dataclass(frozen=True)
class NoPredecessor:
    """Closed variant: the first lineage member carries no predecessor (zero payload fields)."""


@dataclass(frozen=True)
class PredecessorReference:
    """Closed variant: exactly one caller-supplied opaque predecessor reference."""

    opaque_reference: object


def make_predecessor_reference(*, opaque_reference):
    _require_opaque_text("opaque_reference", opaque_reference)
    return PredecessorReference(opaque_reference=opaque_reference)


def _require_predecessor_option(value):
    """The predecessor field is always present and is exactly one closed option variant."""
    if type(value) is NoPredecessor:
        return value
    if type(value) is PredecessorReference:
        _require_opaque_text("opaque_reference", value.opaque_reference)
        return value
    raise LogicalModelError(
        "predecessor_artifact_version_reference must be NoPredecessor or PredecessorReference, not {}".format(
            type(value).__name__
        )
    )


# --- closed definition variants (5dc757c §6/§7) --------------------------------------------------
@dataclass(frozen=True)
class DirectionalShadowIntentDefinition:
    """Directional declared counterfactual: orientation + passive boundary (magnitude + unit) + window."""

    exposure_orientation: object
    passive_boundary_magnitude: object
    boundary_unit_context: object
    hypothetical_window_duration_ms: object


@dataclass(frozen=True)
class InertShadowIntentDefinition:
    """Inert declared counterfactual: orientation INERT_STATE + window. No boundary/unit by construction."""

    exposure_orientation: object
    hypothetical_window_duration_ms: object


def make_directional_shadow_intent_definition(
    *, exposure_orientation, passive_boundary_magnitude, boundary_unit_context, hypothetical_window_duration_ms
):
    if exposure_orientation not in _DIRECTIONAL_ORIENTATIONS:
        raise LogicalModelError(
            "directional exposure_orientation must be POSITIVE_EXPOSURE or NEGATIVE_EXPOSURE, not {!r}".format(
                exposure_orientation
            )
        )
    _require_finite_decimal("passive_boundary_magnitude", passive_boundary_magnitude)
    _require_opaque_text("boundary_unit_context", boundary_unit_context)
    _require_non_negative_int_ms("hypothetical_window_duration_ms", hypothetical_window_duration_ms)
    return DirectionalShadowIntentDefinition(
        exposure_orientation=exposure_orientation,
        passive_boundary_magnitude=passive_boundary_magnitude,
        boundary_unit_context=boundary_unit_context,
        hypothetical_window_duration_ms=hypothetical_window_duration_ms,
    )


def make_inert_shadow_intent_definition(*, exposure_orientation, hypothetical_window_duration_ms):
    if exposure_orientation != INERT_STATE:
        raise LogicalModelError(
            "inert exposure_orientation must be exactly INERT_STATE, not {!r}".format(exposure_orientation)
        )
    _require_non_negative_int_ms("hypothetical_window_duration_ms", hypothetical_window_duration_ms)
    return InertShadowIntentDefinition(
        exposure_orientation=exposure_orientation,
        hypothetical_window_duration_ms=hypothetical_window_duration_ms,
    )


def _require_definition(value):
    if type(value) is DirectionalShadowIntentDefinition or type(value) is InertShadowIntentDefinition:
        return value
    raise LogicalModelError(
        "definition must be a Directional or Inert ShadowIntentDefinition, not {}".format(type(value).__name__)
    )


# --- artifact envelope (5dc757c §3 / 1071067 §3) -------------------------------------------------
@dataclass(frozen=True)
class ShadowIntentDefinitionArtifact:
    """The closed five-field sealed scenario-definition artifact (always five fields).

    ``definitions_by_silver_pair`` is an immutable finite mapping (a read-only proxy) keyed only by the
    exact ``OpaqueSilverPairKey``; duplicate keys are rejected at construction; an empty map is valid.
    """

    artifact_field_shape_version_reference: object
    artifact_version_reference: object
    declarer_opaque_reference: object
    predecessor_artifact_version_reference: object
    definitions_by_silver_pair: object


def make_shadow_intent_definition_artifact(
    *,
    artifact_field_shape_version_reference,
    artifact_version_reference,
    declarer_opaque_reference,
    predecessor_artifact_version_reference,
    definition_entries,
):
    """Build one validated ``ShadowIntentDefinitionArtifact`` from an explicit tuple of entries.

    ``definition_entries`` is an ordered tuple of ``(OpaqueSilverPairKey, definition)`` pairs; ordering
    carries no semantic meaning but is required so duplicate keys are detectable before map construction
    (a duplicate is rejected — no first/last-wins/merge). The resulting map is wrapped read-only; the
    local dict is not retained, so the stored mapping cannot be mutated through any external handle.
    """
    _require_opaque_text("artifact_field_shape_version_reference", artifact_field_shape_version_reference)
    _require_opaque_text("artifact_version_reference", artifact_version_reference)
    _require_opaque_text("declarer_opaque_reference", declarer_opaque_reference)
    _require_predecessor_option(predecessor_artifact_version_reference)

    if type(definition_entries) is not tuple:
        raise LogicalModelError(
            "definition_entries must be a tuple of (OpaqueSilverPairKey, definition) pairs, not {}".format(
                type(definition_entries).__name__
            )
        )
    built = {}
    for entry in definition_entries:
        if type(entry) is not tuple or len(entry) != 2:
            raise LogicalModelError("each definition entry must be a (key, definition) 2-tuple")
        key, definition = entry
        if type(key) is not OpaqueSilverPairKey:
            raise LogicalModelError(
                "definition entry key must be an exact OpaqueSilverPairKey, not {}".format(type(key).__name__)
            )
        _require_definition(definition)
        if key in built:
            raise LogicalModelError("duplicate Silver-pair key in definition_entries is structurally invalid")
        built[key] = definition

    return ShadowIntentDefinitionArtifact(
        artifact_field_shape_version_reference=artifact_field_shape_version_reference,
        artifact_version_reference=artifact_version_reference,
        declarer_opaque_reference=declarer_opaque_reference,
        predecessor_artifact_version_reference=predecessor_artifact_version_reference,
        definitions_by_silver_pair=MappingProxyType(built),
    )


# Defensive guard: the envelope must remain the closed five-field contract.
_EXPECTED_ENVELOPE_FIELDS = (
    "artifact_field_shape_version_reference",
    "artifact_version_reference",
    "declarer_opaque_reference",
    "predecessor_artifact_version_reference",
    "definitions_by_silver_pair",
)
assert tuple(f.name for f in _dataclass_fields(ShadowIntentDefinitionArtifact)) == _EXPECTED_ENVELOPE_FIELDS
