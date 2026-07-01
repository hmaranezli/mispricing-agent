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

from analysis.forensic import gateg5_plumbing as _plumb
from analysis.forensic import gateg7_paper_pnl as pp

# --- managed-position lifecycle states ---
STATE_PAPER_OPEN = "PAPER_OPEN"
STATE_MONITORING = "MONITORING"
STATE_EXIT_TRIGGERED = "EXIT_TRIGGERED"
STATE_EXIT_PENDING_NEXT_POLL = "EXIT_PENDING_NEXT_POLL"
STATE_PAPER_CLOSED = "PAPER_CLOSED"

# --- terminal / fail-closed statuses (never conflate a trigger with a fill) ---
RESOLVED_HOLD = "RESOLVED_HOLD"
RESOLVED_RESIDUAL = "RESOLVED_RESIDUAL"
TP_EXIT_FILLED = "TP_EXIT_FILLED"
TIME_STOP_FILLED = "TIME_STOP_FILLED"
MODEL_PREMIUM_EXIT_FILLED = "MODEL_PREMIUM_EXIT_FILLED"
ENTRY_THESIS_INVALIDATION_FILLED = "ENTRY_THESIS_INVALIDATION_FILLED"
EXIT_DEPTH_INSUFFICIENT = "EXIT_DEPTH_INSUFFICIENT"
EXIT_NO_NEXT_POLL = "EXIT_NO_NEXT_POLL"
RESOLUTION_PENDING = "RESOLUTION_PENDING"
CAPTURE_FAILED = "CAPTURE_FAILED"
GAMMA_CLOB_CONFLICT_FAIL_CLOSED = "GAMMA_CLOB_CONFLICT_FAIL_CLOSED"
STAGED_AGGREGATE = "STAGED_AGGREGATE"

# --- exit-fill outcomes (a fill attempt at poll K+1 against that poll's OWN bid ladder) ---
FILL_FILLED = "FILLED"          # the full requested residual was absorbed -> overlay closes
FILL_PARTIAL = "PARTIAL_FILL"   # only part absorbed -> the residual is conserved, overlay re-monitors
FILL_NONE = "NO_FILL"           # zero depth -> nothing sold, residual + cost basis untouched

# --- pre-registered overlays ---
OVERLAY_HOLD_CONTROL = "HOLD_CONTROL"
OVERLAY_TP_15_FULL = "TP_15_FULL"
OVERLAY_TP_20_FULL = "TP_20_FULL"
OVERLAY_TP_30_FULL = "TP_30_FULL"
OVERLAY_TIME_STOP_T120 = "TIME_STOP_T120"
# MODEL_PREMIUM_EXIT: current fee-net executable exit value >= current model hold value
# (a model-PREMIUM harvest). ENTRY_THESIS_INVALIDATION: current model hold value has
# decayed to/below the remaining shares' fixed entry cost basis (the entry thesis is
# gone). These are two INDEPENDENT counterfactual worlds -- no precedence between them.
OVERLAY_MODEL_PREMIUM_EXIT = "MODEL_PREMIUM_EXIT"
OVERLAY_ENTRY_THESIS_INVALIDATION = "ENTRY_THESIS_INVALIDATION"
OVERLAY_STAGED = "STAGED_15_20_30_COUNTERFACTUAL"
ALL_OVERLAYS = (OVERLAY_HOLD_CONTROL, OVERLAY_TP_15_FULL, OVERLAY_TP_20_FULL, OVERLAY_TP_30_FULL,
                OVERLAY_TIME_STOP_T120, OVERLAY_MODEL_PREMIUM_EXIT,
                OVERLAY_ENTRY_THESIS_INVALIDATION, OVERLAY_STAGED)

TP_PCTS = {OVERLAY_TP_15_FULL: Decimal("0.15"), OVERLAY_TP_20_FULL: Decimal("0.20"),
          OVERLAY_TP_30_FULL: Decimal("0.30")}

CORRELATED_WINDOW_SKIPPED = "CORRELATED_WINDOW_SKIPPED"
INVALID_EDGE_REJECTED = "INVALID_EDGE_REJECTED"
MONITORING_TIMESTAMP_REJECTED = "MONITORING_TIMESTAMP_REJECTED"

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


def _valid_positive_edge(decision: dict):
    """Returns the selected-side net edge as a Decimal ONLY if it is present, finite,
    and strictly positive; otherwise None. A None/malformed/non-finite/non-positive edge
    must never enter the per-window ranking (it must never win or outrank a valid one)."""
    edge = selected_net_edge(decision)
    if edge is None:
        return None
    try:
        if not edge.is_finite():
            return None
    except AttributeError:
        return None
    if edge <= 0:
        return None
    return edge


def select_shared_entry_cohort(decisions: list) -> list:
    """Groups PAPER_OPEN rows by 15m window (pp.window_of(slug)); keeps only the single
    highest-net-edge PAPER_OPEN per window, downgrading the rest to
    CORRELATED_WINDOW_SKIPPED (evidence preserved, never discarded). A PAPER_OPEN row
    whose selected_net_edge is missing/malformed/non-finite/non-positive is rejected
    BEFORE ranking (INVALID_EDGE_REJECTED, evidence preserved) -- it can never win or
    outrank a valid candidate, since it never enters the per-window candidate list at
    all. Non-PAPER_OPEN rows pass through completely untouched -- every mechanically
    valid candidate is preserved for later threshold bucketing; nothing is hard-filtered
    here beyond this edge-validity gate."""
    by_window: dict[str, list[tuple[Decimal, dict]]] = {}
    passthrough = []
    for d in decisions:
        if d.get("status") != pp.PAPER_OPEN:
            passthrough.append(d)
            continue
        edge = _valid_positive_edge(d)
        if edge is None:
            rejected = dict(d)
            rejected["status"] = INVALID_EDGE_REJECTED
            passthrough.append(rejected)
            continue
        w = d.get("window") or pp.window_of(d.get("slug"))
        by_window.setdefault(w, []).append((edge, d))

    out = list(passthrough)
    for _window, rows in by_window.items():
        ranked = sorted(rows, key=lambda pair: pair[0], reverse=True)
        _winner_edge, winner = ranked[0]
        out.append(winner)
        for _edge, loser in ranked[1:]:
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


def _walk_qty_clamped(levels, qty: Decimal) -> dict:
    """Generic quantity-clamped ladder walk. `levels` must already be validated and
    sorted best-first for the side in question (bids descending, asks ascending)."""
    remaining = qty
    filled = Decimal("0")
    notional = Decimal("0")
    levels_used = 0
    for price, size in levels:
        if remaining <= 0:
            break
        levels_used += 1
        take = min(size, remaining)
        filled += take
        notional += take * price
        remaining -= take
    vwap = (notional / filled) if filled > 0 else Decimal("0")
    return {"filled_qty": filled, "notional": notional, "exec_vwap": vwap,
            "depth_sufficient": (remaining == 0), "residual_unfilled_qty": remaining,
            "levels_used": levels_used, "would_move_book": levels_used > 1}


def walk_bid_ladder_for_qty(raw_levels, qty: Decimal) -> BidFill:
    """Validates price (0,1] domain + strictly-positive size, merges duplicate price
    levels (summed size), and sorts best-(highest-)bid-first via the ESTABLISHED
    gateg5_plumbing book pipeline (ladder_to_decimal_json + parse_bid_ladder) BEFORE any
    VWAP walk -- a malformed level fails closed (raises PlumbingError), never a
    fabricated VWAP. `raw_levels` may be any [price,size] pairs (str/int/Decimal)."""
    levels = _plumb.parse_bid_ladder(_plumb.ladder_to_decimal_json(raw_levels))
    r = _walk_qty_clamped(levels, qty)
    return BidFill(filled_qty=r["filled_qty"], proceeds=r["notional"], exec_bid_vwap=r["exec_vwap"],
                   depth_sufficient=r["depth_sufficient"], residual_unfilled_qty=r["residual_unfilled_qty"],
                   levels_used=r["levels_used"], would_move_book=r["would_move_book"])


def walk_ask_ladder_for_qty(raw_levels, qty: Decimal) -> dict:
    """Quantity-clamped ASK walk (validated + ascending via the same established
    pipeline) -- used for entry-depth persistence evidence (re-walking the confirmation
    ladder for the exact original share quantity, never a re-derived dollar notional)."""
    levels = _plumb.parse_ask_ladder(_plumb.ladder_to_decimal_json(raw_levels))
    return _walk_qty_clamped(levels, qty)


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


def compute_model_hold_value(*, fair_prob_selected_side: Decimal, remaining_shares: Decimal) -> Decimal:
    """MODEL hold value = current fair probability (of the SELECTED side) * remaining
    held shares. This is a THEORETICAL mark, structurally distinct from the EXECUTABLE
    liquidation value (bid VWAP * qty - exit fee, see compute_realized_exit_pnl /
    walk_bid_ladder_for_qty) -- the two must never be conflated or share a field name."""
    return fair_prob_selected_side * remaining_shares


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


def evaluate_model_premium_exit_trigger(*, held_qty: Decimal, bid_levels, fee_rate: Decimal,
                                        fair_prob_selected_side: Decimal) -> dict:
    """MODEL_PREMIUM_EXIT trigger-only (poll K). Walks the bid ladder for the COMPLETE
    remaining quantity and requires FULL executable depth for it -- a full-position exit
    the book cannot absorb at K is not a real trigger (depth_sufficient=False, never
    triggered). Both sides of the comparison are computed over the SAME (full remaining)
    quantity: the model hold value = fair_prob_selected_side * held_qty (computed here,
    never a qty-mismatched external value) versus the immediate fee-net EXECUTABLE exit
    value = bid proceeds - exit fee. Triggers when the executable exit value already
    equals/beats the model hold value (a premium worth harvesting). This is NOT
    entry-thesis deterioration -- see evaluate_entry_thesis_invalidation_trigger. Never
    returns a fill status; the fill happens only via execute_exit_fill on poll K+1."""
    model_hold_value = compute_model_hold_value(fair_prob_selected_side=fair_prob_selected_side,
                                                remaining_shares=held_qty)
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


def evaluate_entry_thesis_invalidation_trigger(*, remaining_shares: Decimal,
                                               fair_prob_selected_side: Decimal,
                                               remaining_allocated_entry_cost: Decimal) -> dict:
    """ENTRY_THESIS_INVALIDATION trigger-only (poll K). An INDEPENDENT active
    counterfactual overlay: triggers when the current model hold value of the remaining
    shares (fair_prob_selected_side * remaining_shares) has decayed to at or below the
    remaining shares' fixed entry cost basis (remaining_allocated_entry_cost). That basis
    is the CALLER's exact-remainder-conserved residual cost (fixed_entry_cost_per_share *
    remaining_shares); prior realized proceeds are NEVER subtracted from it -- they belong
    only to the already-filled legs' PnL. No bid-ladder / executable-depth requirement
    here (the trigger is a model-vs-cost thesis check); the actual fill happens only via
    execute_exit_fill on poll K+1. Never returns a fill status."""
    model_hold_value = compute_model_hold_value(fair_prob_selected_side=fair_prob_selected_side,
                                                remaining_shares=remaining_shares)
    triggered = model_hold_value <= remaining_allocated_entry_cost
    return {"triggered": triggered, "model_hold_value": model_hold_value,
            "remaining_allocated_entry_cost": remaining_allocated_entry_cost}


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


def execute_exit_fill(*, requested_qty: Decimal, next_bid_levels, fee_rate: Decimal,
                      remaining_allocated_cost: Decimal) -> dict:
    """Residual-conserving exit fill against poll K+1's OWN bid ladder. Walks the ladder
    for the FULL currently-held residual (`requested_qty`) and books whatever actually
    fills -- never fabricating unfilled shares. Cost is allocated to the filled leg
    PROPORTIONALLY to the filled fraction (leg_cost = remaining_allocated_cost *
    filled/requested), and the residual keeps the EXACT remainder (remaining_cost_after =
    remaining_allocated_cost - leg_cost) so a chain of partial legs telescopes back to the
    original cost basis to the cent (a final leg that clears the whole residual gets
    exactly the leftover, since filled==requested makes leg_cost==remaining_allocated_cost).

      * FILL_FILLED  -> the whole residual was absorbed; remaining_qty_after == 0.
      * FILL_PARTIAL -> only part absorbed; the residual (qty + exact cost) is preserved
                        for a later poll's re-trigger/re-fill -- NOT a terminal close.
      * FILL_NONE    -> zero depth; nothing sold, residual + cost basis untouched.

    Never returns a resolution/settlement outcome (fee-free settlement is a separate,
    resolution-time concern); this only ever executes a taker SELL that pays an exit fee
    on the shares it actually sold."""
    fill = walk_bid_ladder_for_qty(next_bid_levels, requested_qty)
    if fill.filled_qty <= 0:
        return {"status": FILL_NONE, "bid_fill": fill, "filled_qty": Decimal("0"),
                "exit_fee": Decimal("0"), "net_exit_proceeds": Decimal("0"),
                "leg_cost": Decimal("0"), "realized_net_pnl": Decimal("0"),
                "remaining_qty_after": requested_qty,
                "remaining_cost_after": remaining_allocated_cost}
    exit_fee = compute_exit_fee(fill.filled_qty, fee_rate, fill.exec_bid_vwap)
    net_exit_proceeds = fill.proceeds - exit_fee
    leg_cost = remaining_allocated_cost * fill.filled_qty / requested_qty
    remaining_qty_after = requested_qty - fill.filled_qty
    remaining_cost_after = remaining_allocated_cost - leg_cost   # exact remainder
    realized_net_pnl = net_exit_proceeds - leg_cost
    status = FILL_FILLED if remaining_qty_after == 0 else FILL_PARTIAL
    return {"status": status, "bid_fill": fill, "filled_qty": fill.filled_qty,
            "exit_fee": exit_fee, "net_exit_proceeds": net_exit_proceeds, "leg_cost": leg_cost,
            "realized_net_pnl": realized_net_pnl, "remaining_qty_after": remaining_qty_after,
            "remaining_cost_after": remaining_cost_after}


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


def allocate_tranche_costs(held_qty: Decimal, allocated_entry_cost: Decimal, tranche_qtys: list) -> list:
    """Proportional cost allocation by each tranche's EXACT filled quantity (never a
    flat 1/3 split); the LAST tranche absorbs the exact Decimal remainder so the three
    allocated costs sum IDENTICALLY to allocated_entry_cost -- no cent lost/fabricated."""
    if held_qty > 0:
        cost1 = allocated_entry_cost * tranche_qtys[0] / held_qty
        cost2 = allocated_entry_cost * tranche_qtys[1] / held_qty
    else:
        cost1 = cost2 = Decimal("0")
    cost3 = allocated_entry_cost - cost1 - cost2   # exact remainder -> sums identically
    return [cost1, cost2, cost3]


def evaluate_staged_counterfactual(*, held_qty: Decimal, fee_rate: Decimal,
                                   allocated_entry_cost: Decimal, tranche_fills: list,
                                   resolution: dict) -> dict:
    """Requires EXACTLY 3 tranche fills (never a silent zip truncation on a length
    mismatch -- fails closed via ManagedExitError instead). Entry cost is allocated
    PROPORTIONALLY to each tranche's exact filled quantity (not always a flat 1/3);
    the final tranche absorbs the exact Decimal remainder so the three allocated costs
    sum IDENTICALLY to allocated_entry_cost -- no cent is ever lost or fabricated."""
    if not isinstance(tranche_fills, list) or len(tranche_fills) != 3:
        raise ManagedExitError(
            f"{OVERLAY_STAGED} requires exactly 3 tranche fills, got {tranche_fills!r}")
    tranche_qtys = split_into_thirds(held_qty)
    tranche_costs = allocate_tranche_costs(held_qty, allocated_entry_cost, tranche_qtys)

    results = []
    for qty, fill, cost in zip(tranche_qtys, tranche_fills, tranche_costs):
        if fill is not None:
            results.append(fill)
        else:
            results.append(evaluate_hold_control(remaining_shares=qty,
                                                  allocated_entry_cost=cost,
                                                  resolution=resolution))
    pnls = [r.get("realized_net_pnl") for r in results]
    combined = sum(pnls, Decimal("0")) if all(p is not None for p in pnls) else None
    return {"tranche_qtys": tranche_qtys, "tranche_costs": tranche_costs,
            "tranche_results": results, "combined_net_pnl": combined}


def combine_staged_tranche_pnls(tranche_net_pnls: list, original_entry_cost: Decimal) -> dict:
    """Aggregates the three staged tranches' realized net PnLs into ONE result: combined
    net PnL is the exact dollar SUM of the three tranche PnLs; aggregate ROI is that sum
    divided ONCE by the ORIGINAL full entry cost -- never the average of the three tranche
    ROI percentages. Fails closed on a wrong tranche count (ManagedExitError, never a
    silent truncation). Returns a None aggregate if any tranche is not yet terminal (None)
    -- e.g. a tranche settled fail-closed on a Gamma/CLOB conflict."""
    if not isinstance(tranche_net_pnls, list) or len(tranche_net_pnls) != 3:
        raise ManagedExitError(
            f"{OVERLAY_STAGED} aggregate requires exactly 3 tranche PnLs, got {tranche_net_pnls!r}")
    if any(p is None for p in tranche_net_pnls):
        return {"combined_net_pnl": None, "aggregate_roi": None}
    combined = sum(tranche_net_pnls, Decimal("0"))
    roi = (combined / original_entry_cost) if original_entry_cost > 0 else None
    return {"combined_net_pnl": combined, "aggregate_roi": roi}


# ===========================================================================
# I. delayed entry-depth persistence evidence — minimal, one confirmation snapshot;
# never rewrites the original entry.
# ===========================================================================
def record_entry_depth_persistence(*, entry_ask_vwap: Decimal, entry_filled_qty: Decimal,
                                   confirmation_ask_levels) -> dict:
    """Re-walks the confirmation-poll ASK ladder for the EXACT original filled SHARE
    quantity -- never a re-derived dollar notional (price*qty is not invariant under a
    price move: re-deriving a "stake" from entry_ask_vwap*entry_filled_qty and walking
    THAT would silently request a different, wrong quantity whenever the confirmation
    price differs from the entry price). Evidence only -- never mutates or retroactively
    rewrites the original entry values. Fails closed for admission (`admitted=False`)
    when the exact original quantity is not available; the honest partial fill/residual
    is still recorded, never fabricated."""
    result = walk_ask_ladder_for_qty(confirmation_ask_levels, entry_filled_qty)
    admitted = result["depth_sufficient"]
    depth_persisted = admitted and result["exec_vwap"] <= entry_ask_vwap
    return {"depth_persisted": depth_persisted, "confirmation_ask_vwap": result["exec_vwap"],
            "confirmation_filled_qty": result["filled_qty"],
            "confirmation_depth_sufficient": result["depth_sufficient"],
            "confirmation_residual_unfilled_qty": result["residual_unfilled_qty"],
            "admitted": admitted}


# ===========================================================================
# monitoring timing — no-lookahead / staleness proof for one poll's captured evidence.
# Never uses resolution/outcome data (no such parameter exists here).
# ===========================================================================
def validate_monitoring_timing(*, selected_quote_ts_ms, selected_capture_completed_ms,
                               opposite_quote_ts_ms, opposite_capture_completed_ms,
                               hl_feed_ts, hl_capture_completed_ms, poll_decision_ts,
                               quote_stale_ms, entry_ts=None) -> dict:
    """poll_decision_ts must be >= every capture-completion timestamp (no-lookahead); a
    missing or future timestamp fails closed. Only the two BOOK quote timestamps are
    additionally checked for staleness (mirrors the committed G8 discipline, which never
    applies a staleness bound to the HL feed timestamp itself).

    When the position's preserved G8 entry_ts is supplied (optional; None preserves the
    prior behavior exactly), poll_decision_ts must ALSO be >= entry_ts -- a monitoring poll
    can never predate its own entry. A poll before entry (entry_ts > poll_decision_ts) is
    rejected via the SAME fail-closed MONITORING_TIMESTAMP_REJECTED path (field=entry_ts)."""
    ordering_checks = [
        ("selected_quote_ts_ms", selected_quote_ts_ms),
        ("selected_capture_completed_ms", selected_capture_completed_ms),
        ("opposite_quote_ts_ms", opposite_quote_ts_ms),
        ("opposite_capture_completed_ms", opposite_capture_completed_ms),
        ("hl_feed_ts", hl_feed_ts),
        ("hl_capture_completed_ms", hl_capture_completed_ms),
    ]
    if entry_ts is not None:
        ordering_checks.append(("entry_ts", entry_ts))
    for field, ts in ordering_checks:
        if ts is None:
            return {"ok": False, "status": MONITORING_TIMESTAMP_REJECTED, "field": field,
                    "reason": "missing"}
        if ts > poll_decision_ts:
            return {"ok": False, "status": MONITORING_TIMESTAMP_REJECTED, "field": field,
                    "reason": "future"}
    for field, ts in (("selected_quote_ts_ms", selected_quote_ts_ms),
                      ("opposite_quote_ts_ms", opposite_quote_ts_ms)):
        if (poll_decision_ts - ts) > quote_stale_ms:
            return {"ok": False, "status": MONITORING_TIMESTAMP_REJECTED, "field": field,
                    "reason": "stale"}
    return {"ok": True}


# ===========================================================================
# J. concurrent exposure tally — observation only; no sizing/allocation decision.
# ===========================================================================
def format_telegram_report(*, position: dict, overlay_terminals: dict,
                           concurrent_exposure: dict) -> str:
    """Deterministic Telegram-READY text summary. Never sends anything; the caller
    decides whether/where to deliver this string. Never labels a loss "best" -- best/
    worst are picked by plain min/max over realized_net_pnl, whatever their sign."""
    lines = ["[PAPER/SHADOW -- NOT TRADEABLE ALPHA]",
             f"{position.get('asset')} window={position.get('window')} side={position.get('selected_side')}",
             f"entry_ask_vwap={position.get('entry_ask_vwap')} shares={position.get('held_qty')} "
             f"entry_fee={position.get('entry_fee')}"]
    entry_price = pp._d(position.get("entry_ask_vwap"))
    if entry_price is not None:
        for name, pct in TP_PCTS.items():
            target = gross_tp_target_price(entry_price, pct)
            lines.append(f"{name}_target={target} reachable={gross_tp_reachable(target)}")
    best = None
    worst = None
    for overlay, term in overlay_terminals.items():
        pnl = term.get("realized_net_pnl")
        lines.append(f"{overlay}: {term.get('status')} net_pnl={pnl}")
        if pnl is not None:
            pnl_d = Decimal(str(pnl))
            if best is None or pnl_d > best[1]:
                best = (overlay, pnl_d)
            if worst is None or pnl_d < worst[1]:
                worst = (overlay, pnl_d)
    if best:
        lines.append(f"BEST overlay: {best[0]} ({best[1]})")
    if worst:
        lines.append(f"WORST overlay: {worst[0]} ({worst[1]})")
    lines.append(f"concurrent_open_positions={concurrent_exposure.get('open_position_count')}")
    lines.append(f"aggregate_paper_notional={concurrent_exposure.get('aggregate_paper_notional')}")
    return "\n".join(lines)


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
