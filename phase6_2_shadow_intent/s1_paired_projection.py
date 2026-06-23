"""phase6_2_shadow_intent/s1_paired_projection.py — Phase 6.2 — BTC S1 Paired Projection.

Minimal, pure, stdlib-only **dependency leaf** implementing the ratified Post-Phase 6.2 BTC S1 Projection
Runtime TDD Charter (``docs/handoff/post_phase6_2_btc_s1_projection_runtime_tdd_charter.md``) and the
DTO / Failure-Surface Charter (``docs/handoff/post_phase6_2_btc_s1_projection_dto_failure_surface_charter.md``).

It projects a **paired** cross-source observation — the ratified BTC Polymarket CLOB **YES**-token book and
the ratified BTC Hyperliquid l2Book — into a single frozen, slotted, kw-only, factory-only audit-only
carrier, **fail-closed** at every divergence.

Boundary (binding): no network / localhost / API client / scheduler / filesystem / live-or-prod S1 DB /
raw-ledger mutation. Inputs are already-captured raw-evidence carriers (mappings mirroring the ratified raw
ledger provenance columns plus the source-issued payload fields). Numeric laws: Polymarket ``$.timestamp``
parses from an exact integer string ``^[0-9]+$`` to ``int`` epoch-ms; Hyperliquid ``$.time`` is an ``int``
epoch-ms; ``px`` / ``sz`` parse with precision-preserving ``decimal.Decimal`` only — never ``float`` and
never ``Decimal`` from ``float``. Top-of-book only: ``levels[0][0]`` = BID, ``levels[1][0]`` = ASK under the
ratified manual side axiom; deeper levels are discarded; no depth / sum / VWAP / mid / spread / notional /
cross-edge field is produced. Eligible only when ``abs(polymarket_timestamp_ms - hyperliquid_time_ms) <=
1000``. Retrieval timestamps never substitute for source-issued event time. One deterministic failure
surface, ``S1PairedProjectionError`` with a closed ratified ``reason`` literal. Production S1 ingestion
stays BLOCKED; this carrier is test-only / audit-only.
"""
import decimal
import re
from dataclasses import dataclass


S1_PAIRED_PROJECTION_COMPONENT_NAME = "phase6_2_shadow_intent_s1_paired_projection"

# --- ratified identity / provenance constants (BTC paired evidence chain) -------------------------
RATIFIED_POLYMARKET_SOURCE_AUTHORITY = "POLYMARKET_CLOB_BOOK_BY_TOKEN_V1"
RATIFIED_POLYMARKET_TOKEN_ID = (
    "13433573766910980267981622064090484781359464703732825845886677588040916221533")
RATIFIED_POLYMARKET_CAPTURE_SHA256 = (
    "3b9b74e23a9dc796a6e1d9baa7994531550f74b3a6c70353b95690d4d9b25940")
RATIFIED_HYPERLIQUID_SOURCE_AUTHORITY = "HYPERLIQUID_L2_BOOK_BY_COIN_V1"
RATIFIED_HYPERLIQUID_COIN = "BTC"
RATIFIED_HYPERLIQUID_CAPTURE_SHA256 = (
    "a0093a5be765dabb3df9df2f7716046c2bcf54efe65d3ba4e4c9c3f4b17d752d")

# --- anti-substitution sentinels (source-issued event time only) ----------------------------------
POLYMARKET_SOURCE_ISSUED_TIMESTAMP = "POLYMARKET_CLOB_SOURCE_ISSUED_TIMESTAMP"
HYPERLIQUID_SOURCE_ISSUED_TIME = "HYPERLIQUID_L2BOOK_SOURCE_ISSUED_TIME"

# --- ratified manual side axiom -------------------------------------------------------------------
RATIFIED_SIDE_AXIOM = ("BID", "ASK")

# --- ratified alignment bound ---------------------------------------------------------------------
MAX_CROSS_SOURCE_EVENT_TIME_DELTA_MS = 1000

# Exact integer-string timestamp lexis (no sign / point / exponent / whitespace / empty).
_INTEGER_STRING = re.compile(r"\A[0-9]+\Z")
# Non-negative exact decimal lexis for px/sz (no sign / exponent / whitespace / empty).
_DECIMAL_STRING = re.compile(r"\A[0-9]+(?:\.[0-9]+)?\Z")
_SHA256_HEX = re.compile(r"\A[0-9a-f]{64}\Z")


# --- closed deterministic failure-reason vocabulary (ratified DTO / failure-surface literals) -----
S1_PAIR_POLYMARKET_EVIDENCE_MISSING = "S1_PAIR_POLYMARKET_EVIDENCE_MISSING"
S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING = "S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING"
S1_POLYMARKET_TIMESTAMP_MISSING = "S1_POLYMARKET_TIMESTAMP_MISSING"
S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED = "S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED"
S1_HYPERLIQUID_TIME_MISSING = "S1_HYPERLIQUID_TIME_MISSING"
S1_HYPERLIQUID_TIME_REJECTED = "S1_HYPERLIQUID_TIME_REJECTED"
S1_TIME_DELTA_EXCEEDS_1000_MS = "S1_TIME_DELTA_EXCEEDS_1000_MS"
S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED = "S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED"
S1_HYPERLIQUID_SIDE_AXIOM_REJECTED = "S1_HYPERLIQUID_SIDE_AXIOM_REJECTED"
S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED = "S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED"
S1_PROVENANCE_SHA_MISMATCH = "S1_PROVENANCE_SHA_MISMATCH"
S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED = "S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED"

_ABSENT = object()


class S1PairedProjectionError(ValueError):
    """The single deterministic paired-projection failure surface, carrying a closed ``reason`` literal."""

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


def _forbid_direct_construction(self, *args, **kwargs):
    raise S1PairedProjectionError(
        "S1_PAIR_DIRECT_CONSTRUCTION",
        f"{type(self).__name__} is factory-only; use project_paired_s1_evidence")


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class PairedS1Projection:
    """Audit-only paired projection carrier. Pure data; factory-only; production ingestion BLOCKED."""

    polymarket_source_authority: str
    polymarket_token_id: str
    polymarket_outcome_label: str
    polymarket_timestamp_ms: int
    polymarket_timestamp_raw_string: str
    polymarket_capture_sequence: int
    polymarket_response_body_sha256: str

    hyperliquid_source_authority: str
    hyperliquid_coin: str
    hyperliquid_time_ms: int
    hyperliquid_best_bid_px_decimal: decimal.Decimal
    hyperliquid_best_bid_sz_decimal: decimal.Decimal
    hyperliquid_best_bid_order_count: int
    hyperliquid_best_ask_px_decimal: decimal.Decimal
    hyperliquid_best_ask_sz_decimal: decimal.Decimal
    hyperliquid_best_ask_order_count: int
    hyperliquid_capture_sequence: int
    hyperliquid_response_body_sha256: str

    event_time_delta_ms: int

    __init__ = _forbid_direct_construction


def _seal(cls, **field_values):
    instance = object.__new__(cls)
    for name in cls.__dataclass_fields__:
        object.__setattr__(instance, name, field_values[name])
    return instance


def _is_int(value):
    return type(value) is int  # rejects bool (subclass) and every non-int


def _get(evidence, key):
    if key in evidence:
        return evidence[key]
    return _ABSENT


def _parse_decimal(value):
    """Exact, precision-preserving Decimal from an exact non-negative decimal string. Never from float."""
    if type(value) is not str or _DECIMAL_STRING.match(value) is None:
        raise S1PairedProjectionError(
            S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED, "px/sz must be an exact non-negative decimal string")
    try:
        return decimal.Decimal(value)
    except decimal.InvalidOperation:
        raise S1PairedProjectionError(
            S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED, "px/sz is not an exact decimal")


def _top_of_book_level(levels, side_index):
    side = levels[side_index]
    if type(side) is not list or len(side) == 0:
        raise S1PairedProjectionError(
            S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED, "side array missing top-of-book level")
    entry = side[0]
    if type(entry) is not dict:
        raise S1PairedProjectionError(
            S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED, "top-of-book level is not an object")
    px = _get(entry, "px")
    sz = _get(entry, "sz")
    n = _get(entry, "n")
    if px is _ABSENT or sz is _ABSENT or n is _ABSENT:
        raise S1PairedProjectionError(
            S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED, "top-of-book level missing px/sz/n")
    if not _is_int(n):
        raise S1PairedProjectionError(
            S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED, "order count n must be an int")
    return _parse_decimal(px), _parse_decimal(sz), n


def project_paired_s1_evidence(*, polymarket_evidence, hyperliquid_evidence):
    """Project a ratified BTC paired CLOB-YES + l2Book observation into an audit-only carrier, fail-closed.

    Returns a ``PairedS1Projection`` only when both sides match the ratified identity / provenance, carry
    source-issued (never retrieval) event times, satisfy the decimal / integer-string / side-axiom /
    top-of-book laws, and align within ``<= 1000 ms``. Otherwise raises ``S1PairedProjectionError`` with a
    closed ratified reason literal.
    """
    # --- Section 6: paired presence + identity + provenance well-formedness -----------------------
    if type(polymarket_evidence) is not dict:
        raise S1PairedProjectionError(
            S1_PAIR_POLYMARKET_EVIDENCE_MISSING, "Polymarket CLOB YES evidence is absent")
    if type(hyperliquid_evidence) is not dict:
        raise S1PairedProjectionError(
            S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING, "Hyperliquid l2Book evidence is absent")

    p_authority = _get(polymarket_evidence, "source_authority")
    p_token = _get(polymarket_evidence, "polymarket_token_id")
    p_label = _get(polymarket_evidence, "polymarket_outcome_label")
    p_seq = _get(polymarket_evidence, "capture_sequence")
    p_sha = _get(polymarket_evidence, "response_body_sha256")
    if (p_authority != RATIFIED_POLYMARKET_SOURCE_AUTHORITY
            or p_token != RATIFIED_POLYMARKET_TOKEN_ID
            or type(p_label) is not str
            or not _is_int(p_seq)
            or type(p_sha) is not str or _SHA256_HEX.match(p_sha) is None):
        raise S1PairedProjectionError(
            S1_PAIR_POLYMARKET_EVIDENCE_MISSING,
            "Polymarket evidence does not match the ratified CLOB YES identity/provenance")

    h_authority = _get(hyperliquid_evidence, "source_authority")
    h_coin = _get(hyperliquid_evidence, "hyperliquid_coin")
    h_seq = _get(hyperliquid_evidence, "capture_sequence")
    h_sha = _get(hyperliquid_evidence, "response_body_sha256")
    if (h_authority != RATIFIED_HYPERLIQUID_SOURCE_AUTHORITY
            or h_coin != RATIFIED_HYPERLIQUID_COIN
            or not _is_int(h_seq)
            or type(h_sha) is not str or _SHA256_HEX.match(h_sha) is None):
        raise S1PairedProjectionError(
            S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING,
            "Hyperliquid evidence does not match the ratified l2Book identity/provenance")

    # --- Section 5: provenance SHA must bind to the ratified captures -----------------------------
    if p_sha != RATIFIED_POLYMARKET_CAPTURE_SHA256:
        raise S1PairedProjectionError(
            S1_PROVENANCE_SHA_MISMATCH, "Polymarket response_body_sha256 is not the ratified capture")
    if h_sha != RATIFIED_HYPERLIQUID_CAPTURE_SHA256:
        raise S1PairedProjectionError(
            S1_PROVENANCE_SHA_MISMATCH, "Hyperliquid response_body_sha256 is not the ratified capture")

    # --- Section 3/4: anti-substitution + source-issued event times ------------------------------
    if _get(polymarket_evidence, "timestamp_source") != POLYMARKET_SOURCE_ISSUED_TIMESTAMP:
        raise S1PairedProjectionError(
            S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED,
            "Polymarket event time must be the source-issued CLOB timestamp")
    if _get(hyperliquid_evidence, "time_source") != HYPERLIQUID_SOURCE_ISSUED_TIME:
        raise S1PairedProjectionError(
            S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED,
            "Hyperliquid event time must be the source-issued l2Book $.time")

    p_ts_raw = _get(polymarket_evidence, "polymarket_timestamp_raw_string")
    if p_ts_raw is _ABSENT:
        raise S1PairedProjectionError(
            S1_POLYMARKET_TIMESTAMP_MISSING, "Polymarket timestamp is absent")
    if type(p_ts_raw) is not str or _INTEGER_STRING.match(p_ts_raw) is None:
        raise S1PairedProjectionError(
            S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED,
            "Polymarket timestamp must be an exact integer string ^[0-9]+$")
    polymarket_timestamp_ms = int(p_ts_raw)

    h_time = _get(hyperliquid_evidence, "hyperliquid_time_ms")
    if h_time is _ABSENT:
        raise S1PairedProjectionError(
            S1_HYPERLIQUID_TIME_MISSING, "Hyperliquid $.time is absent")
    if not _is_int(h_time) or h_time < 0:
        raise S1PairedProjectionError(
            S1_HYPERLIQUID_TIME_REJECTED, "Hyperliquid $.time must be a non-negative int")

    # --- Section 7: top-of-book / side axiom ------------------------------------------------------
    levels = _get(hyperliquid_evidence, "levels")
    side_axiom = _get(hyperliquid_evidence, "levels_side_axiom")
    if side_axiom is _ABSENT or tuple(side_axiom) != RATIFIED_SIDE_AXIOM:
        raise S1PairedProjectionError(
            S1_HYPERLIQUID_SIDE_AXIOM_REJECTED, "side axiom must be exactly (BID, ASK)")
    if type(levels) is not list or len(levels) != 2:
        raise S1PairedProjectionError(
            S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED, "levels must be exactly two side arrays")
    bid_px, bid_sz, bid_n = _top_of_book_level(levels, 0)
    ask_px, ask_sz, ask_n = _top_of_book_level(levels, 1)

    # --- Section 4: absolute cross-source delta ---------------------------------------------------
    event_time_delta_ms = abs(polymarket_timestamp_ms - h_time)
    if event_time_delta_ms > MAX_CROSS_SOURCE_EVENT_TIME_DELTA_MS:
        raise S1PairedProjectionError(
            S1_TIME_DELTA_EXCEEDS_1000_MS, "paired event-time delta exceeds 1000 ms")

    return _seal(
        PairedS1Projection,
        polymarket_source_authority=p_authority,
        polymarket_token_id=p_token,
        polymarket_outcome_label=p_label,
        polymarket_timestamp_ms=polymarket_timestamp_ms,
        polymarket_timestamp_raw_string=p_ts_raw,
        polymarket_capture_sequence=p_seq,
        polymarket_response_body_sha256=p_sha,
        hyperliquid_source_authority=h_authority,
        hyperliquid_coin=h_coin,
        hyperliquid_time_ms=h_time,
        hyperliquid_best_bid_px_decimal=bid_px,
        hyperliquid_best_bid_sz_decimal=bid_sz,
        hyperliquid_best_bid_order_count=bid_n,
        hyperliquid_best_ask_px_decimal=ask_px,
        hyperliquid_best_ask_sz_decimal=ask_sz,
        hyperliquid_best_ask_order_count=ask_n,
        hyperliquid_capture_sequence=h_seq,
        hyperliquid_response_body_sha256=h_sha,
        event_time_delta_ms=event_time_delta_ms,
    )
