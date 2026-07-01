"""
Gate G9 — Managed Position / Exit Overlays (PURE module).

Extends the committed G8 dual-book PAPER_OPEN entry primitive into a managed-position
paper experiment: a shared entry cohort (one selected candidate per 15m window), a
deterministic PAPER_OPEN -> MONITORING -> EXIT_TRIGGERED -> EXIT_PENDING_NEXT_POLL ->
PAPER_CLOSED lifecycle, and seven pre-registered exit overlays evaluated on the SAME
entry set: HOLD_CONTROL (the control), TP_15/20/30_FULL, TIME_STOP_T120,
EDGE_INVALIDATION, and STAGED_15_20_30_COUNTERFACTUAL (measurement only).

PAPER/SHADOW ONLY. Pure: no network, no DB, no clock, no orders/wallet/signing/capital.
Reuses committed formulas rather than duplicating them: pp.entry_fee_quadratic for BOTH
entry and exit fees (same canonical quadratic fee schedule on both legs of a taker
order), pp.window_of for 15m-window grouping. Never mutates a caller-supplied dict.

Trigger/fill discipline (never violated): a trigger is evaluated on poll K's ALREADY-
captured bid evidence and never returns a fill status; a fill exists ONLY via
execute_full_exit_fill, which takes poll K+1's bid ladder as its own explicit parameter
-- there is no code path that lets a trigger's poll-K evidence become a fill price.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from analysis.forensic import gateg7_paper_pnl as pp

# --- managed-position lifecycle states ---
STATE_PAPER_OPEN = "PAPER_OPEN"
STATE_MONITORING = "MONITORING"
STATE_EXIT_TRIGGERED = "EXIT_TRIGGERED"
STATE_EXIT_PENDING_NEXT_POLL = "EXIT_PENDING_NEXT_POLL"
STATE_PAPER_CLOSED = "PAPER_CLOSED"

# --- terminal / fail-closed statuses (never conflate a trigger with a fill) ---
RESOLVED_HOLD = "RESOLVED_HOLD"
TP_EXIT_FILLED = "TP_EXIT_FILLED"
TIME_STOP_FILLED = "TIME_STOP_FILLED"
EDGE_INVALIDATION_FILLED = "EDGE_INVALIDATION_FILLED"
EXIT_DEPTH_INSUFFICIENT = "EXIT_DEPTH_INSUFFICIENT"
EXIT_NO_NEXT_POLL = "EXIT_NO_NEXT_POLL"
RESOLUTION_PENDING = "RESOLUTION_PENDING"
CAPTURE_FAILED = "CAPTURE_FAILED"
GAMMA_CLOB_CONFLICT_FAIL_CLOSED = "GAMMA_CLOB_CONFLICT_FAIL_CLOSED"

# --- pre-registered overlays ---
OVERLAY_HOLD_CONTROL = "HOLD_CONTROL"
OVERLAY_TP_15_FULL = "TP_15_FULL"
OVERLAY_TP_20_FULL = "TP_20_FULL"
OVERLAY_TP_30_FULL = "TP_30_FULL"
OVERLAY_TIME_STOP_T120 = "TIME_STOP_T120"
OVERLAY_EDGE_INVALIDATION = "EDGE_INVALIDATION"
OVERLAY_STAGED = "STAGED_15_20_30_COUNTERFACTUAL"
ALL_OVERLAYS = (OVERLAY_HOLD_CONTROL, OVERLAY_TP_15_FULL, OVERLAY_TP_20_FULL, OVERLAY_TP_30_FULL,
                OVERLAY_TIME_STOP_T120, OVERLAY_EDGE_INVALIDATION, OVERLAY_STAGED)

TP_PCTS = {OVERLAY_TP_15_FULL: Decimal("0.15"), OVERLAY_TP_20_FULL: Decimal("0.20"),
          OVERLAY_TP_30_FULL: Decimal("0.30")}

CORRELATED_WINDOW_SKIPPED = "CORRELATED_WINDOW_SKIPPED"

TIME_STOP_TTE_S = 120


class ManagedExitError(Exception):
    """Malformed managed-position input -- fail closed, never guessed."""


# ===========================================================================
# B. shared entry cohort — one selected PAPER_OPEN per 15m window, chosen by the
# highest strictly-positive post-fee net edge (the committed G8 selection rule is
# reused unmodified; this only arbitrates ACROSS correlated same-window candidates).
# ===========================================================================
def selected_net_edge(decision: dict):
    side = decision.get("selected_side")
    if side == "YES":
        raw = decision.get("yes_net_edge")
    elif side == "NO":
        raw = decision.get("no_net_edge")
    else:
        return None
    return pp._d(raw)


def select_shared_entry_cohort(decisions: list) -> list:
    """Groups PAPER_OPEN rows by 15m window (pp.window_of(slug)); keeps only the single
    highest-net-edge PAPER_OPEN per window, downgrading the rest to
    CORRELATED_WINDOW_SKIPPED (evidence preserved, never discarded). Non-PAPER_OPEN rows
    pass through completely untouched -- every mechanically valid candidate is preserved
    for later threshold bucketing; nothing is hard-filtered here."""
    by_window: dict[str, list[dict]] = {}
    passthrough = []
    for d in decisions:
        if d.get("status") != pp.PAPER_OPEN:
            passthrough.append(d)
            continue
        w = d.get("window") or pp.window_of(d.get("slug"))
        by_window.setdefault(w, []).append(d)

    out = list(passthrough)
    for _window, rows in by_window.items():
        ranked = sorted(rows, key=lambda r: (selected_net_edge(r) is None, selected_net_edge(r)),
                        reverse=True)
        winner = ranked[0]
        out.append(winner)
        for loser in ranked[1:]:
            skipped = dict(loser)
            skipped["status"] = CORRELATED_WINDOW_SKIPPED
            out.append(skipped)
    return out


# ===========================================================================
# entry cost — reuses the COMMITTED quadratic fee formula (never a new fee formula)
# ===========================================================================
def compute_entry_cost(*, ask_vwap: Decimal, filled_qty: Decimal, fee_rate: Decimal) -> dict:
    entry_fee = pp.entry_fee_quadratic(filled_qty, fee_rate, ask_vwap)
    entry_notional = ask_vwap * filled_qty
    return {"entry_fee": entry_fee, "entry_notional": entry_notional,
            "entry_cost": entry_notional + entry_fee}


# ===========================================================================
# qty-clamped bid-ladder walk (exit side) — symmetric counterpart to the committed
# stake-clamped walk_ask_ladder_for_stake (entry side), but clamped on SHARE QUANTITY
# rather than dollar stake. `levels` must already be best-bid-first (descending).
# ===========================================================================
@dataclass
class BidFill:
    filled_qty: Decimal
    proceeds: Decimal            # gross USD received (before fee), <= requested qty * best bid
    exec_bid_vwap: Decimal
    depth_sufficient: bool       # True iff the FULL requested qty was absorbed
    residual_unfilled_qty: Decimal
    levels_used: int
    would_move_book: bool        # True iff more than the best bid level was needed


def walk_bid_ladder_for_qty(levels, qty: Decimal) -> BidFill:
    remaining = qty
    filled = Decimal("0")
    proceeds = Decimal("0")
    levels_used = 0
    for price, size in levels:
        if remaining <= 0:
            break
        levels_used += 1
        take = min(size, remaining)
        filled += take
        proceeds += take * price
        remaining -= take
    vwap = (proceeds / filled) if filled > 0 else Decimal("0")
    return BidFill(filled_qty=filled, proceeds=proceeds, exec_bid_vwap=vwap,
                   depth_sufficient=(remaining == 0), residual_unfilled_qty=remaining,
                   levels_used=levels_used, would_move_book=(levels_used > 1))


# ===========================================================================
# fees / PnL — Decimal throughout; exit fee reuses the SAME canonical quadratic
# formula as entry (pp.entry_fee_quadratic), never a new fee formula.
# ===========================================================================
def compute_exit_fee(shares_sold: Decimal, fee_rate: Decimal, exit_price: Decimal) -> Decimal:
    return pp.entry_fee_quadratic(shares_sold, fee_rate, exit_price)


def compute_realized_exit_pnl(*, bid_vwap: Decimal, shares_sold: Decimal, exit_fee: Decimal,
                              allocated_entry_cost: Decimal) -> dict:
    net_exit_proceeds = bid_vwap * shares_sold - exit_fee
    realized_net_pnl = net_exit_proceeds - allocated_entry_cost
    net_roi = (realized_net_pnl / allocated_entry_cost) if allocated_entry_cost > 0 else None
    return {"net_exit_proceeds": net_exit_proceeds, "realized_net_pnl": realized_net_pnl,
            "net_roi": net_roi}


def compute_resolution_pnl(*, remaining_shares: Decimal, won: bool,
                           allocated_entry_cost: Decimal) -> dict:
    payout = remaining_shares * (Decimal("1") if won else Decimal("0"))
    realized_net_pnl = payout - allocated_entry_cost
    net_roi = (realized_net_pnl / allocated_entry_cost) if allocated_entry_cost > 0 else None
    return {"payout": payout, "realized_net_pnl": realized_net_pnl, "net_roi": net_roi}


# ===========================================================================
# TP reachability — persisted separately; an unreachable TP on a high entry price is a
# LABEL, never evidence the strategy "failed".
# ===========================================================================
def gross_tp_target_price(entry_price: Decimal, tp_pct: Decimal) -> Decimal:
    return entry_price * (Decimal("1") + tp_pct)


def gross_tp_reachable(target_price: Decimal) -> bool:
    return target_price <= Decimal("1.00")


# ===========================================================================
# G.2-4 — TP trigger (poll K only; NEVER returns a fill "status")
# ===========================================================================
def evaluate_tp_trigger(overlay_name: str, *, held_qty: Decimal, bid_levels, fee_rate: Decimal,
                        allocated_entry_cost: Decimal) -> dict:
    """Trigger-only: walks poll K's FULL-held-quantity bid evidence and checks whether the
    OBSERVED executable fee-net ROI already meets the overlay's TP threshold. Depth-
    insufficient poll-K evidence never fabricates a trigger. Never returns a fill status --
    the actual fill happens only via execute_full_exit_fill on poll K+1."""
    tp_pct = TP_PCTS[overlay_name]
    fill = walk_bid_ladder_for_qty(bid_levels, held_qty)
    if not fill.depth_sufficient:
        return {"triggered": False, "depth_sufficient": False, "bid_fill": fill}
    exit_fee = compute_exit_fee(fill.filled_qty, fee_rate, fill.exec_bid_vwap)
    pnl = compute_realized_exit_pnl(bid_vwap=fill.exec_bid_vwap, shares_sold=fill.filled_qty,
                                    exit_fee=exit_fee, allocated_entry_cost=allocated_entry_cost)
    triggered = pnl["net_roi"] is not None and pnl["net_roi"] >= tp_pct
    return {"triggered": triggered, "depth_sufficient": True, "bid_fill": fill,
            "exit_fee": exit_fee, **pnl}


def evaluate_time_stop_trigger(tte_s) -> bool:
    return tte_s is not None and tte_s <= TIME_STOP_TTE_S


def evaluate_edge_invalidation_trigger(*, held_qty: Decimal, bid_levels, fee_rate: Decimal,
                                       model_hold_value: Decimal) -> dict:
    """Trigger-only (poll K): records BOTH the current model-estimated hold value and the
    immediate fee-net executable exit value; triggers when exit value already >= hold
    value. Never returns a fill status."""
    fill = walk_bid_ladder_for_qty(bid_levels, held_qty)
    if not fill.depth_sufficient:
        return {"triggered": False, "depth_sufficient": False, "bid_fill": fill,
                "model_hold_value": model_hold_value}
    exit_fee = compute_exit_fee(fill.filled_qty, fee_rate, fill.exec_bid_vwap)
    fee_net_exit_value = fill.proceeds - exit_fee
    triggered = fee_net_exit_value >= model_hold_value
    return {"triggered": triggered, "depth_sufficient": True, "bid_fill": fill,
            "exit_fee": exit_fee, "fee_net_exit_value": fee_net_exit_value,
            "model_hold_value": model_hold_value}


# ===========================================================================
# fill execution — the ONLY function that can produce a "FILLED" status. Takes the
# NEXT poll's (K+1) bid ladder as its own explicit parameter; structurally cannot see
# or reuse the trigger poll's ladder.
# ===========================================================================
def execute_full_exit_fill(*, qty: Decimal, next_bid_levels, fee_rate: Decimal,
                           allocated_entry_cost: Decimal) -> dict:
    fill = walk_bid_ladder_for_qty(next_bid_levels, qty)
    if not fill.depth_sufficient:
        return {"status": EXIT_DEPTH_INSUFFICIENT, "bid_fill": fill}
    exit_fee = compute_exit_fee(fill.filled_qty, fee_rate, fill.exec_bid_vwap)
    pnl = compute_realized_exit_pnl(bid_vwap=fill.exec_bid_vwap, shares_sold=fill.filled_qty,
                                    exit_fee=exit_fee, allocated_entry_cost=allocated_entry_cost)
    return {"status": "FILLED", "bid_fill": fill, "exit_fee": exit_fee, **pnl}


# ===========================================================================
# HOLD_CONTROL — the control overlay: no early exit, hold to canonical resolution.
# `resolution` is an OPAQUE, already-decided outcome (status/won) supplied by the
# caller (the orchestrator's resolve_selected_side, which reuses the G6 pure
# deciders) -- this function never fetches or derives a winner itself.
# ===========================================================================
def evaluate_hold_control(*, remaining_shares: Decimal, allocated_entry_cost: Decimal,
                          resolution: dict) -> dict:
    status = resolution.get("status")
    if status == GAMMA_CLOB_CONFLICT_FAIL_CLOSED:
        return {"status": GAMMA_CLOB_CONFLICT_FAIL_CLOSED}
    if status != "RESOLVED":
        return {"status": RESOLUTION_PENDING}
    pnl = compute_resolution_pnl(remaining_shares=remaining_shares, won=resolution["won"],
                                 allocated_entry_cost=allocated_entry_cost)
    return {"status": RESOLVED_HOLD, **pnl}


# ===========================================================================
# STAGED_15_20_30_COUNTERFACTUAL — counterfactual measurement only; no staged
# execution code. Sells 1/3 at each TP tier's first valid fill; any unsold remainder
# goes to resolution. `tranche_fills` are ALREADY-COMPUTED (via execute_full_exit_fill
# or None if never filled before resolution) -- this function only aggregates.
# ===========================================================================
def split_into_thirds(qty: Decimal) -> list:
    """Three tranche quantities summing EXACTLY to qty (remainder folded into the last
    tranche so no fractional share is ever lost or fabricated)."""
    third = (qty / Decimal("3")).quantize(Decimal("0.00000001"))
    t1 = third
    t2 = third
    t3 = qty - t1 - t2
    return [t1, t2, t3]


def evaluate_staged_counterfactual(*, held_qty: Decimal, fee_rate: Decimal,
                                   allocated_entry_cost: Decimal, tranche_fills: list,
                                   resolution: dict) -> dict:
    tranche_qtys = split_into_thirds(held_qty)
    per_tranche_cost = allocated_entry_cost / Decimal("3")
    results = []
    for qty, fill in zip(tranche_qtys, tranche_fills):
        if fill is not None:
            results.append(fill)
        else:
            results.append(evaluate_hold_control(remaining_shares=qty,
                                                  allocated_entry_cost=per_tranche_cost,
                                                  resolution=resolution))
    pnls = [r.get("realized_net_pnl") for r in results if r.get("realized_net_pnl") is not None]
    combined = sum(pnls, Decimal("0")) if len(pnls) == len(results) else None
    return {"tranche_qtys": tranche_qtys, "tranche_results": results, "combined_net_pnl": combined}


# ===========================================================================
# I. delayed entry-depth persistence evidence — minimal, one confirmation snapshot;
# never rewrites the original entry.
# ===========================================================================
def record_entry_depth_persistence(*, entry_ask_vwap: Decimal, entry_filled_qty: Decimal,
                                   confirmation_ask_levels) -> dict:
    """Walks the confirmation-poll ask ladder for the SAME quantity that was originally
    filled and compares the resulting VWAP to the original entry VWAP. Evidence only --
    never mutates or retroactively rewrites the original entry values."""
    from analysis.forensic.gateg5_plumbing import walk_ask_ladder_for_stake
    # reuse the committed stake-clamped walker by supplying the original notional as the
    # "stake" -- gives the confirmation-poll executable VWAP for materially the same size.
    stake = entry_ask_vwap * entry_filled_qty
    fill = walk_ask_ladder_for_stake(confirmation_ask_levels, stake)
    depth_persisted = fill.depth_sufficient and fill.exec_ask_vwap <= entry_ask_vwap
    return {"depth_persisted": depth_persisted, "confirmation_ask_vwap": fill.exec_ask_vwap,
            "confirmation_filled_qty": fill.filled_qty,
            "confirmation_depth_sufficient": fill.depth_sufficient}


# ===========================================================================
# J. concurrent exposure tally — observation only; no sizing/allocation decision.
# ===========================================================================
def tally_concurrent_exposure(open_positions: list) -> dict:
    same_direction = {"YES": 0, "NO": 0}
    assets = set()
    notional = Decimal("0")
    for p in open_positions:
        side = p.get("selected_side")
        if side in same_direction:
            same_direction[side] += 1
        if p.get("asset"):
            assets.add(p["asset"])
        cost = p.get("entry_cost")
        if cost is not None:
            notional += cost
    return {"open_position_count": len(open_positions), "aggregate_paper_notional": notional,
            "same_direction_count": same_direction, "assets": sorted(assets)}
