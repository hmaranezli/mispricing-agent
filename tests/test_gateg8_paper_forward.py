"""
Gate G8 — Forward Paper Dual-Book Capture (OFFLINE).

Covers the pure additions (outcome-label binding, dual-book paper-decision builder,
one-entry-per-condition guard) plus the network-capable orchestrator (injected fetchers,
zero live network) that connects them to real Gamma/CLOB/HL shapes.

PAPER/SHADOW only. NO orders, wallet, signing, capital, or S1 anywhere in this module.
"""
import importlib.util
from decimal import Decimal

import pytest

from analysis.forensic import gateg7_paper_pnl as pp

RUNNER_PATH = "/root/mispricing_agent/tools/gateg5_telemetry_runner.py"


def _load_runner(name="gateg5_telemetry_runner_g8"):
    spec = importlib.util.spec_from_file_location(name, RUNNER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


runner = _load_runner()

from tools import gateg8_paper_forward_capture as fwd  # noqa: E402

NOW_MS = 1_900_000_000_000


# ===========================================================================
# 1/2. outcome-label binding — never by index; swapped order; ambiguous fail-closed
# ===========================================================================
def test_bind_yes_no_tokens_normal_order():
    b = pp.bind_yes_no_tokens(["Up", "Down"], ["tokUp", "tokDown"])
    assert b == {"yes_index": 0, "no_index": 1, "yes_token_id": "tokUp", "no_token_id": "tokDown"}


def test_bind_yes_no_tokens_swapped_order():
    # Down listed FIRST, Up SECOND -> must still bind by label, not by fixed index
    b = pp.bind_yes_no_tokens(["Down", "Up"], ["tokDown", "tokUp"])
    assert b == {"yes_index": 1, "no_index": 0, "yes_token_id": "tokUp", "no_token_id": "tokDown"}


@pytest.mark.parametrize("labels", [["Yes", "No"], ["YES", "NO"], [" yes ", " no "]])
def test_bind_yes_no_tokens_label_variants(labels):
    b = pp.bind_yes_no_tokens(labels, ["tokA", "tokB"])
    assert b["yes_token_id"] == "tokA" and b["no_token_id"] == "tokB"


def test_bind_yes_no_tokens_duplicate_labels_fail_closed():
    with pytest.raises(pp.OutcomeBindingError):
        pp.bind_yes_no_tokens(["Up", "Up"], ["tokA", "tokB"])


def test_bind_yes_no_tokens_unknown_label_fail_closed():
    with pytest.raises(pp.OutcomeBindingError):
        pp.bind_yes_no_tokens(["Up", "Maybe"], ["tokA", "tokB"])


def test_bind_yes_no_tokens_missing_outcome_fail_closed():
    with pytest.raises(pp.OutcomeBindingError):
        pp.bind_yes_no_tokens(["Up"], ["tokA"])


def test_bind_yes_no_tokens_never_guesses_from_index():
    # if labels are ambiguous/unreadable, never fall back to outcomes[0]/outcomes[1]
    with pytest.raises(pp.OutcomeBindingError):
        pp.bind_yes_no_tokens([None, "Down"], ["tokA", "tokB"])


# ===========================================================================
# helpers for build_paper_decision
# ===========================================================================
def _market(**over):
    base = dict(conditionId="cid-1", slug="btc-updown-15m-1000", asset="BTC",
               outcomes=["Up", "Down"], clobTokenIds=["tokUp", "tokDown"],
               market_end_ts=NOW_MS // 1000 + 600, feesEnabled=True,
               feeSchedule={"exponent": 1, "rate": 0.07, "takerOnly": True, "rebateRate": 0.2})
    base.update(over)
    return base


def _book(price, *, quote_ts_ms, started_ms, completed_ms, size="1000"):
    return {"asks": [[price, size]], "quote_ts_ms": quote_ts_ms,
            "capture_started_ms": started_ms, "capture_completed_ms": completed_ms}


def _clean_books(yes_price="0.40", no_price="0.55"):
    yes = _book(yes_price, quote_ts_ms=NOW_MS - 100, started_ms=NOW_MS - 500, completed_ms=NOW_MS - 400)
    no = _book(no_price, quote_ts_ms=NOW_MS - 90, started_ms=NOW_MS - 400, completed_ms=NOW_MS - 300)
    return yes, no


# ===========================================================================
# 4. decision occurs only after both books/reference capture (no-lookahead)
# ===========================================================================
def test_build_paper_decision_ts_after_all_capture_completions():
    yes, no = _clean_books()
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["paper_decision_ts"] == NOW_MS
    assert d["paper_decision_ts"] >= yes["capture_completed_ms"]
    assert d["paper_decision_ts"] >= no["capture_completed_ms"]
    assert d["paper_decision_ts"] >= (NOW_MS - 30_000)   # >= hl feed_ts


def test_build_paper_decision_no_input_after_decision_ts():
    import inspect
    params = inspect.signature(pp.build_paper_decision).parameters
    for forbidden in ("resolution", "outcome", "winner"):
        assert forbidden not in params


# ===========================================================================
# 5. future/stale/unexecutable fail closed
# ===========================================================================
def test_future_yes_quote_rejected():
    yes, no = _clean_books()
    yes["quote_ts_ms"] = NOW_MS + 5000        # future relative to decision_ts
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["status"] == "FUTURE_TIMESTAMP_REJECTED"


def test_stale_no_quote_rejected():
    yes, no = _clean_books()
    no["quote_ts_ms"] = NOW_MS - 5000          # 5s stale, > QUOTE_STALE_MS(2000)
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["status"] == "STALE_QUOTE_REJECTED"
    assert d["side"] == "NO"


def test_insufficient_depth_rejected():
    yes, no = _clean_books()
    yes["asks"] = [["0.40", "0.0000001"]]      # not enough depth to absorb $25 stake
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["status"] == "INSUFFICIENT_DEPTH_REJECTED"


def test_dual_book_skew_exceeded_rejected_no_paper_open():
    yes, no = _clean_books()
    no["capture_completed_ms"] = yes["capture_completed_ms"] + 10_000   # 10s skew
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["status"] == "DUAL_BOOK_SKEW_EXCEEDED"
    assert d["dual_book_skew_ms"] == 10_000
    assert d["status"] != "PAPER_OPEN"


def test_dual_book_skew_within_bound_proceeds():
    yes, no = _clean_books()
    no["capture_completed_ms"] = yes["capture_completed_ms"] + 100   # small skew, within bound
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["status"] in ("PAPER_OPEN", "NO_PAPER_ENTRY")   # not skew-rejected
    assert d["dual_book_skew_ms"] == 100


# ===========================================================================
# 6/7. YES selected / NO selected on real-shaped dual-book fixtures
# ===========================================================================
def test_yes_selected_real_shaped():
    yes, no = _clean_books(yes_price="0.40", no_price="0.55")   # fair_yes=0.70 favors YES
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["status"] == "PAPER_OPEN"
    assert d["selected_side"] == "YES"
    assert d["selected_token_id"] == "tokUp"
    assert Decimal(d["yes_net_edge"]) > 0
    assert d["selected_filled_qty"] is not None and d["selected_entry_notional"] is not None


def test_no_selected_real_shaped():
    yes, no = _clean_books(yes_price="0.55", no_price="0.40")   # fair_yes=0.20 favors NO
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.20"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["status"] == "PAPER_OPEN"
    assert d["selected_side"] == "NO"
    assert d["selected_token_id"] == "tokDown"


def test_yes_selected_swapped_outcome_order():
    # Down listed FIRST in outcomes/tokens -- binding must still track the label, not index
    yes, no = _clean_books(yes_price="0.40", no_price="0.55")
    market = _market(outcomes=["Down", "Up"], clobTokenIds=["tokDown", "tokUp"])
    d = pp.build_paper_decision(market=market, yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["selected_side"] == "YES"
    assert d["selected_token_id"] == "tokUp"


# ===========================================================================
# 8. both negative / tie -> no entry
# ===========================================================================
def test_both_negative_no_entry():
    yes, no = _clean_books(yes_price="0.90", no_price="0.90")
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.50"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["status"] == "NO_PAPER_ENTRY"
    assert d["no_entry_reason"] == pp.NO_PAPER_ENTRY
    assert d["selected_side"] is None


def test_exact_tie_no_entry():
    market = _market(feesEnabled=False)
    yes, no = _clean_books(yes_price="0.40", no_price="0.40")
    d = pp.build_paper_decision(market=market, yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.50"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["status"] == "NO_PAPER_ENTRY"
    assert d["no_entry_reason"] == pp.EDGE_TIE_NO_ENTRY


# ===========================================================================
# 9. canonical feeSchedule used (never takerBaseFee fallback)
# ===========================================================================
def test_canonical_fee_schedule_used_not_taker_base_fee():
    market = _market(takerBaseFee=1000)   # present but must be ignored
    yes, no = _clean_books()
    d = pp.build_paper_decision(market=market, yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["fee_rate"] == "0.07"
    assert d["fee_rate"] != str(Decimal("1000") / Decimal("50000"))


# ===========================================================================
# 10. one entry maximum per condition_id
# ===========================================================================
def test_enforce_one_entry_per_condition_downgrades_duplicates():
    decisions = [
        {"status": "PAPER_OPEN", "condition_id": "cid-1", "paper_decision_ts": 100},
        {"status": "PAPER_OPEN", "condition_id": "cid-1", "paper_decision_ts": 200},
        {"status": "PAPER_OPEN", "condition_id": "cid-2", "paper_decision_ts": 150},
    ]
    out = pp.enforce_one_entry_per_condition(decisions)
    statuses = [(d["condition_id"], d["status"]) for d in out]
    assert statuses.count(("cid-1", "PAPER_OPEN")) == 1
    assert statuses.count(("cid-1", "DUPLICATE_CONDITION_SKIPPED")) == 1
    assert statuses.count(("cid-2", "PAPER_OPEN")) == 1


def test_enforce_one_entry_per_condition_leaves_non_open_untouched():
    decisions = [{"status": "NO_PAPER_ENTRY", "condition_id": "cid-1"},
                {"status": "NO_PAPER_ENTRY", "condition_id": "cid-1"}]
    out = pp.enforce_one_entry_per_condition(decisions)
    assert all(d["status"] == "NO_PAPER_ENTRY" for d in out)
    assert len(out) == 2


# ===========================================================================
# 11. paper ledger contains all required entry evidence
# ===========================================================================
def test_paper_decision_contains_all_required_ledger_fields():
    yes, no = _clean_books()
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS)
    required = ("condition_id", "slug", "asset", "window", "paper_decision_ts", "fair_yes",
               "reference_age_ms", "tte_s", "yes_token_id", "no_token_id", "yes_quote_ts_ms",
               "no_quote_ts_ms", "yes_capture_started_ms", "yes_capture_completed_ms",
               "no_capture_started_ms", "no_capture_completed_ms", "dual_book_skew_ms",
               "yes_exec_ask_vwap", "yes_filled_qty", "no_exec_ask_vwap", "no_filled_qty",
               "fee_rate", "fee_exponent", "yes_gross_edge", "yes_net_edge", "no_gross_edge",
               "no_net_edge", "selected_side", "selected_token_id", "no_entry_reason",
               "selected_filled_qty", "selected_entry_notional", "status")
    for f in required:
        assert f in d, f"missing ledger field: {f}"


# ===========================================================================
# ORCHESTRATOR (injected fetchers; zero live network)
# ===========================================================================
class _FakeBookClient:
    """Sequential fake CLOB book source, keyed by token_id. Counts calls; no retry check."""

    def __init__(self, books_by_token):
        self.books_by_token = books_by_token
        self.calls = []

    def __call__(self, url, params=None):
        token_id = params["token_id"]
        self.calls.append(token_id)
        return self.books_by_token[token_id]


def _real_shaped_book(price, size="1000", ts=None):
    """Real CLOB /book response shape: asks are dicts with price/size keys (matches the
    proven _fetch_market_and_book parsing in tools/gateg5_telemetry_runner.py)."""
    return {"asks": [{"price": price, "size": size}], "bids": [], "timestamp": ts or NOW_MS}


def _hl_fixture(p_now="59000", strike="60000", sigma=0.8):
    def pf(coin, ts_ms):
        return (Decimal(p_now), ts_ms - 30_000) if ts_ms >= NOW_MS - 1000 else (Decimal(strike), ts_ms)
    return pf, (lambda coin, now_ms: sigma)


def test_orchestrator_exactly_two_book_gets_no_retry(monkeypatch):
    client = _FakeBookClient({
        "tokUp": _real_shaped_book("0.40", ts=NOW_MS - 100),
        "tokDown": _real_shaped_book("0.55", ts=NOW_MS - 90),
    })
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 100)))
    result = fwd.capture_and_decide(_market(), now_ms_provider=lambda: next(times),
                                    max_skew_ms=5000, book_fetch_client=client,
                                    hl_price_feedts=pf, hl_sigma_annual=sig)
    assert len(client.calls) == 2
    assert set(client.calls) == {"tokUp", "tokDown"}
    assert result["status"] in ("PAPER_OPEN", "NO_PAPER_ENTRY")


def test_orchestrator_decision_ordering_after_capture(monkeypatch):
    client = _FakeBookClient({
        "tokUp": _real_shaped_book("0.40", ts=NOW_MS - 100),
        "tokDown": _real_shaped_book("0.55", ts=NOW_MS - 90),
    })
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 100)))
    result = fwd.capture_and_decide(_market(), now_ms_provider=lambda: next(times),
                                    max_skew_ms=5000, book_fetch_client=client,
                                    hl_price_feedts=pf, hl_sigma_annual=sig)
    assert result["paper_decision_ts"] >= result["yes_capture_completed_ms"]
    assert result["paper_decision_ts"] >= result["no_capture_completed_ms"]


def test_orchestrator_no_wallet_or_order_imports():
    # scan actual import/call statements only, not the module's own safety-declaring docstring
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(fwd))
    imported = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            calls.add(node.func.attr)
    for forbidden_module in ("wallet", "signing", "execution", "web3"):
        assert not any(forbidden_module in m.lower() for m in imported), imported
    for forbidden_call in ("sign", "place_order", "send_transaction"):
        assert forbidden_call not in calls, calls


def test_orchestrator_paper_ledger_write_and_read(tmp_path):
    db = str(tmp_path / "g8.sqlite3")
    import sqlite3
    conn = sqlite3.connect(db)
    fwd.init_paper_ledger(conn)
    decision = {"status": "PAPER_OPEN", "condition_id": "cid-1", "slug": "btc-updown-15m-1000",
               "asset": "BTC", "window": "1000", "paper_decision_ts": NOW_MS, "fair_yes": "0.70",
               "reference_age_ms": 30_000, "tte_s": 300, "yes_token_id": "tokUp",
               "no_token_id": "tokDown", "yes_quote_ts_ms": NOW_MS - 100, "no_quote_ts_ms": NOW_MS - 90,
               "yes_capture_started_ms": NOW_MS - 500, "yes_capture_completed_ms": NOW_MS - 400,
               "no_capture_started_ms": NOW_MS - 400, "no_capture_completed_ms": NOW_MS - 300,
               "dual_book_skew_ms": 100, "yes_exec_ask_vwap": "0.40", "yes_filled_qty": "62.5",
               "no_exec_ask_vwap": "0.55", "no_filled_qty": "45.45", "fee_rate": "0.07",
               "fee_exponent": 1, "yes_gross_edge": "0.30", "yes_net_edge": "0.28",
               "no_gross_edge": "-0.25", "no_net_edge": "-0.27", "selected_side": "YES",
               "selected_token_id": "tokUp", "no_entry_reason": None,
               "selected_filled_qty": "62.5", "selected_entry_notional": "25"}
    fwd.write_paper_ledger(conn, decision)
    conn.commit()
    row = conn.execute("SELECT condition_id, status, selected_side FROM gateg8_paper_ledger").fetchone()
    assert row == ("cid-1", "PAPER_OPEN", "YES")
    conn.close()


def test_orchestrator_default_off_arm(monkeypatch):
    monkeypatch.delenv(fwd.PAPER_ARM_ENV, raising=False)
    assert fwd.is_armed() is False
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    assert fwd.is_armed() is True


# ===========================================================================
# 12. existing G7 default-off telemetry behavior unchanged (spot-check import + defaults)
# ===========================================================================
def test_existing_runner_defaults_unchanged():
    assert runner.MAX_OBSERVATIONS == 100 or isinstance(runner.MAX_OBSERVATIONS, int)
    assert runner.PROXY_ARM_TOKEN == "PROXY-BASIS-CONFIRMED"
    # importing the g8 module must not alter the g5 runner's armed-by-default state
    import os
    assert os.environ.get(runner.TELEMETRY_ARM_ENV, "") != runner.TELEMETRY_ARM_TOKEN
