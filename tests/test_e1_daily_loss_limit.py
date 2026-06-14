"""tests/test_e1_daily_loss_limit.py — E1 DAILY_LOSS_LIMIT enforcement (TDD).

Anayasa (CLAUDE.md §5): "Günlük kayıp %10'a ulaşınca TÜM SİSTEM DURUR." E0 envanteri bunun kodda
UYGULANMADIĞINI gösterdi (circuit_breaker yalnız bust %50 + streak; risk.py yorumu "taşındı" diyor
ama enforce eden kod yok). E1 bunu enforceable hale getirir.

Stil: monitor/circuit_breaker.py STATUS-RETURN kullanır (`on_trade_closed -> str | None`,
'hard_stop'/'soft_stop'/None) — exception DEĞİL. E1 aynı stili izler: saf `daily_loss_halt(
start_of_day_equity, realized_pnl_today) -> str | None`.

Matematik (açık): daily_loss_pct = max(0, -realized_pnl_today / start_of_day_equity).
Tetik: daily_loss_pct >= 0.10 → yeni girişleri durdur ('daily_loss_stop'). BUST_PROTECTION_PCT=0.50'den
AYRI (bust = felaket drawdown; daily loss = gün/seans riski).

SAF + offline: sentetik equity/pnl; DB/API/clock YOK. İlk RED: daily_loss_halt YOK → ImportError
(enforceable kod eksik — yalnız docs değil).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_daily_loss_halt_triggers_at_ten_percent():
    """daily_loss_pct >= %10 → 'daily_loss_stop'; altı → None; kâr/sıfır → None. Saf, offline.
    İlk RED: monitor.circuit_breaker.daily_loss_halt YOK → ImportError (DAILY_LOSS_LIMIT enforce edilmiyor)."""
    from monitor.circuit_breaker import daily_loss_halt

    # Eşik ALTI: 99.99/1000 = %9.999 < %10 → halt YOK
    assert daily_loss_halt(start_of_day_equity=1000.0, realized_pnl_today=-99.99) is None, \
        "%9.999 kayıp eşik altı → halt yok"

    # Eşik/ÜSTÜ: 100/1000 = %10 ≥ %10 → yeni giriş DUR
    assert daily_loss_halt(start_of_day_equity=1000.0, realized_pnl_today=-100.0) == "daily_loss_stop", \
        "%10 kayıp → daily_loss_stop (yeni giriş durur)"

    # Kâr / sıfır kayıp → halt YOK (negatif loss_pct max(0,...) ile 0'a clamp)
    assert daily_loss_halt(start_of_day_equity=1000.0, realized_pnl_today=50.0) is None, \
        "kârda → halt yok"
    assert daily_loss_halt(start_of_day_equity=1000.0, realized_pnl_today=0.0) is None, \
        "sıfır pnl → halt yok"
