"""
council/verifier.py testleri.
Gerçek API kullanılır — mock yok.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, AsyncMock
import config
from council.verifier import verify, PRICE_DRIFT_HALT_PCT, PM_DRIFT_HALT
from council.scout import scan_edges


# ── Yardımcı ─────────────────────────────────────────────────────────────────

def _fake_finding(asset="BTC", slug="btc-updown-5m-0000000000",
                  action="YES", cur_price=105_000.0, ref_price=104_000.0,
                  best_ask=0.35, best_bid=0.34, seconds_remaining=180.0,
                  fair_value=0.60, edge=0.25):
    """Test için sahte Scout bulgusu. slug kasıtlı geçersiz (fetch_error tetikler)."""
    return {
        "question":          "Bitcoin Up or Down - Test",
        "asset":             asset,
        "slug":              slug,
        "action":            action,
        "edge":              edge,
        "cur_price":         cur_price,
        "ref_price":         ref_price,
        "best_ask":          best_ask,
        "best_bid":          best_bid,
        "seconds_remaining": seconds_remaining,
        "fair_value":        fair_value,
        "neg_risk":          False,
    }


# ── Unit testler (API çağrısı olmadan) ───────────────────────────────────────

def test_result_has_required_fields():
    """_result() her zaman gerekli alanları döndürür."""
    from council.verifier import _result
    r = _result(True, "ok", False)
    required = {
        "pass", "reason", "halt",
        "fresh_cur_price", "fresh_best_ask", "fresh_best_bid",
        "fresh_fair", "fresh_edge", "fresh_seconds",
        "hl_drift_pct", "pm_drift",
    }
    assert required.issubset(set(r.keys()))


def test_soft_fail_halt_is_false():
    """Soft fail'de (edge_gone, expired, fetch_error) halt=False."""
    from council.verifier import _result
    for reason in ("edge_gone", "expired", "fetch_error"):
        r = _result(False, reason, False)
        assert r["halt"] is False, f"{reason} için halt True olmamalı"
        assert r["pass"] is False


def test_hard_fail_halt_matches_config():
    """api_mismatch'te halt değeri HALT_ON_API_MISMATCH config'ine eşit."""
    from council.verifier import _result
    r = _result(False, "api_mismatch", config.HALT_ON_API_MISMATCH)
    assert r["halt"] == config.HALT_ON_API_MISMATCH


def test_price_drift_threshold_is_positive():
    assert PRICE_DRIFT_HALT_PCT > 0


def test_pm_drift_threshold_is_positive():
    assert PM_DRIFT_HALT > 0


def test_pass_result_structure():
    """PASS durumu pass=True, halt=False, reason='ok'."""
    from council.verifier import _result
    r = _result(True, "ok", False,
                fresh_cur=105_000.0, fresh_ask=0.40, fresh_bid=0.39,
                fresh_seconds=120.0, fresh_fair=0.65, fresh_edge=0.25,
                hl_drift_pct=0.01, pm_drift=0.005)
    assert r["pass"] is True
    assert r["reason"] == "ok"
    assert r["halt"] is False
    assert r["fresh_cur_price"] == 105_000.0
    assert r["fresh_edge"] == 0.25


# ── Unit: fetch_by_slug imza kontrolü ────────────────────────────────────────

@pytest.mark.asyncio
async def test_verifier_calls_fetch_by_slug_with_slug_only():
    """verifier PM adımında fetch_by_slug'ı session olmadan çağırmalı."""
    with patch("council.verifier.current_price", return_value=73_000.0), \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = None
        await verify(_fake_finding(cur_price=73_000.0, ref_price=73_000.0))
    mock_fetch.assert_called_once_with(_fake_finding()["slug"])


# ── Integration testler (gerçek API) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_hl_drift_triggers_halt():
    """
    Scout cur_price=1.0 (imkansız) iken HL taze fiyat ~73k → drift devasa → api_mismatch.
    current_price mock'lu — HL rate limit'ten bağımsız.
    """
    with patch("council.verifier.current_price", return_value=73_000.0):
        finding = _fake_finding(cur_price=1.0, ref_price=1.0)
        result = await verify(finding)
    assert result["pass"] is False
    assert result["reason"] == "api_mismatch"
    assert result["halt"] == config.HALT_ON_API_MISMATCH
    assert result["hl_drift_pct"] > PRICE_DRIFT_HALT_PCT


@pytest.mark.asyncio
async def test_verify_expired_soft_fail():
    """
    seconds_remaining=0 → expired veya fetch_error, halt=False.
    current_price mock'lu — HL rate limit'ten bağımsız.
    """
    with patch("council.verifier.current_price", return_value=73_000.0):
        finding = _fake_finding(cur_price=73_000.0, ref_price=73_000.0 * 0.99,
                                seconds_remaining=0.0)
        result = await verify(finding)
    assert result["pass"] is False
    assert result["halt"] is False
    assert result["reason"] in ("expired", "fetch_error")


@pytest.mark.asyncio
async def test_verify_invalid_slug_fetch_error_no_halt():
    """Geçersiz slug → fetch_error, halt=False. HL mock'lu — rate limit'ten bağımsız."""
    with patch("council.verifier.current_price", return_value=95_000.0):
        finding = _fake_finding(cur_price=95_000.0, slug="tamamen-gecersiz-slug-xyz")
        result = await verify(finding)
    assert result["pass"] is False
    assert result["halt"] is False


@pytest.mark.asyncio
async def test_verify_real_scout_finding_has_valid_structure():
    """Gerçek Scout bulgusu → Verifier geçerli yapıda sonuç döndürür."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    result = await verify(findings[0])
    assert "pass" in result
    assert result["reason"] in {"ok", "edge_gone", "expired", "api_mismatch", "fetch_error"}
    assert isinstance(result["halt"], bool)


@pytest.mark.asyncio
async def test_verify_pass_edge_above_min():
    """PASS durumunda fresh_edge >= MIN_EDGE_PCT."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    for f in findings:
        result = await verify(f)
        if result["pass"]:
            assert result["fresh_edge"] >= config.MIN_EDGE_PCT
            return
    pytest.skip("Hiçbir bulgu Verifier'ı geçmedi — normal durum")


@pytest.mark.asyncio
async def test_verify_fresh_prices_positive_on_non_fetch_error():
    """fetch_error dışındaki sonuçlarda fresh_cur_price > 0."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    result = await verify(findings[0])
    if result["reason"] != "fetch_error":
        assert result["fresh_cur_price"] > 0
