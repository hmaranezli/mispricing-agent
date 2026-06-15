"""tests/test_e11f_fill_to_submit_gate_wiring.py — E11f fill-to-submit entry-gate wiring (TDD).

E11d `fill_to_submit_halt` saf predicate + E11e `_session_submit_count` in-memory sayaç hazır;
opened = E10c `_session_trade_count`. E11f: `_scan_and_execute` execute öncesi (E5 risk-mode/NEW_ENTRIES
+ E10b max-trades + E11c no-fill burst gate'lerinden SONRA) `fill_to_submit_halt(_session_trade_count(),
_session_submit_count())` çağrılmalı; "fill_to_submit_stop" → yeni giriş execute'tan ÖNCE engellenmeli
(entry-only; _monitor_positions/panic-flatten/sell_position/exit DOKUNULMAZ).

İzolasyon: _effective_risk_mode→Operational, NEW_ENTRIES→True, _no_fill_streak→0 (diğer gate'ler
bloklamasın). opened/submitted ENJEKTE; gerçek fill_to_submit_halt (default min_submissions=6,
floor_ratio=0.25) kullanılır.

İlk RED: _scan_and_execute fill-to-submit gate'i danışmıyor → düşük oranda bile execute ÇAĞRILIR →
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
def _reset_counters():
    """no-fill / session / submit sayaç sızıntısını engelle (execute() çağrıları gerçek sayaçları oynatır)."""
    names = ("_reset_session_submit_count", "_reset_no_fill_streak", "_reset_session_trade_count")

    def _reset_all():
        for name in names:
            fn = getattr(main_loop, name, None)
            if callable(fn):
                fn()

    _reset_all()
    yield
    _reset_all()


def _finding():
    return {"slug": SLUG, "action": "YES", "fair_value": 0.6,
            "best_ask": 0.45, "edge": 0.15, "seconds_remaining": 600}


async def _run_scan(*, opened, submitted, no_fill_streak=0, session_trade_count_for_gate=None):
    """_scan_and_execute'i NEW_ENTRIES + Operational + enjekte opened/submitted ile koşar; GERÇEK
    fill_to_submit_halt (default 6/0.25) kullanılır. execute spy döner.

    NOT: opened gate'e _session_trade_count() ÜZERİNDEN gider; bu hem E10b max-trades hem fill-to-submit
    okur. E10b'yi tetiklememek için opened < 6 (MAX_TRADES_FIRST_SESSION) seçilir. session_trade_count_for_gate
    None → opened kullanılır."""
    stc = opened if session_trade_count_for_gate is None else session_trade_count_for_gate
    mock_exec = AsyncMock(return_value=None)
    with patch.object(config, "NEW_ENTRIES_ENABLED", True), \
         patch("main_loop._effective_risk_mode", new=MagicMock(return_value="Operational")), \
         patch("main_loop._session_trade_count", new=MagicMock(return_value=stc)), \
         patch("main_loop._session_submit_count", new=MagicMock(return_value=submitted)), \
         patch("main_loop._no_fill_streak", new=MagicMock(return_value=no_fill_streak)), \
         patch("main_loop.scan_edges", new_callable=AsyncMock, return_value=[_finding()]), \
         patch("main_loop._run_council", new_callable=AsyncMock, return_value=({}, {})), \
         patch("main_loop.log_position_open", new_callable=AsyncMock), \
         patch("main_loop.ws_prices", new=MagicMock()), \
         patch("main_loop.execute", mock_exec):
        await main_loop._scan_and_execute([], [], 1000.0)
    return mock_exec


@pytest.mark.asyncio
async def test_below_min_submissions_allows_entry():
    """submitted 5 < min(6) → düşük-örneklem koruması → execute ÇAĞRILIR (guard)."""
    mock_exec = await _run_scan(opened=0, submitted=5)
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_equal_floor_allows_entry():
    """opened 2 / submitted 8 = 0.25 == floor → execute ÇAĞRILIR (equality-safe guard)."""
    mock_exec = await _run_scan(opened=2, submitted=8)
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_healthy_ratio_allows_entry():
    """opened 3 / submitted 8 = 0.375 > floor → execute ÇAĞRILIR (guard)."""
    mock_exec = await _run_scan(opened=3, submitted=8)
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_low_ratio_blocks_entry():
    """opened 1 / submitted 6 ≈ 0.167 < 0.25 floor, submitted>=min → yeni giriş ENGELLENİR
    (execute ÇAĞRILMAZ). İlk RED: gate yok → execute çağrılır."""
    mock_exec = await _run_scan(opened=1, submitted=6)
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_zero_opened_many_submitted_blocks_entry():
    """opened 0 / submitted 6 = 0 < floor → ENGELLENİR (execute ÇAĞRILMAZ)."""
    mock_exec = await _run_scan(opened=0, submitted=6)
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_max_trades_blocks_first_not_fill_to_submit():
    """Gate-order guard: E10b max-trades (session_trade_count=6) ÖNCE bloklar → execute ÇAĞRILMAZ;
    burada karar fill-to-submit DEĞİL (opened=6 zaten max-trades'i tetikler)."""
    mock_exec = await _run_scan(opened=1, submitted=6, session_trade_count_for_gate=6)
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_no_fill_burst_blocks_first_not_fill_to_submit():
    """Gate-order guard: E11c no-fill burst (no_fill_streak=3) ÖNCE bloklar → execute ÇAĞRILMAZ;
    burada karar fill-to-submit DEĞİL (oran sağlıklı: 3/8)."""
    mock_exec = await _run_scan(opened=3, submitted=8, no_fill_streak=3)
    mock_exec.assert_not_called()
