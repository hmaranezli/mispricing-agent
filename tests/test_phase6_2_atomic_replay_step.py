"""tests/test_phase6_2_atomic_replay_step.py — Phase 6.2 Slice E — Atomic Replay Step.

Pins the exact ratified Slice-E atomic-replay-step contract: the sole public callable
``execute_atomic_replay_step`` (four mandatory keyword-only args), the Slice-E-owned two-field
``AtomicReplayStepResult`` (frozen/slots/kw-only, no factory, ``__post_init__`` revalidation), the closed
``AtomicReplayStepError(reason, message)`` ten-reason vocabulary, the per-row A–J precedence + per-slot
E.1–E.12 content, classify-all/apply-all atomicity, terminal absorption, duplicate-root primacy, relevance
scoping, identity/publication postconditions, the closed single manifest-lookup site, and the strict-lazy
opaque-row rule.

Governing charter chain (effective, ratified): the exact-shape charter (``85d1ba6``) as corrected by the
concrete-manifest-type/duplicate/error-surface correction (``ff92ad0``) and the manifest-lookup closed-domain
micro-correction (``90bb5d3``); the behavioral chain ``457d279`` (planning), the atomicity/row-snapshot/
terminal-relevance correction, ``44791ce`` (duplicate-root/context-first, per-slot E.1–E.12), ``e9995e7``
(lifecycle transition table); over the sealed Slice-A/C/D runtime at ``8db0b3c``.

Inputs are built only through the ratified Slice-A factories and through the Slice-C projectors over real
in-memory ``sqlite3.Row`` values (the same construction the sealed Slice-C/D tests use). ``object.__new__``
forgeries appear ONLY to prove the consumer-side defensive revalidation. Slice E owns no S1 parsing: the
opaque row is passed only to the reached Slice-C projectors.
"""
import ast
import inspect
import io
import json
import pathlib
import sqlite3
import tokenize
from decimal import Decimal

import pytest

import phase6_2_shadow_intent.atomic_replay_step as ars
from phase6_2_shadow_intent.atomic_replay_step import (
    execute_atomic_replay_step,
    AtomicReplayStepResult,
    AtomicReplayStepError,
    ATOMIC_REPLAY_STEP_COMPONENT_NAME,
    STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT,
    STEP_INVALID_CURRENT_SEEN_PAIRS,
    STEP_INVALID_MANIFEST_PROJECTION,
    STEP_EVIDENCE_PROJECTION_REJECTED,
    STEP_CLASSIFICATION_PREDICATE_REJECTED,
    STEP_MANIFEST_DEFINITION_ABSENT,
    STEP_DUPLICATE_ROOT,
    STEP_TARGETED_NON_SCORE_ROOT,
    STEP_INVALID_LIFECYCLE_TRANSITION,
    STEP_PUBLICATION_INVARIANT_VIOLATION,
)
import phase6_2_shadow_intent.logical_model as lm
import phase6_2_shadow_intent.s1_evidence_projection as sep

_UNSET = object()


# --- input builders (Slice-A factories + Slice-C projector rows over real sqlite3.Row) -------------

def _row(*, observation_kind="SCORE", family_descriptor="passive_net_edge_diagnostic",
         artifact_locator="loc", physical_record_position="pos",
         provenance_timestamp="1000", venue="hl", pair="BTC",
         unit="proportion", magnitude="2.0", payload=_UNSET):
    if payload is _UNSET:
        payload = json.dumps({
            "observation_kind": observation_kind,
            "provenance_timestamp": int(provenance_timestamp),
            "family_payload": {
                "score_family_descriptor": family_descriptor,
                "score_inputs_summary": [venue, pair],
                "score_unit_context": unit,
                "passive_score_magnitude": magnitude,
            },
        })
    connection = sqlite3.connect(":memory:")
    try:
        connection.row_factory = sqlite3.Row
        return connection.execute(
            "SELECT ? AS observation_kind, ? AS family_descriptor, ? AS artifact_locator, "
            "? AS physical_record_position, ? AS provenance_timestamp, ? AS canonical_text_payload",
            (observation_kind, family_descriptor, artifact_locator, physical_record_position,
             provenance_timestamp, payload)).fetchone()
    finally:
        connection.close()


def _key(locator="loc", position="pos"):
    return lm.make_opaque_silver_pair_key(silver_artifact_locator_text=locator,
                                          silver_physical_record_position_text=position)


def _directional(*, orientation=lm.POSITIVE_EXPOSURE, magnitude="1.5", unit="proportion", duration=840000):
    return lm.make_directional_shadow_intent_definition(
        exposure_orientation=orientation, passive_boundary_magnitude=Decimal(magnitude),
        boundary_unit_context=unit, hypothetical_window_duration_ms=duration)


def _inert(*, duration=840000):
    return lm.make_inert_shadow_intent_definition(
        exposure_orientation=lm.INERT_STATE, hypothetical_window_duration_ms=duration)


def _manifest(*entries):
    if not entries:
        entries = ((_key(), _directional()),)
    return lm.make_shadow_intent_definition_artifact(
        artifact_field_shape_version_reference="fsv1",
        artifact_version_reference="av1",
        declarer_opaque_reference="decl1",
        predecessor_artifact_version_reference=lm.NoPredecessor(),
        definition_entries=tuple(entries))


def _evidence(*, venue="hl", pair="BTC", anchor="1000"):
    return lm.EstablishedRootEvidence(
        root_context=lm.EstablishedRootContext(source_venue_context_text=venue,
                                               source_pair_context_text=pair),
        provenance_anchor_timestamp_text=anchor)


def _slot(*, key=None, state=lm.INTENT_RECORDED, evidence=_UNSET, venue="hl", pair="BTC", anchor="1000"):
    if key is None:
        key = _key()
    if evidence is _UNSET:
        evidence = (lm.NoRootEvidence() if state == lm.AUDIT_REPLAYED
                    else _evidence(venue=venue, pair=pair, anchor=anchor))
    return lm.ShadowIntentLifecycleSlot(
        shadow_intent_identity_reference=key, lifecycle_state=state, root_evidence=evidence)


def _lifecycle(*slot_entries):
    return lm.make_shadow_lifecycle_snapshot(slot_entries=tuple(slot_entries))


def _seen(*keys):
    return lm.make_seen_target_pairs_snapshot(members=tuple(keys))


def _call(*, lifecycle=None, seen=None, row=None, manifest=None):
    return execute_atomic_replay_step(
        current_lifecycle_snapshot=_lifecycle() if lifecycle is None else lifecycle,
        current_seen_pairs=_seen() if seen is None else seen,
        raw_evidence_row=_row() if row is None else row,
        frozen_manifest_projection=_manifest() if manifest is None else manifest)


def _state_of(snapshot, key):
    return snapshot.slots_by_identity[key].lifecycle_state


# --- module identity / API shape ------------------------------------------------------------------

def test_component_name_constant():
    assert ATOMIC_REPLAY_STEP_COMPONENT_NAME == "phase6_2_shadow_intent_atomic_replay_step"


def test_callable_is_strict_keyword_only():
    sig = inspect.signature(execute_atomic_replay_step)
    assert list(sig.parameters) == [
        "current_lifecycle_snapshot", "current_seen_pairs", "raw_evidence_row", "frozen_manifest_projection"]
    for p in sig.parameters.values():
        assert p.kind is inspect.Parameter.KEYWORD_ONLY
        assert p.default is inspect.Parameter.empty


def test_positional_missing_extra_misnamed_args_raise_typeerror():
    lc, sp, row, man = _lifecycle(), _seen(), _row(), _manifest()
    with pytest.raises(TypeError):
        execute_atomic_replay_step(lc, sp, row, man)                       # positional
    with pytest.raises(TypeError):
        execute_atomic_replay_step(current_lifecycle_snapshot=lc, current_seen_pairs=sp,
                                   raw_evidence_row=row)                    # missing
    with pytest.raises(TypeError):
        execute_atomic_replay_step(current_lifecycle_snapshot=lc, current_seen_pairs=sp,
                                   raw_evidence_row=row, frozen_manifest_projection=man, extra=1)  # extra
    with pytest.raises(TypeError):
        execute_atomic_replay_step(current_lifecycle_snapshot=lc, current_seen_pairs=sp,
                                   raw_evidence_row=row, manifest=man)      # misnamed


def test_no_frozen_manifest_projection_or_role_alias_symbols():
    assert not hasattr(ars, "FrozenManifestProjection")
    for forbidden in ("RowStartShadowSnapshot", "NextShadowSnapshot",
                      "RowStartSeenTargetPairs", "NextSeenTargetPairs"):
        assert not hasattr(ars, forbidden), forbidden


# --- AtomicReplayStepResult exact shape -----------------------------------------------------------

def test_result_exact_two_field_shape_frozen_slots_kwonly():
    fields = AtomicReplayStepResult.__dataclass_fields__
    assert list(fields) == ["next_lifecycle_snapshot", "next_seen_target_pairs"]
    params = AtomicReplayStepResult.__dataclass_params__
    assert params.frozen is True and params.kw_only is True
    assert not hasattr(AtomicReplayStepResult, "__dict__") or "__slots__" in vars(AtomicReplayStepResult)
    # directly keyword-constructible (no factory)
    res = AtomicReplayStepResult(next_lifecycle_snapshot=_lifecycle(), next_seen_target_pairs=_seen())
    assert type(res) is AtomicReplayStepResult


def test_result_is_methodless_except_post_init():
    own = {n for n, v in vars(AtomicReplayStepResult).items()
           if callable(v) and not n.startswith("__")}
    assert own == set(), own


def test_result_post_init_rejects_forged_and_missing_slot_snapshots():
    good_seen = _seen()
    forged_lc = object.__new__(lm.ShadowLifecycleSnapshot)            # missing slot
    with pytest.raises(AtomicReplayStepError) as e1:
        AtomicReplayStepResult(next_lifecycle_snapshot=forged_lc, next_seen_target_pairs=good_seen)
    assert e1.value.reason == STEP_PUBLICATION_INVARIANT_VIOLATION
    with pytest.raises(AtomicReplayStepError) as e2:
        AtomicReplayStepResult(next_lifecycle_snapshot=_lifecycle(), next_seen_target_pairs="not-a-snapshot")
    assert e2.value.reason == STEP_PUBLICATION_INVARIANT_VIOLATION


# --- AtomicReplayStepError exact API --------------------------------------------------------------

def test_error_is_valueerror_with_reason_and_message():
    err = AtomicReplayStepError("STEP_DUPLICATE_ROOT", "msg")
    assert isinstance(err, ValueError)
    assert err.reason == "STEP_DUPLICATE_ROOT"
    assert str(err) == "msg"


def test_ten_reason_vocabulary_is_closed_and_distinct():
    reasons = {
        STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT, STEP_INVALID_CURRENT_SEEN_PAIRS,
        STEP_INVALID_MANIFEST_PROJECTION, STEP_EVIDENCE_PROJECTION_REJECTED,
        STEP_CLASSIFICATION_PREDICATE_REJECTED, STEP_MANIFEST_DEFINITION_ABSENT,
        STEP_DUPLICATE_ROOT, STEP_TARGETED_NON_SCORE_ROOT,
        STEP_INVALID_LIFECYCLE_TRANSITION, STEP_PUBLICATION_INVARIANT_VIOLATION,
    }
    assert len(reasons) == 10


# --- consumer-boundary input revalidation + precedence --------------------------------------------

def test_invalid_lifecycle_snapshot_reason():
    with pytest.raises(AtomicReplayStepError) as exc:
        _call(lifecycle="not-a-snapshot")
    assert exc.value.reason == STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT


def test_invalid_lifecycle_snapshot_missing_slot_forgery():
    forged = object.__new__(lm.ShadowLifecycleSnapshot)
    with pytest.raises(AtomicReplayStepError) as exc:
        _call(lifecycle=forged)
    assert exc.value.reason == STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT


def test_invalid_seen_pairs_reason():
    with pytest.raises(AtomicReplayStepError) as exc:
        _call(seen="not-a-snapshot")
    assert exc.value.reason == STEP_INVALID_CURRENT_SEEN_PAIRS


def test_invalid_manifest_reason_and_missing_slot_forgery():
    with pytest.raises(AtomicReplayStepError) as e1:
        _call(manifest="not-a-manifest")
    assert e1.value.reason == STEP_INVALID_MANIFEST_PROJECTION
    forged = object.__new__(lm.ShadowIntentDefinitionArtifact)
    with pytest.raises(AtomicReplayStepError) as e2:
        _call(manifest=forged)
    assert e2.value.reason == STEP_INVALID_MANIFEST_PROJECTION


def test_input_revalidation_precedence_lifecycle_then_seen_then_manifest():
    # all three invalid -> lifecycle reason first (fixed parameter order, before any row logic).
    with pytest.raises(AtomicReplayStepError) as e_lc:
        execute_atomic_replay_step(current_lifecycle_snapshot="x", current_seen_pairs="y",
                                   raw_evidence_row=_row(), frozen_manifest_projection="z")
    assert e_lc.value.reason == STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT
    # lifecycle valid, seen + manifest invalid -> seen reason next.
    with pytest.raises(AtomicReplayStepError) as e_seen:
        execute_atomic_replay_step(current_lifecycle_snapshot=_lifecycle(), current_seen_pairs="y",
                                   raw_evidence_row=_row(), frozen_manifest_projection="z")
    assert e_seen.value.reason == STEP_INVALID_CURRENT_SEEN_PAIRS


# --- no-op / identity matrix (§5.1) ---------------------------------------------------------------

def test_non_targeted_irrelevant_row_is_noop_identity():
    lc, sp = _lifecycle(), _seen()
    row = _row(artifact_locator="OTHER", physical_record_position="X")   # not a manifest target
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=_manifest())
    assert res.next_lifecycle_snapshot is lc
    assert res.next_seen_target_pairs is sp
    assert type(res) is AtomicReplayStepResult


def test_terminal_slot_self_loops_without_reading_context_identity():
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=lm.INTENT_EXPIRED)))
    sp = _seen(k)
    # context-equal in-window SCORE from a different (non-target) pair; terminal slot ignores it.
    row = _row(artifact_locator="OTHER", physical_record_position="X", venue="hl", pair="BTC",
               provenance_timestamp="1500")
    res = _call(lifecycle=lc, seen=sp, row=row)
    assert res.next_lifecycle_snapshot is lc and res.next_seen_target_pairs is sp


def test_context_inequality_is_noop_even_with_unreached_malformed_magnitude():
    k = _key()
    lc = _lifecycle((k, _slot(key=k, venue="hl", pair="BTC")))
    sp = _seen(k)
    # context (kraken, ETH) != slot (hl, BTC); magnitude is malformed but NEVER reached (strict-lazy).
    row = _row(artifact_locator="OTHER", physical_record_position="X",
               venue="kraken", pair="ETH", magnitude="not-a-decimal", provenance_timestamp="1500")
    res = _call(lifecycle=lc, seen=sp, row=row)
    assert res.next_lifecycle_snapshot is lc and res.next_seen_target_pairs is sp


def test_inert_in_window_is_noop():
    k = _key()
    lc = _lifecycle((k, _slot(key=k)))
    sp = _seen(k)
    manifest = _manifest((k, _inert()))
    row = _row(artifact_locator="OTHER", physical_record_position="X", provenance_timestamp="1500")
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert res.next_lifecycle_snapshot is lc and res.next_seen_target_pairs is sp


def test_negative_delta_is_noop():
    k = _key()
    lc = _lifecycle((k, _slot(key=k, anchor="1000")))
    sp = _seen(k)
    row = _row(artifact_locator="OTHER", physical_record_position="X", provenance_timestamp="500")
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=_manifest((k, _directional())))
    assert res.next_lifecycle_snapshot is lc and res.next_seen_target_pairs is sp


def test_unit_mismatch_later_observation_is_noop():
    k = _key()
    lc = _lifecycle((k, _slot(key=k)))
    sp = _seen(k)
    manifest = _manifest((k, _directional(unit="proportion")))
    row = _row(artifact_locator="OTHER", physical_record_position="X",
               unit="ratio", magnitude="2.0", provenance_timestamp="1500")
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert res.next_lifecycle_snapshot is lc and res.next_seen_target_pairs is sp


def test_below_boundary_crossing_is_noop():
    k = _key()
    lc = _lifecycle((k, _slot(key=k)))
    sp = _seen(k)
    manifest = _manifest((k, _directional(orientation=lm.POSITIVE_EXPOSURE, magnitude="1.5")))
    row = _row(artifact_locator="OTHER", physical_record_position="X",
               magnitude="1.4", provenance_timestamp="1500")
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert res.next_lifecycle_snapshot is lc and res.next_seen_target_pairs is sp


def test_sustaining_met_condition_is_noop_identity():
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=lm.HYPOTHETICAL_CONDITION_MET)))
    sp = _seen(k)
    manifest = _manifest((k, _directional(magnitude="1.5")))
    row = _row(artifact_locator="OTHER", physical_record_position="X",
               magnitude="2.0", provenance_timestamp="1500")
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert res.next_lifecycle_snapshot is lc and res.next_seen_target_pairs is sp


# --- establishment / transitions matrix -----------------------------------------------------------

def test_first_target_directional_establishment_adds_slot_and_pair():
    k = _key()
    lc, sp = _lifecycle(), _seen()
    manifest = _manifest((k, _directional(unit="proportion")))
    row = _row(artifact_locator="loc", physical_record_position="pos",
               venue="hl", pair="BTC", unit="proportion", provenance_timestamp="1000")
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert res.next_lifecycle_snapshot is not lc and res.next_seen_target_pairs is not sp
    assert _state_of(res.next_lifecycle_snapshot, k) == lm.INTENT_RECORDED
    assert k in res.next_seen_target_pairs.seen_target_pairs
    slot = res.next_lifecycle_snapshot.slots_by_identity[k]
    assert type(slot.root_evidence) is lm.EstablishedRootEvidence
    assert slot.root_evidence.provenance_anchor_timestamp_text == "1000"
    assert slot.root_evidence.root_context.source_venue_context_text == "hl"
    assert slot.root_evidence.root_context.source_pair_context_text == "BTC"


def test_inert_root_establishment_records_intent():
    k = _key()
    manifest = _manifest((k, _inert()))
    row = _row(artifact_locator="loc", physical_record_position="pos", unit="ANYTHING")
    res = _call(row=row, manifest=manifest)
    assert _state_of(res.next_lifecycle_snapshot, k) == lm.INTENT_RECORDED
    assert k in res.next_seen_target_pairs.seen_target_pairs


def test_root_unit_mismatch_is_permanent_non_establishment_but_commits_seen():
    k = _key()
    lc, sp = _lifecycle(), _seen()
    manifest = _manifest((k, _directional(unit="proportion")))
    row = _row(artifact_locator="loc", physical_record_position="pos", unit="ratio")
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    # slot added as permanently non-established AUDIT_REPLAYED + NoRootEvidence; pair committed seen.
    assert res.next_lifecycle_snapshot is not lc and res.next_seen_target_pairs is not sp
    slot = res.next_lifecycle_snapshot.slots_by_identity[k]
    assert slot.lifecycle_state == lm.AUDIT_REPLAYED
    assert type(slot.root_evidence) is lm.NoRootEvidence
    assert k in res.next_seen_target_pairs.seen_target_pairs


def test_later_row_crossing_records_met_lifecycle_fresh_seen_identity():
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=lm.INTENT_RECORDED, anchor="1000")))
    sp = _seen(k)
    manifest = _manifest((k, _directional(orientation=lm.POSITIVE_EXPOSURE, magnitude="1.5",
                                          unit="proportion", duration=840000)))
    row = _row(artifact_locator="OTHER", physical_record_position="X",
               venue="hl", pair="BTC", unit="proportion", magnitude="2.0", provenance_timestamp="1500")
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert _state_of(res.next_lifecycle_snapshot, k) == lm.HYPOTHETICAL_CONDITION_MET
    assert res.next_lifecycle_snapshot is not lc
    assert res.next_seen_target_pairs is sp                       # no new target -> identity


def test_later_row_expiry_records_expired():
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=lm.INTENT_RECORDED, anchor="1000")))
    sp = _seen(k)
    manifest = _manifest((k, _directional(duration=840000)))
    row = _row(artifact_locator="OTHER", physical_record_position="X",
               provenance_timestamp="900000")                     # delta 899000 > 840000
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert _state_of(res.next_lifecycle_snapshot, k) == lm.INTENT_EXPIRED
    assert res.next_seen_target_pairs is sp


def test_met_to_expired_transition():
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=lm.HYPOTHETICAL_CONDITION_MET, anchor="1000")))
    sp = _seen(k)
    manifest = _manifest((k, _directional(duration=840000)))
    row = _row(artifact_locator="OTHER", physical_record_position="X", provenance_timestamp="900000")
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert _state_of(res.next_lifecycle_snapshot, k) == lm.INTENT_EXPIRED


def test_expiry_precedes_crossing():
    # a row that WOULD cross (magnitude over boundary) but is past the window -> expiry, not met.
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=lm.INTENT_RECORDED, anchor="1000")))
    sp = _seen(k)
    manifest = _manifest((k, _directional(magnitude="1.5", duration=5)))
    row = _row(artifact_locator="OTHER", physical_record_position="X",
               magnitude="2.0", provenance_timestamp="1006")       # delta 6 > 5
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert _state_of(res.next_lifecycle_snapshot, k) == lm.INTENT_EXPIRED


def test_inclusive_window_boundary_delta_equals_duration_crosses():
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=lm.INTENT_RECORDED, anchor="1000")))
    sp = _seen(k)
    manifest = _manifest((k, _directional(magnitude="1.5", duration=5)))
    row = _row(artifact_locator="OTHER", physical_record_position="X",
               magnitude="2.0", provenance_timestamp="1005")       # delta 5 == duration -> in-window
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert _state_of(res.next_lifecycle_snapshot, k) == lm.HYPOTHETICAL_CONDITION_MET


# --- duplicate-root primacy -----------------------------------------------------------------------

@pytest.mark.parametrize("state,evidence", [
    (lm.INTENT_RECORDED, _UNSET),
    (lm.HYPOTHETICAL_CONDITION_MET, _UNSET),
    (lm.INTENT_EXPIRED, _UNSET),
    (lm.INTENT_RETIRED, _UNSET),
    (lm.AUDIT_REPLAYED, _UNSET),       # committed-seen unit-mismatch pair (NoRootEvidence)
])
def test_duplicate_root_fires_regardless_of_slot_state(state, evidence):
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=state, evidence=evidence)))
    sp = _seen(k)
    manifest = _manifest((k, _directional()))
    row = _row(artifact_locator="loc", physical_record_position="pos")    # same targeted pair -> duplicate
    with pytest.raises(AtomicReplayStepError) as exc:
        _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert exc.value.reason == STEP_DUPLICATE_ROOT


def test_duplicate_precedes_terminal_and_inspection():
    # terminal slot + duplicate targeted pair + malformed row payload -> still DUPLICATE (immediate).
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=lm.INTENT_EXPIRED)))
    sp = _seen(k)
    manifest = _manifest((k, _directional()))
    row = _row(artifact_locator="loc", physical_record_position="pos", payload="{not json")
    with pytest.raises(AtomicReplayStepError) as exc:
        _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert exc.value.reason == STEP_DUPLICATE_ROOT


# --- targeted non-SCORE root ----------------------------------------------------------------------

def test_targeted_non_score_root_hard_fails():
    k = _key()
    manifest = _manifest((k, _directional()))
    row = _row(artifact_locator="loc", physical_record_position="pos", observation_kind="HALT")
    with pytest.raises(AtomicReplayStepError) as exc:
        _call(row=row, manifest=manifest)
    assert exc.value.reason == STEP_TARGETED_NON_SCORE_ROOT


# --- manifest definition absent (category-2 row-start slot lookup) --------------------------------

def test_manifest_definition_absent_for_established_slot_not_in_manifest():
    k_slot = _key("SLOTLOC", "SLOTPOS")          # established slot key NOT present in the manifest
    lc = _lifecycle((k_slot, _slot(key=k_slot, state=lm.INTENT_RECORDED, anchor="1000")))
    sp = _seen(k_slot)
    manifest = _manifest((_key("OTHER", "DEF"), _directional()))   # different key only
    row = _row(artifact_locator="ROWLOC", physical_record_position="ROWPOS",
               venue="hl", pair="BTC", provenance_timestamp="1500")   # context-equal, non-target
    with pytest.raises(AtomicReplayStepError) as exc:
        _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert exc.value.reason == STEP_MANIFEST_DEFINITION_ABSENT


# --- evidence projection rejected (reached projection only) ---------------------------------------

def test_root_malformed_context_is_evidence_projection_rejected():
    k = _key()
    manifest = _manifest((k, _directional()))
    bad_payload = json.dumps({
        "observation_kind": "SCORE", "provenance_timestamp": 1000,
        "family_payload": {"score_family_descriptor": "passive_net_edge_diagnostic",
                           "score_inputs_summary": ["only-one"],      # not exactly two
                           "score_unit_context": "proportion",
                           "passive_score_magnitude": "2.0"}})
    row = _row(artifact_locator="loc", physical_record_position="pos", payload=bad_payload)
    with pytest.raises(AtomicReplayStepError) as exc:
        _call(row=row, manifest=manifest)
    assert exc.value.reason == STEP_EVIDENCE_PROJECTION_REJECTED


def test_relevance_scoped_malformed_context_hard_fails_when_active_slot_needs_it():
    # established non-terminal slot present; a SCORE row with malformed context -> hard fail (relevance).
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=lm.INTENT_RECORDED)))
    sp = _seen(k)
    manifest = _manifest((k, _directional()))
    bad_payload = json.dumps({
        "observation_kind": "SCORE", "provenance_timestamp": 1500,
        "family_payload": {"score_family_descriptor": "passive_net_edge_diagnostic",
                           "score_inputs_summary": ["x", "y", "z"],     # three -> malformed
                           "score_unit_context": "proportion",
                           "passive_score_magnitude": "2.0"}})
    row = _row(artifact_locator="OTHER", physical_record_position="X", payload=bad_payload)
    with pytest.raises(AtomicReplayStepError) as exc:
        _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert exc.value.reason == STEP_EVIDENCE_PROJECTION_REJECTED


# --- identity / atomicity / determinism -----------------------------------------------------------

def test_inputs_never_mutated_on_success_and_failure():
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=lm.INTENT_RECORDED, anchor="1000")))
    sp = _seen(k)
    manifest = _manifest((k, _directional(magnitude="1.5")))
    lc_before = dict(lc.slots_by_identity)
    sp_before = set(sp.seen_target_pairs)
    row = _row(artifact_locator="OTHER", physical_record_position="X",
               magnitude="2.0", provenance_timestamp="1500")
    _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert dict(lc.slots_by_identity) == lc_before and set(sp.seen_target_pairs) == sp_before
    # failure path: duplicate -> no mutation
    dup_row = _row(artifact_locator="loc", physical_record_position="pos")
    with pytest.raises(AtomicReplayStepError):
        _call(lifecycle=lc, seen=sp, row=dup_row, manifest=manifest)
    assert dict(lc.slots_by_identity) == lc_before and set(sp.seen_target_pairs) == sp_before


def test_repeated_identical_inputs_are_deterministic():
    k = _key()
    lc = _lifecycle((k, _slot(key=k, state=lm.INTENT_RECORDED, anchor="1000")))
    sp = _seen(k)
    manifest = _manifest((k, _directional(magnitude="1.5")))
    row1 = _row(artifact_locator="OTHER", physical_record_position="X",
                magnitude="2.0", provenance_timestamp="1500")
    row2 = _row(artifact_locator="OTHER", physical_record_position="X",
                magnitude="2.0", provenance_timestamp="1500")
    r1 = _call(lifecycle=lc, seen=sp, row=row1, manifest=manifest)
    r2 = _call(lifecycle=lc, seen=sp, row=row2, manifest=manifest)
    assert r1.next_lifecycle_snapshot == r2.next_lifecycle_snapshot
    assert r1.next_seen_target_pairs == r2.next_seen_target_pairs
    assert r1.next_seen_target_pairs is sp and r2.next_seen_target_pairs is sp


def test_every_success_allocates_fresh_result_even_for_noop():
    lc, sp = _lifecycle(), _seen()
    r1 = _call(lifecycle=lc, seen=sp, row=_row(artifact_locator="OTHER", physical_record_position="X"))
    r2 = _call(lifecycle=lc, seen=sp, row=_row(artifact_locator="OTHER", physical_record_position="X"))
    assert r1 is not r2
    assert r1.next_lifecycle_snapshot is lc and r2.next_lifecycle_snapshot is lc


def test_multi_intent_one_row_establishes_own_slot_and_updates_other():
    # one SCORE is the first root for k_root AND a later crossing observation for k_other.
    k_root = _key("ROOTLOC", "ROOTPOS")
    k_other = _key("OTHERLOC", "OTHERPOS")
    lc = _lifecycle((k_other, _slot(key=k_other, state=lm.INTENT_RECORDED,
                                    venue="hl", pair="BTC", anchor="1000")))
    sp = _seen(k_other)
    manifest = _manifest((k_root, _directional(unit="proportion")),
                         (k_other, _directional(orientation=lm.POSITIVE_EXPOSURE, magnitude="1.5",
                                                unit="proportion", duration=840000)))
    row = _row(artifact_locator="ROOTLOC", physical_record_position="ROOTPOS",
               venue="hl", pair="BTC", unit="proportion", magnitude="2.0", provenance_timestamp="1500")
    res = _call(lifecycle=lc, seen=sp, row=row, manifest=manifest)
    assert _state_of(res.next_lifecycle_snapshot, k_root) == lm.INTENT_RECORDED       # own slot established
    assert _state_of(res.next_lifecycle_snapshot, k_other) == lm.HYPOTHETICAL_CONDITION_MET  # other updated
    assert k_root in res.next_seen_target_pairs.seen_target_pairs


# --- AST locks: row opacity, delegation, guarded reads, single lookup, forbidden behavior ----------

def _module_text():
    return pathlib.Path(ars.__file__).resolve().read_text(encoding="utf-8")


def _module_ast():
    return ast.parse(_module_text())


def _runtime_code_tokens():
    # the module's CODE token identifiers only (string literals and comments excluded), so a forbidden
    # token recited in the docstring disclaimer can never satisfy a behavioral lock — only real code does.
    tokens = set()
    for tok in tokenize.generate_tokens(io.StringIO(_module_text()).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT, tokenize.FSTRING_MIDDLE):
            continue
        tokens.add(tok.string)
    return tokens


def test_no_sqlite_import_and_row_opacity():
    code = _runtime_code_tokens()
    for token in ("sqlite3", "row_factory", "fetchone", "keys", "json", "loads"):
        assert token not in code, token
    tree = _module_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            assert node.value.id != "raw_evidence_row", "row must not be indexed"
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            assert node.value.id != "raw_evidence_row", "row must not be attribute-read"
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Name):
            assert node.iter.id != "raw_evidence_row", "row must not be iterated"


_CARRIER_FIELD_NAMES = frozenset({
    "slots_by_identity", "seen_target_pairs", "shadow_intent_identity_reference", "lifecycle_state",
    "root_evidence", "root_context", "provenance_anchor_timestamp_text", "source_venue_context_text",
    "source_pair_context_text", "exposure_orientation", "passive_boundary_magnitude",
    "boundary_unit_context", "hypothetical_window_duration_ms", "definitions_by_silver_pair",
    "silver_artifact_locator", "silver_physical_record_position", "score_inputs_summary",
    "provenance_timestamp", "score_unit_context", "passive_score_magnitude",
    "passive_score_magnitude_text", "observation_kind", "family_descriptor",
})


def test_all_carrier_field_reads_are_slot_value_guarded():
    # no direct ``.<carrier_field>`` attribute read anywhere in the runtime: all via lm._slot_value.
    for node in ast.walk(_module_ast()):
        if isinstance(node, ast.Attribute):
            assert node.attr not in _CARRIER_FIELD_NAMES, "unguarded carrier read: .{}".format(node.attr)


def test_single_manifest_lookup_site():
    # exactly one subscript site indexes the manifest definitions mapping (bound to local name ``defs``).
    subscripts = [n for n in ast.walk(_module_ast())
                  if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "defs"]
    assert len(subscripts) == 1, len(subscripts)


def test_predicates_and_projections_delegated_not_reimplemented():
    text = _module_text()
    # Slice-C/D are imported and called; no re-coded projection/predicate primitives.
    for token in ("re.compile", "Decimal(", "import decimal", "_PHASE5", "def project_",
                  "InvalidOperation"):
        assert token not in text, token
    for needed in ("project_silver_pair", "context_equals", "classify_timestamp_window",
                   "classify_directional_crossing", "unit_comparable"):
        assert needed in text, needed


def test_no_execution_routing_cache_or_clock_tokens():
    # behavioral identifiers must be absent from CODE (docstring disclaimers excepted).
    code = _runtime_code_tokens()
    for token in ("routing", "broker", "exchange", "paper", "canary", "capacity",
                  "threading", "asyncio", "socket", "time", "registry", "singleton", "global",
                  "open", "connect", "cache"):
        assert token not in code, token


def test_no_broad_exception_catch():
    for node in ast.walk(_module_ast()):
        if isinstance(node, ast.ExceptHandler):
            assert node.type is not None, "bare except is forbidden"
            names = []
            if isinstance(node.type, ast.Name):
                names = [node.type.id]
            elif isinstance(node.type, ast.Tuple):
                names = [e.id for e in node.type.elts if isinstance(e, ast.Name)]
            for n in names:
                assert n not in ("Exception", "BaseException"), n
