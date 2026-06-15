"""tests/test_e12a_latency_cache_observation_policy.py — E12a latency/cache observation (docs-only TDD).

E11a–E11g kapanışı sonrası read-only latency/cache gözlemi yapıldı; bulgu: eklenen E10/E11 gate'leri saf
in-memory ve ihmal edilebilir, tek non-trivial maliyet E5 _effective_risk_mode sqlite okuması (E10/E11
ÖNCESİ risk-state katmanı), scan_perf yalnız nokta-latency logluyor (in-process jitter/tail dağılımı YOK),
config getattr okumaları static-per-process. Karar: ŞİMDİ optimizasyon YOK. Bu slice kararı bir artifact'a
sabitler (E11g/E1b/E7 docs-only cadence) — metrics/cache/optimizasyon KODU EKLEMEZ.

İlk RED: policy artifact yok → dosya bulunamaz / marker'lar eksik. Üretim/config/scan_perf'e dokunulmaz.
"""
import os

ARTIFACT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "superpowers", "risk", "e12a_latency_cache_observation_policy.md",
)

REQUIRED_MARKERS = [
    "VERDICT: NO OPTIMIZATION NOW",
    "E10/E11 gates are pure in-memory",
    "E5 _effective_risk_mode sqlite read is the only non-trivial gate cost",
    "E5/E6 risk-state layer predates E10/E11",
    "scan_perf logs point latency only",
    "jitter and tail spikes require offline log parsing",
    "offline p99 log parsing is safer than in-process aggregation",
    "no in-process p95/p99/max aggregation today",
    "config getattr reads are static-per-process",
    "config.py changes require restart or re-import",
    "config-value caching is not recommended now",
    "optimize only after measured scan_perf/council_ms regression",
    "gate sequence is not timed separately today",
    "future optional slice: scan_perf marker contract test",
    "future optional slice: docs-only offline p95/p99 parsing recipe",
    "future optional slice: lightweight gate-block counters only if measured tail spikes",
]


def _read_artifact() -> str:
    assert os.path.exists(ARTIFACT), f"E12a observation artifact eksik: {ARTIFACT}"
    with open(ARTIFACT, encoding="utf-8") as f:
        return f.read()


def test_artifact_exists():
    """Observation artifact dosyası mevcut olmalı. RED: dosya yok → AssertionError."""
    assert os.path.exists(ARTIFACT), f"E12a observation artifact eksik: {ARTIFACT}"


def test_required_markers_present():
    """Tüm zorunlu literal marker'lar artifact'ta olmalı. RED: artifact yok / marker eksik."""
    text = _read_artifact()
    missing = [m for m in REQUIRED_MARKERS if m not in text]
    assert not missing, f"E12a observation artifact eksik marker(lar): {missing}"
