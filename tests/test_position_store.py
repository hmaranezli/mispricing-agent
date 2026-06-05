"""tests/test_position_store.py — sell_position() testleri.

API docs (https://docs.polymarket.com/api-reference/introduction):
  Matched SELL response:
    - status: "matched"
    - orderID: string
    - takingAmount: string  ← USDC received (taker takes USDC from maker's BUY order)
    - makingAmount: string  ← shares given (maker gives shares)
    - "price" field: DOKÜMANTE DEĞİL, cevap body'sinde YOK
  fill_price = takingAmount / makingAmount (USDC / share)

  CRITICAL: FAK SELL fail → None döner (fallback DEĞİL).
  main_loop None'ı görünce pozisyonu açık bırakır — sahte kapatma olmaz.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


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


def _clob_patch(bid=0.90):
    """get_clob_price(side='SELL') mock — CLOB gerçek zamanlı bid."""
    return patch("execution.position_store.get_clob_price", new_callable=AsyncMock, return_value=bid)


@pytest.mark.asyncio
async def test_sell_position_yes_uses_yes_token():
    """YES pozisyon → yes_token_id kullanılır, side=SELL."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp()
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.90):
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
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.10):
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
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.90):
        from execution.position_store import sell_position
        fill = await sell_position(_open_pos("YES", shares=1.3, bid=0.90))
    expected = round(1.183 / 1.3, 6)  # ≈ 0.91
    assert abs(fill - expected) < 0.001, f"fill_price={fill:.4f}, beklenen={expected:.4f}"


@pytest.mark.asyncio
async def test_sell_position_uses_fak_not_fok():
    """SELL order FAK ile gönderilmeli — FOK değil.

    Docs: FAK = Fill And Kill, partial fills OK, daha yüksek fill rate.
    İnce satış kitabında FOK kill olursa tüm order reddedilir.
    """
    from py_clob_client_v2.clob_types import OrderType
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp()
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.90):
        from execution.position_store import sell_position
        await sell_position(_open_pos("YES"))
    _, kwargs = fake_client.create_and_post_order.call_args
    order_type = kwargs.get("order_type") or fake_client.create_and_post_order.call_args[1].get("order_type")
    assert order_type == OrderType.FAK, f"FAK beklendi, {order_type} geldi"


@pytest.mark.asyncio
async def test_sell_position_uses_clob_bid_for_floor_price():
    """SELL order fiyatı = CLOB bid - FLOOR_BUFFER (stale best_bid değil)."""
    from execution.position_store import _FLOOR_BUFFER
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp()
    clob_bid = 0.75
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(clob_bid):
        from execution.position_store import sell_position
        await sell_position(_open_pos("YES", bid=0.40))  # stale bid farklı
    call = fake_client.create_and_post_order.call_args[0][0]
    expected_floor = round(max(0.01, clob_bid - _FLOOR_BUFFER), 2)
    assert abs(call.price - expected_floor) < 0.001, \
        f"floor_price={call.price:.4f}, beklenen={expected_floor:.4f} (CLOB bid={clob_bid})"


@pytest.mark.asyncio
async def test_sell_position_returns_none_on_exception():
    """API exception → None döner (fallback DEĞİL) — main_loop pozisyonu açık bırakır."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.side_effect = Exception("API down")
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.87):
        from execution.position_store import sell_position
        fill = await sell_position(_open_pos("YES", bid=0.87))
    assert fill is None, f"Exception durumunda None beklendi, {fill} geldi"


@pytest.mark.asyncio
async def test_sell_position_returns_none_on_unmatched():
    """UNMATCHED (FAK kill) → None döner — sahte kapatma olmaz."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {"status": "unmatched", "orderID": "x"}
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.87):
        from execution.position_store import sell_position
        fill = await sell_position(_open_pos("YES", bid=0.87))
    assert fill is None, f"FAK kill durumunda None beklendi, {fill} geldi"


@pytest.mark.asyncio
async def test_sell_position_returns_floor_when_amounts_missing():
    """status=matched ama takingAmount/makingAmount yoksa floor_price döner (None değil)."""
    from execution.position_store import _FLOOR_BUFFER
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {"status": "matched", "orderID": "y"}
    clob_bid = 0.88
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(clob_bid):
        from execution.position_store import sell_position
        fill = await sell_position(_open_pos("YES", bid=0.88))
    expected_floor = round(max(0.01, clob_bid - _FLOOR_BUFFER), 2)
    assert fill is not None, "matched + amounts eksik → floor_price döner, None değil"
    assert abs(fill - expected_floor) < 0.001, \
        f"fill={fill:.4f}, beklenen floor={expected_floor:.4f}"


@pytest.mark.asyncio
async def test_sell_position_returns_none_when_clob_bid_zero_and_no_stale():
    """CLOB bid=None ve current_bid=0 → likidite yok → None döner."""
    with patch("execution.position_store.get_clob_price", new_callable=AsyncMock, return_value=None):
        from execution.position_store import sell_position
        pos = _open_pos("YES", bid=0.0)
        fill = await sell_position(pos)
    assert fill is None


@pytest.mark.asyncio
async def test_sell_position_falls_back_to_stale_bid_when_clob_unavailable():
    """CLOB bid=None ama current_bid>0 → stale bid ile floor hesaplanır, order gönderilir."""
    from execution.position_store import _FLOOR_BUFFER
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp()
    stale_bid = 0.85
    with patch("execution.position_store.get_client", return_value=fake_client), \
         patch("execution.position_store.get_clob_price", new_callable=AsyncMock, return_value=None):
        from execution.position_store import sell_position
        await sell_position(_open_pos("YES", bid=stale_bid))
    call = fake_client.create_and_post_order.call_args[0][0]
    expected_floor = round(max(0.01, stale_bid - _FLOOR_BUFFER), 2)
    assert abs(call.price - expected_floor) < 0.001, \
        f"CLOB None → stale bid={stale_bid} kullanılmalı, floor={expected_floor:.4f}"
