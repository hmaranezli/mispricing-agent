"""tests/test_main_loop.py — main_loop birim testleri. Sıfır API çağrısı."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest_asyncio
import aiosqlite
from db.schema import init_schema
from db.logger import log_position_open
from main_loop import _run_council, _scan_and_execute, _monitor_positions, _load_open_positions, fetch_resolved


# ── Fixture'lar ──────────────────────────────────────────────────────────────

def _finding():
    return {
        "question": "Will BTC go up?", "asset": "BTC", "action": "YES",
        "fair_value": 0.55, "ref_price": 95000.0, "cur_price": 95500.0,
        "best_ask": 0.35, "best_bid": 0.33, "seconds_remaining": 900,
        "edge": 0.20, "slug": "btc-up-15min-test", "neg_risk": False,
    }

def _pass_verify():
    return {"pass": True, "fresh_best_ask": 0.35, "fresh_best_bid": 0.33,
            "fresh_seconds": 900, "halt": False, "reason": ""}

def _pass_redteam():
    return {"pass": True, "vetoes": [], "warnings": [], "fee_adj_edge": 0.18,
            "liquidity_usd": 2000.0, "spread": 0.02}

def _pass_risk():
    return {"pass": True, "position_usd": 25.0, "kelly_f": 0.15,
            "kelly_fraction_applied": 0.25, "reason": ""}

def _pass_gate():
    return {"pass": True, "confidence_score": 82.5,
            "action_taken": "dry_run_logged", "reason": ""}


# ── Task 1: _run_council() ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_council_returns_none_when_verify_fails():
    """verify() fail → _run_council None döner."""
    with patch("main_loop.verify", new_callable=AsyncMock) as mock_v:
        mock_v.return_value = {"pass": False, "reason": "timeout"}
        result = await _run_council(_finding(), bankroll_usd=1000.0,
                                    n_open=0, daily_loss_usd=0.0)
    assert result is None


@pytest.mark.asyncio
async def test_run_council_returns_gate_and_risk_on_success():
    """Tüm katmanlar geçince (gate_result, risk_result) tuple döner."""
    with patch("main_loop.verify",       new_callable=AsyncMock) as mv, \
         patch("main_loop.redteam_eval", new_callable=AsyncMock) as mr, \
         patch("main_loop.risk_eval",    new=MagicMock(return_value=_pass_risk())), \
         patch("main_loop.gate",         new_callable=AsyncMock) as mg:
        mv.return_value = _pass_verify()
        mr.return_value = _pass_redteam()
        mg.return_value = _pass_gate()
        result = await _run_council(_finding(), bankroll_usd=1000.0,
                                    n_open=0, daily_loss_usd=0.0)
    assert result is not None
    gate_result, risk_result = result
    assert gate_result["pass"] is True
    assert risk_result["position_usd"] == 25.0


# ── Task 2: _scan_and_execute() ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_skips_when_max_positions_reached():
    """MAX_OPEN_POSITIONS doluysa scan_edges hiç çağrılmaz."""
    import config
    open_pos = [{"position_id": str(i)} for i in range(config.MAX_OPEN_POSITIONS)]
    with patch("main_loop.scan_edges", new_callable=AsyncMock) as mock_scan:
        await _scan_and_execute(open_pos, [], bankroll_usd=1000.0)
    mock_scan.assert_not_called()


@pytest.mark.asyncio
async def test_scan_opens_position_on_full_council_pass():
    """Konsey geçince execute() çağrılır, pozisyon open_positions'a eklenir."""
    open_pos = []
    fake_pos = {"position_id": "abc-123", "status": "open", "asset": "BTC",
                "action": "YES", "slug": "btc-up-test"}
    with patch("main_loop.scan_edges",   new_callable=AsyncMock) as mock_scan, \
         patch("main_loop._run_council", new_callable=AsyncMock) as mock_council, \
         patch("main_loop.execute",      new_callable=AsyncMock) as mock_exec:
        mock_scan.return_value    = [_finding()]
        mock_council.return_value = (_pass_gate(), _pass_risk())
        mock_exec.return_value    = fake_pos
        await _scan_and_execute(open_pos, [], bankroll_usd=1000.0)
    assert len(open_pos) == 1
    assert open_pos[0]["position_id"] == "abc-123"


@pytest.mark.asyncio
async def test_scan_skips_already_open_slug():
    """Aynı slug için açık pozisyon varsa _run_council çağrılmaz."""
    existing = {"position_id": "exist-001", "slug": "btc-up-15min-test", "status": "open"}
    open_pos = [existing]
    with patch("main_loop.scan_edges",   new_callable=AsyncMock) as mock_scan, \
         patch("main_loop._run_council", new_callable=AsyncMock) as mock_council:
        mock_scan.return_value = [_finding()]   # _finding() slug = "btc-up-test"
        await _scan_and_execute(open_pos, [], bankroll_usd=1000.0)
    mock_council.assert_not_called()
    assert len(open_pos) == 1


# ── Task 3: _monitor_positions() ─────────────────────────────────────────────

def _open_position():
    """Açık pozisyon fixture'ı."""
    opened_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    return {
        "position_id": "pos-xyz", "asset": "BTC", "action": "YES",
        "slug": "btc-up-test", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "position_usd": 25.0, "kelly_f": 0.15,
        "confidence_score": 82.5, "seconds_remaining": 900,
        "opened_at": opened_at, "status": "open",
        "requires_human_approval": False, "dry_run": True,
        "exit_reason": None, "closed_at": None,
    }


@pytest.mark.asyncio
async def test_monitor_closes_position_on_exit_signal():
    """check_exit sinyal verince pozisyon open'dan closed'a geçer."""
    pos = _open_position()
    open_pos = [pos]
    closed = []
    fake_window = {"best_ask": 0.52, "best_bid": 0.50,
                   "seconds_remaining": 900, "neg_risk": False}
    with patch("main_loop.current_price",     new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",     new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=fake_window), \
         patch("main_loop.check_exit",        return_value="max_hold_time"):
        mock_hl.return_value = 95000.0
        mock_pm.return_value = {}
        await _monitor_positions(open_pos, closed)
    assert len(open_pos) == 0
    assert len(closed) == 1
    assert closed[0]["exit_reason"] == "max_hold_time"
    assert closed[0]["status"] == "closed"


@pytest.mark.asyncio
async def test_monitor_closes_on_missing_market():
    """parse_market_window None + fetch_resolved None → market_expired ile kapatılır."""
    open_pos = [_open_position()]
    closed = []
    with patch("main_loop.current_price",       new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",       new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=None), \
         patch("main_loop.fetch_resolved",      new_callable=AsyncMock) as mock_res:
        mock_hl.return_value  = 95000.0
        mock_pm.return_value  = {}
        mock_res.return_value = None
        await _monitor_positions(open_pos, closed)
    assert len(open_pos) == 0
    assert len(closed) == 1
    assert closed[0]["exit_reason"] == "market_expired"


@pytest.mark.asyncio
async def test_monitor_closes_with_resolution_price_on_yes():
    """window=None iken fetch_resolved sonuç verirse pm_exit_price dolu kapanır (YES)."""
    pos = {**_open_position(), "action": "YES"}
    open_pos = [pos]
    closed = []
    with patch("main_loop.current_price",       new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",       new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=None), \
         patch("main_loop.fetch_resolved",      new_callable=AsyncMock) as mock_res:
        mock_hl.return_value  = 95000.0
        mock_pm.return_value  = {}
        mock_res.return_value = {"yes_exit": 1.0, "no_exit": 0.0}
        await _monitor_positions(open_pos, closed)
    assert len(open_pos) == 0
    assert len(closed) == 1
    assert closed[0]["pm_exit_price"] == 1.0
    assert closed[0]["exit_reason"] == "market_resolved"


# ── _load_open_positions() ────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def mem_db():
    async with aiosqlite.connect(":memory:") as db:
        await init_schema(db)
        yield db


@pytest.mark.asyncio
async def test_load_open_positions_empty_db(mem_db):
    """DB'de açık pozisyon yoksa boş liste döner."""
    result = await _load_open_positions(mem_db)
    assert result == []


@pytest.mark.asyncio
async def test_load_open_positions_returns_open_ones(mem_db):
    """DB'deki status=open pozisyonlar yüklenir, closed olanlar atlanır."""
    open_pos = {
        "position_id": "r-001", "slug": "btc-up-5min", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.18,
        "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-05-30T10:00:00+00:00",
    }
    closed_pos = {**open_pos, "position_id": "r-002", "slug": "eth-down-15min"}
    await log_position_open(mem_db, open_pos)
    await log_position_open(mem_db, closed_pos)
    await mem_db.execute("UPDATE positions SET status='closed' WHERE position_id='r-002'")
    await mem_db.commit()

    result = await _load_open_positions(mem_db)
    assert len(result) == 1
    assert result[0]["position_id"] == "r-001"
    assert result[0]["asset"] == "BTC"
    assert result[0]["ref_price"] == 95000.0
    assert result[0]["edge"] == 0.18
    assert result[0]["opened_at"] == "2026-05-30T10:00:00+00:00"
