# Dynamic Bankroll Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bot, canlı modda gerçek Polymarket USDC bakiyesini okuyarak pozisyon boyutunu otomatik ölçeklendirir — bakiye düştükçe tradeler küçülür, DRY_RUN'da değişiklik yoktur.

**Architecture:**
- `execution/balance.py` — yeni modül: `get_effective_bankroll()` async fonksiyonu
- DRY_RUN=True → env'den `BANKROLL_USD` döner (değişiklik yok)
- DRY_RUN=False → Polymarket CLOB'dan gerçek bakiye çeker, `BANKROLL_CONFIG` (env) ile min alır
- `main_loop.py` → her scan döngüsünde `get_effective_bankroll()` çağırır, sonucu `_scan_and_execute`'a geçirir

**Tech Stack:** Python asyncio, py_clob_client_v2, aiosqlite, pytest-asyncio

---

## Dosya Haritası

| Dosya | İşlem | Neden |
|-------|-------|-------|
| `execution/balance.py` | CREATE | Bakiye okuma mantığını izole et |
| `main_loop.py` | MODIFY L26 + L279 | BANKROLL_CONFIG → dynamic per cycle |
| `tests/test_balance.py` | CREATE | DRY_RUN ve LIVE dallarını test et |

---

### Task 1: `execution/balance.py` — Failing Test Yaz

**Files:**
- Create: `tests/test_balance.py`

- [ ] **Step 1: Failing test yaz**

```python
# tests/test_balance.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_dry_run_returns_config():
    """DRY_RUN=True → config bankroll'u döner, API çağrısı yok."""
    with patch("config.DRY_RUN", True):
        from execution.balance import get_effective_bankroll
        result = await get_effective_bankroll(bankroll_config=500.0)
    assert result == 500.0


@pytest.mark.asyncio
async def test_live_uses_polymarket_balance():
    """DRY_RUN=False → gerçek bakiye (micro-USDC → USD)."""
    fake_client = MagicMock()
    fake_client.get_balance_allowance.return_value = {"balance": "250000000"}  # $250.00

    with patch("config.DRY_RUN", False), \
         patch("execution.balance.get_client", return_value=fake_client):
        from importlib import reload
        import execution.balance as bal_mod
        reload(bal_mod)
        result = await bal_mod.get_effective_bankroll(bankroll_config=1000.0)

    assert result == 250.0


@pytest.mark.asyncio
async def test_live_caps_at_config():
    """Bakiye > config → config döner (güvenlik üst sınırı)."""
    fake_client = MagicMock()
    fake_client.get_balance_allowance.return_value = {"balance": "2000000000"}  # $2000

    with patch("config.DRY_RUN", False), \
         patch("execution.balance.get_client", return_value=fake_client):
        from importlib import reload
        import execution.balance as bal_mod
        reload(bal_mod)
        result = await bal_mod.get_effective_bankroll(bankroll_config=500.0)

    assert result == 500.0


@pytest.mark.asyncio
async def test_live_api_error_falls_back_to_config():
    """API hatası → config bankroll fallback, sistem durmuyor."""
    fake_client = MagicMock()
    fake_client.get_balance_allowance.side_effect = Exception("timeout")

    with patch("config.DRY_RUN", False), \
         patch("execution.balance.get_client", return_value=fake_client):
        from importlib import reload
        import execution.balance as bal_mod
        reload(bal_mod)
        result = await bal_mod.get_effective_bankroll(bankroll_config=300.0)

    assert result == 300.0
```

- [ ] **Step 2: Test'in fail ettiğini doğrula**

```bash
source venv/bin/activate && python -m pytest tests/test_balance.py -v
```
Beklenen: `ModuleNotFoundError: No module named 'execution.balance'`

---

### Task 2: `execution/balance.py` — İmplementasyon Yaz

**Files:**
- Create: `execution/balance.py`

- [ ] **Step 3: Modülü yaz**

```python
"""execution/balance.py — Etkili bankroll: DRY_RUN→config, LIVE→gerçek bakiye."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from execution.clob_client import get_client
from py_clob_client_v2.clob_types import BalanceAllowanceParams, AssetType

_MICRO_USDC = 1_000_000  # 1 USDC = 1_000_000 mikro-USDC


async def get_effective_bankroll(bankroll_config: float) -> float:
    """
    DRY_RUN=True  → bankroll_config (env değeri), API çağrısı yok.
    DRY_RUN=False → Polymarket USDC bakiyesi, bankroll_config ile kısıtlanmış.
    Hata durumunda bankroll_config fallback.
    """
    if config.DRY_RUN:
        return bankroll_config

    try:
        client = get_client()
        bal = client.get_balance_allowance(
            params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        )
        micro = float(bal.get("balance", 0))
        usdc = micro / _MICRO_USDC
        effective = min(usdc, bankroll_config)
        if effective < bankroll_config * 0.5:
            print(f"[bankroll] Bakiye düştü: ${effective:.2f} (config=${bankroll_config:.2f})")
        return effective
    except Exception as e:
        print(f"[bankroll] Bakiye okunamadı ({e}), fallback=${bankroll_config:.2f}")
        return bankroll_config
```

- [ ] **Step 4: Testler geçiyor mu?**

```bash
source venv/bin/activate && python -m pytest tests/test_balance.py -v
```
Beklenen: 4 test PASS

- [ ] **Step 5: Commit**

```bash
git add execution/balance.py tests/test_balance.py
git commit -m "feat(balance): get_effective_bankroll — live modda gerçek USDC bakiyesi"
```

---

### Task 3: `main_loop.py` — Dinamik Bankroll Entegrasyonu

**Files:**
- Modify: `main_loop.py:26` (BANKROLL_USD → BANKROLL_CONFIG)
- Modify: `main_loop.py:279` (_scan_and_execute çağrısı)

**Mevcut kod (L26):**
```python
BANKROLL_USD = float(os.getenv("BANKROLL_USD", "1000.0"))
```

**Mevcut kod (scan döngüsü içi):**
```python
await _scan_and_execute(open_positions, closed_today, BANKROLL_USD, conn=conn)
```

- [ ] **Step 6: main_loop.py'yi güncelle**

L26 değişir:
```python
BANKROLL_CONFIG = float(os.getenv("BANKROLL_USD", "1000.0"))
```

Import ekle (dosyanın üstüne, diğer execution importlarına):
```python
from execution.balance import get_effective_bankroll
```

Scan döngüsü içindeki `_scan_and_execute` çağrısını güncelle:
```python
effective_bankroll = await get_effective_bankroll(BANKROLL_CONFIG)
await _scan_and_execute(open_positions, closed_today, effective_bankroll, conn=conn)
```

- [ ] **Step 7: Bot başlatılıyor mu kontrol et**

```bash
source venv/bin/activate && python -c "import main_loop; print('OK')"
```
Beklenen: `OK` (import hatası yok)

- [ ] **Step 8: Tam test suite**

```bash
source venv/bin/activate && python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```
Beklenen: `X passed, Y skipped, 0 failed`

- [ ] **Step 9: Bot restart + log doğrulama**

```bash
tmux kill-session -t mispricing 2>/dev/null
tmux new-session -d -s mispricing "source venv/bin/activate && PYTHONUNBUFFERED=1 python -u main_loop.py 2>&1 | tee -a logs/main_loop.log"
sleep 5 && tail -3 logs/main_loop.log
```
Beklenen: `[bot] Başladı — DRY_RUN=True` (bankroll satırı değişmez — DRY_RUN'da env değeri)

- [ ] **Step 10: Commit + push**

```bash
git add main_loop.py
git commit -m "feat(main_loop): dinamik bankroll — LIVE modda Polymarket bakiyesi kullanılır"
git push origin master
```

---

## Risk Notları

| Durum | Davranış |
|-------|----------|
| $50 bakiye, 10% limit | $5 kayıptan sonra bot durur (2 trade) — kullanıcı config.py'de DAILY_LOSS_LIMIT_PCT'yi artırmalı |
| Bakiye $0'a düşerse | get_effective_bankroll → $0, position_usd=$0 → position_too_small veto → trade yok |
| API timeout | Fallback bankroll_config, log atar, devam eder |
| DRY_RUN | Tamamen değişmez, env değeri kullanılır |
