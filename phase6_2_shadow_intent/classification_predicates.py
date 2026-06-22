"""phase6_2_shadow_intent/classification_predicates.py — Phase 6.2 Slice D — Classification Predicates.

Pure, deterministic recognition predicates over exact Slice-A logical values (``logical_model``) and Slice-C
narrow projection carriers (``s1_evidence_projection``), built under the ratified Phase 6.2 chain: planning
(`457d279`), predicate (`474cc6f`), precedence/decimal-consistency (`d7204d6`), duplicate-root/context-first
(`f57d116`), and the signed-64 duration amendment (`e471f19`).

Each predicate inspects ONLY its own narrow inputs and is strictly independent: it never invokes another
predicate as a hidden prerequisite, never revalidates an entire Slice-A definition (only the narrow scalar/
carrier it needs), never parses a row, never touches SQLite/filesystem/network, never reads an artifact,
never runs a replay loop, never mutates state or a container, never applies a lifecycle transition, and
never caches or uses global state. **Slice E — not Slice D — owns precedence ordering and state
transitions.** This module makes the classifiers available; it sequences nothing.

Timestamp-window classification uses **exact lexical/digit arithmetic** on canonical non-negative-integer
text — never ``int()`` on S1 timestamp text, never float/Decimal — so arbitrarily long timestamps are exact;
the declared duration is an exact ``int`` within ``[0, 2^63-1]``. Directional crossing uses exact ``Decimal``
comparison; ``INERT_STATE`` has no crossing predicate and never inspects magnitude.

Consumer trust boundary: every public predicate defensively revalidates its exact carrier/type and the
relevant field invariants, rejecting ``object.__new__``-forged, missing-slot, wrong-type, and malformed
inputs through one closed ``ClassificationPredicateError`` reason surface. It never catches
``BaseException``/``KeyboardInterrupt``/``SystemExit``/``GeneratorExit``/``MemoryError``. Capacity stays
deferred at 0 emit sites; production / live / paper / canary / execution / routing / actionability remain
forbidden.
"""
import decimal
import re

from phase6_2_shadow_intent.logical_model import (
    POSITIVE_EXPOSURE,
    NEGATIVE_EXPOSURE,
    INERT_STATE,
    MIN_HYPOTHETICAL_WINDOW_DURATION_MS,
    MAX_HYPOTHETICAL_WINDOW_DURATION_MS,
    OpaqueSilverPairKey,
)
from phase6_2_shadow_intent.s1_evidence_projection import (
    SilverPairProjection,
    ScoreContextProjection,
    ScoreTimestampProjection,
    ScoreUnitProjection,
    ScoreMagnitudeProjection,
)


CLASSIFICATION_PREDICATES_COMPONENT_NAME = "phase6_2_shadow_intent_classification_predicates"

# --- closed timestamp-window classification vocabulary --------------------------------------------
WINDOW_NON_COMPARABLE = "WINDOW_NON_COMPARABLE"   # delta < 0
WINDOW_IN_WINDOW = "WINDOW_IN_WINDOW"             # 0 <= delta <= duration
WINDOW_EXPIRED = "WINDOW_EXPIRED"                 # delta > duration

# --- closed deterministic failure-reason vocabulary -----------------------------------------------
PREDICATE_WRONG_CARRIER_TYPE = "PREDICATE_WRONG_CARRIER_TYPE"
PREDICATE_FORGED_OR_MISSING_SLOT = "PREDICATE_FORGED_OR_MISSING_SLOT"
PREDICATE_INVALID_TEXT = "PREDICATE_INVALID_TEXT"
PREDICATE_INVALID_CANONICAL_TIMESTAMP = "PREDICATE_INVALID_CANONICAL_TIMESTAMP"
PREDICATE_INVALID_DURATION = "PREDICATE_INVALID_DURATION"
PREDICATE_INVALID_DECIMAL = "PREDICATE_INVALID_DECIMAL"
PREDICATE_INVALID_DECIMAL_LEXIS = "PREDICATE_INVALID_DECIMAL_LEXIS"
PREDICATE_MAGNITUDE_TEXT_VALUE_DISAGREEMENT = "PREDICATE_MAGNITUDE_TEXT_VALUE_DISAGREEMENT"
PREDICATE_INVALID_ORIENTATION = "PREDICATE_INVALID_ORIENTATION"
PREDICATE_INERT_HAS_NO_CROSSING = "PREDICATE_INERT_HAS_NO_CROSSING"

_MISSING = object()


class ClassificationPredicateError(ValueError):
    """The single deterministic Slice-D domain failure surface, carrying a closed ``reason`` code."""

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


# --- defensive consumer-boundary helpers ----------------------------------------------------------

def _require_carrier(value, carrier_type):
    if type(value) is not carrier_type:
        raise ClassificationPredicateError(
            PREDICATE_WRONG_CARRIER_TYPE,
            "expected an exact {} carrier".format(carrier_type.__name__))


def _slot(carrier, name):
    """Read a declared slot, normalizing an ``object.__new__``-forged missing slot into the closed reason
    (never a leaked ``AttributeError``)."""
    value = getattr(carrier, name, _MISSING)
    if value is _MISSING:
        raise ClassificationPredicateError(
            PREDICATE_FORGED_OR_MISSING_SLOT,
            "forged or missing slot {!r}".format(name))
    return value


def _require_text(value):
    if type(value) is not str:
        raise ClassificationPredicateError(PREDICATE_INVALID_TEXT, "expected opaque text (str)")
    return value


def _require_finite_decimal(value):
    if type(value) is not decimal.Decimal or not value.is_finite():
        raise ClassificationPredicateError(
            PREDICATE_INVALID_DECIMAL, "expected a finite decimal.Decimal")
    return value


# The EXACT ratified Phase-5 S1 magnitude lexis (`phase5/net_edge_calculator_boundary.py`), replicated
# verbatim and applied via fullmatch. `\d` is Python's Unicode-decimal-digit class (NOT rewritten as
# `[0-9]` and NOT compiled with re.ASCII), so Unicode decimal-digit evidence is accepted exactly as Phase 5
# and `Decimal()` accept it. This is NOT the stricter Gate-B grammar.
_PHASE5_DECIMAL = re.compile(r"-?\d+(\.\d+)?")


def _is_phase5_decimal_text(text):
    """``True`` iff ``text`` is an exact ``str`` matching the ratified Phase-5 lexis. Leading/trailing zeros,
    ``-0``, and Unicode decimal digits are valid; historical text is never normalized/transliterated."""
    return type(text) is str and _PHASE5_DECIMAL.fullmatch(text) is not None


def _require_validated_magnitude(observed_magnitude):
    """Full consumer-boundary revalidation of a populated SCORE-magnitude carrier: exact carrier type, both
    populated slots, Phase-5 lexical text, finite ``Decimal`` value, and ``Decimal(text) == value`` — so an
    ``object.__new__`` populated forgery cannot smuggle a malformed magnitude past the crossing predicate."""
    _require_carrier(observed_magnitude, ScoreMagnitudeProjection)
    text = _slot(observed_magnitude, "passive_score_magnitude_text")
    value = _slot(observed_magnitude, "passive_score_magnitude")
    if not _is_phase5_decimal_text(text):
        raise ClassificationPredicateError(
            PREDICATE_INVALID_DECIMAL_LEXIS, "passive_score_magnitude_text violates the Phase-5 S1 lexis")
    if type(value) is not decimal.Decimal or not value.is_finite():
        raise ClassificationPredicateError(
            PREDICATE_INVALID_DECIMAL, "passive_score_magnitude must be a finite decimal.Decimal")
    try:
        reparsed = decimal.Decimal(text)
    except decimal.InvalidOperation:
        raise ClassificationPredicateError(
            PREDICATE_INVALID_DECIMAL_LEXIS, "passive_score_magnitude_text is not an exact decimal")
    if reparsed != value:
        raise ClassificationPredicateError(
            PREDICATE_MAGNITUDE_TEXT_VALUE_DISAGREEMENT,
            "passive_score_magnitude_text and passive_score_magnitude disagree")
    return value


# --- exact lexical arithmetic on canonical non-negative integer text (no int()) -------------------

def _require_canonical_timestamp(text):
    """A canonical non-negative integer string: ``"0"`` or a non-zero-leading digit run. Validated purely
    lexically — no ``int()`` is ever applied to S1 timestamp text."""
    if type(text) is not str or text == "":
        raise ClassificationPredicateError(
            PREDICATE_INVALID_CANONICAL_TIMESTAMP, "timestamp must be canonical non-negative integer text")
    if text != "0" and text[0] == "0":
        raise ClassificationPredicateError(
            PREDICATE_INVALID_CANONICAL_TIMESTAMP, "canonical integer text has no leading zeros")
    for character in text:
        if character < "0" or character > "9":
            raise ClassificationPredicateError(
                PREDICATE_INVALID_CANONICAL_TIMESTAMP, "timestamp must contain only ASCII digits")
    return text


def _compare_canonical(left, right):
    """Return -1/0/1 comparing two canonical non-negative integer strings (length-then-lexicographic)."""
    if len(left) != len(right):
        return -1 if len(left) < len(right) else 1
    if left == right:
        return 0
    return -1 if left < right else 1


def _add_canonical(left, right):
    """Return the canonical decimal-string sum of two canonical non-negative integer strings (exact digit
    addition; no ``int()``)."""
    digits = []
    carry = 0
    i, j = len(left) - 1, len(right) - 1
    while i >= 0 or j >= 0 or carry:
        total = carry
        if i >= 0:
            total += ord(left[i]) - 48
            i -= 1
        if j >= 0:
            total += ord(right[j]) - 48
            j -= 1
        digits.append(chr(48 + (total % 10)))
        carry = total // 10
    return "".join(reversed(digits))


# --- public predicates (each inspects ONLY its own narrow inputs) ---------------------------------

def silver_pair_intersects(*, manifest_key, observed_silver_pair):
    """Exact opaque Silver-pair intersection: both components compared as verbatim text, byte-exact (no
    decode, normalization, or case-fold). ``manifest_key`` is a Slice-A :class:`OpaqueSilverPairKey`;
    ``observed_silver_pair`` is a Slice-C :class:`SilverPairProjection`."""
    _require_carrier(manifest_key, OpaqueSilverPairKey)
    _require_carrier(observed_silver_pair, SilverPairProjection)
    key_locator = _require_text(_slot(manifest_key, "silver_artifact_locator_text"))
    key_position = _require_text(_slot(manifest_key, "silver_physical_record_position_text"))
    observed_locator = _require_text(_slot(observed_silver_pair, "silver_artifact_locator"))
    observed_position = _require_text(_slot(observed_silver_pair, "silver_physical_record_position"))
    return key_locator == observed_locator and key_position == observed_position


def context_equals(*, root_context, observed_context):
    """Exact two-scalar context equality, byte-exact with no normalization. Both inputs are Slice-C
    :class:`ScoreContextProjection` carriers; compares their ``score_inputs_summary`` element-wise."""
    _require_carrier(root_context, ScoreContextProjection)
    _require_carrier(observed_context, ScoreContextProjection)
    root_summary = _require_context_tuple(_slot(root_context, "score_inputs_summary"))
    observed_summary = _require_context_tuple(_slot(observed_context, "score_inputs_summary"))
    return root_summary[0] == observed_summary[0] and root_summary[1] == observed_summary[1]


def _require_context_tuple(value):
    # exact tuple, arity two, exact str elements, each non-empty and non-whitespace; type checks precede
    # .strip() so a non-str element never leaks an AttributeError. Valid text is preserved verbatim.
    if (type(value) is not tuple or len(value) != 2
            or type(value[0]) is not str or type(value[1]) is not str
            or value[0].strip() == "" or value[1].strip() == ""):
        raise ClassificationPredicateError(
            PREDICATE_INVALID_TEXT,
            "score_inputs_summary must be exactly two non-empty, non-whitespace text scalars")
    return value


def classify_timestamp_window(*, anchor, comparison, duration_ms):
    """Classify a comparison timestamp relative to an anchor and an exact integer window duration:
    ``delta < 0`` -> ``WINDOW_NON_COMPARABLE``; ``0 <= delta <= duration`` -> ``WINDOW_IN_WINDOW``;
    ``delta > duration`` -> ``WINDOW_EXPIRED``. ``anchor`` / ``comparison`` are Slice-C
    :class:`ScoreTimestampProjection` carriers; arithmetic is exact lexical/digit arithmetic (no
    ``int()``/float/Decimal)."""
    _require_carrier(anchor, ScoreTimestampProjection)
    _require_carrier(comparison, ScoreTimestampProjection)
    anchor_text = _require_canonical_timestamp(_slot(anchor, "provenance_timestamp"))
    comparison_text = _require_canonical_timestamp(_slot(comparison, "provenance_timestamp"))
    if type(duration_ms) is not int or type(duration_ms) is bool:
        raise ClassificationPredicateError(
            PREDICATE_INVALID_DURATION, "duration_ms must be an exact int")
    if duration_ms < MIN_HYPOTHETICAL_WINDOW_DURATION_MS or duration_ms > MAX_HYPOTHETICAL_WINDOW_DURATION_MS:
        raise ClassificationPredicateError(
            PREDICATE_INVALID_DURATION, "duration_ms must be within [0, 2^63-1]")

    if _compare_canonical(comparison_text, anchor_text) < 0:
        return WINDOW_NON_COMPARABLE
    window_bound = _add_canonical(anchor_text, str(duration_ms))   # str() of a bounded int, never a timestamp
    if _compare_canonical(comparison_text, window_bound) <= 0:
        return WINDOW_IN_WINDOW
    return WINDOW_EXPIRED


def unit_comparable(*, boundary_unit_context, observed_unit):
    """Exact opaque unit comparability: byte-exact text equality, no normalization/conversion/case-fold.
    ``boundary_unit_context`` is the Slice-A directional unit text; ``observed_unit`` is a Slice-C
    :class:`ScoreUnitProjection`."""
    boundary_text = _require_text(boundary_unit_context)
    _require_carrier(observed_unit, ScoreUnitProjection)
    observed_text = _require_text(_slot(observed_unit, "score_unit_context"))
    return boundary_text == observed_text


def classify_directional_crossing(*, exposure_orientation, boundary_magnitude, observed_magnitude):
    """Directional Decimal crossing: ``POSITIVE_EXPOSURE`` -> evidence >= boundary; ``NEGATIVE_EXPOSURE`` ->
    evidence <= boundary (exact ``Decimal`` comparison). ``INERT_STATE`` has no crossing predicate and is
    rejected BEFORE the magnitude carrier is inspected. ``boundary_magnitude`` is a Slice-A finite
    ``Decimal``; ``observed_magnitude`` is a Slice-C :class:`ScoreMagnitudeProjection`."""
    # exact-type guard FIRST: a str subclass or an equality-impostor must be rejected before any
    # equality/membership comparison, so no foreign __eq__ is ever invoked.
    if type(exposure_orientation) is not str:
        raise ClassificationPredicateError(
            PREDICATE_INVALID_ORIENTATION, "exposure_orientation must be an exact str")
    if exposure_orientation == INERT_STATE:
        raise ClassificationPredicateError(
            PREDICATE_INERT_HAS_NO_CROSSING, "INERT_STATE has no crossing predicate")
    if exposure_orientation != POSITIVE_EXPOSURE and exposure_orientation != NEGATIVE_EXPOSURE:
        raise ClassificationPredicateError(
            PREDICATE_INVALID_ORIENTATION,
            "exposure_orientation must be POSITIVE_EXPOSURE or NEGATIVE_EXPOSURE")
    boundary = _require_finite_decimal(boundary_magnitude)
    evidence = _require_validated_magnitude(observed_magnitude)
    if exposure_orientation == POSITIVE_EXPOSURE:
        return evidence >= boundary
    return evidence <= boundary
