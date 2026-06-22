"""raw_acquisition/public_raw_capture.py — raw-only one-shot public-data acquisition runtime.

Sole architectural source of truth:
``docs/handoff/post_phase6_2_public_source_authority_raw_capture_ledger_exact_shape_charter.md``.

One invocation issues at most one HTTP request to exactly one of three closed public, unauthenticated
source-authority variants, streams the exact response entity bytes (≤16 MiB, no decode/parse/decompress),
and either durably commits one RAW_CAPTURED row (capture + RAW_COMMITTED attempt, RV-10 reconciled, in one
local transaction) or commits exactly one mapped failure-attempt row and raises the mapped public exception.
It owns only fetch / raw-byte capture / retrieval provenance / the isolated raw ledger and terminates at
RAW_CAPTURED. It never opens, reads, imports, attaches, queries, mutates, or initializes S1; it never writes
``raw_processing_journal``; it never parses/JSON-decodes the response body; it performs no projection, S1
ingestion, scoring, outcome, calibration, scheduler, retry, cache, or capacity behavior.
"""
import asyncio
import dataclasses
import hashlib
import json
import os
import re
import sqlite3
import struct
import time

import aiohttp


# --- transport / library seams (indirection points; behavior is the real aiohttp) -----------------
_client_session = aiohttp.ClientSession
_client_timeout = aiohttp.ClientTimeout
_dummy_cookie_jar = aiohttp.DummyCookieJar


# --- pinned constants -----------------------------------------------------------------------------
_GAMMA = "POLYMARKET_GAMMA_MARKET_BY_SLUG_V1"
_CLOB = "POLYMARKET_CLOB_BOOK_BY_TOKEN_V1"
_HL = "HYPERLIQUID_META_AND_ASSET_CTXS_V1"

_HYPERLIQUID_BODY = b'{"type":"metaAndAssetCtxs"}'

_MAX_BODY_BYTES = 16 * 1024 * 1024
_CHUNK_BYTES = 65536
_U32_MAX = 0xFFFFFFFF

_CONNECT_TIMEOUT_S = 3.0
_TOTAL_TIMEOUT_S = 10.0

_SLUG_GRAMMAR = re.compile(r"^[0-9a-z][0-9a-z-]{0,254}$")
_TOKEN_GRAMMAR = re.compile(r"^[0-9]{1,80}$")
_COLLECTOR_SHA_GRAMMAR = re.compile(r"^[0-9a-f]{40}$")
_ADDRESS_REPR = re.compile(r"(?<=\bat )0x[0-9a-f]{6,}(?=>)", re.IGNORECASE)

_CATALOG_QUERY = (
    "SELECT type, name, tbl_name, sql FROM sqlite_master "
    "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name, tbl_name"
)
_PINNED_TABLES = ("raw_capture_log", "raw_fetch_attempt_log", "raw_processing_journal")


# --- the charter's exact executable DDL (byte-for-byte) -------------------------------------------
_RAW_LEDGER_DDL = """CREATE TABLE IF NOT EXISTS raw_capture_log (
    capture_sequence             INTEGER PRIMARY KEY AUTOINCREMENT,
    source_authority             TEXT    NOT NULL,
    http_method                  TEXT    NOT NULL,
    request_scheme               TEXT    NOT NULL,
    request_host                 TEXT    NOT NULL,
    request_target               TEXT    NOT NULL,
    request_body                 BLOB    NOT NULL,
    retrieval_started_epoch_ms   INTEGER NOT NULL,
    retrieval_completed_epoch_ms INTEGER NOT NULL,
    retrieval_elapsed_monotonic_ns INTEGER NOT NULL,
    clock_anomaly_evidence       INTEGER NOT NULL,
    http_status                  INTEGER NOT NULL,
    response_headers_payload     BLOB    NOT NULL,
    response_body                BLOB    NOT NULL,
    response_body_sha256         TEXT    NOT NULL,
    collector_commit_sha         TEXT    NOT NULL,

    CHECK (typeof(request_body) = 'blob'),
    CHECK (typeof(response_headers_payload) = 'blob'),
    CHECK (typeof(response_body) = 'blob'),
    CHECK (request_scheme = 'https'),
    CHECK (http_method IN ('GET','POST')),
    CHECK (retrieval_started_epoch_ms >= 0),
    CHECK (retrieval_completed_epoch_ms >= 0),
    CHECK (retrieval_elapsed_monotonic_ns >= 0),
    CHECK (clock_anomaly_evidence IN (0,1)),
    CHECK (http_status BETWEEN 100 AND 599),
    -- forensic clock law (§8): never reject a backward wall-clock; record it as anomaly evidence instead.
    CHECK (
        (retrieval_completed_epoch_ms >= retrieval_started_epoch_ms AND clock_anomaly_evidence = 0)
        OR (retrieval_completed_epoch_ms <  retrieval_started_epoch_ms AND clock_anomaly_evidence = 1)
    ),
    -- SHA shape only (actual digest equality is RV-1):
    CHECK (length(response_body_sha256) = 64 AND response_body_sha256 NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(collector_commit_sha) = 40 AND collector_commit_sha NOT GLOB '*[^0-9a-f]*'),
    -- closed source-authority <-> method/host/target/body coupling (exact GET/POST body compatibility):
    CHECK (
        (source_authority = 'POLYMARKET_GAMMA_MARKET_BY_SLUG_V1'
            AND http_method = 'GET'  AND request_host = 'gamma-api.polymarket.com'
            AND substr(request_target,1,14) = '/markets?slug=' AND length(request_target) > 14
            AND length(request_body) = 0)
        OR (source_authority = 'POLYMARKET_CLOB_BOOK_BY_TOKEN_V1'
            AND http_method = 'GET'  AND request_host = 'clob.polymarket.com'
            AND substr(request_target,1,15) = '/book?token_id=' AND length(request_target) > 15
            AND length(request_body) = 0)
        OR (source_authority = 'HYPERLIQUID_META_AND_ASSET_CTXS_V1'
            AND http_method = 'POST' AND request_host = 'api.hyperliquid.xyz'
            AND request_target = '/info'
            AND request_body = X'7b2274797065223a226d657461416e64417373657443747873227d')
    ),
    -- §3 parent key for the composite provenance FK from raw_fetch_attempt_log (trivially unique because
    -- capture_sequence is already the primary key; declared so the composite FK has a valid parent target):
    UNIQUE (capture_sequence, source_authority, request_target, collector_commit_sha)
);

CREATE TABLE IF NOT EXISTS raw_fetch_attempt_log (
    attempt_sequence             INTEGER PRIMARY KEY AUTOINCREMENT,
    source_authority             TEXT    NOT NULL,
    request_target               TEXT    NOT NULL,
    retrieval_started_epoch_ms   INTEGER NOT NULL,
    retrieval_completed_epoch_ms INTEGER NOT NULL,
    retrieval_elapsed_monotonic_ns INTEGER NOT NULL,
    clock_anomaly_evidence       INTEGER NOT NULL,
    outcome                      TEXT    NOT NULL,
    capture_sequence             INTEGER,
    failure_code                 TEXT,
    failure_payload              TEXT,
    collector_commit_sha         TEXT    NOT NULL,

    CHECK (source_authority IN (
        'POLYMARKET_GAMMA_MARKET_BY_SLUG_V1',
        'POLYMARKET_CLOB_BOOK_BY_TOKEN_V1',
        'HYPERLIQUID_META_AND_ASSET_CTXS_V1')),
    CHECK (outcome IN (
        'RAW_COMMITTED','TRANSPORT_FAILED','TIMEOUT','RESPONSE_TOO_LARGE','HTTP_PROTOCOL_FAILED')),
    CHECK (retrieval_started_epoch_ms >= 0),
    CHECK (retrieval_completed_epoch_ms >= 0),
    CHECK (retrieval_elapsed_monotonic_ns >= 0),
    CHECK (clock_anomaly_evidence IN (0,1)),
    CHECK (
        (retrieval_completed_epoch_ms >= retrieval_started_epoch_ms AND clock_anomaly_evidence = 0)
        OR (retrieval_completed_epoch_ms <  retrieval_started_epoch_ms AND clock_anomaly_evidence = 1)
    ),
    CHECK (length(collector_commit_sha) = 40 AND collector_commit_sha NOT GLOB '*[^0-9a-f]*'),
    -- outcome-conditional nullability of capture_sequence / failure_code / failure_payload:
    CHECK (
        (outcome = 'RAW_COMMITTED'
            AND capture_sequence IS NOT NULL AND failure_code IS NULL AND failure_payload IS NULL)
        OR (outcome IN ('TRANSPORT_FAILED','TIMEOUT','RESPONSE_TOO_LARGE','HTTP_PROTOCOL_FAILED')
            AND capture_sequence IS NULL AND failure_code IS NOT NULL AND failure_payload IS NOT NULL)
    ),
    -- closed outcome -> failure_code mapping (RAW_COMMITTED has NULL failure_code; failures map 1:1):
    CHECK (
        (outcome = 'RAW_COMMITTED'        AND failure_code IS NULL)
        OR (outcome = 'TRANSPORT_FAILED'     AND failure_code = 'RAW_TRANSPORT_ERROR')
        OR (outcome = 'TIMEOUT'              AND failure_code = 'RAW_TIMEOUT')
        OR (outcome = 'RESPONSE_TOO_LARGE'   AND failure_code = 'RAW_RESPONSE_TOO_LARGE')
        OR (outcome = 'HTTP_PROTOCOL_FAILED' AND failure_code = 'RAW_HTTP_PROTOCOL_ERROR')
    ),
    -- composite provenance FK: a RAW_COMMITTED attempt must reference the SAME-provenance capture row.
    -- Failure attempts carry capture_sequence NULL; under MATCH SIMPLE a composite FK with any NULL
    -- referencing column is not enforced, so failure attempts remain allowed.
    FOREIGN KEY (capture_sequence, source_authority, request_target, collector_commit_sha)
        REFERENCES raw_capture_log (capture_sequence, source_authority, request_target, collector_commit_sha)
);

-- exactly one RAW_COMMITTED attempt per captured response:
CREATE UNIQUE INDEX IF NOT EXISTS ux_attempt_committed_capture
    ON raw_fetch_attempt_log (capture_sequence)
    WHERE outcome = 'RAW_COMMITTED';

CREATE TABLE IF NOT EXISTS raw_processing_journal (
    journal_sequence     INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_sequence     INTEGER NOT NULL,
    stage                TEXT    NOT NULL,
    attempt_ordinal      INTEGER NOT NULL,
    event_kind           TEXT    NOT NULL,
    recorded_at_epoch_ms INTEGER NOT NULL,
    failure_code         TEXT,
    failure_payload      TEXT,

    CHECK (stage IN ('OPTION_B_PROJECTION','S1_INGESTION')),
    CHECK (event_kind IN (
        'STARTED','SUCCEEDED','FAILED',
        'RECONCILIATION_REQUIRED','RECONCILED_SUCCEEDED','RECONCILED_FAILED')),
    CHECK (attempt_ordinal >= 1),
    CHECK (recorded_at_epoch_ms >= 0),
    CHECK (
        (event_kind IN ('FAILED','RECONCILED_FAILED')
            AND failure_code IS NOT NULL AND failure_payload IS NOT NULL)
        OR (event_kind IN ('STARTED','SUCCEEDED','RECONCILIATION_REQUIRED','RECONCILED_SUCCEEDED')
            AND failure_code IS NULL AND failure_payload IS NULL)
    ),
    FOREIGN KEY (capture_sequence) REFERENCES raw_capture_log (capture_sequence)
);

-- journal cardinality (§9): partial UNIQUE indexes per (capture, stage, attempt):
CREATE UNIQUE INDEX IF NOT EXISTS ux_journal_started
    ON raw_processing_journal (capture_sequence, stage, attempt_ordinal)
    WHERE event_kind = 'STARTED';
CREATE UNIQUE INDEX IF NOT EXISTS ux_journal_ordinary_terminal
    ON raw_processing_journal (capture_sequence, stage, attempt_ordinal)
    WHERE event_kind IN ('SUCCEEDED','FAILED');
CREATE UNIQUE INDEX IF NOT EXISTS ux_journal_reconciliation_required
    ON raw_processing_journal (capture_sequence, stage, attempt_ordinal)
    WHERE event_kind = 'RECONCILIATION_REQUIRED';
CREATE UNIQUE INDEX IF NOT EXISTS ux_journal_reconciled_terminal
    ON raw_processing_journal (capture_sequence, stage, attempt_ordinal)
    WHERE event_kind IN ('RECONCILED_SUCCEEDED','RECONCILED_FAILED');

-- any terminal or reconciliation requires a prior STARTED for the same (capture, stage, attempt):
CREATE TRIGGER IF NOT EXISTS trg_journal_requires_started
BEFORE INSERT ON raw_processing_journal
WHEN NEW.event_kind IN
    ('SUCCEEDED','FAILED','RECONCILIATION_REQUIRED','RECONCILED_SUCCEEDED','RECONCILED_FAILED')
 AND NOT EXISTS (
    SELECT 1 FROM raw_processing_journal
    WHERE capture_sequence = NEW.capture_sequence AND stage = NEW.stage
      AND attempt_ordinal = NEW.attempt_ordinal AND event_kind = 'STARTED')
BEGIN
    SELECT RAISE(ABORT, 'raw_processing_journal: event requires a prior STARTED');
END;

-- RECONCILIATION_REQUIRED only on an unresolved STARTED (no ordinary terminal present):
CREATE TRIGGER IF NOT EXISTS trg_journal_reconreq_requires_unresolved
BEFORE INSERT ON raw_processing_journal
WHEN NEW.event_kind = 'RECONCILIATION_REQUIRED'
 AND EXISTS (
    SELECT 1 FROM raw_processing_journal
    WHERE capture_sequence = NEW.capture_sequence AND stage = NEW.stage
      AND attempt_ordinal = NEW.attempt_ordinal AND event_kind IN ('SUCCEEDED','FAILED'))
BEGIN
    SELECT RAISE(ABORT, 'raw_processing_journal: RECONCILIATION_REQUIRED forbidden after an ordinary terminal');
END;

-- reconciled terminal only after RECONCILIATION_REQUIRED:
CREATE TRIGGER IF NOT EXISTS trg_journal_reconciled_requires_reconreq
BEFORE INSERT ON raw_processing_journal
WHEN NEW.event_kind IN ('RECONCILED_SUCCEEDED','RECONCILED_FAILED')
 AND NOT EXISTS (
    SELECT 1 FROM raw_processing_journal
    WHERE capture_sequence = NEW.capture_sequence AND stage = NEW.stage
      AND attempt_ordinal = NEW.attempt_ordinal AND event_kind = 'RECONCILIATION_REQUIRED')
BEGIN
    SELECT RAISE(ABORT, 'raw_processing_journal: reconciled terminal requires prior RECONCILIATION_REQUIRED');
END;

-- nothing may follow a final reconciled terminal:
CREATE TRIGGER IF NOT EXISTS trg_journal_no_event_after_reconciled_terminal
BEFORE INSERT ON raw_processing_journal
WHEN EXISTS (
    SELECT 1 FROM raw_processing_journal
    WHERE capture_sequence = NEW.capture_sequence AND stage = NEW.stage
      AND attempt_ordinal = NEW.attempt_ordinal
      AND event_kind IN ('RECONCILED_SUCCEEDED','RECONCILED_FAILED'))
BEGIN
    SELECT RAISE(ABORT, 'raw_processing_journal: no event may follow a reconciled terminal');
END;

-- once reconciliation has begun, only a reconciled terminal may close the ordinal: an ordinary
-- SUCCEEDED/FAILED is forbidden after RECONCILIATION_REQUIRED (closes the transition hole):
CREATE TRIGGER IF NOT EXISTS trg_journal_no_ordinary_terminal_after_reconreq
BEFORE INSERT ON raw_processing_journal
WHEN NEW.event_kind IN ('SUCCEEDED','FAILED')
 AND EXISTS (
    SELECT 1 FROM raw_processing_journal
    WHERE capture_sequence = NEW.capture_sequence AND stage = NEW.stage
      AND attempt_ordinal = NEW.attempt_ordinal AND event_kind = 'RECONCILIATION_REQUIRED')
BEGIN
    SELECT RAISE(ABORT, 'raw_processing_journal: ordinary terminal forbidden after RECONCILIATION_REQUIRED');
END;

CREATE TRIGGER IF NOT EXISTS trg_raw_capture_log_no_update
BEFORE UPDATE ON raw_capture_log
BEGIN SELECT RAISE(ABORT, 'raw_capture_log is append-only: UPDATE forbidden'); END;
CREATE TRIGGER IF NOT EXISTS trg_raw_capture_log_no_delete
BEFORE DELETE ON raw_capture_log
BEGIN SELECT RAISE(ABORT, 'raw_capture_log is append-only: DELETE forbidden'); END;

CREATE TRIGGER IF NOT EXISTS trg_raw_fetch_attempt_log_no_update
BEFORE UPDATE ON raw_fetch_attempt_log
BEGIN SELECT RAISE(ABORT, 'raw_fetch_attempt_log is append-only: UPDATE forbidden'); END;
CREATE TRIGGER IF NOT EXISTS trg_raw_fetch_attempt_log_no_delete
BEFORE DELETE ON raw_fetch_attempt_log
BEGIN SELECT RAISE(ABORT, 'raw_fetch_attempt_log is append-only: DELETE forbidden'); END;

CREATE TRIGGER IF NOT EXISTS trg_raw_processing_journal_no_update
BEFORE UPDATE ON raw_processing_journal
BEGIN SELECT RAISE(ABORT, 'raw_processing_journal is append-only: UPDATE forbidden'); END;
CREATE TRIGGER IF NOT EXISTS trg_raw_processing_journal_no_delete
BEFORE DELETE ON raw_processing_journal
BEGIN SELECT RAISE(ABORT, 'raw_processing_journal is append-only: DELETE forbidden'); END;"""


# --- request variants / result carrier ------------------------------------------------------------
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PolymarketGammaMarketBySlugV1Request:
    slug: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PolymarketClobBookByTokenV1Request:
    token_id: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class HyperliquidMetaAndAssetCtxsV1Request:
    pass


PublicSourceRequest = (
    PolymarketGammaMarketBySlugV1Request
    | PolymarketClobBookByTokenV1Request
    | HyperliquidMetaAndAssetCtxsV1Request
)

_VARIANT_TYPES = (
    PolymarketGammaMarketBySlugV1Request,
    PolymarketClobBookByTokenV1Request,
    HyperliquidMetaAndAssetCtxsV1Request,
)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class RawCaptureCommitted:
    capture_sequence: int
    attempt_sequence: int
    source_authority: str
    http_status: int
    response_body_sha256: str


# --- closed exception hierarchy -------------------------------------------------------------------
class RawAcquisitionError(Exception):
    pass


class RawLedgerPreflightError(RawAcquisitionError):
    pass


class RawLedgerPathError(RawLedgerPreflightError):
    pass


class RawLedgerPragmaError(RawLedgerPreflightError):
    pass


class RawLedgerSchemaFingerprintError(RawLedgerPreflightError):
    pass


class RawLedgerReadinessError(RawLedgerPreflightError):
    pass


class RawTransportError(RawAcquisitionError):
    pass


class RawTimeoutError(RawAcquisitionError):
    pass


class RawResponseTooLargeError(RawAcquisitionError):
    pass


class RawHttpProtocolError(RawAcquisitionError):
    pass


class RawLedgerCommitError(RawAcquisitionError):
    pass


# --- clock / commit / count seams -----------------------------------------------------------------
def _epoch_ms():
    return time.time_ns() // 1_000_000


def _monotonic_ns():
    return time.monotonic_ns()


def _ledger_commit(conn):
    conn.execute("COMMIT")


def _count(conn, sql, params):
    return conn.execute(sql, params).fetchone()[0]


# --- §5.3 failure_payload exact encoding (exception-derived) ---------------------------------------
def _expected_failure_payload(exc):
    payload = {"exception_type": type(exc).__name__, "args": []}
    for arg in exc.args:
        if type(arg) is str:
            payload["args"].append({"kind": "STRING", "value": _ADDRESS_REPR.sub("<memory-address-redacted>", arg)})
        else:
            payload["args"].append({"kind": "NON_STRING", "type": type(arg).__name__})
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    # additional closed-shape / canonicality check (never sufficient provenance by itself):
    if json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"),
                  ensure_ascii=True, allow_nan=False) != text:
        raise RuntimeError("failure_payload canonicality check failed")
    return text


# --- exact ordered header encoding ----------------------------------------------------------------
def _encode_headers(raw_headers):
    if len(raw_headers) > _U32_MAX:
        raise RuntimeError("impossible header-pair count")
    out = [struct.pack(">I", len(raw_headers))]
    for name, value in raw_headers:
        if len(name) > _U32_MAX or len(value) > _U32_MAX:
            raise RuntimeError("impossible header byte length")
        out.append(struct.pack(">I", len(name)))
        out.append(name)
        out.append(struct.pack(">I", len(value)))
        out.append(value)
    return b"".join(out)


# --- request resolution ---------------------------------------------------------------------------
def _resolve_request(request):
    if type(request) is PolymarketGammaMarketBySlugV1Request:
        target = "/markets?slug=" + request.slug
        return (_GAMMA, "GET", "https", "gamma-api.polymarket.com", target, b"",
                {"Accept": "application/json"})
    if type(request) is PolymarketClobBookByTokenV1Request:
        target = "/book?token_id=" + request.token_id
        return (_CLOB, "GET", "https", "clob.polymarket.com", target, b"",
                {"Accept": "application/json"})
    target = "/info"
    return (_HL, "POST", "https", "api.hyperliquid.xyz", target, _HYPERLIQUID_BODY,
            {"Accept": "application/json", "Content-Type": "application/json"})


# --- ledger preflight (S1-isolated; empty-vs-existing; exact-shape) --------------------------------
def _reference_catalog():
    ref = sqlite3.connect(":memory:")
    try:
        ref.execute("PRAGMA foreign_keys=ON")
        ref.executescript(_RAW_LEDGER_DDL)
        catalog = ref.execute(_CATALOG_QUERY).fetchall()
        structural = {}
        for table in _PINNED_TABLES:
            structural[table] = (
                ref.execute("PRAGMA table_xinfo(%s)" % table).fetchall(),
                ref.execute("PRAGMA foreign_key_list(%s)" % table).fetchall(),
                ref.execute("PRAGMA index_list(%s)" % table).fetchall(),
            )
        return catalog, structural
    finally:
        ref.close()


def _candidate_structural(conn):
    structural = {}
    for table in _PINNED_TABLES:
        structural[table] = (
            conn.execute("PRAGMA table_xinfo(%s)" % table).fetchall(),
            conn.execute("PRAGMA foreign_key_list(%s)" % table).fetchall(),
            conn.execute("PRAGMA index_list(%s)" % table).fetchall(),
        )
    return structural


def _check_path_isolation(raw_ledger_path, s1_ledger_path):
    raw_real = os.path.realpath(raw_ledger_path)
    s1_real = os.path.realpath(s1_ledger_path)
    if raw_real == s1_real:
        raise RawLedgerPathError("raw_ledger_path and s1_ledger_path must be disjoint")
    raw_parent = os.path.realpath(os.path.dirname(raw_ledger_path) or ".")
    s1_parent = os.path.realpath(os.path.dirname(s1_ledger_path) or ".")
    if raw_parent == s1_parent and os.path.basename(raw_ledger_path) == os.path.basename(s1_ledger_path):
        raise RawLedgerPathError("raw_ledger_path and s1_ledger_path resolve to the same final component")
    if os.path.exists(raw_ledger_path) and os.path.exists(s1_ledger_path):
        a = os.stat(raw_ledger_path)
        b = os.stat(s1_ledger_path)
        if (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino):
            raise RawLedgerPathError("raw_ledger_path and s1_ledger_path are the same file")


def _preflight_open_raw_ledger(raw_ledger_path, s1_ledger_path):
    _check_path_isolation(raw_ledger_path, s1_ledger_path)
    try:
        conn = sqlite3.connect(raw_ledger_path, isolation_level=None)
    except sqlite3.Error as exc:
        raise RawLedgerPathError("raw_ledger_path is not openable") from exc
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA foreign_keys=ON")

        existing = conn.execute(_CATALOG_QUERY).fetchall()
        if len(existing) == 0:
            # FIRST_INITIALIZATION: complete pinned DDL once in one transaction.
            conn.executescript("BEGIN;\n" + _RAW_LEDGER_DDL + "\nCOMMIT;")
        # EXISTING_LEDGER runs no DDL. Both branches verify exact shape below.

        ref_catalog, ref_structural = _reference_catalog()
        if conn.execute(_CATALOG_QUERY).fetchall() != ref_catalog:
            raise RawLedgerSchemaFingerprintError("raw ledger catalog does not match the pinned schema")
        if _candidate_structural(conn) != ref_structural:
            raise RawLedgerSchemaFingerprintError("raw ledger structure does not match the pinned schema")

        # candidate-only stateful PRAGMA checks against literal required values.
        if str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower() != "wal":
            raise RawLedgerPragmaError("raw ledger journal_mode is not WAL")
        if int(conn.execute("PRAGMA synchronous").fetchone()[0]) != 2:
            raise RawLedgerPragmaError("raw ledger synchronous is not FULL")
        if int(conn.execute("PRAGMA foreign_keys").fetchone()[0]) != 1:
            raise RawLedgerPragmaError("raw ledger foreign_keys is not ON")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise RawLedgerReadinessError("raw ledger fails foreign_key_check")

        # transaction-readiness preflight.
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("ROLLBACK")
    except RawAcquisitionError:
        conn.close()
        raise
    except sqlite3.Error as exc:
        conn.close()
        raise RawLedgerReadinessError("raw ledger is not transaction-ready") from exc
    return conn


# --- ledger writes --------------------------------------------------------------------------------
_INSERT_CAPTURE = (
    "INSERT INTO raw_capture_log("
    "source_authority,http_method,request_scheme,request_host,request_target,request_body,"
    "retrieval_started_epoch_ms,retrieval_completed_epoch_ms,retrieval_elapsed_monotonic_ns,"
    "clock_anomaly_evidence,http_status,response_headers_payload,response_body,response_body_sha256,"
    "collector_commit_sha) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
)
_INSERT_ATTEMPT = (
    "INSERT INTO raw_fetch_attempt_log("
    "source_authority,request_target,retrieval_started_epoch_ms,retrieval_completed_epoch_ms,"
    "retrieval_elapsed_monotonic_ns,clock_anomaly_evidence,outcome,capture_sequence,failure_code,"
    "failure_payload,collector_commit_sha) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
)
_RV10_CAPTURE = (
    "SELECT COUNT(*) FROM raw_capture_log "
    "WHERE capture_sequence = ? AND source_authority = ? AND request_target = ? "
    "AND collector_commit_sha = ?"
)
_RV10_ATTEMPT = (
    "SELECT COUNT(*) FROM raw_fetch_attempt_log "
    "WHERE attempt_sequence = ? AND capture_sequence = ? AND source_authority = ? "
    "AND request_target = ? AND collector_commit_sha = ? AND outcome = 'RAW_COMMITTED' "
    "AND failure_code IS NULL AND failure_payload IS NULL"
)


def _rollback_quiet(conn):
    try:
        conn.execute("ROLLBACK")
    except sqlite3.Error:
        pass


def _commit_capture(conn, *, source_authority, method, scheme, host, target, body,
                    started_epoch_ms, completed_epoch_ms, elapsed_ns, anomaly, status,
                    headers_payload, body_bytes, sha, collector_commit_sha):
    conn.execute("BEGIN IMMEDIATE")
    cap_cur = conn.execute(_INSERT_CAPTURE, (
        source_authority, method, scheme, host, target, body,
        started_epoch_ms, completed_epoch_ms, elapsed_ns, anomaly, status,
        headers_payload, body_bytes, sha, collector_commit_sha))
    capture_sequence = cap_cur.lastrowid
    att_cur = conn.execute(_INSERT_ATTEMPT, (
        source_authority, target, started_epoch_ms, completed_epoch_ms, elapsed_ns, anomaly,
        "RAW_COMMITTED", capture_sequence, None, None, collector_commit_sha))
    attempt_sequence = att_cur.lastrowid
    c1 = _count(conn, _RV10_CAPTURE, (capture_sequence, source_authority, target, collector_commit_sha))
    c2 = _count(conn, _RV10_ATTEMPT,
                (attempt_sequence, capture_sequence, source_authority, target, collector_commit_sha))
    if c1 != 1 or c2 != 1:
        _rollback_quiet(conn)
        raise RawLedgerCommitError("RV-10 in-transaction reconciliation failed")
    try:
        _ledger_commit(conn)
    except sqlite3.Error as exc:
        _rollback_quiet(conn)
        raise RawLedgerCommitError("raw-capture transaction commit failed") from exc
    return RawCaptureCommitted(
        capture_sequence=capture_sequence, attempt_sequence=attempt_sequence,
        source_authority=source_authority, http_status=status, response_body_sha256=sha)


def _commit_failure_attempt(conn, *, source_authority, target, started_epoch_ms, completed_epoch_ms,
                            elapsed_ns, anomaly, collector_commit_sha, outcome, failure_code, exc):
    if elapsed_ns < 0:
        raise RuntimeError("negative monotonic delta")
    payload = _expected_failure_payload(exc)
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(_INSERT_ATTEMPT, (
        source_authority, target, started_epoch_ms, completed_epoch_ms, elapsed_ns, anomaly,
        outcome, None, failure_code, payload, collector_commit_sha))
    try:
        _ledger_commit(conn)
    except sqlite3.Error as commit_exc:
        _rollback_quiet(conn)
        raise RawLedgerCommitError("failure-attempt transaction commit failed") from commit_exc


# --- the single public async acquisition callable -------------------------------------------------
async def acquire_public_raw_capture(
    *,
    request: PublicSourceRequest,
    raw_ledger_path: str,
    s1_ledger_path: str,
    collector_commit_sha: str,
) -> RawCaptureCommitted:
    # --- input guards (exact order; all before any network I/O) ---
    if type(request) not in _VARIANT_TYPES:
        raise TypeError("request must be an exact PublicSourceRequest variant")
    if not (type(raw_ledger_path) is str and type(s1_ledger_path) is str
            and type(collector_commit_sha) is str):
        raise TypeError("raw_ledger_path, s1_ledger_path, and collector_commit_sha must be exact str")
    if (raw_ledger_path == "" or s1_ledger_path == ""
            or "\x00" in raw_ledger_path or "\x00" in s1_ledger_path):
        raise ValueError("raw_ledger_path and s1_ledger_path must be non-empty NUL-free paths")
    if _COLLECTOR_SHA_GRAMMAR.fullmatch(collector_commit_sha) is None:
        raise ValueError("collector_commit_sha must be exactly 40 lowercase hex characters")
    if type(request) is PolymarketGammaMarketBySlugV1Request:
        if _SLUG_GRAMMAR.fullmatch(request.slug) is None:
            raise ValueError("slug must match ^[0-9a-z][0-9a-z-]{0,254}$")
    elif type(request) is PolymarketClobBookByTokenV1Request:
        if _TOKEN_GRAMMAR.fullmatch(request.token_id) is None:
            raise ValueError("token_id must match ^[0-9]{1,80}$")

    source_authority, method, scheme, host, target, body, headers = _resolve_request(request)
    url = scheme + "://" + host + target

    # --- ledger preflight (S1 isolation + open + PRAGMA + init + fingerprint + FK + readiness) ---
    conn = _preflight_open_raw_ledger(raw_ledger_path, s1_ledger_path)
    try:
        timeout = _client_timeout(total=_TOTAL_TIMEOUT_S, connect=_CONNECT_TIMEOUT_S)
        session = _client_session(
            trust_env=False, cookie_jar=_dummy_cookie_jar(),
            auto_decompress=False, timeout=timeout)
        try:
            started_epoch_ms = _epoch_ms()
            started_monotonic_ns = _monotonic_ns()
            too_large = False
            status = None
            raw_headers = ()
            body_bytes = b""
            try:
                async with session.request(
                        method, url, headers=headers,
                        data=(body if body else None), allow_redirects=False) as response:
                    status = int(response.status)
                    raw_headers = tuple((bytes(n), bytes(v)) for n, v in response.raw_headers)
                    buffer = bytearray()
                    async for chunk in response.content.iter_chunked(_CHUNK_BYTES):
                        if len(buffer) + len(chunk) > _MAX_BODY_BYTES:
                            too_large = True
                            break
                        buffer += chunk
                    completed_monotonic_ns = _monotonic_ns()
                    completed_epoch_ms = _epoch_ms()
                    if not too_large:
                        body_bytes = bytes(buffer)
                    del buffer
            except asyncio.TimeoutError as exc:
                completed_monotonic_ns = _monotonic_ns()
                completed_epoch_ms = _epoch_ms()
                _commit_failure_attempt(
                    conn, source_authority=source_authority, target=target,
                    started_epoch_ms=started_epoch_ms, completed_epoch_ms=completed_epoch_ms,
                    elapsed_ns=completed_monotonic_ns - started_monotonic_ns,
                    anomaly=(1 if completed_epoch_ms < started_epoch_ms else 0),
                    collector_commit_sha=collector_commit_sha,
                    outcome="TIMEOUT", failure_code="RAW_TIMEOUT", exc=exc)
                raise RawTimeoutError("raw public fetch timed out")
            except aiohttp.ClientConnectionError as exc:
                completed_monotonic_ns = _monotonic_ns()
                completed_epoch_ms = _epoch_ms()
                _commit_failure_attempt(
                    conn, source_authority=source_authority, target=target,
                    started_epoch_ms=started_epoch_ms, completed_epoch_ms=completed_epoch_ms,
                    elapsed_ns=completed_monotonic_ns - started_monotonic_ns,
                    anomaly=(1 if completed_epoch_ms < started_epoch_ms else 0),
                    collector_commit_sha=collector_commit_sha,
                    outcome="TRANSPORT_FAILED", failure_code="RAW_TRANSPORT_ERROR", exc=exc)
                raise RawTransportError("raw public fetch transport failure")
            except aiohttp.ClientError as exc:
                completed_monotonic_ns = _monotonic_ns()
                completed_epoch_ms = _epoch_ms()
                _commit_failure_attempt(
                    conn, source_authority=source_authority, target=target,
                    started_epoch_ms=started_epoch_ms, completed_epoch_ms=completed_epoch_ms,
                    elapsed_ns=completed_monotonic_ns - started_monotonic_ns,
                    anomaly=(1 if completed_epoch_ms < started_epoch_ms else 0),
                    collector_commit_sha=collector_commit_sha,
                    outcome="HTTP_PROTOCOL_FAILED", failure_code="RAW_HTTP_PROTOCOL_ERROR", exc=exc)
                raise RawHttpProtocolError("raw public fetch protocol failure")

            if too_large:
                too_large_exc = RawResponseTooLargeError("response entity exceeds the 16 MiB cap")
                _commit_failure_attempt(
                    conn, source_authority=source_authority, target=target,
                    started_epoch_ms=started_epoch_ms, completed_epoch_ms=completed_epoch_ms,
                    elapsed_ns=completed_monotonic_ns - started_monotonic_ns,
                    anomaly=(1 if completed_epoch_ms < started_epoch_ms else 0),
                    collector_commit_sha=collector_commit_sha,
                    outcome="RESPONSE_TOO_LARGE", failure_code="RAW_RESPONSE_TOO_LARGE", exc=too_large_exc)
                raise too_large_exc

            elapsed_ns = completed_monotonic_ns - started_monotonic_ns
            if elapsed_ns < 0:
                raise RuntimeError("negative monotonic delta")
            anomaly = 1 if completed_epoch_ms < started_epoch_ms else 0
            headers_payload = _encode_headers(raw_headers)
            sha = hashlib.sha256(body_bytes).hexdigest()
            return _commit_capture(
                conn, source_authority=source_authority, method=method, scheme=scheme, host=host,
                target=target, body=body, started_epoch_ms=started_epoch_ms,
                completed_epoch_ms=completed_epoch_ms, elapsed_ns=elapsed_ns, anomaly=anomaly,
                status=status, headers_payload=headers_payload, body_bytes=body_bytes, sha=sha,
                collector_commit_sha=collector_commit_sha)
        finally:
            await session.close()
    finally:
        conn.close()
