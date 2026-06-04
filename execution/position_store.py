"""execution/position_store.py — SELL order gönder, fill fiyatını döndür.

Docs: https://docs.polymarket.com/api-reference/introduction
  SELL matched response:
    - status: "matched"
    - takingAmount: USDC received (seller takes USDC from book)
    - makingAmount: shares given (seller gives shares to book)
    - "price" field: DOKÜMANTE DEĞİL — kullanılmaz
  fill_price = takingAmount / makingAmount
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.clob_client import get_client
from py_clob_client_v2.clob_types import OrderArgs, OrderType


async def sell_position(pos: dict) -> float:
    """Açık pozisyonun token'larını FAK SELL order ile satar.

    pos: position dict — action, yes_token_id, no_token_id, shares, current_bid gerekli
    Döner: fill fiyatı (float). API başarısızsa current_bid fallback.
    """
    action   = pos["action"]
    token_id = pos["yes_token_id"] if action == "YES" else pos["no_token_id"]
    shares   = pos.get("shares") or 0
    bid      = pos.get("current_bid")
    fallback = float(bid) if bid is not None else 0.0

    if not token_id or shares <= 0:
        print(f"[sell] {pos.get('slug')}: token_id veya shares eksik/sıfır, fallback={fallback:.4f}")
        return fallback

    order_args = OrderArgs(
        token_id=token_id,
        price=fallback,
        size=shares,
        side="SELL",
    )

    try:
        client = get_client()
        resp   = client.create_and_post_order(order_args, order_type=OrderType.FAK)
    except Exception as e:
        print(f"[sell] {pos.get('slug')}: SELL hatası — {e}, fallback={fallback:.4f}")
        return fallback

    if not resp:
        return fallback

    def _get(obj, key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    status       = (_get(resp, "status", "") or "").lower()
    taking_str   = _get(resp, "takingAmount", None)  # USDC received
    making_str   = _get(resp, "makingAmount", None)  # shares given

    if status == "matched":
        try:
            taking = float(taking_str) if taking_str else 0.0
            making = float(making_str) if making_str else 0.0
            if making > 0 and taking > 0:
                fill_price = round(taking / making, 6)
                print(f"[sell] {pos.get('slug')}: SELL FILLED {making:.4f} shares → ${taking:.4f} @ {fill_price:.4f}")
                return fill_price
        except (ValueError, TypeError):
            pass
        # takingAmount/makingAmount yoksa fallback (docs'ta garanti değil)
        print(f"[sell] {pos.get('slug')}: SELL matched ama amounts eksik, fallback={fallback:.4f}")
        return fallback

    print(f"[sell] {pos.get('slug')}: SELL {status}, fallback={fallback:.4f}")
    return fallback
