"""tests/test_clob_client.py — clob_client singleton testleri."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock


def test_get_client_raises_when_env_missing(monkeypatch):
    """POLY_PRIVATE_KEY yoksa get_client() KeyError verir."""
    from execution import clob_client as cc
    cc.reset_client()
    for key in ("POLY_PRIVATE_KEY", "POLY_API_KEY", "POLY_API_SECRET", "POLY_API_PASSPHRASE"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises((KeyError, Exception)):
        cc.get_client()
    cc.reset_client()


def test_get_client_returns_singleton(monkeypatch):
    """get_client() iki kez çağrılınca aynı nesneyi döndürür."""
    from execution import clob_client as cc
    cc.reset_client()
    monkeypatch.setenv("POLY_PRIVATE_KEY",    "0xdeadbeef")
    monkeypatch.setenv("POLY_API_KEY",        "test-key")
    monkeypatch.setenv("POLY_API_SECRET",     "test-secret")
    monkeypatch.setenv("POLY_API_PASSPHRASE", "test-pass")
    monkeypatch.setenv("POLY_WALLET_ADDRESS", "0xabc")

    fake_client = MagicMock()
    with patch("execution.clob_client.ClobClient", return_value=fake_client):
        c1 = cc.get_client()
        c2 = cc.get_client()
    assert c1 is c2
    cc.reset_client()


def test_reset_client_clears_singleton(monkeypatch):
    """reset_client() sonrası get_client() yeni nesne oluşturur."""
    from execution import clob_client as cc
    cc.reset_client()
    monkeypatch.setenv("POLY_PRIVATE_KEY",    "0xdeadbeef")
    monkeypatch.setenv("POLY_API_KEY",        "test-key")
    monkeypatch.setenv("POLY_API_SECRET",     "test-secret")
    monkeypatch.setenv("POLY_API_PASSPHRASE", "test-pass")
    monkeypatch.setenv("POLY_WALLET_ADDRESS", "0xabc")

    fake1, fake2 = MagicMock(), MagicMock()
    with patch("execution.clob_client.ClobClient", side_effect=[fake1, fake2]):
        c1 = cc.get_client()
        cc.reset_client()
        c2 = cc.get_client()
    assert c1 is not c2
    cc.reset_client()
