"""tests/test_source_basis_window_assembler_contract.py — basis-window assembler (TDD).

Zincir: Chainlink client boundary + Crypto v3 normalizer + load_basis_windows loader kapandı. Bir sonraki
seam: NORMALIZE edilmiş Chainlink sample'ları + ENJEKTE HL sampler'ı `source_basis`/`load_basis_windows`
uyumlu window kayıtlarına montajlamak. Hâlâ OFFLINE — fetch YOK, HL/Chainlink client ENJEKTE/sample
verilir; basis/disagreement/p99/sinyal HESAPLANMAZ; dosya YAZILMAZ.

Hedef eksik seam:
    analysis.source_basis.build_basis_windows(pm_windows, chainlink_samples, *, hl_price_at, shifts=())

İlk RED: build_basis_windows yok → AttributeError/ImportError (eksik üretim seam'i). Canlı API/secret YOK.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.source_basis import build_basis_windows


def _samples():
    """Normalize edilmiş Chainlink sample'lar (normalize_crypto_v3_report şekli)."""
    return [
        {"feed_id": "0xBTCUSD", "timestamp_ms": 1000, "price": 100.0},
        {"feed_id": "0xBTCUSD", "timestamp_ms": 2000, "price": 101.0},
        {"feed_id": "0xBTCUSD", "timestamp_ms": 3000, "price": 102.0},
    ]


def _hl_const(price=200.0):
    """Enjekte HL sampler — ts → sabit numeric (gerçek fetch YOK)."""
    return lambda ts_ms: price


def test_assembles_basic_window():
    """Tek pencere → exact-ts Chainlink eşleşmesi + enjekte HL → window kaydı."""
    pm = [{"start_ms": 1000, "end_ms": 2000}]
    out = build_basis_windows(pm, _samples(), hl_price_at=_hl_const(200.0))
    assert out == [{"hl_start": 200.0, "hl_end": 200.0, "cl_start": 100.0, "cl_end": 101.0}]


def test_chainlink_matched_exactly_by_timestamp():
    """cl_start/cl_end pencere start_ms/end_ms ile TAM ts eşleşmesinden gelir."""
    pm = [{"start_ms": 2000, "end_ms": 3000}]
    out = build_basis_windows(pm, _samples(), hl_price_at=_hl_const(200.0))
    assert out[0]["cl_start"] == 101.0 and out[0]["cl_end"] == 102.0


def test_hl_uses_injected_callable_per_endpoint():
    """hl_start/hl_end enjekte callable'dan window start/end ts ile alınır."""
    seen = []

    def hl(ts_ms):
        seen.append(ts_ms)
        return 200.0 + ts_ms / 1000.0

    pm = [{"start_ms": 1000, "end_ms": 2000}]
    out = build_basis_windows(pm, _samples(), hl_price_at=hl)
    assert out[0]["hl_start"] == 201.0 and out[0]["hl_end"] == 202.0
    assert 1000 in seen and 2000 in seen


def test_missing_chainlink_start_sample_raises():
    pm = [{"start_ms": 1500, "end_ms": 2000}]  # 1500 için sample yok
    with pytest.raises(ValueError):
        build_basis_windows(pm, _samples(), hl_price_at=_hl_const())


def test_missing_chainlink_end_sample_raises():
    pm = [{"start_ms": 1000, "end_ms": 2500}]  # 2500 için sample yok
    with pytest.raises(ValueError):
        build_basis_windows(pm, _samples(), hl_price_at=_hl_const())


def test_duplicate_chainlink_timestamp_raises():
    dup = _samples() + [{"feed_id": "0xBTCUSD", "timestamp_ms": 1000, "price": 999.0}]
    pm = [{"start_ms": 1000, "end_ms": 2000}]
    with pytest.raises(ValueError):
        build_basis_windows(pm, dup, hl_price_at=_hl_const())


@pytest.mark.parametrize("bad", ["1000", 1000.0, True, None])
def test_non_int_start_ms_raises(bad):
    pm = [{"start_ms": bad, "end_ms": 2000}]
    with pytest.raises(ValueError):
        build_basis_windows(pm, _samples(), hl_price_at=_hl_const())


@pytest.mark.parametrize("bad", ["2000", 2000.0, True, None])
def test_non_int_end_ms_raises(bad):
    pm = [{"start_ms": 1000, "end_ms": bad}]
    with pytest.raises(ValueError):
        build_basis_windows(pm, _samples(), hl_price_at=_hl_const())


def test_start_not_before_end_raises():
    pm = [{"start_ms": 2000, "end_ms": 2000}]
    with pytest.raises(ValueError):
        build_basis_windows(pm, _samples(), hl_price_at=_hl_const())


@pytest.mark.parametrize("bad_hl", [lambda ts: "x", lambda ts: True, lambda ts: None])
def test_non_numeric_hl_result_raises(bad_hl):
    pm = [{"start_ms": 1000, "end_ms": 2000}]
    with pytest.raises(ValueError):
        build_basis_windows(pm, _samples(), hl_price_at=bad_hl)


def test_preserves_optional_metadata():
    """timestamp/slug/market_id pm_window'dan korunur (zorunlu değil)."""
    pm = [{"start_ms": 1000, "end_ms": 2000, "timestamp": "2026-06-15T00:00:00Z",
           "slug": "btc-updown-15m-x", "market_id": "m1"}]
    out = build_basis_windows(pm, _samples(), hl_price_at=_hl_const())
    assert out[0]["slug"] == "btc-updown-15m-x"
    assert out[0]["timestamp"] == "2026-06-15T00:00:00Z"
    assert out[0]["market_id"] == "m1"


def test_no_hl_by_shift_when_shifts_empty():
    """shifts boş → hl_by_shift SENTEZLENMEZ."""
    pm = [{"start_ms": 1000, "end_ms": 2000}]
    out = build_basis_windows(pm, _samples(), hl_price_at=_hl_const())
    assert "hl_by_shift" not in out[0]


def test_shifts_build_hl_by_shift():
    """shifts verilince hl_by_shift[str(shift)] = {hl_start@start+shift*1000, hl_end@end+shift*1000}."""
    calls = {}

    def hl(ts_ms):
        calls[ts_ms] = 200.0 + ts_ms / 1000.0
        return calls[ts_ms]

    pm = [{"start_ms": 1000, "end_ms": 2000}]
    out = build_basis_windows(pm, _samples(), hl_price_at=hl, shifts=(0, 30, -30))
    hbs = out[0]["hl_by_shift"]
    assert hbs["0"] == {"hl_start": 201.0, "hl_end": 202.0}
    assert hbs["30"] == {"hl_start": 231.0, "hl_end": 232.0}    # +30s → +30000ms
    assert hbs["-30"] == {"hl_start": 171.0, "hl_end": 172.0}   # -30s → -30000ms


@pytest.mark.parametrize("bad_shift", ["30", 30.0, True, None])
def test_malformed_shift_raises(bad_shift):
    pm = [{"start_ms": 1000, "end_ms": 2000}]
    with pytest.raises(ValueError):
        build_basis_windows(pm, _samples(), hl_price_at=_hl_const(), shifts=(bad_shift,))


def test_non_numeric_shifted_hl_result_raises():
    """shift uygulanmış HL sonucu non-numeric → ValueError."""
    def hl(ts_ms):
        return 200.0 if ts_ms in (1000, 2000) else "bad"  # shift'li ts → bad

    pm = [{"start_ms": 1000, "end_ms": 2000}]
    with pytest.raises(ValueError):
        build_basis_windows(pm, _samples(), hl_price_at=hl, shifts=(30,))
