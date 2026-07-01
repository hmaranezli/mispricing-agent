"""
Paper Edge/PnL Vertical — orchestrator tests (OFFLINE, injected fetchers only, zero network).

Proves: exactly one Gamma fetch per condition_id (fee piggybacks on the cached response,
never a second fetch), fee config wired through to net PnL, win/loss/fail-closed handling,
verdict selection, and that diagnosis only runs when net PnL is negative.
"""
import sqlite3
from decimal import Decimal

import pytest

from analysis.forensic import gateg7_paper_pnl as pp
from tools import gateg7_paper_pnl_evaluator as ev


_REAL_FEE_SCHEDULE = {"exponent": 1, "rate": 0.07, "takerOnly": True, "rebateRate": 0.2}


def _gamma_market(slug, cid, *, outcomes=("Up", "Down"), token_ids=("tokUp", "tokDown"),
                  winner_idx=1, fees_enabled=True, taker_base_fee=1000,
                  fee_schedule=_REAL_FEE_SCHEDULE, closed=True):
    prices = ["0.0", "0.0"]
    if winner_idx is not None:
        prices[winner_idx] = "1.0"
    market = {"slug": slug, "conditionId": cid, "clobTokenIds": list(token_ids),
             "outcomes": list(outcomes), "outcomePrices": prices, "closed": closed,
             "umaResolutionStatus": "resolved", "feesEnabled": fees_enabled,
             "takerBaseFee": taker_base_fee}
    if fee_schedule is not None:
        market["feeSchedule"] = dict(fee_schedule)
    return [market]


def _clob_payload(cid, *, token_ids=("tokUp", "tokDown"), winner_idx=1, closed=True):
    return {"condition_id": cid, "closed": closed,
            "tokens": [{"token_id": t, "winner": (i == winner_idx)}
                      for i, t in enumerate(token_ids)]}


def _cand(**over):
    base = dict(signal_id="sig1", asset="BTC", slug="btc-updown-15m-1000", condition_id="cid-1",
                token_id="tokDown", outcome_index=1, outcome_label="Down", exec_ask_vwap="0.40",
                exec_fill_qty_avail="60", entry_edge="0.10", market_end_ts=900, ts_signal="t1",
                fill_decision="UNFILLED_EDGE_LOST", reference_age_ms=5000, tte_s=300)
    base.update(over)
    return base


# ===========================================================================
# exactly-one-gamma-fetch (fee piggybacks; never double-fetched)
# ===========================================================================
def test_evaluate_full_candidate_fetches_gamma_exactly_once():
    calls = {"gamma": 0, "clob": 0}

    def gamma_fetch(slug, cid):
        calls["gamma"] += 1
        return _gamma_market(slug, cid)

    def clob_fetch(cid):
        calls["clob"] += 1
        return _clob_payload(cid)

    ev.evaluate_full_candidate(_cand(), gamma_fetch=gamma_fetch, clob_fetch=clob_fetch)
    assert calls["gamma"] == 1
    assert calls["clob"] == 1


def test_evaluate_full_candidate_fee_piggybacks_on_cached_gamma():
    r = ev.evaluate_full_candidate(
        _cand(), gamma_fetch=lambda s, c: _gamma_market(s, c, fees_enabled=True),
        clob_fetch=lambda c: _clob_payload(c))
    assert r["fee_status"] == pp.FEE_VERIFIED_RATE
    assert r["fee_rate"] == str(Decimal("0.07"))          # feeSchedule.rate, NOT takerBaseFee/50000


def test_evaluate_full_candidate_missing_fee_schedule_is_unsupported():
    r = ev.evaluate_full_candidate(
        _cand(), gamma_fetch=lambda s, c: _gamma_market(s, c, fees_enabled=True, fee_schedule=None),
        clob_fetch=lambda c: _clob_payload(c))
    assert r["fee_status"] == pp.FEE_UNSUPPORTED_SCHEDULE
    assert r["fee_rate"] is None


def test_evaluate_full_candidate_verified_zero_fee():
    r = ev.evaluate_full_candidate(
        _cand(), gamma_fetch=lambda s, c: _gamma_market(s, c, fees_enabled=False),
        clob_fetch=lambda c: _clob_payload(c))
    assert r["fee_status"] == pp.FEE_VERIFIED_ZERO
    assert Decimal(r["fee"]) == Decimal("0")


# ===========================================================================
# win / loss payout through the full pipeline
# ===========================================================================
def test_full_candidate_win_yields_positive_gross():
    # candidate token_id=tokDown=index1, winner_idx=1 -> matched=True -> win
    r = ev.evaluate_full_candidate(
        _cand(), gamma_fetch=lambda s, c: _gamma_market(s, c, winner_idx=1),
        clob_fetch=lambda c: _clob_payload(c, winner_idx=1))
    assert r["matched"] is True
    assert Decimal(r["gross_pnl"]) > 0
    assert isinstance(r["net_pnl"], Decimal)


def test_full_candidate_loss_yields_negative_gross():
    # candidate token_id=tokDown=index1, winner_idx=0 -> matched=False -> loss
    r = ev.evaluate_full_candidate(
        _cand(), gamma_fetch=lambda s, c: _gamma_market(s, c, winner_idx=0),
        clob_fetch=lambda c: _clob_payload(c, winner_idx=0))
    assert r["matched"] is False
    assert Decimal(r["gross_pnl"]) < 0


def test_full_candidate_unresolved_has_no_pnl():
    r = ev.evaluate_full_candidate(
        _cand(), gamma_fetch=lambda s, c: _gamma_market(s, c, closed=False),
        clob_fetch=lambda c: _clob_payload(c))
    assert r["status"] != "RESOLVED"
    assert r["net_pnl"] is None


def test_full_candidate_fee_metadata_missing_keeps_gross_but_net_sentinel():
    r = ev.evaluate_full_candidate(
        _cand(), gamma_fetch=lambda s, c: _gamma_market(s, c, fees_enabled=None),
        clob_fetch=lambda c: _clob_payload(c))
    assert r["fee_status"] == pp.FEE_METADATA_MISSING
    assert r["net_pnl"] == pp.FEE_METADATA_MISSING
    assert "gross_pnl" in r


# ===========================================================================
# diagnosis only on negative net PnL
# ===========================================================================
def test_diagnose_negative_pnl_has_six_categories():
    cand = _cand(signal_id="sig1")
    result = {"status": "RESOLVED", "matched": False, "gross_pnl": "-24",
             "net_pnl": Decimal("-24.288")}
    out = ev.diagnose_negative_pnl([cand], {"sig1": result})
    for key in ("wrong_directional_model", "ask_spread_depth_cost", "stale_reference",
               "proxy_hl_basis", "entry_timing", "fee_drag"):
        assert key in out


def test_diagnose_negative_pnl_no_resolved_returns_note():
    out = ev.diagnose_negative_pnl([_cand()], {"sig1": {"status": "RESOLUTION_NOT_FINAL"}})
    assert "note" in out


# ===========================================================================
# end-to-end run_evaluation: dedup + bucketing + verdict (DB-backed, injected fetchers)
# ===========================================================================
def _market_book(cid, tok, *, end_s, ts_signal_ms, ask="0.40"):
    """Build a real signal_log row via the proven normalize_signal pipeline (entry_edge>0.10
    forces fill_decision in {FILLED_ACTIVE, UNFILLED_EDGE_LOST} territory, both eligible)."""
    from analysis.forensic import gateg5_plumbing as plumb
    market = dict(asset="BTC", side="NO", condition_id=cid, token_id=tok, outcome_index=1,
                  outcome_label="Down", slug=f"btc-updown-15m-{end_s-600}",
                  market_end_ts=end_s, clobTokenIds=["tokUp", tok], outcomes=["Up", "Down"])
    book = {"asks": [[ask, "1000"]], "bids": [["0.05", "1000"]], "quote_ts_ms": ts_signal_ms - 100}
    context = {"reference_feed_ts": ts_signal_ms - 30_000, "intended_stake": "25",
              "decision_cost_buffer": "0", "realized_entry_cost": "0", "realized_fee_cost": "0",
              "fair_yes": "0.65", "fair_yes_sigma": "0.8", "fair_model_version": "test",
              "strike": "60000", "reference_price": "59000", "underlying_spot_price": "59000",
              "entry_edge": "0.20"}
    return plumb.normalize_signal(market, book, context, capture_ts_ms=ts_signal_ms)


def _build_db(tmp_path, specs):
    """specs: list of (condition_id, token_id, end_s, ts_signal_ms)."""
    from analysis.forensic import gateg5_plumbing as plumb
    db = str(tmp_path / "eval.sqlite3")
    conn = sqlite3.connect(db)
    plumb.init_mock_db(conn)
    prev = "GENESIS"
    for cid, tok, end_s, ts_ms in specs:
        ns = _market_book(cid, tok, end_s=end_s, ts_signal_ms=ts_ms)
        prev = plumb.write_signal(conn, ns, prev_hash=prev)
    conn.commit()
    conn.close()
    return db


def test_run_evaluation_insufficient_n_when_no_candidates(tmp_path):
    db = _build_db(tmp_path, [])
    report = ev.run_evaluation(db, gamma_fetch=lambda s, c: [], clob_fetch=lambda c: {})
    assert report["verdict"] == "INSUFFICIENT_RESOLVED_N"
    assert report["cohort"]["candidates"] == 0


def test_run_evaluation_dedups_to_one_gamma_fetch_per_condition(tmp_path):
    db = _build_db(tmp_path, [
        ("0xcid1", "tokDownA", 1000, 500_100),
        ("0xcid1", "tokDownA", 1000, 500_050),   # same cid, EARLIER ts -> this one kept
        ("0xcid2", "tokDownB", 1000, 500_010),
    ])
    calls = {"n": 0}

    def gamma_fetch(slug, cid):
        calls["n"] += 1
        return _gamma_market(slug, cid, winner_idx=1)

    report = ev.run_evaluation(db, gamma_fetch=gamma_fetch, clob_fetch=lambda c: _clob_payload(c))
    assert calls["n"] == 2                          # one per UNIQUE condition_id, not per row
    assert report["cohort"]["candidates"] == 2
    assert {c["condition_id"] for c in report["per_candidate"]} == {"0xcid1", "0xcid2"}


def test_run_evaluation_edge_promising_verdict(tmp_path):
    db = _build_db(tmp_path, [("0xcid1", "tokDownA", 1000, 500_000)])
    report = ev.run_evaluation(
        db, gamma_fetch=lambda s, c: _gamma_market(s, c, winner_idx=1, fees_enabled=False,
                                                   token_ids=("tokUp", "tokDownA")),
        clob_fetch=lambda c: _clob_payload(c, winner_idx=1, token_ids=("tokUp", "tokDownA")))
    assert report["verdict"] == "EDGE_PROMISING"
    assert "NOT tradeable alpha" in report["telegram_summary"]


def test_run_evaluation_edge_negative_diagnose_verdict(tmp_path):
    db = _build_db(tmp_path, [("0xcid1", "tokDownA", 1000, 500_000)])
    report = ev.run_evaluation(
        db, gamma_fetch=lambda s, c: _gamma_market(s, c, winner_idx=0, fees_enabled=False,
                                                   token_ids=("tokUp", "tokDownA")),
        clob_fetch=lambda c: _clob_payload(c, winner_idx=0, token_ids=("tokUp", "tokDownA")))
    assert report["verdict"] == "EDGE_NEGATIVE_DIAGNOSE"
    assert report["diagnosis"] is not None


def test_run_evaluation_does_not_mutate_db(tmp_path):
    db = _build_db(tmp_path, [("0xcid1", "tokDownA", 1000, 500_000)])
    before = open(db, "rb").read()
    ev.run_evaluation(db, gamma_fetch=lambda s, c: [], clob_fetch=lambda c: {})
    after = open(db, "rb").read()
    assert before == after          # no DB mutation from a read-only evaluation
