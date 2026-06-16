"""tests/test_phase4c_first_public_batch_audit.py — pins the Phase 4C first public-data
batch audit checkpoint document (docs-only contract, offline).

This test runs no batch, fetches no endpoint, touches no live/market data. It asserts the
repo-durable audit doc for batch phase4c_batch_1781631021 records the run facts, keeps every
forbidden readiness/profitability/edge claim confined to the explicit no-claims statement, and
never references generated data/output artifacts as tracked/staged files.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff", "phase4c_first_public_batch_audit.md")

BATCH_ID = "phase4c_batch_1781631021"
COMMAND = ("python3 tools/phase4c_batch_orchestrator.py --runs 1 --output-root data/output "
           "--live-public-data --enable-real-subprocess")
STAGES_IN_ORDER = ["phase3d5_sampler", "phase4a_analyzer", "phase4b_aggregator"]
ASSETS = ["BTC", "ETH", "SOL", "XRP"]

NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"

# Positive claim phrases that must NEVER appear outside the explicit no-claims block.
# (Chosen so they do not collide with legitimate verdict/tool identifiers such as
#  GROSS_EDGE_SAMPLE_ONLY or phase4b_gross_edge_aggregate.)
FORBIDDEN_CLAIM_PHRASES = [
    "ready-to-fly", "ready to fly", "system-ready", "system ready",
    "is ready", "are ready", "production ready", "paper ready",
    "execution ready", "live ready", "economics ready", "ready for live",
    "is profitable", "profit confirmed", "profitable strategy",
    "edge confirmed", "positive edge", "tradeable edge", "alpha confirmed",
]


def _read():
    assert os.path.isfile(DOC), f"audit doc missing: {DOC}"
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def _outside_no_claims_block(text):
    """Return doc text with the explicit no-claims block removed."""
    assert NO_CLAIMS_START in text, f"missing {NO_CLAIMS_START}"
    assert NO_CLAIMS_END in text, f"missing {NO_CLAIMS_END}"
    start = text.index(NO_CLAIMS_START)
    end = text.index(NO_CLAIMS_END) + len(NO_CLAIMS_END)
    assert start < end, "no-claims markers out of order"
    return text[:start] + text[end:]


def test_audit_doc_exists():
    assert _read().strip(), "audit doc is empty"


def test_batch_id_present():
    assert BATCH_ID in _read()


def test_command_present():
    assert COMMAND in _read()


def test_request_count_present():
    assert "request_count 12 <= 20" in _read()


def test_stages_present_in_order():
    text = _read()
    idxs = []
    for s in STAGES_IN_ORDER:
        assert s in text, f"stage missing: {s}"
        idxs.append(text.index(s))
    assert idxs == sorted(idxs), f"stages not in order: {idxs}"


def test_assets_present():
    text = _read()
    missing = [a for a in ASSETS if a not in text]
    assert not missing, f"assets missing: {missing}"


def test_no_claims_statement_present():
    text = _read()
    block_start = text.index(NO_CLAIMS_START) if NO_CLAIMS_START in text else -1
    assert block_start >= 0, "no-claims block missing"
    block_end = text.index(NO_CLAIMS_END)
    block = text[block_start:block_end].lower()
    # The explicit statement disclaims each forbidden term.
    for term in ["edge", "pnl", "paper readiness", "economics readiness",
                 "execution readiness", "profitability", "alpha", "live readiness",
                 "system-ready", "ready-to-fly", "ready"]:
        assert term in block, f"no-claims statement missing term: {term}"


def test_forbidden_claims_only_in_no_claims_block():
    body = _outside_no_claims_block(_read()).lower()
    hits = [p for p in FORBIDDEN_CLAIM_PHRASES if p in body]
    assert not hits, f"forbidden positive claim(s) made outside no-claims statement: {hits}"


def test_generated_artifacts_not_referenced_as_tracked():
    text = _read()
    low = text.lower()
    # Generated artifacts must be described as untracked / not staged, never committed.
    assert "untracked" in low, "audit doc must state artifacts are untracked"
    assert "not staged" in low, "audit doc must state artifacts are not staged"
    assert "git add ." not in text, "audit doc must not reference 'git add .'"
    assert "git add data/output" not in low, "audit doc must not stage data/output artifacts"
