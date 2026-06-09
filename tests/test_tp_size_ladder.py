"""tests/test_tp_size_ladder.py — Size-ladder exit depth-walk + conservative TP TDD.

Her TP first-hit anında $1.25/$10/$25/$50/$100 notional SELL depth-walk.
Partial fill → P&L NULL (fail). conservative=min(real,ideal). cadence_artifact_flag.
Sadece paper/shadow; live'a bağlanmaz. Idempotent UNIQUE(paper_id,tp_level,notional).
"""
import asyncio
import sys
import os
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── depth_walk_sell partial-fill aware (4-tuple) ────────────────────────────

def test_depth_walk_sell_complete():
    from execution.paper_tracker import _depth_walk_sell
    book = {"bids": [{"price": "0.60", "size": "10"}]}
    avg, levels, filled, unfilled = _depth_walk_sell(book, shares=2.0)
    assert avg == 0.60 and levels == 1 and filled == 2.0 and unfilled == 0.0


def test_depth_walk_sell_partial():
    from execution.paper_tracker import _depth_walk_sell
    # toplam 3 share var, 10 istiyoruz → 7 unfilled
    book = {"bids": [{"price": "0.60", "size": "2"}, {"price": "0.50", "size": "1"}]}
    avg, levels, filled, unfilled = _depth_walk_sell(book, shares=10.0)
    assert filled == 3.0 and unfilled == 7.0


def test_depth_walk_sell_multi_level():
    from execution.paper_tracker import _depth_walk_sell
    book = {"bids": [{"price": "0.60", "size": "1"}, {"price": "0.40", "size": "100"}]}
    avg, levels, filled, unfilled = _depth_walk_sell(book, shares=2.0)
    assert levels == 2 and unfilled == 0.0
    assert abs(avg - 0.50) < 1e-6  # (0.60+0.40)/2


# ── tradable capacity ────────────────────────────────────────────────────────

def test_tradable_capacity():
    from execution.paper_tracker import _tradable_capacity
    # ideal_tp_price=0.55; bids>=0.55 absorbe: 0.60×10=6.0, 0.58×5=2.9 → 8.9; 0.50 dahil değil
    book = {"bids": [{"price": "0.60", "size": "10"}, {"price": "0.58", "size": "5"},
                     {"price": "0.50", "size": "100"}]}
    cap = _tradable_capacity(book, ideal_tp_price=0.55)
    assert abs(cap - 8.9) < 1e-6


# ── cadence artifact + conservative ─────────────────────────────────────────

def test_cadence_artifact_flag_overshoot():
    from execution.paper_tracker import _cadence_flag
    # observed +26%, target +15% → overshoot 11pp > 5 → True
    assert _cadence_flag(observed_return_pct=0.26, tp_level=15, real_pnl=0.3, ideal_pnl=0.188) is True


def test_cadence_artifact_flag_real_exceeds():
    from execution.paper_tracker import _cadence_flag
    # overshoot küçük ama real %20+ > ideal → True
    assert _cadence_flag(observed_return_pct=0.16, tp_level=15, real_pnl=0.30, ideal_pnl=0.188) is True


def test_cadence_artifact_flag_clean():
    from execution.paper_tracker import _cadence_flag
    assert _cadence_flag(observed_return_pct=0.16, tp_level=15, real_pnl=0.19, ideal_pnl=0.188) is False


def test_conservative_caps_real_to_ideal():
    from execution.paper_tracker import _conservative_pnl
    # real > ideal → ideal'e cap
    assert _conservative_pnl(real_pnl=0.70, ideal_pnl=0.375, complete=True) == 0.375
    # real < ideal → real
    assert _conservative_pnl(real_pnl=0.10, ideal_pnl=0.375, complete=True) == 0.10
    # partial → None
    assert _conservative_pnl(real_pnl=None, ideal_pnl=0.375, complete=False) is None


# ── _measure_tp_ladder: 5 size, partial→NULL ───────────────────────────────

@pytest.mark.asyncio
async def test_ladder_produces_all_sizes():
    import execution.paper_tracker as pt
    written = []
    async def fake_write(rec, db_path): written.append(rec)
    # derin book: tüm size'lar dolar
    book = {"bids": [{"price": "0.60", "size": "100000"}]}
    with patch("execution.paper_tracker.get_book", new_callable=AsyncMock, return_value=book), \
         patch("execution.paper_tracker._write_tp_ladder", side_effect=fake_write):
        await pt._measure_tp_ladder("p1", "tok", 15, "btc-updown-15m-1", "BTC", "YES",
                                    entry_price=0.50, observed_return=0.20,
                                    shares_unused=0, pos_usd_unused=0, db_path=":memory:")
    sizes = sorted(r["simulated_exit_notional_usd"] for r in written)
    assert sizes == [1.25, 10, 25, 50, 100], f"5 size tier üretilmeli, {sizes}"
    for r in written:
        assert r["exit_fill_complete"] == 1  # derin book → hepsi complete


@pytest.mark.asyncio
async def test_ladder_partial_fill_null_pnl():
    import execution.paper_tracker as pt
    written = []
    async def fake_write(rec, db_path): written.append(rec)
    # sığ book: sadece $1.25 dolar, büyükler partial
    book = {"bids": [{"price": "0.60", "size": "3"}]}  # 3 share = ~$1.80 @ entry 0.50 → sadece küçük
    with patch("execution.paper_tracker.get_book", new_callable=AsyncMock, return_value=book), \
         patch("execution.paper_tracker._write_tp_ladder", side_effect=fake_write):
        await pt._measure_tp_ladder("p2", "tok", 20, "eth-updown-15m-1", "ETH", "YES",
                                    entry_price=0.50, observed_return=0.22,
                                    shares_unused=0, pos_usd_unused=0, db_path=":memory:")
    big = [r for r in written if r["simulated_exit_notional_usd"] == 100]
    assert big and big[0]["exit_fill_complete"] == 0, "büyük size partial olmalı"
    assert big[0]["real_tradable_tp_pnl"] is None, "partial fill P&L NULL olmalı"
    assert big[0]["conservative_tp_pnl"] is None, "partial conservative NULL olmalı"
    assert big[0]["exit_unfilled_shares"] > 0


# ── idempotency + schema ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ladder_idempotent_unique():
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        rec = {"paper_id": "p1", "tp_level": 15, "simulated_exit_notional_usd": 50,
               "slug": "s", "asset": "BTC", "action": "YES", "timeframe": "15m"}
        await pt._write_tp_ladder(rec, dbp)
        await pt._write_tp_ladder(rec, dbp)  # IGNORE
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT COUNT(*) FROM tp_size_ladder WHERE paper_id='p1' AND tp_level=15 AND simulated_exit_notional_usd=50") as c:
            n = (await c.fetchone())[0]
        await conn.close()
    assert n == 1


@pytest.mark.asyncio
async def test_tp_size_ladder_schema():
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    async with conn.execute("PRAGMA table_info(tp_size_ladder)") as cur:
        cols = {r[1] for r in await cur.fetchall()}
    # legacy cohort kolonu
    async with conn.execute("PRAGMA table_info(tp_exit_measurements)") as cur:
        leg = {r[1] for r in await cur.fetchall()}
    await conn.close()
    for col in ("simulated_exit_notional_usd", "exit_fill_complete", "exit_unfilled_shares",
                "real_tradable_tp_pnl", "conservative_tp_pnl", "tradable_capacity_usd",
                "cadence_artifact_flag", "overshoot_pct", "timeframe"):
        assert col in cols, f"eksik: {col}"
    assert "measurement_cohort" in leg


# ── 5m/15m timeframe ayrımı ladder'da ───────────────────────────────────────

@pytest.mark.asyncio
async def test_ladder_records_timeframe():
    import execution.paper_tracker as pt
    written = []
    async def fake_write(rec, db_path): written.append(rec)
    book = {"bids": [{"price": "0.60", "size": "100000"}]}
    with patch("execution.paper_tracker.get_book", new_callable=AsyncMock, return_value=book), \
         patch("execution.paper_tracker._write_tp_ladder", side_effect=fake_write):
        await pt._measure_tp_ladder("p5", "tok", 15, "btc-updown-5m-1", "BTC", "YES",
                                    entry_price=0.50, observed_return=0.20,
                                    shares_unused=0, pos_usd_unused=0, db_path=":memory:")
    assert all(r["timeframe"] == "5m" for r in written)
