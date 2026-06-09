"""data/shadow_quote.py — Entry FAK_NO_MATCH sonrası shadow book snapshot ve fee_adj hesabı.

Hiçbir gerçek emir göndermez. "Retry geçer miydi?" sorusunu yanıtlar.
Ana execution path'i bloklamaz — await edilebilir (REST < 2s) veya
background task içinden çağrılır.
"""
import asyncio
import time

from data import ws_prices
from data.clob_price import get_book, sorted_asks

TAKER_FEE      = 0.02   # Polymarket %2 taker fee (conservative default)
ENTRY_SLIPPAGE = 0.01   # clob_executor.PRICE_PREMIUM ile eşleşiyor
REST_TIMEOUT   = 2.0    # shadow REST call maks. süresi (sn)


def _fee_adj(action: str, fair: float, ask: float, fee: float) -> float:
    """Fee ve giriş slippage sonrası gerçek edge. redteam._fee_adjusted_edge() ile aynı formül."""
    if action == "YES":
        return fair * (1 - fee) - (ask + ENTRY_SLIPPAGE)
    return (1 - fair) * (1 - fee) - (ask + ENTRY_SLIPPAGE)


async def _read_book(token_id: str) -> tuple:
    """
    Returns (ask, book_age_ms, source, top_size_usd, levels).

    Önce WS cache dener (microseconds). Miss → REST get_book() (< 2s).
    top_size_usd ve levels sadece REST'te dolu olur.
    """
    # 1. WS cache (no I/O, instant)
    entry = ws_prices._cache.get(token_id)
    if entry and entry.get("best_ask", 0) > 0:
        age_s = time.time() - entry["ts"]
        if age_s < ws_prices.STALE_SECS:
            return entry["best_ask"], round(age_s * 1000, 1), "ws_cache", None, None

    # 2. REST fallback
    try:
        book = await asyncio.wait_for(get_book(token_id), timeout=REST_TIMEOUT)
        asks = sorted_asks(book)  # ucuz→pahalı (best=ilk); asks[0]'ı best sanma
        if asks:
            ask, sz = asks[0]  # en düşük ask (best)
            if ask > 0:
                top_size = round(sz * ask, 2)
                levels   = len(asks)
                return ask, 0.0, "rest", top_size, levels
    except Exception:
        pass

    return None, None, "none", None, None


async def get_shadow_quote(
    token_id:     str,
    action:       str,
    fair:         float,
    original_ask: float,
    min_edge:     float,
    fee:          float = TAKER_FEE,
) -> dict:
    """Shadow book snapshot. WS cache veya REST'ten anlık book okur, fee_adj hesaplar.

    Args:
        token_id:     İşlem yapılmaya çalışılan token (YES için yes_token_id, NO için no_token_id).
        action:       "YES" veya "NO"
        fair:         Fair value (council değerlendirme anındaki)
        original_ask: FAK order'ının verilen ask fiyatı
        min_edge:     config.MIN_EDGE_PCT
        fee:          Taker fee oranı (default 0.02)

    Returns dict:
        ask, no_ask, book_age_ms, fee_adj, price_delta_cents,
        edge_still_passes, would_retry_passed, source, top_size, levels
    All numeric fields → None on API failure.
    """
    ask, age_ms, source, top_size, levels = await _read_book(token_id)

    null_result = {
        "ask": None, "no_ask": None, "book_age_ms": None,
        "fee_adj": None, "price_delta_cents": None,
        "edge_still_passes": None, "would_retry_passed": None,
        "source": "none", "top_size": None, "levels": None,
    }

    if ask is None:
        return null_result

    fa            = _fee_adj(action, fair, ask, fee)
    delta_cents   = round((ask - original_ask) * 100, 2)
    edge_passes   = fa >= min_edge

    return {
        "ask":              ask,
        "no_ask":           ask if action == "NO" else None,
        "book_age_ms":      age_ms,
        "fee_adj":          round(fa, 4),
        "price_delta_cents": delta_cents,
        "edge_still_passes":  edge_passes,
        "would_retry_passed": edge_passes,
        "source":             source,
        "top_size":           top_size,
        "levels":             levels,
    }
