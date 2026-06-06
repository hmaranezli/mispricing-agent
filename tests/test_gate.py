"""tests/test_gate.py — Katman 5 Gate birim testleri."""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import pytest
from council.gate import _confidence_score, _gate_decide, gate


# ── Fixture'lar ───────────────────────────────────────────────────────────────

def _finding(action="YES"):
    return {"question": "Will BTC go up?", "slug": "btc-up-1h",
            "asset": "BTC", "action": action, "edge": 0.12,
            "cur_price": 65000.0}


def _verification(fresh_seconds=400):
    return {"pass": True, "fresh_best_ask": 0.40, "fresh_best_bid": 0.38,
            "fresh_fair": 0.55, "fresh_edge": 0.15, "fresh_seconds": fresh_seconds,
            "fresh_cur_price": 65000.0, "hl_drift_pct": 0.01, "pm_drift": 0.005,
            "reason": "ok", "halt": False}


def _redteam(fee_adj_edge=0.12, liquidity_usd=3000.0, spread=0.02):
    return {"pass": True, "vetoes": [], "warnings": [],
            "fee_adj_edge": fee_adj_edge, "taker_fee": 0.02,
            "spread": spread, "liquidity_usd": liquidity_usd}


def _risk(position_usd=42.0, requires_human_approval=False):
    return {"pass": True, "position_usd": position_usd, "kelly_f": 0.2,
            "kelly_fraction_applied": 0.25,
            "requires_human_approval": requires_human_approval,
            "halt": False, "reason": ""}


# ── Task 1: _confidence_score ─────────────────────────────────────────────────

def test_confidence_score_7pct_edge_full_points():
    """EDGE_MAX=0.06 sonrası %7 edge → edge bileşeni tam 40 puan → toplam ≥95."""
    from council.gate import EDGE_MAX
    assert EDGE_MAX == 0.06, f"EDGE_MAX 0.06 olmalı, şu an: {EDGE_MAX}"
    score = _confidence_score(_redteam(fee_adj_edge=0.07, liquidity_usd=5000.0, spread=0.005), _verification(600))
    assert score >= 95, f"%7 edge + max diğerleri → ≥95, got {score}"


def test_confidence_score_typical_good():
    # edge=0.12, liq=$3000, secs=400, spread=0.02 → ≥ 75
    score = _confidence_score(_redteam(0.12, 3000.0, 0.02), _verification(400))
    assert score >= 75


def test_confidence_score_weak():
    # edge=0.09, liq=$800, secs=150, spread=0.035 → < 75
    score = _confidence_score(_redteam(0.09, 800.0, 0.035), _verification(150))
    assert score < 75


def test_confidence_score_perfect():
    # Tüm bileşenler max → ≥ 95
    score = _confidence_score(_redteam(0.20, 5000.0, 0.005), _verification(600))
    assert score >= 95


def test_confidence_score_clamped():
    # Aşırı değerler → 100'ü geçmez
    score = _confidence_score(_redteam(1.0, 999999.0, 0.0), _verification(9999))
    assert score <= 100.0


# ── Task 2: _gate_decide ──────────────────────────────────────────────────────

def test_gate_decide_required_fields():
    r = _gate_decide(_finding(), _verification(), _redteam(), _risk())
    assert "pass" in r
    assert "confidence_score" in r
    assert "action_taken" in r
    assert "reason" in r


def test_gate_decide_vetoes_below_threshold():
    # Zayıf sinyal → skor < 75 → veto
    r = _gate_decide(
        _finding(), _verification(150),
        _redteam(0.09, 800.0, 0.035), _risk()
    )
    assert r["pass"] is False
    assert r["action_taken"] == "vetoed"
    assert r["reason"] == "confidence_below_threshold"


def test_gate_decide_passes_above_threshold():
    # İyi sinyal → skor ≥ 75 → pass
    r = _gate_decide(
        _finding(), _verification(400),
        _redteam(0.12, 3000.0, 0.02), _risk()
    )
    assert r["pass"] is True
    assert r["confidence_score"] >= 75


# ── Task 3: gate() async ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gate_dry_run_logged(tmp_path, monkeypatch):
    # DRY_RUN=True, iyi sinyal → action_taken="dry_run_logged", log yazılır
    import council.gate as gm
    monkeypatch.setattr(gm, "LOG_FILE", tmp_path / "dry_run.jsonl")
    monkeypatch.setattr(config, "DRY_RUN", True)

    r = await gate(
        _finding(), _verification(400),
        _redteam(0.12, 3000.0, 0.02), _risk()
    )

    assert r["pass"] is True
    assert r["action_taken"] == "dry_run_logged"

    lines = (tmp_path / "dry_run.jsonl").read_text().strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["action_taken"] == "dry_run_logged"
    assert entry["dry_run"] is True
    assert entry["pass"] is True


@pytest.mark.asyncio
async def test_gate_vetoed_action_taken(tmp_path, monkeypatch):
    # Zayıf sinyal → veto, log yazılır
    import council.gate as gm
    monkeypatch.setattr(gm, "LOG_FILE", tmp_path / "dry_run.jsonl")
    monkeypatch.setattr(config, "DRY_RUN", True)

    r = await gate(
        _finding(), _verification(150),
        _redteam(0.09, 800.0, 0.035), _risk()
    )

    assert r["pass"] is False
    assert r["action_taken"] == "vetoed"
    entry = json.loads((tmp_path / "dry_run.jsonl").read_text().strip())
    assert entry["action_taken"] == "vetoed"
    assert entry["pass"] is False


@pytest.mark.asyncio
async def test_gate_approval_flag_dry_run_does_not_block(tmp_path, monkeypatch):
    # requires_human_approval=True + DRY_RUN=True → yine geçer (bloklamaz)
    import council.gate as gm
    monkeypatch.setattr(gm, "LOG_FILE", tmp_path / "dry_run.jsonl")
    monkeypatch.setattr(config, "DRY_RUN", True)

    r = await gate(
        _finding(), _verification(400),
        _redteam(0.12, 3000.0, 0.02),
        _risk(position_usd=200.0, requires_human_approval=True)
    )

    assert r["pass"] is True
    assert r["action_taken"] == "dry_run_logged"
    entry = json.loads((tmp_path / "dry_run.jsonl").read_text().strip())
    assert entry["requires_human_approval"] is True
    assert entry["action_taken"] == "dry_run_logged"
