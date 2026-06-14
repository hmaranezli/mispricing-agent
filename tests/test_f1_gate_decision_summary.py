"""tests/test_f1_gate_decision_summary.py — F1 Gate Decision Summary (TDD).

F-fazı quant artifact'leri (pre_f_money_making_audit, poly_api_data_fidelity_audit,
pm_up_down_resolution_rule_source, f1b_chainlink_stream_blocker) tek bir GATE KARARINA indirgenir.
Bu artifact YENİ ÖLÇÜM MANTIĞI EKLEMEZ ve Feed-proxy'nin gizli bir PASS yolu olmasına izin vermez:
F / production-canary, exact Data Streams kanıtı (veya manuel Streams CSV/JSON) + source-aligned veride
yeniden hesaplanan offline calibration olmadan BLOCKED kalır.

Bu test, gate kararı artifact'inin VAR + kritik karar/NO-GO işaretçilerini içerdiğini sabitler.
İlk RED: dosya YOK. Canlı API/Chainlink/HL fetch YOK.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = REPO_ROOT / "docs" / "superpowers" / "quant" / "f1_gate_decision_summary.md"

# Gelecek GREEN'de bulunması ZORUNLU işaretçiler (substring, case-insensitive).
_REQUIRED_MARKERS = [
    "F1 Gate Decision",
    "F remains BLOCKED",
    "production canary NOT approved",
    "F1b Measurement BLOCKED",
    "exact Chainlink Data Streams required",
    "Feed-proxy cannot clear F1b",
    "calibration metrics blocked until source-aligned data",
    "HL≠Chainlink confounder confirmed",
    "no live API",
    "no production trading code changed",
    "allowed unlock paths: Streams auth or manual Streams CSV/JSON",
    "next action: obtain exact Streams data, then recompute calibration",
]


def test_f1_gate_decision_summary_artifact_exists_and_has_required_sections():
    """docs/superpowers/quant/f1_gate_decision_summary.md VAR olmalı ve kritik karar/NO-GO
    işaretçilerini içermeli. İlk RED: dosya henüz YOK → assertion (feature missing)."""
    assert ARTIFACT.exists(), f"F1 gate decision summary artifact bulunamadı: {ARTIFACT}"
    text = ARTIFACT.read_text(encoding="utf-8")
    low = text.lower()
    missing = [m for m in _REQUIRED_MARKERS if m.lower() not in low]
    assert not missing, f"F1 gate decision artifact eksik zorunlu işaretçi: {missing}"
