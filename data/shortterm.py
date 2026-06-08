"""
data/shortterm.py — Kisa vadeli BTC/ETH Up/Down market bulucu.
Slug'i o anki UTC zamanindan hesaplar, Gamma API'ye direkt sorar.
"""
import asyncio
import json
import time
import aiohttp
from datetime import datetime, timezone

GAMMA = "https://gamma-api.polymarket.com/markets"


def _parse(raw):
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _parse_token_ids(raw) -> list[str]:
    """clobTokenIds alanını her zaman list[str] döndür. JSON string veya list kabul eder."""
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        try:
            result = json.loads(raw)
            return [str(x) for x in result] if isinstance(result, list) else []
        except (json.JSONDecodeError, ValueError):
            return []
    return []


def parse_market_window(m: dict):
    """
    Ham Gamma market dict'inden scout'un ihtiyacı olan alanları çıkarır.
    Returns dict veya None (zorunlu alan eksikse).

    Dönen dict anahtarları:
      start_ms          : eventStartTime (ms epoch)
      end_ms            : endDate (ms epoch)
      seconds_remaining : endDate - now (float, negatif = geçmiş)
      best_bid          : YES token bestBid (float)
      best_ask          : YES token bestAsk (float)
      neg_risk          : bool
    """
    try:
        start_str = m.get("eventStartTime") or m.get("startDate")
        end_str   = m.get("endDate")
        best_ask  = m.get("bestAsk")
        best_bid  = m.get("bestBid")

        if not start_str or not end_str or best_ask is None or best_bid is None:
            return None

        def _parse_dt(s):
            return datetime.fromisoformat(s.rstrip("Z")).replace(tzinfo=timezone.utc)

        start_dt = _parse_dt(start_str)
        end_dt   = _parse_dt(end_str)
        now      = datetime.now(timezone.utc)

        return {
            "start_ms":          int(start_dt.timestamp() * 1000),
            "end_ms":            int(end_dt.timestamp() * 1000),
            "seconds_remaining": (end_dt - now).total_seconds(),
            "best_bid":          float(best_bid),
            "best_ask":          float(best_ask),
            "neg_risk":          bool(m.get("negRisk", False)),
        }
    except (ValueError, TypeError, AttributeError):
        return None


def slugs_for_now(assets=("btc", "eth", "sol", "xrp"), interval=15, lookback=7):
    """Su an ve son birkac periyodun slug'larini uretir."""
    now = int(time.time())
    step = interval * 60
    base = (now // step) * step
    out = []
    for asset in assets:
        for i in range(lookback):
            ts = base - i * step
            out.append(f"{asset}-updown-{interval}m-{ts}")
    return out


async def _fetch_slug(session, slug):
    """Paylaşılan session ile tek slug sorgular (find_shortterm içi)."""
    try:
        async with session.get(GAMMA, params={"slug": slug}) as r:
            if r.status != 200:
                return None
            data = await r.json()
    except Exception:
        return None
    arr = data if isinstance(data, list) else data.get("data", [])
    return arr[0] if arr else None


async def fetch_by_slug(slug):
    """Tek slug için bağımsız sorgu — main_loop._monitor_positions kullanır."""
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        return await _fetch_slug(s, slug)


def _parse_resolution(market: dict) -> dict | None:
    """Market dict'inden YES/NO resolution fiyatlarını çıkarır."""
    import json as _json
    try:
        prices = _json.loads(market["outcomePrices"])
        return {"yes_exit": float(prices[0]), "no_exit": float(prices[1])}
    except (KeyError, IndexError, ValueError, TypeError):
        return None


async def fetch_resolved(slug: str) -> dict | None:
    """Kapanmış market için resolution fiyatlarını döndürür.

    Returns: {"yes_exit": float, "no_exit": float} veya None
    """
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        try:
            async with s.get(GAMMA, params={"slug": slug, "closed": "true"}) as r:
                if r.status != 200:
                    return None
                data = await r.json()
        except Exception:
            return None
    arr = data if isinstance(data, list) else data.get("data", [])
    if not arr:
        return None
    return _parse_resolution(arr[0])


def slugs_for_now_4h(
    assets=("btc", "eth", "sol", "xrp", "bnb", "doge"),
    lookback=3,
):
    """4h pencere slug'ları üretir. Format: {asset}-updown-4h-{unix_ts}"""
    now  = int(time.time())
    step = 4 * 3600  # 14400s
    base = (now // step) * step
    out  = []
    for asset in assets:
        for i in range(lookback):
            ts = base - i * step
            out.append(f"{asset}-updown-4h-{ts}")
    return out


async def find_shortterm_4h(
    assets=("btc", "eth", "sol", "xrp", "bnb", "doge"),
    lookback=3,
):
    """4h Up/Down marketleri çeker. Shadow scan içindir — canlı trade'e gitmez."""
    found   = []
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        tasks   = [_fetch_slug(s, slug) for slug in slugs_for_now_4h(assets, lookback)]
        results = await asyncio.gather(*tasks)
    for m in results:
        if m:
            found.append(m)
    return found


async def find_shortterm(intervals=(5, 15, 60)):
    found = []
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        tasks = []
        for iv in intervals:
            lb = 2 if iv == 5 else 7  # 5dk: yalnızca 2 pencere geriye bak (MIN_SECONDS=300 nedeniyle çoğu zaten filtrelenir)
            for slug in slugs_for_now(interval=iv, lookback=lb):
                tasks.append(_fetch_slug(s, slug))
        results = await asyncio.gather(*tasks)
    for m in results:
        if m:
            found.append(m)
    return found


async def main():
    print("Kisa vadeli BTC/ETH Up/Down marketleri araniyor...\n")
    markets = await find_shortterm()
    if not markets:
        print("Su an aktif kisa vadeli market bulunamadi (slug formati degismis olabilir).")
        print("Ornek denenen slug'lar:")
        for s in slugs_for_now()[:4]:
            print("   ", s)
        return
    print(f"Bulundu: {len(markets)} kisa vadeli market\n")
    for m in markets:
        q = (m.get("question") or "?")[:55]
        prices = _parse(m.get("outcomePrices"))
        ps = " | ".join(f"{float(p):.3f}" for p in prices) if prices else "?"
        print(f"  {q:<55}  [{ps}]  slug={m.get('slug','?')}")


if __name__ == "__main__":
    asyncio.run(main())
