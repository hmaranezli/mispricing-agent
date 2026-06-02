"""execution/reconcile.py — LIVE startup pozisyon mutabakatı."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from data.shortterm import fetch_by_slug, fetch_resolved, parse_market_window
from position.manager import close_position
from db.logger import log_position_close


async def startup_reconcile(open_positions: list, conn) -> dict:
    """
    LIVE startup: DB'deki açık pozisyonları Polymarket ile karşılaştırır.
    DRY_RUN=True → hiçbir şey yapmaz.

    Döner: {"checked": N, "closed": N, "warnings": [...]}
    """
    if config.DRY_RUN:
        return {"checked": 0, "closed": 0, "warnings": []}

    checked  = 0
    closed   = 0
    warnings = []

    for pos in list(open_positions):
        slug = pos["slug"]
        checked += 1
        try:
            market = await fetch_by_slug(slug)
            window = parse_market_window(market) if market else None

            if window is None:
                resolution = await fetch_resolved(slug)
                if resolution:
                    pm_exit = resolution["yes_exit"] if pos["action"] == "YES" else resolution["no_exit"]
                    reason  = "startup_reconcile_resolved"
                else:
                    pm_exit = None
                    reason  = "startup_reconcile_expired"
                    warnings.append(f"{slug}: kapandı ama çözüm fiyatı yok")

                closed_pos = close_position(pos, reason, pm_exit_price=pm_exit)
                if conn:
                    await log_position_close(conn, closed_pos)
                open_positions.remove(pos)
                closed += 1
                print(f"[reconcile] {slug}: kapatıldı ({reason}, exit={pm_exit})")

        except Exception as e:
            warnings.append(f"{slug}: kontrol hatası — {e}")
            print(f"[reconcile] {slug}: hata — {e}")

    if checked > 0:
        print(f"[reconcile] {checked} kontrol, {closed} kapatıldı, {len(warnings)} uyarı")

    return {"checked": checked, "closed": closed, "warnings": warnings}
