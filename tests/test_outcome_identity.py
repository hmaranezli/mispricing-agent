"""tests/test_outcome_identity.py — tracking_key / paper_id outcome-link fix TDD.

Dar kapsam: model_decision_events ↔ shadow_positions deterministik bağlama.
Model/clamp/threshold/entry/exit DEĞİŞMEZ.
"""
import asyncio
import sys
import os
import time
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_make_tracking_key_v2_unique():
    from data.model_telemetry import make_tracking_key_v2
    # EVENT-LEVEL UNIQUE: signal_ts_ms içerir; slug|asset|tf|action YASAK
    k1 = make_tracking_key_v2("btc-updown-15m-1", 12345, "YES", "u1")
    assert k1 == "btc-updown-15m-1|12345|YES|u1"
    assert make_tracking_key_v2("btc-updown-15m-1", 12345, "NO", "u2") != k1  # farklı action


def test_v2_telemetry_carries_paper_id():
    from data.model_telemetry import compute_legacy_telemetry_v2
    rec = compute_legacy_telemetry_v2(
        asset="BTC", action="YES", slug="s", timeframe="15m", p_now=1.0, p_ref=1.0,
        tte_seconds=600, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54, no_ask_observed=None,
        fair_yes_val=0.55, net_ev=0.05, fair_gap=0.05, edge_bin="x", would_enter=True,
        snapshot_id="s1", fee_adjustment=0.02, decision_threshold=0.05, paper_id="P123")
    assert rec["paper_id"] == "P123"


@pytest.mark.asyncio
async def test_paper_open_writes_tracking_key():
    """paper_tracker shadow_positions'a tracking_key + paper_id yazar."""
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
                    "signal_seconds_remaining": 400, "signal_timestamp_ms": int(time.time()*1000),
                    "yes_fair": 0.60, "no_fair": 0.40, "action_fair": 0.60,
                    "paper_viability": "positive_after_slippage"}
        sig = snapshot["signal_timestamp_ms"]
        with patch("execution.paper_tracker.get_book", new_callable=AsyncMock,
                   return_value={"asks": [{"price": "0.58", "size": "1000"}]}):
            await pt._paper_open_worker(finding, {}, {"position_usd": 1.25}, dbp, 0.1,
                                        snapshot=snapshot, paper_id_override="PAP-1",
                                        tracking_key_override=f"btc-updown-15m-9|{sig}")
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT tracking_key, paper_id FROM shadow_positions") as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] == f"btc-updown-15m-9|{sig}", f"tracking_key yanlış: {row[0]}"
    assert row[1] == "PAP-1"
    pt._active.clear()


def test_schedule_accepts_paper_id():
    """schedule_paper_open paper_id param kabul eder (non-blocking korunur)."""
    import execution.paper_tracker as pt
    import inspect
    sig = inspect.signature(pt.schedule_paper_open)
    assert "paper_id" in sig.parameters
    assert "await " not in inspect.getsource(pt.schedule_paper_open)


def test_resolve_join_method():
    """join_method önceliği: paper_id > tracking_key > slug_action_fallback."""
    from data.model_telemetry import resolve_join_method
    assert resolve_join_method(event_paper_id="P", paper_paper_id="P",
                               event_tk="tk", paper_tk="tk") == "paper_id"
    assert resolve_join_method(event_paper_id=None, paper_paper_id=None,
                               event_tk="tk", paper_tk="tk") == "tracking_key"
    assert resolve_join_method(event_paper_id=None, paper_paper_id=None,
                               event_tk="tk", paper_tk=None) == "slug_action_fallback"
