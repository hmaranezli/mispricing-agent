"""tests/test_phase6_2_s1_evidence_projection.py — Phase 6.2 Slice C — S1 Evidence Projection.

Pins the quarantined, dependency-leaf S1 evidence projector
(`phase6_2_shadow_intent/s1_evidence_projection.py`) after the Lazy-Projection / Constructor-Hardening /
Context-Shape correction. The eager monolith is gone: projection is exposed as six separately invoked,
narrow lazy operations (row-envelope, SCORE family/context/timestamp/unit/magnitude), each inspecting ONLY
its own whitelisted field(s) so a later Slice D/E can enforce the ratified ordering (expiry-before-
unit/magnitude, context relevance, terminal relevance). Every exported carrier is frozen/slotted/kw-only/
methodless and **factory-only** (direct construction raises `S1EvidenceProjectionError`, never a raw
`TypeError`).

Built under the ratified Phase 6.2 chain: planning/slice (`457d279`), predicate (`474cc6f`) +
precedence/decimal-consistency (`d7204d6`), negative-evidence fixture boundary (`b4368fd`, `045caea`), the
score-context empty/whitespace amendment (`04c88fc`), and the fixed-literal / Slice-C-trust-ownership
micro-correction (`c8204ec`).

Successful FULL evidence is adapter-only (through `S1DurableSqliteSink.record_observation` + replay).
Malformed-evidence rejection (and the lazy non-inspection proofs) use the quarantined negative-evidence row
helper, whose single-fault rows are poison. Forbidden tokens / payload identifiers in THIS test file are
explicit fixtures; the runtime stays a stdlib-only leaf with no test/fixture awareness.
"""
import ast
import dataclasses
import importlib.util
import io
import pathlib
import sqlite3
from decimal import Decimal

import pytest

from phase6_2_shadow_intent.s1_evidence_projection import (
    project_row_envelope,
    project_score_family,
    project_score_context,
    project_score_timestamp,
    project_score_unit,
    project_score_magnitude,
    RowEnvelopeProjection,
    ScoreFamilyProjection,
    ScoreContextProjection,
    ScoreTimestampProjection,
    ScoreUnitProjection,
    ScoreMagnitudeProjection,
    S1EvidenceProjectionError,
    S1_EVIDENCE_PROJECTION_COMPONENT_NAME,
    PROJECTION_ROW_NOT_SQLITE_ROW,
    PROJECTION_ROW_COLUMN_SET,
    PROJECTION_DIRECT_CONSTRUCTION,
    PROJECTION_NON_SCORE_OBSERVATION,
)
import phase6_2_shadow_intent.s1_evidence_projection as sep

# adapter-only happy-path pipeline (test-side imports are unrestricted; the RUNTIME stays a leaf).
from phase6_1.s1_in_memory_observation_sink import S1InMemoryObservationSink
from phase6_1.s5_runner import run_in_memory_shadow_pipeline
from phase6_1.market_provenance_context import MarketProvenanceContext
from phase6_1.gross_edge_binding_label_context import GrossEdgeBindingLabelContext
from phase6_1_s1_storage.s1_durable_sqlite_sink import S1DurableSqliteSink


# --- load the quarantined negative-evidence helper by path (tests/ is not a package) --------------
_FIXTURE_PATH = pathlib.Path(__file__).resolve().parent / "fixtures" / "phase6_2_negative_evidence_rows.py"
_spec = importlib.util.spec_from_file_location("_phase6_2_negative_evidence_rows", _FIXTURE_PATH)
neg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(neg)


_PUBLIC_OPERATIONS = (
    project_row_envelope, project_score_family, project_score_context,
    project_score_timestamp, project_score_unit, project_score_magnitude,
)
_SCORE_PAYLOAD_OPERATIONS = (
    project_score_family, project_score_context,
    project_score_timestamp, project_score_unit, project_score_magnitude,
)
_EXPORTED_CARRIERS = (
    RowEnvelopeProjection, ScoreFamilyProjection, ScoreContextProjection,
    ScoreTimestampProjection, ScoreUnitProjection, ScoreMagnitudeProjection,
)


# --- adapter-only happy-path builders (mirrors the ratified S1 durable-sink test) -----------------

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


def _adapter_replay_rows(tmp_path, locator="artifact-XYZ"):
    mem = S1InMemoryObservationSink()
    run_in_memory_shadow_pipeline(
        text_stream=io.StringIO(_PASS_LINE + _MALFORMED_LINE),
        artifact_locator=locator,
        market_provenance_context=_provenance(),
        gross_edge_binding_label_context=_label(),
        evidence_epoch_tolerance_ms=0,
        observation_sink=mem,
    )
    sink = S1DurableSqliteSink(database_path=str(tmp_path / "s1.db"))
    try:
        for record in mem.snapshot():
            sink.record_observation(record)
        return sink.replay()
    finally:
        sink.close()


def _score_row(tmp_path, locator="artifact-XYZ"):
    rows = _adapter_replay_rows(tmp_path, locator=locator)
    assert rows[0]["observation_kind"] == "SCORE"
    return rows[0]


def _halt_row(tmp_path):
    rows = _adapter_replay_rows(tmp_path)
    assert rows[1]["observation_kind"] == "HALT"
    return rows[1]


# --- module identity & no-eager-monolith ----------------------------------------------------------

def test_component_name_constant():
    assert S1_EVIDENCE_PROJECTION_COMPONENT_NAME == "phase6_2_shadow_intent_s1_evidence_projection"


def test_eager_monolith_and_all_field_carriers_are_removed():
    # the bypassable eager compatibility surface must not survive.
    for gone in ("project_s1_evidence", "ScoreEvidenceProjection", "NonScoreEnvelopeProjection"):
        assert not hasattr(sep, gone), gone
    public_projection_ops = {n for n in dir(sep) if n.startswith("project_")}
    assert public_projection_ops == {
        "project_row_envelope", "project_score_family", "project_score_context",
        "project_score_timestamp", "project_score_unit", "project_score_magnitude",
    }


# --- adapter-only SCORE happy path, per narrow operation -------------------------------------------

def test_row_envelope_projection_over_score_row(tmp_path):
    row = _score_row(tmp_path, locator="artifact-XYZ")
    env = project_row_envelope(replay_row=row)
    assert type(env) is RowEnvelopeProjection
    assert env.observation_kind == "SCORE"
    assert env.family_descriptor == "passive_net_edge_diagnostic"
    assert env.silver_artifact_locator == "artifact-XYZ"
    assert env.silver_physical_record_position == row["physical_record_position"]
    assert env.provenance_timestamp == "1750000000000"


def test_score_family_projection(tmp_path):
    fam = project_score_family(replay_row=_score_row(tmp_path))
    assert type(fam) is ScoreFamilyProjection
    assert fam.observation_kind == "SCORE"
    assert fam.family_descriptor == "passive_net_edge_diagnostic"


def test_score_context_projection(tmp_path):
    ctx = project_score_context(replay_row=_score_row(tmp_path))
    assert type(ctx) is ScoreContextProjection
    assert ctx.score_inputs_summary == ("hl", "BTC")
    assert all(type(v) is str for v in ctx.score_inputs_summary)


def test_score_timestamp_projection(tmp_path):
    ts = project_score_timestamp(replay_row=_score_row(tmp_path))
    assert type(ts) is ScoreTimestampProjection
    assert ts.provenance_timestamp == "1750000000000"


def test_score_unit_projection(tmp_path):
    import json
    row = _score_row(tmp_path)
    expected = json.loads(row["canonical_text_payload"])["family_payload"]["score_unit_context"]
    unit = project_score_unit(replay_row=row)
    assert type(unit) is ScoreUnitProjection
    assert unit.score_unit_context == expected


def test_score_magnitude_projection(tmp_path):
    mag = project_score_magnitude(replay_row=_score_row(tmp_path))
    assert type(mag) is ScoreMagnitudeProjection
    assert mag.passive_score_magnitude_text == "7"
    assert mag.passive_score_magnitude == Decimal("7")
    assert type(mag.passive_score_magnitude) is Decimal


# --- adapter-only non-SCORE envelope (no payload internals) ----------------------------------------

def test_row_envelope_projection_over_halt_row(tmp_path):
    row = _halt_row(tmp_path)
    env = project_row_envelope(replay_row=row)
    assert type(env) is RowEnvelopeProjection
    assert env.observation_kind == "HALT"
    assert env.family_descriptor == "passive_local_parse_halt"
    assert env.provenance_timestamp is None                 # HALT carries NULL provenance
    assert env.silver_artifact_locator == row["artifact_locator"]


def test_score_family_op_on_halt_row_is_non_score(tmp_path):
    with pytest.raises(S1EvidenceProjectionError) as exc:
        project_score_family(replay_row=_halt_row(tmp_path))
    assert exc.value.reason == PROJECTION_NON_SCORE_OBSERVATION


# --- constructor hardening: every exported carrier is factory-only --------------------------------

def _one_of_each_carrier(tmp_path):
    row = _score_row(tmp_path)
    return {
        RowEnvelopeProjection: project_row_envelope(replay_row=row),
        ScoreFamilyProjection: project_score_family(replay_row=row),
        ScoreContextProjection: project_score_context(replay_row=row),
        ScoreTimestampProjection: project_score_timestamp(replay_row=row),
        ScoreUnitProjection: project_score_unit(replay_row=row),
        ScoreMagnitudeProjection: project_score_magnitude(replay_row=row),
    }


def test_exported_carriers_reject_every_direct_constructor():
    for carrier in _EXPORTED_CARRIERS:
        for call in (lambda c=carrier: c(),
                     lambda c=carrier: c("positional"),
                     lambda c=carrier: c(bogus="x")):
            with pytest.raises(S1EvidenceProjectionError) as exc:
                call()
            assert exc.value.reason == PROJECTION_DIRECT_CONSTRUCTION


def test_exported_carriers_are_frozen_slotted_kwonly_methodless(tmp_path):
    instances = _one_of_each_carrier(tmp_path)
    for carrier, instance in instances.items():
        assert not hasattr(instance, "__dict__"), carrier                 # slotted, no __dict__
        params = carrier.__dataclass_params__
        assert params.frozen is True and params.kw_only is True, carrier   # frozen + kw-only
        public_methods = [
            name for name in vars(carrier)
            if callable(getattr(carrier, name)) and not name.startswith("__")
        ]
        assert public_methods == [], (carrier, public_methods)             # methodless
        field0 = next(iter(carrier.__dataclass_fields__))
        with pytest.raises(dataclasses.FrozenInstanceError):
            object.__setattr__  # keep import; the next line is the real frozen probe
            setattr(instance, field0, "MUTATED")


def test_factory_published_instances_carry_no_mutable_containers(tmp_path):
    ctx = project_score_context(replay_row=_score_row(tmp_path))
    assert type(ctx.score_inputs_summary) is tuple                         # immutable nested value


# --- lazy precedence: narrow operations over a single-fault poison row -----------------------------

def _assert_succeeds(op, row):
    # a narrow operation that does not inspect the malformed field must succeed (relevance/lazy behavior).
    result = op(replay_row=row)
    assert result is not None


def _assert_raises(op, row, reason):
    with pytest.raises(S1EvidenceProjectionError) as exc:
        op(replay_row=row)
    assert exc.value.reason == reason


def test_lazy_malformed_magnitude_only_magnitude_op_fails():
    row = neg.build_negative_evidence_row(
        case=neg.INVALID_S1_DECIMAL_LEXIS, subvariant=neg.EXPONENT_DECIMAL)
    for op in (project_row_envelope, project_score_family, project_score_context,
               project_score_timestamp, project_score_unit):
        _assert_succeeds(op, row)
    _assert_raises(project_score_magnitude, row, neg.INVALID_S1_DECIMAL_LEXIS)


def test_lazy_malformed_timestamp_only_timestamp_op_fails():
    row = neg.build_negative_evidence_row(
        case=neg.INVALID_PROVENANCE_TIMESTAMP, subvariant=neg.CONSISTENT_NEGATIVE_TIMESTAMP)
    for op in (project_row_envelope, project_score_family, project_score_context,
               project_score_unit, project_score_magnitude):
        _assert_succeeds(op, row)
    _assert_raises(project_score_timestamp, row, neg.INVALID_PROVENANCE_TIMESTAMP)


def test_lazy_malformed_context_only_context_op_fails():
    row = neg.build_negative_evidence_row(
        case=neg.MALFORMED_SCORE_INPUTS_SUMMARY, subvariant=neg.EMPTY_TEXT_ELEMENT)
    for op in (project_row_envelope, project_score_family, project_score_timestamp,
               project_score_unit, project_score_magnitude):
        _assert_succeeds(op, row)
    _assert_raises(project_score_context, row, neg.MALFORMED_SCORE_INPUTS_SUMMARY)


def test_lazy_malformed_json_envelope_succeeds_payload_ops_fail():
    row = neg.build_negative_evidence_row(case=neg.MALFORMED_CANONICAL_JSON)
    _assert_succeeds(project_row_envelope, row)                 # envelope never parses the payload
    for op in _SCORE_PAYLOAD_OPERATIONS:
        _assert_raises(op, row, neg.MALFORMED_CANONICAL_JSON)


# --- negative-evidence fixtures: closed cases / subvariants -> exact reason via the demanding op ----

def _operation_for_case(case):
    return {
        neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT: project_score_family,
        neg.ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT: project_score_family,
        neg.ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT: project_score_timestamp,
        neg.MALFORMED_CANONICAL_JSON: project_score_family,
        neg.MALFORMED_SCORE_INPUTS_SUMMARY: project_score_context,
        neg.INVALID_S1_DECIMAL_LEXIS: project_score_magnitude,
        neg.INVALID_PROVENANCE_TIMESTAMP: project_score_timestamp,
    }[case]


_NEGATIVE_CASES = [
    (neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT, None,
     neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT),
    (neg.ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT, None,
     neg.ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT),
    (neg.ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT, None, neg.ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT),
    (neg.MALFORMED_CANONICAL_JSON, None, neg.MALFORMED_CANONICAL_JSON),
    (neg.MALFORMED_SCORE_INPUTS_SUMMARY, neg.MISSING_SCORE_INPUTS_SUMMARY,
     neg.MALFORMED_SCORE_INPUTS_SUMMARY),
    (neg.MALFORMED_SCORE_INPUTS_SUMMARY, neg.WRONG_ARITY_SCORE_INPUTS_SUMMARY,
     neg.MALFORMED_SCORE_INPUTS_SUMMARY),
    (neg.MALFORMED_SCORE_INPUTS_SUMMARY, neg.NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT,
     neg.MALFORMED_SCORE_INPUTS_SUMMARY),
    (neg.MALFORMED_SCORE_INPUTS_SUMMARY, neg.EMPTY_TEXT_ELEMENT, neg.MALFORMED_SCORE_INPUTS_SUMMARY),
    (neg.MALFORMED_SCORE_INPUTS_SUMMARY, neg.WHITESPACE_ONLY_TEXT_ELEMENT,
     neg.MALFORMED_SCORE_INPUTS_SUMMARY),
    (neg.INVALID_S1_DECIMAL_LEXIS, neg.LEADING_PLUS_DECIMAL, neg.INVALID_S1_DECIMAL_LEXIS),
    (neg.INVALID_S1_DECIMAL_LEXIS, neg.EXPONENT_DECIMAL, neg.INVALID_S1_DECIMAL_LEXIS),
    (neg.INVALID_S1_DECIMAL_LEXIS, neg.WHITESPACE_PADDED_DECIMAL, neg.INVALID_S1_DECIMAL_LEXIS),
    (neg.INVALID_S1_DECIMAL_LEXIS, neg.EMPTY_DECIMAL_TEXT, neg.INVALID_S1_DECIMAL_LEXIS),
    (neg.INVALID_S1_DECIMAL_LEXIS, neg.NON_DECIMAL_TEXT, neg.INVALID_S1_DECIMAL_LEXIS),
    (neg.INVALID_PROVENANCE_TIMESTAMP, neg.CONSISTENT_NEGATIVE_TIMESTAMP,
     neg.INVALID_PROVENANCE_TIMESTAMP),
    (neg.INVALID_PROVENANCE_TIMESTAMP, neg.CONSISTENT_NON_INTEGER_TIMESTAMP,
     neg.INVALID_PROVENANCE_TIMESTAMP),
]


@pytest.mark.parametrize("case,subvariant,expected_reason", _NEGATIVE_CASES)
def test_negative_fixture_is_poison_with_exact_reason(case, subvariant, expected_reason):
    row = neg.build_negative_evidence_row(case=case, subvariant=subvariant)
    assert type(row) is sqlite3.Row
    _assert_raises(_operation_for_case(case), row, expected_reason)


# --- fixture API closure + exact five Case-5 subvariants & byte shapes -----------------------------

def test_case5_has_exactly_five_subvariants():
    assert neg.SCORE_INPUTS_SUMMARY_SUBVARIANTS == (
        neg.MISSING_SCORE_INPUTS_SUMMARY, neg.WRONG_ARITY_SCORE_INPUTS_SUMMARY,
        neg.NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT, neg.EMPTY_TEXT_ELEMENT,
        neg.WHITESPACE_ONLY_TEXT_ELEMENT,
    )


def test_seven_top_level_cases_preserved():
    assert len(neg.NEGATIVE_EVIDENCE_CASES) == 7


def _summary_of(row):
    import json
    return json.loads(row["canonical_text_payload"])["family_payload"]["score_inputs_summary"]


def test_empty_and_whitespace_fixture_exact_byte_shapes():
    empty = neg.build_negative_evidence_row(
        case=neg.MALFORMED_SCORE_INPUTS_SUMMARY, subvariant=neg.EMPTY_TEXT_ELEMENT)
    assert _summary_of(empty) == ["hl", ""]

    ws = neg.build_negative_evidence_row(
        case=neg.MALFORMED_SCORE_INPUTS_SUMMARY, subvariant=neg.WHITESPACE_ONLY_TEXT_ELEMENT)
    summary = _summary_of(ws)
    assert summary == ["hl", " "]
    assert summary[1] == " "
    assert summary[1].encode("utf-8") == b"\x20"               # exactly one 0x20 byte


def test_fixture_rejects_unknown_case_and_bad_subvariant():
    with pytest.raises(neg.NegativeEvidenceFixtureError):
        neg.build_negative_evidence_row(case="NOT_A_CASE")
    with pytest.raises(neg.NegativeEvidenceFixtureError):
        neg.build_negative_evidence_row(
            case=neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT, subvariant=neg.EMPTY_TEXT_ELEMENT)
    with pytest.raises(neg.NegativeEvidenceFixtureError):
        neg.build_negative_evidence_row(case=neg.MALFORMED_SCORE_INPUTS_SUMMARY)  # subvariant required


# --- determinism & no-mutation --------------------------------------------------------------------

def test_repeated_operations_are_deterministic(tmp_path):
    row = _score_row(tmp_path)
    for op in _PUBLIC_OPERATIONS:
        assert op(replay_row=row) == op(replay_row=row)


def test_operations_do_not_mutate_replay_row(tmp_path):
    row = _score_row(tmp_path)
    before = {key: row[key] for key in row.keys()}
    for op in _PUBLIC_OPERATIONS:
        op(replay_row=row)
    after = {key: row[key] for key in row.keys()}
    assert before == after


# --- structural row guards ------------------------------------------------------------------------

def test_every_operation_rejects_non_sqlite_row():
    for op in _PUBLIC_OPERATIONS:
        for bad in ({"observation_kind": "SCORE"}, object(), None, 7):
            with pytest.raises(S1EvidenceProjectionError) as exc:
                op(replay_row=bad)
            assert exc.value.reason == PROJECTION_ROW_NOT_SQLITE_ROW


def test_every_operation_rejects_wrong_column_set():
    connection = sqlite3.connect(":memory:")
    try:
        connection.row_factory = sqlite3.Row
        wrong = connection.execute("SELECT ? AS observation_kind, ? AS family_descriptor",
                                   ("SCORE", "passive_net_edge_diagnostic")).fetchone()
    finally:
        connection.close()
    for op in _PUBLIC_OPERATIONS:
        with pytest.raises(S1EvidenceProjectionError) as exc:
            op(replay_row=wrong)
        assert exc.value.reason == PROJECTION_ROW_COLUMN_SET


# --- dependency leaf + import-direction lock + Slice D/E/F absence ---------------------------------

def _package_dir():
    import phase6_2_shadow_intent
    return pathlib.Path(phase6_2_shadow_intent.__file__).resolve().parent


def _imported_module_roots(source_path):
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                roots.add(".")
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def test_runtime_is_dependency_leaf_stdlib_only():
    source = _package_dir() / "s1_evidence_projection.py"
    roots = _imported_module_roots(source)
    allowed_stdlib = {"sqlite3", "json", "re", "decimal", "dataclasses", "types"}
    assert roots <= allowed_stdlib, roots
    forbidden = {"phase6_1", "phase6_1_s1_storage", "phase5", "logical_model",
                 "artifact_verifier", "classification_predicates", "phase6_2_shadow_intent",
                 "tests", "pytest", "."}
    assert roots.isdisjoint(forbidden), roots


def test_no_phase6_2_production_module_imports_tests_or_fixtures():
    forbidden_roots = {"tests", "pytest", "mock", "_phase6_2_negative_evidence_rows"}
    for source in sorted(_package_dir().glob("*.py")):
        roots = _imported_module_roots(source)
        assert roots.isdisjoint(forbidden_roots), (source.name, roots)
        text = source.read_text(encoding="utf-8")
        for token in ("tests.fixtures", "phase6_2_negative_evidence_rows",
                      "unittest.mock", "monkeypatch"):
            assert token not in text, (source.name, token)


def test_runtime_has_no_test_or_fixture_awareness():
    text = (_package_dir() / "s1_evidence_projection.py").read_text(encoding="utf-8")
    for token in ("pytest", "monkeypatch", "conftest", "unittest",
                  "negative_evidence_rows", "import tests"):
        assert token not in text, token


def test_slice_d_e_f_targets_not_created():
    for absent in ("classification_predicates.py", "atomic_replay_step.py", "reconstruction.py"):
        assert not (_package_dir() / absent).exists(), absent
