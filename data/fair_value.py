"""
data/fair_value.py — Binary option fair value hesaplayıcı.
Model: log-normal GBM, drift yok (kısa pencereler ≤60dk için geçerli).
P(fiyat > referans | şimdiki fiyat, kalan süre) = Φ(log(p_now/p_ref) / σ√T)
"""
import math

ASSET_VOL = {
    "BTC": 0.80,
    "ETH": 1.20,
    "SOL": 1.50,
    "XRP": 1.50,
}

_SECONDS_PER_YEAR = 31_557_600.0


def fair_yes(p_now: float, p_ref: float, seconds_remaining: float,
             asset: str = "BTC", current_volatility: float | None = None) -> float:
    """
    P(asset_price > p_ref at resolution | current_price = p_now)

    Args:
        p_now: Şimdiki fiyat (HL live)
        p_ref: Referans fiyat (PM penceresinin açılışında HL fiyatı)
        seconds_remaining: Çözüme kadar kalan saniye
        asset: "BTC", "ETH", "SOL", "XRP" — current_volatility None ise ASSET_VOL'dan alınır
        current_volatility: Dinamik realized vol (hl_candles'dan). Verilirse ASSET_VOL'u geçersiz kılar.

    Returns:
        [0.0, 1.0] arası float — YES token'ın gerçek olasılıksal değeri

    Raises:
        ValueError: p_now veya p_ref ≤ 0 ise
    """
    if p_now <= 0 or p_ref <= 0:
        raise ValueError(f"Fiyatlar pozitif olmalı: p_now={p_now}, p_ref={p_ref}")

    if seconds_remaining <= 0:
        return 1.0 if p_now > p_ref else 0.0

    annual_vol = current_volatility if current_volatility is not None else ASSET_VOL.get(asset, 0.80)
    years = seconds_remaining / _SECONDS_PER_YEAR
    sigma_t = annual_vol * math.sqrt(years)

    if sigma_t < 1e-10:
        return 1.0 if p_now > p_ref else 0.0

    d = math.log(p_now / p_ref)
    z = d / sigma_t
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))
