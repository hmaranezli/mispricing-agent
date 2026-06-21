"""phase6_2_shadow_intent/s1_evidence_projection.py — Phase 6.2 Slice C — S1 Evidence Projection.

A pure, stdlib-only **dependency leaf** that projects a single caller-supplied S1 replay row into a frozen,
slotted, methodless immutable evidence value. Built under the ratified Phase 6.2 chain: the reconstruction
runtime planning/slice charter (`457d279`), the evidence-intersection classification predicate charter
(`474cc6f`) and its precedence/decimal/evidence-consistency correction (`d7204d6`), and the
negative-evidence fixture-boundary charters (`b4368fd`, `045caea`).

Runtime boundary (binding):
  - it accepts **only** a caller-supplied row — it performs **no** SQLite query/connection, filesystem,
    network, cache, global-state, or adapter access, and imports nothing from `phase6_1`, the S1 storage
    adapter, `logical_model`, `artifact_verifier`, or the test tree (stdlib only);
  - it requires a **real** ``sqlite3.Row`` carrying exactly the six projected columns
    (``observation_kind, family_descriptor, artifact_locator, physical_record_position,
    provenance_timestamp, canonical_text_payload``);
  - it reads **only** the ratified whitelist — the row envelope columns plus, for a SCORE, the canonical
    payload paths ``observation_kind``, ``provenance_timestamp``, and ``family_payload.{passive_score_
    magnitude, score_unit_context, score_inputs_summary, score_family_descriptor}`` — never any unlisted
    member, and never by generic dict/JSON scraping;
  - it validates the Phase-5 S1 decimal lexis (``^-?\\d+(\\.\\d+)?$``, NOT the stricter Gate-B grammar),
    the canonical non-negative-integer ``provenance_timestamp`` (no signed-64 ceiling, no ``int()`` on
    arbitrarily long text), and exact row/payload consistency for kind / family descriptor / timestamp;
  - it surfaces exactly one deterministic domain failure — ``S1EvidenceProjectionError`` carrying a closed
    ``reason`` code — and never leaks a JSON / Decimal / type / key / native-parser exception; it never
    catches ``BaseException``/``MemoryError``;
  - it performs **no** lifecycle / crossing / expiry / relevance / actionability decision, and does not
    inspect HALT internals: a non-SCORE row exposes only its whitelisted envelope projection.

This slice owns no replay loop, persistence, query surface, analytics, or emission. Capacity stays deferred
at 0 emit sites; production / live / paper / canary / execution / routing / actionability remain forbidden.
"""
import decimal
import json
import re
import sqlite3
from dataclasses import dataclass


S1_EVIDENCE_PROJECTION_COMPONENT_NAME = "phase6_2_shadow_intent_s1_evidence_projection"

# The exact six projected replay columns (charter §3 / S1 durable-sink replay SELECT).
_EXPECTED_COLUMNS = frozenset((
    "observation_kind", "family_descriptor", "artifact_locator",
    "physical_record_position", "provenance_timestamp", "canonical_text_payload",
))

_SCORE_OBSERVATION_KIND = "SCORE"
_SCORE_FAMILY_DESCRIPTOR = "passive_net_edge_diagnostic"

# Phase-5 S1 magnitude lexis, replicated verbatim (`phase5/net_edge_calculator_boundary.py`); applied via
# fullmatch. NOT the stricter Gate-B artifact grammar.
_PHASE5_DECIMAL = re.compile(r"-?\d+(\.\d+)?")

# Canonical non-negative integer text: "0" or a non-zero-leading run. Lexical only — no int() conversion.
_CANONICAL_NONNEG_INT = re.compile(r"\A(?:0|[1-9][0-9]*)\Z")


# --- closed deterministic failure-reason vocabulary -----------------------------------------------
# The seven evidence-category reasons share the exact strings of the ratified negative-evidence cases.
ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT = "ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT"
ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT = "ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT"
ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT = "ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT"
MALFORMED_CANONICAL_JSON = "MALFORMED_CANONICAL_JSON"
MALFORMED_SCORE_INPUTS_SUMMARY = "MALFORMED_SCORE_INPUTS_SUMMARY"
INVALID_S1_DECIMAL_LEXIS = "INVALID_S1_DECIMAL_LEXIS"
INVALID_PROVENANCE_TIMESTAMP = "INVALID_PROVENANCE_TIMESTAMP"
# structural preconditions (row container shape / payload structure), distinct from evidence values.
PROJECTION_ROW_NOT_SQLITE_ROW = "PROJECTION_ROW_NOT_SQLITE_ROW"
PROJECTION_ROW_COLUMN_SET = "PROJECTION_ROW_COLUMN_SET"
PROJECTION_ROW_ENVELOPE_TYPE = "PROJECTION_ROW_ENVELOPE_TYPE"
PROJECTION_PAYLOAD_STRUCTURE = "PROJECTION_PAYLOAD_STRUCTURE"


class S1EvidenceProjectionError(ValueError):
    """The single deterministic Slice-C domain failure surface.

    Carries a closed ``reason`` code so a harness can assert the EXACT ratified category (single-fault
    isolation). No JSON / Decimal / type / key / native-parser exception is ever leaked through this
    boundary; ``BaseException`` and ``MemoryError`` are never caught.
    """

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


# --- frozen, slotted, methodless immutable projection carriers ------------------------------------

@dataclass(frozen=True, slots=True)
class ScoreEvidenceProjection:
    """Whitelist-only projection of a qualifying SCORE replay row. Pure data — no methods."""

    silver_artifact_locator: str
    silver_physical_record_position: str
    observation_kind: str
    family_descriptor: str
    provenance_timestamp: str
    passive_score_magnitude_text: str
    passive_score_magnitude: decimal.Decimal
    score_unit_context: str
    score_inputs_summary: tuple


@dataclass(frozen=True, slots=True)
class NonScoreEnvelopeProjection:
    """Whitelisted envelope projection of a non-SCORE replay row — no payload internals. Pure data."""

    silver_artifact_locator: str
    silver_physical_record_position: str
    observation_kind: str
    family_descriptor: str
    provenance_timestamp: object


# --- strict JSON helpers (no leaked native parser exceptions) -------------------------------------

@dataclass(frozen=True, slots=True)
class _RawJsonInt:
    lexical: str


@dataclass(frozen=True, slots=True)
class _RawJsonFloat:
    lexical: str


class _DuplicateMemberError(ValueError):
    """Internal: a JSON object carried a duplicate member name (normalized to MALFORMED_CANONICAL_JSON)."""


def _no_duplicate_members(pairs):
    seen = set()
    for key, _value in pairs:                # preserve all pairs until duplicate detection completes
        if key in seen:
            raise _DuplicateMemberError(f"duplicate JSON member: {key!r}")
        seen.add(key)
    return dict(pairs)


def _reject_constant(_token):
    raise _DuplicateMemberError("non-finite JSON constant is not canonical evidence")


def _parse_canonical_payload(text):
    """Strictly parse ``canonical_text_payload`` into a dict, normalizing every parser failure to the
    deterministic MALFORMED_CANONICAL_JSON domain reason. Numbers are captured by their verbatim lexis
    (no ``int()``/``float()`` conversion) so arbitrarily long timestamps never trip the interpreter."""
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_no_duplicate_members,
            parse_int=_RawJsonInt,
            parse_float=_RawJsonFloat,
            parse_constant=_reject_constant,
        )
    except (ValueError, UnicodeError, RecursionError):
        raise S1EvidenceProjectionError(
            MALFORMED_CANONICAL_JSON, "canonical_text_payload is not strict canonical JSON")
    if type(parsed) is not dict:
        raise S1EvidenceProjectionError(
            MALFORMED_CANONICAL_JSON, "canonical_text_payload root is not a JSON object")
    return parsed


# --- row-shape validation -------------------------------------------------------------------------

def _require_row(replay_row):
    if type(replay_row) is not sqlite3.Row:
        raise S1EvidenceProjectionError(
            PROJECTION_ROW_NOT_SQLITE_ROW, "replay_row must be a real sqlite3.Row")
    keys = replay_row.keys()
    if len(keys) != len(_EXPECTED_COLUMNS) or set(keys) != _EXPECTED_COLUMNS:
        raise S1EvidenceProjectionError(
            PROJECTION_ROW_COLUMN_SET, "replay_row must carry exactly the six projected columns")


def _require_str_column(value, column):
    if type(value) is not str:
        raise S1EvidenceProjectionError(
            PROJECTION_ROW_ENVELOPE_TYPE, f"row column {column} must be text")
    return value


# --- whitelist payload readers (named-path only; never generic scraping) --------------------------

def _payload_member(payload, name, missing_reason, missing_message):
    if name not in payload:
        raise S1EvidenceProjectionError(missing_reason, missing_message)
    return payload[name]


def _require_payload_str(value, reason, message):
    if type(value) is not str:
        raise S1EvidenceProjectionError(reason, message)
    return value


def _validate_timestamp(row_timestamp_text, payload_timestamp):
    """Validate the canonical non-negative-integer ``provenance_timestamp`` on both sides and require exact
    lexical equality. Consistent-but-invalid values are INVALID_PROVENANCE_TIMESTAMP (Case 7); two valid
    but unequal values are ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT (Case 3)."""
    payload_canonical = (
        type(payload_timestamp) is _RawJsonInt
        and _CANONICAL_NONNEG_INT.match(payload_timestamp.lexical) is not None
    )
    if not payload_canonical:
        raise S1EvidenceProjectionError(
            INVALID_PROVENANCE_TIMESTAMP,
            "payload provenance_timestamp is not a canonical non-negative integer")
    if _CANONICAL_NONNEG_INT.match(row_timestamp_text) is None:
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT,
            "row provenance_timestamp is not the payload's canonical decimal text")
    if row_timestamp_text != payload_timestamp.lexical:
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT,
            "row and payload provenance_timestamp disagree")
    return row_timestamp_text


def _validate_score_inputs_summary(value):
    if type(value) is not list or len(value) != 2 or not all(type(v) is str for v in value):
        raise S1EvidenceProjectionError(
            MALFORMED_SCORE_INPUTS_SUMMARY,
            "score_inputs_summary must be exactly two ordered text scalars")
    return (value[0], value[1])


def _validate_magnitude(value):
    if type(value) is not str or _PHASE5_DECIMAL.fullmatch(value) is None:
        raise S1EvidenceProjectionError(
            INVALID_S1_DECIMAL_LEXIS, "passive_score_magnitude violates the Phase-5 S1 decimal lexis")
    try:
        magnitude = decimal.Decimal(value)
    except decimal.InvalidOperation:
        raise S1EvidenceProjectionError(
            INVALID_S1_DECIMAL_LEXIS, "passive_score_magnitude is not an exact decimal")
    return value, magnitude


def _project_score(replay_row):
    locator = _require_str_column(replay_row["artifact_locator"], "artifact_locator")
    position = _require_str_column(replay_row["physical_record_position"], "physical_record_position")
    row_family = _require_str_column(replay_row["family_descriptor"], "family_descriptor")
    row_timestamp = _require_str_column(replay_row["provenance_timestamp"], "provenance_timestamp")
    payload = _parse_canonical_payload(
        _require_str_column(replay_row["canonical_text_payload"], "canonical_text_payload"))

    # (1) observation_kind: row says SCORE; require payload agreement.
    payload_kind = _payload_member(
        payload, "observation_kind",
        ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT, "payload observation_kind absent")
    if payload_kind != _SCORE_OBSERVATION_KIND:
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT,
            "row and payload observation_kind disagree")

    # (2) family descriptor: row + payload both exactly the literal, and equal.
    family_payload = _payload_member(
        payload, "family_payload",
        PROJECTION_PAYLOAD_STRUCTURE, "payload family_payload absent")
    if type(family_payload) is not dict:
        raise S1EvidenceProjectionError(
            PROJECTION_PAYLOAD_STRUCTURE, "payload family_payload is not an object")
    payload_family = _payload_member(
        family_payload, "score_family_descriptor",
        ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT, "payload score_family_descriptor absent")
    if (row_family != _SCORE_FAMILY_DESCRIPTOR
            or payload_family != _SCORE_FAMILY_DESCRIPTOR):
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT,
            "row and payload family descriptor must both be the ratified literal and agree")

    # (3) timestamp: canonical non-negative integer, row text == payload lexis.
    payload_timestamp = _payload_member(
        payload, "provenance_timestamp",
        INVALID_PROVENANCE_TIMESTAMP, "payload provenance_timestamp absent")
    provenance_timestamp = _validate_timestamp(row_timestamp, payload_timestamp)

    # (4) score_inputs_summary: exactly two ordered text scalars.
    inputs_summary = _validate_score_inputs_summary(
        _payload_member(
            family_payload, "score_inputs_summary",
            MALFORMED_SCORE_INPUTS_SUMMARY, "score_inputs_summary absent"))

    # (5) magnitude: Phase-5 lexis + exact Decimal.
    magnitude_text, magnitude = _validate_magnitude(
        _payload_member(
            family_payload, "passive_score_magnitude",
            INVALID_S1_DECIMAL_LEXIS, "passive_score_magnitude absent"))

    # (6) unit context: opaque text.
    unit_context = _require_payload_str(
        _payload_member(
            family_payload, "score_unit_context",
            PROJECTION_PAYLOAD_STRUCTURE, "score_unit_context absent"),
        PROJECTION_PAYLOAD_STRUCTURE, "score_unit_context must be text")

    return ScoreEvidenceProjection(
        silver_artifact_locator=locator,
        silver_physical_record_position=position,
        observation_kind=_SCORE_OBSERVATION_KIND,
        family_descriptor=_SCORE_FAMILY_DESCRIPTOR,
        provenance_timestamp=provenance_timestamp,
        passive_score_magnitude_text=magnitude_text,
        passive_score_magnitude=magnitude,
        score_unit_context=unit_context,
        score_inputs_summary=inputs_summary,
    )


def _project_non_score(replay_row, observation_kind):
    # Envelope-only projection: the whitelisted row columns, with HALT internals never inspected.
    locator = _require_str_column(replay_row["artifact_locator"], "artifact_locator")
    position = _require_str_column(replay_row["physical_record_position"], "physical_record_position")
    family = _require_str_column(replay_row["family_descriptor"], "family_descriptor")
    raw_timestamp = replay_row["provenance_timestamp"]
    if raw_timestamp is not None and type(raw_timestamp) is not str:
        raise S1EvidenceProjectionError(
            PROJECTION_ROW_ENVELOPE_TYPE, "row provenance_timestamp must be text or NULL")
    return NonScoreEnvelopeProjection(
        silver_artifact_locator=locator,
        silver_physical_record_position=position,
        observation_kind=observation_kind,
        family_descriptor=family,
        provenance_timestamp=raw_timestamp,
    )


def project_s1_evidence(*, replay_row):
    """Project one caller-supplied S1 replay ``sqlite3.Row`` into an immutable whitelist-only evidence
    value. A SCORE row yields a :class:`ScoreEvidenceProjection` (validated payload consistency + Phase-5
    decimal lexis + canonical timestamp); any other observation kind yields a
    :class:`NonScoreEnvelopeProjection` (envelope only, no payload internals). Malformed evidence raises a
    deterministic :class:`S1EvidenceProjectionError` with a closed ``reason``."""
    _require_row(replay_row)
    observation_kind = _require_str_column(replay_row["observation_kind"], "observation_kind")
    if observation_kind == _SCORE_OBSERVATION_KIND:
        return _project_score(replay_row)
    return _project_non_score(replay_row, observation_kind)
