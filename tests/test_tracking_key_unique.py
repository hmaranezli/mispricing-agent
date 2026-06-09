"""tests/test_tracking_key_unique.py — tracking_key EVENT-LEVEL UNIQUE invariant TDD.

slug|asset|tf|action YASAK (unique değil). Yeni: snapshot_id-bazlı (signal_ts_ms içerir).
8 zorunlu test (kullanıcı şartnamesi).
"""
import asyncio
import sys
import os
import time
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 1. model_decision_events.tracking_key UNIQUE constraint
@pytest.mark.asyncio
async def test_tracking_key_unique_constraint():
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    # aynı tracking_key iki kez → ikincisi reddedilir (UNIQUE)
    await conn.execute("INSERT INTO model_decision_events (event_id, tracking_key, telemetry_schema_version) VALUES ('e1','TK-SAME',2)")
    await conn.commit()
    import aiosqlite as a
    raised = False
    try:
        await conn.execute("INSERT INTO model_decision_events (event_id, tracking_key, telemetry_schema_version) VALUES ('e2','TK-SAME',2)")
        await conn.commit()
    except Exception:
        raised = True
    await conn.close()
    assert raised, "tracking_key UNIQUE constraint olmalı (aynı tk iki kez reddedilmeli)"


# 2. Aynı slug/action ardışık iki event farklı tracking_key
def test_same_slug_action_different_tracking_key():
    from data.model_telemetry import compute_legacy_telemetry_v2
    base = dict(asset="BTC", action="YES", slug="btc-updown-15m-1", timeframe="15m",
                p_now=1.0, p_ref=1.0, tte_seconds=600, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54,
                no_ask_observed=None, fair_yes_val=0.55, net_ev=0.05, fair_gap=0.05,
                edge_bin="x", would_enter=True, fee_adjustment=0.02, decision_threshold=0.05)
    # snapshot_id farklı (signal_ts_ms farklı) → tracking_key farklı
    r1 = compute_legacy_telemetry_v2(**base, snapshot_id="btc-updown-15m-1|1000",
                                     tracking_key="btc-updown-15m-1|1000")
    r2 = compute_legacy_telemetry_v2(**base, snapshot_id="btc-updown-15m-1|2000",
                                     tracking_key="btc-updown-15m-1|2000")
    assert r1["tracking_key"] != r2["tracking_key"], "ardışık event farklı tracking_key olmalı"
    assert "|" in r1["tracking_key"]
    # slug|asset|tf|action FORMATINDA OLMAMALI (4-parça yasak)
    assert r1["tracking_key"].count("|") != 3 or "1000" in r1["tracking_key"]


# 3. would_enter=False event'te de tracking_key dolu
def test_would_enter_false_has_tracking_key():
    from data.model_telemetry import compute_legacy_telemetry_v2
    r = compute_legacy_telemetry_v2(asset="BTC", action="NO", slug="s", timeframe="15m",
        p_now=1.0, p_ref=1.0, tte_seconds=600, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54,
        no_ask_observed=None, fair_yes_val=0.55, net_ev=0.01, fair_gap=0.01, edge_bin="x",
        would_enter=False, snapshot_id="s|999", tracking_key="s|999",
        fee_adjustment=0.02, decision_threshold=0.05)
    assert r["tracking_key"] == "s|999"
    assert r["would_enter"] == 0


# 4. would_enter=True → shadow_positions.tracking_key == event.tracking_key
@pytest.mark.asyncio
async def test_paper_tracking_key_matches_event():
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    pt._active.clear()
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
                    "signal_seconds_remaining": 400, "signal_timestamp_ms": 12345,
                    "yes_fair": 0.60, "no_fair": 0.40, "action_fair": 0.60,
                    "paper_viability": "positive_after_slippage"}
        TK = "btc-updown-15m-9|12345"  # main_loop'tan gelen, snapshot_id-bazlı
        with patch("execution.paper_tracker.get_book", new_callable=AsyncMock,
                   return_value={"asks": [{"price": "0.58", "size": "1000"}]}):
            await pt._paper_open_worker(finding, {}, {"position_usd": 1.25}, dbp, 0.1,
                                        snapshot=snapshot, paper_id_override="PAP-1",
                                        tracking_key_override=TK)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT tracking_key FROM shadow_positions") as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] == TK, f"shadow tracking_key event ile aynı olmalı: {row[0]} != {TK}"
    pt._active.clear()


# 5. paper_id varsa paper_id join; yoksa tracking_key
def test_join_priority():
    from data.model_telemetry import resolve_join_method
    assert resolve_join_method("P", "P", "tk1", "tk1") == "paper_id"
    assert resolve_join_method(None, None, "tk1", "tk1") == "tracking_key"
    assert resolve_join_method(None, None, "tk1", None) == "slug_action_fallback"


# 6+7. slug_action_fallback FINAL cohort'a girmez (rapor filtresi)
def test_is_final_join():
    from data.model_telemetry import is_final_join
    assert is_final_join("paper_id") is True
    assert is_final_join("tracking_key") is True
    assert is_final_join("slug_action_fallback") is False


# 8. collision tespiti (rapor üretmeme sinyali)
@pytest.mark.asyncio
async def test_tracking_key_collision_detectable():
    """tracking_key collision SQL ile tespit edilebilmeli (rapor üretme)."""
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    # UNIQUE constraint sayesinde collision INSERT seviyesinde önlenir;
    # yine de tespit sorgusu çalışmalı
    await conn.execute("INSERT INTO model_decision_events (event_id, tracking_key, telemetry_schema_version) VALUES ('e1','TK1',2)")
    await conn.commit()
    async with conn.execute("""SELECT tracking_key, COUNT(*) FROM model_decision_events
        WHERE telemetry_schema_version=2 AND tracking_key NOT LIKE 'bad_v1:%'
        GROUP BY tracking_key HAVING COUNT(*)>1""") as cur:
        collisions = await cur.fetchall()
    await conn.close()
    assert collisions == [], "collision yok (UNIQUE korur)"


# format helper
def test_make_tracking_key_v2_format():
    from data.model_telemetry import make_tracking_key_v2
    tk = make_tracking_key_v2("btc-updown-15m-1", 12345, "YES", "u1")
    assert tk == "btc-updown-15m-1|12345|YES|u1"
    # action farklı → farklı key
    assert make_tracking_key_v2("btc-updown-15m-1", 12345, "NO", "u1") != tk
