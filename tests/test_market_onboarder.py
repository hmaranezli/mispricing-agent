"""tests/test_market_onboarder.py — TDD for the N=1 onboarder orchestration.

onboard_market wires the three merged building blocks (Gamma metadata courier, Binance candle-open
oracle courier, and the pure support classifier) into one verified onboarding record. It calls the
REAL courier functions with injected fake clients and the REAL classifier. Short-circuits fail-closed:
Gamma-invalid skips Binance+classifier; Binance-invalid skips classifier. The Binance carrier's
Echo-vs-None semantics are preserved verbatim.

First RED: module tools.market_onboarder does not exist -> ImportError.
"""
import asyncio
import json
import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.market_onboarder import onboard_market

_CID = "0x1260dda542bb5fb18a6e4ffb74468d3983dbb0ceb7faa09cf2285e1fc53d3020"
_SLUG = "bitcoin-up-or-down-june-26-2026-3pm-et"
_ASSET = "BTC"
_INTERVAL = "1h"
_EVENT_MS = 1782500400000
_END_MS = 1782504000000
_GAMMA_BASE = "https://gamma.example.com"
_BINANCE_BASE = "https://binance.example.com"
_SYMBOL_MAP = {"BTC": "BTCUSDT"}
_ALLOW = ["BTC", "ETH", "SOL", "XRP"]
_NOW_IN_WINDOW = _EVENT_MS + 600_000


def _gamma_doc(**over):
    d = {
        "conditionId": _CID,
        "outcomes": json.dumps(["Up", "Down"]),
        "clobTokenIds": json.dumps(["YESTOK", "NOTOK"]),
        "eventStartTime": "2026-06-26T19:00:00Z",
        "endDate": "2026-06-26T20:00:00Z",
        "question": "Bitcoin Up or Down - June 26, 3PM ET",
        "slug": _SLUG,
        "description": "BTC/USDT 1H candle open price ...",
        "resolutionSource": "https://www.binance.com/en/trade/BTC_USDT",
        "tags": ["crypto"],
    }
    d.update(over)
    return d


def _kline(open_time=_EVENT_MS, open_price="59668.01"):
    return [open_time, open_price, "60000.0", "59000.0", "59800.0", "1.0",
            open_time + 3_599_999]


def _gamma_client(payload, *, counter=None):
    async def _c(url):
        if counter is not None:
            counter.append(url)
        return payload
    return _c


def _binance_client(payload, *, counter=None, raise_exc=None):
    async def _c(url):
        if counter is not None:
            counter.append(url)
        if raise_exc is not None:
            raise raise_exc
        return payload
    return _c


def _onboard(*, gamma_payload="DEF", binance_payload="DEF", now_ms=_NOW_IN_WINDOW,
             gamma_counter=None, binance_counter=None, binance_raise=None,
             asset=_ASSET, allowlist=_ALLOW, ref=True, expected_condition_id=None):
    gp = [_gamma_doc()] if gamma_payload == "DEF" else gamma_payload
    bp = [_kline()] if binance_payload == "DEF" else binance_payload
    gc = _gamma_client(gp, counter=gamma_counter)
    bc = _binance_client(bp, counter=binance_counter, raise_exc=binance_raise)
    return asyncio.run(onboard_market(
        slug=_SLUG, asset=asset, interval=_INTERVAL, now_ms=now_ms,
        gamma_client=gc, binance_client=bc,
        gamma_base_url=_GAMMA_BASE, binance_base_url=_BINANCE_BASE,
        asset_allowlist=allowlist, reference_source_supported=ref,
        asset_symbol_map=_SYMBOL_MAP, expected_condition_id=expected_condition_id))


# ===========================================================================
# happy path
# ===========================================================================

def test_happy_onboarding_ok():
    gc, bc = [], []
    r = _onboard(gamma_counter=gc, binance_counter=bc)
    assert r["onboarding_status"] == "ONBOARDING_OK"
    assert r["onboarding_error_code"] is None
    assert r["classification"] == {"status": "CACHE_READY"}
    assert r["slug"] == _SLUG
    assert r["condition_id"] == _CID
    assert r["asset"] == _ASSET
    assert r["interval"] == _INTERVAL
    assert r["gamma"]["status"] == "VENUE_METADATA_OK"
    assert r["binance"]["status"] == "VENUE_STRIKE_OK"
    assert r["binance"]["strike_price"] == Decimal("59668.01")
    # adapter proof: CACHE_READY only arises if VENUE_STRIKE_OK -> VENUE_VERIFIED worked
    assert len(gc) == 1 and len(bc) == 1


# ===========================================================================
# gamma invalid -> short-circuit (no binance, no classifier)
# ===========================================================================

def test_gamma_invalid_short_circuits():
    bc = []
    r = _onboard(gamma_payload=[], binance_counter=bc)   # empty -> gamma_empty
    assert r["onboarding_status"] == "ONBOARDING_INVALID"
    assert r["onboarding_error_code"] == "gamma_empty"
    assert r["binance"] is None
    assert r["classification"] is None
    assert r["condition_id"] is None
    assert len(bc) == 0


def test_expected_condition_id_mismatch_short_circuits():
    bc = []
    r = _onboard(expected_condition_id="0xDEAD", binance_counter=bc)
    assert r["onboarding_error_code"] == "gamma_condition_id_mismatch"
    assert r["binance"] is None
    assert r["classification"] is None
    assert len(bc) == 0


# ===========================================================================
# binance invalid -> short-circuit (no classifier), echo-vs-none preserved
# ===========================================================================

def test_binance_invalid_short_circuits_echo_preserved():
    r = _onboard(binance_payload=[_kline(open_price="0")])   # bad price
    assert r["onboarding_status"] == "ONBOARDING_INVALID"
    assert r["onboarding_error_code"] == "binance_bad_price"
    assert r["classification"] is None
    b = r["binance"]
    assert b["status"] == "VENUE_STRIKE_INVALID"
    assert b["symbol"] == "BTCUSDT"
    assert b["interval"] == _INTERVAL
    assert b["event_start_time_ms"] == _EVENT_MS
    assert b["returned_open_time_ms"] is None
    assert b["strike_price"] is None
    assert b["strike_source"] is None


def test_binance_future_candle_short_circuits():
    r = _onboard(now_ms=_EVENT_MS - 1)
    assert r["onboarding_status"] == "ONBOARDING_INVALID"
    assert r["onboarding_error_code"] == "binance_future_candle"
    assert r["classification"] is None


def test_binance_exception_is_fetch_error():
    r = _onboard(binance_raise=TimeoutError("boom"))
    assert r["onboarding_error_code"] == "binance_fetch_error"
    assert r["classification"] is None


# ===========================================================================
# classifier non-OK -> ONBOARDING_INVALID with classifier_* (status preserved)
# ===========================================================================

def test_classifier_observe_only_expired():
    r = _onboard(now_ms=_END_MS)   # candle is past (binance OK) but market expired
    assert r["binance"]["status"] == "VENUE_STRIKE_OK"
    assert r["classification"] == {"status": "OBSERVE_ONLY"}
    assert r["onboarding_status"] == "ONBOARDING_INVALID"
    assert r["onboarding_error_code"] == "classifier_observe_only"


def test_classifier_unsupported_asset_off_allowlist():
    r = _onboard(allowlist=["ETH"])
    assert r["classification"] == {"status": "UNSUPPORTED_ASSET"}
    assert r["onboarding_error_code"] == "classifier_unsupported_asset"


def test_classifier_unsupported_asset_no_reference():
    r = _onboard(ref=False)
    assert r["classification"] == {"status": "UNSUPPORTED_ASSET"}
    assert r["onboarding_error_code"] == "classifier_unsupported_asset"


# ===========================================================================
# source scan: lowercase 'cache' banned; uppercase CACHE_READY allowed
# ===========================================================================

def test_source_scan_no_forbidden_surfaces():
    import tools.market_onboarder as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        raw = fh.read()
    # case-sensitive: behavioral lowercase 'cache' forbidden (CACHE_READY uppercase is allowed)
    assert "cache" not in raw, "lowercase 'cache' present in onboarder source"
    low = raw.lower()
    for term in ("scanner", "runner", "while", "retry", "pagination", "next_cursor", "discover",
                 "trade", "signal", "edge", "candidate", "actionable", "actionability",
                 "order", "fill", "buy", "sell", "stake", "wallet", "signing", "s1",
                 "aiohttp", "requests", "urllib", "socket", "httpx"):
        assert term not in low, f"forbidden term {term!r} present in onboarder source"
