"""data/clob_price.py — CLOB anlık fiyat yardımcısı (paylaşımlı)."""
import aiohttp

CLOB_HOST = "https://clob.polymarket.com"
PRICE_TIMEOUT = 2.0  # price/book hızlı çağrı — agresif timeout (22s outlier guard)


async def get_clob_price(token_id: str, side: str = "BUY") -> float | None:
    """CLOB /price?side=BUY|SELL → token için anlık fiyat.

    BUY  → best ask (almak için ödeyeceğin)
    SELL → best bid (satmak için alacağın)
    Returns: float (>0) veya None (liquidity yok / hata).
    """
    if not token_id:
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=PRICE_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(
                f"{CLOB_HOST}/price",
                params={"token_id": token_id, "side": side},
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    p = float(data.get("price", 0))
                    return p if p > 0 else None
    except Exception:
        pass
    return None


def _book_levels(raw) -> list[tuple[float, float]]:
    """Ham book seviyelerini [(price, size)] güvenli parse eder (string/float).
    Geçersiz/sıfır seviyeler atlanır. Sıralama varsayımı YOK."""
    out = []
    for x in raw or []:
        try:
            p = float(x.get("price", 0) or 0)
            s = float(x.get("size", 0) or 0)
        except (TypeError, ValueError, AttributeError):
            continue
        if p > 0 and s > 0:
            out.append((p, s))
    return out


def sorted_asks(book: dict | None) -> list[tuple[float, float]]:
    """Ask seviyeleri ucuzdan pahalıya (best=ilk). Polymarket /book asks AZALAN gelir
    — sıralamaya güvenme, fiyata göre yeniden sırala."""
    return sorted(_book_levels((book or {}).get("asks")), key=lambda x: x[0])


def sorted_bids(book: dict | None) -> list[tuple[float, float]]:
    """Bid seviyeleri pahalıdan ucuza (best=ilk). Polymarket /book bids ARTAN gelir."""
    return sorted(_book_levels((book or {}).get("bids")), key=lambda x: x[0], reverse=True)


def best_ask_from_book(book: dict | None) -> float | None:
    """En iyi (en düşük) ask. Boş → None (fail-open)."""
    lv = _book_levels((book or {}).get("asks"))
    return min(lv, key=lambda x: x[0])[0] if lv else None


def best_bid_from_book(book: dict | None) -> float | None:
    """En iyi (en yüksek) bid. Boş → None (fail-open)."""
    lv = _book_levels((book or {}).get("bids"))
    return max(lv, key=lambda x: x[0])[0] if lv else None


async def fetch_book_snapshot(token_id: str, min_notional: float = 0.0):
    """P0 single-source REST snapshot: /book → OrderbookSnapshot (bid+ask AYNI book'tan,
    dust-filtreli). WS miss/invalid'de fallback. Frankenstein (WS+REST karışım) yasak."""
    from data.orderbook_snapshot import OrderbookSnapshot
    import time as _t
    book = await get_book(token_id)
    if not book:
        return None
    bids = sorted_bids(book)   # pahalı→ucuz, best=ilk
    asks = sorted_asks(book)   # ucuz→pahalı, best=ilk
    # dust: best seviyesi notional eşiğinin altındaysa bir alt seviyeye in (executable best)
    def _best(levels):
        for px, sz in levels:
            if min_notional <= 0 or px * sz >= min_notional:
                return px, sz
        return (None, None)
    bid, bid_sz = _best(bids)
    ask, ask_sz = _best(asks)
    return OrderbookSnapshot(bid=bid, ask=ask, bid_size=bid_sz, ask_size=ask_sz,
                             source="rest_book", ts=_t.time())


async def get_book(token_id: str) -> dict | None:
    """CLOB GET /book?token_id=<id> → tam OrderBookSummary.

    DİKKAT: Polymarket asks'ı AZALAN ([0]=en yüksek), bids'i ARTAN ([0]=en düşük)
    döndürür — yani [0] HER İKİSİNDE EN KÖTÜ. best_ask_from_book/best_bid_from_book
    veya sorted_asks/sorted_bids kullan; asks[0]/bids[0]'ı best sanma.
    Her level: {"price": "0.46", "size": "150"}
    Returns: dict veya None (hata / token yok).
    """
    if not token_id:
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=PRICE_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(
                f"{CLOB_HOST}/book",
                params={"token_id": token_id},
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    if isinstance(data, dict) and "asks" in data and "bids" in data:
                        return data
    except Exception:
        pass
    return None
