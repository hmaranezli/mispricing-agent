"""
council/scout.py — KATMAN 1: Keşif Ajanı.

Edge tanımı (matematiksel):
  fair_yes = P(fiyat > referans | şimdiki, kalan_süre)  [Black-Scholes binary]

  YES ucuz → fair_yes - YES_ask > MIN_EDGE_PCT
             (HL bullish, market henüz fiyatlamamış)

  NO ucuz  → (1-fair_yes) - NO_ask > MIN_EDGE_PCT
             (HL bearish, market YES'i hâlâ yüksek fiyatlıyor)
             Pre-filter: YES_ask-fair; sonra gerçek NO_ask ile doğrula

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
from data import ws_prices as _ws_prices
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
    fair:     fair_yes değeri [0,1]
    best_ask: YES almak için ödeyeceğimiz fiyat (CLOB YES ask)
    best_bid: NO bid ≈ 1-YES_ask — yalnızca fee hesabında kullanılır, edge'de değil

    Edge hesabı (YES ve NO simetrik):
      YES edge = fair - best_ask    (fair > market → YES ucuz → AL)
      NO edge  = best_ask - fair    (market > fair → YES pahalı → NO ucuz → AL)

    İki edge toplamı her zaman sıfır → aynı anda yalnızca biri pozitif olabilir.

    Returns None (edge yok/yetersiz) veya {"action": "YES"|"NO", "edge": float}
    """
    yes_edge = fair - best_ask
    no_edge  = best_ask - fair   # ← DÜZELTİLDİ: best_bid - fair değil (formül hatası)

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

    # WS cache'den anlık fiyat al; miss veya stale ise REST fallback
    clob_ask = _ws_prices.get_ask(yes_token) if yes_token else None
    if clob_ask is None:
        clob_ask = await get_clob_price(yes_token) if yes_token else None
    if clob_ask is None:
        return None  # Likidite yok → atla

    # YES bid: WS'den gerçek değer; yoksa /price?side=SELL; son çare ask
    _raw_yes_bid = _ws_prices.get_bid(yes_token)
    if _raw_yes_bid is not None:
        yes_bid = _raw_yes_bid
    else:
        yes_bid = await get_clob_price(yes_token, "SELL") or clob_ask

    try:
        ref_price = await price_at_timestamp(asset, window["start_ms"])
        cur       = await current_price(asset)
    except (ValueError, Exception):
        return None

    fair = fair_yes(cur, ref_price, window["seconds_remaining"], asset)
    signal = _edge_signal(fair, clob_ask, yes_bid)
    if signal is None:
        return None

    # NO işlem: WS veya REST'ten gerçek NO_ask ile edge'i doğrula
    no_ask = None
    if signal["action"] == "NO" and no_token:
        no_ask = _ws_prices.get_ask(no_token)
        if no_ask is None:
            no_ask = await get_clob_price(no_token, "BUY")
        if no_ask is not None:
            real_no_edge = round((1 - fair) - no_ask, 4)
            if real_no_edge < config.MIN_EDGE_PCT:
                return None  # YES_ask tabanlı sinyal yanlış pozitif çıktı
            signal = {"action": "NO", "edge": real_no_edge}

    taker_fee = await fetch_fee_rate(yes_token) if yes_token else 0.02

    return {
        "question":          (m.get("question") or "?")[:60],
        "asset":             asset,
        "fair_value":        round(fair, 4),
        "ref_price":         ref_price,
        "cur_price":         cur,
        "best_ask":          clob_ask,    # YES entry fiyatı (CLOB ask, WS veya REST)
        "best_bid":          yes_bid,     # YES exit fiyatı (CLOB bid, WS veya approx)
        "seconds_remaining": window["seconds_remaining"],
        "edge":              round(signal["edge"], 4),
        "action":            signal["action"],
        "neg_risk":          window["neg_risk"],
        "slug":              m.get("slug", ""),
        "_window":           window,
        "_raw_market":       m,
        "yes_token_id":      yes_token,
        "no_token_id":       no_token,
        "no_ask":            no_ask,          # NO token gerçek ask (action=NO ise dolu)
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
