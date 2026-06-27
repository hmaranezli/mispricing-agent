"""Standalone live Hyperliquid reference-price diagnostic probe. allMids perp reference leg.

Live boundary: this file owns the real aiohttp wiring and injects an async adapter into the
UNCHANGED data.hl_reference_price courier. Terminal output only; nothing is persisted. This is a
read-only reference leg, never a settled or authoritative price.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from decimal import Decimal

from data.hl_reference_price import fetch_hl_reference_price

_BASE_URL = "https://api.hyperliquid.xyz"
_POST_BODY = {"type": "allMids"}
_TIMEOUT_CAP_S = 2.0
_SOURCE = "hyperliquid_all_mids_perp"
_REQUIRED_KEYS = frozenset({"asset", "reference_price", "status", "error_code", "reference_source"})
_INVALID_CODES = frozenset({"hl_fetch_error", "hl_malformed_json", "hl_asset_not_found", "hl_bad_price"})


def _make_adapter(timeout_s, *, session_factory, timeout_factory):
    async def client(url, *, json_body):
        timeout = timeout_factory(total=timeout_s)
        session = session_factory(timeout=timeout)
        async with session as active:
            async with active.post(url, json=json_body) as resp:
                resp.raise_for_status()
                return await resp.json()
    return client


def _default_adapter_factory(timeout_s):
    import aiohttp
    return _make_adapter(timeout_s, session_factory=aiohttp.ClientSession,
                         timeout_factory=aiohttp.ClientTimeout)


def _serialize_record(record) -> str:
    if not isinstance(record, dict):
        raise TypeError("record must be a dict")
    if frozenset(record.keys()) != _REQUIRED_KEYS:
        raise ValueError("record key set mismatch")
    asset = record["asset"]
    if not isinstance(asset, str) or not asset or asset != asset.strip():
        raise ValueError("asset must be a non-empty whitespace-clean str")
    if record["reference_source"] != _SOURCE:
        raise ValueError("reference_source mismatch")

    status = record["status"]
    price = record["reference_price"]
    error_code = record["error_code"]

    if status == "VENUE_REFERENCE_OK":
        if not isinstance(price, Decimal):
            raise ValueError("OK reference_price must be Decimal")
        if price.is_nan() or price.is_infinite() or price <= 0:
            raise ValueError("OK reference_price must be finite and > 0")
        if error_code is not None:
            raise ValueError("OK error_code must be None")
        projected = {"asset": asset, "reference_price": format(price, "f"),
                     "status": status, "error_code": None, "reference_source": _SOURCE}
    elif status == "VENUE_REFERENCE_INVALID":
        if price is not None:
            raise ValueError("INVALID reference_price must be None")
        if error_code not in _INVALID_CODES:
            raise ValueError("INVALID error_code unknown")
        projected = {"asset": asset, "reference_price": None,
                     "status": status, "error_code": error_code, "reference_source": _SOURCE}
    else:
        raise ValueError("unknown status")

    return json.dumps(projected, sort_keys=True, separators=(",", ":"))


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools.live_hl_reference_probe",
        description="N=1 read-only Hyperliquid reference-price diagnostic (perp reference leg).")
    p.add_argument("--asset", default="BTC")
    p.add_argument("--timeout-s", type=float, default=2.0)
    return p


def main(argv=None, *, adapter_factory=None, courier=None, out=None, err=None) -> int:
    out = out if out is not None else sys.stdout
    err = err if err is not None else sys.stderr
    adapter_factory = adapter_factory or _default_adapter_factory
    courier = courier or fetch_hl_reference_price

    parser = build_arg_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    asset = args.asset
    if not isinstance(asset, str) or not asset or asset != asset.strip():
        print("validation error: --asset must be a non-empty whitespace-clean str", file=err)
        return 2
    timeout_s = args.timeout_s
    if (not isinstance(timeout_s, float) or not math.isfinite(timeout_s)
            or not (0 < timeout_s <= _TIMEOUT_CAP_S)):
        print(f"validation error: --timeout-s must be finite and in (0, {_TIMEOUT_CAP_S}]", file=err)
        return 2

    try:
        adapter = adapter_factory(timeout_s)
        record = asyncio.run(courier(asset, client=adapter, base_url=_BASE_URL))
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        raise
    except Exception as e:
        print(f"internal error: {e!r}", file=err)
        return 3

    try:
        line = _serialize_record(record)
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        raise
    except Exception as e:
        print(f"projection error: {e!r}", file=err)
        return 3

    print(line, file=out)
    print(f"status={record['status']} error_code={record['error_code']}", file=err)
    return 0 if record["status"] == "VENUE_REFERENCE_OK" else 1


if __name__ == "__main__":  # pragma: no cover - live entrypoint
    raise SystemExit(main())
