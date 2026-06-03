"""tests/test_circuit_breaker.py — monitor/circuit_breaker.py testleri."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def _reset():
    import monitor.state as s
    s.SOFT_PAUSED = False
    s.HARD_PAUSED = False
    import monitor.circuit_breaker as cb
    cb._consecutive_losses = 0


@pytest.fixture
def _reset_fixture():
    _reset()
    yield
    _reset()


def test_win_resets_streak(_reset_fixture):
    from monitor.circuit_breaker import on_trade_closed
    on_trade_closed(pnl=-1.0, current_bankroll=24.0, starting_bankroll=25.0)
    on_trade_closed(pnl=-1.0, current_bankroll=23.0, starting_bankroll=25.0)
    result = on_trade_closed(pnl=+1.0, current_bankroll=24.0, starting_bankroll=25.0)
    import monitor.circuit_breaker as cb
    assert cb._consecutive_losses == 0
    assert result is None


def test_bust_triggers_hard_stop(_reset_fixture):
    from monitor.circuit_breaker import on_trade_closed
    import monitor.state as s
    result = on_trade_closed(pnl=-1.0, current_bankroll=12.0, starting_bankroll=25.0)
    assert result == 'hard_stop'
    assert s.HARD_PAUSED is True


def test_streak_zararda_triggers_soft_stop(_reset_fixture):
    from monitor.circuit_breaker import on_trade_closed
    import monitor.state as s
    for _ in range(6):
        result = on_trade_closed(pnl=-1.0, current_bankroll=20.0, starting_bankroll=25.0)
    assert result == 'soft_stop'
    assert s.SOFT_PAUSED is True
    assert s.HARD_PAUSED is False


def test_streak_karda_still_soft_stop(_reset_fixture):
    """Karda olsa bile streak >= 6 → SOFT STOP."""
    from monitor.circuit_breaker import on_trade_closed
    import monitor.state as s
    for _ in range(6):
        result = on_trade_closed(pnl=-1.0, current_bankroll=30.0, starting_bankroll=25.0)
    assert result == 'soft_stop'
    assert s.SOFT_PAUSED is True
    assert s.HARD_PAUSED is False


def test_bust_overrides_streak(_reset_fixture):
    """Bankroll %50 altina dusunce hard stop — streak sayisindan bagimsiz."""
    from monitor.circuit_breaker import on_trade_closed
    result = on_trade_closed(pnl=-1.0, current_bankroll=11.0, starting_bankroll=25.0)
    assert result == 'hard_stop'


def test_five_losses_no_trigger(_reset_fixture):
    """5 arka arkaya kayip — henuz tetiklememeli (esik 6)."""
    from monitor.circuit_breaker import on_trade_closed
    import monitor.state as s
    for _ in range(5):
        result = on_trade_closed(pnl=-1.0, current_bankroll=20.0, starting_bankroll=25.0)
    assert result is None
    assert s.SOFT_PAUSED is False


def test_win_after_five_losses_no_soft_stop(_reset_fixture):
    """5 kayip + 1 kazanc → streak sifirlanir, soft stop olmamali."""
    from monitor.circuit_breaker import on_trade_closed
    import monitor.state as s
    for _ in range(5):
        on_trade_closed(pnl=-1.0, current_bankroll=20.0, starting_bankroll=25.0)
    result = on_trade_closed(pnl=+2.0, current_bankroll=22.0, starting_bankroll=25.0)
    assert s.SOFT_PAUSED is False
    assert result is None


def test_hard_stop_takes_priority_over_streak(_reset_fixture):
    """Bust ve streak ayni anda → hard stop oncelikli."""
    from monitor.circuit_breaker import on_trade_closed
    import monitor.state as s
    for _ in range(5):
        on_trade_closed(pnl=-1.0, current_bankroll=20.0, starting_bankroll=25.0)
    result = on_trade_closed(pnl=-1.0, current_bankroll=10.0, starting_bankroll=25.0)
    assert result == 'hard_stop'
    assert s.HARD_PAUSED is True
    assert s.SOFT_PAUSED is False
