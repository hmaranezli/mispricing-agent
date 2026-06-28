"""tests/test_diagnostic_blob_filesystem_integration.py — bounded REAL-filesystem integration test.

Exercises the real LinuxBlobSyscalls + FilesystemBlobPersistAdapter against a real renameat2/fsync path.
ALL filesystem mutation is confined to a pytest ``tmp_path`` store root (mode 0o700, current uid). Each
test explicitly removes the created store tree in ``finally`` and verifies removal. It touches NO var/,
SQLite, S1, WAL/SHM, network, or market discovery.

Note: validates observable Linux semantics only — NOT sudden-power-loss durability or dishonest hardware.
"""
import os
import shutil
import stat
import sys

import pytest

from approval.diagnostic_snapshot_canonicalizer import build_immutable_snapshot
from approval.diagnostic_blob_linux_syscalls import LinuxBlobSyscalls
from approval.diagnostic_blob_filesystem_adapter import FilesystemBlobPersistAdapter
from approval.diagnostic_blob_persistence_contract import BlobPersistStatus, BlobPersistReason

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux renameat2 seam required")


def _snap():
    env = {
        "schema_version": "diag-edge-probe-v1",
        "layer": "ECONOMICS",
        "capture_status": "GOLDEN_SAMPLE_OK",
        "fail_closed_reason": None,
        "economics": {"status": "DIAGNOSTIC_OK", "p_up": "0.22570"},
        "capture": {"slug": "btc-updown-15m-1782651600", "asset": "BTC"},
        "provenance": {"valuation_time_ms": 1782652557293, "capture_start_utc": None,
                       "capture_complete_utc": None, "valuation_to_capture_start_offset_ms": None},
        "markers": ["not_actionable"],
        "driver_note": "diagnostic observation only; not trading/actionability",
    }
    return build_immutable_snapshot(env)


def _make_store(tmp_path):
    store = os.path.join(str(tmp_path), "store")
    os.mkdir(store, 0o700)
    os.chmod(store, 0o700)  # exact, regardless of umask
    sc = LinuxBlobSyscalls()
    adapter = FilesystemBlobPersistAdapter(store, os.getuid(), sc)
    return adapter, store


def _teardown(adapter, store):
    adapter.close()
    shutil.rmtree(store, ignore_errors=True)
    removed = not os.path.exists(store)
    print(f"[integration] store={store} removed={removed}")
    assert removed, "store tree must be removed after the test"


def _blob_path(store, digest):
    return os.path.join(store, digest[0:2], digest[2:4], digest + ".json")


def test_first_persist_is_persisted_new_with_exact_layout_and_modes(tmp_path):
    adapter, store = _make_store(tmp_path)
    try:
        snap = _snap()
        d = snap.canonical_payload_digest
        res = adapter.persist_snapshot_blob(snap)
        assert res.status is BlobPersistStatus.PERSISTED_NEW
        assert res.reason is BlobPersistReason.NONE
        assert res.created_now is True
        assert res.durability_verified is True
        blob = _blob_path(store, d)
        assert os.path.isfile(blob)
        with open(blob, "rb") as f:
            assert f.read() == snap.canonical_bytes      # exact bytes via real renameat2/fsync path
        assert stat.S_IMODE(os.stat(blob).st_mode) == 0o600
        assert stat.S_IMODE(os.stat(os.path.join(store, d[0:2])).st_mode) == 0o700
        assert stat.S_IMODE(os.stat(os.path.join(store, d[0:2], d[2:4])).st_mode) == 0o700
        shard = os.path.join(store, d[0:2], d[2:4])
        assert ("." + d + ".tmp") not in os.listdir(shard)   # no adapter temp residue
        assert os.listdir(shard) == [d + ".json"]            # only the published blob
    finally:
        _teardown(adapter, store)


def test_second_identical_persist_is_verified_existing_noop(tmp_path):
    adapter, store = _make_store(tmp_path)
    try:
        snap = _snap()
        d = snap.canonical_payload_digest
        r1 = adapter.persist_snapshot_blob(snap)
        assert r1.status is BlobPersistStatus.PERSISTED_NEW
        r2 = adapter.persist_snapshot_blob(snap)
        assert r2.status is BlobPersistStatus.VERIFIED_EXISTING_NOOP
        assert r2.reason is BlobPersistReason.NONE
        assert r2.created_now is False
        assert r2.durability_verified is True
        shard = os.path.join(store, d[0:2], d[2:4])
        assert ("." + d + ".tmp") not in os.listdir(shard)   # no temp residue after noop
        assert os.listdir(shard) == [d + ".json"]
        with open(_blob_path(store, d), "rb") as f:
            assert f.read() == snap.canonical_bytes          # unchanged
    finally:
        _teardown(adapter, store)


def test_wrong_existing_content_is_collision_and_never_overwritten(tmp_path):
    adapter, store = _make_store(tmp_path)
    try:
        snap = _snap()
        d = snap.canonical_payload_digest
        l1 = os.path.join(store, d[0:2])
        l2 = os.path.join(l1, d[2:4])
        os.mkdir(l1, 0o700); os.chmod(l1, 0o700)
        os.mkdir(l2, 0o700); os.chmod(l2, 0o700)
        target = os.path.join(l2, d + ".json")
        wrong = b"Z" * snap.byte_length                      # same length, wrong bytes
        with open(target, "wb") as f:
            f.write(wrong)
        os.chmod(target, 0o600)

        res = adapter.persist_snapshot_blob(snap)
        assert res.status is BlobPersistStatus.CRITICAL_COLLISION_DETECTED
        assert res.reason is BlobPersistReason.CONTENT_HASH_MISMATCH
        with open(target, "rb") as f:
            assert f.read() == wrong                         # never overwritten
        assert ("." + d + ".tmp") not in os.listdir(l2)      # our temp cleaned
    finally:
        _teardown(adapter, store)
