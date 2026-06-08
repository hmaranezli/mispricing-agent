"""tests/test_new_entries_flag.py — NEW_ENTRIES_ENABLED kill-switch TDD.

Amaç: yeni live entry'yi durdur AMA:
- council/telemetri çalışmaya devam etsin (shadow_candidates yazılsın)
- monitor/exit/stop logic'e dokunma
- 4h shadow scan'e dokunma
"""
import asyncio
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


@pytest.mark.asyncio
async def test_new_entries_disabled_skips_execute():
    """NEW_ENTRIES_ENABLED=False iken council geçse bile execute() çağrılmamalı."""
    import main_loop

    finding = {
        "slug": "btc-updown-15m-123", "asset": "BTC", "action": "YES",
        "fair_value": 0.60, "best_ask": 0.50, "edge": 0.10,
        "seconds_remaining": 400,
        "yes_token_id": "tok1", "no_token_id": "tok2",
    }
    gate_result = {"pass": True, "confidence_score": 80}
    risk_result = {"pass": True, "position_usd": 5.0, "kelly_f": 0.05}

    execute_calls = []
    council_calls = []

    async def mock_scan():
        return [finding]

    async def mock_council(*a, **k):
        council_calls.append(1)
        return (gate_result, risk_result)

    async def mock_execute(*a, **k):
        execute_calls.append(1)
        return None

    with patch.object(config, "NEW_ENTRIES_ENABLED", False), \
         patch("main_loop.scan_edges", side_effect=mock_scan), \
         patch("main_loop._run_council", side_effect=mock_council), \
         patch("main_loop.execute", side_effect=mock_execute):
        await main_loop._scan_and_execute([], [], 1000.0, conn=None)

    assert council_calls, "council çalışmalı (telemetri korunur)"
    assert not execute_calls, "NEW_ENTRIES_ENABLED=False iken execute() çağrılMAMALI"


@pytest.mark.asyncio
async def test_new_entries_enabled_calls_execute():
    """NEW_ENTRIES_ENABLED=True iken normal akış: execute() çağrılmalı."""
    import main_loop

    finding = {
        "slug": "btc-updown-15m-456", "asset": "BTC", "action": "YES",
        "fair_value": 0.60, "best_ask": 0.50, "edge": 0.10,
        "seconds_remaining": 400,
        "yes_token_id": "tok1", "no_token_id": "tok2",
    }
    gate_result = {"pass": True, "confidence_score": 80}
    risk_result = {"pass": True, "position_usd": 5.0, "kelly_f": 0.05}

    execute_calls = []

    async def mock_scan():
        return [finding]

    async def mock_council(*a, **k):
        return (gate_result, risk_result)

    async def mock_execute(*a, **k):
        execute_calls.append(1)
        return None  # FAK kill — pozisyon açılmaz, ama execute çağrıldı

    with patch.object(config, "NEW_ENTRIES_ENABLED", True), \
         patch("main_loop.scan_edges", side_effect=mock_scan), \
         patch("main_loop._run_council", side_effect=mock_council), \
         patch("main_loop.execute", side_effect=mock_execute):
        await main_loop._scan_and_execute([], [], 1000.0, conn=None)

    assert execute_calls, "NEW_ENTRIES_ENABLED=True iken execute() çağrılMALI"


def test_config_has_new_entries_flag():
    """config.NEW_ENTRIES_ENABLED tanımlı olmalı."""
    assert hasattr(config, "NEW_ENTRIES_ENABLED")
    assert isinstance(config.NEW_ENTRIES_ENABLED, bool)
