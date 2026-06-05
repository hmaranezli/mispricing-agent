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
    finding = _fake_finding(cur_price=73_000.0, ref_price=73_000.0)
    finding["yes_token_id"] = "yes-tok-test"
    finding["_window"] = {"best_ask": 0.35, "best_bid": 0.34, "seconds_remaining": 300.0, "neg_risk": False}
    with patch("council.verifier.current_price", return_value=73_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=0.40), \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = None
        await verify(finding)
    mock_fetch.assert_called_once_with(finding["slug"])


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
    seconds_remaining=0 → expired, halt=False.
    current_price mock'lu — HL rate limit'ten bağımsız.
    """
    finding = _fake_finding(cur_price=73_000.0, ref_price=73_000.0 * 0.99,
                            seconds_remaining=0.0)
    finding["yes_token_id"] = "yes-tok-expired"
    finding["_window"] = {"best_ask": 0.35, "best_bid": 0.34, "seconds_remaining": 0.0, "neg_risk": False}
    with patch("council.verifier.current_price", return_value=73_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=0.40), \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock, return_value=None):
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
async def test_verify_uses_window_cache_when_pm_fetch_fails():
    """PM fetch None döndürünce finding._window fallback kullanır — fetch_error olmaz.
    CLOB price ile fresh_best_ask dönmesi beklenir (market API değil).
    """
    cached_window = {
        "best_ask": 0.35, "best_bid": 0.34,
        "seconds_remaining": 300.0, "neg_risk": False,
    }
    finding = _fake_finding(cur_price=105_000.0, ref_price=104_000.0)
    finding["_window"] = cached_window
    finding["yes_token_id"] = "yes-tok-window"
    with patch("council.verifier.current_price", return_value=105_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=0.35), \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock, return_value=None):
        result = await verify(finding)
    assert result["reason"] != "fetch_error", f"_window varken fetch_error döndü: {result}"
    assert abs(result["fresh_best_ask"] - 0.35) < 1e-6   # CLOB fiyatı
    assert result["fresh_seconds"] == 300.0


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


# ── CLOB fiyat testleri ───────────────────────────────────────────────────────

def _fake_finding_with_tokens(
    asset="BTC", slug="btc-updown-5m-0000000000",
    action="YES", cur_price=105_000.0, ref_price=104_000.0,
    best_ask=0.35, best_bid=0.34, seconds_remaining=300.0,
    fair_value=0.60, edge=0.25,
    yes_token_id="yes-tok-123", no_token_id="no-tok-456",
):
    """Token ID'li sahte finding."""
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
        "yes_token_id":      yes_token_id,
        "no_token_id":       no_token_id,
        "_window": {
            "best_ask":          best_ask,
            "best_bid":          best_bid,
            "seconds_remaining": seconds_remaining,
            "neg_risk":          False,
            "start_ms":          0,
        },
    }


def _fake_market_window(best_ask=0.35, best_bid=0.34, seconds=300.0):
    """fetch_by_slug mock için sahte market dict."""
    from unittest.mock import MagicMock
    m = MagicMock()
    m.get = lambda k, d=None: {
        "bestAsk": str(best_ask), "bestBid": str(best_bid),
        "negRisk": False,
        "endDate": "2099-01-01T00:00:00Z",
        "eventStartTime": "2099-01-01T00:00:00Z",
    }.get(k, d)
    return m


@pytest.mark.asyncio
async def test_verify_uses_clob_price_for_edge_not_market_api():
    """Verifier edge hesabında CLOB /price kullanır, market API bestAsk değil."""
    finding = _fake_finding_with_tokens(
        action="YES", best_ask=0.51,  # market API (stale)
        fair_value=0.73, seconds_remaining=300.0,
    )
    # CLOB gerçek fiyat = 0.55 → edge = 0.73 - 0.55 = 0.18 → PASS
    with patch("council.verifier.current_price", new_callable=AsyncMock, return_value=105_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=0.55), \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock, return_value=_fake_market_window()), \
         patch("council.verifier.fair_yes", return_value=0.73):
        result = await verify(finding)
    assert result["pass"] is True
    assert abs(result["fresh_best_ask"] - 0.55) < 1e-6


@pytest.mark.asyncio
async def test_verify_edge_gone_when_clob_eliminates_edge():
    """CLOB fiyatı yüksekken edge yok → edge_gone (halt=False)."""
    finding = _fake_finding_with_tokens(
        action="YES", best_ask=0.51,  # market API
        fair_value=0.73, seconds_remaining=300.0,
    )
    # CLOB = 0.83 → edge = 0.73 - 0.83 = -0.10 → edge_gone
    with patch("council.verifier.current_price", new_callable=AsyncMock, return_value=105_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=0.83), \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock, return_value=_fake_market_window()), \
         patch("council.verifier.fair_yes", return_value=0.73):
        result = await verify(finding)
    assert result["pass"] is False
    assert result["reason"] == "edge_gone"
    assert result["halt"] is False


@pytest.mark.asyncio
async def test_verify_edge_gone_when_no_clob_liquidity():
    """CLOB /price None döndürünce edge_gone (liquidity yok)."""
    finding = _fake_finding_with_tokens(
        action="YES", best_ask=0.35, fair_value=0.60, seconds_remaining=300.0,
    )
    with patch("council.verifier.current_price", new_callable=AsyncMock, return_value=105_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=None), \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock, return_value=_fake_market_window()):
        result = await verify(finding)
    assert result["pass"] is False
    assert result["reason"] == "edge_gone"
    assert result["halt"] is False


@pytest.mark.asyncio
async def test_verify_no_halt_on_large_clob_vs_market_api_drift():
    """CLOB vs market API arası büyük fark HALT tetiklemez (beklenen davranış)."""
    finding = _fake_finding_with_tokens(
        action="YES", best_ask=0.51,  # market API (stale)
        fair_value=0.73, seconds_remaining=300.0,
    )
    # CLOB = 0.83 → drift = 0.32 → edge_gone ama HALT değil
    with patch("council.verifier.current_price", new_callable=AsyncMock, return_value=105_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=0.83), \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock, return_value=_fake_market_window()), \
         patch("council.verifier.fair_yes", return_value=0.73):
        result = await verify(finding)
    assert result["halt"] is False  # ASLA halt tetiklenmemeli


@pytest.mark.asyncio
async def test_verify_no_action_uses_no_token_id():
    """NO action → no_token_id ile CLOB çağrılır."""
    finding = _fake_finding_with_tokens(
        action="NO", best_ask=0.62, best_bid=0.60,
        fair_value=0.35,  # fair_NO = 0.65, NO_ask from CLOB
        seconds_remaining=300.0,
        no_token_id="no-tok-789",
    )
    with patch("council.verifier.current_price", new_callable=AsyncMock, return_value=105_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=0.30) as mock_clob, \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock, return_value=_fake_market_window()), \
         patch("council.verifier.fair_yes", return_value=0.35):
        # NO CLOB price=0.30 → YES bid = 1-0.30=0.70 → NO edge = 0.70-0.35=0.35 → PASS
        result = await verify(finding)
    mock_clob.assert_called_once_with("no-tok-789")


@pytest.mark.asyncio
async def test_verify_yes_action_uses_yes_token_id():
    """YES action → yes_token_id ile CLOB çağrılır."""
    finding = _fake_finding_with_tokens(
        action="YES", best_ask=0.35, fair_value=0.60,
        seconds_remaining=300.0, yes_token_id="yes-tok-abc",
    )
    with patch("council.verifier.current_price", new_callable=AsyncMock, return_value=105_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=0.40) as mock_clob, \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock, return_value=_fake_market_window()), \
         patch("council.verifier.fair_yes", return_value=0.60):
        await verify(finding)
    mock_clob.assert_called_once_with("yes-tok-abc")
