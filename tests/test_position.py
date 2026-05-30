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
