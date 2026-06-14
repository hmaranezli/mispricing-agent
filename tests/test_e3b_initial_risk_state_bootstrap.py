"""tests/test_e3b_initial_risk_state_bootstrap.py — E3b Day-0 risk-state bootstrap (TDD).

E3 fail-closed: missing state → RiskStateCorruptError (Operational'a sessiz düşüş YOK). E3b, ilk geçerli
Operational state'in YALNIZ explicit, operatör-onaylı bir bootstrap fonksiyonuyla oluşturulmasını pinler.
Canlı balance/API'den ÇIKARILMAZ — yalnız caller-verilen değerler.

Bu UTC rollover DEĞİL, active_blockers köprüsü DEĞİL, main_loop wiring DEĞİL.

Beklenen API: initialize_day_zero_state(db_path, trading_day_utc, start_of_day_equity, updated_at_utc,
approved_by, reason) -> RiskStateSnapshot. İlk RED: fonksiyon YOK → ImportError. Yalnız tmp sqlite.
"""
import sys
import os
import json
import sqlite3

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_missing_state_requires_explicit_bootstrap(tmp_path):
    """Bootstrap ÖNCESİ: init sonrası load → RiskStateCorruptError (missing row sessizce Operational OLMAZ)."""
    from monitor.risk_state_store import (
        init_risk_state_store, load_risk_state, RiskStateCorruptError)
    dbp = str(tmp_path / "rs.db")
    init_risk_state_store(dbp)
    with pytest.raises(RiskStateCorruptError):
        load_risk_state(dbp)


def test_initialize_day_zero_state_creates_valid_operational_snapshot(tmp_path):
    """Explicit bootstrap → geçerli Operational snapshot; load aynısını döner. İlk RED: fonksiyon yok."""
    from monitor.risk_state_store import (
        init_risk_state_store, load_risk_state, initialize_day_zero_state)
    dbp = str(tmp_path / "rs.db")
    init_risk_state_store(dbp)
    snap = initialize_day_zero_state(
        dbp, trading_day_utc="2026-06-14", start_of_day_equity=1000.0,
        updated_at_utc="2026-06-14T00:00:00Z", approved_by="human:hasan", reason="day0 canary bootstrap")
    assert snap.realized_pnl_today == 0.0
    assert snap.active_blockers == []
    assert snap.effective_mode == "Operational"
    assert snap.schema_version == 1
    # Audit metadata returned snapshot'ta persist
    assert snap.bootstrap_approved_by == "human:hasan"
    assert snap.bootstrap_reason == "day0 canary bootstrap"
    loaded = load_risk_state(dbp)
    assert loaded.effective_mode == "Operational"
    assert loaded.realized_pnl_today == 0.0
    assert loaded.active_blockers == []
    assert loaded.start_of_day_equity == 1000.0
    assert loaded.trading_day_utc == "2026-06-14"
    # Audit metadata loaded snapshot'ta da persist
    assert loaded.bootstrap_approved_by == "human:hasan"
    assert loaded.bootstrap_reason == "day0 canary bootstrap"


def test_bootstrap_rejects_non_positive_equity(tmp_path):
    """start_of_day_equity <= 0 → ValueError (canlı balance çıkarımı YOK; explicit pozitif şart)."""
    from monitor.risk_state_store import init_risk_state_store, initialize_day_zero_state
    dbp = str(tmp_path / "rs.db")
    init_risk_state_store(dbp)
    with pytest.raises(ValueError):
        initialize_day_zero_state(
            dbp, trading_day_utc="2026-06-14", start_of_day_equity=0.0,
            updated_at_utc="2026-06-14T00:00:00Z", approved_by="human:hasan", reason="x")


def test_bootstrap_requires_operator_approval_fields(tmp_path):
    """Boş approved_by veya boş reason → ValueError (operatör onayı zorunlu)."""
    from monitor.risk_state_store import init_risk_state_store, initialize_day_zero_state
    dbp = str(tmp_path / "rs.db")
    init_risk_state_store(dbp)
    with pytest.raises(ValueError):
        initialize_day_zero_state(
            dbp, trading_day_utc="2026-06-14", start_of_day_equity=1000.0,
            updated_at_utc="2026-06-14T00:00:00Z", approved_by="", reason="x")
    with pytest.raises(ValueError):
        initialize_day_zero_state(
            dbp, trading_day_utc="2026-06-14", start_of_day_equity=1000.0,
            updated_at_utc="2026-06-14T00:00:00Z", approved_by="human:hasan", reason="  ")


def test_bootstrap_does_not_overwrite_existing_state(tmp_path):
    """İkinci bootstrap → ValueError; mevcut state DEĞİŞMEZ (sessiz overwrite YOK)."""
    from monitor.risk_state_store import (
        init_risk_state_store, load_risk_state, initialize_day_zero_state)
    dbp = str(tmp_path / "rs.db")
    init_risk_state_store(dbp)
    initialize_day_zero_state(
        dbp, trading_day_utc="2026-06-14", start_of_day_equity=1000.0,
        updated_at_utc="2026-06-14T00:00:00Z", approved_by="human:hasan", reason="first")
    before = load_risk_state(dbp)
    with pytest.raises(ValueError):
        initialize_day_zero_state(
            dbp, trading_day_utc="2026-06-15", start_of_day_equity=2000.0,
            updated_at_utc="2026-06-15T00:00:00Z", approved_by="human:hasan", reason="second")
    after = load_risk_state(dbp)
    assert after.trading_day_utc == before.trading_day_utc == "2026-06-14"
    assert after.start_of_day_equity == before.start_of_day_equity == 1000.0


def test_bootstrap_does_not_overwrite_corrupt_state(tmp_path):
    """Mevcut satır BOZUKSA bootstrap üzerine YAZMAZ → RiskStateCorruptError/ValueError; her
    RiskStateCorruptError bootstrap-izinli sayılmaz. Bozuk payload tmp DB'de korunur."""
    from monitor.risk_state_store import (
        init_risk_state_store, initialize_day_zero_state,
        load_risk_state, RiskStateCorruptError)
    dbp = str(tmp_path / "rs.db")
    init_risk_state_store(dbp)
    # Singleton satırı bozuk payload ile doldur (geçersiz JSON)
    conn = sqlite3.connect(dbp)
    conn.execute("INSERT INTO risk_state (state_key, payload) VALUES ('global', ?)", ("{corrupt",))
    conn.commit(); conn.close()
    with pytest.raises((RiskStateCorruptError, ValueError)):
        initialize_day_zero_state(
            dbp, trading_day_utc="2026-06-14", start_of_day_equity=1000.0,
            updated_at_utc="2026-06-14T00:00:00Z", approved_by="human:hasan", reason="x")
    # Bozuk payload üzerine yazılmadı → hâlâ corrupt
    raw = sqlite3.connect(dbp).execute(
        "SELECT payload FROM risk_state WHERE state_key='global'").fetchone()[0]
    assert raw == "{corrupt", f"bootstrap bozuk state'i overwrite ETMEMELİ: {raw!r}"
