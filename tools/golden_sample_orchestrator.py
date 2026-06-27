"""Capture-only Golden Sample orchestrator.

Thin async seam: accepts one prevalidated market-onboarder record, concurrently invokes three injected
single-shot fetchers (YES book, NO book, Hyperliquid reference), measures outer timing with injected
monotonic + UTC clocks, validates identity/carrier-semantics/timing with deterministic fixed
precedence, and returns one Decimal-safe structured record. It ends at the record: no downstream
hand-off, no edge math, nothing stored, no network. Integer-only threshold math, no binary floats.

Ownership isolation: caller-owned inputs are deep-cloned through a strict plain-tree validator before
they enter the returned record, so caller mutation cannot reach a returned sample and sample mutation
cannot reach caller inputs. The returned value is an ordinary mutable dict (no intrinsic immutability).
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

_SCHEMA = "golden-sample-v0"
_OK = "GOLDEN_SAMPLE_OK"
_INVALID = "GOLDEN_SAMPLE_INVALID"
_HL_SOURCE = "hyperliquid_all_mids_perp"
_NS_PER_MS = 1_000_000
_BASE_MARKERS = ("client_completion_skew_not_venue_event_time", "no_venue_event_timestamp_degraded")
_SEMANTICS_NOTE = "completion skew is client-completion skew, not venue-event-time skew"


class _PlainTreeError(Exception):
    """Raised when a value is not a permitted plain-tree node."""


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def _is_nonneg_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _ns_to_ms_str(ns):
    return format(Decimal(ns) / Decimal(_NS_PER_MS), "f")


def _iso(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def _clone_plain_tree(value):
    """Deep-clone a permitted plain tree into fresh containers; reject anything else (exact types).

    Permitted: None, exact str, exact int (bool rejected), Decimal, exact dict (str keys), list, tuple.
    Rejected: bool, binary number, set, dataclass/object, exception, datetime, mapping proxy, and
    every non-exact subclass. Never invokes user copy hooks.
    """
    if value is None:
        return None
    t = type(value)
    if t is bool:
        raise _PlainTreeError("bool not permitted")
    if t is int:
        return value
    if t is str:
        return value
    if t is Decimal:
        return value
    if t is dict:
        out = {}
        for k, v in value.items():
            if type(k) is not str:
                raise _PlainTreeError("non-str dict key")
            out[k] = _clone_plain_tree(v)
        return out
    if t is list:
        return [_clone_plain_tree(x) for x in value]
    if t is tuple:
        return tuple(_clone_plain_tree(x) for x in value)
    raise _PlainTreeError(f"unsupported type {t.__name__}")


def _safe_clone(value):
    """Best-effort isolation: clone if a plain tree, else None (never leak the caller object)."""
    try:
        return _clone_plain_tree(value)
    except _PlainTreeError:
        return None


def _record(*, onboarding, yes_book, no_book, hl_reference, timing, max_skew_ms,
            markers, status, error_code):
    return {
        "schema_version": _SCHEMA,
        "onboarding": onboarding,
        "yes_book": yes_book,
        "no_book": no_book,
        "hl_reference": hl_reference,
        "timing": timing,
        "capture_provenance": {"clock_basis": "injected_monotonic_ns+injected_utc"},
        "max_skew_ms": max_skew_ms,
        "markers": list(markers),
        "status": status,
        "error_code": error_code,
    }


def _validate_inputs(onboarding_record, fetchers, clocks, max_skew_ms):
    """Return (error_code|None, identity|None). Pure, pre-fetch."""
    if not _is_pos_int(max_skew_ms):
        return "input_invalid", None
    for fn in list(fetchers) + list(clocks):
        if not callable(fn):
            return "input_invalid", None
    if not isinstance(onboarding_record, dict):
        return "onboarding_invalid", None
    if onboarding_record.get("onboarding_status") != "ONBOARDING_OK":
        return "onboarding_invalid", None
    classification = onboarding_record.get("classification")
    if not isinstance(classification, dict) or classification.get("status") != "CACHE_READY":
        return "onboarding_invalid", None

    asset = onboarding_record.get("asset")
    condition_id = onboarding_record.get("condition_id")
    interval = onboarding_record.get("interval")
    if not (isinstance(asset, str) and asset and isinstance(condition_id, str) and condition_id
            and isinstance(interval, str) and interval):
        return "onboarding_invalid", None

    gamma = onboarding_record.get("gamma")
    binance = onboarding_record.get("binance")
    if not isinstance(gamma, dict) or not isinstance(binance, dict):
        return "onboarding_invalid", None

    tmap = gamma.get("outcome_token_map")
    if not isinstance(tmap, list) or len(tmap) != 2:
        return "onboarding_invalid", None
    try:
        yes_tid = tmap[0]["token_id"]
        no_tid = tmap[1]["token_id"]
    except (KeyError, TypeError, IndexError):
        return "onboarding_invalid", None
    if not (isinstance(yes_tid, str) and yes_tid and isinstance(no_tid, str) and no_tid):
        return "onboarding_invalid", None

    gamma_event = gamma.get("event_start_time_ms")
    gamma_end = gamma.get("end_date_ms")
    binance_event = binance.get("event_start_time_ms")
    if not (_is_nonneg_int(gamma_event) and _is_nonneg_int(gamma_end)
            and _is_nonneg_int(binance_event)):
        return "onboarding_invalid", None
    strike = binance.get("strike_price")
    if not isinstance(strike, Decimal):
        return "onboarding_invalid", None

    return None, {"asset": asset, "yes_tid": yes_tid, "no_tid": no_tid,
                  "gamma_event": gamma_event, "gamma_end": gamma_end,
                  "binance_event": binance_event, "strike": strike}


async def _timed_leg(fetcher, arg, monotonic_ns_fn, utc_now_fn):
    start = monotonic_ns_fn()
    try:
        result = await fetcher(arg)
        exc_repr = None
    except Exception as exc:          # noqa: BLE001 - cancellation/KbdInt/SysExit are BaseException
        result = None
        exc_repr = repr(exc)
    complete = monotonic_ns_fn()
    received = utc_now_fn()
    return {"start": start, "complete": complete, "received": received,
            "result": result, "exc_repr": exc_repr}


def _clock_invalid(legs):
    for leg in legs:
        if not _is_nonneg_int(leg["start"]) or not _is_nonneg_int(leg["complete"]):
            return True
        if leg["complete"] < leg["start"]:
            return True
    return False


def _eval_book(leg):
    """Project + isolate one book leg. Returns invalid flag, isolated evidence, slot error, token."""
    exc = leg["exc_repr"]
    r = leg["result"]
    token = getattr(r, "token_id", None) if r is not None else None
    if exc is not None:
        return {"invalid": True, "evidence": None, "slot_error": "exception", "token": token}
    if r is None:
        return {"invalid": True, "evidence": None, "slot_error": None, "token": None}

    carrier_err = getattr(r, "error_code", None)
    parsed = getattr(r, "parsed_safe_book", None)
    raw = {
        "token_id": getattr(r, "token_id", None),
        "parsed_safe_book": parsed,
        "error_code": carrier_err,
        "http_status": getattr(r, "http_status", None),
        "reject_reason": getattr(r, "reject_reason", None),
        "fetch_span_ms": getattr(r, "fetch_span_ms", None),
        "fetch_started_at": _iso(getattr(r, "fetch_started_at", None)),
        "fetch_completed_at": _iso(getattr(r, "fetch_completed_at", None)),
    }
    try:
        evidence = _clone_plain_tree(raw)
        unsupported = False
    except _PlainTreeError:
        evidence = None
        unsupported = True

    invalid = unsupported or (carrier_err is not None) or (not isinstance(parsed, dict))
    slot_error = "unsupported_evidence" if unsupported else carrier_err
    return {"invalid": invalid, "evidence": evidence, "slot_error": slot_error, "token": token}


def _eval_hl(leg):
    """Project + isolate the Hyperliquid leg. Returns invalid flag, isolated evidence, slot error."""
    exc = leg["exc_repr"]
    r = leg["result"]
    if exc is not None:
        return {"invalid": True, "evidence": None, "slot_error": "exception"}
    if not isinstance(r, dict):
        return {"invalid": True, "evidence": None, "slot_error": None}

    status_ok = (r.get("status") == "VENUE_REFERENCE_OK" and r.get("error_code") is None)
    try:
        evidence = _clone_plain_tree(r)
        unsupported = False
    except _PlainTreeError:
        evidence = None
        unsupported = True

    invalid = unsupported or not status_ok
    slot_error = "unsupported_evidence" if unsupported else r.get("error_code")
    return {"invalid": invalid, "evidence": evidence, "slot_error": slot_error}


def _hl_semantic_mismatch(leg, asset):
    r = leg["result"]
    if r.get("asset") != asset:
        return True
    if r.get("reference_source") != _HL_SOURCE:
        return True
    p = r.get("reference_price")
    if not isinstance(p, Decimal) or isinstance(p, bool):
        return True
    if p.is_nan() or p.is_infinite() or p <= 0:
        return True
    return False


def _strike_expiry_mismatch(ident):
    if ident["gamma_event"] != ident["binance_event"]:
        return True
    if not ident["gamma_end"] > ident["gamma_event"]:
        return True
    s = ident["strike"]
    if s.is_nan() or s.is_infinite() or s <= 0:
        return True
    return False


def _book_slot(expected_tid, leg, ev, *, latency_ns):
    return {
        "expected_token_id": expected_tid,
        "evidence": ev["evidence"],
        "exception_repr": leg["exc_repr"],
        "error_code": ev["slot_error"],
        "start_mono_ns": leg["start"],
        "complete_mono_ns": leg["complete"],
        "latency_ns": latency_ns,
        "latency_ms": _ns_to_ms_str(latency_ns) if latency_ns is not None else None,
        "client_received_at_utc": leg["received"],
    }


def _hl_slot(expected_asset, leg, ev, *, latency_ns):
    return {
        "expected_asset": expected_asset,
        "evidence": ev["evidence"],
        "exception_repr": leg["exc_repr"],
        "error_code": ev["slot_error"],
        "start_mono_ns": leg["start"],
        "complete_mono_ns": leg["complete"],
        "latency_ns": latency_ns,
        "latency_ms": _ns_to_ms_str(latency_ns) if latency_ns is not None else None,
        "client_received_at_utc": leg["received"],
    }


async def orchestrate_golden_sample(*, onboarding_record, yes_book_fetcher, no_book_fetcher,
                                    hl_reference_fetcher, monotonic_ns_fn, utc_now_fn,
                                    max_skew_ms) -> dict:
    err, ident = _validate_inputs(
        onboarding_record,
        [yes_book_fetcher, no_book_fetcher, hl_reference_fetcher],
        [monotonic_ns_fn, utc_now_fn], max_skew_ms)
    if err is not None:
        return _record(onboarding=_safe_clone(onboarding_record), yes_book=None, no_book=None,
                       hl_reference=None, timing=None, max_skew_ms=max_skew_ms,
                       markers=_BASE_MARKERS, status=_INVALID, error_code=err)

    # isolate onboarding synchronously before the first await; unsupported tree -> onboarding_invalid
    try:
        iso_onboarding = _clone_plain_tree(onboarding_record)
    except _PlainTreeError:
        return _record(onboarding=None, yes_book=None, no_book=None, hl_reference=None,
                       timing=None, max_skew_ms=max_skew_ms, markers=_BASE_MARKERS,
                       status=_INVALID, error_code="onboarding_invalid")

    yes_leg, no_leg, hl_leg = await asyncio.gather(
        _timed_leg(yes_book_fetcher, ident["yes_tid"], monotonic_ns_fn, utc_now_fn),
        _timed_leg(no_book_fetcher, ident["no_tid"], monotonic_ns_fn, utc_now_fn),
        _timed_leg(hl_reference_fetcher, ident["asset"], monotonic_ns_fn, utc_now_fn),
    )
    legs = [yes_leg, no_leg, hl_leg]
    clock_invalid = _clock_invalid(legs)

    if clock_invalid:
        yes_lat = no_lat = hl_lat = None
        span_ns = skew_ns = None
    else:
        yes_lat = yes_leg["complete"] - yes_leg["start"]
        no_lat = no_leg["complete"] - no_leg["start"]
        hl_lat = hl_leg["complete"] - hl_leg["start"]
        completes = [leg["complete"] for leg in legs]
        starts = [leg["start"] for leg in legs]
        span_ns = max(completes) - min(starts)
        skew_ns = max(completes) - min(completes)

    threshold_ns = max_skew_ms * _NS_PER_MS

    yes_ev = _eval_book(yes_leg)
    no_ev = _eval_book(no_leg)
    hl_ev = _eval_hl(hl_leg)

    yes_slot = _book_slot(ident["yes_tid"], yes_leg, yes_ev, latency_ns=yes_lat)
    no_slot = _book_slot(ident["no_tid"], no_leg, no_ev, latency_ns=no_lat)
    hl_slot = _hl_slot(ident["asset"], hl_leg, hl_ev, latency_ns=hl_lat)

    timing = {
        "capture_span_ns": span_ns,
        "completion_skew_ns": skew_ns,
        "threshold_ns": threshold_ns,
        "capture_span_ms": _ns_to_ms_str(span_ns) if span_ns is not None else None,
        "completion_skew_ms": _ns_to_ms_str(skew_ns) if skew_ns is not None else None,
        "semantics_note": _SEMANTICS_NOTE,
    }

    markers = list(_BASE_MARKERS)
    if isinstance(hl_leg["result"], dict) and hl_leg["result"].get("reference_source") == _HL_SOURCE:
        markers.append("hyperliquid_perp_reference_basis_risk")

    error_code = None
    if yes_ev["invalid"]:
        error_code = "yes_book_invalid"
    elif no_ev["invalid"]:
        error_code = "no_book_invalid"
    elif hl_ev["invalid"]:
        error_code = "hl_reference_invalid"
    elif yes_ev["token"] != ident["yes_tid"] or no_ev["token"] != ident["no_tid"]:
        error_code = "identity_token_mismatch"
    elif _strike_expiry_mismatch(ident):
        error_code = "strike_expiry_mismatch"
    elif _hl_semantic_mismatch(hl_leg, ident["asset"]):
        error_code = "reference_semantic_mismatch"
    elif clock_invalid:
        error_code = "timing_clock_invalid"
    elif span_ns > threshold_ns or skew_ns > threshold_ns:
        error_code = "timing_skew_violation"

    status = _OK if error_code is None else _INVALID
    return _record(onboarding=iso_onboarding, yes_book=yes_slot, no_book=no_slot,
                   hl_reference=hl_slot, timing=timing, max_skew_ms=max_skew_ms,
                   markers=markers, status=status, error_code=error_code)
