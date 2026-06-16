"""tests/test_phase3_dryrun_contract.py — Phase 3C small read-only dry-run runner (TDD, offline).

Phase 3C = bounded (<=4 public requests) READ-ONLY smoke test of the sampling pipeline. These tests
exercise the orchestration with INJECTED fakes — NO network, NO endpoints, NO secrets/auth/orders.
Dry-run verdict is a CLOSED set {SAMPLE_ONLY, INSUFFICIENT_SAMPLE, DRY_RUN_FAILED} and must NEVER emit
EXECUTION_READY or ECONOMICS_READY_FOR_PAPER. Phase 3C proves plumbing, NOT economics/profitability.

İlk RED: dry_run_eth5m / RequestBudget / _dryrun_verdict / BudgetExceeded henüz yok → AttributeError/ImportError.
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

REQUIRED_SUMMARY_FIELDS = (
    "verdict", "request_count", "max_total_requests", "asset", "interval",
    "slugs_attempted", "snapshots_written", "books_ok", "books_failed",
    "failure_modes", "output_jsonl", "output_summary", "timestamp_utc",
    "official_f1b", "profitability", "phase",
)
ALLOWED_VERDICTS = {"SAMPLE_ONLY", "INSUFFICIENT_SAMPLE", "DRY_RUN_FAILED"}


def _markets(n=4):
    return [{"market_slug": f"eth-updown-5m-{i}", "token_id": f"0x{i}"} for i in range(1, n + 1)]


def _fake_discover(markets):
    async def discover(budget):
        budget.spend("gamma")
        return list(markets)
    return discover


def _fake_book(two_sided=True):
    async def fetch(token_id, budget):
        budget.spend("book")
        if two_sided:
            return {"bids": [{"price": "0.48", "size": "100"}],
                    "asks": [{"price": "0.52", "size": "100"}]}
        return {"bids": [], "asks": []}
    return fetch


async def _noop_sleep(_s):
    return None


def _run(**kw):
    kw.setdefault("sleep_fn", _noop_sleep)
    return asyncio.run(S.dry_run_eth5m(**kw))


# ---- request budget ----

def test_request_budget_blocks_over_max():
    b = S.RequestBudget(4)
    for _ in range(4):
        b.spend("x")
    assert b.count == 4
    with pytest.raises(S.BudgetExceeded):
        b.spend("x")


def test_budget_state_not_reset_per_slug():
    b = S.RequestBudget(4)
    summary = _run(discover_fn=_fake_discover(_markets(4)), fetch_book_fn=_fake_book(),
                   out_dir=os.path.join(TOOLS_DIR, "_unused"), now_unix=None, budget=b,
                   _dry_paths_tmp=True)
    # 1 gamma + 3 books = 4; the 4th market is never fetched (slug cap + budget)
    assert summary["request_count"] == 4
    assert b.count == 4
    assert summary["slugs_attempted"] <= 3
    assert summary["max_total_requests"] == 4


# ---- verdict closed set ----

def test_dryrun_verdict_closed_set():
    assert S._dryrun_verdict(usable_books=1, ran_clean=True) == "SAMPLE_ONLY"
    assert S._dryrun_verdict(usable_books=0, ran_clean=True) == "INSUFFICIENT_SAMPLE"
    assert S._dryrun_verdict(usable_books=0, ran_clean=False) == "DRY_RUN_FAILED"
    for u in (0, 1, 3):
        for clean in (True, False):
            assert S._dryrun_verdict(usable_books=u, ran_clean=clean) in ALLOWED_VERDICTS


def test_verdict_never_execution_or_economics_ready():
    with open(SAMPLER_PATH, encoding="utf-8") as f:
        src = f.read()
    assert "EXECUTION_READY" not in src
    assert "ECONOMICS_READY_FOR_PAPER" not in src


# ---- summary schema ----

def test_summary_schema_and_flags(tmp_path):
    summary = _run(discover_fn=_fake_discover(_markets(3)), fetch_book_fn=_fake_book(),
                   out_dir=str(tmp_path), now_unix=12345)
    for field in REQUIRED_SUMMARY_FIELDS:
        assert field in summary, f"missing summary field {field!r}"
    assert summary["verdict"] in ALLOWED_VERDICTS
    assert summary["asset"] == "ETH" and summary["interval"] == "5m"
    assert summary["official_f1b"] is False
    assert summary["profitability"] is False
    assert summary["phase"] == "3C_dry_run"
    # files written, both timestamped, summary content matches
    assert os.path.exists(summary["output_jsonl"])
    assert os.path.exists(summary["output_summary"])
    with open(summary["output_summary"]) as f:
        on_disk = json.load(f)
    assert on_disk["verdict"] == summary["verdict"]


def test_sample_only_when_two_sided_book(tmp_path):
    summary = _run(discover_fn=_fake_discover(_markets(3)), fetch_book_fn=_fake_book(two_sided=True),
                   out_dir=str(tmp_path), now_unix=222)
    assert summary["verdict"] == "SAMPLE_ONLY"
    assert summary["books_ok"] == 3
    assert summary["snapshots_written"] == 3


def test_insufficient_sample_when_no_two_sided_book(tmp_path):
    summary = _run(discover_fn=_fake_discover(_markets(3)), fetch_book_fn=_fake_book(two_sided=False),
                   out_dir=str(tmp_path), now_unix=333)
    assert summary["verdict"] == "INSUFFICIENT_SAMPLE"
    assert summary["books_ok"] == 0
    assert summary["snapshots_written"] == 0


# ---- no overwrite ----

def test_no_overwrite_of_prior_dry_run_output(tmp_path):
    pre = tmp_path / "phase3_dryrun_snapshots_999.jsonl"
    pre.write_text("ORIGINAL", encoding="utf-8")
    summary = _run(discover_fn=_fake_discover(_markets(3)), fetch_book_fn=_fake_book(),
                   out_dir=str(tmp_path), now_unix=999)
    assert summary["verdict"] == "DRY_RUN_FAILED"
    assert "OUTPUT_EXISTS_NO_OVERWRITE" in summary["failure_modes"]
    assert pre.read_text(encoding="utf-8") == "ORIGINAL"  # untouched


# ---- max 1 snapshot per slug ----

def test_max_one_snapshot_per_slug(tmp_path):
    summary = _run(discover_fn=_fake_discover(_markets(3)), fetch_book_fn=_fake_book(),
                   out_dir=str(tmp_path), now_unix=444)
    with open(summary["output_jsonl"]) as f:
        rows = [json.loads(l) for l in f if l.strip()]
    slugs = [r["market_slug"] for r in rows]
    assert len(slugs) == len(set(slugs))  # no slug repeated
    assert len(rows) <= 3


# ---- CLI guard (refusal paths only; never runs --dry-run-eth5m) ----

def test_cli_refuses_no_args():
    r = subprocess.run([sys.executable, SAMPLER_PATH], capture_output=True, text=True)
    assert r.returncode != 0


def test_cli_refuses_unknown_arg():
    r = subprocess.run([sys.executable, SAMPLER_PATH, "--foo"], capture_output=True, text=True)
    assert r.returncode != 0
