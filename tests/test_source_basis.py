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


def test_tie_boundary_counts_as_up_per_pm_rule():
    """PM kuralı: end == start (tie) ⇒ Up. Tie hem HL hem Chainlink için Up sayılmalı.
    - HL tie (Up) + Chainlink Down → DISAGREE.
    - İki kaynak da tie → ikisi Up → disagreement 0.
    Mevcut helper >= kullandığı için bu GREEN olabilir (tie kuralının regresyon kilidi)."""
    from analysis.source_basis import directional_disagreement_rate

    # HL tie ⇒ Up; Chainlink Down (99<100) ⇒ Down → DISAGREE
    hl_tie_vs_cl_down = [{"hl_start": 100.0, "hl_end": 100.0, "cl_start": 100.0, "cl_end": 99.0}]
    assert directional_disagreement_rate(hl_tie_vs_cl_down) == 1.0, "HL tie(Up) vs CL Down → disagree"

    # İki kaynak da tie ⇒ ikisi Up → disagreement YOK
    both_tie = [{"hl_start": 100.0, "hl_end": 100.0, "cl_start": 50.0, "cl_end": 50.0}]
    assert directional_disagreement_rate(both_tie) == 0.0, "iki tie de Up → disagreement 0"


def test_source_basis_bps_stats_start_and_end_anchors():
    """source_basis_bps_stats(windows): HL ile Chainlink arasındaki kaynak farkını bps cinsinden ölçer.
    basis_bps = ((hl - cl) / cl) * 10000, hem start hem end anchor'ında → count = 2 * pencere sayısı.

    Örnek pencere: start hl=cl=100 → 0 bps; end hl=101, cl=100 → (1/100)*10000 = 100 bps.
    Beklenen: mean_abs_basis_bps=50, max_abs_basis_bps=100, count=2.
    RED: source_basis_bps_stats henüz YOK → ImportError/AttributeError."""
    import pytest
    from analysis.source_basis import source_basis_bps_stats

    windows = [{"hl_start": 100.0, "hl_end": 101.0, "cl_start": 100.0, "cl_end": 100.0}]
    stats = source_basis_bps_stats(windows)
    assert stats["count"] == 2, f"start+end anchor → 2 ölçüm: {stats}"
    assert stats["max_abs_basis_bps"] == pytest.approx(100.0), f"max abs basis: {stats}"
    assert stats["mean_abs_basis_bps"] == pytest.approx(50.0), f"mean abs basis: {stats}"
