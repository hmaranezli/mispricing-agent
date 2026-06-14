"""tests/test_e0_risk_control_hard_caps_inventory.py — E0 Risk-Control Hard Caps Inventory (TDD).

F (para-kazanma/edge) exact Streams verisi gelene kadar PARK edildi. E, AYRI bir risk eksenidir:
model/edge riski değil, EXECUTION/RUIN (iflas) riski — yani "edge belirsizken bile hayatta kalma"
guardrail'leri. Bu artifact yalnız ENVANTER: hangi hard cap'ler config-tabanlı var, hangi
execution breaker'lar logic-tabanlı var, hangileri eksik/yalnızca ima edilmiş. Implementasyon/davranış
değişikliği YOK.

Bu test, envanter artifact'inin VAR + kritik işaretçileri içerdiğini sabitler. İlk RED: dosya YOK.
Canlı API/fetch YOK; read-only.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = REPO_ROOT / "docs" / "superpowers" / "risk" / "e0_risk_control_hard_caps_inventory.md"

# Gelecek GREEN'de bulunması ZORUNLU işaretçiler (substring, case-insensitive).
_REQUIRED_MARKERS = [
    "E0 Risk-Control Hard Caps Inventory",
    "F parked until exact Streams data",
    "E protects survival probability",
    "ruin probability",
    "config-based hard caps",
    "logic-based execution breakers",
    "missing or implied controls",
    "MAX_OPEN_POSITIONS",
    "MAX_CAPITAL_PER_TRADE",
    "MAX_TRADES_FIRST_SESSION",
    "SESSION_LOSS_LIMIT",
    "DAILY_LOSS_LIMIT",
    "cancel/timeout burst breaker",
    "fill-to-submit breaker",
    "emergency/manual pause",
    "exit-only mode",
    "no live API",
    "no production trading code changed",
    "Paper Soak blocked until hard caps are verified",
]


def test_e0_risk_control_hard_caps_inventory_artifact_exists_and_has_required_sections():
    """docs/superpowers/risk/e0_risk_control_hard_caps_inventory.md VAR olmalı ve kritik risk-kontrol
    işaretçilerini içermeli. İlk RED: dosya henüz YOK → assertion (feature missing)."""
    assert ARTIFACT.exists(), f"E0 risk-control inventory artifact bulunamadı: {ARTIFACT}"
    text = ARTIFACT.read_text(encoding="utf-8")
    low = text.lower()
    missing = [m for m in _REQUIRED_MARKERS if m.lower() not in low]
    assert not missing, f"E0 risk-control inventory artifact eksik zorunlu işaretçi: {missing}"
