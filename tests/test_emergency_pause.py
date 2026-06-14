"""tests/test_emergency_pause.py — Faz 2c-2: kill-switch persist + runtime block (TDD).

Reconciliation'ın ürettiği emergency_pause=True artık SADECE rapor değil — DB'de persist
edilen GERÇEK runtime blokaj. Çekirdek invariantlar:
  - execution_state.emergency_paused DB'de persist (restart sonrası kalıcı).
  - execute() girişinde paused=True → network call (create_market_order/post_order) YOK.
  - Otomatik temizlik YASAK → yalnız manuel clear_emergency_pause() (insan onayı).
  - DB okunamazsa FAIL-CLOSED → paused say (network call yok).
  - Scream on Death: pause tetiklendiğinde CRITICAL log (reason/source/order_intent_id).
  - Set idempotent → ikinci set mevcut pause'u (ilk reason/source/created_at) BOZMAZ.
live=0, canlı emir yok.
"""
import sys
import os
import logging
import tempfile
from pathlib import Path

import aiosqlite
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def _fresh_db():
    """init_schema uygulanmış temiz temp DB yolu döner."""
    d = tempfile.mkdtemp()
    dbp = Path(d) / "t.db"
    from db.schema import init_schema
    conn = await aiosqlite.connect(str(dbp))
    await init_schema(conn)
    await conn.close()
    return dbp


# ── Persist + read ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_and_read_emergency_pause():
    """set → is_emergency_paused True + record alanları dolu (reason/source/order_intent_id)."""
    from execution.emergency_pause import (
        set_emergency_pause, is_emergency_paused, get_pause_record)
    dbp = await _fresh_db()
    assert await is_emergency_paused(dbp) is False          # başlangıç: aktif değil
    await set_emergency_pause(dbp, reason="ambiguous_overfill",
                              source="reconcile", order_intent_id="i-1")
    assert await is_emergency_paused(dbp) is True
    rec = await get_pause_record(dbp)
    assert rec["emergency_paused"] == 1
    assert rec["reason"] == "ambiguous_overfill"
    assert rec["source"] == "reconcile"
    assert rec["order_intent_id"] == "i-1"
    assert rec["created_at"] and rec["updated_at"]          # timestamp'ler dolu


@pytest.mark.asyncio
async def test_pause_persists_across_restart():
    """set sonrası YENİ bağlantı (restart simülasyonu) → hâlâ paused."""
    from execution.emergency_pause import set_emergency_pause, is_emergency_paused
    dbp = await _fresh_db()
    await set_emergency_pause(dbp, reason="r", source="reconcile")
    # her çağrı kendi bağlantısını açar → bu çağrı 'restart sonrası okuma'yı temsil eder
    assert await is_emergency_paused(dbp) is True


@pytest.mark.asyncio
async def test_no_auto_clear():
    """Tekrarlı okuma pause'u otomatik temizlemez."""
    from execution.emergency_pause import set_emergency_pause, is_emergency_paused
    dbp = await _fresh_db()
    await set_emergency_pause(dbp, reason="r", source="reconcile")
    for _ in range(3):
        assert await is_emergency_paused(dbp) is True       # kendiliğinden açılmaz


@pytest.mark.asyncio
async def test_clear_emergency_pause_manual_admin():
    """clear_emergency_pause() (admin/insan) → paused False; otomatik reset yoktur."""
    from execution.emergency_pause import (
        set_emergency_pause, is_emergency_paused, clear_emergency_pause)
    dbp = await _fresh_db()
    await set_emergency_pause(dbp, reason="r", source="reconcile", order_intent_id="i-1")
    await clear_emergency_pause(dbp, cleared_by="human:hasan")
    assert await is_emergency_paused(dbp) is False


@pytest.mark.asyncio
async def test_set_idempotent_preserves_original():
    """İkinci set ilk pause'u BOZMAZ — reason/source/order_intent_id/created_at korunur."""
    from execution.emergency_pause import set_emergency_pause, get_pause_record
    dbp = await _fresh_db()
    await set_emergency_pause(dbp, reason="first", source="reconcile", order_intent_id="i-1")
    rec1 = await get_pause_record(dbp)
    await set_emergency_pause(dbp, reason="second", source="other", order_intent_id="i-2")
    rec2 = await get_pause_record(dbp)
    assert rec2["reason"] == "first"                        # ilk neden korunur
    assert rec2["source"] == "reconcile"
    assert rec2["order_intent_id"] == "i-1"
    assert rec2["created_at"] == rec1["created_at"]         # ilk created_at değişmez


@pytest.mark.asyncio
async def test_fail_closed_when_db_unreadable():
    """DB okunamazsa (tablo/şema/query hatası) FAIL-CLOSED → paused say."""
    from execution.emergency_pause import is_emergency_paused
    # init_schema UYGULANMAMIŞ boş DB → execution_state tablosu yok → OperationalError
    d = tempfile.mkdtemp()
    dbp = Path(d) / "no_schema.db"
    conn = await aiosqlite.connect(str(dbp)); await conn.close()   # boş dosya, tablo yok
    assert await is_emergency_paused(dbp) is True           # fail-closed


@pytest.mark.asyncio
async def test_fail_closed_when_db_path_bogus():
    """Geçersiz/erişilemez DB yolu → fail-closed True."""
    from execution.emergency_pause import is_emergency_paused
    bogus = Path(tempfile.mkdtemp()) / "nope" / "deep" / "missing.db"  # parent yok
    assert await is_emergency_paused(bogus) is True


@pytest.mark.asyncio
async def test_scream_on_death_critical_log(caplog):
    """Pause tetiklendiğinde CRITICAL log + reason/source/order_intent_id görünür."""
    from execution.emergency_pause import set_emergency_pause
    dbp = await _fresh_db()
    with caplog.at_level(logging.CRITICAL, logger="execution.emergency_pause"):
        await set_emergency_pause(dbp, reason="ambiguous_overfill",
                                  source="reconcile", order_intent_id="i-99")
    crit = [r for r in caplog.records if r.levelno >= logging.CRITICAL]
    assert crit, "pause tetiklenince CRITICAL log basılmalı"
    blob = " ".join(r.getMessage() for r in crit)
    assert "ambiguous_overfill" in blob and "reconcile" in blob and "i-99" in blob


# ── execute() runtime block (network call yok) ────────────────────────────────

def _finding(action="YES"):
    return {"question": "Will BTC go up?", "asset": "BTC", "action": action,
            "fair_value": 0.55, "ref_price": 95000.0, "cur_price": 96000.0,
            "best_ask": 0.35, "best_bid": 0.33, "seconds_remaining": 900,
            "edge": 0.20, "slug": "btc-up-5m-test", "neg_risk": False,
            "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222"}


@pytest.mark.asyncio
async def test_execute_blocked_when_paused_no_network_call():
    """paused=True → execute None döner; create_market_order/post_order/get_quote ÇAĞRILMAZ."""
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = {"status": "matched", "orderID": "x",
                                           "takingAmount": "1", "makingAmount": "1"}
    gq = AsyncMock()
    with patch("execution.clob_executor.is_emergency_paused",
               new_callable=AsyncMock, return_value=True), \
         patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", gq):
        from execution.clob_executor import execute
        result = await execute(_finding("YES"),
                               {"pass": True, "confidence_score": 82.5},
                               {"pass": True, "position_usd": 25.0, "kelly_f": 0.15}, [])
    assert result is None
    fake_client.create_market_order.assert_not_called()     # network call YOK
    fake_client.post_order.assert_not_called()
    gq.assert_not_called()                                  # quote bile çekilmez


@pytest.mark.asyncio
async def test_execute_proceeds_when_not_paused():
    """paused=False → normal yol; get_quote ve create_market_order çağrılır."""
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = {"status": "matched", "orderID": "ord-abc",
                                           "takingAmount": "71.43", "makingAmount": "25.00"}
    from data.orderbook_snapshot import OrderbookSnapshot
    import time as _t
    snap = OrderbookSnapshot(bid=0.33, ask=0.35, bid_size=1e4, ask_size=1e4,
                             source="rest_book", ts=_t.time())
    with patch("execution.clob_executor.is_emergency_paused",
               new_callable=AsyncMock, return_value=False), \
         patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock, return_value=snap):
        from execution.clob_executor import execute
        result = await execute(_finding("YES"),
                               {"pass": True, "confidence_score": 82.5},
                               {"pass": True, "position_usd": 25.0, "kelly_f": 0.15}, [])
    assert result is not None
    fake_client.create_market_order.assert_called_once()


# ── D6-T2: on_trip callback seam (operatör notify wiring noktası) ─────────────

@pytest.mark.asyncio
async def test_set_emergency_pause_trip_invokes_on_trip_callback():
    """D6-T2 seam C: set_emergency_pause additive `on_trip` callback'i YALNIZ fresh 0→1 trip'te,
    bir kez, reason/source/order_intent_id ile çağırır. Idempotent ikinci çağrı (zaten paused)
    callback'i TEKRAR çağırmaz. Hard coupling YOK (callback enjekte; notifier import edilmez).
    Network/Telegram yok; tmp DB. İlk RED: imza `on_trip` kabul etmiyor → TypeError."""
    from execution.emergency_pause import set_emergency_pause
    dbp = await _fresh_db()

    calls = []
    def spy(reason, source, order_intent_id=None):
        calls.append((reason, source, order_intent_id))

    await set_emergency_pause(dbp, reason="DB_INCONSISTENCY", source="recovery_ladder",
                              order_intent_id="iid-x", on_trip=spy)
    assert calls == [("DB_INCONSISTENCY", "recovery_ladder", "iid-x")], \
        f"fresh trip callback bir kez: {calls}"

    # Idempotent ikinci çağrı (zaten paused) → callback TEKRAR çağrılmamalı.
    await set_emergency_pause(dbp, reason="DB_INCONSISTENCY", source="recovery_ladder",
                              order_intent_id="iid-x", on_trip=spy)
    assert calls == [("DB_INCONSISTENCY", "recovery_ladder", "iid-x")], \
        f"idempotent re-trip callback tekrar ÇAĞIRMAMALI: {calls}"
