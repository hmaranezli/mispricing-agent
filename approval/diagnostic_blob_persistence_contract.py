"""approval/diagnostic_blob_persistence_contract.py — PURE types/contract for the future blob adapter.

This is the Phase 2B-2A interface/value-contract slice ONLY. It defines the status/reason enums, the
frozen ``BlobPersistResult`` value object, and the ``BlobPersistAdapter`` typing.Protocol for the future
content-addressed filesystem blob persistence adapter. It contains NO filesystem, durability, database,
S1, runtime, or network implementation — no ``os``/``pathlib``/``sqlite3``/``tempfile``/``ctypes``, no
``open``/``rename``/``renameat2``/``unlink``/``fsync``/``mkdir``/``chmod``/``stat``, no clock, no
randomness, no subprocess. It performs no work and authorizes nothing.

The single canonical bridge object ``SnapshotReference`` is REUSED from
``approval.diagnostic_snapshot_canonicalizer`` and is never re-defined here.

Contract pinned for the future adapter that implements ``BlobPersistAdapter`` (documentation only — none
of this is implemented in this slice):

* The ``immutable_snapshot_ref`` is LOGICAL (``diag-edge-probe-v1:sha256:<lowercase_digest>``) and is
  NEVER a filesystem path. The target path is DIGEST-DERIVED (shard dirs from the digest) and resolved
  strictly beneath an explicit, caller-supplied, descriptor-validated store root. No hidden global/
  default/production path.
* SnapshotReference validation (``sha256(canonical_bytes)==canonical_payload_digest``; logical ref embeds
  that same digest; ``byte_length`` matches; ``payload_kind`` matches) AND a hard maximum byte-length
  check occur BEFORE the first filesystem mutation.
* The exact byte limit is a SEPARATELY pinned adapter policy constant defined in the future adapter, NOT
  here; it MUST NOT silently modify Phase 2B-1 canonicalization behavior. (No numeric limit/``1 MB`` value
  is introduced in this slice; ``BYTE_LENGTH_EXCEEDS_LIMIT`` is only the reason code reserved for it.)
* No process-global ``umask`` mutation. Exact modes are established through explicit create modes,
  ``fchmod``, and descriptor-based (``fstat``) verification — not path-level ``os.stat``/``chmod``.
* Temp and target live in the SAME shard directory and filesystem (so publication ``rename`` is atomic
  and intra-filesystem).
* Durable-write order (future adapter): write-all -> ``fchmod``/``fstat`` -> ``fsync(temp)`` -> temp hash
  verification -> ``renameat2(RENAME_NOREPLACE)`` -> ``fsync(shard directory)`` -> reopen/``fstat`` ->
  ``fsync(target)`` -> final read-back hash -> ``fsync(shard directory)``.
* Ordinary ``rename``/``replace`` (clobbering) is FORBIDDEN. If ``renameat2``/``RENAME_NOREPLACE`` (or a
  rigorously-defined no-clobber equivalent) is unavailable on the target kernel/filesystem, the adapter
  FAILS CLOSED (``NO_CLOBBER_UNAVAILABLE``).
* An existing IDENTICAL target requires target-fsync, directory-fsync, descriptor metadata verification,
  and a read-back hash before returning ``VERIFIED_EXISTING_NOOP`` with ``durability_verified=True``.
* Every newly created shard is descriptor-verified and durably committed by ``fsync(new_shard_fd)`` plus
  ``fsync(parent_fd)``.
* Root identity requires BOTH a pinned validated root descriptor captured at construction AND a fresh
  no-follow directory open of the configured pathname on every persist, with ``st_dev``/``st_ino``
  equality (else ``ROOT_IDENTITY_CHANGED``).
* Known pre-publication temp cleanup is permitted ONLY under bounded inode-identity proof, followed by
  ``unlink`` and parent-directory fsync; any ambiguous residue/publication state is
  ``BLOCKED_RECOVERY_REQUIRED``.
* No overwrite, silent repair, automatic retry, GC, or S1 row attempt. A failed persistence is never
  transformed into success.
* ``PERSISTED_NEW`` and ``VERIFIED_EXISTING_NOOP`` authorize NOTHING — not an S1 append, not an approval,
  not actionability/capacity.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# Single canonical bridge object — reused, never re-defined.
from approval.diagnostic_snapshot_canonicalizer import SnapshotReference

__all__ = [
    "BlobPersistStatus",
    "BlobPersistReason",
    "BlobPersistResult",
    "BlobPersistAdapter",
]


class BlobPersistStatus(str, Enum):
    """Closed, deterministic outcome statuses. No generic SUCCESS status exists by design."""

    PERSISTED_NEW = "PERSISTED_NEW"
    VERIFIED_EXISTING_NOOP = "VERIFIED_EXISTING_NOOP"
    SNAPSHOT_VALIDATION_FAILED = "SNAPSHOT_VALIDATION_FAILED"
    BLOB_PERSIST_FAILED = "BLOB_PERSIST_FAILED"
    CRITICAL_COLLISION_DETECTED = "CRITICAL_COLLISION_DETECTED"
    BLOCKED_RECOVERY_REQUIRED = "BLOCKED_RECOVERY_REQUIRED"


class BlobPersistReason(str, Enum):
    """Closed, deterministic reason codes — stable audit-comparable strings, never free text."""

    NONE = "NONE"
    INVALID_DIGEST = "INVALID_DIGEST"
    SNAPSHOT_DIGEST_MISMATCH = "SNAPSHOT_DIGEST_MISMATCH"
    SNAPSHOT_REF_MISMATCH = "SNAPSHOT_REF_MISMATCH"
    SNAPSHOT_BYTE_LENGTH_MISMATCH = "SNAPSHOT_BYTE_LENGTH_MISMATCH"
    SNAPSHOT_PAYLOAD_KIND_MISMATCH = "SNAPSHOT_PAYLOAD_KIND_MISMATCH"
    BYTE_LENGTH_EXCEEDS_LIMIT = "BYTE_LENGTH_EXCEEDS_LIMIT"
    ROOT_MISSING = "ROOT_MISSING"
    ROOT_IDENTITY_CHANGED = "ROOT_IDENTITY_CHANGED"
    OWNER_MISMATCH = "OWNER_MISMATCH"
    MODE_MISMATCH = "MODE_MISMATCH"
    SYMLINK_OR_NONREGULAR = "SYMLINK_OR_NONREGULAR"
    SHARD_DURABILITY_FAILED = "SHARD_DURABILITY_FAILED"
    TEMP_CREATE_FAILED = "TEMP_CREATE_FAILED"
    WRITE_FAILED = "WRITE_FAILED"
    FILE_FSYNC_FAILED = "FILE_FSYNC_FAILED"
    TEMP_VERIFY_FAILED = "TEMP_VERIFY_FAILED"
    NO_CLOBBER_UNAVAILABLE = "NO_CLOBBER_UNAVAILABLE"
    PUBLISH_FAILED = "PUBLISH_FAILED"
    DIRECTORY_FSYNC_FAILED = "DIRECTORY_FSYNC_FAILED"
    FINAL_READBACK_FAILED = "FINAL_READBACK_FAILED"
    CONTENT_HASH_MISMATCH = "CONTENT_HASH_MISMATCH"
    TEMP_CLEANUP_AMBIGUOUS = "TEMP_CLEANUP_AMBIGUOUS"
    AMBIGUOUS_PUBLICATION_STATE = "AMBIGUOUS_PUBLICATION_STATE"


@dataclass(frozen=True)
class BlobPersistResult:
    """Passive, immutable persistence outcome. Carries no path/bytes/clock/identity/authority. Authorizes
    nothing — ``PERSISTED_NEW``/``VERIFIED_EXISTING_NOOP`` are durability facts, not S1/approval grants."""

    status: BlobPersistStatus
    reason: BlobPersistReason
    canonical_payload_digest: str
    immutable_snapshot_ref: str
    byte_length: int
    created_now: bool
    durability_verified: bool


@runtime_checkable
class BlobPersistAdapter(Protocol):
    """Boundary the future filesystem adapter implements. Defined here as a type contract only; the
    Protocol itself performs no work."""

    def persist_snapshot_blob(self, snapshot: SnapshotReference) -> BlobPersistResult:
        ...
