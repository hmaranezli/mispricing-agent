"""
tests/test_hl_candles.py — data/hl_candles.py testleri.
Mevcut fonksiyonlar için regresyon + yeni fonksiyonlar için integration.
Gerçek API kullanılır — mock yok.
"""
import asyncio
import time
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.hl_candles import fetch_candles, realized_move, price_at_timestamp, current_price

# ── Mevcut fonksiyonlar (regresyon) ─────────────────────────────────────────

def test_realized_move_empty():
    assert realized_move([], 5) is None


def test_realized_move_single_candle():
    assert realized_move([{"o": "100", "c": "100"}], 5) is None


def test_realized_move_calculates_pct():
    candles = [{"o": "100", "c": "101"}, {"o": "101", "c": "103"}]
    result = realized_move(candles, 5)
    assert result is not None
    assert abs(result - 3.0) < 0.01  # (103-100)/100*100 = 3%


def test_realized_move_negative():
    candles = [{"o": "100", "c": "99"}, {"o": "99", "c": "98"}]
    result = realized_move(candles, 5)
    assert result is not None
    assert result < 0


def test_realized_move_zero_open_returns_none():
    candles = [{"o": "0", "c": "100"}, {"o": "100", "c": "101"}]
    assert realized_move(candles, 5) is None


# ── Yeni fonksiyonlar (gerçek API) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_current_price_btc_is_positive():
    price = await current_price("BTC")
    assert isinstance(price, float)
    assert price > 1_000  # BTC en az $1000


@pytest.mark.asyncio
async def test_current_price_eth_is_positive():
    price = await current_price("ETH")
    assert isinstance(price, float)
    assert price > 100  # ETH en az $100


@pytest.mark.asyncio
async def test_price_at_timestamp_5min_ago():
    """5 dakika önceki fiyat gerçek ve pozitif döner."""
    ts_ms = int(time.time() * 1000) - 5 * 60 * 1000
    price = await price_at_timestamp("BTC", ts_ms)
    assert isinstance(price, float)
    assert price > 1_000


@pytest.mark.asyncio
async def test_price_at_timestamp_close_to_current():
    """1 dakika önceki fiyat şimdikine yakın (±%5 içinde)."""
    ts_ms = int(time.time() * 1000) - 60_000
    past = await price_at_timestamp("BTC", ts_ms)
    now = await current_price("BTC")
    pct_diff = abs(past - now) / now * 100
    assert pct_diff < 5.0


@pytest.mark.asyncio
async def test_price_at_timestamp_too_old_raises():
    """8 günden eski timestamp için ValueError fırlatır."""
    ts_ms = int(time.time() * 1000) - 8 * 24 * 60 * 60 * 1000
    with pytest.raises(ValueError, match="mum bulunamadı"):
        await price_at_timestamp("BTC", ts_ms)
