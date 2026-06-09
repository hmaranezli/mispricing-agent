"""db/schema.py — SQLite şeması ve başlatma."""

_SCHEMA = """
CREATE TABLE IF NOT EXISTS shadow_candidates (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                TEXT NOT NULL,
    slug              TEXT NOT NULL,
    asset             TEXT NOT NULL,
    action            TEXT NOT NULL,
    fair_value        REAL,
    best_ask          REAL,
    edge              REAL,
    passed            INTEGER NOT NULL,
    veto_layer        TEXT,
    veto_reason       TEXT,
    dry_run           INTEGER NOT NULL DEFAULT 1,
    confidence_score  REAL,
    kelly_f           REAL,
    seconds_remaining REAL
);

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

CREATE TABLE IF NOT EXISTS entry_air_pocket_events (
    id                                   INTEGER PRIMARY KEY AUTOINCREMENT,
    slug                                 TEXT,
    asset                                TEXT,
    action                               TEXT,
    market_id                            TEXT,
    token_id                             TEXT,
    event_ts                             TEXT,
    council_pass_ts                      TEXT,
    order_submit_ts                      TEXT,
    error_ts                             TEXT,
    council_to_submit_ms                 REAL,
    submit_to_error_ms                   REAL,
    fair                                 REAL,
    expected_ask                         REAL,
    original_worst_price                 REAL,
    original_fee_adj                     REAL,
    min_edge                             REAL,
    reported_liquidity                   REAL,
    top_of_book_size                     REAL,
    book_levels_used                     INTEGER,
    book_source                          TEXT,
    book_age_ms                          REAL,
    order_id                             TEXT,
    error_type                           TEXT,
    position_created                     INTEGER DEFAULT 0,
    fresh_ask_after_fail                 REAL,
    fresh_no_ask_after_fail              REAL,
    fresh_book_age_ms                    REAL,
    fresh_fee_adj_after_fail             REAL,
    fresh_price_delta_cents              REAL,
    fresh_edge_still_passes_min_edge     INTEGER,
    would_retry_passed_shadow            INTEGER,
    delayed_ask_after_fail               REAL,
    delayed_no_ask_after_fail            REAL,
    delayed_book_age_ms                  REAL,
    delayed_fee_adj_after_fail           REAL,
    delayed_price_delta_cents            REAL,
    delayed_edge_still_passes_min_edge   INTEGER,
    delayed_would_retry_passed_shadow    INTEGER
);

CREATE TABLE IF NOT EXISTS air_pocket_shadow (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    seq_no                    INTEGER,
    position_id               TEXT,
    slug                      TEXT,
    asset                     TEXT,
    action                    TEXT,
    current_exit_price        REAL,
    current_exit_result       TEXT,
    guarded_exit_decision     TEXT,
    decision_reason           TEXT,
    override_reason           TEXT,
    depth_ratio               REAL,
    pred_gap                  REAL,
    actual_trigger_fill_gap   REAL,
    post_wait_bid             REAL,
    post_wait_depth           REAL,
    post_wait_error           TEXT,
    would_have_improved_fill  INTEGER,
    false_positive_guard      INTEGER,
    shadow_compute_ms         REAL,
    live_exit_delay_ms        REAL,
    error                     TEXT,
    created_at                TEXT
);

CREATE TABLE IF NOT EXISTS shadow_positions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id              TEXT UNIQUE,
    source_event_id       TEXT,
    ts_open               TEXT,
    slug                  TEXT,
    asset                 TEXT,
    action                TEXT,
    entry_price_estimated REAL,
    entry_method          TEXT,
    position_usd_paper    REAL,
    shares_paper          REAL,
    fair_value            REAL,
    edge                  REAL,
    ref_price             REAL,
    entry_hl_price        REAL,
    confidence_score      REAL,
    status                TEXT DEFAULT 'open',
    ts_close              TEXT,
    close_reason          TEXT,
    pm_exit_estimated     REAL,
    resolve_exit          REAL,
    mae_pct               REAL,
    mfe_pct               REAL,
    mfe_peak              REAL,
    cohort                TEXT DEFAULT 'paper',
    confidence_level      TEXT DEFAULT 'low',
    data_quality          TEXT,
    is_paper              INTEGER DEFAULT 1,
    dedupe_reason         TEXT,
    edge_bucket           TEXT,
    fee_adj_edge          REAL,
    depth_walk_estimated_fill        REAL,
    estimated_slippage_pct           REAL,
    net_ev_after_estimated_slippage  REAL,
    paper_viability       TEXT,
    yes_fair              REAL,
    no_fair               REAL,
    action_fair           REAL,
    entry_source          TEXT,
    snapshot_age_ms       REAL,
    seconds_remaining_at_signal  REAL,
    seconds_remaining_at_open    REAL,
    late_entry_flag       INTEGER,
    collapse_timing_flag  INTEGER,
    signal_timestamp_ms   INTEGER,
    created_at            TEXT
);

CREATE TABLE IF NOT EXISTS shadow_stop_events (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id             TEXT,
    ts                   TEXT,
    slug                 TEXT,
    asset                TEXT,
    action               TEXT,
    seconds_remaining    REAL,
    pm_price             REAL,
    drawdown_pct         REAL,
    hl_drift_pct         REAL,
    mae_pct              REAL,
    mfe_pct              REAL,
    mfe_peak             REAL,
    current_action       TEXT,
    conservative_action  TEXT,
    balanced_action      TEXT,
    mfe_breakeven_action TEXT,
    decision_reason      TEXT,
    paper_compute_ms     REAL,
    created_at           TEXT
);

CREATE TABLE IF NOT EXISTS shadow_model_pnl (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id          TEXT,
    model             TEXT,
    would_exit_price  REAL,
    would_exit_reason TEXT,
    would_exit_ts     TEXT,
    would_pnl         REAL,
    resolve_exit      REAL,
    cohort            TEXT DEFAULT 'paper',
    created_at        TEXT
);

CREATE TABLE IF NOT EXISTS paper_entry_events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id         TEXT,
    ts               TEXT,
    slug             TEXT,
    asset            TEXT,
    action           TEXT,
    best_ask         REAL,
    depth_walk_price REAL,
    ask_buffer_price REAL,
    chosen_price     REAL,
    chosen_method    TEXT,
    book_levels      INTEGER,
    created_at       TEXT
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
    # Faz 3: Entry execution telemetri
    "ALTER TABLE positions ADD COLUMN ask_at_decision REAL",
    "ALTER TABLE positions ADD COLUMN slippage_pct REAL",
    # Faz 3: Exit execution telemetri
    "ALTER TABLE positions ADD COLUMN sell_limit_price REAL",
    "ALTER TABLE positions ADD COLUMN first_exit_decision_ts TEXT",
    # Faz 4A-0: Shadow Mode entry depth telemetri (fire-and-forget, trade'i bloklamaz)
    "ALTER TABLE positions ADD COLUMN entry_top_book_size REAL",
    "ALTER TABLE positions ADD COLUMN entry_depth_for_size REAL",
    "ALTER TABLE positions ADD COLUMN entry_est_exit_price REAL",
    "ALTER TABLE positions ADD COLUMN entry_depth_slippage_pct REAL",
    "ALTER TABLE positions ADD COLUMN entry_book_levels_used INTEGER",
    # 4h shadow universe + fee telemetri
    "ALTER TABLE shadow_candidates ADD COLUMN timeframe TEXT",
    "ALTER TABLE shadow_candidates ADD COLUMN trade_enabled INTEGER DEFAULT 1",
    "ALTER TABLE shadow_candidates ADD COLUMN fee_adj_edge REAL",
    "ALTER TABLE shadow_candidates ADD COLUMN liquidity_usd REAL",
    "ALTER TABLE shadow_candidates ADD COLUMN spread REAL",
    # Edge bucket shadow experiment — paper cohort genişletmesi
    "ALTER TABLE shadow_positions ADD COLUMN edge_bucket TEXT",
    "ALTER TABLE shadow_positions ADD COLUMN fee_adj_edge REAL",
    "ALTER TABLE shadow_positions ADD COLUMN depth_walk_estimated_fill REAL",
    "ALTER TABLE shadow_positions ADD COLUMN estimated_slippage_pct REAL",
    "ALTER TABLE shadow_positions ADD COLUMN net_ev_after_estimated_slippage REAL",
    "ALTER TABLE shadow_positions ADD COLUMN paper_viability TEXT",
    # NO baseline + temporal snapshot handoff
    "ALTER TABLE shadow_positions ADD COLUMN yes_fair REAL",
    "ALTER TABLE shadow_positions ADD COLUMN no_fair REAL",
    "ALTER TABLE shadow_positions ADD COLUMN action_fair REAL",
    "ALTER TABLE shadow_positions ADD COLUMN entry_source TEXT",
    "ALTER TABLE shadow_positions ADD COLUMN snapshot_age_ms REAL",
    "ALTER TABLE shadow_positions ADD COLUMN seconds_remaining_at_signal REAL",
    "ALTER TABLE shadow_positions ADD COLUMN seconds_remaining_at_open REAL",
    "ALTER TABLE shadow_positions ADD COLUMN late_entry_flag INTEGER",
    "ALTER TABLE shadow_positions ADD COLUMN collapse_timing_flag INTEGER",
    "ALTER TABLE shadow_positions ADD COLUMN signal_timestamp_ms INTEGER",
]


async def init_schema(conn) -> None:
    await conn.executescript(_SCHEMA)
    for sql in _MIGRATIONS:
        try:
            await conn.execute(sql)
        except Exception:
            pass  # sütun zaten varsa hata verir, yok say
    await conn.commit()
