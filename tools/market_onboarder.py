"""Market onboarder: wires Gamma metadata, Binance candle-open, and support classification into one
verified onboarding record. Injected clients, fail-closed short-circuits, no hot-path integration."""
from __future__ import annotations

from analysis.market_support_classifier import classify_market_support
from data.pm_gamma_market_meta import fetch_gamma_market
from data.binance_candle_oracle import fetch_binance_candle_open

_OK = "ONBOARDING_OK"
_INVALID = "ONBOARDING_INVALID"
_CLASSIFIER_OK_STATUS = "CACHE_READY"


def _record(*, slug, asset, interval, condition_id, gamma, binance, classification,
            onboarding_status, onboarding_error_code) -> dict:
    return {
        "slug": slug,
        "condition_id": condition_id,
        "asset": asset,
        "interval": interval,
        "gamma": gamma,
        "binance": binance,
        "classification": classification,
        "onboarding_status": onboarding_status,
        "onboarding_error_code": onboarding_error_code,
    }


async def onboard_market(*, slug, asset, interval, now_ms, gamma_client, binance_client,
                         gamma_base_url, binance_base_url, asset_allowlist,
                         reference_source_supported, asset_symbol_map,
                         expected_condition_id=None) -> dict:
    # ---- step 1: Gamma metadata ----
    gamma = await fetch_gamma_market(slug, client=gamma_client, base_url=gamma_base_url,
                                     expected_condition_id=expected_condition_id)
    if gamma["status"] != "VENUE_METADATA_OK":
        return _record(slug=slug, asset=asset, interval=interval,
                       condition_id=gamma.get("condition_id"), gamma=gamma, binance=None,
                       classification=None, onboarding_status=_INVALID,
                       onboarding_error_code=gamma["error_code"])

    # ---- step 2: Binance candle-open strike ----
    symbol = asset_symbol_map[asset]
    binance = await fetch_binance_candle_open(symbol, interval, gamma["event_start_time_ms"],
                                              now_ms, client=binance_client,
                                              base_url=binance_base_url)
    if binance["status"] != "VENUE_STRIKE_OK":
        return _record(slug=slug, asset=asset, interval=interval,
                       condition_id=gamma["condition_id"], gamma=gamma, binance=binance,
                       classification=None, onboarding_status=_INVALID,
                       onboarding_error_code=binance["error_code"])

    # ---- step 3: support classification (adapters; no module changes) ----
    token_map = gamma["outcome_token_map"]
    gamma_meta = {
        "asset": asset,
        "condition_id": gamma["condition_id"],
        "yes_token_id": token_map[0]["token_id"],
        "no_token_id": token_map[1]["token_id"],
        "outcomes": gamma["outcomes"],
        "event_start_time_ms": gamma["event_start_time_ms"],
        "end_date_ms": gamma["end_date_ms"],
    }
    strike_result = {
        "status": "VENUE_VERIFIED" if binance["status"] == "VENUE_STRIKE_OK" else binance["status"],
        "strike": binance["strike_price"],
        "open_time_ms": binance["returned_open_time_ms"],
    }
    support = {"asset_allowlist": asset_allowlist,
               "reference_source_supported": reference_source_supported}
    status = classify_market_support(gamma_meta=gamma_meta, strike_result=strike_result,
                                     support=support, now_ms=now_ms)
    classification = {"status": status}

    if status == _CLASSIFIER_OK_STATUS:
        return _record(slug=slug, asset=asset, interval=interval,
                       condition_id=gamma["condition_id"], gamma=gamma, binance=binance,
                       classification=classification, onboarding_status=_OK,
                       onboarding_error_code=None)
    return _record(slug=slug, asset=asset, interval=interval,
                   condition_id=gamma["condition_id"], gamma=gamma, binance=binance,
                   classification=classification, onboarding_status=_INVALID,
                   onboarding_error_code="classifier_" + status.lower())
