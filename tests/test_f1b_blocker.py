"""tests/test_f1b_blocker.py — F1b real HL↔Chainlink basis measurement BLOCKER (TDD).

F1a, PM Up/Down'ın Chainlink BTC/USD **Data Streams** (data.chain.link/streams/btc-usd) ile resolve
olduğunu kanıtladı ve HL≠Chainlink confounder'ını işaretledi. F1b gerçek ölçümü, exact Data Streams
verisi olmadan YAPILAMAZ — Data Streams authenticated (API key) iken Data Feeds (on-chain) DEĞİLDİR ve
ikisi DEĞİŞTİRİLEMEZ (interchangeable değil).

KRİTİK quant blocker = Time Resolution Mismatch: Data Streams tick/pull-based + düşük latency; Data
Feeds heartbeat/deviation push-based + stale kalabilir. Feed'i 30s/60s shift_seconds ile kullanmak
GERÇEK kaynak basis'i değil, temporal heartbeat noise / stale price confounder ölçer → F1b'yi
TEMİZLEMEZ. Feed-proxy yalnız açıkça etiketli smoke test olarak ileride kullanılabilir.

Bu test, blocker artifact'inin VAR + kritik işaretçileri içerdiğini sabitler. İlk RED: dosya YOK.
Canlı API/Chainlink/HL fetch YOK; offline data only.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = REPO_ROOT / "docs" / "superpowers" / "quant" / "f1b_chainlink_stream_blocker.md"

# Gelecek GREEN'de bulunması ZORUNLU işaretçiler (substring, case-insensitive).
_REQUIRED_MARKERS = [
    "F1b Measurement BLOCKED",
    "Data Streams vs Data Feeds",
    "Authentication required for Streams",
    "Time Resolution Mismatch",
    "Heartbeat/Deviation vs Tick/Pull",
    "temporal heartbeat noise",
    "stale price confounder",
    "Allowed paths: exact Streams auth, explicit manual CSV/JSON paste, "
    "explicitly-labeled Feed-proxy smoke test cannot clear F1b",
    "no live API",
    "offline data only",
]


def test_f1b_blocker_artifact_exists_and_has_required_sections():
    """docs/superpowers/quant/f1b_chainlink_stream_blocker.md VAR olmalı ve kritik blocker
    işaretçilerini içermeli. İlk RED: dosya henüz YOK → assertion (feature missing)."""
    assert ARTIFACT.exists(), f"F1b blocker artifact bulunamadı: {ARTIFACT}"
    text = ARTIFACT.read_text(encoding="utf-8")
    low = text.lower()
    missing = [m for m in _REQUIRED_MARKERS if m.lower() not in low]
    assert not missing, f"F1b blocker artifact eksik zorunlu işaretçi: {missing}"
