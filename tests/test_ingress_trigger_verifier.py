"""tests/test_ingress_trigger_verifier.py — isolated Ingress, Authentication & CLI/API Trigger
Candidate Verification slice (TDD).

This slice implements ONLY the pure, library-side verification layer for an externally-arriving
trigger command candidate, as bounded by the ratified Ingress, Authentication & CLI/API Trigger
Boundary Charter. Core doctrine: external ingress is NOT execution and NOT authorization. A perfectly
shaped, perfectly signed, allowlisted candidate becomes, at most, a passive, frozen, digest-bound,
NON-EXECUTABLE verified candidate — never an S1 append authorization.

It builds NO CLI / arg parser / web framework / network listener / server / port / bot / callback,
opens NO DB, performs NO S1 append, invokes NO circuit / writer / initializer, and emits NO authority
flag. It reuses ONLY ratified crypto/trust primitives (trust_anchor, verifier_registry,
package_verifier public-key-only verification) — it invents NO crypto and adds NO dependency.

First RED: approval.ingress_trigger_verifier does not exist -> ImportError (missing production seam).
"""
import dataclasses
import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval import ingress_trigger_verifier as itv
from approval import verifier_registry as _vr

_PUBLIC_KEY = b"ED25519-PUBLIC-KEY-BYTES-EXAMPLE-ONLY"
_SENTINEL = object()


def _sigver(public_key, message, signature):
    """Injected, public-key-only, detached-signature verifier (test stand-in for air-gapped check)."""
    return signature == hashlib.sha256(public_key + message).digest()


def _base_candidate(**over):
    fields = dict(
        operator_command_id="opcmd-1",
        operator_identity_reference="operator://ops-lead",
        command_scope="S1_APPEND_CANDIDATE_REVIEW",
        target_circuit_digest="t_circuit_digest",
        decision_result_digest="d_decision_digest",
        initializer_result_digest="i_initializer_digest",
        writer_expectation_digest="w_writer_digest",
        db_path_digest="dbp_digest",
        s1_target="BTC-UPDN-5M-W0001",
        evidence_digest="ev_digest",
        canonical_payload_digest="cp_digest",
        approval_row_digest="ar_digest",
        freshness_binding_digest="fb_digest",
        immutable_snapshot_ref="snap-ref-0001",
        request_timestamp_reference="ts-ref-0001",
        replay_protection_nonce="nonce-0001",
        replay_protection_sequence="seq-0001",
        command_digest="",
        raw_db_path="",
        freshness_evidence_kind="EXPLICIT_BINDING",
        asserted_authority="",
    )
    explicit_digest = "command_digest" in over
    fields.update(over)
    cand = itv.IngressTriggerCandidate(**fields)
    if not explicit_digest:
        cand = dataclasses.replace(cand, command_digest=itv.compute_command_digest(cand))
    return cand


def _bindings(cand):
    return itv.ExpectedBindings(
        command_scope=cand.command_scope,
        target_circuit_digest=cand.target_circuit_digest,
        decision_result_digest=cand.decision_result_digest,
        initializer_result_digest=cand.initializer_result_digest,
        writer_expectation_digest=cand.writer_expectation_digest,
        db_path_digest=cand.db_path_digest,
        s1_target=cand.s1_target,
        evidence_digest=cand.evidence_digest,
        canonical_payload_digest=cand.canonical_payload_digest,
        approval_row_digest=cand.approval_row_digest,
        freshness_binding_digest=cand.freshness_binding_digest,
        immutable_snapshot_ref=cand.immutable_snapshot_ref,
    )


def _anchor(pinned_fp):
    return {
        "public_key_fingerprint": pinned_fp,
        "artifact_state": "FINAL",
        "ceremony_evidence_marker": "ceremony-2026-01-01",
        "trust_source": "OFFLINE_AIR_GAPPED_CEREMONY",
        "rotation_state": "ACTIVE_SINGLE",
        "revocation_state": "NONE",
    }


def _registry():
    return {
        "ops_gpg_verifier": _vr.PinnedVerifier(
            identity="ops_gpg_verifier", version="v3", fingerprint="vfp-123"
        )
    }


def _replay(cand):
    return itv.ReplayPreflight(
        durable_store_ref="replay-store://ratified-durable-1",
        checked_command_digest=cand.command_digest,
        checked_nonce=cand.replay_protection_nonce,
        checked_sequence=cand.replay_protection_sequence,
        uniqueness_confirmed=True,
    )


def _call(
    candidate=None,
    *,
    bindings=None,
    command_bytes=None,
    signature=None,
    public_key=_PUBLIC_KEY,
    pinned_fp=None,
    signature_verifier=_sigver,
    trust_anchor_artifact=None,
    operator_allowlist=None,
    verifier_identity="ops_gpg_verifier",
    verifier_version="v3",
    verifier_fingerprint="vfp-123",
    verifier_registry=None,
    replay_preflight=_SENTINEL,
    transport_context=None,
):
    cand = candidate if candidate is not None else _base_candidate()
    if pinned_fp is None:
        pinned_fp = hashlib.sha256(public_key).hexdigest()
    if bindings is None:
        bindings = _bindings(cand)
    if command_bytes is None:
        command_bytes = itv.canonical_command_bytes(cand)
    if signature is None:
        signature = hashlib.sha256(public_key + command_bytes).digest()
    if trust_anchor_artifact is None:
        trust_anchor_artifact = _anchor(pinned_fp)
    if operator_allowlist is None:
        operator_allowlist = frozenset({cand.operator_identity_reference})
    if verifier_registry is None:
        verifier_registry = _registry()
    if replay_preflight is _SENTINEL:
        replay_preflight = _replay(cand)
    if transport_context is None:
        transport_context = itv.TransportContext()
    return itv.verify_ingress_trigger_candidate(
        candidate=cand,
        command_bytes=command_bytes,
        signature=signature,
        public_key=public_key,
        pinned_public_key_fingerprint=pinned_fp,
        signature_verifier=signature_verifier,
        trust_anchor_artifact=trust_anchor_artifact,
        operator_allowlist=operator_allowlist,
        verifier_identity=verifier_identity,
        verifier_version=verifier_version,
        verifier_fingerprint=verifier_fingerprint,
        verifier_registry=verifier_registry,
        replay_preflight=replay_preflight,
        expected_bindings=bindings,
        transport_context=transport_context,
    )


_AUTHORITY_FLAGS = (
    "s1_append_authorized",
    "production_stream_authorized",
    "trading_authorized",
    "capacity_enabled",
    "wallet_authorized",
    "execution_token_created",
    "circuit_invoked",
    "db_created",
)


# --------------------------------------------------------------------------- happy path

def test_valid_candidate_returns_passive_verified_candidate_only():
    res = _call()
    assert res.status == itv.VERIFIED_PASSIVE_CANDIDATE
    assert res.reason == ""
    assert res.verified_candidate is not None
    assert res.candidate_digest
    assert res.verified_candidate.candidate_digest == res.candidate_digest
    # Verified candidate is passive evidence, not authorization.
    assert "not S1 append authorization" in res.verified_candidate.statement


def test_verified_status_is_not_an_authorized_status():
    res = _call()
    assert res.status != "AUTHORIZED"
    assert res.status != "PRODUCTION_APPEND_AUTHORIZED"


def test_all_authority_flags_false_on_verified_result_and_candidate():
    res = _call()
    for flag in _AUTHORITY_FLAGS:
        assert getattr(res, flag) is False, flag
        assert getattr(res.verified_candidate, flag) is False, flag


def test_candidate_digest_is_deterministic():
    assert _call().candidate_digest == _call().candidate_digest


# ----------------------------------------------------------------- shape / parsing alone

@pytest.mark.parametrize(
    "field",
    [
        "operator_command_id",
        "operator_identity_reference",
        "command_scope",
        "target_circuit_digest",
        "s1_target",
        "evidence_digest",
        "freshness_binding_digest",
        "immutable_snapshot_ref",
        "request_timestamp_reference",
        "replay_protection_nonce",
        "replay_protection_sequence",
    ],
)
def test_missing_required_field_fails_closed(field):
    cand = _base_candidate(**{field: ""})
    res = _call(cand, bindings=_bindings(cand))
    assert res.status == itv.BLOCKED
    assert res.reason == "missing_required_field"
    assert res.verified_candidate is None


def test_shape_success_alone_is_not_authorization():
    # Perfectly shaped + bound candidate, but the signature does not verify -> fail closed.
    res = _call(signature=b"WRONG-SIGNATURE-BYTES")
    assert res.status == itv.BLOCKED
    assert res.reason == "signature_verification_failed"
    assert res.verified_candidate is None


# --------------------------------------------------------------- authority-escalation vectors

def test_asserted_authority_field_fails_closed():
    cand = _base_candidate(asserted_authority="s1_append_authorized=true")
    res = _call(cand, bindings=_bindings(cand))
    assert res.status == itv.BLOCKED
    assert res.reason == "authority_escalation"


def test_authority_token_in_scope_fails_closed_even_if_pinned():
    # Even if the expected binding were (mis)pinned to the same escalated scope, the token scan blocks.
    cand = _base_candidate(command_scope="S1_APPEND_TRADING_AUTHORIZED")
    res = _call(cand, bindings=_bindings(cand))
    assert res.status == itv.BLOCKED
    assert res.reason == "authority_escalation"


def test_raw_mutable_path_supplied_fails_closed():
    cand = _base_candidate(raw_db_path="/var/lib/s1/live.db")
    res = _call(cand, bindings=_bindings(cand))
    assert res.status == itv.BLOCKED
    assert res.reason == "raw_path_supplied"


def test_wall_clock_only_freshness_fails_closed():
    cand = _base_candidate(freshness_evidence_kind="WALL_CLOCK_ONLY")
    res = _call(cand, bindings=_bindings(cand))
    assert res.status == itv.BLOCKED
    assert res.reason == "wall_clock_only_freshness_forbidden"


# ----------------------------------------------------------------------- cross-binding mismatch

def test_target_circuit_digest_mismatch_fails_closed():
    cand = _base_candidate()
    res = _call(cand, bindings=dataclasses.replace(_bindings(cand), target_circuit_digest="other"))
    assert res.status == itv.BLOCKED
    assert res.reason == "target_circuit_digest_mismatch"


def test_db_path_digest_mismatch_fails_closed():
    cand = _base_candidate()
    res = _call(cand, bindings=dataclasses.replace(_bindings(cand), db_path_digest="other"))
    assert res.status == itv.BLOCKED
    assert res.reason == "db_path_digest_mismatch"


def test_s1_target_mismatch_fails_closed():
    cand = _base_candidate()
    res = _call(cand, bindings=dataclasses.replace(_bindings(cand), s1_target="ETH-UPDN-5M-W9"))
    assert res.status == itv.BLOCKED
    assert res.reason == "s1_target_mismatch"


def test_freshness_binding_mismatch_fails_closed():
    cand = _base_candidate()
    res = _call(cand, bindings=dataclasses.replace(_bindings(cand), freshness_binding_digest="x"))
    assert res.status == itv.BLOCKED
    assert res.reason == "freshness_binding_mismatch"


# ------------------------------------------------------- command digest & anti-blind-signing

def test_command_digest_mismatch_fails_closed():
    cand = _base_candidate(command_digest="deadbeef-not-the-real-digest")
    res = _call(cand, bindings=_bindings(cand))
    assert res.status == itv.BLOCKED
    assert res.reason == "command_digest_mismatch"


def test_blind_signing_shown_bytes_mismatch_fails_closed():
    # Shown/signed bytes differ from the canonical bytes of the candidate -> anti-blind-signing block.
    cand = _base_candidate()
    shown = b"DIFFERENT-SHOWN-BYTES-THAN-CANONICAL"
    sig = hashlib.sha256(_PUBLIC_KEY + shown).digest()  # would "verify", but bytes are wrong
    res = _call(cand, bindings=_bindings(cand), command_bytes=shown, signature=sig)
    assert res.status == itv.BLOCKED
    assert res.reason == "blind_signing_shown_bytes_mismatch"


# ---------------------------------------------------------------------- signature / key gates

def test_missing_signature_fails_closed():
    res = _call(signature=b"")
    assert res.status == itv.BLOCKED
    assert res.reason == "signature_missing"


def test_invalid_signature_fails_closed():
    res = _call(signature=b"NOT-A-VALID-SIGNATURE")
    assert res.status == itv.BLOCKED
    assert res.reason == "signature_verification_failed"


def test_public_key_fingerprint_mismatch_fails_closed():
    # Pinned fingerprint says one thing; resident public key hashes to another -> swap detected.
    bad_fp = hashlib.sha256(b"SOME-OTHER-KEY").hexdigest()
    res = _call(pinned_fp=bad_fp, trust_anchor_artifact=_anchor(bad_fp))
    assert res.status == itv.BLOCKED
    assert res.reason == "public_key_fingerprint_mismatch"


def test_operator_not_allowlisted_fails_closed():
    res = _call(operator_allowlist=frozenset({"operator://someone-else"}))
    assert res.status == itv.BLOCKED
    assert res.reason == "operator_not_allowlisted"


def test_trust_anchor_invalid_fails_closed():
    res = _call(trust_anchor_artifact={"public_key_fingerprint": "tooshort"})
    assert res.status == itv.BLOCKED
    assert res.reason == "trust_anchor_invalid"


def test_anchor_key_binding_mismatch_fails_closed():
    # Trust anchor pins a fingerprint that does not match the resident pinned public-key fingerprint.
    other = hashlib.sha256(b"ANCHOR-FOR-A-DIFFERENT-KEY").hexdigest()
    res = _call(trust_anchor_artifact=_anchor(other))
    assert res.status == itv.BLOCKED
    assert res.reason == "anchor_key_binding_mismatch"


# ------------------------------------------------------------- missing / insufficient verifier

def test_missing_signature_verifier_returns_missing_ratified_verifier():
    res = _call(signature_verifier=None)
    assert res.status == itv.BLOCKED_MISSING_RATIFIED_VERIFIER
    assert res.verified_candidate is None


def test_unpinned_verifier_identity_returns_missing_ratified_verifier():
    res = _call(verifier_registry={})  # identity not pinned
    assert res.status == itv.BLOCKED_MISSING_RATIFIED_VERIFIER


def test_test_only_verifier_rejected_as_missing_ratified_verifier():
    reg = {
        "mock_verifier": _vr.PinnedVerifier(
            identity="mock_verifier", version="v3", fingerprint="vfp-123"
        )
    }
    res = _call(verifier_identity="mock_verifier", verifier_registry=reg)
    assert res.status == itv.BLOCKED_MISSING_RATIFIED_VERIFIER


def test_verifier_fingerprint_mismatch_returns_missing_ratified_verifier():
    res = _call(verifier_fingerprint="wrong-vfp")
    assert res.status == itv.BLOCKED_MISSING_RATIFIED_VERIFIER


# ------------------------------------------------------------------------- replay protection

def test_replay_preflight_absent_returns_not_ratified():
    res = _call(replay_preflight=None)
    assert res.status == itv.BLOCKED_REPLAY_STATE_NOT_RATIFIED
    assert res.verified_candidate is None


def test_replay_preflight_empty_store_returns_not_ratified():
    cand = _base_candidate()
    rp = dataclasses.replace(_replay(cand), durable_store_ref="")
    res = _call(cand, bindings=_bindings(cand), replay_preflight=rp)
    assert res.status == itv.BLOCKED_REPLAY_STATE_NOT_RATIFIED


def test_replay_preflight_binding_mismatch_fails_closed():
    cand = _base_candidate()
    rp = dataclasses.replace(_replay(cand), checked_nonce="some-other-nonce")
    res = _call(cand, bindings=_bindings(cand), replay_preflight=rp)
    assert res.status == itv.BLOCKED
    assert res.reason == "replay_preflight_mismatch"


def test_replay_detected_when_uniqueness_not_confirmed_fails_closed():
    cand = _base_candidate()
    rp = dataclasses.replace(_replay(cand), uniqueness_confirmed=False)
    res = _call(cand, bindings=_bindings(cand), replay_preflight=rp)
    assert res.status == itv.BLOCKED
    assert res.reason == "replay_detected"


# ----------------------------------------------------------- transport / ingress implication

@pytest.mark.parametrize(
    "kwarg,reason",
    [
        ("used_default_route", "default_route_forbidden"),
        ("unauthenticated_cli_shortcut", "unauthenticated_cli_shortcut_forbidden"),
        ("env_authority_asserted", "env_authority_forbidden"),
        ("bearer_token_only_authority", "bearer_only_authority_forbidden"),
        ("listener_opened", "listener_forbidden"),
        ("framework_introduced", "framework_introduced_forbidden"),
    ],
)
def test_transport_implication_fails_closed(kwarg, reason):
    tc = itv.TransportContext(**{kwarg: True})
    res = _call(transport_context=tc)
    assert res.status == itv.BLOCKED
    assert res.reason == reason
    assert res.verified_candidate is None


# ------------------------------------------------------------------ no side effects at all

def test_no_db_or_file_created_and_no_circuit_side_effect(tmp_path):
    before = set(os.listdir(tmp_path))
    res = _call()
    after = set(os.listdir(tmp_path))
    assert before == after  # nothing written anywhere by the verifier
    assert res.status == itv.VERIFIED_PASSIVE_CANDIDATE
    assert res.circuit_invoked is False
    assert res.db_created is False


def test_blocked_results_also_carry_all_false_authority_flags():
    res = _call(signature=b"WRONG")
    assert res.verified_candidate is None
    for flag in _AUTHORITY_FLAGS:
        assert getattr(res, flag) is False, flag


# --------------------------------------------------------- structural: no ingress surface exists

_FORBIDDEN_SOURCE_TOKENS = (
    "argparse",
    "click",
    "typer",
    "flask",
    "fastapi",
    "uvicorn",
    "socket",
    "http.server",
    "urllib",
    "requests",
    "telegram",
    "webhook",
    "subprocess",
    "asyncio",
    "if __name__",
    "sqlite3",
    "time.time",
    "datetime",
    "os.environ",
    "getenv",
    # never invoke the append machinery as a side effect:
    "production_s1_append_circuit",
    "s1_append_execution_db_writer",
    "live_s1_db_initialization",
)


def _module_source():
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "approval",
        "ingress_trigger_verifier.py",
    )
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


@pytest.mark.parametrize("token", _FORBIDDEN_SOURCE_TOKENS)
def test_module_has_no_ingress_network_or_append_surface(token):
    assert token not in _module_source(), token


def test_module_imports_are_stdlib_and_ratified_primitives_only():
    import ast

    tree = ast.parse(_module_source())
    allowed_top = {"hashlib", "dataclasses", "typing", "approval", "__future__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in allowed_top, alias.name
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root in allowed_top, node.module
