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

import config

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_daily_loss_halt_triggers_at_configured_limit():
    """daily_loss_pct >= config.DAILY_LOSS_LIMIT → 'daily_loss_stop'; altı → None; kâr/sıfır → None.
    E8 micro-canary: config.DAILY_LOSS_LIMIT = 0.35 (eski 0.10 hardcode'u kaldırıldı). Saf, offline."""
    from monitor.circuit_breaker import daily_loss_halt

    # E8 yapılandırılmış eşik 0.35 (boundary sayıları buna göre).
    assert config.DAILY_LOSS_LIMIT == 0.35, \
        f"E8 micro-canary eşiği 0.35 olmalı: {config.DAILY_LOSS_LIMIT}"

    # Eşik ALTI: 349/1000 = %34.9 < %35 → halt YOK
    assert daily_loss_halt(start_of_day_equity=1000.0, realized_pnl_today=-349.0) is None, \
        "%34.9 kayıp eşik altı → halt yok"

    # Eşik/ÜSTÜ: 350/1000 = %35 ≥ %35 → yeni giriş DUR
    assert daily_loss_halt(start_of_day_equity=1000.0, realized_pnl_today=-350.0) == "daily_loss_stop", \
        "%35 kayıp → daily_loss_stop (yeni giriş durur)"

    # Kâr / sıfır kayıp → halt YOK (negatif loss_pct max(0,...) ile 0'a clamp)
    assert daily_loss_halt(start_of_day_equity=1000.0, realized_pnl_today=50.0) is None, \
        "kârda → halt yok"
    assert daily_loss_halt(start_of_day_equity=1000.0, realized_pnl_today=0.0) is None, \
        "sıfır pnl → halt yok"


def test_daily_loss_halt_fallback_when_config_missing(monkeypatch):
    """config.DAILY_LOSS_LIMIT YOKSA daily_loss_halt getattr fallback'i 0.10 kullanır (eski davranış
    korunur). monkeypatch ile sabit kaldırılır; daily_loss_halt onu call-time okur."""
    from monitor.circuit_breaker import daily_loss_halt
    monkeypatch.delattr(config, "DAILY_LOSS_LIMIT", raising=False)

    # Fallback 0.10 → 99/1000 = %9.9 < %10 → halt YOK
    assert daily_loss_halt(start_of_day_equity=1000.0, realized_pnl_today=-99.0) is None, \
        "fallback %10 altı → halt yok"
    # Fallback 0.10 → 100/1000 = %10 ≥ %10 → DUR
    assert daily_loss_halt(start_of_day_equity=1000.0, realized_pnl_today=-100.0) == "daily_loss_stop", \
        "fallback %10 → daily_loss_stop"
