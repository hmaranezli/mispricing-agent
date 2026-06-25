"""tests/test_reference_collector.py — Tier-0 PUBLIC_REFERENCE_BASKET collector (TDD).

`collect_tier0` concurrently+timed-fetches Coinbase+Kraken USD spot and Hyperliquid perp (all via
injected clients), then writes APPEND-ONLY evidence to the three Tier-0 tables against a temp db:
  - reference_price_ticks         (one row per source)
  - proxy_reference_basket_ticks  (Coinbase+Kraken midpoint + spread guard; perp NEVER merged)
  - perp_basis_ticks              (HL perp basis vs the spot basket; separate row)
All prices/spreads/basis are Decimal strings. Timing (started/completed/span/skew) is persisted.
No candidates, no order_intents/positions/shadow_positions writes, no live calls.

First RED: module data.reference_collector does not exist → ImportError.
"""
import json
import os
import sys
from decimal import Decimal

import pytest
import aiosqlite

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import init_schema
from data.reference_collector import collect_tier0


def _client(payload):
    async def _c(url):
        return payload
    return _c


_CB = _client({"data": {"amount": "100.00", "base": "SOL", "currency": "USD"}})
_KR = _client({"error": [], "result": {"SOLUSD": {"c": ["100.50", "1"]}}})
_HL = _client({"price": "101.00"})


async def _fresh_db(tmp_path):
    db = tmp_path / "tier0.db"
    async with aiosqlite.connect(str(db)) as conn:
        await init_schema(conn)
    return str(db)


async def _count(db, table):
    async with aiosqlite.connect(str(db)) as conn:
        async with conn.execute(f"SELECT COUNT(*) FROM {table}") as cur:
            return (await cur.fetchone())[0]


@pytest.mark.asyncio
async def test_collect_writes_three_source_ticks(tmp_path):
    db = await _fresh_db(tmp_path)
    await collect_tier0("SOL", coinbase_client=_CB, kraken_client=_KR, hyperliquid_client=_HL,
                        db_path=db, spread_guard_max_bps="100")
    assert await _count(db, "reference_price_ticks") == 3   # coinbase + kraken + hyperliquid


@pytest.mark.asyncio
async def test_spot_basket_is_decimal_midpoint_of_coinbase_and_kraken_only(tmp_path):
    db = await _fresh_db(tmp_path)
    await collect_tier0("SOL", coinbase_client=_CB, kraken_client=_KR, hyperliquid_client=_HL,
                        db_path=db, spread_guard_max_bps="100")
    async with aiosqlite.connect(str(db)) as conn:
        async with conn.execute(
            "SELECT spot_reference_decimal_text, spread_guard_status, proxy_confidence, "
            "not_official_chainlink FROM proxy_reference_basket_ticks") as cur:
            row = await cur.fetchone()
    # midpoint of 100.00 and 100.50 = 100.25 — exact Decimal, not float
    assert Decimal(row[0]) == Decimal("100.25")
    assert row[1] == "ok"
    assert row[2] == "high"
    assert row[3] == 1


@pytest.mark.asyncio
async def test_perp_written_as_basis_never_merged_into_spot(tmp_path):
    db = await _fresh_db(tmp_path)
    await collect_tier0("SOL", coinbase_client=_CB, kraken_client=_KR, hyperliquid_client=_HL,
                        db_path=db, spread_guard_max_bps="100")
    async with aiosqlite.connect(str(db)) as conn:
        async with conn.execute(
            "SELECT perp_price_decimal_text, spot_reference_decimal_text, basis_bps_decimal_text, "
            "basis_direction FROM perp_basis_ticks") as cur:
            row = await cur.fetchone()
    assert Decimal(row[0]) == Decimal("101.00")        # perp price isolated
    assert Decimal(row[1]) == Decimal("100.25")        # references the spot basket
    # basis_bps = (101.00 - 100.25)/100.25 * 10000 = 74.8129...
    assert Decimal(row[2]) > 0
    assert row[3] == "perp_premium"
    # perp price must NOT have moved the spot basket
    async with aiosqlite.connect(str(db)) as conn:
        async with conn.execute("SELECT spot_reference_decimal_text FROM proxy_reference_basket_ticks") as cur:
            spot = (await cur.fetchone())[0]
    assert Decimal(spot) == Decimal("100.25")


@pytest.mark.asyncio
async def test_timing_evidence_persisted(tmp_path):
    db = await _fresh_db(tmp_path)
    await collect_tier0("SOL", coinbase_client=_CB, kraken_client=_KR, hyperliquid_client=_HL,
                        db_path=db, spread_guard_max_bps="100")
    async with aiosqlite.connect(str(db)) as conn:
        async with conn.execute(
            "SELECT coinbase_fetch_started_at, coinbase_fetch_completed_at, kraken_fetch_started_at, "
            "kraken_fetch_completed_at, basket_capture_span_ms, completion_skew_ms "
            "FROM proxy_reference_basket_ticks") as cur:
            row = await cur.fetchone()
    assert all(v is not None for v in row[:4]), "per-source timing must be persisted"
    assert row[4] is not None and row[4] >= 0, "basket_capture_span_ms persisted"
    assert row[5] is not None and row[5] >= 0, "completion_skew_ms persisted"


@pytest.mark.asyncio
async def test_single_spot_source_degrades_explicitly(tmp_path):
    db = await _fresh_db(tmp_path)
    bad_kr = _client({"error": ["EService:Busy"], "result": {}})  # kraken unavailable
    await collect_tier0("SOL", coinbase_client=_CB, kraken_client=bad_kr, hyperliquid_client=_HL,
                        db_path=db, spread_guard_max_bps="100")
    async with aiosqlite.connect(str(db)) as conn:
        async with conn.execute(
            "SELECT spread_guard_status, proxy_confidence FROM proxy_reference_basket_ticks") as cur:
            row = await cur.fetchone()
    assert row[0] == "single_source"
    assert row[1] == "low"


@pytest.mark.asyncio
async def test_spread_guard_fail_is_explicit(tmp_path):
    db = await _fresh_db(tmp_path)
    far_kr = _client({"error": [], "result": {"SOLUSD": {"c": ["120.00", "1"]}}})  # 20% apart
    await collect_tier0("SOL", coinbase_client=_CB, kraken_client=far_kr, hyperliquid_client=_HL,
                        db_path=db, spread_guard_max_bps="50")  # 50 bps cap
    async with aiosqlite.connect(str(db)) as conn:
        async with conn.execute(
            "SELECT spread_guard_status, proxy_confidence FROM proxy_reference_basket_ticks") as cur:
            row = await cur.fetchone()
    assert row[0] == "fail"
    assert row[1] == "unusable"


@pytest.mark.asyncio
async def test_missing_all_spot_sources_yields_missing_reference(tmp_path):
    db = await _fresh_db(tmp_path)
    bad = _client({"error": ["x"], "result": {}})
    bad_cb = _client({"data": {"base": "SOL", "currency": "USD"}})  # no amount
    await collect_tier0("SOL", coinbase_client=bad_cb, kraken_client=bad, hyperliquid_client=_HL,
                        db_path=db, spread_guard_max_bps="100")
    async with aiosqlite.connect(str(db)) as conn:
        async with conn.execute(
            "SELECT spread_guard_status, proxy_confidence, spot_reference_decimal_text "
            "FROM proxy_reference_basket_ticks") as cur:
            row = await cur.fetchone()
    assert row[0] == "missing"
    assert row[1] == "unusable"
    assert row[2] is None


@pytest.mark.asyncio
async def test_no_trading_tables_written(tmp_path):
    db = await _fresh_db(tmp_path)
    await collect_tier0("SOL", coinbase_client=_CB, kraken_client=_KR, hyperliquid_client=_HL,
                        db_path=db, spread_guard_max_bps="100")
    for t in ("order_intents", "positions", "shadow_positions", "candidates"):
        assert await _count(db, t) == 0, f"Tier-0 must not write {t}"
