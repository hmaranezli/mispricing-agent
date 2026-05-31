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
    await conn.execute(
        """INSERT OR IGNORE INTO positions
               (position_id, ts_open, slug, asset, action, pm_entry_price,
                fair_value, ref_price, edge, position_usd, kelly_f,
                confidence_score, status, dry_run)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)""",
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
        ),
    )
    await conn.commit()


async def log_position_close(conn, position: dict) -> None:
    if conn is None:
        return
    entry   = position.get("pm_entry_price")
    exit_p  = position.get("pm_exit_price")
    pos_usd = position.get("position_usd", 0)
    if entry and exit_p is not None:
        realized_pnl = (exit_p - entry) / entry * pos_usd
    else:
        realized_pnl = None
    await conn.execute(
        """UPDATE positions
           SET status='closed', ts_close=?, pm_exit_price=?,
               exit_reason=?, realized_pnl=?
           WHERE position_id=?""",
        (
            position.get("closed_at", datetime.now(timezone.utc).isoformat()),
            exit_p,
            position.get("exit_reason"),
            realized_pnl,
            position["position_id"],
        ),
    )
    await conn.commit()
