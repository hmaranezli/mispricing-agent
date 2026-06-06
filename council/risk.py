"""
council/risk.py — KATMAN 4: Risk Değerlendirmesi.

"Ne kadar?" sorusunu cevaplar.
Kelly fraksiyonu ile pozisyon boyutlandırır; sistem limitlerini ve
insan onayı koşullarını kontrol eder.

Saf fonksiyon — API çağrısı yok, DB bağlantısı yok.
Tüm dış durum (bankroll, açık pozisyonlar, günlük kayıp) parametre olarak gelir.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

KELLY_FRACTION   = 0.25  # Çeyrek Kelly — tam Kelly'nin 1/4'ü
MIN_POSITION_USD = 1.25  # test sabit pozisyon — Kelly floor, geçici bypass


def _kelly(action: str, fee_adj_edge: float,
           fresh_ask: float, fresh_bid: float) -> float:
    """Ham Kelly fraksiyonu. Bölme sıfırı (payda < 0.01) → 0.0."""
    if action == "YES":
        denom = 1.0 - fresh_ask
        return fee_adj_edge / denom if denom >= 0.01 else 0.0
    else:  # NO
        denom = fresh_bid
        return fee_adj_edge / denom if denom >= 0.01 else 0.0


def _result(pass_: bool, position_usd: float = 0.0, kelly_f: float = 0.0,
            requires_human_approval: bool = False,
            halt: bool = False, reason: str = "") -> dict:
    return {
        "pass":                    pass_,
        "position_usd":            round(position_usd, 2),
        "kelly_f":                 round(kelly_f, 4),
        "kelly_fraction_applied":  KELLY_FRACTION,
        "requires_human_approval": requires_human_approval,
        "halt":                    halt,
        "reason":                  reason,
    }


def risk(
    finding:        dict,
    verification:   dict,
    redteam:        dict,
    bankroll_usd:   float,
    open_positions: int,
    daily_loss_usd: float,
) -> dict:
    """
    Pozisyon boyutlandırması ve sistem limiti kontrolü.

    Args:
        finding:        Scout scan_edges() çıktısı
        verification:   Verifier verify() çıktısı (fresh_best_ask/bid buradan)
        redteam:        RedTeam redteam() çıktısı (fee_adj_edge buradan)
        bankroll_usd:   Mevcut sermaye (USD)
        open_positions: Açık pozisyon sayısı
        daily_loss_usd: Bugünkü gerçekleşmiş kayıp (USD)

    Returns:
        {pass, position_usd, kelly_f, kelly_fraction_applied,
         requires_human_approval, halt, reason}
    """
    # 1. Açık pozisyon limiti (gunluk kayip limiti circuit_breaker'a tasindi)
    if open_positions >= config.MAX_OPEN_POSITIONS:
        return _result(False, reason="max_open_positions_reached")

    # 3. Edge geçerlilik — çift emniyet (RedTeam zaten kontrol etti)
    fee_adj_edge = redteam["fee_adj_edge"]
    if fee_adj_edge < config.MIN_EDGE_PCT:
        return _result(False, reason="edge_below_minimum")

    # 4. Kelly hesabı ve minimum pozisyon
    kelly_f = _kelly(
        action=finding["action"],
        fee_adj_edge=fee_adj_edge,
        fresh_ask=verification["fresh_best_ask"],
        fresh_bid=verification["fresh_best_bid"],
    )
    # Kelly=0 → "girme" demek (payda<0.01, token fiyatı berbat). Floor BYPASS edilmemeli.
    if kelly_f <= 0:
        return _result(False, kelly_f=kelly_f, reason="kelly_zero_no_edge")
    capped_f     = min(kelly_f * KELLY_FRACTION, config.MAX_TRADE_PCT)
    position_usd = max(capped_f * bankroll_usd, MIN_POSITION_USD)  # Kelly floor: min $1.25 (yalnızca kelly>0)

    # 5. İnsan onayı bayrağı (veto değil — Gate handle eder)
    requires_human_approval = position_usd > config.HUMAN_APPROVAL_USD

    return _result(
        pass_=True,
        position_usd=position_usd,
        kelly_f=kelly_f,
        requires_human_approval=requires_human_approval,
        reason="",
    )


async def main():
    """Manuel test: Scout→Verifier→RedTeam→Risk zincirini çalıştırır."""
    import asyncio
    from council.scout import scan_edges
    from council.verifier import verify
    from council.redteam import redteam as rt

    print("=" * 70)
    print("RISK — pozisyon boyutlandırma")
    print("=" * 70)

    bankroll = getattr(config, "STARTING_CAPITAL_USD", 1000.0)

    findings = await scan_edges()
    if not findings:
        print("Scout'tan bulgu yok.")
        return

    for f in findings:
        v = await verify(f)
        if not v["pass"]:
            print(f"\n{f['question'][:50]} → Verifier: {v['reason']}")
            continue
        r = await rt(f, v)
        if not r["pass"]:
            print(f"\n{f['question'][:50]} → RedTeam veto: {r['vetoes']}")
            continue
        rk = risk(f, v, r,
                  bankroll_usd=bankroll, open_positions=0, daily_loss_usd=0.0)
        icon = "PASS" if rk["pass"] else f"VETO [{rk['reason']}]"
        print(f"\n{f['question'][:50]}")
        print(f"  Kelly (ham)   : {rk['kelly_f']:.3f}")
        print(f"  Pozisyon      : ${rk['position_usd']:.2f}")
        if rk["requires_human_approval"]:
            print("  *** İNSAN ONAYI GEREKLİ ***")
        if rk["halt"]:
            print("  *** SİSTEM DURDU — günlük kayıp limiti ***")
        print(f"  Karar         : {icon}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
