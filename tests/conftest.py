"""tests/conftest.py — test izolasyonu: hiçbir unit test CANLI logs/mispricing.db okumamalı.

Faz 2c-3 Task A ile execute() artık order_intent.has_unresolved_intent(None, ...) çağırıyor;
db_path=None iken bu canonical DB_FILE'ı (logs/mispricing.db) okur. DB_FILE patch'lemeyen
execute()-çağıran testler (test_clob_executor, test_entry_air_pocket, test_shadow_4h ...) bu
yüzden canlı DB'ye dokunurdu — KABUL EDİLEMEZ.

Aşağıdaki autouse fixture YALNIZCA default-path okumalarını izole eder:
  - execution.order_intent.DB_FILE  → schema-inited, per-test tmp DB
  - execution.emergency_pause.DB_FILE → aynı tmp DB
db.logger.DB_FILE / get_connection DEĞİŞMEZ (test_db_logger gibi canlı-DB testleri etkilenmez).
Production kodu DEĞİŞMEZ; tekil testler patch.object(oi, "DB_FILE", ...) ile kendi tmp'lerine
override edebilir (with-block içinde compose olur). Canlı DB okunmadığının kesin kanıtı için
bkz. tests/test_execute_intent_wiring.py::test_execute_default_path_is_isolated_never_live.
"""
import sqlite3

import pytest

from db import schema as _schema


def _init_sync(path: str) -> None:
    """init_schema'nın senkron eşdeğeri (aiosqlite yerine sqlite3) — fixture setup için."""
    conn = sqlite3.connect(path)
    try:
        conn.executescript(_schema._SCHEMA)
        for stmt in _schema._MIGRATIONS:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError:
                pass  # idempotent: duplicate column / zaten var
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def _isolate_default_db_path(monkeypatch, tmp_path):
    """execute()/guard'ın db_path=None default'unu CANLI DB yerine per-test tmp'ye yönlendirir."""
    db = tmp_path / "isolated.db"
    _init_sync(str(db))
    import execution.order_intent as oi
    import execution.emergency_pause as ep
    monkeypatch.setattr(oi, "DB_FILE", str(db))
    monkeypatch.setattr(ep, "DB_FILE", str(db))
    yield


@pytest.fixture(autouse=True)
def _legacy_council_authority(request, monkeypatch):
    """Council decision authority is now DEFAULT-DISABLED in production (bypass — see
    docs/protocols/council_decision_authority_bypass.md). Legacy main_loop wiring/accounting tests
    were written when a council PASS routed to execute(); they validate the POST-council entry-gate
    and accounting wiring, which is now opt-in. Re-enable the flag for those tests so that coverage
    is preserved. The dedicated bypass suite (test_council_decision_authority_bypass) OPTS OUT so it
    can verify the default-safe (disabled) production behavior."""
    if request.module.__name__.endswith("test_council_decision_authority_bypass"):
        return
    import config
    monkeypatch.setattr(config, "COUNCIL_DECISION_AUTHORITY_ENABLED", True)
