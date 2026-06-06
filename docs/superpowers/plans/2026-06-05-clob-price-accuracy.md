# CLOB Price Accuracy Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polymarket CLOB API docs analizi sonucu bulunan 3 kritik fiyat yanlışlığını düzelt: (1) YES_bid REST fallback'i gerçek bid endpoint'ini kullan, (2) NO işlemlerde YES_ask yerine gerçek NO_ask kullan, (3) RedTeam'e orderbook derinlik/spread veto ekle.

**Architecture:** Her fix birbirinden bağımsız kütüphane katmanında: `data/clob_price.py` (yardımcı), `council/scout.py` (fiyat çekme/edge), `council/redteam.py` (veto mantığı). Bağımlılık sırası: Task 1 → Task 2 → Task 3. Her task kendi testleriyle tamamlanır.

**Tech Stack:** Python 3.12, aiohttp, pytest-asyncio, unittest.mock

---

## Mevcut Durumun Özeti (Context)

Polymarket CLOB API'sinde:
- `GET /price?token_id=<id>&side=SELL` → **best bid** direkt döner (SELL = seni n alacağı fiyat)
- `GET /price?token_id=<id>&side=BUY` → **best ask** direkt döner (BUY = ödeyeceğin fiyat)
- `GET /book?token_id=<id>` → **tam orderbook** (bids/asks + size, min_order_size, last_trade_price)
- NO token (ör. `no_token_id`) **bağımsız bir orderbook**'a sahip — YES tokendan ayrı

**3 Kritik Bug:**

1. **YES_bid fallback yanlış** (`scout.py:103`): WS stale olduğunda `yes_bid = clob_ask` (ask fiyatı kullanılıyor). Gerçekte `GET /price?side=SELL` çağrılmalı.

2. **NO edge için yanlış fiyat** (`scout.py:104`, `redteam.py:42`): NO işlemde ödenen fiyat `NO_ask`. Ama kod `YES_ask` kullanıyor. Binary markette `YES_ask + NO_ask ≥ 1.0` (spread nedeniyle), yani `YES_ask ≠ NO_ask`. Mevcut formül NO edge'i sistematik olarak aşırı tahmin ediyor.

3. **Derinlik kontrolü yok** (`redteam.py`): $1.25 FAK order için `asks[0].size` hiç kontrol edilmiyor. İnce markette partial fill riski var. `/book` endpoint `size` veriyor.

**Önemli:** `data/clob_price.py`'daki `get_clob_price(token_id, side="SELL")` zaten çalışıyor — sadece scout doğru çağırmıyor.

---

## Dosya Haritası

| Dosya | İşlem | Neden |
|-------|-------|-------|
| `data/clob_price.py` | Değiştir | `get_book(token_id)` ekle |
| `council/scout.py` | Değiştir | YES_bid fallback + NO_ask real edge |
| `council/redteam.py` | Değiştir | `_fee_adjusted_edge` + book depth veto |
| `tests/test_clob_price.py` | Değiştir | `get_book` testleri ekle |
| `tests/test_scout.py` | Değiştir | YES_bid + NO_ask testleri ekle |
| `tests/test_redteam.py` | Değiştir | NO fee + depth veto testleri ekle |

---

## Task 1: `get_book()` helper — `data/clob_price.py`

**Context:** `data/clob_price.py` mevcut; sadece `get_clob_price` var. `get_book` yoktur. Bu fonksiyon Task 2 ve 3 için temel.

**API Response Formatı (docs'tan):**
```json
{
  "market": "0xabc...",
  "asset_id": "0xtok...",
  "bids": [{"price": "0.44", "size": "200"}, {"price": "0.43", "size": "100"}],
  "asks": [{"price": "0.46", "size": "150"}, {"price": "0.47", "size": "250"}],
  "min_order_size": "1",
  "tick_size": "0.01",
  "neg_risk": false,
  "last_trade_price": "0.45"
}
```
`bids`: fiyata göre azalan (bids[0] = en iyi bid). `asks`: fiyata göre artan (asks[0] = en iyi ask).

**Files:**
- Modify: `data/clob_price.py`
- Modify: `tests/test_clob_price.py`

---

- [ ] **Step 1: Failing testleri yaz** — `tests/test_clob_price.py` sonuna ekle

Dosya başına `from data.clob_price import get_clob_price` import satırı zaten var. Şunu ekle:
```python
from data.clob_price import get_clob_price, get_book
```

Sonra 4 test ekle:
```python
@pytest.mark.asyncio
async def test_get_book_returns_dict_with_bids_and_asks():
    """Başarılı yanıtta bids/asks içeren dict döner."""
    book_data = {
        "market": "0xabc",
        "asset_id": "tok-yes",
        "timestamp": "1234567890",
        "hash": "abc",
        "bids": [{"price": "0.44", "size": "200"}, {"price": "0.43", "size": "100"}],
        "asks": [{"price": "0.46", "size": "150"}, {"price": "0.47", "size": "250"}],
        "min_order_size": "1",
        "tick_size": "0.01",
        "neg_risk": False,
        "last_trade_price": "0.45",
    }
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=book_data)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("data.clob_price.aiohttp.ClientSession", return_value=mock_session):
        result = await get_book("tok-yes")

    assert result is not None
    assert result["asks"][0]["price"] == "0.46"
    assert result["bids"][0]["price"] == "0.44"
    assert result["last_trade_price"] == "0.45"


@pytest.mark.asyncio
async def test_get_book_returns_none_for_empty_token():
    """Boş token_id → API çağrısı yapılmaz, None döner."""
    with patch("data.clob_price.aiohttp.ClientSession") as mock_cls:
        result = await get_book("")
    mock_cls.assert_not_called()
    assert result is None


@pytest.mark.asyncio
async def test_get_book_returns_none_on_http_404():
    """HTTP 404 (token yok / sona ermiş market) → None döner."""
    mock_resp = MagicMock()
    mock_resp.status = 404
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("data.clob_price.aiohttp.ClientSession", return_value=mock_session):
        result = await get_book("tok-expired")
    assert result is None


@pytest.mark.asyncio
async def test_get_book_returns_none_on_exception():
    """Network exception → None döner (crash yok)."""
    with patch("data.clob_price.aiohttp.ClientSession", side_effect=Exception("timeout")):
        result = await get_book("tok-abc")
    assert result is None
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_clob_price.py::test_get_book_returns_dict_with_bids_and_asks tests/test_clob_price.py::test_get_book_returns_none_for_empty_token tests/test_clob_price.py::test_get_book_returns_none_on_http_404 tests/test_clob_price.py::test_get_book_returns_none_on_exception -v
```
Beklenen: 4x FAIL ("cannot import name 'get_book'")

- [ ] **Step 3: `get_book()` implement et** — `data/clob_price.py` sonuna ekle

```python
async def get_book(token_id: str) -> dict | None:
    """CLOB GET /book?token_id=<id> → tam OrderBookSummary.

    bids: fiyata göre azalan (bids[0] = en iyi bid)
    asks: fiyata göre artan (asks[0] = en iyi ask)
    Her level: {"price": "0.46", "size": "150"}
    Returns: dict veya None (hata / token yok).
    """
    if not token_id:
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(
                f"{CLOB_HOST}/book",
                params={"token_id": token_id},
            ) as r:
                if r.status == 200:
                    return await r.json()
    except Exception:
        pass
    return None
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_clob_price.py -v
```
Beklenen: tüm mevcut testler + 4 yeni test PASS

- [ ] **Step 5: Commit**

```bash
git add data/clob_price.py tests/test_clob_price.py
git commit -m "feat(data): get_book() helper — CLOB /book endpoint tam orderbook + derinlik"
```

---

## Task 2: Scout YES_bid Fallback + NO_ask Gerçek Edge

**Context:** `council/scout.py`'da 2 sorun var:

**Sorun A (satır 102-103):** WS bid yoksa `yes_bid = clob_ask` (ASK fiyatı). Gerçekte `GET /price?side=SELL` çağrılmalı. `get_clob_price(token, "SELL")` zaten çalışıyor — sadece çağrılmıyor.

**Sorun B (satır 104 + 112-113):** NO işlemde `_edge_signal` YES_ask tabanlı pre-filter kullanıyor. Bu geçtikten sonra gerçek NO_ask çekilip edge yeniden hesaplanmalı. Eğer gerçek NO_ask ile `(1-fair) - no_ask < MIN_EDGE_PCT` → false positive → `None` dön.

**Örnek False Positive:**
```
fair=0.45, YES_ask=0.51 → YES_ask-fair=0.06 → "NO signal" (pre-filter geçer)
Gerçek NO_ask=0.55 → real_no_edge=(1-0.45)-0.55=0.00 < 0.05 → açma!
```

**Değiştirilecek satırlar `council/scout.py`:**

Satır 101-104 (YES_bid fallback):
```python
# Mevcut:
_raw_yes_bid  = _ws_prices.get_bid(yes_token)
yes_bid       = _raw_yes_bid if _raw_yes_bid is not None else clob_ask
no_bid_approx = yes_bid   # redteam: 1-yes_bid = NO_ask ✓
```
→ Sonraki adımda değiştiriyoruz.

Satır 112-115 (signal ve sonrası):
```python
# Mevcut:
signal = _edge_signal(fair, clob_ask, no_bid_approx)
if signal is None:
    return None
```
→ Sonraki adımda genişletiyoruz.

**Files:**
- Modify: `council/scout.py`
- Modify: `tests/test_scout.py`

---

- [ ] **Step 1: Failing testleri yaz** — `tests/test_scout.py` sonuna ekle

`council.scout` import satırı başta var. Şunları da ekle:
```python
import data.ws_prices as _ws_module
```

Sonra 3 test ekle:

```python
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
    # YES_bid: WS=None, REST SELL endpoint=0.48
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
        result = await _process_market({"question": "Bitcoin Up or Down 5m", "slug": "btc-test"})

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
    # fair=0.45, YES_ask=0.51 → pre-filter no_edge=0.06 → NO signal (geçer)
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
        result = await _process_market({"question": "Bitcoin Up or Down 5m", "slug": "btc-test"})

    assert result is None, (
        f"False positive filtre çalışmadı! "
        f"fair=0.45, YES_ask=0.51, NO_ask=0.55 → real_no_edge=0.00 < MIN_EDGE_PCT, result={result}"
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
        result = await _process_market({"question": "Bitcoin Up or Down 5m", "slug": "btc-test"})

    assert result is not None, "Gerçek NO edge 0.32 → bulgu dönmeli"
    assert result["action"] == "NO"
    assert abs(result["edge"] - 0.32) < 1e-4, (
        f"NO edge yanlış: beklenen 0.32, gelen {result['edge']}"
    )
    assert result.get("no_ask") == 0.38, (
        f"no_ask finding'de yok ya da yanlış: {result.get('no_ask')}"
    )
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_scout.py::test_yes_bid_uses_sell_endpoint_when_ws_bid_is_none tests/test_scout.py::test_no_false_positive_filtered_by_real_no_ask tests/test_scout.py::test_no_edge_uses_real_no_ask_and_correct_formula -v
```
Beklenen: 3x FAIL

- [ ] **Step 3: `council/scout.py` değişikliklerini uygula**

**Değişiklik A — satırlar 101-104** (YES_bid REST fallback):

Şu kodu:
```python
    # YES bid: WS'den gerçek değer; yoksa YES_ask ≈ YES_bid (ince spread)
    _raw_yes_bid  = _ws_prices.get_bid(yes_token)
    yes_bid       = _raw_yes_bid if _raw_yes_bid is not None else clob_ask
    no_bid_approx = yes_bid   # redteam: 1-yes_bid = NO_ask ✓
```

Şununla değiştir:
```python
    # YES bid: WS'den gerçek değer; yoksa /price?side=SELL; son çare ask
    _raw_yes_bid = _ws_prices.get_bid(yes_token)
    if _raw_yes_bid is not None:
        yes_bid = _raw_yes_bid
    else:
        yes_bid = await get_clob_price(yes_token, "SELL") or clob_ask
```

**Değişiklik B — satırlar 112-115** (signal sonrasına NO_ask bloğu ekle):

Şu kodu:
```python
    signal = _edge_signal(fair, clob_ask, yes_bid)
    if signal is None:
        return None

    taker_fee = await fetch_fee_rate(yes_token) if yes_token else 0.02
```

Şununla değiştir:
```python
    signal = _edge_signal(fair, clob_ask, yes_bid)
    if signal is None:
        return None

    # NO işlem: WS veya REST'ten gerçek NO_ask ile edge'i doğrula
    no_ask = None
    if signal["action"] == "NO" and no_token:
        no_ask = _ws_prices.get_ask(no_token)
        if no_ask is None:
            no_ask = await get_clob_price(no_token, "BUY")
        if no_ask is not None:
            real_no_edge = round((1 - fair) - no_ask, 4)
            if real_no_edge < config.MIN_EDGE_PCT:
                return None  # YES_ask tabanlı sinyal yanlış pozitif çıktı
            signal = {"action": "NO", "edge": real_no_edge}

    taker_fee = await fetch_fee_rate(yes_token) if yes_token else 0.02
```

**Değişiklik C — return dict** (satır 119 civarı, `"no_token_id"` satırına yakın):

`"no_token_id": no_token,` satırından sonra şunu ekle:
```python
        "no_ask":            no_ask,          # NO token gerçek ask (action=NO ise dolu)
```

**Değişiklik D — modül docstring** (satır 10-12):

```python
# Mevcut:
#   NO ucuz  → YES_ask - fair_yes > MIN_EDGE_PCT
#              (HL bearish, market YES'i hâlâ yüksek fiyatlıyor)
#              no_edge = YES_ask - fair_YES  [ince spread: YES_ask ≈ YES_bid]
```

Şununla değiştir:
```python
#   NO ucuz  → (1-fair_yes) - NO_ask > MIN_EDGE_PCT
#              (HL bearish, market YES'i hâlâ yüksek fiyatlıyor)
#              no_edge = (1-fair_yes) - NO_ask  [gerçek NO token ask fiyatı]
#              Pre-filter: YES_ask-fair_yes; sonra /price?token=no_token&side=BUY ile doğrula
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_scout.py -v
```
Beklenen: tüm eski testler + 3 yeni test PASS

- [ ] **Step 5: Commit**

```bash
git add council/scout.py tests/test_scout.py
git commit -m "fix(scout): YES_bid REST fallback SELL endpoint + NO_ask gerçek edge doğrulama"
```

---

## Task 3: RedTeam NO Fee Adj + Orderbook Derinlik Veto

**Context:** `council/redteam.py`'da 2 sorun var:

**Sorun A:** `_fee_adjusted_edge` NO için `1-YES_bid` kullanıyor ama artık `finding["no_ask"]` (Task 2'den) gerçek NO_ask'ı taşıyor. Bunu kullanmalı.

**Sorun B:** Derinlik kontrolü yok. `get_book()` (Task 1'den) ile `asks[0].size × asks[0].price < MIN_BOOK_DEPTH_USD` → `book_too_thin` veto. CLOB spread (`asks[0].price - bids[0].price > SPREAD_VETO`) → `clob_spread_too_wide` veto.

**Mevcut `_fee_adjusted_edge` (satır 33-42):**
```python
def _fee_adjusted_edge(fair: float, ask: float, bid: float,
                        action: str, fee: float) -> float:
    if action == "YES":
        return fair * (1 - fee) - ask
    return (1 - fair) * (1 - fee) - (1 - bid)
```
`1 - bid` = `1 - YES_bid` ≈ NO_ask approximation. Gerçek `no_ask` varsa onu kullan.

**Backward compatibility:** `no_ask=None` (default) → eski `1-bid` formülü korunur. Mevcut testler değişmez.

**`_fake_finding` helper güncellemesi:** `yes_token_id` ve `no_token_id` varsayılan değerlerle eklenmeli (depth check için `action_token` hesaplar). Mevcut testler etkilenmez çünkü expired slug → `fetch_by_slug=None` → `market is None` → early return → book check'e hiç ulaşılmaz.

**Files:**
- Modify: `council/redteam.py`
- Modify: `tests/test_redteam.py`

---

- [ ] **Step 1: Failing testleri yaz** — `tests/test_redteam.py`'a ekle

`_fake_finding` helper'ını güncelle (dosyanın başına bak, satır 22-33 arası):

```python
def _fake_finding(slug="btc-updown-5m-1748571000", action="YES",
                  fair_value=0.65, edge=0.15,
                  cur_price=73_500.0, ref_price=73_000.0,
                  best_ask=0.47, best_bid=0.46, seconds_remaining=180.0,
                  yes_token_id="tok-yes", no_token_id="tok-no",
                  no_ask=None):
    d = {
        "question": "Bitcoin Up or Down - Test",
        "asset": "BTC", "slug": slug, "action": action,
        "edge": edge, "cur_price": cur_price, "ref_price": ref_price,
        "best_ask": best_ask, "best_bid": best_bid,
        "seconds_remaining": seconds_remaining,
        "fair_value": fair_value, "neg_risk": False,
        "yes_token_id": yes_token_id, "no_token_id": no_token_id,
    }
    if no_ask is not None:
        d["no_ask"] = no_ask
    return d
```

Sonra testleri ekle — önce import kontrolü (dosya başında var mı kontrol et):
`from council.redteam import (redteam, _parse_taker_fee, _fee_adjusted_edge, _result, SPREAD_VETO, ...)`
`MIN_BOOK_DEPTH_USD` de import edilmeli — ekleme yapıyoruz.

Şu testleri dosyanın sonuna ekle:

```python
# ── NO fee adj: gerçek no_ask ─────────────────────────────────────────────────

def test_fee_adjusted_edge_no_with_real_no_ask_uses_it_directly():
    """no_ask verildiğinde NO formülü (1-fair)*(1-fee) - no_ask kullanır."""
    net = _fee_adjusted_edge(fair=0.45, ask=0.55, bid=0.44, action="NO", fee=0.02, no_ask=0.38)
    expected = (1 - 0.45) * (1 - 0.02) - 0.38
    assert abs(net - expected) < 1e-6, f"Beklenen {expected:.6f}, gelen {net:.6f}"


def test_fee_adjusted_edge_no_without_no_ask_falls_back_to_1_minus_bid():
    """no_ask=None iken (1-bid) eski davranışı korunur — geriye dönük uyum."""
    net_old = _fee_adjusted_edge(fair=0.35, ask=0.65, bid=0.60, action="NO", fee=0.02)
    net_new = _fee_adjusted_edge(fair=0.35, ask=0.65, bid=0.60, action="NO", fee=0.02, no_ask=None)
    assert abs(net_old - net_new) < 1e-9
    assert abs(net_old - ((1 - 0.35) * 0.98 - (1 - 0.60))) < 1e-6


# ── RedTeam: CLOB book derinlik ve spread ─────────────────────────────────────

@pytest.mark.asyncio
async def test_book_too_thin_veto_when_depth_below_threshold():
    """asks[0] ince → book_too_thin veto."""
    from unittest.mock import patch, AsyncMock
    from council.redteam import MIN_BOOK_DEPTH_USD

    # size=0.10, price=0.46 → depth_usd=0.046 < MIN_BOOK_DEPTH_USD
    thin_book = {
        "asks": [{"price": "0.46", "size": "0.10"}],
        "bids": [{"price": "0.44", "size": "0.10"}],
    }
    fake_market = {"spread": 0.01, "liquidityClob": 1000, "volume24hr": 100, "takerBaseFee": 1000}

    with patch("council.redteam.fetch_by_slug", new_callable=AsyncMock, return_value=fake_market), \
         patch("council.redteam.get_book", new_callable=AsyncMock, return_value=thin_book):
        result = await redteam(
            _fake_finding(action="YES"),
            _fake_verification(fresh_fair=0.65, fresh_ask=0.47, fresh_edge=0.18),
        )

    assert "book_too_thin" in result["vetoes"], (
        f"book_too_thin veto beklendi, gelen vetolar: {result['vetoes']}"
    )


@pytest.mark.asyncio
async def test_book_fetch_failure_does_not_veto_trade():
    """get_book None → depth veto YOK (API hatası trade'i bloke etmez)."""
    from unittest.mock import patch, AsyncMock

    fake_market = {"spread": 0.01, "liquidityClob": 1000, "volume24hr": 100, "takerBaseFee": 1000}

    with patch("council.redteam.fetch_by_slug", new_callable=AsyncMock, return_value=fake_market), \
         patch("council.redteam.get_book", new_callable=AsyncMock, return_value=None):
        result = await redteam(
            _fake_finding(action="YES"),
            _fake_verification(fresh_fair=0.65, fresh_ask=0.47, fresh_edge=0.18),
        )

    assert "book_too_thin" not in result["vetoes"]
    assert "clob_spread_too_wide" not in result["vetoes"]


@pytest.mark.asyncio
async def test_deep_book_does_not_trigger_depth_veto():
    """asks[0].size büyük → book_too_thin YOK."""
    from unittest.mock import patch, AsyncMock

    # size=500, price=0.46 → depth_usd=230 >> MIN_BOOK_DEPTH_USD
    deep_book = {
        "asks": [{"price": "0.46", "size": "500"}],
        "bids": [{"price": "0.44", "size": "500"}],
    }
    fake_market = {"spread": 0.01, "liquidityClob": 1000, "volume24hr": 100, "takerBaseFee": 1000}

    with patch("council.redteam.fetch_by_slug", new_callable=AsyncMock, return_value=fake_market), \
         patch("council.redteam.get_book", new_callable=AsyncMock, return_value=deep_book):
        result = await redteam(
            _fake_finding(action="YES"),
            _fake_verification(fresh_fair=0.65, fresh_ask=0.47, fresh_edge=0.18),
        )

    assert "book_too_thin" not in result["vetoes"]


@pytest.mark.asyncio
async def test_clob_spread_too_wide_veto():
    """CLOB spread > SPREAD_VETO → clob_spread_too_wide veto."""
    from unittest.mock import patch, AsyncMock

    # asks[0]=0.80, bids[0]=0.70 → spread=0.10 > SPREAD_VETO(0.05)
    wide_book = {
        "asks": [{"price": "0.80", "size": "100"}],
        "bids": [{"price": "0.70", "size": "100"}],
    }
    fake_market = {"spread": 0.01, "liquidityClob": 1000, "volume24hr": 100, "takerBaseFee": 1000}

    with patch("council.redteam.fetch_by_slug", new_callable=AsyncMock, return_value=fake_market), \
         patch("council.redteam.get_book", new_callable=AsyncMock, return_value=wide_book):
        result = await redteam(
            _fake_finding(action="YES"),
            _fake_verification(fresh_fair=0.90, fresh_ask=0.78, fresh_edge=0.12),
        )

    assert "clob_spread_too_wide" in result["vetoes"], (
        f"clob_spread_too_wide beklendi, gelen: {result['vetoes']}"
    )
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

```bash
cd /root/mispricing_agent && python -m pytest \
  tests/test_redteam.py::test_fee_adjusted_edge_no_with_real_no_ask_uses_it_directly \
  tests/test_redteam.py::test_fee_adjusted_edge_no_without_no_ask_falls_back_to_1_minus_bid \
  tests/test_redteam.py::test_book_too_thin_veto_when_depth_below_threshold \
  tests/test_redteam.py::test_book_fetch_failure_does_not_veto_trade \
  tests/test_redteam.py::test_deep_book_does_not_trigger_depth_veto \
  tests/test_redteam.py::test_clob_spread_too_wide_veto -v
```
Beklenen: 6x FAIL

- [ ] **Step 3: `council/redteam.py` değişikliklerini uygula**

**Değişiklik A — import ekle** (dosyanın import bölümüne, `from data.shortterm import fetch_by_slug` satırından sonra):
```python
from data.clob_price import get_book
```

**Değişiklik B — sabit ekle** (SPREAD_VETO ve diğer sabitlerden sonra, satır 15-19 civarı):
```python
MIN_BOOK_DEPTH_USD = 2.0    # En iyi ask level'ında min $2 USD derinlik (order ~$1.25)
```

**Değişiklik C — `_fee_adjusted_edge` signature** (satır 33-42):

Şu kodu:
```python
def _fee_adjusted_edge(fair: float, ask: float, bid: float,
                        action: str, fee: float) -> float:
    """
    Fee sonrası gerçek edge.
    YES: fair × (1−fee) − ask
    NO:  (1−fair) × (1−fee) − (1−bid)
    """
    if action == "YES":
        return fair * (1 - fee) - ask
    return (1 - fair) * (1 - fee) - (1 - bid)
```

Şununla değiştir:
```python
def _fee_adjusted_edge(fair: float, ask: float, bid: float,
                        action: str, fee: float,
                        no_ask: float | None = None) -> float:
    """
    Fee sonrası gerçek edge.
    YES: fair × (1−fee) − ask
    NO:  (1−fair) × (1−fee) − entry
         entry = no_ask (gerçek NO ask, Scout'tan geldiyse)
                 veya 1−bid (YES_bid tabanlı yaklaşım, fallback)
    """
    if action == "YES":
        return fair * (1 - fee) - ask
    entry = no_ask if no_ask is not None else (1 - bid)
    return (1 - fair) * (1 - fee) - entry
```

**Değişiklik D — `market is None` path'daki `_fee_adjusted_edge` çağrısı** (satır 93-99 civarı):

Şu çağrıyı:
```python
        fee_adj = _fee_adjusted_edge(
            fair=verification["fresh_fair"],
            ask=verification["fresh_best_ask"],
            bid=verification["fresh_best_bid"],
            action=finding["action"],
            fee=taker_fee,
        )
```

Şununla değiştir:
```python
        fee_adj = _fee_adjusted_edge(
            fair=verification["fresh_fair"],
            ask=verification["fresh_best_ask"],
            bid=verification["fresh_best_bid"],
            action=finding["action"],
            fee=taker_fee,
            no_ask=finding.get("no_ask"),
        )
```

**Değişiklik E — main path'daki `_fee_adjusted_edge` çağrısı** (satır 127-133 civarı, yorum `# ── 6. Fee sonrası edge kontrolü`):

Aynı şekilde `no_ask=finding.get("no_ask"),` parametresi ekle.

**Değişiklik F — book depth + CLOB spread check** (Hacim uyarısı bloğundan sonra, Fee kontrolünden önce — satır 124-126 civarı araya):

```python
    # ── 4b. CLOB book derinliği ve spread ─────────────────────────────────────
    action_token = (finding.get("no_token_id") if finding.get("action") == "NO"
                    else finding.get("yes_token_id"))
    book = await get_book(action_token) if action_token else None
    if book:
        asks = book.get("asks") or []
        bids = book.get("bids") or []
        if asks:
            depth_usd = float(asks[0].get("size", 0)) * float(asks[0].get("price", 0))
            if depth_usd < MIN_BOOK_DEPTH_USD:
                vetoes.append("book_too_thin")
        if asks and bids:
            clob_spread = float(asks[0]["price"]) - float(bids[0]["price"])
            if clob_spread > SPREAD_VETO:
                vetoes.append("clob_spread_too_wide")

    # ── 6. Fee sonrası edge kontrolü ─────────────────────────────────────────
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_redteam.py -v
```
Beklenen: tüm eski testler + 6 yeni test PASS

- [ ] **Step 5: Tam test suite — hepsi yeşil**

```bash
cd /root/mispricing_agent && python -m pytest tests/ -q
```
Beklenen: tüm testler PASS, 0 failed

- [ ] **Step 6: Commit**

```bash
git add council/redteam.py tests/test_redteam.py
git commit -m "fix(redteam): NO fee adj gerçek no_ask + CLOB book derinlik/spread veto"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - [x] YES_bid REST fallback SELL endpoint → Task 2 ✓
   - [x] NO_ask gerçek fiyat → Task 2 ✓
   - [x] NO false positive filtre → Task 2 ✓
   - [x] `no_ask` finding'e yazılıyor → Task 2 ✓
   - [x] RedTeam NO fee adj → Task 3 ✓
   - [x] Book depth veto → Task 3 ✓
   - [x] CLOB spread veto → Task 3 ✓
   - [x] `get_book()` helper → Task 1 ✓

2. **Bağımlılık sırası:** Task 1 (`get_book`) → Task 2 (scout) → Task 3 (redteam). Her task öncekine bağlı.

3. **Backward compat:**
   - `_fee_adjusted_edge(no_ask=None)` eski formülü korur ✓
   - `_fake_finding` eski parametreleri aynen alıyor (ekleme yapıldı, değiştirilmedi) ✓
   - `book is None` → depth veto yok (API hatası trade'i bloke etmez) ✓
   - `no_ask` None ise (NO_token yoksa) eski davranış korunur ✓

4. **Tip tutarlılığı:**
   - `get_book` → `dict | None` ✓
   - `no_ask: float | None = None` ✓
   - `float(asks[0].get("size", 0)) * float(asks[0].get("price", 0))` → string'den float ✓
