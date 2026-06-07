# Bot Darboğaz Giderme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bot frekansını ve giriş kalitesini aynı anda artır: dinamik realized volatility + gate kalibrasyonu + hız ayarları.

**Architecture:** 7 bağımsız değişiklik; Task 1→2→3 sıralı (bağımlılık zinciri), Task 4-7 bağımsız paralel yapılabilir. Her task TDD: önce kırmızı test, sonra yeşil kod, sonra commit.

**Tech Stack:** Python 3.11, asyncio, pytest, math (stdlib — yeni bağımlılık yok)

---

## Dosya Haritası

| Dosya | Değişiklik |
|-------|-----------|
| `data/hl_candles.py` | `calculate_realized_volatility()` ekle |
| `data/fair_value.py` | `current_volatility` parametresi ekle |
| `council/scout.py` | vol cache + market cache + MAX_ENTRY_PRICE 0.65→0.75 |
| `council/gate.py` | EDGE_MAX 0.08→0.06 |
| `position/manager.py` | MIN_HOLD_SECS 60→30 |
| `data/ws_prices.py` | STALE_SECS 60→15 |
| `main_loop.py` | SCAN_INTERVAL_SECS 15→7 |
| `tests/test_hl_candles.py` | 5 yeni test |
| `tests/test_fair_value.py` | 1 yeni test |
| `tests/test_gate.py` | 1 yeni test |
| `tests/test_position.py` | 1 güncelleme + 1 yeni test |

---

### Task 1: `calculate_realized_volatility` — hl_candles.py

**Files:**
- Modify: `data/hl_candles.py`
- Test: `tests/test_hl_candles.py`

- [ ] **Step 1: Kırmızı testleri yaz** (`tests/test_hl_candles.py` altına ekle)

```python
import math as _math

def test_calculate_realized_vol_empty_returns_fallback():
    from data.hl_candles import calculate_realized_volatility
    assert calculate_realized_volatility([]) == 0.80

def test_calculate_realized_vol_single_candle_returns_fallback():
    from data.hl_candles import calculate_realized_volatility
    assert calculate_realized_volatility([{"c": "100"}]) == 0.80

def test_calculate_realized_vol_flat_market_clamped_to_min():
    from data.hl_candles import calculate_realized_volatility
    candles = [{"c": "100.0"} for _ in range(10)]
    vol = calculate_realized_volatility(candles)
    assert vol == 0.30  # std_dev=0 → annualized=0 → clamp 0.30

def test_calculate_realized_vol_extreme_moves_clamped_to_max():
    from data.hl_candles import calculate_realized_volatility
    # 100→200→100→200: log_returns=[0.693,-0.693,0.693] → annualized >> 3.00
    candles = [{"c": "100"}, {"c": "200"}, {"c": "100"}, {"c": "200"}]
    assert calculate_realized_volatility(candles) == 3.00

def test_calculate_realized_vol_in_valid_range():
    from data.hl_candles import calculate_realized_volatility
    # Gerçekçi BTC hareketi: ±%0.1/mum
    import random; random.seed(42)
    px = 100_000.0
    candles = []
    for _ in range(60):
        px *= (1 + random.gauss(0, 0.001))
        candles.append({"c": str(px)})
    vol = calculate_realized_volatility(candles)
    assert 0.30 <= vol <= 3.00
    assert vol != 0.80  # gerçek hesap, fallback değil
```

- [ ] **Step 2: Testleri çalıştır, FAIL olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_hl_candles.py::test_calculate_realized_vol_empty_returns_fallback -v 2>&1 | tail -5
```
Beklenen: `ImportError: cannot import name 'calculate_realized_volatility'`

- [ ] **Step 3: Fonksiyonu `data/hl_candles.py`'a ekle** (dosyanın en üstüne `import math` ekle, `realized_move` fonksiyonunun hemen altına):

```python
import math  # dosyanın üstüne ekle


def calculate_realized_volatility(candles: list[dict]) -> float:
    """
    Son N dakikanın 1m mumlarından yıllıklandırılmış realized volatilite.
    Formül: stdev(log_returns) * sqrt(525_600)
    Guardrail: [0.30, 3.00] — aşırı spike ve sıfır değerini engeller.
    Yeterli veri yoksa 0.80 (BTC ort.) döner.
    """
    if not candles or len(candles) < 2:
        return 0.80

    returns = []
    for i in range(1, len(candles)):
        prev = float(candles[i - 1]["c"])
        curr = float(candles[i]["c"])
        if prev > 0 and curr > 0:
            returns.append(math.log(curr / prev))

    if len(returns) < 2:
        return 0.80

    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = math.sqrt(variance)
    annualized = std_dev * math.sqrt(525_600)   # 365*24*60 = 525 600 dakika/yıl
    return max(0.30, min(annualized, 3.00))
```

- [ ] **Step 4: Testleri çalıştır, PASS olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_hl_candles.py -v 2>&1 | tail -10
```
Beklenen: 5 yeni test dahil hepsi PASS.

- [ ] **Step 5: Commit**

```bash
cd /root/mispricing_agent && git add data/hl_candles.py tests/test_hl_candles.py && git commit -m "feat(hl_candles): calculate_realized_volatility — dinamik yıllık vol (stdev log-returns)"
```

---

### Task 2: `fair_yes` dinamik volatilite parametresi — fair_value.py

**Files:**
- Modify: `data/fair_value.py`
- Test: `tests/test_fair_value.py`

- [ ] **Step 1: Kırmızı test yaz**

```python
def test_fair_yes_uses_current_volatility_when_provided():
    """current_volatility verildiğinde ASSET_VOL kullanılmaz."""
    # p_now 1 birim üstünde, 15 dk kaldı
    # vol=0.001 (neredeyse sıfır) → sigma_t ≈ 0 → sonuç 1.0'e yakın
    # BTC normal vol=0.80 → sigma_t büyük → sonuç 0.5'e yakın
    low_vol = fair_yes(100_001.0, 100_000.0, 900.0, "BTC", current_volatility=0.001)
    normal  = fair_yes(100_001.0, 100_000.0, 900.0, "BTC")
    assert low_vol > 0.90, f"Düşük vol → kesinlik yüksek, beklenen >0.90, got {low_vol:.4f}"
    assert abs(normal - 0.50) < 0.01, f"Normal vol + az üstünde → 0.50'ye yakın, got {normal:.4f}"
```

- [ ] **Step 2: Çalıştır, FAIL olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_fair_value.py::test_fair_yes_uses_current_volatility_when_provided -v 2>&1 | tail -5
```

- [ ] **Step 3: `data/fair_value.py`'ı güncelle** — sadece imza ve vol seçimi değişir:

```python
def fair_yes(p_now: float, p_ref: float, seconds_remaining: float,
             asset: str = "BTC", current_volatility: float | None = None) -> float:
    """
    P(asset_price > p_ref at resolution | current_price = p_now)

    Args:
        p_now: Şimdiki fiyat (HL live)
        p_ref: Referans fiyat (PM penceresinin açılışında HL fiyatı)
        seconds_remaining: Çözüme kadar kalan saniye
        asset: "BTC", "ETH", "SOL", "XRP" — current_volatility None ise kullanılır
        current_volatility: Dinamik realized vol (hl_candles'dan). Verilirse ASSET_VOL'u geçersiz kılar.

    Returns:
        [0.0, 1.0] arası float — YES token'ın gerçek olasılıksal değeri
    """
    if p_now <= 0 or p_ref <= 0:
        raise ValueError(f"Fiyatlar pozitif olmalı: p_now={p_now}, p_ref={p_ref}")

    if seconds_remaining <= 0:
        return 1.0 if p_now > p_ref else 0.0

    annual_vol = current_volatility if current_volatility is not None else ASSET_VOL.get(asset, 0.80)
    years = seconds_remaining / _SECONDS_PER_YEAR
    sigma_t = annual_vol * math.sqrt(years)

    if sigma_t < 1e-10:
        return 1.0 if p_now > p_ref else 0.0

    d = math.log(p_now / p_ref)
    z = d / sigma_t
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))
```

- [ ] **Step 4: Testleri çalıştır**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_fair_value.py -v 2>&1 | tail -10
```
Beklenen: Tüm eski testler + yeni test PASS.

- [ ] **Step 5: Commit**

```bash
cd /root/mispricing_agent && git add data/fair_value.py tests/test_fair_value.py && git commit -m "feat(fair_value): current_volatility parametresi — dinamik vol desteği, ASSET_VOL fallback korundu"
```

---

### Task 3: Scout — vol cache + market cache + MAX_ENTRY_PRICE 0.75

**Files:**
- Modify: `council/scout.py`
- Test: `tests/test_scout.py` (mevcut testler regresyon kontrolü)

- [ ] **Step 1: `council/scout.py`'ı güncelle**

Dosyanın başına şunu ekle (mevcut importların altına):

```python
import time
```

`from data.fair_value import fair_yes` satırını güncelle:

```python
from data.fair_value import fair_yes, ASSET_VOL
from data.hl_candles import price_at_timestamp, current_price, fetch_candles, calculate_realized_volatility
```

`MIN_SECONDS = 180` satırından hemen sonra sabitler ekle:

```python
MAX_ENTRY_PRICE  = 0.75   # 0.65→0.75: reversal koruması gevşetildi, daha fazla işlem
MARKET_CACHE_TTL_SECS = 60.0    # market listesi 60s cache — REST API yükünü azaltır
VOL_CACHE_TTL_SECS    = 300.0   # realized vol 5 dk cache — 4 API çağrısı/5dk
```

Modül düzey cache değişkenleri ekle (`CONVICTION_MIN = 0.58` satırının hemen altına):

```python
_markets_cache:   list[dict] = []
_markets_cache_ts: float     = 0.0
_vol_cache:       dict[str, float] = {}
_vol_cache_ts:    float            = 0.0
```

Yeni `_get_all_vols()` fonksiyonunu `_asset_of()` fonksiyonunun hemen öncesine ekle:

```python
async def _get_all_vols() -> dict[str, float]:
    """Her tracked asset için realized vol çeker — 5 dk cache ile."""
    global _vol_cache, _vol_cache_ts
    now = time.time()
    if (now - _vol_cache_ts) < VOL_CACHE_TTL_SECS and _vol_cache:
        return _vol_cache

    async def _fetch_one(asset: str) -> tuple[str, float]:
        try:
            candles = await fetch_candles(asset, "1m", 60)
            return asset, calculate_realized_volatility(candles)
        except Exception:
            return asset, ASSET_VOL.get(asset, 0.80)

    pairs = await asyncio.gather(*[_fetch_one(a) for a in config.TRACKED_ASSETS])
    _vol_cache = dict(pairs)
    _vol_cache_ts = now
    return _vol_cache
```

`_process_market` imzasını güncelle (asset_vols ekle):

```python
async def _process_market(m: dict, asset_vols: dict[str, float]) -> dict | None:
```

`_process_market` içinde `fair = fair_yes(...)` satırını güncelle:

```python
    live_vol = asset_vols.get(asset, 0.80)
    fair = fair_yes(cur, ref_price, window["seconds_remaining"], asset, live_vol)
```

`scan_edges()` fonksiyonunu güncelle:

```python
async def scan_edges() -> list[dict]:
    """Tüm kısa vadeli marketleri tarar, gerçek edge olanları döner.
    Market listesi 60s, vol hesabı 5 dk cache'li — REST API korunur."""
    global _markets_cache, _markets_cache_ts
    now = time.time()
    if (now - _markets_cache_ts) > MARKET_CACHE_TTL_SECS or not _markets_cache:
        fresh = await find_shortterm()
        _markets_cache = fresh or []
        _markets_cache_ts = now

    if not _markets_cache:
        return []

    asset_vols = await _get_all_vols()
    tasks = [_process_market(m, asset_vols) for m in _markets_cache]
    results = await asyncio.gather(*tasks)

    findings = [r for r in results if r is not None]
    findings.sort(key=lambda x: x["edge"], reverse=True)
    return findings
```

- [ ] **Step 2: Mevcut testleri çalıştır (regresyon)**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_scout.py -v 2>&1 | tail -15
```
Beklenen: Tüm mevcut `_asset_of` ve `_edge_signal` testleri PASS.

- [ ] **Step 3: Commit**

```bash
cd /root/mispricing_agent && git add council/scout.py && git commit -m "feat(scout): dinamik vol cache + market list cache + MAX_ENTRY_PRICE 0.65→0.75"
```

---

### Task 4: Gate EDGE_MAX 0.06

**Files:**
- Modify: `council/gate.py` (sadece 1 satır)
- Test: `tests/test_gate.py`

- [ ] **Step 1: Kırmızı test yaz** (`tests/test_gate.py` sonuna ekle):

```python
def test_confidence_score_edge_at_7pct_now_max_points():
    """EDGE_MAX=0.06 sonrası %7 edge tam puan (40) veriyor — eskiden kısmi veriyordu."""
    from council.gate import EDGE_MAX
    assert EDGE_MAX == 0.06, f"EDGE_MAX beklenen 0.06, got {EDGE_MAX}"
    # edge=0.07 > EDGE_MAX=0.06 → edge_s=1.0 → 40 puan
    # + liq=$1000 → 30 + time=400s → 15 + spread=0.01 → 15 = 100
    score = _confidence_score(_redteam(0.07, 1000.0, 0.01), _verification(400))
    assert score == 100.0, f"7% edge + max liq/time/spread → 100 bekleniyor, got {score}"
```

- [ ] **Step 2: Çalıştır, FAIL olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_gate.py::test_confidence_score_edge_at_7pct_now_max_points -v 2>&1 | tail -5
```

- [ ] **Step 3: `council/gate.py`'ı değiştir** — tek satır:

```python
EDGE_MAX    = 0.06   # DÜZELTİLDİ: 0.08→0.06. %6 artık tam puan — Polymarket binary için gerçekçi üst sınır
```

- [ ] **Step 4: Testleri çalıştır**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_gate.py -v 2>&1 | tail -15
```
Beklenen: Tüm eski + yeni test PASS.

- [ ] **Step 5: Commit**

```bash
cd /root/mispricing_agent && git add council/gate.py tests/test_gate.py && git commit -m "feat(gate): EDGE_MAX 0.08→0.06 — %6 edge artık tam puan, gerçekçi Polymarket üst sınırı"
```

---

### Task 5: MIN_HOLD_SECS 60→30

**Files:**
- Modify: `position/manager.py` (1 satır)
- Test: `tests/test_position.py`

- [ ] **Step 1: Kırmızı test yaz** (`tests/test_position.py` sonuna ekle):

```python
def test_check_exit_stop_loss_fires_between_30_and_60_secs():
    """45. saniyede (30s < 45s < 60s) stop_loss artık çalışır (MIN_HOLD_SECS=30)."""
    pos = _position(action="YES", held_minutes=0)
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=45)).isoformat()
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.27, time_to_expiry_secs=900)
    assert result == "stop_loss_hit", (
        "45s > MIN_HOLD_SECS(30) → stop tetiklenmeli (eski 60s kuralıyla çalışmazdı)"
    )
```

- [ ] **Step 2: Çalıştır, FAIL olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_position.py::test_check_exit_stop_loss_fires_between_30_and_60_secs -v 2>&1 | tail -5
```
Beklenen: `AssertionError: 45s > MIN_HOLD_SECS(30) → stop tetiklenmeli`

- [ ] **Step 3: `position/manager.py` güncelle** — 1 satır:

```python
MIN_HOLD_SECS = 30  # 60→30: anlık gürültü koruması korunur, gereksiz 60s bekleme kaldırıldı
```

Mevcut docstring'i de güncelle:
```python
def test_check_exit_no_stop_loss_before_min_hold():
    """İlk 30s içinde stop_loss çalışmaz — anlık ters dönüş gürültüsü filtresi."""
```

- [ ] **Step 4: Testleri çalıştır**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_position.py -v 2>&1 | tail -15
```
Beklenen: Tüm testler PASS.

- [ ] **Step 5: Commit**

```bash
cd /root/mispricing_agent && git add position/manager.py tests/test_position.py && git commit -m "feat(manager): MIN_HOLD_SECS 60→30 — gürültü koruması korunur, 30-60s arası stop artık çalışır"
```

---

### Task 6: STALE_SECS 60→15

**Files:**
- Modify: `data/ws_prices.py` (1 satır)
- Test: mevcut `test_stale_cache_returns_none` zaten `ws.STALE_SECS` kullandığı için otomatik güncellenir

- [ ] **Step 1: `data/ws_prices.py`'ı değiştir**:

```python
STALE_SECS    = 15   # 60→15: Gamma fallback kaldırıldı → stale WS artık CLOB REST'e düşüyor
                     # 15s yeterli taze; >15s ise CLOB REST çağrısı kabul edilebilir maliyette
```

- [ ] **Step 2: Testleri çalıştır**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_ws_prices.py -v 2>&1 | tail -10
```
Beklenen: Tüm testler PASS (`test_stale_cache_returns_none` `ws.STALE_SECS+5=20` kullanır → hâlâ doğru çalışır).

- [ ] **Step 3: Commit**

```bash
cd /root/mispricing_agent && git add data/ws_prices.py && git commit -m "feat(ws_prices): STALE_SECS 60→15 — taze fiyat, CLOB REST fallback güvenli"
```

---

### Task 7: SCAN_INTERVAL 15→7

**Files:**
- Modify: `main_loop.py` (1 satır)

- [ ] **Step 1: `main_loop.py`'ı değiştir**:

```python
SCAN_INTERVAL_SECS = 7   # 15→7: market cache sayesinde REST API'yi patlatmaz (cache 60s)
```

- [ ] **Step 2: Testleri çalıştır**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_main_loop.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Tam test paketi**

```bash
cd /root/mispricing_agent && python -m pytest tests/ -x -q 2>&1 | tail -10
```
Beklenen: 356+ PASS, 0 FAIL.

- [ ] **Step 4: Commit**

```bash
cd /root/mispricing_agent && git add main_loop.py && git commit -m "feat(main_loop): SCAN_INTERVAL 15→7 — market cache ile REST API güvenli, 2x frekans"
```

---

## Son Kontrol

```bash
cd /root/mispricing_agent && python -m pytest tests/ -q 2>&1 | tail -5
```

## Restart Checklist (kullanıcı aksiyonu)

1. `config.py`'de: `CONFIDENCE_THRESHOLD = 50` (75'ten)
2. Bot başlat: `PYTHONUNBUFFERED=1 python main_loop.py`
3. İlk 30 dakika gate loglarını izle: confidence_score artık 50-90 aralığında görünmeli
4. Vol değerlerini kontrol et: BTC için 0.40-1.20 bekleniyor (sakin gün=0.40, volatil=1.20)
