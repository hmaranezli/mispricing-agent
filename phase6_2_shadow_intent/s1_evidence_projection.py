"""phase6_2_shadow_intent/s1_evidence_projection.py — Phase 6.2 Slice C — S1 Evidence Projection.

A pure, stdlib-only **dependency leaf** that projects a single caller-supplied S1 replay row into frozen,
slotted, methodless, **factory-only** immutable evidence values through **separately invoked, narrow lazy
operations**. Built under the ratified Phase 6.2 chain: the reconstruction runtime planning/slice charter
(`457d279`), the evidence-intersection classification predicate charter (`474cc6f`) + its
precedence/decimal/evidence-consistency correction (`d7204d6`), the negative-evidence fixture-boundary
charters (`b4368fd`, `045caea`), the score-context empty/whitespace amendment (`04c88fc`), and the
fixed-literal / Slice-C-trust-ownership micro-correction (`c8204ec`).

Public lazy operations (each accepts the caller-supplied real ``sqlite3.Row`` directly and defensively
revalidates its own inputs — no shared parse cache, no global state, no cross-call coupling):

  - ``project_row_envelope``        — row type + exact six-column shape + envelope values only (no payload
                                      parse);
  - ``project_score_family``        — strict JSON parse + duplicate-member rejection + row/payload kind and
                                      family-descriptor consistency only;
  - ``project_score_context``       — SCORE-family prerequisites + ``score_inputs_summary`` only;
  - ``project_score_timestamp``     — SCORE-family prerequisites + row/payload ``provenance_timestamp`` only;
  - ``project_score_unit``          — SCORE-family prerequisites + ``score_unit_context`` only;
  - ``project_score_magnitude``     — SCORE-family prerequisites + ``passive_score_magnitude`` only.

Each operation inspects **only** its own whitelisted field(s): a later/forbidden field is never read, so a
caller (a later Slice D/E) can enforce the ratified ordering (expiry-before-unit/magnitude, context
relevance, terminal relevance). **Slice C performs no expiry, context-equality, crossing, lifecycle,
terminal, or relevance decision** — it only makes the narrow operations available.

Boundary (binding): no SQLite query/connection, filesystem, network, cache, global-state, or adapter
access; imports nothing from ``phase6_1``, the S1 storage adapter, ``logical_model``, ``artifact_verifier``,
or the test tree (stdlib only). Reads only the ratified whitelist; validates the Phase-5 S1 decimal lexis
(``^-?\\d+(\\.\\d+)?$``, NOT Gate-B), the canonical non-negative-integer ``provenance_timestamp`` (no
signed-64 ceiling, no ``int()`` on arbitrarily long text), exact row/payload consistency, and the
source-proven non-empty / non-whitespace context-shape invariant. One deterministic failure surface,
``S1EvidenceProjectionError`` with a closed ``reason`` code; never leaks a JSON / Decimal / type / key /
native-parser exception and never catches ``BaseException``/``MemoryError``. Every exported carrier is
factory-only — direct construction raises ``S1EvidenceProjectionError`` (never a raw ``TypeError``).
Capacity stays deferred at 0 emit sites; production / live / paper / canary / execution / routing /
actionability remain forbidden.
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

_ABSENT = object()  # distinguishes an absent member from a JSON null.


# --- closed deterministic failure-reason vocabulary -----------------------------------------------
# The seven evidence-category reasons share the exact strings of the ratified negative-evidence cases.
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
    """The single deterministic Slice-C domain failure surface.

    Carries a closed ``reason`` code so a harness can assert the EXACT ratified category (single-fault
    isolation). No JSON / Decimal / type / key / native-parser exception is ever leaked through this
    boundary; ``BaseException`` and ``MemoryError`` are never caught.
    """

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


def _forbid_direct_construction(self, *args, **kwargs):
    """Bound to every exported carrier's ``__init__`` so a direct constructor (no args / positional /
    keyword) raises the domain error instead of admitting an unvalidated instance — never a raw
    ``TypeError``."""
    raise S1EvidenceProjectionError(
        PROJECTION_DIRECT_CONSTRUCTION,
        f"{type(self).__name__} is factory-only; use the module projection operations")


# --- frozen, slotted, kw-only, methodless, factory-only immutable projection carriers -------------

@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class RowEnvelopeProjection:
    """Envelope-only projection of any replay row (no payload inspection). Pure data."""

    observation_kind: str
    family_descriptor: str
    silver_artifact_locator: str
    silver_physical_record_position: str
    provenance_timestamp: object          # opaque str (SCORE) or None (HALT) — not validated here.

    __init__ = _forbid_direct_construction


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ScoreFamilyProjection:
    """SCORE-family consistency projection: validated row/payload kind + family descriptor. Pure data."""

    observation_kind: str
    family_descriptor: str

    __init__ = _forbid_direct_construction


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ScoreContextProjection:
    """SCORE context projection: the verbatim two-scalar ``score_inputs_summary``. Pure data."""

    score_inputs_summary: tuple

    __init__ = _forbid_direct_construction


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ScoreTimestampProjection:
    """SCORE timestamp projection: the canonical non-negative-integer provenance text. Pure data."""

    provenance_timestamp: str

    __init__ = _forbid_direct_construction


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ScoreUnitProjection:
    """SCORE unit projection: the opaque ``score_unit_context`` token. Pure data."""

    score_unit_context: str

    __init__ = _forbid_direct_construction


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ScoreMagnitudeProjection:
    """SCORE magnitude projection: verbatim S1 lexis + exact base-10 Decimal. Pure data."""

    passive_score_magnitude_text: str
    passive_score_magnitude: decimal.Decimal

    __init__ = _forbid_direct_construction


# --- single closed construction path --------------------------------------------------------------

def _seal(cls, **field_values):
    """The one closed construction primitive: build a carrier via ``object.__new__`` + per-slot
    ``object.__setattr__`` (bypassing the raising ``__init__`` and the frozen guard). Callers MUST have
    defensively validated every field first; no other code path constructs a carrier."""
    instance = object.__new__(cls)
    for name in cls.__dataclass_fields__:
        object.__setattr__(instance, name, field_values[name])
    return instance


def _publication_guard(condition, field):
    if not condition:
        raise S1EvidenceProjectionError(
            PROJECTION_PUBLICATION_INVARIANT, f"refusing to publish carrier: invalid {field}")


def _make_row_envelope(*, observation_kind, family_descriptor, silver_artifact_locator,
                       silver_physical_record_position, provenance_timestamp):
    _publication_guard(type(observation_kind) is str, "observation_kind")
    _publication_guard(type(family_descriptor) is str, "family_descriptor")
    _publication_guard(type(silver_artifact_locator) is str, "silver_artifact_locator")
    _publication_guard(type(silver_physical_record_position) is str, "silver_physical_record_position")
    _publication_guard(provenance_timestamp is None or type(provenance_timestamp) is str,
                       "provenance_timestamp")
    return _seal(
        RowEnvelopeProjection,
        observation_kind=observation_kind, family_descriptor=family_descriptor,
        silver_artifact_locator=silver_artifact_locator,
        silver_physical_record_position=silver_physical_record_position,
        provenance_timestamp=provenance_timestamp)


def _make_score_family(*, observation_kind, family_descriptor):
    _publication_guard(observation_kind == _SCORE_OBSERVATION_KIND, "observation_kind")
    _publication_guard(family_descriptor == _SCORE_FAMILY_DESCRIPTOR, "family_descriptor")
    return _seal(ScoreFamilyProjection,
                 observation_kind=observation_kind, family_descriptor=family_descriptor)


def _make_score_context(*, score_inputs_summary):
    _publication_guard(
        type(score_inputs_summary) is tuple and len(score_inputs_summary) == 2
        and all(type(v) is str for v in score_inputs_summary), "score_inputs_summary")
    return _seal(ScoreContextProjection, score_inputs_summary=score_inputs_summary)


def _make_score_timestamp(*, provenance_timestamp):
    _publication_guard(type(provenance_timestamp) is str, "provenance_timestamp")
    return _seal(ScoreTimestampProjection, provenance_timestamp=provenance_timestamp)


def _make_score_unit(*, score_unit_context):
    _publication_guard(type(score_unit_context) is str, "score_unit_context")
    return _seal(ScoreUnitProjection, score_unit_context=score_unit_context)


def _make_score_magnitude(*, passive_score_magnitude_text, passive_score_magnitude):
    _publication_guard(type(passive_score_magnitude_text) is str, "passive_score_magnitude_text")
    _publication_guard(type(passive_score_magnitude) is decimal.Decimal, "passive_score_magnitude")
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


# --- shared validation primitives -----------------------------------------------------------------

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


def _require_score_family(row_kind, row_family, payload):
    """Validate the SCORE-family prerequisite (row/payload kind both exactly SCORE and agreeing; row +
    payload family descriptor both exactly the ratified literal). Returns the validated ``family_payload``
    dict. Inspects neither context, timestamp, unit, nor magnitude."""
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

    family_payload = _member(payload, "family_payload")
    if family_payload is _ABSENT or type(family_payload) is not dict:
        raise S1EvidenceProjectionError(
            PROJECTION_PAYLOAD_STRUCTURE, "payload family_payload absent or not an object")
    payload_family = _member(family_payload, "score_family_descriptor")
    if payload_family is _ABSENT or type(payload_family) is not str:
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT,
            "payload score_family_descriptor absent or non-text")
    if row_family != _SCORE_FAMILY_DESCRIPTOR or payload_family != _SCORE_FAMILY_DESCRIPTOR:
        raise S1EvidenceProjectionError(
            ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT,
            "row and payload family descriptor must both be the ratified literal and agree")
    return family_payload


def _validate_context(family_payload):
    summary = _member(family_payload, "score_inputs_summary")
    if (summary is _ABSENT or type(summary) is not list or len(summary) != 2
            or not all(type(v) is str for v in summary)
            or any(v.strip() == "" for v in summary)):
        raise S1EvidenceProjectionError(
            MALFORMED_SCORE_INPUTS_SUMMARY,
            "score_inputs_summary must be exactly two ordered, non-empty, non-whitespace text scalars")
    return (summary[0], summary[1])         # preserved verbatim — no trim/normalize/repair/case-fold.


def _validate_timestamp(row_timestamp_text, payload_timestamp):
    """Validate the canonical non-negative-integer ``provenance_timestamp`` on both sides and require exact
    lexical equality. A consistent-but-invalid value is INVALID_PROVENANCE_TIMESTAMP (Case 7); two valid
    but unequal values are ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT (Case 3). No ``int()`` is used."""
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
            ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT, "row and payload provenance_timestamp disagree")
    return row_timestamp_text


def _validate_magnitude(value):
    if value is _ABSENT or type(value) is not str or _PHASE5_DECIMAL.fullmatch(value) is None:
        raise S1EvidenceProjectionError(
            INVALID_S1_DECIMAL_LEXIS, "passive_score_magnitude violates the Phase-5 S1 decimal lexis")
    try:
        magnitude = decimal.Decimal(value)
    except decimal.InvalidOperation:
        raise S1EvidenceProjectionError(
            INVALID_S1_DECIMAL_LEXIS, "passive_score_magnitude is not an exact decimal")
    return value, magnitude


# --- public lazy projection operations (each inspects ONLY its own whitelisted field[s]) ----------

def project_row_envelope(*, replay_row):
    """Project the row envelope only: validate the real ``sqlite3.Row`` type, the exact six-column shape,
    and the envelope value types. Does NOT parse ``canonical_text_payload`` — usable for any observation
    kind (SCORE or non-SCORE)."""
    _require_row(replay_row)
    return _make_row_envelope(
        observation_kind=_envelope_str(replay_row, "observation_kind"),
        family_descriptor=_envelope_str(replay_row, "family_descriptor"),
        silver_artifact_locator=_envelope_str(replay_row, "artifact_locator"),
        silver_physical_record_position=_envelope_str(replay_row, "physical_record_position"),
        provenance_timestamp=_nullable_provenance(replay_row))


def _nullable_provenance(replay_row):
    value = replay_row["provenance_timestamp"]
    if value is not None and type(value) is not str:
        raise S1EvidenceProjectionError(
            PROJECTION_ROW_ENVELOPE_TYPE, "row provenance_timestamp must be text or NULL")
    return value


def project_score_family(*, replay_row):
    """Project SCORE-family consistency only: strict canonical-JSON parse (duplicate-member rejection) and
    row/payload ``observation_kind`` + family-descriptor agreement. Inspects neither context, timestamp,
    unit, nor magnitude."""
    _require_row(replay_row)
    row_kind = _envelope_str(replay_row, "observation_kind")
    row_family = _envelope_str(replay_row, "family_descriptor")
    payload = _parse_payload(replay_row)
    _require_score_family(row_kind, row_family, payload)
    return _make_score_family(
        observation_kind=_SCORE_OBSERVATION_KIND, family_descriptor=_SCORE_FAMILY_DESCRIPTOR)


def project_score_context(*, replay_row):
    """Project the SCORE context only: SCORE-family prerequisites plus the exactly-two non-empty,
    non-whitespace ``score_inputs_summary`` scalars. Inspects neither timestamp, unit, nor magnitude."""
    _require_row(replay_row)
    row_kind = _envelope_str(replay_row, "observation_kind")
    row_family = _envelope_str(replay_row, "family_descriptor")
    payload = _parse_payload(replay_row)
    family_payload = _require_score_family(row_kind, row_family, payload)
    return _make_score_context(score_inputs_summary=_validate_context(family_payload))


def project_score_timestamp(*, replay_row):
    """Project the SCORE timestamp only: SCORE-family prerequisites plus the row/payload
    ``provenance_timestamp`` (canonical non-negative integer, exact row/payload agreement). Inspects
    neither context, unit, nor magnitude."""
    _require_row(replay_row)
    row_kind = _envelope_str(replay_row, "observation_kind")
    row_family = _envelope_str(replay_row, "family_descriptor")
    row_timestamp = _envelope_str(replay_row, "provenance_timestamp")
    payload = _parse_payload(replay_row)
    _require_score_family(row_kind, row_family, payload)
    payload_timestamp = _member(payload, "provenance_timestamp")
    if payload_timestamp is _ABSENT:
        raise S1EvidenceProjectionError(
            INVALID_PROVENANCE_TIMESTAMP, "payload provenance_timestamp absent")
    return _make_score_timestamp(
        provenance_timestamp=_validate_timestamp(row_timestamp, payload_timestamp))


def project_score_unit(*, replay_row):
    """Project the SCORE unit only: SCORE-family prerequisites plus the opaque ``score_unit_context`` text.
    Inspects neither context, timestamp, nor magnitude."""
    _require_row(replay_row)
    row_kind = _envelope_str(replay_row, "observation_kind")
    row_family = _envelope_str(replay_row, "family_descriptor")
    payload = _parse_payload(replay_row)
    family_payload = _require_score_family(row_kind, row_family, payload)
    unit = _member(family_payload, "score_unit_context")
    if unit is _ABSENT or type(unit) is not str:
        raise S1EvidenceProjectionError(
            PROJECTION_PAYLOAD_STRUCTURE, "score_unit_context absent or non-text")
    return _make_score_unit(score_unit_context=unit)


def project_score_magnitude(*, replay_row):
    """Project the SCORE magnitude only: SCORE-family prerequisites plus the Phase-5-lexis
    ``passive_score_magnitude`` (verbatim text + exact base-10 Decimal). Inspects neither context,
    timestamp, nor unit."""
    _require_row(replay_row)
    row_kind = _envelope_str(replay_row, "observation_kind")
    row_family = _envelope_str(replay_row, "family_descriptor")
    payload = _parse_payload(replay_row)
    family_payload = _require_score_family(row_kind, row_family, payload)
    magnitude_text, magnitude = _validate_magnitude(_member(family_payload, "passive_score_magnitude"))
    return _make_score_magnitude(
        passive_score_magnitude_text=magnitude_text, passive_score_magnitude=magnitude)
