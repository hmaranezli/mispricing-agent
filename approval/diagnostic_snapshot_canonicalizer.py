"""approval/diagnostic_snapshot_canonicalizer.py — pure Phase 2B immutable snapshot canonicalizer.

The first implementation slice of the Persistence Bridge between ``tools/live_diagnostic_edge_probe.py``
and the S1 append boundary. It deterministically canonicalizes a COMPLETE ``diag-edge-probe-v1`` envelope
into stable bytes, a SHA-256 ``canonical_payload_digest``, and a LOGICAL ``immutable_snapshot_ref``.

Pure by construction: NO filesystem IO, NO DB access, NO network, NO clock, NO randomness, NO blob
persistence, NO append, NO authorization. It invents NO ``created_at`` / ``operator_command_id`` /
signer identity / approval status / authority flag — those belong to the separate, later append command.
Building a snapshot authorizes nothing.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

_PAYLOAD_KIND = "diag-edge-probe-v1"
_REF_PREFIX = _PAYLOAD_KIND + ":sha256:"
# The complete, recognized top-level key set the driver emits for a diag-edge-probe-v1 envelope.
_REQUIRED_KEYS = frozenset((
    "capture",
    "capture_status",
    "driver_note",
    "economics",
    "fail_closed_reason",
    "layer",
    "markers",
    "provenance",
    "schema_version",
))


class SnapshotEnvelopeError(ValueError):
    """Raised when the offered object is not a complete, recognized diag-edge-probe-v1 envelope, or
    cannot be canonicalized deterministically (e.g. NaN/Infinity floats)."""


@dataclass(frozen=True)
class SnapshotReference:
    """Passive, immutable canonicalization result. Authorizes nothing; carries no identity/clock."""

    canonical_payload_digest: str
    immutable_snapshot_ref: str
    payload_kind: str
    byte_length: int
    canonical_bytes: bytes


def build_immutable_snapshot(raw_envelope) -> SnapshotReference:
    """Canonicalize a complete diag-edge-probe-v1 envelope into a frozen SnapshotReference. Pure.

    Fails closed (SnapshotEnvelopeError) on a non-dict, a missing/extra top-level key, a foreign
    schema_version, or any value that is not deterministically JSON-serializable (NaN/Infinity).
    """
    if not isinstance(raw_envelope, dict):
        raise SnapshotEnvelopeError("envelope must be a dict")
    if frozenset(raw_envelope.keys()) != _REQUIRED_KEYS:
        raise SnapshotEnvelopeError("envelope top-level keys do not match diag-edge-probe-v1")
    if raw_envelope.get("schema_version") != _PAYLOAD_KIND:
        raise SnapshotEnvelopeError("unrecognized schema_version")

    try:
        canonical_text = json.dumps(
            raw_envelope, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
    except (ValueError, TypeError) as exc:
        raise SnapshotEnvelopeError(f"envelope not deterministically serializable: {exc}") from exc

    canonical_bytes = canonical_text.encode("utf-8")
    digest = hashlib.sha256(canonical_bytes).hexdigest()
    return SnapshotReference(
        canonical_payload_digest=digest,
        immutable_snapshot_ref=_REF_PREFIX + digest,
        payload_kind=_PAYLOAD_KIND,
        byte_length=len(canonical_bytes),
        canonical_bytes=canonical_bytes,
    )
