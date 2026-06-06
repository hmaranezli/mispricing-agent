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


# ── Task 2: check_exit — zaman + expiry ──────────────────────────────────────

def test_check_exit_near_expiry_returns_none():
    """time_to_expiry_secs < 90, fiyat OK → None (profit_target/max_hold engellenir)."""
    pos = _position(held_minutes=15)
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.40,
                        time_to_expiry_secs=80)
    assert result is None


def test_check_exit_near_expiry_still_fires_stop_loss():
    """Son 90s'de bile stop_loss çalışmalı — NEAR_EXPIRY tam kayıpları engellemez.

    Mevcut kod near_expiry'de her şeyi None döndürüyor → -$1.25 tam kayıp.
    Fix: near_expiry sadece profit_target'ı engellemeli, stop_loss geçmeli.
    entry=0.35, eşik=0.35×0.80=0.28; pm=0.20 < 0.28 → stop_loss_hit bekleniyor.
    """
    pos = _position(action="YES", held_minutes=8)
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.20,
                        time_to_expiry_secs=50)
    assert result == "stop_loss_hit", (
        f"Near-expiry'de felaket zararı durdurulmalı, got: {result}"
    )


def test_check_exit_max_hold_time():
    """MAX_HOLD_MINUTES (20) geçmişse → 'max_hold_time'."""
    pos = _position(held_minutes=21)
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


# ── Task 3: check_exit — kâr hedefi (2-döngü onay + slippage eşiği) ───────────

def test_check_exit_profit_needs_two_cycles_yes():
    """YES: büyük kâr tek döngüde değil, 2 ardışık döngüde onaylanınca çıkar.

    entry=0.35, fair=0.55, edge=0.20; pm=0.53 → captured=0.18 (>=0.10), fraction=0.90 (>=0.85).
    Tek snapshot spike'ı yanlış çıkış yaptırmasın diye 2 döngü gerek.
    """
    pos = _position(action="YES", held_minutes=5)
    first = check_exit(pos, hl_price=95500, pm_yes_price=0.53, time_to_expiry_secs=900)
    assert first is None, "İlk döngü tek başına çıkış yaptırmamalı"
    second = check_exit(pos, hl_price=95500, pm_yes_price=0.53, time_to_expiry_secs=900)
    assert second == "profit_target_hit"


def test_check_exit_profit_needs_two_cycles_no():
    """NO: büyük kâr 2 ardışık döngüde onaylanınca çıkar.

    entry=0.33, fair_NO=0.65, edge=0.32; pm_yes=0.38 → 1-pm=0.62, captured=0.29, fraction=0.906.
    """
    pos = _position(action="NO", held_minutes=5)
    first = check_exit(pos, hl_price=94800, pm_yes_price=0.38, time_to_expiry_secs=900)
    assert first is None
    second = check_exit(pos, hl_price=94800, pm_yes_price=0.38, time_to_expiry_secs=900)
    assert second == "profit_target_hit"


def test_check_exit_profit_resets_on_dip():
    """Kâr sinyali ardışık değilse sayaç sıfırlanır → tek seferlik spike çıkış yapmaz."""
    pos = _position(action="YES", held_minutes=5)
    check_exit(pos, hl_price=95500, pm_yes_price=0.53, time_to_expiry_secs=900)  # count=1
    mid = check_exit(pos, hl_price=95000, pm_yes_price=0.38, time_to_expiry_secs=900)  # reset
    assert mid is None
    again = check_exit(pos, hl_price=95500, pm_yes_price=0.53, time_to_expiry_secs=900)  # count=1
    assert again is None, "Sayaç sıfırlandı, tek döngü yetmez"


def test_check_exit_small_profit_holds_to_resolution():
    """Küçük kazanç (captured < PROFIT_LOCK_MIN) → erken çıkma, resolve'a kadar tut.

    entry=0.35, fair=0.42 (küçük edge=0.07), pm=0.41 → captured=0.06 < 0.10.
    fraction=(0.41-0.35)/0.07=0.857>=0.85 olsa bile mutlak kazanç slippage'i hak etmiyor → tut.
    """
    pos = _position(action="YES", held_minutes=5)
    pos["fair_value"] = 0.42
    r1 = check_exit(pos, hl_price=95300, pm_yes_price=0.41, time_to_expiry_secs=900)
    r2 = check_exit(pos, hl_price=95300, pm_yes_price=0.41, time_to_expiry_secs=900)
    assert r1 is None and r2 is None, "Küçük kazançta erken çıkış olmamalı (slippage yer)"


def test_check_exit_thesis_reversal_now_holds():
    """thesis_invalidated KALDIRILDI: HL ters dönse bile resolve'a kadar tut.

    Eski davranış 'thesis_invalidated' döndürürdü (–$5.97 kanama). Artık None — para resolve'dan geliyor.
    """
    pos = _position(action="YES", held_minutes=5)
    result = check_exit(pos, hl_price=94800, pm_yes_price=0.34, time_to_expiry_secs=900)
    assert result is None, "thesis artık çıkış tetiklemez, resolve'a kadar tutulur"


def test_check_exit_stop_loss_after_min_hold():
    """MIN_HOLD sonrası gerçek PM zararı -%20'yi geçince → stop_loss_hit (felaket koruması)."""
    pos = _position(action="YES", held_minutes=5)  # 5dk > 60s
    # entry=0.35, stop eşiği=0.28; pm=0.27 < 0.28
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.27, time_to_expiry_secs=900)
    assert result == "stop_loss_hit"


def test_check_exit_no_stop_loss_before_min_hold():
    """İlk 60s içinde stop_loss çalışmaz — anlık ters dönüş gürültüsü filtresi."""
    pos = _position(action="YES", held_minutes=0)  # yeni açıldı, held_seconds ~0
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.27, time_to_expiry_secs=900)
    assert result is None, "60s dolmadan stop tetiklenmemeli"



def test_close_position_includes_exit_hl_price():
    """close_position exit_hl_price parametresini closed dict'e eklemeli."""
    from datetime import timedelta
    pos = {
        "position_id": "pos-hl-01", "asset": "BTC", "action": "YES",
        "slug": "btc-up-5m", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0, "seconds_remaining": 300,
        "opened_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        "status": "open", "dry_run": True,
        "exit_reason": None, "closed_at": None, "entry_hl_price": 66500.0,
    }
    closed = close_position(pos, "thesis_invalidated", pm_exit_price=0.72, exit_hl_price=66502.0)
    assert closed["exit_hl_price"] == 66502.0, \
        f"exit_hl_price={closed.get('exit_hl_price')}, beklenen 66502.0"
    assert closed["status"] == "closed"


def test_close_position_exit_hl_price_none_when_not_given():
    """exit_hl_price verilmezse None olmalı — backward compat."""
    from datetime import timedelta
    pos = {
        "position_id": "pos-hl-02", "asset": "BTC", "action": "YES",
        "slug": "btc-up-5m", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0, "seconds_remaining": 300,
        "opened_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        "status": "open", "dry_run": True,
        "exit_reason": None, "closed_at": None,
    }
    closed = close_position(pos, "market_expired")
    assert closed.get("exit_hl_price") is None
