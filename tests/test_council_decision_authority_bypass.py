"""tests/test_council_decision_authority_bypass.py — proves the Council Decision-Authority Bypass
(TDD, offline).

The council/multi-agent layer is deterministic Python that was trade-path connected. This suite
proves that, by default, a council PASS is disconnected from execution authority: it cannot reach
execute(), cannot reach _dry_execute/_clob_execute, and cannot create an order intent. Council still
runs as diagnostic-only. A config flag (default disabled) is the sole control; enabling it cannot
bypass DRY_RUN or authorize live execution.

No network, no public-data fetch, no real orders/DB/Telegram: scan_edges, _run_council, and the
executors are mocked; entry-gate helpers are forced open so the ONLY thing that can stop execution
is the bypass.
"""
import os
import sys

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import main_loop

SLUG = "btc-updown-15m-bypass"


@pytest.fixture(autouse=True)
def _reset_counters():
    for name in ("_reset_no_fill_streak", "_reset_session_trade_count", "_reset_session_submit_count"):
        fn = getattr(main_loop, name, None)
        if callable(fn):
            fn()
    yield
    for name in ("_reset_no_fill_streak", "_reset_session_trade_count", "_reset_session_submit_count"):
        fn = getattr(main_loop, name, None)
        if callable(fn):
            fn()


def _finding():
    return {"slug": SLUG, "action": "YES", "fair_value": 0.6,
            "best_ask": 0.45, "edge": 0.15, "seconds_remaining": 600}


def _pass_gate():
    return {"pass": True, "confidence_score": 0.99}


def _pass_risk():
    return {"pass": True, "kelly_f": 0.25, "position_usd": 50.0}


def _gates_open():
    """Context patches that force every entry-gate OPEN, so the bypass is the only possible stop."""
    return [
        patch.object(config, "NEW_ENTRIES_ENABLED", True),
        patch("main_loop._effective_risk_mode", new=MagicMock(return_value="Operational")),
        patch("main_loop._session_trade_count", new=MagicMock(return_value=0)),
        patch("main_loop._session_submit_count", new=MagicMock(return_value=0)),
        patch("main_loop._no_fill_streak", new=MagicMock(return_value=0)),
        patch("main_loop.scan_edges", new_callable=AsyncMock),
        patch("main_loop._run_council", new_callable=AsyncMock),
        patch("main_loop.log_position_open", new_callable=AsyncMock),
        patch("main_loop.ws_prices", new=MagicMock()),
    ]


async def _drive(*, council_ret, extra_patches):
    ctx = _gates_open() + list(extra_patches)
    started = []
    try:
        for c in ctx:
            c.start(); started.append(c)
        main_loop.scan_edges.return_value = [_finding()]
        main_loop._run_council.return_value = council_ret
        await main_loop._scan_and_execute([], [], 1000.0)
    finally:
        for c in reversed(started):
            c.stop()


def test_flag_defaults_disabled():
    assert hasattr(config, "COUNCIL_DECISION_AUTHORITY_ENABLED")
    assert config.COUNCIL_DECISION_AUTHORITY_ENABLED is False


@pytest.mark.asyncio
async def test_council_pass_does_not_call_execute_by_default():
    mock_exec = AsyncMock(return_value=None)
    await _drive(council_ret=(_pass_gate(), _pass_risk()),
                 extra_patches=[patch("main_loop.execute", mock_exec)])
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_council_pass_does_not_create_order_intent_by_default():
    import execution.order_intent as oi
    mock_dry = AsyncMock(return_value=None)
    mock_clob = AsyncMock(return_value=None)
    mock_intent = AsyncMock()
    await _drive(council_ret=(_pass_gate(), _pass_risk()), extra_patches=[
        patch("main_loop._dry_execute", mock_dry),
        patch("main_loop._clob_execute", mock_clob),
        patch.object(oi, "create_intent", mock_intent),
    ])
    mock_dry.assert_not_called()
    mock_clob.assert_not_called()
    mock_intent.assert_not_called()


@pytest.mark.asyncio
async def test_gate_confidence_cannot_authorize_execution():
    mock_exec = AsyncMock(return_value=None)
    await _drive(council_ret=({"pass": True, "confidence_score": 0.999}, _pass_risk()),
                 extra_patches=[patch("main_loop.execute", mock_exec)])
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_risk_kelly_cannot_override_execution():
    mock_exec = AsyncMock(return_value=None)
    await _drive(council_ret=(_pass_gate(), {"pass": True, "kelly_f": 0.9, "position_usd": 999.0}),
                 extra_patches=[patch("main_loop.execute", mock_exec)])
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_no_route_to_dry_or_clob_execute_by_default():
    mock_dry = AsyncMock(return_value=None)
    mock_clob = AsyncMock(return_value=None)
    await _drive(council_ret=(_pass_gate(), _pass_risk()), extra_patches=[
        patch("main_loop._dry_execute", mock_dry),
        patch("main_loop._clob_execute", mock_clob),
    ])
    mock_dry.assert_not_called()
    mock_clob.assert_not_called()


@pytest.mark.asyncio
async def test_council_remains_callable_but_diagnostic_only():
    mock_exec = AsyncMock(return_value=None)
    open_pos = []
    ctx = _gates_open() + [patch("main_loop.execute", mock_exec)]
    started = []
    try:
        for c in ctx:
            c.start(); started.append(c)
        main_loop.scan_edges.return_value = [_finding()]
        main_loop._run_council.return_value = (_pass_gate(), _pass_risk())
        await main_loop._scan_and_execute(open_pos, [], 1000.0)
        council_calls = main_loop._run_council.call_count  # capture while patch active
    finally:
        for c in reversed(started):
            c.stop()
    assert council_calls == 1                     # council still runs (diagnostic)
    mock_exec.assert_not_called()                 # but cannot execute
    assert open_pos == []                         # no position opened


@pytest.mark.asyncio
async def test_flag_enabled_routes_to_execute():
    """Enabling the flag is the sole control that restores routing (opt-in)."""
    mock_exec = AsyncMock(return_value=None)
    with patch.object(config, "COUNCIL_DECISION_AUTHORITY_ENABLED", True):
        await _drive(council_ret=(_pass_gate(), _pass_risk()),
                     extra_patches=[patch("main_loop.execute", mock_exec)])
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_flag_enabled_still_respects_dry_run():
    """Even with the flag enabled, execution routing obeys DRY_RUN — never live (_clob)."""
    mock_dry = AsyncMock(return_value=None)
    mock_clob = AsyncMock(return_value=None)
    with patch.object(config, "COUNCIL_DECISION_AUTHORITY_ENABLED", True), \
         patch.object(config, "DRY_RUN", True):
        await _drive(council_ret=(_pass_gate(), _pass_risk()), extra_patches=[
            patch("main_loop._dry_execute", mock_dry),
            patch("main_loop._clob_execute", mock_clob),
        ])
    mock_dry.assert_called_once()
    mock_clob.assert_not_called()
