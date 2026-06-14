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


def test_notify_emergency_pause_emits_operator_alert():
    """D#6 gap: DB emergency_pause TRIP operatöre Telegram alert üretmeli. notify_emergency_pause
    wrapper'ı reason + source'u mesaja koyar (notify_halt deseniyle simetrik). Network yok
    (send_telegram patch'li). İlk RED: notify_emergency_pause henüz YOK → AttributeError."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_emergency_pause(reason="FAK_RESIDUAL_LIVE", source="reconcile")
    assert mock_send.called, "emergency_pause notify send_telegram çağırmalı"
    msg = mock_send.call_args[0][0]
    assert "FAK_RESIDUAL_LIVE" in msg, f"reason mesajda olmalı: {msg!r}"
    assert "reconcile" in msg, f"source mesajda olmalı: {msg!r}"


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


def test_notify_resolved_late_kazandi():
    """WIN pozisyon için GÜNCELLENDİ + ✅ içeren mesaj gönderir."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_resolved_late({
            "seq_no": 56, "asset": "XRP", "action": "YES",
            "pm_entry_price": 0.5, "pm_exit_price": 1.0, "position_usd": 1.25,
        })
    msg = mock_send.call_args[0][0]
    assert "GÜNCELLENDİ" in msg
    assert "#56" in msg
    assert "XRP" in msg
    assert "✅" in msg


def test_notify_resolved_late_kaybetti():
    """LOSS pozisyon için ❌ içeren mesaj gönderir."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_resolved_late({
            "seq_no": 10, "asset": "BTC", "action": "YES",
            "pm_entry_price": 0.51, "pm_exit_price": 0.0, "position_usd": 1.25,
        })
    msg = mock_send.call_args[0][0]
    assert "❌" in msg


def test_notify_resolved_late_no_exit_price():
    """pm_exit_price=None ise P&L satırı olmadan yine de mesaj gönderir."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_resolved_late({
            "asset": "ETH", "action": "NO",
            "pm_entry_price": 0.5, "pm_exit_price": None, "position_usd": 1.25,
        })
    mock_send.assert_called_once()


# ── HL fiyat bildirim testleri ────────────────────────────────────────────────

def _send_notifier(fn, pos):
    """fn'i çağır, gönderilen mesaj metnini döndür."""
    with patch("monitor.notifier.requests.post") as mock_post, \
         patch("monitor.notifier.config") as cfg:
        mock_post.return_value.status_code = 200
        cfg.TELEGRAM_BOT_TOKEN = "tok"
        cfg.TELEGRAM_CHAT_ID   = "123"
        cfg.DRY_RUN            = True
        fn(pos)
        return mock_post.call_args[1]["json"]["text"]


def _base_pos(**kwargs):
    base = {
        "position_id": "pos-01", "asset": "BTC", "action": "YES",
        "slug": "btc-up-5m", "pm_entry_price": 0.35, "fair_value": 0.55,
        "edge": 0.20, "position_usd": 1.25, "seq_no": 42,
        "exit_reason": "thesis_invalidated", "pm_exit_price": 0.72,
    }
    return {**base, **kwargs}


def test_notify_open_shows_entry_hl_price():
    """notify_open entry_hl_price'ı göstermeli."""
    from monitor import notifier
    text = _send_notifier(notifier.notify_open, _base_pos(entry_hl_price=66500.0))
    assert "66,500" in text or "66500" in text, f"HL fiyatı bildirimde yok: {text}"


def test_notify_open_no_crash_without_hl_price():
    """entry_hl_price yokken notify_open hata vermemeli."""
    from monitor import notifier
    _send_notifier(notifier.notify_open, _base_pos())


def test_notify_close_shows_hl_entry_and_exit():
    """notify_close hem entry hem exit HL göstermeli."""
    from monitor import notifier
    text = _send_notifier(notifier.notify_close, _base_pos(entry_hl_price=66500.0, exit_hl_price=66502.0))
    assert "66,500" in text or "66500" in text, f"entry HL yok: {text}"
    assert "66,502" in text or "66502" in text, f"exit HL yok: {text}"


def test_notify_close_no_crash_without_hl():
    """HL fiyatlar yokken notify_close hata vermemeli."""
    from monitor import notifier
    _send_notifier(notifier.notify_close, _base_pos())


def test_notify_resolved_late_shows_hl_prices():
    """notify_resolved_late HL giriş ve çıkış göstermeli."""
    from monitor import notifier
    pos = {
        "seq_no": 42, "asset": "BTC", "action": "YES",
        "pm_entry_price": 0.35, "pm_exit_price": 1.0, "position_usd": 1.25,
        "entry_hl_price": 66500.0, "exit_hl_price": 66510.0,
    }
    text = _send_notifier(notifier.notify_resolved_late, pos)
    assert "66,500" in text or "66500" in text, f"entry HL yok: {text}"
    assert "66,510" in text or "66510" in text, f"exit HL yok: {text}"


def test_notify_resolved_late_no_crash_without_hl():
    """HL fiyatlar yokken notify_resolved_late hata vermemeli."""
    from monitor import notifier
    pos = {"seq_no": 1, "asset": "BTC", "action": "YES",
           "pm_entry_price": 0.35, "pm_exit_price": 1.0, "position_usd": 1.25}
    _send_notifier(notifier.notify_resolved_late, pos)
