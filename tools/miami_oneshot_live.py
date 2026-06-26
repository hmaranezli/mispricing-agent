"""tools/miami_oneshot_live.py — Option A live fetcher wiring for the one-shot Miami runner.

Constructs the three SYNC fetcher callables the committed runner core expects, wrapping the committed
async fetchers behind injected network seams. Policy: zero re-attempts, no backoff, no cache; each
wrapper calls its underlying fetch exactly once; ``timeout_s`` defaults to 1.0s with an absolute cap
of 2.0s.

Option A: token<->outcome is venue-verified via read-only CLOB /markets/{condition_id}; strike and
expiry are OPERATOR-ASSERTED for this read-only phase (no trading, trade_allowed stays False). The
audit marker ``strike_expiry_operator_asserted_not_venue_verified`` is added to the final row notes by
the caller via the runner's ``extra_notes_markers`` hook. Venue-verified strike/expiry (e.g. a Gamma
probe) is a STRICT future gate before any Paper/Canary/Live/automated phase.

The network seams (``http_client_factory`` / ``json_client_factory``) are injected so tests run fully
offline. The production default factories (lazy aiohttp) form the only live boundary and are never
exercised by tests.
"""
from __future__ import annotations

import asyncio

from data.pm_clob_fetcher import fetch_clob_book
from data.public_spot_fetchers import fetch_hyperliquid_perp
from data.pm_clob_market_meta import fetch_clob_market

TIMEOUT_DEFAULT_S = 1.0
TIMEOUT_CAP_S = 2.0
STRIKE_EXPIRY_MARKER = "strike_expiry_operator_asserted_not_venue_verified"


def _default_http_client_factory():  # pragma: no cover - live boundary, never run in tests
    import aiohttp
    return lambda: aiohttp.ClientSession()


def _default_json_client_factory(timeout_s):  # pragma: no cover - live boundary
    import aiohttp

    def _factory():
        async def _client(url):
            timeout = aiohttp.ClientTimeout(total=timeout_s)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.get(url) as r:
                    return await r.json()
        return _client
    return _factory


def build_live_fetchers(*, base_url, operator_strike, operator_expiry,
                        timeout_s=TIMEOUT_DEFAULT_S,
                        http_client_factory=None, json_client_factory=None):
    """Return (book_fetcher, reference_fetcher, metadata_fetcher) sync callables. Single-shot each."""
    if timeout_s <= 0 or timeout_s > TIMEOUT_CAP_S:
        raise ValueError(f"timeout_s must be in (0, {TIMEOUT_CAP_S}], got {timeout_s}")

    http_client_factory = http_client_factory or _default_http_client_factory()
    json_client_factory = json_client_factory or _default_json_client_factory(timeout_s)

    def book_fetcher(token_id):
        async def _go():
            async with http_client_factory() as http:
                return await fetch_clob_book(token_id, http_client=http,
                                             base_url=base_url, timeout_s=timeout_s)
        res = asyncio.run(_go())
        return {"parsed_safe_book": res.parsed_safe_book, "error_code": res.error_code}

    def reference_fetcher(asset):
        tick = asyncio.run(fetch_hyperliquid_perp(asset, client=json_client_factory()))
        if tick.get("reject_reason"):
            return {"price": None, "error_code": tick["reject_reason"]}
        return {"price": float(tick["price_decimal_text"]), "error_code": None}

    def metadata_fetcher(condition_id):
        res = asyncio.run(fetch_clob_market(condition_id, client=json_client_factory(),
                                            base_url=base_url))
        if res.get("error_code"):
            return {"tokens": None, "strike": None, "expiry": None, "error_code": res["error_code"]}
        # Option A: token<->outcome venue-verified; strike/expiry operator-asserted pass-through.
        return {"tokens": res["tokens"], "strike": operator_strike, "expiry": operator_expiry,
                "error_code": None}

    return book_fetcher, reference_fetcher, metadata_fetcher


if __name__ == "__main__":  # pragma: no cover - live boundary
    import sys
    import tools.miami_oneshot_runner as runner

    pre = runner.build_arg_parser().parse_args()
    bf, rf, mf = build_live_fetchers(base_url=pre.base_url, operator_strike=pre.strike,
                                     operator_expiry=pre.expiry,
                                     timeout_s=min(TIMEOUT_DEFAULT_S, TIMEOUT_CAP_S))
    raise SystemExit(runner.main(book_fetcher=bf, reference_fetcher=rf, metadata_fetcher=mf,
                                 extra_notes_markers=[STRIKE_EXPIRY_MARKER], out=sys.stdout))
