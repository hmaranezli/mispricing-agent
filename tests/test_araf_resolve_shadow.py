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


@pytest.mark.asyncio
async def test_conflicting_duplicate_shadow_fails_closed(tmp_path):
    """Aynı order_intent_id için FARKLI evidence ile ikinci çağrı → sessiz "DUPLICATE" YASAK,
    overwrite YASAK → fail-closed (exception). Tek satır A olarak kalır; order_intents/positions
    dokunulmaz. (Conflict ≠ identical-duplicate: identical → DUPLICATE no-op; farklı payload →
    tutarsız veri → kayıt bozulmasını maskelememek için fail-closed — pure resolver felsefesi.)"""
    from execution.araf_resolve_shadow import record_araf_resolution

    db = str(tmp_path / "araf_shadow_conflict.db")
    from db.schema import init_schema
    async with aiosqlite.connect(db) as conn:
        await init_schema(conn)
        await conn.commit()

    resolution_a = ResolutionResult(
        state="FILLED",
        matched_size=Decimal("10"),
        avg_price=Decimal("0.42"),
        fee_rate_bps=Decimal("0"),
        matched_trade_ids=("trade-001",),
        accounting_source="CONFIRMED_TRADE",
    )
    first = await record_araf_resolution(db, "iid-conflict-1", "0xexch-conflict-1", resolution_a)
    assert first == "RECORDED", f"ilk kayıt RECORDED: {first!r}"

    # FARKLI evidence (B) — aynı intent. Tutarsız → fail-closed beklenir.
    resolution_b = ResolutionResult(
        state="FILLED",
        matched_size=Decimal("9"),
        avg_price=Decimal("0.43"),
        fee_rate_bps=Decimal("0"),
        matched_trade_ids=("trade-999",),
        accounting_source="CONFIRMED_TRADE",
    )
    # GREEN'de özel ArafShadowConflictError eklenebilir; şimdilik generic Exception kabul.
    with pytest.raises(Exception):
        await record_araf_resolution(db, "iid-conflict-1", "0xexch-conflict-1", resolution_b)

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT matched_size, avg_price, matched_trade_ids FROM araf_resolution_shadow "
            "WHERE order_intent_id=?", ("iid-conflict-1",)).fetchall()
        assert len(rows) == 1, f"tek satır kalmalı: {len(rows)}"
        # İlk (A) evidence korunmalı — B ile overwrite YASAK.
        assert rows[0][0] == "10", f"matched_size A korunmalı: {rows[0][0]!r}"
        assert rows[0][1] == "0.42", f"avg_price A korunmalı: {rows[0][1]!r}"
        assert rows[0][2] == "trade-001", f"matched_trade_ids A korunmalı: {rows[0][2]!r}"

        assert conn.execute("SELECT COUNT(*) FROM order_intents").fetchone()[0] == 0, \
            "order_intents'e yazım YOK (A3-pure)"
        assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0, \
            "positions'a yazım YOK (A3-pure)"
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_recovery_required_shadow_writes_null_accounting(tmp_path):
    """state="RECOVERY_REQUIRED" → accounting alanları DB'ye NULL (sahte "None"/""/"0" YASAK),
    recovery_reason="MISSING_TELEMETRY" yazılır; order_intents/positions dokunulmaz (A3-pure).
    Anti-hallucination: kanıt yokken muhasebe sayısı uydurulmaz."""
    from execution.araf_resolve_shadow import record_araf_resolution

    db = str(tmp_path / "araf_shadow_recovery.db")
    from db.schema import init_schema
    async with aiosqlite.connect(db) as conn:
        await init_schema(conn)
        await conn.commit()

    resolution = ResolutionResult(
        state="RECOVERY_REQUIRED",
        matched_size=None,
        avg_price=None,
        fee_rate_bps=None,
        matched_trade_ids=None,
        accounting_source=None,
    )
    # ResolutionResult frozen dataclass + recovery_reason alanı YOK → object.__setattr__ ile ekle
    # (normal setattr FrozenInstanceError atar; bu bypass setup'ı writer'a ulaşmadan çökmemeli).
    object.__setattr__(resolution, "recovery_reason", "MISSING_TELEMETRY")

    result = await record_araf_resolution(db, "iid-recovery-1", "0xexch-recovery-1", resolution)
    assert result == "RECORDED", f"RECOVERY_REQUIRED kaydı RECORDED: {result!r}"

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT resolution_state, matched_size, avg_price, fee_rate_bps, matched_trade_ids, "
            "accounting_source, recovery_reason FROM araf_resolution_shadow "
            "WHERE order_intent_id=?", ("iid-recovery-1",)).fetchall()
        assert len(rows) == 1, f"tek satır: {len(rows)}"
        r = rows[0]
        assert r[0] == "RECOVERY_REQUIRED", f"resolution_state: {r[0]!r}"
        # Accounting alanları gerçek NULL — sahte string ("None"/""/"0") YASAK.
        assert r[1] is None, f"matched_size NULL olmalı (sahte string değil): {r[1]!r}"
        assert r[2] is None, f"avg_price NULL: {r[2]!r}"
        assert r[3] is None, f"fee_rate_bps NULL: {r[3]!r}"
        assert r[4] is None, f"matched_trade_ids NULL: {r[4]!r}"
        assert r[5] is None, f"accounting_source NULL: {r[5]!r}"
        assert r[6] == "MISSING_TELEMETRY", f"recovery_reason: {r[6]!r}"

        assert conn.execute("SELECT COUNT(*) FROM order_intents").fetchone()[0] == 0, \
            "order_intents'e yazım YOK (A3-pure)"
        assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0, \
            "positions'a yazım YOK (A3-pure)"
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_shadow_write_failure_raises(tmp_path):
    """DB yazım altyapısı bozuksa (araf_resolution_shadow tablosu yok) record_araf_resolution
    hatayı YUTMAZ → fail-closed exception propagate; "RECORDED"/"DUPLICATE" DÖNMEZ. Canlı state
    tabloları (order_intents/positions) yan-etkisiz kalır."""
    from execution.araf_resolve_shadow import record_araf_resolution

    db = str(tmp_path / "araf_shadow_dbfail.db")
    from db.schema import init_schema
    async with aiosqlite.connect(db) as conn:
        await init_schema(conn)
        await conn.commit()

    # Şema kurulduktan SONRA yalnız shadow tablosunu boz (DROP) — diğer tablolar sağlam kalır.
    boot = sqlite3.connect(db)
    try:
        boot.execute("DROP TABLE araf_resolution_shadow")
        boot.commit()
    finally:
        boot.close()

    resolution = ResolutionResult(
        state="FILLED",
        matched_size=Decimal("10"),
        avg_price=Decimal("0.42"),
        fee_rate_bps=Decimal("0"),
        matched_trade_ids=("trade-001",),
        accounting_source="CONFIRMED_TRADE",
    )

    with pytest.raises(Exception) as exc_info:
        await record_araf_resolution(db, "iid-dbfail-1", "0xexch-dbfail-1", resolution)

    # Gevşek altyapı-hatası kontrolü (sqlite "no such table" / tablo adı).
    msg = str(exc_info.value).lower()
    assert "no such table" in msg or "araf_resolution_shadow" in msg, \
        f"DB altyapı hatası beklenir (yutulmamalı): {exc_info.value!r}"

    # Exception sonrası canlı state tabloları okunabiliyorsa yan-etki yok (A3-pure).
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM order_intents").fetchone()[0] == 0, \
            "order_intents'e yazım YOK"
        assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0, \
            "positions'a yazım YOK"
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_duplicate_resolution_shadow_is_idempotent(tmp_path):
    """Aynı order_intent_id için ikinci record_araf_resolution → "DUPLICATE", tek satır kalır,
    ilk satır OVERWRITE EDİLMEZ; order_intents/positions dokunulmaz (A3-pure idempotency)."""
    from execution.araf_resolve_shadow import record_araf_resolution

    db = str(tmp_path / "araf_shadow_dup.db")
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

    first = await record_araf_resolution(db, "iid-dup-1", "0xexch-dup-1", resolution)
    assert first == "RECORDED", f"ilk kayıt RECORDED: {first!r}"

    # İkinci çağrı — aynı order_intent_id + aynı evidence → idempotent DUPLICATE.
    second = await record_araf_resolution(db, "iid-dup-1", "0xexch-dup-1", resolution)
    assert second == "DUPLICATE", f"aynı intent ikinci kez DUPLICATE: {second!r}"

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT matched_size, avg_price, matched_trade_ids FROM araf_resolution_shadow "
            "WHERE order_intent_id=?", ("iid-dup-1",)).fetchall()
        assert len(rows) == 1, f"tek satır kalmalı (overwrite/çift YOK): {len(rows)}"
        assert rows[0][0] == "10", f"matched_size ilk kayıtla aynı: {rows[0][0]!r}"
        assert rows[0][1] == "0.42", f"avg_price ilk kayıtla aynı: {rows[0][1]!r}"
        assert rows[0][2] == "trade-001", f"matched_trade_ids ilk kayıtla aynı: {rows[0][2]!r}"

        assert conn.execute("SELECT COUNT(*) FROM order_intents").fetchone()[0] == 0, \
            "order_intents'e yazım YOK (A3-pure)"
        assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0, \
            "positions'a yazım YOK (A3-pure)"
    finally:
        conn.close()
