"""tests/test_phase6_2_s1_evidence_projection.py — Phase 6.2 Slice C — S1 Evidence Projection.

Pins the quarantined, dependency-leaf S1 evidence projector
(`phase6_2_shadow_intent/s1_evidence_projection.py`) built under the ratified Phase 6.2 chain — the
reconstruction-runtime planning/slice charter (`457d279`), the predicate + precedence/decimal-consistency
charters (`474cc6f`, `d7204d6`), and the negative-evidence fixture-boundary charters (`b4368fd`,
`045caea`).

The projector reads ONLY caller-supplied replay rows (no SQLite query/connection/filesystem/network/
adapter/global-state access), validates the exact whitelist + Phase-5 S1 decimal lexis + row/payload
consistency, and returns a frozen, slotted, methodless immutable projection. Every SUCCESSFUL projection
fixture is built exclusively through the ratified `S1DurableSqliteSink.record_observation` and consumed
from its replay (adapter-only happy-path authority). Malformed-evidence rejection is exercised ONLY via the
quarantined negative-evidence row helper, whose single-fault rows are poison: their only valid outcome is
the Slice-C `S1EvidenceProjectionError`.

Forbidden tokens / payload identifiers appearing in THIS test file are explicit fixtures; the runtime
module stays a stdlib-only leaf with no test/fixture awareness (proven by the dependency + import-direction
locks below).
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
    project_s1_evidence,
    ScoreEvidenceProjection,
    NonScoreEnvelopeProjection,
    S1EvidenceProjectionError,
    S1_EVIDENCE_PROJECTION_COMPONENT_NAME,
    PROJECTION_ROW_NOT_SQLITE_ROW,
    PROJECTION_ROW_COLUMN_SET,
)

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
    """A genuine (SCORE row, HALT row) pair produced exclusively through the ratified S1 adapter."""
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


# --- module identity ------------------------------------------------------------------------------

def test_component_name_constant():
    assert S1_EVIDENCE_PROJECTION_COMPONENT_NAME == "phase6_2_shadow_intent_s1_evidence_projection"


# --- adapter-only SCORE happy path ----------------------------------------------------------------

def test_score_row_from_adapter_projects_whitelisted_evidence(tmp_path):
    import json
    row = _score_row(tmp_path, locator="artifact-XYZ")
    payload = json.loads(row["canonical_text_payload"])
    family = payload["family_payload"]

    projection = project_s1_evidence(replay_row=row)

    assert type(projection) is ScoreEvidenceProjection
    assert projection.observation_kind == "SCORE"
    assert projection.family_descriptor == "passive_net_edge_diagnostic"
    assert projection.silver_artifact_locator == "artifact-XYZ"
    assert projection.silver_physical_record_position == row["physical_record_position"]
    assert projection.provenance_timestamp == row["provenance_timestamp"] == "1750000000000"
    assert projection.passive_score_magnitude_text == family["passive_score_magnitude"]
    assert projection.passive_score_magnitude == Decimal(family["passive_score_magnitude"])
    assert projection.score_unit_context == family["score_unit_context"]
    assert projection.score_inputs_summary == tuple(family["score_inputs_summary"])


def test_score_projection_exposes_only_the_whitelisted_fields():
    fields = {f.name for f in dataclasses.fields(ScoreEvidenceProjection)}
    assert fields == {
        "silver_artifact_locator", "silver_physical_record_position",
        "observation_kind", "family_descriptor", "provenance_timestamp",
        "passive_score_magnitude_text", "passive_score_magnitude",
        "score_unit_context", "score_inputs_summary",
    }


def test_score_projection_is_frozen_slotted_and_methodless(tmp_path):
    projection = project_s1_evidence(replay_row=_score_row(tmp_path))
    assert not hasattr(projection, "__dict__")                      # slotted
    with pytest.raises(dataclasses.FrozenInstanceError):
        projection.observation_kind = "MUTATED"                     # frozen
    public_methods = [
        name for name in vars(type(projection))
        if callable(getattr(type(projection), name)) and not name.startswith("__")
    ]
    assert public_methods == []                                     # methodless data carrier


def test_score_inputs_summary_is_two_text_tuple(tmp_path):
    projection = project_s1_evidence(replay_row=_score_row(tmp_path))
    assert type(projection.score_inputs_summary) is tuple
    assert len(projection.score_inputs_summary) == 2
    assert all(type(v) is str for v in projection.score_inputs_summary)


def test_passive_score_magnitude_is_exact_decimal(tmp_path):
    projection = project_s1_evidence(replay_row=_score_row(tmp_path))
    assert type(projection.passive_score_magnitude) is Decimal
    # verbatim S1 lexis preserved alongside the exact Decimal value.
    assert projection.passive_score_magnitude == Decimal(projection.passive_score_magnitude_text)


# --- adapter-only NON-SCORE envelope path (no HALT internals) -------------------------------------

def test_non_score_halt_row_projects_envelope_only(tmp_path):
    row = _halt_row(tmp_path)
    projection = project_s1_evidence(replay_row=row)
    assert type(projection) is NonScoreEnvelopeProjection
    assert projection.observation_kind == "HALT"
    assert projection.family_descriptor == "passive_local_parse_halt"
    assert projection.silver_artifact_locator == row["artifact_locator"]
    assert projection.silver_physical_record_position == row["physical_record_position"]
    assert projection.provenance_timestamp is None                  # HALT carries NULL provenance


def test_non_score_envelope_exposes_only_envelope_fields_no_internals():
    fields = {f.name for f in dataclasses.fields(NonScoreEnvelopeProjection)}
    assert fields == {
        "silver_artifact_locator", "silver_physical_record_position",
        "observation_kind", "family_descriptor", "provenance_timestamp",
    }
    # no SCORE / HALT payload internals are surfaced.
    for banned in ("passive_score_magnitude", "score_inputs_summary", "score_unit_context",
                   "canonical_text_payload"):
        assert banned not in fields


def test_non_score_envelope_is_frozen_and_slotted(tmp_path):
    projection = project_s1_evidence(replay_row=_halt_row(tmp_path))
    assert not hasattr(projection, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        projection.observation_kind = "MUTATED"


# --- determinism & no-mutation --------------------------------------------------------------------

def test_repeated_projection_is_deterministic(tmp_path):
    row = _score_row(tmp_path)
    assert project_s1_evidence(replay_row=row) == project_s1_evidence(replay_row=row)


def test_projection_does_not_mutate_replay_row(tmp_path):
    row = _score_row(tmp_path)
    before = {key: row[key] for key in row.keys()}
    project_s1_evidence(replay_row=row)
    after = {key: row[key] for key in row.keys()}
    assert before == after


# --- structural row guards (step 3) ---------------------------------------------------------------

def test_rejects_non_sqlite_row():
    for bad in ({"observation_kind": "SCORE"}, object(), None, 7, ("SCORE",)):
        with pytest.raises(S1EvidenceProjectionError) as exc:
            project_s1_evidence(replay_row=bad)
        assert exc.value.reason == PROJECTION_ROW_NOT_SQLITE_ROW


def test_rejects_wrong_column_set():
    # a genuine sqlite3.Row, but NOT the exact six projected columns.
    connection = sqlite3.connect(":memory:")
    try:
        connection.row_factory = sqlite3.Row
        wrong = connection.execute("SELECT ? AS observation_kind, ? AS family_descriptor",
                                   ("SCORE", "passive_net_edge_diagnostic")).fetchone()
    finally:
        connection.close()
    with pytest.raises(S1EvidenceProjectionError) as exc:
        project_s1_evidence(replay_row=wrong)
    assert exc.value.reason == PROJECTION_ROW_COLUMN_SET


# --- negative-evidence fixtures: closed cases / subvariants, single-fault poison -------------------

_NEGATIVE_CASES = [
    (neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT, None,
     neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT),
    (neg.ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT, None,
     neg.ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT),
    (neg.ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT, None,
     neg.ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT),
    (neg.MALFORMED_CANONICAL_JSON, None, neg.MALFORMED_CANONICAL_JSON),
    (neg.MALFORMED_SCORE_INPUTS_SUMMARY, neg.MISSING_SCORE_INPUTS_SUMMARY,
     neg.MALFORMED_SCORE_INPUTS_SUMMARY),
    (neg.MALFORMED_SCORE_INPUTS_SUMMARY, neg.WRONG_ARITY_SCORE_INPUTS_SUMMARY,
     neg.MALFORMED_SCORE_INPUTS_SUMMARY),
    (neg.MALFORMED_SCORE_INPUTS_SUMMARY, neg.NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT,
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
    with pytest.raises(S1EvidenceProjectionError) as exc:
        project_s1_evidence(replay_row=row)
    # single-fault isolation: the EXACT ratified category, never an incidental earlier failure.
    assert exc.value.reason == expected_reason


def test_negative_case_3_owns_timestamp_disagreement_case_7_is_consistent():
    # Case 3 (disagreement) and Case 7 (consistent invalid) are a strict, non-overlapping partition.
    row3 = neg.build_negative_evidence_row(case=neg.ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT)
    with pytest.raises(S1EvidenceProjectionError) as e3:
        project_s1_evidence(replay_row=row3)
    assert e3.value.reason == neg.ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT

    row7 = neg.build_negative_evidence_row(
        case=neg.INVALID_PROVENANCE_TIMESTAMP, subvariant=neg.CONSISTENT_NEGATIVE_TIMESTAMP)
    with pytest.raises(S1EvidenceProjectionError) as e7:
        project_s1_evidence(replay_row=row7)
    assert e7.value.reason == neg.INVALID_PROVENANCE_TIMESTAMP


# --- fixture API closure (closed selector, not a generic factory) ---------------------------------

def test_fixture_rejects_unknown_case_and_bad_subvariant():
    with pytest.raises(neg.NegativeEvidenceFixtureError):
        neg.build_negative_evidence_row(case="NOT_A_CASE")
    with pytest.raises(neg.NegativeEvidenceFixtureError):
        # case 1 accepts NO subvariant
        neg.build_negative_evidence_row(
            case=neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT, subvariant=neg.EMPTY_DECIMAL_TEXT)
    with pytest.raises(neg.NegativeEvidenceFixtureError):
        # case 6 REQUIRES a subvariant
        neg.build_negative_evidence_row(case=neg.INVALID_S1_DECIMAL_LEXIS)


def test_fixture_returns_only_a_closed_connectionless_row():
    row = neg.build_negative_evidence_row(case=neg.MALFORMED_CANONICAL_JSON)
    assert type(row) is sqlite3.Row
    # the Row survives the (already-closed) connection and exposes exactly the six aliases.
    assert set(row.keys()) == {
        "observation_kind", "family_descriptor", "artifact_locator",
        "physical_record_position", "provenance_timestamp", "canonical_text_payload",
    }


# --- dependency leaf + import-direction lock ------------------------------------------------------

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
            if node.level:                         # relative import
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
                 "artifact_verifier", "phase6_2_shadow_intent", "tests", "pytest", "."}
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
    # No code-level coupling to the test harness (a docstring citing the authorizing fixture-boundary
    # charters is documentation, not awareness — the runtime carries no test flag/branch/parser).
    text = (_package_dir() / "s1_evidence_projection.py").read_text(encoding="utf-8")
    for token in ("pytest", "monkeypatch", "conftest", "unittest",
                  "negative_evidence_rows", "import tests"):
        assert token not in text, token
