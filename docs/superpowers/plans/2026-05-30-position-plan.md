# position/ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Açık pozisyonu ~14 dakika izleyen, 3 çıkış koşuluyla (zaman + thesis + kâr hedefi) kapatan `position/manager.py` modülünü TDD ile yaz.

**Architecture:** İki saf fonksiyon: `check_exit()` (karar, saf/pure — yan etki yok) ve `close_position()` (durum güncelleme + JSONL log). `_log()` yardımcısı execution/executor.py ile aynı pattern. `fair_yes()` import edilir (saf hesaplama, API yok).

**Tech Stack:** Python 3.12, pytest, stdlib: json, datetime, pathlib. `data.fair_value.fair_yes` (saf fonksiyon, API çağrısı yapmaz).

---

## Dosya Haritası

| Dosya | İşlem | Sorumluluk |
|-------|--------|------------|
| `position/manager.py` | Oluştur | `_log()` + `close_position()` + `check_exit()` |
| `tests/test_position.py` | Oluştur | 10 test |

---

## Referans: Test Sabitleri

Aşağıdaki `fair_yes()` değerleri önceden doğrulandı (`time_to_expiry_secs=900, asset="BTC"`):

| hl_price | ref_price | fair_yes | Kullanım |
|----------|-----------|----------|---------|
| 95000 | 95000 | 0.5000 | flat → tut |
| 94800 | 95000 | 0.3109 | YES thesis bozulur (< pm_yes=0.35) |
| 95200 | 95000 | 0.6887 | NO thesis bozulur (> pm_yes=0.30) |
| 95500 | 95000 | 0.8904 | YES kâr testi (thesis tutulur, pm_yes=0.53) |

---

## Task 1: `_log()` + `close_position()`

**Dosyalar:**
- Oluştur: `position/manager.py`
- Oluştur: `tests/test_position.py`

- [ ] **Step 1: `position/manager.py` iskeletini oluştur**

```python
"""position/manager.py — Açık pozisyon takibi ve çıkış kararı."""
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from data.fair_value import fair_yes

LOG_FILE = Path("logs/dry_run.jsonl")

PROFIT_TARGET_FRACTION = 0.85
NEAR_EXPIRY_SECS       = 90


def _log(event: str, data: dict, log_file: Path = LOG_FILE) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts":    datetime.now(timezone.utc).isoformat(),
        "layer": "position",
        "event": event,
        **data,
    }
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def close_position(
    position:      dict,
    exit_reason:   str,
    pm_exit_price: float | None = None,
    log_file:      Path = LOG_FILE,
) -> dict:
    """Pozisyonu kapatır, JSONL'a yazar, güncellenmiş kaydı döndürür."""
    closed = {
        **position,
        "status":        "closed",
        "exit_reason":   exit_reason,
        "closed_at":     datetime.now(timezone.utc).isoformat(),
        "pm_exit_price": pm_exit_price,
    }
    _log("position_closed", {
        "position_id":    closed["position_id"],
        "asset":          closed["asset"],
        "action":         closed["action"],
        "slug":           closed["slug"],
        "exit_reason":    exit_reason,
        "pm_entry_price": closed["pm_entry_price"],
        "pm_exit_price":  pm_exit_price,
        "fair_value":     closed["fair_value"],
        "closed_at":      closed["closed_at"],
        "dry_run":        closed["dry_run"],
    }, log_file)
    return closed


def check_exit(
    position:            dict,
    hl_price:            float,
    pm_yes_price:        float,
    time_to_expiry_secs: int,
) -> str | None:
    """Placeholder — Task 2'de implemente edilecek."""
    return None
```

- [ ] **Step 2: 3 testi yaz**

`tests/test_position.py` dosyasını oluştur:

```python
"""tests/test_position.py — position/manager birim testleri. API çağrısı yok."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from position.manager import check_exit, close_position, _log


# ── Fixture'lar ──────────────────────────────────────────────────────────────

def _position(action: str = "YES", held_minutes: int = 5) -> dict:
    """Geçerli bir açık pozisyon kaydı döndürür."""
    opened_at = (datetime.now(timezone.utc) - timedelta(minutes=held_minutes)).isoformat()
    # YES: entry=0.35, fair=0.55  |  NO: entry=0.33, fair_YES=0.35 (fair_NO=0.65)
    entry = 0.35 if action == "YES" else 0.33
    fair  = 0.55 if action == "YES" else 0.35
    return {
        "position_id":             "test-pos-1234",
        "asset":                   "BTC",
        "action":                  action,
        "slug":                    "btc-up-15min-test",
        "pm_entry_price":          entry,
        "fair_value":              fair,
        "ref_price":               95000.0,
        "position_usd":            25.0,
        "kelly_f":                 0.15,
        "confidence_score":        82.5,
        "seconds_remaining":       900,
        "opened_at":               opened_at,
        "status":                  "open",
        "requires_human_approval": False,
        "dry_run":                 True,
        "exit_reason":             None,
        "closed_at":               None,
    }


# ── Task 1: _log() + close_position() ────────────────────────────────────────

def test_position_log_writes_jsonl(tmp_path):
    """_log() layer='position' ile geçerli JSONL satırı yazar."""
    log_file = tmp_path / "test.jsonl"
    _log("test_event", {"key": "val"}, log_file=log_file)
    record = json.loads(log_file.read_text().strip())
    assert record["layer"] == "position"
    assert record["event"] == "test_event"
    assert record["key"] == "val"
    assert "ts" in record


def test_close_position_returns_updated_record(tmp_path):
    """close_position status='closed', exit_reason, pm_exit_price, closed_at set eder."""
    pos = _position()
    closed = close_position(pos, "max_hold_time", pm_exit_price=0.52,
                            log_file=tmp_path / "log.jsonl")
    assert closed["status"] == "closed"
    assert closed["exit_reason"] == "max_hold_time"
    assert closed["pm_exit_price"] == 0.52
    dt = datetime.fromisoformat(closed["closed_at"])
    assert dt.tzinfo is not None


def test_close_position_logs_jsonl(tmp_path):
    """close_position JSONL'a position_closed yazar, position_id içerir."""
    pos = _position()
    log_file = tmp_path / "log.jsonl"
    close_position(pos, "thesis_invalidated", log_file=log_file)
    record = json.loads(log_file.read_text().strip())
    assert record["event"] == "position_closed"
    assert record["exit_reason"] == "thesis_invalidated"
    assert record["position_id"] == pos["position_id"]
```

- [ ] **Step 3: Testleri çalıştır — geçmeli**

```bash
cd /root/mispricing_agent && source venv/bin/activate && pytest tests/test_position.py::test_position_log_writes_jsonl tests/test_position.py::test_close_position_returns_updated_record tests/test_position.py::test_close_position_logs_jsonl -v
```

Beklenti: **3 PASSED**

- [ ] **Step 4: Commit**

```bash
git add position/manager.py tests/test_position.py
git commit -m "feat(position): _log() + close_position() + 3 test"
```

---

## Task 2: `check_exit()` — zaman ve expiry kontrolleri

**Dosyalar:**
- Güncelle: `position/manager.py`
- Güncelle: `tests/test_position.py`

- [ ] **Step 1: 3 testi yaz (önce başarısız olacak)**

`tests/test_position.py` sonuna ekle:

```python
# ── Task 2: check_exit — zaman + expiry ──────────────────────────────────────

def test_check_exit_near_expiry_returns_none():
    """time_to_expiry_secs < 90 → None (market kapansın, dokunma)."""
    pos = _position(held_minutes=15)  # Zaman dolsa bile
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.40,
                        time_to_expiry_secs=80)
    assert result is None


def test_check_exit_max_hold_time():
    """14+ dakika geçmişse → 'max_hold_time'."""
    pos = _position(held_minutes=15)
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.40,
                        time_to_expiry_secs=900)
    assert result == "max_hold_time"


def test_check_exit_holds_when_no_condition_met():
    """Hiçbir koşul tetiklenmezse → None (tut)."""
    # flat market: fair_yes(95000,95000,900,'BTC')=0.50 > pm=0.38 → thesis holds
    # captured edge: (0.38-0.35)/0.20 = 0.15 < 0.85 → profit target yok
    pos = _position(action="YES", held_minutes=5)
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.38,
                        time_to_expiry_secs=900)
    assert result is None
```

- [ ] **Step 2: Testleri çalıştır — başarısız olmalı**

```bash
pytest tests/test_position.py::test_check_exit_near_expiry_returns_none tests/test_position.py::test_check_exit_max_hold_time tests/test_position.py::test_check_exit_holds_when_no_condition_met -v
```

Beklenti: **3 FAILED** (check_exit her zaman None döndürüyor)

- [ ] **Step 3: `check_exit()` zaman + expiry mantığını uygula**

`position/manager.py`'deki `check_exit()` placeholder'ını tamamen değiştir:

```python
def check_exit(
    position:            dict,
    hl_price:            float,
    pm_yes_price:        float,
    time_to_expiry_secs: int,
) -> str | None:
    """
    Pozisyon için çıkış kararı verir.

    Returns:
        "max_hold_time"      — MAX_HOLD_MINUTES doldu
        "thesis_invalidated" — HL tersine döndü
        "profit_target_hit"  — Edge'in %85'i yakalandı
        None                 — tut
    """
    # 1. Market kapanışa yakın → dokunma, bırak çözümlensin
    if time_to_expiry_secs < NEAR_EXPIRY_SECS:
        return None

    # 2. Zaman limiti
    opened_at = datetime.fromisoformat(position["opened_at"])
    held_minutes = (datetime.now(timezone.utc) - opened_at).total_seconds() / 60
    if held_minutes >= config.MAX_HOLD_MINUTES:
        return "max_hold_time"

    return None  # thesis + profit — Task 3'te eklenecek
```

- [ ] **Step 4: Testleri çalıştır — geçmeli**

```bash
pytest tests/test_position.py::test_check_exit_near_expiry_returns_none tests/test_position.py::test_check_exit_max_hold_time tests/test_position.py::test_check_exit_holds_when_no_condition_met -v
```

Beklenti: **3 PASSED**

- [ ] **Step 5: Commit**

```bash
git add position/manager.py tests/test_position.py
git commit -m "feat(position): check_exit() zaman + expiry guard — 3 test"
```

---

## Task 3: `check_exit()` — thesis ve kâr hedefi

**Dosyalar:**
- Güncelle: `position/manager.py`
- Güncelle: `tests/test_position.py`

- [ ] **Step 1: 4 testi yaz (önce başarısız olacak)**

`tests/test_position.py` sonuna ekle:

```python
# ── Task 3: check_exit — thesis + kâr hedefi ─────────────────────────────────

def test_check_exit_thesis_invalidated_yes():
    """YES: HL düşünce fair_yes < pm_price → 'thesis_invalidated'."""
    # fair_yes(94800, 95000, 900, 'BTC') = 0.3109 < pm_yes_price=0.35
    pos = _position(action="YES", held_minutes=5)
    result = check_exit(pos, hl_price=94800, pm_yes_price=0.35,
                        time_to_expiry_secs=900)
    assert result == "thesis_invalidated"


def test_check_exit_thesis_invalidated_no():
    """NO: HL yükselince fair_yes > pm_price → 'thesis_invalidated'."""
    # fair_yes(95200, 95000, 900, 'BTC') = 0.6887 > pm_yes_price=0.30
    pos = _position(action="NO", held_minutes=5)
    result = check_exit(pos, hl_price=95200, pm_yes_price=0.30,
                        time_to_expiry_secs=900)
    assert result == "thesis_invalidated"


def test_check_exit_profit_target_hit_yes():
    """YES: pm_yes_price >= entry + 0.85*edge → 'profit_target_hit'."""
    # entry=0.35, fair=0.55, edge=0.20, target=0.52 → pm_yes=0.53
    # fair_yes(95500, 95000, 900, 'BTC') = 0.8904 >= 0.53 → thesis tutulur
    # captured: (0.53-0.35)/0.20 = 0.90 >= 0.85 ✓
    pos = _position(action="YES", held_minutes=5)
    result = check_exit(pos, hl_price=95500, pm_yes_price=0.53,
                        time_to_expiry_secs=900)
    assert result == "profit_target_hit"


def test_check_exit_profit_target_hit_no():
    """NO: (1-pm_yes) >= entry + 0.85*(fair_NO-entry) → 'profit_target_hit'."""
    # entry=0.33, fair_NO=0.65, edge=0.32, target=0.602
    # pm_yes=0.38 → 1-pm=0.62 >= 0.602 ✓
    # fair_yes(94800, 95000, 900, 'BTC') = 0.3109 <= pm_yes=0.38 → thesis tutulur
    # captured: (0.62-0.33)/0.32 = 0.906 >= 0.85 ✓
    pos = _position(action="NO", held_minutes=5)
    result = check_exit(pos, hl_price=94800, pm_yes_price=0.38,
                        time_to_expiry_secs=900)
    assert result == "profit_target_hit"
```

- [ ] **Step 2: Testleri çalıştır — başarısız olmalı**

```bash
pytest tests/test_position.py::test_check_exit_thesis_invalidated_yes tests/test_position.py::test_check_exit_thesis_invalidated_no tests/test_position.py::test_check_exit_profit_target_hit_yes tests/test_position.py::test_check_exit_profit_target_hit_no -v
```

Beklenti: **4 FAILED**

- [ ] **Step 3: thesis + kâr hedefi mantığını uygula**

`position/manager.py`'deki `check_exit()` içindeki `return None  # thesis + profit — Task 3'te eklenecek` satırını sil ve yerine yaz:

```python
    # 3. Thesis kontrolü — HL tersine döndü mü?
    new_fair = fair_yes(hl_price, position["ref_price"],
                        time_to_expiry_secs, position["asset"])
    if position["action"] == "YES":
        thesis_broken = new_fair < pm_yes_price
    else:
        thesis_broken = new_fair > pm_yes_price

    if thesis_broken:
        return "thesis_invalidated"

    # 4. Kâr hedefi — edge'in PROFIT_TARGET_FRACTION kadarı yakalandı mı?
    if position["action"] == "YES":
        current_val = pm_yes_price
        target_val  = position["fair_value"]
    else:
        current_val = 1 - pm_yes_price
        target_val  = 1 - position["fair_value"]

    entry_price = position["pm_entry_price"]
    edge = target_val - entry_price
    if edge > 0 and (current_val - entry_price) / edge >= PROFIT_TARGET_FRACTION:
        return "profit_target_hit"

    return None
```

- [ ] **Step 4: Tüm 10 testi çalıştır — hepsi geçmeli**

```bash
pytest tests/test_position.py -v
```

Beklenti: **10 PASSED**

- [ ] **Step 5: Tüm test suite'ini çalıştır — regresyon yok**

```bash
pytest tests/ --asyncio-mode=auto
```

Beklenti: önceki sayıya ek **10 yeni test** — hiçbir FAILED

- [ ] **Step 6: Commit**

```bash
git add position/manager.py tests/test_position.py
git commit -m "feat(position): check_exit() thesis + kâr hedefi — Katman 7 tamamlandı"
```

---

## Self-Review

- 3 çıkış koşulu (zaman, thesis, kâr) → Task 2 + Task 3'te tam kaplı ✅
- near_expiry özel durumu (< 90s → None) → Task 2 test 1 ✅
- YES ve NO action her ikisi için thesis + profit → Task 3'te 4 test ✅
- `close_position` JSONL yan etkisi → Task 1 test 3 ✅
- `fair_yes` değerleri önceden doğrulandı (sabitlerin yorumları kodda) ✅
- `_log()` layer="position" → execution ile çakışmaz ✅
- Kapsam dışı: polling döngüsü (main_loop), PM fiyat çekme API'si ✅
- Placeholder yok ✅
- `check_exit` imzası Task 2 ve Task 3'te tutarlı ✅
