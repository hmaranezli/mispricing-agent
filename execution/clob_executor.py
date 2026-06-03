"""execution/clob_executor.py — Gerçek Polymarket CLOB order placement.

executor.py ile birebir aynı interface:
  async def execute(finding, gate_result, risk_result, open_positions) -> dict | None
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone
from uuid import uuid4
from execution.clob_client import get_client
from py_clob_client_v2.clob_types import OrderArgs, OrderType

MIN_SHARES = 1  # Canary testi ile doğrulandı: CLOB gerçek min = $1 USDC, 5 share değil


def _calc_shares(usdc: float, price: float) -> float:
    """price × shares'in tam olarak ≤2 decimal olduğu en yüksek hassasiyeti döndür.
    CLOB kuralı: maker_amount (USDC) max 2dp, taker_amount (shares) max 4dp.
    Kontrol: (maker × 100) % 1 == 0 → trailing-zero'larla da çalışır.
    """
    p = Decimal(str(round(price, 2)))
    budget = Decimal(str(round(usdc, 2)))
    for precision in ("0.0001", "0.001", "0.01", "0.1", "1"):
        s = (budget / p).quantize(Decimal(precision), rounding=ROUND_DOWN)
        if (s * p * 100) % 1 == 0:
            return float(s)
    return max(1.0, float((budget / p).quantize(Decimal("1"), rounding=ROUND_DOWN)))


async def execute(
    finding:        dict,
    gate_result:    dict,
    risk_result:    dict,
    open_positions: list[dict],
) -> dict | None:
    """Polymarket CLOB'a BUY IOC order gönder. Dolarsa position dict döner, dolmazsa None."""
    action   = finding["action"]
    token_id = finding["yes_token_id"] if action == "YES" else finding["no_token_id"]

    if not token_id:
        print(f"[clob] {finding['slug']}: token_id yok, order gönderilmedi")
        return None

    position_usd = risk_result["position_usd"]
    entry_price  = finding["best_ask"]
    if entry_price <= 0:
        return None
    if position_usd < 1.0:
        print(f"[clob] {finding['slug']}: position_usd={position_usd:.2f} < $1 minimum, atlandı")
        return None
    shares = _calc_shares(position_usd, entry_price)
    if shares < MIN_SHARES:
        print(f"[clob] {finding['slug']}: shares={shares:.2f} < {MIN_SHARES} minimum, atlandı")
        return None

    order_args = OrderArgs(
        token_id=token_id,
        price=entry_price,
        size=shares,
        side="BUY",
    )

    try:
        client = get_client()
        resp   = client.create_and_post_order(order_args, order_type=OrderType.FOK)
    except Exception as e:
        print(f"[clob] {finding['slug']}: order hatası — {e}")
        return None

    if not resp:
        return None

    # py-clob-client dict veya object döndürebilir — her ikisini de destekle
    def _get(obj, key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    status         = _get(resp, "status", "")
    success        = _get(resp, "success", False)
    order_id       = _get(resp, "orderID", "")
    taking_amount  = _get(resp, "takingAmount", None)   # v2: gerçek share sayısı
    making_amount  = _get(resp, "makingAmount", None)   # v2: USDC harcanan
    size_filled    = _get(resp, "sizeFilled", None)     # v1: fill edilen share

    matched = success is True or status.lower() == "matched"
    if not matched:
        print(f"[clob] {finding['slug']}: order UNMATCHED (status={status})")
        return None

    # fill_shares: v2 takingAmount → v1 sizeFilled → FOK fallback (tümü doldu)
    if taking_amount is not None and float(taking_amount) > 0:
        fill_shares = float(taking_amount)
    elif size_filled is not None and float(size_filled) > 0:
        fill_shares = float(size_filled)
    else:
        fill_shares = shares

    if fill_shares <= 0:
        print(f"[clob] {finding['slug']}: fill_shares=0, pozisyon açılmadı")
        return None

    # fill_price: v2'de making/taking → v1'de "price" alanı → limit fiyatı fallback
    if making_amount and float(taking_amount or 0) > 0:
        fill_price = round(float(making_amount) / float(taking_amount), 6)
    else:
        fill_price_s = _get(resp, "price", str(entry_price))
        fill_price   = float(fill_price_s or entry_price)

    # position_usd: USDC gerçekten harcanan (v2 making_amount) veya fill × shares
    pos_usd = float(making_amount) if making_amount else fill_price * fill_shares

    return {
        "position_id":             str(uuid4()),
        "asset":                   finding["asset"],
        "action":                  action,
        "slug":                    finding["slug"],
        "pm_entry_price":          fill_price,
        "fair_value":              finding["fair_value"],
        "ref_price":               finding["ref_price"],
        "edge":                    finding["edge"],
        "position_usd":            pos_usd,
        "kelly_f":                 risk_result["kelly_f"],
        "confidence_score":        gate_result["confidence_score"],
        "shares":                  fill_shares,
        "order_id":                order_id,
        "fill_price":              fill_price,
        "yes_token_id":            finding.get("yes_token_id"),
        "no_token_id":             finding.get("no_token_id"),
        "requires_human_approval": False,
        "dry_run":                 False,
        "status":                  "open",
        "opened_at":               datetime.now(timezone.utc).isoformat(),
    }
