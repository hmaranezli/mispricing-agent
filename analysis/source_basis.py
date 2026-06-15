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


def _is_int(v) -> bool:
    """int — bool REDDEDİLİR (True/False ms/saniye değildir)."""
    return isinstance(v, int) and not isinstance(v, bool)


def build_basis_windows(pm_windows, chainlink_samples, *, hl_price_at, shifts=()):
    """OFFLINE basis-window montajcısı: normalize Chainlink sample'ları + ENJEKTE HL sampler'ı
    `load_basis_windows`/`source_basis` uyumlu window kayıtlarına çevirir. Fetch/secret/HMAC YOK;
    basis/disagreement/p99/sinyal HESAPLANMAZ; dosya YAZILMAZ.

    pm_windows: list[dict], her biri int-not-bool start_ms<end_ms (+ ops. timestamp/slug/market_id).
    chainlink_samples: normalize_crypto_v3_report şekli ({timestamp_ms int, price numeric}); aynı
    timestamp_ms iki kez → ValueError. Chainlink eşleşmesi EXACT ts; eksik start/end → ValueError.
    hl_price_at: enjekte callable (implicit network YOK); non-numeric/bool sonuç → ValueError.
    shifts: ops. int-not-bool saniye iterable (neg/0/poz); boş → hl_by_shift YOK; her shift için
    hl_by_shift[str(shift)] = {hl_start@start+shift*1000, hl_end@end+shift*1000}; malformed shift veya
    non-numeric shifted HL → ValueError. Çıktı: window dict listesi."""
    if not isinstance(pm_windows, list):
        raise ValueError(f"pm_windows list olmalı, bulundu: {type(pm_windows).__name__}")
    if not isinstance(chainlink_samples, list):
        raise ValueError(f"chainlink_samples list olmalı, bulundu: {type(chainlink_samples).__name__}")
    if not callable(hl_price_at):
        raise ValueError("hl_price_at callable olmalı (enjekte)")

    # Chainlink ts → price haritası (exact-match), duplicate ts fail-closed.
    cl_by_ts = {}
    for j, s in enumerate(chainlink_samples):
        if not isinstance(s, dict):
            raise ValueError(f"chainlink_samples[{j}] dict olmalı, bulundu: {type(s).__name__}")
        ts = s.get("timestamp_ms")
        if not _is_int(ts):
            raise ValueError(f"chainlink_samples[{j}].timestamp_ms int olmalı (bool değil): {ts!r}")
        price = s.get("price")
        if not _is_number(price):
            raise ValueError(f"chainlink_samples[{j}].price numeric olmalı: {price!r}")
        if ts in cl_by_ts:
            raise ValueError(f"yinelenen Chainlink timestamp_ms: {ts}")
        cl_by_ts[ts] = price

    # Shift listesi doğrulama (montaj öncesi).
    shift_list = list(shifts)
    for sh in shift_list:
        if not _is_int(sh):
            raise ValueError(f"shift int saniye olmalı (bool değil): {sh!r}")

    def _hl(ts_ms):
        v = hl_price_at(ts_ms)
        if not _is_number(v):
            raise ValueError(f"hl_price_at({ts_ms}) numeric olmalı: {v!r}")
        return v

    out = []
    for i, w in enumerate(pm_windows):
        if not isinstance(w, dict):
            raise ValueError(f"pm_windows[{i}] dict olmalı, bulundu: {type(w).__name__}")
        start_ms, end_ms = w.get("start_ms"), w.get("end_ms")
        if not _is_int(start_ms):
            raise ValueError(f"pm_windows[{i}].start_ms int olmalı (bool değil): {start_ms!r}")
        if not _is_int(end_ms):
            raise ValueError(f"pm_windows[{i}].end_ms int olmalı (bool değil): {end_ms!r}")
        if start_ms >= end_ms:
            raise ValueError(f"pm_windows[{i}] start_ms<end_ms olmalı: {start_ms} >= {end_ms}")
        if start_ms not in cl_by_ts:
            raise ValueError(f"pm_windows[{i}] start_ms={start_ms} için Chainlink sample yok")
        if end_ms not in cl_by_ts:
            raise ValueError(f"pm_windows[{i}] end_ms={end_ms} için Chainlink sample yok")

        rec = {
            "hl_start": _hl(start_ms),
            "hl_end": _hl(end_ms),
            "cl_start": cl_by_ts[start_ms],
            "cl_end": cl_by_ts[end_ms],
        }
        for meta in ("timestamp", "slug", "market_id"):
            if meta in w:
                rec[meta] = w[meta]
        if shift_list:
            rec["hl_by_shift"] = {
                str(sh): {"hl_start": _hl(start_ms + sh * 1000),
                          "hl_end": _hl(end_ms + sh * 1000)}
                for sh in shift_list
            }
        out.append(rec)

    return out


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
