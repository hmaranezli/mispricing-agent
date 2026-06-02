"""tests/test_balance.py — get_effective_bankroll testleri."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
import execution.balance as balance_mod


@pytest.mark.asyncio
async def test_dry_run_returns_config():
    """DRY_RUN=True → config bankroll döner, API çağrısı yok."""
    with patch.object(balance_mod.config, "DRY_RUN", True):
        result = await balance_mod.get_effective_bankroll(bankroll_config=500.0)
    assert result == 500.0


@pytest.mark.asyncio
async def test_live_uses_polymarket_balance():
    """DRY_RUN=False → gerçek bakiye mikro-USDC'den dönüştürülür."""
    fake_client = MagicMock()
    fake_client.get_balance_allowance.return_value = {"balance": "250000000"}  # $250.00

    with patch.object(balance_mod.config, "DRY_RUN", False), \
         patch.object(balance_mod, "get_client", return_value=fake_client):
        result = await balance_mod.get_effective_bankroll(bankroll_config=1000.0)

    assert result == 250.0


@pytest.mark.asyncio
async def test_live_caps_at_config():
    """Bakiye > config → config döner (güvenlik üst sınırı)."""
    fake_client = MagicMock()
    fake_client.get_balance_allowance.return_value = {"balance": "2000000000"}  # $2000

    with patch.object(balance_mod.config, "DRY_RUN", False), \
         patch.object(balance_mod, "get_client", return_value=fake_client):
        result = await balance_mod.get_effective_bankroll(bankroll_config=500.0)

    assert result == 500.0


@pytest.mark.asyncio
async def test_live_api_error_falls_back_to_config():
    """API hatası → config bankroll fallback, sistem durmuyor."""
    fake_client = MagicMock()
    fake_client.get_balance_allowance.side_effect = Exception("timeout")

    with patch.object(balance_mod.config, "DRY_RUN", False), \
         patch.object(balance_mod, "get_client", return_value=fake_client):
        result = await balance_mod.get_effective_bankroll(bankroll_config=300.0)

    assert result == 300.0
