"""monitor/circuit_breaker.py — Akilli devre kesici: bankroll korumasi + streak takibi."""
import config
from monitor.state import soft_pause, hard_pause

_consecutive_losses: int = 0

BUST_PROTECTION_PCT: float = getattr(config, "BUST_PROTECTION_PCT", 0.50)
STREAK_WARN_COUNT:   int   = getattr(config, "STREAK_WARN_COUNT", 6)


def reset_streak() -> None:
    global _consecutive_losses
    _consecutive_losses = 0


def on_trade_closed(pnl: float, current_bankroll: float, starting_bankroll: float) -> str | None:
    """
    Her trade kapanisinda cagrilir.

    Returns:
        'hard_stop'  → bankroll %50 altina dustu, HARD_PAUSED=True
        'soft_stop'  → streak >= N (karda da zararda da), SOFT_PAUSED=True
        None         → normal, devam et
    """
    global _consecutive_losses

    if pnl >= 0:
        _consecutive_losses = 0
        return None

    # Bust: bankroll yariya dustu — her zaman oncelikli
    if current_bankroll < starting_bankroll * BUST_PROTECTION_PCT:
        hard_pause()
        return 'hard_stop'

    _consecutive_losses += 1

    if _consecutive_losses >= STREAK_WARN_COUNT:
        soft_pause()
        return 'soft_stop'

    return None
