"""tools/live_diagnostic_edge_probe.py — diagnostic bridge: one live Golden Sample capture -> calculator.

This CLI driver is the SOLE one-way bridge from the live capture pipeline to the pure diagnostic
economics calculator:

    preflight economic validation
      -> ONE capture (onboard_market -> run_golden_sample_live)
      -> (only on GOLDEN_SAMPLE_OK) compute_diagnostic_edge_report
      -> one strict JSON envelope to stdout

Capture-layer failures (validation / onboarding / identity / GOLDEN_SAMPLE_INVALID) and the
calculator-layer fail-closed (CALC_FAILED_CLOSED) are kept strictly distinct: the calculator runs
ONLY after a GOLDEN_SAMPLE_OK capture, so CALC_FAILED_CLOSED can never mislabel a capture failure.

Pure boundaries: stdout JSON only; nothing persisted; one live capture, zero retry. Diagnostic
observation only — no side selection, ranking, instruction, sizing, or any actionability signal.

Exit map (THIS driver only): 0 economics DIAGNOSTIC_OK · 1 economics CALC_FAILED_CLOSED ·
2 VALIDATION/usage · 3 internal · 4 ONBOARDING_INVALID · 5 identity mismatch · 6 GOLDEN_SAMPLE_INVALID.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from tools.market_onboarder import onboard_market
from tools.golden_sample_live_wiring import run_golden_sample_live
from analysis.golden_sample_economics import compute_diagnostic_edge_report

GAMMA_BASE_DEFAULT = "https://gamma-api.polymarket.com"
BINANCE_BASE_DEFAULT = "https://api.binance.com"
PM_BASE_DEFAULT = "https://clob.polymarket.com"
HL_BASE_DEFAULT = "https://api.hyperliquid.xyz"
DEADLINE_CAP_S = 2.0
_PRECISION_MIN = 28
_PRECISION_MAX = 80
_ASSET_ALLOWLIST = ["BTC", "ETH", "SOL", "XRP"]
_SCHEMA = "diag-edge-probe-v1"
_DRIVER_NOTE = "diagnostic observation only; not trading/actionability"
_MARKERS = ("not_actionable", "capture_and_economics_layers_separated",
            "perp_reference_not_spot_truth_settlement")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _epoch_int(v):
    """Exact non-bool int >= 0 (type(True) is bool, so bool is excluded)."""
    return type(v) is int and v >= 0


def _epoch_ms_to_iso_z(epoch_ms: int) -> str:
    """Integer-only UTC ISO-8601 (millisecond precision) derived from a stored epoch-ms value."""
    if type(epoch_ms) is not int or epoch_ms < 0:
        raise ValueError("epoch_ms must be a non-bool int >= 0")
    seconds, millis = divmod(epoch_ms, 1000)
    dt = _EPOCH + timedelta(seconds=seconds, milliseconds=millis)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{millis:03d}Z"


def _build_provenance(capture, valuation_time_ms):
    """UTC mirrors + signed offset derived from the canonical epoch-ms stored in capture.timing."""
    start_ms = complete_ms = None
    if isinstance(capture, dict):
        timing = capture.get("timing")
        if isinstance(timing, dict):
            start_ms = timing.get("capture_start_time_ms")
            complete_ms = timing.get("capture_complete_time_ms")
    offset = (start_ms - valuation_time_ms
              if _epoch_int(start_ms) and _epoch_int(valuation_time_ms) else None)
    return {
        "valuation_time_ms": valuation_time_ms,
        "capture_start_utc": _epoch_ms_to_iso_z(start_ms) if _epoch_int(start_ms) else None,
        "capture_complete_utc": _epoch_ms_to_iso_z(complete_ms) if _epoch_int(complete_ms) else None,
        "valuation_to_capture_start_offset_ms": offset,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools.live_diagnostic_edge_probe",
        description="N=1 diagnostic bridge: Golden Sample capture -> diagnostic economics report.")
    # capture inputs
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
    # economic inputs (value args are str for Decimal fidelity; NEVER float)
    p.add_argument("--intended-stake-usd", required=True)
    p.add_argument("--valuation-time-ms", type=int, required=True)
    p.add_argument("--fee-per-share", required=True)
    p.add_argument("--slippage-allowance", required=True)
    p.add_argument("--safety-margin", required=True)
    p.add_argument("--max-spread", required=True)
    p.add_argument("--sigma-annual", required=True)
    p.add_argument("--drift-annual", required=True)
    p.add_argument("--decimal-precision", type=int, required=True)
    # optional injected wall-clock for onboarding window (no economic role)
    p.add_argument("--now-ms", type=int, default=None)
    return p


def _envelope(*, layer, capture_status, reason, capture, economics, provenance):
    return {
        "schema_version": _SCHEMA,
        "layer": layer,
        "capture_status": capture_status,
        "fail_closed_reason": reason,
        "capture": capture,
        "economics": economics,
        "provenance": provenance,
        "markers": list(_MARKERS),
        "driver_note": _DRIVER_NOTE,
    }


def _strict_jsonify(value):
    """JSON-safe projection: Decimal -> fixed string, datetime -> iso, bool/int/str/None pass,
    list/dict recurse, float rejected. No default=str; never mutates input."""
    if value is None or isinstance(value, bool):
        return value
    t = type(value)
    if t is int or t is str:
        return value
    if t is float:
        raise TypeError("float is not permitted in diagnostic output")
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if t is dict:
        out = {}
        for k, v in value.items():
            if type(k) is not str:
                raise TypeError("non-str dict key")
            out[k] = _strict_jsonify(v)
        return out
    if t in (list, tuple):
        return [_strict_jsonify(x) for x in value]
    raise TypeError(f"unsupported node type {t.__name__}")


def _emit(envelope, out):
    print(json.dumps(_strict_jsonify(envelope), sort_keys=True, separators=(",", ":")), file=out)


# ---------------------------------------------------------------------------
# preflight validation (before any onboarding/capture/calculator)
# ---------------------------------------------------------------------------

def _strict_dec(raw):
    try:
        d = Decimal(raw)
    except (InvalidOperation, TypeError, ValueError):
        return None
    if d.is_nan() or d.is_infinite():
        return None
    return d


def _validate_economics(args) -> bool:
    stake = _strict_dec(args.intended_stake_usd)
    if stake is None or stake <= 0:
        return False
    for raw, lo_ok in ((args.fee_per_share, True), (args.slippage_allowance, True),
                       (args.safety_margin, True)):
        d = _strict_dec(raw)
        if d is None or d < 0 or d >= 1:
            return False
    spread = _strict_dec(args.max_spread)
    if spread is None or not (0 < spread < 1):
        return False
    sigma = _strict_dec(args.sigma_annual)
    if sigma is None or sigma <= 0:
        return False
    if _strict_dec(args.drift_annual) is None:
        return False
    if not (isinstance(args.valuation_time_ms, int) and not isinstance(args.valuation_time_ms, bool)
            and args.valuation_time_ms >= 0):
        return False
    if not (_PRECISION_MIN <= args.decimal_precision <= _PRECISION_MAX):
        return False
    return True


def _valid_deadline(v) -> bool:
    return isinstance(v, float) and math.isfinite(v) and 0 < v <= DEADLINE_CAP_S


# ---------------------------------------------------------------------------
# capture (one async pipeline, one asyncio.run, zero retry)
# ---------------------------------------------------------------------------

def _identity_reason(record, args):
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


def _onboarding_payload(record):
    classification = record.get("classification")
    gamma = record.get("gamma")
    binance = record.get("binance")
    return {
        "phase": "ONBOARDING",
        "onboarding_status": record.get("onboarding_status"),
        "onboarding_error_code": record.get("onboarding_error_code"),
        "slug": record.get("slug"), "asset": record.get("asset"),
        "interval": record.get("interval"), "condition_id": record.get("condition_id"),
        "classification": classification.get("status") if isinstance(classification, dict) else None,
        "gamma_status": gamma.get("status") if isinstance(gamma, dict) else None,
        "binance_status": binance.get("status") if isinstance(binance, dict) else None,
    }


def _identity_payload(record, args, reason):
    return {"phase": "IDENTITY", "identity_status": "IDENTITY_MISMATCH", "reason": reason,
            "slug": record.get("slug"), "asset": record.get("asset"),
            "condition_id": record.get("condition_id"),
            "expected_condition_id": args.expected_condition_id}


async def _capture(*, args, now_ms, build_onboarding_clients, build_pm_session,
                   hl_client_factory, monotonic_ns_fn, utc_now_fn, wall_ms_fn):
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
    reason = _identity_reason(record, args)
    if reason is not None:
        return {"kind": "IDENTITY_MISMATCH", "record": record, "reason": reason}

    pm_session = build_pm_session(args.pm_timeout_s)
    capture = await run_golden_sample_live(
        onboarding_record=record, pm_session=pm_session, hl_client_factory=hl_client_factory,
        pm_base_url=args.pm_base_url, hl_base_url=args.hl_base_url,
        pm_timeout_s=args.pm_timeout_s, hl_timeout_s=args.hl_timeout_s,
        monotonic_ns_fn=monotonic_ns_fn, utc_now_fn=utc_now_fn, wall_ms_fn=wall_ms_fn,
        max_skew_ms=args.max_skew_ms)
    return {"kind": "CAPTURE", "record": record, "capture": capture}


def _iso_utc_now() -> str:  # pragma: no cover - trivial wall-clock provenance
    return datetime.now(timezone.utc).isoformat()


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
         wall_ms_fn=None, economics_fn=None, out=None, err=None) -> int:
    out = out if out is not None else sys.stdout
    err = err if err is not None else sys.stderr

    parser = build_arg_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    def _validation_envelope():
        # valuation_time_ms is parsed by argparse (type=int) before any bound check, so it is echoed
        return _envelope(layer="VALIDATION", capture_status=None, reason="invalid_config",
                         capture=None, economics=None,
                         provenance=_build_provenance(None, args.valuation_time_ms))

    # ---- preflight validation (no onboarding/capture/calculator on failure) ----
    if not (_valid_deadline(args.onboarding_timeout_s) and _valid_deadline(args.pm_timeout_s)
            and _valid_deadline(args.hl_timeout_s)):
        _emit(_validation_envelope(), out)
        return 2
    if not (isinstance(args.max_skew_ms, int) and not isinstance(args.max_skew_ms, bool)
            and args.max_skew_ms > 0):
        _emit(_validation_envelope(), out)
        return 2
    if not _validate_economics(args):
        _emit(_validation_envelope(), out)
        return 2

    if args.now_ms is not None:
        now_ms = args.now_ms
    elif now_fn is not None:
        now_ms = now_fn()
    else:
        now_ms = None  # pragma: no cover - live boundary fills wall clock below
        import time as _t  # pragma: no cover
        now_ms = int(_t.time() * 1000)  # pragma: no cover
    if now_ms < 0:
        _emit(_validation_envelope(), out)
        return 2

    build_onboarding_clients = build_onboarding_clients or _make_onboarding_clients
    build_pm_session = build_pm_session or _make_pm_session
    hl_client_factory = hl_client_factory or _make_hl_factory()
    monotonic_ns_fn = monotonic_ns_fn or _default_monotonic_ns()
    utc_now_fn = utc_now_fn or _iso_utc_now
    if wall_ms_fn is None:                       # explicit 0/False/"" must reach clock validation
        wall_ms_fn = _default_wall_ms
    economics_fn = economics_fn or compute_diagnostic_edge_report

    val_ms = args.valuation_time_ms

    # ---- one live capture, zero retry ----
    try:
        outcome = asyncio.run(_capture(
            args=args, now_ms=now_ms, build_onboarding_clients=build_onboarding_clients,
            build_pm_session=build_pm_session, hl_client_factory=hl_client_factory,
            monotonic_ns_fn=monotonic_ns_fn, utc_now_fn=utc_now_fn, wall_ms_fn=wall_ms_fn))
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        print(f"internal error: {e!r}", file=err)
        return 3

    kind = outcome["kind"]
    if kind == "ONBOARDING_INVALID":
        _emit(_envelope(layer="ONBOARDING", capture_status="ONBOARDING_INVALID",
                        reason=outcome["record"].get("onboarding_error_code"),
                        capture=_onboarding_payload(outcome["record"]), economics=None,
                        provenance=_build_provenance(None, val_ms)), out)
        return 4
    if kind == "IDENTITY_MISMATCH":
        _emit(_envelope(layer="IDENTITY", capture_status="IDENTITY_MISMATCH",
                        reason=outcome["reason"],
                        capture=_identity_payload(outcome["record"], args, outcome["reason"]),
                        economics=None, provenance=_build_provenance(None, val_ms)), out)
        return 5

    capture = outcome["capture"]
    if capture["status"] != "GOLDEN_SAMPLE_OK":
        _emit(_envelope(layer="CAPTURE", capture_status=capture["status"],
                        reason=capture.get("error_code"), capture=capture, economics=None,
                        provenance=_build_provenance(capture, val_ms)), out)
        return 6

    # ---- capture OK: invoke the pure calculator (the ONLY place it runs) ----
    config = {
        "fee_per_share": args.fee_per_share, "slippage_allowance": args.slippage_allowance,
        "safety_margin": args.safety_margin, "max_spread": args.max_spread,
        "sigma_annual": args.sigma_annual, "drift_annual": args.drift_annual,
        "valuation_time_ms": args.valuation_time_ms, "decimal_precision": args.decimal_precision,
        "expected_condition_id": args.expected_condition_id,
    }
    try:
        economics = economics_fn(golden_sample_record=capture,
                                 intended_stake_usd=args.intended_stake_usd, config=config)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        print(f"internal error: {e!r}", file=err)
        return 3

    _emit(_envelope(layer="ECONOMICS", capture_status="GOLDEN_SAMPLE_OK",
                    reason=None, capture=capture, economics=economics,
                    provenance=_build_provenance(capture, val_ms)), out)
    return 0 if economics.get("status") == "DIAGNOSTIC_OK" else 1


def _default_monotonic_ns():  # pragma: no cover - live boundary monotonic clock
    import time as _t
    return _t.monotonic_ns


def _default_wall_ms():  # pragma: no cover - live boundary epoch-ms wall clock
    import time as _t
    return _t.time_ns() // 1_000_000


if __name__ == "__main__":  # pragma: no cover - live boundary
    raise SystemExit(main())
