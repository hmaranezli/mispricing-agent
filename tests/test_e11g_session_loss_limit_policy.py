"""tests/test_e11g_session_loss_limit_policy.py — E11g SESSION_LOSS_LIMIT policy decision (docs-only TDD).

Master E kalan maddesi SESSION_LOSS_LIMIT, read-only discovery sonrası DEFER ediliyor: DB-backed,
NET-PnL, gün-anahtarlı DAILY_LOSS_LIMIT (restart-safe, → Exit-Only) micro-canary kayıp bütçesini zaten
kapsıyor; in-memory session-loss yalnız risk-farkındalık side-car'ı (restart-unsafe, sermaye koruması
DEĞİL). Bu slice ENFORCEMENT breaker eklemez — yalnız policy kararını bir artifact'a sabitler
(E1b/E7 docs-only cadence). config.SESSION_LOSS_LIMIT / session_loss_halt / schema değişikliği YOK.

İlk RED: policy artifact yok → dosya bulunamaz / marker'lar eksik. Üretim/config/schema'ya dokunulmaz.
"""
import os

ARTIFACT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "superpowers", "risk", "e11g_session_loss_limit_policy.md",
)

REQUIRED_MARKERS = [
    "VERDICT: DEFERRED",
    "DAILY_LOSS_LIMIT covers session-loss for micro-canary",
    "SESSION_LOSS_LIMIT is not implemented as an enforcement breaker",
    "in-memory session-loss is risk-awareness side-car, not capital protection",
    "restart-unsafe",
    "entry-only BLOCK",
    "never full halt",
    "exit paths remain active",
    "SESSION_LOSS_LIMIT config constant is human-owned",
    "no schema migration",
    "no DB-backed session state",
    "future DB-backed session loss requires explicit policy and migration",
    "DAILY_LOSS_LIMIT config/fallback observation required",
]


def _read_artifact() -> str:
    assert os.path.exists(ARTIFACT), f"E11g policy artifact eksik: {ARTIFACT}"
    with open(ARTIFACT, encoding="utf-8") as f:
        return f.read()


def test_artifact_exists():
    """Policy artifact dosyası mevcut olmalı. RED: dosya yok → AssertionError."""
    assert os.path.exists(ARTIFACT), f"E11g policy artifact eksik: {ARTIFACT}"


def test_required_markers_present():
    """Tüm zorunlu literal marker'lar artifact'ta olmalı. RED: artifact yok / marker eksik."""
    text = _read_artifact()
    missing = [m for m in REQUIRED_MARKERS if m not in text]
    assert not missing, f"E11g policy artifact eksik marker(lar): {missing}"
