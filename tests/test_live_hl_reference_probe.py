"""tests/test_live_hl_reference_probe.py — strict offline TDD for the HL reference diagnostic probe.

Fully offline: injected fake adapter factories, fake session/response objects, and (for schema-failure
paths) an injected fake courier. No real network. The probe wraps the UNCHANGED data.hl_reference_price
courier behind an injected async adapter and projects/serializes the result deterministically.

First RED: module tools.live_hl_reference_probe does not exist -> ImportError.
"""
import asyncio
import io
import json
import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.live_hl_reference_probe import (
    main,
    build_arg_parser,
    _make_adapter,
    _serialize_record,
    _default_adapter_factory,
)

_ENDPOINT = "https://api.hyperliquid.xyz/info"
_BODY = {"type": "allMids"}


# ===========================================================================
# fakes for the adapter seam
# ===========================================================================

class _FakeResp:
    def __init__(self, payload, *, status_exc=None, json_exc=None):
        self._payload = payload
        self._status_exc = status_exc
        self._json_exc = json_exc
        self.raise_for_status_calls = 0
        self.json_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def raise_for_status(self):
        self.raise_for_status_calls += 1
        if self._status_exc is not None:
            raise self._status_exc

    async def json(self):
        self.json_calls += 1
        if self._json_exc is not None:
            raise self._json_exc
        return self._payload


class _FakeSession:
    def __init__(self, resp, post_sink):
        self._resp = resp
        self._post_sink = post_sink
        self.enter_calls = 0

    async def __aenter__(self):
        self.enter_calls += 1
        return self

    async def __aexit__(self, *a):
        return False

    def post(self, url, *, json):
        self._post_sink.append((url, json))
        return self._resp


def _session_factory(resp, post_sink, sf_calls):
    def factory(*, timeout):
        sf_calls.append(timeout)
        return _FakeSession(resp, post_sink)
    return factory


def _timeout_factory(tf_calls):
    def factory(*, total):
        tf_calls.append(total)
        return ("TIMEOUT", total)
    return factory


# ===========================================================================
# adapter: exact call sequence + no retry  (logic is NOT pragma-excluded)
# ===========================================================================

def test_adapter_exact_call_sequence():
    resp = _FakeResp({"BTC": "60000.0"})
    post_sink, sf, tf = [], [], []
    adapter = _make_adapter(2.0, session_factory=_session_factory(resp, post_sink, sf),
                            timeout_factory=_timeout_factory(tf))
    out = asyncio.run(adapter(_ENDPOINT, json_body=_BODY))
    assert out == {"BTC": "60000.0"}
    assert tf == [2.0]                          # timeout built once with total=timeout_s
    assert len(sf) == 1                         # session built once
    assert post_sink == [(_ENDPOINT, _BODY)]    # one post, exact body
    assert resp.raise_for_status_calls == 1
    assert resp.json_calls == 1


def test_adapter_no_retry_on_status_error():
    resp = _FakeResp(None, status_exc=RuntimeError("503"))
    post_sink, sf, tf = [], [], []
    adapter = _make_adapter(1.0, session_factory=_session_factory(resp, post_sink, sf),
                            timeout_factory=_timeout_factory(tf))
    with pytest.raises(RuntimeError):
        asyncio.run(adapter(_ENDPOINT, json_body=_BODY))
    assert len(post_sink) == 1                  # exactly one post, no retry
    assert resp.raise_for_status_calls == 1
    assert resp.json_calls == 0                 # json not reached


def test_adapter_no_retry_on_json_error():
    resp = _FakeResp(None, json_exc=ValueError("bad json"))
    post_sink, sf, tf = [], [], []
    adapter = _make_adapter(1.0, session_factory=_session_factory(resp, post_sink, sf),
                            timeout_factory=_timeout_factory(tf))
    with pytest.raises(ValueError):
        asyncio.run(adapter(_ENDPOINT, json_body=_BODY))
    assert len(post_sink) == 1
    assert resp.json_calls == 1


def test_default_adapter_factory_builds_callable():
    # constructs the real aiohttp-backed adapter closure WITHOUT any network call
    adapter = _default_adapter_factory(2.0)
    assert callable(adapter)


# ===========================================================================
# adapter-factory fakes for whole-probe tests (real courier runs)
# ===========================================================================

def _adapter_factory(payload=None, *, raise_exc=None, factory_sink=None, url_sink=None):
    def factory(timeout_s):
        if factory_sink is not None:
            factory_sink.append(timeout_s)

        async def client(url, *, json_body):
            if url_sink is not None:
                url_sink.append((url, json_body))
            if raise_exc is not None:
                raise raise_exc
            return payload
        return client
    return factory


def _io():
    return io.StringIO(), io.StringIO()


# ===========================================================================
# CLI defaults + validation (exit 2 before any network construction)
# ===========================================================================

def test_defaults_btc_and_two():
    args = build_arg_parser().parse_args([])
    assert args.asset == "BTC"
    assert args.timeout_s == 2.0


@pytest.mark.parametrize("asset", ["", " ", " BTC ", "\tBTC"])
def test_bad_asset_exit_2_zero_calls(asset):
    out, err = _io()
    sink = []
    af = _adapter_factory({"BTC": "1.0"}, factory_sink=sink)
    code = main(["--asset", asset], adapter_factory=af, out=out, err=err)
    assert code == 2
    assert out.getvalue() == ""        # empty stdout
    assert sink == []                  # adapter factory never called -> no session/post


@pytest.mark.parametrize("tval", ["nan", "inf", "-inf", "0", "-1", "2.5", "3.0"])
def test_bad_timeout_exit_2_zero_calls(tval):
    out, err = _io()
    sink = []
    af = _adapter_factory({"BTC": "1.0"}, factory_sink=sink)
    code = main(["--timeout-s", tval], adapter_factory=af, out=out, err=err)
    assert code == 2
    assert out.getvalue() == ""
    assert sink == []


def test_malformed_timeout_argparse_exit_2():
    out, err = _io()
    sink = []
    af = _adapter_factory({"BTC": "1.0"}, factory_sink=sink)
    code = main(["--timeout-s", "abc"], adapter_factory=af, out=out, err=err)
    assert code == 2
    assert out.getvalue() == ""
    assert sink == []


def test_timeout_at_cap_is_accepted():
    out, err = _io()
    sink = []
    af = _adapter_factory({"BTC": "60000.0"}, factory_sink=sink)
    code = main(["--timeout-s", "2.0"], adapter_factory=af, out=out, err=err)
    assert code == 0
    assert sink == [2.0]


# ===========================================================================
# pinned endpoint + body through the real courier
# ===========================================================================

def test_endpoint_and_body_pinned():
    out, err = _io()
    urls = []
    af = _adapter_factory({"BTC": "60000.0"}, url_sink=urls)
    main(["--asset", "BTC"], adapter_factory=af, out=out, err=err)
    assert urls == [(_ENDPOINT, _BODY)]


# ===========================================================================
# courier outcomes -> exit codes (real courier)
# ===========================================================================

def test_ok_exit_0_single_json_line():
    out, err = _io()
    af = _adapter_factory({"BTC": "60123.5"})
    code = main(["--asset", "BTC"], adapter_factory=af, out=out, err=err)
    assert code == 0
    assert out.getvalue().count("\n") == 1     # exactly one line
    rec = json.loads(out.getvalue())
    assert rec == {"asset": "BTC", "reference_price": "60123.5",
                   "status": "VENUE_REFERENCE_OK", "error_code": None,
                   "reference_source": "hyperliquid_all_mids_perp"}


def test_fetch_error_exit_1():
    out, err = _io()
    af = _adapter_factory(raise_exc=TimeoutError("boom"))
    code = main(["--asset", "BTC"], adapter_factory=af, out=out, err=err)
    assert code == 1
    rec = json.loads(out.getvalue())
    assert rec["status"] == "VENUE_REFERENCE_INVALID"
    assert rec["error_code"] == "hl_fetch_error"
    assert rec["reference_price"] is None


def test_malformed_non_dict_exit_1():
    out, err = _io()
    af = _adapter_factory(["not", "dict"])
    code = main(["--asset", "BTC"], adapter_factory=af, out=out, err=err)
    assert code == 1
    assert json.loads(out.getvalue())["error_code"] == "hl_malformed_json"


def test_asset_not_found_exit_1():
    out, err = _io()
    af = _adapter_factory({"ETH": "3000.0"})
    code = main(["--asset", "BTC"], adapter_factory=af, out=out, err=err)
    assert code == 1
    assert json.loads(out.getvalue())["error_code"] == "hl_asset_not_found"


def test_bad_price_exit_1():
    out, err = _io()
    af = _adapter_factory({"BTC": "0"})
    code = main(["--asset", "BTC"], adapter_factory=af, out=out, err=err)
    assert code == 1
    assert json.loads(out.getvalue())["error_code"] == "hl_bad_price"


# ===========================================================================
# strict serialization boundary
# ===========================================================================

def _ok_record(**over):
    r = {"asset": "BTC", "reference_price": Decimal("60123.5"),
         "status": "VENUE_REFERENCE_OK", "error_code": None,
         "reference_source": "hyperliquid_all_mids_perp"}
    r.update(over)
    return r


def _invalid_record(**over):
    r = {"asset": "BTC", "reference_price": None,
         "status": "VENUE_REFERENCE_INVALID", "error_code": "hl_fetch_error",
         "reference_source": "hyperliquid_all_mids_perp"}
    r.update(over)
    return r


def test_serialize_ok_deterministic():
    s = _serialize_record(_ok_record())
    assert s == ('{"asset":"BTC","error_code":null,"reference_price":"60123.5",'
                 '"reference_source":"hyperliquid_all_mids_perp","status":"VENUE_REFERENCE_OK"}')


def test_serialize_invalid_deterministic():
    s = _serialize_record(_invalid_record())
    assert s == ('{"asset":"BTC","error_code":"hl_fetch_error","reference_price":null,'
                 '"reference_source":"hyperliquid_all_mids_perp","status":"VENUE_REFERENCE_INVALID"}')


def test_serialize_decimal_fixed_point():
    s = _serialize_record(_ok_record(reference_price=Decimal("60000.00")))
    assert json.loads(s)["reference_price"] == "60000.00"   # no sci-notation, fixed string


@pytest.mark.parametrize("bad_price", [60123.5, 60123, True])
def test_serialize_rejects_non_decimal_price_on_ok(bad_price):
    with pytest.raises((TypeError, ValueError)):
        _serialize_record(_ok_record(reference_price=bad_price))


@pytest.mark.parametrize("bad_price", [Decimal("NaN"), Decimal("Infinity"), Decimal("0"), Decimal("-1")])
def test_serialize_rejects_nonpositive_or_nonfinite_decimal_on_ok(bad_price):
    with pytest.raises(ValueError):
        _serialize_record(_ok_record(reference_price=bad_price))


def test_serialize_rejects_missing_key():
    r = _ok_record()
    del r["error_code"]
    with pytest.raises(ValueError):
        _serialize_record(r)


def test_serialize_rejects_extra_key():
    r = _ok_record()
    r["extra"] = "x"
    with pytest.raises(ValueError):
        _serialize_record(r)


def test_serialize_rejects_wrong_source():
    with pytest.raises(ValueError):
        _serialize_record(_ok_record(reference_source="binance"))


def test_serialize_rejects_unknown_status():
    with pytest.raises(ValueError):
        _serialize_record(_ok_record(status="WHATEVER"))


def test_serialize_rejects_unknown_error_code():
    with pytest.raises(ValueError):
        _serialize_record(_invalid_record(error_code="hl_made_up"))


def test_serialize_rejects_inconsistent_ok_with_error_code():
    with pytest.raises(ValueError):
        _serialize_record(_ok_record(error_code="hl_fetch_error"))


def test_serialize_rejects_inconsistent_invalid_with_price():
    with pytest.raises(ValueError):
        _serialize_record(_invalid_record(reference_price=Decimal("1")))


# ===========================================================================
# schema failure through main -> exit 3, empty stdout (injected fake courier)
# ===========================================================================

def test_schema_failure_exit_3_empty_stdout():
    out, err = _io()

    async def fake_courier(asset, *, client, base_url):
        # float price on an OK carrier -> projection must fail
        return _ok_record(reference_price=3.5)

    af = _adapter_factory({"BTC": "1.0"})
    code = main(["--asset", "BTC"], adapter_factory=af, courier=fake_courier, out=out, err=err)
    assert code == 3
    assert out.getvalue() == ""        # empty stdout on projection failure
    assert err.getvalue() != ""        # diagnostic on stderr


# ===========================================================================
# source scan (case-insensitive) + prove default=str absent
# ===========================================================================

def test_source_scan_no_forbidden_surfaces():
    import tools.live_hl_reference_probe as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        low = fh.read().lower()
    banned = (
        "trade", "signal", "edge", "candidate", "actionable", "actionability",
        "order", "fill", "buy", "sell", "stake", "wallet", "signing", "s1",
        "scanner", "cache", "runner", "pagination", "next_cursor", "discover",
        "while", "retry", "spot", "truth", "settlement", "oracle",
    )
    for term in banned:
        assert term not in low, f"forbidden term {term!r} present in probe source"
    assert "default=str" not in low, "default=str serializer hook must be absent"
