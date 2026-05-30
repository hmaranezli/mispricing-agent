"""
data/hl_candles.py — Hyperliquid'den GERCEK gecmis fiyat (candle) ceker.
Uydurma yok: belirli bir zaman penceresinde fiyat gercekte ne yapti, olcer.
"""
import asyncio
import time
import aiohttp

INFO_URL = "https://api.hyperliquid.xyz/info"


async def fetch_candles(asset, interval="1m", minutes_back=20):
    end = int(time.time() * 1000)
    start = end - minutes_back * 60 * 1000
    payload = {
        "type": "candleSnapshot",
        "req": {"coin": asset, "interval": interval,
                "startTime": start, "endTime": end},
    }
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.post(INFO_URL, json=payload) as r:
            r.raise_for_status()
            return await r.json()


def realized_move(candles, window_minutes):
    """Son 'window_minutes' dakikada fiyat GERCEKTE % kac degisti."""
    if not candles or len(candles) < 2:
        return None
    recent = candles[-window_minutes:] if len(candles) >= window_minutes else candles
    open_px = float(recent[0]["o"])
    close_px = float(recent[-1]["c"])
    if open_px == 0:
        return None
    return (close_px - open_px) / open_px * 100.0


async def main():
    for asset in ("BTC", "ETH"):
        candles = await fetch_candles(asset, "1m", 20)
        if not candles:
            print(f"{asset}: veri gelmedi")
            continue
        m5 = realized_move(candles, 5)
        m15 = realized_move(candles, 15)
        last = float(candles[-1]["c"])
        print(f"{asset}: fiyat ${last:,.1f}")
        print(f"  son 5 dk GERCEK degisim : {m5:+.3f}%" if m5 is not None else "  5dk: yok")
        print(f"  son 15 dk GERCEK degisim: {m15:+.3f}%" if m15 is not None else "  15dk: yok")
        print(f"  cekilen mum sayisi: {len(candles)}\n")


if __name__ == "__main__":
    asyncio.run(main())
