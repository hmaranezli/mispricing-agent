"""phase6_2_shadow_intent/atomic_replay_step.py — Phase 6.2 Slice E — Atomic Replay Step.

The exact ratified ``Step`` law: a pure, deterministic function over one row-start shadow snapshot, one
row-start seen-target-pairs snapshot, one opaque S1 replay row, and the complete frozen manifest artifact,
yielding either one atomically-published ``AtomicReplayStepResult`` (``NextShadowSnapshot``,
``NextSeenTargetPairs``) or exactly one ``AtomicReplayStepError`` from the closed ten-reason vocabulary.

Governing charter chain (effective, ratified): the exact-shape charter (``85d1ba6``) as corrected by the
concrete-manifest-type/duplicate/error-surface correction (``ff92ad0``) and the manifest-lookup closed-domain
micro-correction (``90bb5d3``); the behavioral chain ``457d279`` (planning), the replay-step atomicity /
row-start-snapshot / terminal-relevance correction, ``44791ce`` (duplicate-root / context-first, per-slot
E.1–E.12), and ``e9995e7`` (lifecycle transition table).

This module sequences nothing beyond one row: it owns the per-row A–J ordering and per-slot E.1–E.12
classification, classify-all/apply-all atomicity (inert proposals, then one atomic publication or whole-row
failure), duplicate-root primacy, row-start-snapshot exclusion of the just-established slot, terminal
absorption, relevance scoping, and the single contract-defined manifest lookup. It delegates **every**
projection to Slice C and **every** predicate to Slice D (never re-implementing their logic), reuses the
sealed Slice-A revalidators and the guarded ``_slot_value`` discipline for every carrier-field read, and
treats ``raw_evidence_row`` as opaque (passed only to the reached Slice-C projectors; never imported as
sqlite3, indexed, iterated, parsed, or directly inspected). It normalizes only the sealed Slice-A/C/D
domain failures into the mapped reasons and never broadly catches ``Exception``/``BaseException``.

Capacity stays deferred at 0 emit sites; production / live / paper / canary / execution / routing /
actionability remain forbidden. Phase 6.2 is INCOMPLETE and NOT runtime-ready (the Slice-F reconstruction
fold and Slice-G closeout remain).
"""
from types import MappingProxyType
from dataclasses import dataclass

from phase6_2_shadow_intent.logical_model import (
    LogicalModelError,
    _slot_value,
    OpaqueSilverPairKey,
    ShadowIntentLifecycleSlot,
    ShadowLifecycleSnapshot,
    SeenTargetPairsSnapshot,
    ShadowIntentDefinitionArtifact,
    DirectionalShadowIntentDefinition,
    InertShadowIntentDefinition,
    EstablishedRootContext,
    EstablishedRootEvidence,
    NoRootEvidence,
    AUDIT_REPLAYED,
    INTENT_RECORDED,
    HYPOTHETICAL_CONDITION_MET,
    INTENT_EXPIRED,
    INTENT_RETIRED,
    make_shadow_lifecycle_snapshot,
    make_seen_target_pairs_snapshot,
    make_opaque_silver_pair_key,
    _revalidate_silver_pair_key,
    _revalidate_lifecycle_slot,
    _revalidate_definition,
    _require_opaque_text,
    _require_predecessor_option,
)
from phase6_2_shadow_intent.s1_evidence_projection import (
    S1EvidenceProjectionError,
    project_silver_pair,
    project_observation_kind,
    project_score_family,
    project_score_context,
    project_score_timestamp,
    project_score_unit,
    project_score_magnitude,
)
from phase6_2_shadow_intent.classification_predicates import (
    ClassificationPredicateError,
    context_equals,
    classify_timestamp_window,
    unit_comparable,
    classify_directional_crossing,
    WINDOW_NON_COMPARABLE,
    WINDOW_IN_WINDOW,
    WINDOW_EXPIRED,
)


ATOMIC_REPLAY_STEP_COMPONENT_NAME = "phase6_2_shadow_intent_atomic_replay_step"

_SCORE_OBSERVATION_KIND = "SCORE"

# --- closed deterministic failure-reason vocabulary (exactly ten; 1:1 with the charter) -----------
STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT = "STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT"
STEP_INVALID_CURRENT_SEEN_PAIRS = "STEP_INVALID_CURRENT_SEEN_PAIRS"
STEP_INVALID_MANIFEST_PROJECTION = "STEP_INVALID_MANIFEST_PROJECTION"
STEP_EVIDENCE_PROJECTION_REJECTED = "STEP_EVIDENCE_PROJECTION_REJECTED"
STEP_CLASSIFICATION_PREDICATE_REJECTED = "STEP_CLASSIFICATION_PREDICATE_REJECTED"
STEP_MANIFEST_DEFINITION_ABSENT = "STEP_MANIFEST_DEFINITION_ABSENT"
STEP_DUPLICATE_ROOT = "STEP_DUPLICATE_ROOT"
STEP_TARGETED_NON_SCORE_ROOT = "STEP_TARGETED_NON_SCORE_ROOT"
STEP_INVALID_LIFECYCLE_TRANSITION = "STEP_INVALID_LIFECYCLE_TRANSITION"
STEP_PUBLICATION_INVARIANT_VIOLATION = "STEP_PUBLICATION_INVARIANT_VIOLATION"

# Legal non-self forward edges (e9995e7 §4); self-loops are always legal no-ops.
_LEGAL_FORWARD = {
    AUDIT_REPLAYED: frozenset({INTENT_RECORDED}),
    INTENT_RECORDED: frozenset({HYPOTHETICAL_CONDITION_MET, INTENT_EXPIRED, INTENT_RETIRED}),
    HYPOTHETICAL_CONDITION_MET: frozenset({INTENT_EXPIRED, INTENT_RETIRED}),
}


class AtomicReplayStepError(ValueError):
    """The single deterministic Slice-E domain failure surface, carrying one closed ``reason`` code
    (matching the sealed Slice-C ``S1EvidenceProjectionError`` / Slice-D ``ClassificationPredicateError``
    constructor pattern)."""

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


# --- consumer-boundary revalidators (reuse the sealed Slice-A revalidators; map to closed reasons) -

def _revalidate_lifecycle_snapshot(snapshot, reason):
    if type(snapshot) is not ShadowLifecycleSnapshot:
        raise AtomicReplayStepError(reason, "expected an exact ShadowLifecycleSnapshot")
    try:
        slots = _slot_value(snapshot, "slots_by_identity")
        if type(slots) is not MappingProxyType:
            raise AtomicReplayStepError(reason, "slots_by_identity must be a read-only mapping proxy")
        for key, slot in slots.items():
            _revalidate_silver_pair_key(key)
            _revalidate_lifecycle_slot(slot)
            if key != _slot_value(slot, "shadow_intent_identity_reference"):
                raise AtomicReplayStepError(reason, "snapshot key must equal slot identity")
    except LogicalModelError as exc:
        raise AtomicReplayStepError(reason, str(exc))
    return slots


def _revalidate_seen_snapshot(snapshot, reason):
    if type(snapshot) is not SeenTargetPairsSnapshot:
        raise AtomicReplayStepError(reason, "expected an exact SeenTargetPairsSnapshot")
    try:
        members = _slot_value(snapshot, "seen_target_pairs")
        if type(members) is not frozenset:
            raise AtomicReplayStepError(reason, "seen_target_pairs must be a frozenset")
        for member in members:
            _revalidate_silver_pair_key(member)
    except LogicalModelError as exc:
        raise AtomicReplayStepError(reason, str(exc))
    return members


def _revalidate_manifest(manifest):
    reason = STEP_INVALID_MANIFEST_PROJECTION
    if type(manifest) is not ShadowIntentDefinitionArtifact:
        raise AtomicReplayStepError(reason, "expected an exact ShadowIntentDefinitionArtifact")
    try:
        _require_opaque_text("artifact_field_shape_version_reference",
                             _slot_value(manifest, "artifact_field_shape_version_reference"))
        _require_opaque_text("artifact_version_reference",
                             _slot_value(manifest, "artifact_version_reference"))
        _require_opaque_text("declarer_opaque_reference",
                             _slot_value(manifest, "declarer_opaque_reference"))
        _require_predecessor_option(_slot_value(manifest, "predecessor_artifact_version_reference"))
        defs = _slot_value(manifest, "definitions_by_silver_pair")
        if type(defs) is not MappingProxyType:
            raise AtomicReplayStepError(reason, "definitions_by_silver_pair must be a read-only proxy")
        for key, definition in defs.items():
            _revalidate_silver_pair_key(key)
            _revalidate_definition(definition)
    except LogicalModelError as exc:
        raise AtomicReplayStepError(reason, str(exc))
    return defs


# --- delegated projection / predicate / lookup normalizers ----------------------------------------

def _project(operation, raw_evidence_row):
    """Invoke one reached Slice-C strict-lazy projector over the opaque row, normalizing its sealed
    ``S1EvidenceProjectionError`` to the mapped reason (only when reached)."""
    try:
        return operation(replay_row=raw_evidence_row)
    except S1EvidenceProjectionError as exc:
        raise AtomicReplayStepError(STEP_EVIDENCE_PROJECTION_REJECTED, str(exc))


def _predicate(classifier, **inputs):
    """Invoke one reached Slice-D pure predicate, normalizing its sealed ``ClassificationPredicateError``
    to the mapped reason."""
    try:
        return classifier(**inputs)
    except ClassificationPredicateError as exc:
        raise AtomicReplayStepError(STEP_CLASSIFICATION_PREDICATE_REJECTED, str(exc))


def _lookup_definition(defs, key):
    """The single contract-defined manifest lookup site. ``KeyError`` (a key the contract guarantees
    present — the current target after classification, or a row-start slot reached by precedence) is
    normalized here and only here."""
    try:
        return defs[key]
    except KeyError:
        raise AtomicReplayStepError(
            STEP_MANIFEST_DEFINITION_ABSENT, "manifest definition absent for a contract-guaranteed key")


def _require_legal_transition(old_state, new_state):
    if new_state == old_state:
        return
    if new_state not in _LEGAL_FORWARD.get(old_state, frozenset()):
        raise AtomicReplayStepError(
            STEP_INVALID_LIFECYCLE_TRANSITION,
            "illegal lifecycle transition {} -> {}".format(old_state, new_state))


# --- the Slice-E-owned atomic publication carrier -------------------------------------------------

@dataclass(frozen=True, slots=True, kw_only=True)
class AtomicReplayStepResult:
    """The single atomic publication point: the next shadow snapshot + next seen-target-pairs snapshot.
    Directly keyword-constructible (no factory); ``__post_init__`` defensively revalidates both snapshot
    fields (incl. populated / missing-slot forgeries) through the closed publication-invariant reason.
    Identity preservation is a Step postcondition, NOT a constructor invariant."""

    next_lifecycle_snapshot: ShadowLifecycleSnapshot
    next_seen_target_pairs: SeenTargetPairsSnapshot

    def __post_init__(self):
        _revalidate_lifecycle_snapshot(self.next_lifecycle_snapshot, STEP_PUBLICATION_INVARIANT_VIOLATION)
        _revalidate_seen_snapshot(self.next_seen_target_pairs, STEP_PUBLICATION_INVARIANT_VIOLATION)


# --- the public atomic replay step ----------------------------------------------------------------

def execute_atomic_replay_step(
    *,
    current_lifecycle_snapshot: ShadowLifecycleSnapshot,
    current_seen_pairs: SeenTargetPairsSnapshot,
    raw_evidence_row: object,
    frozen_manifest_projection: ShadowIntentDefinitionArtifact,
) -> AtomicReplayStepResult:
    """Apply one atomic replay step. Returns a fresh :class:`AtomicReplayStepResult` on success (both
    inputs preserved by identity on a true no-op; only the changed snapshot rebuilt on a partial change),
    or raises exactly one :class:`AtomicReplayStepError`. Inputs are never mutated; failure publishes
    nothing."""
    # 1. consumer-boundary input revalidation, fixed parameter order (before any row logic).
    row_start_slots = _revalidate_lifecycle_snapshot(
        current_lifecycle_snapshot, STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT)
    seen_members = _revalidate_seen_snapshot(current_seen_pairs, STEP_INVALID_CURRENT_SEEN_PAIRS)
    defs = _revalidate_manifest(frozen_manifest_projection)

    # 2. (A) row Silver-pair projection — the global guard.
    silver = _project(project_silver_pair, raw_evidence_row)
    row_key = make_opaque_silver_pair_key(
        silver_artifact_locator_text=_slot_value(silver, "silver_artifact_locator"),
        silver_physical_record_position_text=_slot_value(silver, "silver_physical_record_position"))
    is_target = row_key in defs

    # 3. (B) duplicate-root guard — immediate, before terminal handling or any inspection.
    if is_target and row_key in seen_members:
        raise AtomicReplayStepError(STEP_DUPLICATE_ROOT, "duplicate targeted Silver pair in replay")

    new_slot_entry = None     # (key, slot) proposed for establishment / permanent non-establishment
    commit_pair = None        # targeted key proposed for the seen set
    established_key = None     # key established this row (excluded from same-row per-slot classification)

    # 4. (C) first-target root path.
    if is_target:             # and not already seen (duplicate already guarded)
        established_key = row_key
        definition = _lookup_definition(defs, row_key)
        kind = _project(project_observation_kind, raw_evidence_row)
        if _slot_value(kind, "observation_kind") != _SCORE_OBSERVATION_KIND:
            raise AtomicReplayStepError(
                STEP_TARGETED_NON_SCORE_ROOT, "targeted root is not a SCORE observation")
        _project(project_score_family, raw_evidence_row)
        context = _project(project_score_context, raw_evidence_row)
        timestamp = _project(project_score_timestamp, raw_evidence_row)
        summary = _slot_value(context, "score_inputs_summary")
        anchor_text = _slot_value(timestamp, "provenance_timestamp")
        root_context = EstablishedRootContext(
            source_venue_context_text=summary[0], source_pair_context_text=summary[1])
        if type(definition) is DirectionalShadowIntentDefinition:
            unit = _project(project_score_unit, raw_evidence_row)
            if not _predicate(unit_comparable,
                              boundary_unit_context=_slot_value(definition, "boundary_unit_context"),
                              observed_unit=unit):
                # permanent non-establishment: stays AUDIT_REPLAYED + NoRootEvidence; pair still committed.
                new_slot_entry = (row_key, ShadowIntentLifecycleSlot(
                    shadow_intent_identity_reference=row_key,
                    lifecycle_state=AUDIT_REPLAYED, root_evidence=NoRootEvidence()))
                commit_pair = row_key
            else:
                new_slot_entry = (row_key, _establish_slot(row_key, root_context, anchor_text))
                commit_pair = row_key
        else:                 # inert root establishes INTENT_RECORDED regardless of unit comparability
            new_slot_entry = (row_key, _establish_slot(row_key, root_context, anchor_text))
            commit_pair = row_key

    # 5. (D) freeze the row-start established + non-terminal slot set (excluding the just-established key).
    active = []
    for key, slot in row_start_slots.items():
        if key == established_key:
            continue
        state = _slot_value(slot, "lifecycle_state")
        if state == INTENT_RECORDED or state == HYPOTHETICAL_CONDITION_MET:
            active.append((key, slot))

    transitions = {}          # key -> (old_state, new_state); root_evidence preserved
    # (E) skip later-observation predicates entirely when no established non-terminal slot needs relevance.
    if active:
        kind = _project(project_observation_kind, raw_evidence_row)
        if _slot_value(kind, "observation_kind") == _SCORE_OBSERVATION_KIND:
            # (F) validate context shape once; (G) determine context-equal slots.
            context = _project(project_score_context, raw_evidence_row)
            context_equal = []
            for key, slot in active:
                root_context = _slot_value(_slot_value(slot, "root_evidence"), "root_context")
                if _predicate(context_equals, root_context=root_context, observed_context=context):
                    context_equal.append((key, slot))
            if context_equal:
                # (E.6) full SCORE-family consistency only for context-equal SCOREs; (E.7) timestamp.
                _project(project_score_family, raw_evidence_row)
                timestamp = _project(project_score_timestamp, raw_evidence_row)
                for key, slot in context_equal:
                    transition = _classify_slot(defs, key, slot, raw_evidence_row, timestamp)
                    if transition is not None:
                        transitions[key] = transition

    return _publish(
        current_lifecycle_snapshot, current_seen_pairs, row_start_slots, seen_members,
        transitions, new_slot_entry, commit_pair)


def _establish_slot(key, root_context, anchor_text):
    return ShadowIntentLifecycleSlot(
        shadow_intent_identity_reference=key,
        lifecycle_state=INTENT_RECORDED,
        root_evidence=EstablishedRootEvidence(
            root_context=root_context, provenance_anchor_timestamp_text=anchor_text))


def _classify_slot(defs, key, slot, raw_evidence_row, timestamp):
    """Classify one context-equal established non-terminal slot against the row, per E.7–E.12. Returns
    ``(old_state, new_state)`` for a proposed transition, or ``None`` for a no-op."""
    definition = _lookup_definition(defs, key)        # category-2 row-start-slot manifest lookup
    duration = _slot_value(definition, "hypothetical_window_duration_ms")
    anchor = _slot_value(_slot_value(slot, "root_evidence"), "provenance_anchor_timestamp_text")
    window = _predicate(classify_timestamp_window,
                        anchor=anchor, comparison=timestamp, duration_ms=duration)
    if window == WINDOW_NON_COMPARABLE:               # E.8 negative delta -> no-op
        return None
    old_state = _slot_value(slot, "lifecycle_state")
    if window == WINDOW_EXPIRED:                       # E.9 expiry (precedes unit/magnitude)
        return (old_state, INTENT_EXPIRED)
    # WINDOW_IN_WINDOW:
    if type(definition) is InertShadowIntentDefinition:   # E.10 inert in-window -> no-op
        return None
    unit = _project(project_score_unit, raw_evidence_row)
    if not _predicate(unit_comparable,
                      boundary_unit_context=_slot_value(definition, "boundary_unit_context"),
                      observed_unit=unit):              # E.11 unit mismatch -> no crossing
        return None
    magnitude = _project(project_score_magnitude, raw_evidence_row)
    crossed = _predicate(classify_directional_crossing,
                         exposure_orientation=_slot_value(definition, "exposure_orientation"),
                         boundary_magnitude=_slot_value(definition, "passive_boundary_magnitude"),
                         observed_magnitude=magnitude)   # E.12 directional crossing
    if crossed and old_state == INTENT_RECORDED:
        return (old_state, HYPOTHETICAL_CONDITION_MET)
    return None                                          # already MET / no crossing -> no-op


def _publish(current_lifecycle_snapshot, current_seen_pairs, row_start_slots, seen_members,
             transitions, new_slot_entry, commit_pair):
    """Apply all proposals atomically (J): unchanged snapshots preserved by identity, changed snapshots
    factory-built fresh. Any publication-invariant failure maps to the publication reason."""
    lifecycle_changed = bool(transitions) or new_slot_entry is not None
    seen_changed = commit_pair is not None

    if not lifecycle_changed and not seen_changed:
        next_lifecycle = current_lifecycle_snapshot       # true no-op: identity
        next_seen = current_seen_pairs                     # true no-op: identity
    else:
        try:
            if lifecycle_changed:
                entries = []
                for key, slot in row_start_slots.items():
                    if key in transitions:
                        old_state, new_state = transitions[key]
                        _require_legal_transition(old_state, new_state)
                        entries.append((key, ShadowIntentLifecycleSlot(
                            shadow_intent_identity_reference=key,
                            lifecycle_state=new_state,
                            root_evidence=_slot_value(slot, "root_evidence"))))
                    else:
                        entries.append((key, slot))
                if new_slot_entry is not None:
                    entries.append(new_slot_entry)
                next_lifecycle = make_shadow_lifecycle_snapshot(slot_entries=tuple(entries))
            else:
                next_lifecycle = current_lifecycle_snapshot   # unchanged component: identity
            if seen_changed:
                next_seen = make_seen_target_pairs_snapshot(
                    members=tuple(seen_members) + (commit_pair,))
            else:
                next_seen = current_seen_pairs                # unchanged component: identity
        except LogicalModelError as exc:
            raise AtomicReplayStepError(STEP_PUBLICATION_INVARIANT_VIOLATION, str(exc))

    return AtomicReplayStepResult(
        next_lifecycle_snapshot=next_lifecycle, next_seen_target_pairs=next_seen)
