"""data/public_spot_fetchers.py — read-only PUBLIC reference fetchers (Tier-0 radar).

Coinbase + Kraken USD **spot** and Hyperliquid **perp** fetchers. Each uses an INJECTED async http
client (``async def client(url) -> dict`` returning parsed JSON) — no env, no secret, no auth, and (in
this module) no implicit network client. Each returns a canonical *tick* dict with a Decimal-string
price, the verbatim raw payload, per-call timing, and an explicit ``reject_reason`` instead of raising,
so a degraded source never crashes the collector.

Source taxonomy (enforced by ``source_type``):
  coinbase|kraken -> spot   (USD only; USDT is rejected, never silently mixed)
  hyperliquid     -> perp   (separate basis input; never merged into the spot basket)

This module imports NO trading/runtime surface (main_loop/scout/execution/position/monitor/S1).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

_KRAKEN_USD_PAIR = {"BTC": "XBTUSD", "ETH": "ETHUSD", "SOL": "SOLUSD", "XRP": "XRPUSD"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decimal_text(value) -> str | None:
    """Parse a price into a canonical Decimal string, or None if not a valid finite number."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not d.is_finite():
        return None
    return str(d)


def _base_tick(source_name: str, source_type: str, asset: str, pair: str,
               started_at: str, completed_at: str, raw_payload) -> dict:
    return {
        "source_name": source_name,
        "source_type": source_type,
        "asset": asset,
        "pair": pair,
        "quote": "USD",
        "source_event_ts_raw": None,
        "source_event_ts_parse_status": "missing",  # these public endpoints carry no usable event ts
        "fetch_started_at": started_at,
        "fetch_completed_at": completed_at,
        "source_age_ms": None,
        "price_raw": None,
        "price_decimal_text": None,
        "raw_payload_json": json.dumps(raw_payload) if raw_payload is not None else None,
        "reject_reason": None,
    }


async def _timed_fetch(client, url):
    started = _now_iso()
    try:
        payload = await client(url)
    except Exception as e:  # network/parse failure is evidence, not a crash
        return None, started, _now_iso(), repr(e)
    return payload, started, _now_iso(), None


async def fetch_coinbase_spot(asset: str, *, client) -> dict:
    """Coinbase USD spot. Endpoint shape: {"data": {"amount","base","currency"}}."""
    pair = f"{asset.upper()}-USD"
    url = f"https://api.coinbase.com/v2/prices/{pair}/spot"
    payload, started, completed, err = await _timed_fetch(client, url)
    tick = _base_tick("coinbase", "spot", asset, pair, started, completed, payload)
    if err is not None or not isinstance(payload, dict):
        tick["reject_reason"] = err or "malformed_payload"
        return tick
    data = payload.get("data") or {}
    if data.get("currency") not in (None, "USD"):
        tick["reject_reason"] = "quote_not_usd"
        return tick
    price = _decimal_text(data.get("amount"))
    if price is None:
        tick["reject_reason"] = "missing_or_malformed_price"
        return tick
    tick["price_raw"] = str(data.get("amount"))
    tick["price_decimal_text"] = price
    return tick


async def fetch_kraken_spot(asset: str, *, client) -> dict:
    """Kraken USD spot. Endpoint shape: {"error": [...], "result": {PAIR: {"c": [last, lot]}}}."""
    pair = _KRAKEN_USD_PAIR.get(asset.upper(), f"{asset.upper()}USD")
    url = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
    payload, started, completed, err = await _timed_fetch(client, url)
    tick = _base_tick("kraken", "spot", asset, pair, started, completed, payload)
    if err is not None or not isinstance(payload, dict):
        tick["reject_reason"] = err or "malformed_payload"
        return tick
    if payload.get("error"):
        tick["reject_reason"] = "source_error"
        return tick
    result = payload.get("result") or {}
    if not result:
        tick["reject_reason"] = "missing_or_malformed_price"
        return tick
    first = next(iter(result.values()))
    last = (first.get("c") or [None])[0] if isinstance(first, dict) else None
    price = _decimal_text(last)
    if price is None:
        tick["reject_reason"] = "missing_or_malformed_price"
        return tick
    tick["price_raw"] = str(last)
    tick["price_decimal_text"] = price
    return tick


async def fetch_hyperliquid_perp(asset: str, *, client) -> dict:
    """Hyperliquid perp adapter. Canonical injected shape: {"price": "<decimal>"}. source_type=perp."""
    pair = f"{asset.upper()}-PERP"
    url = f"https://api.hyperliquid.xyz/info::{asset.upper()}"  # adapter marker; real client injects data
    payload, started, completed, err = await _timed_fetch(client, url)
    tick = _base_tick("hyperliquid", "perp", asset, pair, started, completed, payload)
    tick["quote"] = "USD"
    if err is not None or not isinstance(payload, dict):
        tick["reject_reason"] = err or "malformed_payload"
        return tick
    price = _decimal_text(payload.get("price"))
    if price is None:
        tick["reject_reason"] = "missing_or_malformed_price"
        return tick
    tick["price_raw"] = str(payload.get("price"))
    tick["price_decimal_text"] = price
    return tick
