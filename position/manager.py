"""position/manager.py — Açık pozisyon takibi ve çıkış kararı."""
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from data import ws_prices as _ws

LOG_FILE = Path("logs/dry_run.jsonl")

PROFIT_TARGET_FRACTION = 0.85
PROFIT_LOCK_MIN        = 0.10  # mutlak yakalanan kazanç bu kadarı geçmeli (≈6¢ round-trip slippage + marj)
PROFIT_CONFIRM_CYCLES  = 2     # kâr sinyali bu kadar ardışık döngü görülmeli (tek snapshot spike koruması)
NEAR_EXPIRY_SECS       = 90
STOP_LOSS_MAX          = 0.25  # Kalibrasyon: -%25 eşiği (eski 0.30 — veri: winner P25 MAE=-22.4%, loser P50=-29.5%, sim FalseCut=0)
STOP_LOSS_MIN          = 0.12  # Vadeye yakında min tolerans (%12) — gamma trap erken tespiti
MIN_HOLD_SECS          = 15    # Kalibrasyon: ilk 15s stop çalışmaz (eski 30 — daha çevik giriş koruması)
MIN_PROFIT_CONFIRM_SECS = 3   # WS hızında cycle-sayısı yeterli değil — zaman kapısı


def _dynamic_stop(held_secs: float, time_to_expiry_secs: int) -> float:
    """Zaman bazlı dinamik stop eşiği.

    Giriş anında geniş tolerans (toparlama vakti var), vadeye yakın dar tolerans
    (gamma trap — kitap inceliyor, fill kötüleşiyor, erken çık).

    SL(t) = STOP_LOSS_MAX - fraction_elapsed × (STOP_LOSS_MAX - STOP_LOSS_MIN)

    #1270 anatomisi: 0.55→0.09 bir 7s scan cycle'da kitap çöktü.
    Static %20 stop doğru tetikledi AMA fill zamanında kitap yoktu.
    Tighter near-expiry stop daha erken tetikler → fill daha iyi.
    """
    total = held_secs + max(time_to_expiry_secs, 1)
    fraction_elapsed = held_secs / total
    return STOP_LOSS_MAX - fraction_elapsed * (STOP_LOSS_MAX - STOP_LOSS_MIN)


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
    entry_price = position["pm_entry_price"]
    if position["action"] == "YES":
        current_val  = pm_yes_price
        target_val   = position["fair_value"]
        _mae_quality = "exact"
    else:
        _no_tid = position.get("no_token_id")
        _no_bid = _ws.get_bid(_no_tid) if _no_tid else None
        if _no_bid is not None:
            current_val  = _no_bid
            _mae_quality = "exact"
        elif position.get("_no_clob_bid") is not None:
            current_val  = position["_no_clob_bid"]
            _mae_quality = "clob_fallback"
        else:
            current_val  = 1 - pm_yes_price
            _mae_quality = "estimated"
        target_val = 1 - position["fair_value"]

    # ── MAE/MFE in-memory tracking ────────────────────────────────────────────
    if entry_price and entry_price > 0:
        current_pct = (current_val - entry_price) / entry_price
        position["price_source"]     = "rest"
        position["mae_data_quality"] = _mae_quality
        if position.get("mae_px") is None or current_val < position["mae_px"]:
            position["mae_px"]  = current_val
            position["mae_pct"] = current_pct
            position["mae_ts"]  = now.isoformat()
        if position.get("mfe_px") is None or current_val > position["mfe_px"]:
            position["mfe_px"]  = current_val
            position["mfe_pct"] = current_pct
            position["mfe_ts"]  = now.isoformat()
    # ─────────────────────────────────────────────────────────────────────────

    # 2. Zaman limiti (near_expiry'de engelle — market zaten kapanıyor)
    if not near_expiry and held_minutes >= config.MAX_HOLD_MINUTES:
        return "max_hold_time"

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
        position.setdefault("_profit_confirm_first_ts", now.isoformat())
        elapsed = (now - datetime.fromisoformat(
            position["_profit_confirm_first_ts"]
        )).total_seconds()
        if (position["_profit_confirm"] >= PROFIT_CONFIRM_CYCLES
                and elapsed >= MIN_PROFIT_CONFIRM_SECS):
            return "profit_target_hit"
    else:
        position["_profit_confirm"] = 0
        position.pop("_profit_confirm_first_ts", None)

    # 4. MIN_HOLD_SECS: ilk 60s içinde stop_loss çalışmaz (anlık ters dönüş gürültüsü)
    held_seconds = (now - opened_at).total_seconds()
    if held_seconds < MIN_HOLD_SECS:
        return None

    # 5. Dynamic stop-loss: erken geniş, vadeye yakın dar (gamma trap koruması)
    sl_threshold = _dynamic_stop(held_seconds, time_to_expiry_secs)
    if current_val < entry_price * (1 - sl_threshold):
        position.setdefault("sl_trigger_px", current_val)
        position.setdefault("first_trigger_ts", now.isoformat())
        if entry_price and entry_price > 0:
            position.setdefault(
                "sl_trigger_pct",
                (current_val - entry_price) / entry_price,
            )
        return "stop_loss_hit"

    # 6. Varsayılan: resolve'a kadar tut
    return None
