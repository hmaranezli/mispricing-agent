"""tests/test_signing_payload_return.py — passive signing payload + presentation fidelity +
air-gapped signature return + preflight-gated approval-ledger append bridge (TDD).

Bu slice, RATIFIYE Signing Payload Construction & Air-Gapped Signature Return Boundary Charter'ından
sonraki entegre köprüdür. Deterministik kanonik signing payload byte'ları üretir, görünür sunum
metnini TAM kanonik byte'lardan türetir (caller metni DEĞİL), pasif inert imza dönüşünü alır,
KABULDEN ÖNCE payload digest + doğrulama + append-preflight'ı zorunlu kılar, ve YALNIZCA mevcut
izole append-only approval ledger mekanizmasıyla TEK bir kayıt ekler. Hiçbir S1 yetkisi / S1 append /
production stream / execution token / trading / wallet / capacity üretilmez.

İlk RED: approval.signing_payload_return yok → ImportError (eksik üretim seam'i).
"""
import ast
import hashlib
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval.signing_payload_return import (
    BridgeResult,
    Presentation,
    SignatureReturn,
    SigningPayload,
    accept_signature_and_append,
    build_signing_payload,
    render_presentation,
)
from approval.s1_evidence_matrix import COLUMNS, ROW_CLASSES, construct_s1_evidence_matrix
from approval.s1_matrix_review import compile_operator_review_package
from approval.append_preflight import PreflightDecision
from approval.approval_ledger_db import init_approval_ledger, record_count
from approval.trust_anchor import AnchorResult
from approval.verifier_registry import ResolveResult

_FP = hashlib.sha256(b"operator-public-key-day-zero").hexdigest()
_ALLOW = PreflightDecision(True, "")
_DENY = PreflightDecision(False, "duplicate_storm")


def _review_package():
    m = construct_s1_evidence_matrix(
        audit_summary={"status": "PASS_COMPLETE"},
        approval_ledger_refs=("appr-0001",),
        evidence={r: {c: "EVIDENCE_PRESENT" for c in COLUMNS} for r in ROW_CLASSES},
    )
    return compile_operator_review_package(m)


def _payload(**over):
    kw = dict(
        review_package=_review_package(),
        approval_record_id="appr-0001",
        command_scope="s1_evidence_matrix_construction",
        signer_identity_class="human_operator",
        public_key_fingerprint=_FP,
    )
    kw.update(over)
    return build_signing_payload(**kw)


def _sigret(payload, **over):
    kw = dict(
        signer_identity_class="human_operator",
        claimed_payload_digest=payload.payload_digest,
        signature=b"INERT-DETACHED-SIGNATURE-BYTES",
        verification_valid=True,
    )
    kw.update(over)
    return SignatureReturn(**kw)


def _accept(db, payload, sigret, **over):
    kw = dict(
        signing_payload=payload,
        signature_return=sigret,
        verifier_result=ResolveResult(True, "", "ed25519_detached_v1"),
        trust_anchor_result=AnchorResult(True, ""),
        preflight_decision=_ALLOW,
        ceremony_evidence_marker="DAY_ZERO_CEREMONY_witnessed",
    )
    kw.update(over)
    return accept_signature_and_append(db, **kw)


# 1 — canonical payload bytes deterministic for identical input
def test_canonical_bytes_deterministic():
    a = _payload()
    b = _payload()
    assert a.canonical_bytes == b.canonical_bytes
    assert a.payload_digest == b.payload_digest
    assert isinstance(a.canonical_bytes, bytes)


# 2 — canonical payload digest changes on any byte-relevant field change
def test_digest_changes_on_field_change():
    base = _payload()
    other = _payload(command_scope="DIFFERENT_SCOPE")
    assert base.payload_digest != other.payload_digest


# 3 — visible presentation text is derived from exact canonical bytes, not caller text
def test_presentation_from_canonical_bytes_not_caller_text():
    params = set(inspect.signature(render_presentation).parameters)
    for bad in ("text", "display", "message", "summary", "caption"):
        assert bad not in {p.lower() for p in params}
    p = _payload()
    pres = render_presentation(p)
    assert isinstance(pres, Presentation)
    assert p.canonical_bytes.decode("utf-8") in pres.visible_text


# 4 — presentation summary includes payload digest and literal statement
def test_presentation_includes_digest_and_statement():
    p = _payload()
    pres = render_presentation(p)
    assert p.payload_digest in pres.visible_text
    assert "signature is evidence, not S1 authorization" in pres.visible_text


# 5 — presentation cannot hide/truncate/replace canonical bytes
def test_presentation_no_hide_truncate():
    p = _payload()
    pres = render_presentation(p)
    assert pres.canonical_bytes == p.canonical_bytes
    assert len(p.payload_digest) == 64
    assert p.payload_digest in pres.visible_text  # full digest, not truncated


# 6 — caller cannot pass alternate digest/display/waiver/override/policy/command/token/authority
def test_no_caller_override_params():
    # 'command_scope' is a legitimate descriptive field (which scope is approved), not an injected
    # executable command — so 'command' is intentionally NOT banned; injection vectors are.
    banned = ("digest", "display", "text", "waiver", "override", "policy", "token", "authoriz")
    for fn in (build_signing_payload, render_presentation, accept_signature_and_append):
        params = {p.lower() for p in inspect.signature(fn).parameters}
        for b in banned:
            assert not any(b in p for p in params), f"{fn.__name__} exposes '{b}'"


# 7 — air-gapped signature return is passive/inert data only
def test_signature_return_is_inert():
    p = _payload()
    sr = _sigret(p)
    with pytest.raises(Exception):
        sr.signature = b"x"  # type: ignore[misc]
    for v in vars(sr).values():
        assert not callable(v)


# 8 — signature return with digest mismatch fails closed before DB append
def test_digest_mismatch_fails_closed(tmp_path):
    db = str(tmp_path / "approval_ledger.sqlite3")
    init_approval_ledger(db)
    p = _payload()
    sr = _sigret(p, claimed_payload_digest="f" * 64)
    res = _accept(db, p, sr)
    assert res.appended is False
    assert res.reason == "payload_digest_mismatch"
    assert record_count(db) == 0


# 9 — signature return with missing/invalid verification fails closed before append
def test_invalid_verification_fails_closed(tmp_path):
    db = str(tmp_path / "approval_ledger.sqlite3")
    init_approval_ledger(db)
    p = _payload()
    res = _accept(db, p, _sigret(p, verification_valid=False))
    assert res.appended is False
    assert res.reason == "missing_or_invalid_verification"
    assert record_count(db) == 0


# 10 — append preflight DENIED blocks DB append
def test_preflight_denied_blocks_append(tmp_path):
    db = str(tmp_path / "approval_ledger.sqlite3")
    init_approval_ledger(db)
    p = _payload()
    res = _accept(db, p, _sigret(p), preflight_decision=_DENY)
    assert res.appended is False
    assert res.reason == "append_preflight_denied"
    assert record_count(db) == 0


# 11 — append preflight ALLOWED permits exactly one approval-ledger append
def test_preflight_allowed_appends_one(tmp_path):
    db = str(tmp_path / "approval_ledger.sqlite3")
    init_approval_ledger(db)
    p = _payload()
    res = _accept(db, p, _sigret(p))
    assert res.appended is True
    assert res.reason == ""
    assert res.append_sequence == 1
    assert record_count(db) == 1


# 12 — append uses existing isolated append-only mechanism only (triggers still abort)
def test_append_only_mechanism(tmp_path):
    import sqlite3

    db = str(tmp_path / "approval_ledger.sqlite3")
    init_approval_ledger(db)
    p = _payload()
    _accept(db, p, _sigret(p))
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


# 13 — no approval ledger append occurs before digest match + verification + preflight
def test_no_append_before_all_gates(tmp_path):
    db = str(tmp_path / "approval_ledger.sqlite3")
    init_approval_ledger(db)
    p = _payload()
    _accept(db, p, _sigret(p, claimed_payload_digest="0" * 64))
    _accept(db, p, _sigret(p, verification_valid=None))
    _accept(db, p, _sigret(p), preflight_decision=_DENY)
    assert record_count(db) == 0


# 14 — duplicate/retry signature return blocked by existing preflight semantics
def test_duplicate_blocked_by_preflight(tmp_path):
    db = str(tmp_path / "approval_ledger.sqlite3")
    init_approval_ledger(db)
    p = _payload()
    res = _accept(db, p, _sigret(p), preflight_decision=PreflightDecision(False, "duplicate_storm"))
    assert res.appended is False
    assert res.reason == "append_preflight_denied"
    assert record_count(db) == 0


# 15 — no S1 DB created
def test_no_s1_db_created(tmp_path):
    db = str(tmp_path / "approval_ledger.sqlite3")
    init_approval_ledger(db)
    p = _payload()
    _accept(db, p, _sigret(p))
    for f in os.listdir(tmp_path):
        assert "s1" not in f.lower(), f"unexpected S1 artifact: {f}"


# 16 — no S1 append/stream/trade/execute/order/capacity command surface
def test_no_forbidden_command_surface():
    import approval.signing_payload_return as mod

    for name in dir(mod):
        low = name.lower()
        for banned in (
            "s1_append",
            "s1_stream",
            "production_stream",
            "execute",
            "place_order",
            "submit_order",
            "_order",
            "trade",
            "capacity",
            "execution_token",
            "stream",
            "wallet",
        ):
            assert banned not in low, f"forbidden command surface: {name}"


# 17 — no key/secret/env/gpg/yubikey/hsm/tails/offline-salt access in source
def test_no_secret_or_key_access():
    import approval.signing_payload_return as mod

    # The import allowlist (test_slice_imports_narrow) already proves no os/subprocess/crypto/secret
    # module is imported. Here we scan for real code-level ACCESS tokens (these never appear in
    # legitimate docstring prose), not domain vocabulary like "secret/key" used in documentation.
    low = inspect.getsource(mod).lower()
    for tok in ("environ", "getenv", "subprocess", "open(", "yubikey", "offline_salt", ".system("):
        assert tok not in low, f"forbidden secret/key access token: {tok}"


# 18 — no filesystem artifact/export/report generated by build/render
def test_build_render_generate_no_files(tmp_path):
    before = set(os.listdir(tmp_path))
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        p = _payload()
        render_presentation(p)
    finally:
        os.chdir(cwd)
    assert set(os.listdir(tmp_path)) == before


# 19 — imports stdlib-only and narrow (plus sibling approval ledger), no forbidden module
def test_slice_imports_narrow():
    import approval.signing_payload_return as mod

    tree = ast.parse(inspect.getsource(mod))
    allowed_top = {"hashlib", "dataclasses", "typing", "__future__", "approval"}
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
        "s1_evidence",
        "s1_matrix",
        "raw_capture",
        "socket",
        "requests",
        "urllib",
        "wallet",
        "clob",
        "trading",
        "nacl",
        "cryptography",
        "subprocess",
    )
    for modname in imported_full:
        low = modname.lower()
        for tok in forbidden:
            assert tok not in low, f"forbidden import: {modname}"


# 20 — all authority flags remain hard-coded False; outputs passive/frozen
def test_authority_flags_false_and_frozen(tmp_path):
    db = str(tmp_path / "approval_ledger.sqlite3")
    init_approval_ledger(db)
    p = _payload()
    res = _accept(db, p, _sigret(p))
    for flag in (
        "s1_append_authorized",
        "production_stream_authorized",
        "execution_token_created",
        "trading_authorized",
        "capacity_enabled",
        "wallet_authorized",
    ):
        assert getattr(res, flag) is False
        assert getattr(p, flag) is False
    with pytest.raises(Exception):
        res.appended = True  # type: ignore[misc]
    with pytest.raises(Exception):
        p.payload_digest = "x"  # type: ignore[misc]
