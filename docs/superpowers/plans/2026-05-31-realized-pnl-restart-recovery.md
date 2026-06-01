# Realized P&L + Daily Loss Restart Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kapanan pozisyonların P&L'ini DB'ye yaz; bot yeniden başlayınca bugünün kapanan pozisyonlarını DB'den geri yükleyerek günlük kayıp limitini doğru hesapla.

**Architecture:** `realized_pnl` kolonu `db/schema.py` migration'ıyla eklenir. `log_position_close` kapanışta P&L hesaplayıp yazar. Yeni `load_closed_today` fonksiyonu bugünün UTC tarihine göre filtreler. `main()` startup'ta bu fonksiyonu çağırıp `closed_today`'i doldurur; böylece `_daily_loss_usd` restart'tan bağımsız doğru çalışır.

**Tech Stack:** Python 3.12, aiosqlite, pytest, AsyncMock — mevcut stack değişmiyor.

---

## Dosya Haritası

| Dosya | İşlem | Ne değişiyor |
|-------|--------|--------------|
| `db/schema.py` | Güncelle | `_MIGRATIONS`'a `realized_pnl REAL` ekle |
| `db/logger.py` | Güncelle | `log_position_close` P&L hesaplar + yazar; `load_closed_today` yeni fonksiyon |
| `main_loop.py` | Güncelle | `load_closed_today` import + `main()` startup'ta çağır |
| `tests/test_db.py` | Güncelle | 3 yeni test (schema + pnl stored + load_closed_today) |
| `tests/test_main_loop.py` | Güncelle | 1 yeni test (restart recovery → daily_loss doğru) |

---

## Task 1: Schema Migration — `realized_pnl` Kolonu

**Dosyalar:**
- Güncelle: `db/schema.py`
- Güncelle: `tests/test_db.py`

- [ ] **Step 1: Testi yaz (başarısız olacak)**

`tests/test_db.py` sonuna ekle:

```python
@pytest.mark.asyncio
async def test_positions_schema_has_realized_pnl(conn):
    """positions tablosu realized_pnl sütununa sahip olmalı."""
    async with conn.execute("PRAGMA table_info(positions)") as cur:
        cols = {row[1] for row in await cur.fetchall()}
    assert "realized_pnl" in cols, "positions tablosunda realized_pnl sütunu yok"
```

- [ ] **Step 2: Testi çalıştır — başarısız olmalı**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/test_db.py::test_positions_schema_has_realized_pnl -v
```

Beklenti: **FAILED** — `AssertionError: positions tablosunda realized_pnl sütunu yok`

- [ ] **Step 3: Migration ekle**

`db/schema.py` içinde `_MIGRATIONS` listesine yeni satır ekle:

```python
_MIGRATIONS = [
    "ALTER TABLE positions ADD COLUMN ref_price REAL",
    "ALTER TABLE positions ADD COLUMN edge REAL",
    "ALTER TABLE positions ADD COLUMN realized_pnl REAL",   # ← yeni
]
```

- [ ] **Step 4: Testi çalıştır — geçmeli**

```bash
pytest tests/test_db.py::test_positions_schema_has_realized_pnl -v
```

Beklenti: **PASSED**

- [ ] **Step 5: Mevcut DB'yi migrate et (canlı DB var)**

```bash
python3 -c "
import asyncio, aiosqlite
from db.schema import init_schema

async def migrate():
    async with aiosqlite.connect('logs/mispricing.db') as db:
        await init_schema(db)
        async with db.execute('PRAGMA table_info(positions)') as cur:
            cols = [r[1] for r in await cur.fetchall()]
        print('Kolonlar:', cols)

asyncio.run(migrate())
"
```

Beklenti: `realized_pnl` listede görünür.

- [ ] **Step 6: Tüm DB testleri — regresyon yok**

```bash
pytest tests/test_db.py -v -q
```

Beklenti: hepsi PASSED.

- [ ] **Step 7: Commit**

```bash
git add db/schema.py tests/test_db.py
git commit -m "feat(db): realized_pnl kolonu — migration ile mevcut DB'ye eklenir"
```

---

## Task 2: `log_position_close` — P&L Hesapla ve Yaz

**Dosyalar:**
- Güncelle: `db/logger.py`
- Güncelle: `tests/test_db.py`

- [ ] **Step 1: 2 testi yaz (başarısız olacak)**

`tests/test_db.py` sonuna ekle:

```python
@pytest.mark.asyncio
async def test_log_position_close_stores_realized_pnl(conn):
    """Kapanan pozisyonda realized_pnl hesaplanıp DB'ye yazılır.
    entry=0.40, exit=0.0, position_usd=50 → pnl = (0.0-0.40)/0.40*50 = -50.0
    """
    pos = {
        "position_id": "pos-pnl", "slug": "eth-down-15min", "asset": "ETH",
        "action": "NO", "pm_entry_price": 0.40, "fair_value": 0.55,
        "ref_price": 3000.0, "edge": 0.15,
        "position_usd": 50.0, "kelly_f": 0.12, "confidence_score": 78.0,
        "opened_at": "2026-05-31T10:00:00+00:00",
    }
    await logger.log_position_open(conn, pos)
    closed = {**pos, "pm_exit_price": 0.0, "exit_reason": "market_resolved",
              "closed_at": "2026-05-31T10:14:00+00:00", "status": "closed"}
    await logger.log_position_close(conn, closed)

    async with conn.execute(
        "SELECT realized_pnl FROM positions WHERE position_id='pos-pnl'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] is not None
    assert abs(row[0] - (-50.0)) < 1e-4


@pytest.mark.asyncio
async def test_log_position_close_realized_pnl_none_when_no_exit_price(conn):
    """pm_exit_price=None (market_expired) → realized_pnl=None."""
    pos = {
        "position_id": "pos-noexit", "slug": "btc-up-5min", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20,
        "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-05-31T10:00:00+00:00",
    }
    await logger.log_position_open(conn, pos)
    closed = {**pos, "pm_exit_price": None, "exit_reason": "market_expired",
              "closed_at": "2026-05-31T10:14:00+00:00", "status": "closed"}
    await logger.log_position_close(conn, closed)

    async with conn.execute(
        "SELECT realized_pnl FROM positions WHERE position_id='pos-noexit'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] is None
```

- [ ] **Step 2: Testleri çalıştır — başarısız olmalı**

```bash
pytest tests/test_db.py::test_log_position_close_stores_realized_pnl \
       tests/test_db.py::test_log_position_close_realized_pnl_none_when_no_exit_price -v
```

Beklenti: **2 FAILED** — `realized_pnl` NULL geliyor (henüz hesaplanmıyor).

- [ ] **Step 3: `log_position_close` güncelle**

`db/logger.py` içindeki `log_position_close` fonksiyonunu değiştir:

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
               exit_reason=?, realized_pnl=?
           WHERE position_id=?""",
        (
            position.get("closed_at", datetime.now(timezone.utc).isoformat()),
            exit_p,
            position.get("exit_reason"),
            realized_pnl,
            position["position_id"],
        ),
    )
    await conn.commit()
```

- [ ] **Step 4: Testleri çalıştır — geçmeli**

```bash
pytest tests/test_db.py::test_log_position_close_stores_realized_pnl \
       tests/test_db.py::test_log_position_close_realized_pnl_none_when_no_exit_price -v
```

Beklenti: **2 PASSED**

- [ ] **Step 5: Tüm DB testleri — regresyon yok**

```bash
pytest tests/test_db.py -v -q
```

Beklenti: hepsi PASSED.

- [ ] **Step 6: Commit**

```bash
git add db/logger.py tests/test_db.py
git commit -m "feat(db): log_position_close realized_pnl hesaplar ve yazar"
```

---

## Task 3: `load_closed_today` — Restart Recovery Sorgusu

**Dosyalar:**
- Güncelle: `db/logger.py`
- Güncelle: `tests/test_db.py`

- [ ] **Step 1: Testi yaz (başarısız olacak)**

`tests/test_db.py` import satırına ekle (üstte):

```python
from datetime import date, timedelta
```

Sonra dosya sonuna ekle:

```python
@pytest.mark.asyncio
async def test_load_closed_today_returns_only_todays(conn):
    """load_closed_today yalnızca bugünün UTC kapanışlarını döndürür, önceki günleri değil."""
    from db.logger import load_closed_today

    today     = date.today().isoformat()          # "2026-05-31"
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    base = {
        "slug": "btc-up-5min", "asset": "BTC", "action": "YES",
        "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20,
        "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.0,
    }

    # Bugün kapanan
    pos_today = {**base, "position_id": "today-001",
                 "opened_at": f"{today}T09:00:00+00:00"}
    await logger.log_position_open(conn, pos_today)
    await logger.log_position_close(conn, {
        **pos_today, "pm_exit_price": 0.5, "exit_reason": "profit_target_hit",
        "closed_at": f"{today}T09:14:00+00:00", "status": "closed",
    })

    # Dün kapanan
    pos_yesterday = {**base, "position_id": "yest-001",
                     "opened_at": f"{yesterday}T09:00:00+00:00"}
    await logger.log_position_open(conn, pos_yesterday)
    await logger.log_position_close(conn, {
        **pos_yesterday, "pm_exit_price": 0.3, "exit_reason": "max_hold_time",
        "closed_at": f"{yesterday}T09:14:00+00:00", "status": "closed",
    })

    result = await load_closed_today(conn)
    assert len(result) == 1
    assert result[0]["position_id"] == "today-001"
    assert result[0]["closed_at"].startswith(today)
    assert result[0]["pm_exit_price"] == 0.5
```

- [ ] **Step 2: Testi çalıştır — başarısız olmalı**

```bash
pytest tests/test_db.py::test_load_closed_today_returns_only_todays -v
```

Beklenti: **FAILED** — `ImportError: cannot import name 'load_closed_today'`

- [ ] **Step 3: `load_closed_today` fonksiyonunu yaz**

`db/logger.py` dosyasına `log_position_close`'dan SONRA ekle:

```python
async def load_closed_today(conn) -> list[dict]:
    """Bugünün UTC kapanan pozisyonlarını yükler — restart sonrası daily_loss recovery."""
    from datetime import datetime, timezone
    today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")  # "2026-05-31"
    async with conn.execute(
        """SELECT position_id, ts_open, ts_close, slug, asset, action,
                  pm_entry_price, pm_exit_price, position_usd, realized_pnl,
                  exit_reason, dry_run
           FROM positions
           WHERE status='closed' AND ts_close LIKE ?""",
        (f"{today_prefix}%",),
    ) as cur:
        rows = await cur.fetchall()
    return [
        {
            "position_id":    r[0],
            "opened_at":      r[1],
            "closed_at":      r[2],
            "slug":           r[3],
            "asset":          r[4],
            "action":         r[5],
            "pm_entry_price": r[6],
            "pm_exit_price":  r[7],
            "position_usd":   r[8],
            "realized_pnl":   r[9],
            "exit_reason":    r[10],
            "dry_run":        bool(r[11]),
        }
        for r in rows
    ]
```

- [ ] **Step 4: Testi çalıştır — geçmeli**

```bash
pytest tests/test_db.py::test_load_closed_today_returns_only_todays -v
```

Beklenti: **PASSED**

- [ ] **Step 5: Tüm DB testleri — regresyon yok**

```bash
pytest tests/test_db.py -v -q
```

Beklenti: hepsi PASSED.

- [ ] **Step 6: Commit**

```bash
git add db/logger.py tests/test_db.py
git commit -m "feat(db): load_closed_today — restart sonrası bugünün pozisyonlarını yükler"
```

---

## Task 4: Main Loop Startup Recovery

**Dosyalar:**
- Güncelle: `main_loop.py`
- Güncelle: `tests/test_main_loop.py`

- [ ] **Step 1: Testi yaz (başarısız olacak)**

`tests/test_main_loop.py` import satırını güncelle:

```python
from main_loop import _run_council, _scan_and_execute, _monitor_positions, _load_open_positions, fetch_resolved
```

Dosyanın sonuna ekle:

```python
@pytest.mark.asyncio
async def test_daily_loss_includes_recovered_closed_positions(mem_db):
    """Restart sonrası DB'den yüklenen bugünün kapanan pozisyonları _daily_loss_usd'e dahil edilir."""
    from datetime import date
    from db.logger import log_position_open, log_position_close, load_closed_today
    from main_loop import _daily_loss_usd

    today = date.today().isoformat()
    pos = {
        "position_id": "recovery-001", "slug": "btc-up-test", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.40, "fair_value": 0.60,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 50.0,
        "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": f"{today}T10:00:00+00:00",
    }
    await log_position_open(mem_db, pos)

    closed = {**pos, "pm_exit_price": 0.0, "exit_reason": "market_resolved",
              "closed_at": f"{today}T10:14:00+00:00", "status": "closed"}
    await log_position_close(mem_db, closed)

    # Restart simülasyonu: bellekte hiçbir şey yok, DB'den yükle
    recovered = await load_closed_today(mem_db)
    assert len(recovered) == 1

    # (0.0 - 0.40) / 0.40 * 50 = -50 → kayıp 50.0
    loss = _daily_loss_usd(recovered)
    assert abs(loss - 50.0) < 1e-4
```

- [ ] **Step 2: Testi çalıştır — başarısız olmalı**

```bash
pytest tests/test_main_loop.py::test_daily_loss_includes_recovered_closed_positions -v
```

Beklenti: **FAILED** — `ImportError: cannot import name 'load_closed_today'` (main_loop'ta import yok)

- [ ] **Step 3: `main_loop.py` güncelle**

Import satırını değiştir:

```python
from db.logger import log_candidate, log_position_open, log_position_close, load_closed_today, get_connection
```

`main()` fonksiyonunda `_load_open_positions` çağrısından hemen sonraya ekle:

```python
async def main() -> None:
    open_positions: list[dict] = []
    closed_today:   list[dict] = []
    print(f"[bot] Başladı — DRY_RUN={config.DRY_RUN}, tarama={SCAN_INTERVAL_SECS}s")
    conn = await get_connection()
    open_positions = await _load_open_positions(conn)
    closed_today   = await load_closed_today(conn)          # ← YENİ
    if open_positions:
        print(f"[bot] DB'den {len(open_positions)} açık pozisyon yüklendi.")
    if closed_today:
        daily_loss = _daily_loss_usd(closed_today)
        print(f"[bot] Bugün {len(closed_today)} kapanan pozisyon geri yüklendi, günlük kayıp: ${daily_loss:.2f}")
    try:
        ...
```

- [ ] **Step 4: Testi çalıştır — geçmeli**

```bash
pytest tests/test_main_loop.py::test_daily_loss_includes_recovered_closed_positions -v
```

Beklenti: **PASSED**

- [ ] **Step 5: Tüm main_loop testleri — regresyon yok**

```bash
pytest tests/test_main_loop.py -v -q
```

Beklenti: hepsi PASSED.

- [ ] **Step 6: Commit**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(main_loop): startup'ta load_closed_today — daily loss restart'tan bağımsız"
```

---

## Task 5: Tam Suite + Bot Restart

- [ ] **Step 1: Tam test suite**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/ --asyncio-mode=auto -q
```

Beklenti: **167+ passed, 0 failed**, 3 skipped (scout/verifier skip'leri normal).

- [ ] **Step 2: Bot'u yeni kodla yeniden başlat**

```bash
tmux send-keys -t mispricing C-c
sleep 1
tmux send-keys -t mispricing "source venv/bin/activate && python -u main_loop.py" Enter
sleep 3
tmux capture-pane -t mispricing -p -S -5
```

Beklenti: `[bot] Başladı — DRY_RUN=True`, hata yok.  
Eğer bugün kapanan pozisyon varsa: `[bot] Bugün N kapanan pozisyon geri yüklendi, günlük kayıp: $X.XX`

- [ ] **Step 3: Memory güncelle**

`/root/.claude/projects/-root-mispricing-agent/memory/project_overview.md` içinde:
- realized_pnl + restart recovery ✅ olarak işaretle
- Test sayısını güncelle
- Sıradaki adımı güncelle (Polymarket execution veya performance review)
