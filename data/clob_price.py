"""data/clob_price.py — CLOB anlık fiyat yardımcısı (paylaşımlı)."""
import aiohttp

CLOB_HOST = "https://clob.polymarket.com"


async def get_clob_price(token_id: str) -> float | None:
    """CLOB /price?side=BUY → token için anlık best ask fiyatı.

    Returns: float (>0) veya None (liquidity yok / hata).
    """
    if not token_id:
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(
                f"{CLOB_HOST}/price",
                params={"token_id": token_id, "side": "BUY"},
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    p = float(data.get("price", 0))
                    return p if p > 0 else None
    except Exception:
        pass
    return None
