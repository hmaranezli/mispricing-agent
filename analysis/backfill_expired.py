#!/usr/bin/env python3
"""analysis/backfill_expired.py — market_expired P&L retroaktif heal.

Kullanım:
    python analysis/backfill_expired.py

Mevcut DB'deki pm_exit_price=NULL olan kapanmış pozisyonlar için
fetch_resolved çağırır; veri gelirse DB'ye yazar ve exit_reason'ı
'market_resolved_late' olarak günceller.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.logger import get_connection, patch_position_resolution
from data.shortterm import fetch_resolved


async def backfill() -> None:
    conn = None
    try:
        conn = await get_connection()
        async with conn.execute(
            """SELECT position_id, slug, action, pm_entry_price, position_usd
               FROM positions
               WHERE status='closed' AND pm_exit_price IS NULL"""
        ) as cur:
            rows = await cur.fetchall()

        total = len(rows)
        print(f"{total} market_expired kayıt bulundu.\n")

        recovered = 0
        for position_id, slug, action, pm_entry_price, position_usd in rows:
            try:
                resolution = await fetch_resolved(slug)
                if resolution is None:
                    print(f"  — {slug}: hâlâ resolve yok (iptal market?)")
                    continue
                if not pm_entry_price:
                    print(f"  — {slug}: pm_entry_price=0, skipping")
                    continue
                pm_exit = resolution["yes_exit"] if action == "YES" else resolution["no_exit"]
                realized_pnl = (pm_exit - pm_entry_price) / pm_entry_price * position_usd
                await patch_position_resolution(conn, position_id, pm_exit, realized_pnl, "market_resolved_late")
                print(f"  ✓ {slug} {action}: exit={pm_exit:.4f}, pnl={realized_pnl:+.2f}")
                recovered += 1
            except Exception as e:
                print(f"  ✗ {slug}: hata — {e}")

        still_null = total - recovered
        print(f"\nSonuç: {recovered} recovered, {still_null} still null")
    finally:
        if conn:
            await conn.close()


if __name__ == "__main__":
    asyncio.run(backfill())
