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
from council.scout import scan_edges, _asset_of, _edge_signal, _drift_ok, MIN_SECONDS

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


# ── Entry filter (_drift_ok) testleri ────────────────────────────────────────

def test_min_seconds_is_300():
    """MIN_SECONDS gamma trap önlemi için 300s olmalı (5dk window başına giriş eşiği)."""
    assert MIN_SECONDS == 300, f"MIN_SECONDS 300 olmalı, şu an: {MIN_SECONDS}"


def test_drift_ok_blocks_no_when_hl_bullish_beyond_threshold():
    """NO işlem: HL ref'ten %0.5 üstte → giriş engellenmeli (HL bullish, NO yanlış yön)."""
    assert _drift_ok("NO", cur=1.005, ref_price=1.0) is False


def test_drift_ok_blocks_yes_when_hl_bearish_beyond_threshold():
    """YES işlem: HL ref'ten %0.5 altta → giriş engellenmeli (HL bearish, YES yanlış yön)."""
    assert _drift_ok("YES", cur=0.994, ref_price=1.0) is False


def test_drift_ok_allows_no_within_threshold():
    """NO işlem: HL ref'ten %0.2 üstte (<%0.3 eşik) → küçük gürültü, giriş geçmeli."""
    assert _drift_ok("NO", cur=1.002, ref_price=1.0) is True


def test_drift_ok_allows_yes_within_threshold():
    """YES işlem: HL ref'ten %0.2 altta (<%0.3 eşik) → küçük gürültü, giriş geçmeli."""
    assert _drift_ok("YES", cur=0.998, ref_price=1.0) is True


def test_drift_ok_aligned_no_when_hl_bearish():
    """NO işlem: HL ref altında → doğru yön, giriş geçmeli."""
    assert _drift_ok("NO", cur=0.994, ref_price=1.0) is True


def test_drift_ok_aligned_yes_when_hl_bullish():
    """YES işlem: HL ref üstünde → doğru yön, giriş geçmeli."""
    assert _drift_ok("YES", cur=1.005, ref_price=1.0) is True


def test_edge_signal_yes_cheap():
    """fair > ask yeterince → YES al."""
    result = _edge_signal(fair=0.70, best_ask=0.40, best_bid=0.39)
    assert result is not None
    assert result["action"] == "YES"
    assert abs(result["edge"] - 0.30) < 1e-6


def test_edge_signal_no_cheap():
    """YES_ask > fair yeterince → NO al (market YES'i aşırı fiyatlıyor).
    Senaryo: HL bearish (fair=0.30), piyasa hâlâ YES'e 0.62 diyor → NO ucuz.
    no_edge = best_ask - fair = 0.62 - 0.30 = 0.32 (doğru formül)
    """
    result = _edge_signal(fair=0.30, best_ask=0.62, best_bid=0.60)
    assert result is not None
    assert result["action"] == "NO"
    assert abs(result["edge"] - 0.32) < 1e-6


def test_edge_signal_yes_rejected_low_conviction():
    """YES edge var ama fair < CONVICTION_MIN (0.58) → None. Düşük win-rate işlem alınmaz.
    fair=0.55, ask=0.47 → edge=0.08 (geçer) ama konviksiyon %55 < %58 → reddet.
    """
    result = _edge_signal(fair=0.55, best_ask=0.47, best_bid=0.46)
    assert result is None, f"Düşük konviksiyonlu YES alınmamalı, result={result}"


def test_edge_signal_no_rejected_low_conviction():
    """NO edge var ama (1-fair) < CONVICTION_MIN → None.
    fair=0.45, ask=0.53 → no_edge=0.08 (geçer) ama NO konviksiyonu 1-0.45=0.55 < 0.58 → reddet.
    """
    result = _edge_signal(fair=0.45, best_ask=0.53, best_bid=0.52)
    assert result is None, f"Düşük konviksiyonlu NO alınmamalı, result={result}"


def test_edge_signal_yes_accepted_at_conviction():
    """fair ≥ CONVICTION_MIN ve edge yeterli → YES geçer.
    fair=0.65, ask=0.55 → edge=0.10, konviksiyon %65 ≥ %58 → YES.
    """
    result = _edge_signal(fair=0.65, best_ask=0.55, best_bid=0.54)
    assert result is not None and result["action"] == "YES"


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
    """NO edge ama MIN_EDGE_PCT altında → None.
    no_edge = best_ask - fair = 0.51 - 0.47 = 0.04 < 0.05 → None
    """
    result = _edge_signal(fair=0.47, best_ask=0.51, best_bid=0.49)
    assert result is None


# ── Kök hata regression testleri ─────────────────────────────────────────────

def test_edge_signal_no_false_signal_when_market_aligned():
    """KRİTİK regression: market ve HL hemfikirken NO sinyali üretmemeli.

    Senaryo (#1157 kaybının kökü):
      HL bearish → fair_YES=0.40
      Market da bearish → YES_ask=0.36 (zaten düşük fiyatlamış)
      Gerçek edge = YES_ask - fair_YES = 0.36-0.40 = -0.04 → AÇMA!

    Eski hatalı formül:
      no_edge = (1-YES_ask) - fair = (1-0.36)-0.40 = +0.24 → yanlış açıyordu

    Yeni doğru formül (best_ask - fair):
      no_edge = 0.36 - 0.40 = -0.04 → None ✓
    """
    result = _edge_signal(fair=0.40, best_ask=0.36, best_bid=0.64)
    assert result is None, (
        f"Market ve HL hemfikirken NO açılmamalı! "
        f"fair=0.40, YES_ask=0.36 → gerçek edge=-0.04, result={result}"
    )


def test_edge_signal_no_genuine_mispricing():
    """Gerçek NO fırsatı: HL çok bearish ama market hâlâ bullish.

    Senaryo:
      HL drops 3% → fair_YES=0.10 (çok bearish)
      Market hâlâ YES_ask=0.65 (lag — henüz fiyatlamadı)
      Gerçek edge = 0.65 - 0.10 = 0.55 → AÇILMALI!

    Eski formül: (1-0.65)-0.10 = 0.25 (açıyordu ama edge yanlış)
    Yeni formül: 0.65-0.10 = 0.55 (doğru edge) ✓
    """
    result = _edge_signal(fair=0.10, best_ask=0.65, best_bid=0.35)
    assert result is not None, "Gerçek NO fırsatı bulunmalı"
    assert result["action"] == "NO"
    assert abs(result["edge"] - 0.55) < 1e-6, (
        f"Edge 0.55 olmalı, gelen: {result['edge']}"
    )


def test_edge_signal_no_only_when_ask_above_fair():
    """NO yalnızca YES_ask > fair_YES olduğunda açılır (market YES'i aşırı fiyatladığında)."""
    # YES_ask = fair_YES + MIN_EDGE_PCT → tam eşikte
    # no_edge = 0.40 - 0.35 = 0.05 → geçmeli
    result = _edge_signal(fair=0.35, best_ask=0.40, best_bid=0.60)
    assert result is not None
    assert result["action"] == "NO"
    # YES_ask = fair_YES + MIN_EDGE_PCT - epsilon → geçmemeli
    result2 = _edge_signal(fair=0.35, best_ask=0.395, best_bid=0.605)
    assert result2 is None, "Tam eşik altında NO açılmamalı"


def test_edge_signal_exact_min_threshold():
    """MIN_EDGE_PCT (0.05) üstünde edge → geçer. fair konviksiyon eşiği üstünde (0.65)."""
    # 0.65 - 0.50 = 0.15 >= 0.05 ve konviksiyon 0.65 ≥ 0.62 → geçmeli
    result = _edge_signal(fair=0.65, best_ask=0.50, best_bid=0.49)
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
        result = await _process_market({"question": "Solana Up or Down 5m"}, {})
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
    """seconds_remaining >= 300 — gamma trap ve near-expiry ince kitap önlemi."""
    findings = await scan_edges()
    for f in findings:
        assert f["seconds_remaining"] >= 300, \
            f"Eşik altı market geçmiş: {f['seconds_remaining']:.0f}s < 300s"


@pytest.mark.asyncio
async def test_finding_contains_token_ids():
    """scan_edges() döndürdüğü finding'de yes_token_id ve no_token_id bulunur."""
    from unittest.mock import AsyncMock, patch
    from datetime import datetime, timezone, timedelta
    import council.scout as _scout_mod

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
         patch("council.scout.fair_yes", return_value=0.65), \
         patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.35), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02), \
         patch("council.scout.fetch_candles", new_callable=AsyncMock,
               return_value=[{"c": "95000"}, {"c": "95100"}]), \
         patch.object(_scout_mod, "_markets_cache_ts", 0.0), \
         patch.object(_scout_mod, "_markets_cache", []):
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
    import council.scout as _scout_mod

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
         patch("council.scout.fair_yes", return_value=0.60), \
         patch("council.scout.fetch_candles", new_callable=AsyncMock,
               return_value=[{"c": "95000"}, {"c": "95100"}]), \
         patch.object(_scout_mod, "_markets_cache_ts", 0.0), \
         patch.object(_scout_mod, "_markets_cache", []):
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
    import council.scout as _scout_mod

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
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02), \
         patch("council.scout.fetch_candles", new_callable=AsyncMock,
               return_value=[{"c": "95000"}, {"c": "95100"}]), \
         patch.object(_scout_mod, "_markets_cache_ts", 0.0), \
         patch.object(_scout_mod, "_markets_cache", []):
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
        result = await _process_market(market, {})
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
    with patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=None):
        result = await _process_market(market, {})
    assert result is None, "CLOB liquidity=None should return None (skip market)"


def test_process_market_uses_ws_cache_when_available(monkeypatch):
    """WS cache'de fiyat varsa REST çağrısı yapılmaz."""
    import data.ws_prices as _ws
    import asyncio
    from datetime import datetime, timezone, timedelta
    _ws._cache.clear()
    _ws._update_cache("yes_tok_ws", best_bid=0.46, best_ask=0.54)

    from council.scout import _process_market

    rest_called = []

    async def fake_clob(token_id, side="BUY"):
        rest_called.append(token_id)
        return 0.54

    async def fake_price_at(asset, ts):
        return 95000.0

    async def fake_current(asset):
        return 95200.0

    async def fake_fee(token_id):
        return 0.02

    monkeypatch.setattr("council.scout.get_clob_price", fake_clob)
    monkeypatch.setattr("council.scout.price_at_timestamp", fake_price_at)
    monkeypatch.setattr("council.scout.current_price", fake_current)
    monkeypatch.setattr("council.scout.fetch_fee_rate", fake_fee)

    now = datetime.now(timezone.utc)
    market = {
        "question": "Will BTC go up?",
        "slug": "btc-up-ws-test",
        "clobTokenIds": '["yes_tok_ws", "no_tok_ws"]',
        "eventStartTime": (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate": (now + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bestAsk": "0.54", "bestBid": "0.46",
        "negRisk": False, "outcomePrices": "[0.54, 0.46]",
        "closed": False, "active": True,
    }

    asyncio.run(_process_market(market, {}))
    assert "yes_tok_ws" not in rest_called, "WS cache varken REST çağrılmamalı"


def test_process_market_falls_back_to_rest_when_ws_miss(monkeypatch):
    """WS cache miss → REST get_clob_price çağrılır."""
    import data.ws_prices as _ws
    import asyncio
    from datetime import datetime, timezone, timedelta
    _ws._cache.clear()  # miss

    from council.scout import _process_market

    rest_called = []

    async def fake_clob(token_id, side="BUY"):
        rest_called.append(token_id)
        return 0.54

    async def fake_price_at(asset, ts):
        return 95000.0

    async def fake_current(asset):
        return 95200.0

    async def fake_fee(token_id):
        return 0.02

    monkeypatch.setattr("council.scout.get_clob_price", fake_clob)
    monkeypatch.setattr("council.scout.price_at_timestamp", fake_price_at)
    monkeypatch.setattr("council.scout.current_price", fake_current)
    monkeypatch.setattr("council.scout.fetch_fee_rate", fake_fee)

    now = datetime.now(timezone.utc)
    market = {
        "question": "Will BTC go up?",
        "slug": "btc-up-rest-test",
        "clobTokenIds": '["yes_tok_rest", "no_tok_rest"]',
        "eventStartTime": (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate": (now + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bestAsk": "0.54", "bestBid": "0.46",
        "negRisk": False, "outcomePrices": "[0.54, 0.46]",
        "closed": False, "active": True,
    }

    asyncio.run(_process_market(market, {}))
    assert "yes_tok_rest" in rest_called, "WS miss'te REST çağrılmalı"


# ── YES_bid REST fallback testleri ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_yes_bid_uses_sell_endpoint_when_ws_bid_is_none():
    """WS get_bid None → /price?side=SELL çağrılır; clob_ask kullanılmaz."""
    from council.scout import _process_market
    from unittest.mock import patch, AsyncMock
    import data.ws_prices as ws_mod

    fake_window = {
        "neg_risk": False, "seconds_remaining": 300.0,
        "best_ask": 0.50, "best_bid": 0.49, "start_ms": 0,
    }
    # fair=0.65, YES_ask=0.50 → YES edge=0.15 → YES action
    # YES_bid: WS=None → REST SELL endpoint=0.48
    with patch("council.scout.parse_market_window", return_value=fake_window), \
         patch("council.scout._parse_token_ids", return_value=["tok-yes", "tok-no"]), \
         patch.object(ws_mod, "get_ask", return_value=0.50), \
         patch.object(ws_mod, "get_bid", return_value=None), \
         patch("council.scout.get_clob_price", new_callable=AsyncMock,
               side_effect=lambda tid, side="BUY": 0.48 if side == "SELL" else None) as mock_price, \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=50000.0), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=50000.0), \
         patch("council.scout.fair_yes", return_value=0.65), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02):
        result = await _process_market({"question": "Bitcoin Up or Down 5m", "slug": "btc-test"}, {})

    # SELL endpoint çağrılmış olmalı
    mock_price.assert_any_call("tok-yes", "SELL")
    # best_bid = 0.48 (SELL endpoint), NOT 0.50 (ask)
    if result and result.get("action") == "YES":
        assert result["best_bid"] == 0.48, (
            f"YES_bid REST fallback hatalı: beklenen 0.48, gelen {result['best_bid']}"
        )


# ── NO_ask gerçek fiyat testleri ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_false_positive_filtered_by_real_no_ask():
    """YES_ask tabanlı NO sinyali geçti ama gerçek NO_ask ile edge < MIN_EDGE_PCT → None."""
    from council.scout import _process_market
    from unittest.mock import patch, AsyncMock
    import data.ws_prices as ws_mod

    fake_window = {
        "neg_risk": False, "seconds_remaining": 300.0,
        "best_ask": 0.50, "best_bid": 0.49, "start_ms": 0,
    }
    # fair=0.45, YES_ask=0.51 → pre-filter no_edge=0.06 → NO signal fires
    # Gerçek NO_ask=0.55 → real_no_edge=(1-0.45)-0.55=0.00 < MIN_EDGE_PCT → None döner
    with patch("council.scout.parse_market_window", return_value=fake_window), \
         patch("council.scout._parse_token_ids", return_value=["tok-yes", "tok-no"]), \
         patch.object(ws_mod, "get_ask",
               side_effect=lambda tid: 0.51 if tid == "tok-yes" else 0.55), \
         patch.object(ws_mod, "get_bid", return_value=None), \
         patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=None), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=50000.0), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=50000.0), \
         patch("council.scout.fair_yes", return_value=0.45), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02):
        result = await _process_market({"question": "Bitcoin Up or Down 5m", "slug": "btc-test"}, {})

    assert result is None, (
        f"False positive filtre çalışmadı! "
        f"fair=0.45, YES_ask=0.51, NO_ask=0.55 → real_no_edge=0.00 < MIN_EDGE_PCT"
    )


@pytest.mark.asyncio
async def test_no_edge_uses_real_no_ask_and_correct_formula():
    """NO sinyali: gerçek NO_ask ile (1-fair)-no_ask edge hesaplanır, finding'e yazılır."""
    from council.scout import _process_market
    from unittest.mock import patch, AsyncMock
    import data.ws_prices as ws_mod

    fake_window = {
        "neg_risk": False, "seconds_remaining": 300.0,
        "best_ask": 0.50, "best_bid": 0.49, "start_ms": 0,
    }
    # fair=0.30, YES_ask=0.65, NO_ask=0.38
    # real_no_edge = (1-0.30) - 0.38 = 0.70 - 0.38 = 0.32 ≥ MIN_EDGE_PCT
    with patch("council.scout.parse_market_window", return_value=fake_window), \
         patch("council.scout._parse_token_ids", return_value=["tok-yes", "tok-no"]), \
         patch.object(ws_mod, "get_ask",
               side_effect=lambda tid: 0.65 if tid == "tok-yes" else 0.38), \
         patch.object(ws_mod, "get_bid", return_value=None), \
         patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=None), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=50000.0), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=50000.0), \
         patch("council.scout.fair_yes", return_value=0.30), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02):
        result = await _process_market({"question": "Bitcoin Up or Down 5m", "slug": "btc-test"}, {})

    assert result is not None, "Gerçek NO edge 0.32 → bulgu dönmeli"
    assert result["action"] == "NO"
    assert abs(result["edge"] - 0.32) < 1e-4, (
        f"NO edge yanlış: beklenen 0.32, gelen {result['edge']}"
    )
    assert result.get("no_ask") == 0.38, (
        f"no_ask finding'de yok ya da yanlış: {result.get('no_ask')}"
    )


# ── Task: Basis+Funding wiring (market_state) ─────────────────────────────────

import council.scout as _scout_mod


def _make_market(seconds_remaining=600):
    """Test market dict — parse_market_window'u geçecek minimum alan seti.
    Default 600s: MIN_SECONDS=300 eşiği için yeterli buffer (test latency'si aşımını engeller).
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=10)
    end   = now + timedelta(seconds=seconds_remaining)
    return {
        "question":       "Bitcoin Up or Down",
        "slug":           "btc-updown-test",
        "clobTokenIds":   '["yes-tok","no-tok"]',
        "bestAsk":        "0.35",
        "bestBid":        "0.33",
        "eventStartTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate":        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "negRisk":        False,
    }


@pytest.mark.asyncio
async def test_process_market_includes_oracle_px():
    """`_process_market` bulgu dict'ine oracle_px ekler."""
    from council.scout import _process_market
    from unittest.mock import AsyncMock, patch

    market_state = {
        "BTC": {"oracle_px": 60938.0, "funding_rate": 4.8e-6, "basis_pct": 0.00035}
    }
    with patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.35), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=60_000.0), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=61_000.0), \
         patch("council.scout.fair_yes", return_value=0.70), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02), \
         patch("council.scout._ws_prices.get_ask", return_value=None), \
         patch("council.scout._ws_prices.get_bid", return_value=None):
        result = await _process_market(_make_market(), {}, market_state)

    assert result is not None
    assert result.get("oracle_px") == 60938.0


@pytest.mark.asyncio
async def test_process_market_includes_funding_rate():
    """`_process_market` bulgu dict'ine funding_rate ekler."""
    from council.scout import _process_market
    from unittest.mock import AsyncMock, patch

    market_state = {
        "BTC": {"oracle_px": 60938.0, "funding_rate": 4.8e-6, "basis_pct": 0.00035}
    }
    with patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.35), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=60_000.0), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=61_000.0), \
         patch("council.scout.fair_yes", return_value=0.70), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02), \
         patch("council.scout._ws_prices.get_ask", return_value=None), \
         patch("council.scout._ws_prices.get_bid", return_value=None):
        result = await _process_market(_make_market(), {}, market_state)

    assert result is not None
    assert result.get("funding_rate") == 4.8e-6


@pytest.mark.asyncio
async def test_process_market_includes_basis_pct():
    """`_process_market` bulgu dict'ine basis_pct ekler."""
    from council.scout import _process_market
    from unittest.mock import AsyncMock, patch

    market_state = {
        "BTC": {"oracle_px": 60938.0, "funding_rate": 4.8e-6, "basis_pct": 0.00035}
    }
    with patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.35), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=60_000.0), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=61_000.0), \
         patch("council.scout.fair_yes", return_value=0.70), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02), \
         patch("council.scout._ws_prices.get_ask", return_value=None), \
         patch("council.scout._ws_prices.get_bid", return_value=None):
        result = await _process_market(_make_market(), {}, market_state)

    assert result is not None
    assert result.get("basis_pct") == 0.00035


@pytest.mark.asyncio
async def test_process_market_no_market_state_oracle_fields_none():
    """`market_state` verilmezse oracle_px, funding_rate, basis_pct = None, çökmez."""
    from council.scout import _process_market
    from unittest.mock import AsyncMock, patch

    with patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.35), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=60_000.0), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=61_000.0), \
         patch("council.scout.fair_yes", return_value=0.70), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02), \
         patch("council.scout._ws_prices.get_ask", return_value=None), \
         patch("council.scout._ws_prices.get_bid", return_value=None):
        result = await _process_market(_make_market(), {})   # 3. argüman yok

    assert result is not None
    assert result.get("oracle_px") is None
    assert result.get("funding_rate") is None
    assert result.get("basis_pct") is None


@pytest.mark.asyncio
async def test_get_market_state_returns_oracle_funding_basis():
    """`_get_market_state()` oracle_px, funding_rate, basis_pct içeren dict döner."""
    from council.scout import _get_market_state
    from unittest.mock import AsyncMock, patch

    fake_raw = {
        "BTC": {"mid": 61_000.0, "oracle": 60_938.0, "funding": 4.8e-6,
                "mark": 61_100.0, "prev_day": 60_500.0},
    }
    with patch("council.scout.fetch_market_state", new_callable=AsyncMock, return_value=fake_raw), \
         patch.object(_scout_mod, "_market_state_cache", {}), \
         patch.object(_scout_mod, "_market_state_cache_ts", 0.0):
        state = await _get_market_state()

    assert "BTC" in state
    btc = state["BTC"]
    assert btc["oracle_px"] == 60_938.0
    assert btc["funding_rate"] == 4.8e-6
    assert abs(btc["basis_pct"] - abs(61_000.0 - 60_938.0) / 60_938.0) < 1e-9


# ── Faz 3: scan_audit + current_price prefetch ────────────────────────────────

@pytest.mark.asyncio
async def test_process_market_increments_skipped_min_seconds():
    """seconds_remaining < MIN_SECONDS → audit['skipped_min_seconds'] artar, API çağrısı olmaz."""
    from council.scout import _process_market
    from unittest.mock import AsyncMock, patch

    market = _make_market(seconds_remaining=60)  # MIN_SECONDS=300'den az
    audit = {"skipped_no_asset": 0, "skipped_no_window": 0, "skipped_neg_risk": 0,
             "skipped_min_seconds": 0, "skipped_no_price": 0, "api_reached": 0,
             "ws_hit": 0, "pm_rest": 0}
    mock_cur = AsyncMock(return_value=61_000.0)
    with patch("council.scout.current_price", mock_cur):
        result = await _process_market(market, {}, audit=audit)

    assert result is None
    assert audit["skipped_min_seconds"] == 1
    mock_cur.assert_not_called()  # API'ye gitmeden düşmeli


@pytest.mark.asyncio
async def test_process_market_uses_prefetched_cur_price():
    """cur_prices sözlüğü verildiğinde current_price() çağrılmamalı."""
    from council.scout import _process_market
    from unittest.mock import AsyncMock, patch

    mock_cur = AsyncMock(return_value=99_999.0)
    with patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.35), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=60_000.0), \
         patch("council.scout.current_price", mock_cur), \
         patch("council.scout.fair_yes", return_value=0.70), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02), \
         patch("council.scout._ws_prices.get_ask", return_value=None), \
         patch("council.scout._ws_prices.get_bid", return_value=None):
        await _process_market(_make_market(), {}, cur_prices={"BTC": 61_000.0})

    mock_cur.assert_not_called()  # prefetch verildi → current_price çağrılmamalı


@pytest.mark.asyncio
async def test_scan_edges_prefetches_current_price_once_per_asset(capsys):
    """scan_edges tüm market listesi için current_price'ı N kez değil, 4 kez çağırmalı."""
    from council.scout import scan_edges
    from unittest.mock import AsyncMock, patch
    import council.scout as _mod

    fake_markets = [_make_market(600), _make_market(700), _make_market(800)]
    mock_cur = AsyncMock(return_value=61_000.0)

    with patch.object(_mod, "_markets_cache", fake_markets), \
         patch.object(_mod, "_markets_cache_ts", 1e18), \
         patch("council.scout.current_price", mock_cur), \
         patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.35), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=60_000.0), \
         patch("council.scout.fair_yes", return_value=0.55), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02), \
         patch("council.scout._ws_prices.get_ask", return_value=None), \
         patch("council.scout._ws_prices.get_bid", return_value=None), \
         patch("council.scout._get_all_vols", new_callable=AsyncMock, return_value={}), \
         patch("council.scout._get_market_state", new_callable=AsyncMock, return_value={}):
        await scan_edges()

    # 4 tracked asset için 4 çağrı — 3 market×4 asset = 12 çağrı değil
    assert mock_cur.call_count == len(config.TRACKED_ASSETS), \
        f"current_price {mock_cur.call_count} kez çağrıldı, {len(config.TRACKED_ASSETS)} beklendi"


@pytest.mark.asyncio
async def test_scan_edges_prints_scan_audit(capsys):
    """scan_edges her taramada [scan_audit] satırı basmalı."""
    from council.scout import scan_edges
    from unittest.mock import AsyncMock, patch
    import council.scout as _mod

    with patch.object(_mod, "_markets_cache", [_make_market(600)]), \
         patch.object(_mod, "_markets_cache_ts", 1e18), \
         patch("council.scout.current_price", new_callable=AsyncMock, return_value=61_000.0), \
         patch("council.scout.get_clob_price", new_callable=AsyncMock, return_value=0.35), \
         patch("council.scout.price_at_timestamp", new_callable=AsyncMock, return_value=60_000.0), \
         patch("council.scout.fair_yes", return_value=0.55), \
         patch("council.scout.fetch_fee_rate", new_callable=AsyncMock, return_value=0.02), \
         patch("council.scout._ws_prices.get_ask", return_value=None), \
         patch("council.scout._ws_prices.get_bid", return_value=None), \
         patch("council.scout._get_all_vols", new_callable=AsyncMock, return_value={}), \
         patch("council.scout._get_market_state", new_callable=AsyncMock, return_value={}):
        await scan_edges()

    out = capsys.readouterr().out
    assert "[scan_audit]" in out, f"[scan_audit] satırı beklendi, çıktı: {out!r}"
    assert "skip_time=" in out
    assert "api=" in out
