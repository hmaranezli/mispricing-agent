"""tests/test_phase3d_pilot_contract.py — Phase 3D2 bounded pilot runner (TDD, offline).

Phase 3D pilot = BOUNDED (<=11 requests) READ-ONLY collection of ETH 5m books to validate the
diversity / time-series / pacing / partial-fail-safe regime. ALL tests use INJECTED fakes — NO network,
NO endpoints, NO secrets/auth/orders. Pilot verdict is a CLOSED set and NEVER a readiness/economics verdict.

İlk RED: pilot_eth5m / RateLimited henüz yok → AttributeError/ImportError.
"""
import asyncio
import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO, "tools")
sys.path.insert(0, TOOLS_DIR)

import phase3_exec_sampler as S  # noqa: E402

SAMPLER_PATH = os.path.join(TOOLS_DIR, "phase3_exec_sampler.py")

REQUIRED_FIELDS = (
    "verdict", "target_snapshots", "snapshots_written", "unique_slugs", "snapshots_per_slug",
    "snapshot_type_split", "request_count", "max_total_requests", "discovery_requests",
    "book_requests", "books_ok", "books_failed", "asset", "interval", "failure_modes",
    "partial", "output_jsonl", "output_summary", "timestamp_utc",
    "official_f1b", "profitability", "phase",
)
ALLOWED = {"PILOT_SAMPLE_ONLY", "PILOT_INSUFFICIENT_MARKET_DIVERSITY",
           "PILOT_RATE_LIMITED_PARTIAL", "PILOT_FAILED"}


def _markets(n, single=False):
    if single:
        return [{"market_slug": "eth-updown-5m-SINGLE", "token_id": "0xSINGLE"}]
    return [{"market_slug": f"eth-updown-5m-{i}", "token_id": f"0x{i}"} for i in range(1, n + 1)]


def _disc(markets):
    async def d(budget):
        budget.spend("gamma")
        return list(markets)
    return d


def _book(two_sided=True, rate_after=None, fail_after=None, token_none=False):
    state = {"n": 0}

    async def fb(token, budget):
        budget.spend("book")
        state["n"] += 1
        if rate_after is not None and state["n"] > rate_after:
            raise S.RateLimited("429")
        if fail_after is not None and state["n"] > fail_after:
            raise RuntimeError("boom")
        if two_sided:
            return {"bids": [{"price": "0.48", "size": "100"}], "asks": [{"price": "0.52", "size": "100"}]}
        return {"bids": [], "asks": []}
    return fb


class _Sleeps:
    def __init__(self):
        self.calls = []

    async def __call__(self, s):
        self.calls.append(s)


def _run(**kw):
    kw.setdefault("sleep_fn", _Sleeps())
    return asyncio.run(S.pilot_eth5m(**kw)), kw["sleep_fn"]


# ---- budget / sub-caps ----

def test_budget_shared_and_aborts_before_request_12(tmp_path):
    b = S.RequestBudget(11)
    summary, _ = _run(discover_fn=_disc(_markets(12)), fetch_book_fn=_book(),
                      output_dir=str(tmp_path), timestamp_fn=lambda: 100, budget=b)
    assert summary["request_count"] == 11        # 1 discovery + 10 books
    assert summary["discovery_requests"] == 1
    assert summary["book_requests"] == 10
    assert b.count == 11                          # never reached 12
    assert summary["max_total_requests"] == 11


def test_discovery_and_book_subcaps_enforced(tmp_path):
    summary, _ = _run(discover_fn=_disc(_markets(20)), fetch_book_fn=_book(),
                      output_dir=str(tmp_path), timestamp_fn=lambda: 101)
    assert summary["discovery_requests"] <= 1
    assert summary["book_requests"] <= 10


# ---- pacing (injected, no real waiting) ----

def test_pacing_cross_market_uses_2s(tmp_path):
    # 10 distinct slugs -> 10 cross-market books -> 9 inter-call sleeps, all pacing_s=2.0
    summary, sleeps = _run(discover_fn=_disc(_markets(10)), fetch_book_fn=_book(),
                           output_dir=str(tmp_path), timestamp_fn=lambda: 102)
    assert sleeps.calls == [2.0] * 9


def test_pacing_time_series_uses_ts_interval(tmp_path):
    summary, sleeps = _run(discover_fn=_disc(_markets(1, single=True)), fetch_book_fn=_book(),
                           output_dir=str(tmp_path), timestamp_fn=lambda: 103)
    # single slug -> 10 snapshots -> 9 inter-call sleeps, all TS_INTERVAL_S=20.0
    assert sleeps.calls == [20.0] * 9


# ---- time-series labels ----

def test_time_series_fallback_labels(tmp_path):
    summary, _ = _run(discover_fn=_disc(_markets(1, single=True)), fetch_book_fn=_book(),
                      output_dir=str(tmp_path), timestamp_fn=lambda: 104)
    split = summary["snapshot_type_split"]
    assert split["new_market_cross_section"] == 1
    assert split["same_slug_time_series"] == 9
    assert summary["unique_slugs"] == 1


# ---- diversity floor ----

def test_diversity_floor_single_slug_preserves_sample(tmp_path):
    summary, _ = _run(discover_fn=_disc(_markets(1, single=True)), fetch_book_fn=_book(),
                      output_dir=str(tmp_path), timestamp_fn=lambda: 105)
    assert summary["verdict"] == "PILOT_INSUFFICIENT_MARKET_DIVERSITY"
    assert summary["snapshots_written"] == 10           # sample preserved, not discarded
    assert os.path.exists(summary["output_jsonl"])


def test_cross_market_sample_only(tmp_path):
    summary, _ = _run(discover_fn=_disc(_markets(10)), fetch_book_fn=_book(),
                      output_dir=str(tmp_path), timestamp_fn=lambda: 106)
    assert summary["verdict"] == "PILOT_SAMPLE_ONLY"
    assert summary["unique_slugs"] >= 2
    assert summary["snapshots_written"] == 10


# ---- partial / fail-safe ----

def test_rate_limited_partial_preserves_jsonl(tmp_path):
    # 2 books ok, then rate-limited on the 3rd
    summary, _ = _run(discover_fn=_disc(_markets(10)), fetch_book_fn=_book(rate_after=2),
                      output_dir=str(tmp_path), timestamp_fn=lambda: 107)
    assert summary["verdict"] == "PILOT_RATE_LIMITED_PARTIAL"
    assert summary["partial"] is True
    assert "RATE_LIMITED" in summary["failure_modes"]
    with open(summary["output_jsonl"]) as f:
        rows = [l for l in f if l.strip()]
    assert len(rows) == 2                                 # preserved successful snapshots
    assert os.path.exists(summary["output_summary"])      # partial summary written


def test_unexpected_exception_writes_partial_failed(tmp_path):
    summary, _ = _run(discover_fn=_disc(_markets(10)), fetch_book_fn=_book(fail_after=1),
                      output_dir=str(tmp_path), timestamp_fn=lambda: 108)
    assert summary["verdict"] == "PILOT_FAILED"
    assert summary["partial"] is True
    with open(summary["output_jsonl"]) as f:
        rows = [l for l in f if l.strip()]
    assert len(rows) == 1                                 # the one good snapshot preserved


# ---- no overwrite ----

def test_no_overwrite_guard(tmp_path):
    pre = tmp_path / "phase3d_pilot_snapshots_109.jsonl"
    pre.write_text("ORIGINAL", encoding="utf-8")
    summary, _ = _run(discover_fn=_disc(_markets(5)), fetch_book_fn=_book(),
                      output_dir=str(tmp_path), timestamp_fn=lambda: 109)
    assert summary["verdict"] == "PILOT_FAILED"
    assert "OUTPUT_EXISTS_NO_OVERWRITE" in summary["failure_modes"]
    assert pre.read_text(encoding="utf-8") == "ORIGINAL"


# ---- lineage ----

def test_lineage_missing_tagged(tmp_path):
    markets = [{"market_slug": "eth-updown-5m-X", "token_id": None}]
    summary, _ = _run(discover_fn=_disc(markets), fetch_book_fn=_book(),
                      output_dir=str(tmp_path), timestamp_fn=lambda: 110)
    assert "LINEAGE_MISSING" in summary["failure_modes"]


# ---- schema + flags + closed verdict ----

def test_summary_schema_and_flags(tmp_path):
    summary, _ = _run(discover_fn=_disc(_markets(10)), fetch_book_fn=_book(),
                      output_dir=str(tmp_path), timestamp_fn=lambda: 111)
    for field in REQUIRED_FIELDS:
        assert field in summary, f"missing field {field!r}"
    assert summary["verdict"] in ALLOWED
    assert summary["asset"] == "ETH" and summary["interval"] == "5m"
    assert summary["official_f1b"] is False
    assert summary["profitability"] is False
    assert summary["phase"] == "3D_pilot"
    assert summary["target_snapshots"] == 10


# ---- Phase 3D3 multi-asset bounded discovery ----

ALLOWED_3D3 = {"PILOT_SAMPLE_ONLY", "PILOT_INSUFFICIENT_MARKET_DIVERSITY",
               "PILOT_RATE_LIMITED_PARTIAL", "PILOT_FAILED"}
_3D3_ASSETS = ("BTC", "ETH", "SOL", "XRP")


def _ma_markets(slugs_per_asset=1):
    out = []
    for a in _3D3_ASSETS:
        for j in range(1, slugs_per_asset + 1):
            out.append({"asset": a, "market_slug": f"{a.lower()}-updown-5m-{j}",
                        "token_id": f"0x{a}{j}"})
    return out


def _ma_disc(markets):
    async def d(budget):
        budget.spend("gamma")
        return list(markets)
    return d


def _ma_book(two_sided_assets=None):
    """token-aware fake book; two_sided only for tokens whose asset is in two_sided_assets (None=all)."""
    log = []

    async def fb(token, budget):
        budget.spend("book")
        log.append(token)
        asset = next((a for a in _3D3_ASSETS if token.startswith(f"0x{a}")), None)
        if two_sided_assets is None or asset in two_sided_assets:
            return {"bids": [{"price": "0.48", "size": "100"}], "asks": [{"price": "0.52", "size": "100"}]}
        return {"bids": [], "asks": []}
    fb.log = log
    return fb


def _run_3d3(**kw):
    kw.setdefault("sleep_fn", _Sleeps())
    return asyncio.run(S.pilot_3d3_multi_asset(**kw))


def _asset_of(token):
    return next((a for a in _3D3_ASSETS if token.startswith(f"0x{a}")), None)


def test_3d3_processes_all_four_assets_first(tmp_path):
    book = _ma_book()
    summary = _run_3d3(discover_fn=_ma_disc(_ma_markets(1)), fetch_book_fn=book,
                       output_dir=str(tmp_path), timestamp_fn=lambda: 300)
    # first 4 book fetches must cover all four assets (fairness, no starvation)
    first4_assets = {_asset_of(t) for t in book.log[:4]}
    assert first4_assets == set(_3D3_ASSETS)


def test_3d3_no_single_asset_consumes_entire_budget(tmp_path):
    book = _ma_book()
    summary = _run_3d3(discover_fn=_ma_disc(_ma_markets(1)), fetch_book_fn=book,
                       output_dir=str(tmp_path), timestamp_fn=lambda: 301)
    bba = summary["books_by_asset"]
    total_books = sum(bba.values())
    assert total_books > 0
    assert max(bba.values()) < total_books   # no asset took everything
    assert len([a for a in bba if bba[a] > 0]) >= 2


def test_3d3_summary_reports_per_asset_counts(tmp_path):
    summary = _run_3d3(discover_fn=_ma_disc(_ma_markets(1)), fetch_book_fn=_ma_book(),
                       output_dir=str(tmp_path), timestamp_fn=lambda: 302)
    for field in ("assets_seen", "unique_assets", "books_by_asset", "snapshots_by_asset"):
        assert field in summary, f"missing {field!r}"
    assert set(summary["assets_seen"]) == set(_3D3_ASSETS)
    assert summary["unique_assets"] == 4
    assert sum(summary["books_by_asset"].values()) == summary["book_requests"]
    assert sum(summary["snapshots_by_asset"].values()) == summary["snapshots_written"]


def test_3d3_sample_only_when_enough_unique(tmp_path):
    summary = _run_3d3(discover_fn=_ma_disc(_ma_markets(1)), fetch_book_fn=_ma_book(),
                       output_dir=str(tmp_path), timestamp_fn=lambda: 303)
    assert summary["verdict"] == "PILOT_SAMPLE_ONLY"
    assert summary["unique_slugs"] >= S.MIN_PILOT_UNIQUE_SLUGS


def test_3d3_single_usable_slug_insufficient_diversity(tmp_path):
    # only BTC books are two-sided; ETH/SOL/XRP one-sided -> 1 unique usable slug
    summary = _run_3d3(discover_fn=_ma_disc(_ma_markets(1)), fetch_book_fn=_ma_book(two_sided_assets={"BTC"}),
                       output_dir=str(tmp_path), timestamp_fn=lambda: 304)
    assert summary["verdict"] == "PILOT_INSUFFICIENT_MARKET_DIVERSITY"
    assert summary["verdict"] != "PILOT_SAMPLE_ONLY"


def test_3d3_budget_bounded_at_20(tmp_path):
    b = S.RequestBudget(S.PILOT_3D3_MAX_TOTAL_REQUESTS)
    summary = _run_3d3(discover_fn=_ma_disc(_ma_markets(6)), fetch_book_fn=_ma_book(),
                       output_dir=str(tmp_path), timestamp_fn=lambda: 305, budget=b)
    assert summary["max_total_requests"] == 20
    assert summary["request_count"] <= 20
    assert b.count <= 20


def test_3d3_outputs_under_data_output_by_default():
    sample = os.path.join(S.OUT_DIR, "phase3d3_pilot_summary_1.json").replace(os.sep, "/")
    assert "data/output" in sample


def test_3d3_verdict_in_closed_set(tmp_path):
    summary = _run_3d3(discover_fn=_ma_disc(_ma_markets(1)), fetch_book_fn=_ma_book(),
                       output_dir=str(tmp_path), timestamp_fn=lambda: 306)
    assert summary["verdict"] in ALLOWED_3D3
    assert summary["official_f1b"] is False
    assert summary["profitability"] is False


# ---- Phase 3D4 per-asset discovery expansion ----

def _d4_disc(candidates_by_asset):
    """Injectable per-asset discovery: one call per asset, spends 1 each."""
    async def d(asset, budget):
        budget.spend("gamma")
        n = candidates_by_asset.get(asset, 0)
        return [{"asset": asset, "market_slug": f"{asset.lower()}-updown-5m-{j}",
                 "token_id": f"0x{asset}{j}"} for j in range(1, n + 1)]
    return d


def _run_3d4(**kw):
    kw.setdefault("sleep_fn", _Sleeps())
    return asyncio.run(S.pilot_3d4_multi_asset_discovery(**kw))


def test_3d4_all_assets_discovered_and_round_robin(tmp_path):
    book = _ma_book()
    summary = _run_3d4(discover_asset_fn=_d4_disc({"BTC": 1, "ETH": 1, "SOL": 1, "XRP": 1}),
                       fetch_book_fn=book, output_dir=str(tmp_path), timestamp_fn=lambda: 400)
    assert set(summary["assets_seen"]) == set(_3D3_ASSETS)
    assert summary["unique_assets"] == 4
    # first 4 book fetches cover all four assets (round-robin fairness)
    assert {_asset_of(t) for t in book.log[:4]} == set(_3D3_ASSETS)
    assert summary["request_count"] <= 20
    assert summary["discovery_requests"] == 4
    assert summary["verdict"] == "PILOT_SAMPLE_ONLY"


def test_3d4_single_asset_insufficient_diversity(tmp_path):
    summary = _run_3d4(discover_asset_fn=_d4_disc({"BTC": 1}), fetch_book_fn=_ma_book(),
                       output_dir=str(tmp_path), timestamp_fn=lambda: 401)
    assert summary["verdict"] == "PILOT_INSUFFICIENT_MARKET_DIVERSITY"
    assert summary["verdict"] != "PILOT_SAMPLE_ONLY"
    assert summary["unique_slugs"] < S.MIN_PILOT_UNIQUE_SLUGS


def test_3d4_summary_per_asset_fields(tmp_path):
    summary = _run_3d4(discover_asset_fn=_d4_disc({"BTC": 1, "ETH": 1, "SOL": 0, "XRP": 0}),
                       fetch_book_fn=_ma_book(), output_dir=str(tmp_path), timestamp_fn=lambda: 402)
    for field in ("discovery_by_asset", "candidates_by_asset", "books_by_asset", "snapshots_by_asset"):
        assert field in summary, f"missing {field!r}"
    # all four assets were probed for discovery (one call each)
    assert set(summary["discovery_by_asset"].keys()) == set(_3D3_ASSETS)
    # candidates recorded per asset incl. zeros
    assert summary["candidates_by_asset"]["SOL"] == 0
    assert summary["candidates_by_asset"]["XRP"] == 0
    assert summary["candidates_by_asset"]["BTC"] == 1


def test_3d4_budget_bounded_at_20(tmp_path):
    b = S.RequestBudget(S.PILOT_3D4_MAX_TOTAL_REQUESTS)
    # all one-sided -> book attempts continue to the cap; verify ceiling never exceeded
    summary = _run_3d4(discover_asset_fn=_d4_disc({"BTC": 6, "ETH": 6, "SOL": 6, "XRP": 6}),
                       fetch_book_fn=_ma_book(two_sided_assets=set()),
                       output_dir=str(tmp_path), timestamp_fn=lambda: 403, budget=b)
    assert summary["max_total_requests"] == 20
    assert summary["request_count"] <= 20
    assert b.count <= 20


def test_3d4_verdict_in_closed_set_and_flags(tmp_path):
    summary = _run_3d4(discover_asset_fn=_d4_disc({"BTC": 1, "ETH": 1, "SOL": 1, "XRP": 1}),
                       fetch_book_fn=_ma_book(), output_dir=str(tmp_path), timestamp_fn=lambda: 404)
    assert summary["verdict"] in ALLOWED_3D3
    assert summary["official_f1b"] is False
    assert summary["profitability"] is False
    assert summary["phase"] == "3D4_pilot"


def test_3d4_outputs_under_data_output_by_default():
    sample = os.path.join(S.OUT_DIR, "phase3d4_pilot_summary_1.json").replace(os.sep, "/")
    assert "data/output" in sample


# ---- output directory hygiene: artifacts default under data/output, not tools/ ----

def test_default_output_dir_is_data_output_not_tools():
    norm = S.OUT_DIR.replace(os.sep, "/").rstrip("/")
    assert norm.endswith("data/output"), f"default OUT_DIR should be data/output, got {norm}"
    assert not norm.endswith("/tools"), "default OUT_DIR must not be tools/"


def test_pilot_default_filenames_built_under_data_output():
    sample = os.path.join(S.OUT_DIR, "phase3d_pilot_snapshots_123.jsonl").replace(os.sep, "/")
    assert "data/output" in sample
    summary = os.path.join(S.OUT_DIR, "phase3d_pilot_summary_123.json").replace(os.sep, "/")
    assert "data/output" in summary


# ---- static scan: forbidden readiness literals absent ----

def test_no_readiness_literals_in_sampler():
    with open(SAMPLER_PATH, encoding="utf-8") as f:
        src = f.read()
    assert "EXECUTION_READY" not in src
    assert "ECONOMICS_READY_FOR_PAPER" not in src


# ---- CLI guard (refusal paths only; pilot/dry-run never invoked) ----

def test_cli_refuses_no_args():
    r = subprocess.run([sys.executable, SAMPLER_PATH], capture_output=True, text=True)
    assert r.returncode != 0


def test_cli_refuses_unknown_arg():
    r = subprocess.run([sys.executable, SAMPLER_PATH, "--nope"], capture_output=True, text=True)
    assert r.returncode != 0


def test_cli_pilot_branch_exists_but_not_run():
    with open(SAMPLER_PATH, encoding="utf-8") as f:
        src = f.read()
    assert "--pilot-eth5m" in src
    assert "--dry-run-eth5m" in src   # dry-run kept
