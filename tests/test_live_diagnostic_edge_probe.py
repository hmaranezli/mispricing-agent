"""tests/test_live_diagnostic_edge_probe.py — offline TDD for the capture -> economics bridge driver.

live_diagnostic_edge_probe.main runs preflight economic validation, then ONE live capture
(onboard_market -> run_golden_sample_live), and ONLY on GOLDEN_SAMPLE_OK invokes the pure diagnostic
economics calculator. Capture-layer failures and calculator-layer fail-closed are kept strictly
distinct. Everything is injected: capture clients, clocks, and (optionally) the economics function.
No network, no real clock for capture timing.

First RED: module tools.live_diagnostic_edge_probe does not exist -> ImportError.
"""
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.live_diagnostic_edge_probe import main, build_arg_parser

_CID = "0x1260dda542bb5fb18a6e4ffb74468d3983dbb0ceb7faa09cf2285e1fc53d3020"
_SLUG = "bitcoin-up-or-down-june-26-2026-3pm-et"
_EVENT_MS = 1782500400000
_END_MS = 1782504000000
_NOW_IN_WINDOW = _EVENT_MS + 600_000
_VAL_MS = _END_MS - 3_600_000
_ISO_UTC = "2026-06-27T12:00:00+00:00"

_YES_BODY = ('{"asks":[{"price":"0.40","size":"1000"},{"price":"0.50","size":"1000"}],'
             '"bids":[{"price":"0.38","size":"1000"},{"price":"0.30","size":"1000"}],'
             '"neg_risk":false}')
_NO_BODY = ('{"asks":[{"price":"0.60","size":"1000"},{"price":"0.62","size":"1000"}],'
            '"bids":[{"price":"0.58","size":"1000"},{"price":"0.50","size":"1000"}],'
            '"neg_risk":false}')
_HL_PAYLOAD = {"BTC": "60279.5"}

_OMIT = object()
_DEFAULT = object()


def _gamma_doc(**over):
    d = {
        "conditionId": _CID,
        "outcomes": json.dumps(["Up", "Down"]),
        "clobTokenIds": json.dumps(["YESTOK", "NOTOK"]),
        "eventStartTime": "2026-06-26T19:00:00Z",
        "endDate": "2026-06-26T20:00:00Z",
        "slug": _SLUG,
    }
    d.update(over)
    return d


def _kline(open_time=_EVENT_MS, open_price="59668.01"):
    return [open_time, open_price, "60000.0", "59000.0", "59800.0", "1.0", open_time + 3_599_999]


class _FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    async def text(self):
        return self._body


class _FakePmHttp:
    def __init__(self, body_by_token, *, raise_exc=None):
        self.body_by_token = body_by_token
        self.raise_exc = raise_exc
        self.calls = []

    async def get(self, url, *, params=None, timeout=None):
        token = (params or {}).get("token_id")
        self.calls.append(token)
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


class _Ctx:
    def __init__(self):
        self.gamma_calls = []
        self.binance_calls = []
        self.session = None
        self.http = None
        self.econ = None


class _EconSpy:
    def __init__(self, result=None, raise_exc=None):
        self.calls = []
        self.result = result if result is not None else {"status": "DIAGNOSTIC_OK"}
        self.raise_exc = raise_exc

    def __call__(self, *, golden_sample_record, intended_stake_usd, config):
        self.calls.append({"stake": intended_stake_usd, "config": dict(config)})
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.result


def _make_injections(ctx, *, gamma_payload, binance_payload, hl_raise=None):
    def build_onboarding_clients(timeout_s):
        async def gamma(url):
            ctx.gamma_calls.append(url)
            return gamma_payload

        async def binance(url):
            ctx.binance_calls.append(url)
            return binance_payload
        return gamma, binance

    ctx.http = _FakePmHttp({"YESTOK": _YES_BODY, "NOTOK": _NO_BODY})
    ctx.session = _FakePmSession(ctx.http)

    def build_pm_session(pm_timeout_s):
        return ctx.session

    def hl_client_factory(timeout_s):
        async def client(url, *, json_body):
            if hl_raise is not None:
                raise hl_raise
            return _HL_PAYLOAD
        return client

    def monotonic_ns_fn(_s={"v": 0}):
        _s["v"] += 1
        return _s["v"]

    return dict(build_onboarding_clients=build_onboarding_clients,
                build_pm_session=build_pm_session, hl_client_factory=hl_client_factory,
                now_fn=lambda: _NOW_IN_WINDOW, monotonic_ns_fn=monotonic_ns_fn,
                utc_now_fn=lambda: _ISO_UTC)


def _argv(**over):
    base = {
        "--slug": _SLUG, "--asset": "BTC", "--interval": "4h",
        "--binance-symbol": "BTCUSDT", "--expected-condition-id": _CID,
        "--max-skew-ms": "100000", "--onboarding-timeout-s": "2.0",
        "--pm-timeout-s": "2.0", "--hl-timeout-s": "2.0",
        "--gamma-base-url": "https://g", "--binance-base-url": "https://b",
        "--pm-base-url": "https://pm", "--hl-base-url": "https://hl",
        "--intended-stake-usd": "100", "--valuation-time-ms": str(_VAL_MS),
        "--fee-per-share": "0.01", "--slippage-allowance": "0.005",
        "--safety-margin": "0.005", "--max-spread": "0.05",
        "--sigma-annual": "0.5", "--drift-annual": "0", "--decimal-precision": "40",
    }
    base.update(over)
    argv = []
    for k, v in base.items():
        if v is _OMIT:
            continue
        argv += [k, str(v)]
    return argv


def _invoke(*, argv_over=None, gamma_payload=_DEFAULT, binance_payload=_DEFAULT,
            hl_raise=None, economics_fn=None, monkeypatch_onboard=None):
    ctx = _Ctx()
    gp = [_gamma_doc()] if gamma_payload is _DEFAULT else gamma_payload
    bp = [_kline()] if binance_payload is _DEFAULT else binance_payload
    inj = _make_injections(ctx, gamma_payload=gp, binance_payload=bp, hl_raise=hl_raise)
    if economics_fn is not None:
        inj["economics_fn"] = economics_fn
        ctx.econ = economics_fn
    out, err = io.StringIO(), io.StringIO()
    code = main(_argv(**(argv_over or {})), out=out, err=err, **inj)
    payload = None
    if out.getvalue().strip():
        payload = json.loads(out.getvalue())
    return code, payload, ctx


# ===========================================================================
# happy path: capture OK + real economics -> DIAGNOSTIC_OK
# ===========================================================================

def test_happy_path_exit0_economics_ok():
    code, env, _ = _invoke()
    assert code == 0
    assert env["schema_version"] == "diag-edge-probe-v0"
    assert env["layer"] == "ECONOMICS"
    assert env["capture_status"] == "GOLDEN_SAMPLE_OK"
    assert env["economics"]["status"] == "DIAGNOSTIC_OK"
    assert env["fail_closed_reason"] is None
    assert env["capture"]["status"] == "GOLDEN_SAMPLE_OK"
    assert "not_actionable" in env["markers"]


def test_happy_path_both_legs_present_no_actionability():
    _, env, _ = _invoke()
    econ = env["economics"]
    assert econ["yes_leg"]["diagnostic_net_edge"] is not None
    assert econ["no_leg"]["diagnostic_net_edge"] is not None
    blob = json.dumps(env).lower()
    for bad in ("recommend", "buy_", "sell_", "route", "order_intent"):
        assert bad not in blob


# ===========================================================================
# economics fail-closed after capture OK -> exit 1 (calculator actually ran)
# ===========================================================================

def test_economics_fail_closed_insufficient_depth_exit1():
    code, env, _ = _invoke(argv_over={"--intended-stake-usd": "1000000"})  # deeper than book
    assert code == 1
    assert env["layer"] == "ECONOMICS"
    assert env["capture_status"] == "GOLDEN_SAMPLE_OK"
    assert env["economics"]["status"] == "CALC_FAILED_CLOSED"
    assert env["economics"]["fail_closed_reason"] == "insufficient_depth"


# ===========================================================================
# preflight validation bounds -> VALIDATION layer, exit 2, zero work
# ===========================================================================

@pytest.mark.parametrize("over", [
    {"--intended-stake-usd": "0"},
    {"--intended-stake-usd": "-1"},
    {"--fee-per-share": "1"},
    {"--fee-per-share": "-0.01"},
    {"--slippage-allowance": "1"},
    {"--safety-margin": "1"},
    {"--max-spread": "0"},
    {"--max-spread": "1"},
    {"--sigma-annual": "0"},
    {"--sigma-annual": "-0.1"},
    {"--drift-annual": "abc"},
    {"--decimal-precision": "27"},
    {"--decimal-precision": "81"},
    {"--intended-stake-usd": "NaN"},
])
def test_validation_bounds_exit2_zero_work(over):
    spy = _EconSpy()
    code, env, ctx = _invoke(argv_over=over, economics_fn=spy)
    assert code == 2
    assert env["layer"] == "VALIDATION"
    assert env["fail_closed_reason"] == "invalid_config"
    assert env["capture"] is None
    assert env["economics"] is None
    assert ctx.gamma_calls == []        # no onboarding
    assert ctx.binance_calls == []      # no binance
    assert spy.calls == []              # no calculator


# ===========================================================================
# missing required CLI args -> exit 2, zero work
# ===========================================================================

@pytest.mark.parametrize("missing", ["--slug", "--intended-stake-usd", "--sigma-annual",
                                      "--valuation-time-ms", "--decimal-precision", "--max-spread"])
def test_missing_required_arg_exit2(missing):
    spy = _EconSpy()
    code, _, ctx = _invoke(argv_over={missing: _OMIT}, economics_fn=spy)
    assert code == 2
    assert ctx.gamma_calls == []
    assert spy.calls == []


# ===========================================================================
# capture-layer stops: calculator NEVER invoked, never CALC_FAILED_CLOSED
# ===========================================================================

def test_onboarding_invalid_exit4():
    spy = _EconSpy()
    code, env, ctx = _invoke(gamma_payload=[], economics_fn=spy)   # gamma_empty
    assert code == 4
    assert env["layer"] == "ONBOARDING"
    assert env["capture_status"] == "ONBOARDING_INVALID"
    assert env["economics"] is None
    assert spy.calls == []
    assert ctx.http.calls == []         # no capture book fetches


def test_identity_mismatch_exit5(monkeypatch):
    spy = _EconSpy()

    async def fake_onboard(**kwargs):
        return {
            "onboarding_status": "ONBOARDING_OK", "onboarding_error_code": None,
            "slug": kwargs["slug"], "asset": kwargs["asset"], "interval": kwargs["interval"],
            "condition_id": "0xDIFFERENT",
            "gamma": {"status": "VENUE_METADATA_OK",
                      "outcome_token_map": [{"token_id": "YESTOK"}, {"token_id": "NOTOK"}],
                      "event_start_time_ms": _EVENT_MS, "end_date_ms": _END_MS},
            "binance": {"status": "VENUE_STRIKE_OK", "event_start_time_ms": _EVENT_MS},
            "classification": {"status": "CACHE_READY"},
        }

    monkeypatch.setattr("tools.live_diagnostic_edge_probe.onboard_market", fake_onboard)
    code, env, ctx = _invoke(economics_fn=spy)
    assert code == 5
    assert env["layer"] == "IDENTITY"
    assert env["economics"] is None
    assert spy.calls == []


def test_golden_sample_invalid_exit6_not_calc_failed():
    spy = _EconSpy()
    code, env, ctx = _invoke(hl_raise=RuntimeError("hl down"), economics_fn=spy)
    assert code == 6
    assert env["layer"] == "CAPTURE"
    assert env["capture_status"] == "GOLDEN_SAMPLE_INVALID"
    assert env["economics"] is None
    assert env["fail_closed_reason"] != "CALC_FAILED_CLOSED"
    assert spy.calls == []              # calculator never ran
    blob = json.dumps(env)
    assert "CALC_FAILED_CLOSED" not in blob


# ===========================================================================
# CLI type contract: economic value args are type=str (no float)
# ===========================================================================

def test_economic_value_args_are_str_type():
    parser = build_arg_parser()
    by_dest = {a.dest: a for a in parser._actions}
    for dest in ("intended_stake_usd", "fee_per_share", "slippage_allowance", "safety_margin",
                 "max_spread", "sigma_annual", "drift_annual"):
        assert by_dest[dest].type is None       # argparse str default == no float coercion
    assert by_dest["valuation_time_ms"].type is int
    assert by_dest["decimal_precision"].type is int
    assert by_dest["max_skew_ms"].type is int
    assert by_dest["pm_timeout_s"].type is float


# ===========================================================================
# isolation / serialization / side-effects
# ===========================================================================

def test_import_isolation_one_way_bridge():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    econ = open(os.path.join(base, "analysis", "golden_sample_economics.py")).read()
    orch = open(os.path.join(base, "tools", "golden_sample_orchestrator.py")).read()
    wiring = open(os.path.join(base, "tools", "golden_sample_live_wiring.py")).read()
    driver = open(os.path.join(base, "tools", "live_diagnostic_edge_probe.py")).read()
    # capture/economics never import each other
    assert "golden_sample_economics" not in orch
    assert "golden_sample_economics" not in wiring
    assert "golden_sample_orchestrator" not in econ
    assert "live_golden_sample" not in econ
    # the driver imports BOTH sides (one-way bridge)
    assert "golden_sample_live_wiring" in driver
    assert "golden_sample_economics" in driver


def test_strict_json_no_default_str_and_decimal_strings():
    _, env, _ = _invoke()
    # round-trips; the model probability + vwap render as quoted decimal strings
    assert isinstance(env["economics"]["model"]["model_fair_probability_up"], str)
    assert isinstance(env["economics"]["yes_leg"]["pm_stake_adjusted_vwap"], str)
    # capture record's Decimal strike rendered as a fixed-point string
    assert isinstance(env["capture"]["onboarding"]["binance"]["strike_price"], str)


def test_existing_probe_exit_codes_unchanged():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(base, "tools", "live_golden_sample_probe.py")).read()
    # the original probe still ends its capture branch with 0/else-1 (untouched contract)
    assert 'return 0 if capture["status"] == "GOLDEN_SAMPLE_OK" else 1' in src
    assert "diag-edge-probe-v0" not in src
