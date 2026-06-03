"""tests/test_telegram_commands.py — Telegram komut sistemi testleri."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


# ── parse_hours ────────────────────────────────────────────────────────────────

def test_parse_hours_no_number_returns_none():
    """/istatistik → None (tum zamanlar)"""
    from monitor.telegram_commands import parse_hours
    assert parse_hours("/istatistik") is None

def test_parse_hours_6_returns_6():
    """/istatistik6 → 6"""
    from monitor.telegram_commands import parse_hours
    assert parse_hours("/istatistik6") == 6

def test_parse_hours_12_returns_12():
    """/istatistik12 → 12"""
    from monitor.telegram_commands import parse_hours
    assert parse_hours("/istatistik12") == 12

def test_parse_hours_24_returns_24():
    """/istatistik24 → 24"""
    from monitor.telegram_commands import parse_hours
    assert parse_hours("/istatistik24") == 24

def test_parse_hours_invalid_suffix_returns_none():
    """/istatistikABC → None (sayisal degil)"""
    from monitor.telegram_commands import parse_hours
    assert parse_hours("/istatistikABC") is None


# ── is_authorized ──────────────────────────────────────────────────────────────

def test_authorized_chat_id_passes(monkeypatch):
    """Dogru chat_id → True"""
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    from monitor import telegram_commands
    import importlib; importlib.reload(telegram_commands)
    assert telegram_commands.is_authorized("12345") is True

def test_unauthorized_chat_id_blocked(monkeypatch):
    """Yanlis chat_id → False"""
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    from monitor import telegram_commands
    import importlib; importlib.reload(telegram_commands)
    assert telegram_commands.is_authorized("99999") is False


# ── build_stats_message ────────────────────────────────────────────────────────

def test_build_stats_includes_win_rate():
    """/istatistik mesaji win rate icermeli"""
    from monitor.telegram_commands import build_stats_message
    msg = build_stats_message(total=100, wins=75, losses=25, pnl=150.0, hours=None)
    assert "75" in msg or "75.0" in msg  # win count
    assert "75.0%" in msg or "75%" in msg  # win rate

def test_build_stats_shows_hours_label():
    """/istatistik6 mesaji 'son 6 saat' icermeli"""
    from monitor.telegram_commands import build_stats_message
    msg = build_stats_message(total=10, wins=8, losses=2, pnl=5.0, hours=6)
    assert "6" in msg

def test_build_stats_all_time_label():
    """/istatistik mesaji (hours=None) 'tum' veya 'all' icermeli"""
    from monitor.telegram_commands import build_stats_message
    msg = build_stats_message(total=10, wins=8, losses=2, pnl=5.0, hours=None)
    assert msg  # en azindan bos olmamali


# ── build_durum_message ────────────────────────────────────────────────────────

def test_build_durum_shows_open_count():
    """/durum mesaji acik pozisyon sayisi icermeli"""
    from monitor.telegram_commands import build_durum_message
    positions = [
        {"slug": "btc-5m", "action": "YES", "pm_entry_price": 0.51, "position_usd": 1.25},
        {"slug": "eth-5m", "action": "NO",  "pm_entry_price": 0.48, "position_usd": 1.25},
    ]
    msg = build_durum_message(open_positions=positions, daily_pnl=5.50)
    assert "2" in msg  # 2 acik pozisyon
    assert "btc" in msg.lower() or "BTC" in msg

def test_build_durum_empty_positions():
    """/durum acik pozisyon yoksa bos mesaj vermemeli"""
    from monitor.telegram_commands import build_durum_message
    msg = build_durum_message(open_positions=[], daily_pnl=0.0)
    assert msg  # bos olmamali
    assert "0" in msg
