"""tests/test_araf_resolve_driver.py — B1 ARAF discover/fetch driver (paper-only, A3-pure devamı).

Driver boundary (onaylı): RECOVERY_REQUIRED/SUBMITTED_UNKNOWN order_intents keşfi → (sonraki RED'ler)
get_order/get_trades → adapt_live_trades_page → decide_araf_resolution → record_araf_resolution.
İlk faz: yalnız discover (pure DB-read). positions/order_intents-terminal/confirm_fill_atomic YOK.

İlk RED structural: `execution.araf_resolve_driver.discover_eligible_intents` henüz yok → ImportError.
Eligible filtre ilk fazda yalnız status IN UNRESOLVED_STATES (reconciliation_status filtresi YOK).
Canlı API/DB yok — tmp_path SQLite + production init_schema.
"""
import sqlite3

import aiosqlite
import pytest


def _insert_intent(conn, iid, status):
    """order_intents'e test-local minimal satır (schema.py kolonları). status NOT NULL."""
    conn.execute(
        """INSERT INTO order_intents
               (order_intent_id, slug, market_token_id, side, intended_price, intended_size,
                status, exchange_order_id, reconciliation_status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (iid, f"slug-{iid}", f"tok-{iid}", "BUY", 0.42, 10.0,
         status, f"0xexch-{iid}", "pending", "2026-06-13T00:00:00+00:00"))


@pytest.mark.asyncio
async def test_discover_eligible_intents_returns_unresolved_only(tmp_path):
    """discover_eligible_intents → yalnız UNRESOLVED_STATES (SUBMITTED_UNKNOWN/RECOVERY_REQUIRED);
    terminal (FILLED) HARİÇ. Dönen satırlar gerekli alanları taşır; sonuç deterministic (id-sıralı)."""
    # Import test GÖVDESİNDE → modül yoksa temiz "1 failed" (collection error DEĞİL).
    from execution.araf_resolve_driver import discover_eligible_intents

    db = str(tmp_path / "araf_driver.db")
    from db.schema import init_schema
    async with aiosqlite.connect(db) as conn:
        await init_schema(conn)
        await conn.commit()

    boot = sqlite3.connect(db)
    try:
        _insert_intent(boot, "iid-a-unknown", "SUBMITTED_UNKNOWN")
        _insert_intent(boot, "iid-b-recovery", "RECOVERY_REQUIRED")
        _insert_intent(boot, "iid-c-filled", "FILLED")   # terminal → dönmemeli
        boot.commit()
    finally:
        boot.close()

    rows = await discover_eligible_intents(db)

    # Yalnız iki unresolved; FILLED yok. Deterministic: order_intent_id'ye göre sırala.
    ids = sorted(r["order_intent_id"] for r in rows)
    assert ids == ["iid-a-unknown", "iid-b-recovery"], f"yalnız unresolved beklenir: {ids}"

    statuses = {r["status"] for r in rows}
    assert statuses == {"SUBMITTED_UNKNOWN", "RECOVERY_REQUIRED"}, f"status seti: {statuses}"
    assert "iid-c-filled" not in ids, "terminal FILLED intent dönmemeli"

    # Her satır driver fetch'i için gerekli alanları taşımalı.
    by_id = {r["order_intent_id"]: r for r in rows}
    r = by_id["iid-a-unknown"]
    for field in ("order_intent_id", "exchange_order_id", "slug", "market_token_id",
                  "side", "intended_size", "intended_price", "status"):
        _ = r[field]   # mapping-by-name erişimi (dict veya sqlite3.Row) — yoksa KeyError/RED
    assert r["exchange_order_id"] == "0xexch-iid-a-unknown"
    assert r["slug"] == "slug-iid-a-unknown"
    assert r["market_token_id"] == "tok-iid-a-unknown"
    assert r["side"] == "BUY"
    assert r["status"] == "SUBMITTED_UNKNOWN"
