# WebSocket Price Feed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polymarket CLOB WebSocket'e bağlanarak gerçek zamanlı `best_bid`/`best_ask` cache'i oluştur; REST polling'i ve `fetch_resolved` polling'i kaldır.

**Architecture:** `data/ws_prices.py` modülünde asyncio arka plan görevi olarak tek kalıcı WS bağlantısı tutulur. `book`, `price_change`, `best_bid_ask`, `market_resolved` eventleri parse edilir. Scout ve main_loop bu cache'i okur; REST fallback'i korur. Market resolve anında WS event'ı queue'ya atılır, main_loop anında kapatır.

**Tech Stack:** `websockets==15.0.1` (kurulu), `asyncio`, mevcut `aiohttp` fallback

---

## Dosya Yapısı

| Dosya | İşlem | Açıklama |
|-------|--------|----------|
| `data/ws_prices.py` | Oluştur | WS cache modülü — bağlantı, parse, public API |
| `tests/test_ws_prices.py` | Oluştur | Birim testler (WS bağlantısı yok, mock) |
| `council/scout.py` | Düzenle | `get_clob_price` → WS cache + REST fallback |
| `main_loop.py` | Düzenle | WS görevi başlat, `market_resolved` anında kapat, WS bid kullan |
| `tests/test_main_loop.py` | Düzenle | `_handle_ws_resolved` testleri |

---

## Task 1: `data/ws_prices.py` — WS fiyat cache modülü

**Files:**
- Create: `data/ws_prices.py`
- Create: `tests/test_ws_prices.py`

---

- [ ] **Step 1: Failing testleri yaz**

`tests/test_ws_prices.py` dosyasını oluştur:

```python
"""tests/test_ws_prices.py — ws_prices birim testleri. Gerçek WS bağlantısı yok."""
import asyncio
import time
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data.ws_prices as ws


def _reset():
    ws._cache.clear()
    ws._subscribed.clear()
    ws._pending.clear()
    ws._resolved_queue = None


def test_get_ask_returns_none_when_not_cached():
    _reset()
    assert ws.get_ask("tok_missing") is None


def test_get_bid_returns_none_when_not_cached():
    _reset()
    assert ws.get_bid("tok_missing") is None


def test_update_cache_and_get_ask():
    _reset()
    ws._update_cache("tok1", best_bid=0.48, best_ask=0.52)
    assert ws.get_ask("tok1") == 0.52
    assert ws.get_bid("tok1") == 0.48


def test_update_cache_spread():
    _reset()
    ws._update_cache("tok2", best_bid=0.73, best_ask=0.77, spread=0.04)
    assert ws.get_spread("tok2") == 0.04


def test_handle_book_extracts_best_bid_and_ask():
    _reset()
    # bids ascending (son = en yüksek), asks ascending (ilk = en düşük)
    event = {
        "event_type": "book",
        "asset_id": "tok3",
        "bids": [{"price": "0.48", "size": "30"}, {"price": "0.50", "size": "15"}],
        "asks": [{"price": "0.52", "size": "25"}, {"price": "0.54", "size": "10"}],
        "timestamp": "1234567890",
    }
    ws._handle_book(event)
    assert ws.get_ask("tok3") == 0.52
    assert ws.get_bid("tok3") == 0.50


def test_handle_book_empty_bids_does_not_crash():
    _reset()
    event = {
        "event_type": "book", "asset_id": "tok_empty",
        "bids": [], "asks": [{"price": "0.60", "size": "10"}], "timestamp": "1",
    }
    ws._handle_book(event)
    assert ws.get_ask("tok_empty") == 0.60
    assert ws.get_bid("tok_empty") is None


def test_handle_price_change_updates_best_bid_ask():
    _reset()
    event = {
        "event_type": "price_change",
        "market": "0x123",
        "price_changes": [{
            "asset_id": "tok4",
            "price": "0.51", "size": "100", "side": "BUY", "hash": "abc",
            "best_bid": "0.51",
            "best_ask": "0.53",
        }],
        "timestamp": "123",
    }
    ws._handle_price_change(event)
    assert ws.get_ask("tok4") == 0.53
    assert ws.get_bid("tok4") == 0.51


def test_handle_price_change_without_best_fields_does_not_crash():
    _reset()
    event = {
        "event_type": "price_change", "market": "0x1",
        "price_changes": [{"asset_id": "tok5", "price": "0.50", "size": "0",
                           "side": "BUY", "hash": "x"}],
        "timestamp": "1",
    }
    ws._handle_price_change(event)  # best_bid/best_ask yok → crash yok
    assert ws.get_ask("tok5") is None


def test_handle_best_bid_ask_event():
    _reset()
    event = {
        "event_type": "best_bid_ask",
        "asset_id": "tok6",
        "market": "0x456",
        "best_bid": "0.73",
        "best_ask": "0.77",
        "spread": "0.04",
        "timestamp": "123",
    }
    ws._handle_best_bid_ask(event)
    assert ws.get_ask("tok6") == 0.77
    assert ws.get_bid("tok6") == 0.73
    assert ws.get_spread("tok6") == 0.04


def test_handle_market_resolved_queues_event():
    _reset()
    ws._resolved_queue = asyncio.Queue()
    event = {
        "event_type": "market_resolved",
        "id": "1234", "market": "0x789",
        "assets_ids": ["yes_tok", "no_tok"],
        "winning_asset_id": "yes_tok",
        "winning_outcome": "Yes",
        "timestamp": "123",
    }
    ws._handle_market_resolved(event)
    assert ws._resolved_queue.qsize() == 1
    queued = ws._resolved_queue.get_nowait()
    assert queued["winning_outcome"] == "Yes"
    assert "yes_tok" in queued["assets_ids"]


def test_handle_market_resolved_no_queue_does_not_crash():
    _reset()
    ws._resolved_queue = None
    event = {"event_type": "market_resolved", "winning_outcome": "No", "assets_ids": []}
    ws._handle_market_resolved(event)  # crash yok


def test_subscribe_adds_to_pending():
    _reset()
    ws.subscribe(["tok_a", "tok_b"])
    assert "tok_a" in ws._pending
    assert "tok_b" in ws._pending


def test_subscribe_skips_already_subscribed():
    _reset()
    ws._subscribed.add("tok_existing")
    ws.subscribe(["tok_existing", "tok_new"])
    assert "tok_existing" not in ws._pending
    assert "tok_new" in ws._pending


def test_subscribe_skips_empty_string():
    _reset()
    ws.subscribe(["", "tok_ok"])
    assert "" not in ws._pending
    assert "tok_ok" in ws._pending


def test_stale_cache_returns_none():
    _reset()
    ws._update_cache("tok_stale", best_bid=0.48, best_ask=0.52)
    ws._cache["tok_stale"]["ts"] = time.time() - (ws.STALE_SECS + 5)
    assert ws.get_ask("tok_stale") is None
    assert ws.get_bid("tok_stale") is None
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

```bash
python -m pytest tests/test_ws_prices.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'data.ws_prices'`

- [ ] **Step 3: `data/ws_prices.py` modülünü yaz**

```python
"""data/ws_prices.py — Polymarket CLOB WebSocket fiyat önbelleği.

Endpoint  : wss://ws-subscriptions-clob.polymarket.com/ws/market
Döküman   : https://docs.polymarket.com  (AsyncAPI Market Channel)
Kullanım  : asyncio.create_task(ws_prices.run(initial_token_ids=[...]))
"""
import asyncio
import json
import time
import websockets

WS_URL        = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
PING_INTERVAL = 10   # saniye
RECONNECT_DELAY = 5  # bağlantı kopunca bekle
STALE_SECS    = 60   # bu kadar eski cache girdisi stale sayılır

# ── Modül düzeyi durum ────────────────────────────────────────────────────────
_cache:    dict[str, dict]       = {}   # token_id → {best_bid, best_ask, spread, ts}
_subscribed: set[str]            = set()
_pending:    set[str]            = set()
_ws                              = None
_resolved_queue: asyncio.Queue | None = None


# ── Public API ────────────────────────────────────────────────────────────────

def get_ask(token_id: str) -> float | None:
    """Cache'deki best_ask. None → kayıt yok veya stale."""
    entry = _cache.get(token_id)
    if entry and (time.time() - entry["ts"]) < STALE_SECS and entry["best_ask"] > 0:
        return entry["best_ask"]
    return None


def get_bid(token_id: str) -> float | None:
    """Cache'deki best_bid. None → kayıt yok veya stale."""
    entry = _cache.get(token_id)
    if entry and (time.time() - entry["ts"]) < STALE_SECS and entry["best_bid"] > 0:
        return entry["best_bid"]
    return None


def get_spread(token_id: str) -> float | None:
    entry = _cache.get(token_id)
    if entry and (time.time() - entry["ts"]) < STALE_SECS:
        return entry.get("spread")
    return None


def subscribe(token_ids: list[str]) -> None:
    """Token ID'leri subscribe listesine ekle. WS aktifse 2s içinde gönderilir."""
    _pending.update(t for t in token_ids if t and t not in _subscribed)


async def run(initial_token_ids: list[str] | None = None) -> None:
    """Ana WS döngüsü. asyncio.create_task ile çalıştırılır."""
    global _resolved_queue
    if _resolved_queue is None:
        _resolved_queue = asyncio.Queue()
    if initial_token_ids:
        subscribe(initial_token_ids)
    while True:
        try:
            await _connect_and_run()
        except Exception as e:
            print(f"[ws] Bağlantı hatası: {e} — {RECONNECT_DELAY}s sonra yeniden deneniyor")
        await asyncio.sleep(RECONNECT_DELAY)


# ── İç fonksiyonlar ───────────────────────────────────────────────────────────

def _update_cache(token_id: str, best_bid: float | None, best_ask: float | None,
                  spread: float | None = None) -> None:
    if not token_id:
        return
    entry = _cache.setdefault(token_id,
                               {"best_bid": 0.0, "best_ask": 1.0, "spread": None, "ts": 0})
    if best_bid is not None and best_bid > 0:
        entry["best_bid"] = best_bid
    if best_ask is not None and best_ask > 0:
        entry["best_ask"] = best_ask
    if spread is not None:
        entry["spread"] = spread
    entry["ts"] = time.time()


def _handle_book(event: dict) -> None:
    token_id = event.get("asset_id")
    bids = event.get("bids", [])
    asks = event.get("asks", [])
    # bids listesi ascending — son eleman = highest bid
    best_bid = float(bids[-1]["price"]) if bids else None
    best_ask = float(asks[0]["price"])  if asks else None
    _update_cache(token_id, best_bid, best_ask)


def _handle_price_change(event: dict) -> None:
    for change in event.get("price_changes", []):
        token_id = change.get("asset_id")
        raw_bid  = change.get("best_bid")
        raw_ask  = change.get("best_ask")
        _update_cache(
            token_id,
            float(raw_bid) if raw_bid else None,
            float(raw_ask) if raw_ask else None,
        )


def _handle_best_bid_ask(event: dict) -> None:
    token_id = event.get("asset_id")
    raw_bid  = event.get("best_bid")
    raw_ask  = event.get("best_ask")
    raw_spr  = event.get("spread")
    _update_cache(
        token_id,
        float(raw_bid) if raw_bid else None,
        float(raw_ask) if raw_ask else None,
        float(raw_spr) if raw_spr else None,
    )


def _handle_market_resolved(event: dict) -> None:
    if _resolved_queue is not None:
        _resolved_queue.put_nowait(event)


async def _flush_pending(ws) -> None:
    global _pending
    if not _pending:
        return
    batch = list(_pending)
    msg = json.dumps({
        "assets_ids":            batch,
        "type":                  "market",
        "custom_feature_enabled": True,
    })
    await ws.send(msg)
    _subscribed.update(batch)
    _pending -= set(batch)


async def _connect_and_run() -> None:
    global _ws
    async with websockets.connect(WS_URL) as ws:
        _ws = ws
        print("[ws] Polymarket CLOB WebSocket bağlandı")
        await _flush_pending(ws)
        ping_task  = asyncio.create_task(_ping_loop(ws))
        flush_task = asyncio.create_task(_pending_flush_loop(ws))
        try:
            async for raw in ws:
                if raw == "PONG":
                    continue
                try:
                    event = json.loads(raw)
                    etype = event.get("event_type")
                    if   etype == "book":            _handle_book(event)
                    elif etype == "price_change":    _handle_price_change(event)
                    elif etype == "best_bid_ask":    _handle_best_bid_ask(event)
                    elif etype == "market_resolved": _handle_market_resolved(event)
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass
        finally:
            ping_task.cancel()
            flush_task.cancel()
            _ws = None


async def _ping_loop(ws) -> None:
    while True:
        await asyncio.sleep(PING_INTERVAL)
        try:
            await ws.send("PING")
        except Exception:
            break


async def _pending_flush_loop(ws) -> None:
    while True:
        await asyncio.sleep(2)
        try:
            await _flush_pending(ws)
        except Exception:
            break
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```bash
python -m pytest tests/test_ws_prices.py -v
```

Expected: `14 passed`

- [ ] **Step 5: Commit**

```bash
git add data/ws_prices.py tests/test_ws_prices.py
git commit -m "feat(ws): Polymarket CLOB WebSocket fiyat cache modülü"
```

---

## Task 2: `council/scout.py` — WS cache + REST fallback

**Files:**
- Modify: `council/scout.py:93-99`
- Modify: `tests/test_scout.py`

---

- [ ] **Step 1: Failing test yaz**

`tests/test_scout.py` dosyasına aşağıdaki 2 testi ekle (mevcut testlerin sonuna):

```python
def test_process_market_uses_ws_cache_when_available(monkeypatch):
    """WS cache'de fiyat varsa REST çağrısı yapılmaz."""
    import data.ws_prices as _ws
    import asyncio
    _ws._cache.clear()
    _ws._update_cache("yes_tok_ws", best_bid=0.46, best_ask=0.54)

    from council.scout import _process_market
    market = {
        "question": "Will BTC go up?",
        "slug": "btc-up-test",
        "clobTokenIds": '["yes_tok_ws", "no_tok_ws"]',
        "eventStartTime": "2025-01-01T00:00:00Z",
        "endDate":        "2025-01-01T01:00:00Z",
        "bestAsk": "0.54",
        "bestBid": "0.46",
        "negRisk": False,
        "outcomePrices": '[0.54, 0.46]',
        "closed": False,
        "active": True,
    }

    rest_called = []

    async def fake_clob(token_id, side="BUY"):
        rest_called.append(token_id)
        return 0.54

    monkeypatch.setattr("council.scout.get_clob_price", fake_clob)
    monkeypatch.setattr("data.hl_candles.price_at_timestamp",
                        lambda *a, **k: asyncio.coroutine(lambda: 95000.0)())
    monkeypatch.setattr("data.hl_candles.current_price",
                        lambda *a, **k: asyncio.coroutine(lambda: 95200.0)())

    # WS cache'den alınca REST çağrılmamalı
    result = asyncio.get_event_loop().run_until_complete(_process_market(market))
    assert "yes_tok_ws" not in rest_called, "WS cache varken REST çağrılmamalı"


def test_process_market_falls_back_to_rest_when_ws_miss(monkeypatch):
    """WS cache miss → REST get_clob_price çağrılır."""
    import data.ws_prices as _ws
    import asyncio
    _ws._cache.clear()  # cache boş → miss

    from council.scout import _process_market
    market = {
        "question": "Will BTC go up?",
        "slug": "btc-up-rest-fallback",
        "clobTokenIds": '["yes_tok_rest", "no_tok_rest"]',
        "eventStartTime": "2025-01-01T00:00:00Z",
        "endDate":        "2025-01-01T01:00:00Z",
        "bestAsk": "0.54", "bestBid": "0.46",
        "negRisk": False, "outcomePrices": '[0.54, 0.46]',
        "closed": False, "active": True,
    }

    rest_called = []

    async def fake_clob(token_id, side="BUY"):
        rest_called.append(token_id)
        return 0.54

    monkeypatch.setattr("council.scout.get_clob_price", fake_clob)
    monkeypatch.setattr("data.hl_candles.price_at_timestamp",
                        lambda *a, **k: asyncio.coroutine(lambda: 95000.0)())
    monkeypatch.setattr("data.hl_candles.current_price",
                        lambda *a, **k: asyncio.coroutine(lambda: 95200.0)())

    asyncio.get_event_loop().run_until_complete(_process_market(market))
    assert "yes_tok_rest" in rest_called, "WS miss'te REST çağrılmalı"
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

```bash
python -m pytest tests/test_scout.py::test_process_market_uses_ws_cache_when_available \
                 tests/test_scout.py::test_process_market_falls_back_to_rest_when_ws_miss -v
```

Expected: FAIL (ws_prices henüz scout'a entegre değil)

- [ ] **Step 3: `council/scout.py` import ve `_process_market` güncelle**

`council/scout.py` dosyasında `from data.clob_price import get_clob_price` satırının altına ekle:

```python
from data import ws_prices as _ws_prices
```

Ardından `_process_market` içindeki şu bloğu:

```python
    # CLOB gerçek zamanlı fiyat — market API bestAsk stale olduğundan kullanmıyoruz
    clob_yes = await get_clob_price(yes_token) if yes_token else None
    if clob_yes is None:
        return None  # CLOB likidite yok → atla

    clob_ask      = clob_yes                  # YES almak için ödeyeceğimiz fiyat (CLOB real-time)
    no_bid_approx = clob_yes                  # YES_ask ≈ YES_bid (ince spread); redteam: 1-bid=NO_bid ✓
```

şununla değiştir:

```python
    # WS cache'den anlık fiyat al; miss veya stale ise REST fallback
    clob_ask = _ws_prices.get_ask(yes_token) if yes_token else None
    if clob_ask is None:
        clob_ask = await get_clob_price(yes_token) if yes_token else None
    if clob_ask is None:
        return None  # Likidite yok → atla

    # YES bid: WS'den gerçek değer; yoksa YES_ask ≈ YES_bid (ince spread)
    yes_bid       = _ws_prices.get_bid(yes_token) or clob_ask
    no_bid_approx = yes_bid   # redteam: 1-yes_bid = NO_ask ✓
```

Return dict içinde de düzenle:

```python
        "best_ask":          clob_ask,    # YES entry fiyatı (CLOB ask)
        "best_bid":          yes_bid,     # YES exit fiyatı (CLOB bid) — WS'den gerçek
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```bash
python -m pytest tests/test_scout.py -v
```

Expected: `38 passed`

- [ ] **Step 5: Commit**

```bash
git add council/scout.py tests/test_scout.py
git commit -m "feat(scout): WS cache önce dene, REST fallback ikinci"
```

---

## Task 3: `main_loop.py` — WS başlat + instant resolution + gerçek bid

**Files:**
- Modify: `main_loop.py`
- Modify: `tests/test_main_loop.py`

---

- [ ] **Step 1: Failing testleri yaz**

`tests/test_main_loop.py` dosyasına şu testleri ekle:

```python
# ── WS resolved handler testleri ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_ws_resolved_closes_yes_position_on_yes_win(tmp_path, monkeypatch):
    """YES pozisyon + 'Yes' kazanınca pm_exit=1.0 ile kapanmalı."""
    from main_loop import _handle_ws_resolved
    from unittest.mock import AsyncMock, patch

    pos = {
        "position_id": "pos-ws-1", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "yes_token_id": "yes_tok_1", "no_token_id": "no_tok_1",
        "pm_entry_price": 0.55, "fair_value": 0.70, "edge": 0.15,
        "position_usd": 1.25, "kelly_f": 0.10, "confidence_score": 80.0,
        "seconds_remaining": 300, "status": "open", "dry_run": False,
        "opened_at": "2026-01-01T00:00:00+00:00", "exit_reason": None, "closed_at": None,
        "entry_hl_price": 95000.0,
    }
    open_positions = [pos]
    closed_today   = []
    event = {
        "event_type": "market_resolved",
        "assets_ids": ["yes_tok_1", "no_tok_1"],
        "winning_asset_id": "yes_tok_1",
        "winning_outcome": "Yes",
        "timestamp": "123",
    }

    monkeypatch.setattr("data.hl_candles.current_price",
                        AsyncMock(return_value=96000.0))

    with patch("main_loop.log_position_close", new=AsyncMock()), \
         patch("main_loop.notify_close"):
        await _handle_ws_resolved(event, open_positions, closed_today, conn=None)

    assert len(open_positions) == 0
    assert len(closed_today) == 1
    assert closed_today[0]["pm_exit_price"] == 1.0
    assert closed_today[0]["exit_reason"] == "market_resolved"


@pytest.mark.asyncio
async def test_handle_ws_resolved_closes_no_position_on_no_win(tmp_path, monkeypatch):
    """NO pozisyon + 'No' kazanınca pm_exit=1.0 ile kapanmalı."""
    from main_loop import _handle_ws_resolved
    from unittest.mock import AsyncMock, patch

    pos = {
        "position_id": "pos-ws-2", "slug": "eth-down-15m", "asset": "ETH",
        "action": "NO", "yes_token_id": "yes_tok_2", "no_token_id": "no_tok_2",
        "pm_entry_price": 0.40, "fair_value": 0.20, "edge": 0.20,
        "position_usd": 1.25, "kelly_f": 0.10, "confidence_score": 80.0,
        "seconds_remaining": 300, "status": "open", "dry_run": False,
        "opened_at": "2026-01-01T00:00:00+00:00", "exit_reason": None, "closed_at": None,
        "entry_hl_price": 3000.0,
    }
    open_positions = [pos]
    closed_today   = []
    event = {
        "event_type": "market_resolved",
        "assets_ids": ["yes_tok_2", "no_tok_2"],
        "winning_asset_id": "no_tok_2",
        "winning_outcome": "No",
        "timestamp": "123",
    }

    monkeypatch.setattr("data.hl_candles.current_price", AsyncMock(return_value=2900.0))

    with patch("main_loop.log_position_close", new=AsyncMock()), \
         patch("main_loop.notify_close"):
        await _handle_ws_resolved(event, open_positions, closed_today, conn=None)

    assert len(open_positions) == 0
    assert closed_today[0]["pm_exit_price"] == 1.0


@pytest.mark.asyncio
async def test_handle_ws_resolved_yes_position_loses(monkeypatch):
    """YES pozisyon + 'No' kazanınca pm_exit=0.0 ile kapanmalı."""
    from main_loop import _handle_ws_resolved
    from unittest.mock import AsyncMock, patch

    pos = {
        "position_id": "pos-ws-3", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "yes_token_id": "yes_tok_3", "no_token_id": "no_tok_3",
        "pm_entry_price": 0.55, "fair_value": 0.70, "edge": 0.15,
        "position_usd": 1.25, "kelly_f": 0.10, "confidence_score": 80.0,
        "seconds_remaining": 300, "status": "open", "dry_run": False,
        "opened_at": "2026-01-01T00:00:00+00:00", "exit_reason": None, "closed_at": None,
        "entry_hl_price": 95000.0,
    }
    open_positions = [pos]
    closed_today   = []
    event = {
        "event_type": "market_resolved",
        "assets_ids": ["yes_tok_3", "no_tok_3"],
        "winning_asset_id": "no_tok_3",
        "winning_outcome": "No",
        "timestamp": "123",
    }

    monkeypatch.setattr("data.hl_candles.current_price", AsyncMock(return_value=94000.0))

    with patch("main_loop.log_position_close", new=AsyncMock()), \
         patch("main_loop.notify_close"):
        await _handle_ws_resolved(event, open_positions, closed_today, conn=None)

    assert closed_today[0]["pm_exit_price"] == 0.0


@pytest.mark.asyncio
async def test_handle_ws_resolved_ignores_unrelated_market(monkeypatch):
    """assets_ids eşleşmiyorsa pozisyona dokunmamalı."""
    from main_loop import _handle_ws_resolved
    from unittest.mock import AsyncMock

    pos = {
        "position_id": "pos-ws-4", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "yes_token_id": "yes_tok_4", "no_token_id": "no_tok_4",
        "pm_entry_price": 0.55, "fair_value": 0.70, "edge": 0.15,
        "position_usd": 1.25, "kelly_f": 0.10, "confidence_score": 80.0,
        "seconds_remaining": 300, "status": "open", "dry_run": False,
        "opened_at": "2026-01-01T00:00:00+00:00", "exit_reason": None, "closed_at": None,
        "entry_hl_price": 95000.0,
    }
    open_positions = [pos]
    closed_today   = []
    event = {
        "event_type": "market_resolved",
        "assets_ids": ["other_tok_1", "other_tok_2"],  # farklı market
        "winning_asset_id": "other_tok_1",
        "winning_outcome": "Yes",
        "timestamp": "123",
    }

    monkeypatch.setattr("data.hl_candles.current_price", AsyncMock(return_value=95000.0))
    await _handle_ws_resolved(event, open_positions, closed_today, conn=None)

    assert len(open_positions) == 1  # dokunmadı
    assert len(closed_today) == 0
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

```bash
python -m pytest tests/test_main_loop.py::test_handle_ws_resolved_closes_yes_position_on_yes_win -v
```

Expected: `ImportError: cannot import name '_handle_ws_resolved'`

- [ ] **Step 3: `main_loop.py` import satırına ws_prices ekle**

`main_loop.py` dosyasındaki `import config` satırının altına ekle:

```python
from data import ws_prices
```

- [ ] **Step 4: `_handle_ws_resolved` fonksiyonunu ekle**

`main_loop.py` içinde `_heal_pending_resolutions` fonksiyonunun hemen üstüne şu fonksiyonu ekle:

```python
async def _handle_ws_resolved(
    event: dict,
    open_positions: list[dict],
    closed_today:   list[dict],
    conn=None,
) -> None:
    """WS market_resolved event'ına göre açık pozisyonu anında kapat."""
    winning_outcome = event.get("winning_outcome")   # "Yes" veya "No"
    assets_ids      = set(event.get("assets_ids", []))
    if not assets_ids:
        return

    for pos in list(open_positions):
        if pos.get("yes_token_id") not in assets_ids \
           and pos.get("no_token_id") not in assets_ids:
            continue
        # Pozisyon bu markete ait → resolve et
        if pos["action"] == "YES":
            pm_exit = 1.0 if winning_outcome == "Yes" else 0.0
        else:  # NO
            pm_exit = 1.0 if winning_outcome == "No" else 0.0
        try:
            hl_price = await current_price(pos["asset"])
        except Exception:
            hl_price = None
        closed = close_position(pos, "market_resolved", pm_exit_price=pm_exit,
                                exit_hl_price=hl_price)
        await log_position_close(conn, closed)
        open_positions.remove(pos)
        closed_today.append(closed)
        notify_close(closed)
        print(f"[ws] {pos['slug']} resolved — {winning_outcome} wins → pm_exit={pm_exit}")
```

- [ ] **Step 5: `main()` içinde WS görevi başlat**

`main()` fonksiyonundaki `asyncio.create_task(poll_commands())` satırının hemen altına ekle:

```python
    # WS fiyat feed — mevcut açık pozisyon token'larıyla başlat
    initial_tids = [
        tid
        for pos in open_positions
        for tid in (pos.get("yes_token_id"), pos.get("no_token_id"))
        if tid
    ]
    asyncio.create_task(ws_prices.run(initial_tids))
```

- [ ] **Step 6: Ana döngüde WS resolved olaylarını işle**

`main()` içindeki `try` bloğundaki `await _monitor_positions(...)` satırının **hemen ardına** şunu ekle:

```python
                # WS üzerinden gelen anlık resolution olaylarını işle
                if ws_prices._resolved_queue:
                    while not ws_prices._resolved_queue.empty():
                        ev = ws_prices._resolved_queue.get_nowait()
                        await _handle_ws_resolved(ev, open_positions, closed_today, conn=conn)
                        for pos in closed_today[n_closed_before:]:
                            notify_close(pos)
```

**Not:** `n_closed_before` zaten bu bloktan önce tanımlı — mevcut kodu bozmaz.

- [ ] **Step 7: Yeni pozisyon açıldıktan sonra token'ları subscribe et**

`_scan_and_execute` fonksiyonundaki `open_positions.append(position)` satırının hemen altına ekle:

```python
            # WS feed'e bu pozisyonun token'larını ekle
            ws_prices.subscribe([
                t for t in (position.get("yes_token_id"), position.get("no_token_id")) if t
            ])
```

- [ ] **Step 8: `_monitor_positions` içinde WS bid kullan**

`_monitor_positions` fonksiyonunda `pm_yes_price` hesabını şununla değiştir:

```python
            # YES için gerçek SELL fiyatı: WS bid veya Gamma window bid
            if pos["action"] == "YES":
                ws_bid = ws_prices.get_bid(pos.get("yes_token_id", ""))
                pm_yes_price = ws_bid or window["best_bid"]
            else:
                ws_bid = ws_prices.get_bid(pos.get("no_token_id", ""))
                pm_yes_price = ws_bid or window["best_ask"]
```

DRY_RUN exit fiyatı için de aynı mantık — mevcut `pm_exit = window["best_bid"]` yerine:

```python
                if config.DRY_RUN:
                    if pos["action"] == "NO":
                        pm_exit = round(1 - (ws_prices.get_ask(pos.get("yes_token_id", "")) or window["best_ask"]), 4)
                    else:
                        pm_exit = ws_prices.get_bid(pos.get("yes_token_id", "")) or window["best_bid"]
```

- [ ] **Step 9: Tüm testleri çalıştır**

```bash
python -m pytest tests/test_main_loop.py tests/test_ws_prices.py tests/test_scout.py -v
```

Expected: Tüm testler geçmeli, 0 fail.

- [ ] **Step 10: Commit**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(main_loop): WS fiyat feed entegrasyonu — instant resolution + gerçek bid"
```

---

## Son Kontrol

- [ ] **Tüm testler yeşil**

```bash
python -m pytest tests/ --ignore=tests/test_db.py -v 2>&1 | tail -5
```

Expected: `X passed, 0 failed`

- [ ] **Graphify ve GitHub güncelle**

```bash
graphify update .
git add graphify-out/
git push origin master
```

---

## Özet: Bu Plan Ne Sağlar

| Öncesi | Sonrası |
|--------|---------|
| REST polling her 15s | WS push — sub-saniye fiyat |
| YES_bid = YES_ask (approx) | Gerçek YES_bid WS'den |
| `fetch_resolved` polling | `market_resolved` event — anında |
| spread bilinmiyor | `spread` field WS'den |
| Scout'ta REST gecikme | WS cache sıfır gecikme |
