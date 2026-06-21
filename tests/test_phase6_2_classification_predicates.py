"""tests/test_phase6_2_classification_predicates.py — Phase 6.2 Slice D — Classification Predicates.

Pins the quarantined, pure classification predicates
(`phase6_2_shadow_intent/classification_predicates.py`) built under the ratified Phase 6.2 chain: the
reconstruction-runtime planning/slice charter (`457d279`), the evidence-intersection predicate charter
(`474cc6f`), the precedence/decimal-consistency correction (`d7204d6`), the duplicate-root/context-first
micro-correction (`f57d116`), and the signed-64 duration amendment (`e471f19`).

Each predicate is a pure, deterministic classifier over exact Slice-A logical values and Slice-C narrow
projection carriers. It inspects ONLY its own narrow inputs; it never invokes another classifier, never
revalidates a whole definition, and never parses a row, touches SQLite, reads an artifact, runs a replay
loop, mutates state, applies a lifecycle transition, or caches. Slice E (not Slice D) owns precedence
ordering and state transitions. Timestamp arithmetic is exact lexical/digit arithmetic — never `int()` on
S1 timestamp text, never float/Decimal — so arbitrarily long canonical timestamps are exact.

Slice-C carriers under test are produced ONLY through the ratified Slice-C projection operations over real
in-memory `sqlite3.Row` values; Slice-A values are built through the ratified `logical_model` factories.
Forged (`object.__new__`) inputs appear ONLY to prove the consumer-side defensive revalidation.
"""
import ast
import inspect
import json
import pathlib
import sqlite3
from decimal import Decimal

import pytest

import phase6_2_shadow_intent.classification_predicates as cp
from phase6_2_shadow_intent.classification_predicates import (
    silver_pair_intersects,
    context_equals,
    classify_timestamp_window,
    unit_comparable,
    classify_directional_crossing,
    ClassificationPredicateError,
    CLASSIFICATION_PREDICATES_COMPONENT_NAME,
    WINDOW_NON_COMPARABLE,
    WINDOW_IN_WINDOW,
    WINDOW_EXPIRED,
    PREDICATE_WRONG_CARRIER_TYPE,
    PREDICATE_FORGED_OR_MISSING_SLOT,
    PREDICATE_INVALID_TEXT,
    PREDICATE_INVALID_CANONICAL_TIMESTAMP,
    PREDICATE_INVALID_DURATION,
    PREDICATE_INVALID_DECIMAL,
    PREDICATE_INVALID_DECIMAL_LEXIS,
    PREDICATE_MAGNITUDE_TEXT_VALUE_DISAGREEMENT,
    PREDICATE_INVALID_ORIENTATION,
    PREDICATE_INERT_HAS_NO_CROSSING,
)
import phase6_2_shadow_intent.s1_evidence_projection as sep
import phase6_2_shadow_intent.logical_model as lm


# --- Slice-C carrier builders (genuine carriers via the ratified ops over real in-memory rows) -----

def _row(*, observation_kind="SCORE", family_descriptor="passive_net_edge_diagnostic",
         artifact_locator="loc", physical_record_position="pos",
         provenance_timestamp="0", canonical_text_payload="{}"):
    connection = sqlite3.connect(":memory:")
    try:
        connection.row_factory = sqlite3.Row
        return connection.execute(
            "SELECT ? AS observation_kind, ? AS family_descriptor, ? AS artifact_locator, "
            "? AS physical_record_position, ? AS provenance_timestamp, ? AS canonical_text_payload",
            (observation_kind, family_descriptor, artifact_locator, physical_record_position,
             provenance_timestamp, canonical_text_payload)).fetchone()
    finally:
        connection.close()


def _silver_pair(locator="loc", position="pos"):
    return sep.project_silver_pair(replay_row=_row(artifact_locator=locator,
                                                   physical_record_position=position))


def _context(a, b):
    payload = json.dumps({"family_payload": {"score_inputs_summary": [a, b]}})
    return sep.project_score_context(replay_row=_row(canonical_text_payload=payload))


def _timestamp(digits):
    payload = '{"provenance_timestamp": ' + digits + '}'   # canonical digits -> a valid JSON number
    return sep.project_score_timestamp(
        replay_row=_row(provenance_timestamp=digits, canonical_text_payload=payload))


def _unit(unit_text):
    payload = json.dumps({"family_payload": {"score_unit_context": unit_text}})
    return sep.project_score_unit(replay_row=_row(canonical_text_payload=payload))


def _magnitude(text):
    payload = json.dumps({"family_payload": {"passive_score_magnitude": text}})
    return sep.project_score_magnitude(replay_row=_row(canonical_text_payload=payload))


def _key(locator="loc", position="pos"):
    return lm.make_opaque_silver_pair_key(silver_artifact_locator_text=locator,
                                          silver_physical_record_position_text=position)


# --- module identity ------------------------------------------------------------------------------

def test_component_name_constant():
    assert CLASSIFICATION_PREDICATES_COMPONENT_NAME == "phase6_2_shadow_intent_classification_predicates"


# --- Silver-pair intersection ---------------------------------------------------------------------

def test_silver_pair_intersects_exact_match():
    assert silver_pair_intersects(manifest_key=_key("L", "P"),
                                  observed_silver_pair=_silver_pair("L", "P")) is True


def test_silver_pair_intersects_false_on_any_component_difference():
    assert silver_pair_intersects(manifest_key=_key("L", "P"),
                                  observed_silver_pair=_silver_pair("L", "Q")) is False
    assert silver_pair_intersects(manifest_key=_key("L", "P"),
                                  observed_silver_pair=_silver_pair("M", "P")) is False


def test_silver_pair_is_byte_exact_no_trim_or_casefold():
    assert silver_pair_intersects(manifest_key=_key("L", "P"),
                                  observed_silver_pair=_silver_pair(" L", "P")) is False
    assert silver_pair_intersects(manifest_key=_key("l", "P"),
                                  observed_silver_pair=_silver_pair("L", "P")) is False


def test_silver_pair_rejects_wrong_carrier_types():
    with pytest.raises(ClassificationPredicateError) as e1:
        silver_pair_intersects(manifest_key="not-a-key", observed_silver_pair=_silver_pair())
    assert e1.value.reason == PREDICATE_WRONG_CARRIER_TYPE
    with pytest.raises(ClassificationPredicateError) as e2:
        silver_pair_intersects(manifest_key=_key(), observed_silver_pair="not-a-projection")
    assert e2.value.reason == PREDICATE_WRONG_CARRIER_TYPE


def test_silver_pair_rejects_forged_missing_slot():
    forged = object.__new__(sep.SilverPairProjection)        # no slots set
    with pytest.raises(ClassificationPredicateError) as exc:
        silver_pair_intersects(manifest_key=_key(), observed_silver_pair=forged)
    assert exc.value.reason == PREDICATE_FORGED_OR_MISSING_SLOT


# --- context equality -----------------------------------------------------------------------------

def test_context_equals_exact():
    assert context_equals(root_context=_context("hl", "BTC"),
                          observed_context=_context("hl", "BTC")) is True


def test_context_unequal_on_any_scalar():
    assert context_equals(root_context=_context("hl", "BTC"),
                          observed_context=_context("hl", "ETH")) is False
    assert context_equals(root_context=_context("hl", "BTC"),
                          observed_context=_context("kraken", "BTC")) is False


def test_context_is_byte_exact_no_normalization():
    assert context_equals(root_context=_context("hl", "BTC"),
                          observed_context=_context("hl ", "BTC")) is False   # trailing space preserved
    assert context_equals(root_context=_context("HL", "BTC"),
                          observed_context=_context("hl", "BTC")) is False   # case preserved


def test_context_rejects_wrong_type_and_forged():
    with pytest.raises(ClassificationPredicateError) as e1:
        context_equals(root_context="x", observed_context=_context("hl", "BTC"))
    assert e1.value.reason == PREDICATE_WRONG_CARRIER_TYPE
    forged = object.__new__(sep.ScoreContextProjection)
    with pytest.raises(ClassificationPredicateError) as e2:
        context_equals(root_context=_context("hl", "BTC"), observed_context=forged)
    assert e2.value.reason == PREDICATE_FORGED_OR_MISSING_SLOT


# --- timestamp-window classification (exact lexical arithmetic, no int()) -------------------------

def test_window_zero_duration_boundary():
    assert classify_timestamp_window(anchor=_timestamp("100"), comparison=_timestamp("100"),
                                     duration_ms=0) == WINDOW_IN_WINDOW
    assert classify_timestamp_window(anchor=_timestamp("100"), comparison=_timestamp("101"),
                                     duration_ms=0) == WINDOW_EXPIRED


def test_window_delta_equals_duration_is_in_window():
    assert classify_timestamp_window(anchor=_timestamp("100"), comparison=_timestamp("105"),
                                     duration_ms=5) == WINDOW_IN_WINDOW


def test_window_delta_equals_duration_plus_one_is_expired():
    assert classify_timestamp_window(anchor=_timestamp("100"), comparison=_timestamp("106"),
                                     duration_ms=5) == WINDOW_EXPIRED


def test_window_negative_delta_is_non_comparable():
    assert classify_timestamp_window(anchor=_timestamp("100"), comparison=_timestamp("99"),
                                     duration_ms=5) == WINDOW_NON_COMPARABLE


def test_window_max_duration_boundary():
    mx = str(lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS)
    assert classify_timestamp_window(anchor=_timestamp("0"), comparison=_timestamp(mx),
                                     duration_ms=lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS) == WINDOW_IN_WINDOW
    over = str(lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS + 1)
    assert classify_timestamp_window(anchor=_timestamp("0"), comparison=_timestamp(over),
                                     duration_ms=lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS) == WINDOW_EXPIRED


def test_window_5000_digit_timestamps_without_raw_valueerror():
    big = "1" + "0" * 4999                       # 10**4999, a 5000-digit canonical integer
    big_plus_one = "1" + "0" * 4998 + "1"        # 10**4999 + 1
    assert classify_timestamp_window(anchor=_timestamp(big), comparison=_timestamp(big),
                                     duration_ms=0) == WINDOW_IN_WINDOW
    assert classify_timestamp_window(anchor=_timestamp(big), comparison=_timestamp(big_plus_one),
                                     duration_ms=0) == WINDOW_EXPIRED
    assert classify_timestamp_window(anchor=_timestamp(big), comparison=_timestamp("0"),
                                     duration_ms=0) == WINDOW_NON_COMPARABLE


def test_window_rejects_invalid_duration():
    for bad in (-1, lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS + 1, True, "5", 1.0):
        with pytest.raises(ClassificationPredicateError) as exc:
            classify_timestamp_window(anchor=_timestamp("0"), comparison=_timestamp("0"), duration_ms=bad)
        assert exc.value.reason == PREDICATE_INVALID_DURATION


def test_window_rejects_wrong_type_and_forged_or_noncanonical():
    with pytest.raises(ClassificationPredicateError) as e1:
        classify_timestamp_window(anchor="x", comparison=_timestamp("0"), duration_ms=0)
    assert e1.value.reason == PREDICATE_WRONG_CARRIER_TYPE
    missing = object.__new__(sep.ScoreTimestampProjection)
    with pytest.raises(ClassificationPredicateError) as e2:
        classify_timestamp_window(anchor=missing, comparison=_timestamp("0"), duration_ms=0)
    assert e2.value.reason == PREDICATE_FORGED_OR_MISSING_SLOT
    forged = object.__new__(sep.ScoreTimestampProjection)
    object.__setattr__(forged, "provenance_timestamp", "-5")     # non-canonical forged value
    with pytest.raises(ClassificationPredicateError) as e3:
        classify_timestamp_window(anchor=forged, comparison=_timestamp("0"), duration_ms=0)
    assert e3.value.reason == PREDICATE_INVALID_CANONICAL_TIMESTAMP


# --- unit comparability ---------------------------------------------------------------------------

def test_unit_comparable_exact():
    assert unit_comparable(boundary_unit_context="proportion",
                           observed_unit=_unit("proportion")) is True


def test_unit_incomparable_byte_exact():
    assert unit_comparable(boundary_unit_context="proportion", observed_unit=_unit("Proportion")) is False
    assert unit_comparable(boundary_unit_context="proportion", observed_unit=_unit(" proportion")) is False


def test_unit_rejects_non_text_boundary_and_forged():
    with pytest.raises(ClassificationPredicateError) as e1:
        unit_comparable(boundary_unit_context=7, observed_unit=_unit("proportion"))
    assert e1.value.reason in (PREDICATE_WRONG_CARRIER_TYPE, PREDICATE_INVALID_ORIENTATION,
                               "PREDICATE_INVALID_TEXT")
    with pytest.raises(ClassificationPredicateError) as e2:
        unit_comparable(boundary_unit_context="proportion", observed_unit="not-a-carrier")
    assert e2.value.reason == PREDICATE_WRONG_CARRIER_TYPE
    forged = object.__new__(sep.ScoreUnitProjection)
    with pytest.raises(ClassificationPredicateError) as e3:
        unit_comparable(boundary_unit_context="proportion", observed_unit=forged)
    assert e3.value.reason == PREDICATE_FORGED_OR_MISSING_SLOT


# --- directional Decimal crossing -----------------------------------------------------------------

def test_positive_crossing_at_and_above_boundary():
    assert classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                         boundary_magnitude=Decimal("1.5"),
                                         observed_magnitude=_magnitude("1.5")) is True
    assert classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                         boundary_magnitude=Decimal("1.5"),
                                         observed_magnitude=_magnitude("1.51")) is True


def test_positive_crossing_below_boundary_is_false():
    assert classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                         boundary_magnitude=Decimal("1.5"),
                                         observed_magnitude=_magnitude("1.49")) is False


def test_negative_crossing_at_and_below_boundary():
    assert classify_directional_crossing(exposure_orientation=lm.NEGATIVE_EXPOSURE,
                                         boundary_magnitude=Decimal("1.5"),
                                         observed_magnitude=_magnitude("1.5")) is True
    assert classify_directional_crossing(exposure_orientation=lm.NEGATIVE_EXPOSURE,
                                         boundary_magnitude=Decimal("1.5"),
                                         observed_magnitude=_magnitude("1.51")) is False


def test_crossing_decimal_equality_150_equals_15():
    # 1.50 == 1.5 exactly -> at-boundary crossing holds for both orientations.
    assert classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                         boundary_magnitude=Decimal("1.5"),
                                         observed_magnitude=_magnitude("1.50")) is True
    assert classify_directional_crossing(exposure_orientation=lm.NEGATIVE_EXPOSURE,
                                         boundary_magnitude=Decimal("1.5"),
                                         observed_magnitude=_magnitude("1.50")) is True


def test_crossing_negative_zero_equals_zero():
    assert classify_directional_crossing(exposure_orientation=lm.NEGATIVE_EXPOSURE,
                                         boundary_magnitude=Decimal("0"),
                                         observed_magnitude=_magnitude("-0")) is True
    assert classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                         boundary_magnitude=Decimal("0"),
                                         observed_magnitude=_magnitude("-0")) is True


def test_crossing_negative_values():
    assert classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                         boundary_magnitude=Decimal("-2"),
                                         observed_magnitude=_magnitude("-1")) is True
    assert classify_directional_crossing(exposure_orientation=lm.NEGATIVE_EXPOSURE,
                                         boundary_magnitude=Decimal("-2"),
                                         observed_magnitude=_magnitude("-3")) is True


def test_inert_has_no_crossing_and_does_not_inspect_magnitude():
    # INERT_STATE is rejected BEFORE the magnitude carrier is inspected (pass a forged/None magnitude).
    with pytest.raises(ClassificationPredicateError) as exc:
        classify_directional_crossing(exposure_orientation=lm.INERT_STATE,
                                      boundary_magnitude=Decimal("1"),
                                      observed_magnitude=None)
    assert exc.value.reason == PREDICATE_INERT_HAS_NO_CROSSING


def test_crossing_rejects_invalid_orientation_and_decimal_and_forged():
    with pytest.raises(ClassificationPredicateError) as e1:
        classify_directional_crossing(exposure_orientation="SIDEWAYS",
                                      boundary_magnitude=Decimal("1"),
                                      observed_magnitude=_magnitude("1"))
    assert e1.value.reason == PREDICATE_INVALID_ORIENTATION
    with pytest.raises(ClassificationPredicateError) as e2:
        classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                      boundary_magnitude=1.5,            # float, not Decimal
                                      observed_magnitude=_magnitude("1"))
    assert e2.value.reason == PREDICATE_INVALID_DECIMAL
    with pytest.raises(ClassificationPredicateError) as e3:
        classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                      boundary_magnitude=Decimal("1"),
                                      observed_magnitude="not-a-carrier")
    assert e3.value.reason == PREDICATE_WRONG_CARRIER_TYPE
    forged = object.__new__(sep.ScoreMagnitudeProjection)
    with pytest.raises(ClassificationPredicateError) as e4:
        classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                      boundary_magnitude=Decimal("1"), observed_magnitude=forged)
    assert e4.value.reason == PREDICATE_FORGED_OR_MISSING_SLOT


def test_crossing_rejects_non_finite_boundary_decimal():
    with pytest.raises(ClassificationPredicateError) as exc:
        classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                      boundary_magnitude=Decimal("NaN"),
                                      observed_magnitude=_magnitude("1"))
    assert exc.value.reason == PREDICATE_INVALID_DECIMAL


# --- purity / determinism / no-mutation -----------------------------------------------------------

def test_predicates_are_deterministic_and_pure():
    sp_key, sp_obs = _key("L", "P"), _silver_pair("L", "P")
    assert silver_pair_intersects(manifest_key=sp_key, observed_silver_pair=sp_obs) is \
        silver_pair_intersects(manifest_key=sp_key, observed_silver_pair=sp_obs)
    mag = _magnitude("1.50")
    before = mag.passive_score_magnitude
    classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                  boundary_magnitude=Decimal("1.5"), observed_magnitude=mag)
    assert mag.passive_score_magnitude == before        # input carrier not mutated


# --- strict field privacy: no classifier calls another / no whole-definition pass (static) --------

_PUBLIC_PREDICATES = (silver_pair_intersects, context_equals, classify_timestamp_window,
                      unit_comparable, classify_directional_crossing)


def test_no_classifier_invokes_another_and_no_whole_definition_pass():
    predicate_names = {fn.__name__ for fn in _PUBLIC_PREDICATES}
    for fn in _PUBLIC_PREDICATES:
        src = inspect.getsource(fn)
        for other in predicate_names - {fn.__name__}:
            assert other + "(" not in src, (fn.__name__, other)
        # no predicate revalidates an entire Slice-A definition (only narrow fields are passed in).
        assert "ShadowIntentDefinition" not in src, fn.__name__


# --- consumer-boundary populated-forgery defenses -------------------------------------------------

def _forge(carrier_type, **slots):
    """An object.__new__-forged carrier with caller-chosen POPULATED slots (bypasses the Slice-C
    factory's publication invariants) — used ONLY to prove Slice-D defensive revalidation."""
    obj = object.__new__(carrier_type)
    for name, value in slots.items():
        object.__setattr__(obj, name, value)
    return obj


@pytest.mark.parametrize("bad_tuple", [("", "BTC"), ("hl", ""), (" ", "BTC"), ("hl", " ")])
def test_context_rejects_populated_blank_forgery_in_both_positions(bad_tuple):
    forged = _forge(sep.ScoreContextProjection, score_inputs_summary=bad_tuple)
    valid = _context("hl", "BTC")
    with pytest.raises(ClassificationPredicateError) as e_root:
        context_equals(root_context=forged, observed_context=valid)
    assert e_root.value.reason == PREDICATE_INVALID_TEXT
    with pytest.raises(ClassificationPredicateError) as e_obs:
        context_equals(root_context=valid, observed_context=forged)
    assert e_obs.value.reason == PREDICATE_INVALID_TEXT


def test_context_rejects_non_tuple_and_wrong_arity_and_non_text_forgery():
    valid = _context("hl", "BTC")
    for bad in (["hl", "BTC"], ("hl",), ("hl", "BTC", "x"), ("hl", 7)):
        forged = _forge(sep.ScoreContextProjection, score_inputs_summary=bad)
        with pytest.raises(ClassificationPredicateError) as exc:
            context_equals(root_context=forged, observed_context=valid)
        assert exc.value.reason == PREDICATE_INVALID_TEXT


def test_context_preserves_valid_verbatim_text_with_internal_or_edge_nonblank():
    # a trailing-space-but-nonblank scalar is VALID and preserved verbatim (no trim/repair).
    a = _forge(sep.ScoreContextProjection, score_inputs_summary=("hl ", "BTC"))
    b = _forge(sep.ScoreContextProjection, score_inputs_summary=("hl ", "BTC"))
    assert context_equals(root_context=a, observed_context=b) is True
    c = _context("hl", "BTC")                       # genuine "hl" (no trailing space)
    assert context_equals(root_context=a, observed_context=c) is False   # byte-exact, not trimmed


def test_magnitude_rejects_text_value_disagreement_forgery():
    forged = _forge(sep.ScoreMagnitudeProjection,
                    passive_score_magnitude_text="7", passive_score_magnitude=Decimal("8"))
    with pytest.raises(ClassificationPredicateError) as exc:
        classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                      boundary_magnitude=Decimal("1"), observed_magnitude=forged)
    assert exc.value.reason == PREDICATE_MAGNITUDE_TEXT_VALUE_DISAGREEMENT


def test_magnitude_rejects_invalid_lexical_text_forgery():
    for bad_text in ("garbage", "+1", "1e3", " 1 ", "", "1."):
        forged = _forge(sep.ScoreMagnitudeProjection,
                        passive_score_magnitude_text=bad_text, passive_score_magnitude=Decimal("1"))
        with pytest.raises(ClassificationPredicateError) as exc:
            classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                          boundary_magnitude=Decimal("1"), observed_magnitude=forged)
        assert exc.value.reason == PREDICATE_INVALID_DECIMAL_LEXIS


def test_magnitude_rejects_non_str_text_and_missing_slot_and_nonfinite_value():
    non_str_text = _forge(sep.ScoreMagnitudeProjection,
                          passive_score_magnitude_text=7, passive_score_magnitude=Decimal("7"))
    with pytest.raises(ClassificationPredicateError) as e1:
        classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                      boundary_magnitude=Decimal("1"), observed_magnitude=non_str_text)
    assert e1.value.reason == PREDICATE_INVALID_DECIMAL_LEXIS

    missing_text = _forge(sep.ScoreMagnitudeProjection, passive_score_magnitude=Decimal("7"))
    with pytest.raises(ClassificationPredicateError) as e2:
        classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                      boundary_magnitude=Decimal("1"), observed_magnitude=missing_text)
    assert e2.value.reason == PREDICATE_FORGED_OR_MISSING_SLOT

    non_finite = _forge(sep.ScoreMagnitudeProjection,
                        passive_score_magnitude_text="1", passive_score_magnitude=Decimal("NaN"))
    with pytest.raises(ClassificationPredicateError) as e3:
        classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                      boundary_magnitude=Decimal("1"), observed_magnitude=non_finite)
    assert e3.value.reason == PREDICATE_INVALID_DECIMAL


def test_magnitude_accepts_valid_lexical_distinctions_via_forgery():
    # 007 / 1.50 / -0 are Phase-5-valid with Decimal(text) == stored value.
    for text in ("007", "1.50", "-0"):
        carrier = _forge(sep.ScoreMagnitudeProjection,
                         passive_score_magnitude_text=text, passive_score_magnitude=Decimal(text))
        # POSITIVE vs a boundary at/below the value -> a clean bool, no error.
        result = classify_directional_crossing(
            exposure_orientation=lm.POSITIVE_EXPOSURE,
            boundary_magnitude=Decimal(text), observed_magnitude=carrier)
        assert result is True


def test_orientation_requires_exact_str_type_rejecting_subclass():
    class _StrSub(str):
        pass
    valid_mag = _magnitude("2")
    for impostor in (_StrSub("POSITIVE_EXPOSURE"), _StrSub("NEGATIVE_EXPOSURE")):
        with pytest.raises(ClassificationPredicateError) as exc:
            classify_directional_crossing(exposure_orientation=impostor,
                                          boundary_magnitude=Decimal("1"), observed_magnitude=valid_mag)
        assert exc.value.reason == PREDICATE_INVALID_ORIENTATION


def test_orientation_rejects_equality_impostor_without_invoking_eq():
    class _EqBomb:
        def __eq__(self, other):
            raise AssertionError("exposure_orientation __eq__ must never be invoked")
        __hash__ = None
    with pytest.raises(ClassificationPredicateError) as exc:
        classify_directional_crossing(exposure_orientation=_EqBomb(),
                                      boundary_magnitude=Decimal("1"),
                                      observed_magnitude=_magnitude("1"))
    assert exc.value.reason == PREDICATE_INVALID_ORIENTATION


def test_inert_rejection_still_precedes_magnitude_inspection_after_type_guard():
    # exact-str INERT_STATE is still rejected BEFORE any magnitude inspection.
    with pytest.raises(ClassificationPredicateError) as exc:
        classify_directional_crossing(exposure_orientation=lm.INERT_STATE,
                                      boundary_magnitude=Decimal("1"), observed_magnitude=None)
    assert exc.value.reason == PREDICATE_INERT_HAS_NO_CROSSING


# --- dependency direction: only logical_model, s1_evidence_projection, stdlib ----------------------

def _module_path():
    return pathlib.Path(cp.__file__).resolve()


def test_dependency_direction_only_siblings_and_stdlib():
    tree = ast.parse(_module_path().read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.add(("." * node.level) + (node.module or ""))
    allowed = {
        "decimal",
        "phase6_2_shadow_intent.logical_model",
        "phase6_2_shadow_intent.s1_evidence_projection",
    }
    assert imports <= allowed, imports
    for imp in imports:
        root = imp.split(".")[0]
        assert root not in {"phase6_1", "phase6_1_s1_storage", "phase5", "artifact_verifier",
                            "tests", "pytest", "sqlite3", "json"}, imp


def test_runtime_has_no_row_sqlite_or_test_awareness():
    text = _module_path().read_text(encoding="utf-8")
    for token in ("sqlite3", "replay_row", "canonical_text_payload", "json.loads",
                  "pytest", "monkeypatch", "tests."):
        assert token not in text, token


def test_slice_e_f_targets_not_created():
    package = _module_path().parent
    for absent in ("atomic_replay_step.py", "reconstruction.py"):
        assert not (package / absent).exists(), absent
