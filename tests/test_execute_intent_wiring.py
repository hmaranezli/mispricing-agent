"""tests/test_execute_intent_wiring.py — Faz 2c-3 execute() intent-wiring.

Task 0: schema + lineage kolonu (positions.order_intent_id) + execution_state
init_schema idempotency/readback. Hiçbir test gerçek network/canlı DB kullanmaz —
yalnız tmp DB. execute()/post_order wiring BU dosyada henüz YOK (sonraki task'lar).
"""
import sys
import os
import logging
import sqlite3
import tempfile
from pathlib import Path

from decimal import Decimal
from unittest.mock import patch, MagicMock, AsyncMock

import aiosqlite
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── execute() test helper'ları (test_clob_executor deseni, lokal kopya) ──────

def _qask(p):
    """Entry quote (ask). p=ask, bid=p-0.02."""
    from data.orderbook_snapshot import OrderbookSnapshot
    import time as _t
    return OrderbookSnapshot(bid=round(p - 0.02, 4), ask=p, bid_size=1e4, ask_size=1e4,
                             source="rest_book", ts=_t.time())


def _finding(action="YES"):
    return {
        "question": "Will BTC go up?", "asset": "BTC", "action": action,
        "fair_value": 0.55, "ref_price": 95000.0, "cur_price": 96000.0,
        "best_ask": 0.35, "best_bid": 0.33, "seconds_remaining": 900,
        "edge": 0.20, "slug": "btc-up-5m-test", "neg_risk": False,
        "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222",
    }


def _gate():
    return {"pass": True, "confidence_score": 82.5, "action_taken": "open"}


def _risk():
    return {"pass": True, "position_usd": 25.0, "kelly_f": 0.15,
            "kelly_fraction_applied": 0.25, "reason": ""}


def _fake_matched_resp():
    return {"status": "matched", "success": True, "orderID": "ord-abc",
            "takingAmount": "71.43", "makingAmount": "25.00"}


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


# ── Task A: has_unresolved_intent EARLY-STOP guard ──────────────────────────

@pytest.mark.asyncio
async def test_unresolved_intent_early_stops_before_quote_and_submit():
    """Aynı token için çözülmemiş intent varsa execute() EN ERKEN None döner:
    quote/prevalidation YOK, yeni intent YOK, create_market_order/post_order YOK."""
    import execution.order_intent as oi
    from execution.order_intent import create_intent, transition

    dbp = await _fresh_db()
    finding = _finding("YES")
    token_id = finding["yes_token_id"]
    # Bu token için çözülmemiş (SUBMITTED_UNKNOWN) intent seed et
    iid = await create_intent(dbp, token_id=token_id, side="BUY",
                              intended_price=0.35, intended_size=25.0, slug=finding["slug"])
    await transition(dbp, iid, "SUBMITTED_UNKNOWN")

    get_quote_spy = AsyncMock(return_value=_qask(0.35))
    clp_spy = MagicMock(return_value=(Decimal("0.36"), None))
    create_intent_spy = AsyncMock(return_value="should-not-be-created")
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()

    with patch.object(oi, "DB_FILE", str(dbp)), \
         patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock,
               return_value=False), \
         patch("execution.clob_executor.get_quote", get_quote_spy), \
         patch("execution.clob_executor.compute_limit_price", clp_spy), \
         patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.order_intent.create_intent", create_intent_spy):
        from execution.clob_executor import execute
        result = await execute(finding, _gate(), _risk(), [])

    assert result is None, "unresolved intent → execute None dönmeli (position yok)"
    get_quote_spy.assert_not_called()                 # quote/prevalidation'a girilmedi
    clp_spy.assert_not_called()                       # compute_limit_price'a girilmedi
    create_intent_spy.assert_not_called()             # yeni intent yaratılmadı
    fake_client.create_market_order.assert_not_called()
    fake_client.post_order.assert_not_called()         # submit YOK


@pytest.mark.asyncio
async def test_execute_default_path_is_isolated_never_live():
    """KANIT: DB_FILE'ı manuel patch'lemeyen execute() (test_clob_executor deseni) CANLI
    logs/mispricing.db'yi ASLA okumaz — conftest izole tmp'ye yönlendirir. execute() içindeki
    tüm aiosqlite.connect path'leri kaydedilir; canlı path görülürse test FAIL eder."""
    import execution.order_intent as oi
    import db.logger
    from execution.order_intent import create_intent, transition

    # conftest oi.DB_FILE'ı izole tmp'ye yönlendirdi; gerçek canlı path db.logger'da (patch'siz).
    isolated = os.path.abspath(str(oi.DB_FILE))
    live = os.path.abspath(str(db.logger.DB_FILE))
    assert isolated != live, "conftest default-path'i izole tmp'ye yönlendirmeli"
    assert live.endswith("logs/mispricing.db"), f"canlı path beklenen değil: {live}"

    finding = _finding("YES")
    token_id = finding["yes_token_id"]
    # Default path'in (oi.DB_FILE = izole tmp) işaret ettiği DB'ye unresolved intent seed et
    iid = await create_intent(None, token_id=token_id, side="BUY",
                              intended_price=0.35, intended_size=25.0, slug=finding["slug"])
    await transition(None, iid, "SUBMITTED_UNKNOWN")

    opened: list[str] = []
    real_connect = aiosqlite.connect

    def _recording_connect(database, *a, **k):
        opened.append(os.path.abspath(str(database)))
        return real_connect(database, *a, **k)

    get_quote_spy = AsyncMock(return_value=_qask(0.35))
    fake_client = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()

    with patch("aiosqlite.connect", _recording_connect), \
         patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock,
               return_value=False), \
         patch("execution.clob_executor.get_quote", get_quote_spy), \
         patch("execution.clob_executor.get_client", return_value=fake_client):
        from execution.clob_executor import execute
        result = await execute(finding, _gate(), _risk(), [])

    assert result is None
    assert live not in opened, f"CANLI DB OKUNDU — KABUL EDİLEMEZ: {live} ∈ {opened}"
    assert isolated in opened, f"izole tmp DB okunmalıydı (non-vacuous): {opened}"
    get_quote_spy.assert_not_called()                  # Task A invariant: quote yok
    fake_client.post_order.assert_not_called()          # Task A invariant: submit yok


# ── Task B: network öncesi create_intent + SUBMITTED_UNKNOWN commit sınırı ───

@pytest.mark.asyncio
async def test_intent_committed_submitted_unknown_before_post_order():
    """COMMIT SINIRI KANITI: post_order mock'u çağrıldığı AN, AYRI bir sqlite3 connection ile
    readback yapılır; intent'in DB'ye SUBMITTED_UNKNOWN olarak commit edilmiş olduğu görülmeli.
    RED: mevcut kodda network öncesi intent lifecycle bağlı değil → readback'te satır yok."""
    import sqlite3
    import execution.order_intent as oi

    finding = _finding("YES")
    token_id = finding["yes_token_id"]
    db_path = str(oi.DB_FILE)  # conftest izole tmp (order_intents tablosu mevcut)

    captured = {"readback_ran": False, "status_at_network": "NO_ROW", "rows_at_network": -1}

    def _post_order_readback(*a, **k):
        # NETWORK SINIRI — bu noktada intent SUBMITTED_UNKNOWN olarak commit edilmiş OLMALI.
        c = sqlite3.connect(db_path)  # AYRI connection (commit görünürlüğü kanıtı)
        try:
            rows = c.execute(
                "SELECT status FROM order_intents WHERE market_token_id=?", (token_id,)
            ).fetchall()
        finally:
            c.close()
        captured["readback_ran"] = True
        captured["rows_at_network"] = len(rows)
        captured["status_at_network"] = rows[0][0] if rows else None
        return _fake_matched_resp()

    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.side_effect = _post_order_readback

    with patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock,
               return_value=False), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock,
               return_value=_qask(0.35)), \
         patch("execution.clob_executor.get_client", return_value=fake_client):
        from execution.clob_executor import execute
        await execute(finding, _gate(), _risk(), [])

    # Non-vacuous: readback gerçekten çalıştı + post_order sınırına gelindi
    assert captured["readback_ran"] is True, "post_order readback çalışmadı (sınıra gelinmedi)"
    fake_client.post_order.assert_called_once()
    # Commit sınırı: network anında intent SUBMITTED_UNKNOWN olarak DB'de görünür olmalı
    assert captured["rows_at_network"] == 1, \
        f"network öncesi tam 1 intent commit edilmeli: rows={captured['rows_at_network']}"
    assert captured["status_at_network"] == "SUBMITTED_UNKNOWN", \
        f"network anında intent SUBMITTED_UNKNOWN commit'li olmalı: {captured['status_at_network']}"


# ── Task C/D: create_intent / transition fail → HARD ABORT (submit YOK) ──────

@pytest.mark.asyncio
async def test_create_intent_fail_hard_aborts_no_submit(caplog):
    """Task C: create_intent raise → execute None döner, post_order/create_market_order YOK,
    ERROR/CRITICAL log var. RED: try/except yok → execute raise eder (hard-abort değil)."""
    create_intent_boom = AsyncMock(side_effect=sqlite3.OperationalError("disk I/O error"))
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()

    raised = None
    with caplog.at_level(logging.ERROR, logger="execution.clob_executor"), \
         patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock,
               return_value=False), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock,
               return_value=_qask(0.35)), \
         patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.order_intent.create_intent", create_intent_boom):
        from execution.clob_executor import execute
        try:
            result = await execute(_finding("YES"), _gate(), _risk(), [])
        except Exception as ex:
            raised, result = ex, "RAISED"

    assert raised is None, f"create_intent fail → hard-abort (None) olmalı, raise ETMEMELİ: {raised}"
    assert result is None
    fake_client.create_market_order.assert_not_called()
    fake_client.post_order.assert_not_called()             # submit YOK
    errs = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errs, "create_intent fail → ERROR/CRITICAL log basılmalı"


@pytest.mark.asyncio
async def test_transition_fail_hard_aborts_intent_stays_created(caplog):
    """Task D: transition→SUBMITTED_UNKNOWN raise → execute None, submit YOK, ERROR/CRITICAL log;
    intent INTENT_CREATED'de kalır = 'never submitted' (2c-4 blocker). RED: try/except yok."""
    import execution.order_intent as oi
    finding = _finding("YES")
    token_id = finding["yes_token_id"]
    db_path = str(oi.DB_FILE)  # conftest izole tmp

    transition_boom = AsyncMock(side_effect=sqlite3.OperationalError("database is locked"))
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()

    raised = None
    with caplog.at_level(logging.ERROR, logger="execution.clob_executor"), \
         patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock,
               return_value=False), \
         patch("execution.clob_executor.get_quote", new_callable=AsyncMock,
               return_value=_qask(0.35)), \
         patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.order_intent.transition", transition_boom):
        from execution.clob_executor import execute
        try:
            result = await execute(finding, _gate(), _risk(), [])
        except Exception as ex:
            raised, result = ex, "RAISED"

    assert raised is None, f"transition fail → hard-abort (None) olmalı, raise ETMEMELİ: {raised}"
    assert result is None
    fake_client.create_market_order.assert_not_called()
    fake_client.post_order.assert_not_called()             # submit YOK
    # Intent INTENT_CREATED'de kalmalı (never submitted)
    c = sqlite3.connect(db_path)
    try:
        rows = c.execute(
            "SELECT status FROM order_intents WHERE market_token_id=?", (token_id,)).fetchall()
    finally:
        c.close()
    assert rows == [("INTENT_CREATED",)], f"transition fail → intent INTENT_CREATED kalmalı: {rows}"
    errs = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errs, "transition fail → ERROR/CRITICAL log basılmalı"
    blob = " ".join(r.getMessage() for r in errs)
    assert "INTENT_CREATED" in blob or "never" in blob.lower(), \
        f"log 'never submitted' / INTENT_CREATED işaretlemeli: {blob}"


# ── Fail-Closed Hardening: has_unresolved_intent DB-read fail → fail-closed ──

@pytest.mark.asyncio
async def test_unresolved_check_db_fail_is_fail_closed(caplog):
    """has_unresolved_intent DB-read'de raise ederse execute() FAIL-CLOSED durur: crash YOK,
    None döner, hiçbir aşamaya (quote/prevalidation/create_intent/submit) girilmez, anlamlı log.
    RED: guard çağrısı try/except'siz → execute raise eder."""
    check_boom = AsyncMock(side_effect=sqlite3.OperationalError("db unreadable"))
    get_quote_spy = AsyncMock(return_value=_qask(0.35))
    clp_spy = MagicMock(return_value=(Decimal("0.36"), None))
    create_intent_spy = AsyncMock(return_value="should-not-be-created")
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.return_value = _fake_matched_resp()

    raised = None
    with caplog.at_level(logging.ERROR, logger="execution.clob_executor"), \
         patch("execution.clob_executor.is_emergency_paused", new_callable=AsyncMock,
               return_value=False), \
         patch("execution.order_intent.has_unresolved_intent", check_boom), \
         patch("execution.clob_executor.get_quote", get_quote_spy), \
         patch("execution.clob_executor.compute_limit_price", clp_spy), \
         patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.order_intent.create_intent", create_intent_spy):
        from execution.clob_executor import execute
        try:
            result = await execute(_finding("YES"), _gate(), _risk(), [])
        except Exception as ex:
            raised, result = ex, "RAISED"

    assert raised is None, f"unresolved-check fail → fail-closed (None) olmalı, raise ETMEMELİ: {raised}"
    assert result is None
    get_quote_spy.assert_not_called()                  # quote'a girilmedi
    clp_spy.assert_not_called()                        # compute_limit_price'a girilmedi
    create_intent_spy.assert_not_called()              # yeni intent yok
    fake_client.create_market_order.assert_not_called()
    fake_client.post_order.assert_not_called()          # submit YOK
    errs = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errs, "unresolved-check fail → ERROR/CRITICAL log basılmalı"
    blob = " ".join(r.getMessage() for r in errs).lower()
    assert "unresolved" in blob and "fail-closed" in blob and "abort" in blob, \
        f"log 'unresolved intent check failed / fail-closed / aborting' anlamı içermeli: {blob}"
