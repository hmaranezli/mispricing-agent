#!/usr/bin/env python3
"""
Gate G9 — Managed Position orchestrator (isolated ledger + G6-reuse resolution + a
single-poll monitoring-snapshot capture primitive). PAPER/SHADOW ONLY.

HARD BOUNDARIES:
  * PUBLIC read-only GET only (CLOB book x2 per poll: selected + opposite token).
    NO auth, NO wallet, NO signing, NO capital, NO orders.
  * NO resolution fetch performed here for HOLD/PnL decisions -- resolve_selected_side
    only DECIDES from already-fetched Gamma/CLOB payloads, reusing the committed G6
    pure deciders (gamma_decide/clob_decide) unmodified; it never invents a new
    resolution heuristic.
  * NO S1 access. Live S1 stays CREATED_EMPTY_LOCKED_CONTAINER; append DENIED.
  * Inert unless armed: GATEG9_MANAGED_ARM=MANAGED-EXIT-PAPER-CONFIRMED (default OFF).
  * Isolated tables only (gateg9_*); never signal_log, mark_path, or the G8 paper
    ledger. No REAL columns for monetary/edge values -- canonical Decimal strings.

SCOPE NOTE: this gate builds the ledger, the resolution wrapper, and the single-poll
snapshot-capture primitive -- the building blocks a future bounded multi-poll driver
would use. It does NOT build that stateful multi-poll driver loop (tracking each
overlay's pending-trigger state across real polls); the poll-K vs poll-K+1 trigger/fill
discipline is already fully proven at the pure-function level in
analysis.forensic.gateg9_managed_exit. Building an untested stateful loop under this
gate's time-boxed scope would be a half-finished implementation, which is avoided here
by design, not by oversight. See the report for the proposed next-gate command.
"""
from __future__ import annotations

import json
import os
import sqlite3
from decimal import Decimal

from analysis.forensic import gateg5_model as gm
from analysis.forensic import gateg9_managed_exit as ge
from tools import gateg5_telemetry_runner as runner
from tools import gateg6_terminal_evaluator as g6
from tools.gateg5_telemetry_runner import (
    TARGET_INTERVAL_S,
    _hl_price_feedts as _default_hl_price_feedts,
    _hl_sigma_annual as _default_hl_sigma_annual,
    _public_get as _default_public_get,
)

MANAGED_ARM_ENV = "GATEG9_MANAGED_ARM"
MANAGED_ARM_TOKEN = "MANAGED-EXIT-PAPER-CONFIRMED"


def is_armed() -> bool:
    return os.environ.get(MANAGED_ARM_ENV, "") == MANAGED_ARM_TOKEN


def _require_armed() -> None:
    if not is_armed():
        raise PermissionError(
            f"{MANAGED_ARM_ENV} != {MANAGED_ARM_TOKEN!r}. G9 UNARMED -- refusing any "
            "network I/O or DB write.")


# =============================================================================
# L. ledger separation — 5 isolated append-mostly tables; idempotent/restart-safe
# writers via the same SAVEPOINT-guarded insert-or-noop idiom used by G8.
# =============================================================================
_POSITION_COLS = ["position_id", "condition_id", "slug", "asset", "window", "selected_side",
                  "selected_token_id", "opposite_token_id", "held_qty", "entry_ask_vwap",
                  "entry_fee", "entry_cost", "entry_ts", "state", "created_ts",
                  "market_end_ts", "fee_rate"]

_SNAPSHOT_COLS = ["position_id", "condition_id", "slug", "asset", "window", "poll_seq",
                  "selected_side", "selected_token_id", "held_qty", "entry_ask_vwap",
                  "entry_fee", "entry_cost", "poll_ts_ms", "selected_capture_started_ms",
                  "selected_capture_completed_ms", "opposite_capture_started_ms",
                  "opposite_capture_completed_ms", "tte_s", "reference_age_ms",
                  "held_qty_bid_vwap", "held_qty_filled_qty", "held_qty_depth_sufficient",
                  "would_move_book", "best_bid", "total_relevant_bid_notional",
                  "fair_yes", "hl_feed_ts", "current_hold_value", "opposite_exec_ask_vwap",
                  "opposite_net_edge_diagnostic", "current_spread", "gross_return",
                  "fee_net_return"]

_EVENT_COLS = ["position_id", "overlay", "event_type", "poll_seq", "ts_ms", "payload_json"]

_TERMINAL_COLS = ["position_id", "overlay", "status", "realized_net_pnl", "net_roi", "closed_ts"]

_EXPOSURE_COLS = ["ts_ms", "open_position_count", "aggregate_paper_notional",
                  "same_direction_yes", "same_direction_no", "assets_json"]

_INT_COLS = frozenset({"entry_ts", "created_ts", "market_end_ts", "poll_seq", "poll_ts_ms",
                       "selected_capture_started_ms", "selected_capture_completed_ms",
                       "opposite_capture_started_ms", "opposite_capture_completed_ms",
                       "tte_s", "reference_age_ms", "held_qty_depth_sufficient",
                       "would_move_book", "closed_ts", "ts_ms", "open_position_count",
                       "same_direction_yes", "same_direction_no"})


def _cols_sql(cols):
    return ",".join(f"{c} INTEGER" if c in _INT_COLS else f"{c} TEXT" for c in cols)


def init_managed_ledger(conn) -> None:
    """Fresh isolated tables (TEXT/INTEGER only; never REAL; never signal_log/mark_path/S1)."""
    conn.execute(f"CREATE TABLE IF NOT EXISTS gateg9_managed_positions("
                 f"id INTEGER PRIMARY KEY, {_cols_sql(_POSITION_COLS)})")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_g9_position_condition "
                 "ON gateg9_managed_positions(condition_id)")
    conn.execute(f"CREATE TABLE IF NOT EXISTS gateg9_monitoring_snapshots("
                 f"id INTEGER PRIMARY KEY, {_cols_sql(_SNAPSHOT_COLS)})")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_g9_snapshot_poll "
                 "ON gateg9_monitoring_snapshots(position_id, poll_seq)")
    conn.execute(f"CREATE TABLE IF NOT EXISTS gateg9_overlay_events("
                 f"id INTEGER PRIMARY KEY, {_cols_sql(_EVENT_COLS)})")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_g9_event "
                 "ON gateg9_overlay_events(position_id, overlay, event_type, poll_seq)")
    conn.execute(f"CREATE TABLE IF NOT EXISTS gateg9_overlay_terminal("
                 f"id INTEGER PRIMARY KEY, {_cols_sql(_TERMINAL_COLS)})")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_g9_terminal "
                 "ON gateg9_overlay_terminal(position_id, overlay)")
    conn.execute(f"CREATE TABLE IF NOT EXISTS gateg9_concurrent_exposure_snapshots("
                 f"id INTEGER PRIMARY KEY, {_cols_sql(_EXPOSURE_COLS)})")
    conn.commit()


def _insert_or_noop(conn, table: str, cols: list, row: dict, *, created: str, exists: str) -> str:
    """SAVEPOINT-guarded idempotent insert: a UNIQUE-index collision (restart/reopen/
    reentrant write of the SAME natural key) is rolled back to the savepoint (never
    poisoning the connection) and reported as a no-op -- never a duplicate row."""
    insert_sql = (f"INSERT INTO {table}({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})")
    conn.execute("SAVEPOINT g9_write")
    try:
        conn.execute(insert_sql, tuple(row.get(c) for c in cols))
    except sqlite3.IntegrityError:
        conn.execute("ROLLBACK TO g9_write")
        conn.execute("RELEASE g9_write")
        conn.commit()
        return exists
    conn.execute("RELEASE g9_write")
    conn.commit()
    return created


def write_managed_position(conn, position: dict) -> str:
    return _insert_or_noop(conn, "gateg9_managed_positions", _POSITION_COLS, position,
                           created="CREATED", exists="ALREADY_EXISTS")


def write_monitoring_snapshot(conn, snapshot: dict) -> str:
    return _insert_or_noop(conn, "gateg9_monitoring_snapshots", _SNAPSHOT_COLS, snapshot,
                           created="RECORDED", exists="ALREADY_RECORDED")


def write_overlay_event(conn, event: dict) -> str:
    return _insert_or_noop(conn, "gateg9_overlay_events", _EVENT_COLS, event,
                           created="RECORDED", exists="ALREADY_RECORDED")


def write_overlay_terminal(conn, terminal: dict) -> str:
    """The critical restart-safe guarantee: at most ONE terminal row per
    (position_id, overlay), enforced at the SQLite level -- never a duplicate fill."""
    return _insert_or_noop(conn, "gateg9_overlay_terminal", _TERMINAL_COLS, terminal,
                           created="RECORDED", exists="ALREADY_RECORDED")


def write_concurrent_exposure_snapshot(conn, tally: dict, *, ts_ms: int) -> None:
    row = {"ts_ms": ts_ms, "open_position_count": tally["open_position_count"],
          "aggregate_paper_notional": str(tally["aggregate_paper_notional"]),
          "same_direction_yes": tally["same_direction_count"].get("YES", 0),
          "same_direction_no": tally["same_direction_count"].get("NO", 0),
          "assets_json": json.dumps(tally["assets"], separators=(",", ":"))}
    conn.execute(f"INSERT INTO gateg9_concurrent_exposure_snapshots({','.join(_EXPOSURE_COLS)}) "
                 f"VALUES ({','.join('?' for _ in _EXPOSURE_COLS)})",
                 tuple(row.get(c) for c in _EXPOSURE_COLS))
    conn.commit()


# =============================================================================
# resolution — reuses the COMMITTED G6 pure deciders (gamma_decide/clob_decide)
# unmodified; never invents a new resolution heuristic. Gamma/CLOB disagreement
# fails closed exactly as G6 itself treats it (ST_CONFLICT), mapped here to the
# managed-position vocabulary.
# =============================================================================
def resolve_selected_side(*, gamma_payload, slug: str, condition_id: str, clob_payload,
                          selected_token_id: str) -> dict:
    g_status, g_idx, g_meta = g6.gamma_decide(gamma_payload, slug, condition_id)
    if g_status != g6.ST_RESOLVED:
        return {"status": ge.RESOLUTION_PENDING, "gamma_status": g_status}
    outcomes = g_meta.get("outcomes") or []
    token_ids = g_meta.get("clobTokenIds") or []
    if not (isinstance(token_ids, list) and 0 <= g_idx < len(token_ids)):
        return {"status": ge.RESOLUTION_PENDING, "gamma_status": g6.ST_OUTCOME_AMBIGUOUS}
    gamma_winner_token = str(token_ids[g_idx])

    c_status, c_winner_token, _c_meta = g6.clob_decide(clob_payload, condition_id)
    if c_status != g6.ST_RESOLVED:
        return {"status": ge.RESOLUTION_PENDING, "clob_status": c_status}
    if gamma_winner_token != str(c_winner_token):
        return {"status": ge.GAMMA_CLOB_CONFLICT_FAIL_CLOSED}

    won = (str(selected_token_id) == gamma_winner_token)
    return {"status": "RESOLVED", "won": won, "winner_token": gamma_winner_token}


# =============================================================================
# single-poll monitoring snapshot capture — reuses the SAME timing/arm discipline as
# G8's capture_and_decide (arm-gated, sequential injected GETs, decision/poll timestamp
# stamped only after every input is available). Captures BOTH asks and bids (G8's own
# _fetch_book intentionally drops bids -- entry never needs them; exit monitoring does).
# =============================================================================
def _fetch_book_full(token_id: str, *, now_ms_provider, public_get) -> dict:
    started = now_ms_provider()
    raw = public_get(runner.CLOB_BOOK, {"token_id": token_id})
    completed = now_ms_provider()
    ts = raw.get("timestamp", completed)
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        ts = completed
    asks = sorted(((Decimal(str(lvl["price"])), Decimal(str(lvl["size"])))
                   for lvl in raw.get("asks", [])), key=lambda lv: lv[0])
    bids = sorted(((Decimal(str(lvl["price"])), Decimal(str(lvl["size"])))
                   for lvl in raw.get("bids", [])), key=lambda lv: lv[0], reverse=True)
    return {"asks": asks, "bids": bids, "quote_ts_ms": ts,
            "capture_started_ms": started, "capture_completed_ms": completed}


def capture_monitoring_snapshot(position: dict, *, poll_seq: int, now_ms_provider,
                                public_get=None, hl_price_feedts=None,
                                hl_sigma_annual=None) -> dict:
    """One bounded poll's continuous monitoring evidence for one managed position.
    HARD ARM GATE: refuses before any network call when unarmed."""
    _require_armed()
    public_get = public_get or _default_public_get
    hl_pf = hl_price_feedts or _default_hl_price_feedts
    hl_sig = hl_sigma_annual or _default_hl_sigma_annual

    held_qty = Decimal(str(position["held_qty"]))
    fee_rate = Decimal(str(position["fee_rate"]))
    entry_ask_vwap = Decimal(str(position["entry_ask_vwap"]))

    selected_book = _fetch_book_full(position["selected_token_id"], now_ms_provider=now_ms_provider,
                                     public_get=public_get)                       # GET #1
    opposite_book = _fetch_book_full(position["opposite_token_id"], now_ms_provider=now_ms_provider,
                                     public_get=public_get)                       # GET #2

    now_ms = max(selected_book["capture_completed_ms"], opposite_book["capture_completed_ms"])
    p_now, hl_feed_ts = hl_pf(position["asset"], now_ms)
    window_start_ms = (position["market_end_ts"] - TARGET_INTERVAL_S) * 1000
    strike, _ = hl_pf(position["asset"], window_start_ms)
    sigma_annual = hl_sig(position["asset"], now_ms)
    tte_s_for_fair = position["market_end_ts"] - (now_ms // 1000)
    fair_yes = None
    if tte_s_for_fair > 0:
        tte_years = Decimal(tte_s_for_fair) / gm.SECONDS_PER_YEAR
        fair_yes = gm.fair_yes_gbm(p_now, strike, sigma_annual, tte_years)

    held_fill = ge.walk_bid_ladder_for_qty(selected_book["bids"], held_qty)
    best_bid = selected_book["bids"][0][0] if selected_book["bids"] else None
    total_relevant_bid_notional = sum((p * s for p, s in selected_book["bids"]), Decimal("0"))

    opposite_exec_ask_vwap = opposite_book["asks"][0][0] if opposite_book["asks"] else None
    opposite_net_edge_diagnostic = (
        (Decimal("1") - p_now / Decimal("100000") - opposite_exec_ask_vwap)
        if opposite_exec_ask_vwap is not None else None)   # diagnostic only; never used for entry

    current_spread = (best_bid is not None and selected_book["asks"]
                      and (selected_book["asks"][0][0] - best_bid)) or None
    gross_return = ((held_fill.exec_bid_vwap - entry_ask_vwap) / entry_ask_vwap
                    if held_fill.filled_qty > 0 else None)
    exit_fee_if_now = (ge.compute_exit_fee(held_fill.filled_qty, fee_rate, held_fill.exec_bid_vwap)
                       if held_fill.filled_qty > 0 else None)
    entry_cost = Decimal(str(position["entry_cost"]))
    fee_net_return = None
    current_hold_value = held_fill.proceeds
    if held_fill.filled_qty > 0 and exit_fee_if_now is not None:
        pnl_now = ge.compute_realized_exit_pnl(bid_vwap=held_fill.exec_bid_vwap,
                                               shares_sold=held_fill.filled_qty,
                                               exit_fee=exit_fee_if_now,
                                               allocated_entry_cost=entry_cost)
        fee_net_return = pnl_now["net_roi"]
        current_hold_value = pnl_now["net_exit_proceeds"]

    poll_ts_ms = now_ms_provider()   # stamped ONLY after every input above is available
    tte_s = position["market_end_ts"] - (poll_ts_ms // 1000)
    reference_age_ms = poll_ts_ms - hl_feed_ts

    return {
        "position_id": position["position_id"], "condition_id": position["condition_id"],
        "slug": position["slug"], "asset": position["asset"], "window": position["window"],
        "poll_seq": poll_seq, "selected_side": position["selected_side"],
        "selected_token_id": position["selected_token_id"], "held_qty": str(held_qty),
        "entry_ask_vwap": str(entry_ask_vwap), "entry_fee": position["entry_fee"],
        "entry_cost": position["entry_cost"], "poll_ts_ms": poll_ts_ms,
        "selected_capture_started_ms": selected_book["capture_started_ms"],
        "selected_capture_completed_ms": selected_book["capture_completed_ms"],
        "opposite_capture_started_ms": opposite_book["capture_started_ms"],
        "opposite_capture_completed_ms": opposite_book["capture_completed_ms"],
        "tte_s": tte_s, "reference_age_ms": reference_age_ms,
        "held_qty_bid_vwap": str(held_fill.exec_bid_vwap), "held_qty_filled_qty": str(held_fill.filled_qty),
        "held_qty_depth_sufficient": int(held_fill.depth_sufficient),
        "would_move_book": int(held_fill.would_move_book),
        "best_bid": (str(best_bid) if best_bid is not None else None),
        "total_relevant_bid_notional": str(total_relevant_bid_notional),
        "fair_yes": (str(fair_yes) if fair_yes is not None else None), "hl_feed_ts": hl_feed_ts,
        "current_hold_value": str(current_hold_value),
        "opposite_exec_ask_vwap": (str(opposite_exec_ask_vwap) if opposite_exec_ask_vwap is not None else None),
        "opposite_net_edge_diagnostic": (str(opposite_net_edge_diagnostic)
                                         if opposite_net_edge_diagnostic is not None else None),
        "current_spread": (str(current_spread) if current_spread else None),
        "gross_return": (str(gross_return) if gross_return is not None else None),
        "fee_net_return": (str(fee_net_return) if fee_net_return is not None else None),
    }
