"""
council/scout.py — KATMAN 1: Keşif Ajanı.

Edge tanımı (matematiksel):
  fair_yes = P(fiyat > referans | şimdiki, kalan_süre)  [Black-Scholes binary]
  YES ucuz → fair_yes - best_ask > MIN_EDGE_PCT
  NO ucuz  → best_bid - fair_yes > MIN_EDGE_PCT

Referans fiyat: PM penceresinin eventStartTime'ındaki HL fiyatı.
PM fiyatı: Gamma CLOB'dan bestAsk/bestBid (gerçek zamanlı).
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.shortterm import find_shortterm, parse_market_window, _parse_token_ids
from data.hl_candles import price_at_timestamp, current_price
from data.fair_value import fair_yes
from data.fee_rate import fetch_fee_rate
from data.clob_price import get_clob_price
import config

MIN_SECONDS = 180  # Çözüme bu kadar saniyeden az kalmışsa atla (RedTeam 120s eşiği + 60s buffer)


def _asset_of(question) -> str | None:
    q = (question or "").lower()
    if "bitcoin" in q or "btc" in q:
        return "BTC"
    if "ethereum" in q or "eth" in q:
        return "ETH"
    if "solana" in q or "sol" in q:
        return "SOL"
    if "ripple" in q or "xrp" in q:
        return "XRP"
    return None


def _edge_signal(fair: float, best_ask: float, best_bid: float) -> dict | None:
    """
    fair: fair_yes değeri [0,1]
    best_ask: YES almak için ödeyeceğimiz fiyat
    best_bid: YES satmak için alacağımız fiyat

    Edge hesabı:
      YES edge = fair - best_ask         (YES ucuzsa pozitif)
      NO edge  = best_bid - fair         (NO ucuzsa pozitif; fair_no=1-fair, no_ask=1-best_bid)

    Returns None (edge yok/yetersiz) veya {"action": "YES"|"NO", "edge": float}
    """
    yes_edge = fair - best_ask
    no_edge  = best_bid - fair

    if yes_edge >= config.MIN_EDGE_PCT:
        return {"action": "YES", "edge": yes_edge}
    if no_edge >= config.MIN_EDGE_PCT:
        return {"action": "NO", "edge": no_edge}
    return None


async def _process_market(m: dict) -> dict | None:
    """Tek marketi değerlendirir. Edge yoksa veya veri eksikse None."""
    asset = _asset_of(m.get("question", ""))
    if asset is None:
        return None

    if asset not in config.TRACKED_ASSETS:
        return None

    window = parse_market_window(m)
    if window is None:
        return None

    if window["neg_risk"]:
        return None

    if window["seconds_remaining"] < MIN_SECONDS:
        return None

    _tids = _parse_token_ids(m.get("clobTokenIds"))
    yes_token = _tids[0] if _tids else None
    no_token  = _tids[1] if len(_tids) > 1 else None

    # CLOB gerçek zamanlı fiyat — market API bestAsk stale olduğundan kullanmıyoruz
    clob_yes = await get_clob_price(yes_token) if yes_token else None
    if clob_yes is None:
        return None  # CLOB likidite yok → atla

    clob_ask = clob_yes                    # YES almak için ödeyeceğimiz fiyat
    clob_bid = max(0.0, 1.0 - clob_yes)   # YES satmak için alacağımız fiyat (binary approximation)

    try:
        ref_price = await price_at_timestamp(asset, window["start_ms"])
        cur       = await current_price(asset)
    except (ValueError, Exception):
        return None

    fair = fair_yes(cur, ref_price, window["seconds_remaining"], asset)
    signal = _edge_signal(fair, clob_ask, clob_bid)
    if signal is None:
        return None

    taker_fee = await fetch_fee_rate(yes_token) if yes_token else 0.02

    return {
        "question":          (m.get("question") or "?")[:60],
        "asset":             asset,
        "fair_value":        round(fair, 4),
        "ref_price":         ref_price,
        "cur_price":         cur,
        "best_ask":          clob_ask,       # CLOB gerçek fiyat (market API değil)
        "best_bid":          clob_bid,       # 1 - clob_yes approximation
        "seconds_remaining": window["seconds_remaining"],
        "edge":              round(signal["edge"], 4),
        "action":            signal["action"],
        "neg_risk":          window["neg_risk"],
        "slug":              m.get("slug", ""),
        "_window":           window,
        "_raw_market":       m,
        "yes_token_id":      yes_token,
        "no_token_id":       no_token,
        "taker_fee":         taker_fee,
    }


async def scan_edges() -> list[dict]:
    """Tüm kısa vadeli marketleri tarar, gerçek edge olanları döner."""
    markets = await find_shortterm()
    if not markets:
        return []

    tasks = [_process_market(m) for m in markets]
    results = await asyncio.gather(*tasks)

    findings = [r for r in results if r is not None]
    findings.sort(key=lambda x: x["edge"], reverse=True)
    return findings


async def main():
    print("=" * 70)
    print("SCOUT — gerçek fair value mispricing taraması (order YOK)")
    print(f"Min edge: {config.MIN_EDGE_PCT:.0%} | Min kalan süre: {MIN_SECONDS}s")
    print("=" * 70)

    findings = await scan_edges()
    if not findings:
        print("\nGerçek mispricing yok.")
        print("(Piyasa sakin veya PM fair value'yu zaten yansıtıyor.)")
        return

    for f in findings:
        print(f"\n{f['question']}  [{f['asset']}]")
        print(f"  Referans fiyat (pencere açılışı) : ${f['ref_price']:,.2f}")
        print(f"  Şimdiki fiyat (HL live)          : ${f['cur_price']:,.2f}")
        print(f"  Fair YES değeri                  : {f['fair_value']:.3f}")
        print(f"  CLOB ask / bid                   : {f['best_ask']:.3f} / {f['best_bid']:.3f}")
        print(f"  EDGE                             : {f['edge']:+.3f}  >>> EŞİK ÜSTÜ")
        print(f"  Kalan süre                       : {f['seconds_remaining']:.0f}s")
        print(f"  Aksiyon                          : {f['action']} AL")

    print("\n" + "=" * 70)
    print(f"{len(findings)} eşik üstü bulgu. Order verilmedi (DRY_RUN={config.DRY_RUN}).")


if __name__ == "__main__":
    asyncio.run(main())
