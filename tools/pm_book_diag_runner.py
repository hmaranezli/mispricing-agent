"""tools/pm_book_diag_runner.py — diagnostic/lab-only PM CLOB book capture runner.

Connects fetch_clob_book (single-token courier) to collect_polymarket_book_tick (append-only writer)
via a thin Decimal-sanitizing adapter. Each capture cycle fetches YES then NO books sequentially
and writes exactly one row to the supplied lab DB. This is SERIAL INTERVAL EVIDENCE only —
not a simultaneous snapshot, not a paired near-sync observation.

Caller must supply ALL of: yes_token_id, no_token_id, market_slug, asset, timeframe, db_path,
base_url, http_client, cycle_sleep_seconds, and at least one stop condition (max_captures or
duration_seconds). No defaults exist for any of these — missing values are programmer errors.

raw_body_text from the fetcher is NOT persisted to the DB in this slice. The writer stores
reserialized json.dumps output, not the byte-verbatim HTTP body. No end-to-end raw HTTP
preservation is claimed.

This runner ONLY opens a lab DB, calls fetch_clob_book per token, sanitizes Decimal values,
and writes one row via collect_polymarket_book_tick. It does nothing else. In particular it
calls no external lookup APIs, reads no reference tables, computes no math beyond sanitization,
and touches no execution, wallet, signing, Telegram, or S1 production surface.
"""
from __future__ import annotations

import argparse
import asyncio
import time
from decimal import Decimal

import aiosqlite

from db.schema import init_schema
from data.pm_clob_fetcher import fetch_clob_book
from data.pm_book_writer import collect_polymarket_book_tick


def _sanitize_decimals(obj):
    """Recursively convert Decimal to canonical fixed-point string.

    Prevents TypeError in writer's json.dumps when fetcher's parse_float/parse_int=Decimal
    has produced Decimal objects in parsed_safe_book. format(d, 'f') ensures no scientific
    notation (Decimal('1E-7') -> '0.0000001'), matching the writer's Decimal discipline.
    """
    if isinstance(obj, Decimal):
        return format(obj, "f")
    if isinstance(obj, dict):
        return {k: _sanitize_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_decimals(v) for v in obj]
    return obj


async def run_pm_book_diag(
    *,
    yes_token_id: str,
    no_token_id: str,
    market_slug: str,
    asset: str,
    timeframe: str,
    db_path: str,
    base_url: str,
    http_client,
    cycle_sleep_seconds: float,
    max_captures: int | None = None,
    duration_seconds: float | None = None,
    _sleep_fn=asyncio.sleep,
    _monotonic_fn=time.monotonic,
) -> dict:
    """Run a bounded diagnostic capture loop writing to a dedicated lab DB.

    Returns {"captures": N} where N is the total rows written.
    Raises ValueError on any programmer contract violation (checked before loop).
    Re-raises RuntimeError on DB write failure (fail-fast; evidence not lost silently).
    """
    # --- pre-loop contract checks (fail fast) ---------------------------------
    if not yes_token_id:
        raise ValueError("yes_token_id must be non-empty")
    if not no_token_id:
        raise ValueError("no_token_id must be non-empty")
    if yes_token_id == no_token_id:
        raise ValueError("yes_token_id and no_token_id must be distinct")
    if not market_slug:
        raise ValueError("market_slug must be non-empty")
    if not asset:
        raise ValueError("asset must be non-empty")
    if not timeframe:
        raise ValueError("timeframe must be non-empty")
    if not db_path:
        raise ValueError("db_path must be non-empty")
    if not base_url:
        raise ValueError("base_url must be non-empty")
    if http_client is None:
        raise ValueError("http_client must not be None")
    if cycle_sleep_seconds < 1.0:
        raise ValueError("cycle_sleep_seconds must be >= 1.0 to prevent rate-limit behavior")
    if max_captures is None and duration_seconds is None:
        raise ValueError("at least one stop condition required: supply max_captures or duration_seconds")
    if max_captures is not None and max_captures < 1:
        raise ValueError("max_captures must be >= 1")
    if duration_seconds is not None and duration_seconds <= 0:
        raise ValueError("duration_seconds must be > 0")

    # --- dedicated lab DB only -----------------------------------------------
    conn = await aiosqlite.connect(db_path)
    try:
        await init_schema(conn)
    except Exception:
        await conn.close()
        raise

    # --- single-token fetcher adapter ----------------------------------------
    # BookFetchResult is discarded after extracting lightweight scalars.
    # raw_body_text is NOT retained beyond the single call — no memory accumulation.
    async def _book_fetcher(token_id: str):
        result = await fetch_clob_book(token_id, http_client=http_client, base_url=base_url)
        if result.error_code:
            print(
                f"  fetcher [{token_id[:16]}] "
                f"error={result.error_code} http={result.http_status} "
                f"span_ms={result.fetch_span_ms}",
                flush=True,
            )
        if result.parsed_safe_book is None:
            return None
        # Sanitize Decimal -> fixed-point string; discard raw_body_text
        return _sanitize_decimals(result.parsed_safe_book)

    # --- bounded capture loop ------------------------------------------------
    deadline = _monotonic_fn() + duration_seconds if duration_seconds is not None else None
    captures = 0

    try:
        while True:
            row = await collect_polymarket_book_tick(
                conn=conn,
                market_slug=market_slug,
                asset=asset,
                timeframe=timeframe,
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
                book_fetcher=_book_fetcher,
            )
            captures += 1
            print(
                f"[cap {captures}] id={row['book_tick_id']} "
                f"capture_ms={row['capture_span_ms']} "
                f"skew_ms={row['yes_no_completion_skew_ms']} "
                f"reject={row['reject_reason']}",
                flush=True,
            )

            if max_captures is not None and captures >= max_captures:
                break
            if deadline is not None and _monotonic_fn() >= deadline:
                break
            await _sleep_fn(cycle_sleep_seconds)

    except Exception as exc:
        await conn.close()
        raise RuntimeError(
            f"DB write failed; aborting diagnostic runner after {captures} captures: {exc!r}"
        ) from exc

    await conn.close()
    return {"captures": captures}


# ---------------------------------------------------------------------------
# CLI entrypoint (auditable replacement for one-off inline `python -c` launch)
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    """Build the diagnostic-runner CLI parser. All market/token/path args are explicit and required.

    The CLI performs NO market or token discovery: the caller supplies the exact slug and both
    token ids. No default DB path exists. At least one stop condition (--max-captures or
    --duration-seconds) must be supplied (enforced in main()).
    """
    p = argparse.ArgumentParser(
        prog="tools.pm_book_diag_runner",
        description="Lab-only PM CLOB book capture runner (serial interval evidence only).",
    )
    p.add_argument("--market-slug", required=True, help="explicit Polymarket slug")
    p.add_argument("--yes-token-id", required=True, help="explicit YES/Up CLOB token id")
    p.add_argument("--no-token-id", required=True, help="explicit NO/Down CLOB token id")
    p.add_argument("--asset", required=True, help="asset label, e.g. BTC")
    p.add_argument("--timeframe", required=True, help="timeframe label, e.g. 5m")
    p.add_argument("--db-path", required=True, help="dedicated lab DB path (no default)")
    p.add_argument("--base-url", required=True, help="CLOB base url")
    p.add_argument("--cycle-sleep-seconds", required=True, type=float,
                   help="sleep between cycles (>= 1.0 enforced by runner)")
    p.add_argument("--max-captures", type=int, default=None, help="bounded capture count")
    p.add_argument("--duration-seconds", type=float, default=None, help="bounded wall-clock limit")
    return p


async def _amain(args, *, session_factory, run_fn) -> dict:
    """Create the injected client session inside the runtime path and run the diagnostic loop."""
    session_cm = session_factory()
    async with session_cm as session:
        result = await run_fn(
            yes_token_id=args.yes_token_id,
            no_token_id=args.no_token_id,
            market_slug=args.market_slug,
            asset=args.asset,
            timeframe=args.timeframe,
            db_path=args.db_path,
            base_url=args.base_url,
            http_client=session,
            cycle_sleep_seconds=args.cycle_sleep_seconds,
            max_captures=args.max_captures,
            duration_seconds=args.duration_seconds,
        )
    print("RUNNER_RESULT", result, flush=True)
    return result


def main(argv=None, *, session_factory=None, run_fn=None) -> int:
    """Parse args, enforce stop-condition presence, then run. Returns process exit code.

    ``session_factory`` and ``run_fn`` are injectable for tests so no real network/DB is touched.
    In production, the aiohttp ClientSession is created lazily only on the runtime path.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.max_captures is None and args.duration_seconds is None:
        parser.error("at least one of --max-captures or --duration-seconds is required")

    if session_factory is None:
        import aiohttp
        session_factory = aiohttp.ClientSession
    if run_fn is None:
        run_fn = run_pm_book_diag

    asyncio.run(_amain(args, session_factory=session_factory, run_fn=run_fn))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
