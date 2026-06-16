"""tests/test_phase4c_public_batch_preflight_checklist.py — pins the Phase 4C first
public-data batch pre-flight checklist document (docs-only contract, offline).

This test does NOT run any batch, fetch any endpoint, or touch live/market data. It only
asserts that the repo-durable checklist document exists and contains the exact operator/system
gate markers and the no-claims (sample-only) language required before any first controlled
public-data batch. NO edge/PnL/profitability/paper/economics/execution/live readiness claim is
made or implied by this test; the markers it pins are themselves disclaimers.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKLIST_PATH = os.path.join(REPO, "docs", "phase4c_public_batch_preflight_checklist.md")


def _read():
    assert os.path.isfile(CHECKLIST_PATH), f"checklist doc missing: {CHECKLIST_PATH}"
    with open(CHECKLIST_PATH, encoding="utf-8") as f:
        return f.read()


# Required gate markers — each must appear verbatim in the checklist.
REQUIRED_MARKERS = [
    # Required repo state
    "HEAD == origin/master",
    "git diff",
    "--cached",
    "untracked",
    "not staged",
    # Required flags for the first controlled public-data batch
    "--runs 1",
    "--output-root data/output",
    "--live-public-data",
    "--enable-real-subprocess",
    # Explicitly forbidden flags/modes for the actual batch
    "--diagnostic-fake-runner",
    "--offline-fixture-subprocess",
    "--command-plan-only",
    # Request cap
    "per_run_max_total_requests == 20",
    # Stage expectations — exactly 3 stages in order
    "phase3d5_sampler",
    "phase4a_analyzer",
    "phase4b_aggregator",
    # Expected artifact / log layout
    "phase4c_batch_<ts>/run_01",
    "run_01/logs",
    # Abort / fail-closed expectations
    "nonzero exit",
    "missing artifact",
    "request_count > 20",
    "timeout",
    "plan warning",
    # Safety boundaries
    "public data only",
    "no secrets",
    "no orders",
    "no balances",
    "no Telegram",
    "no restart",
    "main_loop",
    "config",
    # Reporting requirements after the batch
    "exit code",
    "request_count",
    "stage verdict",
    "artifact path",
    "git cleanliness",
]

# No-claims language — the checklist must explicitly frame the batch as sample-only observation
# and disclaim each forbidden claim term.
NO_CLAIMS_MARKERS = [
    "sample-only observation",
    "not edge",
    "not PnL",
    "not profitability",
    "not paper readiness",
    "not economics readiness",
    "not execution readiness",
    "not live readiness",
]


def test_checklist_document_exists():
    text = _read()
    assert text.strip(), "checklist document is empty"


def test_checklist_contains_required_gate_markers():
    text = _read()
    missing = [m for m in REQUIRED_MARKERS if m not in text]
    assert not missing, f"checklist missing required markers: {missing}"


def test_checklist_contains_no_claims_language():
    text = _read()
    missing = [m for m in NO_CLAIMS_MARKERS if m not in text]
    assert not missing, f"checklist missing no-claims markers: {missing}"
