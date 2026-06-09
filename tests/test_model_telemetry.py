"""tests/test_model_telemetry.py — Legacy fair-value telemetri + VOL CLAMP hipotezi TDD.

Model davranışını DEĞİŞTİRMEZ — sadece iç değişkenleri (raw vs clamped vol, sigma_t,
z_score, overconfidence flag) loglar. Async/non-blocking; hata → log+devam (crash yok).
"""
import asyncio
import sys
import os
import math
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── raw vs clamped vol ──────────────────────────────────────────────────────

def test_realized_vol_raw_no_clamp():
    """realized_vol_raw clamp UYGULAMAZ (clamp öncesi ham değer)."""
    from data.hl_candles import realized_vol_raw, calculate_realized_volatility
    # yüksek volatilite üreten candle serisi
    candles = [{"c": str(100 * (1.05 ** i))} for i in range(20)]  # her adım +%5
    raw = realized_vol_raw(candles)
    clamped = calculate_realized_volatility(candles)
    # raw clamp'siz; clamped <= 3.0
    assert clamped <= 3.0
    # davranış korundu: calculate = clamp(raw)
    assert abs(clamped - max(0.30, min(raw, 3.00))) < 1e-9


def test_calculate_realized_volatility_unchanged():
    """Refactor davranış-koruyucu: clamp'li sonuç eski formülle aynı."""
    from data.hl_candles import calculate_realized_volatility
    candles = [{"c": "100"}, {"c": "101"}, {"c": "100.5"}, {"c": "102"}]
    v = calculate_realized_volatility(candles)
    assert 0.30 <= v <= 3.00


# ── compute_legacy_telemetry ────────────────────────────────────────────────

def test_clamp_hit_high_vol():
    from data.model_telemetry import compute_legacy_telemetry, VOL_CLAMP_MAX
    rec = compute_legacy_telemetry(asset="XRP", action="YES", p_now=1.05, p_ref=1.00,
                                   secs=600, best_bid=0.55, best_ask=0.58,
                                   raw_vol=4.5,  # > 3.0
                                   fair_yes_val=0.67, net_ev=0.05, fair_gap=0.07,
                                   edge_bin="0.03-0.06", would_enter=True, snapshot_id="s1")
    assert rec["raw_realized_vol"] == 4.5
    assert rec["clamped_model_vol"] == VOL_CLAMP_MAX  # 3.0
    assert rec["vol_was_clamped"] is True


def test_no_clamp_in_range():
    from data.model_telemetry import compute_legacy_telemetry
    rec = compute_legacy_telemetry(asset="BTC", action="YES", p_now=1.01, p_ref=1.00,
                                   secs=600, best_bid=0.50, best_ask=0.52,
                                   raw_vol=0.80,  # aralık içi
                                   fair_yes_val=0.55, net_ev=0.05, fair_gap=0.05,
                                   edge_bin="0.03-0.06", would_enter=True, snapshot_id="s2")
    assert rec["vol_was_clamped"] is False
    assert rec["clamped_model_vol"] == 0.80


def test_sigma_t_and_z_computed():
    from data.model_telemetry import compute_legacy_telemetry
    rec = compute_legacy_telemetry(asset="BTC", action="YES", p_now=1.05, p_ref=1.00,
                                   secs=600, best_bid=0.5, best_ask=0.52, raw_vol=0.80,
                                   fair_yes_val=0.6, net_ev=0.05, fair_gap=0.05,
                                   edge_bin="x", would_enter=True, snapshot_id="s3")
    # sigma_t = vol*sqrt(secs/yıl); z = log(p_now/p_ref)/sigma_t
    years = 600 / 31_557_600.0
    exp_sigma = 0.80 * math.sqrt(years)
    exp_z = math.log(1.05 / 1.00) / exp_sigma
    assert abs(rec["sigma_t"] - exp_sigma) < 1e-7
    assert abs(rec["z_score"] - exp_z) < 1e-5
    assert abs(rec["z_abs"] - abs(exp_z)) < 1e-6
    assert rec["drift_term"] == 0


def test_z_overconfidence_flag():
    from data.model_telemetry import compute_legacy_telemetry, Z_OVERCONF_THRESHOLD
    # clamp + yüksek z → overconfidence imzası
    rec = compute_legacy_telemetry(asset="XRP", action="YES", p_now=1.20, p_ref=1.00,
                                   secs=300, best_bid=0.5, best_ask=0.52, raw_vol=5.0,
                                   fair_yes_val=0.9, net_ev=0.05, fair_gap=0.05,
                                   edge_bin="x", would_enter=True, snapshot_id="s4")
    if rec["z_abs"] >= Z_OVERCONF_THRESHOLD:
        assert rec["z_overconfidence_flag"] is True
        assert rec["vol_clamp_and_high_z"] is True  # clamp(5.0>3) AND high z
    assert rec["z_overconfidence_threshold"] == Z_OVERCONF_THRESHOLD


def test_z_overconfidence_flag_false_low_z():
    from data.model_telemetry import compute_legacy_telemetry
    rec = compute_legacy_telemetry(asset="BTC", action="YES", p_now=1.001, p_ref=1.00,
                                   secs=600, best_bid=0.5, best_ask=0.52, raw_vol=0.80,
                                   fair_yes_val=0.51, net_ev=0.05, fair_gap=0.05,
                                   edge_bin="x", would_enter=True, snapshot_id="s5")
    assert rec["z_overconfidence_flag"] is False
    assert rec["vol_clamp_and_high_z"] is False  # clamp yok


def test_fair_no_complement():
    from data.model_telemetry import compute_legacy_telemetry
    rec = compute_legacy_telemetry(asset="BTC", action="NO", p_now=1.0, p_ref=1.0,
                                   secs=600, best_bid=0.5, best_ask=0.52, raw_vol=0.8,
                                   fair_yes_val=0.62, net_ev=0.05, fair_gap=0.05,
                                   edge_bin="x", would_enter=True, snapshot_id="s6")
    assert abs(rec["fair_no"] - 0.38) < 1e-9
    assert rec["model_version"] == "LEGACY_GBM_V1"


# ── schema ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_model_decision_events_schema():
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    async with conn.execute("PRAGMA table_info(model_decision_events)") as cur:
        cols = {r[1] for r in await cur.fetchall()}
    await conn.close()
    for col in ("event_id", "snapshot_id", "model_version", "raw_realized_vol",
                "clamped_model_vol", "vol_was_clamped", "vol_clamp_min", "vol_clamp_max",
                "sigma_t", "z_score", "z_abs", "z_overconfidence_flag",
                "vol_clamp_and_high_z", "fair_yes", "fair_no", "action_fair",
                "net_ev", "edge_bin", "would_enter"):
        assert col in cols, f"eksik: {col}"


# ── non-blocking + idempotent + crash-safe ──────────────────────────────────

def test_schedule_no_await():
    import data.model_telemetry as mt
    import inspect
    assert "await " not in inspect.getsource(mt.schedule_telemetry)


@pytest.mark.asyncio
async def test_schedule_non_blocking_fast():
    import data.model_telemetry as mt
    import time
    rec = {"event_id": "e1", "snapshot_id": "s1"}
    with patch("data.model_telemetry._write_telemetry", new_callable=AsyncMock):
        t0 = time.perf_counter()
        mt.schedule_telemetry(rec, db_path=":memory:")
        dt = (time.perf_counter() - t0) * 1000
    assert dt < 5.0


@pytest.mark.asyncio
async def test_write_idempotent():
    from db.schema import init_schema
    import data.model_telemetry as mt
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        rec = mt.compute_legacy_telemetry(asset="BTC", action="YES", p_now=1.01, p_ref=1.0,
            secs=600, best_bid=0.5, best_ask=0.52, raw_vol=0.8, fair_yes_val=0.55,
            net_ev=0.05, fair_gap=0.05, edge_bin="x", would_enter=True, snapshot_id="dup1")
        rec["event_id"] = "dup1"
        await mt._write_telemetry(rec, dbp)
        await mt._write_telemetry(rec, dbp)  # aynı event_id → idempotent
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT COUNT(*) FROM model_decision_events WHERE event_id='dup1'") as c:
            n = (await c.fetchone())[0]
        await conn.close()
    assert n == 1


@pytest.mark.asyncio
async def test_telemetry_db_error_no_crash():
    """DB write hatası → exception loglanır, bot loop crash etmez (worker yutar)."""
    import data.model_telemetry as mt
    async def boom(*a, **k): raise RuntimeError("db locked")
    # _telemetry_worker exception'ı yutmalı
    with patch("data.model_telemetry._write_telemetry", side_effect=boom):
        await mt._telemetry_worker({"event_id": "e", "snapshot_id": "s"}, ":memory:")
    # buraya ulaşması = crash yok
    assert True
