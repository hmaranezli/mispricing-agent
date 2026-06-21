"""tests/test_phase6_1_b2_pass_path_ingestion.py — Phase 6.1 B2 pass-path ingestion mapping.

Pins the pure, stateless pass-path ingestion boundary defined in
`docs/handoff/phase6_1_b2_pass_path_ingestion_mapping_contract_charter.md`. The boundary consumes EXACTLY
three ratified passive inputs — one Option-B `parsed_payload` mapping, one `MarketProvenanceContext`, and
one `GrossEdgeBindingLabelContext` — and assembles ONE exact `PublicRawSnapshotRecord` through the frozen
`make_public_raw_snapshot_record`, with zero fabrication.

It maps 13 scalar caller arguments + one single GROSS_EDGE `field_payload` binding. It performs no numeric
math (gross magnitude/unit are verbatim strings; a numeric magnitude HALTS, never coerced), the only
permitted numeric carriage is the lossless non-negative-int -> canonical-str for `observed_at_epoch_ms`,
and it never touches S2 identity, Silver tuples, COST/Cell-3, or any runner/stream surface.

Forbidden tokens/identifiers appearing in THIS test file are explicit fixtures; the runtime module must
contain none of them.
"""
import ast
import inspect

import pytest

import phase6_1
from phase6_1.b2_pass_path_ingestion import (
    ingest_pass_path_snapshot_record,
    B2PassPathIngestionTypeError,
    B2PassPathIngestionValueError,
    B2_PASS_PATH_INGESTION_COMPONENT_NAME,
)
from phase6_1.b2_normalization_contract import PublicRawSnapshotRecord
from phase6_1.b2_replay_normalization import normalize_replay_snapshot_to_evidence_material
from phase6_1.market_provenance_context import MarketProvenanceContext
from phase6_1.gross_edge_binding_label_context import GrossEdgeBindingLabelContext


_MODULE_BASENAME = "b2_pass_path_ingestion.py"


# --- deterministic fixtures (record-level source_field deliberately != binding-level source_field) -

def _provenance(**overrides):
    base = dict(
        source_artifact="docs/handoff/replay_artifact_lines",
        source_field="replay.line",                     # record-level provenance
        base_asset="BTC",
        quote_asset="USD",
        instrument_id="BTC-USD-PERP",
        venue_scope="hyperliquid_perp",
        venue_buy="hyperliquid",
        venue_sell="hyperliquid",
        retrieval_epoch_ms=1_750_000_000_500,
        raw_snapshot_identity="market-identity-0001",
    )
    base.update(overrides)
    return MarketProvenanceContext(**base)


def _gross_label(**overrides):
    base = dict(
        normalized_field_name="gross_edge_magnitude",
        source_field="raw.gross_magnitude",             # binding-level provenance, distinct from above
    )
    base.update(overrides)
    return GrossEdgeBindingLabelContext(**base)


def _payload(**overrides):
    base = {
        "gross_magnitude": "12.34",
        "unit": "usd",
        "venue": "hl",
        "pair": "BTC",
        "observed_at_epoch_ms": "1750000000000",        # != str(retrieval) so the anti-copy lock passes
    }
    base.update(overrides)
    return base


_UNSET = object()  # distinct default sentinel: None is itself a value under test, so it can't be the default


def _ingest(parsed_payload=_UNSET, market_provenance_context=_UNSET,
            gross_edge_binding_label_context=_UNSET):
    return ingest_pass_path_snapshot_record(
        parsed_payload=_payload() if parsed_payload is _UNSET else parsed_payload,
        market_provenance_context=_provenance() if market_provenance_context is _UNSET
        else market_provenance_context,
        gross_edge_binding_label_context=_gross_label() if gross_edge_binding_label_context is _UNSET
        else gross_edge_binding_label_context,
    )


def _module_path():
    import pathlib  # test-only path resolution; the runtime imports no pathlib
    return pathlib.Path(phase6_1.__file__).resolve().parent / _MODULE_BASENAME


def _module_tree():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _module_text():
    with open(_module_path(), "r", encoding="utf-8") as fh:
        return fh.read()


# --- construction / scalar field mapping ----------------------------------------------------------

def test_produces_exact_public_raw_snapshot_record():
    record = _ingest()
    assert type(record) is PublicRawSnapshotRecord


def test_maps_all_thirteen_scalar_fields_from_correct_sources():
    record = _ingest()
    # record-level provenance + market identity all come from MarketProvenanceContext (E)
    assert record.source_artifact == "docs/handoff/replay_artifact_lines"
    assert record.source_field == "replay.line"
    assert record.base_asset == "BTC"
    assert record.quote_asset == "USD"
    assert record.instrument_id == "BTC-USD-PERP"
    assert record.venue_scope == "hyperliquid_perp"
    assert record.venue_buy == "hyperliquid"
    assert record.venue_sell == "hyperliquid"
    assert record.retrieval_epoch_ms == 1_750_000_000_500
    assert record.raw_snapshot_identity == "market-identity-0001"
    # venue / pair / observed_at come from the payload (P)
    assert record.venue == "hl"
    assert record.pair == "BTC"
    assert record.observed_at_epoch_ms == "1750000000000"


# --- field_payload: exactly one GROSS_EDGE binding, B2-normalizer-consumable -----------------------

def test_field_payload_is_one_gross_edge_binding_roundtrips_through_frozen_b2_normalizer():
    record = _ingest()
    assert type(record.field_payload) is tuple
    assert len(record.field_payload) == 1  # exactly one binding entry; no COST entry

    material = normalize_replay_snapshot_to_evidence_material(
        raw_snapshot=record, evidence_epoch_tolerance_ms=0
    )
    bindings = material.normalized_field_bindings
    assert len(bindings) == 1
    binding = bindings[0]
    assert binding.binding_role == "GROSS_EDGE"
    assert binding.normalized_field_name == "gross_edge_magnitude"
    assert binding.source_field == "raw.gross_magnitude"
    assert binding.unit_bound_magnitude.magnitude == "12.34"
    assert binding.unit_bound_magnitude.unit == "usd"
    assert binding.zero_cost_evidence is None  # GROSS_EDGE carries no zero-cost evidence (no COST)


def test_record_level_and_binding_level_source_field_are_distinct_and_not_aliased():
    record = _ingest(
        market_provenance_context=_provenance(source_field="record.level.distinct"),
        gross_edge_binding_label_context=_gross_label(source_field="binding.level.distinct"),
    )
    assert record.source_field == "record.level.distinct"
    material = normalize_replay_snapshot_to_evidence_material(
        raw_snapshot=record, evidence_epoch_tolerance_ms=0
    )
    assert material.normalized_field_bindings[0].source_field == "binding.level.distinct"


# --- observed_at_epoch_ms carriage rules ----------------------------------------------------------

def test_observed_at_str_is_carried_verbatim():
    record = _ingest(parsed_payload=_payload(observed_at_epoch_ms="1749999999999"))
    assert record.observed_at_epoch_ms == "1749999999999"


def test_observed_at_non_negative_int_is_losslessly_carried_to_canonical_str():
    record = _ingest(parsed_payload=_payload(observed_at_epoch_ms=1_750_000_000_001))
    assert record.observed_at_epoch_ms == "1750000000001"
    assert type(record.observed_at_epoch_ms) is str


def test_observed_at_zero_int_is_carried_as_canonical_zero_string():
    record = _ingest(parsed_payload=_payload(observed_at_epoch_ms=0))
    assert record.observed_at_epoch_ms == "0"


def test_observed_at_float_halts_without_coercion():
    with pytest.raises(B2PassPathIngestionTypeError):
        _ingest(parsed_payload=_payload(observed_at_epoch_ms=1750000000000.0))


def test_observed_at_bool_halts():
    with pytest.raises(B2PassPathIngestionTypeError):
        _ingest(parsed_payload=_payload(observed_at_epoch_ms=True))


def test_observed_at_negative_int_halts():
    with pytest.raises(B2PassPathIngestionValueError):
        _ingest(parsed_payload=_payload(observed_at_epoch_ms=-1))


# --- precision-safe anti-float seal on the gross magnitude ----------------------------------------

def test_numeric_gross_magnitude_halts_structurally_without_coercion():
    for bad in (12.34, 9, True):
        with pytest.raises(B2PassPathIngestionTypeError):
            _ingest(parsed_payload=_payload(gross_magnitude=bad))


def test_non_str_unit_venue_pair_halt():
    for key in ("unit", "venue", "pair"):
        for bad in (1, 1.0, None, True, ["x"]):
            with pytest.raises(B2PassPathIngestionTypeError):
                _ingest(parsed_payload=_payload(**{key: bad}))


# --- structural ingestion halts: missing keys / non-dict payload ----------------------------------

def test_missing_required_payload_key_halts():
    for key in ("gross_magnitude", "unit", "venue", "pair", "observed_at_epoch_ms"):
        payload = _payload()
        del payload[key]
        with pytest.raises(B2PassPathIngestionValueError):
            _ingest(parsed_payload=payload)


def test_non_dict_payload_halts():
    for bad in (None, [("gross_magnitude", "1")], "payload", 3, ("a",)):
        with pytest.raises(B2PassPathIngestionTypeError):
            _ingest(parsed_payload=bad)


# --- exact-type rejection of the two ratified context inputs ---------------------------------------

def test_rejects_wrong_market_provenance_context_type():
    for bad in (None, {"source_artifact": "x"}, _gross_label(), object()):
        with pytest.raises(B2PassPathIngestionTypeError):
            _ingest(market_provenance_context=bad)


def test_rejects_market_provenance_context_subclass():
    class _Sub(MarketProvenanceContext):
        pass

    sub = object.__new__(_Sub)
    with pytest.raises(B2PassPathIngestionTypeError):
        _ingest(market_provenance_context=sub)


def test_rejects_wrong_gross_edge_label_context_type():
    for bad in (None, {"normalized_field_name": "x"}, _provenance(), object()):
        with pytest.raises(B2PassPathIngestionTypeError):
            _ingest(gross_edge_binding_label_context=bad)


def test_rejects_gross_edge_label_context_subclass():
    class _Sub(GrossEdgeBindingLabelContext):
        pass

    sub = object.__new__(_Sub)
    with pytest.raises(B2PassPathIngestionTypeError):
        _ingest(gross_edge_binding_label_context=sub)


# --- the frozen anti-copy lock is surfaced, never repaired -----------------------------------------

def test_observed_equals_str_retrieval_is_rejected_by_frozen_b2_not_repaired():
    # retrieval_epoch_ms == 1_750_000_000_500; an observed string equal to str(retrieval) must be
    # rejected by the frozen make_public_raw_snapshot_record anti-copy lock, surfaced (not silently fixed).
    from phase6_1.b2_normalization_contract import B2NormalizationValueError
    with pytest.raises(B2NormalizationValueError):
        _ingest(parsed_payload=_payload(observed_at_epoch_ms="1750000000500"))


# --- 3-input exclusive, keyword-only boundary -----------------------------------------------------

def test_signature_is_exactly_three_keyword_only_inputs():
    sig = inspect.signature(ingest_pass_path_snapshot_record)
    params = sig.parameters
    assert list(params) == [
        "parsed_payload", "market_provenance_context", "gross_edge_binding_label_context"
    ]
    for p in params.values():
        assert p.kind is inspect.Parameter.KEYWORD_ONLY
        assert p.default is inspect.Parameter.empty


def test_component_name_constant():
    assert B2_PASS_PATH_INGESTION_COMPONENT_NAME == "phase6_1_b2_pass_path_ingestion"


# --- identity segregation: S2 / Silver / shadow-input completely bypass this boundary --------------

def test_module_does_not_reference_s2_identity_silver_or_shadow_input():
    text = _module_text()
    for forbidden in (
        "S2IdentityWiringCandidate",
        "s2_identity_wiring_candidate",
        "identity_evidence",
        "Silver",
        "silver",
        "passive_shadow_input",
        "PassiveShadowInput",
        "shadow",
        "capacity",
    ):
        assert forbidden not in text, forbidden


def _import_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_module_imports_only_phase6_1_roots():
    roots = _import_roots(_module_tree())
    assert roots <= {"phase6_1"}, roots
    assert "phase5" not in roots
    for forbidden in {"re", "uuid", "datetime", "time", "hashlib", "os", "pathlib", "io", "sys",
                      "json", "logging", "decimal"}:
        assert forbidden not in roots, forbidden


# --- no runner / stream / repair / numeric-cast surface (AST) --------------------------------------

def test_module_has_no_loop_comprehension_or_try_surface():
    banned_nodes = (ast.For, ast.AsyncFor, ast.While, ast.Try,
                    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    for node in ast.walk(_module_tree()):
        assert not isinstance(node, banned_nodes), type(node).__name__


def test_module_has_no_isinstance_or_numeric_cast_or_io_calls():
    banned_calls = {"isinstance", "float", "int", "round", "open", "eval", "exec", "compile",
                    "__import__", "input", "Decimal"}
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls, node.func.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"loads", "dumps"}, node.attr


def test_module_defines_only_the_one_public_function_and_two_error_types():
    func_names = [
        n.name for n in ast.walk(_module_tree())
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert func_names == ["ingest_pass_path_snapshot_record"], func_names
    class_names = [n.name for n in ast.walk(_module_tree()) if isinstance(n, ast.ClassDef)]
    assert class_names == ["B2PassPathIngestionTypeError", "B2PassPathIngestionValueError"], class_names
