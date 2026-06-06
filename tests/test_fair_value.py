"""
tests/test_fair_value.py — data/fair_value.py unit testleri
Gerçek API çağrısı yok — saf matematik testleri.
"""
import math
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fair_value import fair_yes, ASSET_VOL


def test_fair_yes_at_reference_price_is_half():
    """Fiyat tam referanstayken, süre varsa → 0.50."""
    result = fair_yes(100_000.0, 100_000.0, 300.0, "BTC")
    assert abs(result - 0.5) < 1e-6


def test_fair_yes_above_reference_is_above_half():
    """Fiyat referansın üstündeyse → 0.50'den büyük."""
    result = fair_yes(101_000.0, 100_000.0, 300.0, "BTC")
    assert result > 0.5


def test_fair_yes_below_reference_is_below_half():
    """Fiyat referansın altındaysa → 0.50'den küçük."""
    result = fair_yes(99_000.0, 100_000.0, 300.0, "BTC")
    assert result < 0.5


def test_fair_yes_expired_above():
    """Süre dolmuş, fiyat referansın üstünde → 1.0."""
    assert fair_yes(101_000.0, 100_000.0, 0.0, "BTC") == 1.0


def test_fair_yes_expired_below():
    """Süre dolmuş, fiyat referansın altında → 0.0."""
    assert fair_yes(99_000.0, 100_000.0, 0.0, "BTC") == 0.0


def test_fair_yes_expired_equal():
    """Süre dolmuş, fiyat tam referansta → 0.0 (üstünde değil)."""
    assert fair_yes(100_000.0, 100_000.0, 0.0, "BTC") == 0.0


def test_fair_yes_concrete_example():
    """
    Somut senaryo: ref=105000, cur=104800, 180s kaldı (BTC vol=%80).
    Analitik:
      sigma_t = 0.80 * sqrt(180 / 31_557_600) = 0.80 * 0.002388 = 0.001910
      d = log(104800/105000) = -0.001908
      z = -0.001908 / 0.001910 ≈ -0.999
      Φ(-0.999) ≈ 0.159
    Beklenti: [0.10, 0.25]
    """
    result = fair_yes(104_800.0, 105_000.0, 180.0, "BTC")
    assert 0.10 < result < 0.25


def test_fair_yes_symmetry():
    """fair_yes(up) + fair_yes(down) == 1 — log-normal modelde simetri geometrik.
    p_up = ref * r, p_down = ref / r → log(p_up/ref) = -log(p_down/ref) → Φ(z) + Φ(-z) = 1.
    """
    r = 1.01  # oransal hareket
    above = fair_yes(100_000.0 * r, 100_000.0, 300.0, "BTC")   # +%1
    below = fair_yes(100_000.0 / r, 100_000.0, 300.0, "BTC")   # -%0.99 (geometrik simetrik)
    assert abs(above + below - 1.0) < 1e-10


def test_fair_yes_invalid_zero_price():
    """Sıfır p_now ValueError fırlatır."""
    with pytest.raises(ValueError, match="pozitif"):
        fair_yes(0.0, 100_000.0, 300.0, "BTC")


def test_fair_yes_invalid_negative_price():
    """Negatif p_now ValueError fırlatır."""
    with pytest.raises(ValueError, match="pozitif"):
        fair_yes(-1.0, 100_000.0, 300.0, "BTC")


def test_fair_yes_invalid_zero_ref():
    """Sıfır p_ref ValueError fırlatır."""
    with pytest.raises(ValueError, match="pozitif"):
        fair_yes(100_000.0, 0.0, 300.0, "BTC")


def test_fair_yes_output_range():
    """Her koşulda sonuç [0, 1] aralığında."""
    cases = [
        (50_000.0, 100_000.0, 300.0, "BTC"),    # çok geride
        (200_000.0, 100_000.0, 300.0, "BTC"),   # çok ileride
        (100_000.0, 100_000.0, 1.0, "BTC"),     # neredeyse bitti
        (100_000.0, 100_000.0, 3600.0, "ETH"),  # 1 saat, ETH
    ]
    for args in cases:
        r = fair_yes(*args)
        assert 0.0 <= r <= 1.0, f"Aralık dışı: {r} for {args}"


def test_asset_vol_keys_exist():
    """Takip edilen tüm varlıklar ASSET_VOL sözlüğünde var ve pozitif."""
    for asset in ("BTC", "ETH", "SOL", "XRP"):
        assert asset in ASSET_VOL, f"{asset} ASSET_VOL'da yok"
        assert ASSET_VOL[asset] > 0, f"{asset} vol sıfır veya negatif"


def test_fair_yes_eth_uses_higher_vol():
    """ETH daha yüksek vol kullandığı için aynı sapmayla daha geniş dağılım."""
    btc_result = fair_yes(101_000.0, 100_000.0, 300.0, "BTC")
    eth_result = fair_yes(101_000.0, 100_000.0, 300.0, "ETH")
    # ETH vol > BTC vol → sigma_t daha büyük → z daha küçük → sonuç 0.5'e daha yakın
    assert abs(eth_result - 0.5) < abs(btc_result - 0.5)


def test_fair_yes_more_time_means_closer_to_half():
    """Daha uzun süre → daha büyük sigma_t → z daha küçük → 0.5'e daha yakın."""
    short = fair_yes(101_000.0, 100_000.0, 60.0, "BTC")   # 1 dk
    long_ = fair_yes(101_000.0, 100_000.0, 3600.0, "BTC")  # 1 saat
    assert abs(long_ - 0.5) < abs(short - 0.5)


def test_fair_yes_uses_current_volatility_when_provided():
    """current_volatility verildiğinde ASSET_VOL kullanılmaz.

    Senaryo: fiyat referansın 1 birim üstünde, 15 dk kaldı.
      - vol=0.001 (neredeyse sıfır) → sigma_t ≈ 0 → sonuç 1.0'e yakın (>0.90)
      - BTC normal vol=0.80 → sigma_t büyük → sonuç 0.5'e çok yakın
    """
    low_vol = fair_yes(100_001.0, 100_000.0, 900.0, "BTC", current_volatility=0.001)
    normal  = fair_yes(100_001.0, 100_000.0, 900.0, "BTC")
    assert low_vol > 0.90, f"Düşük vol → kesinlik yüksek, beklenen >0.90, got {low_vol:.4f}"
    assert abs(normal - 0.50) < 0.01, f"Normal vol + az üstünde → 0.50'ye yakın, got {normal:.4f}"
