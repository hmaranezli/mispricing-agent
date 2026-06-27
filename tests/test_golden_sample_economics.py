"""tests/test_golden_sample_economics.py — strict offline TDD for the diagnostic economics calculator.

compute_diagnostic_edge_report is a PURE, DETERMINISTIC function: it consumes a GOLDEN_SAMPLE_OK
record + explicit inert operator/config inputs and returns a diagnostic economic report. No I/O, no
clock, no float. Diagnostic math only — never trading/actionability.

First RED: module analysis.golden_sample_economics does not exist -> ImportError.
"""
import ast
import os
import sys
from decimal import Decimal, localcontext

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.golden_sample_economics import compute_diagnostic_edge_report, _normal_cdf

_COND = "0xCOND"
_YES = "YESTOK"
_NO = "NOTOK"
_END_MS = 1782604800000
_VAL_MS = _END_MS - 3_600_000          # one hour before expiry
_PREC = 40


def _book(asks, bids):
    return {"asks": [{"price": p, "size": s} for (p, s) in asks],
            "bids": [{"price": p, "size": s} for (p, s) in bids]}


_DEF_YES = _book([("0.50", "1000"), ("0.40", "1000")], [("0.38", "1000"), ("0.30", "1000")])
_DEF_NO = _book([("0.62", "1000"), ("0.60", "1000")], [("0.58", "1000"), ("0.50", "1000")])


def _record(*, status="GOLDEN_SAMPLE_OK", error_code=None, cond=_COND,
            yes_tok=_YES, no_tok=_NO, yes_expected=None, no_expected=None,
            yes_book=None, no_book=None, yes_evidence=True, no_evidence=True,
            strike="60175.95", reference="60328.5", end_ms=_END_MS):
    yb = _DEF_YES if yes_book is None else yes_book
    nb = _DEF_NO if no_book is None else no_book

    def slot(expected, book, present):
        ev = {"parsed_safe_book": book} if book is not None else None
        return {"expected_token_id": expected, "evidence": (ev if present else None)}

    return {
        "status": status,
        "error_code": error_code,
        "onboarding": {
            "condition_id": cond,
            "binance": {"strike_price": strike},
            "gamma": {"end_date_ms": end_ms, "event_start_time_ms": end_ms - 4 * 3_600_000,
                      "outcome_token_map": [{"outcome": "Up", "token_id": yes_tok},
                                            {"outcome": "Down", "token_id": no_tok}]},
        },
        "hl_reference": {"evidence": {"reference_price": reference,
                                      "reference_source": "hyperliquid_all_mids_perp"}},
        "yes_book": slot(yes_expected or yes_tok, yb, yes_evidence),
        "no_book": slot(no_expected or no_tok, nb, no_evidence),
    }


def _config(**over):
    c = {"fee_per_share": "0.01", "slippage_allowance": "0.005", "safety_margin": "0.005",
         "max_spread": "0.05", "sigma_annual": "0.5", "drift_annual": "0",
         "valuation_time_ms": _VAL_MS, "decimal_precision": _PREC,
         "expected_condition_id": _COND}
    c.update(over)
    return c


def _run(*, record=None, stake="100", config=None):
    return compute_diagnostic_edge_report(
        golden_sample_record=_record() if record is None else record,
        intended_stake_usd=stake,
        config=_config() if config is None else config)


def _fail(rep, reason):
    assert rep["status"] == "CALC_FAILED_CLOSED"
    assert rep["fail_closed_reason"] == reason
    assert rep["yes_leg"]["diagnostic_net_edge"] is None
    assert rep["no_leg"]["diagnostic_net_edge"] is None
    assert rep["model"]["model_fair_probability_up"] is None


# ===========================================================================
# happy path
# ===========================================================================

def test_happy_both_legs_diagnostic_ok():
    rep = _run()
    assert rep["status"] == "DIAGNOSTIC_OK"
    assert rep["fail_closed_reason"] is None
    assert rep["identity"] == {"condition_id": _COND, "yes_token_id": _YES, "no_token_id": _NO}
    assert rep["yes_leg"]["sufficient_depth"] is True
    assert rep["no_leg"]["sufficient_depth"] is True
    assert "not_actionable" in rep["markers"]
    assert "stake_adjusted_vwap_not_top_of_book" in rep["markers"]
    assert "perp_reference_not_spot_truth_settlement" in rep["markers"]
    assert "diagnostic_model_not_oracle" in rep["markers"]


def test_happy_edge_equation_internal_consistency():
    rep = _run()
    with localcontext() as ctx:
        ctx.prec = _PREC
        p_up = Decimal(rep["model"]["model_fair_probability_up"])
        fee = Decimal(rep["costs"]["fee_per_share"])
        slip = Decimal(rep["costs"]["slippage_allowance"])
        margin = Decimal(rep["costs"]["safety_margin"])
        vwap_yes = Decimal(rep["yes_leg"]["pm_stake_adjusted_vwap"])
        vwap_no = Decimal(rep["no_leg"]["pm_stake_adjusted_vwap"])
        exp_yes = p_up - vwap_yes - fee - slip - margin
        exp_no = (Decimal("1") - p_up) - vwap_no - fee - slip - margin
    assert Decimal(rep["yes_leg"]["diagnostic_net_edge"]) == exp_yes
    assert Decimal(rep["no_leg"]["diagnostic_net_edge"]) == exp_no


def test_all_numeric_output_leaves_are_strings():
    rep = _run()
    for leaf in (rep["yes_leg"]["pm_stake_adjusted_vwap"],
                 rep["yes_leg"]["diagnostic_net_edge"],
                 rep["yes_leg"]["best_bid"], rep["yes_leg"]["best_ask"], rep["yes_leg"]["spread"],
                 rep["model"]["model_fair_probability_up"], rep["model"]["time_to_expiry_years"],
                 rep["intended_stake_usd"], rep["costs"]["fee_per_share"]):
        assert isinstance(leaf, str)
        Decimal(leaf)  # parses


# ===========================================================================
# stake-adjusted VWAP: multi-level, partial last level, NOT top-of-book
# ===========================================================================

def test_multi_level_vwap_partial_last_and_not_top_of_book():
    # asks given OUT OF ORDER (0.50 first) to prove ascending sort; stake spans two levels
    yb = _book([("0.50", "100"), ("0.40", "100")], [("0.38", "1000")])
    nb = _book([("0.60", "100000")], [("0.58", "1000")])
    rep = _run(record=_record(yes_book=yb, no_book=nb), stake="60")
    with localcontext() as ctx:
        ctx.prec = _PREC
        expected_vwap = Decimal("60") / Decimal("140")   # 40@0.40 fully + 20usd@0.50 -> 40 shares
    vwap = Decimal(rep["yes_leg"]["pm_stake_adjusted_vwap"])
    assert vwap == expected_vwap
    assert vwap > Decimal("0.40")            # strictly worse than best ask => not top-of-book
    assert rep["yes_leg"]["best_ask"] == "0.40"


def test_insufficient_depth_fails_closed():
    yb = _book([("0.40", "10")], [("0.38", "1000")])     # notional 4 < stake 100
    rep = _run(record=_record(yes_book=yb))
    _fail(rep, "insufficient_depth")
    assert rep["yes_leg"]["sufficient_depth"] is False


# ===========================================================================
# book structural guards
# ===========================================================================

def test_empty_asks_fails_closed_before_spread():
    yb = _book([], [("0.38", "1000")])
    _fail(_run(record=_record(yes_book=yb)), "empty_book")


def test_empty_bids_fails_closed_before_spread():
    yb = _book([("0.40", "1000")], [])
    _fail(_run(record=_record(yes_book=yb)), "empty_book")


def test_crossed_or_locked_book():
    yb = _book([("0.40", "1000")], [("0.50", "1000")])   # best_bid 0.50 >= best_ask 0.40
    _fail(_run(record=_record(yes_book=yb)), "crossed_or_locked_book")


def test_spread_guard_exceeded():
    rep = _run(config=_config(max_spread="0.001"))       # default spread 0.02 > 0.001
    _fail(rep, "spread_guard_exceeded")


def test_book_evidence_missing():
    _fail(_run(record=_record(yes_evidence=False)), "book_evidence_missing")


def test_book_malformed_price_out_of_range():
    yb = _book([("1.50", "1000")], [("0.38", "1000")])
    _fail(_run(record=_record(yes_book=yb)), "book_malformed")


def test_book_malformed_missing_size_key():
    yb = {"asks": [{"price": "0.40"}], "bids": [{"price": "0.38", "size": "1000"}]}
    _fail(_run(record=_record(yes_book=yb)), "book_malformed")


# ===========================================================================
# status / identity gates (zero math)
# ===========================================================================

def test_golden_sample_not_ok_status():
    _fail(_run(record=_record(status="GOLDEN_SAMPLE_INVALID")), "golden_sample_not_ok")


def test_golden_sample_not_ok_error_code():
    _fail(_run(record=_record(error_code="timing_skew_violation")), "golden_sample_not_ok")


def test_identity_mismatch_token():
    _fail(_run(record=_record(yes_expected="WRONGTOK")), "identity_mismatch")


def test_identity_mismatch_condition_id():
    _fail(_run(config=_config(expected_condition_id="0xDEAD")), "identity_mismatch")


# ===========================================================================
# model input gates
# ===========================================================================

@pytest.mark.parametrize("missing", ["sigma_annual", "drift_annual", "valuation_time_ms"])
def test_missing_model_inputs(missing):
    c = _config()
    del c[missing]
    _fail(_run(config=c), "missing_model_inputs")


def test_sigma_nonpositive_invalid_config():
    _fail(_run(config=_config(sigma_annual="0")), "invalid_config")


def test_expired_or_nonpositive_tte():
    _fail(_run(config=_config(valuation_time_ms=_END_MS)), "expired_or_nonpositive_tte")


def test_nonpositive_reference():
    _fail(_run(record=_record(reference="0")), "nonpositive_reference_or_strike")


def test_nonpositive_strike():
    _fail(_run(record=_record(strike="0")), "nonpositive_reference_or_strike")


# ===========================================================================
# unsafe numeric / stake / config
# ===========================================================================

def test_unsafe_float_in_book():
    yb = {"asks": [{"price": 0.40, "size": "1000"}], "bids": [{"price": "0.38", "size": "1000"}]}
    _fail(_run(record=_record(yes_book=yb)), "unsafe_numeric")


def test_unsafe_bool_in_book():
    yb = {"asks": [{"price": True, "size": "1000"}], "bids": [{"price": "0.38", "size": "1000"}]}
    _fail(_run(record=_record(yes_book=yb)), "unsafe_numeric")


def test_unsafe_nan_string_in_config():
    _fail(_run(config=_config(fee_per_share="NaN")), "unsafe_numeric")


def test_unsafe_inf_string_stake():
    _fail(_run(stake="Infinity"), "unsafe_numeric")


@pytest.mark.parametrize("bad", ["0", "-5"])
def test_invalid_stake(bad):
    _fail(_run(stake=bad), "invalid_stake")


def test_invalid_stake_unparseable():
    _fail(_run(stake="abc"), "invalid_stake")


def test_invalid_config_negative_fee():
    _fail(_run(config=_config(fee_per_share="-0.01")), "invalid_config")


def test_invalid_config_missing_fee_key():
    c = _config()
    del c["fee_per_share"]
    _fail(_run(config=c), "invalid_config")


def test_invalid_config_bad_precision():
    _fail(_run(config=_config(decimal_precision=0)), "invalid_config")


# ===========================================================================
# programmer-contract violations raise (not fail-closed carriers)
# ===========================================================================

def test_record_not_dict_raises():
    with pytest.raises(TypeError):
        compute_diagnostic_edge_report(golden_sample_record=["x"], intended_stake_usd="100",
                                       config=_config())


def test_config_not_mapping_raises():
    with pytest.raises(TypeError):
        compute_diagnostic_edge_report(golden_sample_record=_record(), intended_stake_usd="100",
                                       config=["not", "mapping"])


# ===========================================================================
# deterministic Decimal normal CDF
# ===========================================================================

def test_normal_cdf_known_points_and_bounds():
    with localcontext() as ctx:
        ctx.prec = _PREC
        mid = _normal_cdf(Decimal("0"))
        hi = _normal_cdf(Decimal("1"))
        lo = _normal_cdf(Decimal("-1"))
        assert abs(mid - Decimal("0.5")) < Decimal("0.000001")
        assert lo < mid < hi                       # monotonic
        assert Decimal("0") <= lo and hi <= Decimal("1")
        # symmetry within tolerance
        assert abs(_normal_cdf(Decimal("-1")) - (Decimal("1") - _normal_cdf(Decimal("1")))) \
            < Decimal("0.000001")
        # a known value: Phi(1) ~ 0.8413
        assert abs(hi - Decimal("0.8413")) < Decimal("0.001")


# ===========================================================================
# determinism / purity
# ===========================================================================

def test_determinism_byte_identical():
    assert _run() == _run()


def test_no_forbidden_imports_or_vocabulary():
    import analysis.golden_sample_economics as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        src = fh.read()
    low = src.lower()
    forbidden_imports = ("aiohttp", "requests", "sqlite", "pathlib", "subprocess",
                         "socket", "urllib", "httpx", "import os", "from os",
                         "import time", "datetime", "import math", "from math")
    for term in forbidden_imports:
        assert term not in low, f"forbidden import surface {term!r}"
    banned_vocab = ("buy", "sell", "trade", "execut", "order", "route",
                    "paper", "canary", "live", "wallet", "capital", "scanner", "runner")
    for term in banned_vocab:
        assert term not in low, f"banned actionability token {term!r}"


def test_decimal_only_no_float_literals_or_calls():
    import analysis.golden_sample_economics as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        src = fh.read()
    assert "float(" not in src
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            raise AssertionError(f"float literal {node.value!r} at line {node.lineno}")
