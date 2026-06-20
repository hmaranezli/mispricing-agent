"""tests/test_phase6_1_b2_replay_normalization.py — Phase 6.1 B2 replay normalization slice.

Pins one deterministic, replay-artifact-only normalizer that consumes an exact PublicRawSnapshotRecord
and returns NormalizedEvidenceMaterial built from the existing B2 contract carriers. Meaning comes only
from explicit labels and binding fields, never tuple position. No network, no file IO, no env, no Phase
5 import, no magnitude parsing/conversion/comparison.

Forbidden carrier names / Phase 5 identifiers appearing in THIS file are explicit test fixtures; the
runtime must contain none of them.
"""
import ast
import os
import pathlib

import pytest

import phase6_1
from phase6_1.b2_normalization_contract import (
    PublicRawSnapshotRecord,
    UnitBoundMagnitude,
    NormalizedEvidenceMaterial,
    make_public_raw_snapshot_record,
    B2NormalizationTypeError,
    B2NormalizationValueError,
)
from phase6_1.b2_replay_normalization import (
    normalize_replay_snapshot_to_evidence_material,
)


_B2_REPLAY_BASENAME = "b2_replay_normalization.py"


# --- deterministic replay builders ----------------------------------------------------------------

def _entry(
    normalized_field_name="gross_edge",
    source_field="summary.gross_edge",
    magnitude="0.006",
    unit="proportion",
):
    return (
        ("normalized_field_name", normalized_field_name),
        ("source_field", source_field),
        ("magnitude", magnitude),
        ("unit", unit),
    )


def _raw(field_payload=None, **overrides):
    payload = (_entry(),) if field_payload is None else field_payload
    kwargs = dict(
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="summary.eligible_pairs",
        venue="hyperliquid",
        pair="BTC-USD",
        retrieval_epoch_ms=1_750_000_000_000,
        raw_snapshot_identity="replay-fixture-0001",
        field_payload=payload,
    )
    kwargs.update(overrides)
    return make_public_raw_snapshot_record(**kwargs)


def _normalize(**overrides):
    kwargs = dict(raw_snapshot=_raw(), evidence_epoch_tolerance_ms=0)
    kwargs.update(overrides)
    return normalize_replay_snapshot_to_evidence_material(**kwargs)


def _runtime_path():
    return pathlib.Path(phase6_1.__file__).resolve().parent / _B2_REPLAY_BASENAME


def _tree():
    with open(_runtime_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _project(binding):
    return (
        binding.normalized_field_name,
        binding.source_field,
        binding.unit_bound_magnitude.magnitude,
        binding.unit_bound_magnitude.unit,
    )


# --- happy path -----------------------------------------------------------------------------------

def test_valid_payload_produces_material():
    material = _normalize()
    assert type(material) is NormalizedEvidenceMaterial
    assert len(material.normalized_field_bindings) == 1


def test_output_raw_snapshot_is_input_by_id():
    raw = _raw()
    material = normalize_replay_snapshot_to_evidence_material(
        raw_snapshot=raw, evidence_epoch_tolerance_ms=0
    )
    assert material.raw_snapshot is raw
    assert id(material.raw_snapshot) == id(raw)


def test_bindings_preserve_labels_exactly():
    material = _normalize()
    binding = material.normalized_field_bindings[0]
    assert binding.normalized_field_name == "gross_edge"
    assert binding.source_field == "summary.gross_edge"
    assert type(binding.unit_bound_magnitude) is UnitBoundMagnitude
    assert binding.unit_bound_magnitude.magnitude == "0.006"
    assert binding.unit_bound_magnitude.unit == "proportion"


# --- label-addressed, not positional --------------------------------------------------------------

def test_reversed_label_pairs_inside_entry_yield_same_binding():
    reversed_entry = (
        ("unit", "proportion"),
        ("magnitude", "0.006"),
        ("source_field", "summary.gross_edge"),
        ("normalized_field_name", "gross_edge"),
    )
    material = _normalize(raw_snapshot=_raw(field_payload=(reversed_entry,)))
    assert _project(material.normalized_field_bindings[0]) == (
        "gross_edge", "summary.gross_edge", "0.006", "proportion",
    )


def test_reversed_entry_sequence_infers_no_meaning_from_index():
    forward = (
        _entry(normalized_field_name="gross_edge", source_field="summary.gross_edge"),
        _entry(normalized_field_name="total_cost", source_field="summary.total_cost"),
    )
    material = _normalize(raw_snapshot=_raw(field_payload=tuple(reversed(forward))))
    by_name = {b.normalized_field_name: b for b in material.normalized_field_bindings}
    assert by_name["gross_edge"].source_field == "summary.gross_edge"
    assert by_name["total_cost"].source_field == "summary.total_cost"


# --- fail-fast on malformed payload ---------------------------------------------------------------

def test_empty_field_payload_fails_fast():
    with pytest.raises(B2NormalizationValueError):
        _normalize(raw_snapshot=_raw(field_payload=()))


def test_missing_required_label_fails_fast():
    entry = (
        ("normalized_field_name", "gross_edge"),
        ("source_field", "summary.gross_edge"),
        ("magnitude", "0.006"),
        # unit missing
    )
    with pytest.raises(B2NormalizationValueError):
        _normalize(raw_snapshot=_raw(field_payload=(entry,)))


def test_duplicate_label_inside_entry_fails_fast():
    entry = (
        ("normalized_field_name", "gross_edge"),
        ("source_field", "summary.gross_edge"),
        ("magnitude", "0.006"),
        ("magnitude", "0.007"),
        ("unit", "proportion"),
    )
    with pytest.raises(B2NormalizationValueError):
        _normalize(raw_snapshot=_raw(field_payload=(entry,)))


def test_unknown_label_fails_fast():
    entry = _entry() + (("weird_label", "x"),)
    with pytest.raises(B2NormalizationValueError):
        _normalize(raw_snapshot=_raw(field_payload=(entry,)))


def test_non_str_label_fails_fast():
    entry = ((123, "gross_edge"), ("source_field", "s"), ("magnitude", "0.006"), ("unit", "proportion"))
    with pytest.raises(B2NormalizationTypeError):
        _normalize(raw_snapshot=_raw(field_payload=(entry,)))


def test_non_str_value_fails_fast():
    entry = (
        ("normalized_field_name", "gross_edge"),
        ("source_field", "summary.gross_edge"),
        ("magnitude", 0.006),
        ("unit", "proportion"),
    )
    with pytest.raises(B2NormalizationTypeError):
        _normalize(raw_snapshot=_raw(field_payload=(entry,)))


@pytest.mark.parametrize("bad_pair", [("magnitude",), ("magnitude", "0.006", "extra")])
def test_non_two_item_pair_fails_fast(bad_pair):
    entry = (("normalized_field_name", "x"), ("source_field", "y"), ("unit", "u"), bad_pair)
    with pytest.raises(B2NormalizationTypeError):
        _normalize(raw_snapshot=_raw(field_payload=(entry,)))


# --- raw snapshot type discipline -----------------------------------------------------------------

@pytest.mark.parametrize("bad", [{"x": 1}, ["x"], None, "raw", 123])
def test_wrong_raw_snapshot_type_fails_fast(bad):
    with pytest.raises(B2NormalizationTypeError):
        normalize_replay_snapshot_to_evidence_material(
            raw_snapshot=bad, evidence_epoch_tolerance_ms=0
        )


def test_raw_snapshot_subclass_fails_fast():
    class _Sub(PublicRawSnapshotRecord):
        pass

    sub = object.__new__(_Sub)
    object.__setattr__(sub, "field_payload", (_entry(),))
    with pytest.raises(B2NormalizationTypeError):
        normalize_replay_snapshot_to_evidence_material(
            raw_snapshot=sub, evidence_epoch_tolerance_ms=0
        )


# --- tolerance contract + fail-fast ordering ------------------------------------------------------

def test_tolerance_zero_accepted():
    assert _normalize(evidence_epoch_tolerance_ms=0).evidence_epoch_tolerance_ms == 0


@pytest.mark.parametrize("bad", [None, True, 1.0, "0"])
def test_tolerance_wrong_type_rejected(bad):
    with pytest.raises(B2NormalizationTypeError):
        _normalize(evidence_epoch_tolerance_ms=bad)


def test_tolerance_negative_rejected():
    with pytest.raises(B2NormalizationValueError):
        _normalize(evidence_epoch_tolerance_ms=-1)


def test_tolerance_validated_before_payload_traversal():
    # field_payload that explodes if iterated; a malformed tolerance must raise FIRST.
    class _ExplodingPayload:
        def __iter__(self):
            raise AssertionError("field_payload must not be traversed before tolerance validation")

    raw = object.__new__(PublicRawSnapshotRecord)
    object.__setattr__(raw, "field_payload", _ExplodingPayload())
    with pytest.raises(B2NormalizationTypeError):
        normalize_replay_snapshot_to_evidence_material(
            raw_snapshot=raw, evidence_epoch_tolerance_ms=None
        )


# --- duplicate normalized_field_name across entries (through material contract) -------------------

def test_duplicate_normalized_field_name_across_entries_fails_fast():
    payload = (
        _entry(normalized_field_name="gross_edge"),
        _entry(normalized_field_name="gross_edge"),
    )
    with pytest.raises(B2NormalizationValueError):
        _normalize(raw_snapshot=_raw(field_payload=payload))


# --- no magnitude parsing / conversion / comparison -----------------------------------------------

def test_magnitude_kept_verbatim_without_numeric_parsing():
    # a non-numeric magnitude is carried as an exact str — proving no Decimal/float/int parsing
    material = _normalize(raw_snapshot=_raw(field_payload=(_entry(magnitude="not-a-number"),)))
    ubm = material.normalized_field_bindings[0].unit_bound_magnitude
    assert ubm.magnitude == "not-a-number"
    assert type(ubm.magnitude) is str


def test_runtime_does_no_numeric_parsing():
    forbidden = {"Decimal", "float", "int", "complex"}
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden, node.func.id
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] != "decimal"
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] != "decimal"


# --- determinism ----------------------------------------------------------------------------------

def test_deterministic_replay_reproducibility():
    raw = _raw(field_payload=(
        _entry(normalized_field_name="gross_edge", source_field="summary.gross_edge"),
        _entry(normalized_field_name="total_cost", source_field="summary.total_cost", magnitude="0.004"),
    ))
    first = tuple(_project(b) for b in normalize_replay_snapshot_to_evidence_material(
        raw_snapshot=raw, evidence_epoch_tolerance_ms=0).normalized_field_bindings)
    second = tuple(_project(b) for b in normalize_replay_snapshot_to_evidence_material(
        raw_snapshot=raw, evidence_epoch_tolerance_ms=0).normalized_field_bindings)
    assert first == second


# --- structural locks specific to this slice ------------------------------------------------------

def test_runtime_does_not_import_phase5():
    roots = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert "phase5" not in roots


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


def test_runtime_uses_no_isinstance():
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance"


_FORBIDDEN_IMPORT_ROOTS = {
    "requests", "http", "socket", "websocket", "urllib", "aiohttp", "subprocess",
    "sqlite3", "psycopg2", "ssl", "smtplib", "ftplib", "pickle", "os", "sys",
    "pathlib", "shutil", "tempfile", "io",
}
_FORBIDDEN_CALL_NAMES = {"open", "eval", "exec", "compile", "__import__", "input"}


def test_runtime_has_no_network_env_secret_io():
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


_BANNED_SURFACE_SUBSTRINGS = (
    "calculate", "compute", "derive", "score", "readiness",
    "actionability", "actionable", "recommendation", "verdict", "rank", "threshold",
)


def test_runtime_has_no_calculation_or_actionability_surface():
    for node in ast.walk(_tree()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            low = node.name.lower()
            assert not any(tok in low for tok in _BANNED_SURFACE_SUBSTRINGS), node.name
