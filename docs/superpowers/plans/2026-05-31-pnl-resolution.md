# P&L Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** market_expired kapanışlarda Polymarket resolution API'sinden sonucu çekip pm_exit_price ve P&L hesapla.

**Architecture:** `_parse_resolution` (pure parse, test edilebilir) + `fetch_resolved` (HTTP) shortterm.py'de. `_monitor_positions` window=None durumunda önce fetch_resolved dener. `notify_close` P&L bilgisi varsa ekler.

**Tech Stack:** Python 3.12, aiohttp, pytest, AsyncMock

---

## Dosya Haritası

| Dosya | İşlem | Ne değişiyor |
|-------|--------|--------------|
| `data/shortterm.py` | Güncelle | `_parse_resolution()` + `fetch_resolved()` ekle |
| `main_loop.py` | Güncelle | `_monitor_positions` window=None dalı + `fetch_resolved` import |
| `monitor/notifier.py` | Güncelle | `notify_close` P&L satırı ekle |
| `tests/test_shortterm.py` | Güncelle | 3 yeni test |
| `tests/test_main_loop.py` | Güncelle | 1 yeni test |
| `tests/test_monitor.py` | Güncelle | 1 yeni test |

---

## Task 1: `_parse_resolution` + `fetch_resolved` — shortterm.py

**Dosyalar:**
- Güncelle: `data/shortterm.py`
- Güncelle: `tests/test_shortterm.py`

- [ ] **Step 1: 3 testi yaz (başarısız olacak)**

`tests/test_shortterm.py` sonuna ekle:

```python
# ── Resolution ────────────────────────────────────────────────────────────────

def test_parse_resolution_up_wins():
    """outcomePrices["1","0"] → yes_exit=1.0, no_exit=0.0."""
    from data.shortterm import _parse_resolution
    result = _parse_resolution({"outcomePrices": '["1", "0"]'})
    assert result == {"yes_exit": 1.0, "no_exit": 0.0}


def test_parse_resolution_down_wins():
    """outcomePrices["0","1"] → yes_exit=0.0, no_exit=1.0."""
    from data.shortterm import _parse_resolution
    result = _parse_resolution({"outcomePrices": '["0", "1"]'})
    assert result == {"yes_exit": 0.0, "no_exit": 1.0}


def test_parse_resolution_missing_prices_returns_none():
    """outcomePrices alanı yoksa None döner."""
    from data.shortterm import _parse_resolution
    assert _parse_resolution({"closed": True}) is None
```

- [ ] **Step 2: Testleri çalıştır — başarısız olmalı**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/test_shortterm.py::test_parse_resolution_up_wins \
       tests/test_shortterm.py::test_parse_resolution_down_wins \
       tests/test_shortterm.py::test_parse_resolution_missing_prices_returns_none -v
```

Beklenti: **3 FAILED** — `cannot import name '_parse_resolution'`

- [ ] **Step 3: `_parse_resolution` ve `fetch_resolved` yaz**

`data/shortterm.py`'e `find_shortterm` fonksiyonundan ÖNCE ekle:

```python
def _parse_resolution(market: dict) -> dict | None:
    """Market dict'inden YES/NO resolution fiyatlarını çıkarır."""
    import json as _json
    try:
        prices = _json.loads(market["outcomePrices"])
        return {"yes_exit": float(prices[0]), "no_exit": float(prices[1])}
    except (KeyError, IndexError, ValueError, TypeError):
        return None


async def fetch_resolved(slug: str) -> dict | None:
    """Kapanmış market için resolution fiyatlarını döndürür.

    Returns: {"yes_exit": float, "no_exit": float} veya None
    """
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        try:
            async with s.get(GAMMA, params={"slug": slug, "closed": "true"}) as r:
                if r.status != 200:
                    return None
                data = await r.json()
        except Exception:
            return None
    arr = data if isinstance(data, list) else data.get("data", [])
    if not arr:
        return None
    return _parse_resolution(arr[0])
```

- [ ] **Step 4: Testleri çalıştır — geçmeli**

```bash
pytest tests/test_shortterm.py::test_parse_resolution_up_wins \
       tests/test_shortterm.py::test_parse_resolution_down_wins \
       tests/test_shortterm.py::test_parse_resolution_missing_prices_returns_none -v
```

Beklenti: **3 PASSED**

- [ ] **Step 5: Tüm shortterm testleri — regresyon yok**

```bash
pytest tests/test_shortterm.py -v -q
```

Beklenti: hepsi PASSED

- [ ] **Step 6: Commit**

```bash
git add data/shortterm.py tests/test_shortterm.py
git commit -m "feat(shortterm): _parse_resolution + fetch_resolved — P&L için resolution API"
```

---

## Task 2: `_monitor_positions` güncelleme

**Dosyalar:**
- Güncelle: `main_loop.py`
- Güncelle: `tests/test_main_loop.py`

- [ ] **Step 1: Testi yaz (başarısız olacak)**

`tests/test_main_loop.py` import satırına `fetch_resolved` ekle:

```python
from main_loop import _run_council, _scan_and_execute, _monitor_positions, _load_open_positions, fetch_resolved
```

Sonra dosyanın sonuna test ekle:

```python
@pytest.mark.asyncio
async def test_monitor_closes_with_resolution_price_on_yes():
    """window=None iken fetch_resolved sonuç verirse pm_exit_price dolu kapanır (YES)."""
    pos = {**_open_position(), "action": "YES"}
    open_pos = [pos]
    closed = []
    with patch("main_loop.current_price",      new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",      new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=None), \
         patch("main_loop.fetch_resolved",     new_callable=AsyncMock) as mock_res:
        mock_hl.return_value  = 95000.0
        mock_pm.return_value  = {}
        mock_res.return_value = {"yes_exit": 1.0, "no_exit": 0.0}
        await _monitor_positions(open_pos, closed)
    assert len(open_pos) == 0
    assert len(closed) == 1
    assert closed[0]["pm_exit_price"] == 1.0
    assert closed[0]["exit_reason"] == "market_resolved"
```

- [ ] **Step 2: Testi çalıştır — başarısız olmalı**

```bash
pytest tests/test_main_loop.py::test_monitor_closes_with_resolution_price_on_yes -v
```

Beklenti: **FAILED** — `cannot import name 'fetch_resolved'` veya `exit_reason != 'market_resolved'`

- [ ] **Step 3: `main_loop.py`'i güncelle**

Import satırına ekle:

```python
from data.shortterm import fetch_by_slug, fetch_resolved, parse_market_window
```

`_monitor_positions` içinde `if window is None:` bloğunu değiştir:

```python
if window is None:
    resolution = await fetch_resolved(pos["slug"])
    if resolution:
        pm_exit = resolution["yes_exit"] if pos["action"] == "YES" else resolution["no_exit"]
        closed = close_position(pos, "market_resolved", pm_exit_price=pm_exit)
    else:
        closed = close_position(pos, "market_expired")
    await log_position_close(conn, closed)
    open_positions.remove(pos)
    closed_today.append(closed)
    continue
```

- [ ] **Step 4: Testi çalıştır — geçmeli**

```bash
pytest tests/test_main_loop.py::test_monitor_closes_with_resolution_price_on_yes -v
```

Beklenti: **PASSED**

- [ ] **Step 5: Tüm main_loop testleri**

```bash
pytest tests/test_main_loop.py -v -q
```

Beklenti: hepsi PASSED

- [ ] **Step 6: Commit**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(main_loop): market_resolved — resolution price ile pozisyon kapat"
```

---

## Task 3: `notify_close` P&L satırı

**Dosyalar:**
- Güncelle: `monitor/notifier.py`
- Güncelle: `tests/test_monitor.py`

- [ ] **Step 1: Testi yaz (başarısız olacak)**

`tests/test_monitor.py` sonuna ekle:

```python
def test_notify_close_shows_pnl_when_exit_price_known():
    """pm_exit_price bilinince mesajda P&L satırı görünür."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_close({
            "asset": "ETH", "action": "NO",
            "exit_reason": "market_resolved",
            "pm_entry_price": 0.31,
            "pm_exit_price": 0.0,
            "position_usd": 50.0,
        })
    msg = mock_send.call_args[0][0]
    assert "P&L" in msg
    assert "-" in msg  # kayıp


def test_notify_close_no_pnl_when_exit_price_missing():
    """pm_exit_price yoksa P&L satırı olmaz."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_close({
            "asset": "BTC", "action": "YES",
            "exit_reason": "market_expired",
            "pm_entry_price": 0.35,
            "pm_exit_price": None,
            "position_usd": 25.0,
        })
    msg = mock_send.call_args[0][0]
    assert "P&L" not in msg
```

- [ ] **Step 2: Testleri çalıştır — başarısız olmalı**

```bash
pytest tests/test_monitor.py::test_notify_close_shows_pnl_when_exit_price_known \
       tests/test_monitor.py::test_notify_close_no_pnl_when_exit_price_missing -v
```

Beklenti: **2 FAILED** — "P&L" mesajda yok

- [ ] **Step 3: `notify_close` güncelle**

`monitor/notifier.py`'deki `notify_close` fonksiyonunu değiştir:

```python
def notify_close(pos: dict) -> None:
    msg = (
        f"KAPANDI {pos['asset']} {pos['action']}\n"
        f"Sebep: {pos.get('exit_reason', '?')}"
    )
    entry    = pos.get("pm_entry_price")
    exit_p   = pos.get("pm_exit_price")
    pos_usd  = pos.get("position_usd", 0)
    if entry and exit_p is not None:
        pnl  = (exit_p - entry) / entry * pos_usd
        sign = "+" if pnl >= 0 else ""
        icon = "✅" if pnl >= 0 else "❌"
        msg += f"\nP&L: {sign}${pnl:.2f} {icon}"
    send_telegram(msg)
```

- [ ] **Step 4: Testleri çalıştır — geçmeli**

```bash
pytest tests/test_monitor.py::test_notify_close_shows_pnl_when_exit_price_known \
       tests/test_monitor.py::test_notify_close_no_pnl_when_exit_price_missing -v
```

Beklenti: **2 PASSED**

- [ ] **Step 5: Tüm monitor testleri**

```bash
pytest tests/test_monitor.py -v -q
```

Beklenti: hepsi PASSED

- [ ] **Step 6: Commit**

```bash
git add monitor/notifier.py tests/test_monitor.py
git commit -m "feat(notifier): notify_close P&L satırı — kazanç/kayıp Telegram'da görünür"
```

---

## Task 4: Tam suite + bot restart

- [ ] **Step 1: Tam test suite çalıştır**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/ --asyncio-mode=auto -q
```

Beklenti: tüm testler PASSED, EXIT:0

- [ ] **Step 2: Geçmiş kapanan pozisyon için resolution test et**

```bash
source venv/bin/activate && python -c "
import asyncio
from data.shortterm import fetch_resolved

async def r():
    result = await fetch_resolved('eth-updown-15m-1780174800')
    print('Resolution:', result)
    if result:
        pos_usd = 50.0
        entry   = 0.31
        exit_p  = result['no_exit']  # NO pozisyonumuz
        pnl     = (exit_p - entry) / entry * pos_usd
        print(f'P&L: \${pnl:.2f}')

asyncio.run(r())
"
```

Beklenti: `Resolution: {'yes_exit': 1.0, 'no_exit': 0.0}` ve `P&L: -$50.00`

- [ ] **Step 3: Bot'u yeni kodla yeniden başlat**

```bash
tmux send-keys -t mispricing C-c && sleep 1
tmux send-keys -t mispricing "python -u main_loop.py" Enter
sleep 3
tmux capture-pane -t mispricing -p -S -3
```

Beklenti: `[bot] Başladı — DRY_RUN=True`, hata yok

- [ ] **Step 4: Memory güncelle**

`/root/.claude/projects/-root-mispricing-agent/memory/project_overview.md` içinde:
- P&L resolution ✅ olarak işaretle
- Sıradaki adımı güncelle
