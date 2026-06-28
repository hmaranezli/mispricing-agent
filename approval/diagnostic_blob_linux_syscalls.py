"""approval/diagnostic_blob_linux_syscalls.py — minimal Linux blob syscall seam (Phase 2B-2B.1).

Mechanism-ONLY layer for the future filesystem blob persist adapter. It is the single production wrapper
over descriptor-relative os.* operations plus an isolated libc renameat2(RENAME_NOREPLACE) binding. It
makes NO status/reason/business decisions, owns NO orchestration, and contains NO DB/S1/network/clock/
market logic. Raw return values and raw OSError values pass through unchanged.

Publication is exclusively no-clobber renameat2(RENAME_NOREPLACE); there is deliberately no ordinary
clobbering move or hard-link fallback. The libc symbol is resolved once at construction via dlsym; no
raw kernel-number invocation and no architecture-specific number table is used.
"""
import ctypes
import errno as _errno
import os
import sys
from typing import Protocol, runtime_checkable

# Module-namespace bindings so tests patch THROUGH this module, never the global os module.
_os_open = os.open
_os_mkdir = os.mkdir
_os_unlink = os.unlink
_os_write = os.write
_os_pread = os.pread
_os_fstat = os.fstat
_os_fchmod = os.fchmod
_os_fsync = os.fsync
_os_close = os.close

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_CREATE_FLAGS = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
_EXISTING_FLAGS = os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC

_RENAME_NOREPLACE = 1


def _current_platform() -> str:
    """Indirection so tests can simulate a non-Linux platform without mutating global sys state."""
    return sys.platform


def _load_libc():
    """Load libc with errno support. Indirection so tests can inject a fake libc object."""
    return ctypes.CDLL(None, use_errno=True)


@runtime_checkable
class BlobSyscallSeam(Protocol):
    """Minimal injectable syscall surface for the persistence algorithm. Mechanism only."""

    def open_root(self, path: str) -> int: ...
    def open_dir(self, name: str, dir_fd: int) -> int: ...
    def mkdir(self, name: str, dir_fd: int, mode: int) -> None: ...
    def create_exclusive_rw(self, name: str, dir_fd: int, mode: int) -> int: ...
    def open_existing_blob(self, name: str, dir_fd: int) -> int: ...
    def write(self, fd: int, data: bytes) -> int: ...
    def pread(self, fd: int, count: int, offset: int) -> bytes: ...
    def fstat(self, fd: int) -> os.stat_result: ...
    def fchmod(self, fd: int, mode: int) -> None: ...
    def fsync(self, fd: int) -> None: ...
    def rename_noreplace(self, old_dir_fd: int, old_name: str, new_dir_fd: int, new_name: str) -> None: ...
    def unlink(self, name: str, dir_fd: int) -> None: ...
    def close(self, fd: int) -> None: ...


class LinuxBlobSyscalls:
    """Thin Linux mechanism wrappers. No business/status decisions; raw OSError passes through."""

    def __init__(self):
        if _current_platform() != "linux":
            raise OSError(_errno.ENOSYS, "renameat2 seam requires linux")
        libc = _load_libc()
        symbol = getattr(libc, "renameat2", None)
        if symbol is None:
            raise OSError(_errno.ENOSYS, "libc renameat2 symbol unavailable")
        symbol.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        symbol.restype = ctypes.c_int
        self._renameat2 = symbol

    # --- descriptor-relative os wrappers ---------------------------------------------------------
    def open_root(self, path: str) -> int:
        return _os_open(path, _DIR_FLAGS)

    def open_dir(self, name: str, dir_fd: int) -> int:
        return _os_open(name, _DIR_FLAGS, dir_fd=dir_fd)

    def mkdir(self, name: str, dir_fd: int, mode: int) -> None:
        _os_mkdir(name, mode, dir_fd=dir_fd)

    def create_exclusive_rw(self, name: str, dir_fd: int, mode: int) -> int:
        return _os_open(name, _CREATE_FLAGS, mode, dir_fd=dir_fd)

    def open_existing_blob(self, name: str, dir_fd: int) -> int:
        return _os_open(name, _EXISTING_FLAGS, dir_fd=dir_fd)

    def write(self, fd: int, data: bytes) -> int:
        return _os_write(fd, data)

    def pread(self, fd: int, count: int, offset: int) -> bytes:
        return _os_pread(fd, count, offset)

    def fstat(self, fd: int) -> os.stat_result:
        return _os_fstat(fd)

    def fchmod(self, fd: int, mode: int) -> None:
        _os_fchmod(fd, mode)

    def fsync(self, fd: int) -> None:
        _os_fsync(fd)

    def unlink(self, name: str, dir_fd: int) -> None:
        _os_unlink(name, dir_fd=dir_fd)

    def close(self, fd: int) -> None:
        _os_close(fd)

    # --- isolated no-clobber publication ---------------------------------------------------------
    def rename_noreplace(self, old_dir_fd: int, old_name: str, new_dir_fd: int, new_name: str) -> None:
        old_bytes = os.fsencode(old_name)
        new_bytes = os.fsencode(new_name)
        if b"\x00" in old_bytes or b"\x00" in new_bytes:
            raise ValueError("embedded NUL byte in name")
        ctypes.set_errno(0)
        ret = self._renameat2(old_dir_fd, old_bytes, new_dir_fd, new_bytes, _RENAME_NOREPLACE)
        if ret != 0:
            err = ctypes.get_errno()
            if err == 0:
                err = _errno.EIO
            raise OSError(err, os.strerror(err))
