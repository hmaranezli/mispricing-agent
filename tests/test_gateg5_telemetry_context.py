"""
Gate G.5 — HL-basis model context tests (pure model + mocked-HL integration).

  * NO network: HL fetches are monkeypatched. NO live DB, NO S1, NO wallet/capital.
  * Verifies real entry_edge/fair_yes/reference_age wiring and observation-only fill
    decisions, with stale/sentinel behavior unchanged.

Run with:  pytest -q tests/test_gateg5_telemetry_context.py
"""

import importlib.util
from decimal import Decimal

import pytest

from analysis.forensic import gateg5_model as gm
from analysis.forensic import gateg5_plumbing as plumb

engine = plumb.engine
FillDecision = engine.FillDecision

# load the runner module (tools/ is not a package) for _model_context + HL hooks
_SPEC = importlib.util.spec_from_file_location(
    "gateg5_telemetry_runner", "/root/mispricing_agent/tools/gateg5_telemetry_runner.py")
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)

NOW_MS = 1_000_000_000_000
NOW_S = NOW_MS // 1000


# ---------------------------------------------------------------------------
# pure model
# ---------------------------------------------------------------------------
def test_fair_yes_at_the_money_below_half():
    # reference == strike, no drift -> d2 = -(sigma^2/2)*tte / (sigma*sqrt(tte)) < 0 -> p<0.5
    fy = gm.fair_yes_gbm(Decimal("100"), Decimal("100"), Decimal("0.8"), Decimal("0.1"))
    assert isinstance(fy, Decimal)
    assert Decimal("0") < fy < Decimal("0.5")


def test_fair_yes_monotonic_in_reference():
    lo = gm.fair_yes_gbm(Decimal("95"), Decimal("100"), Decimal("0.8"), Decimal("0.1"))
    atm = gm.fair_yes_gbm(Decimal("100"), Decimal("100"), Decimal("0.8"), Decimal("0.1"))
    hi = gm.fair_yes_gbm(Decimal("105"), Decimal("100"), Decimal("0.8"), Decimal("0.1"))
    assert lo < atm < hi


@pytest.mark.parametrize("kw", [
    {"reference": "0"}, {"strike": "0"}, {"sigma_annual": "0"}, {"tte_years": "0"},
    {"reference": "NaN"}, {"sigma_annual": "Infinity"},
])
def test_model_input_errors(kw):
    base = dict(reference="100", strike="100", sigma_annual="0.8", tte_years="0.1")
    base.update(kw)
    with pytest.raises(gm.ModelInputError):
        gm.fair_yes_gbm(base["reference"], base["strike"],
                        base["sigma_annual"], base["tte_years"])


def test_no_side_entry_edge():
    assert gm.no_side_entry_edge(Decimal("0.3"), Decimal("0.5")) == Decimal("0.2")
    # zero-cost convention: edge == (1-fy) - vwap
    assert gm.no_side_entry_edge("0.7", "0.10") == Decimal("0.2")


# ---------------------------------------------------------------------------
# mocked-HL integration through _model_context + plumbing.normalize_signal
# ---------------------------------------------------------------------------
def _market(**over):
    base = dict(
        asset="BTC", side="NO", condition_id="cond-1", token_id="tokDown",
        outcome_index=1, outcome_label="Down", slug="btc-updown-15m-1000000000",
        market_end_ts=NOW_S + 600, clobTokenIds=["tokUp", "tokDown"],
        outcomes=["Up", "Down"],
    )
    base.update(over)
    return base


def _book(asks, quote_ts_ms=NOW_MS - 100):
    return {"asks": asks, "bids": [["0.05", "1000"]], "quote_ts_ms": quote_ts_ms}


def _patch_hl(monkeypatch, p_now, strike, sigma=0.8):
    def fake_pf(coin, ts_ms):
        if ts_ms == NOW_MS:                       # 'now' reference
            return Decimal(str(p_now)), NOW_MS - 30_000
        return Decimal(str(strike)), ts_ms        # window-open strike
    monkeypatch.setattr(runner, "_hl_price_feedts", fake_pf)
    monkeypatch.setattr(runner, "_hl_sigma_annual", lambda coin, now_ms: sigma)


def test_model_context_fields_and_reference_age(monkeypatch):
    _patch_hl(monkeypatch, p_now="60000", strike="60000")
    ctx = runner._model_context("BTC", _market(), _book([["0.40", "1000"]]), NOW_MS)
    assert ctx["reference_feed_ts"] == NOW_MS - 30_000        # real HL ts, not now
    assert ctx["reference_price"] == "60000"
    assert ctx["strike"] == "60000"
    assert "HL_DIAGNOSTIC_BASIS" in ctx["fair_model_version"]
    assert ctx["realized_entry_cost"] == "0" and ctx["realized_fee_cost"] == "0"  # zero-cost
    ns = plumb.normalize_signal(_market(), _book([["0.40", "1000"]]), ctx, capture_ts_ms=NOW_MS)
    assert ns.signal.reference_age_ms == 30_000               # nonzero, from injected feed ts


def test_high_no_edge_yields_filled_active(monkeypatch):
    # p_now well BELOW strike -> P(up)~0 -> P(no/down)~1; cheap NO ask -> big edge
    _patch_hl(monkeypatch, p_now="59000", strike="60000")
    book = _book([["0.10", "1000"]])
    ctx = runner._model_context("BTC", _market(), book, NOW_MS)
    assert Decimal(ctx["entry_edge"]) >= Decimal("0.15")
    ns = plumb.normalize_signal(_market(), book, ctx, capture_ts_ms=NOW_MS)
    assert ns.signal.fill_decision == FillDecision.FILLED_ACTIVE


def test_low_no_edge_stays_unfilled_edge_lost(monkeypatch):
    # p_now well ABOVE strike -> P(up)~1 -> P(no)~0 -> negative NO edge
    _patch_hl(monkeypatch, p_now="61000", strike="60000")
    book = _book([["0.40", "1000"]])
    ctx = runner._model_context("BTC", _market(), book, NOW_MS)
    assert Decimal(ctx["entry_edge"]) < Decimal("0.15")
    ns = plumb.normalize_signal(_market(), book, ctx, capture_ts_ms=NOW_MS)
    assert ns.signal.fill_decision == FillDecision.UNFILLED_EDGE_LOST


def test_stale_quote_unchanged(monkeypatch):
    # even with a strong edge, a stale book quote -> UNFILLED_QUOTE_STALE (precedence preserved)
    _patch_hl(monkeypatch, p_now="59000", strike="60000")
    book = _book([["0.10", "1000"]], quote_ts_ms=NOW_MS - 5_000)   # 5s old > 2000ms
    ctx = runner._model_context("BTC", _market(), book, NOW_MS)
    ns = plumb.normalize_signal(_market(), book, ctx, capture_ts_ms=NOW_MS)
    assert ns.signal.fill_decision == FillDecision.UNFILLED_QUOTE_STALE
