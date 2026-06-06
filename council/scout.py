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
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.shortterm import find_shortterm, parse_market_window, _parse_token_ids
from data.hl_candles import price_at_timestamp, current_price, fetch_candles, calculate_realized_volatility
from data.fair_value import fair_yes, ASSET_VOL
from data.fee_rate import fetch_fee_rate
from data.clob_price import get_clob_price
from data.hyperliquid import fetch_market_state
from data import ws_prices as _ws_prices
import config

MIN_SECONDS          = 300   # Çözüme bu kadar saniyeden az kalmışsa atla (gamma trap önlemi)
MAX_ENTRY_PRICE      = 0.75  # 0.65→0.75: reversal koruması korunur, daha fazla işlem
CONVICTION_MIN       = 0.58  # Aldığımız tarafın fair'i ≥ bu olmalı. Win-rate ≈ ortalama fair.
                              # Düşük-fair/yüksek-edge (örn fair=0.40) işlemler +EV ama %40 win → atla.
ENTRY_DRIFT_MAX      = 0.003 # HL ref'ten bu kadar yanlış yönde ise giriş engelle (%0.3)
MARKET_CACHE_TTL_SECS = 60.0   # Market listesi REST API'den bu sıklıkla yenilenir
VOL_CACHE_TTL_SECS    = 300.0  # Realized vol 5 dk cache — 4 varlık × 5 dk = az API çağrısı

# ── Modül düzey cache'ler ─────────────────────────────────────────────────────
_markets_cache:    list[dict]       = []
_markets_cache_ts: float            = 0.0
_vol_cache:        dict[str, float] = {}
_vol_cache_ts:     float            = 0.0
_market_state_cache:    dict[str, dict] = {}
_market_state_cache_ts: float           = 0.0


async def _get_all_vols() -> dict[str, float]:
    """Her tracked asset için realized vol çeker — VOL_CACHE_TTL_SECS cache ile.
    Paralel çekme: 4 varlık eşzamanlı → yaklaşık tek çağrı süresi kadar bekler.
    API hatasında asset'in ASSET_VOL sabit değerine düşer.
    """
    global _vol_cache, _vol_cache_ts
    now = time.time()
    if (now - _vol_cache_ts) < VOL_CACHE_TTL_SECS and _vol_cache:
        return _vol_cache

    async def _fetch_one(asset: str) -> tuple[str, float]:
        try:
            candles = await fetch_candles(asset, "1m", 60)
            return asset, calculate_realized_volatility(candles)
        except Exception:
            return asset, ASSET_VOL.get(asset, 0.80)

    pairs = await asyncio.gather(*[_fetch_one(a) for a in config.TRACKED_ASSETS])
    _vol_cache = dict(pairs)
    _vol_cache_ts = now
    return _vol_cache


async def _get_market_state() -> dict[str, dict]:
    """Her asset için oracle_px, funding_rate, basis_pct — VOL_CACHE_TTL_SECS cache.
    fetch_market_state() tek API çağrısıyla tüm varlıkları döner → 0 ekstra maliyet.
    API hatasında boş dict — RedTeam None kontrolüyle güvenle atlatır.
    """
    global _market_state_cache, _market_state_cache_ts
    now = time.time()
    if (now - _market_state_cache_ts) < VOL_CACHE_TTL_SECS and _market_state_cache:
        return _market_state_cache
    try:
        raw = await fetch_market_state(tuple(config.TRACKED_ASSETS))
        _market_state_cache = {
            asset: {
                "oracle_px":    d["oracle"],
                "funding_rate": d["funding"],
                "basis_pct":    abs(d["mid"] - d["oracle"]) / d["oracle"]
                                if d["oracle"] > 0 else 0.0,
            }
            for asset, d in raw.items()
        }
        _market_state_cache_ts = now
    except Exception:
        pass
    return _market_state_cache


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


def _drift_ok(action: str, cur: float, ref_price: float) -> bool:
    """Entry filter: HL zaten yanlış yönde güçlü hareket etmişse giriş engelle.

    ETH NO trajedisinin kökü: HL ref'in üzerindeyken NO açıldı — scout anında
    sinyal vardı ama konsey ~5-10s sonra execute etti; o sürede HL daha da
    yukarı gitti. Bu filtre yanlış-yön entryleri scout seviyesinde keser.

    drift = (cur - ref_price) / ref_price
    NO için: drift > ENTRY_DRIFT_MAX → HL bullish, NO yanlış yön → False
    YES için: drift < -ENTRY_DRIFT_MAX → HL bearish, YES yanlış yön → False
    """
    drift = (cur - ref_price) / ref_price
    if action == "NO"  and drift >  ENTRY_DRIFT_MAX: return False
    if action == "YES" and drift < -ENTRY_DRIFT_MAX: return False
    return True


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

    # Konviksiyon filtresi: aldığımız tarafın kazanma olasılığı (fair) yeterince yüksek olmalı.
    # Win-rate ≈ ortalama fair. Düşük-fair işlem +EV olsa da %40 win → kayıp serisi → almayız.
    if yes_edge >= config.MIN_EDGE_PCT:
        if fair < CONVICTION_MIN:          # YES alıyoruz → kazanma olasılığı = fair
            return None
        return {"action": "YES", "edge": yes_edge}
    if no_edge >= config.MIN_EDGE_PCT:
        if (1 - fair) < CONVICTION_MIN:    # NO alıyoruz → kazanma olasılığı = 1 - fair
            return None
        return {"action": "NO", "edge": no_edge}
    return None


async def _process_market(m: dict, asset_vols: dict[str, float],
                           market_state: dict[str, dict] | None = None) -> dict | None:
    """Tek marketi değerlendirir. Edge yoksa veya veri eksikse None."""
    asset = _asset_of(m.get("question", ""))
    if asset is None:
        return None

    if asset not in config.TRACKED_ASSETS:
        return None

    ms = (market_state or {}).get(asset, {})

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

    live_vol = asset_vols.get(asset, 0.80)
    fair = fair_yes(cur, ref_price, window["seconds_remaining"], asset, live_vol)
    signal = _edge_signal(fair, clob_ask, yes_bid)
    if signal is None:
        return None

    # Max entry fiyatı filtresi: pahalı tokenlar reversal'da çok zararlı
    entry_price = clob_ask if signal["action"] == "YES" else None
    if signal["action"] == "NO" and no_token:
        pass  # no_ask aşağıda hesaplanacak — filtre orada uygulanır
    elif entry_price is not None and entry_price > MAX_ENTRY_PRICE:
        return None

    # NO işlem: WS veya REST'ten gerçek NO_ask ile edge'i doğrula
    no_ask = None
    if signal["action"] == "NO" and no_token:
        no_ask = _ws_prices.get_ask(no_token)
        if no_ask is None:
            no_ask = await get_clob_price(no_token, "BUY")
        if no_ask is not None:
            if no_ask > MAX_ENTRY_PRICE:
                return None  # pahalı NO token → reversal riski yüksek
            real_no_edge = round((1 - fair) - no_ask, 4)
            if real_no_edge < config.MIN_EDGE_PCT:
                return None  # YES_ask tabanlı sinyal yanlış pozitif çıktı
            signal = {"action": "NO", "edge": real_no_edge}

    # Entry filter: HL ref'ten yanlış yönde güçlü hareket → giriş engelle
    if not _drift_ok(signal["action"], cur, ref_price):
        return None

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
        "oracle_px":         ms.get("oracle_px"),
        "funding_rate":      ms.get("funding_rate"),
        "basis_pct":         ms.get("basis_pct"),
    }


async def scan_edges() -> list[dict]:
    """Tüm kısa vadeli marketleri tarar, gerçek edge olanları döner.
    Market listesi MARKET_CACHE_TTL_SECS (60s), vol hesabı VOL_CACHE_TTL_SECS (5dk)
    cache'li — REST API yükü minimize, fiyat taraması WS cache ile anlık.
    """
    global _markets_cache, _markets_cache_ts
    now = time.time()
    if (now - _markets_cache_ts) > MARKET_CACHE_TTL_SECS or not _markets_cache:
        fresh = await find_shortterm()
        _markets_cache = fresh or []
        _markets_cache_ts = now

    if not _markets_cache:
        return []

    asset_vols   = await _get_all_vols()
    market_state = await _get_market_state()
    tasks = [_process_market(m, asset_vols, market_state) for m in _markets_cache]
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
