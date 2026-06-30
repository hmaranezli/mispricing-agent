#!/usr/bin/env python3
"""
Gate G.5 — Forensic Measurement Engine (CODE DRAFT — DO NOT RUN)

Implements the offline forensic measurement layer specified in
docs/superpowers/quant/gateg5_offline_forensic_engine.md. It defines the
SQLite schemas, sentinel-safe Decimal math, the conservative terminal
accounting, the four replay arms, deterministic stratified holdout, resolution
/ token-outcome binding, summary classifications, and diagnostics stubs.

HARD BOUNDARIES (constitution + Hasan authorization):
  * NO real orders, NO wallet/signing/capital, NO Live S1 access.
  * Live S1 remains CREATED_EMPTY_LOCKED_CONTAINER; append DENIED / NOT PERFORMED.
  * capacity 0. /tmp artifacts only. NO strategy change. NO repo mutation.
  * main() refuses to run unless GATEG5_ARM=START-RUNNER-CONFIRMED.

This module computes NOTHING on import and creates NO files on import. A run
root is only created after the hard execution guard passes inside main().
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from decimal import Decimal, getcontext, InvalidOperation
from typing import Any, Optional

# Decimal-safe context: never use binary float for money. SQLite REAL is banned.
getcontext().prec = 50

ARM_ENV = "GATEG5_ARM"
ARM_TOKEN = "START-RUNNER-CONFIRMED"
RUN_ROOT_PREFIX = "/tmp/hasan-gateg5-"

# Live-S1 lock posture, asserted in the banner; this engine never touches S1.
LIVE_S1_STATE = "CREATED_EMPTY_LOCKED_CONTAINER"
LIVE_S1_APPEND = "DENIED / NOT PERFORMED"
LIVE_S1_CAPACITY = 0
WALLET_CAPITAL = "BLOCKED"


# =============================================================================
# Forensic error types
# =============================================================================
class ForensicError(Exception):
    """Base for all forensic-integrity violations (fail closed, never silent)."""


class SentinelMathError(ForensicError):
    """Raised when numeric math is attempted on a NOT_COMPUTED_* sentinel."""


class LookaheadError(ForensicError):
    """Raised when a field with knowable_ts > decision tick is read."""


class EntryParityError(ForensicError):
    """Raised when arm entry prices disagree with signal_log.exec_ask_vwap."""


class CostAccountingError(ForensicError):
    """Raised when decision_cost_buffer leaks into a PnL/EV figure."""


# =============================================================================
# 1. exit_mark_status sentinel enum + fill_decision enum + classifications
# =============================================================================
class ExitMarkStatus:
    COMPUTED_EXECUTABLE = "COMPUTED_EXECUTABLE"
    COMPUTED_THIN_PARTIAL = "COMPUTED_THIN_PARTIAL"
    NOT_COMPUTED_BLOCKED_NO_LIQUIDITY = "NOT_COMPUTED_BLOCKED_NO_LIQUIDITY"
    NOT_COMPUTED_STALE_QUOTE = "NOT_COMPUTED_STALE_QUOTE"

    ALL = (
        COMPUTED_EXECUTABLE,
        COMPUTED_THIN_PARTIAL,
        NOT_COMPUTED_BLOCKED_NO_LIQUIDITY,
        NOT_COMPUTED_STALE_QUOTE,
    )
    # exit_mark_vwap is a literal sentinel STRING (not 0, not NULL, not "") here:
    NOT_COMPUTED = (
        NOT_COMPUTED_BLOCKED_NO_LIQUIDITY,
        NOT_COMPUTED_STALE_QUOTE,
    )


class FillDecision:
    FILLED_ACTIVE = "FILLED_ACTIVE"
    VALID_HOLDOUT_SHADOW = "VALID_HOLDOUT_SHADOW"
    UNFILLED_ENTRY_DEPTH_FAIL = "UNFILLED_ENTRY_DEPTH_FAIL"
    UNFILLED_EDGE_LOST = "UNFILLED_EDGE_LOST"
    UNFILLED_QUOTE_STALE = "UNFILLED_QUOTE_STALE"
    UNFILLED_SHADOW_CAP_REACHED = "UNFILLED_SHADOW_CAP_REACHED"
    UNSEQUENCEABLE = "UNSEQUENCEABLE"
    UNFILLED_SELLBACK_REJECT = "UNFILLED_SELLBACK_REJECT"

    # Only these two feed the four EV arms (§5 cohort eligibility).
    EV_ELIGIBLE = (FILLED_ACTIVE, VALID_HOLDOUT_SHADOW)
    # cap-reached is diagnostics-only; everything below is excluded from EV.
    EV_EXCLUDED = (
        UNFILLED_ENTRY_DEPTH_FAIL,
        UNFILLED_EDGE_LOST,
        UNFILLED_QUOTE_STALE,
        UNFILLED_SHADOW_CAP_REACHED,
        UNSEQUENCEABLE,
        UNFILLED_SELLBACK_REJECT,
    )


class TerminalStatus:
    END_TS_FORCED = "END_TS_FORCED"          # forced fill at terminal mark
    BLOCKED_NEVER_CLEAN = "BLOCKED_NEVER_CLEAN"  # empty/stale terminal book


class Forensic:
    """Output classifications — TWO ORTHOGONAL AXES (§10)."""

    # Axis 1 — schema/integrity validity (independent of effective-N)
    SCHEMA_PASS = "FORENSIC_SCHEMA_PASS"
    PARTIAL_CAP_BIASED = "FORENSIC_PARTIAL_CAP_BIASED"
    PARTIAL_NOT_EXERCISED = "FORENSIC_PARTIAL_NOT_EXERCISED"
    FAIL_LOOKAHEAD_RISK = "FORENSIC_FAIL_LOOKAHEAD_RISK"
    FAIL_RESOLUTION_JOIN = "FORENSIC_FAIL_RESOLUTION_JOIN"
    FAIL_TOKEN_OUTCOME_BINDING = "FORENSIC_FAIL_TOKEN_OUTCOME_BINDING"
    FAIL_CENSUS_RECONCILIATION = "FORENSIC_FAIL_CENSUS_RECONCILIATION"

    AXIS1_FAIL = (
        FAIL_LOOKAHEAD_RISK,
        FAIL_RESOLUTION_JOIN,
        FAIL_TOKEN_OUTCOME_BINDING,
        FAIL_CENSUS_RECONCILIATION,
    )
    AXIS1_PARTIAL = (PARTIAL_CAP_BIASED, PARTIAL_NOT_EXERCISED)

    # Axis 2 — alpha-inference eligibility (NEVER collapsed into Axis 1)
    INSUFFICIENT_EFFECTIVE_N = "FORENSIC_INSUFFICIENT_EFFECTIVE_N"
    ALPHA_INFERENCE_ELIGIBLE = "ALPHA_INFERENCE_ELIGIBLE"

    # Token binding assertion result
    TOKEN_BIND_PASS = "PASS"
    TOKEN_BIND_FAIL = "FORENSIC_FAIL_TOKEN_OUTCOME_BINDING"


# Active strategy constants (frozen at G.4b — measurement only, never re-tuned here)
TP_PCT = Decimal("50")
SL_PCT = Decimal("-30")
QUOTE_STALE_MS = 2000


# =============================================================================
# 2. SQLite schema (exact CREATE TABLE statements; TEXT/Decimal, NO REAL)
# =============================================================================
SCHEMA_SIGNAL_LOG = """
CREATE TABLE IF NOT EXISTS signal_log(
  signal_id            TEXT PRIMARY KEY,
  ts_signal            TEXT NOT NULL,
  ts_signal_ms         INTEGER NOT NULL,
  knowable_ts          INTEGER NOT NULL,
  asset                TEXT NOT NULL,
  side                 TEXT NOT NULL,
  condition_id         TEXT NOT NULL,
  token_id             TEXT NOT NULL,
  outcome_index        INTEGER NOT NULL,
  outcome_label        TEXT NOT NULL,
  slug                 TEXT NOT NULL,
  market_end_ts        INTEGER NOT NULL,
  underlying_spot_price TEXT NOT NULL,
  reference_price      TEXT NOT NULL,
  reference_feed_ts    INTEGER NOT NULL,
  reference_age_ms     INTEGER NOT NULL,
  fair_yes             TEXT NOT NULL,
  fair_yes_sigma       TEXT NOT NULL,
  fair_model_version   TEXT NOT NULL,
  strike               TEXT NOT NULL,
  tte_s                INTEGER NOT NULL,
  ask_ladder_json      TEXT NOT NULL,
  bid_ladder_json      TEXT NOT NULL,
  book_hash            TEXT NOT NULL,
  top_ask_price        TEXT NOT NULL,
  top_ask_size         TEXT NOT NULL,
  intended_stake       TEXT NOT NULL,
  book_ask_vwap        TEXT NOT NULL,
  book_bid_vwap        TEXT NOT NULL,
  exec_ask_vwap        TEXT NOT NULL,
  exec_fill_qty_avail  TEXT NOT NULL,
  decision_cost_buffer TEXT NOT NULL,
  realized_entry_cost  TEXT NOT NULL,
  realized_fee_cost    TEXT NOT NULL,
  cost_components      TEXT NOT NULL,
  entry_edge           TEXT NOT NULL,
  exit_depth_notional_avail TEXT NOT NULL,
  exit_depth_required  TEXT NOT NULL,
  fill_decision        TEXT NOT NULL,
  fill_reason          TEXT,
  holdout_seed         TEXT,
  edge_bucket          TEXT NOT NULL,
  tte_bucket           TEXT NOT NULL,
  row_hash             TEXT NOT NULL,
  prev_row_hash        TEXT NOT NULL
);
"""

SCHEMA_MARK_PATH = """
CREATE TABLE IF NOT EXISTS mark_path(
  id               INTEGER PRIMARY KEY,
  signal_id        TEXT NOT NULL,
  seq              INTEGER NOT NULL,
  ts_mark          TEXT NOT NULL,
  ts_mark_ms       INTEGER NOT NULL,
  knowable_ts      INTEGER NOT NULL,
  bid_ladder_json  TEXT NOT NULL,
  exit_mark_status TEXT NOT NULL,
  exit_mark_vwap   TEXT NOT NULL,
  mark_depth       TEXT NOT NULL,
  levels_used      INTEGER NOT NULL,
  executable_flag  INTEGER NOT NULL,
  liquidity_class  TEXT NOT NULL,
  spot_price       TEXT NOT NULL,
  spot_age_ms      INTEGER NOT NULL,
  fair_yes_t       TEXT NOT NULL,
  fair_yes_sigma_t TEXT NOT NULL,
  tte_s            INTEGER NOT NULL,
  row_hash         TEXT NOT NULL,
  prev_row_hash    TEXT NOT NULL
);
"""

SCHEMA_RESOLUTION = """
CREATE TABLE IF NOT EXISTS resolution(
  condition_id         TEXT PRIMARY KEY,
  resolved_yes         TEXT NOT NULL,
  resolution_finalized INTEGER NOT NULL,
  resolution_ts        INTEGER,
  settlement_ts        INTEGER,
  resolution_source    TEXT NOT NULL,
  resolution_fetch_ts  INTEGER NOT NULL,
  settlement_delay_s   INTEGER,
  token_outcome_assert TEXT NOT NULL
);
"""

ALL_SCHEMAS = (SCHEMA_SIGNAL_LOG, SCHEMA_MARK_PATH, SCHEMA_RESOLUTION)


def init_schema(conn) -> None:
    """Create the three forensic tables. Caller owns the sqlite3 connection."""
    for ddl in ALL_SCHEMAS:
        conn.execute(ddl)
    conn.commit()
    assert_no_real_columns(conn)


def assert_no_real_columns(conn) -> None:
    """Static integrity scan: no SQLite REAL columns anywhere (constitution)."""
    offenders = []
    for table in ("signal_log", "mark_path", "resolution"):
        for row in conn.execute(f"PRAGMA table_info({table})"):
            col_name, col_type = row[1], (row[2] or "").upper()
            if "REAL" in col_type or "FLOAT" in col_type or "DOUBLE" in col_type:
                offenders.append(f"{table}.{col_name}:{col_type}")
    if offenders:
        raise ForensicError(f"REAL/float columns banned, found: {offenders}")


# =============================================================================
# 3. Sentinel-safe Decimal math
# =============================================================================
def D(value: Any) -> Decimal:
    """Decimal coercion that refuses NOT_COMPUTED_* sentinels and junk."""
    if isinstance(value, str) and value in ExitMarkStatus.ALL:
        raise SentinelMathError(
            f"refused numeric coercion of exit_mark sentinel {value!r}"
        )
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise SentinelMathError(f"non-numeric value {value!r} cannot be Decimal") from exc


def exit_mark_value(status: str, raw_vwap: str) -> Decimal:
    """
    Return a numeric exit mark ONLY when transacting is legitimate.

    COMPUTED_EXECUTABLE      -> numeric VWAP (clean transactable)
    COMPUTED_THIN_PARTIAL    -> numeric VWAP, but RESERVED for terminal_conservative()
                                only; mid-path callers must not clean-close on it.
    NOT_COMPUTED_*           -> hard error; the column is a literal sentinel string.
    """
    if status not in ExitMarkStatus.ALL:
        raise ForensicError(f"unknown exit_mark_status {status!r}")
    if status in ExitMarkStatus.NOT_COMPUTED:
        raise SentinelMathError(
            f"exit_mark_vwap is sentinel {status!r}; numeric math forbidden"
        )
    return D(raw_vwap)


def is_clean_executable(mark: "Mark") -> bool:
    return (
        mark.exit_mark_status == ExitMarkStatus.COMPUTED_EXECUTABLE
        and int(mark.executable_flag) == 1
    )


# =============================================================================
# Lightweight in-memory row views (replay reads from DB rows -> these dataclasses)
# =============================================================================
@dataclass
class Mark:
    signal_id: str
    seq: int
    ts_mark_ms: int
    knowable_ts: int
    bid_ladder_json: str
    exit_mark_status: str
    exit_mark_vwap: str
    executable_flag: int
    liquidity_class: str
    tte_s: int
    # --- per-signal diagnostics extension (telemetry only; never gates exit) ---
    elapsed_ms_since_signal: int = 0  # ts_mark_ms - ts_signal_ms (post-entry age)


@dataclass
class Signal:
    signal_id: str
    ts_signal_ms: int
    knowable_ts: int
    asset: str
    side: str
    condition_id: str
    token_id: str
    outcome_index: int
    outcome_label: str
    market_end_ts: int
    intended_stake: str
    exec_ask_vwap: str
    exec_fill_qty_avail: str
    decision_cost_buffer: str
    realized_entry_cost: str
    realized_fee_cost: str
    fill_decision: str
    edge_bucket: str
    tte_bucket: str
    # --- per-signal diagnostics extension (Decimal-safe TEXT; coerced via D()) ---
    # All numeric market quantities stored as Decimal-safe strings (anti-float),
    # coerced through D() at compute time exactly like exec_ask_vwap.
    entry_edge: str = "0"          # modeled diagnostic net edge at ts_signal
    fair_yes: str = "0"            # model P(Up) at ts_signal
    reference_age_ms: int = 0      # ts_signal_ms - reference_feed_ts
    tte_s: int = 0                 # market_end_ts - ts_signal (position-owned)
    ask_spread_pct: str = "0"      # (best_ask - best_bid)/mid at entry
    ask_depth_avail: str = "0"     # executable ask notional at entry


@dataclass
class TerminalResult:
    status: str            # END_TS_FORCED / BLOCKED_NEVER_CLEAN
    filled_shares: Decimal
    residual_shares: Decimal
    realized_value: Decimal
    residual_value: Decimal  # always 0
    pnl: Decimal


# =============================================================================
# Cost helper — realized only; decision_cost_buffer NEVER enters PnL
# =============================================================================
def realized_cost(sig: Signal) -> Decimal:
    """intended_stake + realized_entry_cost + realized_fee_cost. Buffer EXCLUDED."""
    return (
        D(sig.intended_stake)
        + D(sig.realized_entry_cost)
        + D(sig.realized_fee_cost)
    )


def assert_buffer_not_in_pnl(pnl_terms: dict) -> None:
    """Guard: decision_cost_buffer must never appear in any PnL term."""
    if "decision_cost_buffer" in pnl_terms:
        raise CostAccountingError("decision_cost_buffer leaked into PnL terms")


# =============================================================================
# Bid-ladder parsing + FAK walk (Decimal-safe)
# =============================================================================
def parse_bid_ladder(bid_ladder_json: str) -> list[tuple[Decimal, Decimal]]:
    """Return [(price, size), ...] sorted best (highest) bid first."""
    raw = json.loads(bid_ladder_json) if bid_ladder_json else []
    levels = [(D(p), D(s)) for p, s in raw]
    levels.sort(key=lambda lv: lv[0], reverse=True)
    return levels


def fak_walk_bids(levels: list[tuple[Decimal, Decimal]], shares: Decimal):
    """
    Fill-and-kill walk of held `shares` against available bid levels.
    Returns (filled_shares, realized_value). No price improvement, no synthetic depth.
    """
    remaining = shares
    realized = Decimal("0")
    for price, size in levels:
        if remaining <= 0:
            break
        take = size if size < remaining else remaining
        realized += take * price
        remaining -= take
    filled = shares - remaining
    return filled, realized


# =============================================================================
# 4. terminal_conservative()
# =============================================================================
def terminal_conservative(
    marks: list[Mark],
    market_end_ts: int,
    held_shares: Decimal,
    cost: Decimal,
) -> TerminalResult:
    """
    Conservative terminal accounting when no clean executable TP/SL exit
    occurred before market_end_ts.

    Selection is BY TIME ONLY: use the last observed bid ladder at or before
    market_end_ts. NEVER search backward for the most favorable executable mark.

      * empty / stale-only terminal book -> realized_value=0, residual=all shares,
        residual valued at 0, status BLOCKED_NEVER_CLEAN.
      * partial bids -> FAK-walk available bids, realize filled portion, unfilled
        residual valued at 0, status END_TS_FORCED.

    All math Decimal-safe. Residual value is ALWAYS 0 (no optimistic settlement,
    no reuse of an earlier favorable mark).
    """
    eligible = [m for m in marks if m.ts_mark_ms <= market_end_ts]
    if not eligible:
        # No mark at/before end -> treat as fully blocked.
        return TerminalResult(
            status=TerminalStatus.BLOCKED_NEVER_CLEAN,
            filled_shares=Decimal("0"),
            residual_shares=held_shares,
            realized_value=Decimal("0"),
            residual_value=Decimal("0"),
            pnl=_pnl_pct(Decimal("0"), cost),
        )

    # last by timestamp (tie-break by seq) — time-selected, not favorability-selected
    terminal = max(eligible, key=lambda m: (m.ts_mark_ms, m.seq))

    # empty book OR stale-only -> treated as empty
    if terminal.exit_mark_status in (
        ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY,
        ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE,
    ):
        return TerminalResult(
            status=TerminalStatus.BLOCKED_NEVER_CLEAN,
            filled_shares=Decimal("0"),
            residual_shares=held_shares,
            realized_value=Decimal("0"),
            residual_value=Decimal("0"),
            pnl=_pnl_pct(Decimal("0"), cost),
        )

    # executable or thin-partial -> FAK-walk the available bids of THIS terminal ladder
    levels = parse_bid_ladder(terminal.bid_ladder_json)
    if not levels:
        return TerminalResult(
            status=TerminalStatus.BLOCKED_NEVER_CLEAN,
            filled_shares=Decimal("0"),
            residual_shares=held_shares,
            realized_value=Decimal("0"),
            residual_value=Decimal("0"),
            pnl=_pnl_pct(Decimal("0"), cost),
        )

    filled, realized_value = fak_walk_bids(levels, held_shares)
    residual_shares = held_shares - filled
    return TerminalResult(
        status=TerminalStatus.END_TS_FORCED,
        filled_shares=filled,
        residual_shares=residual_shares,
        realized_value=realized_value,
        residual_value=Decimal("0"),   # unfilled residual ALWAYS 0
        pnl=_pnl_pct(realized_value, cost),
    )


def _pnl_pct(proceeds: Decimal, cost: Decimal) -> Decimal:
    if cost == 0:
        raise CostAccountingError("cost==0 in pnl_pct (would div-by-zero)")
    return (proceeds - cost) / cost * Decimal("100")


# =============================================================================
# Causality guard
# =============================================================================
def assert_no_lookahead(field_knowable_ts: int, decision_tick: int) -> None:
    """Any field whose knowable_ts > decision tick taints the whole run."""
    if field_knowable_ts > decision_tick:
        raise LookaheadError(
            f"FORENSIC_FAIL_LOOKAHEAD_RISK: knowable_ts {field_knowable_ts} "
            f"> decision_tick {decision_tick}"
        )


def assert_entry_parity(sig: Signal, arm_entry_price: Decimal) -> None:
    if D(sig.exec_ask_vwap) != arm_entry_price:
        raise EntryParityError(
            f"FORENSIC_FAIL_CENSUS_RECONCILIATION (entry mismatch) "
            f"{sig.signal_id}: arm {arm_entry_price} != exec_ask_vwap {sig.exec_ask_vwap}"
        )


# =============================================================================
# 5. Replay engine
# =============================================================================
def _eligible_marks(sig: Signal, marks: list[Mark]) -> list[Mark]:
    """Only marks with ts_signal <= ts_mark <= market_end_ts, ordered by seq."""
    out = [
        m
        for m in marks
        if sig.ts_signal_ms <= m.ts_mark_ms <= sig.market_end_ts
    ]
    out.sort(key=lambda m: m.seq)
    return out


def exit_ev(sig: Signal, marks: list[Mark]) -> dict:
    """
    Causal TP50/SL30 replay over recorded mark_path only. Shared across
    FILLED_ACTIVE and VALID_HOLDOUT_SHADOW (entry priced identically).
    """
    if sig.fill_decision not in FillDecision.EV_ELIGIBLE:
        raise ForensicError(
            f"exit_ev called on EV-excluded decision {sig.fill_decision}"
        )
    entry = D(sig.exec_ask_vwap)
    assert_entry_parity(sig, entry)
    held = D(sig.exec_fill_qty_avail)
    cost = realized_cost(sig)  # buffer excluded

    for m in _eligible_marks(sig, marks):
        assert_no_lookahead(m.knowable_ts, m.ts_mark_ms)
        # unexecutable / blocked / stale -> cannot transact; skip (not a free wait)
        if not is_clean_executable(m):
            continue
        proceeds = exit_mark_value(m.exit_mark_status, m.exit_mark_vwap) * held
        pnl = _pnl_pct(proceeds, cost)
        # SL precedence / worst-case-first if a tick appears to cross both barriers
        if pnl <= SL_PCT:
            return _exit_outcome("STOP_LOSS_30", sig, m, pnl, cost, held)
        if pnl >= TP_PCT:
            return _exit_outcome("TAKE_PROFIT_50", sig, m, pnl, cost, held)

    # never cleanly closed -> terminal conservative forced-fill at LAST mark <= end_ts
    tc = terminal_conservative(_eligible_marks(sig, marks), sig.market_end_ts, held, cost)
    return {
        "signal_id": sig.signal_id,
        "arm": "exit_ev",
        "cohort": sig.fill_decision,
        "outcome": tc.status,
        "entry_price": str(entry),
        "filled_shares": str(tc.filled_shares),
        "residual_shares": str(tc.residual_shares),
        "realized_value": str(tc.realized_value),
        "residual_value": str(tc.residual_value),
        "cost": str(cost),
        "pnl_pct": str(tc.pnl),
    }


def _exit_outcome(outcome, sig, mark, pnl, cost, held) -> dict:
    return {
        "signal_id": sig.signal_id,
        "arm": "exit_ev",
        "cohort": sig.fill_decision,
        "outcome": outcome,
        "entry_price": str(D(sig.exec_ask_vwap)),
        "exit_seq": mark.seq,
        "exit_mark_vwap": str(exit_mark_value(mark.exit_mark_status, mark.exit_mark_vwap)),
        "held_shares": str(held),
        "cost": str(cost),
        "pnl_pct": str(pnl),
    }


def hold_ev(sig: Signal, resolution_row: dict) -> Optional[dict]:
    """
    Hold to finalized resolution; payoff $1 if won else $0. Entry priced as
    market-taker exec_ask_vwap at ts_signal (parity with exit arm).
    """
    if sig.fill_decision not in FillDecision.EV_ELIGIBLE:
        raise ForensicError(
            f"hold_ev called on EV-excluded decision {sig.fill_decision}"
        )
    if not resolution_row or int(resolution_row.get("resolution_finalized", 0)) != 1:
        return {"signal_id": sig.signal_id, "arm": "hold_ev", "outcome": "EXCLUDED_UNFINALIZED"}
    resolved_yes = resolution_row.get("resolved_yes")
    if resolved_yes in ("VOID", "UNRESOLVED"):
        return {"signal_id": sig.signal_id, "arm": "hold_ev", "outcome": f"EXCLUDED_{resolved_yes}"}
    if resolved_yes not in ("0", "1"):
        raise ForensicError(f"unexpected resolved_yes {resolved_yes!r}")

    entry = D(sig.exec_ask_vwap)
    assert_entry_parity(sig, entry)
    held = D(sig.exec_fill_qty_avail)
    cost = realized_cost(sig)  # buffer excluded
    won = _won(sig.side, resolved_yes)
    payoff = held * (Decimal("1") if won else Decimal("0"))
    pnl = _pnl_pct(payoff, cost)
    return {
        "signal_id": sig.signal_id,
        "arm": "hold_ev",
        "cohort": sig.fill_decision,
        "outcome": "WON" if won else "LOST",
        "entry_price": str(entry),
        "payoff": str(payoff),
        "cost": str(cost),
        "pnl_pct": str(pnl),
    }


def _won(side: str, resolved_yes: str) -> bool:
    """side YES/Up wins on resolved_yes=='1'; NO/Down wins on '0'."""
    s = side.upper()
    if s in ("YES", "UP"):
        return resolved_yes == "1"
    if s in ("NO", "DOWN"):
        return resolved_yes == "0"
    raise ForensicError(f"unknown side {side!r}")


def run_four_arms(signals: list[Signal], marks_by_sig: dict, resolutions: dict) -> dict:
    """Dispatch the four EV arms over EV-eligible cohorts only."""
    arms = {
        "hold_ev_FILLED": [],
        "exit_ev_FILLED": [],
        "hold_ev_HOLDOUT": [],
        "exit_ev_HOLDOUT": [],
    }
    for sig in signals:
        if sig.fill_decision == FillDecision.FILLED_ACTIVE:
            arms["hold_ev_FILLED"].append(hold_ev(sig, resolutions.get(sig.condition_id)))
            arms["exit_ev_FILLED"].append(exit_ev(sig, marks_by_sig.get(sig.signal_id, [])))
        elif sig.fill_decision == FillDecision.VALID_HOLDOUT_SHADOW:
            arms["hold_ev_HOLDOUT"].append(hold_ev(sig, resolutions.get(sig.condition_id)))
            arms["exit_ev_HOLDOUT"].append(exit_ev(sig, marks_by_sig.get(sig.signal_id, [])))
        # EV_EXCLUDED (incl. UNFILLED_SHADOW_CAP_REACHED) -> not in any arm
    return arms


# =============================================================================
# 6. Deterministic / seeded stratified holdout (FIFO BANNED)
# =============================================================================
def edge_bucket(entry_edge: Decimal) -> str:
    e = D(entry_edge)
    if e < Decimal("0.15"):
        return "lt_0.15"
    if e < Decimal("0.25"):
        return "0.15_0.25"
    if e < Decimal("0.40"):
        return "0.25_0.40"
    return "ge_0.40"


def tte_bucket(tte_s: int) -> str:
    if tte_s < 180:
        return "lt_3m"
    if tte_s < 420:
        return "3m_7m"
    if tte_s < 720:
        return "7m_12m"
    return "ge_12m"


def stratum_key(asset: str, side: str, edge_b: str, tte_b: str) -> str:
    return f"{asset}|{side}|{edge_b}|{tte_b}"


def passes_active_executable_criteria(sig_candidate: dict) -> bool:
    """
    A signal is holdout-comparable ONLY if it passes 100% of active executable
    criteria: depth OK, edge>=floor, quote fresh, sellback OK. Anything failing
    becomes UNFILLED_* and is excluded from EV arms.
    """
    return (
        sig_candidate.get("depth_ok") is True
        and D(sig_candidate.get("entry_edge", "0")) >= Decimal("0.15")
        and int(sig_candidate.get("quote_age_ms", 10 ** 9)) <= QUOTE_STALE_MS
        and sig_candidate.get("sellback_ok") is True
    )


def deterministic_holdout_decision(
    signal_id: str,
    stratum: str,
    holdout_fraction: Decimal,
    stratum_admitted_count: int,
    stratum_cap: int,
) -> str:
    """
    Deterministic seeded admission within a stratum (no FIFO, no wall-clock).
    Returns FILLED_ACTIVE / VALID_HOLDOUT_SHADOW / UNFILLED_SHADOW_CAP_REACHED.
    """
    h = hashlib.sha256(f"{stratum}|{signal_id}".encode()).hexdigest()
    bucket = Decimal(int(h[:8], 16)) / Decimal(0xFFFFFFFF)  # in [0,1]
    if bucket >= holdout_fraction:
        return FillDecision.FILLED_ACTIVE
    # diverted to holdout, subject to per-stratum cap
    if stratum_admitted_count >= stratum_cap:
        return FillDecision.UNFILLED_SHADOW_CAP_REACHED  # diagnostics-only
    return FillDecision.VALID_HOLDOUT_SHADOW


# =============================================================================
# 7. Resolution / token-outcome binding (condition_id join only, never slug)
# =============================================================================
def assert_token_outcome_binding(
    condition_id: str,
    token_id: str,
    outcome_index: int,
    outcome_label: str,
    market_metadata: dict,
) -> str:
    """
    The winner token_id must belong to condition_id AND map to the expected
    positional outcome_index/outcome_label (G.2c positional binding). Join is on
    condition_id ONLY — slug is documentary and never used here.

    Returns Forensic.TOKEN_BIND_PASS or raises -> FAIL_TOKEN_OUTCOME_BINDING.
    """
    if market_metadata.get("condition_id") != condition_id:
        raise ForensicError(Forensic.TOKEN_BIND_FAIL + ": condition_id mismatch")
    token_ids = list(market_metadata.get("clobTokenIds", []))
    outcomes = list(market_metadata.get("outcomes", []))
    if not (0 <= outcome_index < len(token_ids)):
        raise ForensicError(Forensic.TOKEN_BIND_FAIL + ": outcome_index out of range")
    if token_ids[outcome_index] != token_id:
        raise ForensicError(Forensic.TOKEN_BIND_FAIL + ": token_id ↮ outcome_index")
    if outcome_index < len(outcomes) and outcomes[outcome_index] != outcome_label:
        raise ForensicError(Forensic.TOKEN_BIND_FAIL + ": outcome_label mismatch")
    return Forensic.TOKEN_BIND_PASS


def resolution_is_usable_for_final_ev(resolution_row: dict) -> bool:
    """Provisional/unfinalized excluded; VOID/UNRESOLVED are separate buckets."""
    if int(resolution_row.get("resolution_finalized", 0)) != 1:
        return False
    return resolution_row.get("resolved_yes") in ("0", "1")


# =============================================================================
# Hash-chain helpers (tamper-evident append log)
# =============================================================================
def canonical_row_hash(row: dict, exclude=("row_hash",)) -> str:
    payload = {k: v for k, v in row.items() if k not in exclude}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def verify_hash_chain(rows: list[dict]) -> bool:
    """Verify prev_row_hash linkage; break => tamper flag (False)."""
    prev = "GENESIS"
    for r in rows:
        if r.get("prev_row_hash") != prev:
            return False
        if canonical_row_hash(r) != r.get("row_hash"):
            return False
        prev = r["row_hash"]
    return True


# =============================================================================
# 8. Summary classification builder (two orthogonal axes)
# =============================================================================
@dataclass
class ForensicSummary:
    axis1: str = Forensic.SCHEMA_PASS          # schema/integrity verdict
    axis2: str = Forensic.INSUFFICIENT_EFFECTIVE_N  # alpha-inference eligibility
    fails: list = field(default_factory=list)
    partials: list = field(default_factory=list)
    notes: dict = field(default_factory=dict)


def build_summary(
    schema_ok: bool,
    lookahead_clean: bool,
    resolution_join_ok: bool,
    token_binding_ok: bool,
    census_ok: bool,
    cap_dropped_fraction: Decimal,
    any_arm_zero_samples: bool,
    effective_n_ok: bool,
) -> ForensicSummary:
    """
    Axis 1 (schema/integrity) and Axis 2 (alpha eligibility) are INDEPENDENT.
    Low effective-N NEVER turns a schema pass into a schema failure, and a
    schema failure is NEVER excused by adequate effective-N.
    """
    s = ForensicSummary()

    # --- Axis 1: schema/integrity ---
    if not lookahead_clean:
        s.fails.append(Forensic.FAIL_LOOKAHEAD_RISK)
    if not resolution_join_ok:
        s.fails.append(Forensic.FAIL_RESOLUTION_JOIN)
    if not token_binding_ok:
        s.fails.append(Forensic.FAIL_TOKEN_OUTCOME_BINDING)
    if not census_ok or not schema_ok:
        s.fails.append(Forensic.FAIL_CENSUS_RECONCILIATION)

    if cap_dropped_fraction > Decimal("0.10"):
        s.partials.append(Forensic.PARTIAL_CAP_BIASED)
    if any_arm_zero_samples:
        s.partials.append(Forensic.PARTIAL_NOT_EXERCISED)

    # precedence within Axis 1 only
    if s.fails:
        s.axis1 = s.fails[0]
    elif s.partials:
        s.axis1 = s.partials[0]
    else:
        s.axis1 = Forensic.SCHEMA_PASS

    # --- Axis 2: alpha-inference eligibility (orthogonal) ---
    s.axis2 = (
        Forensic.ALPHA_INFERENCE_ELIGIBLE
        if effective_n_ok
        else Forensic.INSUFFICIENT_EFFECTIVE_N
    )
    s.notes["cap_dropped_fraction"] = str(cap_dropped_fraction)
    return s


# =============================================================================
# 9. Diagnostics placeholders (skeletons — pure, offline, no API)
# =============================================================================
# --- 9a. Sentinel-safe arm aggregation primitives ---------------------------
# Arm result rows carry a numeric "pnl_pct" ONLY for computed outcomes
# (WON/LOST/TP/SL/terminal). Excluded buckets (EXCLUDED_UNFINALIZED / _VOID /
# _UNRESOLVED) carry no pnl_pct and are skipped — never coerced. D() additionally
# refuses any NOT_COMPUTED_* sentinel string, so aggregate sums can never run
# numeric math on a sentinel.
def _arm_pnls(rows) -> list:
    out = []
    for r in rows:
        if r is None or "pnl_pct" not in r:
            continue  # excluded / no-numeric-pnl bucket
        out.append(D(r["pnl_pct"]))  # D() raises SentinelMathError on any sentinel
    return out


def _mean(values):
    if not values:
        return None
    return sum(values) / Decimal(len(values))


def _sub(a, b):
    """None-safe subtraction; either operand None (empty cohort) -> None."""
    if a is None or b is None:
        return None
    return a - b


def aggregate_arms(arms: dict) -> dict:
    """
    1. EV arm aggregations — mean realized pnl_pct per arm + per-arm numeric N.
    Each arm aggregated INDEPENDENTLY (no cross-arm summing -> no double penalty:
    a holdout signal contributes once to its hold arm and once to its exit arm,
    never combined into a single doubled figure).
    """
    return {
        "hold_ev_FILLED": _mean(_arm_pnls(arms.get("hold_ev_FILLED", []))),
        "exit_ev_FILLED": _mean(_arm_pnls(arms.get("exit_ev_FILLED", []))),
        "hold_ev_HOLDOUT": _mean(_arm_pnls(arms.get("hold_ev_HOLDOUT", []))),
        "exit_ev_HOLDOUT": _mean(_arm_pnls(arms.get("exit_ev_HOLDOUT", []))),
        "n": {k: len(_arm_pnls(v)) for k, v in arms.items()},
    }


def delta_diagnostics(arms: dict) -> dict:
    """
    2. Delta diagnostics over aggregated arms:
      exit_bleed     = hold_ev(FILLED)  - exit_ev(FILLED)
      toxicity       = hold_ev(FILLED)  - hold_ev(VALID_HOLDOUT_SHADOW)
      path_toxicity  = exit_ev(FILLED)  - exit_ev(VALID_HOLDOUT_SHADOW)
    """
    agg = aggregate_arms(arms)
    return {
        "exit_bleed": _sub(agg["hold_ev_FILLED"], agg["exit_ev_FILLED"]),
        "toxicity": _sub(agg["hold_ev_FILLED"], agg["hold_ev_HOLDOUT"]),
        "path_toxicity": _sub(agg["exit_ev_FILLED"], agg["exit_ev_HOLDOUT"]),
    }


def diag_cap_selection_bias(arms: dict) -> dict:
    """
    3a. Cap/holdout selection bias (admitted-fill cohort vs comparable holdout):
      cap_selection_bias      = hold_ev(FILLED) - hold_ev(VALID_HOLDOUT_SHADOW)
      path_cap_selection_bias = exit_ev(FILLED) - exit_ev(VALID_HOLDOUT_SHADOW)
    """
    agg = aggregate_arms(arms)
    return {
        "cap_selection_bias": _sub(agg["hold_ev_FILLED"], agg["hold_ev_HOLDOUT"]),
        "path_cap_selection_bias": _sub(agg["exit_ev_FILLED"], agg["exit_ev_HOLDOUT"]),
    }


def diag_admitted_vs_capped(signals) -> dict:
    """3b. Admitted-vs-capped distribution by stratum (counts only, no pricing)."""
    dist = {}
    for s in signals:
        strat = stratum_key(s.asset, s.side, s.edge_bucket, s.tte_bucket)
        slot = dist.setdefault(strat, {"admitted": 0, "capped": 0, "active": 0})
        if s.fill_decision == FillDecision.VALID_HOLDOUT_SHADOW:
            slot["admitted"] += 1
        elif s.fill_decision == FillDecision.UNFILLED_SHADOW_CAP_REACHED:
            slot["capped"] += 1
        elif s.fill_decision == FillDecision.FILLED_ACTIVE:
            slot["active"] += 1
    return dist


def diag_effective_n(signals) -> dict:
    """
    3c. effective-N / independence warning.
    STATISTICAL_INDEPENDENCE_WARNING if unique underlying assets < 3 OR unique
    market windows (distinct condition_id) < 3. effective_n_ok gates alpha
    inference ONLY (Axis 2); it never invalidates schema validation (Axis 1).
    """
    ev_signals = [s for s in signals if s.fill_decision in FillDecision.EV_ELIGIBLE]
    assets = {s.asset for s in ev_signals}
    windows = {s.condition_id for s in ev_signals}
    warning = (len(assets) < 3) or (len(windows) < 3)
    return {
        "raw_trade_count": len(ev_signals),
        "unique_underlying_assets": len(assets),
        "unique_market_windows": len(windows),
        "statistical_independence_warning": warning,
        "effective_n_ok": not warning,
    }


def build_dual_axis_summary(signals, arms, integrity=None,
                            cap_dropped_fraction=Decimal("0")) -> "ForensicSummary":
    """
    4. Dual-axis classification. Axis 1 (schema/integrity) and Axis 2 (alpha
    eligibility) are independent: FORENSIC_SCHEMA_PASS and
    FORENSIC_INSUFFICIENT_EFFECTIVE_N can coexist.
    """
    integrity = integrity or {}
    eff = diag_effective_n(signals)
    any_arm_zero = any(len(_arm_pnls(arms.get(k, []))) == 0
                       for k in ("hold_ev_FILLED", "exit_ev_FILLED",
                                 "hold_ev_HOLDOUT", "exit_ev_HOLDOUT"))
    return build_summary(
        schema_ok=integrity.get("schema_ok", True),
        lookahead_clean=integrity.get("lookahead_clean", True),
        resolution_join_ok=integrity.get("resolution_join_ok", True),
        token_binding_ok=integrity.get("token_binding_ok", True),
        census_ok=integrity.get("census_ok", True),
        cap_dropped_fraction=D(cap_dropped_fraction),
        any_arm_zero_samples=any_arm_zero,
        effective_n_ok=eff["effective_n_ok"],
    )


# --- 9d. Per-signal model/execution diagnostics -----------------------------
# TELEMETRY ISOLATION: every function below ONLY reads and buckets
# already-recorded signals/marks/arm results. None of them touch fill routing,
# holdout admission, TP50/SL30 logic, or hold_ev/exit_ev execution. They return
# diagnostic dicts and mutate nothing. G.5 remains forensic observation only.
def _hold_pnl_by_signal(arms: dict) -> dict:
    """signal_id -> Decimal(hold pnl_pct) for rows that produced a numeric pnl."""
    out = {}
    for key in ("hold_ev_FILLED", "hold_ev_HOLDOUT"):
        for r in arms.get(key, []):
            if r is None or "pnl_pct" not in r:
                continue
            out[r["signal_id"]] = D(r["pnl_pct"])
    return out


def _decile(frac: Decimal) -> str:
    """Map a [0,1] value to a decile-bucket label '0.0-0.1' ... '0.9-1.0'."""
    f = D(frac)
    if f < 0:
        f = Decimal("0")
    if f >= 1:
        return "0.9-1.0"
    lo = (f * 10).to_integral_value(rounding="ROUND_FLOOR")
    return f"{lo/10}-{(lo+1)/10}"


def diag_calibration_curve(signals, resolutions) -> dict:
    """fair_yes decile vs realized resolved_yes rate (model reliability)."""
    buckets = {}
    for s in signals:
        if s.fill_decision not in FillDecision.EV_ELIGIBLE:
            continue
        res = resolutions.get(s.condition_id)
        if not res or not resolution_is_usable_for_final_ev(res):
            continue
        b = _decile(D(s.fair_yes))
        slot = buckets.setdefault(b, {"n": 0, "sum_fair": Decimal("0"), "yes": 0})
        slot["n"] += 1
        slot["sum_fair"] += D(s.fair_yes)
        slot["yes"] += 1 if res["resolved_yes"] == "1" else 0
    for b, slot in buckets.items():
        n = slot["n"]
        slot["mean_fair_yes"] = slot["sum_fair"] / Decimal(n) if n else None
        slot["realized_yes_rate"] = Decimal(slot["yes"]) / Decimal(n) if n else None
    return buckets


def diag_modeled_edge_vs_hold_pnl(signals, arms) -> dict:
    """Does modeled edge predict hold EV? mean hold pnl_pct per edge_bucket."""
    hold = _hold_pnl_by_signal(arms)
    buckets = {}
    for s in signals:
        if s.signal_id not in hold:
            continue
        slot = buckets.setdefault(s.edge_bucket, [])
        slot.append(hold[s.signal_id])
    return {b: {"n": len(v), "mean_hold_pnl_pct": _mean(v)} for b, v in buckets.items()}


def diag_edge_realization_gap(signals, arms) -> dict:
    """
    Per-signal edge_realization_gap = modeled_entry_edge - realized_hold_fraction
    (realized_hold_fraction = hold pnl_pct / 100). Positive & large => modeled
    edge failed to realize (edge evaporation). Returns per-signal + mean.
    """
    hold = _hold_pnl_by_signal(arms)
    per = {}
    for s in signals:
        if s.signal_id not in hold:
            continue
        realized_frac = hold[s.signal_id] / Decimal("100")
        per[s.signal_id] = D(s.entry_edge) - realized_frac
    return {"per_signal": per, "mean_gap": _mean(list(per.values()))}


def diag_first_30s_mark_drift(signals, marks_by_sig) -> dict:
    """
    Early post-entry drift within 30s of entry, by edge_bucket. Drift =
    (exit_mark_vwap - exec_ask_vwap)/exec_ask_vwap on the latest CLEAN executable
    mark with elapsed_ms_since_signal <= 30000. Sentinel/blocked marks skipped
    (never coerced). Negative drift => adverse immediate post-entry move.
    """
    sig_by_id = {s.signal_id: s for s in signals}
    by_bucket = {}
    per = {}
    for sid, marks in marks_by_sig.items():
        s = sig_by_id.get(sid)
        if s is None:
            continue
        entry = D(s.exec_ask_vwap)
        window = [m for m in marks
                  if int(m.elapsed_ms_since_signal) <= 30000 and is_clean_executable(m)]
        if not window:
            continue
        m = max(window, key=lambda mm: mm.ts_mark_ms)
        drift = (exit_mark_value(m.exit_mark_status, m.exit_mark_vwap) - entry) / entry
        per[sid] = drift
        by_bucket.setdefault(s.edge_bucket, []).append(drift)
    return {
        "per_signal": per,
        "by_edge_bucket": {b: {"n": len(v), "mean_drift": _mean(v)}
                           for b, v in by_bucket.items()},
    }


def _reference_age_bucket(age_ms: int) -> str:
    a = int(age_ms)
    if a < 500:
        return "lt_500ms"
    if a < 2000:
        return "500_2000ms"
    if a < 5000:
        return "2000_5000ms"
    return "ge_5000ms"


def diag_reference_age_buckets(signals, arms) -> dict:
    """Stale-feed adverse fills: mean hold pnl_pct per reference_age bucket."""
    hold = _hold_pnl_by_signal(arms)
    buckets = {}
    for s in signals:
        if s.signal_id not in hold:
            continue
        buckets.setdefault(_reference_age_bucket(s.reference_age_ms), []).append(
            hold[s.signal_id])
    return {b: {"n": len(v), "mean_hold_pnl_pct": _mean(v)} for b, v in buckets.items()}


def _spread_bucket(spread_pct: Decimal) -> str:
    sp = D(spread_pct)
    if sp < Decimal("0.02"):
        return "tight_lt2pct"
    if sp < Decimal("0.05"):
        return "mid_2_5pct"
    return "wide_ge5pct"


def _depth_bucket(depth: Decimal) -> str:
    d = D(depth)
    if d < Decimal("10"):
        return "thin_lt10"
    if d < Decimal("50"):
        return "mid_10_50"
    return "deep_ge50"


def diag_spread_depth_tte_buckets(signals, arms) -> dict:
    """mean hold pnl_pct per (spread, depth, tte) bucket — isolates bad strata."""
    hold = _hold_pnl_by_signal(arms)
    buckets = {}
    for s in signals:
        if s.signal_id not in hold:
            continue
        key = f"{_spread_bucket(s.ask_spread_pct)}|{_depth_bucket(s.ask_depth_avail)}|{tte_bucket(s.tte_s)}"
        buckets.setdefault(key, []).append(hold[s.signal_id])
    return {b: {"n": len(v), "mean_hold_pnl_pct": _mean(v)} for b, v in buckets.items()}


# =============================================================================
# Hard execution guard + main
# =============================================================================
def _banner() -> str:
    return (
        "Gate G.5 Forensic Engine (DRAFT)\n"
        f"  Live S1: {LIVE_S1_STATE}\n"
        f"  S1 append: {LIVE_S1_APPEND}\n"
        f"  capacity: {LIVE_S1_CAPACITY}\n"
        f"  wallet/capital: {WALLET_CAPITAL}\n"
        "  NO real orders. /tmp artifacts only. Measurement, not strategy.\n"
    )


def main(argv=None) -> int:
    """
    HARD EXECUTION GUARD: refuses to run unless GATEG5_ARM=START-RUNNER-CONFIRMED.
    Unarmed invocation prints the reason and exits WITHOUT creating a run root.
    """
    sys.stderr.write(_banner())
    arm = os.environ.get(ARM_ENV, "")
    if arm != ARM_TOKEN:
        sys.stderr.write(
            f"[GUARD] {ARM_ENV} != {ARM_TOKEN!r} (got {arm!r}). "
            "Runner is UNARMED — refusing to execute. No run root created. "
            "No DB, no capture, no orders.\n"
        )
        return 2

    # --- ARMED PATH (intentionally NOT implemented in this draft) ---
    # A future, separately authorized build would, only here:
    #   * create the /tmp/hasan-gateg5-<stamp> run root,
    #   * init_schema() on a fresh SQLite DB,
    #   * load captured signal_log/mark_path/resolution rows,
    #   * run_four_arms(), diagnostics, build_summary(),
    #   * write an immutable forensic report.
    # This draft deliberately leaves the armed path inert.
    sys.stderr.write(
        "[GUARD] ARMED token present, but this DRAFT does not implement the "
        "armed execution path. Exiting without side effects.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
