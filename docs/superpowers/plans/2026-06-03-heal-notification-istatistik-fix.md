# Heal Notification + İstatistik Berabere Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) Heal edilen pozisyonlar için Telegram'a ikinci bildirim gönder; (2) /istatistik'te berabere sayısını göster ve win rate matematiğini düzelt.

**Architecture:** `notify_resolved_late` notifier.py'e eklenir. `_heal_pending_resolutions` query'sine `asset, seq_no` eklenerek heal sonrası bu fonksiyon çağrılır. `_query_stats` berabere sayısı döndürür, `build_stats_message` berabere satırı ve düzeltilmiş win rate gösterir. Hiçbir trading mantığı değişmez.

**Tech Stack:** Python, aiosqlite, requests, pytest, pytest-asyncio

---

## Değişen Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `monitor/notifier.py` | `notify_resolved_late` fonksiyonu ekle |
| `main_loop.py` | import + SELECT query + notify çağrısı |
| `monitor/telegram_commands.py` | `_query_stats` + `build_stats_message` + call site |
| `tests/test_monitor.py` | 3 yeni test |
| `tests/test_main_loop.py` | 3 mevcut heal testine mock ekle + 2 yeni test |
| `tests/test_telegram_commands.py` | 4 yeni test |

---

## Task 1: notify_resolved_late fonksiyonu

**Files:**
- Modify: `monitor/notifier.py` (satır 61 civarı, `notify_halt`'tan önce)
- Modify: `tests/test_monitor.py` (sona ekle)

- [ ] **Step 1: Failing testleri yaz**

`tests/test_monitor.py` dosyasının sonuna ekle:

```python
def test_notify_resolved_late_kazandi():
    """WIN pozisyon için GÜNCELLENDİ + ✅ içeren mesaj gönderir."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_resolved_late({
            "seq_no": 56, "asset": "XRP", "action": "YES",
            "pm_entry_price": 0.5, "pm_exit_price": 1.0, "position_usd": 1.25,
        })
    msg = mock_send.call_args[0][0]
    assert "GÜNCELLENDİ" in msg
    assert "#56" in msg
    assert "XRP" in msg
    assert "✅" in msg


def test_notify_resolved_late_kaybetti():
    """LOSS pozisyon için ❌ içeren mesaj gönderir."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_resolved_late({
            "seq_no": 10, "asset": "BTC", "action": "YES",
            "pm_entry_price": 0.51, "pm_exit_price": 0.0, "position_usd": 1.25,
        })
    msg = mock_send.call_args[0][0]
    assert "❌" in msg


def test_notify_resolved_late_no_exit_price():
    """pm_exit_price=None ise P&L satırı olmadan yine de mesaj gönderir."""
    with patch("monitor.notifier.send_telegram") as mock_send:
        notifier.notify_resolved_late({
            "asset": "ETH", "action": "NO",
            "pm_entry_price": 0.5, "pm_exit_price": None, "position_usd": 1.25,
        })
    mock_send.assert_called_once()
```

- [ ] **Step 2: Test koş — RED bekle**

```bash
cd /root/mispricing_agent
pytest tests/test_monitor.py::test_notify_resolved_late_kazandi -v
```

Beklenen: `AttributeError: module 'monitor.notifier' has no attribute 'notify_resolved_late'`

- [ ] **Step 3: notify_resolved_late ekle**

`monitor/notifier.py`'de `notify_halt` fonksiyonundan (satır 61) hemen önce ekle:

```python
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
    send_telegram(msg)
```

- [ ] **Step 4: Test koş — GREEN bekle**

```bash
pytest tests/test_monitor.py -v
```

Beklenen: tüm test_monitor testleri PASS (öncekiler + 3 yeni)

- [ ] **Step 5: Commit**

```bash
git add monitor/notifier.py tests/test_monitor.py
git commit -m "feat(notifier): notify_resolved_late — heal bildirimi"
```

---

## Task 2: _heal_pending_resolutions notify çağrısı

**Files:**
- Modify: `main_loop.py` (satır 23 import + satır 163-192 fonksiyon)
- Modify: `tests/test_main_loop.py` (3 mevcut test güncelle + 2 yeni)

- [ ] **Step 1: Yeni failing testleri yaz**

`tests/test_main_loop.py`'de `test_heal_respects_limit` testinden sonra ekle:

```python
@pytest.mark.asyncio
async def test_heal_calls_notify_resolved_late(mem_db):
    """Heal başarılıysa notify_resolved_late doğru asset/seq_no ile çağrılır."""
    await mem_db.execute(
        """INSERT INTO positions
               (position_id, ts_open, ts_close, slug, asset, action, pm_entry_price,
                position_usd, kelly_f, confidence_score, status, exit_reason, dry_run, seq_no)
           VALUES ('heal-ntf', '2026-06-01T10:00:00+00:00', '2026-06-01T10:05:00+00:00',
                   'xrp-updown-5m-1000', 'XRP', 'YES', 0.5, 1.25, 0.30, 80.0,
                   'closed', 'market_expired', 1, 99)"""
    )
    await mem_db.commit()

    with patch("main_loop.fetch_resolved", new_callable=AsyncMock) as mock_res, \
         patch("main_loop.notify_resolved_late") as mock_notify:
        mock_res.return_value = {"yes_exit": 1.0, "no_exit": 0.0}
        await _heal_pending_resolutions(mem_db, [], limit=3)

    mock_notify.assert_called_once()
    call_pos = mock_notify.call_args[0][0]
    assert call_pos["asset"] == "XRP"
    assert call_pos["seq_no"] == 99
    assert call_pos["pm_exit_price"] == 1.0
    assert call_pos["action"] == "YES"


@pytest.mark.asyncio
async def test_heal_no_notify_when_api_none(mem_db):
    """fetch_resolved None döndürürse notify_resolved_late çağrılmaz."""
    await mem_db.execute(
        """INSERT INTO positions
               (position_id, ts_open, ts_close, slug, asset, action, pm_entry_price,
                position_usd, kelly_f, confidence_score, status, exit_reason, dry_run)
           VALUES ('heal-no-ntf', '2026-06-01T10:00:00+00:00', '2026-06-01T10:05:00+00:00',
                   'btc-updown-5m-2000', 'BTC', 'YES', 0.5, 1.25, 0.30, 80.0,
                   'closed', 'market_expired', 1)"""
    )
    await mem_db.commit()

    with patch("main_loop.fetch_resolved", new_callable=AsyncMock) as mock_res, \
         patch("main_loop.notify_resolved_late") as mock_notify:
        mock_res.return_value = None
        await _heal_pending_resolutions(mem_db, [], limit=3)

    mock_notify.assert_not_called()
```

- [ ] **Step 2: Test koş — RED bekle**

```bash
pytest tests/test_main_loop.py::test_heal_calls_notify_resolved_late -v
```

Beklenen: `ImportError` veya `AssertionError: Expected 'notify_resolved_late' to have been called once`

- [ ] **Step 3: main_loop.py import satırını güncelle**

Satır 23'ü bul (`from monitor.notifier import ...`) ve `notify_resolved_late` ekle:

```python
# Eski:
from monitor.notifier import notify_open, notify_close, notify_halt, notify_restart, notify_soft_stop, notify_hard_stop

# Yeni:
from monitor.notifier import notify_open, notify_close, notify_halt, notify_restart, notify_soft_stop, notify_hard_stop, notify_resolved_late
```

- [ ] **Step 4: _heal_pending_resolutions query ve loop güncelle**

`main_loop.py` satır 163-192 arasındaki tüm fonksiyon gövdesini şununla değiştir:

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
        """SELECT position_id, slug, asset, action, pm_entry_price, position_usd, seq_no
           FROM positions
           WHERE status='closed' AND pm_exit_price IS NULL
           LIMIT ?""",
        (limit,),
    ) as cur:
        rows = await cur.fetchall()

    for position_id, slug, asset, action, pm_entry_price, position_usd, seq_no in rows:
        try:
            resolution = await fetch_resolved(slug)
            if resolution is None:
                continue
            pm_exit      = resolution["yes_exit"] if action == "YES" else resolution["no_exit"]
            if not pm_entry_price:
                print(f"[heal] {slug} pm_entry_price=0, skipping")
                continue
            realized_pnl = (pm_exit - pm_entry_price) / pm_entry_price * position_usd
            await patch_position_resolution(conn, position_id, pm_exit, realized_pnl)
            for pos in closed_today:
                if pos.get("position_id") == position_id:
                    pos["pm_exit_price"] = pm_exit
                    pos["realized_pnl"]  = realized_pnl
                    pos["exit_reason"]   = "market_resolved_late"
                    break
            notify_resolved_late({
                "seq_no":         seq_no,
                "asset":          asset,
                "action":         action,
                "pm_entry_price": pm_entry_price,
                "pm_exit_price":  pm_exit,
                "position_usd":   position_usd,
            })
        except Exception as e:
            print(f"[heal] {slug} hata: {e}")
```

- [ ] **Step 5: Mevcut 3 heal testine mock ekle**

`test_heal_fixes_null_pnl_when_api_returns`, `test_heal_skips_when_api_still_none`, `test_heal_respects_limit` testlerinin her birinde `with patch(...)` bloğuna şunu ekle:

```python
# Her üç testte şu satırı with bloğuna ekle:
patch("main_loop.notify_resolved_late"),
```

Örnek — `test_heal_fixes_null_pnl_when_api_returns`:
```python
with patch("main_loop.fetch_resolved", new_callable=AsyncMock) as mock_res, \
     patch("main_loop.notify_resolved_late"):          # ← EKLENDİ
    mock_res.return_value = {"yes_exit": 1.0, "no_exit": 0.0}
    await _heal_pending_resolutions(mem_db, closed_today, limit=3)
```

Aynı pattern'i `test_heal_skips_when_api_still_none` ve `test_heal_respects_limit` için de uygula.

- [ ] **Step 6: Heal testlerini koş — hepsi GREEN**

```bash
pytest tests/test_main_loop.py -k "heal" -v
```

Beklenen: 5 test PASS (3 eski + 2 yeni)

- [ ] **Step 7: Tüm testler**

```bash
pytest --tb=short -q
```

Beklenen: tüm testler PASS, 0 failed

- [ ] **Step 8: Commit**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(main_loop): heal sonrasi notify_resolved_late bildirimi"
```

---

## Task 3: /istatistik berabere fix

**Files:**
- Modify: `monitor/telegram_commands.py` (`_query_stats` + `build_stats_message` + call site)
- Modify: `tests/test_telegram_commands.py` (sona ekle)

- [ ] **Step 1: Failing testleri yaz**

`tests/test_telegram_commands.py`'de son testin arkasına ekle:

```python
def test_build_stats_shows_breakeven_when_nonzero():
    """breakeven>0 iken 'Berabere' satırı mesaja eklenmeli."""
    from monitor.telegram_commands import build_stats_message
    msg = build_stats_message(total=167, wins=139, losses=19, pnl=100.0,
                              hours=None, expired=1, breakeven=8)
    assert "Berabere" in msg
    assert "8" in msg


def test_build_stats_no_breakeven_line_when_zero():
    """breakeven=0 iken 'Berabere' satırı görünmemeli."""
    from monitor.telegram_commands import build_stats_message
    msg = build_stats_message(total=100, wins=80, losses=20, pnl=50.0,
                              hours=None, expired=0, breakeven=0)
    assert "Berabere" not in msg


def test_build_stats_win_rate_uses_wins_plus_losses_only():
    """Win rate = wins/(wins+losses) — expired ve berabere dahil edilmez."""
    from monitor.telegram_commands import build_stats_message
    # 139/(139+19) = 87.97...% → 88.0%
    msg = build_stats_message(total=167, wins=139, losses=19, pnl=100.0,
                              hours=None, expired=1, breakeven=8)
    assert "88.0%" in msg


def test_build_stats_win_rate_unchanged_when_no_breakeven():
    """Berabere=0 iken win rate değişmez — geriye dönük uyumluluk."""
    from monitor.telegram_commands import build_stats_message
    # 75/(75+25) = 75.0% — eski toplam-bazlı hesapla aynı sonuç
    msg = build_stats_message(total=100, wins=75, losses=25, pnl=150.0,
                              hours=None, breakeven=0)
    assert "75.0%" in msg
```

- [ ] **Step 2: Test koş — RED bekle**

```bash
pytest tests/test_telegram_commands.py::test_build_stats_shows_breakeven_when_nonzero -v
```

Beklenen: `TypeError: build_stats_message() got an unexpected keyword argument 'breakeven'`

- [ ] **Step 3: _query_stats güncelle**

`_query_stats` fonksiyonundaki `c.execute` çağrısını bul ve güncelle:

```python
# Eski:
c.execute(
    f"SELECT COUNT(*), SUM(realized_pnl), "
    f"COUNT(CASE WHEN realized_pnl>0 THEN 1 END), "
    f"COUNT(CASE WHEN realized_pnl<0 THEN 1 END), "
    f"COUNT(CASE WHEN pm_exit_price IS NULL THEN 1 END) "
    f"FROM positions {where}", params
)
row = c.fetchone()
conn.close()
return {
    "total":   row[0] or 0,
    "pnl":     row[1] or 0.0,
    "wins":    row[2] or 0,
    "losses":  row[3] or 0,
    "expired": row[4] or 0,
}

# Yeni:
c.execute(
    f"SELECT COUNT(*), SUM(realized_pnl), "
    f"COUNT(CASE WHEN realized_pnl>0 THEN 1 END), "
    f"COUNT(CASE WHEN realized_pnl<0 THEN 1 END), "
    f"COUNT(CASE WHEN pm_exit_price IS NULL THEN 1 END), "
    f"COUNT(CASE WHEN realized_pnl=0 AND pm_exit_price IS NOT NULL THEN 1 END) "
    f"FROM positions {where}", params
)
row = c.fetchone()
conn.close()
return {
    "total":     row[0] or 0,
    "pnl":       row[1] or 0.0,
    "wins":      row[2] or 0,
    "losses":    row[3] or 0,
    "expired":   row[4] or 0,
    "breakeven": row[5] or 0,
}
```

- [ ] **Step 4: build_stats_message güncelle**

```python
# Eski:
def build_stats_message(total: int, wins: int, losses: int, pnl: float, hours: int | None, expired: int = 0) -> str:
    win_rate = wins / total * 100 if total else 0
    label    = f"son {hours} saat" if hours else "tum zamanlar"
    msg = (
        f"=== ISTATISTIK ({label}) ===\n"
        f"Trade     : {total}\n"
        f"Win/Loss  : {wins}/{losses}\n"
        f"Win rate  : {win_rate:.1f}%\n"
        f"Net P&L   : ${pnl:+.2f}"
    )
    if expired:
        msg += f"\nExpired   : {expired} (PnL bekleniyor)"
    return msg

# Yeni:
def build_stats_message(total: int, wins: int, losses: int, pnl: float, hours: int | None, expired: int = 0, breakeven: int = 0) -> str:
    denominator = wins + losses
    win_rate    = wins / denominator * 100 if denominator else 0
    label       = f"son {hours} saat" if hours else "tum zamanlar"
    msg = (
        f"=== ISTATISTIK ({label}) ===\n"
        f"Trade     : {total}\n"
        f"Win/Loss  : {wins}/{losses}\n"
        f"Win rate  : {win_rate:.1f}%\n"
        f"Net P&L   : ${pnl:+.2f}"
    )
    if breakeven:
        msg += f"\nBerabere  : {breakeven}"
    if expired:
        msg += f"\nExpired   : {expired} (PnL bekleniyor)"
    return msg
```

- [ ] **Step 5: Call site güncelle**

`poll_commands` içindeki çağrıyı bul ve `breakeven` ekle:

```python
# Eski:
return build_stats_message(s["total"], s["wins"], s["losses"], s["pnl"], hours, s.get("expired", 0))

# Yeni:
return build_stats_message(s["total"], s["wins"], s["losses"], s["pnl"], hours, s.get("expired", 0), s.get("breakeven", 0))
```

- [ ] **Step 6: Test koş — GREEN bekle**

```bash
pytest tests/test_telegram_commands.py -v
```

Beklenen: tüm test_telegram_commands testleri PASS (öncekiler + 4 yeni)

- [ ] **Step 7: Tüm testler**

```bash
pytest --tb=short -q
```

Beklenen: 0 failed

- [ ] **Step 8: Commit**

```bash
git add monitor/telegram_commands.py tests/test_telegram_commands.py
git commit -m "fix(istatistik): berabere sayisi goster + win rate duzeltmesi"
```
