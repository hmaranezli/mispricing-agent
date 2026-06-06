"""position/manager.py — Açık pozisyon takibi ve çıkış kararı."""
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

LOG_FILE = Path("logs/dry_run.jsonl")

PROFIT_TARGET_FRACTION = 0.85
PROFIT_LOCK_MIN        = 0.10  # mutlak yakalanan kazanç bu kadarı geçmeli (≈6¢ round-trip slippage + marj)
PROFIT_CONFIRM_CYCLES  = 2     # kâr sinyali bu kadar ardışık döngü görülmeli (tek snapshot spike koruması)
NEAR_EXPIRY_SECS       = 90
STOP_LOSS_PCT          = 0.20  # entry'den %20 düşerse → stop_loss_hit (felaket koruması)
MIN_HOLD_SECS          = 30    # İlk 30s: stop_loss çalışmaz — anlık tersine dönüş filtresi


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
        "max_hold_time"     — MAX_HOLD_MINUTES doldu
        "profit_target_hit" — Büyük kâr 2 ardışık döngüde onaylandı (erken kilitle)
        "stop_loss_hit"     — Gerçek PM zararı -%20'yi geçti (MIN_HOLD sonrası, felaket koruması)
        None                — tut (varsayılan: resolve'a kadar bekle — para resolve'dan geliyor)

    Felsefe (2026-06-05 veri analizi):
      Erken çıkışlar net -$2.64 kaybettiriyor, resolve'a kadar tutuşlar +$10.10 kazandırıyor.
      Bu yüzden VARSAYILAN resolve'a kadar tutmak. Erken çıkış yalnızca iki halde:
        1. Büyük, onaylanmış kâr (slippage'i hak eden) → profit_target_hit
        2. Felaket zararı (yanıldık, token çöküyor) → stop_loss_hit
      thesis_invalidated KALDIRILDI: pencere-ortası HL dönüşleri çoğunlukla gürültü,
      resolve'a kadar geri dönüyor; tek başına -$5.97 kaybettiriyordu.
    """
    # 1. Market kapanışa yakın → sadece profit_target ve max_hold'u engelle.
    #    stop_loss geçer: son saniyede çöküş olursa tam kayıptan koru.
    near_expiry = time_to_expiry_secs < NEAR_EXPIRY_SECS

    # 2. Zaman limiti (near_expiry'de engelle — market zaten kapanıyor)
    if near_expiry:
        pass  # skip non-stop-loss exits below; stop_loss still checked at step 5
    opened_at = datetime.fromisoformat(position["opened_at"])
    now = datetime.now(timezone.utc)
    held_minutes = (now - opened_at).total_seconds() / 60
    if not near_expiry and held_minutes >= config.MAX_HOLD_MINUTES:
        return "max_hold_time"

    entry_price = position["pm_entry_price"]
    if position["action"] == "YES":
        current_val = pm_yes_price
        target_val  = position["fair_value"]
    else:
        current_val = 1 - pm_yes_price
        target_val  = 1 - position["fair_value"]

    # 3. Kâr hedefi — yalnızca BÜYÜK + ONAYLANMIŞ kazançta erken çıkış
    #    a) edge'in PROFIT_TARGET_FRACTION'ı yakalandı (oransal)
    #    b) mutlak kazanç PROFIT_LOCK_MIN'i geçti (round-trip slippage'i hak etsin)
    #    c) PROFIT_CONFIRM_CYCLES ardışık döngüde görüldü (tek snapshot spike koruması)
    edge     = target_val - entry_price
    captured = current_val - entry_price
    profit_ready = (
        edge > 0
        and captured / edge >= PROFIT_TARGET_FRACTION
        and captured >= PROFIT_LOCK_MIN
    )
    if profit_ready and not near_expiry:
        position["_profit_confirm"] = position.get("_profit_confirm", 0) + 1
        if position["_profit_confirm"] >= PROFIT_CONFIRM_CYCLES:
            return "profit_target_hit"
    else:
        position["_profit_confirm"] = 0

    # 4. MIN_HOLD_SECS: ilk 60s içinde stop_loss çalışmaz (anlık ters dönüş gürültüsü)
    held_seconds = (now - opened_at).total_seconds()
    if held_seconds < MIN_HOLD_SECS:
        return None

    # 5. Stop-loss: gerçek PM zararı entry'den STOP_LOSS_PCT kadar düştüyse (felaket koruması)
    if current_val < entry_price * (1 - STOP_LOSS_PCT):
        return "stop_loss_hit"

    # 6. Varsayılan: resolve'a kadar tut
    return None
