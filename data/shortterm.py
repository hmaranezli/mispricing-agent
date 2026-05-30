"""
data/shortterm.py — Kisa vadeli BTC/ETH Up/Down market bulucu.
Slug'i o anki UTC zamanindan hesaplar, Gamma API'ye direkt sorar.
"""
import asyncio
import json
import time
import aiohttp

GAMMA = "https://gamma-api.polymarket.com/markets"


def _parse(raw):
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def slugs_for_now(assets=("btc", "eth"), interval=15, lookback=4):
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


async def fetch_by_slug(session, slug):
    try:
        async with session.get(GAMMA, params={"slug": slug}) as r:
            if r.status != 200:
                return None
            data = await r.json()
    except Exception:
        return None
    arr = data if isinstance(data, list) else data.get("data", [])
    return arr[0] if arr else None


async def find_shortterm(intervals=(5, 15, 60)):
    found = []
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        tasks = []
        for iv in intervals:
            for slug in slugs_for_now(interval=iv):
                tasks.append(fetch_by_slug(s, slug))
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
