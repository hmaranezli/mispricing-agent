"""tests/test_poly_api_data_fidelity_audit.py — F1: Poly API data fidelity & usage audit (TDD).

Pre-F money-making audit, sahte edge'in yalnız model matematiğinden DEĞİL, veri besleme / API
semantiğinden de gelebileceğini söyledi (garbage-in garbage-out). Bu audit, Polymarket (+ kıyas
kaynağı Hyperliquid) veri besleme doğruluğunu OFFLINE denetler: market/query semantics, price source,
timestamp/latency, aggregation, adjusted/unadjusted, condition/status, stale/missing handling, fee
uyumu. Amaç: recorded Brier 0.39 / fair-67-vs-win-14 sonucunun model mi yoksa VERİ confounder'ı mı
olduğunu izole etmek (fair-vs-realized confounder) — calibration metriklerinden ÖNCE.

Bu test, audit artifact'inin VAR olduğunu ve kritik fidelity/NO-GO işaretçilerini içerdiğini sabitler.
İlk RED: dosya henüz YOK → assertion (feature missing). Canlı API/DB/Telegram yok.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT = REPO_ROOT / "docs" / "superpowers" / "quant" / "poly_api_data_fidelity_audit.md"

# Artifact'te bulunması ZORUNLU fidelity/NO-GO işaretçileri (substring, case-insensitive).
_REQUIRED_MARKERS = [
    "Poly API data fidelity",
    "API usage audit",
    "data ingestion correctness",
    "garbage-in garbage-out",
    "market/query semantics",
    "adjusted/unadjusted data",
    "timestamp/latency assumptions",
    "aggregation rules",
    "condition/status codes",
    "stale/missing data handling",
    "fee/slippage compatibility",
    "fair-vs-realized confounder",
    "Pre-F money-making audit",
    "FAIL/BLOCKED on edge correctness",
    "no live API",
    "offline data only",
    "D#7 phase-2 balance/auth probe not run",
    "production canary NOT approved",
]


def test_poly_api_data_fidelity_audit_artifact_exists_and_has_required_sections():
    """docs/superpowers/quant/poly_api_data_fidelity_audit.md VAR olmalı ve kritik fidelity/NO-GO
    işaretçilerini içermeli. İlk RED: dosya henüz YOK → assertion (feature missing)."""
    assert AUDIT.exists(), f"Poly API data fidelity audit artifact bulunamadı: {AUDIT}"
    text = AUDIT.read_text(encoding="utf-8")
    low = text.lower()
    missing = [m for m in _REQUIRED_MARKERS if m.lower() not in low]
    assert not missing, f"data fidelity audit artifact eksik zorunlu işaretçi: {missing}"
