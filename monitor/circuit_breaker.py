"""monitor/circuit_breaker.py — Akilli devre kesici: bankroll korumasi + streak takibi."""
import config
from monitor.state import soft_pause, hard_pause

_consecutive_losses: int = 0

BUST_PROTECTION_PCT: float = getattr(config, "BUST_PROTECTION_PCT", 0.50)
STREAK_WARN_COUNT:   int   = getattr(config, "STREAK_WARN_COUNT", 6)


def reset_streak() -> None:
    global _consecutive_losses
    _consecutive_losses = 0


def daily_loss_halt(start_of_day_equity, realized_pnl_today) -> str | None:
    """E1 — Anayasa §5 günlük kayıp limiti. SAF + offline (clock/DB/global state YOK).

    daily_loss_pct = max(0, -realized_pnl_today / start_of_day_equity).
    daily_loss_pct >= DAILY_LOSS_LIMIT → "daily_loss_stop" (yeni girişler durur), aksi None.
    Status-return stili (on_trade_closed ile simetrik; exception breaker DEĞİL). BUST_PROTECTION_PCT
    (felaket drawdown) ve streak'ten AYRI gün/seans guard'ı.

    Eşik: getattr(config, "DAILY_LOSS_LIMIT", 0.10) — config sabiti ayrı (anayasa) RED/GREEN'de eklenecek.
    start_of_day_equity <= 0 → ValueError (sessiz sıfıra bölme YOK).
    """
    if start_of_day_equity <= 0:
        raise ValueError(f"start_of_day_equity pozitif olmalı: {start_of_day_equity}")
    limit = getattr(config, "DAILY_LOSS_LIMIT", 0.10)
    daily_loss_pct = max(0.0, -realized_pnl_today / start_of_day_equity)
    if daily_loss_pct >= limit:
        return "daily_loss_stop"
    return None


def max_trades_first_session_halt(trades_today, *, limit=None) -> str | None:
    """E10a — ilk-seans işlem-sayısı capı. SAF + offline (DB/API/canlı state YOK; trades_today enjekte).

    trades_today >= limit → "max_trades_stop" (yeni girişler durur), aksi None. Status-return stili
    (daily_loss_halt simetrisi). limit None → getattr(config, "MAX_TRADES_FIRST_SESSION", 6) [conservative
    fallback = STREAK_WARN_COUNT ile hizalı; config sabiti AYRI human-owned task]. trades_today<0 veya
    limit<=0 → ValueError. Restart-safe DEĞİL (enjekte sayaç); RiskStateSnapshot şemasına dokunmaz."""
    if limit is None:
        limit = getattr(config, "MAX_TRADES_FIRST_SESSION", 6)
    if limit <= 0:
        raise ValueError(f"limit pozitif olmalı: {limit}")
    if trades_today < 0:
        raise ValueError(f"trades_today negatif olamaz: {trades_today}")
    if trades_today >= limit:
        return "max_trades_stop"
    return None


def no_fill_burst_halt(no_fill_streak, *, limit=None) -> str | None:
    """E11a — arka arkaya no-fill/no-open burst breaker. SAF + offline (DB/API/canlı state YOK;
    no_fill_streak enjekte). FAK_ZERO_FILL / RECOVERY_REQUIRED / prevalidation-reject gibi capital
    riske girmeyen ama submit gürültüsü üreten ardışık çıktılar eşiğe ulaşınca yeni girişler durmalı.

    no_fill_streak >= limit → "no_fill_burst_stop" (yeni girişler durur), aksi None. Status-return stili
    (daily_loss_halt / max_trades_first_session_halt simetrisi). limit None → getattr(config,
    "NO_FILL_BURST_LIMIT", 3) [conservative fallback; config sabiti AYRI human-owned task].
    no_fill_streak<0 veya limit<=0 → ValueError. Restart-safe DEĞİL (enjekte sayaç); main_loop wiring
    / RiskStateSnapshot şeması bu fonksiyona dahil DEĞİL."""
    if limit is None:
        limit = getattr(config, "NO_FILL_BURST_LIMIT", 3)
    if limit <= 0:
        raise ValueError(f"limit pozitif olmalı: {limit}")
    if no_fill_streak < 0:
        raise ValueError(f"no_fill_streak negatif olamaz: {no_fill_streak}")
    if no_fill_streak >= limit:
        return "no_fill_burst_stop"
    return None


def fill_to_submit_halt(opened, submitted, *, min_submissions=None, floor_ratio=None) -> str | None:
    """E11d — fill-to-submit oran breaker. SAF + offline (DB/API/canlı state YOK; opened/submitted enjekte).
    Çok submit'e karşı az gerçek açılış (düşük oran = toksik likidite / sürekli FAK kill) → yeni girişler
    durmalı. Status-return stili (no_fill_burst_halt / max_trades_first_session_halt simetrisi).

    Düşük-örneklem koruması: submitted < min_submissions → None (oran düşük olsa bile; gürültü).
    submitted >= min_submissions ve opened/submitted < floor_ratio → "fill_to_submit_stop"; oran == floor
    veya > floor → None (sınır izinli). min_submissions None → getattr(config,
    "FILL_TO_SUBMIT_MIN_SUBMISSIONS", 6); floor_ratio None → getattr(config, "FILL_TO_SUBMIT_FLOOR_RATIO",
    0.25) [conservative fallback; config sabitleri AYRI human-owned task]. opened<0 / submitted<0 /
    opened>submitted / min_submissions<=0 / floor_ratio<=0 / floor_ratio>1 → ValueError. Restart-safe DEĞİL
    (enjekte sayaç); main_loop wiring / RiskStateSnapshot şeması bu fonksiyona dahil DEĞİL."""
    if min_submissions is None:
        min_submissions = getattr(config, "FILL_TO_SUBMIT_MIN_SUBMISSIONS", 6)
    if floor_ratio is None:
        floor_ratio = getattr(config, "FILL_TO_SUBMIT_FLOOR_RATIO", 0.25)
    if min_submissions <= 0:
        raise ValueError(f"min_submissions pozitif olmalı: {min_submissions}")
    if floor_ratio <= 0 or floor_ratio > 1:
        raise ValueError(f"floor_ratio (0, 1] aralığında olmalı: {floor_ratio}")
    if opened < 0:
        raise ValueError(f"opened negatif olamaz: {opened}")
    if submitted < 0:
        raise ValueError(f"submitted negatif olamaz: {submitted}")
    if opened > submitted:
        raise ValueError(f"opened ({opened}) submitted'ı ({submitted}) aşamaz")
    if submitted < min_submissions:
        return None
    if opened / submitted < floor_ratio:
        return "fill_to_submit_stop"
    return None


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
