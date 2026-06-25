"""tools/paper_smoke_runner.py — isolated bounded paper-smoke runner.

PURE CALLER of already-ratified paper functions. It starts ONLY:
  1) ``main_loop._paper_shadow_scan_loop(conn, db_path=db_path)``
  2) ``execution.paper_tracker._paper_monitor_loop(db_path)``
against a DEDICATED sqlite ``--db-path`` for a bounded window, then prints a read-only summary.

It NEVER starts ``main_loop.main()``, the Telegram poller / notifier, the live monitor, the executor,
bankroll/credential lookup, ``_scan_and_execute``, or any live / CLOB / S1 / wallet / signing path.
It contains NO business logic, makes NO trading/paper decision, and changes NO runtime behavior. Every
DB read/write is restricted to the supplied ``db_path`` — the default ``logs/mispricing.db`` is never
opened by this runner.

Invocation::

    python -m tools.paper_smoke_runner --duration-secs 1500 --db-path logs/paper_smoke.db

Safety gates (checked BEFORE any task/DB work; refuse with nonzero ``SystemExit`` on any violation):
``config.DRY_RUN is True``, ``config.NEW_ENTRIES_ENABLED is False``,
``config.COUNCIL_DECISION_AUTHORITY_ENABLED is False``.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (config attribute name, required value) — all must hold or the runner refuses to start.
_REQUIRED_GATES = (
    ("DRY_RUN", True),
    ("NEW_ENTRIES_ENABLED", False),
    ("COUNCIL_DECISION_AUTHORITY_ENABLED", False),
)


def check_safety_gates(cfg) -> None:
    """Refuse (``SystemExit`` nonzero) unless paper-safe. Must run BEFORE any task/DB work."""
    for name, expected in _REQUIRED_GATES:
        actual = getattr(cfg, name, None)
        if actual is not expected:
            raise SystemExit(f"REFUSED: config.{name} must be {expected!r} (got {actual!r})")


async def summarize(db_path: str) -> dict:
    """Read-only summary STRICTLY against the supplied ``db_path``. Never opens the default DB."""
    import aiosqlite

    out = {
        "db_path": str(db_path),
        "shadow_positions_by_status": {},
        "paper_entry_events": 0,
        "positions": None,
        "order_intents": None,
    }
    async with aiosqlite.connect(str(db_path)) as conn:
        async with conn.execute(
            "SELECT status, COUNT(*) FROM shadow_positions GROUP BY status"
        ) as cur:
            out["shadow_positions_by_status"] = {s: n for s, n in await cur.fetchall()}
        async with conn.execute("SELECT COUNT(*) FROM paper_entry_events") as cur:
            row = await cur.fetchone()
            out["paper_entry_events"] = row[0] if row else 0
        # Zero-delta evidence — counted ONLY in the dedicated db (never the live db).
        for tbl in ("positions", "order_intents"):
            try:
                async with conn.execute(f"SELECT COUNT(*) FROM {tbl}") as cur:
                    row = await cur.fetchone()
                    out[tbl] = row[0] if row else 0
            except Exception:
                out[tbl] = None
    return out


async def run_paper_smoke(*, duration_secs, db_path: str, cfg=None) -> dict:
    """Start ONLY the two paper loops against ``db_path`` for ``duration_secs``, then summarize.

    Pure-until-loops: safety gates run first; on any failure no task or DB connection is created.
    Both loops are cancelled and awaited on timeout / cancellation / SIGINT (no task leak).
    """
    if cfg is None:
        import config as cfg
    check_safety_gates(cfg)
    if duration_secs is None or duration_secs <= 0:
        raise SystemExit("REFUSED: duration_secs must be positive")

    import aiosqlite
    from db.schema import init_schema
    from execution import paper_tracker
    import main_loop

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    tasks: list[asyncio.Task] = []
    saved_exc: BaseException | None = None
    try:
        await init_schema(conn)
        tasks = [
            asyncio.create_task(main_loop._paper_shadow_scan_loop(conn, db_path=db_path)),
            asyncio.create_task(paper_tracker._paper_monitor_loop(db_path)),
        ]
        # Responsive wait: return as soon as the timebox expires OR a loop raises (fail-fast).
        # Normal timeout → done is empty (both still running); a loop crash → its task is in done.
        done, _pending = await asyncio.wait(
            tasks, timeout=duration_secs, return_when=asyncio.FIRST_EXCEPTION
        )
        for t in done:
            if t.cancelled():
                continue  # normal cancellation is acceptable, never a failure
            exc = t.exception()
            if exc is not None and not isinstance(exc, asyncio.CancelledError):
                saved_exc = exc  # an UNEXPECTED crash — must not be swallowed
                break
        # Cancel whatever is still running and await ONLY for cleanup (swallow here is cleanup-only).
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await conn.close()

    if saved_exc is not None:
        # A paper loop crashed before the timebox: fail fast, re-raising the original exception.
        raise saved_exc

    return await summarize(db_path)


def _positive_int(value) -> int:
    iv = int(value)
    if iv <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return iv


def _print_summary(summary: dict) -> None:
    print(f"[paper_smoke] db_path={summary['db_path']}")
    print(f"[paper_smoke] shadow_positions_by_status={summary['shadow_positions_by_status']}")
    print(f"[paper_smoke] paper_entry_events={summary['paper_entry_events']}")
    print(
        f"[paper_smoke] positions={summary['positions']} "
        f"order_intents={summary['order_intents']} (dedicated db only)"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="paper_smoke_runner",
        description="Isolated bounded paper smoke (no live/S1/Telegram).",
    )
    parser.add_argument("--duration-secs", type=_positive_int, required=True)
    parser.add_argument("--db-path", required=True)
    args = parser.parse_args(argv)
    summary = asyncio.run(run_paper_smoke(duration_secs=args.duration_secs, db_path=args.db_path))
    _print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
