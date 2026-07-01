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

STATEFUL RUNTIME: a bounded run()/main() drives every admitted position through every
pre-registered overlay across successive polls, using the SAVEPOINT-guarded idempotent
ledger writers above for restart-safety. One overlay's advance never reads or mutates
another overlay's runtime entry. Trigger (poll K) and fill (poll K+1) remain
structurally separate calls into analysis.forensic.gateg9_managed_exit -- this module
never computes edge/fee/fill math itself, only orchestrates around it.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from decimal import Decimal

from analysis.forensic import gateg5_model as gm
from analysis.forensic import gateg7_paper_pnl as pp
from analysis.forensic import gateg9_managed_exit as ge
from tools import gateg5_telemetry_runner as runner
from tools import gateg6_terminal_evaluator as g6
from tools.gateg5_telemetry_runner import (
    TARGET_INTERVAL_S,
    _hl_price_feedts as _default_hl_price_feedts,
    _hl_sigma_annual as _default_hl_sigma_annual,
    _public_get as _default_public_get,
)
from tools.gateg8_paper_forward_capture import DEFAULT_STAKE

QUOTE_STALE_MS = pp.QUOTE_STALE_MS   # reused, never a new threshold

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
    HARD ARM GATE: refuses before any network call when unarmed. Never takes a
    resolution/outcome parameter -- monitoring decisions are structurally lookahead-free.
    """
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
    hl_capture_started_ms = now_ms_provider()
    p_now, hl_feed_ts = hl_pf(position["asset"], now_ms)
    window_start_ms = (position["market_end_ts"] - TARGET_INTERVAL_S) * 1000
    strike, _ = hl_pf(position["asset"], window_start_ms)
    sigma_annual = hl_sig(position["asset"], now_ms)
    tte_s_for_fair = position["market_end_ts"] - (now_ms // 1000)
    fair_yes = None
    if tte_s_for_fair > 0:
        tte_years = Decimal(tte_s_for_fair) / gm.SECONDS_PER_YEAR
        fair_yes = gm.fair_yes_gbm(p_now, strike, sigma_annual, tte_years)
    hl_capture_completed_ms = now_ms_provider()

    poll_ts_ms = now_ms_provider()   # stamped ONLY after every input above is available

    # ---- A.5: no-lookahead / staleness gate on every captured timestamp ----
    timing = ge.validate_monitoring_timing(
        selected_quote_ts_ms=selected_book["quote_ts_ms"],
        selected_capture_completed_ms=selected_book["capture_completed_ms"],
        opposite_quote_ts_ms=opposite_book["quote_ts_ms"],
        opposite_capture_completed_ms=opposite_book["capture_completed_ms"],
        hl_feed_ts=hl_feed_ts, hl_capture_completed_ms=hl_capture_completed_ms,
        poll_decision_ts=poll_ts_ms, quote_stale_ms=QUOTE_STALE_MS)
    if not timing["ok"]:
        return {"status": timing["status"], "field": timing["field"], "reason": timing["reason"],
               "position_id": position["position_id"], "condition_id": position["condition_id"],
               "poll_seq": poll_seq, "poll_ts_ms": poll_ts_ms}

    held_fill = ge.walk_bid_ladder_for_qty(selected_book["bids"], held_qty)
    best_bid = selected_book["bids"][0][0] if selected_book["bids"] else None
    total_relevant_bid_notional = sum((p * s for p, s in selected_book["bids"]), Decimal("0"))

    # ---- A.2: canonical opposite-side net edge -- reuses G8's OWN per-side formula
    # (pp._evaluate_side) unmodified, never a parallel fee formula or an arbitrary
    # normalization hack. fair_no = 1 - fair_yes (canonical complement, never derived
    # from a raw un-normalized price).
    opposite_leg = None
    if fair_yes is not None:
        fair_component = (Decimal("1") - fair_yes) if position["selected_side"] == "YES" else fair_yes
        fee_cfg = {"fee_rate": fee_rate, "fee_status": pp.FEE_VERIFIED_RATE}
        opposite_leg = pp._evaluate_side(fair_component, opposite_book["asks"], fee_cfg,
                                         Decimal("0"), DEFAULT_STAKE)
    opposite_exec_ask_vwap = Decimal(opposite_leg["exec_ask_vwap"]) if opposite_leg else None
    opposite_net_edge_diagnostic = opposite_leg["net_edge"] if opposite_leg else None

    current_spread = (best_bid is not None and selected_book["asks"]
                      and (selected_book["asks"][0][0] - best_bid)) or None
    gross_return = ((held_fill.exec_bid_vwap - entry_ask_vwap) / entry_ask_vwap
                    if held_fill.filled_qty > 0 else None)

    # ---- A.1: MODEL hold value vs EXECUTABLE liquidation value -- computed and
    # persisted as two structurally distinct fields; NEVER conflated or shared.
    fair_selected = None
    model_hold_value = None
    if fair_yes is not None:
        fair_selected = fair_yes if position["selected_side"] == "YES" else (Decimal("1") - fair_yes)
        model_hold_value = ge.compute_model_hold_value(fair_prob_selected_side=fair_selected,
                                                        remaining_shares=held_qty)

    entry_cost = Decimal(str(position["entry_cost"]))
    fee_net_return = None
    executable_exit_net_proceeds = None
    if held_fill.filled_qty > 0:
        exit_fee_if_now = ge.compute_exit_fee(held_fill.filled_qty, fee_rate, held_fill.exec_bid_vwap)
        pnl_now = ge.compute_realized_exit_pnl(bid_vwap=held_fill.exec_bid_vwap,
                                               shares_sold=held_fill.filled_qty,
                                               exit_fee=exit_fee_if_now,
                                               allocated_entry_cost=entry_cost)
        fee_net_return = pnl_now["net_roi"]
        executable_exit_net_proceeds = pnl_now["net_exit_proceeds"]

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
        "hl_capture_started_ms": hl_capture_started_ms,
        "hl_capture_completed_ms": hl_capture_completed_ms,
        "tte_s": tte_s, "reference_age_ms": reference_age_ms,
        "held_qty_bid_vwap": str(held_fill.exec_bid_vwap), "held_qty_filled_qty": str(held_fill.filled_qty),
        "held_qty_depth_sufficient": int(held_fill.depth_sufficient),
        "would_move_book": int(held_fill.would_move_book),
        "best_bid": (str(best_bid) if best_bid is not None else None),
        "total_relevant_bid_notional": str(total_relevant_bid_notional),
        "fair_yes": (str(fair_yes) if fair_yes is not None else None), "hl_feed_ts": hl_feed_ts,
        "model_hold_value": (str(model_hold_value) if model_hold_value is not None else None),
        "executable_exit_net_proceeds": (str(executable_exit_net_proceeds)
                                         if executable_exit_net_proceeds is not None else None),
        "opposite_exec_ask_vwap": (str(opposite_exec_ask_vwap) if opposite_exec_ask_vwap is not None else None),
        "opposite_net_edge_diagnostic": (str(opposite_net_edge_diagnostic)
                                         if opposite_net_edge_diagnostic is not None else None),
        "current_spread": (str(current_spread) if current_spread else None),
        "gross_return": (str(gross_return) if gross_return is not None else None),
        "fee_net_return": (str(fee_net_return) if fee_net_return is not None else None),
        # non-persisted (not in _SNAPSHOT_COLS, so write_monitoring_snapshot ignores these):
        # the caller's overlay-advance step reuses the SAME already-fetched bid ladder
        # (rather than a second GET) and the SAME fair_selected (rather than re-deriving it,
        # so a model-premium / entry-thesis trigger can recompute over the CURRENT residual
        # quantity, not the stale full-quantity snapshot value).
        "_selected_bids": selected_book["bids"],
        "_fair_selected": fair_selected,
    }


# =============================================================================
# PHASE B — stateful multi-poll managed vertical.
# =============================================================================
_OVERLAY_KEYS_SIMPLE = [ge.OVERLAY_HOLD_CONTROL, ge.OVERLAY_TP_15_FULL, ge.OVERLAY_TP_20_FULL,
                       ge.OVERLAY_TP_30_FULL, ge.OVERLAY_TIME_STOP_T120,
                       ge.OVERLAY_MODEL_PREMIUM_EXIT, ge.OVERLAY_ENTRY_THESIS_INVALIDATION]
_STAGED_TRANCHE_TP = [ge.OVERLAY_TP_15_FULL, ge.OVERLAY_TP_20_FULL, ge.OVERLAY_TP_30_FULL]
_STAGED_TRANCHE_KEYS = [f"{ge.OVERLAY_STAGED}#{i}" for i in range(3)]
_ALL_OVERLAY_KEYS = _OVERLAY_KEYS_SIMPLE + _STAGED_TRANCHE_KEYS

# each overlay-runtime key -> the pure trigger_kind it evaluates (staged tranches reuse
# the TP15/20/30 trigger, but each keeps its OWN isolated runtime + terminal identity).
_TRIGGER_KIND = {k: k for k in _OVERLAY_KEYS_SIMPLE}
for _i, _k in enumerate(_STAGED_TRANCHE_KEYS):
    _TRIGGER_KIND[_k] = _STAGED_TRANCHE_TP[_i]

_OVERLAY_FILLED_TERMINAL = {
    ge.OVERLAY_TP_15_FULL: ge.TP_EXIT_FILLED, ge.OVERLAY_TP_20_FULL: ge.TP_EXIT_FILLED,
    ge.OVERLAY_TP_30_FULL: ge.TP_EXIT_FILLED, ge.OVERLAY_TIME_STOP_T120: ge.TIME_STOP_FILLED,
    ge.OVERLAY_MODEL_PREMIUM_EXIT: ge.MODEL_PREMIUM_EXIT_FILLED,
    ge.OVERLAY_ENTRY_THESIS_INVALIDATION: ge.ENTRY_THESIS_INVALIDATION_FILLED,
}


# -----------------------------------------------------------------------------
# cohort admission — reads the G8 ledger (read-only), maps its PAPER_OPEN candidates
# into the G9 position shape, and delegates window arbitration to the COMMITTED
# ge.select_shared_entry_cohort (never a new selection heuristic).
# -----------------------------------------------------------------------------
def load_g8_paper_open_candidates(g8_conn) -> list:
    cols = ["condition_id", "slug", "asset", "window", "status", "selected_side",
           "selected_token_id", "yes_token_id", "no_token_id", "selected_filled_qty",
           "selected_entry_notional", "yes_exec_ask_vwap", "no_exec_ask_vwap", "fee_rate",
           "yes_net_edge", "no_net_edge", "paper_decision_ts"]
    rows = g8_conn.execute(
        f"SELECT {','.join(cols)} FROM gateg8_paper_ledger WHERE status=?", (pp.PAPER_OPEN,)).fetchall()
    return [dict(zip(cols, r)) for r in rows]


def _position_from_g8_decision(decision: dict) -> dict:
    """Maps one admitted G8 PAPER_OPEN row into a G9 managed-position row. market_end_ts
    is reconstructed EXACTLY from the window column (epoch-seconds window start) --
    never approximated from a later timestamp."""
    selected_side = decision["selected_side"]
    selected_token_id = decision["yes_token_id"] if selected_side == "YES" else decision["no_token_id"]
    opposite_token_id = decision["no_token_id"] if selected_side == "YES" else decision["yes_token_id"]
    entry_ask_vwap = Decimal(str(decision["yes_exec_ask_vwap"] if selected_side == "YES"
                                else decision["no_exec_ask_vwap"]))
    filled_qty = Decimal(str(decision["selected_filled_qty"]))
    fee_rate = Decimal(str(decision["fee_rate"]))
    cost = ge.compute_entry_cost(ask_vwap=entry_ask_vwap, filled_qty=filled_qty, fee_rate=fee_rate)
    market_end_ts = int(decision["window"]) + TARGET_INTERVAL_S
    return {
        "position_id": decision["condition_id"], "condition_id": decision["condition_id"],
        "slug": decision["slug"], "asset": decision["asset"], "window": decision["window"],
        "selected_side": selected_side, "selected_token_id": selected_token_id,
        "opposite_token_id": opposite_token_id, "held_qty": str(filled_qty),
        "entry_ask_vwap": str(entry_ask_vwap), "entry_fee": str(cost["entry_fee"]),
        "entry_cost": str(cost["entry_cost"]), "entry_ts": decision["paper_decision_ts"],
        "state": ge.STATE_PAPER_OPEN, "created_ts": decision["paper_decision_ts"],
        "market_end_ts": market_end_ts, "fee_rate": str(fee_rate),
    }


# -----------------------------------------------------------------------------
# overlay runtime — in-memory per-(position, overlay) advance state; rehydratable
# from the ledger itself so a restart can never fabricate a fill.
# -----------------------------------------------------------------------------
def _overlay_full_qty_cost(position: dict) -> dict:
    """Each overlay identity's ORIGINAL (pre-any-fill) quantity + allocated entry cost:
    the simple overlays each own the whole position; the 3 staged tranches own an exact
    1/3-with-remainder split (qtys sum to held_qty, costs sum to entry_cost)."""
    held_qty = Decimal(str(position["held_qty"]))
    entry_cost = Decimal(str(position["entry_cost"]))
    out = {k: (held_qty, entry_cost) for k in _OVERLAY_KEYS_SIMPLE}
    tranche_qtys = ge.split_into_thirds(held_qty)
    tranche_costs = ge.allocate_tranche_costs(held_qty, entry_cost, tranche_qtys)
    for i, key in enumerate(_STAGED_TRANCHE_KEYS):
        out[key] = (tranche_qtys[i], tranche_costs[i])
    return out


def _ensure_overlay_accounting(runtime: dict, full_qty: Decimal, full_cost: Decimal) -> dict:
    """Normalizes a (possibly minimal) runtime dict so it always carries residual
    accounting: the overlay's original full_qty/full_cost, the currently-held remaining
    qty + its exact remaining cost basis, and the realized PnL/proceeds accrued from any
    already-booked partial legs. Idempotent -- never overwrites values already present."""
    r = dict(runtime)
    r.setdefault("triggered_at_poll_seq", None)
    if r.get("full_qty") is None:
        r["full_qty"] = full_qty
    if r.get("full_cost") is None:
        r["full_cost"] = full_cost
    if r.get("remaining_qty") is None:
        r["remaining_qty"] = r["full_qty"]
    if r.get("remaining_cost") is None:
        r["remaining_cost"] = r["full_cost"]
    if r.get("realized_pnl_so_far") is None:
        r["realized_pnl_so_far"] = Decimal("0")
    if r.get("net_proceeds_so_far") is None:
        r["net_proceeds_so_far"] = Decimal("0")
    return r


def _fresh_overlay_runtimes() -> dict:
    return {k: {"state": ge.STATE_MONITORING, "triggered_at_poll_seq": None,
                "full_qty": None, "full_cost": None, "remaining_qty": None,
                "remaining_cost": None, "realized_pnl_so_far": Decimal("0"),
                "net_proceeds_so_far": Decimal("0")} for k in _ALL_OVERLAY_KEYS}


def rehydrate_position_overlay_runtimes(conn, position: dict) -> dict:
    """Reconstructs each overlay's runtime state from the ledger ALONE (never fabricating
    a fill from stale evidence): a terminal row means CLOSED (skip forever); otherwise the
    persisted FILL legs are replayed to recover the exact remaining qty + remaining cost
    basis + accrued realized PnL/proceeds, and the overlay is EXIT_PENDING_NEXT_POLL iff
    its latest TRIGGER poll_seq is not yet followed by a fill-attempt (FILL or NO_FILL) at
    a later poll -- else MONITORING. A partially-filled residual is thus preserved across
    a restart, never abandoned and never double-filled."""
    position_id = position["position_id"]
    qc = _overlay_full_qty_cost(position)
    out = {}
    for key in _ALL_OVERLAY_KEYS:
        full_qty, full_cost = qc[key]
        base = {"state": ge.STATE_MONITORING, "triggered_at_poll_seq": None,
                "full_qty": full_qty, "full_cost": full_cost, "remaining_qty": full_qty,
                "remaining_cost": full_cost, "realized_pnl_so_far": Decimal("0"),
                "net_proceeds_so_far": Decimal("0")}
        term = conn.execute(
            "SELECT status FROM gateg9_overlay_terminal WHERE position_id=? AND overlay=?",
            (position_id, key)).fetchone()
        if term:
            out[key] = {**base, "state": ge.STATE_PAPER_CLOSED, "remaining_qty": Decimal("0"),
                        "remaining_cost": Decimal("0")}
            continue
        legs = conn.execute(
            "SELECT poll_seq, payload_json FROM gateg9_overlay_events WHERE position_id=? AND overlay=? "
            "AND event_type='FILL' ORDER BY poll_seq", (position_id, key)).fetchall()
        realized = Decimal("0")
        proceeds = Decimal("0")
        remaining_qty, remaining_cost = full_qty, full_cost
        last_fill_seq = None
        for seq, pj in legs:
            p = json.loads(pj)
            realized += Decimal(p["realized_net_pnl"])
            proceeds += Decimal(p["net_exit_proceeds"])
            remaining_qty = Decimal(p["remaining_qty_after"])
            remaining_cost = Decimal(p["remaining_cost_after"])
            last_fill_seq = seq
        nofill = conn.execute(
            "SELECT MAX(poll_seq) FROM gateg9_overlay_events WHERE position_id=? AND overlay=? "
            "AND event_type='NO_FILL'", (position_id, key)).fetchone()
        attempt_seqs = [s for s in (last_fill_seq, (nofill[0] if nofill else None)) if s is not None]
        last_attempt_seq = max(attempt_seqs) if attempt_seqs else None
        trig = conn.execute(
            "SELECT MAX(poll_seq) FROM gateg9_overlay_events WHERE position_id=? AND overlay=? "
            "AND event_type='TRIGGER'", (position_id, key)).fetchone()
        last_trigger_seq = trig[0] if trig else None
        state = ge.STATE_MONITORING
        triggered_at = None
        if last_trigger_seq is not None and (last_attempt_seq is None or last_trigger_seq > last_attempt_seq):
            state = ge.STATE_EXIT_PENDING_NEXT_POLL
            triggered_at = last_trigger_seq
        out[key] = {**base, "state": state, "triggered_at_poll_seq": triggered_at,
                    "remaining_qty": remaining_qty, "remaining_cost": remaining_cost,
                    "realized_pnl_so_far": realized, "net_proceeds_so_far": proceeds}
    return out


def _next_poll_seq(conn, position_id: str) -> int:
    row = conn.execute("SELECT MAX(poll_seq) FROM gateg9_monitoring_snapshots WHERE position_id=?",
                      (position_id,)).fetchone()
    return (row[0] or 0) + 1


def write_managed_position_state(conn, position_id: str, new_state: str) -> None:
    conn.execute("UPDATE gateg9_managed_positions SET state=? WHERE condition_id=?",
                (new_state, position_id))
    conn.commit()


# -----------------------------------------------------------------------------
# one overlay, one poll — trigger (poll K) OR fill (poll K+1), never both in one call,
# never contaminating another overlay's runtime entry.
# -----------------------------------------------------------------------------
def _advance_overlay_one_poll(conn, *, position: dict, overlay_key: str, trigger_kind: str,
                              snap: dict, runtime: dict, full_qty: Decimal, full_cost: Decimal,
                              fee_rate: Decimal) -> dict:
    runtime = _ensure_overlay_accounting(runtime, full_qty, full_cost)
    if runtime["state"] == ge.STATE_PAPER_CLOSED:
        return runtime
    poll_seq = snap["poll_seq"]
    ts_ms = snap["poll_ts_ms"]
    bid_levels = snap["_selected_bids"]

    if runtime["state"] == ge.STATE_EXIT_PENDING_NEXT_POLL:
        # this poll IS poll K+1 relative to the trigger recorded at
        # runtime["triggered_at_poll_seq"] -- the fill uses ONLY this poll's ladder, and
        # only the CURRENT residual (qty + exact cost basis) is offered.
        fill = ge.execute_exit_fill(requested_qty=runtime["remaining_qty"], next_bid_levels=bid_levels,
                                    fee_rate=fee_rate, remaining_allocated_cost=runtime["remaining_cost"])
        if fill["status"] == ge.FILL_NONE:
            # zero depth at K+1: nothing sold. Return to MONITORING so the residual can
            # re-trigger and re-attempt on a later poll -- never a terminal close.
            write_overlay_event(conn, {"position_id": position["position_id"], "overlay": overlay_key,
                                       "event_type": "NO_FILL", "poll_seq": poll_seq, "ts_ms": ts_ms,
                                       "payload_json": json.dumps(
                                           {"status": ge.FILL_NONE,
                                            "residual": str(fill["remaining_qty_after"])})})
            return {**runtime, "state": ge.STATE_MONITORING, "triggered_at_poll_seq": None}

        # a real leg (partial or full): persist it and accrue its realized PnL/proceeds.
        write_overlay_event(conn, {"position_id": position["position_id"], "overlay": overlay_key,
                                   "event_type": "FILL", "poll_seq": poll_seq, "ts_ms": ts_ms,
                                   "payload_json": json.dumps({
                                       "status": fill["status"], "filled_qty": str(fill["filled_qty"]),
                                       "exec_bid_vwap": str(fill["bid_fill"].exec_bid_vwap),
                                       "exit_fee": str(fill["exit_fee"]),
                                       "net_exit_proceeds": str(fill["net_exit_proceeds"]),
                                       "leg_cost": str(fill["leg_cost"]),
                                       "realized_net_pnl": str(fill["realized_net_pnl"]),
                                       "remaining_qty_after": str(fill["remaining_qty_after"]),
                                       "remaining_cost_after": str(fill["remaining_cost_after"])})})
        new_realized = runtime["realized_pnl_so_far"] + fill["realized_net_pnl"]
        new_proceeds = runtime["net_proceeds_so_far"] + fill["net_exit_proceeds"]
        if fill["status"] == ge.FILL_FILLED:
            # the whole residual is now sold across one or more legs -> close, booking the
            # AGGREGATE realized PnL (all legs) and ROI over the overlay's original cost.
            net_roi = (new_realized / full_cost) if full_cost > 0 else None
            write_overlay_terminal(conn, {"position_id": position["position_id"], "overlay": overlay_key,
                                          "status": _OVERLAY_FILLED_TERMINAL[trigger_kind],
                                          "realized_net_pnl": str(new_realized),
                                          "net_roi": (str(net_roi) if net_roi is not None else None),
                                          "closed_ts": ts_ms})
            return {**runtime, "state": ge.STATE_PAPER_CLOSED, "triggered_at_poll_seq": None,
                    "remaining_qty": Decimal("0"), "remaining_cost": Decimal("0"),
                    "realized_pnl_so_far": new_realized, "net_proceeds_so_far": new_proceeds}
        # PARTIAL_FILL: conserve the residual (exact qty + cost), write NO terminal row,
        # and return to MONITORING so the residual can re-trigger on a later poll.
        return {**runtime, "state": ge.STATE_MONITORING, "triggered_at_poll_seq": None,
                "remaining_qty": fill["remaining_qty_after"], "remaining_cost": fill["remaining_cost_after"],
                "realized_pnl_so_far": new_realized, "net_proceeds_so_far": new_proceeds}

    # STATE_MONITORING -> evaluate this overlay's OWN trigger condition against THIS poll's
    # (K's) evidence only, over the CURRENT residual qty/cost; never returns/writes a fill.
    qty = runtime["remaining_qty"]
    cost = runtime["remaining_cost"]
    if trigger_kind == ge.OVERLAY_HOLD_CONTROL:
        return runtime   # the control never exits early; settled only at resolution
    if trigger_kind in ge.TP_PCTS:
        trig = ge.evaluate_tp_trigger(trigger_kind, held_qty=qty, bid_levels=bid_levels,
                                      fee_rate=fee_rate, allocated_entry_cost=cost)
        triggered = trig["triggered"]
    elif trigger_kind == ge.OVERLAY_TIME_STOP_T120:
        triggered = ge.evaluate_time_stop_trigger(snap.get("tte_s"))
    elif trigger_kind == ge.OVERLAY_MODEL_PREMIUM_EXIT:
        fair_sel = snap.get("_fair_selected")
        if fair_sel is None:
            return runtime   # no model value available this poll -- stay MONITORING
        # model hold value is recomputed over the CURRENT residual `qty` inside the trigger
        trig = ge.evaluate_model_premium_exit_trigger(held_qty=qty, bid_levels=bid_levels,
                                                       fee_rate=fee_rate, fair_prob_selected_side=fair_sel)
        triggered = trig["triggered"]
    elif trigger_kind == ge.OVERLAY_ENTRY_THESIS_INVALIDATION:
        fair_sel = snap.get("_fair_selected")
        if fair_sel is None:
            return runtime   # no model value available this poll -- stay MONITORING
        # residual cost basis = the overlay's CURRENT remaining allocated entry cost
        # (fixed per-share basis * residual shares); prior realized proceeds are never
        # netted into it.
        trig = ge.evaluate_entry_thesis_invalidation_trigger(
            remaining_shares=qty, fair_prob_selected_side=fair_sel,
            remaining_allocated_entry_cost=cost)
        triggered = trig["triggered"]
    else:
        raise ge.ManagedExitError(f"unknown overlay trigger_kind {trigger_kind!r}")

    if triggered:
        write_overlay_event(conn, {"position_id": position["position_id"], "overlay": overlay_key,
                                   "event_type": "TRIGGER", "poll_seq": poll_seq, "ts_ms": ts_ms,
                                   "payload_json": json.dumps({})})
        return {**runtime, "state": ge.STATE_EXIT_PENDING_NEXT_POLL, "triggered_at_poll_seq": poll_seq}
    return runtime


def advance_position_one_poll(conn, position: dict, *, poll_seq: int, now_ms_provider,
                              public_get=None, hl_price_feedts=None, hl_sigma_annual=None,
                              overlay_runtimes: dict) -> dict:
    """One bounded poll for ONE managed position: captures+persists the monitoring
    snapshot, then advances every pre-registered overlay (including all 3 STAGED
    tranches) by exactly one poll over its CURRENT residual. `overlay_runtimes` is
    mutated in place; the caller owns it (fresh via _fresh_overlay_runtimes or rehydrated
    via rehydrate_position_overlay_runtimes on --resume)."""
    snap = capture_monitoring_snapshot(position, poll_seq=poll_seq, now_ms_provider=now_ms_provider,
                                       public_get=public_get, hl_price_feedts=hl_price_feedts,
                                       hl_sigma_annual=hl_sigma_annual)
    write_monitoring_snapshot(conn, snap)
    if snap.get("status") == ge.MONITORING_TIMESTAMP_REJECTED:
        return snap

    fee_rate = Decimal(str(position["fee_rate"]))
    qc = _overlay_full_qty_cost(position)
    for key in _ALL_OVERLAY_KEYS:
        full_qty, full_cost = qc[key]
        overlay_runtimes[key] = _advance_overlay_one_poll(
            conn, position=position, overlay_key=key, trigger_kind=_TRIGGER_KIND[key], snap=snap,
            runtime=overlay_runtimes[key], full_qty=full_qty, full_cost=full_cost, fee_rate=fee_rate)
    # if all 3 staged tranches have closed via fills (before any resolution), reconcile the
    # aggregate now; a no-op until every tranche is terminal, idempotent thereafter.
    _maybe_write_staged_aggregate(conn, position, closed_ts=snap["poll_ts_ms"])
    return snap


def finalize_position_at_resolution(conn, position: dict, *, overlay_runtimes: dict,
                                    resolution: dict, closed_ts: int) -> None:
    """Settles EVERY not-yet-closed overlay identity (simple + 3 staged tranches) at
    market resolution. Any overlay still holding a residual (never triggered, triggered
    but never reached a K+1 fill, OR partially filled and re-monitoring) settles that
    residual FEE-FREE: payout = residual_qty * (1 or 0), residual PnL = payout -
    remaining allocated entry cost (compute_resolution_pnl has NO fee parameter). The
    overlay's terminal realized PnL is the AGGREGATE of every already-booked partial leg
    plus this residual settlement -- so no share, cost, or fee ever disappears. Status is
    RESOLVED_HOLD when the full original quantity was held to resolution, RESOLVED_RESIDUAL
    when part was sold earlier. A Gamma/CLOB conflict fails every overlay closed with a
    null PnL (no winner to settle against). Marks the position PAPER_CLOSED, then writes
    the staged aggregate. Idempotent via the unique terminal/event indexes."""
    qc = _overlay_full_qty_cost(position)
    conflict = resolution.get("status") == ge.GAMMA_CLOB_CONFLICT_FAIL_CLOSED
    won = resolution.get("won")

    for key in _ALL_OVERLAY_KEYS:
        full_qty, full_cost = qc[key]
        rt = _ensure_overlay_accounting(overlay_runtimes[key], full_qty, full_cost)
        overlay_runtimes[key] = rt
        if rt["state"] == ge.STATE_PAPER_CLOSED:
            continue
        if conflict:
            write_overlay_terminal(conn, {"position_id": position["position_id"], "overlay": key,
                                          "status": ge.GAMMA_CLOB_CONFLICT_FAIL_CLOSED,
                                          "realized_net_pnl": None, "net_roi": None,
                                          "closed_ts": closed_ts})
            overlay_runtimes[key] = {**rt, "state": ge.STATE_PAPER_CLOSED}
            continue
        remaining_qty = rt["remaining_qty"]
        remaining_cost = rt["remaining_cost"]
        res = ge.compute_resolution_pnl(remaining_shares=remaining_qty, won=won,
                                        allocated_entry_cost=remaining_cost)
        aggregate = rt["realized_pnl_so_far"] + res["realized_net_pnl"]
        net_roi = (aggregate / full_cost) if full_cost > 0 else None
        # forensic: the settlement leg pays ZERO taker/exit fee (structurally guaranteed --
        # compute_resolution_pnl has no fee parameter -- and recorded explicitly here).
        write_overlay_event(conn, {"position_id": position["position_id"], "overlay": key,
                                   "event_type": "RESOLUTION_SETTLE", "poll_seq": 0, "ts_ms": closed_ts,
                                   "payload_json": json.dumps({
                                       "residual_qty": str(remaining_qty), "payout": str(res["payout"]),
                                       "remaining_cost": str(remaining_cost),
                                       "residual_net_pnl": str(res["realized_net_pnl"]),
                                       "exit_fee": "0"})})
        status = ge.RESOLVED_HOLD if remaining_qty == full_qty else ge.RESOLVED_RESIDUAL
        write_overlay_terminal(conn, {"position_id": position["position_id"], "overlay": key,
                                      "status": status, "realized_net_pnl": str(aggregate),
                                      "net_roi": (str(net_roi) if net_roi is not None else None),
                                      "closed_ts": closed_ts})
        overlay_runtimes[key] = {**rt, "state": ge.STATE_PAPER_CLOSED,
                                 "remaining_qty": Decimal("0"), "remaining_cost": Decimal("0")}

    write_managed_position_state(conn, position["position_id"], ge.STATE_PAPER_CLOSED)
    _maybe_write_staged_aggregate(conn, position, closed_ts=closed_ts)


def _maybe_write_staged_aggregate(conn, position: dict, *, closed_ts: int) -> str:
    """Once ALL 3 staged tranche terminal rows exist (whether they closed via fills or at
    resolution), reconcile them into ONE persisted aggregate terminal row (overlay ==
    OVERLAY_STAGED): combined net PnL = exact sum of the tranche PnLs, ROI over the
    ORIGINAL full entry cost (never an average of tranche ROIs). No-op ('INCOMPLETE')
    until every tranche is terminal; idempotent via the unique terminal index thereafter.
    A tranche with a null PnL (Gamma/CLOB conflict) yields a null aggregate, still written
    exactly once."""
    position_id = position["position_id"]
    pnls = []
    for key in _STAGED_TRANCHE_KEYS:
        row = conn.execute("SELECT realized_net_pnl FROM gateg9_overlay_terminal "
                           "WHERE position_id=? AND overlay=?", (position_id, key)).fetchone()
        if row is None:
            return "INCOMPLETE"
        pnls.append(Decimal(row[0]) if row[0] is not None else None)
    agg = ge.combine_staged_tranche_pnls(pnls, Decimal(str(position["entry_cost"])))
    combined = agg["combined_net_pnl"]
    roi = agg["aggregate_roi"]
    return write_overlay_terminal(conn, {
        "position_id": position_id, "overlay": ge.OVERLAY_STAGED, "status": ge.STAGED_AGGREGATE,
        "realized_net_pnl": (str(combined) if combined is not None else None),
        "net_roi": (str(roi) if roi is not None else None), "closed_ts": closed_ts})


def build_position_telegram_report(conn, position_id: str) -> str:
    """Reads back the position + every overlay terminal row + the latest concurrent-
    exposure snapshot and delegates formatting to the COMMITTED pure formatter. The 3 raw
    staged tranche rows (OVERLAY_STAGED#0/#1/#2) are collapsed away in favour of the single
    reconciled staged aggregate row so the report never double-counts staged PnL."""
    prow = conn.execute(
        "SELECT asset, window, selected_side, entry_ask_vwap, held_qty, entry_fee "
        "FROM gateg9_managed_positions WHERE condition_id=?", (position_id,)).fetchone()
    position = {"asset": prow[0], "window": prow[1], "selected_side": prow[2],
               "entry_ask_vwap": prow[3], "held_qty": prow[4], "entry_fee": prow[5]}
    terms = conn.execute(
        "SELECT overlay, status, realized_net_pnl FROM gateg9_overlay_terminal "
        "WHERE position_id=?", (position_id,)).fetchall()
    tranche_prefix = ge.OVERLAY_STAGED + "#"
    overlay_terminals = {r[0]: {"status": r[1], "realized_net_pnl": r[2]}
                         for r in terms if not r[0].startswith(tranche_prefix)}
    exp_row = conn.execute(
        "SELECT open_position_count, aggregate_paper_notional FROM gateg9_concurrent_exposure_snapshots "
        "ORDER BY id DESC LIMIT 1").fetchone()
    concurrent_exposure = ({"open_position_count": exp_row[0], "aggregate_paper_notional": exp_row[1]}
                           if exp_row else {"open_position_count": 0, "aggregate_paper_notional": "0"})
    return ge.format_telegram_report(position=position, overlay_terminals=overlay_terminals,
                                     concurrent_exposure=concurrent_exposure)


# -----------------------------------------------------------------------------
# bounded driver — explicit positive bounds, monotonic elapsed stop, /tmp-restricted
# DB, refuses a pre-existing artifact unless --resume, operator-abort clean exit.
# -----------------------------------------------------------------------------
def _require_positive_env_int(name: str) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        raise PermissionError(f"{name} must be set explicitly (no default) to run the G9 driver")
    try:
        value = int(raw)
    except ValueError:
        raise PermissionError(f"{name} must be an integer, got {raw!r}") from None
    if value <= 0:
        raise PermissionError(f"{name} must be a positive integer, got {value!r}")
    return value


def run(db_path: str, g8_db_path: str, *, resume: bool = False,
       now_ms_provider=lambda: int(time.time() * 1000), monotonic_provider=time.monotonic,
       abort_check=None, public_get=None, hl_price_feedts=None, hl_sigma_annual=None,
       gamma_fetch=None, clob_fetch=None) -> dict:
    """Bounded managed-position paper driver (PAPER/SHADOW ONLY; NO orders). Requires
    GATEG9_MANAGED_ARM + GATEG9_MAX_OBSERVATIONS + GATEG9_MAX_ELAPSED_S +
    GATEG9_POLL_INTERVAL_S explicitly set to POSITIVE integers -- fails closed before
    any network call or DB creation/write otherwise. Admits the G8-positive post-fee
    entry cohort (one per correlated 15m window, via the COMMITTED
    ge.select_shared_entry_cohort), then advances every open position's every overlay
    one poll per cycle until MAX_OBSERVATIONS or monotonic MAX_ELAPSED_S. Operator abort
    (runner._ABORT_REQUESTED) exits the loop cleanly at the next safe boundary --
    already-persisted paper state is never rolled back."""
    _require_armed()
    max_observations = _require_positive_env_int("GATEG9_MAX_OBSERVATIONS")
    max_elapsed_s = _require_positive_env_int("GATEG9_MAX_ELAPSED_S")
    poll_interval_s = _require_positive_env_int("GATEG9_POLL_INTERVAL_S")

    if abort_check is None:
        abort_check = lambda: runner._ABORT_REQUESTED   # noqa: E731

    runner._require_under_tmp(db_path, "DB")
    if resume:
        if not os.path.lexists(db_path):
            raise PermissionError(f"--resume requires an existing ledger DB: {db_path!r}")
    else:
        runner._refuse_existing(db_path, "DB")

    conn = sqlite3.connect(db_path)
    init_managed_ledger(conn)   # idempotent; harmless re-create on --resume

    g8_conn = sqlite3.connect(f"file:{g8_db_path}?mode=ro", uri=True)
    try:
        candidates = load_g8_paper_open_candidates(g8_conn)
    finally:
        g8_conn.close()
    cohort = ge.select_shared_entry_cohort(candidates)
    admitted = [c for c in cohort if c.get("status") == pp.PAPER_OPEN]

    public_get = public_get or _default_public_get
    hl_pf = hl_price_feedts or _default_hl_price_feedts
    hl_sig = hl_sigma_annual or _default_hl_sigma_annual
    gamma_fetch = gamma_fetch or g6.gamma_fetch_live
    clob_fetch = clob_fetch or g6.clob_fetch_live

    positions = {}
    overlay_runtimes = {}
    poll_seqs = {}
    for cand in admitted:
        position = _position_from_g8_decision(cand)
        pid = position["position_id"]
        write_managed_position(conn, position)
        positions[pid] = position
        if resume:
            overlay_runtimes[pid] = rehydrate_position_overlay_runtimes(conn, position)
            poll_seqs[pid] = _next_poll_seq(conn, pid)
        else:
            overlay_runtimes[pid] = _fresh_overlay_runtimes()
            poll_seqs[pid] = 1

    start_mono = monotonic_provider()
    observations = 0
    stop_reason = "UNSET"

    while True:
        elapsed_s = int(monotonic_provider() - start_mono)
        if abort_check():
            stop_reason = "OPERATOR_ABORT"
            break
        if observations >= max_observations:
            stop_reason = "MAX_OBSERVATIONS"
            break
        if elapsed_s >= max_elapsed_s:
            stop_reason = "MAX_ELAPSED"
            break
        if not positions:
            stop_reason = "NO_OPEN_POSITIONS"
            break

        now_ms = now_ms_provider()
        for pid, position in list(positions.items()):
            if position["market_end_ts"] <= (now_ms // 1000):
                try:
                    g_payload = gamma_fetch(position["slug"], position["condition_id"])
                    c_payload = clob_fetch(position["condition_id"])
                    resolution = resolve_selected_side(
                        gamma_payload=g_payload, slug=position["slug"],
                        condition_id=position["condition_id"], clob_payload=c_payload,
                        selected_token_id=position["selected_token_id"])
                except Exception:                       # noqa: BLE001 -- fail closed, keep polling
                    resolution = {"status": ge.RESOLUTION_PENDING}
                if resolution["status"] in ("RESOLVED", ge.GAMMA_CLOB_CONFLICT_FAIL_CLOSED):
                    finalize_position_at_resolution(conn, position, overlay_runtimes=overlay_runtimes[pid],
                                                    resolution=resolution, closed_ts=now_ms)
                    del positions[pid]
                    continue
            poll_seq = poll_seqs[pid]
            advance_position_one_poll(conn, position, poll_seq=poll_seq, now_ms_provider=now_ms_provider,
                                      public_get=public_get, hl_price_feedts=hl_pf,
                                      hl_sigma_annual=hl_sig, overlay_runtimes=overlay_runtimes[pid])
            poll_seqs[pid] = poll_seq + 1
            observations += 1

        tally = ge.tally_concurrent_exposure([
            {"selected_side": p["selected_side"], "asset": p["asset"],
            "entry_cost": Decimal(p["entry_cost"])} for p in positions.values()])
        write_concurrent_exposure_snapshot(conn, tally, ts_ms=now_ms)

        if stop_reason == "OPERATOR_ABORT":
            break
        time.sleep(poll_interval_s)

    conn.close()
    return {"stop_reason": stop_reason, "observations": observations, "db_path": db_path,
           "open_positions_remaining": len(positions)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Gate G9 bounded managed-position paper driver (PAPER/SHADOW ONLY; no orders).")
    parser.add_argument("--db", required=True, help="SQLite path for the isolated G9 managed ledger")
    parser.add_argument("--g8-db", required=True, help="Path to the G8 paper ledger to admit candidates from")
    parser.add_argument("--resume", action="store_true",
                       help="Reopen an existing G9 ledger and rehydrate open positions/overlays")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if not is_armed():
        sys.stderr.write(
            f"[GUARD] {MANAGED_ARM_ENV} != {MANAGED_ARM_TOKEN!r}. G9 driver UNARMED -- refusing "
            "any network I/O or DB write. No fetch, no DB, no loop.\n")
        return 2
    runner._install_signal_handlers()
    try:
        result = run(args.db, args.g8_db, resume=args.resume)
    except PermissionError as e:
        sys.stderr.write(f"[GUARD] refusing to run: {e}\n")
        return 2
    sys.stderr.write(f"[gateg9] done: {result}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
