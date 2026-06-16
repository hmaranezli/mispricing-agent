"""tests/test_reference_basket_4h_readiness_contract.py — 4h audited-readiness extension (TDD).

PUBLIC_REFERENCE_BASKET provisional research only. SAF/OFFLINE. Bu RED, ReferenceBasketNormalizer'ı
**audited 4h readiness context** ile genişletir: default interval="4h" hâlâ LIMITED_TIMING_APPROX kalır;
yalnız caller IN-MEMORY doğrulanmış audit/lineage context verince CORE_READY_FOR_4H'a yükselir; lineage
eksik/uyumsuzsa SESSİZCE onaylanmaz (LIMITED + quality_flags). Coinbase lineage = AGGREGATED_FROM_1H,
Kraken lineage = NATIVE_INTERVAL_240. 5m/15m davranışı DEĞİŞMEZ. CANLI fetch/secret/env/dosya-okuma YOK.

İlk RED: normalize_reference_basket henüz `audited_4h_context` keyword'ünü kabul etmez →
TypeError (unexpected keyword argument).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.reference_basket import normalize_reference_basket


def _spot(cb=100.0, kr=100.0):
    return {"coinbase": {"price": cb, "quote": "USD", "market": "spot", "ts_ms": 1000},
            "kraken": {"price": kr, "quote": "USD", "market": "spot", "ts_ms": 1000}}


def _ready_ctx(coinbase="AGGREGATED_FROM_1H", kraken="NATIVE_INTERVAL_240", ready=True):
    ctx = {"ready": ready}
    if coinbase is not None:
        ctx["coinbase_lineage"] = coinbase
    if kraken is not None:
        ctx["kraken_lineage"] = kraken
    return ctx


# ---- default 4h stays limited ----

def test_default_4h_remains_limited_timing_approx():
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="4h")
    assert r["interval_readiness"] == "LIMITED_TIMING_APPROX"


# ---- audited context promotes 4h ----

def test_4h_with_audited_context_core_ready():
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="4h",
                                   audited_4h_context=_ready_ctx())
    assert r["interval_readiness"] == "CORE_READY_FOR_4H"


def test_audited_4h_preserves_coinbase_lineage():
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="4h",
                                   audited_4h_context=_ready_ctx())
    assert r["audited_4h"]["coinbase_lineage"] == "AGGREGATED_FROM_1H"


def test_audited_4h_preserves_kraken_lineage():
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="4h",
                                   audited_4h_context=_ready_ctx())
    assert r["audited_4h"]["kraken_lineage"] == "NATIVE_INTERVAL_240"


# ---- partial / missing audit context stays limited ----

def test_partial_audit_context_remains_limited():
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="4h",
                                   audited_4h_context=_ready_ctx(ready=False))
    assert r["interval_readiness"] == "LIMITED_TIMING_APPROX"


# ---- lineage guards must not silently bless ----

def test_lineage_mismatch_blocks_core_ready():
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="4h",
                                   audited_4h_context=_ready_ctx(coinbase="NATIVE_INTERVAL_240"))
    assert r["interval_readiness"] == "LIMITED_TIMING_APPROX"
    assert any("lineage" in f for f in r["quality_flags"])


def test_coinbase_missing_aggregated_lineage_blocks_core_ready():
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="4h",
                                   audited_4h_context=_ready_ctx(coinbase=None))
    assert r["interval_readiness"] == "LIMITED_TIMING_APPROX"
    assert any("coinbase" in f and "lineage" in f for f in r["quality_flags"])


def test_kraken_missing_native_lineage_blocks_core_ready():
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="4h",
                                   audited_4h_context=_ready_ctx(kraken=None))
    assert r["interval_readiness"] == "LIMITED_TIMING_APPROX"
    assert any("kraken" in f and "lineage" in f for f in r["quality_flags"])


# ---- 5m/15m unchanged ----

def test_5m_core_ready_unchanged():
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="5m")
    assert r["interval_readiness"] == "CORE_READY_FOR_5M15M"


def test_15m_core_ready_unchanged():
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="15m")
    assert r["interval_readiness"] == "CORE_READY_FOR_5M15M"


def test_5m_ignores_4h_context():
    # audited_4h_context must not affect non-4h intervals
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="5m",
                                   audited_4h_context=_ready_ctx())
    assert r["interval_readiness"] == "CORE_READY_FOR_5M15M"
    assert r["audited_4h"] is None


# ---- spread guard unchanged for 4h ----

def test_spread_guard_unchanged_for_4h():
    # wide spread + a ready 4h context: spread guard still fails (orthogonal to readiness)
    r = normalize_reference_basket(_spot(cb=100.0, kr=102.0), spread_bps_threshold=50.0,
                                   interval="4h", audited_4h_context=_ready_ctx())
    assert r["status"] == "SPREAD_GUARD_FAIL"
    assert r["spread_guard_passed"] is False
    assert r["interval_readiness"] == "CORE_READY_FOR_4H"


# ---- metadata unchanged ----

def test_metadata_unchanged_with_4h_context():
    r = normalize_reference_basket(_spot(), spread_bps_threshold=500.0, interval="4h",
                                   audited_4h_context=_ready_ctx())
    md = r["metadata"]
    assert md["provisional"] is True
    assert md["public_reference_basket"] is True
    assert md["official_f1b"] is False
    assert md["chainlink_basis"] is False
    assert md["profitability"] is False
