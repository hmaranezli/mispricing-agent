"""approval/package_verifier.py — air-gapped approval package verification boundary (public-key only).

This is the VPS-side boundary for a future operator-approval mechanism. It enforces, as pure
functions with NO side effects and NO new dependency:

  * Inert payload integrity: the approval package must be EXACT canonical bytes. Any corrupted byte,
    whitespace/newline shift, non-canonical formatting, missing required field, or unauthorized extra
    field FAILS CLOSED. (Gemini concern #1.)
  * Public-key integrity lock: the resident public key is pinned by its sha256 fingerprint. A silent
    public-key swap/overwrite FAILS CLOSED on fingerprint mismatch. (Gemini concern #2.)
  * Public-key-ONLY verification: the signature check is delegated to an injected verifier callable
    of shape ``(public_key, message, signature) -> bool``. There is NO parameter, and no module
    surface, through which a private key, seed, or signing primitive can enter this verifier. The
    private key is structurally impossible to pass into the VPS API.

The output is PASSIVE: a frozen ``VerificationResult(valid, reason)``. A ``valid=True`` result
authorizes NOTHING — no S1 append, no matrix construction, no paper/live, no trading, no wallet/
signing, no capacity. Downstream authority requires separately ratified gates and an explicit
operator command.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable

# Closed approval-package schema. The set is exact: a package must carry EXACTLY these keys.
REQUIRED_FIELDS = frozenset(
    {
        "approval_record_id",
        "operator_identity_class",
        "exact_command_text",
        "command_scope",
        "target_commit_sha",
        "target_ledger_identity",
        "target_s1_identity",
        "timestamp_utc",
        "nonce",
        "expiry_utc",
    }
)


@dataclass(frozen=True)
class VerificationResult:
    """Passive, immutable verification outcome. Never an authorization handle."""

    valid: bool
    reason: str


def public_key_fingerprint(public_key: bytes) -> str:
    """Pinned-integrity fingerprint of a public key (sha256 hex). Public material only."""
    return hashlib.sha256(public_key).hexdigest()


def canonical_package_bytes(fields: dict) -> bytes:
    """Deterministic canonical encoding of an approval package (sorted keys, compact separators).

    The offline signer and the VPS verifier must canonicalize identically; this is the single
    canonical form against which inert transferred bytes are compared.
    """
    return json.dumps(
        fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def verify_approval_package(
    package_bytes: bytes,
    *,
    public_key: bytes,
    pinned_public_key_fingerprint: str,
    signature: bytes,
    signature_verifier: Callable[[bytes, bytes, bytes], bool],
) -> VerificationResult:
    """Verify an inert offline-signed approval package using the public key only.

    Fails closed (``valid=False`` with a reason) on ANY mismatch. Returns ``valid=True`` only when
    every gate passes — and even then authorizes nothing.
    """
    # 1. Parse — malformed bytes fail closed.
    try:
        parsed = json.loads(package_bytes)
    except (ValueError, UnicodeDecodeError):
        return VerificationResult(False, "malformed_package")
    if not isinstance(parsed, dict):
        return VerificationResult(False, "malformed_package")

    # 2. Exact canonical bytes — any whitespace/newline/byte/canonicalization shift fails closed.
    if canonical_package_bytes(parsed) != package_bytes:
        return VerificationResult(False, "non_canonical_bytes")

    # 3. Closed schema — missing or unauthorized extra field fails closed.
    keys = set(parsed.keys())
    if keys - REQUIRED_FIELDS:
        return VerificationResult(False, "unauthorized_extra_field")
    if REQUIRED_FIELDS - keys:
        return VerificationResult(False, "missing_required_field")

    # 4. Pinned public-key integrity — silent swap/overwrite fails closed.
    if public_key_fingerprint(public_key) != pinned_public_key_fingerprint:
        return VerificationResult(False, "public_key_fingerprint_mismatch")

    # 5. Public-key-only signature verification — rejection fails closed.
    if signature_verifier(public_key, package_bytes, signature) is not True:
        return VerificationResult(False, "signature_verification_failed")

    return VerificationResult(True, "")
