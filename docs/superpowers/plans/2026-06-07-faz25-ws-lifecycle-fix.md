# Faz 2.5 WS Lifecycle Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** WS bağlantısını Polymarket API dokümanına tam uyumlu hale getir — token yokken bağlanma, ilk PING 1s'de at, update subscription format, pozisyon kapanınca unsubscribe, circuit breaker sadece gerçek abonelikte saysın.

**Architecture:** `data/ws_prices.py` 4 cerrahi değişiklik alır (guard, ping, format, unsubscribe). `main_loop.py` pozisyon kapanma noktalarına `ws_prices.unsubscribe()` çağrısı alır. Tüm değişiklikler TDD: önce kırmızı test, sonra yeşil kod.

**Tech Stack:** Python asyncio, websockets kütüphanesi, pytest-asyncio, unittest.mock

---

## File Structure

| Dosya | Değişiklik |
|-------|-----------|
| `data/ws_prices.py` | Guard, PING_INTERVAL=8, _ping_loop, _flush_pending(initial_connect), unsubscribe(), _pending_unsub, circuit breaker had_subs |
| `tests/test_ws_prices.py` | 9 yeni test |
| `main_loop.py` | 4 close noktasına ws_prices.unsubscribe() çağrısı |
| `tests/test_main_loop.py` | 1 yeni test (unsubscribe-on-close) |

---

## Task 1: Guard + Circuit Breaker + PING Timing (ws_prices.py)

**Files:**
- Modify: `data/ws_prices.py:13,68-91,232-238`
- Test: `tests/test_ws_prices.py`

### Step 1.1: RED — 4 failing test yaz

- [ ] `tests/test_ws_prices.py` sonuna ekle:

```python
# ── Faz 2.5: Guard + PING ──────────────────────────────────────────────────────

def test_ping_interval_is_8():
    """PING_INTERVAL 8s olmalı — sunucunun 10s limitinin 2s öncesi."""
    assert ws.PING_INTERVAL == 8, "PING_INTERVAL 8 olmalı"


def test_ping_loop_first_ping_at_1s():
    """_ping_loop: ilk PING 1s sonra (PING_INTERVAL değil) gönderilmeli."""
    import inspect
    source = inspect.getsource(ws._ping_loop)
    assert "asyncio.sleep(1)" in source, \
        "_ping_loop içinde 1s ilk ping bekleme olmalı"


def test_run_has_no_token_guard():
    """run(): token yokken _connect_and_run çağrılmamalı — guard olmalı."""
    import inspect
    source = inspect.getsource(ws.run)
    assert "not _pending and not _subscribed" in source, \
        "run() içinde 'while not _pending and not _subscribed' guard olmalı"


def test_run_circuit_breaker_uses_had_subs():
    """run(): circuit breaker yalnızca gerçekten subscribed bağlantıları saymalı."""
    import inspect
    source = inspect.getsource(ws.run)
    assert "had_subs" in source, \
        "run() içinde had_subs flag'i ile circuit breaker koruması olmalı"
```

- [ ] Testleri çalıştır — FAIL bekleniyor:

```bash
cd /root/mispricing_agent
pytest tests/test_ws_prices.py::test_ping_interval_is_8 \
       tests/test_ws_prices.py::test_ping_loop_first_ping_at_1s \
       tests/test_ws_prices.py::test_run_has_no_token_guard \
       tests/test_ws_prices.py::test_run_circuit_breaker_uses_had_subs -v
```

Expected: 4x FAIL

### Step 1.2: GREEN — ws_prices.py değişiklikleri

- [ ] `data/ws_prices.py` satır 13'teki `PING_INTERVAL = 10` → `8`:

```python
PING_INTERVAL      = 8    # saniye — sunucunun 10s limitinin 2s öncesi
```

- [ ] `run()` fonksiyonunu (satır 68-91) tamamen şununla değiştir:

```python
async def run(initial_token_ids: list[str] | None = None) -> None:
    """Ana WS döngüsü. asyncio.create_task ile çalıştırılır."""
    global _resolved_queue, _short_lived_count
    if _resolved_queue is None:
        _resolved_queue = asyncio.Queue()
    if initial_token_ids:
        subscribe(initial_token_ids)
    while True:
        # Token yoksa bekleme — no-sub kill önlemi
        while not _pending and not _subscribed:
            await asyncio.sleep(1)
        had_subs = bool(_subscribed or _pending)
        t_start = time.time()
        try:
            await _connect_and_run()
            _short_lived_count = 0  # temiz çıkış → sayacı sıfırla
        except Exception as e:
            lifetime = time.time() - t_start
            etype    = type(e).__name__
            print(f"[ws] Bağlantı koptu ({lifetime:.1f}s): {etype}: {e} — {RECONNECT_DELAY}s sonra yeniden deneniyor")
            if lifetime < _SHORT_LIVED_SECS and had_subs:
                _short_lived_count += 1
                if _short_lived_count >= _CIRCUIT_BREAKER_N:
                    _warn_ws_circuit_breaker(_short_lived_count)
                    _short_lived_count = 0
            else:
                _short_lived_count = 0
        await asyncio.sleep(RECONNECT_DELAY)
```

- [ ] `_ping_loop()` fonksiyonunu (satır 232-238) tamamen şununla değiştir:

```python
async def _ping_loop(ws) -> None:
    # İlk PING: subscribe sonrası hemen (1s) — sunucu 10s içinde PING bekliyor
    await asyncio.sleep(1)
    try:
        await ws.send("PING")
    except Exception:
        return
    # Sonra her 8s'de bir (10s limitin 2s öncesi)
    while True:
        await asyncio.sleep(PING_INTERVAL)
        try:
            await ws.send("PING")
        except Exception:
            break
```

- [ ] Testleri çalıştır — PASS bekleniyor:

```bash
pytest tests/test_ws_prices.py::test_ping_interval_is_8 \
       tests/test_ws_prices.py::test_ping_loop_first_ping_at_1s \
       tests/test_ws_prices.py::test_run_has_no_token_guard \
       tests/test_ws_prices.py::test_run_circuit_breaker_uses_had_subs -v
```

Expected: 4x PASS

- [ ] Tüm test suite'ini çalıştır — hiçbir şey bozulmamalı:

```bash
pytest tests/test_ws_prices.py -v
```

Expected: Tüm testler PASS

### Step 1.3: Commit

```bash
git add data/ws_prices.py tests/test_ws_prices.py
git commit -m "feat(ws): Faz 2.5 guard+ping — no-token no-connect, 1s ilk ping, 8s interval, circuit breaker had_subs"
```

---

## Task 2: Subscription Format Fix + unsubscribe() (ws_prices.py)

**Files:**
- Modify: `data/ws_prices.py:19-27,55-58,166-178,241-247`
- Test: `tests/test_ws_prices.py`

### Step 2.1: RED — 6 failing test yaz

- [ ] `tests/test_ws_prices.py` sonuna ekle:

```python
# ── Faz 2.5: Subscription Format + Unsubscribe ───────────────────────────────

def test_unsubscribe_removes_from_subscribed():
    """unsubscribe(): _subscribed'den tokenı çıkarır."""
    _reset()
    ws._subscribed.add("tok_open")
    ws.unsubscribe(["tok_open"])
    assert "tok_open" not in ws._subscribed, "_subscribed'den silinmeli"


def test_unsubscribe_removes_from_pending():
    """unsubscribe(): _pending'den de kaldırır."""
    _reset()
    ws._pending.add("tok_pend")
    ws.unsubscribe(["tok_pend"])
    assert "tok_pend" not in ws._pending, "_pending'den silinmeli"


def test_unsubscribe_adds_to_pending_unsub():
    """unsubscribe(): _pending_unsub kuyruğuna ekler (WS'e mesaj gönderilecek)."""
    _reset()
    ws._subscribed.add("tok_open")
    ws.unsubscribe(["tok_open"])
    assert "tok_open" in ws._pending_unsub, "_pending_unsub'a eklenmeli"


def test_unsubscribe_skips_empty_strings():
    """unsubscribe(): boş string'leri yoksayar."""
    _reset()
    ws.unsubscribe(["", None, "tok_valid"])
    assert "" not in ws._pending_unsub
    assert None not in ws._pending_unsub


@pytest.mark.asyncio
async def test_flush_pending_uses_initial_format_on_connect():
    """_flush_pending(initial_connect=True): type=market formatı kullanır."""
    import json
    _reset()
    ws.subscribe(["tok_init"])
    ws_mock = AsyncMock()
    await ws._flush_pending(ws_mock, initial_connect=True)
    assert ws_mock.send.called
    payload = json.loads(ws_mock.send.call_args[0][0])
    assert payload.get("type") == "market", "initial connect → type=market"
    assert "assets_ids" in payload
    assert "operation" not in payload, "initial connect → operation olmamalı"


@pytest.mark.asyncio
async def test_flush_pending_uses_update_format_on_existing_connection():
    """_flush_pending(initial_connect=False): operation=subscribe formatı kullanır."""
    import json
    _reset()
    ws.subscribe(["tok_update"])
    ws_mock = AsyncMock()
    await ws._flush_pending(ws_mock, initial_connect=False)
    assert ws_mock.send.called
    payload = json.loads(ws_mock.send.call_args[0][0])
    assert payload.get("operation") == "subscribe", "update → operation=subscribe"
    assert "assets_ids" in payload
    assert "type" not in payload, "update → type olmamalı"


@pytest.mark.asyncio
async def test_flush_pending_sends_unsubscribe_message():
    """_flush_pending: _pending_unsub varsa operation=unsubscribe mesajı gönderir."""
    import json
    _reset()
    ws._pending_unsub.add("tok_unsub")
    ws_mock = AsyncMock()
    await ws._flush_pending(ws_mock, initial_connect=False)
    assert ws_mock.send.called
    # İlk çağrı unsubscribe mesajı olmalı
    first_call = ws_mock.send.call_args_list[0][0][0]
    payload = json.loads(first_call)
    assert payload.get("operation") == "unsubscribe"
    assert "tok_unsub" in payload.get("assets_ids", [])
```

- [ ] `_reset()` helper'ını güncelle — `_pending_unsub.clear()` ekle:

```python
def _reset():
    ws._cache.clear()
    ws._subscribed.clear()
    ws._pending.clear()
    ws._pending_unsub.clear()
    ws._resolved_queue = None
```

- [ ] Testleri çalıştır — FAIL bekleniyor:

```bash
pytest tests/test_ws_prices.py::test_unsubscribe_removes_from_subscribed \
       tests/test_ws_prices.py::test_unsubscribe_removes_from_pending \
       tests/test_ws_prices.py::test_unsubscribe_adds_to_pending_unsub \
       tests/test_ws_prices.py::test_unsubscribe_skips_empty_strings \
       tests/test_ws_prices.py::test_flush_pending_uses_initial_format_on_connect \
       tests/test_ws_prices.py::test_flush_pending_uses_update_format_on_existing_connection \
       tests/test_ws_prices.py::test_flush_pending_sends_unsubscribe_message -v
```

Expected: 7x FAIL (`AttributeError: module has no attribute '_pending_unsub'` veya benzeri)

### Step 2.2: GREEN — ws_prices.py değişiklikleri

- [ ] Modül değişkenleri bloğuna (satır 19-27 arası) `_pending_unsub` ekle:

```python
_cache:    dict[str, dict]       = {}   # token_id → {best_bid, best_ask, spread, ts}
_subscribed: set[str]            = set()
_pending:    set[str]            = set()
_pending_unsub: set[str]         = set()   # unsubscribe kuyruğu
_ws                              = None
_resolved_queue: asyncio.Queue | None = None
_price_event: asyncio.Event | None = None
_reconnect_count: int            = 0
_short_lived_count: int          = 0   # ard arda kısa bağlantı sayısı
```

- [ ] `subscribe()` fonksiyonundan (satır 55-57) SONRASINA `unsubscribe()` fonksiyonu ekle:

```python
def unsubscribe(token_ids: list[str]) -> None:
    """Token ID'lerini abonelikten çıkar. WS aktifse 2s içinde unsubscribe gönderilir."""
    for tid in token_ids:
        if tid:
            _subscribed.discard(tid)
            _pending.discard(tid)
            _pending_unsub.add(tid)
```

- [ ] `_flush_pending()` fonksiyonunu (satır 166-178) tamamen şununla değiştir:

```python
async def _flush_pending(ws, *, initial_connect: bool = True) -> None:
    """_pending tokenlarını subscribe et + _pending_unsub tokenlarını unsubscribe et.

    initial_connect=True  → ilk bağlantı formatı: {"assets_ids": [...], "type": "market"}
    initial_connect=False → update formatı: {"operation": "subscribe", "assets_ids": [...]}
    """
    # Önce unsubscribe mesajlarını gönder
    if _pending_unsub:
        unsub_batch = list(_pending_unsub)
        _pending_unsub.clear()
        msg = json.dumps({"operation": "unsubscribe", "assets_ids": unsub_batch})
        print(f"[ws] Unsubscribe: {len(unsub_batch)} token")
        await ws.send(msg)

    if not _pending:
        return
    batch = list(_pending)
    _pending.clear()          # atomic clear before await — no TOCTOU
    if initial_connect:
        msg = json.dumps({
            "assets_ids":             batch,
            "type":                   "market",
            "custom_feature_enabled": True,
        })
        print(f"[ws] Subscribe (initial): {len(batch)} token, ilk: {batch[:3]}")
    else:
        msg = json.dumps({"operation": "subscribe", "assets_ids": batch})
        print(f"[ws] Subscribe (update): {len(batch)} token, ilk: {batch[:3]}")
    await ws.send(msg)
    _subscribed.update(batch)
```

- [ ] `_connect_and_run()` içindeki `await _flush_pending(ws)` çağrısını güncelle — `initial_connect=True` parametresini ekle:

Satır 197'deki:
```python
await _flush_pending(ws)
```
→
```python
await _flush_pending(ws, initial_connect=True)
```

- [ ] `_pending_flush_loop()` içindeki çağrıyı güncelle — `initial_connect=False` ekle:

```python
async def _pending_flush_loop(ws) -> None:
    while True:
        await asyncio.sleep(2)
        try:
            await _flush_pending(ws, initial_connect=False)
        except Exception:
            break
```

- [ ] Testleri çalıştır — PASS bekleniyor:

```bash
pytest tests/test_ws_prices.py::test_unsubscribe_removes_from_subscribed \
       tests/test_ws_prices.py::test_unsubscribe_removes_from_pending \
       tests/test_ws_prices.py::test_unsubscribe_adds_to_pending_unsub \
       tests/test_ws_prices.py::test_unsubscribe_skips_empty_strings \
       tests/test_ws_prices.py::test_flush_pending_uses_initial_format_on_connect \
       tests/test_ws_prices.py::test_flush_pending_uses_update_format_on_existing_connection \
       tests/test_ws_prices.py::test_flush_pending_sends_unsubscribe_message -v
```

Expected: 7x PASS

- [ ] Tüm ws test suite'ini çalıştır:

```bash
pytest tests/test_ws_prices.py -v
```

Expected: Tüm testler PASS

### Step 2.3: Commit

```bash
git add data/ws_prices.py tests/test_ws_prices.py
git commit -m "feat(ws): Faz 2.5 subscription format + unsubscribe — initial/update ayrımı, _pending_unsub kuyruğu"
```

---

## Task 3: main_loop.py — Unsubscribe on Position Close

**Files:**
- Modify: `main_loop.py` (4 nokta)
- Test: `tests/test_main_loop.py`

### Step 3.1: RED — 1 failing test yaz

- [ ] `tests/test_main_loop.py` dosyasında `default_ws_prices` fixture'ını bul (satır ~18-40).
  `mock_ws.subscribe.return_value = None` satırından SONRASINA şunu ekle:

```python
        mock_ws.unsubscribe.return_value = None
```

- [ ] Aynı dosyaya yeni test ekle (dosya sonuna):

```python
# ── Faz 2.5: unsubscribe-on-close ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_monitor_calls_ws_unsubscribe_on_position_close(default_ws_prices):
    """Pozisyon kapanınca ws_prices.unsubscribe() yes/no token'larıyla çağrılır."""
    import main_loop as _ml
    import time as _time
    _ml._last_rest_ts = 0  # REST heartbeat tetiklensin

    pos = {
        "position_id":    "unsub-test-pos",
        "slug":           "btc-unsub-test",
        "asset":          "BTC",
        "action":         "YES",
        "pm_entry_price": 0.60,
        "fair_value":     0.75,
        "ref_price":      60000,
        "edge":           0.15,
        "position_usd":   1.25,
        "kelly_f":        0.1,
        "confidence_score": 80,
        "shares":         2.0,
        "yes_token_id":   "yes_tok_unsub",
        "no_token_id":    "no_tok_unsub",
        "order_id":       "ord_unsub",
        "seq_no":         99,
        "entry_hl_price": 60000,
        "opened_at":      "2026-06-07T00:00:00+00:00",
    }
    open_positions = [pos]
    closed_today = []

    with patch("main_loop.check_exit", return_value="stop_loss_hit"), \
         patch("main_loop.get_window", new_callable=AsyncMock,
               return_value={"seconds_remaining": 120, "best_bid": 0.40,
                             "best_ask": 0.42, "condition_id": "0xabc",
                             "slug": "btc-unsub-test"}), \
         patch("main_loop.current_price", new_callable=AsyncMock,
               return_value=60000), \
         patch("main_loop.sell_position", new_callable=AsyncMock,
               return_value=(0.40, 2.0)), \
         patch("main_loop.log_position_close", new_callable=AsyncMock), \
         patch("main_loop.notify_close"):
        await _monitor_positions(open_positions, closed_today, conn=None)

    default_ws_prices.unsubscribe.assert_called_once()
    unsubbed = default_ws_prices.unsubscribe.call_args[0][0]
    assert "yes_tok_unsub" in unsubbed, "yes_token_id unsubscribe edilmeli"
    assert "no_tok_unsub"  in unsubbed, "no_token_id unsubscribe edilmeli"
```

- [ ] Testi çalıştır — FAIL bekleniyor:

```bash
pytest tests/test_main_loop.py::test_monitor_calls_ws_unsubscribe_on_position_close -v
```

Expected: FAIL (`AssertionError: Expected 'unsubscribe' to have been called once.`)

### Step 3.2: GREEN — main_loop.py 4 close noktasına unsubscribe ekle

Her `open_positions.remove(pos)` çağrısının hemen SONRASINA şu satırı ekle:

```python
ws_prices.unsubscribe([t for t in (pos.get("yes_token_id"), pos.get("no_token_id")) if t])
```

**Nokta 1** — `_handle_ws_resolved` (satır ~231):

```python
        await log_position_close(conn, closed)
        open_positions.remove(pos)
        ws_prices.unsubscribe([t for t in (pos.get("yes_token_id"), pos.get("no_token_id")) if t])
        closed_today.append(closed)
```

**Nokta 2** — `_do_flatten` (satır ~338):

```python
                open_positions.remove(pos)
                ws_prices.unsubscribe([t for t in (pos.get("yes_token_id"), pos.get("no_token_id")) if t])
                closed_today.append(closed_dict)
```

**Nokta 3** — `_monitor_positions` market_resolved path (satır ~422):

```python
                        await log_position_close(conn, closed)
                        open_positions.remove(pos)
                        ws_prices.unsubscribe([t for t in (pos.get("yes_token_id"), pos.get("no_token_id")) if t])
                        closed_today.append(closed)
```

**Nokta 4** — `_monitor_positions` normal exit path (satır ~500):

```python
                open_positions.remove(pos)
                ws_prices.unsubscribe([t for t in (pos.get("yes_token_id"), pos.get("no_token_id")) if t])
                closed_today.append(closed)
```

- [ ] Testi çalıştır — PASS bekleniyor:

```bash
pytest tests/test_main_loop.py::test_monitor_calls_ws_unsubscribe_on_position_close -v
```

Expected: PASS

- [ ] Tüm test suite'ini çalıştır:

```bash
pytest tests/ -x -q 2>&1 | tail -5
```

Expected: Tüm testler PASS, 0 error

### Step 3.3: Commit + bot restart

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(ws): Faz 2.5 unsubscribe-on-close — pozisyon kapanınca WS temizliği (4 nokta)"
```

- [ ] Botu yeniden başlat ve WS loglarını izle:

```bash
kill $(pgrep -f "main_loop.py") 2>/dev/null
sleep 2
screen -S bot -dm bash -c 'PYTHONUNBUFFERED=1 python main_loop.py >> logs/bot_v2.log 2>&1'
sleep 15 && tail -20 logs/bot_v2.log
```

- [ ] Log'da görülmesi beklenenler (pozisyon yoksa):
  - `[ws] WARNING: token listesi boş` → GÖRÜNMEMELI (guard aktif)
  - `[ws] Polymarket CLOB WebSocket bağlandı (#1)` → GÖRÜNMEMELI (guard aktif)
  - Sadece `[scan HH:MM:SS] edge yok` döngüsü

- [ ] Log'da görülmesi beklenenler (pozisyon açılınca):
  - `[ws] Polymarket CLOB WebSocket bağlandı (#1)`
  - `[ws] Subscribe (initial): N token, ilk: [...]`
  - Sonraki reconnect'lerde `[ws] Subscribe (initial):` tekrar görülmeli

---

## Doğrulama Kontrol Listesi

- [ ] `pytest tests/ -q` — tümü PASS
- [ ] Log'da "WARNING: token listesi boş" yok (token yokken WS açılmıyor)
- [ ] Bağlantı 10-11s değil 30s+ sürüyor (pozisyon varken test et)
- [ ] Circuit breaker Telegram spam yok
- [ ] `git log --oneline -3` — 3 commit görünüyor
