# Basis Risk + Funding Rate Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ekle: Spot/Perp basis dislokasyonu ve kalabalık funding rate durumlarında RedTeam'in işlemi veto etmesi — sıfır ekstra API çağrısı (HL meta verisi zaten mevcut).

**Architecture:** Scout, `fetch_market_state()` çıktısından `oracle_px` + `funding_rate` + `basis_pct` değerlerini 300s TTL ile cache'ler ve bunları finding dict'e ekler. RedTeam bu alanları okuyarak iki yeni veto kontrolü uygular: `high_basis_risk` (perp mid, oracle'dan >0.3% ayrışmış) ve `funding_rate_crowded` (saatlik funding |>0.0001|, anormallik habercisi). Verifier/Gate değişmez.

**Tech Stack:** Python asyncio, `data/hyperliquid.py::fetch_market_state()` (zaten mevcut), pytest-asyncio, TDD.

---

## Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|-------|------------|
| `council/scout.py` | Yeni import, iki yeni cache değişkeni, `_get_market_state()`, `_process_market` imzası ve return dict |
| `council/redteam.py` | İki yeni sabit + iki yeni erken veto kontrolü |
| `tests/test_scout.py` | 5 yeni test (market_state wiring) |
| `tests/test_redteam.py` | 6 yeni test (basis/funding veto) |

---

## Task 1: test_scout.py — Başarısız Testler (RED)

**Files:**
- Modify: `tests/test_scout.py`

- [ ] **Step 1: Mevcut test suite'ini çalıştır — hepsi geçiyor olmalı**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_scout.py -v --tb=short 2>&1 | tail -20
```

Expected: tüm mevcut testler PASS. Hata varsa önce onu düzelt.

- [ ] **Step 2: Beş yeni başarısız test ekle — test_scout.py dosyasının SONUNA**

`tests/test_scout.py` dosyasının sonuna şunları ekle (dosyayı oku, sonuna ekle):

```python
# ── Task: Basis+Funding wiring (market_state) ─────────────────────────────────

import council.scout as _scout_mod


def _make_market(seconds_remaining=300):
    """Test market dict — parse_market_window'u geçecek minimum alan seti."""
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
    """`market_state=None` (varsayılan) → oracle_px, funding_rate, basis_pct = None, çökmez."""
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
    """`_get_market_state()` üç alan içeren dict döner: oracle_px, funding_rate, basis_pct."""
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
```

- [ ] **Step 3: Testlerin FAILED olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_scout.py -k "market_state or oracle or funding or basis" -v --tb=short 2>&1 | tail -30
```

Expected: `ERROR` veya `FAILED` — `_process_market` üçüncü argüman kabul etmiyor, `_get_market_state` yok.

---

## Task 2: scout.py — Implementasyon (GREEN)

**Files:**
- Modify: `council/scout.py`

- [ ] **Step 1: `fetch_market_state` import ekle**

`council/scout.py` dosyasında `from data import ws_prices as _ws_prices` satırının ÜSTÜNE ekle:

```python
from data.hyperliquid import fetch_market_state
```

- [ ] **Step 2: İki yeni cache değişkeni ekle**

`_vol_cache_ts: float = 0.0` satırından SONRA ekle:

```python
_market_state_cache:    dict[str, dict] = {}
_market_state_cache_ts: float           = 0.0
```

- [ ] **Step 3: `_get_market_state()` fonksiyonunu ekle**

`_get_all_vols()` fonksiyonunun HEMEN SONRASINA (boş satır bırakarak) ekle:

```python
async def _get_market_state() -> dict[str, dict]:
    """Her asset için oracle_px, funding_rate, basis_pct — VOL_CACHE_TTL_SECS cache.
    fetch_market_state() tek API çağrısıyla tüm varlıkları döner → 0 ekstra maliyet.
    API hatasında: boş dict (RedTeam None kontrolüyle atlatır).
    """
    global _market_state_cache, _market_state_cache_ts
    now = time.time()
    if (now - _market_state_cache_ts) < VOL_CACHE_TTL_SECS and _market_state_cache:
        return _market_state_cache
    try:
        raw = await fetch_market_state(tuple(config.TRACKED_ASSETS))
        _market_state_cache = {
            asset: {
                "oracle_px":    d["oracle"],
                "funding_rate": d["funding"],
                "basis_pct":    abs(d["mid"] - d["oracle"]) / d["oracle"]
                                if d["oracle"] > 0 else 0.0,
            }
            for asset, d in raw.items()
        }
        _market_state_cache_ts = now
    except Exception:
        pass  # cache stale/boş kalır; RedTeam None kontrolüyle güvenli
    return _market_state_cache
```

- [ ] **Step 4: `_process_market` imzasına opsiyonel `market_state` parametresi ekle**

```python
# ESKİ:
async def _process_market(m: dict, asset_vols: dict[str, float]) -> dict | None:

# YENİ:
async def _process_market(m: dict, asset_vols: dict[str, float],
                           market_state: dict[str, dict] | None = None) -> dict | None:
```

- [ ] **Step 5: `_process_market` içinde `ms` çözümlemesi ekle**

`asset = _asset_of(...)` satırından HEMEN SONRA (if asset is None bloğundan önce değil, hemen arkasına) ekle:

NOT: `asset` değişkeni zaten tanımlanmış oluyor ama `if asset is None: return None` kontrolü yapılmadan önce ms tanımlanmaya çalışmamalı. En temiz yer: `if asset not in config.TRACKED_ASSETS` bloğundan sonra, `window = parse_market_window(m)` satırından ÖNCE:

```python
    ms = (market_state or {}).get(asset, {})
```

Bu satırı `asset = _asset_of(m.get("question", ""))` ve `if asset is None: return None` bloklarından SONRA, `if asset not in config.TRACKED_ASSETS` bloğundan SONRA, `window = parse_market_window(m)` satırından ÖNCE yerleştir.

Kesin konum (scout.py:118-121 arası):
```python
    if asset not in config.TRACKED_ASSETS:
        return None

    ms = (market_state or {}).get(asset, {})   # ← BURAYA EKLE

    window = parse_market_window(m)
```

- [ ] **Step 6: `_process_market` return dict'ine üç alan ekle**

`return { ... }` bloğunun `"taker_fee": taker_fee,` satırından SONRA şunları ekle:

```python
        "oracle_px":    ms.get("oracle_px"),
        "funding_rate": ms.get("funding_rate"),
        "basis_pct":    ms.get("basis_pct"),
```

- [ ] **Step 7: `scan_edges()` içinde `_get_market_state()` çağrısı ve geçiş ekle**

```python
# ESKİ:
    asset_vols = await _get_all_vols()
    tasks = [_process_market(m, asset_vols) for m in _markets_cache]

# YENİ:
    asset_vols   = await _get_all_vols()
    market_state = await _get_market_state()
    tasks = [_process_market(m, asset_vols, market_state) for m in _markets_cache]
```

- [ ] **Step 8: Yeni testlerin GEÇTİĞİNİ doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_scout.py -k "market_state or oracle or funding or basis" -v --tb=short 2>&1 | tail -30
```

Expected: 5 test PASS.

- [ ] **Step 9: Eski testlerin HÂLÂ geçtiğini doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_scout.py -v --tb=short 2>&1 | tail -20
```

Expected: tüm testler PASS (gerileme yok).

- [ ] **Step 10: Commit**

```bash
cd /root/mispricing_agent && git add council/scout.py tests/test_scout.py
git commit -m "$(cat <<'EOF'
feat(scout): oracle_px + funding_rate + basis_pct alanlarını finding dict'e ekle

_get_market_state() ile 300s cache — fetch_market_state() tek çağrıda
tüm varlıkları döndürür, 0 ekstra API maliyeti. _process_market imzasına
opsiyonel market_state parametresi eklendi (geriye uyumlu).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: test_redteam.py — Başarısız Testler (RED)

**Files:**
- Modify: `tests/test_redteam.py`

- [ ] **Step 1: Mevcut import satırını güncelle**

`tests/test_redteam.py` dosyasında import satırını bul:

```python
from council.redteam import (
    redteam, _parse_taker_fee, _fee_adjusted_edge, _result,
    SPREAD_VETO, LIQUIDITY_VETO_USD, MIN_THESIS_SECS, EDGE_SANITY_MAX,
    MIN_BOOK_DEPTH_USD,
)
```

Bunu şu şekilde değiştir (iki yeni sabit import ediyoruz):

```python
from council.redteam import (
    redteam, _parse_taker_fee, _fee_adjusted_edge, _result,
    SPREAD_VETO, LIQUIDITY_VETO_USD, MIN_THESIS_SECS, EDGE_SANITY_MAX,
    MIN_BOOK_DEPTH_USD, BASIS_VETO_PCT, FUNDING_RATE_VETO,
)
```

- [ ] **Step 2: Altı yeni test ekle — dosyanın SONUNA**

```python
# ── Task: Basis Risk + Funding Rate Guard ─────────────────────────────────────

def test_basis_veto_constant_value():
    """BASIS_VETO_PCT sabit değeri kontrol — eşiği biliriz."""
    assert BASIS_VETO_PCT == 0.003


def test_funding_rate_veto_constant_value():
    """FUNDING_RATE_VETO sabit değeri kontrol."""
    assert FUNDING_RATE_VETO == 0.0001


@pytest.mark.asyncio
async def test_veto_high_basis_risk():
    """basis_pct > 0.003 → high_basis_risk veto."""
    f = _fake_finding()
    f["basis_pct"]    = 0.004   # > 0.003 eşiği
    f["funding_rate"] = 0.0     # normal
    result = await redteam(f, _fake_verification())
    assert "high_basis_risk" in result["vetoes"]


@pytest.mark.asyncio
async def test_veto_funding_rate_crowded():
    """|funding_rate| > 0.0001 → funding_rate_crowded veto."""
    f = _fake_finding()
    f["basis_pct"]    = 0.0     # normal
    f["funding_rate"] = 0.0002  # > 0.0001 eşiği
    result = await redteam(f, _fake_verification())
    assert "funding_rate_crowded" in result["vetoes"]


@pytest.mark.asyncio
async def test_veto_negative_funding_rate_crowded():
    """Negatif funding da kalabalık → |−0.0002| > 0.0001 → veto."""
    f = _fake_finding()
    f["basis_pct"]    = 0.0
    f["funding_rate"] = -0.0002
    result = await redteam(f, _fake_verification())
    assert "funding_rate_crowded" in result["vetoes"]


@pytest.mark.asyncio
async def test_no_veto_normal_basis_and_funding():
    """Normal değerler → ne basis ne funding veto."""
    f = _fake_finding()
    f["basis_pct"]    = 0.001    # < 0.003 → OK
    f["funding_rate"] = 4.8e-6   # << 0.0001 → OK
    result = await redteam(f, _fake_verification())
    assert "high_basis_risk"      not in result["vetoes"]
    assert "funding_rate_crowded" not in result["vetoes"]


@pytest.mark.asyncio
async def test_no_veto_when_basis_funding_absent():
    """Alanlar yoksa (None) → kontrol atlanır, çökmez."""
    f = _fake_finding()   # basis_pct / funding_rate yoksa None dönmeli
    # _fake_finding bu alanları içermiyor
    result = await redteam(f, _fake_verification())
    # Sadece basis/funding veto olmamalı (başka veto olabilir: market_data_unavailable vs)
    assert "high_basis_risk"      not in result["vetoes"]
    assert "funding_rate_crowded" not in result["vetoes"]
```

- [ ] **Step 3: Testlerin FAILED olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_redteam.py -k "basis or funding" -v --tb=short 2>&1 | tail -30
```

Expected: `ImportError` veya `FAILED` — `BASIS_VETO_PCT`, `FUNDING_RATE_VETO` henüz tanımlı değil.

---

## Task 4: redteam.py — Implementasyon (GREEN)

**Files:**
- Modify: `council/redteam.py`

- [ ] **Step 1: İki yeni sabit ekle**

`council/redteam.py` dosyasında `ENTRY_SLIPPAGE = 0.015` satırından SONRA ekle:

```python
BASIS_VETO_PCT     = 0.003   # |perp_mid − oracle| / oracle > 0.3% → spot'tan kopuk
FUNDING_RATE_VETO  = 0.0001  # |funding/saat| > 0.01%/saat → kalabalık kaldıraç pozisyonu
```

- [ ] **Step 2: İki yeni veto kontrolü ekle**

`council/redteam.py` dosyasında şu bloğu bul:

```python
    # ── 1-2. API gerektirmeyen erken kontroller ───────────────────────────────
    if verification["fresh_edge"] > EDGE_SANITY_MAX:
        vetoes.append("edge_suspiciously_large")

    if verification["fresh_seconds"] < MIN_THESIS_SECS:
        vetoes.append("insufficient_time_for_thesis")

    # ── Gamma'dan taze market verisi ─────────────────────────────────────────
```

Bu bloğu şununla değiştir (iki kontrol eklenmiş):

```python
    # ── 1-2. API gerektirmeyen erken kontroller ───────────────────────────────
    if verification["fresh_edge"] > EDGE_SANITY_MAX:
        vetoes.append("edge_suspiciously_large")

    if verification["fresh_seconds"] < MIN_THESIS_SECS:
        vetoes.append("insufficient_time_for_thesis")

    # ── 1c. Spot/Perp basis ve funding rate (Scout'tan, 0 ekstra API) ─────────
    basis_pct    = finding.get("basis_pct")
    funding_rate = finding.get("funding_rate")
    if basis_pct is not None and abs(basis_pct) > BASIS_VETO_PCT:
        vetoes.append("high_basis_risk")
    if funding_rate is not None and abs(funding_rate) > FUNDING_RATE_VETO:
        vetoes.append("funding_rate_crowded")

    # ── Gamma'dan taze market verisi ─────────────────────────────────────────
```

- [ ] **Step 3: Yeni testlerin GEÇTİĞİNİ doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_redteam.py -k "basis or funding" -v --tb=short 2>&1 | tail -30
```

Expected: 6 test PASS.

- [ ] **Step 4: Eski testlerin HÂLÂ geçtiğini doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_redteam.py -v --tb=short 2>&1 | tail -20
```

Expected: tüm testler PASS.

- [ ] **Step 5: Commit**

```bash
cd /root/mispricing_agent && git add council/redteam.py tests/test_redteam.py
git commit -m "$(cat <<'EOF'
feat(redteam): basis risk + funding rate veto guard ekle

BASIS_VETO_PCT=0.003 (spot/perp %0.3 dislokasyonu) ve
FUNDING_RATE_VETO=0.0001/saat (kalabalık kaldıraç). Scout'tan
gelen oracle_px+funding_rate verisini kullanır, 0 ekstra API çağrısı.
Alanlar None ise kontrol atlanır — graceful degradation.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Tam Suite Doğrulaması + Graphify + Push

**Files:** Yok (doğrulama + araç çağrıları)

- [ ] **Step 1: Tüm test suite çalıştır**

```bash
cd /root/mispricing_agent && python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: tüm testler PASS (önceki 346+ + yeni 11 = 357+ geçiyor). Yeni FAIL varsa Task 2 veya 4'e dön, düzelt.

- [ ] **Step 2: Graphify güncelle**

```bash
cd /root/mispricing_agent && graphify update .
```

- [ ] **Step 3: GitHub'a push et**

```bash
cd /root/mispricing_agent && git push origin master
```

- [ ] **Step 4: Push başarısını doğrula**

```bash
cd /root/mispricing_agent && git log --oneline -5
```

Expected: son 2 commit (scout + redteam) görünüyor.

---

## Özet: Neden Bu Tasarım?

1. **P2 reddedildi** (oracle'ı `current_price` için kullanmak): `log(oracle_now / perp_ref)` = apples-to-oranges. Perp candle'dan gelen tarihsel referans fiyata karşı spot oracle kullanmak 3 senaryodan 2'sinde yanlış sonuç verir.

2. **P1 uygulandı** (filtre, formül değişikliği değil): Basis yüksekse işlemi atla. Basis düşükse perp ≈ oracle → mevcut fair_value formülü doğru. Sıfır formül değişikliği.

3. **Sıfır ekstra API çağrısı**: `fetch_market_state()` zaten `metaAndAssetCtxs` endpoint'ini çağırıyor ve `oracle`, `funding`, `mid` döndürüyor. Scout'un vol cache'i ile aynı TTL (300s).

4. **Graceful degradation**: API hatasında cache boş kalır → `ms.get("oracle_px")` → None → RedTeam kontrolü atlanır. Bot çalışmaya devam eder.
