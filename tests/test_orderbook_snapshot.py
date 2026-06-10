"""tests/test_orderbook_snapshot.py — P0 Data Pipeline Refactor TDD.

Atomic OrderbookSnapshot + single-source + dust filter + crossed guard.
Decision logic (fair/clamp/threshold/TP) DEĞİŞMEZ — sadece fiyat snapshot kalitesi.
"""
import sys
import os
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── KURAL 1: Atomic snapshot — crossed invalid ───────────────────────────────

def test_snapshot_bid_only_crossed_invalid():
    """WS bid-only update eski ask ile crossed üretirse snapshot INVALID."""
    from data.orderbook_snapshot import OrderbookSnapshot
    # yeni bid=0.58 (güncel), ask=0.57 (eski/stale) → crossed
    snap = OrderbookSnapshot(bid=0.58, ask=0.57, bid_size=100, ask_size=100,
                             source="ws", ts=time.time())
    assert snap.is_crossed is True
    assert snap.valid() is False


def test_snapshot_ask_only_crossed_invalid():
    """WS ask-only update eski bid ile crossed üretirse snapshot INVALID."""
    from data.orderbook_snapshot import OrderbookSnapshot
    snap = OrderbookSnapshot(bid=0.50, ask=0.49, bid_size=100, ask_size=100,
                             source="ws", ts=time.time())
    assert snap.is_crossed is True
    assert snap.valid() is False


def test_snapshot_valid_non_crossed():
    """KURAL: valid non-crossed snapshot edge hesabına girebilmeli."""
    from data.orderbook_snapshot import OrderbookSnapshot
    snap = OrderbookSnapshot(bid=0.50, ask=0.54, bid_size=100, ask_size=100,
                             source="ws", ts=time.time())
    assert snap.is_crossed is False
    assert snap.valid() is True


def test_snapshot_missing_side_invalid():
    """Aynı snapshot içinde bid veya ask yoksa INVALID."""
    from data.orderbook_snapshot import OrderbookSnapshot
    assert OrderbookSnapshot(bid=0.5, ask=None, bid_size=1, ask_size=None,
                             source="ws", ts=time.time()).valid() is False
    assert OrderbookSnapshot(bid=None, ask=0.5, bid_size=None, ask_size=1,
                             source="ws", ts=time.time()).valid() is False


# ── KURAL 3: Dust/Depth filter ───────────────────────────────────────────────

def test_dust_order_top_of_book_skipped():
    """Min executable notional altındaki dust → snapshot invalid (depth-aware)."""
    from data.orderbook_snapshot import OrderbookSnapshot
    # ask_size 1 share × 0.50 = $0.50 notional < min $5 → dust → invalid
    snap = OrderbookSnapshot(bid=0.50, ask=0.54, bid_size=100, ask_size=1,
                             source="ws", ts=time.time())
    assert snap.valid(min_notional=5.0) is False
    # yeterli notional → valid
    snap2 = OrderbookSnapshot(bid=0.50, ask=0.54, bid_size=100, ask_size=100,
                              source="ws", ts=time.time())
    assert snap2.valid(min_notional=5.0) is True


def test_snapshot_stale_invalid():
    """Çok eski snapshot (age > max) invalid."""
    from data.orderbook_snapshot import OrderbookSnapshot
    snap = OrderbookSnapshot(bid=0.50, ask=0.54, bid_size=100, ask_size=100,
                             source="ws", ts=time.time() - 30)
    assert snap.valid(max_age_s=10) is False


# ── KURAL 4: Crossed guard — scout edge skip ─────────────────────────────────

def test_crossed_guard_skips_edge():
    """bid >= ask ise scout edge hesabı SKIP edilmeli (reason=crossed_orderbook)."""
    from council.scout import _crossed_orderbook_skip
    assert _crossed_orderbook_skip(yes_bid=0.58, yes_ask=0.57) == "crossed_orderbook"
    assert _crossed_orderbook_skip(yes_bid=0.54, yes_ask=0.54) == "crossed_orderbook"  # eşit de crossed
    assert _crossed_orderbook_skip(yes_bid=0.50, yes_ask=0.54) is None  # normal → geçer


# ── KURAL 2: Single source — WS get_snapshot atomik ──────────────────────────

def test_ws_get_snapshot_atomic_source():
    """WS cache'den tek atomik snapshot (source='ws'), bid+ask aynı entry'den."""
    import data.ws_prices as ws
    ws._cache.clear()
    ws._cache["TKN"] = {"best_bid": 0.50, "best_ask": 0.54, "bid_size": 100.0,
                        "ask_size": 80.0, "spread": 0.04, "ts": time.time()}
    snap = ws.get_snapshot("TKN")
    assert snap is not None
    assert snap.bid == 0.50 and snap.ask == 0.54
    assert snap.source == "ws"
    assert snap.valid() is True
    ws._cache.clear()


def test_ws_get_snapshot_crossed_invalid():
    """WS cache crossed (kısmi update) → snapshot invalid (Frankenstein engellenir)."""
    import data.ws_prices as ws
    ws._cache.clear()
    # bid yeni (0.58), ask eski (0.57) → crossed
    ws._cache["TKN"] = {"best_bid": 0.58, "best_ask": 0.57, "bid_size": 100.0,
                        "ask_size": 100.0, "spread": None, "ts": time.time()}
    snap = ws.get_snapshot("TKN")
    assert snap.is_crossed is True and snap.valid() is False
    ws._cache.clear()
