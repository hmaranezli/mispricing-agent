"""tests/test_ws_prices.py — ws_prices birim testleri. Gerçek WS bağlantısı yok."""
import asyncio
import time
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data.ws_prices as ws


def _reset():
    ws._cache.clear()
    ws._subscribed.clear()
    ws._pending.clear()
    ws._resolved_queue = None


def test_get_ask_returns_none_when_not_cached():
    _reset()
    assert ws.get_ask("tok_missing") is None


def test_get_bid_returns_none_when_not_cached():
    _reset()
    assert ws.get_bid("tok_missing") is None


def test_update_cache_and_get_ask():
    _reset()
    ws._update_cache("tok1", best_bid=0.48, best_ask=0.52)
    assert ws.get_ask("tok1") == 0.52
    assert ws.get_bid("tok1") == 0.48


def test_update_cache_spread():
    _reset()
    ws._update_cache("tok2", best_bid=0.73, best_ask=0.77, spread=0.04)
    assert ws.get_spread("tok2") == 0.04


def test_handle_book_extracts_best_bid_and_ask():
    _reset()
    # bids ascending (son = en yüksek), asks ascending (ilk = en düşük)
    event = {
        "event_type": "book",
        "asset_id": "tok3",
        "bids": [{"price": "0.48", "size": "30"}, {"price": "0.50", "size": "15"}],
        "asks": [{"price": "0.52", "size": "25"}, {"price": "0.54", "size": "10"}],
        "timestamp": "1234567890",
    }
    ws._handle_book(event)
    assert ws.get_ask("tok3") == 0.52
    assert ws.get_bid("tok3") == 0.50


def test_handle_book_empty_bids_does_not_crash():
    _reset()
    event = {
        "event_type": "book", "asset_id": "tok_empty",
        "bids": [], "asks": [{"price": "0.60", "size": "10"}], "timestamp": "1",
    }
    ws._handle_book(event)
    assert ws.get_ask("tok_empty") == 0.60
    assert ws.get_bid("tok_empty") is None


def test_handle_price_change_updates_best_bid_ask():
    _reset()
    event = {
        "event_type": "price_change",
        "market": "0x123",
        "price_changes": [{
            "asset_id": "tok4",
            "price": "0.51", "size": "100", "side": "BUY", "hash": "abc",
            "best_bid": "0.51",
            "best_ask": "0.53",
        }],
        "timestamp": "123",
    }
    ws._handle_price_change(event)
    assert ws.get_ask("tok4") == 0.53
    assert ws.get_bid("tok4") == 0.51


def test_handle_price_change_without_best_fields_does_not_crash():
    _reset()
    event = {
        "event_type": "price_change", "market": "0x1",
        "price_changes": [{"asset_id": "tok5", "price": "0.50", "size": "0",
                           "side": "BUY", "hash": "x"}],
        "timestamp": "1",
    }
    ws._handle_price_change(event)  # best_bid/best_ask yok → crash yok
    assert ws.get_ask("tok5") is None


def test_handle_best_bid_ask_event():
    _reset()
    event = {
        "event_type": "best_bid_ask",
        "asset_id": "tok6",
        "market": "0x456",
        "best_bid": "0.73",
        "best_ask": "0.77",
        "spread": "0.04",
        "timestamp": "123",
    }
    ws._handle_best_bid_ask(event)
    assert ws.get_ask("tok6") == 0.77
    assert ws.get_bid("tok6") == 0.73
    assert ws.get_spread("tok6") == 0.04


def test_handle_market_resolved_queues_event():
    _reset()
    ws._resolved_queue = asyncio.Queue()
    event = {
        "event_type": "market_resolved",
        "id": "1234", "market": "0x789",
        "assets_ids": ["yes_tok", "no_tok"],
        "winning_asset_id": "yes_tok",
        "winning_outcome": "Yes",
        "timestamp": "123",
    }
    ws._handle_market_resolved(event)
    assert ws._resolved_queue.qsize() == 1
    queued = ws._resolved_queue.get_nowait()
    assert queued["winning_outcome"] == "Yes"
    assert "yes_tok" in queued["assets_ids"]


def test_handle_market_resolved_no_queue_does_not_crash():
    _reset()
    ws._resolved_queue = None
    event = {"event_type": "market_resolved", "winning_outcome": "No", "assets_ids": []}
    ws._handle_market_resolved(event)  # crash yok


def test_subscribe_adds_to_pending():
    _reset()
    ws.subscribe(["tok_a", "tok_b"])
    assert "tok_a" in ws._pending
    assert "tok_b" in ws._pending


def test_subscribe_skips_already_subscribed():
    _reset()
    ws._subscribed.add("tok_existing")
    ws.subscribe(["tok_existing", "tok_new"])
    assert "tok_existing" not in ws._pending
    assert "tok_new" in ws._pending


def test_subscribe_skips_empty_string():
    _reset()
    ws.subscribe(["", "tok_ok"])
    assert "" not in ws._pending
    assert "tok_ok" in ws._pending


def test_stale_cache_returns_none():
    _reset()
    ws._update_cache("tok_stale", best_bid=0.48, best_ask=0.52)
    ws._cache["tok_stale"]["ts"] = time.time() - (ws.STALE_SECS + 5)
    assert ws.get_ask("tok_stale") is None
    assert ws.get_bid("tok_stale") is None


# ── Task 1: price_event ──────────────────────────────────────────────────────

def test_get_price_event_returns_asyncio_event():
    """get_price_event() bir asyncio.Event döndürür."""
    ws._price_event = None  # modül state sıfırla
    event = ws.get_price_event()
    assert isinstance(event, asyncio.Event)


def test_get_price_event_is_singleton():
    """get_price_event() her çağrıda aynı instance'ı döndürür."""
    ws._price_event = None
    e1 = ws.get_price_event()
    e2 = ws.get_price_event()
    assert e1 is e2


def test_update_cache_sets_price_event():
    """_update_cache() çağrıldığında price_event set edilir."""
    ws._price_event = None
    event = ws.get_price_event()
    event.clear()
    ws._update_cache("tok-test", best_bid=0.50, best_ask=0.52)
    assert event.is_set(), "_update_cache() sonrası price_event set olmalı"


def test_ws_connect_does_not_use_lib_keepalive():
    """_connect_and_run: websockets lib ping_interval/ping_timeout KULLANMAMALI.
    Uygulama seviyesi _ping_loop mekanizması kullanılır; lib ping Polymarket ile uyumsuz.
    """
    import inspect
    source = inspect.getsource(ws._connect_and_run)
    assert "ping_interval" not in source, "ping_interval ws.connect'te olmamalı — _ping_loop kullanılıyor"
    assert "ping_timeout"  not in source, "ping_timeout ws.connect'te olmamalı — _ping_loop kullanılıyor"


def test_ws_circuit_breaker_calls_send_telegram():
    """_warn_ws_circuit_breaker: Telegram uyarısı gönderir."""
    from unittest.mock import patch, MagicMock
    import data.ws_prices as _ws
    mock_send = MagicMock()
    with patch.dict("sys.modules", {"monitor.notifier": MagicMock(send_telegram=mock_send)}):
        # sys.modules patch ile lazy import'u yakala
        import importlib, sys
        mock_mod = MagicMock()
        mock_mod.send_telegram = mock_send
        sys.modules["monitor.notifier"] = mock_mod
        _ws._warn_ws_circuit_breaker(8)
    mock_send.assert_called_once()
    args = mock_send.call_args[0][0]
    assert "8" in args or "WS" in args, "uyarı mesajı reconnect sayısı veya WS içermeli"


def test_apply_partial_fill_modifies_pos_and_returns_true():
    """_apply_partial_fill: kısmi fill → pos güncellenir, True döner."""
    from main_loop import _apply_partial_fill
    pos = {"shares": 2.0, "position_usd": 1.25}
    result = _apply_partial_fill(pos, pm_exit=0.80, making_shares=0.5)
    assert result is True,                        "kısmi fill → True"
    assert pos["shares"] == pytest.approx(1.5),   "kalan shares"
    assert pos.get("_closing") is False,          "_closing sıfırlanmalı"
    assert pos.get("partial_fill_count") == 1
    assert pos.get("partial_fill_shares") == pytest.approx(0.5)
    assert pos.get("partial_realized_usdc") == pytest.approx(0.40)


def test_apply_partial_fill_returns_false_for_full_fill():
    """_apply_partial_fill: tam fill (>=%98) → pos değişmez, False döner."""
    from main_loop import _apply_partial_fill
    pos = {"shares": 2.0, "position_usd": 1.25}
    result = _apply_partial_fill(pos, pm_exit=0.80, making_shares=2.0)
    assert result is False,       "tam fill → False"
    assert pos["shares"] == 2.0,  "tam fill → shares değişmemeli"


# ── Faz 2.5: Guard + PING ──────────────────────────────────────────────────────

def test_ping_interval_is_8():
    """PING_INTERVAL 8s olmalı — sunucunun 10s limitinin 2s öncesi."""
    assert ws.PING_INTERVAL == 8, "PING_INTERVAL 8 olmalı"


def test_ping_loop_first_ping_at_1s():
    """_ping_loop: ilk PING 1s sonra (PING_INTERVAL değil) gönderilmeli."""
    import inspect
    source = inspect.getsource(ws._ping_loop)
    assert "asyncio.sleep(1)" in source, \
        "_ping_loop içinde 1s ilk ping bekleme olmalı"


def test_run_has_no_token_guard():
    """run(): token yokken bağlanma — guard olmalı."""
    import inspect
    source = inspect.getsource(ws.run)
    assert "not _pending and not _subscribed" in source, \
        "run() içinde 'while not _pending and not _subscribed' guard olmalı"


def test_run_circuit_breaker_uses_had_subs():
    """run(): circuit breaker yalnızca gerçekten subscribed bağlantıları saymalı."""
    import inspect
    source = inspect.getsource(ws.run)
    assert "had_subs" in source, \
        "run() içinde had_subs flag'i ile circuit breaker koruması olmalı"
