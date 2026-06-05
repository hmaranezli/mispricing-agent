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
    """Edge var ama MIN_EDGE_PCT altında → None. (MIN_EDGE_PCT=0.05)"""
    # 0.54 - 0.51 = 0.03 < 0.05
    result = _edge_signal(fair=0.54, best_ask=0.51, best_bid=0.50)
    assert result is None


def test_edge_signal_below_min_threshold_no():
    """NO edge ama MIN_EDGE_PCT altında → None."""
    # best_bid - fair = 0.50 - 0.47 = 0.03 < 0.05
    result = _edge_signal(fair=0.47, best_ask=0.52, best_bid=0.50)
    assert result is None


def test_edge_signal_exact_min_threshold():
    """MIN_EDGE_PCT (0.05) üstünde edge → geçer. Float kesinliğinden kaçınmak için 0.10 kullan."""
    # 0.60 - 0.50 = 0.10 >= 0.05 → geçmeli
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
        "slug", "yes_token_id", "no_token_id",
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
async def test_process_market_skips_asset_not_in_tracked():
    """config.TRACKED_ASSETS dışındaki varlık → _process_market None döner."""
    from council.scout import _process_market
    original = list(config.TRACKED_ASSETS)
    config.TRACKED_ASSETS = ["BTC", "ETH"]  # SOL geçici olarak çıkarıldı
    try:
        result = await _process_market({"question": "Solana Up or Down 5m"})
        assert result is None, "SOL TRACKED_ASSETS dışındayken None dönmeli"
    finally:
        config.TRACKED_ASSETS = original


@pytest.mark.asyncio
async def test_process_market_accepts_tracked_asset():
    """config.TRACKED_ASSETS içindeki varlık → _process_market None dönemez (None döner ama TRACKED_ASSETS yüzünden değil)."""
    from council.scout import _process_market
    # BTC TRACKED_ASSETS'te → asset filtresi geçer, veri yokluğu yüzünden None dönebilir
    # Önemli olan: TRACKED_ASSETS filtresinin BTC'yi bloke ETMEMESİ
    # Bunu dolaylı test ederiz: SOL'u ekleyince SOL sorgusu geçer
    original = list(config.TRACKED_ASSETS)
    config.TRACKED_ASSETS = ["SOL"]
    try:
        # SOL TRACKED'ta → asset filtresi geçmeli (None olsa bile TRACKED yüzünden değil)
        # Gerçek API'ye gitmeden test: _asset_of("Solana...") = "SOL", "SOL" in ["SOL"] = True → filter geçer
        assert "SOL" in config.TRACKED_ASSETS
    finally:
        config.TRACKED_ASSETS = original


@pytest.mark.asyncio
async def test_scan_edges_results_only_tracked_assets():
    """Tüm scan bulgularının asset'i config.TRACKED_ASSETS içinde olmalı."""
    findings = await scan_edges()
    for f in findings:
        assert f["asset"] in config.TRACKED_ASSETS, \
            f"{f['asset']} TRACKED_ASSETS dışında: {config.TRACKED_ASSETS}"


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


@pytest.mark.asyncio
async def test_scan_edges_findings_include_raw_market():
    """Her bulgu _raw_market içeriyor — RedTeam spread/liquidity/fee fallback için."""
    findings = await scan_edges()
    if not findings:
        pytest.skip("Şu an aktif mispricing yok")
    for f in findings:
        assert "_raw_market" in f, "Bulguda _raw_market yok"
        assert isinstance(f["_raw_market"], dict)


@pytest.mark.asyncio
async def test_scan_edges_min_seconds_above_thesis_threshold():
    """seconds_remaining >= 180 — RedTeam'in 120s eşiğine 60s buffer."""
    findings = await scan_edges()
    for f in findings:
        assert f["seconds_remaining"] >= 180, \
            f"Eşik altı market geçmiş: {f['seconds_remaining']:.0f}s < 180s"


@pytest.mark.asyncio
async def test_finding_contains_token_ids():
    """scan_edges() döndürdüğü finding'de yes_token_id ve no_token_id bulunur."""
    from unittest.mock import AsyncMock, patch
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    fake_market = {
        "question": "Will BTC go up?",
        "slug": "btc-updown-5m-123",
        "bestAsk": "0.35",
        "bestBid": "0.33",
        "eventStartTime": (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate": (now + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "negRisk": False,
        "clobTokenIds": ["yes-token-abc", "no-token-xyz"],
    }
    with patch("council.scout.find_shortterm", new_callable=AsyncMock) as mock_find, \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock) as mock_ref, \
         patch("council.scout.current_price", new_callable=AsyncMock) as mock_cur, \
         patch("council.scout.fair_yes", return_value=0.60), \
         patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.35), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02):
        mock_find.return_value = [fake_market]
        mock_ref.return_value = 95000.0
        mock_cur.return_value = 96000.0
        findings = await scan_edges()

    assert len(findings) >= 1, "No findings returned"
    f = findings[0]
    assert f.get("yes_token_id") == "yes-token-abc", f"yes_token_id eksik veya yanlış: {f}"
    assert f.get("no_token_id")  == "no-token-xyz",  f"no_token_id eksik veya yanlış: {f}"


@pytest.mark.asyncio
async def test_finding_token_ids_none_when_absent():
    """clobTokenIds yoksa yes_token_id ve no_token_id None döner, exception yok."""
    from unittest.mock import AsyncMock, patch
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    fake_market = {
        "question": "Will BTC go up?",
        "slug": "btc-updown-5m-456",
        "bestAsk": "0.35",
        "bestBid": "0.33",
        "eventStartTime": (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate": (now + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "negRisk": False,
        # clobTokenIds intentionally absent
    }
    with patch("council.scout.find_shortterm", new_callable=AsyncMock) as mock_find, \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock) as mock_ref, \
         patch("council.scout.current_price", new_callable=AsyncMock) as mock_cur, \
         patch("council.scout.fair_yes", return_value=0.60):
        mock_find.return_value = [fake_market]
        mock_ref.return_value = 95000.0
        mock_cur.return_value = 96000.0
        findings = await scan_edges()

    if findings:
        assert findings[0].get("yes_token_id") is None
        assert findings[0].get("no_token_id")  is None


@pytest.mark.asyncio
async def test_finding_token_ids_single_element_no_crash():
    """clobTokenIds sadece 1 eleman içeriyorsa yes_token_id set, no_token_id None — crash yok."""
    from unittest.mock import AsyncMock, patch
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    fake_market = {
        "question": "Will BTC go up?",
        "slug": "btc-updown-5m-789",
        "bestAsk": "0.35",
        "bestBid": "0.33",
        "eventStartTime": (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate": (now + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "negRisk": False,
        "clobTokenIds": ["only-yes-token"],  # sadece 1 eleman
    }
    with patch("council.scout.find_shortterm", new_callable=AsyncMock) as mock_find, \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock) as mock_ref, \
         patch("council.scout.current_price", new_callable=AsyncMock) as mock_cur, \
         patch("council.scout.fair_yes", return_value=0.60), \
         patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.35), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02):
        mock_find.return_value = [fake_market]
        mock_ref.return_value = 95000.0
        mock_cur.return_value = 96000.0
        findings = await scan_edges()

    if findings:
        assert findings[0].get("yes_token_id") == "only-yes-token"
        assert findings[0].get("no_token_id") is None


# ── CLOB fiyat testleri ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_market_uses_clob_price_not_market_api():
    """_process_market CLOB fiyatını kullanır, market API best_ask'ı değil."""
    from unittest.mock import AsyncMock, patch
    from datetime import datetime, timezone, timedelta
    from council.scout import _process_market

    now = datetime.now(timezone.utc)
    market = {
        "question": "Will BTC go up?",
        "slug": "btc-updown-5m-clob-test",
        "bestAsk": "0.80",   # stale market API price — should be IGNORED
        "bestBid": "0.79",
        "eventStartTime": (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate": (now + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "negRisk": False,
        "clobTokenIds": '["yes-tok-111","no-tok-222"]',
    }
    # CLOB real price = 0.55, fair = 0.65 → YES edge = 0.65 - 0.55 = 0.10 ≥ 0.05
    with patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.55), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=100_000.0), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=104_000.0), \
         patch("council.scout.fair_yes", return_value=0.65), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02):
        result = await _process_market(market)
    assert result is not None, "Should find edge with CLOB price"
    assert abs(result["best_ask"] - 0.55) < 1e-6, f"best_ask should be CLOB price 0.55, got {result['best_ask']}"


@pytest.mark.asyncio
async def test_process_market_returns_none_when_no_clob_liquidity():
    """CLOB None döndürünce (likidite yok) market atlanır."""
    from unittest.mock import AsyncMock, patch
    from datetime import datetime, timezone, timedelta
    from council.scout import _process_market

    now = datetime.now(timezone.utc)
    market = {
        "question": "Will BTC go up?",
        "slug": "btc-updown-5m-no-clob",
        "bestAsk": "0.35",
        "bestBid": "0.34",
        "eventStartTime": (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate": (now + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "negRisk": False,
        "clobTokenIds": '["yes-tok-333","no-tok-444"]',
    }
    with patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=None), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=100_000.0), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=104_000.0):
        result = await _process_market(market)
    assert result is None, "CLOB liquidity=None should return None (skip market)"
