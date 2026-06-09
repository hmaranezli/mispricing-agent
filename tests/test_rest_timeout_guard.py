"""tests/test_rest_timeout_guard.py — REST Timeout Guard TDD.

22s outlier'ın kökü: 20s ClientTimeout'lar. Hedef:
- price/book/current_price (hızlı): <= 2s
- find_shortterm/market_state/range (ağır): <= 3s
- tek scan REST budget: <= 6s
Timeout → fail-open (skip, None/[], exception yutulur, loop bloklanmaz).
"""
import asyncio
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Agresif timeout sabitleri ────────────────────────────────────────────────

def test_clob_price_timeout_fast():
    import data.clob_price as cp
    assert cp.PRICE_TIMEOUT <= 2.0, "get_clob_price/get_book timeout <= 2s olmalı"


def test_candle_timeout_fast():
    import data.hl_candles as hc
    assert hc.CANDLE_TIMEOUT <= 2.0, "fetch_candles (current_price) timeout <= 2s"


def test_range_timeout_heavy():
    import data.hl_candles as hc
    assert hc.RANGE_TIMEOUT <= 3.0, "fetch_candles_range (price_at_timestamp) timeout <= 3s"


def test_shortterm_timeout_heavy():
    import data.shortterm as st
    assert st.REST_TIMEOUT <= 3.0, "find_shortterm/fetch_by_slug timeout <= 3s"


def test_market_state_timeout_heavy():
    import data.hyperliquid as hl
    assert hl.MARKET_STATE_TIMEOUT <= 3.0, "fetch_market_state timeout <= 3s"


def test_no_20s_timeout_anywhere():
    """Hiçbir data modülünde 20s timeout kalmamalı (22s outlier kökü)."""
    import data.shortterm, data.hl_candles, data.hyperliquid
    assert data.shortterm.REST_TIMEOUT < 10
    assert data.hl_candles.CANDLE_TIMEOUT < 10
    assert data.hl_candles.RANGE_TIMEOUT < 10
    assert data.hyperliquid.MARKET_STATE_TIMEOUT < 10


def test_scan_rest_budget_under_6s():
    """Tek scan cycle ağır REST budget hedefi: en yavaş concurrent path <= 6s.

    find_shortterm + market_state concurrent değil sıralı olabilir → toplam <= 6s.
    """
    import data.shortterm as st
    import data.hyperliquid as hl
    import data.hl_candles as hc
    # en kötü sıralı: discovery + market_state (current_price concurrent gather)
    worst_sequential = st.REST_TIMEOUT + hl.MARKET_STATE_TIMEOUT
    assert worst_sequential <= 6.0, f"REST budget {worst_sequential}s > 6s hedefi"


# ── Fail-open davranışı ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_clob_price_timeout_returns_none():
    """get_clob_price timeout → None (fail-open), exception fırlatmaz."""
    import data.clob_price as cp

    class _BoomSession:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        def get(self, *a, **k):
            raise asyncio.TimeoutError("rest timeout")

    with patch("data.clob_price.aiohttp.ClientSession", _BoomSession):
        result = await cp.get_clob_price("tok", "BUY")
    assert result is None


@pytest.mark.asyncio
async def test_get_book_timeout_returns_none():
    import data.clob_price as cp

    class _BoomSession:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        def get(self, *a, **k):
            raise asyncio.TimeoutError("rest timeout")

    with patch("data.clob_price.aiohttp.ClientSession", _BoomSession):
        result = await cp.get_book("tok")
    assert result is None


@pytest.mark.asyncio
async def test_current_price_timeout_propagates_for_caller_skip():
    """current_price timeout → ValueError/Exception; çağıran (scout) yakalar→skip.
    Burada exception'ın fail-open şekilde yakalanabilir olduğunu doğrularız."""
    import data.hl_candles as hc
    with patch("data.hl_candles.fetch_candles", new_callable=AsyncMock, return_value=[]):
        with pytest.raises(ValueError):
            await hc.current_price("BTC")
    # scout gather(return_exceptions=True) bu ValueError'ı yakalar → market skip (fail-open)


@pytest.mark.asyncio
async def test_scan_edges_survives_current_price_exception():
    """scan_edges current_price exception'ında çökmez (gather return_exceptions)."""
    import council.scout as scout

    async def boom(asset):
        raise asyncio.TimeoutError("hl timeout")

    scout._markets_cache = [{"slug": "x", "question": "BTC up?"}]
    scout._markets_cache_ts = 9e18
    with patch("council.scout.current_price", side_effect=boom), \
         patch("council.scout._get_all_vols", new_callable=AsyncMock, return_value={}), \
         patch("council.scout._get_market_state", new_callable=AsyncMock, return_value={}), \
         patch("council.scout._process_market", new_callable=AsyncMock, return_value=None):
        out = await scout.scan_edges()  # çökmemeli
    assert isinstance(out, list)
    scout._markets_cache = []
    scout._markets_cache_ts = 0.0
