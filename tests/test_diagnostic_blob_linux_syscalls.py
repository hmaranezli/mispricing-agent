"""tests/test_diagnostic_blob_linux_syscalls.py — TDD for the minimal Linux blob syscall seam (2B-2B.1).

Mechanism-seam ONLY: thin wrappers over os.* (dir_fd-relative) plus an isolated libc renameat2(
RENAME_NOREPLACE). NO orchestration/status/adapter logic. Tests use monkeypatch/fakes and a fake libc;
they perform NO real filesystem mutation. Patching is done through the production module namespace.
"""
import ast
import ctypes
import errno
import inspect
import os
import types

import pytest

from approval import diagnostic_blob_linux_syscalls as mod
from approval.diagnostic_blob_linux_syscalls import BlobSyscallSeam, LinuxBlobSyscalls


_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_CREATE_FLAGS = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
_EXISTING_FLAGS = os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC

_SENTINEL = object()


class FakeBlobSyscalls:
    """Structural-only stand-in implementing every BlobSyscallSeam method. Test-module local."""

    def open_root(self, path): return 3
    def open_dir(self, name, dir_fd): return 4
    def mkdir(self, name, dir_fd, mode): return None
    def create_exclusive_rw(self, name, dir_fd, mode): return 5
    def open_existing_blob(self, name, dir_fd): return 6
    def write(self, fd, data): return len(data)
    def pread(self, fd, count, offset): return b""
    def fstat(self, fd): return os.stat_result(range(10))
    def fchmod(self, fd, mode): return None
    def fsync(self, fd): return None
    def rename_noreplace(self, old_dir_fd, old_name, new_dir_fd, new_name): return None
    def unlink(self, name, dir_fd): return None
    def close(self, fd): return None


def _open_recorder():
    calls = []

    def rec(path, flags, mode=_SENTINEL, *, dir_fd=_SENTINEL):
        calls.append({"path": path, "flags": flags, "mode": mode, "dir_fd": dir_fd})
        return 7

    return calls, rec


def _linux_with_fake_libc(monkeypatch, renameat2=None):
    """Construct LinuxBlobSyscalls with an injected fake libc (no real rename ever runs)."""
    ns = types.SimpleNamespace()
    if renameat2 is not None:
        ns.renameat2 = renameat2
    monkeypatch.setattr(mod, "_current_platform", lambda: "linux")
    monkeypatch.setattr(mod, "_load_libc", lambda: ns)
    return LinuxBlobSyscalls()


# --- contract / hygiene ----------------------------------------------------------------------------

def test_fake_structurally_satisfies_seam():
    assert isinstance(FakeBlobSyscalls(), BlobSyscallSeam)


def test_fake_exists_only_in_test_module():
    assert getattr(mod, "FakeBlobSyscalls", None) is None


def test_production_source_has_no_forbidden_tokens_or_imports():
    src = inspect.getsource(mod)
    for bad in ("os.rename", "os.replace", "os.link", ".syscall(", "syscall(", "SYS_"):
        assert bad not in src, f"forbidden token {bad!r} in production source"
    tree = ast.parse(src)
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    forbidden = {"sqlite3", "socket", "requests", "aiohttp", "urllib", "time", "datetime",
                 "random", "secrets", "asyncio", "subprocess"}
    assert not (roots & forbidden), f"forbidden imports: {roots & forbidden}"


# --- os wrapper flag/forwarding evidence -----------------------------------------------------------

def test_open_root_exact_flags(monkeypatch):
    calls, rec = _open_recorder()
    monkeypatch.setattr(mod, "_os_open", rec)
    s = _linux_with_fake_libc(monkeypatch, renameat2=lambda *a: 0)
    fd = s.open_root("/root/x")
    assert fd == 7
    assert calls == [{"path": "/root/x", "flags": _DIR_FLAGS, "mode": _SENTINEL, "dir_fd": _SENTINEL}]


def test_open_dir_exact_flags_and_dir_fd(monkeypatch):
    calls, rec = _open_recorder()
    monkeypatch.setattr(mod, "_os_open", rec)
    s = _linux_with_fake_libc(monkeypatch, renameat2=lambda *a: 0)
    s.open_dir("ab", 3)
    assert calls[0]["flags"] == _DIR_FLAGS
    assert calls[0]["dir_fd"] == 3
    assert calls[0]["path"] == "ab"


def test_create_exclusive_rw_exact_flags_and_mode(monkeypatch):
    calls, rec = _open_recorder()
    monkeypatch.setattr(mod, "_os_open", rec)
    s = _linux_with_fake_libc(monkeypatch, renameat2=lambda *a: 0)
    s.create_exclusive_rw(".tmp", 4, 0o600)
    assert calls[0]["flags"] == _CREATE_FLAGS
    assert calls[0]["flags"] & os.O_RDWR
    assert calls[0]["mode"] == 0o600
    assert calls[0]["dir_fd"] == 4


def test_open_existing_blob_exact_flags(monkeypatch):
    calls, rec = _open_recorder()
    monkeypatch.setattr(mod, "_os_open", rec)
    s = _linux_with_fake_libc(monkeypatch, renameat2=lambda *a: 0)
    s.open_existing_blob("digest.json", 4)
    assert calls[0]["flags"] == _EXISTING_FLAGS
    assert calls[0]["dir_fd"] == 4


def test_mkdir_forwards_mode_and_dir_fd(monkeypatch):
    calls = []
    monkeypatch.setattr(mod, "_os_mkdir", lambda name, mode, *, dir_fd: calls.append((name, mode, dir_fd)))
    s = _linux_with_fake_libc(monkeypatch, renameat2=lambda *a: 0)
    s.mkdir("ab", 3, 0o700)
    assert calls == [("ab", 0o700, 3)]


def test_unlink_forwards_dir_fd(monkeypatch):
    calls = []
    monkeypatch.setattr(mod, "_os_unlink", lambda name, *, dir_fd: calls.append((name, dir_fd)))
    s = _linux_with_fake_libc(monkeypatch, renameat2=lambda *a: 0)
    s.unlink(".tmp", 5)
    assert calls == [(".tmp", 5)]


def test_write_pread_fchmod_fsync_close_delegate(monkeypatch):
    log = []
    monkeypatch.setattr(mod, "_os_write", lambda fd, data: log.append(("write", fd, data)) or len(data))
    monkeypatch.setattr(mod, "_os_pread", lambda fd, n, off: log.append(("pread", fd, n, off)) or b"xy")
    monkeypatch.setattr(mod, "_os_fchmod", lambda fd, mode: log.append(("fchmod", fd, mode)))
    monkeypatch.setattr(mod, "_os_fsync", lambda fd: log.append(("fsync", fd)))
    monkeypatch.setattr(mod, "_os_close", lambda fd: log.append(("close", fd)))
    s = _linux_with_fake_libc(monkeypatch, renameat2=lambda *a: 0)
    assert s.write(8, b"abc") == 3
    assert s.pread(8, 2, 4) == b"xy"
    s.fchmod(8, 0o600)
    s.fsync(8)
    s.close(8)
    assert log == [("write", 8, b"abc"), ("pread", 8, 2, 4), ("fchmod", 8, 0o600),
                   ("fsync", 8), ("close", 8)]


def test_fstat_oserror_preserved(monkeypatch):
    def boom(fd):
        raise OSError(errno.EBADF, "bad fd")
    monkeypatch.setattr(mod, "_os_fstat", boom)
    s = _linux_with_fake_libc(monkeypatch, renameat2=lambda *a: 0)
    with pytest.raises(OSError) as ei:
        s.fstat(9)
    assert ei.value.errno == errno.EBADF


def test_fsync_oserror_preserved(monkeypatch):
    def boom(fd):
        raise OSError(errno.EIO, "io")
    monkeypatch.setattr(mod, "_os_fsync", boom)
    s = _linux_with_fake_libc(monkeypatch, renameat2=lambda *a: 0)
    with pytest.raises(OSError) as ei:
        s.fsync(9)
    assert ei.value.errno == errno.EIO


# --- renameat2 wrapper -----------------------------------------------------------------------------

def test_rename_noreplace_passes_fds_fsencoded_names_and_flag(monkeypatch):
    seen = []

    def fake_renameat2(old_fd, old_b, new_fd, new_b, flags):
        ctypes.set_errno(0)
        seen.append((old_fd, old_b, new_fd, new_b, flags))
        return 0

    s = _linux_with_fake_libc(monkeypatch, renameat2=fake_renameat2)
    s.rename_noreplace(3, "tmpname", 3, "target.json")
    assert seen == [(3, os.fsencode("tmpname"), 3, os.fsencode("target.json"), 1)]


def test_rename_noreplace_eexist_preserved(monkeypatch):
    def fake_renameat2(*a):
        ctypes.set_errno(errno.EEXIST)
        return -1
    s = _linux_with_fake_libc(monkeypatch, renameat2=fake_renameat2)
    with pytest.raises(OSError) as ei:
        s.rename_noreplace(3, "t", 3, "target.json")
    assert ei.value.errno == errno.EEXIST


def test_rename_noreplace_errno_zero_becomes_eio(monkeypatch):
    def fake_renameat2(*a):
        return -1  # failure but leaves errno cleared
    s = _linux_with_fake_libc(monkeypatch, renameat2=fake_renameat2)
    with pytest.raises(OSError) as ei:
        s.rename_noreplace(3, "t", 3, "target.json")
    assert ei.value.errno == errno.EIO


def test_rename_noreplace_rejects_embedded_nul_before_libc(monkeypatch):
    def must_not_call(*a):
        raise AssertionError("libc renameat2 must not be reached for NUL names")
    s = _linux_with_fake_libc(monkeypatch, renameat2=must_not_call)
    with pytest.raises(ValueError):
        s.rename_noreplace(3, "bad\x00name", 3, "target.json")


def test_missing_libc_symbol_yields_enosys(monkeypatch):
    monkeypatch.setattr(mod, "_current_platform", lambda: "linux")
    monkeypatch.setattr(mod, "_load_libc", lambda: types.SimpleNamespace())  # no renameat2 attribute
    with pytest.raises(OSError) as ei:
        LinuxBlobSyscalls()
    assert ei.value.errno == errno.ENOSYS


def test_non_linux_construction_yields_enosys(monkeypatch):
    monkeypatch.setattr(mod, "_current_platform", lambda: "darwin")
    with pytest.raises(OSError) as ei:
        LinuxBlobSyscalls()
    assert ei.value.errno == errno.ENOSYS


def test_linux_instance_structurally_satisfies_seam(monkeypatch):
    s = _linux_with_fake_libc(monkeypatch, renameat2=lambda *a: 0)
    assert isinstance(s, BlobSyscallSeam)
