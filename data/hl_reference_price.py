"""Hyperliquid reference-price courier. Injected POST client, one call, fail-closed; Decimal price.

This source is a reference price (Hyperliquid allMids perp mid), never a true spot price.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

_OK = "VENUE_REFERENCE_OK"
_INVALID = "VENUE_REFERENCE_INVALID"
_SOURCE = "hyperliquid_all_mids_perp"


def _reject(asset, code):
    return {
        "asset": asset,
        "reference_price": None,
        "status": _INVALID,
        "error_code": code,
        "reference_source": _SOURCE,
    }


async def fetch_hl_reference_price(asset, *, client, base_url) -> dict:
    # ---- programmer-contract checks: fail-fast (never an hl_* carrier) ----
    if not isinstance(asset, str):
        raise TypeError("asset must be a str")
    if not asset or asset != asset.strip():
        raise ValueError("asset must be non-empty and whitespace-clean")
    if not isinstance(base_url, str):
        raise TypeError("base_url must be a str")
    if not base_url or base_url != base_url.strip():
        raise ValueError("base_url must be non-empty and whitespace-clean")
    if not callable(client):
        raise TypeError("client must be callable")

    normalized_base_url = base_url.rstrip("/")
    if not normalized_base_url:
        raise ValueError("base_url must contain a non-slash value")

    endpoint = f"{normalized_base_url}/info"

    # ---- one venue call (POST seam); this try wraps ONLY the awaited client op ----
    try:
        payload = await client(endpoint, json_body={"type": "allMids"})
    except Exception:
        return _reject(asset, "hl_fetch_error")

    # ---- everything below is OUTSIDE the try: never mislabeled as hl_fetch_error ----
    if not isinstance(payload, dict):
        return _reject(asset, "hl_malformed_json")
    if asset not in payload:
        return _reject(asset, "hl_asset_not_found")

    raw_price = payload[asset]
    if not isinstance(raw_price, str):          # allMids values are contractually strings
        return _reject(asset, "hl_bad_price")
    try:
        price = Decimal(raw_price)
    except InvalidOperation:
        return _reject(asset, "hl_bad_price")
    if price.is_nan() or price.is_infinite() or price <= 0:
        return _reject(asset, "hl_bad_price")

    return {
        "asset": asset,
        "reference_price": price,
        "status": _OK,
        "error_code": None,
        "reference_source": _SOURCE,
    }
