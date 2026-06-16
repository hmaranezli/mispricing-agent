"""tests/test_reference_basket_normalizer_contract.py — ReferenceBasketNormalizer (TDD).

PUBLIC_REFERENCE_BASKET provisional research only. SAF/OFFLINE normalizer: spot kaynaklarını (Coinbase +
Kraken, USD-only) iki-kaynak midpoint + spread guard ile birleştirir; perp (Hyperliquid) AYRI girdi olarak
gelir; temiz basis = HL_perp - spot_reference. CANLI fetch/secret/env YOK. build_basis_windows YOK.
official_f1b YOK. Kâr/arbitraj iddiası YOK.

Hedef seam:
    analysis.reference_basket.normalize_reference_basket(
        spot_sources, perp=None, *, spread_bps_threshold, anchor_ms=None,
        freshness_tolerance_ms=None, interval=None)

İlk RED: modül/fonksiyon yok → ImportError (eksik üretim seam'i).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.reference_basket import normalize_reference_basket

MODULE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "analysis", "reference_basket.py")


def _spot(cb_price, kr_price, *, cb_quote="USD", kr_quote="USD",
          cb_market="spot", kr_market="spot", cb_ts=1000, kr_ts=1000):
    out = {}
    if cb_price is not None:
        out["coinbase"] = {"price": cb_price, "quote": cb_quote, "market": cb_market, "ts_ms": cb_ts}
    if kr_price is not None:
        out["kraken"] = {"price": kr_price, "quote": kr_quote, "market": kr_market, "ts_ms": kr_ts}
    return out


# ---- core: two-source midpoint + spread ----

def test_two_source_usd_midpoint():
    r = normalize_reference_basket(_spot(100.0, 102.0), spread_bps_threshold=500.0)
    assert r["status"] == "OK"
    assert r["spot_reference"] == 101.0
    assert sorted(r["used_spot_sources"]) == ["coinbase", "kraken"]


def test_spread_bps_calculation():
    r = normalize_reference_basket(_spot(100.0, 102.0), spread_bps_threshold=500.0)
    expected = abs(100.0 - 102.0) / 101.0 * 1e4
    assert round(r["spread_bps"], 6) == round(expected, 6)


def test_spread_guard_pass_under_threshold():
    r = normalize_reference_basket(_spot(100.0, 100.05), spread_bps_threshold=50.0)
    assert r["status"] == "OK"
    assert r["spread_guard_passed"] is True


def test_spread_guard_fail_over_threshold():
    r = normalize_reference_basket(_spot(100.0, 102.0), spread_bps_threshold=50.0)
    assert r["status"] == "SPREAD_GUARD_FAIL"
    assert r["spread_guard_passed"] is False
    assert any("spread_guard" in f for f in r["quality_flags"])


# ---- freshness / timestamp validation ----

def test_freshness_validation_flags_and_excludes_stale():
    spot = _spot(100.0, 102.0, cb_ts=10500, kr_ts=20000)
    r = normalize_reference_basket(spot, spread_bps_threshold=500.0,
                                   anchor_ms=10000, freshness_tolerance_ms=2000)
    # kraken ts 20000 is >2000 from anchor 10000 -> stale -> excluded
    assert r["status"] == "DEGRADED_SINGLE_SOURCE"
    assert r["used_spot_sources"] == ["coinbase"]
    assert any("stale" in f and "kraken" in f for f in r["quality_flags"])


# ---- degraded / missing ----

def test_missing_coinbase_degrades_single_source():
    r = normalize_reference_basket(_spot(None, 102.0), spread_bps_threshold=500.0)
    assert r["status"] == "DEGRADED_SINGLE_SOURCE"
    assert r["spot_reference"] == 102.0
    assert r["spread_bps"] is None
    assert r["used_spot_sources"] == ["kraken"]


def test_missing_kraken_degrades_single_source():
    r = normalize_reference_basket(_spot(100.0, None), spread_bps_threshold=500.0)
    assert r["status"] == "DEGRADED_SINGLE_SOURCE"
    assert r["spot_reference"] == 100.0
    assert r["used_spot_sources"] == ["coinbase"]


def test_both_sources_missing_returns_missing_reference():
    r = normalize_reference_basket(_spot(None, None), spread_bps_threshold=500.0)
    assert r["status"] == "MISSING_REFERENCE"
    assert r["spot_reference"] is None


# ---- quote / market guards ----

def test_usd_usdt_quote_mixing_excluded_and_flagged():
    r = normalize_reference_basket(_spot(100.0, 102.0, kr_quote="USDT"), spread_bps_threshold=500.0)
    # kraken is USDT -> excluded from USD core
    assert r["status"] == "DEGRADED_SINGLE_SOURCE"
    assert r["used_spot_sources"] == ["coinbase"]
    assert any("quote" in f and "kraken" in f for f in r["quality_flags"])


def test_spot_perp_raw_mixing_excluded_and_flagged():
    r = normalize_reference_basket(_spot(100.0, 102.0, kr_market="perp"), spread_bps_threshold=500.0)
    # a perp-market entry must NOT be averaged into the spot midpoint
    assert r["status"] == "DEGRADED_SINGLE_SOURCE"
    assert r["used_spot_sources"] == ["coinbase"]
    assert any(("perp" in f or "market" in f) and "kraken" in f for f in r["quality_flags"])


# ---- clean basis from separate spot/perp ----

def test_clean_basis_from_separate_spot_perp():
    spot = _spot(100.0, 100.0)
    perp = {"source": "hyperliquid", "price": 100.5, "quote": "USD", "market": "perp", "ts_ms": 1000}
    r = normalize_reference_basket(spot, perp=perp, spread_bps_threshold=500.0)
    assert r["spot_reference"] == 100.0
    assert r["perp_reference"] == 100.5
    assert round(r["basis_bps"], 6) == round((100.5 - 100.0) / 100.0 * 1e4, 6)


def test_basis_none_without_perp():
    r = normalize_reference_basket(_spot(100.0, 100.0), spread_bps_threshold=500.0)
    assert r["basis_bps"] is None
    assert r["perp_reference"] is None


# ---- interval readiness ----

def test_interval_readiness_5m_core_ready():
    r = normalize_reference_basket(_spot(100.0, 100.0), spread_bps_threshold=500.0, interval="5m")
    assert r["interval_readiness"] == "CORE_READY_FOR_5M15M"


def test_interval_readiness_15m_core_ready():
    r = normalize_reference_basket(_spot(100.0, 100.0), spread_bps_threshold=500.0, interval="15m")
    assert r["interval_readiness"] == "CORE_READY_FOR_5M15M"


def test_interval_readiness_4h_limited():
    r = normalize_reference_basket(_spot(100.0, 100.0), spread_bps_threshold=500.0, interval="4h")
    assert r["interval_readiness"] == "LIMITED_TIMING_APPROX"


# ---- metadata ----

def test_metadata_flags():
    r = normalize_reference_basket(_spot(100.0, 100.0), spread_bps_threshold=500.0)
    md = r["metadata"]
    assert md["provisional"] is True
    assert md["public_reference_basket"] is True
    assert md["official_f1b"] is False
    assert md["chainlink_basis"] is False
    assert md["profitability"] is False


# ---- input validation ----

def test_invalid_threshold_raises():
    with pytest.raises(ValueError):
        normalize_reference_basket(_spot(100.0, 100.0), spread_bps_threshold=0)


def test_bool_price_rejected_as_non_numeric():
    # bool is not a price -> coinbase dropped as missing, kraken usable -> degraded
    r = normalize_reference_basket(_spot(True, 100.0), spread_bps_threshold=500.0)
    assert r["status"] == "DEGRADED_SINGLE_SOURCE"
    assert r["used_spot_sources"] == ["kraken"]


# ---- no network/client/env dependency ----

def test_no_network_client_or_env_dependency():
    with open(MODULE_PATH, encoding="utf-8") as f:
        src = f.read()
    for forbidden in ("aiohttp", "requests", "httpx", "urllib", "socket",
                      "os.environ", "getenv", "build_basis_windows"):
        assert forbidden not in src, f"normalizer must not reference {forbidden!r}"
