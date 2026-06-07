"""tests/test_db_logger.py — db/logger.py Shadow Book v1 testleri."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import pytest
from db.logger import get_connection, log_shadow_candidate
from unittest.mock import patch, AsyncMock


def _finding(slug="btc-5m-shadow", seconds_remaining=270):
    return {
        "slug": slug, "asset": "BTC", "action": "YES",
        "fair_value": 0.75, "best_ask": 0.60, "best_bid": 0.58,
        "edge": 0.15, "seconds_remaining": seconds_remaining,
    }


@pytest.mark.asyncio
async def test_log_shadow_candidate_stores_rich_fields(tmp_path):
    """log_shadow_candidate shadow_candidates tablosuna tüm alanları yazmalı."""
    conn = await get_connection(tmp_path / "test.db")
    finding = _finding()
    await log_shadow_candidate(
        conn, finding,
        passed=False, veto_layer="risk", veto_reason="kelly=0",
        confidence_score=72.5, kelly_f=0.08,
    )
    async with conn.execute(
        "SELECT slug, asset, action, veto_layer, veto_reason, "
        "confidence_score, kelly_f, seconds_remaining "
        "FROM shadow_candidates WHERE slug=?",
        ("btc-5m-shadow",),
    ) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert row is not None, "shadow_candidates'a kayıt yazılmalı"
    assert row[0] == "btc-5m-shadow"
    assert row[1] == "BTC"
    assert row[2] == "YES"
    assert row[3] == "risk"
    assert row[4] == "kelly=0"
    assert abs(row[5] - 72.5) < 1e-6
    assert abs(row[6] - 0.08) < 1e-6
    assert row[7] == 270


@pytest.mark.asyncio
async def test_log_shadow_candidate_nullable_fields(tmp_path):
    """confidence_score / kelly_f geçilmeden çağrılabilmeli (eski call site uyumu)."""
    conn = await get_connection(tmp_path / "test2.db")
    finding = _finding(slug="eth-5m-compat")
    await log_shadow_candidate(conn, finding, passed=True)
    async with conn.execute(
        "SELECT confidence_score, kelly_f FROM shadow_candidates WHERE slug=?",
        ("eth-5m-compat",),
    ) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert row is not None
    assert row[0] is None
    assert row[1] is None


@pytest.mark.asyncio
async def test_log_shadow_candidate_separate_from_candidates(tmp_path):
    """shadow_candidates ve candidates birbirinden bağımsız tablolar."""
    conn = await get_connection(tmp_path / "test3.db")
    finding = _finding(slug="sol-5m-separate")
    await log_shadow_candidate(conn, finding, passed=False, veto_layer="gate", veto_reason="low_conf")
    # candidates tablosu boş olmalı (shadow ayrı tabloya gidiyor)
    async with conn.execute("SELECT COUNT(*) FROM candidates WHERE slug=?",
                            ("sol-5m-separate",)) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert row[0] == 0, "shadow_candidates'a yazılan kayıt candidates'a gitmemeli"


@pytest.mark.asyncio
async def test_run_council_creates_shadow_task_on_veto(tmp_path):
    """_run_council veto ettiğinde asyncio.create_task ile shadow log yaratmalı."""
    import main_loop as _ml

    conn = await get_connection(tmp_path / "test4.db")
    finding = _finding(slug="btc-shadow-council")
    created_tasks = []

    original_create_task = asyncio.create_task

    def capturing_create_task(coro, **kwargs):
        task = original_create_task(coro, **kwargs)
        created_tasks.append(task)
        return task

    with patch("main_loop.verify", new_callable=AsyncMock,
               return_value={"pass": False, "reason": "price_mismatch"}), \
         patch("main_loop.asyncio.create_task", side_effect=capturing_create_task):
        result = await _ml._run_council(
            finding, bankroll_usd=100.0, n_open=0,
            daily_loss_usd=0.0, conn=conn,
        )

    await asyncio.gather(*created_tasks, return_exceptions=True)
    assert result is None

    async with conn.execute(
        "SELECT veto_layer FROM shadow_candidates WHERE slug=?",
        ("btc-shadow-council",),
    ) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert row is not None, "veto sonrası shadow_candidates'a kayıt yazılmalı"
    assert row[0] == "verifier"
