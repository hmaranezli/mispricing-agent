"""execution/position_store.py — SELL order gönder, fill fiyatını döndür."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.clob_client import get_client


async def sell_position(pos: dict) -> float:
    """
    Açık pozisyonun token'larını satar (IOC SELL order).

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

    order_args = {
        "token_id":      token_id,
        "price":         fallback,
        "size":          shares,
        "side":          "SELL",
        "time_in_force": "IOC",
    }

    try:
        client = get_client()
        resp   = client.create_and_post_order(order_args)
    except Exception as e:
        print(f"[sell] {pos.get('slug')}: SELL hatası — {e}, fallback={fallback:.4f}")
        return fallback

    if not resp:
        return fallback

    status    = resp.get("status") if isinstance(resp, dict) else getattr(resp, "status", "")
    price_str = resp.get("price")  if isinstance(resp, dict) else getattr(resp, "price", None)

    if status == "MATCHED" and price_str:
        return float(price_str)

    print(f"[sell] {pos.get('slug')}: SELL {status}, fallback={fallback:.4f}")
    return fallback
