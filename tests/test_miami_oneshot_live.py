"""tests/test_miami_oneshot_live.py — TDD for Option A live fetcher wiring.

build_live_fetchers constructs the three sync fetcher callables the committed runner core expects,
wrapping the committed async fetchers behind INJECTED network seams (fake session / fake json client).
Strike/expiry are operator-asserted (Option A). No retries, single call per wrapper, timeout cap 2.0s.
No real network in tests.

First RED: module tools.miami_oneshot_live does not exist -> ImportError.
"""
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools.miami_oneshot_runner as runner
from tools.miami_oneshot_live import build_live_fetchers, STRIKE_EXPIRY_MARKER

_BASE = "https://clob.example.com"
_NOW = "2026-06-26T17:50:00Z"
_STRIKE = 65000.0
_EXPIRY = "2026-06-26T18:00:00Z"

_YES_BOOK_JSON = json.dumps({"asks": [{"price": "0.83", "size": "50"}],
                             "bids": [{"price": "0.81", "size": "50"}]})
_NO_BOOK_JSON = json.dumps({"asks": [{"price": "0.19", "size": "150"}],
                            "bids": [{"price": "0.17", "size": "150"}]})


# ---- fake aiohttp-like session (for fetch_clob_book) ----------------------
class _FakeResp:
    def __init__(self, body):
        self.status = 200
        self._body = body

    async def text(self):
        return self._body


class _FakeSession:
    def __init__(self, counter):
        self._counter = counter

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, *, params=None, timeout=None):
        self._counter.append((params or {}).get("token_id"))
        tid = (params or {}).get("token_id")
        return _FakeResp(_YES_BOOK_JSON if tid == "YESTOK" else _NO_BOOK_JSON)


def _http_factory(counter):
    def _f():
        return _FakeSession(counter)
    return _f


# ---- fake json client (for HL reference + CLOB metadata) ------------------
def _json_factory(counter, *, price="65135.0", meta_payload=None, raise_on=None):
    if meta_payload is None:
        meta_payload = {"tokens": [{"outcome": "Up", "token_id": "YESTOK"},
                                   {"outcome": "Down", "token_id": "NOTOK"}]}

    def _f():
        async def _client(url):
            counter.append(url)
            if raise_on and raise_on in url:
                raise TimeoutError("boom")
            if "markets" in url:
                return meta_payload
            return {"price": price}   # HL adapter shape
        return _client
    return _f


def _build(**over):
    kw = dict(base_url=_BASE, operator_strike=_STRIKE, operator_expiry=_EXPIRY, timeout_s=1.0)
    kw.update(over)
    return build_live_fetchers(**kw)


# ===========================================================================
# timeout cap / default validation
# ===========================================================================

def test_timeout_over_cap_raises():
    with pytest.raises(ValueError):
        _build(timeout_s=2.5)


def test_timeout_non_positive_raises():
    with pytest.raises(ValueError):
        _build(timeout_s=0)


def test_default_timeout_builds_three_callables():
    http_c, json_c = [], []
    bf, rf, mf = _build(http_client_factory=_http_factory(http_c),
                        json_client_factory=_json_factory(json_c))
    assert callable(bf) and callable(rf) and callable(mf)


# ===========================================================================
# book fetcher
# ===========================================================================

def test_book_fetcher_adapts_and_single_call():
    http_c, json_c = [], []
    bf, rf, mf = _build(http_client_factory=_http_factory(http_c),
                        json_client_factory=_json_factory(json_c))
    res = bf("YESTOK")
    assert res["error_code"] is None
    assert res["parsed_safe_book"]["asks"][0]["price"] is not None
    assert http_c == ["YESTOK"]   # exactly one call, no retry


# ===========================================================================
# reference fetcher (degraded preserved: no source_event_ts)
# ===========================================================================

def test_reference_fetcher_returns_price_no_venue_ts():
    http_c, json_c = [], []
    bf, rf, mf = _build(http_client_factory=_http_factory(http_c),
                        json_client_factory=_json_factory(json_c))
    res = rf("BTC")
    assert res["error_code"] is None
    assert float(res["price"]) == pytest.approx(65135.0)
    assert "source_event_ts" not in res          # stays degraded
    assert len([u for u in json_c if "markets" not in u]) == 1   # single HL call


# ===========================================================================
# metadata fetcher (Option A: operator-asserted strike/expiry)
# ===========================================================================

def test_metadata_fetcher_tokens_from_venue_strike_expiry_operator_asserted():
    http_c, json_c = [], []
    bf, rf, mf = _build(http_client_factory=_http_factory(http_c),
                        json_client_factory=_json_factory(json_c))
    res = mf("0xCID")
    assert res["error_code"] is None
    assert res["tokens"] == [{"outcome": "Up", "token_id": "YESTOK"},
                             {"outcome": "Down", "token_id": "NOTOK"}]
    assert res["strike"] == _STRIKE and res["expiry"] == _EXPIRY   # operator-asserted pass-through
    assert len([u for u in json_c if "markets" in u]) == 1   # single metadata call


def test_metadata_fetcher_malformed_fail_closed():
    http_c, json_c = [], []
    bf, rf, mf = _build(http_client_factory=_http_factory(http_c),
                        json_client_factory=_json_factory(json_c, meta_payload={"no": "tokens"}))
    res = mf("0xCID")
    assert res["error_code"] is not None and res["tokens"] is None


# ===========================================================================
# end-to-end into the committed runner core
# ===========================================================================

def _argv(**over):
    base = {
        "--yes-token-id": "YESTOK", "--no-token-id": "NOTOK", "--condition-id": "0xCID",
        "--asset": "BTC", "--timeframe": "1h", "--strike": str(_STRIKE),
        "--expiry": _EXPIRY, "--intended-stake-usd": "5.0",
        "--base-url": _BASE, "--fee-cost": "0.01",
    }
    base.update(over)
    argv = []
    for k, v in base.items():
        argv += [k, str(v)]
    return argv


def test_end_to_end_live_wiring_into_runner_main():
    http_c, json_c = [], []
    bf, rf, mf = _build(http_client_factory=_http_factory(http_c),
                        json_client_factory=_json_factory(json_c))
    out = io.StringIO()
    code = runner.main(_argv(), book_fetcher=bf, reference_fetcher=rf, metadata_fetcher=mf,
                       now_fn=lambda: _NOW, out=out,
                       extra_notes_markers=[STRIKE_EXPIRY_MARKER])
    text = out.getvalue()
    assert code == 0
    assert "basis_risk_accepted_hyperliquid_vs_settlement_oracle" in text
    assert "degraded_ts_override" in text
    assert "operator_fee_cost=0.01" in text
    assert STRIKE_EXPIRY_MARKER in text


def test_end_to_end_single_call_per_fetcher():
    http_c, json_c = [], []
    bf, rf, mf = _build(http_client_factory=_http_factory(http_c),
                        json_client_factory=_json_factory(json_c))
    out = io.StringIO()
    runner.main(_argv(), book_fetcher=bf, reference_fetcher=rf, metadata_fetcher=mf,
                now_fn=lambda: _NOW, out=out, extra_notes_markers=[STRIKE_EXPIRY_MARKER])
    assert http_c == ["YESTOK", "NOTOK"]                       # 2 book calls, no retry
    assert len([u for u in json_c if "markets" not in u]) == 1  # 1 HL call
    assert len([u for u in json_c if "markets" in u]) == 1      # 1 metadata call


# ===========================================================================
# source scan
# ===========================================================================

def test_source_scan_no_forbidden_surfaces():
    import tools.miami_oneshot_live as m
    src = open(m.__file__, "r", encoding="utf-8").read().lower()
    for banned in ("place_order", "submit_order", "order_placement", "wallet", "signing",
                   "hedge", "scheduler", " cron", "while true", "s1_storage", "scanner",
                   "discovery", "retry"):
        assert banned not in src, f"forbidden term {banned!r} present"
