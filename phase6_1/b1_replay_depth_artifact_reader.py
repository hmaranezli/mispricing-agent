"""phase6_1/b1_replay_depth_artifact_reader.py — Phase 6.1 replay depth-artifact reader.

The single allowlisted IO module in the phase6_1 package. It reads ONE caller-supplied local replay
depth artifact (read-only) and builds exactly one ``PublicDepthSourceRecord`` through the B1 depth
factory. It performs no network access, no environment access, no path discovery or globbing, and no
writes. It decides nothing: every field is carried verbatim into the B1 factory, which enforces the
exact-type / fail-fast field contract. ``observed_size`` is never parsed or converted — it is passed
through as the artifact's own string.

This module's narrow IO surface (read-only ``open``; imports limited to ``pathlib``/``json`` plus the
required internal B1 factory import) is permitted solely by the module-scoped exception in
``docs/handoff/phase6_1_replay_depth_reader_io_lock_exception_amendment_charter.md`` and is bounded by
``docs/handoff/phase6_1_replay_depth_artifact_reader_charter.md``. No other phase6_1 module may use IO.
"""
import json
import pathlib

from phase6_1.b1_depth_source_contract import make_public_depth_source_record


REPLAY_DEPTH_READER_COMPONENT_NAME = "phase6_1_b1_replay_depth_artifact_reader"


class ReplayDepthArtifactError(Exception):
    """Raised when an artifact is not a flat mapping, is missing a required field, or carries an
    unknown field. Field-level type/value problems are raised by the B1 factory itself."""


# The closed 8-field artifact contract: exactly these keys, no more and no fewer.
_REQUIRED_ARTIFACT_FIELDS = frozenset((
    "observed_size",
    "size_unit",
    "depth_source_field",
    "depth_source_artifact",
    "depth_source_contract",
    "depth_snapshot_identity",
    "depth_observed_at_epoch_ms",
    "depth_retrieval_epoch_ms",
))


def read_replay_depth_artifact(artifact_path):
    """Read ONE local replay depth artifact at the caller-supplied ``artifact_path`` and return a
    ``PublicDepthSourceRecord``. The path must be explicit — no discovery, globbing, environment
    lookup, or default path is performed. The artifact must be a flat mapping carrying exactly the 8
    contract keys; a missing key or an unknown key fails fast here, and every value is handed verbatim
    to ``make_public_depth_source_record`` (which fails fast on any malformed field). ``observed_size``
    is carried through as the artifact's own string and is never parsed or converted."""
    path = pathlib.Path(artifact_path)
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    if type(payload) is not dict:
        raise ReplayDepthArtifactError(
            "replay depth artifact must be a flat mapping of the 8 contract fields"
        )

    keys = frozenset(payload)
    missing = _REQUIRED_ARTIFACT_FIELDS - keys
    if missing:
        raise ReplayDepthArtifactError(
            "replay depth artifact missing required field(s): {}".format(sorted(missing))
        )
    unknown = keys - _REQUIRED_ARTIFACT_FIELDS
    if unknown:
        raise ReplayDepthArtifactError(
            "replay depth artifact carries unknown field(s): {}".format(sorted(unknown))
        )

    return make_public_depth_source_record(
        observed_size=payload["observed_size"],
        size_unit=payload["size_unit"],
        depth_source_field=payload["depth_source_field"],
        depth_source_artifact=payload["depth_source_artifact"],
        depth_source_contract=payload["depth_source_contract"],
        depth_snapshot_identity=payload["depth_snapshot_identity"],
        depth_observed_at_epoch_ms=payload["depth_observed_at_epoch_ms"],
        depth_retrieval_epoch_ms=payload["depth_retrieval_epoch_ms"],
    )
