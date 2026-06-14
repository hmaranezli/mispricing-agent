"""analysis/source_basis.py — offline HL-vs-Chainlink price-source basis validation.

F1a DOĞRULANMIŞ confounder: bot fair_value Hyperliquid mark/mid kullanıyor, PM Up/Down ise Chainlink
BTC/USD data stream ile resolve oluyor. Bu modül o kaynak sapmasını OFFLINE sayısallaştırır.

SAF fonksiyonlar: pencere çiftlerini GİRDİ alır (canlı fetch YOK). Gerçek Chainlink serisi doldurma
AYRI onaylı adım. PM kuralı: bir penceredeki yön = (end >= start) ⇒ Up, aksi Down (tie ≥ ⇒ Up).
"""


def _direction_up(start: float, end: float) -> bool:
    """PM Up/Down kuralı: end >= start ⇒ Up (tie Up'a gider)."""
    return end >= start


def directional_disagreement_rate(windows) -> float:
    """HL yönü ile Chainlink yönünün FARKLI olduğu pencere oranı (sahte-edge göstergesi).

    windows: her biri {hl_start, hl_end, cl_start, cl_end} olan dict listesi. Her pencere için
    HL yönü (_direction_up(hl_start, hl_end)) ile Chainlink yönü (_direction_up(cl_start, cl_end))
    karşılaştırılır; farklı olanların oranı döner. Boş liste → 0.0 (sapma ölçülemez).
    """
    if not windows:
        return 0.0
    disagree = 0
    for w in windows:
        hl_up = _direction_up(w["hl_start"], w["hl_end"])
        cl_up = _direction_up(w["cl_start"], w["cl_end"])
        if hl_up != cl_up:
            disagree += 1
    return disagree / len(windows)


def directional_disagreement_rate_with_shift(windows, shift_seconds) -> float:
    """Latency-shifted yön sapma oranı: HL anchor'ı verilen `shift_seconds`'a göre seçilir.

    Gerçek-veride HL ve Chainlink eşzamanlı örneklenmez; bu fonksiyon HL'yi bir zaman ofsetiyle
    hizalayıp Chainlink yönüyle kıyaslar. Her window için HL anchor = `window["hl_by_shift"][shift_seconds]`
    (dict: {"hl_start", "hl_end"}); Chainlink yönü `cl_start`/`cl_end`'ten. PM kuralı end ≥ start ⇒ Up.

    `shift_seconds` window'da YOKSA → açık `KeyError` (sessiz shift=0 fallback YOK). Boş liste → 0.0.
    """
    if not windows:
        return 0.0
    disagree = 0
    for w in windows:
        hl = w["hl_by_shift"][shift_seconds]   # eksikse KeyError — sessiz fallback yok
        hl_up = _direction_up(hl["hl_start"], hl["hl_end"])
        cl_up = _direction_up(w["cl_start"], w["cl_end"])
        if hl_up != cl_up:
            disagree += 1
    return disagree / len(windows)


def source_basis_bps_stats(windows) -> dict:
    """HL ile Chainlink fiyat-kaynağı farkını bps cinsinden ölçer (start + end anchor).

    basis_bps = ((hl_price - cl_price) / cl_price) * 10000. Payda = Chainlink fiyatı, çünkü PM
    resolution Chainlink kullanır (referans odur). Her pencere için 2 ölçüm (start, end) → count =
    2 * pencere sayısı. Çıktı: mean_abs_basis_bps, max_abs_basis_bps, count.

    Boş girdi → {"mean_abs_basis_bps": 0.0, "max_abs_basis_bps": 0.0, "count": 0}. Canlı fetch YOK.
    """
    abs_bps = []
    for w in windows:
        for hl_key, cl_key in (("hl_start", "cl_start"), ("hl_end", "cl_end")):
            cl = w[cl_key]
            bps = ((w[hl_key] - cl) / cl) * 10000.0
            abs_bps.append(abs(bps))
    if not abs_bps:
        return {"mean_abs_basis_bps": 0.0, "max_abs_basis_bps": 0.0, "count": 0}
    return {
        "mean_abs_basis_bps": sum(abs_bps) / len(abs_bps),
        "max_abs_basis_bps": max(abs_bps),
        "count": len(abs_bps),
    }
