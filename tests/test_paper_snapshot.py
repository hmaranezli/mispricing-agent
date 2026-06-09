"""tests/test_paper_snapshot.py — NO slippage baseline + temporal snapshot handoff TDD.

GÖREV 1: action-side slippage baseline (YES→yes_ask, NO→no_ask) + action_fair telemetri.
GÖREV 2: entry T=0 snapshot ile açılır; 60s loop entry'yi yeniden çekmez; collapse/late ayrı cohort.
"""
import asyncio
import sys
import os
import time
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── GÖREV 1: action-side fair + slippage baseline ────────────────────────────

def test_action_fair_yes():
    from execution.paper_tracker import _action_fair
    assert _action_fair("YES", 0.64) == 0.64


def test_action_fair_no():
    from execution.paper_tracker import _action_fair
    # NO action_fair = 1 - yes_fair
    assert _action_fair("NO", 0.22) == 0.78


def test_slippage_baseline_yes_uses_yes_ask():
    from execution.paper_tracker import _slippage_baseline
    f = {"action": "YES", "best_ask": 0.56, "no_ask": 0.45}
    assert _slippage_baseline(f) == 0.56


def test_slippage_baseline_no_uses_no_ask():
    from execution.paper_tracker import _slippage_baseline
    # NO baseline = no_ask, YES best_ask DEĞİL
    f = {"action": "NO", "best_ask": 0.33, "no_ask": 0.66}
    assert _slippage_baseline(f) == 0.66


def test_no_slippage_no_longer_artifact():
    """NO trade: entry 0.66, no_ask 0.66 → slip ~0 (eski bug %100 üretmezdi)."""
    from execution.paper_tracker import _slippage_baseline
    f = {"action": "NO", "best_ask": 0.33, "no_ask": 0.66}
    baseline = _slippage_baseline(f)
    slip = (0.66 - baseline) / baseline
    assert abs(slip) < 0.10, f"NO slippage artifact %47-100 olmamalı, bulundu {slip}"


def test_net_ev_uses_action_fair():
    """NO: net_ev = (1-yes_fair)*(1-fee) - entry = no_fair*(1-fee) - entry."""
    from execution.paper_tracker import _net_ev_after_slippage
    # yes_fair=0.22 → no_fair=0.78; entry=0.66 → 0.78*0.98 - 0.66 = 0.7644-0.66 = 0.1044 > 0
    net_ev, viab = _net_ev_after_slippage("NO", fair=0.22, est_fill=0.66, fee=0.02)
    assert net_ev > 0
    assert viab == "positive_after_slippage"


# ── GÖREV 2: build_entry_snapshot (T=0) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_build_entry_snapshot_fields():
    import execution.paper_tracker as pt
    finding = {"slug": "sol-updown-15m-1", "asset": "SOL", "action": "YES",
               "best_ask": 0.56, "best_bid": 0.54, "no_ask": 0.45,
               "fair_value": 0.64, "edge": 0.08, "fee_adj_edge": 0.054,
               "edge_bucket": "E50", "seconds_remaining": 400,
               "yes_token_id": "y", "no_token_id": "n", "ref_price": 100, "cur_price": 101}
    book = {"asks": [{"price": "0.58", "size": "1000"}]}
    with patch("execution.paper_tracker.get_book", new_callable=AsyncMock, return_value=book):
        snap = await pt.build_entry_snapshot(finding, position_usd=1.25)
    assert snap is not None
    assert snap["entry_price"] == 0.58
    assert snap["entry_method"] == "depth_walk"
    assert snap["signal_best_ask"] == 0.56
    assert snap["signal_seconds_remaining"] == 400
    assert snap["signal_timestamp_ms"] > 0
    assert snap["yes_fair"] == 0.64
    assert snap["action_fair"] == 0.64
    assert snap["paper_viability"] in ("positive_after_slippage", "negative_after_slippage")


@pytest.mark.asyncio
async def test_build_snapshot_no_action_baseline():
    import execution.paper_tracker as pt
    finding = {"slug": "xrp-updown-15m-1", "asset": "XRP", "action": "NO",
               "best_ask": 0.33, "best_bid": 0.31, "no_ask": 0.66,
               "fair_value": 0.22, "edge": 0.10, "fee_adj_edge": 0.10,
               "edge_bucket": "E50", "seconds_remaining": 400,
               "yes_token_id": "y", "no_token_id": "n", "ref_price": 1, "cur_price": 1}
    book = {"asks": [{"price": "0.66", "size": "1000"}]}  # NO token book
    with patch("execution.paper_tracker.get_book", new_callable=AsyncMock, return_value=book):
        snap = await pt.build_entry_snapshot(finding, position_usd=1.25)
    assert snap["no_fair"] == 0.78
    assert snap["action_fair"] == 0.78
    # slippage NO baseline (no_ask 0.66) → entry 0.66 → ~0, %47-100 DEĞİL
    assert abs(snap["signal_slippage"]) < 0.10


# ── schedule/worker snapshot kullanımı (get_book ÇAĞIRMAZ) ───────────────────

@pytest.mark.asyncio
async def test_worker_with_snapshot_skips_get_book():
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    pt._active.clear()
    get_book_called = []

    async def spy_book(*a, **k):
        get_book_called.append(1)
        return {"asks": [{"price": "0.99", "size": "1"}]}

    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        finding = {"slug": "sol-updown-15m-2", "asset": "SOL", "action": "YES",
                   "best_ask": 0.56, "no_ask": 0.45, "fair_value": 0.64, "edge": 0.08,
                   "fee_adj_edge": 0.054, "edge_bucket": "E50", "seconds_remaining": 400,
                   "yes_token_id": "y", "no_token_id": "n", "ref_price": 100, "cur_price": 101}
        snapshot = {
            "entry_price": 0.58, "entry_method": "depth_walk", "data_quality": "high",
            "signal_best_ask": 0.56, "signal_best_bid": 0.54,
            "signal_depth_walk_entry": 0.58, "signal_fee_adj_edge": 0.054,
            "signal_net_ev": 0.044, "signal_slippage": 0.036,
            "signal_seconds_remaining": 400, "signal_timestamp_ms": int(time.time() * 1000),
            "yes_fair": 0.64, "no_fair": 0.36, "action_fair": 0.64,
            "paper_viability": "positive_after_slippage", "levels": 1,
        }
        with patch("execution.paper_tracker.get_book", side_effect=spy_book):
            await pt._paper_open_worker(finding, {"confidence_score": None},
                                        {"position_usd": 1.25}, dbp, 0.1, snapshot=snapshot)

        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute(
            "SELECT entry_price_estimated, entry_source, snapshot_age_ms, action_fair, "
            "no_fair, estimated_slippage_pct FROM shadow_positions") as c:
            row = await c.fetchone()
        await conn.close()
    assert not get_book_called, "snapshot varsa worker get_book ÇAĞIRMAMALI (temporal sync)"
    assert row[0] == 0.58
    assert row[1] == "scout_snapshot"
    assert row[2] is not None       # snapshot_age_ms
    assert row[3] == 0.64           # action_fair
    pt._active.clear()


# ── collapse/late ayrı cohort ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_collapse_late_separate_cohort():
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    pt._active.clear()
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        finding = {"slug": "btc-updown-15m-3", "asset": "BTC", "action": "YES",
                   "best_ask": 0.80, "no_ask": 0.20, "fair_value": 0.82, "edge": 0.05,
                   "fee_adj_edge": 0.04, "edge_bucket": "E40",
                   "seconds_remaining": 100,  # collapse'a yakın
                   "yes_token_id": "y", "no_token_id": "n", "ref_price": 1, "cur_price": 1}
        snapshot = {
            "entry_price": 0.80, "entry_method": "depth_walk", "data_quality": "high",
            "signal_best_ask": 0.80, "signal_best_bid": 0.78, "signal_depth_walk_entry": 0.80,
            "signal_fee_adj_edge": 0.04, "signal_net_ev": -0.01, "signal_slippage": 0.0,
            "signal_seconds_remaining": 100,  # < COLLAPSE_SECS
            "signal_timestamp_ms": int(time.time() * 1000),
            "yes_fair": 0.82, "no_fair": 0.18, "action_fair": 0.82,
            "paper_viability": "negative_after_slippage", "levels": 1,
        }
        await pt._paper_open_worker(finding, {}, {"position_usd": 1.25}, dbp, 0.1, snapshot=snapshot)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute(
            "SELECT cohort, data_quality, collapse_timing_flag FROM shadow_positions") as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] == "paper_late", f"collapse market clean cohort'a karışmamalı, bulundu {row[0]}"
    assert row[2] == 1
    pt._active.clear()


@pytest.mark.asyncio
async def test_clean_cohort_excludes_late():
    """Normal seconds_remaining → cohort='paper' (clean)."""
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    pt._active.clear()
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        finding = {"slug": "sol-updown-15m-4", "asset": "SOL", "action": "YES",
                   "best_ask": 0.56, "no_ask": 0.45, "fair_value": 0.64, "edge": 0.08,
                   "fee_adj_edge": 0.054, "edge_bucket": "E50", "seconds_remaining": 400,
                   "yes_token_id": "y", "no_token_id": "n", "ref_price": 1, "cur_price": 1}
        snapshot = {
            "entry_price": 0.58, "entry_method": "depth_walk", "data_quality": "high",
            "signal_best_ask": 0.56, "signal_best_bid": 0.54, "signal_depth_walk_entry": 0.58,
            "signal_fee_adj_edge": 0.054, "signal_net_ev": 0.044, "signal_slippage": 0.036,
            "signal_seconds_remaining": 400, "signal_timestamp_ms": int(time.time() * 1000),
            "yes_fair": 0.64, "no_fair": 0.36, "action_fair": 0.64,
            "paper_viability": "positive_after_slippage", "levels": 1,
        }
        await pt._paper_open_worker(finding, {}, {"position_usd": 1.25}, dbp, 0.1, snapshot=snapshot)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT cohort FROM shadow_positions") as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] == "paper"
    pt._active.clear()


# ── schema kolonları ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_snapshot_schema_columns():
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    async with conn.execute("PRAGMA table_info(shadow_positions)") as cur:
        cols = {r[1] for r in await cur.fetchall()}
    await conn.close()
    for col in ("yes_fair", "no_fair", "action_fair", "entry_source", "snapshot_age_ms",
                "seconds_remaining_at_signal", "seconds_remaining_at_open",
                "late_entry_flag", "collapse_timing_flag", "signal_timestamp_ms"):
        assert col in cols, f"eksik kolon: {col}"


# ── schedule non-blocking korunur ────────────────────────────────────────────

def test_schedule_still_no_await():
    import execution.paper_tracker as pt
    import inspect
    assert "await " not in inspect.getsource(pt.schedule_paper_open)
