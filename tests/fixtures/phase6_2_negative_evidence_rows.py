"""tests/fixtures/phase6_2_negative_evidence_rows.py — quarantined negative-evidence row builder.

Authorized by ``docs/handoff/phase6_2_negative_evidence_fixture_boundary_charter.md`` (`b4368fd`) and
``docs/handoff/phase6_2_negative_evidence_case_isolation_relevance_harness_micro_correction_charter.md``
(`045caea`). This is a **tests-only** helper that constructs **intentionally invalid** S1 replay rows whose
**only** permitted outcome is a Slice-C ``S1EvidenceProjectionError`` (the projector-level hard failure).

Construction boundary (binding, charter §5 / §15):
  - the row is a **genuine** ``sqlite3.Row`` built with ``sqlite3.connect(":memory:")``,
    ``row_factory = sqlite3.Row`` and **one parameterized ``SELECT``** aliasing exactly the six replay
    columns — **no table, no DDL/DML, no temp/production DB, no adapter, no mock/monkeypatch/fake-Row/dict
    substitution, no private SQL-constant import, no network/persistent state**;
  - each builder call uses a **fresh** in-memory connection, produces **exactly one** ``sqlite3.Row``,
    **closes the connection**, and returns **only** that Row (never the connection/cursor);
  - it is a **closed case selector**, not a generic factory: the caller selects one of the seven closed
    cases (plus a required subvariant for Cases 5/6/7) and supplies nothing else — no arbitrary payload,
    column, value, or SQL.

Single-fault discipline (charter §3): every case malforms **exactly one** named invariant while keeping
every other field valid and canonical enough to reach that exact rejection branch. The seven cases are a
strict partition; Case 3 owns all row/payload timestamp disagreement, Case 7 is consistent-invalids only.
"""
import json
import sqlite3


# --- closed top-level negative-case vocabulary (charter §4) ---------------------------------------
ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT = "ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT"
ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT = "ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT"
ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT = "ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT"
MALFORMED_CANONICAL_JSON = "MALFORMED_CANONICAL_JSON"
MALFORMED_SCORE_INPUTS_SUMMARY = "MALFORMED_SCORE_INPUTS_SUMMARY"
INVALID_S1_DECIMAL_LEXIS = "INVALID_S1_DECIMAL_LEXIS"
INVALID_PROVENANCE_TIMESTAMP = "INVALID_PROVENANCE_TIMESTAMP"

NEGATIVE_EVIDENCE_CASES = (
    ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT,
    ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT,
    ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT,
    MALFORMED_CANONICAL_JSON,
    MALFORMED_SCORE_INPUTS_SUMMARY,
    INVALID_S1_DECIMAL_LEXIS,
    INVALID_PROVENANCE_TIMESTAMP,
)

# --- closed subvariants (charter §6/§7/§8; Case-5 extended by 04c88fc §6 + c8204ec §4) ------------
MISSING_SCORE_INPUTS_SUMMARY = "MISSING_SCORE_INPUTS_SUMMARY"
WRONG_ARITY_SCORE_INPUTS_SUMMARY = "WRONG_ARITY_SCORE_INPUTS_SUMMARY"
NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT = "NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT"
EMPTY_TEXT_ELEMENT = "EMPTY_TEXT_ELEMENT"
WHITESPACE_ONLY_TEXT_ELEMENT = "WHITESPACE_ONLY_TEXT_ELEMENT"
SCORE_INPUTS_SUMMARY_SUBVARIANTS = (
    MISSING_SCORE_INPUTS_SUMMARY,
    WRONG_ARITY_SCORE_INPUTS_SUMMARY,
    NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT,
    EMPTY_TEXT_ELEMENT,
    WHITESPACE_ONLY_TEXT_ELEMENT,
)

LEADING_PLUS_DECIMAL = "LEADING_PLUS_DECIMAL"
EXPONENT_DECIMAL = "EXPONENT_DECIMAL"
WHITESPACE_PADDED_DECIMAL = "WHITESPACE_PADDED_DECIMAL"
EMPTY_DECIMAL_TEXT = "EMPTY_DECIMAL_TEXT"
NON_DECIMAL_TEXT = "NON_DECIMAL_TEXT"
DECIMAL_LEXIS_SUBVARIANTS = (
    LEADING_PLUS_DECIMAL,
    EXPONENT_DECIMAL,
    WHITESPACE_PADDED_DECIMAL,
    EMPTY_DECIMAL_TEXT,
    NON_DECIMAL_TEXT,
)

CONSISTENT_NEGATIVE_TIMESTAMP = "CONSISTENT_NEGATIVE_TIMESTAMP"
CONSISTENT_NON_INTEGER_TIMESTAMP = "CONSISTENT_NON_INTEGER_TIMESTAMP"
PROVENANCE_TIMESTAMP_SUBVARIANTS = (
    CONSISTENT_NEGATIVE_TIMESTAMP,
    CONSISTENT_NON_INTEGER_TIMESTAMP,
)

_SUBVARIANTS_BY_CASE = {
    MALFORMED_SCORE_INPUTS_SUMMARY: SCORE_INPUTS_SUMMARY_SUBVARIANTS,
    INVALID_S1_DECIMAL_LEXIS: DECIMAL_LEXIS_SUBVARIANTS,
    INVALID_PROVENANCE_TIMESTAMP: PROVENANCE_TIMESTAMP_SUBVARIANTS,
}

# the exact six replay aliases (charter §5).
_SELECT_SIX_ALIASES = (
    "SELECT ? AS observation_kind, ? AS family_descriptor, ? AS artifact_locator, "
    "? AS physical_record_position, ? AS provenance_timestamp, ? AS canonical_text_payload"
)

# A fixed canonical Silver pair + baseline timestamp shared by every case (opaque identity only).
_BASELINE_LOCATOR = "opaque-artifact-locator"
_BASELINE_POSITION = "0"
_BASELINE_TIMESTAMP_TEXT = "1750000000000"
_BASELINE_TIMESTAMP_INT = 1750000000000
_FAMILY_DESCRIPTOR = "passive_net_edge_diagnostic"


class NegativeEvidenceFixtureError(Exception):
    """Raised for fixture misuse (unknown case / missing or invalid subvariant) — an ordinary test-time
    programmer error, never an asserted Slice-C ``S1EvidenceProjectionError``."""


def _baseline_family_payload():
    return {
        "passive_score_magnitude": "7",
        "score_unit_context": "proportion",
        "score_inputs_summary": ["hl", "BTC"],
        "score_family_descriptor": _FAMILY_DESCRIPTOR,
    }


def _baseline_payload_obj():
    return {
        "observation_kind": "SCORE",
        "provenance_timestamp": _BASELINE_TIMESTAMP_INT,
        "family_payload": _baseline_family_payload(),
    }


def _canonical(payload_obj):
    return json.dumps(payload_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _row_from_columns(*, observation_kind, family_descriptor, artifact_locator,
                      physical_record_position, provenance_timestamp, canonical_text_payload):
    """Build exactly one genuine ``sqlite3.Row`` over the six aliases, then close the connection."""
    connection = sqlite3.connect(":memory:")
    try:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            _SELECT_SIX_ALIASES,
            (observation_kind, family_descriptor, artifact_locator,
             physical_record_position, provenance_timestamp, canonical_text_payload),
        ).fetchone()
    finally:
        connection.close()
    return row


def _decimal_lexis_for(subvariant):
    return {
        LEADING_PLUS_DECIMAL: "+1",
        EXPONENT_DECIMAL: "1e3",
        WHITESPACE_PADDED_DECIMAL: " 1 ",
        EMPTY_DECIMAL_TEXT: "",
        NON_DECIMAL_TEXT: "not-a-decimal",
    }[subvariant]


def _validate_selection(case, subvariant):
    if case not in NEGATIVE_EVIDENCE_CASES:
        raise NegativeEvidenceFixtureError(f"unknown negative-evidence case: {case!r}")
    allowed = _SUBVARIANTS_BY_CASE.get(case)
    if allowed is None:
        if subvariant is not None:
            raise NegativeEvidenceFixtureError(f"case {case} accepts no subvariant")
    else:
        if subvariant not in allowed:
            raise NegativeEvidenceFixtureError(
                f"case {case} requires a subvariant in {allowed}; got {subvariant!r}"
            )


def build_negative_evidence_row(*, case, subvariant=None):
    """Return exactly one genuine, intentionally-invalid ``sqlite3.Row`` for the selected closed case.

    Every case malforms exactly one named invariant; all other fields stay valid and canonical so the
    projector reaches that exact rejection branch (absolute single-fault rule). The connection is closed
    before return; only the Row is handed back.
    """
    _validate_selection(case, subvariant)

    observation_kind = "SCORE"
    family_descriptor = _FAMILY_DESCRIPTOR
    provenance_timestamp_text = _BASELINE_TIMESTAMP_TEXT
    payload = _baseline_payload_obj()

    if case == ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT:
        # row kind and payload kind are each individually valid tokens but unequal.
        payload["observation_kind"] = "HALT"
        canonical_text_payload = _canonical(payload)
    elif case == ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT:
        # row and payload descriptors each individually valid text but unequal.
        payload["family_payload"]["score_family_descriptor"] = "passive_local_parse_halt"
        canonical_text_payload = _canonical(payload)
    elif case == ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT:
        # row and payload timestamps each individually valid non-negative integers but unequal.
        payload["provenance_timestamp"] = _BASELINE_TIMESTAMP_INT + 1
        canonical_text_payload = _canonical(payload)
    elif case == MALFORMED_CANONICAL_JSON:
        # one fixed truncated-object form; all row columns otherwise valid.
        canonical_text_payload = '{"observation_kind": "SCORE"'
    elif case == MALFORMED_SCORE_INPUTS_SUMMARY:
        if subvariant == MISSING_SCORE_INPUTS_SUMMARY:
            del payload["family_payload"]["score_inputs_summary"]
        elif subvariant == WRONG_ARITY_SCORE_INPUTS_SUMMARY:
            payload["family_payload"]["score_inputs_summary"] = ["hl"]
        elif subvariant == NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT:
            payload["family_payload"]["score_inputs_summary"] = ["hl", 7]
        elif subvariant == EMPTY_TEXT_ELEMENT:
            # exactly ["hl", ""] — second element the empty string.
            payload["family_payload"]["score_inputs_summary"] = ["hl", ""]
        else:  # WHITESPACE_ONLY_TEXT_ELEMENT — exactly ["hl", " "]; second element one U+0020 (0x20).
            payload["family_payload"]["score_inputs_summary"] = ["hl", " "]
        canonical_text_payload = _canonical(payload)
    elif case == INVALID_S1_DECIMAL_LEXIS:
        payload["family_payload"]["passive_score_magnitude"] = _decimal_lexis_for(subvariant)
        canonical_text_payload = _canonical(payload)
    else:  # INVALID_PROVENANCE_TIMESTAMP — row and payload represent the SAME invalid value.
        if subvariant == CONSISTENT_NEGATIVE_TIMESTAMP:
            payload["provenance_timestamp"] = -5
            provenance_timestamp_text = "-5"
        else:  # CONSISTENT_NON_INTEGER_TIMESTAMP
            payload["provenance_timestamp"] = 1.5
            provenance_timestamp_text = "1.5"
        canonical_text_payload = _canonical(payload)

    return _row_from_columns(
        observation_kind=observation_kind,
        family_descriptor=family_descriptor,
        artifact_locator=_BASELINE_LOCATOR,
        physical_record_position=_BASELINE_POSITION,
        provenance_timestamp=provenance_timestamp_text,
        canonical_text_payload=canonical_text_payload,
    )
