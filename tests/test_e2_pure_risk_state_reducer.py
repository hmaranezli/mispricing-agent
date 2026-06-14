"""tests/test_e2_pure_risk_state_reducer.py — E2 pure risk-state reducer (TDD).

E1b policy'sini kodlanabilir tek saf fonksiyona indirger: `reduce_risk_mode(active_blockers) -> str`.
SAF: global state YOK, DB YOK, clock YOK, config erişimi YOK, production yan etki YOK.

Çekirdek: mode = max_priority(active_blockers). Öncelik (yüksek→düşük):
  Kill-Switch > Halted > Exit-Only > Cooldown > Operational.
Blocker→mode map: kill_switch→Kill-Switch, halted/manual_review→Halted, daily_loss→Exit-Only,
cooldown→Cooldown, [] (identity)→Operational. Kill-Switch acil son çare; Halted'a İNDİRİLMEZ.
Bilinmeyen blocker SESSİZCE yutulmaz → ValueError.

İlk RED: monitor.risk_state / reduce_risk_mode YOK → ModuleNotFoundError/ImportError. Canlı API yok.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_reduce_risk_mode_max_priority_contract():
    """Identity, hiyerarşi, Kill-Switch>Halted, sıra-bağımsızlık, idempotent dup, unknown→ValueError.
    İlk RED: monitor.risk_state.reduce_risk_mode YOK (saf reducer eksik)."""
    from monitor.risk_state import reduce_risk_mode

    # Identity
    assert reduce_risk_mode([]) == "Operational"

    # Tek blocker → kendi modu
    assert reduce_risk_mode(["cooldown"]) == "Cooldown"
    assert reduce_risk_mode(["daily_loss"]) == "Exit-Only"
    assert reduce_risk_mode(["halted"]) == "Halted"
    assert reduce_risk_mode(["kill_switch"]) == "Kill-Switch"
    assert reduce_risk_mode(["manual_review"]) == "Halted"

    # max_priority hiyerarşisi
    assert reduce_risk_mode(["cooldown", "daily_loss"]) == "Exit-Only"
    assert reduce_risk_mode(["daily_loss", "halted"]) == "Halted"
    assert reduce_risk_mode(["cooldown", "halted"]) == "Halted"

    # Kill-Switch en üstte; Halted'a İNDİRİLMEZ
    assert reduce_risk_mode(["kill_switch", "halted"]) == "Kill-Switch"
    assert reduce_risk_mode(["kill_switch", "daily_loss"]) == "Kill-Switch"

    # Sıra-bağımsızlık
    assert reduce_risk_mode(["daily_loss", "cooldown"]) == "Exit-Only"
    assert reduce_risk_mode(["daily_loss", "kill_switch"]) == "Kill-Switch"

    # Idempotent duplicate
    assert reduce_risk_mode(["cooldown", "cooldown"]) == "Cooldown"
    assert reduce_risk_mode(["kill_switch", "kill_switch"]) == "Kill-Switch"

    # Bilinmeyen blocker → ValueError (sessizce yutulMAZ)
    with pytest.raises(ValueError):
        reduce_risk_mode(["unknown_blocker"])
