"""tests/test_phase6_1_s1_in_memory_observation_sink.py — Phase 6.1 S1 in-memory reference sink.

Pins the pure-Python, instance-bound, append-only S1 in-memory reference sink and its frozen passive
record DTOs (`ObservationScoreRecord`, `ObservationHaltRecord`), built under
`docs/handoff/phase6_1_s1_runtime_sink_tdd_planning_charter.md` and the Slice-0B record-model charter,
with the exact-name name-lock exception authorized by
`docs/handoff/phase6_1_s1_score_record_name_lock_exception_charter.md`.

The sink admits only exact `ObservationScoreRecord` / `ObservationHaltRecord` records (each carrying an
exact `S2IdentityWiringCandidate` as identity evidence), appends them to an instance-bound list, and
exposes only an immutable `snapshot()` tuple copy. It scores nothing, ranks nothing, decides nothing,
normalises nothing, and mints no identity. Forbidden tokens/identifiers in THIS file are explicit test
fixtures; the runtime module stays pure-Python and identity-blind.
"""
import ast
import io

import pytest

import phase6_1
from phase6_1.option_b_event_stream_reader import (
    OptionBEventEnvelope,
    read_option_b_event_stream,
)
from phase6_1.s2_identity_wiring_candidate import (
    S2IdentityWiringCandidate,
    route_option_b_envelope_to_s2_identity_candidate,
)
from phase6_1.s1_in_memory_observation_sink import (
    ObservationScoreRecord,
    ObservationHaltRecord,
    S1InMemoryObservationSink,
    S1ObservationSinkTypeError,
)


_MODULE_BASENAME = "s1_in_memory_observation_sink.py"


def _module_path():
    import pathlib  # test-only path resolution; the sink runtime imports no pathlib
    return pathlib.Path(phase6_1.__file__).resolve().parent / _MODULE_BASENAME


def _module_tree():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _candidate(payload=None, locator="loc", position=0):
    return S2IdentityWiringCandidate(
        forwarded_payload_or_local_halt=(payload if payload is not None else {"a": 1}),
        artifact_locator=locator,
        physical_record_position=position,
    )


def _score_record(cand=None, payload=None):
    return ObservationScoreRecord(
        identity_evidence=(cand if cand is not None else _candidate()),
        observation_kind="SCORE",
        provenance_timestamp=1_750_000_000_000,
        opaque_cost_context=(),
        family_payload=(payload if payload is not None else {"diag": 1}),
    )


def _halt_record(cand=None, payload=None):
    return ObservationHaltRecord(
        identity_evidence=(cand if cand is not None else _candidate()),
        observation_kind="HALT",
        provenance_timestamp=1_750_000_000_000,
        opaque_cost_context=(),
        family_payload=(payload if payload is not None else {"halt": "x"}),
    )


# --- append-only: records retained in sequence, both families equal-peer -------------------------

def test_appends_score_and_halt_in_sequence():
    sink = S1InMemoryObservationSink()
    s = _score_record()
    h = _halt_record()
    sink.record_observation(s)
    sink.record_observation(h)
    snap = sink.snapshot()
    assert snap == (s, h)
    assert snap[0] is s
    assert snap[1] is h


def test_empty_sink_snapshot_is_empty_tuple():
    sink = S1InMemoryObservationSink()
    assert sink.snapshot() == ()
    assert type(sink.snapshot()) is tuple


# --- snapshot anti-leak seal ----------------------------------------------------------------------

def test_snapshot_is_an_immutable_tuple_copy():
    sink = S1InMemoryObservationSink()
    sink.record_observation(_score_record())
    snap = sink.snapshot()
    assert type(snap) is tuple
    with pytest.raises(TypeError):
        snap[0] = "tamper"  # tuples are immutable


def test_prior_snapshot_unchanged_after_later_append():
    sink = S1InMemoryObservationSink()
    sink.record_observation(_score_record())
    snap1 = sink.snapshot()
    assert len(snap1) == 1
    sink.record_observation(_halt_record())
    # the earlier snapshot must NOT have grown — it was a detached copy
    assert len(snap1) == 1
    assert len(sink.snapshot()) == 2


def test_snapshot_does_not_expose_internal_list_by_reference():
    sink = S1InMemoryObservationSink()
    sink.record_observation(_score_record())
    a = sink.snapshot()
    b = sink.snapshot()
    # distinct tuple objects, and never the internal mutable container
    assert a is not sink.__dict__.get("_records")
    assert type(a) is tuple and type(b) is tuple


# --- exact-type gatekeeper ------------------------------------------------------------------------

def test_rejects_non_record_inputs():
    sink = S1InMemoryObservationSink()
    bad_inputs = [
        {"identity_evidence": _candidate()},      # raw dict
        [1, 2, 3],                                # list
        object(),                                 # unknown
        "record",                                 # str
        42,                                       # int
        None,                                     # none
        _candidate(),                             # identity-only object (not a record)
    ]
    for bad in bad_inputs:
        with pytest.raises(S1ObservationSinkTypeError):
            sink.record_observation(bad)
    assert sink.snapshot() == ()  # nothing was recorded


def test_rejects_record_subclasses():
    class _SubScore(ObservationScoreRecord):
        pass

    sub = _SubScore(
        identity_evidence=_candidate(),
        observation_kind="SCORE",
        provenance_timestamp=1,
        opaque_cost_context=(),
        family_payload={},
    )
    sink = S1InMemoryObservationSink()
    with pytest.raises(S1ObservationSinkTypeError):
        sink.record_observation(sub)


def test_rejects_record_with_non_candidate_identity_evidence():
    # identity must be the ratified S2IdentityWiringCandidate, not an arbitrary stand-in
    bad = ObservationScoreRecord(
        identity_evidence={"artifact_locator": "x", "physical_record_position": 0},
        observation_kind="SCORE",
        provenance_timestamp=1,
        opaque_cost_context=(),
        family_payload={},
    )
    sink = S1InMemoryObservationSink()
    with pytest.raises(S1ObservationSinkTypeError):
        sink.record_observation(bad)


def test_gatekeeper_error_is_a_typeerror():
    assert issubclass(S1ObservationSinkTypeError, TypeError)


# --- identity consumption: evidence carried by identity, never minted -----------------------------

def test_identity_evidence_carried_through_by_identity():
    cand = _candidate(locator=object(), position=7)
    rec = _score_record(cand=cand)
    sink = S1InMemoryObservationSink()
    sink.record_observation(rec)
    stored = sink.snapshot()[0]
    assert stored.identity_evidence is cand
    assert stored.identity_evidence.artifact_locator is cand.artifact_locator
    assert stored.identity_evidence.physical_record_position == 7


def test_provenance_timestamp_is_carried_not_used_as_identity():
    rec = _halt_record()
    sink = S1InMemoryObservationSink()
    sink.record_observation(rec)
    stored = sink.snapshot()[0]
    assert stored.provenance_timestamp == 1_750_000_000_000  # timestamp only, carried verbatim


def test_integration_with_real_s2_identity_wiring_candidate():
    text = '{"a": 1}\nnot-json\n'
    locator = object()
    sink = S1InMemoryObservationSink()
    for env in read_option_b_event_stream(text_stream=io.StringIO(text), artifact_locator=locator):
        cand = route_option_b_envelope_to_s2_identity_candidate(envelope=env)
        sink.record_observation(_score_record(cand=cand))
    snap = sink.snapshot()
    assert len(snap) == 2
    assert all(type(r.identity_evidence) is S2IdentityWiringCandidate for r in snap)
    assert [r.identity_evidence.physical_record_position for r in snap] == [0, len('{"a": 1}\n')]


# --- DTOs are frozen passive carriers -------------------------------------------------------------

def test_dtos_are_frozen():
    s = _score_record()
    h = _halt_record()
    with pytest.raises(Exception):
        s.observation_kind = "tamper"
    with pytest.raises(Exception):
        h.identity_evidence = None


def test_dtos_carry_exactly_the_five_envelope_fields():
    s = _score_record()
    for field in ("identity_evidence", "observation_kind", "provenance_timestamp",
                  "opaque_cost_context", "family_payload"):
        assert hasattr(s, field)


# --- anti-mutation interface ----------------------------------------------------------------------

def test_sink_exposes_no_mutation_interface():
    sink = S1InMemoryObservationSink()
    for forbidden in ("pop", "remove", "update", "delete", "clear", "insert", "extend",
                      "overwrite", "upsert", "__setitem__", "__delitem__"):
        assert not hasattr(sink, forbidden), forbidden


# --- anti-singleton: instance-bound state, no cross-instance leakage ------------------------------

def test_two_sinks_are_independent():
    a = S1InMemoryObservationSink()
    b = S1InMemoryObservationSink()
    a.record_observation(_score_record())
    assert len(a.snapshot()) == 1
    assert b.snapshot() == ()  # b shares no state with a


def test_fresh_sink_starts_empty():
    assert S1InMemoryObservationSink().snapshot() == ()


# --- AST / source pure-Python, DB/IO/minting bans -------------------------------------------------

def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_module_imports_no_db_io_clock_random_or_minting_modules():
    roots = _import_roots(_module_tree())
    for forbidden in {"sqlite3", "pandas", "numpy", "io", "os", "pathlib", "sys", "json", "csv",
                      "tempfile", "pickle", "shelve", "hashlib", "uuid", "random", "secrets",
                      "time", "datetime", "calendar"}:
        assert forbidden not in roots, forbidden


def test_module_only_imports_dataclasses_and_s2_candidate():
    roots = _import_roots(_module_tree())
    external = roots - {"phase6_1"}
    assert external <= {"dataclasses"}, external
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("phase6_1"):
            assert node.module == "phase6_1.s2_identity_wiring_candidate", node.module


def test_module_has_no_filesystem_db_or_dynamic_exec_calls():
    forbidden_calls = {"open", "eval", "exec", "compile", "__import__", "input"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden_calls, node.func.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"connect", "cursor", "execute", "environ", "getenv",
                                     "popen", "system", "dumps", "loads"}, node.attr


def test_module_has_no_identity_minting():
    forbidden_attrs = {"uuid4", "uuid1", "sha256", "md5", "sha1", "hexdigest", "token_hex",
                       "token_bytes", "getrandbits"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attrs, node.attr
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"hash", "id"}, node.func.id


def test_module_uses_no_isinstance():
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance"


def test_dtos_have_no_methods_beyond_dataclass_mechanics():
    tree = _module_tree()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name in {"ObservationScoreRecord",
                                                            "ObservationHaltRecord"}:
            for child in node.body:
                assert not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)), \
                    "DTO {} must define no methods".format(node.name)


def test_dtos_are_frozen_dataclasses():
    import dataclasses
    assert dataclasses.is_dataclass(ObservationScoreRecord)
    assert dataclasses.is_dataclass(ObservationHaltRecord)
    assert ObservationScoreRecord.__dataclass_params__.frozen is True
    assert ObservationHaltRecord.__dataclass_params__.frozen is True


def test_no_module_level_mutable_store():
    # the only state lives on instances (self._records); no module-level list/dict/set assignment
    tree = _module_tree()
    for node in tree.body:  # module top-level statements only
        if isinstance(node, ast.Assign):
            assert not isinstance(node.value, (ast.List, ast.Dict, ast.Set)), \
                "no module-level mutable store"
