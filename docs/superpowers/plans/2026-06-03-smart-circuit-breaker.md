# Smart Circuit Breaker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mevcut kaba `DAILY_LOSS_LIMIT_PCT` kuralını, kâr durumuna göre akıllıca davranan bir devre kesici sistemiyle değiştirmek; soft/hard stop'ları Telegram'dan `/baslat`/`/hardbaslat` komutlarıyla kaldırılabilir hale getirmek.

**Architecture:** Paylaşılan durum (`monitor/state.py`) + karar motoru (`monitor/circuit_breaker.py`) + güncellenmiş `main_loop.py` entegrasyonu. Tüm duraklamalar process'i öldürmez — asyncio event loop yaşar, Telegram polling devam eder.

**Tech Stack:** Python 3.12, asyncio, sqlite3 (P&L takibi), py_clob_client_v2 (LIVE bakiye)

---

## Dosya Haritası

| Dosya | Değişiklik |
|---|---|
| `monitor/state.py` | YENİ — SOFT_PAUSED / HARD_PAUSED bayrakları |
| `monitor/circuit_breaker.py` | YENİ — bankroll + streak karar motoru |
| `monitor/notifier.py` | GÜNCELLEME — notify_restart, notify_soft_stop, notify_hard_stop, notify_streak_warn |
| `monitor/telegram_commands.py` | GÜNCELLEME — /hardbaslat komutu eklendi |
| `config.py` | GÜNCELLEME — DAILY_LOSS_LIMIT_PCT → BUST_PROTECTION_PCT + STREAK_WARN_COUNT |
| `main_loop.py` | GÜNCELLEME — circuit breaker entegrasyonu, restart bildirimi |
| `tests/test_circuit_breaker.py` | YENİ — 8 test |
| `tests/test_circuit_breaker_state.py` | YENİ — 4 test |

---

## Task 1: State Modülü (`monitor/state.py`)

**Files:**
- Create: `monitor/state.py`

- [ ] **Step 1: Dosyayı oluştur**

```python
# monitor/state.py
"""Paylaşılan bot durumu — main_loop ve telegram_commands arasında ortak flag'ler."""

SOFT_PAUSED: bool = False
HARD_PAUSED: bool = False


def soft_pause() -> None:
    global SOFT_PAUSED
    SOFT_PAUSED = True


def soft_resume() -> None:
    global SOFT_PAUSED
    SOFT_PAUSED = False


def hard_pause() -> None:
    global HARD_PAUSED
    HARD_PAUSED = True


def hard_resume() -> None:
    global HARD_PAUSED
    HARD_PAUSED = False


def is_paused() -> bool:
    return SOFT_PAUSED or HARD_PAUSED
```

- [ ] **Step 2: Import testi**

```bash
source venv/bin/activate && python -c "from monitor.state import is_paused, soft_pause, soft_resume, hard_pause, hard_resume; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add monitor/state.py
git commit -m "feat(state): paylasilan bot durumu — SOFT_PAUSED / HARD_PAUSED bayraklari"
```

---

## Task 2: Circuit Breaker Testleri (RED)

**Files:**
- Create: `tests/test_circuit_breaker.py`

- [ ] **Step 1: Failing testleri yaz**

```python
# tests/test_circuit_breaker.py
"""monitor/circuit_breaker.py testleri."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def _reset():
    """Her test öncesi state ve streak sıfırla."""
    import monitor.state as s
    s.SOFT_PAUSED = False
    s.HARD_PAUSED = False
    import monitor.circuit_breaker as cb
    cb._consecutive_losses = 0


def test_win_resets_streak(_reset_fixture):
    from monitor.circuit_breaker import on_trade_closed
    on_trade_closed(pnl=-1.0, current_bankroll=24.0, starting_bankroll=25.0)
    on_trade_closed(pnl=-1.0, current_bankroll=23.0, starting_bankroll=25.0)
    result = on_trade_closed(pnl=+1.0, current_bankroll=24.0, starting_bankroll=25.0)
    import monitor.circuit_breaker as cb
    assert cb._consecutive_losses == 0
    assert result is None


def test_bust_triggers_hard_stop(_reset_fixture):
    from monitor.circuit_breaker import on_trade_closed
    import monitor.state as s
    result = on_trade_closed(pnl=-1.0, current_bankroll=12.0, starting_bankroll=25.0)
    assert result == 'hard_stop'
    assert s.HARD_PAUSED is True


def test_streak_zararda_triggers_soft_stop(_reset_fixture):
    from monitor.circuit_breaker import on_trade_closed
    import monitor.state as s
    for _ in range(6):
        result = on_trade_closed(pnl=-1.0, current_bankroll=20.0, starting_bankroll=25.0)
    assert result == 'soft_stop'
    assert s.SOFT_PAUSED is True
    assert s.HARD_PAUSED is False


def test_streak_karda_still_soft_stop(_reset_fixture):
    """Kârda olsa bile streak >= 6 → SOFT STOP."""
    from monitor.circuit_breaker import on_trade_closed
    import monitor.state as s
    for _ in range(6):
        result = on_trade_closed(pnl=-1.0, current_bankroll=30.0, starting_bankroll=25.0)
    assert result == 'soft_stop'
    assert s.SOFT_PAUSED is True
    assert s.HARD_PAUSED is False


def test_bust_overrides_streak(_reset_fixture):
    """Bankroll %50 altına düşünce hard stop — streak sayısından bağımsız."""
    from monitor.circuit_breaker import on_trade_closed
    result = on_trade_closed(pnl=-1.0, current_bankroll=11.0, starting_bankroll=25.0)
    assert result == 'hard_stop'


def test_five_losses_no_trigger(_reset_fixture):
    """5 arka arkaya kayıp — henüz tetiklememeli (eşik 6)."""
    from monitor.circuit_breaker import on_trade_closed
    import monitor.state as s
    for _ in range(5):
        result = on_trade_closed(pnl=-1.0, current_bankroll=20.0, starting_bankroll=25.0)
    assert result is None
    assert s.SOFT_PAUSED is False


def test_win_after_five_losses_no_soft_stop(_reset_fixture):
    """5 kayıp + 1 kazanç → streak sıfırlanır, soft stop olmamalı."""
    from monitor.circuit_breaker import on_trade_closed
    import monitor.state as s
    for _ in range(5):
        on_trade_closed(pnl=-1.0, current_bankroll=20.0, starting_bankroll=25.0)
    result = on_trade_closed(pnl=+2.0, current_bankroll=22.0, starting_bankroll=25.0)
    assert s.SOFT_PAUSED is False
    assert result is None


@pytest.fixture
def _reset_fixture():
    _reset()
    yield
    _reset()
```

- [ ] **Step 2: Testleri çalıştır — FAIL bekleniyor**

```bash
source venv/bin/activate && python -m pytest tests/test_circuit_breaker.py -v --tb=short 2>&1 | tail -15
```

Expected: `ModuleNotFoundError: No module named 'monitor.circuit_breaker'`

---

## Task 3: Circuit Breaker Implementasyonu (GREEN)

**Files:**
- Create: `monitor/circuit_breaker.py`

- [ ] **Step 1: Implementasyonu yaz**

```python
# monitor/circuit_breaker.py
"""Akıllı devre kesici — bankroll koruması + streak takibi."""
import config
from monitor.state import soft_pause, hard_pause

_consecutive_losses: int = 0

BUST_PROTECTION_PCT: float = getattr(config, "BUST_PROTECTION_PCT", 0.50)
STREAK_WARN_COUNT:   int   = getattr(config, "STREAK_WARN_COUNT", 6)


def reset_streak() -> None:
    global _consecutive_losses
    _consecutive_losses = 0


def on_trade_closed(pnl: float, current_bankroll: float, starting_bankroll: float) -> str | None:
    """
    Her trade kapanışında çağrılır.

    Returns:
        'hard_stop'       → bankroll %50 altına düştü, HARD_PAUSED=True
        'soft_stop'       → streak >= N ve zararda, SOFT_PAUSED=True
        'streak_warning'  → streak >= N ama kârda, devam et
        None              → normal, devam et
    """
    global _consecutive_losses

    if pnl > 0:
        _consecutive_losses = 0
        return None

    # Bust: bankroll yarıya düştü
    if current_bankroll < starting_bankroll * BUST_PROTECTION_PCT:
        hard_pause()
        return 'hard_stop'

    _consecutive_losses += 1

    if _consecutive_losses >= STREAK_WARN_COUNT:
        soft_pause()
        return 'soft_stop'

    return None
```

- [ ] **Step 2: Testleri çalıştır — PASS bekleniyor**

```bash
source venv/bin/activate && python -m pytest tests/test_circuit_breaker.py -v --tb=short 2>&1 | tail -15
```

Expected: `8 passed`

- [ ] **Step 3: Commit**

```bash
git add monitor/circuit_breaker.py tests/test_circuit_breaker.py
git commit -m "feat(circuit_breaker): akilli devre kesici — bust %50 hard stop, streak soft stop"
```

---

## Task 4: Notifier Güncellemesi

**Files:**
- Modify: `monitor/notifier.py`

- [ ] **Step 1: Mevcut notifier'ı oku**

```bash
cat monitor/notifier.py
```

- [ ] **Step 2: Yeni fonksiyonları ekle** (dosyanın sonuna `notify_halt`'ın altına)

```python
def notify_restart(dry_run: bool, bankroll: float) -> None:
    mod = "DRY_RUN" if dry_run else "LIVE"
    send_telegram(f"Bot baslatildi — {mod} | Bankroll: ${bankroll:.2f}")


def notify_soft_stop(streak: int, current_bankroll: float) -> None:
    send_telegram(
        f"SOFT STOP: {streak} arka arkaya kayip + zarar\n"
        f"Bankroll: ${current_bankroll:.2f}\n"
        f"/baslat ile devam"
    )


def notify_hard_stop(current_bankroll: float, starting_bankroll: float) -> None:
    pct = current_bankroll / starting_bankroll * 100
    send_telegram(
        f"HARD STOP: Bakiye %{pct:.0f} seviyesinde (${current_bankroll:.2f})\n"
        f"Bust korumasi devreye girdi!\n"
        f"/hardbaslat ile devam"
    )


def notify_streak_warn(streak: int) -> None:
    send_telegram(
        f"UYARI: {streak} arka arkaya kayip\n"
        f"Sistem karda — devam ediyor"
    )
```

- [ ] **Step 3: Import testi**

```bash
source venv/bin/activate && python -c "from monitor.notifier import notify_restart, notify_soft_stop, notify_hard_stop, notify_streak_warn; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add monitor/notifier.py
git commit -m "feat(notifier): notify_restart, notify_soft_stop, notify_hard_stop, notify_streak_warn"
```

---

## Task 5: Telegram Commands Güncelleme (`/hardbaslat`)

**Files:**
- Modify: `monitor/telegram_commands.py`

- [ ] **Step 1: Failing testi yaz** (`tests/test_telegram_commands.py`'e ekle)

```python
def test_hardbaslat_clears_hard_paused(monkeypatch):
    """/hardbaslat komutu HARD_PAUSED'u temizler."""
    import monitor.state as s
    s.HARD_PAUSED = True
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    from monitor import telegram_commands
    import importlib; importlib.reload(telegram_commands)
    from unittest.mock import patch
    with patch("monitor.telegram_commands.send_telegram"):
        result = telegram_commands.handle_command("/hardbaslat")
    assert s.HARD_PAUSED is False
    assert "devam" in result.lower() or "kaldirildi" in result.lower()


def test_baslat_clears_soft_paused(monkeypatch):
    """/baslat komutu SOFT_PAUSED'u temizler."""
    import monitor.state as s
    s.SOFT_PAUSED = True
    from monitor import telegram_commands
    from unittest.mock import patch
    with patch("monitor.telegram_commands.send_telegram"):
        result = telegram_commands.handle_command("/baslat")
    assert s.SOFT_PAUSED is False
```

- [ ] **Step 2: Testi çalıştır — FAIL bekleniyor**

```bash
source venv/bin/activate && python -m pytest tests/test_telegram_commands.py::test_hardbaslat_clears_hard_paused -v --tb=short
```

Expected: FAIL

- [ ] **Step 3: `handle_command` fonksiyonunu güncelle**

`monitor/telegram_commands.py` içindeki `handle_command` fonksiyonunda `/durdur` ve `/baslat` bloklarını bul ve şu şekilde değiştir:

```python
def handle_command(text: str) -> str:
    text = text.strip()

    if text == "/durum":
        positions = _query_open_positions()
        daily_pnl = _query_daily_pnl()
        return build_durum_message(positions, daily_pnl)

    if text == "/durdur":
        ks_arm()
        return "Kill switch DEVREDE. Bot durdu. /baslat ile kaldir."

    if text == "/baslat":
        from monitor.state import soft_resume
        soft_resume()
        ks_disarm()
        return "Soft stop KALDIRILDI. Bot devam ediyor."

    if text == "/hardbaslat":
        from monitor.state import hard_resume
        hard_resume()
        return "Hard stop KALDIRILDI. Bot devam ediyor."

    if text.startswith("/istatistik"):
        hours = parse_hours(text)
        s     = _query_stats(hours)
        return build_stats_message(s["total"], s["wins"], s["losses"], s["pnl"], hours)

    return f"Bilinmeyen komut: {text}\nKomutlar: /durum /istatistik /istatistik6 /durdur /baslat /hardbaslat"
```

- [ ] **Step 4: Testleri çalıştır — PASS bekleniyor**

```bash
source venv/bin/activate && python -m pytest tests/test_telegram_commands.py -v --tb=short 2>&1 | tail -10
```

Expected: `14 passed`

- [ ] **Step 5: Commit**

```bash
git add monitor/telegram_commands.py tests/test_telegram_commands.py
git commit -m "feat(telegram): /hardbaslat komutu — HARD_PAUSED kaldirilir"
```

---

## Task 6: Config Güncellemesi

**Files:**
- Modify: `config.py`

- [ ] **Step 1: `DAILY_LOSS_LIMIT_PCT` satırını değiştir**

`config.py`'de şu satırı:
```python
DAILY_LOSS_LIMIT_PCT = 0.30   # Gunluk kayip %30'a ulasinca SISTEM DURUR (25/50 USD bankroll icin 5-6 arka arkaya kayba izin verir)
```

Şununla değiştir:
```python
BUST_PROTECTION_PCT  = 0.50   # Bankroll baslangicin %50'sine dusunce → HARD STOP
STREAK_WARN_COUNT    = 6      # N arka arkaya kayip → soft stop (zararda) veya uyari (karda)
```

- [ ] **Step 2: Config import testi**

```bash
source venv/bin/activate && python -c "import config; print(config.BUST_PROTECTION_PCT, config.STREAK_WARN_COUNT)"
```

Expected: `0.5 6`

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "config: DAILY_LOSS_LIMIT_PCT → BUST_PROTECTION_PCT + STREAK_WARN_COUNT"
```

---

## Task 7: Main Loop Entegrasyonu

**Files:**
- Modify: `main_loop.py`

- [ ] **Step 1: Import'ları güncelle** (dosyanın başındaki import bloğunu güncelle)

Mevcut:
```python
from monitor.notifier import notify_open, notify_close, notify_halt
from monitor.kill_switch import check as kill_switch_check
from monitor.telegram_commands import poll_commands
```

Yeni:
```python
from monitor.notifier import notify_open, notify_close, notify_halt, notify_restart, notify_soft_stop, notify_hard_stop, notify_streak_warn
from monitor.kill_switch import check as kill_switch_check
from monitor.telegram_commands import poll_commands
from monitor.state import is_paused, HARD_PAUSED, SOFT_PAUSED
from monitor import circuit_breaker
```

- [ ] **Step 2: `_daily_loss_usd` fonksiyonunu bul ve kaldır**

`main_loop.py` içindeki `def _daily_loss_usd(...)` fonksiyonunu tamamen kaldır. Artık kullanılmayacak.

- [ ] **Step 3: `main()` fonksiyonuna starting_bankroll ve restart bildirimi ekle**

`main()` içinde `conn = await get_connection()` satırından hemen sonra:

```python
    starting_bankroll = await get_effective_bankroll(BANKROLL_CONFIG)
    circuit_breaker.BUST_PROTECTION_PCT = config.BUST_PROTECTION_PCT
    circuit_breaker.STREAK_WARN_COUNT   = config.STREAK_WARN_COUNT
    notify_restart(dry_run=config.DRY_RUN, bankroll=starting_bankroll)
```

- [ ] **Step 4: Ana while döngüsünü güncelle** — kill_switch kontrolünün hemen ALTINA pause kontrolü ekle

Mevcut:
```python
        if kill_switch_check():
            notify_halt("kill_switch")
            print("[bot] Kill switch etkin — sistem durdu.")
            break
```

Yeni:
```python
        if kill_switch_check():
            notify_halt("kill_switch")
            print("[bot] Kill switch etkin — sistem durdu.")
            break

        # Soft/Hard pause — process yaşar, Telegram polling devam eder
        if is_paused():
            import monitor.state as _st
            reason = "hard_stop" if _st.HARD_PAUSED else "soft_stop"
            print(f"[bot] {reason} — bekliyor... (/baslat veya /hardbaslat)")
            await asyncio.sleep(SCAN_INTERVAL_SECS)
            continue
```

- [ ] **Step 5: Trade kapanışından sonra circuit breaker çağrısı ekle**

`main_loop.py`'de `notify_close(pos)` çağrılarının hemen ALTINA şunu ekle:

`_monitor_positions` fonksiyonunda, `close_position` çağrısından sonra kapatılan pozisyonu döndürürken circuit_breaker'ı çağır. Bunun için `_monitor_positions`'ın döndürdüğü `closed` pozisyonları main loop'ta işlenirken:

```python
                # Kapanan pozisyonlar için circuit breaker
                for pos in closed_today[n_closed_before:]:
                    notify_close(pos)
                    pnl = pos.get("realized_pnl") or 0.0
                    effective_bankroll = await get_effective_bankroll(BANKROLL_CONFIG)
                    cb_result = circuit_breaker.on_trade_closed(
                        pnl=pnl,
                        current_bankroll=effective_bankroll,
                        starting_bankroll=starting_bankroll,
                    )
                    if cb_result == 'hard_stop':
                        notify_hard_stop(effective_bankroll, starting_bankroll)
                        print(f"[bot] HARD STOP: bakiye ${effective_bankroll:.2f} / başlangıç ${starting_bankroll:.2f}")
                    elif cb_result == 'soft_stop':
                        notify_soft_stop(config.STREAK_WARN_COUNT, effective_bankroll)
                        print(f"[bot] SOFT STOP: {config.STREAK_WARN_COUNT} arka arkaya kayıp + zarar")
                    elif cb_result == 'streak_warning':
                        notify_streak_warn(config.STREAK_WARN_COUNT)
                        print(f"[bot] UYARI: {config.STREAK_WARN_COUNT} arka arkaya kayıp — kârda, devam")
```

Mevcut `notify_close` döngüsünü bu blokla değiştir.

- [ ] **Step 6: `display_loss` satırlarını temizle**

`main()` içindeki şu satırı kaldır:
```python
        display_loss = 0.0 if config.DRY_RUN else _daily_loss_usd(closed_today)
        print(f"[bot] Bugün {len(closed_today)} kapanan pozisyon geri yüklendi, günlük kayıp: ${display_loss:.2f} (DRY_RUN={config.DRY_RUN})")
```

Yerine:
```python
        if closed_today:
            print(f"[bot] Bugün {len(closed_today)} kapanan pozisyon geri yüklendi.")
```

- [ ] **Step 7: Bot'u yeniden başlat ve log kontrol et**

```bash
tmux kill-session -t mispricing 2>/dev/null
tmux new-session -d -s mispricing "source venv/bin/activate && PYTHONUNBUFFERED=1 python -u main_loop.py 2>&1 | tee -a logs/main_loop.log"
sleep 4
tail -5 logs/main_loop.log
```

Expected log: `[bot] Başladı — DRY_RUN=True, tarama=15s`
Expected Telegram: "Bot baslatildi — DRY_RUN | Bankroll: $25.00"

- [ ] **Step 8: Commit**

```bash
git add main_loop.py
git commit -m "feat(main_loop): smart circuit breaker entegrasyonu — hard/soft stop + restart bildirimi"
```

---

## Task 8: Tam Test Suite Doğrulama

- [ ] **Step 1: Tüm testleri çalıştır**

```bash
source venv/bin/activate && python -m pytest tests/ -q --tb=short 2>&1 | tail -8
```

Expected: `233+ passed, X skipped, 0 failed`

- [ ] **Step 2: Manuel Telegram testi**

Bot çalışırken Telegram'dan gönder:
1. `/durum` → açık pozisyonlar gelmeli
2. `/istatistik6` → son 6 saat istatistik gelmeli
3. `/hardbaslat` → "Hard stop KALDIRILDI" gelmeli (zaten paused değildi ama hata vermemeli)

- [ ] **Step 3: Final commit + push**

```bash
git add -A
git commit -m "feat: smart circuit breaker tam entegrasyon — tum testler gecti"
git push origin master
```

---

## Özet

| Kural | Tetikleyici | Sonuç | Kurtarma |
|---|---|---|---|
| Bust koruması | Bankroll < %50 başlangıç | HARD STOP | `/hardbaslat` |
| Streak (zararda) | 6 arka arkaya kayıp + zarar | SOFT STOP | `/baslat` |
| Streak | 6 arka arkaya kayıp (kârda da zararda da) | SOFT STOP | `/baslat` |
| Restart | Her bot başlangıcı | Telegram bildirim | — |
| Kill switch | Manuel `/durdur` | Bot durur | `/baslat` |
