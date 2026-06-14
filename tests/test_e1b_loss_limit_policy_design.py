"""tests/test_e1b_loss_limit_policy_design.py — E1b Loss Limit Policy Design (TDD).

DAILY_LOSS_LIMIT yalnız bir sayı DEĞİL — bir risk state-machine geçişidir. Sabit 0.10 config RED'i
erken (pivot edildi); önce POLİTİKA tasarlanmalı: modlar (Operational/Cooldown/Exit-Only/Halted),
çekirdek formül `mode = max_priority(active_blockers)`, geçiş matrisi, hiyerarşi, UTC start-of-day
reset (yalnız günlük sayaçlar, yüksek-öncelikli blocker'ları temizlemez), persistence (restart risk
state'i sıfırlamamalı), cooldown/win-reset deadlock çözümü. Policy-first; kod/wiring sonra.

Bu test policy artifact'inin VAR + kritik tasarım işaretçilerini içerdiğini sabitler. İlk RED: dosya
YOK. Canlı API/fetch YOK; saf path kontrolü.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = REPO_ROOT / "docs" / "superpowers" / "risk" / "e1b_loss_limit_policy_design.md"

_REQUIRED_MARKERS = [
    "E1b Loss Limit Policy Design",
    "do not hardcode 0.10 yet",
    "state machine",
    "mode = max_priority(active_blockers)",
    "active_blockers",
    "Operational",
    "Cooldown",
    "Exit-Only",
    "Halted",
    "transition matrix",
    "hierarchy: Halted > Exit-Only > Cooldown > Operational",
    "Halted is logical risk mode, not process restart",
    "Kill-Switch is emergency last resort, outside normal policy mode transitions",
    "Kill-Switch is separate from Halted policy state",
    "Exit-Only is graceful degradation",
    "Exit-Only disables new entries",
    "exit/risk management remains active",
    "consecutive loss streak tracked only in Operational",
    "consecutive loss streak resets on win",
    "6 consecutive realized losses triggers Cooldown",
    "Cooldown disables new entries",
    "Cooldown must not wait for a new win while entries are disabled",
    "Cooldown exit is deterministic time expiry or manual reset",
    "Cooldown exit resets the consecutive-loss trigger without requiring a win",
    "daily realized loss breaker",
    "daily breaker enters Exit-Only",
    "catastrophic bankroll stop",
    "50 percent bankroll drawdown enters Halted",
    "Halted requires human review/manual reset",
    "UTC 00:00 start-of-day boundary",
    "UTC 00:00 resets daily counters, not all risk state",
    "UTC reset refreshes start_of_day_equity",
    "UTC reset zeroes realized_pnl_today",
    "UTC reset may clear daily Exit-Only only if no higher-priority blocker remains",
    "UTC reset must not clear Halted",
    "UTC reset must not clear kill-switch/manual-review state",
    "after any reset, effective mode is recomputed from active blockers",
    "next-day reset for daily limits",
    "no process restart required",
    "restart must not reset risk state",
    "start_of_day_equity",
    "realized_pnl_today",
    "risk mode persistence",
    "state persistence must not be process-memory only",
    "volatility-adjusted thresholds future consideration",
    "MAX_OPEN_POSITIONS=1 for canary",
    "MAX_TRADES_FIRST_SESSION required",
    "trade-size USD cap required",
    "no live API",
    "no production trading code changed",
    "Paper Soak blocked until policy and wiring are verified",
]


def test_e1b_loss_limit_policy_design_artifact_exists_and_has_required_sections():
    """docs/superpowers/risk/e1b_loss_limit_policy_design.md VAR olmalı ve kritik tasarım
    işaretçilerini içermeli. İlk RED: dosya henüz YOK → assertion (feature missing)."""
    assert ARTIFACT.exists(), f"E1b loss-limit policy design artifact bulunamadı: {ARTIFACT}"
    text = ARTIFACT.read_text(encoding="utf-8")
    low = text.lower()
    missing = [m for m in _REQUIRED_MARKERS if m.lower() not in low]
    assert not missing, f"E1b policy design artifact eksik zorunlu işaretçi: {missing}"
