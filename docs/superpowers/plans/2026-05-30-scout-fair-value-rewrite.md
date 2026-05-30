# Scout Fair Value Rewrite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scout'un hatalı `0.50` sabit referans fiyatını gerçek binary-option fair value modeli ile değiştir; bayat `outcomePrices` yerine canlı `bestAsk/bestBid` kullan; pencere hizalamasını `eventStartTime`'a göre düzelt.

**Architecture:** 3 yeni/değiştirilmiş veri katmanı fonksiyonu (fair_value, price_at_timestamp, parse_market_window), ardından Scout'un TDD ile tamamen yeniden yazılması. Tüm testler gerçek API'ye karşı çalışır — mock yok.

**Tech Stack:** Python 3.11, aiohttp, pytest-asyncio, math.erf (standart kütüphane, scipy gerekmez)

---

## Dosya Haritası

| Dosya | İşlem | Sorumluluk |
|-------|--------|-----------|
| `data/fair_value.py` | **YENİ** | Binary option fair value: `fair_yes(p_now, p_ref, secs, asset)` |
| `data/hl_candles.py` | **GÜNCELLENİYOR** | `price_at_timestamp(asset, ts_ms)` + `current_price(asset)` ekleniyor |
| `data/shortterm.py` | **GÜNCELLENİYOR** | `parse_market_window(m)` — eventStartTime/endDate/bestBid/bestAsk çıkarımı |
| `council/scout.py` | **TAM REWRITE** | Yeni fair value modeli ile sıfırdan |
| `tests/test_fair_value.py` | **YENİ** | fair_yes() unit testleri |
| `tests/test_hl_candles.py` | **YENİ** | price_at_timestamp() + current_price() integration testleri |
| `tests/test_shortterm.py` | **YENİ** | parse_market_window() testleri |
| `tests/test_scout.py` | **YENİ** | Scout integration testleri |

---

## Task A1: data/fair_value.py — Binary Option Fair Value Modeli

**Files:**
- Create: `data/fair_value.py`
- Create: `tests/test_fair_value.py`

### Matematiksel temel
BTC fiyatı log-normal dağılım izler (GBM). Kısa pencereler (≤60 dk) için drift ihmal edilebilir. Binary option:

```
P(S_T > K | S_t = p_now) = Φ(d)
d = log(p_now / p_ref) / (σ * sqrt(T))
σ_yıllık: BTC=0.80, ETH=1.20, SOL=1.50, XRP=1.50
```

- [ ] **Adım 1: Failing testleri yaz**

```python
# tests/test_fair_value.py
import math
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.fair_value import fair_yes, ASSET_VOL

def test_fair_yes_at_reference_price_is_half():
    """Fiyat tam referanstayken, süre varsa → 0.50."""
    result = fair_yes(100_000.0, 100_000.0, 300.0, "BTC")
    assert abs(result - 0.5) < 1e-6

def test_fair_yes_above_reference_is_above_half():
    """Fiyat referansın üstündeyse → 0.50'den büyük."""
    result = fair_yes(101_000.0, 100_000.0, 300.0, "BTC")
    assert result > 0.5

def test_fair_yes_below_reference_is_below_half():
    """Fiyat referansın altındaysa → 0.50'den küçük."""
    result = fair_yes(99_000.0, 100_000.0, 300.0, "BTC")
    assert result < 0.5

def test_fair_yes_expired_above():
    """Süre dolmuş, fiyat referansın üstünde → 1.0."""
    assert fair_yes(101_000.0, 100_000.0, 0.0, "BTC") == 1.0

def test_fair_yes_expired_below():
    """Süre dolmuş, fiyat referansın altında → 0.0."""
    assert fair_yes(99_000.0, 100_000.0, 0.0, "BTC") == 0.0

def test_fair_yes_expired_equal():
    """Süre dolmuş, fiyat tam referansta → 0.0 (üstünde değil)."""
    assert fair_yes(100_000.0, 100_000.0, 0.0, "BTC") == 0.0

def test_fair_yes_concrete_example():
    """
    Somut: ref=105000, cur=104800, 180s kaldı (BTC vol=80%).
    Analitik: z = log(104800/105000) / (0.80 * sqrt(180/31557600)) ≈ -1.0
    Φ(-1.0) ≈ 0.159 → beklenti [0.10, 0.25] aralığında.
    """
    result = fair_yes(104_800.0, 105_000.0, 180.0, "BTC")
    assert 0.10 < result < 0.25

def test_fair_yes_symmetry():
    """fair_yes(up) + fair_yes(down) == 1 (aynı mutlak sapma)."""
    above = fair_yes(101_000.0, 100_000.0, 300.0, "BTC")
    below = fair_yes(99_000.0, 100_000.0, 300.0, "BTC")
    assert abs(above + below - 1.0) < 1e-6

def test_fair_yes_invalid_zero_price():
    """Sıfır fiyat ValueError fırlatır."""
    with pytest.raises(ValueError, match="pozitif"):
        fair_yes(0.0, 100_000.0, 300.0, "BTC")

def test_fair_yes_invalid_negative_price():
    with pytest.raises(ValueError, match="pozitif"):
        fair_yes(-1.0, 100_000.0, 300.0, "BTC")

def test_fair_yes_output_range():
    """Her koşulda sonuç [0,1] aralığında."""
    cases = [
        (50_000.0, 100_000.0, 300.0, "BTC"),   # çok geride
        (200_000.0, 100_000.0, 300.0, "BTC"),  # çok ileride
        (100_000.0, 100_000.0, 1.0, "BTC"),    # neredeyse bitti
    ]
    for args in cases:
        r = fair_yes(*args)
        assert 0.0 <= r <= 1.0, f"Aralık dışı: {r} for {args}"

def test_asset_vol_keys_exist():
    """Takip edilen tüm varlıklar ASSET_VOL sözlüğünde var."""
    for asset in ("BTC", "ETH", "SOL", "XRP"):
        assert asset in ASSET_VOL
        assert ASSET_VOL[asset] > 0
```

- [ ] **Adım 2: Testlerin kırmızı olduğunu doğrula**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/test_fair_value.py -v 2>&1 | head -30
```

Beklenti: `ModuleNotFoundError: No module named 'data.fair_value'`

- [ ] **Adım 3: data/fair_value.py'yi yaz**

```python
"""
data/fair_value.py — Binary option fair value hesaplayıcı.
Model: log-normal GBM, drift yok (kısa pencereler ≤60dk için geçerli).
P(fiyat > referans | şimdiki fiyat, kalan süre) = Φ(log(p_now/p_ref) / σ√T)
"""
import math

ASSET_VOL = {
    "BTC": 0.80,
    "ETH": 1.20,
    "SOL": 1.50,
    "XRP": 1.50,
}

_SECONDS_PER_YEAR = 31_557_600.0


def fair_yes(p_now: float, p_ref: float, seconds_remaining: float, asset: str = "BTC") -> float:
    """
    P(asset_price > p_ref at resolution | current_price = p_now)
    
    Args:
        p_now: Şimdiki fiyat (HL live)
        p_ref: Referans fiyat (PM penceresinin açılışında HL fiyatı)
        seconds_remaining: Çözüme kadar kalan saniye
        asset: "BTC", "ETH", "SOL", "XRP"
    
    Returns:
        [0.0, 1.0] arası float — YES token'ın gerçek olasılıksal değeri
    
    Raises:
        ValueError: p_now veya p_ref ≤ 0 ise
    """
    if p_now <= 0 or p_ref <= 0:
        raise ValueError(f"Fiyatlar pozitif olmalı: p_now={p_now}, p_ref={p_ref}")

    if seconds_remaining <= 0:
        return 1.0 if p_now > p_ref else 0.0

    annual_vol = ASSET_VOL.get(asset, 0.80)
    years = seconds_remaining / _SECONDS_PER_YEAR
    sigma_t = annual_vol * math.sqrt(years)

    d = math.log(p_now / p_ref)
    z = d / sigma_t

    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))
```

- [ ] **Adım 4: Testlerin yeşil olduğunu doğrula**

```bash
pytest tests/test_fair_value.py -v
```

Beklenti: `12 passed`

- [ ] **Adım 5: Commit**

```bash
git add data/fair_value.py tests/test_fair_value.py
git commit -m "feat(data): binary option fair value modeli (fair_yes)"
```

---

## Task A2: data/hl_candles.py — price_at_timestamp() + current_price()

**Files:**
- Modify: `data/hl_candles.py`
- Create: `tests/test_hl_candles.py`

Scout'un ihtiyacı:
1. `price_at_timestamp(asset, ts_ms)` → eventStartTime'daki HL fiyatı
2. `current_price(asset)` → şimdiki HL fiyatı

- [ ] **Adım 1: Failing testleri yaz**

```python
# tests/test_hl_candles.py
import asyncio, time, math, pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.hl_candles import fetch_candles, realized_move, price_at_timestamp, current_price

# --- Mevcut fonksiyonlar (regresyon) ---

def test_realized_move_empty():
    assert realized_move([], 5) is None

def test_realized_move_single_candle():
    assert realized_move([{"o": "100", "c": "100"}], 5) is None

def test_realized_move_calculates_pct():
    candles = [{"o": "100", "c": "102"}, {"o": "102", "c": "103"}]
    result = realized_move(candles, 5)
    assert result is not None
    assert abs(result - 3.0) < 0.01  # (103-100)/100*100 = 3%

def test_realized_move_negative():
    candles = [{"o": "100", "c": "99"}, {"o": "99", "c": "98"}]
    result = realized_move(candles, 5)
    assert result is not None
    assert result < 0

# --- Yeni fonksiyonlar (integration — gerçek API) ---

@pytest.mark.asyncio
async def test_current_price_btc_is_positive():
    price = await current_price("BTC")
    assert isinstance(price, float)
    assert price > 1_000  # BTC $1000'dan büyük olmalı

@pytest.mark.asyncio
async def test_current_price_eth_is_positive():
    price = await current_price("ETH")
    assert isinstance(price, float)
    assert price > 100  # ETH $100'dan büyük olmalı

@pytest.mark.asyncio
async def test_price_at_timestamp_5min_ago():
    """5 dakika önceki fiyat gerçek ve pozitif döner."""
    ts_ms = int(time.time() * 1000) - 5 * 60 * 1000
    price = await price_at_timestamp("BTC", ts_ms)
    assert isinstance(price, float)
    assert price > 1_000

@pytest.mark.asyncio
async def test_price_at_timestamp_close_to_current():
    """1 dakika önceki fiyat, şimdiki fiyattan çok uzak olmamalı (±%5)."""
    ts_ms = int(time.time() * 1000) - 60_000
    past = await price_at_timestamp("BTC", ts_ms)
    now = await current_price("BTC")
    pct_diff = abs(past - now) / now * 100
    assert pct_diff < 5.0  # 1 dakikada %5'ten fazla fark: API sorunu

@pytest.mark.asyncio
async def test_price_at_timestamp_too_old_raises():
    """7 günden eski timestamp için (1 dakika mumda veri olmayabilir) hata verir."""
    ts_ms = int(time.time() * 1000) - 8 * 24 * 60 * 60 * 1000
    with pytest.raises(ValueError, match="mum bulunamadı"):
        await price_at_timestamp("BTC", ts_ms)
```

- [ ] **Adım 2: Testlerin kırmızı olduğunu doğrula**

```bash
pytest tests/test_hl_candles.py -v 2>&1 | head -30
```

Beklenti: `ImportError: cannot import name 'price_at_timestamp'`

- [ ] **Adım 3: hl_candles.py'ye iki fonksiyon ekle**

Mevcut dosyanın sonuna, `main()` fonksiyonunun ÖNÜNE ekle:

```python
async def fetch_candles_range(asset: str, interval: str, start_ms: int, end_ms: int):
    """Belirli zaman aralığında mum çeker (ms epoch)."""
    payload = {
        "type": "candleSnapshot",
        "req": {"coin": asset, "interval": interval,
                "startTime": start_ms, "endTime": end_ms},
    }
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.post(INFO_URL, json=payload) as r:
            r.raise_for_status()
            return await r.json()


async def price_at_timestamp(asset: str, ts_ms: int) -> float:
    """
    ts_ms anındaki HL spot fiyatını döner (en yakın 1m mumun open fiyatı).
    Raises ValueError: o zaman için mum bulunamazsa.
    """
    start = ts_ms - 120_000  # 2dk önce
    end   = ts_ms + 120_000  # 2dk sonra
    candles = await fetch_candles_range(asset, "1m", start, end)
    if not candles:
        raise ValueError(f"{asset} için ts={ts_ms} civarında mum bulunamadı")
    closest = min(candles, key=lambda c: abs(int(c["t"]) - ts_ms))
    return float(closest["o"])


async def current_price(asset: str) -> float:
    """Şimdiki HL fiyatını döner (son 1m mumun close fiyatı)."""
    candles = await fetch_candles(asset, "1m", minutes_back=2)
    if not candles:
        raise ValueError(f"{asset} için canlı fiyat alınamadı")
    return float(candles[-1]["c"])
```

- [ ] **Adım 4: Testlerin yeşil olduğunu doğrula**

```bash
pytest tests/test_hl_candles.py -v
```

Beklenti: `9 passed`

- [ ] **Adım 5: Commit**

```bash
git add data/hl_candles.py tests/test_hl_candles.py
git commit -m "feat(data): price_at_timestamp ve current_price fonksiyonları"
```

---

## Task A3: data/shortterm.py — parse_market_window() ekle

**Files:**
- Modify: `data/shortterm.py`
- Create: `tests/test_shortterm.py`

Gamma API'den gelen `eventStartTime`, `endDate`, `bestBid`, `bestAsk`, `negRisk` alanlarını standart bir dict'e çıkaran helper.

- [ ] **Adım 1: Failing testleri yaz**

```python
# tests/test_shortterm.py
import asyncio, time, pytest, sys, os
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.shortterm import find_shortterm, parse_market_window, _parse

# --- _parse unit testleri ---

def test_parse_list():
    assert _parse(["0.6", "0.4"]) == ["0.6", "0.4"]

def test_parse_json_string():
    assert _parse('["0.6","0.4"]') == ["0.6", "0.4"]

def test_parse_invalid():
    assert _parse("invalid") is None

def test_parse_none():
    assert _parse(None) is None

# --- parse_market_window unit testleri ---

def test_parse_market_window_full():
    """Tüm alanlar dolu market dict'inden doğru çıkarım."""
    raw = {
        "eventStartTime": "2026-05-30T04:30:00Z",
        "endDate":        "2026-05-30T04:35:00Z",
        "bestBid":        0.48,
        "bestAsk":        0.52,
        "negRisk":        False,
        "question":       "Bitcoin Up or Down - May 30, 4:30AM-4:35AM ET",
        "slug":           "btc-updown-5m-1748571000",
    }
    w = parse_market_window(raw)
    assert w["start_ms"] == int(datetime(2026, 5, 30, 4, 30, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert w["end_ms"]   == int(datetime(2026, 5, 30, 4, 35, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert w["best_bid"] == 0.48
    assert w["best_ask"] == 0.52
    assert w["neg_risk"] is False

def test_parse_market_window_seconds_remaining_positive():
    """Gelecekteki bir market için seconds_remaining > 0."""
    future = datetime.now(timezone.utc).replace(microsecond=0)
    from datetime import timedelta
    end_dt = future + timedelta(minutes=5)
    raw = {
        "eventStartTime": future.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDate":        end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bestBid": 0.50, "bestAsk": 0.51, "negRisk": False,
    }
    w = parse_market_window(raw)
    assert w["seconds_remaining"] > 0

def test_parse_market_window_missing_event_start_returns_none():
    """eventStartTime yoksa None döner."""
    raw = {"endDate": "2026-05-30T04:35:00Z", "bestBid": 0.48, "bestAsk": 0.52}
    assert parse_market_window(raw) is None

def test_parse_market_window_missing_best_ask_returns_none():
    """bestAsk yoksa None döner."""
    raw = {
        "eventStartTime": "2026-05-30T04:30:00Z",
        "endDate":        "2026-05-30T04:35:00Z",
        "bestBid": 0.48,
    }
    assert parse_market_window(raw) is None

# --- Integration: gerçek API ---

@pytest.mark.asyncio
async def test_find_shortterm_returns_markets():
    markets = await find_shortterm()
    assert isinstance(markets, list)
    # Bazen piyasa kapalıdır; boş liste geçerli

@pytest.mark.asyncio
async def test_find_shortterm_markets_have_required_fields():
    """Dönen marketlerde eventStartTime ve bestAsk alanları var."""
    markets = await find_shortterm()
    for m in markets:
        # Tüm marketler bu alanları içermeli
        assert "eventStartTime" in m or "startDate" in m, f"Zaman alanı yok: {list(m.keys())}"
        # bestAsk olmayabilir (market kapalı/resolved), sadece varsa kontrol et
        if m.get("bestAsk"):
            assert 0.0 < float(m["bestAsk"]) < 1.0
```

- [ ] **Adım 2: Testlerin kırmızı olduğunu doğrula**

```bash
pytest tests/test_shortterm.py -v 2>&1 | head -30
```

Beklenti: `ImportError: cannot import name 'parse_market_window'`

- [ ] **Adım 3: parse_market_window() fonksiyonunu shortterm.py'ye ekle**

Mevcut `find_shortterm` fonksiyonunun ÖNÜNE ekle:

```python
from datetime import datetime, timezone, timedelta


def parse_market_window(m: dict):
    """
    Ham Gamma market dict'inden scout'un ihtiyacı olan alanları çıkarır.
    Returns dict veya None (zorunlu alan eksikse).
    
    Dönen dict anahtarları:
      start_ms          : eventStartTime (ms epoch)
      end_ms            : endDate (ms epoch)  
      seconds_remaining : endDate - now (float)
      best_bid          : YES token bestBid (float)
      best_ask          : YES token bestAsk (float)
      neg_risk          : bool
    """
    try:
        start_str = m.get("eventStartTime") or m.get("startDate")
        end_str   = m.get("endDate")
        best_ask  = m.get("bestAsk")
        best_bid  = m.get("bestBid")

        if not start_str or not end_str or best_ask is None or best_bid is None:
            return None

        def _parse_dt(s):
            s = s.rstrip("Z")
            return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)

        start_dt = _parse_dt(start_str)
        end_dt   = _parse_dt(end_str)
        now      = datetime.now(timezone.utc)

        return {
            "start_ms":          int(start_dt.timestamp() * 1000),
            "end_ms":            int(end_dt.timestamp() * 1000),
            "seconds_remaining": (end_dt - now).total_seconds(),
            "best_bid":          float(best_bid),
            "best_ask":          float(best_ask),
            "neg_risk":          bool(m.get("negRisk", False)),
        }
    except (ValueError, TypeError, AttributeError):
        return None
```

- [ ] **Adım 4: Testlerin yeşil olduğunu doğrula**

```bash
pytest tests/test_shortterm.py -v
```

Beklenti: `11 passed`

- [ ] **Adım 5: Commit**

```bash
git add data/shortterm.py tests/test_shortterm.py
git commit -m "feat(data): parse_market_window - eventStartTime/bestAsk/bestBid çıkarımı"
```

---

## Task B1: council/scout.py — Tam Rewrite (Fair Value Modeli)

**Files:**
- Rewrite: `council/scout.py`
- Create: `tests/test_scout.py`

**Yeni edge mantığı:**
```
fair = fair_yes(cur_price, ref_price, seconds_remaining, asset)

YES ucuz mu?  → fair - best_ask  > MIN_EDGE_PCT  → YES AL
NO ucuz mu?   → best_bid - fair  > MIN_EDGE_PCT  → NO AL
  (NO'yu satın almak = 1-best_bid ödeyip NO almak.
   NO'nun fair değeri = 1-fair.
   Edge = (1-fair) - (1-best_bid) = best_bid - fair)
```

- [ ] **Adım 1: Failing testleri yaz**

```python
# tests/test_scout.py
import asyncio, pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Scout'u import et (henüz yok)
from council.scout import scan_edges, _asset_of, _edge_signal

# --- Unit testler ---

def test_asset_of_bitcoin():
    assert _asset_of("Bitcoin Up or Down") == "BTC"

def test_asset_of_ethereum():
    assert _asset_of("Ethereum Up or Down") == "ETH"

def test_asset_of_btc_short():
    assert _asset_of("BTC Up or Down") == "BTC"

def test_asset_of_unknown():
    assert _asset_of("Dogecoin Up or Down") is None

def test_edge_signal_yes_cheap():
    """fair > ask → YES al."""
    result = _edge_signal(fair=0.70, best_ask=0.40, best_bid=0.39)
    assert result["action"] == "YES"
    assert abs(result["edge"] - 0.30) < 1e-6

def test_edge_signal_no_cheap():
    """fair < bid → NO al."""
    result = _edge_signal(fair=0.30, best_ask=0.62, best_bid=0.60)
    assert result["action"] == "NO"
    assert abs(result["edge"] - 0.30) < 1e-6

def test_edge_signal_no_edge():
    """fair ≈ fiyat → edge yok → None."""
    result = _edge_signal(fair=0.50, best_ask=0.51, best_bid=0.49)
    assert result is None

def test_edge_signal_min_threshold():
    """MIN_EDGE_PCT eşiği altında → None."""
    # MIN_EDGE_PCT = 0.08; edge = 0.07 → yok
    result = _edge_signal(fair=0.57, best_ask=0.50, best_bid=0.49)
    assert result is None  # 0.57 - 0.50 = 0.07 < 0.08

# --- Integration: gerçek API ---

@pytest.mark.asyncio
async def test_scan_edges_returns_list():
    findings = await scan_edges()
    assert isinstance(findings, list)

@pytest.mark.asyncio
async def test_scan_edges_findings_have_required_fields():
    """Her bulgu zorunlu alanları içeriyor."""
    findings = await scan_edges()
    required = {"question", "asset", "fair_value", "best_ask", "best_bid",
                "edge", "action", "ref_price", "cur_price", "seconds_remaining"}
    for f in findings:
        missing = required - set(f.keys())
        assert not missing, f"Eksik alanlar: {missing} in {f}"

@pytest.mark.asyncio
async def test_scan_edges_edge_above_min():
    """Dönen tüm bulgular MIN_EDGE_PCT üstünde."""
    findings = await scan_edges()
    for f in findings:
        assert f["edge"] >= config.MIN_EDGE_PCT, \
            f"Eşik altı bulgu: edge={f['edge']:.3f} < {config.MIN_EDGE_PCT}"

@pytest.mark.asyncio
async def test_scan_edges_neg_risk_filtered():
    """negRisk=True marketler sonuçlarda olmamalı."""
    findings = await scan_edges()
    for f in findings:
        assert not f.get("neg_risk", False), "negRisk=True market geçmiş!"

@pytest.mark.asyncio
async def test_scan_edges_time_filter():
    """60 saniyeden az kalan marketler olmamalı."""
    findings = await scan_edges()
    for f in findings:
        assert f["seconds_remaining"] >= 60, \
            f"Çok az süre kalmış market: {f['seconds_remaining']:.0f}s"

@pytest.mark.asyncio
async def test_scan_edges_fair_value_in_range():
    """fair_value her zaman [0,1] arasında."""
    findings = await scan_edges()
    for f in findings:
        assert 0.0 <= f["fair_value"] <= 1.0
```

- [ ] **Adım 2: Testlerin kırmızı olduğunu doğrula**

```bash
pytest tests/test_scout.py -v 2>&1 | head -30
```

Beklenti: `ImportError: cannot import name '_edge_signal'`

- [ ] **Adım 3: council/scout.py'yi yeniden yaz**

```python
"""
council/scout.py — KATMAN 1: Keşif Ajanı.

Edge tanımı (doğru):
  fair_yes = P(fiyat > referans | şimdiki fiyat, kalan süre)  [Black-Scholes binary]
  YES ucuz → fair_yes - best_ask > MIN_EDGE_PCT
  NO ucuz  → best_bid - fair_yes > MIN_EDGE_PCT (= fair_no - best_no_ask)

Referans fiyat: PM penceresinin eventStartTime'ındaki HL fiyatı.
PM fiyatı: Gamma CLOB'dan bestAsk / bestBid (gerçek zamanlı).
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.shortterm import find_shortterm, parse_market_window
from data.hl_candles import price_at_timestamp, current_price
from data.fair_value import fair_yes
import config

MIN_SECONDS = 60   # Çözüme bu kadar saniyeden az kalmışsa atla


def _asset_of(question: str) -> str | None:
    q = (question or "").lower()
    if "bitcoin" in q or " btc" in q:
        return "BTC"
    if "ethereum" in q or " eth" in q:
        return "ETH"
    if "solana" in q or " sol" in q:
        return "SOL"
    if "ripple" in q or " xrp" in q:
        return "XRP"
    return None


def _edge_signal(fair: float, best_ask: float, best_bid: float) -> dict | None:
    """
    fair: fair_yes değeri [0,1]
    best_ask: YES almak için ödeyeceğimiz fiyat
    best_bid: YES satmak için alacağımız fiyat (= NO almak için ödeyeceğimiz 1-best_bid)
    
    Returns None (edge yok) veya {"action": "YES"|"NO", "edge": float}
    """
    yes_edge = fair - best_ask          # YES almak
    no_edge  = best_bid - fair          # NO almak (fair_no = 1-fair, no_ask = 1-best_bid)

    if yes_edge >= config.MIN_EDGE_PCT:
        return {"action": "YES", "edge": yes_edge}
    if no_edge >= config.MIN_EDGE_PCT:
        return {"action": "NO", "edge": no_edge}
    return None


async def _process_market(m: dict) -> dict | None:
    """Tek marketi değerlendirir. Edge yoksa veya hata olursa None."""
    asset = _asset_of(m.get("question", ""))
    if asset is None:
        return None

    window = parse_market_window(m)
    if window is None:
        return None

    if window["neg_risk"]:
        return None

    if window["seconds_remaining"] < MIN_SECONDS:
        return None

    if window["best_ask"] <= 0 or window["best_bid"] <= 0:
        return None

    try:
        ref_price = await price_at_timestamp(asset, window["start_ms"])
        cur       = await current_price(asset)
    except (ValueError, Exception):
        return None

    fair = fair_yes(cur, ref_price, window["seconds_remaining"], asset)
    signal = _edge_signal(fair, window["best_ask"], window["best_bid"])
    if signal is None:
        return None

    return {
        "question":          (m.get("question") or "?")[:60],
        "asset":             asset,
        "fair_value":        round(fair, 4),
        "ref_price":         ref_price,
        "cur_price":         cur,
        "best_ask":          window["best_ask"],
        "best_bid":          window["best_bid"],
        "seconds_remaining": window["seconds_remaining"],
        "edge":              round(signal["edge"], 4),
        "action":            signal["action"],
        "neg_risk":          window["neg_risk"],
    }


async def scan_edges() -> list[dict]:
    """Tüm kısa vadeli marketleri tarar, gerçek edge olanları döner."""
    markets = await find_shortterm()
    if not markets:
        return []

    tasks = [_process_market(m) for m in markets]
    results = await asyncio.gather(*tasks)

    findings = [r for r in results if r is not None]
    findings.sort(key=lambda x: x["edge"], reverse=True)
    return findings


async def main():
    print("=" * 70)
    print("SCOUT — gerçek fair value mispricing taraması (order YOK)")
    print(f"Min edge: {config.MIN_EDGE_PCT:.0%} | Min kalan süre: {MIN_SECONDS}s")
    print("=" * 70)

    findings = await scan_edges()
    if not findings:
        print("\nGerçek mispricing yok.")
        print("(Piyasa sakin veya PM fair value'yu zaten yansıtıyor.)")
        return

    for f in findings:
        flag = "  >>> EŞİK ÜSTÜ" if f["edge"] >= config.MIN_EDGE_PCT else ""
        print(f"\n{f['question']}  [{f['asset']}]")
        print(f"  Referans fiyat (pencere açılışı) : ${f['ref_price']:,.2f}")
        print(f"  Şimdiki fiyat (HL live)          : ${f['cur_price']:,.2f}")
        print(f"  Fair YES değeri                  : {f['fair_value']:.3f}")
        print(f"  PM bestAsk / bestBid              : {f['best_ask']:.3f} / {f['best_bid']:.3f}")
        print(f"  EDGE                             : {f['edge']:+.3f}{flag}")
        print(f"  Kalan süre                       : {f['seconds_remaining']:.0f}s")
        print(f"  Aksiyon                          : {f['action']} AL")

    n = len(findings)
    print("\n" + "=" * 70)
    print(f"{n} eşik üstü bulgu. Order verilmedi (DRY_RUN={config.DRY_RUN}).")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Adım 4: Testlerin yeşil olduğunu doğrula**

```bash
pytest tests/test_scout.py -v
```

Beklenti: `13 passed` (integration testler gerçek API ile çalışır, piyasa kapalıysa 0 bulgu geçerli)

- [ ] **Adım 5: Scout'u manuel çalıştır ve çıktıyı gözle doğrula**

```bash
cd /root/mispricing_agent && source venv/bin/activate
python -m council.scout
```

Kontrol et:
- Referans fiyat mantıklı mı? (BTC $90k-$120k arası)
- Fair value 0.50 civarı mı? (piyasa açılışına yakınsa)
- Edge formülü doğru yönde mi? (YES al diyorsa fair > ask)

- [ ] **Adım 6: Tüm testler yeşil**

```bash
pytest tests/ -v
```

Beklenti: `33+ passed, 0 failed`

- [ ] **Adım 7: Final commit**

```bash
git add council/scout.py tests/test_scout.py
git commit -m "feat(scout): fair value modeli ile tam rewrite - 0.50 sabit referans kaldırıldı"
```

---

## Verification Checklist (Tamamlama Öncesi)

Tüm tasklar bitmeden `superpowers:verification-before-completion` skill'ini invoke et:

- [ ] `pytest tests/ -v` → 0 failed
- [ ] `python -m council.scout` → gerçek çıktı, mantıklı sayılar
- [ ] `python -m data.fair_value` → (test modülü yok, import hatasız)
- [ ] `python -m data.hl_candles` → BTC/ETH fiyatları çıkıyor
- [ ] Scout'un bulduğu fair_value değerleri mantıklı aralıkta (0.05-0.95)
- [ ] negRisk filtresi çalışıyor (çıktıda negRisk market yok)
- [ ] seconds_remaining filtresi çalışıyor (60s altı market yok)

---

## Sıradaki Aşama (Bu Plandan Sonra)

Bu plan bittikten sonra Konsey Katman 2: **Verifier** yazılacak:
- Scout'un bulduğu fiyatı **bağımsız** bir API çağrısıyla teyit eder
- Fair value + referans fiyatı tekrar hesaplar
- Uyuşmazlık → `HALT_ON_API_MISMATCH` devreye girer
