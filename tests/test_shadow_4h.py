"""tests/test_shadow_4h.py — 4h shadow universe TDD.

Kapsam:
- slugs_for_now_4h() format doğrulaması
- find_shortterm_4h() HTTP mock
- shadow_candidates schema yeni kolonlar
- log_shadow_candidate() yeni paramlar
- _shadow_4h_scan_loop hiçbir zaman execute'a gitmesin
"""
import asyncio
import re
import sys
import os
import json
import aiosqlite
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import AsyncMock, MagicMock, patch


# ── slugs_for_now_4h ────────────────────────────────────────────────────────

def test_slugs_for_now_4h_format():
    """Slug formatı: {asset}-updown-4h-{unix_ts}, asla 4m veya 240m olmamalı."""
    from data.shortterm import slugs_for_now_4h
    slugs = slugs_for_now_4h(assets=("btc",), lookback=3)
    assert len(slugs) == 3
    for s in slugs:
        assert re.match(r"^btc-updown-4h-\d+$", s), f"Yanlış format: {s}"
        assert "4m" not in s, f"'4m' olmamalı: {s}"
        assert "240m" not in s, f"'240m' olmamalı: {s}"


def test_slugs_for_now_4h_boundary():
    """Timestamp 4 saatlik sınırda (14400s modulo 0)."""
    from data.shortterm import slugs_for_now_4h
    slugs = slugs_for_now_4h(assets=("eth",), lookback=1)
    ts = int(slugs[0].split("-")[-1])
    assert ts % (4 * 3600) == 0, f"4h sınırı değil: {ts}"


def test_slugs_for_now_4h_lookback_decreasing():
    """Lookback arttıkça timestamp azalmalı (geçmişe gidiyoruz)."""
    from data.shortterm import slugs_for_now_4h
    slugs = slugs_for_now_4h(assets=("btc",), lookback=3)
    ts_list = [int(s.split("-")[-1]) for s in slugs]
    assert ts_list[0] > ts_list[1] > ts_list[2]
    assert ts_list[0] - ts_list[1] == 4 * 3600
    assert ts_list[1] - ts_list[2] == 4 * 3600


def test_slugs_for_now_4h_multi_asset():
    """6 asset × lookback=2 = 12 slug."""
    from data.shortterm import slugs_for_now_4h
    slugs = slugs_for_now_4h(
        assets=("btc", "eth", "sol", "xrp", "bnb", "doge"),
        lookback=2,
    )
    assert len(slugs) == 12
    assets_found = {s.split("-")[0] for s in slugs}
    assert assets_found == {"btc", "eth", "sol", "xrp", "bnb", "doge"}


# ── find_shortterm_4h ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_shortterm_4h_returns_found_markets():
    """HTTP mock: 1 market bulunur, 1 None (miss) → 1 döner."""
    from data.shortterm import slugs_for_now_4h

    fake_market = {
        "slug": "btc-updown-4h-1780934400",
        "question": "Will BTC be higher?",
        "bestAsk": "0.52",
        "bestBid": "0.48",
        "eventStartTime": "2026-06-08T16:00:00Z",
        "endDate": "2026-06-08T20:00:00Z",
        "negRisk": False,
        "outcomePrices": '["0.52","0.48"]',
        "liquidityNum": 18457,
        "clobTokenIds": '["tok1","tok2"]',
    }

    async def fake_fetch_slug(session, slug):
        # Zaman-bağımsız: herhangi bir btc 4h slug'ına yanıt ver
        if "btc" in slug and "updown-4h" in slug:
            return {**fake_market, "slug": slug}
        return None

    with patch("data.shortterm._fetch_slug", side_effect=fake_fetch_slug):
        from data.shortterm import find_shortterm_4h
        markets = await find_shortterm_4h(assets=("btc", "eth"), lookback=1)

    assert len(markets) == 1
    assert markets[0]["slug"].startswith("btc-updown-4h-")


@pytest.mark.asyncio
async def test_find_shortterm_4h_returns_empty_on_no_match():
    """HTTP miss → boş liste."""
    with patch("data.shortterm._fetch_slug", return_value=None):
        from data.shortterm import find_shortterm_4h
        markets = await find_shortterm_4h(assets=("bnb",), lookback=2)
    assert markets == []


# ── shadow_candidates schema ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_shadow_candidates_has_new_columns():
    """Migrasyon sonrası 5 yeni kolon mevcut olmalı."""
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    async with conn.execute("PRAGMA table_info(shadow_candidates)") as cur:
        cols = {row[1] for row in await cur.fetchall()}
    await conn.close()
    for col in ("timeframe", "trade_enabled", "fee_adj_edge", "liquidity_usd", "spread"):
        assert col in cols, f"Kolon eksik: {col}"


# ── log_shadow_candidate yeni paramlar ─────────────────────────────────────

@pytest.mark.asyncio
async def test_log_shadow_candidate_stores_4h_fields():
    """timeframe, trade_enabled, fee_adj_edge, liquidity_usd, spread DB'ye yazılmalı."""
    from db.schema import init_schema
    from db.logger import log_shadow_candidate

    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)

    finding = {
        "slug":              "btc-updown-4h-1780934400",
        "asset":             "BTC",
        "action":            "YES",
        "fair_value":        0.58,
        "best_ask":          0.52,
        "edge":              0.06,
        "seconds_remaining": 12000,
    }

    await log_shadow_candidate(
        conn, finding, passed=False,
        timeframe="4h",
        trade_enabled=0,
        fee_adj_edge=0.041,
        liquidity_usd=18457.0,
        spread=-0.0,
    )

    async with conn.execute(
        "SELECT timeframe, trade_enabled, fee_adj_edge, liquidity_usd, spread "
        "FROM shadow_candidates WHERE slug=?",
        ("btc-updown-4h-1780934400",),
    ) as cur:
        row = await cur.fetchone()

    await conn.close()
    assert row is not None
    assert row[0] == "4h"
    assert row[1] == 0          # trade_enabled=False
    assert abs(row[2] - 0.041) < 1e-6
    assert abs(row[3] - 18457.0) < 1e-3
    assert row[4] is not None   # spread yazıldı


@pytest.mark.asyncio
async def test_log_shadow_candidate_existing_calls_unaffected():
    """Eski çağrı tarzı (timeframe/trade_enabled yok) → trade_enabled=1, timeframe=NULL."""
    from db.schema import init_schema
    from db.logger import log_shadow_candidate

    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)

    finding = {
        "slug": "btc-updown-15m-1780941600", "asset": "BTC",
        "action": "YES", "fair_value": 0.55, "best_ask": 0.50,
        "edge": 0.05, "seconds_remaining": 300,
    }
    await log_shadow_candidate(conn, finding, passed=False, veto_layer="redteam",
                               veto_reason="edge_killed_by_fee")

    async with conn.execute(
        "SELECT timeframe, trade_enabled FROM shadow_candidates WHERE slug=?",
        ("btc-updown-15m-1780941600",),
    ) as cur:
        row = await cur.fetchone()
    await conn.close()

    assert row[0] is None    # timeframe yok → NULL
    assert row[1] == 1       # trade_enabled DEFAULT 1


# ── 60m çıkarma ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_edges_does_not_use_60m():
    """scan_edges() artık 60m interval kullanmamalı.
    find_shortterm'e geçilen interval listesinde 60 olmamalı."""
    captured_intervals = []

    async def mock_find_shortterm(intervals=(5, 15)):
        captured_intervals.extend(intervals)
        return []

    with patch("council.scout.find_shortterm", side_effect=mock_find_shortterm), \
         patch("council.scout._get_all_vols", return_value={}), \
         patch("council.scout._get_market_state", return_value={}), \
         patch("council.scout.current_price", return_value=50000.0):
        from council.scout import scan_edges
        import council.scout as _scout_mod
        _scout_mod._markets_cache = []
        _scout_mod._markets_cache_ts = 0.0
        await scan_edges()

    assert 60 not in captured_intervals, f"60m hâlâ kullanılıyor: {captured_intervals}"
    assert 5 in captured_intervals
    assert 15 in captured_intervals


# ── _shadow_4h_scan_loop execute'a asla gitmemeli ───────────────────────────

@pytest.mark.asyncio
async def test_shadow_4h_loop_never_calls_execute():
    """4h shadow scan execute()/clob_executor'a asla erişmemeli."""
    execute_called = []

    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)

    fake_market = {
        "slug": "btc-updown-4h-1780934400",
        "question": "Will BTC go up?",
        "bestAsk": "0.52", "bestBid": "0.48",
        "eventStartTime": "2026-06-08T16:00:00Z",
        "endDate": "2026-06-08T20:00:00Z",
        "negRisk": False,
        "outcomePrices": '["0.52","0.48"]',
        "liquidityNum": 18000,
        "clobTokenIds": '["tok1","tok2"]',
    }

    with patch("data.shortterm.find_shortterm_4h", return_value=[fake_market]), \
         patch("data.hl_candles.price_at_timestamp", return_value=70000.0), \
         patch("data.hl_candles.current_price", return_value=70500.0), \
         patch("data.fair_value.fair_yes", return_value=0.58), \
         patch("execution.clob_executor.execute", side_effect=lambda *a, **k: execute_called.append(1)):
        from main_loop import _run_shadow_4h_scan
        await _run_shadow_4h_scan(conn)

    await conn.close()
    assert not execute_called, "4h shadow scan execute'a bağlandı — YASAK"


@pytest.mark.asyncio
async def test_shadow_4h_scan_writes_trade_enabled_false():
    """4h shadow scan her zaman trade_enabled=0 yazar."""
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)

    from datetime import datetime, timezone, timedelta
    _now = datetime.now(timezone.utc)
    fake_market = {
        "slug": "eth-updown-4h-1780934400",
        "question": "Will ETH go up?",
        "bestAsk": "0.51", "bestBid": "0.49",
        # Dinamik: pencere şu an açık (zaman-bağımsız test) — _4H_MIN_SECS geçer
        "eventStartTime": (_now - timedelta(hours=1)).isoformat(),
        "endDate": (_now + timedelta(hours=3)).isoformat(),
        "negRisk": False,
        "outcomePrices": '["0.51","0.49"]',
        "liquidityNum": 4900,
        "clobTokenIds": '["tok3","tok4"]',
    }

    with patch("data.shortterm.find_shortterm_4h", new_callable=AsyncMock, return_value=[fake_market]), \
         patch("main_loop.find_shortterm_4h", new_callable=AsyncMock, return_value=[fake_market]), \
         patch("main_loop.price_at_timestamp", new_callable=AsyncMock, return_value=3000.0), \
         patch("main_loop.current_price", new_callable=AsyncMock, return_value=3020.0), \
         patch("main_loop.fair_yes", return_value=0.56):
        from main_loop import _run_shadow_4h_scan
        await _run_shadow_4h_scan(conn)

    async with conn.execute(
        "SELECT trade_enabled, timeframe FROM shadow_candidates WHERE slug LIKE '%4h%'"
    ) as cur:
        rows = await cur.fetchall()
    await conn.close()

    assert rows, "4h shadow kaydı DB'ye yazılmadı"
    for row in rows:
        assert row[0] == 0,    f"trade_enabled=0 olmalı, {row[0]} bulundu"
        assert row[1] == "4h", f"timeframe='4h' olmalı, {row[1]} bulundu"
