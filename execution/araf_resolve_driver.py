"""execution/araf_resolve_driver.py — B1 ARAF discover/fetch driver (paper-only, A3-pure devamı).

İlk faz: yalnız DISCOVER (pure DB-read). Çözülmemiş (UNRESOLVED_STATES) order_intents'i listeler.
Fetch/adapt/decide/record orchestration SONRAKİ RED'ler. positions/order_intents-terminal/
confirm_fill_atomic/canlı client YOK. Hiç write yok — salt SELECT.
"""
import aiosqlite

from execution.order_intent import DB_FILE, UNRESOLVED_STATES

# Driver fetch'i için intent başına gerekli alanlar (SELECT projeksiyonu).
_ELIGIBLE_FIELDS = (
    "order_intent_id", "exchange_order_id", "slug", "market_token_id",
    "side", "intended_size", "intended_price", "status",
)


async def discover_eligible_intents(db_path=None) -> list[dict]:
    """ARAF resolution için eligible order_intents (status ∈ UNRESOLVED_STATES) → dict listesi.

    Pure DB-read: yalnız order_intents SELECT; write YOK. reconciliation_status filtresi YOK
    (ilk faz kararı). Deterministic: ORDER BY created_at ASC, order_intent_id ASC.
    """
    qmarks = ",".join("?" * len(UNRESOLVED_STATES))
    sql = (
        f"SELECT {', '.join(_ELIGIBLE_FIELDS)} FROM order_intents "
        f"WHERE status IN ({qmarks}) "
        "ORDER BY created_at ASC, order_intent_id ASC"
    )
    async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(sql, tuple(sorted(UNRESOLVED_STATES))) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]
