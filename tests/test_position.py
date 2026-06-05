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


# ── Task 3: check_exit — thesis + kâr hedefi ─────────────────────────────────

def test_check_exit_thesis_invalidated_yes():
    """YES: HL ref'in altına düşünce fair_yes < 0.48 → 'thesis_invalidated'."""
    # fair_yes(94800, 95000, 900, 'BTC') ≈ 0.31 < 0.48 → thesis broken
    pos = _position(action="YES", held_minutes=5)
    result = check_exit(pos, hl_price=94800, pm_yes_price=0.35,
                        time_to_expiry_secs=900)
    assert result == "thesis_invalidated"


def test_check_exit_thesis_invalidated_no():
    """NO: HL ref'in üstüne çıkınca fair_yes > 0.52 → 'thesis_invalidated'.

    fair_yes(95200, 95000, 900, 'BTC') ≈ 0.69 > 0.52 → thesis broken (HL bullish'e döndü)
    pm_yes_price=0.60 → NO değer=0.40, kâr henüz hedefte değil (0.22 < 0.85)
    """
    pos = _position(action="NO", held_minutes=5)
    result = check_exit(pos, hl_price=95200, pm_yes_price=0.60,
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


def test_check_exit_no_holds_when_hl_at_ref():
    """NO: HL ref fiyatında (flat) → thesis BOZULMAZ, pozisyon tutulur.

    Eski bug: NO_entry=0.64 → threshold=1-0.64-0.02=0.34, fair_yes(ref,ref)=0.50 > 0.34 → anında ateşleniyordu.
    Yeni fix: threshold=0.52, fair_yes(ref,ref)=0.50 < 0.52 → holds ✓
    """
    pos = _position(action="NO", held_minutes=1)
    # HL ref fiyatında (p_now == p_ref → fair_yes = 0.50)
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.60,
                        time_to_expiry_secs=900)
    assert result is None, f"HL ref'te flat → thesis bozulmamalı, sonuç: {result}"



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
