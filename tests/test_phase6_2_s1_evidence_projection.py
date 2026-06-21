"""tests/test_phase6_2_s1_evidence_projection.py — Phase 6.2 Slice C — S1 Evidence Projection.

Pins the quarantined, dependency-leaf S1 evidence projector
(`phase6_2_shadow_intent/s1_evidence_projection.py`) after the Strict-Lazy Guard/Context-Precedence &
Publication-Invariant correction. Projection is exposed as strictly independent, separately invoked lazy
operations: a Silver-pair global guard, an observation-kind guard, and five SCORE field operations
(family / context / timestamp / unit / magnitude). Each inspects ONLY its own whitelisted field(s) — no
hidden prerequisite calls — so a later Slice D/E can enforce the legal ordering (Silver-pair guard →
duplicate/root → relevance → per-field classification). Every exported carrier is frozen/slotted/kw-only/
methodless and factory-only; every private maker independently enforces the carrier's complete invariant.

Built under the ratified Phase 6.2 chain (planning `457d279`; predicate `474cc6f` + precedence/decimal
`d7204d6`; negative-evidence boundary `b4368fd`, `045caea`; score-context amendment `04c88fc`;
fixed-literal / trust-ownership `c8204ec`). Successful FULL evidence is adapter-only; malformed-evidence
and lazy non-inspection proofs use the quarantined negative-evidence row helper (unchanged). Forbidden
tokens / payload identifiers in THIS file are explicit fixtures; the runtime stays a stdlib-only leaf.
"""
import ast
import dataclasses
import importlib.util
import inspect
import io
import pathlib
import sqlite3
from decimal import Decimal

import pytest

from phase6_2_shadow_intent.s1_evidence_projection import (
    project_silver_pair,
    project_observation_kind,
    project_score_family,
    project_score_context,
    project_score_timestamp,
    project_score_unit,
    project_score_magnitude,
    SilverPairProjection,
    ObservationKindProjection,
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
    PROJECTION_PUBLICATION_INVARIANT,
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


_GUARD_OPERATIONS = (project_silver_pair, project_observation_kind)
_SCORE_PAYLOAD_OPERATIONS = (
    project_score_family, project_score_context,
    project_score_timestamp, project_score_unit, project_score_magnitude,
)
_PUBLIC_OPERATIONS = _GUARD_OPERATIONS + _SCORE_PAYLOAD_OPERATIONS
_EXPORTED_CARRIERS = (
    SilverPairProjection, ObservationKindProjection, ScoreFamilyProjection, ScoreContextProjection,
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


# --- module identity & removal of the overreading envelope op -------------------------------------

def test_component_name_constant():
    assert S1_EVIDENCE_PROJECTION_COMPONENT_NAME == "phase6_2_shadow_intent_s1_evidence_projection"


def test_overreading_row_envelope_op_and_carrier_are_removed():
    for gone in ("project_row_envelope", "RowEnvelopeProjection",
                 "project_s1_evidence", "ScoreEvidenceProjection", "NonScoreEnvelopeProjection"):
        assert not hasattr(sep, gone), gone
    public_projection_ops = {n for n in dir(sep) if n.startswith("project_")}
    assert public_projection_ops == {
        "project_silver_pair", "project_observation_kind", "project_score_family",
        "project_score_context", "project_score_timestamp", "project_score_unit",
        "project_score_magnitude",
    }


# --- adapter-only SCORE happy path, per narrow operation -------------------------------------------

def test_silver_pair_projection(tmp_path):
    row = _score_row(tmp_path, locator="artifact-XYZ")
    sp = project_silver_pair(replay_row=row)
    assert type(sp) is SilverPairProjection
    assert sp.silver_artifact_locator == "artifact-XYZ"
    assert sp.silver_physical_record_position == row["physical_record_position"]


def test_observation_kind_projection(tmp_path):
    ok = project_observation_kind(replay_row=_score_row(tmp_path))
    assert type(ok) is ObservationKindProjection
    assert ok.observation_kind == "SCORE"


def test_score_family_projection(tmp_path):
    fam = project_score_family(replay_row=_score_row(tmp_path))
    assert type(fam) is ScoreFamilyProjection
    assert fam.observation_kind == "SCORE"
    assert fam.family_descriptor == "passive_net_edge_diagnostic"


def test_score_context_projection(tmp_path):
    ctx = project_score_context(replay_row=_score_row(tmp_path))
    assert type(ctx) is ScoreContextProjection
    assert ctx.score_inputs_summary == ("hl", "BTC")


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


# --- adapter-only non-SCORE: guards work; SCORE-family op is non-SCORE -----------------------------

def test_halt_row_guards_succeed(tmp_path):
    row = _halt_row(tmp_path)
    assert project_silver_pair(replay_row=row).silver_artifact_locator == row["artifact_locator"]
    assert project_observation_kind(replay_row=row).observation_kind == "HALT"


def test_score_family_op_on_halt_row_is_non_score(tmp_path):
    with pytest.raises(S1EvidenceProjectionError) as exc:
        project_score_family(replay_row=_halt_row(tmp_path))
    assert exc.value.reason == PROJECTION_NON_SCORE_OBSERVATION


# --- strict context-first independence (Case 1 / Case 2) ------------------------------------------

def test_context_independent_of_kind_disagreement():
    row = neg.build_negative_evidence_row(case=neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT)
    # context can be determined before family consistency: a kind defect does not abort context.
    assert project_score_context(replay_row=row).score_inputs_summary == ("hl", "BTC")
    with pytest.raises(S1EvidenceProjectionError) as exc:
        project_score_family(replay_row=row)
    assert exc.value.reason == neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT


def test_context_independent_of_family_disagreement():
    row = neg.build_negative_evidence_row(case=neg.ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT)
    assert project_score_context(replay_row=row).score_inputs_summary == ("hl", "BTC")
    with pytest.raises(S1EvidenceProjectionError) as exc:
        project_score_family(replay_row=row)
    assert exc.value.reason == neg.ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT


# --- full operation-by-case non-inspection matrix -------------------------------------------------

def _demanding_op(case):
    return {
        neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT: project_score_family,
        neg.ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT: project_score_family,
        neg.ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT: project_score_timestamp,
        neg.MALFORMED_SCORE_INPUTS_SUMMARY: project_score_context,
        neg.INVALID_S1_DECIMAL_LEXIS: project_score_magnitude,
        neg.INVALID_PROVENANCE_TIMESTAMP: project_score_timestamp,
    }[case]


# (case, subvariant, expected_reason) — single-field poison: exactly ONE op fails, all others succeed.
_SINGLE_FIELD_CASES = [
    (neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT, None,
     neg.ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT),
    (neg.ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT, None,
     neg.ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT),
    (neg.ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT, None, neg.ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT),
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


@pytest.mark.parametrize("case,subvariant,reason", _SINGLE_FIELD_CASES)
def test_single_field_poison_only_demanding_op_fails(case, subvariant, reason):
    row = neg.build_negative_evidence_row(case=case, subvariant=subvariant)
    assert type(row) is sqlite3.Row
    failing = _demanding_op(case)
    with pytest.raises(S1EvidenceProjectionError) as exc:
        failing(replay_row=row)
    assert exc.value.reason == reason
    # every OTHER public operation must succeed (required lazy non-inspection behavior).
    for op in _PUBLIC_OPERATIONS:
        if op is failing:
            continue
        assert op(replay_row=row) is not None, op.__name__


def test_malformed_canonical_json_guards_succeed_payload_ops_fail():
    row = neg.build_negative_evidence_row(case=neg.MALFORMED_CANONICAL_JSON)
    for guard in _GUARD_OPERATIONS:                # silver-pair + observation-kind never parse
        assert guard(replay_row=row) is not None
    for op in _SCORE_PAYLOAD_OPERATIONS:
        with pytest.raises(S1EvidenceProjectionError) as exc:
            op(replay_row=row)
        assert exc.value.reason == neg.MALFORMED_CANONICAL_JSON


# --- publication-maker rejection matrix (direct private-maker exercise) ----------------------------

def _expect_publication_invariant(call):
    with pytest.raises(S1EvidenceProjectionError) as exc:
        call()
    assert exc.value.reason == PROJECTION_PUBLICATION_INVARIANT


def test_publication_makers_reject_malformed_values_without_raw_exceptions():
    _expect_publication_invariant(
        lambda: sep._make_silver_pair(silver_artifact_locator=123,
                                      silver_physical_record_position="x"))
    _expect_publication_invariant(lambda: sep._make_observation_kind(observation_kind=None))
    _expect_publication_invariant(
        lambda: sep._make_score_family(observation_kind="HALT", family_descriptor="x"))
    _expect_publication_invariant(
        lambda: sep._make_score_family(observation_kind="SCORE", family_descriptor="wrong"))
    # context: empty / whitespace-only / wrong-arity / non-text element (no raw TypeError leak)
    _expect_publication_invariant(lambda: sep._make_score_context(score_inputs_summary=("hl", "")))
    _expect_publication_invariant(lambda: sep._make_score_context(score_inputs_summary=("hl", " ")))
    _expect_publication_invariant(
        lambda: sep._make_score_context(score_inputs_summary=("hl", "BTC", "x")))
    _expect_publication_invariant(lambda: sep._make_score_context(score_inputs_summary=("hl", 7)))
    _expect_publication_invariant(lambda: sep._make_score_context(score_inputs_summary=["hl", "BTC"]))
    # timestamp: non-canonical grammar
    _expect_publication_invariant(lambda: sep._make_score_timestamp(provenance_timestamp="-5"))
    _expect_publication_invariant(lambda: sep._make_score_timestamp(provenance_timestamp="01"))
    _expect_publication_invariant(lambda: sep._make_score_timestamp(provenance_timestamp=5))
    # unit
    _expect_publication_invariant(lambda: sep._make_score_unit(score_unit_context=7))
    # magnitude: bad lexis / value mismatch / non-Decimal (no raw InvalidOperation leak)
    _expect_publication_invariant(
        lambda: sep._make_score_magnitude(passive_score_magnitude_text="garbage",
                                          passive_score_magnitude=Decimal("0")))
    _expect_publication_invariant(
        lambda: sep._make_score_magnitude(passive_score_magnitude_text="7",
                                          passive_score_magnitude=Decimal("8")))
    _expect_publication_invariant(
        lambda: sep._make_score_magnitude(passive_score_magnitude_text="7",
                                          passive_score_magnitude="not-a-decimal"))


def test_publication_makers_accept_valid_lexical_variants():
    # valid Phase-5 forms (leading/trailing zeros, negative zero) publish with verbatim text preserved.
    for text in ("007", "1.50", "-0"):
        carrier = sep._make_score_magnitude(
            passive_score_magnitude_text=text, passive_score_magnitude=Decimal(text))
        assert carrier.passive_score_magnitude_text == text
        assert carrier.passive_score_magnitude == Decimal(text)


# --- negative fixtures still poison via the demanding op (deterministic reason) --------------------

@pytest.mark.parametrize("case,subvariant,reason", _SINGLE_FIELD_CASES + [
    (neg.MALFORMED_CANONICAL_JSON, None, neg.MALFORMED_CANONICAL_JSON),
])
def test_negative_fixture_demanding_op_exact_reason(case, subvariant, reason):
    row = neg.build_negative_evidence_row(case=case, subvariant=subvariant)
    op = project_score_family if case == neg.MALFORMED_CANONICAL_JSON else _demanding_op(case)
    with pytest.raises(S1EvidenceProjectionError) as exc:
        op(replay_row=row)
    assert exc.value.reason == reason


# --- constructor hardening: every exported carrier is factory-only --------------------------------

def _one_of_each_carrier(tmp_path):
    row = _score_row(tmp_path)
    return {
        SilverPairProjection: project_silver_pair(replay_row=row),
        ObservationKindProjection: project_observation_kind(replay_row=row),
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
    for carrier, instance in _one_of_each_carrier(tmp_path).items():
        assert not hasattr(instance, "__dict__"), carrier
        params = carrier.__dataclass_params__
        assert params.frozen is True and params.kw_only is True, carrier
        public_methods = [
            name for name in vars(carrier)
            if callable(getattr(carrier, name)) and not name.startswith("__")
        ]
        assert public_methods == [], (carrier, public_methods)
        field0 = next(iter(carrier.__dataclass_fields__))
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(instance, field0, "MUTATED")


def test_context_carrier_owns_immutable_tuple(tmp_path):
    ctx = project_score_context(replay_row=_score_row(tmp_path))
    assert type(ctx.score_inputs_summary) is tuple


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


# --- static proof: guard operations access no forbidden columns / never parse ----------------------

_ALL_COLUMNS = ("observation_kind", "family_descriptor", "artifact_locator",
                "physical_record_position", "provenance_timestamp", "canonical_text_payload")


def _operation_code(func):
    """The function's executable code with its docstring stripped — so static field-access proofs scan
    real references, not documentation prose that legitimately names fields the op does NOT read."""
    tree = ast.parse(inspect.getsource(func))
    fn = tree.body[0]
    if (fn.body and isinstance(fn.body[0], ast.Expr)
            and isinstance(fn.body[0].value, ast.Constant)
            and isinstance(fn.body[0].value.value, str)):
        fn.body = fn.body[1:]
    return ast.unparse(fn)


def test_silver_pair_op_accesses_only_silver_columns():
    code = _operation_code(project_silver_pair)
    allowed = {"artifact_locator", "physical_record_position"}
    for column in _ALL_COLUMNS:
        if column in allowed:
            continue
        assert column not in code, column
    assert "_parse_payload" not in code and "canonical_text_payload" not in code


def test_observation_kind_op_accesses_only_observation_kind():
    code = _operation_code(project_observation_kind)
    for column in _ALL_COLUMNS:
        if column == "observation_kind":
            continue
        assert column not in code, column
    assert "_parse_payload" not in code


def test_context_op_does_not_reference_unrelated_fields():
    code = _operation_code(project_score_context)
    for token in ("observation_kind", "family_descriptor", "score_family_descriptor",
                  "provenance_timestamp", "score_unit_context", "passive_score_magnitude"):
        assert token not in code, token
    # it MAY reach the structural family_payload parent + score_inputs_summary only.
    assert "score_inputs_summary" in code


# --- fixture closure: five Case-5 subvariants + seven top-level cases (helper unchanged) -----------

def test_case5_has_exactly_five_subvariants_and_seven_top_level():
    assert neg.SCORE_INPUTS_SUMMARY_SUBVARIANTS == (
        neg.MISSING_SCORE_INPUTS_SUMMARY, neg.WRONG_ARITY_SCORE_INPUTS_SUMMARY,
        neg.NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT, neg.EMPTY_TEXT_ELEMENT,
        neg.WHITESPACE_ONLY_TEXT_ELEMENT,
    )
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
    assert summary == ["hl", " "] and summary[1].encode("utf-8") == b"\x20"


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


def test_slice_e_f_targets_not_created():
    for absent in ("atomic_replay_step.py", "reconstruction.py"):
        assert not (_package_dir() / absent).exists(), absent
