"""Binance klines candle-open courier. Injected client, one call, fail-closed; Decimal price."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

_INTERVAL_MS = {
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
}

_OK = "VENUE_STRIKE_OK"
_INVALID = "VENUE_STRIKE_INVALID"
_STRIKE_SOURCE = "binance_klines_candle_open"


def _is_clean_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


async def fetch_binance_candle_open(symbol, interval, event_start_time_ms, now_ms,
                                    *, client, base_url) -> dict:
    # ---- programmer-contract checks: fail-fast (never a binance_* carrier) ----
    if not isinstance(symbol, str):
        raise TypeError("symbol must be a str")
    if not symbol:
        raise ValueError("symbol must be non-empty")
    if not isinstance(interval, str):
        raise TypeError("interval must be a str")
    if interval not in _INTERVAL_MS:
        raise ValueError("interval must be one of " + ", ".join(sorted(_INTERVAL_MS)))
    if not _is_clean_int(event_start_time_ms) or event_start_time_ms < 0:
        raise ValueError("event_start_time_ms must be an int >= 0")
    if not _is_clean_int(now_ms) or now_ms < 0:
        raise ValueError("now_ms must be an int >= 0")
    if not isinstance(base_url, str):
        raise TypeError("base_url must be a str")
    if not base_url:
        raise ValueError("base_url must be non-empty")
    if not callable(client):
        raise TypeError("client must be callable")

    def reject(code):
        return {
            "symbol": symbol,
            "interval": interval,
            "event_start_time_ms": event_start_time_ms,
            "returned_open_time_ms": None,
            "strike_price": None,
            "strike_source": None,
            "status": _INVALID,
            "error_code": code,
        }

    # ---- future strike paradox: before any client call ----
    if now_ms < event_start_time_ms:
        return reject("binance_future_candle")

    span = _INTERVAL_MS[interval]
    end = event_start_time_ms + span - 1
    url = (base_url.rstrip("/") + "/api/v3/klines?symbol=" + symbol
           + "&interval=" + interval + "&startTime=" + str(event_start_time_ms)
           + "&endTime=" + str(end) + "&limit=1")

    # ---- one venue call ----
    try:
        payload = await client(url)
    except Exception as exc:
        if getattr(exc, "status", None) == 451 or getattr(exc, "code", None) == 451:
            return reject("binance_geo_blocked")
        return reject("binance_fetch_error")

    if not isinstance(payload, list):
        return reject("binance_malformed_json")
    if len(payload) == 0:
        return reject("binance_empty")
    if len(payload) > 1:
        return reject("binance_multiple_candles")

    kline = payload[0]
    if not isinstance(kline, (list, tuple)) or len(kline) < 2:
        return reject("binance_malformed_kline")
    open_time = kline[0]
    if not _is_clean_int(open_time):
        return reject("binance_malformed_kline")
    if open_time != event_start_time_ms:
        return reject("binance_open_time_mismatch")

    raw_open = kline[1]
    if raw_open is None or isinstance(raw_open, bool):
        return reject("binance_bad_price")
    try:
        price = Decimal(str(raw_open))
    except (InvalidOperation, ValueError, TypeError):
        return reject("binance_bad_price")
    if price <= 0:
        return reject("binance_bad_price")

    return {
        "symbol": symbol,
        "interval": interval,
        "event_start_time_ms": event_start_time_ms,
        "returned_open_time_ms": open_time,
        "strike_price": price,
        "strike_source": _STRIKE_SOURCE,
        "status": _OK,
        "error_code": None,
    }
