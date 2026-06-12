"""tests/test_emergency_pause_resolve.py — Faz 2c-4 Slice D: emergency_pause resolve protokolü.

Append-only audit tablosu `execution_state_events` + (sonraki adımlarda) resolve_emergency_pause
akışı, TDD ile. Kurallar: network yok; canlı DB'ye write yok; YALNIZ temp-file tmp DB
(in-memory DEĞİL); schema gerçek `db.schema.init_schema` yolundan kurulur (test içinde elle
schema YOK).
"""
import sqlite3
import tempfile
from pathlib import Path

import aiosqlite
import pytest

from db.schema import init_schema


async def _fresh_tmp_db() -> Path:
    """Temp-file tmp DB + gerçek init_schema; idempotency için init iki kez koşar
    (canlı logs/mispricing.db'ye DOKUNMAZ, in-memory DEĞİL)."""
    d = tempfile.mkdtemp()
    dbp = Path(d) / "t.db"
    conn = await aiosqlite.connect(str(dbp))
    await init_schema(conn)
    await init_schema(conn)   # idempotent re-run (restart sim) bozmamalı
    await conn.close()
    return dbp


# ── 1) RED: append-only audit tablosu execution_state_events yokluğu ──────────

@pytest.mark.asyncio
async def test_events_table_migration_idempotent():
    """init_schema (iki kez) sonrası append-only `execution_state_events` tablosu OLMALI;
    çift init bozmamalı; tablo append-only/autoincrement davranmalı (iki event → ikisi durur,
    event_id artan)."""
    dbp = await _fresh_tmp_db()
    conn = await aiosqlite.connect(str(dbp))
    try:
        tables = [r[0] for r in await (await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
        # Tablo varlığı — RED: tablo henüz migration'da yok → AssertionError (collection/import değil):
        assert "execution_state_events" in tables, (
            f"execution_state_events append-only audit tablosu init_schema sonrası YOK: {tables}")
        # Append-only / autoincrement (GREEN sonrası): iki event eklenir, ikisi de durur, id artan:
        async def _ins(et):
            await conn.execute(
                "INSERT INTO execution_state_events (event_type, ts, new_state) VALUES (?,?,?)",
                (et, "2026-06-11T00:00:00+00:00", 1))
            await conn.commit()
        await _ins("TRIP")
        await _ins("RESOLVE")
        rows = await (await conn.execute(
            "SELECT event_id, event_type FROM execution_state_events ORDER BY event_id")).fetchall()
        assert len(rows) == 2, f"iki event de durmalı (append-only): {rows}"
        assert rows[0][0] < rows[1][0], f"event_id autoincrement artan olmalı: {rows}"
    finally:
        # TDD hijyeni: failing assertion olsa bile aiosqlite connection KAPATILIR
        # (aksi halde açık bağlantı process exit'i asar → RC=124 teardman hang).
        await conn.close()


# ── 2) RED: set_emergency_pause TRIP olayını append etmeli (idempotent) ───────

@pytest.mark.asyncio
async def test_set_emergency_pause_appends_trip_event_idempotent():
    """Gerçek set_emergency_pause çağrısı execution_state_events'e bir TRIP satırı ekler;
    idempotent ikinci çağrı yeni TRIP EKLEMEZ; execution_state.emergency_paused=1 kalır.
    (Event satırını test KENDİ yazmaz — yalnız gerçek fonksiyonun yan etkisini okur.)"""
    from execution.emergency_pause import set_emergency_pause
    dbp = await _fresh_tmp_db()
    # 1. çağrı (False→True trip)
    await set_emergency_pause(str(dbp), reason="task_h_recovery_write_failed:X",
                              source="task_h", order_intent_id="iid-1")
    conn = await aiosqlite.connect(str(dbp))
    try:
        n1 = (await (await conn.execute(
            "SELECT COUNT(*) FROM execution_state_events WHERE event_type='TRIP'")).fetchone())[0]
        # RED: set_emergency_pause henüz TRIP event yazmıyor → 0 → AssertionError
        assert n1 == 1, f"TRIP event count expected 1, got {n1}"
        # 2. çağrı (zaten paused → idempotent, yeni TRIP eklenmemeli)
        await set_emergency_pause(str(dbp), reason="ikinci-tetik",
                                  source="task_h", order_intent_id="iid-1")
        n2 = (await (await conn.execute(
            "SELECT COUNT(*) FROM execution_state_events WHERE event_type='TRIP'")).fetchone())[0]
        assert n2 == 1, f"idempotent ikinci set sonrası TRIP event count expected 1, got {n2}"
        # state hâlâ paused
        paused = (await (await conn.execute(
            "SELECT emergency_paused FROM execution_state WHERE state_key='global'")).fetchone())[0]
        assert paused == 1, f"execution_state.emergency_paused=1 kalmalı: {paused}"
    finally:
        await conn.close()


# ── 3) RED: verified resolve — offending intent terminal ise pause clear edilir ──

@pytest.mark.asyncio
async def test_verified_resolve_clears_when_intent_terminal():
    """Offending order_intent TERMINAL (CANCELLED) ise verified-resolve emergency_pause'u temizler
    ve append-only RESOLVE event yazar. Net-yeni resolve_emergency_pause → ilk RED Importance:
    'feature missing' (ImportError, test gövdesi içi import → '1 failed', collection error DEĞİL)."""
    from execution import order_intent, emergency_pause
    dbp = await _fresh_tmp_db()
    # 1-2. intent yarat (INTENT_CREATED)
    iid = await order_intent.create_intent(str(dbp), "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    # 3. terminal state'e taşı (INTENT_CREATED → CANCELLED; monotonic guard bloklamaz)
    await order_intent.transition(str(dbp), iid, "CANCELLED")
    # 4. pause'u bu intent'e bağla (recovery-ladder DB-write-fail trip senaryosu)
    await emergency_pause.set_emergency_pause(
        str(dbp), reason="task_h_recovery_write_failed:X", source="task_h", order_intent_id=iid)
    # 5. RED: net-yeni fonksiyon — import test gövdesinde (ImportError = feature missing)
    from execution.emergency_pause import resolve_emergency_pause
    await resolve_emergency_pause(
        str(dbp), order_intent_id=iid, resolved_by="human:hasan",
        reason="terminal intent reconciled", mode="verified")
    # 6. GREEN'de doğrulanacak davranış
    conn = await aiosqlite.connect(str(dbp))
    try:
        assert await emergency_pause.is_emergency_paused(str(dbp)) is False
        paused = (await (await conn.execute(
            "SELECT emergency_paused FROM execution_state WHERE state_key='global'")).fetchone())[0]
        assert paused == 0, f"execution_state.emergency_paused=0 olmalı: {paused}"
        ev = await (await conn.execute(
            "SELECT old_state, new_state, verified, force, order_intent_id, resolved_by, reason "
            "FROM execution_state_events WHERE event_type='RESOLVE'")).fetchall()
        assert len(ev) == 1, f"tek RESOLVE event olmalı: {ev}"
        old_state, new_state, verified, force, oi_id, rb, rsn = ev[0]
        assert old_state == 1 and new_state == 0, f"old=1 new=0 olmalı: {ev[0]}"
        assert verified == 1 and force == 0, f"verified=1 force=0 olmalı: {ev[0]}"
        assert oi_id == iid, f"order_intent_id eşleşmeli: {oi_id} != {iid}"
        assert rb == "human:hasan", f"resolved_by korunmalı: {rb}"
        assert rsn == "terminal intent reconciled", f"reason korunmalı: {rsn}"
    finally:
        await conn.close()


# ── 4) PIN (characterization): non-terminal intent → verified-resolve BLOCKED, fail-closed ──

@pytest.mark.asyncio
async def test_verified_resolve_blocked_when_intent_not_terminal():
    """Mevcut fail-closed davranışı kilitler (RED değil, characterization): offending intent
    TERMINAL değilse (INTENT_CREATED) verified-resolve REDDEDİLİR — pause AKTİF kalır, RESOLVE
    event YAZILMAZ, TRIP event korunur."""
    from execution import order_intent, emergency_pause
    from execution.emergency_pause import resolve_emergency_pause
    dbp = await _fresh_tmp_db()
    # intent yarat ama TERMINALE TAŞIMA → INTENT_CREATED (unresolved) olarak bırak
    iid = await order_intent.create_intent(str(dbp), "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    await emergency_pause.set_emergency_pause(
        str(dbp), reason="task_h_recovery_write_failed:X", source="task_h", order_intent_id=iid)
    result = await resolve_emergency_pause(
        str(dbp), order_intent_id=iid, resolved_by="human:hasan",
        reason="not terminal", mode="verified")
    conn = await aiosqlite.connect(str(dbp))
    try:
        assert result["resolved"] is False, f"blocked olmalı: {result}"
        assert result["blocked"] is True, f"blocked=True olmalı: {result}"
        assert result["observed_intent_state"] == "INTENT_CREATED", f"observed: {result}"
        # pause AKTİF kalır (fail-closed)
        assert await emergency_pause.is_emergency_paused(str(dbp)) is True
        paused = (await (await conn.execute(
            "SELECT emergency_paused FROM execution_state WHERE state_key='global'")).fetchone())[0]
        assert paused == 1, f"execution_state.emergency_paused=1 kalmalı: {paused}"
        n_trip = (await (await conn.execute(
            "SELECT COUNT(*) FROM execution_state_events WHERE event_type='TRIP'")).fetchone())[0]
        n_res = (await (await conn.execute(
            "SELECT COUNT(*) FROM execution_state_events WHERE event_type='RESOLVE'")).fetchone())[0]
        assert n_trip == 1, f"TRIP event 1 olmalı: {n_trip}"
        assert n_res == 0, f"blocked'ta RESOLVE event YAZILMAMALI: {n_res}"
    finally:
        await conn.close()


# ── 5) RED: force mode — var olan ama NON-TERMINAL intent'i bypass eder (audit'li) ──

@pytest.mark.asyncio
async def test_force_resolve_clears_nonterminal_intent_with_audit():
    """mode='force': var olan ama TERMINAL olmayan (RECOVERY_REQUIRED) intent için terminal
    önkoşulu BYPASS edilir → operatör override ile pause temizlenir + force RESOLVE event yazılır.
    RED (şimdilik): mode='force' guard'da ValueError fırlatır (feature missing)."""
    from execution import order_intent, emergency_pause
    from execution.emergency_pause import resolve_emergency_pause
    dbp = await _fresh_tmp_db()
    iid = await order_intent.create_intent(str(dbp), "tok-1", "BUY", 0.36, 25.0, slug="btc-x")
    # NON-TERMINAL recovery state (var olan ama stuck) → force'un gerçek senaryosu
    await order_intent.transition(str(dbp), iid, "RECOVERY_REQUIRED")
    await emergency_pause.set_emergency_pause(
        str(dbp), reason="task_h_recovery_write_failed:X", source="task_h", order_intent_id=iid)
    # RED: mode='force' henüz desteklenmiyor → ValueError; GREEN'de override clear + audit beklenir
    result = await resolve_emergency_pause(
        str(dbp), order_intent_id=iid, resolved_by="human:hasan",
        reason="manual override, intent stuck", mode="force")
    conn = await aiosqlite.connect(str(dbp))
    try:
        assert result["resolved"] is True, f"force clear etmeli: {result}"
        assert result["mode"] == "force", f"mode='force' olmalı: {result}"
        assert result["observed_intent_state"] == "RECOVERY_REQUIRED", f"observed: {result}"
        assert await emergency_pause.is_emergency_paused(str(dbp)) is False
        paused = (await (await conn.execute(
            "SELECT emergency_paused FROM execution_state WHERE state_key='global'")).fetchone())[0]
        assert paused == 0, f"force sonrası emergency_paused=0 olmalı: {paused}"
        n_trip = (await (await conn.execute(
            "SELECT COUNT(*) FROM execution_state_events WHERE event_type='TRIP'")).fetchone())[0]
        ev = await (await conn.execute(
            "SELECT old_state, new_state, force, verified, order_intent_id, observed_intent_state, "
            "resolved_by, reason FROM execution_state_events WHERE event_type='RESOLVE'")).fetchall()
        assert n_trip == 1, f"TRIP event 1 korunmalı: {n_trip}"
        assert len(ev) == 1, f"tek RESOLVE event olmalı: {ev}"
        old_state, new_state, force, verified, oi_id, observed, rb, rsn = ev[0]
        assert old_state == 1 and new_state == 0, f"old=1 new=0 olmalı: {ev[0]}"
        assert force == 1 and verified == 0, f"force=1 verified=0 olmalı: {ev[0]}"
        assert oi_id == iid, f"order_intent_id eşleşmeli: {oi_id} != {iid}"
        assert observed == "RECOVERY_REQUIRED", f"observed_intent_state kaydedilmeli: {observed}"
        assert rb == "human:hasan", f"resolved_by korunmalı: {rb}"
        assert rsn == "manual override, intent stuck", f"reason korunmalı: {rsn}"
    finally:
        await conn.close()


# ── 6) PIN (characterization): missing intent → HER İKİ mode fail-closed (force bile bypass etmez) ──

@pytest.mark.asyncio
async def test_missing_intent_fails_closed_in_all_modes():
    """Mevcut fail-closed guard'ını kilitler (RED değil): offending order_intent KAYDI YOK ise
    hem verified hem force REDDEDİLİR — pause AKTİF kalır, RESOLVE event YAZILMAZ, force bile
    var-olmayan intent'i BYPASS etmez."""
    from execution import emergency_pause
    from execution.emergency_pause import resolve_emergency_pause
    dbp = await _fresh_tmp_db()
    # create_intent ÇAĞRILMAZ → order_intents boş; pause sahte bir id'ye bağlanır
    missing_id = "ghost-uuid-999"
    await emergency_pause.set_emergency_pause(
        str(dbp), reason="task_h_recovery_write_failed:X", source="task_h",
        order_intent_id=missing_id)
    # Adım 1: verified → fail-closed
    verified_result = await resolve_emergency_pause(
        str(dbp), order_intent_id=missing_id, resolved_by="human:hasan",
        reason="missing intent test", mode="verified")
    assert verified_result["resolved"] is False, f"verified blocked olmalı: {verified_result}"
    assert verified_result["blocked"] is True, f"verified blocked=True: {verified_result}"
    assert "observed_intent_state" in verified_result, f"key olmalı: {verified_result}"
    assert verified_result["observed_intent_state"] is None, f"None olmalı: {verified_result}"
    assert await emergency_pause.is_emergency_paused(str(dbp)) is True
    # Adım 2: force → yine fail-closed (var-olmayan intent BYPASS edilmez)
    force_result = await resolve_emergency_pause(
        str(dbp), order_intent_id=missing_id, resolved_by="human:hasan",
        reason="missing intent test", mode="force")
    assert force_result["resolved"] is False, f"force blocked olmalı: {force_result}"
    assert force_result["blocked"] is True, f"force blocked=True: {force_result}"
    assert "observed_intent_state" in force_result, f"key olmalı: {force_result}"
    assert force_result["observed_intent_state"] is None, f"None olmalı: {force_result}"
    assert await emergency_pause.is_emergency_paused(str(dbp)) is True
    # Adım 3: state + audit — pause korunur, RESOLVE event hiç yazılmaz
    conn = await aiosqlite.connect(str(dbp))
    try:
        paused = (await (await conn.execute(
            "SELECT emergency_paused FROM execution_state WHERE state_key='global'")).fetchone())[0]
        assert paused == 1, f"emergency_paused=1 kalmalı: {paused}"
        n_trip = (await (await conn.execute(
            "SELECT COUNT(*) FROM execution_state_events WHERE event_type='TRIP'")).fetchone())[0]
        n_res = (await (await conn.execute(
            "SELECT COUNT(*) FROM execution_state_events WHERE event_type='RESOLVE'")).fetchone())[0]
        assert n_trip == 1, f"TRIP event 1 olmalı: {n_trip}"
        assert n_res == 0, f"missing intent'te RESOLVE event YAZILMAMALI: {n_res}"
    finally:
        await conn.close()
