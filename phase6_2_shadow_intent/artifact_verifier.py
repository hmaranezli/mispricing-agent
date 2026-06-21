"""phase6_2_shadow_intent/artifact_verifier.py — Phase 6.2 Slice B artifact verification.

Verifies a sealed scenario-definition artifact exactly per the ratified Gate B charter
(``docs/handoff/phase6_2_shadow_intent_definition_artifact_canonical_encoding_digest_charter.md``,
``474cc6f``): one complete UTF-8 canonical JSON document, a detached SHA-256 digest, the fixed physical
variant discriminators, the canonical decimal/duration string grammars, strictly-ascending Silver-pair
ordering, and byte-for-byte canonical identity. On success it returns the immutable Gate-A logical
projection built **exclusively** through the Slice-A factories (``logical_model``).

Scope (Slice B of ``…reconstruction_runtime_tdd_planning_slice_charter.md``): canonical bytes + detached
digest + immutable projection **only**. Explicit locator only — no latest/glob/env/default/sidecar, no
file/path/URI handling, no directory scan, no network, no S1 access, no second artifact, and **no public
writer / artifact-authoring API** (the canonical encoder is private and used solely for the byte-identity
check). This module imports only ``logical_model`` and the standard library.
"""
import decimal
import hashlib
import json
import re

from dataclasses import dataclass

from phase6_2_shadow_intent import logical_model as lm


ARTIFACT_VERIFIER_COMPONENT_NAME = "phase6_2_shadow_intent_artifact_verifier"

# The exact ASCII field-shape literal pinned for this canonical profile (474cc6f §5).
_FIELD_SHAPE_LITERAL = "PHASE6_2_SHADOW_INTENT_DEFINITION_ARTIFACT_FIELD_SHAPE_V1"

_SHA256_HEX = re.compile(r"\A[0-9a-f]{64}\Z")

# Gate B grammars (474cc6f §11/§12): canonical exact-decimal and non-negative-integer duration strings.
_CANONICAL_DECIMAL = re.compile(r"\A-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?\Z")
_CANONICAL_DURATION = re.compile(r"\A(0|[1-9][0-9]*)\Z")

_DIRECTIONAL_KIND = "DIRECTIONAL_SHADOW_INTENT_DEFINITION"
_INERT_KIND = "INERT_SHADOW_INTENT_DEFINITION"

_ROOT_MEMBERS = frozenset({
    "artifact_field_shape_version_reference", "artifact_version_reference", "declarer_opaque_reference",
    "predecessor_artifact_version_reference", "definitions_by_silver_pair",
})
_DIRECTIONAL_MEMBERS = frozenset({
    "definition_kind", "silver_artifact_locator_text", "silver_physical_record_position_text",
    "exposure_orientation", "passive_boundary_magnitude", "boundary_unit_context",
    "hypothetical_window_duration_ms",
})
_INERT_MEMBERS = frozenset({
    "definition_kind", "silver_artifact_locator_text", "silver_physical_record_position_text",
    "exposure_orientation", "hypothetical_window_duration_ms",
})


class ArtifactVerificationError(ValueError):
    """Raised for any pre-replay verification failure (digest, encoding, structure, or byte identity)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SealedArtifactReference:
    """A frozen, slotted explicit artifact reference: an opaque locator + an expected detached digest.

    ``opaque_artifact_locator`` is opaque metadata — never parsed as a path/URI, normalized, opened, or
    used for discovery. ``expected_detached_sha256_digest`` is the caller-supplied expected digest.
    """

    opaque_artifact_locator: object
    expected_detached_sha256_digest: object


def make_sealed_artifact_reference(*, opaque_artifact_locator, expected_detached_sha256_digest):
    if type(opaque_artifact_locator) is not str:
        raise ArtifactVerificationError("opaque_artifact_locator must be a str")
    if type(expected_detached_sha256_digest) is not str:
        raise ArtifactVerificationError("expected_detached_sha256_digest must be a str")
    return SealedArtifactReference(
        opaque_artifact_locator=opaque_artifact_locator,
        expected_detached_sha256_digest=expected_detached_sha256_digest,
    )


def _no_duplicate_members(pairs):
    """``object_pairs_hook``: reject duplicate object members before any dict is constructed."""
    seen = set()
    built = {}
    for key, value in pairs:
        if key in seen:
            raise ArtifactVerificationError("duplicate object member: {!r}".format(key))
        seen.add(key)
        built[key] = value
    return built


def _reject_number(value):
    raise ArtifactVerificationError("JSON numbers are forbidden; values must be canonical strings")


def _require_str(name, value):
    if type(value) is not str:
        raise ArtifactVerificationError("{} must be a JSON string, not {}".format(name, type(value).__name__))
    return value


def _decimal_to_canonical(d):
    """Render a finite ``Decimal`` into the unique Gate B canonical decimal string (474cc6f §11)."""
    if d.is_zero():
        return "0"
    text = format(d, "f")  # fixed-point, no exponent
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    if "." in text:
        integer_part, fraction = text.split(".", 1)
        fraction = fraction.rstrip("0")
    else:
        integer_part, fraction = text, ""
    integer_part = integer_part.lstrip("0") or "0"
    rendered = integer_part if fraction == "" else integer_part + "." + fraction
    return ("-" + rendered) if negative else rendered


def _canonical_predecessor(predecessor):
    if type(predecessor) is lm.NoPredecessor:
        return {"kind": "NO_PREDECESSOR"}
    return {"kind": "PREDECESSOR_REFERENCE", "opaque_reference": predecessor.opaque_reference}


def _canonical_definition_entry(key, definition):
    entry = {
        "silver_artifact_locator_text": key.silver_artifact_locator_text,
        "silver_physical_record_position_text": key.silver_physical_record_position_text,
        "exposure_orientation": definition.exposure_orientation,
        "hypothetical_window_duration_ms": str(definition.hypothetical_window_duration_ms),
    }
    if type(definition) is lm.DirectionalShadowIntentDefinition:
        entry["definition_kind"] = _DIRECTIONAL_KIND
        entry["passive_boundary_magnitude"] = _decimal_to_canonical(definition.passive_boundary_magnitude)
        entry["boundary_unit_context"] = definition.boundary_unit_context
    else:
        entry["definition_kind"] = _INERT_KIND
    return entry


def _canonical_bytes(artifact):
    """Re-encode the logical artifact into the fixed-schema canonical UTF-8 bytes.

    Object members are emitted in the profile's deterministic (code-point) order via ``sort_keys`` with
    minimal separators and canonical JSON string escaping (``ensure_ascii=False``); the definitions array
    is pre-sorted by the unsigned UTF-8 byte tuple of the Silver pair. Lone surrogates fail to encode and
    are surfaced as a verification error.
    """
    entries = []
    for key, definition in artifact.definitions_by_silver_pair.items():
        sort_key = (
            key.silver_artifact_locator_text.encode("utf-8"),
            key.silver_physical_record_position_text.encode("utf-8"),
        )
        entries.append((sort_key, _canonical_definition_entry(key, definition)))
    entries.sort(key=lambda pair: pair[0])
    root = {
        "artifact_field_shape_version_reference": artifact.artifact_field_shape_version_reference,
        "artifact_version_reference": artifact.artifact_version_reference,
        "declarer_opaque_reference": artifact.declarer_opaque_reference,
        "predecessor_artifact_version_reference": _canonical_predecessor(
            artifact.predecessor_artifact_version_reference
        ),
        "definitions_by_silver_pair": [entry for _, entry in entries],
    }
    text = json.dumps(root, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError:
        raise ArtifactVerificationError("artifact contains an invalid Unicode scalar (e.g. a lone surrogate)")


def _build_predecessor(raw):
    if type(raw) is not dict:
        raise ArtifactVerificationError("predecessor_artifact_version_reference must be a JSON object")
    kind = raw.get("kind")
    if kind == "NO_PREDECESSOR":
        if set(raw) != {"kind"}:
            raise ArtifactVerificationError("NO_PREDECESSOR must have exactly one member")
        return lm.NoPredecessor()
    if kind == "PREDECESSOR_REFERENCE":
        if set(raw) != {"kind", "opaque_reference"}:
            raise ArtifactVerificationError("PREDECESSOR_REFERENCE must have exactly {kind, opaque_reference}")
        return lm.make_predecessor_reference(
            opaque_reference=_require_str("opaque_reference", raw["opaque_reference"])
        )
    raise ArtifactVerificationError("unknown predecessor kind: {!r}".format(kind))


def _build_definition(raw):
    if type(raw) is not dict:
        raise ArtifactVerificationError("definition entry must be a JSON object")
    kind = raw.get("definition_kind")
    locator = _require_str("silver_artifact_locator_text", raw.get("silver_artifact_locator_text"))
    position = _require_str("silver_physical_record_position_text", raw.get("silver_physical_record_position_text"))
    key = lm.make_opaque_silver_pair_key(
        silver_artifact_locator_text=locator, silver_physical_record_position_text=position
    )
    duration_text = _require_str("hypothetical_window_duration_ms", raw.get("hypothetical_window_duration_ms"))
    if _CANONICAL_DURATION.match(duration_text) is None:
        raise ArtifactVerificationError("invalid duration grammar: {!r}".format(duration_text))

    if kind == _DIRECTIONAL_KIND:
        if set(raw) != _DIRECTIONAL_MEMBERS:
            raise ArtifactVerificationError("directional entry has wrong member set")
        magnitude_text = _require_str("passive_boundary_magnitude", raw["passive_boundary_magnitude"])
        if _CANONICAL_DECIMAL.match(magnitude_text) is None or magnitude_text == "-0":
            raise ArtifactVerificationError("invalid decimal grammar: {!r}".format(magnitude_text))
        definition = lm.make_directional_shadow_intent_definition(
            exposure_orientation=_require_str("exposure_orientation", raw["exposure_orientation"]),
            passive_boundary_magnitude=decimal.Decimal(magnitude_text),
            boundary_unit_context=_require_str("boundary_unit_context", raw["boundary_unit_context"]),
            hypothetical_window_duration_ms=int(duration_text),
        )
    elif kind == _INERT_KIND:
        if set(raw) != _INERT_MEMBERS:
            raise ArtifactVerificationError("inert entry has wrong member set")
        definition = lm.make_inert_shadow_intent_definition(
            exposure_orientation=_require_str("exposure_orientation", raw["exposure_orientation"]),
            hypothetical_window_duration_ms=int(duration_text),
        )
    else:
        raise ArtifactVerificationError("unknown definition_kind: {!r}".format(kind))
    return key, position, locator, definition


def _parse_and_project(text):
    """Strict-parse + structurally validate the canonical text and build the Slice-A logical artifact."""
    try:
        root = json.loads(
            text,
            object_pairs_hook=_no_duplicate_members,
            parse_float=_reject_number,
            parse_int=_reject_number,
            parse_constant=_reject_number,
        )
    except ArtifactVerificationError:
        raise
    except (ValueError, UnicodeError) as exc:
        raise ArtifactVerificationError("malformed JSON: {}".format(exc))

    if type(root) is not dict:
        raise ArtifactVerificationError("artifact root must be a JSON object")
    if set(root) != _ROOT_MEMBERS:
        raise ArtifactVerificationError("artifact root must have exactly the five schema members")
    if _require_str("artifact_field_shape_version_reference", root["artifact_field_shape_version_reference"]) != _FIELD_SHAPE_LITERAL:
        raise ArtifactVerificationError("artifact_field_shape_version_reference must be the pinned literal")
    _require_str("artifact_version_reference", root["artifact_version_reference"])
    _require_str("declarer_opaque_reference", root["declarer_opaque_reference"])
    predecessor = _build_predecessor(root["predecessor_artifact_version_reference"])

    raw_entries = root["definitions_by_silver_pair"]
    if type(raw_entries) is not list:
        raise ArtifactVerificationError("definitions_by_silver_pair must be a JSON array")
    entries = []
    previous_sort_key = None
    for raw in raw_entries:
        key, position, locator, definition = _build_definition(raw)
        sort_key = (locator.encode("utf-8"), position.encode("utf-8"))
        if previous_sort_key is not None and not (previous_sort_key < sort_key):
            raise ArtifactVerificationError("definition entries must be strictly ascending by Silver pair")
        previous_sort_key = sort_key
        entries.append((key, definition))

    return lm.make_shadow_intent_definition_artifact(
        artifact_field_shape_version_reference=root["artifact_field_shape_version_reference"],
        artifact_version_reference=root["artifact_version_reference"],
        declarer_opaque_reference=root["declarer_opaque_reference"],
        predecessor_artifact_version_reference=predecessor,
        definition_entries=tuple(entries),
    )


def verify_artifact(*, reference, binary_stream):
    """Verify one sealed artifact and return its immutable Slice-A logical projection.

    Order (474cc6f §15/§17): (1) validate the reference/digest shape; (2) read the caller-owned stream
    **exactly once**; (3) compute SHA-256 and compare with the expected digest **before** parsing;
    (4) reject BOM / strict-UTF-8-decode; (5) strict JSON parse with duplicate-member detection and no
    JSON numbers; (6) validate variants/members/grammars/ordering and build the logical artifact through
    the Slice-A factories; (7) canonically re-encode and require byte-for-byte equality with the input;
    (8) return the projection. The stream is never sought, reread, substituted, retained, or closed; each
    call is an independent initialization (no global state).
    """
    if type(reference) is not SealedArtifactReference:
        raise ArtifactVerificationError("reference must be a SealedArtifactReference")
    expected_digest = reference.expected_detached_sha256_digest
    if type(expected_digest) is not str or _SHA256_HEX.match(expected_digest) is None:
        raise ArtifactVerificationError("expected_detached_sha256_digest must be 64 lowercase hex chars")

    raw_bytes = binary_stream.read()
    if type(raw_bytes) is not bytes:
        raise ArtifactVerificationError("binary_stream.read() must return exact bytes")

    actual_digest = hashlib.sha256(raw_bytes).hexdigest()
    if actual_digest != expected_digest:
        raise ArtifactVerificationError("detached SHA-256 digest mismatch")

    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise ArtifactVerificationError("byte-order mark (BOM) is forbidden")
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ArtifactVerificationError("artifact bytes are not valid UTF-8: {}".format(exc))

    try:
        artifact = _parse_and_project(text)
    except lm.LogicalModelError as exc:
        raise ArtifactVerificationError("logical validation failed: {}".format(exc))

    if _canonical_bytes(artifact) != raw_bytes:
        raise ArtifactVerificationError("artifact bytes are not canonical (byte-identity check failed)")
    return artifact
