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
