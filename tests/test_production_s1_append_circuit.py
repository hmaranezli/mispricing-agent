"""tests/test_production_s1_append_circuit.py — isolated Production S1 Append Execution Wiring/Circuit.

Bu slice, RATIFIYE Production S1 Append Execution Wiring/Circuit Boundary Charter'ına göre, ÜÇ ratifiye
pasif modülü (karar / initializer / writer) caller'ın verdiği pytest tmp_path SQLite konteynerleri
üzerinde KOMPOZE eden, kütüphane-içi bir devredir. CLI/REST/network/auth/ingress/daemon/scheduler
YOKTUR. Production append/stream YAPMAZ, üretim DB yolu KULLANMAZ, approval-ledger MUTATE ETMEZ.

wiring ≠ execution. REVIEWABLE_FOR_S1_APPEND ≠ AUTHORIZED. CREATED_EMPTY_LOCKED_CONTAINER ≠ AUTHORIZED.
Başarılı test-kapsamı sonucu APPEND_RECORDED_IN_TEST_CONTAINER olabilir; ASLA PRODUCTION_APPEND_AUTHORIZED
değildir. Tüm üretim yetki bayrakları False.

İlk RED: approval.production_s1_append_circuit yok → ImportError (eksik üretim seam'i).
"""
import ast
import dataclasses
import inspect
import os
import sqlite3
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval.live_s1_db_initialization import (  # noqa: E402
    LiveS1DbInitRequest,
    compute_initialization_intent_digest,
    initialize_live_s1_db,
)
from approval.s1_append_authorization_decision import (  # noqa: E402
    S1AppendEvidenceSnapshot,
    evaluate_s1_append_authorization,
)
from approval.s1_append_execution_db_writer import compute_freshness_binding_digest  # noqa: E402
from approval.production_s1_append_circuit import (  # noqa: E402
    S1AppendCircuitCommand,
    S1AppendCircuitResult,
    compute_container_fingerprint,
    compute_writer_request_digest,
    run_production_s1_append_circuit,
)

_DEC = "a" * 64
_REV = "b" * 64
_EVI = "e" * 64
_CAN = "c" * 64
_APR = "d" * 64
_SNAP = "snap::frozen::seq=7752"
_TGT = "s1_btc_15m_window_0001"
_OPID = "OPCMD-APPEND-0001"
_CREATED = "2026-06-19T00:00:00Z"


def _reviewable_decision(**over):
    kw = dict(
        approval_ledger_row_present=True,
        approval_row_append_only=True,
        canonical_payload_digest=_DEC,
        displayed_payload_digest=_DEC,
        signed_payload_digest=_DEC,
        approval_row_digest=_DEC,
        review_package_digest=_REV,
        review_package_digest_expected=_REV,
        matrix_state="REVIEWABLE",
        signature_present=True,
        signature_verifier_passed=True,
        preflight_allowed=True,
        payload_freshness_state="FRESH",
        signature_freshness_state="FRESH",
        canonical_payload_binding_present=True,
        operator_identity="human_operator_001",
        signer_identity="human_operator_001",
        signer_fingerprint_known=True,
        s1_target_known=True,
        s1_target_evidence_present=True,
        single_flight_lock_held=True,
        verification_interrupted=False,
        partial_transaction_marker=False,
        duplicate_evidence=False,
        replay_attempt=False,
    )
    kw.update(over)
    return evaluate_s1_append_authorization(S1AppendEvidenceSnapshot(**kw))


def _init_container(tmp_path):
    parent = str(tmp_path / "s1root")
    os.mkdir(parent)
    os.chmod(parent, 0o700)
    db = os.path.join(parent, "s1_live.sqlite3")
    intent = compute_initialization_intent_digest(
        db_path=db, expected_parent_dir=parent, schema_version="s1_v1", operator_command_id="OPCMD-INIT-1"
    )
    req = LiveS1DbInitRequest(
        db_path=db,
        expected_parent_dir=parent,
        expected_owner_uid=-1,
        enforce_owner_check=False,
        expected_file_mode=0o600,
        expected_dir_mode=0o700,
        schema_version="s1_v1",
        operator_command_id="OPCMD-INIT-1",
        initialization_intent_digest=intent,
        allow_synchronous_extra=False,
    )
    res = initialize_live_s1_db(req)
    assert res.status == "CREATED_EMPTY_LOCKED_CONTAINER"
    return parent, db, req, res


def _valid(tmp_path):
    parent, db, ireq, ires = _init_container(tmp_path)
    dec = _reviewable_decision()
    fresh = compute_freshness_binding_digest(
        immutable_snapshot_ref=_SNAP, evidence_digest=_EVI, s1_target=_TGT,
        canonical_payload_digest=_CAN, approval_row_digest=_APR,
    )
    wrd = compute_writer_request_digest(
        decision_status="REVIEWABLE_FOR_S1_APPEND",
        evidence_digest=_EVI, s1_target=_TGT, canonical_payload_digest=_CAN,
        approval_row_digest=_APR, freshness_binding_digest=fresh,
        immutable_snapshot_ref=_SNAP, operator_command_id=_OPID, created_at_utc=_CREATED,
    )
    fp = compute_container_fingerprint(db)
    cmd = S1AppendCircuitCommand(
        operator_command_id=_OPID,
        db_path=db,
        s1_target=_TGT,
        evidence_digest=_EVI,
        canonical_payload_digest=_CAN,
        approval_row_digest=_APR,
        freshness_binding_digest=fresh,
        immutable_snapshot_ref=_SNAP,
        created_at_utc=_CREATED,
        decision_result_digest=dec.evidence_digest,
        initializer_result_digest=ires.initialization_result_digest,
        writer_request_digest=wrd,
        schema_version="s1_v1",
        expected_container_fingerprint=fp,
        expected_pre_append_row_count=0,
        external_trigger="",
        auth_not_implemented_and_required_for_any_external_trigger=True,
    )
    return dict(parent=parent, db=db, ireq=ireq, ires=ires, dec=dec, cmd=cmd)


def _run(ctx, **cmd_over):
    cmd = dataclasses.replace(ctx["cmd"], **cmd_over) if cmd_over else ctx["cmd"]
    return run_production_s1_append_circuit(
        command=cmd, decision_result=ctx["dec"], initializer_request=ctx["ireq"], initializer_result=ctx["ires"]
    )


def _log_rows(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        t = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='s1_appends'").fetchone()
        if not t:
            return []
        return con.execute("SELECT evidence_digest, s1_target FROM s1_appends").fetchall()
    finally:
        con.close()


# --- happy path -------------------------------------------------------------
def test_success_records_in_test_container_only(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx)
    assert r.status == "APPEND_RECORDED_IN_TEST_CONTAINER"
    assert r.status != "PRODUCTION_APPEND_AUTHORIZED"
    assert r.append_seq >= 1
    assert _log_rows(ctx["db"]) == [(_EVI, _TGT)]


def test_success_authority_flags_false(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx)
    for flag in (
        "production_s1_append_authorized",
        "production_stream_authorized",
        "trading_authorized",
        "capacity_enabled",
        "wallet_authorized",
    ):
        assert getattr(r, flag) is False


# --- explicit command requirement / auth-ingress deferral -------------------
def test_missing_operator_command_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, operator_command_id="")
    assert r.status == "BLOCKED"
    assert r.reason == "missing_required_field"
    assert _log_rows(ctx["db"]) == []


def test_auth_flag_false_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, auth_not_implemented_and_required_for_any_external_trigger=False)
    assert r.status == "BLOCKED"
    assert r.reason == "auth_required_not_implemented"


def test_external_trigger_field_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, external_trigger="http://ingress/append")
    assert r.status == "BLOCKED"
    assert r.reason == "external_ingress_forbidden"
    assert _log_rows(ctx["db"]) == []


# --- component-state gating -------------------------------------------------
def test_decision_not_reviewable_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    blocked_dec = _reviewable_decision(matrix_state="BLOCKED_INCOMPLETE")
    assert blocked_dec.status == "BLOCKED"
    r = run_production_s1_append_circuit(
        command=ctx["cmd"], decision_result=blocked_dec, initializer_request=ctx["ireq"], initializer_result=ctx["ires"]
    )
    assert r.status == "BLOCKED"
    assert r.reason == "decision_not_reviewable"


def test_container_not_created_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    bad_ires = dataclasses.replace(ctx["ires"], status="BLOCKED")
    r = run_production_s1_append_circuit(
        command=ctx["cmd"], decision_result=ctx["dec"], initializer_request=ctx["ireq"], initializer_result=bad_ires
    )
    assert r.status == "BLOCKED"
    assert r.reason == "container_not_created"


# --- digest / identity binding ----------------------------------------------
def test_decision_digest_mismatch_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, decision_result_digest="0" * 64)
    assert r.status == "BLOCKED"
    assert r.reason == "decision_digest_mismatch"


def test_initializer_digest_mismatch_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, initializer_result_digest="0" * 64)
    assert r.status == "BLOCKED"
    assert r.reason == "initializer_digest_mismatch"


def test_writer_request_digest_mismatch_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, writer_request_digest="0" * 64)
    assert r.status == "BLOCKED"
    assert r.reason == "writer_request_digest_mismatch"


def test_db_path_mismatch_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, db_path=ctx["db"] + "_other")
    assert r.status == "BLOCKED"
    assert r.reason == "db_path_mismatch"
    assert _log_rows(ctx["db"]) == []


def test_schema_version_mismatch_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, schema_version="s1_v2")
    assert r.status == "BLOCKED"
    assert r.reason == "schema_version_mismatch"


def test_s1_target_mismatch_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, s1_target="s1_eth_other_target")
    assert r.status == "BLOCKED"
    assert r.reason == "freshness_binding_mismatch"


def test_canonical_payload_mismatch_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, canonical_payload_digest="f" * 64)
    assert r.status == "BLOCKED"
    assert r.reason == "freshness_binding_mismatch"


def test_approval_row_mismatch_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, approval_row_digest="9" * 64)
    assert r.status == "BLOCKED"
    assert r.reason == "freshness_binding_mismatch"


def test_immutable_snapshot_mismatch_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, immutable_snapshot_ref="snap::different")
    assert r.status == "BLOCKED"
    assert r.reason == "freshness_binding_mismatch"


# --- pre-append tamper battery (suspect state, no cleanup) -------------------
def test_fingerprint_mismatch_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, expected_container_fingerprint="0" * 64)
    assert r.status == "BLOCKED_TAMPER_SUSPECT"
    assert r.reason == "fingerprint_mismatch"
    assert _log_rows(ctx["db"]) == []


def test_wrong_pragma_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    con = sqlite3.connect(ctx["db"])
    con.execute("PRAGMA journal_mode=DELETE")
    con.commit()
    con.close()
    # recompute fingerprint so this isolates the PRAGMA tamper, not a fingerprint diff
    cmd = dataclasses.replace(ctx["cmd"], expected_container_fingerprint=compute_container_fingerprint(ctx["db"]))
    r = run_production_s1_append_circuit(
        command=cmd, decision_result=ctx["dec"], initializer_request=ctx["ireq"], initializer_result=ctx["ires"]
    )
    assert r.status == "BLOCKED_TAMPER_SUSPECT"
    assert r.reason == "journal_fingerprint_mismatch"


def test_nonzero_rows_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    con = sqlite3.connect(ctx["db"])
    con.execute(
        "INSERT INTO s1_appends (evidence_digest, s1_target, canonical_payload_digest, approval_row_digest, "
        "freshness_binding_digest, immutable_snapshot_ref, operator_command_id, created_at_utc) "
        "VALUES ('e','t','c','a','f','s','o','2026-01-01T00:00:00Z')"
    )
    con.commit()
    con.close()
    r = _run(ctx)
    assert r.status == "BLOCKED_TAMPER_SUSPECT"
    assert r.reason == "nonzero_rows"


def test_missing_triggers_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    con = sqlite3.connect(ctx["db"])
    con.execute("DROP TRIGGER s1_appends_no_update")
    con.execute("DROP TRIGGER s1_appends_no_delete")
    con.commit()
    con.close()
    cmd = dataclasses.replace(ctx["cmd"], expected_container_fingerprint=compute_container_fingerprint(ctx["db"]))
    r = run_production_s1_append_circuit(
        command=cmd, decision_result=ctx["dec"], initializer_request=ctx["ireq"], initializer_result=ctx["ires"]
    )
    assert r.status == "BLOCKED_TAMPER_SUSPECT"
    assert r.reason == "schema_fingerprint_mismatch"


def test_wrong_file_mode_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    os.chmod(ctx["db"], 0o644)
    r = _run(ctx)
    assert r.status == "BLOCKED_TAMPER_SUSPECT"
    assert r.reason == "file_mode_mismatch"


def test_corrupt_db_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    with open(ctx["db"], "wb") as fh:
        fh.write(b"not a database")
    os.chmod(ctx["db"], 0o600)
    r = _run(ctx)
    assert r.status == "BLOCKED_TAMPER_SUSPECT"
    assert r.reason in ("integrity_failure", "introspection_failed")


def test_hot_journal_returns_recovery_required_no_cleanup(tmp_path):
    ctx = _valid(tmp_path)
    sidecar = ctx["db"] + "-journal"
    with open(sidecar, "wb") as fh:
        fh.write(b"\x00hot")
    r = _run(ctx)
    assert r.status == "BLOCKED_RECOVERY_REQUIRED"
    assert os.path.exists(sidecar)
    assert _log_rows(ctx["db"]) == []


def test_lock_residue_returns_recovery_required_no_cleanup(tmp_path):
    ctx = _valid(tmp_path)
    sidecar = ctx["db"] + "-lock"
    with open(sidecar, "wb") as fh:
        fh.write(b"\x00lock")
    r = _run(ctx)
    assert r.status == "BLOCKED_RECOVERY_REQUIRED"
    assert os.path.exists(sidecar)


# --- idempotency / atomicity / concurrency ----------------------------------
def test_duplicate_replay_blocks_zero_extra_rows(tmp_path):
    ctx = _valid(tmp_path)
    r1 = _run(ctx)
    assert r1.status == "APPEND_RECORDED_IN_TEST_CONTAINER"
    for _ in range(4):
        r = _run(ctx)
        assert r.status == "BLOCKED_DUPLICATE"
    assert _log_rows(ctx["db"]) == [(_EVI, _TGT)]


def test_concurrent_threads_exactly_one_append(tmp_path):
    ctx = _valid(tmp_path)
    lock = threading.Lock()
    results = []
    barrier = threading.Barrier(8)

    def worker():
        barrier.wait()
        results.append(
            run_production_s1_append_circuit(
                command=ctx["cmd"], decision_result=ctx["dec"], initializer_request=ctx["ireq"],
                initializer_result=ctx["ires"], single_flight=lock,
            )
        )

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    appended = [x for x in results if x.status == "APPEND_RECORDED_IN_TEST_CONTAINER"]
    assert len(appended) == 1
    assert _log_rows(ctx["db"]) == [(_EVI, _TGT)]
    for x in results:
        if x.status != "APPEND_RECORDED_IN_TEST_CONTAINER":
            assert x.status in ("BLOCKED", "BLOCKED_DUPLICATE", "BLOCKED_TAMPER_SUSPECT", "BLOCKED_RECOVERY_REQUIRED")


# --- result object: frozen, passive, deterministic --------------------------
def test_result_is_frozen(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx)
    with pytest.raises(Exception):
        r.status = "PRODUCTION_APPEND_AUTHORIZED"  # type: ignore[misc]


def test_blocked_result_authority_flags_false(tmp_path):
    ctx = _valid(tmp_path)
    r = _run(ctx, decision_result_digest="0" * 64)
    for flag in (
        "production_s1_append_authorized",
        "production_stream_authorized",
        "trading_authorized",
        "capacity_enabled",
        "wallet_authorized",
    ):
        assert getattr(r, flag) is False


def test_result_digest_deterministic_for_blocked(tmp_path):
    ctx = _valid(tmp_path)
    r1 = _run(ctx, decision_result_digest="0" * 64)
    r2 = _run(ctx, decision_result_digest="0" * 64)
    assert len(r1.circuit_result_digest) == 64
    assert r1.circuit_result_digest == r2.circuit_result_digest


# --- isolation / no-surface (library only, no CLI/API/network/auto-start) ----
def test_no_cli_api_network_auto_start_tokens():
    import approval.production_s1_append_circuit as mod

    low = inspect.getsource(mod).lower()
    # Framework/network/CLI absence is guaranteed by the stdlib+approval import allowlist
    # (test_imports_stdlib_and_approval_only) — argparse/click/flask/socket/requests/urllib/
    # subprocess simply cannot be imported. Here scan only EXECUTABLE patterns that the allowlist
    # cannot express; bare capability words appear in the docstring that documents the constraints.
    for tok in ("if __name__", ".environ", "getenv(", "os.system", "os.popen", "os.fork", "eval(", "exec("):
        assert tok not in low, f"forbidden executable token: {tok}"


def test_no_auto_promotion_or_trade_surface():
    import approval.production_s1_append_circuit as mod

    for name in dir(mod):
        if not callable(getattr(mod, name)):
            continue
        low = name.lower()
        for verb in (
            "schedule", "enqueue", "worker", "observe", "subscribe", "listener",
            "start_stream", "place_", "submit_order", "trade", "set_capacity", "on_append",
        ):
            assert verb not in low, f"forbidden surface: {name}"


def test_imports_stdlib_and_approval_only():
    import approval.production_s1_append_circuit as mod

    tree = ast.parse(inspect.getsource(mod))
    allowed_top = {"hashlib", "sqlite3", "dataclasses", "typing", "__future__", "os", "approval"}
    imported_top = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported_top.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_top.add(node.module.split(".")[0])
    assert imported_top <= allowed_top, f"unexpected imports: {imported_top - allowed_top}"


# --- Schema & Journal Unification: legacy/dual-table rejection + no-legacy token --------------------
_LEGACY = "s1_append" + "_log"  # token appears as a literal only in the forbidden-token assertion


def test_dual_table_container_fails_closed(tmp_path):
    ctx = _valid(tmp_path)
    con = sqlite3.connect(ctx["db"])
    con.execute(f"CREATE TABLE {_LEGACY} (seq INTEGER PRIMARY KEY AUTOINCREMENT)")
    con.commit()
    con.close()
    cmd = dataclasses.replace(ctx["cmd"], expected_container_fingerprint=compute_container_fingerprint(ctx["db"]))
    r = run_production_s1_append_circuit(
        command=cmd, decision_result=ctx["dec"], initializer_request=ctx["ireq"], initializer_result=ctx["ires"]
    )
    assert r.status == "BLOCKED_TAMPER_SUSPECT"
    assert r.reason == "forbidden_dual_table"
    assert _log_rows(ctx["db"]) == []


def test_circuit_uses_canonical_table_only_no_legacy():
    import approval.production_s1_append_circuit as mod

    src = inspect.getsource(mod)
    assert "s1_appends" in src, "circuit must use the canonical s1_appends table"
    assert "s1_append_log" not in src, "legacy s1_append_log must not be used by the circuit"
