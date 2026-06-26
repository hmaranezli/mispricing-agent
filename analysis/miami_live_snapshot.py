"""analysis/miami_live_snapshot.py — Miami v3 Sub-slice A: pure snapshot assembler.

Takes INJECTED offline raw inputs (a fake Polymarket CLOB YES book, a fake CLOB NO book, a fake
reference tick) plus operator-supplied market facts, validates them, and returns ONLY the calculator
INPUT kwargs that ``expiry_snipe_calculator.compute_decision_row`` expects. It does NOT build the
48-key decision row, computes no edge or cost terms, performs no pin/spread/fee/slippage math, writes
no CSV, and makes no network call. Reference price is observation only.

Resolved policy:
  * Hyperliquid is accepted as ``spot_reference`` (settlement-oracle basis risk is recorded as a
    note marker, never silently ignored).
  * Degraded timestamp mode: if the reference tick carries a trusted venue event timestamp, staleness
    is computed from it; otherwise client capture timing is used and a ``degraded_ts_override`` marker
    is recorded. Client time is never relabelled as a venue timestamp.
  * Volatility is not fetched: a per-asset annual default is used unless the operator overrides it;
    an unknown asset with no override is a hard error.
  * Token->outcome mapping, strike, and expiry are cross-checked against injected venue metadata;
    any mismatch is a hard fail-closed error.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

SECONDS_PER_YEAR = 365 * 24 * 3600

DEFAULT_ANNUAL_VOLATILITY = {"BTC": 0.40, "ETH": 0.50}

_YES_OUTCOMES = {"up", "yes"}
_NO_OUTCOMES = {"down", "no"}

# Exact calculator INPUT key set this assembler returns (NOT the 48-key decision row).
CALCULATOR_INPUT_KEYS = (
    "timestamp", "asset", "timeframe", "market_slug_or_label", "expiry",
    "time_to_expiry_seconds", "strike", "spot_reference", "reference_source",
    "reference_staleness_ms", "yes_bid", "yes_ask", "no_bid", "no_ask",
    "yes_available_size", "no_available_size", "intended_stake_usd",
    "volatility_sigma", "tie_resolves_to",
)


@dataclass(frozen=True)
class AssembledSnapshot:
    kwargs: dict          # exactly CALCULATOR_INPUT_KEYS
    notes_markers: list   # provenance markers (basis risk, degraded timestamp, ...)


def _parse_utc_z(value, field):
    """Parse a strict UTC ISO-8601 'Z' timestamp -> aware UTC datetime. Reject ET/local/offset."""
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field} must be a UTC ISO-8601 timestamp ending in 'Z': {value!r}")
    body = value[:-1]
    try:
        dt = datetime.fromisoformat(body)
    except ValueError:
        raise ValueError(f"{field} is not a valid timestamp: {value!r}")
    if dt.tzinfo is not None:
        raise ValueError(f"{field} must use 'Z', not an explicit offset: {value!r}")
    return dt.replace(tzinfo=timezone.utc)


def _epoch(dt):
    return dt.timestamp()


def _best_levels(book, side):
    """Return (best_bid, best_ask, best_ask_size). Fail-closed on missing side/crossed/invalid."""
    if not isinstance(book, dict):
        raise ValueError(f"missing_{side}_side: book is not a dict")
    bids = book.get("bids") or []
    asks = book.get("asks") or []
    if not bids or not asks:
        raise ValueError(f"missing_{side}_side: empty bids or asks")

    def _lvl(entry):
        return float(entry["price"]), float(entry["size"])

    bid_levels = [_lvl(b) for b in bids]
    ask_levels = [_lvl(a) for a in asks]
    bb_price, bb_size = max(bid_levels, key=lambda t: t[0])
    ba_price, ba_size = min(ask_levels, key=lambda t: t[0])

    for label, v in (("bid_price", bb_price), ("bid_size", bb_size),
                     ("ask_price", ba_price), ("ask_size", ba_size)):
        if v <= 0:
            raise ValueError(f"{side}_{label} must be > 0, got {v}")
    if bb_price >= ba_price:
        raise ValueError(f"{side} book crossed/locked: bid {bb_price} >= ask {ba_price}")
    return bb_price, ba_price, ba_size


def _crosscheck_metadata(*, market_metadata, yes_token_id, no_token_id, strike, expiry_dt):
    if not isinstance(market_metadata, dict):
        raise ValueError("market_metadata must be a dict")
    tokens = market_metadata.get("tokens") or []
    by_token = {}
    for t in tokens:
        by_token[t.get("token_id")] = str(t.get("outcome", "")).lower()
    yes_outcome = by_token.get(yes_token_id)
    no_outcome = by_token.get(no_token_id)
    if yes_outcome not in _YES_OUTCOMES:
        raise ValueError(f"token/outcome mismatch: yes_token_id maps to {yes_outcome!r}")
    if no_outcome not in _NO_OUTCOMES:
        raise ValueError(f"token/outcome mismatch: no_token_id maps to {no_outcome!r}")

    md_strike = market_metadata.get("strike")
    if md_strike is None or abs(float(md_strike) - float(strike)) > 1e-6:
        raise ValueError(f"strike mismatch: operator {strike} vs metadata {md_strike}")

    md_expiry = market_metadata.get("expiry")
    md_expiry_dt = _parse_utc_z(md_expiry, "market_metadata.expiry")
    if _epoch(md_expiry_dt) != _epoch(expiry_dt):
        raise ValueError(f"expiry metadata mismatch: operator {expiry_dt} vs metadata {md_expiry_dt}")


def _staleness_ms(reference_tick, captured_dt):
    """Return (reference_staleness_ms, degraded: bool)."""
    src_ts = reference_tick.get("source_event_ts")
    if src_ts:
        src_dt = _parse_utc_z(src_ts, "reference_tick.source_event_ts")
        return int(round((_epoch(captured_dt) - _epoch(src_dt)) * 1000)), False
    client_ts = reference_tick.get("client_fetched_at")
    if client_ts:
        client_dt = _parse_utc_z(client_ts, "reference_tick.client_fetched_at")
        return int(round((_epoch(captured_dt) - _epoch(client_dt)) * 1000)), True
    return 0, True


def assemble_snapshot_inputs(*, asset, timeframe, market_slug_or_label, yes_token_id, no_token_id,
                             strike, expiry, intended_stake_usd, tie_resolves_to, captured_at,
                             reference_source, yes_book, no_book, reference_tick, market_metadata,
                             volatility_annual=None) -> AssembledSnapshot:
    """Validate injected raw inputs and return calculator INPUT kwargs (+ provenance markers)."""
    captured_dt = _parse_utc_z(captured_at, "captured_at")
    expiry_dt = _parse_utc_z(expiry, "expiry")

    time_to_expiry_seconds = int(round(_epoch(expiry_dt) - _epoch(captured_dt)))
    if time_to_expiry_seconds <= 0:
        raise ValueError(f"time_to_expiry_seconds must be > 0, got {time_to_expiry_seconds}")

    _crosscheck_metadata(market_metadata=market_metadata, yes_token_id=yes_token_id,
                         no_token_id=no_token_id, strike=strike, expiry_dt=expiry_dt)

    yes_bid, yes_ask, yes_avail = _best_levels(yes_book, "yes")
    no_bid, no_ask, no_avail = _best_levels(no_book, "no")

    spot_reference = float(reference_tick["price"])
    if spot_reference <= 0:
        raise ValueError(f"reference price must be > 0, got {spot_reference}")

    reference_staleness_ms, degraded = _staleness_ms(reference_tick, captured_dt)

    annual = volatility_annual if volatility_annual is not None else DEFAULT_ANNUAL_VOLATILITY.get(asset)
    if annual is None:
        raise ValueError(f"no volatility default for asset {asset!r} and no override supplied")
    volatility_sigma = float(annual) / math.sqrt(SECONDS_PER_YEAR)

    markers = []
    if str(reference_source).lower().startswith("hyperliquid"):
        markers.append("basis_risk_accepted_hyperliquid_vs_settlement_oracle")
    if degraded:
        markers.append("degraded_ts_override")

    kwargs = {
        "timestamp": captured_at, "asset": asset, "timeframe": timeframe,
        "market_slug_or_label": market_slug_or_label, "expiry": expiry,
        "time_to_expiry_seconds": time_to_expiry_seconds, "strike": float(strike),
        "spot_reference": spot_reference, "reference_source": reference_source,
        "reference_staleness_ms": reference_staleness_ms,
        "yes_bid": yes_bid, "yes_ask": yes_ask, "no_bid": no_bid, "no_ask": no_ask,
        "yes_available_size": yes_avail, "no_available_size": no_avail,
        "intended_stake_usd": float(intended_stake_usd),
        "volatility_sigma": volatility_sigma, "tie_resolves_to": tie_resolves_to,
    }
    return AssembledSnapshot(kwargs=kwargs, notes_markers=markers)
