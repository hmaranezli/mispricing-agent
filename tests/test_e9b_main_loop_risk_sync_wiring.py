"""tests/test_e9b_main_loop_risk_sync_wiring.py — E9b main_loop runtime risk sync wiring (TDD).

E9a `sync_risk_state_from_runtime_signals` hazır ama main_loop ÇAĞIRMIYOR. E9b: ana loop her
iterasyonda runtime sinyalleri toplayıp sync helper'ı entry/gate'ten ÖNCE çağırmalı. En dar testable
seam = `main_loop._sync_runtime_risk_state(closed_today, current_equity, circuit_breaker_status,
kill_switch_active)` — closed_today'den realized_pnl_today TOPLAR, sync helper'ı çağırır, RiskStateCorruptError
PROPAGATE eder (caller iterasyonda yeni girişi fail-closed atlar).

İlk RED: main_loop._sync_runtime_risk_state YOK → AttributeError. Canlı API/DB/order/Telegram/KILL yok
(sync helper + sinyaller monkeypatch/enjekte).

NOT: "sync-scan ordering" (sync ÖNCE) ve "corrupt→scan çağrılmaz" loop-seviyesi davranışları GREEN
call-site'ta (main() döngüsü) bağlanır; bu RED, eksik wiring SEAM'ini + fail-closed propagation'ı pinler.
"""
import sys
import os

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main_loop
from monitor.risk_state_store import RiskStateCorruptError


def _ok_snap():
    # sync helper'ın döndüreceği şey önemsiz (helper persist eder); MagicMock yeter.
    return MagicMock(name="RiskStateSnapshot")


def test_sync_helper_sums_realized_pnl_from_closed_today():
    """realized_pnl_today = sum(closed_today realized_pnl); None/eksik → 0. Canlı DB sorgusu YOK."""
    spy = MagicMock(return_value=_ok_snap())
    closed = [{"realized_pnl": -120.0}, {"realized_pnl": None}, {}, {"realized_pnl": 50.0}]
    with patch("main_loop.sync_risk_state_from_runtime_signals", spy, create=True):
        main_loop._sync_runtime_risk_state(
            closed_today=closed, current_equity=1000.0,
            circuit_breaker_status=None, kill_switch_active=False)
    assert spy.called
    assert spy.call_args.kwargs["realized_pnl_today"] == -70.0   # -120 + 0 + 0 + 50


def test_sync_helper_passes_circuit_breaker_status():
    spy = MagicMock(return_value=_ok_snap())
    with patch("main_loop.sync_risk_state_from_runtime_signals", spy, create=True):
        main_loop._sync_runtime_risk_state(
            closed_today=[], current_equity=1000.0,
            circuit_breaker_status="soft_stop", kill_switch_active=False)
    assert spy.call_args.kwargs["circuit_breaker_status"] == "soft_stop"


def test_sync_helper_passes_kill_switch_active():
    spy = MagicMock(return_value=_ok_snap())
    with patch("main_loop.sync_risk_state_from_runtime_signals", spy, create=True):
        main_loop._sync_runtime_risk_state(
            closed_today=[], current_equity=1000.0,
            circuit_breaker_status=None, kill_switch_active=True)
    assert spy.call_args.kwargs["kill_switch_active"] is True


def test_sync_helper_passes_current_equity():
    spy = MagicMock(return_value=_ok_snap())
    with patch("main_loop.sync_risk_state_from_runtime_signals", spy, create=True):
        main_loop._sync_runtime_risk_state(
            closed_today=[], current_equity=1234.5,
            circuit_breaker_status=None, kill_switch_active=False)
    assert spy.call_args.kwargs["current_equity"] == 1234.5


def test_sync_helper_propagates_corrupt_error_fail_closed():
    """sync RiskStateCorruptError fırlatırsa helper PROPAGATE eder (caller fail-closed: scan atlar)."""
    def _boom(*a, **k):
        raise RiskStateCorruptError("missing/corrupt")
    with patch("main_loop.sync_risk_state_from_runtime_signals", _boom, create=True):
        with pytest.raises(RiskStateCorruptError):
            main_loop._sync_runtime_risk_state(
                closed_today=[], current_equity=1000.0,
                circuit_breaker_status=None, kill_switch_active=False)
