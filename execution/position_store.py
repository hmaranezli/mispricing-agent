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

from datetime import datetime, timezone
from execution.clob_client import get_client
from py_clob_client_v2.clob_types import OrderArgs, OrderType
from data.clob_price import get_clob_price
import data.ws_prices as ws_prices

_FLOOR_BUFFER = 0.01   # bid'den bu kadar aşağı floor — PRICE_PREMIUM=0.01 ile simetrik


async def sell_position(pos: dict) -> tuple[float, float] | None:
    """Açık pozisyonun token'larını FAK SELL order ile satar.

    pos: position dict — action, yes_token_id, no_token_id, shares gerekli
    Döner:
      (fill_price, making_shares) → satış gerçekleşti (kısmi veya tam)
      None                        → FAK kill / hata (satış GERÇEKLEŞMEDİ — pozisyonu açık bırak)

    Tam/kısmi ayrımı çağıran (_monitor_positions) tarafından yapılır:
      making_shares >= pos["shares"] * 0.98 → tam kapanış
      making_shares < pos["shares"] * 0.98  → kısmi fill, shares güncelle, tekrar dene

    Side effects (pos dict güncellenir):
      sell_attempt_count, sell_unmatched_count, exit_bid_at_trigger,
      exit_ask_at_trigger, spread_at_trigger, fill_ts, sl_fill_px,
      sl_fill_pct, trigger_fill_gap_pct, trigger_to_fill_secs
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

    ws_ask = ws_prices.get_ask(token_id)

    # Book snapshot: yalnızca ilk denemede yaz (setdefault — FAK retry üzerine yazmaz)
    pos.setdefault("exit_bid_at_trigger", best_bid if best_bid > 0 else None)
    pos.setdefault("exit_ask_at_trigger", ws_ask)
    if best_bid and ws_ask:
        pos.setdefault("spread_at_trigger", round(ws_ask - best_bid, 4))
    pos["book_depth_at_trigger"] = None  # REST CLOB depth yok; Faz 2 WS ile gelecek

    pos["sell_attempt_count"] = pos.get("sell_attempt_count", 0) + 1

    if best_bid <= 0:
        print(f"[sell] {pos.get('slug')}: bid=0 — CLOB likidite yok, atlanıyor")
        pos["sell_unmatched_count"] = pos.get("sell_unmatched_count", 0) + 1
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
        pos["sell_unmatched_count"] = pos.get("sell_unmatched_count", 0) + 1
        return None

    if not resp:
        print(f"[sell] {pos.get('slug')}: SELL yanıt yok → pozisyon açık kalıyor")
        pos["sell_unmatched_count"] = pos.get("sell_unmatched_count", 0) + 1
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
                _record_fill(pos, fill_price)
                print(f"[sell] {pos.get('slug')}: SELL FILLED {making:.4f} shares → ${taking:.4f} @ {fill_price:.4f}")
                return (fill_price, making)
        except (ValueError, TypeError):
            pass
        # takingAmount/makingAmount yoksa başarılı satış kabul et, tam fill say
        _record_fill(pos, floor_price)
        assumed_making = pos.get("shares") or 0.0
        print(f"[sell] {pos.get('slug')}: SELL matched ama amounts eksik, floor={floor_price:.4f}")
        return (floor_price, assumed_making)

    # status != matched → FAK kill veya başka hata → pozisyonu açık bırak
    pos["sell_unmatched_count"] = pos.get("sell_unmatched_count", 0) + 1
    print(f"[sell] {pos.get('slug')}: SELL {status} (fill yok) → pozisyon açık kalıyor")
    return None


def _record_fill(pos: dict, fill_price: float) -> None:
    """Başarılı fill sonrası timing ve slippage metriklerini pos'a yazar."""
    fill_ts = datetime.now(timezone.utc).isoformat()
    pos["fill_ts"]    = fill_ts
    pos["sl_fill_px"] = fill_price

    entry = pos.get("pm_entry_price")
    if entry and entry > 0:
        sl_fill_pct = round((fill_price - entry) / entry, 6)
        pos["sl_fill_pct"] = sl_fill_pct
        sl_trigger_pct = pos.get("sl_trigger_pct")
        if sl_trigger_pct is not None:
            pos["trigger_fill_gap_pct"] = round(sl_fill_pct - sl_trigger_pct, 6)

    first_trigger_ts = pos.get("first_trigger_ts")
    if first_trigger_ts:
        try:
            dt_trigger = datetime.fromisoformat(first_trigger_ts)
            dt_fill    = datetime.fromisoformat(fill_ts)
            pos["trigger_to_fill_secs"] = round(
                (dt_fill - dt_trigger).total_seconds(), 2
            )
        except ValueError:
            pass
