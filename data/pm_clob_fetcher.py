"""data/pm_clob_fetcher.py — isolated single-token PM CLOB /book courier (radar, NOT trading).

Given a token_id, base_url, and an INJECTED async http_client, fetches one CLOB /book payload,
preserves the verbatim raw HTTP body text, parses JSON float-safely via
json.loads(raw, parse_float=Decimal, parse_int=Decimal) — so no IEEE-754 float ever enters
parsed_safe_book — and returns a structured BookFetchResult carrier. Per-token failures are
returned as structured carriers, never raised into the caller. Programmer errors (empty
token_id/base_url, None http_client) raise ValueError immediately.

This module:
  * calls ONLY the CLOB /book endpoint; token_id is the sole query input (no discovery or mapping)
  * holds no module-level state, no book cache, no accumulated ladder history
  * never writes to any DB and never pairs with reference data
  * never computes log returns, edge math, or output signals of any kind
  * imports NO trading/runtime surface (main_loop/scout/execution/wallet/Telegram/S1)

Async client protocol (aiohttp-like, injectable):
  response = await http_client.get(url, params=..., timeout=...)
  status   = response.status          # int
  body     = await response.text()    # raw body text
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


@dataclass
class BookFetchResult:
    token_id: str
    raw_body_text: str | None
    parsed_safe_book: dict | None
    fetch_started_at: datetime
    fetch_completed_at: datetime
    fetch_span_ms: int
    http_status: int | None
    error_code: str | None
    reject_reason: str | None
    venue_book_ts_raw: None
    venue_book_ts_parse_status: str


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _span_ms(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() * 1000)


async def fetch_clob_book(
    token_id: str,
    *,
    http_client,
    base_url: str,
    timeout_s: float | None = None,
    now_fn=_now_utc,
) -> BookFetchResult:
    """Fetch one CLOB /book payload for token_id via injected http_client; return evidence carrier."""
    if not token_id:
        raise ValueError("token_id must be a non-empty string")
    if not base_url:
        raise ValueError("base_url must be a non-empty string")
    if http_client is None:
        raise ValueError("http_client must not be None")

    started = now_fn()

    def _build(*, http_status, raw_body_text, parsed_safe_book, error_code, reject_reason):
        completed = now_fn()
        return BookFetchResult(
            token_id=token_id,
            raw_body_text=raw_body_text,
            parsed_safe_book=parsed_safe_book,
            fetch_started_at=started,
            fetch_completed_at=completed,
            fetch_span_ms=_span_ms(started, completed),
            http_status=http_status,
            error_code=error_code,
            reject_reason=reject_reason,
            venue_book_ts_raw=None,
            venue_book_ts_parse_status="missing",
        )

    url = f"{base_url.rstrip('/')}/book"
    get_kwargs: dict = {"params": {"token_id": token_id}}
    if timeout_s is not None:
        get_kwargs["timeout"] = timeout_s

    # --- network call ---------------------------------------------------------
    try:
        response = await http_client.get(url, **get_kwargs)
    except (asyncio.TimeoutError, TimeoutError):
        return _build(http_status=None, raw_body_text=None, parsed_safe_book=None,
                      error_code="timeout", reject_reason="timeout")
    except Exception as exc:
        return _build(http_status=None, raw_body_text=None, parsed_safe_book=None,
                      error_code="network_error", reject_reason=repr(exc))

    status: int = response.status

    # --- non-200 / rate-limit -------------------------------------------------
    if status == 429:
        try:
            body = await response.text()
        except Exception:
            body = None
        return _build(http_status=status, raw_body_text=body, parsed_safe_book=None,
                      error_code="http_429", reject_reason="http_429")

    if status != 200:
        try:
            body = await response.text()
        except Exception:
            body = None
        return _build(http_status=status, raw_body_text=body, parsed_safe_book=None,
                      error_code="non_200", reject_reason=f"http_{status}")

    # --- 200: read raw body text first ----------------------------------------
    try:
        raw_body_text: str = await response.text()
    except Exception as exc:
        return _build(http_status=status, raw_body_text=None, parsed_safe_book=None,
                      error_code="network_error", reject_reason=repr(exc))

    if not raw_body_text:
        return _build(http_status=status, raw_body_text=raw_body_text, parsed_safe_book=None,
                      error_code="empty_body", reject_reason="empty_body")

    # --- float-safe parse (parse_float AND parse_int = Decimal) ---------------
    try:
        parsed = json.loads(raw_body_text, parse_float=Decimal, parse_int=Decimal)
    except (json.JSONDecodeError, ValueError):
        return _build(http_status=status, raw_body_text=raw_body_text, parsed_safe_book=None,
                      error_code="malformed_json", reject_reason="malformed_json")

    if not isinstance(parsed, dict) or ("asks" not in parsed and "bids" not in parsed):
        safe = parsed if isinstance(parsed, dict) else None
        return _build(http_status=status, raw_body_text=raw_body_text, parsed_safe_book=safe,
                      error_code="missing_book_sides", reject_reason="missing_book_sides")

    return _build(http_status=status, raw_body_text=raw_body_text, parsed_safe_book=parsed,
                  error_code=None, reject_reason=None)
