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
    """gate_result pass=False → None döner, JSONL'da position_skipped yazar."""
    log_file = tmp_path / "log.jsonl"
    result = await execute(
        _finding(), _gate(pass_=False), _risk(),
        open_positions=[], log_file=log_file
    )
    assert result is None
    lines = log_file.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "position_skipped"
    assert record["reason"] == "gate_vetoed"


@pytest.mark.asyncio
async def test_max_open_positions_returns_none(tmp_path):
    """5 açık pozisyon varken → None döner, JSONL'da position_skipped yazar."""
    log_file = tmp_path / "log.jsonl"
    fake_positions = [{"position_id": str(i)} for i in range(5)]
    result = await execute(
        _finding(), _gate(), _risk(),
        open_positions=fake_positions, log_file=log_file
    )
    assert result is None
    lines = log_file.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "position_skipped"
    assert record["reason"] == "max_open_positions"


# ── Task 3: Happy path ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_returns_position_record(tmp_path):
    """Guard'lar geçince tam pozisyon kaydı döner ve JSONL'a position_opened yazar."""
    log_file = tmp_path / "log.jsonl"
    result = await execute(
        _finding(), _gate(), _risk(),
        open_positions=[], log_file=log_file
    )
    assert result is not None
    assert result["status"] == "open"
    for field in ["position_id", "asset", "action", "slug",
                  "pm_entry_price", "fair_value", "ref_price",
                  "position_usd", "kelly_f", "confidence_score",
                  "seconds_remaining", "opened_at", "dry_run",
                  "requires_human_approval", "exit_reason", "closed_at"]:
        assert field in result, f"Alan eksik: {field}"
    lines = log_file.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "position_opened"
    assert record["position_id"] == result["position_id"]


@pytest.mark.asyncio
async def test_no_action_entry_price(tmp_path):
    """action=NO için pm_entry_price = round(1 - best_bid, 4)."""
    finding = _finding()
    finding["action"] = "NO"
    result = await execute(
        finding, _gate(), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    assert result["pm_entry_price"] == round(1 - finding["best_bid"], 4)


@pytest.mark.asyncio
async def test_position_id_is_uuid4(tmp_path):
    """position_id geçerli bir UUID4 string'i."""
    result = await execute(
        _finding(), _gate(), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    parsed = uuid.UUID(result["position_id"])
    assert parsed.version == 4


@pytest.mark.asyncio
async def test_opened_at_is_valid_iso(tmp_path):
    """opened_at geçerli ISO 8601 UTC timestamp."""
    result = await execute(
        _finding(), _gate(), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    dt = datetime.fromisoformat(result["opened_at"])
    assert dt.tzinfo is not None


@pytest.mark.asyncio
async def test_requires_human_approval_false_below_threshold(tmp_path):
    """position_usd < HUMAN_APPROVAL_USD → requires_human_approval=False."""
    result = await execute(
        _finding(), _gate(), _risk(),  # _risk() → position_usd=25.0 < 50
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    assert result["requires_human_approval"] is False


@pytest.mark.asyncio
async def test_requires_human_approval_true_above_threshold(tmp_path):
    """position_usd > HUMAN_APPROVAL_USD → requires_human_approval=True."""
    big_risk = _risk()
    big_risk["position_usd"] = 100.0  # > HUMAN_APPROVAL_USD=50
    result = await execute(
        _finding(), _gate(), big_risk,
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    assert result["requires_human_approval"] is True


@pytest.mark.asyncio
async def test_execute_position_includes_edge(tmp_path):
    """execute() dönen position dict finding'deki edge değerini taşımalı."""
    result = await execute(
        _finding(), _gate(), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    assert "edge" in result, "position dict'te edge alanı yok"
    assert result["edge"] == _finding()["edge"]


@pytest.mark.asyncio
async def test_two_calls_produce_different_position_ids(tmp_path):
    """İki ardışık çağrı farklı position_id üretir."""
    r1 = await execute(
        _finding(), _gate(), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    r2 = await execute(
        _finding(), _gate(), _risk(),
        open_positions=[], log_file=tmp_path / "log.jsonl"
    )
    assert r1["position_id"] != r2["position_id"]
