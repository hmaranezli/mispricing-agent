"""tests/test_telemetry_v31.py — Telemetry V3.1 Data Integrity + Lifecycle TDD.

Fix1 snapshot_age, Fix2 spread crossed-flag, Fix3 hl_drift, Fix4+4.1 lifecycle+restart recovery.
Model/clamp/threshold/entry/exit/TP DEĞİŞMEZ. Salt telemetri.
"""
import asyncio
import sys
import os
import time
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Fix 2: action_spread crossed-flag + consistent_spread ────────────────────

def test_spread_crossed_flag_set():
    """Crossed book (yes_bid>yes_ask) → spread_crossed_flag=1, net_ev DEĞİŞMEZ."""
    from data.model_telemetry import compute_legacy_telemetry_v2
    # NO action: action_bid=no_bid=1-yes_ask, action_ask=no_ask=1-yes_bid (observed yoksa)
    # yes_bid=0.54 > yes_ask=0.53 → crossed
    rec = compute_legacy_telemetry_v2(
        asset="XRP", action="NO", slug="s", timeframe="5m", p_now=1.0, p_ref=1.0,
        tte_seconds=200, raw_vol=0.8, yes_bid=0.54, yes_ask=0.53, no_ask_observed=None,
        fair_yes_val=0.6, net_ev=0.12, fair_gap=0.12, edge_bin="x", would_enter=True,
        snapshot_id="s|1", tracking_key="s|1|NO|u", fee_adjustment=0.02, decision_threshold=0.05)
    assert rec["spread_crossed_flag"] == 1
    assert rec["net_ev"] == 0.12  # edge ZEHİRLENMEDİ
    # consistent_spread = yes_ask - yes_bid (negatif çünkü crossed)
    assert abs(rec["bid_ask_consistent_spread"] - (0.53 - 0.54)) < 1e-9


def test_spread_normal_flag_zero():
    from data.model_telemetry import compute_legacy_telemetry_v2
    rec = compute_legacy_telemetry_v2(
        asset="BTC", action="YES", slug="s", timeframe="5m", p_now=1.0, p_ref=1.0,
        tte_seconds=200, raw_vol=0.8, yes_bid=0.50, yes_ask=0.54, no_ask_observed=None,
        fair_yes_val=0.6, net_ev=0.08, fair_gap=0.08, edge_bin="x", would_enter=True,
        snapshot_id="s|2", tracking_key="s|2|YES|u", fee_adjustment=0.02, decision_threshold=0.05)
    assert rec["spread_crossed_flag"] == 0
    assert abs(rec["bid_ask_consistent_spread"] - 0.04) < 1e-9


# ── Fix 1: snapshot_age_ms hook'tan dolu geçer ───────────────────────────────

def test_snapshot_age_passed():
    from data.model_telemetry import compute_legacy_telemetry_v2
    rec = compute_legacy_telemetry_v2(
        asset="BTC", action="YES", slug="s", timeframe="5m", p_now=1.0, p_ref=1.0,
        tte_seconds=200, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54, no_ask_observed=None,
        fair_yes_val=0.6, net_ev=0.08, fair_gap=0.08, edge_bin="x", would_enter=True,
        snapshot_id="s|3", tracking_key="s|3|YES|u", fee_adjustment=0.02,
        decision_threshold=0.05, snapshot_age_ms=1234)
    assert rec["snapshot_age_ms"] == 1234


# ── Fix 3: hl_drift_at_entry logla (salt-okunur) ─────────────────────────────

def test_hl_drift_logged():
    from data.model_telemetry import compute_legacy_telemetry_v2
    rec = compute_legacy_telemetry_v2(
        asset="BTC", action="YES", slug="s", timeframe="5m", p_now=1.0, p_ref=1.0,
        tte_seconds=200, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54, no_ask_observed=None,
        fair_yes_val=0.6, net_ev=0.08, fair_gap=0.08, edge_bin="x", would_enter=True,
        snapshot_id="s|4", tracking_key="s|4|YES|u", fee_adjustment=0.02,
        decision_threshold=0.05, hl_drift_at_entry=0.0025)
    assert rec["hl_drift_at_entry"] == 0.0025


# ── Fix 4.1: Restart Recovery — orphan open paper invalid ────────────────────

@pytest.mark.asyncio
async def test_restart_recovery_marks_orphan_invalid():
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn)
        # önceki process'ten kalan açık paper
        await conn.execute("""INSERT INTO shadow_positions
            (paper_id, slug, asset, action, status, time_to_mfe_s, mfe_mae_time_valid, created_at)
            VALUES ('orphan1','s','BTC','YES','open',5.0,1,'t')""")
        await conn.commit(); await conn.close()
        await pt.recover_orphan_open_paper(dbp)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT time_to_mfe_s, mfe_mae_time_valid, mfe_mae_time_invalid_reason FROM shadow_positions WHERE paper_id='orphan1'") as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] is None  # time NULL'landı
    assert row[1] == 0  # valid=0
    assert row[2] == "process_restart"


# ── Fix 4: Clean new trade — valid=1 + time damgalı ──────────────────────────

@pytest.mark.asyncio
async def test_clean_new_trade_valid_one():
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    pt._active.clear()
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        finding = {"slug": "btc-updown-5m-1", "asset": "BTC", "action": "YES",
                   "best_ask": 0.50, "no_ask": 0.45, "fair_value": 0.60, "edge": 0.10,
                   "fee_adj_edge": 0.054, "edge_bucket": "E50", "seconds_remaining": 300,
                   "yes_token_id": "y", "no_token_id": "n", "ref_price": 1, "cur_price": 1}
        snapshot = {"entry_price": 0.58, "entry_method": "depth_walk", "data_quality": "high",
                    "signal_best_ask": 0.56, "signal_best_bid": 0.54, "signal_depth_walk_entry": 0.58,
                    "signal_fee_adj_edge": 0.054, "signal_net_ev": 0.044, "signal_slippage": 0.036,
                    "signal_seconds_remaining": 300, "signal_timestamp_ms": 123,
                    "yes_fair": 0.60, "no_fair": 0.40, "action_fair": 0.60,
                    "paper_viability": "positive_after_slippage"}
        with patch("execution.paper_tracker.get_book", new_callable=AsyncMock,
                   return_value={"asks": [{"price": "0.58", "size": "1000"}]}):
            await pt._paper_open_worker(finding, {}, {"position_usd": 1.25}, dbp, 0.1,
                                        snapshot=snapshot, paper_id_override="P1",
                                        tracking_key_override="btc-updown-5m-1|123|YES|u")
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT mfe_mae_time_valid FROM shadow_positions WHERE paper_id='P1'") as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] == 1  # yeni paper bu process'te → valid=1
    pt._active.clear()


# ── Fix 4: time_to_mfe/mae peak anında damgalanır ───────────────────────────

def test_time_to_mfe_mae_stamped_on_peak():
    """dd yeni peak/trough yapınca state['_t_mfe']/['_t_mae'] elapsed ile damgalanır."""
    from execution.paper_tracker import _stamp_mfe_mae_time
    state = {"_mfe_peak": 0.0, "_mae_trough": 0.0}
    # ilk favorable hareket → _t_mfe damgalanır
    _stamp_mfe_mae_time(state, dd=0.05, elapsed=12.0)
    assert state["_mfe_peak"] == 0.05 and state["_t_mfe"] == 12.0
    # daha yüksek peak → _t_mfe güncellenir
    _stamp_mfe_mae_time(state, dd=0.08, elapsed=30.0)
    assert state["_mfe_peak"] == 0.08 and state["_t_mfe"] == 30.0
    # peak düşerse _t_mfe DEĞİŞMEZ (peak korunur)
    _stamp_mfe_mae_time(state, dd=0.02, elapsed=45.0)
    assert state["_mfe_peak"] == 0.08 and state["_t_mfe"] == 30.0
    # adverse hareket → _t_mae damgalanır
    _stamp_mfe_mae_time(state, dd=-0.04, elapsed=50.0)
    assert state["_mae_trough"] == -0.04 and state["_t_mae"] == 50.0


# ── schema V3.1 kolonları ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_v31_schema_columns():
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    async with conn.execute("PRAGMA table_info(model_decision_events)") as cur:
        mde = {r[1] for r in await cur.fetchall()}
    async with conn.execute("PRAGMA table_info(shadow_positions)") as cur:
        sp = {r[1] for r in await cur.fetchall()}
    await conn.close()
    for c in ("spread_crossed_flag", "bid_ask_consistent_spread", "hl_drift_at_entry"):
        assert c in mde, f"eksik: {c}"
    for c in ("time_to_mfe_s", "time_to_mae_s", "resolve_ts", "mfe_mae_time_valid", "mfe_mae_time_invalid_reason"):
        assert c in sp, f"eksik: {c}"
