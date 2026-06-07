"""main_loop.py — Scout→Konsey→Execute→Monitor ana döngüsü."""
import asyncio
import sys
import os
import time
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from data import ws_prices
from council.scout import scan_edges
from council.verifier import verify
from council.redteam import redteam as redteam_eval
from council.risk import risk as risk_eval
from council.gate import gate
from execution.executor       import execute as _dry_execute
from execution.clob_executor  import execute as _clob_execute
from execution.position_store import sell_position
from execution.balance        import get_effective_bankroll
from execution.reconcile      import startup_reconcile
from execution.ghost          import detect_ghosts
from position.manager import check_exit, close_position
from data.hl_candles import current_price
from data.shortterm import fetch_by_slug, fetch_resolved, parse_market_window
from data.clob_price import get_clob_price
from monitor.notifier import notify_open, notify_close, notify_halt, notify_restart, notify_soft_stop, notify_hard_stop, notify_resolved_late, send_telegram
from monitor.kill_switch import check as kill_switch_check
from monitor.telegram_commands import poll_commands
from monitor.state import is_paused
from monitor import circuit_breaker
from monitor import positions_cache
from db.logger import log_candidate, log_position_open, log_position_close, load_closed_today, get_connection, patch_position_resolution, log_partial_fill_update

SCAN_INTERVAL_SECS = 7
BANKROLL_CONFIG = float(os.getenv("BANKROLL_USD", "1000.0"))


async def execute(finding, gate_result, risk_result, open_positions):
    """DRY_RUN flag'ine göre executor seç. Runtime'da değerlendirilir."""
    if config.DRY_RUN:
        return await _dry_execute(finding, gate_result, risk_result, open_positions)
    return await _clob_execute(finding, gate_result, risk_result, open_positions)


async def _load_open_positions(conn) -> list[dict]:
    """DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri doldurur."""
    async with conn.execute(
        "SELECT position_id, ts_open, slug, asset, action, pm_entry_price, "
        "fair_value, ref_price, edge, position_usd, kelly_f, confidence_score, dry_run, "
        "shares, order_id, yes_token_id, no_token_id, seq_no, entry_hl_price, "
        "partial_fill_count, partial_fill_shares, partial_realized_usdc "
        "FROM positions WHERE status='open' AND dry_run=?",
        (1 if config.DRY_RUN else 0,),
    ) as cur:
        rows = await cur.fetchall()
    return [
        {
            "position_id":            r[0],
            "opened_at":              r[1],
            "slug":                   r[2],
            "asset":                  r[3],
            "action":                 r[4],
            "pm_entry_price":         r[5],
            "fair_value":             r[6],
            "ref_price":              r[7],
            "edge":                   r[8],
            "position_usd":           r[9],
            "kelly_f":                r[10],
            "confidence_score":       r[11],
            "status":                 "open",
            "requires_human_approval": (r[9] or 0) > config.HUMAN_APPROVAL_USD,
            "dry_run":                bool(r[12]),
            "shares":                 r[13],
            "order_id":               r[14],
            "yes_token_id":           r[15],
            "no_token_id":            r[16],
            "exit_reason":            None,
            "closed_at":              None,
            "seq_no":                 r[17],
            "entry_hl_price":         r[18],
            "partial_fill_count":     r[19] or 0,
            "partial_fill_shares":    r[20],
            "partial_realized_usdc":  r[21],
        }
        for r in rows
    ]




async def _run_council(
    finding:        dict,
    bankroll_usd:   float,
    n_open:         int,
    daily_loss_usd: float,
    conn=None,
) -> tuple | None:
    """Finding'i 5 katmandan geçirir. Herhangi biri düşerse None."""
    slug = finding.get("slug", "?")

    verification = await verify(finding)
    if not verification["pass"]:
        reason = verification.get("reason", "?")
        print(f"[council] {slug} VETO verifier: {reason}")
        await log_candidate(conn, finding, passed=False,
                            veto_layer="verifier", veto_reason=reason)
        return None

    # Taze fiyatları finding'e yaz — execute() stale scout fiyatı değil fresh_ask kullansın
    if verification.get("fresh_best_ask", 0) > 0:
        finding["best_ask"] = verification["fresh_best_ask"]
    if verification.get("fresh_best_bid", 0) > 0:
        finding["best_bid"] = verification["fresh_best_bid"]

    rt = await redteam_eval(finding, verification)
    if not rt["pass"]:
        vetoes = rt.get("vetoes", [])
        print(f"[council] {slug} VETO redteam: {vetoes} | fee_adj={rt.get('fee_adj_edge', '?'):.3f}")
        await log_candidate(conn, finding, passed=False,
                            veto_layer="redteam", veto_reason=str(vetoes))
        return None

    rk = risk_eval(finding, verification, rt,
                   bankroll_usd=bankroll_usd,
                   open_positions=n_open,
                   daily_loss_usd=daily_loss_usd)
    if not rk["pass"]:
        reason = rk.get("reason", "?")
        print(f"[council] {slug} VETO risk: {reason}")
        await log_candidate(conn, finding, passed=False,
                            veto_layer="risk", veto_reason=reason)
        return None

    gate_result = await gate(finding, verification, rt, rk)
    if not gate_result["pass"]:
        reason = gate_result.get("reason", "?")
        print(f"[council] {slug} VETO gate: {reason}")
        await log_candidate(conn, finding, passed=False,
                            veto_layer="gate", veto_reason=reason)
        return None

    print(f"[council] {slug} GEÇTİ → execute")
    await log_candidate(conn, finding, passed=True)
    return gate_result, rk


async def _scan_and_execute(
    open_positions: list[dict],
    closed_today:   list[dict],
    bankroll_usd:   float,
    conn=None,
    failed_slugs: set | None = None,
) -> None:
    """Yeni fırsatları tarar, konsey geçenleri açar."""
    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
        return

    findings = await scan_edges()
    daily_loss = 0.0
    open_slugs  = {p["slug"] for p in open_positions}
    _failed     = failed_slugs if failed_slugs is not None else set()

    from datetime import datetime, timezone as _tz
    _ts = datetime.now(_tz.utc).strftime("%H:%M:%S")
    if findings:
        for _f in findings:
            _skip = "failed" if _f["slug"] in _failed else ("open" if _f["slug"] in open_slugs else "")
            print(f"[scan {_ts}] {_f['slug']}: {_f['action']} fair={_f['fair_value']:.3f} ask={_f['best_ask']:.3f} edge={_f['edge']:.3f} secs={_f['seconds_remaining']:.0f}" + (f" SKIP:{_skip}" if _skip else ""))
    else:
        print(f"[scan {_ts}] edge yok")

    for finding in findings:
        if len(open_positions) >= config.MAX_OPEN_POSITIONS:
            break
        slug = finding["slug"]
        if slug in open_slugs:
            continue
        if slug in _failed:
            continue

        result = await _run_council(finding,
                                    bankroll_usd=bankroll_usd,
                                    n_open=len(open_positions),
                                    daily_loss_usd=daily_loss,
                                    conn=conn)
        if result is None:
            continue

        gate_result, risk_result = result
        position = await execute(finding, gate_result, risk_result, open_positions)
        if position:
            await log_position_open(conn, position)
            open_positions.append(position)
            open_slugs.add(slug)
            ws_prices.subscribe([
                t for t in (position.get("yes_token_id"), position.get("no_token_id")) if t
            ])
        else:
            pass  # FAK kill — capital riske girmedi, bir sonraki taramada yeniden dene


async def _handle_ws_resolved(
    event: dict,
    open_positions: list[dict],
    closed_today:   list[dict],
    conn=None,
    failed_slugs: set | None = None,
) -> None:
    """WS market_resolved event'ına göre açık pozisyonu anında kapat."""
    winning_outcome = event.get("winning_outcome")   # "Yes" veya "No"
    assets_ids      = set(event.get("assets_ids", []))
    if not assets_ids:
        return

    for pos in list(open_positions):
        if pos.get("yes_token_id") not in assets_ids \
           and pos.get("no_token_id") not in assets_ids:
            continue
        if pos["action"] == "YES":
            pm_exit = 1.0 if winning_outcome == "Yes" else 0.0
        else:  # NO
            pm_exit = 1.0 if winning_outcome == "No" else 0.0
        try:
            hl_price = await current_price(pos["asset"])
        except Exception:
            hl_price = None
        closed = close_position(pos, "market_resolved", pm_exit_price=pm_exit,
                                exit_hl_price=hl_price)
        await log_position_close(conn, closed)
        open_positions.remove(pos)
        ws_prices.unsubscribe([t for t in (pos.get("yes_token_id"), pos.get("no_token_id")) if t])
        closed_today.append(closed)
        if failed_slugs is not None:
            failed_slugs.add(pos["slug"])
        notify_close(closed)
        print(f"[ws] {pos['slug']} resolved — {winning_outcome} wins → pm_exit={pm_exit}")


async def _heal_pending_resolutions(
    conn,
    closed_today: list[dict],
    limit: int = 3,
) -> None:
    """market_expired + pm_exit_price=None kayıtları için resolution retry eder."""
    if conn is None:
        return
    async with conn.execute(
        """SELECT position_id, slug, asset, action, pm_entry_price, position_usd, seq_no,
                  entry_hl_price
           FROM positions
           WHERE status='closed' AND pm_exit_price IS NULL
           LIMIT ?""",
        (limit,),
    ) as cur:
        rows = await cur.fetchall()

    for position_id, slug, asset, action, pm_entry_price, position_usd, seq_no, entry_hl_price in rows:
        try:
            resolution = await fetch_resolved(slug)
            if resolution is None:
                continue
            pm_exit      = resolution["yes_exit"] if action == "YES" else resolution["no_exit"]
            if not pm_entry_price:
                print(f"[heal] {slug} pm_entry_price=0, skipping")
                continue
            realized_pnl = (pm_exit - pm_entry_price) / pm_entry_price * position_usd
            try:
                exit_hl_price = await current_price(asset)
            except Exception:
                exit_hl_price = None
            await patch_position_resolution(conn, position_id, pm_exit, realized_pnl,
                                            exit_hl_price=exit_hl_price)
            for pos in closed_today:
                if pos.get("position_id") == position_id:
                    pos["pm_exit_price"] = pm_exit
                    pos["realized_pnl"]  = realized_pnl
                    pos["exit_reason"]   = "market_resolved_late"
                    break
            notify_resolved_late({
                "seq_no":          seq_no,
                "asset":           asset,
                "action":          action,
                "pm_entry_price":  pm_entry_price,
                "pm_exit_price":   pm_exit,
                "position_usd":    position_usd,
                "entry_hl_price":  entry_hl_price,
                "exit_hl_price":   exit_hl_price,
            })
        except Exception as e:
            print(f"[heal] {slug} hata: {e}")


_last_rest_ts: float = 0.0  # modül-seviye heartbeat zamanlayıcı


def _apply_partial_fill(pos: dict, pm_exit: float, making_shares: float) -> bool:
    """Kısmi fill kontrolü + pos güncelleme.

    Returns:
        True  → kısmi fill oldu, pos güncellendi (_closing=False, shares azaltıldı)
        False → tam fill (>=%98), pos değişmedi
    """
    old_shares = pos.get("shares") or 0.0
    if old_shares <= 0 or making_shares >= old_shares * 0.98:
        return False
    pos["shares"] = round(old_shares - making_shares, 6)
    pos["_closing"] = False
    pos["partial_fill_count"] = pos.get("partial_fill_count", 0) + 1
    pos["partial_fill_shares"] = round(
        pos.get("partial_fill_shares", 0.0) + making_shares, 6
    )
    pos["partial_realized_usdc"] = round(
        pos.get("partial_realized_usdc", 0.0) + pm_exit * making_shares, 6
    )
    return True


async def _do_flatten(open_positions: list, closed_today: list, conn=None) -> None:
    """Panic flatten: tüm açık pozisyonları FAK SELL ile kapatmaya çalışır."""
    import monitor.state as _st
    send_telegram(f"[FLATTEN] {len(open_positions)} pozisyon kapatılıyor...")
    for pos in list(open_positions):
        if pos.get("_closing"):
            continue
        pos["_closing"] = True
        sell_result = await sell_position(pos)
        if sell_result is not None:
            pm_exit, making_shares = sell_result
            old_shares = pos.get("shares") or 0.0
            if _apply_partial_fill(pos, pm_exit, making_shares):
                print(f"[flatten] {pos['slug']} kısmi fill {making_shares:.4f}/{old_shares:.4f} → {pos['shares']:.4f} kalan")
            else:
                closed_dict = close_position(
                    pos, "panic_flatten",
                    pm_exit_price=pm_exit,
                    exit_hl_price=pos.get("_cached_hl_price"),
                )
                open_positions.remove(pos)
                ws_prices.unsubscribe([t for t in (pos.get("yes_token_id"), pos.get("no_token_id")) if t])
                closed_today.append(closed_dict)
                notify_close(closed_dict)
                try:
                    await log_position_close(conn, closed_dict)
                except Exception as e:
                    print(f"[flatten] {pos['slug']} log hatası: {e}")
        else:
            pos["_closing"] = False
            print(f"[flatten] {pos['slug']} SELL başarısız — açık kalıyor, monitor devam")
    remaining = len(open_positions)
    msg = (
        f"[FLATTEN] {remaining} pozisyon hâlâ açık — izlemeye devam"
        if remaining else
        "[FLATTEN] Tüm pozisyonlar kapatıldı. Bot PAUSE modunda."
    )
    send_telegram(msg)


async def _monitor_positions(
    open_positions: list[dict],
    closed_today:   list[dict],
    conn=None,
    failed_slugs: set | None = None,
) -> bool:
    """Açık pozisyonları izler. WS event gelince hızlı path, 7s timeout → REST heartbeat.

    Döner:
      True  → WS hızlı path (scan henüz erken)
      False → REST heartbeat çalıştı (scan zamanı) — timeout VEYA heartbeat vadesi dolmuş

    Heartbeat starvation koruması: WS sürekli aksa bile her SCAN_INTERVAL_SECS'te bir
    REST path zorunlu çalışır (HL cache + PM prices yenilenir, scan tetiklenir).

    failed_slugs: kapanan pozisyon slug'ları buraya eklenir → aynı pencere yeniden açılmaz.
    """
    global _last_rest_ts
    price_event = ws_prices.get_price_event()
    now = time.time()
    heartbeat_due = (now - _last_rest_ts) >= float(SCAN_INTERVAL_SECS)

    try:
        await asyncio.wait_for(price_event.wait(), timeout=float(SCAN_INTERVAL_SECS))
        price_event.clear()
        ws_triggered = not heartbeat_due  # WS event geldi ama heartbeat vadesi dolduysa REST'e düş
    except asyncio.TimeoutError:
        ws_triggered = False

    if not ws_triggered:
        _last_rest_ts = time.time()  # wait sonrası gerçek zaman — timeout 7s beklerse now stale olurdu

    for pos in list(open_positions):
        if pos.get("_closing"):
            continue
        try:
            if ws_triggered:
                # ── WS hızlı path: REST yok, cached context ───────────────
                hl_price = pos.get("_cached_hl_price")
                if hl_price is None:
                    continue  # heartbeat doldurana kadar skip — yanlış hl_price=0 ile karar verme
                seconds_remaining = pos.get("_cached_seconds_remaining", 900)
                yes_tid           = pos.get("yes_token_id", "")
                if pos["action"] == "YES":
                    pm_yes_price = ws_prices.get_bid(yes_tid)
                    _price_source, _data_quality = "ws_bid", "exact"
                else:
                    pm_yes_price = ws_prices.get_ask(yes_tid)
                    _price_source, _data_quality = "ws_ask_complement", "estimated"
                if pm_yes_price is None:
                    continue
            else:
                # ── REST heartbeat: tam refresh, cache yaz ─────────────────
                hl_price   = await current_price(pos["asset"])
                pos["_cached_hl_price"] = hl_price
                market_raw = await fetch_by_slug(pos["slug"])
                window     = parse_market_window(market_raw)

                if window is None:
                    resolution = await fetch_resolved(pos["slug"])
                    if resolution:
                        pm_exit = (resolution["yes_exit"] if pos["action"] == "YES"
                                   else resolution["no_exit"])
                        closed = close_position(pos, "market_resolved",
                                                pm_exit_price=pm_exit, exit_hl_price=hl_price)
                        await log_position_close(conn, closed)
                        open_positions.remove(pos)
                        ws_prices.unsubscribe([t for t in (pos.get("yes_token_id"), pos.get("no_token_id")) if t])
                        closed_today.append(closed)
                    # fetch_resolved da None → geçici API hatası, bu döngüde atla
                    continue

                pos["_cached_seconds_remaining"] = window["seconds_remaining"]
                seconds_remaining = window["seconds_remaining"]
                yes_tid = pos.get("yes_token_id", "")
                if pos["action"] == "YES":
                    pm_yes_price = ws_prices.get_bid(yes_tid)
                    if pm_yes_price is None:
                        pm_yes_price = await get_clob_price(yes_tid, "SELL")
                        _price_source, _data_quality = "clob_rest_bid", "exact"
                    else:
                        _price_source, _data_quality = "ws_bid", "exact"
                else:
                    pm_yes_price = ws_prices.get_ask(yes_tid)
                    if pm_yes_price is None:
                        pm_yes_price = await get_clob_price(yes_tid, "BUY")
                        _price_source, _data_quality = "clob_rest_ask_complement", "estimated"
                    else:
                        _price_source, _data_quality = "ws_ask_complement", "estimated"
                if pm_yes_price is None:
                    continue  # fiyat yok → bu döngüyü atla, bir sonrakinde tekrar dene

            exit_reason = check_exit(pos, hl_price, pm_yes_price, seconds_remaining)
            # Gerçek fiyat kaynağını yaz — check_exit "rest" hardcode eder, biz overwrite ederiz
            pos["price_source"]     = _price_source
            pos["mae_data_quality"] = _data_quality

            if exit_reason:
                if config.DRY_RUN:
                    if pos["action"] == "NO":
                        _no_bid = ws_prices.get_bid(pos.get("no_token_id", ""))
                        if ws_triggered:
                            pm_exit = (_no_bid if _no_bid is not None
                                       else round(1 - pm_yes_price, 4))
                        else:
                            pm_exit = (_no_bid if _no_bid is not None
                                       else round(1 - window["best_ask"], 4))
                    else:
                        _yes_bid = ws_prices.get_bid(pos.get("yes_token_id", ""))
                        pm_exit = (_yes_bid if _yes_bid is not None
                                   else (pm_yes_price if ws_triggered else window["best_bid"]))
                else:
                    # LIVE: _closing=True → duplicate sell koruması, sonra gerçek SELL order
                    pos["_closing"] = True
                    if pos["action"] == "NO":
                        _no_bid = ws_prices.get_bid(pos.get("no_token_id", ""))
                        pos["current_bid"] = (_no_bid if _no_bid is not None
                                              else round(1 - pm_yes_price, 4)
                                              if ws_triggered
                                              else round(1 - window["best_ask"], 4))
                    else:
                        _yes_bid = ws_prices.get_bid(pos.get("yes_token_id", ""))
                        pos["current_bid"] = (_yes_bid if _yes_bid is not None
                                              else (pm_yes_price if ws_triggered
                                                    else window["best_bid"]))
                    sell_result = await sell_position(pos)
                    if sell_result is None:
                        # FAK kill veya hata — _closing resetle, pozisyonu açık bırak
                        pos["_closing"] = False
                        print(f"[monitor] {pos['slug']} SELL başarısız — pozisyon açık kalıyor")
                        continue
                    pm_exit, making_shares = sell_result
                    old_shares = pos.get("shares") or 0.0
                    if _apply_partial_fill(pos, pm_exit, making_shares):
                        print(f"[monitor] {pos['slug']} kısmi fill {making_shares:.4f}/{old_shares:.4f} → {pos['shares']:.4f} kalan")
                        try:
                            await log_partial_fill_update(conn, pos)
                        except Exception as _e:
                            print(f"[monitor] {pos['slug']} partial DB update hatası: {_e}")
                        continue
                closed = close_position(pos, exit_reason, pm_exit_price=pm_exit,
                                        exit_hl_price=hl_price)
                # SELL borsa tarafında başarılı → pozisyonu HEMEN kaldır.
                # Log hatası double-sell'e yol açmamalı; reconcile kurtarır.
                open_positions.remove(pos)
                ws_prices.unsubscribe([t for t in (pos.get("yes_token_id"), pos.get("no_token_id")) if t])
                closed_today.append(closed)
                if failed_slugs is not None and exit_reason == "stop_loss_hit":
                    failed_slugs.add(pos["slug"])
                try:
                    await log_position_close(conn, closed)
                except Exception as log_err:
                    print(f"[monitor] {pos['slug']} log hatası: {log_err} — pozisyon kapatıldı, DB yazılamadı")

        except Exception as e:
            print(f"[monitor] {pos['slug']} hata: {e}")

    return ws_triggered


async def main() -> None:
    open_positions: list[dict] = []
    closed_today:   list[dict] = []
    failed_slugs:   set[str]   = set()
    print(f"[bot] Başladı — DRY_RUN={config.DRY_RUN}, tarama={SCAN_INTERVAL_SECS}s")
    asyncio.create_task(poll_commands())
    conn = await get_connection()
    open_positions = await _load_open_positions(conn)
    closed_today   = await load_closed_today(conn)
    if open_positions:
        print(f"[bot] DB'den {len(open_positions)} açık pozisyon yüklendi.")
        rec = await startup_reconcile(open_positions, conn)
        if rec["closed"]:
            print(f"[bot] Reconcile: {rec['closed']} pozisyon kapatıldı.")
    if closed_today:
        print(f"[bot] Bugün {len(closed_today)} kapanan pozisyon geri yüklendi.")

    # Hayalet pozisyon kontrolü: portföyde olup DB'de izlenmeyen shareler (kill-mid-exec artığı)
    if not config.DRY_RUN:
        try:
            ghosts = await detect_ghosts(open_positions)
            if ghosts:
                redeemable = sum(float(g.get("currentValue") or 0)
                                 for g in ghosts if g.get("redeemable"))
                print(f"[ghost] {len(ghosts)} hayalet pozisyon portföyde (DB'de yok). "
                      f"Redeemable ≈ ${redeemable:.2f}")
                for g in ghosts:
                    print(f"[ghost]   {g.get('slug','?')} {g.get('outcome','?')} "
                          f"size={g.get('size')} value=${float(g.get('currentValue') or 0):.2f} "
                          f"redeemable={g.get('redeemable')}")
        except Exception as e:
            print(f"[ghost] kontrol hatası: {e}")

    initial_tids = [
        tid
        for pos in open_positions
        for tid in (pos.get("yes_token_id"), pos.get("no_token_id"))
        if tid
    ]
    asyncio.create_task(ws_prices.run(initial_tids))

    starting_bankroll = await get_effective_bankroll(BANKROLL_CONFIG)
    circuit_breaker.BUST_PROTECTION_PCT = config.BUST_PROTECTION_PCT
    circuit_breaker.STREAK_WARN_COUNT   = config.STREAK_WARN_COUNT
    notify_restart(dry_run=config.DRY_RUN, bankroll=starting_bankroll)

    try:
        while True:
            if kill_switch_check():
                notify_halt("kill_switch")
                print("[bot] Kill switch etkin — sistem durdu.")
                break

            import monitor.state as _st

            # FLATTEN: açık pozisyonları sat → monitor döngüsü öncesinde
            if _st.FLATTEN_REQUESTED:
                _st.clear_flatten()
                await _do_flatten(open_positions, closed_today, conn=conn)

            try:
                n_closed_before = len(closed_today)

                # Pause olsa bile açık pozisyonlar her zaman izlenir (stop/exit koruması)
                ws_triggered = await _monitor_positions(
                    open_positions, closed_today, conn=conn, failed_slugs=failed_slugs
                )
                # WS üzerinden gelen anlık resolution olaylarını işle
                if ws_prices._resolved_queue:
                    while not ws_prices._resolved_queue.empty():
                        ev = ws_prices._resolved_queue.get_nowait()
                        await _handle_ws_resolved(ev, open_positions, closed_today, conn=conn,
                                                  failed_slugs=failed_slugs)
                for pos in closed_today[n_closed_before:]:
                    notify_close(pos)
                    pnl = pos.get("realized_pnl") or 0.0
                    effective_bk = await get_effective_bankroll(BANKROLL_CONFIG)
                    cb_result = circuit_breaker.on_trade_closed(
                        pnl=pnl,
                        current_bankroll=effective_bk,
                        starting_bankroll=starting_bankroll,
                    )
                    if cb_result == 'hard_stop':
                        notify_hard_stop(effective_bk, starting_bankroll)
                        print(f"[bot] HARD STOP: bakiye ${effective_bk:.2f} / başlangıç ${starting_bankroll:.2f}")
                    elif cb_result == 'soft_stop':
                        notify_soft_stop(config.STREAK_WARN_COUNT, effective_bk)
                        print(f"[bot] SOFT STOP: {config.STREAK_WARN_COUNT} arka arkaya kayıp")

                # Pause modunda scan/heal atlanır — sadece monitor çalışır
                if is_paused():
                    reason = "hard_stop" if _st.HARD_PAUSED else "soft_stop/pause"
                    print(f"[bot] {reason} — yeni islem yok, pozisyon monitor aktif")
                    continue

                if not ws_triggered:
                    # REST heartbeat: scan + heal + cache yenile
                    n_open_before = len(open_positions)
                    effective_bankroll = await get_effective_bankroll(BANKROLL_CONFIG)
                    await _scan_and_execute(open_positions, closed_today, effective_bankroll,
                                            conn=conn, failed_slugs=failed_slugs)
                    for pos in open_positions[n_open_before:]:
                        notify_open(pos)
                    await _heal_pending_resolutions(conn, closed_today)
                    positions_cache.set_open_positions(open_positions)

            except Exception as e:
                print(f"[bot] Döngü hatası: {e}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
