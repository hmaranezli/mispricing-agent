"""RED→GREEN tests for the ratified Post-Phase 6.2 S1 Production Ingestion Adapter / Durable Writer TDD
Charter (``docs/handoff/post_phase6_2_s1_production_ingestion_adapter_durable_writer_tdd_charter.md``).

Boundary: pure, stdlib-only, zero-network. Raw-evidence inputs are temporary SQLite raw-ledger fixtures
(built in ``tmp_path`` from the ratified ``_RAW_LEDGER_DDL``); the durable destination is an in-memory
SQLite table created by the fixture (never by production code). No HTTP, no scheduler, no real ``/root``
ledger paths, no real/prod S1 DB, no raw-ledger mutation. The adapter only reuses the RATIFIED
``s1_paired_projection`` runtime; production ingestion stays BLOCKED.
"""
import inspect
import json
import sqlite3

import pytest

from phase6_2_shadow_intent import s1_paired_projection as proj
from phase6_2_shadow_intent import s1_production_ingestion_adapter as adapter
from raw_acquisition.public_raw_capture import _RAW_LEDGER_DDL, _HYPERLIQUID_L2BOOK_BTC_BODY


_COLLECTOR_SHA = "0" * 40
_POLY_TS = "1782189645718"
_HL_TIME = 1782189645000  # |1782189645718 - 1782189645000| = 718 <= 1000


def _poly_body(timestamp=_POLY_TS, include_timestamp=True):
    body = {
        "market": "0xfeed", "asset_id": proj.RATIFIED_POLYMARKET_TOKEN_ID,
        "hash": "x", "bids": [{"price": "0.5", "size": "10"}], "asks": [],
        "min_order_size": "1", "tick_size": "0.01", "neg_risk": False, "last_trade_price": "0.5",
    }
    if include_timestamp:
        body["timestamp"] = timestamp
    return json.dumps(body).encode()


def _hl_body(time_ms=_HL_TIME, levels=None):
    if levels is None:
        levels = [
            [{"px": "42000.5", "sz": "1.25", "n": 3}, {"px": "41999.0", "sz": "2.0", "n": 5}],
            [{"px": "42001.0", "sz": "0.75", "n": 2}, {"px": "42002.0", "sz": "1.0", "n": 4}],
        ]
    return json.dumps({"coin": "BTC", "time": time_ms, "levels": levels}).encode()


def _insert_capture(conn, *, source_authority, http_method, request_host, request_target,
                    request_body, response_body, response_body_sha256,
                    retrieval_started=1000, retrieval_completed=2000):
    cur = conn.execute(
        "INSERT INTO raw_capture_log ("
        " source_authority, http_method, request_scheme, request_host, request_target, request_body,"
        " retrieval_started_epoch_ms, retrieval_completed_epoch_ms, retrieval_elapsed_monotonic_ns,"
        " clock_anomaly_evidence, http_status, response_headers_payload, response_body,"
        " response_body_sha256, collector_commit_sha)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (source_authority, http_method, "https", request_host, request_target, request_body,
         retrieval_started, retrieval_completed, 1, 0, 200, b"", response_body,
         response_body_sha256, _COLLECTOR_SHA))
    capture_sequence = cur.lastrowid
    conn.execute(
        "INSERT INTO raw_fetch_attempt_log ("
        " source_authority, request_target, retrieval_started_epoch_ms, retrieval_completed_epoch_ms,"
        " retrieval_elapsed_monotonic_ns, clock_anomaly_evidence, outcome, capture_sequence,"
        " failure_code, failure_payload, collector_commit_sha)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (source_authority, request_target, retrieval_started, retrieval_completed, 1, 0,
         "RAW_COMMITTED", capture_sequence, None, None, _COLLECTOR_SHA))
    return capture_sequence


def _add_polymarket(conn, *, token_id=None, sha=None, body=None,
                    retrieval_started=1000, retrieval_completed=2000):
    token = proj.RATIFIED_POLYMARKET_TOKEN_ID if token_id is None else token_id
    return _insert_capture(
        conn, source_authority="POLYMARKET_CLOB_BOOK_BY_TOKEN_V1", http_method="GET",
        request_host="clob.polymarket.com", request_target="/book?token_id=" + token,
        request_body=b"", response_body=_poly_body() if body is None else body,
        response_body_sha256=proj.RATIFIED_POLYMARKET_CAPTURE_SHA256 if sha is None else sha,
        retrieval_started=retrieval_started, retrieval_completed=retrieval_completed)


def _add_hyperliquid(conn, *, sha=None, body=None):
    return _insert_capture(
        conn, source_authority="HYPERLIQUID_L2_BOOK_BY_COIN_V1", http_method="POST",
        request_host="api.hyperliquid.xyz", request_target="/info",
        request_body=_HYPERLIQUID_L2BOOK_BTC_BODY, response_body=_hl_body() if body is None else body,
        response_body_sha256=proj.RATIFIED_HYPERLIQUID_CAPTURE_SHA256 if sha is None else sha)


def _make_raw_ledger(tmp_path, *, polymarket=True, hyperliquid=True, poly_kw=None, hl_kw=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "raw_capture.sqlite3"
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_RAW_LEDGER_DDL)
    if polymarket:
        _add_polymarket(conn, **(poly_kw or {}))
    if hyperliquid:
        _add_hyperliquid(conn, **(hl_kw or {}))
    conn.commit()
    conn.close()
    return str(path)


_DEST_TABLE = "s1_projection_audit"
_DEST_DDL = (
    "CREATE TABLE s1_projection_audit ("
    " append_sequence INTEGER PRIMARY KEY AUTOINCREMENT,"
    " idempotency_key TEXT NOT NULL UNIQUE,"
    " polymarket_capture_sequence INTEGER NOT NULL,"
    " polymarket_response_body_sha256 TEXT NOT NULL,"
    " hyperliquid_capture_sequence INTEGER NOT NULL,"
    " hyperliquid_response_body_sha256 TEXT NOT NULL,"
    " polymarket_timestamp_ms INTEGER NOT NULL,"
    " hyperliquid_time_ms INTEGER NOT NULL,"
    " event_time_delta_ms INTEGER NOT NULL,"
    " best_bid_px TEXT NOT NULL, best_bid_sz TEXT NOT NULL,"
    " best_ask_px TEXT NOT NULL, best_ask_sz TEXT NOT NULL,"
    " projection_authority TEXT NOT NULL)"
)


def _dest_conn(create=True):
    conn = sqlite3.connect(":memory:")
    if create:
        conn.execute(_DEST_DDL)
        conn.commit()
    return conn


def _count(conn, table=_DEST_TABLE):
    return conn.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]


def _ingest(raw_ledger_path, dest_conn):
    return adapter.ingest_paired_s1_projection(
        raw_ledger_path=raw_ledger_path, destination_connection=dest_conn,
        destination_table=_DEST_TABLE)


def _reason(excinfo):
    return excinfo.value.reason


# --- happy path ----------------------------------------------------------------------------------

def test_valid_pair_ingests_one_row(tmp_path):
    ledger = _make_raw_ledger(tmp_path)
    conn = _dest_conn()
    result = _ingest(ledger, conn)
    assert result.written is True
    assert _count(conn) == 1


def test_audit_row_carries_full_provenance(tmp_path):
    ledger = _make_raw_ledger(tmp_path)
    conn = _dest_conn()
    _ingest(ledger, conn)
    row = conn.execute(
        "SELECT polymarket_response_body_sha256, hyperliquid_response_body_sha256,"
        " polymarket_capture_sequence, hyperliquid_capture_sequence FROM s1_projection_audit").fetchone()
    assert row[0] == proj.RATIFIED_POLYMARKET_CAPTURE_SHA256
    assert row[1] == proj.RATIFIED_HYPERLIQUID_CAPTURE_SHA256
    assert row[2] is not None and row[3] is not None


def test_decimals_persisted_as_exact_text_never_float(tmp_path):
    ledger = _make_raw_ledger(tmp_path)
    conn = _dest_conn()
    _ingest(ledger, conn)
    row = conn.execute(
        "SELECT best_bid_px, best_ask_px FROM s1_projection_audit").fetchone()
    assert row[0] == "42000.5"
    assert row[1] == "42001.0"
    assert type(row[0]) is str


# --- Group A: read-only raw-ledger access --------------------------------------------------------

def test_raw_ledger_opened_read_only_rejects_writes(tmp_path):
    ledger = _make_raw_ledger(tmp_path)
    ro = adapter.open_raw_ledger_readonly(ledger)
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("INSERT INTO raw_capture_log (source_authority) VALUES ('x')")
    ro.close()


def test_ingest_does_not_mutate_raw_ledger(tmp_path):
    ledger = _make_raw_ledger(tmp_path)
    before = sqlite3.connect(ledger)
    cap_before = before.execute("SELECT COUNT(*) FROM raw_capture_log").fetchone()[0]
    before.close()
    _ingest(ledger, _dest_conn())
    after = sqlite3.connect(ledger)
    cap_after = after.execute("SELECT COUNT(*) FROM raw_capture_log").fetchone()[0]
    after.close()
    assert cap_before == cap_after == 2


def test_retrieval_time_never_substitutes_source_event_time(tmp_path):
    # retrieval_completed is far from $.timestamp; the projection must use the source field only.
    ledger = _make_raw_ledger(
        tmp_path, poly_kw={"retrieval_started": 1, "retrieval_completed": 999_999_999})
    result = _ingest(ledger, _dest_conn())
    assert result.projection.polymarket_timestamp_ms == int(_POLY_TS)


# --- Group B: adapter pairing --------------------------------------------------------------------

def test_lone_hyperliquid_fails_closed(tmp_path):
    ledger = _make_raw_ledger(tmp_path, polymarket=False)
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _ingest(ledger, _dest_conn())
    assert _reason(e) == "S1_PAIR_POLYMARKET_EVIDENCE_MISSING"


def test_lone_polymarket_fails_closed(tmp_path):
    ledger = _make_raw_ledger(tmp_path, hyperliquid=False)
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _ingest(ledger, _dest_conn())
    assert _reason(e) == "S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING"


def test_wrong_token_id_fails_closed(tmp_path):
    ledger = _make_raw_ledger(tmp_path, poly_kw={"token_id": "999"})
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _ingest(ledger, _dest_conn())
    assert _reason(e) == "S1_PAIR_POLYMARKET_EVIDENCE_MISSING"


def test_wrong_coin_fails_closed(tmp_path):
    bad = json.dumps({"coin": "ETH", "time": _HL_TIME, "levels": [
        [{"px": "1", "sz": "1", "n": 1}], [{"px": "2", "sz": "1", "n": 1}]]}).encode()
    ledger = _make_raw_ledger(tmp_path, hl_kw={"body": bad})
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _ingest(ledger, _dest_conn())
    assert _reason(e) == "S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING"


def test_missing_polymarket_timestamp_fails_closed(tmp_path):
    ledger = _make_raw_ledger(tmp_path, poly_kw={"body": _poly_body(include_timestamp=False)})
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _ingest(ledger, _dest_conn())
    assert _reason(e) == "S1_POLYMARKET_TIMESTAMP_MISSING"


def test_sha_mismatch_fails_closed(tmp_path):
    ledger = _make_raw_ledger(tmp_path, poly_kw={"sha": "0" * 64})
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _ingest(ledger, _dest_conn())
    assert _reason(e) == "S1_PROVENANCE_SHA_MISMATCH"


def test_adapter_delegates_to_ratified_projection_runtime(tmp_path, monkeypatch):
    calls = {"n": 0}
    original = proj.project_paired_s1_evidence

    def spy(**kwargs):
        calls["n"] += 1
        return original(**kwargs)

    monkeypatch.setattr(proj, "project_paired_s1_evidence", spy)
    _ingest(_make_raw_ledger(tmp_path), _dest_conn())
    assert calls["n"] == 1


# --- Group E: failure-surface literals -----------------------------------------------------------

def test_delta_exceeds_1000_fails_closed(tmp_path):
    ledger = _make_raw_ledger(tmp_path, hl_kw={"body": _hl_body(time_ms=int(_POLY_TS) - 1001)})
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _ingest(ledger, _dest_conn())
    assert _reason(e) == "S1_TIME_DELTA_EXCEEDS_1000_MS"


def test_float_px_fails_closed(tmp_path):
    bad = _hl_body(levels=[
        [{"px": 42000.5, "sz": "1.25", "n": 3}], [{"px": "42001.0", "sz": "0.75", "n": 2}]])
    ledger = _make_raw_ledger(tmp_path, hl_kw={"body": bad})
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _ingest(ledger, _dest_conn())
    assert _reason(e) == "S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED"


def test_malformed_levels_fails_closed(tmp_path):
    bad = json.dumps({"coin": "BTC", "time": _HL_TIME, "levels": [
        [{"px": "42000.5", "sz": "1.25", "n": 3}]]}).encode()
    ledger = _make_raw_ledger(tmp_path, hl_kw={"body": bad})
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _ingest(ledger, _dest_conn())
    assert _reason(e) == "S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED"


# --- Group C: durable writer boundary ------------------------------------------------------------

def test_writer_does_not_create_schema(tmp_path):
    ledger = _make_raw_ledger(tmp_path)
    conn = _dest_conn(create=False)  # destination table intentionally absent
    with pytest.raises(sqlite3.OperationalError):
        _ingest(ledger, conn)
    # production code must not have created the table
    names = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert _DEST_TABLE not in names


def test_no_orphan_row_all_provenance_present(tmp_path):
    ledger = _make_raw_ledger(tmp_path)
    conn = _dest_conn()
    _ingest(ledger, conn)
    row = conn.execute(
        "SELECT polymarket_capture_sequence, polymarket_response_body_sha256,"
        " hyperliquid_capture_sequence, hyperliquid_response_body_sha256, idempotency_key"
        " FROM s1_projection_audit").fetchone()
    assert all(value not in (None, "") for value in row)


def test_rowid_is_not_domain_identity(tmp_path):
    # replay must not create a second row even though autoincrement rowid would differ.
    ledger = _make_raw_ledger(tmp_path)
    conn = _dest_conn()
    _ingest(ledger, conn)
    _ingest(ledger, conn)
    assert _count(conn) == 1


# --- Group D: idempotency / replay ---------------------------------------------------------------

def test_replay_is_noop_not_duplicate(tmp_path):
    ledger = _make_raw_ledger(tmp_path)
    conn = _dest_conn()
    first = _ingest(ledger, conn)
    second = _ingest(ledger, conn)
    assert first.written is True
    assert second.written is False
    assert _count(conn) == 1


def test_idempotency_key_is_deterministic_from_both_identities(tmp_path):
    key_a = _ingest(_make_raw_ledger(tmp_path / "a", ), _dest_conn()).idempotency_key
    key_b = _ingest(_make_raw_ledger(tmp_path / "b"), _dest_conn()).idempotency_key
    assert key_a == key_b  # same source identities -> same key, independent of ledger/rowid
    assert proj.RATIFIED_POLYMARKET_CAPTURE_SHA256 != key_a  # derived, not a raw passthrough


# --- Group G: transaction / atomicity ------------------------------------------------------------

def test_validation_failure_leaves_no_row(tmp_path):
    ledger = _make_raw_ledger(tmp_path, poly_kw={"sha": "0" * 64})
    conn = _dest_conn()
    with pytest.raises(proj.S1PairedProjectionError):
        _ingest(ledger, conn)
    assert _count(conn) == 0


def test_no_commit_before_invariants_pass(tmp_path):
    ledger = _make_raw_ledger(tmp_path, hl_kw={"body": _hl_body(time_ms=int(_POLY_TS) - 1001)})
    conn = _dest_conn()
    with pytest.raises(proj.S1PairedProjectionError):
        _ingest(ledger, conn)
    assert _count(conn) == 0


# --- Group F: no-network / no-scheduler / no-actionability (static) ------------------------------

def test_adapter_has_no_network_or_scheduler_imports():
    # Inspect actual imports via AST (not docstring prose, which legitimately names what the adapter
    # does NOT do). No network / scheduler / concurrency module may be imported.
    import ast

    tree = ast.parse(inspect.getsource(adapter))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                imported_roots.add(node.module.split(".")[0])
    forbidden = {
        "socket", "http", "urllib", "requests", "aiohttp", "asyncio", "httpx",
        "threading", "sched", "subprocess", "multiprocessing", "signal", "schedule",
    }
    assert imported_roots.isdisjoint(forbidden)
    # also no sleep / cron-style call sites anywhere in the executable body
    src = inspect.getsource(adapter)
    for forbidden_call in ("time.sleep", "sleep(", "crontab", "BackgroundScheduler"):
        assert forbidden_call not in src


def test_adapter_exposes_no_scheduler_or_loop_entrypoint():
    for banned in ("main", "run_forever", "schedule", "poll", "loop", "daemon", "collect"):
        assert not hasattr(adapter, banned)
