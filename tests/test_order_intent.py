"""tests/test_order_intent.py — Faz 2a: local idempotency + order_intent state machine.

Native idempotency YOK (salt random) → pre-submit INTENT_CREATED kaydı + DB UNIQUE.
SUBMITTED_UNKNOWN varken 2. emir YASAK. Fill-confirm olmadan position açık DEĞİL.
Heuristic reconciliation (get_trades) = 2c (burada sadece alanlar + contract).
"""
import sys
import os
import aiosqlite
import pytest
from pathlib import Path
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def _db():
    from db.schema import init_schema
    d = tempfile.mkdtemp()
    dbp = Path(d) / "t.db"
    conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
    return dbp


# 1. Network'ten ÖNCE intent DB'ye yazılır (pre-submit INTENT_CREATED)
@pytest.mark.asyncio
async def test_create_intent_written_before_submit():
    import execution.order_intent as oi
    dbp = await _db()
    iid = await oi.create_intent(dbp, token_id="tok1", side="BUY", intended_price=0.55,
                                 intended_size=25.0, slug="btc-5m", wallet="0xabc")
    assert iid
    conn = await aiosqlite.connect(str(dbp))
    async with conn.execute("SELECT status, market_token_id, side, intended_price, intended_size, payload_hash, intent_timestamp FROM order_intents WHERE order_intent_id=?", (iid,)) as c:
        row = await c.fetchone()
    await conn.close()
    assert row[0] == "INTENT_CREATED"
    assert row[1] == "tok1" and row[2] == "BUY" and row[3] == 0.55 and row[4] == 25.0
    assert row[5] and row[6]  # payload_hash + intent_timestamp dolu


# 2. Aynı order_intent_id ikinci kez yazılamaz (DB UNIQUE)
@pytest.mark.asyncio
async def test_duplicate_intent_id_rejected():
    import execution.order_intent as oi
    dbp = await _db()
    iid = await oi.create_intent(dbp, token_id="tok1", side="BUY", intended_price=0.5,
                                 intended_size=10.0, slug="s")
    # aynı id ile tekrar INSERT → reddedilir
    import sqlite3
    raised = False
    try:
        # async with closes the connection (and joins its non-daemon worker thread) even when the
        # duplicate INSERT raises IntegrityError below — otherwise the aiosqlite connection leaks.
        async with aiosqlite.connect(str(dbp)) as conn:
            await conn.execute("INSERT INTO order_intents (order_intent_id, status, created_at) VALUES (?, 'INTENT_CREATED', 't')", (iid,))
            await conn.commit()
    except sqlite3.IntegrityError:
        raised = True
    assert raised


# 3 & 4. SUBMITTED_UNKNOWN varken yeni emir BLOKLANIR (otomatik 2. submit yok)
@pytest.mark.asyncio
async def test_unresolved_intent_blocks_new_order():
    import execution.order_intent as oi
    dbp = await _db()
    iid = await oi.create_intent(dbp, token_id="tokX", side="BUY", intended_price=0.5,
                                 intended_size=10.0, slug="s")
    await oi.transition(dbp, iid, "SUBMITTED_UNKNOWN")
    # aynı token için çözülmemiş intent var → yeni emir bloklanmalı
    assert await oi.has_unresolved_intent(dbp, "tokX") is True
    # farklı token serbest
    assert await oi.has_unresolved_intent(dbp, "tokOther") is False
    # RECOVERY_REQUIRED de bloklar
    await oi.transition(dbp, iid, "RECOVERY_REQUIRED", reason="ambiguous")
    assert await oi.has_unresolved_intent(dbp, "tokX") is True


# 5. Fill-confirm olmadan position AÇIK SAYILMAZ
def test_position_open_only_when_filled():
    import execution.order_intent as oi
    assert oi.is_position_open("INTENT_CREATED") is False
    assert oi.is_position_open("SUBMITTED_UNKNOWN") is False
    assert oi.is_position_open("ACCEPTED") is False  # accepted ≠ filled
    assert oi.is_position_open("REJECTED") is False
    assert oi.is_position_open("FILLED") is True
    assert oi.is_position_open("PARTIAL_FILLED") is True


# 6. Reconciliation alanları schema'da var (2c için hazır, gerçek matching 2c)
@pytest.mark.asyncio
async def test_reconciliation_fields_in_schema():
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    async with conn.execute("PRAGMA table_info(order_intents)") as cur:
        cols = {r[1] for r in await cur.fetchall()}
    await conn.close()
    for c in ("order_intent_id", "slug", "market_token_id", "side", "intended_price",
              "intended_size", "payload_hash", "status", "intent_timestamp", "submitted_at",
              "wallet_address", "exchange_order_id", "matched_trade_id", "size_matched",
              "reconciliation_status", "reconciliation_reason"):
        assert c in cols, f"eksik order_intents kolon: {c}"


# state machine geçiş + transition alanları
@pytest.mark.asyncio
async def test_transition_records_server_order_id_and_size():
    import execution.order_intent as oi
    dbp = await _db()
    iid = await oi.create_intent(dbp, token_id="t", side="BUY", intended_price=0.5,
                                 intended_size=10.0, slug="s")
    await oi.transition(dbp, iid, "ACCEPTED", server_order_id="srv-99")
    await oi.transition(dbp, iid, "FILLED", size_matched=10.0)
    conn = await aiosqlite.connect(str(dbp))
    async with conn.execute("SELECT status, exchange_order_id, size_matched FROM order_intents WHERE order_intent_id=?", (iid,)) as c:
        row = await c.fetchone()
    await conn.close()
    assert row[0] == "FILLED" and row[1] == "srv-99" and row[2] == 10.0
