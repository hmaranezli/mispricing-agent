"""db/schema.py — SQLite şeması ve başlatma."""

_SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    slug        TEXT NOT NULL,
    asset       TEXT NOT NULL,
    action      TEXT NOT NULL,
    fair_value  REAL,
    best_ask    REAL,
    edge        REAL,
    passed      INTEGER NOT NULL,
    veto_layer  TEXT,
    veto_reason TEXT,
    dry_run     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS positions (
    position_id      TEXT PRIMARY KEY,
    ts_open          TEXT NOT NULL,
    slug             TEXT NOT NULL,
    asset            TEXT NOT NULL,
    action           TEXT NOT NULL,
    pm_entry_price   REAL,
    fair_value       REAL,
    position_usd     REAL,
    kelly_f          REAL,
    confidence_score REAL,
    status           TEXT NOT NULL DEFAULT 'open',
    ts_close         TEXT,
    pm_exit_price    REAL,
    exit_reason      TEXT,
    dry_run          INTEGER NOT NULL DEFAULT 1
);
"""


async def init_schema(conn) -> None:
    await conn.executescript(_SCHEMA)
    await conn.commit()
