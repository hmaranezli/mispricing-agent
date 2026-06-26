"""analysis/market_support_classifier.py — pure venue-support classification.

A single deterministic function decides whether one Polymarket crypto Up/Down market is fit for
the automated candidate path, given:
  - Gamma metadata (condition_id, yes/no token ids, outcomes, event_start_time_ms, end_date_ms, asset)
  - a Binance candle-open strike-verification result (status, strike, open_time_ms)
  - asset allowlist + reference-source support
  - an EXPLICIT now_ms (caller-supplied; this module reads no clock)

It computes only a classification string. It performs no input/output, no live calls, and never
guesses, infers, or approximates a strike. Every uncertain or malformed condition fails closed.

This is strictly a data-validation / cache-readiness gate: it does not generate signals and does
not generate trading candidates.

Classifications:
  CACHE_READY           - all gates pass; venue metadata + strike are verified and cache-ready
  OBSERVE_ONLY          - window not open yet, or already past expiry
  MANUAL_ONE_SHOT_ONLY  - strike/metadata not venue-verified; operator-asserted path remains
  UNSUPPORTED_ASSET     - asset off the allowlist, or no supported reference source
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

CACHE_READY = "CACHE_READY"
OBSERVE_ONLY = "OBSERVE_ONLY"
MANUAL_ONE_SHOT_ONLY = "MANUAL_ONE_SHOT_ONLY"
UNSUPPORTED_ASSET = "UNSUPPORTED_ASSET"

_STRIKE_VENUE_VERIFIED = "VENUE_VERIFIED"


def _strike_is_venue_verified(strike_result, event_start_time_ms) -> bool:
    if not isinstance(strike_result, dict):
        return False
    if strike_result.get("status") != _STRIKE_VENUE_VERIFIED:
        return False
    open_time = strike_result.get("open_time_ms")
    if not isinstance(open_time, int) or open_time != event_start_time_ms:
        return False
    raw = strike_result.get("strike")
    if raw is None or isinstance(raw, bool):
        return False
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return False
    return value > 0


def _gamma_is_structurally_valid(gamma_meta) -> bool:
    if not isinstance(gamma_meta, dict):
        return False
    for key in ("condition_id", "yes_token_id", "no_token_id"):
        value = gamma_meta.get(key)
        if not isinstance(value, str) or not value:
            return False
    outcomes = gamma_meta.get("outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != 2:
        return False
    for label in outcomes:
        if not isinstance(label, str) or not label:
            return False
    for key in ("event_start_time_ms", "end_date_ms"):
        if not isinstance(gamma_meta.get(key), int) or isinstance(gamma_meta.get(key), bool):
            return False
    return True


def classify_market_support(*, gamma_meta, strike_result, support, now_ms) -> str:
    """Return one classification string. Pure, deterministic, fail-closed. now_ms is explicit."""
    if not isinstance(now_ms, int) or isinstance(now_ms, bool):
        raise TypeError("now_ms must be an int (explicit caller-supplied epoch ms; no internal clock)")

    # 1. asset gate (broadest): off-allowlist or no reference source -> unsupported asset
    asset = gamma_meta.get("asset") if isinstance(gamma_meta, dict) else None
    allowlist = support.get("asset_allowlist") if isinstance(support, dict) else None
    if not isinstance(allowlist, (list, tuple, set)) or asset not in allowlist:
        return UNSUPPORTED_ASSET
    if not support.get("reference_source_supported"):
        return UNSUPPORTED_ASSET

    # 2. structural validity of venue metadata (needed before any time reasoning)
    if not _gamma_is_structurally_valid(gamma_meta):
        return MANUAL_ONE_SHOT_ONLY

    # 3. expiry gate: at/after close there is nothing to act on
    if now_ms >= gamma_meta["end_date_ms"]:
        return OBSERVE_ONLY

    # 4. future strike paradox: before window open the candle (hence strike) does not exist
    if now_ms < gamma_meta["event_start_time_ms"]:
        return OBSERVE_ONLY

    # 5. strike must be venue-verified at the exact window open; else operator-asserted fallback only
    if not _strike_is_venue_verified(strike_result, gamma_meta["event_start_time_ms"]):
        return MANUAL_ONE_SHOT_ONLY

    # 6. all gates pass
    return CACHE_READY
