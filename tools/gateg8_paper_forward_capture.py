#!/usr/bin/env python3
"""
Gate G8 — Forward Paper Dual-Book Capture (entry-only; NO resolution, NO orders).

Connects the committed bidirectional fee-aware paper selector (analysis.forensic.
gateg7_paper_pnl) to real entry-time YES and NO CLOB books so a future bounded run can
create genuine paper decisions. PAPER/SHADOW ONLY.

HARD BOUNDARIES:
  * PUBLIC read-only GET only (Gamma market listing reused from the caller; CLOB book x2).
    NO auth, NO wallet, NO signing, NO capital, NO orders.
  * NO resolution fetch anywhere in this module. NO terminal PnL computed here.
  * NO S1 access. Live S1 stays CREATED_EMPTY_LOCKED_CONTAINER; append DENIED.
  * Exactly TWO CLOB book GETs per evaluated market (YES + NO), SEQUENTIAL (no existing
    async CLOB client to reuse -- building one would be new infrastructure, out of scope).
    No retry.
  * Inert unless armed: GATEG8_PAPER_ARM=BIDIRECTIONAL-PAPER-CONFIRMED (default OFF).
  * This module does NOT authorize or perform a live run. PAPER_OPEN is the first
    position-taking artifact and requires a SEPARATE, explicitly reviewed authorization.
"""
from __future__ import annotations

import os
import sqlite3
from decimal import Decimal

from analysis.forensic import gateg5_model as gm
from analysis.forensic import gateg7_paper_pnl as pp
from tools.gateg5_telemetry_runner import (
    CLOB_BOOK, TARGET_INTERVAL_S, TransportError,
    _hl_price_feedts as _default_hl_price_feedts,
    _hl_sigma_annual as _default_hl_sigma_annual,
    _public_get as _default_public_get,
)

PAPER_ARM_ENV = "GATEG8_PAPER_ARM"
PAPER_ARM_TOKEN = "BIDIRECTIONAL-PAPER-CONFIRMED"
DEFAULT_STAKE = Decimal("25")

_LEDGER_COLS = [
    "condition_id", "slug", "asset", "window", "paper_decision_ts", "fair_yes",
    "reference_age_ms", "tte_s", "yes_token_id", "no_token_id", "yes_quote_ts_ms",
    "no_quote_ts_ms", "yes_capture_started_ms", "yes_capture_completed_ms",
    "no_capture_started_ms", "no_capture_completed_ms", "dual_book_skew_ms",
    "yes_exec_ask_vwap", "yes_filled_qty", "no_exec_ask_vwap", "no_filled_qty",
    "fee_rate", "fee_exponent", "yes_gross_edge", "yes_net_edge", "no_gross_edge",
    "no_net_edge", "selected_side", "selected_token_id", "no_entry_reason",
    "selected_filled_qty", "selected_entry_notional", "status",
]


def is_armed() -> bool:
    return os.environ.get(PAPER_ARM_ENV, "") == PAPER_ARM_TOKEN


def init_paper_ledger(conn) -> None:
    """Fresh isolated paper table (TEXT/INTEGER only; never REAL). This is paper evidence
    ONLY -- never signal_log, never Live S1, never wallet/order code."""
    cols_sql = ",".join(f"{c} TEXT" if c not in
                        ("paper_decision_ts", "reference_age_ms", "tte_s", "yes_quote_ts_ms",
                         "no_quote_ts_ms", "yes_capture_started_ms", "yes_capture_completed_ms",
                         "no_capture_started_ms", "no_capture_completed_ms", "dual_book_skew_ms",
                         "fee_exponent")
                        else f"{c} INTEGER" for c in _LEDGER_COLS)
    conn.execute(f"CREATE TABLE IF NOT EXISTS gateg8_paper_ledger(id INTEGER PRIMARY KEY, {cols_sql})")
    conn.commit()


def write_paper_ledger(conn, decision: dict) -> None:
    """Persist one paper decision row. Never touches signal_log/mark_path/S1."""
    conn.execute(
        f"INSERT INTO gateg8_paper_ledger({','.join(_LEDGER_COLS)}) "
        f"VALUES ({','.join('?' for _ in _LEDGER_COLS)})",
        tuple(decision.get(c) for c in _LEDGER_COLS))


def _fetch_book(token_id: str, *, now_ms_provider, public_get) -> dict:
    """One CLOB book GET; records capture-start/complete around it. No retry."""
    started = now_ms_provider()
    raw = public_get(CLOB_BOOK, {"token_id": token_id})
    completed = now_ms_provider()
    ts = raw.get("timestamp", completed)
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        ts = completed
    asks = [[lvl["price"], lvl["size"]] for lvl in raw.get("asks", [])]
    return {"asks": asks, "quote_ts_ms": ts,
            "capture_started_ms": started, "capture_completed_ms": completed}


def capture_and_decide(market: dict, *, now_ms_provider, max_skew_ms: int,
                       book_fetch_client=None, hl_price_feedts=None, hl_sigma_annual=None,
                       intended_stake: Decimal = DEFAULT_STAKE,
                       cost_buffer: Decimal = Decimal("0")) -> dict:
    """One full entry-time decision cycle for one market. `market` must already carry the
    Gamma fields needed for binding/fees (conditionId, slug, asset, outcomes, clobTokenIds,
    market_end_ts, feesEnabled, feeSchedule) -- NO extra Gamma fetch happens here.

    Exactly TWO CLOB book GETs (YES then NO, sequential -- no existing async CLOB client to
    reuse), then HL fair-value inputs, THEN `paper_decision_ts` is stamped -- only after every
    entry input above is available. Delegates all edge/fee/selection math to the COMMITTED
    analysis.forensic.gateg7_paper_pnl.build_paper_decision (never duplicated here).
    """
    public_get = book_fetch_client or _default_public_get
    hl_pf = hl_price_feedts or _default_hl_price_feedts
    hl_sig = hl_sigma_annual or _default_hl_sigma_annual

    binding = pp.bind_yes_no_tokens(market["outcomes"], market["clobTokenIds"])  # fail closed first

    yes_book = _fetch_book(binding["yes_token_id"], now_ms_provider=now_ms_provider,
                           public_get=public_get)   # GET #1
    no_book = _fetch_book(binding["no_token_id"], now_ms_provider=now_ms_provider,
                          public_get=public_get)     # GET #2 (sequential; no retry)

    now_ms = max(yes_book["capture_completed_ms"], no_book["capture_completed_ms"])
    p_now, feed_ts = hl_pf(market["asset"], now_ms)
    window_start_ms = (market["market_end_ts"] - TARGET_INTERVAL_S) * 1000
    strike, _ = hl_pf(market["asset"], window_start_ms)
    sigma_annual = hl_sig(market["asset"], now_ms)
    hl_done_ms = now_ms_provider()

    tte_s = market["market_end_ts"] - (hl_done_ms // 1000)
    if tte_s <= 0:
        raise gm.ModelInputError("nonpositive tte for market window")
    tte_years = Decimal(tte_s) / gm.SECONDS_PER_YEAR
    fair_yes = gm.fair_yes_gbm(p_now, strike, sigma_annual, tte_years)

    decision_ts = now_ms_provider()   # stamped ONLY after every input above is available

    return pp.build_paper_decision(
        market=market, yes_book=yes_book, no_book=no_book, fair_yes=fair_yes, feed_ts=feed_ts,
        tte_s=tte_s, max_skew_ms=max_skew_ms, decision_ts=decision_ts,
        intended_stake=intended_stake, cost_buffer=cost_buffer)
