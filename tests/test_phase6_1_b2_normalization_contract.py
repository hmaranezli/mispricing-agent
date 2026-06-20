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
    NormalizedEvidenceFieldBinding,
    NormalizedEvidenceMaterial,
    make_public_raw_snapshot_record,
    make_unit_bound_magnitude,
    make_normalized_evidence_field_binding,
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
        base_asset="BTC",
        quote_asset="USD",
        instrument_id="BTC-USD-PERP",
        venue_scope="SINGLE_VENUE",
        venue_buy="hyperliquid",
        venue_sell="hyperliquid",
        retrieval_epoch_ms=1_750_000_000_000,
        observed_at_epoch_ms="1749990000000",
        raw_snapshot_identity="replay-fixture-0001",
        field_payload=(("bid", "0.50"), ("ask", "0.60")),
    )
    kwargs.update(overrides)
    return make_public_raw_snapshot_record(**kwargs)


def _ubm(**overrides):
    kwargs = dict(magnitude="0.006", unit="proportion")
    kwargs.update(overrides)
    return make_unit_bound_magnitude(**kwargs)


def _binding(**overrides):
    kwargs = dict(
        normalized_field_name="gross_edge",
        source_field="summary.gross_edge",
        unit_bound_magnitude=_ubm(),
    )
    kwargs.update(overrides)
    return make_normalized_evidence_field_binding(**kwargs)


def _material(**overrides):
    kwargs = dict(
        raw_snapshot=_raw(),
        normalized_field_bindings=(_binding(),),
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


# --- NormalizedEvidenceFieldBinding: explicit field binding (no positional semantics) -------------

def test_binding_direct_construction_blocked():
    with pytest.raises(B2NormalizationTypeError):
        NormalizedEvidenceFieldBinding()


def test_binding_is_frozen_slotted_no_dict():
    binding = _binding()
    assert not hasattr(binding, "__dict__")
    with pytest.raises(Exception):
        binding.normalized_field_name = "tampered"
    with pytest.raises(AttributeError):
        object.__setattr__(binding, "injected", 1)


def test_binding_holds_fields_and_preserves_magnitude_by_identity():
    ubm = _ubm()
    binding = _binding(unit_bound_magnitude=ubm)
    assert binding.normalized_field_name == "gross_edge"
    assert binding.source_field == "summary.gross_edge"
    assert binding.unit_bound_magnitude is ubm
    assert id(binding.unit_bound_magnitude) == id(ubm)


def test_binding_requires_all_three_fields():
    with pytest.raises(TypeError):
        make_normalized_evidence_field_binding(
            normalized_field_name="gross_edge", source_field="summary.gross_edge"
        )


@pytest.mark.parametrize("field", ["normalized_field_name", "source_field"])
@pytest.mark.parametrize("bad", [123, None, {"a": 1}, ["x"]])
def test_binding_rejects_non_str_names(field, bad):
    with pytest.raises(B2NormalizationTypeError):
        _binding(**{field: bad})


def test_binding_rejects_str_subclass_name():
    class _S(str):
        pass

    with pytest.raises(B2NormalizationTypeError):
        _binding(normalized_field_name=_S("gross_edge"))


@pytest.mark.parametrize("field", ["normalized_field_name", "source_field"])
@pytest.mark.parametrize("bad", ["", "   "])
def test_binding_rejects_empty_names(field, bad):
    with pytest.raises(B2NormalizationValueError):
        _binding(**{field: bad})


@pytest.mark.parametrize("bad", ["0.006", 0.006, None, {"m": 1}])
def test_binding_rejects_bare_magnitude(bad):
    with pytest.raises(B2NormalizationTypeError):
        _binding(unit_bound_magnitude=bad)


def test_binding_rejects_unit_bound_magnitude_subclass():
    class _Sub(UnitBoundMagnitude):
        pass

    sub = object.__new__(_Sub)
    with pytest.raises(B2NormalizationTypeError):
        _binding(unit_bound_magnitude=sub)


# --- NormalizedEvidenceMaterial: binding collection (no positional semantics) ----------------------

def test_material_accepts_tuple_of_exact_bindings():
    assert _material(normalized_field_bindings=()).normalized_field_bindings == ()
    ok = _material(normalized_field_bindings=(
        _binding(normalized_field_name="gross_edge"),
        _binding(normalized_field_name="total_cost"),
    ))
    assert len(ok.normalized_field_bindings) == 2


def test_material_rejects_tuple_of_bare_unit_bound_magnitude():
    with pytest.raises(B2NormalizationTypeError):
        _material(normalized_field_bindings=(_ubm(),))


@pytest.mark.parametrize("bad", [["x"], {"a": 1}, {"y"}, frozenset({"z"}), "nope"])
def test_material_rejects_non_tuple_bindings(bad):
    with pytest.raises(B2NormalizationTypeError):
        _material(normalized_field_bindings=bad)


def test_material_rejects_duplicate_normalized_field_name():
    with pytest.raises(B2NormalizationValueError):
        _material(normalized_field_bindings=(
            _binding(normalized_field_name="gross_edge"),
            _binding(normalized_field_name="gross_edge"),
        ))


def test_material_infers_no_meaning_from_index_under_reversal():
    forward = (
        _binding(normalized_field_name="gross_edge", source_field="summary.gross_edge"),
        _binding(normalized_field_name="total_cost", source_field="summary.total_cost"),
    )
    reversed_bindings = tuple(reversed(forward))
    material = _material(normalized_field_bindings=reversed_bindings)
    # each binding still carries its own explicit field names regardless of tuple position
    assert material.normalized_field_bindings[0].normalized_field_name == "total_cost"
    assert material.normalized_field_bindings[0].source_field == "summary.total_cost"
    assert material.normalized_field_bindings[1].normalized_field_name == "gross_edge"
    assert material.normalized_field_bindings[1].source_field == "summary.gross_edge"


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


# --- Slice 1: core market identity fields on the raw snapshot --------------------------------------

_CORE_STR_IDENTITY_FIELDS = [
    "base_asset", "quote_asset", "venue_scope", "venue_buy", "venue_sell", "instrument_id",
]


def test_raw_snapshot_accepts_core_market_identity_fields():
    raw = _raw()
    assert raw.base_asset == "BTC"
    assert raw.quote_asset == "USD"
    assert raw.instrument_id == "BTC-USD-PERP"
    assert raw.venue_scope == "SINGLE_VENUE"
    assert raw.venue_buy == "hyperliquid"
    assert raw.venue_sell == "hyperliquid"
    assert raw.observed_at_epoch_ms == "1749990000000"


@pytest.mark.parametrize("field", _CORE_STR_IDENTITY_FIELDS)
@pytest.mark.parametrize("bad", [123, None, {"a": 1}, ["x"], True, 1.0])
def test_raw_snapshot_rejects_non_str_core_identity(field, bad):
    with pytest.raises(B2NormalizationTypeError):
        _raw(**{field: bad})


@pytest.mark.parametrize("field", _CORE_STR_IDENTITY_FIELDS)
def test_raw_snapshot_rejects_str_subclass_core_identity(field):
    class _S(str):
        pass

    with pytest.raises(B2NormalizationTypeError):
        _raw(**{field: _S("BTC")})


@pytest.mark.parametrize("field", _CORE_STR_IDENTITY_FIELDS)
@pytest.mark.parametrize("bad", ["", "   "])
def test_raw_snapshot_rejects_empty_core_identity(field, bad):
    with pytest.raises(B2NormalizationValueError):
        _raw(**{field: bad})


def test_core_identity_fields_are_not_derived_from_pair_or_venue():
    # carrier/contract only: values are carried verbatim, never split or projected
    raw = _raw(
        pair="ETH-USDT", venue="binance",
        base_asset="ETH", quote_asset="USDT", instrument_id="ETH-USDT-PERP",
        venue_scope="CROSS_VENUE", venue_buy="binance", venue_sell="hyperliquid",
    )
    assert raw.pair == "ETH-USDT"
    assert raw.venue == "binance"
    assert raw.base_asset == "ETH"
    assert raw.quote_asset == "USDT"
    assert raw.venue_buy == "binance"
    assert raw.venue_sell == "hyperliquid"


# --- Slice 1: observed_at_epoch_ms canonical unsigned integer string + time isolation --------------

def test_observed_at_epoch_ms_accepts_canonical_unsigned_int_string():
    assert _raw(observed_at_epoch_ms="0", retrieval_epoch_ms=1).observed_at_epoch_ms == "0"
    assert _raw(observed_at_epoch_ms="42", retrieval_epoch_ms=1).observed_at_epoch_ms == "42"


@pytest.mark.parametrize("bad", [1749990000000, 1.0, True, None, {"t": 1}, ["1"]])
def test_observed_at_epoch_ms_rejects_non_str(bad):
    with pytest.raises(B2NormalizationTypeError):
        _raw(observed_at_epoch_ms=bad)


@pytest.mark.parametrize("bad", ["", "   ", "-1", "1.0", "1_000", "12a", "0x1f", "007", " 12", "12 "])
def test_observed_at_epoch_ms_rejects_non_canonical(bad):
    with pytest.raises(B2NormalizationValueError):
        _raw(observed_at_epoch_ms=bad)


def test_observed_at_epoch_ms_must_not_equal_str_of_retrieval_epoch_ms():
    # anti-copy / lookahead-bias lock: observed time is not the retrieval timestamp stringified
    with pytest.raises(B2NormalizationValueError):
        _raw(retrieval_epoch_ms=1_750_000_000_000, observed_at_epoch_ms="1750000000000")


def test_observed_at_epoch_ms_distinct_from_retrieval_is_accepted():
    raw = _raw(retrieval_epoch_ms=1_750_000_000_000, observed_at_epoch_ms="1749999999000")
    assert raw.retrieval_epoch_ms == 1_750_000_000_000
    assert raw.observed_at_epoch_ms == "1749999999000"


def test_missing_observed_at_epoch_ms_fails_fast():
    with pytest.raises(TypeError):
        make_public_raw_snapshot_record(
            source_artifact="a", source_field="b", venue="hyperliquid", pair="BTC-USD",
            base_asset="BTC", quote_asset="USD", instrument_id="BTC-USD-PERP",
            venue_scope="SINGLE_VENUE", venue_buy="hyperliquid", venue_sell="hyperliquid",
            retrieval_epoch_ms=1_750_000_000_000,
            raw_snapshot_identity="replay-fixture-0001", field_payload=(),
        )  # observed_at_epoch_ms intentionally omitted


def test_raw_snapshot_with_core_identity_stays_frozen_slotted():
    raw = _raw()
    assert not hasattr(raw, "__dict__")
    with pytest.raises(Exception):
        raw.base_asset = "ETH"
    with pytest.raises(AttributeError):
        object.__setattr__(raw, "injected_identity", 1)


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
