"""phase6_1_s1_storage/s1_durable_sqlite_sink.py — Phase 6.1 durable S1 SQLite/WAL audit adapter.

An append-only, ACID, WAL-mode SQLite durable adapter for the S1 observation audit trail, implemented
exactly per ``docs/handoff/phase6_1_s1_durable_storage_field_shape_schema_charter.md`` (ratified
``fae7caf``). It lives in the quarantined ``phase6_1_s1_storage/`` package so the pure ``phase6_1/``
passive package never references ``sqlite3``, persistence, or payload encoding.

It consumes already-built, frozen ``ObservationScoreRecord`` / ``ObservationHaltRecord`` (read-only — it
never edits, reshapes, or bypasses their factories) and writes each one with exactly one ACID ``INSERT``
into a single append-only table ``s1_observation_audit_log``. The table is a tiny audit envelope plus one
``canonical_text_payload`` column; ``UPDATE`` / ``DELETE`` are never issued.

Embedded live Python object references (the net-edge basis, the halt carrier, the cost-context tuple) are
**irreversibly projected** into canonical textual evidence / opaque structural strings — only named
evidentiary facts and type-name labels are recorded. No object-restoration codec is used and no object
identity or memory address is ever rendered. The medium-intrinsic rowid is internal append
ordering only and is never returned to the caller. The only read surface is a minimal append-order
``replay`` for audit verification — no reporting, aggregation, query DSL, or analytics index.
"""
import dataclasses
import json
import sqlite3

from phase6_1.s1_in_memory_observation_sink import (
    ObservationScoreRecord,
    ObservationHaltRecord,
)
from phase6_1.s2_identity_wiring_candidate import S2IdentityWiringCandidate


S1_DURABLE_SQLITE_SINK_COMPONENT_NAME = "phase6_1_s1_storage_s1_durable_sqlite_sink"
AUDIT_LOG_TABLE_NAME = "s1_observation_audit_log"

# Exact hybrid DDL (charter §5): a tiny audit envelope + exactly one canonical_text_payload column.
_CREATE_TABLE_SQL = (
    "CREATE TABLE IF NOT EXISTS s1_observation_audit_log ("
    "append_sequence INTEGER PRIMARY KEY, "
    "observation_kind TEXT NOT NULL, "
    "family_descriptor TEXT NOT NULL, "
    "artifact_locator TEXT NOT NULL, "
    "physical_record_position TEXT NOT NULL, "
    "provenance_timestamp TEXT, "
    "canonical_text_payload TEXT NOT NULL"
    ")"
)

# append_sequence (rowid) is omitted from the INSERT so SQLite assigns the monotonic append order itself.
_INSERT_SQL = (
    "INSERT INTO s1_observation_audit_log "
    "(observation_kind, family_descriptor, artifact_locator, physical_record_position, "
    "provenance_timestamp, canonical_text_payload) VALUES (?, ?, ?, ?, ?, ?)"
)

# Append-order readback only; append_sequence is intentionally NOT selected (rowid containment).
_REPLAY_SQL = (
    "SELECT observation_kind, family_descriptor, artifact_locator, physical_record_position, "
    "provenance_timestamp, canonical_text_payload FROM s1_observation_audit_log "
    "ORDER BY append_sequence"
)

_SCALAR_TYPES = (str, bool, int, float)


class S1DurableSqliteSinkTypeError(TypeError):
    """Raised when a non-exact observation record (or one without an exact identity carrier) is offered
    for durable recording."""


def _project(value):
    """Irreversibly project any value into canonical, JSON-serialisable evidentiary structure.

    Scalars pass through; tuples/lists/dicts recurse; frozen dataclasses become a labelled mapping of
    their named fields; exceptions become a type label plus their string args; anything else collapses to
    a bare type-name label. No object-restoration codec is used and no object is rendered by address.
    """
    if value is None:
        return None
    value_type = type(value)
    if value_type in _SCALAR_TYPES:
        return value
    if value_type is tuple or value_type is list:
        return [_project(item) for item in value]
    if value_type is dict:
        return {str(key): _project(value[key]) for key in value}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        projected = {"_carrier_type": value_type.__name__}
        for field in dataclasses.fields(value):
            projected[field.name] = _project(getattr(value, field.name))
        return projected
    if isinstance(value, BaseException):
        return {
            "_carrier_type": value_type.__name__,
            "_message_args": [a if type(a) is str else {"_opaque_type": type(a).__name__}
                              for a in value.args],
        }
    return {"_opaque_type": value_type.__name__}


def _opaque_text(value):
    """Value-preserving opaque stringification for an envelope column (never interpreted/sorted)."""
    if type(value) is str:
        return value
    if type(value) is int:          # bool is excluded: ``type(True) is bool``
        return str(value)
    return json.dumps(_project(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _canonical_text_payload(record):
    return json.dumps(_project(record), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _family_descriptor(family_payload):
    if "score_family_descriptor" in family_payload:
        return family_payload["score_family_descriptor"]
    return family_payload["halt_family_descriptor"]


class S1DurableSqliteSink:
    """Append-only durable SQLite/WAL adapter for the S1 observation audit trail."""

    def __init__(self, *, database_path):
        # Autocommit (isolation_level=None): each INSERT statement is its own ACID transaction, fsynced
        # under synchronous=FULL — one durable ACID INSERT per observation.
        self._connection = sqlite3.connect(database_path, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute(_CREATE_TABLE_SQL)

    def record_observation(self, record):
        """Durably append one exact ``ObservationScoreRecord`` / ``ObservationHaltRecord`` via one ACID
        INSERT. Anything else (or a record without an exact ``S2IdentityWiringCandidate`` identity) fails
        fast. Returns ``None`` — the medium-intrinsic rowid is never surfaced."""
        if type(record) is not ObservationScoreRecord and type(record) is not ObservationHaltRecord:
            raise S1DurableSqliteSinkTypeError(
                "record_observation accepts only an exact ObservationScoreRecord or ObservationHaltRecord"
            )
        identity = record.identity_evidence
        if type(identity) is not S2IdentityWiringCandidate:
            raise S1DurableSqliteSinkTypeError(
                "record.identity_evidence must be an exact S2IdentityWiringCandidate"
            )
        provenance_timestamp = record.provenance_timestamp
        self._connection.execute(
            _INSERT_SQL,
            (
                record.observation_kind,
                _family_descriptor(record.family_payload),
                _opaque_text(identity.artifact_locator),
                _opaque_text(identity.physical_record_position),
                None if provenance_timestamp is None else _opaque_text(provenance_timestamp),
                _canonical_text_payload(record),
            ),
        )
        return None

    def replay(self):
        """Return all recorded observations as an immutable tuple of rows in append order (the
        medium-intrinsic append_sequence is the ordering only and is not exposed). Audit verification
        only — no analytics."""
        return tuple(self._connection.execute(_REPLAY_SQL).fetchall())

    def close(self):
        """Close the connection (checkpointing the WAL into the main database file)."""
        self._connection.close()

    def _synchronous_setting(self):
        return self._connection.execute("PRAGMA synchronous").fetchone()[0]
