"""Gamma market metadata courier. Injected client, one call, fail-closed; no human text echoed."""
from __future__ import annotations

import json
from datetime import datetime, timezone

_OK = "VENUE_METADATA_OK"
_INVALID = "VENUE_METADATA_INVALID"


def _invalid(code: str) -> dict:
    return {
        "condition_id": None,
        "outcomes": None,
        "clob_token_ids": None,
        "outcome_token_map": None,
        "event_start_time_utc": None,
        "event_start_time_ms": None,
        "end_date_utc": None,
        "end_date_ms": None,
        "status": _INVALID,
        "error_code": code,
    }


def _decode_list(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            return None
        return parsed if isinstance(parsed, list) else None
    return None


def _utc_z_to_ms(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


async def fetch_gamma_market(slug, *, client, base_url, expected_condition_id=None) -> dict:
    # ---- programmer-contract checks: fail-fast (never a gamma_* carrier) ----
    if not isinstance(slug, str):
        raise TypeError("slug must be a str")
    if not slug:
        raise ValueError("slug must be non-empty")
    if not isinstance(base_url, str):
        raise TypeError("base_url must be a str")
    if not base_url:
        raise ValueError("base_url must be non-empty")
    if expected_condition_id is not None and not isinstance(expected_condition_id, str):
        raise TypeError("expected_condition_id must be a str or None")
    if not callable(client):
        raise TypeError("client must be callable")

    url = base_url.rstrip("/") + "/markets?slug=" + slug

    # ---- one venue call: venue/data exceptions -> structured invalid carrier ----
    try:
        payload = await client(url)
    except Exception:
        return _invalid("gamma_fetch_error")

    if isinstance(payload, list):
        if len(payload) == 0:
            return _invalid("gamma_empty")
        if len(payload) > 1:
            return _invalid("gamma_multiple_docs")
        doc = payload[0]
    elif isinstance(payload, dict):
        doc = payload
    else:
        return _invalid("gamma_malformed_json")
    if not isinstance(doc, dict):
        return _invalid("gamma_malformed_json")

    cid = doc.get("conditionId")
    if not isinstance(cid, str) or not cid:
        return _invalid("gamma_missing_condition_id")
    if expected_condition_id is not None and expected_condition_id != cid:
        return _invalid("gamma_condition_id_mismatch")

    outcomes = _decode_list(doc.get("outcomes"))
    if outcomes is None:
        return _invalid("gamma_malformed_outcomes")
    tokens = _decode_list(doc.get("clobTokenIds"))
    if tokens is None:
        return _invalid("gamma_malformed_tokens")
    if len(outcomes) != 2:
        return _invalid("gamma_outcomes_count")
    if len(tokens) != len(outcomes):
        return _invalid("gamma_token_count_mismatch")

    mapping = []
    normalized_tokens = []
    for outcome, token in zip(outcomes, tokens):
        if not isinstance(outcome, str) or not outcome:
            return _invalid("gamma_token_align")
        if token is None:
            return _invalid("gamma_token_align")
        token_text = str(token)
        if not token_text:
            return _invalid("gamma_token_align")
        normalized_tokens.append(token_text)
        mapping.append({"outcome": outcome, "token_id": token_text})

    raw_event = doc.get("eventStartTime")
    if raw_event is None:
        return _invalid("gamma_missing_event_start")
    raw_end = doc.get("endDate")
    if raw_end is None:
        return _invalid("gamma_missing_end_date")

    event_ms = _utc_z_to_ms(raw_event)
    if event_ms is None:
        return _invalid("gamma_bad_timestamp")
    end_ms = _utc_z_to_ms(raw_end)
    if end_ms is None:
        return _invalid("gamma_bad_timestamp")
    if event_ms >= end_ms:
        return _invalid("gamma_time_inversion")

    return {
        "condition_id": cid,
        "outcomes": list(outcomes),
        "clob_token_ids": normalized_tokens,
        "outcome_token_map": mapping,
        "event_start_time_utc": raw_event,
        "event_start_time_ms": event_ms,
        "end_date_utc": raw_end,
        "end_date_ms": end_ms,
        "status": _OK,
        "error_code": None,
    }
