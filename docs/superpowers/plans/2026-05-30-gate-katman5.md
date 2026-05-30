# Gate Katmanı (Katman 5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `council/gate.py` — 4 katman çıktısından güven skoru hesapla, eşik altını veto et, DRY_RUN'da JSONL logla.

**Architecture:** 2 katmanlı: `_confidence_score()` + `_gate_decide()` saf fonksiyonlar (sync, testable), `gate()` async wrapper (log + approval + aksiyon). `_log()` JSONL yazar, ileride DB'ye geçiş için tek yer.

**Tech Stack:** Python 3.12, pytest + pytest-asyncio, json, pathlib.

---

## Dosya Yapısı

| Dosya | İşlem | Sorumluluk |
|-------|--------|------------|
| `council/gate.py` | Oluştur | `_confidence_score`, `_gate_decide`, `_log`, `gate`, `main` |
| `tests/test_gate.py` | Oluştur | 10 test: 7 sync + 3 async |
| `logs/dry_run.jsonl` | Otomatik oluşur | DRY_RUN çıktısı (git'e eklenmez) |

---

## Sabit Referanslar (config.py'den, değiştirme)

```python
config.CONFIDENCE_THRESHOLD = 75
config.DRY_RUN              = True
config.HUMAN_APPROVAL_USD   = 50
```

---

## Task 1: Skeleton + `_confidence_score()` + 4 Test

**Files:**
- Create: `council/gate.py`
- Create: `tests/test_gate.py`

- [ ] **Step 1: `tests/test_gate.py` dosyasını oluştur**

```python
"""tests/test_gate.py — Katman 5 Gate birim testleri."""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import pytest
from council.gate import _confidence_score, _gate_decide, gate


# ── Fixture'lar ───────────────────────────────────────────────────────────────

def _finding(action="YES"):
    return {"question": "Will BTC go up?", "slug": "btc-up-1h",
            "asset": "BTC", "action": action, "edge": 0.12,
            "cur_price": 65000.0}


def _verification(fresh_seconds=400):
    return {"pass": True, "fresh_best_ask": 0.40, "fresh_best_bid": 0.38,
            "fresh_fair": 0.55, "fresh_edge": 0.15, "fresh_seconds": fresh_seconds,
            "fresh_cur_price": 65000.0, "hl_drift_pct": 0.01, "pm_drift": 0.005,
            "reason": "ok", "halt": False}


def _redteam(fee_adj_edge=0.12, liquidity_usd=3000.0, spread=0.02):
    return {"pass": True, "vetoes": [], "warnings": [],
            "fee_adj_edge": fee_adj_edge, "taker_fee": 0.02,
            "spread": spread, "liquidity_usd": liquidity_usd}


def _risk(position_usd=42.0, requires_human_approval=False):
    return {"pass": True, "position_usd": position_usd, "kelly_f": 0.2,
            "kelly_fraction_applied": 0.25,
            "requires_human_approval": requires_human_approval,
            "halt": False, "reason": ""}


# ── Task 1: _confidence_score ─────────────────────────────────────────────────

def test_confidence_score_typical_good():
    # edge=0.12, liq=$3000, secs=400, spread=0.02 → ≥ 75
    score = _confidence_score(_redteam(0.12, 3000.0, 0.02), _verification(400))
    assert score >= 75


def test_confidence_score_weak():
    # edge=0.09, liq=$800, secs=150, spread=0.035 → < 75
    score = _confidence_score(_redteam(0.09, 800.0, 0.035), _verification(150))
    assert score < 75


def test_confidence_score_perfect():
    # Tüm bileşenler max → ≥ 95
    score = _confidence_score(_redteam(0.20, 5000.0, 0.005), _verification(600))
    assert score >= 95


def test_confidence_score_clamped():
    # Aşırı değerler → 100'ü geçmez
    score = _confidence_score(_redteam(1.0, 999999.0, 0.0), _verification(9999))
    assert score <= 100.0
```

- [ ] **Step 2: Testi çalıştır — FAIL bekleniyor**

```bash
cd /root/mispricing_agent && source venv/bin/activate
pytest tests/test_gate.py::test_confidence_score_typical_good -v
```

Beklenen: `ERROR` — `ModuleNotFoundError: No module named 'council.gate'`

- [ ] **Step 3: `council/gate.py` skeleton + `_confidence_score()` yaz**

```python
"""
council/gate.py — KATMAN 5: Kapı.

Son karar ve uygulama katmanı. 4 katmandan geçen bulgu için güven
skoru hesaplar, insan onayı yönetir, DRY_RUN'da JSONL'a loglar.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

# ── Skor bileşeni sınırları ───────────────────────────────────────────────────
EDGE_ZERO   = 0.08   # config.MIN_EDGE_PCT eşiği
EDGE_MAX    = 0.15
LIQ_ZERO    = 500    # RedTeam LIQUIDITY_VETO_USD eşiği
LIQ_MAX     = 3000
TIME_ZERO   = 120    # RedTeam MIN_THESIS_SECS eşiği
TIME_MAX    = 300
SPREAD_ZERO = 0.04   # RedTeam SPREAD_VETO eşiği
SPREAD_MAX  = 0.01

APPROVAL_TIMEOUT_SECS = 300
LOG_FILE = Path("logs/dry_run.jsonl")


def _confidence_score(redteam: dict, verification: dict) -> float:
    """0-100 güven skoru. 4 bileşen ağırlıklı toplam."""
    edge   = redteam["fee_adj_edge"]
    liq    = redteam["liquidity_usd"]
    secs   = verification["fresh_seconds"]
    spread = redteam["spread"]

    edge_s   = min(max((edge   - EDGE_ZERO)   / (EDGE_MAX   - EDGE_ZERO),   0.0), 1.0)
    liq_s    = min(max((liq    - LIQ_ZERO)    / (LIQ_MAX    - LIQ_ZERO),    0.0), 1.0)
    time_s   = min(max((secs   - TIME_ZERO)   / (TIME_MAX   - TIME_ZERO),   0.0), 1.0)
    spread_s = min(max((SPREAD_ZERO - spread) / (SPREAD_ZERO - SPREAD_MAX), 0.0), 1.0)

    return round(edge_s * 40 + liq_s * 30 + time_s * 15 + spread_s * 15, 1)


def _gate_decide(finding: dict, verification: dict,
                 redteam: dict, risk_result: dict) -> dict:
    """Stub — Task 2'de implement edilecek."""
    return {"pass": False, "confidence_score": 0.0,
            "action_taken": "vetoed", "reason": "not_implemented"}


async def gate(finding: dict, verification: dict,
               redteam: dict, risk_result: dict) -> dict:
    """Stub — Task 3'te implement edilecek."""
    return {"pass": False, "confidence_score": 0.0,
            "action_taken": "vetoed", "reason": "not_implemented"}
```

- [ ] **Step 4: 4 testi çalıştır — PASS bekleniyor**

```bash
pytest tests/test_gate.py::test_confidence_score_typical_good \
       tests/test_gate.py::test_confidence_score_weak \
       tests/test_gate.py::test_confidence_score_perfect \
       tests/test_gate.py::test_confidence_score_clamped -v
```

Beklenen: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add council/gate.py tests/test_gate.py
git commit -m "test(gate): _confidence_score + 4 test — Katman 5 başlangıcı"
```

---

## Task 2: `_gate_decide()` + 3 Test

**Files:**
- Modify: `council/gate.py` — `_gate_decide()` implement et
- Modify: `tests/test_gate.py` — 3 test ekle

- [ ] **Step 1: `tests/test_gate.py`'ye testleri ekle**

`test_confidence_score_clamped` fonksiyonunun altına:

```python
# ── Task 2: _gate_decide ──────────────────────────────────────────────────────

def test_gate_decide_required_fields():
    r = _gate_decide(_finding(), _verification(), _redteam(), _risk())
    assert "pass" in r
    assert "confidence_score" in r
    assert "action_taken" in r
    assert "reason" in r


def test_gate_decide_vetoes_below_threshold():
    # Zayıf sinyal → skor < 75 → veto
    r = _gate_decide(
        _finding(), _verification(150),
        _redteam(0.09, 800.0, 0.035), _risk()
    )
    assert r["pass"] is False
    assert r["action_taken"] == "vetoed"
    assert r["reason"] == "confidence_below_threshold"


def test_gate_decide_passes_above_threshold():
    # İyi sinyal → skor ≥ 75 → pass
    r = _gate_decide(
        _finding(), _verification(400),
        _redteam(0.12, 3000.0, 0.02), _risk()
    )
    assert r["pass"] is True
    assert r["confidence_score"] >= 75
```

- [ ] **Step 2: Testleri çalıştır — FAIL bekleniyor**

```bash
pytest tests/test_gate.py::test_gate_decide_vetoes_below_threshold \
       tests/test_gate.py::test_gate_decide_passes_above_threshold -v
```

Beklenen: İkisi de `FAILED` (stub her zaman `not_implemented` döner)

- [ ] **Step 3: `council/gate.py`'de `_gate_decide()` implement et**

Mevcut stub'ı şununla değiştir:

```python
def _gate_decide(finding: dict, verification: dict,
                 redteam: dict, risk_result: dict) -> dict:
    """Güven skoru hesapla, CONFIDENCE_THRESHOLD kontrolü yap."""
    score = _confidence_score(redteam, verification)
    if score < config.CONFIDENCE_THRESHOLD:
        return {
            "pass":             False,
            "confidence_score": score,
            "action_taken":     "vetoed",
            "reason":           "confidence_below_threshold",
        }
    return {
        "pass":             True,
        "confidence_score": score,
        "action_taken":     "pending",
        "reason":           "",
    }
```

- [ ] **Step 4: Testleri çalıştır — PASS bekleniyor**

```bash
pytest tests/test_gate.py::test_gate_decide_required_fields \
       tests/test_gate.py::test_gate_decide_vetoes_below_threshold \
       tests/test_gate.py::test_gate_decide_passes_above_threshold -v
```

Beklenen: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add council/gate.py tests/test_gate.py
git commit -m "feat(gate): _gate_decide() güven skoru eşik kontrolü — Task 2"
```

---

## Task 3: `_log()` + `gate()` + 3 Async Test

**Files:**
- Modify: `council/gate.py` — `_log()` + `gate()` implement et
- Modify: `tests/test_gate.py` — 3 async test ekle

- [ ] **Step 1: `tests/test_gate.py`'ye async testleri ekle**

`test_gate_decide_passes_above_threshold` fonksiyonunun altına:

```python
# ── Task 3: gate() async ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gate_dry_run_logged(tmp_path, monkeypatch):
    # DRY_RUN=True, iyi sinyal → action_taken="dry_run_logged", log yazılır
    import council.gate as gm
    monkeypatch.setattr(gm, "LOG_FILE", tmp_path / "dry_run.jsonl")
    monkeypatch.setattr(config, "DRY_RUN", True)

    r = await gate(
        _finding(), _verification(400),
        _redteam(0.12, 3000.0, 0.02), _risk()
    )

    assert r["pass"] is True
    assert r["action_taken"] == "dry_run_logged"

    lines = (tmp_path / "dry_run.jsonl").read_text().strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["action_taken"] == "dry_run_logged"
    assert entry["dry_run"] is True
    assert entry["pass"] is True


@pytest.mark.asyncio
async def test_gate_vetoed_action_taken(tmp_path, monkeypatch):
    # Zayıf sinyal → veto, log yazılır
    import council.gate as gm
    monkeypatch.setattr(gm, "LOG_FILE", tmp_path / "dry_run.jsonl")
    monkeypatch.setattr(config, "DRY_RUN", True)

    r = await gate(
        _finding(), _verification(150),
        _redteam(0.09, 800.0, 0.035), _risk()
    )

    assert r["pass"] is False
    assert r["action_taken"] == "vetoed"
    entry = json.loads((tmp_path / "dry_run.jsonl").read_text().strip())
    assert entry["action_taken"] == "vetoed"
    assert entry["pass"] is False


@pytest.mark.asyncio
async def test_gate_approval_flag_dry_run_does_not_block(tmp_path, monkeypatch):
    # requires_human_approval=True + DRY_RUN=True → yine geçer (bloklamaz)
    import council.gate as gm
    monkeypatch.setattr(gm, "LOG_FILE", tmp_path / "dry_run.jsonl")
    monkeypatch.setattr(config, "DRY_RUN", True)

    r = await gate(
        _finding(), _verification(400),
        _redteam(0.12, 3000.0, 0.02),
        _risk(position_usd=200.0, requires_human_approval=True)
    )

    assert r["pass"] is True
    assert r["action_taken"] == "dry_run_logged"
    entry = json.loads((tmp_path / "dry_run.jsonl").read_text().strip())
    assert entry["requires_human_approval"] is True
    assert entry["action_taken"] == "dry_run_logged"
```

- [ ] **Step 2: Testleri çalıştır — FAIL bekleniyor**

```bash
pytest tests/test_gate.py::test_gate_dry_run_logged \
       tests/test_gate.py::test_gate_vetoed_action_taken \
       tests/test_gate.py::test_gate_approval_flag_dry_run_does_not_block \
       --asyncio-mode=auto -v
```

Beklenen: Üçü de `FAILED` (stub `not_implemented` döner)

- [ ] **Step 3: `council/gate.py`'de `_log()` + `gate()` implement et**

Mevcut `async def gate(...)` stub'ının hemen önüne `_log()` ekle, ardından `gate()` implement et:

```python
def _log(finding: dict, verification: dict, redteam: dict,
         decision: dict, risk_result: dict) -> None:
    """Kararı LOG_FILE'a yaz. Dizin yoksa oluşturur."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts":                      datetime.now(timezone.utc).isoformat(),
        "dry_run":                 config.DRY_RUN,
        "pass":                    decision["pass"],
        "action":                  finding.get("action", ""),
        "slug":                    finding.get("slug", ""),
        "asset":                   finding.get("asset", ""),
        "position_usd":            risk_result.get("position_usd", 0.0),
        "confidence_score":        decision["confidence_score"],
        "fee_adj_edge":            redteam.get("fee_adj_edge", 0.0),
        "liquidity_usd":           redteam.get("liquidity_usd", 0.0),
        "fresh_seconds":           verification.get("fresh_seconds", 0),
        "spread":                  redteam.get("spread", 0.0),
        "action_taken":            decision["action_taken"],
        "requires_human_approval": risk_result.get("requires_human_approval", False),
        "reason":                  decision["reason"],
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def gate(finding: dict, verification: dict,
               redteam: dict, risk_result: dict) -> dict:
    """
    Son karar: güven skoru → insan onayı → log → aksiyon.

    Returns:
        {pass, confidence_score, action_taken, reason}
    """
    decision = _gate_decide(finding, verification, redteam, risk_result)

    if not decision["pass"]:
        _log(finding, verification, redteam, decision, risk_result)
        return decision

    # İnsan onayı bayrağı
    if risk_result.get("requires_human_approval", False) and not config.DRY_RUN:
        # Canlı modda Telegram + timeout (şimdilik timeout döner)
        decision["action_taken"] = "approval_timeout"
        decision["pass"] = False
        decision["reason"] = "human_approval_timeout"
        _log(finding, verification, redteam, decision, risk_result)
        return decision

    # DRY_RUN: logla ve dön
    decision["action_taken"] = "dry_run_logged"
    _log(finding, verification, redteam, decision, risk_result)
    return decision
```

- [ ] **Step 4: Testleri çalıştır — PASS bekleniyor**

```bash
pytest tests/test_gate.py --asyncio-mode=auto -v
```

Beklenen: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add council/gate.py tests/test_gate.py
git commit -m "feat(gate): _log() + gate() async — JSONL log, DRY_RUN akışı — Task 3"
```

---

## Task 4: `main()` + Tam Test Koşusu

**Files:**
- Modify: `council/gate.py` — `main()` ekle

- [ ] **Step 1: `council/gate.py`'nin sonuna `main()` ekle**

Mevcut son fonksiyonun altına:

```python


async def main():
    """Manuel test: Scout→Verifier→RedTeam→Risk→Gate tam zinciri."""
    from council.scout import scan_edges
    from council.verifier import verify
    from council.redteam import redteam as rt
    from council.risk import risk

    print("=" * 70)
    print("GATE — son karar ve loglama")
    print("=" * 70)

    bankroll = getattr(config, "STARTING_CAPITAL_USD", 1000.0)

    findings = await scan_edges()
    if not findings:
        print("Scout'tan bulgu yok.")
        return

    for f in findings:
        v = await verify(f)
        if not v["pass"]:
            print(f"\n{f['question'][:50]} → Verifier: {v['reason']}")
            continue
        r = await rt(f, v)
        if not r["pass"]:
            print(f"\n{f['question'][:50]} → RedTeam veto: {r['vetoes']}")
            continue
        rk = risk(f, v, r, bankroll_usd=bankroll, open_positions=0, daily_loss_usd=0.0)
        if not rk["pass"]:
            print(f"\n{f['question'][:50]} → Risk veto: {rk['reason']}")
            continue
        g = await gate(f, v, r, rk)
        icon = "GEÇER" if g["pass"] else f"VETO [{g['action_taken']}]"
        print(f"\n{f['question'][:50]}")
        print(f"  Güven skoru   : {g['confidence_score']:.1f} / 100")
        print(f"  Pozisyon      : ${rk['position_usd']:.2f}")
        print(f"  Aksiyon       : {g['action_taken']}")
        print(f"  Karar         : {icon}")

    print(f"\nLog: {LOG_FILE}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

- [ ] **Step 2: Tam test suite'ini çalıştır**

```bash
pytest tests/ --asyncio-mode=auto -v 2>&1 | tail -20
```

Beklenen: En az `106 passed` (önceki 96 + yeni 10), `0 failed`

- [ ] **Step 3: Final commit**

```bash
git add council/gate.py
git commit -m "feat(council): Gate katmanı tamamlandı — güven skoru, JSONL log (Katman 5)"
```

---

## Doğrulama

```bash
pytest tests/test_gate.py --asyncio-mode=auto -v --tb=short
```

Beklenen çıktı:
```
tests/test_gate.py::test_confidence_score_typical_good PASSED
tests/test_gate.py::test_confidence_score_weak PASSED
tests/test_gate.py::test_confidence_score_perfect PASSED
tests/test_gate.py::test_confidence_score_clamped PASSED
tests/test_gate.py::test_gate_decide_required_fields PASSED
tests/test_gate.py::test_gate_decide_vetoes_below_threshold PASSED
tests/test_gate.py::test_gate_decide_passes_above_threshold PASSED
tests/test_gate.py::test_gate_dry_run_logged PASSED
tests/test_gate.py::test_gate_vetoed_action_taken PASSED
tests/test_gate.py::test_gate_approval_flag_dry_run_does_not_block PASSED

10 passed, 0 skipped, 0 failed
```
