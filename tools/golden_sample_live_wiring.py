"""Capture-only Golden Sample live wiring (async library; no driver, no __main__, no print).

This thin seam adapts two UNCHANGED single-shot couriers to the UNCHANGED capture-only orchestrator:

  * data.pm_clob_fetcher.fetch_clob_book          -> PM CLOB /book leg (YES + NO tokens)
  * data.hl_reference_price.fetch_hl_reference_price -> Hyperliquid allMids reference leg (perp leg)

It hands tools.golden_sample_orchestrator.orchestrate_golden_sample one caller-provided prevalidated
onboarding_record, in-process. The wiring owns ONLY three things:

  1. per-leg deadline validation (pm_timeout_s, hl_timeout_s) as positive finite non-bool numbers;
  2. the shared PM session lifetime via `async with` (one client shared by the YES and NO legs);
  3. three thin single-argument closure adapters (YES, NO, HL) matching the orchestrator's
     `await fetcher(arg)` contract.

Everything else — concurrency, deterministic precedence, partial-evidence joining, and all
latency/span/skew timing — stays inside the orchestrator. This module never fans out concurrently
and starts no task of its own. The onboarding_record is consumed as-is and is not re-derived. Per-leg
deadlines are network configuration only; they are never evidence fields and never max_skew_ms.
Nothing here is persisted. Prices stay Decimal; no fixed-point-to-binary conversion occurs.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from decimal import Decimal

from data.pm_clob_fetcher import fetch_clob_book
from data.hl_reference_price import fetch_hl_reference_price
from tools.golden_sample_orchestrator import orchestrate_golden_sample


def _validate_deadline(name, value):
    """A per-leg network deadline must be a positive finite non-bool int/float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a non-bool int/float network deadline")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


async def run_golden_sample_live(
    *,
    onboarding_record,
    pm_session,
    hl_client_factory,
    pm_base_url,
    hl_base_url,
    pm_timeout_s,
    hl_timeout_s,
    monotonic_ns_fn,
    utc_now_fn,
    max_skew_ms,
) -> dict:
    """Bind injected live clients to the unchanged orchestrator and return its in-memory record.

    pm_session: async context manager yielding a PM http_client exposing
        `await http_client.get(url, params=..., timeout=...)`. Shared by the YES and NO legs.
    hl_client_factory: callable(timeout_s) -> async callable(url, *, json_body=...) for the HL leg.
    """
    _validate_deadline("pm_timeout_s", pm_timeout_s)
    _validate_deadline("hl_timeout_s", hl_timeout_s)

    async with pm_session as http_client:
        hl_client = hl_client_factory(hl_timeout_s)

        def yes_book_fetcher(token_id):
            return fetch_clob_book(token_id, http_client=http_client,
                                   base_url=pm_base_url, timeout_s=pm_timeout_s)

        def no_book_fetcher(token_id):
            return fetch_clob_book(token_id, http_client=http_client,
                                   base_url=pm_base_url, timeout_s=pm_timeout_s)

        def hl_reference_fetcher(asset):
            return fetch_hl_reference_price(asset, client=hl_client, base_url=hl_base_url)

        return await orchestrate_golden_sample(
            onboarding_record=onboarding_record,
            yes_book_fetcher=yes_book_fetcher,
            no_book_fetcher=no_book_fetcher,
            hl_reference_fetcher=hl_reference_fetcher,
            monotonic_ns_fn=monotonic_ns_fn,
            utc_now_fn=utc_now_fn,
            max_skew_ms=max_skew_ms,
        )


def _encode(value):
    """Strict projection to JSON-safe nodes. Decimal -> fixed-point str; datetime -> isoformat.

    Rejects binary numbers and any other node so no IEEE-754 float and no opaque object can leak.
    Pure: builds fresh containers and never mutates the input.
    """
    if value is None:
        return None
    t = type(value)
    if t is bool:
        return value          # bool is JSON-safe; json.dumps renders true/false natively (no default=str)
    if t is int:
        return value
    if t is str:
        return value
    if t is Decimal:
        return format(value, "f")
    if t is float:
        raise TypeError("float is not permitted; prices must remain Decimal")
    if isinstance(value, datetime):
        return value.isoformat()
    if t is dict:
        out = {}
        for k, v in value.items():
            if type(k) is not str:
                raise TypeError("non-str dict key in Golden Sample projection")
            out[k] = _encode(v)
        return out
    if t is list:
        return [_encode(x) for x in value]
    if t is tuple:
        return [_encode(x) for x in value]
    raise TypeError(f"unsupported projection node type {t.__name__}")


def serialize_golden_sample(record) -> str:
    """Return a strict deterministic JSON string for one Golden Sample record without mutating it."""
    return json.dumps(_encode(record), sort_keys=True, separators=(",", ":"))
