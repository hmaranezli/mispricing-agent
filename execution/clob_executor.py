"""execution/clob_executor.py — Gerçek Polymarket CLOB order placement.

executor.py ile birebir aynı interface:
  async def execute(finding, gate_result, risk_result, open_positions) -> dict | None

Docs: https://docs.polymarket.com/trading/orders/create.md
- BUY market order: MarketOrderArgs(amount=USD, price=worst_price_limit)
- FAK = Fill-And-Kill: fills available depth, cancels remainder → partial fills OK
- PartialCreateOrderOptions(tick_size, neg_risk) zorunlu
"""
import asyncio
import logging
import math
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
from execution.emergency_pause import is_emergency_paused
from execution import emergency_pause
from execution import order_intent
import monitor.notifier as notifier
import aiosqlite
from data.shadow_quote import get_shadow_quote
from db.logger import log_entry_air_pocket, update_entry_air_pocket_delayed
import config

logger = logging.getLogger("execution.clob_executor")

PRICE_PREMIUM = 0.01   # worst-price slippage buffer: live_ask + 1 cent
TICK_SIZE     = "0.01" # binary prediction markets default tick size


# ── Faz 2c Task H4+H5 — accounting/telemetry contract helper'ları ────────────

class _TelemetryDataMissing(Exception):
    """Telemetri (ask_at_decision / slippage) eksik veya geçersiz — None/0/default YASAK."""


def _compute_slippage(side, expected_price, fill_price):
    """Direction-normalized slippage; POZİTİF = ADVERSE. Yön GERÇEK order side'dan (BUY/SELL);
    YES/NO outcome/action KULLANILMAZ. STRICT: side None/YES/NO/UNKNOWN → ValueError;
    expected/fill <=0 veya None → ValueError. Default BUY YOK.
      BUY adverse:  (fill - expected) / expected
      SELL adverse: (expected - fill) / expected
    """
    if side not in ("BUY", "SELL"):
        raise ValueError(f"_compute_slippage geçersiz side: {side!r} (yalnız 'BUY'/'SELL')")
    if expected_price is None or fill_price is None:
        raise ValueError("_compute_slippage fiyat None olamaz")
    if not (math.isfinite(expected_price) and math.isfinite(fill_price)):
        # NaN/Inf tuzağı: float('nan') <= 0 == False → sayısal bariyerden sızmasın.
        raise ValueError(f"_compute_slippage fiyat non-finite: expected={expected_price} fill={fill_price}")
    if expected_price <= 0 or fill_price <= 0:
        raise ValueError(f"_compute_slippage fiyat <=0: expected={expected_price} fill={fill_price}")
    if side == "BUY":
        return (fill_price - expected_price) / expected_price
    return (expected_price - fill_price) / expected_price


def _map_decision_to_position_row(decision, finding, gate_result, risk_result,
                                  order_intent_id, order_id, position_id,
                                  ask_at_decision, slippage_pct):
    """SAF helper — yalnız assignment. H2 muhasebe matematiği TEKRAR EDİLMEZ (shares/spent_usd/
    fill_price decision'dan). Eksik finding/decision alanı → KeyError/TypeError (çağıran
    POSITION_ROW_BUILD_FAILED'e route eder)."""
    return {
        "position_id":             position_id,
        "opened_at":               datetime.now(timezone.utc).isoformat(),
        "asset":                   finding["asset"],
        "action":                  finding["action"],
        "slug":                    finding["slug"],
        "pm_entry_price":          float(decision["fill_price"]),
        "fair_value":              finding["fair_value"],
        "ref_price":               finding["ref_price"],
        "edge":                    finding["edge"],
        "position_usd":            float(decision["spent_usd"]),
        "kelly_f":                 risk_result["kelly_f"],
        "confidence_score":        gate_result["confidence_score"],
        "shares":                  float(decision["shares"]),
        "order_id":                order_id,
        "fill_price":              float(decision["fill_price"]),
        "yes_token_id":            finding.get("yes_token_id"),
        "no_token_id":             finding.get("no_token_id"),
        "entry_hl_price":          finding.get("cur_price"),
        "ask_at_decision":         ask_at_decision,
        "slippage_pct":            slippage_pct,
        "requires_human_approval": False,
        "dry_run":                 False,
        "status":                  "open",
        "order_intent_id":         order_intent_id,
    }


def _recovery_envelope(order_intent_id, reason):
    return {"accounting_persisted": False, "accounting_result": "RECOVERY_REQUIRED",
            "order_intent_id": order_intent_id, "recovery_reason": reason}


async def _recovery_ladder(order_intent_id, reason, slug, order_id=None, size=None):
    """RECOVERY_REQUIRED owner = execute(). transition fail → kill-switch (set_emergency_pause) →
    son-çare CRITICAL (is_emergency_paused fail-closed sonraki execute'u bloklar)."""
    try:
        await order_intent.transition(None, order_intent_id, "RECOVERY_REQUIRED",
                                      reason=reason, server_order_id=order_id, size_matched=size)
        logger.critical("[clob] %s: RECOVERY_REQUIRED (%s) intent=%s — 2c-4 reconcile, yeni emir bloklu",
                        slug, reason, order_intent_id)
        # D6-T3: temiz RECOVERY_REQUIRED de operatöre bildirilmeli — kill-switch TETİKLENMEZ
        # (emergency_pause=0), yani D6-T2 on_trip notify zinciri çalışmaz → ayrı wrapper. CRITICAL
        # log tek başına yeterli değil. Modül-attribute çağrı (test patch'lenebilir); fail-soft
        # (send_telegram try/except'li) — notify hatası recovery yolunu çökertmez.
        try:
            notifier.notify_recovery_required(reason, order_intent_id, slug)
        except Exception as e_notify:
            logger.critical("[clob] %s: RECOVERY_REQUIRED notify FAIL (yutuldu): %s", slug, e_notify)
        return
    except Exception as e1:
        logger.critical("[clob] %s: RECOVERY_REQUIRED write FAIL (%s) — kill-switch deneniyor: %s",
                        slug, reason, e1)
    try:
        await emergency_pause.set_emergency_pause(
            None, reason=f"task_h_recovery_write_failed:{reason}", source="task_h",
            order_intent_id=order_intent_id,
            # D6-T2: fresh 0→1 trip'te operatör Telegram alert. Modül-attribute çağrı → test
            # patch'lenebilir; notify fail-soft (set_emergency_pause callback exception'ı yutar).
            on_trip=lambda r, s, _iid=None: notifier.notify_emergency_pause(r, s))
        logger.critical("[clob] %s: EMERGENCY_PAUSE set — yeni emir KESİN durdu (%s)", slug, reason)
    except Exception as e2:
        logger.critical("[clob] %s: kill-switch write de FAIL (%s) — is_emergency_paused fail-closed "
                        "son kilit: %s", slug, reason, e2)


async def _readback_existing_position_id(order_intent_id):
    """DUPLICATE → aynı order_intent_id için mevcut (position_id, ts_open) readback. Yoksa None."""
    async with aiosqlite.connect(str(order_intent.DB_FILE)) as conn:
        cur = await conn.execute(
            "SELECT position_id, ts_open FROM positions WHERE order_intent_id=?", (order_intent_id,))
        return await cur.fetchone()


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
    # Faz 2c-2: KILL-SWITCH RUNTIME BLOCK. emergency_paused → hiçbir network call YAPILMAZ.
    # Fail-closed: durum okunamazsa is_emergency_paused True döner (güvenli taraf).
    # get_quote / get_client / create_market_order BU SATIRIN ALTINDA — paused'da hiçbiri çalışmaz.
    if await is_emergency_paused():  # canonical DB_FILE → restart-safe, fail-closed
        print(f"[clob] {finding.get('slug')}: EMERGENCY_PAUSE aktif — order GÖNDERİLMEDİ "
              f"(network call yok)")
        return None

    action   = finding["action"]
    token_id = finding["yes_token_id"] if action == "YES" else finding["no_token_id"]

    if not token_id:
        print(f"[clob] {finding['slug']}: token_id yok, order gönderilmedi")
        return None

    # Faz 2c-3 Task A: EARLY-STOP. Aynı token için çözülmemiş intent (SUBMITTED_UNKNOWN/
    # RECOVERY_REQUIRED) varsa hiçbir şey yapma — quote/prevalidation/yeni intent/submit YOK.
    # Timeout sonrası otomatik 2. submit YASAK; durum 2c-4 reconcile'a aittir.
    # Fail-Closed Hardening: kontrol DB-read'de hata atarsa emin değiliz → FAIL-CLOSED dur.
    try:
        _has_unresolved = await order_intent.has_unresolved_intent(None, token_id)
    except Exception as e:
        logger.critical(
            "[clob] %s: unresolved intent check FAILED — FAIL-CLOSED, aborting execution "
            "(order GÖNDERİLMEDİ): %s", finding.get("slug"), e)
        return None
    if _has_unresolved:
        print(f"[clob] {finding['slug']}: UNRESOLVED_INTENT ({token_id}) — execute DURDU "
              f"(quote/order YOK, 2c-4 reconcile bekliyor)")
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

    # Faz 2c-3 Task B: NETWORK ÖNCESİ intent lifecycle. create_intent (INTENT_CREATED) +
    # transition SUBMITTED_UNKNOWN — ikisi de commit edilir. post_order ANCAK bu commit'ten
    # SONRA çağrılır; süreç burada ölürse intent SUBMITTED_UNKNOWN'da kalır (2c-4 reconcile).
    #
    # Faz 2c-3 Task C: create_intent (DB) fail → HARD ABORT — borsaya submit YOK.
    try:
        order_intent_id = await order_intent.create_intent(
            None, token_id, BUY, worst_price, position_usd, slug=finding.get("slug"))
    except Exception as e:
        logger.critical(
            "[clob] %s: create_intent FAIL — HARD ABORT, order GÖNDERİLMEDİ (network call YOK): %s",
            finding.get("slug"), e)
        return None

    # Faz 2c-3 Task D: transition→SUBMITTED_UNKNOWN fail → HARD ABORT — submit YOK.
    # Intent INTENT_CREATED'de kalır = "never submitted" → 2c-4 reconcile blocker.
    try:
        await order_intent.transition(None, order_intent_id, "SUBMITTED_UNKNOWN",
                                      submitted_at=order_submit_ts)
    except Exception as e:
        logger.critical(
            "[clob] %s: transition→SUBMITTED_UNKNOWN FAIL — HARD ABORT, order GÖNDERİLMEDİ; "
            "intent %s INTENT_CREATED kaldı (never submitted, 2c-4 reconcile blocker): %s",
            finding.get("slug"), order_intent_id, e)
        return None

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
            # Faz 2c-3 Task G: borsa 'eşleşecek emir yok' = KESİN no-fill kanıtı (emir gitti,
            # hiç fill olmadı). Araf DEĞİL — intent SUBMITTED_UNKNOWN'dan terminal CANCELLED'a
            # geçer (reason FAK_ZERO_FILL). Position AÇILMAZ. Telemetri ayrıca loglanır.
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
            try:
                await order_intent.transition(
                    None, order_intent_id, "CANCELLED", reason="FAK_ZERO_FILL")
            except Exception as t_err:
                logger.error(
                    "[clob] %s: no-match CANCELLED transition FAILED — intent %s "
                    "SUBMITTED_UNKNOWN kaldı (2c-4 reconcile): %s",
                    finding.get("slug"), order_intent_id, t_err)
        else:
            # Faz 2c-3 Task E: timeout/connection/unknown — "emir GİTMEDİ" VARSAYILMAZ.
            # intent SUBMITTED_UNKNOWN'da KALIR (transition YOK), resubmit YOK → 2c-4 reconcile.
            logger.error(
                "[clob] %s: order submit FAILED (no-fill-proof) — intent SUBMITTED_UNKNOWN "
                "korunuyor, resubmit YOK (2c-4 reconcile): %s", finding.get("slug"), e_str)
        return None

    if not resp:
        return None

    def _get(obj, key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    # Faz 2c H4: classify_fak_fill → kind dispatch (H2 kararı; muhasebe TEKRAR HESAPLANMAZ)
    decision = order_intent.classify_fak_fill(
        status=_get(resp, "status", ""),
        taking_amount=_get(resp, "takingAmount", None),
        making_amount=_get(resp, "makingAmount", None),
        requested_usd=position_usd,
        order_id=_get(resp, "orderID", None),
    )
    kind = decision["kind"]
    order_id = _get(resp, "orderID", "") or ""

    if kind == "BLOCK_UNKNOWN":
        # no_fill_proof: order_id var ama fill yok → SUBMITTED_UNKNOWN'da BIRAK (transition YOK)
        logger.error("[clob] %s: no_fill_proof (order_id var, fill yok) — SUBMITTED_UNKNOWN kalır "
                     "(2c-4 reconcile)", finding.get("slug"))
        return None

    if kind == "TERMINAL_ZERO":
        # zero-fill, order_id yok → terminal CANCELLED (FAK_ZERO_FILL); position YOK
        try:
            await order_intent.transition(None, order_intent_id, "CANCELLED",
                                          reason=decision.get("reason") or "FAK_ZERO_FILL")
        except Exception as e:
            logger.error("[clob] %s: TERMINAL_ZERO CANCELLED transition fail: %s",
                         finding.get("slug"), e)
        return None

    if kind == "RECOVERY":
        # cost-missing / invariant-breach → recovery (confirm_fill_atomic ASLA çağrılmaz)
        reason = decision.get("reason") or "FAK_RECOVERY"
        _size = float(decision["shares"]) if decision.get("shares") is not None else None
        await _recovery_ladder(order_intent_id, reason, finding.get("slug"),
                               order_id=order_id, size=_size)
        return _recovery_envelope(order_intent_id, reason)

    # OPEN_FILLED / OPEN_PARTIAL → atomik confirm.
    # position_id TEK kez üret — confirm_fill_atomic'e ve return position'a AYNI değer gider.
    position_id = str(uuid4())
    try:
        # Atomic telemetry (confirm ÖNCESİ position_row'a): ask_at_decision + direction-normalized
        # slippage. None/0/default YASAK → TELEMETRY_DATA_MISSING.
        ask_at_decision = finding.get("best_ask")
        # NaN/Inf tuzağı: float('nan') <= 0 == False → None/<=0 yetmez, isfinite ŞART.
        if (ask_at_decision is None or not math.isfinite(ask_at_decision)
                or ask_at_decision <= 0):
            raise _TelemetryDataMissing(f"ask_at_decision geçersiz: {ask_at_decision!r}")
        # Yön GERÇEK order side (entry = BUY); YES/NO action slippage yönü için KULLANILMAZ.
        slippage_pct = _compute_slippage(BUY, float(ask_at_decision), float(decision["fill_price"]))
        if not math.isfinite(slippage_pct):
            raise _TelemetryDataMissing(f"slippage_pct non-finite: {slippage_pct!r}")
        position_row = _map_decision_to_position_row(
            decision, finding, gate_result, risk_result, order_intent_id, order_id,
            position_id, float(ask_at_decision), slippage_pct)
    except _TelemetryDataMissing as e:
        logger.error("[clob] %s: telemetry eksik (%s) → TELEMETRY_DATA_MISSING recovery",
                     finding.get("slug"), e)
        await _recovery_ladder(order_intent_id, "TELEMETRY_DATA_MISSING", finding.get("slug"),
                               order_id=order_id)
        return _recovery_envelope(order_intent_id, "TELEMETRY_DATA_MISSING")
    except ValueError as e:
        # _compute_slippage strict validation (side/price invalid) → telemetri geçersiz
        logger.error("[clob] %s: slippage/telemetry invalid (%s) → TELEMETRY_DATA_MISSING",
                     finding.get("slug"), e)
        await _recovery_ladder(order_intent_id, "TELEMETRY_DATA_MISSING", finding.get("slug"),
                               order_id=order_id)
        return _recovery_envelope(order_intent_id, "TELEMETRY_DATA_MISSING")
    except (KeyError, TypeError) as e:
        # _map_decision_to_position_row alan eksikliği → build fail (CONFIRM_TX_FAILED'den AYRI)
        logger.critical("[clob] %s: position_row build FAIL (%s) → POSITION_ROW_BUILD_FAILED",
                        finding.get("slug"), e)
        await _recovery_ladder(order_intent_id, "POSITION_ROW_BUILD_FAILED", finding.get("slug"),
                               order_id=order_id)
        return _recovery_envelope(order_intent_id, "POSITION_ROW_BUILD_FAILED")

    terminal_state = decision["state"]   # FILLED | PARTIAL_FILLED
    try:
        result = await order_intent.confirm_fill_atomic(
            None, order_intent_id, position_row, terminal_state)
    except Exception as e:
        logger.critical("[clob] %s: confirm_fill_atomic FAIL (%s) → CONFIRM_TX_FAILED recovery",
                        finding.get("slug"), e)
        await _recovery_ladder(order_intent_id, "CONFIRM_TX_FAILED", finding.get("slug"),
                               order_id=order_id, size=position_row.get("shares"))
        return _recovery_envelope(order_intent_id, "CONFIRM_TX_FAILED")

    if result == "DUPLICATE":
        existing = await _readback_existing_position_id(order_intent_id)
        if existing is None:
            logger.critical("[clob] %s: DUPLICATE ama readback BOŞ → DB_INCONSISTENCY recovery",
                            finding.get("slug"))
            await _recovery_ladder(order_intent_id, "DB_INCONSISTENCY", finding.get("slug"),
                                   order_id=order_id)
            return _recovery_envelope(order_intent_id, "DB_INCONSISTENCY")
        logger.warning("[clob] %s: confirm DUPLICATE — order_intent_id=%s existing_position_id=%s "
                       "ts=%s (candidate uuid DÖNDÜRÜLMEZ)", finding.get("slug"), order_intent_id,
                       existing[0], existing[1])
        return {"accounting_persisted": True, "accounting_result": "DUPLICATE",
                "order_intent_id": order_intent_id, "existing_position_id": existing[0],
                "existing_ts_open_or_created_at": existing[1]}

    # OPENED — envelope (accounting metadata position objesine SIZMAZ)
    print(f"[clob] {finding['slug']}: OPENED {position_row['shares']} @ {position_row['fill_price']} "
          f"(${position_row['position_usd']}) state={terminal_state}")
    return {"accounting_persisted": True, "accounting_result": "OPENED", "position": position_row}
