"""tests/test_air_pocket_shadow.py — Air-Pocket Exit Guard Shadow (Faz A) TDD.

KRİTİK: Bu saf shadow. Canlı exit ASLA bloklanmaz/gecikmez.
- schedule() senkron + non-blocking (create_task fırlatır, anında döner)
- stop anında ekstra get_book/DB YOK
- post-wait get_book gerçek veriden would_have_improved_fill hesaplar
- tüm hatalar fail-open: shadow patlasa bile canlı exit devam eder
"""
import asyncio
import sys
import os
import time
import aiosqlite
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── _decide: saf karar ağacı ────────────────────────────────────────────────

def test_decide_healthy_book_exit_now():
    from execution.air_pocket_shadow import _decide
    # gap düşük, mae normal, expiry uzak → normal exit
    decision, override, reason = _decide(gap=0.02, mae=-0.25, secs=300)
    assert decision == "EXIT_NOW"
    assert override is None
    assert reason == "healthy_book"


def test_decide_air_pocket_gap_wait():
    from execution.air_pocket_shadow import _decide
    # #1339 benzeri: gap %28 > %12 eşik
    decision, override, reason = _decide(gap=0.28, mae=-0.30, secs=300)
    assert decision == "WAIT_STABILIZE"
    assert reason == "air_pocket_gap"
    assert override is None


def test_decide_catastrophe_override():
    from execution.air_pocket_shadow import _decide
    # mae < -45% → token çöküyor, beklemeden çık
    decision, override, reason = _decide(gap=0.28, mae=-0.54, secs=300)
    assert decision == "EXIT_NOW"
    assert override == "catastrophe"


def test_decide_expiry_override():
    from execution.air_pocket_shadow import _decide
    # expiry < 45s → vade riski > fill riski, hemen çık
    decision, override, reason = _decide(gap=0.28, mae=-0.30, secs=30)
    assert decision == "EXIT_NOW"
    assert override == "expiry"


def test_decide_expiry_beats_catastrophe():
    from execution.air_pocket_shadow import _decide
    # expiry önceliği en yüksek
    decision, override, reason = _decide(gap=0.28, mae=-0.54, secs=10)
    assert decision == "EXIT_NOW"
    assert override == "expiry"


# ── schedule(): non-blocking, hızlı ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_schedule_is_non_blocking_and_fast():
    """schedule() create_task fırlatır, anında döner. live_exit_delay_ms küçük olmalı."""
    import execution.air_pocket_shadow as aps
    aps._active = 0
    pos = {"seq_no": 1, "position_id": "p1", "slug": "s", "asset": "BTC",
           "action": "NO", "sl_trigger_px": 0.5, "mae_pct": -0.28,
           "_cached_seconds_remaining": 300, "shares": 2.0, "no_token_id": "tok"}

    with patch("execution.air_pocket_shadow._worker", new_callable=AsyncMock):
        delay = aps.schedule(pos, current_exit_price=0.36, exit_token="tok", db_path=":memory:")

    assert isinstance(delay, float)
    assert delay < 5.0, f"schedule {delay}ms sürdü — canlı exit'i geciktirir"


@pytest.mark.asyncio
async def test_schedule_no_await_in_path():
    """schedule() içinde await OLMAMALI — senkron dönmeli (canlı exit bloklanmaz)."""
    import execution.air_pocket_shadow as aps
    import inspect
    src = inspect.getsource(aps.schedule)
    assert "await " not in src, "schedule() içinde await var — canlı exit bloklanabilir"


# ── semaphore/bounded queue: fail-open ──────────────────────────────────────

@pytest.mark.asyncio
async def test_queue_full_fails_open():
    """Aktif task MAX'a ulaşınca yeni task YARATILMAZ, canlı exit etkilenmez."""
    import execution.air_pocket_shadow as aps
    aps._active = aps.MAX_CONCURRENT  # queue dolu simüle
    created = []
    pos = {"seq_no": 9, "position_id": "p9", "action": "NO", "no_token_id": "t"}

    with patch("asyncio.create_task", side_effect=lambda *a, **k: created.append(1)):
        delay = aps.schedule(pos, current_exit_price=0.36, exit_token="t", db_path=":memory:")

    assert not created, "queue doluyken task yaratılmamalı (fail-open)"
    assert isinstance(delay, float)
    aps._active = 0  # temizle


# ── _worker: post-wait gerçek veri ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_worker_would_have_improved_fill_true():
    """post-wait bid > current fill → would_have_improved_fill=True (gerçek veri)."""
    import execution.air_pocket_shadow as aps
    aps._active = 1

    fake_book = {"bids": [{"price": "0.45", "size": "100"}]}  # post-wait bid 0.45 > current 0.36
    snap = dict(seq_no=1, position_id="p1", slug="s", asset="BTC", action="NO",
                sl_trigger_px=0.50, mae_pct=-0.28, seconds_remaining=300, shares=2.0)
    written = {}

    async def fake_write(rec, db_path):
        written.update(rec)

    with patch("execution.air_pocket_shadow.get_book", new_callable=AsyncMock, return_value=fake_book), \
         patch("execution.air_pocket_shadow.asyncio.sleep", new_callable=AsyncMock), \
         patch("execution.air_pocket_shadow._write", side_effect=fake_write):
        await aps._worker(snap, current_exit_price=0.36, exit_token="tok", db_path=":memory:")

    assert written.get("would_have_improved_fill") == 1
    assert written.get("post_wait_bid") == 0.45
    assert written.get("shadow_compute_ms") is not None
    assert written.get("actual_trigger_fill_gap") is not None  # (0.50-0.36)/0.50 = 0.28


@pytest.mark.asyncio
async def test_worker_book_error_records_and_survives():
    """get_book hata/timeout → post_wait_error kaydedilir, worker patlamaz, kayıt yazılır."""
    import execution.air_pocket_shadow as aps
    aps._active = 1
    snap = dict(seq_no=2, position_id="p2", slug="s", asset="BTC", action="NO",
                sl_trigger_px=0.50, mae_pct=-0.28, seconds_remaining=300, shares=2.0)
    written = {}

    async def fake_write(rec, db_path):
        written.update(rec)

    async def boom(*a, **k):
        raise asyncio.TimeoutError("book timeout")

    with patch("execution.air_pocket_shadow.get_book", side_effect=boom), \
         patch("execution.air_pocket_shadow.asyncio.sleep", new_callable=AsyncMock), \
         patch("execution.air_pocket_shadow._write", side_effect=fake_write):
        await aps._worker(snap, current_exit_price=0.36, exit_token="tok", db_path=":memory:")

    assert written.get("post_wait_error") is not None
    # karar yine de hesaplanmış olmalı (gap'e göre)
    assert written.get("guarded_exit_decision") is not None


@pytest.mark.asyncio
async def test_worker_db_failure_does_not_raise():
    """DB write patlasa bile _worker exception fırlatmaz (canlı exit zaten ayrı path)."""
    import execution.air_pocket_shadow as aps
    aps._active = 1
    snap = dict(seq_no=3, position_id="p3", slug="s", asset="BTC", action="NO",
                sl_trigger_px=0.50, mae_pct=-0.28, seconds_remaining=300, shares=2.0)

    async def db_boom(*a, **k):
        raise RuntimeError("db locked")

    with patch("execution.air_pocket_shadow.get_book", new_callable=AsyncMock,
               return_value={"bids": [{"price": "0.40", "size": "50"}]}), \
         patch("execution.air_pocket_shadow.asyncio.sleep", new_callable=AsyncMock), \
         patch("execution.air_pocket_shadow._write", side_effect=db_boom):
        # exception fırlatmamalı
        await aps._worker(snap, current_exit_price=0.36, exit_token="tok", db_path=":memory:")
    # buraya ulaşması = patlamadı
    assert aps._active == 0  # finally decrement çalıştı


@pytest.mark.asyncio
async def test_worker_decrements_active_on_success():
    """_worker bittiğinde _active azalmalı (finally) — queue dolmasın."""
    import execution.air_pocket_shadow as aps
    aps._active = 1
    snap = dict(seq_no=4, position_id="p4", slug="s", asset="BTC", action="NO",
                sl_trigger_px=0.50, mae_pct=-0.28, seconds_remaining=300, shares=2.0)

    with patch("execution.air_pocket_shadow.get_book", new_callable=AsyncMock,
               return_value={"bids": [{"price": "0.40", "size": "50"}]}), \
         patch("execution.air_pocket_shadow.asyncio.sleep", new_callable=AsyncMock), \
         patch("execution.air_pocket_shadow._write", new_callable=AsyncMock):
        await aps._worker(snap, current_exit_price=0.36, exit_token="tok", db_path=":memory:")

    assert aps._active == 0


# ── DB schema ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_air_pocket_shadow_table_created():
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    async with conn.execute("PRAGMA table_info(air_pocket_shadow)") as cur:
        cols = {row[1] for row in await cur.fetchall()}
    await conn.close()
    required = {
        "seq_no", "position_id", "slug", "asset", "action",
        "current_exit_price", "current_exit_result",
        "guarded_exit_decision", "decision_reason", "override_reason",
        "depth_ratio", "pred_gap", "actual_trigger_fill_gap",
        "post_wait_bid", "post_wait_depth", "post_wait_error",
        "would_have_improved_fill", "false_positive_guard",
        "shadow_compute_ms", "live_exit_delay_ms", "error", "created_at",
    }
    missing = required - cols
    assert not missing, f"Eksik kolonlar: {missing}"


@pytest.mark.asyncio
async def test_write_inserts_row():
    """_write gerçek DB'ye satır yazar (timeout'lu async)."""
    from db.schema import init_schema
    import execution.air_pocket_shadow as aps
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp))
        await init_schema(conn)
        await conn.close()

        rec = {"seq_no": 7, "position_id": "p7", "slug": "s", "asset": "BTC",
               "action": "NO", "current_exit_price": 0.36,
               "guarded_exit_decision": "WAIT_STABILIZE", "decision_reason": "air_pocket_gap",
               "actual_trigger_fill_gap": 0.28, "would_have_improved_fill": 1,
               "shadow_compute_ms": 405.2, "live_exit_delay_ms": 0.3}
        await aps._write(rec, dbp)

        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT seq_no, guarded_exit_decision FROM air_pocket_shadow") as cur:
            row = await cur.fetchone()
        await conn.close()
    assert row[0] == 7
    assert row[1] == "WAIT_STABILIZE"
