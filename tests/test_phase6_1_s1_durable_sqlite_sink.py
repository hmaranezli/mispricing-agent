"""tests/test_phase6_1_s1_durable_sqlite_sink.py — Phase 6.1 S1 durable SQLite/WAL adapter.

Pins the append-only SQLite/WAL durable S1 audit adapter defined in
`docs/handoff/phase6_1_s1_durable_storage_field_shape_schema_charter.md` (ratified `fae7caf`). The adapter
lives in the quarantined `phase6_1_s1_storage/` package (outside the locked `phase6_1/` passive package),
records real frozen `ObservationScoreRecord` / `ObservationHaltRecord` via exactly one ACID INSERT each
into a single append-only table, projects embedded live objects into irreversible canonical text evidence
(never pickle/repr/id), and exposes only a minimal append-order readback.

Real records are produced by the proven S5 pipeline so the projection is tested against genuine DTOs.
"""
import ast
import io
import json
import pathlib
import re
import sqlite3

import pytest

import phase6_1
from phase6_1.s1_in_memory_observation_sink import (
    S1InMemoryObservationSink,
    ObservationScoreRecord,
    ObservationHaltRecord,
)
from phase6_1.s5_runner import run_in_memory_shadow_pipeline
from phase6_1.market_provenance_context import MarketProvenanceContext
from phase6_1.gross_edge_binding_label_context import GrossEdgeBindingLabelContext

from phase6_1_s1_storage.s1_durable_sqlite_sink import (
    S1DurableSqliteSink,
    S1DurableSqliteSinkTypeError,
    S1_DURABLE_SQLITE_SINK_COMPONENT_NAME,
    AUDIT_LOG_TABLE_NAME,
)


_PASS_LINE = (
    '{"gross_magnitude": "7", "unit": "proportion", "venue": "hl", "pair": "BTC", '
    '"observed_at_epoch_ms": "1750000000000"}\n'
)
_MALFORMED_LINE = '{bad json not parseable\n'

_EXPECTED_COLUMNS = (
    "append_sequence", "observation_kind", "family_descriptor", "artifact_locator",
    "physical_record_position", "provenance_timestamp", "canonical_text_payload",
)


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


def _real_records(locator="loc"):
    """A (ObservationScoreRecord, ObservationHaltRecord) pair from the proven S5 pipeline."""
    mem = S1InMemoryObservationSink()
    run_in_memory_shadow_pipeline(
        text_stream=io.StringIO(_PASS_LINE + _MALFORMED_LINE),
        artifact_locator=locator,
        market_provenance_context=_provenance(),
        gross_edge_binding_label_context=_label(),
        evidence_epoch_tolerance_ms=0,
        observation_sink=mem,
    )
    return mem.snapshot()


def _db(tmp_path, name="s1.db"):
    return str(tmp_path / name)


def _module_path():
    return pathlib.Path(phase6_1.__file__).resolve().parent.parent / "phase6_1_s1_storage" / \
        "s1_durable_sqlite_sink.py"


def _module_text():
    return _module_path().read_text(encoding="utf-8")


# --- exact schema ---------------------------------------------------------------------------------

def test_table_name_and_exact_seven_column_schema(tmp_path):
    sink = S1DurableSqliteSink(database_path=_db(tmp_path))
    try:
        assert AUDIT_LOG_TABLE_NAME == "s1_observation_audit_log"
        probe = sqlite3.connect(_db(tmp_path))
        info = probe.execute("PRAGMA table_info(s1_observation_audit_log)").fetchall()
        probe.close()
        names = tuple(row[1] for row in info)
        assert names == _EXPECTED_COLUMNS
        by_name = {row[1]: row for row in info}
        assert by_name["append_sequence"][2] == "INTEGER"
        assert by_name["append_sequence"][5] == 1            # primary key
        assert by_name["provenance_timestamp"][3] == 0       # nullable
        for required in ("observation_kind", "family_descriptor", "artifact_locator",
                         "physical_record_position", "canonical_text_payload"):
            assert by_name[required][3] == 1                 # NOT NULL
            assert by_name[required][2] == "TEXT"
    finally:
        sink.close()


def test_pragmas_are_wal_and_synchronous_full(tmp_path):
    path = _db(tmp_path)
    sink = S1DurableSqliteSink(database_path=path)
    try:
        probe = sqlite3.connect(path)
        assert probe.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        probe.close()
        # synchronous is per-connection; assert on the sink's own connection surface via a fresh read
        assert S1DurableSqliteSink(database_path=path)._synchronous_setting() == 2  # FULL == 2
    finally:
        sink.close()


# --- one ACID insert per observation, append order ------------------------------------------------

def test_one_insert_per_observation_in_append_order(tmp_path):
    score, halt = _real_records()
    sink = S1DurableSqliteSink(database_path=_db(tmp_path))
    try:
        sink.record_observation(score)
        sink.record_observation(halt)
        rows = sink.replay()
        assert len(rows) == 2
        assert rows[0]["observation_kind"] == "SCORE"
        assert rows[1]["observation_kind"] == "HALT"
        assert rows[0]["family_descriptor"] == "passive_net_edge_diagnostic"
        assert rows[1]["family_descriptor"] == "passive_local_parse_halt"
    finally:
        sink.close()


def test_envelope_columns_carry_opaque_silver_pair_and_timestamp(tmp_path):
    score, halt = _real_records(locator="artifact-XYZ")
    sink = S1DurableSqliteSink(database_path=_db(tmp_path))
    try:
        sink.record_observation(score)
        sink.record_observation(halt)
        rows = sink.replay()
        assert rows[0]["artifact_locator"] == "artifact-XYZ"
        assert rows[0]["physical_record_position"].isdigit()         # opaque position, verbatim text
        assert rows[0]["provenance_timestamp"] == "1750000000000"    # SCORE observed-at, verbatim
        assert rows[1]["provenance_timestamp"] is None               # HALT carries None
    finally:
        sink.close()


# --- durable projection, not object preservation --------------------------------------------------

def test_score_payload_projects_net_edge_basis_evidence(tmp_path):
    score, _ = _real_records()
    sink = S1DurableSqliteSink(database_path=_db(tmp_path))
    try:
        sink.record_observation(score)
        payload = json.loads(sink.replay()[0]["canonical_text_payload"])
        text = json.dumps(payload)
        assert '"7"' in text                       # net_edge_value / passive_score_magnitude
        assert "passive_net_edge_diagnostic" in text
        assert "gross_edge_value" in text          # basis evidence projected (named field, not object)
        assert "net_edge_unit" in text
    finally:
        sink.close()


def test_halt_payload_projects_local_parse_halt_carrier(tmp_path):
    _, halt = _real_records()
    sink = S1DurableSqliteSink(database_path=_db(tmp_path))
    try:
        sink.record_observation(halt)
        text = sink.replay()[0]["canonical_text_payload"]
        assert "OptionBLocalParseHalt" in text     # carrier type label projected
        assert "passive_local_parse_halt" in text
        assert "bad json not parseable" in text    # the carrier's raw_line evidence, verbatim
    finally:
        sink.close()


def test_no_memory_address_or_repr_leakage_in_payloads(tmp_path):
    score, halt = _real_records()
    sink = S1DurableSqliteSink(database_path=_db(tmp_path))
    try:
        sink.record_observation(score)
        sink.record_observation(halt)
        leak = re.compile(r"object at 0x[0-9A-Fa-f]+|<[\w.]+ object at 0x")
        for row in sink.replay():
            assert leak.search(row["canonical_text_payload"]) is None
    finally:
        sink.close()


def test_canonical_payload_is_deterministic_across_stores(tmp_path):
    score, _ = _real_records()
    a = S1DurableSqliteSink(database_path=_db(tmp_path, "a.db"))
    b = S1DurableSqliteSink(database_path=_db(tmp_path, "b.db"))
    try:
        a.record_observation(score)
        b.record_observation(score)
        assert a.replay()[0]["canonical_text_payload"] == b.replay()[0]["canonical_text_payload"]
    finally:
        a.close()
        b.close()


# --- durability across reopen ---------------------------------------------------------------------

def test_records_persist_across_reopen(tmp_path):
    path = _db(tmp_path)
    score, halt = _real_records()
    first = S1DurableSqliteSink(database_path=path)
    first.record_observation(score)
    first.record_observation(halt)
    first.close()

    reopened = S1DurableSqliteSink(database_path=path)
    try:
        rows = reopened.replay()
        assert len(rows) == 2
        assert rows[0]["observation_kind"] == "SCORE"
        assert rows[1]["observation_kind"] == "HALT"
    finally:
        reopened.close()


# --- rowid containment / return discipline --------------------------------------------------------

def test_rowid_not_leaked_to_caller(tmp_path):
    score, _ = _real_records()
    sink = S1DurableSqliteSink(database_path=_db(tmp_path))
    try:
        assert sink.record_observation(score) is None
        row = sink.replay()[0]
        assert "append_sequence" not in row.keys()
        assert "rowid" not in row.keys()
    finally:
        sink.close()


# --- exact-type admission -------------------------------------------------------------------------

def test_rejects_non_observation_records(tmp_path):
    sink = S1DurableSqliteSink(database_path=_db(tmp_path))
    try:
        for bad in (object(), {"observation_kind": "SCORE"}, None, 7):
            with pytest.raises(S1DurableSqliteSinkTypeError):
                sink.record_observation(bad)
    finally:
        sink.close()


# --- append-only: no UPDATE/DELETE SQL or mutator methods -----------------------------------------

def test_source_has_no_update_delete_or_object_restoration():
    text = _module_text()
    upper = text.upper()
    for sql in ("UPDATE ", "DELETE ", "REPLACE ", "DROP ", " ALTER "):
        assert sql not in upper, sql
    for banned in ("pickle", "dill", "marshal", "shelve", "repr(", "eval(", "__reduce__"):
        assert banned not in text, banned


def test_public_api_has_no_mutator_methods():
    public = {n for n in dir(S1DurableSqliteSink) if not n.startswith("_")}
    assert public == {"record_observation", "replay", "close"}, public


def test_module_uses_no_object_id_leakage():
    tree = ast.parse(_module_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"id", "repr", "vars", "eval", "exec", "compile"}, node.func.id


def test_component_name_constant():
    assert S1_DURABLE_SQLITE_SINK_COMPONENT_NAME == "phase6_1_s1_storage_s1_durable_sqlite_sink"


# --- quarantine: phase6_1/ stays ignorant of storage ----------------------------------------------

def test_pure_phase6_1_package_imports_no_sqlite_or_storage():
    pkg_dir = pathlib.Path(phase6_1.__file__).resolve().parent
    for path in pkg_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "phase6_1_s1_storage" not in text, path.name
        assert "sqlite3" not in text, path.name
