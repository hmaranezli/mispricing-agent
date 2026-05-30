"""tests/test_main_loop.py — main_loop birim testleri. Sıfır API çağrısı."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from main_loop import _run_council, _scan_and_execute, _monitor_positions


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
