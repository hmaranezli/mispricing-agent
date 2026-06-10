"""tests/test_live_exec_lineage.py — Faz 1: live execution path /price-ters → QuoteProvider.

5 /price-ters (position_store/clob_executor/main_loop) → get_quote book-derived explicit bid/ask.
Entry→ask, exit/mark→bid. /price (get_clob_price) kritik yoldan ÇIKAR. live=0, canlı emir yok.
"""
import sys
import os
import inspect
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 1. Entry → ask invariant (clob_executor.execute book-derived ask)
def test_clob_executor_entry_uses_quote_ask():
    import execution.clob_executor as ce
    src = inspect.getsource(ce.execute)
    assert "get_clob_price" not in src, "entry'de /price (get_clob_price) kalmamalı"
    assert "get_quote" in src, "entry get_quote kullanmalı"
    assert ".ask" in src, "entry AL→ask kullanmalı"


# 2. Exit → bid invariant (position_store.sell_position book-derived bid)
def test_position_store_exit_uses_quote_bid():
    import execution.position_store as ps
    src = inspect.getsource(ps.sell_position)
    assert "get_clob_price" not in src, "exit'te /price kalmamalı"
    assert "get_quote" in src, "exit get_quote kullanmalı"
    assert ".bid" in src, "exit SAT→bid kullanmalı"


# 3. main_loop monitor mark-to-market → bid (+ NO complement YES ask)
def test_main_loop_monitor_no_clob_price():
    import main_loop
    src = inspect.getsource(main_loop._monitor_positions)
    assert "get_clob_price" not in src, "live monitor'da /price kalmamalı"
    assert "get_quote" in src, "live monitor get_quote kullanmalı"


# 4. Critical path birleşik: get_clob_price = 0
def test_live_exec_critical_path_no_clob_price():
    import execution.clob_executor as ce
    import execution.position_store as ps
    import main_loop
    combined = (inspect.getsource(ce.execute)
                + inspect.getsource(ps.sell_position)
                + inspect.getsource(main_loop._monitor_positions))
    assert combined.count("get_clob_price") == 0, "live execution critical path'te /price KALMAMALI"


# 5. get_quote book-derived (side kelimesi değil) — regression
@pytest.mark.asyncio
async def test_get_quote_is_book_derived_not_side():
    from data.clob_price import get_quote
    from unittest.mock import AsyncMock, patch
    book = {"asks": [{"price": "0.55", "size": "1000"}], "bids": [{"price": "0.50", "size": "1000"}]}
    with patch("data.clob_price.get_book", new_callable=AsyncMock, return_value=book), \
         patch("data.ws_prices.get_snapshot", return_value=None):
        q = await get_quote("TKN")
    assert q.ask == 0.55 and q.bid == 0.50  # AL→ask, SAT→bid book-derived
