"""tests/test_monitor.py — monitor/ birim testleri. Sıfır gerçek HTTP/dosya."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch
import monitor.notifier as notifier
import monitor.kill_switch as ks


# ── Notifier ─────────────────────────────────────────────────────────────────

def test_send_telegram_calls_post_when_token_set():
    """Token + chat_id varsa requests.post çağrılır."""
    with patch.object(notifier.config, "TELEGRAM_BOT_TOKEN", "tok123"), \
         patch.object(notifier.config, "TELEGRAM_CHAT_ID", "chat456"), \
         patch("monitor.notifier.requests.post") as mock_post:
        notifier.send_telegram("test mesajı")
    mock_post.assert_called_once()


def test_send_telegram_no_op_when_token_missing():
    """Token yoksa requests.post hiç çağrılmaz."""
    with patch.object(notifier.config, "TELEGRAM_BOT_TOKEN", None), \
         patch("monitor.notifier.requests.post") as mock_post:
        notifier.send_telegram("test")
    mock_post.assert_not_called()


def test_dry_run_prefix_in_message():
    """DRY_RUN=True iken mesaj '[DRY RUN]' ile başlar."""
    with patch.object(notifier.config, "TELEGRAM_BOT_TOKEN", "tok"), \
         patch.object(notifier.config, "TELEGRAM_CHAT_ID", "c"), \
         patch.object(notifier.config, "DRY_RUN", True), \
         patch("monitor.notifier.requests.post") as mock_post:
        notifier.send_telegram("merhaba")
    text = mock_post.call_args[1]["json"]["text"]
    assert text.startswith("[DRY RUN]")


def test_notify_open_contains_asset_and_action():
    """notify_open mesajı asset ve action içerir."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_open({"asset": "BTC", "action": "YES",
                               "edge": 0.20, "position_usd": 25.0})
    msg = mock_send.call_args[0][0]
    assert "BTC" in msg and "YES" in msg


def test_notify_close_contains_exit_reason():
    """notify_close mesajı exit_reason içerir."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_close({"asset": "ETH", "action": "NO",
                                "exit_reason": "max_hold_time"})
    msg = mock_send.call_args[0][0]
    assert "max_hold_time" in msg


def test_notify_halt_contains_reason():
    """notify_halt mesajı sebep string'ini içerir."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_halt("daily_loss_limit")
    msg = mock_send.call_args[0][0]
    assert "daily_loss_limit" in msg


def test_notify_close_shows_pnl_when_exit_price_known():
    """pm_exit_price bilinince mesajda P&L satırı görünür."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_close({
            "asset": "ETH", "action": "NO",
            "exit_reason": "market_resolved",
            "pm_entry_price": 0.31,
            "pm_exit_price": 0.0,
            "position_usd": 50.0,
        })
    msg = mock_send.call_args[0][0]
    assert "P&L" in msg
    assert "-" in msg  # kayıp


def test_notify_close_shows_exit_amount_and_pct():
    """notify_close çıkış tutarını ve yüzdeyi gösterir — '50 giriyor 90 çıkıyor' formatı."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_close({
            "asset": "BTC", "action": "NO",
            "exit_reason": "thesis_invalidated",
            "pm_entry_price": 0.49,
            "pm_exit_price": 0.89,   # NO bid, doğru fiyat
            "position_usd": 50.0,
        })
    msg = mock_send.call_args[0][0]
    # Giriş $50 görünmeli
    assert "$50" in msg
    # Çıkış ~$90.82 görünmeli (50 * 0.89/0.49)
    assert "90" in msg
    # Yüzde görünmeli
    assert "%" in msg
    # Kar olduğu için + işareti
    assert "+" in msg


def test_notify_close_no_pnl_when_exit_price_missing():
    """pm_exit_price yoksa P&L satırı olmaz."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_close({
            "asset": "BTC", "action": "YES",
            "exit_reason": "market_expired",
            "pm_entry_price": 0.35,
            "pm_exit_price": None,
            "position_usd": 25.0,
        })
    msg = mock_send.call_args[0][0]
    assert "P&L" not in msg


# ── Kill Switch ───────────────────────────────────────────────────────────────

def test_kill_switch_true_when_file_exists(tmp_path, monkeypatch):
    """logs/KILL dosyası varsa check() True döner."""
    kill_file = tmp_path / "KILL"
    monkeypatch.setattr(ks, "KILL_FILE", kill_file)
    ks.arm()
    assert ks.check() is True


def test_kill_switch_false_when_file_absent(tmp_path, monkeypatch):
    """logs/KILL dosyası yoksa check() False döner."""
    kill_file = tmp_path / "KILL"
    monkeypatch.setattr(ks, "KILL_FILE", kill_file)
    assert ks.check() is False
