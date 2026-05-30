# execution/ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate onaylı sinyali DRY_RUN modunda JSONL'a loglayan ve position/ için pozisyon kaydı döndüren `execute()` fonksiyonunu TDD ile yaz.

**Architecture:** Tek dosya `execution/executor.py`. İçinde `_log()` yardımcı fonksiyonu ve `async execute()` fonksiyonu. Dışa bağımlılık yok — sadece stdlib + config.

**Tech Stack:** Python 3.12, pytest-asyncio (asyncio-mode=auto), stdlib: uuid, json, datetime, pathlib

---

## Dosya Haritası

| Dosya | İşlem | Sorumluluk |
|-------|--------|------------|
| `execution/executor.py` | Oluştur | `_log()` + `execute()` |
| `tests/test_executor.py` | Oluştur | 8 test |

---

## Task 1: `_log()` yardımcı fonksiyon

**Dosyalar:**
- Oluştur: `execution/executor.py`
- Test: `tests/test_executor.py`

- [ ] **Step 1: Başlangıç modül iskeletini yaz**

`execution/executor.py` dosyasını oluştur:

```python
"""execution/executor.py — DRY_RUN order logger."""
import json
import sys
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

LOG_FILE = Path("logs/dry_run.jsonl")


def _log(event: str, data: dict, log_file: Path = LOG_FILE) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts":    datetime.now(timezone.utc).isoformat(),
        "layer": "execution",
        "event": event,
        **data,
    }
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

- [ ] **Step 2: _log testlerini yaz**

`tests/test_executor.py` dosyasını oluştur:

```python
"""tests/test_executor.py — execution/executor birim testleri."""
import json
import uuid
from datetime import datetime
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from execution.executor import _log, execute


# ── Fixture'lar ──────────────────────────────────────────────────────────────

def _finding():
    return {
        "question":          "Will BTC go up in 15min?",
        "asset":             "BTC",
        "action":            "YES",
        "fair_value":        0.55,
        "ref_price":         95000.0,
        "cur_price":         95500.0,
        "best_ask":          0.35,
        "best_bid":          0.33,
        "seconds_remaining": 600,
        "edge":              0.20,
        "slug":              "btc-up-15min-test",
        "neg_risk":          False,
    }


def _gate(pass_=True):
    return {
        "pass":             pass_,
        "confidence_score": 82.5,
        "action_taken":     "dry_run_logged",
        "reason":           "",
    }


def _risk():
    return {
        "pass":                    True,
        "position_usd":            25.0,
        "kelly_f":                 0.15,
        "kelly_fraction_applied":  0.25,
        "reason":                  "",
    }


# ── Task 1: _log() ───────────────────────────────────────────────────────────

def test_log_writes_jsonl(tmp_path):
    """_log() geçerli bir JSONL satırı yazar."""
    log_file = tmp_path / "test.jsonl"
    _log("test_event", {"key": "value"}, log_file=log_file)
    lines = log_file.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["layer"] == "execution"
    assert record["event"] == "test_event"
    assert record["key"] == "value"
    assert "ts" in record


def test_log_has_all_required_fields(tmp_path):
    """position_opened kaydı gerekli tüm alanları içerir."""
    log_file = tmp_path / "test.jsonl"
    _log("position_opened", {
        "position_id":    "abc",
        "asset":          "BTC",
        "action":         "YES",
        "slug":           "btc-up-test",
        "pm_entry_price": 0.35,
        "fair_value":     0.55,
        "position_usd":   25.0,
        "confidence_score": 82.5,
        "dry_run":        True,
    }, log_file=log_file)
    record = json.loads(log_file.read_text().strip())
    for field in ["position_id", "asset", "action", "slug",
                  "pm_entry_price", "fair_value", "position_usd",
                  "confidence_score", "dry_run", "ts", "layer", "event"]:
        assert field in record, f"Alan eksik: {field}"
```

- [ ] **Step 3: Testleri çalıştır — geçmeli**

```bash
cd /root/mispricing_agent && source venv/bin/activate && pytest tests/test_executor.py::test_log_writes_jsonl tests/test_executor.py::test_log_has_all_required_fields -v
```

Beklenti: **2 PASSED**

- [ ] **Step 4: Commit**

```bash
git add execution/executor.py tests/test_executor.py
git commit -m "feat(execution): _log() yardımcı fonksiyon + 2 test"
```

---

## Task 2: Guard — gate fail ve max pozisyon

**Dosyalar:**
- Güncelle: `execution/executor.py`
- Güncelle: `tests/test_executor.py`

- [ ] **Step 1: Testleri yaz (önce başarısız olacak)**

`tests/test_executor.py` sonuna ekle:

```python
# ── Task 2: Guard testleri ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gate_fail_returns_none(tmp_path):
    """gate_result pass=False → None döner."""
    result = await execute(
        _finding(), _gate(pass_=False), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    assert result is None


@pytest.mark.asyncio
async def test_max_open_positions_returns_none(tmp_path):
    """5 açık pozisyon varken → None döner."""
    fake_positions = [{"position_id": str(i)} for i in range(5)]
    result = await execute(
        _finding(), _gate(), _risk(),
        open_positions=fake_positions, log_file=tmp_path / "log.jsonl"
    )
    assert result is None
```

- [ ] **Step 2: Testleri çalıştır — başarısız olmalı**

```bash
pytest tests/test_executor.py::test_gate_fail_returns_none tests/test_executor.py::test_max_open_positions_returns_none -v
```

Beklenti: **2 FAILED** (execute fonksiyonu henüz yok)

- [ ] **Step 3: execute() guard'larını uygula**

`execution/executor.py`'ye ekle (dosyanın sonuna):

```python
async def execute(
    finding:        dict,
    gate_result:    dict,
    risk_result:    dict,
    open_positions: list,
    log_file:       Path = LOG_FILE,
) -> dict | None:
    """Gate onaylı bulguyu DRY_RUN'da loglar, pozisyon kaydı döndürür."""
    if not gate_result.get("pass"):
        _log("position_skipped", {"reason": "gate_vetoed", "dry_run": config.DRY_RUN}, log_file)
        return None

    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
        _log("position_skipped", {"reason": "max_open_positions", "dry_run": config.DRY_RUN}, log_file)
        return None

    return None  # happy path — Task 3'te tamamlanacak
```

- [ ] **Step 4: Testleri çalıştır — geçmeli**

```bash
pytest tests/test_executor.py::test_gate_fail_returns_none tests/test_executor.py::test_max_open_positions_returns_none -v
```

Beklenti: **2 PASSED**

- [ ] **Step 5: Commit**

```bash
git add execution/executor.py tests/test_executor.py
git commit -m "feat(execution): gate + max_open_positions guard — 2 test"
```

---

## Task 3: execute() happy path — pozisyon kaydı

**Dosyalar:**
- Güncelle: `execution/executor.py`
- Güncelle: `tests/test_executor.py`

- [ ] **Step 1: 4 testi yaz (önce başarısız olacak)**

`tests/test_executor.py` sonuna ekle:

```python
# ── Task 3: Happy path ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_returns_position_record(tmp_path):
    """Guard'lar geçince tam pozisyon kaydı döner."""
    result = await execute(
        _finding(), _gate(), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    assert result is not None
    assert result["status"] == "open"
    for field in ["position_id", "asset", "action", "slug",
                  "pm_entry_price", "fair_value", "ref_price",
                  "position_usd", "kelly_f", "confidence_score",
                  "seconds_remaining", "opened_at", "dry_run",
                  "exit_reason", "closed_at"]:
        assert field in result, f"Alan eksik: {field}"


@pytest.mark.asyncio
async def test_position_id_is_uuid4(tmp_path):
    """position_id geçerli bir UUID4 string'i."""
    result = await execute(
        _finding(), _gate(), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    parsed = uuid.UUID(result["position_id"])
    assert parsed.version == 4


@pytest.mark.asyncio
async def test_opened_at_is_valid_iso(tmp_path):
    """opened_at geçerli ISO 8601 UTC timestamp."""
    result = await execute(
        _finding(), _gate(), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    dt = datetime.fromisoformat(result["opened_at"])
    assert dt.tzinfo is not None


@pytest.mark.asyncio
async def test_two_calls_produce_different_position_ids(tmp_path):
    """İki ardışık çağrı farklı position_id üretir."""
    r1 = await execute(
        _finding(), _gate(), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    r2 = await execute(
        _finding(), _gate(), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    assert r1["position_id"] != r2["position_id"]
```

- [ ] **Step 2: Testleri çalıştır — başarısız olmalı**

```bash
pytest tests/test_executor.py::test_execute_returns_position_record tests/test_executor.py::test_position_id_is_uuid4 tests/test_executor.py::test_opened_at_is_valid_iso tests/test_executor.py::test_two_calls_produce_different_position_ids -v
```

Beklenti: **4 FAILED** (execute() hâlâ None döndürüyor)

- [ ] **Step 3: execute() happy path'i uygula**

`execution/executor.py`'deki `execute()` fonksiyonunda `return None  # happy path` satırını sil ve yerine yaz:

```python
    # Giriş fiyatı: YES için ask, NO için 1-bid
    if finding["action"] == "YES":
        pm_entry_price = finding["best_ask"]
    else:
        pm_entry_price = round(1 - finding["best_bid"], 4)

    position = {
        "position_id":       str(uuid.uuid4()),
        "asset":             finding["asset"],
        "action":            finding["action"],
        "slug":              finding["slug"],
        "pm_entry_price":    pm_entry_price,
        "fair_value":        finding["fair_value"],
        "ref_price":         finding["ref_price"],
        "position_usd":      risk_result["position_usd"],
        "kelly_f":           risk_result["kelly_f"],
        "confidence_score":  gate_result["confidence_score"],
        "seconds_remaining": finding["seconds_remaining"],
        "opened_at":         datetime.now(timezone.utc).isoformat(),
        "status":            "open",
        "dry_run":           config.DRY_RUN,
        "exit_reason":       None,
        "closed_at":         None,
    }

    _log("position_opened", {
        "position_id":      position["position_id"],
        "asset":            position["asset"],
        "action":           position["action"],
        "slug":             position["slug"],
        "pm_entry_price":   position["pm_entry_price"],
        "fair_value":       position["fair_value"],
        "position_usd":     position["position_usd"],
        "confidence_score": position["confidence_score"],
        "dry_run":          position["dry_run"],
    }, log_file)

    return position
```

- [ ] **Step 4: Tüm 8 testi çalıştır — hepsi geçmeli**

```bash
pytest tests/test_executor.py -v
```

Beklenti: **8 PASSED**

- [ ] **Step 5: Tüm test suite'ini çalıştır — regresyon yok**

```bash
pytest tests/ --asyncio-mode=auto -v
```

Beklenti: **114 passed, 6 skipped** (önceki 106 + yeni 8)

- [ ] **Step 6: Commit**

```bash
git add execution/executor.py tests/test_executor.py
git commit -m "feat(execution): execute() happy path + 6 test — Katman 6 tamamlandı"
```

---

## Self-Review Notları

- Spec'teki 8 test → plana 1:1 yansıdı ✅
- `_log()` her task'ta `log_file` parametresi alır → testler tmp_path kullanır, prod logu kirletmez ✅
- `execute()` imzası: `open_positions: list` (type annotation minimal, runtime'da list[dict] gelir) ✅
- `action == "NO"` giriş fiyatı `1 - best_bid` → spec ile tutarlı ✅
- `config.MAX_OPEN_POSITIONS = 5` → test fixture tam 5 eleman gönderir ✅
- Kapsam dışı: gerçek Polymarket CLOB, HUMAN_APPROVAL_USD, PostgreSQL — hiçbiri bu planda yok ✅
