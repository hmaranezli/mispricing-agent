import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def _make_pos(slug="btc-up-5m-test", position_id="pos-1"):
    return {
        "position_id": position_id, "slug": slug, "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.51, "position_usd": 25.0,
        "yes_token_id": "yes-tok", "no_token_id": "no-tok",
        "shares": 49.0, "status": "open", "dry_run": False,
        "opened_at": "2026-06-02T00:00:00+00:00",
        "fair_value": 0.55, "ref_price": 71000.0, "edge": 0.09,
        "kelly_f": 0.1, "confidence_score": 80.0,
        "exit_reason": None, "closed_at": None,
    }


@pytest.mark.asyncio
async def test_reconcile_skips_in_dry_run():
    """DRY_RUN=True → hiçbir şey yapmaz, 0 checked."""
    with patch("config.DRY_RUN", True):
        from execution.reconcile import startup_reconcile
        result = await startup_reconcile([_make_pos()], conn=None)
    assert result == {"checked": 0, "closed": 0, "warnings": []}


@pytest.mark.asyncio
async def test_reconcile_closes_resolved_market():
    """Market kapanmış (window=None) + çözüm var → pozisyon kapatılır."""
    from importlib import reload
    import execution.reconcile as rec_mod
    reload(rec_mod)

    pos = _make_pos()
    positions = [pos]

    with patch("config.DRY_RUN", False), \
         patch("execution.reconcile.fetch_by_slug", new_callable=AsyncMock, return_value=None), \
         patch("execution.reconcile.fetch_resolved", new_callable=AsyncMock,
               return_value={"yes_exit": 1.0, "no_exit": 0.0}), \
         patch("execution.reconcile.parse_market_window", return_value=None), \
         patch("execution.reconcile.log_position_close", new_callable=AsyncMock) as mock_close:
        result = await rec_mod.startup_reconcile(positions, conn=AsyncMock())

    assert result["closed"] == 1
    assert result["checked"] == 1
    mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_reconcile_active_market_not_closed():
    """Market hâlâ açık (window mevcut) → pozisyona dokunulmaz."""
    from importlib import reload
    import execution.reconcile as rec_mod
    reload(rec_mod)

    pos = _make_pos()
    positions = [pos]
    fake_window = {"seconds_remaining": 300, "best_ask": 0.51,
                   "best_bid": 0.50, "neg_risk": False}

    with patch("config.DRY_RUN", False), \
         patch("execution.reconcile.fetch_by_slug", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("execution.reconcile.parse_market_window", return_value=fake_window):
        result = await rec_mod.startup_reconcile(positions, conn=None)

    assert result["closed"] == 0
    assert result["checked"] == 1
