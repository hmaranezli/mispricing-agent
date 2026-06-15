"""tests/test_e11c_no_fill_burst_gate_wiring.py — E11c no-fill burst entry-gate wiring (TDD).

E11a `no_fill_burst_halt` saf predicate + E11b `_no_fill_streak` in-memory sayaç hazır ama
`_scan_and_execute` HENÜZ gate'i DANIŞMIYOR. E11c: execute öncesi (E5 risk-mode + NEW_ENTRIES ve
E10b max-trades gate'lerinden SONRA) `no_fill_burst_halt(_no_fill_streak())` çağrılmalı;
"no_fill_burst_stop" → yeni giriş execute'tan ÖNCE engellenmeli (entry-only; _monitor_positions/
panic-flatten/sell_position/exit DOKUNULMAZ).

İzolasyon: _effective_risk_mode→Operational, NEW_ENTRIES_ENABLED→True, _session_trade_count→0 (E5/E10b
bloklamasın, no-fill gate tek differansiyel olsun). no-fill eşiği gerçek default fallback 3
(config.NO_FILL_BURST_LIMIT yok). _no_fill_streak ENJEKTE edilir; gerçek no_fill_burst_halt kullanılır.

İlk RED: _scan_and_execute no-fill gate'i danışmıyor → eşik/üstünde bile execute ÇAĞRILIR →
assert_not_called fail ("Expected execute not to have been called"). Canlı API/DB/order/Telegram yok.
"""
import os
import sys

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import main_loop


SLUG = "btc-updown-15m-t"


@pytest.fixture(autouse=True)
def _reset_streaks():
    """no-fill / session sayaç sızıntısını engelle (execute() None çağrıları gerçek sayacı oynatabilir)."""
    for name in ("_reset_no_fill_streak", "_reset_session_trade_count"):
        fn = getattr(main_loop, name, None)
        if callable(fn):
            fn()
    yield
    for name in ("_reset_no_fill_streak", "_reset_session_trade_count"):
        fn = getattr(main_loop, name, None)
        if callable(fn):
            fn()


def _finding():
    return {"slug": SLUG, "action": "YES", "fair_value": 0.6,
            "best_ask": 0.45, "edge": 0.15, "seconds_remaining": 600}


async def _run_scan_with_no_fill_streak(streak):
    """_scan_and_execute'i NEW_ENTRIES + Operational + E10b-bypass + enjekte no-fill streak ile koşar;
    GERÇEK no_fill_burst_halt (default limit 3) kullanılır. execute spy döner."""
    mock_exec = AsyncMock(return_value=None)
    with patch.object(config, "NEW_ENTRIES_ENABLED", True), \
         patch("main_loop._effective_risk_mode", new=MagicMock(return_value="Operational")), \
         patch("main_loop._session_trade_count", new=MagicMock(return_value=0)), \
         patch("main_loop._no_fill_streak", new=MagicMock(return_value=streak)), \
         patch("main_loop.scan_edges", new_callable=AsyncMock, return_value=[_finding()]), \
         patch("main_loop._run_council", new_callable=AsyncMock, return_value=({}, {})), \
         patch("main_loop.log_position_open", new_callable=AsyncMock), \
         patch("main_loop.ws_prices", new=MagicMock()), \
         patch("main_loop.execute", mock_exec):
        await main_loop._scan_and_execute([], [], 1000.0)
    return mock_exec


@pytest.mark.asyncio
async def test_below_limit_allows_entry():
    """no-fill streak < limit(3) → execute ÇAĞRILIR (guard; gate over-block etmemeli)."""
    mock_exec = await _run_scan_with_no_fill_streak(2)
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_zero_streak_allows_entry():
    """no-fill streak 0 → execute ÇAĞRILIR (guard)."""
    mock_exec = await _run_scan_with_no_fill_streak(0)
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_at_limit_blocks_entry():
    """no-fill streak == limit(3) → yeni giriş ENGELLENİR (execute ÇAĞRILMAZ). İlk RED: gate yok → çağrılır."""
    mock_exec = await _run_scan_with_no_fill_streak(3)
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_above_limit_blocks_entry():
    """no-fill streak > limit(3) → yeni giriş ENGELLENİR (execute ÇAĞRILMAZ)."""
    mock_exec = await _run_scan_with_no_fill_streak(5)
    mock_exec.assert_not_called()
