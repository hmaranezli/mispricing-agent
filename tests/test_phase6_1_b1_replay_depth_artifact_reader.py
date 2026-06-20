"""tests/test_phase6_1_b1_replay_depth_artifact_reader.py — Phase 6.1 replay depth-artifact reader.

Pins the single allowlisted IO module in the phase6_1 package. The reader opens ONE caller-supplied
local replay depth artifact (read-only) and builds exactly one PublicDepthSourceRecord through the B1
depth factory. It performs no network/env access, no path discovery/globbing, and no writes. It decides
nothing: values are carried verbatim into the B1 factory, which enforces the field contract.

Forbidden tokens / identifiers appearing in THIS file are explicit test fixtures; the reader runtime
must keep its closed, module-scoped surface (read-only `open`; imports ⊆ {pathlib, json, csv} plus the
required internal B1 import; no numeric parsing of observed_size; no carrier/Phase 5 construction).
"""
import ast
import inspect
import json
import pathlib

import pytest

import phase6_1
from phase6_1.b1_depth_source_contract import (
    PublicDepthSourceRecord,
    B1DepthSourceTypeError,
    B1DepthSourceValueError,
)
from phase6_1.b1_replay_depth_artifact_reader import (
    read_replay_depth_artifact,
    ReplayDepthArtifactError,
)


_READER_BASENAME = "b1_replay_depth_artifact_reader.py"

_VALID_ARTIFACT = {
    "observed_size": "125.5",
    "size_unit": "contracts",
    "depth_source_field": "levels.0.size",
    "depth_source_artifact": "replay-depth-fixture-0001 (read-only public depth reference)",
    "depth_source_contract": "external_market_replay_depth_provenance_contract.md",
    "depth_snapshot_identity": "replay-depth-0001",
    "depth_observed_at_epoch_ms": "1749990000000",
    "depth_retrieval_epoch_ms": 1_750_000_000_000,
}


def _write_artifact(tmp_path, payload, name="artifact.json"):
    p = tmp_path / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return str(p)


def _reader_path():
    return pathlib.Path(phase6_1.__file__).resolve().parent / _READER_BASENAME


def _reader_tree():
    with open(_reader_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _reader_text():
    with open(_reader_path(), "r", encoding="utf-8") as fh:
        return fh.read()


# --- happy path: build a PublicDepthSourceRecord from a local artifact ----------------------------

def test_reads_valid_artifact_into_public_depth_source_record(tmp_path):
    path = _write_artifact(tmp_path, _VALID_ARTIFACT)
    record = read_replay_depth_artifact(path)
    assert type(record) is PublicDepthSourceRecord
    assert record.observed_size == "125.5"
    assert record.size_unit == "contracts"
    assert record.depth_source_field == "levels.0.size"
    assert record.depth_source_contract == "external_market_replay_depth_provenance_contract.md"
    assert record.depth_snapshot_identity == "replay-depth-0001"
    assert record.depth_observed_at_epoch_ms == "1749990000000"
    assert record.depth_retrieval_epoch_ms == 1_750_000_000_000


# --- exact-string preservation / no numeric coercion of observed_size -----------------------------

def test_observed_size_decimal_string_carried_verbatim(tmp_path):
    payload = dict(_VALID_ARTIFACT, observed_size="100.00")
    record = read_replay_depth_artifact(_write_artifact(tmp_path, payload))
    assert record.observed_size == "100.00"
    assert type(record.observed_size) is str


def test_observed_size_non_numeric_string_carried_verbatim(tmp_path):
    payload = dict(_VALID_ARTIFACT, observed_size="not-a-number")
    record = read_replay_depth_artifact(_write_artifact(tmp_path, payload))
    assert record.observed_size == "not-a-number"
    assert type(record.observed_size) is str


def test_numeric_observed_size_rejected_must_already_be_string(tmp_path):
    # A JSON number decodes to int/float; the B1 factory requires an exact str → fail fast.
    payload = dict(_VALID_ARTIFACT, observed_size=125)
    with pytest.raises(B1DepthSourceTypeError):
        read_replay_depth_artifact(_write_artifact(tmp_path, payload))


# --- strict 8-field contract ----------------------------------------------------------------------

@pytest.mark.parametrize("field", sorted(_VALID_ARTIFACT))
def test_missing_field_fails_fast(tmp_path, field):
    payload = dict(_VALID_ARTIFACT)
    del payload[field]
    with pytest.raises(ReplayDepthArtifactError):
        read_replay_depth_artifact(_write_artifact(tmp_path, payload))


def test_unknown_extra_field_fails_fast(tmp_path):
    payload = dict(_VALID_ARTIFACT, depth_extra_hint="something")
    with pytest.raises(ReplayDepthArtifactError):
        read_replay_depth_artifact(_write_artifact(tmp_path, payload))


def test_non_mapping_artifact_fails_fast(tmp_path):
    p = tmp_path / "list.json"
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ReplayDepthArtifactError):
        read_replay_depth_artifact(str(p))


def test_empty_field_fails_fast_via_factory(tmp_path):
    payload = dict(_VALID_ARTIFACT, observed_size="")
    with pytest.raises(B1DepthSourceValueError):
        read_replay_depth_artifact(_write_artifact(tmp_path, payload))


# --- time isolation / lookahead-bias lock (enforced by the factory) -------------------------------

def test_observed_time_not_substituted_from_retrieval(tmp_path):
    payload = dict(
        _VALID_ARTIFACT,
        depth_retrieval_epoch_ms=1_750_000_000_000,
        depth_observed_at_epoch_ms="1750000000000",
    )
    with pytest.raises(B1DepthSourceValueError):
        read_replay_depth_artifact(_write_artifact(tmp_path, payload))


def test_distinct_timestamps_accepted(tmp_path):
    payload = dict(
        _VALID_ARTIFACT,
        depth_retrieval_epoch_ms=1_750_000_000_000,
        depth_observed_at_epoch_ms="1749999999000",
    )
    record = read_replay_depth_artifact(_write_artifact(tmp_path, payload))
    assert record.depth_observed_at_epoch_ms == "1749999999000"
    assert record.depth_retrieval_epoch_ms == 1_750_000_000_000


# --- explicit local path only: no default, no discovery, no globbing ------------------------------

def test_requires_explicit_path_argument():
    params = inspect.signature(read_replay_depth_artifact).parameters.values()
    required = [p for p in params if p.default is inspect.Parameter.empty
                and p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                               inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    assert len(required) == 1
    with pytest.raises(TypeError):
        read_replay_depth_artifact()


def test_missing_file_fails_fast_no_fallback(tmp_path):
    with pytest.raises(OSError):
        read_replay_depth_artifact(str(tmp_path / "does-not-exist.json"))


def test_directory_path_fails_fast_no_discovery(tmp_path):
    # Pointing at a directory must fail (no globbing / no discovery), not scan its contents.
    with pytest.raises(OSError):
        read_replay_depth_artifact(str(tmp_path))


# --- module-scoped source/AST locks: the closed reader surface ------------------------------------

_ALLOWED_EXTERNAL_IMPORT_ROOTS = {"pathlib", "json", "csv"}
_FORBIDDEN_IMPORT_ROOTS = {
    "requests", "http", "socket", "websocket", "websockets", "urllib", "aiohttp", "subprocess",
    "sqlite3", "psycopg2", "ssl", "smtplib", "ftplib", "pickle", "shelve", "os", "sys", "io",
    "shutil", "tempfile",
}


def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_reader_imports_only_allowlisted_external_plus_internal_b1():
    roots = _import_roots(_reader_tree())
    external = roots - {"phase6_1"}
    assert external <= _ALLOWED_EXTERNAL_IMPORT_ROOTS, external
    assert external & _FORBIDDEN_IMPORT_ROOTS == set()


def test_reader_imports_no_b2_b3_phase5():
    mods = set()
    for node in ast.walk(_reader_tree()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    for m in mods:
        assert not m.startswith("phase5"), m
        assert not m.startswith("phase6_1.b2"), m
        assert not m.startswith("phase6_1.b3"), m


def test_reader_only_open_is_read_only():
    opens = [
        node for node in ast.walk(_reader_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"
    ]
    assert opens, "reader is expected to open the local artifact read-only"
    for node in opens:
        mode = None
        if len(node.args) >= 2:
            mode = node.args[1]
        for kw in node.keywords:
            if kw.arg == "mode":
                mode = kw.value
        if mode is None:
            continue  # default 'r'
        assert isinstance(mode, ast.Constant) and isinstance(mode.value, str), ast.dump(node)
        assert not any(c in mode.value for c in ("w", "a", "x", "+")), mode.value


def test_reader_has_no_dynamic_exec_or_other_io_calls():
    forbidden = {"eval", "exec", "compile", "__import__", "input"}
    for node in ast.walk(_reader_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden, node.func.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"environ", "getenv", "popen", "system"}


def test_reader_does_no_numeric_parsing():
    forbidden = {"Decimal", "float", "int", "complex"}
    for node in ast.walk(_reader_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden, node.func.id
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] != "decimal"
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] != "decimal"


def test_reader_uses_no_isinstance():
    for node in ast.walk(_reader_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance"


def test_reader_constructs_only_public_depth_source_record():
    referenced = set()
    for node in ast.walk(_reader_tree()):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                referenced.add(alias.name)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
    assert "make_public_depth_source_record" in referenced
    forbidden_carriers = {
        "NormalizedEvidenceMaterial", "NormalizedEvidenceFieldBinding", "PublicRawSnapshotRecord",
        "PassiveShadowInput", "ShadowObservation", "NetEdgeCalculationResult",
        "make_passive_shadow_input", "make_shadow_observation",
    }
    assert forbidden_carriers & referenced == set()


def test_reader_has_no_edge_direction():
    assert "edge_direction" not in _reader_text()
