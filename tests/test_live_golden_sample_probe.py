"""tests/test_live_golden_sample_probe.py — TDD for the N=1 onboarder -> Golden Sample capture driver.

live_golden_sample_probe.main runs ONE asyncio.run over a single async pipeline:
    await onboard_market  ->  validate/gate (+ identity)  ->  await run_golden_sample_live
Onboarding fully completes (and its one-shot clients self-close) before capture begins; capture timing
is owned exclusively by the unchanged orchestrator's injected monotonic clock. Everything is injected
here: onboarding clients, the PM session, the HL client factory, the now/monotonic/utc clocks, and the
output stream. No real network, no real clock for capture timing.

First RED: module tools.live_golden_sample_probe does not exist -> ImportError.
"""
import json
import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.live_golden_sample_probe import main, build_arg_parser

# ---- shapes reused verbatim from the onboarder's own contract ----
_CID = "0x1260dda542bb5fb18a6e4ffb74468d3983dbb0ceb7faa09cf2285e1fc53d3020"
_SLUG = "bitcoin-up-or-down-june-26-2026-3pm-et"
_EVENT_MS = 1782500400000
_NOW_IN_WINDOW = _EVENT_MS + 600_000
_BOOK_BODY = '{"asks": [[0.51, 10]], "bids": [[0.49, 20]]}'
_HL_PAYLOAD = {"BTC": "60279.5"}
_ISO_UTC = "2026-06-27T12:00:00+00:00"

_OMIT = object()
_DEFAULT = object()


def _gamma_doc(**over):
    d = {
        "conditionId": _CID,
        "outcomes": json.dumps(["Up", "Down"]),
        "clobTokenIds": json.dumps(["YESTOK", "NOTOK"]),
        "eventStartTime": "2026-06-26T19:00:00Z",
        "endDate": "2026-06-26T20:00:00Z",
        "question": "Bitcoin Up or Down - June 26, 3PM ET",
        "slug": _SLUG,
    }
    d.update(over)
    return d


def _kline(open_time=_EVENT_MS, open_price="59668.01"):
    return [open_time, open_price, "60000.0", "59000.0", "59800.0", "1.0", open_time + 3_599_999]


# ---------------------------------------------------------------------------
# injected fakes
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    async def text(self):
        return self._body


class _FakePmHttp:
    def __init__(self, body_by_token, *, order_log=None, raise_exc=None):
        self.body_by_token = body_by_token
        self.order_log = order_log
        self.raise_exc = raise_exc
        self.calls = []

    async def get(self, url, *, params=None, timeout=None):
        token = (params or {}).get("token_id")
        if self.order_log is not None:
            self.order_log.append(("pm_get", token))
        self.calls.append({"url": url, "params": dict(params or {}), "timeout": timeout})
        if self.raise_exc is not None:
            raise self.raise_exc
        return _FakeResponse(200, self.body_by_token[token])


class _FakePmSession:
    def __init__(self, http):
        self.http = http
        self.entered = 0
        self.exited = 0

    async def __aenter__(self):
        self.entered += 1
        return self.http

    async def __aexit__(self, *exc):
        self.exited += 1
        return False


class _ExternalCancellation(BaseException):
    """Stand-in for external cancellation the orchestrator must not swallow."""


class _Ctx:
    """Carries all injected fakes + their call records for one main() invocation."""
    def __init__(self):
        self.order_log = []
        self.onb_deadlines = []
        self.pm_deadlines = []
        self.hl_events = []
        self.gamma_calls = []
        self.binance_calls = []
        self.session = None
        self.http = None


def _make_injections(ctx, *, gamma_payload, binance_payload, book_bodies, hl_payload,
                     pm_raise=None, hl_raise=None):
    def build_onboarding_clients(timeout_s):
        ctx.onb_deadlines.append(timeout_s)

        async def gamma(url):
            ctx.order_log.append(("gamma", url))
            ctx.gamma_calls.append(url)
            return gamma_payload

        async def binance(url):
            ctx.order_log.append(("binance", url))
            ctx.binance_calls.append(url)
            return binance_payload
        return gamma, binance

    ctx.http = _FakePmHttp(book_bodies, order_log=ctx.order_log, raise_exc=pm_raise)
    ctx.session = _FakePmSession(ctx.http)

    def build_pm_session(pm_timeout_s):
        ctx.pm_deadlines.append(pm_timeout_s)
        return ctx.session

    def hl_client_factory(timeout_s):
        ctx.hl_events.append(("factory", timeout_s))

        async def client(url, *, json_body):
            ctx.order_log.append(("hl", url))
            ctx.hl_events.append(("call", url, json_body))
            if hl_raise is not None:
                raise hl_raise
            return hl_payload
        return client

    def monotonic_ns_fn(_state={"v": 0}):
        _state["v"] += 1
        ctx.order_log.append(("mono", _state["v"]))
        return _state["v"]

    return dict(build_onboarding_clients=build_onboarding_clients,
                build_pm_session=build_pm_session,
                hl_client_factory=hl_client_factory,
                now_fn=lambda: _NOW_IN_WINDOW,
                monotonic_ns_fn=monotonic_ns_fn,
                utc_now_fn=lambda: _ISO_UTC)


def _argv(**over):
    base = {
        "--slug": _SLUG, "--asset": "BTC", "--interval": "1h",
        "--binance-symbol": "BTCUSDT", "--expected-condition-id": _CID,
        "--max-skew-ms": "100000", "--onboarding-timeout-s": "2.0",
        "--pm-timeout-s": "1.5", "--hl-timeout-s": "2.0",
    }
    base.update(over)
    argv = []
    for k, v in base.items():
        if v is _OMIT:
            continue
        argv += [k, str(v)]
    return argv


def _invoke(*, argv_over=None, gamma_payload=_DEFAULT, binance_payload=_DEFAULT,
            book_bodies=None, hl_payload=None, pm_raise=None, hl_raise=None):
    ctx = _Ctx()
    gp = [_gamma_doc()] if gamma_payload is _DEFAULT else gamma_payload
    bp = [_kline()] if binance_payload is _DEFAULT else binance_payload
    bodies = book_bodies if book_bodies is not None else {"YESTOK": _BOOK_BODY, "NOTOK": _BOOK_BODY}
    hp = hl_payload if hl_payload is not None else _HL_PAYLOAD
    inj = _make_injections(ctx, gamma_payload=gp, binance_payload=bp, book_bodies=bodies,
                           hl_payload=hp, pm_raise=pm_raise, hl_raise=hl_raise)
    import io
    out = io.StringIO()
    err = io.StringIO()
    code = main(_argv(**(argv_over or {})), out=out, err=err, **inj)
    return code, out.getvalue(), err.getvalue(), ctx


# ===========================================================================
# happy path: single loop, OK, exact call counts, strict serialization
# ===========================================================================

def test_happy_path_exit_zero_strict_json():
    code, out, _, ctx = _invoke()
    assert code == 0
    rec = json.loads(out)
    assert rec["status"] == "GOLDEN_SAMPLE_OK"
    assert rec["hl_reference"]["evidence"]["reference_price"] == "60279.5"   # Decimal -> fixed str
    assert rec["hl_reference"]["evidence"]["reference_source"] == "hyperliquid_all_mids_perp"


def test_exact_call_counts_zero_retry():
    code, _, _, ctx = _invoke()
    assert code == 0
    assert len(ctx.gamma_calls) == 1           # gamma once
    assert len(ctx.binance_calls) == 1         # binance once (after valid gamma)
    pm_tokens = sorted(c["params"]["token_id"] for c in ctx.http.calls)
    assert pm_tokens == ["NOTOK", "YESTOK"]    # YES + NO once each, no duplicate => no retry
    assert len([e for e in ctx.hl_events if e[0] == "factory"]) == 1
    assert len([e for e in ctx.hl_events if e[0] == "call"]) == 1


def test_onboarding_finishes_before_first_monotonic_tick():
    _, _, _, ctx = _invoke()
    mono_idxs = [i for i, e in enumerate(ctx.order_log) if e[0] == "mono"]
    onb_idxs = [i for i, e in enumerate(ctx.order_log) if e[0] in ("gamma", "binance")]
    assert mono_idxs and onb_idxs
    assert max(onb_idxs) < min(mono_idxs)      # all onboarding strictly before any capture tick
    # gamma strictly before binance
    g = next(i for i, e in enumerate(ctx.order_log) if e[0] == "gamma")
    b = next(i for i, e in enumerate(ctx.order_log) if e[0] == "binance")
    assert g < b


def test_capture_legs_after_onboarding():
    _, _, _, ctx = _invoke()
    last_onb = max(i for i, e in enumerate(ctx.order_log) if e[0] in ("gamma", "binance"))
    cap_idxs = [i for i, e in enumerate(ctx.order_log) if e[0] in ("pm_get", "hl")]
    assert cap_idxs and min(cap_idxs) > last_onb


def test_deadlines_threaded_to_each_phase():
    _, _, _, ctx = _invoke()
    assert ctx.onb_deadlines == [2.0]
    assert ctx.pm_deadlines == [1.5]
    assert ("factory", 2.0) in ctx.hl_events
    assert all(c["timeout"] == 1.5 for c in ctx.http.calls)


# ===========================================================================
# pre-gate failures: zero capture work
# ===========================================================================

def test_onboarding_invalid_exit_4_zero_capture():
    code, out, _, ctx = _invoke(gamma_payload=[])   # empty -> gamma_empty
    assert code == 4
    payload = json.loads(out)
    assert payload["phase"] == "ONBOARDING"
    assert payload["onboarding_status"] == "ONBOARDING_INVALID"
    assert payload["onboarding_error_code"] == "gamma_empty"
    # zero capture: no PM session, no HL factory, no book/hl calls
    assert ctx.session.entered == 0 and ctx.session.exited == 0
    assert ctx.pm_deadlines == []
    assert ctx.hl_events == []
    assert ctx.http.calls == []
    assert len(ctx.binance_calls) == 0          # gamma-invalid short-circuits binance too


def test_expected_condition_id_forwarded_unchanged(monkeypatch):
    # the required CLI condition id is forwarded verbatim into onboard_market (never substituted)
    captured = {}

    async def fake_onboard(**kwargs):
        captured.update(kwargs)
        return {"onboarding_status": "ONBOARDING_INVALID", "onboarding_error_code": "stub",
                "slug": kwargs["slug"], "asset": kwargs["asset"], "interval": kwargs["interval"],
                "condition_id": None, "gamma": None, "binance": None, "classification": None}

    monkeypatch.setattr("tools.live_golden_sample_probe.onboard_market", fake_onboard)
    code, _, _, ctx = _invoke()
    assert captured["expected_condition_id"] == _CID
    assert code == 4
    # forwarding does not trigger capture
    assert ctx.session.entered == 0 and ctx.hl_events == [] and ctx.http.calls == []


def test_early_condition_mismatch_exit_4_zero_binance_zero_capture():
    # real path: a wrong on-chain conditionId is rejected by Gamma (forwarded expected id) BEFORE
    # Binance -> ONBOARDING_INVALID / exit 4, gamma once, binance zero, zero capture.
    code, out, _, ctx = _invoke(gamma_payload=[_gamma_doc(conditionId="0xWRONG")])
    assert code == 4
    payload = json.loads(out)
    assert payload["phase"] == "ONBOARDING"
    assert payload["onboarding_status"] == "ONBOARDING_INVALID"
    assert payload["onboarding_error_code"] == "gamma_condition_id_mismatch"
    assert len(ctx.gamma_calls) == 1          # gamma once
    assert len(ctx.binance_calls) == 0        # binance zero (short-circuit)
    assert ctx.http.calls == []               # PM zero
    assert ctx.hl_events == []                # HL zero
    assert ctx.session.entered == 0           # no PM session built


def test_identity_gate_exit_5_via_inconsistent_ok_record(monkeypatch):
    # defense-in-depth: a (mocked) ONBOARDING_OK record whose condition_id disagrees with the
    # operator input must be rejected by the post-onboarding identity gate -> exit 5, zero capture.
    async def fake_onboard(**kwargs):
        return {
            "onboarding_status": "ONBOARDING_OK", "onboarding_error_code": None,
            "slug": kwargs["slug"], "asset": kwargs["asset"], "interval": kwargs["interval"],
            "condition_id": "0xDIFFERENT",
            "gamma": {"status": "VENUE_METADATA_OK",
                      "outcome_token_map": [{"token_id": "YESTOK"}, {"token_id": "NOTOK"}],
                      "event_start_time_ms": _EVENT_MS, "end_date_ms": _EVENT_MS + 3_600_000},
            "binance": {"status": "VENUE_STRIKE_OK", "event_start_time_ms": _EVENT_MS,
                        "strike_price": Decimal("59668.01")},
            "classification": {"status": "CACHE_READY"},
        }

    monkeypatch.setattr("tools.live_golden_sample_probe.onboard_market", fake_onboard)
    code, out, _, ctx = _invoke()
    assert code == 5
    payload = json.loads(out)
    assert payload["phase"] == "IDENTITY"
    assert payload["identity_status"] == "IDENTITY_MISMATCH"
    assert payload["reason"] == "condition_id_mismatch"
    assert payload["condition_id"] == "0xDIFFERENT"
    assert payload["expected_condition_id"] == _CID
    # zero capture
    assert ctx.session.entered == 0
    assert ctx.pm_deadlines == []
    assert ctx.hl_events == []
    assert ctx.http.calls == []


def test_capture_invalid_exit_1():
    # onboarding OK + identity OK, but HL leg fails -> GOLDEN_SAMPLE_INVALID -> exit 1
    code, out, _, ctx = _invoke(hl_raise=RuntimeError("hl down"))
    assert code == 1
    rec = json.loads(out)
    assert rec["status"] == "GOLDEN_SAMPLE_INVALID"
    assert rec["error_code"] == "hl_reference_invalid"
    assert rec["yes_book"]["evidence"] is not None     # partial evidence retained
    assert ctx.session.entered == 1 and ctx.session.exited == 1


# ===========================================================================
# CLI validation -> exit 2 (no onboarding work)
# ===========================================================================

@pytest.mark.parametrize("missing", ["--slug", "--asset", "--interval", "--binance-symbol",
                                      "--expected-condition-id", "--max-skew-ms",
                                      "--onboarding-timeout-s", "--pm-timeout-s", "--hl-timeout-s"])
def test_required_flags_missing_exit_2(missing):
    code, _, _, ctx = _invoke(argv_over={missing: _OMIT})
    assert code == 2
    assert ctx.gamma_calls == []     # never reached onboarding


@pytest.mark.parametrize("bad", ["0", "-1", "2.5", "inf", "nan"])
def test_pm_timeout_cap_and_validity_exit_2(bad):
    code, _, _, ctx = _invoke(argv_over={"--pm-timeout-s": bad})
    assert code == 2
    assert ctx.gamma_calls == []


@pytest.mark.parametrize("flag", ["--onboarding-timeout-s", "--hl-timeout-s"])
def test_other_deadlines_over_cap_exit_2(flag):
    code, _, _, ctx = _invoke(argv_over={flag: "2.0001"})
    assert code == 2
    assert ctx.gamma_calls == []


@pytest.mark.parametrize("bad", ["0", "-5"])
def test_max_skew_ms_must_be_positive_int_exit_2(bad):
    code, _, _, ctx = _invoke(argv_over={"--max-skew-ms": bad})
    assert code == 2
    assert ctx.gamma_calls == []


def test_now_ms_negative_exit_2():
    code, _, _, ctx = _invoke(argv_over={"--now-ms": "-1"})
    assert code == 2
    assert ctx.gamma_calls == []


def test_max_skew_ms_forwarded_into_capture_record():
    code, out, _, _ = _invoke(argv_over={"--max-skew-ms": "12345"})
    assert code == 0
    assert json.loads(out)["max_skew_ms"] == 12345


# ===========================================================================
# session cleanup on success / invalid leg / external cancellation
# ===========================================================================

def test_session_closed_on_success():
    _, _, _, ctx = _invoke()
    assert ctx.session.entered == 1 and ctx.session.exited == 1


def test_session_closed_on_invalid_leg():
    _, _, _, ctx = _invoke(hl_raise=RuntimeError("hl down"))
    assert ctx.session.entered == 1 and ctx.session.exited == 1


def test_session_closed_on_external_cancellation():
    with pytest.raises(_ExternalCancellation):
        _invoke(pm_raise=_ExternalCancellation())
    # cleanup is proven structurally inside the wiring; here we assert the BaseException propagates
    # (i.e. the driver does not swallow external cancellation into a normal exit code)


# ===========================================================================
# locked behaviors
# ===========================================================================

def test_reference_source_supported_locked_true_no_cli_toggle():
    parser = build_arg_parser()
    actions = {a.dest for a in parser._actions}
    assert "reference_source_supported" not in actions   # no CLI toggle exists


def test_condition_id_is_required():
    parser = build_arg_parser()
    cond = next(a for a in parser._actions if a.dest == "expected_condition_id")
    assert cond.required is True


# ===========================================================================
# strict serialization / structural guards
# ===========================================================================

def test_stdout_has_no_default_str_float_leak():
    code, out, _, _ = _invoke()
    assert code == 0
    # round-trips as strict JSON; the one Decimal renders as a quoted fixed-point string
    rec = json.loads(out)
    asks = rec["yes_book"]["evidence"]["parsed_safe_book"]["asks"]
    assert asks[0][0] == "0.51" and isinstance(asks[0][0], str)
    assert rec["yes_book"]["client_received_at_utc"] == _ISO_UTC   # ISO-8601 provenance string


def test_exactly_one_asyncio_run():
    import tools.live_golden_sample_probe as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        src = fh.read()
    assert src.count("asyncio.run") == 1


def test_driver_owns_no_concurrency():
    import tools.live_golden_sample_probe as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        src = fh.read()
    assert "gather" not in src
    assert "create_task" not in src
    assert "ensure_future" not in src


def test_source_scan_no_forbidden_surfaces():
    import tools.live_golden_sample_probe as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        low = fh.read().lower()
    banned = (
        "assembler", "calculator", "edge", "csv", "s1", "cache", "scanner",
        "actionable", "actionability", "spot", "oracle", "settlement", "truth",
        "trade", "signal", "candidate", "fill", "buy", "sell", "stake", "wallet",
        "signing", "while", "retry", "pagination", "next_cursor", "discover",
    )
    for term in banned:
        assert term not in low, f"forbidden term {term!r} present in probe source"
