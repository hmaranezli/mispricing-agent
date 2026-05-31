"""tests/test_db.py — db/ birim testleri. aiosqlite in-memory, sıfır sunucu."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
import aiosqlite
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
