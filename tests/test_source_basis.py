"""tests/test_source_basis.py — offline HL-vs-Chainlink basis validation (TDD).

F1a DOĞRULANMIŞ confounder: bot fair_value Hyperliquid mark/mid kullanıyor, PM Up/Down ise Chainlink
BTC/USD data stream ile resolve oluyor (end ≥ start ⇒ Up). İki kaynak farklıysa HL-temelli yön kararı
PM çözümünden SAPABİLİR → sahte edge. Bu modül o sapmayı OFFLINE sayısallaştırır.

EN KARAR-İLGİLİ metrik: directional_disagreement_rate — her Up/Down penceresinde HL'nin verdiği yön
(hl_end ≥ hl_start ⇒ Up) ile Chainlink'in verdiği yön (cl_end ≥ cl_start ⇒ Up) FARKLI olduğu pencere
oranı. Yüksek oran = HL-temelli edge, Chainlink resolution'a göre kurgusal.

SAF fonksiyon: iki seriyi GİRDİ alır (canlı fetch YOK); gerçek Chainlink serisi doldurma ayrı onaylı
adım. PM kuralı (≥ ⇒ Up, tie Up'a) her iki kaynağa simetrik uygulanır. İlk RED: modül YOK → ImportError.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_directional_disagreement_rate_counts_sign_flips():
    """HL yönü ile Chainlink yönü farklı olan pencere oranı. PM kuralı: end ≥ start ⇒ Up.
    İlk RED: analysis.source_basis YOK → ImportError (feature missing). Canlı fetch YOK; seriler enjekte."""
    from analysis.source_basis import directional_disagreement_rate

    windows = [
        # HL Up (101≥100) ama Chainlink Down (99<100) → DISAGREE (sahte edge senaryosu)
        {"hl_start": 100.0, "hl_end": 101.0, "cl_start": 100.0, "cl_end": 99.0},
        # İkisi de Up → AGREE
        {"hl_start": 100.0, "hl_end": 101.0, "cl_start": 100.0, "cl_end": 102.0},
    ]
    rate = directional_disagreement_rate(windows)
    assert rate == 0.5, f"2 pencerede 1 yön-sapması beklenir (0.5): {rate}"
