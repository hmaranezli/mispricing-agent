"""tests/test_s1_append_authorization_decision.py — passive Production S1 Append Authorization
Decision layer (TDD).

Bu slice, RATIFIYE Production S1 Append Authorization Boundary Charter'ına göre PASİF, mutasyonsuz bir
KARAR katmanıdır. Caller'ın verdiği pasif evidence snapshot'ını değerlendirir ve YALNIZCA
``REVIEWABLE_FOR_S1_APPEND`` veya ``BLOCKED`` döndürür — asla ``AUTHORIZED``. S1 append YAPMAZ, S1 DB
YARATMAZ, ledger MUTATE ETMEZ, execution token / trade / wallet / capacity üretmez. Wall-clock
KULLANMAZ; tazelik açık snapshot alanlarıyla temsil edilir.

İlk RED: approval.s1_append_authorization_decision yok → ImportError (eksik üretim seam'i).
"""
import ast
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from approval.s1_append_authorization_decision import (
    S1AppendAuthorizationDecision,
    S1AppendEvidenceSnapshot,
    evaluate_s1_append_authorization,
)

_D = "a" * 64  # shared payload digest (all bound digests equal in the valid case)
_R = "b" * 64  # review package digest


def _snap(**over) -> S1AppendEvidenceSnapshot:
    kw = dict(
        approval_ledger_row_present=True,
        approval_row_append_only=True,
        canonical_payload_digest=_D,
        displayed_payload_digest=_D,
        signed_payload_digest=_D,
        approval_row_digest=_D,
        review_package_digest=_R,
        review_package_digest_expected=_R,
        matrix_state="REVIEWABLE",
        signature_present=True,
        signature_verifier_passed=True,
        preflight_allowed=True,
        payload_freshness_state="FRESH",
        signature_freshness_state="FRESH",
        canonical_payload_binding_present=True,
        operator_identity="human_operator_001",
        signer_identity="human_operator_001",
        signer_fingerprint_known=True,
        s1_target_known=True,
        s1_target_evidence_present=True,
        single_flight_lock_held=True,
        verification_interrupted=False,
        partial_transaction_marker=False,
        duplicate_evidence=False,
        replay_attempt=False,
    )
    kw.update(over)
    return S1AppendEvidenceSnapshot(**kw)


def _blocked_reason(**over):
    d = evaluate_s1_append_authorization(_snap(**over))
    assert d.status == "BLOCKED"
    return d.reasons


# --- individual fail-closed conditions ---
def test_missing_approval_row():
    assert "missing_approval_ledger_row" in _blocked_reason(approval_ledger_row_present=False)


def test_mutable_approval_row():
    assert "mutable_approval_row" in _blocked_reason(approval_row_append_only=False)


def test_missing_canonical_digest():
    assert "missing_canonical_payload_digest" in _blocked_reason(canonical_payload_digest="")


def test_payload_digest_mismatch():
    assert "payload_digest_mismatch" in _blocked_reason(signed_payload_digest="c" * 64)


def test_missing_review_package_digest():
    assert "missing_review_package_digest" in _blocked_reason(review_package_digest="")


def test_review_package_digest_mismatch():
    assert "review_package_digest_mismatch" in _blocked_reason(review_package_digest_expected="c" * 64)


def test_matrix_not_reviewable():
    assert "matrix_not_reviewable" in _blocked_reason(matrix_state="BLOCKED_INCOMPLETE")


def test_matrix_authorized_attempt():
    assert "matrix_treated_as_authorized" in _blocked_reason(matrix_state="AUTHORIZED")


def test_signature_missing():
    assert "missing_signature_evidence" in _blocked_reason(signature_present=False)


def test_signature_not_verifier_passed():
    assert "signature_not_verifier_passed" in _blocked_reason(signature_verifier_passed=False)


def test_preflight_not_allowed():
    assert "preflight_not_allowed" in _blocked_reason(preflight_allowed=False)


def test_stale_payload():
    assert "stale_payload_evidence" in _blocked_reason(payload_freshness_state="STALE")


def test_stale_signature():
    assert "stale_signature_return" in _blocked_reason(signature_freshness_state="STALE")


def test_hardware_digest_only_unbound():
    assert "hardware_digest_only_unbound" in _blocked_reason(canonical_payload_binding_present=False)


def test_approval_row_digest_mismatch():
    assert "approval_row_digest_mismatch" in _blocked_reason(approval_row_digest="c" * 64)


def test_duplicate_evidence():
    assert "duplicate_approval_evidence" in _blocked_reason(duplicate_evidence=True)


def test_ambiguous_identity():
    assert "ambiguous_operator_identity" in _blocked_reason(operator_identity="AMBIGUOUS")


def test_unknown_signer_fingerprint():
    assert "unknown_signer_fingerprint" in _blocked_reason(signer_fingerprint_known=False)


def test_unknown_s1_target():
    assert "unknown_s1_target" in _blocked_reason(s1_target_known=False)


def test_missing_s1_target_evidence():
    assert "missing_s1_target_evidence" in _blocked_reason(s1_target_evidence_present=False)


def test_race_lock_unavailable():
    assert "race_lock_unavailable" in _blocked_reason(single_flight_lock_held=False)


def test_interrupted_verification():
    assert "interrupted_verification" in _blocked_reason(verification_interrupted=True)


def test_partial_transaction():
    assert "partial_transaction" in _blocked_reason(partial_transaction_marker=True)


def test_replay_attempt():
    assert "duplicate_retry_replay" in _blocked_reason(replay_attempt=True)


# --- hidden TTL/config/env is impossible by API shape ---
def test_no_hidden_ttl_config_env_in_api():
    snap_fields = {f.lower() for f in S1AppendEvidenceSnapshot.__annotations__}
    fn_params = {p.lower() for p in inspect.signature(evaluate_s1_append_authorization).parameters}
    # precise clock/TTL tokens (avoid bare "now"/"time" which false-match "known"/legit words)
    for bad in ("ttl", "config", "wall_clock", "clock", "timestamp", "deadline", "_env"):
        assert not any(bad in f for f in snap_fields), f"hidden freshness field: {bad}"
        assert not any(bad in p for p in fn_params), f"hidden freshness param: {bad}"
    # freshness is explicit, caller-supplied state
    assert "payload_freshness_state" in snap_fields
    assert "signature_freshness_state" in snap_fields


# --- the only success path ---
def test_complete_fresh_is_reviewable_only():
    d = evaluate_s1_append_authorization(_snap())
    assert d.status == "REVIEWABLE_FOR_S1_APPEND"
    assert d.status != "AUTHORIZED"
    assert d.reasons == ()


def test_reviewable_sets_no_authority_flags():
    d = evaluate_s1_append_authorization(_snap())
    for flag in (
        "s1_append_authorized",
        "production_stream_authorized",
        "execution_token_created",
        "trading_authorized",
        "capacity_enabled",
        "wallet_authorized",
    ):
        assert getattr(d, flag) is False


def test_output_has_reasons_and_deterministic_digest():
    d1 = evaluate_s1_append_authorization(_snap())
    d2 = evaluate_s1_append_authorization(_snap())
    assert isinstance(d1.reasons, tuple)
    assert len(d1.evidence_digest) == 64
    assert d1.evidence_digest == d2.evidence_digest
    # a changed field changes the evidence digest
    d3 = evaluate_s1_append_authorization(_snap(operator_identity="other"))
    assert d3.evidence_digest != d1.evidence_digest


def test_output_frozen_passive():
    d = evaluate_s1_append_authorization(_snap())
    with pytest.raises(Exception):
        d.status = "AUTHORIZED"  # type: ignore[misc]


def test_multiple_blockers_all_listed():
    d = evaluate_s1_append_authorization(
        _snap(signature_present=False, preflight_allowed=False, matrix_state="AUTHORIZED")
    )
    assert d.status == "BLOCKED"
    assert "missing_signature_evidence" in d.reasons
    assert "preflight_not_allowed" in d.reasons
    assert "matrix_treated_as_authorized" in d.reasons


# --- isolation / no-surface ---
def test_no_db_file_network_env_access():
    import approval.s1_append_authorization_decision as mod

    low = inspect.getsource(mod).lower()
    for tok in ("sqlite", "open(", "socket", "requests", "urllib", "environ", "getenv", "subprocess", ".execute(", ".commit("):
        assert tok not in low, f"forbidden access token: {tok}"


def test_no_mutation_or_command_surface():
    import approval.s1_append_authorization_decision as mod

    for name in dir(mod):
        if not callable(getattr(mod, name)):
            continue
        low = name.lower()
        for verb in (
            "append_",
            "write_",
            "commit_",
            "insert_",
            "update_",
            "delete_",
            "truncate_",
            "redact_",
            "vacuum_",
            "execute",
            "place_",
            "submit_",
            "send_",
            "stream",
            "trade",
            "sign_",
        ):
            assert not low.startswith(verb), f"forbidden surface: {name}"


def test_imports_stdlib_only():
    import approval.s1_append_authorization_decision as mod

    tree = ast.parse(inspect.getsource(mod))
    allowed_top = {"hashlib", "dataclasses", "typing", "__future__"}
    imported_top = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported_top.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_top.add(node.module.split(".")[0])
    assert imported_top <= allowed_top, f"unexpected imports: {imported_top - allowed_top}"


def test_no_file_generated(tmp_path):
    before = set(os.listdir(tmp_path))
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        evaluate_s1_append_authorization(_snap())
        evaluate_s1_append_authorization(_snap(matrix_state="AUTHORIZED"))
    finally:
        os.chdir(cwd)
    assert set(os.listdir(tmp_path)) == before
