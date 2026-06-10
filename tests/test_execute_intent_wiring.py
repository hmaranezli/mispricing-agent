"""tests/test_execute_intent_wiring.py — Faz 2c-3 execute() intent-wiring.

Task 0: schema + lineage kolonu (positions.order_intent_id) + execution_state
init_schema idempotency/readback. Hiçbir test gerçek network/canlı DB kullanmaz —
yalnız tmp DB. execute()/post_order wiring BU dosyada henüz YOK (sonraki task'lar).
"""
import sys
import os
import tempfile
from pathlib import Path

import aiosqlite
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def _fresh_db() -> Path:
    """Tmp DB + tam init_schema (canlı logs/mispricing.db'ye DOKUNMAZ)."""
    from db.schema import init_schema
    d = tempfile.mkdtemp()
    dbp = Path(d) / "t.db"
    conn = await aiosqlite.connect(str(dbp))
    await init_schema(conn)
    await conn.close()
    return dbp


async def _columns(dbp: Path, table: str) -> list[str]:
    conn = await aiosqlite.connect(str(dbp))
    async with conn.execute(f"PRAGMA table_info({table})") as cur:
        cols = [r[1] for r in await cur.fetchall()]
    await conn.close()
    return cols


# ── R3: positions.order_intent_id lineage kolonu ────────────────────────────

@pytest.mark.asyncio
async def test_positions_has_order_intent_id_column():
    dbp = await _fresh_db()
    cols = await _columns(dbp, "positions")
    assert "order_intent_id" in cols, f"order_intent_id kolonu eklenmeli: {cols}"


@pytest.mark.asyncio
async def test_init_schema_idempotent_rerun_preserves_rows():
    """init_schema iki kez (restart sim) → hata yok, satır korunur, kolon tek kalır."""
    from db.schema import init_schema
    dbp = await _fresh_db()
    # Satır ekle (order_intent_id'siz)
    conn = await aiosqlite.connect(str(dbp))
    try:
        await conn.execute(
            "INSERT INTO positions (position_id, ts_open, slug, asset, action, status, dry_run) "
            "VALUES ('p1','2026-06-10T00:00:00','s','BTC','YES','open',1)")
        await conn.commit()
        # Re-init (idempotent — bozmamalı)
        await init_schema(conn)
        async with conn.execute(
            "SELECT position_id, order_intent_id FROM positions WHERE position_id='p1'") as cur:
            row = await cur.fetchone()
    finally:
        await conn.close()  # aiosqlite conn DAİMA kapanmalı (açık kalırsa loop teardown asılır)
    assert row == ("p1", None), f"satır korunmalı, order_intent_id NULL olmalı: {row}"
    cols = await _columns(dbp, "positions")
    assert cols.count("order_intent_id") == 1, "kolon tekrar eklenmemeli (idempotent)"


@pytest.mark.asyncio
async def test_order_intent_id_migration_on_legacy_db_preserves_rows():
    """Eski (kolonsuz) positions tablosu + satır → init_schema ALTER ekler, satır korunur."""
    from db.schema import init_schema
    d = tempfile.mkdtemp()
    dbp = Path(d) / "legacy.db"
    conn = await aiosqlite.connect(str(dbp))
    try:
        # order_intent_id'siz minimal "legacy" positions tablosu
        await conn.execute("CREATE TABLE positions (position_id TEXT PRIMARY KEY, slug TEXT)")
        await conn.execute("INSERT INTO positions (position_id, slug) VALUES ('p-legacy','old-slug')")
        await conn.commit()
        # Migration uygula
        await init_schema(conn)
        async with conn.execute(
            "SELECT position_id, slug, order_intent_id FROM positions WHERE position_id='p-legacy'") as cur:
            row = await cur.fetchone()
    finally:
        await conn.close()
    assert row == ("p-legacy", "old-slug", None), f"legacy satır korunmalı + kolon NULL: {row}"


@pytest.mark.asyncio
async def test_log_position_open_persists_order_intent_id():
    """log_position_open position dict'teki order_intent_id'yi DB'ye yazar (lineage)."""
    from db.logger import log_position_open
    dbp = await _fresh_db()
    conn = await aiosqlite.connect(str(dbp))
    try:
        position = {
            "position_id": "pos-1",
            "opened_at": "2026-06-10T12:00:00+00:00",
            "slug": "btc-updown-5m-x", "asset": "BTC", "action": "YES",
            "pm_entry_price": 0.35, "fair_value": 0.55, "ref_price": 95000.0,
            "edge": 0.20, "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.0,
            "shares": 71.43, "order_id": "ord-1",
            "yes_token_id": "y1", "no_token_id": "n1",
            "order_intent_id": "intent-abc-123",
        }
        await log_position_open(conn, position)
        async with conn.execute(
            "SELECT order_intent_id FROM positions WHERE position_id='pos-1'") as cur:
            row = await cur.fetchone()
    finally:
        await conn.close()
    assert row[0] == "intent-abc-123", f"order_intent_id persist edilmeli: {row}"


# ── execution_state: init_schema idempotency/readback (regression lock) ──────
# Not: execution_state tablosu 2c-2 migration'ında zaten var; bu testler
# karakterizasyon/regression — canlı logs/mispricing.db'deki eksiklik eski
# process artefaktıydı, şema kusuru değil. Tablo şemadan düşerse bunlar yakalar.

@pytest.mark.asyncio
async def test_execution_state_created_by_init_schema():
    """Fresh init_schema → execution_state var, paused okunabilir (fail-closed DEĞİL)."""
    from execution.emergency_pause import is_emergency_paused
    dbp = await _fresh_db()
    cols = await _columns(dbp, "execution_state")
    assert "emergency_paused" in cols, f"execution_state şemada olmalı: {cols}"
    # Tablo var + satır yok → fail-closed değil, temiz False
    assert await is_emergency_paused(dbp) is False


@pytest.mark.asyncio
async def test_execution_state_singleton_survives_reinit():
    """set_emergency_pause sonrası re-init (restart sim) → singleton korunur, okunabilir."""
    from db.schema import init_schema
    from execution.emergency_pause import set_emergency_pause, is_emergency_paused, get_pause_record
    dbp = await _fresh_db()
    await set_emergency_pause(dbp, reason="test-trip", source="unit", order_intent_id="i-1")
    # Restart sim: yeni connection + init_schema (CREATE IF NOT EXISTS satırı silmemeli)
    conn = await aiosqlite.connect(str(dbp))
    await init_schema(conn)
    await conn.close()
    assert await is_emergency_paused(dbp) is True
    rec = await get_pause_record(dbp)
    assert rec is not None and rec["emergency_paused"] == 1
    assert rec["reason"] == "test-trip" and rec["source"] == "unit"
