"""tests/test_clob_executor.py — clob_executor execute() testleri (FAK + MarketOrderArgs)."""
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

def _fake_matched_resp():
    return {
        "status": "matched", "success": True, "orderID": "ord-abc",
        "takingAmount": "71.43",   # shares received
        "makingAmount": "25.00",   # USDC spent
    }


# ── Temel FAK fill davranışı ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_returns_position_on_matched_fak():
    """FAK 'matched' → position dict döner, gerekli alanlar dolu."""
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
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
async def test_execute_returns_none_when_fak_unmatched():
    """FAK UNMATCHED → None döner, pozisyon açılmaz."""
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = {"status": "unmatched", "orderID": "x"}
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
        from execution.clob_executor import execute
        result = await execute(_finding("YES"), _gate(), _risk(), [])
    assert result is None


@pytest.mark.asyncio
async def test_execute_uses_yes_token_for_yes_action():
    """YES action → yes_token_id FAK order'a gönderilir."""
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
        from execution.clob_executor import execute
        await execute(_finding("YES"), _gate(), _risk(), [])
    market_order_args = fake_client.create_market_order.call_args[1]["order_args"]
    assert market_order_args.token_id == "yes-tok-111"


@pytest.mark.asyncio
async def test_execute_uses_no_token_for_no_action():
    """NO action → no_token_id FAK order'a gönderilir."""
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
        from execution.clob_executor import execute
        await execute(_finding("NO"), _gate(), _risk(), [])
    market_order_args = fake_client.create_market_order.call_args[1]["order_args"]
    assert market_order_args.token_id == "no-tok-222"


@pytest.mark.asyncio
async def test_execute_uses_fak_order_type():
    """post_order OrderType.FAK ile çağrılır — FOK değil."""
    from py_clob_client_v2 import OrderType
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
        from execution.clob_executor import execute
        await execute(_finding("YES"), _gate(), _risk(), [])
    order_type_arg = fake_client.post_order.call_args[0][1]
    assert order_type_arg == OrderType.FAK, f"FAK beklendi, {order_type_arg} geldi"


@pytest.mark.asyncio
async def test_execute_passes_dollar_amount_not_shares():
    """BUY market order'da amount = dolar miktarı (shares değil) — docs zorunluluğu."""
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
        from execution.clob_executor import execute
        await execute(_finding("YES"), _gate(), _risk(), [])
    market_order_args = fake_client.create_market_order.call_args[1]["order_args"]
    # amount == position_usd (25.0), shares olmayacak (25/0.38 ~ 65 gibi bir şey)
    assert abs(market_order_args.amount - 25.0) < 0.01, \
        f"amount dolar miktarı olmalı (25.0), {market_order_args.amount} geldi"


@pytest.mark.asyncio
async def test_execute_passes_tick_size_options():
    """PartialCreateOrderOptions tick_size geçirilir — docs zorunluluğu."""
    from py_clob_client_v2 import PartialCreateOrderOptions
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
        from execution.clob_executor import execute
        await execute(_finding("YES"), _gate(), _risk(), [])
    opts = fake_client.create_market_order.call_args[1]["options"]
    assert isinstance(opts, PartialCreateOrderOptions)
    assert opts.tick_size == "0.01"
    assert opts.neg_risk is False


@pytest.mark.asyncio
async def test_execute_worst_price_includes_premium():
    """worst_price = live_ask + PRICE_PREMIUM — slippage koruması."""
    from execution.clob_executor import PRICE_PREMIUM
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.52)):
        from execution.clob_executor import execute
        await execute(_finding("YES"), _gate(), _risk(), [])
    market_order_args = fake_client.create_market_order.call_args[1]["order_args"]
    expected = round(0.52 + PRICE_PREMIUM, 4)
    assert abs(market_order_args.price - expected) < 1e-4, \
        f"worst_price={market_order_args.price:.4f}, beklenen={expected:.4f}"


@pytest.mark.asyncio
async def test_execute_falls_back_to_finding_ask_when_clob_price_fails():
    """_get_clob_price None → finding['best_ask'] + PRICE_PREMIUM fallback."""
    from execution.clob_executor import PRICE_PREMIUM
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=None):
        from execution.clob_executor import execute
        await execute(_finding("YES"), _gate(), _risk(), [])
    market_order_args = fake_client.create_market_order.call_args[1]["order_args"]
    expected = round(0.35 + PRICE_PREMIUM, 4)  # finding["best_ask"] = 0.35
    assert abs(market_order_args.price - expected) < 1e-4


@pytest.mark.asyncio
async def test_execute_position_includes_entry_hl_price():
    """LIVE position dict'te entry_hl_price = finding['cur_price'] olmalı."""
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()
    finding = {**_finding("YES"), "cur_price": 66500.0}
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
        from execution.clob_executor import execute
        result = await execute(finding, _gate(), _risk(), [])
    assert result is not None
    assert result.get("entry_hl_price") == 66500.0


@pytest.mark.asyncio
async def test_execute_returns_none_when_token_id_missing():
    """token_id yoksa order gönderilmez, None döner."""
    finding = {**_finding("YES"), "yes_token_id": None}
    with patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
        from execution.clob_executor import execute
        result = await execute(finding, _gate(), _risk(), [])
    assert result is None


@pytest.mark.asyncio
async def test_execute_returns_none_when_position_too_small():
    """position_usd < $1 → order gönderilmez."""
    risk = {**_risk(), "position_usd": 0.50}
    with patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
        from execution.clob_executor import execute
        result = await execute(_finding("YES"), _gate(), risk, [])
    assert result is None


@pytest.mark.asyncio
async def test_execute_market_order_args_has_fak_order_type():
    """MarketOrderArgs.order_type=FAK geçirilmeli — kütüphane default'u FOK, açıkça override zorunlu."""
    from py_clob_client_v2 import OrderType
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
        from execution.clob_executor import execute
        await execute(_finding("YES"), _gate(), _risk(), [])
    order_args = fake_client.create_market_order.call_args[1]["order_args"]
    assert order_args.order_type == OrderType.FAK, \
        f"MarketOrderArgs.order_type FAK olmalı (kütüphane default FOK!), geldi: {order_args.order_type}"


@pytest.mark.asyncio
async def test_execute_matched_without_success_field():
    """status='matched' yeterli — 'success' field dokümante değil, olmaması gerekmez."""
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    # success alanı yok — sadece status var
    fake_client.post_order.return_value = {
        "status": "matched", "orderID": "ord-xyz",
        "takingAmount": "71.43", "makingAmount": "25.00",
    }
    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=_qask(0.35)):
        from execution.clob_executor import execute
        result = await execute(_finding("YES"), _gate(), _risk(), [])
    assert result is not None, "status='matched' ile position açılmalıydı"
