"""
council/verifier.py — KATMAN 2: Bağımsız Doğrulayıcı.

Scout bulgusunu CLOB gerçek zamanlı fiyatıyla teyit eder.
  - CLOB /price ile edge yeniden hesaplanır (market API değil)
  - Soft fail: edge_gone, expired, fetch_error  → halt=False
  - Hard fail: HL drift anomalisi               → halt=HALT_ON_API_MISMATCH
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.hl_candles import current_price
from data.shortterm import fetch_by_slug, parse_market_window
from data.fair_value import fair_yes
from data.clob_price import get_clob_price
import config

PRICE_DRIFT_HALT_PCT = 2.0    # HL fiyatı Scout'tan bu yana >%2 farklıysa → HALT
PM_DRIFT_HALT        = 0.10   # Bilgi amaçlı — artık blocking değil
MIN_SECONDS          = 60     # Çözüme <60s kaldıysa → expired


async def verify(finding: dict) -> dict:
    """
    Scout bulgusunu bağımsız CLOB fiyatıyla doğrular.

    Returns:
        {pass, reason, halt, fresh_cur_price, fresh_best_ask, fresh_best_bid,
         fresh_fair, fresh_edge, fresh_seconds, hl_drift_pct, pm_drift}
    """
    asset     = finding["asset"]
    slug      = finding["slug"]
    scout_cur = finding["cur_price"]
    scout_ask = finding["best_ask"]
    ref_price = finding["ref_price"]
    action    = finding["action"]

    # ── 1. HL taze fiyat ──────────────────────────────────────────────────────
    try:
        fresh_cur = await current_price(asset)
    except Exception as e:
        return _result(False, "fetch_error", False, extra={"error": str(e)})

    # ── 2. HL drift kontrolü ─────────────────────────────────────────────────
    hl_drift = abs(fresh_cur - scout_cur) / scout_cur * 100
    if hl_drift > PRICE_DRIFT_HALT_PCT:
        return _result(False, "api_mismatch", config.HALT_ON_API_MISMATCH,
                       fresh_cur=fresh_cur, hl_drift_pct=hl_drift)

    # ── 3. CLOB gerçek zamanlı fiyat ─────────────────────────────────────────
    # YES action → YES token fiyatı; NO action → NO token fiyatı
    token_id = finding.get("yes_token_id") if action == "YES" else finding.get("no_token_id")
    clob_price = await get_clob_price(token_id) if token_id else None

    if not clob_price:
        return _result(False, "edge_gone", False,
                       fresh_cur=fresh_cur, hl_drift_pct=hl_drift,
                       extra={"clob_reason": "no_clob_liquidity"})

    # CLOB fiyatını YES frame'ine çevir (verifier formülüyle uyumlu)
    if action == "YES":
        fresh_ask = clob_price               # YES ask
        fresh_bid = max(0.0, clob_price - 0.01)
    else:
        fresh_bid = max(0.0, 1.0 - clob_price)   # YES bid = 1 - NO ask
        fresh_ask = min(1.0, fresh_bid + 0.01)

    # pm_drift: bilgi amaçlı (artık blocking değil — market API vs CLOB farklı sistemler)
    pm_drift = abs(clob_price - scout_ask)

    # ── 4. Süre kontrolü ─────────────────────────────────────────────────────
    fresh_seconds = None
    try:
        market = await fetch_by_slug(slug)
        if market is not None:
            window = parse_market_window(market)
            if window is not None:
                fresh_seconds = window["seconds_remaining"]
    except Exception:
        pass

    if fresh_seconds is None:
        w = finding.get("_window")
        fresh_seconds = w["seconds_remaining"] if w else 0.0

    if fresh_seconds < MIN_SECONDS:
        return _result(False, "expired", False,
                       fresh_cur=fresh_cur, fresh_ask=fresh_ask,
                       fresh_bid=fresh_bid, fresh_seconds=fresh_seconds,
                       hl_drift_pct=hl_drift, pm_drift=pm_drift)

    # ── 5. Fair value + edge (CLOB fiyatıyla) ────────────────────────────────
    fresh_fair = fair_yes(fresh_cur, ref_price, fresh_seconds, asset)
    fresh_edge = (fresh_fair - fresh_ask) if action == "YES" else (fresh_bid - fresh_fair)

    # ── 6. Edge kontrolü ─────────────────────────────────────────────────────
    if fresh_edge < config.MIN_EDGE_PCT:
        return _result(False, "edge_gone", False,
                       fresh_cur=fresh_cur, fresh_ask=fresh_ask,
                       fresh_bid=fresh_bid, fresh_seconds=fresh_seconds,
                       fresh_fair=fresh_fair, fresh_edge=fresh_edge,
                       hl_drift_pct=hl_drift, pm_drift=pm_drift)

    # ── 7. PASS ───────────────────────────────────────────────────────────────
    return _result(True, "ok", False,
                   fresh_cur=fresh_cur, fresh_ask=fresh_ask,
                   fresh_bid=fresh_bid, fresh_seconds=fresh_seconds,
                   fresh_fair=fresh_fair, fresh_edge=fresh_edge,
                   hl_drift_pct=hl_drift, pm_drift=pm_drift)


def _result(pass_: bool, reason: str, halt: bool, *,
            fresh_cur: float = 0.0, fresh_ask: float = 0.0,
            fresh_bid: float = 0.0, fresh_seconds: float = 0.0,
            fresh_fair: float = 0.0, fresh_edge: float = 0.0,
            hl_drift_pct: float = 0.0, pm_drift: float = 0.0,
            extra: dict = None) -> dict:
    r = {
        "pass":            pass_,
        "reason":          reason,
        "halt":            halt,
        "fresh_cur_price": fresh_cur,
        "fresh_best_ask":  fresh_ask,
        "fresh_best_bid":  fresh_bid,
        "fresh_fair":      fresh_fair,
        "fresh_edge":      round(fresh_edge, 4),
        "fresh_seconds":   fresh_seconds,
        "hl_drift_pct":    round(hl_drift_pct, 4),
        "pm_drift":        round(pm_drift, 4),
    }
    if extra:
        r.update(extra)
    return r


async def main():
    from council.scout import scan_edges
    print("=" * 70)
    print("VERIFIER — Scout bulgularını CLOB fiyatıyla teyit ediyor")
    print("=" * 70)
    findings = await scan_edges()
    if not findings:
        print("Scout'tan bulgu gelmedi.")
        return
    for f in findings:
        r = await verify(f)
        icon = "PASS" if r["pass"] else f"FAIL [{r['reason']}]"
        halt = " *** HALT ***" if r["halt"] else ""
        print(f"\n{f['question'][:55]}")
        print(f"  Scout edge : {f['edge']:+.3f}  ask:{f['best_ask']:.3f}")
        print(f"  CLOB ask   : {r['fresh_best_ask']:.3f}  edge:{r['fresh_edge']:+.3f}")
        print(f"  HL drift   : {r['hl_drift_pct']:.4f}%  |  PM drift: {r['pm_drift']:.4f}")
        print(f"  Sonuç      : {icon}{halt}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
