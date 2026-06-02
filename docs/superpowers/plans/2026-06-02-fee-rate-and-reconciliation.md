# Fee Rate + Pozisyon Mutabakatı İmplementasyon Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) Fee rate'i Scout seviyesine taşı — RedTeam her zaman finding dict'ten okur, Gamma API'ye bağımlılık kalmaz. (2) LIVE bot başlarken DB pozisyonlarını Polymarket ile karşılaştır — kaybolmuş ya da kapanmış pozisyonları tespit et.

**Architecture:**
- Task 1: `data/fee_rate.py` yeni modül → Scout `_process_market` içinde CLOB `/fee-rate/{token_id}` çekip finding'e ekler. RedTeam `finding["taker_fee"]` okur, Gamma `takerBaseFee` parsing kaldırılır. 5 dk TTL cache ile API yükü minimize edilir.
- Task 2: `execution/reconcile.py` yeni modül → `startup_reconcile(open_positions, conn)`. LIVE modda Polymarket data API'den kullanıcı pozisyonlarını çeker, DB ile karşılaştırır. Market kapandıysa otomatik kapatır, Polymarket'te olmayan DB pozisyonlarını flagler.

**Tech Stack:** Python asyncio, aiohttp, py_clob_client_v2, aiosqlite, pytest-asyncio

---

## Dosya Haritası

| Dosya | İşlem | Sorumluluk |
|-------|-------|------------|
| `data/fee_rate.py` | CREATE | CLOB fee-rate fetch + 5dk TTL cache |
| `council/scout.py` | MODIFY L80-109 | `_process_market` → fee_rate çek → finding'e ekle |
| `council/redteam.py` | MODIFY L105-111 | `finding["taker_fee"]` kullan, Gamma parse kaldır |
| `execution/reconcile.py` | CREATE | Startup pozisyon mutabakatı |
| `main_loop.py` | MODIFY L258-264 | LIVE startup'ta `startup_reconcile` çağır |
| `tests/test_fee_rate.py` | CREATE | fee_rate modül testleri |
| `tests/test_reconcile.py` | CREATE | reconcile modül testleri |

---

## Task 1: `data/fee_rate.py` — Failing Test

**Files:**
- Create: `tests/test_fee_rate.py`

- [ ] **Step 1: Failing test yaz**

```python
# tests/test_fee_rate.py
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, AsyncMock
import data.fee_rate as fee_mod


@pytest.mark.asyncio
async def test_fetch_returns_parsed_fee():
    """CLOB API base_fee:1000 → 0.02 döner."""
    with patch("data.fee_rate.aiohttp") as mock_http:
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=ctx)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session = AsyncMock()
        mock_session.get.return_value = ctx
        ctx.json = AsyncMock(return_value={"base_fee": 1000})
        mock_http.ClientSession.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_http.ClientSession.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fee_mod.fetch_fee_rate("some-token-id-123")

    assert result == pytest.approx(0.02)


@pytest.mark.asyncio
async def test_cache_avoids_second_api_call():
    """Aynı token ikinci çağrıda cache'den gelir, API çağrısı yapılmaz."""
    fee_mod._cache.clear()
    fee_mod._cache["tok-abc"] = (0.02, time.monotonic() + 300)
    call_count = 0

    async def fake_fetch(token_id):
        nonlocal call_count
        call_count += 1
        return 0.02

    with patch.object(fee_mod, "_fetch_from_api", side_effect=fake_fetch):
        result = await fee_mod.fetch_fee_rate("tok-abc")

    assert result == 0.02
    assert call_count == 0  # cache hit, API çağrılmadı


@pytest.mark.asyncio
async def test_expired_cache_refetches():
    """Süresi geçmiş cache → API tekrar çağrılır."""
    fee_mod._cache.clear()
    fee_mod._cache["tok-xyz"] = (0.02, time.monotonic() - 1)  # süresi geçmiş

    with patch.object(fee_mod, "_fetch_from_api", return_value=0.02) as mock_fetch:
        result = await fee_mod.fetch_fee_rate("tok-xyz")

    mock_fetch.assert_called_once_with("tok-xyz")
    assert result == 0.02


@pytest.mark.asyncio
async def test_api_error_returns_default():
    """API hatası → 0.02 fallback, sistem durmuyor."""
    fee_mod._cache.clear()
    with patch.object(fee_mod, "_fetch_from_api", side_effect=Exception("timeout")):
        result = await fee_mod.fetch_fee_rate("tok-err")
    assert result == 0.02
```

- [ ] **Step 2: Fail doğrula**

```bash
source venv/bin/activate && python -m pytest tests/test_fee_rate.py -v 2>&1 | tail -8
```
Beklenen: `ModuleNotFoundError: No module named 'data.fee_rate'`

---

## Task 2: `data/fee_rate.py` — İmplementasyon

**Files:**
- Create: `data/fee_rate.py`

- [ ] **Step 3: Modülü yaz**

```python
"""data/fee_rate.py — Polymarket CLOB fee rate, 5dk TTL cache ile."""
import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import aiohttp
except ImportError:
    aiohttp = None

CLOB_HOST = "https://clob.polymarket.com"
CACHE_TTL  = 300  # 5 dakika
DEFAULT    = 0.02  # %2 fallback

_cache: dict[str, tuple[float, float]] = {}  # token_id → (fee, expires_at)


def _parse(raw) -> float:
    """base_fee (bps) → ondalık. 1000 → 0.02."""
    try:
        fee = float(raw) / 50_000
        return fee if 0 < fee <= 0.20 else DEFAULT
    except (TypeError, ValueError):
        return DEFAULT


async def _fetch_from_api(token_id: str) -> float:
    if aiohttp is None:
        return DEFAULT
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{CLOB_HOST}/fee-rate/{token_id}", timeout=aiohttp.ClientTimeout(total=5)
        ) as resp:
            data = await resp.json()
            return _parse(data.get("base_fee"))


async def fetch_fee_rate(token_id: str) -> float:
    """
    token_id için taker fee'yi döner. 5dk cache kullanır.
    Hata durumunda DEFAULT=%2 fallback.
    """
    now = time.monotonic()
    if token_id in _cache:
        fee, expires = _cache[token_id]
        if now < expires:
            return fee

    try:
        fee = await _fetch_from_api(token_id)
    except Exception:
        return DEFAULT

    _cache[token_id] = (fee, now + CACHE_TTL)
    return fee
```

- [ ] **Step 4: Testler geçiyor mu?**

```bash
source venv/bin/activate && python -m pytest tests/test_fee_rate.py -v 2>&1 | tail -8
```
Beklenen: 4 test PASS

- [ ] **Step 5: Commit**

```bash
git add data/fee_rate.py tests/test_fee_rate.py
git commit -m "feat(fee_rate): CLOB fee-rate fetch — 5dk TTL cache, %2 fallback"
```

---

## Task 3: Scout → Fee'yi Finding'e Ekle

**Files:**
- Modify: `council/scout.py` — `_process_market` son blok

Mevcut `_process_market` sonu (L91-109):
```python
_tids = _parse_token_ids(m.get("clobTokenIds"))
return {
    ...
    "yes_token_id": _tids[0] if _tids else None,
    "no_token_id":  _tids[1] if len(_tids) > 1 else None,
}
```

- [ ] **Step 6: Scout'u güncelle**

`council/scout.py` başına import ekle (diğer data importlarının yanına):
```python
from data.fee_rate import fetch_fee_rate
```

`_process_market` içinde `_tids` satırından önce fee çek:
```python
    _tids = _parse_token_ids(m.get("clobTokenIds"))
    yes_token = _tids[0] if _tids else None
    # Fee rate — cache'li, hata durumunda 0.02 fallback
    taker_fee = await fetch_fee_rate(yes_token) if yes_token else 0.02

    return {
        "question":          (m.get("question") or "?")[:60],
        "asset":             asset,
        "fair_value":        round(fair, 4),
        "ref_price":         ref_price,
        "cur_price":         cur,
        "best_ask":          window["best_ask"],
        "best_bid":          window["best_bid"],
        "seconds_remaining": window["seconds_remaining"],
        "edge":              round(signal["edge"], 4),
        "action":            signal["action"],
        "neg_risk":          window["neg_risk"],
        "slug":              m.get("slug", ""),
        "_window":           window,
        "_raw_market":       m,
        "yes_token_id":      yes_token,
        "no_token_id":       _tids[1] if len(_tids) > 1 else None,
        "taker_fee":         taker_fee,
    }
```

- [ ] **Step 7: RedTeam → `finding["taker_fee"]` kullan**

`council/redteam.py` L105-111 değişir. Mevcut kod:
```python
    try:
        spread      = float(market.get("spread") or 999)
        liquidity   = float(market.get("liquidityClob") or 0)
        volume_24hr = float(market.get("volume24hr") or 0)
        taker_fee   = _parse_taker_fee(market.get("takerBaseFee"))
    except (TypeError, ValueError):
        return _result(False, vetoes + ["parse_error"], warnings, 0.0, 0.02, 0.0, 0.0)
```

Değiştirilecek:
```python
    try:
        spread      = float(market.get("spread") or 999)
        liquidity   = float(market.get("liquidityClob") or 0)
        volume_24hr = float(market.get("volume24hr") or 0)
        # Scout seviyesinde çekilmiş fee — Gamma bağımlılığı yok
        taker_fee   = finding.get("taker_fee") or _parse_taker_fee(market.get("takerBaseFee"))
    except (TypeError, ValueError):
        return _result(False, vetoes + ["parse_error"], warnings, 0.0, 0.02, 0.0, 0.0)
```

- [ ] **Step 8: Tam test suite çalıştır**

```bash
source venv/bin/activate && python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```
Beklenen: `X passed, Y skipped, 0 failed`

- [ ] **Step 9: Commit**

```bash
git add council/scout.py council/redteam.py
git commit -m "feat(scout): taker_fee finding dict'e eklendi — Gamma takerBaseFee bağımlılığı azaldı"
```

---

## Task 4: `execution/reconcile.py` — Failing Test

**Files:**
- Create: `tests/test_reconcile.py`

- [ ] **Step 10: Failing test yaz**

```python
# tests/test_reconcile.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def _make_pos(slug="btc-up-5m-test", position_id="pos-1"):
    return {
        "position_id": position_id, "slug": slug, "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.51, "position_usd": 25.0,
        "yes_token_id": "yes-tok", "no_token_id": "no-tok",
        "shares": 49.0, "status": "open", "dry_run": False,
    }


@pytest.mark.asyncio
async def test_reconcile_skips_in_dry_run():
    """DRY_RUN=True → hiçbir şey yapmaz."""
    with patch("config.DRY_RUN", True):
        from execution.reconcile import startup_reconcile
        result = await startup_reconcile([_make_pos()], conn=None)
    assert result == {"checked": 0, "closed": 0, "warnings": []}


@pytest.mark.asyncio
async def test_reconcile_closes_resolved_market():
    """Market kapanmış → pozisyon DB'de kapatılır."""
    pos = _make_pos()
    fake_conn = AsyncMock()

    with patch("config.DRY_RUN", False), \
         patch("execution.reconcile.fetch_by_slug", return_value=None), \
         patch("execution.reconcile.fetch_resolved",
               return_value={"yes_exit": 1.0, "no_exit": 0.0}), \
         patch("execution.reconcile.log_position_close", new_callable=AsyncMock) as mock_close:
        from importlib import reload
        import execution.reconcile as rec_mod
        reload(rec_mod)
        result = await rec_mod.startup_reconcile([pos], conn=fake_conn)

    assert result["closed"] == 1
    mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_reconcile_warns_on_active_market_missing_polymarket_data():
    """Market hâlâ açık → uyarı logla, pozisyona dokunma."""
    pos = _make_pos()
    fake_window = {"seconds_remaining": 300, "best_ask": 0.51,
                   "best_bid": 0.50, "neg_risk": False}
    fake_market = MagicMock()

    with patch("config.DRY_RUN", False), \
         patch("execution.reconcile.fetch_by_slug", return_value=fake_market), \
         patch("execution.reconcile.parse_market_window", return_value=fake_window):
        from importlib import reload
        import execution.reconcile as rec_mod
        reload(rec_mod)
        result = await rec_mod.startup_reconcile([pos], conn=None)

    assert result["closed"] == 0
    assert result["checked"] == 1
```

- [ ] **Step 11: Fail doğrula**

```bash
source venv/bin/activate && python -m pytest tests/test_reconcile.py -v 2>&1 | tail -8
```
Beklenen: `ModuleNotFoundError: No module named 'execution.reconcile'`

---

## Task 5: `execution/reconcile.py` — İmplementasyon

**Files:**
- Create: `execution/reconcile.py`

- [ ] **Step 12: Modülü yaz**

```python
"""execution/reconcile.py — LIVE startup pozisyon mutabakatı."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from data.shortterm import fetch_by_slug, fetch_resolved, parse_market_window
from position.manager import close_position
from db.logger import log_position_close


async def startup_reconcile(open_positions: list[dict], conn) -> dict:
    """
    LIVE startup: DB'deki açık pozisyonları Polymarket ile karşılaştırır.
    DRY_RUN=True → hiçbir şey yapmaz.

    Döner: {"checked": N, "closed": N, "warnings": [...]}
    """
    if config.DRY_RUN:
        return {"checked": 0, "closed": 0, "warnings": []}

    checked = 0
    closed  = 0
    warnings = []

    for pos in list(open_positions):
        slug = pos["slug"]
        checked += 1
        try:
            market = await fetch_by_slug(slug)
            window = parse_market_window(market) if market else None

            if window is None:
                # Market kapandı — resolution fiyatını bul
                resolution = await fetch_resolved(slug)
                if resolution:
                    pm_exit = resolution["yes_exit"] if pos["action"] == "YES" else resolution["no_exit"]
                    reason  = "startup_reconcile_resolved"
                else:
                    pm_exit = None
                    reason  = "startup_reconcile_expired"
                    warnings.append(f"{slug}: kapandı ama çözüm fiyatı yok")

                closed_pos = close_position(pos, reason, pm_exit_price=pm_exit)
                if conn:
                    await log_position_close(conn, closed_pos)
                open_positions.remove(pos)
                closed += 1
                print(f"[reconcile] {slug}: kapatıldı ({reason}, exit={pm_exit})")
            else:
                # Market hâlâ açık — pozisyon sağlıklı
                pass

        except Exception as e:
            warnings.append(f"{slug}: kontrol hatası — {e}")
            print(f"[reconcile] {slug}: hata — {e}")

    if checked > 0:
        print(f"[reconcile] {checked} pozisyon kontrol edildi, {closed} kapatıldı, {len(warnings)} uyarı")

    return {"checked": checked, "closed": closed, "warnings": warnings}
```

- [ ] **Step 13: Testler geçiyor mu?**

```bash
source venv/bin/activate && python -m pytest tests/test_reconcile.py -v 2>&1 | tail -8
```
Beklenen: 3 test PASS

- [ ] **Step 14: Commit**

```bash
git add execution/reconcile.py tests/test_reconcile.py
git commit -m "feat(reconcile): startup pozisyon mutabakatı — kapanmış marketler otomatik kapatılır"
```

---

## Task 6: main_loop.py — Reconcile Entegrasyonu

**Files:**
- Modify: `main_loop.py` — import + startup çağrısı

- [ ] **Step 15: Import ekle**

`main_loop.py` import bölümüne (`from execution.balance import ...` satırının altına):
```python
from execution.reconcile import startup_reconcile
```

- [ ] **Step 16: Startup sırasına ekle**

`main_loop.py` içinde `open_positions = await _load_open_positions(conn)` satırından sonra:

Mevcut (L258-264):
```python
    open_positions = await _load_open_positions(conn)
    closed_today   = await load_closed_today(conn)
    if open_positions:
        print(f"[bot] DB'den {len(open_positions)} açık pozisyon yüklendi.")
    if closed_today:
```

Değiştirilecek:
```python
    open_positions = await _load_open_positions(conn)
    closed_today   = await load_closed_today(conn)
    if open_positions:
        print(f"[bot] DB'den {len(open_positions)} açık pozisyon yüklendi.")
        rec = await startup_reconcile(open_positions, conn)
        if rec["closed"]:
            print(f"[bot] Reconcile: {rec['closed']} pozisyon kapatıldı.")
    if closed_today:
```

- [ ] **Step 17: Tam test suite**

```bash
source venv/bin/activate && python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```
Beklenen: `X passed, Y skipped, 0 failed`

- [ ] **Step 18: Bot restart — DRY_RUN'da reconcile atlanıyor mu?**

```bash
tmux kill-session -t mispricing 2>/dev/null
tmux new-session -d -s mispricing "source venv/bin/activate && PYTHONUNBUFFERED=1 python -u main_loop.py 2>&1 | tee -a logs/main_loop.log"
sleep 5 && grep -i "reconcile\|pozisyon\|Başladı" logs/main_loop.log | head -5
```
Beklenen: `[bot] Başladı — DRY_RUN=True` ve reconcile satırı YOK (DRY_RUN'da atlanıyor)

- [ ] **Step 19: Final commit + push**

```bash
git add main_loop.py
git commit -m "feat(main_loop): startup reconcile — LIVE modda kapanmış pozisyonlar otomatik temizlenir"
git push origin master
```

---

## Self-Review

**Spec coverage:**
- ✅ Fee rate: `data/fee_rate.py` fetch + cache → Scout `taker_fee` → RedTeam fallback
- ✅ Reconciliation: `execution/reconcile.py` → main_loop startup
- ✅ DRY_RUN guard: reconcile Task 4 test 1 doğrular
- ✅ Hata durumları: timeout/exception → fallback her iki modülde

**Placeholder scan:** Yok.

**Type consistency:** `startup_reconcile(open_positions: list[dict], conn) -> dict` — tüm kullanan yerlerde aynı imza.
