"""tests/test_approval_ledger_db.py — isolated Human Approval Ledger DB slice (TDD).

Bu slice, önceki ratifiye slice'ların (Human Approval Package Verification + Day-Zero Trust Anchor /
Production Verifier Wiring) PASİF sonuçlarını S1'den TAMAMEN bağımsız, append-only bir sqlite
ledger'a yazar. Hiçbir kayıt "execute onaylı / S1 onaylı / trade onaylı / capacity açık" anlamına
GELEMEZ. DB application-API seviyesinde append-only'dir: update/delete/mutation API'si YOKTUR.

Fail-closed: eksik verifier/trust-anchor provenance, geçersiz verifier/anchor result, ambiguous
status, ve placeholder fingerprint'ler (all-zero / repeated-char / non-hex / non-lowercase) reddedilir.
Ceremony evidence yalnızca KAYITLI İDDİA olarak saklanır (fiziksel törenin matematiksel kanıtı
DEĞİL); sha256-şekilli fingerprint entropy kanıtı SAYILMAZ.

İlk RED: approval.approval_ledger_db yok → ImportError (eksik üretim seam'i).
"""
import ast
import hashlib
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval.approval_ledger_db import (
    AppendResult,
    PASSIVE_STATUS,
    StoredApprovalRecord,
    append_passive_record,
    fetch_record,
    init_approval_ledger,
    list_sequences,
    record_count,
)
from approval.trust_anchor import AnchorResult
from approval.verifier_registry import ResolveResult

# realistic lowercase 64-hex fingerprint WITH entropy (not a placeholder)
_REAL_FP = hashlib.sha256(b"operator-public-key-day-zero").hexdigest()


def _ok_verifier():
    return ResolveResult(True, "", "ed25519_detached_v1")


def _ok_anchor():
    return AnchorResult(True, "")


def _append(db, **over):
    kw = dict(
        verifier_result=_ok_verifier(),
        trust_anchor_result=_ok_anchor(),
        approval_record_id="appr-0001",
        command_scope="s1_evidence_matrix_construction",
        public_key_fingerprint=_REAL_FP,
        ceremony_evidence_marker="DAY_ZERO_CEREMONY_witnessed",
        status=PASSIVE_STATUS,
    )
    kw.update(over)
    return append_passive_record(db, **kw)


# 1 — DB initializes in isolated approval namespace/path only
def test_init_creates_isolated_db(tmp_path):
    db = str(tmp_path / "approval_ledger.sqlite3")
    assert not os.path.exists(db)
    init_approval_ledger(db)
    assert os.path.exists(db)
    assert record_count(db) == 0


# 2 — append passive verification record succeeds
def test_append_passive_record_succeeds(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    res = _append(db)
    assert isinstance(res, AppendResult)
    assert res.valid is True
    assert res.reason == ""
    assert res.append_sequence == 1
    assert record_count(db) == 1


# 3 — appended record is immutable via public API (frozen record + DB-level append-only)
def test_record_is_immutable(tmp_path):
    import sqlite3

    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    _append(db)
    rec = fetch_record(db, 1)
    assert isinstance(rec, StoredApprovalRecord)
    with pytest.raises(Exception):
        rec.status = "X"  # type: ignore[misc]
    # DB-level append-only: a raw UPDATE/DELETE must be blocked by triggers
    conn = sqlite3.connect(db)
    try:
        with pytest.raises(sqlite3.Error):
            conn.execute("UPDATE approval_ledger SET status='X' WHERE append_sequence=1")
            conn.commit()
        with pytest.raises(sqlite3.Error):
            conn.execute("DELETE FROM approval_ledger WHERE append_sequence=1")
            conn.commit()
    finally:
        conn.close()


# 4 — no update/delete/mutation API exists
def test_no_mutation_api_exists():
    import approval.approval_ledger_db as mod

    for name in dir(mod):
        low = name.lower()
        for banned in ("update", "delete", "mutate", "edit", "remove", "drop", "overwrite"):
            assert banned not in low, f"mutation API exposed: {name}"


# 5 — S1/raw/network/wallet/signing/trading/capacity modules are not imported
def test_slice_imports_no_forbidden_dependency():
    import approval.approval_ledger_db as mod

    tree = ast.parse(inspect.getsource(mod))
    allowed_top = {"sqlite3", "re", "dataclasses", "typing", "__future__"}
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
        "s1",
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


# 6/7/8 — record cannot mark S1 append / matrix / trading-paper-live-capacity authorized
def test_record_carries_only_non_authority_flags(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    _append(db)
    rec = fetch_record(db, 1)
    assert rec.s1_append_authorized is False
    assert rec.s1_matrix_authorized is False
    assert rec.trading_authorized is False
    assert rec.paper_live_authorized is False
    assert rec.capacity_authorized is False


# 9 — missing verifier provenance fails closed
def test_missing_verifier_provenance_fails_closed(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    res = _append(db, verifier_result=None)
    assert res.valid is False
    assert res.reason == "missing_verifier_provenance"
    assert record_count(db) == 0


# 10 — missing trust-anchor provenance fails closed
def test_missing_trust_anchor_provenance_fails_closed(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    res = _append(db, trust_anchor_result=None)
    assert res.valid is False
    assert res.reason == "missing_trust_anchor_provenance"


# 11 — ceremony evidence is stored only as claim/evidence, not proof
def test_ceremony_evidence_is_claim_not_proof(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    _append(db)
    rec = fetch_record(db, 1)
    assert rec.ceremony_evidence_kind == "recorded_claim_not_physical_proof"


# 12 — sha256-shaped fingerprint is not treated as entropy proof
def test_fingerprint_shape_is_not_entropy_proof(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    _append(db)
    rec = fetch_record(db, 1)
    assert rec.fingerprint_entropy_claim == "shape_only_not_entropy_proof"


# 13 — all-zero fingerprint fails closed
def test_all_zero_fingerprint_fails_closed(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    res = _append(db, public_key_fingerprint="0" * 64)
    assert res.valid is False
    assert res.reason == "placeholder_all_zero_fingerprint"


# 14 — repeated-character fingerprint fails closed
def test_repeated_char_fingerprint_fails_closed(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    res = _append(db, public_key_fingerprint="a" * 64)
    assert res.valid is False
    assert res.reason == "placeholder_repeated_char_fingerprint"


# 15 — malformed fingerprint fails closed (non-hex / non-lowercase / wrong length)
def test_malformed_fingerprint_fails_closed(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    for bad in ("ABC" + "d" * 61, "z" * 64, "abc123", _REAL_FP.upper()):
        res = _append(db, public_key_fingerprint=bad)
        assert res.valid is False, bad
        assert res.reason == "malformed_fingerprint", bad


# 16 — ambiguous approval status fails closed
def test_ambiguous_status_fails_closed(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    for bad in ("APPROVED_TO_EXECUTE", "S1_AUTHORIZED", "MAYBE", ""):
        res = _append(db, status=bad)
        assert res.valid is False, bad
        assert res.reason == "ambiguous_approval_status", bad


# 17 — invalid verifier result cannot be appended as approval
def test_invalid_verifier_result_rejected(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    res = _append(db, verifier_result=ResolveResult(False, "unknown_verifier_identity"))
    assert res.valid is False
    assert res.reason == "invalid_verifier_result"
    assert record_count(db) == 0


# 18 — invalid trust-anchor result cannot be appended as approval
def test_invalid_trust_anchor_result_rejected(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    res = _append(db, trust_anchor_result=AnchorResult(False, "malformed_fingerprint"))
    assert res.valid is False
    assert res.reason == "invalid_trust_anchor_result"


# 19 — append order is deterministic
def test_append_order_is_deterministic(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    _append(db, approval_record_id="appr-1")
    _append(db, approval_record_id="appr-2")
    _append(db, approval_record_id="appr-3")
    assert list_sequences(db) == [1, 2, 3]
    assert [fetch_record(db, s).approval_record_id for s in list_sequences(db)] == [
        "appr-1",
        "appr-2",
        "appr-3",
    ]


# 20 — output remains passive/frozen with reason only
def test_append_result_is_passive_frozen(tmp_path):
    db = str(tmp_path / "a.sqlite3")
    init_approval_ledger(db)
    res = _append(db)
    with pytest.raises(Exception):
        res.valid = False  # type: ignore[misc]
    assert set(vars(res).keys()) == {"valid", "reason", "append_sequence"}
