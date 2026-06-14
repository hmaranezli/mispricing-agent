"""monitor/risk_state.py — E2 saf risk-state reducer (E1b policy'sinin kodlanabilir çekirdeği).

SAF fonksiyon: global mutable state YOK, DB YOK, clock/time YOK, config erişimi YOK, env YOK, network
YOK, production loop modüllerinden import YOK, yan etki YOK. Yalnız active_blockers → effective_mode.

Çekirdek: mode = max_priority(active_blockers). Öncelik (yüksek→düşük):
  Kill-Switch > Halted > Exit-Only > Cooldown > Operational.
Kill-Switch acil son çare; Halted'a İNDİRİLMEZ (en üstte kalır).
"""

# Blocker adı → risk modu (explicit; sessiz fallback yok).
_BLOCKER_MODE = {
    "kill_switch":   "Kill-Switch",
    "halted":        "Halted",
    "manual_review": "Halted",
    "daily_loss":    "Exit-Only",
    "cooldown":      "Cooldown",
}

# Mod önceliği (büyük = daha yüksek). "Operational" = identity (blocker yok).
_MODE_PRIORITY = {
    "Operational": 0,
    "Cooldown":    1,
    "Exit-Only":   2,
    "Halted":      3,
    "Kill-Switch": 4,
}


def reduce_risk_mode(active_blockers) -> str:
    """active_blockers listesinden efektif risk modu = en yüksek öncelikli mod.

    Boş liste → "Operational" (identity). Bilinmeyen blocker → ValueError (adıyla; sessizce yutulmaz).
    Sıra-bağımsız ve duplicate-idempotent (max üzerinden doğal). SAF — yan etki yok.
    """
    effective = "Operational"
    for blocker in active_blockers:
        if blocker not in _BLOCKER_MODE:
            raise ValueError(f"Bilinmeyen risk blocker: {blocker!r}")
        mode = _BLOCKER_MODE[blocker]
        if _MODE_PRIORITY[mode] > _MODE_PRIORITY[effective]:
            effective = mode
    return effective
