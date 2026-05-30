"""
tests/test_shortterm.py — data/shortterm.py testleri.
parse_market_window unit testleri + gerçek API integration testleri.
"""
import asyncio
import time
import pytest
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.shortterm import find_shortterm, parse_market_window, _parse

# ── _parse unit testleri ──────────────────────────────────────────────────────

def test_parse_list():
    assert _parse(["0.6", "0.4"]) == ["0.6", "0.4"]


def test_parse_json_string():
    assert _parse('["0.6","0.4"]') == ["0.6", "0.4"]


def test_parse_invalid():
    assert _parse("gecersiz") is None


def test_parse_none():
    assert _parse(None) is None


# ── parse_market_window unit testleri ────────────────────────────────────────

def test_parse_market_window_full():
    """Tüm alanlar dolu market dict'inden doğru çıkarım."""
    raw = {
        "eventStartTime": "2026-05-30T04:30:00Z",
        "endDate":        "2026-05-30T04:35:00Z",
        "bestBid":        0.48,
        "bestAsk":        0.52,
        "negRisk":        False,
        "question":       "Bitcoin Up or Down - May 30, 4:30AM-4:35AM ET",
    }
    w = parse_market_window(raw)
    assert w is not None
    expected_start = int(datetime(2026, 5, 30, 4, 30, 0, tzinfo=timezone.utc).timestamp() * 1000)
    expected_end   = int(datetime(2026, 5, 30, 4, 35, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert w["start_ms"] == expected_start
    assert w["end_ms"]   == expected_end
    assert w["best_bid"] == 0.48
    assert w["best_ask"] == 0.52
    assert w["neg_risk"] is False


def test_parse_market_window_seconds_remaining_future():
    """Gelecekteki bir market için seconds_remaining > 0."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    end_dt = now + timedelta(minutes=5)
    raw = {
        "eventStartTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate":        end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bestBid": 0.50, "bestAsk": 0.51, "negRisk": False,
    }
    w = parse_market_window(raw)
    assert w is not None
    assert w["seconds_remaining"] > 0


def test_parse_market_window_seconds_remaining_past():
    """Geçmişteki bir market için seconds_remaining < 0."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    end_dt = now - timedelta(minutes=5)
    start_dt = now - timedelta(minutes=10)
    raw = {
        "eventStartTime": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate":        end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bestBid": 0.50, "bestAsk": 0.51, "negRisk": False,
    }
    w = parse_market_window(raw)
    assert w is not None
    assert w["seconds_remaining"] < 0


def test_parse_market_window_missing_event_start_returns_none():
    """eventStartTime yoksa None döner."""
    raw = {
        "endDate": "2026-05-30T04:35:00Z",
        "bestBid": 0.48, "bestAsk": 0.52, "negRisk": False,
    }
    assert parse_market_window(raw) is None


def test_parse_market_window_missing_best_ask_returns_none():
    """bestAsk yoksa None döner."""
    raw = {
        "eventStartTime": "2026-05-30T04:30:00Z",
        "endDate":        "2026-05-30T04:35:00Z",
        "bestBid": 0.48,
    }
    assert parse_market_window(raw) is None


def test_parse_market_window_missing_end_date_returns_none():
    """endDate yoksa None döner."""
    raw = {
        "eventStartTime": "2026-05-30T04:30:00Z",
        "bestBid": 0.48, "bestAsk": 0.52,
    }
    assert parse_market_window(raw) is None


def test_parse_market_window_neg_risk_true():
    """negRisk=True doğru parse edilir."""
    raw = {
        "eventStartTime": "2026-05-30T04:30:00Z",
        "endDate":        "2026-05-30T04:35:00Z",
        "bestBid": 0.48, "bestAsk": 0.52,
        "negRisk": True,
    }
    w = parse_market_window(raw)
    assert w is not None
    assert w["neg_risk"] is True


def test_parse_market_window_neg_risk_defaults_false():
    """negRisk alanı yoksa False varsayılır."""
    raw = {
        "eventStartTime": "2026-05-30T04:30:00Z",
        "endDate":        "2026-05-30T04:35:00Z",
        "bestBid": 0.48, "bestAsk": 0.52,
    }
    w = parse_market_window(raw)
    assert w is not None
    assert w["neg_risk"] is False


# ── Integration: gerçek API ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_shortterm_returns_list():
    markets = await find_shortterm()
    assert isinstance(markets, list)


@pytest.mark.asyncio
async def test_find_shortterm_parse_market_window_works():
    """Dönen marketlerde parse_market_window çalışıyor (None dönmeyenlerde alanlar var)."""
    markets = await find_shortterm()
    for m in markets:
        w = parse_market_window(m)
        if w is None:
            continue  # bazı marketlerde eksik alan olabilir
        assert "start_ms" in w
        assert "end_ms" in w
        assert "best_bid" in w
        assert "best_ask" in w
        assert isinstance(w["neg_risk"], bool)


# ── Market kapsamı ────────────────────────────────────────────────────────────

def test_slugs_cover_all_four_assets():
    """slugs_for_now her interval için btc/eth/sol/xrp içermeli."""
    from data.shortterm import slugs_for_now
    for iv in [5, 15, 60]:
        slugs = slugs_for_now(interval=iv)
        slug_str = " ".join(slugs)
        for asset in ["btc", "eth", "sol", "xrp"]:
            assert asset in slug_str, f"{asset} interval={iv}m slug listesinde yok"


def test_slugs_lookback_at_least_7():
    """Her asset için en az 7 pencere sorgulanmalı."""
    from data.shortterm import slugs_for_now
    slugs = slugs_for_now(assets=("btc",), interval=15)
    assert len(slugs) >= 7, f"Lookback yetersiz: {len(slugs)} slug (min 7 bekleniyor)"


def test_total_slug_count_80_plus():
    """4 asset × 3 interval × 7 lookback = 84 slug — 80+ hedefine ulaşmış olmalı."""
    from data.shortterm import slugs_for_now
    total = sum(
        len(slugs_for_now(assets=("btc", "eth", "sol", "xrp"), interval=iv))
        for iv in [5, 15, 60]
    )
    assert total >= 80, f"Toplam slug sayısı yetersiz: {total} (min 80 bekleniyor)"
