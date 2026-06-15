"""tests/test_scan_perf_offline_parsing_recipe_contract.py — offline p95/p99 parsing recipe (docs-only TDD).

E12a observation kararı: jitter/tail spike'lar IN-PROCESS aggregation ile DEĞİL, scan_perf loglarından
OFFLINE parse edilerek görülmeli (in-process aggregation'dan güvenli, runtime loop'a dokunmaz). scan_perf
marker contract (f85a1d0) alan adlarını pinledi. Bu slice o offline parsing tarifini bir artifact'a
sabitler (docs-only) — parser KODU EKLEMEZ, in-process p95/p99/max EKLEMEZ, scan_perf format DEĞİŞMEZ.

Hedef eksik artifact:
    docs/superpowers/risk/scan_perf_offline_p95_p99_parsing_recipe.md

İlk RED: artifact yok → dosya bulunamaz / marker'lar eksik. main_loop/scan_perf'e dokunulmaz.
"""
import os

ARTIFACT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "superpowers", "risk", "scan_perf_offline_p95_p99_parsing_recipe.md",
)

REQUIRED_MARKERS = [
    "scan_perf is parsed offline from logs, not aggregated in-process",
    "required fields: total_ms, scan_edges_ms, council_ms, execute_ms, candidates",
    "derived metrics: count, avg, p50, p95, p99, max",
    "jitter and tail-spike review",
    "offline parsing is safer than in-process aggregation for this bot",
    "offline parsing is non-blocking for the runtime loop because it does not run inside main_loop",
    "this does not change runtime behavior",
    "this does not unblock F/live",
]


def _read_artifact() -> str:
    assert os.path.exists(ARTIFACT), f"scan_perf offline parsing recipe artifact eksik: {ARTIFACT}"
    with open(ARTIFACT, encoding="utf-8") as f:
        return f.read()


def test_artifact_exists():
    """Recipe artifact dosyası mevcut olmalı. RED: dosya yok → AssertionError."""
    assert os.path.exists(ARTIFACT), f"scan_perf offline parsing recipe artifact eksik: {ARTIFACT}"


def test_required_markers_present():
    """Tüm zorunlu literal marker'lar artifact'ta olmalı. RED: artifact yok / marker eksik."""
    text = _read_artifact()
    missing = [m for m in REQUIRED_MARKERS if m not in text]
    assert not missing, f"recipe artifact eksik marker(lar): {missing}"
