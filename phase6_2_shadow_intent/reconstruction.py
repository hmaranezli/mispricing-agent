"""phase6_2_shadow_intent/reconstruction.py — Phase 6.2 Slice F — Reconstruction Fold.

The pure sequencer over an already-materialized tuple of opaque S1 replay rows and one verified manifest
artifact, as pinned by the ratified Slice-F reconstruction-loop exact-shape charter (base ``04a20eb``).
It validates the two inputs by exact type, seeds factory-fresh empty lifecycle / seen-pair snapshots, and
folds the rows left-to-right through the single Slice-E step, passing each step's two snapshot fields by
identity into the next call and passing the same verified artifact by identity on every call. An empty
replay returns a fresh empty carrier; a non-empty replay returns the exact final Slice-E carrier unwrapped.

Slice F is a sequencer only: it never inspects, parses, indexes, reorders, deduplicates, copies, or buffers
rows; never performs manifest lookup, projection, or provenance checks; defines no error class and contains
no ``try``/``except``. The Slice-E error surface and all factory / system exceptions propagate unchanged;
only the two exact input guards raise native ``TypeError``. Auxiliary fold memory is O(1) loop / reference /
carrier overhead beyond the caller-materialized input tuple and the evolving output payload.

Capacity stays deferred at 0 emit sites; live / paper / canary / execution / routing / actionability remain
forbidden. Phase 6.2 is INCOMPLETE and NOT ready for any live use (Slice-G closeout remains).
"""
from phase6_2_shadow_intent.atomic_replay_step import (
    execute_atomic_replay_step,
    AtomicReplayStepResult,
)
from phase6_2_shadow_intent.logical_model import (
    ShadowIntentDefinitionArtifact,
    make_shadow_lifecycle_snapshot,
    make_seen_target_pairs_snapshot,
)


def reconstruct_shadow_intent_state(
    *,
    ordered_replay_rows: tuple[object, ...],
    verified_manifest_artifact: ShadowIntentDefinitionArtifact,
) -> AtomicReplayStepResult:
    """Fold the ordered opaque replay rows through the Slice-E step and return the final carrier."""
    if type(ordered_replay_rows) is not tuple:
        raise TypeError("ordered_replay_rows must be an exact tuple")
    if type(verified_manifest_artifact) is not ShadowIntentDefinitionArtifact:
        raise TypeError("verified_manifest_artifact must be an exact ShadowIntentDefinitionArtifact")

    current_lifecycle_snapshot = make_shadow_lifecycle_snapshot(slot_entries=())
    current_seen_pairs = make_seen_target_pairs_snapshot(members=())
    result = None

    for raw_evidence_row in ordered_replay_rows:
        result = execute_atomic_replay_step(
            current_lifecycle_snapshot=current_lifecycle_snapshot,
            current_seen_pairs=current_seen_pairs,
            raw_evidence_row=raw_evidence_row,
            frozen_manifest_projection=verified_manifest_artifact,
        )
        current_lifecycle_snapshot = result.next_lifecycle_snapshot
        current_seen_pairs = result.next_seen_target_pairs

    if result is None:
        result = AtomicReplayStepResult(
            next_lifecycle_snapshot=current_lifecycle_snapshot,
            next_seen_target_pairs=current_seen_pairs,
        )
    return result
