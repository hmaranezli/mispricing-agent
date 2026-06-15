"""tests/test_e6_effective_risk_mode_source.py — E6 _effective_risk_mode kaynak wiring (TDD).

E5 entry-gate `_effective_risk_mode()`'a dayanıyor ama o ŞİMDİLİK sabit "Operational" döndürüyor.
E6: bu fonksiyon PERSIST edilmiş RiskStateSnapshot kaynağından (load_risk_state) modu okumalı.

FAIL-CLOSED: missing/corrupt/okunamaz state → SESSİZCE "Operational" DÖNMEZ; mantıksal fail-closed mod
"Halted" (geçerli snapshot açıkça "Kill-Switch" demedikçe). E5 gate bu gerçek kaynağı kullanır.

Kapsam: kaynak = persist snapshot. build_active_blockers/circuit_breaker/daily_loss_halt/UTC rollover
ÇAĞRILMAZ; persist/güncelleme YOK; config guardrail sabitine dokunulmaz. Bu RED eksik KAYNAK wiring'ini
kanıtlar (reducer/bridge/entry-gate iç davranışı değil). Stub/monkeypatch; canlı DB/API/order YOK.
"""
import sys
import os

import pytest
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import main_loop
from monitor.risk_state_store import RiskStateCorruptError


class _FakeSnap:
    def __init__(self, effective_mode):
        self.effective_mode = effective_mode


def test_effective_risk_mode_uses_persisted_exit_only_snapshot(monkeypatch):
    monkeypatch.setattr(main_loop, "load_risk_state",
                        lambda *a, **k: _FakeSnap("Exit-Only"), raising=False)
    assert main_loop._effective_risk_mode() == "Exit-Only"


def test_effective_risk_mode_uses_persisted_kill_switch_snapshot(monkeypatch):
    monkeypatch.setattr(main_loop, "load_risk_state",
                        lambda *a, **k: _FakeSnap("Kill-Switch"), raising=False)
    assert main_loop._effective_risk_mode() == "Kill-Switch"


def test_effective_risk_mode_fails_closed_on_corrupt_state(monkeypatch):
    def _boom(*a, **k):
        raise RiskStateCorruptError("corrupt")
    monkeypatch.setattr(main_loop, "load_risk_state", _boom, raising=False)
    assert main_loop._effective_risk_mode() == "Halted"   # fail-closed, NOT Operational


def test_effective_risk_mode_fails_closed_on_generic_error(monkeypatch):
    def _boom(*a, **k):
        raise OSError("db unreadable")
    monkeypatch.setattr(main_loop, "load_risk_state", _boom, raising=False)
    assert main_loop._effective_risk_mode() == "Halted"   # fail-closed, NOT Operational


@pytest.mark.asyncio
async def test_scan_and_execute_blocks_when_persisted_mode_exit_only(monkeypatch):
    """E5 gate gerçek kaynağı kullanmalı: persist Exit-Only → execute ÇAĞRILMAZ."""
    monkeypatch.setattr(main_loop, "load_risk_state",
                        lambda *a, **k: _FakeSnap("Exit-Only"), raising=False)
    mock_exec = AsyncMock(return_value=None)
    with patch.object(config, "NEW_ENTRIES_ENABLED", True), \
         patch("main_loop.scan_edges", new_callable=AsyncMock,
               return_value=[{"slug": "btc-updown-15m-t", "action": "YES", "fair_value": 0.6,
                              "best_ask": 0.45, "edge": 0.15, "seconds_remaining": 600}]), \
         patch("main_loop._run_council", new_callable=AsyncMock, return_value=({}, {})), \
         patch("main_loop.execute", mock_exec):
        await main_loop._scan_and_execute([], [], bankroll_usd=1000.0)
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_scan_and_execute_allows_when_persisted_mode_operational(monkeypatch):
    """Persist Operational → execute ÇAĞRILIR (gate fazla bloklamaz)."""
    monkeypatch.setattr(main_loop, "load_risk_state",
                        lambda *a, **k: _FakeSnap("Operational"), raising=False)
    mock_exec = AsyncMock(return_value=None)
    with patch.object(config, "NEW_ENTRIES_ENABLED", True), \
         patch("main_loop.scan_edges", new_callable=AsyncMock,
               return_value=[{"slug": "btc-updown-15m-t", "action": "YES", "fair_value": 0.6,
                              "best_ask": 0.45, "edge": 0.15, "seconds_remaining": 600}]), \
         patch("main_loop._run_council", new_callable=AsyncMock, return_value=({}, {})), \
         patch("main_loop.execute", mock_exec):
        await main_loop._scan_and_execute([], [], bankroll_usd=1000.0)
    mock_exec.assert_called_once()
