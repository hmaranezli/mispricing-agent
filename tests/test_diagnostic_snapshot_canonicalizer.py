"""tests/test_diagnostic_snapshot_canonicalizer.py — TDD for the pure Phase 2B snapshot canonicalizer.

This pure slice canonicalizes a complete diag-edge-probe-v1 envelope into deterministic bytes, a
SHA-256 digest, and a LOGICAL immutable_snapshot_ref. It performs NO IO/DB/network/clock/blob/append.
"""
import dataclasses
import hashlib
import json

import pytest

from approval.diagnostic_snapshot_canonicalizer import (
    build_immutable_snapshot,
    SnapshotReference,
    SnapshotEnvelopeError,
)


def _valid_envelope():
    """A complete, recognized diag-edge-probe-v1 envelope (all 9 top-level keys)."""
    return {
        "schema_version": "diag-edge-probe-v1",
        "layer": "ECONOMICS",
        "capture_status": "GOLDEN_SAMPLE_OK",
        "fail_closed_reason": None,
        "economics": {"status": "DIAGNOSTIC_OK", "p_up": "0.22570"},
        "capture": {"slug": "btc-updown-15m-1782651600", "asset": "BTC"},
        "provenance": {
            "valuation_time_ms": 1782652557293,
            "capture_start_utc": "2026-06-28T13:00:00.000Z",
            "capture_complete_utc": "2026-06-28T13:00:01.000Z",
            "valuation_to_capture_start_offset_ms": 1500,
        },
        "markers": ["not_actionable", "capture_and_economics_layers_separated"],
        "driver_note": "diagnostic observation only; not trading/actionability",
    }


def _sample8_style_envelope():
    """Sample #8-style: economics=null, fail_closed_reason populated, ONBOARDING layer."""
    return {
        "schema_version": "diag-edge-probe-v1",
        "layer": "ONBOARDING",
        "capture_status": "ONBOARDING_INVALID",
        "fail_closed_reason": "classifier_observe_only",
        "economics": None,
        "capture": {"slug": "btc-updown-15m-1782651600", "classification": "OBSERVE_ONLY"},
        "provenance": {
            "valuation_time_ms": 1782652557293,
            "capture_start_utc": None,
            "capture_complete_utc": None,
            "valuation_to_capture_start_offset_ms": None,
        },
        "markers": ["not_actionable"],
        "driver_note": "diagnostic observation only; not trading/actionability",
    }


def test_digest_is_deterministic_regardless_of_key_order():
    env = _valid_envelope()
    # Same content, deliberately different insertion order.
    reordered = dict(reversed(list(env.items())))
    a = build_immutable_snapshot(env)
    b = build_immutable_snapshot(reordered)
    assert a.canonical_payload_digest == b.canonical_payload_digest
    assert a.canonical_bytes == b.canonical_bytes
    assert a.immutable_snapshot_ref == b.immutable_snapshot_ref


def test_canonical_bytes_use_compact_separators_and_utf8():
    env = _valid_envelope()
    env["driver_note"] = "diagnostic ☑ not trading"  # non-ASCII to prove UTF-8
    ref = build_immutable_snapshot(env)
    expected = json.dumps(
        env, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    assert ref.canonical_bytes == expected
    assert b", " not in ref.canonical_bytes  # compact item separator
    assert b'": ' not in ref.canonical_bytes  # compact key separator
    assert "☑".encode("utf-8") in ref.canonical_bytes  # real UTF-8, not \u escape
    assert ref.byte_length == len(expected)


def test_digest_matches_sha256_of_canonical_bytes():
    ref = build_immutable_snapshot(_valid_envelope())
    assert ref.canonical_payload_digest == hashlib.sha256(ref.canonical_bytes).hexdigest()


def test_allow_nan_false_rejects_nan_and_infinity():
    for bad in (float("nan"), float("inf"), float("-inf")):
        env = _valid_envelope()
        env["economics"] = {"status": "DIAGNOSTIC_OK", "p_up": bad}
        with pytest.raises(SnapshotEnvelopeError):
            build_immutable_snapshot(env)


def test_missing_required_top_level_key_fails_closed():
    env = _valid_envelope()
    del env["provenance"]
    with pytest.raises(SnapshotEnvelopeError):
        build_immutable_snapshot(env)


def test_foreign_extra_top_level_key_fails_closed():
    env = _valid_envelope()
    env["unexpected_field"] = "x"
    with pytest.raises(SnapshotEnvelopeError):
        build_immutable_snapshot(env)


def test_foreign_schema_version_fails_closed():
    env = _valid_envelope()
    env["schema_version"] = "some-other-schema-v9"
    with pytest.raises(SnapshotEnvelopeError):
        build_immutable_snapshot(env)


def test_non_dict_envelope_fails_closed():
    for bad in (None, "string", 123, ["list"]):
        with pytest.raises(SnapshotEnvelopeError):
            build_immutable_snapshot(bad)


def test_sample8_style_envelope_canonicalizes_successfully():
    ref = build_immutable_snapshot(_sample8_style_envelope())
    assert ref.payload_kind == "diag-edge-probe-v1"
    assert ref.canonical_payload_digest == hashlib.sha256(ref.canonical_bytes).hexdigest()
    assert b'"economics":null' in ref.canonical_bytes
    assert b'"fail_closed_reason":"classifier_observe_only"' in ref.canonical_bytes


def test_immutable_snapshot_ref_is_logical_format():
    ref = build_immutable_snapshot(_valid_envelope())
    assert ref.immutable_snapshot_ref == (
        "diag-edge-probe-v1:sha256:" + ref.canonical_payload_digest
    )
    # Logical ref, not a filesystem path.
    assert "/" not in ref.immutable_snapshot_ref
    assert "\\" not in ref.immutable_snapshot_ref


def test_value_object_has_no_identity_clock_or_authorization_fields():
    ref = build_immutable_snapshot(_valid_envelope())
    assert isinstance(ref, SnapshotReference)
    field_names = {f.name for f in dataclasses.fields(ref)}
    assert field_names == {
        "canonical_payload_digest",
        "immutable_snapshot_ref",
        "payload_kind",
        "byte_length",
        "canonical_bytes",
    }
    forbidden_tokens = ("created_at", "operator_command_id", "wall", "clock",
                        "signer", "approval", "authoriz", "capacity", "wallet")
    for name in field_names:
        for tok in forbidden_tokens:
            assert tok not in name.lower()


def test_value_object_is_frozen():
    ref = build_immutable_snapshot(_valid_envelope())
    with pytest.raises(dataclasses.FrozenInstanceError):
        ref.canonical_payload_digest = "tampered"
