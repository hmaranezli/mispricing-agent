"""monitor/risk_sync.py — E9a risk-state runtime signal sync (write-path orchestrator).

Runtime risk sinyallerini persist edilmiş RiskStateSnapshot'a çevirir. SAF orchestrator: clock/DB-PnL/
canlı-KILL/emergency-pause OKUMAZ (hepsi enjekte); main_loop IMPORT ETMEZ; bootstrap YAPMAZ
(initialize_day_zero_state çağırmaz); snapshot yok/bozuk → RiskStateCorruptError propagate (overwrite yok).

Akış: load → (yeni gün ise rollover) → daily_loss_halt(snapshot.start_of_day_equity, realized_pnl_today)
[denominator-lock] → build_active_blockers → reduce_risk_mode → YALNIZ değiştiyse save (DB churn yok).
"""
from monitor.risk_state_store import (
    load_risk_state, save_risk_state, rollover_risk_state_if_new_day, RiskStateSnapshot)
from monitor.risk_state import build_active_blockers, reduce_risk_mode
from monitor.circuit_breaker import daily_loss_halt

# Save'i tetikleyen alanlar (updated_at_utc TEK BAŞINA write tetiklemez).
_WRITE_TRIGGER_FIELDS = (
    "active_blockers", "effective_mode", "realized_pnl_today",
    "start_of_day_equity", "trading_day_utc",
)


def _trigger_tuple(snap: RiskStateSnapshot):
    return (list(snap.active_blockers), snap.effective_mode, snap.realized_pnl_today,
            snap.start_of_day_equity, snap.trading_day_utc)


def sync_risk_state_from_runtime_signals(
    db_path, *, current_trading_day_utc, updated_at_utc, current_equity, realized_pnl_today,
    circuit_breaker_status, kill_switch_active, manual_review_required=False,
) -> RiskStateSnapshot:
    """Runtime sinyallerden risk-state snapshot'ı senkronize et. Yalnız değiştiyse persist eder.

    Snapshot yok/bozuk → load_risk_state RiskStateCorruptError fırlatır (propagate; bootstrap/overwrite YOK).
    Yeni gün → rollover (start_of_day_equity=current_equity, daily counters reset). daily_loss denominator
    = base.start_of_day_equity (current_equity DEĞİL — same-day kilidi). active_blockers/effective_mode
    runtime sinyallerden yeniden hesaplanır (kill_switch/manual_review canlı sinyaldir; caller geçer).
    """
    loaded = load_risk_state(db_path)   # missing/corrupt → RiskStateCorruptError (propagate)

    # Yeni gün → rollover (saf snapshot→snapshot; günlük sayaç reset, yapısal blocker korunur).
    if current_trading_day_utc > loaded.trading_day_utc:
        base = rollover_risk_state_if_new_day(
            loaded, current_trading_day_utc, current_equity, updated_at_utc)
    else:
        base = loaded

    # Denominator-lock: daily_loss eşiği base.start_of_day_equity üzerinden (current_equity değil).
    daily_loss_status = daily_loss_halt(base.start_of_day_equity, realized_pnl_today)
    active_blockers = build_active_blockers(
        daily_loss_status=daily_loss_status,
        circuit_breaker_status=circuit_breaker_status,
        kill_switch_active=kill_switch_active,
        manual_review_required=manual_review_required,
    )
    effective_mode = reduce_risk_mode(active_blockers)

    new_snap = RiskStateSnapshot(
        trading_day_utc=current_trading_day_utc,
        start_of_day_equity=base.start_of_day_equity,
        realized_pnl_today=realized_pnl_today,
        active_blockers=active_blockers,
        effective_mode=effective_mode,
        updated_at_utc=updated_at_utc,
        schema_version=base.schema_version,
        bootstrap_approved_by=base.bootstrap_approved_by,
        bootstrap_reason=base.bootstrap_reason,
    )

    # Yalnız trigger alanları LOADED'a göre değiştiyse yaz (updated_at_utc tek başına tetiklemez).
    if _trigger_tuple(new_snap) == _trigger_tuple(loaded):
        return loaded
    save_risk_state(db_path, new_snap)
    return new_snap
