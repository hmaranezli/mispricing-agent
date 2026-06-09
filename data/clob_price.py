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


async def get_book(token_id: str) -> dict | None:
    """CLOB GET /book?token_id=<id> → tam OrderBookSummary.

    bids: fiyata göre azalan (bids[0] = en iyi bid)
    asks: fiyata göre artan (asks[0] = en iyi ask)
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
