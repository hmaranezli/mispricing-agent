"""tests/test_public_spot_fetchers.py — read-only public spot/perp fetchers (TDD).

Coinbase + Kraken USD spot fetchers and a Hyperliquid perp fetcher use an INJECTED async http client
(`async def client(url) -> dict` returning parsed JSON). No env/secret/auth, NO live calls. Each returns
a canonical tick dict with a Decimal-string price, verbatim raw payload, per-call timing, and an explicit
`reject_reason` (never a crash) for malformed/missing price or a non-USD (USDT) quote.

First RED: module data.public_spot_fetchers does not exist → ImportError.
"""
import json
import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.public_spot_fetchers import (
    fetch_coinbase_spot, fetch_kraken_spot, fetch_hyperliquid_perp,
)


def _client_returning(payload):
    async def _c(url):
        return payload
    return _c


# ---------------------------------------------------------------------- Coinbase
@pytest.mark.asyncio
async def test_coinbase_spot_parses_decimal_string_and_preserves_raw():
    payload = {"data": {"amount": "64250.37", "base": "BTC", "currency": "USD"}}
    tick = await fetch_coinbase_spot("BTC", client=_client_returning(payload))
    assert tick["source_name"] == "coinbase"
    assert tick["source_type"] == "spot"
    assert tick["quote"] == "USD"
    assert tick["price_decimal_text"] == "64250.37"
    assert Decimal(tick["price_decimal_text"]) == Decimal("64250.37")
    assert tick["reject_reason"] is None
    assert json.loads(tick["raw_payload_json"]) == payload
    assert tick["fetch_started_at"] and tick["fetch_completed_at"]


@pytest.mark.asyncio
async def test_coinbase_rejects_non_usd_quote_not_crash():
    payload = {"data": {"amount": "64250.37", "base": "BTC", "currency": "USDT"}}
    tick = await fetch_coinbase_spot("BTC", client=_client_returning(payload))
    assert tick["reject_reason"] == "quote_not_usd"
    assert tick["price_decimal_text"] is None


@pytest.mark.asyncio
async def test_coinbase_rejects_missing_price_not_crash():
    payload = {"data": {"base": "BTC", "currency": "USD"}}  # no amount
    tick = await fetch_coinbase_spot("BTC", client=_client_returning(payload))
    assert tick["reject_reason"] == "missing_or_malformed_price"
    assert tick["price_decimal_text"] is None


# ------------------------------------------------------------------------ Kraken
@pytest.mark.asyncio
async def test_kraken_spot_parses_last_trade_price():
    payload = {"error": [], "result": {"XXBTZUSD": {"c": ["64251.10", "0.01"]}}}
    tick = await fetch_kraken_spot("BTC", client=_client_returning(payload))
    assert tick["source_name"] == "kraken"
    assert tick["source_type"] == "spot"
    assert tick["quote"] == "USD"
    assert tick["price_decimal_text"] == "64251.10"
    assert tick["reject_reason"] is None


@pytest.mark.asyncio
async def test_kraken_rejects_api_error_payload():
    payload = {"error": ["EQuery:Unknown asset pair"], "result": {}}
    tick = await fetch_kraken_spot("BTC", client=_client_returning(payload))
    assert tick["reject_reason"] == "source_error"
    assert tick["price_decimal_text"] is None


# ------------------------------------------------------------------- Hyperliquid
@pytest.mark.asyncio
async def test_hyperliquid_perp_is_perp_source_type():
    payload = {"price": "64280.00"}
    tick = await fetch_hyperliquid_perp("BTC", client=_client_returning(payload))
    assert tick["source_name"] == "hyperliquid"
    assert tick["source_type"] == "perp"          # NEVER 'spot' — must not merge into spot basket
    assert tick["price_decimal_text"] == "64280.00"
    assert tick["reject_reason"] is None


@pytest.mark.asyncio
async def test_fetchers_take_no_secret_or_env():
    """Injected client only — calling with a plain async client must work with no env set."""
    import inspect
    for fn in (fetch_coinbase_spot, fetch_kraken_spot, fetch_hyperliquid_perp):
        sig = inspect.signature(fn)
        assert "client" in sig.parameters, f"{fn.__name__} must accept an injected client"
        # client must be keyword-only (dependency injection, never an implicit default network client)
        assert sig.parameters["client"].kind == inspect.Parameter.KEYWORD_ONLY
