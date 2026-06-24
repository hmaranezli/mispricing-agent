"""tests/test_trust_anchor_verifier_wiring.py — Day-Zero trust-anchor provisioning + production
crypto verifier wiring slice (TDD).

İki ratifiye sınırı fiziksel olarak zorlar (stdlib-only, yeni bağımlılık YOK, pasif):

  1. Production verifier wiring keyfi enjekte callable / lambda / mock / dummy / always-true KABUL
     ETMEZ. Üretim çözümü YALNIZCA açıkça pinlenmiş verifier kimliklerine izin verir; bilinmeyen /
     eksik / unpinned kimlik, sürüm/fingerprint uyuşmazlığı, callable enjeksiyonu, lambda, ve
     production modunda mock/test verifier → fail closed.
  2. Day-Zero trust-anchor artifact deterministik bir şekle sahip olmalı ve pinlenmiş public-key
     fingerprint mevcut + immutable değilse fail closed olmalı; eksik/malformed fingerprint, mutable
     / non-final state, eksik ceremony evidence, yasaklı trust source (network/model/config/self),
     ambiguous rotation/revocation → fail closed.

Çıktı PASİF: valid/invalid + deterministik reason. HİÇBİR sonuç DB/S1/matrix/paper/live/trading/
wallet/capacity yetkilendirmez.

İlk RED: approval.verifier_registry / approval.trust_anchor yok → ImportError (eksik üretim seam'i).
"""
import ast
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval.trust_anchor import (
    AnchorResult,
    REQUIRED_ANCHOR_FIELDS,
    validate_trust_anchor_artifact,
)
from approval.verifier_registry import (
    PinnedVerifier,
    ResolveResult,
    resolve_production_verifier,
)

_FP = "a" * 64  # well-formed sha256-shaped fingerprint


def _registry():
    """Production registry: only explicitly pinned identities (one real, one test-only)."""
    return {
        "ed25519_detached_v1": PinnedVerifier(
            identity="ed25519_detached_v1", version="1", fingerprint=_FP, test_only=False
        ),
        "mock_verifier_v1": PinnedVerifier(
            identity="mock_verifier_v1", version="1", fingerprint=_FP, test_only=True
        ),
        "unpinned_v1": PinnedVerifier(
            identity="unpinned_v1", version="1", fingerprint="", test_only=False
        ),
    }


# ---------- production verifier registry ----------

# 1 — valid pinned production verifier identity resolves
def test_valid_pinned_identity_resolves():
    res = resolve_production_verifier(
        "ed25519_detached_v1", version="1", fingerprint=_FP, registry=_registry()
    )
    assert isinstance(res, ResolveResult)
    assert res.valid is True
    assert res.reason == ""
    assert res.identity == "ed25519_detached_v1"


# 2 — unknown verifier identity fails closed
def test_unknown_identity_fails_closed():
    res = resolve_production_verifier(
        "does_not_exist", version="1", fingerprint=_FP, registry=_registry()
    )
    assert res.valid is False
    assert res.reason == "unknown_verifier_identity"


# 2b — missing verifier identity fails closed
def test_missing_identity_fails_closed():
    res = resolve_production_verifier(
        "", version="1", fingerprint=_FP, registry=_registry()
    )
    assert res.valid is False
    assert res.reason == "missing_verifier_identity"


# 2c — unpinned verifier identity (registered but no fingerprint) fails closed
def test_unpinned_identity_fails_closed():
    res = resolve_production_verifier(
        "unpinned_v1", version="1", fingerprint=_FP, registry=_registry()
    )
    assert res.valid is False
    assert res.reason == "unpinned_verifier_identity"


# 3 — callable injection attempt fails closed
def test_callable_injection_fails_closed():
    def sneaky_verifier(pub, msg, sig):
        return True

    res = resolve_production_verifier(
        sneaky_verifier, version="1", fingerprint=_FP, registry=_registry()
    )
    assert res.valid is False
    assert res.reason == "callable_injection"


# 4 — lambda/anonymous verifier fails closed
def test_lambda_verifier_fails_closed():
    res = resolve_production_verifier(
        lambda pub, msg, sig: True, version="1", fingerprint=_FP, registry=_registry()
    )
    assert res.valid is False
    assert res.reason == "anonymous_verifier_rejected"


# 5 — mock/test verifier rejected in production mode
def test_mock_verifier_rejected_in_production():
    res = resolve_production_verifier(
        "mock_verifier_v1", version="1", fingerprint=_FP, registry=_registry()
    )
    assert res.valid is False
    assert res.reason == "test_verifier_rejected_in_production"


# 6 — verifier version mismatch fails closed
def test_verifier_version_mismatch_fails_closed():
    res = resolve_production_verifier(
        "ed25519_detached_v1", version="2", fingerprint=_FP, registry=_registry()
    )
    assert res.valid is False
    assert res.reason == "verifier_version_mismatch"


# 6b — verifier fingerprint mismatch fails closed
def test_verifier_fingerprint_mismatch_fails_closed():
    res = resolve_production_verifier(
        "ed25519_detached_v1", version="1", fingerprint="b" * 64, registry=_registry()
    )
    assert res.valid is False
    assert res.reason == "verifier_fingerprint_mismatch"


# ---------- Day-Zero trust-anchor artifact ----------

def _valid_anchor():
    return {
        "public_key_fingerprint": _FP,
        "artifact_state": "FINAL",
        "ceremony_evidence_marker": "DAY_ZERO_CEREMONY_2026-06-24_witnessed",
        "trust_source": "OFFLINE_AIR_GAPPED_CEREMONY",
        "rotation_state": "ACTIVE_SINGLE",
        "revocation_state": "NONE",
    }


# 7 — valid Day-Zero trust-anchor artifact validates
def test_valid_trust_anchor_validates():
    res = validate_trust_anchor_artifact(_valid_anchor())
    assert isinstance(res, AnchorResult)
    assert res.valid is True
    assert res.reason == ""


# 8 — missing public key fingerprint fails closed
def test_missing_fingerprint_fails_closed():
    a = _valid_anchor()
    a["public_key_fingerprint"] = ""
    res = validate_trust_anchor_artifact(a)
    assert res.valid is False
    assert res.reason == "missing_public_key_fingerprint"


# 9 — malformed fingerprint fails closed
def test_malformed_fingerprint_fails_closed():
    a = _valid_anchor()
    a["public_key_fingerprint"] = "XYZ-not-hex"
    res = validate_trust_anchor_artifact(a)
    assert res.valid is False
    assert res.reason == "malformed_fingerprint"


# 10 — mutable/non-final artifact state fails closed
def test_non_final_artifact_state_fails_closed():
    a = _valid_anchor()
    a["artifact_state"] = "DRAFT"
    res = validate_trust_anchor_artifact(a)
    assert res.valid is False
    assert res.reason == "mutable_or_non_final_artifact"


# 11 — forbidden trust source marker fails closed
def test_forbidden_trust_source_fails_closed():
    for bad in ("NETWORK_FETCHED", "MODEL_DERIVED", "CONFIG_DERIVED", "SERVER_SELF_GENERATED"):
        a = _valid_anchor()
        a["trust_source"] = bad
        res = validate_trust_anchor_artifact(a)
        assert res.valid is False, bad
        assert res.reason == "forbidden_trust_source", bad


# 12 — ambiguous rotation/revocation state fails closed
def test_ambiguous_rotation_revocation_fails_closed():
    a = _valid_anchor()
    a["rotation_state"] = "AMBIGUOUS"
    res = validate_trust_anchor_artifact(a)
    assert res.valid is False
    assert res.reason == "ambiguous_rotation_state"

    b = _valid_anchor()
    b["revocation_state"] = "MAYBE"
    res2 = validate_trust_anchor_artifact(b)
    assert res2.valid is False
    assert res2.reason == "ambiguous_revocation_state"


# 12b — unauthorized extra field fails closed
def test_extra_field_fails_closed():
    a = _valid_anchor()
    a["inject_capacity"] = "1"
    res = validate_trust_anchor_artifact(a)
    assert res.valid is False
    assert res.reason == "unauthorized_extra_field"


# ---------- passivity & isolation ----------

# 13 — output remains passive and non-authorizing (frozen, two fields only)
def test_outputs_are_passive_immutable():
    r = resolve_production_verifier(
        "ed25519_detached_v1", version="1", fingerprint=_FP, registry=_registry()
    )
    a = validate_trust_anchor_artifact(_valid_anchor())
    with pytest.raises(Exception):
        r.valid = False  # type: ignore[misc]
    with pytest.raises(Exception):
        a.valid = False  # type: ignore[misc]
    assert set(vars(a).keys()) == {"valid", "reason"}
    # ResolveResult carries only passive descriptive fields, never a callable handle
    assert set(vars(r).keys()) <= {"valid", "reason", "identity"}
    for v in vars(r).values():
        assert not callable(v)


# 14 — slice imports no forbidden dependency or S1/raw/network/wallet modules
def test_slice_imports_no_forbidden_dependency():
    import approval.trust_anchor as ta
    import approval.verifier_registry as vr

    allowed_top = {"re", "hashlib", "dataclasses", "typing", "__future__"}
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
        "os",
    )
    for mod in (ta, vr):
        tree = ast.parse(inspect.getsource(mod))
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
        assert imported_top <= allowed_top, f"{mod.__name__}: unexpected {imported_top - allowed_top}"
        for modname in imported_full:
            low = modname.lower()
            for tok in forbidden_substrings:
                assert tok not in low, f"{mod.__name__}: forbidden import {modname}"
