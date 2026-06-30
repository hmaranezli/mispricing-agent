"""
analysis.forensic.gateg7_source_basis — Gate G7b offline source-basis contract.

Classifies the entry-time price reference against the SETTLEMENT source family and
computes the HL diagnostic basis (HL_reference - settlement_reference) at ts_signal.

Three mutually-exclusive modes (never blended):
  * TRUE_CHAINLINK       — exact decoded Chainlink Streams data injected AND it passed
                           schema / lookahead / freshness. Only then is the
                           Chainlink-aligned basis computed.
  * CHAINLINK_PROXY_ONLY — no trusted Chainlink, but a clean Coinbase+Kraken USD spot
                           basket is available. Reused as a DIAGNOSTIC PROXY ONLY,
                           permanently labeled CHAINLINK_PROXY_ONLY /
                           CHAINLINK_PROXY_NOT_CANONICAL. NEVER alpha, NEVER canonical.
  * NOT_COMPUTED         — neither trusted Chainlink nor a clean proxy is available.

Hard boundaries (G7b constitution):
  * NO live fetch, NO network, NO Chainlink credential / API key / HMAC / auth here.
    Chainlink data is INJECTED already-decoded (the auth-gated fetch is a separate,
    human-approved, secret-backed step that this module does not open).
  * Proxy data may answer "how far is HL from external spot proxy?" — it may NEVER be
    substituted into the Chainlink-aligned edge, and never described as Chainlink alpha.
  * Lookahead-safe: reference_ts_ms must be <= ts_signal_ms; stale/future/missing/schema
    failures fail closed (no crash, edge -> NOT_COMPUTED).
  * Decimal/string-safe: every economic output is a canonical Decimal string (no float).

This module imports NO trading/runtime surface (main_loop/scout/execution/position/
monitor/S1). It reuses the Chainlink Streams report validator only for schema checks.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from data import chainlink_streams as cl

# --- modes ---------------------------------------------------------------
TRUE_CHAINLINK = "TRUE_CHAINLINK"
CHAINLINK_PROXY_ONLY = "CHAINLINK_PROXY_ONLY"
NOT_COMPUTED = "NOT_COMPUTED"

# --- generic statuses ----------------------------------------------------
STATUS_OK = "OK"
COMPUTED = "COMPUTED"
BASIS_NOT_COMPUTED = "BASIS_NOT_COMPUTED"

# --- chainlink capture statuses (fail-closed taxonomy) -------------------
CHAINLINK_AUTH_REQUIRED = "CHAINLINK_AUTH_REQUIRED"
CHAINLINK_SOURCE_AUTH_BLOCKED = "CHAINLINK_SOURCE_AUTH_BLOCKED"
CHAINLINK_REFERENCE_UNAVAILABLE = "CHAINLINK_REFERENCE_UNAVAILABLE"
CHAINLINK_REFERENCE_STALE = "CHAINLINK_REFERENCE_STALE"
CHAINLINK_TIMESTAMP_AFTER_SIGNAL = "CHAINLINK_TIMESTAMP_AFTER_SIGNAL"
CHAINLINK_SCHEMA_MISMATCH = "CHAINLINK_SCHEMA_MISMATCH"

# --- chainlink access modes ----------------------------------------------
ACCESS_INJECTED_DECODED = "INJECTED_DECODED"
ACCESS_AUTH_REQUIRED = "AUTH_REQUIRED"
ACCESS_AUTH_BLOCKED = "AUTH_BLOCKED"
ACCESS_UNAVAILABLE = "UNAVAILABLE"
ACCESS_NOT_COMPUTED = "NOT_COMPUTED"

# --- proxy labels + statuses ---------------------------------------------
CHAINLINK_PROXY_ONLY = "CHAINLINK_PROXY_ONLY"
CHAINLINK_PROXY_NOT_CANONICAL = "CHAINLINK_PROXY_NOT_CANONICAL"
PROXY_REFERENCE_UNAVAILABLE = "PROXY_REFERENCE_UNAVAILABLE"
PROXY_REFERENCE_STALE = "PROXY_REFERENCE_STALE"
PROXY_TIMESTAMP_AFTER_SIGNAL = "PROXY_TIMESTAMP_AFTER_SIGNAL"
PROXY_SPREAD_GUARD_FAIL = "PROXY_SPREAD_GUARD_FAIL"

# --- G7-lite post-signal diagnostic (proxy captured AFTER an immutable signal) ---
PROXY_POST_SIGNAL_DIAGNOSTIC = "PROXY_POST_SIGNAL_DIAGNOSTIC"
PROXY_TS_PROVENANCE_CAPTURE_ONLY = "CAPTURE_TIME_ONLY"

_BPS = Decimal(10000)
_PCT = Decimal(100)


def _dec(value):
    """Parse into a finite Decimal, or None. bool is rejected (True/False is not a price)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return d if d.is_finite() else None


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _bucket(basis_pct: Decimal) -> str:
    a = abs(basis_pct)
    if a < Decimal("0.05"):
        return "FLAT"
    if a < Decimal("0.25"):
        return "TIGHT"
    if a < Decimal("1.0"):
        return "WIDE"
    return "EXTREME"


def _raw_report_price(report: dict):
    """Mirror chainlink_streams price-key precedence to recover the RAW (unscaled) price."""
    for key in ("price", "benchmarkPrice", "BenchmarkPrice"):
        if key in report:
            return report[key]
    return None


def _eval_chainlink(chainlink, hl_price: Decimal, ts_signal_ms: int, max_age_ms: int):
    """Return a dict of chainlink_* output fields. TRUE_CHAINLINK basis only on clean pass."""
    out = {
        "chainlink_reference_price": None,
        "chainlink_reference_ts_ms": None,
        "chainlink_reference_age_ms": None,
        "chainlink_stream_id": None,
        "chainlink_capture_status": CHAINLINK_REFERENCE_UNAVAILABLE,
        "chainlink_access_mode": ACCESS_UNAVAILABLE,
        "basis_hl_minus_chainlink": None,
        "basis_hl_minus_chainlink_pct": None,
        "chainlink_basis_bucket": None,
        "chainlink_reference_stale_flag": 0,
        "chainlink_aligned_edge_status": NOT_COMPUTED,
        "_ok": False,
    }
    if chainlink is None:
        return out
    if not isinstance(chainlink, dict):
        out["chainlink_capture_status"] = CHAINLINK_SCHEMA_MISMATCH
        out["chainlink_access_mode"] = ACCESS_NOT_COMPUTED
        return out

    # explicit auth/blocked signalling (the auth-gated fetch is never opened here)
    status = chainlink.get("status")
    if status in ("AUTH_REQUIRED", CHAINLINK_AUTH_REQUIRED):
        out["chainlink_capture_status"] = CHAINLINK_AUTH_REQUIRED
        out["chainlink_access_mode"] = ACCESS_AUTH_REQUIRED
        return out
    if status in ("AUTH_BLOCKED", CHAINLINK_SOURCE_AUTH_BLOCKED):
        out["chainlink_capture_status"] = CHAINLINK_SOURCE_AUTH_BLOCKED
        out["chainlink_access_mode"] = ACCESS_AUTH_BLOCKED
        return out

    report = chainlink.get("report")
    scale = chainlink.get("price_scale")
    if not isinstance(report, dict):
        out["chainlink_capture_status"] = CHAINLINK_REFERENCE_UNAVAILABLE
        out["chainlink_access_mode"] = ACCESS_NOT_COMPUTED
        return out

    # schema validation via the existing Streams boundary (gives feed_id + ts; raises on bad schema)
    try:
        normalized = cl.normalize_crypto_v3_report(report, price_scale=scale)
    except ValueError:
        out["chainlink_capture_status"] = CHAINLINK_SCHEMA_MISMATCH
        out["chainlink_access_mode"] = ACCESS_NOT_COMPUTED
        return out

    # recover an EXACT Decimal price (avoid the normalizer's float division)
    raw_price = _dec(_raw_report_price(report))
    scale_d = _dec(scale)
    if raw_price is None or scale_d is None or scale_d <= 0:
        out["chainlink_capture_status"] = CHAINLINK_SCHEMA_MISMATCH
        out["chainlink_access_mode"] = ACCESS_NOT_COMPUTED
        return out
    ref_price = raw_price / scale_d
    ref_ts_ms = normalized["timestamp_ms"]

    out["chainlink_stream_id"] = normalized["feed_id"]
    out["chainlink_reference_price"] = str(ref_price)
    out["chainlink_reference_ts_ms"] = ref_ts_ms
    out["chainlink_access_mode"] = ACCESS_INJECTED_DECODED

    # lookahead guard: reference must be at or before the signal
    if ref_ts_ms > ts_signal_ms:
        out["chainlink_capture_status"] = CHAINLINK_TIMESTAMP_AFTER_SIGNAL
        return out
    age = ts_signal_ms - ref_ts_ms
    out["chainlink_reference_age_ms"] = age
    if age > max_age_ms:
        out["chainlink_capture_status"] = CHAINLINK_REFERENCE_STALE
        out["chainlink_reference_stale_flag"] = 1
        return out

    if ref_price <= 0:
        out["chainlink_capture_status"] = CHAINLINK_SCHEMA_MISMATCH
        return out

    basis = hl_price - ref_price
    basis_pct = basis / ref_price * _PCT
    out["chainlink_capture_status"] = STATUS_OK
    out["basis_hl_minus_chainlink"] = str(basis)
    out["basis_hl_minus_chainlink_pct"] = str(basis_pct)
    out["chainlink_basis_bucket"] = _bucket(basis_pct)
    out["chainlink_aligned_edge_status"] = COMPUTED
    out["_ok"] = True
    return out


def _eval_proxy(proxy, hl_price: Decimal, ts_signal_ms: int, max_age_ms: int,
                spread_bps_threshold: Decimal):
    """Coinbase+Kraken USD spot basket reused as DIAGNOSTIC PROXY ONLY (Decimal midpoint +
    spread guard + freshness + lookahead). HL perp is NEVER merged into this basket."""
    out = {
        "proxy_reference_price": None,
        "proxy_reference_ts_ms": None,
        "proxy_source": None,
        "proxy_capture_status": PROXY_REFERENCE_UNAVAILABLE,
        "proxy_basis_hl_minus_proxy": None,
        "proxy_labels": [CHAINLINK_PROXY_ONLY, CHAINLINK_PROXY_NOT_CANONICAL],
        "_ok": False,
    }
    if not isinstance(proxy, dict):
        return out

    cb = _dec(proxy.get("coinbase"))
    kr = _dec(proxy.get("kraken"))
    ts_ms = _int(proxy.get("ts_ms"))
    used = [n for n, v in (("coinbase", cb), ("kraken", kr)) if v is not None]
    out["proxy_source"] = "+".join(used) if used else None

    # require BOTH USD spot sources for a guarded basket (single-source is not blessed here)
    if cb is None or kr is None:
        out["proxy_capture_status"] = PROXY_REFERENCE_UNAVAILABLE
        return out
    if ts_ms is None:
        out["proxy_capture_status"] = PROXY_REFERENCE_UNAVAILABLE
        return out

    mid = (cb + kr) / Decimal(2)
    out["proxy_reference_price"] = str(mid)
    out["proxy_reference_ts_ms"] = ts_ms

    if ts_ms > ts_signal_ms:
        out["proxy_capture_status"] = PROXY_TIMESTAMP_AFTER_SIGNAL
        out["proxy_reference_price"] = None
        return out
    if (ts_signal_ms - ts_ms) > max_age_ms:
        out["proxy_capture_status"] = PROXY_REFERENCE_STALE
        out["proxy_reference_price"] = None
        return out

    spread_bps = (abs(cb - kr) / mid * _BPS) if mid != 0 else None
    if spread_bps is None or spread_bps > spread_bps_threshold:
        out["proxy_capture_status"] = PROXY_SPREAD_GUARD_FAIL
        out["proxy_reference_price"] = None
        return out

    out["proxy_capture_status"] = STATUS_OK
    out["proxy_basis_hl_minus_proxy"] = str(hl_price - mid)
    out["_ok"] = True
    return out


def compute_source_basis(*, hl_reference, ts_signal_ms, chainlink=None, proxy=None,
                         max_reference_age_ms, spread_bps_threshold):
    """Offline source-basis contract. Pure: no fetch, no DB, no S1, no clock.

    hl_reference: {"price": <decimal-ish>, "ts_ms": int} — HL diagnostic reference (perp).
    chainlink:    None | {"status": "AUTH_REQUIRED"|"AUTH_BLOCKED"} | {"report": <decoded
                  crypto-v3 dict>, "price_scale": <num>}. INJECTED only; never fetched here.
    proxy:        None | {"coinbase": <decimal-ish|None>, "kraken": <decimal-ish|None>,
                  "ts_ms": int} — Coinbase+Kraken USD spot. Diagnostic proxy ONLY.

    Returns a flat dict of diagnostic fields (all economic values Decimal strings or None).
    """
    ts_signal_ms = _int(ts_signal_ms)
    max_age = _int(max_reference_age_ms)
    spread_thr = _dec(spread_bps_threshold)
    hl_price = _dec((hl_reference or {}).get("price")) if isinstance(hl_reference, dict) else None
    hl_ts = _int((hl_reference or {}).get("ts_ms")) if isinstance(hl_reference, dict) else None

    record = {
        "source_basis_mode": NOT_COMPUTED,
        "hl_reference_price": str(hl_price) if hl_price is not None else None,
        "hl_reference_ts_ms": hl_ts,
    }

    # Fail closed if the contract inputs themselves are unusable (no crash).
    if (ts_signal_ms is None or max_age is None or spread_thr is None
            or spread_thr <= 0 or hl_price is None or hl_price <= 0):
        cl_out = _eval_chainlink(None, Decimal(0), 0, 0)
        px_out = _eval_proxy(None, Decimal(0), 0, 0, Decimal(1))
        cl_out["chainlink_capture_status"] = (
            CHAINLINK_REFERENCE_UNAVAILABLE if hl_price is not None
            else CHAINLINK_REFERENCE_UNAVAILABLE)
        record.update({k: v for k, v in cl_out.items() if k != "_ok"})
        record.update({k: v for k, v in px_out.items() if k != "_ok"})
        record["basis_not_computed_reason"] = BASIS_NOT_COMPUTED
        return record

    cl_out = _eval_chainlink(chainlink, hl_price, ts_signal_ms, max_age)
    px_out = _eval_proxy(proxy, hl_price, ts_signal_ms, max_age, spread_thr)

    cl_ok = cl_out.pop("_ok")
    px_ok = px_out.pop("_ok")
    record.update(cl_out)
    record.update(px_out)

    # Mode precedence: trusted Chainlink wins; proxy can only ever be CHAINLINK_PROXY_ONLY.
    if cl_ok:
        record["source_basis_mode"] = TRUE_CHAINLINK
    elif px_ok:
        record["source_basis_mode"] = CHAINLINK_PROXY_ONLY
    else:
        record["source_basis_mode"] = NOT_COMPUTED
    return record


def compute_post_signal_proxy_diagnostic(*, hl_reference_price, ts_signal_ms,
                                         coinbase, kraken, capture_started_ts_ms,
                                         capture_completed_ts_ms, spread_bps_threshold):
    """G7-lite: asynchronous POST-SIGNAL HL-perp vs Coinbase+Kraken USD-spot diagnostic.

    The proxy is NEVER an at-entry/lookahead-safe/canonical/Chainlink-aligned reference.
    `ts_signal_ms` is IMMUTABLE and echoed unchanged (never shifted to a capture time). The
    proxy capture happens AFTER the signal; we persist capture-start/complete timestamps and
    the two SEPARATE signed skew metrics (started-vs-signal, lag-after-signal) — never collapsed.

    TRUE_CHAINLINK / Chainlink-aligned fields stay NOT_COMPUTED/null. The basis is computed
    (mode CHAINLINK_PROXY_ONLY, status PROXY_POST_SIGNAL_DIAGNOSTIC) ONLY when both USD spot legs
    are valid AND the Decimal spread guard passes; otherwise fail closed to NOT_COMPUTED.
    Decimal/string-safe (no float/REAL). Pure: no fetch, no DB, no clock.
    """
    ts_signal = _int(ts_signal_ms)
    started = _int(capture_started_ts_ms)
    completed = _int(capture_completed_ts_ms)
    hl = _dec(hl_reference_price)
    cb = _dec(coinbase)
    kr = _dec(kraken)
    thr = _dec(spread_bps_threshold)
    used = [n for n, v in (("coinbase", cb), ("kraken", kr)) if v is not None]

    rec = {
        "source_basis_mode": NOT_COMPUTED,
        "ts_signal_ms": ts_signal,                       # IMMUTABLE — echoed, never shifted
        "hl_reference_price": str(hl) if hl is not None else None,
        "proxy_source": "+".join(used) if used else None,
        "proxy_reference_price": None,
        "proxy_basis_hl_minus_proxy": None,
        "proxy_capture_status": PROXY_REFERENCE_UNAVAILABLE,
        "proxy_ts_provenance": PROXY_TS_PROVENANCE_CAPTURE_ONLY,
        "proxy_capture_started_ts_ms": started,
        "proxy_capture_completed_ts_ms": completed,
        "proxy_capture_started_vs_signal_ms":
            (started - ts_signal) if (started is not None and ts_signal is not None) else None,
        "proxy_lag_after_signal_ms":
            (completed - ts_signal) if (completed is not None and ts_signal is not None) else None,
        "proxy_labels": [CHAINLINK_PROXY_ONLY, CHAINLINK_PROXY_NOT_CANONICAL],
        # Chainlink-aligned fields are NEVER populated by proxy data.
        "chainlink_reference_price": None,
        "chainlink_capture_status": CHAINLINK_REFERENCE_UNAVAILABLE,
        "chainlink_access_mode": ACCESS_NOT_COMPUTED,
        "basis_hl_minus_chainlink": None,
        "chainlink_aligned_edge_status": NOT_COMPUTED,
    }

    # both USD spot legs required (single-source is not blessed); HL reference required
    if cb is None or kr is None or hl is None or thr is None or thr <= 0:
        rec["proxy_capture_status"] = PROXY_REFERENCE_UNAVAILABLE
        return rec

    mid = (cb + kr) / Decimal(2)
    spread_bps = (abs(cb - kr) / mid * _BPS) if mid != 0 else None
    if spread_bps is None or spread_bps > thr:
        rec["proxy_capture_status"] = PROXY_SPREAD_GUARD_FAIL
        return rec

    rec["proxy_reference_price"] = str(mid)
    rec["proxy_basis_hl_minus_proxy"] = str(hl - mid)
    rec["proxy_capture_status"] = PROXY_POST_SIGNAL_DIAGNOSTIC
    rec["source_basis_mode"] = CHAINLINK_PROXY_ONLY
    return rec
