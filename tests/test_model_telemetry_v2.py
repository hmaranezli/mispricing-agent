"""tests/test_model_telemetry_v2.py — Telemetry V2 + counterfactual altyapısı TDD.

V2: NO bid/ask türetimi, TTE izolasyonu, counterfactual_supported, tracking_key,
outcome link. Counterfactual OFFLINE (bot loop'ta değil). Math-safe. V1 karantina.
"""
import asyncio
import sys
import os
import math
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── V2 compute: NO türetim + TTE + tracking_key ─────────────────────────────

def test_v2_no_derived_from_yes_book():
    from data.model_telemetry import compute_legacy_telemetry_v2
    rec = compute_legacy_telemetry_v2(
        asset="BTC", action="NO", slug="btc-updown-15m-1", timeframe="15m",
        p_now=1.0, p_ref=1.0, tte_seconds=600, raw_vol=0.8,
        yes_bid=0.50, yes_ask=0.54, no_ask_observed=None,
        fair_yes_val=0.60, net_ev=0.05, fair_gap=0.05, edge_bin="x",
        would_enter=False, snapshot_id="s1", fee_adjustment=0.02,
        decision_threshold=0.05)
    # no_ask = 1 - yes_bid = 0.50; no_bid = 1 - yes_ask = 0.46
    assert rec["no_ask"] == 0.50
    assert rec["no_bid"] == 0.46
    assert rec["bid_ask_source"] == "derived_from_yes_book"
    # NO action → action_ask = no_ask
    assert rec["action_ask"] == 0.50
    assert rec["action_bid"] == 0.46


def test_v2_no_observed_ask_used():
    from data.model_telemetry import compute_legacy_telemetry_v2
    rec = compute_legacy_telemetry_v2(
        asset="BTC", action="NO", slug="s", timeframe="15m", p_now=1.0, p_ref=1.0,
        tte_seconds=600, raw_vol=0.8, yes_bid=0.50, yes_ask=0.54, no_ask_observed=0.45,
        fair_yes_val=0.60, net_ev=0.05, fair_gap=0.05, edge_bin="x",
        would_enter=False, snapshot_id="s2", fee_adjustment=0.02, decision_threshold=0.05)
    assert rec["no_ask"] == 0.45  # gözlenen kullanılır
    assert rec["bid_ask_source"] == "observed_no_ask"


def test_v2_tte_logged():
    from data.model_telemetry import compute_legacy_telemetry_v2
    rec = compute_legacy_telemetry_v2(
        asset="BTC", action="YES", slug="s", timeframe="15m", p_now=1.0, p_ref=1.0,
        tte_seconds=600, raw_vol=0.8, yes_bid=0.50, yes_ask=0.54, no_ask_observed=None,
        fair_yes_val=0.55, net_ev=0.05, fair_gap=0.05, edge_bin="x",
        would_enter=True, snapshot_id="s3", fee_adjustment=0.02, decision_threshold=0.05)
    assert rec["time_to_expiry_seconds"] == 600
    assert rec["time_to_expiry_ms"] == 600000
    assert abs(rec["pricing_tte_years"] - 600/31_557_600.0) < 1e-12
    assert rec["pricing_model_tte_input"] == rec["pricing_tte_years"]
    assert rec["telemetry_schema_version"] == 2


def test_v2_tracking_key():
    from data.model_telemetry import compute_legacy_telemetry_v2
    # tracking_key None → snapshot_id'den türetilir (EVENT-LEVEL UNIQUE)
    rec = compute_legacy_telemetry_v2(
        asset="BTC", action="YES", slug="btc-updown-15m-1", timeframe="15m",
        p_now=1.0, p_ref=1.0, tte_seconds=600, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54,
        no_ask_observed=None, fair_yes_val=0.55, net_ev=0.05, fair_gap=0.05,
        edge_bin="x", would_enter=True, snapshot_id="btc-updown-15m-1|9876",
        fee_adjustment=0.02, decision_threshold=0.05)
    assert rec["tracking_key"] == "btc-updown-15m-1|9876"  # snapshot_id (unique), 4-parça DEĞİL
    assert rec["outcome_link_supported"] is True


def test_v2_counterfactual_supported_flag():
    from data.model_telemetry import compute_legacy_telemetry_v2
    ok = compute_legacy_telemetry_v2(
        asset="BTC", action="YES", slug="s", timeframe="15m", p_now=1.0, p_ref=1.0,
        tte_seconds=600, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54, no_ask_observed=None,
        fair_yes_val=0.55, net_ev=0.05, fair_gap=0.05, edge_bin="x",
        would_enter=True, snapshot_id="s5", fee_adjustment=0.02, decision_threshold=0.05)
    assert ok["counterfactual_supported"] is True
    assert ok["counterfactual_missing_reason"] is None
    # TTE eksik → supported False
    bad = compute_legacy_telemetry_v2(
        asset="BTC", action="YES", slug="s", timeframe="15m", p_now=1.0, p_ref=1.0,
        tte_seconds=None, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54, no_ask_observed=None,
        fair_yes_val=0.55, net_ev=0.05, fair_gap=0.05, edge_bin="x",
        would_enter=True, snapshot_id="s6", fee_adjustment=0.02, decision_threshold=0.05)
    assert bad["counterfactual_supported"] is False
    assert bad["counterfactual_missing_reason"]


# ── Offline counterfactual (read-only, same-event) ──────────────────────────

def test_counterfactual_uses_raw_vol():
    from data.model_telemetry import compute_counterfactual
    # clamp aktif: raw 4.0, clamped 3.0 → raw counterfactual farklı sigma_t
    ev = dict(raw_realized_vol=4.0, clamped_model_vol=3.0, p_now=1.05, ref_price=1.0,
              pricing_tte_years=600/31_557_600.0, action="YES", action_ask=0.52,
              fee_adjustment=0.02, decision_threshold=0.05)
    cf = compute_counterfactual(ev)
    assert cf["counterfactual_supported"] is True
    # sigma_t_raw = raw * sqrt(years); z_raw = log(p_now/p_ref)/sigma_t_raw
    years = 600/31_557_600.0
    sig_raw = 4.0 * math.sqrt(years)
    z_raw = math.log(1.05/1.0)/sig_raw
    fair_raw = 0.5*(1+math.erf(z_raw/math.sqrt(2)))
    assert abs(cf["raw_vol_counterfactual_action_fair"] - fair_raw) < 1e-6
    # net_ev_raw = fair_raw*(1-0.02) - (0.52+0.01)
    exp_nev = fair_raw*0.98 - (0.52+0.01)
    assert abs(cf["raw_vol_counterfactual_net_ev"] - exp_nev) < 1e-6


def test_counterfactual_suppressed_entry():
    from data.model_telemetry import compute_counterfactual
    # lower clamp: raw 0.20 (<0.30), clamped 0.30 → raw daha düşük vol → daha ekstrem fair
    ev = dict(raw_realized_vol=0.20, clamped_model_vol=0.30, p_now=1.02, ref_price=1.0,
              pricing_tte_years=600/31_557_600.0, action="YES", action_ask=0.55,
              fee_adjustment=0.02, decision_threshold=0.05, would_enter=0, net_ev=0.02)
    cf = compute_counterfactual(ev)
    # raw vol düşük → fair daha confident → net_ev daha yüksek → unclamped enter olabilir
    assert "would_enter_unclamped" in cf
    assert "lower_clamp_suppressed_entry" in cf


def test_counterfactual_math_safe_near_expiry():
    from data.model_telemetry import compute_counterfactual
    # TTE → 0 → sigma_t → 0 → div by zero riski
    ev = dict(raw_realized_vol=0.8, clamped_model_vol=0.8, p_now=1.0, ref_price=1.0,
              pricing_tte_years=0.0, action="YES", action_ask=0.52,
              fee_adjustment=0.02, decision_threshold=0.05)
    cf = compute_counterfactual(ev)  # crash etmemeli
    assert cf["counterfactual_supported"] is False
    assert "math_error" in cf["counterfactual_missing_reason"] or "tte" in cf["counterfactual_missing_reason"].lower()


def test_counterfactual_missing_no_ask():
    from data.model_telemetry import compute_counterfactual
    ev = dict(raw_realized_vol=0.8, clamped_model_vol=0.8, p_now=1.0, ref_price=1.0,
              pricing_tte_years=600/31_557_600.0, action="NO", action_ask=None,
              fee_adjustment=0.02, decision_threshold=0.05)
    cf = compute_counterfactual(ev)
    assert cf["counterfactual_supported"] is False
    assert cf["counterfactual_missing_reason"]


# ── schema V2 + V1 karantina ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_v2_schema_columns():
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    async with conn.execute("PRAGMA table_info(model_decision_events)") as cur:
        cols = {r[1] for r in await cur.fetchall()}
    await conn.close()
    for col in ("telemetry_schema_version", "yes_bid", "yes_ask", "no_bid", "no_ask",
                "bid_ask_source", "action_bid", "action_ask", "action_spread",
                "time_to_expiry_seconds", "time_to_expiry_ms", "pricing_tte_years",
                "pricing_model_tte_input", "window_open_ts", "window_close_ts",
                "counterfactual_supported", "counterfactual_missing_reason",
                "outcome_link_supported", "tracking_key", "paper_id", "shadow_candidate_id"):
        assert col in cols, f"eksik V2 kolon: {col}"


@pytest.mark.asyncio
async def test_v1_events_quarantined_not_in_v2():
    """V2 raporu telemetry_schema_version=2 filtreler; V1 (1/NULL) dahil değil."""
    from db.schema import init_schema
    import data.model_telemetry as mt
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn)
        # V1 event simüle (version NULL)
        await conn.execute("INSERT INTO model_decision_events (event_id, snapshot_id, model_version) VALUES ('v1e','v1s','LEGACY_GBM_V1')")
        await conn.commit(); await conn.close()
        # V2 event yaz
        rec = mt.compute_legacy_telemetry_v2(
            asset="BTC", action="YES", slug="s", timeframe="15m", p_now=1.0, p_ref=1.0,
            tte_seconds=600, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54, no_ask_observed=None,
            fair_yes_val=0.55, net_ev=0.05, fair_gap=0.05, edge_bin="x",
            would_enter=True, snapshot_id="v2s", fee_adjustment=0.02, decision_threshold=0.05)
        await mt._write_telemetry_v2(rec, dbp)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT COUNT(*) FROM model_decision_events WHERE telemetry_schema_version=2") as c:
            v2n = (await c.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM model_decision_events") as c:
            total = (await c.fetchone())[0]
        await conn.close()
    assert v2n == 1 and total == 2  # V1 korundu, V2 ayrı


# ── non-blocking + crash-safe ───────────────────────────────────────────────

def test_v2_schedule_no_await():
    import data.model_telemetry as mt
    import inspect
    assert "await " not in inspect.getsource(mt.schedule_telemetry)


@pytest.mark.asyncio
async def test_v2_write_idempotent():
    from db.schema import init_schema
    import data.model_telemetry as mt
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        rec = mt.compute_legacy_telemetry_v2(
            asset="BTC", action="YES", slug="s", timeframe="15m", p_now=1.0, p_ref=1.0,
            tte_seconds=600, raw_vol=0.8, yes_bid=0.5, yes_ask=0.54, no_ask_observed=None,
            fair_yes_val=0.55, net_ev=0.05, fair_gap=0.05, edge_bin="x",
            would_enter=True, snapshot_id="dup", fee_adjustment=0.02, decision_threshold=0.05)
        await mt._write_telemetry_v2(rec, dbp)
        await mt._write_telemetry_v2(rec, dbp)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute("SELECT COUNT(*) FROM model_decision_events WHERE event_id=?", (rec["event_id"],)) as c:
            n = (await c.fetchone())[0]
        await conn.close()
    assert n == 1
