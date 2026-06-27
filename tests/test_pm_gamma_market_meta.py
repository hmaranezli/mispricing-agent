"""tests/test_pm_gamma_market_meta.py — TDD for the Gamma metadata courier.

fetch_gamma_market is an async courier over an INJECTED client (no real network). It fetches one
Polymarket market metadata document by slug and returns a plain machine carrier with venue metadata
only (no human/oracle text, no strike, no trading semantics). Programmer-contract violations raise;
venue/data failures return a structured VENUE_METADATA_INVALID carrier with an exact gamma_* code.

NOTE: the event_start >= end_date row uses error_code 'gamma_time_inversion' (not 'gamma_time_order')
because the authorized source-scan forbids the substring 'order' case-insensitively.

First RED: module data.pm_gamma_market_meta does not exist -> ImportError.
"""
import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.pm_gamma_market_meta import fetch_gamma_market

_CID = "0x1260dda542bb5fb18a6e4ffb74468d3983dbb0ceb7faa09cf2285e1fc53d3020"
_SLUG = "bitcoin-up-or-down-june-26-2026-3pm-et"
_BASE = "https://gamma-api.example.com"
_EVENT = "2026-06-26T19:00:00Z"
_END = "2026-06-26T20:00:00Z"
_EVENT_MS = 1782500400000
_END_MS = 1782504000000


def _client(payload, *, counter=None, raise_exc=None):
    async def _c(url):
        if counter is not None:
            counter.append(url)
        if raise_exc is not None:
            raise raise_exc
        return payload
    return _c


def _doc(**over):
    d = {
        "conditionId": _CID,
        "outcomes": json.dumps(["Up", "Down"]),
        "clobTokenIds": json.dumps(["YESTOK", "NOTOK"]),
        "eventStartTime": _EVENT,
        "endDate": _END,
        # human / oracle text intentionally present in the payload (must NOT be echoed):
        "question": "Bitcoin Up or Down - June 26, 3PM ET",
        "slug": _SLUG,
        "description": "resolves using the BTC/USDT open price 59668.01 USD per 1H candle",
        "resolutionSource": "https://www.binance.com/en/trade/BTC_USDT",
        "tags": ["crypto", "bitcoin"],
    }
    d.update(over)
    return d


def _run(payload, **kw):
    counter = kw.pop("counter", None)
    raise_exc = kw.pop("raise_exc", None)
    client = _client(payload, counter=counter, raise_exc=raise_exc)
    return asyncio.run(fetch_gamma_market(_SLUG, client=client, base_url=_BASE, **kw))


# ===========================================================================
# fail-fast: programmer-contract violations RAISE (never gamma_* carrier)
# ===========================================================================

def test_bad_slug_type_raises():
    with pytest.raises((TypeError, ValueError)):
        asyncio.run(fetch_gamma_market(123, client=_client([_doc()]), base_url=_BASE))


def test_empty_slug_raises():
    with pytest.raises((TypeError, ValueError)):
        asyncio.run(fetch_gamma_market("", client=_client([_doc()]), base_url=_BASE))


def test_bad_base_url_raises():
    with pytest.raises((TypeError, ValueError)):
        asyncio.run(fetch_gamma_market(_SLUG, client=_client([_doc()]), base_url=""))


def test_non_callable_client_raises():
    with pytest.raises(TypeError):
        asyncio.run(fetch_gamma_market(_SLUG, client=None, base_url=_BASE))


def test_bad_expected_condition_id_type_raises():
    with pytest.raises(TypeError):
        asyncio.run(fetch_gamma_market(_SLUG, client=_client([_doc()]),
                                       base_url=_BASE, expected_condition_id=123))


# ===========================================================================
# happy path
# ===========================================================================

def test_happy_list_of_one():
    r = _run([_doc()])
    assert r["status"] == "VENUE_METADATA_OK"
    assert r["error_code"] is None
    assert r["condition_id"] == _CID
    assert r["outcomes"] == ["Up", "Down"]
    assert r["clob_token_ids"] == ["YESTOK", "NOTOK"]
    assert r["outcome_token_map"] == [
        {"outcome": "Up", "token_id": "YESTOK"},
        {"outcome": "Down", "token_id": "NOTOK"},
    ]
    assert r["event_start_time_utc"] == _EVENT and r["event_start_time_ms"] == _EVENT_MS
    assert r["end_date_utc"] == _END and r["end_date_ms"] == _END_MS


def test_happy_dict_form():
    assert _run(_doc())["status"] == "VENUE_METADATA_OK"


def test_expected_condition_id_match():
    assert _run([_doc()], expected_condition_id=_CID)["status"] == "VENUE_METADATA_OK"


def test_expected_condition_id_omitted_ok():
    assert _run([_doc()])["status"] == "VENUE_METADATA_OK"


def test_native_list_fields_also_ok():
    r = _run([_doc(outcomes=["Up", "Down"], clobTokenIds=["YESTOK", "NOTOK"])])
    assert r["status"] == "VENUE_METADATA_OK"
    assert r["clob_token_ids"] == ["YESTOK", "NOTOK"]


def test_no_human_or_oracle_text_keys_in_output():
    r = _run([_doc()])
    for k in ("question", "title", "slug", "description", "tags",
              "question_audit_hint_only", "resolution_source"):
        assert k not in r


def test_no_strike_parsed_from_text():
    r = _run([_doc(description="open price 59668.01 USD", question="... 59,668 ...")])
    assert "strike" not in r
    flat = str(r)
    assert "59668" not in flat and "59,668" not in flat


# ===========================================================================
# fail-closed venue/data matrix (one per row)
# ===========================================================================

def test_fetch_error():
    r = _run([_doc()], raise_exc=TimeoutError("boom"))
    assert r["status"] == "VENUE_METADATA_INVALID" and r["error_code"] == "gamma_fetch_error"


def test_malformed_json_non_dict_list():
    assert _run("not-json")["error_code"] == "gamma_malformed_json"


def test_empty():
    assert _run([])["error_code"] == "gamma_empty"


def test_multiple_docs():
    assert _run([_doc(), _doc()])["error_code"] == "gamma_multiple_docs"


def test_missing_condition_id():
    d = _doc()
    del d["conditionId"]
    assert _run([d])["error_code"] == "gamma_missing_condition_id"


def test_condition_id_mismatch():
    assert _run([_doc()], expected_condition_id="0xDEAD")["error_code"] == "gamma_condition_id_mismatch"


def test_malformed_outcomes_undecodable():
    assert _run([_doc(outcomes="{not json")])["error_code"] == "gamma_malformed_outcomes"


def test_missing_outcomes():
    d = _doc()
    del d["outcomes"]
    assert _run([d])["error_code"] == "gamma_malformed_outcomes"


def test_outcomes_count():
    assert _run([_doc(outcomes=json.dumps(["Up", "Down", "Side"]))])["error_code"] == "gamma_outcomes_count"


def test_malformed_tokens_undecodable():
    assert _run([_doc(clobTokenIds="{bad")])["error_code"] == "gamma_malformed_tokens"


def test_missing_tokens():
    d = _doc()
    del d["clobTokenIds"]
    assert _run([d])["error_code"] == "gamma_malformed_tokens"


def test_token_count_mismatch():
    assert _run([_doc(clobTokenIds=json.dumps(["ONLYONE"]))])["error_code"] == "gamma_token_count_mismatch"


def test_token_align_none():
    assert _run([_doc(clobTokenIds=json.dumps(["YESTOK", None]))])["error_code"] == "gamma_token_align"


def test_token_align_empty():
    assert _run([_doc(clobTokenIds=json.dumps(["YESTOK", ""]))])["error_code"] == "gamma_token_align"


def test_missing_event_start():
    d = _doc()
    del d["eventStartTime"]
    assert _run([d])["error_code"] == "gamma_missing_event_start"


def test_missing_end_date():
    d = _doc()
    del d["endDate"]
    assert _run([d])["error_code"] == "gamma_missing_end_date"


def test_bad_timestamp_offset_plus0000():
    assert _run([_doc(eventStartTime="2026-06-26T19:00:00+00:00")])["error_code"] == "gamma_bad_timestamp"


def test_bad_timestamp_naive():
    assert _run([_doc(eventStartTime="2026-06-26T19:00:00")])["error_code"] == "gamma_bad_timestamp"


def test_bad_timestamp_nonz_offset():
    assert _run([_doc(endDate="2026-06-26T20:00:00+01:00")])["error_code"] == "gamma_bad_timestamp"


def test_time_inversion():
    assert _run([_doc(eventStartTime=_END, endDate=_EVENT)])["error_code"] == "gamma_time_inversion"


# ===========================================================================
# single-call + invalid carrier has no forbidden keys
# ===========================================================================

def test_single_call_no_retry():
    c = []
    _run([_doc()], counter=c)
    assert len(c) == 1


def test_invalid_carrier_has_no_text_keys():
    r = _run([])  # gamma_empty
    for k in ("question", "title", "slug", "description", "tags",
              "question_audit_hint_only", "resolution_source", "strike"):
        assert k not in r
    assert r["status"] == "VENUE_METADATA_INVALID"


# ===========================================================================
# source scan (case-insensitive): no trading/actionability/infra/network surface
# ===========================================================================

def test_source_scan_no_forbidden_surfaces():
    import data.pm_gamma_market_meta as m
    with open(m.__file__, "r", encoding="utf-8") as fh:
        low = fh.read().lower()
    banned = (
        "trade", "signal", "edge", "candidate", "actionable", "actionability",
        "order", "fill", "buy", "sell", "stake", "wallet", "signing", "s1",
        "scanner", "cache", "runner",
        "aiohttp", "requests", "urllib", "socket", "httpx",
        "discover", "pagination", "next_cursor", "while",
    )
    for term in banned:
        assert term not in low, f"forbidden term {term!r} present in courier source"
