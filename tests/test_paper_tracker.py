"""tests/test_paper_tracker.py — Paper/Shadow Position Tracker + MFE Breakeven TDD.

KRİTİK: Canlı davranış ASLA değişmez. Paper sadece council_pass+entry_disabled'dan
beslenir, ayrı tablolarda, gerçek para yok, live loop bloklanmaz.
"""
import asyncio
import sys
import os
import time
import aiosqlite
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Entry price estimate: mid ASLA, depth-walk / ask+buffer ─────────────────

def test_estimate_entry_depth_walk():
    from execution.paper_tracker import _estimate_entry_price
    book = {"asks": [{"price": "0.50", "size": "10"}, {"price": "0.52", "size": "100"}]}
    price, method, quality, levels = _estimate_entry_price(book, position_usd=2.0)
    # $2 ile: 0.50×... ilk seviye 10 share = $5 kapasite → $2 hepsi 0.50'den
    assert method == "depth_walk"
    assert price == 0.50
    assert quality == "high"  # tam dolduruldu
    assert levels == 1


def test_estimate_entry_depth_walk_multi_level():
    from execution.paper_tracker import _estimate_entry_price
    book = {"asks": [{"price": "0.50", "size": "2"}, {"price": "0.60", "size": "100"}]}
    # $2: ilk seviye 2share×0.50=$1, kalan $1 ikinci seviyeden 0.60'tan
    price, method, quality, levels = _estimate_entry_price(book, position_usd=2.0)
    assert method == "depth_walk"
    assert price > 0.50  # ağırlıklı ort, iki seviye
    assert levels == 2


def test_estimate_entry_not_mid():
    """Mid-price ASLA kullanılmaz — depth-walk ask tarafından."""
    from execution.paper_tracker import _estimate_entry_price
    book = {"asks": [{"price": "0.60", "size": "100"}],
            "bids": [{"price": "0.40", "size": "100"}]}
    price, method, quality, levels = _estimate_entry_price(book, position_usd=1.0)
    mid = (0.60 + 0.40) / 2
    assert price != mid, "mid-price kullanılmamalı"
    assert price == 0.60  # ask'tan


def test_estimate_entry_empty_book_low_quality():
    from execution.paper_tracker import _estimate_entry_price
    price, method, quality, levels = _estimate_entry_price({"asks": []}, position_usd=1.0)
    assert price is None
    assert quality == "low"


def test_ask_buffer_fallback():
    from execution.paper_tracker import _ask_buffer_price, TAKER_BUFFER
    price, method, quality = _ask_buffer_price(0.50)
    assert price == round(0.50 + TAKER_BUFFER, 4)
    assert method == "ask_buffer"
    assert quality == "low"


# ── MFE Breakeven model ──────────────────────────────────────────────────────

def test_mfe_breakeven_arms_at_15pct():
    from execution.paper_tracker import _mfe_breakeven_decide
    # mfe_peak 0.15'e ulaştı → armed (state dict ile)
    state = {"_breakeven_armed": False}
    action, reason = _mfe_breakeven_decide(dd=0.10, mfe_peak=0.15, mae=-0.05,
                                           secs=300, elapsed=60, state=state)
    assert state["_breakeven_armed"] is True


def test_mfe_breakeven_exit_on_buffer_breach():
    from execution.paper_tracker import _mfe_breakeven_decide
    state = {"_breakeven_armed": True}
    # armed + dd entry-3% altına döndü → EXIT
    action, reason = _mfe_breakeven_decide(dd=-0.04, mfe_peak=0.20, mae=-0.10,
                                           secs=300, elapsed=120, state=state)
    assert action == "EXIT"
    assert reason == "mfe_breakeven_stop"


def test_mfe_breakeven_holds_when_armed_above_buffer():
    from execution.paper_tracker import _mfe_breakeven_decide
    state = {"_breakeven_armed": True}
    action, reason = _mfe_breakeven_decide(dd=0.05, mfe_peak=0.20, mae=-0.10,
                                           secs=300, elapsed=120, state=state)
    assert action == "HOLD"


def test_mfe_breakeven_catastrophe_priority():
    from execution.paper_tracker import _mfe_breakeven_decide
    state = {"_breakeven_armed": False}
    action, reason = _mfe_breakeven_decide(dd=-0.50, mfe_peak=0.0, mae=-0.50,
                                           secs=300, elapsed=60, state=state)
    assert action == "CATASTROPHE_EXIT"
    assert reason == "catastrophe"


def test_mfe_breakeven_min_hold_holds():
    from execution.paper_tracker import _mfe_breakeven_decide
    state = {"_breakeven_armed": False}
    action, reason = _mfe_breakeven_decide(dd=-0.30, mfe_peak=0.0, mae=-0.30,
                                           secs=300, elapsed=5, state=state)
    assert action == "HOLD"
    assert reason == "min_hold"


# ── schedule_paper_open: non-blocking, dedupe, max-limit, fail-open ──────────

@pytest.mark.asyncio
async def test_schedule_non_blocking_fast():
    import execution.paper_tracker as pt
    pt._active.clear()
    finding = {"slug": "btc-updown-15m-1", "asset": "BTC", "action": "YES",
               "best_ask": 0.50, "fair_value": 0.60, "edge": 0.10,
               "yes_token_id": "y", "no_token_id": "n", "seconds_remaining": 400,
               "ref_price": 100.0, "cur_price": 101.0}
    gate = {"confidence_score": 80}
    risk = {"position_usd": 1.25}
    with patch("execution.paper_tracker._paper_open_worker", new_callable=AsyncMock):
        delay = pt.schedule_paper_open(finding, gate, risk, conn=None, db_path=":memory:")
    assert isinstance(delay, float)
    assert delay < 5.0


def test_schedule_no_await_in_path():
    import execution.paper_tracker as pt
    import inspect
    assert "await " not in inspect.getsource(pt.schedule_paper_open)


@pytest.mark.asyncio
async def test_schedule_dedupe_same_combo():
    import execution.paper_tracker as pt
    pt._active.clear()
    pt._active[("btc-updown-15m-1", "BTC", "YES")] = {"status": "open"}  # zaten açık
    finding = {"slug": "btc-updown-15m-1", "asset": "BTC", "action": "YES",
               "best_ask": 0.50, "yes_token_id": "y", "seconds_remaining": 400}
    created = []
    with patch("asyncio.create_task", side_effect=lambda *a, **k: created.append(1)):
        pt.schedule_paper_open(finding, {}, {"position_usd": 1.25}, db_path=":memory:")
    assert not created, "dedupe: aynı combo açıkken yeni paper açılmamalı"
    pt._active.clear()


@pytest.mark.asyncio
async def test_schedule_max_limit_fail_open():
    import execution.paper_tracker as pt
    pt._active.clear()
    for i in range(pt.MAX_PAPER_POSITIONS):
        pt._active[(f"s{i}", "BTC", "YES")] = {"status": "open"}
    finding = {"slug": "new-slug", "asset": "ETH", "action": "NO",
               "best_ask": 0.50, "no_token_id": "n", "seconds_remaining": 400}
    created = []
    with patch("asyncio.create_task", side_effect=lambda *a, **k: created.append(1)):
        pt.schedule_paper_open(finding, {}, {"position_usd": 1.25}, db_path=":memory:")
    assert not created, "max limit aşıldı → fail-open, task yaratılmaz"
    pt._active.clear()


# ── Lifecycle: expiry / TTL / stale → close ──────────────────────────────────

def test_should_close_on_expiry():
    from execution.paper_tracker import _should_close
    pos = {"_opened_monotonic": time.monotonic(), "_stale_count": 0,
           "_last_secs": -5}
    assert _should_close(pos, time.monotonic()) == "expired"


def test_should_close_on_ttl():
    from execution.paper_tracker import _should_close, MAX_TTL_SECS
    pos = {"_opened_monotonic": time.monotonic() - MAX_TTL_SECS - 10,
           "_stale_count": 0, "_last_secs": 300}
    assert _should_close(pos, time.monotonic()) == "ttl_exceeded"


def test_should_close_on_stale():
    from execution.paper_tracker import _should_close, STALE_LIMIT
    pos = {"_opened_monotonic": time.monotonic(), "_stale_count": STALE_LIMIT,
           "_last_secs": 300}
    assert _should_close(pos, time.monotonic()) == "stale_price"


def test_should_not_close_when_healthy():
    from execution.paper_tracker import _should_close
    pos = {"_opened_monotonic": time.monotonic(), "_stale_count": 0,
           "_last_secs": 300}
    assert _should_close(pos, time.monotonic()) is None


# ── DB schema + paper/live ayrımı ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_shadow_tables_created():
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    tables = {}
    for t in ("shadow_positions", "shadow_stop_events", "shadow_model_pnl", "paper_entry_events"):
        async with conn.execute(f"PRAGMA table_info({t})") as cur:
            tables[t] = {r[1] for r in await cur.fetchall()}
    await conn.close()
    assert tables["shadow_positions"], "shadow_positions yok"
    assert "is_paper" in tables["shadow_positions"]
    assert "cohort" in tables["shadow_positions"]
    assert "confidence_level" in tables["shadow_positions"]
    assert "source_event_id" in tables["shadow_positions"]  # lineage
    assert tables["shadow_stop_events"]
    assert tables["shadow_model_pnl"]
    assert "model" in tables["shadow_model_pnl"]
    assert tables["paper_entry_events"]


@pytest.mark.asyncio
async def test_paper_pnl_not_in_live_positions():
    """Paper kayıtları live positions tablosuna ASLA yazılmaz."""
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    pt._active.clear()
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()

        finding = {"slug": "btc-updown-15m-9", "asset": "BTC", "action": "YES",
                   "best_ask": 0.50, "fair_value": 0.60, "edge": 0.10,
                   "yes_token_id": "y", "no_token_id": "n", "seconds_remaining": 400,
                   "ref_price": 100.0, "cur_price": 101.0}
        fake_book = {"asks": [{"price": "0.50", "size": "1000"}]}
        with patch("execution.paper_tracker.get_book", new_callable=AsyncMock, return_value=fake_book):
            await pt._paper_open_worker(finding, {"confidence_score": 80},
                                        {"position_usd": 1.25}, dbp, 0.1)

        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT COUNT(*) FROM positions") as c:
            live_count = (await c.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM shadow_positions") as c:
            paper_count = (await c.fetchone())[0]
        await conn.close()
    assert live_count == 0, "paper, live positions'a yazılmamalı"
    assert paper_count == 1, "paper shadow_positions'a yazılmalı"
    pt._active.clear()


@pytest.mark.asyncio
async def test_paper_open_writes_lineage_and_quality():
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    pt._active.clear()
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        finding = {"slug": "eth-updown-15m-9", "asset": "ETH", "action": "NO",
                   "best_ask": 0.48, "fair_value": 0.40, "edge": 0.08,
                   "yes_token_id": "y", "no_token_id": "n", "seconds_remaining": 400,
                   "ref_price": 3000.0, "cur_price": 2990.0}
        fake_book = {"asks": [{"price": "0.48", "size": "1000"}]}
        with patch("execution.paper_tracker.get_book", new_callable=AsyncMock, return_value=fake_book):
            await pt._paper_open_worker(finding, {"confidence_score": 75},
                                        {"position_usd": 1.25}, dbp, 0.1)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute(
            "SELECT cohort, confidence_level, is_paper, source_event_id, edge, entry_method FROM shadow_positions"
        ) as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] == "paper"
    assert row[1] == "low"
    assert row[2] == 1
    assert row[3] is not None  # source_event_id lineage
    assert row[5] == "depth_walk"
    pt._active.clear()


# ── Dayanıklılık: worker DB fail / exception ────────────────────────────────

@pytest.mark.asyncio
async def test_worker_db_fail_does_not_raise():
    import execution.paper_tracker as pt
    pt._active.clear()
    finding = {"slug": "x", "asset": "BTC", "action": "YES", "best_ask": 0.5,
               "yes_token_id": "y", "no_token_id": "n", "seconds_remaining": 400,
               "fair_value": 0.6, "edge": 0.1, "ref_price": 1, "cur_price": 1}
    with patch("execution.paper_tracker.get_book", new_callable=AsyncMock,
               return_value={"asks": [{"price": "0.5", "size": "1000"}]}), \
         patch("execution.paper_tracker._insert_paper_position", side_effect=RuntimeError("db locked")):
        # exception fırlatmamalı
        await pt._paper_open_worker(finding, {}, {"position_usd": 1.25}, ":memory:", 0.1)
    pt._active.clear()


@pytest.mark.asyncio
async def test_worker_book_error_uses_fallback_or_skips():
    """get_book patlarsa worker crash etmez (fallback dener veya skip)."""
    import execution.paper_tracker as pt
    pt._active.clear()
    finding = {"slug": "x2", "asset": "BTC", "action": "YES", "best_ask": 0.5,
               "yes_token_id": "y", "no_token_id": "n", "seconds_remaining": 400,
               "fair_value": 0.6, "edge": 0.1, "ref_price": 1, "cur_price": 1}
    async def boom(*a, **k): raise asyncio.TimeoutError("book")
    inserted = []
    async def fake_insert(rec, db_path):
        inserted.append(rec)
    with patch("execution.paper_tracker.get_book", side_effect=boom), \
         patch("execution.paper_tracker._insert_paper_position", side_effect=fake_insert):
        await pt._paper_open_worker(finding, {}, {"position_usd": 1.25}, ":memory:", 0.1)
    # fallback ask+buffer ile yine de açılmalı (best_ask var)
    assert inserted, "book hatası → ask+buffer fallback ile açılmalı"
    assert inserted[0]["entry_method"] == "ask_buffer"
    pt._active.clear()


# ── Model decisions matrisi ──────────────────────────────────────────────────

def test_all_models_produce_actions():
    from execution.paper_tracker import _all_model_decisions
    state = {"action": "YES", "_breakeven_armed": False}
    d = _all_model_decisions(dd=-0.30, hl_drift=0.0, mfe_peak=0.0, mae=-0.30,
                             secs=300, elapsed=60, frac=0.2, state=state)
    for m in ("current", "conservative", "balanced", "mfe_breakeven"):
        assert m in d
        assert d[m][0] in ("HOLD", "EXIT", "CATASTROPHE_EXIT")


# ── update_paper_position: MFE/MAE tracking + model exit lock ────────────────

@pytest.mark.asyncio
async def test_update_tracks_mfe_mae():
    import execution.paper_tracker as pt
    state = {"slug": "s", "asset": "BTC", "action": "YES", "entry_price": 0.50,
             "shares": 2.0, "ref_price": 100.0, "_opened_monotonic": time.monotonic() - 60,
             "_mfe_peak": 0.0, "_mae_trough": 0.0, "_breakeven_armed": False,
             "_model_exits": {}, "paper_id": "p", "status": "open"}
    with patch("execution.paper_tracker._record_stop_event", new_callable=AsyncMock):
        # fiyat 0.60'a çıktı → mfe +20%
        await pt.update_paper_position(state, pm_price=0.60, hl_price=101.0, secs=300, db_path=":memory:")
    assert state["_mfe_peak"] > 0.15  # +20% MFE → breakeven armed beklenir
    assert state["_breakeven_armed"] is True


@pytest.mark.asyncio
async def test_update_locks_model_exit_once():
    import execution.paper_tracker as pt
    state = {"slug": "s", "asset": "BTC", "action": "YES", "entry_price": 0.50,
             "shares": 2.0, "ref_price": 100.0, "_opened_monotonic": time.monotonic() - 60,
             "_mfe_peak": 0.0, "_mae_trough": 0.0, "_breakeven_armed": False,
             "_model_exits": {}, "paper_id": "p", "status": "open"}
    with patch("execution.paper_tracker._record_stop_event", new_callable=AsyncMock):
        # büyük drawdown → current model EXIT eder
        await pt.update_paper_position(state, pm_price=0.30, hl_price=99.0, secs=300, db_path=":memory:")
    assert "current" in state["_model_exits"], "EXIT eden model kilitlenmneli"
    # ilk exit fiyatı kilitli kalmalı
    first = state["_model_exits"]["current"]
    with patch("execution.paper_tracker._record_stop_event", new_callable=AsyncMock):
        await pt.update_paper_position(state, pm_price=0.25, hl_price=98.0, secs=200, db_path=":memory:")
    assert state["_model_exits"]["current"] == first, "kilitli exit değişmemeli"
