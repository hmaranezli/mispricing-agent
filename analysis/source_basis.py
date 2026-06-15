"""analysis/source_basis.py — offline HL-vs-Chainlink price-source basis validation.

F1a DOĞRULANMIŞ confounder: bot fair_value Hyperliquid mark/mid kullanıyor, PM Up/Down ise Chainlink
BTC/USD data stream ile resolve oluyor. Bu modül o kaynak sapmasını OFFLINE sayısallaştırır.

SAF fonksiyonlar: pencere çiftlerini GİRDİ alır (canlı fetch YOK). Gerçek Chainlink serisi doldurma
AYRI onaylı adım. PM kuralı: bir penceredeki yön = (end >= start) ⇒ Up, aksi Down (tie ≥ ⇒ Up).
"""
import json

_REQUIRED_KEYS = ("hl_start", "hl_end", "cl_start", "cl_end")


def _is_number(v) -> bool:
    """Numeric int/float — bool REDDEDİLİR (True/False fiyat değildir)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def load_basis_windows(path):
    """OFFLINE basis-window loader/validator (F1b human-supplied artifact iniş sözleşmesi).

    JSON kök bir LİSTE olmalı; her kayıt dict ve zorunlu numeric anahtarlar hl_start/hl_end/cl_start/
    cl_end içermeli (bool REDDEDİLİR). Opsiyonel hl_by_shift VARSA: shift-string → {hl_start, hl_end}
    (numeric) mapping olmalı; YOKSA dokunulmaz (sessiz shift sentezi YOK). timestamp/slug/market_id gibi
    metadata İZİNLİ, zorunlu değil, korunur. İhlal → ValueError. Canlı fetch/secret YOK; CSV YOK."""
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"bozuk JSON: {e}") from e

    if not isinstance(data, list):
        raise ValueError(f"kök JSON liste olmalı, bulundu: {type(data).__name__}")

    for i, rec in enumerate(data):
        if not isinstance(rec, dict):
            raise ValueError(f"window[{i}] dict olmalı, bulundu: {type(rec).__name__}")
        for k in _REQUIRED_KEYS:
            if k not in rec:
                raise ValueError(f"window[{i}] zorunlu anahtar eksik: {k}")
            if not _is_number(rec[k]):
                raise ValueError(f"window[{i}].{k} numeric olmalı, bulundu: {rec[k]!r}")

        if "hl_by_shift" in rec:
            hbs = rec["hl_by_shift"]
            if not isinstance(hbs, dict):
                raise ValueError(f"window[{i}].hl_by_shift dict olmalı, bulundu: {type(hbs).__name__}")
            for shift_key, anchor in hbs.items():
                if not isinstance(anchor, dict):
                    raise ValueError(
                        f"window[{i}].hl_by_shift[{shift_key!r}] dict olmalı, "
                        f"bulundu: {type(anchor).__name__}")
                for k in ("hl_start", "hl_end"):
                    if k not in anchor:
                        raise ValueError(
                            f"window[{i}].hl_by_shift[{shift_key!r}] zorunlu anahtar eksik: {k}")
                    if not _is_number(anchor[k]):
                        raise ValueError(
                            f"window[{i}].hl_by_shift[{shift_key!r}].{k} numeric olmalı, "
                            f"bulundu: {anchor[k]!r}")

    return data


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
