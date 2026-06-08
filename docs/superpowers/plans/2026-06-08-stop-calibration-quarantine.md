# Stop Kalibrasyon + ETH-NO Quarantine + NO Exact MAE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop kanamasını -%30'dan -%25'e çekmek, ETH-NO'yu karantinaya almak ve NO pozisyonlar için MAE takibini exact WS bid üzerine taşımak.

**Architecture:** Üç bağımsız değişiklik sırayla uygulanır. Task 1 tamamen `position/manager.py` sabitleridir. Task 2 `config.py`'e yeni sabit ekler ve `council/scout.py`'e tek-satır filtre ekler. Task 3 `manager.py`'e `ws_prices` import ve NO branch değiştirir — herhangi bir API değişikliği gerektirmez çünkü `main_loop.py` zaten her iki token ID'yi de WS'e subscribe ediyor.

**Tech Stack:** Python 3.11+, aiosqlite, pytest-asyncio, unittest.mock

**Veri Bağlamı (karar gerekçesi):**
- `sl_trigger_pct` avg=-29.9%, median=-29.0% → stop hep MAX=0.30'da → geniş
- Simülasyon: Fixed -25% → P&L +$0.330, FalseCut=0 (winner P25 MAE=-22.4%)
- ETH-NO: 1W/4L, WR=%20, P&L=-$1.169 (24h)
- NO stop trades: mae_data_quality='estimated' %73 → WS no_token_id subscribe var ama manager complement kullanıyor

---

## Task 1: STOP_LOSS_MAX=0.25 + MIN_HOLD_SECS=15

**Files:**
- Modify: `position/manager.py:17,19`
- Test: `tests/test_manager.py` (yeni testler eklenir, mevcut korunur)

**Mevcut kod (manager.py:17-19):**
```python
STOP_LOSS_MAX          = 0.30  # Erken tutuşta max tolerans (%30) — pozisyonun toparlama vakti var
STOP_LOSS_MIN          = 0.12  # Vadeye yakında min tolerans (%12) — gamma trap erken tespiti
MIN_HOLD_SECS          = 30    # İlk 30s: stop_loss çalışmaz — anlık tersine dönüş filtresi
```

- [ ] **Step 1: Failing testleri yaz**

`tests/test_manager.py` dosyasının SONUNA ekle:

```python
def test_stop_loss_max_constant_is_025():
    """Kalibrasyon: STOP_LOSS_MAX=0.25 olmalı (eski 0.30 → kalibre edildi)."""
    from position.manager import STOP_LOSS_MAX
    assert STOP_LOSS_MAX == pytest.approx(0.25), f"STOP_LOSS_MAX={STOP_LOSS_MAX}, 0.25 bekleniyor"


def test_min_hold_secs_constant_is_15():
    """Kalibrasyon: MIN_HOLD_SECS=15 olmalı (eski 30 → daha çevik)."""
    from position.manager import MIN_HOLD_SECS
    assert MIN_HOLD_SECS == 15, f"MIN_HOLD_SECS={MIN_HOLD_SECS}, 15 bekleniyor"


def test_stop_triggers_at_025_threshold():
    """Yeni eşik: entry=0.60, 16s hold, price=0.450 → stop_loss_hit (0.25 eşiği aşıldı)."""
    pos = _pos(action="YES", entry=0.60, fair=0.75)
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=16)).isoformat()
    # 16s hold, 600s to expiry → dynamic_stop ≈ 0.247
    # stop_at = 0.60 * (1 - 0.247) = 0.452 → price=0.450 < 0.452 → STOP
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.450, time_to_expiry_secs=600)
    assert result == "stop_loss_hit"


def test_stop_does_not_trigger_within_15s():
    """MIN_HOLD_SECS=15: 14s içinde büyük çöküşte bile stop tetiklenmemeli."""
    pos = _pos(action="YES", entry=0.60, fair=0.75)
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=14)).isoformat()
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.10, time_to_expiry_secs=300)
    assert result is None, "14s < MIN_HOLD_SECS=15 → stop_loss çalışmamalı"


def test_stop_can_trigger_after_15s():
    """MIN_HOLD_SECS=15: 16s geçtikten sonra büyük düşüşte stop_loss_hit döner."""
    pos = _pos(action="YES", entry=0.60, fair=0.75)
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=16)).isoformat()
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.10, time_to_expiry_secs=300)
    assert result == "stop_loss_hit", "16s ≥ MIN_HOLD_SECS=15 → stop_loss_hit bekleniyor"
```

- [ ] **Step 2: Testlerin FAIL ettiğini doğrula**

```bash
cd /root/mispricing_agent
python -m pytest tests/test_manager.py::test_stop_loss_max_constant_is_025 \
                 tests/test_manager.py::test_min_hold_secs_constant_is_15 \
                 tests/test_manager.py::test_stop_triggers_at_025_threshold \
                 tests/test_manager.py::test_stop_does_not_trigger_within_15s \
                 tests/test_manager.py::test_stop_can_trigger_after_15s -v
```

Beklenen: `FAILED` — `AssertionError: STOP_LOSS_MAX=0.30, 0.25 bekleniyor` ve `MIN_HOLD_SECS=30`.

Not: `test_stop_triggers_at_025_threshold` de FAIL edebilir (eski 0.30 eşiğinde price=0.450 stop tetiklemeyebilir).
Not: `test_stop_does_not_trigger_within_15s` eski MIN_HOLD_SECS=30'da PASS edebilir (30s > 14s dolduğu için stop zaten çalışmıyor). Bu normal.
Not: `test_stop_can_trigger_after_15s` eski MIN_HOLD_SECS=30'da FAIL eder (16s < 30s → stop çalışmaz).

- [ ] **Step 3: Minimal implementasyon — manager.py sabitleri değiştir**

`position/manager.py:17,19` satırlarını değiştir:

```python
STOP_LOSS_MAX          = 0.25  # Kalibrasyon: -%25 eşiği (eski 0.30 — veri: winner P25 MAE=-22.4%, loser P50 MAE=-29.5%)
STOP_LOSS_MIN          = 0.12  # Vadeye yakında min tolerans (%12) — gamma trap erken tespiti
MIN_HOLD_SECS          = 15    # Kalibrasyon: ilk 15s stop çalışmaz (eski 30 — daha çevik giriş koruması)
```

- [ ] **Step 4: Testlerin PASS ettiğini doğrula**

```bash
python -m pytest tests/test_manager.py::test_stop_loss_max_constant_is_025 \
                 tests/test_manager.py::test_min_hold_secs_constant_is_15 \
                 tests/test_manager.py::test_stop_triggers_at_025_threshold \
                 tests/test_manager.py::test_stop_does_not_trigger_within_15s \
                 tests/test_manager.py::test_stop_can_trigger_after_15s -v
```

Beklenen: `5 passed`.

- [ ] **Step 5: Regresyon kontrolü**

```bash
python -m pytest tests/test_manager.py -v
```

Beklenen: tüm mevcut testler hâlâ geçmeli. `test_check_exit_stop_loss_hit_still_has_mae_mfe` 60s hold kullandığı için yeni MIN_HOLD_SECS=15'te hâlâ PASS eder.

- [ ] **Step 6: Commit**

```bash
git add position/manager.py tests/test_manager.py
git commit -m "feat(calibration): STOP_LOSS_MAX 0.30→0.25, MIN_HOLD_SECS 30→15 — veri: winner P25 MAE=-22.4%, loser P50=-29.5%"
```

---

## Task 2: ETH-NO Geçici Quarantine

**Files:**
- Modify: `config.py` (yeni `BLOCKED_COMBOS` sabiti eklenir)
- Modify: `council/scout.py:233` (quarantine check, signal belirlendikten hemen sonra)
- Test: `tests/test_scout.py` (yeni testler eklenir)

**Gerekçe:** ETH-NO son 24h: 1W/4L, WR=%20, P&L=-$1.169. Kalıcı yasak değil — NO exact pricing fix sonrası yeniden değerlendirilecek.

- [ ] **Step 1: Failing testi yaz**

`tests/test_scout.py` dosyasının SONUNA ekle (dosyanın başındaki import'lar zaten mevcut — `import config`, `from council.scout import ... _process_market` gerekiyor, yoksa ekle):

```python
@pytest.mark.asyncio
async def test_process_market_eth_no_quarantined(monkeypatch):
    """config.BLOCKED_COMBOS=[('ETH','NO')] olduğunda ETH-NO sinyali None döner."""
    from unittest.mock import AsyncMock, MagicMock
    import council.scout as scout

    monkeypatch.setattr(config, "BLOCKED_COMBOS", [("ETH", "NO")])

    m = {
        "question": "Ethereum Up or Down",
        "slug": "eth-updown-15m-9999999999",
        "clobTokenIds": '["yes-eth-tok", "no-eth-tok"]',
    }

    # parse_market_window → geçerli pencere (600s kaldı)
    monkeypatch.setattr(scout, "parse_market_window", lambda _: {
        "start_ms": 0, "end_ms": 10**12, "seconds_remaining": 600,
        "best_bid": 0.44, "best_ask": 0.56, "neg_risk": False,
    })
    # WS cache'de YES ask var — NO sinyali üretecek
    mock_ws = MagicMock()
    mock_ws.get_ask.return_value = 0.56
    mock_ws.get_bid.return_value = 0.44
    monkeypatch.setattr(scout, "_ws_prices", mock_ws)
    monkeypatch.setattr(scout, "_parse_token_ids", lambda _: ["yes-eth-tok", "no-eth-tok"])
    monkeypatch.setattr(scout, "price_at_timestamp", AsyncMock(return_value=3000.0))
    monkeypatch.setattr(scout, "current_price", AsyncMock(return_value=3000.0))
    # fair=0.35 → yes_edge=0.35-0.56<0, no_edge=0.56-0.35=0.21>MIN_EDGE → NO sinyali
    monkeypatch.setattr(scout, "fair_yes", lambda *a, **kw: 0.35)
    monkeypatch.setattr(scout, "fetch_fee_rate", AsyncMock(return_value=0.02))
    monkeypatch.setattr(scout, "get_clob_price", AsyncMock(return_value=0.41))

    result = await scout._process_market(m, {"ETH": 0.80})
    assert result is None, f"ETH-NO quarantine: None bekleniyor, {result!r} geldi"


@pytest.mark.asyncio
async def test_process_market_eth_yes_not_quarantined(monkeypatch):
    """ETH-YES quarantine'de DEĞİL — YES sinyali engellenmemeli."""
    from unittest.mock import AsyncMock, MagicMock
    import council.scout as scout

    monkeypatch.setattr(config, "BLOCKED_COMBOS", [("ETH", "NO")])

    m = {
        "question": "Ethereum Up or Down",
        "slug": "eth-updown-15m-9999999998",
        "clobTokenIds": '["yes-eth-tok2", "no-eth-tok2"]',
    }

    monkeypatch.setattr(scout, "parse_market_window", lambda _: {
        "start_ms": 0, "end_ms": 10**12, "seconds_remaining": 600,
        "best_bid": 0.44, "best_ask": 0.56, "neg_risk": False,
    })
    mock_ws = MagicMock()
    mock_ws.get_ask.return_value = 0.56
    mock_ws.get_bid.return_value = 0.44
    monkeypatch.setattr(scout, "_ws_prices", mock_ws)
    monkeypatch.setattr(scout, "_parse_token_ids", lambda _: ["yes-eth-tok2", "no-eth-tok2"])
    monkeypatch.setattr(scout, "price_at_timestamp", AsyncMock(return_value=3000.0))
    monkeypatch.setattr(scout, "current_price", AsyncMock(return_value=3000.0))
    # fair=0.72 → yes_edge=0.72-0.56=0.16>MIN_EDGE → YES sinyali → quarantine'e takılmamalı
    monkeypatch.setattr(scout, "fair_yes", lambda *a, **kw: 0.72)
    monkeypatch.setattr(scout, "fetch_fee_rate", AsyncMock(return_value=0.02))
    monkeypatch.setattr(scout, "get_clob_price", AsyncMock(return_value=0.56))

    result = await scout._process_market(m, {"ETH": 0.80})
    assert result is not None, "ETH-YES quarantine dışında — sinyali engellenmemeli"
    assert result["action"] == "YES"
```

**Not:** `test_scout.py` import satırı: `from council.scout import scan_edges, _asset_of, _edge_signal, _drift_ok, MIN_SECONDS` → `_process_market` da eklenmeli:

```python
from council.scout import scan_edges, _asset_of, _edge_signal, _drift_ok, _process_market, MIN_SECONDS
```

- [ ] **Step 2: Testlerin FAIL ettiğini doğrula**

```bash
python -m pytest tests/test_scout.py::test_process_market_eth_no_quarantined \
                 tests/test_scout.py::test_process_market_eth_yes_not_quarantined -v
```

Beklenen:
- `test_process_market_eth_no_quarantined` → FAIL: `ETH-NO quarantine: None bekleniyor, {...} geldi` (henüz quarantine yok)
- `test_process_market_eth_yes_not_quarantined` → PASS veya ImportError (import düzeltilince PASS olur)

- [ ] **Step 3: config.py'e BLOCKED_COMBOS ekle**

`config.py` sonuna (`TRACKED_ASSETS` satırından SONRA) ekle:

```python
# ── Geçici quarantine (NO exact pricing fix sonrası yeniden değerlendirilecek) ──
BLOCKED_COMBOS = [("ETH", "NO")]  # ETH-NO: 1W/4L WR=%20 P&L=-$1.17 (2026-06-08, 24h sample)
```

- [ ] **Step 4: scout.py'e quarantine check ekle**

`council/scout.py`'de, `signal = _edge_signal(fair, clob_ask, yes_bid)` satırından HEMEN SONRA (mevcut `if signal is None: return None` bloğundan SONRA):

**Mevcut (yaklaşık satır 231-233):**
```python
    signal = _edge_signal(fair, clob_ask, yes_bid)
    if signal is None:
        return None

    # Max entry fiyatı filtresi: pahalı tokenlar reversal'da çok zararlı
    entry_price = clob_ask if signal["action"] == "YES" else None
```

**Yeni (quarantine check eklendi):**
```python
    signal = _edge_signal(fair, clob_ask, yes_bid)
    if signal is None:
        return None

    # Quarantine: geçici blok — config.BLOCKED_COMBOS tarafından engellenen asset/action çiftleri
    _blocked = {tuple(c) for c in getattr(config, "BLOCKED_COMBOS", [])}
    if _blocked and (asset, signal["action"]) in _blocked:
        _inc("skipped_quarantine")
        return None

    # Max entry fiyatı filtresi: pahalı tokenlar reversal'da çok zararlı
    entry_price = clob_ask if signal["action"] == "YES" else None
```

- [ ] **Step 5: Testlerin PASS ettiğini doğrula**

```bash
python -m pytest tests/test_scout.py::test_process_market_eth_no_quarantined \
                 tests/test_scout.py::test_process_market_eth_yes_not_quarantined -v
```

Beklenen: `2 passed`.

- [ ] **Step 6: Tüm scout testleri regresyon kontrolü**

```bash
python -m pytest tests/test_scout.py -v
```

Beklenen: mevcut testler hâlâ geçmeli.

- [ ] **Step 7: Commit**

```bash
git add config.py council/scout.py tests/test_scout.py
git commit -m "feat(quarantine): ETH-NO geçici blok — BLOCKED_COMBOS config + scout filtre (WR=%20, P&L=-\$1.17)"
```

---

## Task 3: NO Exact MAE Fix (complement → WS no_token_id bid)

**Files:**
- Modify: `position/manager.py` (import ekle + NO branch düzelt + MAE quality güncelle)
- Modify: `tests/test_manager.py` (yeni NO exact testleri + mevcut NO testi güncelle)

**Bağlam:** `main_loop.py:231-232` zaten BOTH `yes_token_id` + `no_token_id`'yi WS'e subscribe ediyor. Yani `ws_prices.get_bid(no_token_id)` hazır — sadece `manager.py` complement yerine bunu kullanmıyor.

**Mevcut akış (manager.py:118-123):**
```python
if position["action"] == "YES":
    current_val = pm_yes_price
    target_val  = position["fair_value"]
else:
    current_val = 1 - pm_yes_price   # ← TAHMINI (estimated)
    target_val  = 1 - position["fair_value"]
```

**Hedef:** NO için önce `ws_prices.get_bid(no_token_id)`, yoksa complement fallback.

- [ ] **Step 1: Failing testleri yaz**

`tests/test_manager.py` dosyasının SONUNA ekle:

```python
def test_no_position_uses_no_token_bid_for_mae():
    """NO pozisyon: no_token_id WS bid varsa MAE exact'tir (complement değil)."""
    from unittest.mock import patch
    pos = _pos(action="NO", entry=0.45, fair=0.25)
    pos["no_token_id"] = "no-tok-abc"
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()

    with patch("position.manager._ws.get_bid", return_value=0.38) as mock_bid:
        check_exit(pos, hl_price=60000, pm_yes_price=0.65, time_to_expiry_secs=300)
        mock_bid.assert_called_with("no-tok-abc")
        assert pos["mae_data_quality"] == "exact", (
            f"WS bid mevcut → exact bekleniyor, '{pos['mae_data_quality']}' geldi"
        )
        assert pos.get("mae_px") == pytest.approx(0.38), (
            f"mae_px complement değil WS bid olmalı: 0.38 bekleniyor, {pos.get('mae_px')} geldi"
        )


def test_no_position_falls_back_to_complement_when_no_ws_bid():
    """WS no_token_id bid yoksa complement kullanılmalı ve quality='estimated'."""
    from unittest.mock import patch
    pos = _pos(action="NO", entry=0.45, fair=0.25)
    pos["no_token_id"] = "no-tok-xyz"
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()

    with patch("position.manager._ws.get_bid", return_value=None):
        check_exit(pos, hl_price=60000, pm_yes_price=0.58, time_to_expiry_secs=300)
        assert pos["mae_data_quality"] == "estimated"
        assert pos.get("mae_px") == pytest.approx(1 - 0.58)


def test_no_position_without_no_token_id_uses_complement():
    """no_token_id pozisyonda yoksa complement fallback, quality='estimated'."""
    pos = _pos(action="NO", entry=0.45, fair=0.25)
    # no_token_id yok
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    check_exit(pos, hl_price=60000, pm_yes_price=0.55, time_to_expiry_secs=300)
    assert pos["mae_data_quality"] == "estimated"
    assert pos.get("mae_px") == pytest.approx(1 - 0.55)


def test_no_stop_loss_uses_exact_no_bid():
    """NO stop-loss kararı da exact WS no_bid kullanmalı (complement değil)."""
    from unittest.mock import patch
    pos = _pos(action="NO", entry=0.45, fair=0.25)
    pos["no_token_id"] = "no-tok-stop"
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()

    # no_bid=0.29 → (0.29-0.45)/0.45 = -35.6% → -%25 eşiğini aştı → stop_loss_hit
    with patch("position.manager._ws.get_bid", return_value=0.29):
        result = check_exit(pos, hl_price=60000, pm_yes_price=0.72, time_to_expiry_secs=300)
        assert result == "stop_loss_hit", (
            f"no_bid=0.29 ile -%35 kayıp → stop_loss_hit bekleniyor, '{result}' geldi"
        )
```

- [ ] **Step 2: Mevcut NO testi kontrol et**

`test_check_exit_no_action_tracks_mfe_correctly` testi şu an complement kullanıyor ve `no_token_id` olmadan çağırıyor. Bu test fix sonrası hâlâ PASS etmeli (no_token_id yoksa fallback complement). Confirm et:

```bash
python -m pytest tests/test_manager.py::test_check_exit_no_action_tracks_mfe_correctly -v
```

Bu test fix öncesi de PASS etmeli — fallback davranışı korunuyor.

- [ ] **Step 3: Yeni testlerin FAIL ettiğini doğrula**

```bash
python -m pytest tests/test_manager.py::test_no_position_uses_no_token_bid_for_mae \
                 tests/test_manager.py::test_no_position_falls_back_to_complement_when_no_ws_bid \
                 tests/test_manager.py::test_no_position_without_no_token_id_uses_complement \
                 tests/test_manager.py::test_no_stop_loss_uses_exact_no_bid -v
```

Beklenen: `FAILED` (henüz `_ws` import yok, `get_bid` kullanılmıyor).

- [ ] **Step 4: manager.py'i güncelle**

**4a. Import ekle** (`position/manager.py:8-9` arası, `import config` satırından SONRA):

```python
import config
from data import ws_prices as _ws
```

**4b. NO branch'i güncelle** (`position/manager.py:118-123`, mevcut `if/else` bloğunu değiştir):

```python
    if position["action"] == "YES":
        current_val  = pm_yes_price
        target_val   = position["fair_value"]
        _mae_quality = "exact"
    else:
        _no_tid = position.get("no_token_id")
        _no_bid = _ws.get_bid(_no_tid) if _no_tid else None
        if _no_bid is not None:
            current_val  = _no_bid
            _mae_quality = "exact"
        else:
            current_val  = 1 - pm_yes_price
            _mae_quality = "estimated"
        target_val = 1 - position["fair_value"]
```

**4c. MAE quality satırını güncelle** (`position/manager.py:128-129`):

Mevcut:
```python
        position["price_source"] = "rest"
        position["mae_data_quality"] = "estimated" if position["action"] == "NO" else "rest"
```

Yeni:
```python
        position["price_source"]     = "rest"
        position["mae_data_quality"] = _mae_quality
```

- [ ] **Step 5: Testlerin PASS ettiğini doğrula**

```bash
python -m pytest tests/test_manager.py::test_no_position_uses_no_token_bid_for_mae \
                 tests/test_manager.py::test_no_position_falls_back_to_complement_when_no_ws_bid \
                 tests/test_manager.py::test_no_position_without_no_token_id_uses_complement \
                 tests/test_manager.py::test_no_stop_loss_uses_exact_no_bid -v
```

Beklenen: `4 passed`.

- [ ] **Step 6: Tüm manager testleri regresyon kontrolü**

```bash
python -m pytest tests/test_manager.py -v
```

Beklenen: tüm testler (Task 1 + Task 3 dahil) PASS. `test_check_exit_no_action_tracks_mfe_correctly` hâlâ PASS (no_token_id yoksa complement fallback).

- [ ] **Step 7: Commit**

```bash
git add position/manager.py tests/test_manager.py
git commit -m "feat(mae): NO pozisyon exact MAE — ws no_token_id bid direkt, complement sadece fallback"
```

---

## Final: Tam Test Süiti + Bot Restart

- [ ] **Tüm testler yeşil**

```bash
python -m pytest --tb=short -q
```

Beklenen: `481+ passed, 8 skipped, 0 failed`.

- [ ] **Bot başlat (pause'dan çıkar)**

```bash
# VPS'te:
kill $(cat logs/bot.pid 2>/dev/null) 2>/dev/null; sleep 1
PYTHONUNBUFFERED=1 python main_loop.py >> logs/bot.log 2>&1 &
echo $! > logs/bot.pid
```

- [ ] **İlk 20 trade sonrası gözlem sorgusu**

```python
# İlk kontrol (20 trade sonrası DB'den):
SELECT
    count(*) as total,
    sum(case when exit_reason='stop_loss_hit' then 1 else 0 end) as stops,
    avg(case when exit_reason='stop_loss_hit' then sl_trigger_pct end) as avg_trigger,
    avg(case when exit_reason='stop_loss_hit' then sl_fill_pct end) as avg_fill,
    sum(case when asset='ETH' and action='NO' then 1 else 0 end) as eth_no_count,
    avg(realized_pnl) as avg_pnl
FROM positions
WHERE dry_run=0 AND status='closed'
ORDER BY ts_close DESC
LIMIT 20;
```

ETH-NO count = 0 → quarantine çalışıyor.
avg_trigger ≈ -25% → yeni eşik aktif.

---

## Self-Review

**Spec coverage:**
- ✅ STOP_LOSS_MAX 0.30→0.25 (Task 1)
- ✅ MIN_HOLD_SECS 30→15 (Task 1)
- ✅ ETH-NO quarantine config + scout filter (Task 2)
- ✅ NO exact MAE via no_token_id WS bid (Task 3)
- ✅ Complement fallback when WS miss (Task 3)
- ✅ TDD tüm görevlerde
- ✅ Bot restart adımı

**Placeholder scan:** Yok — tüm kod blokları eksiksiz.

**Type consistency:**
- `_mae_quality`: str, Task 3 boyunca tutarlı
- `_no_tid`, `_no_bid`: Task 3'te tanımlanıp kullanılıyor
- `_blocked`: Task 2'de tuple set, scout.py'de `in` operatörüyle kontrol
- `check_exit` imzası değişmedi — Task 1 ve 3 backward compatible
