"""
Gate G7b — offline source-basis contract tests.

  * NO network, NO live fetch, NO Chainlink credential/HMAC, NO DB, NO S1, NO wallet/capital.
  * TRUE_CHAINLINK basis is computed ONLY when exact decoded Chainlink Streams data is injected
    and passes lookahead/freshness/schema. Otherwise TRUE_CHAINLINK -> NOT_COMPUTED.
  * Coinbase+Kraken USD spot basket is reused as a DIAGNOSTIC PROXY ONLY, permanently labeled
    CHAINLINK_PROXY_ONLY / CHAINLINK_PROXY_NOT_CANONICAL. Proxy never fills the Chainlink-aligned edge.
  * All economic outputs are Decimal/string-safe (no float/REAL leakage).

Run with:  pytest -q tests/test_gateg7_source_basis.py
"""

from decimal import Decimal

import pytest

from analysis.forensic import gateg7_source_basis as sb

TS_SIGNAL = 1_000_000_000_000          # ms
MAX_AGE = 60_000                       # 60s freshness bound
SPREAD_BPS = Decimal("50")             # caller-supplied spread guard


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _hl(price="60010", ts_ms=TS_SIGNAL - 10_000):
    return {"price": price, "ts_ms": ts_ms}


def _decoded_report(price=60000, scale=10**8, ts_s=(TS_SIGNAL - 5_000) // 1000):
    """A 'crypto v3'-shaped already-decoded Chainlink report (scaled integer price)."""
    return {"feedID": "0xBTCUSD", "observationsTimestamp": ts_s, "price": price * scale}


def _chainlink(price=60000, scale=10**8, ts_s=(TS_SIGNAL - 5_000) // 1000):
    return {"report": _decoded_report(price, scale, ts_s), "price_scale": scale}


def _proxy(cb="60020", kr="60040", ts_ms=TS_SIGNAL - 8_000):
    return {"coinbase": cb, "kraken": kr, "ts_ms": ts_ms}


def _call(**over):
    base = dict(hl_reference=_hl(), ts_signal_ms=TS_SIGNAL,
                max_reference_age_ms=MAX_AGE, spread_bps_threshold=SPREAD_BPS)
    base.update(over)
    return sb.compute_source_basis(**base)


# ---------------------------------------------------------------------------
# TRUE_CHAINLINK path
# ---------------------------------------------------------------------------
def test_clean_chainlink_yields_true_chainlink_basis():
    r = _call(chainlink=_chainlink())
    assert r["source_basis_mode"] == sb.TRUE_CHAINLINK
    assert r["chainlink_capture_status"] == sb.STATUS_OK
    assert r["chainlink_access_mode"] == sb.ACCESS_INJECTED_DECODED
    # HL 60010 vs Chainlink 60000 -> +10 basis
    assert Decimal(r["chainlink_reference_price"]) == Decimal("60000")
    assert Decimal(r["basis_hl_minus_chainlink"]) == Decimal("10")
    assert r["chainlink_aligned_edge_status"] == sb.COMPUTED
    assert r["chainlink_reference_stale_flag"] == 0


def test_true_chainlink_takes_precedence_but_proxy_still_measured():
    r = _call(chainlink=_chainlink(), proxy=_proxy())
    assert r["source_basis_mode"] == sb.TRUE_CHAINLINK
    assert r["chainlink_aligned_edge_status"] == sb.COMPUTED
    # proxy basis is also recorded alongside, clearly labeled non-canonical
    assert r["proxy_capture_status"] == sb.STATUS_OK
    assert sb.CHAINLINK_PROXY_ONLY in r["proxy_labels"]
    assert sb.CHAINLINK_PROXY_NOT_CANONICAL in r["proxy_labels"]


# ---------------------------------------------------------------------------
# Chainlink fail-closed -> NOT_COMPUTED
# ---------------------------------------------------------------------------
def test_auth_required_blocks_to_not_computed():
    r = _call(chainlink={"status": "AUTH_REQUIRED"})
    assert r["source_basis_mode"] == sb.NOT_COMPUTED
    assert r["chainlink_capture_status"] == sb.CHAINLINK_AUTH_REQUIRED
    assert r["chainlink_access_mode"] == sb.ACCESS_AUTH_REQUIRED
    assert r["basis_hl_minus_chainlink"] is None
    assert r["chainlink_aligned_edge_status"] == sb.NOT_COMPUTED


def test_auth_blocked_status():
    r = _call(chainlink={"status": "AUTH_BLOCKED"})
    assert r["chainlink_capture_status"] == sb.CHAINLINK_SOURCE_AUTH_BLOCKED
    assert r["source_basis_mode"] == sb.NOT_COMPUTED


def test_missing_chainlink_unavailable():
    r = _call(chainlink=None)
    assert r["chainlink_capture_status"] == sb.CHAINLINK_REFERENCE_UNAVAILABLE
    assert r["source_basis_mode"] == sb.NOT_COMPUTED
    assert r["basis_hl_minus_chainlink"] is None


def test_stale_chainlink_not_computed():
    old_ts = (TS_SIGNAL - 5 * MAX_AGE) // 1000
    r = _call(chainlink=_chainlink(ts_s=old_ts))
    assert r["chainlink_capture_status"] == sb.CHAINLINK_REFERENCE_STALE
    assert r["chainlink_reference_stale_flag"] == 1
    assert r["source_basis_mode"] == sb.NOT_COMPUTED
    assert r["basis_hl_minus_chainlink"] is None


def test_chainlink_timestamp_after_signal_rejected():
    future = (TS_SIGNAL + 5_000) // 1000
    r = _call(chainlink=_chainlink(ts_s=future))
    assert r["chainlink_capture_status"] == sb.CHAINLINK_TIMESTAMP_AFTER_SIGNAL
    assert r["source_basis_mode"] == sb.NOT_COMPUTED
    assert r["basis_hl_minus_chainlink"] is None


def test_chainlink_schema_mismatch():
    bad = {"report": {"feedID": "0xBTCUSD"}, "price_scale": 10**8}  # no price/timestamp
    r = _call(chainlink=bad)
    assert r["chainlink_capture_status"] == sb.CHAINLINK_SCHEMA_MISMATCH
    assert r["source_basis_mode"] == sb.NOT_COMPUTED


# ---------------------------------------------------------------------------
# proxy path (CHAINLINK_PROXY_ONLY)
# ---------------------------------------------------------------------------
def test_clean_proxy_yields_proxy_only_labeled():
    r = _call(proxy=_proxy())
    assert r["source_basis_mode"] == sb.CHAINLINK_PROXY_ONLY
    assert r["proxy_capture_status"] == sb.STATUS_OK
    assert sb.CHAINLINK_PROXY_ONLY in r["proxy_labels"]
    assert sb.CHAINLINK_PROXY_NOT_CANONICAL in r["proxy_labels"]
    # midpoint of 60020/60040 = 60030; HL 60010 -> basis -20
    assert Decimal(r["proxy_reference_price"]) == Decimal("60030")
    assert Decimal(r["proxy_basis_hl_minus_proxy"]) == Decimal("-20")


def test_proxy_never_populates_chainlink_aligned_edge():
    r = _call(proxy=_proxy())
    assert r["chainlink_capture_status"] == sb.CHAINLINK_REFERENCE_UNAVAILABLE
    assert r["basis_hl_minus_chainlink"] is None
    assert r["chainlink_aligned_edge_status"] == sb.NOT_COMPUTED
    assert r["source_basis_mode"] == sb.CHAINLINK_PROXY_ONLY


def test_proxy_timestamp_after_signal_rejected():
    r = _call(proxy=_proxy(ts_ms=TS_SIGNAL + 1_000))
    assert r["proxy_capture_status"] == sb.PROXY_TIMESTAMP_AFTER_SIGNAL
    assert r["proxy_basis_hl_minus_proxy"] is None
    assert r["source_basis_mode"] == sb.NOT_COMPUTED


def test_proxy_stale_rejected():
    r = _call(proxy=_proxy(ts_ms=TS_SIGNAL - 10 * MAX_AGE))
    assert r["proxy_capture_status"] == sb.PROXY_REFERENCE_STALE
    assert r["proxy_basis_hl_minus_proxy"] is None
    assert r["source_basis_mode"] == sb.NOT_COMPUTED


def test_proxy_spread_guard_fail_rejected():
    # 60000 vs 61000 -> ~165 bps >> 50 bps guard
    r = _call(proxy=_proxy(cb="60000", kr="61000"))
    assert r["proxy_capture_status"] == sb.PROXY_SPREAD_GUARD_FAIL
    assert r["proxy_basis_hl_minus_proxy"] is None


def test_proxy_usdt_or_missing_source_unavailable():
    r = _call(proxy={"coinbase": None, "kraken": "60040", "ts_ms": TS_SIGNAL - 1_000})
    assert r["proxy_capture_status"] == sb.PROXY_REFERENCE_UNAVAILABLE
    assert r["source_basis_mode"] == sb.NOT_COMPUTED


# ---------------------------------------------------------------------------
# Decimal/string-safety
# ---------------------------------------------------------------------------
def test_all_numeric_outputs_are_string_safe_no_float():
    r = _call(chainlink=_chainlink(), proxy=_proxy())
    money_fields = ("chainlink_reference_price", "basis_hl_minus_chainlink",
                    "basis_hl_minus_chainlink_pct", "proxy_reference_price",
                    "proxy_basis_hl_minus_proxy", "hl_reference_price")
    for f in money_fields:
        v = r[f]
        if v is not None:
            assert isinstance(v, str), f"{f} must be str, got {type(v).__name__}"
            Decimal(v)  # round-trips exactly
            assert not isinstance(v, float)


def test_nothing_injected_is_fully_not_computed():
    r = _call()
    assert r["source_basis_mode"] == sb.NOT_COMPUTED
    assert r["chainlink_capture_status"] == sb.CHAINLINK_REFERENCE_UNAVAILABLE
    assert r["proxy_capture_status"] == sb.PROXY_REFERENCE_UNAVAILABLE
    assert r["basis_hl_minus_chainlink"] is None
    assert r["proxy_basis_hl_minus_proxy"] is None
