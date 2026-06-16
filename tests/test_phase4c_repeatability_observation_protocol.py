"""tests/test_phase4c_repeatability_observation_protocol.py — pins the Phase 4C controlled
public-data repeatability observation protocol (docs-only contract, offline).

This test runs no batch, fetches no endpoint, touches no live/market data. It asserts the
repo-durable protocol document defines the one-run-at-a-time rule, the exact run command, the
recovery rule, capture/comparison fields, non-statistical operator thresholds, stop conditions,
and keeps every forbidden readiness/profitability/edge claim confined to the explicit
framing / no-claims sections. It also pins that the protocol disclaims any stationarity proof.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "protocols", "phase4c_repeatability_observation_protocol.md")

COMMAND = ("python3 tools/phase4c_batch_orchestrator.py --runs 1 --output-root data/output "
           "--live-public-data --enable-real-subprocess")

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"

PER_RUN_FIELDS = [
    "batch_id", "manifest path", "exit code", "run_count", "completed_runs", "failed_runs",
    "aborted", "abort_reason", "per_run_max_total_requests", "request_count",
    "discovery_requests", "book_requests", "assets", "complement_pairs_attempted",
    "complement_pairs_written", "pair_books_ok", "pair_books_failed", "failure_modes",
    "stage names", "order", "status", "verdict", "exit_code",
    "stdout", "stderr", "artifact path", "duration",
]

CROSS_RUN_FIELDS = [
    "request_count min/max", "discovery_requests min/max", "book_requests min/max",
    "assets observed", "number of successful runs", "aborted", "fail-closed",
    "artifact count consistency", "log count consistency", "stage order consistency",
    "failure_modes summary",
]

OPERATOR_THRESHOLDS = [
    "request_count > 20", "nonzero exit", "missing artifact", "missing log",
    "unexpected staged generated artifact", "material run-to-run drift",
    "do not prove stationarity",
]

STOP_CONDITIONS = [
    "nonzero exit", "missing artifact", "missing logs", "request_count > 20", "timeout",
    "dirty git state", "unexpected staged generated artifact", "forbidden flags",
    "multi-run invocation", "unresolved prior-run audit",
]

PRE_RUN_GATES = [
    "HEAD == origin/master", "git diff", "--cached", "untracked", "not staged",
    "first audit checkpoint",
]

# Positive claim phrases that must NEVER appear outside the framing / no-claims blocks.
FORBIDDEN_CLAIM_PHRASES = [
    "ready-to-fly", "ready to fly", "system-ready", "system ready",
    "is ready", "are ready", "production ready", "paper ready",
    "execution ready", "live ready", "economics ready", "ready for live",
    "is profitable", "profit confirmed", "profitable strategy",
    "edge confirmed", "positive edge", "tradeable edge", "alpha confirmed",
]


def _read():
    assert os.path.isfile(DOC), f"protocol doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _strip_block(text, start, end):
    if start in text and end in text:
        s = text.index(start)
        e = text.index(end) + len(end)
        return text[:s] + text[e:]
    return text


def test_protocol_doc_exists():
    assert _read().strip(), "protocol doc is empty"


def test_command_present_exactly():
    assert COMMAND in _read()


def test_run_limit_3_to_5_present():
    text = _read()
    assert "3 to 5" in text, "missing '3 to 5' run limit"


def test_one_run_at_a_time_rule_present():
    low = _read().lower()
    assert "one-run-at-a-time" in low or "one run at a time" in low
    assert "--runs 1" in _read()


def test_multi_run_invocation_forbidden():
    text = _read()
    assert "--runs 3" in text and "--runs 5" in text, "multi-run flags not shown as forbidden"


def test_recovery_rule_present():
    low = _read().lower()
    assert "recovery" in low
    assert "do not rerun blindly" in low
    assert "new phase4c_batch_" in low or "new batch directory" in low


def test_artifact_policy_present():
    low = _read().lower()
    assert "untracked" in low and "must not be committed" in low


def test_pre_run_gates_present():
    text = _read()
    missing = [m for m in PRE_RUN_GATES if m not in text]
    assert not missing, f"pre-run gates missing: {missing}"


def test_per_run_fields_present():
    text = _read()
    missing = [m for m in PER_RUN_FIELDS if m not in text]
    assert not missing, f"per-run fields missing: {missing}"


def test_cross_run_comparison_fields_present():
    text = _read()
    missing = [m for m in CROSS_RUN_FIELDS if m not in text]
    assert not missing, f"cross-run fields missing: {missing}"


def test_operator_attention_thresholds_present():
    text = _read()
    low = text.lower()
    assert "non-statistical" in low, "thresholds must be flagged non-statistical"
    missing = [m for m in OPERATOR_THRESHOLDS if m not in text]
    assert not missing, f"operator thresholds missing: {missing}"


def test_stop_conditions_present():
    text = _read()
    missing = [m for m in STOP_CONDITIONS if m not in text]
    assert not missing, f"stop conditions missing: {missing}"


def test_no_claims_statement_present():
    text = _read()
    assert NO_CLAIMS_START in text and NO_CLAIMS_END in text
    block = text[text.index(NO_CLAIMS_START):text.index(NO_CLAIMS_END)].lower()
    for term in ["edge", "pnl", "paper readiness", "economics readiness",
                 "execution readiness", "profitability", "alpha", "live readiness",
                 "system-ready", "ready-to-fly", "ready"]:
        assert term in block, f"no-claims statement missing term: {term}"


def test_does_not_prove_stationarity():
    low = _read().lower()
    assert "does not prove stationarity" in low or "no stationarity proof" in low


def test_forbidden_claims_only_in_framing_or_no_claims():
    text = _read()
    body = _strip_block(text, FRAMING_START, FRAMING_END)
    body = _strip_block(body, NO_CLAIMS_START, NO_CLAIMS_END).lower()
    hits = [p for p in FORBIDDEN_CLAIM_PHRASES if p in body]
    assert not hits, f"forbidden positive claim(s) outside framing/no-claims: {hits}"
