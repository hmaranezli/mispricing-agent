"""
council/redteam.py testleri.
Unit testler sahte veri ile, integration testler gerçek API ile. Mock yok.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from council.redteam import (
    redteam, _parse_taker_fee, _fee_adjusted_edge, _result,
    SPREAD_VETO, LIQUIDITY_VETO_USD, MIN_THESIS_SECS, EDGE_SANITY_MAX,
)
from council.scout import scan_edges
from council.verifier import verify


# ── Yardımcılar ──────────────────────────────────────────────────────────────

def _fake_finding(slug="btc-updown-5m-1748571000", action="YES",
                  fair_value=0.65, edge=0.15,
                  cur_price=73_500.0, ref_price=73_000.0,
                  best_ask=0.47, best_bid=0.46, seconds_remaining=180.0):
    return {
        "question": "Bitcoin Up or Down - Test",
        "asset": "BTC", "slug": slug, "action": action,
        "edge": edge, "cur_price": cur_price, "ref_price": ref_price,
        "best_ask": best_ask, "best_bid": best_bid,
        "seconds_remaining": seconds_remaining,
        "fair_value": fair_value, "neg_risk": False,
    }


def _fake_verification(fresh_fair=0.65, fresh_edge=0.15,
                        fresh_seconds=180.0, fresh_ask=0.47, fresh_bid=0.46):
    return {
        "pass": True, "reason": "ok", "halt": False,
        "fresh_cur_price": 73_500.0,
        "fresh_best_ask": fresh_ask, "fresh_best_bid": fresh_bid,
        "fresh_fair": fresh_fair, "fresh_edge": fresh_edge,
        "fresh_seconds": fresh_seconds,
        "hl_drift_pct": 0.01, "pm_drift": 0.005,
    }


# ── Unit: _parse_taker_fee ────────────────────────────────────────────────────

def test_parse_taker_fee_1000_is_2pct():
    """Gamma takerBaseFee=1000 → %2 (Polymarket belgelenmiş fee)."""
    assert abs(_parse_taker_fee(1000) - 0.02) < 1e-6


def test_parse_taker_fee_none_defaults_to_2pct():
    assert _parse_taker_fee(None) == 0.02


def test_parse_taker_fee_unreasonable_defaults_to_2pct():
    """fee > %20 mantıksız → fallback 0.02."""
    assert _parse_taker_fee(999_999) == 0.02


# ── Unit: _fee_adjusted_edge ──────────────────────────────────────────────────

def test_fee_adjusted_edge_yes_less_than_gross():
    """Fee, YES edge'ini düşürür."""
    net = _fee_adjusted_edge(fair=0.65, ask=0.47, bid=0.46, action="YES", fee=0.02)
    assert abs(net - (0.65 * 0.98 - 0.47)) < 1e-6
    assert net < (0.65 - 0.47)


def test_fee_adjusted_edge_no():
    """NO edge fee sonrası doğru hesaplanır."""
    net = _fee_adjusted_edge(fair=0.35, ask=0.65, bid=0.60, action="NO", fee=0.02)
    assert abs(net - ((1 - 0.35) * 0.98 - (1 - 0.60))) < 1e-6


def test_fee_adjusted_edge_zero_fee_equals_gross():
    """Fee=0 → net == gross."""
    net = _fee_adjusted_edge(fair=0.65, ask=0.47, bid=0.46, action="YES", fee=0.0)
    assert abs(net - (0.65 - 0.47)) < 1e-6


# ── Unit: _result yapısı ──────────────────────────────────────────────────────

def test_result_has_required_fields():
    r = _result(True, [], [], 0.15, 0.02, 0.01, 5000.0)
    required = {"pass", "vetoes", "warnings", "fee_adj_edge",
                "taker_fee", "spread", "liquidity_usd"}
    assert required.issubset(set(r.keys()))


def test_result_pass_with_warning_no_veto():
    r = _result(True, [], ["low_volume"], 0.10, 0.02, 0.01, 5000.0)
    assert r["pass"] is True


def test_result_fail_with_veto():
    r = _result(False, ["spread_too_wide"], [], 0.10, 0.02, 0.99, 5000.0)
    assert r["pass"] is False
    assert "spread_too_wide" in r["vetoes"]


# ── Integration: gerçek API ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_veto_insufficient_time():
    """fresh_seconds=60 (< 120) → insufficient_time_for_thesis veto."""
    result = await redteam(
        _fake_finding(),
        _fake_verification(fresh_seconds=60.0),
    )
    assert "insufficient_time_for_thesis" in result["vetoes"]
    assert result["pass"] is False


@pytest.mark.asyncio
async def test_veto_edge_suspiciously_large():
    """fresh_edge=0.40 (> 0.35) → edge_suspiciously_large veto."""
    result = await redteam(
        _fake_finding(),
        _fake_verification(fresh_edge=0.40),
    )
    assert "edge_suspiciously_large" in result["vetoes"]
    assert result["pass"] is False


@pytest.mark.asyncio
async def test_veto_edge_killed_by_fee():
    """fair=0.50, ask=0.43 → gross=0.07, net≈0.059 < 0.08 → veto."""
    result = await redteam(
        _fake_finding(action="YES"),
        _fake_verification(fresh_fair=0.50, fresh_ask=0.43, fresh_edge=0.07),
    )
    assert "edge_killed_by_fee" in result["vetoes"]


@pytest.mark.asyncio
async def test_warning_alone_does_not_cause_fail():
    """Warning tek başına pass=False yapmaz."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    f = findings[0]
    v = await verify(f)
    if not v["pass"]:
        pytest.skip("Verifier geçmedi")
    result = await redteam(f, v)
    if result["warnings"] and not result["vetoes"]:
        assert result["pass"] is True


@pytest.mark.asyncio
async def test_real_pipeline_result_structure():
    """Scout → Verifier → RedTeam zinciri doğru yapı döndürür."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    f = findings[0]
    v = await verify(f)
    if not v["pass"]:
        pytest.skip("Verifier geçmedi")
    result = await redteam(f, v)
    required = {"pass", "vetoes", "warnings", "fee_adj_edge",
                "taker_fee", "spread", "liquidity_usd"}
    assert required.issubset(set(result.keys()))
    assert isinstance(result["vetoes"], list)
    assert isinstance(result["warnings"], list)


@pytest.mark.asyncio
async def test_redteam_uses_raw_market_fallback_when_pm_fetch_fails():
    """PM fetch None döndürünce _raw_market fallback kullanır — market_data_unavailable olmaz."""
    from unittest.mock import patch, AsyncMock

    fake_raw = {
        "spread": "0.02",
        "liquidityClob": "5000",
        "volume24hr": "200",
        "takerBaseFee": "1000",
    }
    finding = _fake_finding(slug="btc-updown-15m-test")
    finding["_raw_market"] = fake_raw
    with patch("council.redteam.fetch_by_slug", new_callable=AsyncMock, return_value=None):
        result = await redteam(finding, _fake_verification(fresh_seconds=300.0))
    assert "market_data_unavailable" not in result["vetoes"], \
        f"_raw_market varken market_data_unavailable çıktı: {result['vetoes']}"


@pytest.mark.asyncio
async def test_redteam_calls_fetch_by_slug_with_slug_only():
    """RedTeam fetch_by_slug'ı yalnızca slug ile çağırmalı — session parametresi olmamalı.
    Bug: redteam(s, slug) yerine redteam(slug) çağrılmalı.
    """
    from unittest.mock import patch, AsyncMock

    fake_market = {
        "spread": "0.02",
        "liquidityClob": "5000",
        "volume24hr": "100",
        "takerBaseFee": "1000",
    }
    with patch("council.redteam.fetch_by_slug", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = fake_market
        result = await redteam(
            _fake_finding(slug="btc-updown-15m-test"),
            _fake_verification(fresh_seconds=300.0, fresh_edge=0.15),
        )
    mock_fetch.assert_called_once_with("btc-updown-15m-test")
    assert "market_data_unavailable" not in result["vetoes"]


@pytest.mark.asyncio
async def test_fee_adj_edge_lte_gross_edge():
    """fee_adj_edge her zaman fresh_edge'den küçük veya eşit."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    f = findings[0]
    v = await verify(f)
    if not v["pass"]:
        pytest.skip("Verifier geçmedi")
    result = await redteam(f, v)
    if result["taker_fee"] > 0:
        assert result["fee_adj_edge"] <= v["fresh_edge"] + 1e-6
