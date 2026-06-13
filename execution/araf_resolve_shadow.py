"""execution/araf_resolve_shadow.py — A3-pure ARAF resolution shadow persistence (paper-first).

Boundary (onaylı): `decide_araf_resolution`'ın `ResolutionResult`'ını yalnız append-only
`araf_resolution_shadow` tablosuna dayanıklı yazar. `order_intents` ve `positions` DOKUNULMAZ
(canlı state machine / pozisyon yok). P&L / fee-amount / muhasebe materialize YOK.

Decimal alanlar string olarak yazılır (float yok, keyfi quantize yok). matched_trade_ids tuple/list
ise kanonik metne (data-order korunur) çevrilir. Version provenance kod-sabiti (git-SHA gömme yok).
Idempotency anahtarı = order_intent_id; aynı intent ikinci kez → "DUPLICATE" (sessiz overwrite YOK).
DB write fail YUTULMAZ → raise (çağıran recovery/retry'a gider). Canlı API/DB import YOK.
"""
from datetime import datetime, timezone

import aiosqlite

from execution.order_intent import DB_FILE

_RESOLVER_CONTRACT = "v0"
_ADAPTER_CONTRACT = "v0"
_SCHEMA_VERSION = 1


class ArafShadowConflictError(Exception):
    """Aynı order_intent_id için FARKLI evidence ile ikinci kayıt denemesi (tutarsız veri).
    Fail-closed: sessiz DUPLICATE/overwrite YASAK — kayıt bozulmasını maskelememek için raise.
    (Pure resolver `_ACCOUNTING_CONFLICT`→RECOVERY felsefesinin shadow-katmanı karşılığı.)"""


def _canonical_trade_ids(matched_trade_ids) -> str | None:
    """tuple/list → data-order korunmuş kanonik metin (virgül-join). None → None.
    Tek id'de tek token döner. Decimal/sayı yorumu YOK — kimlik metni olduğu gibi taşınır."""
    if matched_trade_ids is None:
        return None
    return ",".join(str(t) for t in matched_trade_ids)


def _decimal_str(value) -> str | None:
    """Decimal/None → string (float'a DÜŞMEDEN). None → None. str(Decimal) kanonik gösterimi korur."""
    if value is None:
        return None
    return str(value)


async def record_araf_resolution(db_path, order_intent_id, exchange_order_id, resolution) -> str:
    """ResolutionResult'ı araf_resolution_shadow'a yazar. Döner "RECORDED" | "DUPLICATE".

    A3-pure: yalnız shadow tablosu. order_intents/positions'a DOKUNMAZ. Aynı order_intent_id +
    AYNI evidence → idempotent "DUPLICATE" (overwrite/merge YOK). Aynı order_intent_id + FARKLI
    evidence → fail-closed `ArafShadowConflictError` (tutarsız veri maskelenmez). DB fault → raise.
    """
    now = datetime.now(timezone.utc).isoformat()
    # Yazılacak kanonik evidence (SELECT kolon sırasıyla birebir; created_at/recovery_reason hariç).
    new_evidence = (
        exchange_order_id,
        resolution.state,
        _decimal_str(resolution.matched_size),
        _decimal_str(resolution.avg_price),
        _decimal_str(resolution.fee_rate_bps),
        _canonical_trade_ids(resolution.matched_trade_ids),
        resolution.accounting_source,
        _RESOLVER_CONTRACT,
        _ADAPTER_CONTRACT,
        _SCHEMA_VERSION,
    )
    async with aiosqlite.connect(str(db_path or DB_FILE)) as conn:
        await conn.execute("BEGIN IMMEDIATE")
        cur = await conn.execute(
            "SELECT exchange_order_id, resolution_state, matched_size, avg_price, fee_rate_bps, "
            "matched_trade_ids, accounting_source, resolver_contract, adapter_contract, "
            "schema_version FROM araf_resolution_shadow WHERE order_intent_id=?", (order_intent_id,))
        existing = await cur.fetchone()
        if existing is not None:
            await conn.execute("ROLLBACK")
            if tuple(existing) == new_evidence:
                return "DUPLICATE"          # birebir aynı → idempotent no-op
            raise ArafShadowConflictError(  # farklı evidence → tutarsız → fail-closed
                f"araf_resolution_shadow conflict for order_intent_id={order_intent_id!r}: "
                f"stored != new (overwrite YASAK)")
        await conn.execute(
            """INSERT INTO araf_resolution_shadow
                   (order_intent_id, exchange_order_id, resolution_state, matched_size, avg_price,
                    fee_rate_bps, matched_trade_ids, accounting_source, resolver_contract,
                    adapter_contract, schema_version, recovery_reason, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (order_intent_id,
             exchange_order_id,
             resolution.state,
             _decimal_str(resolution.matched_size),
             _decimal_str(resolution.avg_price),
             _decimal_str(resolution.fee_rate_bps),
             _canonical_trade_ids(resolution.matched_trade_ids),
             resolution.accounting_source,
             _RESOLVER_CONTRACT,
             _ADAPTER_CONTRACT,
             _SCHEMA_VERSION,
             getattr(resolution, "recovery_reason", None),
             now))
        await conn.execute("COMMIT")
        return "RECORDED"
