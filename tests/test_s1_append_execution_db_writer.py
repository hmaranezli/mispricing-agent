"""tests/test_s1_append_execution_db_writer.py — isolated S1 Append Execution & DB Writer (TDD).

Bu slice, RATIFIYE S1 Append Execution & DB Writer Boundary Charter'ına göre, YALNIZCA caller'ın
verdiği tempfile/test SQLite yoluna yazan, izole bir fiziksel append yazıcısıdır. PRODUCTION S1
append YAPMAZ, canlı S1 DB / production stream YARATMAZ, approval-ledger MUTATE ETMEZ, trade/order/
capacity ÜRETMEZ. Hiçbir varsayılan/üretim DB yolu ve hiçbir otomatik giriş noktası yoktur.

Freshness, çıplak bir caller boolean'ı DEĞİL; immutable snapshot ref + digest'lere bağlı bir
freshness_binding_digest'tir. REVIEWABLE_FOR_S1_APPEND, AUTHORIZED DEĞİLDİR.

İlk RED: approval.s1_append_execution_db_writer yok → ImportError (eksik üretim seam'i).
"""
import ast
import inspect
import os
import sqlite3
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval.s1_append_execution_db_writer import (  # noqa: E402
    S1AppendRequest,
    S1AppendResult,
    compute_freshness_binding_digest,
    execute_s1_append,
    init_s1_append_db,
)

_E = "e" * 64  # evidence_digest
_C = "c" * 64  # canonical_payload_digest
_A = "a" * 64  # approval_row_digest
_TARGET = "s1_stream_btc_15m_window_0001"
_SNAP = "snapshot_ref::frozen::seq=7752::digest=" + ("d" * 16)
_CMD = "operator_command::human_operator_001::id=OPCMD-0001"


def _valid_request(**over) -> S1AppendRequest:
    base = dict(
        decision_status="REVIEWABLE_FOR_S1_APPEND",
        evidence_digest=over.get("evidence_digest", _E),
        s1_target=over.get("s1_target", _TARGET),
        canonical_payload_digest=over.get("canonical_payload_digest", _C),
        approval_row_digest=over.get("approval_row_digest", _A),
        immutable_snapshot_ref=over.get("immutable_snapshot_ref", _SNAP),
        operator_command_id=over.get("operator_command_id", _CMD),
    )
    binding = compute_freshness_binding_digest(
        immutable_snapshot_ref=base["immutable_snapshot_ref"],
        evidence_digest=base["evidence_digest"],
        s1_target=base["s1_target"],
        canonical_payload_digest=base["canonical_payload_digest"],
        approval_row_digest=base["approval_row_digest"],
    )
    kw = dict(
        decision_status=base["decision_status"],
        evidence_digest=base["evidence_digest"],
        s1_target=base["s1_target"],
        canonical_payload_digest=base["canonical_payload_digest"],
        approval_row_digest=base["approval_row_digest"],
        freshness_binding_digest=binding,
        immutable_snapshot_ref=base["immutable_snapshot_ref"],
        operator_command_id=base["operator_command_id"],
    )
    # explicit overrides for the listed dataclass fields (e.g., to break a binding)
    for k in ("decision_status", "freshness_binding_digest"):
        if k in over:
            kw[k] = over[k]
    return S1AppendRequest(**kw)


def _db(tmp_path):
    p = str(tmp_path / "s1_append_test.sqlite3")
    init_s1_append_db(p)
    return p


def _rows(db_path):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return con.execute("SELECT evidence_digest, s1_target FROM s1_append_log").fetchall()
    finally:
        con.close()


# --- happy path -------------------------------------------------------------
def test_valid_request_appends_exactly_one(tmp_path):
    db = _db(tmp_path)
    r = execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    assert r.status == "APPENDED"
    assert r.append_seq == 1
    assert _rows(db) == [(_E, _TARGET)]


def test_writer_writes_only_exact_reviewed_target(tmp_path):
    db = _db(tmp_path)
    execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    assert _rows(db) == [(_E, _TARGET)]


# --- explicit frozen request requirements -----------------------------------
def test_missing_operator_command_fails_closed(tmp_path):
    db = _db(tmp_path)
    r = execute_s1_append(db, request=_valid_request(operator_command_id=""), accepted_snapshot_ref=_SNAP)
    assert r.status == "BLOCKED"
    assert r.reason == "missing_required_field"
    assert _rows(db) == []


def test_missing_evidence_digest_fails_closed(tmp_path):
    db = _db(tmp_path)
    r = execute_s1_append(db, request=_valid_request(evidence_digest=""), accepted_snapshot_ref=_SNAP)
    assert r.status == "BLOCKED"
    assert r.reason == "missing_required_field"


# --- REVIEWABLE is not AUTHORIZED -------------------------------------------
def test_authorized_status_rejected(tmp_path):
    db = _db(tmp_path)
    r = execute_s1_append(db, request=_valid_request(decision_status="AUTHORIZED"), accepted_snapshot_ref=_SNAP)
    assert r.status == "BLOCKED"
    assert r.reason == "decision_treated_as_authorized"
    assert _rows(db) == []


def test_non_reviewable_status_rejected(tmp_path):
    db = _db(tmp_path)
    r = execute_s1_append(db, request=_valid_request(decision_status="BLOCKED"), accepted_snapshot_ref=_SNAP)
    assert r.status == "BLOCKED"
    assert r.reason == "decision_not_reviewable"


# --- freshness: bound to immutable evidence, never a bare boolean ------------
def test_no_bare_boolean_freshness_field():
    names = {f.lower() for f in S1AppendRequest.__annotations__}
    for bad in ("is_fresh", "fresh_flag", "freshness_bool", "fresh"):
        assert bad not in names, f"bare-boolean freshness field present: {bad}"
    assert "freshness_binding_digest" in names
    assert "immutable_snapshot_ref" in names


def test_freshness_binding_mismatch_fails_closed(tmp_path):
    db = _db(tmp_path)
    # tamper canonical digest WITHOUT recomputing the binding
    req = _valid_request()
    bad = S1AppendRequest(
        decision_status=req.decision_status,
        evidence_digest=req.evidence_digest,
        s1_target=req.s1_target,
        canonical_payload_digest="f" * 64,
        approval_row_digest=req.approval_row_digest,
        freshness_binding_digest=req.freshness_binding_digest,
        immutable_snapshot_ref=req.immutable_snapshot_ref,
        operator_command_id=req.operator_command_id,
    )
    r = execute_s1_append(db, request=bad, accepted_snapshot_ref=_SNAP)
    assert r.status == "BLOCKED"
    assert r.reason == "freshness_binding_mismatch"
    assert _rows(db) == []


def test_target_mismatch_fails_closed(tmp_path):
    db = _db(tmp_path)
    req = _valid_request()
    bad = S1AppendRequest(
        decision_status=req.decision_status,
        evidence_digest=req.evidence_digest,
        s1_target="s1_stream_other_target",
        canonical_payload_digest=req.canonical_payload_digest,
        approval_row_digest=req.approval_row_digest,
        freshness_binding_digest=req.freshness_binding_digest,
        immutable_snapshot_ref=req.immutable_snapshot_ref,
        operator_command_id=req.operator_command_id,
    )
    r = execute_s1_append(db, request=bad, accepted_snapshot_ref=_SNAP)
    assert r.status == "BLOCKED"
    assert r.reason == "freshness_binding_mismatch"
    assert _rows(db) == []


def test_approval_row_mismatch_fails_closed(tmp_path):
    db = _db(tmp_path)
    req = _valid_request()
    bad = S1AppendRequest(
        decision_status=req.decision_status,
        evidence_digest=req.evidence_digest,
        s1_target=req.s1_target,
        canonical_payload_digest=req.canonical_payload_digest,
        approval_row_digest="0" * 64,
        freshness_binding_digest=req.freshness_binding_digest,
        immutable_snapshot_ref=req.immutable_snapshot_ref,
        operator_command_id=req.operator_command_id,
    )
    r = execute_s1_append(db, request=bad, accepted_snapshot_ref=_SNAP)
    assert r.status == "BLOCKED"
    assert r.reason == "freshness_binding_mismatch"


def test_stale_or_unbound_snapshot_fails_closed(tmp_path):
    db = _db(tmp_path)
    r = execute_s1_append(
        db, request=_valid_request(), accepted_snapshot_ref="snapshot_ref::different::stale"
    )
    assert r.status == "BLOCKED"
    assert r.reason == "stale_or_unbound_freshness"
    assert _rows(db) == []


# --- single-flight guard (exists, but not the only protection) ---------------
def test_single_flight_lock_unavailable_fails_closed(tmp_path):
    db = _db(tmp_path)
    held = threading.Lock()
    held.acquire()
    try:
        r = execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP, single_flight=held)
        assert r.status == "BLOCKED"
        assert r.reason == "race_lock_unavailable"
        assert _rows(db) == []
    finally:
        held.release()


def test_unique_constraint_blocks_even_when_lock_grants(tmp_path):
    # fresh ungated lock each call → only the schema UNIQUE constraint protects
    db = _db(tmp_path)
    r1 = execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    r2 = execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    assert r1.status == "APPENDED"
    assert r2.status == "BLOCKED_DUPLICATE"
    assert len(_rows(db)) == 1


# --- idempotency / replay ----------------------------------------------------
def test_replay_writes_zero_additional_rows(tmp_path):
    db = _db(tmp_path)
    execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    before = len(_rows(db))
    for _ in range(5):
        r = execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
        assert r.status == "BLOCKED_DUPLICATE"
    assert len(_rows(db)) == before == 1


def test_same_digest_different_target_allowed(tmp_path):
    # idempotency key is (evidence_digest, s1_target); a different target is a different row
    db = _db(tmp_path)
    execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    other_snap = _SNAP  # same snapshot, different target → rebind via helper in _valid_request
    r = execute_s1_append(
        db, request=_valid_request(s1_target="s1_stream_eth_15m_window_0001"),
        accepted_snapshot_ref=other_snap,
    )
    assert r.status == "APPENDED"
    assert len(_rows(db)) == 2


# --- recovery: detect, never clean up ---------------------------------------
def test_hot_journal_returns_recovery_required_no_cleanup(tmp_path):
    db = _db(tmp_path)
    sidecar = db + "-journal"
    with open(sidecar, "wb") as fh:
        fh.write(b"\x00orphan-hot-journal")
    r = execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    assert r.status == "BLOCKED_RECOVERY_REQUIRED"
    assert r.reason == "recovery_required"
    assert os.path.exists(sidecar), "recovery path must NOT delete the journal"
    assert _rows(db) == []


def test_orphan_wal_returns_recovery_required(tmp_path):
    db = _db(tmp_path)
    sidecar = db + "-wal"
    with open(sidecar, "wb") as fh:
        fh.write(b"\x00orphan-wal")
    r = execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    assert r.status == "BLOCKED_RECOVERY_REQUIRED"
    assert os.path.exists(sidecar)


def test_lock_residue_returns_recovery_required(tmp_path):
    db = _db(tmp_path)
    sidecar = db + "-shm"
    with open(sidecar, "wb") as fh:
        fh.write(b"\x00orphan-shm")
    r = execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    assert r.status == "BLOCKED_RECOVERY_REQUIRED"
    assert os.path.exists(sidecar)


# --- exceptions / atomicity --------------------------------------------------
def test_connection_error_fails_closed(tmp_path):
    # a directory path cannot be opened as a sqlite db → fail closed, no authority
    bad_dir = str(tmp_path / "i_am_a_dir")
    os.mkdir(bad_dir)
    r = execute_s1_append(bad_dir, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    assert r.status == "BLOCKED"
    assert r.reason == "write_failed"
    assert r.production_s1_append_authorized is False


def test_duplicate_leaves_no_partial_row(tmp_path):
    db = _db(tmp_path)
    execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    assert len(_rows(db)) == 1  # rollback left exactly one committed row


def test_concurrent_threads_exactly_one_append(tmp_path):
    db = _db(tmp_path)
    lock = threading.Lock()
    results = []
    barrier = threading.Barrier(8)

    def worker():
        barrier.wait()
        results.append(execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP, single_flight=lock))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    appended = [x for x in results if x.status == "APPENDED"]
    assert len(appended) == 1
    assert len(_rows(db)) == 1
    for x in results:
        if x.status != "APPENDED":
            assert x.status in ("BLOCKED_DUPLICATE", "BLOCKED")


# --- result object: frozen, passive, no authority ---------------------------
def test_result_is_frozen(tmp_path):
    db = _db(tmp_path)
    r = execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    with pytest.raises(Exception):
        r.status = "APPENDED_AND_AUTHORIZED"  # type: ignore[misc]


def test_result_authority_flags_false(tmp_path):
    db = _db(tmp_path)
    r = execute_s1_append(db, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    for flag in (
        "production_s1_append_authorized",
        "production_stream_authorized",
        "trading_authorized",
        "capacity_enabled",
        "wallet_authorized",
    ):
        assert getattr(r, flag) is False


def test_blocked_results_carry_authority_false(tmp_path):
    db = _db(tmp_path)
    blocked = execute_s1_append(db, request=_valid_request(decision_status="AUTHORIZED"), accepted_snapshot_ref=_SNAP)
    for flag in (
        "production_s1_append_authorized",
        "production_stream_authorized",
        "trading_authorized",
        "capacity_enabled",
        "wallet_authorized",
    ):
        assert getattr(blocked, flag) is False


def test_result_digest_deterministic(tmp_path):
    db1 = _db(tmp_path / "a") if False else str(tmp_path / "a.sqlite3")
    db2 = str(tmp_path / "b.sqlite3")
    init_s1_append_db(db1)
    init_s1_append_db(db2)
    r1 = execute_s1_append(db1, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    r2 = execute_s1_append(db2, request=_valid_request(), accepted_snapshot_ref=_SNAP)
    assert len(r1.result_digest) == 64
    assert r1.result_digest == r2.result_digest


# --- no auto-promotion / no production surface ------------------------------
def test_no_default_db_path_or_main_entrypoint():
    import approval.s1_append_execution_db_writer as mod

    src = inspect.getsource(mod)
    assert '__main__' not in src, "no auto-run entrypoint allowed"
    for prod in (".sqlite3\"", ".sqlite3'", "/var/", "/prod", "production.db", "s1_prod"):
        assert prod not in src, f"hardcoded production path token: {prod}"


def test_no_auto_promotion_or_trade_surface():
    import approval.s1_append_execution_db_writer as mod

    for name in dir(mod):
        if not callable(getattr(mod, name)):
            continue
        low = name.lower()
        for verb in (
            "schedule",
            "enqueue",
            "queue_",
            "worker",
            "observe",
            "subscribe",
            "callback",
            "on_append",
            "place_",
            "submit_order",
            "send_order",
            "trade",
            "stream_",
            "start_stream",
            "set_capacity",
        ):
            assert verb not in low, f"forbidden surface: {name}"


def test_no_network_secret_env_access_tokens():
    import approval.s1_append_execution_db_writer as mod

    low = inspect.getsource(mod).lower()
    # real access vectors only; "wallet_authorized" is a REQUIRED no-authority flag, not a vector —
    # the stdlib-only import allowlist is the actual guarantee that no wallet/key module is reachable.
    for tok in ("requests", "urllib", "socket", "subprocess", "environ", "getenv", "private_key", "gpg", "yubikey", "/hsm"):
        assert tok not in low, f"forbidden access token: {tok}"


def test_imports_stdlib_only():
    import approval.s1_append_execution_db_writer as mod

    tree = ast.parse(inspect.getsource(mod))
    allowed_top = {"hashlib", "sqlite3", "dataclasses", "typing", "__future__", "os", "threading"}
    imported_top = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported_top.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_top.add(node.module.split(".")[0])
    assert imported_top <= allowed_top, f"unexpected imports: {imported_top - allowed_top}"
