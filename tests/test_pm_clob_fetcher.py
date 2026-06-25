"""tests/test_pm_clob_fetcher.py — TDD for isolated PM CLOB /book fetcher boundary.

fetch_clob_book is a single-token, stateless courier: given token_id + injected async http_client,
fetches one CLOB /book payload, preserves raw body text, parses JSON float-safely
(parse_float=Decimal, parse_int=Decimal — no IEEE-754 float ever enters parsed_safe_book), and
returns a structured BookFetchResult carrier. Never writes DB. Never pairs with references.
Never calls live network in tests.

First RED: module data.pm_clob_fetcher does not exist -> ImportError.
"""
import asyncio
import json
import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.pm_clob_fetcher import BookFetchResult, fetch_clob_book

_BASE = "https://clob.example.com"
_TOKEN = "tok-abc-123"
_BOOK_JSON = json.dumps({
    "asks": [{"price": "0.60", "size": "10"}],
    "bids": [{"price": "0.58", "size": "5"}],
})
# price is a JSON float literal (1e-7) so parse_float=Decimal converts it; size is an integer literal
# so parse_int=Decimal converts it. String-quoted values ("1E-7") would NOT be converted.
_TINY_JSON = '{"asks": [{"price": 1e-7, "size": 3}], "bids": []}'


# ---------------------------------------------------------------------------
# Fake client infrastructure (aiohttp-like: get() -> response; response.status;
# await response.text())
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, status: int, body_text: str, raise_on_json: bool = False):
        self.status = status
        self._body = body_text
        self._raise_on_json = raise_on_json

    async def text(self):
        return self._body

    async def json(self):
        if self._raise_on_json:
            raise RuntimeError("response.json() must NOT be called — fetcher must use response.text()")
        return json.loads(self._body)


class _FakeClient:
    def __init__(self, response: _FakeResponse):
        self._response = response

    async def get(self, url, *, params=None, timeout=None):
        return self._response


class _RaisingClient:
    """Client whose get() raises the given exception."""
    def __init__(self, exc: BaseException):
        self._exc = exc

    async def get(self, url, *, params=None, timeout=None):
        raise self._exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_no_float(obj, path="root"):
    """Recursively assert no float anywhere in obj (only Decimal / str / int / None / bool)."""
    if isinstance(obj, float):
        raise AssertionError(f"float found at {path}: {obj!r}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_float(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_no_float(v, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_success_returns_raw_body_and_decimal_parsed_book():
    """Success path: raw_body_text is the exact original string; parsed_safe_book has Decimal numerics."""
    resp = _FakeResponse(200, _BOOK_JSON)
    result = await fetch_clob_book(_TOKEN, http_client=_FakeClient(resp), base_url=_BASE)
    assert result.raw_body_text == _BOOK_JSON
    assert result.parsed_safe_book is not None
    assert result.error_code is None
    assert result.reject_reason is None
    assert result.http_status == 200
    assert result.token_id == _TOKEN
    _assert_no_float(result.parsed_safe_book)


@pytest.mark.asyncio
async def test_parse_float_and_parse_int_decimal_no_float_in_parsed():
    """Integer and scientific-notation numerics must emerge as Decimal, not float."""
    resp = _FakeResponse(200, _TINY_JSON)
    result = await fetch_clob_book(_TOKEN, http_client=_FakeClient(resp), base_url=_BASE)
    assert result.error_code is None
    _assert_no_float(result.parsed_safe_book)
    asks = result.parsed_safe_book["asks"]
    assert isinstance(asks[0]["price"], Decimal), "price '1E-7' must be Decimal"
    assert isinstance(asks[0]["size"], Decimal), "integer size 3 must be Decimal"
    # fetcher does NOT canonicalize to fixed-point; that is the writer's job


@pytest.mark.asyncio
async def test_response_json_is_not_used():
    """Fetcher must call response.text(), never response.json()."""
    resp = _FakeResponse(200, _BOOK_JSON, raise_on_json=True)
    result = await fetch_clob_book(_TOKEN, http_client=_FakeClient(resp), base_url=_BASE)
    assert result.error_code is None  # success only possible via text(), not json()


@pytest.mark.asyncio
async def test_raw_body_and_parsed_are_separate():
    """Mutating parsed_safe_book must not alter raw_body_text."""
    resp = _FakeResponse(200, _BOOK_JSON)
    result = await fetch_clob_book(_TOKEN, http_client=_FakeClient(resp), base_url=_BASE)
    original_raw = result.raw_body_text
    result.parsed_safe_book["__injected__"] = "poison"
    assert result.raw_body_text == original_raw
    assert "__injected__" not in result.raw_body_text


@pytest.mark.asyncio
async def test_http_429_returns_error_carrier():
    resp = _FakeResponse(429, '{"error":"rate_limited"}')
    result = await fetch_clob_book(_TOKEN, http_client=_FakeClient(resp), base_url=_BASE)
    assert result.error_code == "http_429"
    assert result.parsed_safe_book is None
    assert result.http_status == 429
    assert result.raw_body_text is not None  # body preserved when available


@pytest.mark.asyncio
async def test_non_200_returns_error_carrier():
    resp = _FakeResponse(503, "service unavailable")
    result = await fetch_clob_book(_TOKEN, http_client=_FakeClient(resp), base_url=_BASE)
    assert result.error_code == "non_200"
    assert result.http_status == 503
    assert result.parsed_safe_book is None


@pytest.mark.asyncio
async def test_timeout_returns_error_carrier():
    result = await fetch_clob_book(
        _TOKEN, http_client=_RaisingClient(asyncio.TimeoutError()), base_url=_BASE)
    assert result.error_code == "timeout"
    assert result.http_status is None
    assert result.raw_body_text is None
    assert result.parsed_safe_book is None


@pytest.mark.asyncio
async def test_network_error_returns_error_carrier():
    result = await fetch_clob_book(
        _TOKEN, http_client=_RaisingClient(OSError("connection refused")), base_url=_BASE)
    assert result.error_code == "network_error"
    assert result.http_status is None
    assert result.parsed_safe_book is None


@pytest.mark.asyncio
async def test_malformed_json_preserves_raw_body():
    resp = _FakeResponse(200, "not json")
    result = await fetch_clob_book(_TOKEN, http_client=_FakeClient(resp), base_url=_BASE)
    assert result.raw_body_text == "not json"
    assert result.parsed_safe_book is None
    assert result.error_code == "malformed_json"


@pytest.mark.asyncio
async def test_empty_body_returns_error_carrier():
    resp = _FakeResponse(200, "")
    result = await fetch_clob_book(_TOKEN, http_client=_FakeClient(resp), base_url=_BASE)
    assert result.raw_body_text == ""
    assert result.parsed_safe_book is None
    assert result.error_code == "empty_body"


@pytest.mark.asyncio
async def test_missing_book_sides_returns_partial_error_carrier():
    """Valid JSON dict but no asks/bids keys: parsed_safe_book preserved, error noted."""
    body = json.dumps({"market": "BTC"})
    resp = _FakeResponse(200, body)
    result = await fetch_clob_book(_TOKEN, http_client=_FakeClient(resp), base_url=_BASE)
    assert result.parsed_safe_book is not None
    assert result.error_code == "missing_book_sides"
    assert result.raw_body_text == body


@pytest.mark.asyncio
async def test_timing_fields_always_present():
    """fetch_started_at, fetch_completed_at, fetch_span_ms >= 0 on both success and failure."""
    clients = [
        _FakeClient(_FakeResponse(200, _BOOK_JSON)),
        _RaisingClient(asyncio.TimeoutError()),
    ]
    for client in clients:
        result = await fetch_clob_book(_TOKEN, http_client=client, base_url=_BASE)
        assert result.fetch_started_at is not None
        assert result.fetch_completed_at is not None
        assert result.fetch_span_ms >= 0


@pytest.mark.asyncio
async def test_venue_ts_always_missing():
    """venue_book_ts_raw=None and venue_book_ts_parse_status='missing' on success and failure."""
    clients = [
        _FakeClient(_FakeResponse(200, _BOOK_JSON)),
        _RaisingClient(asyncio.TimeoutError()),
    ]
    for client in clients:
        result = await fetch_clob_book(_TOKEN, http_client=client, base_url=_BASE)
        assert result.venue_book_ts_raw is None
        assert result.venue_book_ts_parse_status == "missing"


@pytest.mark.asyncio
async def test_programmer_errors_fail_fast():
    """Empty token_id, empty base_url, or None http_client raise ValueError immediately."""
    client = _FakeClient(_FakeResponse(200, _BOOK_JSON))
    with pytest.raises(ValueError):
        await fetch_clob_book("", http_client=client, base_url=_BASE)
    with pytest.raises(ValueError):
        await fetch_clob_book(_TOKEN, http_client=client, base_url="")
    with pytest.raises(ValueError):
        await fetch_clob_book(_TOKEN, http_client=None, base_url=_BASE)


def test_module_has_no_forbidden_scope():
    """Source-text scan ensures no forbidden surfaces in pm_clob_fetcher.py."""
    import data.pm_clob_fetcher as m
    src = open(m.__file__, "r", encoding="utf-8").read().lower()
    for banned in ("gamma", "metadata", "token_map", "proxy_reference_basket_ticks",
                   "reference_book_pairs", "stale_lag", "math.log", "implied",
                   "candidate", "actionability", "response.json"):
        assert banned not in src, f"forbidden term {banned!r} found in pm_clob_fetcher.py"
