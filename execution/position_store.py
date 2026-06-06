"""execution/position_store.py — SELL order gönder, fill fiyatını döndür.

Docs: https://docs.polymarket.com/api-reference/introduction
  SELL matched response:
    - status: "matched"
    - takingAmount: USDC received (seller takes USDC from book)
    - makingAmount: shares given (seller gives shares to book)
    - "price" field: DOKÜMANTE DEĞİL — kullanılmaz
  fill_price = takingAmount / makingAmount

  FAK SELL fiyat stratejisi:
    CLOB /price?side=SELL ile gerçek zamanlı bid alınır, 2¢ floor ile FAK gönderilir.
    FAK kill (alıcı yok) → None döner → main_loop pozisyonu AÇIK tutar, sonraki döngüde tekrar dener.
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.clob_client import get_client
from py_clob_client_v2.clob_types import OrderArgs, OrderType
from data.clob_price import get_clob_price

_FLOOR_BUFFER = 0.01   # bid'den bu kadar aşağı floor — PRICE_PREMIUM=0.01 ile simetrik


async def sell_position(pos: dict) -> float | None:
    """Açık pozisyonun token'larını FAK SELL order ile satar.

    pos: position dict — action, yes_token_id, no_token_id, shares gerekli
    Döner:
      float  → fill fiyatı (satış gerçekleşti)
      None   → FAK kill / hata (satış GERÇEKLEŞMEDİ — pozisyonu açık bırak)
    """
    action   = pos["action"]
    token_id = pos["yes_token_id"] if action == "YES" else pos["no_token_id"]
    shares   = pos.get("shares") or 0

    if not token_id or shares <= 0:
        print(f"[sell] {pos.get('slug')}: token_id veya shares eksik/sıfır — atlanıyor")
        return None

    # CLOB'dan gerçek zamanlı sell price (stale market API değil)
    clob_bid = await get_clob_price(token_id, side="SELL")
    stale_bid = float(pos.get("current_bid") or 0.0)
    best_bid = clob_bid if clob_bid else stale_bid

    if best_bid <= 0:
        print(f"[sell] {pos.get('slug')}: bid=0 — CLOB likidite yok, atlanıyor")
        return None

    # Floor fiyatı: gerçek bidden _FLOOR_BUFFER kadar aşağı
    # FAK bu fiyattan veya üstünden doldurur → küçük fiyat hareketlerinde de fill olur
    floor_price = round(max(0.01, best_bid - _FLOOR_BUFFER), 2)

    order_args = OrderArgs(
        token_id=token_id,
        price=floor_price,
        size=shares,
        side="SELL",
    )

    try:
        client = get_client()
        resp   = client.create_and_post_order(order_args, order_type=OrderType.FAK)
    except Exception as e:
        print(f"[sell] {pos.get('slug')}: SELL hatası — {e} → pozisyon açık kalıyor")
        return None  # FAK başarısız → None → main_loop açık tutar

    if not resp:
        print(f"[sell] {pos.get('slug')}: SELL yanıt yok → pozisyon açık kalıyor")
        return None

    def _get(obj, key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    status     = (_get(resp, "status", "") or "").lower()
    taking_str = _get(resp, "takingAmount", None)  # USDC received
    making_str = _get(resp, "makingAmount", None)  # shares given

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
        # takingAmount/makingAmount yoksa başarılı satış kabul et, floor fiyatı kullan
        print(f"[sell] {pos.get('slug')}: SELL matched ama amounts eksik, floor={floor_price:.4f}")
        return floor_price

    # status != matched → FAK kill veya başka hata → pozisyonu açık bırak
    print(f"[sell] {pos.get('slug')}: SELL {status} (fill yok) → pozisyon açık kalıyor")
    return None
