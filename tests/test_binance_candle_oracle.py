"""tests/test_binance_candle_oracle.py — TDD for the Binance candle-open oracle courier.

fetch_binance_candle_open is an async courier over an INJECTED client (no real network). It returns
the exact candle-open price as a venue-verified numeric strike (Decimal). Programmer-contract
violations raise; the future-candle branch and every venue/data failure return a structured
VENUE_STRIKE_INVALID carrier that echoes the request inputs and nulls all fetched/derived fields.

First RED: module data.binance_candle_oracle does not exist -> ImportError.
"""
import asyncio
import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.binance_candle_oracle import fetch_binance_candle_open

_SYMBOL = "BTCUSDT"
_INTERVAL = "1h"
_EVENT_MS = 1782500400000
_INTERVAL_MS = 3_600_000
_BASE = "https://api.binance.example.com"
_NOW_PAST = _EVENT_MS + 600_000   # now is after window open


def _kline(open_time=_EVENT_MS, open_price="59668.01000000"):
    return [open_time, open_price, "60000.0", "59000.0", "59800.0", "123.4",
            open_time + _INTERVAL_MS - 1]


def _client(payload, *, counter=None, raise_exc=None):
    async def _c(url):
        if counter is not None:
            counter.append(url)
        if raise_exc is not None:
            raise raise_exc
        return payload
    return _c


def _run(payload=None, *, now_ms=_NOW_PAST, counter=None, raise_exc=None):
    client = _client(payload, counter=counter, raise_exc=raise_exc)
    return asyncio.run(fetch_binance_candle_open(_SYMBOL, _INTERVAL, _EVENT_MS, now_ms,
                                                 client=client, base_url=_BASE))


def _assert_invalid(r, code):
    assert r["status"] == "VENUE_STRIKE_INVALID"
    assert r["error_code"] == code
    # echo originals
    assert r["symbol"] == _SYMBOL
    assert r["interval"] == _INTERVAL
    assert r["event_start_time_ms"] == _EVENT_MS
    # null all fetched/derived
    assert r["returned_open_time_ms"] is None
    assert r["strike_price"] is None
    assert r["strike_source"] is None


class _GeoStatusExc(Exception):
    status = 451


class _GeoCodeExc(Exception):
    code = 451


# ===========================================================================
# happy path
# ===========================================================================

def test_happy_path():
    c = []
    r = _run([_kline()], counter=c)
    assert r["status"] == "VENUE_STRIKE_OK"
    assert r["error_code"] is None
    assert r["symbol"] == _SYMBOL
    assert r["interval"] == _INTERVAL
    assert r["event_start_time_ms"] == _EVENT_MS
    assert r["returned_open_time_ms"] == _EVENT_MS
    assert r["strike_price"] == Decimal("59668.01000000")
    assert r["strike_source"] == "binance_klines_candle_open"
    assert len(c) == 1


def test_strike_is_decimal_not_float():
    r = _run([_kline(open_price="59668.01")])
    assert isinstance(r["strike_price"], Decimal)
    assert not isinstance(r["strike_price"], float)


def test_now_equal_event_start_is_not_future():
    c = []
    r = _run([_kline()], now_ms=_EVENT_MS, counter=c)
    assert r["status"] == "VENUE_STRIKE_OK"
    assert len(c) == 1


# ===========================================================================
# future strike paradox (no client call)
# ===========================================================================

def test_future_candle_no_client_call():
    c = []
    r = _run([_kline()], now_ms=_EVENT_MS - 1, counter=c)
    _assert_invalid(r, "binance_future_candle")
    assert len(c) == 0


# ===========================================================================
# geo-block (duck-typed) vs generic fetch error
# ===========================================================================

def test_geo_blocked_via_status():
    _assert_invalid(_run(raise_exc=_GeoStatusExc("blocked")), "binance_geo_blocked")


def test_geo_blocked_via_code():
    _assert_invalid(_run(raise_exc=_GeoCodeExc("blocked")), "binance_geo_blocked")


def test_generic_exception_is_fetch_error():
    _assert_invalid(_run(raise_exc=TimeoutError("boom")), "binance_fetch_error")


# ===========================================================================
# venue/data fail-closed matrix
# ===========================================================================

def test_malformed_json_non_list():
    _assert_invalid(_run({"not": "list"}), "binance_malformed_json")


def test_empty_array():
    _assert_invalid(_run([]), "binance_empty")


def test_multiple_candles():
    _assert_invalid(_run([_kline(), _kline()]), "binance_multiple_candles")


def test_malformed_kline_not_list():
    _assert_invalid(_run(["not-a-kline"]), "binance_malformed_kline")


def test_malformed_kline_too_short():
    _assert_invalid(_run([[_EVENT_MS]]), "binance_malformed_kline")


def test_malformed_kline_open_time_not_int():
    _assert_invalid(_run([["not-int", "59668.01"]]), "binance_malformed_kline")


def test_open_time_mismatch():
    _assert_invalid(_run([_kline(open_time=_EVENT_MS + 1)]), "binance_open_time_mismatch")


def test_bad_price_nonnumeric():
    _assert_invalid(_run([_kline(open_price="abc")]), "binance_bad_price")


def test_bad_price_none():
    _assert_invalid(_run([_kline(open_price=None)]), "binance_bad_price")


def test_bad_price_zero():
    _assert_invalid(_run([_kline(open_price="0")]), "binance_bad_price")


def test_bad_price_negative():
    _assert_invalid(_run([_kline(open_price="-5")]), "binance_bad_price")


def test_bad_price_bool():
    _assert_invalid(_run([_kline(open_price=True)]), "binance_bad_price")


# ===========================================================================
# fail-fast programmer-contract violations (raise, never binance_*)
# ===========================================================================

def _ff(symbol=_SYMBOL, interval=_INTERVAL, event=_EVENT_MS, now=_NOW_PAST,
        client="DEFAULT", base_url=_BASE):
    if client == "DEFAULT":
        client = _client([_kline()])
    return asyncio.run(fetch_binance_candle_open(symbol, interval, event, now,
                                                 client=client, base_url=base_url))


def test_ff_bad_symbol_type():
    with pytest.raises((TypeError, ValueError)):
        _ff(symbol=123)


def test_ff_empty_symbol():
    with pytest.raises((TypeError, ValueError)):
        _ff(symbol="")


def test_ff_unsupported_interval():
    with pytest.raises((TypeError, ValueError)):
        _ff(interval="7m")


def test_ff_bad_interval_type():
    with pytest.raises((TypeError, ValueError)):
        _ff(interval=123)


def test_ff_bad_event_start_type():
    with pytest.raises((TypeError, ValueError)):
        _ff(event="x")


def test_ff_negative_event_start():
    with pytest.raises((TypeError, ValueError)):
        _ff(event=-1)


def test_ff_bool_event_start():
    with pytest.raises((TypeError, ValueError)):
        _ff(event=True)


def test_ff_bad_now_type():
    with pytest.raises((TypeError, ValueError)):
        _ff(now="x")


def test_ff_negative_now():
    with pytest.raises((TypeError, ValueError)):
        _ff(now=-1)


def test_ff_bad_base_url():
    with pytest.raises((TypeError, ValueError)):
        _ff(base_url="")


def test_ff_non_callable_client():
    with pytest.raises(TypeError):
        _ff(client=None)


# ===========================================================================
# source scan (case-insensitive)
# ===========================================================================

def test_source_scan_no_forbidden_surfaces():
    import data.binance_candle_oracle as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        low = fh.read().lower()
    banned = (
        "retry", "while", "time.time", "datetime.now", "datetime.utcnow",
        "trade", "signal", "edge", "candidate", "actionable", "actionability",
        "order", "fill", "buy", "sell", "stake", "wallet", "signing", "s1",
        "scanner", "cache", "runner",
        "aiohttp", "requests", "urllib", "socket", "httpx",
        "discover", "pagination", "next_cursor",
    )
    for term in banned:
        assert term not in low, f"forbidden term {term!r} present in oracle source"
