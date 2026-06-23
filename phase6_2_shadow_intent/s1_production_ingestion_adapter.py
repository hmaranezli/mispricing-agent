"""phase6_2_shadow_intent/s1_production_ingestion_adapter.py — Phase 6.2 — S1 Production Ingestion
Adapter / Durable Writer.

Minimal, pure, stdlib-only bridge implementing the ratified Post-Phase 6.2 S1 Production Ingestion Adapter
/ Durable Writer TDD Charter
(``docs/handoff/post_phase6_2_s1_production_ingestion_adapter_durable_writer_tdd_charter.md``) and its
RATIFIED boundary charter.

It reads an **already-captured** raw-evidence ledger in **read-only** mode, extracts exactly one
RAW_COMMITTED Polymarket CLOB YES-token capture and one RAW_COMMITTED Hyperliquid l2Book capture, delegates
**all** projection / validation to the RATIFIED ``s1_paired_projection`` runtime, and appends a single
deterministic, idempotent audit row to a **caller-supplied** destination table on a **caller-supplied**
SQLite connection.

Boundary (binding): no network / localhost / API client / scheduler / daemon / poller / cron / loop /
background task / real ``/root`` ledger path / real-or-prod S1 DB. It performs **no** raw-ledger mutation
(read-only), implements **no** parallel projection formula (reuses ``s1_paired_projection``), creates /
migrates **no** schema (the destination table must pre-exist), and triggers **no** data collection,
calibration, trading, or actionability. Decimals are persisted as exact source strings (never ``float``).
Replay is a deterministic **no-op** keyed on both source content identities (``response_body_sha256``),
never on ``rowid`` / wall-clock / insertion order — so orphan / duplicate rows are structurally impossible.
Failures surface only the RATIFIED closed ``S1PairedProjectionError`` literals. Capacity stays 0; production
ingestion remains BLOCKED.
"""
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass

from . import s1_paired_projection as projection
from .s1_paired_projection import S1PairedProjectionError


S1_PRODUCTION_INGESTION_ADAPTER_COMPONENT_NAME = "phase6_2_shadow_intent_s1_production_ingestion_adapter"

# Stable projection-runtime authority identifier carried on every audit row (provenance, not a version bump).
PROJECTION_AUTHORITY = "phase6_2_shadow_intent.s1_paired_projection/PAIRED_S1_V1"

_SAFE_TABLE_NAME = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")
_TOKEN_TARGET_PREFIX = "/book?token_id="


@dataclass(frozen=True, slots=True)
class IngestResult:
    """Outcome of a single ingest: whether a new audit row was written, the deterministic idempotency key,
    and the RATIFIED projection carrier."""

    written: bool
    idempotency_key: str
    projection: object


def open_raw_ledger_readonly(path):
    """Open the raw-evidence ledger strictly read-only (SQLite ``mode=ro`` URI). Any write attempt through
    the returned connection fails closed at the SQLite layer."""
    return sqlite3.connect("file:%s?mode=ro" % path, uri=True)


def _single_committed_capture(ro_conn, source_authority):
    """Return the single RAW_COMMITTED capture row for ``source_authority`` as a dict, or ``None`` when the
    evidence is absent or not unambiguously a single committed capture."""
    rows = ro_conn.execute(
        "SELECT c.capture_sequence, c.source_authority, c.request_target, c.response_body,"
        "       c.response_body_sha256"
        " FROM raw_capture_log c"
        " JOIN raw_fetch_attempt_log a"
        "   ON a.capture_sequence = c.capture_sequence AND a.outcome = 'RAW_COMMITTED'"
        " WHERE c.source_authority = ?",
        (source_authority,)).fetchall()
    if len(rows) != 1:
        return None
    capture_sequence, src, request_target, response_body, sha = rows[0]
    return {
        "capture_sequence": capture_sequence,
        "source_authority": src,
        "request_target": request_target,
        "response_body": response_body,
        "response_body_sha256": sha,
    }


def _decode_body(response_body):
    """Decode the raw response body into a dict; any decode failure yields an empty dict so that the
    downstream RATIFIED projection raises the appropriate closed missing/shape literal (fail closed)."""
    try:
        parsed = json.loads(response_body)
    except (ValueError, TypeError, UnicodeDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _token_id_from_target(request_target):
    if isinstance(request_target, str) and request_target.startswith(_TOKEN_TARGET_PREFIX):
        return request_target[len(_TOKEN_TARGET_PREFIX):]
    return None


def _build_polymarket_evidence(capture):
    body = _decode_body(capture["response_body"])
    evidence = {
        "source_authority": capture["source_authority"],
        "polymarket_token_id": _token_id_from_target(capture["request_target"]),
        "polymarket_outcome_label": "Yes",  # ratified YES-token binding; never inferred from payload text
        "capture_sequence": capture["capture_sequence"],
        "response_body_sha256": capture["response_body_sha256"],
        # source-issued CLOB $.timestamp only; retrieval columns are never read as event time.
        "timestamp_source": projection.POLYMARKET_SOURCE_ISSUED_TIMESTAMP,
    }
    if "timestamp" in body:
        evidence["polymarket_timestamp_raw_string"] = body["timestamp"]
    return evidence


def _build_hyperliquid_evidence(capture):
    body = _decode_body(capture["response_body"])
    evidence = {
        "source_authority": capture["source_authority"],
        "hyperliquid_coin": body.get("coin"),
        "capture_sequence": capture["capture_sequence"],
        "response_body_sha256": capture["response_body_sha256"],
        # source-issued l2Book $.time only; retrieval columns are never read as event time.
        "time_source": projection.HYPERLIQUID_SOURCE_ISSUED_TIME,
        # ratified manual side axiom (operator-owned, not a JSON fact).
        "levels_side_axiom": list(projection.RATIFIED_SIDE_AXIOM),
    }
    if "time" in body:
        evidence["hyperliquid_time_ms"] = body["time"]
    if "levels" in body:
        evidence["levels"] = body["levels"]
    return evidence


def _idempotency_key(carrier):
    """Deterministic key derived from BOTH source content identities (response_body_sha256), independent of
    rowid / wall-clock / insertion order."""
    material = "%s|%s" % (
        carrier.polymarket_response_body_sha256, carrier.hyperliquid_response_body_sha256)
    return hashlib.sha256(material.encode("ascii")).hexdigest()


def ingest_paired_s1_projection(*, raw_ledger_path, destination_connection, destination_table):
    """Bridge one ratified BTC paired CLOB-YES + l2Book observation from a read-only raw ledger into a
    single idempotent audit row on the caller-supplied destination table. Fail-closed at every divergence
    via the RATIFIED ``S1PairedProjectionError`` literals; never mutates the raw ledger; never creates
    schema."""
    if _SAFE_TABLE_NAME.match(destination_table) is None:
        raise ValueError("destination_table must be a simple SQL identifier")

    ro_conn = open_raw_ledger_readonly(raw_ledger_path)
    try:
        polymarket_capture = _single_committed_capture(
            ro_conn, projection.RATIFIED_POLYMARKET_SOURCE_AUTHORITY)
        hyperliquid_capture = _single_committed_capture(
            ro_conn, projection.RATIFIED_HYPERLIQUID_SOURCE_AUTHORITY)
    finally:
        ro_conn.close()

    if polymarket_capture is None:
        raise S1PairedProjectionError(
            projection.S1_PAIR_POLYMARKET_EVIDENCE_MISSING,
            "no single RAW_COMMITTED Polymarket CLOB YES-token capture in raw ledger")
    if hyperliquid_capture is None:
        raise S1PairedProjectionError(
            projection.S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING,
            "no single RAW_COMMITTED Hyperliquid l2Book capture in raw ledger")

    # Delegate ALL projection / validation to the RATIFIED runtime (no parallel formula here).
    carrier = projection.project_paired_s1_evidence(
        polymarket_evidence=_build_polymarket_evidence(polymarket_capture),
        hyperliquid_evidence=_build_hyperliquid_evidence(hyperliquid_capture))

    idempotency_key = _idempotency_key(carrier)

    # Atomic, idempotent durable append. INSERT OR IGNORE on the UNIQUE idempotency_key makes replay a
    # no-op; the projection above has already enforced every provenance/projection invariant, so no
    # partial/orphan row is possible. The destination table must pre-exist (no schema creation here).
    insert_sql = (
        "INSERT OR IGNORE INTO %s ("
        " idempotency_key, polymarket_capture_sequence, polymarket_response_body_sha256,"
        " hyperliquid_capture_sequence, hyperliquid_response_body_sha256,"
        " polymarket_timestamp_ms, hyperliquid_time_ms, event_time_delta_ms,"
        " best_bid_px, best_bid_sz, best_ask_px, best_ask_sz, projection_authority)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)" % destination_table)
    with destination_connection:
        cursor = destination_connection.execute(insert_sql, (
            idempotency_key,
            carrier.polymarket_capture_sequence, carrier.polymarket_response_body_sha256,
            carrier.hyperliquid_capture_sequence, carrier.hyperliquid_response_body_sha256,
            carrier.polymarket_timestamp_ms, carrier.hyperliquid_time_ms, carrier.event_time_delta_ms,
            str(carrier.hyperliquid_best_bid_px_decimal), str(carrier.hyperliquid_best_bid_sz_decimal),
            str(carrier.hyperliquid_best_ask_px_decimal), str(carrier.hyperliquid_best_ask_sz_decimal),
            PROJECTION_AUTHORITY))
    written = cursor.rowcount == 1

    return IngestResult(written=written, idempotency_key=idempotency_key, projection=carrier)
