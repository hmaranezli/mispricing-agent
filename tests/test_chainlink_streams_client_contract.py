"""tests/test_chainlink_streams_client_contract.py — read-only Chainlink Streams client interface (TDD).

F1b'nin tek hard blocker'ı Chainlink BTC/USD Data Streams verisi (auth-gated). HL tarafı public
read-only helper'larla zaten hazır. Bu slice OFFLINE arayüz hazırlığı: gerçek bir fetch/HMAC/endpoint
EKLEMEDEN, enjekte edilebilir bir client kontratı pin'ler. `fetch_stream_reports` thin bir
sınır/doğrulama katmanıdır — client ENJEKTE edilir (implicit env/default network client YOK), gerçek
Chainlink çağrısı/secret YOK, payload normalize EDİLMEZ (uydurma price alanı yok).

Hedef eksik seam:
    data.chainlink_streams.fetch_stream_reports(stream_id, start_ms, end_ms, *, client)

İlk RED: data.chainlink_streams / fetch_stream_reports yok → ImportError/ModuleNotFoundError (eksik
üretim seam'i). Testler FAKE client enjekte eder — canlı API/secret/network YOK.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.chainlink_streams import fetch_stream_reports


class _FakeClient:
    """Enjekte test client'ı — gerçek network/secret YOK. fetch_reports çağrılarını kaydeder."""

    def __init__(self, result):
        self._result = result
        self.calls = []

    def fetch_reports(self, *, stream_id, start_ms, end_ms):
        self.calls.append({"stream_id": stream_id, "start_ms": start_ms, "end_ms": end_ms})
        return self._result


def _reports():
    # Opak report dict'leri — bu slice normalize ETMEZ (price alanı uydurulmaz).
    return [{"observationsTimestamp": 1000, "fullReport": "0xaa"},
            {"observationsTimestamp": 2000, "fullReport": "0xbb"}]


def test_returns_client_reports_unchanged():
    """Geçerli girdi → client.fetch_reports sonucu DEĞİŞTİRİLMEDEN döner."""
    client = _FakeClient(_reports())
    out = fetch_stream_reports("0xBTCUSD", 1000, 2000, client=client)
    assert out == _reports()


def test_calls_client_fetch_reports_once_with_args():
    """client.fetch_reports TAM BİR KEZ, doğru argümanlarla çağrılır (implicit/default client YOK)."""
    client = _FakeClient(_reports())
    fetch_stream_reports("0xBTCUSD", 1000, 2000, client=client)
    assert client.calls == [{"stream_id": "0xBTCUSD", "start_ms": 1000, "end_ms": 2000}]


def test_requires_explicit_client():
    """client zorunlu keyword arg — verilmezse TypeError (implicit env/default network client YOK)."""
    with pytest.raises(TypeError):
        fetch_stream_reports("0xBTCUSD", 1000, 2000)


def test_empty_stream_id_raises():
    client = _FakeClient(_reports())
    with pytest.raises(ValueError):
        fetch_stream_reports("", 1000, 2000, client=client)


@pytest.mark.parametrize("bad", ["1000", 1000.0, True, None])
def test_non_int_start_ms_raises(bad):
    """start_ms int olmalı (bool/float/str/None reddedilir)."""
    client = _FakeClient(_reports())
    with pytest.raises(ValueError):
        fetch_stream_reports("0xBTCUSD", bad, 2000, client=client)


@pytest.mark.parametrize("bad", ["2000", 2000.0, True, None])
def test_non_int_end_ms_raises(bad):
    """end_ms int olmalı (bool/float/str/None reddedilir)."""
    client = _FakeClient(_reports())
    with pytest.raises(ValueError):
        fetch_stream_reports("0xBTCUSD", 1000, bad, client=client)


def test_start_not_before_end_raises():
    """start_ms >= end_ms → ValueError."""
    client = _FakeClient(_reports())
    with pytest.raises(ValueError):
        fetch_stream_reports("0xBTCUSD", 2000, 2000, client=client)
    with pytest.raises(ValueError):
        fetch_stream_reports("0xBTCUSD", 3000, 2000, client=client)


def test_client_result_not_list_raises():
    """client list DÖNDÜRMEZSE → ValueError."""
    client = _FakeClient({"not": "a list"})
    with pytest.raises(ValueError):
        fetch_stream_reports("0xBTCUSD", 1000, 2000, client=client)


def test_client_result_not_list_of_dicts_raises():
    """list ama elemanlar dict değilse → ValueError."""
    client = _FakeClient([{"ok": 1}, "not-a-dict"])
    with pytest.raises(ValueError):
        fetch_stream_reports("0xBTCUSD", 1000, 2000, client=client)
