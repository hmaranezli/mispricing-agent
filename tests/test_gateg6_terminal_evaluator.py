"""
Gate G.6 — Terminal evaluator offline unit tests (static mock Gamma/CLOB JSON).

  * NO live API: fetchers are injected; all payloads are static dicts/lists.
  * NO DB writes, NO S1, NO wallet/capital/orders.

Run with:  pytest -q tests/test_gateg6_terminal_evaluator.py
"""

import importlib.util
from decimal import Decimal

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "gateg6_terminal_evaluator", "/root/mispricing_agent/tools/gateg6_terminal_evaluator.py")
ev = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ev)

CID = "0xCID"
SLUG = "btc-updown-15m-1782813600"
UP_TOK = "111"
DOWN_TOK = "222"


def cand(outcome_label="Down", token_id=DOWN_TOK, exec_ask="0.20",
         qty="125", ts_signal="2026-06-30T10:00:00Z", **over):
    base = dict(signal_id="sig1", asset="BTC", outcome_label=outcome_label,
                outcome_index=1, condition_id=CID, token_id=token_id,
                exec_ask_vwap=exec_ask, exec_fill_qty_avail=qty, entry_edge="0.20",
                ts_signal=ts_signal, market_end_ts=1782814500, slug=SLUG)
    base.update(over)
    return base


def gamma_payload(closed=True, uma="resolved", prices=("0", "1"),
                  outcomes=("Up", "Down"), toks=(UP_TOK, DOWN_TOK), slug=SLUG, cid=CID):
    return [{"slug": slug, "conditionId": cid, "closed": closed,
             "umaResolutionStatus": uma,
             "outcomePrices": list(prices), "outcomes": list(outcomes),
             "clobTokenIds": list(toks),
             "resolutionSource": "https://data.chain.link/streams/btc-usd"}]


def clob_payload(closed=True, winner_tok=DOWN_TOK, toks=((UP_TOK, "Up"), (DOWN_TOK, "Down")), cid=CID):
    return {"condition_id": cid, "closed": closed,
            "tokens": [{"token_id": t, "outcome": o, "winner": (t == winner_tok)} for t, o in toks]}


def _eval(c, g, cl):
    return ev.evaluate_candidate(c, gamma_fetch=lambda s, i: g, clob_fetch=lambda i: cl)


# ---- clean resolved win (Down wins; candidate Down) ----
def test_clean_resolved_win():
    r = _eval(cand(), gamma_payload(prices=("0", "1")), clob_payload(winner_tok=DOWN_TOK))
    assert r["status"] == ev.ST_RESOLVED
    assert r["matched"] is True and r["payout"] == "1"
    assert Decimal(r["pnl_per_share"]) == Decimal("0.80")
    # min(125, 25/0.20=125) = 125 -> 0.80*125 = 100
    assert Decimal(r["normalized_pnl_at_25usd"]) == Decimal("100.00")


# ---- clean resolved loss (Up wins; candidate Down) ----
def test_clean_resolved_loss():
    r = _eval(cand(), gamma_payload(prices=("1", "0")), clob_payload(winner_tok=UP_TOK))
    assert r["status"] == ev.ST_RESOLVED
    assert r["matched"] is False and r["payout"] == "0"
    assert Decimal(r["pnl_per_share"]) == Decimal("-0.20")
    assert Decimal(r["normalized_pnl_at_25usd"]) == Decimal("-25.00")  # full diagnostic stake lost


# ---- fail-closed states ----
def test_resolution_missing_no_match():
    r = _eval(cand(), [], clob_payload())                       # gamma empty
    assert r["status"] == ev.ST_RES_MISSING


def test_resolution_not_final_uma():
    r = _eval(cand(), gamma_payload(uma="proposed"), clob_payload())
    assert r["status"] == ev.ST_RES_NOT_FINAL


def test_resolution_not_final_open():
    r = _eval(cand(), gamma_payload(closed=False), clob_payload())
    assert r["status"] == ev.ST_RES_NOT_FINAL


def test_price_token_mismatch():
    # candidate token not present in CLOB token set
    r = _eval(cand(token_id=DOWN_TOK),
              gamma_payload(), clob_payload(toks=((UP_TOK, "Up"), ("999", "Down")), winner_tok=UP_TOK))
    assert r["status"] == ev.ST_PRICE_TOKEN_MISMATCH


def test_unresolved_conflict():
    # Gamma says Down won (prices 0,1) but CLOB marks Up as winner
    r = _eval(cand(), gamma_payload(prices=("0", "1")), clob_payload(winner_tok=UP_TOK))
    assert r["status"] == ev.ST_CONFLICT


def test_outcome_index_ambiguous_unknown_label():
    # local label "Maybe" not a known synonym -> fail closed, no positional fallback
    r = _eval(cand(outcome_label="Maybe"), gamma_payload(), clob_payload())
    assert r["status"] == ev.ST_OUTCOME_AMBIGUOUS


def test_void_or_refund_non_binary():
    r = _eval(cand(), gamma_payload(prices=("0.5", "0.5")), clob_payload())
    assert r["status"] == ev.ST_VOID_OR_REFUND


# ---- normalized min() clamp math ----
def test_normalized_clamp_uses_min():
    # exec_fill_qty_avail (1000) far exceeds 25/0.20 (=125) -> clamp to 125
    r = _eval(cand(qty="1000"), gamma_payload(prices=("0", "1")), clob_payload(winner_tok=DOWN_TOK))
    assert Decimal(r["normalized_qty_25"]) == Decimal("125")
    assert Decimal(r["normalized_pnl_at_25usd"]) == Decimal("100.00")


def test_normalized_clamp_uses_avail_when_smaller():
    # exec_fill_qty_avail (50) < 25/0.20 (=125) -> use 50
    r = _eval(cand(qty="50"), gamma_payload(prices=("0", "1")), clob_payload(winner_tok=DOWN_TOK))
    assert Decimal(r["normalized_qty_25"]) == Decimal("50")
    assert Decimal(r["normalized_pnl_at_25usd"]) == Decimal("40.00")  # 0.80*50


# ---- dedup chooses earliest ts_signal ----
def test_dedup_earliest_ts_signal():
    a = cand(ts_signal="2026-06-30T10:05:00Z", signal_id="late")
    b = cand(ts_signal="2026-06-30T10:00:00Z", signal_id="early")
    out = ev.dedup_earliest([a, b])
    assert len(out) == 1 and out[0]["signal_id"] == "early"


# ---- unique window effective-N ----
def test_effective_n_unique_windows_and_cross_asset():
    cands = [
        cand(asset="BTC", condition_id="0xA", slug="btc-updown-15m-1000"),
        cand(asset="SOL", condition_id="0xB", slug="sol-updown-15m-1000"),   # same window, cross-asset
        cand(asset="BTC", condition_id="0xA", slug="btc-updown-15m-1000"),   # dup of 0xA
        cand(asset="BTC", condition_id="0xC", slug="btc-updown-15m-2000"),
    ]
    eff = ev.effective_n_report(cands)
    assert eff["total_rows"] == 4
    assert eff["unique_condition_ids"] == 3
    assert eff["unique_windows"] == 2
    assert eff["duplicate_condition_ids"] == 1     # 0xA appears twice
    assert eff["same_window_cross_asset_windows"] == 1
    assert eff["correlation_warning"] is True


# ---- pure deciders directly on static JSON ----
def test_gamma_decide_pure():
    st, idx, meta = ev.gamma_decide(gamma_payload(prices=("0", "1")), SLUG, CID)
    assert st == ev.ST_RESOLVED and idx == 1
    assert meta["resolutionSource"].endswith("btc-usd")


def test_clob_decide_pure():
    st, tok, meta = ev.clob_decide(clob_payload(winner_tok=DOWN_TOK), CID)
    assert st == ev.ST_RESOLVED and tok == DOWN_TOK
    assert meta["winner_outcome"] == "Down"
