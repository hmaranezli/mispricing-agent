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
    ref_price        REAL,
    edge             REAL,
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


_MIGRATIONS = [
    "ALTER TABLE positions ADD COLUMN ref_price REAL",
    "ALTER TABLE positions ADD COLUMN edge REAL",
    "ALTER TABLE positions ADD COLUMN realized_pnl REAL",
    # CLOB API kolonları:
    "ALTER TABLE positions ADD COLUMN shares REAL",
    "ALTER TABLE positions ADD COLUMN order_id TEXT",
    "ALTER TABLE positions ADD COLUMN yes_token_id TEXT",
    "ALTER TABLE positions ADD COLUMN no_token_id TEXT",
    # Sira numarasi:
    "ALTER TABLE positions ADD COLUMN seq_no INTEGER",
]


async def init_schema(conn) -> None:
    await conn.executescript(_SCHEMA)
    for sql in _MIGRATIONS:
        try:
            await conn.execute(sql)
        except Exception:
            pass  # sütun zaten varsa hata verir, yok say
    await conn.commit()
