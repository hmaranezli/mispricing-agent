"""data/pm_clob_market_meta.py — read-only CLOB /markets/{condition_id} metadata fetcher.

One call only (no second attempt, no backoff, no cache): given an injected async
``client(url) -> dict`` and a base url, fetches one market metadata document and extracts ONLY the
token<->outcome mapping. Returns a structured carrier ``{"tokens": [...]|None, "error_code": None|str}``
instead of raising, so a degraded/malformed venue response is evidence, not a crash. This module
computes nothing and exposes no order/trade surface — it is a courier for the outcome mapping used as
the token-swap safety pin in the snapshot assembler's cross-check.
"""
from __future__ import annotations


async def fetch_clob_market(condition_id: str, *, client, base_url: str) -> dict:
    """Fetch one CLOB market document; return {'tokens', 'error_code'}. Single call, fail-closed."""
    url = f"{base_url.rstrip('/')}/markets/{condition_id}"
    try:
        payload = await client(url)
    except Exception:
        return {"tokens": None, "error_code": "clob_market_fetch_error"}

    if not isinstance(payload, dict):
        return {"tokens": None, "error_code": "clob_market_malformed_json"}
    raw = payload.get("tokens")
    if not isinstance(raw, list) or len(raw) < 2:
        return {"tokens": None, "error_code": "clob_market_malformed_json"}

    tokens = []
    for t in raw:
        if not isinstance(t, dict) or "outcome" not in t or "token_id" not in t:
            return {"tokens": None, "error_code": "clob_market_malformed_json"}
        tokens.append({"outcome": t["outcome"], "token_id": str(t["token_id"])})
    return {"tokens": tokens, "error_code": None}
