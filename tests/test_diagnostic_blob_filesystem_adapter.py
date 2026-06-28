"""tests/test_diagnostic_blob_filesystem_adapter.py — TDD for the bounded filesystem blob adapter.

All tests drive an in-memory FakeFS implementing BlobSyscallSeam. NO real directory/file/blob/temp/
root/shard creation, no SQLite/DB/S1/network/runtime. Injection is only through the seam boundary.
"""
import ast
import dataclasses
import errno
import inspect
import stat

import pytest

from approval.diagnostic_snapshot_canonicalizer import build_immutable_snapshot
from approval.diagnostic_blob_persistence_contract import (
    BlobPersistStatus,
    BlobPersistReason,
    BlobPersistResult,
    BlobPersistAdapter,
)
from approval import diagnostic_blob_filesystem_adapter as adapter_mod
from approval.diagnostic_blob_filesystem_adapter import (
    FilesystemBlobPersistAdapter,
    MAX_BLOB_BYTES,
)

ROOT = "/store"
UID = 0


# ----------------------------------------------------------------------------- in-memory fake seam

class _Stat:
    def __init__(self, mode, uid, dev, ino, size):
        self.st_mode = mode
        self.st_uid = uid
        self.st_dev = dev
        self.st_ino = ino
        self.st_size = size


class _Node:
    def __init__(self, kind, mode, uid, dev, ino):
        self.kind = kind          # 'dir' | 'file' | 'symlink'
        self.mode = mode
        self.uid = uid
        self.dev = dev
        self.ino = ino
        self.children = {}
        self.data = bytearray()


class FakeFS:
    """In-memory BlobSyscallSeam. Records calls; supports targeted fault injection."""

    def __init__(self, root_path=ROOT, uid=UID, dev=1):
        self.root_path = root_path
        self.uid = uid
        self.dev = dev
        self._ino = 1
        self.root = self._mk("dir", stat.S_IFDIR | 0o700, uid)
        self.fds = {}
        self._fd = 10
        self.calls = []
        # fault hooks
        self.write_chunk = None
        self.write_zero = False
        self.fail_fsync_first_file = False
        self._file_fsynced = False
        self.rename_errno = None
        self.fchmod_errno = None
        self.unlink_errno = None

    def _mk(self, kind, mode, uid):
        self._ino += 1
        return _Node(kind, mode, uid, self.dev, self._ino)

    def _newfd(self, node):
        self._fd += 1
        self.fds[self._fd] = node
        return self._fd

    def _n(self, fd):
        return self.fds[fd]

    # --- helpers for tests ---
    def seed_dirs(self, *names):
        node = self.root
        for nm in names:
            if nm not in node.children:
                node.children[nm] = self._mk("dir", stat.S_IFDIR | 0o700, self.uid)
            node = node.children[nm]
        return node

    def seed_file(self, parent, name, data, mode=0o600):
        n = self._mk("file", stat.S_IFREG | mode, self.uid)
        n.data = bytearray(data)
        parent.children[name] = n
        return n

    # --- seam ---
    def open_root(self, path):
        self.calls.append(("open_root", path))
        if path != self.root_path:
            raise OSError(errno.ENOENT, "no such root")
        return self._newfd(self.root)

    def open_dir(self, name, dir_fd):
        self.calls.append(("open_dir", name, dir_fd))
        parent = self._n(dir_fd)
        if name not in parent.children:
            raise OSError(errno.ENOENT, name)
        node = parent.children[name]
        if node.kind == "symlink":
            raise OSError(errno.ELOOP, name)
        if node.kind != "dir":
            raise OSError(errno.ENOTDIR, name)
        return self._newfd(node)

    def mkdir(self, name, dir_fd, mode):
        self.calls.append(("mkdir", name, dir_fd, mode))
        parent = self._n(dir_fd)
        if name in parent.children:
            raise OSError(errno.EEXIST, name)
        parent.children[name] = self._mk("dir", stat.S_IFDIR | (mode & 0o777), self.uid)

    def create_exclusive_rw(self, name, dir_fd, mode):
        self.calls.append(("create_exclusive_rw", name, dir_fd, mode))
        parent = self._n(dir_fd)
        if name in parent.children:
            raise OSError(errno.EEXIST, name)
        node = self._mk("file", stat.S_IFREG | (mode & 0o777), self.uid)
        parent.children[name] = node
        return self._newfd(node)

    def open_existing_blob(self, name, dir_fd):
        self.calls.append(("open_existing_blob", name, dir_fd))
        parent = self._n(dir_fd)
        if name not in parent.children:
            raise OSError(errno.ENOENT, name)
        node = parent.children[name]
        if node.kind == "symlink":
            raise OSError(errno.ELOOP, name)
        return self._newfd(node)

    def write(self, fd, data):
        self.calls.append(("write", fd, bytes(data)))
        if self.write_zero:
            return 0
        node = self._n(fd)
        chunk = data[: self.write_chunk] if self.write_chunk is not None else data
        node.data += bytes(chunk)
        return len(chunk)

    def pread(self, fd, count, offset):
        self.calls.append(("pread", fd, count, offset))
        node = self._n(fd)
        return bytes(node.data[offset:offset + count])

    def fstat(self, fd):
        self.calls.append(("fstat", fd))
        node = self._n(fd)
        size = len(node.data) if node.kind == "file" else 0
        return _Stat(node.mode, node.uid, node.dev, node.ino, size)

    def fchmod(self, fd, mode):
        self.calls.append(("fchmod", fd, mode))
        node = self._n(fd)
        if self.fchmod_errno is not None and node.kind == "file":
            raise OSError(self.fchmod_errno, "fchmod")  # target temp only, not shard dirs
        node.mode = (node.mode & ~0o777) | (mode & 0o777)

    def fsync(self, fd):
        self.calls.append(("fsync", fd))
        node = self._n(fd)
        if self.fail_fsync_first_file and node.kind == "file" and not self._file_fsynced:
            self._file_fsynced = True
            raise OSError(errno.EIO, "fsync")
        if node.kind == "file":
            self._file_fsynced = True

    def rename_noreplace(self, old_dir_fd, old_name, new_dir_fd, new_name):
        self.calls.append(("rename_noreplace", old_dir_fd, old_name, new_dir_fd, new_name))
        if self.rename_errno is not None:
            raise OSError(self.rename_errno, "rename_noreplace")
        oldp = self._n(old_dir_fd)
        newp = self._n(new_dir_fd)
        if old_name not in oldp.children:
            raise OSError(errno.ENOENT, old_name)
        if new_name in newp.children:
            raise OSError(errno.EEXIST, new_name)
        newp.children[new_name] = oldp.children.pop(old_name)

    def unlink(self, name, dir_fd):
        self.calls.append(("unlink", name, dir_fd))
        if self.unlink_errno is not None:
            raise OSError(self.unlink_errno, "unlink")
        parent = self._n(dir_fd)
        if name not in parent.children:
            raise OSError(errno.ENOENT, name)
        del parent.children[name]

    def close(self, fd):
        self.calls.append(("close", fd))
        self.fds.pop(fd, None)


# ----------------------------------------------------------------------------- fixtures / helpers

def _envelope(note="diagnostic observation only; not trading/actionability"):
    return {
        "schema_version": "diag-edge-probe-v1",
        "layer": "ECONOMICS",
        "capture_status": "GOLDEN_SAMPLE_OK",
        "fail_closed_reason": None,
        "economics": {"status": "DIAGNOSTIC_OK"},
        "capture": {"slug": "btc-updown-15m-1782651600"},
        "provenance": {"valuation_time_ms": 1782652557293, "capture_start_utc": None,
                       "capture_complete_utc": None, "valuation_to_capture_start_offset_ms": None},
        "markers": ["not_actionable"],
        "driver_note": note,
    }


def _snap(note="diagnostic observation only; not trading/actionability"):
    return build_immutable_snapshot(_envelope(note))


def _adapter(fs):
    return FilesystemBlobPersistAdapter(ROOT, UID, fs)


def _shard_names(snap):
    d = snap.canonical_payload_digest
    return d[0:2], d[2:4], d + ".json", "." + d + ".tmp"


# ----------------------------------------------------------------------------- contract / hygiene

def test_adapter_satisfies_protocol_and_constant():
    fs = FakeFS()
    a = _adapter(fs)
    assert isinstance(a, BlobPersistAdapter)
    assert MAX_BLOB_BYTES == 1_048_576


def test_production_has_no_fake_and_no_forbidden_imports_or_calls():
    src = inspect.getsource(adapter_mod)
    assert "Fake" not in src
    for bad in (".rename(", ".replace(", ".link(", "os.rename", "os.open", "sqlite3", "tempfile"):
        assert bad not in src, f"forbidden token {bad!r}"
    tree = ast.parse(src)
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    forbidden = {"os", "sqlite3", "socket", "requests", "aiohttp", "urllib", "time",
                 "datetime", "random", "secrets", "asyncio", "subprocess", "tempfile"}
    assert not (roots & forbidden), f"forbidden imports: {roots & forbidden}"


# ----------------------------------------------------------------------------- happy path

def test_persisted_new_full_flow_and_fields():
    fs = FakeFS()
    a = _adapter(fs)
    snap = _snap()
    aa, bb, target, temp = _shard_names(snap)
    res = a.persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.PERSISTED_NEW
    assert res.reason is BlobPersistReason.NONE
    assert res.created_now is True
    assert res.durability_verified is True
    assert res.canonical_payload_digest == snap.canonical_payload_digest
    assert res.immutable_snapshot_ref == snap.immutable_snapshot_ref
    assert res.byte_length == snap.byte_length
    # published target exists, temp consumed, content correct
    shard = fs.root.children[aa].children[bb]
    assert target in shard.children
    assert temp not in shard.children
    assert bytes(shard.children[target].data) == snap.canonical_bytes
    assert (shard.children[target].mode & 0o777) == 0o600
    # publication uses rename_noreplace
    assert any(c[0] == "rename_noreplace" for c in fs.calls)


def test_shard_layout_and_modes():
    fs = FakeFS()
    snap = _snap()
    aa, bb, target, _ = _shard_names(snap)
    _adapter(fs).persist_snapshot_blob(snap)
    assert (fs.root.children[aa].mode & 0o777) == 0o700
    assert (fs.root.children[aa].children[bb].mode & 0o777) == 0o700
    assert (fs.root.children[aa].children[bb].children[target].mode & 0o777) == 0o600


def test_new_shard_durability_fsync_order():
    fs = FakeFS()
    snap = _snap()
    aa, bb, _, _ = _shard_names(snap)
    _adapter(fs).persist_snapshot_blob(snap)
    names = [c[0] for c in fs.calls if c[0] in ("mkdir", "open_dir", "fchmod", "fstat", "fsync")]
    i = names.index("mkdir")  # skip construction/root fstat noise
    # first shard level: mkdir -> open_dir -> fchmod -> fstat -> fsync(shard) -> fsync(parent)
    assert names[i:i + 6] == ["mkdir", "open_dir", "fchmod", "fstat", "fsync", "fsync"]


def test_write_all_loops_over_short_writes():
    fs = FakeFS()
    fs.write_chunk = 1  # one byte per write
    snap = _snap()
    res = _adapter(fs).persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.PERSISTED_NEW
    write_calls = [c for c in fs.calls if c[0] == "write"]
    assert len(write_calls) == snap.byte_length


# ----------------------------------------------------------------------------- validation precedence

def test_invalid_digest_no_fs_mutation():
    fs = FakeFS()
    a = _adapter(fs)
    base = len(fs.calls)
    snap = dataclasses.replace(_snap(), canonical_payload_digest="NOThex")
    res = a.persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.SNAPSHOT_VALIDATION_FAILED
    assert res.reason is BlobPersistReason.INVALID_DIGEST
    assert fs.calls[base:] == []  # no filesystem call at all


def test_snapshot_digest_mismatch():
    snap = dataclasses.replace(_snap(), canonical_bytes=b"tampered")
    res = _adapter(FakeFS()).persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.SNAPSHOT_VALIDATION_FAILED
    assert res.reason is BlobPersistReason.SNAPSHOT_DIGEST_MISMATCH


def test_snapshot_ref_mismatch():
    snap = dataclasses.replace(_snap(), immutable_snapshot_ref="diag-edge-probe-v1:sha256:deadbeef")
    res = _adapter(FakeFS()).persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.SNAPSHOT_VALIDATION_FAILED
    assert res.reason is BlobPersistReason.SNAPSHOT_REF_MISMATCH


def test_snapshot_byte_length_mismatch():
    snap = dataclasses.replace(_snap(), byte_length=_snap().byte_length + 1)
    res = _adapter(FakeFS()).persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.SNAPSHOT_VALIDATION_FAILED
    assert res.reason is BlobPersistReason.SNAPSHOT_BYTE_LENGTH_MISMATCH


def test_snapshot_payload_kind_mismatch():
    snap = dataclasses.replace(_snap(), payload_kind="foreign-kind")
    res = _adapter(FakeFS()).persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.SNAPSHOT_VALIDATION_FAILED
    assert res.reason is BlobPersistReason.SNAPSHOT_PAYLOAD_KIND_MISMATCH


def test_byte_length_exceeds_limit():
    big = _snap("X" * (MAX_BLOB_BYTES + 10))
    assert big.byte_length > MAX_BLOB_BYTES
    fs = FakeFS()
    a = _adapter(fs)
    base = len(fs.calls)
    res = a.persist_snapshot_blob(big)
    assert res.status is BlobPersistStatus.SNAPSHOT_VALIDATION_FAILED
    assert res.reason is BlobPersistReason.BYTE_LENGTH_EXCEEDS_LIMIT
    assert fs.calls[base:] == []  # rejected before first mutation


# ----------------------------------------------------------------------------- root identity / metadata

def test_root_identity_change_blocks():
    fs = FakeFS()
    a = _adapter(fs)
    fs.root = fs._mk("dir", stat.S_IFDIR | 0o700, UID)  # replaced root inode at same path
    res = a.persist_snapshot_blob(_snap())
    assert res.status is BlobPersistStatus.BLOCKED_RECOVERY_REQUIRED
    assert res.reason is BlobPersistReason.ROOT_IDENTITY_CHANGED


def test_root_owner_mismatch_blocks():
    fs = FakeFS()
    a = _adapter(fs)
    fs.root.uid = 999
    res = a.persist_snapshot_blob(_snap())
    assert res.status is BlobPersistStatus.BLOCKED_RECOVERY_REQUIRED
    assert res.reason is BlobPersistReason.OWNER_MISMATCH


def test_root_mode_mismatch_blocks():
    fs = FakeFS()
    a = _adapter(fs)
    fs.root.mode = stat.S_IFDIR | 0o755
    res = a.persist_snapshot_blob(_snap())
    assert res.status is BlobPersistStatus.BLOCKED_RECOVERY_REQUIRED
    assert res.reason is BlobPersistReason.MODE_MISMATCH


# ----------------------------------------------------------------------------- write/temp/publish faults

def test_short_write_zero_fails_closed_and_cleans_temp():
    fs = FakeFS()
    fs.write_zero = True
    snap = _snap()
    aa, bb, _, temp = _shard_names(snap)
    res = _adapter(fs).persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.BLOB_PERSIST_FAILED
    assert res.reason is BlobPersistReason.WRITE_FAILED
    assert temp not in fs.root.children[aa].children[bb].children  # bounded cleanup removed our temp


def test_temp_fchmod_failure_is_temp_verify_failed():
    fs = FakeFS()
    fs.fchmod_errno = errno.EPERM
    res = _adapter(fs).persist_snapshot_blob(_snap())
    assert res.status is BlobPersistStatus.BLOB_PERSIST_FAILED
    assert res.reason is BlobPersistReason.TEMP_VERIFY_FAILED


def test_temp_fsync_failure_is_file_fsync_failed():
    fs = FakeFS()
    fs.fail_fsync_first_file = True
    res = _adapter(fs).persist_snapshot_blob(_snap())
    assert res.status is BlobPersistStatus.BLOB_PERSIST_FAILED
    assert res.reason is BlobPersistReason.FILE_FSYNC_FAILED


def test_no_clobber_unavailable_maps_enosys():
    fs = FakeFS()
    fs.rename_errno = errno.ENOSYS
    snap = _snap()
    aa, bb, _, temp = _shard_names(snap)
    res = _adapter(fs).persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.BLOB_PERSIST_FAILED
    assert res.reason is BlobPersistReason.NO_CLOBBER_UNAVAILABLE
    assert temp not in fs.root.children[aa].children[bb].children


def test_publish_other_errno_is_publish_failed():
    fs = FakeFS()
    fs.rename_errno = errno.EROFS
    res = _adapter(fs).persist_snapshot_blob(_snap())
    assert res.status is BlobPersistStatus.BLOB_PERSIST_FAILED
    assert res.reason is BlobPersistReason.PUBLISH_FAILED


# ----------------------------------------------------------------------------- existing target

def test_existing_identical_target_is_verified_noop():
    fs = FakeFS()
    snap = _snap()
    aa, bb, target, temp = _shard_names(snap)
    shard = fs.seed_dirs(aa, bb)
    fs.seed_file(shard, target, snap.canonical_bytes, mode=0o600)
    res = _adapter(fs).persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.VERIFIED_EXISTING_NOOP
    assert res.reason is BlobPersistReason.NONE
    assert res.created_now is False
    assert res.durability_verified is True
    assert temp not in shard.children  # our temp cleaned


def test_existing_mismatched_content_is_collision():
    fs = FakeFS()
    snap = _snap()
    aa, bb, target, _ = _shard_names(snap)
    shard = fs.seed_dirs(aa, bb)
    fs.seed_file(shard, target, b"Z" * snap.byte_length, mode=0o600)  # same length, wrong bytes
    res = _adapter(fs).persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.CRITICAL_COLLISION_DETECTED
    assert res.reason is BlobPersistReason.CONTENT_HASH_MISMATCH
    assert res.durability_verified is False


# ----------------------------------------------------------------------------- cleanup / pre-existing temp

def test_ambiguous_cleanup_preserves_residue():
    fs = FakeFS()
    fs.write_zero = True       # forces WRITE_FAILED -> cleanup attempt
    fs.unlink_errno = errno.EIO  # cleanup unlink fails -> ambiguous
    snap = _snap()
    aa, bb, _, temp = _shard_names(snap)
    res = _adapter(fs).persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.BLOCKED_RECOVERY_REQUIRED
    assert res.reason is BlobPersistReason.TEMP_CLEANUP_AMBIGUOUS
    assert temp in fs.root.children[aa].children[bb].children  # residue preserved


def test_preexisting_deterministic_temp_not_deleted():
    fs = FakeFS()
    snap = _snap()
    aa, bb, _, temp = _shard_names(snap)
    shard = fs.seed_dirs(aa, bb)
    fs.seed_file(shard, temp, b"prior residue", mode=0o600)
    res = _adapter(fs).persist_snapshot_blob(snap)
    assert res.status is BlobPersistStatus.BLOCKED_RECOVERY_REQUIRED
    assert res.reason is BlobPersistReason.AMBIGUOUS_PUBLICATION_STATE
    assert temp in shard.children                       # not deleted
    assert not any(c[0] == "unlink" for c in fs.calls)  # never unlinked a pre-existing temp


# ----------------------------------------------------------------------------- result invariants

def test_result_field_invariants_across_outcomes():
    ok = _adapter(FakeFS()).persist_snapshot_blob(_snap())
    assert ok.durability_verified is True and ok.reason is BlobPersistReason.NONE

    fs = FakeFS()
    fs.rename_errno = errno.ENOSYS
    bad = _adapter(fs).persist_snapshot_blob(_snap())
    assert bad.created_now is False
    assert bad.durability_verified is False
    assert bad.reason is not BlobPersistReason.NONE
