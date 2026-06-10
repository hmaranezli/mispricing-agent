"""db/logger.py — Aday ve pozisyon kayıtları. conn=None → sessiz atla."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from pathlib import Path
import config

DB_FILE = Path("logs/mispricing.db")


async def get_connection(db_path: Path | None = None):
    import aiosqlite
    from db.schema import init_schema
    path = db_path or DB_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(path))
    await init_schema(conn)
    return conn


async def log_shadow_candidate(
    conn,
    finding:          dict,
    passed:           bool,
    veto_layer:       str | None = None,
    veto_reason:      str | None = None,
    confidence_score: float | None = None,
    kelly_f:          float | None = None,
    timeframe:        str | None = None,
    trade_enabled:    int = 1,
    fee_adj_edge:     float | None = None,
    liquidity_usd:    float | None = None,
    spread:           float | None = None,
) -> None:
    """Konsey kararı noktasında shadow_candidates tablosuna yazar (ayrı tablo, live P&L'e karışmaz).

    timeframe:     "5m", "15m", "4h" — None ise eski çağrılar için NULL
    trade_enabled: 0 = shadow-only (4h), 1 = canlı execution için aday (15m)
    fee_adj_edge:  redteam fee_adj hesabı
    liquidity_usd: market likiditesi
    spread:        yes+no price spread
    """
    if conn is None:
        return
    await conn.execute(
        """INSERT INTO shadow_candidates
               (ts, slug, asset, action, fair_value, best_ask, edge,
                passed, veto_layer, veto_reason, dry_run,
                confidence_score, kelly_f, seconds_remaining,
                timeframe, trade_enabled, fee_adj_edge, liquidity_usd, spread)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now(timezone.utc).isoformat(),
            finding.get("slug", ""),
            finding.get("asset", ""),
            finding.get("action", ""),
            finding.get("fair_value"),
            finding.get("best_ask"),
            finding.get("edge"),
            1 if passed else 0,
            veto_layer,
            veto_reason,
            1 if config.DRY_RUN else 0,
            confidence_score,
            kelly_f,
            finding.get("seconds_remaining"),
            timeframe,
            trade_enabled,
            fee_adj_edge,
            liquidity_usd,
            spread,
        ),
    )
    await conn.commit()


async def log_candidate(
    conn,
    finding:     dict,
    passed:      bool,
    veto_layer:  str | None = None,
    veto_reason: str | None = None,
) -> None:
    if conn is None:
        return
    await conn.execute(
        """INSERT INTO candidates
               (ts, slug, asset, action, fair_value, best_ask, edge,
                passed, veto_layer, veto_reason, dry_run)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now(timezone.utc).isoformat(),
            finding.get("slug", ""),
            finding.get("asset", ""),
            finding.get("action", ""),
            finding.get("fair_value"),
            finding.get("best_ask"),
            finding.get("edge"),
            1 if passed else 0,
            veto_layer,
            veto_reason,
            1 if config.DRY_RUN else 0,
        ),
    )
    await conn.commit()


async def log_position_open(conn, position: dict) -> None:
    if conn is None:
        return
    async with conn.execute("SELECT COALESCE(MAX(seq_no), 0) + 1 FROM positions") as cur:
        row = await cur.fetchone()
    seq_no = row[0] if row else 1
    position["seq_no"] = seq_no
    await conn.execute(
        """INSERT OR IGNORE INTO positions
               (position_id, ts_open, slug, asset, action, pm_entry_price,
                fair_value, ref_price, edge, position_usd, kelly_f,
                confidence_score, status, dry_run,
                shares, order_id, yes_token_id, no_token_id, seq_no,
                entry_hl_price, ask_at_decision, slippage_pct, order_intent_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            position["position_id"],
            position.get("opened_at", datetime.now(timezone.utc).isoformat()),
            position.get("slug", ""),
            position.get("asset", ""),
            position.get("action", ""),
            position.get("pm_entry_price"),
            position.get("fair_value"),
            position.get("ref_price"),
            position.get("edge"),
            position.get("position_usd"),
            position.get("kelly_f"),
            position.get("confidence_score"),
            1 if config.DRY_RUN else 0,
            position.get("shares"),
            position.get("order_id"),
            position.get("yes_token_id"),
            position.get("no_token_id"),
            seq_no,
            position.get("entry_hl_price"),
            position.get("ask_at_decision"),
            position.get("slippage_pct"),
            position.get("order_intent_id"),
        ),
    )
    await conn.commit()


async def log_position_close(conn, position: dict) -> None:
    if conn is None:
        return
    entry   = position.get("pm_entry_price")
    exit_p  = position.get("pm_exit_price")
    pos_usd = position.get("position_usd", 0)
    partial_usdc     = position.get("partial_realized_usdc") or 0.0
    remaining_shares = position.get("shares") or 0.0
    if entry and exit_p is not None:
        if partial_usdc > 0:
            # Kısmi fill: kümülatif muhasebe — partial USDC + kalan hisse × son fiyat
            total_exit   = partial_usdc + remaining_shares * exit_p
            realized_pnl = round(total_exit - pos_usd, 6)
        else:
            realized_pnl = (exit_p - entry) / entry * pos_usd
    else:
        realized_pnl = None
    await conn.execute(
        """UPDATE positions
           SET status='closed', ts_close=?, pm_exit_price=?,
               exit_reason=?, realized_pnl=?, exit_hl_price=?,
               mae_pct=?, mfe_pct=?, mae_px=?, mfe_px=?,
               mae_ts=?, mfe_ts=?, mae_data_quality=?, price_source=?,
               sl_trigger_px=?, sl_trigger_pct=?, first_trigger_ts=?,
               exit_bid_at_trigger=?, exit_ask_at_trigger=?,
               spread_at_trigger=?, book_depth_at_trigger=?,
               sell_attempt_count=?, sell_unmatched_count=?,
               fill_ts=?, sl_fill_px=?, sl_fill_pct=?,
               trigger_fill_gap_pct=?, trigger_to_fill_secs=?,
               partial_fill_count=?, partial_fill_shares=?, partial_realized_usdc=?,
               sell_limit_price=?, first_exit_decision_ts=?
           WHERE position_id=?""",
        (
            position.get("closed_at", datetime.now(timezone.utc).isoformat()),
            exit_p,
            position.get("exit_reason"),
            realized_pnl,
            position.get("exit_hl_price"),
            position.get("mae_pct"),
            position.get("mfe_pct"),
            position.get("mae_px"),
            position.get("mfe_px"),
            position.get("mae_ts"),
            position.get("mfe_ts"),
            position.get("mae_data_quality"),
            position.get("price_source"),
            position.get("sl_trigger_px"),
            position.get("sl_trigger_pct"),
            position.get("first_trigger_ts"),
            position.get("exit_bid_at_trigger"),
            position.get("exit_ask_at_trigger"),
            position.get("spread_at_trigger"),
            position.get("book_depth_at_trigger"),
            position.get("sell_attempt_count"),
            position.get("sell_unmatched_count"),
            position.get("fill_ts"),
            position.get("sl_fill_px"),
            position.get("sl_fill_pct"),
            position.get("trigger_fill_gap_pct"),
            position.get("trigger_to_fill_secs"),
            position.get("partial_fill_count", 0),
            position.get("partial_fill_shares"),
            position.get("partial_realized_usdc"),
            position.get("sell_limit_price"),
            position.get("first_exit_decision_ts"),
            position["position_id"],
        ),
    )
    await conn.commit()


async def load_closed_today(conn) -> list[dict]:
    """Bugünün UTC kapanan pozisyonlarını yükler — restart sonrası daily_loss recovery."""
    today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    async with conn.execute(
        """SELECT position_id, ts_open, ts_close, slug, asset, action,
                  pm_entry_price, pm_exit_price, position_usd, realized_pnl,
                  exit_reason, dry_run, seq_no
           FROM positions
           WHERE status='closed' AND ts_close LIKE ?""",
        (f"{today_prefix}%",),
    ) as cur:
        rows = await cur.fetchall()
    return [
        {
            "position_id":    r[0],
            "opened_at":      r[1],
            "closed_at":      r[2],
            "slug":           r[3],
            "asset":          r[4],
            "action":         r[5],
            "pm_entry_price": r[6],
            "pm_exit_price":  r[7],
            "position_usd":   r[8],
            "realized_pnl":   r[9],
            "exit_reason":    r[10],
            "dry_run":        bool(r[11]),
            "seq_no":         r[12],
        }
        for r in rows
    ]


async def patch_position_resolution(
    conn,
    position_id:   str,
    pm_exit_price: float,
    realized_pnl:  float,
    exit_reason:   str = "market_resolved_late",
    exit_hl_price: float | None = None,
) -> None:
    """Kapanmış pozisyonun exit fiyatı ve P&L'ini günceller (market_expired → resolved_late)."""
    if conn is None:
        return
    await conn.execute(
        """UPDATE positions
           SET pm_exit_price=?, realized_pnl=?, exit_reason=?, exit_hl_price=?
           WHERE position_id=?""",
        (pm_exit_price, realized_pnl, exit_reason, exit_hl_price, position_id),
    )
    if conn.total_changes == 0:
        print(f"[patch] WARN: no row found for position_id={position_id!r} — nothing updated")
    await conn.commit()


async def log_entry_air_pocket(conn, event: dict) -> int:
    """Entry-side FAK_NO_MATCH event'ını entry_air_pocket_events tablosuna yazar.

    Returns: event_id (int) — delayed snapshot update için kullanılır.
    """
    if conn is None:
        return 0
    cursor = await conn.execute(
        """INSERT INTO entry_air_pocket_events (
               slug, asset, action, market_id, token_id,
               event_ts, council_pass_ts, order_submit_ts, error_ts,
               council_to_submit_ms, submit_to_error_ms,
               fair, expected_ask, original_worst_price, original_fee_adj, min_edge,
               reported_liquidity, top_of_book_size, book_levels_used, book_source, book_age_ms,
               order_id, error_type, position_created,
               fresh_ask_after_fail, fresh_no_ask_after_fail, fresh_book_age_ms,
               fresh_fee_adj_after_fail, fresh_price_delta_cents,
               fresh_edge_still_passes_min_edge, would_retry_passed_shadow,
               delayed_ask_after_fail, delayed_no_ask_after_fail, delayed_book_age_ms,
               delayed_fee_adj_after_fail, delayed_price_delta_cents,
               delayed_edge_still_passes_min_edge, delayed_would_retry_passed_shadow
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            event.get("slug"),
            event.get("asset"),
            event.get("action"),
            event.get("market_id"),
            event.get("token_id"),
            event.get("event_ts"),
            event.get("council_pass_ts"),
            event.get("order_submit_ts"),
            event.get("error_ts"),
            event.get("council_to_submit_ms"),
            event.get("submit_to_error_ms"),
            event.get("fair"),
            event.get("expected_ask"),
            event.get("original_worst_price"),
            event.get("original_fee_adj"),
            event.get("min_edge"),
            event.get("reported_liquidity"),
            event.get("top_of_book_size"),
            event.get("book_levels_used"),
            event.get("book_source"),
            event.get("book_age_ms"),
            event.get("order_id"),
            event.get("error_type"),
            event.get("position_created", 0),
            event.get("fresh_ask_after_fail"),
            event.get("fresh_no_ask_after_fail"),
            event.get("fresh_book_age_ms"),
            event.get("fresh_fee_adj_after_fail"),
            event.get("fresh_price_delta_cents"),
            event.get("fresh_edge_still_passes_min_edge"),
            event.get("would_retry_passed_shadow"),
            event.get("delayed_ask_after_fail"),
            event.get("delayed_no_ask_after_fail"),
            event.get("delayed_book_age_ms"),
            event.get("delayed_fee_adj_after_fail"),
            event.get("delayed_price_delta_cents"),
            event.get("delayed_edge_still_passes_min_edge"),
            event.get("delayed_would_retry_passed_shadow"),
        ),
    )
    await conn.commit()
    return cursor.lastrowid


async def update_entry_air_pocket_delayed(conn, event_id: int, delayed: dict) -> None:
    """Delayed shadow snapshot alanlarını mevcut air_pocket event'a yazar.

    Background task'tan çağrılır — ana execution path'i bloklamaz.
    """
    if conn is None or not event_id:
        return
    await conn.execute(
        """UPDATE entry_air_pocket_events SET
               delayed_ask_after_fail=?,
               delayed_no_ask_after_fail=?,
               delayed_book_age_ms=?,
               delayed_fee_adj_after_fail=?,
               delayed_price_delta_cents=?,
               delayed_edge_still_passes_min_edge=?,
               delayed_would_retry_passed_shadow=?
           WHERE id=?""",
        (
            delayed.get("delayed_ask_after_fail"),
            delayed.get("delayed_no_ask_after_fail"),
            delayed.get("delayed_book_age_ms"),
            delayed.get("delayed_fee_adj_after_fail"),
            delayed.get("delayed_price_delta_cents"),
            delayed.get("delayed_edge_still_passes_min_edge"),
            delayed.get("delayed_would_retry_passed_shadow"),
            event_id,
        ),
    )
    await conn.commit()


async def log_partial_fill_update(conn, position: dict) -> None:
    """Kısmi fill sonrası açık pozisyonun shares ve partial_* alanlarını DB'ye yazar.

    Bot crash/restart durumunda partial fill state kaybolmasın diye her kısmi
    fill'den hemen sonra çağrılır.
    """
    if conn is None:
        return
    await conn.execute(
        """UPDATE positions
           SET shares=?, partial_fill_count=?, partial_fill_shares=?, partial_realized_usdc=?
           WHERE position_id=? AND status='open'""",
        (
            position.get("shares"),
            position.get("partial_fill_count", 0),
            position.get("partial_fill_shares"),
            position.get("partial_realized_usdc"),
            position["position_id"],
        ),
    )
    await conn.commit()
