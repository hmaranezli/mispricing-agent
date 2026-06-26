"""analysis/decision_log_csv.py — thin, append-only Decision Log CSV writer (stdlib csv only).

Appends exactly one calculator decision-row dict to a local CSV. Pure file I/O: stdlib only, no
external dataframe library, no scanner/loop/scheduler, no historical analysis beyond the header line.

CANONICAL_SCHEMA is the single source of column order for this writer. A drift-guard test pins it
to ``compute_decision_row`` output so the two cannot silently diverge.

Concurrency: a minimal advisory ``fcntl.flock`` exclusive lock guards the append on Linux
(single-host, advisory only). Cross-host locking / lockfiles / retries are deliberately deferred.
"""
from __future__ import annotations

import csv
import os

try:
    import fcntl  # Linux advisory file lock; optional
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - non-Linux fallback
    _HAVE_FCNTL = False

# Canonical column order — mirrors expiry_snipe_calculator.compute_decision_row construction order.
CANONICAL_SCHEMA = (
    # identity / snapshot
    "timestamp", "asset", "timeframe", "market_slug_or_label", "expiry",
    "time_to_expiry_seconds", "strike", "spot_reference", "reference_source",
    "reference_staleness_ms",
    # raw book
    "yes_bid", "yes_ask", "no_bid", "no_ask",
    # tie / pin
    "tie_resolves_to", "tie_rule_applied", "distance_to_strike", "distance_to_strike_bps",
    "noise_band_bps", "is_pin_risk", "pin_risk_reason",
    # yes side
    "yes_fair_probability", "yes_implied_probability", "yes_market_edge", "yes_spread_cost",
    "yes_slippage_buffer", "yes_latency_buffer", "yes_fee_cost", "yes_adjusted_edge",
    # no side
    "no_fair_probability", "no_implied_probability", "no_market_edge", "no_spread_cost",
    "no_slippage_buffer", "no_latency_buffer", "no_fee_cost", "no_adjusted_edge",
    # decision
    "selected_side_candidate", "candidate_threshold", "candidate", "intended_stake_usd",
    "liquidity_status",
    # doctrine
    "expected_hold_seconds", "is_in_doctrine_window", "snipe_window_label",
    # governance
    "operator_decision_required", "trade_allowed", "notes",
)

_SCHEMA_SET = frozenset(CANONICAL_SCHEMA)


def _format_cell(value) -> str:
    """Stable, locale-independent cell rendering. None -> empty cell; bool/float -> str()."""
    if value is None:
        return ""
    return str(value)


def _validate_keys(decision_row_dict: dict) -> None:
    keys = set(decision_row_dict.keys())
    missing = _SCHEMA_SET - keys
    extra = keys - _SCHEMA_SET
    if missing:
        raise ValueError(f"missing keys: {sorted(missing)}")
    if extra:
        raise ValueError(f"unexpected keys: {sorted(extra)}")


def append_decision_row(decision_row_dict: dict, filepath, *, create_parents: bool = False) -> None:
    """Append one decision row to ``filepath`` as CSV. Append-only; header written once.

    Validates exact schema (missing/extra keys -> ValueError). On an existing non-empty file,
    verifies the header matches CANONICAL_SCHEMA exactly (mismatch -> ValueError, no append).
    """
    _validate_keys(decision_row_dict)

    path = os.fspath(filepath)
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        if create_parents:
            os.makedirs(parent, exist_ok=True)
        else:
            raise FileNotFoundError(
                f"parent dir {parent!r} missing; pass create_parents=True to create it")

    file_has_content = os.path.exists(path) and os.path.getsize(path) > 0

    if file_has_content:
        with open(path, "r", newline="", encoding="utf-8") as f:
            existing_header = next(csv.reader(f), [])
        if existing_header != list(CANONICAL_SCHEMA):
            raise ValueError("header mismatch: existing CSV header does not match canonical schema")

    row_cells = [_format_cell(decision_row_dict[col]) for col in CANONICAL_SCHEMA]

    with open(path, "a", newline="", encoding="utf-8") as f:
        if _HAVE_FCNTL:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            writer = csv.writer(f)
            if not file_has_content:
                writer.writerow(list(CANONICAL_SCHEMA))
            writer.writerow(row_cells)
            f.flush()
        finally:
            if _HAVE_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
