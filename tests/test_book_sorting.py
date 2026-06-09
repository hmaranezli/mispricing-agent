"""tests/test_book_sorting.py — Order book sorting bug fix TDD.

Polymarket /book: asks AZALAN ([0]=en yüksek), bids ARTAN ([0]=en düşük).
Yani [0] HER İKİSİNDE EN KÖTÜ. Robust: min(asks)/max(bids), sıralamaya güvenme.
"""
import asyncio
import sys
import os
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── best_ask/best_bid robust seçim ───────────────────────────────────────────

def test_best_ask_is_min_unsorted():
    from data.clob_price import best_ask_from_book
    # azalan sıralı (gerçek Polymarket): [0]=0.99 en kötü, best = 0.35
    book = {"asks": [{"price": "0.99", "size": "100"}, {"price": "0.50", "size": "10"},
                     {"price": "0.35", "size": "5"}]}
    assert best_ask_from_book(book) == 0.35


def test_best_bid_is_max_unsorted():
    from data.clob_price import best_bid_from_book
    # artan sıralı: [0]=0.01 en kötü, best = 0.34
    book = {"bids": [{"price": "0.01", "size": "100"}, {"price": "0.20", "size": "10"},
                     {"price": "0.34", "size": "5"}]}
    assert best_bid_from_book(book) == 0.34


def test_best_ask_empty_fail_open():
    from data.clob_price import best_ask_from_book
    assert best_ask_from_book({"asks": []}) is None
    assert best_ask_from_book(None) is None
    assert best_ask_from_book({}) is None


def test_best_bid_empty_fail_open():
    from data.clob_price import best_bid_from_book
    assert best_bid_from_book({"bids": []}) is None
    assert best_bid_from_book(None) is None


def test_sorted_asks_ascending():
    from data.clob_price import sorted_asks
    book = {"asks": [{"price": "0.99", "size": "1"}, {"price": "0.35", "size": "2"},
                     {"price": "0.50", "size": "3"}]}
    lv = sorted_asks(book)  # ucuz→pahalı
    prices = [p for p, s in lv]
    assert prices == [0.35, 0.50, 0.99]


def test_sorted_bids_descending():
    from data.clob_price import sorted_bids
    book = {"bids": [{"price": "0.01", "size": "1"}, {"price": "0.34", "size": "2"},
                     {"price": "0.20", "size": "3"}]}
    lv = sorted_bids(book)  # pahalı→ucuz
    prices = [p for p, s in lv]
    assert prices == [0.34, 0.20, 0.01]


def test_book_levels_safe_parse():
    """price string/float, geçersiz/sıfır seviyeler atlanır."""
    from data.clob_price import sorted_asks
    book = {"asks": [{"price": "0.50", "size": "10"}, {"price": "abc", "size": "5"},
                     {"price": "0.40", "size": "0"}, {"price": "0.30", "size": "8"}]}
    lv = sorted_asks(book)
    prices = [p for p, s in lv]
    assert prices == [0.30, 0.50]  # geçersiz ve size=0 atlandı


# ── paper entry artık 0.99 artifact üretmez ─────────────────────────────────

def test_paper_estimate_uses_cheapest_ask():
    from execution.paper_tracker import _estimate_entry_price
    # azalan asks (gerçek format): best=0.35
    book = {"asks": [{"price": "0.99", "size": "1000"}, {"price": "0.50", "size": "500"},
                     {"price": "0.35", "size": "1000"}]}
    price, method, quality, levels = _estimate_entry_price(book, position_usd=2.0)
    assert price == 0.35, f"en ucuz ask'tan başlamalı, 0.99 değil — bulundu {price}"
    assert method == "depth_walk"
    assert price != 0.99


def test_paper_estimate_depth_walk_multi_level_cheapest_first():
    from execution.paper_tracker import _estimate_entry_price
    # $1: 0.35×2=0.70 first, kalan 0.30 → 0.50'den
    book = {"asks": [{"price": "0.99", "size": "1000"}, {"price": "0.50", "size": "1000"},
                     {"price": "0.35", "size": "2"}]}
    price, method, quality, levels = _estimate_entry_price(book, position_usd=1.0)
    assert 0.35 <= price < 0.50, f"ağırlıklı ort en ucuz seviyelerden, bulundu {price}"


# ── air_pocket_shadow + shadow_quote sorted book kullanır ───────────────────

@pytest.mark.asyncio
async def test_air_pocket_uses_best_bid():
    import execution.air_pocket_shadow as aps
    aps._active = 1
    # artan bids: best bid = 0.45 (max), [0]=0.10 en kötü
    fake_book = {"bids": [{"price": "0.10", "size": "100"}, {"price": "0.45", "size": "100"}]}
    snap = dict(seq_no=1, position_id="p", slug="s", asset="BTC", action="NO",
                sl_trigger_px=0.50, mae_pct=-0.28, seconds_remaining=300, shares=2.0)
    written = {}
    async def fake_write(rec, db_path): written.update(rec)
    with patch("execution.air_pocket_shadow.get_book", new_callable=AsyncMock, return_value=fake_book), \
         patch("execution.air_pocket_shadow.asyncio.sleep", new_callable=AsyncMock), \
         patch("execution.air_pocket_shadow._write", side_effect=fake_write):
        await aps._worker(snap, current_exit_price=0.30, exit_token="t", db_path=":memory:")
    assert written.get("post_wait_bid") == 0.45, f"best bid max olmalı, bulundu {written.get('post_wait_bid')}"


@pytest.mark.asyncio
async def test_shadow_quote_uses_best_ask():
    from data.shadow_quote import _read_book
    fake_book = {"asks": [{"price": "0.99", "size": "100"}, {"price": "0.40", "size": "50"}]}
    with patch("data.shadow_quote.ws_prices") as mws, \
         patch("data.shadow_quote.get_book", new_callable=AsyncMock, return_value=fake_book):
        mws._cache = {}
        ask, age, source, top_size, levels = await _read_book("tok")
    assert ask == 0.40, f"best ask min olmalı, bulundu {ask}"
