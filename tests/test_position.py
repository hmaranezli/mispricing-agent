"""tests/test_position.py — position/manager birim testleri. API çağrısı yok."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from position.manager import check_exit, close_position, _log, _dynamic_stop


# ── Fixture'lar ──────────────────────────────────────────────────────────────

def _position(action: str = "YES", held_minutes: int = 5) -> dict:
    """Geçerli bir açık pozisyon kaydı döndürür."""
    opened_at = (datetime.now(timezone.utc) - timedelta(minutes=held_minutes)).isoformat()
    entry = 0.35 if action == "YES" else 0.33
    fair  = 0.55 if action == "YES" else 0.35
    return {
        "position_id":             "test-pos-1234",
        "asset":                   "BTC",
        "action":                  action,
        "slug":                    "btc-up-15min-test",
        "pm_entry_price":          entry,
        "fair_value":              fair,
        "ref_price":               95000.0,
        "position_usd":            25.0,
        "kelly_f":                 0.15,
        "confidence_score":        82.5,
        "seconds_remaining":       900,
        "opened_at":               opened_at,
        "status":                  "open",
        "requires_human_approval": False,
        "dry_run":                 True,
        "exit_reason":             None,
        "closed_at":               None,
    }


# ── Task 1: _log() + close_position() ────────────────────────────────────────

def test_position_log_writes_jsonl(tmp_path):
    """_log() layer='position' ile geçerli JSONL satırı yazar."""
    log_file = tmp_path / "test.jsonl"
    _log("test_event", {"key": "val"}, log_file=log_file)
    record = json.loads(log_file.read_text().strip())
    assert record["layer"] == "position"
    assert record["event"] == "test_event"
    assert record["key"] == "val"
    assert "ts" in record


def test_close_position_returns_updated_record(tmp_path):
    """close_position status='closed', exit_reason, pm_exit_price, closed_at set eder."""
    pos = _position()
    closed = close_position(pos, "max_hold_time", pm_exit_price=0.52,
                            log_file=tmp_path / "log.jsonl")
    assert closed["status"] == "closed"
    assert closed["exit_reason"] == "max_hold_time"
    assert closed["pm_exit_price"] == 0.52
    dt = datetime.fromisoformat(closed["closed_at"])
    assert dt.tzinfo is not None


def test_close_position_logs_jsonl(tmp_path):
    """close_position JSONL'a position_closed yazar, position_id içerir."""
    pos = _position()
    log_file = tmp_path / "log.jsonl"
    close_position(pos, "thesis_invalidated", log_file=log_file)
    record = json.loads(log_file.read_text().strip())
    assert record["event"] == "position_closed"
    assert record["exit_reason"] == "thesis_invalidated"
    assert record["position_id"] == pos["position_id"]


# ── Task 2: check_exit — zaman + expiry ──────────────────────────────────────

def test_check_exit_near_expiry_returns_none():
    """time_to_expiry_secs < 90, fiyat OK → None (profit_target/max_hold engellenir)."""
    pos = _position(held_minutes=15)
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.40,
                        time_to_expiry_secs=80)
    assert result is None


def test_check_exit_near_expiry_still_fires_stop_loss():
    """Son 90s'de bile stop_loss çalışmalı — NEAR_EXPIRY tam kayıpları engellemez.

    8dk tutulmuş (480s), 50s kaldı → dinamik stop ~%13.7 → eşik=0.35×0.863=0.302.
    pm=0.20 < 0.302 → stop_loss_hit bekleniyor (tighter near-expiry stop, daha erken koruma).
    """
    pos = _position(action="YES", held_minutes=8)
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.20,
                        time_to_expiry_secs=50)
    assert result == "stop_loss_hit", (
        f"Near-expiry'de felaket zararı durdurulmalı, got: {result}"
    )


def test_check_exit_max_hold_time():
    """MAX_HOLD_MINUTES (20) geçmişse → 'max_hold_time'."""
    pos = _position(held_minutes=21)
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.40,
                        time_to_expiry_secs=900)
    assert result == "max_hold_time"


def test_check_exit_holds_when_no_condition_met():
    """Hiçbir koşul tetiklenmezse → None (tut)."""
    # flat market: fair_yes(95000,95000,900,'BTC')=0.50 > pm=0.38 → thesis holds
    # captured edge: (0.38-0.35)/0.20 = 0.15 < 0.85 → profit target yok
    pos = _position(action="YES", held_minutes=5)
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.38,
                        time_to_expiry_secs=900)
    assert result is None


# ── Task 3: check_exit — kâr hedefi (2-döngü onay + slippage eşiği) ───────────

def test_check_exit_profit_needs_two_cycles_yes():
    """YES: büyük kâr tek döngüde değil, 2 ardışık döngüde + 3s geçince onaylanınca çıkar.

    entry=0.35, fair=0.55, edge=0.20; pm=0.53 → captured=0.18 (>=0.10), fraction=0.90 (>=0.85).
    Tek snapshot spike'ı yanlış çıkış yaptırmasın diye 2 döngü + MIN_PROFIT_CONFIRM_SECS gerek.
    """
    pos = _position(action="YES", held_minutes=5)
    first = check_exit(pos, hl_price=95500, pm_yes_price=0.53, time_to_expiry_secs=900)
    assert first is None, "İlk döngü tek başına çıkış yaptırmamalı"
    # Zaman kapısını aşmak için first_ts'i 4s önceye al
    pos["_profit_confirm_first_ts"] = (
        datetime.now(timezone.utc) - timedelta(seconds=4)
    ).isoformat()
    second = check_exit(pos, hl_price=95500, pm_yes_price=0.53, time_to_expiry_secs=900)
    assert second == "profit_target_hit"


def test_check_exit_profit_needs_two_cycles_no():
    """NO: büyük kâr 2 ardışık döngüde + 3s geçince onaylanınca çıkar.

    entry=0.33, fair_NO=0.65, edge=0.32; pm_yes=0.38 → 1-pm=0.62, captured=0.29, fraction=0.906.
    """
    pos = _position(action="NO", held_minutes=5)
    first = check_exit(pos, hl_price=94800, pm_yes_price=0.38, time_to_expiry_secs=900)
    assert first is None
    # Zaman kapısını aşmak için first_ts'i 4s önceye al
    pos["_profit_confirm_first_ts"] = (
        datetime.now(timezone.utc) - timedelta(seconds=4)
    ).isoformat()
    second = check_exit(pos, hl_price=94800, pm_yes_price=0.38, time_to_expiry_secs=900)
    assert second == "profit_target_hit"


def test_check_exit_profit_resets_on_dip():
    """Kâr sinyali ardışık değilse sayaç sıfırlanır → tek seferlik spike çıkış yapmaz."""
    pos = _position(action="YES", held_minutes=5)
    check_exit(pos, hl_price=95500, pm_yes_price=0.53, time_to_expiry_secs=900)  # count=1
    mid = check_exit(pos, hl_price=95000, pm_yes_price=0.38, time_to_expiry_secs=900)  # reset
    assert mid is None
    again = check_exit(pos, hl_price=95500, pm_yes_price=0.53, time_to_expiry_secs=900)  # count=1
    assert again is None, "Sayaç sıfırlandı, tek döngü yetmez"


def test_check_exit_small_profit_holds_to_resolution():
    """Küçük kazanç (captured < PROFIT_LOCK_MIN) → erken çıkma, resolve'a kadar tut.

    entry=0.35, fair=0.42 (küçük edge=0.07), pm=0.41 → captured=0.06 < 0.10.
    fraction=(0.41-0.35)/0.07=0.857>=0.85 olsa bile mutlak kazanç slippage'i hak etmiyor → tut.
    """
    pos = _position(action="YES", held_minutes=5)
    pos["fair_value"] = 0.42
    r1 = check_exit(pos, hl_price=95300, pm_yes_price=0.41, time_to_expiry_secs=900)
    r2 = check_exit(pos, hl_price=95300, pm_yes_price=0.41, time_to_expiry_secs=900)
    assert r1 is None and r2 is None, "Küçük kazançta erken çıkış olmamalı (slippage yer)"


def test_check_exit_thesis_reversal_now_holds():
    """thesis_invalidated KALDIRILDI: HL ters dönse bile resolve'a kadar tut.

    Eski davranış 'thesis_invalidated' döndürürdü (–$5.97 kanama). Artık None — para resolve'dan geliyor.
    """
    pos = _position(action="YES", held_minutes=5)
    result = check_exit(pos, hl_price=94800, pm_yes_price=0.34, time_to_expiry_secs=900)
    assert result is None, "thesis artık çıkış tetiklemez, resolve'a kadar tutulur"


def test_check_exit_stop_loss_after_min_hold():
    """MIN_HOLD sonrası gerçek PM zararı dinamik stop eşiğini geçince → stop_loss_hit.
    5dk tutulmuş, 900s kaldı → dinamik stop ~%25.5 → eşik=0.35×0.745=0.2608, pm=0.25<0.2608.
    """
    pos = _position(action="YES", held_minutes=5)  # 5dk > 30s
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.25, time_to_expiry_secs=900)
    assert result == "stop_loss_hit"


def test_check_exit_no_stop_loss_before_min_hold():
    """İlk 30s içinde stop_loss çalışmaz — anlık ters dönüş gürültüsü filtresi."""
    pos = _position(action="YES", held_minutes=0)  # yeni açıldı, held_seconds ~0
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.27, time_to_expiry_secs=900)
    assert result is None, "30s dolmadan stop tetiklenmemeli"


def test_check_exit_stop_loss_fires_at_45s():
    """45s sonra stop_loss çalışır — MIN_HOLD_SECS=30'dan büyük.

    45s tutulmuş, 900s kaldı → dinamik stop ~%29.1 → eşik=0.35×0.709=0.248.
    pm=0.20 < 0.248 → stop_loss_hit (42.9% kayıp, max stop'tan bile büyük).
    """
    from position.manager import MIN_HOLD_SECS
    assert MIN_HOLD_SECS == 30, f"MIN_HOLD_SECS 30 olmalı, şu an: {MIN_HOLD_SECS}"
    opened_at = (datetime.now(timezone.utc) - timedelta(seconds=45)).isoformat()
    pos = _position(action="YES", held_minutes=0)
    pos["opened_at"] = opened_at
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.20, time_to_expiry_secs=900)
    assert result == "stop_loss_hit", f"45s > 30s MIN_HOLD → stop_loss tetiklenmeli, got: {result}"



# ── Task: Dinamik stop-loss ───────────────────────────────────────────────────

def test_dynamic_stop_wider_early():
    """Erken tutuşta stop geniş — STOP_LOSS_MAX'a yakın (%30)."""
    sl = _dynamic_stop(held_secs=60, time_to_expiry_secs=900)
    assert sl > 0.28, f"Erken stop geniş olmalı (>%28), gelen: {sl:.3f}"


def test_dynamic_stop_tighter_near_expiry():
    """Vadeye yakında stop dar — STOP_LOSS_MIN'e yakın (%12)."""
    sl = _dynamic_stop(held_secs=900, time_to_expiry_secs=60)
    assert sl < 0.18, f"Vadeye yakın stop dar olmalı (<18%), gelen: {sl:.3f}"


def test_dynamic_stop_catches_gamma_trap():
    """Kritik gamma trap testi: 13dk tutulmuş, 2dk kaldı.

    Dinamik stop ~%14.4 → eşik=0.55×(1-0.144)=0.471.
    pm=0.45 (18.2% kayıp) < 0.471 → ÇIKIŞ.
    Static %20 stop: eşik=0.55×0.80=0.44, pm=0.45>0.44 → ÇIKMAZ (gamma trap!).
    """
    held_secs = 780  # 13 dakika
    remaining = 120  # 2 dakika
    opened_at = (datetime.now(timezone.utc) - timedelta(seconds=held_secs)).isoformat()
    pos = _position(action="YES", held_minutes=0)
    pos["opened_at"] = opened_at
    pos["pm_entry_price"] = 0.55
    pos["fair_value"] = 0.75
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.45,
                        time_to_expiry_secs=remaining)
    assert result == "stop_loss_hit", (
        f"Gamma trap: vadeye yakın tighter stop 18.2% kayıpla çıkış yapmalı, got: {result}"
    )


def test_dynamic_stop_no_trigger_early_small_loss():
    """Erken tutuşta küçük kayıp stop tetiklemez — geniş tolerans korunur.

    5dk tutulmuş, 900s kaldı → dinamik stop ~%25.5 → eşik=0.35×0.745=0.2608.
    pm=0.30 (14.3% kayıp) > 0.2608 → tut.
    """
    pos = _position(action="YES", held_minutes=5)
    result = check_exit(pos, hl_price=95000, pm_yes_price=0.30, time_to_expiry_secs=900)
    assert result is None, f"Erken küçük kayıpla çıkış yapılmamalı, got: {result}"


def test_close_position_includes_exit_hl_price():
    """close_position exit_hl_price parametresini closed dict'e eklemeli."""
    from datetime import timedelta
    pos = {
        "position_id": "pos-hl-01", "asset": "BTC", "action": "YES",
        "slug": "btc-up-5m", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0, "seconds_remaining": 300,
        "opened_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        "status": "open", "dry_run": True,
        "exit_reason": None, "closed_at": None, "entry_hl_price": 66500.0,
    }
    closed = close_position(pos, "thesis_invalidated", pm_exit_price=0.72, exit_hl_price=66502.0)
    assert closed["exit_hl_price"] == 66502.0, \
        f"exit_hl_price={closed.get('exit_hl_price')}, beklenen 66502.0"
    assert closed["status"] == "closed"


def test_close_position_exit_hl_price_none_when_not_given():
    """exit_hl_price verilmezse None olmalı — backward compat."""
    from datetime import timedelta
    pos = {
        "position_id": "pos-hl-02", "asset": "BTC", "action": "YES",
        "slug": "btc-up-5m", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.20, "position_usd": 1.25,
        "kelly_f": 0.15, "confidence_score": 82.0, "seconds_remaining": 300,
        "opened_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        "status": "open", "dry_run": True,
        "exit_reason": None, "closed_at": None,
    }
    closed = close_position(pos, "market_expired")
    assert closed.get("exit_hl_price") is None


# ── Task 3: MAE/MFE in-memory tracking + stop trigger snapshot ───────────────

def test_check_exit_tracks_mae_when_price_drops():
    """YES pozisyon: fiyat düşünce mae_px güncellenir."""
    pos = _position("YES", held_minutes=5)
    check_exit(pos, hl_price=95000, pm_yes_price=0.32, time_to_expiry_secs=500)
    assert pos.get("mae_px") == pytest.approx(0.32, abs=1e-6)
    expected_pct = (0.32 - 0.35) / 0.35
    assert pos.get("mae_pct") == pytest.approx(expected_pct, abs=1e-6)
    assert pos.get("mae_ts") is not None


def test_check_exit_tracks_mfe_when_price_rises():
    """YES pozisyon: fiyat yükselince mfe_px güncellenir."""
    pos = _position("YES", held_minutes=5)
    check_exit(pos, hl_price=95000, pm_yes_price=0.50, time_to_expiry_secs=500)
    assert pos.get("mfe_px") == pytest.approx(0.50, abs=1e-6)
    expected_pct = (0.50 - 0.35) / 0.35
    assert pos.get("mfe_pct") == pytest.approx(expected_pct, abs=1e-6)
    assert pos.get("mfe_ts") is not None


def test_check_exit_mae_sticks_to_worst_value():
    """MAE, fiyat toparlansa bile en kötü değerde kalır."""
    pos = _position("YES", held_minutes=5)
    check_exit(pos, hl_price=95000, pm_yes_price=0.28, time_to_expiry_secs=500)
    first_mae = pos["mae_px"]
    check_exit(pos, hl_price=95000, pm_yes_price=0.40, time_to_expiry_secs=490)
    assert pos["mae_px"] == pytest.approx(first_mae, abs=1e-6)


def test_check_exit_mfe_sticks_to_best_value():
    """MFE, fiyat düşse bile en iyi değerde kalır."""
    pos = _position("YES", held_minutes=5)
    check_exit(pos, hl_price=95000, pm_yes_price=0.52, time_to_expiry_secs=500)
    first_mfe = pos["mfe_px"]
    check_exit(pos, hl_price=95000, pm_yes_price=0.38, time_to_expiry_secs=490)
    assert pos["mfe_px"] == pytest.approx(first_mfe, abs=1e-6)


def test_check_exit_no_position_mae_data_quality_estimated():
    """NO pozisyon: mae_data_quality='estimated' (1-YES ask, gerçek NO bid değil)."""
    pos = _position("NO", held_minutes=5)
    check_exit(pos, hl_price=95000, pm_yes_price=0.70, time_to_expiry_secs=500)
    assert pos.get("mae_data_quality") == "estimated"
    assert pos.get("price_source") == "rest"


def test_check_exit_yes_position_mae_data_quality_rest():
    """YES pozisyon: mae_data_quality='rest'."""
    pos = _position("YES", held_minutes=5)
    check_exit(pos, hl_price=95000, pm_yes_price=0.40, time_to_expiry_secs=500)
    assert pos.get("mae_data_quality") == "rest"
    assert pos.get("price_source") == "rest"


def test_check_exit_stop_captures_trigger_snapshot():
    """Stop tetiklenince sl_trigger_px, sl_trigger_pct, first_trigger_ts set edilir."""
    pos = _position("YES", held_minutes=5)
    entry = pos["pm_entry_price"]  # 0.35
    # STOP_LOSS_MAX=0.30: eşik = entry * (1 - 0.30) = 0.245
    crash_price = round(entry * 0.68, 4)  # 0.238 — stop eşiğinin altında
    result = check_exit(pos, hl_price=95000, pm_yes_price=crash_price, time_to_expiry_secs=500)
    assert result == "stop_loss_hit"
    assert pos.get("sl_trigger_px") == pytest.approx(crash_price, abs=1e-6)
    expected_pct = (crash_price - entry) / entry
    assert pos.get("sl_trigger_pct") == pytest.approx(expected_pct, abs=1e-4)
    assert pos.get("first_trigger_ts") is not None


def test_check_exit_stop_trigger_ts_not_overwritten_on_retry():
    """İkinci stop tetiklemesinde first_trigger_ts değişmez (setdefault)."""
    pos = _position("YES", held_minutes=5)
    entry = pos["pm_entry_price"]
    crash_price = round(entry * 0.68, 4)
    # İlk tetikleme
    check_exit(pos, hl_price=95000, pm_yes_price=crash_price, time_to_expiry_secs=500)
    first_ts = pos["first_trigger_ts"]
    # FAK başarısız oldu, döngü tekrar çağırdı
    check_exit(pos, hl_price=95000, pm_yes_price=crash_price - 0.01, time_to_expiry_secs=490)
    assert pos["first_trigger_ts"] == first_ts, "first_trigger_ts FAK retry'da değişmemeli"


# ── Task 2: Profit confirm zaman kapısı ──────────────────────────────────────

def test_profit_confirm_time_gate_blocks_exit_when_elapsed_too_short():
    """Cycles tamamlandı ama <3s geçti → profit_target_hit dönmez."""
    from datetime import datetime, timezone
    pos = _position("YES", held_minutes=5)
    high_price = 0.54

    # İlk çağrı: _profit_confirm_first_ts set edilir
    result1 = check_exit(pos, hl_price=95000, pm_yes_price=high_price, time_to_expiry_secs=500)
    assert result1 is None, "İlk cycle: henüz yeterli sayı yok"
    assert pos.get("_profit_confirm_first_ts") is not None

    # Hemen ikinci çağrı (0ms geçti): cycles=2 tamamlandı ama 3s geçmedi
    result2 = check_exit(pos, hl_price=95000, pm_yes_price=high_price, time_to_expiry_secs=500)
    assert result2 is None, "Cycles=2 ama <3s → zaman kapısı bloklamalı"


def test_profit_confirm_time_gate_allows_exit_when_elapsed_sufficient():
    """Cycles tamamlandı VE >=3s geçti → profit_target_hit döner."""
    from datetime import datetime, timezone, timedelta
    pos = _position("YES", held_minutes=5)
    high_price = 0.54

    # _profit_confirm_first_ts'i 4s önceye set et (simüle edilmiş 3s geçmesi)
    past_ts = (datetime.now(timezone.utc) - timedelta(seconds=4)).isoformat()
    pos["_profit_confirm_first_ts"] = past_ts
    pos["_profit_confirm"] = 1  # bir cycle zaten sayılmış

    # Şimdi ikinci çağrı: cycles=2 VE 4s > 3s → çıkış
    result = check_exit(pos, hl_price=95000, pm_yes_price=high_price, time_to_expiry_secs=500)
    assert result == "profit_target_hit", f"Beklenen profit_target_hit, alınan: {result}"


def test_profit_confirm_reset_clears_first_ts():
    """Profit hedefi kaybolunca _profit_confirm_first_ts da sıfırlanır."""
    pos = _position("YES", held_minutes=5)
    pos["_profit_confirm"] = 1
    pos["_profit_confirm_first_ts"] = "2026-06-07T10:00:00+00:00"

    # Düşük fiyat → profit_ready=False → reset
    check_exit(pos, hl_price=95000, pm_yes_price=0.38, time_to_expiry_secs=500)
    assert pos["_profit_confirm"] == 0
    assert "_profit_confirm_first_ts" not in pos, "_profit_confirm_first_ts silinmeli"
