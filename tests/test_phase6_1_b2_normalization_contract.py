"""tests/test_phase6_1_b2_normalization_contract.py — Phase 6.1 B2 typed-contract slice.

Pins ONLY the narrow structural contract at the B1/B2 seam — three frozen/slotted/init-blocked
carriers and their keyword-only, exact-type, fail-fast factories:
  - PublicRawSnapshotRecord       (B1 -> B2 input)
  - UnitBoundMagnitude            (magnitude + unit atomically bound)
  - NormalizedEvidenceMaterial    (B2 output; references the raw snapshot by identity)

No normalization logic, no value mapping, no Phase 5 import, no carrier construction, no IO. Replay-
first: every input here is static and deterministic.

Forbidden carrier names / Phase 5 identifiers appearing in THIS file are explicit test fixtures; the
runtime must contain none of them.
"""
import ast
import inspect
import os
import pathlib

import pytest

import phase6_1
from phase6_1.b2_normalization_contract import (
    PublicRawSnapshotRecord,
    UnitBoundMagnitude,
    NormalizedEvidenceMaterial,
    make_public_raw_snapshot_record,
    make_unit_bound_magnitude,
    make_normalized_evidence_material,
    B2NormalizationTypeError,
    B2NormalizationValueError,
    B2NormalizationTruthinessError,
    B2NormalizationCoercionError,
)


_B2_MODULE_BASENAME = "b2_normalization_contract.py"


# --- deterministic builders -----------------------------------------------------------------------

def _raw(**overrides):
    kwargs = dict(
        source_artifact="phase4c_batch_1781637248 (read-only provenance reference)",
        source_field="summary.eligible_pairs",
        venue="hyperliquid",
        pair="BTC-USD",
        retrieval_epoch_ms=1_750_000_000_000,
        raw_snapshot_identity="replay-fixture-0001",
        field_payload=(("bid", "0.50"), ("ask", "0.60")),
    )
    kwargs.update(overrides)
    return make_public_raw_snapshot_record(**kwargs)


def _ubm(**overrides):
    kwargs = dict(magnitude="0.006", unit="proportion")
    kwargs.update(overrides)
    return make_unit_bound_magnitude(**kwargs)


def _material(**overrides):
    kwargs = dict(
        raw_snapshot=_raw(),
        normalized_values=(_ubm(),),
        evidence_epoch_tolerance_ms=0,
    )
    kwargs.update(overrides)
    return make_normalized_evidence_material(**kwargs)


def _runtime_b2_path():
    pkg_dir = pathlib.Path(phase6_1.__file__).resolve().parent
    return pkg_dir / _B2_MODULE_BASENAME


def _b2_tree():
    with open(_runtime_b2_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


# --- PublicRawSnapshotRecord: immutability / construction -----------------------------------------

def test_raw_snapshot_accepts_valid_and_reads_fields():
    raw = _raw()
    assert raw.source_artifact.startswith("phase4c_batch")
    assert raw.venue == "hyperliquid"
    assert raw.pair == "BTC-USD"
    assert raw.retrieval_epoch_ms == 1_750_000_000_000
    assert raw.raw_snapshot_identity == "replay-fixture-0001"
    assert raw.field_payload == (("bid", "0.50"), ("ask", "0.60"))


def test_raw_snapshot_is_frozen_and_slotted():
    raw = _raw()
    assert not hasattr(raw, "__dict__")
    with pytest.raises(Exception):
        raw.venue = "kraken"
    with pytest.raises(AttributeError):
        object.__setattr__(raw, "injected", 1)


def test_raw_snapshot_direct_construction_blocked():
    with pytest.raises(B2NormalizationTypeError):
        PublicRawSnapshotRecord()


def test_raw_snapshot_anti_coercion_dunders_raise():
    raw = _raw()
    with pytest.raises(B2NormalizationTruthinessError):
        bool(raw)
    with pytest.raises(B2NormalizationTruthinessError):
        len(raw)
    for fn in (int, float, complex):
        with pytest.raises(B2NormalizationCoercionError):
            fn(raw)
    with pytest.raises(B2NormalizationCoercionError):
        str(raw)
    with pytest.raises(B2NormalizationCoercionError):
        bytes(raw)


# --- PublicRawSnapshotRecord: field guards --------------------------------------------------------

@pytest.mark.parametrize("bad", [{"a": 1}, ["x"], {"y"}, None, 123])
def test_raw_snapshot_rejects_non_str_provenance(bad):
    with pytest.raises(B2NormalizationTypeError):
        _raw(venue=bad)


def test_raw_snapshot_rejects_str_subclass_provenance():
    class _S(str):
        pass

    with pytest.raises(B2NormalizationTypeError):
        _raw(venue=_S("hyperliquid"))


@pytest.mark.parametrize("bad", ["", "   "])
def test_raw_snapshot_rejects_empty_provenance(bad):
    with pytest.raises(B2NormalizationValueError):
        _raw(source_field=bad)


@pytest.mark.parametrize("bad", [True, False])
def test_raw_snapshot_rejects_bool_epoch(bad):
    with pytest.raises(B2NormalizationTypeError):
        _raw(retrieval_epoch_ms=bad)


@pytest.mark.parametrize("bad", [1.0, "1750000000000"])
def test_raw_snapshot_rejects_non_int_epoch(bad):
    with pytest.raises(B2NormalizationTypeError):
        _raw(retrieval_epoch_ms=bad)


def test_raw_snapshot_rejects_negative_epoch():
    with pytest.raises(B2NormalizationValueError):
        _raw(retrieval_epoch_ms=-1)


def test_raw_snapshot_accepts_zero_epoch():
    assert _raw(retrieval_epoch_ms=0).retrieval_epoch_ms == 0


# --- PublicRawSnapshotRecord: tuple-only payload --------------------------------------------------

def test_payload_accepts_nested_tuples_of_scalars():
    raw = _raw(field_payload=(("bid", "0.5"), ("ask", "0.6"), ("depth", 3)))
    assert raw.field_payload[2] == ("depth", 3)


@pytest.mark.parametrize("bad", [["x"], {"a": 1}, {"y"}, "not-a-tuple"])
def test_payload_rejects_non_tuple_top_level(bad):
    with pytest.raises(B2NormalizationTypeError):
        _raw(field_payload=bad)


@pytest.mark.parametrize("bad", [(["x"],), ({"a": 1},), ({1, 2},)])
def test_payload_rejects_nested_mutable_containers(bad):
    with pytest.raises(B2NormalizationTypeError):
        _raw(field_payload=bad)


# --- UnitBoundMagnitude: magnitude + unit atomically bound ----------------------------------------

def test_unit_bound_magnitude_requires_both_magnitude_and_unit():
    # magnitude alone is rejected: omitting unit is a missing required keyword-only argument
    with pytest.raises(TypeError):
        make_unit_bound_magnitude(magnitude="0.006")


def test_unit_bound_magnitude_holds_both():
    ubm = _ubm()
    assert ubm.magnitude == "0.006"
    assert ubm.unit == "proportion"


@pytest.mark.parametrize("bad", [0.006, 6, None, {"m": 1}, ["0.006"]])
def test_unit_bound_magnitude_rejects_non_str_magnitude(bad):
    with pytest.raises(B2NormalizationTypeError):
        _ubm(magnitude=bad)


@pytest.mark.parametrize("bad", ["", "   "])
def test_unit_bound_magnitude_rejects_empty_unit(bad):
    with pytest.raises(B2NormalizationValueError):
        _ubm(unit=bad)


def test_unit_bound_magnitude_is_frozen_slotted_blocked():
    ubm = _ubm()
    assert not hasattr(ubm, "__dict__")
    with pytest.raises(B2NormalizationTypeError):
        UnitBoundMagnitude()
    with pytest.raises(Exception):
        ubm.unit = "bps"


# --- NormalizedEvidenceMaterial: identity, provenance, tolerance ----------------------------------

def test_material_references_raw_snapshot_by_identity():
    raw = _raw()
    material = _material(raw_snapshot=raw)
    assert material.raw_snapshot is raw
    assert id(material.raw_snapshot) == id(raw)


def test_material_preserves_provenance_through_raw_snapshot():
    raw = _raw()
    material = _material(raw_snapshot=raw)
    assert material.raw_snapshot.source_artifact == raw.source_artifact
    assert material.raw_snapshot.source_field == raw.source_field
    assert material.raw_snapshot.venue == raw.venue
    assert material.raw_snapshot.pair == raw.pair
    assert material.raw_snapshot.retrieval_epoch_ms == raw.retrieval_epoch_ms
    assert material.raw_snapshot.raw_snapshot_identity == raw.raw_snapshot_identity


@pytest.mark.parametrize("bad", [{"raw": 1}, None, "raw", 123])
def test_material_rejects_non_raw_snapshot(bad):
    with pytest.raises(B2NormalizationTypeError):
        _material(raw_snapshot=bad)


def test_material_rejects_raw_snapshot_subclass():
    class _Sub(PublicRawSnapshotRecord):
        pass

    sub = object.__new__(_Sub)
    with pytest.raises(B2NormalizationTypeError):
        _material(raw_snapshot=sub)


def test_material_normalized_values_must_be_tuple_of_unit_bound():
    assert _material(normalized_values=()).normalized_values == ()
    ok = _material(normalized_values=(_ubm(), _ubm()))
    assert len(ok.normalized_values) == 2


@pytest.mark.parametrize("bad", [["x"], {"a": 1}, {"y"}, "nope"])
def test_material_rejects_non_tuple_normalized_values(bad):
    with pytest.raises(B2NormalizationTypeError):
        _material(normalized_values=bad)


@pytest.mark.parametrize("bad_elem", ["0.006", 0.006, 6, None])
def test_material_rejects_bare_magnitude_element(bad_elem):
    # a bare magnitude (no unit binding) must be rejected
    with pytest.raises(B2NormalizationTypeError):
        _material(normalized_values=(bad_elem,))


def test_material_tolerance_zero_is_valid_strict_match():
    assert _material(evidence_epoch_tolerance_ms=0).evidence_epoch_tolerance_ms == 0


def test_material_tolerance_none_is_malformed():
    with pytest.raises(B2NormalizationTypeError):
        _material(evidence_epoch_tolerance_ms=None)


def test_material_tolerance_negative_is_malformed():
    with pytest.raises(B2NormalizationValueError):
        _material(evidence_epoch_tolerance_ms=-1)


@pytest.mark.parametrize("bad", [True, 1.0, "0"])
def test_material_tolerance_wrong_type_is_malformed(bad):
    with pytest.raises(B2NormalizationTypeError):
        _material(evidence_epoch_tolerance_ms=bad)


def test_material_is_frozen_slotted_blocked():
    material = _material()
    assert not hasattr(material, "__dict__")
    with pytest.raises(B2NormalizationTypeError):
        NormalizedEvidenceMaterial()
    with pytest.raises(Exception):
        material.evidence_epoch_tolerance_ms = 5


# --- missing fields fail fast; no defaults; no loose kwargs ----------------------------------------

def test_missing_required_fields_fail_fast():
    with pytest.raises(TypeError):
        make_public_raw_snapshot_record(source_artifact="a")  # missing the rest


def test_factories_accept_no_var_keyword():
    for fn in (
        make_public_raw_snapshot_record,
        make_unit_bound_magnitude,
        make_normalized_evidence_material,
    ):
        params = inspect.signature(fn).parameters.values()
        assert all(p.kind is not inspect.Parameter.VAR_KEYWORD for p in params), fn.__name__
        assert all(p.kind is not inspect.Parameter.VAR_POSITIONAL for p in params), fn.__name__


# --- structural locks specific to this slice ------------------------------------------------------

def test_b2_runtime_does_not_import_phase5():
    roots = set()
    for node in ast.walk(_b2_tree()):
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


def test_b2_runtime_constructs_no_carriers_and_no_chain_calls():
    referenced = set()
    for node in ast.walk(_b2_tree()):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                referenced.add(alias.name)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
    leaked = _FORBIDDEN_CARRIER_NAMES & referenced
    assert leaked == set(), "carrier construction / chain reference leaked: %r" % leaked


def test_b2_runtime_uses_no_isinstance():
    for node in ast.walk(_b2_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "isinstance"


_FORBIDDEN_IMPORT_ROOTS = {
    "requests", "http", "socket", "websocket", "urllib", "aiohttp", "subprocess",
    "sqlite3", "psycopg2", "ssl", "smtplib", "ftplib", "pickle", "os", "sys",
    "pathlib", "shutil", "tempfile", "io",
}
_FORBIDDEN_CALL_NAMES = {"open", "eval", "exec", "compile", "__import__", "input"}


def test_b2_runtime_has_no_network_env_secret_io():
    tree = _b2_tree()
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
