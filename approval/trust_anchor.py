"""approval/trust_anchor.py — Day-Zero trust-anchor artifact model (passive validation only).

The pinned public-key fingerprint is the root of trust for the VPS verifier. This module validates a
Day-Zero trust-anchor artifact against a deterministic closed shape and fails closed unless the
fingerprint is present, well-formed, and the artifact is final/immutable, ceremony-witnessed, and
sourced from an offline air-gapped ceremony (never network / model / config / server-self-generated).
Rotation and revocation state must be unambiguous.

This module creates no artifact, reads no file, performs no network/model/config lookup, and holds no
private-key material. The output is PASSIVE: a frozen ``AnchorResult(valid, reason)``. A
``valid=True`` result authorizes NOTHING.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

REQUIRED_ANCHOR_FIELDS = frozenset(
    {
        "public_key_fingerprint",
        "artifact_state",
        "ceremony_evidence_marker",
        "trust_source",
        "rotation_state",
        "revocation_state",
    }
)

_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")

_FINAL_STATE = "FINAL"
_ALLOWED_TRUST_SOURCE = "OFFLINE_AIR_GAPPED_CEREMONY"
_VALID_ROTATION = frozenset({"ACTIVE_SINGLE"})
_VALID_REVOCATION = frozenset({"NONE"})


@dataclass(frozen=True)
class AnchorResult:
    """Passive, immutable trust-anchor validation outcome."""

    valid: bool
    reason: str


def validate_trust_anchor_artifact(artifact) -> AnchorResult:
    """Validate a Day-Zero trust-anchor artifact. Fails closed on any missing/ambiguous evidence."""
    if not isinstance(artifact, dict):
        return AnchorResult(False, "malformed_artifact")

    if set(artifact.keys()) - REQUIRED_ANCHOR_FIELDS:
        return AnchorResult(False, "unauthorized_extra_field")

    fingerprint = artifact.get("public_key_fingerprint", "")
    if not fingerprint:
        return AnchorResult(False, "missing_public_key_fingerprint")
    if not isinstance(fingerprint, str) or not _FINGERPRINT_RE.match(fingerprint):
        return AnchorResult(False, "malformed_fingerprint")

    if artifact.get("artifact_state") != _FINAL_STATE:
        return AnchorResult(False, "mutable_or_non_final_artifact")

    if not artifact.get("ceremony_evidence_marker"):
        return AnchorResult(False, "missing_ceremony_evidence")

    if artifact.get("trust_source") != _ALLOWED_TRUST_SOURCE:
        return AnchorResult(False, "forbidden_trust_source")

    if artifact.get("rotation_state") not in _VALID_ROTATION:
        return AnchorResult(False, "ambiguous_rotation_state")

    if artifact.get("revocation_state") not in _VALID_REVOCATION:
        return AnchorResult(False, "ambiguous_revocation_state")

    return AnchorResult(True, "")
