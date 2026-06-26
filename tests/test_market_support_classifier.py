"""tests/test_market_support_classifier.py — TDD for the pure venue-support classifier.

classify_market_support is a pure, deterministic function: given Gamma metadata, a Binance
strike-verification result, asset allowlist / reference-source support, and an EXPLICIT now_ms,
it returns one of four simple string classifications. It reads no clock, touches no disk, makes
no live calls. All inputs are plain dicts/primitives; tests inject them directly.

First RED: module analysis.market_support_classifier does not exist -> ImportError.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.market_support_classifier import (
    classify_market_support,
    CACHE_READY,
    OBSERVE_ONLY,
    MANUAL_ONE_SHOT_ONLY,
    UNSUPPORTED_ASSET,
)

# ---- fixtures (plain dicts; no network, no disk) --------------------------
_EVENT_START = 1782500400000          # 2026-06-26T19:00:00Z in ms
_END = _EVENT_START + 3_600_000       # +1h window close
_NOW_IN_WINDOW = _EVENT_START + 600_000   # 10 min into the open window


def _gamma(**over):
    g = dict(asset="BTC", condition_id="0xCID", yes_token_id="YES", no_token_id="NO",
             outcomes=["Up", "Down"], event_start_time_ms=_EVENT_START, end_date_ms=_END)
    g.update(over)
    return g


def _strike(**over):
    s = dict(status="VENUE_VERIFIED", strike="59668.01", open_time_ms=_EVENT_START)
    s.update(over)
    return s


def _support(**over):
    sp = dict(asset_allowlist=["BTC", "ETH", "SOL", "XRP"], reference_source_supported=True)
    sp.update(over)
    return sp


def _call(**over):
    kw = dict(gamma_meta=_gamma(), strike_result=_strike(), support=_support(),
              now_ms=_NOW_IN_WINDOW)
    kw.update(over)
    return classify_market_support(**kw)


# ===========================================================================
# happy path
# ===========================================================================

def test_all_gates_pass_supported():
    assert _call() == CACHE_READY


# ===========================================================================
# asset gate (broadest)
# ===========================================================================

def test_asset_not_in_allowlist_unsupported():
    assert _call(gamma_meta=_gamma(asset="DOGE")) == UNSUPPORTED_ASSET


def test_reference_source_not_supported_unsupported():
    assert _call(support=_support(reference_source_supported=False)) == UNSUPPORTED_ASSET


def test_missing_allowlist_unsupported():
    assert _call(support={"reference_source_supported": True}) == UNSUPPORTED_ASSET


# ===========================================================================
# time gates: future strike paradox + expiry
# ===========================================================================

def test_future_candle_observe_only():
    assert _call(now_ms=_EVENT_START - 1) == OBSERVE_ONLY


def test_expired_at_end_observe_only():
    assert _call(now_ms=_END) == OBSERVE_ONLY


def test_expired_after_end_observe_only():
    assert _call(now_ms=_END + 1) == OBSERVE_ONLY


# ===========================================================================
# strike validity (manual fallback still possible)
# ===========================================================================

def test_strike_not_venue_verified_manual():
    assert _call(strike_result=_strike(status="STRIKE_UNKNOWN_FUTURE_CANDLE")) == MANUAL_ONE_SHOT_ONLY


def test_strike_missing_manual():
    assert _call(strike_result=_strike(strike=None)) == MANUAL_ONE_SHOT_ONLY


def test_strike_nonnumeric_manual():
    assert _call(strike_result=_strike(strike="not-a-number")) == MANUAL_ONE_SHOT_ONLY


def test_strike_zero_manual():
    assert _call(strike_result=_strike(strike="0")) == MANUAL_ONE_SHOT_ONLY


def test_strike_negative_manual():
    assert _call(strike_result=_strike(strike="-5")) == MANUAL_ONE_SHOT_ONLY


def test_strike_open_time_mismatch_manual():
    assert _call(strike_result=_strike(open_time_ms=_EVENT_START + 1)) == MANUAL_ONE_SHOT_ONLY


def test_strike_missing_open_time_manual():
    assert _call(strike_result=_strike(open_time_ms=None)) == MANUAL_ONE_SHOT_ONLY


# ===========================================================================
# gamma structural validity (manual fallback still possible)
# ===========================================================================

def test_gamma_missing_condition_id_manual():
    assert _call(gamma_meta=_gamma(condition_id="")) == MANUAL_ONE_SHOT_ONLY


def test_gamma_missing_token_manual():
    assert _call(gamma_meta=_gamma(yes_token_id="")) == MANUAL_ONE_SHOT_ONLY


def test_gamma_malformed_outcomes_len_manual():
    assert _call(gamma_meta=_gamma(outcomes=["Up"])) == MANUAL_ONE_SHOT_ONLY


def test_gamma_malformed_outcomes_type_manual():
    assert _call(gamma_meta=_gamma(outcomes="UpDown")) == MANUAL_ONE_SHOT_ONLY


def test_gamma_missing_event_start_manual():
    assert _call(gamma_meta=_gamma(event_start_time_ms=None)) == MANUAL_ONE_SHOT_ONLY


def test_gamma_missing_end_date_manual():
    assert _call(gamma_meta=_gamma(end_date_ms=None)) == MANUAL_ONE_SHOT_ONLY


# ===========================================================================
# precedence (deterministic ordering)
# ===========================================================================

def test_asset_precedes_gamma_validity():
    # bad asset AND bad gamma -> asset gate wins (broadest)
    assert _call(gamma_meta=_gamma(asset="DOGE", condition_id="")) == UNSUPPORTED_ASSET


def test_gamma_validity_precedes_time_gates():
    # missing event_start makes time gates uncomputable -> structural failure wins
    assert _call(gamma_meta=_gamma(event_start_time_ms=None), now_ms=_END + 10) == MANUAL_ONE_SHOT_ONLY


def test_expiry_precedes_strike_validity():
    # expired AND bad strike -> expiry (observe) wins
    assert _call(now_ms=_END + 10, strike_result=_strike(strike=None)) == OBSERVE_ONLY


# ===========================================================================
# determinism + explicit clock contract
# ===========================================================================

def test_deterministic_repeat():
    a = _call()
    b = _call()
    assert a == b == CACHE_READY


def test_now_ms_actually_drives_result():
    # same market record, only now_ms changes -> proves now_ms is consumed, no internal clock
    assert _call(now_ms=_NOW_IN_WINDOW) == CACHE_READY
    assert _call(now_ms=_END + 1) == OBSERVE_ONLY


def test_now_ms_must_be_int():
    with pytest.raises(TypeError):
        _call(now_ms="1782500400000")


# ===========================================================================
# source scan (the success constant no longer contains SCANNER, so the word
# scanner is now forbidden outright, case-insensitively)
# ===========================================================================

def test_source_scan_no_forbidden_surfaces():
    import analysis.market_support_classifier as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        raw = fh.read()
    lower = raw.lower()

    # case-insensitive bans: these must not appear in any casing
    for term in ("scanner", "discover", "pagination", "next_cursor",
                 "aiohttp", "requests", "urllib", "socket", "httpx"):
        assert term not in lower, f"forbidden term {term!r} present in classifier source"

    # case-sensitive bans: precise behavioral surfaces (disk/clock/loop)
    for term in ("open(", "Path(", "json.dump", "json.load",
                 "time.time", "datetime.now", "datetime.utcnow", "while"):
        assert term not in raw, f"forbidden term {term!r} present in classifier source"
