"""tests/test_golden_sample_orchestrator.py — strict offline TDD, capture-only Golden Sample.

Fully offline: injected async fetchers, injected monotonic-ns clock, injected UTC clock. No network,
no real clock, no assembler/calculator. Proves concurrent single-shot capture, deterministic
fail-closed precedence, integer-only timing/threshold math, Decimal preservation, capture-only output.

First RED: module tools.golden_sample_orchestrator does not exist -> ImportError.
"""
import asyncio
import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.golden_sample_orchestrator import orchestrate_golden_sample

_YES_TID = "YESTOK"
_NO_TID = "NOTOK"
_ASSET = "BTC"
_YES_BOOK = {"bids": [{"price": Decimal("0.81"), "size": Decimal("50")}],
             "asks": [{"price": Decimal("0.83"), "size": Decimal("50")}]}
_NO_BOOK = {"bids": [{"price": Decimal("0.17"), "size": Decimal("50")}],
            "asks": [{"price": Decimal("0.19"), "size": Decimal("50")}]}

_TOP_KEYS = {"schema_version", "onboarding", "yes_book", "no_book", "hl_reference",
             "timing", "capture_provenance", "max_skew_ms", "markers", "status", "error_code"}


# --- fakes -----------------------------------------------------------------

class _Carrier:
    def __init__(self, token_id, parsed_safe_book, error_code=None, http_status=200,
                 reject_reason=None, fetch_span_ms=5):
        self.token_id = token_id
        self.parsed_safe_book = parsed_safe_book
        self.error_code = error_code
        self.http_status = http_status
        self.reject_reason = reject_reason
        self.fetch_span_ms = fetch_span_ms
        self.fetch_started_at = None
        self.fetch_completed_at = None


def _book_fetcher(carrier, *, counter=None, exc=None):
    async def f(token_id):
        if counter is not None:
            counter.append(token_id)
        if exc is not None:
            raise exc
        return carrier
    return f


def _hl_record(asset=_ASSET, price="60279.5", **over):
    r = {"asset": asset, "reference_price": Decimal(price),
         "status": "VENUE_REFERENCE_OK", "error_code": None,
         "reference_source": "hyperliquid_all_mids_perp"}
    r.update(over)
    return r


def _hl_fetcher(record, *, counter=None, exc=None):
    async def f(asset):
        if counter is not None:
            counter.append(asset)
        if exc is not None:
            raise exc
        return record
    return f


def _mono(seq):
    it = iter(seq)
    return lambda: next(it)


def _utc(val="2026-06-27T04:00:01Z"):
    return lambda: val


def _onb(**over):
    gamma = {"condition_id": "0xCID", "outcomes": ["Up", "Down"],
             "clob_token_ids": [_YES_TID, _NO_TID],
             "outcome_token_map": [{"outcome": "Up", "token_id": _YES_TID},
                                   {"outcome": "Down", "token_id": _NO_TID}],
             "event_start_time_ms": 1782532800000, "end_date_ms": 1782547200000,
             "status": "VENUE_METADATA_OK", "error_code": None}
    binance = {"symbol": "BTCUSDT", "interval": "4h", "event_start_time_ms": 1782532800000,
               "returned_open_time_ms": 1782532800000, "strike_price": Decimal("60305.73"),
               "strike_source": "binance_klines_candle_open", "status": "VENUE_STRIKE_OK",
               "error_code": None}
    rec = {"slug": "btc-updown-4h", "condition_id": "0xCID", "asset": _ASSET, "interval": "4h",
           "gamma": gamma, "binance": binance, "classification": {"status": "CACHE_READY"},
           "onboarding_status": "ONBOARDING_OK", "onboarding_error_code": None}
    rec.update(over)
    return rec


def _run(*, onboarding_record=None, yes=None, no=None, hl=None,
         mono=None, utc=None, max_skew_ms=1000):
    onboarding_record = _onb() if onboarding_record is None else onboarding_record
    yes = _book_fetcher(_Carrier(_YES_TID, _YES_BOOK)) if yes is None else yes
    no = _book_fetcher(_Carrier(_NO_TID, _NO_BOOK)) if no is None else no
    hl = _hl_fetcher(_hl_record()) if hl is None else hl
    mono = _mono([1000, 1500, 1100, 1700, 1200, 1600]) if mono is None else mono
    utc = _utc() if utc is None else utc
    return asyncio.run(orchestrate_golden_sample(
        onboarding_record=onboarding_record, yes_book_fetcher=yes, no_book_fetcher=no,
        hl_reference_fetcher=hl, monotonic_ns_fn=mono, utc_now_fn=utc, max_skew_ms=max_skew_ms))


def _has_float(obj):
    if isinstance(obj, bool):
        return False
    if isinstance(obj, float):
        return True
    if isinstance(obj, dict):
        return any(_has_float(k) or _has_float(v) for k, v in obj.items())
    if isinstance(obj, (list, tuple, set)):
        return any(_has_float(x) for x in obj)
    return False


# ===========================================================================
# happy path
# ===========================================================================

def test_golden_sample_ok():
    rec = _run()
    assert rec["status"] == "GOLDEN_SAMPLE_OK"
    assert rec["error_code"] is None
    assert set(rec.keys()) == _TOP_KEYS
    assert rec["yes_book"]["latency_ns"] == 500
    assert rec["no_book"]["latency_ns"] == 600
    assert rec["hl_reference"]["latency_ns"] == 400
    assert rec["timing"]["capture_span_ns"] == 700
    assert rec["timing"]["completion_skew_ns"] == 200
    assert rec["timing"]["threshold_ns"] == 1_000_000_000
    assert rec["hl_reference"]["evidence"]["reference_price"] == Decimal("60279.5")
    assert "client_completion_skew_not_venue_event_time" in rec["markers"]
    assert "hyperliquid_perp_reference_basis_risk" in rec["markers"]


def test_ms_display_fixed_point_strings():
    rec = _run()
    assert rec["yes_book"]["latency_ms"] == "0.0005"
    assert rec["timing"]["capture_span_ms"] == "0.0007"
    assert isinstance(rec["timing"]["completion_skew_ms"], str)


def test_no_float_anywhere_in_record():
    assert _has_float(_run()) is False


def test_ok_and_invalid_share_top_key_set():
    ok = _run()
    inv = _run(hl=_hl_fetcher(_hl_record(status="VENUE_REFERENCE_INVALID", error_code="hl_fetch_error",
                                         reference_price=None)))
    assert set(ok.keys()) == set(inv.keys()) == _TOP_KEYS


def test_three_leg_slots_always_present():
    rec = _run(onboarding_record=_onb(onboarding_status="ONBOARDING_INVALID"))
    for k in ("yes_book", "no_book", "hl_reference", "timing"):
        assert k in rec   # present (None on pre-fetch invalid)


# ===========================================================================
# input / onboarding validation — zero fetcher calls
# ===========================================================================

def test_onboarding_not_ok_zero_calls():
    yc, nc, hc = [], [], []
    rec = _run(onboarding_record=_onb(onboarding_status="ONBOARDING_INVALID"),
               yes=_book_fetcher(_Carrier(_YES_TID, _YES_BOOK), counter=yc),
               no=_book_fetcher(_Carrier(_NO_TID, _NO_BOOK), counter=nc),
               hl=_hl_fetcher(_hl_record(), counter=hc))
    assert rec["status"] == "GOLDEN_SAMPLE_INVALID"
    assert rec["error_code"] == "onboarding_invalid"
    assert yc == [] and nc == [] and hc == []
    assert rec["yes_book"] is None and rec["timing"] is None


def test_classification_not_cache_ready():
    rec = _run(onboarding_record=_onb(classification={"status": "OBSERVE_ONLY"}))
    assert rec["error_code"] == "onboarding_invalid"


@pytest.mark.parametrize("bad", [0, -1, True, 1.0, Decimal("1"), "1", None])
def test_max_skew_ms_must_be_positive_int_zero_calls(bad):
    yc = []
    rec = _run(max_skew_ms=bad, yes=_book_fetcher(_Carrier(_YES_TID, _YES_BOOK), counter=yc))
    assert rec["status"] == "GOLDEN_SAMPLE_INVALID"
    assert rec["error_code"] == "input_invalid"
    assert yc == []


def test_non_callable_fetcher_zero_effect():
    rec = _run(hl="not-callable")
    assert rec["error_code"] == "input_invalid"


# ===========================================================================
# exactly one call per fetcher, no retry
# ===========================================================================

def test_exactly_one_call_per_fetcher():
    yc, nc, hc = [], [], []
    _run(yes=_book_fetcher(_Carrier(_YES_TID, _YES_BOOK), counter=yc),
         no=_book_fetcher(_Carrier(_NO_TID, _NO_BOOK), counter=nc),
         hl=_hl_fetcher(_hl_record(), counter=hc))
    assert yc == [_YES_TID] and nc == [_NO_TID] and hc == [_ASSET]


def test_no_retry_on_leg_exception():
    hc = []
    rec = _run(hl=_hl_fetcher(_hl_record(), counter=hc, exc=TimeoutError("boom")))
    assert rec["error_code"] == "hl_reference_invalid"
    assert hc == [_ASSET]                       # called once, no retry
    assert rec["hl_reference"]["exception_repr"] is not None


# ===========================================================================
# concurrency: all three start before any completion (barrier proof)
# ===========================================================================

def test_concurrent_start_all_three():
    async def scenario():
        started = []
        all_started = asyncio.Event()

        def make(name, ret):
            async def f(arg):
                started.append(name)
                if len(started) == 3:
                    all_started.set()
                await all_started.wait()
                return ret
            return f

        rec = await orchestrate_golden_sample(
            onboarding_record=_onb(),
            yes_book_fetcher=make("y", _Carrier(_YES_TID, _YES_BOOK)),
            no_book_fetcher=make("n", _Carrier(_NO_TID, _NO_BOOK)),
            hl_reference_fetcher=make("h", _hl_record()),
            monotonic_ns_fn=lambda: 0, utc_now_fn=_utc(), max_skew_ms=1000)
        return started, rec

    started, rec = asyncio.run(asyncio.wait_for(scenario(), 5))
    assert len(started) == 3                     # all three started (would deadlock if sequential)
    assert rec["status"] == "GOLDEN_SAMPLE_OK"


# ===========================================================================
# external cancellation must propagate (not become invalid carrier)
# ===========================================================================

def test_external_cancellation_propagates():
    async def scenario():
        async def slow(arg):
            await asyncio.sleep(10)

        task = asyncio.ensure_future(orchestrate_golden_sample(
            onboarding_record=_onb(), yes_book_fetcher=slow,
            no_book_fetcher=_book_fetcher(_Carrier(_NO_TID, _NO_BOOK)),
            hl_reference_fetcher=_hl_fetcher(_hl_record()),
            monotonic_ns_fn=lambda: 0, utc_now_fn=_utc(), max_skew_ms=1000))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


# ===========================================================================
# leg invalidity + deterministic precedence
# ===========================================================================

def test_yes_book_invalid():
    rec = _run(yes=_book_fetcher(_Carrier(_YES_TID, None, error_code="non_200")))
    assert rec["error_code"] == "yes_book_invalid"


def test_no_book_invalid():
    rec = _run(no=_book_fetcher(_Carrier(_NO_TID, None, error_code="timeout")))
    assert rec["error_code"] == "no_book_invalid"


def test_hl_invalid_status():
    rec = _run(hl=_hl_fetcher(_hl_record(status="VENUE_REFERENCE_INVALID",
                                         error_code="hl_bad_price", reference_price=None)))
    assert rec["error_code"] == "hl_reference_invalid"


def test_hl_raised_exception_is_invalid():
    rec = _run(hl=_hl_fetcher(_hl_record(), exc=ValueError("x")))
    assert rec["error_code"] == "hl_reference_invalid"


def test_precedence_yes_beats_no_and_hl():
    rec = _run(yes=_book_fetcher(_Carrier(_YES_TID, None, error_code="non_200")),
               no=_book_fetcher(_Carrier(_NO_TID, None, error_code="timeout")),
               hl=_hl_fetcher(_hl_record(), exc=ValueError("x")))
    assert rec["error_code"] == "yes_book_invalid"


def test_precedence_book_invalid_beats_clock_invalid():
    rec = _run(yes=_book_fetcher(_Carrier(_YES_TID, None, error_code="non_200")),
               mono=_mono([5, 4, 0, 0, 0, 0]))  # regression on yes, but book invalid wins
    assert rec["error_code"] == "yes_book_invalid"


def test_partial_evidence_retained_on_invalid():
    rec = _run(hl=_hl_fetcher(_hl_record(status="VENUE_REFERENCE_INVALID",
                                         error_code="hl_fetch_error", reference_price=None)))
    assert rec["error_code"] == "hl_reference_invalid"
    assert rec["yes_book"]["evidence"] is not None      # valid book evidence preserved
    assert rec["no_book"]["evidence"] is not None
    assert rec["timing"]["capture_span_ns"] is not None  # timing evidence retained


# ===========================================================================
# identity / strike-expiry / reference-semantic mismatches
# ===========================================================================

def test_identity_token_mismatch():
    rec = _run(yes=_book_fetcher(_Carrier("WRONGTOK", _YES_BOOK)))
    assert rec["error_code"] == "identity_token_mismatch"


def test_strike_expiry_mismatch_event_start_disagree():
    onb = _onb()
    onb["binance"] = dict(onb["binance"], event_start_time_ms=999)  # != gamma event start
    rec = _run(onboarding_record=onb)
    assert rec["error_code"] == "strike_expiry_mismatch"


def test_reference_semantic_wrong_asset():
    rec = _run(hl=_hl_fetcher(_hl_record(asset="ETH")))
    assert rec["error_code"] == "reference_semantic_mismatch"


def test_reference_semantic_wrong_source():
    rec = _run(hl=_hl_fetcher(_hl_record(reference_source="binance")))
    assert rec["error_code"] == "reference_semantic_mismatch"


def test_reference_semantic_nonpositive_price():
    rec = _run(hl=_hl_fetcher({"asset": _ASSET, "reference_price": Decimal("0"),
                               "status": "VENUE_REFERENCE_OK", "error_code": None,
                               "reference_source": "hyperliquid_all_mids_perp"}))
    assert rec["error_code"] == "reference_semantic_mismatch"


# ===========================================================================
# timing clock validity + skew threshold
# ===========================================================================

def test_clock_regression_invalid():
    rec = _run(mono=_mono([2000, 1000, 0, 0, 0, 0]))   # yes complete < start
    assert rec["error_code"] == "timing_clock_invalid"


def test_clock_non_int_invalid():
    rec = _run(mono=_mono([0, 5, 0, 5, 0, "x"]))
    assert rec["error_code"] == "timing_clock_invalid"


def test_clock_negative_invalid():
    rec = _run(mono=_mono([-1, 5, 0, 5, 0, 5]))
    assert rec["error_code"] == "timing_clock_invalid"


def test_skew_equality_accepted():
    # span = 1_000_000, skew = 1_000_000, threshold(max_skew_ms=1)=1_000_000 -> accepted
    rec = _run(mono=_mono([0, 1_000_000, 0, 0, 0, 0]), max_skew_ms=1)
    assert rec["status"] == "GOLDEN_SAMPLE_OK"


def test_one_ns_above_threshold_rejected():
    rec = _run(mono=_mono([0, 1_000_001, 0, 0, 0, 0]), max_skew_ms=1)
    assert rec["error_code"] == "timing_skew_violation"


def test_capture_span_violation_skew_ok():
    # completes equal (skew 0) but span large
    rec = _run(mono=_mono([0, 1_100_000, 1_050_000, 1_100_000, 1_050_000, 1_100_000]),
               max_skew_ms=1)
    assert rec["timing"]["completion_skew_ns"] == 0
    assert rec["timing"]["capture_span_ns"] == 1_100_000
    assert rec["error_code"] == "timing_skew_violation"


# ===========================================================================
# UTC receipt provenance per leg + courier wall-clock isolation
# ===========================================================================

def test_separate_utc_receipt_per_leg():
    vals = iter(["u_yes", "u_no", "u_hl"])
    rec = _run(utc=lambda: next(vals))
    received = {rec["yes_book"]["client_received_at_utc"],
                rec["no_book"]["client_received_at_utc"],
                rec["hl_reference"]["client_received_at_utc"]}
    assert received == {"u_yes", "u_no", "u_hl"}


def test_courier_wall_clock_does_not_control_skew_gate():
    # carriers claim huge fetch_span_ms, but outer monotonic envelope is tight -> still OK
    yc = _Carrier(_YES_TID, _YES_BOOK, fetch_span_ms=999_999)
    nc = _Carrier(_NO_TID, _NO_BOOK, fetch_span_ms=999_999)
    rec = _run(yes=_book_fetcher(yc), no=_book_fetcher(nc),
               mono=_mono([0, 10, 0, 10, 0, 10]), max_skew_ms=1)
    assert rec["status"] == "GOLDEN_SAMPLE_OK"


# ===========================================================================
# capture-only: no assembler/calculator surfaces, no spot_reference
# ===========================================================================

def test_capture_only_no_calculator_surfaces():
    import tools.golden_sample_orchestrator as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        raw = fh.read()
    low = raw.lower()
    # case-insensitive bans
    for term in ("miami_live_snapshot", "expiry_snipe_calculator", "miami_oneshot_runner",
                 "miami_oneshot_live", "spot", "truth", "oracle", "settlement",
                 "calculator", "assembler", "spot_reference",
                 "order", "fill", "trade", "buy", "sell", "stake", "wallet", "signing",
                 "scanner", "persistence", "csv", "while", "retry", "float("):
        assert term not in low, f"forbidden surface {term!r} present"
    # case-sensitive: lowercase 'cache' forbidden; the uppercase onboarder status
    # CACHE_READY (which the orchestrator must compare against) is permitted
    assert "cache" not in raw, "lowercase behavioral 'cache' present"


def test_record_has_no_calculator_inputs_and_no_spot_field():
    rec = _run()
    flat = str(rec)
    assert "spot_reference" not in flat
    assert "calculator_input_spot_reference_is_perp_reference_alias" not in rec["markers"]


# ===========================================================================
# ownership isolation (OK): caller mutation cannot reach the returned sample
# ===========================================================================

def _fresh_book(price="0.81"):
    return {"bids": [{"price": Decimal(price), "size": Decimal("50")}],
            "asks": [{"price": Decimal("0.83"), "size": Decimal("50")}]}


def test_mutate_input_onboarding_after_return_does_not_change_sample():
    onb = _onb()
    rec = _run(onboarding_record=onb)
    onb["gamma"]["outcome_token_map"][0]["token_id"] = "HACKED"
    onb["asset"] = "HACK"
    assert rec["onboarding"]["gamma"]["outcome_token_map"][0]["token_id"] == _YES_TID
    assert rec["onboarding"]["asset"] == _ASSET


def test_mutate_input_yes_book_after_return():
    book = _fresh_book()
    rec = _run(yes=_book_fetcher(_Carrier(_YES_TID, book)))
    book["bids"][0]["price"] = Decimal("0.99")
    assert rec["yes_book"]["evidence"]["parsed_safe_book"]["bids"][0]["price"] == Decimal("0.81")


def test_mutate_input_no_book_after_return():
    book = _fresh_book("0.17")
    rec = _run(no=_book_fetcher(_Carrier(_NO_TID, book)))
    book["bids"][0]["price"] = Decimal("0.99")
    assert rec["no_book"]["evidence"]["parsed_safe_book"]["bids"][0]["price"] == Decimal("0.17")


def test_mutate_input_hl_record_after_return():
    hlrec = _hl_record()
    rec = _run(hl=_hl_fetcher(hlrec))
    hlrec["reference_price"] = Decimal("1")
    assert rec["hl_reference"]["evidence"]["reference_price"] == Decimal("60279.5")


def test_mutate_returned_onboarding_does_not_change_input():
    onb = _onb()
    rec = _run(onboarding_record=onb)
    rec["onboarding"]["asset"] = "HACK"
    rec["onboarding"]["gamma"]["outcome_token_map"][0]["token_id"] = "HACK"
    assert onb["asset"] == _ASSET
    assert onb["gamma"]["outcome_token_map"][0]["token_id"] == _YES_TID


def test_mutate_returned_book_evidence_does_not_change_carrier():
    book = _fresh_book()
    carrier = _Carrier(_YES_TID, book)
    rec = _run(yes=_book_fetcher(carrier))
    rec["yes_book"]["evidence"]["parsed_safe_book"]["bids"][0]["price"] = Decimal("9")
    assert book["bids"][0]["price"] == Decimal("0.81")
    assert carrier.parsed_safe_book["bids"][0]["price"] == Decimal("0.81")


def test_mutate_returned_hl_evidence_does_not_change_courier():
    hlrec = _hl_record()
    rec = _run(hl=_hl_fetcher(hlrec))
    rec["hl_reference"]["evidence"]["reference_price"] = Decimal("9")
    assert hlrec["reference_price"] == Decimal("60279.5")


def test_nested_containers_not_identical_by_identity():
    onb = _onb()
    book = _fresh_book()
    carrier = _Carrier(_YES_TID, book)
    hlrec = _hl_record()
    rec = _run(onboarding_record=onb, yes=_book_fetcher(carrier), hl=_hl_fetcher(hlrec))
    assert rec["onboarding"] is not onb
    assert rec["onboarding"]["gamma"] is not onb["gamma"]
    assert rec["yes_book"]["evidence"]["parsed_safe_book"] is not book
    assert rec["hl_reference"]["evidence"] is not hlrec


# ===========================================================================
# partial / pre-fetch INVALID isolation
# ===========================================================================

def test_partial_invalid_retained_evidence_isolated():
    book = _fresh_book()
    rec = _run(yes=_book_fetcher(_Carrier(_YES_TID, book)),
               hl=_hl_fetcher(_hl_record(status="VENUE_REFERENCE_INVALID",
                                         error_code="hl_fetch_error", reference_price=None)))
    assert rec["error_code"] == "hl_reference_invalid"
    book["bids"][0]["price"] = Decimal("9")
    assert rec["yes_book"]["evidence"]["parsed_safe_book"]["bids"][0]["price"] == Decimal("0.81")
    assert rec["yes_book"]["evidence"]["parsed_safe_book"] is not book


def test_failed_leg_diagnostic_is_plain_string():
    rec = _run(hl=_hl_fetcher(_hl_record(), exc=ValueError("boom")))
    assert rec["error_code"] == "hl_reference_invalid"
    assert isinstance(rec["hl_reference"]["exception_repr"], str)
    assert rec["hl_reference"]["evidence"] is None
    _assert_plain_tree(rec["hl_reference"])


def test_prefetch_invalid_onboarding_isolated_zero_calls():
    onb = _onb(onboarding_status="ONBOARDING_INVALID")
    yc = []
    rec = _run(onboarding_record=onb,
               yes=_book_fetcher(_Carrier(_YES_TID, _YES_BOOK), counter=yc))
    assert rec["error_code"] == "onboarding_invalid"
    assert yc == []
    assert rec["onboarding"] is None or rec["onboarding"] is not onb


# ===========================================================================
# strict plain-tree: unsupported nested content maps to *_invalid
# ===========================================================================

def _assert_plain_tree(node, path="root"):
    if node is None:
        return
    t = type(node)
    if t is bool:
        raise AssertionError(f"bool at {path}")
    if t in (int, str) or t is Decimal:
        return
    if t is dict:
        for k, v in node.items():
            assert type(k) is str, f"non-str key at {path}"
            _assert_plain_tree(v, f"{path}.{k}")
        return
    if t in (list, tuple):
        for i, v in enumerate(node):
            _assert_plain_tree(v, f"{path}[{i}]")
        return
    raise AssertionError(f"unsupported type {t.__name__} at {path}")


def test_returned_ok_record_is_strict_plain_tree():
    rec = _run()
    _assert_plain_tree(rec)
    assert isinstance(rec["hl_reference"]["evidence"]["reference_price"], Decimal)
    assert type(rec["yes_book"]["start_mono_ns"]) is int
    assert isinstance(rec["yes_book"]["client_received_at_utc"], str)
    assert rec["onboarding"]["binance"]["strike_price"] == Decimal("60305.73")


def test_unsupported_onboarding_datetime_invalid_zero_calls():
    import datetime as _dt
    onb = _onb()
    onb["gamma"]["weird"] = _dt.datetime(2026, 6, 27)
    yc = []
    rec = _run(onboarding_record=onb,
               yes=_book_fetcher(_Carrier(_YES_TID, _YES_BOOK), counter=yc))
    assert rec["error_code"] == "onboarding_invalid"
    assert yc == []


def test_unsupported_onboarding_bool_invalid():
    onb = _onb()
    onb["gamma"]["flag"] = True
    rec = _run(onboarding_record=onb)
    assert rec["error_code"] == "onboarding_invalid"


def test_unsupported_yes_evidence_float_price():
    bad = {"bids": [{"price": 0.81, "size": Decimal("50")}],
           "asks": [{"price": Decimal("0.83"), "size": Decimal("50")}]}
    rec = _run(yes=_book_fetcher(_Carrier(_YES_TID, bad)))
    assert rec["error_code"] == "yes_book_invalid"


def test_unsupported_no_evidence_set():
    bad = {"bids": {Decimal("1")}, "asks": [{"price": Decimal("0.19"), "size": Decimal("50")}]}
    rec = _run(no=_book_fetcher(_Carrier(_NO_TID, bad)))
    assert rec["error_code"] == "no_book_invalid"


def test_unsupported_book_nonstr_key():
    bad = {"bids": [{1: Decimal("0.81")}], "asks": [{"price": Decimal("0.83")}]}
    rec = _run(yes=_book_fetcher(_Carrier(_YES_TID, bad)))
    assert rec["error_code"] == "yes_book_invalid"


def test_unsupported_hl_evidence_float_price():
    rec = _run(hl=_hl_fetcher({"asset": _ASSET, "reference_price": 60279.5,
                               "status": "VENUE_REFERENCE_OK", "error_code": None,
                               "reference_source": "hyperliquid_all_mids_perp"}))
    assert rec["error_code"] == "hl_reference_invalid"


def test_decimal_and_scalars_preserved():
    rec = _run()
    assert isinstance(rec["hl_reference"]["evidence"]["reference_price"], Decimal)
    assert type(rec["max_skew_ms"]) is int
    assert rec["error_code"] is None
    assert isinstance(rec["status"], str)
