"""RED→GREEN tests for the ratified Post-Phase 6.2 BTC S1 Projection Runtime TDD Charter
(``docs/handoff/post_phase6_2_btc_s1_projection_runtime_tdd_charter.md``) and the DTO / Failure-Surface
Charter literals.

Boundary: pure, stdlib-only, zero-network. Inputs are in-memory fixtures mirroring the ratified raw-ledger
provenance columns (``source_authority`` / ``capture_sequence`` / ``response_body_sha256``) plus the
source-issued payload fields. No HTTP, no localhost, no API client, no scheduler, no live/prod S1 DB, no
raw-ledger mutation. The projection returns a test-only/audit-only carrier; production ingestion stays
BLOCKED.
"""
import decimal

import pytest

from phase6_2_shadow_intent import s1_paired_projection as proj


_OMIT = object()


def _build(base, over):
    row = dict(base)
    for key, value in over.items():
        if value is _OMIT:
            row.pop(key, None)
        else:
            row[key] = value
    return row


def _poly(**over):
    base = dict(
        source_authority="POLYMARKET_CLOB_BOOK_BY_TOKEN_V1",
        polymarket_token_id=proj.RATIFIED_POLYMARKET_TOKEN_ID,
        polymarket_outcome_label="Yes",
        capture_sequence=1,
        response_body_sha256=proj.RATIFIED_POLYMARKET_CAPTURE_SHA256,
        timestamp_source=proj.POLYMARKET_SOURCE_ISSUED_TIMESTAMP,
        polymarket_timestamp_raw_string="1782189645718",
    )
    return _build(base, over)


def _hl(**over):
    base = dict(
        source_authority="HYPERLIQUID_L2_BOOK_BY_COIN_V1",
        hyperliquid_coin="BTC",
        capture_sequence=7,
        response_body_sha256=proj.RATIFIED_HYPERLIQUID_CAPTURE_SHA256,
        time_source=proj.HYPERLIQUID_SOURCE_ISSUED_TIME,
        hyperliquid_time_ms=1782189645000,
        levels_side_axiom=["BID", "ASK"],
        levels=[
            [{"px": "42000.5", "sz": "1.25", "n": 3}, {"px": "41999.0", "sz": "2.0", "n": 5}],
            [{"px": "42001.0", "sz": "0.75", "n": 2}, {"px": "42002.0", "sz": "1.0", "n": 4}],
        ],
    )
    return _build(base, over)


def _project(poly=None, hl=None):
    return proj.project_paired_s1_evidence(
        polymarket_evidence=_poly() if poly is None else poly,
        hyperliquid_evidence=_hl() if hl is None else hl,
    )


def _reason(excinfo):
    return excinfo.value.reason


# --- happy path ----------------------------------------------------------------------------------

def test_valid_pair_projects_carrier():
    result = _project()
    assert isinstance(result, proj.PairedS1Projection)


# --- Section 3: type identity --------------------------------------------------------------------

def test_px_sz_are_decimal_never_float():
    r = _project()
    for value in (
        r.hyperliquid_best_bid_px_decimal, r.hyperliquid_best_bid_sz_decimal,
        r.hyperliquid_best_ask_px_decimal, r.hyperliquid_best_ask_sz_decimal,
    ):
        assert type(value) is decimal.Decimal
        assert not isinstance(value, float)


def test_decimal_values_are_exact_from_source_strings():
    r = _project()
    assert r.hyperliquid_best_bid_px_decimal == decimal.Decimal("42000.5")
    assert r.hyperliquid_best_ask_px_decimal == decimal.Decimal("42001.0")
    assert r.hyperliquid_best_bid_sz_decimal == decimal.Decimal("1.25")


def test_timestamps_are_int():
    r = _project()
    assert type(r.polymarket_timestamp_ms) is int
    assert type(r.hyperliquid_time_ms) is int
    assert type(r.event_time_delta_ms) is int
    assert r.polymarket_timestamp_ms == 1782189645718


def test_order_counts_are_int():
    r = _project()
    assert type(r.hyperliquid_best_bid_order_count) is int
    assert type(r.hyperliquid_best_ask_order_count) is int
    assert r.hyperliquid_best_bid_order_count == 3
    assert r.hyperliquid_best_ask_order_count == 2


def test_float_px_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(levels=[
            [{"px": 42000.5, "sz": "1.25", "n": 3}, {"px": "41999.0", "sz": "2.0", "n": 5}],
            [{"px": "42001.0", "sz": "0.75", "n": 2}, {"px": "42002.0", "sz": "1.0", "n": 4}]]))
    assert _reason(e) == "S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED"


def test_scientific_notation_sz_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(levels=[
            [{"px": "42000.5", "sz": "1e5", "n": 3}, {"px": "41999.0", "sz": "2.0", "n": 5}],
            [{"px": "42001.0", "sz": "0.75", "n": 2}, {"px": "42002.0", "sz": "1.0", "n": 4}]]))
    assert _reason(e) == "S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED"


def test_signed_px_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(levels=[
            [{"px": "-42000.5", "sz": "1.25", "n": 3}, {"px": "41999.0", "sz": "2.0", "n": 5}],
            [{"px": "42001.0", "sz": "0.75", "n": 2}, {"px": "42002.0", "sz": "1.0", "n": 4}]]))
    assert _reason(e) == "S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED"


def test_malformed_polymarket_timestamp_string_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(poly=_poly(polymarket_timestamp_raw_string="1782189645.718"))
    assert _reason(e) == "S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED"


def test_exponent_polymarket_timestamp_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(poly=_poly(polymarket_timestamp_raw_string="1.78e12"))
    assert _reason(e) == "S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED"


def test_whitespace_polymarket_timestamp_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(poly=_poly(polymarket_timestamp_raw_string=" 1782189645718 "))
    assert _reason(e) == "S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED"


# --- Section 4: time boundary matrix (absolute delta) --------------------------------------------

def test_delta_999_accepted():
    r = _project(hl=_hl(hyperliquid_time_ms=1782189645718 - 999))
    assert r.event_time_delta_ms == 999


def test_delta_1000_accepted():
    r = _project(hl=_hl(hyperliquid_time_ms=1782189645718 - 1000))
    assert r.event_time_delta_ms == 1000


def test_delta_1001_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(hyperliquid_time_ms=1782189645718 - 1001))
    assert _reason(e) == "S1_TIME_DELTA_EXCEEDS_1000_MS"


def test_delta_is_absolute_polymarket_ahead():
    r = _project(hl=_hl(hyperliquid_time_ms=1782189645718 - 500))
    assert r.event_time_delta_ms == 500


def test_delta_is_absolute_hyperliquid_ahead():
    r = _project(hl=_hl(hyperliquid_time_ms=1782189645718 + 500))
    assert r.event_time_delta_ms == 500


def test_missing_polymarket_timestamp():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(poly=_poly(polymarket_timestamp_raw_string=_OMIT))
    assert _reason(e) == "S1_POLYMARKET_TIMESTAMP_MISSING"


def test_missing_hyperliquid_time():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(hyperliquid_time_ms=_OMIT))
    assert _reason(e) == "S1_HYPERLIQUID_TIME_MISSING"


def test_retrieval_time_substitution_polymarket_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(poly=_poly(timestamp_source="RETRIEVAL_COMPLETED_EPOCH_MS"))
    assert _reason(e) == "S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED"


def test_retrieval_time_substitution_hyperliquid_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(time_source="RETRIEVAL_COMPLETED_EPOCH_MS"))
    assert _reason(e) == "S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED"


def test_negative_polymarket_timestamp_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(poly=_poly(polymarket_timestamp_raw_string="-1782189645718"))
    assert _reason(e) == "S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED"


def test_negative_hyperliquid_time_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(hyperliquid_time_ms=-1782189645000))
    assert _reason(e) == "S1_HYPERLIQUID_TIME_REJECTED"


def test_non_int_hyperliquid_time_rejected():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(hyperliquid_time_ms="1782189645000"))
    assert _reason(e) == "S1_HYPERLIQUID_TIME_REJECTED"


# --- Section 5: provenance linkage / no orphan rows ----------------------------------------------

def test_projection_carries_polymarket_provenance():
    r = _project()
    assert r.polymarket_capture_sequence == 1
    assert r.polymarket_response_body_sha256 == proj.RATIFIED_POLYMARKET_CAPTURE_SHA256
    assert r.polymarket_source_authority == "POLYMARKET_CLOB_BOOK_BY_TOKEN_V1"


def test_projection_carries_hyperliquid_provenance():
    r = _project()
    assert r.hyperliquid_capture_sequence == 7
    assert r.hyperliquid_response_body_sha256 == proj.RATIFIED_HYPERLIQUID_CAPTURE_SHA256
    assert r.hyperliquid_source_authority == "HYPERLIQUID_L2_BOOK_BY_COIN_V1"


def test_missing_polymarket_capture_sequence_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(poly=_poly(capture_sequence=_OMIT))
    assert _reason(e) == "S1_PAIR_POLYMARKET_EVIDENCE_MISSING"


def test_missing_hyperliquid_sha_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(response_body_sha256=_OMIT))
    assert _reason(e) == "S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING"


def test_polymarket_sha_mismatch_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(poly=_poly(response_body_sha256="0" * 64))
    assert _reason(e) == "S1_PROVENANCE_SHA_MISMATCH"


def test_hyperliquid_sha_mismatch_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(response_body_sha256="f" * 64))
    assert _reason(e) == "S1_PROVENANCE_SHA_MISMATCH"


# --- Section 6: paired-state guards --------------------------------------------------------------

def test_missing_polymarket_evidence_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        proj.project_paired_s1_evidence(polymarket_evidence=None, hyperliquid_evidence=_hl())
    assert _reason(e) == "S1_PAIR_POLYMARKET_EVIDENCE_MISSING"


def test_missing_hyperliquid_evidence_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        proj.project_paired_s1_evidence(polymarket_evidence=_poly(), hyperliquid_evidence=None)
    assert _reason(e) == "S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING"


def test_wrong_polymarket_token_id_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(poly=_poly(polymarket_token_id="999"))
    assert _reason(e) == "S1_PAIR_POLYMARKET_EVIDENCE_MISSING"


def test_wrong_hyperliquid_coin_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(hyperliquid_coin="ETH"))
    assert _reason(e) == "S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING"


def test_wrong_polymarket_source_authority_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(poly=_poly(source_authority="POLYMARKET_GAMMA_MARKET_BY_SLUG_V1"))
    assert _reason(e) == "S1_PAIR_POLYMARKET_EVIDENCE_MISSING"


def test_wrong_hyperliquid_source_authority_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(source_authority="HYPERLIQUID_META_AND_ASSET_CTXS_V1"))
    assert _reason(e) == "S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING"


# --- Section 7: top-of-book / side axiom ---------------------------------------------------------

def test_top_of_book_only_uses_level_index_zero():
    r = _project()
    # bid top-of-book = levels[0][0]; ask top-of-book = levels[1][0]; deeper levels never surface.
    assert r.hyperliquid_best_bid_px_decimal == decimal.Decimal("42000.5")
    assert r.hyperliquid_best_ask_px_decimal == decimal.Decimal("42001.0")


def test_deeper_levels_not_projected():
    r = _project()
    field_values = [getattr(r, name) for name in r.__dataclass_fields__]
    assert decimal.Decimal("41999.0") not in field_values   # levels[0][1] bid depth
    assert decimal.Decimal("42002.0") not in field_values   # levels[1][1] ask depth


def test_no_depth_or_derived_fields_present():
    forbidden = {"depth", "sum", "vwap", "mid", "spread", "notional", "cross_edge", "total"}
    for name in proj.PairedS1Projection.__dataclass_fields__:
        assert not any(token in name for token in forbidden)


def test_missing_top_of_book_bid_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(levels=[[], [{"px": "42001.0", "sz": "0.75", "n": 2}]]))
    assert _reason(e) == "S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED"


def test_malformed_levels_length_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(levels=[[{"px": "42000.5", "sz": "1.25", "n": 3}]]))
    assert _reason(e) == "S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED"


def test_n_type_divergence_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(levels=[
            [{"px": "42000.5", "sz": "1.25", "n": "3"}, {"px": "41999.0", "sz": "2.0", "n": 5}],
            [{"px": "42001.0", "sz": "0.75", "n": 2}, {"px": "42002.0", "sz": "1.0", "n": 4}]]))
    assert _reason(e) == "S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED"


def test_side_axiom_violation_fails_closed():
    with pytest.raises(proj.S1PairedProjectionError) as e:
        _project(hl=_hl(levels_side_axiom=["ASK", "BID"]))
    assert _reason(e) == "S1_HYPERLIQUID_SIDE_AXIOM_REJECTED"


# --- direct construction is forbidden (factory-only carrier) -------------------------------------

def test_direct_construction_forbidden():
    with pytest.raises(proj.S1PairedProjectionError):
        proj.PairedS1Projection()
