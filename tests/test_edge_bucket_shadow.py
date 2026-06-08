"""tests/test_edge_bucket_shadow.py — Edge Bucket Shadow Experiment TDD.

Paper cohort, düşük edge (fee_adj >= 0.03) adayları council-bağımsız izler.
Canlı scan_edges / MIN_EDGE / entry / stop DEĞİŞMEZ.
"""
import asyncio
import sys
import os
import aiosqlite
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── edge_bucket sınıflandırma ────────────────────────────────────────────────

def test_edge_bucket_boundaries():
    from council.scout import _edge_bucket
    assert _edge_bucket(0.029) is None      # < 0.03 paper evren dışı
    assert _edge_bucket(0.030) == "E30"
    assert _edge_bucket(0.034) == "E30"
    assert _edge_bucket(0.035) == "E35"
    assert _edge_bucket(0.039) == "E35"
    assert _edge_bucket(0.040) == "E40"
    assert _edge_bucket(0.049) == "E40"
    assert _edge_bucket(0.050) == "E50"
    assert _edge_bucket(0.10) == "E50"
    assert _edge_bucket(None) is None


# ── shadow fee_adj hesabı ────────────────────────────────────────────────────

def test_shadow_fee_adj_yes():
    from council.scout import _shadow_fee_adj
    f = {"action": "YES", "fair_value": 0.60, "best_ask": 0.50, "taker_fee": 0.02}
    # 0.60*0.98 - (0.50+0.01) = 0.588 - 0.51 = 0.078
    assert abs(_shadow_fee_adj(f) - 0.078) < 1e-6


def test_shadow_fee_adj_no():
    from council.scout import _shadow_fee_adj
    f = {"action": "NO", "fair_value": 0.40, "best_ask": 0.55,
         "no_ask": 0.45, "taker_fee": 0.02}
    # (1-0.40)*0.98 - (0.45+0.01) = 0.588 - 0.46 = 0.128
    assert abs(_shadow_fee_adj(f) - 0.128) < 1e-6


# ── canlı scan_edges DEĞİŞMEDİ (hâlâ 0.05 raw) ──────────────────────────────

def test_edge_signal_default_unchanged():
    """_edge_signal default min_edge config.MIN_EDGE_PCT (canlı davranış)."""
    from council.scout import _edge_signal
    import config
    # raw edge 0.04 < 0.05 → None (canlı eşik korunur)
    assert _edge_signal(fair=0.62, best_ask=0.58, best_bid=0.42) is None
    # raw edge 0.06 >= 0.05 → sinyal
    sig = _edge_signal(fair=0.66, best_ask=0.60, best_bid=0.40)
    assert sig is not None and sig["action"] == "YES"


def test_edge_signal_shadow_min_edge():
    """min_edge override ile düşük edge sinyal üretir (shadow)."""
    from council.scout import _edge_signal
    # raw edge 0.04, min_edge=0.03 → sinyal üretir
    sig = _edge_signal(fair=0.62, best_ask=0.58, best_bid=0.42, min_edge=0.03)
    assert sig is not None
    assert sig["action"] == "YES"


# ── paper_tracker edge_bucket yazımı ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_paper_open_writes_edge_bucket():
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    pt._active.clear()
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        finding = {"slug": "btc-updown-15m-7", "asset": "BTC", "action": "YES",
                   "best_ask": 0.50, "fair_value": 0.60, "edge": 0.10,
                   "fee_adj_edge": 0.078, "edge_bucket": "E50",
                   "yes_token_id": "y", "no_token_id": "n", "seconds_remaining": 400,
                   "ref_price": 100.0, "cur_price": 101.0}
        fake_book = {"asks": [{"price": "0.50", "size": "1000"}]}
        with patch("execution.paper_tracker.get_book", new_callable=AsyncMock, return_value=fake_book):
            await pt._paper_open_worker(finding, {"confidence_score": None},
                                        {"position_usd": 1.25}, dbp, 0.1)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute(
            "SELECT edge_bucket, fee_adj_edge FROM shadow_positions") as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] == "E50"
    assert abs(row[1] - 0.078) < 1e-6
    pt._active.clear()


@pytest.mark.asyncio
async def test_shadow_positions_has_bucket_columns():
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    async with conn.execute("PRAGMA table_info(shadow_positions)") as cur:
        cols = {r[1] for r in await cur.fetchall()}
    await conn.close()
    for col in ("edge_bucket", "fee_adj_edge", "depth_walk_estimated_fill",
                "estimated_slippage_pct", "net_ev_after_estimated_slippage",
                "paper_viability"):
        assert col in cols, f"eksik kolon: {col}"


# ── net EV after slippage + viability ───────────────────────────────────────

def test_net_ev_after_slippage_positive():
    from execution.paper_tracker import _net_ev_after_slippage
    # YES: fair 0.60, est_fill 0.51, fee 0.02 → 0.60*0.98 - 0.51 = 0.078 > 0
    net_ev, viability = _net_ev_after_slippage("YES", fair=0.60, est_fill=0.51, fee=0.02)
    assert net_ev > 0
    assert viability == "positive_after_slippage"


def test_net_ev_after_slippage_negative():
    from execution.paper_tracker import _net_ev_after_slippage
    # YES: fair 0.55, est_fill 0.56 → 0.55*0.98 - 0.56 = -0.021 < 0
    net_ev, viability = _net_ev_after_slippage("YES", fair=0.55, est_fill=0.56, fee=0.02)
    assert net_ev <= 0
    assert viability == "negative_after_slippage"


def test_net_ev_after_slippage_no_action():
    from execution.paper_tracker import _net_ev_after_slippage
    # NO: (1-fair)*(1-fee) - est_fill
    net_ev, viability = _net_ev_after_slippage("NO", fair=0.40, est_fill=0.46, fee=0.02)
    # (0.60)*0.98 - 0.46 = 0.588 - 0.46 = 0.128 > 0
    assert net_ev > 0
    assert viability == "positive_after_slippage"


@pytest.mark.asyncio
async def test_paper_open_writes_net_ev_and_viability():
    from db.schema import init_schema
    import execution.paper_tracker as pt
    import tempfile
    from pathlib import Path
    pt._active.clear()
    with tempfile.TemporaryDirectory() as d:
        dbp = Path(d) / "t.db"
        conn = await aiosqlite.connect(str(dbp)); await init_schema(conn); await conn.close()
        finding = {"slug": "btc-updown-15m-8", "asset": "BTC", "action": "YES",
                   "best_ask": 0.50, "fair_value": 0.60, "edge": 0.10,
                   "fee_adj_edge": 0.078, "edge_bucket": "E50",
                   "yes_token_id": "y", "no_token_id": "n", "seconds_remaining": 400,
                   "ref_price": 100.0, "cur_price": 101.0}
        fake_book = {"asks": [{"price": "0.51", "size": "1000"}]}
        with patch("execution.paper_tracker.get_book", new_callable=AsyncMock, return_value=fake_book):
            await pt._paper_open_worker(finding, {"confidence_score": None},
                                        {"position_usd": 1.25}, dbp, 0.1)
        conn = await aiosqlite.connect(str(dbp))
        async with conn.execute(
            "SELECT net_ev_after_estimated_slippage, paper_viability, "
            "estimated_slippage_pct, depth_walk_estimated_fill FROM shadow_positions") as c:
            row = await c.fetchone()
        await conn.close()
    assert row[0] is not None      # net_ev hesaplandı
    assert row[1] in ("positive_after_slippage", "negative_after_slippage")
    assert row[2] is not None      # estimated_slippage_pct
    assert row[3] == 0.51          # depth_walk_estimated_fill
    pt._active.clear()


# ── scan_shadow_edges entegrasyon ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_shadow_edges_returns_bucketed():
    """scan_shadow_edges düşük-edge adayları fee_adj + edge_bucket ile döndürür."""
    import council.scout as scout

    # Düşük raw edge bir finding üretecek market (raw 0.04 < live 0.05)
    fake_finding = {
        "slug": "btc-updown-15m-1", "asset": "BTC", "action": "YES",
        "fair_value": 0.64, "best_ask": 0.57, "best_bid": 0.40,
        "edge": 0.07, "seconds_remaining": 400, "taker_fee": 0.02,
        "no_ask": None, "yes_token_id": "y", "no_token_id": "n",
    }  # fee_adj = 0.64*0.98 - (0.57+0.01) = 0.0472 → E40

    async def fake_process(m, *a, **k):
        return fake_finding

    scout._markets_cache = [{"slug": "btc-updown-15m-1"}]
    scout._markets_cache_ts = 9e18  # cache taze
    with patch("council.scout._process_market", side_effect=fake_process), \
         patch("council.scout._get_all_vols", new_callable=AsyncMock, return_value={}), \
         patch("council.scout._get_market_state", new_callable=AsyncMock, return_value={}), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=100.0):
        out = await scout.scan_shadow_edges()

    assert out, "shadow scan düşük-edge aday döndürmeli"
    f = out[0]
    assert "fee_adj_edge" in f
    assert "edge_bucket" in f
    assert f["edge_bucket"] in ("E30", "E35", "E40", "E50")
    scout._markets_cache = []
    scout._markets_cache_ts = 0.0
