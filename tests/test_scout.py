"""
tests/test_scout.py — council/scout.py testleri.
Unit testler (_asset_of, _edge_signal) + gerçek API integration testleri.
"""
import asyncio
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from council.scout import scan_edges, _asset_of, _edge_signal

# ── Unit testler ──────────────────────────────────────────────────────────────

def test_asset_of_bitcoin():
    assert _asset_of("Bitcoin Up or Down") == "BTC"


def test_asset_of_ethereum():
    assert _asset_of("Ethereum Up or Down") == "ETH"


def test_asset_of_btc_short():
    assert _asset_of("BTC-USD Up or Down") == "BTC"


def test_asset_of_solana():
    assert _asset_of("Solana Up or Down") == "SOL"


def test_asset_of_xrp():
    assert _asset_of("XRP Up or Down") == "XRP"


def test_asset_of_unknown_returns_none():
    assert _asset_of("Dogecoin Up or Down") is None


def test_asset_of_empty_returns_none():
    assert _asset_of("") is None


def test_asset_of_none_returns_none():
    assert _asset_of(None) is None


def test_edge_signal_yes_cheap():
    """fair > ask yeterince → YES al."""
    result = _edge_signal(fair=0.70, best_ask=0.40, best_bid=0.39)
    assert result is not None
    assert result["action"] == "YES"
    assert abs(result["edge"] - 0.30) < 1e-6


def test_edge_signal_no_cheap():
    """bid > fair yeterince → NO al."""
    result = _edge_signal(fair=0.30, best_ask=0.62, best_bid=0.60)
    assert result is not None
    assert result["action"] == "NO"
    assert abs(result["edge"] - 0.30) < 1e-6


def test_edge_signal_no_edge_when_fair():
    """fair ≈ fiyat → edge yok → None."""
    result = _edge_signal(fair=0.50, best_ask=0.51, best_bid=0.49)
    assert result is None


def test_edge_signal_below_min_threshold_yes():
    """Edge var ama MIN_EDGE_PCT altında → None. (MIN_EDGE_PCT=0.08)"""
    # 0.57 - 0.50 = 0.07 < 0.08
    result = _edge_signal(fair=0.57, best_ask=0.50, best_bid=0.49)
    assert result is None


def test_edge_signal_below_min_threshold_no():
    """NO edge ama MIN_EDGE_PCT altında → None."""
    # best_bid - fair = 0.50 - 0.44 = 0.06 < 0.08
    result = _edge_signal(fair=0.44, best_ask=0.52, best_bid=0.50)
    assert result is None


def test_edge_signal_exact_min_threshold():
    """MIN_EDGE_PCT (0.08) üstünde edge → geçer. Float kesinliğinden kaçınmak için 0.10 kullan."""
    # 0.60 - 0.50 = 0.10 >= 0.08 → geçmeli
    result = _edge_signal(fair=0.60, best_ask=0.50, best_bid=0.49)
    assert result is not None
    assert result["action"] == "YES"


# ── Integration: gerçek API ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_edges_returns_list():
    findings = await scan_edges()
    assert isinstance(findings, list)


@pytest.mark.asyncio
async def test_scan_edges_findings_have_required_fields():
    """Her bulgu zorunlu alanları içeriyor."""
    findings = await scan_edges()
    required = {
        "question", "asset", "fair_value", "best_ask", "best_bid",
        "edge", "action", "ref_price", "cur_price", "seconds_remaining",
        "slug",
    }
    for f in findings:
        missing = required - set(f.keys())
        assert not missing, f"Eksik alanlar: {missing}"


@pytest.mark.asyncio
async def test_scan_edges_edge_above_min():
    """Dönen tüm bulgular MIN_EDGE_PCT eşiği üstünde."""
    findings = await scan_edges()
    for f in findings:
        assert f["edge"] >= config.MIN_EDGE_PCT, \
            f"Eşik altı bulgu: edge={f['edge']:.3f} < {config.MIN_EDGE_PCT}"


@pytest.mark.asyncio
async def test_scan_edges_neg_risk_filtered():
    """negRisk=True marketler sonuçlarda olmamalı."""
    findings = await scan_edges()
    for f in findings:
        assert not f.get("neg_risk", False)


@pytest.mark.asyncio
async def test_scan_edges_time_filter():
    """60 saniyeden az kalan marketler olmamalı."""
    findings = await scan_edges()
    for f in findings:
        assert f["seconds_remaining"] >= 60, \
            f"Az süre kalmış market geçmiş: {f['seconds_remaining']:.0f}s"


@pytest.mark.asyncio
async def test_scan_edges_fair_value_in_range():
    """fair_value her zaman [0, 1] arasında."""
    findings = await scan_edges()
    for f in findings:
        assert 0.0 <= f["fair_value"] <= 1.0


@pytest.mark.asyncio
async def test_scan_edges_prices_positive():
    """ref_price ve cur_price pozitif."""
    findings = await scan_edges()
    for f in findings:
        assert f["ref_price"] > 0
        assert f["cur_price"] > 0


@pytest.mark.asyncio
async def test_scan_edges_sorted_by_edge_desc():
    """Bulgular edge'e göre büyükten küçüğe sıralı."""
    findings = await scan_edges()
    if len(findings) >= 2:
        for i in range(len(findings) - 1):
            assert findings[i]["edge"] >= findings[i + 1]["edge"]


@pytest.mark.asyncio
async def test_scan_edges_findings_include_window_cache():
    """Her bulgu _window içeriyor — Verifier PM fallback için."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    for f in findings:
        assert "_window" in f, "Bulguda _window yok"
        assert "best_ask" in f["_window"]
        assert "best_bid" in f["_window"]
        assert "seconds_remaining" in f["_window"]
