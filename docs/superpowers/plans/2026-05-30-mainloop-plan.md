# main_loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scout → Konsey → Execution → Position takip döngüsünü 30 saniyede bir çalıştıran `main_loop.py`'yi TDD ile yaz.

**Architecture:** Tek dosya `main_loop.py`. Üç async fonksiyon (explicit state params → test edilebilir): `_run_council()`, `_scan_and_execute()`, `_monitor_positions()`. Durum (open_positions, closed_today) list olarak yaşar, `main()` yönetir. `BANKROLL_USD` main_loop.py'de sabit — kullanıcı canlıya geçmeden önce ayarlar.

**Tech Stack:** Python 3.12, asyncio, unittest.mock (AsyncMock), pytest-asyncio.

---

## Dosya Haritası

| Dosya | İşlem | Sorumluluk |
|-------|--------|------------|
| `main_loop.py` | Oluştur | `_run_council`, `_scan_and_execute`, `_monitor_positions`, `main` |
| `tests/test_main_loop.py` | Oluştur | 6 test (mock ile, sıfır API çağrısı) |

---

## Fonksiyon İmzaları (referans)

```python
# Mevcut council fonksiyonları:
await verify(finding: dict) -> dict
await redteam(finding: dict, verification: dict) -> dict
risk(finding, verification, redteam, bankroll_usd: float, open_positions: int, daily_loss_usd: float) -> dict
await gate(finding, verification, redteam, risk_result) -> dict
```

---

## Task 1: `main_loop.py` iskeleti + `_run_council()`

**Dosyalar:**
- Oluştur: `main_loop.py`
- Oluştur: `tests/test_main_loop.py`

- [ ] **Step 1: `main_loop.py` oluştur**

```python
"""main_loop.py — Scout→Konsey→Execute→Monitor ana döngüsü."""
import asyncio
import sys
import os
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from council.scout import scan_edges
from council.verifier import verify
from council.redteam import redteam as redteam_eval
from council.risk import risk as risk_eval
from council.gate import gate
from execution.executor import execute
from position.manager import check_exit, close_position
from data.hl_candles import current_price
from data.shortterm import fetch_by_slug, parse_market_window

SCAN_INTERVAL_SECS = 30
BANKROLL_USD = 1000.0  # Başlangıç sermayesi — canlıya geçmeden önce ayarla


def _daily_loss_usd(closed_today: list[dict]) -> float:
    """Bugün kapanan pozisyonlardan gerçekleşen kaybı toplar."""
    today = date.today()
    loss = 0.0
    for pos in closed_today:
        if pos.get("pm_exit_price") is None:
            continue
        closed_date = datetime.fromisoformat(pos["closed_at"]).date()
        if closed_date != today:
            continue
        # P&L: (exit - entry) / entry * position_usd
        pnl = (pos["pm_exit_price"] - pos["pm_entry_price"]) / pos["pm_entry_price"] * pos["position_usd"]
        if pnl < 0:
            loss += abs(pnl)
    return loss


async def _run_council(
    finding:       dict,
    bankroll_usd:  float,
    n_open:        int,
    daily_loss_usd: float,
) -> tuple | None:
    """Finding'i 5 katmandan geçirir. Herhangi biri düşerse None."""
    verification = await verify(finding)
    if not verification["pass"]:
        return None

    rt = await redteam_eval(finding, verification)
    if not rt["pass"]:
        return None

    rk = risk_eval(finding, verification, rt,
                   bankroll_usd=bankroll_usd,
                   open_positions=n_open,
                   daily_loss_usd=daily_loss_usd)
    if not rk["pass"]:
        return None

    gate_result = await gate(finding, verification, rt, rk)
    if not gate_result["pass"]:
        return None

    return gate_result, rk


async def _scan_and_execute(
    open_positions: list[dict],
    closed_today:   list[dict],
    bankroll_usd:   float,
) -> None:
    """Placeholder — Task 2'de implemente edilecek."""
    pass


async def _monitor_positions(
    open_positions: list[dict],
    closed_today:   list[dict],
) -> None:
    """Placeholder — Task 3'te implemente edilecek."""
    pass


async def main() -> None:
    open_positions: list[dict] = []
    closed_today:   list[dict] = []
    print(f"[bot] Başladı — DRY_RUN={config.DRY_RUN}, tarama={SCAN_INTERVAL_SECS}s")
    while True:
        try:
            await _monitor_positions(open_positions, closed_today)
            await _scan_and_execute(open_positions, closed_today, BANKROLL_USD)
        except Exception as e:
            print(f"[bot] Döngü hatası: {e}")
        await asyncio.sleep(SCAN_INTERVAL_SECS)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 2 testi yaz**

`tests/test_main_loop.py` dosyasını oluştur:

```python
"""tests/test_main_loop.py — main_loop birim testleri. Sıfır API çağrısı."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from main_loop import _run_council, _scan_and_execute, _monitor_positions


# ── Fixture'lar ──────────────────────────────────────────────────────────────

def _finding():
    return {
        "question": "Will BTC go up?", "asset": "BTC", "action": "YES",
        "fair_value": 0.55, "ref_price": 95000.0, "cur_price": 95500.0,
        "best_ask": 0.35, "best_bid": 0.33, "seconds_remaining": 900,
        "edge": 0.20, "slug": "btc-up-15min-test", "neg_risk": False,
    }

def _pass_verify():
    return {"pass": True, "fresh_best_ask": 0.35, "fresh_best_bid": 0.33,
            "fresh_seconds": 900, "halt": False, "reason": ""}

def _pass_redteam():
    return {"pass": True, "vetoes": [], "warnings": [], "fee_adj_edge": 0.18,
            "liquidity_usd": 2000.0, "spread": 0.02}

def _pass_risk():
    return {"pass": True, "position_usd": 25.0, "kelly_f": 0.15,
            "kelly_fraction_applied": 0.25, "reason": ""}

def _pass_gate():
    return {"pass": True, "confidence_score": 82.5,
            "action_taken": "dry_run_logged", "reason": ""}


# ── Task 1: _run_council() ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_council_returns_none_when_verify_fails():
    """verify() fail → _run_council None döner."""
    with patch("main_loop.verify", new_callable=AsyncMock) as mock_v:
        mock_v.return_value = {"pass": False, "reason": "timeout"}
        result = await _run_council(_finding(), bankroll_usd=1000.0,
                                    n_open=0, daily_loss_usd=0.0)
    assert result is None


@pytest.mark.asyncio
async def test_run_council_returns_gate_and_risk_on_success():
    """Tüm katmanlar geçince (gate_result, risk_result) tuple döner."""
    with patch("main_loop.verify",      new_callable=AsyncMock) as mv, \
         patch("main_loop.redteam_eval",new_callable=AsyncMock) as mr, \
         patch("main_loop.risk_eval",   new=MagicMock()) as mk, \
         patch("main_loop.gate",        new_callable=AsyncMock) as mg:
        mv.return_value = _pass_verify()
        mr.return_value = _pass_redteam()
        mk.return_value = _pass_risk()
        mg.return_value = _pass_gate()
        result = await _run_council(_finding(), bankroll_usd=1000.0,
                                    n_open=0, daily_loss_usd=0.0)
    assert result is not None
    gate_result, risk_result = result
    assert gate_result["pass"] is True
    assert risk_result["position_usd"] == 25.0
```

- [ ] **Step 3: Testleri çalıştır — geçmeli**

```bash
cd /root/mispricing_agent && source venv/bin/activate && pytest tests/test_main_loop.py::test_run_council_returns_none_when_verify_fails tests/test_main_loop.py::test_run_council_returns_gate_and_risk_on_success -v
```

Beklenti: **2 PASSED**

- [ ] **Step 4: Commit**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(main_loop): iskelet + _run_council() + 2 test"
```

---

## Task 2: `_scan_and_execute()`

**Dosyalar:**
- Güncelle: `main_loop.py`
- Güncelle: `tests/test_main_loop.py`

- [ ] **Step 1: 2 testi yaz (önce başarısız olacak)**

`tests/test_main_loop.py` sonuna ekle:

```python
# ── Task 2: _scan_and_execute() ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_skips_when_max_positions_reached():
    """MAX_OPEN_POSITIONS doluysa scan_edges hiç çağrılmaz."""
    import config
    open_pos = [{"position_id": str(i)} for i in range(config.MAX_OPEN_POSITIONS)]
    with patch("main_loop.scan_edges", new_callable=AsyncMock) as mock_scan:
        await _scan_and_execute(open_pos, [], bankroll_usd=1000.0)
    mock_scan.assert_not_called()


@pytest.mark.asyncio
async def test_scan_opens_position_on_full_council_pass():
    """Konsey geçince execute() çağrılır, pozisyon open_positions'a eklenir."""
    open_pos = []
    fake_pos = {"position_id": "abc-123", "status": "open", "asset": "BTC",
                "action": "YES", "slug": "btc-up-test"}
    with patch("main_loop.scan_edges",   new_callable=AsyncMock) as mock_scan, \
         patch("main_loop._run_council", new_callable=AsyncMock) as mock_council, \
         patch("main_loop.execute",      new_callable=AsyncMock) as mock_exec:
        mock_scan.return_value    = [_finding()]
        mock_council.return_value = (_pass_gate(), _pass_risk())
        mock_exec.return_value    = fake_pos
        await _scan_and_execute(open_pos, [], bankroll_usd=1000.0)
    assert len(open_pos) == 1
    assert open_pos[0]["position_id"] == "abc-123"
```

- [ ] **Step 2: Testleri çalıştır — başarısız olmalı**

```bash
pytest tests/test_main_loop.py::test_scan_skips_when_max_positions_reached tests/test_main_loop.py::test_scan_opens_position_on_full_council_pass -v
```

Beklenti: **2 FAILED**

- [ ] **Step 3: `_scan_and_execute()` placeholder'ını değiştir**

`main_loop.py`'deki `_scan_and_execute` fonksiyonunu güncelle:

```python
async def _scan_and_execute(
    open_positions: list[dict],
    closed_today:   list[dict],
    bankroll_usd:   float,
) -> None:
    """Yeni fırsatları tarar, konsey geçenleri açar."""
    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
        return

    findings = await scan_edges()
    daily_loss = _daily_loss_usd(closed_today)

    for finding in findings:
        if len(open_positions) >= config.MAX_OPEN_POSITIONS:
            break

        result = await _run_council(finding,
                                    bankroll_usd=bankroll_usd,
                                    n_open=len(open_positions),
                                    daily_loss_usd=daily_loss)
        if result is None:
            continue

        gate_result, risk_result = result
        position = await execute(finding, gate_result, risk_result, open_positions)
        if position:
            open_positions.append(position)
```

- [ ] **Step 4: Testleri çalıştır — geçmeli**

```bash
pytest tests/test_main_loop.py::test_scan_skips_when_max_positions_reached tests/test_main_loop.py::test_scan_opens_position_on_full_council_pass -v
```

Beklenti: **2 PASSED**

- [ ] **Step 5: Commit**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(main_loop): _scan_and_execute() + 2 test"
```

---

## Task 3: `_monitor_positions()`

**Dosyalar:**
- Güncelle: `main_loop.py`
- Güncelle: `tests/test_main_loop.py`

- [ ] **Step 1: 2 testi yaz (önce başarısız olacak)**

`tests/test_main_loop.py` sonuna ekle:

```python
# ── Task 3: _monitor_positions() ─────────────────────────────────────────────

def _open_position():
    """Açık pozisyon fixture'ı."""
    from datetime import timedelta
    opened_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    return {
        "position_id": "pos-xyz", "asset": "BTC", "action": "YES",
        "slug": "btc-up-test", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "position_usd": 25.0, "kelly_f": 0.15,
        "confidence_score": 82.5, "seconds_remaining": 900,
        "opened_at": opened_at, "status": "open",
        "requires_human_approval": False, "dry_run": True,
        "exit_reason": None, "closed_at": None,
    }


@pytest.mark.asyncio
async def test_monitor_closes_position_on_exit_signal():
    """check_exit sinyal verince pozisyon open'dan closed'a geçer."""
    from datetime import timedelta
    pos = _open_position()
    open_pos = [pos]
    closed = []
    fake_window = {"best_ask": 0.52, "best_bid": 0.50,
                   "seconds_remaining": 900, "neg_risk": False}
    with patch("main_loop.current_price", new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug", new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=fake_window), \
         patch("main_loop.check_exit", return_value="max_hold_time") as mock_exit:
        mock_hl.return_value = 95000.0
        mock_pm.return_value = {}
        await _monitor_positions(open_pos, closed)
    assert len(open_pos) == 0
    assert len(closed) == 1
    assert closed[0]["exit_reason"] == "max_hold_time"
    assert closed[0]["status"] == "closed"


@pytest.mark.asyncio
async def test_monitor_closes_on_missing_market():
    """parse_market_window None dönerse market_expired ile kapatılır."""
    open_pos = [_open_position()]
    closed = []
    with patch("main_loop.current_price", new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug", new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=None):
        mock_hl.return_value = 95000.0
        mock_pm.return_value = {}
        await _monitor_positions(open_pos, closed)
    assert len(open_pos) == 0
    assert len(closed) == 1
    assert closed[0]["exit_reason"] == "market_expired"
```

- [ ] **Step 2: Testleri çalıştır — başarısız olmalı**

```bash
pytest tests/test_main_loop.py::test_monitor_closes_position_on_exit_signal tests/test_main_loop.py::test_monitor_closes_on_missing_market -v
```

Beklenti: **2 FAILED**

- [ ] **Step 3: `_monitor_positions()` placeholder'ını değiştir**

`main_loop.py`'deki `_monitor_positions` fonksiyonunu güncelle:

```python
async def _monitor_positions(
    open_positions: list[dict],
    closed_today:   list[dict],
) -> None:
    """Açık pozisyonları izler, çıkış koşulu varsa kapatır."""
    for pos in list(open_positions):
        try:
            hl_price   = await current_price(pos["asset"])
            market_raw = await fetch_by_slug(pos["slug"])
            window     = parse_market_window(market_raw)

            if window is None:
                closed = close_position(pos, "market_expired")
                open_positions.remove(pos)
                closed_today.append(closed)
                continue

            exit_reason = check_exit(pos, hl_price,
                                     window["best_ask"],
                                     window["seconds_remaining"])
            if exit_reason:
                closed = close_position(pos, exit_reason,
                                        pm_exit_price=window["best_ask"])
                open_positions.remove(pos)
                closed_today.append(closed)

        except Exception as e:
            print(f"[monitor] {pos['slug']} hata: {e}")
```

- [ ] **Step 4: Tüm 6 testi çalıştır — hepsi geçmeli**

```bash
pytest tests/test_main_loop.py -v
```

Beklenti: **6 PASSED**

- [ ] **Step 5: Tüm suite — regresyon yok**

```bash
pytest tests/ --asyncio-mode=auto
```

Beklenti: önceki sayı + 6 yeni, sıfır FAILED.

- [ ] **Step 6: Commit**

```bash
git add main_loop.py tests/test_main_loop.py
git commit -m "feat(main_loop): _monitor_positions() + 6 test — döngü tamamlandı"
```

---

## Self-Review

- `_run_council` tüm 5 katmanı doğru sırayla çağırıyor ✅
- `risk()` imzası: `bankroll_usd`, `open_positions: int`, `daily_loss_usd` — tüm parametreler verildi ✅
- Explicit state params → sıfır global durum → test izolasyonu ✅
- `_monitor_positions` önce, `_scan_and_execute` sonra (kapanan slot önce boşalır) ✅
- `SCAN_INTERVAL_SECS = 30` ✅
- `BANKROLL_USD = 1000.0` — kullanıcı canlıya geçmeden ayarlar ✅
- Tüm testlerde sıfır gerçek API çağrısı (AsyncMock ile) ✅
- Kapsam dışı: Telegram, PostgreSQL, kill switch ✅
- Placeholder yok ✅
- `_open_position` fixture `datetime` import'u test dosyasında mevcut ✅
