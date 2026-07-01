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


@pytest.fixture(autouse=True)
def _block_live_network(monkeypatch):
    """Every test in this module drives injected fakes only; hard-patch urlopen so any
    accidentally-unmocked path fails loudly instead of silently reaching the live network.
    urllib.request is a process-wide singleton module, so this also covers calls made
    through tools.gateg8_paper_forward_capture's real gateg5_telemetry_runner import."""
    monkeypatch.setattr(runner.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("live network")))


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
               "hl_capture_started_ms", "hl_capture_completed_ms",
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
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
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
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
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


# ===========================================================================
# BLOCKER 5 — token-ID integrity: two distinct non-empty string token IDs required
# before any CLOB GET. Never guessed, no invented numeric regex.
# ===========================================================================
def test_bind_yes_no_tokens_rejects_none_token_id():
    with pytest.raises(pp.OutcomeBindingError):
        pp.bind_yes_no_tokens(["Up", "Down"], [None, "tokDown"])


def test_bind_yes_no_tokens_rejects_empty_token_id():
    with pytest.raises(pp.OutcomeBindingError):
        pp.bind_yes_no_tokens(["Up", "Down"], ["", "tokDown"])


def test_bind_yes_no_tokens_rejects_whitespace_only_token_id():
    with pytest.raises(pp.OutcomeBindingError):
        pp.bind_yes_no_tokens(["Up", "Down"], ["   ", "tokDown"])


def test_bind_yes_no_tokens_rejects_duplicate_token_ids():
    with pytest.raises(pp.OutcomeBindingError):
        pp.bind_yes_no_tokens(["Up", "Down"], ["tokSame", "tokSame"])


def test_bind_yes_no_tokens_rejects_non_string_token_id():
    with pytest.raises(pp.OutcomeBindingError):
        pp.bind_yes_no_tokens(["Up", "Down"], [12345, "tokDown"])


def test_capture_and_decide_invalid_token_ids_never_calls_book_client(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    client = _FakeBookClient({})
    pf, sig = _hl_fixture()
    market = _market(clobTokenIds=[None, "tokDown"])
    with pytest.raises(pp.OutcomeBindingError):
        fwd.capture_and_decide(market, now_ms_provider=lambda: NOW_MS, max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert client.calls == []


# ===========================================================================
# BLOCKER 3 — complete HL timing proof: hl_capture_started_ms/completed_ms recorded,
# persisted, and enforced in the same no-lookahead ordering as the dual books.
# ===========================================================================
def test_build_paper_decision_hl_capture_completed_future_rejected():
    yes, no = _clean_books()
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS,
                                hl_capture_started_ms=NOW_MS - 200,
                                hl_capture_completed_ms=NOW_MS + 1000)
    assert d["status"] == "FUTURE_TIMESTAMP_REJECTED"
    assert d["field"] == "hl_capture_completed_ms"


def test_build_paper_decision_persists_hl_capture_timing():
    yes, no = _clean_books()
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no,
                                fair_yes=Decimal("0.70"), feed_ts=NOW_MS - 30_000, tte_s=300,
                                max_skew_ms=5000, decision_ts=NOW_MS,
                                hl_capture_started_ms=NOW_MS - 300,
                                hl_capture_completed_ms=NOW_MS - 200)
    assert d["hl_capture_started_ms"] == NOW_MS - 300
    assert d["hl_capture_completed_ms"] == NOW_MS - 200
    assert d["paper_decision_ts"] >= d["hl_capture_completed_ms"] >= d["hl_capture_started_ms"]


def test_orchestrator_hl_capture_timing_actual_ordering(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    client = _FakeBookClient({
        "tokUp": _real_shaped_book("0.40", ts=NOW_MS - 100),
        "tokDown": _real_shaped_book("0.55", ts=NOW_MS - 90),
    })
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 100)))
    result = fwd.capture_and_decide(_market(), now_ms_provider=lambda: next(times),
                                    max_skew_ms=5000, book_fetch_client=client,
                                    hl_price_feedts=pf, hl_sigma_annual=sig)
    assert result["hl_capture_started_ms"] is not None
    assert result["hl_capture_completed_ms"] is not None
    assert result["hl_capture_started_ms"] <= result["hl_capture_completed_ms"]
    assert result["paper_decision_ts"] >= result["hl_capture_completed_ms"]
    assert result["paper_decision_ts"] >= result["yes_capture_completed_ms"]
    assert result["paper_decision_ts"] >= result["no_capture_completed_ms"]


# ===========================================================================
# BLOCKER 2 — hard arm enforcement: main() AND capture_and_decide() must both refuse
# before ANY network call or DB write when unarmed. is_armed() alone is insufficient.
# ===========================================================================
def test_capture_and_decide_unarmed_rejects_before_network(monkeypatch):
    monkeypatch.delenv(fwd.PAPER_ARM_ENV, raising=False)
    client = _FakeBookClient({})
    pf, sig = _hl_fixture()
    with pytest.raises(PermissionError):
        fwd.capture_and_decide(_market(), now_ms_provider=lambda: NOW_MS, max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert client.calls == []


def test_main_unarmed_rejects_before_db_write(monkeypatch, tmp_path):
    monkeypatch.delenv(fwd.PAPER_ARM_ENV, raising=False)
    db = str(tmp_path / "g8_unarmed.sqlite3")
    rc = fwd.main(["--db", db])
    assert rc == 2
    import os
    assert not os.path.exists(db)


def test_main_requires_db_argument():
    with pytest.raises(SystemExit):
        fwd.main([])


def test_cli_accepts_db_argument(monkeypatch, tmp_path):
    # unarmed -> guard triggers, but argv must parse successfully first (proves --db exists)
    monkeypatch.delenv(fwd.PAPER_ARM_ENV, raising=False)
    db = str(tmp_path / "g8_cli.sqlite3")
    rc = fwd.main(["--db", db])
    assert rc == 2


# ===========================================================================
# BLOCKER 1 — real bounded driver/CLI: explicit bounds, monotonic elapsed, one ledger
# row per attempted market decision, reusing G5 market discovery/cadence/public client.
# ===========================================================================
def _armed_env(monkeypatch, *, max_obs="5", max_elapsed="600", max_skew="5000"):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    monkeypatch.setenv("GATEG8_MAX_OBSERVATIONS", max_obs)
    monkeypatch.setenv("GATEG8_MAX_ELAPSED_S", max_elapsed)
    monkeypatch.setenv("GATEG8_MAX_SKEW_MS", max_skew)
    # time.sleep is a process-wide singleton attribute; patching it here also covers the
    # bounded cadence sleep inside tools.gateg8_paper_forward_capture.run (no real 30s wait).
    monkeypatch.setattr(runner.time, "sleep", lambda *a, **k: None)


def _fake_gamma_and_book(url, params=None):
    if url == runner.GAMMA_MARKETS:
        return [{"conditionId": "cond-x", "clobTokenIds": ["tokUp", "tokDown"],
                 "outcomes": ["Up", "Down"], "slug": params["slug"],
                 "endDate": "2099-01-01T00:00:00Z"}]
    if url == runner.CLOB_BOOK:
        return _real_shaped_book("0.40")
    raise AssertionError(f"unexpected GET {url}")


def test_run_requires_explicit_bounds_env(monkeypatch, tmp_path):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    monkeypatch.delenv("GATEG8_MAX_OBSERVATIONS", raising=False)
    monkeypatch.delenv("GATEG8_MAX_ELAPSED_S", raising=False)
    monkeypatch.delenv("GATEG8_MAX_SKEW_MS", raising=False)
    db = str(tmp_path / "g8_run_noenv.sqlite3")
    with pytest.raises(PermissionError):
        fwd.run(db)


@pytest.mark.parametrize("bad_value", ["0", "-1"])
@pytest.mark.parametrize("env_name", [
    "GATEG8_MAX_OBSERVATIONS", "GATEG8_MAX_ELAPSED_S", "GATEG8_MAX_SKEW_MS"])
def test_run_rejects_non_positive_bound_before_network_or_db(monkeypatch, tmp_path, env_name, bad_value):
    _armed_env(monkeypatch)   # sets all three to valid positive defaults first
    monkeypatch.setenv(env_name, bad_value)   # then override exactly the one under test
    db = str(tmp_path / f"g8_run_badbound_{env_name}_{bad_value}.sqlite3")
    calls = []

    def no_network(url, params=None):
        calls.append(url)
        raise AssertionError("no GET expected: non-positive bound must reject first")

    with pytest.raises(PermissionError):
        fwd.run(db, public_get=no_network)
    assert calls == []
    import os
    assert not os.path.exists(db)


def test_run_unarmed_rejects_before_network_or_db(monkeypatch, tmp_path):
    monkeypatch.delenv(fwd.PAPER_ARM_ENV, raising=False)
    db = str(tmp_path / "g8_run_unarmed.sqlite3")
    with pytest.raises(PermissionError):
        fwd.run(db)
    import os
    assert not os.path.exists(db)


def test_run_stops_on_max_observations(monkeypatch, tmp_path):
    _armed_env(monkeypatch, max_obs="1")
    db = str(tmp_path / "g8_run_obs.sqlite3")
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 100_000)))
    result = fwd.run(db, now_ms_provider=lambda: next(times), monotonic_provider=lambda: 0.0,
                     public_get=_fake_gamma_and_book, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert result["stop_reason"] == "MAX_OBSERVATIONS"
    assert result["observations"] >= 1


def test_run_stops_on_monotonic_elapsed(monkeypatch, tmp_path):
    _armed_env(monkeypatch, max_obs="1000", max_elapsed="10")
    db = str(tmp_path / "g8_run_elapsed.sqlite3")
    mono = iter([0.0, 20.0])   # loop-top check already exceeds the 10s bound
    calls = []

    def no_network(url, params=None):
        calls.append(url)
        raise AssertionError("no GET expected before the elapsed bound trips")

    result = fwd.run(db, now_ms_provider=lambda: NOW_MS,
                     monotonic_provider=lambda: next(mono),
                     public_get=no_network)
    assert result["stop_reason"] == "MAX_ELAPSED"
    assert calls == []


def test_run_writes_one_ledger_row_per_attempted_market(monkeypatch, tmp_path):
    _armed_env(monkeypatch, max_obs="1")
    db = str(tmp_path / "g8_run_ledger.sqlite3")
    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 100_000)))
    fwd.run(db, now_ms_provider=lambda: next(times), monotonic_provider=lambda: 0.0,
           public_get=_fake_gamma_and_book, hl_price_feedts=pf, hl_sigma_annual=sig)
    import sqlite3
    conn = sqlite3.connect(db)
    n = conn.execute("SELECT COUNT(*) FROM gateg8_paper_ledger").fetchone()[0]
    conn.close()
    assert n == 1


def test_run_no_retry_on_transport_error_still_writes_a_row(monkeypatch, tmp_path):
    _armed_env(monkeypatch, max_obs="1")
    db = str(tmp_path / "g8_run_toxic.sqlite3")
    attempts = {"n": 0}

    def toxic_market(url, params=None):
        if url == runner.GAMMA_MARKETS:
            return [{"conditionId": "cond-toxic", "clobTokenIds": [None, "tokDown"],
                     "outcomes": ["Up", "Down"], "slug": params["slug"],
                     "endDate": "2099-01-01T00:00:00Z"}]
        attempts["n"] += 1
        raise AssertionError("book GET must never be reached for invalid token metadata")

    pf, sig = _hl_fixture()
    times = iter(list(range(NOW_MS, NOW_MS + 100_000)))
    result = fwd.run(db, now_ms_provider=lambda: next(times), monotonic_provider=lambda: 0.0,
                     public_get=toxic_market, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert attempts["n"] == 0
    import sqlite3
    conn = sqlite3.connect(db)
    n = conn.execute("SELECT COUNT(*) FROM gateg8_paper_ledger").fetchone()[0]
    conn.close()
    assert n == 1
    assert result["observations"] == 1


# ===========================================================================
# BLOCKER 4 — atomic one-PAPER_OPEN-per-condition_id in the SQLite ledger path itself
# (DB-level uniqueness guard, not only the Python-list enforce_one_entry_per_condition).
# ===========================================================================
def _open_decision(condition_id, ts):
    return {"status": "PAPER_OPEN", "condition_id": condition_id, "slug": "btc-updown-15m-1000",
           "asset": "BTC", "window": "1000", "paper_decision_ts": ts, "fair_yes": "0.70",
           "reference_age_ms": 30_000, "tte_s": 300, "yes_token_id": "tokUp",
           "no_token_id": "tokDown", "yes_quote_ts_ms": ts - 100, "no_quote_ts_ms": ts - 90,
           "yes_capture_started_ms": ts - 500, "yes_capture_completed_ms": ts - 400,
           "no_capture_started_ms": ts - 400, "no_capture_completed_ms": ts - 300,
           "dual_book_skew_ms": 100, "hl_capture_started_ms": ts - 600,
           "hl_capture_completed_ms": ts - 550,
           "yes_exec_ask_vwap": "0.40", "yes_filled_qty": "62.5",
           "no_exec_ask_vwap": "0.55", "no_filled_qty": "45.45", "fee_rate": "0.07",
           "fee_exponent": 1, "yes_gross_edge": "0.30", "yes_net_edge": "0.28",
           "no_gross_edge": "-0.25", "no_net_edge": "-0.27", "selected_side": "YES",
           "selected_token_id": "tokUp", "no_entry_reason": None,
           "selected_filled_qty": "62.5", "selected_entry_notional": "25"}


def test_write_paper_ledger_downgrades_second_paper_open_same_condition(tmp_path):
    import sqlite3
    db = str(tmp_path / "g8_dedup.sqlite3")
    conn = sqlite3.connect(db)
    fwd.init_paper_ledger(conn)
    s1 = fwd.write_paper_ledger(conn, _open_decision("cid-dup", NOW_MS))
    s2 = fwd.write_paper_ledger(conn, _open_decision("cid-dup", NOW_MS + 100))
    assert s1 == "PAPER_OPEN"
    assert s2 == "DUPLICATE_CONDITION_SKIPPED"
    rows = conn.execute(
        "SELECT status FROM gateg8_paper_ledger WHERE condition_id='cid-dup' ORDER BY id"
    ).fetchall()
    assert [r[0] for r in rows] == ["PAPER_OPEN", "DUPLICATE_CONDITION_SKIPPED"]
    assert sum(1 for r in rows if r[0] == "PAPER_OPEN") == 1
    conn.close()


def test_write_paper_ledger_dedup_survives_db_reopen(tmp_path):
    import sqlite3
    db = str(tmp_path / "g8_dedup_reopen.sqlite3")
    conn1 = sqlite3.connect(db)
    fwd.init_paper_ledger(conn1)
    fwd.write_paper_ledger(conn1, _open_decision("cid-reopen", NOW_MS))
    conn1.close()

    conn2 = sqlite3.connect(db)
    fwd.init_paper_ledger(conn2)   # idempotent re-create; unique index persists on disk
    s2 = fwd.write_paper_ledger(conn2, _open_decision("cid-reopen", NOW_MS + 500))
    assert s2 == "DUPLICATE_CONDITION_SKIPPED"
    count = conn2.execute(
        "SELECT COUNT(*) FROM gateg8_paper_ledger WHERE condition_id='cid-reopen' AND status='PAPER_OPEN'"
    ).fetchone()[0]
    assert count == 1
    conn2.close()


def test_write_paper_ledger_different_conditions_both_open(tmp_path):
    import sqlite3
    db = str(tmp_path / "g8_dedup_multi.sqlite3")
    conn = sqlite3.connect(db)
    fwd.init_paper_ledger(conn)
    s1 = fwd.write_paper_ledger(conn, _open_decision("cid-a", NOW_MS))
    s2 = fwd.write_paper_ledger(conn, _open_decision("cid-b", NOW_MS))
    assert s1 == "PAPER_OPEN" and s2 == "PAPER_OPEN"
    conn.close()


# ===========================================================================
# G8 FAILURE OBSERVABILITY PATCH — evidence-only diagnostics (RED-first).
# Deterministic injected clocks; no real sleeps or network. No behavioral change.
# ===========================================================================
import json as _json
import re as _re


class _SeqFailBookClient:
    """CLOB book source that returns a real-shaped book for the first N calls and raises
    TransportError on the (fail_index)-th call (0-based). No retry."""
    def __init__(self, books_in_order, fail_index=None, exc=None):
        self.books_in_order = books_in_order
        self.fail_index = fail_index
        self.exc = exc
        self.calls = []

    def __call__(self, url, params=None):
        i = len(self.calls)
        self.calls.append(params["token_id"])
        if self.fail_index is not None and i == self.fail_index:
            raise self.exc
        return self.books_in_order[i]


def _ok_books():
    return [_real_shaped_book("0.40", ts=NOW_MS - 100), _real_shaped_book("0.55", ts=NOW_MS - 90)]


def _clock():
    return iter(list(range(NOW_MS, NOW_MS + 200000)))


# --- 1. STALE evidence: raw ts, capture ts, age-at-capture, age-at-decision, side ---
def test_stale_rejection_persists_raw_ts_capture_ts_and_both_ages():
    yes, no = _clean_books()
    no["quote_ts_ms"] = NOW_MS - 5000                     # 5s stale on NO
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no, fair_yes=Decimal("0.70"),
                                feed_ts=NOW_MS - 30_000, tte_s=300, max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["status"] == "STALE_QUOTE_REJECTED"
    assert d["stale_side"] == "NO"
    assert d["no_quote_ts_ms"] == NOW_MS - 5000            # raw quote timestamp retained
    assert d["no_capture_started_ms"] == NOW_MS - 400
    assert d["no_capture_completed_ms"] == NOW_MS - 300
    assert d["quote_age_at_capture_ms"] == (NOW_MS - 300) - (NOW_MS - 5000)   # 4700
    assert d["quote_age_at_decision_ms"] == NOW_MS - (NOW_MS - 5000)          # 5000
    assert d["condition_id"] == "cid-1" and d["asset"] == "BTC" and d["window"] == "1000"


def test_stale_evidence_present_on_yes_side_too():
    yes, no = _clean_books()
    yes["quote_ts_ms"] = NOW_MS - 9000
    d = pp.build_paper_decision(market=_market(), yes_book=yes, no_book=no, fair_yes=Decimal("0.70"),
                                feed_ts=NOW_MS - 30_000, tte_s=300, max_skew_ms=5000, decision_ts=NOW_MS)
    assert d["status"] == "STALE_QUOTE_REJECTED" and d["stale_side"] == "YES"
    assert d["quote_age_at_decision_ms"] == 9000


# --- 2. stage timings persisted for every stage on the success/decision path ---
_REQUIRED_STAGES = ("OUTCOME_BINDING", "YES_CLOB_FETCH", "NO_CLOB_FETCH", "HL_CURRENT_PRICE",
                    "HL_WINDOW_STRIKE", "HL_SIGMA", "MODEL_CALCULATION", "TOTAL_CAPTURE_TO_DECISION")


def test_capture_success_persists_all_stage_timings(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    client = _SeqFailBookClient(_ok_books())
    pf, sig = _hl_fixture()
    times = _clock()
    d = fwd.capture_and_decide(_market(), now_ms_provider=lambda: next(times), max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert d["status"] in ("PAPER_OPEN", "NO_PAPER_ENTRY", "STALE_QUOTE_REJECTED",
                           "INSUFFICIENT_DEPTH_REJECTED")
    st = _json.loads(d["stage_timings_json"])
    for stage in _REQUIRED_STAGES:
        assert stage in st, stage
        assert set(st[stage]) >= {"start_ts", "completed_ts", "duration_ms"}
        assert st[stage]["duration_ms"] == st[stage]["completed_ts"] - st[stage]["start_ts"]
        assert st[stage]["duration_ms"] >= 0


# --- 3. CAPTURE_FAILED: each failing stage retains stage + exception class ---
def _fail_hl_pf(fail_call):
    calls = {"n": 0}
    def pf(coin, ts_ms):
        i = calls["n"]; calls["n"] += 1
        if i == fail_call:
            raise fwd.TransportError("HL failure at call %d" % i)
        return (Decimal("59000"), ts_ms - 30_000) if ts_ms >= NOW_MS - 1000 else (Decimal("60000"), ts_ms)
    return pf


@pytest.mark.parametrize("stage,mk_kwargs,client,pf,sig", [
    ("OUTCOME_BINDING", dict(clobTokenIds=[None, "tokDown"]), _SeqFailBookClient(_ok_books()),
     _hl_fixture()[0], _hl_fixture()[1]),
    ("YES_CLOB_FETCH", {}, _SeqFailBookClient(_ok_books(), fail_index=0, exc=fwd.TransportError("boom")),
     _hl_fixture()[0], _hl_fixture()[1]),
    ("NO_CLOB_FETCH", {}, _SeqFailBookClient(_ok_books(), fail_index=1, exc=fwd.TransportError("boom")),
     _hl_fixture()[0], _hl_fixture()[1]),
    # new capture order acquires the window strike FIRST, then current price: strike is HL pf
    # call 0, current price is HL pf call 1.
    ("HL_WINDOW_STRIKE", {}, _SeqFailBookClient(_ok_books()), _fail_hl_pf(0), _hl_fixture()[1]),
    ("HL_CURRENT_PRICE", {}, _SeqFailBookClient(_ok_books()), _fail_hl_pf(1), _hl_fixture()[1]),
    ("HL_SIGMA", {}, _SeqFailBookClient(_ok_books()), _hl_fixture()[0],
     (lambda coin, now_ms: (_ for _ in ()).throw(fwd.TransportError("sigma boom")))),
    ("MODEL_CALCULATION", dict(market_end_ts=NOW_MS // 1000 - 10), _SeqFailBookClient(_ok_books()),
     _hl_fixture()[0], _hl_fixture()[1]),
])
def test_capture_failure_attaches_failure_stage(monkeypatch, stage, mk_kwargs, client, pf, sig):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    times = _clock()
    with pytest.raises((pp.OutcomeBindingError, fwd.TransportError, fwd.gm.ModelInputError)) as ei:
        fwd.capture_and_decide(_market(**mk_kwargs), now_ms_provider=lambda: next(times),
                               max_skew_ms=5000, book_fetch_client=client, hl_price_feedts=pf,
                               hl_sigma_annual=sig)
    assert getattr(ei.value, "_g8_failure_stage", None) == stage
    # partial stage timings up to the failing stage must be attached
    assert isinstance(getattr(ei.value, "_g8_stage_timings", None), dict)
    assert stage in ei.value._g8_stage_timings


# --- 4. exception sanitization: no URL, no token ID, length-capped ---
def test_sanitize_exception_message_strips_url_token_and_caps():
    raw = fwd.TransportError(
        "HTTP 404 Not Found from https://clob.polymarket.com/book?token_id="
        "72992098207167438785226794729055861537646282440410797118853672361701085335416")
    msg = fwd._sanitize_exception_message(raw)
    assert "://" not in msg                          # no URL scheme survives ("HTTP 404" status word is fine)
    assert "polymarket.com" not in msg
    assert not _re.search(r"\d{16,}", msg)          # no long token id survives
    assert len(msg) <= 256


# --- 5. run(): CAPTURE_FAILED row persists stage/class/sanitized-msg + flushed log line ---
def _gamma_raw(slug):
    return {"conditionId": "cid-run-1", "slug": slug, "outcomes": ["Up", "Down"],
            "clobTokenIds": ["tokUp", "tokDown"], "endDate": "2027-01-01T00:00:00Z",
            "feesEnabled": True, "feeSchedule": {"exponent": 1, "rate": 0.07, "takerOnly": True}}


def _armed_g8_env(monkeypatch, max_obs="1"):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    monkeypatch.setenv("GATEG8_MAX_OBSERVATIONS", max_obs)
    monkeypatch.setenv("GATEG8_MAX_ELAPSED_S", "600")
    monkeypatch.setenv("GATEG8_MAX_SKEW_MS", "1500")
    monkeypatch.setattr(fwd.time, "sleep", lambda *a, **k: None)


def test_run_capture_failed_persists_evidence_and_logs(monkeypatch, tmp_path, capsys):
    _armed_g8_env(monkeypatch)
    leaky = ("HTTP 404 from https://clob.polymarket.com/book?token_id="
             "72992098207167438785226794729055861537646282440410797118853672361701085335416")

    def pg(url, params=None):
        if url == fwd.runner.GAMMA_MARKETS:
            return [_gamma_raw(params["slug"])]
        raise fwd.TransportError(leaky)   # every CLOB book GET fails at YES_CLOB_FETCH

    pf, sig = _hl_fixture()
    db = str(tmp_path / "g8_obs.sqlite3")
    times = _clock()
    fwd.run(db, now_ms_provider=lambda: next(times), monotonic_provider=lambda: 0.0,
            public_get=pg, hl_price_feedts=pf, hl_sigma_annual=sig)
    import sqlite3
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT status, failure_stage, exception_class, exception_message, asset "
                      "FROM gateg8_paper_ledger WHERE status='CAPTURE_FAILED'").fetchone()
    conn.close()
    assert row is not None
    status, stage, exc_class, exc_msg, asset = row
    assert stage == "YES_CLOB_FETCH"
    assert exc_class == "TransportError"
    assert exc_msg and "://" not in exc_msg and "polymarket.com" not in exc_msg
    assert not _re.search(r"\d{16,}", exc_msg)
    # flushed per-observation log line on stderr
    err = capsys.readouterr().err
    assert "[g8obs]" in err
    assert "status=CAPTURE_FAILED" in err and "stage=YES_CLOB_FETCH" in err
    # never leaks a book payload / url / token id into the log
    assert "asks" not in err and "://" not in err and "polymarket.com" not in err
    assert not _re.search(r"\d{16,}", err)


# --- 6. economic invariant unchanged (enrichment adds evidence keys only) ---
def test_capture_and_decide_does_not_alter_economic_fields(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    client = _SeqFailBookClient(_ok_books())
    pf, sig = _hl_fixture(p_now="60000", strike="59000")   # p_now>strike -> fair_yes>0.5 -> YES
    times = _clock()
    d = fwd.capture_and_decide(_market(), now_ms_provider=lambda: next(times), max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    if d["status"] == "PAPER_OPEN":
        sv = Decimal(d["yes_exec_ask_vwap"] if d["selected_side"] == "YES" else d["no_exec_ask_vwap"])
        assert Decimal(d["selected_entry_notional"]) == sv * Decimal(d["selected_filled_qty"])


# --- 7. next-window candidate evidence ---
def test_next_window_evidence_flags_future_window(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    m = _market(market_end_ts=NOW_MS // 1000 + 100000)   # window_start well in the future
    client = _SeqFailBookClient(_ok_books())
    pf, sig = _hl_fixture()
    times = _clock()
    d = fwd.capture_and_decide(m, now_ms_provider=lambda: next(times), max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert d["window_start_in_future"] == 1
    assert d["window_start_ms"] > d["probe_now_ms"]
    assert d["window_start_delta_ms"] == d["window_start_ms"] - d["probe_now_ms"]


def test_current_window_evidence_not_future(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    d = None
    client = _SeqFailBookClient(_ok_books())
    pf, sig = _hl_fixture()
    times = _clock()
    d = fwd.capture_and_decide(_market(), now_ms_provider=lambda: next(times), max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert d["window_start_in_future"] == 0


# ===========================================================================
# G8 CAPTURE-ORDER + FUTURE-WINDOW FIX (RED-first).
# Design A+D: HL inputs acquired first, CLOB books last; future window gated pre-network;
# mandatory strike no-lookahead guard. No economic/threshold change. Injected clocks only.
# ===========================================================================
class _MonoClock:
    """Single shared monotone millisecond clock. read() advances 1ms per call (used as the
    now_ms_provider); advance() injects per-stage acquisition latency. Models the real
    invariant that a freshly fetched CLOB quote is timestamped at ~wall-clock at fetch time."""

    def __init__(self, start=NOW_MS):
        self.now = start

    def read(self):
        self.now += 1
        return self.now

    def advance(self, ms):
        self.now += ms


def _ordered_hl(clock, log, *, strike_ts=None, p_now="60000", strike="59000", sigma=0.8,
                strike_latency_ms=0, price_latency_ms=0, sigma_latency_ms=0,
                strike_feed_offset_ms=0):
    """Injected HL providers that (a) record call order into shared `log` and (b) advance the
    shared clock to simulate real per-call latency. The window-open strike query is identified
    by exact `strike_ts` match when supplied (robust at the equality boundary), else by
    magnitude. Strike feed_ts defaults to exactly window_start_ms (no lookahead);
    strike_feed_offset_ms forces a future-dated strike candle for the guard test."""
    def _is_strike(ts):
        return ts == strike_ts if strike_ts is not None else ts < NOW_MS - 1000

    def pf(coin, ts_ms):
        if _is_strike(ts_ms):
            log.append(("HL_STRIKE", ts_ms))
            clock.advance(strike_latency_ms)
            return Decimal(strike), ts_ms + strike_feed_offset_ms
        log.append(("HL_PRICE", ts_ms))
        clock.advance(price_latency_ms)
        return Decimal(p_now), ts_ms - 30_000

    def sig(coin, now_ms):
        log.append(("HL_SIGMA", now_ms))
        clock.advance(sigma_latency_ms)
        return sigma

    return pf, sig


def _quote_client(clock, log, prices, *, age_ms=0):
    """CLOB book source: real /book shape; quote timestamp == clock.now - age_ms at fetch
    (age_ms=0 => a genuinely fresh quote). Records ('CLOB', token) call order into `log`."""
    def _get(url, params=None):
        tid = params["token_id"]
        log.append(("CLOB", tid))
        return {"asks": [{"price": prices[tid], "size": "1000"}], "bids": [],
                "timestamp": clock.now - age_ms}
    return _get


def _wsm(market):
    return (market["market_end_ts"] - fwd.TARGET_INTERVAL_S) * 1000


# --- exact provider/client call order: HL inputs first, books the FINAL acquisition ---
def test_capture_order_hl_inputs_before_books(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    clock, log, m = _MonoClock(), [], _market()
    pf, sig = _ordered_hl(clock, log, strike_ts=_wsm(m))
    client = _quote_client(clock, log, {"tokUp": "0.40", "tokDown": "0.55"})
    fwd.capture_and_decide(m, now_ms_provider=clock.read, max_skew_ms=5000,
                           book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    kinds = [k for (k, _) in log]
    assert kinds == ["HL_STRIKE", "HL_SIGMA", "HL_PRICE", "CLOB", "CLOB"]
    # both CLOB books strictly after every HL input
    assert min(i for i, k in enumerate(kinds) if k == "CLOB") > max(
        i for i, k in enumerate(kinds) if k != "CLOB")


# --- simulated 6s HL latency must NOT stale a freshly fetched quote ---
def test_hl_latency_does_not_stale_fresh_quote(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    clock, log, m = _MonoClock(), [], _market()
    pf, sig = _ordered_hl(clock, log, strike_ts=_wsm(m), strike_latency_ms=6000)
    client = _quote_client(clock, log, {"tokUp": "0.40", "tokDown": "0.55"})
    d = fwd.capture_and_decide(m, now_ms_provider=clock.read, max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert d["status"] != pp.STALE_QUOTE_REJECTED
    assert d["status"] in (pp.PAPER_OPEN, pp.NO_PAPER_ENTRY, pp.INSUFFICIENT_DEPTH_REJECTED)


# --- a genuinely old CLOB quote still becomes STALE (decision-time freshness preserved) ---
def test_genuinely_old_quote_still_stale(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    clock, log, m = _MonoClock(), [], _market()
    pf, sig = _ordered_hl(clock, log, strike_ts=_wsm(m))
    client = _quote_client(clock, log, {"tokUp": "0.40", "tokDown": "0.55"}, age_ms=5000)
    d = fwd.capture_and_decide(m, now_ms_provider=clock.read, max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert d["status"] == pp.STALE_QUOTE_REJECTED
    assert d["stale_side"] in ("YES", "NO")
    assert d["quote_age_at_decision_ms"] >= 5000


# --- future next-window: WINDOW_NOT_STARTED with ZERO provider/network calls ---
def test_future_window_not_started_zero_network(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    clock, log = _MonoClock(), []
    m = _market(market_end_ts=NOW_MS // 1000 + 100_000)   # window_start well in the future
    pf, sig = _ordered_hl(clock, log, strike_ts=_wsm(m))
    client = _quote_client(clock, log, {"tokUp": "0.40", "tokDown": "0.55"})
    d = fwd.capture_and_decide(m, now_ms_provider=clock.read, max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert d["status"] == fwd.WINDOW_NOT_STARTED
    assert log == []                                  # zero HL/CLOB calls before the gate
    assert d["window_start_in_future"] == 1
    assert d["status"] != pp.PAPER_OPEN               # structurally cannot open
    assert d.get("selected_side") is None             # never reached edge evaluation


# --- equality boundary window_start_ms == probe_now_ms remains ELIGIBLE ---
def test_equality_boundary_window_eligible(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    clock = _MonoClock(start=NOW_MS - 1)              # first read (probe_now) == NOW_MS
    log = []
    m = _market(market_end_ts=NOW_MS // 1000 + fwd.TARGET_INTERVAL_S)
    assert _wsm(m) == NOW_MS                          # window_start_ms == probe_now_ms
    pf, sig = _ordered_hl(clock, log, strike_ts=_wsm(m))
    client = _quote_client(clock, log, {"tokUp": "0.40", "tokDown": "0.55"})
    d = fwd.capture_and_decide(m, now_ms_provider=clock.read, max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert d["status"] != fwd.WINDOW_NOT_STARTED      # boundary is eligible
    assert log != []                                  # proceeded to acquisition


# --- mandatory strike no-lookahead guard: reject BEFORE any CLOB acquisition ---
def test_strike_feed_ts_future_rejected_before_clob(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    clock, log, m = _MonoClock(), [], _market()
    pf, sig = _ordered_hl(clock, log, strike_ts=_wsm(m), strike_feed_offset_ms=1)  # feed_ts > wsm
    client = _quote_client(clock, log, {"tokUp": "0.40", "tokDown": "0.55"})
    d = fwd.capture_and_decide(m, now_ms_provider=clock.read, max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    assert d["status"] == pp.FUTURE_TIMESTAMP_REJECTED
    assert d["field"] == "hl_strike_feed_ts"
    assert all(k != "CLOB" for (k, _) in log)         # rejected before CLOB books
    assert d["status"] != pp.PAPER_OPEN


# --- decision_ts is final; every persisted evidence timestamp <= decision_ts ---
def test_decision_ts_is_final_all_evidence_not_after(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    clock, log, m = _MonoClock(), [], _market()
    pf, sig = _ordered_hl(clock, log, strike_ts=_wsm(m))
    client = _quote_client(clock, log, {"tokUp": "0.40", "tokDown": "0.55"})
    d = fwd.capture_and_decide(m, now_ms_provider=clock.read, max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    dts = d["paper_decision_ts"]
    st = _json.loads(d["stage_timings_json"])
    for stage, t in st.items():
        assert t["start_ts"] <= dts and t["completed_ts"] <= dts, stage
    for key in ("yes_capture_completed_ms", "no_capture_completed_ms", "yes_quote_ts_ms",
                "no_quote_ts_ms", "hl_capture_started_ms", "hl_capture_completed_ms",
                "probe_now_ms"):
        if d.get(key) is not None:
            assert d[key] <= dts, key


# --- eligible stage timings present & correct; TOTAL brackets first stage -> decision ---
def test_eligible_stage_timings_and_total(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    clock, log, m = _MonoClock(), [], _market()
    pf, sig = _ordered_hl(clock, log, strike_ts=_wsm(m))
    client = _quote_client(clock, log, {"tokUp": "0.40", "tokDown": "0.55"})
    d = fwd.capture_and_decide(m, now_ms_provider=clock.read, max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    st = _json.loads(d["stage_timings_json"])
    for stage in ("OUTCOME_BINDING", "HL_WINDOW_STRIKE", "HL_SIGMA", "HL_CURRENT_PRICE",
                  "YES_CLOB_FETCH", "NO_CLOB_FETCH", "MODEL_CALCULATION",
                  "TOTAL_CAPTURE_TO_DECISION"):
        assert stage in st, stage
        assert st[stage]["duration_ms"] == st[stage]["completed_ts"] - st[stage]["start_ts"] >= 0
    total = st["TOTAL_CAPTURE_TO_DECISION"]
    assert total["completed_ts"] == d["paper_decision_ts"]
    assert total["start_ts"] == st["OUTCOME_BINDING"]["start_ts"]   # first stage anchors TOTAL


# --- reorder preserves economics EXACTLY (golden via the unchanged economic functions) ---
def test_reorder_preserves_economics_exactly(monkeypatch):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    clock, log, m = _MonoClock(), [], _market()
    P_NOW, STRIKE, SIGMA = Decimal("60000"), Decimal("59000"), 0.8
    pf, sig = _ordered_hl(clock, log, strike_ts=_wsm(m), p_now=str(P_NOW), strike=str(STRIKE),
                          sigma=SIGMA)
    client = _quote_client(clock, log, {"tokUp": "0.40", "tokDown": "0.55"})
    d = fwd.capture_and_decide(m, now_ms_provider=clock.read, max_skew_ms=5000,
                               book_fetch_client=client, hl_price_feedts=pf, hl_sigma_annual=sig)
    # golden expectation: identical inputs through the COMMITTED, unmodified economic path.
    # clock stays within one wall-second, so tte_s is deterministic.
    tte_s = m["market_end_ts"] - (NOW_MS // 1000)
    fair_yes = fwd.gm.fair_yes_gbm(P_NOW, STRIKE, SIGMA, Decimal(tte_s) / fwd.gm.SECONDS_PER_YEAR)
    exp_yes = {"asks": [["0.40", "1000"]], "quote_ts_ms": NOW_MS,
               "capture_started_ms": NOW_MS, "capture_completed_ms": NOW_MS}
    exp_no = {"asks": [["0.55", "1000"]], "quote_ts_ms": NOW_MS,
              "capture_started_ms": NOW_MS, "capture_completed_ms": NOW_MS}
    golden = pp.build_paper_decision(market=m, yes_book=exp_yes, no_book=exp_no, fair_yes=fair_yes,
                                     feed_ts=NOW_MS - 30_000, tte_s=tte_s, max_skew_ms=5000,
                                     decision_ts=NOW_MS + 100, hl_capture_started_ms=NOW_MS,
                                     hl_capture_completed_ms=NOW_MS + 1)
    for field in ("fair_yes", "selected_side", "yes_net_edge", "no_net_edge",
                  "yes_exec_ask_vwap", "no_exec_ask_vwap", "selected_entry_notional"):
        assert d[field] == golden[field], field


# --- run(): persists a current (eligible) AND a future (WINDOW_NOT_STARTED) observation ---
def _gamma_from_slug(slug):
    import datetime as _dt
    epoch = int(slug.rsplit("-", 1)[1])
    end_iso = _dt.datetime.fromtimestamp(epoch + fwd.TARGET_INTERVAL_S,
                                         _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"conditionId": f"0xcid-{epoch}", "slug": slug, "outcomes": ["Up", "Down"],
            "clobTokenIds": ["tokUp", "tokDown"], "endDate": end_iso,
            "feesEnabled": True, "feeSchedule": {"exponent": 1, "rate": 0.07, "takerOnly": True}}


def test_run_persists_current_and_future_window(monkeypatch, tmp_path, capsys):
    _armed_g8_env(monkeypatch, max_obs="2")
    clock, log = _MonoClock(), []

    def pg(url, params=None):
        if url == fwd.runner.GAMMA_MARKETS:
            return [_gamma_from_slug(params["slug"])]
        log.append(("CLOB", params["token_id"]))
        return {"asks": [{"price": "0.99", "size": "1000"}], "bids": [], "timestamp": clock.now}

    def pf(coin, ts_ms):
        if ts_ms < NOW_MS - 1000:                     # window-open strike query (past)
            log.append(("HL_STRIKE", ts_ms))
            return Decimal("59000"), ts_ms
        log.append(("HL_PRICE", ts_ms))
        return Decimal("60000"), ts_ms - 30_000

    def sig(coin, now_ms):
        log.append(("HL_SIGMA", now_ms))
        return 0.8

    db = str(tmp_path / "run_cur_fut.sqlite3")
    fwd.run(db, now_ms_provider=clock.read, monotonic_provider=lambda: 0.0,
            public_get=pg, hl_price_feedts=pf, hl_sigma_annual=sig)
    import sqlite3
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT status, window_start_in_future FROM gateg8_paper_ledger ORDER BY id").fetchall()
    conn.close()
    assert len(rows) == 2
    statuses = [r[0] for r in rows]
    fut = [r for r in rows if r[0] == fwd.WINDOW_NOT_STARTED]
    assert len(fut) == 1 and fut[0][1] == 1           # exactly one future row, flagged
    assert any(s != fwd.WINDOW_NOT_STARTED for s in statuses)   # eligible row reached capture
    err = capsys.readouterr().err
    assert err.count("[g8obs]") == 2                  # exactly one log line per observation
