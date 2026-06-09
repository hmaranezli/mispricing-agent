"""
data/hl_candles.py — Hyperliquid'den GERCEK gecmis fiyat (candle) ceker.
Uydurma yok: belirli bir zaman penceresinde fiyat gercekte ne yapti, olcer.
"""
import asyncio
import math
import time
import aiohttp

INFO_URL = "https://api.hyperliquid.xyz/info"
CANDLE_TIMEOUT = 2.0  # fetch_candles (current_price) — hızlı çağrı, agresif timeout (20s→2s)
RANGE_TIMEOUT  = 3.0  # fetch_candles_range (price_at_timestamp) — ağır çağrı (20s→3s)


async def fetch_candles(asset, interval="1m", minutes_back=20):
    end = int(time.time() * 1000)
    start = end - minutes_back * 60 * 1000
    payload = {
        "type": "candleSnapshot",
        "req": {"coin": asset, "interval": interval,
                "startTime": start, "endTime": end},
    }
    timeout = aiohttp.ClientTimeout(total=CANDLE_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.post(INFO_URL, json=payload) as r:
            r.raise_for_status()
            return await r.json()


def realized_vol_raw(candles: list[dict]) -> float | None:
    """Yıllıklandırılmış realized vol — CLAMP YOK (clamp öncesi ham değer).
    Telemetri/audit içindir. Veri yetersizse None döner."""
    if not candles or len(candles) < 2:
        return None
    returns = []
    for i in range(1, len(candles)):
        prev = float(candles[i - 1]["c"])
        curr = float(candles[i]["c"])
        if prev > 0 and curr > 0:
            returns.append(math.log(curr / prev))
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(525_600)


def calculate_realized_volatility(candles: list[dict]) -> float:
    """
    Son N dakikanın 1m mumlarından yıllıklandırılmış realized volatilite.
    Formül: stdev(log_returns) * sqrt(525_600)  [1 yılda 525 600 dakika]
    Guardrail: [0.30, 3.00] — sıfır ve aşırı spike değerlerini engeller.
    Veri yetersizse 0.80 döner (BTC ortalama vol fallback).

    DAVRANIŞ KORUNDU: clamp(realized_vol_raw). Sadece raw expose edildi (telemetri için).
    """
    raw = realized_vol_raw(candles)
    if raw is None:
        return 0.80
    return max(0.30, min(raw, 3.00))


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


async def fetch_candles_range(asset: str, interval: str, start_ms: int, end_ms: int):
    """Belirli zaman aralığında mum çeker (ms epoch)."""
    payload = {
        "type": "candleSnapshot",
        "req": {"coin": asset, "interval": interval,
                "startTime": start_ms, "endTime": end_ms},
    }
    timeout = aiohttp.ClientTimeout(total=RANGE_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.post(INFO_URL, json=payload) as r:
            r.raise_for_status()
            return await r.json()


async def price_at_timestamp(asset: str, ts_ms: int) -> float:
    """
    ts_ms anındaki HL spot fiyatını döner (en yakın 1m mumun open fiyatı).
    Raises ValueError: o zaman için mum bulunamazsa.
    """
    start = ts_ms - 120_000  # 2 dk önce
    end   = ts_ms + 120_000  # 2 dk sonra
    candles = await fetch_candles_range(asset, "1m", start, end)
    if not candles:
        raise ValueError(f"{asset} için ts={ts_ms} civarında mum bulunamadı")
    closest = min(candles, key=lambda c: abs(int(c["t"]) - ts_ms))
    return float(closest["o"])


async def current_price(asset: str) -> float:
    """Şimdiki HL fiyatını döner (son 1m mumun close fiyatı)."""
    candles = await fetch_candles(asset, "1m", minutes_back=2)
    if not candles:
        raise ValueError(f"{asset} için canlı fiyat alınamadı")
    return float(candles[-1]["c"])


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
