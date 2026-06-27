"""tools/live_onboarder_probe.py — standalone N=1 live diagnostic for the market onboarder.

LIVE BOUNDARY: this file owns real aiohttp client setup/teardown and injects async client adapters
into onboard_market. The four core building blocks stay network-free and clock-free. Read-only GETs
only; nothing is persisted. Exit 1 (ONBOARDING_INVALID) is valid fail-closed evidence, not a failure.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time

from tools.market_onboarder import onboard_market

GAMMA_BASE_DEFAULT = "https://gamma-api.polymarket.com"
BINANCE_BASE_DEFAULT = "https://api.binance.com"
TIMEOUT_DEFAULT_S = 2.0
TIMEOUT_CAP_S = 2.0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools.live_onboarder_probe",
        description="N=1 read-only live diagnostic through the market onboarder.")
    p.add_argument("--slug", required=True)
    p.add_argument("--asset", required=True)
    p.add_argument("--interval", required=True)
    p.add_argument("--binance-symbol", required=True)
    p.add_argument("--expected-condition-id", default=None)
    p.add_argument("--gamma-base-url", default=GAMMA_BASE_DEFAULT)
    p.add_argument("--binance-base-url", default=BINANCE_BASE_DEFAULT)
    p.add_argument("--allowlist", default="BTC,ETH,SOL,XRP")
    p.add_argument("--reference-source-supported", action=argparse.BooleanOptionalAction,
                   default=True)
    p.add_argument("--timeout-s", type=float, default=TIMEOUT_DEFAULT_S)
    p.add_argument("--now-ms", type=int, default=None)
    return p


def _make_clients(timeout_s):  # pragma: no cover - live boundary, never run offline
    import aiohttp

    def _one_shot_client():
        async def _c(url):
            total = aiohttp.ClientTimeout(total=timeout_s)
            async with aiohttp.ClientSession(timeout=total) as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()   # 451 -> ClientResponseError(.status) -> geo seam
                    return await resp.json()
        return _c

    return _one_shot_client(), _one_shot_client()


async def _run(args, gamma_client, binance_client, now_ms):
    allowlist = [a.strip() for a in args.allowlist.split(",") if a.strip()]
    return await onboard_market(
        slug=args.slug, asset=args.asset, interval=args.interval, now_ms=now_ms,
        gamma_client=gamma_client, binance_client=binance_client,
        gamma_base_url=args.gamma_base_url, binance_base_url=args.binance_base_url,
        asset_allowlist=allowlist,
        reference_source_supported=args.reference_source_supported,
        asset_symbol_map={args.asset: args.binance_symbol},
        expected_condition_id=args.expected_condition_id)


def main(argv=None, *, client_factory=None, now_fn=None, out=None) -> int:
    out = out or sys.stdout
    parser = build_arg_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    if args.timeout_s <= 0 or args.timeout_s > TIMEOUT_CAP_S:
        print(f"validation error: --timeout-s must be in (0, {TIMEOUT_CAP_S}]", file=out)
        return 2

    if args.now_ms is not None:
        now_ms = args.now_ms
    elif now_fn is not None:
        now_ms = now_fn()
    else:
        now_ms = int(time.time() * 1000)
    if now_ms < 0:
        print("validation error: now_ms must be >= 0", file=out)
        return 2

    try:
        factory = client_factory or _make_clients
        gamma_client, binance_client = factory(args.timeout_s)
        record = asyncio.run(_run(args, gamma_client, binance_client, now_ms))
    except SystemExit:
        raise
    except Exception as e:   # unexpected internal
        print(f"internal error: {e!r}", file=out)
        return 3

    classification = record["classification"]
    print(f"ONBOARDING_STATUS: {record['onboarding_status']}", file=out)
    print(f"ONBOARDING_ERROR_CODE: {record['onboarding_error_code']}", file=out)
    print(f"CLASSIFICATION: {classification['status'] if classification else None}", file=out)
    print("--- full record ---", file=out)
    print(json.dumps(record, indent=2, default=str), file=out)

    return 0 if record["onboarding_status"] == "ONBOARDING_OK" else 1


if __name__ == "__main__":  # pragma: no cover - live boundary
    raise SystemExit(main())
