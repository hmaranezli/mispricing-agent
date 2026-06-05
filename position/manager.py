"""position/manager.py — Açık pozisyon takibi ve çıkış kararı."""
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from data.fair_value import fair_yes

LOG_FILE = Path("logs/dry_run.jsonl")

PROFIT_TARGET_FRACTION = 0.85
NEAR_EXPIRY_SECS       = 90


def _log(event: str, data: dict, log_file: Path = LOG_FILE) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts":    datetime.now(timezone.utc).isoformat(),
        "layer": "position",
        "event": event,
        **data,
    }
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def close_position(
    position:      dict,
    exit_reason:   str,
    pm_exit_price: float | None = None,
    exit_hl_price: float | None = None,
    log_file:      Path = LOG_FILE,
) -> dict:
    """Pozisyonu kapatır, JSONL'a yazar, güncellenmiş kaydı döndürür."""
    closed = {
        **position,
        "status":        "closed",
        "exit_reason":   exit_reason,
        "closed_at":     datetime.now(timezone.utc).isoformat(),
        "pm_exit_price": pm_exit_price,
        "exit_hl_price": exit_hl_price,
    }
    _log("position_closed", {
        "position_id":    closed["position_id"],
        "asset":          closed["asset"],
        "action":         closed["action"],
        "slug":           closed["slug"],
        "exit_reason":    exit_reason,
        "pm_entry_price": closed["pm_entry_price"],
        "pm_exit_price":  pm_exit_price,
        "exit_hl_price":  exit_hl_price,
        "fair_value":     closed["fair_value"],
        "closed_at":      closed["closed_at"],
        "dry_run":        closed["dry_run"],
    }, log_file)
    return closed


def check_exit(
    position:            dict,
    hl_price:            float,
    pm_yes_price:        float,
    time_to_expiry_secs: int,
) -> str | None:
    """
    Pozisyon için çıkış kararı verir.

    Returns:
        "max_hold_time"      — MAX_HOLD_MINUTES doldu
        "thesis_invalidated" — HL tersine döndü
        "profit_target_hit"  — Edge'in %85'i yakalandı
        None                 — tut
    """
    # 1. Market kapanışa yakın → dokunma, bırak çözümlensin
    if time_to_expiry_secs < NEAR_EXPIRY_SECS:
        return None

    # 2. Zaman limiti
    opened_at = datetime.fromisoformat(position["opened_at"])
    held_minutes = (datetime.now(timezone.utc) - opened_at).total_seconds() / 60
    if held_minutes >= config.MAX_HOLD_MINUTES:
        return "max_hold_time"

    entry_price = position["pm_entry_price"]

    # 3. Kâr hedefi — edge'in PROFIT_TARGET_FRACTION kadarı yakalandı mı?
    # Önce kâr kontrolü: thesis_invalidated'dan önce gelmeli ki kazancı kaçırmasın
    if position["action"] == "YES":
        current_val = pm_yes_price
        target_val  = position["fair_value"]
    else:
        current_val = 1 - pm_yes_price
        target_val  = 1 - position["fair_value"]

    edge = target_val - entry_price
    if edge > 0 and (current_val - entry_price) / edge >= PROFIT_TARGET_FRACTION:
        return "profit_target_hit"

    # 4. Thesis kontrolü — HL yön kaybetti mi?
    # YES girişi: HL ref'in ÜSTÜNDEYDI (bullish). Thesis bozulur → HL ref'in altına düşünce.
    # NO girişi: HL ref'in ALTINDAYDI (bearish). Thesis bozulur → HL ref'in üstüne çıkınca.
    # Eşik: her zaman 0.50 ± buffer — entry fiyatına bağlı DEĞİL.
    # (entry price bazlı eşik: NO_entry=0.64 → threshold=0.34, HL ref'e döner dönmez ateşliyordu)
    new_fair = fair_yes(hl_price, position["ref_price"],
                        time_to_expiry_secs, position["asset"])
    thesis_buffer = 0.02
    if position["action"] == "YES":
        thesis_broken = new_fair < (0.50 - thesis_buffer)   # HL bearish'e döndü
    else:
        thesis_broken = new_fair > (0.50 + thesis_buffer)   # HL bullish'e döndü

    if thesis_broken:
        return "thesis_invalidated"

    return None
