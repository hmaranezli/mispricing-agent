"""tests/test_e9a_risk_state_sync.py — E9a risk-state runtime signal sync helper (TDD).

E9 envanteri: risk-state WRITE-PATH yok (E6 yalnız OKUYOR). Bu helper runtime risk sinyallerini
(daily_loss_halt(realized_pnl_today, start_of_day_equity) + circuit_breaker_status + kill_switch +
manual_review) persist edilmiş RiskStateSnapshot'a çevirir. main_loop wiring AYRI (E9b).

Beklenen API:
    from monitor.risk_sync import sync_risk_state_from_runtime_signals
    sync_risk_state_from_runtime_signals(db_path, *, current_trading_day_utc, updated_at_utc,
        current_equity, realized_pnl_today, circuit_breaker_status, kill_switch_active,
        manual_review_required=False) -> RiskStateSnapshot

SAF orchestrator: clock/DB-PnL/canlı KILL/emergency-pause OKUMAZ (hepsi enjekte). Bootstrap YAPMAZ
(initialize_day_zero_state çağırmaz); snapshot yoksa/bozuksa → RiskStateCorruptError (fail-closed,
overwrite yok). "Yalnız değiştiyse yaz" (E9b'de churn). config.DAILY_LOSS_LIMIT=0.35 boundary.

İlk RED: monitor.risk_sync YOK → ImportError. Yalnız tmp sqlite; canlı API/DB/order yok.
"""
import sys
import os
import json
import sqlite3

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor.risk_state_store import (
    init_risk_state_store, save_risk_state, load_risk_state,
    initialize_day_zero_state, RiskStateSnapshot, RiskStateCorruptError)


def _bootstrap_operational(tmp_path, day="2026-06-15", equity=1000.0):
    dbp = str(tmp_path / "rs.db")
    init_risk_state_store(dbp)
    initialize_day_zero_state(
        dbp, trading_day_utc=day, start_of_day_equity=equity,
        updated_at_utc=f"{day}T00:00:00Z", approved_by="human:hasan", reason="e9a test")
    return dbp


def test_same_day_daily_loss_persisted(tmp_path):
    """Operational snapshot + aynı gün realized_pnl_today=-350 (start_of_day_equity=1000, 0.35 eşik) →
    active_blockers=["daily_loss"], effective_mode="Exit-Only", realized_pnl_today persist + load görür."""
    from monitor.risk_sync import sync_risk_state_from_runtime_signals
    dbp = _bootstrap_operational(tmp_path, equity=1000.0)
    out = sync_risk_state_from_runtime_signals(
        dbp, current_trading_day_utc="2026-06-15", updated_at_utc="2026-06-15T12:00:00Z",
        current_equity=1000.0, realized_pnl_today=-350.0,
        circuit_breaker_status=None, kill_switch_active=False)
    assert out.active_blockers == ["daily_loss"]
    assert out.effective_mode == "Exit-Only"
    assert out.realized_pnl_today == -350.0
    loaded = load_risk_state(dbp)
    assert loaded.effective_mode == "Exit-Only"
    assert loaded.active_blockers == ["daily_loss"]
    assert loaded.realized_pnl_today == -350.0


def test_denominator_lock_uses_snapshot_start_of_day_equity(tmp_path):
    """Payda = snapshot.start_of_day_equity (1000), current_equity (2000) DEĞİL → -350 yine daily_loss
    tetikler (350/1000=0.35≥0.35). current_equity payda olsaydı 350/2000=0.175<0.35 → tetiklemezdi."""
    from monitor.risk_sync import sync_risk_state_from_runtime_signals
    dbp = _bootstrap_operational(tmp_path, equity=1000.0)
    out = sync_risk_state_from_runtime_signals(
        dbp, current_trading_day_utc="2026-06-15", updated_at_utc="2026-06-15T12:00:00Z",
        current_equity=2000.0, realized_pnl_today=-350.0,
        circuit_breaker_status=None, kill_switch_active=False)
    assert out.effective_mode == "Exit-Only"
    assert "daily_loss" in out.active_blockers


def test_metric_only_update_persists_pnl_without_mode_change(tmp_path):
    """active_blockers/mode Operational kalsa bile realized_pnl_today 0→+10 değişimi SAVE edilir
    (PnL metriği stale kalmaz)."""
    from monitor.risk_sync import sync_risk_state_from_runtime_signals
    dbp = _bootstrap_operational(tmp_path, equity=1000.0)
    out = sync_risk_state_from_runtime_signals(
        dbp, current_trading_day_utc="2026-06-15", updated_at_utc="2026-06-15T12:00:00Z",
        current_equity=1000.0, realized_pnl_today=10.0,
        circuit_breaker_status=None, kill_switch_active=False)
    assert out.active_blockers == []
    assert out.effective_mode == "Operational"
    assert load_risk_state(dbp).realized_pnl_today == 10.0


def test_circuit_breaker_status_mapping(tmp_path):
    """soft_stop→["cooldown"]/"Cooldown"; hard_stop→["halted"]/"Halted"."""
    from monitor.risk_sync import sync_risk_state_from_runtime_signals
    dbp = _bootstrap_operational(tmp_path, equity=1000.0)
    soft = sync_risk_state_from_runtime_signals(
        dbp, current_trading_day_utc="2026-06-15", updated_at_utc="2026-06-15T12:00:00Z",
        current_equity=1000.0, realized_pnl_today=0.0,
        circuit_breaker_status="soft_stop", kill_switch_active=False)
    assert soft.active_blockers == ["cooldown"] and soft.effective_mode == "Cooldown"
    hard = sync_risk_state_from_runtime_signals(
        dbp, current_trading_day_utc="2026-06-15", updated_at_utc="2026-06-15T12:05:00Z",
        current_equity=1000.0, realized_pnl_today=0.0,
        circuit_breaker_status="hard_stop", kill_switch_active=False)
    assert hard.active_blockers == ["halted"] and hard.effective_mode == "Halted"


def test_kill_switch_mapping(tmp_path):
    """kill_switch_active=True → ["kill_switch"]/"Kill-Switch"."""
    from monitor.risk_sync import sync_risk_state_from_runtime_signals
    dbp = _bootstrap_operational(tmp_path, equity=1000.0)
    out = sync_risk_state_from_runtime_signals(
        dbp, current_trading_day_utc="2026-06-15", updated_at_utc="2026-06-15T12:00:00Z",
        current_equity=1000.0, realized_pnl_today=0.0,
        circuit_breaker_status=None, kill_switch_active=True)
    assert out.active_blockers == ["kill_switch"] and out.effective_mode == "Kill-Switch"


def test_no_snapshot_fails_closed_no_bootstrap(tmp_path):
    """Geçerli snapshot YOKSA sync initialize_day_zero_state ÇAĞIRMAZ → RiskStateCorruptError (fail-closed)."""
    from monitor.risk_sync import sync_risk_state_from_runtime_signals
    dbp = str(tmp_path / "rs.db")
    init_risk_state_store(dbp)   # tablo var ama satır yok
    with pytest.raises(RiskStateCorruptError):
        sync_risk_state_from_runtime_signals(
            dbp, current_trading_day_utc="2026-06-15", updated_at_utc="2026-06-15T12:00:00Z",
            current_equity=1000.0, realized_pnl_today=-350.0,
            circuit_breaker_status=None, kill_switch_active=False)


def test_corrupt_snapshot_not_overwritten(tmp_path):
    """Bozuk payload → RiskStateCorruptError; payload overwrite EDİLMEZ (tmp DB'de korunur)."""
    from monitor.risk_sync import sync_risk_state_from_runtime_signals
    dbp = _bootstrap_operational(tmp_path, equity=1000.0)
    conn = sqlite3.connect(dbp)
    conn.execute("UPDATE risk_state SET payload=? WHERE state_key='global'", ("{corrupt",))
    conn.commit(); conn.close()
    with pytest.raises(RiskStateCorruptError):
        sync_risk_state_from_runtime_signals(
            dbp, current_trading_day_utc="2026-06-15", updated_at_utc="2026-06-15T12:00:00Z",
            current_equity=1000.0, realized_pnl_today=0.0,
            circuit_breaker_status=None, kill_switch_active=False)
    raw = sqlite3.connect(dbp).execute(
        "SELECT payload FROM risk_state WHERE state_key='global'").fetchone()[0]
    assert raw == "{corrupt"


def test_new_day_rollover_clears_daily_loss_preserves_kill_switch(tmp_path):
    """Önceki gün snapshot'ı (daily_loss+kill_switch, Kill-Switch) + yeni gün → rollover: trading_day_utc
    güncellenir, start_of_day_equity=current_equity, realized_pnl_today yeni günden, daily_loss temizlenir
    (yeniden tetiklenmedikçe), kill_switch KORUNUR."""
    from monitor.risk_sync import sync_risk_state_from_runtime_signals
    dbp = str(tmp_path / "rs.db")
    init_risk_state_store(dbp)
    save_risk_state(dbp, RiskStateSnapshot(
        trading_day_utc="2026-06-14", start_of_day_equity=1000.0, realized_pnl_today=-400.0,
        active_blockers=["kill_switch", "daily_loss"], effective_mode="Kill-Switch",
        updated_at_utc="2026-06-14T20:00:00Z", schema_version=1,
        bootstrap_approved_by="human:hasan", bootstrap_reason="prior day"))
    out = sync_risk_state_from_runtime_signals(
        dbp, current_trading_day_utc="2026-06-15", updated_at_utc="2026-06-15T00:05:00Z",
        current_equity=1200.0, realized_pnl_today=0.0,
        circuit_breaker_status=None, kill_switch_active=True)
    assert out.trading_day_utc == "2026-06-15"
    assert out.start_of_day_equity == 1200.0
    assert out.realized_pnl_today == 0.0
    assert "daily_loss" not in out.active_blockers
    assert "kill_switch" in out.active_blockers
    assert out.effective_mode == "Kill-Switch"


def test_no_op_does_not_save_when_nothing_changed(tmp_path, monkeypatch):
    """Hiçbir şey değişmediyse (aynı gün, aynı equity/pnl, breaker yok) → save_risk_state ÇAĞRILMAZ
    (DB churn yok); sync değişmemiş snapshot'ı döner. save_risk_state çağrılırsa AssertionError ile yakalanır."""
    from monitor import risk_sync
    from monitor.risk_sync import sync_risk_state_from_runtime_signals
    dbp = _bootstrap_operational(tmp_path, day="2026-06-15", equity=1000.0)
    base = load_risk_state(dbp)  # bootstrap: realized_pnl_today=0.0, Operational, []

    def _no_save(*a, **k):
        raise AssertionError("save_risk_state çağrılmamalı — hiçbir şey değişmedi (no-op)")
    monkeypatch.setattr(risk_sync, "save_risk_state", _no_save, raising=False)

    out = sync_risk_state_from_runtime_signals(
        dbp, current_trading_day_utc="2026-06-15", updated_at_utc="2026-06-15T13:00:00Z",
        current_equity=base.start_of_day_equity, realized_pnl_today=base.realized_pnl_today,
        circuit_breaker_status=None, kill_switch_active=False, manual_review_required=False)
    assert out.effective_mode == "Operational"
    assert out.active_blockers == []
    assert out.realized_pnl_today == base.realized_pnl_today
