"""
council/redteam.py — KATMAN 3: Şeytan Avukatı.

"Bu işlemi neden YAPMAMALIYIZ?" sorusunu sorar.
Herhangi bir veto → pass=False. Warning'ler loglanır, bloklamaz.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.shortterm import fetch_by_slug
from data.clob_price import get_book
import config

SPREAD_VETO        = 0.05   # bid-ask spread > 5 cent → veto
LIQUIDITY_VETO_USD = 500    # CLOB likidite < $500 → veto
VOLUME_WARN_USD    = 50     # 24s hacim < $50 → warning (bloklamaz)
MIN_THESIS_SECS    = 120    # < 2dk → PM yeniden fiyatlanamaz → veto
EDGE_SANITY_MAX    = 0.35   # edge > %35 → veri hatası şüphesi → veto
MIN_BOOK_DEPTH_USD = 5.0    # En iyi ask level'ında min $5 USD derinlik — ince kitapta exit slippage %40'a çıkıyor
ENTRY_SLIPPAGE     = 0.01   # clob_executor.PRICE_PREMIUM=0.01 ile eşleşiyor.
BASIS_VETO_PCT     = 0.003  # |perp_mid − oracle| / oracle > 0.3% → perp spot'tan kopuk, PM oracle'da resolves
FUNDING_RATE_VETO  = 0.0001 # |funding/saat| > 0.01%/saat → kalabalık kaldıraç, perp spot'u yanıltıyor


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
                        action: str, fee: float,
                        no_ask: float | None = None,
                        slippage: float = ENTRY_SLIPPAGE) -> float:
    """
    Fee VE giriş slippage sonrası gerçek edge.
    Gerçek giriş maliyeti = ask + slippage (FAK worst_price = ask + PRICE_PREMIUM).
    YES: fair × (1−fee) − (ask + slippage)
    NO:  (1−fair) × (1−fee) − (entry + slippage)
         entry = no_ask (Scout'tan gerçek NO ask, varsa) veya 1−bid (fallback)
    """
    if action == "YES":
        return fair * (1 - fee) - (ask + slippage)
    entry = no_ask if no_ask is not None else (1 - bid)
    return (1 - fair) * (1 - fee) - (entry + slippage)


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

    # ── 1c. Spot/Perp basis ve funding rate (Scout'tan, 0 ekstra API) ─────────
    basis_pct    = finding.get("basis_pct")
    funding_rate = finding.get("funding_rate")
    if basis_pct is not None and abs(basis_pct) > BASIS_VETO_PCT:
        vetoes.append("high_basis_risk")
    if funding_rate is not None and abs(funding_rate) > FUNDING_RATE_VETO:
        vetoes.append("funding_rate_crowded")

    # ── Gamma'dan taze market verisi ─────────────────────────────────────────
    try:
        market = await fetch_by_slug(finding["slug"])
    except Exception:
        market = None

    # PM fetch başarısız → Scout'un cached _raw_market'i fallback
    if market is None:
        market = finding.get("_raw_market")

    if market is None:
        # Hiçbir kaynak yok — fee default ile hesapla
        taker_fee = 0.02
        fee_adj = _fee_adjusted_edge(
            fair=verification["fresh_fair"],
            ask=verification["fresh_best_ask"],
            bid=verification["fresh_best_bid"],
            action=finding["action"],
            fee=taker_fee,
            no_ask=finding.get("no_ask"),
        )
        if fee_adj < config.MIN_EDGE_PCT:
            vetoes.append("edge_killed_by_fee")
        vetoes.append("market_data_unavailable")
        return _result(False, vetoes, warnings, fee_adj, taker_fee, 0.0, 0.0)

    try:
        spread      = float(market.get("spread") or 999)
        liquidity   = float(market.get("liquidityClob") or 0)
        volume_24hr = float(market.get("volume24hr") or 0)
        # Scout seviyesinde çekilmiş fee — Gamma bağımlılığı azaldı
        taker_fee   = finding.get("taker_fee") or _parse_taker_fee(market.get("takerBaseFee"))
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

    # ── 4b. CLOB book derinliği ve spread ────────────────────────────────────
    action_token = (finding.get("no_token_id") if finding.get("action") == "NO"
                    else finding.get("yes_token_id"))
    book = await get_book(action_token) if action_token else None
    if book:
        asks = book.get("asks") or []
        bids = book.get("bids") or []
        # Polymarket /book: asks descending (0.99→best), bids ascending (0.01→best)
        # Best ask = asks[-1] (cheapest seller), best bid = bids[-1] (highest buyer)
        if asks:
            best_ask = asks[-1]
            depth_usd = float(best_ask.get("size", 0)) * float(best_ask.get("price", 0))
            if depth_usd < MIN_BOOK_DEPTH_USD:
                vetoes.append("book_too_thin")
        if asks and bids:
            clob_spread = float(asks[-1]["price"]) - float(bids[-1]["price"])
            if clob_spread > SPREAD_VETO:
                vetoes.append("clob_spread_too_wide")

    # ── 6. Fee sonrası edge kontrolü ─────────────────────────────────────────
    fee_adj = _fee_adjusted_edge(
        fair=verification["fresh_fair"],
        ask=verification["fresh_best_ask"],
        bid=verification["fresh_best_bid"],
        action=finding["action"],
        fee=taker_fee,
        no_ask=finding.get("no_ask"),
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
