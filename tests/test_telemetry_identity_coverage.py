"""tests/test_telemetry_identity_coverage.py — Telemetry Identity & Coverage Fix TDD.

tracking_key = slug|signal_ts_ms|action|uuid (action ayrıştırıcı, %100 unique).
INSERT OR IGNORE KALDIRILDI → INSERT + IntegrityError + collision_counter.
would_enter=False coverage (council-veto/below_threshold adaylar loglanır).
Model/clamp/threshold/entry/exit DEĞİŞMEZ.
"""
import asyncio
import sys
import os
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 1. Aynı slug+signal_ts farklı action → farklı tracking_key (action ayrıştırıcı)
def test_same_slug_ts_different_action_different_key():
    from data.model_telemetry import make_tracking_key_v2
    k_yes = make_tracking_key_v2("btc-updown-15m-1", 1000, "YES", "uid1")
    k_no = make_tracking_key_v2("btc-updown-15m-1", 1000, "NO", "uid2")
    assert k_yes != k_no
    assert "YES" in k_yes and "NO" in k_no
    # format: slug|ts|action|uid
    assert k_yes == "btc-updown-15m-1|1000|YES|uid1"


# 2. Duplicate exact tracking_key → IntegrityError → counter++ → crash yok
@pytest.mark.asyncio
async def test_duplicate_tracking_key_counts_collision_no_crash():
    from db.schema import init_schema
    import data.model_telemetry as mt
    import tempfile
    from pathlib import Path
    mt._collision_count = 0
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        rec1 = {"event_id": "e1", "snapshot_id": "s", "model_version": "LEGACY_GBM_V1",
                "telemetry_schema_version": 2, "tracking_key": "TK-DUP", "created_at": "t"}
        rec2 = {"event_id": "e2", "snapshot_id": "s", "model_version": "LEGACY_GBM_V1",
                "telemetry_schema_version": 2, "tracking_key": "TK-DUP", "created_at": "t"}
        await mt._write_telemetry_v2(rec1, dbp)
        # ikinci aynı tracking_key → IntegrityError yakalanır, counter++, crash yok
        await mt._telemetry_worker(rec2, dbp)  # worker exception yutar
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT COUNT(*) FROM model_decision_events WHERE tracking_key='TK-DUP'") as c:
            n = (await c.fetchone())[0]
        await conn.close()
    assert n == 1, "ikinci INSERT reddedilmeli (UNIQUE)"
    assert mt._collision_count >= 1, "collision counter artmalı (sessiz değil)"


# 3. would_enter=False event DB'ye yazılır
@pytest.mark.asyncio
async def test_would_enter_false_event_written():
    from db.schema import init_schema
    import data.model_telemetry as mt
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        rec = mt.compute_legacy_telemetry_v2(
            asset="BTC", action="NO", slug="s", timeframe="15m", p_now=1.0, p_ref=1.0,
            tte_seconds=600, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54, no_ask_observed=None,
            fair_yes_val=0.55, net_ev=0.01, fair_gap=0.01, edge_bin="0.00-0.03",
            would_enter=False, snapshot_id="s|1", tracking_key="s|1|NO|u1",
            fee_adjustment=0.02, decision_threshold=0.05, skip_reason="below_threshold")
        await mt._write_telemetry_v2(rec, dbp)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT would_enter, skip_reason, tracking_key, paper_id FROM model_decision_events") as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] == 0
    assert row[1] == "below_threshold"
    assert row[2] == "s|1|NO|u1"


# 4. would_enter=False paper_id NULL ama tracking_key dolu
def test_would_enter_false_paper_id_null_tracking_key_filled():
    from data.model_telemetry import compute_legacy_telemetry_v2
    rec = compute_legacy_telemetry_v2(
        asset="BTC", action="NO", slug="s", timeframe="15m", p_now=1.0, p_ref=1.0,
        tte_seconds=600, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54, no_ask_observed=None,
        fair_yes_val=0.55, net_ev=0.01, fair_gap=0.01, edge_bin="x", would_enter=False,
        snapshot_id="s|1", tracking_key="s|1|NO|u1", fee_adjustment=0.02,
        decision_threshold=0.05, paper_id=None, skip_reason="council_veto")
    assert rec["paper_id"] is None
    assert rec["tracking_key"] == "s|1|NO|u1"
    assert rec["skip_reason"] == "council_veto"


# 5. would_enter=True paper/shadow tracking_key eşleşir
@pytest.mark.asyncio
async def test_would_enter_true_paper_tracking_key_matches():
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile, time
    from pathlib import Path
    pt._active.clear()
    TK = "btc-updown-15m-9|123|YES|uidX"
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        finding = {"slug": "btc-updown-15m-9", "asset": "BTC", "action": "YES",
                   "best_ask": 0.50, "no_ask": 0.45, "fair_value": 0.60, "edge": 0.10,
                   "fee_adj_edge": 0.054, "edge_bucket": "E50", "seconds_remaining": 400,
                   "yes_token_id": "y", "no_token_id": "n", "ref_price": 1, "cur_price": 1}
        snapshot = {"entry_price": 0.58, "entry_method": "depth_walk", "data_quality": "high",
                    "signal_best_ask": 0.56, "signal_best_bid": 0.54, "signal_depth_walk_entry": 0.58,
                    "signal_fee_adj_edge": 0.054, "signal_net_ev": 0.044, "signal_slippage": 0.036,
                    "signal_seconds_remaining": 400, "signal_timestamp_ms": 123,
                    "yes_fair": 0.60, "no_fair": 0.40, "action_fair": 0.60,
                    "paper_viability": "positive_after_slippage"}
        with patch("execution.paper_tracker.get_book", new_callable=AsyncMock,
                   return_value={"asks": [{"price": "0.58", "size": "1000"}]}):
            await pt._paper_open_worker(finding, {}, {"position_usd": 1.25}, dbp, 0.1,
                                        snapshot=snapshot, paper_id_override="PAP-1",
                                        tracking_key_override=TK)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT tracking_key FROM shadow_positions") as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] == TK
    pt._active.clear()


# 6. slug_action_fallback post-fix final cohort'a girmez
def test_slug_action_fallback_not_final():
    from data.model_telemetry import is_final_join, resolve_join_method
    jm = resolve_join_method(None, None, "tk1", None)
    assert jm == "slug_action_fallback"
    assert is_final_join(jm) is False
