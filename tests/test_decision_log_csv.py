"""tests/test_decision_log_csv.py — TDD for the thin Decision Log CSV writer.

append_decision_row appends exactly one calculator row to a local CSV using stdlib csv only.
Append-only, canonical column order, exact-schema validation, header written once. No pandas,
no network, no DB, no historical analysis beyond reading the header line.

First RED: module analysis.decision_log_csv does not exist -> ImportError.
"""
import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.decision_log_csv import CANONICAL_SCHEMA, append_decision_row
from analysis.expiry_snipe_calculator import compute_decision_row


def _row(**over):
    """A dict carrying exactly the canonical schema keys with simple typed values."""
    base = {
        "timestamp": "2026-06-26T05:00:00Z", "asset": "BTC", "timeframe": "5m",
        "market_slug_or_label": "btc-updown-5m-1", "expiry": "2026-06-26T05:02:00Z",
        "time_to_expiry_seconds": 120, "strike": 100000.0, "spot_reference": 100100.0,
        "reference_source": "hyperliquid", "reference_staleness_ms": 50,
        "yes_bid": 0.55, "yes_ask": 0.57, "no_bid": 0.43, "no_ask": 0.45,
        "tie_resolves_to": "UP", "tie_rule_applied": False, "distance_to_strike": 100.0,
        "distance_to_strike_bps": 10.0, "noise_band_bps": 54.7, "is_pin_risk": False,
        "pin_risk_reason": None,
        "yes_fair_probability": 0.57, "yes_implied_probability": 0.56, "yes_market_edge": 0.01,
        "yes_spread_cost": 0.01, "yes_slippage_buffer": 0.0, "yes_latency_buffer": 0.0,
        "yes_fee_cost": 0.0, "yes_adjusted_edge": 0.0,
        "no_fair_probability": 0.43, "no_implied_probability": 0.44, "no_market_edge": -0.01,
        "no_spread_cost": 0.01, "no_slippage_buffer": 0.0, "no_latency_buffer": 0.0,
        "no_fee_cost": 0.0, "no_adjusted_edge": -0.02,
        "selected_side_candidate": "none", "candidate_threshold": 0.03, "candidate": False,
        "intended_stake_usd": 30.0, "liquidity_status": "enough_for_stake",
        "expected_hold_seconds": 120, "is_in_doctrine_window": False,
        "snipe_window_label": "5m_snipe",
        "operator_decision_required": True, "trade_allowed": False, "notes": "x",
    }
    base.update(over)
    return base


def _read(path):
    with open(path, newline="") as f:
        return list(csv.reader(f))


# ---------------------------------------------------------------------------

def test_new_file_writes_canonical_header_then_row(tmp_path):
    p = tmp_path / "log.csv"
    append_decision_row(_row(), str(p))
    rows = _read(str(p))
    assert rows[0] == list(CANONICAL_SCHEMA)          # header in canonical order
    assert len(rows) == 2                              # header + 1 data row


def test_append_second_row_keeps_single_header(tmp_path):
    p = tmp_path / "log.csv"
    append_decision_row(_row(asset="BTC"), str(p))
    append_decision_row(_row(asset="ETH"), str(p))
    rows = _read(str(p))
    assert rows[0] == list(CANONICAL_SCHEMA)
    assert len(rows) == 3                              # header + 2 data
    asset_idx = CANONICAL_SCHEMA.index("asset")
    assert [rows[1][asset_idx], rows[2][asset_idx]] == ["BTC", "ETH"]


def test_missing_key_raises_value_error(tmp_path):
    p = tmp_path / "log.csv"
    bad = _row()
    del bad["asset"]
    with pytest.raises(ValueError):
        append_decision_row(bad, str(p))
    assert not p.exists()                              # nothing written on validation failure


def test_extra_key_raises_value_error(tmp_path):
    p = tmp_path / "log.csv"
    bad = _row()
    bad["surprise"] = 1
    with pytest.raises(ValueError):
        append_decision_row(bad, str(p))
    assert not p.exists()


def test_existing_header_mismatch_raises_and_does_not_append(tmp_path):
    p = tmp_path / "log.csv"
    # write a file with a wrong header
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wrong", "header"])
        w.writerow(["a", "b"])
    with pytest.raises(ValueError):
        append_decision_row(_row(), str(p))
    rows = _read(str(p))
    assert rows == [["wrong", "header"], ["a", "b"]]   # untouched


def test_missing_parent_dir_without_create_parents_fails_clearly(tmp_path):
    p = tmp_path / "nested" / "deep" / "log.csv"
    with pytest.raises(FileNotFoundError):
        append_decision_row(_row(), str(p))
    assert not p.exists()
    assert not (tmp_path / "nested").exists()          # no dirs created


def test_create_parents_true_makes_dirs_and_writes(tmp_path):
    p = tmp_path / "nested" / "deep" / "log.csv"
    append_decision_row(_row(), str(p), create_parents=True)
    assert p.exists()
    rows = _read(str(p))
    assert rows[0] == list(CANONICAL_SCHEMA) and len(rows) == 2


def test_dict_input_order_does_not_affect_column_order(tmp_path):
    p = tmp_path / "log.csv"
    shuffled = dict(reversed(list(_row(asset="XRP").items())))   # reversed insertion order
    append_decision_row(shuffled, str(p))
    with open(p, newline="") as f:
        rec = next(csv.DictReader(f))
    assert rec["asset"] == "XRP"
    # header order is canonical regardless of input dict order
    assert _read(str(p))[0] == list(CANONICAL_SCHEMA)


def test_bool_none_float_formatting_stable(tmp_path):
    p = tmp_path / "log.csv"
    append_decision_row(_row(trade_allowed=False, operator_decision_required=True,
                             pin_risk_reason=None, yes_fair_probability=0.5), str(p))
    with open(p, newline="") as f:
        rec = next(csv.DictReader(f))
    assert rec["trade_allowed"] == "False"
    assert rec["operator_decision_required"] == "True"
    assert rec["pin_risk_reason"] == ""                # None -> empty cell
    assert rec["yes_fair_probability"] == "0.5"


def test_append_only_prefix_preserved(tmp_path):
    p = tmp_path / "log.csv"
    append_decision_row(_row(asset="BTC"), str(p))
    first = open(p, "rb").read()
    append_decision_row(_row(asset="ETH"), str(p))
    second = open(p, "rb").read()
    assert second[:len(first)] == first                # earlier bytes are a strict prefix


def test_drift_guard_matches_calculator_keys(tmp_path):
    inputs = {
        "timestamp": "t", "asset": "BTC", "timeframe": "5m", "market_slug_or_label": "s",
        "expiry": "e", "time_to_expiry_seconds": 120, "strike": 100000.0,
        "spot_reference": 100100.0, "reference_source": "hyperliquid",
        "reference_staleness_ms": 50, "yes_bid": 0.55, "yes_ask": 0.57, "no_bid": 0.43,
        "no_ask": 0.45, "yes_available_size": 1000.0, "no_available_size": 1000.0,
        "intended_stake_usd": 30.0, "volatility_sigma": 0.0005, "tie_resolves_to": "UP",
    }
    produced = compute_decision_row(inputs, {})
    assert set(CANONICAL_SCHEMA) == set(produced.keys())
    # and a real calculator row appends cleanly end-to-end
    p = tmp_path / "log.csv"
    append_decision_row(produced, str(p))
    assert _read(str(p))[0] == list(CANONICAL_SCHEMA)


def test_source_scan_no_forbidden_surfaces():
    import analysis.decision_log_csv as m
    src = open(m.__file__, "r", encoding="utf-8").read()
    low = src.lower()
    for banned in ("pandas", "aiohttp", "requests", "socket", "websocket",
                   "sqlite", "place_order", "submit_order", "wallet", "signing"):
        assert banned not in low, f"forbidden term {banned!r} present"
    import_lines = "\n".join(ln for ln in src.splitlines()
                             if ln.strip().startswith(("import ", "from "))).lower()
    for forbidden in ("pandas", "aiohttp", "requests", "execution", "council",
                      "scout", "db.", "sqlite"):
        assert forbidden not in import_lines, f"must not import {forbidden!r}"
