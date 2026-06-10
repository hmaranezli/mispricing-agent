"""tests/test_order_pricing.py — Faz 2b: taker-intent tick-safe limit price + bounds/cap reject.

Kör round_down YASAK. FAK/IOC taker intent'ine göre:
  TAKER_BUY entry:  (ask + buffer) → ceil_to_tick
  TAKER_SELL exit:  (bid − buffer) → floor_to_tick
Out-of-bounds / Max Slippage Cap → SESSİZ clamp YOK → REJECTED, network call YAPILMAZ.
Float YASAK → Decimal tick-safe arithmetic.
"""
import sys
import os
from decimal import Decimal
import inspect
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 1. Taker BUY → ceil_to_tick
def test_taker_buy_ceil_to_tick():
    from execution.order_pricing import compute_limit_price
    # quote ask=0.553, buffer=0.01 → raw=0.563 → ceil(tick 0.01)=0.57
    px, reason = compute_limit_price("TAKER_BUY", Decimal("0.553"), Decimal("0.01"),
                                     Decimal("0.01"), max_slippage_cap=Decimal("0.10"))
    assert reason is None
    assert px == Decimal("0.57"), f"ceil_to_tick beklenen 0.57, alınan {px}"


# 2. Taker SELL → floor_to_tick
def test_taker_sell_floor_to_tick():
    from execution.order_pricing import compute_limit_price
    # quote bid=0.557, buffer=0.01 → raw=0.547 → floor(tick 0.01)=0.54
    px, reason = compute_limit_price("TAKER_SELL", Decimal("0.557"), Decimal("0.01"),
                                     Decimal("0.01"), max_slippage_cap=Decimal("0.10"))
    assert reason is None
    assert px == Decimal("0.54"), f"floor_to_tick beklenen 0.54, alınan {px}"


# 3. Max Slippage Cap aşımı → REJECTED
def test_max_slippage_cap_exceeded_reject():
    from execution.order_pricing import compute_limit_price
    # buffer 0.10, quote 0.50 → raw 0.60, sapma %20 > cap %3 → reject
    px, reason = compute_limit_price("TAKER_BUY", Decimal("0.50"), Decimal("0.10"),
                                     Decimal("0.01"), max_slippage_cap=Decimal("0.03"))
    assert px is None
    assert reason == "MAX_SLIPPAGE_EXCEEDED"


# 4. Out-of-bounds → REJECTED (sessiz clamp YOK)
def test_out_of_bounds_reject_no_clamp():
    from execution.order_pricing import compute_limit_price
    # quote 0.99 + buffer 0.05 BUY → raw 1.04 → ceil > PRICE_MAX 0.99 → reject (clamp DEĞİL)
    px, reason = compute_limit_price("TAKER_BUY", Decimal("0.99"), Decimal("0.05"),
                                     Decimal("0.01"), price_max=Decimal("0.99"),
                                     max_slippage_cap=Decimal("0.50"))
    assert px is None, "out-of-bounds clamp edilmemeli, reject olmalı"
    assert reason == "OUT_OF_BOUNDS"


# 5. Canonical hash rounded limit price ile değişir
def test_payload_hash_uses_rounded_limit_price():
    from execution.order_pricing import order_payload_hash
    h1 = order_payload_hash(token_id="t", side="BUY", limit_price=Decimal("0.57"),
                            size=Decimal("25"), order_type="FAK", tif="FAK")
    h2 = order_payload_hash(token_id="t", side="BUY", limit_price=Decimal("0.58"),
                            size=Decimal("25"), order_type="FAK", tif="FAK")
    assert h1 != h2, "rounded limit price değişince hash değişmeli"
    # key sırası bağımsız (canonical) — aynı değerler aynı hash
    h3 = order_payload_hash(size=Decimal("25"), token_id="t", limit_price=Decimal("0.57"),
                            tif="FAK", order_type="FAK", side="BUY")
    assert h1 == h3, "canonical: key sırası hash'i değiştirmemeli"


# 6. Float hassasiyet hatası yok (Decimal arithmetic)
def test_decimal_no_float_error():
    from execution.order_pricing import compute_limit_price
    # 0.1+0.2 float'ta 0.30000000000000004; Decimal'da tam 0.30
    px, reason = compute_limit_price("TAKER_BUY", Decimal("0.20"), Decimal("0.10"),
                                     Decimal("0.01"), max_slippage_cap=Decimal("1.0"))
    assert reason is None
    assert px == Decimal("0.30"), f"Decimal tam 0.30 olmalı, alınan {px}"
    # dönüş tipi Decimal (float değil)
    assert isinstance(px, Decimal)


# 7. Reject → network call YAPILMAZ (execute entegrasyonu)
@pytest.mark.asyncio
async def test_reject_no_network_call():
    import execution.clob_executor as ce
    from unittest.mock import AsyncMock, patch
    from data.orderbook_snapshot import OrderbookSnapshot
    import time as _t
    # out-of-bounds quote → pre-validation reject → create_market_order ÇAĞRILMAMALI
    snap = OrderbookSnapshot(bid=0.98, ask=0.99, bid_size=1e4, ask_size=1e4,
                             source="rest_book", ts=_t.time())
    finding = {"slug": "s", "action": "YES", "yes_token_id": "tok", "no_token_id": "n",
               "best_ask": 0.99}
    risk = {"position_usd": 25.0}
    mock_client = AsyncMock()
    with patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=snap), \
         patch("execution.clob_executor.get_client", return_value=mock_client), \
         patch("execution.clob_executor.PRICE_PREMIUM", 0.05):
        result = await ce.execute(finding, {}, risk, [])
    # out-of-bounds (0.99+0.05 ceil > 0.99) → reject → order gönderilmedi
    assert not mock_client.create_market_order.called, "reject'te create_market_order çağrılmamalı"
    assert result is None
