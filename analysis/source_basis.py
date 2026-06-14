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
