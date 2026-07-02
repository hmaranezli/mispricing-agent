"""analysis/forensic/gateg8_exit_evidence.py — G8 Exit-Bid Evidence (Slice 1).

PURE simulated held-token exit-liquidation evidence for one G8 PAPER_OPEN holding, evaluated
on a later (or the opening) current-window poll.

HARD BOUNDARIES:
  * NO order executes. Every economic field is a SIMULATED mark computed against the DISPLAYED
    bid ladder -- never a real fill, never realized PnL, never FAK/FOK authorization.
  * Evidence binds EXCLUSIVELY to the ORIGINAL unique PAPER_OPEN holding (side/token/qty/entry
    basis). A later poll's selected_side/token NEVER changes the holding being evaluated; the
    held-token ladder is selected by exact held_token_id, never by the current poll's side.
  * Reuses the COMMITTED pure exit primitives (gateg9_managed_exit) and the canonical fee
    function (gateg7_paper_pnl.entry_fee_quadratic) -- never a new fee/PnL formula. Entry fee is
    recomputed exactly ONCE (inside entry_cost) and never re-charged on the exit leg.
  * Pure: no network, no clock, no G9 orchestration, no wallet/signing/capital/order path.
  * Append-only: write_exit_evidence never UPDATEs/UPSERTs; a same-key identical payload is a
    no-op, a same-key differing payload fails closed.
"""
from __future__ import annotations

import re
import sqlite3
from decimal import Decimal

from analysis.forensic import gateg5_plumbing as _plumb
from analysis.forensic import gateg7_paper_pnl as pp
from analysis.forensic import gateg9_managed_exit as ge

# evidence classification (exact Slice-1 vocabulary)
EV_OK = "OK"
EV_BID_DEPTH_INSUFFICIENT = "BID_DEPTH_INSUFFICIENT"
EV_BOOK_UNAVAILABLE = "BOOK_UNAVAILABLE"
EV_FEE_UNAVAILABLE = "FEE_UNAVAILABLE"
EV_LADDER_MALFORMED = "LADDER_MALFORMED"


class ExitEvidenceConflictError(Exception):
    """A row with the same source_ledger_id already exists with a DIFFERENT payload.
    Fail closed -- never overwrite historical evidence."""


_EXIT_EVIDENCE_COLS = [
    # identity / provenance
    "source_ledger_id", "entry_ledger_id", "condition_id", "slug", "asset", "window",
    "obs_ts_ms", "poll_ledger_status",
    # original holding (immutable across later polls)
    "held_side", "held_token_id", "held_qty", "entry_ask_vwap", "fee_rate",
    "entry_notional", "entry_fee", "entry_cost", "entry_ts_ms",
    # held-token book timing
    "bid_quote_ts_ms", "bid_capture_started_ms", "bid_capture_completed_ms",
    # top of held-token book
    "best_bid", "best_ask",
    # walk evidence
    "requested_full_qty", "walkable_bid_qty", "residual_unwalkable_qty",
    "bid_depth_sufficient", "levels_used", "would_move_book",
    # full-quantity simulated economics (NULL unless full depth AND fee known)
    "full_qty_exec_bid_vwap", "exit_fee", "simulated_gross_liquidation_value",
    "simulated_net_liquidation_value", "simulated_mark_to_exit_pnl",
    # walkable-portion simulated evidence (portion only; NOT a fill claim, NOT FAK)
    "simulated_walkable_bid_vwap", "simulated_walkable_gross_liquidation_value",
    # classification
    "evidence_status", "failure_provenance",
]

_EXIT_INTEGER_COLS = frozenset({
    "source_ledger_id", "entry_ledger_id", "obs_ts_ms", "entry_ts_ms",
    "bid_quote_ts_ms", "bid_capture_started_ms", "bid_capture_completed_ms",
    "bid_depth_sufficient", "levels_used", "would_move_book",
})

_URL_RE = re.compile(r"https?://\S+")
_HEX_RE = re.compile(r"0x[0-9a-fA-F]{12,}")
_LONGNUM_RE = re.compile(r"\d{16,}")


def _sanitize(exc, cap: int = 200) -> str:
    """Redact URLs, 0x-hashes and long token IDs; collapse whitespace; length-cap."""
    msg = str(exc)
    msg = _URL_RE.sub("[URL]", msg)
    msg = _HEX_RE.sub("[HEX]", msg)
    msg = _LONGNUM_RE.sub("[ID]", msg)
    msg = " ".join(msg.split())
    return (msg[:cap] + "...[truncated]") if len(msg) > cap else msg


def _s(x):
    return str(x) if x is not None else None


def init_exit_evidence_table(conn) -> None:
    """Append-only evidence table. TEXT/INTEGER only (Decimal-as-canonical-TEXT); never REAL.
    UNIQUE(source_ledger_id) is the deterministic poll identity (1:1 with a ledger poll row);
    a secondary non-unique (condition_id, obs_ts_ms) index supports analysis."""
    cols_sql = ",".join(f"{c} INTEGER" if c in _EXIT_INTEGER_COLS else f"{c} TEXT"
                        for c in _EXIT_EVIDENCE_COLS)
    conn.execute(f"CREATE TABLE IF NOT EXISTS gateg8_exit_evidence(id INTEGER PRIMARY KEY, {cols_sql})")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_g8_exit_evidence_source "
                 "ON gateg8_exit_evidence(source_ledger_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_g8_exit_evidence_cond "
                 "ON gateg8_exit_evidence(condition_id, obs_ts_ms)")
    conn.commit()


def build_exit_evidence(*, entry_row: dict, entry_ledger_id: int, source_ledger_id: int,
                        obs_ts_ms, poll_ledger_status: str, books_by_token: dict) -> dict:
    """Build ONE simulated exit-evidence row for the ORIGINAL PAPER_OPEN holding described by
    `entry_row`, evaluated against this poll's held-token book. `books_by_token` maps token_id ->
    book dict ({bids, asks, quote_ts_ms, capture_started_ms, capture_completed_ms}) or None.

    The held token is `entry_row['selected_token_id']`; its ladder is selected by exact match,
    never by the current poll's side. No full-quantity value is fabricated when depth or fee is
    unavailable -- those fields stay None and a fail-closed status is recorded.
    """
    held_side = entry_row["selected_side"]
    held_token_id = entry_row["selected_token_id"]
    held_qty = Decimal(str(entry_row["selected_filled_qty"]))
    entry_ask_vwap = entry_row["yes_exec_ask_vwap"] if held_side == "YES" else entry_row["no_exec_ask_vwap"]
    fee_rate_raw = entry_row.get("fee_rate")
    entry_notional = entry_row.get("selected_entry_notional")

    row = {c: None for c in _EXIT_EVIDENCE_COLS}
    row.update({
        "source_ledger_id": source_ledger_id, "entry_ledger_id": entry_ledger_id,
        "condition_id": entry_row.get("condition_id"), "slug": entry_row.get("slug"),
        "asset": entry_row.get("asset"), "window": entry_row.get("window"),
        "obs_ts_ms": obs_ts_ms, "poll_ledger_status": poll_ledger_status,
        "held_side": held_side, "held_token_id": held_token_id, "held_qty": _s(held_qty),
        "entry_ask_vwap": _s(entry_ask_vwap), "fee_rate": _s(fee_rate_raw),
        "entry_notional": _s(entry_notional), "entry_ts_ms": entry_row.get("paper_decision_ts"),
        "requested_full_qty": _s(held_qty),
    })

    # original entry cost = original notional + entry fee (canonical fee, computed ONCE).
    # Requires both fee_rate and the original notional; otherwise fee-dependent fields stay None.
    fee_available = fee_rate_raw is not None and entry_notional is not None
    entry_cost_dec = None
    if fee_available:
        fee_rate = Decimal(str(fee_rate_raw))
        entry_fee_dec = pp.entry_fee_quadratic(held_qty, fee_rate, Decimal(str(entry_ask_vwap)))
        entry_cost_dec = Decimal(str(entry_notional)) + entry_fee_dec
        row["entry_fee"] = _s(entry_fee_dec)
        row["entry_cost"] = _s(entry_cost_dec)

    book = books_by_token.get(held_token_id)
    if book is None:
        # missing captured book -- never invent an empty zero-price ladder
        row["evidence_status"] = EV_BOOK_UNAVAILABLE
        return row

    row["bid_quote_ts_ms"] = book.get("quote_ts_ms")
    row["bid_capture_started_ms"] = book.get("capture_started_ms")
    row["bid_capture_completed_ms"] = book.get("capture_completed_ms")

    try:
        bid_levels = _plumb.parse_bid_ladder(_plumb.ladder_to_decimal_json(book.get("bids") or []))
        ask_levels = _plumb.parse_ask_ladder(_plumb.ladder_to_decimal_json(book.get("asks") or []))
        fill = ge.walk_bid_ladder_for_qty(book.get("bids") or [], held_qty)
    except _plumb.PlumbingError as e:
        row["evidence_status"] = EV_LADDER_MALFORMED
        row["failure_provenance"] = _sanitize(e)
        return row

    row["best_bid"] = _s(bid_levels[0][0]) if bid_levels else None      # validated descending
    row["best_ask"] = _s(ask_levels[0][0]) if ask_levels else None      # validated ascending
    row["walkable_bid_qty"] = _s(fill.filled_qty)
    row["residual_unwalkable_qty"] = _s(fill.residual_unfilled_qty)
    row["bid_depth_sufficient"] = 1 if fill.depth_sufficient else 0
    row["levels_used"] = fill.levels_used
    row["would_move_book"] = 1 if fill.would_move_book else 0
    if fill.filled_qty > 0:
        row["simulated_walkable_bid_vwap"] = _s(fill.exec_bid_vwap)
        row["simulated_walkable_gross_liquidation_value"] = _s(fill.exec_bid_vwap * fill.filled_qty)

    if not fill.depth_sufficient:
        # partial simulated evidence retained above; full-position fields stay None
        row["evidence_status"] = EV_BID_DEPTH_INSUFFICIENT
        return row
    if not fee_available:
        # walk fields retained; no fee -> no full-position liquidation economics (no default fee)
        row["evidence_status"] = EV_FEE_UNAVAILABLE
        return row

    full_vwap = fill.exec_bid_vwap
    gross = full_vwap * held_qty
    exit_fee = ge.compute_exit_fee(held_qty, Decimal(str(fee_rate_raw)), full_vwap)
    net = gross - exit_fee
    row["full_qty_exec_bid_vwap"] = _s(full_vwap)
    row["exit_fee"] = _s(exit_fee)
    row["simulated_gross_liquidation_value"] = _s(gross)
    row["simulated_net_liquidation_value"] = _s(net)
    row["simulated_mark_to_exit_pnl"] = _s(net - entry_cost_dec)   # mark, NOT realized PnL
    row["evidence_status"] = EV_OK
    return row


def write_exit_evidence(conn, row: dict) -> str:
    """Append-only idempotent writer keyed on source_ledger_id.

    - new key -> insert once, return "RECORDED";
    - existing key + byte-identical payload -> no-op, return "ALREADY_RECORDED";
    - existing key + any differing field -> raise ExitEvidenceConflictError, leave row unchanged.

    Never UPDATE/UPSERT/REPLACE. No automatic retry or repair.
    """
    payload = tuple(row.get(c) for c in _EXIT_EVIDENCE_COLS)
    select_sql = (f"SELECT {','.join(_EXIT_EVIDENCE_COLS)} FROM gateg8_exit_evidence "
                  "WHERE source_ledger_id=?")
    existing = conn.execute(select_sql, (row.get("source_ledger_id"),)).fetchone()
    if existing is not None:
        if tuple(existing) == payload:
            return "ALREADY_RECORDED"
        raise ExitEvidenceConflictError(
            f"exit-evidence conflict for source_ledger_id={row.get('source_ledger_id')}")

    insert_sql = (f"INSERT INTO gateg8_exit_evidence({','.join(_EXIT_EVIDENCE_COLS)}) "
                  f"VALUES ({','.join('?' for _ in _EXIT_EVIDENCE_COLS)})")
    conn.execute("SAVEPOINT g8_exit_write")
    try:
        conn.execute(insert_sql, payload)
    except sqlite3.IntegrityError:
        # a concurrent/reentrant insert of the SAME key raced us: re-check payload identity
        conn.execute("ROLLBACK TO g8_exit_write")
        conn.execute("RELEASE g8_exit_write")
        existing = conn.execute(select_sql, (row.get("source_ledger_id"),)).fetchone()
        if existing is not None and tuple(existing) == payload:
            conn.commit()
            return "ALREADY_RECORDED"
        raise ExitEvidenceConflictError(
            f"exit-evidence conflict for source_ledger_id={row.get('source_ledger_id')}")
    conn.execute("RELEASE g8_exit_write")
    conn.commit()
    return "RECORDED"
