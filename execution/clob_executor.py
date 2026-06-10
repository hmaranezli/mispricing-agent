"""execution/clob_executor.py — Gerçek Polymarket CLOB order placement.

executor.py ile birebir aynı interface:
  async def execute(finding, gate_result, risk_result, open_positions) -> dict | None

Docs: https://docs.polymarket.com/trading/orders/create.md
- BUY market order: MarketOrderArgs(amount=USD, price=worst_price_limit)
- FAK = Fill-And-Kill: fills available depth, cancels remainder → partial fills OK
- PartialCreateOrderOptions(tick_size, neg_risk) zorunlu
"""
import asyncio
import re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from uuid import uuid4
from execution.clob_client import get_client
from py_clob_client_v2 import MarketOrderArgs, OrderType, PartialCreateOrderOptions
from py_clob_client_v2.order_builder.constants import BUY
from data.clob_price import get_quote
from execution.order_pricing import compute_limit_price
from data.shadow_quote import get_shadow_quote
from db.logger import log_entry_air_pocket, update_entry_air_pocket_delayed
import config

PRICE_PREMIUM = 0.01   # worst-price slippage buffer: live_ask + 1 cent
TICK_SIZE     = "0.01" # binary prediction markets default tick size


async def _handle_fak_no_match(
    finding:         dict,
    gate_result:     dict,
    token_id:        str,
    council_pass_ts: str | None,
    order_submit_ts: str,
    error_ts:        str,
    live_ask:        float,
    worst_price:     float,
    e_str:           str,
    conn,
) -> None:
    """FAK_NO_MATCH sonrası telemetri: immediate shadow quote + DB log + delayed task.

    Canlı retry YOK. Hiçbir yeni emir gönderilmez.
    Bu fonksiyon ana execution path'te await edilir ama trade kararını değiştirmez.
    """
    # ── Zamanlama (ms) ──────────────────────────────────────────────────────
    council_to_submit_ms = None
    if council_pass_ts:
        try:
            t_c = datetime.fromisoformat(council_pass_ts)
            t_s = datetime.fromisoformat(order_submit_ts)
            council_to_submit_ms = round((t_s - t_c).total_seconds() * 1000, 1)
        except Exception:
            pass
    try:
        t_s = datetime.fromisoformat(order_submit_ts)
        t_e = datetime.fromisoformat(error_ts)
        submit_to_error_ms = round((t_e - t_s).total_seconds() * 1000, 1)
    except Exception:
        submit_to_error_ms = None

    # ── order_id extraction (error string içinden) ──────────────────────────
    m        = re.search(r"'orderID':\s*'(0x[0-9a-fA-F]+)'", e_str)
    order_id = m.group(1) if m else None

    # ── Immediate shadow quote (WS cache veya REST < 2s) ────────────────────
    min_edge = getattr(config, "MIN_EDGE_PCT", 0.04)
    action   = finding.get("action", "YES")
    fair     = finding.get("fair_value", 0.0)

    try:
        shadow = await get_shadow_quote(
            token_id=token_id,
            action=action,
            fair=fair,
            original_ask=live_ask,
            min_edge=min_edge,
        )
    except Exception as sq_err:
        print(f"[air_pocket] shadow_quote hatası ({finding.get('slug')}): {sq_err}")
        shadow = {
            "ask": None, "no_ask": None, "book_age_ms": None,
            "fee_adj": None, "price_delta_cents": None,
            "edge_still_passes": None, "would_retry_passed": None,
            "source": "none", "top_size": None, "levels": None,
        }

    def _int_flag(v) -> int | None:
        return (1 if v else 0) if v is not None else None

    event = {
        "slug":                  finding.get("slug"),
        "asset":                 finding.get("asset"),
        "action":                action,
        "market_id":             None,
        "token_id":              token_id,
        "event_ts":              error_ts,
        "council_pass_ts":       council_pass_ts,
        "order_submit_ts":       order_submit_ts,
        "error_ts":              error_ts,
        "council_to_submit_ms":  council_to_submit_ms,
        "submit_to_error_ms":    submit_to_error_ms,
        "fair":                  fair,
        "expected_ask":          finding.get("best_ask"),
        "original_worst_price":  worst_price,
        "original_fee_adj":      gate_result.get("fee_adj_edge"),
        "min_edge":              min_edge,
        "reported_liquidity":    gate_result.get("liquidity_usd"),
        "top_of_book_size":      shadow.get("top_size"),
        "book_levels_used":      shadow.get("levels"),
        "book_source":           shadow.get("source"),
        "book_age_ms":           shadow.get("book_age_ms"),
        "order_id":              order_id,
        "error_type":            "fak_no_match",
        "position_created":      0,
        # Immediate shadow
        "fresh_ask_after_fail":             shadow.get("ask") if action == "YES" else None,
        "fresh_no_ask_after_fail":          shadow.get("ask") if action == "NO"  else None,
        "fresh_book_age_ms":                shadow.get("book_age_ms"),
        "fresh_fee_adj_after_fail":         shadow.get("fee_adj"),
        "fresh_price_delta_cents":          shadow.get("price_delta_cents"),
        "fresh_edge_still_passes_min_edge": _int_flag(shadow.get("edge_still_passes")),
        "would_retry_passed_shadow":        _int_flag(shadow.get("would_retry_passed")),
        # Delayed — background task tarafından doldurulacak
        "delayed_ask_after_fail":             None,
        "delayed_no_ask_after_fail":          None,
        "delayed_book_age_ms":                None,
        "delayed_fee_adj_after_fail":         None,
        "delayed_price_delta_cents":          None,
        "delayed_edge_still_passes_min_edge": None,
        "delayed_would_retry_passed_shadow":  None,
    }

    event_id = None
    if conn is not None:
        try:
            event_id = await log_entry_air_pocket(conn, event)
        except Exception as log_err:
            print(f"[air_pocket] DB log hatası ({finding.get('slug')}): {log_err}")

    print(f"[air_pocket] {finding.get('slug')} FAK_NO_MATCH — event_id={event_id} "
          f"fresh_ask={shadow.get('ask')} would_retry={shadow.get('would_retry_passed')}")

    # ── Delayed snapshot (fire-and-forget) ──────────────────────────────────
    if event_id is not None and conn is not None:
        asyncio.create_task(_delayed_capture_and_store(
            event_id=event_id,
            conn=conn,
            token_id=token_id,
            action=action,
            fair=fair,
            original_ask=live_ask,
            min_edge=min_edge,
        ))


async def _delayed_capture_and_store(
    event_id:     int,
    conn,
    token_id:     str,
    action:       str,
    fair:         float,
    original_ask: float,
    min_edge:     float,
    delay_ms:     int = 400,
) -> None:
    """Background task: delay_ms sonrası shadow book snapshot al ve DB'yi güncelle.

    Ana döngüyü ASLA bekletmez. Hata → structured log, bot crash etmez.
    """
    try:
        await asyncio.sleep(delay_ms / 1000)
        q = await get_shadow_quote(token_id, action, fair, original_ask, min_edge)
        delayed = {
            "delayed_ask_after_fail":             q["ask"] if action == "YES" else None,
            "delayed_no_ask_after_fail":          q["ask"] if action == "NO"  else None,
            "delayed_book_age_ms":                q["book_age_ms"],
            "delayed_fee_adj_after_fail":         q["fee_adj"],
            "delayed_price_delta_cents":          q["price_delta_cents"],
            "delayed_edge_still_passes_min_edge": (1 if q["edge_still_passes"] else 0)
                                                  if q["edge_still_passes"] is not None else None,
            "delayed_would_retry_passed_shadow":  (1 if q["would_retry_passed"] else 0)
                                                  if q["would_retry_passed"] is not None else None,
        }
        await update_entry_air_pocket_delayed(conn, event_id, delayed)
    except Exception as e:
        print(f"[air_pocket_delayed] event_id={event_id} telemetry_error={e}")


async def execute(
    finding:        dict,
    gate_result:    dict,
    risk_result:    dict,
    open_positions: list[dict],
    conn=None,
    council_pass_ts: str | None = None,
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

    # P0 QuoteProvider: AL→ask (book-derived). /price BUY (=bid, TERS) YASAK. council gecikmesi (~5s) komp.
    _q = await get_quote(token_id)
    live_ask    = _q.ask if (_q and _q.ask) else finding["best_ask"]
    # Faz 2b: TAKER_BUY tick-safe limit (ask+buffer → ceil_to_tick), bounds/cap pre-validation.
    # Float YASAK → Decimal. Reject → SESSİZ clamp YOK → network call YAPILMAZ (FATAL_PREVALIDATION).
    from decimal import Decimal
    _limit, _reject = compute_limit_price(
        "TAKER_BUY", Decimal(str(live_ask)), Decimal(str(PRICE_PREMIUM)),
        Decimal(str(TICK_SIZE)),
        price_min=Decimal(str(getattr(config, "PRICE_MIN", "0.01"))),
        price_max=Decimal(str(getattr(config, "PRICE_MAX", "0.99"))),
        max_slippage_cap=Decimal(str(getattr(config, "MAX_SLIPPAGE_CAP", "0.03"))))
    if _reject:
        print(f"[clob] {finding['slug']}: FATAL_PREVALIDATION {_reject} — order GÖNDERİLMEDİ "
              f"(ask={live_ask}+{PRICE_PREMIUM})")
        return None  # network call YOK
    worst_price = float(_limit)  # API uyumu (hesap Decimal'di)

    print(f"[clob] {finding['slug']}: FAK BUY amount=${position_usd:.2f} worst_price={worst_price:.4f} (live={live_ask:.4f}+{PRICE_PREMIUM})")

    order_submit_ts = datetime.now(timezone.utc).isoformat()
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
        error_ts = datetime.now(timezone.utc).isoformat()
        e_str    = str(e)
        print(f"[clob] {finding['slug']}: order hatası — {e_str}")
        if "no orders found to match" in e_str.lower():
            await _handle_fak_no_match(
                finding=finding,
                gate_result=gate_result,
                token_id=token_id,
                council_pass_ts=council_pass_ts,
                order_submit_ts=order_submit_ts,
                error_ts=error_ts,
                live_ask=live_ask,
                worst_price=worst_price,
                e_str=e_str,
                conn=conn,
            )
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
