# Faz 1: MAE/MFE + Telemetri Loglama — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Her trade kapanışında 22 yeni telemetri alanını DB'ye yaz — MAE/MFE (pozisyonun gerçek fiyat yolculuğu), stop slippage (trigger vs fill gap), ve sell timing — hiçbir strateji parametresine dokunmadan.

**Architecture:** `check_exit()` her çağrıda `pos` dict'ini in-memory günceller (MAE/MFE), stop tetiklendiğinde anlık snapshot alır. `sell_position()` CLOB/WS'den book durumu + fill timing yakalar. `close_position()` tüm yeni alanları spread'ler, `log_position_close()` bunları DB'ye yazar.

**Tech Stack:** Python 3.11, aiosqlite (SQLite migrations), `data.ws_prices` (WS bid/ask cache), `execution.clob_client` (FAK orders)

---

## Dosya Haritası

| Dosya | Değişiklik |
|-------|-----------|
| `db/schema.py` | `_MIGRATIONS` listesine 22 yeni `ALTER TABLE` ekle |
| `db/logger.py` | `log_position_close()` UPDATE sorgusunu genişlet |
| `position/manager.py` | `check_exit()`: MAE/MFE tracking + stop trigger snapshot |
| `execution/position_store.py` | `sell_position()`: book snapshot + timing + fill metrics |
| `tests/test_db.py` | Schema kolon testi + telemetri yazma/okuma testi |
| `tests/test_position.py` | MAE/MFE tracking + stop trigger testleri |
| `tests/test_position_store.py` | Book snapshot + timing + sl_fill testleri |

---

## 22 Yeni Kolon Tanımı

| Kolon | Tip | Kim yazar | Açıklama |
|-------|-----|-----------|----------|
| `mae_pct` | REAL | `check_exit` | `(min_val - entry) / entry` |
| `mfe_pct` | REAL | `check_exit` | `(max_val - entry) / entry` |
| `mae_px` | REAL | `check_exit` | MAE anındaki token değeri |
| `mfe_px` | REAL | `check_exit` | MFE anındaki token değeri |
| `mae_ts` | TEXT | `check_exit` | MAE timestamp |
| `mfe_ts` | TEXT | `check_exit` | MFE timestamp |
| `mae_data_quality` | TEXT | `check_exit` | `'rest'` (YES) veya `'estimated'` (NO: 1-ask) |
| `price_source` | TEXT | `check_exit` | `'rest'` (Faz 1); Faz 2'de `'ws_bid'` |
| `sl_trigger_px` | REAL | `check_exit` | Stop kararı anındaki token değeri |
| `sl_trigger_pct` | REAL | `check_exit` | `(trigger_px - entry) / entry` |
| `first_trigger_ts` | TEXT | `check_exit` | İlk stop kararı timestamp (`setdefault`) |
| `exit_bid_at_trigger` | REAL | `sell_position` | CLOB bid (ilk satış denemesinde) |
| `exit_ask_at_trigger` | REAL | `sell_position` | WS ask (ilk satış denemesinde) |
| `spread_at_trigger` | REAL | `sell_position` | `ask - bid` (ilk deneme) |
| `book_depth_at_trigger` | REAL | `sell_position` | `None` (Faz 2'de WS book) |
| `sell_attempt_count` | INTEGER | `sell_position` | Toplam satış denemesi sayısı |
| `sell_unmatched_count` | INTEGER | `sell_position` | FAK kill / hata sayısı |
| `fill_ts` | TEXT | `sell_position` | Başarılı fill timestamp |
| `sl_fill_px` | REAL | `sell_position` | Gerçek fill fiyatı |
| `sl_fill_pct` | REAL | `sell_position` | `(fill_px - entry) / entry` |
| `trigger_fill_gap_pct` | REAL | `sell_position` | `sl_fill_pct - sl_trigger_pct` (negatif = kötü) |
| `trigger_to_fill_secs` | REAL | `sell_position` | `fill_ts - first_trigger_ts` (saniye) |

---

## Task 1: DB Schema Migrasyonu

**Files:**
- Modify: `db/schema.py` — `_MIGRATIONS` listesi
- Test: `tests/test_db.py`

- [ ] **Step 1: Failing testi yaz**

`tests/test_db.py`'e ekle (mevcut `test_positions_schema_has_ref_price_and_edge` testinin altına):

```python
@pytest.mark.asyncio
async def test_schema_has_faz1_telemetry_columns(conn):
    """init_schema sonrası 22 Faz 1 telemetri kolonu positions tablosunda var."""
    async with conn.execute("PRAGMA table_info(positions)") as cur:
        cols = {row[1] for row in await cur.fetchall()}
    expected = [
        "mae_pct", "mfe_pct", "mae_px", "mfe_px", "mae_ts", "mfe_ts",
        "mae_data_quality", "price_source",
        "sl_trigger_px", "sl_trigger_pct", "first_trigger_ts",
        "exit_bid_at_trigger", "exit_ask_at_trigger", "spread_at_trigger",
        "book_depth_at_trigger", "sell_attempt_count", "sell_unmatched_count",
        "fill_ts", "sl_fill_px", "sl_fill_pct", "trigger_fill_gap_pct",
        "trigger_to_fill_secs",
    ]
    missing = [c for c in expected if c not in cols]
    assert not missing, f"Eksik kolonlar: {missing}"
```

- [ ] **Step 2: Testi çalıştır, kırmızı olduğunu doğrula**

```
cd /root/mispricing_agent && python -m pytest tests/test_db.py::test_schema_has_faz1_telemetry_columns -v
```
Beklenen: `FAILED` — `AssertionError: Eksik kolonlar: ['mae_pct', ...]`

- [ ] **Step 3: Implementasyonu yaz**

`db/schema.py` — `_MIGRATIONS` listesine ekle (mevcut son satırın altına):

```python
    # Faz 1: MAE/MFE + stop slippage + sell timing telemetrisi
    "ALTER TABLE positions ADD COLUMN mae_pct REAL",
    "ALTER TABLE positions ADD COLUMN mfe_pct REAL",
    "ALTER TABLE positions ADD COLUMN mae_px REAL",
    "ALTER TABLE positions ADD COLUMN mfe_px REAL",
    "ALTER TABLE positions ADD COLUMN mae_ts TEXT",
    "ALTER TABLE positions ADD COLUMN mfe_ts TEXT",
    "ALTER TABLE positions ADD COLUMN mae_data_quality TEXT",
    "ALTER TABLE positions ADD COLUMN price_source TEXT",
    "ALTER TABLE positions ADD COLUMN sl_trigger_px REAL",
    "ALTER TABLE positions ADD COLUMN sl_trigger_pct REAL",
    "ALTER TABLE positions ADD COLUMN first_trigger_ts TEXT",
    "ALTER TABLE positions ADD COLUMN exit_bid_at_trigger REAL",
    "ALTER TABLE positions ADD COLUMN exit_ask_at_trigger REAL",
    "ALTER TABLE positions ADD COLUMN spread_at_trigger REAL",
    "ALTER TABLE positions ADD COLUMN book_depth_at_trigger REAL",
    "ALTER TABLE positions ADD COLUMN sell_attempt_count INTEGER",
    "ALTER TABLE positions ADD COLUMN sell_unmatched_count INTEGER",
    "ALTER TABLE positions ADD COLUMN fill_ts TEXT",
    "ALTER TABLE positions ADD COLUMN sl_fill_px REAL",
    "ALTER TABLE positions ADD COLUMN sl_fill_pct REAL",
    "ALTER TABLE positions ADD COLUMN trigger_fill_gap_pct REAL",
    "ALTER TABLE positions ADD COLUMN trigger_to_fill_secs REAL",
```

- [ ] **Step 4: Testi çalıştır, yeşil olduğunu doğrula**

```
python -m pytest tests/test_db.py::test_schema_has_faz1_telemetry_columns -v
```
Beklenen: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add db/schema.py tests/test_db.py
git commit -m "feat(db): Faz 1 — 22 MAE/MFE telemetri kolonu schema migrasyonu"
```

---

## Task 2: log_position_close Telemetri Yazımı

**Files:**
- Modify: `db/logger.py` — `log_position_close()` fonksiyonu
- Test: `tests/test_db.py`

- [ ] **Step 1: Failing testi yaz**

`tests/test_db.py`'e ekle:

```python
@pytest.mark.asyncio
async def test_log_position_close_writes_telemetry(conn):
    """log_position_close MAE/MFE + stop slippage + timing alanlarını DB'ye yazar."""
    # Önce pozisyon aç
    pos = {
        "position_id": "pos-tel-001", "slug": "btc-up-15min", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.5,
        "opened_at": "2026-06-07T10:00:00+00:00",
    }
    await logger.log_position_open(conn, pos)

    closed = {
        **pos,
        "status": "closed",
        "pm_exit_price": 0.22,
        "exit_reason": "stop_loss_hit",
        "closed_at": "2026-06-07T10:14:00+00:00",
        "exit_hl_price": 95100.0,
        # MAE/MFE
        "mae_pct": -0.37,
        "mfe_pct": 0.05,
        "mae_px": 0.22,
        "mfe_px": 0.37,
        "mae_ts": "2026-06-07T10:13:30+00:00",
        "mfe_ts": "2026-06-07T10:02:00+00:00",
        "mae_data_quality": "rest",
        "price_source": "rest",
        # Stop trigger
        "sl_trigger_px": 0.245,
        "sl_trigger_pct": -0.30,
        "first_trigger_ts": "2026-06-07T10:13:25+00:00",
        # Fill
        "exit_bid_at_trigger": 0.24,
        "exit_ask_at_trigger": 0.26,
        "spread_at_trigger": 0.02,
        "book_depth_at_trigger": None,
        "sell_attempt_count": 2,
        "sell_unmatched_count": 1,
        "fill_ts": "2026-06-07T10:13:32+00:00",
        "sl_fill_px": 0.22,
        "sl_fill_pct": -0.371,
        "trigger_fill_gap_pct": -0.071,
        "trigger_to_fill_secs": 7.0,
    }
    await logger.log_position_close(conn, closed)

    async with conn.execute(
        """SELECT mae_pct, mfe_pct, sl_trigger_pct, sl_fill_px,
                  trigger_fill_gap_pct, sell_attempt_count, trigger_to_fill_secs,
                  mae_data_quality, price_source
           FROM positions WHERE position_id='pos-tel-001'"""
    ) as cur:
        row = await cur.fetchone()

    assert abs(row[0] - (-0.37)) < 1e-6,  f"mae_pct yanlış: {row[0]}"
    assert abs(row[1] - 0.05) < 1e-6,     f"mfe_pct yanlış: {row[1]}"
    assert abs(row[2] - (-0.30)) < 1e-6,  f"sl_trigger_pct yanlış: {row[2]}"
    assert abs(row[3] - 0.22) < 1e-6,     f"sl_fill_px yanlış: {row[3]}"
    assert abs(row[4] - (-0.071)) < 1e-6, f"trigger_fill_gap_pct yanlış: {row[4]}"
    assert row[5] == 2,                    f"sell_attempt_count yanlış: {row[5]}"
    assert abs(row[6] - 7.0) < 1e-6,      f"trigger_to_fill_secs yanlış: {row[6]}"
    assert row[7] == "rest",               f"mae_data_quality yanlış: {row[7]}"
    assert row[8] == "rest",               f"price_source yanlış: {row[8]}"
```

- [ ] **Step 2: Testi çalıştır, kırmızı olduğunu doğrula**

```
python -m pytest tests/test_db.py::test_log_position_close_writes_telemetry -v
```
Beklenen: `FAILED` — UPDATE sorgusunda yeni kolonlar yok

- [ ] **Step 3: Implementasyonu yaz**

`db/logger.py` `log_position_close()` fonksiyonunu şununla değiştir:

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
               exit_reason=?, realized_pnl=?, exit_hl_price=?,
               mae_pct=?, mfe_pct=?, mae_px=?, mfe_px=?,
               mae_ts=?, mfe_ts=?, mae_data_quality=?, price_source=?,
               sl_trigger_px=?, sl_trigger_pct=?, first_trigger_ts=?,
               exit_bid_at_trigger=?, exit_ask_at_trigger=?,
               spread_at_trigger=?, book_depth_at_trigger=?,
               sell_attempt_count=?, sell_unmatched_count=?,
               fill_ts=?, sl_fill_px=?, sl_fill_pct=?,
               trigger_fill_gap_pct=?, trigger_to_fill_secs=?
           WHERE position_id=?""",
        (
            position.get("closed_at", datetime.now(timezone.utc).isoformat()),
            exit_p,
            position.get("exit_reason"),
            realized_pnl,
            position.get("exit_hl_price"),
            position.get("mae_pct"),
            position.get("mfe_pct"),
            position.get("mae_px"),
            position.get("mfe_px"),
            position.get("mae_ts"),
            position.get("mfe_ts"),
            position.get("mae_data_quality"),
            position.get("price_source"),
            position.get("sl_trigger_px"),
            position.get("sl_trigger_pct"),
            position.get("first_trigger_ts"),
            position.get("exit_bid_at_trigger"),
            position.get("exit_ask_at_trigger"),
            position.get("spread_at_trigger"),
            position.get("book_depth_at_trigger"),
            position.get("sell_attempt_count"),
            position.get("sell_unmatched_count"),
            position.get("fill_ts"),
            position.get("sl_fill_px"),
            position.get("sl_fill_pct"),
            position.get("trigger_fill_gap_pct"),
            position.get("trigger_to_fill_secs"),
            position["position_id"],
        ),
    )
    await conn.commit()
```

- [ ] **Step 4: Testi çalıştır, yeşil olduğunu doğrula**

```
python -m pytest tests/test_db.py::test_log_position_close_writes_telemetry -v
```
Beklenen: `PASSED`

- [ ] **Step 5: Mevcut DB testlerinin hâlâ geçtiğini doğrula**

```
python -m pytest tests/test_db.py -v
```
Beklenen: tüm testler `PASSED`

- [ ] **Step 6: Commit**

```bash
git add db/logger.py tests/test_db.py
git commit -m "feat(db): log_position_close Faz 1 telemetri alanlarını yazar"
```

---

## Task 3: check_exit — MAE/MFE Tracking + Stop Trigger Snapshot

**Files:**
- Modify: `position/manager.py` — `check_exit()` fonksiyonu
- Test: `tests/test_position.py`

### Tasarım Notu

- `current_val`: YES pozisyon → `pm_yes_price`, NO pozisyon → `1 - pm_yes_price`
- `mae_px` = trade boyunca görülen en düşük `current_val` (en kötü drawdown)
- `mfe_px` = trade boyunca görülen en yüksek `current_val` (en iyi gain)
- NO pozisyon için `current_val = 1 - pm_yes_price` = YES ask'ın tamamlayıcısı (gerçek NO bid değil) → `mae_data_quality = "estimated"`
- `sl_trigger_px` / `sl_trigger_pct` / `first_trigger_ts`: stop tetiklendiğinde `setdefault` ile yaz — FAK başarısız olup döngü tekrar geldiğinde üzerine yazma
- `now` zaten `check_exit` içinde tanımlı (`opened_at` hesabında kullanılıyor)

- [ ] **Step 1: Failing testleri yaz**

`tests/test_position.py`'e ekle:

```python
# ── Task 3: MAE/MFE in-memory tracking ───────────────────────────────────────

def test_check_exit_tracks_mae_when_price_drops():
    """YES pozisyon: fiyat düşünce mae_px güncellenir."""
    pos = _position("YES", held_minutes=5)
    # İlk çağrı: fiyat 0.35'in altına indi ama stop'a girmedi
    check_exit(pos, hl_price=95000, pm_yes_price=0.32, time_to_expiry_secs=500)
    assert pos.get("mae_px") == pytest.approx(0.32, abs=1e-6)
    expected_pct = (0.32 - 0.35) / 0.35
    assert pos.get("mae_pct") == pytest.approx(expected_pct, abs=1e-6)
    assert pos.get("mae_ts") is not None


def test_check_exit_tracks_mfe_when_price_rises():
    """YES pozisyon: fiyat yükselince mfe_px güncellenir."""
    pos = _position("YES", held_minutes=5)
    check_exit(pos, hl_price=95000, pm_yes_price=0.50, time_to_expiry_secs=500)
    assert pos.get("mfe_px") == pytest.approx(0.50, abs=1e-6)
    expected_pct = (0.50 - 0.35) / 0.35
    assert pos.get("mfe_pct") == pytest.approx(expected_pct, abs=1e-6)
    assert pos.get("mfe_ts") is not None


def test_check_exit_mae_sticks_to_worst_value():
    """MAE, fiyat toparlansa bile en kötü değerde kalır."""
    pos = _position("YES", held_minutes=5)
    check_exit(pos, hl_price=95000, pm_yes_price=0.28, time_to_expiry_secs=500)
    first_mae = pos["mae_px"]
    # Fiyat toparlandı — MAE değişmemeli
    check_exit(pos, hl_price=95000, pm_yes_price=0.40, time_to_expiry_secs=490)
    assert pos["mae_px"] == pytest.approx(first_mae, abs=1e-6)


def test_check_exit_mfe_sticks_to_best_value():
    """MFE, fiyat düşse bile en iyi değerde kalır."""
    pos = _position("YES", held_minutes=5)
    check_exit(pos, hl_price=95000, pm_yes_price=0.52, time_to_expiry_secs=500)
    first_mfe = pos["mfe_px"]
    # Fiyat düştü — MFE değişmemeli
    check_exit(pos, hl_price=95000, pm_yes_price=0.38, time_to_expiry_secs=490)
    assert pos["mfe_px"] == pytest.approx(first_mfe, abs=1e-6)


def test_check_exit_no_position_mae_data_quality_estimated():
    """NO pozisyon: mae_data_quality='estimated' (1-YES ask, gerçek NO bid değil)."""
    pos = _position("NO", held_minutes=5)
    check_exit(pos, hl_price=95000, pm_yes_price=0.70, time_to_expiry_secs=500)
    assert pos.get("mae_data_quality") == "estimated"
    assert pos.get("price_source") == "rest"


def test_check_exit_yes_position_mae_data_quality_rest():
    """YES pozisyon: mae_data_quality='rest'."""
    pos = _position("YES", held_minutes=5)
    check_exit(pos, hl_price=95000, pm_yes_price=0.40, time_to_expiry_secs=500)
    assert pos.get("mae_data_quality") == "rest"
    assert pos.get("price_source") == "rest"


def test_check_exit_stop_captures_trigger_snapshot():
    """Stop tetiklenince sl_trigger_px, sl_trigger_pct, first_trigger_ts set edilir."""
    pos = _position("YES", held_minutes=5)
    entry = pos["pm_entry_price"]  # 0.35
    # Fiyat %31 düştü → stop_loss_hit
    # STOP_LOSS_MAX=0.30, yani eşik: entry * (1 - 0.30) = 0.245
    # 0.35 * 0.69 = 0.2415
    crash_price = round(entry * 0.68, 4)  # ~0.238, stop eşiğinin altında
    result = check_exit(pos, hl_price=95000, pm_yes_price=crash_price, time_to_expiry_secs=500)
    assert result == "stop_loss_hit"
    assert pos.get("sl_trigger_px") == pytest.approx(crash_price, abs=1e-6)
    expected_pct = (crash_price - entry) / entry
    assert pos.get("sl_trigger_pct") == pytest.approx(expected_pct, abs=1e-4)
    assert pos.get("first_trigger_ts") is not None


def test_check_exit_stop_trigger_ts_not_overwritten_on_retry():
    """İkinci stop tetiklemesinde first_trigger_ts değişmez (setdefault)."""
    pos = _position("YES", held_minutes=5)
    entry = pos["pm_entry_price"]  # 0.35
    crash_price = round(entry * 0.68, 4)

    # İlk tetikleme
    check_exit(pos, hl_price=95000, pm_yes_price=crash_price, time_to_expiry_secs=500)
    first_ts = pos["first_trigger_ts"]

    # Sanki FAK başarısız oldu, döngü tekrar çağırdı
    check_exit(pos, hl_price=95000, pm_yes_price=crash_price - 0.01, time_to_expiry_secs=490)
    assert pos["first_trigger_ts"] == first_ts, "first_trigger_ts FAK retry'da değişmemeli"
```

- [ ] **Step 2: Testi çalıştır, kırmızı olduğunu doğrula**

```
python -m pytest tests/test_position.py -k "mae or mfe or stop_captures or trigger_ts" -v
```
Beklenen: tüm yeni testler `FAILED` — `pos.get("mae_px") is None`

- [ ] **Step 3: Implementasyonu yaz**

`position/manager.py` — `check_exit()` fonksiyonunun `entry_price` hesabı ile kâr hedefi arasına ekle. Tam değişiklik (line 119–125 sonrasına):

```python
    entry_price = position["pm_entry_price"]
    if position["action"] == "YES":
        current_val = pm_yes_price
        target_val  = position["fair_value"]
    else:
        current_val = 1 - pm_yes_price
        target_val  = 1 - position["fair_value"]

    # ── MAE/MFE in-memory tracking ────────────────────────────────────────────
    if entry_price and entry_price > 0:
        current_pct = (current_val - entry_price) / entry_price
        position["price_source"] = "rest"
        position["mae_data_quality"] = "estimated" if position["action"] == "NO" else "rest"
        if position.get("mae_px") is None or current_val < position["mae_px"]:
            position["mae_px"]  = current_val
            position["mae_pct"] = current_pct
            position["mae_ts"]  = now.isoformat()
        if position.get("mfe_px") is None or current_val > position["mfe_px"]:
            position["mfe_px"]  = current_val
            position["mfe_pct"] = current_pct
            position["mfe_ts"]  = now.isoformat()
    # ─────────────────────────────────────────────────────────────────────────
```

Ve stop-loss bloğunu (mevcut son `if current_val < ...` satırı) şununla değiştir:

```python
    sl_threshold = _dynamic_stop(held_seconds, time_to_expiry_secs)
    if current_val < entry_price * (1 - sl_threshold):
        position.setdefault("sl_trigger_px",    current_val)
        position.setdefault("first_trigger_ts", now.isoformat())
        if entry_price and entry_price > 0:
            position.setdefault(
                "sl_trigger_pct",
                (current_val - entry_price) / entry_price,
            )
        return "stop_loss_hit"
```

- [ ] **Step 4: Testi çalıştır, yeşil olduğunu doğrula**

```
python -m pytest tests/test_position.py -k "mae or mfe or stop_captures or trigger_ts" -v
```
Beklenen: tüm yeni testler `PASSED`

- [ ] **Step 5: Tüm position testlerini çalıştır**

```
python -m pytest tests/test_position.py -v
```
Beklenen: tüm testler `PASSED`

- [ ] **Step 6: Commit**

```bash
git add position/manager.py tests/test_position.py
git commit -m "feat(manager): check_exit MAE/MFE tracking + stop trigger snapshot"
```

---

## Task 4: sell_position — Book Snapshot + Timing + Fill Metrics

**Files:**
- Modify: `execution/position_store.py` — `sell_position()` fonksiyonu
- Test: `tests/test_position_store.py`

### Tasarım Notu

- `exit_bid_at_trigger`: ilk denemede alınan CLOB bid — `setdefault` ile yazılır (yeniden deneme üzerine yazmaz)
- `exit_ask_at_trigger`: WS ask cache'den — `setdefault`
- `spread_at_trigger`: `ask - bid` — `setdefault`
- `sell_attempt_count`: her `sell_position` çağrısında +1 (yeniden denemeler dahil)
- `sell_unmatched_count`: FAK kill, hata, veya yanıtsız her denemede +1
- `fill_ts`, `sl_fill_px`, `sl_fill_pct`, `trigger_fill_gap_pct`, `trigger_to_fill_secs`: yalnızca başarılı fill'de yazılır
- `trigger_fill_gap_pct` = `sl_fill_pct - sl_trigger_pct` (her ikisi de varsa)
- `first_trigger_ts`: `check_exit` tarafından zaten yazılmış; `sell_position` okur ama değiştirmez
- Gerekli imports: `datetime`, `timezone` (module top'a ekle), `data.ws_prices` (local import — circular dependency riski yok)

- [ ] **Step 1: Failing testleri yaz**

`tests/test_position_store.py`'e ekle (mevcut testlerin sonuna):

```python
# ── Task 4: Book snapshot + timing + fill metrics ─────────────────────────────

@pytest.mark.asyncio
async def test_sell_increments_attempt_count():
    """Her sell_position çağrısı sell_attempt_count'u artırır."""
    pos = _open_pos()
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp()
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.90), \
         patch("execution.position_store.ws_prices"):
        from execution.position_store import sell_position
        await sell_position(pos)
    assert pos.get("sell_attempt_count") == 1


@pytest.mark.asyncio
async def test_sell_increments_unmatched_count_on_fak_kill():
    """FAK kill (status != matched) sell_unmatched_count'u artırır."""
    pos = _open_pos()
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = {"status": "unmatched"}
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.90), \
         patch("execution.position_store.ws_prices"):
        from execution.position_store import sell_position
        result = await sell_position(pos)
    assert result is None
    assert pos.get("sell_unmatched_count") == 1
    assert pos.get("sell_attempt_count") == 1


@pytest.mark.asyncio
async def test_sell_captures_exit_bid_at_trigger_first_attempt_only():
    """exit_bid_at_trigger yalnızca ilk denemede yazılır (setdefault)."""
    pos = _open_pos()
    pos["sell_attempt_count"] = 0  # ilk deneme simüle et
    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp()
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.90), \
         patch("execution.position_store.ws_prices") as mock_ws:
        mock_ws.get_ask.return_value = 0.92
        from execution.position_store import sell_position
        await sell_position(pos)
    assert pos.get("exit_bid_at_trigger") == pytest.approx(0.90, abs=1e-4)
    assert pos.get("exit_ask_at_trigger") == pytest.approx(0.92, abs=1e-4)
    assert pos.get("spread_at_trigger") == pytest.approx(0.02, abs=1e-4)

    # İkinci deneme: bid değişse bile exit_bid_at_trigger değişmez
    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.85), \
         patch("execution.position_store.ws_prices") as mock_ws:
        mock_ws.get_ask.return_value = 0.87
        await sell_position(pos)
    assert pos.get("exit_bid_at_trigger") == pytest.approx(0.90, abs=1e-4)  # değişmedi


@pytest.mark.asyncio
async def test_sell_captures_fill_timing_and_sl_metrics():
    """Başarılı fill: fill_ts, sl_fill_px, sl_fill_pct, trigger_fill_gap_pct, trigger_to_fill_secs set edilir."""
    pos = _open_pos()  # pm_entry_price=0.35, yes_token_id set
    pos["sl_trigger_pct"] = -0.30      # check_exit tarafından set edilmişti
    pos["first_trigger_ts"] = "2026-06-07T10:13:25+00:00"

    fake_client = MagicMock()
    fake_client.create_and_post_order.return_value = _matched_resp(taking="0.286", making="1.3")
    # fill_price = 0.286 / 1.3 = 0.22

    with patch("execution.position_store.get_client", return_value=fake_client), \
         _clob_patch(0.90), \
         patch("execution.position_store.ws_prices"):
        from execution.position_store import sell_position
        fill_price = await sell_position(pos)

    assert fill_price == pytest.approx(0.22, abs=1e-3)
    assert pos.get("sl_fill_px") == pytest.approx(0.22, abs=1e-3)

    entry = 0.35
    expected_fill_pct = (0.22 - entry) / entry  # ≈ -0.371
    assert pos.get("sl_fill_pct") == pytest.approx(expected_fill_pct, abs=1e-3)

    expected_gap = expected_fill_pct - (-0.30)  # ≈ -0.071
    assert pos.get("trigger_fill_gap_pct") == pytest.approx(expected_gap, abs=1e-3)

    assert pos.get("fill_ts") is not None
    assert pos.get("trigger_to_fill_secs") is not None
    assert pos.get("trigger_to_fill_secs") >= 0
```

- [ ] **Step 2: Testi çalıştır, kırmızı olduğunu doğrula**

```
python -m pytest tests/test_position_store.py -k "attempt_count or unmatched or bid_at_trigger or fill_timing" -v
```
Beklenen: tüm yeni testler `FAILED`

- [ ] **Step 3: Implementasyonu yaz**

`execution/position_store.py` — tam yeniden yazma (aynı imza, ek imports ve mutasyonlar):

```python
"""execution/position_store.py — SELL order gönder, fill fiyatını döndür.

Docs: https://docs.polymarket.com/api-reference/introduction
  SELL matched response:
    - status: "matched"
    - takingAmount: USDC received (seller takes USDC from book)
    - makingAmount: shares given (seller gives shares to book)
    - "price" field: DOKÜMANTE DEĞİL — kullanılmaz
  fill_price = takingAmount / makingAmount

  FAK SELL fiyat stratejisi:
    CLOB /price?side=SELL ile gerçek zamanlı bid alınır, 2¢ floor ile FAK gönderilir.
    FAK kill (alıcı yok) → None döner → main_loop pozisyonu AÇIK tutar, sonraki döngüde tekrar dener.
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from execution.clob_client import get_client
from py_clob_client_v2.clob_types import OrderArgs, OrderType
from data.clob_price import get_clob_price
import data.ws_prices as ws_prices

_FLOOR_BUFFER = 0.01   # bid'den bu kadar aşağı floor — PRICE_PREMIUM=0.01 ile simetrik


async def sell_position(pos: dict) -> float | None:
    """Açık pozisyonun token'larını FAK SELL order ile satar.

    pos: position dict — action, yes_token_id, no_token_id, shares gerekli
    Döner:
      float  → fill fiyatı (satış gerçekleşti)
      None   → FAK kill / hata (satış GERÇEKLEŞMEDİ — pozisyonu açık bırak)

    Side effects (pos dict güncellenir):
      sell_attempt_count, sell_unmatched_count, exit_bid_at_trigger,
      exit_ask_at_trigger, spread_at_trigger, fill_ts, sl_fill_px,
      sl_fill_pct, trigger_fill_gap_pct, trigger_to_fill_secs
    """
    action   = pos["action"]
    token_id = pos["yes_token_id"] if action == "YES" else pos["no_token_id"]
    shares   = pos.get("shares") or 0

    if not token_id or shares <= 0:
        print(f"[sell] {pos.get('slug')}: token_id veya shares eksik/sıfır — atlanıyor")
        return None

    # CLOB'dan gerçek zamanlı sell price (stale market API değil)
    clob_bid = await get_clob_price(token_id, side="SELL")
    stale_bid = float(pos.get("current_bid") or 0.0)
    best_bid = clob_bid if clob_bid else stale_bid

    ws_ask = ws_prices.get_ask(token_id)

    # Book snapshot: yalnızca ilk denemede yaz (setdefault)
    pos.setdefault("exit_bid_at_trigger", best_bid if best_bid > 0 else None)
    pos.setdefault("exit_ask_at_trigger", ws_ask)
    if best_bid and ws_ask:
        pos.setdefault("spread_at_trigger", round(ws_ask - best_bid, 4))
    pos["book_depth_at_trigger"] = None  # REST CLOB depth yok; Faz 2 WS ile gelecek

    pos["sell_attempt_count"] = pos.get("sell_attempt_count", 0) + 1

    if best_bid <= 0:
        print(f"[sell] {pos.get('slug')}: bid=0 — CLOB likidite yok, atlanıyor")
        pos["sell_unmatched_count"] = pos.get("sell_unmatched_count", 0) + 1
        return None

    # Floor fiyatı: gerçek bidden _FLOOR_BUFFER kadar aşağı
    floor_price = round(max(0.01, best_bid - _FLOOR_BUFFER), 2)

    order_args = OrderArgs(
        token_id=token_id,
        price=floor_price,
        size=shares,
        side="SELL",
    )

    try:
        client = get_client()
        resp   = client.create_and_post_order(order_args, order_type=OrderType.FAK)
    except Exception as e:
        print(f"[sell] {pos.get('slug')}: SELL hatası — {e} → pozisyon açık kalıyor")
        pos["sell_unmatched_count"] = pos.get("sell_unmatched_count", 0) + 1
        return None

    if not resp:
        print(f"[sell] {pos.get('slug')}: SELL yanıt yok → pozisyon açık kalıyor")
        pos["sell_unmatched_count"] = pos.get("sell_unmatched_count", 0) + 1
        return None

    def _get(obj, key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    status     = (_get(resp, "status", "") or "").lower()
    taking_str = _get(resp, "takingAmount", None)  # USDC received
    making_str = _get(resp, "makingAmount", None)  # shares given

    if status == "matched":
        try:
            taking = float(taking_str) if taking_str else 0.0
            making = float(making_str) if making_str else 0.0
            if making > 0 and taking > 0:
                fill_price = round(taking / making, 6)
                _record_fill(pos, fill_price)
                print(f"[sell] {pos.get('slug')}: SELL FILLED {making:.4f} shares → ${taking:.4f} @ {fill_price:.4f}")
                return fill_price
        except (ValueError, TypeError):
            pass
        # takingAmount/makingAmount yoksa başarılı satış kabul et, floor fiyatı kullan
        _record_fill(pos, floor_price)
        print(f"[sell] {pos.get('slug')}: SELL matched ama amounts eksik, floor={floor_price:.4f}")
        return floor_price

    # status != matched → FAK kill veya başka hata
    pos["sell_unmatched_count"] = pos.get("sell_unmatched_count", 0) + 1
    print(f"[sell] {pos.get('slug')}: SELL {status} (fill yok) → pozisyon açık kalıyor")
    return None


def _record_fill(pos: dict, fill_price: float) -> None:
    """Başarılı fill sonrası timing ve slippage metriklerini pos'a yazar."""
    fill_ts = datetime.now(timezone.utc).isoformat()
    pos["fill_ts"]    = fill_ts
    pos["sl_fill_px"] = fill_price

    entry = pos.get("pm_entry_price")
    if entry and entry > 0:
        sl_fill_pct = round((fill_price - entry) / entry, 6)
        pos["sl_fill_pct"] = sl_fill_pct
        sl_trigger_pct = pos.get("sl_trigger_pct")
        if sl_trigger_pct is not None:
            pos["trigger_fill_gap_pct"] = round(sl_fill_pct - sl_trigger_pct, 6)

    first_trigger_ts = pos.get("first_trigger_ts")
    if first_trigger_ts:
        try:
            dt_trigger = datetime.fromisoformat(first_trigger_ts)
            dt_fill    = datetime.fromisoformat(fill_ts)
            pos["trigger_to_fill_secs"] = round(
                (dt_fill - dt_trigger).total_seconds(), 2
            )
        except ValueError:
            pass
```

- [ ] **Step 4: Testi çalıştır, yeşil olduğunu doğrula**

```
python -m pytest tests/test_position_store.py -k "attempt_count or unmatched or bid_at_trigger or fill_timing" -v
```
Beklenen: tüm yeni testler `PASSED`

- [ ] **Step 5: Tüm position_store testlerini çalıştır**

```
python -m pytest tests/test_position_store.py -v
```
Beklenen: tüm testler `PASSED`

- [ ] **Step 6: Commit**

```bash
git add execution/position_store.py tests/test_position_store.py
git commit -m "feat(store): sell_position book snapshot + timing + fill metrics"
```

---

## Task 5: Full Test Suite + Integration Smoke

**Files:** değişiklik yok — doğrulama

- [ ] **Step 1: Tam test süitini çalıştır**

```
cd /root/mispricing_agent && python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```
Beklenen: `300+ passed, 0 failed` (öncekiyle aynı toplam + yeni testler)

- [ ] **Step 2: Smoke — yeni alanların end-to-end aktığını doğrula**

```python
# Tek seferlik script — main_loop.py'daki `close_position + log_position_close` akışını simüle eder
python3 - <<'EOF'
import asyncio, sys
sys.path.insert(0, ".")
from datetime import datetime, timezone, timedelta
from db.logger import get_connection, log_position_open, log_position_close
from position.manager import check_exit, close_position

async def smoke():
    conn = await get_connection(db_path=__import__("pathlib").Path(":memory:"))
    opened = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    pos = {
        "position_id": "smoke-001", "slug": "btc-up-15min", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.5,
        "opened_at": opened, "status": "open", "dry_run": False,
        "yes_token_id": "tok-yes", "no_token_id": "tok-no",
    }
    await log_position_open(conn, pos)

    # Birkaç fiyat güncellemesi simüle et
    check_exit(pos, 95000, 0.42, 700)  # MFE artması
    check_exit(pos, 95000, 0.38, 680)  # düştü
    check_exit(pos, 95000, 0.24, 650)  # stop_loss_hit!

    # Stop tetiklendi, satış olmuş gibi simüle et
    pos["sl_trigger_pct"] = pos.get("sl_trigger_pct")
    pos["first_trigger_ts"] = pos.get("first_trigger_ts")
    pos["fill_ts"] = datetime.now(timezone.utc).isoformat()
    pos["sl_fill_px"] = 0.22
    entry = 0.35
    pos["sl_fill_pct"] = round((0.22 - entry) / entry, 6)
    if pos.get("sl_trigger_pct") is not None:
        pos["trigger_fill_gap_pct"] = round(pos["sl_fill_pct"] - pos["sl_trigger_pct"], 6)
    pos["sell_attempt_count"] = 1
    pos["exit_bid_at_trigger"] = 0.23

    closed = close_position(pos, "stop_loss_hit", pm_exit_price=0.22)
    await log_position_close(conn, closed)

    import aiosqlite
    async with conn.execute(
        "SELECT mae_pct, mfe_pct, sl_trigger_pct, sl_fill_pct, trigger_fill_gap_pct, price_source FROM positions WHERE position_id='smoke-001'"
    ) as cur:
        row = await cur.fetchone()
    print(f"mae_pct={row[0]:.4f}, mfe_pct={row[1]:.4f}, sl_trigger={row[2]:.4f}, sl_fill={row[3]:.4f}, gap={row[4]:.4f}, src={row[5]}")
    assert row[0] is not None, "mae_pct None!"
    assert row[1] is not None, "mfe_pct None!"
    print("SMOKE PASS ✓")

asyncio.run(smoke())
EOF
```
Beklenen: `SMOKE PASS ✓` ve anlamlı sayılar

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "test: Faz 1 full suite — MAE/MFE + stop slippage telemetri end-to-end"
```

---

## Self-Review Checklist

### Spec coverage
- [x] 22 yeni kolon — Task 1 (schema.py)
- [x] log_position_close tüm yeni alanları yazar — Task 2
- [x] MAE: min price over lifetime — Task 3
- [x] MFE: max price over lifetime — Task 3
- [x] mae_data_quality: YES→"rest", NO→"estimated" — Task 3
- [x] price_source: "rest" (Faz 2'de "ws_bid") — Task 3
- [x] sl_trigger_px/pct: stop kararı anında — Task 3
- [x] first_trigger_ts: setdefault (FAK retry'da değişmez) — Task 3
- [x] exit_bid_at_trigger / ask / spread: ilk denemede — Task 4
- [x] sell_attempt_count / sell_unmatched_count — Task 4
- [x] fill_ts, sl_fill_px, sl_fill_pct — Task 4
- [x] trigger_fill_gap_pct = sl_fill_pct - sl_trigger_pct — Task 4
- [x] trigger_to_fill_secs = fill_ts - first_trigger_ts — Task 4
- [x] TDD: her task için önce failing test, sonra impl — tüm tasklar

### Sıfır Risk Doğrulaması
- `config.py` değiştirilmedi ✓
- `DRY_RUN` dokunulmadı ✓
- Strateji parametreleri değiştirilmedi ✓
- Yalnızca veri toplanıyor ✓
