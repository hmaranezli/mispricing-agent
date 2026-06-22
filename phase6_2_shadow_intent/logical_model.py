"""phase6_2_shadow_intent/logical_model.py — Phase 6.2 Slice A logical model.

Frozen, slotted, methodless logical types plus closed structural validation for the sealed
scenario-definition artifact, exactly per the ratified Gate A field-shape charter
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

Construction discipline: every field-bearing value type is ``frozen=True, slots=True, kw_only=True`` and
enforces its complete structural invariants in ``__post_init__`` using the same shared validators its
factory uses, so direct construction can never bypass validation; ``NoPredecessor`` is a genuine
zero-field slotted variant; and ``ShadowIntentDefinitionArtifact`` is **factory-only** (direct
construction with any args fails). All instances are slotted (no ``__dict__``). Structural-validation
failures surface as a single closed ``LogicalModelError``.

The shadow-intent lifecycle-slot / root-evidence / dual-snapshot value types are now implemented by the
Slice-A runtime extension at the bottom of this module — ``EstablishedRootContext``,
``EstablishedRootEvidence``, ``NoRootEvidence``, ``ShadowIntentLifecycleSlot``, the factory-only
``ShadowLifecycleSnapshot``, and the factory-only ``SeenTargetPairsSnapshot`` — per the ratified
field-shape charter chain (``85de568`` as superseded by ``38eccce`` / ``9fc7749`` / ``01331ec``). They are
passive Slice-A carriers only: no ``Step`` algorithm, lifecycle application, or replay-loop behavior lives
here (those remain Slice E/F).
"""
import decimal
import re
from dataclasses import dataclass, fields as _dataclass_fields
from types import MappingProxyType


LOGICAL_MODEL_COMPONENT_NAME = "phase6_2_shadow_intent_logical_model"

# --- closed orientation vocabulary (5dc757c §7) --------------------------------------------------
POSITIVE_EXPOSURE = "POSITIVE_EXPOSURE"
NEGATIVE_EXPOSURE = "NEGATIVE_EXPOSURE"
INERT_STATE = "INERT_STATE"
_DIRECTIONAL_ORIENTATIONS = frozenset({POSITIVE_EXPOSURE, NEGATIVE_EXPOSURE})

# --- declared hypothetical-window duration range (signed-64, e471f19) ----------------------------
MIN_HYPOTHETICAL_WINDOW_DURATION_MS = 0
MAX_HYPOTHETICAL_WINDOW_DURATION_MS = 9223372036854775807  # 2^63 - 1

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


# --- shared validators (used by both __post_init__ and the factory revalidation pass) -------------
def _require_opaque_text(name, value):
    """An opaque text scalar is exactly a ``str``, preserved verbatim (no normalization/inference)."""
    if type(value) is not str:
        raise LogicalModelError(
            "field {!r} must be opaque text (str), not {}".format(name, type(value).__name__)
        )
    return value


def _require_non_negative_int_ms(name, value):
    """Exact integer milliseconds within the inclusive signed-64 range ``[0, 2^63-1]`` (``e471f19``).

    ``bool`` is not an integer here (``type(True) is bool``); negative values and values above
    ``MAX_HYPOTHETICAL_WINDOW_DURATION_MS`` are rejected.
    """
    if type(value) is not int:
        raise LogicalModelError(
            "field {!r} must be an exact int (milliseconds), not {}".format(name, type(value).__name__)
        )
    if value < MIN_HYPOTHETICAL_WINDOW_DURATION_MS:
        raise LogicalModelError("field {!r} must be a non-negative integer".format(name))
    if value > MAX_HYPOTHETICAL_WINDOW_DURATION_MS:
        raise LogicalModelError(
            "field {!r} must be <= MAX_HYPOTHETICAL_WINDOW_DURATION_MS (2^63-1)".format(name)
        )
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


def _require_directional_orientation(value):
    """Exact type check precedes closed-set membership so unhashable/wrong-typed inputs never leak a
    raw ``TypeError`` from the ``in`` test — they always surface as ``LogicalModelError``."""
    if type(value) is not str or value not in _DIRECTIONAL_ORIENTATIONS:
        raise LogicalModelError(
            "directional exposure_orientation must be POSITIVE_EXPOSURE or NEGATIVE_EXPOSURE, not {!r}".format(
                value
            )
        )
    return value


def _require_inert_orientation(value):
    if type(value) is not str or value != INERT_STATE:
        raise LogicalModelError(
            "inert exposure_orientation must be exactly INERT_STATE, not {!r}".format(value)
        )
    return value


def validate_lifecycle_state(value):
    """Return ``value`` if it is exactly one of the closed lifecycle states, else raise."""
    if type(value) is not str or value not in CLOSED_LIFECYCLE_STATES:
        raise LogicalModelError("invalid lifecycle state: {!r}".format(value))
    return value


def _slot_value(carrier, slot_name):
    """Read one declared slot, surfacing a *missing-slot* forgery as the closed ``LogicalModelError``.

    An ``object.__new__(Cls)`` forgery that never populated ``slot_name`` raises a raw
    ``AttributeError`` on attribute access. Defensive revalidation must not let that escape; this
    helper converts **only** that exact ``AttributeError`` into ``LogicalModelError``. It deliberately
    catches **nothing else** — never ``BaseException``, ``MemoryError``, ``KeyboardInterrupt``, or any
    unrelated exception — so genuine faults are never masked.
    """
    try:
        return getattr(carrier, slot_name)
    except AttributeError:
        raise LogicalModelError(
            "forged or missing slot {!r} on {}".format(slot_name, type(carrier).__name__)
        )


# --- OpaqueSilverPairKey (5dc757c §2 / 474cc6f §2) -----------------------------------------------
@dataclass(frozen=True, slots=True, kw_only=True)
class OpaqueSilverPairKey:
    """The two opaque text components of the borrowed S1 Silver pair, carried verbatim.

    Frozen, slotted, and hashable so it can key the definitions map. The position component stays opaque
    text and is never decoded as an integer (``b06d7ed`` §6). Direct construction self-validates.
    """

    silver_artifact_locator_text: object
    silver_physical_record_position_text: object

    def __post_init__(self):
        _require_opaque_text("silver_artifact_locator_text", self.silver_artifact_locator_text)
        _require_opaque_text("silver_physical_record_position_text", self.silver_physical_record_position_text)


def make_opaque_silver_pair_key(*, silver_artifact_locator_text, silver_physical_record_position_text):
    return OpaqueSilverPairKey(
        silver_artifact_locator_text=silver_artifact_locator_text,
        silver_physical_record_position_text=silver_physical_record_position_text,
    )


# --- predecessor option-sum (1071067 §4) ---------------------------------------------------------
@dataclass(frozen=True, slots=True)
class NoPredecessor:
    """Closed variant: the first lineage member carries no predecessor (genuine zero payload fields)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class PredecessorReference:
    """Closed variant: exactly one caller-supplied opaque predecessor reference. Self-validating."""

    opaque_reference: object

    def __post_init__(self):
        _require_opaque_text("opaque_reference", self.opaque_reference)


def make_predecessor_reference(*, opaque_reference):
    return PredecessorReference(opaque_reference=opaque_reference)


def _require_predecessor_option(value):
    """The predecessor field is always present and is exactly one closed option variant."""
    if type(value) is NoPredecessor:
        return value
    if type(value) is PredecessorReference:
        _require_opaque_text("opaque_reference", _slot_value(value, "opaque_reference"))
        return value
    raise LogicalModelError(
        "predecessor_artifact_version_reference must be NoPredecessor or PredecessorReference, not {}".format(
            type(value).__name__
        )
    )


# --- closed definition variants (5dc757c §6/§7) --------------------------------------------------
@dataclass(frozen=True, slots=True, kw_only=True)
class DirectionalShadowIntentDefinition:
    """Directional declared counterfactual: orientation + passive boundary (magnitude + unit) + window.

    Frozen, slotted, keyword-only, and self-validating on construction.
    """

    exposure_orientation: object
    passive_boundary_magnitude: object
    boundary_unit_context: object
    hypothetical_window_duration_ms: object

    def __post_init__(self):
        _require_directional_orientation(self.exposure_orientation)
        _require_finite_decimal("passive_boundary_magnitude", self.passive_boundary_magnitude)
        _require_opaque_text("boundary_unit_context", self.boundary_unit_context)
        _require_non_negative_int_ms("hypothetical_window_duration_ms", self.hypothetical_window_duration_ms)


@dataclass(frozen=True, slots=True, kw_only=True)
class InertShadowIntentDefinition:
    """Inert declared counterfactual: orientation INERT_STATE + window. No boundary/unit by construction."""

    exposure_orientation: object
    hypothetical_window_duration_ms: object

    def __post_init__(self):
        _require_inert_orientation(self.exposure_orientation)
        _require_non_negative_int_ms("hypothetical_window_duration_ms", self.hypothetical_window_duration_ms)


def make_directional_shadow_intent_definition(
    *, exposure_orientation, passive_boundary_magnitude, boundary_unit_context, hypothetical_window_duration_ms
):
    return DirectionalShadowIntentDefinition(
        exposure_orientation=exposure_orientation,
        passive_boundary_magnitude=passive_boundary_magnitude,
        boundary_unit_context=boundary_unit_context,
        hypothetical_window_duration_ms=hypothetical_window_duration_ms,
    )


def make_inert_shadow_intent_definition(*, exposure_orientation, hypothetical_window_duration_ms):
    return InertShadowIntentDefinition(
        exposure_orientation=exposure_orientation,
        hypothetical_window_duration_ms=hypothetical_window_duration_ms,
    )


def _revalidate_silver_pair_key(key):
    """Defensive: re-assert an exact key's complete invariants (guards object.__new__ bypasses)."""
    if type(key) is not OpaqueSilverPairKey:
        raise LogicalModelError(
            "definition entry key must be an exact OpaqueSilverPairKey, not {}".format(type(key).__name__)
        )
    _require_opaque_text("silver_artifact_locator_text", _slot_value(key, "silver_artifact_locator_text"))
    _require_opaque_text(
        "silver_physical_record_position_text", _slot_value(key, "silver_physical_record_position_text")
    )


def _revalidate_definition(definition):
    """Defensive: re-assert a definition variant's complete invariants (guards object.__new__ bypasses)."""
    if type(definition) is DirectionalShadowIntentDefinition:
        _require_directional_orientation(_slot_value(definition, "exposure_orientation"))
        _require_finite_decimal(
            "passive_boundary_magnitude", _slot_value(definition, "passive_boundary_magnitude")
        )
        _require_opaque_text("boundary_unit_context", _slot_value(definition, "boundary_unit_context"))
        _require_non_negative_int_ms(
            "hypothetical_window_duration_ms", _slot_value(definition, "hypothetical_window_duration_ms")
        )
        return
    if type(definition) is InertShadowIntentDefinition:
        _require_inert_orientation(_slot_value(definition, "exposure_orientation"))
        _require_non_negative_int_ms(
            "hypothetical_window_duration_ms", _slot_value(definition, "hypothetical_window_duration_ms")
        )
        return
    raise LogicalModelError(
        "definition must be a Directional or Inert ShadowIntentDefinition, not {}".format(type(definition).__name__)
    )


# --- artifact envelope (5dc757c §3 / 1071067 §3) — factory-only ----------------------------------
@dataclass(frozen=True, slots=True, init=False, eq=False, repr=False)
class ShadowIntentDefinitionArtifact:
    """The closed five-field sealed scenario-definition artifact (always five fields).

    Construction is **factory-only**: direct construction (no args / positional / keyword) raises
    ``LogicalModelError``; only :func:`make_shadow_intent_definition_artifact` may create an instance.
    ``definitions_by_silver_pair`` is an immutable finite mapping (a read-only proxy) keyed only by the
    exact ``OpaqueSilverPairKey``; duplicate keys are rejected at construction; an empty map is valid.
    """

    artifact_field_shape_version_reference: object
    artifact_version_reference: object
    declarer_opaque_reference: object
    predecessor_artifact_version_reference: object
    definitions_by_silver_pair: object

    def __init__(self, *args, **kwargs):
        raise LogicalModelError(
            "ShadowIntentDefinitionArtifact cannot be constructed directly; "
            "use make_shadow_intent_definition_artifact(...)."
        )


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
    (a duplicate is rejected — no first/last-wins/merge). Every envelope reference, the predecessor
    variant, and every key + definition + nested field is **defensively revalidated** in one bounded
    O(n) pass before map construction (guarding any ``object.__new__`` bypass). The resulting map is
    wrapped read-only; the local dict is not retained, so the stored mapping cannot be mutated through
    any external handle.
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
        _revalidate_silver_pair_key(key)
        _revalidate_definition(definition)
        if key in built:
            raise LogicalModelError("duplicate Silver-pair key in definition_entries is structurally invalid")
        built[key] = definition

    artifact = object.__new__(ShadowIntentDefinitionArtifact)
    object.__setattr__(artifact, "artifact_field_shape_version_reference", artifact_field_shape_version_reference)
    object.__setattr__(artifact, "artifact_version_reference", artifact_version_reference)
    object.__setattr__(artifact, "declarer_opaque_reference", declarer_opaque_reference)
    object.__setattr__(artifact, "predecessor_artifact_version_reference", predecessor_artifact_version_reference)
    object.__setattr__(artifact, "definitions_by_silver_pair", MappingProxyType(built))
    return artifact


# Defensive guard: the envelope must remain the closed five-field contract.
_EXPECTED_ENVELOPE_FIELDS = (
    "artifact_field_shape_version_reference",
    "artifact_version_reference",
    "declarer_opaque_reference",
    "predecessor_artifact_version_reference",
    "definitions_by_silver_pair",
)
assert tuple(f.name for f in _dataclass_fields(ShadowIntentDefinitionArtifact)) == _EXPECTED_ENVELOPE_FIELDS


# =================================================================================================
# Slice-A Runtime Extension — lifecycle slot / root-evidence option-sum / dual-snapshot value types
#
# Effective ratified contract: the field-shape amendment (85de568) as superseded by the exactness
# correction (38eccce), the U+200B source-fidelity correction (9fc7749) and its typo micro-correction
# (01331ec). Historical superseded clauses do not govern. These are Slice-A-owned passive carriers;
# no Step algorithm, lifecycle application, or replay-loop behavior lives here.
# =================================================================================================

# Canonical anchor-timestamp grammar: ASCII "0" | [1-9][0-9]* (ASCII digits only — NOT ``\d``, no
# Unicode decimal digits, no sign/fraction/exponent/whitespace/leading-zeros). ``[0-9]`` is ASCII by
# definition; acceptance is lexical (no int() conversion).
_CANONICAL_ANCHOR_TIMESTAMP = re.compile(r"0|[1-9][0-9]*")


def _require_nonblank_context_text(name, value):
    """A context scalar is exactly a ``str`` AND ``value.strip() != ""`` (verbatim preserved).

    Invalidity is defined operationally and exclusively (9fc7749/01331ec): a scalar is blank **iff**
    Python ``str.strip()`` returns ``""``. No broader Unicode-whitespace / zero-width / invisible
    category is consulted — so ``U+200B`` (which ``str.strip()`` leaves intact) is **non-blank and
    accepted**, while the empty string, ASCII whitespace, NBSP ``U+00A0``, EM SPACE ``U+2003``, and
    IDEOGRAPHIC SPACE ``U+3000`` are blank and rejected. ``strip()`` is used **only** for the
    emptiness test; the accepted value is stored exactly as received.
    """
    if type(value) is not str:
        raise LogicalModelError(
            "field {!r} must be opaque context text (str), not {}".format(name, type(value).__name__)
        )
    if value.strip() == "":
        raise LogicalModelError(
            "field {!r} must be non-blank (str.strip() != ''); empty/whitespace-only is invalid".format(name)
        )
    return value


def _require_canonical_anchor_timestamp_text(value):
    """Exact ``str`` matching the ASCII grammar ``"0" | [1-9][0-9]*`` (lexical; no ``int()``)."""
    if type(value) is not str:
        raise LogicalModelError(
            "provenance_anchor_timestamp_text must be canonical decimal text (str), not {}".format(
                type(value).__name__
            )
        )
    if _CANONICAL_ANCHOR_TIMESTAMP.fullmatch(value) is None:
        raise LogicalModelError(
            "provenance_anchor_timestamp_text must match ASCII '0' | [1-9][0-9]* (no \\d/Unicode digits, "
            "sign, fraction, exponent, whitespace, or leading zeros): {!r}".format(value)
        )
    return value


# --- the immutable two-scalar root context (457d279 precedence §5: (source_venue, source_pair)) ---
@dataclass(frozen=True, slots=True, kw_only=True)
class EstablishedRootContext:
    """The established intent's two opaque text context scalars, carried verbatim. Self-validating."""

    source_venue_context_text: object
    source_pair_context_text: object

    def __post_init__(self):
        _require_nonblank_context_text("source_venue_context_text", self.source_venue_context_text)
        _require_nonblank_context_text("source_pair_context_text", self.source_pair_context_text)


def _revalidate_established_root_context(ctx):
    """Defensive: re-assert an exact context's complete invariants (guards object.__new__ bypasses)."""
    if type(ctx) is not EstablishedRootContext:
        raise LogicalModelError(
            "root_context must be an exact EstablishedRootContext, not {}".format(type(ctx).__name__)
        )
    _require_nonblank_context_text("source_venue_context_text", _slot_value(ctx, "source_venue_context_text"))
    _require_nonblank_context_text("source_pair_context_text", _slot_value(ctx, "source_pair_context_text"))


# --- closed root-evidence option-sum (NoRootEvidence | EstablishedRootEvidence) -------------------
@dataclass(frozen=True, slots=True)
class NoRootEvidence:
    """Closed variant: the slot has no established root (genuine zero payload fields)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class EstablishedRootEvidence:
    """Closed variant: the two-scalar context + canonical provenance anchor timestamp. Self-validating."""

    root_context: object
    provenance_anchor_timestamp_text: object

    def __post_init__(self):
        _revalidate_established_root_context(self.root_context)
        _require_canonical_anchor_timestamp_text(self.provenance_anchor_timestamp_text)


def _require_root_evidence_option(value):
    """The root_evidence field is always present and is exactly one closed option variant."""
    if type(value) is NoRootEvidence:
        return value
    if type(value) is EstablishedRootEvidence:
        _revalidate_established_root_context(_slot_value(value, "root_context"))
        _require_canonical_anchor_timestamp_text(_slot_value(value, "provenance_anchor_timestamp_text"))
        return value
    raise LogicalModelError(
        "root_evidence must be NoRootEvidence or EstablishedRootEvidence, not {}".format(type(value).__name__)
    )


def _require_slot_state_root_invariant(state, root_evidence):
    """Closed lifecycle-state / root-evidence compatibility (e9995e7 §4; 457d279 atomicity §5).

    ``AUDIT_REPLAYED`` <=> ``NoRootEvidence``; every established/forward/terminal state
    (``INTENT_RECORDED`` / ``HYPOTHETICAL_CONDITION_MET`` / ``INTENT_EXPIRED`` / ``INTENT_RETIRED``)
    <=> ``EstablishedRootEvidence``. (Both arguments are already individually validated.)
    """
    if state == AUDIT_REPLAYED:
        if type(root_evidence) is not NoRootEvidence:
            raise LogicalModelError("AUDIT_REPLAYED slot must carry NoRootEvidence")
    else:
        if type(root_evidence) is not EstablishedRootEvidence:
            raise LogicalModelError(
                "lifecycle state {!r} (established/forward/terminal) must carry EstablishedRootEvidence".format(state)
            )


# --- per-intent lifecycle slot -------------------------------------------------------------------
@dataclass(frozen=True, slots=True, kw_only=True)
class ShadowIntentLifecycleSlot:
    """Passive per-intent slot: borrowed identity + closed lifecycle state + closed root evidence.

    Frozen, slotted, keyword-only, methodless, self-validating. The identity reuses the existing
    ``OpaqueSilverPairKey`` (never mints another identity); ``exposure_orientation`` and the
    hypothetical window stay manifest-resident and are deliberately NOT carried here.
    """

    shadow_intent_identity_reference: object
    lifecycle_state: object
    root_evidence: object

    def __post_init__(self):
        _revalidate_silver_pair_key(self.shadow_intent_identity_reference)
        validate_lifecycle_state(self.lifecycle_state)
        _require_root_evidence_option(self.root_evidence)
        _require_slot_state_root_invariant(self.lifecycle_state, self.root_evidence)


def _revalidate_lifecycle_slot(slot):
    """Defensive: re-assert a slot's complete invariants (guards object.__new__ bypasses)."""
    if type(slot) is not ShadowIntentLifecycleSlot:
        raise LogicalModelError(
            "snapshot entry value must be an exact ShadowIntentLifecycleSlot, not {}".format(type(slot).__name__)
        )
    identity = _slot_value(slot, "shadow_intent_identity_reference")
    state = _slot_value(slot, "lifecycle_state")
    root = _slot_value(slot, "root_evidence")
    _revalidate_silver_pair_key(identity)
    validate_lifecycle_state(state)
    _require_root_evidence_option(root)
    _require_slot_state_root_invariant(state, root)


# --- shadow snapshot (one type for both RowStartShadowSnapshot / NextShadowSnapshot roles) --------
@dataclass(frozen=True, slots=True, init=False, repr=False)
class ShadowLifecycleSnapshot:
    """Factory-only immutable snapshot: ``slots_by_identity`` is a read-only proxy of
    ``OpaqueSilverPairKey -> ShadowIntentLifecycleSlot``. Direct construction raises; equality is
    content-based and order-independent (the proxy compares as the underlying mapping)."""

    slots_by_identity: object

    def __init__(self, *args, **kwargs):
        raise LogicalModelError(
            "ShadowLifecycleSnapshot cannot be constructed directly; use make_shadow_lifecycle_snapshot(...)."
        )


def make_shadow_lifecycle_snapshot(*, slot_entries):
    """Build one validated ``ShadowLifecycleSnapshot`` from an exact tuple of exact 2-tuples.

    ``slot_entries`` is an ordered ``tuple`` of ``(OpaqueSilverPairKey, ShadowIntentLifecycleSlot)``
    pairs (ordering carries no semantic meaning; it exists only so duplicates are detectable before
    map construction). Every key and slot is defensively revalidated, the map key MUST equal
    ``slot.shadow_intent_identity_reference``, and a duplicate key is rejected (no first/last-wins).
    The local dict is wrapped read-only and not retained; no caller dict is accepted. An empty map is
    valid.
    """
    if type(slot_entries) is not tuple:
        raise LogicalModelError(
            "slot_entries must be a tuple of (OpaqueSilverPairKey, ShadowIntentLifecycleSlot) pairs, not {}".format(
                type(slot_entries).__name__
            )
        )
    built = {}
    for entry in slot_entries:
        if type(entry) is not tuple or len(entry) != 2:
            raise LogicalModelError("each slot entry must be a (key, slot) 2-tuple")
        key, slot = entry
        _revalidate_silver_pair_key(key)
        _revalidate_lifecycle_slot(slot)
        if key != _slot_value(slot, "shadow_intent_identity_reference"):
            raise LogicalModelError("snapshot key must equal slot.shadow_intent_identity_reference")
        if key in built:
            raise LogicalModelError("duplicate Silver-pair key in slot_entries is structurally invalid")
        built[key] = slot

    snapshot = object.__new__(ShadowLifecycleSnapshot)
    object.__setattr__(snapshot, "slots_by_identity", MappingProxyType(built))
    return snapshot


# --- seen-target-pairs snapshot (one type for both RowStart / Next SeenTargetPairs roles) ---------
@dataclass(frozen=True, slots=True, init=False, repr=False)
class SeenTargetPairsSnapshot:
    """Factory-only immutable replay-local snapshot: ``seen_target_pairs`` is a ``frozenset`` of exact
    ``OpaqueSilverPairKey`` values. Direct construction raises; equality is set-content and
    order-independent."""

    seen_target_pairs: object

    def __init__(self, *args, **kwargs):
        raise LogicalModelError(
            "SeenTargetPairsSnapshot cannot be constructed directly; use make_seen_target_pairs_snapshot(...)."
        )


def make_seen_target_pairs_snapshot(*, members):
    """Build one validated ``SeenTargetPairsSnapshot`` from an exact tuple of exact keys.

    ``members`` is an exact ``tuple`` of ``OpaqueSilverPairKey`` values; each is defensively
    revalidated, and a duplicate member is rejected **before** frozenset construction (no silent
    deduplication). An empty members tuple is valid.
    """
    if type(members) is not tuple:
        raise LogicalModelError(
            "members must be a tuple of OpaqueSilverPairKey values, not {}".format(type(members).__name__)
        )
    seen = set()
    for member in members:
        _revalidate_silver_pair_key(member)
        if member in seen:
            raise LogicalModelError("duplicate member in members is structurally invalid (no silent dedup)")
        seen.add(member)

    snapshot = object.__new__(SeenTargetPairsSnapshot)
    object.__setattr__(snapshot, "seen_target_pairs", frozenset(seen))
    return snapshot
