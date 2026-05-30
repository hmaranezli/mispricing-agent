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

SCAN_INTERVAL_SECS = 30
BANKROLL_USD = 1000.0  # Başlangıç sermayesi — canlıya geçmeden önce ayarla


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
) -> tuple | None:
    """Finding'i 5 katmandan geçirir. Herhangi biri düşerse None."""
    verification = await verify(finding)
    if not verification["pass"]:
        return None

    rt = await redteam_eval(finding, verification)
    if not rt["pass"]:
        return None

    rk = risk_eval(finding, verification, rt,
                   bankroll_usd=bankroll_usd,
                   open_positions=n_open,
                   daily_loss_usd=daily_loss_usd)
    if not rk["pass"]:
        return None

    gate_result = await gate(finding, verification, rt, rk)
    if not gate_result["pass"]:
        return None

    return gate_result, rk


async def _scan_and_execute(
    open_positions: list[dict],
    closed_today:   list[dict],
    bankroll_usd:   float,
) -> None:
    """Placeholder — Task 2'de implemente edilecek."""
    pass


async def _monitor_positions(
    open_positions: list[dict],
    closed_today:   list[dict],
) -> None:
    """Placeholder — Task 3'te implemente edilecek."""
    pass


async def main() -> None:
    open_positions: list[dict] = []
    closed_today:   list[dict] = []
    print(f"[bot] Başladı — DRY_RUN={config.DRY_RUN}, tarama={SCAN_INTERVAL_SECS}s")
    while True:
        try:
            await _monitor_positions(open_positions, closed_today)
            await _scan_and_execute(open_positions, closed_today, BANKROLL_USD)
        except Exception as e:
            print(f"[bot] Döngü hatası: {e}")
        await asyncio.sleep(SCAN_INTERVAL_SECS)


if __name__ == "__main__":
    asyncio.run(main())
