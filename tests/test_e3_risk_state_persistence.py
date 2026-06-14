"""tests/test_e3_risk_state_persistence.py — E3 risk-state persistence (TDD).

E1b: risk state restart'tan sağ çıkmalı; process-memory-only YASAK. E3 bu kalıcılık sözleşmesini
pinler. Persistence yeterli state'i saklamalı (günlük risk state + active_blockers yeniden kurulabilsin)
ve eksik/bozuk/tanınmayan state'te SESSİZCE Operational'a DÜŞMEMELİ (fail-closed).

Storage sözleşmesi (GREEN bunu izleyecek; emergency_pause singleton pattern'i gibi): tek satırlı
`risk_state` tablosu, JSON `payload` kolonu, `state_key='global'`. Testler YALNIZ tmp_path sqlite
kullanır — canlı logs/mispricing.db'ye DOKUNMAZ.

İlk RED: monitor.risk_state_store YOK → ModuleNotFoundError (beklenen isimlerden biri).
"""
import sys
import os
import json
import sqlite3

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _snapshot(**over):
    """Beklenen RiskStateSnapshot alanlarını dict olarak üretir (test rahatlığı; GREEN dataclass/uyumlu)."""
    base = dict(
        trading_day_utc="2026-06-14",
        start_of_day_equity=1000.0,
        realized_pnl_today=-125.0,
        active_blockers=["daily_loss"],
        effective_mode="Exit-Only",
        updated_at_utc="2026-06-14T21:00:00Z",
        schema_version=1,
    )
    base.update(over)
    return base


def test_risk_state_snapshot_persists_across_reopen(tmp_path):
    """save sonra load (restart sim) → tüm alanlar aynı. Yalnız tmp sqlite. İlk RED: modül yok."""
    from monitor.risk_state_store import (
        RiskStateSnapshot, init_risk_state_store, save_risk_state, load_risk_state)
    dbp = str(tmp_path / "risk_state.db")
    init_risk_state_store(dbp)
    snap = RiskStateSnapshot(**_snapshot())
    save_risk_state(dbp, snap)

    loaded = load_risk_state(dbp)   # taze çağrı = restart sonrası okuma
    assert loaded.trading_day_utc == "2026-06-14"
    assert loaded.start_of_day_equity == 1000.0
    assert loaded.realized_pnl_today == -125.0
    assert sorted(loaded.active_blockers) == ["daily_loss"]
    assert loaded.effective_mode == "Exit-Only"
    assert loaded.updated_at_utc == "2026-06-14T21:00:00Z"
    assert loaded.schema_version == 1


def test_persisted_effective_mode_matches_reducer(tmp_path):
    """effective_mode reduce_risk_mode(active_blockers) ile tutarlı + restart'tan sonra korunur."""
    from monitor.risk_state import reduce_risk_mode
    from monitor.risk_state_store import (
        RiskStateSnapshot, init_risk_state_store, save_risk_state, load_risk_state)
    dbp = str(tmp_path / "risk_state.db")
    init_risk_state_store(dbp)
    blockers = ["cooldown", "daily_loss"]
    assert reduce_risk_mode(blockers) == "Exit-Only"
    save_risk_state(dbp, RiskStateSnapshot(**_snapshot(
        active_blockers=blockers, effective_mode="Exit-Only")))
    assert load_risk_state(dbp).effective_mode == "Exit-Only"


def test_corrupt_state_fails_closed(tmp_path):
    """Bozuk payload → RiskStateCorruptError; Operational'a SESSİZ düşüş YOK. Yalnız tmp DB mutasyonu."""
    from monitor.risk_state_store import (
        RiskStateSnapshot, RiskStateCorruptError,
        init_risk_state_store, save_risk_state, load_risk_state)
    dbp = str(tmp_path / "risk_state.db")
    init_risk_state_store(dbp)
    save_risk_state(dbp, RiskStateSnapshot(**_snapshot()))
    # tmp DB'de payload'ı boz (geçersiz JSON)
    conn = sqlite3.connect(dbp)
    conn.execute("UPDATE risk_state SET payload=? WHERE state_key='global'", ("{not valid json",))
    conn.commit(); conn.close()
    with pytest.raises(RiskStateCorruptError):
        load_risk_state(dbp)


def test_unknown_persisted_blocker_rejected(tmp_path):
    """Saklı active_blockers'da bilinmeyen blocker → RiskStateCorruptError/ValueError; YUTULMAZ."""
    from monitor.risk_state_store import (
        RiskStateSnapshot, RiskStateCorruptError,
        init_risk_state_store, save_risk_state, load_risk_state)
    dbp = str(tmp_path / "risk_state.db")
    init_risk_state_store(dbp)
    save_risk_state(dbp, RiskStateSnapshot(**_snapshot()))
    # tmp DB'ye bilinmeyen blocker enjekte et
    conn = sqlite3.connect(dbp)
    row = conn.execute("SELECT payload FROM risk_state WHERE state_key='global'").fetchone()
    payload = json.loads(row[0])
    payload["active_blockers"] = ["unknown_blocker"]
    conn.execute("UPDATE risk_state SET payload=? WHERE state_key='global'", (json.dumps(payload),))
    conn.commit(); conn.close()
    with pytest.raises((RiskStateCorruptError, ValueError)):
        load_risk_state(dbp)
