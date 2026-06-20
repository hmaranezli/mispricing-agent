"""tests/test_phase6_1_b1_depth_source_contract.py — Phase 6.1 B1 replay depth source contract slice.

Pins ONLY an immutable, provenance-tagged depth-evidence carrier and its keyword-only, exact-type,
fail-fast factory. Replay-artifact-only: no fetch, no IO, no network, no decision. ``observed_size`` is
carried verbatim as evidence and never parsed or compared.

Forbidden tokens / Phase 5 identifiers appearing in THIS file are explicit test fixtures; the runtime
must contain none of them.
"""
import ast
import inspect
import pathlib

import pytest

import phase6_1
from phase6_1.b1_depth_source_contract import (
    PublicDepthSourceRecord,
    make_public_depth_source_record,
    B1DepthSourceTypeError,
    B1DepthSourceValueError,
    B1DepthSourceTruthinessError,
    B1DepthSourceCoercionError,
)


_B1_DEPTH_BASENAME = "b1_depth_source_contract.py"


# --- deterministic builder ------------------------------------------------------------------------

def _depth(**overrides):
    kwargs = dict(
        observed_size="125.5",
        size_unit="contracts",
        depth_source_field="levels.0.size",
        depth_source_artifact="replay-depth-fixture-0001 (read-only public depth reference)",
        depth_source_contract="external_market_replay_depth_provenance_contract.md",
        depth_observed_at_epoch_ms="1749990000000",
        depth_retrieval_epoch_ms=1_750_000_000_000,
        depth_snapshot_identity="replay-depth-0001",
    )
    kwargs.update(overrides)
    return make_public_depth_source_record(**kwargs)


def _runtime_path():
    return pathlib.Path(phase6_1.__file__).resolve().parent / _B1_DEPTH_BASENAME


def _tree():
    with open(_runtime_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


_STR_FIELDS = [
    "observed_size", "size_unit", "depth_source_field", "depth_source_artifact",
    "depth_source_contract", "depth_snapshot_identity",
]


# --- construction / immutability ------------------------------------------------------------------

def test_depth_record_accepts_valid_and_reads_fields():
    d = _depth()
    assert d.observed_size == "125.5"
    assert d.size_unit == "contracts"
    assert d.depth_source_field == "levels.0.size"
    assert d.depth_source_artifact.startswith("replay-depth-fixture")
    assert d.depth_source_contract == "external_market_replay_depth_provenance_contract.md"
    assert d.depth_observed_at_epoch_ms == "1749990000000"
    assert d.depth_retrieval_epoch_ms == 1_750_000_000_000
    assert d.depth_snapshot_identity == "replay-depth-0001"


def test_depth_record_is_frozen_slotted():
    d = _depth()
    assert not hasattr(d, "__dict__")
    with pytest.raises(Exception):
        d.observed_size = "999"
    with pytest.raises(AttributeError):
        object.__setattr__(d, "injected", 1)


def test_depth_record_direct_construction_blocked():
    with pytest.raises(B1DepthSourceTypeError):
        PublicDepthSourceRecord()


def test_depth_record_anti_coercion_dunders_raise():
    d = _depth()
    with pytest.raises(B1DepthSourceTruthinessError):
        bool(d)
    with pytest.raises(B1DepthSourceTruthinessError):
        len(d)
    for fn in (int, float, complex):
        with pytest.raises(B1DepthSourceCoercionError):
            fn(d)
    with pytest.raises(B1DepthSourceCoercionError):
        str(d)
    with pytest.raises(B1DepthSourceCoercionError):
        bytes(d)


# --- string field guards --------------------------------------------------------------------------

@pytest.mark.parametrize("field", _STR_FIELDS)
@pytest.mark.parametrize("bad", [123, None, True, 1.0, {"a": 1}, ["x"]])
def test_depth_record_rejects_non_str(field, bad):
    with pytest.raises(B1DepthSourceTypeError):
        _depth(**{field: bad})


@pytest.mark.parametrize("field", _STR_FIELDS)
def test_depth_record_rejects_str_subclass(field):
    class _S(str):
        pass

    with pytest.raises(B1DepthSourceTypeError):
        _depth(**{field: _S("x")})


@pytest.mark.parametrize("field", _STR_FIELDS)
@pytest.mark.parametrize("bad", ["", "   "])
def test_depth_record_rejects_empty(field, bad):
    with pytest.raises(B1DepthSourceValueError):
        _depth(**{field: bad})


# --- retrieval epoch (exact non-negative int) -----------------------------------------------------

@pytest.mark.parametrize("bad", [True, False])
def test_depth_retrieval_rejects_bool(bad):
    with pytest.raises(B1DepthSourceTypeError):
        _depth(depth_retrieval_epoch_ms=bad)


@pytest.mark.parametrize("bad", [1.0, "1750000000000", None])
def test_depth_retrieval_rejects_non_int(bad):
    with pytest.raises(B1DepthSourceTypeError):
        _depth(depth_retrieval_epoch_ms=bad)


def test_depth_retrieval_rejects_negative():
    with pytest.raises(B1DepthSourceValueError):
        _depth(depth_retrieval_epoch_ms=-1)


def test_depth_retrieval_accepts_zero():
    d = _depth(depth_retrieval_epoch_ms=0, depth_observed_at_epoch_ms="1")
    assert d.depth_retrieval_epoch_ms == 0


# --- observed epoch (canonical unsigned integer string) -------------------------------------------

@pytest.mark.parametrize("bad", [1749990000000, 1.0, True, None, {"t": 1}, ["1"]])
def test_depth_observed_rejects_non_str(bad):
    with pytest.raises(B1DepthSourceTypeError):
        _depth(depth_observed_at_epoch_ms=bad)


@pytest.mark.parametrize("bad", ["", "   ", "-1", "1.0", "1_000", "12a", "0x1f", "007", " 12", "12 "])
def test_depth_observed_rejects_non_canonical(bad):
    with pytest.raises(B1DepthSourceValueError):
        _depth(depth_observed_at_epoch_ms=bad)


def test_depth_observed_accepts_canonical():
    d = _depth(depth_observed_at_epoch_ms="0", depth_retrieval_epoch_ms=5)
    assert d.depth_observed_at_epoch_ms == "0"


# --- time isolation / lookahead-bias lock ---------------------------------------------------------

def test_depth_observed_must_not_equal_str_of_retrieval():
    with pytest.raises(B1DepthSourceValueError):
        _depth(depth_retrieval_epoch_ms=1_750_000_000_000, depth_observed_at_epoch_ms="1750000000000")


def test_depth_observed_distinct_from_retrieval_accepted():
    d = _depth(depth_retrieval_epoch_ms=1_750_000_000_000, depth_observed_at_epoch_ms="1749999999000")
    assert d.depth_retrieval_epoch_ms == 1_750_000_000_000
    assert d.depth_observed_at_epoch_ms == "1749999999000"


# --- no defaults / no loose kwargs ----------------------------------------------------------------

def test_missing_required_fields_fail_fast():
    with pytest.raises(TypeError):
        make_public_depth_source_record(observed_size="1")  # missing the rest


def test_factory_accepts_no_var_keyword():
    params = inspect.signature(make_public_depth_source_record).parameters.values()
    assert all(p.kind is not inspect.Parameter.VAR_KEYWORD for p in params)
    assert all(p.kind is not inspect.Parameter.VAR_POSITIONAL for p in params)


# --- observed_size is evidence carried verbatim (no numeric decision) ------------------------------

def test_observed_size_carried_verbatim_even_if_non_numeric():
    d = _depth(observed_size="not-a-number")
    assert d.observed_size == "not-a-number"
    assert type(d.observed_size) is str


def test_runtime_does_no_numeric_parsing_of_observed_size():
    forbidden = {"Decimal", "float", "int", "complex"}
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden, node.func.id
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] != "decimal"
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] != "decimal"


# --- replay-only: no network / IO / env / dynamic exec --------------------------------------------

_FORBIDDEN_IMPORT_ROOTS = {
    "requests", "http", "socket", "websocket", "websockets", "urllib", "aiohttp", "subprocess",
    "sqlite3", "psycopg2", "ssl", "smtplib", "ftplib", "pickle", "os", "sys", "pathlib", "shutil",
    "tempfile", "io",
}
_FORBIDDEN_CALL_NAMES = {"open", "eval", "exec", "compile", "__import__", "input"}


def test_runtime_no_network_io_env_exec():
    tree = _tree()
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots & _FORBIDDEN_IMPORT_ROOTS == set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in _FORBIDDEN_CALL_NAMES
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"environ", "getenv", "popen", "system"}


def test_runtime_uses_no_isinstance():
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance"


# --- isolation from B2 / B3 / Phase 5 / Slice 0 carriers ------------------------------------------

def test_runtime_imports_no_b2_b3_phase5():
    mods = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    for m in mods:
        assert not m.startswith("phase5"), m
        assert not m.startswith("phase6_1.b2"), m
        assert not m.startswith("phase6_1.b3"), m
        assert "passive_shadow_input" not in m, m
        assert "shadow_observation" not in m, m
        assert "provenance_chain" not in m, m


_FORBIDDEN_CARRIER_NAMES = {
    "PassiveShadowInput", "ShadowObservation", "NetEdgeCalculationResult",
    "make_passive_shadow_input", "make_shadow_observation", "verify_provenance_chain",
}


def test_runtime_references_no_slice0_carriers():
    referenced = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                referenced.add(alias.name)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
    assert _FORBIDDEN_CARRIER_NAMES & referenced == set()


def test_runtime_has_no_edge_direction():
    with open(_runtime_path(), "r", encoding="utf-8") as fh:
        text = fh.read()
    assert "edge_direction" not in text
