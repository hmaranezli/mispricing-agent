"""execution/clob_executor.py — Gerçek Polymarket CLOB order placement.

executor.py ile birebir aynı interface:
  async def execute(finding, gate_result, risk_result, open_positions) -> dict | None

Docs: https://docs.polymarket.com/trading/orders/create.md
- BUY market order: MarketOrderArgs(amount=USD, price=worst_price_limit)
- FAK = Fill-And-Kill: fills available depth, cancels remainder → partial fills OK
- PartialCreateOrderOptions(tick_size, neg_risk) zorunlu
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from uuid import uuid4
import aiohttp
from execution.clob_client import get_client
from py_clob_client_v2 import MarketOrderArgs, OrderType, PartialCreateOrderOptions
from py_clob_client_v2.order_builder.constants import BUY

CLOB_HOST     = "https://clob.polymarket.com"
PRICE_PREMIUM = 0.03   # worst-price slippage buffer: live_ask + 3 cent
TICK_SIZE     = "0.01" # binary prediction markets default tick size


async def _get_clob_price(token_id: str) -> float | None:
    """CLOB /price?side=BUY → token için anlık best ask fiyatı."""
    try:
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(f"{CLOB_HOST}/price",
                             params={"token_id": token_id, "side": "BUY"}) as r:
                if r.status == 200:
                    data = await r.json()
                    p = float(data.get("price", 0))
                    return p if p > 0 else None
    except Exception:
        pass
    return None


async def execute(
    finding:        dict,
    gate_result:    dict,
    risk_result:    dict,
    open_positions: list[dict],
) -> dict | None:
    """Polymarket CLOB'a FAK market BUY order gönder.

    FAK (Fill-And-Kill): mevcut derinliği doldurur, kalanı iptal eder.
    FOK (Fill-Or-Kill) yerine FAK kullanılır — kısmi fill kabul edilir.
    Dolarsa position dict döner, dolmazsa None.
    """
    action   = finding["action"]
    token_id = finding["yes_token_id"] if action == "YES" else finding["no_token_id"]

    if not token_id:
        print(f"[clob] {finding['slug']}: token_id yok, order gönderilmedi")
        return None

    position_usd = risk_result["position_usd"]
    if position_usd < 1.0:
        print(f"[clob] {finding['slug']}: position_usd={position_usd:.2f} < $1 minimum, atlandı")
        return None

    # CLOB'dan anlık fiyat — council gecikmesini (~5s) kompanse et
    clob_price  = await _get_clob_price(token_id)
    live_ask    = clob_price if clob_price else finding["best_ask"]
    worst_price = round(live_ask + PRICE_PREMIUM, 4)  # slippage limit

    print(f"[clob] {finding['slug']}: FAK BUY amount=${position_usd:.2f} worst_price={worst_price:.4f} (live={live_ask:.4f}+{PRICE_PREMIUM})")

    try:
        client = get_client()
        market_order = client.create_market_order(
            order_args=MarketOrderArgs(
                token_id=token_id,
                side=BUY,
                amount=position_usd,      # BUY için: dolar miktarı (docs: "dollar amount to spend")
                price=worst_price,        # worst-price slippage koruması
                order_type=OrderType.FAK, # explicit: kütüphane default FOK — override zorunlu
            ),
            options=PartialCreateOrderOptions(
                tick_size=TICK_SIZE,
                neg_risk=finding.get("neg_risk", False),
            ),
        )
        resp = client.post_order(market_order, OrderType.FAK)
    except Exception as e:
        print(f"[clob] {finding['slug']}: order hatası — {e}")
        return None

    if not resp:
        return None

    def _get(obj, key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    status        = _get(resp, "status", "")
    success       = _get(resp, "success", False)
    order_id      = _get(resp, "orderID", "")
    taking_amount = _get(resp, "takingAmount", None)  # v2: fill edilen share
    making_amount = _get(resp, "makingAmount", None)  # v2: harcanan USDC

    # FAK: "matched" = fill oldu (tam veya kısmi) — docs statuses: matched/live/delayed/unmatched
    matched = (status or "").lower() == "matched"
    if not matched:
        print(f"[clob] {finding['slug']}: FAK UNMATCHED (status={status})")
        return None

    fill_shares = float(taking_amount) if taking_amount and float(taking_amount) > 0 else 0.0
    if fill_shares <= 0:
        print(f"[clob] {finding['slug']}: fill_shares=0")
        return None

    pos_usd    = float(making_amount) if making_amount else position_usd
    fill_price = round(pos_usd / fill_shares, 6) if fill_shares > 0 else worst_price

    print(f"[clob] {finding['slug']}: FILLED {fill_shares:.4f} shares @ ${fill_price:.4f} (${pos_usd:.2f})")

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
        "entry_hl_price":          finding.get("cur_price"),
        "requires_human_approval": False,
        "dry_run":                 False,
        "status":                  "open",
        "opened_at":               datetime.now(timezone.utc).isoformat(),
    }
