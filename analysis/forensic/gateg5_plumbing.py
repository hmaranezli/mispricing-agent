#!/usr/bin/env python3
"""
Gate G.5 — Live→Offline Translation Plumbing (DRAFT — DO NOT RUN AS RUNNER)

Boundary:  mock API payload -> normalizer -> G.5 Signal/Mark dataclasses
           -> mock SQLite writer (G.5 signal_log / mark_path schemas).

HARD BOUNDARIES (constitution + Hasan authorization):
  * NO network, NO API polling, NO time.time()/wall-clock in core normalization.
  * Deterministic: caller injects capture_ts_ms / now_ms / reference_feed_ts.
  * Decimal-safe only; no binary float money math. SQLite REAL banned.
  * NO Live S1 access. Live S1 CREATED_EMPTY_LOCKED_CONTAINER; append DENIED.
  * Mock SQLite under /tmp only. capacity 0. wallet/capital BLOCKED.

This module computes NOTHING on import and opens NO database on import.
It imports the PUBLISHED, feature-locked forensic engine read-only for its
dataclasses, sentinel enums, Decimal helpers, schema DDL, and hash-chain.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

# --- read-only import of the published, feature-locked forensic engine ---
from analysis.forensic import gateg5_forensic_engine as engine

D = engine.D
ExitMarkStatus = engine.ExitMarkStatus
FillDecision = engine.FillDecision
QUOTE_STALE_MS = engine.QUOTE_STALE_MS


# =============================================================================
# Error taxonomy (all fail closed; never silent, never raw KeyError to caller)
# =============================================================================
class PlumbingError(engine.ForensicError):
    """Base for normalization/writer integrity violations."""


class MalformedLevelError(PlumbingError):
    """A price/size is non-finite, non-numeric, null, or out of bounds."""


class CrossedBookError(PlumbingError):
    """top_bid >= top_ask (crossed/locked book) — no edge may be computed."""


class IdentityError(PlumbingError):
    """Missing/ambiguous identity field (token_id, condition_id, market_end_ts, outcome)."""


class TimestampError(PlumbingError):
    """Causality/timestamp disorder (negative age, quote after market_end_ts)."""


# =============================================================================
# Decimal hardening — strict numeric coercion (rejects NaN/Inf/null/junk)
# =============================================================================
def _strict_decimal(value, kind: str) -> Decimal:
    """Coerce to a FINITE Decimal or raise MalformedLevelError.

    Rejects None, bool, non-numeric strings, and NaN/Infinity/-Infinity.
    """
    if value is None or isinstance(value, bool):
        raise MalformedLevelError(f"{kind} is null/bool: {value!r}")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise MalformedLevelError(f"{kind} not numeric: {value!r}") from exc
    if not d.is_finite():
        raise MalformedLevelError(f"{kind} non-finite: {value!r}")
    return d


def _validate_price_size(price: Decimal, size: Decimal) -> None:
    """Polymarket binary outcome token: 0 < price <= 1 and size > 0."""
    if price <= 0 or price > 1:
        raise MalformedLevelError(f"price out of (0,1] bounds: {price}")
    if size <= 0:
        raise MalformedLevelError(f"size must be > 0: {size}")


# =============================================================================
# Ladder ingestion — validate, merge duplicate prices, sort deterministically
# =============================================================================
def _canonical_levels(raw_levels) -> list[tuple[Decimal, Decimal]]:
    """Validate every level; MERGE duplicate prices (sum sizes); SORT ascending.

    Policy (deterministic): duplicate price rows are summed; the canonical ladder
    is always sorted by price ascending. Side-specific best-first ordering is
    applied by parse_ask_ladder / parse_bid_ladder.
    """
    merged: dict[Decimal, Decimal] = {}
    for level in (raw_levels or []):
        if not (isinstance(level, (list, tuple)) and len(level) == 2):
            raise MalformedLevelError(f"level must be [price,size]: {level!r}")
        price = _strict_decimal(level[0], "price")
        size = _strict_decimal(level[1], "size")
        _validate_price_size(price, size)
        merged[price] = merged.get(price, Decimal("0")) + size
    return sorted(merged.items(), key=lambda lv: lv[0])  # ascending by price


def ladder_to_decimal_json(raw_levels) -> str:
    """Canonical Decimal-string JSON (validated, merged, ascending)."""
    levels = _canonical_levels(raw_levels)
    return json.dumps([[str(p), str(s)] for p, s in levels], separators=(",", ":"))


def parse_ask_ladder(ask_ladder_json: str) -> list[tuple[Decimal, Decimal]]:
    """[(price,size), ...] best (lowest) ask first."""
    raw = json.loads(ask_ladder_json) if ask_ladder_json else []
    return [( _strict_decimal(p, "price"), _strict_decimal(s, "size")) for p, s in raw]


def parse_bid_ladder(bid_ladder_json: str) -> list[tuple[Decimal, Decimal]]:
    """[(price,size), ...] best (highest) bid first."""
    raw = json.loads(bid_ladder_json) if bid_ladder_json else []
    levels = [( _strict_decimal(p, "price"), _strict_decimal(s, "size")) for p, s in raw]
    levels.sort(key=lambda lv: lv[0], reverse=True)
    return levels


def best_ask(ask_ladder_json: str) -> Optional[tuple[Decimal, Decimal]]:
    levels = parse_ask_ladder(ask_ladder_json)
    return levels[0] if levels else None


def best_bid(bid_ladder_json: str) -> Optional[tuple[Decimal, Decimal]]:
    levels = parse_bid_ladder(bid_ladder_json)
    return levels[0] if levels else None


def total_book_ask_notional(ask_ladder_json: str) -> Decimal:
    """DIAGNOSTIC ONLY — whole-book ask notional = sum(price*size) over ALL ask
    levels. This is NOT the executable entry cost and NOT the entry VWAP; for the
    stake-clamped executable entry use walk_ask_ladder_for_stake(). Decimal-safe.
    """
    total = Decimal("0")
    for price, size in parse_ask_ladder(ask_ladder_json):
        total += price * size
    return total


def ask_spread_pct(ask_ladder_json: str, bid_ladder_json: str) -> Decimal:
    """(best_ask - best_bid)/mid, mid=(best_ask+best_bid)/2. Decimal-safe.

    Rejects a crossed/locked book (best_bid >= best_ask) — no edge on a crossed book.
    """
    ba = best_ask(ask_ladder_json)
    bb = best_bid(bid_ladder_json)
    if ba is None or bb is None:
        raise PlumbingError("ask_spread_pct requires both a best ask and best bid")
    a, b = ba[0], bb[0]
    if b >= a:
        raise CrossedBookError(f"crossed/locked book: best_bid {b} >= best_ask {a}")
    mid = (a + b) / Decimal("2")
    if mid == 0:
        raise PlumbingError("degenerate mid==0 in ask_spread_pct")
    return (a - b) / mid


# =============================================================================
# Stake-clamped ask ladder walk (executable entry — NOT whole-book sum)
# =============================================================================
@dataclass
class AskFill:
    filled_qty: Decimal          # shares actually buyable for the clamped stake
    fill_cost: Decimal           # USD actually spent (<= intended_stake)
    exec_ask_vwap: Decimal       # fill_cost / filled_qty (executable entry price)
    depth_sufficient: bool       # True iff the full intended stake was absorbed
    residual_unfilled_stake: Decimal  # intended_stake - fill_cost (0 if sufficient)


def walk_ask_ladder_for_stake(levels, intended_stake: Decimal) -> AskFill:
    """Stake-clamped taker walk of ascending ask levels.

    Consumes levels until `intended_stake` USD is filled, STOPPING MID-LEVEL when
    the next level would overshoot. No price improvement, no synthetic depth.
    """
    remaining = intended_stake
    filled = Decimal("0")
    cost = Decimal("0")
    for price, size in levels:
        if remaining <= 0:
            break
        level_notional = price * size
        if level_notional <= remaining:
            filled += size
            cost += level_notional
            remaining -= level_notional
        else:
            take = remaining / price          # partial fill of this level
            filled += take
            cost += remaining
            remaining = Decimal("0")
    vwap = (cost / filled) if filled > 0 else Decimal("0")
    return AskFill(
        filled_qty=filled,
        fill_cost=cost,
        exec_ask_vwap=vwap,
        depth_sufficient=(remaining == 0),
        residual_unfilled_stake=remaining,
    )


def _iso_from_ms(ms: int) -> str:
    """Deterministic UTC ISO string from an injected epoch-ms (NOT wall clock)."""
    sec, msec = divmod(int(ms), 1000)
    dt = datetime.datetime.fromtimestamp(sec, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{msec:03d}Z"


def make_signal_id(condition_id: str, token_id: str, ts_signal_ms: int) -> str:
    return hashlib.sha256(
        f"{condition_id}|{token_id}|{int(ts_signal_ms)}".encode()
    ).hexdigest()


def _require(d: dict, key: str, err=IdentityError):
    """Fetch a required field or raise a smooth typed error (never raw KeyError)."""
    if key not in d or d[key] is None or d[key] == "":
        raise err(f"missing required field: {key!r}")
    return d[key]


def _validate_outcome_mapping(market: dict, token_id: str,
                              outcome_index: int, outcome_label: str) -> None:
    """Reject ambiguous outcome mapping before positional binding."""
    token_ids = market.get("clobTokenIds")
    outcomes = market.get("outcomes")
    if not isinstance(token_ids, list) or not token_ids:
        raise IdentityError("clobTokenIds missing/empty")
    if not isinstance(outcomes, list) or len(outcomes) != len(token_ids):
        raise IdentityError("outcomes/clobTokenIds length mismatch (ambiguous mapping)")
    if not (0 <= outcome_index < len(token_ids)):
        raise IdentityError(f"outcome_index {outcome_index} out of range")
    if token_ids.count(token_id) != 1:
        raise IdentityError(f"token_id {token_id!r} not uniquely placed (ambiguous mapping)")


# =============================================================================
# Normalized carriers
# =============================================================================
@dataclass
class NormalizedSignal:
    signal: "engine.Signal"
    row: dict
    ask_fill: "AskFill"


@dataclass
class NormalizedMark:
    mark: "engine.Mark"
    row: dict


# =============================================================================
# 1. Signal normalizer
# =============================================================================
def normalize_signal(market: dict, book: dict, context: dict, *,
                     capture_ts_ms: int) -> NormalizedSignal:
    """Translate mocked market + CLOB book + model context into a G.5 Signal +
    full signal_log row. Pure & deterministic: NO network, NO wall clock.
    """
    # ---- identity / outcome mapping (smooth rejects; no raw KeyError) ----
    condition_id = _require(market, "condition_id")
    token_id = _require(market, "token_id")
    if "outcome_index" not in market or market["outcome_index"] is None:
        raise IdentityError("missing required field: 'outcome_index'")
    outcome_index = int(market["outcome_index"])
    outcome_label = _require(market, "outcome_label")
    if "market_end_ts" not in market or market["market_end_ts"] is None:
        raise IdentityError("missing required field: 'market_end_ts'")
    market_end_ts = int(market["market_end_ts"])
    _validate_outcome_mapping(market, token_id, outcome_index, outcome_label)
    bind = engine.assert_token_outcome_binding(
        condition_id, token_id, outcome_index, outcome_label, market
    )

    ts_signal_ms = int(capture_ts_ms)
    reference_feed_ts = int(_require(context, "reference_feed_ts"))
    reference_age_ms = ts_signal_ms - reference_feed_ts
    if reference_age_ms < 0:
        raise TimestampError(
            f"negative reference_age_ms ({reference_age_ms}): feed newer than capture")

    # ---- book ingestion (validates levels; rejects crossed book) ----
    ask_json = ladder_to_decimal_json(book["asks"])
    bid_json = ladder_to_decimal_json(book["bids"])
    spread_pct = ask_spread_pct(ask_json, bid_json)   # raises CrossedBookError if crossed
    book_notional = total_book_ask_notional(ask_json)  # diagnostic only

    book_quote_ts_ms = int(_require(book, "quote_ts_ms"))
    if book_quote_ts_ms > market_end_ts * 1000:
        raise TimestampError("quote_ts_ms is after market_end_ts")
    quote_age_ms = ts_signal_ms - book_quote_ts_ms

    # ---- stake-clamped executable entry (NOT whole-book sum) ----
    intended_stake = _strict_decimal(_require(context, "intended_stake"), "intended_stake")
    fill = walk_ask_ladder_for_stake(parse_ask_ladder(ask_json), intended_stake)
    if fill.filled_qty <= 0:
        raise PlumbingError("no ask depth to fill any of intended_stake")
    exec_ask_vwap = fill.exec_ask_vwap

    tte_s = market_end_ts - (ts_signal_ms // 1000)
    entry_edge = _strict_decimal(_require(context, "entry_edge"), "entry_edge")

    fill_decision = context.get("fill_decision")
    if fill_decision is None:
        if quote_age_ms > QUOTE_STALE_MS:
            fill_decision = FillDecision.UNFILLED_QUOTE_STALE
        elif not fill.depth_sufficient:
            fill_decision = FillDecision.UNFILLED_ENTRY_DEPTH_FAIL
        elif entry_edge < Decimal("0.15"):
            fill_decision = FillDecision.UNFILLED_EDGE_LOST
        else:
            fill_decision = FillDecision.FILLED_ACTIVE

    edge_b = engine.edge_bucket(entry_edge)
    tte_b = engine.tte_bucket(tte_s)
    signal_id = make_signal_id(condition_id, token_id, ts_signal_ms)
    knowable_ts = ts_signal_ms

    sig = engine.Signal(
        signal_id=signal_id, ts_signal_ms=ts_signal_ms, knowable_ts=knowable_ts,
        asset=_require(market, "asset"), side=_require(market, "side"),
        condition_id=condition_id, token_id=token_id, outcome_index=outcome_index,
        outcome_label=outcome_label, market_end_ts=market_end_ts,
        intended_stake=str(intended_stake), exec_ask_vwap=str(exec_ask_vwap),
        exec_fill_qty_avail=str(fill.filled_qty),
        decision_cost_buffer=str(_strict_decimal(context["decision_cost_buffer"], "buf")),
        realized_entry_cost=str(_strict_decimal(context["realized_entry_cost"], "rec")),
        realized_fee_cost=str(_strict_decimal(context["realized_fee_cost"], "rfc")),
        fill_decision=fill_decision, edge_bucket=edge_b, tte_bucket=tte_b,
        entry_edge=str(entry_edge),
        fair_yes=str(_strict_decimal(context["fair_yes"], "fair_yes")),
        reference_age_ms=reference_age_ms, tte_s=tte_s,
        ask_spread_pct=str(spread_pct), ask_depth_avail=str(book_notional),
    )

    ba = best_ask(ask_json)
    bid_notional = sum((p * s for p, s in parse_bid_ladder(bid_json)), Decimal("0"))
    cost_components = json.dumps({
        "realized_entry_cost": str(_strict_decimal(context["realized_entry_cost"], "rec")),
        "realized_fee_cost": str(_strict_decimal(context["realized_fee_cost"], "rfc")),
        "decision_cost_buffer": str(_strict_decimal(context["decision_cost_buffer"], "buf")),
    }, separators=(",", ":"))

    row = {
        "signal_id": signal_id, "ts_signal": _iso_from_ms(ts_signal_ms),
        "ts_signal_ms": ts_signal_ms, "knowable_ts": knowable_ts,
        "asset": market["asset"], "side": market["side"], "condition_id": condition_id,
        "token_id": token_id, "outcome_index": outcome_index,
        "outcome_label": outcome_label, "slug": market.get("slug", ""),
        "market_end_ts": market_end_ts,
        "underlying_spot_price": str(_strict_decimal(context["underlying_spot_price"], "spot")),
        "reference_price": str(_strict_decimal(context["reference_price"], "ref")),
        "reference_feed_ts": reference_feed_ts, "reference_age_ms": reference_age_ms,
        "fair_yes": str(_strict_decimal(context["fair_yes"], "fair_yes")),
        "fair_yes_sigma": str(_strict_decimal(context["fair_yes_sigma"], "sigma")),
        "fair_model_version": context["fair_model_version"],
        "strike": str(_strict_decimal(context["strike"], "strike")), "tte_s": tte_s,
        "ask_ladder_json": ask_json, "bid_ladder_json": bid_json,
        "book_hash": hashlib.sha256(f"{ask_json}|{bid_json}".encode()).hexdigest(),
        "top_ask_price": str(ba[0]) if ba else "0",
        "top_ask_size": str(ba[1]) if ba else "0",
        "intended_stake": str(intended_stake), "book_ask_vwap": str(exec_ask_vwap),
        "book_bid_vwap": str(bid_notional), "exec_ask_vwap": str(exec_ask_vwap),
        "exec_fill_qty_avail": str(fill.filled_qty),
        "decision_cost_buffer": str(_strict_decimal(context["decision_cost_buffer"], "buf")),
        "realized_entry_cost": str(_strict_decimal(context["realized_entry_cost"], "rec")),
        "realized_fee_cost": str(_strict_decimal(context["realized_fee_cost"], "rfc")),
        "cost_components": cost_components, "entry_edge": str(entry_edge),
        "exit_depth_notional_avail": str(bid_notional),
        "exit_depth_required": str(exec_ask_vwap * fill.filled_qty),
        "fill_decision": fill_decision, "fill_reason": context.get("fill_reason"),
        "holdout_seed": hashlib.sha256(signal_id.encode()).hexdigest(),
        "edge_bucket": edge_b, "tte_bucket": tte_b,
        "row_hash": "", "prev_row_hash": "",
    }
    assert bind == "PASS"
    return NormalizedSignal(signal=sig, row=row, ask_fill=fill)


# =============================================================================
# 2. Mark normalizer
# =============================================================================
def normalize_mark(snapshot: dict, sig: "engine.Signal", seq: int) -> NormalizedMark:
    """One recorded bid-book snapshot -> G.5 Mark + mark_path row. Sentinel-safe."""
    ts_mark_ms = int(_require(snapshot, "ts_mark_ms"))
    quote_ts_ms = int(_require(snapshot, "quote_ts_ms"))
    bid_json = ladder_to_decimal_json(snapshot["bids"])
    held = D(sig.exec_fill_qty_avail)
    age = ts_mark_ms - quote_ts_ms
    levels = parse_bid_ladder(bid_json)

    if age > QUOTE_STALE_MS:
        status = ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE
        vwap = ExitMarkStatus.NOT_COMPUTED_STALE_QUOTE
        executable, liquidity, mark_depth, levels_used = 0, "STALE_QUOTE", Decimal("0"), 0
    elif not levels:
        status = ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY
        vwap = ExitMarkStatus.NOT_COMPUTED_BLOCKED_NO_LIQUIDITY
        executable, liquidity, mark_depth, levels_used = 0, "BLOCKED_NO_LIQUIDITY", Decimal("0"), 0
    else:
        filled, realized = engine.fak_walk_bids(levels, held)
        mark_depth = sum((p * s for p, s in levels), Decimal("0"))
        used, rem = 0, held
        for p, s in levels:
            if rem <= 0:
                break
            used += 1
            rem -= s
        levels_used = used
        if filled >= held:
            status, executable, liquidity = ExitMarkStatus.COMPUTED_EXECUTABLE, 1, "DEEP_EXECUTABLE"
            vwap = str(realized / held)
        else:
            status, executable, liquidity = ExitMarkStatus.COMPUTED_THIN_PARTIAL, 0, "THIN_FILL"
            vwap = str(realized / filled) if filled > 0 else "0"

    tte_s = sig.market_end_ts - (ts_mark_ms // 1000)
    mark = engine.Mark(
        signal_id=sig.signal_id, seq=seq, ts_mark_ms=ts_mark_ms, knowable_ts=ts_mark_ms,
        bid_ladder_json=bid_json, exit_mark_status=status, exit_mark_vwap=vwap,
        executable_flag=executable, liquidity_class=liquidity, tte_s=tte_s,
        elapsed_ms_since_signal=ts_mark_ms - sig.ts_signal_ms,
    )
    row = {
        "signal_id": sig.signal_id, "seq": seq, "ts_mark": _iso_from_ms(ts_mark_ms),
        "ts_mark_ms": ts_mark_ms, "knowable_ts": ts_mark_ms, "bid_ladder_json": bid_json,
        "exit_mark_status": status, "exit_mark_vwap": vwap, "mark_depth": str(mark_depth),
        "levels_used": levels_used, "executable_flag": executable,
        "liquidity_class": liquidity,
        "spot_price": str(_strict_decimal(snapshot["spot_price"], "spot")),
        "spot_age_ms": int(snapshot["spot_age_ms"]),
        "fair_yes_t": str(_strict_decimal(snapshot["fair_yes_t"], "fyt")),
        "fair_yes_sigma_t": str(_strict_decimal(snapshot["fair_yes_sigma_t"], "fyst")),
        "tte_s": tte_s, "row_hash": "", "prev_row_hash": "",
    }
    return NormalizedMark(mark=mark, row=row)


# =============================================================================
# 3. DB writer boundary (mock SQLite under /tmp; hash-chained append)
# =============================================================================
_SIGNAL_COLS = [
    "signal_id", "ts_signal", "ts_signal_ms", "knowable_ts", "asset", "side",
    "condition_id", "token_id", "outcome_index", "outcome_label", "slug",
    "market_end_ts", "underlying_spot_price", "reference_price",
    "reference_feed_ts", "reference_age_ms", "fair_yes", "fair_yes_sigma",
    "fair_model_version", "strike", "tte_s", "ask_ladder_json", "bid_ladder_json",
    "book_hash", "top_ask_price", "top_ask_size", "intended_stake",
    "book_ask_vwap", "book_bid_vwap", "exec_ask_vwap", "exec_fill_qty_avail",
    "decision_cost_buffer", "realized_entry_cost", "realized_fee_cost",
    "cost_components", "entry_edge", "exit_depth_notional_avail",
    "exit_depth_required", "fill_decision", "fill_reason", "holdout_seed",
    "edge_bucket", "tte_bucket", "row_hash", "prev_row_hash",
]
_MARK_COLS = [
    "signal_id", "seq", "ts_mark", "ts_mark_ms", "knowable_ts", "bid_ladder_json",
    "exit_mark_status", "exit_mark_vwap", "mark_depth", "levels_used",
    "executable_flag", "liquidity_class", "spot_price", "spot_age_ms",
    "fair_yes_t", "fair_yes_sigma_t", "tte_s", "row_hash", "prev_row_hash",
]


def init_mock_db(conn) -> None:
    engine.init_schema(conn)            # also runs assert_no_real_columns


def _chain_insert(conn, table: str, cols: list, row: dict, prev_hash: str) -> str:
    row = dict(row)
    row["prev_row_hash"] = prev_hash
    row["row_hash"] = engine.canonical_row_hash(
        {k: row[k] for k in cols}, exclude=("row_hash",))
    placeholders = ",".join("?" for _ in cols)
    conn.execute(
        f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
        [row[c] for c in cols])
    return row["row_hash"]


def write_signal(conn, norm: "NormalizedSignal", prev_hash: str = "GENESIS") -> str:
    return _chain_insert(conn, "signal_log", _SIGNAL_COLS, norm.row, prev_hash)


def write_mark(conn, norm: "NormalizedMark", prev_hash: str = "GENESIS") -> str:
    return _chain_insert(conn, "mark_path", _MARK_COLS, norm.row, prev_hash)
