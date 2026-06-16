"""tests/test_phase4c_repeatability_observation_02_audit.py — pins the Phase 4C repeatability
observation #2 audit checkpoint (docs-only contract, offline).

Runs no batch, fetches no endpoint, touches no live/market data. Asserts the observation #2 audit
doc records the run facts, a non-statistical baseline comparison (with explicit deltas), the
not-stationarity / not-statistical-significance / no-economic-inference disclaimers, and confines
every forbidden readiness/profitability/edge claim to the explicit framing / no-claims sections.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "handoff", "phase4c_repeatability_observation_02_audit.md")

BASELINE_BATCH_ID = "phase4c_batch_1781631021"
NEW_BATCH_ID = "phase4c_batch_1781636200"
COMMAND = ("python3 tools/phase4c_batch_orchestrator.py --runs 1 --output-root data/output "
           "--live-public-data --enable-real-subprocess")
STAGES_IN_ORDER = ["phase3d5_sampler", "phase4a_analyzer", "phase4b_aggregator"]

FRAMING_START = "<!-- FRAMING-START -->"
FRAMING_END = "<!-- FRAMING-END -->"
NO_CLAIMS_START = "<!-- NO-CLAIMS-START -->"
NO_CLAIMS_END = "<!-- NO-CLAIMS-END -->"

COMPARISON_MARKERS = [
    "Baseline Comparison (Non-Statistical)",
    "request_count_delta",
    "discovery_requests_delta",
    "book_requests_delta",
    "artifact count comparison",
    "log count comparison",
    "stage order comparison",
]

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


def _strip_block(text, start, end):
    if start in text and end in text:
        s = text.index(start)
        e = text.index(end) + len(end)
        return text[:s] + text[e:]
    return text


def test_audit_doc_exists():
    assert _read().strip(), "audit doc is empty"


def test_observation_number_2_present():
    text = _read()
    assert "observation number: 2" in text.lower() or "observation #2" in text.lower() \
        or "observation number 2" in text.lower()


def test_baseline_and_new_batch_ids_present():
    text = _read()
    assert BASELINE_BATCH_ID in text, "baseline batch id missing"
    assert NEW_BATCH_ID in text, "new batch id missing"


def test_command_present_exactly():
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


def test_baseline_comparison_section_and_deltas():
    text = _read()
    missing = [m for m in COMPARISON_MARKERS if m not in text]
    assert not missing, f"comparison markers missing: {missing}"


def test_not_stationarity_not_statistical_significance():
    low = _read().lower()
    assert "not a stationarity test" in low or "does not prove stationarity" in low \
        or "no stationarity proof" in low, "missing not-stationarity disclaimer"
    assert "not statistical significance" in low or "no statistical significance" in low \
        or "not a statistical significance" in low, "missing not-significance disclaimer"


def test_no_economic_inference_present():
    low = _read().lower()
    assert "no economic inference" in low or "not an economic inference" in low


def test_no_claims_statement_present():
    text = _read()
    assert NO_CLAIMS_START in text and NO_CLAIMS_END in text
    block = text[text.index(NO_CLAIMS_START):text.index(NO_CLAIMS_END)].lower()
    for term in ["edge", "pnl", "paper readiness", "economics readiness",
                 "execution readiness", "profitability", "alpha", "live readiness",
                 "system-ready", "ready-to-fly", "ready"]:
        assert term in block, f"no-claims statement missing term: {term}"


def test_forbidden_claims_only_in_framing_or_no_claims():
    text = _read()
    body = _strip_block(text, FRAMING_START, FRAMING_END)
    body = _strip_block(body, NO_CLAIMS_START, NO_CLAIMS_END).lower()
    hits = [p for p in FORBIDDEN_CLAIM_PHRASES if p in body]
    assert not hits, f"forbidden positive claim(s) outside framing/no-claims: {hits}"


def test_generated_artifacts_not_referenced_as_tracked():
    text = _read()
    low = text.lower()
    assert "untracked" in low, "must state artifacts are untracked"
    assert "not staged" in low, "must state artifacts are not staged"
    assert "git add ." not in text, "must not reference 'git add .'"
    assert "git add data/output" not in low, "must not stage data/output artifacts"
