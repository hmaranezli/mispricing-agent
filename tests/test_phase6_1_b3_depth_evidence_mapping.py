"""tests/test_phase6_1_b3_depth_evidence_mapping.py — Phase 6.1 B3 first runtime slice.

Pins the smallest possible B3 boundary: one pure identity/provenance pass-through function
``depth_evidence_reference_from_material(material)`` that returns the B2 material's
depth_source_reference exactly as-is (or None). No output carrier, no class, no construction, no IO,
no depth-subfield inspection. Authored under
`docs/handoff/phase6_1_b3_depth_evidence_mapping_tdd_slice_charter.md`.

Forbidden identifiers/tokens appearing in THIS file are explicit test fixtures; the B3 runtime must
contain none of the forbidden ones.
"""
import ast
import os
import pathlib
import re

import pytest

import phase6_1
from phase6_1.b1_depth_source_contract import (
    PublicDepthSourceRecord,
    make_public_depth_source_record,
)
from phase6_1.b2_normalization_contract import make_public_raw_snapshot_record
from phase6_1.b2_replay_normalization import normalize_replay_snapshot_to_evidence_material
from phase6_1.b3_depth_evidence_mapping import depth_evidence_reference_from_material


_B3_BASENAME = "b3_depth_evidence_mapping.py"


# --- deterministic builders -----------------------------------------------------------------------

def _raw():
    entry = (
        ("normalized_field_name", "gross_edge"),
        ("source_field", "summary.gross_edge"),
        ("binding_role", "GROSS_EDGE"),
        ("magnitude", "0.006"),
        ("unit", "proportion"),
    )
    return make_public_raw_snapshot_record(
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="summary.eligible_pairs",
        venue="hyperliquid",
        pair="BTC-USD",
        base_asset="BTC",
        quote_asset="USD",
        instrument_id="BTC-USD-PERP",
        venue_scope="SINGLE_VENUE",
        venue_buy="hyperliquid",
        venue_sell="hyperliquid",
        retrieval_epoch_ms=1_750_000_000_000,
        observed_at_epoch_ms="1749990000000",
        raw_snapshot_identity="replay-fixture-0001",
        field_payload=(entry,),
    )


def _depth_record():
    return make_public_depth_source_record(
        observed_size="125.5",
        size_unit="contracts",
        depth_source_field="levels.0.size",
        depth_source_artifact="replay-depth-fixture-0001 (read-only public depth reference)",
        depth_source_contract="external_market_replay_depth_provenance_contract.md",
        depth_observed_at_epoch_ms="1749990000000",
        depth_retrieval_epoch_ms=1_750_000_000_000,
        depth_snapshot_identity="replay-depth-0001",
    )


def _material_with_depth(record):
    return normalize_replay_snapshot_to_evidence_material(
        raw_snapshot=_raw(), evidence_epoch_tolerance_ms=0, depth_source_reference=record
    )


def _material_without_depth():
    return normalize_replay_snapshot_to_evidence_material(
        raw_snapshot=_raw(), evidence_epoch_tolerance_ms=0
    )


def _module_path():
    return pathlib.Path(phase6_1.__file__).resolve().parent / _B3_BASENAME


def _module_text():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return fh.read()


def _module_tree():
    return ast.parse(_module_text())


# --- identity pass-through ------------------------------------------------------------------------

def test_returns_exact_depth_reference_by_identity():
    record = _depth_record()
    material = _material_with_depth(record)
    result = depth_evidence_reference_from_material(material)
    assert result is record
    assert id(result) == id(record)


def test_returned_reference_is_exact_type_when_present():
    record = _depth_record()
    result = depth_evidence_reference_from_material(_material_with_depth(record))
    assert type(result) is PublicDepthSourceRecord


# --- None propagation, no fabrication -------------------------------------------------------------

def test_returns_none_when_depth_absent():
    result = depth_evidence_reference_from_material(_material_without_depth())
    assert result is None


# --- single public function, no class / output carrier --------------------------------------------

def test_module_defines_exactly_one_public_function_and_no_class():
    tree = _module_tree()
    funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    public = [n for n in funcs if not n.startswith("_")]
    assert public == ["depth_evidence_reference_from_material"]
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert classes == []


def test_module_defines_no_dataclass():
    assert "dataclass" not in _module_text()


# --- constructs nothing ---------------------------------------------------------------------------

_FORBIDDEN_CONSTRUCTION = {
    "PassiveShadowInput", "make_passive_shadow_input",
    "ShadowObservation", "make_shadow_observation",
    "NetEdgeCalculationResult", "_make_net_edge_result",
    "ShadowIntentEnvelope", "make_shadow_intent_envelope",
    "make_public_depth_source_record",
}


def test_module_constructs_no_carrier_and_no_depth_record():
    referenced = set()
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                referenced.add(alias.name)
    assert _FORBIDDEN_CONSTRUCTION & referenced == set()
    assert "make_public_depth_source_record" not in _module_text()


# --- imports nothing forbidden (no reader / Phase 5 / Shadow Intent / IO) --------------------------

def test_module_imports_no_reader_phase5_shadow_or_io():
    mods = set()
    roots = set()
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
            roots.add(node.module.split(".")[0])
    for m in mods:
        assert "replay_depth_artifact_reader" not in m, m
        assert not m.startswith("phase5"), m
        assert "shadow_intent" not in m, m
        assert not m.startswith("phase6_1.b3"), m
    assert roots & {
        "os", "sys", "io", "json", "csv", "pathlib", "requests", "urllib", "http", "socket",
        "aiohttp", "websocket", "subprocess",
    } == set()


# --- does not inspect depth subfields -------------------------------------------------------------

_DEPTH_SUBFIELDS = (
    "observed_size", "size_unit", "depth_source_field", "depth_source_artifact",
    "depth_source_contract", "depth_snapshot_identity", "depth_observed_at_epoch_ms",
    "depth_retrieval_epoch_ms",
)


def test_module_does_not_inspect_depth_subfields():
    text = _module_text()
    for name in _DEPTH_SUBFIELDS:
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])"
        assert re.search(pattern, text) is None, name


# --- no numeric / arithmetic / ordering surface; no IO calls --------------------------------------

def test_module_has_no_numeric_or_io_or_exec_surface():
    tree = _module_tree()
    numeric_calls = {"Decimal", "int", "float", "complex", "round", "sum", "min", "max", "abs"}
    io_exec_calls = {"open", "eval", "exec", "compile", "__import__", "input"}
    arith = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
    order = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in numeric_calls, node.func.id
            assert node.func.id not in io_exec_calls, node.func.id
            assert node.func.id != "isinstance"
        assert not isinstance(node, ast.BinOp) or not isinstance(node.op, arith)
        if isinstance(node, ast.Compare):
            assert not any(isinstance(op, order) for op in node.ops)
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"environ", "getenv", "popen", "system"}


# --- no capacity / actionability tokens -----------------------------------------------------------

_FORBIDDEN_SEMANTIC_TOKENS = (
    "capacity_pass_reference", "sizing", "allocation", "routing", "route", "execution", "execute",
    "order", "trade", "candidate", "signal", "score", "verdict", "threshold", "ranking", "rank",
)


def test_module_has_no_capacity_or_actionability_tokens():
    text = _module_text()
    for tok in _FORBIDDEN_SEMANTIC_TOKENS:
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(tok) + r"(?![A-Za-z0-9_])"
        assert re.search(pattern, text, re.IGNORECASE) is None, tok
