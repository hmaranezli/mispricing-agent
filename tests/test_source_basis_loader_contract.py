"""tests/test_source_basis_loader_contract.py — source_basis input loader/validator contract (TDD).

F1b availability audit: F1b can start now = NO (approved Chainlink BTC/USD Data Streams + matched HL
serisi YOK). Veri gelmeden, human-supplied artifact'ın iniş yapacağı sözleşmeyi pin'leyen offline bir
loader/validator hazırlanır. Bu slice F1b ölçümünü BAŞLATMAZ, F/live AÇMAZ — yalnız girdi sözleşmesi.

Hedef eksik seam:
    analysis.source_basis.load_basis_windows(path)

Sözleşme (source_basis.py'nin TÜKETTİĞİ anahtarlardan türetildi; uydurma alan YOK):
- Kök JSON bir LİSTE olmalı (window kayıtları); değilse → ValueError.
- Bozuk JSON → ValueError.
- Her kayıtta zorunlu anahtarlar: hl_start, hl_end, cl_start, cl_end (numeric float/int).
- Eksik zorunlu anahtar → ValueError. Non-numeric zorunlu değer → ValueError.
- Opsiyonel hl_by_shift: VARSA, shift-saniye string'inden numeric hl_start/hl_end içeren objeye mapping
  olmalı; bozuksa → ValueError. YOKSA hata YOK (shift'li analiz ayrı davranış; sessiz shift sentezi YOK).
- timestamp/slug/market_id gibi metadata anahtarlarına İZİN var ama ZORUNLU DEĞİL ve mevcut basis
  fonksiyonlarınca tüketilmez (korunur, doğrulanmaz).

İlk RED: load_basis_windows yok → AttributeError/ImportError (eksik üretim seam'i). Canlı fetch/secret YOK.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.source_basis import load_basis_windows


def _write(tmp_path, payload, *, raw=None):
    p = tmp_path / "windows.json"
    if raw is not None:
        p.write_text(raw, encoding="utf-8")
    else:
        p.write_text(json.dumps(payload), encoding="utf-8")
    return str(p)


def _valid_record():
    return {"hl_start": 100.0, "hl_end": 101.0, "cl_start": 100.5, "cl_end": 100.9}


def test_loads_valid_windows(tmp_path):
    """Geçerli liste → window dict listesi döner; zorunlu anahtarlar korunur."""
    path = _write(tmp_path, [_valid_record(), _valid_record()])
    windows = load_basis_windows(path)
    assert isinstance(windows, list)
    assert len(windows) == 2
    for w in windows:
        for k in ("hl_start", "hl_end", "cl_start", "cl_end"):
            assert isinstance(w[k], (int, float))


def test_empty_list_ok(tmp_path):
    """Boş liste geçerli (sapma ölçülemez ama sözleşme ihlali değil)."""
    path = _write(tmp_path, [])
    assert load_basis_windows(path) == []


def test_non_list_root_raises(tmp_path):
    """Kök JSON liste değil (dict) → ValueError."""
    path = _write(tmp_path, {"hl_start": 1, "hl_end": 2, "cl_start": 1, "cl_end": 2})
    with pytest.raises(ValueError):
        load_basis_windows(path)


def test_malformed_json_raises(tmp_path):
    """Bozuk JSON → ValueError."""
    path = _write(tmp_path, None, raw="{not valid json,,,")
    with pytest.raises(ValueError):
        load_basis_windows(path)


@pytest.mark.parametrize("missing", ["hl_start", "hl_end", "cl_start", "cl_end"])
def test_missing_required_key_raises(tmp_path, missing):
    """Zorunlu anahtar eksik → ValueError."""
    rec = _valid_record()
    del rec[missing]
    path = _write(tmp_path, [rec])
    with pytest.raises(ValueError):
        load_basis_windows(path)


@pytest.mark.parametrize("key", ["hl_start", "hl_end", "cl_start", "cl_end"])
def test_non_numeric_required_value_raises(tmp_path, key):
    """Zorunlu değer numeric değil → ValueError."""
    rec = _valid_record()
    rec[key] = "not-a-number"
    path = _write(tmp_path, [rec])
    with pytest.raises(ValueError):
        load_basis_windows(path)


def test_bool_required_value_raises(tmp_path):
    """bool numeric sayılmaz (True/False fiyat değildir) → ValueError."""
    rec = _valid_record()
    rec["hl_start"] = True
    path = _write(tmp_path, [rec])
    with pytest.raises(ValueError):
        load_basis_windows(path)


def test_optional_hl_by_shift_valid(tmp_path):
    """hl_by_shift VARSA + geçerli (shift-string → numeric hl_start/hl_end) → kabul, korunur."""
    rec = _valid_record()
    rec["hl_by_shift"] = {"0": {"hl_start": 100.0, "hl_end": 101.0},
                          "30": {"hl_start": 100.2, "hl_end": 101.1}}
    path = _write(tmp_path, [rec])
    windows = load_basis_windows(path)
    assert windows[0]["hl_by_shift"]["30"]["hl_end"] == 101.1


def test_optional_hl_by_shift_absent_ok(tmp_path):
    """hl_by_shift YOKSA hata YOK (shift'li analiz ayrı; sessiz shift sentezi yapılmaz)."""
    path = _write(tmp_path, [_valid_record()])
    windows = load_basis_windows(path)
    assert "hl_by_shift" not in windows[0]


def test_malformed_hl_by_shift_raises(tmp_path):
    """hl_by_shift VAR ama bozuk (shift objesi non-numeric hl_start) → ValueError."""
    rec = _valid_record()
    rec["hl_by_shift"] = {"0": {"hl_start": "x", "hl_end": 101.0}}
    path = _write(tmp_path, [rec])
    with pytest.raises(ValueError):
        load_basis_windows(path)


def test_metadata_keys_allowed_not_required(tmp_path):
    """timestamp/slug/market_id gibi metadata İZİNLİ, ZORUNLU değil; loader patlatmaz."""
    rec = _valid_record()
    rec.update({"timestamp": "2026-06-15T00:00:00Z", "slug": "btc-updown-15m-x", "market_id": "m1"})
    path = _write(tmp_path, [rec])
    windows = load_basis_windows(path)
    assert windows[0]["slug"] == "btc-updown-15m-x"
