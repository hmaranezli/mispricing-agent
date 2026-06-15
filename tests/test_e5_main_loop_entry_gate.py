"""tests/test_e5_main_loop_entry_gate.py — E5 main_loop entry-gate wiring (TDD).

Risk-state çekirdeği (E1b→E4) hazır ama main_loop'a BAĞLI DEĞİL. E5: efektif risk modu "Operational"
değilse main_loop YENİ GİRİŞ açmamalı (execute çağrılmamalı). Bu ENTRY-ONLY gating'tir — exit/risk/
açık-pozisyon yönetimi (_monitor_positions, ayrı) ETKİLENMEZ; süreç restart/kill DEĞİL.

Seam: main_loop._effective_risk_mode() (GREEN'de eklenecek) — _scan_and_execute execute'tan ÖNCE
danışmalı. Test bu seam'i ENJEKTE eder (reducer/bridge iç davranışını test ETMEZ; yalnız wiring).
config.NEW_ENTRIES_ENABLED=True yapılır ki execute'u blokayabilecek TEK şey risk-gate olsun.

SAF/offline: scan_edges/_run_council/execute stub; canlı API/DB/order/Telegram YOK. İlk RED:
_effective_risk_mode YOK + _scan_and_execute onu danışmıyor → Halted'da bile execute çağrılır → fail.
"""
import sys
import os

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from main_loop import _scan_and_execute


def _finding():
    return {"slug": "btc-updown-15m-test", "action": "YES", "fair_value": 0.60,
            "best_ask": 0.45, "edge": 0.15, "seconds_remaining": 600}


@pytest.mark.asyncio
async def test_non_operational_mode_blocks_new_entry():
    """Efektif risk modu Halted → yeni giriş ENGELLENİR (execute ÇAĞRILMAZ). Entry-only gate.
    İlk RED: _scan_and_execute risk modunu danışmıyor → execute çağrılır → assert_not_called fail."""
    mock_exec = AsyncMock(return_value=None)
    with patch.object(config, "NEW_ENTRIES_ENABLED", True), \
         patch("main_loop.scan_edges", new_callable=AsyncMock, return_value=[_finding()]), \
         patch("main_loop._run_council", new_callable=AsyncMock, return_value=({}, {})), \
         patch("main_loop.execute", mock_exec), \
         patch("main_loop._effective_risk_mode", create=True,
               new=MagicMock(return_value="Halted")):
        await _scan_and_execute([], [], bankroll_usd=1000.0)
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_operational_mode_allows_new_entry():
    """Efektif risk modu Operational → yeni giriş yolu ilerleyebilir (execute ÇAĞRILIR). Gate fazla
    bloklamamalı (bu, GREEN'in entry-only kalmasını sabitler)."""
    mock_exec = AsyncMock(return_value=None)
    with patch.object(config, "NEW_ENTRIES_ENABLED", True), \
         patch("main_loop.scan_edges", new_callable=AsyncMock, return_value=[_finding()]), \
         patch("main_loop._run_council", new_callable=AsyncMock, return_value=({}, {})), \
         patch("main_loop.execute", mock_exec), \
         patch("main_loop._effective_risk_mode", create=True,
               new=MagicMock(return_value="Operational")):
        await _scan_and_execute([], [], bankroll_usd=1000.0)
    mock_exec.assert_called_once()
