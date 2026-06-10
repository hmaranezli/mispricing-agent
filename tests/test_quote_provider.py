"""tests/test_quote_provider.py — QuoteProvider abstraction (P0 /price-ters fix).

/price kritik karar/PnL/MFE/MAE yolundan ÇIKARILDI. Tek quote abstraction (get_quote):
WS_BOOK veya REST_BOOK; explicit bid/ask (SAT→bid, AL→ask); BUY/SELL kelimesine güvenilmez.
"""
import sys
import os
import time
import inspect
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 2. /book-derived quote: best_ask=min(asks), best_bid=max(bids)
@pytest.mark.asyncio
async def test_get_quote_rest_book_derived():
    from data.clob_price import get_quote
    book = {"asks": [{"price": "0.67", "size": "1000"}, {"price": "0.99", "size": "5"}],
            "bids": [{"price": "0.66", "size": "1000"}, {"price": "0.01", "size": "5"}]}
    with patch("data.clob_price.get_book", new_callable=AsyncMock, return_value=book), \
         patch("data.ws_prices.get_snapshot", return_value=None):
        q = await get_quote("TKN")
    assert q is not None and q.source == "rest_book"
    assert q.ask == 0.67 and q.bid == 0.66  # min ask, max bid (NOT /price side)


# get_quote: WS valid → WS (single source, REST'e düşmez)
@pytest.mark.asyncio
async def test_get_quote_prefers_valid_ws():
    from data.clob_price import get_quote
    import data.ws_prices as ws
    ws._cache.clear()
    ws._cache["TKN"] = {"best_bid": 0.50, "best_ask": 0.54, "bid_size": 1e4,
                        "ask_size": 1e4, "spread": 0.04, "ts": time.time()}
    with patch("data.clob_price.fetch_book_snapshot", new_callable=AsyncMock) as mock_rest:
        q = await get_quote("TKN", min_notional=5.0)
    assert q.source == "ws" and q.ask == 0.54 and q.bid == 0.50
    mock_rest.assert_not_called()  # WS valid → REST'e düşme
    ws._cache.clear()


# get_quote: WS crossed/invalid → REST book fallback
@pytest.mark.asyncio
async def test_get_quote_ws_crossed_falls_to_rest():
    from data.clob_price import get_quote
    import data.ws_prices as ws
    ws._cache.clear()
    ws._cache["TKN"] = {"best_bid": 0.58, "best_ask": 0.57, "bid_size": 1e4,  # crossed
                        "ask_size": 1e4, "spread": None, "ts": time.time()}
    book = {"asks": [{"price": "0.60", "size": "1000"}], "bids": [{"price": "0.59", "size": "1000"}]}
    with patch("data.clob_price.get_book", new_callable=AsyncMock, return_value=book):
        q = await get_quote("TKN")
    assert q.source == "rest_book" and q.ask == 0.60 and q.bid == 0.59
    ws._cache.clear()


# 7. Paper exit SAT tarafı → BID kullanır (get_clob_price SELL=ask DEĞİL)
@pytest.mark.asyncio
async def test_paper_exit_uses_bid_quote():
    """Exit (pozisyon satışı) action-side BID ile. /price SELL (=ask, optimistic) YASAK."""
    import execution.paper_tracker as pt
    from data.orderbook_snapshot import OrderbookSnapshot
    snap = OrderbookSnapshot(bid=0.62, ask=0.65, bid_size=1e4, ask_size=1e4,
                             source="rest_book", ts=time.time())
    with patch("data.clob_price.get_quote", new_callable=AsyncMock, return_value=snap):
        px = await pt._exit_quote_price("TKN")
    assert px == 0.62  # BID (sat tarafı), 0.65 (ask) DEĞİL


# 9. Kritik yolda /price (get_clob_price) kullanımı YOK
def test_no_clob_price_in_critical_path():
    """scout decision + paper exit/mfe yolunda get_clob_price (/price) kalmamalı."""
    import council.scout as scout
    import execution.paper_tracker as pt
    # scout: clob_ask/yes_bid/no_ask quote'tan (get_clob_price kritik yolda değil)
    src = inspect.getsource(scout._process_market)
    assert "get_clob_price" not in src, "scout._process_market'ta /price kalmamalı"
    # paper exit quote helper /price kullanmamalı
    assert "get_clob_price" not in inspect.getsource(pt._exit_quote_price)


# 10. Pre-patch open paper → invalidated_api_contract
@pytest.mark.asyncio
async def test_pre_patch_open_paper_invalidated():
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn)
        await conn.execute("""INSERT INTO shadow_positions
            (paper_id, slug, asset, action, status, resolve_exit, mfe_mae_time_valid, created_at)
            VALUES ('pre1','s','BTC','YES','open',0.5,1,'t')""")
        await conn.commit(); await conn.close()
        n = await pt.invalidate_pre_patch_open_paper(dbp)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT status, close_reason, resolve_exit, mfe_mae_time_valid, mfe_mae_time_invalid_reason FROM shadow_positions WHERE paper_id='pre1'") as c:
            row = await c.fetchone()
        await conn.close()
    assert n == 1
    assert row[0] == "closed" and row[1] == "invalidated_api_contract"
    assert row[2] is None and row[3] == 0
    assert row[4] == "pre_quote_provider_api_contract_bug"
