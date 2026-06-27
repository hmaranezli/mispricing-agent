"""tests/test_hl_reference_price.py — TDD for the Hyperliquid reference-price courier.

fetch_hl_reference_price is an async courier over an INJECTED POST client (no real network). It reads
one coin's mid from the Hyperliquid allMids document and returns it as a Decimal reference price (NOT
a true spot price). Programmer-contract violations raise; venue/data failures return a structured
VENUE_REFERENCE_INVALID carrier echoing the asset with a null price.

POST seam: the injected client is called as client(url, *, json_body={"type": "allMids"}).

First RED: module data.hl_reference_price does not exist -> ImportError.
"""
import asyncio
import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.hl_reference_price import fetch_hl_reference_price

_BASE = "https://api.hyperliquid.example.com"
_MIDS = {"BTC": "60123.5", "ETH": "3000.0"}


def _client(payload, *, counter=None, raise_exc=None, body_sink=None):
    async def _c(url, *, json_body):
        if counter is not None:
            counter.append(url)
        if body_sink is not None:
            body_sink.append(json_body)
        if raise_exc is not None:
            raise raise_exc
        return payload
    return _c


def _run(payload, *, asset="BTC", counter=None, raise_exc=None, body_sink=None, base_url=_BASE):
    client = _client(payload, counter=counter, raise_exc=raise_exc, body_sink=body_sink)
    return asyncio.run(fetch_hl_reference_price(asset, client=client, base_url=base_url))


def _assert_invalid(r, code, asset="BTC"):
    assert r["status"] == "VENUE_REFERENCE_INVALID"
    assert r["error_code"] == code
    assert r["asset"] == asset
    assert r["reference_price"] is None
    assert r["reference_source"] == "hyperliquid_all_mids_perp"


# ===========================================================================
# happy path
# ===========================================================================

def test_happy_btc():
    r = _run(_MIDS)
    assert r["status"] == "VENUE_REFERENCE_OK"
    assert r["error_code"] is None
    assert r["asset"] == "BTC"
    assert r["reference_price"] == Decimal("60123.5")
    assert r["reference_source"] == "hyperliquid_all_mids_perp"


def test_reference_price_is_decimal_not_float():
    r = _run(_MIDS)
    assert isinstance(r["reference_price"], Decimal)
    assert not isinstance(r["reference_price"], float)


def test_single_call_and_post_body():
    c, b = [], []
    _run(_MIDS, counter=c, body_sink=b)
    assert len(c) == 1                      # exactly one call, no retry
    assert c[0] == _BASE + "/info"
    assert b == [{"type": "allMids"}]       # POST body seam


# ===========================================================================
# case-sensitive asset matching
# ===========================================================================

def test_case_sensitive_missing_asset():
    _assert_invalid(_run(_MIDS, asset="btc"), "hl_asset_not_found", asset="btc")


# ===========================================================================
# fail-closed matrix
# ===========================================================================

def test_fetch_error():
    _assert_invalid(_run(_MIDS, raise_exc=TimeoutError("boom")), "hl_fetch_error")


def test_malformed_non_dict_list():
    _assert_invalid(_run(["not", "dict"]), "hl_malformed_json")


def test_malformed_non_dict_str():
    _assert_invalid(_run("not-a-dict"), "hl_malformed_json")


def test_asset_not_found():
    _assert_invalid(_run({"ETH": "3000.0"}), "hl_asset_not_found")


def test_bad_price_none():
    _assert_invalid(_run({"BTC": None}), "hl_bad_price")


def test_bad_price_nonnumeric():
    _assert_invalid(_run({"BTC": "abc"}), "hl_bad_price")


def test_bad_price_nan():
    _assert_invalid(_run({"BTC": "NaN"}), "hl_bad_price")


def test_bad_price_infinity():
    _assert_invalid(_run({"BTC": "Infinity"}), "hl_bad_price")


def test_bad_price_zero():
    _assert_invalid(_run({"BTC": "0"}), "hl_bad_price")


def test_bad_price_negative():
    _assert_invalid(_run({"BTC": "-5"}), "hl_bad_price")


def test_bad_price_bool():
    _assert_invalid(_run({"BTC": True}), "hl_bad_price")


# ---- strict string-only price: any non-str numeric type is hl_bad_price ----

def test_bad_price_float_type():
    _assert_invalid(_run({"BTC": 60123.5}), "hl_bad_price")


def test_bad_price_int_type():
    _assert_invalid(_run({"BTC": 60123}), "hl_bad_price")


def test_bad_price_decimal_object_type():
    _assert_invalid(_run({"BTC": Decimal("60123.5")}), "hl_bad_price")


# ===========================================================================
# safe endpoint construction (both base_url forms hit the same /info)
# ===========================================================================

def test_endpoint_no_trailing_slash():
    c = []
    _run(_MIDS, counter=c, base_url="https://api.hyperliquid.xyz")
    assert c == ["https://api.hyperliquid.xyz/info"]


def test_endpoint_with_trailing_slash():
    c = []
    _run(_MIDS, counter=c, base_url="https://api.hyperliquid.xyz/")
    assert c == ["https://api.hyperliquid.xyz/info"]


def test_endpoint_with_multi_trailing_slash():
    c = []
    _run(_MIDS, counter=c, base_url="https://api.hyperliquid.xyz///")
    assert c == ["https://api.hyperliquid.xyz/info"]


# ===========================================================================
# fail-fast programmer-contract violations: EXACT exception + ZERO client calls
# (prove malformed programmer inputs never reach the injected client)
# ===========================================================================

def _expect_raise(exc_type, *, asset="BTC", base_url=_BASE):
    counter = []
    client = _client(_MIDS, counter=counter)
    with pytest.raises(exc_type):
        asyncio.run(fetch_hl_reference_price(asset, client=client, base_url=base_url))
    return counter


def test_ff_asset_wrong_type_typeerror():
    assert _expect_raise(TypeError, asset=123) == []


def test_ff_asset_empty_valueerror():
    assert _expect_raise(ValueError, asset="") == []


def test_ff_asset_space_valueerror():
    assert _expect_raise(ValueError, asset=" ") == []


def test_ff_asset_padded_valueerror():
    assert _expect_raise(ValueError, asset=" BTC ") == []


def test_ff_asset_tab_valueerror():
    assert _expect_raise(ValueError, asset="\tBTC") == []


def test_ff_base_url_wrong_type_typeerror():
    assert _expect_raise(TypeError, base_url=123) == []


def test_ff_base_url_empty_valueerror():
    assert _expect_raise(ValueError, base_url="") == []


def test_ff_base_url_space_valueerror():
    assert _expect_raise(ValueError, base_url=" ") == []


def test_ff_base_url_leading_space_valueerror():
    assert _expect_raise(ValueError, base_url=" https://api.hyperliquid.xyz") == []


def test_ff_base_url_trailing_space_valueerror():
    assert _expect_raise(ValueError, base_url="https://api.hyperliquid.xyz ") == []


def test_ff_base_url_slash_only_valueerror():
    assert _expect_raise(ValueError, base_url="/") == []


def test_ff_base_url_multi_slash_only_valueerror():
    assert _expect_raise(ValueError, base_url="///") == []


def test_ff_non_callable_client_typeerror():
    # None is not callable; it can never be invoked, so call count is trivially zero
    with pytest.raises(TypeError):
        asyncio.run(fetch_hl_reference_price("BTC", client=None, base_url=_BASE))


# ===========================================================================
# source scan (case-insensitive)
# ===========================================================================

def test_source_scan_no_forbidden_surfaces():
    import data.hl_reference_price as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        low = fh.read().lower()
    banned = (
        "trade", "signal", "edge", "candidate", "actionable", "actionability",
        "order", "fill", "buy", "sell", "stake", "wallet", "signing", "s1",
        "scanner", "runner", "cache", "pagination", "next_cursor", "discover",
        "while", "retry",
        "aiohttp", "requests",
    )
    for term in banned:
        assert term not in low, f"forbidden term {term!r} present in reference courier source"
