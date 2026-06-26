"""tools/miami_oneshot_runner.py — Miami v3 Sub-slice B one-shot live runner (tested core).

Performs exactly one read-only one-shot via INJECTED fetcher callables:
  YES book, NO book, Hyperliquid reference price, and condition_id market metadata.
It adapts the results into ``analysis.miami_live_snapshot.assemble_snapshot_inputs``, calls
``analysis.expiry_snipe_calculator.compute_decision_row``, merges note markers + operator_fee_cost
into the final ``row['notes']``, and prints a compact operator summary (full 48-field dump only under
--full/--verbose). CSV append happens only under --append + --csv-path.

The runner selects no market and no stake, places no order, and writes no DB. Reference is read-only.

Exit codes:
  0 = success
  1 = fetch / reject error
  2 = validation / cross-check failure (incl. argparse errors and pre-fetch contract checks)
  3 = internal / unexpected error

The three fetcher callables are REQUIRED injected dependencies (no hidden network default), so tests
run fully offline. Live fetcher construction is a separate authorized wiring step (see __main__).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from analysis.miami_live_snapshot import assemble_snapshot_inputs
from analysis.expiry_snipe_calculator import compute_decision_row
from analysis.decision_log_csv import append_decision_row

_COMPACT_FIELDS = (
    "candidate", "selected_side_candidate", "yes_adjusted_edge", "no_adjusted_edge",
    "liquidity_status", "is_pin_risk", "reference_staleness_ms",
    "trade_allowed", "operator_decision_required", "notes",
)


def _now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools.miami_oneshot_runner",
        description="Miami v3 one-shot read-only snapshot -> decision row (operator aid; no trading).")
    p.add_argument("--yes-token-id", required=True)
    p.add_argument("--no-token-id", required=True)
    p.add_argument("--condition-id", required=True, help="safety pin: metadata cross-check source")
    p.add_argument("--asset", required=True)
    p.add_argument("--timeframe", required=True)
    p.add_argument("--strike", required=True, type=float)
    p.add_argument("--expiry", required=True, help="UTC ISO-8601 ending in 'Z'")
    p.add_argument("--intended-stake-usd", required=True, type=float)
    p.add_argument("--base-url", required=True)
    p.add_argument("--fee-cost", required=True, type=float, help="must be > 0")
    p.add_argument("--volatility-annual", type=float, default=None)
    p.add_argument("--tie-resolves-to", default="UP")
    p.add_argument("--reference-source", default="Hyperliquid")
    p.add_argument("--append", action="store_true")
    p.add_argument("--csv-path", default=None)
    p.add_argument("--full", "--verbose", dest="full", action="store_true")
    return p


def _rejection_reason(row: dict, calc_notes: str) -> str:
    """Runner-side interpretation of WHY candidate is False (does not change calculator logic)."""
    if row["is_pin_risk"]:
        return "pin_risk"
    if "stale_reference" in calc_notes:
        return "stale_reference"
    if row["liquidity_status"] in ("weak_fill", "insufficient"):
        return "insufficient_liquidity_or_weak_fill"
    return "below_threshold_or_negative_adjusted_edge"


def _book_to_sides(parsed_safe_book):
    if not isinstance(parsed_safe_book, dict):
        return {"bids": [], "asks": []}
    return {"bids": parsed_safe_book.get("bids") or [], "asks": parsed_safe_book.get("asks") or []}


def main(argv=None, *, book_fetcher, reference_fetcher, metadata_fetcher,
         now_fn=None, out=None, extra_notes_markers=()) -> int:
    out = out or sys.stdout
    now_fn = now_fn or _now_z
    parser = build_arg_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:                     # argparse error -> validation class
        return int(e.code) if e.code is not None else 2

    try:
        # ---- pre-fetch contract checks (Exit 2) ------------------------------
        if args.fee_cost <= 0:
            print("validation error: --fee-cost must be > 0", file=out)
            return 2
        if args.append and not args.csv_path:
            print("validation error: --append requires --csv-path", file=out)
            return 2

        captured_at = now_fn()

        # ---- one-shot read-only fetches (Exit 1 on reject) -------------------
        yres = book_fetcher(args.yes_token_id)
        if yres.get("error_code"):
            print(f"fetch error: yes book {yres['error_code']}", file=out)
            return 1
        nres = book_fetcher(args.no_token_id)
        if nres.get("error_code"):
            print(f"fetch error: no book {nres['error_code']}", file=out)
            return 1
        rres = reference_fetcher(args.asset)
        if rres.get("error_code"):
            print(f"fetch error: reference {rres['error_code']}", file=out)
            return 1
        mres = metadata_fetcher(args.condition_id)
        if mres.get("error_code"):
            print(f"fetch error: metadata {mres['error_code']}", file=out)
            return 1

        reference_tick = {"price": rres.get("price"), "client_fetched_at": captured_at}
        if rres.get("source_event_ts"):
            reference_tick["source_event_ts"] = rres["source_event_ts"]

        # ---- assemble (Exit 2 on validation/cross-check) ---------------------
        try:
            assembled = assemble_snapshot_inputs(
                asset=args.asset, timeframe=args.timeframe,
                market_slug_or_label=args.condition_id,
                yes_token_id=args.yes_token_id, no_token_id=args.no_token_id,
                strike=args.strike, expiry=args.expiry,
                intended_stake_usd=args.intended_stake_usd, tie_resolves_to=args.tie_resolves_to,
                captured_at=captured_at, reference_source=args.reference_source,
                yes_book=_book_to_sides(yres.get("parsed_safe_book")),
                no_book=_book_to_sides(nres.get("parsed_safe_book")),
                reference_tick=reference_tick,
                market_metadata={"tokens": mres.get("tokens"), "strike": mres.get("strike"),
                                 "expiry": mres.get("expiry")},
                volatility_annual=args.volatility_annual,
            )
        except ValueError as e:
            print(f"validation/cross-check error: {e}", file=out)   # no fabricated row
            return 2

        # ---- compute + audit-merge notes -------------------------------------
        row = compute_decision_row(assembled.kwargs, {"fee_cost": args.fee_cost})
        calc_notes = row["notes"]
        audit = ([f"operator_fee_cost={args.fee_cost}"]
                 + list(extra_notes_markers) + list(assembled.notes_markers))
        row["notes"] = " | ".join(audit + [calc_notes])

        # ---- output ----------------------------------------------------------
        if args.full:
            for k in sorted(row.keys()):
                print(f"{k}={row[k]}", file=out)
        else:
            for f in _COMPACT_FIELDS:
                print(f"{f}={row[f]}", file=out)
        if not row["candidate"]:
            print(f"rejection_reason={_rejection_reason(row, calc_notes)}", file=out)

        if args.append:
            append_decision_row(row, args.csv_path, create_parents=True)

        return 0
    except SystemExit:
        raise
    except Exception as e:  # unexpected -> internal
        print(f"internal error: {e!r}", file=out)
        return 3


if __name__ == "__main__":
    print("miami_oneshot_runner: live fetcher wiring is a separate authorized step; "
          "this module exposes a tested orchestration core that requires injected fetchers.",
          file=sys.stderr)
    raise SystemExit(3)
