"""tests/test_chainlink_streams_report_normalizer_contract.py — Crypto v3 report normalizer (TDD).

`fetch_stream_reports` opak report'ları DEĞİŞTİRMEDEN döndürüyor. Bir sonraki seam: zaten-decode-edilmiş
Crypto v3 report dict'ini basis-window montajından ÖNCE normalize etmek. Bu slice yalnız o normalizer'ın
sözleşmesini pin'ler — fullReport blob DECODE EDİLMEZ, canlı fetch/secret YOK.

Chainlink docs: raw REST report = feedID/validFromTimestamp/observationsTimestamp/fullReport; decoded
Crypto v3 report = feedId, observationsTimestamp, price. Bu fonksiyon DECODED report bekler.

Hedef eksik seam:
    data.chainlink_streams.normalize_crypto_v3_report(report, *, price_scale)

İlk RED: normalize_crypto_v3_report yok → AttributeError/ImportError (eksik üretim seam'i).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.chainlink_streams import normalize_crypto_v3_report


# Crypto v3 price_scale örnek: 1e18 (18-ondalık fixed-point). Test sabiti — config/secret değil.
SCALE = 10 ** 18


def _decoded_report(price=2_000 * 10 ** 18):
    """Decoded Crypto v3-benzeri report (feedId + observationsTimestamp + price)."""
    return {"feedId": "0xBTCUSD", "observationsTimestamp": 1700, "price": price}


def test_normalizes_decoded_report():
    """Geçerli decoded report → tam normalize edilmiş dict."""
    out = normalize_crypto_v3_report(_decoded_report(price=2_000 * SCALE), price_scale=SCALE)
    assert out == {"feed_id": "0xBTCUSD", "timestamp_ms": 1700 * 1000, "price": 2_000.0}


def test_accepts_feedID_capital_variant():
    """feed id `feedID` (büyük) varyantından da okunur."""
    rep = {"feedID": "0xBTCUSD", "observationsTimestamp": 1700, "price": 2_000 * SCALE}
    out = normalize_crypto_v3_report(rep, price_scale=SCALE)
    assert out["feed_id"] == "0xBTCUSD"


@pytest.mark.parametrize("price_key", ["price", "benchmarkPrice", "BenchmarkPrice"])
def test_accepts_price_key_variants(price_key):
    """price `price`/`benchmarkPrice`/`BenchmarkPrice` varyantlarından okunur."""
    rep = {"feedId": "0xBTCUSD", "observationsTimestamp": 1700, price_key: 2_000 * SCALE}
    out = normalize_crypto_v3_report(rep, price_scale=SCALE)
    assert out["price"] == 2_000.0


def test_output_has_no_opaque_fields():
    """Normalize çıktısı YALNIZ feed_id/timestamp_ms/price içerir — fullReport vb. taşınmaz."""
    rep = _decoded_report()
    rep["fullReport"] = "0xdeadbeef"
    rep["validFromTimestamp"] = 1699
    out = normalize_crypto_v3_report(rep, price_scale=SCALE)
    assert set(out.keys()) == {"feed_id", "timestamp_ms", "price"}


def test_missing_feed_id_raises():
    rep = {"observationsTimestamp": 1700, "price": 2_000 * SCALE}
    with pytest.raises(ValueError):
        normalize_crypto_v3_report(rep, price_scale=SCALE)


def test_empty_feed_id_raises():
    rep = {"feedId": "", "observationsTimestamp": 1700, "price": 2_000 * SCALE}
    with pytest.raises(ValueError):
        normalize_crypto_v3_report(rep, price_scale=SCALE)


def test_missing_timestamp_raises():
    rep = {"feedId": "0xBTCUSD", "price": 2_000 * SCALE}
    with pytest.raises(ValueError):
        normalize_crypto_v3_report(rep, price_scale=SCALE)


@pytest.mark.parametrize("bad", ["1700", 1700.0, True, None])
def test_non_int_timestamp_raises(bad):
    """observationsTimestamp int saniye olmalı (str/float/bool/None reddedilir)."""
    rep = {"feedId": "0xBTCUSD", "observationsTimestamp": bad, "price": 2_000 * SCALE}
    with pytest.raises(ValueError):
        normalize_crypto_v3_report(rep, price_scale=SCALE)


def test_missing_price_raises():
    """fullReport VAR ama decoded price YOK (raw REST payload) → ValueError."""
    rep = {"feedID": "0xBTCUSD", "observationsTimestamp": 1700,
           "validFromTimestamp": 1699, "fullReport": "0xdeadbeef"}
    with pytest.raises(ValueError):
        normalize_crypto_v3_report(rep, price_scale=SCALE)


@pytest.mark.parametrize("bad", ["2000", True, None])
def test_non_numeric_price_raises(bad):
    rep = {"feedId": "0xBTCUSD", "observationsTimestamp": 1700, "price": bad}
    with pytest.raises(ValueError):
        normalize_crypto_v3_report(rep, price_scale=SCALE)


@pytest.mark.parametrize("bad", [0, -1, "1e18", True, None])
def test_bad_price_scale_raises(bad):
    """price_scale pozitif numeric olmalı (0/negatif/str/bool/None reddedilir)."""
    rep = _decoded_report()
    with pytest.raises(ValueError):
        normalize_crypto_v3_report(rep, price_scale=bad)
