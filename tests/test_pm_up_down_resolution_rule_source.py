"""tests/test_pm_up_down_resolution_rule_source.py — F1a: PM Up/Down resolution rule source capture (TDD).

F1 data fidelity audit, edge correctness'in kök confounder'ı olarak price-source/resolution-index
belirsizliğini işaretledi (BLOCKED-UNTIL-DOCS). F1a bu blocker'ı daraltır: repo'nun hedeflediği
spesifik Up/Down crypto market'lerinin (slug `{asset}-updown-{interval}m-{ts}`) TAM resolution
kuralını (resolution source / index / timestamp / edge cases) repo'ya KAYDETME kapısı.

KRİTİK: exact index genel docs'tan ÇIKARILMAZ (do not infer index from generic docs). Genel
Polymarket Resolution docs (UMA Optimistic Oracle, per-market resolution rules: resolution source +
end date + edge cases) yalnız genel kanıttır; spesifik per-market/event rule metni kaydedilene kadar
resolution-source/index = BLOCKED-UNTIL-DOCS / DATA FIDELITY NOT VERIFIED.

Bu test artifact'in VAR + kritik işaretçileri içerdiğini sabitler. İlk RED: dosya YOK. Canlı API yok.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = REPO_ROOT / "docs" / "superpowers" / "quant" / "pm_up_down_resolution_rule_source.md"

# Artifact'te bulunması ZORUNLU işaretçiler (substring, case-insensitive).
_REQUIRED_MARKERS = [
    "PM Up/Down resolution rule source",
    "resolution-source/index",
    "per-market resolution rules",
    "UMA Optimistic Oracle",
    "resolution source",
    "end date",
    "edge cases",
    "Gamma markets/events by slug",
    "do not infer index from generic docs",
    "BLOCKED-UNTIL-DOCS",
    "DATA FIDELITY NOT VERIFIED",
    "Poly API data fidelity",
    "fair-vs-realized confounder",
    "no live API",
    "offline data only",
    "D#7 phase-2 balance/auth probe not run",
    "production canary NOT approved",
]


def test_pm_up_down_resolution_rule_source_artifact_exists_and_has_required_sections():
    """docs/superpowers/quant/pm_up_down_resolution_rule_source.md VAR olmalı ve kritik işaretçileri
    içermeli. İlk RED: dosya henüz YOK → assertion (feature missing)."""
    assert ARTIFACT.exists(), f"PM Up/Down resolution rule source artifact bulunamadı: {ARTIFACT}"
    text = ARTIFACT.read_text(encoding="utf-8")
    low = text.lower()
    missing = [m for m in _REQUIRED_MARKERS if m.lower() not in low]
    assert not missing, f"resolution rule source artifact eksik zorunlu işaretçi: {missing}"
