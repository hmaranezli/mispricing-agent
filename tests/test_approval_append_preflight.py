"""tests/test_approval_append_preflight.py — Human Approval Ledger append abuse-resistance preflight
(TDD).

Bu slice, append-only approval ledger'a yazmadan ÖNCE PASİF, deterministik bir abuse-preflight kararı
üretir. Spam / typo loop / retry storm / malicious while(true) flood ve disk/inode tükenmesi
FAIL-CLOSED ile bloklanır. Preflight HİÇBİR satır yazmaz, HİÇBİR şeyi silmez/truncate/compact etmez,
ve HİÇBİR şeyi yetkilendirmez (S1/matrix/paper/live/trading/capacity yok). Rate-limit dimensions
açık girdidir (gizli global config YOK); state, append-only ledger satırlarından TÜRETİLİR veya
caller'ın verdiği immutable snapshot'tan gelir — yeni mutable side-DB YOK.

İlk RED: approval.append_preflight yok → ImportError (eksik üretim seam'i).
"""
import ast
import hashlib
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval.append_preflight import (
    AppendAttempt,
    DiskStat,
    PreflightDecision,
    evaluate_append_preflight,
    snapshot_from_ledger,
)
from approval.approval_ledger_db import (
    PASSIVE_STATUS,
    append_passive_record,
    init_approval_ledger,
    record_count,
)
from approval.trust_anchor import AnchorResult
from approval.verifier_registry import ResolveResult

_REAL_FP = hashlib.sha256(b"operator-public-key-day-zero").hexdigest()
_SAFE_DISK = DiskStat(free_bytes=10_000_000, free_inodes=100_000)


def _pf(**over):
    kw = dict(
        actor_id="operator_a",
        window_id="win-1",
        record_signature="sig-1",
        history=tuple(),
        max_appends_per_window=3,
        max_invalid_per_window=3,
        max_duplicates=3,
        disk_stat=_SAFE_DISK,
        min_free_bytes=1_000_000,
        min_free_inodes=10_000,
    )
    kw.update(over)
    return evaluate_append_preflight(**kw)


def _attempt(actor, window, sig, outcome):
    return AppendAttempt(actor_id=actor, window_id=window, record_signature=sig, outcome=outcome)


# 1 — valid append preflight passes under quota
def test_valid_preflight_passes():
    d = _pf()
    assert isinstance(d, PreflightDecision)
    assert d.allowed is True
    assert d.reason == ""


# 2 — missing actor/source identity fails closed
def test_missing_actor_fails_closed():
    d = _pf(actor_id="")
    assert d.allowed is False
    assert d.reason == "missing_actor_identity"


# 3 — quota exceeded fails closed and does not append
def test_quota_exceeded_fails_closed():
    hist = tuple(_attempt("operator_a", "win-1", f"s{i}", "valid") for i in range(3))
    d = _pf(history=hist, max_appends_per_window=3)
    assert d.allowed is False
    assert d.reason == "append_quota_exceeded"


# 4 — repeated invalid attempts classified as duplicate storm
def test_repeated_signature_is_duplicate_storm():
    hist = tuple(_attempt("operator_a", "win-1", "sig-dup", "invalid") for _ in range(3))
    d = _pf(history=hist, record_signature="sig-dup", max_duplicates=3)
    assert d.allowed is False
    assert d.reason == "duplicate_storm"


# 5 — duplicate storm blocks further append passively (no exception, just blocked)
def test_duplicate_storm_blocks_passively():
    hist = tuple(_attempt("operator_a", "win-1", "sig-dup", "invalid") for _ in range(5))
    d = _pf(history=hist, record_signature="sig-dup", max_duplicates=3)
    assert d.allowed is False
    assert d.reason == "duplicate_storm"


# 6 — retry storm within window fails closed
def test_retry_storm_within_window_fails_closed():
    hist = tuple(_attempt("operator_a", "win-1", f"s{i}", "invalid") for i in range(3))
    d = _pf(history=hist, max_invalid_per_window=3, max_duplicates=99)
    assert d.allowed is False
    assert d.reason == "retry_storm"


# 7 — separate actor/source windows are isolated
def test_actor_windows_are_isolated():
    flood = tuple(_attempt("attacker", "win-1", f"s{i}", "valid") for i in range(50))
    d = _pf(actor_id="operator_a", history=flood, max_appends_per_window=3)
    assert d.allowed is True
    assert d.reason == ""


# 8 — legitimate operator can still append after unrelated actor flood
def test_legit_operator_after_unrelated_flood():
    flood = tuple(_attempt("attacker", "win-1", f"s{i}", "invalid") for i in range(99))
    d = _pf(actor_id="operator_a", history=flood)
    assert d.allowed is True


# 9 — disk free-space preflight fail blocks append before DB write
def test_disk_free_space_fail_blocks():
    d = _pf(disk_stat=DiskStat(free_bytes=500, free_inodes=100_000), min_free_bytes=1_000_000)
    assert d.allowed is False
    assert d.reason == "disk_free_space_preflight_failed"


# 10 — inode preflight fail blocks append before DB write
def test_inode_preflight_fail_blocks():
    d = _pf(disk_stat=DiskStat(free_bytes=10_000_000, free_inodes=5), min_free_inodes=10_000)
    assert d.allowed is False
    assert d.reason == "inode_preflight_failed"


# 11 — automatic deletion/truncation/compaction API does not exist
def test_no_destructive_api_exists():
    import approval.append_preflight as mod

    for name in dir(mod):
        low = name.lower()
        for banned in ("delete", "truncate", "compact", "redact", "drop", "vacuum", "remove", "mutate"):
            assert banned not in low, f"destructive API exposed: {name}"


# 12 — no DB row is written on blocked preflight (preflight is pure/passive)
def test_no_db_write_on_preflight(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    assert record_count(db) == 0
    _pf(actor_id="")  # blocked
    _pf()  # allowed decision — still must not write
    assert record_count(db) == 0


# 13 — rate-limit pass does not set approval/S1/capacity flags
def test_pass_sets_no_authority_flags():
    d = _pf()
    assert set(vars(d).keys()) == {"allowed", "reason"}
    for bad in ("s1", "approved", "capacity", "trade", "paper", "live"):
        assert not hasattr(d, bad)


# 14 — rate-limit fail does not authorize recovery
def test_fail_does_not_authorize_recovery():
    d = _pf(disk_stat=DiskStat(free_bytes=1, free_inodes=1), min_free_bytes=1_000_000)
    assert d.allowed is False
    assert set(vars(d).keys()) == {"allowed", "reason"}
    assert "recover" not in d.reason.lower()


# 15 — derived state from existing rows is deterministic
def test_snapshot_from_ledger_deterministic(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    for i in range(3):
        append_passive_record(
            db,
            verifier_result=ResolveResult(True, "", "ed25519_detached_v1"),
            trust_anchor_result=AnchorResult(True, ""),
            approval_record_id=f"appr-{i}",
            command_scope="scope",
            public_key_fingerprint=_REAL_FP,
            ceremony_evidence_marker="m",
            status=PASSIVE_STATUS,
        )
    s1 = snapshot_from_ledger(db)
    s2 = snapshot_from_ledger(db)
    assert s1 == s2
    assert isinstance(s1, tuple)
    assert len(s1) == 3
    assert all(isinstance(a, AppendAttempt) for a in s1)


# 16 — caller-supplied immutable snapshot path is accepted
def test_caller_supplied_snapshot_accepted():
    snap = (_attempt("operator_a", "win-1", "sig-x", "valid"),)
    d = _pf(history=snap)
    assert d.allowed is True


# 17 — ambiguous window/quota input fails closed
def test_ambiguous_input_fails_closed():
    assert _pf(window_id="").reason == "ambiguous_window_input"
    assert _pf(max_appends_per_window=-1).reason == "ambiguous_quota_input"
    assert _pf(max_invalid_per_window=None).reason == "ambiguous_quota_input"
    assert _pf(min_free_bytes=-5).reason == "ambiguous_quota_input"


# 18 — output is passive/frozen with reason only
def test_decision_is_passive_frozen():
    d = _pf()
    with pytest.raises(Exception):
        d.allowed = False  # type: ignore[misc]
    assert set(vars(d).keys()) == {"allowed", "reason"}


# 19 — imports no forbidden S1/raw/network/wallet/signing/trading/capacity modules
def test_slice_imports_no_forbidden_dependency():
    import approval.append_preflight as mod

    tree = ast.parse(inspect.getsource(mod))
    allowed_top = {"sqlite3", "dataclasses", "typing", "__future__"}
    imported_top, imported_full = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported_full.add(n.name)
                imported_top.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_full.add(node.module)
                imported_top.add(node.module.split(".")[0])
    assert imported_top <= allowed_top, f"unexpected imports: {imported_top - allowed_top}"
    forbidden = (
        "raw_capture",
        "socket",
        "requests",
        "urllib",
        "http",
        "wallet",
        "clob",
        "signing",
        "trading",
        "capacity",
        "paper",
    )
    for modname in imported_full:
        low = modname.lower()
        for tok in forbidden:
            assert tok not in low, f"forbidden import: {modname}"


# 20 — existing approval DB immutability still holds (append-only triggers)
def test_existing_db_immutability_holds(tmp_path):
    import sqlite3

    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    append_passive_record(
        db,
        verifier_result=ResolveResult(True, "", "ed25519_detached_v1"),
        trust_anchor_result=AnchorResult(True, ""),
        approval_record_id="appr-x",
        command_scope="scope",
        public_key_fingerprint=_REAL_FP,
        ceremony_evidence_marker="m",
        status=PASSIVE_STATUS,
    )
    conn = sqlite3.connect(db)
    try:
        with pytest.raises(sqlite3.Error):
            conn.execute("UPDATE approval_ledger SET status='X'")
            conn.commit()
        with pytest.raises(sqlite3.Error):
            conn.execute("DELETE FROM approval_ledger")
            conn.commit()
    finally:
        conn.close()
