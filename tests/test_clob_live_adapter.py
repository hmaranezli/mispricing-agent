"""tests/test_clob_live_adapter.py — v0→v1 Live Schema Adapter / ACL (thin).

Canlı `get_trades_paginated` page'ini resolver v0 trades-dict'ine çevirir. Karar kaynağı:
docs/ARAF_PHASE_CLOSEOUT.md §8.4 (kalibrasyon, DÜZELTİLDİ). Tek zorunlu yapısal dönüşüm =
page["trades"] → trades_dict["data"]; trade-level alanlar PASS-THROUGH (rename yok); next_cursor
taşınır (zero-fill scan-complete `=="LTE="` için); limit/count resolver dict'ine SIZMAZ.

Adapter Decimal/math/fee_amount ÜRETMEZ; numerikler string kalır (Decimal parse resolver-owned).
Fixture maskeli (gerçek ID/adres/miktar yok — nötr placeholder). Canlı API/DB yok (saf, I/O-free).
"""
import pytest


# ── 1) RED: page envelope transform (trades → data) + pass-through + metadata sınırı ──

def test_adapt_live_trades_page_renames_trades_to_data():
    """Canlı page → resolver trades-dict: `trades` listesi `data`'ya taşınır (rename), next_cursor
    korunur, limit/count resolver dict'ine sızmaz, trade-level alanlar birebir pass-through kalır.

    İlk RED structural: `data.clob_live_adapter.adapt_live_trades_page` henüz yok → ImportError.
    """
    # Import test GÖVDESİNDE → modül yoksa temiz "1 failed" (collection error DEĞİL).
    from data.clob_live_adapter import adapt_live_trades_page

    # Maskeli canlı-şekilli page (gerçek ID/adres/miktar yok; nötr placeholder).
    live_page = {
        "trades": [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "status": "CONFIRMED",
                "taker_order_id": "0x" + "1" * 64,
                "side": "BUY",
                "size": "10",
                "price": "0.42",
                "fee_rate_bps": "0",
                "maker_orders": [
                    {
                        "order_id": "0x" + "2" * 64,
                        "matched_amount": "10",
                        "price": "0.42",
                        "fee_rate_bps": "0",
                        "side": "SELL",
                    }
                ],
            }
        ],
        "next_cursor": "LTE=",
        "limit": 300,
        "count": 1,
    }

    out = adapt_live_trades_page(live_page)

    # Çıktı dict olmalı.
    assert isinstance(out, dict)

    # Zorunlu transform: page["trades"] → out["data"] (rename), liste birebir taşınır.
    assert "data" in out
    assert out["data"] == live_page["trades"]

    # next_cursor taşınır (resolver zero-fill scan-complete için zorunlu okur).
    assert out["next_cursor"] == "LTE="

    # limit/count resolver dict'ine SIZMAZ (driver/crawler telemetry'si).
    assert "limit" not in out
    assert "count" not in out

    # Trade-level alanlar PASS-THROUGH (rename yok; numerikler string kalır).
    t = out["data"][0]
    assert t["id"] == "00000000-0000-0000-0000-000000000001"
    assert t["status"] == "CONFIRMED"
    assert t["taker_order_id"] == "0x" + "1" * 64
    assert t["side"] == "BUY"
    assert t["size"] == "10"
    assert t["price"] == "0.42"
    assert t["fee_rate_bps"] == "0"
    m = t["maker_orders"][0]
    assert m["order_id"] == "0x" + "2" * 64
    assert m["matched_amount"] == "10"
    assert m["price"] == "0.42"
    assert m["fee_rate_bps"] == "0"
    assert m["side"] == "SELL"


# ── 2) Structural fail-closed matrix: yapısal ihlalde LiveSchemaError (resolver'a bozuk dict gitmez) ──

def test_adapt_live_trades_page_non_dict_page_fail_closed():
    """page dict değilse → LiveSchemaError (uydurma boş sayfa DÖNDÜRÜLMEZ)."""
    from data.clob_live_adapter import adapt_live_trades_page, LiveSchemaError
    with pytest.raises(LiveSchemaError):
        adapt_live_trades_page(["not", "a", "dict"])


def test_adapt_live_trades_page_missing_trades_fail_closed():
    """page'de 'trades' yoksa → LiveSchemaError."""
    from data.clob_live_adapter import adapt_live_trades_page, LiveSchemaError
    with pytest.raises(LiveSchemaError):
        adapt_live_trades_page({"next_cursor": "LTE=", "limit": 300, "count": 0})


def test_adapt_live_trades_page_trades_not_list_fail_closed():
    """page['trades'] list değilse → LiveSchemaError."""
    from data.clob_live_adapter import adapt_live_trades_page, LiveSchemaError
    with pytest.raises(LiveSchemaError):
        adapt_live_trades_page({"trades": {"not": "a list"}, "next_cursor": "LTE="})


def test_adapt_live_trades_page_missing_next_cursor_fail_closed():
    """page'de 'next_cursor' yoksa → LiveSchemaError (resolver zero-fill scan-complete için zorunlu)."""
    from data.clob_live_adapter import adapt_live_trades_page, LiveSchemaError
    with pytest.raises(LiveSchemaError):
        adapt_live_trades_page({"trades": [], "limit": 300, "count": 0})


def test_adapt_live_trades_page_trade_element_not_dict_fail_closed():
    """trades list elemanı dict değilse → LiveSchemaError (sığ shape check)."""
    from data.clob_live_adapter import adapt_live_trades_page, LiveSchemaError
    with pytest.raises(LiveSchemaError):
        adapt_live_trades_page({"trades": ["not-a-dict"], "next_cursor": "LTE="})
