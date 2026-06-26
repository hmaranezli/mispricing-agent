"""tests/test_pm_clob_market_meta.py — TDD for read-only CLOB /markets/{condition_id} metadata fetcher.

Single-shot, zero-retry, injected async ``client(url)->dict``. Extracts token<->outcome mapping only;
returns a structured carrier with ``error_code`` instead of raising. No network in tests.

First RED: module data.pm_clob_market_meta does not exist -> ImportError.
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.pm_clob_market_meta import fetch_clob_market

_BASE = "https://clob.example.com"
_CID = "0xCID"


def _client(payload=None, exc=None):
    calls = []

    async def _c(url):
        calls.append(url)
        if exc is not None:
            raise exc
        return payload

    _c.calls = calls
    return _c


def _run(client):
    return asyncio.run(fetch_clob_market(_CID, client=client, base_url=_BASE))


def test_success_extracts_token_outcome_mapping():
    c = _client({"tokens": [{"outcome": "Up", "token_id": 111},
                            {"outcome": "Down", "token_id": 222}]})
    res = _run(c)
    assert res["error_code"] is None
    assert res["tokens"] == [{"outcome": "Up", "token_id": "111"},
                             {"outcome": "Down", "token_id": "222"}]
    assert c.calls == [f"{_BASE}/markets/{_CID}"]   # single call, correct url


def test_single_call_no_retry_on_success():
    c = _client({"tokens": [{"outcome": "Up", "token_id": "1"}, {"outcome": "Down", "token_id": "2"}]})
    _run(c)
    assert len(c.calls) == 1


def test_client_exception_fail_closed():
    c = _client(exc=TimeoutError("boom"))
    res = _run(c)
    assert res["error_code"] is not None and res["tokens"] is None
    assert len(c.calls) == 1   # no retry


def test_missing_tokens_malformed():
    res = _run(_client({"question": "BTC up?"}))
    assert res["error_code"] is not None and res["tokens"] is None


def test_too_few_tokens_malformed():
    res = _run(_client({"tokens": [{"outcome": "Up", "token_id": "1"}]}))
    assert res["error_code"] is not None


def test_token_missing_fields_malformed():
    res = _run(_client({"tokens": [{"outcome": "Up"}, {"outcome": "Down", "token_id": "2"}]}))
    assert res["error_code"] is not None


def test_non_dict_payload_malformed():
    res = _run(_client(["not", "a", "dict"]))
    assert res["error_code"] is not None


def test_source_scan_no_forbidden_surfaces():
    import data.pm_clob_market_meta as m
    src = open(m.__file__, "r", encoding="utf-8").read().lower()
    for banned in ("place_order", "submit_order", "wallet", "signing", "hedge",
                   "scheduler", " cron", "while true", "retry"):
        assert banned not in src, f"forbidden term {banned!r} present"
