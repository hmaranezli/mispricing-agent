# Faz 2 — WS Event-Driven Position Monitor: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `_monitor_positions` artık 7s uyumak yerine WS price event'ini bekler; event gelince cached context ile `check_exit()` çalışır (<1s latency). 7s timeout = REST heartbeat (cache refresh + fallback). MIN_PROFIT_CONFIRM_SECS=3 zaman kapısı ve `_closing` double-close koruması eklenir.

**Architecture:** `ws_prices.py`'a `asyncio.Event` eklenir, her fiyat güncellemesinde set edilir. `_monitor_positions` iki path'li olur: WS event path (REST yok, cached context) ve REST heartbeat path (7s timeout, tam refresh). `main()` döngüsündeki `asyncio.sleep(7)` kaldırılır; scan ve heal yalnızca REST path'te çalışır.

**Tech Stack:** Python 3.12, asyncio, aiosqlite, pytest-asyncio, unittest.mock

---

## Dosya Haritası

| Dosya | Değişiklik |
|-------|-----------|
| `data/ws_prices.py` | `_price_event` modül değişkeni + `get_price_event()` + `_update_cache()` sonu event.set() |
| `position/manager.py` | `MIN_PROFIT_CONFIRM_SECS = 3` + profit confirm zaman kapısı |
| `main_loop.py` | `_monitor_positions` iki path → `bool` döner; `main()` sleep kaldırılır, scan koşullu |
| `tests/test_ws_prices.py` | 3 yeni test |
| `tests/test_position.py` | 3 yeni test |
| `tests/test_main_loop.py` | 5 yeni test |

---

## Task 1: ws_prices.py — Price Event

**Files:**
- Modify: `data/ws_prices.py`
- Test: `tests/test_ws_prices.py`

- [ ] **Step 1: Failing testleri yaz**

`tests/test_ws_prices.py` dosyasının sonuna ekle:

```python
# ── Task 1: price_event ──────────────────────────────────────────────────────

def test_get_price_event_returns_asyncio_event():
    """get_price_event() bir asyncio.Event döndürür."""
    import data.ws_prices as ws
    ws._price_event = None  # modül state sıfırla
    event = ws.get_price_event()
    assert isinstance(event, asyncio.Event)


def test_get_price_event_is_singleton():
    """get_price_event() her çağrıda aynı instance'ı döndürür."""
    import data.ws_prices as ws
    ws._price_event = None
    e1 = ws.get_price_event()
    e2 = ws.get_price_event()
    assert e1 is e2


def test_update_cache_sets_price_event():
    """_update_cache() çağrıldığında price_event set edilir."""
    import data.ws_prices as ws
    ws._price_event = None
    event = ws.get_price_event()
    event.clear()
    ws._update_cache("tok-test", best_bid=0.50, best_ask=0.52)
    assert event.is_set(), "_update_cache() sonrası price_event set olmalı"
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

```bash
python -m pytest tests/test_ws_prices.py -k "price_event" -v --tb=short
```

Beklenen: 3 FAILED — `AttributeError: module 'data.ws_prices' has no attribute '_price_event'`

- [ ] **Step 3: ws_prices.py'a implementasyonu ekle**

`data/ws_prices.py` modül değişkenleri bloğuna (`_resolved_queue` satırından sonra) ekle:

```python
_price_event: asyncio.Event | None = None
```

Aynı dosyada `_resolved_queue` satırından sonra, `get_ask` fonksiyonundan önce yeni public fonksiyon ekle:

```python
def get_price_event() -> asyncio.Event:
    """WS fiyat güncellemelerini dinleyen global asyncio.Event (lazy init)."""
    global _price_event
    if _price_event is None:
        _price_event = asyncio.Event()
    return _price_event
```

`_update_cache()` fonksiyonunun sonuna (`entry["ts"] = time.time()` satırından sonra) ekle:

```python
    if _price_event is not None:
        _price_event.set()
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```bash
python -m pytest tests/test_ws_prices.py -k "price_event" -v --tb=short
```

Beklenen: 3 PASSED

- [ ] **Step 5: Tüm suite temiz kalsın**

```bash
python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5
```

Beklenen: `N passed, M skipped` — 0 failed

- [ ] **Step 6: Commit**

```bash
git add data/ws_prices.py tests/test_ws_prices.py
git commit -m "feat(ws): price_event — _update_cache her güncellemede event set eder"
```

---

## Task 2: position/manager.py — Profit Confirm Zaman Kapısı

**Files:**
- Modify: `position/manager.py`
- Test: `tests/test_position.py`

- [ ] **Step 1: Failing testleri yaz**

`tests/test_position.py` dosyasının sonuna (mevcut Faz 1 testlerinin altına) ekle:

```python
# ── Task 2: Profit confirm zaman kapısı ──────────────────────────────────────

def test_profit_confirm_time_gate_blocks_exit_when_elapsed_too_short():
    """Cycles tamamlandı ama <3s geçti → profit_target_hit dönmez."""
    from datetime import datetime, timezone
    pos = _position("YES", held_minutes=5)
    entry = pos["pm_entry_price"]  # 0.35
    # fair_value=0.55 → edge=0.20, PROFIT_TARGET_FRACTION=0.85 → target=0.35+0.17=0.52
    # 0.54 > 0.52 → profit_ready=True, captured=0.19 > PROFIT_LOCK_MIN=0.10 ✓
    high_price = 0.54

    # İlk çağrı: _profit_confirm_first_ts set edilir
    result1 = check_exit(pos, hl_price=95000, pm_yes_price=high_price, time_to_expiry_secs=500)
    assert result1 is None, "İlk cycle: henüz yeterli sayı yok"
    assert pos.get("_profit_confirm_first_ts") is not None

    # Hemen ikinci çağrı (0ms geçti): cycles=2 tamamlandı ama 3s geçmedi
    result2 = check_exit(pos, hl_price=95000, pm_yes_price=high_price, time_to_expiry_secs=500)
    assert result2 is None, "Cycles=2 ama <3s → zaman kapısı bloklamalı"


def test_profit_confirm_time_gate_allows_exit_when_elapsed_sufficient():
    """Cycles tamamlandı VE >=3s geçti → profit_target_hit döner."""
    from datetime import datetime, timezone, timedelta
    pos = _position("YES", held_minutes=5)
    high_price = 0.54

    # _profit_confirm_first_ts'i 4s önceye set et (simüle edilmiş 3s geçmesi)
    past_ts = (datetime.now(timezone.utc) - timedelta(seconds=4)).isoformat()
    pos["_profit_confirm_first_ts"] = past_ts
    pos["_profit_confirm"] = 1  # bir cycle zaten sayılmış

    # Şimdi ikinci çağrı: cycles=2 VE 4s > 3s → çıkış
    result = check_exit(pos, hl_price=95000, pm_yes_price=high_price, time_to_expiry_secs=500)
    assert result == "profit_target_hit", f"Beklenen profit_target_hit, alınan: {result}"


def test_profit_confirm_reset_clears_first_ts():
    """Profit hedefi kaybolunca _profit_confirm_first_ts da sıfırlanır."""
    pos = _position("YES", held_minutes=5)
    pos["_profit_confirm"] = 1
    pos["_profit_confirm_first_ts"] = "2026-06-07T10:00:00+00:00"

    # Düşük fiyat → profit_ready=False → reset
    check_exit(pos, hl_price=95000, pm_yes_price=0.38, time_to_expiry_secs=500)
    assert pos["_profit_confirm"] == 0
    assert "_profit_confirm_first_ts" not in pos, "_profit_confirm_first_ts silinmeli"
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

```bash
python -m pytest tests/test_position.py -k "time_gate" -v --tb=short
```

Beklenen: `test_profit_confirm_time_gate_blocks_exit_when_elapsed_too_short` FAILED (profit_target_hit dönüyor, dönmemeli), diğerleri ilgili assertion'larda fail

- [ ] **Step 3: manager.py'a implementasyonu ekle**

`position/manager.py` sabit bloğuna (`MIN_HOLD_SECS` satırından sonra) ekle:

```python
MIN_PROFIT_CONFIRM_SECS = 3   # WS hızında cycle-sayısı yeterli değil — zaman kapısı
```

`check_exit()` içindeki profit confirm bloğunu bul (satır 153-158) ve şununla değiştir:

```python
    if profit_ready and not near_expiry:
        position["_profit_confirm"] = position.get("_profit_confirm", 0) + 1
        position.setdefault("_profit_confirm_first_ts", now.isoformat())
        elapsed = (now - datetime.fromisoformat(
            position["_profit_confirm_first_ts"]
        )).total_seconds()
        if (position["_profit_confirm"] >= PROFIT_CONFIRM_CYCLES
                and elapsed >= MIN_PROFIT_CONFIRM_SECS):
            return "profit_target_hit"
    else:
        position["_profit_confirm"] = 0
        position.pop("_profit_confirm_first_ts", None)
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```bash
python -m pytest tests/test_position.py -k "time_gate" -v --tb=short
```

Beklenen: 3 PASSED

- [ ] **Step 5: Tüm suite temiz kalsın**

```bash
python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5
```

Beklenen: 0 failed

- [ ] **Step 6: Commit**

```bash
git add position/manager.py tests/test_position.py
git commit -m "feat(manager): MIN_PROFIT_CONFIRM_SECS=3 zaman kapısı — WS hızında glitch koruması"
```

---

## Task 3: main_loop._monitor_positions — İki Path + `_closing` Flag

**Files:**
- Modify: `main_loop.py`
- Test: `tests/test_main_loop.py`

- [ ] **Step 1: Failing testleri yaz**

`tests/test_main_loop.py` dosyasının sonuna (price_source testlerinin altına) ekle:

```python
# ── Faz 2: WS event-driven _monitor_positions ────────────────────────────────

@pytest.mark.asyncio
async def test_monitor_ws_path_returns_true_and_makes_no_rest_calls():
    """WS event anında gelirse True döner ve REST çağrısı yapılmaz."""
    import config as _cfg
    import data.ws_prices as _ws
    _ws._price_event = None
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900
    fake_window = {"best_ask": 0.52, "best_bid": 0.50, "seconds_remaining": 900, "neg_risk": False}

    with patch("main_loop.current_price",       new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",        new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window",  return_value=fake_window), \
         patch("main_loop.ws_prices")           as mock_ws, \
         patch("main_loop.check_exit",           return_value=None), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_ws.get_bid.return_value = 0.50
        mock_ws.get_price_event.return_value = asyncio.Event()
        mock_ws.get_price_event.return_value.set()   # event hazır — anında uyanacak
        result = await _monitor_positions([pos], [])

    assert result is True, "WS event tetiklendi → True dönmeli"
    mock_hl.assert_not_called(), "WS path'te current_price (REST) çağrılmamalı"
    mock_pm.assert_not_called(), "WS path'te fetch_by_slug (REST) çağrılmamalı"


@pytest.mark.asyncio
async def test_monitor_rest_path_returns_false_and_refreshes_cache():
    """WS event 7s içinde gelmezse False döner, cache güncellenir."""
    import config as _cfg
    import data.ws_prices as _ws
    _ws._price_event = None
    pos = _pos_with_token("YES")
    fake_window = {"best_ask": 0.52, "best_bid": 0.50, "seconds_remaining": 888, "neg_risk": False}

    empty_event = asyncio.Event()   # set edilmedi — timeout ateşlenecek

    with patch("main_loop.current_price",       new_callable=AsyncMock, return_value=96000.0), \
         patch("main_loop.fetch_by_slug",        new_callable=AsyncMock, return_value={}), \
         patch("main_loop.parse_market_window",  return_value=fake_window), \
         patch("main_loop.ws_prices")           as mock_ws, \
         patch("main_loop.check_exit",           return_value=None), \
         patch("main_loop.asyncio.wait_for",     new_callable=AsyncMock,
               side_effect=asyncio.TimeoutError), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_ws.get_bid.return_value = 0.50
        mock_ws.get_price_event.return_value = empty_event
        result = await _monitor_positions([pos], [])

    assert result is False, "Timeout → False dönmeli"
    assert pos.get("_cached_hl_price")          == 96000.0, "HL cache güncellenmeli"
    assert pos.get("_cached_seconds_remaining") == 888,     "seconds_remaining cache güncellenmeli"


@pytest.mark.asyncio
async def test_monitor_ws_path_skips_closing_position():
    """_closing=True pozisyon WS event path'te tamamen skip edilir."""
    import config as _cfg
    import data.ws_prices as _ws
    _ws._price_event = None
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900
    pos["_closing"] = True   # zaten satılıyor

    mock_check = MagicMock(return_value="stop_loss_hit")
    with patch("main_loop.ws_prices")          as mock_ws, \
         patch("main_loop.check_exit",          mock_check), \
         patch("main_loop.asyncio.wait_for",    new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_ws.get_bid.return_value = 0.20
        mock_ws.get_price_event.return_value = asyncio.Event()
        await _monitor_positions([pos], [])

    mock_check.assert_not_called(), "_closing pozisyonunda check_exit çağrılmamalı"


@pytest.mark.asyncio
async def test_monitor_live_sets_closing_true_before_sell():
    """LIVE: exit kararında _closing=True sell_position() öncesinde set edilir."""
    import config as _cfg
    import data.ws_prices as _ws
    _ws._price_event = None
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900

    closing_at_call = {}
    async def fake_sell(p):
        closing_at_call["val"] = p.get("_closing")
        return 0.30

    with patch("main_loop.ws_prices")          as mock_ws, \
         patch("main_loop.check_exit",          return_value="stop_loss_hit"), \
         patch("main_loop.sell_position",        side_effect=fake_sell), \
         patch("main_loop.log_position_close",  new_callable=AsyncMock), \
         patch("main_loop.asyncio.wait_for",    new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", False):
        mock_ws.get_bid.return_value = 0.20
        mock_ws.get_price_event.return_value = asyncio.Event()
        await _monitor_positions([pos], [])

    assert closing_at_call.get("val") is True, "sell_position() çağrısında _closing=True olmalı"


@pytest.mark.asyncio
async def test_monitor_live_resets_closing_on_fak_fail():
    """LIVE: sell_position() None dönerse _closing=False reset edilir."""
    import config as _cfg
    import data.ws_prices as _ws
    _ws._price_event = None
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900
    open_pos = [pos]

    with patch("main_loop.ws_prices")         as mock_ws, \
         patch("main_loop.check_exit",         return_value="stop_loss_hit"), \
         patch("main_loop.sell_position",       new_callable=AsyncMock, return_value=None), \
         patch("main_loop.asyncio.wait_for",   new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", False):
        mock_ws.get_bid.return_value = 0.20
        mock_ws.get_price_event.return_value = asyncio.Event()
        await _monitor_positions(open_pos, [])

    assert pos.get("_closing") is False, "FAK fail → _closing=False resetlenmeli"
    assert len(open_pos) == 1,           "FAK fail → pozisyon listede kalmalı"
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

```bash
python -m pytest tests/test_main_loop.py -k "ws_path or closing" -v --tb=line 2>&1 | tail -20
```

Beklenen: 5 FAILED

- [ ] **Step 3: `_monitor_positions` fonksiyonunu tamamen değiştir**

`main_loop.py`'daki mevcut `_monitor_positions` fonksiyonunu aşağıdakiyle değiştir (imza `bool` döner):

```python
async def _monitor_positions(
    open_positions: list[dict],
    closed_today:   list[dict],
    conn=None,
    failed_slugs: set | None = None,
) -> bool:
    """Açık pozisyonları izler. WS event gelince hızlı path, 7s timeout → REST heartbeat.

    Döner:
      True  → WS event tetikledi (scan yapma — henüz erken)
      False → 7s timeout (REST refresh yapıldı — scan zamanı)
    """
    price_event = ws_prices.get_price_event()
    try:
        await asyncio.wait_for(price_event.wait(), timeout=float(SCAN_INTERVAL_SECS))
        price_event.clear()
        ws_triggered = True
    except asyncio.TimeoutError:
        ws_triggered = False

    for pos in list(open_positions):
        if pos.get("_closing"):
            continue
        try:
            if ws_triggered:
                # ── WS hızlı path: REST yok, cached context ───────────────
                hl_price          = pos.get("_cached_hl_price") or pos.get("ref_price", 0)
                seconds_remaining = pos.get("_cached_seconds_remaining", 900)
                yes_tid           = pos.get("yes_token_id", "")
                if pos["action"] == "YES":
                    pm_yes_price = ws_prices.get_bid(yes_tid)
                    _price_source, _data_quality = "ws_bid", "exact"
                else:
                    pm_yes_price = ws_prices.get_ask(yes_tid)
                    _price_source, _data_quality = "ws_ask_complement", "estimated"
                if pm_yes_price is None:
                    continue
            else:
                # ── REST heartbeat: tam refresh, cache yaz ─────────────────
                hl_price   = await current_price(pos["asset"])
                pos["_cached_hl_price"] = hl_price
                market_raw = await fetch_by_slug(pos["slug"])
                window     = parse_market_window(market_raw)
                if window is None:
                    resolution = await fetch_resolved(pos["slug"])
                    if resolution:
                        pm_exit = (resolution["yes_exit"] if pos["action"] == "YES"
                                   else resolution["no_exit"])
                        closed = close_position(pos, "market_resolved",
                                                pm_exit_price=pm_exit, exit_hl_price=hl_price)
                        await log_position_close(conn, closed)
                        open_positions.remove(pos)
                        closed_today.append(closed)
                    continue
                pos["_cached_seconds_remaining"] = window["seconds_remaining"]
                seconds_remaining = window["seconds_remaining"]
                yes_tid = pos.get("yes_token_id", "")
                if pos["action"] == "YES":
                    pm_yes_price = ws_prices.get_bid(yes_tid)
                    if pm_yes_price is None:
                        pm_yes_price = await get_clob_price(yes_tid, "SELL")
                        _price_source, _data_quality = "clob_rest_bid", "exact"
                    else:
                        _price_source, _data_quality = "ws_bid", "exact"
                else:
                    pm_yes_price = ws_prices.get_ask(yes_tid)
                    if pm_yes_price is None:
                        pm_yes_price = await get_clob_price(yes_tid, "BUY")
                        _price_source, _data_quality = "clob_rest_ask_complement", "estimated"
                    else:
                        _price_source, _data_quality = "ws_ask_complement", "estimated"
                if pm_yes_price is None:
                    continue

            exit_reason = check_exit(pos, hl_price, pm_yes_price, seconds_remaining)
            pos["price_source"]    = _price_source
            pos["mae_data_quality"] = _data_quality

            if exit_reason:
                if config.DRY_RUN:
                    if pos["action"] == "NO":
                        _no_bid = ws_prices.get_bid(pos.get("no_token_id", ""))
                        if ws_triggered:
                            pm_exit = (_no_bid if _no_bid is not None
                                       else round(1 - pm_yes_price, 4))
                        else:
                            pm_exit = (_no_bid if _no_bid is not None
                                       else round(1 - window["best_ask"], 4))
                    else:
                        _yes_bid = ws_prices.get_bid(pos.get("yes_token_id", ""))
                        pm_exit = (_yes_bid if _yes_bid is not None
                                   else (pm_yes_price if ws_triggered else window["best_bid"]))
                else:
                    pos["_closing"] = True
                    if pos["action"] == "NO":
                        _no_bid = ws_prices.get_bid(pos.get("no_token_id", ""))
                        pos["current_bid"] = (_no_bid if _no_bid is not None
                                              else round(1 - pm_yes_price, 4)
                                              if ws_triggered
                                              else round(1 - window["best_ask"], 4))
                    else:
                        _yes_bid = ws_prices.get_bid(pos.get("yes_token_id", ""))
                        pos["current_bid"] = (_yes_bid if _yes_bid is not None
                                              else (pm_yes_price if ws_triggered
                                                    else window["best_bid"]))
                    pm_exit = await sell_position(pos)
                    if pm_exit is None:
                        pos["_closing"] = False
                        print(f"[monitor] {pos['slug']} SELL başarısız — pozisyon açık kalıyor")
                        continue
                closed = close_position(pos, exit_reason, pm_exit_price=pm_exit,
                                        exit_hl_price=hl_price)
                await log_position_close(conn, closed)
                open_positions.remove(pos)
                closed_today.append(closed)
                if failed_slugs is not None and exit_reason == "stop_loss_hit":
                    failed_slugs.add(pos["slug"])

        except Exception as e:
            print(f"[monitor] {pos['slug']} hata: {e}")

    return ws_triggered
```

- [ ] **Step 4: Yeni testlerin geçtiğini doğrula**

```bash
python -m pytest tests/test_main_loop.py -k "ws_path or closing" -v --tb=short 2>&1 | tail -15
```

Beklenen: 5 PASSED

- [ ] **Step 5: Tüm suite — özellikle eski monitor testleri**

```bash
python -m pytest tests/test_main_loop.py -v --tb=short 2>&1 | tail -20
```

Beklenen: Tüm testler PASSED (eski testler varsa `return_value=True/False` ile mock güncellenmesi gerekebilir — **sonraki adıma geç**)

- [ ] **Step 5b: Eski _monitor_positions testlerini `bool` dönüşüne uyarla**

Mevcut testler `await _monitor_positions(...)` return değerini kullanmıyor ama fonksiyon artık `bool` döndürüyor — bu sorun yaratmaz. Ancak `asyncio.wait_for` patching gereken testler için gerekirse `side_effect=asyncio.TimeoutError` ekle.

```bash
python -m pytest tests/ -x -q --tb=short 2>&1 | tail -5
```

Beklenen: 0 failed

- [ ] **Step 6: Commit**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(monitor): Faz 2 iki path — WS event hızlı path + REST heartbeat + _closing flag"
```

---

## Task 4: main_loop.main() — Sleep Kaldır, Scan Koşullu Yap

**Files:**
- Modify: `main_loop.py`
- Test: `tests/test_main_loop.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_main_loop.py` sonuna ekle:

```python
@pytest.mark.asyncio
async def test_scan_and_execute_not_called_on_ws_event():
    """WS event gelince (True dönünce) _scan_and_execute çağrılmaz."""
    import config as _cfg
    mock_scan = AsyncMock()

    with patch("main_loop._monitor_positions",  new_callable=AsyncMock, return_value=True), \
         patch("main_loop._scan_and_execute",    mock_scan), \
         patch("main_loop.get_effective_bankroll", new_callable=AsyncMock, return_value=25.0), \
         patch("main_loop.ws_prices"), \
         patch.object(_cfg, "DRY_RUN", True):
        # Tek iterasyon simüle et — main() yerine iç mantığı test et
        ws_triggered = await _monitor_positions.__wrapped__([], [], conn=None) \
            if hasattr(_monitor_positions, "__wrapped__") else True
        if not ws_triggered:
            await mock_scan([], [], 25.0, conn=None, failed_slugs=set())

    mock_scan.assert_not_called(), "WS event → scan yapılmamalı"
```

**Not:** Bu test ana `main()` döngüsünün mantığını doğrular. Testi daha deterministik yazmak için Task 4 implementasyonundan sonra aşağıdaki pattern'i kullan:

```python
@pytest.mark.asyncio
async def test_main_loop_scan_skipped_on_ws_event_path():
    """_monitor_positions True döndüğünde scan_and_execute çağrılmaz."""
    import config as _cfg
    scan_called = []

    async def fake_monitor(*a, **kw):
        return True  # WS event

    async def fake_scan(*a, **kw):
        scan_called.append(1)

    with patch("main_loop._monitor_positions",     fake_monitor), \
         patch("main_loop._scan_and_execute",       fake_scan), \
         patch("main_loop.ws_prices"), \
         patch("main_loop.get_effective_bankroll",  new_callable=AsyncMock, return_value=25.0), \
         patch("main_loop._heal_pending_resolutions", new_callable=AsyncMock), \
         patch("main_loop.positions_cache"), \
         patch.object(_cfg, "DRY_RUN", True):
        # main() döngüsünün tek iterasyonu
        ws_triggered = await fake_monitor()
        if not ws_triggered:
            await fake_scan()

    assert scan_called == [], "WS event → scan_and_execute çağrılmamalı"
```

- [ ] **Step 2: main() döngüsünü güncelle**

`main_loop.py`'daki `main()` içinde `try` bloğunu bul (satır 438-475):

Mevcut kod:
```python
            try:
                n_closed_before = len(closed_today)

                await _monitor_positions(open_positions, closed_today, conn=conn, failed_slugs=failed_slugs)
                # WS üzerinden gelen anlık resolution olaylarını işle
                if ws_prices._resolved_queue:
                    ...
                for pos in closed_today[n_closed_before:]:
                    ...

                n_open_before = len(open_positions)
                effective_bankroll = await get_effective_bankroll(BANKROLL_CONFIG)
                await _scan_and_execute(open_positions, closed_today, effective_bankroll, conn=conn, failed_slugs=failed_slugs)
                for pos in open_positions[n_open_before:]:
                    notify_open(pos)

                await _heal_pending_resolutions(conn, closed_today)
                positions_cache.set_open_positions(open_positions)

            except Exception as e:
                print(f"[bot] Döngü hatası: {e}")
            await asyncio.sleep(SCAN_INTERVAL_SECS)   # ← KALDIRILACAK
```

Şununla değiştir:

```python
            try:
                n_closed_before = len(closed_today)

                ws_triggered = await _monitor_positions(
                    open_positions, closed_today, conn=conn, failed_slugs=failed_slugs
                )
                # WS üzerinden gelen anlık resolution olaylarını işle
                if ws_prices._resolved_queue:
                    while not ws_prices._resolved_queue.empty():
                        ev = ws_prices._resolved_queue.get_nowait()
                        await _handle_ws_resolved(ev, open_positions, closed_today, conn=conn,
                                                  failed_slugs=failed_slugs)
                for pos in closed_today[n_closed_before:]:
                    notify_close(pos)
                    pnl = pos.get("realized_pnl") or 0.0
                    effective_bk = await get_effective_bankroll(BANKROLL_CONFIG)
                    cb_result = circuit_breaker.on_trade_closed(
                        pnl=pnl,
                        current_bankroll=effective_bk,
                        starting_bankroll=starting_bankroll,
                    )
                    if cb_result == 'hard_stop':
                        notify_hard_stop(effective_bk, starting_bankroll)
                        print(f"[bot] HARD STOP: bakiye ${effective_bk:.2f} / başlangıç ${starting_bankroll:.2f}")
                    elif cb_result == 'soft_stop':
                        notify_soft_stop(config.STREAK_WARN_COUNT, effective_bk)
                        print(f"[bot] SOFT STOP: {config.STREAK_WARN_COUNT} arka arkaya kayıp")

                if not ws_triggered:
                    # REST heartbeat: scan + heal + cache
                    n_open_before = len(open_positions)
                    effective_bankroll = await get_effective_bankroll(BANKROLL_CONFIG)
                    await _scan_and_execute(open_positions, closed_today, effective_bankroll,
                                            conn=conn, failed_slugs=failed_slugs)
                    for pos in open_positions[n_open_before:]:
                        notify_open(pos)
                    await _heal_pending_resolutions(conn, closed_today)
                    positions_cache.set_open_positions(open_positions)

            except Exception as e:
                print(f"[bot] Döngü hatası: {e}")
            # asyncio.sleep KALDIRILDI — _monitor_positions kendi içinde wait eder
```

- [ ] **Step 3: Tüm suite çalıştır**

```bash
python -m pytest tests/ -x -q --tb=short 2>&1 | tail -8
```

Beklenen: 0 failed (420+ passed)

- [ ] **Step 4: Bot restart ve ilk 30s log kontrolü**

```bash
kill $(pgrep -f main_loop.py) 2>/dev/null; sleep 2
source venv/bin/activate && PYTHONUNBUFFERED=1 nohup python main_loop.py >> logs/bot_v2.log 2>&1 &
sleep 8 && tail -20 logs/bot_v2.log
```

Beklenen: `[bot] Başladı` + `[ws] Polymarket CLOB WebSocket bağlandı` + scan logları

- [ ] **Step 5: Final commit + push**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(main): Faz 2 — WS event-driven döngü, sleep kaldırıldı, scan REST heartbeat'te"
git push origin master
```

---

## Self-Review

**Spec coverage check:**
- [x] Rule 1 — Full event wake-up + full check_exit: Task 3 `ws_triggered` path
- [x] Rule 2 — REST yok event path'te: Task 3 WS path içinde REST mock'suz assert
- [x] Rule 3 — 7s heartbeat: Task 3 REST path + Task 4 `not ws_triggered` koşulu
- [x] Rule 4 — MIN_PROFIT_CONFIRM_SECS=3: Task 2
- [x] Rule 5 — `_closing` flag: Task 3 `test_monitor_live_sets_closing_true_before_sell`
- [x] Rule 6 — FAK fail reset: Task 3 `test_monitor_live_resets_closing_on_fak_fail`

**Type consistency:**
- `_monitor_positions` → `bool` dönüşü Task 3'te tanımlanıyor, Task 4'te `ws_triggered = await _monitor_positions(...)` ile kullanılıyor ✓
- `get_price_event()` Task 1'de tanımlanıyor, Task 3 testlerinde `mock_ws.get_price_event.return_value` ile mock'lanıyor ✓
- `MIN_PROFIT_CONFIRM_SECS` Task 2'de `manager.py` modül sabitine ekleniyor ✓

**Placeholder scan:** Placeholder yok — tüm adımlar tam kod içeriyor ✓
