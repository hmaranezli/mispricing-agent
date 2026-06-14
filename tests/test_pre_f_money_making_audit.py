"""tests/test_pre_f_money_making_audit.py — Pre-F money-making audit artifact gate (TDD).

D readiness (D#1–D#11) yalnız OPERASYONEL güvenliği kanıtlar (graceful shutdown, kill-switch, notify,
restart preflight). Botun PARA KAZANDIĞINI kanıtlamaz. Pre-F money-making audit gate, Master Plan F
(gerçek para / ölçek) ÖNCESİNDE para-kazanma mantığının test edilebilir ve sağlam olup olmadığını
OFFLINE denetler. Bu Paper Soak DEĞİL, canary/live onayı DEĞİL — offline artifact kapısıdır.

Bu test, audit artifact'inin VAR olduğunu ve kritik denetim/NO-GO işaretçilerini içerdiğini sabitler.
İlk RED: dosya henüz YOK → assertion (feature missing). Canlı sistem/API/DB/Telegram yok.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT = REPO_ROOT / "docs" / "superpowers" / "quant" / "pre_f_money_making_audit.md"

# Artifact'te bulunması ZORUNLU denetim/NO-GO işaretçileri (substring, case-insensitive).
_REQUIRED_MARKERS = [
    "Pre-F Audit: Ops-Chain (D#1-D#11) Verified, Live-Gate (D#2/D#7) Closed",
    "Pre-F money-making audit",
    "edge correctness",
    "entry/exit correctness",
    "fair price",
    "expected edge",
    "fee/slippage logic verified",
    "win-rate vs loss-magnitude",
    "paper PnL",
    "reject reasons",
    "calibration metrics",
    "offline data only",
    "no live API",
    "no Telegram",
    "no live DB",
    "D#7 phase-2 balance/auth probe not run",
    "production canary NOT approved",
    "PASS/FAIL recommendation",
]


def test_pre_f_money_making_audit_artifact_exists_and_has_required_sections():
    """docs/superpowers/quant/pre_f_money_making_audit.md VAR olmalı ve kritik denetim/NO-GO
    işaretçilerini içermeli. İlk RED: dosya henüz YOK → assertion (feature missing)."""
    assert AUDIT.exists(), f"Pre-F money-making audit artifact bulunamadı: {AUDIT}"
    text = AUDIT.read_text(encoding="utf-8")
    low = text.lower()
    missing = [m for m in _REQUIRED_MARKERS if m.lower() not in low]
    assert not missing, f"Pre-F audit artifact eksik zorunlu işaretçi: {missing}"
