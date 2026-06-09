"""data/depth_enricher.py — Faz 4A-0 Shadow Mode depth telemetri.

Pozisyon açıldıktan sonra (position_id belli olduktan sonra) async
fire-and-forget olarak çağrılır. Trade kararını ve execution'ı ASLA
bloklamaz. Hata durumunda pozisyon kaydındaki alanlar NULL kalır.
Hiçbir gate/scout/risk filtresi içermez — sadece log.
"""
import asyncio
import aiosqlite
from pathlib import Path

from data.clob_price import get_book, sorted_bids

DB_FILE = Path("logs/mispricing.db")


async def enrich_entry_depth(
    position_id: str,
    token_id:    str,
    shares:      float,
    entry_price: float,
    db_path:     Path | None = None,
) -> None:
    """Exit-side book depth metrikleri pozisyon kaydına yaz (fire-and-forget).

    token_id: tuttuğumuz token (YES → YES token, NO → NO token).
    Bu tokenin BID tarafı = stop anında satacağımız taraf.
    """
    try:
        book = await get_book(token_id)
        if not book:
            return

        bids = sorted_bids(book)  # pahalı→ucuz (best=ilk); bids[0]'ı best sanma
        if not bids:
            return

        top_size = bids[0][1]  # en yüksek bid'in size'ı
        if top_size <= 0:
            return

        # Depth walk: position_size kadar fill için kaç level ve ortalama fiyat
        remaining = shares
        levels    = 0
        w_price   = 0.0
        for px, sz in bids:
            take       = min(remaining, sz)
            w_price   += take * px
            remaining -= take
            levels    += 1
            if remaining <= 0:
                break

        filled        = shares - remaining
        est_exit      = w_price / filled if filled > 0 else None
        slippage      = (est_exit - entry_price) / entry_price if (est_exit and entry_price > 0) else None

        path = db_path or DB_FILE
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """UPDATE positions SET
                     entry_top_book_size          = ?,
                     entry_depth_for_size         = ?,
                     entry_est_exit_price         = ?,
                     entry_depth_slippage_pct     = ?,
                     entry_book_levels_used       = ?
                   WHERE position_id = ?""",
                (top_size, filled, est_exit, slippage, levels, position_id),
            )
            await conn.commit()

    except Exception:
        pass  # shadow mode: sessizce geç, trade'i bloklamaz
