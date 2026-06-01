"""tests/test_clob_executor.py — clob_executor execute() testleri."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock


def _finding(action="YES"):
    return {
        "question": "Will BTC go up?", "asset": "BTC", "action": action,
        "fair_value": 0.55, "ref_price": 95000.0, "cur_price": 96000.0,
        "best_ask": 0.35, "best_bid": 0.33, "seconds_remaining": 900,
        "edge": 0.20, "slug": "btc-up-5m-test", "neg_risk": False,
        "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222",
    }

def _gate():
    return {"pass": True, "confidence_score": 82.5, "action_taken": "open"}

def _risk():
    return {"pass": True, "position_usd": 25.0, "kelly_f": 0.15,
            "kelly_fraction_applied": 0.25, "reason": ""}


@pytest.mark.asyncio
async def test_execute_returns_position_on_matched_order():
    """Order MATCHED → position dict döner, gerekli alanlar dolu."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {
        "status": "MATCHED", "orderID": "ord-abc",
        "sizeFilled": "71.43", "price": "0.35",
    }
    with patch("execution.clob_executor.get_client", return_value=fake_client):
        from execution.clob_executor import execute
        result = await execute(_finding("YES"), _gate(), _risk(), [])

    assert result is not None
    assert result["asset"] == "BTC"
    assert result["action"] == "YES"
    assert result["yes_token_id"] == "yes-tok-111"
    assert abs(result["shares"] - 71.43) < 0.01
    assert result["order_id"] == "ord-abc"
    assert result["dry_run"] is False


@pytest.mark.asyncio
async def test_execute_returns_none_when_not_matched():
    """Order UNMATCHED → None döner, pozisyon açılmaz."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {
        "status": "UNMATCHED", "orderID": "ord-xyz", "sizeFilled": "0", "price": "0.35",
    }
    with patch("execution.clob_executor.get_client", return_value=fake_client):
        from execution.clob_executor import execute
        result = await execute(_finding("YES"), _gate(), _risk(), [])
    assert result is None


@pytest.mark.asyncio
async def test_execute_uses_yes_token_for_yes_action():
    """YES action → yes_token_id order'a gönderilir."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {
        "status": "MATCHED", "orderID": "x", "sizeFilled": "71.0", "price": "0.35",
    }
    with patch("execution.clob_executor.get_client", return_value=fake_client):
        from execution.clob_executor import execute
        await execute(_finding("YES"), _gate(), _risk(), [])
    call_args = fake_client.create_and_post_order.call_args[0][0]
    assert call_args["token_id"] == "yes-tok-111"
    assert call_args["side"] == "BUY"


@pytest.mark.asyncio
async def test_execute_uses_no_token_for_no_action():
    """NO action → no_token_id order'a gönderilir."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {
        "status": "MATCHED", "orderID": "x", "sizeFilled": "71.0", "price": "0.67",
    }
    with patch("execution.clob_executor.get_client", return_value=fake_client):
        from execution.clob_executor import execute
        await execute(_finding("NO"), _gate(), _risk(), [])
    call_args = fake_client.create_and_post_order.call_args[0][0]
    assert call_args["token_id"] == "no-tok-222"
