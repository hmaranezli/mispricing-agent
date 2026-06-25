"""tests/test_pm_book_writer.py — isolated polymarket_book_ticks evidence writer (TDD).

`collect_polymarket_book_tick` snapshots a YES and a NO CLOB book via an INJECTED `book_fetcher`
(`async def book_fetcher(token_id) -> dict|None`), times each side separately, normalizes ladders with
strict Decimal discipline (price AND size as Decimal strings; asks ascending, bids descending; top-of-book
from the normalized ladders), and APPEND-INSERTS exactly one row into the supplied sqlite connection.

This slice does ZERO reference/pairing/log-return math, reads NO reference table, and does NOT discover or
infer the YES/NO token mapping (both token ids are authoritative caller inputs). Partial per-side failures
are persisted with side-specific `reject_reason`, never crash. venue timestamp is never fabricated.

First RED: module data.pm_book_writer does not exist → ImportError.
"""
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import aiosqlite

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import init_schema
from data.pm_book_writer import collect_polymarket_book_tick

# asks deliberately OUT of order; non-integer sizes to prove no float/int coercion
_YES_BOOK = {"asks": [{"price": "0.62", "size": "10.5"}, {"price": "0.60", "size": "5.25"}],
             "bids": [{"price": "0.55", "size": "3.5"}, {"price": "0.58", "size": "7.75"}]}
_NO_BOOK = {"asks": [{"price": "0.41", "size": "9"}, {"price": "0.39", "size": "4.5"}],
            "bids": [{"price": "0.36", "size": "2"}, {"price": "0.38", "size": "6"}]}


def _fetcher(mapping):
    """mapping: token_id -> book dict | Exception instance (raise) | None."""
    calls = []
    async def _f(token_id):
        calls.append(token_id)
        v = mapping.get(token_id, KeyError(token_id))
        if isinstance(v, BaseException):
            raise v
        return v
    _f.calls = calls
    return _f


async def _conn(tmp_path):
    db = tmp_path / "pm.db"
    conn = await aiosqlite.connect(str(db))
    await init_schema(conn)
    return conn


async def _one_row(conn):
    conn.row_factory = aiosqlite.Row
    async with conn.execute("SELECT * FROM polymarket_book_ticks") as cur:
        rows = await cur.fetchall()
    assert len(rows) == 1, f"expected exactly one row, got {len(rows)}"
    return dict(rows[0])


@pytest.mark.asyncio
async def test_schema_creates_table(tmp_path):
    conn = await _conn(tmp_path)
    async with conn.execute("PRAGMA table_info(polymarket_book_ticks)") as cur:
        cols = {r[1] for r in await cur.fetchall()}
    assert {"book_tick_id", "yes_asks_json", "no_bids_json", "top_yes_ask_text",
            "venue_book_ts_parse_status", "not_paired_with_reference"} <= cols
    await conn.close()


@pytest.mark.asyncio
async def test_success_both_sides_normalized_decimal(tmp_path):
    conn = await _conn(tmp_path)
    fetch = _fetcher({"YESTOK": _YES_BOOK, "NOTOK": _NO_BOOK})
    await collect_polymarket_book_tick(
        conn=conn, market_slug="btc-updown-5m-1", asset="BTC", timeframe="5m",
        yes_token_id="YESTOK", no_token_id="NOTOK", book_fetcher=fetch)
    row = await _one_row(conn)
    # raw preserved verbatim
    assert json.loads(row["raw_yes_book_json"]) == _YES_BOOK
    # asks ascending by Decimal(price), bids descending — from normalized ladders, not raw order
    yes_asks = json.loads(row["yes_asks_json"])
    assert [a[0] for a in yes_asks] == ["0.60", "0.62"]
    yes_bids = json.loads(row["yes_bids_json"])
    assert [b[0] for b in yes_bids] == ["0.58", "0.55"]
    # price AND size are Decimal strings (size not rounded to int)
    assert yes_asks[0] == ["0.60", "5.25"]
    # top-of-book derived from sorted ladders
    assert row["top_yes_ask_text"] == "0.60" and row["top_yes_bid_text"] == "0.58"
    assert row["top_no_ask_text"] == "0.39" and row["top_no_bid_text"] == "0.38"
    assert Decimal(row["top_no_ask_text"]) == Decimal("0.39")
    # level counts
    assert row["yes_ask_levels"] == 2 and row["no_bid_levels"] == 2
    # venue ts never fabricated; anti-claim + non-pairing flags
    assert row["venue_book_ts_raw"] is None and row["venue_book_ts_parse_status"] == "missing"
    assert row["not_paired_with_reference"] == 1
    assert row["not_execution_proven"] == 1 and row["not_profitability_proven"] == 1
    assert row["reject_reason"] is None
    await conn.close()


@pytest.mark.asyncio
async def test_explicit_token_ids_used_exactly_no_discovery(tmp_path):
    conn = await _conn(tmp_path)
    fetch = _fetcher({"YESTOK": _YES_BOOK, "NOTOK": _NO_BOOK})
    await collect_polymarket_book_tick(
        conn=conn, market_slug="s", asset="BTC", timeframe="5m",
        yes_token_id="YESTOK", no_token_id="NOTOK", book_fetcher=fetch)
    assert fetch.calls == ["YESTOK", "NOTOK"], "must fetch exactly the caller-supplied token ids, in order"
    row = await _one_row(conn)
    assert row["yes_token_id"] == "YESTOK" and row["no_token_id"] == "NOTOK"
    await conn.close()


@pytest.mark.asyncio
async def test_partial_yes_ok_no_fail_persists_row(tmp_path):
    conn = await _conn(tmp_path)
    fetch = _fetcher({"YESTOK": _YES_BOOK, "NOTOK": RuntimeError("boom")})
    await collect_polymarket_book_tick(
        conn=conn, market_slug="s", asset="BTC", timeframe="5m",
        yes_token_id="YESTOK", no_token_id="NOTOK", book_fetcher=fetch)
    row = await _one_row(conn)
    assert row["yes_asks_json"] is not None and row["top_yes_ask_text"] == "0.60"
    assert row["raw_no_book_json"] is None and row["no_asks_json"] is None
    assert row["no_ask_levels"] is None
    assert "no_missing_pm_book" in row["reject_reason"]
    await conn.close()


@pytest.mark.asyncio
async def test_partial_no_ok_yes_fail_persists_row(tmp_path):
    conn = await _conn(tmp_path)
    fetch = _fetcher({"YESTOK": None, "NOTOK": _NO_BOOK})  # None book = missing
    await collect_polymarket_book_tick(
        conn=conn, market_slug="s", asset="BTC", timeframe="5m",
        yes_token_id="YESTOK", no_token_id="NOTOK", book_fetcher=fetch)
    row = await _one_row(conn)
    assert row["no_asks_json"] is not None and row["top_no_ask_text"] == "0.39"
    assert row["yes_asks_json"] is None
    assert "yes_missing_pm_book" in row["reject_reason"]
    await conn.close()


@pytest.mark.asyncio
async def test_both_missing_and_empty_ladder_persisted_not_crash(tmp_path):
    conn = await _conn(tmp_path)
    # YES empty ladder (book present, no levels), NO missing entirely
    fetch = _fetcher({"YESTOK": {"asks": [], "bids": []}, "NOTOK": None})
    await collect_polymarket_book_tick(
        conn=conn, market_slug="s", asset="BTC", timeframe="5m",
        yes_token_id="YESTOK", no_token_id="NOTOK", book_fetcher=fetch)
    row = await _one_row(conn)
    assert row["yes_ask_levels"] == 0  # book present but no valid levels
    assert "yes_empty_ladder" in row["reject_reason"]
    assert "no_missing_pm_book" in row["reject_reason"]
    await conn.close()


@pytest.mark.asyncio
async def test_timing_fields_persisted(tmp_path):
    conn = await _conn(tmp_path)
    fetch = _fetcher({"YESTOK": _YES_BOOK, "NOTOK": _NO_BOOK})
    await collect_polymarket_book_tick(
        conn=conn, market_slug="s", asset="BTC", timeframe="5m",
        yes_token_id="YESTOK", no_token_id="NOTOK", book_fetcher=fetch)
    row = await _one_row(conn)
    for c in ("fetch_started_at", "fetch_completed_at", "yes_fetch_started_at",
              "yes_fetch_completed_at", "no_fetch_started_at", "no_fetch_completed_at"):
        assert row[c] is not None, f"{c} must be persisted"
    for c in ("fetch_span_ms", "yes_fetch_span_ms", "no_fetch_span_ms",
              "yes_no_completion_skew_ms", "capture_span_ms"):
        assert row[c] is not None and row[c] >= 0, f"{c} must be a non-negative ms value"
    await conn.close()


@pytest.mark.asyncio
async def test_scientific_notation_canonicalization(tmp_path):
    """Tiny price/size given in scientific-notation strings must persist as fixed-point, no 'E'/'e'."""
    conn = await _conn(tmp_path)
    sci_book = {"asks": [{"price": "1E-7", "size": "2E-6"}],
                "bids": [{"price": "3E-7", "size": "4E-5"}]}
    fetch = _fetcher({"YESTOK": sci_book, "NOTOK": sci_book})
    await collect_polymarket_book_tick(
        conn=conn, market_slug="s", asset="BTC", timeframe="5m",
        yes_token_id="YESTOK", no_token_id="NOTOK", book_fetcher=fetch)
    row = await _one_row(conn)
    # canonical fixed-point for BOTH price and size
    assert json.loads(row["yes_asks_json"]) == [["0.0000001", "0.000002"]]
    assert json.loads(row["yes_bids_json"]) == [["0.0000003", "0.00004"]]
    assert row["top_yes_ask_text"] == "0.0000001"
    assert row["top_no_bid_text"] == "0.0000003"
    # no scientific notation anywhere in the canonical economic fields
    for field in ("yes_asks_json", "yes_bids_json", "no_asks_json", "no_bids_json",
                  "top_yes_bid_text", "top_yes_ask_text", "top_no_bid_text", "top_no_ask_text"):
        val = row[field] or ""
        assert "E" not in val and "e" not in val, f"{field} must be fixed-point, got {val!r}"
    await conn.close()


def test_module_has_no_reference_or_pairing_or_return_math():
    import data.pm_book_writer as m
    src = open(m.__file__, "r", encoding="utf-8").read().lower()
    for banned in ("proxy_reference_basket_ticks", "reference_book_pairs", "stale_lag",
                   "reference_move", "math.log", "ln(", "/prev", "implied"):
        assert banned not in src, f"slice must not contain '{banned}'"
    # no trading/runtime imports
    import_lines = "\n".join(ln for ln in src.splitlines()
                             if ln.strip().startswith("import ") or ln.strip().startswith("from ")).lower()
    for forbidden in ("main_loop", "scout", "execution", "wallet", "telegram", "s1_storage"):
        assert forbidden not in import_lines, f"must not import '{forbidden}'"
