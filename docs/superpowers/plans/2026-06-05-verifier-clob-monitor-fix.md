# Verifier CLOB Fix + Monitor API-Error Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two bugs causing false trades and duplicate positions: (1) Verifier uses stale market API `bestAsk` instead of real CLOB price → trades open with negative real edge; (2) `_monitor_positions` closes positions on transient API errors → scout re-opens the same market.

**Architecture:**
- Extract shared `get_clob_price()` to `data/clob_price.py` (used by both verifier and executor).
- Verifier fetches CLOB `/price` per token; if CLOB shows no liquidity or edge_gone → soft fail.
- Monitor skips (does NOT close) when `fetch_by_slug` AND `fetch_resolved` both return None (transient API error).

**Tech Stack:** Python asyncio, aiohttp, pytest-asyncio, unittest.mock

---

### Task 1: Extract `get_clob_price` to `data/clob_price.py`

**Files:**
- Create: `data/clob_price.py`
- Modify: `execution/clob_executor.py` (import instead of local copy)
- Create: `tests/test_clob_price.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_clob_price.py`:

```python
"""data/clob_price.py testleri."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.clob_price import get_clob_price


@pytest.mark.asyncio
async def test_get_clob_price_returns_float_on_success():
    """Başarılı API yanıtında float döner."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"price": "0.7500"})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("data.clob_price.aiohttp.ClientSession", return_value=mock_session):
        result = await get_clob_price("tok-abc")
    assert result == 0.75


@pytest.mark.asyncio
async def test_get_clob_price_returns_none_when_price_zero():
    """API price=0 → None döner (liquidity yok)."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"price": "0"})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("data.clob_price.aiohttp.ClientSession", return_value=mock_session):
        result = await get_clob_price("tok-abc")
    assert result is None


@pytest.mark.asyncio
async def test_get_clob_price_returns_none_on_http_error():
    """HTTP 400/500 → None döner."""
    mock_resp = MagicMock()
    mock_resp.status = 400
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("data.clob_price.aiohttp.ClientSession", return_value=mock_session):
        result = await get_clob_price("tok-abc")
    assert result is None


@pytest.mark.asyncio
async def test_get_clob_price_returns_none_on_exception():
    """Network exception → None döner (crash yok)."""
    with patch("data.clob_price.aiohttp.ClientSession", side_effect=Exception("timeout")):
        result = await get_clob_price("tok-abc")
    assert result is None


@pytest.mark.asyncio
async def test_get_clob_price_returns_none_for_empty_token():
    """Boş token_id → API çağrısı yapılmaz, None döner."""
    with patch("data.clob_price.aiohttp.ClientSession") as mock_cls:
        result = await get_clob_price("")
    mock_cls.assert_not_called()
    assert result is None


@pytest.mark.asyncio
async def test_get_clob_price_returns_none_for_none_token():
    """None token_id → API çağrısı yapılmaz, None döner."""
    with patch("data.clob_price.aiohttp.ClientSession") as mock_cls:
        result = await get_clob_price(None)
    mock_cls.assert_not_called()
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/test_clob_price.py -v 2>&1 | head -30
```
Expected: `ModuleNotFoundError: No module named 'data.clob_price'`

- [ ] **Step 3: Create `data/clob_price.py`**

```python
"""data/clob_price.py — CLOB anlık fiyat yardımcısı (paylaşımlı)."""
import aiohttp

CLOB_HOST = "https://clob.polymarket.com"


async def get_clob_price(token_id: str) -> float | None:
    """CLOB /price?side=BUY → token için anlık best ask fiyatı.

    Returns: float (>0) veya None (liquidity yok / hata).
    """
    if not token_id:
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(
                f"{CLOB_HOST}/price",
                params={"token_id": token_id, "side": "BUY"},
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    p = float(data.get("price", 0))
                    return p if p > 0 else None
    except Exception:
        pass
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_clob_price.py -v
```
Expected: `6 passed`

- [ ] **Step 5: Update `execution/clob_executor.py` to import from `data.clob_price`**

Remove the local `_get_clob_price` function (lines ~26-39) and replace with import:

```python
from data.clob_price import get_clob_price as _get_clob_price
```

- [ ] **Step 6: Verify clob_executor tests still pass**

```bash
pytest tests/test_clob_executor.py -v
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add data/clob_price.py execution/clob_executor.py tests/test_clob_price.py
git commit -m "refactor: get_clob_price data/clob_price.py'ye taşındı (paylaşımlı)"
```

---

### Task 2: Verifier — CLOB price ile edge doğrulaması

**Root cause:** Verifier, `fetch_by_slug` ile market API'nin `bestAsk`'ını kullanır. Market API CLOB'dan 10-30 saniye gecikmeli kalır → sahte edge → negatif gerçek edge ile trade açılır.

**Files:**
- Modify: `council/verifier.py`
- Modify: `tests/test_verifier.py`

- [ ] **Step 1: Yeni failing testler yaz**

`tests/test_verifier.py` dosyasına ekle (mevcut testlerin altına):

```python
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
```

- [ ] **Step 2: Testlerin kırmızı olduğunu doğrula**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/test_verifier.py::test_verify_uses_clob_price_for_edge_not_market_api \
       tests/test_verifier.py::test_verify_edge_gone_when_clob_eliminates_edge \
       tests/test_verifier.py::test_verify_edge_gone_when_no_clob_liquidity \
       -v 2>&1 | tail -15
```
Expected: `FAILED` — `get_clob_price` import error.

- [ ] **Step 3: `council/verifier.py` güncelle**

Tam yeni `council/verifier.py` içeriği:

```python
"""
council/verifier.py — KATMAN 2: Bağımsız Doğrulayıcı.

Scout bulgusunu CLOB gerçek zamanlı fiyatıyla teyit eder.
  - CLOB /price ile edge yeniden hesaplanır (market API değil)
  - Soft fail: edge_gone, expired, fetch_error  → halt=False
  - Hard fail: HL drift anomalisi               → halt=HALT_ON_API_MISMATCH
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.hl_candles import current_price
from data.shortterm import fetch_by_slug, parse_market_window
from data.fair_value import fair_yes
from data.clob_price import get_clob_price
import config

PRICE_DRIFT_HALT_PCT = 2.0    # HL fiyatı Scout'tan bu yana >%2 farklıysa → HALT
PM_DRIFT_HALT        = 0.10   # Bilgi amaçlı — artık blocking değil
MIN_SECONDS          = 60     # Çözüme <60s kaldıysa → expired


async def verify(finding: dict) -> dict:
    """
    Scout bulgusunu bağımsız CLOB fiyatıyla doğrular.

    Returns:
        {pass, reason, halt, fresh_cur_price, fresh_best_ask, fresh_best_bid,
         fresh_fair, fresh_edge, fresh_seconds, hl_drift_pct, pm_drift}
    """
    asset     = finding["asset"]
    slug      = finding["slug"]
    scout_cur = finding["cur_price"]
    scout_ask = finding["best_ask"]
    ref_price = finding["ref_price"]
    action    = finding["action"]

    # ── 1. HL taze fiyat ──────────────────────────────────────────────────────
    try:
        fresh_cur = await current_price(asset)
    except Exception as e:
        return _result(False, "fetch_error", False, extra={"error": str(e)})

    # ── 2. HL drift kontrolü ─────────────────────────────────────────────────
    hl_drift = abs(fresh_cur - scout_cur) / scout_cur * 100
    if hl_drift > PRICE_DRIFT_HALT_PCT:
        return _result(False, "api_mismatch", config.HALT_ON_API_MISMATCH,
                       fresh_cur=fresh_cur, hl_drift_pct=hl_drift)

    # ── 3. CLOB gerçek zamanlı fiyat ─────────────────────────────────────────
    # YES action → YES token fiyatı; NO action → NO token fiyatı
    token_id = finding.get("yes_token_id") if action == "YES" else finding.get("no_token_id")
    clob_price = await get_clob_price(token_id) if token_id else None

    if not clob_price:
        return _result(False, "edge_gone", False,
                       fresh_cur=fresh_cur, hl_drift_pct=hl_drift,
                       extra={"clob_reason": "no_clob_liquidity"})

    # CLOB fiyatını YES frame'ine çevir (verifier formülüyle uyumlu)
    if action == "YES":
        fresh_ask = clob_price               # YES ask
        fresh_bid = max(0.0, clob_price - 0.01)
    else:
        fresh_bid = max(0.0, 1.0 - clob_price)   # YES bid = 1 - NO ask
        fresh_ask = min(1.0, fresh_bid + 0.01)

    # pm_drift: bilgi amaçlı (artık blocking değil — market API ile CLOB farklı sistemler)
    pm_drift = abs(clob_price - scout_ask)

    # ── 4. Süre kontrolü ─────────────────────────────────────────────────────
    fresh_seconds = None
    try:
        market = await fetch_by_slug(slug)
        if market is not None:
            window = parse_market_window(market)
            if window is not None:
                fresh_seconds = window["seconds_remaining"]
    except Exception:
        pass

    if fresh_seconds is None:
        w = finding.get("_window")
        fresh_seconds = w["seconds_remaining"] if w else 0.0

    if fresh_seconds < MIN_SECONDS:
        return _result(False, "expired", False,
                       fresh_cur=fresh_cur, fresh_ask=fresh_ask,
                       fresh_bid=fresh_bid, fresh_seconds=fresh_seconds,
                       hl_drift_pct=hl_drift, pm_drift=pm_drift)

    # ── 5. Fair value + edge (CLOB fiyatıyla) ────────────────────────────────
    fresh_fair = fair_yes(fresh_cur, ref_price, fresh_seconds, asset)
    fresh_edge = (fresh_fair - fresh_ask) if action == "YES" else (fresh_bid - fresh_fair)

    # ── 6. Edge kontrolü ─────────────────────────────────────────────────────
    if fresh_edge < config.MIN_EDGE_PCT:
        return _result(False, "edge_gone", False,
                       fresh_cur=fresh_cur, fresh_ask=fresh_ask,
                       fresh_bid=fresh_bid, fresh_seconds=fresh_seconds,
                       fresh_fair=fresh_fair, fresh_edge=fresh_edge,
                       hl_drift_pct=hl_drift, pm_drift=pm_drift)

    # ── 7. PASS ───────────────────────────────────────────────────────────────
    return _result(True, "ok", False,
                   fresh_cur=fresh_cur, fresh_ask=fresh_ask,
                   fresh_bid=fresh_bid, fresh_seconds=fresh_seconds,
                   fresh_fair=fresh_fair, fresh_edge=fresh_edge,
                   hl_drift_pct=hl_drift, pm_drift=pm_drift)


def _result(pass_: bool, reason: str, halt: bool, *,
            fresh_cur: float = 0.0, fresh_ask: float = 0.0,
            fresh_bid: float = 0.0, fresh_seconds: float = 0.0,
            fresh_fair: float = 0.0, fresh_edge: float = 0.0,
            hl_drift_pct: float = 0.0, pm_drift: float = 0.0,
            extra: dict = None) -> dict:
    r = {
        "pass":            pass_,
        "reason":          reason,
        "halt":            halt,
        "fresh_cur_price": fresh_cur,
        "fresh_best_ask":  fresh_ask,
        "fresh_best_bid":  fresh_bid,
        "fresh_fair":      fresh_fair,
        "fresh_edge":      round(fresh_edge, 4),
        "fresh_seconds":   fresh_seconds,
        "hl_drift_pct":    round(hl_drift_pct, 4),
        "pm_drift":        round(pm_drift, 4),
    }
    if extra:
        r.update(extra)
    return r


async def main():
    from council.scout import scan_edges
    print("=" * 70)
    print("VERIFIER — Scout bulgularını CLOB fiyatıyla teyit ediyor")
    print("=" * 70)
    findings = await scan_edges()
    if not findings:
        print("Scout'tan bulgu gelmedi.")
        return
    for f in findings:
        r = await verify(f)
        icon = "PASS" if r["pass"] else f"FAIL [{r['reason']}]"
        halt = " *** HALT ***" if r["halt"] else ""
        print(f"\n{f['question'][:55]}")
        print(f"  Scout edge : {f['edge']:+.3f}  ask:{f['best_ask']:.3f}")
        print(f"  CLOB ask   : {r['fresh_best_ask']:.3f}  edge:{r['fresh_edge']:+.3f}")
        print(f"  HL drift   : {r['hl_drift_pct']:.4f}%  |  PM drift: {r['pm_drift']:.4f}")
        print(f"  Sonuç      : {icon}{halt}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

- [ ] **Step 4: Yeni testlerin yeşil olduğunu doğrula**

```bash
pytest tests/test_verifier.py::test_verify_uses_clob_price_for_edge_not_market_api \
       tests/test_verifier.py::test_verify_edge_gone_when_clob_eliminates_edge \
       tests/test_verifier.py::test_verify_edge_gone_when_no_clob_liquidity \
       tests/test_verifier.py::test_verify_no_halt_on_large_clob_vs_market_api_drift \
       tests/test_verifier.py::test_verify_no_action_uses_no_token_id \
       tests/test_verifier.py::test_verify_yes_action_uses_yes_token_id \
       -v 2>&1 | tail -15
```
Expected: `6 passed`

- [ ] **Step 5: Eski testlerin durumunu kontrol et ve güncelle**

```bash
pytest tests/test_verifier.py -v 2>&1 | tail -30
```

Kırılan testleri tespit et. Kıran testler `get_clob_price` mock'lamıyor olanlardır. Her kırık test için mock ekle:

```python
# Kırık test örneği — şu şekilde güncelle:
@pytest.mark.asyncio
async def test_verify_hl_drift_triggers_halt():
    """HL fiyat %2+ sapması → halt (HALT_ON_API_MISMATCH config)."""
    finding = _fake_finding_with_tokens(cur_price=100_000.0)
    with patch("council.verifier.current_price", new_callable=AsyncMock, return_value=103_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=0.40):
        result = await verify(finding)
    assert result["pass"] is False
    assert result["halt"] == config.HALT_ON_API_MISMATCH

@pytest.mark.asyncio
async def test_verify_expired_soft_fail():
    """seconds_remaining < MIN_SECONDS → expired (halt=False)."""
    finding = _fake_finding_with_tokens(seconds_remaining=30.0)
    with patch("council.verifier.current_price", new_callable=AsyncMock, return_value=105_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=0.40), \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock, return_value=None), \
         patch("council.verifier.fair_yes", return_value=0.60):
        result = await verify(finding)
    assert result["pass"] is False
    assert result["reason"] == "expired"
    assert result["halt"] is False

@pytest.mark.asyncio
async def test_verify_invalid_slug_fetch_error_no_halt():
    """fetch_by_slug None ama CLOB OK → _window fallback, süre yeterli → PASS."""
    finding = _fake_finding_with_tokens(seconds_remaining=300.0)
    with patch("council.verifier.current_price", new_callable=AsyncMock, return_value=105_000.0), \
         patch("council.verifier.get_clob_price", new_callable=AsyncMock, return_value=0.40), \
         patch("council.verifier.fetch_by_slug", new_callable=AsyncMock, return_value=None), \
         patch("council.verifier.fair_yes", return_value=0.60):
        result = await verify(finding)
    # _window fallback: seconds=300 → not expired, CLOB edge = 0.60-0.40=0.20 → PASS
    assert result["pass"] is True
```

- [ ] **Step 6: Tüm verifier testleri yeşil**

```bash
pytest tests/test_verifier.py -v 2>&1 | tail -20
```
Expected: all passed

- [ ] **Step 7: Commit**

```bash
git add council/verifier.py tests/test_verifier.py
git commit -m "feat(verifier): market API yerine CLOB /price ile edge doğrulaması

Stale market API bestAsk yerine CLOB /price kullanılıyor.
CLOB liquidity yoksa edge_gone (soft fail).
PM_DRIFT_HALT artık blocking değil — market API vs CLOB farklı sistemler."
```

---

### Task 3: Monitor — geçici API hatasında pozisyon kapatma

**Root cause:** `_monitor_positions`'da `fetch_by_slug` geçici `None` döndüğünde ve `fetch_resolved` da `None` dönünce, pozisyon `market_expired` olarak kapatılıyor. Bir sonraki scan aynı marketi tekrar açıyor → duplicate pozisyon.

**Files:**
- Modify: `main_loop.py` (sadece `_monitor_positions` içindeki `window is None` bloğu)
- Modify: `tests/test_main_loop.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_main_loop.py` dosyasına ekle:

```python
@pytest.mark.asyncio
async def test_monitor_skips_position_on_transient_api_error():
    """fetch_by_slug=None VE fetch_resolved=None → pozisyon kapatılmaz, atlanır."""
    from main_loop import _monitor_positions

    pos = {
        "position_id": "pos-skip-001",
        "slug": "btc-updown-5m-9999",
        "asset": "BTC",
        "action": "YES",
        "pm_entry_price": 0.80,
        "position_usd": 1.25,
        "shares": 1.5,
        "status": "open",
        "seq_no": 1,
    }
    open_positions = [pos]
    closed_today = []

    with patch("main_loop.current_price", new_callable=AsyncMock, return_value=95_000.0), \
         patch("main_loop.fetch_by_slug", new_callable=AsyncMock, return_value=None), \
         patch("main_loop.fetch_resolved", new_callable=AsyncMock, return_value=None):
        await _monitor_positions(open_positions, closed_today, conn=None)

    # API error olduğunda pozisyon kapatılmaz
    assert len(open_positions) == 1, "Geçici API hatasında pozisyon listeden çıkarılmamalı"
    assert len(closed_today) == 0, "Geçici API hatasında closed_today'e eklenmemeli"
    assert open_positions[0]["status"] == "open"


@pytest.mark.asyncio
async def test_monitor_closes_on_definitive_resolution():
    """fetch_by_slug=None ama fetch_resolved sonuç döndürünce → market_resolved kapatılır."""
    from main_loop import _monitor_positions

    pos = {
        "position_id": "pos-resolve-001",
        "slug": "btc-updown-5m-8888",
        "asset": "BTC",
        "action": "YES",
        "pm_entry_price": 0.75,
        "position_usd": 1.25,
        "shares": 1.5,
        "status": "open",
        "seq_no": 1,
        "entry_hl_price": 95_000.0,
    }
    open_positions = [pos]
    closed_today = []

    with patch("main_loop.current_price", new_callable=AsyncMock, return_value=95_000.0), \
         patch("main_loop.fetch_by_slug", new_callable=AsyncMock, return_value=None), \
         patch("main_loop.fetch_resolved", new_callable=AsyncMock,
               return_value={"yes_exit": 1.0, "no_exit": 0.0}), \
         patch("main_loop.log_position_close", new_callable=AsyncMock):
        await _monitor_positions(open_positions, closed_today, conn=None)

    assert len(open_positions) == 0, "Resolved market pozisyonu kapatmalı"
    assert len(closed_today) == 1
    assert closed_today[0]["exit_reason"] == "market_resolved"
```

- [ ] **Step 2: Testlerin kırmızı olduğunu doğrula**

```bash
pytest tests/test_main_loop.py::test_monitor_skips_position_on_transient_api_error \
       tests/test_main_loop.py::test_monitor_closes_on_definitive_resolution \
       -v 2>&1 | tail -15
```
Expected: `test_monitor_skips_position_on_transient_api_error` FAILS (pozisyon hatalı kapatılıyor).

- [ ] **Step 3: `main_loop.py` — `_monitor_positions` içindeki `window is None` bloğunu düzelt**

`main_loop.py` satır 238-248 bloğunu bul ve değiştir:

**ESKİ (kaldır):**
```python
if window is None:
    resolution = await fetch_resolved(pos["slug"])
    if resolution:
        pm_exit = resolution["yes_exit"] if pos["action"] == "YES" else resolution["no_exit"]
        closed = close_position(pos, "market_resolved", pm_exit_price=pm_exit,
                                exit_hl_price=hl_price)
    else:
        closed = close_position(pos, "market_expired", exit_hl_price=hl_price)
    await log_position_close(conn, closed)
    open_positions.remove(pos)
    closed_today.append(closed)
    continue
```

**YENİ:**
```python
if window is None:
    resolution = await fetch_resolved(pos["slug"])
    if resolution:
        pm_exit = resolution["yes_exit"] if pos["action"] == "YES" else resolution["no_exit"]
        closed = close_position(pos, "market_resolved", pm_exit_price=pm_exit,
                                exit_hl_price=hl_price)
        await log_position_close(conn, closed)
        open_positions.remove(pos)
        closed_today.append(closed)
    # fetch_resolved da None → geçici API hatası, bu döngüde atla
    # Pozisyonu kapatma: bir sonraki scan döngüsünde tekrar dene
    continue
```

- [ ] **Step 4: Testlerin yeşil olduğunu doğrula**

```bash
pytest tests/test_main_loop.py::test_monitor_skips_position_on_transient_api_error \
       tests/test_main_loop.py::test_monitor_closes_on_definitive_resolution \
       -v
```
Expected: `2 passed`

- [ ] **Step 5: Mevcut monitor testlerinin hâlâ geçtiğini doğrula**

```bash
pytest tests/test_main_loop.py -v 2>&1 | tail -20
```

Kırılan test varsa kontrol et: `test_monitor_closes_on_missing_market` testi ESKİ davranışı test ediyorsa güncelle:

```python
@pytest.mark.asyncio
async def test_monitor_closes_on_missing_market():
    """fetch_by_slug=None ama fetch_resolved sonuç döndürünce kapanır."""
    # Bu test artık fetch_resolved'ın sonuç döndürdüğü durumu test eder
    # fetch_resolved=None durumu atlanır (test_monitor_skips_position_on_transient_api_error)
    ...
    with patch(..., fetch_resolved=AsyncMock(return_value={"yes_exit": 1.0, "no_exit": 0.0})):
        await _monitor_positions(open_positions, closed_today, conn=None)
    assert len(open_positions) == 0  # kapatılmalı
```

- [ ] **Step 6: Tüm testler yeşil**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -10
```
Expected: all passed (5 skip OK)

- [ ] **Step 7: Commit**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "fix(monitor): geçici API hatasında pozisyon kapatılmıyor

fetch_by_slug=None VE fetch_resolved=None → pozisyon atlanır, kapatılmaz.
Sadece fetch_resolved kesin sonuç döndürünce market_resolved kapanışı yapılır.
Neden: geçici API hatası 'market_expired' tetikliyordu → scout aynı marketi
tekrar açıyordu → duplicate pozisyon."
```

---

### Task 4: Son doğrulama ve GitHub push

- [ ] **Step 1: Tüm test suite yeşil**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/ -v --tb=short 2>&1 | tail -15
```
Expected: ≥295 passed, 0 failed

- [ ] **Step 2: graphify güncelle**

```bash
graphify update .
```

- [ ] **Step 3: GitHub push**

```bash
git push origin master
```

- [ ] **Step 4: Bot restart**

```bash
./restart.sh
```

Expected: `1 process çalışıyor (tmux: mispricing)`
