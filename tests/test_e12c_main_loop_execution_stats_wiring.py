"""tests/test_e12c_main_loop_execution_stats_wiring.py — E12c main_loop ↔ ExecutionStats wiring (TDD).

E12b `monitor/execution_stats.py::ExecutionStats` saf konteyner hazır ama main_loop hâlâ üç ayrı
modül-seviyesi int (`_SESSION_TRADE_COUNT`/`_NO_FILL_STREAK`/`_SESSION_SUBMIT_COUNT`) kullanıyor. E12c:
bu sayaçları tek modül-seviyesi `_EXECUTION_STATS` (ExecutionStats instance) ARKASINA alır — mevcut public
helper fonksiyon ADLARI ve DAVRANIŞI korunur (E11b/E11e eşdeğer). Dış davranış/imza değişmez.

NOT: Bu slice'ta dependency injection veya reset-fixture temizliği GEREKMİYOR — mevcut modül-seviyesi
sayaçlarla parite için modül-seviyesi `_EXECUTION_STATS` kabul edilir. DI / fixture cleanup ileride ayrı
bir iyileştirme olabilir, bu RED'in parçası DEĞİL.

İlk RED: main_loop `_EXECUTION_STATS` (ExecutionStats) EXPOSE ETMİYOR → AttributeError / helper'lar hâlâ
ayrı int'lerle besleniyor. Saf in-memory; canlı API/DB/order/Telegram YOK.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main_loop
from monitor.execution_stats import ExecutionStats


@pytest.fixture(autouse=True)
def _reset_stats():
    """Sayaç sızıntısını engelle (mevcut reset helper'ları üzerinden)."""
    def _reset_all():
        for name in ("_reset_session_trade_count", "_reset_no_fill_streak",
                     "_reset_session_submit_count"):
            fn = getattr(main_loop, name, None)
            if callable(fn):
                fn()
    _reset_all()
    yield
    _reset_all()


def test_module_exposes_execution_stats_instance():
    """main_loop modül-seviyesi `_EXECUTION_STATS` bir ExecutionStats örneği olmalı.
    RED: attribute yok → AttributeError."""
    assert isinstance(main_loop._EXECUTION_STATS, ExecutionStats)


# ── trade_count: read / increment / reset, _EXECUTION_STATS üzerinden ─────────
def test_trade_count_reads_execution_stats():
    main_loop._EXECUTION_STATS.reset_all()
    main_loop._EXECUTION_STATS.increment_trade_count()
    main_loop._EXECUTION_STATS.increment_trade_count()
    assert main_loop._session_trade_count() == 2


def test_increment_trade_count_updates_execution_stats():
    main_loop._EXECUTION_STATS.reset_all()
    main_loop._increment_session_trade_count()
    assert main_loop._EXECUTION_STATS.trade_count == 1
    assert main_loop._session_trade_count() == 1


def test_reset_trade_count_only():
    main_loop._EXECUTION_STATS.reset_all()
    main_loop._increment_session_trade_count()
    main_loop._increment_no_fill_streak()
    main_loop._increment_session_submit_count()
    main_loop._reset_session_trade_count()
    assert main_loop._session_trade_count() == 0
    assert main_loop._no_fill_streak() == 1
    assert main_loop._session_submit_count() == 1


# ── no_fill_streak: read / increment / reset ─────────────────────────────────
def test_no_fill_streak_reads_execution_stats():
    main_loop._EXECUTION_STATS.reset_all()
    main_loop._EXECUTION_STATS.increment_no_fill_streak()
    assert main_loop._no_fill_streak() == 1


def test_increment_no_fill_streak_updates_execution_stats():
    main_loop._EXECUTION_STATS.reset_all()
    main_loop._increment_no_fill_streak()
    assert main_loop._EXECUTION_STATS.no_fill_streak == 1
    assert main_loop._no_fill_streak() == 1


def test_reset_no_fill_streak_only():
    main_loop._EXECUTION_STATS.reset_all()
    main_loop._increment_session_trade_count()
    main_loop._increment_no_fill_streak()
    main_loop._increment_session_submit_count()
    main_loop._reset_no_fill_streak()
    assert main_loop._no_fill_streak() == 0
    assert main_loop._session_trade_count() == 1
    assert main_loop._session_submit_count() == 1


# ── submit_count: read / increment / reset ───────────────────────────────────
def test_submit_count_reads_execution_stats():
    main_loop._EXECUTION_STATS.reset_all()
    main_loop._EXECUTION_STATS.increment_submit_count()
    assert main_loop._session_submit_count() == 1


def test_increment_submit_count_updates_execution_stats():
    main_loop._EXECUTION_STATS.reset_all()
    main_loop._increment_session_submit_count()
    assert main_loop._EXECUTION_STATS.submit_count == 1
    assert main_loop._session_submit_count() == 1


def test_reset_submit_count_only():
    main_loop._EXECUTION_STATS.reset_all()
    main_loop._increment_session_trade_count()
    main_loop._increment_no_fill_streak()
    main_loop._increment_session_submit_count()
    main_loop._reset_session_submit_count()
    assert main_loop._session_submit_count() == 0
    assert main_loop._session_trade_count() == 1
    assert main_loop._no_fill_streak() == 1


def test_e11b_no_fill_reset_on_trade_equivalent():
    """E11b eşdeğeri: no-fill birikir, sonra trade reset (gerçek açılış) no-fill'i etkilemez ama
    _reset_no_fill_streak no-fill'i sıfırlar — public helper davranışı korunur."""
    main_loop._EXECUTION_STATS.reset_all()
    main_loop._increment_no_fill_streak()
    main_loop._increment_no_fill_streak()
    assert main_loop._no_fill_streak() == 2
    main_loop._reset_no_fill_streak()
    assert main_loop._no_fill_streak() == 0
