"""tests/test_position_store.py — sell_position() testleri.

API docs (https://docs.polymarket.com/api-reference/introduction):
  Matched SELL response:
    - status: "matched"
    - orderID: string
    - takingAmount: string  ← USDC received (taker takes USDC from maker's BUY order)
    - makingAmount: string  ← shares given (maker gives shares)
    - "price" field: DOKÜMANTE DEĞİL, cevap body'sinde YOK
  fill_price = takingAmount / makingAmount (USDC / share)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock


def _open_pos(action="YES", shares=1.3, bid=0.90):
    return {
        "position_id": "pos-sell-001", "asset": "BTC", "action": action,
        "slug": "btc-up-5m-test", "pm_entry_price": 0.35,
        "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222",
        "shares": shares, "current_bid": bid,
    }


def _matched_resp(taking="1.17", making="1.3"):
    """Gerçek API response — takingAmount=USDC, makingAmount=shares (SELL için)."""
    return {
        "status": "matched",
        "orderID": "ord-sell-abc",
        "takingAmount": taking,   # USDC received
        "makingAmount": making,   # shares given
    }


@pytest.mark.asyncio
async def test_sell_position_yes_uses_yes_token():
    """YES pozisyon → yes_token_id kullanılır, side=SELL."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp()
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        await sell_position(_open_pos("YES"))
    call = fake_client.create_and_post_order.call_args[0][0]
    assert call.token_id == "yes-tok-111"
    assert call.side == "SELL"


@pytest.mark.asyncio
async def test_sell_position_no_uses_no_token():
    """NO pozisyon → no_token_id kullanılır."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp(taking="0.13", making="1.3")
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        await sell_position(_open_pos("NO"))
    call = fake_client.create_and_post_order.call_args[0][0]
    assert call.token_id == "no-tok-222"


@pytest.mark.asyncio
async def test_sell_position_returns_fill_price_from_taking_making():
    """Başarılı SELL → takingAmount/makingAmount'tan fill fiyatı hesaplanır.

    takingAmount=USDC received, makingAmount=shares given
    fill_price = takingAmount / makingAmount
    """
    fake_client = MagicMock()
    # 1.3 share @ 0.91 → 1.183 USDC received
    fake_client.create_and_post_order.return_value = _matched_resp(taking="1.183", making="1.3")
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        fill = await sell_position(_open_pos("YES", shares=1.3, bid=0.90))
    expected = round(1.183 / 1.3, 6)  # ≈ 0.91
    assert abs(fill - expected) < 0.001, f"fill_price={fill:.4f}, beklenen={expected:.4f}"


@pytest.mark.asyncio
async def test_sell_position_uses_fak_not_fok():
    """SELL order FAK ile gönderilmeli — FOK değil.

    Docs: FAK = Fill And Kill, partial fills OK, daha yüksek fill rate.
    İnce satış kitabında FOK kill olursa fallback fiyatı döner ama token satılmaz.
    """
    from py_clob_client_v2.clob_types import OrderType
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp()
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        await sell_position(_open_pos("YES"))
    _, kwargs = fake_client.create_and_post_order.call_args
    order_type = kwargs.get("order_type") or fake_client.create_and_post_order.call_args[1].get("order_type")
    assert order_type == OrderType.FAK, f"FAK beklendi, {order_type} geldi"


@pytest.mark.asyncio
async def test_sell_position_returns_fallback_on_exception():
    """API exception → current_bid fallback döner, exception fırlatılmaz."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.side_effect = Exception("API down")
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        fill = await sell_position(_open_pos("YES", bid=0.87))
    assert abs(fill - 0.87) < 0.001


@pytest.mark.asyncio
async def test_sell_position_returns_fallback_on_unmatched():
    """UNMATCHED → current_bid fallback döner."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {"status": "unmatched", "orderID": "x"}
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        fill = await sell_position(_open_pos("YES", bid=0.87))
    assert abs(fill - 0.87) < 0.001


@pytest.mark.asyncio
async def test_sell_position_returns_fallback_when_amounts_missing():
    """takingAmount/makingAmount yoksa fallback kullanılır."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {"status": "matched", "orderID": "y"}
    with patch("execution.position_store.get_client", return_value=fake_client):
        from execution.position_store import sell_position
        fill = await sell_position(_open_pos("YES", bid=0.88))
    assert abs(fill - 0.88) < 0.001
