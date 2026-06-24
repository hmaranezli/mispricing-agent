"""tests/test_live_s1_db_initialization.py — isolated Live S1 DB Initialization & Schema Provisioning.

Bu slice, RATIFIYE Live S1 DB Initialization & Schema Provisioning Boundary Charter'ına göre, YALNIZCA
caller'ın verdiği tempfile/test SQLite yolunda BOŞ, append-only, kilitli bir konteyner YARATIR. S1
append YAPMAZ, production stream AÇMAZ, writer ÇALIŞTIRMAZ, approval-ledger MUTATE ETMEZ, trade/order/
capacity ÜRETMEZ. Varsayılan/üretim DB yolu ve otomatik giriş noktası YOKTUR. Suspect/recovery
durumunda fail-closed olur ve hiçbir şeyi SİLMEZ.

Konteyner yaratmak append yetkisi DEĞİLDİR; şema sağlamak production-stream yetkisi DEĞİLDİR.
REVIEWABLE_FOR_S1_APPEND, AUTHORIZED DEĞİLDİR.

İlk RED: approval.live_s1_db_initialization yok → ImportError (eksik üretim seam'i).
"""
import ast
import inspect
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval.live_s1_db_initialization import (  # noqa: E402
    LiveS1DbInitRequest,
    LiveS1DbInitResult,
    compute_initialization_intent_digest,
    initialize_live_s1_db,
)

_EXPECTED_COLS = [
    "seq",
    "evidence_digest",
    "s1_target",
    "canonical_payload_digest",
    "approval_row_digest",
    "freshness_binding_digest",
    "immutable_snapshot_ref",
    "operator_command_id",
    "created_at_utc",
]


def _setup(tmp_path, dir_mode=0o700):
    parent = str(tmp_path / "s1_root")
    os.mkdir(parent)
    os.chmod(parent, dir_mode)
    db_path = os.path.join(parent, "s1_live.sqlite3")
    return parent, db_path


def _req(parent, db_path, **over):
    vals = dict(
        db_path=db_path,
        expected_parent_dir=parent,
        expected_owner_uid=-1,
        enforce_owner_check=False,
        expected_file_mode=0o600,
        expected_dir_mode=0o700,
        schema_version="s1_v1",
        operator_command_id="OPCMD-INIT-0001",
        allow_synchronous_extra=False,
    )
    intent_override = over.pop("initialization_intent_digest", None)
    vals.update(over)
    intent = compute_initialization_intent_digest(
        db_path=vals["db_path"],
        expected_parent_dir=vals["expected_parent_dir"],
        schema_version=vals["schema_version"],
        operator_command_id=vals["operator_command_id"],
    )
    vals["initialization_intent_digest"] = intent_override if intent_override is not None else intent
    return LiveS1DbInitRequest(**vals)


def _mode(path):
    return os.stat(path).st_mode & 0o777


# --- happy path -------------------------------------------------------------
def test_creates_empty_locked_container(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "CREATED_EMPTY_LOCKED_CONTAINER"
    assert r.created_now is True
    assert r.row_count == 0
    assert os.path.exists(db)
    assert _mode(db) == 0o600


def test_status_is_not_authorized(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status != "AUTHORIZED"


def test_zero_rows_after_init(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM s1_appends").fetchone()[0] == 0
    finally:
        con.close()


def test_journal_mode_wal_verified(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db))
    assert r.journal_mode.lower() == "wal"
    con = sqlite3.connect(db)
    try:
        assert con.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    finally:
        con.close()


def test_synchronous_full_floor_verified(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db))
    assert r.synchronous == "FULL"


def test_extra_not_silently_enabled(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db))  # allow_synchronous_extra defaults False
    assert r.synchronous == "FULL"
    assert "allow_synchronous_extra" in {f.lower() for f in LiveS1DbInitRequest.__annotations__}


# --- explicit frozen request requirements -----------------------------------
def test_missing_operator_command_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db, operator_command_id=""))
    assert r.status == "BLOCKED"
    assert r.reason == "missing_required_field"
    assert not os.path.exists(db)


def test_empty_db_path_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, ""))
    assert r.status == "BLOCKED"
    assert r.reason == "missing_required_field"


def test_missing_intent_digest_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db, initialization_intent_digest=""))
    assert r.status == "BLOCKED"
    assert r.reason == "missing_required_field"


def test_intent_digest_mismatch_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db, initialization_intent_digest="0" * 64))
    assert r.status == "BLOCKED"
    assert r.reason == "intent_digest_mismatch"
    assert not os.path.exists(db)


# --- path policy: no default / no fallback ----------------------------------
def test_path_parent_mismatch_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    # expected_parent_dir does not match dirname(db_path)
    other = str(tmp_path / "elsewhere")
    os.mkdir(other)
    os.chmod(other, 0o700)
    r = initialize_live_s1_db(_req(parent, db, expected_parent_dir=other))
    assert r.status == "BLOCKED"
    assert r.reason == "path_policy_mismatch"
    assert not os.path.exists(db)


def test_parent_dir_missing_not_autocreated(tmp_path):
    missing_parent = str(tmp_path / "does_not_exist")
    db = os.path.join(missing_parent, "s1_live.sqlite3")
    r = initialize_live_s1_db(_req(missing_parent, db))
    assert r.status == "BLOCKED"
    assert r.reason == "parent_dir_missing"
    assert not os.path.exists(missing_parent)  # must NOT auto-create


# --- permission policy ------------------------------------------------------
def test_parent_dir_mode_mismatch_fails_closed(tmp_path):
    parent, db = _setup(tmp_path, dir_mode=0o750)
    r = initialize_live_s1_db(_req(parent, db, expected_dir_mode=0o700))
    assert r.status == "BLOCKED"
    assert r.reason == "parent_dir_mode_mismatch"
    assert not os.path.exists(db)


def test_over_permissive_dir_policy_rejected(tmp_path):
    parent, db = _setup(tmp_path, dir_mode=0o777)
    r = initialize_live_s1_db(_req(parent, db, expected_dir_mode=0o777))
    assert r.status == "BLOCKED"
    assert r.reason == "over_permissive_mode_policy"


def test_over_permissive_file_policy_rejected(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db, expected_file_mode=0o666))
    assert r.status == "BLOCKED"
    assert r.reason == "over_permissive_mode_policy"
    assert not os.path.exists(db)


def test_created_file_mode_is_restrictive(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))
    assert _mode(db) == 0o600


def test_owner_match_passes(tmp_path):
    parent, db = _setup(tmp_path)
    uid = os.stat(parent).st_uid
    r = initialize_live_s1_db(_req(parent, db, enforce_owner_check=True, expected_owner_uid=uid))
    assert r.status == "CREATED_EMPTY_LOCKED_CONTAINER"


def test_owner_mismatch_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    uid = os.stat(parent).st_uid
    r = initialize_live_s1_db(_req(parent, db, enforce_owner_check=True, expected_owner_uid=uid + 99999))
    assert r.status == "BLOCKED"
    assert r.reason == "owner_mismatch"
    assert not os.path.exists(db)


# --- idempotency ------------------------------------------------------------
def test_idempotent_second_init_noop_zero_rows(tmp_path):
    parent, db = _setup(tmp_path)
    r1 = initialize_live_s1_db(_req(parent, db))
    r2 = initialize_live_s1_db(_req(parent, db))
    assert r1.created_now is True
    assert r2.status == "CREATED_EMPTY_LOCKED_CONTAINER"
    assert r2.created_now is False
    assert r2.row_count == 0


def test_idempotent_result_digest_deterministic(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))
    r2 = initialize_live_s1_db(_req(parent, db))
    r3 = initialize_live_s1_db(_req(parent, db))
    assert len(r2.initialization_result_digest) == 64
    assert r2.initialization_result_digest == r3.initialization_result_digest


# --- existing suspect / mismatched DB ---------------------------------------
def test_existing_wrong_file_mode_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))
    os.chmod(db, 0o644)
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED"
    assert r.reason == "file_mode_mismatch"


def test_existing_wrong_journal_mode_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    con = sqlite3.connect(db)
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute(
        "CREATE TABLE s1_appends (seq INTEGER PRIMARY KEY AUTOINCREMENT, evidence_digest TEXT NOT NULL, "
        "s1_target TEXT NOT NULL, canonical_payload_digest TEXT NOT NULL, approval_row_digest TEXT NOT NULL, "
        "freshness_binding_digest TEXT NOT NULL, immutable_snapshot_ref TEXT NOT NULL, "
        "operator_command_id TEXT NOT NULL, created_at_utc TEXT NOT NULL, UNIQUE(evidence_digest, s1_target))"
    )
    con.commit()
    con.close()
    os.chmod(db, 0o600)
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED"
    assert r.reason == "wrong_pragma"


def test_existing_schema_mismatch_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    con = sqlite3.connect(db)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE s1_appends (seq INTEGER PRIMARY KEY, foo TEXT)")
    con.commit()
    con.close()
    os.chmod(db, 0o600)
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED"
    assert r.reason == "schema_mismatch"


def test_existing_missing_unique_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    con = sqlite3.connect(db)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(
        "CREATE TABLE s1_appends (seq INTEGER PRIMARY KEY AUTOINCREMENT, evidence_digest TEXT NOT NULL, "
        "s1_target TEXT NOT NULL, canonical_payload_digest TEXT NOT NULL, approval_row_digest TEXT NOT NULL, "
        "freshness_binding_digest TEXT NOT NULL, immutable_snapshot_ref TEXT NOT NULL, "
        "operator_command_id TEXT NOT NULL, created_at_utc TEXT NOT NULL)"
    )
    con.commit()
    con.close()
    os.chmod(db, 0o600)
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED"
    assert r.reason == "missing_unique_constraint"


def test_existing_nonzero_rows_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))
    con = sqlite3.connect(db)
    con.execute(
        "INSERT INTO s1_appends (evidence_digest, s1_target, canonical_payload_digest, approval_row_digest, "
        "freshness_binding_digest, immutable_snapshot_ref, operator_command_id, created_at_utc) "
        "VALUES ('e','t','c','a','f','s','o','2026-01-01T00:00:00Z')"
    )
    con.commit()
    con.close()
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED"
    assert r.reason == "nonzero_rows"


def test_corrupt_nonsqlite_file_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    with open(db, "wb") as fh:
        fh.write(b"this is not a sqlite database at all")
    os.chmod(db, 0o600)
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED"
    assert r.reason == "initialization_failed"


# --- recovery: detect, never clean up ---------------------------------------
def test_hot_journal_returns_recovery_required_no_cleanup(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))
    sidecar = db + "-journal"
    with open(sidecar, "wb") as fh:
        fh.write(b"\x00hot-journal")
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED_RECOVERY_REQUIRED"
    assert r.reason == "recovery_required"
    assert os.path.exists(sidecar)


def test_orphan_wal_without_db_returns_recovery_required(tmp_path):
    parent, db = _setup(tmp_path)
    sidecar = db + "-wal"
    with open(sidecar, "wb") as fh:
        fh.write(b"\x00orphan-wal")
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED_RECOVERY_REQUIRED"
    assert os.path.exists(sidecar)
    assert not os.path.exists(db)


def test_lock_residue_returns_recovery_required_no_cleanup(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))
    sidecar = db + "-lock"
    with open(sidecar, "wb") as fh:
        fh.write(b"\x00lock")
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED_RECOVERY_REQUIRED"
    assert os.path.exists(sidecar)


# --- schema has no actionable semantics -------------------------------------
def test_no_actionable_columns_in_schema(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info('s1_appends')")]
    finally:
        con.close()
    assert cols == _EXPECTED_COLS
    for bad in ("price", "side", "order", "trade", "qty", "size", "pnl", "capacity", "notional"):
        assert not any(bad in c.lower() for c in cols), f"actionable column: {bad}"


# --- result object: frozen, passive, no authority ---------------------------
def test_result_is_frozen(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db))
    with pytest.raises(Exception):
        r.status = "AUTHORIZED"  # type: ignore[misc]


def test_result_authority_flags_false(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db))
    for flag in (
        "s1_append_authorized",
        "production_stream_authorized",
        "trading_authorized",
        "capacity_enabled",
        "wallet_authorized",
    ):
        assert getattr(r, flag) is False


def test_blocked_result_authority_flags_false(tmp_path):
    parent, db = _setup(tmp_path)
    r = initialize_live_s1_db(_req(parent, db, operator_command_id=""))
    for flag in (
        "s1_append_authorized",
        "production_stream_authorized",
        "trading_authorized",
        "capacity_enabled",
        "wallet_authorized",
    ):
        assert getattr(r, flag) is False


# --- isolation / no-surface -------------------------------------------------
def test_no_default_db_path_or_main_entrypoint():
    import approval.live_s1_db_initialization as mod

    src = inspect.getsource(mod)
    assert "__main__" not in src
    for prod in (".sqlite3\"", ".sqlite3'", "/var/", "/prod", "production.db", "/root/"):
        assert prod not in src, f"hardcoded production path token: {prod}"


def test_no_auto_start_or_trade_surface():
    import approval.live_s1_db_initialization as mod

    for name in dir(mod):
        if not callable(getattr(mod, name)):
            continue
        low = name.lower()
        for verb in (
            "schedule",
            "enqueue",
            "worker",
            "observe",
            "subscribe",
            "callback",
            "listener",
            "start_stream",
            "place_",
            "submit_order",
            "trade",
            "append_row",
        ):
            assert verb not in low, f"forbidden surface: {name}"


def test_does_not_import_writer_or_ledger():
    import approval.live_s1_db_initialization as mod

    tree = ast.parse(inspect.getsource(mod))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for n in node.names:
                imported.add(n.name)
    for forbidden in ("approval.s1_append_execution_db_writer", "approval.approval_ledger_db"):
        assert forbidden not in imported, f"must not import {forbidden}"


def test_no_network_secret_env_access_tokens():
    import approval.live_s1_db_initialization as mod

    low = inspect.getsource(mod).lower()
    for tok in ("requests", "urllib", "socket", "subprocess", "environ", "getenv", "private_key", "gpg", "yubikey", "/hsm"):
        assert tok not in low, f"forbidden access token: {tok}"


def test_imports_stdlib_only():
    import approval.live_s1_db_initialization as mod

    tree = ast.parse(inspect.getsource(mod))
    allowed_top = {"hashlib", "sqlite3", "dataclasses", "typing", "__future__", "os", "stat"}
    imported_top = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported_top.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_top.add(node.module.split(".")[0])
    assert imported_top <= allowed_top, f"unexpected imports: {imported_top - allowed_top}"


# --- Schema & Journal Unification: canonical table + shared fingerprints -----
import approval.live_s1_db_initialization as _initmod  # noqa: E402
import approval.production_s1_append_circuit as _circuitmod  # noqa: E402

_LEGACY = "s1_append" + "_log"  # construct token so the literal appears only in the assertions below


def test_legacy_table_only_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    con = sqlite3.connect(db)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(f"CREATE TABLE {_LEGACY} (seq INTEGER PRIMARY KEY AUTOINCREMENT)")
    con.commit()
    con.close()
    os.chmod(db, 0o600)
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED"
    assert r.reason == "forbidden_legacy_table"


def test_dual_table_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))  # creates canonical s1_appends
    con = sqlite3.connect(db)
    con.execute(f"CREATE TABLE {_LEGACY} (seq INTEGER PRIMARY KEY AUTOINCREMENT)")
    con.commit()
    con.close()
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED"
    assert r.reason == "forbidden_dual_table"


def test_existing_missing_triggers_fails_closed(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))
    con = sqlite3.connect(db)
    con.execute("DROP TRIGGER s1_appends_no_update")
    con.execute("DROP TRIGGER s1_appends_no_delete")
    con.commit()
    con.close()
    r = initialize_live_s1_db(_req(parent, db))
    assert r.status == "BLOCKED"
    assert r.reason == "missing_triggers"


def test_shared_canonical_schema_fingerprint(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))
    # initializer + circuit agree on ONE deterministic schema fingerprint
    assert _circuitmod.compute_container_fingerprint(db) == _initmod.canonical_schema_fingerprint()


def test_shared_canonical_journal_fingerprint(tmp_path):
    parent, db = _setup(tmp_path)
    initialize_live_s1_db(_req(parent, db))
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        assert _initmod.container_journal_fingerprint(con) == _initmod.canonical_journal_fingerprint()
    finally:
        con.close()


def test_canonical_table_is_s1_appends_and_no_legacy_in_source():
    assert _initmod.CANONICAL_TABLE == "s1_appends"
    src = inspect.getsource(_initmod)
    assert "s1_appends" in src
    assert "s1_append_log" not in src  # constructed via concatenation; literal must be absent
