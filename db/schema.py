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
    # HL fiyat kolonlari:
    "ALTER TABLE positions ADD COLUMN entry_hl_price REAL",
    "ALTER TABLE positions ADD COLUMN exit_hl_price REAL",
    # Faz 1: MAE/MFE + stop slippage + sell timing telemetrisi
    "ALTER TABLE positions ADD COLUMN mae_pct REAL",
    "ALTER TABLE positions ADD COLUMN mfe_pct REAL",
    "ALTER TABLE positions ADD COLUMN mae_px REAL",
    "ALTER TABLE positions ADD COLUMN mfe_px REAL",
    "ALTER TABLE positions ADD COLUMN mae_ts TEXT",
    "ALTER TABLE positions ADD COLUMN mfe_ts TEXT",
    "ALTER TABLE positions ADD COLUMN mae_data_quality TEXT",
    "ALTER TABLE positions ADD COLUMN price_source TEXT",
    "ALTER TABLE positions ADD COLUMN sl_trigger_px REAL",
    "ALTER TABLE positions ADD COLUMN sl_trigger_pct REAL",
    "ALTER TABLE positions ADD COLUMN first_trigger_ts TEXT",
    "ALTER TABLE positions ADD COLUMN exit_bid_at_trigger REAL",
    "ALTER TABLE positions ADD COLUMN exit_ask_at_trigger REAL",
    "ALTER TABLE positions ADD COLUMN spread_at_trigger REAL",
    "ALTER TABLE positions ADD COLUMN book_depth_at_trigger REAL",
    "ALTER TABLE positions ADD COLUMN sell_attempt_count INTEGER",
    "ALTER TABLE positions ADD COLUMN sell_unmatched_count INTEGER",
    "ALTER TABLE positions ADD COLUMN fill_ts TEXT",
    "ALTER TABLE positions ADD COLUMN sl_fill_px REAL",
    "ALTER TABLE positions ADD COLUMN sl_fill_pct REAL",
    "ALTER TABLE positions ADD COLUMN trigger_fill_gap_pct REAL",
    "ALTER TABLE positions ADD COLUMN trigger_to_fill_secs REAL",
    # Faz 2.2: Partial fill telemetri
    "ALTER TABLE positions ADD COLUMN partial_fill_count INTEGER DEFAULT 0",
    "ALTER TABLE positions ADD COLUMN partial_fill_shares REAL",
    "ALTER TABLE positions ADD COLUMN partial_realized_usdc REAL",
]


async def init_schema(conn) -> None:
    await conn.executescript(_SCHEMA)
    for sql in _MIGRATIONS:
        try:
            await conn.execute(sql)
        except Exception:
            pass  # sütun zaten varsa hata verir, yok say
    await conn.commit()
