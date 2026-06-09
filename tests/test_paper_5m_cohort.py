"""tests/test_paper_5m_cohort.py — 5m ayrı deney cohort TDD.

5m marketler MIN_SECONDS=300 yüzünden 15m taramasında elenir. 5m için dinamik
min_seconds=60 (sadece shadow path). 5m paper'lar cohort='paper_5m' → 15m clean'e
ASLA karışmaz. Canlı MIN_SECONDS=300 değişmez.
"""
import asyncio
import sys
import os
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_process_market_min_seconds_default_unchanged():
    """_process_market min_seconds default → scout.MIN_SECONDS (canlı 300 korunur)."""
    import council.scout as scout
    import inspect
    sig = inspect.signature(scout._process_market)
    assert "min_seconds" in sig.parameters
    assert sig.parameters["min_seconds"].default is None  # None → MIN_SECONDS


@pytest.mark.asyncio
async def test_5m_paper_cohort_separate():
    """5m slug → cohort='paper_5m', 15m clean cohort='paper'a karışmaz."""
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    pt._active.clear()
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        finding = {"slug": "btc-updown-5m-999", "asset": "BTC", "action": "YES",
                   "best_ask": 0.56, "no_ask": 0.45, "fair_value": 0.64, "edge": 0.08,
                   "fee_adj_edge": 0.054, "edge_bucket": "E50", "seconds_remaining": 200,
                   "yes_token_id": "y", "no_token_id": "n", "ref_price": 1, "cur_price": 1}
        snapshot = {
            "entry_price": 0.58, "entry_method": "depth_walk", "data_quality": "high",
            "signal_best_ask": 0.56, "signal_best_bid": 0.54, "signal_depth_walk_entry": 0.58,
            "signal_fee_adj_edge": 0.054, "signal_net_ev": 0.044, "signal_slippage": 0.036,
            "signal_seconds_remaining": 200, "signal_timestamp_ms": 1,
            "yes_fair": 0.64, "no_fair": 0.36, "action_fair": 0.64,
            "paper_viability": "positive_after_slippage",
        }
        import time as _t
        snapshot["signal_timestamp_ms"] = int(_t.time() * 1000)
        await pt._paper_open_worker(finding, {}, {"position_usd": 1.25}, dbp, 0.1, snapshot=snapshot)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT cohort FROM shadow_positions WHERE slug LIKE '%-5m-%'") as c:
            row = await c.fetchone()
        await conn.close()
    assert row is not None
    assert row[0] == "paper_5m", f"5m cohort='paper_5m' olmalı, bulundu {row[0]}"
    pt._active.clear()


@pytest.mark.asyncio
async def test_15m_still_paper_cohort():
    """15m normal → cohort='paper' (5m değişikliği 15m'i bozmaz)."""
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile, time as _t
    from pathlib import Path
    pt._active.clear()
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        finding = {"slug": "btc-updown-15m-999", "asset": "BTC", "action": "YES",
                   "best_ask": 0.56, "no_ask": 0.45, "fair_value": 0.64, "edge": 0.08,
                   "fee_adj_edge": 0.054, "edge_bucket": "E50", "seconds_remaining": 400,
                   "yes_token_id": "y", "no_token_id": "n", "ref_price": 1, "cur_price": 1}
        snapshot = {
            "entry_price": 0.58, "entry_method": "depth_walk", "data_quality": "high",
            "signal_best_ask": 0.56, "signal_best_bid": 0.54, "signal_depth_walk_entry": 0.58,
            "signal_fee_adj_edge": 0.054, "signal_net_ev": 0.044, "signal_slippage": 0.036,
            "signal_seconds_remaining": 400, "signal_timestamp_ms": int(_t.time()*1000),
            "yes_fair": 0.64, "no_fair": 0.36, "action_fair": 0.64,
            "paper_viability": "positive_after_slippage",
        }
        await pt._paper_open_worker(finding, {}, {"position_usd": 1.25}, dbp, 0.1, snapshot=snapshot)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT cohort FROM shadow_positions WHERE slug LIKE '%-15m-%'") as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] == "paper", f"15m cohort='paper' olmalı, bulundu {row[0]}"
    pt._active.clear()


@pytest.mark.asyncio
async def test_scan_shadow_5m_uses_low_min_seconds():
    """scan_shadow_edges 5m filtresi + düşük min_seconds ile 5m aday döndürür."""
    import council.scout as scout
    fake = {"slug": "btc-updown-5m-1", "asset": "BTC", "action": "YES",
            "fair_value": 0.64, "best_ask": 0.57, "best_bid": 0.40, "edge": 0.07,
            "seconds_remaining": 120, "taker_fee": 0.02, "no_ask": None,
            "yes_token_id": "y", "no_token_id": "n"}
    captured = {}
    async def fake_process(m, *a, **k):
        captured["min_seconds"] = k.get("min_seconds")
        return fake
    scout._markets_cache = [{"slug": "btc-updown-5m-1"}]
    scout._markets_cache_ts = 9e18
    with patch("council.scout._process_market", side_effect=fake_process), \
         patch("council.scout._get_all_vols", new_callable=AsyncMock, return_value={}), \
         patch("council.scout._get_market_state", new_callable=AsyncMock, return_value={}), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=1.0):
        out = await scout.scan_shadow_edges(min_seconds=60, tf_filter="-5m-")
    assert captured["min_seconds"] == 60, "5m taramada min_seconds=60 geçilmeli"
    assert out and out[0]["edge_bucket"] in ("E30", "E35", "E40", "E50")
    scout._markets_cache = []; scout._markets_cache_ts = 0.0
