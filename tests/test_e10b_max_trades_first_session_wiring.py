"""tests/test_e10b_max_trades_first_session_wiring.py — E10b max-trades entry-path wiring (TDD).

E10a `max_trades_first_session_halt` saf predicate hazır ama entry-path ÇAĞIRMIYOR. E10b: _scan_and_execute
session işlem sayısını `_session_trade_count()` ile alıp `max_trades_first_session_halt`'a geçirmeli;
"max_trades_stop" → execute'tan ÖNCE yeni giriş engellenmeli (entry-only; _monitor_positions/exit
etkilenmez). Sayı ENJEKTE (in-memory, DB COUNT YOK); restart-safe değil; RiskStateSnapshot şeması değişmez.

Seam: `main_loop._session_trade_count()` (E5/E6 _effective_risk_mode gibi enjekte edilebilir). config
NEW_ENTRIES_ENABLED=True + _effective_risk_mode→Operational yapılır ki tek olası blocker max_trades olsun.

İlk RED: _scan_and_execute max_trades'i danışmıyor → limit'te bile execute çağrılır → assert_not_called fail.
Canlı API/DB/order/Telegram yok.
"""
import sys
import os

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import main_loop


def _finding():
    return {"slug": "btc-updown-15m-t", "action": "YES", "fair_value": 0.6,
            "best_ask": 0.45, "edge": 0.15, "seconds_remaining": 600}


async def _run_scan_with_session_count(count):
    """_scan_and_execute'i NEW_ENTRIES + Operational + enjekte session count ile koşar; execute spy döner."""
    mock_exec = AsyncMock(return_value=None)
    with patch.object(config, "NEW_ENTRIES_ENABLED", True), \
         patch("main_loop._effective_risk_mode", create=True, new=MagicMock(return_value="Operational")), \
         patch("main_loop._session_trade_count", create=True, new=MagicMock(return_value=count)), \
         patch("main_loop._session_submit_count", create=True, new=MagicMock(return_value=count)), \
         patch("main_loop.scan_edges", new_callable=AsyncMock, return_value=[_finding()]), \
         patch("main_loop._run_council", new_callable=AsyncMock, return_value=({}, {})), \
         patch("main_loop.execute", mock_exec):
        await main_loop._scan_and_execute([], [], bankroll_usd=1000.0)
    return mock_exec


@pytest.mark.asyncio
async def test_below_limit_allows_entry():
    """session count < MAX_TRADES_FIRST_SESSION (6) → execute ÇAĞRILIR."""
    mock_exec = await _run_scan_with_session_count(5)
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_at_limit_blocks_entry():
    """session count == 6 → yeni giriş ENGELLENİR (execute ÇAĞRILMAZ). İlk RED: gate yok → execute çağrılır."""
    mock_exec = await _run_scan_with_session_count(6)
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_above_limit_blocks_entry():
    """session count > 6 → yeni giriş ENGELLENİR (execute ÇAĞRILMAZ)."""
    mock_exec = await _run_scan_with_session_count(7)
    mock_exec.assert_not_called()
