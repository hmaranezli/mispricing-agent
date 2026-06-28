"""tools/live_golden_sample_probe.py — N=1 read-only onboarder -> Golden Sample capture diagnostic.

LIVE BOUNDARY: this file owns real aiohttp client setup/teardown and injects async client adapters
into the UNCHANGED onboard_market and run_golden_sample_live, driving a single async pipeline under one
event-loop entry:

    await onboard_market  ->  gate (+ identity)  ->  await run_golden_sample_live

Onboarding fully completes and its one-shot clients self-close before any capture client is built;
capture latency/span/skew are owned exclusively by the orchestrator's injected monotonic clock. The
driver itself owns no concurrency. UTC provenance is emitted as an ISO-8601 string; the only Decimal
(prices) is rendered via the wiring's strict serializer. Nothing is persisted; read-only GET/POST only.

Exit map: 0 GOLDEN_SAMPLE_OK · 1 GOLDEN_SAMPLE_INVALID · 2 usage/validation · 3 internal ·
4 ONBOARDING_INVALID (zero capture) · 5 identity mismatch (zero capture).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import time
from datetime import datetime, timezone

from tools.market_onboarder import onboard_market
from tools.golden_sample_live_wiring import run_golden_sample_live, serialize_golden_sample

GAMMA_BASE_DEFAULT = "https://gamma-api.polymarket.com"
BINANCE_BASE_DEFAULT = "https://api.binance.com"
PM_BASE_DEFAULT = "https://clob.polymarket.com"
HL_BASE_DEFAULT = "https://api.hyperliquid.xyz"
DEADLINE_CAP_S = 2.0
_ASSET_ALLOWLIST = ["BTC", "ETH", "SOL", "XRP"]


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools.live_golden_sample_probe",
        description="N=1 read-only onboarder -> Golden Sample capture diagnostic.")
    p.add_argument("--slug", required=True)
    p.add_argument("--asset", required=True)
    p.add_argument("--interval", required=True)
    p.add_argument("--binance-symbol", required=True)
    p.add_argument("--expected-condition-id", required=True)
    p.add_argument("--max-skew-ms", type=int, required=True)
    p.add_argument("--onboarding-timeout-s", type=float, required=True)
    p.add_argument("--pm-timeout-s", type=float, required=True)
    p.add_argument("--hl-timeout-s", type=float, required=True)
    p.add_argument("--gamma-base-url", default=GAMMA_BASE_DEFAULT)
    p.add_argument("--binance-base-url", default=BINANCE_BASE_DEFAULT)
    p.add_argument("--pm-base-url", default=PM_BASE_DEFAULT)
    p.add_argument("--hl-base-url", default=HL_BASE_DEFAULT)
    p.add_argument("--now-ms", type=int, default=None)
    return p


def _valid_deadline(v) -> bool:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    if not math.isfinite(v):
        return False
    return 0 < v <= DEADLINE_CAP_S


def _identity_check(record, args):
    """Return a mismatch reason str if the onboarded market differs from the requested one, else None.

    Defense-in-depth: onboard_market is called WITH the operator's expected_condition_id, so a wrong
    on-chain conditionId fails closed early inside Gamma (gamma_condition_id_mismatch -> exit 4) before
    Binance. This post-onboarding gate is a redundant safety that re-checks condition/asset/slug/token
    identity on the returned record; it surfaces as exit 5 only if an ONBOARDING_OK record is itself
    internally inconsistent with the operator input.
    """
    if record.get("condition_id") != args.expected_condition_id:
        return "condition_id_mismatch"
    if record.get("asset") != args.asset:
        return "asset_mismatch"
    if record.get("slug") != args.slug:
        return "slug_mismatch"
    gamma = record.get("gamma") or {}
    tmap = gamma.get("outcome_token_map")
    if not isinstance(tmap, list) or len(tmap) != 2:
        return "token_map_shape"
    try:
        yes_tid = tmap[0]["token_id"]
        no_tid = tmap[1]["token_id"]
    except (KeyError, TypeError, IndexError):
        return "token_id_missing"
    if not (isinstance(yes_tid, str) and yes_tid and isinstance(no_tid, str) and no_tid):
        return "token_id_empty"
    return None


def _onboarding_invalid_payload(record) -> dict:
    classification = record.get("classification")
    gamma = record.get("gamma")
    binance = record.get("binance")
    return {
        "phase": "ONBOARDING",
        "onboarding_status": record.get("onboarding_status"),
        "onboarding_error_code": record.get("onboarding_error_code"),
        "slug": record.get("slug"),
        "asset": record.get("asset"),
        "interval": record.get("interval"),
        "condition_id": record.get("condition_id"),
        "classification": classification.get("status") if isinstance(classification, dict) else None,
        "gamma_status": gamma.get("status") if isinstance(gamma, dict) else None,
        "binance_status": binance.get("status") if isinstance(binance, dict) else None,
    }


def _identity_payload(record, args, reason) -> dict:
    return {
        "phase": "IDENTITY",
        "identity_status": "IDENTITY_MISMATCH",
        "reason": reason,
        "slug": record.get("slug"),
        "asset": record.get("asset"),
        "condition_id": record.get("condition_id"),
        "expected_condition_id": args.expected_condition_id,
    }


async def _pipeline(*, args, now_ms, build_onboarding_clients, build_pm_session,
                    hl_client_factory, monotonic_ns_fn, utc_now_fn, wall_ms_fn) -> dict:
    gamma_client, binance_client = build_onboarding_clients(args.onboarding_timeout_s)
    record = await onboard_market(
        slug=args.slug, asset=args.asset, interval=args.interval, now_ms=now_ms,
        gamma_client=gamma_client, binance_client=binance_client,
        gamma_base_url=args.gamma_base_url, binance_base_url=args.binance_base_url,
        asset_allowlist=_ASSET_ALLOWLIST, reference_source_supported=True,
        asset_symbol_map={args.asset: args.binance_symbol},
        expected_condition_id=args.expected_condition_id)

    if record["onboarding_status"] != "ONBOARDING_OK":
        return {"kind": "ONBOARDING_INVALID", "record": record}

    reason = _identity_check(record, args)
    if reason is not None:
        return {"kind": "IDENTITY_MISMATCH", "record": record, "reason": reason}

    pm_session = build_pm_session(args.pm_timeout_s)
    capture = await run_golden_sample_live(
        onboarding_record=record,
        pm_session=pm_session,
        hl_client_factory=hl_client_factory,
        pm_base_url=args.pm_base_url,
        hl_base_url=args.hl_base_url,
        pm_timeout_s=args.pm_timeout_s,
        hl_timeout_s=args.hl_timeout_s,
        monotonic_ns_fn=monotonic_ns_fn,
        utc_now_fn=utc_now_fn,
        wall_ms_fn=wall_ms_fn,
        max_skew_ms=args.max_skew_ms)
    return {"kind": "CAPTURE", "record": record, "capture": capture}


def _iso_utc_now() -> str:  # pragma: no cover - trivial wall-clock provenance
    return datetime.now(timezone.utc).isoformat()


def _default_wall_ms() -> int:  # pragma: no cover - live boundary epoch-ms wall clock
    return time.time_ns() // 1_000_000


def _make_onboarding_clients(timeout_s):  # pragma: no cover - live boundary
    import aiohttp

    def _one_shot():
        async def _c(url):
            total = aiohttp.ClientTimeout(total=timeout_s)
            async with aiohttp.ClientSession(timeout=total) as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        return _c
    return _one_shot(), _one_shot()


def _make_pm_session(pm_timeout_s):  # pragma: no cover - live boundary
    import aiohttp

    class _SingleRunPmSession:
        def __init__(self):
            self._session = None

        async def __aenter__(self):
            self._session = aiohttp.ClientSession()
            return self

        async def __aexit__(self, *exc):
            if self._session is not None:
                await self._session.close()
            return False

        async def get(self, url, *, params=None, timeout=None):
            total = aiohttp.ClientTimeout(total=timeout if timeout is not None else pm_timeout_s)
            return await self._session.get(url, params=params, timeout=total)

    return _SingleRunPmSession()


def _make_hl_factory():  # pragma: no cover - live boundary
    import aiohttp

    def factory(timeout_s):
        async def client(url, *, json_body):
            total = aiohttp.ClientTimeout(total=timeout_s)
            async with aiohttp.ClientSession(timeout=total) as session:
                async with session.post(url, json=json_body) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        return client
    return factory


def main(argv=None, *, build_onboarding_clients=None, build_pm_session=None,
         hl_client_factory=None, now_fn=None, monotonic_ns_fn=None, utc_now_fn=None,
         wall_ms_fn=None, out=None, err=None) -> int:
    out = out if out is not None else sys.stdout
    err = err if err is not None else sys.stderr

    parser = build_arg_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    for name, value in (("--onboarding-timeout-s", args.onboarding_timeout_s),
                        ("--pm-timeout-s", args.pm_timeout_s),
                        ("--hl-timeout-s", args.hl_timeout_s)):
        if not _valid_deadline(value):
            print(f"validation error: {name} must be finite, > 0, and <= {DEADLINE_CAP_S}", file=err)
            return 2

    if not (isinstance(args.max_skew_ms, int) and not isinstance(args.max_skew_ms, bool)
            and args.max_skew_ms > 0):
        print("validation error: --max-skew-ms must be a positive int", file=err)
        return 2

    if args.now_ms is not None:
        now_ms = args.now_ms
    elif now_fn is not None:
        now_ms = now_fn()
    else:
        now_ms = int(time.time() * 1000)
    if now_ms < 0:
        print("validation error: now_ms must be >= 0", file=err)
        return 2

    build_onboarding_clients = build_onboarding_clients or _make_onboarding_clients
    build_pm_session = build_pm_session or _make_pm_session
    hl_client_factory = hl_client_factory or _make_hl_factory()
    monotonic_ns_fn = monotonic_ns_fn or time.monotonic_ns
    utc_now_fn = utc_now_fn or _iso_utc_now
    if wall_ms_fn is None:                       # explicit 0/False/"" must reach clock validation
        wall_ms_fn = _default_wall_ms

    try:
        outcome = asyncio.run(_pipeline(
            args=args, now_ms=now_ms,
            build_onboarding_clients=build_onboarding_clients,
            build_pm_session=build_pm_session,
            hl_client_factory=hl_client_factory,
            monotonic_ns_fn=monotonic_ns_fn,
            utc_now_fn=utc_now_fn,
            wall_ms_fn=wall_ms_fn))
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:   # unexpected internal failure only
        print(f"internal error: {e!r}", file=err)
        return 3

    kind = outcome["kind"]
    if kind == "ONBOARDING_INVALID":
        print(json.dumps(_onboarding_invalid_payload(outcome["record"]),
                         sort_keys=True, separators=(",", ":")), file=out)
        return 4
    if kind == "IDENTITY_MISMATCH":
        print(json.dumps(_identity_payload(outcome["record"], args, outcome["reason"]),
                         sort_keys=True, separators=(",", ":")), file=out)
        return 5

    capture = outcome["capture"]
    print(serialize_golden_sample(capture), file=out)
    return 0 if capture["status"] == "GOLDEN_SAMPLE_OK" else 1


if __name__ == "__main__":  # pragma: no cover - live boundary
    raise SystemExit(main())
