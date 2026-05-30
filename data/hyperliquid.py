"""
data/hyperliquid.py — Hyperliquid veri katmani (public, key gerekmez).
BTC/ETH icin: anlik fiyat (mid), funding rate, mark/oracle fiyat.
"""
import asyncio
import aiohttp

INFO_URL = "https://api.hyperliquid.xyz/info"


async def _post(session, payload):
    async with session.post(INFO_URL, json=payload) as r:
        r.raise_for_status()
        return await r.json()


async def fetch_market_state(assets=("BTC", "ETH")):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        # Tum perp'lerin anlik durumu (fiyat, funding, mark, oracle)
        meta = await _post(s, {"type": "metaAndAssetCtxs"})
    universe = meta[0]["universe"]
    ctxs = meta[1]
    out = {}
    for name, ctx in zip([u["name"] for u in universe], ctxs):
        if name in assets:
            out[name] = {
                "mid":     float(ctx.get("midPx") or 0),
                "mark":    float(ctx.get("markPx") or 0),
                "oracle":  float(ctx.get("oraclePx") or 0),
                "funding": float(ctx.get("funding") or 0),
                "prev_day": float(ctx.get("prevDayPx") or 0),
            }
    return out


def _signal(d):
    """Basit yon gostergesi: mark vs oracle + gunluk degisim + funding."""
    mark, oracle = d["mark"], d["oracle"]
    prem = (mark - oracle) / oracle * 100 if oracle else 0
    chg = (mark - d["prev_day"]) / d["prev_day"] * 100 if d["prev_day"] else 0
    fund = d["funding"] * 100
    bias = "YUKARI" if (prem > 0 and fund > 0) else "ASAGI" if (prem < 0 and fund < 0) else "KARISIK"
    return prem, chg, fund, bias


async def main():
    print("Hyperliquid market durumu cekiliyor...\n")
    try:
        state = await fetch_market_state()
    except Exception as e:
        print(f"HATA: {type(e).__name__}: {e}")
        return
    if not state:
        print("Veri bulunamadi.")
        return
    for asset, d in state.items():
        prem, chg, fund, bias = _signal(d)
        print(f"{asset}:")
        print(f"  Fiyat (mark): ${d['mark']:,.1f}")
        print(f"  Mark-Oracle farki: {prem:+.4f}%")
        print(f"  24s degisim: {chg:+.2f}%")
        print(f"  Funding: {fund:+.5f}%")
        print(f"  --> YON SINYALI: {bias}\n")


if __name__ == "__main__":
    asyncio.run(main())
