"""
council/verifier.py — KATMAN 2: HL Drift Kontrolü.

Scout zaten CLOB gerçek zamanlı fiyatıyla edge hesapladı.
Verifier sadece şunu kontrol eder: Scout'tan bu yana HL fiyatı >%2 oynadı mı?
Oynadıysa → fair value bozulur → veto.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.hl_candles import current_price
import config

PRICE_DRIFT_HALT_PCT = 2.0  # HL fiyatı Scout'tan bu yana >%2 farklıysa → HALT


async def verify(finding: dict) -> dict:
    """
    HL drift kontrolü. Scout'un CLOB fiyatlarını pass-through eder.

    Returns:
        {pass, reason, halt, fresh_cur_price, fresh_best_ask, fresh_best_bid,
         fresh_fair, fresh_edge, fresh_seconds, hl_drift_pct}
    """
    asset     = finding["asset"]
    scout_cur = finding["cur_price"]

    if scout_cur == 0:
        return _result(False, "fetch_error", False, extra={"error": "scout_cur=0"})

    try:
        fresh_cur = await current_price(asset)
    except Exception as e:
        return _result(False, "fetch_error", False, extra={"error": str(e)})

    hl_drift = abs(fresh_cur - scout_cur) / scout_cur * 100
    if hl_drift > PRICE_DRIFT_HALT_PCT:
        return _result(False, "api_mismatch", config.HALT_ON_API_MISMATCH,
                       fresh_cur=fresh_cur, hl_drift_pct=hl_drift)

    # Scout CLOB fiyatlarını zaten kullandı — pass-through
    return _result(True, "ok", False,
                   fresh_cur=fresh_cur,
                   fresh_ask=finding["best_ask"],
                   fresh_bid=finding["best_bid"],
                   fresh_seconds=finding["seconds_remaining"],
                   fresh_fair=finding["fair_value"],
                   fresh_edge=finding["edge"],
                   hl_drift_pct=hl_drift)


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
    print("VERIFIER — Scout bulgularında HL drift kontrolü")
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
        print(f"  Scout CLOB ask : {f['best_ask']:.3f}  edge:{f['edge']:+.3f}")
        print(f"  HL drift       : {r['hl_drift_pct']:.4f}%")
        print(f"  Sonuç          : {icon}{halt}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
