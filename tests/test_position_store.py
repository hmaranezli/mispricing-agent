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

def _qask(p):
    """Test helper — entry quote (ask). p=ask, bid=p-0.02. None→None."""
    if p is None: return None
    from data.orderbook_snapshot import OrderbookSnapshot
    import time as _t
    return OrderbookSnapshot(bid=round(p-0.02,4), ask=p, bid_size=1e4, ask_size=1e4, source="rest_book", ts=_t.time())

def _qbid(p):
    """Test helper — exit quote (bid). p=bid, ask=p+0.02. None→None."""
    if p is None: return None
    from data.orderbook_snapshot import OrderbookSnapshot
    import time as _t
    return OrderbookSnapshot(bid=p, ask=round(p+0.02,4), bid_size=1e4, ask_size=1e4, source="rest_book", ts=_t.time())


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
    return patch("execution.position_store.get_quote", new_callable=AsyncMock, return_value=_qbid(bid))


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
        fill_price, making = await sell_position(_open_pos("YES", shares=1.3, bid=0.90))
    expected = round(1.183 / 1.3, 6)  # ≈ 0.91
    assert abs(fill_price - expected) < 0.001, f"fill_price={fill_price:.4f}, beklenen={expected:.4f}"
    assert abs(making - 1.3) < 0.001, f"making={making}, beklenen=1.3"


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
        fill_price, making = await sell_position(_open_pos("YES", bid=0.88))
    expected_floor = round(max(0.01, clob_bid - _FLOOR_BUFFER), 2)
    assert fill_price is not None, "matched + amounts eksik → floor_price döner, None değil"
    assert abs(fill_price - expected_floor) < 0.001, \
        f"fill={fill_price:.4f}, beklenen floor={expected_floor:.4f}"


@pytest.mark.asyncio
async def test_sell_position_returns_none_when_clob_bid_zero_and_no_stale():
    """CLOB bid=None ve current_bid=0 → likidite yok → None döner."""
    with patch("execution.position_store.get_quote", new_callable=AsyncMock, return_value=None):
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
         patch("execution.position_store.get_quote", new_callable=AsyncMock, return_value=None):
        from execution.position_store import sell_position
        await sell_position(_open_pos("YES", bid=stale_bid))
    call = fake_client.create_and_post_order.call_args[0][0]
    expected_floor = round(max(0.01, stale_bid - _FLOOR_BUFFER), 2)
    assert abs(call.price - expected_floor) < 0.001, \
        f"CLOB None → stale bid={stale_bid} kullanılmalı, floor={expected_floor:.4f}"


# ── Task 4: Book snapshot + timing + fill metrics ─────────────────────────────

@pytest.mark.asyncio
async def test_sell_increments_attempt_count():
    """Her sell_position çağrısı sell_attempt_count'u artırır."""
    pos = _open_pos()
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp()
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.90), \
         patch("execution.position_store.ws_prices") as mock_ws:
        mock_ws.get_ask.return_value = None
        from execution.position_store import sell_position
        await sell_position(pos)
    assert pos.get("sell_attempt_count") == 1


@pytest.mark.asyncio
async def test_sell_increments_unmatched_count_on_fak_kill():
    """FAK kill (status != matched) sell_unmatched_count'u artırır."""
    pos = _open_pos()
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {"status": "unmatched"}
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.90), \
         patch("execution.position_store.ws_prices") as mock_ws:
        mock_ws.get_ask.return_value = None
        from execution.position_store import sell_position
        result = await sell_position(pos)
    assert result is None
    assert pos.get("sell_unmatched_count") == 1
    assert pos.get("sell_attempt_count") == 1


@pytest.mark.asyncio
async def test_sell_captures_exit_bid_at_trigger_first_attempt_only():
    """exit_bid_at_trigger yalnızca ilk denemede yazılır (setdefault)."""
    pos = _open_pos()
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp()
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.90), \
         patch("execution.position_store.ws_prices") as mock_ws:
        mock_ws.get_ask.return_value = 0.92
        from execution.position_store import sell_position
        await sell_position(pos)
    assert pos.get("exit_bid_at_trigger") == pytest.approx(0.90, abs=1e-4)
    assert pos.get("exit_ask_at_trigger") == pytest.approx(0.92, abs=1e-4)
    assert pos.get("spread_at_trigger") == pytest.approx(0.02, abs=1e-4)

    # İkinci deneme: bid değişse bile exit_bid_at_trigger değişmez
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.85), \
         patch("execution.position_store.ws_prices") as mock_ws:
        mock_ws.get_ask.return_value = 0.87
        await sell_position(pos)
    assert pos.get("exit_bid_at_trigger") == pytest.approx(0.90, abs=1e-4)


@pytest.mark.asyncio
async def test_sell_captures_fill_timing_and_sl_metrics():
    """Başarılı fill: fill_ts, sl_fill_px, sl_fill_pct, trigger_fill_gap_pct, trigger_to_fill_secs set edilir."""
    pos = _open_pos()  # pm_entry_price=0.35
    pos["sl_trigger_pct"] = -0.30
    pos["first_trigger_ts"] = "2026-06-07T10:13:25+00:00"

    fake_client = MagicMock()
    # fill_price = 0.286 / 1.3 = 0.22
    fake_client.create_and_post_order.return_value = _matched_resp(taking="0.286", making="1.3")
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.90), \
         patch("execution.position_store.ws_prices") as mock_ws:
        mock_ws.get_ask.return_value = None
        from execution.position_store import sell_position
        fill_price, making = await sell_position(pos)

    assert fill_price == pytest.approx(0.22, abs=1e-3)
    assert making == pytest.approx(1.3, abs=1e-3)
    assert pos.get("sl_fill_px") == pytest.approx(0.22, abs=1e-3)

    entry = 0.35
    expected_fill_pct = (0.22 - entry) / entry  # ≈ -0.371
    assert pos.get("sl_fill_pct") == pytest.approx(expected_fill_pct, abs=1e-3)

    expected_gap = expected_fill_pct - (-0.30)  # ≈ -0.071
    assert pos.get("trigger_fill_gap_pct") == pytest.approx(expected_gap, abs=1e-3)

    assert pos.get("fill_ts") is not None
    assert pos.get("trigger_to_fill_secs") is not None
    assert pos.get("trigger_to_fill_secs") >= 0


# ── Faz 3: fak_no_match label + sell_limit_price ────────────────────────────

@pytest.mark.asyncio
async def test_sell_position_fak_no_match_label_on_exception(capsys):
    """'no orders found' exception → çıktıda fak_no_match etiketi görünmeli."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.side_effect = Exception(
        "no orders found to match with FAK order"
    )
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.87):
        from execution.position_store import sell_position
        result = await sell_position(_open_pos("YES", bid=0.87))
    assert result is None
    captured = capsys.readouterr().out
    assert "fak_no_match" in captured, f"fak_no_match etiketi beklendi, çıktı: {captured!r}"


@pytest.mark.asyncio
async def test_sell_position_fak_no_match_label_on_unmatched(capsys):
    """status=unmatched (FAK kill) → çıktıda fak_no_match etiketi görünmeli."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {"status": "unmatched", "orderID": "x"}
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.87), \
         patch("execution.position_store.ws_prices") as mock_ws:
        mock_ws.get_ask.return_value = None
        from execution.position_store import sell_position
        result = await sell_position(_open_pos("YES", bid=0.87))
    assert result is None
    captured = capsys.readouterr().out
    assert "fak_no_match" in captured, f"fak_no_match etiketi beklendi, çıktı: {captured!r}"


@pytest.mark.asyncio
async def test_sell_position_stores_sell_limit_price():
    """FAK order'da kullanılan floor_price pos['sell_limit_price']'a kaydedilmeli."""
    from execution.position_store import _FLOOR_BUFFER
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp()
    clob_bid = 0.87
    pos = _open_pos("YES", bid=clob_bid)
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(clob_bid), \
         patch("execution.position_store.ws_prices") as mock_ws:
        mock_ws.get_ask.return_value = None
        from execution.position_store import sell_position
        await sell_position(pos)
    expected_floor = round(max(0.01, clob_bid - _FLOOR_BUFFER), 2)
    assert pos.get("sell_limit_price") == pytest.approx(expected_floor), \
        f"sell_limit_price={pos.get('sell_limit_price')}, beklenen={expected_floor}"
