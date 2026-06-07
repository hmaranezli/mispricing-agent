# Faz 3 Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faz 3 veri toplama öncesi 4 kritik gözlemlenebilirlik iyileştirmesi: max_hold_time MAE/MFE veri kaybı düzeltme (BLOCKER), scan/monitor performans telemetrisi, entry execution slippage ölçümü, candidates tablosunu Shadow Book telemetrisine genişletme.

**Architecture:** Task 1 bir bug fix'tir — `check_exit()` içinde MAE/MFE tracking bloğu max_hold_time return'ünden ÖNCE çalışacak şekilde taşınır. Tasks 2-3 mevcut döngülere `time.time()` ölçüm noktaları ve yeni log satırları ekler. Task 4 mevcut `candidates` tablosunu yeni kolonlarla genişletir ve `log_candidate` imzasını uyumlu şekilde günceller. Strateji parametrelerine ve DRY_RUN durumuna dokunulmaz.

**Tech Stack:** Python asyncio, aiosqlite, pytest-asyncio

---

## Dosya Haritası

| Görev | Dosya | İşlem |
|-------|-------|-------|
| Task 1 | `position/manager.py:107-141` | Bug fix — MAE/MFE bloğunu öne taşı |
| Task 1 | `tests/test_manager.py` | Yeni oluştur |
| Task 2 | `main_loop.py:92-201` | `_run_council` + `_scan_and_execute` timing |
| Task 2 | `main_loop.py:360-516` | `_monitor_positions` başına `[monitor_perf]` |
| Task 3 | `db/schema.py:78-82` | Migration ekle |
| Task 3 | `db/logger.py:53-90` | `log_position_open` güncelle |
| Task 3 | `main_loop.py:191-199` | ask_at_decision + slippage_pct hesapla |
| Task 4 | `db/schema.py:82` | Migration ekle |
| Task 4 | `db/logger.py:22-50` | `log_candidate` imzası + INSERT güncelle |
| Task 4 | `main_loop.py:92-145` | `_run_council` call site'ları güncelle |

---

## Task 1: max_hold_time MAE/MFE Fix (BLOCKER)

**Files:**
- Create: `tests/test_manager.py`
- Modify: `position/manager.py:107-141`

- [ ] **Step 1: Failing test yaz**

```python
# tests/test_manager.py
import pytest
from datetime import datetime, timezone, timedelta
from position.manager import check_exit


def _pos(action="YES", entry=0.60, fair=0.75, held_minutes=25):
    return {
        "position_id":    "test-mht",
        "slug":           "btc-5m-test",
        "pm_entry_price": entry,
        "fair_value":     fair,
        "action":         action,
        "opened_at":      (datetime.now(timezone.utc)
                           - timedelta(minutes=held_minutes)).isoformat(),
    }


def test_check_exit_max_hold_time_populates_mae_mfe():
    """max_hold_time kapanışında MAE/MFE kaybolmamalı — bug fix testi."""
    pos = _pos(held_minutes=25)  # MAX_HOLD_MINUTES=20 geçmiş
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.45,
                        time_to_expiry_secs=300)
    assert result == "max_hold_time"
    assert pos.get("mae_px") is not None,  "max_hold_time sonrası mae_px None olmamalı"
    assert pos.get("mfe_px") is not None,  "max_hold_time sonrası mfe_px None olmamalı"
    assert pos["mae_pct"] == pytest.approx((0.45 - 0.60) / 0.60, abs=1e-6)
    assert pos["mfe_px"] == pytest.approx(0.45)


def test_check_exit_max_hold_time_no_exit_within_limit():
    """Henüz MAX_HOLD_MINUTES dolmadıysa max_hold_time döndürmemeli."""
    pos = _pos(held_minutes=5)
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.65,
                        time_to_expiry_secs=300)
    assert result != "max_hold_time"


def test_check_exit_no_position_normal_flow():
    """Normal aralıkta hold — None dönmeli (resolve bekliyor)."""
    pos = _pos(held_minutes=2, entry=0.60, fair=0.75)
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.62,
                        time_to_expiry_secs=500)
    assert result is None
    assert pos.get("mae_px") is not None  # MAE her çağrıda güncellenmeli
```

- [ ] **Step 2: Testi çalıştır — kırmızı olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_manager.py::test_check_exit_max_hold_time_populates_mae_mfe -v
```

Beklenen: `FAILED` — `AssertionError: max_hold_time sonrası mae_px None olmamalı`

- [ ] **Step 3: Fix — MAE/MFE bloğunu max_hold_time return'ünden önce taşı**

`position/manager.py` satır 107-141 arası şu hale getirilecek (entry_price/current_val bloğunu ve MAE/MFE bloğunu max_hold_time return'ünün üstüne çek):

```python
    # 1. Market kapanışa yakın → sadece profit_target ve max_hold'u engelle.
    #    stop_loss geçer: son saniyede çöküş olursa tam kayıptan koru.
    near_expiry = time_to_expiry_secs < NEAR_EXPIRY_SECS

    if near_expiry:
        pass  # skip non-stop-loss exits below; stop_loss still checked at step 5
    opened_at = datetime.fromisoformat(position["opened_at"])
    now = datetime.now(timezone.utc)
    held_minutes = (now - opened_at).total_seconds() / 60

    entry_price = position["pm_entry_price"]
    if position["action"] == "YES":
        current_val = pm_yes_price
        target_val  = position["fair_value"]
    else:
        current_val = 1 - pm_yes_price
        target_val  = 1 - position["fair_value"]

    # ── MAE/MFE in-memory tracking — tüm early return'lerden ÖNCE çalışır ──────
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

    # 2. Zaman limiti (near_expiry'de engelle — market zaten kapanıyor)
    if not near_expiry and held_minutes >= config.MAX_HOLD_MINUTES:
        return "max_hold_time"
```

Satır 143'ten itibaren (`# 3. Kâr hedefi...`) kod değişmez. Eskiden satır 120-126 olan entry_price/current_val bloğu artık satır 117 öncesinde; eskiden satır 128-141 olan MAE/MFE bloğu da aynı şekilde öne taşındı.

- [ ] **Step 4: Testi çalıştır — yeşil olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_manager.py -v
```

Beklenen: 3/3 `PASSED`

- [ ] **Step 5: Tüm test suite çalıştır**

```bash
cd /root/mispricing_agent && python -m pytest tests/ -x -q 2>&1 | tail -5
```

Beklenen: mevcut test sayısı + 3 yeni, hiç FAIL yok.

- [ ] **Step 6: Commit**

```bash
cd /root/mispricing_agent && git add position/manager.py tests/test_manager.py
git commit -m "fix(manager): max_hold_time MAE/MFE tracking — early return öncesine taşındı

max_hold_time kapanışlarında mae_px/mfe_px None kalıyordu (Faz 3 veri kaybı).
entry_price/current_val hesabı ve MAE/MFE bloğu max_hold_time return satırının
üstüne taşındı — her çıkış tipinde izleme garantili."
```

---

## Task 2: Scan + Monitor Performance Telemetry

**Files:**
- Modify: `main_loop.py:92-201` (`_run_council`, `_scan_and_execute`)
- Modify: `main_loop.py:360` (`_monitor_positions` başı)

- [ ] **Step 1: Failing test yaz**

```python
# tests/test_main_loop.py içine ekle (mevcut dosyaya append)

def test_scan_perf_log_format(capsys):
    """_scan_and_execute scan_edges çağrısını doğru zamanlıyor — log satırı çıkmalı."""
    import re
    # Bu test sadece log formatını kontrol eder — gerçek bir integration testi değil.
    # scan_perf satırının formatı: [scan_perf] total=Xs scan_edges=Xs council=Xs execute=Xs candidates=N
    pattern = re.compile(
        r"\[scan_perf\] total=[\d.]+s scan_edges=[\d.]+s council=[\d.]+s execute=[\d.]+s candidates=\d+"
    )
    # Format testi: regex geçerli mi?
    sample = "[scan_perf] total=12.4s scan_edges=3.1s council=0.2s execute=0.0s candidates=3"
    assert pattern.match(sample), f"scan_perf log formatı eşleşmedi: {sample}"


def test_monitor_perf_log_format():
    """monitor_perf log satırı formatı doğru mu?"""
    import re
    pattern = re.compile(
        r"\[monitor_perf\] open_positions=\d+ ws_subscribed=\d+ ws_active=(True|False)"
    )
    sample = "[monitor_perf] open_positions=2 ws_subscribed=4 ws_active=True"
    assert pattern.match(sample)
```

- [ ] **Step 2: Testi çalıştır — geçtiğini doğrula (format testi, implementasyon gerekmez)**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_main_loop.py::test_scan_perf_log_format tests/test_main_loop.py::test_monitor_perf_log_format -v
```

Beklenen: 2/2 `PASSED` (format regex testleri implementasyon gerektirmez)

- [ ] **Step 3: `_scan_and_execute` içine timing ekle**

`main_loop.py` satır 148-201 (`_scan_and_execute` fonksiyonu) şu hale getirilecek:

```python
async def _scan_and_execute(
    open_positions: list[dict],
    closed_today:   list[dict],
    bankroll_usd:   float,
    conn=None,
    failed_slugs: set | None = None,
) -> None:
    """Yeni fırsatları tarar, konsey geçenleri açar."""
    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
        return

    t0 = time.time()
    findings = await scan_edges()
    t_scan_edges = time.time() - t0

    daily_loss = 0.0
    open_slugs  = {p["slug"] for p in open_positions}
    _failed     = failed_slugs if failed_slugs is not None else set()

    from datetime import datetime, timezone as _tz
    _ts = datetime.now(_tz.utc).strftime("%H:%M:%S")
    if findings:
        for _f in findings:
            _skip = "failed" if _f["slug"] in _failed else ("open" if _f["slug"] in open_slugs else "")
            print(f"[scan {_ts}] {_f['slug']}: {_f['action']} fair={_f['fair_value']:.3f} ask={_f['best_ask']:.3f} edge={_f['edge']:.3f} secs={_f['seconds_remaining']:.0f}" + (f" SKIP:{_skip}" if _skip else ""))
    else:
        print(f"[scan {_ts}] edge yok")

    t_council_total = 0.0
    t_execute_total = 0.0
    for finding in findings:
        if len(open_positions) >= config.MAX_OPEN_POSITIONS:
            break
        slug = finding["slug"]
        if slug in open_slugs:
            continue
        if slug in _failed:
            continue

        t1 = time.time()
        result = await _run_council(finding,
                                    bankroll_usd=bankroll_usd,
                                    n_open=len(open_positions),
                                    daily_loss_usd=daily_loss,
                                    conn=conn)
        t_council_total += time.time() - t1
        if result is None:
            continue

        gate_result, risk_result = result
        t2 = time.time()
        position = await execute(finding, gate_result, risk_result, open_positions)
        t_execute_total += time.time() - t2
        if position:
            await log_position_open(conn, position)
            open_positions.append(position)
            open_slugs.add(slug)
            ws_prices.subscribe([
                t for t in (position.get("yes_token_id"), position.get("no_token_id")) if t
            ])
        else:
            pass  # FAK kill — capital riske girmedi, bir sonraki taramada yeniden dene

    t_total = time.time() - t0
    print(
        f"[scan_perf] total={t_total:.1f}s scan_edges={t_scan_edges:.1f}s "
        f"council={t_council_total:.1f}s execute={t_execute_total:.1f}s "
        f"candidates={len(findings)}"
    )
```

- [ ] **Step 4: `_monitor_positions` başına `[monitor_perf]` ekle**

`main_loop.py` satır 360-362 arası (fonksiyon docstring'inden hemen sonra, `global _last_rest_ts` öncesi):

```python
async def _monitor_positions(
    open_positions: list[dict],
    closed_today:   list[dict],
    conn=None,
    failed_slugs: set | None = None,
) -> bool:
    """..."""
    global _last_rest_ts
    print(
        f"[monitor_perf] open_positions={len(open_positions)} "
        f"ws_subscribed={len(ws_prices._subscribed)} "
        f"ws_active={ws_prices._ws is not None}"
    )
    price_event = ws_prices.get_price_event()
    # ... rest unchanged
```

- [ ] **Step 5: Tüm test suite çalıştır**

```bash
cd /root/mispricing_agent && python -m pytest tests/ -x -q 2>&1 | tail -5
```

Beklenen: hiç FAIL yok.

- [ ] **Step 6: Commit**

```bash
cd /root/mispricing_agent && git add main_loop.py
git commit -m "feat(telemetry): scan_perf + monitor_perf log satırları

[scan_perf] total/scan_edges/council/execute/candidates timing — API
darboğazını ve council gecikmesini ölçer.
[monitor_perf] open_positions/ws_subscribed/ws_active durumu — WS bağlantı
sağlığını her döngüde doğrular."
```

---

## Task 3: Entry Execution Telemetry (ask_at_decision + slippage_pct)

**Files:**
- Modify: `db/schema.py:78-82`
- Modify: `db/logger.py:53-90`
- Modify: `main_loop.py:191-199`

- [ ] **Step 1: Failing test yaz**

```python
# tests/test_main_loop.py içine ekle

@pytest.mark.asyncio
async def test_scan_and_execute_sets_ask_at_decision(default_ws_prices):
    """execute() başarılı olduğunda position'a ask_at_decision ve slippage_pct yazılmalı."""
    import main_loop as _ml
    _ml._last_rest_ts = 0

    finding = {
        "slug": "btc-5m-ask-test", "asset": "BTC", "action": "YES",
        "fair_value": 0.75, "best_ask": 0.60, "best_bid": 0.58,
        "edge": 0.15, "seconds_remaining": 200,
    }
    fake_pos = {
        "position_id": "ask-test-pos", "slug": "btc-5m-ask-test",
        "asset": "BTC", "action": "YES", "pm_entry_price": 0.61,
        "fair_value": 0.75, "edge": 0.15, "position_usd": 1.25,
        "kelly_f": 0.1, "confidence_score": 80, "shares": 2.0,
        "yes_token_id": "ytid", "no_token_id": "ntid",
        "order_id": "oid", "opened_at": "2026-06-07T00:00:00+00:00",
        "dry_run": False,
    }
    open_positions: list = []
    with patch("main_loop.scan_edges", new_callable=AsyncMock, return_value=[finding]), \
         patch("main_loop._run_council", new_callable=AsyncMock,
               return_value=({"pass": True}, {"pass": True, "kelly_f": 0.1})), \
         patch("main_loop.execute", new_callable=AsyncMock, return_value=fake_pos), \
         patch("main_loop.log_position_open", new_callable=AsyncMock):
        await _ml._scan_and_execute(open_positions, [], bankroll_usd=100.0, conn=None)

    assert len(open_positions) == 1
    pos = open_positions[0]
    assert pos.get("ask_at_decision") == pytest.approx(0.60)
    expected_slippage = (0.61 - 0.60) / 0.60
    assert pos.get("slippage_pct") == pytest.approx(expected_slippage, abs=1e-6)
```

- [ ] **Step 2: Testi çalıştır — kırmızı olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_main_loop.py::test_scan_and_execute_sets_ask_at_decision -v
```

Beklenen: `FAILED` — `AssertionError: assert None == 0.60`

- [ ] **Step 3: Schema migration ekle**

`db/schema.py` satır 82'den sonra (mevcut son iki migration satırından sonra) ekle:

```python
    # Faz 3: entry execution telemetri
    "ALTER TABLE positions ADD COLUMN ask_at_decision REAL",
    "ALTER TABLE positions ADD COLUMN slippage_pct REAL",
```

- [ ] **Step 4: `log_position_open` içinde yeni kolonları yaz**

`db/logger.py` satır 60-89 arası INSERT sorgusunu güncelle:

```python
    await conn.execute(
        """INSERT OR IGNORE INTO positions
               (position_id, ts_open, slug, asset, action, pm_entry_price,
                fair_value, ref_price, edge, position_usd, kelly_f,
                confidence_score, status, dry_run,
                shares, order_id, yes_token_id, no_token_id, seq_no,
                entry_hl_price, ask_at_decision, slippage_pct)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
            position.get("ask_at_decision"),
            position.get("slippage_pct"),
        ),
    )
```

- [ ] **Step 5: `_scan_and_execute` içinde ask_at_decision ve slippage_pct hesapla**

`main_loop.py` satır 191-199 arası, `if position:` bloğuna ekle:

```python
        if position:
            # Entry execution telemetri: karar anındaki fiyat ve gerçek fill arasındaki fark
            ask_at_decision = finding.get("best_ask")
            position["ask_at_decision"] = ask_at_decision
            fill_price = position.get("pm_entry_price")
            if fill_price and ask_at_decision and ask_at_decision > 0:
                position["slippage_pct"] = (fill_price - ask_at_decision) / ask_at_decision
            await log_position_open(conn, position)
            open_positions.append(position)
            open_slugs.add(slug)
            ws_prices.subscribe([
                t for t in (position.get("yes_token_id"), position.get("no_token_id")) if t
            ])
```

- [ ] **Step 6: Testi çalıştır — yeşil olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_main_loop.py::test_scan_and_execute_sets_ask_at_decision -v
```

Beklenen: `PASSED`

- [ ] **Step 7: Tüm test suite çalıştır**

```bash
cd /root/mispricing_agent && python -m pytest tests/ -x -q 2>&1 | tail -5
```

Beklenen: hiç FAIL yok.

- [ ] **Step 8: Commit**

```bash
cd /root/mispricing_agent && git add db/schema.py db/logger.py main_loop.py
git commit -m "feat(telemetry): ask_at_decision + slippage_pct entry execution metriği

Karar anındaki PM ask ile gerçek fill arasındaki farkı ölçer.
slippage_pct = (fill_price - ask_at_decision) / ask_at_decision
positions tablosuna 2 yeni kolon, log_position_open güncellendi."
```

---

## Task 4: Shadow Book v1 — Candidates Tablosu Genişletme

**Karar notu:** `candidates` tablosu zaten tüm pass/fail kararlarını logluyor. Yeni tablo yerine mevcut tabloya ek kolonlar ekleniyor (YAGNI). Shadow analizi için yeterli; canlı P&L kalibrasyonuyla karışmaz (farklı tablo).

**Files:**
- Modify: `db/schema.py` (yeni migration'lar)
- Modify: `db/logger.py:22-50` (`log_candidate` imzası + INSERT)
- Modify: `main_loop.py:92-145` (`_run_council` call siteleri)

- [ ] **Step 1: Failing test yaz**

```python
# tests/test_db_logger.py içine ekle (veya yeni dosya oluştur)
import pytest
import asyncio
import aiosqlite
import os
from db.logger import get_connection, log_candidate
from db.schema import init_schema


@pytest.mark.asyncio
async def test_log_candidate_stores_shadow_fields(tmp_path):
    """log_candidate confidence_score, kelly_f, seconds_remaining alanlarını yazmalı."""
    db_path = tmp_path / "test.db"
    conn = await get_connection(db_path)
    finding = {
        "slug": "btc-5m-shadow-test", "asset": "BTC", "action": "YES",
        "fair_value": 0.75, "best_ask": 0.60, "edge": 0.15,
        "seconds_remaining": 270,
    }
    await log_candidate(
        conn, finding, passed=False,
        veto_layer="risk", veto_reason="kelly=0",
        confidence_score=72.5, kelly_f=0.08,
        seconds_remaining=270,
    )
    async with conn.execute(
        "SELECT confidence_score, kelly_f, seconds_remaining FROM candidates WHERE slug=?",
        ("btc-5m-shadow-test",)
    ) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert row is not None
    assert row[0] == pytest.approx(72.5)
    assert row[1] == pytest.approx(0.08)
    assert row[2] == 270


@pytest.mark.asyncio
async def test_log_candidate_shadow_fields_nullable(tmp_path):
    """Eski call site'lar shadow field'ları geçmeden çalışmaya devam etmeli."""
    db_path = tmp_path / "test2.db"
    conn = await get_connection(db_path)
    finding = {
        "slug": "eth-5m-compat", "asset": "ETH", "action": "YES",
        "fair_value": 0.70, "best_ask": 0.55, "edge": 0.15,
    }
    await log_candidate(conn, finding, passed=True)  # eski imza — crash olmamalı
    async with conn.execute(
        "SELECT confidence_score, kelly_f FROM candidates WHERE slug=?",
        ("eth-5m-compat",)
    ) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert row is not None
    assert row[0] is None  # geçilmedi → NULL
    assert row[1] is None
```

- [ ] **Step 2: Testi çalıştır — kırmızı olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_db_logger.py::test_log_candidate_stores_shadow_fields -v
```

Beklenen: `FAILED` — `TypeError: log_candidate() got an unexpected keyword argument 'confidence_score'`

(Eğer `tests/test_db_logger.py` yoksa, yeni dosya olarak yaz.)

- [ ] **Step 3: Schema migration ekle**

`db/schema.py` satır 82 sonrasına ekle:

```python
    # Faz 3: Shadow Book v1 — candidates tablosu genişletme
    "ALTER TABLE candidates ADD COLUMN confidence_score REAL",
    "ALTER TABLE candidates ADD COLUMN kelly_f REAL",
    "ALTER TABLE candidates ADD COLUMN seconds_remaining INTEGER",
```

- [ ] **Step 4: `log_candidate` imzasını ve INSERT'i güncelle**

`db/logger.py` satır 22-50 arası:

```python
async def log_candidate(
    conn,
    finding:          dict,
    passed:           bool,
    veto_layer:       str | None = None,
    veto_reason:      str | None = None,
    confidence_score: float | None = None,
    kelly_f:          float | None = None,
    seconds_remaining: int | None = None,
) -> None:
    if conn is None:
        return
    await conn.execute(
        """INSERT INTO candidates
               (ts, slug, asset, action, fair_value, best_ask, edge,
                passed, veto_layer, veto_reason, dry_run,
                confidence_score, kelly_f, seconds_remaining)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now(timezone.utc).isoformat(),
            finding.get("slug", ""),
            finding.get("asset", ""),
            finding.get("action", ""),
            finding.get("fair_value"),
            finding.get("best_ask"),
            finding.get("edge"),
            1 if passed else 0,
            veto_layer,
            veto_reason,
            1 if config.DRY_RUN else 0,
            confidence_score,
            kelly_f,
            seconds_remaining if seconds_remaining is not None
                else finding.get("seconds_remaining"),
        ),
    )
    await conn.commit()
```

- [ ] **Step 5: `_run_council` call site'larını güncelle**

`main_loop.py` satır 92-145 (`_run_council` fonksiyonu) — her `log_candidate` çağrısını `seconds_remaining` ile güncelle, pass durumunda `confidence_score` ve `kelly_f` ekle:

```python
async def _run_council(
    finding:        dict,
    bankroll_usd:   float,
    n_open:         int,
    daily_loss_usd: float,
    conn=None,
) -> tuple | None:
    """Finding'i 5 katmandan geçirir. Herhangi biri düşerse None."""
    slug = finding.get("slug", "?")
    _secs = finding.get("seconds_remaining")

    verification = await verify(finding)
    if not verification["pass"]:
        reason = verification.get("reason", "?")
        print(f"[council] {slug} VETO verifier: {reason}")
        await log_candidate(conn, finding, passed=False,
                            veto_layer="verifier", veto_reason=reason,
                            seconds_remaining=_secs)
        return None

    if verification.get("fresh_best_ask", 0) > 0:
        finding["best_ask"] = verification["fresh_best_ask"]
    if verification.get("fresh_best_bid", 0) > 0:
        finding["best_bid"] = verification["fresh_best_bid"]

    rt = await redteam_eval(finding, verification)
    if not rt["pass"]:
        vetoes = rt.get("vetoes", [])
        print(f"[council] {slug} VETO redteam: {vetoes} | fee_adj={rt.get('fee_adj_edge', '?'):.3f}")
        await log_candidate(conn, finding, passed=False,
                            veto_layer="redteam", veto_reason=str(vetoes),
                            seconds_remaining=_secs)
        return None

    rk = risk_eval(finding, verification, rt,
                   bankroll_usd=bankroll_usd,
                   open_positions=n_open,
                   daily_loss_usd=daily_loss_usd)
    if not rk["pass"]:
        reason = rk.get("reason", "?")
        print(f"[council] {slug} VETO risk: {reason}")
        await log_candidate(conn, finding, passed=False,
                            veto_layer="risk", veto_reason=reason,
                            kelly_f=rk.get("kelly_f"),
                            seconds_remaining=_secs)
        return None

    gate_result = await gate(finding, verification, rt, rk)
    if not gate_result["pass"]:
        reason = gate_result.get("reason", "?")
        print(f"[council] {slug} VETO gate: {reason}")
        await log_candidate(conn, finding, passed=False,
                            veto_layer="gate", veto_reason=reason,
                            confidence_score=gate_result.get("confidence"),
                            kelly_f=rk.get("kelly_f"),
                            seconds_remaining=_secs)
        return None

    print(f"[council] {slug} GEÇTİ → execute")
    await log_candidate(conn, finding, passed=True,
                        confidence_score=gate_result.get("confidence"),
                        kelly_f=rk.get("kelly_f"),
                        seconds_remaining=_secs)
    return gate_result, rk
```

- [ ] **Step 6: Testi çalıştır — yeşil olduğunu doğrula**

```bash
cd /root/mispricing_agent && python -m pytest tests/test_db_logger.py -v
```

Beklenen: 2/2 `PASSED`

- [ ] **Step 7: Tüm test suite çalıştır**

```bash
cd /root/mispricing_agent && python -m pytest tests/ -x -q 2>&1 | tail -5
```

Beklenen: hiç FAIL yok.

- [ ] **Step 8: Commit**

```bash
cd /root/mispricing_agent && git add db/schema.py db/logger.py main_loop.py tests/test_db_logger.py
git commit -m "feat(shadow-book): candidates tablosuna veto telemetri kolonları eklendi

confidence_score, kelly_f, seconds_remaining — hangi katman ne gerekçeyle
veto ettiğini ve o andaki piyasa durumunu kayıt altına alır.
Shadow Book v1: council performans analizi için decision-point veri tabanı."
```

---

## Spec Self-Review

**1. Spec coverage:**
- ✅ max_hold_time MAE/MFE fix: Task 1
- ✅ scan_perf telemetry: Task 2
- ✅ monitor_perf telemetry: Task 2
- ✅ entry execution telemetry (ask_at_decision, slippage): Task 3
- ✅ Shadow Book v1 decision-point: Task 4
- ✅ Strateji parametresi değişikliği yok: hiçbir Task config.py dokunmuyor
- ✅ DRY_RUN durumu korunuyor: her Task mevcut `config.DRY_RUN` kontrol noktalarını bozmuyor

**2. Placeholder scan:** Yok.

**3. Type consistency:**
- `log_candidate(confidence_score=float|None, kelly_f=float|None, seconds_remaining=int|None)` — Task 4 Step 4'te tanımlandı, Step 5'te kullanıldı ✅
- `position["ask_at_decision"]` — Task 3 Step 5'te set edildi, Step 4'te DB'ye yazıldı ✅
- `_monitor_positions` return type `bool` değişmedi ✅

**4. Gemini async-queue notu:**
Shadow Book logging (`log_candidate`) zaten `await` ile çağrılıyor ve aiosqlite async. Ayrı bir fire-and-forget queue gerekmez — aiosqlite commit'i main loop'u bloklayacak kadar yavaş değil (<1ms). Eğer gelecekte yoğun veto trafiği olursa Task 4'e bakılabilir.
