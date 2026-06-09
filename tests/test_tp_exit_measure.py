"""tests/test_tp_exit_measure.py — Peak-time TP depth-walk telemetrisi TDD.

MFE +15/+20/+30% eşiği İLK geçildiğinde, o anki book ile realistic SELL depth-walk
(aggressive taker, bids ezerek) → tradable TP P&L. First-hit idempotent (unique).
Sadece paper/shadow; live execute'a bağlanmaz; fire-and-forget non-blocking.
"""
import asyncio
import sys
import os
import time
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── schema ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tp_exit_measurements_table():
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    async with conn.execute("PRAGMA table_info(tp_exit_measurements)") as cur:
        cols = {r[1] for r in await cur.fetchall()}
    await conn.close()
    for col in ("paper_id", "tp_level", "real_tradable_tp_pnl", "exit_slippage_pct",
                "exit_book_age_ms", "tp_hit_ts", "exit_depth_walk_source", "created_at"):
        assert col in cols, f"eksik kolon: {col}"


@pytest.mark.asyncio
async def test_tp_measurement_idempotent_unique():
    """Aynı paper_id+tp_level iki kez yazılsa → tek kayıt (restart-safe idempotency)."""
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        rec = {"paper_id": "p1", "slug": "s", "asset": "BTC", "action": "YES",
               "tp_level": 15, "real_tradable_tp_pnl": 0.10, "exit_slippage_pct": 0.02,
               "exit_book_age_ms": 0.0, "tp_hit_ts": "t", "exit_depth_walk_source": "rest_book",
               "created_at": "t"}
        await pt._write_tp_measurement(rec, dbp)
        await pt._write_tp_measurement(rec, dbp)  # ikinci kez — IGNORE
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT COUNT(*) FROM tp_exit_measurements WHERE paper_id='p1' AND tp_level=15") as c:
            n = (await c.fetchone())[0]
        await conn.close()
    assert n == 1, f"idempotency: 1 kayıt olmalı, {n} bulundu"


# ── depth-walk sell hesabı ───────────────────────────────────────────────────

def test_tp_sell_depth_walk_aggressive():
    """Bids ezerek (pahalı→ucuz) ağırlıklı satış fiyatı (4-tuple)."""
    from execution.paper_tracker import _depth_walk_sell
    book = {"bids": [{"price": "0.40", "size": "1"}, {"price": "0.60", "size": "1"},
                     {"price": "0.50", "size": "1"}]}
    avg, levels, filled, unfilled = _depth_walk_sell(book, shares=2.0)
    assert abs(avg - 0.55) < 1e-6
    assert levels == 2 and unfilled == 0.0


def test_tp_sell_empty_book():
    from execution.paper_tracker import _depth_walk_sell
    avg, levels, filled, unfilled = _depth_walk_sell({"bids": []}, shares=2.0)
    assert avg is None and unfilled == 2.0


# ── update_paper_position TP first-hit tetikleme ────────────────────────────

@pytest.mark.asyncio
async def test_tp_triggered_on_first_cross():
    """dd>=+15% ilk kez → tp15 ölçüm task'ı fırlatılır, state'e işlenir."""
    import execution.paper_tracker as pt
    created = []
    state = {"slug": "s", "asset": "BTC", "action": "YES", "entry_price": 0.50,
             "shares": 2.0, "position_usd": 1.25, "ref_price": 100.0,
             "yes_token_id": "y", "no_token_id": "n", "paper_id": "p1",
             "_opened_monotonic": time.monotonic() - 60, "_mfe_peak": 0.0,
             "_mae_trough": 0.0, "_breakeven_armed": False, "_model_exits": {},
             "_tp_hits": set(), "status": "open"}
    with patch("execution.paper_tracker._record_stop_event", new_callable=AsyncMock), \
         patch("asyncio.create_task", side_effect=lambda *a, **k: created.append(1)):
        # pm 0.58 → dd +16% → tp15 tetiklenir
        await pt.update_paper_position(state, pm_price=0.58, hl_price=101.0, secs=400, db_path=":memory:")
    assert 15 in state["_tp_hits"], "tp15 first-hit state'e işlenmeli"
    assert created, "tp ölçüm task'ı (create_task) fırlatılmalı"


@pytest.mark.asyncio
async def test_tp_not_retriggered_same_level():
    """tp15 bir kez hit olunca tekrar dd>=+15%'te YENİDEN tetiklenmez (idempotent state)."""
    import execution.paper_tracker as pt
    state = {"slug": "s", "asset": "BTC", "action": "YES", "entry_price": 0.50,
             "shares": 2.0, "position_usd": 1.25, "ref_price": 100.0,
             "yes_token_id": "y", "no_token_id": "n", "paper_id": "p1",
             "_opened_monotonic": time.monotonic() - 60, "_mfe_peak": 0.0,
             "_mae_trough": 0.0, "_breakeven_armed": False, "_model_exits": {},
             "_tp_hits": {15}, "status": "open"}  # tp15 zaten hit
    created = []
    with patch("execution.paper_tracker._record_stop_event", new_callable=AsyncMock), \
         patch("asyncio.create_task", side_effect=lambda *a, **k: created.append(1)):
        await pt.update_paper_position(state, pm_price=0.58, hl_price=101.0, secs=400, db_path=":memory:")
    assert not created, "tp15 tekrar tetiklenmemeli (fiyat dalgalanması)"


@pytest.mark.asyncio
async def test_tp_below_threshold_no_trigger():
    """dd < +15% → hiçbir tp tetiklenmez."""
    import execution.paper_tracker as pt
    state = {"slug": "s", "asset": "BTC", "action": "YES", "entry_price": 0.50,
             "shares": 2.0, "position_usd": 1.25, "ref_price": 100.0,
             "yes_token_id": "y", "no_token_id": "n", "paper_id": "p1",
             "_opened_monotonic": time.monotonic() - 60, "_mfe_peak": 0.0,
             "_mae_trough": 0.0, "_breakeven_armed": False, "_model_exits": {},
             "_tp_hits": set(), "status": "open"}
    created = []
    with patch("execution.paper_tracker._record_stop_event", new_callable=AsyncMock), \
         patch("asyncio.create_task", side_effect=lambda *a, **k: created.append(1)):
        await pt.update_paper_position(state, pm_price=0.55, hl_price=101.0, secs=400, db_path=":memory:")  # +10%
    assert not state["_tp_hits"]
    assert not created


# (Not: _measure_tp_exit → _measure_tp_ladder oldu; ladder testleri test_tp_size_ladder.py'de)

@pytest.mark.asyncio
async def test_measure_tp_ladder_book_error_fail_open():
    import execution.paper_tracker as pt
    async def boom(*a, **k): raise asyncio.TimeoutError("book")
    with patch("execution.paper_tracker.get_book", side_effect=boom), \
         patch("execution.paper_tracker._write_tp_ladder", new_callable=AsyncMock):
        # exception fırlatmamalı (fail-open)
        await pt._measure_tp_ladder("p1", "tok", 15, "s", "BTC", "YES",
                                    entry_price=0.50, observed_return=0.20, db_path=":memory:")
