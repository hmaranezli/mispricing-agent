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


def _root(venue="hl", pair="BTC"):
    # The Slice-A established-root carrier the lifecycle slot stores; the asymmetric root operand for
    # context_equals. Built through the ratified self-validating logical_model dataclass (no row, no maker).
    return lm.EstablishedRootContext(source_venue_context_text=venue, source_pair_context_text=pair)


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
    # ASYMMETRIC: root is the Slice-A EstablishedRootContext (two scalar fields); observed is the Slice-C
    # ScoreContextProjection (score_inputs_summary tuple). Compared byte/position-exact: venue<->[0], pair<->[1].
    assert context_equals(root_context=_root("hl", "BTC"),
                          observed_context=_context("hl", "BTC")) is True


def test_context_unequal_on_any_scalar():
    assert context_equals(root_context=_root("hl", "BTC"),
                          observed_context=_context("hl", "ETH")) is False
    assert context_equals(root_context=_root("hl", "BTC"),
                          observed_context=_context("kraken", "BTC")) is False


def test_context_is_byte_exact_no_normalization():
    assert context_equals(root_context=_root("hl", "BTC"),
                          observed_context=_context("hl ", "BTC")) is False   # trailing space preserved
    assert context_equals(root_context=_root("HL", "BTC"),
                          observed_context=_context("hl", "BTC")) is False   # case preserved


def test_context_root_must_be_established_root_not_score_context():
    # The OLD symmetric root operand (a ScoreContextProjection) is now an exact-carrier-type violation:
    # PREDICATE_WRONG_CARRIER_TYPE is reserved to the EstablishedRootContext root operand.
    with pytest.raises(ClassificationPredicateError) as exc:
        context_equals(root_context=_context("hl", "BTC"), observed_context=_context("hl", "BTC"))
    assert exc.value.reason == PREDICATE_WRONG_CARRIER_TYPE


def test_context_rejects_wrong_type_and_forged():
    with pytest.raises(ClassificationPredicateError) as e1:
        context_equals(root_context="x", observed_context=_context("hl", "BTC"))
    assert e1.value.reason == PREDICATE_WRONG_CARRIER_TYPE
    # observed-operand forgery (missing slot) still surfaces the closed forged/missing-slot reason.
    forged = object.__new__(sep.ScoreContextProjection)
    with pytest.raises(ClassificationPredicateError) as e2:
        context_equals(root_context=_root("hl", "BTC"), observed_context=forged)
    assert e2.value.reason == PREDICATE_FORGED_OR_MISSING_SLOT


def test_context_rejects_root_missing_slot_forgery():
    # An object.__new__-forged EstablishedRootContext with NO slots set surfaces the forged/missing-slot reason.
    forged_root = object.__new__(lm.EstablishedRootContext)
    with pytest.raises(ClassificationPredicateError) as exc:
        context_equals(root_context=forged_root, observed_context=_context("hl", "BTC"))
    assert exc.value.reason == PREDICATE_FORGED_OR_MISSING_SLOT


def test_context_rejects_root_partial_slot_forgery_matrix():
    # A PARTIALLY-populated EstablishedRootContext forgery (one slot set, the other slot left unset by
    # object.__new__) must surface PREDICATE_FORGED_OR_MISSING_SLOT for EITHER missing slot — never a raw
    # AttributeError (pytest.raises(ClassificationPredicateError) fails if AttributeError leaks instead).
    venue_only = object.__new__(lm.EstablishedRootContext)        # pair slot MISSING
    object.__setattr__(venue_only, "source_venue_context_text", "hl")
    with pytest.raises(ClassificationPredicateError) as e_pair:
        context_equals(root_context=venue_only, observed_context=_context("hl", "BTC"))
    assert e_pair.value.reason == PREDICATE_FORGED_OR_MISSING_SLOT

    pair_only = object.__new__(lm.EstablishedRootContext)         # venue slot MISSING
    object.__setattr__(pair_only, "source_pair_context_text", "BTC")
    with pytest.raises(ClassificationPredicateError) as e_venue:
        context_equals(root_context=pair_only, observed_context=_context("hl", "BTC"))
    assert e_venue.value.reason == PREDICATE_FORGED_OR_MISSING_SLOT


def test_context_root_u200b_scalar_is_nonblank_and_accepted():
    # U+200B is non-blank under Python str.strip() and is accepted verbatim in the root scalars.
    zwsp = "​"
    assert context_equals(root_context=_root(zwsp, "BTC"),
                          observed_context=_context(zwsp, "BTC")) is True
    assert context_equals(root_context=_root(zwsp, "BTC"),
                          observed_context=_context("hl", "BTC")) is False


# --- timestamp-window classification (exact lexical arithmetic, no int()) -------------------------

def test_window_zero_duration_boundary():
    # ASYMMETRIC: anchor is a bare canonical timestamp str; comparison stays a ScoreTimestampProjection.
    assert classify_timestamp_window(anchor="100", comparison=_timestamp("100"),
                                     duration_ms=0) == WINDOW_IN_WINDOW
    assert classify_timestamp_window(anchor="100", comparison=_timestamp("101"),
                                     duration_ms=0) == WINDOW_EXPIRED


def test_window_delta_equals_duration_is_in_window():
    assert classify_timestamp_window(anchor="100", comparison=_timestamp("105"),
                                     duration_ms=5) == WINDOW_IN_WINDOW


def test_window_delta_equals_duration_plus_one_is_expired():
    assert classify_timestamp_window(anchor="100", comparison=_timestamp("106"),
                                     duration_ms=5) == WINDOW_EXPIRED


def test_window_negative_delta_is_non_comparable():
    assert classify_timestamp_window(anchor="100", comparison=_timestamp("99"),
                                     duration_ms=5) == WINDOW_NON_COMPARABLE


def test_window_max_duration_boundary():
    mx = str(lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS)
    assert classify_timestamp_window(anchor="0", comparison=_timestamp(mx),
                                     duration_ms=lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS) == WINDOW_IN_WINDOW
    over = str(lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS + 1)
    assert classify_timestamp_window(anchor="0", comparison=_timestamp(over),
                                     duration_ms=lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS) == WINDOW_EXPIRED


def test_window_5000_digit_timestamps_without_raw_valueerror():
    big = "1" + "0" * 4999                       # 10**4999, a 5000-digit canonical integer
    big_plus_one = "1" + "0" * 4998 + "1"        # 10**4999 + 1
    assert classify_timestamp_window(anchor=big, comparison=_timestamp(big),
                                     duration_ms=0) == WINDOW_IN_WINDOW
    assert classify_timestamp_window(anchor=big, comparison=_timestamp(big_plus_one),
                                     duration_ms=0) == WINDOW_EXPIRED
    assert classify_timestamp_window(anchor=big, comparison=_timestamp("0"),
                                     duration_ms=0) == WINDOW_NON_COMPARABLE


def test_window_rejects_invalid_duration():
    for bad in (-1, lm.MAX_HYPOTHETICAL_WINDOW_DURATION_MS + 1, True, "5", 1.0):
        with pytest.raises(ClassificationPredicateError) as exc:
            classify_timestamp_window(anchor="0", comparison=_timestamp("0"), duration_ms=bad)
        assert exc.value.reason == PREDICATE_INVALID_DURATION


def test_window_anchor_non_canonical_str_is_invalid_canonical_timestamp():
    for bad in ("x", "", "-5", "00", "007", "+1", "1.0", "1e3", " 1", "1 "):
        with pytest.raises(ClassificationPredicateError) as exc:
            classify_timestamp_window(anchor=bad, comparison=_timestamp("0"), duration_ms=0)
        assert exc.value.reason == PREDICATE_INVALID_CANONICAL_TIMESTAMP


def test_window_anchor_every_non_str_maps_to_invalid_canonical_timestamp():
    # The OLD symmetric anchor (a ScoreTimestampProjection) and every other non-str value collapse to the
    # SAME reason: there is no carrier branch, ghost check, or PREDICATE_WRONG_CARRIER_TYPE for the anchor.
    class _StrSub(str):
        pass
    non_str_anchors = (
        _timestamp("0"),                                 # old symmetric ScoreTimestampProjection anchor
        object.__new__(sep.ScoreTimestampProjection),    # forged/missing-slot carrier
        100, True, None, Decimal("1"), b"100", ["100"], {"x": 1}, object(),
        _StrSub("100"),                                  # str subclass: type(x) is str is False
    )
    for bad in non_str_anchors:
        with pytest.raises(ClassificationPredicateError) as exc:
            classify_timestamp_window(anchor=bad, comparison=_timestamp("0"), duration_ms=0)
        assert exc.value.reason == PREDICATE_INVALID_CANONICAL_TIMESTAMP, repr(bad)


def test_window_comparison_carrier_wrong_type_forged_or_noncanonical():
    # PREDICATE_WRONG_CARRIER_TYPE is reserved to the comparison carrier operand.
    with pytest.raises(ClassificationPredicateError) as e1:
        classify_timestamp_window(anchor="0", comparison="x", duration_ms=0)
    assert e1.value.reason == PREDICATE_WRONG_CARRIER_TYPE
    missing = object.__new__(sep.ScoreTimestampProjection)
    with pytest.raises(ClassificationPredicateError) as e2:
        classify_timestamp_window(anchor="0", comparison=missing, duration_ms=0)
    assert e2.value.reason == PREDICATE_FORGED_OR_MISSING_SLOT
    forged = object.__new__(sep.ScoreTimestampProjection)
    object.__setattr__(forged, "provenance_timestamp", "-5")     # non-canonical forged value
    with pytest.raises(ClassificationPredicateError) as e3:
        classify_timestamp_window(anchor="0", comparison=forged, duration_ms=0)
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


@pytest.mark.parametrize("venue,pair", [("", "BTC"), ("hl", ""), (" ", "BTC"), ("hl", " ")])
def test_context_rejects_populated_blank_root_forgery(venue, pair):
    # An object.__new__-forged EstablishedRootContext with a populated-but-blank scalar (bypassing the
    # dataclass __post_init__) is rejected at the consumer boundary with the closed invalid-text reason.
    forged_root = _forge(lm.EstablishedRootContext,
                         source_venue_context_text=venue, source_pair_context_text=pair)
    with pytest.raises(ClassificationPredicateError) as exc:
        context_equals(root_context=forged_root, observed_context=_context("hl", "BTC"))
    assert exc.value.reason == PREDICATE_INVALID_TEXT


@pytest.mark.parametrize("bad_tuple", [("", "BTC"), ("hl", ""), (" ", "BTC"), ("hl", " ")])
def test_context_rejects_populated_blank_observed_forgery(bad_tuple):
    forged = _forge(sep.ScoreContextProjection, score_inputs_summary=bad_tuple)
    with pytest.raises(ClassificationPredicateError) as exc:
        context_equals(root_context=_root("hl", "BTC"), observed_context=forged)
    assert exc.value.reason == PREDICATE_INVALID_TEXT


def test_context_rejects_root_non_str_scalar_forgery():
    # A populated-but-non-str root scalar (bypassing __post_init__) surfaces the closed invalid-text reason.
    for venue, pair in ((7, "BTC"), ("hl", 7), (None, "BTC")):
        forged_root = _forge(lm.EstablishedRootContext,
                             source_venue_context_text=venue, source_pair_context_text=pair)
        with pytest.raises(ClassificationPredicateError) as exc:
            context_equals(root_context=forged_root, observed_context=_context("hl", "BTC"))
        assert exc.value.reason == PREDICATE_INVALID_TEXT


def test_context_rejects_non_tuple_and_wrong_arity_and_non_text_observed_forgery():
    valid_root = _root("hl", "BTC")
    for bad in (["hl", "BTC"], ("hl",), ("hl", "BTC", "x"), ("hl", 7)):
        forged = _forge(sep.ScoreContextProjection, score_inputs_summary=bad)
        with pytest.raises(ClassificationPredicateError) as exc:
            context_equals(root_context=valid_root, observed_context=forged)
        assert exc.value.reason == PREDICATE_INVALID_TEXT


def test_context_preserves_valid_verbatim_text_with_internal_or_edge_nonblank():
    # a trailing-space-but-nonblank scalar is VALID and preserved verbatim (no trim/repair).
    root_edge = _root("hl ", "BTC")                 # genuine self-validating root with trailing space
    obs_edge = _forge(sep.ScoreContextProjection, score_inputs_summary=("hl ", "BTC"))
    assert context_equals(root_context=root_edge, observed_context=obs_edge) is True
    c = _context("hl", "BTC")                       # genuine "hl" (no trailing space)
    assert context_equals(root_context=root_edge, observed_context=c) is False   # byte-exact, not trimmed


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
    # 007 / 1.50 / -0 are Phase-5-valid with Decimal(text) == stored value (Gate-B would reject all three).
    for text in ("007", "1.50", "-0"):
        carrier = _forge(sep.ScoreMagnitudeProjection,
                         passive_score_magnitude_text=text, passive_score_magnitude=Decimal(text))
        result = classify_directional_crossing(
            exposure_orientation=lm.POSITIVE_EXPOSURE,
            boundary_magnitude=Decimal(text), observed_magnitude=carrier)
        assert result is True


@pytest.mark.parametrize("text", ["١", "-١.٥", "७", "007", "1.50", "-0"])
def test_magnitude_accepts_phase5_unicode_decimal_digits_verbatim(text):
    # Python's `\d` (the ratified Phase-5 contract) accepts Unicode decimal digits, and so does Decimal.
    carrier = _forge(sep.ScoreMagnitudeProjection,
                     passive_score_magnitude_text=text, passive_score_magnitude=Decimal(text))
    assert carrier.passive_score_magnitude_text == text          # lexical text preserved verbatim
    result = classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                           boundary_magnitude=Decimal(text), observed_magnitude=carrier)
    assert result is True


@pytest.mark.parametrize("text", ["Ⅻ", "garbage", "+1", "1e3", " 1 ", "", "1.", "٤2x", "1٫5"])
def test_magnitude_rejects_non_phase5_text_including_unicode_nondigit(text):
    # Unicode numeric symbols Python's `\d` does NOT accept (Roman numeral, Arabic decimal separator,
    # mixed garbage) are rejected; the stored Decimal is irrelevant — lexis is checked first.
    forged = _forge(sep.ScoreMagnitudeProjection,
                    passive_score_magnitude_text=text, passive_score_magnitude=Decimal("1"))
    with pytest.raises(ClassificationPredicateError) as exc:
        classify_directional_crossing(exposure_orientation=lm.POSITIVE_EXPOSURE,
                                      boundary_magnitude=Decimal("1"), observed_magnitude=forged)
    assert exc.value.reason == PREDICATE_INVALID_DECIMAL_LEXIS


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
        "re",
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


# --- deterministic simultaneous-invalid precedence locks ------------------------------------------

def test_context_precedence_root_before_observed():
    # invalid root + invalid observed -> ROOT reason (root operand revalidated first). Distinct reasons
    # prove which fired: blank-forged root -> INVALID_TEXT; wrong-type observed -> WRONG_CARRIER_TYPE.
    blank_root = _forge(lm.EstablishedRootContext,
                        source_venue_context_text="", source_pair_context_text="BTC")
    with pytest.raises(ClassificationPredicateError) as e_both:
        context_equals(root_context=blank_root, observed_context="not-a-carrier")
    assert e_both.value.reason == PREDICATE_INVALID_TEXT

    # valid root + invalid observed -> OBSERVED reason.
    with pytest.raises(ClassificationPredicateError) as e_obs:
        context_equals(root_context=_root("hl", "BTC"), observed_context="not-a-carrier")
    assert e_obs.value.reason == PREDICATE_WRONG_CARRIER_TYPE


def test_timestamp_precedence_anchor_then_comparison_then_duration():
    # invalid anchor + invalid comparison + invalid duration -> ANCHOR reason.
    with pytest.raises(ClassificationPredicateError) as e_anchor:
        classify_timestamp_window(anchor="x", comparison="not-a-carrier", duration_ms=-1)
    assert e_anchor.value.reason == PREDICATE_INVALID_CANONICAL_TIMESTAMP

    # valid anchor + invalid comparison + invalid duration -> COMPARISON reason.
    with pytest.raises(ClassificationPredicateError) as e_cmp:
        classify_timestamp_window(anchor="0", comparison="not-a-carrier", duration_ms=-1)
    assert e_cmp.value.reason == PREDICATE_WRONG_CARRIER_TYPE

    # valid anchor + valid comparison + invalid duration -> DURATION reason.
    with pytest.raises(ClassificationPredicateError) as e_dur:
        classify_timestamp_window(anchor="0", comparison=_timestamp("0"), duration_ms=-1)
    assert e_dur.value.reason == PREDICATE_INVALID_DURATION


# --- asymmetric-correction AST locks (ratified b874ec0 as corrected by 8fc292e) --------------------

def test_timestamp_anchor_has_no_carrier_branch_static():
    # The scalar anchor flows directly through the single canonical validator: no carrier-type guard,
    # no slot read, no provenance attribute read, and no second _require_carrier on the anchor.
    src = inspect.getsource(cp.classify_timestamp_window)
    assert "_require_carrier(anchor" not in src
    assert "_slot(anchor" not in src
    assert "anchor.provenance_timestamp" not in src
    assert "_require_canonical_timestamp(anchor)" in src
    # the comparison carrier is the ONLY exact-carrier guard in the function.
    assert src.count("_require_carrier(") == 1


def test_timestamp_anchor_no_isinstance_or_type_special_case_on_anchor():
    # Static AST proof: no branch special-cases ScoreTimestampProjection (or any carrier) as a legal anchor.
    tree = ast.parse(inspect.getsource(cp.classify_timestamp_window))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "isinstance":
            for arg in node.args:
                assert not (isinstance(arg, ast.Name) and arg.id == "anchor"), "isinstance(anchor, ...)"
        # no attribute read off the anchor (e.g. anchor.provenance_timestamp).
        if isinstance(node, ast.Attribute):
            assert not (isinstance(node.value, ast.Name) and node.value.id == "anchor"), "anchor.<attr>"
        # no `type(anchor) is <Carrier>` comparison.
        if isinstance(node, ast.Compare):
            left = node.left
            if (isinstance(left, ast.Call) and isinstance(left.func, ast.Name)
                    and left.func.id == "type" and left.args
                    and isinstance(left.args[0], ast.Name) and left.args[0].id == "anchor"):
                raise AssertionError("type(anchor) is <...> branch is forbidden")


# --- closed AST usage whitelist for the root_context carrier (no alias vocabulary) -----------------
#
# Instead of blacklisting attribute/alias shapes, every `Load` of the name `root_context` in a function
# body must be the FIRST positional argument of one exact whitelisted call shape, with NO keywords. Any
# other AST parent shape — Attribute, getattr/vars call, Subscript, Assign, AnnAssign, NamedExpr, container
# capture, Return, Lambda, or forwarding into an unlisted callable — has a non-whitelisted parent and is
# rejected. Alias creation is therefore impossible: the `root_context` Load that would feed an alias is
# itself not whitelisted, so no alias vocabulary is maintained or needed.

def _root_context_use_tags(fn_source, *, legal_shape):
    """Return a tag for every `root_context` Load in ``fn_source`` (each must be the sole/first positional
    arg of a whitelisted call), raising AssertionError on the first non-whitelisted use."""
    import textwrap
    tree = ast.parse(textwrap.dedent(fn_source))
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    tags = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Name) and node.id == "root_context"
                and isinstance(node.ctx, ast.Load)):
            continue
        parent = parents.get(node)
        tag = legal_shape(parent, node) if isinstance(parent, ast.Call) else None
        if tag is None:
            raise AssertionError("non-whitelisted root_context use; parent={}".format(
                type(parent).__name__))
        tags.append(tag)
    return tags


def _legal_context_equals_use(call, name):
    # the ONLY legal use: _require_root_context_scalars(root_context)  (sole positional arg, no keywords).
    if (isinstance(call.func, ast.Name) and call.func.id == "_require_root_context_scalars"
            and len(call.args) == 1 and call.args[0] is name and not call.keywords):
        return "scalars_helper"
    return None


def _legal_helper_use(call, name):
    # legal uses inside _require_root_context_scalars: the carrier guard and the two declared _slot reads,
    # always with root_context as the FIRST positional arg and no keywords.
    if not (isinstance(call.func, ast.Name) and call.args and call.args[0] is name and not call.keywords):
        return None
    if (call.func.id == "_require_carrier" and len(call.args) == 2
            and isinstance(call.args[1], ast.Name) and call.args[1].id == "EstablishedRootContext"):
        return "carrier"
    if (call.func.id == "_slot" and len(call.args) == 2
            and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str)):
        return "slot:" + call.args[1].value
    return None


def test_context_root_uses_are_closed_whitelist_real_runtime():
    # context_equals uses root_context exactly once: forwarded to _require_root_context_scalars.
    ce_tags = _root_context_use_tags(inspect.getsource(cp.context_equals),
                                     legal_shape=_legal_context_equals_use)
    assert ce_tags == ["scalars_helper"], ce_tags
    # _require_root_context_scalars uses root_context exactly thrice: one carrier guard + the two _slot
    # field reads — nothing else, no rebinding, no extra use.
    helper_tags = _root_context_use_tags(inspect.getsource(cp._require_root_context_scalars),
                                         legal_shape=_legal_helper_use)
    assert sorted(helper_tags) == sorted(
        ["carrier", "slot:source_venue_context_text", "slot:source_pair_context_text"]), helper_tags


@pytest.mark.parametrize("body", [
    "    return root_context.source_venue_context_text\n",          # direct attribute access
    "    return getattr(root_context, 'source_venue_context_text')\n",  # getattr access
    "    rc = root_context\n    return rc\n",                        # Assign alias
    "    rc: object = root_context\n    return rc\n",                # AnnAssign alias
    "    return (rc := root_context)\n",                            # NamedExpr (walrus) alias
    "    return [root_context]\n",                                  # container capture
    "    return root_context\n",                                    # bare return forwarding
    "    return _slot(root_context, 'source_venue_context_text', extra)\n",  # wrong arity
    "    return _slot(root_context, field_name)\n",                 # non-constant field
])
def test_root_context_whitelist_rejects_non_whitelisted_shapes(body):
    src = "def f(root_context, field_name=None, extra=None):\n" + body
    with pytest.raises(AssertionError):
        _root_context_use_tags(src, legal_shape=_legal_helper_use)


def test_root_context_whitelist_accepts_only_exact_legal_call_shapes():
    helper_src = (
        "def f(root_context):\n"
        "    _require_carrier(root_context, EstablishedRootContext)\n"
        "    a = _slot(root_context, 'source_venue_context_text')\n"
        "    b = _slot(root_context, 'source_pair_context_text')\n"
        "    return a, b\n"
    )
    assert sorted(_root_context_use_tags(helper_src, legal_shape=_legal_helper_use)) == sorted(
        ["carrier", "slot:source_venue_context_text", "slot:source_pair_context_text"])
    ce_src = "def f(root_context):\n    return _require_root_context_scalars(root_context)\n"
    assert _root_context_use_tags(ce_src, legal_shape=_legal_context_equals_use) == ["scalars_helper"]
    # a keyword-form call is NOT the whitelisted positional shape and is rejected.
    kw_src = "def f(root_context):\n    return _slot(root_context, name='source_venue_context_text')\n"
    with pytest.raises(AssertionError):
        _root_context_use_tags(kw_src, legal_shape=_legal_helper_use)


def test_module_has_no_private_maker_overload_or_synthetic_row():
    text = _module_path().read_text(encoding="utf-8")
    for forbidden in ("_make_score_context", "_make_score_timestamp", "row_factory", "fetchone",
                      "connect(", "@overload", "typing.overload"):
        assert forbidden not in text, forbidden
