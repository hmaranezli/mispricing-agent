"""tests/test_e3c_utc_risk_state_rollover.py — E3c UTC risk-state rollover (TDD).

E1b §8: UTC 00:00 yalnız GÜNLÜK sayaçları sıfırlar (Halted/kill-switch/manual-review temizlemez),
sonra mod active_blockers'tan yeniden hesaplanır. E3c bunu SAF, deterministik bir fonksiyonla pinler:
sistem clock OKUMAZ; zaman + yeni equity caller'dan ENJEKTE edilir; save/load YOK (snapshot→snapshot).

Beklenen API: rollover_risk_state_if_new_day(snapshot, current_trading_day_utc, new_start_of_day_equity,
updated_at_utc) -> RiskStateSnapshot. İlk RED: fonksiyon YOK → ImportError. Canlı API/clock/DB yok.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _snap(active_blockers, effective_mode, day="2026-06-14", pnl=-50.0, equity=1000.0):
    from monitor.risk_state_store import RiskStateSnapshot
    return RiskStateSnapshot(
        trading_day_utc=day, start_of_day_equity=equity, realized_pnl_today=pnl,
        active_blockers=list(active_blockers), effective_mode=effective_mode,
        updated_at_utc=f"{day}T12:00:00Z", schema_version=1,
        bootstrap_approved_by="human:hasan", bootstrap_reason="day0")


def test_same_day_returns_unchanged_snapshot():
    """current_day == snapshot.day → günlük reset YOK; pnl/blockers/mode değişmez."""
    from monitor.risk_state_store import rollover_risk_state_if_new_day
    snap = _snap(["daily_loss"], "Exit-Only", day="2026-06-14", pnl=-50.0)
    out = rollover_risk_state_if_new_day(snap, "2026-06-14", 2000.0, "2026-06-14T13:00:00Z")
    assert out.realized_pnl_today == -50.0
    assert out.active_blockers == ["daily_loss"]
    assert out.effective_mode == "Exit-Only"
    assert out.trading_day_utc == "2026-06-14"


def test_new_day_resets_daily_loss_but_preserves_manual_review():
    """Yeni gün → daily_loss kaldırılır, manual_review korunur, mode Halted; pnl=0, equity güncel."""
    from monitor.risk_state_store import rollover_risk_state_if_new_day
    snap = _snap(["daily_loss", "manual_review"], "Halted")
    out = rollover_risk_state_if_new_day(snap, "2026-06-15", 1500.0, "2026-06-15T00:00:00Z")
    assert "daily_loss" not in out.active_blockers
    assert "manual_review" in out.active_blockers
    assert out.effective_mode == "Halted"
    assert out.realized_pnl_today == 0.0
    assert out.start_of_day_equity == 1500.0
    assert out.trading_day_utc == "2026-06-15"


def test_new_day_resets_daily_loss_to_operational_when_no_other_blockers():
    """Yeni gün, tek blocker daily_loss → [] ve mode Operational."""
    from monitor.risk_state_store import rollover_risk_state_if_new_day
    snap = _snap(["daily_loss"], "Exit-Only")
    out = rollover_risk_state_if_new_day(snap, "2026-06-15", 1000.0, "2026-06-15T00:00:00Z")
    assert out.active_blockers == []
    assert out.effective_mode == "Operational"


def test_new_day_preserves_kill_switch():
    """Yeni gün → daily_loss kaldırılır, kill_switch korunur, mode Kill-Switch."""
    from monitor.risk_state_store import rollover_risk_state_if_new_day
    snap = _snap(["daily_loss", "kill_switch"], "Kill-Switch")
    out = rollover_risk_state_if_new_day(snap, "2026-06-15", 1000.0, "2026-06-15T00:00:00Z")
    assert "daily_loss" not in out.active_blockers
    assert "kill_switch" in out.active_blockers
    assert out.effective_mode == "Kill-Switch"


def test_rollover_rejects_backwards_day():
    """current_day < snapshot.day → ValueError."""
    from monitor.risk_state_store import rollover_risk_state_if_new_day
    snap = _snap(["daily_loss"], "Exit-Only", day="2026-06-14")
    with pytest.raises(ValueError):
        rollover_risk_state_if_new_day(snap, "2026-06-13", 1000.0, "2026-06-13T00:00:00Z")


def test_rollover_rejects_non_positive_new_equity():
    """new_start_of_day_equity <= 0 → ValueError."""
    from monitor.risk_state_store import rollover_risk_state_if_new_day
    snap = _snap(["daily_loss"], "Exit-Only")
    with pytest.raises(ValueError):
        rollover_risk_state_if_new_day(snap, "2026-06-15", 0.0, "2026-06-15T00:00:00Z")


def test_rollover_preserves_bootstrap_audit_metadata():
    """Rollover sonrası bootstrap audit alanları korunur."""
    from monitor.risk_state_store import rollover_risk_state_if_new_day
    snap = _snap(["daily_loss"], "Exit-Only")
    out = rollover_risk_state_if_new_day(snap, "2026-06-15", 1000.0, "2026-06-15T00:00:00Z")
    assert out.bootstrap_approved_by == "human:hasan"
    assert out.bootstrap_reason == "day0"
