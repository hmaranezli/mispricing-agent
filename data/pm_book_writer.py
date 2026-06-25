"""data/pm_book_writer.py — isolated polymarket_book_ticks evidence writer (radar, NOT trading).

Snapshots a YES and a NO Polymarket CLOB book via an INJECTED ``book_fetcher`` and APPEND-INSERTS exactly
one row into a supplied sqlite connection. This slice:
  * does ZERO reference/pairing/log-return math and reads NO reference table;
  * treats ``yes_token_id`` / ``no_token_id`` as authoritative caller inputs (no discovery/mapping);
  * normalizes ladders with strict Decimal discipline — price AND size as Decimal strings, asks ascending,
    bids descending, top-of-book derived from the normalized ladders (raw venue order is not trusted);
  * persists partial per-side failures with side-specific ``reject_reason`` (never crashes / never drops);
  * never fabricates a venue book timestamp (client receipt time is not a venue event ts).

Imports NO trading/runtime surface (main_loop/scout/execution/wallet/Telegram/S1).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

_SCHEMA_VERSION = 1


def _now_utc():
    return datetime.now(timezone.utc)


def _span_ms(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() * 1000)


def _dec(value):
    """Canonical positive Decimal, or None if not a valid finite positive number."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not d.is_finite() or d <= 0:
        return None
    return d


def _normalize_side(book):
    """Return (asks, bids) as ascending/descending Decimal-string ladders, or raise on a non-dict book.

    asks: ascending by price; bids: descending by price. Each entry is [price_text, size_text] with both
    values exact Decimal strings (size never rounded). Levels with non-positive/invalid price or size drop.
    """
    if not isinstance(book, dict):
        raise ValueError("malformed_book")

    def _levels(raw):
        out = []
        for x in raw or []:
            if not isinstance(x, dict):
                continue
            p, s = _dec(x.get("price")), _dec(x.get("size"))
            if p is not None and s is not None:
                # Canonical fixed-point strings (never scientific notation) for price AND size.
                out.append((p, format(p, "f"), format(s, "f")))
        return out

    asks = sorted(_levels(book.get("asks")), key=lambda t: t[0])              # ascending price
    bids = sorted(_levels(book.get("bids")), key=lambda t: t[0], reverse=True)  # descending price
    return ([[pt, st] for _, pt, st in asks], [[pt, st] for _, pt, st in bids])


def _capture_side(token_id, book_fetcher_result_or_exc):
    """Build a per-side evidence dict from a fetched book (or a failure marker)."""
    side = {
        "raw_json": None, "asks": None, "bids": None,
        "ask_levels": None, "bid_levels": None, "top_bid": None, "top_ask": None,
        "reject": None,
    }
    book, exc = book_fetcher_result_or_exc
    if exc is not None:
        side["reject"] = "missing_pm_book"
        return side
    if book is None:
        side["reject"] = "missing_pm_book"
        return side
    try:
        asks, bids = _normalize_side(book)
    except ValueError:
        side["raw_json"] = json.dumps(book) if book is not None else None
        side["reject"] = "malformed_book"
        return side
    side["raw_json"] = json.dumps(book)
    side["asks"], side["bids"] = json.dumps(asks), json.dumps(bids)
    side["ask_levels"], side["bid_levels"] = len(asks), len(bids)
    side["top_ask"] = asks[0][0] if asks else None
    side["top_bid"] = bids[0][0] if bids else None
    if not asks and not bids:
        side["reject"] = "empty_ladder"
    return side


async def _fetch(book_fetcher, token_id):
    try:
        return (await book_fetcher(token_id), None)
    except Exception as e:  # per-token failure is evidence, not a crash
        return (None, e)


async def collect_polymarket_book_tick(*, conn, market_slug: str, asset: str, timeframe: str,
                                       yes_token_id: str, no_token_id: str, book_fetcher,
                                       now_fn=_now_utc) -> dict:
    """Snapshot YES then NO books (timed separately) and append one row into ``conn``. Returns a summary."""
    yes_start = now_fn()
    yes_res = await _fetch(book_fetcher, yes_token_id)
    yes_done = now_fn()
    no_start = now_fn()
    no_res = await _fetch(book_fetcher, no_token_id)
    no_done = now_fn()

    yes = _capture_side(yes_token_id, yes_res)
    no = _capture_side(no_token_id, no_res)

    # combined reject_reason (side-specific; both-missing collapses to a single token)
    if yes["reject"] == "missing_pm_book" and no["reject"] == "missing_pm_book":
        reject = "both_missing_pm_book"
    else:
        parts = []
        if yes["reject"]:
            parts.append(f"yes_{yes['reject']}")
        if no["reject"]:
            parts.append(f"no_{no['reject']}")
        reject = ";".join(parts) if parts else None

    fetch_started, fetch_completed = yes_start, no_done
    row = {
        "book_tick_id": f"bt-{uuid.uuid4()}",
        "market_slug": market_slug, "asset": asset, "timeframe": timeframe,
        "yes_token_id": yes_token_id, "no_token_id": no_token_id,
        "fetch_started_at": fetch_started.isoformat(), "fetch_completed_at": fetch_completed.isoformat(),
        "fetch_span_ms": _span_ms(fetch_started, fetch_completed),
        "yes_fetch_started_at": yes_start.isoformat(), "yes_fetch_completed_at": yes_done.isoformat(),
        "yes_fetch_span_ms": _span_ms(yes_start, yes_done),
        "no_fetch_started_at": no_start.isoformat(), "no_fetch_completed_at": no_done.isoformat(),
        "no_fetch_span_ms": _span_ms(no_start, no_done),
        "yes_no_completion_skew_ms": abs(_span_ms(yes_done, no_done)),
        "capture_span_ms": _span_ms(min(yes_start, no_start), max(yes_done, no_done)),
        "raw_yes_book_json": yes["raw_json"], "raw_no_book_json": no["raw_json"],
        "yes_asks_json": yes["asks"], "yes_bids_json": yes["bids"],
        "no_asks_json": no["asks"], "no_bids_json": no["bids"],
        "yes_ask_levels": yes["ask_levels"], "yes_bid_levels": yes["bid_levels"],
        "no_ask_levels": no["ask_levels"], "no_bid_levels": no["bid_levels"],
        "top_yes_bid_text": yes["top_bid"], "top_yes_ask_text": yes["top_ask"],
        "top_no_bid_text": no["top_bid"], "top_no_ask_text": no["top_ask"],
        "venue_book_ts_raw": None, "venue_book_ts_parse_status": "missing",
        "reject_reason": reject,
        "not_paired_with_reference": 1, "not_execution_proven": 1, "not_profitability_proven": 1,
        "schema_version": _SCHEMA_VERSION, "created_at": _now_utc().isoformat(),
    }

    cols = list(row.keys())
    await conn.execute(
        f"INSERT INTO polymarket_book_ticks ({','.join(cols)}) "
        f"VALUES ({','.join('?' for _ in cols)})",
        [row[c] for c in cols])
    await conn.commit()
    return row
