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
