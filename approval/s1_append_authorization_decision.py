"""approval/s1_append_authorization_decision.py — passive Production S1 Append Authorization decision.

This is a PURE value-object decision layer. It evaluates a caller-supplied passive evidence snapshot
and returns ``REVIEWABLE_FOR_S1_APPEND`` or ``BLOCKED`` with a deterministic reason list and an
evidence digest. It is the final non-promotion gate described by the ratified Production S1 Append
Authorization Boundary Charter.

Hard constraints honoured by construction:
  * Performs NO S1 append, creates NO S1 DB, opens NO file, makes NO network call, inspects NO
    secret / env, and uses NO wall-clock time. Freshness is an EXPLICIT caller-supplied snapshot
    field, never an implicit TTL/config/env value.
  * Mutates nothing; reads no DB, ledger, or payload body. Inputs are passive snapshots only.
  * Does partial-transaction recovery NEVER — a partial/interrupted marker simply fails closed.
  * Every authority flag on the output is hard-coded ``False``. A ``REVIEWABLE_FOR_S1_APPEND``
    decision is **never** ``AUTHORIZED`` and authorizes nothing; it only states the evidence is
    complete and fresh enough for a separate, future, explicitly-commanded S1 append review.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class S1AppendEvidenceSnapshot:
    """Immutable, caller-supplied passive evidence snapshot. No DB/file/network/clock inside."""

    approval_ledger_row_present: bool
    approval_row_append_only: bool
    canonical_payload_digest: str
    displayed_payload_digest: str
    signed_payload_digest: str
    approval_row_digest: str
    review_package_digest: str
    review_package_digest_expected: str
    matrix_state: str
    signature_present: bool
    signature_verifier_passed: bool
    preflight_allowed: bool
    payload_freshness_state: str
    signature_freshness_state: str
    canonical_payload_binding_present: bool
    operator_identity: str
    signer_identity: str
    signer_fingerprint_known: bool
    s1_target_known: bool
    s1_target_evidence_present: bool
    single_flight_lock_held: bool
    verification_interrupted: bool
    partial_transaction_marker: bool
    duplicate_evidence: bool
    replay_attempt: bool


@dataclass(frozen=True)
class S1AppendAuthorizationDecision:
    """Passive, immutable decision. Authorizes nothing."""

    status: str  # "REVIEWABLE_FOR_S1_APPEND" | "BLOCKED"
    reasons: tuple
    evidence_digest: str
    s1_append_authorized: bool = False
    production_stream_authorized: bool = False
    execution_token_created: bool = False
    trading_authorized: bool = False
    capacity_enabled: bool = False
    wallet_authorized: bool = False


def _evidence_digest(snapshot: S1AppendEvidenceSnapshot) -> str:
    parts = [f"{f.name}={getattr(snapshot, f.name)!r}" for f in fields(snapshot)]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def evaluate_s1_append_authorization(
    snapshot: S1AppendEvidenceSnapshot,
) -> S1AppendAuthorizationDecision:
    """Decide REVIEWABLE_FOR_S1_APPEND vs BLOCKED. Pure, passive, fail-closed; authorizes nothing."""
    reasons = []
    s = snapshot

    if not s.approval_ledger_row_present:
        reasons.append("missing_approval_ledger_row")
    if not s.approval_row_append_only:
        reasons.append("mutable_approval_row")
    if not s.canonical_payload_digest:
        reasons.append("missing_canonical_payload_digest")
    else:
        if s.displayed_payload_digest != s.canonical_payload_digest or (
            s.signed_payload_digest != s.canonical_payload_digest
        ):
            reasons.append("payload_digest_mismatch")
        if s.approval_row_digest != s.canonical_payload_digest:
            reasons.append("approval_row_digest_mismatch")
    if not s.review_package_digest:
        reasons.append("missing_review_package_digest")
    elif s.review_package_digest != s.review_package_digest_expected:
        reasons.append("review_package_digest_mismatch")

    if s.matrix_state == "AUTHORIZED":
        reasons.append("matrix_treated_as_authorized")
    elif s.matrix_state != "REVIEWABLE":
        reasons.append("matrix_not_reviewable")

    if not s.signature_present:
        reasons.append("missing_signature_evidence")
    if not s.signature_verifier_passed:
        reasons.append("signature_not_verifier_passed")
    if not s.preflight_allowed:
        reasons.append("preflight_not_allowed")

    if s.payload_freshness_state != "FRESH":
        reasons.append("stale_payload_evidence")
    if s.signature_freshness_state != "FRESH":
        reasons.append("stale_signature_return")

    if not s.canonical_payload_binding_present:
        reasons.append("hardware_digest_only_unbound")

    if not s.operator_identity or s.operator_identity == "AMBIGUOUS":
        reasons.append("ambiguous_operator_identity")
    if not s.signer_fingerprint_known:
        reasons.append("unknown_signer_fingerprint")

    if not s.s1_target_known:
        reasons.append("unknown_s1_target")
    if not s.s1_target_evidence_present:
        reasons.append("missing_s1_target_evidence")

    if not s.single_flight_lock_held:
        reasons.append("race_lock_unavailable")
    if s.verification_interrupted:
        reasons.append("interrupted_verification")
    if s.partial_transaction_marker:
        reasons.append("partial_transaction")
    if s.duplicate_evidence:
        reasons.append("duplicate_approval_evidence")
    if s.replay_attempt:
        reasons.append("duplicate_retry_replay")

    digest = _evidence_digest(s)
    status = "REVIEWABLE_FOR_S1_APPEND" if not reasons else "BLOCKED"
    return S1AppendAuthorizationDecision(
        status=status, reasons=tuple(reasons), evidence_digest=digest
    )
