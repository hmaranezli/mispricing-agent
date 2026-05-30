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
MIN_POSITION_USD = 5.0   # Bu altı → fee'ye değmez → veto


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
    return _result(False, reason="not_implemented")
