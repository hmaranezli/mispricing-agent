"""tests/test_miami_live_snapshot.py — TDD for Miami v3 Sub-slice A pure assembler.

assemble_snapshot_inputs takes INJECTED offline raw inputs (fake CLOB YES book, fake CLOB NO book,
fake reference tick, injected venue metadata) plus operator-supplied market facts, and returns ONLY
the validated calculator INPUT kwargs that compute_decision_row expects. It does NOT build the
48-key decision row, computes no edge/cost, touches no network/CSV.

First RED: module analysis.miami_live_snapshot does not exist -> ImportError.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.miami_live_snapshot import assemble_snapshot_inputs, DEFAULT_ANNUAL_VOLATILITY
from analysis.expiry_snipe_calculator import compute_decision_row

SECONDS_PER_YEAR = 365 * 24 * 3600

# the exact calculator INPUT key set (NOT the 48-key decision row)
_CALC_INPUT_KEYS = {
    "timestamp", "asset", "timeframe", "market_slug_or_label", "expiry",
    "time_to_expiry_seconds", "strike", "spot_reference", "reference_source",
    "reference_staleness_ms", "yes_bid", "yes_ask", "no_bid", "no_ask",
    "yes_available_size", "no_available_size", "intended_stake_usd",
    "volatility_sigma", "tie_resolves_to",
}


def _yes_book():
    return {"bids": [{"price": 0.81, "size": 50}, {"price": 0.80, "size": 10}],
            "asks": [{"price": 0.83, "size": 50}, {"price": 0.84, "size": 20}]}


def _no_book():
    return {"bids": [{"price": 0.17, "size": 150}],
            "asks": [{"price": 0.19, "size": 150}]}


def _ref_trusted():
    return {"price": 65135.0, "source_event_ts": "2026-06-26T17:49:59Z"}


def _ref_degraded():
    return {"price": 65135.0, "client_fetched_at": "2026-06-26T17:49:59.950Z"}  # no venue ts


def _metadata():
    return {"tokens": [{"outcome": "Up", "token_id": "YESTOK"},
                       {"outcome": "Down", "token_id": "NOTOK"}],
            "strike": 65000.0, "expiry": "2026-06-26T18:00:00Z"}


def _call(**over):
    kw = dict(
        asset="BTC", timeframe="1h", market_slug_or_label="BTC-1h-Above-65000-SYN",
        yes_token_id="YESTOK", no_token_id="NOTOK",
        strike=65000.0, expiry="2026-06-26T18:00:00Z",
        intended_stake_usd=10.0, tie_resolves_to="UP",
        captured_at="2026-06-26T17:50:00Z", reference_source="Hyperliquid",
        yes_book=_yes_book(), no_book=_no_book(), reference_tick=_ref_trusted(),
        market_metadata=_metadata(), volatility_annual=None,
    )
    kw.update(over)
    return kw


# ===========================================================================
# 1. Happy path → calculator consumes kwargs cleanly
# ===========================================================================

def test_happy_path_feeds_calculator():
    res = assemble_snapshot_inputs(**_call())
    row = compute_decision_row(res.kwargs, {"fee_cost": 0.01})
    assert "candidate" in row and "yes_adjusted_edge" in row     # calculator produced full row
    assert "basis_risk_accepted_hyperliquid_vs_settlement_oracle" in res.notes_markers


# ===========================================================================
# 2. Output keys are exactly calculator INPUT keys (not 48-key decision row)
# ===========================================================================

def test_output_is_calculator_input_keys_only():
    res = assemble_snapshot_inputs(**_call())
    assert set(res.kwargs.keys()) == _CALC_INPUT_KEYS
    for decision_only in ("candidate", "yes_adjusted_edge", "selected_side_candidate",
                          "is_pin_risk", "trade_allowed"):
        assert decision_only not in res.kwargs


# ===========================================================================
# 3. Top-of-book derivation
# ===========================================================================

def test_top_of_book_derived_correctly():
    res = assemble_snapshot_inputs(**_call())
    k = res.kwargs
    assert k["yes_bid"] == 0.81 and k["yes_ask"] == 0.83 and k["yes_available_size"] == 50
    assert k["no_bid"] == 0.17 and k["no_ask"] == 0.19 and k["no_available_size"] == 150


# ===========================================================================
# 4/5. Volatility default vs override
# ===========================================================================

def test_default_annual_volatility_used():
    res = assemble_snapshot_inputs(**_call(volatility_annual=None))
    assert res.kwargs["volatility_sigma"] == pytest.approx(
        DEFAULT_ANNUAL_VOLATILITY["BTC"] / math.sqrt(SECONDS_PER_YEAR))


def test_operator_volatility_override_wins():
    res = assemble_snapshot_inputs(**_call(volatility_annual=0.60))
    assert res.kwargs["volatility_sigma"] == pytest.approx(0.60 / math.sqrt(SECONDS_PER_YEAR))


# ===========================================================================
# 6. Unknown asset without override → ValueError
# ===========================================================================

def test_unknown_asset_without_override_raises():
    md = _metadata()
    with pytest.raises(ValueError):
        assemble_snapshot_inputs(**_call(asset="DOGE", volatility_annual=None, market_metadata=md))


# ===========================================================================
# 7. Expiry must be UTC Z; ET/local/naive rejected
# ===========================================================================

@pytest.mark.parametrize("bad_expiry", [
    "2026-06-26T14:00:00-04:00",   # offset
    "2026-06-26T18:00:00",          # naive
    "2026-06-26 14:00 ET",          # ET label
    "2026-06-26T18:00:00+00:00",    # explicit offset, not Z
])
def test_non_utc_z_expiry_rejected(bad_expiry):
    md = _metadata()
    md["expiry"] = bad_expiry
    with pytest.raises(ValueError):
        assemble_snapshot_inputs(**_call(expiry=bad_expiry, market_metadata=md))


# ===========================================================================
# 8. time_to_expiry derived; expired/zero → ValueError
# ===========================================================================

def test_expired_market_raises():
    # captured_at after expiry -> ttx <= 0
    with pytest.raises(ValueError):
        assemble_snapshot_inputs(**_call(captured_at="2026-06-26T18:30:00Z"))


def test_time_to_expiry_derived_value():
    res = assemble_snapshot_inputs(**_call())
    assert res.kwargs["time_to_expiry_seconds"] == 600  # 17:50:00 -> 18:00:00


# ===========================================================================
# 9/10. Missing YES / NO side → ValueError
# ===========================================================================

def test_missing_yes_side_raises():
    with pytest.raises(ValueError):
        assemble_snapshot_inputs(**_call(yes_book={"bids": [], "asks": []}))


def test_missing_no_side_raises():
    with pytest.raises(ValueError):
        assemble_snapshot_inputs(**_call(no_book={"bids": [{"price": 0.17, "size": 150}], "asks": []}))


# ===========================================================================
# 11. Crossed / locked book → ValueError
# ===========================================================================

def test_crossed_book_raises():
    crossed = {"bids": [{"price": 0.85, "size": 10}], "asks": [{"price": 0.83, "size": 10}]}
    with pytest.raises(ValueError):
        assemble_snapshot_inputs(**_call(yes_book=crossed))


# ===========================================================================
# 12. Zero/negative bid/ask/size → ValueError
# ===========================================================================

@pytest.mark.parametrize("bad_book", [
    {"bids": [{"price": 0.0, "size": 10}], "asks": [{"price": 0.83, "size": 10}]},
    {"bids": [{"price": 0.81, "size": 10}], "asks": [{"price": -0.1, "size": 10}]},
    {"bids": [{"price": 0.81, "size": 0}], "asks": [{"price": 0.83, "size": 10}]},
    {"bids": [{"price": 0.81, "size": 10}], "asks": [{"price": 0.83, "size": -5}]},
])
def test_zero_or_negative_book_values_raise(bad_book):
    with pytest.raises(ValueError):
        assemble_snapshot_inputs(**_call(yes_book=bad_book))


# ===========================================================================
# 13. Missing trusted reference ts → degraded note, NOT fail-closed
# ===========================================================================

def test_degraded_timestamp_mode_marks_not_fails():
    res = assemble_snapshot_inputs(**_call(reference_tick=_ref_degraded()))
    assert "degraded_ts_override" in res.notes_markers
    assert isinstance(res.kwargs["reference_staleness_ms"], int)
    assert res.kwargs["reference_staleness_ms"] >= 0


def test_trusted_timestamp_no_degraded_marker():
    res = assemble_snapshot_inputs(**_call(reference_tick=_ref_trusted()))
    assert "degraded_ts_override" not in res.notes_markers
    assert res.kwargs["reference_staleness_ms"] == 1000   # 17:50:00 - 17:49:59


# ===========================================================================
# 14/15/16. Cross-check mismatches → ValueError
# ===========================================================================

def test_token_outcome_mismatch_raises():
    md = _metadata()
    md["tokens"] = [{"outcome": "Down", "token_id": "YESTOK"},   # YES token mapped to Down
                    {"outcome": "Up", "token_id": "NOTOK"}]
    with pytest.raises(ValueError):
        assemble_snapshot_inputs(**_call(market_metadata=md))


def test_strike_mismatch_raises():
    md = _metadata()
    md["strike"] = 64000.0   # != operator strike 65000
    with pytest.raises(ValueError):
        assemble_snapshot_inputs(**_call(market_metadata=md))


def test_expiry_metadata_mismatch_raises():
    md = _metadata()
    md["expiry"] = "2026-06-26T19:00:00Z"   # != operator expiry
    with pytest.raises(ValueError):
        assemble_snapshot_inputs(**_call(market_metadata=md))


# ===========================================================================
# 17. Source scan
# ===========================================================================

def test_source_scan_no_forbidden_surfaces():
    import analysis.miami_live_snapshot as m
    src = open(m.__file__, "r", encoding="utf-8").read()
    low = src.lower()
    for banned in ("aiohttp", "requests", "socket", "websocket", "place_order", "submit_order",
                   "wallet", "signing", "hedge", "perp", "scheduler", "cron",
                   "yes_adjusted_edge", "candidate"):
        assert banned not in low, f"forbidden term {banned!r} present"
    import_lines = "\n".join(ln for ln in src.splitlines()
                             if ln.strip().startswith(("import ", "from "))).lower()
    for forbidden in ("aiohttp", "requests", "socket", "execution", "council", "scout",
                      "decision_log_csv", "sqlite", "db."):
        assert forbidden not in import_lines, f"must not import {forbidden!r}"
