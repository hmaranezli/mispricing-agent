"""tests/test_araf_resolve_shadow.py — A3-pure ARAF resolution shadow persistence.

Boundary kararı (onaylı): A3-pure paper-first. `decide_araf_resolution`'ın `ResolutionResult`'ı
yeni append-only `araf_resolution_shadow` tablosuna dayanıklı yazılır; `order_intents` ve
`positions` DOKUNULMAZ (canlı state machine / pozisyon yok). Version provenance kod-sabiti:
resolver_contract="v0", adapter_contract="v0", schema_version=1 (git-SHA gömme yok).

İlk RED structural: `execution.araf_resolve_shadow.record_araf_resolution` henüz yok → ImportError.
Canlı API/DB yok — tmp_path SQLite + production `init_schema` (GREEN sonrası tabloyu yaratır).
"""
import sqlite3
from decimal import Decimal

import aiosqlite
import pytest

from data.clob_reconcile import ResolutionResult


@pytest.mark.asyncio
async def test_filled_resolution_persists_shadow_record(tmp_path):
    """FILLED ResolutionResult + order_intent_id + exchange_order_id → araf_resolution_shadow'a
    BİR satır kalıcı yazılır, "RECORDED" döner; order_intents/positions'a yazım YOK (A3-pure).
    Decimal alanlar string olarak (float yok, keyfi quantize yok)."""
    # Import test GÖVDESİNDE → modül yoksa temiz "1 failed" (collection error DEĞİL).
    from execution.araf_resolve_shadow import record_araf_resolution

    db = str(tmp_path / "araf_shadow.db")
    # Production schema init (GREEN, araf_resolution_shadow'u additive migration ile yaratacak).
    from db.schema import init_schema
    async with aiosqlite.connect(db) as conn:
        await init_schema(conn)
        await conn.commit()

    resolution = ResolutionResult(
        state="FILLED",
        matched_size=Decimal("10"),
        avg_price=Decimal("0.42"),
        fee_rate_bps=Decimal("0"),
        matched_trade_ids=("trade-001",),
        accounting_source="CONFIRMED_TRADE",
    )

    result = await record_araf_resolution(
        db, "iid-araf-1", "0xexch-araf-1", resolution)

    assert result == "RECORDED", f"ilk kayıt RECORDED dönmeli: {result!r}"

    # Shadow row readback (sync sqlite3 — saf doğrulama).
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT order_intent_id, exchange_order_id, resolution_state, matched_size, "
            "avg_price, fee_rate_bps, matched_trade_ids, accounting_source, resolver_contract, "
            "adapter_contract, schema_version FROM araf_resolution_shadow"
        ).fetchall()
        assert len(rows) == 1, f"tek shadow satırı beklenir: {len(rows)}"
        r = rows[0]
        assert r[0] == "iid-araf-1"
        assert r[1] == "0xexch-araf-1"
        assert r[2] == "FILLED"
        assert r[3] == "10", f"matched_size Decimal-string: {r[3]!r}"
        assert r[4] == "0.42", f"avg_price Decimal-string: {r[4]!r}"
        assert r[5] == "0", f"fee_rate_bps Decimal-string (rate evidence): {r[5]!r}"
        assert r[6] == "trade-001", f"matched_trade_ids kanonik metin: {r[6]!r}"
        assert r[7] == "CONFIRMED_TRADE"
        assert r[8] == "v0", f"resolver_contract: {r[8]!r}"
        assert r[9] == "v0", f"adapter_contract: {r[9]!r}"
        assert r[10] == 1, f"schema_version: {r[10]!r}"

        # A3-pure: order_intents ve positions DOKUNULMAZ.
        assert conn.execute("SELECT COUNT(*) FROM order_intents").fetchone()[0] == 0, \
            "order_intents'e yazım YOK (A3-pure)"
        assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0, \
            "positions'a yazım YOK (A3-pure)"
    finally:
        conn.close()
