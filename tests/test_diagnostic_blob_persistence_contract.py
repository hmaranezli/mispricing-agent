"""tests/test_diagnostic_blob_persistence_contract.py — TDD for the PURE blob-persistence contract slice.

This slice defines types/contracts ONLY (enums, a frozen result dataclass, a typing.Protocol). It must
contain NO filesystem/durability/DB/S1/runtime/network implementation. SnapshotReference is reused from
the canonical canonicalizer module — never re-defined here.
"""
import ast
import dataclasses
import inspect
import typing

import pytest

from approval import diagnostic_snapshot_canonicalizer as _canon
from approval.diagnostic_snapshot_canonicalizer import build_immutable_snapshot, SnapshotReference

from approval import diagnostic_blob_persistence_contract as contract
from approval.diagnostic_blob_persistence_contract import (
    BlobPersistStatus,
    BlobPersistReason,
    BlobPersistResult,
    BlobPersistAdapter,
)


_EXPECTED_STATUS = {
    "PERSISTED_NEW",
    "VERIFIED_EXISTING_NOOP",
    "SNAPSHOT_VALIDATION_FAILED",
    "BLOB_PERSIST_FAILED",
    "CRITICAL_COLLISION_DETECTED",
    "BLOCKED_RECOVERY_REQUIRED",
}

_EXPECTED_REASONS = {
    "NONE",
    "INVALID_DIGEST",
    "SNAPSHOT_DIGEST_MISMATCH",
    "SNAPSHOT_REF_MISMATCH",
    "SNAPSHOT_BYTE_LENGTH_MISMATCH",
    "SNAPSHOT_PAYLOAD_KIND_MISMATCH",
    "BYTE_LENGTH_EXCEEDS_LIMIT",
    "ROOT_MISSING",
    "ROOT_IDENTITY_CHANGED",
    "OWNER_MISMATCH",
    "MODE_MISMATCH",
    "SYMLINK_OR_NONREGULAR",
    "SHARD_DURABILITY_FAILED",
    "TEMP_CREATE_FAILED",
    "WRITE_FAILED",
    "FILE_FSYNC_FAILED",
    "TEMP_VERIFY_FAILED",
    "NO_CLOBBER_UNAVAILABLE",
    "PUBLISH_FAILED",
    "DIRECTORY_FSYNC_FAILED",
    "FINAL_READBACK_FAILED",
    "CONTENT_HASH_MISMATCH",
    "TEMP_CLEANUP_AMBIGUOUS",
    "AMBIGUOUS_PUBLICATION_STATE",
}

_EXPECTED_RESULT_FIELDS = {
    "status",
    "reason",
    "canonical_payload_digest",
    "immutable_snapshot_ref",
    "byte_length",
    "created_now",
    "durability_verified",
}


def _sample_ref():
    env = {
        "schema_version": "diag-edge-probe-v1",
        "layer": "ECONOMICS",
        "capture_status": "GOLDEN_SAMPLE_OK",
        "fail_closed_reason": None,
        "economics": {"status": "DIAGNOSTIC_OK"},
        "capture": {"slug": "btc-updown-15m-1782651600"},
        "provenance": {"valuation_time_ms": 1782652557293, "capture_start_utc": None,
                       "capture_complete_utc": None, "valuation_to_capture_start_offset_ms": None},
        "markers": ["not_actionable"],
        "driver_note": "diagnostic observation only; not trading/actionability",
    }
    return build_immutable_snapshot(env)


def _module_ast():
    return ast.parse(inspect.getsource(contract))


def test_status_enum_membership_is_exact():
    assert {m.name for m in BlobPersistStatus} == _EXPECTED_STATUS
    # No generic SUCCESS status allowed.
    assert "SUCCESS" not in {m.name for m in BlobPersistStatus}


def test_reason_enum_membership_is_exact():
    assert {m.name for m in BlobPersistReason} == _EXPECTED_REASONS


def test_reason_values_are_stable_audit_strings():
    for m in BlobPersistReason:
        assert isinstance(m.value, str)
        assert m.value == m.name  # stable, deterministic, audit-comparable


def test_status_values_are_stable_audit_strings():
    for m in BlobPersistStatus:
        assert isinstance(m.value, str)
        assert m.value == m.name


def test_result_is_frozen_dataclass():
    assert dataclasses.is_dataclass(BlobPersistResult)
    r = BlobPersistResult(
        status=BlobPersistStatus.PERSISTED_NEW,
        reason=BlobPersistReason.NONE,
        canonical_payload_digest="a" * 64,
        immutable_snapshot_ref="diag-edge-probe-v1:sha256:" + "a" * 64,
        byte_length=10,
        created_now=True,
        durability_verified=True,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.status = BlobPersistStatus.BLOB_PERSIST_FAILED


def test_result_field_set_is_exact():
    assert {f.name for f in dataclasses.fields(BlobPersistResult)} == _EXPECTED_RESULT_FIELDS


def test_result_has_no_forbidden_fields():
    field_names = {f.name for f in dataclasses.fields(BlobPersistResult)}
    forbidden_tokens = (
        "path", "dir", "root", "bytes", "canonical_bytes", "time", "clock", "created_at",
        "operator", "signer", "identity", "approval", "authoriz", "market", "price", "side",
        "wallet", "capital", "capacity", "stake", "fd", "inode",
    )
    for name in field_names:
        for tok in forbidden_tokens:
            assert tok not in name.lower(), f"forbidden token {tok!r} in field {name!r}"


def test_protocol_method_accepts_canonical_snapshot_reference():
    hints = typing.get_type_hints(BlobPersistAdapter.persist_snapshot_blob)
    assert hints["snapshot"] is SnapshotReference
    assert hints["return"] is BlobPersistResult


def test_protocol_is_runtime_checkable_and_shape_works():
    class _Dummy:
        def persist_snapshot_blob(self, snapshot):
            return BlobPersistResult(
                status=BlobPersistStatus.PERSISTED_NEW,
                reason=BlobPersistReason.NONE,
                canonical_payload_digest=snapshot.canonical_payload_digest,
                immutable_snapshot_ref=snapshot.immutable_snapshot_ref,
                byte_length=snapshot.byte_length,
                created_now=True,
                durability_verified=True,
            )

    d = _Dummy()
    assert isinstance(d, BlobPersistAdapter)
    out = d.persist_snapshot_blob(_sample_ref())
    assert isinstance(out, BlobPersistResult)
    assert out.status is BlobPersistStatus.PERSISTED_NEW


def test_no_duplicate_snapshot_reference_dataclass():
    # If exposed at all, it must be the SAME canonical object, never a re-definition.
    assert getattr(contract, "SnapshotReference", _canon.SnapshotReference) is _canon.SnapshotReference
    tree = _module_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            assert node.name != "SnapshotReference", "must not re-define SnapshotReference"


def test_module_imports_no_io_or_clock_or_network():
    forbidden_roots = {
        "os", "pathlib", "sqlite3", "tempfile", "ctypes", "subprocess", "socket",
        "requests", "aiohttp", "urllib", "time", "datetime", "random", "secrets", "asyncio",
    }
    tree = _module_ast()
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                seen.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                seen.add(node.module.split(".")[0])
    assert not (seen & forbidden_roots), f"forbidden imports: {seen & forbidden_roots}"


def test_module_makes_no_io_calls():
    forbidden_calls = {
        "open", "rename", "replace", "unlink", "remove", "rmdir", "fsync", "mkdir",
        "makedirs", "openat", "renameat2", "chmod", "fchmod", "stat", "fstat", "lstat",
        "connect", "execute", "fdopen", "syscall",
    }
    tree = _module_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (
                func.attr if isinstance(func, ast.Attribute) else None)
            assert name not in forbidden_calls, f"forbidden call: {name}"
