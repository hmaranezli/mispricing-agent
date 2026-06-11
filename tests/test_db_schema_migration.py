"""tests/test_db_schema_migration.py — Faz 2c Task H1: positions(order_intent_id) partial UNIQUE index.

H1 kapsamı = YALNIZ partial UNIQUE index `WHERE order_intent_id IS NOT NULL`.
shares kolonu ZATEN var (schema.py:325) — eklenmez, backfill yapılmaz.

Kurallar: network yok; canlı DB'ye write yok; YALNIZ temp-file tmp DB (in-memory DEĞİL);
schema gerçek `db.schema.init_schema` yolundan kurulur (test içinde elle schema YOK).
"""
import sqlite3
import tempfile
from pathlib import Path

import aiosqlite
import pytest

from db.schema import init_schema


async def _fresh_tmp_db() -> Path:
    """Temp-file tmp DB + gerçek init_schema (canlı logs/mispricing.db'ye DOKUNMAZ, in-memory DEĞİL)."""
    d = tempfile.mkdtemp()
    dbp = Path(d) / "t.db"
    conn = await aiosqlite.connect(str(dbp))
    await init_schema(conn)
    await conn.close()
    return dbp


# ── 0) Ön koşul: order_intent_id kolonu gerçek schema ile geliyor mu ─────────

@pytest.mark.asyncio
async def test_precondition_order_intent_id_column_exists_via_real_schema():
    """RED testlerinin doğru nedenle fail etmesi için ön koşul: gerçek schema.py ile init edilen
    tmp DB'de positions.order_intent_id kolonu OLMALI. Yoksa index testleri YANLIŞ nedenle fail
    eder → bunu ayrı blocker olarak gösterir. (shares varlığı RED nedeni DEĞİL.)"""
    dbp = await _fresh_tmp_db()
    conn = await aiosqlite.connect(str(dbp))
    cols = [r[1] for r in await (await conn.execute("PRAGMA table_info(positions)")).fetchall()]
    await conn.close()
    assert "order_intent_id" in cols, (
        f"BLOCKER: order_intent_id kolonu gerçek schema'da YOK — index RED'i yanlış nedenle "
        f"fail eder: {cols}")


# ── 1) RED: partial UNIQUE index yokluğu ─────────────────────────────────────

@pytest.mark.asyncio
async def test_partial_unique_index_exists_with_not_null_predicate():
    """RED: ix_positions_order_intent_id (veya eşdeğer) partial UNIQUE index, gerçek schema'da
    HENÜZ yok → DOĞRU NEDENLE fail. Index SQL'i `WHERE order_intent_id IS NOT NULL` içermeli."""
    dbp = await _fresh_tmp_db()
    conn = await aiosqlite.connect(str(dbp))
    # sqlite_master: order_intent_id'e ait index'in tam CREATE SQL'i (WHERE şartı dahil)
    rows = await (await conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql LIKE '%order_intent_id%'"
    )).fetchall()
    await conn.close()
    assert rows, ("partial UNIQUE index YOK (order_intent_id'e ait index sqlite_master'da "
                  "bulunamadı) — H1 migration eklenmeli")
    sql = " ".join((r[1] or "") for r in rows)
    sql_norm = " ".join(sql.upper().split())
    assert "UNIQUE" in sql_norm, f"index UNIQUE olmalı: {sql}"
    assert "WHERE" in sql_norm and "ORDER_INTENT_ID IS NOT NULL" in sql_norm, (
        f"partial şart `WHERE order_intent_id IS NOT NULL` olmalı: {sql}")


# ── 2) RED: aynı non-null order_intent_id → IntegrityError; NULL'lar serbest ──

@pytest.mark.asyncio
async def test_duplicate_non_null_order_intent_id_blocked_nulls_allowed():
    """RED: index olmadığı için aynı non-null order_intent_id ile ikinci INSERT IntegrityError
    FIRLATMAZ → `pytest.raises` 'DID NOT RAISE' ile DOĞRU NEDENLE fail. NULL order_intent_id'li
    iki kayıt ise (partial index gereği) her durumda sorunsuz girmeli."""
    dbp = await _fresh_tmp_db()
    conn = await aiosqlite.connect(str(dbp))

    async def ins(pid, oiid):
        await conn.execute(
            "INSERT INTO positions (position_id, ts_open, slug, asset, action, status, dry_run, "
            "order_intent_id) VALUES (?,?,?,?,?,?,?,?)",
            (pid, "2026-06-10T00:00:00", "s", "BTC", "YES", "open", 0, oiid))
        await conn.commit()

    try:
        # NULL order_intent_id → iki kayıt serbest (partial index NULL'ı kısıtlamaz)
        await ins("p-null-1", None)
        await ins("p-null-2", None)
        # İlk non-null intent
        await ins("p1", "intent-dup")
        # AYNI non-null intent ikinci kez → index VARSA IntegrityError beklenir
        with pytest.raises(sqlite3.IntegrityError):
            await ins("p2", "intent-dup")
    finally:
        await conn.close()


# ── 3) Regression-lock (PASS bekleniyor): shares NULL → NULL kalır, 0'a zorlanmaz ─

@pytest.mark.asyncio
async def test_legacy_null_shares_stays_null_not_zeroed():
    """Regression-lock (RED DEĞİL): shares=NULL INSERT edilen kayıt geri okunduğunda shares NULL
    KALMALI (sahte 0'a zorlanmamalı). H1 shares'a dokunmaz; bu invariant'ı kilitler."""
    dbp = await _fresh_tmp_db()
    conn = await aiosqlite.connect(str(dbp))
    await conn.execute(
        "INSERT INTO positions (position_id, ts_open, slug, asset, action, status, dry_run) "
        "VALUES ('p-noshares','2026-06-10T00:00:00','s','BTC','YES','open',0)")
    await conn.commit()
    row = await (await conn.execute(
        "SELECT shares FROM positions WHERE position_id='p-noshares'")).fetchone()
    await conn.close()
    assert row[0] is None, f"shares NULL kalmalı (0'a çevrilmemeli): {row[0]!r}"
