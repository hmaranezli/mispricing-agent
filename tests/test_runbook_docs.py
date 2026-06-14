"""tests/test_runbook_docs.py — D#8 son gap: start/stop/restart runbook artifact (TDD).

D#8'in kod-seviyesi gap'leri (restart self-kill preflight + SIGTERM graceful shutdown) kapandı;
kalan tek parça operatör runbook'u. Bu test runbook dosyasının VAR olduğunu ve kritik güvenlik
bölümlerini içerdiğini sabitler (regresyon: biri silinirse test kırılır).

Doküman testi — kod/restart/sinyal yok; yalnız repo dosyası okunur.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "start_stop_restart.md"

# Runbook'ta bulunması ZORUNLU güvenlik işaretçileri (substring, case-insensitive).
_REQUIRED_MARKERS = [
    "tmux footgun",                                          # self-kill footgun açıklaması
    'venv/bin/python -m monitor.restart_guard --target "$SESSION"',  # preflight komutu birebir
    "SIGTERM",                                               # graceful shutdown sinyali
    "SIGINT",
    "graceful shutdown",
    "post-restart",                                          # restart sonrası doğrulama
    "schema",                                                # execution_state/araf_resolution_shadow doğrulama
    "production canary NOT approved",                        # canlıya onay yok bayrağı
    "Pre-F",                                                 # money-making audit gate korunur
]


def test_runbook_exists_and_has_required_safety_sections():
    """Runbook docs/runbooks/start_stop_restart.md VAR olmalı ve kritik güvenlik işaretçilerini
    içermeli. İlk RED: dosya henüz YOK → FileNotFoundError (feature missing)."""
    assert RUNBOOK.exists(), f"runbook bulunamadı: {RUNBOOK}"
    text = RUNBOOK.read_text(encoding="utf-8")
    low = text.lower()
    missing = [m for m in _REQUIRED_MARKERS if m.lower() not in low]
    assert not missing, f"runbook eksik zorunlu bölüm/işaretçi: {missing}"
