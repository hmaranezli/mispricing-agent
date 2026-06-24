"""approval/signing_payload_return.py — passive signing payload + presentation fidelity + air-gapped
signature return + preflight-gated approval-ledger bridge.

This integrative slice ties the ratified passive components together WITHOUT creating any authority:

  * ``build_signing_payload`` produces DETERMINISTIC canonical bytes from a ReviewPackage and a
    structured signing intent. The caller supplies only ids/scope/identity/fingerprint — never a
    digest, display text, waiver, override, policy, command, token, or authority flag. The payload
    embeds the matrix digest, the review-package digest, no-authority flags, and the literal
    "signature is evidence, not S1 authorization".
  * ``render_presentation`` derives the visible text from the EXACT canonical bytes (anti-blind-
    signing): it shows the full canonical bytes and the full (untruncated) payload digest. It hides
    nothing and accepts no caller text.
  * ``SignatureReturn`` is inert, passive data (signature bytes + claimed digest + a passive
    verification flag). Importing/returning it executes nothing.
  * ``accept_signature_and_append`` verifies BEFORE accepting: payload-digest match, then a valid
    verification, then an ALLOWED append preflight — and only then performs EXACTLY ONE append into
    the existing isolated append-only approval ledger. Any failed gate returns before any write.

Every authority flag is hard-coded ``False``. This slice creates no S1 DB, performs no S1 append, no
production stream, no trading, no wallet/capital, and no capacity. It opens no file, makes no network
call, inspects no secret/key, and adds no delete/update/truncate API.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from approval import approval_ledger_db as _ledger

_EVIDENCE_STATEMENT = "signature is evidence, not S1 authorization"


@dataclass(frozen=True)
class SigningPayload:
    """Deterministic, canonical, non-executable signing payload. Authorizes nothing."""

    canonical_bytes: bytes
    payload_digest: str
    matrix_digest: str
    review_package_digest: str
    approval_record_id: str
    command_scope: str
    signer_identity_class: str
    public_key_fingerprint: str
    statement: str = _EVIDENCE_STATEMENT
    s1_append_authorized: bool = False
    production_stream_authorized: bool = False
    execution_token_created: bool = False
    trading_authorized: bool = False
    capacity_enabled: bool = False
    wallet_authorized: bool = False


@dataclass(frozen=True)
class Presentation:
    """Passive presentation derived from the exact canonical bytes (anti-blind-signing)."""

    canonical_bytes: bytes
    payload_digest: str
    visible_text: str


@dataclass(frozen=True)
class SignatureReturn:
    """Inert, passive air-gapped signature return. Executes nothing."""

    signer_identity_class: str
    claimed_payload_digest: str
    signature: bytes
    verification_valid: bool


@dataclass(frozen=True)
class BridgeResult:
    """Passive bridge outcome. Authorizes nothing."""

    appended: bool
    reason: str
    append_sequence: int = -1
    s1_append_authorized: bool = False
    production_stream_authorized: bool = False
    execution_token_created: bool = False
    trading_authorized: bool = False
    capacity_enabled: bool = False
    wallet_authorized: bool = False


def _review_package_digest(review_package) -> str:
    parts = [
        f"status={review_package.status}",
        f"reason={review_package.reason}",
        f"matrix_digest={review_package.matrix_digest}",
        f"summary={review_package.summary}",
        "warnings=" + "|".join(review_package.warnings),
        f"statement={review_package.reviewable_not_authorized_statement}",
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def build_signing_payload(
    *,
    review_package,
    approval_record_id: str,
    command_scope: str,
    signer_identity_class: str,
    public_key_fingerprint: str,
) -> SigningPayload:
    """Build deterministic canonical signing-payload bytes. Pure; authorizes nothing."""
    rp_digest = _review_package_digest(review_package)
    lines = [
        "PAYLOAD_KIND=non_executable_signing_payload",
        f"matrix_digest={review_package.matrix_digest}",
        f"review_package_digest={rp_digest}",
        f"review_package_status={review_package.status}",
        f"approval_record_id={approval_record_id}",
        f"command_scope={command_scope}",
        f"signer_identity_class={signer_identity_class}",
        f"public_key_fingerprint={public_key_fingerprint}",
        "s1_append_authorized=False",
        "production_stream_authorized=False",
        "execution_token_created=False",
        "trading_authorized=False",
        "capacity_enabled=False",
        "wallet_authorized=False",
        f"statement={_EVIDENCE_STATEMENT}",
    ]
    canonical_bytes = "\n".join(lines).encode("utf-8")
    payload_digest = hashlib.sha256(canonical_bytes).hexdigest()
    return SigningPayload(
        canonical_bytes=canonical_bytes,
        payload_digest=payload_digest,
        matrix_digest=review_package.matrix_digest,
        review_package_digest=rp_digest,
        approval_record_id=approval_record_id,
        command_scope=command_scope,
        signer_identity_class=signer_identity_class,
        public_key_fingerprint=public_key_fingerprint,
    )


def render_presentation(signing_payload: SigningPayload) -> Presentation:
    """Render the operator-visible text from the EXACT canonical bytes. Hides/truncates nothing."""
    visible_text = (
        signing_payload.canonical_bytes.decode("utf-8")
        + f"\nPAYLOAD_DIGEST={signing_payload.payload_digest}"
    )
    return Presentation(
        canonical_bytes=signing_payload.canonical_bytes,
        payload_digest=signing_payload.payload_digest,
        visible_text=visible_text,
    )


def accept_signature_and_append(
    db_path: str,
    *,
    signing_payload: SigningPayload,
    signature_return: SignatureReturn,
    verifier_result,
    trust_anchor_result,
    preflight_decision,
    ceremony_evidence_marker: str,
) -> BridgeResult:
    """Verify-before-accept, then append EXACTLY ONE passive record if all gates pass."""
    # Gate 1: payload digest must match what was signed (anti-blind-signing).
    if signature_return.claimed_payload_digest != signing_payload.payload_digest:
        return BridgeResult(False, "payload_digest_mismatch")
    # Gate 2: passive verification of the signature must be valid.
    if getattr(signature_return, "verification_valid", False) is not True:
        return BridgeResult(False, "missing_or_invalid_verification")
    # Gate 3: append preflight must be ALLOWED.
    if getattr(preflight_decision, "allowed", False) is not True:
        return BridgeResult(False, "append_preflight_denied")

    # Only now: one append via the existing isolated append-only ledger mechanism.
    result = _ledger.append_passive_record(
        db_path,
        verifier_result=verifier_result,
        trust_anchor_result=trust_anchor_result,
        approval_record_id=signing_payload.approval_record_id,
        command_scope=signing_payload.command_scope,
        public_key_fingerprint=signing_payload.public_key_fingerprint,
        ceremony_evidence_marker=ceremony_evidence_marker,
        status=_ledger.PASSIVE_STATUS,
    )
    if not result.valid:
        return BridgeResult(False, result.reason)
    return BridgeResult(True, "", result.append_sequence)
