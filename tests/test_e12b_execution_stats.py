"""tests/test_e12b_execution_stats.py — E12b ExecutionStats abstraction (tech-debt TDD).

E10/E11 process-runtime sayaçları (`_SESSION_TRADE_COUNT` / `_NO_FILL_STREAK` / `_SESSION_SUBMIT_COUNT`)
ve reset/increment helper'ları main_loop'a yayıldı; testler iç detayları tek tek patch'liyor. E12b bu
sayaçları tek bir saf `ExecutionStats` nesnesinde merkezileştirir (tek izolasyon yüzeyi). Bu slice
DAVRANIŞI DEĞİŞTİRMEZ — yalnız abstraction'ı pin'ler; main_loop wiring / persistence / DB / schema YOK.

Hedef eksik seam:
    from monitor.execution_stats import ExecutionStats

İlk RED: monitor.execution_stats / ExecutionStats yok → ImportError/ModuleNotFoundError (eksik üretim
seam'i; syntax/unrelated import hatası DEĞİL). Saf in-memory nesne; canlı API/DB/order/Telegram YOK.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor.execution_stats import ExecutionStats


def test_default_starts_at_zero():
    """Varsayılan kurucu → üç sayaç da 0."""
    s = ExecutionStats()
    assert s.trade_count == 0
    assert s.no_fill_streak == 0
    assert s.submit_count == 0


def test_constructor_accepts_initial_counts():
    """Kurucu başlangıç değerleri kabul eder; property'ler tam o plain int'leri döndürür."""
    s = ExecutionStats(trade_count=1, no_fill_streak=2, submit_count=3)
    assert s.trade_count == 1
    assert s.no_fill_streak == 2
    assert s.submit_count == 3
    assert isinstance(s.trade_count, int)
    assert isinstance(s.no_fill_streak, int)
    assert isinstance(s.submit_count, int)


def test_negative_trade_count_raises():
    with pytest.raises(ValueError):
        ExecutionStats(trade_count=-1)


def test_negative_no_fill_streak_raises():
    with pytest.raises(ValueError):
        ExecutionStats(no_fill_streak=-1)


def test_negative_submit_count_raises():
    with pytest.raises(ValueError):
        ExecutionStats(submit_count=-1)


def test_increment_trade_count_only():
    s = ExecutionStats()
    s.increment_trade_count()
    assert s.trade_count == 1
    assert s.no_fill_streak == 0
    assert s.submit_count == 0


def test_increment_no_fill_streak_only():
    s = ExecutionStats()
    s.increment_no_fill_streak()
    assert s.no_fill_streak == 1
    assert s.trade_count == 0
    assert s.submit_count == 0


def test_increment_submit_count_only():
    s = ExecutionStats()
    s.increment_submit_count()
    assert s.submit_count == 1
    assert s.trade_count == 0
    assert s.no_fill_streak == 0


def test_reset_trade_count_only():
    s = ExecutionStats(trade_count=5, no_fill_streak=2, submit_count=3)
    s.reset_trade_count()
    assert s.trade_count == 0
    assert s.no_fill_streak == 2
    assert s.submit_count == 3


def test_reset_no_fill_streak_only():
    s = ExecutionStats(trade_count=5, no_fill_streak=2, submit_count=3)
    s.reset_no_fill_streak()
    assert s.no_fill_streak == 0
    assert s.trade_count == 5
    assert s.submit_count == 3


def test_reset_submit_count_only():
    s = ExecutionStats(trade_count=5, no_fill_streak=2, submit_count=3)
    s.reset_submit_count()
    assert s.submit_count == 0
    assert s.trade_count == 5
    assert s.no_fill_streak == 2


def test_reset_all_zeroes_everything():
    s = ExecutionStats(trade_count=5, no_fill_streak=2, submit_count=3)
    s.reset_all()
    assert s.trade_count == 0
    assert s.no_fill_streak == 0
    assert s.submit_count == 0


def test_snapshot_returns_plain_dict():
    s = ExecutionStats(trade_count=1, no_fill_streak=2, submit_count=3)
    assert s.snapshot() == {"trade_count": 1, "no_fill_streak": 2, "submit_count": 3}


def test_snapshot_is_non_mutating():
    """Dönen dict'i düzenlemek ExecutionStats nesnesini DEĞİŞTİRMEZ."""
    s = ExecutionStats(trade_count=1, no_fill_streak=2, submit_count=3)
    snap = s.snapshot()
    snap["trade_count"] = 999
    snap["no_fill_streak"] = 999
    snap["submit_count"] = 999
    assert s.trade_count == 1
    assert s.no_fill_streak == 2
    assert s.submit_count == 3


def test_counters_never_negative_via_public_api():
    """Public API üzerinden sayaçlar asla negatife düşmez (reset 0'da idempotent)."""
    s = ExecutionStats()
    s.reset_trade_count()
    s.reset_no_fill_streak()
    s.reset_submit_count()
    s.reset_all()
    assert s.trade_count == 0
    assert s.no_fill_streak == 0
    assert s.submit_count == 0
