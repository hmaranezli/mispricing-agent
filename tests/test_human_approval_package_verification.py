"""tests/test_human_approval_package_verification.py — isolated air-gapped approval package
verification slice (TDD).

Bu slice, gelecekteki insan onay (operator approval) mekanizmasının VPS tarafındaki TEK sınırını
pin'ler: internet'e açık VPS YALNIZCA public-key ile doğrulama yapar. İki Gemini endişesi fiziksel
olarak fail-closed edilir:
  1. Inert offline-imzalı paket transfer/parse kırılganlığı: herhangi bir byte/whitespace/newline/
     format/alan/kanonikleştirme uyuşmazlığı → fail closed.
  2. VPS'te duran public key bütünlüğü: sessiz public-key swap/overwrite → pinned fingerprint
     (sha256) uyuşmazlığı ile fail closed.

Tasarım: gerçek asimetrik kripto YOK (yeni bağımlılık YOK). signature_verifier ENJEKTE edilir
(public-key-only callable), private key API'ye yapısal olarak GEÇİRİLEMEZ. Doğrulama çıktısı PASİF:
valid/invalid + fail-closed reason. Geçerli sonuç HİÇBİR ŞEYİ yetkilendirmez (S1 append yok, matrix
yok, paper/live yok, capacity yok).

İlk RED: approval.package_verifier yok → ImportError (eksik üretim seam'i).
"""
import ast
import inspect
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval.package_verifier import (
    REQUIRED_FIELDS,
    VerificationResult,
    canonical_package_bytes,
    public_key_fingerprint,
    verify_approval_package,
)

_PUBLIC_KEY = b"ED25519-PUBLIC-KEY-BYTES-EXAMPLE-ONLY"
_SIGNATURE = b"DETACHED-SIGNATURE-BYTES-EXAMPLE-ONLY"


def _valid_fields():
    """Kapalı şemanın tüm zorunlu alanları (string değerler — float kanonikleştirme riski yok)."""
    return {
        "approval_record_id": "appr-0001",
        "operator_identity_class": "human_operator",
        "exact_command_text": "AUTHORIZE S1 MATRIX CONSTRUCTION scope=review",
        "command_scope": "s1_evidence_matrix_construction",
        "target_commit_sha": "7d3e7cd0ab2f6e65cc7789f38a306e2806664094",
        "target_ledger_identity": "raw_capture_run_001",
        "target_s1_identity": "none",
        "timestamp_utc": "2026-06-24T12:00:00Z",
        "nonce": "nonce-abc-123",
        "expiry_utc": "2026-06-24T13:00:00Z",
    }


def _accept_verifier(public_key, message, signature):
    """Enjekte edilen public-key-only doğrulayıcı (kabul). Private key YOK."""
    return True


def _reject_verifier(public_key, message, signature):
    """Enjekte edilen public-key-only doğrulayıcı (red)."""
    return False


def _pinned():
    return public_key_fingerprint(_PUBLIC_KEY)


# 1 — valid canonical package reaches verifier with exact canonical bytes
def test_valid_canonical_package_is_accepted():
    pkg = canonical_package_bytes(_valid_fields())
    res = verify_approval_package(
        pkg,
        public_key=_PUBLIC_KEY,
        pinned_public_key_fingerprint=_pinned(),
        signature=_SIGNATURE,
        signature_verifier=_accept_verifier,
    )
    assert isinstance(res, VerificationResult)
    assert res.valid is True
    assert res.reason == ""


# 2 — corrupted byte fails closed
def test_corrupted_byte_fails_closed():
    pkg = bytearray(canonical_package_bytes(_valid_fields()))
    pkg[5] ^= 0x01  # flip one bit in one byte
    res = verify_approval_package(
        bytes(pkg),
        public_key=_PUBLIC_KEY,
        pinned_public_key_fingerprint=_pinned(),
        signature=_SIGNATURE,
        signature_verifier=_accept_verifier,
    )
    assert res.valid is False
    assert res.reason != ""


# 3 — whitespace/newline/canonicalization shift fails closed
def test_non_canonical_whitespace_fails_closed():
    pkg = canonical_package_bytes(_valid_fields())
    # parse + re-dump with non-canonical formatting (indent/spaces/newlines)
    shifted = json.dumps(json.loads(pkg), indent=2).encode("utf-8")
    assert shifted != pkg
    res = verify_approval_package(
        shifted,
        public_key=_PUBLIC_KEY,
        pinned_public_key_fingerprint=_pinned(),
        signature=_SIGNATURE,
        signature_verifier=_accept_verifier,
    )
    assert res.valid is False
    assert res.reason == "non_canonical_bytes"


# 4 — missing required field fails closed
def test_missing_required_field_fails_closed():
    fields = _valid_fields()
    del fields["nonce"]
    pkg = canonical_package_bytes(fields)
    res = verify_approval_package(
        pkg,
        public_key=_PUBLIC_KEY,
        pinned_public_key_fingerprint=_pinned(),
        signature=_SIGNATURE,
        signature_verifier=_accept_verifier,
    )
    assert res.valid is False
    assert res.reason == "missing_required_field"


# 5 — unauthorized extra field fails closed
def test_unauthorized_extra_field_fails_closed():
    fields = _valid_fields()
    fields["inject_capacity"] = "1"
    pkg = canonical_package_bytes(fields)
    res = verify_approval_package(
        pkg,
        public_key=_PUBLIC_KEY,
        pinned_public_key_fingerprint=_pinned(),
        signature=_SIGNATURE,
        signature_verifier=_accept_verifier,
    )
    assert res.valid is False
    assert res.reason == "unauthorized_extra_field"


# 6 — public key fingerprint mismatch fails closed (pinned integrity lock)
def test_public_key_fingerprint_mismatch_fails_closed():
    pkg = canonical_package_bytes(_valid_fields())
    res = verify_approval_package(
        pkg,
        public_key=_PUBLIC_KEY,
        pinned_public_key_fingerprint="0" * 64,  # wrong pin → silent swap detection
        signature=_SIGNATURE,
        signature_verifier=_accept_verifier,
    )
    assert res.valid is False
    assert res.reason == "public_key_fingerprint_mismatch"


# 6b — a swapped public key (different bytes) under the old pin also fails closed
def test_swapped_public_key_fails_closed():
    pkg = canonical_package_bytes(_valid_fields())
    swapped = b"ATTACKER-SWAPPED-PUBLIC-KEY-BYTES"
    res = verify_approval_package(
        pkg,
        public_key=swapped,
        pinned_public_key_fingerprint=_pinned(),  # pinned to the ORIGINAL key
        signature=_SIGNATURE,
        signature_verifier=_accept_verifier,
    )
    assert res.valid is False
    assert res.reason == "public_key_fingerprint_mismatch"


# 7 — signature verifier rejection fails closed
def test_signature_rejection_fails_closed():
    pkg = canonical_package_bytes(_valid_fields())
    res = verify_approval_package(
        pkg,
        public_key=_PUBLIC_KEY,
        pinned_public_key_fingerprint=_pinned(),
        signature=_SIGNATURE,
        signature_verifier=_reject_verifier,
    )
    assert res.valid is False
    assert res.reason == "signature_verification_failed"


# 8 — verifier API exposes no private-key/signing input
def test_verifier_api_exposes_no_private_key_input():
    params = set(inspect.signature(verify_approval_package).parameters)
    forbidden_tokens = (
        "private",
        "secret",
        "seed",
        "signing_key",
        "sign_key",
        "privkey",
        "passphrase",
        "mnemonic",
    )
    for p in params:
        low = p.lower()
        for tok in forbidden_tokens:
            assert tok not in low, f"forbidden private-key-ish param: {p}"
    # the injected verifier is for verification only; no module-level signing helper exists
    import approval.package_verifier as mod

    for banned in ("sign", "private_key", "load_private", "generate_key", "keygen"):
        assert not hasattr(mod, banned), f"module exposes signing surface: {banned}"


# 9 — no S1/raw-ledger/network/wallet dependency imported by the new slice
def test_slice_imports_no_forbidden_dependency():
    import approval.package_verifier as mod

    src = inspect.getsource(mod)
    tree = ast.parse(src)
    allowed_top = {"json", "hashlib", "dataclasses", "typing", "__future__"}
    imported_top = set()
    imported_full = set()  # full dotted module paths actually imported
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported_full.add(n.name)
                imported_top.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_full.add(node.module)
                imported_top.add(node.module.split(".")[0])
    # Structural guarantee: ONLY the allowlisted stdlib/typing modules are imported. This alone
    # excludes every S1/ledger/network/wallet/crypto dependency. (Scope the forbidden-substring
    # check to import paths only — schema field names and docstrings legitimately mention this
    # vocabulary without importing anything.)
    assert imported_top <= allowed_top, f"unexpected imports: {imported_top - allowed_top}"

    forbidden_substrings = (
        "sqlite",
        "ledger",
        "socket",
        "requests",
        "urllib",
        "http",
        "aiohttp",
        "websocket",
        "wallet",
        "clob",
        "nacl",
        "cryptography",
        "subprocess",
    )
    for modname in imported_full:
        low = modname.lower()
        for tok in forbidden_substrings:
            assert tok not in low, f"forbidden dependency imported: {modname}"


# passive-only: a valid result is a plain immutable record, not an authorization handle
def test_verification_result_is_passive_immutable():
    pkg = canonical_package_bytes(_valid_fields())
    res = verify_approval_package(
        pkg,
        public_key=_PUBLIC_KEY,
        pinned_public_key_fingerprint=_pinned(),
        signature=_SIGNATURE,
        signature_verifier=_accept_verifier,
    )
    # frozen dataclass: no mutation, exactly two passive fields
    with pytest.raises(Exception):
        res.valid = False  # type: ignore[misc]
    assert set(vars(res).keys()) == {"valid", "reason"}
