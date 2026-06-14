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


# E4 active_blockers köprüsü: sinyal→blocker dönüşümü + kanonik çıktı sırası.
_CANONICAL_ORDER = ["kill_switch", "manual_review", "halted", "daily_loss", "cooldown"]
_INACTIVE_STATUSES = (None, "", "ok", "continue", "no_stop")


def build_active_blockers(daily_loss_status=None, circuit_breaker_status=None,
                          kill_switch_active=False, manual_review_required=False) -> list:
    """Mevcut risk/breaker sinyallerini reducer'ın anladığı active_blockers listesine çevirir.

    SAF: circuit_breaker/daily_loss_halt ÇAĞIRMAZ, persist/DB YOK, config/env/global YOK, network YOK,
    effective_mode HESAPLAMAZ, girdileri mutate ETMEZ. Yalnız caller-verilen sinyal değerlerini dönüştürür.

    Map: daily_loss_status=="daily_loss_stop"→"daily_loss"; circuit_breaker_status "soft_stop"→"cooldown",
    "hard_stop"→"halted"; kill_switch_active→"kill_switch"; manual_review_required→"manual_review".
    Pasif: None/""/"ok"/"continue"/"no_stop". Bilinmeyen daily_loss/circuit_breaker status → ValueError.
    Çıktı _CANONICAL_ORDER'a göre süzülür (yalnız aktif olanlar, duplicate yok). circuit_breaker_status
    tek değerli olduğundan cooldown VE halted aynı anda olamaz (5-öğeli "all active" ulaşılamaz)."""
    active = set()

    if daily_loss_status not in _INACTIVE_STATUSES:
        if daily_loss_status == "daily_loss_stop":
            active.add("daily_loss")
        else:
            raise ValueError(f"Bilinmeyen daily_loss_status: {daily_loss_status!r}")

    if circuit_breaker_status not in _INACTIVE_STATUSES:
        if circuit_breaker_status == "soft_stop":
            active.add("cooldown")
        elif circuit_breaker_status == "hard_stop":
            active.add("halted")
        else:
            raise ValueError(f"Bilinmeyen circuit_breaker_status: {circuit_breaker_status!r}")

    if kill_switch_active:
        active.add("kill_switch")
    if manual_review_required:
        active.add("manual_review")

    return [b for b in _CANONICAL_ORDER if b in active]
