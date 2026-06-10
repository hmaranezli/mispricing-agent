"""execution/order_pricing.py — Faz 2b: taker-intent tick-safe limit price + bounds/cap reject.

Kör round_down YASAK. FAK/IOC AGRESİF TAKER execution intent'ine göre yön:
  TAKER_BUY  (entry): (ask + slippage_buffer) → CEIL_to_tick  (fill garantisi için yukarı)
  TAKER_SELL (exit):  (bid − slippage_buffer) → FLOOR_to_tick (fill garantisi için aşağı)

Out-of-bounds (PRICE_MIN/MAX) veya Max Slippage Cap → SESSİZ clamp YOK → REJECTED:
network call YAPILMAZ; intent FATAL_PREVALIDATION.

Float KESİNLİKLE YASAK → Decimal tick-safe arithmetic.
"""
import hashlib
import json
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

_DEC_MIN = Decimal("0.01")
_DEC_MAX = Decimal("0.99")


def _ceil_to_tick(price: Decimal, tick: Decimal) -> Decimal:
    return (price / tick).quantize(Decimal("1"), rounding=ROUND_CEILING) * tick


def _floor_to_tick(price: Decimal, tick: Decimal) -> Decimal:
    return (price / tick).quantize(Decimal("1"), rounding=ROUND_FLOOR) * tick


def compute_limit_price(intent_side, quote_price, slippage_buffer, tick_size,
                        price_min=_DEC_MIN, price_max=_DEC_MAX, max_slippage_cap=None):
    """Taker-intent limit price. Tümü Decimal. Returns (Decimal limit_price, None) veya
    (None, reject_reason). reject: MAX_SLIPPAGE_EXCEEDED / OUT_OF_BOUNDS / INVALID_TICK / INVALID_SIDE.
    """
    q = Decimal(quote_price); buf = Decimal(slippage_buffer); tick = Decimal(tick_size)
    pmin = Decimal(price_min); pmax = Decimal(price_max)
    if tick <= 0:
        return None, "INVALID_TICK"

    if intent_side == "TAKER_BUY":
        limit = _ceil_to_tick(q + buf, tick)
    elif intent_side == "TAKER_SELL":
        limit = _floor_to_tick(q - buf, tick)
    else:
        return None, "INVALID_SIDE"

    # Max slippage cap (quote'tan sapma) — SESSİZ clamp YOK, reject
    if max_slippage_cap is not None and q > 0:
        cap = Decimal(max_slippage_cap)
        slip = abs(limit - q) / q
        if slip > cap:
            return None, "MAX_SLIPPAGE_EXCEEDED"

    # Bounds — SESSİZ clamp YOK, reject
    if limit < pmin or limit > pmax:
        return None, "OUT_OF_BOUNDS"

    return limit, None


def order_payload_hash(token_id, side, limit_price, size, order_type, tif,
                       reject_reason=None):
    """Canonical (sort_keys) sha256 — borsaya gidecek SON tick-rounded limit_price üzerinden.
    Reject ise reject_reason deterministik biçimde hash'e dahil. Decimal → str (float yasak)."""
    payload = {
        "token_id": token_id,
        "side": side,
        "limit_price": str(limit_price) if limit_price is not None else None,
        "size": str(size) if size is not None else None,
        "order_type": order_type,
        "tif": tif,
        "reject_reason": reject_reason,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
