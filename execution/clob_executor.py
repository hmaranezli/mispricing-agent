"""execution/clob_executor.py — Gerçek Polymarket CLOB order placement.

executor.py ile birebir aynı interface:
  async def execute(finding, gate_result, risk_result, open_positions) -> dict | None
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from uuid import uuid4
from execution.clob_client import get_client
from py_clob_client_v2.clob_types import OrderArgs


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
    shares = round(position_usd / entry_price, 4)

    order_args = OrderArgs(
        token_id=token_id,
        price=entry_price,
        size=shares,
        side="BUY",
    )

    try:
        client = get_client()
        resp   = client.create_and_post_order(order_args)
    except Exception as e:
        print(f"[clob] {finding['slug']}: order hatası — {e}")
        return None

    if not resp:
        return None

    # py-clob-client dict veya object döndürebilir — her ikisini de destekle
    def _get(obj, key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    status       = _get(resp, "status", "")
    order_id     = _get(resp, "orderID", "")
    size_filled  = _get(resp, "sizeFilled", "0")
    fill_price_s = _get(resp, "price", str(entry_price))

    if status != "MATCHED":
        print(f"[clob] {finding['slug']}: order UNMATCHED (status={status})")
        return None

    fill_price  = float(fill_price_s or entry_price)
    fill_shares = float(size_filled or shares)

    if fill_shares <= 0:
        print(f"[clob] {finding['slug']}: fill_shares=0, pozisyon açılmadı")
        return None

    if fill_shares < shares * 0.99:
        print(f"[clob] {finding['slug']}: kısmi dolma — beklenen={shares:.4f}, gerçek={fill_shares:.4f}")

    return {
        "position_id":             str(uuid4()),
        "asset":                   finding["asset"],
        "action":                  action,
        "slug":                    finding["slug"],
        "pm_entry_price":          fill_price,
        "fair_value":              finding["fair_value"],
        "ref_price":               finding["ref_price"],
        "edge":                    finding["edge"],
        "position_usd":            fill_price * fill_shares,
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
