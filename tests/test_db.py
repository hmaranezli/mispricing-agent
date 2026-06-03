"""tests/test_db.py — db/ birim testleri. aiosqlite in-memory, sıfır sunucu."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
import aiosqlite
from datetime import date, timedelta
from db.schema import init_schema
from db import logger


@pytest_asyncio.fixture
async def conn():
    async with aiosqlite.connect(":memory:") as db:
        await init_schema(db)
        yield db


# ── Schema ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_schema_creates_both_tables(conn):
    """init_schema sonrası candidates ve positions tabloları var."""
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) as cur:
        names = {row[0] for row in await cur.fetchall()}
    assert "candidates" in names
    assert "positions" in names


# ── Candidates ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_candidate_passed(conn):
    """Geçen aday: passed=1, veto_layer=None."""
    finding = {"slug": "btc-up-5min", "asset": "BTC", "action": "YES",
               "fair_value": 0.55, "best_ask": 0.35, "edge": 0.20}
    await logger.log_candidate(conn, finding, passed=True)
    async with conn.execute("SELECT passed, veto_layer FROM candidates") as cur:
        row = await cur.fetchone()
    assert row[0] == 1
    assert row[1] is None


@pytest.mark.asyncio
async def test_log_candidate_vetoed(conn):
    """Veto yiyen aday: passed=0, veto_layer ve veto_reason dolu."""
    finding = {"slug": "eth-down-15min", "asset": "ETH", "action": "NO",
               "fair_value": 0.45, "best_ask": 0.60, "edge": 0.05}
    await logger.log_candidate(conn, finding, passed=False,
                               veto_layer="risk", veto_reason="edge too small")
    async with conn.execute(
        "SELECT passed, veto_layer, veto_reason FROM candidates"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] == 0
    assert row[1] == "risk"
    assert "edge" in row[2]


@pytest.mark.asyncio
async def test_dry_run_flag_written(conn):
    """DRY_RUN=True iken candidates.dry_run=1."""
    finding = {"slug": "sol-up-1h", "asset": "SOL", "action": "YES",
               "fair_value": 0.60, "best_ask": 0.40, "edge": 0.20}
    await logger.log_candidate(conn, finding, passed=True)
    async with conn.execute("SELECT dry_run FROM candidates") as cur:
        row = await cur.fetchone()
    assert row[0] == 1


# ── Positions ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_position_open(conn):
    """Açılan pozisyon: positions tablosuna status='open' ile yazılır."""
    pos = {"position_id": "pos-001", "slug": "btc-up-5min", "asset": "BTC",
           "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
           "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.5,
           "opened_at": "2026-05-30T10:00:00+00:00"}
    await logger.log_position_open(conn, pos)
    async with conn.execute(
        "SELECT status, asset FROM positions WHERE position_id='pos-001'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] == "open"
    assert row[1] == "BTC"


@pytest.mark.asyncio
async def test_log_position_close(conn):
    """Kapanan pozisyon: status='closed', exit_reason ve pm_exit_price güncellenir."""
    pos = {"position_id": "pos-002", "slug": "eth-down-15min", "asset": "ETH",
           "action": "NO", "pm_entry_price": 0.60, "fair_value": 0.45,
           "position_usd": 20.0, "kelly_f": 0.12, "confidence_score": 78.0,
           "opened_at": "2026-05-30T10:00:00+00:00"}
    await logger.log_position_open(conn, pos)
    closed = {**pos, "pm_exit_price": 0.45, "exit_reason": "profit_target_hit",
              "closed_at": "2026-05-30T10:14:00+00:00", "status": "closed"}
    await logger.log_position_close(conn, closed)
    async with conn.execute(
        "SELECT status, exit_reason, pm_exit_price FROM positions WHERE position_id='pos-002'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] == "closed"
    assert row[1] == "profit_target_hit"
    assert abs(row[2] - 0.45) < 1e-6


@pytest.mark.asyncio
async def test_positions_schema_has_ref_price_and_edge(conn):
    """positions tablosu ref_price ve edge sütunlarına sahip olmalı."""
    async with conn.execute("PRAGMA table_info(positions)") as cur:
        cols = {row[1] for row in await cur.fetchall()}
    assert "ref_price" in cols, "positions tablosunda ref_price sütunu yok"
    assert "edge" in cols, "positions tablosunda edge sütunu yok"


@pytest.mark.asyncio
async def test_log_position_open_stores_ref_price_and_edge(conn):
    """log_position_open ref_price ve edge değerlerini DB'ye yazar."""
    pos = {"position_id": "pos-003", "slug": "sol-up-5min", "asset": "SOL",
           "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
           "ref_price": 150.0, "edge": 0.18,
           "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 80.0,
           "opened_at": "2026-05-30T10:00:00+00:00"}
    await logger.log_position_open(conn, pos)
    async with conn.execute(
        "SELECT ref_price, edge FROM positions WHERE position_id='pos-003'"
    ) as cur:
        row = await cur.fetchone()
    assert abs(row[0] - 150.0) < 1e-6, f"ref_price yanlış: {row[0]}"
    assert abs(row[1] - 0.18) < 1e-6, f"edge yanlış: {row[1]}"


@pytest.mark.asyncio
async def test_positions_schema_has_realized_pnl(conn):
    """positions tablosu realized_pnl sütununa sahip olmalı."""
    async with conn.execute("PRAGMA table_info(positions)") as cur:
        cols = {row[1] for row in await cur.fetchall()}
    assert "realized_pnl" in cols, "positions tablosunda realized_pnl sütunu yok"


@pytest.mark.asyncio
async def test_log_position_close_stores_realized_pnl(conn):
    """Kapanan pozisyonda realized_pnl hesaplanıp DB'ye yazılır.
    entry=0.40, exit=0.0, position_usd=50 → pnl = (0.0-0.40)/0.40*50 = -50.0
    """
    pos = {
        "position_id": "pos-pnl", "slug": "eth-down-15min", "asset": "ETH",
        "action": "NO", "pm_entry_price": 0.40, "fair_value": 0.55,
        "ref_price": 3000.0, "edge": 0.15,
        "position_usd": 50.0, "kelly_f": 0.12, "confidence_score": 78.0,
        "opened_at": "2026-05-31T10:00:00+00:00",
    }
    await logger.log_position_open(conn, pos)
    closed = {**pos, "pm_exit_price": 0.0, "exit_reason": "market_resolved",
              "closed_at": "2026-05-31T10:14:00+00:00", "status": "closed"}
    await logger.log_position_close(conn, closed)

    async with conn.execute(
        "SELECT realized_pnl FROM positions WHERE position_id='pos-pnl'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] is not None
    assert abs(row[0] - (-50.0)) < 1e-4


@pytest.mark.asyncio
async def test_log_position_close_realized_pnl_none_when_no_exit_price(conn):
    """pm_exit_price=None (market_expired) → realized_pnl=None."""
    pos = {
        "position_id": "pos-noexit", "slug": "btc-up-5min", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20,
        "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-05-31T10:00:00+00:00",
    }
    await logger.log_position_open(conn, pos)
    closed = {**pos, "pm_exit_price": None, "exit_reason": "market_expired",
              "closed_at": "2026-05-31T10:14:00+00:00", "status": "closed"}
    await logger.log_position_close(conn, closed)

    async with conn.execute(
        "SELECT realized_pnl FROM positions WHERE position_id='pos-noexit'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] is None


@pytest.mark.asyncio
async def test_load_closed_today_returns_only_todays(conn):
    """load_closed_today yalnızca bugünün UTC kapanışlarını döndürür, önceki günleri değil."""
    from db.logger import load_closed_today

    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    base = {
        "slug": "btc-up-5min", "asset": "BTC", "action": "YES",
        "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20,
        "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.0,
    }

    # Bugün kapanan
    pos_today = {**base, "position_id": "today-001",
                 "opened_at": f"{today}T09:00:00+00:00"}
    await logger.log_position_open(conn, pos_today)
    await logger.log_position_close(conn, {
        **pos_today, "pm_exit_price": 0.5, "exit_reason": "profit_target_hit",
        "closed_at": f"{today}T09:14:00+00:00", "status": "closed",
    })

    # Dün kapanan
    pos_yesterday = {**base, "position_id": "yest-001",
                     "opened_at": f"{yesterday}T09:00:00+00:00"}
    await logger.log_position_open(conn, pos_yesterday)
    await logger.log_position_close(conn, {
        **pos_yesterday, "pm_exit_price": 0.3, "exit_reason": "max_hold_time",
        "closed_at": f"{yesterday}T09:14:00+00:00", "status": "closed",
    })

    result = await load_closed_today(conn)
    assert len(result) == 1
    assert result[0]["position_id"] == "today-001"
    assert result[0]["closed_at"].startswith(today)
    assert result[0]["pm_exit_price"] == 0.5


@pytest.mark.asyncio
async def test_patch_position_resolution_writes_db(conn):
    """patch_position_resolution sonrası DB'de pm_exit_price, realized_pnl, exit_reason doğru."""
    await conn.execute(
        """INSERT INTO positions
               (position_id, ts_open, slug, asset, action, pm_entry_price,
                position_usd, kelly_f, confidence_score, status, dry_run)
           VALUES ('pid-heal-001', '2026-06-01T10:00:00+00:00', 'btc-up-5m',
                   'BTC', 'YES', 0.20, 50.0, 0.10, 75.0, 'closed', 1)"""
    )
    await conn.commit()

    from db.logger import patch_position_resolution
    await patch_position_resolution(conn, "pid-heal-001", 1.0, 200.0, "market_resolved_late")

    async with conn.execute(
        "SELECT pm_exit_price, realized_pnl, exit_reason FROM positions WHERE position_id='pid-heal-001'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] == 1.0
    assert abs(row[1] - 200.0) < 0.01
    assert row[2] == "market_resolved_late"


@pytest.mark.asyncio
async def test_patch_position_resolution_conn_none_is_noop():
    """conn=None → sessizce atlanır, exception yok."""
    from db.logger import patch_position_resolution
    await patch_position_resolution(None, "x", 1.0, 10.0, "market_resolved_late")  # no raise


@pytest.mark.asyncio
async def test_positions_schema_has_clob_columns(conn):
    """positions tablosu shares, order_id, yes_token_id, no_token_id sütunlarına sahip olmalı."""
    async with conn.execute("PRAGMA table_info(positions)") as cur:
        cols = {row[1] for row in await cur.fetchall()}
    assert "shares"       in cols, "shares sütunu yok"
    assert "order_id"     in cols, "order_id sütunu yok"
    assert "yes_token_id" in cols, "yes_token_id sütunu yok"
    assert "no_token_id"  in cols, "no_token_id sütunu yok"


@pytest.mark.asyncio
async def test_log_position_open_stores_clob_fields(conn):
    """log_position_open shares, order_id, yes_token_id, no_token_id alanlarını yazar."""
    pos = {
        "position_id": "clob-001", "slug": "btc-up-5min", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20,
        "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-06-01T10:00:00+00:00",
        "shares": 71.43, "order_id": "ord-abc123",
        "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222",
    }
    await logger.log_position_open(conn, pos)
    async with conn.execute(
        "SELECT shares, order_id, yes_token_id, no_token_id FROM positions WHERE position_id='clob-001'"
    ) as cur:
        row = await cur.fetchone()
    assert abs(row[0] - 71.43) < 0.01
    assert row[1] == "ord-abc123"
    assert row[2] == "yes-tok-111"
    assert row[3] == "no-tok-222"


@pytest.mark.asyncio
async def test_positions_has_entry_exit_hl_price_columns():
    """positions tablosunda entry_hl_price ve exit_hl_price kolonları olmalı."""
    async with aiosqlite.connect(":memory:") as db:
        await init_schema(db)
        async with db.execute("PRAGMA table_info(positions)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
    assert "entry_hl_price" in cols, "entry_hl_price kolonu eksik"
    assert "exit_hl_price" in cols, "exit_hl_price kolonu eksik"


@pytest.mark.asyncio
async def test_log_position_open_saves_entry_hl_price(conn):
    """log_position_open → entry_hl_price DB'ye kaydedilmeli."""
    pos = {
        "position_id": "hl-001", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-06-03T10:00:00+00:00",
        "entry_hl_price": 66500.0,
    }
    await logger.log_position_open(conn, pos)
    async with conn.execute(
        "SELECT entry_hl_price FROM positions WHERE position_id='hl-001'"
    ) as cur:
        row = await cur.fetchone()
    assert row is not None
    assert abs(row[0] - 66500.0) < 0.01, f"entry_hl_price={row[0]}, beklenen 66500.0"


@pytest.mark.asyncio
async def test_log_position_close_saves_exit_hl_price(conn):
    """log_position_close → exit_hl_price DB'ye kaydedilmeli."""
    pos = {
        "position_id": "hl-002", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-06-03T10:00:00+00:00",
        "entry_hl_price": 66500.0,
    }
    closed = {
        **pos, "status": "closed", "exit_reason": "thesis_invalidated",
        "closed_at": "2026-06-03T10:14:00+00:00",
        "pm_exit_price": 0.72, "exit_hl_price": 66502.0,
    }
    await logger.log_position_open(conn, pos)
    await logger.log_position_close(conn, closed)
    async with conn.execute(
        "SELECT exit_hl_price FROM positions WHERE position_id='hl-002'"
    ) as cur:
        row = await cur.fetchone()
    assert row is not None
    assert abs(row[0] - 66502.0) < 0.01, f"exit_hl_price={row[0]}, beklenen 66502.0"


@pytest.mark.asyncio
async def test_patch_position_resolution_saves_exit_hl_price(conn):
    """patch_position_resolution exit_hl_price ile çağrılınca DB'ye kaydedilmeli."""
    pos = {
        "position_id": "hl-003", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-06-03T10:00:00+00:00",
    }
    await logger.log_position_open(conn, pos)
    await conn.execute(
        "UPDATE positions SET status='closed', pm_exit_price=NULL WHERE position_id='hl-003'"
    )
    await conn.commit()
    await logger.patch_position_resolution(conn, "hl-003", 1.0, 1.07, exit_hl_price=66510.0)
    async with conn.execute(
        "SELECT exit_hl_price FROM positions WHERE position_id='hl-003'"
    ) as cur:
        row = await cur.fetchone()
    assert row is not None
    assert abs(row[0] - 66510.0) < 0.01
