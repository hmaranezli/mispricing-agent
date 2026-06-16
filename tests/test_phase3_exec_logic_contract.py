"""tests/test_phase3_exec_logic_contract.py — Phase 3 read-only execution sampling logic (TDD, offline).

PUBLIC_REFERENCE_BASKET / Phase 3 = EXECUTION readiness ONLY (no profitability/alpha). This pins the
PURE/OFFLINE parsing + aggregation + verdict logic for the throwaway sampler. NO network, NO secrets,
NO auth, NO orders/balances. Synthetic books only. Implementation lives under data/output/ (research-only),
NOT wired to production.

Implementation: tools/phase3_exec_logic.py (research-only, not wired to production).
"""
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO, "tools")
sys.path.insert(0, TOOLS_DIR)

import phase3_exec_logic as P  # noqa: E402

LOGIC_PATH = os.path.join(TOOLS_DIR, "phase3_exec_logic.py")
SAMPLER_PATH = os.path.join(TOOLS_DIR, "phase3_exec_sampler.py")


def _snap(asset="ETH", interval="5m", slug="eth-updown-5m-1000", token="0xtok",
          ts=1000, bids=None, asks=None):
    return {"asset": asset, "interval": interval, "market_slug": slug, "token_id": token,
            "utc_timestamp_ms": ts,
            "bids": [(0.48, 1000)] if bids is None else bids,
            "asks": [(0.52, 1000)] if asks is None else asks}


# ---- spread ----

def test_spread_bps_math():
    assert P.spread_bps(0.48, 0.52) == pytest.approx(800.0)


# ---- slippage walk per tier ----

def _deep_asks():
    return [(0.50, 1000), (0.51, 1000), (0.52, 1000)]  # level notionals 500 / 510 / 520


def test_slippage_walk_small_tiers_zero_slippage():
    for tier in (25, 50, 150, 500):
        r = P.slippage_walk(_deep_asks(), tier)
        assert r["fully_filled"] is True
        assert r["slippage_bps"] == pytest.approx(0.0)
        assert r["flag"] is None


def test_slippage_walk_1000_crosses_levels():
    r = P.slippage_walk(_deep_asks(), 1000)
    assert r["fully_filled"] is True
    # 500 @0.50 + 500 @0.51 -> vwap ~0.504951 -> ~99 bps vs best 0.50
    assert r["slippage_bps"] == pytest.approx(99.02, abs=0.5)


def test_depth_too_thin_on_insufficient_depth():
    r = P.slippage_walk(_deep_asks(), 2000)  # total capacity 1530 < 2000
    assert r["fully_filled"] is False
    assert r["flag"] == "DEPTH_TOO_THIN"


# ---- book classification / tagging ----

def test_two_sided_book_ok():
    assert P.classify_book(_snap()) == "TWO_SIDED"


def test_one_sided_book_tagging():
    assert P.classify_book(_snap(asks=[])) == "ONE_SIDED_BOOK"
    assert P.classify_book(_snap(bids=[])) == "ONE_SIDED_BOOK"


def test_empty_book_insufficient():
    assert P.classify_book(_snap(bids=[], asks=[])) == "INSUFFICIENT_BOOK_DATA"


def test_lineage_missing_tagging():
    s = _snap()
    del s["token_id"]
    assert P.classify_book(s) == "LINEAGE_MISSING"
    s2 = _snap()
    s2["utc_timestamp_ms"] = None
    assert P.classify_book(s2) == "LINEAGE_MISSING"


# ---- per-slug cap + diversity ----

def test_per_slug_cap_enforcement():
    snaps = [_snap(slug="A", ts=i) for i in range(25)]
    kept, dropped = P.apply_per_slug_cap(snaps, cap=20)
    assert len(kept) == 20
    assert dropped == 5


def test_per_slug_cap_keeps_all_when_under_cap():
    snaps = [_snap(slug="A", ts=i) for i in range(5)]
    kept, dropped = P.apply_per_slug_cap(snaps, cap=20)
    assert len(kept) == 5
    assert dropped == 0


def test_insufficient_market_diversity():
    assert P.diversity_status(unique_slugs=5, min_unique_slugs=10) == "INSUFFICIENT_MARKET_DIVERSITY"
    assert P.diversity_status(unique_slugs=20, min_unique_slugs=10) == "OK"


# ---- snapshot type classification ----

def test_snapshot_type_classification():
    snaps = [_snap(slug="A", ts=1), _snap(slug="A", ts=2), _snap(slug="B", ts=3)]
    labels = P.classify_snapshot_types(snaps)
    assert labels == ["new_market_cross_section", "same_slug_time_series", "new_market_cross_section"]


# ---- no cell merging ----

def test_no_cell_merging_across_asset():
    mixed = [_snap(asset="ETH"), _snap(asset="SOL")]
    with pytest.raises(ValueError):
        P.aggregate_cell(mixed)


def test_no_cell_merging_across_interval():
    mixed = [_snap(interval="5m"), _snap(interval="15m")]
    with pytest.raises(ValueError):
        P.aggregate_cell(mixed)


# ---- percentiles ----

def test_percentiles_correctness():
    vals = list(range(1, 101))  # 1..100
    pc = P.percentiles(vals)
    assert pc["p50"] == pytest.approx(50.5, abs=1.0)
    assert pc["p90"] == pytest.approx(90.1, abs=1.0)
    assert pc["p95"] == pytest.approx(95.05, abs=1.0)
    assert pc["n"] == 100


# ---- verdict ----

def _ready_report(asset="ETH", interval="5m"):
    return {"asset": asset, "interval": interval, "n": 300, "unique_slugs": 20,
            "per_slug_cap_respected": True, "two_sided_ratio": 0.85, "p95_spread_bps": 25.0,
            "fill_ratios": {"25": 0.95, "50": 0.95, "150": 0.95},
            "lineage_complete": True, "diversity_status": "OK"}


def test_verdict_execution_ready_all_pass():
    status, fails = P.verdict(_ready_report())
    assert status == "EXECUTION_READY"
    assert fails == []


def test_verdict_not_ready_when_spread_too_wide():
    rep = _ready_report()
    rep["p95_spread_bps"] = 40.0  # ETH 5m gate is 30
    status, fails = P.verdict(rep)
    assert status == "EXECUTION_NOT_READY"
    assert "spread_too_wide" in fails


def test_verdict_not_ready_when_n_below_target():
    rep = _ready_report()
    rep["n"] = 100
    status, fails = P.verdict(rep)
    assert status == "EXECUTION_NOT_READY"
    assert "n_below_target" in fails


def test_verdict_not_ready_when_depth_too_thin():
    rep = _ready_report()
    rep["fill_ratios"]["150"] = 0.5
    status, fails = P.verdict(rep)
    assert status == "EXECUTION_NOT_READY"
    assert any("depth_too_thin" in f for f in fails)


def test_verdict_control_cell_spread_not_gating():
    # ETH 15m is control/report-only: a wide p95 spread must NOT fail it
    rep = _ready_report(interval="15m")
    rep["n"] = 100
    rep["unique_slugs"] = 8
    rep["p95_spread_bps"] = 999.0
    status, fails = P.verdict(rep)
    assert "spread_too_wide" not in fails
    assert status == "EXECUTION_READY"


# ---- safety: static scan ----

def test_safety_static_scan_no_forbidden_symbols():
    # Concrete auth/secret/order/balance *code symbols* (prose disclaimers like "no secrets" are fine).
    for path in (LOGIC_PATH, SAMPLER_PATH):
        with open(path, encoding="utf-8") as f:
            src = f.read()
        for bad in ("api_key", "api_secret", "private_key", "passphrase",
                    "place_order", "create_order", "get_balance",
                    "os.environ", "getenv", "load_dotenv"):
            assert bad not in src, f"{os.path.basename(path)} must not reference {bad!r}"


# ---- safety: isolation (not imported by production) ----

def test_safety_isolation_not_imported_by_production():
    import subprocess
    # Phase 3 implementation is research-only under tools/. Production = repo minus the research dir
    # (tools/), tests, graphify-out, .git. Filter by PATH (grep --exclude-dir matches basename).
    res = subprocess.run(["grep", "-rIl", "--include=*.py", "phase3_exec", REPO],
                         capture_output=True, text=True)
    hits = [ln for ln in res.stdout.splitlines()
            if ln.strip()
            and "/tools/" not in ln
            and "/tests/" not in ln
            and "/data/output/" not in ln
            and "/graphify-out/" not in ln
            and "/.git/" not in ln]
    assert hits == [], f"Phase 3 logic must not be imported by production: {hits}"
