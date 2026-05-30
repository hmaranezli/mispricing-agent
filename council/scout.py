"""
council/scout.py — KATMAN 1: Kesif Ajani (GERCEK mispricing tanimi).
Edge SADECE su durumda gecerli:
  - Hyperliquid son N dk'da BELIRGIN yon gosterdi (guclu hareket)
  - Polymarket o yonu HENUZ fiyatlamadi (ters tarafta veya notrde)
Iki kaynak ayni yonu soyluyorsa -> edge YOK (hemfikirler).
Uydurma katsayi yok, order yok.
"""
import asyncio
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.shortterm import find_shortterm, _parse
from data.hl_candles import fetch_candles, realized_move
import config

# Hyperliquid hareketi bu esigi gecmezse "yon yok" sayilir (gurultu).
STRONG_MOVE_PCT = 0.10   # son penceede en az %0.10 hareket = belirgin yon


def _asset_of(q):
    q = (q or "").lower()
    if "bitcoin" in q or "btc" in q:
        return "BTC"
    if "ethereum" in q or "eth" in q:
        return "ETH"
    return None


def _interval_minutes(slug):
    m = re.search(r"-(\d+)m-", slug or "")
    return int(m.group(1)) if m else None


async def scan_edges():
    markets = await find_shortterm()
    if not markets:
        print("Polymarket marketi gelmedi.")
        return []

    candles = {}
    for asset in ("BTC", "ETH"):
        candles[asset] = await fetch_candles(asset, "1m", 20)

    findings = []
    for m in markets:
        asset = _asset_of(m.get("question"))
        if asset not in candles or not candles[asset]:
            continue
        iv = _interval_minutes(m.get("slug"))
        if iv is None:
            continue
        prices = _parse(m.get("outcomePrices"))
        if not prices or len(prices) < 2:
            continue
        pm_yes = float(prices[0])

        # FILTRE 1: cozulmus market (kenarlar) -> ele
        if pm_yes <= 0.10 or pm_yes >= 0.90:
            continue

        move = realized_move(candles[asset], iv)
        if move is None:
            continue

        # FILTRE 2: Hyperliquid belirgin yon gostermiyorsa -> edge yok
        if abs(move) < STRONG_MOVE_PCT:
            continue

        hl_direction = "UP" if move > 0 else "DOWN"

        # GERCEK mispricing testi: HL yonu ile PM fiyati ZIT mi?
        # HL UP diyor ama PM hala ucuz (yes<0.50) -> YES AL firsati
        # HL DOWN diyor ama PM hala pahali (yes>0.50) -> NO AL firsati
        edge = None
        action = None
        if hl_direction == "UP" and pm_yes < 0.50:
            edge = 0.50 - pm_yes + min(abs(move) * 2, 0.20)   # PM ne kadar geride
            action = "YES AL (HL yukari, PM ucuz)"
        elif hl_direction == "DOWN" and pm_yes > 0.50:
            edge = pm_yes - 0.50 + min(abs(move) * 2, 0.20)
            action = "NO AL (HL asagi, PM pahali)"
        else:
            # HL ve PM ayni yonde -> hemfikir -> edge yok
            continue

        findings.append({
            "question": (m.get("question") or "?")[:48],
            "asset": asset, "iv": iv, "pm_yes": pm_yes,
            "move": move, "hl_dir": hl_direction,
            "edge": edge, "action": action,
        })
    return findings


async def main():
    print("=" * 70)
    print("SCOUT — gercek mispricing taramasi (order YOK)")
    print(f"Min edge: {config.MIN_EDGE_PCT:.0%} | guclu hareket esigi: {STRONG_MOVE_PCT}%")
    print("=" * 70)
    findings = await scan_edges()
    if not findings:
        print("\nGercek mispricing yok.")
        print("(Ya piyasa sakin, ya HL ile PM hemfikir -> beklemek dogru.)")
        return
    findings.sort(key=lambda x: x["edge"], reverse=True)
    for f in findings:
        flag = "  >>> ESIK USTU" if f["edge"] >= config.MIN_EDGE_PCT else ""
        print(f"\n{f['question']}  [{f['asset']} {f['iv']}m]")
        print(f"  HL gercek {f['iv']}dk hareket: {f['move']:+.3f}%  -> {f['hl_dir']}")
        print(f"  Polymarket YES        : {f['pm_yes']:.3f}")
        print(f"  EDGE                  : {f['edge']:+.3f}{flag}")
        print(f"  Aksiyon               : {f['action']}")
    n = sum(1 for f in findings if f["edge"] >= config.MIN_EDGE_PCT)
    print("\n" + "=" * 70)
    print(f"{len(findings)} aday, {n} esik ustu. Order verilmedi.")


if __name__ == "__main__":
    asyncio.run(main())
