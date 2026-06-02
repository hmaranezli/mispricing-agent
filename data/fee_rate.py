"""data/fee_rate.py — Polymarket CLOB fee rate, 5dk TTL cache ile."""
import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import aiohttp
except ImportError:
    aiohttp = None

CLOB_HOST = "https://clob.polymarket.com"
CACHE_TTL  = 300  # 5 dakika
DEFAULT    = 0.02  # %2 fallback

_cache: dict = {}  # token_id → (fee, expires_at)


def _parse(raw) -> float:
    """base_fee (bps) → ondalık. 1000 → 0.02."""
    try:
        fee = float(raw) / 50_000
        return fee if 0.001 <= fee <= 0.20 else DEFAULT
    except (TypeError, ValueError):
        return DEFAULT


async def _fetch_from_api(token_id: str) -> float:
    if aiohttp is None:
        return DEFAULT
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{CLOB_HOST}/fee-rate/{token_id}",
            timeout=aiohttp.ClientTimeout(total=5)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return _parse(data.get("base_fee"))


async def fetch_fee_rate(token_id: str) -> float:
    """
    token_id için taker fee'yi döner. 5dk cache kullanır.
    Hata durumunda DEFAULT=%2 fallback.
    """
    now = time.monotonic()
    if token_id in _cache:
        fee, expires = _cache[token_id]
        if now < expires:
            return fee

    try:
        fee = await _fetch_from_api(token_id)
    except Exception:
        return DEFAULT

    _cache[token_id] = (fee, now + CACHE_TTL)
    return fee
