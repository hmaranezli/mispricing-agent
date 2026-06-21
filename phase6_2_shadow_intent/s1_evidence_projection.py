"""phase6_2_shadow_intent/s1_evidence_projection.py — Phase 6.2 Slice C — S1 Evidence Projection.

A pure, stdlib-only **dependency leaf** that projects a single caller-supplied S1 replay row into frozen,
slotted, methodless, **factory-only** immutable evidence values through **strictly independent, separately
invoked lazy operations**. Built under the ratified Phase 6.2 chain: planning/slice (`457d279`), predicate
(`474cc6f`) + precedence/decimal-consistency (`d7204d6`), negative-evidence fixture boundary (`b4368fd`,
`045caea`), the score-context empty/whitespace amendment (`04c88fc`), and the fixed-literal /
Slice-C-trust-ownership micro-correction (`c8204ec`).

Public strict-lazy operations — each accepts the caller-supplied real ``sqlite3.Row`` directly, defensively
revalidates its own inputs, and inspects **only** its own whitelisted field(s); there are **no hidden
prerequisite calls between operations** (no shared parse cache, no global state):

  - ``project_silver_pair``      — row type + exact six-column shape + ``artifact_locator`` /
                                   ``physical_record_position`` (exact str) only; reads no kind, family,
                                   timestamp, or payload — the global Silver-pair guard;
  - ``project_observation_kind`` — row container/column shape + row ``observation_kind`` (exact str) only;
  - ``project_score_family``     — strict JSON parse + duplicate-member rejection + row/payload
                                   ``observation_kind`` and family-descriptor consistency only;
  - ``project_score_context``    — strict JSON parse + ``family_payload.score_inputs_summary`` only
                                   (independent of kind/family/timestamp/unit/magnitude);
  - ``project_score_timestamp``  — row/payload ``provenance_timestamp`` validity + equality only;
  - ``project_score_unit``       — ``score_unit_context`` only;
  - ``project_score_magnitude``  — ``passive_score_magnitude`` only.

This enables the legal ordering owned by a later Slice D/E (Silver-pair global guard → duplicate/root
decision → relevance decision → observation kind / per-field classification only when required). **Slice C
performs no expiry, context-equality, crossing, lifecycle, terminal, relevance, or actionability decision.**

Boundary (binding): no SQLite query/connection, filesystem, network, cache, global-state, or adapter
access; imports nothing from ``phase6_1``, the S1 storage adapter, ``logical_model``, ``artifact_verifier``,
``classification_predicates``, or the test tree (stdlib only). Validates the Phase-5 S1 decimal lexis
(``^-?\\d+(\\.\\d+)?$``, NOT Gate-B), the canonical non-negative-integer ``provenance_timestamp`` (no
signed-64 ceiling, no ``int()`` on arbitrarily long text), exact row/payload consistency, and the
source-proven non-empty / non-whitespace context-shape invariant. One deterministic failure surface,
``S1EvidenceProjectionError`` with a closed ``reason`` code; never leaks a JSON / Decimal / type / key /
native-parser exception and never catches ``BaseException``/``MemoryError``. Every exported carrier is
factory-only — direct construction raises ``S1EvidenceProjectionError`` (never a raw ``TypeError``) — and
every private maker independently enforces the carrier's complete invariant (via shared validators) before
publication. Capacity stays deferred at 0 emit sites; production / live / paper / canary / execution /
routing / actionability remain forbidden.
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

# Phase-5 S1 magnitude lexis, replicated verbatim (`phase5/net_edge_calculator_boundary.py`); fullmatch.
_PHASE5_DECIMAL = re.compile(r"-?\d+(\.\d+)?")
# Canonical non-negative integer text: "0" or a non-zero-leading run. Lexical only — no int() conversion.
_CANONICAL_NONNEG_INT = re.compile(r"\A(?:0|[1-9][0-9]*)\Z")

_ABSENT = object()  # distinguishes an absent member from a JSON null.


# --- closed deterministic failure-reason vocabulary -----------------------------------------------
ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT = "ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT"
ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT = "ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT"
ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT = "ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT"
MALFORMED_CANONICAL_JSON = "MALFORMED_CANONICAL_JSON"
MALFORMED_SCORE_INPUTS_SUMMARY = "MALFORMED_SCORE_INPUTS_SUMMARY"
INVALID_S1_DECIMAL_LEXIS = "INVALID_S1_DECIMAL_LEXIS"
INVALID_PROVENANCE_TIMESTAMP = "INVALID_PROVENANCE_TIMESTAMP"
# structural / precondition reasons, distinct from the seven evidence-value categories.
PROJECTION_ROW_NOT_SQLITE_ROW = "PROJECTION_ROW_NOT_SQLITE_ROW"
PROJECTION_ROW_COLUMN_SET = "PROJECTION_ROW_COLUMN_SET"
PROJECTION_ROW_ENVELOPE_TYPE = "PROJECTION_ROW_ENVELOPE_TYPE"
PROJECTION_PAYLOAD_STRUCTURE = "PROJECTION_PAYLOAD_STRUCTURE"
PROJECTION_NON_SCORE_OBSERVATION = "PROJECTION_NON_SCORE_OBSERVATION"
PROJECTION_DIRECT_CONSTRUCTION = "PROJECTION_DIRECT_CONSTRUCTION"
PROJECTION_PUBLICATION_INVARIANT = "PROJECTION_PUBLICATION_INVARIANT"


class S1EvidenceProjectionError(ValueError):
    """The single deterministic Slice-C domain failure surface, carrying a closed ``reason`` code."""

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


def _forbid_direct_construction(self, *args, **kwargs):
    """Bound to every exported carrier's ``__init__`` so a direct constructor (no / positional / keyword
    args) raises the domain error instead of admitting an unvalidated instance — never a raw ``TypeError``."""
    raise S1EvidenceProjectionError(
        PROJECTION_DIRECT_CONSTRUCTION,
        f"{type(self).__name__} is factory-only; use the module projection operations")


# --- shared invariant validators (single source of truth; public + publication cannot drift) ------

def _is_str(value):
    return type(value) is str


def _is_canonical_timestamp(text):
    return _is_str(text) and _CANONICAL_NONNEG_INT.match(text) is not None


def _two_nonblank_text(sequence):
    return (len(sequence) == 2
            and all(type(v) is str for v in sequence)
            and all(v.strip() != "" for v in sequence))


def _is_phase5_text(text):
    return _is_str(text) and _PHASE5_DECIMAL.fullmatch(text) is not None


def _is_finite_decimal(value):
    return type(value) is decimal.Decimal and value.is_finite()


# --- frozen, slotted, kw-only, methodless, factory-only immutable projection carriers -------------

@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class SilverPairProjection:
    """The opaque Silver pair only (global guard). Pure data."""

    silver_artifact_locator: str
    silver_physical_record_position: str

    __init__ = _forbid_direct_construction


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ObservationKindProjection:
    """The row observation_kind only. Pure data."""

    observation_kind: str

    __init__ = _forbid_direct_construction


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ScoreFamilyProjection:
    """Validated row/payload kind + family descriptor. Pure data."""

    observation_kind: str
    family_descriptor: str

    __init__ = _forbid_direct_construction


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ScoreContextProjection:
    """The verbatim two-scalar ``score_inputs_summary``. Pure data."""

    score_inputs_summary: tuple

    __init__ = _forbid_direct_construction


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ScoreTimestampProjection:
    """The canonical non-negative-integer provenance text. Pure data."""

    provenance_timestamp: str

    __init__ = _forbid_direct_construction


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ScoreUnitProjection:
    """The opaque ``score_unit_context`` token. Pure data."""

    score_unit_context: str

    __init__ = _forbid_direct_construction


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ScoreMagnitudeProjection:
    """Verbatim S1 lexis + exact base-10 Decimal. Pure data."""

    passive_score_magnitude_text: str
    passive_score_magnitude: decimal.Decimal

    __init__ = _forbid_direct_construction


# --- single closed construction path + per-carrier publication makers -----------------------------

def _seal(cls, **field_values):
    """The one closed construction primitive: build a carrier via ``object.__new__`` + per-slot
    ``object.__setattr__`` (bypassing the raising ``__init__`` and the frozen guard). Callers MUST have
    enforced the carrier's complete invariant first; no other code path constructs a carrier."""
    instance = object.__new__(cls)
    for name in cls.__dataclass_fields__:
        object.__setattr__(instance, name, field_values[name])
    return instance


def _publication_error(field):
    return S1EvidenceProjectionError(
        PROJECTION_PUBLICATION_INVARIANT, f"refusing to publish carrier: invalid {field}")


def _make_silver_pair(*, silver_artifact_locator, silver_physical_record_position):
    if not _is_str(silver_artifact_locator):
        raise _publication_error("silver_artifact_locator")
    if not _is_str(silver_physical_record_position):
        raise _publication_error("silver_physical_record_position")
    return _seal(SilverPairProjection,
                 silver_artifact_locator=silver_artifact_locator,
                 silver_physical_record_position=silver_physical_record_position)


def _make_observation_kind(*, observation_kind):
    if not _is_str(observation_kind):
        raise _publication_error("observation_kind")
    return _seal(ObservationKindProjection, observation_kind=observation_kind)


def _make_score_family(*, observation_kind, family_descriptor):
    if observation_kind != _SCORE_OBSERVATION_KIND:
        raise _publication_error("observation_kind")
    if family_descriptor != _SCORE_FAMILY_DESCRIPTOR:
        raise _publication_error("family_descriptor")
    return _seal(ScoreFamilyProjection,
                 observation_kind=observation_kind, family_descriptor=family_descriptor)


def _make_score_context(*, score_inputs_summary):
    if type(score_inputs_summary) is not tuple or not _two_nonblank_text(score_inputs_summary):
        raise _publication_error("score_inputs_summary")
    return _seal(ScoreContextProjection, score_inputs_summary=score_inputs_summary)


def _make_score_timestamp(*, provenance_timestamp):
    if not _is_canonical_timestamp(provenance_timestamp):
        raise _publication_error("provenance_timestamp")
    return _seal(ScoreTimestampProjection, provenance_timestamp=provenance_timestamp)


def _make_score_unit(*, score_unit_context):
    if not _is_str(score_unit_context):
        raise _publication_error("score_unit_context")
    return _seal(ScoreUnitProjection, score_unit_context=score_unit_context)


def _make_score_magnitude(*, passive_score_magnitude_text, passive_score_magnitude):
    if not _is_phase5_text(passive_score_magnitude_text):
        raise _publication_error("passive_score_magnitude_text")
    if not _is_finite_decimal(passive_score_magnitude):
        raise _publication_error("passive_score_magnitude")
    try:
        reparsed = decimal.Decimal(passive_score_magnitude_text)
    except decimal.InvalidOperation:
        raise _publication_error("passive_score_magnitude_text")
    if reparsed != passive_score_magnitude:
        raise _publication_error("passive_score_magnitude")
    return _seal(ScoreMagnitudeProjection,
                 passive_score_magnitude_text=passive_score_magnitude_text,
                 passive_score_magnitude=passive_score_magnitude)


# --- strict JSON helpers (no leaked native parser exceptions) -------------------------------------

@dataclass(frozen=True, slots=True)
class _RawJsonInt:
    lexical: str


@dataclass(frozen=True, slots=True)
class _RawJsonFloat:
    lexical: str


class _MalformedJsonError(ValueError):
    """Internal: normalized to MALFORMED_CANONICAL_JSON (duplicate member / non-finite constant)."""


def _no_duplicate_members(pairs):
    seen = set()
    for key, _value in pairs:                # preserve all pairs until duplicate detection completes
        if key in seen:
            raise _MalformedJsonError(f"duplicate JSON member: {key!r}")
        seen.add(key)
    return dict(pairs)


def _reject_constant(_token):
    raise _MalformedJsonError("non-finite JSON constant is not canonical evidence")


# --- shared row / payload access primitives -------------------------------------------------------

def _require_row(replay_row):
    if type(replay_row) is not sqlite3.Row:
        raise S1EvidenceProjectionError(
            PROJECTION_ROW_NOT_SQLITE_ROW, "replay_row must be a real sqlite3.Row")
    keys = replay_row.keys()
    if len(keys) != len(_EXPECTED_COLUMNS) or set(keys) != _EXPECTED_COLUMNS:
        raise S1EvidenceProjectionError(
            PROJECTION_ROW_COLUMN_SET, "replay_row must carry exactly the six projected columns")


def _envelope_str(replay_row, column):
    value = replay_row[column]
    if type(value) is not str:
        raise S1EvidenceProjectionError(
            PROJECTION_ROW_ENVELOPE_TYPE, f"row column {column} must be text")
    return value


def _parse_payload(replay_row):
    """Strictly parse ``canonical_text_payload`` into a dict; every parser failure normalizes to the
    deterministic MALFORMED_CANONICAL_JSON reason. Numbers are captured by verbatim lexis (no
    ``int()``/``float()``), so arbitrarily long timestamps never trip the interpreter."""
    text = _envelope_str(replay_row, "canonical_text_payload")
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


def _member(container, name):
    if name in container:
        return container[name]
    return _ABSENT


def _require_family_payload(payload):
    """Return the structural ``family_payload`` parent dict required to reach a family-scoped scalar.
    Reads no family DESCRIPTOR — only the container needed to address the requested scalar."""
    family_payload = _member(payload, "family_payload")
    if family_payload is _ABSENT or type(family_payload) is not dict:
        raise S1EvidenceProjectionError(
            PROJECTION_PAYLOAD_STRUCTURE, "payload family_payload absent or not an object")
    return family_payload


# --- public strict-lazy operations (each inspects ONLY its own whitelisted field[s]) --------------

def project_silver_pair(*, replay_row):
    """Project the opaque Silver pair only — the global guard. Validates the real ``sqlite3.Row`` type,
    the exact six-column shape, and ``artifact_locator`` / ``physical_record_position`` as exact text. Reads
    no observation_kind, family_descriptor, provenance_timestamp, or payload field."""
    _require_row(replay_row)
    return _make_silver_pair(
        silver_artifact_locator=_envelope_str(replay_row, "artifact_locator"),
        silver_physical_record_position=_envelope_str(replay_row, "physical_record_position"))


def project_observation_kind(*, replay_row):
    """Project the row ``observation_kind`` only. Validates the row container/column shape and the row
    observation_kind as exact text. Reads no family, timestamp, locator semantics, or payload field."""
    _require_row(replay_row)
    return _make_observation_kind(observation_kind=_envelope_str(replay_row, "observation_kind"))


def project_score_family(*, replay_row):
    """Project SCORE-family consistency only: strict canonical-JSON parse (duplicate-member rejection) and
    row/payload ``observation_kind`` + family-descriptor agreement. Inspects neither context, timestamp,
    unit, nor magnitude."""
    _require_row(replay_row)
    row_kind = _envelope_str(replay_row, "observation_kind")
    row_family = _envelope_str(replay_row, "family_descriptor")
    payload = _parse_payload(replay_row)

    payload_kind = _member(payload, "observation_kind")
    if payload_kind is _ABSENT or type(payload_kind) is not str:
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT, "payload observation_kind absent or non-text")
    if row_kind != payload_kind:
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT, "row and payload observation_kind disagree")
    if row_kind != _SCORE_OBSERVATION_KIND:
        raise S1EvidenceProjectionError(
            PROJECTION_NON_SCORE_OBSERVATION, "observation_kind is not SCORE")

    family_payload = _require_family_payload(payload)
    payload_family = _member(family_payload, "score_family_descriptor")
    if payload_family is _ABSENT or type(payload_family) is not str:
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT,
            "payload score_family_descriptor absent or non-text")
    if row_family != _SCORE_FAMILY_DESCRIPTOR or payload_family != _SCORE_FAMILY_DESCRIPTOR:
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT,
            "row and payload family descriptor must both be the ratified literal and agree")
    return _make_score_family(
        observation_kind=_SCORE_OBSERVATION_KIND, family_descriptor=_SCORE_FAMILY_DESCRIPTOR)


def project_score_context(*, replay_row):
    """Project the SCORE context only, INDEPENDENTLY of kind/family/timestamp/unit/magnitude: strict JSON
    parse, then exactly-two non-empty, non-whitespace ``family_payload.score_inputs_summary`` scalars,
    returned verbatim. Reads neither row/payload observation_kind, row/payload family descriptor,
    provenance_timestamp, score_unit_context, nor passive_score_magnitude."""
    _require_row(replay_row)
    payload = _parse_payload(replay_row)
    family_payload = _require_family_payload(payload)
    summary = _member(family_payload, "score_inputs_summary")
    if type(summary) is not list or not _two_nonblank_text(summary):
        raise S1EvidenceProjectionError(
            MALFORMED_SCORE_INPUTS_SUMMARY,
            "score_inputs_summary must be exactly two ordered, non-empty, non-whitespace text scalars")
    return _make_score_context(score_inputs_summary=(summary[0], summary[1]))


def project_score_timestamp(*, replay_row):
    """Project the SCORE timestamp only: the row/payload ``provenance_timestamp`` (canonical non-negative
    integer, exact row/payload agreement). Inspects neither kind, family, context, unit, nor magnitude."""
    _require_row(replay_row)
    row_timestamp = _envelope_str(replay_row, "provenance_timestamp")
    payload = _parse_payload(replay_row)
    payload_timestamp = _member(payload, "provenance_timestamp")
    if payload_timestamp is _ABSENT:
        raise S1EvidenceProjectionError(
            INVALID_PROVENANCE_TIMESTAMP, "payload provenance_timestamp absent")
    if not (type(payload_timestamp) is _RawJsonInt and _is_canonical_timestamp(payload_timestamp.lexical)):
        raise S1EvidenceProjectionError(
            INVALID_PROVENANCE_TIMESTAMP,
            "payload provenance_timestamp is not a canonical non-negative integer")
    if not _is_canonical_timestamp(row_timestamp):
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT,
            "row provenance_timestamp is not the payload's canonical decimal text")
    if row_timestamp != payload_timestamp.lexical:
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT, "row and payload provenance_timestamp disagree")
    return _make_score_timestamp(provenance_timestamp=row_timestamp)


def project_score_unit(*, replay_row):
    """Project the SCORE unit only: the opaque ``score_unit_context`` text. Inspects neither kind, family,
    context, timestamp, nor magnitude."""
    _require_row(replay_row)
    payload = _parse_payload(replay_row)
    family_payload = _require_family_payload(payload)
    unit = _member(family_payload, "score_unit_context")
    if unit is _ABSENT or type(unit) is not str:
        raise S1EvidenceProjectionError(
            PROJECTION_PAYLOAD_STRUCTURE, "score_unit_context absent or non-text")
    return _make_score_unit(score_unit_context=unit)


def project_score_magnitude(*, replay_row):
    """Project the SCORE magnitude only: the Phase-5-lexis ``passive_score_magnitude`` (verbatim text +
    exact base-10 Decimal). Inspects neither kind, family, context, timestamp, nor unit."""
    _require_row(replay_row)
    payload = _parse_payload(replay_row)
    family_payload = _require_family_payload(payload)
    value = _member(family_payload, "passive_score_magnitude")
    if value is _ABSENT or not _is_phase5_text(value):
        raise S1EvidenceProjectionError(
            INVALID_S1_DECIMAL_LEXIS, "passive_score_magnitude violates the Phase-5 S1 decimal lexis")
    try:
        magnitude = decimal.Decimal(value)
    except decimal.InvalidOperation:
        raise S1EvidenceProjectionError(
            INVALID_S1_DECIMAL_LEXIS, "passive_score_magnitude is not an exact decimal")
    return _make_score_magnitude(
        passive_score_magnitude_text=value, passive_score_magnitude=magnitude)
