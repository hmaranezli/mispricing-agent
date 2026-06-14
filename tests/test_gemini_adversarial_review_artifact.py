"""tests/test_gemini_adversarial_review_artifact.py — D#11: Gemini adversarial review artifact (TDD).

D#11 gap: D readiness için bağımsız Gemini adversarial review'ın repo'da kalıcı bir artifact'i YOK.
Bu test artifact'in VAR olduğunu ve kritik adversarial/NO-GO işaretçilerini içerdiğini sabitler.

ÖNEMLİ — anti-hallucination (anayasa madde 3): GREEN, GERÇEK bir Gemini adversarial review çıktısı
sağlanmadan yazılMAZ. Verdict uydurulamaz. Bu test mevcutken GREEN'i ancak insan/gerçek Gemini run'ı
review metnini verince yazarız. Offline — kod/restart/sinyal/API yok.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = REPO_ROOT / "docs" / "superpowers" / "evidence" / "gemini_adversarial_review_d11.md"

# Artifact'te bulunması ZORUNLU adversarial/NO-GO işaretçileri (substring, case-insensitive).
_REQUIRED_MARKERS = [
    "Gemini adversarial review",
    "PASS/FAIL",
    "99fb9c3",                                  # review anchor HEAD (D#10 GREEN)
    "D#10 PASS",
    "production_readiness_packet.md",           # incelenen girdi
    "independent_verifier_d10.md",              # incelenen girdi
    "D#2 human-only live gate",
    "D#7 phase-2 balance/auth probe not run",
    "production canary NOT approved",
    "Pre-F money-making audit",
    "edge correctness not approved",
    "false green",
    "hidden risk",
    "blocking findings",
    "no live API/Telegram/DB/restart/kill",
]


def test_gemini_adversarial_review_artifact_exists_and_has_required_sections():
    """docs/superpowers/evidence/gemini_adversarial_review_d11.md VAR olmalı ve kritik adversarial/
    NO-GO işaretçilerini içermeli. İlk RED: dosya henüz YOK → assertion (feature missing).
    GREEN gerçek Gemini review metni gerektirir (uydurma YASAK)."""
    assert ARTIFACT.exists(), f"Gemini adversarial review artifact bulunamadı: {ARTIFACT}"
    text = ARTIFACT.read_text(encoding="utf-8")
    low = text.lower()
    missing = [m for m in _REQUIRED_MARKERS if m.lower() not in low]
    assert not missing, f"Gemini review artifact eksik zorunlu işaretçi: {missing}"
