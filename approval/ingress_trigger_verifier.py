"""approval/ingress_trigger_verifier.py — isolated Ingress, Authentication & CLI/API Trigger
Candidate Verification (pure library only).

This is the verification layer bounded by the ratified Ingress, Authentication & CLI/API Trigger
Boundary Charter. Core doctrine, enforced structurally: **external ingress is not execution and not
authorization.** A caller-supplied external trigger command candidate may, at most, become a
**passive, frozen, digest-bound, non-executable** verified candidate for separate later review. A
shape pass, a parse pass, an auth pass, or a valid signature is each **evidence only** — never an S1
append authorization.

What this module is, and is NOT, by construction:
  * It is a set of pure functions over caller-supplied data. It builds **no** CLI / argument parser /
    web framework / network listener / server / port / bot / callback endpoint, opens **no** file or
    database, makes **no** network call, reads **no** secret / wallet / private key / environment, and
    has **no** auto-run entrypoint. There is no transport here at all; transport facts are merely
    *described* by the caller so a transport-implied trigger can be rejected.
  * It **never** calls the append circuit, the writer, the initializer, a stream, or a production DB.
    It cannot: it imports none of them. Every authority flag it emits is hard-coded ``False``.
  * It invents **no** cryptography and adds **no** dependency. It reuses ONLY ratified primitives: the
    trust-anchor validator, the pinned production-verifier registry, and the public-key-only detached
    signature check (an injected ``(public_key, message, signature) -> bool`` verifier, exactly as the
    ratified package verifier consumes). The VPS holds no private key; signing is off-VPS.

Replay/freshness boundary: this slice does not own durable replay state and creates no replay DB. It
requires **caller-supplied replay-preflight evidence** bound to this exact command_digest / nonce /
sequence; absent such evidence it returns ``BLOCKED_REPLAY_STATE_NOT_RATIFIED`` rather than pretending
replay is solved. Freshness must be an explicit binding (no wall-clock-only trust); no clock is read.

The output is PASSIVE: a frozen ``IngressVerificationResult``. ``VERIFIED_PASSIVE_CANDIDATE`` is NOT
``AUTHORIZED``; it authorizes no S1 append, no stream, no trade, no capacity, no wallet/signing. Any
hand-off from a verified candidate to an execution review is a separate, explicitly commanded step —
never an in-line call from here.
"""
from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass
from typing import Callable, Optional

from approval import package_verifier as _pkg
from approval import trust_anchor as _anchor
from approval import verifier_registry as _registry

# Result status vocabulary.
VERIFIED_PASSIVE_CANDIDATE = "VERIFIED_PASSIVE_CANDIDATE"
BLOCKED = "BLOCKED"
BLOCKED_REPLAY_STATE_NOT_RATIFIED = "BLOCKED_REPLAY_STATE_NOT_RATIFIED"
BLOCKED_MISSING_RATIFIED_VERIFIER = "BLOCKED_MISSING_RATIFIED_VERIFIER"

_STATEMENT = "verified ingress candidate is evidence, not S1 append authorization"

# Required non-empty command fields (Gate D). ``command_digest`` is checked separately (it is the
# binding digest of the rest); ``raw_db_path`` must be EMPTY; ``asserted_authority`` must be EMPTY.
_REQUIRED_NONEMPTY_FIELDS = (
    "operator_command_id",
    "operator_identity_reference",
    "command_scope",
    "target_circuit_digest",
    "decision_result_digest",
    "initializer_result_digest",
    "writer_expectation_digest",
    "db_path_digest",
    "s1_target",
    "evidence_digest",
    "canonical_payload_digest",
    "approval_row_digest",
    "freshness_binding_digest",
    "immutable_snapshot_ref",
    "request_timestamp_reference",
    "replay_protection_nonce",
    "replay_protection_sequence",
)

# Cross-binding: (candidate attr, expected-binding attr, mismatch reason).
_CROSS_BINDINGS = (
    ("command_scope", "command_scope", "command_scope_mismatch"),
    ("target_circuit_digest", "target_circuit_digest", "target_circuit_digest_mismatch"),
    ("decision_result_digest", "decision_result_digest", "decision_result_digest_mismatch"),
    ("initializer_result_digest", "initializer_result_digest", "initializer_result_digest_mismatch"),
    ("writer_expectation_digest", "writer_expectation_digest", "writer_expectation_digest_mismatch"),
    ("db_path_digest", "db_path_digest", "db_path_digest_mismatch"),
    ("s1_target", "s1_target", "s1_target_mismatch"),
    ("evidence_digest", "evidence_digest", "evidence_digest_mismatch"),
    ("canonical_payload_digest", "canonical_payload_digest", "canonical_payload_digest_mismatch"),
    ("approval_row_digest", "approval_row_digest", "approval_row_digest_mismatch"),
    ("freshness_binding_digest", "freshness_binding_digest", "freshness_binding_mismatch"),
    ("immutable_snapshot_ref", "immutable_snapshot_ref", "immutable_snapshot_ref_mismatch"),
)

# Substrings that, in a command scope or an asserted-authority field, signal authority escalation.
# (The legitimate review scope "S1_APPEND_CANDIDATE_REVIEW" contains none of these.)
_FORBIDDEN_AUTHORITY_TOKENS = (
    "authorized",
    "trading",
    "capacity",
    "wallet",
    "signing",
    "live_execute",
    "canary",
    "paper_live",
    "production_append",
    "execution_token",
    "stream_start",
    "capital",
)

_EXPLICIT_FRESHNESS_KIND = "EXPLICIT_BINDING"


@dataclass(frozen=True)
class IngressTriggerCandidate:
    """Immutable, caller-supplied external trigger command candidate. Passive; authorizes nothing."""

    operator_command_id: str
    operator_identity_reference: str
    command_scope: str
    target_circuit_digest: str
    decision_result_digest: str
    initializer_result_digest: str
    writer_expectation_digest: str
    db_path_digest: str
    s1_target: str
    evidence_digest: str
    canonical_payload_digest: str
    approval_row_digest: str
    freshness_binding_digest: str
    immutable_snapshot_ref: str
    request_timestamp_reference: str
    replay_protection_nonce: str
    replay_protection_sequence: str
    command_digest: str
    raw_db_path: str = ""
    freshness_evidence_kind: str = _EXPLICIT_FRESHNESS_KIND
    asserted_authority: str = ""


@dataclass(frozen=True)
class ExpectedBindings:
    """Server-side pinned values the candidate is bound against. Mismatch fails closed."""

    command_scope: str
    target_circuit_digest: str
    decision_result_digest: str
    initializer_result_digest: str
    writer_expectation_digest: str
    db_path_digest: str
    s1_target: str
    evidence_digest: str
    canonical_payload_digest: str
    approval_row_digest: str
    freshness_binding_digest: str
    immutable_snapshot_ref: str


@dataclass(frozen=True)
class TransportContext:
    """Caller-described transport facts. Any forbidden implication fails closed. No transport here."""

    used_default_route: bool = False
    unauthenticated_cli_shortcut: bool = False
    env_authority_asserted: bool = False
    bearer_token_only_authority: bool = False
    listener_opened: bool = False
    framework_introduced: bool = False


@dataclass(frozen=True)
class ReplayPreflight:
    """Caller-supplied replay-preflight evidence. Binds to this exact command_digest/nonce/sequence."""

    durable_store_ref: str
    checked_command_digest: str
    checked_nonce: str
    checked_sequence: str
    uniqueness_confirmed: bool


@dataclass(frozen=True)
class VerifiedCandidate:
    """Passive, frozen, non-executable verified candidate. Authorizes NOTHING."""

    operator_command_id: str
    command_scope: str
    command_digest: str
    candidate_digest: str
    statement: str = _STATEMENT
    s1_append_authorized: bool = False
    production_stream_authorized: bool = False
    trading_authorized: bool = False
    capacity_enabled: bool = False
    wallet_authorized: bool = False
    execution_token_created: bool = False
    circuit_invoked: bool = False
    db_created: bool = False


@dataclass(frozen=True)
class IngressVerificationResult:
    """Passive, immutable ingress verification outcome. Authorizes nothing in production."""

    status: str
    reason: str
    candidate_digest: str = ""
    verified_candidate: Optional[VerifiedCandidate] = None
    s1_append_authorized: bool = False
    production_stream_authorized: bool = False
    trading_authorized: bool = False
    capacity_enabled: bool = False
    wallet_authorized: bool = False
    execution_token_created: bool = False
    circuit_invoked: bool = False
    db_created: bool = False


def canonical_command_bytes(candidate: IngressTriggerCandidate) -> bytes:
    """Deterministic canonical bytes of the candidate, EXCLUDING ``command_digest``.

    Reuses the ratified canonical encoder so the off-VPS signer and the VPS verifier canonicalize
    identically. ``command_digest`` is the digest of exactly these bytes."""
    fields = dataclasses.asdict(candidate)
    fields.pop("command_digest", None)
    return _pkg.canonical_package_bytes(fields)


def compute_command_digest(candidate: IngressTriggerCandidate) -> str:
    """SHA256 of the canonical command bytes. Pure; binds every field except the digest itself."""
    return hashlib.sha256(canonical_command_bytes(candidate)).hexdigest()


def _candidate_digest(candidate: IngressTriggerCandidate) -> str:
    parts = [
        "KIND=verified_passive_ingress_candidate",
        f"command_digest={candidate.command_digest}",
        f"operator_command_id={candidate.operator_command_id}",
        f"operator_identity_reference={candidate.operator_identity_reference}",
        f"command_scope={candidate.command_scope}",
        f"target_circuit_digest={candidate.target_circuit_digest}",
        f"s1_target={candidate.s1_target}",
        "s1_append_authorized=False",
        f"statement={_STATEMENT}",
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _blocked(status: str, reason: str) -> IngressVerificationResult:
    return IngressVerificationResult(status=status, reason=reason)


def _transport_reason(transport: TransportContext) -> str:
    if transport.used_default_route:
        return "default_route_forbidden"
    if transport.unauthenticated_cli_shortcut:
        return "unauthenticated_cli_shortcut_forbidden"
    if transport.env_authority_asserted:
        return "env_authority_forbidden"
    if transport.bearer_token_only_authority:
        return "bearer_only_authority_forbidden"
    if transport.listener_opened:
        return "listener_forbidden"
    if transport.framework_introduced:
        return "framework_introduced_forbidden"
    return ""


def verify_ingress_trigger_candidate(
    *,
    candidate: IngressTriggerCandidate,
    command_bytes: bytes,
    signature: bytes,
    public_key: bytes,
    pinned_public_key_fingerprint: str,
    signature_verifier: Optional[Callable[[bytes, bytes, bytes], bool]],
    trust_anchor_artifact,
    operator_allowlist,
    verifier_identity,
    verifier_version: str,
    verifier_fingerprint: str,
    verifier_registry,
    replay_preflight: Optional[ReplayPreflight],
    expected_bindings: ExpectedBindings,
    transport_context: TransportContext,
) -> IngressVerificationResult:
    """Verify an external trigger command candidate into a passive verified candidate, or fail closed.

    Pure and side-effect-free: no DB, no file, no network, no circuit/writer/initializer call. Returns
    ``VERIFIED_PASSIVE_CANDIDATE`` only when every gate passes — and even then authorizes nothing.
    """
    # 0. A ratified public-key-only verifier must exist and be pinned; otherwise fail closed loudly.
    if signature_verifier is None or not callable(signature_verifier):
        return _blocked(BLOCKED_MISSING_RATIFIED_VERIFIER, "no_ratified_signature_verifier")
    resolved = _registry.resolve_production_verifier(
        verifier_identity,
        version=verifier_version,
        fingerprint=verifier_fingerprint,
        registry=verifier_registry,
    )
    if not resolved.valid:
        return _blocked(BLOCKED_MISSING_RATIFIED_VERIFIER, resolved.reason or "verifier_not_ratified")

    # 1. Transport implication — a default route / CLI shortcut / env / bearer-only / listener /
    #    framework-implied trigger fails closed regardless of how well-formed the candidate is.
    treason = _transport_reason(transport_context)
    if treason:
        return _blocked(BLOCKED, treason)

    # 2. Shape — every required command field must be present and non-empty (necessary, not sufficient).
    for field in _REQUIRED_NONEMPTY_FIELDS:
        if not getattr(candidate, field):
            return _blocked(BLOCKED, "missing_required_field")
    if not candidate.command_digest:
        return _blocked(BLOCKED, "missing_required_field")

    # 3. No raw mutable path — only a path DIGEST is permitted (Gate L #14).
    if candidate.raw_db_path:
        return _blocked(BLOCKED, "raw_path_supplied")

    # 4. Explicit freshness only — no wall-clock-only trust.
    if candidate.freshness_evidence_kind != _EXPLICIT_FRESHNESS_KIND:
        return _blocked(BLOCKED, "wall_clock_only_freshness_forbidden")

    # 5. Authority escalation — no asserted authority, no authority token in scope (even if pinned).
    if candidate.asserted_authority:
        return _blocked(BLOCKED, "authority_escalation")
    low_scope = candidate.command_scope.lower()
    if any(tok in low_scope for tok in _FORBIDDEN_AUTHORITY_TOKENS):
        return _blocked(BLOCKED, "authority_escalation")

    # 6. Cross-binding — candidate fields must equal the server-side pinned bindings.
    for cand_attr, exp_attr, reason in _CROSS_BINDINGS:
        if getattr(candidate, cand_attr) != getattr(expected_bindings, exp_attr):
            return _blocked(BLOCKED, reason)

    # 7. command_digest must recompute exactly over the candidate's canonical bytes.
    recomputed_canonical = canonical_command_bytes(candidate)
    if candidate.command_digest != hashlib.sha256(recomputed_canonical).hexdigest():
        return _blocked(BLOCKED, "command_digest_mismatch")

    # 8. Anti-blind-signing — the shown/signed bytes must equal the candidate's canonical bytes.
    if command_bytes != recomputed_canonical:
        return _blocked(BLOCKED, "blind_signing_shown_bytes_mismatch")

    # 9. Trust anchor — the Day-Zero pinned public-key root must validate.
    anchor_result = _anchor.validate_trust_anchor_artifact(trust_anchor_artifact)
    if not anchor_result.valid:
        return _blocked(BLOCKED, "trust_anchor_invalid")
    if trust_anchor_artifact.get("public_key_fingerprint") != pinned_public_key_fingerprint:
        return _blocked(BLOCKED, "anchor_key_binding_mismatch")

    # 10. Operator identity must be explicitly allowlisted (pinned), not discovered.
    if candidate.operator_identity_reference not in operator_allowlist:
        return _blocked(BLOCKED, "operator_not_allowlisted")

    # 11. Pinned public-key integrity — a silent key swap fails closed.
    if _pkg.public_key_fingerprint(public_key) != pinned_public_key_fingerprint:
        return _blocked(BLOCKED, "public_key_fingerprint_mismatch")

    # 12. Detached, public-key-only signature over the exact canonical command bytes.
    if not signature:
        return _blocked(BLOCKED, "signature_missing")
    if signature_verifier(public_key, command_bytes, signature) is not True:
        return _blocked(BLOCKED, "signature_verification_failed")

    # 13. Replay — caller-supplied preflight evidence bound to this exact command; else NOT RATIFIED.
    if replay_preflight is None or not replay_preflight.durable_store_ref:
        return _blocked(BLOCKED_REPLAY_STATE_NOT_RATIFIED, "replay_state_not_ratified")
    if (
        replay_preflight.checked_command_digest != candidate.command_digest
        or replay_preflight.checked_nonce != candidate.replay_protection_nonce
        or replay_preflight.checked_sequence != candidate.replay_protection_sequence
    ):
        return _blocked(BLOCKED, "replay_preflight_mismatch")
    if replay_preflight.uniqueness_confirmed is not True:
        return _blocked(BLOCKED, "replay_detected")

    # All gates clean: emit a PASSIVE verified candidate. This authorizes nothing.
    candidate_digest = _candidate_digest(candidate)
    verified = VerifiedCandidate(
        operator_command_id=candidate.operator_command_id,
        command_scope=candidate.command_scope,
        command_digest=candidate.command_digest,
        candidate_digest=candidate_digest,
    )
    return IngressVerificationResult(
        status=VERIFIED_PASSIVE_CANDIDATE,
        reason="",
        candidate_digest=candidate_digest,
        verified_candidate=verified,
    )
