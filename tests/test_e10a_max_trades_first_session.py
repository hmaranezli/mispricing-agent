"""tests/test_e10a_max_trades_first_session.py — E10a max-trades-first-session predicate (TDD).

E10 envanteri: MAX_TRADES_FIRST_SESSION enforcement YOK (yalnız docs marker). E10a saf predicate'i
pinler: `max_trades_first_session_halt(trades_today, *, limit=None) -> str|None`. daily_loss_halt ile
simetrik status-return; trades_today ENJEKTE (DB/canlı sayım YOK; restart-safe DEĞİL; RiskStateSnapshot
şeması DEĞİŞMEZ; SESSION_LOSS_LIMIT bu slice'ta YOK).

limit None → getattr(config, "MAX_TRADES_FIRST_SESSION", ...). İlk RED: predicate yok → ImportError.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def test_below_limit_returns_none():
    from monitor.circuit_breaker import max_trades_first_session_halt
    assert max_trades_first_session_halt(2, limit=5) is None


def test_at_limit_returns_max_trades_stop():
    from monitor.circuit_breaker import max_trades_first_session_halt
    assert max_trades_first_session_halt(5, limit=5) == "max_trades_stop"


def test_above_limit_returns_max_trades_stop():
    from monitor.circuit_breaker import max_trades_first_session_halt
    assert max_trades_first_session_halt(6, limit=5) == "max_trades_stop"


def test_explicit_limit_overrides_config(monkeypatch):
    """Explicit limit, config'i ezer: config=100 ama limit=5 → 5'te durur."""
    from monitor.circuit_breaker import max_trades_first_session_halt
    monkeypatch.setattr(config, "MAX_TRADES_FIRST_SESSION", 100, raising=False)
    assert max_trades_first_session_halt(5, limit=5) == "max_trades_stop"


def test_limit_none_reads_config(monkeypatch):
    """limit=None → config.MAX_TRADES_FIRST_SESSION okunur."""
    from monitor.circuit_breaker import max_trades_first_session_halt
    monkeypatch.setattr(config, "MAX_TRADES_FIRST_SESSION", 3, raising=False)
    assert max_trades_first_session_halt(3) == "max_trades_stop"
    assert max_trades_first_session_halt(2) is None


def test_negative_trades_today_raises(monkeypatch):
    from monitor.circuit_breaker import max_trades_first_session_halt
    with pytest.raises(ValueError):
        max_trades_first_session_halt(-1, limit=5)


def test_non_positive_limit_raises():
    from monitor.circuit_breaker import max_trades_first_session_halt
    with pytest.raises(ValueError):
        max_trades_first_session_halt(0, limit=0)
