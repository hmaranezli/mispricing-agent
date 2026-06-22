"""tests/test_phase6_2_reconstruction.py — Phase 6.2 Slice-F reconstruction-fold suite.

Governing contract: ``docs/handoff/phase6_2_slice_f_reconstruction_loop_exact_shape_charter.md``
(base ``04a20eb``). Slice F is a pure sequencer/folder over an already-materialized tuple of opaque
S1 replay rows and one verified manifest artifact: it seeds factory-fresh empty snapshots, threads each
``execute_atomic_replay_step`` result by identity, returns the final Slice-E carrier unwrapped (or a fresh
empty carrier for an empty replay), defines no error class, contains no ``try``/``except``, and adds only
O(1) loop/reference/carrier overhead.

Successful evidence is genuine only: replay rows come solely from ``S1DurableSqliteSink.replay()`` after
genuine ``record_observation`` of records produced by the proven S5 pipeline; the verified manifest comes
solely from ``verify_artifact``. Negative rows come solely from the quarantined negative-evidence fixture
and are used only for rejection/failure tests. ``id(...)`` is never used in this suite.
"""
import ast
import hashlib
import importlib.util
import inspect
import io
import json
import pathlib

import pytest

import phase6_2_shadow_intent.reconstruction as recon
from phase6_2_shadow_intent.reconstruction import reconstruct_shadow_intent_state
from phase6_2_shadow_intent import logical_model as lm
from phase6_2_shadow_intent import artifact_verifier as av
from phase6_2_shadow_intent.atomic_replay_step import (
    execute_atomic_replay_step,
    AtomicReplayStepResult,
    AtomicReplayStepError,
    STEP_EVIDENCE_PROJECTION_REJECTED,
)

from phase6_1.s1_in_memory_observation_sink import S1InMemoryObservationSink
from phase6_1.s5_runner import run_in_memory_shadow_pipeline
from phase6_1.market_provenance_context import MarketProvenanceContext
from phase6_1.gross_edge_binding_label_context import GrossEdgeBindingLabelContext
from phase6_1_s1_storage.s1_durable_sqlite_sink import S1DurableSqliteSink


# --- load the quarantined negative-evidence helper by path (tests/ is not a package) --------------
_FIXTURE_PATH = pathlib.Path(__file__).resolve().parent / "fixtures" / "phase6_2_negative_evidence_rows.py"
_neg_spec = importlib.util.spec_from_file_location("_phase6_2_negative_evidence_rows_slf", _FIXTURE_PATH)
neg = importlib.util.module_from_spec(_neg_spec)
_neg_spec.loader.exec_module(neg)


# --- runtime source path (independent of importing the module under test) -------------------------
_RUNTIME_PATH = pathlib.Path(lm.__file__).resolve().parent / "reconstruction.py"


def _runtime_text():
    return _RUNTIME_PATH.read_text(encoding="utf-8")


def _runtime_ast():
    return ast.parse(_runtime_text())


# --- genuine S5 -> S1 evidence (success rows only) ------------------------------------------------
_PASS_LINE = (
    '{"gross_magnitude": "7", "unit": "proportion", "venue": "hl", "pair": "BTC", '
    '"observed_at_epoch_ms": "1750000000000"}\n'
)
_MALFORMED_LINE = '{bad json not parseable\n'


def _provenance():
    return MarketProvenanceContext(
        source_artifact="docs/handoff/replay_artifact_lines",
        source_field="replay.line",
        base_asset="BTC", quote_asset="USD", instrument_id="BTC-USD-PERP",
        venue_scope="hyperliquid_perp", venue_buy="hyperliquid", venue_sell="hyperliquid",
        retrieval_epoch_ms=1_750_000_000_500, raw_snapshot_identity="market-identity-0001",
    )


def _label():
    return GrossEdgeBindingLabelContext(
        normalized_field_name="gross_edge_magnitude", source_field="raw.gross_magnitude",
    )


def _genuine_records(locator="loc"):
    """A genuine (ObservationScoreRecord, ObservationHaltRecord) pair from the proven S5 pipeline."""
    mem = S1InMemoryObservationSink()
    run_in_memory_shadow_pipeline(
        text_stream=io.StringIO(_PASS_LINE + _MALFORMED_LINE),
        artifact_locator=locator,
        market_provenance_context=_provenance(),
        gross_edge_binding_label_context=_label(),
        evidence_epoch_tolerance_ms=0,
        observation_sink=mem,
    )
    return mem.snapshot()


def _genuine_replay_rows(tmp_path, *, record_halt=True, name="s1.db"):
    """Return the genuine immutable replay tuple straight from S1DurableSqliteSink.replay()."""
    score, halt = _genuine_records()
    sink = S1DurableSqliteSink(database_path=str(tmp_path / name))
    try:
        sink.record_observation(score)
        if record_halt:
            sink.record_observation(halt)
        rows = sink.replay()
    finally:
        sink.close()
    return rows


# --- genuine verified manifest (Slice-B only) -----------------------------------------------------
_FSV = "PHASE6_2_SHADOW_INTENT_DEFINITION_ARTIFACT_FIELD_SHAPE_V1"


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(b):
    return hashlib.sha256(b).hexdigest()


def _artifact_bytes(definitions=()):
    root = {
        "artifact_field_shape_version_reference": _FSV,
        "artifact_version_reference": "v1",
        "declarer_opaque_reference": "decl",
        "predecessor_artifact_version_reference": {"kind": "NO_PREDECESSOR"},
        "definitions_by_silver_pair": list(definitions),
    }
    return _canon(root)


def _verified_manifest(definitions=()):
    data = _artifact_bytes(definitions)
    reference = av.make_sealed_artifact_reference(
        opaque_artifact_locator="opaque-locator", expected_detached_sha256_digest=_digest(data)
    )
    return av.verify_artifact(reference=reference, binary_stream=io.BytesIO(data))


def _verified_manifest_targeting_baseline():
    """A genuine verified manifest whose single definition targets the negative fixture's Silver pair."""
    definition = {
        "definition_kind": "DIRECTIONAL_SHADOW_INTENT_DEFINITION",
        "silver_artifact_locator_text": "opaque-artifact-locator",
        "silver_physical_record_position_text": "0",
        "exposure_orientation": "POSITIVE_EXPOSURE",
        "passive_boundary_magnitude": "1.5",
        "boundary_unit_context": "proportion",
        "hypothetical_window_duration_ms": "840000",
    }
    return _verified_manifest(definitions=(definition,))


def _negative_row():
    return neg.build_negative_evidence_row(case=neg.MALFORMED_CANONICAL_JSON)


def _empty_lifecycle():
    return lm.make_shadow_lifecycle_snapshot(slot_entries=())


def _empty_seen():
    return lm.make_seen_target_pairs_snapshot(members=())


# --- genuine state-changing evidence: two valid lines -> two SCORE rows, manifest targets the first
# Pinned expected Silver-pair coordinates of the first adapter-produced replay row; the genuine adapter
# row is asserted to match these (never derived from a fabricated row).
_GENUINE_FIRST_LOCATOR = "loc"
_GENUINE_FIRST_POSITION = "0"


def _genuine_two_score_rows(tmp_path, name="s1_stateful.db"):
    """Return the genuine immutable replay tuple of two SCORE rows from two valid pipeline lines.

    Both rows share locator ``loc`` with distinct physical_record_positions, so a manifest targeting the
    first row establishes one shadow intent while the second row stays a non-targeted Slice-E no-op.
    """
    mem = S1InMemoryObservationSink()
    run_in_memory_shadow_pipeline(
        text_stream=io.StringIO(_PASS_LINE + _PASS_LINE),
        artifact_locator="loc",
        market_provenance_context=_provenance(),
        gross_edge_binding_label_context=_label(),
        evidence_epoch_tolerance_ms=0,
        observation_sink=mem,
    )
    score_first, score_second = mem.snapshot()
    sink = S1DurableSqliteSink(database_path=str(tmp_path / name))
    try:
        sink.record_observation(score_first)
        sink.record_observation(score_second)
        rows = sink.replay()
    finally:
        sink.close()
    return rows


def _verified_manifest_targeting_first_genuine_row():
    """A genuine verified manifest (Slice-B output) whose single directional definition targets the first
    adapter-produced SCORE row (locator ``loc`` / position ``0``)."""
    definition = {
        "definition_kind": "DIRECTIONAL_SHADOW_INTENT_DEFINITION",
        "silver_artifact_locator_text": _GENUINE_FIRST_LOCATOR,
        "silver_physical_record_position_text": _GENUINE_FIRST_POSITION,
        "exposure_orientation": "POSITIVE_EXPOSURE",
        "passive_boundary_magnitude": "1.5",
        "boundary_unit_context": "proportion",
        "hypothetical_window_duration_ms": "840000",
    }
    return _verified_manifest(definitions=(definition,))


def _expected_genuine_key():
    return lm.make_opaque_silver_pair_key(
        silver_artifact_locator_text=_GENUINE_FIRST_LOCATOR,
        silver_physical_record_position_text=_GENUINE_FIRST_POSITION,
    )


# === 1. EXACT PUBLIC API ==========================================================================

def test_reconstruction_module_and_callable_exist():
    assert _RUNTIME_PATH.exists()
    assert callable(reconstruct_shadow_intent_state)
    assert reconstruct_shadow_intent_state.__name__ == "reconstruct_shadow_intent_state"


def test_callable_is_keyword_only_with_exact_params_in_order():
    sig = inspect.signature(reconstruct_shadow_intent_state)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["ordered_replay_rows", "verified_manifest_artifact"]
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params)
    assert all(p.default is inspect.Parameter.empty for p in params)


def test_callable_has_no_varargs_varkw_or_extra_entrypoints():
    sig = inspect.signature(reconstruct_shadow_intent_state)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds
    # the module exposes exactly one public callable name
    public = [n for n in vars(recon) if not n.startswith("_") and callable(getattr(recon, n))
              and getattr(getattr(recon, n), "__module__", None) == recon.__name__]
    assert public == ["reconstruct_shadow_intent_state"]


def test_exact_live_class_annotations_no_strings():
    ann = reconstruct_shadow_intent_state.__annotations__
    assert ann["ordered_replay_rows"] == tuple[object, ...]
    assert ann["verified_manifest_artifact"] is lm.ShadowIntentDefinitionArtifact
    assert ann["return"] is AtomicReplayStepResult
    for value in ann.values():
        assert not isinstance(value, str)


def test_runtime_has_no_future_annotations_import():
    assert "from __future__ import annotations" not in _runtime_text()


# === 2. EXACT GUARDS AND PRECEDENCE ===============================================================

def test_rows_guard_exact_message():
    with pytest.raises(TypeError) as exc:
        reconstruct_shadow_intent_state(ordered_replay_rows=[], verified_manifest_artifact=_verified_manifest())
    assert str(exc.value) == "ordered_replay_rows must be an exact tuple"


def test_artifact_guard_exact_message():
    with pytest.raises(TypeError) as exc:
        reconstruct_shadow_intent_state(ordered_replay_rows=(), verified_manifest_artifact="not-an-artifact")
    assert str(exc.value) == "verified_manifest_artifact must be an exact ShadowIntentDefinitionArtifact"


def test_rows_guard_precedes_artifact_guard_when_both_invalid():
    with pytest.raises(TypeError) as exc:
        reconstruct_shadow_intent_state(ordered_replay_rows=[], verified_manifest_artifact="not-an-artifact")
    assert str(exc.value) == "ordered_replay_rows must be an exact tuple"


class _TupleSubclass(tuple):
    pass


@pytest.mark.parametrize("bad_rows", [
    [],
    (object() for _ in range(0)),
    iter(()),
    _TupleSubclass(),
    "()",
    None,
])
def test_non_exact_tuple_rows_rejected(bad_rows):
    with pytest.raises(TypeError) as exc:
        reconstruct_shadow_intent_state(
            ordered_replay_rows=bad_rows, verified_manifest_artifact=_verified_manifest())
    assert str(exc.value) == "ordered_replay_rows must be an exact tuple"


class _ArtifactSubclass(lm.ShadowIntentDefinitionArtifact):
    pass


class _ArtifactLookAlike:
    artifact_field_shape_version_reference = None
    artifact_version_reference = None
    declarer_opaque_reference = None
    predecessor_artifact_version_reference = None
    definitions_by_silver_pair = None


@pytest.mark.parametrize("bad_artifact", [
    "nope",
    object(),
    {"definitions_by_silver_pair": {}},
    _ArtifactLookAlike(),
    object.__new__(_ArtifactSubclass),
])
def test_non_exact_artifact_rejected(bad_artifact):
    with pytest.raises(TypeError) as exc:
        reconstruct_shadow_intent_state(
            ordered_replay_rows=(), verified_manifest_artifact=bad_artifact)
    assert str(exc.value) == "verified_manifest_artifact must be an exact ShadowIntentDefinitionArtifact"


def test_positional_argument_raises_binding_typeerror():
    with pytest.raises(TypeError):
        reconstruct_shadow_intent_state((), _verified_manifest())


def test_missing_argument_raises_binding_typeerror():
    with pytest.raises(TypeError):
        reconstruct_shadow_intent_state(ordered_replay_rows=())


def test_extra_keyword_raises_binding_typeerror():
    with pytest.raises(TypeError):
        reconstruct_shadow_intent_state(
            ordered_replay_rows=(), verified_manifest_artifact=_verified_manifest(), unexpected=1)


def test_misnamed_keyword_raises_binding_typeerror():
    with pytest.raises(TypeError):
        reconstruct_shadow_intent_state(rows=(), verified_manifest_artifact=_verified_manifest())


def test_runtime_defines_no_error_class():
    tree = _runtime_ast()
    assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))


# === 3. FACTORY-FRESH EMPTY REPLAY ================================================================

def test_empty_replay_returns_fresh_result_with_empty_snapshots():
    result = reconstruct_shadow_intent_state(
        ordered_replay_rows=(), verified_manifest_artifact=_verified_manifest())
    assert type(result) is AtomicReplayStepResult
    assert result.next_lifecycle_snapshot == _empty_lifecycle()
    assert result.next_seen_target_pairs == _empty_seen()
    assert result is not None


def test_empty_replay_executes_zero_slice_e_steps(monkeypatch):
    calls = []

    def _spy(**kwargs):
        calls.append(kwargs)
        return execute_atomic_replay_step(**kwargs)

    monkeypatch.setattr(recon, "execute_atomic_replay_step", _spy)
    reconstruct_shadow_intent_state(
        ordered_replay_rows=(), verified_manifest_artifact=_verified_manifest())
    assert calls == []


def test_empty_replay_two_independent_results_distinct_but_equal():
    manifest = _verified_manifest()
    result_a = reconstruct_shadow_intent_state(ordered_replay_rows=(), verified_manifest_artifact=manifest)
    result_b = reconstruct_shadow_intent_state(ordered_replay_rows=(), verified_manifest_artifact=manifest)
    assert result_a is not result_b
    assert result_a.next_lifecycle_snapshot is not result_b.next_lifecycle_snapshot
    assert result_a.next_seen_target_pairs is not result_b.next_seen_target_pairs
    assert result_a == result_b


def test_exact_type_forged_artifact_undetected_on_empty_replay():
    # Documented limitation: an exact-type artifact that never came from verify_artifact passes the
    # type guard; on empty replay no step runs, so Slice F cannot detect the forgery (Slice-B owns it).
    forged = object.__new__(lm.ShadowIntentDefinitionArtifact)
    assert type(forged) is lm.ShadowIntentDefinitionArtifact
    result = reconstruct_shadow_intent_state(ordered_replay_rows=(), verified_manifest_artifact=forged)
    assert type(result) is AtomicReplayStepResult
    assert result.next_lifecycle_snapshot == _empty_lifecycle()
    assert result.next_seen_target_pairs == _empty_seen()


# === 4./5. PURE SEQUENTIAL FOLD OVER GENUINE EVIDENCE =============================================

def test_single_row_success_returns_step_result_by_identity(tmp_path, monkeypatch):
    rows = _genuine_replay_rows(tmp_path, record_halt=False)
    assert len(rows) == 1
    manifest = _verified_manifest()
    records = []

    def _spy(**kwargs):
        result = execute_atomic_replay_step(**kwargs)
        records.append((kwargs, result))
        return result

    monkeypatch.setattr(recon, "execute_atomic_replay_step", _spy)
    final = reconstruct_shadow_intent_state(ordered_replay_rows=rows, verified_manifest_artifact=manifest)

    assert len(records) == 1
    only_kwargs, only_result = records[0]
    assert final is only_result                                  # unwrapped, by identity
    assert only_kwargs["raw_evidence_row"] is rows[0]            # row by identity
    assert only_kwargs["frozen_manifest_projection"] is manifest  # artifact by identity
    assert only_kwargs["current_lifecycle_snapshot"] == _empty_lifecycle()
    assert only_kwargs["current_seen_pairs"] == _empty_seen()
    # non-targeted genuine row is a Slice-E no-op: next snapshots are the seeds by identity
    assert only_result.next_lifecycle_snapshot is only_kwargs["current_lifecycle_snapshot"]
    assert only_result.next_seen_target_pairs is only_kwargs["current_seen_pairs"]


def test_multi_row_success_threads_by_identity_and_returns_final(tmp_path, monkeypatch):
    rows = _genuine_replay_rows(tmp_path)
    assert len(rows) >= 2
    manifest = _verified_manifest()
    records = []

    def _spy(**kwargs):
        result = execute_atomic_replay_step(**kwargs)
        records.append((kwargs, result))
        return result

    monkeypatch.setattr(recon, "execute_atomic_replay_step", _spy)
    final = reconstruct_shadow_intent_state(ordered_replay_rows=rows, verified_manifest_artifact=manifest)

    assert len(records) == len(rows)
    # every row passed once, by identity, in tuple order; same artifact identity every call
    for index, (kwargs, _result) in enumerate(records):
        assert kwargs["raw_evidence_row"] is rows[index]
        assert kwargs["frozen_manifest_projection"] is manifest
    # seed for the first call; identity threading thereafter
    assert records[0][0]["current_lifecycle_snapshot"] == _empty_lifecycle()
    assert records[0][0]["current_seen_pairs"] == _empty_seen()
    for index in range(1, len(records)):
        assert records[index][0]["current_lifecycle_snapshot"] is records[index - 1][1].next_lifecycle_snapshot
        assert records[index][0]["current_seen_pairs"] is records[index - 1][1].next_seen_target_pairs
    # final returned object is exactly the last Slice-E carrier
    assert final is records[-1][1]


def test_fold_does_not_inspect_rows_or_use_sqlite(tmp_path):
    # genuine replay succeeds with an empty verified manifest (every genuine row a Slice-E no-op),
    # proving Slice F never parses/indexes the opaque rows itself.
    rows = _genuine_replay_rows(tmp_path)
    final = reconstruct_shadow_intent_state(
        ordered_replay_rows=rows, verified_manifest_artifact=_verified_manifest())
    assert type(final) is AtomicReplayStepResult


def test_targeted_multi_row_success_grows_state_and_threads_changed_snapshots(tmp_path, monkeypatch):
    rows = _genuine_two_score_rows(tmp_path)
    assert len(rows) == 2
    # the genuine first replay row really carries the pinned Silver-pair coordinates (not fabricated)
    assert rows[0]["artifact_locator"] == _GENUINE_FIRST_LOCATOR
    assert rows[0]["physical_record_position"] == _GENUINE_FIRST_POSITION
    manifest = _verified_manifest_targeting_first_genuine_row()
    expected_key = _expected_genuine_key()
    records = []

    def _spy(**kwargs):
        result = execute_atomic_replay_step(**kwargs)
        records.append((kwargs, result))
        return result

    monkeypatch.setattr(recon, "execute_atomic_replay_step", _spy)
    final = reconstruct_shadow_intent_state(ordered_replay_rows=rows, verified_manifest_artifact=manifest)

    assert len(records) == 2
    first_kwargs, first_result = records[0]
    second_kwargs, _second_result = records[1]

    # first Slice-E call starts empty and changes state into a non-empty, targeted reconstruction
    assert first_kwargs["current_lifecycle_snapshot"] == _empty_lifecycle()
    assert first_kwargs["current_seen_pairs"] == _empty_seen()
    assert len(first_result.next_lifecycle_snapshot.slots_by_identity) == 1
    assert len(first_result.next_seen_target_pairs.seen_target_pairs) == 1
    assert first_result.next_lifecycle_snapshot != _empty_lifecycle()
    assert expected_key in first_result.next_lifecycle_snapshot.slots_by_identity
    assert expected_key in first_result.next_seen_target_pairs.seen_target_pairs

    # second Slice-E call receives the first result's CHANGED snapshots by identity
    assert second_kwargs["current_lifecycle_snapshot"] is first_result.next_lifecycle_snapshot
    assert second_kwargs["current_seen_pairs"] is first_result.next_seen_target_pairs

    # every genuine row passed once, by identity, in tuple order; same manifest identity every call
    for index, (kwargs, _result) in enumerate(records):
        assert kwargs["raw_evidence_row"] is rows[index]
        assert kwargs["frozen_manifest_projection"] is manifest

    # final reconstruction is the exact final Slice-E carrier, unwrapped, with non-empty retained state
    assert final is records[-1][1]
    assert len(final.next_lifecycle_snapshot.slots_by_identity) == 1
    assert len(final.next_seen_target_pairs.seen_target_pairs) == 1
    assert expected_key in final.next_lifecycle_snapshot.slots_by_identity
    assert expected_key in final.next_seen_target_pairs.seen_target_pairs


def test_stateful_cross_execution_distinct_but_equal_nonempty(tmp_path):
    manifest = _verified_manifest_targeting_first_genuine_row()
    expected_key = _expected_genuine_key()
    result_a = reconstruct_shadow_intent_state(
        ordered_replay_rows=_genuine_two_score_rows(tmp_path, name="exec_a.db"),
        verified_manifest_artifact=manifest)
    result_b = reconstruct_shadow_intent_state(
        ordered_replay_rows=_genuine_two_score_rows(tmp_path, name="exec_b.db"),
        verified_manifest_artifact=manifest)
    # both alive simultaneously
    assert result_a is not result_b
    assert result_a.next_lifecycle_snapshot is not result_b.next_lifecycle_snapshot
    assert result_a.next_seen_target_pairs is not result_b.next_seen_target_pairs
    assert result_a == result_b
    for result in (result_a, result_b):
        assert len(result.next_lifecycle_snapshot.slots_by_identity) == 1
        assert expected_key in result.next_lifecycle_snapshot.slots_by_identity
        assert expected_key in result.next_seen_target_pairs.seen_target_pairs


# === 7. RESULT, FAILURE, AND EXCEPTION SURFACES ==================================================

def test_failing_row_propagates_same_exception_and_stops_fold(monkeypatch):
    failing_row = _negative_row()
    trailing_row = _negative_row()
    manifest = _verified_manifest_targeting_baseline()
    visited = []
    captured = {}

    def _spy(**kwargs):
        visited.append(kwargs["raw_evidence_row"])
        try:
            return execute_atomic_replay_step(**kwargs)
        except AtomicReplayStepError as error:
            captured["error"] = error
            raise

    monkeypatch.setattr(recon, "execute_atomic_replay_step", _spy)
    with pytest.raises(AtomicReplayStepError) as exc:
        reconstruct_shadow_intent_state(
            ordered_replay_rows=(failing_row, trailing_row), verified_manifest_artifact=manifest)

    assert exc.value is captured["error"]                 # same exception object, unchanged
    assert exc.value.reason == STEP_EVIDENCE_PROJECTION_REJECTED
    assert visited == [failing_row]                       # first failing row only; trailing never visited


def test_failing_row_returns_no_partial_result(monkeypatch):
    manifest = _verified_manifest_targeting_baseline()

    monkeypatch.setattr(recon, "execute_atomic_replay_step", execute_atomic_replay_step)
    with pytest.raises(AtomicReplayStepError):
        reconstruct_shadow_intent_state(
            ordered_replay_rows=(_negative_row(),), verified_manifest_artifact=manifest)


def test_runtime_has_no_try_except_finally_or_with():
    tree = _runtime_ast()
    for node in ast.walk(tree):
        assert not isinstance(node, (ast.Try, ast.ExceptHandler, ast.With, ast.AsyncWith))
    assert "suppress" not in _runtime_text()


# === 8. DETERMINISM AND IDENTITY (CPython-safe, no id()) =========================================

def test_cross_execution_results_distinct_but_content_equal(tmp_path):
    rows = _genuine_replay_rows(tmp_path)
    manifest = _verified_manifest()
    result_1 = reconstruct_shadow_intent_state(ordered_replay_rows=rows, verified_manifest_artifact=manifest)
    result_2 = reconstruct_shadow_intent_state(ordered_replay_rows=rows, verified_manifest_artifact=manifest)
    # both alive simultaneously
    assert result_1 is not result_2
    assert result_1.next_lifecycle_snapshot is not result_2.next_lifecycle_snapshot
    assert result_1.next_seen_target_pairs is not result_2.next_seen_target_pairs
    assert result_1 == result_2


def test_no_id_usage_in_this_suite():
    text = pathlib.Path(__file__).resolve().read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "id"


# === 9. MEMORY MODEL — STRUCTURAL PROOF ONLY =====================================================

def test_runtime_single_public_function_only():
    tree = _runtime_ast()
    funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert funcs == ["reconstruct_shadow_intent_state"]


def test_runtime_has_no_comprehensions():
    tree = _runtime_ast()
    for node in ast.walk(tree):
        assert not isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))


def test_runtime_has_no_growing_mutation_calls():
    banned = {"append", "extend", "add", "update", "setdefault", "insert", "appendleft", "extendleft"}
    tree = _runtime_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in banned


def test_runtime_has_no_subscript_assignment_or_augassign():
    tree = _runtime_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                assert not isinstance(target, ast.Subscript)
        assert not isinstance(node, ast.AugAssign)


def test_runtime_has_no_memory_or_id_probes():
    text = _runtime_text()
    for banned in ("id(", "tracemalloc", "getsizeof", "gc.", "resource."):
        assert banned not in text
    tree = _runtime_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "id"


def test_runtime_uses_no_growing_collection_literals():
    # the only working state is loop var + two snapshot refs + latest result ref: no list/set/dict literals
    tree = _runtime_ast()
    for node in ast.walk(tree):
        assert not isinstance(node, (ast.List, ast.Set, ast.Dict))


def test_runtime_has_no_builtin_rematerialization():
    # no tuple(...)/list(...)/dict(...)/set(...) rematerialization of the input or any working state
    banned = {"tuple", "list", "dict", "set"}
    tree = _runtime_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned, node.func.id


def test_runtime_has_no_module_or_global_state():
    tree = _runtime_ast()
    # no module-level mutable binding / accumulator / cache / singleton / registry
    for node in tree.body:
        assert not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
    # no global/nonlocal escape anywhere
    for node in ast.walk(tree):
        assert not isinstance(node, (ast.Global, ast.Nonlocal))


def test_runtime_raw_evidence_row_is_strictly_whitelisted():
    tree = _runtime_ast()
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}

    # the for-loop target is exactly the local raw_evidence_row iterating directly over the input tuple
    for_loops = [n for n in ast.walk(tree) if isinstance(n, ast.For)]
    assert len(for_loops) == 1
    loop = for_loops[0]
    assert isinstance(loop.target, ast.Name) and loop.target.id == "raw_evidence_row"
    assert isinstance(loop.target.ctx, ast.Store)
    assert isinstance(loop.iter, ast.Name) and loop.iter.id == "ordered_replay_rows"
    assert isinstance(loop.iter.ctx, ast.Load)

    # exactly one Load use of raw_evidence_row, and it is the value of the keyword argument
    # raw_evidence_row in the single execute_atomic_replay_step(...) call — nothing else
    loads = [n for n in ast.walk(tree)
             if isinstance(n, ast.Name) and n.id == "raw_evidence_row" and isinstance(n.ctx, ast.Load)]
    assert len(loads) == 1
    load = loads[0]
    keyword = parents[load]
    assert isinstance(keyword, ast.keyword) and keyword.arg == "raw_evidence_row"
    call = parents[keyword]
    assert isinstance(call, ast.Call)
    assert isinstance(call.func, ast.Name) and call.func.id == "execute_atomic_replay_step"
    # the load IS the keyword value (not buried inside attribute/subscript/call/compare/collection)
    assert keyword.value is load


# === 10. EXACT DEPENDENCY AND PURITY BOUNDARY ====================================================

def test_runtime_imports_exactly_two_allowed_modules():
    tree = _runtime_ast()
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module)
    # exact equality: no missing and no additional runtime dependency may pass
    assert modules == {
        "phase6_2_shadow_intent.atomic_replay_step",
        "phase6_2_shadow_intent.logical_model",
    }


def test_runtime_forbidden_tokens_absent():
    text = _runtime_text()
    for banned in (
        "sqlite3", "pytest", "unittest", "mock", "monkeypatch",
        "artifact_verifier", "s1_evidence_projection", "classification_predicates",
        "phase6_1", "phase6_1_s1_storage", "tests.", "fixtures",
        "threading", "asyncio", "multiprocessing", "socket", "requests", "urllib",
        "datetime", "time.", "random", "lru_cache", "open(",
    ):
        assert banned not in text, banned


def test_runtime_no_slice_e_reimplementation_tokens():
    text = _runtime_text()
    for banned in (
        "project_", "_slot_value", "_revalidate", "definitions_by_silver_pair",
        "make_opaque_silver_pair_key", "sorted(", "reversed(", "filter(",
        ".keys(", ".values(", ".items(", "verify_artifact",
    ):
        assert banned not in text, banned


# === 11. POSITIVE EXISTENCE (absence lock retired) ===============================================

def test_runtime_exposes_exactly_the_pinned_public_callable():
    assert hasattr(recon, "reconstruct_shadow_intent_state")
    callables = [n for n in vars(recon)
                 if callable(getattr(recon, n))
                 and getattr(getattr(recon, n), "__module__", None) == recon.__name__]
    assert callables == ["reconstruct_shadow_intent_state"]
