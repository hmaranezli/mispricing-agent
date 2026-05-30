"""
data/polymarket.py — Polymarket veri katmani (ADIM 1: canli fiyat cekme)
Gamma API (public, key gerekmez). Kelime-sinirli filtre + sayfalama.
"""
import asyncio
import json
import re
import aiohttp

GAMMA_URL = "https://gamma-api.polymarket.com/markets"

# Kelime-sinirli desen: "Netherlands" icindeki "ether"i YAKALAMAZ.
CRYPTO_RE = re.compile(
    r"\b(bitcoin|btc|ethereum|solana|crypto|"
    r"bitcoin's|eth/usd|btc/usd)\b", re.IGNORECASE
)


def _parse(raw):
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


async def fetch_crypto_markets(max_pages=6, page_size=500):
    out, seen = [], set()
    timeout = aiohttp.ClientTimeout(total=25)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for page in range(max_pages):
            params = {
                "active": "true", "closed": "false",
                "limit": str(page_size), "offset": str(page * page_size),
            }
            async with session.get(GAMMA_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()
            batch = data if isinstance(data, list) else data.get("data", [])
            if not batch:
                break
            for m in batch:
                q = m.get("question") or ""
                mid = m.get("id") or m.get("conditionId")
                if mid in seen:
                    continue
                if CRYPTO_RE.search(q):
                    seen.add(mid)
                    out.append(m)
    return out


def _fmt(m):
    q = (m.get("question") or "?")[:64]
    prices = _parse(m.get("outcomePrices"))
    outcomes = _parse(m.get("outcomes")) or ["YES", "NO"]
    vol = m.get("volume") or m.get("volumeNum") or 0
    if prices and len(prices) >= 2:
        ps = " | ".join(f"{o}={float(p):.3f}" for o, p in zip(outcomes, prices))
    else:
        ps = "fiyat yok"
    try:
        vs = f"${float(vol):,.0f}"
    except (ValueError, TypeError):
        vs = str(vol)
    return f"  {q:<64}  {ps:<24}  vol={vs}"


async def main():
    print("Polymarket'ten crypto marketleri cekiliyor (cok sayfa)...\n")
    try:
        markets = await fetch_crypto_markets()
    except Exception as e:
        print(f"HATA: {type(e).__name__}: {e}")
        return
    # Hacme gore sirala (en likit en ustte)
    def _v(m):
        try:
            return float(m.get("volume") or m.get("volumeNum") or 0)
        except (ValueError, TypeError):
            return 0.0
    markets.sort(key=_v, reverse=True)
    print(f"Bulunan crypto market sayisi: {len(markets)}\n")
    for m in markets[:30]:
        print(_fmt(m))
    print(f"\n... toplam {len(markets)} market (en likit 30 gosterildi).")


if __name__ == "__main__":
    asyncio.run(main())
