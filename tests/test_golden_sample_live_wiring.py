"""tests/test_golden_sample_live_wiring.py — TDD for the capture-only Golden Sample live wiring.

run_golden_sample_live is a thin async library seam. It adapts two UNCHANGED single-shot couriers
(data.pm_clob_fetcher.fetch_clob_book over the PM CLOB /book endpoint, and
data.hl_reference_price.fetch_hl_reference_price over the Hyperliquid allMids document) to the
single-positional-argument fetcher contract of the UNCHANGED capture-only
tools.golden_sample_orchestrator.orchestrate_golden_sample, and hands the orchestrator one
caller-provided prevalidated onboarding_record in-process.

The wiring owns ONLY: per-leg deadline validation, the shared PM session lifetime (async with), and
three thin single-argument closure adapters (YES, NO, HL). All concurrency, deterministic precedence,
partial-evidence joining, and timing remain inside the orchestrator. No network, no real clock: every
client and clock is injected here.

First RED: module tools.golden_sample_live_wiring does not exist -> ImportError.
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.golden_sample_live_wiring import run_golden_sample_live, serialize_golden_sample

_FIXED_UTC = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
_HL_SOURCE = "hyperliquid_all_mids_perp"


# ---------------------------------------------------------------------------
# injected fakes (no real network, no real clock)
# ---------------------------------------------------------------------------

class _ExternalCancellation(BaseException):
    """Stand-in for external cancellation: a BaseException the orchestrator must not swallow."""


class _FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    async def text(self):
        return self._body


class _FakeHttpClient:
    """Shared PM client: records each .get; serves a 200 book body per token_id."""

    def __init__(self, body_by_token, *, raise_exc=None):
        self.body_by_token = body_by_token
        self.raise_exc = raise_exc
        self.calls = []

    async def get(self, url, *, params=None, timeout=None):
        self.calls.append({"url": url, "params": dict(params or {}), "timeout": timeout})
        if self.raise_exc is not None:
            raise self.raise_exc
        token = params["token_id"]
        return _FakeResponse(200, self.body_by_token[token])


class _FakePmSession:
    """Async context manager that yields the shared PM client and counts enter/exit."""

    def __init__(self, http_client):
        self.http_client = http_client
        self.entered = 0
        self.exited = 0

    async def __aenter__(self):
        self.entered += 1
        return self.http_client

    async def __aexit__(self, *exc):
        self.exited += 1
        return False


def _hl_factory(payload, *, calls_sink, raise_exc=None):
    """Return an HL client factory(timeout_s) -> async callable(url, *, json_body)."""
    def factory(timeout_s):
        calls_sink.append(("factory", timeout_s))

        async def client(url, *, json_body):
            calls_sink.append(("call", url, json_body))
            if raise_exc is not None:
                raise raise_exc
            return payload
        return client
    return factory


def _mono_counter():
    """Strictly-increasing integer monotonic clock; tiny values stay well under any threshold."""
    state = {"v": 0}

    def f():
        state["v"] += 1
        return state["v"]
    return f


def _onboarding_record(*, yes_tid="YES_TOKEN", no_tid="NO_TOKEN", asset="BTC",
                       event_ms=1000, end_ms=2000, strike="60000.0"):
    return {
        "slug": "demo-slug",
        "condition_id": "0xcond",
        "asset": asset,
        "interval": "1h",
        "gamma": {
            "outcome_token_map": [{"token_id": yes_tid}, {"token_id": no_tid}],
            "event_start_time_ms": event_ms,
            "end_date_ms": end_ms,
        },
        "binance": {
            "event_start_time_ms": event_ms,
            "strike_price": Decimal(strike),
        },
        "classification": {"status": "CACHE_READY"},
        "onboarding_status": "ONBOARDING_OK",
        "onboarding_error_code": None,
    }


# numeric (unquoted) JSON so parse_float/parse_int=Decimal yields Decimal book levels
_YES_BODY = '{"asks": [[0.51, 10]], "bids": [[0.49, 20]]}'
_NO_BODY = '{"asks": [[0.50, 11]], "bids": [[0.48, 21]]}'
_HL_PAYLOAD = {"BTC": "60279.5", "ETH": "3000.0"}


def _run(*, record=None, http_client=None, session=None, hl_factory=None, hl_calls=None,
         pm_base_url="https://clob.example.com", hl_base_url="https://hl.example.com",
         pm_timeout_s=1.5, hl_timeout_s=2.0, max_skew_ms=10_000,
         monotonic_ns_fn=None, utc_now_fn=None):
    record = record if record is not None else _onboarding_record()
    if http_client is None:
        http_client = _FakeHttpClient({"YES_TOKEN": _YES_BODY, "NO_TOKEN": _NO_BODY})
    if session is None:
        session = _FakePmSession(http_client)
    if hl_factory is None:
        hl_calls = hl_calls if hl_calls is not None else []
        hl_factory = _hl_factory(_HL_PAYLOAD, calls_sink=hl_calls)
    out = asyncio.run(run_golden_sample_live(
        onboarding_record=record,
        pm_session=session,
        hl_client_factory=hl_factory,
        pm_base_url=pm_base_url,
        hl_base_url=hl_base_url,
        pm_timeout_s=pm_timeout_s,
        hl_timeout_s=hl_timeout_s,
        monotonic_ns_fn=monotonic_ns_fn or _mono_counter(),
        utc_now_fn=utc_now_fn or (lambda: _FIXED_UTC),
        max_skew_ms=max_skew_ms,
    ))
    return out, session, http_client


# ===========================================================================
# 1. correct YES/NO token + HL asset forwarding
# ===========================================================================

def test_yes_no_tokens_and_hl_asset_forwarded():
    hl_calls = []
    rec, _, http = _run(hl_calls=hl_calls)
    tokens = sorted(c["params"]["token_id"] for c in http.calls)
    assert tokens == ["NO_TOKEN", "YES_TOKEN"]
    # endpoint construction is the courier's job; assert it hit /book
    assert all(c["url"].endswith("/book") for c in http.calls)
    # HL leg: exactly the allMids POST body for the onboarding asset
    call_entries = [e for e in hl_calls if e[0] == "call"]
    assert len(call_entries) == 1
    assert call_entries[0][2] == {"type": "allMids"}
    assert rec["status"] == "GOLDEN_SAMPLE_OK"


def test_yes_and_no_slots_bind_expected_token_ids():
    rec, _, _ = _run()
    assert rec["yes_book"]["expected_token_id"] == "YES_TOKEN"
    assert rec["no_book"]["expected_token_id"] == "NO_TOKEN"
    assert rec["hl_reference"]["expected_asset"] == "BTC"


# ===========================================================================
# 2. exactly one call per courier, no retry
# ===========================================================================

def test_exactly_one_call_per_courier():
    hl_calls = []
    _, _, http = _run(hl_calls=hl_calls)
    # two book gets (YES + NO), each once
    assert len(http.calls) == 2
    factory_entries = [e for e in hl_calls if e[0] == "factory"]
    call_entries = [e for e in hl_calls if e[0] == "call"]
    assert len(factory_entries) == 1
    assert len(call_entries) == 1


def test_one_book_get_per_token():
    rec, _, http = _run()
    seen = [c["params"]["token_id"] for c in http.calls]
    assert sorted(seen) == ["NO_TOKEN", "YES_TOKEN"]
    assert len(seen) == len(set(seen))  # no duplicate => no retry


# ===========================================================================
# 3. shared PM session lifecycle + cleanup (success, leg failure, cancellation)
# ===========================================================================

def test_session_opened_and_closed_on_success():
    _, session, _ = _run()
    assert session.entered == 1
    assert session.exited == 1


def test_session_closed_when_one_leg_fails():
    hl_calls = []
    factory = _hl_factory(_HL_PAYLOAD, calls_sink=hl_calls, raise_exc=RuntimeError("hl down"))
    rec, session, _ = _run(hl_factory=factory)
    assert session.entered == 1
    assert session.exited == 1
    assert rec["status"] == "GOLDEN_SAMPLE_INVALID"


def test_session_closed_on_external_cancellation():
    http = _FakeHttpClient({"YES_TOKEN": _YES_BODY, "NO_TOKEN": _NO_BODY},
                           raise_exc=_ExternalCancellation())
    session = _FakePmSession(http)
    with pytest.raises(_ExternalCancellation):
        _run(http_client=http, session=session)
    assert session.entered == 1
    assert session.exited == 1


# ===========================================================================
# 4. one failed leg retains partial evidence from completed legs
# ===========================================================================

def test_failed_hl_leg_preserves_book_evidence():
    # The HL courier fail-closes a client exception into a structured carrier (not a raise), so the
    # failed leg yields an INVALID carrier while the other two bounded legs keep full evidence.
    factory = _hl_factory(_HL_PAYLOAD, calls_sink=[], raise_exc=RuntimeError("hl down"))
    rec, _, _ = _run(hl_factory=factory)
    assert rec["status"] == "GOLDEN_SAMPLE_INVALID"
    assert rec["error_code"] == "hl_reference_invalid"
    # the two book legs completed and retained their evidence
    assert rec["yes_book"]["evidence"] is not None
    assert rec["no_book"]["evidence"] is not None
    # the failed leg's evidence is its fail-closed carrier, surfacing the venue error code
    assert rec["hl_reference"]["evidence"]["status"] == "VENUE_REFERENCE_INVALID"
    assert rec["hl_reference"]["evidence"]["error_code"] == "hl_fetch_error"
    assert rec["hl_reference"]["error_code"] == "hl_fetch_error"


# ===========================================================================
# 5. timeout validation + separation from max_skew_ms
# ===========================================================================

@pytest.mark.parametrize("bad", [0, -1, -0.5])
def test_pm_timeout_nonpositive_valueerror(bad):
    session = _FakePmSession(_FakeHttpClient({}))
    with pytest.raises(ValueError):
        _run(session=session, pm_timeout_s=bad)
    assert session.entered == 0  # rejected before any session work


@pytest.mark.parametrize("bad", [True, "1.0", None])
def test_pm_timeout_wrong_type_typeerror(bad):
    session = _FakePmSession(_FakeHttpClient({}))
    with pytest.raises(TypeError):
        _run(session=session, pm_timeout_s=bad)
    assert session.entered == 0


@pytest.mark.parametrize("bad", [float("inf"), float("nan")])
def test_pm_timeout_non_finite_valueerror(bad):
    session = _FakePmSession(_FakeHttpClient({}))
    with pytest.raises(ValueError):
        _run(session=session, pm_timeout_s=bad)
    assert session.entered == 0


@pytest.mark.parametrize("bad", [0, -1, True, "2", float("inf"), float("nan"), None])
def test_hl_timeout_invalid_rejected(bad):
    session = _FakePmSession(_FakeHttpClient({}))
    with pytest.raises((TypeError, ValueError)):
        _run(session=session, hl_timeout_s=bad)
    assert session.entered == 0


def test_timeouts_threaded_separately_from_max_skew():
    hl_calls = []
    rec, _, http = _run(hl_calls=hl_calls, pm_timeout_s=1.5, hl_timeout_s=2.0, max_skew_ms=7_000)
    assert all(c["timeout"] == 1.5 for c in http.calls)        # pm deadline -> /book get
    assert ("factory", 2.0) in hl_calls                         # hl deadline -> client factory
    assert rec["max_skew_ms"] == 7_000                          # skew gate untouched, forwarded


def test_max_skew_ms_has_no_default():
    # keyword-only with no default => omitting it is a TypeError
    with pytest.raises(TypeError):
        asyncio.run(run_golden_sample_live(
            onboarding_record=_onboarding_record(),
            pm_session=_FakePmSession(_FakeHttpClient({})),
            hl_client_factory=_hl_factory(_HL_PAYLOAD, calls_sink=[]),
            pm_base_url="https://clob.example.com",
            hl_base_url="https://hl.example.com",
            pm_timeout_s=1.5,
            hl_timeout_s=2.0,
            monotonic_ns_fn=_mono_counter(),
            utc_now_fn=lambda: _FIXED_UTC,
        ))


def test_max_skew_ms_forwarded_unchanged():
    rec, _, _ = _run(max_skew_ms=12_345)
    assert rec["max_skew_ms"] == 12_345


# ===========================================================================
# 6. Decimal preservation, strict plain-tree output, caller<->sample isolation
# ===========================================================================

def test_hl_reference_price_preserved_as_decimal():
    rec, _, _ = _run()
    price = rec["hl_reference"]["evidence"]["reference_price"]
    assert isinstance(price, Decimal)
    assert not isinstance(price, float)
    assert price == Decimal("60279.5")
    assert rec["hl_reference"]["evidence"]["reference_source"] == _HL_SOURCE


def test_book_levels_preserved_as_decimal():
    rec, _, _ = _run()
    asks = rec["yes_book"]["evidence"]["parsed_safe_book"]["asks"]
    assert isinstance(asks[0][0], Decimal)
    assert isinstance(asks[0][1], Decimal)
    assert not isinstance(asks[0][0], float)


def test_no_spot_reference_alias_anywhere():
    rec, _, _ = _run()
    blob = json.dumps(serialize_golden_sample(rec))
    assert "spot_reference" not in blob
    assert "spot" not in rec["hl_reference"]["evidence"]


def test_caller_mutation_does_not_reach_sample():
    record = _onboarding_record()
    rec, _, _ = _run(record=record)
    record["gamma"]["outcome_token_map"][0]["token_id"] = "MUTATED"
    record["binance"]["strike_price"] = Decimal("1")
    assert rec["onboarding"]["gamma"]["outcome_token_map"][0]["token_id"] == "YES_TOKEN"
    assert rec["onboarding"]["binance"]["strike_price"] == Decimal("60000.0")


def test_sample_mutation_does_not_reach_caller():
    record = _onboarding_record()
    rec, _, _ = _run(record=record)
    rec["onboarding"]["asset"] = "MUTATED"
    rec["onboarding"]["gamma"]["event_start_time_ms"] = 999999
    assert record["asset"] == "BTC"
    assert record["gamma"]["event_start_time_ms"] == 1000


# ===========================================================================
# optional pure serializer: strict JSON, Decimal->fixed string, reject floats
# ===========================================================================

def test_serializer_is_pure_and_decimal_fixed_point():
    rec, _, _ = _run()
    before = rec["hl_reference"]["evidence"]["reference_price"]
    line = serialize_golden_sample(rec)
    # does not mutate the record
    assert rec["hl_reference"]["evidence"]["reference_price"] is before
    decoded = json.loads(line)
    assert decoded["hl_reference"]["evidence"]["reference_price"] == "60279.5"
    assert decoded["yes_book"]["evidence"]["parsed_safe_book"]["asks"][0][0] == "0.51"


def test_serializer_datetime_is_iso_provenance():
    rec, _, _ = _run()
    decoded = json.loads(serialize_golden_sample(rec))
    assert decoded["yes_book"]["client_received_at_utc"] == _FIXED_UTC.isoformat()


def test_serializer_rejects_float():
    with pytest.raises(TypeError):
        serialize_golden_sample({"bad": 1.5})


def test_serializer_rejects_unsupported_node():
    with pytest.raises(TypeError):
        serialize_golden_sample({"bad": {1, 2, 3}})


def test_serializer_returns_str():
    rec, _, _ = _run()
    assert isinstance(serialize_golden_sample(rec), str)


# ===========================================================================
# 7. no forbidden downstream/runtime surfaces in the wiring source
# ===========================================================================

def test_source_scan_no_forbidden_surfaces():
    import tools.golden_sample_live_wiring as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        low = fh.read().lower()
    banned = (
        "assembler", "calculator", "runner", "option a", "persistence", "csv",
        "trade", "signal", "edge", "candidate", "actionable", "actionability",
        "order", "fill", "buy", "sell", "stake", "wallet", "signing", "s1",
        "scanner", "discover", "pagination", "next_cursor", "while", "retry",
        "spot", "truth", "oracle", "settlement", "aiohttp", "requests",
    )
    for term in banned:
        assert term not in low, f"forbidden term {term!r} present in live wiring source"


# ===========================================================================
# 8. no real network / no real clock (structural guard)
# ===========================================================================

def test_wiring_does_not_create_its_own_gather_or_tasks():
    import tools.golden_sample_live_wiring as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        src = fh.read()
    assert "gather" not in src           # concurrency owned by the orchestrator only
    assert "create_task" not in src
    assert "ensure_future" not in src
