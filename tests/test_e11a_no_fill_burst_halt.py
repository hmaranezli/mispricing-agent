"""tests/test_e11a_no_fill_burst_halt.py — E11a no-fill burst pure predicate (TDD).

Execution-quality breaker: arka arkaya no-fill/no-open (FAK_ZERO_FILL / RECOVERY_REQUIRED /
prevalidation-reject) çıktısı burst eşiğine ulaşınca yeni girişler durmalı (capital korunmadı,
sadece submit gürültüsü). E11a YALNIZ saf predicate'i pin'ler — sayaç enjekte; DB/API/canlı state/
main_loop/entry-gate YOK (E10a `max_trades_first_session_halt` / E1 `daily_loss_halt` simetrisi).

Hedef eksik seam:
    from monitor.circuit_breaker import no_fill_burst_halt

İlk RED: `no_fill_burst_halt` yok → ImportError/AttributeError (eksik üretim seam'i; syntax/unrelated
import hatası DEĞİL). config.NO_FILL_BURST_LIMIT EKLENMEZ (human-owned, ayrı config-only slice).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from monitor.circuit_breaker import no_fill_burst_halt


def test_below_limit_returns_none():
    """streak < limit → None (henüz burst değil)."""
    assert no_fill_burst_halt(2, limit=3) is None


def test_at_limit_returns_stop():
    """streak == limit → "no_fill_burst_stop"."""
    assert no_fill_burst_halt(3, limit=3) == "no_fill_burst_stop"


def test_above_limit_returns_stop():
    """streak > limit → "no_fill_burst_stop"."""
    assert no_fill_burst_halt(5, limit=3) == "no_fill_burst_stop"


def test_zero_streak_returns_none():
    """streak 0 → None (sınır altı)."""
    assert no_fill_burst_halt(0, limit=3) is None


def test_explicit_limit_overrides_config(monkeypatch):
    """explicit limit, config'ten bağımsız uygulanır (config 99 olsa bile limit=2 geçerli)."""
    monkeypatch.setattr(config, "NO_FILL_BURST_LIMIT", 99, raising=False)
    assert no_fill_burst_halt(2, limit=2) == "no_fill_burst_stop"


def test_limit_none_reads_config_when_present(monkeypatch):
    """limit=None → config.NO_FILL_BURST_LIMIT okunur (monkeypatch ile)."""
    monkeypatch.setattr(config, "NO_FILL_BURST_LIMIT", 2, raising=False)
    assert no_fill_burst_halt(1) is None
    assert no_fill_burst_halt(2) == "no_fill_burst_stop"


def test_limit_none_falls_back_to_three_when_config_missing(monkeypatch):
    """limit=None ve config.NO_FILL_BURST_LIMIT yok → güvenli fallback 3."""
    monkeypatch.delattr(config, "NO_FILL_BURST_LIMIT", raising=False)
    assert no_fill_burst_halt(2) is None
    assert no_fill_burst_halt(3) == "no_fill_burst_stop"


def test_negative_streak_raises():
    """no_fill_streak < 0 → ValueError (sayaç negatif olamaz)."""
    with pytest.raises(ValueError):
        no_fill_burst_halt(-1, limit=3)


def test_non_positive_limit_raises():
    """limit <= 0 → ValueError."""
    with pytest.raises(ValueError):
        no_fill_burst_halt(0, limit=0)
    with pytest.raises(ValueError):
        no_fill_burst_halt(0, limit=-2)
