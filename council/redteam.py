"""
council/redteam.py — KATMAN 3: Şeytan Avukatı.

"Bu işlemi neden YAPMAMALIYIZ?" sorusunu sorar.
Herhangi bir veto → pass=False. Warning'ler loglanır, bloklamaz.
"""
import asyncio
import sys
import os
import aiohttp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.shortterm import fetch_by_slug
import config

SPREAD_VETO        = 0.05   # bid-ask spread > 5 cent → veto
LIQUIDITY_VETO_USD = 500    # CLOB likidite < $500 → veto
VOLUME_WARN_USD    = 50     # 24s hacim < $50 → warning (bloklamaz)
MIN_THESIS_SECS    = 120    # < 2dk → PM yeniden fiyatlanamaz → veto
EDGE_SANITY_MAX    = 0.35   # edge > %35 → veri hatası şüphesi → veto


def _parse_taker_fee(raw) -> float:
    """Gamma takerBaseFee → ondalık oran.
    Polymarket %2 fee → takerBaseFee=1000 → 1000/50000 = 0.02.
    """
    try:
        fee = float(raw) / 50_000
        return fee if 0 < fee <= 0.20 else 0.02
    except (TypeError, ValueError):
        return 0.02


def _fee_adjusted_edge(fair: float, ask: float, bid: float,
                        action: str, fee: float) -> float:
    """
    Fee sonrası gerçek edge.
    YES: fair × (1−fee) − ask
    NO:  (1−fair) × (1−fee) − (1−bid)
    """
    if action == "YES":
        return fair * (1 - fee) - ask
    return (1 - fair) * (1 - fee) - (1 - bid)


def _result(pass_: bool, vetoes: list, warnings: list,
            fee_adj: float, taker_fee: float,
            spread: float, liquidity: float) -> dict:
    return {
        "pass":          pass_,
        "vetoes":        vetoes,
        "warnings":      warnings,
        "fee_adj_edge":  round(fee_adj, 4),
        "taker_fee":     round(taker_fee, 4),
        "spread":        spread,
        "liquidity_usd": liquidity,
    }


async def redteam(finding: dict, verification: dict) -> dict:
    """
    Bulguya karşı şeytan avukatlığı yapar.

    Args:
        finding:      Scout scan_edges() çıktısı (slug, action dahil)
        verification: Verifier verify() çıktısı (fresh_fair, fresh_edge, fresh_seconds dahil)

    Returns:
        {pass, vetoes, warnings, fee_adj_edge, taker_fee, spread, liquidity_usd}
    """
    vetoes   = []
    warnings = []

    # ── 1-2. API gerektirmeyen erken kontroller ───────────────────────────────
    if verification["fresh_edge"] > EDGE_SANITY_MAX:
        vetoes.append("edge_suspiciously_large")

    if verification["fresh_seconds"] < MIN_THESIS_SECS:
        vetoes.append("insufficient_time_for_thesis")

    # ── Gamma'dan taze market verisi ─────────────────────────────────────────
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            market = await fetch_by_slug(s, finding["slug"])
    except Exception:
        market = None

    if market is None:
        # Market verisi alınamadı — fee default ile hesapla
        taker_fee = 0.02
        fee_adj = _fee_adjusted_edge(
            fair=verification["fresh_fair"],
            ask=verification["fresh_best_ask"],
            bid=verification["fresh_best_bid"],
            action=finding["action"],
            fee=taker_fee,
        )
        if fee_adj < config.MIN_EDGE_PCT:
            vetoes.append("edge_killed_by_fee")
        vetoes.append("market_data_unavailable")
        return _result(False, vetoes, warnings, fee_adj, taker_fee, 0.0, 0.0)

    try:
        spread      = float(market.get("spread") or 999)
        liquidity   = float(market.get("liquidityClob") or 0)
        volume_24hr = float(market.get("volume24hr") or 0)
        taker_fee   = _parse_taker_fee(market.get("takerBaseFee"))
    except (TypeError, ValueError):
        return _result(False, vetoes + ["parse_error"], warnings, 0.0, 0.02, 0.0, 0.0)

    # ── 3. Spread kontrolü ────────────────────────────────────────────────────
    if spread > SPREAD_VETO:
        vetoes.append("spread_too_wide")

    # ── 4. Likidite kontrolü ─────────────────────────────────────────────────
    if liquidity < LIQUIDITY_VETO_USD:
        vetoes.append("liquidity_insufficient")

    # ── 5. Hacim uyarısı ─────────────────────────────────────────────────────
    if volume_24hr < VOLUME_WARN_USD:
        warnings.append("low_volume")

    # ── 6. Fee sonrası edge kontrolü ─────────────────────────────────────────
    fee_adj = _fee_adjusted_edge(
        fair=verification["fresh_fair"],
        ask=verification["fresh_best_ask"],
        bid=verification["fresh_best_bid"],
        action=finding["action"],
        fee=taker_fee,
    )
    if fee_adj < config.MIN_EDGE_PCT:
        vetoes.append("edge_killed_by_fee")

    return _result(len(vetoes) == 0, vetoes, warnings,
                   fee_adj, taker_fee, spread, liquidity)


async def main():
    from council.scout import scan_edges
    from council.verifier import verify
    print("=" * 70)
    print("REDTEAM — şeytan avukatı kontrolü")
    print("=" * 70)
    findings = await scan_edges()
    if not findings:
        print("Scout'tan bulgu yok.")
        return
    for f in findings:
        v = await verify(f)
        if not v["pass"]:
            print(f"\n{f['question'][:50]} → Verifier: {v['reason']}")
            continue
        r = await redteam(f, v)
        icon = "PASS" if r["pass"] else f"VETO [{', '.join(r['vetoes'])}]"
        print(f"\n{f['question'][:50]}")
        print(f"  Gross edge   : {v['fresh_edge']:+.3f}")
        print(f"  Fee-adj edge : {r['fee_adj_edge']:+.3f}  (fee: {r['taker_fee']:.1%})")
        print(f"  Spread       : {r['spread']:.3f}  |  Likidite: ${r['liquidity_usd']:,.0f}")
        if r["warnings"]:
            print(f"  Uyarılar     : {', '.join(r['warnings'])}")
        print(f"  Karar        : {icon}")


if __name__ == "__main__":
    asyncio.run(main())
