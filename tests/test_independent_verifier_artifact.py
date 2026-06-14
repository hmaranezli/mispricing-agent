"""tests/test_independent_verifier_artifact.py — D#10: independent verifier PASS artifact (TDD).

D#10 gap: D readiness için bağımsız/read-only verifier attestation'ı repo'da kalıcı bir artifact
DEĞİL. Bu test, verifier artifact'inin VAR olduğunu ve kritik doğrulama/NO-GO işaretçilerini
içerdiğini sabitler (regresyon: biri silinir/eskirse test kırılır). Offline — kod/restart/sinyal/API yok.

Mevcut pattern referansı: docs/superpowers/evidence/2026-06-11-h6-verifier-current-session.txt
(H6 verifier: PASS/BLOCKED_NEEDS_EVIDENCE/TRACEABILITY_ACCEPTED verdict'leri + evidence chain).
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = REPO_ROOT / "docs" / "superpowers" / "evidence" / "independent_verifier_d10.md"

# Verifier artifact'inde bulunması ZORUNLU doğrulama/NO-GO işaretçileri (substring, case-insensitive).
_REQUIRED_MARKERS = [
    "independent verifier",
    "PASS/FAIL",
    "production_readiness_packet.md",           # doğrulanan girdi
    "c371b1e",                                  # D#9 packet HEAD'i / doğrulama anchor'ı
    "D#9 PASS",
    "D#2 human-only live gate",
    "D#7 phase-2 balance/auth probe",
    "production canary NOT approved",
    "Pre-F money-making audit",
    "no live API/Telegram/DB/restart/kill",
    "hidden risk",
    "false green",
    "missing evidence",
]


def test_independent_verifier_artifact_exists_and_has_required_sections():
    """docs/superpowers/evidence/independent_verifier_d10.md VAR olmalı ve kritik doğrulama/NO-GO
    işaretçilerini içermeli. İlk RED: dosya henüz YOK → assertion (feature missing)."""
    assert ARTIFACT.exists(), f"independent verifier artifact bulunamadı: {ARTIFACT}"
    text = ARTIFACT.read_text(encoding="utf-8")
    low = text.lower()
    missing = [m for m in _REQUIRED_MARKERS if m.lower() not in low]
    assert not missing, f"verifier artifact eksik zorunlu işaretçi: {missing}"
