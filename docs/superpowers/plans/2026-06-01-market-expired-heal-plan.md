# market_expired Heal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `market_expired` exit_reason ile kapanan pozisyonlarda `pm_exit_price=None` ve `realized_pnl=None` olan kaydı düzelt — retroaktif script ile mevcut 31 kaydı, yapısal fix ile gelecek tüm kayıtları heal et.

**Architecture:** `patch_position_resolution()` DB patch fonksiyonu `db/logger.py`'e eklenir. Retroaktif one-shot script `analysis/backfill_expired.py` mevcut null kayıtları heal eder. `_heal_pending_resolutions()` her scan döngüsünün sonunda çalışarak `pm_exit_price IS NULL` kayıtları sorgular ve API'den resolve gelince patch'ler. Exit reason sözleşmesi: `market_resolved_late`.

**Tech Stack:** Python 3.12, aiosqlite, pytest, pytest-asyncio, AsyncMock — mevcut stack, değişmiyor.

---

## Dosya Haritası

| Dosya | İşlem | Değişiklik |
|-------|--------|-----------|
| `db/logger.py` | Güncelle | `patch_position_resolution()` yeni async fonksiyon |
| `analysis/backfill_expired.py` | Yeni | One-shot retroaktif heal script |
| `main_loop.py` | Güncelle | `_heal_pending_resolutions()` + main loop'a çağrı |
| `tests/test_db.py` | Güncelle | `test_patch_position_resolution_writes_db` |
| `tests/test_main_loop.py` | Güncelle | import satırı + 3 heal testi |

---

## Task 1: `patch_position_resolution()` — DB Patch Fonksiyonu

**Dosyalar:**
- Güncelle: `db/logger.py` (mevcut dosya, sona ekle)
- Güncelle: `tests/test_db.py` (mevcut dosya, sona ekle)

- [ ] **Step 1: Failing test yaz**

`tests/test_db.py` dosyasının sonuna ekle:

```python
@pytest.mark.asyncio
async def test_patch_position_resolution_writes_db(conn):
    """patch_position_resolution sonrası DB'de pm_exit_price, realized_pnl, exit_reason doğru."""
    await conn.execute(
        """INSERT INTO positions
               (position_id, ts_open, slug, asset, action, pm_entry_price,
                position_usd, kelly_f, confidence_score, status, dry_run)
           VALUES ('pid-heal-001', '2026-06-01T10:00:00+00:00', 'btc-up-5m',
                   'BTC', 'YES', 0.20, 50.0, 0.10, 75.0, 'closed', 1)"""
    )
    await conn.commit()

    from db.logger import patch_position_resolution
    await patch_position_resolution(conn, "pid-heal-001", 1.0, 200.0, "market_resolved_late")

    async with conn.execute(
        "SELECT pm_exit_price, realized_pnl, exit_reason FROM positions WHERE position_id='pid-heal-001'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] == 1.0
    assert abs(row[1] - 200.0) < 0.01
    assert row[2] == "market_resolved_late"


@pytest.mark.asyncio
async def test_patch_position_resolution_conn_none_is_noop():
    """conn=None → sessizce atlanır, exception yok."""
    from db.logger import patch_position_resolution
    await patch_position_resolution(None, "x", 1.0, 10.0, "market_resolved_late")  # no raise
```

- [ ] **Step 2: Testi çalıştır — FAIL bekliyoruz**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/test_db.py::test_patch_position_resolution_writes_db -v
```

Beklenen: `ImportError: cannot import name 'patch_position_resolution'`

- [ ] **Step 3: `patch_position_resolution` fonksiyonunu `db/logger.py`'e ekle**

`db/logger.py` dosyasının en sonuna (137. satırdan sonra) ekle:

```python

async def patch_position_resolution(
    conn,
    position_id:   str,
    pm_exit_price: float,
    realized_pnl:  float,
    exit_reason:   str = "market_resolved_late",
) -> None:
    """Kapanmış pozisyonun exit fiyatı ve P&L'ini günceller (market_expired → resolved_late)."""
    if conn is None:
        return
    await conn.execute(
        "UPDATE positions SET pm_exit_price=?, realized_pnl=?, exit_reason=? WHERE position_id=?",
        (pm_exit_price, realized_pnl, exit_reason, position_id),
    )
    await conn.commit()
```

- [ ] **Step 4: Testi çalıştır — PASS bekliyoruz**

```bash
pytest tests/test_db.py::test_patch_position_resolution_writes_db \
       tests/test_db.py::test_patch_position_resolution_conn_none_is_noop -v
```

Beklenen: 2 PASSED

- [ ] **Step 5: Tüm test suite'i çalıştır — regresyon yok mu?**

```bash
pytest tests/ -q --tb=short
```

Beklenen: öncekiyle aynı pass sayısı + 2 yeni PASSED

- [ ] **Step 6: Commit**

```bash
git add db/logger.py tests/test_db.py
git commit -m "feat(db): patch_position_resolution — market_expired → resolved_late"
```

---

## Task 2: Retroaktif Backfill Script

**Dosyalar:**
- Yeni: `analysis/backfill_expired.py`

- [ ] **Step 1: `analysis/backfill_expired.py` dosyasını oluştur**

```python
#!/usr/bin/env python3
"""analysis/backfill_expired.py — market_expired P&L retroaktif heal.

Kullanım:
    python analysis/backfill_expired.py

Mevcut DB'deki pm_exit_price=NULL olan kapanmış pozisyonlar için
fetch_resolved çağırır; veri gelirse DB'ye yazar ve exit_reason'ı
'market_resolved_late' olarak günceller.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.logger import get_connection, patch_position_resolution
from data.shortterm import fetch_resolved


async def backfill() -> None:
    conn = await get_connection()
    try:
        async with conn.execute(
            """SELECT position_id, slug, action, pm_entry_price, position_usd
               FROM positions
               WHERE status='closed' AND pm_exit_price IS NULL"""
        ) as cur:
            rows = await cur.fetchall()

        total = len(rows)
        print(f"{total} market_expired kayıt bulundu.\n")

        recovered = 0
        for position_id, slug, action, pm_entry_price, position_usd in rows:
            resolution = await fetch_resolved(slug)
            if resolution is None:
                print(f"  — {slug}: hâlâ resolve yok (iptal market?)")
                continue
            pm_exit = resolution["yes_exit"] if action == "YES" else resolution["no_exit"]
            realized_pnl = (pm_exit - pm_entry_price) / pm_entry_price * position_usd
            await patch_position_resolution(conn, position_id, pm_exit, realized_pnl, "market_resolved_late")
            print(f"  ✓ {slug} {action}: exit={pm_exit:.4f}, pnl={realized_pnl:+.2f}")
            recovered += 1

        still_null = total - recovered
        print(f"\nSonuç: {recovered} recovered, {still_null} still null")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(backfill())
```

- [ ] **Step 2: Script'i gerçek DB üzerinde çalıştır**

```bash
cd /root/mispricing_agent && source venv/bin/activate
python analysis/backfill_expired.py
```

Beklenen çıktı:
```
31 market_expired kayıt bulundu.
  ✓ btc-updown-5m-... YES: exit=1.0000, pnl=+200.00
  ...
Sonuç: XX recovered, YY still null
```

- [ ] **Step 3: DB'yi doğrula — null kaldı mı?**

```bash
python -c "
import asyncio, aiosqlite

async def check():
    async with aiosqlite.connect('logs/mispricing.db') as db:
        async with db.execute(
            'SELECT exit_reason, COUNT(*), SUM(realized_pnl) FROM positions WHERE status=\"closed\" GROUP BY exit_reason'
        ) as c:
            for r in await c.fetchall():
                print(f'  {r[0]:25} count={r[1]:3}  toplam_pnl={r[2]}')
asyncio.run(check())
"
```

`market_expired` satırında `count` düşmüş, `market_resolved_late` satırı belirmiş olmalı.

- [ ] **Step 4: Commit**

```bash
git add analysis/backfill_expired.py
git commit -m "feat(analysis): backfill_expired — market_expired P&L retroaktif heal"
```

---

## Task 3: `_heal_pending_resolutions()` — Yapısal Fix

**Dosyalar:**
- Güncelle: `main_loop.py`
- Güncelle: `tests/test_main_loop.py`

- [ ] **Step 1: test_main_loop.py import satırını güncelle**

Mevcut satır (12. satır):

```python
from main_loop import _run_council, _scan_and_execute, _monitor_positions, _load_open_positions, fetch_resolved
```

Yeni hali:

```python
from main_loop import _run_council, _scan_and_execute, _monitor_positions, _load_open_positions, fetch_resolved, _heal_pending_resolutions
```

- [ ] **Step 2: Failing testleri `tests/test_main_loop.py` sonuna yaz**

```python
# ── Task: _heal_pending_resolutions() ────────────────────────────────────────

@pytest.mark.asyncio
async def test_heal_fixes_null_pnl_when_api_returns(mem_db):
    """fetch_resolved veri döndürünce pm_exit_price ve realized_pnl DB'ye yazılır."""
    await mem_db.execute(
        """INSERT INTO positions
               (position_id, ts_open, ts_close, slug, asset, action, pm_entry_price,
                position_usd, kelly_f, confidence_score, status, exit_reason, dry_run)
           VALUES ('heal-001', '2026-06-01T10:00:00+00:00', '2026-06-01T10:05:00+00:00',
                   'btc-up-5m', 'BTC', 'YES', 0.20, 50.0, 0.10, 75.0,
                   'closed', 'market_expired', 1)"""
    )
    await mem_db.commit()

    closed_today = [{"position_id": "heal-001", "pm_exit_price": None, "exit_reason": "market_expired"}]

    with patch("main_loop.fetch_resolved", new_callable=AsyncMock) as mock_res:
        mock_res.return_value = {"yes_exit": 1.0, "no_exit": 0.0}
        await _heal_pending_resolutions(mem_db, closed_today, limit=3)

    async with mem_db.execute(
        "SELECT pm_exit_price, realized_pnl, exit_reason FROM positions WHERE position_id='heal-001'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] == 1.0
    assert abs(row[1] - 200.0) < 0.01   # (1.0 - 0.20) / 0.20 * 50 = 200
    assert row[2] == "market_resolved_late"
    assert closed_today[0]["pm_exit_price"] == 1.0
    assert closed_today[0]["exit_reason"] == "market_resolved_late"


@pytest.mark.asyncio
async def test_heal_skips_when_api_still_none(mem_db):
    """fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz."""
    await mem_db.execute(
        """INSERT INTO positions
               (position_id, ts_open, ts_close, slug, asset, action, pm_entry_price,
                position_usd, kelly_f, confidence_score, status, exit_reason, dry_run)
           VALUES ('heal-002', '2026-06-01T10:00:00+00:00', '2026-06-01T10:05:00+00:00',
                   'btc-up-5m', 'BTC', 'YES', 0.20, 50.0, 0.10, 75.0,
                   'closed', 'market_expired', 1)"""
    )
    await mem_db.commit()

    with patch("main_loop.fetch_resolved", new_callable=AsyncMock) as mock_res:
        mock_res.return_value = None
        await _heal_pending_resolutions(mem_db, [], limit=3)

    async with mem_db.execute(
        "SELECT pm_exit_price FROM positions WHERE position_id='heal-002'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] is None


@pytest.mark.asyncio
async def test_heal_respects_limit(mem_db):
    """limit=2 → 5 null kayıt varsa sadece 2 işlenir, 3 null kalır."""
    for i in range(5):
        await mem_db.execute(
            f"""INSERT INTO positions
                   (position_id, ts_open, ts_close, slug, asset, action, pm_entry_price,
                    position_usd, kelly_f, confidence_score, status, exit_reason, dry_run)
               VALUES ('lim-{i:03d}', '2026-06-01T10:00:00+00:00', '2026-06-01T10:05:00+00:00',
                       'slug-{i}', 'BTC', 'YES', 0.20, 50.0, 0.10, 75.0,
                       'closed', 'market_expired', 1)"""
        )
    await mem_db.commit()

    with patch("main_loop.fetch_resolved", new_callable=AsyncMock) as mock_res:
        mock_res.return_value = {"yes_exit": 1.0, "no_exit": 0.0}
        await _heal_pending_resolutions(mem_db, [], limit=2)

    async with mem_db.execute(
        "SELECT COUNT(*) FROM positions WHERE pm_exit_price IS NULL AND status='closed'"
    ) as cur:
        remaining = (await cur.fetchone())[0]
    assert remaining == 3  # 5 - 2 = 3 hâlâ null
```

- [ ] **Step 3: Testleri çalıştır — FAIL bekliyoruz**

```bash
pytest tests/test_main_loop.py::test_heal_fixes_null_pnl_when_api_returns -v
```

Beklenen: `ImportError: cannot import name '_heal_pending_resolutions'`

- [ ] **Step 4: `_heal_pending_resolutions` fonksiyonunu `main_loop.py`'e ekle**

`main_loop.py`'deki `from db.logger import ...` satırını güncelle (21. satır):

```python
from db.logger import log_candidate, log_position_open, log_position_close, load_closed_today, get_connection, patch_position_resolution
```

Ardından `_monitor_positions` fonksiyonundan hemen ÖNCE (148. satırdan önce) yeni fonksiyonu ekle:

```python
async def _heal_pending_resolutions(
    conn,
    closed_today: list[dict],
    limit: int = 3,
) -> None:
    """market_expired + pm_exit_price=None kayıtları için resolution retry eder."""
    if conn is None:
        return
    async with conn.execute(
        """SELECT position_id, slug, action, pm_entry_price, position_usd
           FROM positions
           WHERE status='closed' AND pm_exit_price IS NULL
           LIMIT ?""",
        (limit,),
    ) as cur:
        rows = await cur.fetchall()

    for position_id, slug, action, pm_entry_price, position_usd in rows:
        try:
            resolution = await fetch_resolved(slug)
            if resolution is None:
                continue
            pm_exit      = resolution["yes_exit"] if action == "YES" else resolution["no_exit"]
            realized_pnl = (pm_exit - pm_entry_price) / pm_entry_price * position_usd
            await patch_position_resolution(conn, position_id, pm_exit, realized_pnl)
            for pos in closed_today:
                if pos.get("position_id") == position_id:
                    pos["pm_exit_price"] = pm_exit
                    pos["realized_pnl"]  = realized_pnl
                    pos["exit_reason"]   = "market_resolved_late"
                    break
        except Exception as e:
            print(f"[heal] {slug} hata: {e}")
```

- [ ] **Step 5: `main()` içindeki ana döngüye heal çağrısı ekle**

`main_loop.py`'deki while True bloğunu güncelle. `await _scan_and_execute(...)` satırından SONRA, `asyncio.sleep` öncesine ekle:

```python
            await _scan_and_execute(open_positions, closed_today, BANKROLL_USD, conn=conn)
            for pos in open_positions[n_open_before:]:
                notify_open(pos)

            await _heal_pending_resolutions(conn, closed_today)   # ← EKLE
```

- [ ] **Step 6: Testleri çalıştır — 3 PASS bekliyoruz**

```bash
pytest tests/test_main_loop.py::test_heal_fixes_null_pnl_when_api_returns \
       tests/test_main_loop.py::test_heal_skips_when_api_still_none \
       tests/test_main_loop.py::test_heal_respects_limit -v
```

Beklenen: 3 PASSED

- [ ] **Step 7: Tüm test suite**

```bash
pytest tests/ -q --tb=short
```

Beklenen: önceki sayı + 3 yeni PASSED, 0 FAILED

- [ ] **Step 8: Commit**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(main_loop): _heal_pending_resolutions — market_expired retry her scan'de"
```

---

## Task 4: Verification — Strateji Analizine Hazırlık

- [ ] **Step 1: Backfill script'i çalıştır (Task 2 zaten yaptıysa atla)**

```bash
python analysis/backfill_expired.py
```

- [ ] **Step 2: DB durumunu doğrula**

```bash
python -c "
import asyncio, aiosqlite

async def check():
    async with aiosqlite.connect('logs/mispricing.db') as db:
        async with db.execute(
            'SELECT exit_reason, COUNT(*), ROUND(SUM(COALESCE(realized_pnl,0)),2), '
            'SUM(CASE WHEN realized_pnl IS NULL THEN 1 ELSE 0 END) null_cnt '
            'FROM positions WHERE status=\"closed\" GROUP BY exit_reason'
        ) as c:
            print(f'  {\"exit_reason\":25} {\"count\":>5} {\"toplam_pnl\":>12} {\"null_pnl\":>8}')
            for r in await c.fetchall():
                print(f'  {r[0]:25} {r[1]:5} {r[2]:12.2f} {r[3]:8}')
asyncio.run(check())
"
```

Beklenen: `market_expired` null_cnt = 0 (ya da çok az, iptal marketler).

- [ ] **Step 3: Performance analizi**

```bash
python analysis/performance.py
```

Tüm trade'lerin P&L'i doluysa anlamlı istatistik gelecek.

- [ ] **Step 4: Son commit — graphify güncelle**

```bash
graphify update .
git add graphify-out/
git commit -m "chore: graphify update — market_expired heal sprint"
```
