"""tests/test_production_readiness_evidence.py — D#9: production readiness evidence packet (TDD).

D#1-D#8 readiness kanıtı memory/terminal raporlarında var ama repo'da kalıcı bir artifact DEĞİL.
Bu test, repo içinde testlenen bir evidence packet'in VAR olduğunu ve kritik kanıt/NO-GO işaretçilerini
içerdiğini sabitler (regresyon: biri silinir/eskirse test kırılır).

Doküman testi — kod/restart/sinyal yok; yalnız repo dosyası okunur.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKET = REPO_ROOT / "docs" / "superpowers" / "evidence" / "production_readiness_packet.md"

# Packet'te bulunması ZORUNLU kanıt/NO-GO işaretçileri (substring, case-insensitive).
_REQUIRED_MARKERS = [
    "b26f7f8",                                  # paket yazıldığı andaki HEAD
    "D#6 FULLY CLOSED",                         # Telegram notify üç kol kapandı
    "D#8 FULLY CLOSED",                         # start/stop/runbook kapandı
    "D#7 phase-2 balance/auth probe pending",   # canlı probe henüz yok
    "D#2 human-only live gate",                 # DRY_RUN→False insan kapısı açık
    "production canary NOT approved",
    "Pre-F money-making audit",
    "no live API/Telegram/DB/restart/kill",
    "old untracked patch files untouched",
    "test_main_loop.py subset 76 passed, 1 deselected",
    "restart_guard 7 passed",
    "restart_sh 1 passed",
]


def test_evidence_packet_exists_and_has_required_sections():
    """docs/superpowers/evidence/production_readiness_packet.md VAR olmalı ve kritik kanıt/NO-GO
    işaretçilerini içermeli. İlk RED: dosya henüz YOK → assertion (feature missing)."""
    assert PACKET.exists(), f"evidence packet bulunamadı: {PACKET}"
    text = PACKET.read_text(encoding="utf-8")
    low = text.lower()
    missing = [m for m in _REQUIRED_MARKERS if m.lower() not in low]
    assert not missing, f"evidence packet eksik zorunlu işaretçi: {missing}"
