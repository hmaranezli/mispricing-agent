# HL Fiyat Bildirimleri + Fill Rate İyileştirme

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Telegram bildirimlerine gerçek HL giriş/çıkış fiyatı ekle; LIVE fill rate'i iyileştirmek için CLOB order fiyatına +0.01 premium uygula.

**Architecture:** Schema migration → DB logger → executor/clob_executor → position/manager → main_loop → notifier. Her katman bir öncekine bağımlı; sıra önemli. DRY_RUN etkilenmez (sadece notifier görüntüsü değişir). PRICE_PREMIUM sadece clob_executor'da, diğer dosyalara dokunmaz.

**Tech Stack:** aiosqlite, SQLite ALTER TABLE migration, Python async, pytest-asyncio

---

## Dosya Haritası

| Dosya | Değişiklik |
|-------|-----------|
| `db/schema.py` | `_MIGRATIONS` → 2 yeni kolon ekle |
| `db/logger.py` | `log_position_open`, `log_position_close`, `patch_position_resolution` |
| `execution/executor.py` | position dict'e `entry_hl_price` ekle |
| `execution/clob_executor.py` | `PRICE_PREMIUM` sabiti + order fiyatı + `entry_hl_price` |
| `position/manager.py` | `close_position` → `exit_hl_price` parametresi |
| `main_loop.py` | `_load_open_positions`, `_monitor_positions`, `_heal_pending_resolutions` |
| `monitor/notifier.py` | `notify_open`, `notify_close`, `notify_resolved_late` |
| `tests/test_db.py` | yeni kolon testleri |
| `tests/test_executor.py` | `entry_hl_price` testi |
| `tests/test_clob_executor.py` | price premium + `entry_hl_price` testleri |
| `tests/test_position.py` | `exit_hl_price` parametresi testi |
| `tests/test_main_loop.py` | monitor + heal HL fiyat testleri |
| `tests/test_monitor.py` | bildirim format testleri |

---

## Task 1: Schema Migration

**Files:**
- Modify: `db/schema.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_db.py` dosyasına ekle:

```python
@pytest.mark.asyncio
async def test_positions_has_entry_exit_hl_price_columns():
    """positions tablosunda entry_hl_price ve exit_hl_price kolonları olmalı."""
    import aiosqlite
    from db.schema import init_schema
    async with aiosqlite.connect(":memory:") as conn:
        await init_schema(conn)
        async with conn.execute("PRAGMA table_info(positions)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
    assert "entry_hl_price" in cols, "entry_hl_price kolonu eksik"
    assert "exit_hl_price" in cols, "exit_hl_price kolonu eksik"
```

- [ ] **Step 2: Testi çalıştır, FAIL bekle**

```bash
source venv/bin/activate && python -m pytest tests/test_db.py::test_positions_has_entry_exit_hl_price_columns -v
```

Beklenen: `FAIL — AssertionError: entry_hl_price kolonu eksik`

- [ ] **Step 3: Migration ekle**

`db/schema.py` → `_MIGRATIONS` listesine iki satır ekle (mevcut listeye append):

```python
_MIGRATIONS = [
    "ALTER TABLE positions ADD COLUMN ref_price REAL",
    "ALTER TABLE positions ADD COLUMN edge REAL",
    "ALTER TABLE positions ADD COLUMN realized_pnl REAL",
    # CLOB API kolonları:
    "ALTER TABLE positions ADD COLUMN shares REAL",
    "ALTER TABLE positions ADD COLUMN order_id TEXT",
    "ALTER TABLE positions ADD COLUMN yes_token_id TEXT",
    "ALTER TABLE positions ADD COLUMN no_token_id TEXT",
    # Sira numarasi:
    "ALTER TABLE positions ADD COLUMN seq_no INTEGER",
    # HL fiyat kolonları:
    "ALTER TABLE positions ADD COLUMN entry_hl_price REAL",
    "ALTER TABLE positions ADD COLUMN exit_hl_price REAL",
]
```

- [ ] **Step 4: Test geçsin**

```bash
python -m pytest tests/test_db.py::test_positions_has_entry_exit_hl_price_columns -v
```

Beklenen: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add db/schema.py tests/test_db.py
git commit -m "feat(schema): entry_hl_price ve exit_hl_price kolonları ekle"
```

---

## Task 2: db/logger.py Güncellemeleri

**Files:**
- Modify: `db/logger.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Failing testler yaz**

`tests/test_db.py` dosyasına ekle:

```python
@pytest.mark.asyncio
async def test_log_position_open_saves_entry_hl_price():
    """log_position_open → entry_hl_price DB'ye kaydedilmeli."""
    import aiosqlite
    from db.schema import init_schema
    from db.logger import log_position_open
    pos = {
        "position_id": "hl-001", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-06-03T10:00:00+00:00",
        "entry_hl_price": 66500.0,
    }
    async with aiosqlite.connect(":memory:") as conn:
        await init_schema(conn)
        await log_position_open(conn, pos)
        async with conn.execute(
            "SELECT entry_hl_price FROM positions WHERE position_id='hl-001'"
        ) as cur:
            row = await cur.fetchone()
    assert row is not None
    assert abs(row[0] - 66500.0) < 0.01, f"entry_hl_price={row[0]}, beklenen 66500.0"


@pytest.mark.asyncio
async def test_log_position_close_saves_exit_hl_price():
    """log_position_close → exit_hl_price DB'ye kaydedilmeli."""
    import aiosqlite
    from db.schema import init_schema
    from db.logger import log_position_open, log_position_close
    pos = {
        "position_id": "hl-002", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-06-03T10:00:00+00:00",
        "entry_hl_price": 66500.0,
    }
    closed = {
        **pos, "status": "closed", "exit_reason": "thesis_invalidated",
        "closed_at": "2026-06-03T10:14:00+00:00",
        "pm_exit_price": 0.72, "exit_hl_price": 66502.0,
    }
    async with aiosqlite.connect(":memory:") as conn:
        await init_schema(conn)
        await log_position_open(conn, pos)
        await log_position_close(conn, closed)
        async with conn.execute(
            "SELECT exit_hl_price FROM positions WHERE position_id='hl-002'"
        ) as cur:
            row = await cur.fetchone()
    assert row is not None
    assert abs(row[0] - 66502.0) < 0.01, f"exit_hl_price={row[0]}, beklenen 66502.0"


@pytest.mark.asyncio
async def test_patch_position_resolution_saves_exit_hl_price():
    """patch_position_resolution → exit_hl_price ile çağrılınca DB'ye kaydedilmeli."""
    import aiosqlite
    from db.schema import init_schema
    from db.logger import log_position_open, patch_position_resolution
    pos = {
        "position_id": "hl-003", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-06-03T10:00:00+00:00",
    }
    async with aiosqlite.connect(":memory:") as conn:
        await init_schema(conn)
        await log_position_open(conn, pos)
        await conn.execute(
            "UPDATE positions SET status='closed', pm_exit_price=NULL WHERE position_id='hl-003'"
        )
        await conn.commit()
        await patch_position_resolution(conn, "hl-003", 1.0, 1.07, exit_hl_price=66510.0)
        async with conn.execute(
            "SELECT exit_hl_price FROM positions WHERE position_id='hl-003'"
        ) as cur:
            row = await cur.fetchone()
    assert row is not None
    assert abs(row[0] - 66510.0) < 0.01
```

- [ ] **Step 2: Çalıştır, FAIL bekle**

```bash
python -m pytest tests/test_db.py::test_log_position_open_saves_entry_hl_price tests/test_db.py::test_log_position_close_saves_exit_hl_price tests/test_db.py::test_patch_position_resolution_saves_exit_hl_price -v
```

Beklenen: 3 FAIL

- [ ] **Step 3: db/logger.py güncelle**

`log_position_open` fonksiyonunu bul, INSERT sorgusunu güncelle:

```python
async def log_position_open(conn, position: dict) -> None:
    if conn is None:
        return
    async with conn.execute("SELECT COALESCE(MAX(seq_no), 0) + 1 FROM positions") as cur:
        row = await cur.fetchone()
    seq_no = row[0] if row else 1
    position["seq_no"] = seq_no
    await conn.execute(
        """INSERT OR IGNORE INTO positions
               (position_id, ts_open, slug, asset, action, pm_entry_price,
                fair_value, ref_price, edge, position_usd, kelly_f,
                confidence_score, status, dry_run,
                shares, order_id, yes_token_id, no_token_id, seq_no,
                entry_hl_price)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?)""",
        (
            position["position_id"],
            position.get("opened_at", datetime.now(timezone.utc).isoformat()),
            position.get("slug", ""),
            position.get("asset", ""),
            position.get("action", ""),
            position.get("pm_entry_price"),
            position.get("fair_value"),
            position.get("ref_price"),
            position.get("edge"),
            position.get("position_usd"),
            position.get("kelly_f"),
            position.get("confidence_score"),
            1 if config.DRY_RUN else 0,
            position.get("shares"),
            position.get("order_id"),
            position.get("yes_token_id"),
            position.get("no_token_id"),
            seq_no,
            position.get("entry_hl_price"),
        ),
    )
    await conn.commit()
```

`log_position_close` fonksiyonunu bul, UPDATE sorgusunu güncelle:

```python
async def log_position_close(conn, position: dict) -> None:
    if conn is None:
        return
    entry   = position.get("pm_entry_price")
    exit_p  = position.get("pm_exit_price")
    pos_usd = position.get("position_usd", 0)
    if entry and exit_p is not None:
        realized_pnl = (exit_p - entry) / entry * pos_usd
    else:
        realized_pnl = None
    await conn.execute(
        """UPDATE positions
           SET status='closed', ts_close=?, pm_exit_price=?,
               exit_reason=?, realized_pnl=?, exit_hl_price=?
           WHERE position_id=?""",
        (
            position.get("closed_at", datetime.now(timezone.utc).isoformat()),
            exit_p,
            position.get("exit_reason"),
            realized_pnl,
            position.get("exit_hl_price"),
            position["position_id"],
        ),
    )
    await conn.commit()
```

`patch_position_resolution` imzasını ve sorgusunu güncelle:

```python
async def patch_position_resolution(
    conn,
    position_id:   str,
    pm_exit_price: float,
    realized_pnl:  float,
    exit_reason:   str = "market_resolved_late",
    exit_hl_price: float | None = None,
) -> None:
    """Kapanmış pozisyonun exit fiyatı ve P&L'ini günceller (market_expired → resolved_late)."""
    if conn is None:
        return
    await conn.execute(
        """UPDATE positions
           SET pm_exit_price=?, realized_pnl=?, exit_reason=?, exit_hl_price=?
           WHERE position_id=?""",
        (pm_exit_price, realized_pnl, exit_reason, exit_hl_price, position_id),
    )
    if conn.total_changes == 0:
        print(f"[patch] WARN: no row found for position_id={position_id!r} — nothing updated")
    await conn.commit()
```

- [ ] **Step 4: Testler geçsin**

```bash
python -m pytest tests/test_db.py -v
```

Beklenen: tüm testler PASSED

- [ ] **Step 5: Commit**

```bash
git add db/logger.py tests/test_db.py
git commit -m "feat(logger): entry_hl_price ve exit_hl_price DB'ye kaydet"
```

---

## Task 3: execution/executor.py — DRY_RUN entry_hl_price

**Files:**
- Modify: `execution/executor.py`
- Test: `tests/test_executor.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_executor.py` dosyasını aç, mevcut testlerin altına ekle:

```python
@pytest.mark.asyncio
async def test_dry_run_position_includes_entry_hl_price():
    """DRY_RUN executor → position dict'te entry_hl_price olmalı (finding'den cur_price)."""
    from execution.executor import execute
    finding = {
        "asset": "BTC", "action": "YES", "slug": "btc-up-5m",
        "best_ask": 0.35, "best_bid": 0.33,
        "fair_value": 0.55, "ref_price": 95000.0,
        "edge": 0.20, "cur_price": 66500.0,
    }
    gate   = {"pass": True, "confidence_score": 82.5}
    risk   = {"pass": True, "position_usd": 1.25, "kelly_f": 0.15}
    result = await execute(finding, gate, risk, [])
    assert result is not None
    assert result.get("entry_hl_price") == 66500.0, \
        f"entry_hl_price={result.get('entry_hl_price')}, beklenen 66500.0"
```

- [ ] **Step 2: Çalıştır, FAIL bekle**

```bash
python -m pytest tests/test_executor.py::test_dry_run_position_includes_entry_hl_price -v
```

Beklenen: `FAIL — AssertionError: entry_hl_price=None`

- [ ] **Step 3: executor.py güncelle**

`execution/executor.py` → `position` dict'ini bul (satır ~59), `"dry_run": config.DRY_RUN,` satırından önce ekle:

```python
    position = {
        "position_id":       str(uuid.uuid4()),
        "asset":             finding["asset"],
        "action":            finding["action"],
        "slug":              finding["slug"],
        "pm_entry_price":    pm_entry_price,
        "fair_value":        finding["fair_value"],
        "ref_price":         finding["ref_price"],
        "edge":              finding["edge"],
        "position_usd":      risk_result["position_usd"],
        "kelly_f":           risk_result["kelly_f"],
        "confidence_score":  gate_result["confidence_score"],
        "seconds_remaining": finding["seconds_remaining"],
        "opened_at":         datetime.now(timezone.utc).isoformat(),
        "status":                  "open",
        "requires_human_approval": risk_result["position_usd"] > config.HUMAN_APPROVAL_USD,
        "dry_run":                 config.DRY_RUN,
        "entry_hl_price":          finding.get("cur_price"),
        "exit_reason":             None,
        "closed_at":               None,
    }
```

- [ ] **Step 4: Test geçsin**

```bash
python -m pytest tests/test_executor.py -v
```

Beklenen: tüm testler PASSED

- [ ] **Step 5: Commit**

```bash
git add execution/executor.py tests/test_executor.py
git commit -m "feat(executor): DRY_RUN position'a entry_hl_price ekle"
```

---

## Task 4: execution/clob_executor.py — PRICE_PREMIUM + entry_hl_price

**Files:**
- Modify: `execution/clob_executor.py`
- Test: `tests/test_clob_executor.py`

- [ ] **Step 1: Failing testler yaz**

`tests/test_clob_executor.py` dosyasına ekle:

```python
@pytest.mark.asyncio
async def test_clob_order_uses_price_premium():
    """LIVE order fiyatı = best_ask + PRICE_PREMIUM olmalı."""
    from execution.clob_executor import PRICE_PREMIUM
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {
        "status": "matched", "success": True, "orderID": "ord-prem",
        "takingAmount": "69.0", "makingAmount": "24.84",
    }
    with patch("execution.clob_executor.get_client", return_value=fake_client):
        from execution.clob_executor import execute
        await execute(_finding("YES"), _gate(), _risk(), [])

    call_args = fake_client.create_and_post_order.call_args
    order_args = call_args[0][0]
    expected_price = round(0.35 + PRICE_PREMIUM, 6)
    assert abs(order_args.price - expected_price) < 1e-6, \
        f"Order fiyatı {order_args.price:.4f} — beklenen {expected_price:.4f} (best_ask+PRICE_PREMIUM)"


@pytest.mark.asyncio
async def test_clob_position_includes_entry_hl_price():
    """LIVE position dict'te entry_hl_price = finding['cur_price'] olmalı."""
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {
        "status": "matched", "success": True, "orderID": "ord-hl",
        "takingAmount": "69.0", "makingAmount": "24.84",
    }
    finding = {**_finding("YES"), "cur_price": 66500.0}
    with patch("execution.clob_executor.get_client", return_value=fake_client):
        from execution.clob_executor import execute
        result = await execute(finding, _gate(), _risk(), [])
    assert result is not None
    assert result.get("entry_hl_price") == 66500.0, \
        f"entry_hl_price={result.get('entry_hl_price')}, beklenen 66500.0"
```

- [ ] **Step 2: Çalıştır, FAIL bekle**

```bash
python -m pytest tests/test_clob_executor.py::test_clob_order_uses_price_premium tests/test_clob_executor.py::test_clob_position_includes_entry_hl_price -v
```

Beklenen: 2 FAIL

- [ ] **Step 3: clob_executor.py güncelle**

Dosyanın başına (MIN_SHARES satırından sonra) ekle:

```python
MIN_SHARES    = 1
PRICE_PREMIUM = 0.01   # FOK fill rate iyileştirmesi: best_ask + 1 cent
```

`entry_price` satırını bul ve güncelle:

```python
    entry_price  = finding["best_ask"] + PRICE_PREMIUM
```

`return` dict'ine `entry_hl_price` ekle (diğer alanların yanına):

```python
    return {
        ...
        "yes_token_id":            finding.get("yes_token_id"),
        "no_token_id":             finding.get("no_token_id"),
        "entry_hl_price":          finding.get("cur_price"),
        "requires_human_approval": False,
        "dry_run":                 False,
        "status":                  "open",
        "opened_at":               datetime.now(timezone.utc).isoformat(),
    }
```

- [ ] **Step 4: Tüm clob testleri geçsin**

```bash
python -m pytest tests/test_clob_executor.py -v
```

Beklenen: tüm testler PASSED

**Not:** Mevcut `test_execute_returns_position_on_matched_order` testi `"sizeFilled": "71.43"` kullanıyor. Bu test hâlâ geçmeli — shares mock'tan geliyor, PRICE_PREMIUM'u etkilemez.

- [ ] **Step 5: Commit**

```bash
git add execution/clob_executor.py tests/test_clob_executor.py
git commit -m "feat(clob): PRICE_PREMIUM=0.01 fill rate + entry_hl_price ekle"
```

---

## Task 5: position/manager.py — close_position exit_hl_price

**Files:**
- Modify: `position/manager.py`
- Test: `tests/test_position.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_position.py` dosyasına ekle:

```python
def test_close_position_includes_exit_hl_price():
    """close_position exit_hl_price parametresini closed dict'e eklemeli."""
    from position.manager import close_position
    from datetime import datetime, timezone, timedelta
    pos = {
        "position_id": "pos-hl-01", "asset": "BTC", "action": "YES",
        "slug": "btc-up-5m", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0, "seconds_remaining": 300,
        "opened_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        "status": "open", "dry_run": True,
        "exit_reason": None, "closed_at": None,
        "entry_hl_price": 66500.0,
    }
    closed = close_position(pos, "thesis_invalidated", pm_exit_price=0.72, exit_hl_price=66502.0)
    assert closed["exit_hl_price"] == 66502.0, \
        f"exit_hl_price={closed.get('exit_hl_price')}, beklenen 66502.0"
    assert closed["status"] == "closed"
    assert closed["exit_reason"] == "thesis_invalidated"


def test_close_position_exit_hl_price_none_when_not_given():
    """exit_hl_price verilmezse None olmalı — backward compat."""
    from position.manager import close_position
    from datetime import datetime, timezone, timedelta
    pos = {
        "position_id": "pos-hl-02", "asset": "BTC", "action": "YES",
        "slug": "btc-up-5m", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0, "seconds_remaining": 300,
        "opened_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        "status": "open", "dry_run": True,
        "exit_reason": None, "closed_at": None,
    }
    closed = close_position(pos, "market_expired")
    assert closed.get("exit_hl_price") is None
```

- [ ] **Step 2: Çalıştır, FAIL bekle**

```bash
python -m pytest tests/test_position.py::test_close_position_includes_exit_hl_price tests/test_position.py::test_close_position_exit_hl_price_none_when_not_given -v
```

Beklenen: 2 FAIL

- [ ] **Step 3: position/manager.py güncelle**

`close_position` fonksiyonu imzasını güncelle ve `closed` dict'e `exit_hl_price` ekle:

```python
def close_position(
    position:       dict,
    exit_reason:    str,
    pm_exit_price:  float | None = None,
    exit_hl_price:  float | None = None,
    log_file:       Path = LOG_FILE,
) -> dict:
    """Pozisyonu kapatır, JSONL'a yazar, güncellenmiş kaydı döndürür."""
    closed = {
        **position,
        "status":        "closed",
        "exit_reason":   exit_reason,
        "closed_at":     datetime.now(timezone.utc).isoformat(),
        "pm_exit_price": pm_exit_price,
        "exit_hl_price": exit_hl_price,
    }
    _log("position_closed", {
        "position_id":    closed["position_id"],
        "asset":          closed["asset"],
        "action":         closed["action"],
        "slug":           closed["slug"],
        "exit_reason":    exit_reason,
        "pm_entry_price": closed["pm_entry_price"],
        "pm_exit_price":  pm_exit_price,
        "exit_hl_price":  exit_hl_price,
        "fair_value":     closed["fair_value"],
        "closed_at":      closed["closed_at"],
        "dry_run":        closed["dry_run"],
    }, log_file)
    return closed
```

- [ ] **Step 4: Tüm position testleri geçsin**

```bash
python -m pytest tests/test_position.py -v
```

Beklenen: tüm testler PASSED

- [ ] **Step 5: Commit**

```bash
git add position/manager.py tests/test_position.py
git commit -m "feat(manager): close_position exit_hl_price parametresi ekle"
```

---

## Task 6: main_loop.py — HL Fiyat Akışı

**Files:**
- Modify: `main_loop.py`
- Test: `tests/test_main_loop.py`

### 6a: _load_open_positions — entry_hl_price SELECT

- [ ] **Step 1: Failing test yaz**

`tests/test_main_loop.py` → `test_load_open_positions_returns_open_ones` fonksiyonunu bul. Bu testin altına yeni test ekle:

```python
@pytest.mark.asyncio
async def test_load_open_positions_includes_entry_hl_price(mem_db):
    """DB'deki entry_hl_price pozisyon yüklenince gelsin."""
    pos = {
        "position_id": "hl-load-01", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.18,
        "position_usd": 1.25, "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-06-03T10:00:00+00:00",
        "entry_hl_price": 66500.0,
    }
    await log_position_open(mem_db, pos)
    result = await _load_open_positions(mem_db)
    assert len(result) == 1
    assert result[0].get("entry_hl_price") == 66500.0, \
        f"entry_hl_price={result[0].get('entry_hl_price')}, beklenen 66500.0"
```

- [ ] **Step 2: Çalıştır, FAIL bekle**

```bash
python -m pytest tests/test_main_loop.py::test_load_open_positions_includes_entry_hl_price -v
```

Beklenen: FAIL

- [ ] **Step 3: _load_open_positions güncelle**

`main_loop.py` → `_load_open_positions` fonksiyonunu bul. SELECT sorgusuna `entry_hl_price` ekle ve dict'i güncelle:

```python
    async with conn.execute(
        "SELECT position_id, ts_open, slug, asset, action, pm_entry_price, "
        "fair_value, ref_price, edge, position_usd, kelly_f, confidence_score, dry_run, "
        "shares, order_id, yes_token_id, no_token_id, seq_no, entry_hl_price "
        "FROM positions WHERE status='open' AND dry_run=?",
        (1 if config.DRY_RUN else 0,),
    ) as cur:
```

Dict'e `"entry_hl_price": r[18],` ekle (mevcut `"seq_no": r[17],` satırından sonra):

```python
        {
            "position_id":            r[0],
            "opened_at":              r[1],
            "slug":                   r[2],
            "asset":                  r[3],
            "action":                 r[4],
            "pm_entry_price":         r[5],
            "fair_value":             r[6],
            "ref_price":              r[7],
            "edge":                   r[8],
            "position_usd":           r[9],
            "kelly_f":                r[10],
            "confidence_score":       r[11],
            "status":                 "open",
            "requires_human_approval": (r[9] or 0) > config.HUMAN_APPROVAL_USD,
            "dry_run":                bool(r[12]),
            "shares":                 r[13],
            "order_id":               r[14],
            "yes_token_id":           r[15],
            "no_token_id":            r[16],
            "exit_reason":            None,
            "closed_at":              None,
            "seq_no":                 r[17],
            "entry_hl_price":         r[18],
        }
```

- [ ] **Step 4: Test geçsin**

```bash
python -m pytest tests/test_main_loop.py::test_load_open_positions_includes_entry_hl_price -v
```

Beklenen: PASSED

### 6b: _monitor_positions — exit_hl_price geçir

- [ ] **Step 5: Failing test yaz**

`tests/test_main_loop.py` → `test_monitor_closes_position_on_exit_signal` testinin altına ekle:

```python
@pytest.mark.asyncio
async def test_monitor_passes_exit_hl_price_to_closed_position():
    """_monitor_positions exit anındaki HL fiyatını closed dict'e eklemeli."""
    pos = _open_position()
    open_pos = [pos]
    closed = []
    fake_window = {"best_ask": 0.72, "best_bid": 0.70,
                   "seconds_remaining": 500, "neg_risk": False}
    with patch("main_loop.current_price",     new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",     new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=fake_window), \
         patch("main_loop.fetch_resolved",    new_callable=AsyncMock, return_value=None), \
         patch("main_loop.check_exit",        return_value="thesis_invalidated"):
        mock_hl.return_value = 66502.0
        mock_pm.return_value = {}
        await _monitor_positions(open_pos, closed)
    assert len(closed) == 1
    assert closed[0].get("exit_hl_price") == 66502.0, \
        f"exit_hl_price={closed[0].get('exit_hl_price')}, beklenen 66502.0 (mock HL fiyatı)"
```

- [ ] **Step 6: Çalıştır, FAIL bekle**

```bash
python -m pytest tests/test_main_loop.py::test_monitor_passes_exit_hl_price_to_closed_position -v
```

Beklenen: FAIL

- [ ] **Step 7: _monitor_positions güncelle**

`main_loop.py` → `_monitor_positions` fonksiyonunda `close_position` çağrılarını bul. Her çağrıya `exit_hl_price=hl_price` ekle.

**Branch 1 — market_resolved:**
```python
                closed = close_position(pos, "market_resolved", pm_exit_price=pm_exit,
                                        exit_hl_price=hl_price)
```

**Branch 2 — market_expired:**
```python
                closed = close_position(pos, "market_expired", exit_hl_price=hl_price)
```

**Branch 3 — exit_reason (thesis_invalidated, profit_target_hit, max_hold_time):**
```python
                closed = close_position(pos, exit_reason, pm_exit_price=pm_exit,
                                        exit_hl_price=hl_price)
```

- [ ] **Step 8: Test geçsin**

```bash
python -m pytest tests/test_main_loop.py::test_monitor_passes_exit_hl_price_to_closed_position -v
```

Beklenen: PASSED

### 6c: _heal_pending_resolutions — HL fiyatları

- [ ] **Step 9: Failing test yaz**

`tests/test_main_loop.py` → heal testlerinin altına ekle:

```python
@pytest.mark.asyncio
async def test_heal_passes_hl_prices_to_notify(mem_db):
    """_heal entry_hl_price DB'den okuyup, exit HL için current_price çağırmalı."""
    from db.schema import init_schema
    pos_data = (
        "heal-hl-01", "slug-heal-hl", "BTC", "YES", 0.35, 1.25, 82.0,
        "closed", "market_expired", 1, 5,
    )
    await mem_db.execute(
        """INSERT INTO positions
           (position_id, slug, asset, action, pm_entry_price, position_usd,
            confidence_score, status, exit_reason, dry_run, seq_no, entry_hl_price)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 66500.0)""",
        pos_data,
    )
    await mem_db.commit()
    closed_today = [{"position_id": "heal-hl-01", "pm_exit_price": None,
                     "exit_reason": "market_expired"}]
    notify_calls = []
    with patch("main_loop.fetch_resolved",   new_callable=AsyncMock,
               return_value={"yes_exit": 1.0, "no_exit": 0.0}), \
         patch("main_loop.patch_position_resolution", new_callable=AsyncMock), \
         patch("main_loop.current_price",    new_callable=AsyncMock,
               return_value=66510.0) as mock_hl, \
         patch("main_loop.notify_resolved_late", side_effect=lambda p: notify_calls.append(p)):
        await _heal_pending_resolutions(mem_db, closed_today)
    mock_hl.assert_called_once_with("BTC")
    assert len(notify_calls) == 1
    assert notify_calls[0].get("entry_hl_price") == 66500.0, \
        f"entry_hl_price={notify_calls[0].get('entry_hl_price')}, beklenen 66500.0"
    assert notify_calls[0].get("exit_hl_price") == 66510.0, \
        f"exit_hl_price={notify_calls[0].get('exit_hl_price')}, beklenen 66510.0"
```

- [ ] **Step 10: Çalıştır, FAIL bekle**

```bash
python -m pytest tests/test_main_loop.py::test_heal_passes_hl_prices_to_notify -v
```

Beklenen: FAIL

- [ ] **Step 11: _heal_pending_resolutions güncelle**

`main_loop.py` → `_heal_pending_resolutions` fonksiyonunu bul. SELECT sorgusuna `entry_hl_price` ekle:

```python
    async with conn.execute(
        """SELECT position_id, slug, asset, action, pm_entry_price, position_usd, seq_no,
                  entry_hl_price
           FROM positions
           WHERE status='closed' AND pm_exit_price IS NULL
           LIMIT ?""",
        (limit,),
    ) as cur:
        rows = await cur.fetchall()

    for position_id, slug, asset, action, pm_entry_price, position_usd, seq_no, entry_hl_price in rows:
        try:
            resolution = await fetch_resolved(slug)
            if resolution is None:
                continue
            pm_exit      = resolution["yes_exit"] if action == "YES" else resolution["no_exit"]
            if not pm_entry_price:
                print(f"[heal] {slug} pm_entry_price=0, skipping")
                continue
            realized_pnl = (pm_exit - pm_entry_price) / pm_entry_price * position_usd
            try:
                exit_hl_price = await current_price(asset)
            except Exception:
                exit_hl_price = None
            await patch_position_resolution(conn, position_id, pm_exit, realized_pnl,
                                            exit_hl_price=exit_hl_price)
            for pos in closed_today:
                if pos.get("position_id") == position_id:
                    pos["pm_exit_price"] = pm_exit
                    pos["realized_pnl"]  = realized_pnl
                    pos["exit_reason"]   = "market_resolved_late"
                    break
            notify_resolved_late({
                "seq_no":          seq_no,
                "asset":           asset,
                "action":          action,
                "pm_entry_price":  pm_entry_price,
                "pm_exit_price":   pm_exit,
                "position_usd":    position_usd,
                "entry_hl_price":  entry_hl_price,
                "exit_hl_price":   exit_hl_price,
            })
        except Exception as e:
            print(f"[heal] {slug} hata: {e}")
```

- [ ] **Step 12: Tüm main_loop testleri geçsin**

```bash
python -m pytest tests/test_main_loop.py -v
```

Beklenen: tüm testler PASSED

- [ ] **Step 13: Commit**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(main_loop): HL fiyat akışı — load/monitor/heal"
```

---

## Task 7: monitor/notifier.py — Bildirim Formatları

**Files:**
- Modify: `monitor/notifier.py`
- Test: `tests/test_monitor.py`

- [ ] **Step 1: Failing testler yaz**

`tests/test_monitor.py` dosyasını aç (yoksa oluştur), ekle:

```python
"""tests/test_monitor.py — notifier bildirim format testleri."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch


def _make_pos(**kwargs):
    base = {
        "position_id": "pos-01", "asset": "BTC", "action": "YES",
        "slug": "btc-up-5m", "pm_entry_price": 0.35, "fair_value": 0.55,
        "edge": 0.20, "position_usd": 1.25, "seq_no": 42,
        "exit_reason": "thesis_invalidated",
        "pm_exit_price": 0.72,
    }
    return {**base, **kwargs}


def test_notify_open_shows_entry_hl_price():
    """notify_open HL fiyatını bildirimi içermeli."""
    from monitor.notifier import notify_open
    sent = []
    with patch("monitor.notifier.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        with patch("monitor.notifier.config") as cfg:
            cfg.TELEGRAM_BOT_TOKEN = "tok"
            cfg.TELEGRAM_CHAT_ID   = "123"
            cfg.DRY_RUN            = True
            notify_open(_make_pos(entry_hl_price=66500.0))
        text = mock_post.call_args[1]["json"]["text"]
    assert "66,500" in text or "66500" in text, \
        f"HL fiyatı bildirimde yok: {text}"


def test_notify_open_no_crash_without_hl_price():
    """entry_hl_price yokken notify_open hata vermemeli."""
    from monitor.notifier import notify_open
    with patch("monitor.notifier.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        with patch("monitor.notifier.config") as cfg:
            cfg.TELEGRAM_BOT_TOKEN = "tok"
            cfg.TELEGRAM_CHAT_ID   = "123"
            cfg.DRY_RUN            = True
            notify_open(_make_pos())   # entry_hl_price yok


def test_notify_close_shows_hl_entry_and_exit():
    """notify_close hem entry hem exit HL fiyatını göstermeli."""
    from monitor.notifier import notify_close
    pos = _make_pos(entry_hl_price=66500.0, exit_hl_price=66502.0)
    with patch("monitor.notifier.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        with patch("monitor.notifier.config") as cfg:
            cfg.TELEGRAM_BOT_TOKEN = "tok"
            cfg.TELEGRAM_CHAT_ID   = "123"
            cfg.DRY_RUN            = True
            notify_close(pos)
        text = mock_post.call_args[1]["json"]["text"]
    assert "66,500" in text or "66500" in text, f"entry HL yok: {text}"
    assert "66,502" in text or "66502" in text, f"exit HL yok: {text}"


def test_notify_close_no_crash_without_hl_prices():
    """HL fiyatlar yokken notify_close hata vermemeli."""
    from monitor.notifier import notify_close
    with patch("monitor.notifier.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        with patch("monitor.notifier.config") as cfg:
            cfg.TELEGRAM_BOT_TOKEN = "tok"
            cfg.TELEGRAM_CHAT_ID   = "123"
            cfg.DRY_RUN            = True
            notify_close(_make_pos())   # HL fiyatlar yok


def test_notify_resolved_late_shows_hl_prices():
    """notify_resolved_late HL giriş ve çıkış fiyatlarını göstermeli."""
    from monitor.notifier import notify_resolved_late
    pos = {
        "seq_no": 42, "asset": "BTC", "action": "YES",
        "pm_entry_price": 0.35, "pm_exit_price": 1.0,
        "position_usd": 1.25,
        "entry_hl_price": 66500.0, "exit_hl_price": 66510.0,
    }
    with patch("monitor.notifier.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        with patch("monitor.notifier.config") as cfg:
            cfg.TELEGRAM_BOT_TOKEN = "tok"
            cfg.TELEGRAM_CHAT_ID   = "123"
            cfg.DRY_RUN            = True
            notify_resolved_late(pos)
        text = mock_post.call_args[1]["json"]["text"]
    assert "66,500" in text or "66500" in text, f"entry HL yok: {text}"
    assert "66,510" in text or "66510" in text, f"exit HL yok: {text}"
```

- [ ] **Step 2: Çalıştır, FAIL bekle**

```bash
python -m pytest tests/test_monitor.py -v
```

Beklenen: ilk 3 FAIL (HL fiyatlar mesajda yok)

- [ ] **Step 3: notifier.py güncelle**

`monitor/notifier.py` → 3 fonksiyonu güncelle:

```python
def notify_open(pos: dict) -> None:
    entry_hl = pos.get("entry_hl_price")
    hl_line  = f"\nHL: ${entry_hl:,.0f}" if entry_hl else ""
    send_telegram(
        f"AÇILDI {_seq(pos)}{pos['asset']} {pos['action']}\n"
        f"Edge: {pos.get('edge', 0):.0%} | Pozisyon: ${pos.get('position_usd', 0):.2f}"
        f"{hl_line}"
    )


def notify_close(pos: dict) -> None:
    msg = (
        f"KAPANDI {_seq(pos)}{pos['asset']} {pos['action']}\n"
        f"Sebep: {pos.get('exit_reason', '?')}"
    )
    entry   = pos.get("pm_entry_price")
    exit_p  = pos.get("pm_exit_price")
    pos_usd = pos.get("position_usd", 0)
    if entry and exit_p is not None:
        pnl    = (exit_p - entry) / entry * pos_usd
        cikis  = pos_usd + pnl
        pct    = pnl / pos_usd * 100 if pos_usd else 0
        sign   = "+" if pnl >= 0 else ""
        icon   = "✅" if pnl >= 0 else "❌"
        msg += (
            f"\nGiriş: ${pos_usd:.2f} → Çıkış: ${cikis:.2f}"
            f"\nP&L: {sign}${pnl:.2f} ({sign}{pct:.1f}%) {icon}"
        )
    entry_hl = pos.get("entry_hl_price")
    exit_hl  = pos.get("exit_hl_price")
    if entry_hl and exit_hl:
        msg += f"\nHL: ${entry_hl:,.0f} → ${exit_hl:,.0f}"
    elif entry_hl:
        msg += f"\nHL: ${entry_hl:,.0f}"
    send_telegram(msg)


def notify_resolved_late(pos: dict) -> None:
    """Heal edilmiş pozisyon için gecikmiş Telegram bildirimi."""
    msg = (
        f"GÜNCELLENDİ {_seq(pos)}{pos['asset']} {pos['action']}\n"
        f"market_resolved_late"
    )
    entry   = pos.get("pm_entry_price")
    exit_p  = pos.get("pm_exit_price")
    pos_usd = pos.get("position_usd", 0)
    if entry and exit_p is not None:
        pnl   = (exit_p - entry) / entry * pos_usd
        cikis = pos_usd + pnl
        pct   = pnl / pos_usd * 100 if pos_usd else 0
        sign  = "+" if pnl >= 0 else ""
        icon  = "✅" if pnl >= 0 else "❌"
        msg += (
            f"\nGiriş: ${pos_usd:.2f} → Çıkış: ${cikis:.2f}"
            f"\nP&L: {sign}${pnl:.2f} ({sign}{pct:.1f}%) {icon}"
        )
    entry_hl = pos.get("entry_hl_price")
    exit_hl  = pos.get("exit_hl_price")
    if entry_hl and exit_hl:
        msg += f"\nHL: ${entry_hl:,.0f} → ${exit_hl:,.0f}"
    elif entry_hl:
        msg += f"\nHL: ${entry_hl:,.0f}"
    send_telegram(msg)
```

- [ ] **Step 4: Tüm monitor testleri geçsin**

```bash
python -m pytest tests/test_monitor.py -v
```

Beklenen: tüm testler PASSED

- [ ] **Step 5: Commit**

```bash
git add monitor/notifier.py tests/test_monitor.py
git commit -m "feat(notifier): HL giriş/çıkış fiyatı bildirimlere ekle"
```

---

## Task 8: Tam Regresyon + Restart

- [ ] **Step 1: Tüm test suite**

```bash
source venv/bin/activate && python -m pytest --tb=short -q
```

Beklenen: **260+ passed, 0 failed**

Eğer fail varsa: ilgili task'a geri dön, düzelt, testi tekrar çalıştır.

- [ ] **Step 2: Bot restart**

```bash
./restart.sh
```

- [ ] **Step 3: Doğrula**

```bash
ps aux | grep "main_loop.py" | grep -v grep | grep -v bash
```

Beklenen: tek bir `python -u main_loop.py` process

- [ ] **Step 4: Final commit**

```bash
git add -A
git status  # sadece restart.sh ve plan dosyası varsa
git commit -m "chore: HL fiyat + fill rate feature tamamlandı — 260+ test green"
```
