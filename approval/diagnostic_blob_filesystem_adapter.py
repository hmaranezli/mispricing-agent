"""approval/diagnostic_blob_filesystem_adapter.py — bounded content-addressed filesystem blob adapter.

Phase 2B-2B.2 orchestrator implementing the published BlobPersistAdapter contract over an injected
BlobSyscallSeam. It durably persists the canonical bytes of a validated SnapshotReference into a
content-addressed, descriptor-relative layout, exclusively via no-clobber renameat2 publication:

    <root>/<digest[0:2]>/<digest[2:4]>/<digest>.json     (deterministic temp: .<digest>.tmp)

It NEVER uses a clobbering rename/replace/link, never overwrites/repairs/retries/GCs, and never
converts a failed persistence into success. It owns NO DB/S1/network/clock/randomness/market logic and
authorizes nothing — PERSISTED_NEW / VERIFIED_EXISTING_NOOP are durability facts only.

Hardening invariants (2B-2B.2):
  * The validated construction root descriptor is pinned for the adapter lifetime; ``close()`` is
    explicit and idempotent. A fresh no-follow root open + st_dev/st_ino identity check still runs on
    every persist.
  * All permission checks use exact ``stat.S_IMODE(st_mode) == expected`` — setuid/setgid/sticky bits
    are rejected. All metadata checks are descriptor-based (fstat), never path-level.
  * After any EEXIST-target outcome (noop OR collision OR metadata block), a failed bounded temp
    cleanup escalates to BLOCKED_RECOVERY_REQUIRED / TEMP_CLEANUP_AMBIGUOUS.
  * Target-file fsync failure maps to FILE_FSYNC_FAILED; shard-directory fsync failure maps to
    DIRECTORY_FSYNC_FAILED.
  * Tracked descriptors are closed in reverse order; a close failure after an otherwise-successful
    persist downgrades the result to BLOCKED_RECOVERY_REQUIRED / AMBIGUOUS_PUBLICATION_STATE.
"""
import errno
import hashlib
import stat

from approval.diagnostic_blob_persistence_contract import (
    BlobPersistStatus as _S,
    BlobPersistReason as _R,
    BlobPersistResult,
)
from approval.diagnostic_snapshot_canonicalizer import SnapshotReference  # type reference only

MAX_BLOB_BYTES = 1_048_576
_ROOT_MODE = 0o700
_SHARD_MODE = 0o700
_BLOB_MODE = 0o600
_PAYLOAD_KIND = "diag-edge-probe-v1"
_REF_PREFIX = _PAYLOAD_KIND + ":sha256:"
_HEX = frozenset("0123456789abcdef")
_SUCCESS = (_S.PERSISTED_NEW, _S.VERIFIED_EXISTING_NOOP)


def _is_lower_hex64(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in _HEX for c in value)


class FilesystemBlobPersistAdapter:
    """Bounded filesystem blob persist adapter (implements BlobPersistAdapter). Authorizes nothing."""

    def __init__(self, store_root: str, expected_owner_uid: int, syscalls):
        self._store_root = store_root
        self._uid = expected_owner_uid
        self._sc = syscalls
        # Pin + validate the root descriptor at construction; keep it open for the adapter lifetime.
        fd = syscalls.open_root(store_root)
        try:
            st = syscalls.fstat(fd)
            if not stat.S_ISDIR(st.st_mode):
                raise ValueError("store root is not a directory")
            if stat.S_IMODE(st.st_mode) != _ROOT_MODE:
                raise ValueError("store root mode is not exactly 0o700")
            if st.st_uid != expected_owner_uid:
                raise ValueError("store root owner mismatch")
            self._root_identity = (st.st_dev, st.st_ino)
            self._root_fd = fd
        except BaseException:
            try:
                syscalls.close(fd)
            except OSError:
                pass
            raise

    def close(self):
        """Idempotently close the pinned construction root descriptor."""
        fd = self._root_fd
        if fd is None:
            return
        self._root_fd = None
        self._sc.close(fd)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    # ---------------------------------------------------------------------------------------------
    def persist_snapshot_blob(self, snapshot) -> BlobPersistResult:
        sc = self._sc
        digest = snapshot.canonical_payload_digest
        ref = snapshot.immutable_snapshot_ref
        blen = snapshot.byte_length
        data = snapshot.canonical_bytes

        def fail(status, reason):
            return BlobPersistResult(status, reason, digest, ref, blen, False, False)

        # -- closed adapter: fail closed immediately, no fresh seam operation --
        if self._root_fd is None:
            return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.AMBIGUOUS_PUBLICATION_STATE)

        # -- phase 0: pure snapshot preflight (no filesystem mutation) --
        if not _is_lower_hex64(digest):
            return fail(_S.SNAPSHOT_VALIDATION_FAILED, _R.INVALID_DIGEST)
        if hashlib.sha256(data).hexdigest() != digest:
            return fail(_S.SNAPSHOT_VALIDATION_FAILED, _R.SNAPSHOT_DIGEST_MISMATCH)
        if ref != _REF_PREFIX + digest:
            return fail(_S.SNAPSHOT_VALIDATION_FAILED, _R.SNAPSHOT_REF_MISMATCH)
        if blen != len(data):
            return fail(_S.SNAPSHOT_VALIDATION_FAILED, _R.SNAPSHOT_BYTE_LENGTH_MISMATCH)
        if snapshot.payload_kind != _PAYLOAD_KIND:
            return fail(_S.SNAPSHOT_VALIDATION_FAILED, _R.SNAPSHOT_PAYLOAD_KIND_MISMATCH)
        if blen > MAX_BLOB_BYTES:
            return fail(_S.SNAPSHOT_VALIDATION_FAILED, _R.BYTE_LENGTH_EXCEEDS_LIMIT)

        target_name = digest + ".json"
        temp_name = "." + digest + ".tmp"
        open_fds = []

        def track(fd):
            open_fds.append(fd)
            return fd

        def write_all(fd):
            total = 0
            while total < blen:
                try:
                    n = sc.write(fd, data[total:])
                except OSError:
                    return False
                if not isinstance(n, int) or n <= 0:
                    return False
                total += n
            return True

        def read_back(fd):
            out = bytearray()
            while len(out) < blen:
                try:
                    chunk = sc.pread(fd, blen - len(out), len(out))
                except OSError:
                    return None
                if not chunk:
                    return None
                out += chunk
            return bytes(out)

        def cleanup_temp(shard_fd, temp_id):
            # Remove ONLY a temp we created, under reopened inode-identity proof. False => ambiguous.
            if temp_id is None:
                return False
            try:
                fd = sc.open_existing_blob(temp_name, shard_fd)
            except OSError:
                return False
            ok = False
            close_failed = False
            try:
                st = sc.fstat(fd)
                ok = (st.st_dev, st.st_ino) == temp_id
            except OSError:
                ok = False
            finally:
                try:
                    sc.close(fd)
                except OSError:
                    close_failed = True   # unproven descriptor close => ambiguous, never treat as clean
            if not ok or close_failed:
                return False
            try:
                sc.unlink(temp_name, shard_fd)
                sc.fsync(shard_fd)
                return True
            except OSError:
                return False

        def fail_after_cleanup(shard_fd, temp_id, status, reason):
            if cleanup_temp(shard_fd, temp_id):
                return fail(status, reason)
            return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.TEMP_CLEANUP_AMBIGUOUS)

        def existing_target(shard_fd, temp_id):
            try:
                tgt_fd = track(sc.open_existing_blob(target_name, shard_fd))
            except OSError as e:
                outcome = fail(_S.BLOCKED_RECOVERY_REQUIRED,
                               _R.SYMLINK_OR_NONREGULAR if e.errno == errno.ELOOP
                               else _R.AMBIGUOUS_PUBLICATION_STATE)
                return _finish_existing(shard_fd, temp_id, outcome)
            try:
                st = sc.fstat(tgt_fd)
            except OSError:
                return _finish_existing(shard_fd, temp_id,
                                        fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.AMBIGUOUS_PUBLICATION_STATE))
            if not stat.S_ISREG(st.st_mode):
                outcome = fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.SYMLINK_OR_NONREGULAR)
            elif st.st_uid != self._uid:
                outcome = fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.OWNER_MISMATCH)
            elif stat.S_IMODE(st.st_mode) != _BLOB_MODE:
                outcome = fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.MODE_MISMATCH)
            elif st.st_size != blen:
                outcome = fail(_S.CRITICAL_COLLISION_DETECTED, _R.CONTENT_HASH_MISMATCH)
            else:
                rb = read_back(tgt_fd)
                if rb is None or len(rb) != blen or hashlib.sha256(rb).hexdigest() != digest:
                    outcome = fail(_S.CRITICAL_COLLISION_DETECTED, _R.CONTENT_HASH_MISMATCH)
                else:
                    try:
                        sc.fsync(tgt_fd)
                    except OSError:
                        return _finish_existing(shard_fd, temp_id,
                                                fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.FILE_FSYNC_FAILED))
                    try:
                        sc.fsync(shard_fd)
                    except OSError:
                        return _finish_existing(shard_fd, temp_id,
                                                fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.DIRECTORY_FSYNC_FAILED))
                    outcome = BlobPersistResult(_S.VERIFIED_EXISTING_NOOP, _R.NONE, digest, ref,
                                                blen, False, True)
            return _finish_existing(shard_fd, temp_id, outcome)

        def _finish_existing(shard_fd, temp_id, outcome):
            # Any EEXIST-target outcome (noop/collision/block) escalates on cleanup ambiguity.
            if not cleanup_temp(shard_fd, temp_id):
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.TEMP_CLEANUP_AMBIGUOUS)
            return outcome

        def body():
            # -- phase 1: fresh root open + descriptor identity/metadata --
            try:
                root_fd = track(sc.open_root(self._store_root))
            except OSError as e:
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, _root_open_reason(e))
            try:
                rst = sc.fstat(root_fd)
            except OSError:
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.AMBIGUOUS_PUBLICATION_STATE)
            mismatch = self._dir_metadata_reason(rst)
            if mismatch is not None:
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, mismatch)
            if (rst.st_dev, rst.st_ino) != self._root_identity:
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.ROOT_IDENTITY_CHANGED)

            # -- phase 2: descriptor-relative shard creation/verification --
            l1, err = self._open_or_create_shard(root_fd, digest[0:2], track)
            if err is not None:
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, err)
            shard_fd, err = self._open_or_create_shard(l1, digest[2:4], track)
            if err is not None:
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, err)

            # -- phase 3: temp create + write + descriptor verification + read-back --
            try:
                temp_fd = track(sc.create_exclusive_rw(temp_name, shard_fd, _BLOB_MODE))
            except OSError as e:
                if e.errno == errno.EEXIST:
                    return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.AMBIGUOUS_PUBLICATION_STATE)
                return fail(_S.BLOB_PERSIST_FAILED, _R.TEMP_CREATE_FAILED)
            try:
                tst = sc.fstat(temp_fd)
                temp_id = (tst.st_dev, tst.st_ino)
            except OSError:
                return fail_after_cleanup(shard_fd, None, _S.BLOB_PERSIST_FAILED, _R.TEMP_VERIFY_FAILED)

            if not write_all(temp_fd):
                return fail_after_cleanup(shard_fd, temp_id, _S.BLOB_PERSIST_FAILED, _R.WRITE_FAILED)
            try:
                sc.fchmod(temp_fd, _BLOB_MODE)
                vst = sc.fstat(temp_fd)
            except OSError:
                return fail_after_cleanup(shard_fd, temp_id, _S.BLOB_PERSIST_FAILED, _R.TEMP_VERIFY_FAILED)
            if not (stat.S_ISREG(vst.st_mode) and vst.st_uid == self._uid
                    and stat.S_IMODE(vst.st_mode) == _BLOB_MODE and vst.st_size == blen):
                return fail_after_cleanup(shard_fd, temp_id, _S.BLOB_PERSIST_FAILED, _R.TEMP_VERIFY_FAILED)
            try:
                sc.fsync(temp_fd)
            except OSError:
                return fail_after_cleanup(shard_fd, temp_id, _S.BLOB_PERSIST_FAILED, _R.FILE_FSYNC_FAILED)
            rb = read_back(temp_fd)
            if rb is None or len(rb) != blen or hashlib.sha256(rb).hexdigest() != digest:
                return fail_after_cleanup(shard_fd, temp_id, _S.BLOB_PERSIST_FAILED, _R.TEMP_VERIFY_FAILED)

            # -- phase 4: no-clobber publication --
            try:
                sc.rename_noreplace(shard_fd, temp_name, shard_fd, target_name)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    return existing_target(shard_fd, temp_id)
                if e.errno == errno.ENOSYS:
                    return fail_after_cleanup(shard_fd, temp_id, _S.BLOB_PERSIST_FAILED,
                                              _R.NO_CLOBBER_UNAVAILABLE)
                return fail_after_cleanup(shard_fd, temp_id, _S.BLOB_PERSIST_FAILED, _R.PUBLISH_FAILED)

            # published: temp consumed by rename. Durably commit the new directory entry.
            try:
                sc.fsync(shard_fd)
            except OSError:
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.DIRECTORY_FSYNC_FAILED)

            # reopen target, verify metadata + read-back hash, fsync target + shard.
            try:
                tgt_fd = track(sc.open_existing_blob(target_name, shard_fd))
                fst = sc.fstat(tgt_fd)
            except OSError:
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.FINAL_READBACK_FAILED)
            if not (stat.S_ISREG(fst.st_mode) and fst.st_uid == self._uid
                    and stat.S_IMODE(fst.st_mode) == _BLOB_MODE and fst.st_size == blen):
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.FINAL_READBACK_FAILED)
            try:
                sc.fsync(tgt_fd)        # target file durability
            except OSError:
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.FILE_FSYNC_FAILED)
            rb2 = read_back(tgt_fd)
            if rb2 is None or len(rb2) != blen or hashlib.sha256(rb2).hexdigest() != digest:
                return fail(_S.CRITICAL_COLLISION_DETECTED, _R.CONTENT_HASH_MISMATCH)
            try:
                sc.fsync(shard_fd)      # final directory-entry durability
            except OSError:
                return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.DIRECTORY_FSYNC_FAILED)

            return BlobPersistResult(_S.PERSISTED_NEW, _R.NONE, digest, ref, blen, True, True)

        try:
            result = body()
        except BaseException:
            self._close_all_reverse(open_fds)
            raise
        # Close tracked descriptors in reverse order; do not swallow a close failure on success.
        close_failed = self._close_all_reverse(open_fds)
        if close_failed and result.status in _SUCCESS:
            return fail(_S.BLOCKED_RECOVERY_REQUIRED, _R.AMBIGUOUS_PUBLICATION_STATE)
        return result

    # ---------------------------------------------------------------------------------------------
    def _close_all_reverse(self, open_fds):
        close_failed = False
        for fd in reversed(open_fds):
            try:
                self._sc.close(fd)
            except OSError:
                close_failed = True
        return close_failed

    def _dir_metadata_reason(self, st):
        if not stat.S_ISDIR(st.st_mode):
            return _R.SYMLINK_OR_NONREGULAR
        if st.st_uid != self._uid:
            return _R.OWNER_MISMATCH
        if stat.S_IMODE(st.st_mode) != _SHARD_MODE:
            return _R.MODE_MISMATCH
        return None

    def _open_or_create_shard(self, parent_fd, name, track):
        sc = self._sc
        created = False
        try:
            sc.mkdir(name, parent_fd, _SHARD_MODE)
            created = True
        except OSError as e:
            if e.errno != errno.EEXIST:
                return None, _R.SHARD_DURABILITY_FAILED
        try:
            fd = track(sc.open_dir(name, parent_fd))
        except OSError as e:
            if e.errno in (errno.ELOOP, errno.ENOTDIR):
                return None, _R.SYMLINK_OR_NONREGULAR
            return None, _R.SHARD_DURABILITY_FAILED
        if created:
            try:
                sc.fchmod(fd, _SHARD_MODE)
            except OSError:
                return None, _R.SHARD_DURABILITY_FAILED
        try:
            st = sc.fstat(fd)
        except OSError:
            return None, _R.SHARD_DURABILITY_FAILED
        reason = self._dir_metadata_reason(st)
        if reason is not None:
            return None, reason
        if created:
            try:
                sc.fsync(fd)          # durably commit the new shard
                sc.fsync(parent_fd)   # ...and its directory entry in the parent
            except OSError:
                return None, _R.SHARD_DURABILITY_FAILED
        return fd, None


def _root_open_reason(e):
    if e.errno == errno.ELOOP:
        return _R.SYMLINK_OR_NONREGULAR
    return _R.ROOT_MISSING
