"""execution/araf_resolve_driver.py — B1 ARAF discover/fetch driver (paper-only, A3-pure devamı).

İlk faz: yalnız DISCOVER (pure DB-read). Çözülmemiş (UNRESOLVED_STATES) order_intents'i listeler.
Fetch/adapt/decide/record orchestration SONRAKİ RED'ler. positions/order_intents-terminal/
confirm_fill_atomic/canlı client YOK. Hiç write yok — salt SELECT.
"""
import inspect

import aiosqlite

from execution.order_intent import DB_FILE, UNRESOLVED_STATES
from data.clob_live_adapter import adapt_live_trades_page
from data.clob_reconcile import decide_araf_resolution, ResolutionResult
from execution.araf_resolve_shadow import record_araf_resolution

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


async def _maybe_await(value):
    """Sync/async client toleransı: client metodu sync değer veya awaitable döndürebilir.
    Awaitable ise await eder; değilse olduğu gibi döner. (Async test stub + sync canlı
    ClobClient ikisini de destekler; ayrı async adapter bu fazda YOK.)"""
    if inspect.isawaitable(value):
        return await value
    return value


def _recovery_resolution(reason: str) -> ResolutionResult:
    """Fail-closed non-terminal resolution + recovery_reason (shadow'a yazılır). ResolutionResult
    frozen dataclass + recovery_reason alanı YOK → object.__setattr__ ile eklenir (record_araf_resolution
    getattr ile okur). Accounting alanları None (anti-hallucination: kanıt yok)."""
    resolution = ResolutionResult(
        state="RECOVERY_REQUIRED",
        matched_size=None,
        avg_price=None,
        fee_rate_bps=None,
        matched_trade_ids=None,
        accounting_source=None,
    )
    object.__setattr__(resolution, "recovery_reason", reason)
    return resolution


async def resolve_intent_to_shadow(client, intent_row: dict, db_path=None) -> str:
    """Tek eligible intent için ARAF resolution orchestration → A3-pure shadow yazımı.

    Akış: get_order + get_trades_paginated (injected client) → adapt_live_trades_page →
    decide_araf_resolution(order or {}) → record_araf_resolution. positions/order_intents-update/
    confirm_fill_atomic/PnL/fee-amount/canlı-client import YOK. Döner record_araf_resolution sonucu.

    NULL exchange_order_id ve next_cursor != "LTE=" (pagination) recovery yolları SONRAKİ RED'ler.
    """
    exchange_order_id = intent_row.get("exchange_order_id")

    # NULL exchange_order_id: fetch için order_id yok → client'a DOKUNMA; explicit recovery shadow.
    if not exchange_order_id:
        return await record_araf_resolution(
            db_path, intent_row["order_intent_id"], exchange_order_id,
            _recovery_resolution("MISSING_EXCHANGE_ORDER_ID"))

    order = await _maybe_await(client.get_order(exchange_order_id))

    # NOT: get_trades_paginated için nötr parametre. maker/taker ayrımı BUY/SELL yönünden
    # TÜRETİLMEZ; gerçek dual-fetch (taker_order_id vs maker_address) policy sonraki RED'de.
    params = {"order_id": exchange_order_id}
    page = await _maybe_await(client.get_trades_paginated(params, next_cursor=None))

    adapted = adapt_live_trades_page(page)

    # Tarama eksik (çok sayfa): next_cursor != END_CURSOR → fill'ler sonraki sayfalara yayılabilir →
    # terminal karar (FILLED) UNDERCOUNT riski. decide ÇAĞIRMA; explicit recovery shadow.
    if adapted.get("next_cursor") != "LTE=":
        return await record_araf_resolution(
            db_path, intent_row["order_intent_id"], exchange_order_id,
            _recovery_resolution("INCOMPLETE_SCAN_PAGINATION"))

    resolution = decide_araf_resolution(intent_row, order or {}, adapted)

    return await record_araf_resolution(
        db_path, intent_row["order_intent_id"], exchange_order_id, resolution)
