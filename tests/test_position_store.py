"""tests/test_position_store.py — sell_position() testleri."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock


def _open_pos(action="YES", shares=71.43, bid=0.90):
    return {
        "position_id": "pos-sell-001", "asset": "BTC", "action": action,
        "slug": "btc-up-5m-test", "pm_entry_price": 0.35,
        "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222",
        "shares": shares, "current_bid": bid,
    }


@pytest.mark.asyncio
async def test_sell_position_yes_uses_yes_token():
    """YES pozisyon → yes_token_id kullanılır, side=SELL."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {
        "status": "MATCHED", "price": "0.90", "sizeFilled": "71.43",
    }
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        await sell_position(_open_pos("YES"))
    call = fake_client.create_and_post_order.call_args[0][0]
    assert call["token_id"] == "yes-tok-111"
    assert call["side"] == "SELL"


@pytest.mark.asyncio
async def test_sell_position_no_uses_no_token():
    """NO pozisyon → no_token_id kullanılır."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {
        "status": "MATCHED", "price": "0.10", "sizeFilled": "71.43",
    }
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        await sell_position(_open_pos("NO"))
    call = fake_client.create_and_post_order.call_args[0][0]
    assert call["token_id"] == "no-tok-222"


@pytest.mark.asyncio
async def test_sell_position_returns_fill_price():
    """Başarılı SELL → float fill fiyatı döner."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {
        "status": "MATCHED", "price": "0.92", "sizeFilled": "71.43",
    }
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        fill = await sell_position(_open_pos("YES"))
    assert abs(fill - 0.92) < 0.001


@pytest.mark.asyncio
async def test_sell_position_returns_fallback_on_failure():
    """API exception → current_bid fallback döner, exception fırlatılmaz."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.side_effect = Exception("API down")
    pos = _open_pos("YES", bid=0.87)
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        fill = await sell_position(pos)
    assert abs(fill - 0.87) < 0.001


@pytest.mark.asyncio
async def test_sell_position_returns_fallback_on_unmatched():
    """UNMATCHED status → current_bid fallback döner, exception yok."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {
        "status": "UNMATCHED", "price": "0.90", "sizeFilled": "0",
    }
    pos = _open_pos("YES", bid=0.87)
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        fill = await sell_position(pos)
    assert abs(fill - 0.87) < 0.001
