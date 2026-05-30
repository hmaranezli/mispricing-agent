"""main_loop.py — Scout→Konsey→Execute→Monitor ana döngüsü."""
import asyncio
import sys
import os
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from council.scout import scan_edges
from council.verifier import verify
from council.redteam import redteam as redteam_eval
from council.risk import risk as risk_eval
from council.gate import gate
from execution.executor import execute
from position.manager import check_exit, close_position
from data.hl_candles import current_price
from data.shortterm import fetch_by_slug, parse_market_window
from monitor.notifier import notify_open, notify_close, notify_halt
from monitor.kill_switch import check as kill_switch_check
from db.logger import log_candidate, log_position_open, log_position_close, get_connection

SCAN_INTERVAL_SECS = 30
BANKROLL_USD = 1000.0  # Başlangıç sermayesi — canlıya geçmeden önce ayarla


async def _load_open_positions(conn) -> list[dict]:
    """DB'deki status=open pozisyonları yükler — restart sonrası memory'yi geri doldurur."""
    async with conn.execute(
        "SELECT position_id, ts_open, slug, asset, action, pm_entry_price, "
        "fair_value, ref_price, edge, position_usd, kelly_f, confidence_score, dry_run "
        "FROM positions WHERE status='open'"
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
            "exit_reason":            None,
            "closed_at":              None,
        }
        for r in rows
    ]


def _daily_loss_usd(closed_today: list[dict]) -> float:
    """Bugün kapanan pozisyonlardan gerçekleşen kaybı toplar."""
    today = date.today()
    loss = 0.0
    for pos in closed_today:
        if pos.get("pm_exit_price") is None:
            continue
        closed_date = datetime.fromisoformat(pos["closed_at"]).date()
        if closed_date != today:
            continue
        pnl = (pos["pm_exit_price"] - pos["pm_entry_price"]) / pos["pm_entry_price"] * pos["position_usd"]
        if pnl < 0:
            loss += abs(pnl)
    return loss


async def _run_council(
    finding:        dict,
    bankroll_usd:   float,
    n_open:         int,
    daily_loss_usd: float,
    conn=None,
) -> tuple | None:
    """Finding'i 5 katmandan geçirir. Herhangi biri düşerse None."""
    verification = await verify(finding)
    if not verification["pass"]:
        await log_candidate(conn, finding, passed=False,
                            veto_layer="verifier", veto_reason=verification.get("reason"))
        return None

    rt = await redteam_eval(finding, verification)
    if not rt["pass"]:
        await log_candidate(conn, finding, passed=False,
                            veto_layer="redteam", veto_reason=str(rt.get("vetoes", [])))
        return None

    rk = risk_eval(finding, verification, rt,
                   bankroll_usd=bankroll_usd,
                   open_positions=n_open,
                   daily_loss_usd=daily_loss_usd)
    if not rk["pass"]:
        await log_candidate(conn, finding, passed=False,
                            veto_layer="risk", veto_reason=rk.get("reason"))
        return None

    gate_result = await gate(finding, verification, rt, rk)
    if not gate_result["pass"]:
        await log_candidate(conn, finding, passed=False,
                            veto_layer="gate", veto_reason=gate_result.get("reason"))
        return None

    await log_candidate(conn, finding, passed=True)
    return gate_result, rk


async def _scan_and_execute(
    open_positions: list[dict],
    closed_today:   list[dict],
    bankroll_usd:   float,
    conn=None,
) -> None:
    """Yeni fırsatları tarar, konsey geçenleri açar."""
    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
        return

    findings = await scan_edges()
    daily_loss = _daily_loss_usd(closed_today)
    open_slugs = {p["slug"] for p in open_positions}

    for finding in findings:
        if len(open_positions) >= config.MAX_OPEN_POSITIONS:
            break
        if finding["slug"] in open_slugs:
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


async def _monitor_positions(
    open_positions: list[dict],
    closed_today:   list[dict],
    conn=None,
) -> None:
    """Açık pozisyonları izler, çıkış koşulu varsa kapatır."""
    for pos in list(open_positions):
        try:
            hl_price   = await current_price(pos["asset"])
            market_raw = await fetch_by_slug(pos["slug"])
            window     = parse_market_window(market_raw)

            if window is None:
                closed = close_position(pos, "market_expired")
                await log_position_close(conn, closed)
                open_positions.remove(pos)
                closed_today.append(closed)
                continue

            exit_reason = check_exit(pos, hl_price,
                                     window["best_ask"],
                                     window["seconds_remaining"])
            if exit_reason:
                closed = close_position(pos, exit_reason,
                                        pm_exit_price=window["best_ask"])
                await log_position_close(conn, closed)
                open_positions.remove(pos)
                closed_today.append(closed)

        except Exception as e:
            print(f"[monitor] {pos['slug']} hata: {e}")


async def main() -> None:
    open_positions: list[dict] = []
    closed_today:   list[dict] = []
    print(f"[bot] Başladı — DRY_RUN={config.DRY_RUN}, tarama={SCAN_INTERVAL_SECS}s")
    conn = await get_connection()
    open_positions = await _load_open_positions(conn)
    if open_positions:
        print(f"[bot] DB'den {len(open_positions)} açık pozisyon yüklendi.")
    try:
        while True:
            if kill_switch_check():
                notify_halt("kill_switch")
                print("[bot] Kill switch etkin — sistem durdu.")
                break
            try:
                n_open_before   = len(open_positions)
                n_closed_before = len(closed_today)

                await _monitor_positions(open_positions, closed_today, conn=conn)
                for pos in closed_today[n_closed_before:]:
                    notify_close(pos)

                await _scan_and_execute(open_positions, closed_today, BANKROLL_USD, conn=conn)
                for pos in open_positions[n_open_before:]:
                    notify_open(pos)

            except Exception as e:
                print(f"[bot] Döngü hatası: {e}")
            await asyncio.sleep(SCAN_INTERVAL_SECS)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
