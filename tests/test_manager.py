"""tests/test_manager.py — position/manager.py birim testleri."""
import pytest
from datetime import datetime, timezone, timedelta
from position.manager import check_exit


def _pos(action="YES", entry=0.60, fair=0.75, held_minutes=25):
    return {
        "position_id":    "test-mht",
        "slug":           "btc-5m-test",
        "pm_entry_price": entry,
        "fair_value":     fair,
        "action":         action,
        "opened_at":      (datetime.now(timezone.utc)
                           - timedelta(minutes=held_minutes)).isoformat(),
    }


def test_check_exit_max_hold_time_populates_mae_mfe():
    """max_hold_time kapanışında MAE/MFE kaybolmamalı — bug fix testi."""
    pos = _pos(held_minutes=25)  # MAX_HOLD_MINUTES=20 geçmiş
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.45,
                        time_to_expiry_secs=300)
    assert result == "max_hold_time"
    assert pos.get("mae_px") is not None,  "max_hold_time sonrası mae_px None olmamalı"
    assert pos.get("mfe_px") is not None,  "max_hold_time sonrası mfe_px None olmamalı"
    assert pos["mae_pct"] == pytest.approx((0.45 - 0.60) / 0.60, abs=1e-6)
    assert pos["mfe_px"] == pytest.approx(0.45)


def test_check_exit_max_hold_time_no_exit_within_limit():
    """Henüz MAX_HOLD_MINUTES dolmadıysa max_hold_time döndürmemeli."""
    pos = _pos(held_minutes=5)
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.65,
                        time_to_expiry_secs=300)
    assert result != "max_hold_time"


def test_check_exit_mae_mfe_updated_on_every_call():
    """Normal hold sırasında da MAE/MFE her çağrıda güncellenmeli."""
    pos = _pos(held_minutes=2, entry=0.60, fair=0.75)
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.62,
                        time_to_expiry_secs=500)
    assert result is None
    assert pos.get("mae_px") is not None
    assert pos.get("mfe_px") == pytest.approx(0.62)


def test_check_exit_stop_loss_hit_still_has_mae_mfe():
    """stop_loss_hit kapanışında MAE/MFE mevcut (regresyon koruması)."""
    pos = _pos(held_minutes=5, entry=0.60, fair=0.75)
    # MIN_HOLD_SECS=30 geçmiş, büyük düşüş
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.30,
                        time_to_expiry_secs=300)
    assert result == "stop_loss_hit"
    assert pos.get("mae_px") is not None
    assert pos["mae_pct"] == pytest.approx((0.30 - 0.60) / 0.60, abs=1e-6)


def test_check_exit_no_action_tracks_mfe_correctly():
    """NO pozisyonda no_token_id yoksa complement fallback çalışmalı."""
    pos = _pos(action="NO", entry=0.40, fair=0.25, held_minutes=2)
    # no_token_id yok → complement: 1-0.70=0.30
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.70,
                        time_to_expiry_secs=500)
    assert pos.get("mae_px") == pytest.approx(0.30)  # 1 - 0.70


# ── Task 1: STOP_LOSS_MAX=0.25, MIN_HOLD_SECS=15 ─────────────────────────────

def test_stop_loss_max_constant_is_025():
    """Kalibrasyon: STOP_LOSS_MAX=0.25 olmalı (eski 0.30 → veri destekli)."""
    from position.manager import STOP_LOSS_MAX
    assert STOP_LOSS_MAX == pytest.approx(0.25), f"STOP_LOSS_MAX={STOP_LOSS_MAX}, 0.25 bekleniyor"


def test_min_hold_secs_constant_is_15():
    """Kalibrasyon: MIN_HOLD_SECS=15 olmalı (eski 30 → daha çevik)."""
    from position.manager import MIN_HOLD_SECS
    assert MIN_HOLD_SECS == 15, f"MIN_HOLD_SECS={MIN_HOLD_SECS}, 15 bekleniyor"


def test_stop_triggers_at_025_threshold():
    """Yeni eşik: entry=0.60, 16s hold, price=0.450 → stop_loss_hit."""
    pos = _pos(action="YES", entry=0.60, fair=0.75)
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=16)).isoformat()
    # 16s hold, 600s to expiry → dynamic_stop ≈ 0.247 → stop_at=0.60*(1-0.247)=0.452
    # price=0.450 < 0.452 → STOP
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.450, time_to_expiry_secs=600)
    assert result == "stop_loss_hit"


def test_stop_does_not_trigger_within_15s():
    """MIN_HOLD_SECS=15: 14s içinde büyük çöküşte bile stop tetiklenmemeli."""
    pos = _pos(action="YES", entry=0.60, fair=0.75)
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=14)).isoformat()
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.10, time_to_expiry_secs=300)
    assert result is None, "14s < MIN_HOLD_SECS=15 → stop_loss çalışmamalı"


def test_stop_can_trigger_after_15s():
    """MIN_HOLD_SECS=15: 16s geçtikten sonra büyük düşüşte stop_loss_hit döner."""
    pos = _pos(action="YES", entry=0.60, fair=0.75)
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=16)).isoformat()
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.10, time_to_expiry_secs=300)
    assert result == "stop_loss_hit", "16s ≥ MIN_HOLD_SECS=15 → stop_loss_hit bekleniyor"


# ── Task 3: NO exact MAE ─────────────────────────────────────────────────────

def test_no_position_uses_no_token_bid_for_mae():
    """NO pozisyon: no_token_id WS bid varsa MAE exact'tir (complement değil)."""
    from unittest.mock import patch
    pos = _pos(action="NO", entry=0.45, fair=0.25)
    pos["no_token_id"] = "no-tok-abc"
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()

    with patch("position.manager._ws.get_bid", return_value=0.38) as mock_bid:
        check_exit(pos, hl_price=60000, pm_yes_price=0.65, time_to_expiry_secs=300)
        mock_bid.assert_called_with("no-tok-abc")
        assert pos["mae_data_quality"] == "exact", (
            f"WS bid mevcut → exact bekleniyor, '{pos['mae_data_quality']}' geldi"
        )
        assert pos.get("mae_px") == pytest.approx(0.38), (
            f"mae_px complement değil WS bid olmalı: 0.38 bekleniyor, {pos.get('mae_px')} geldi"
        )


def test_no_position_falls_back_to_complement_when_no_ws_bid():
    """WS no_token_id bid yoksa complement kullanılmalı ve quality='estimated'."""
    from unittest.mock import patch
    pos = _pos(action="NO", entry=0.45, fair=0.25)
    pos["no_token_id"] = "no-tok-xyz"
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()

    with patch("position.manager._ws.get_bid", return_value=None):
        check_exit(pos, hl_price=60000, pm_yes_price=0.58, time_to_expiry_secs=300)
        assert pos["mae_data_quality"] == "estimated"
        assert pos.get("mae_px") == pytest.approx(1 - 0.58)


def test_no_position_without_no_token_id_uses_complement():
    """no_token_id pozisyonda yoksa complement fallback, quality='estimated'."""
    pos = _pos(action="NO", entry=0.45, fair=0.25)
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    check_exit(pos, hl_price=60000, pm_yes_price=0.55, time_to_expiry_secs=300)
    assert pos["mae_data_quality"] == "estimated"
    assert pos.get("mae_px") == pytest.approx(1 - 0.55)


def test_no_stop_loss_uses_exact_no_bid():
    """NO stop-loss kararı da exact WS no_bid kullanmalı (complement değil)."""
    from unittest.mock import patch
    pos = _pos(action="NO", entry=0.45, fair=0.25)
    pos["no_token_id"] = "no-tok-stop"
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()

    # no_bid=0.29 → (0.29-0.45)/0.45 = -35.6% → -%25 eşiğini aştı → stop_loss_hit
    with patch("position.manager._ws.get_bid", return_value=0.29):
        result = check_exit(pos, hl_price=60000, pm_yes_price=0.72, time_to_expiry_secs=300)
        assert result == "stop_loss_hit", (
            f"no_bid=0.29 ile -%35 kayıp → stop_loss_hit bekleniyor, '{result}' geldi"
        )


# ── 3-tier NO MAE: WS bid → CLOB fallback → complement ───────────────────────

def test_no_position_uses_clob_fallback_when_no_ws_bid():
    """NO: WS bid miss → pos['_no_clob_bid'] CLOB fallback kullanılır, quality='clob_fallback'."""
    from unittest.mock import patch
    pos = _pos(action="NO", entry=0.45, fair=0.25)
    pos["no_token_id"] = "no-tok-clob"
    pos["_no_clob_bid"] = 0.35  # monitor tarafından pre-fetch edilmiş
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()

    with patch("position.manager._ws.get_bid", return_value=None):
        check_exit(pos, hl_price=60000, pm_yes_price=0.68, time_to_expiry_secs=300)
        assert pos["mae_data_quality"] == "clob_fallback", (
            f"CLOB fallback → 'clob_fallback' bekleniyor, '{pos['mae_data_quality']}' geldi"
        )
        assert pos.get("mae_px") == pytest.approx(0.35), (
            f"mae_px CLOB bid=0.35 olmalı, {pos.get('mae_px')} geldi"
        )


def test_no_stop_uses_clob_bid_when_ws_miss():
    """NO stop kararı: WS miss, _no_clob_bid var → CLOB fiyatıyla stop tetiklenir."""
    from unittest.mock import patch
    pos = _pos(action="NO", entry=0.45, fair=0.25)
    pos["no_token_id"] = "no-tok-clob-stop"
    pos["_no_clob_bid"] = 0.29  # -35.6% kayıp → -%25 eşiğini aşar → stop
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()

    with patch("position.manager._ws.get_bid", return_value=None):
        result = check_exit(pos, hl_price=60000, pm_yes_price=0.72, time_to_expiry_secs=300)
        assert result == "stop_loss_hit", (
            f"CLOB no_bid=0.29 → stop_loss_hit bekleniyor, '{result}' geldi"
        )
        assert pos["mae_data_quality"] == "clob_fallback"


def test_no_complement_is_last_resort_quality_estimated():
    """NO: WS miss + _no_clob_bid yok → complement, quality='estimated'."""
    from unittest.mock import patch
    pos = _pos(action="NO", entry=0.45, fair=0.25)
    pos["no_token_id"] = "no-tok-comp"
    # _no_clob_bid intentionally absent
    pos["opened_at"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()

    with patch("position.manager._ws.get_bid", return_value=None):
        check_exit(pos, hl_price=60000, pm_yes_price=0.68, time_to_expiry_secs=300)
        assert pos["mae_data_quality"] == "estimated"
        assert pos.get("mae_px") == pytest.approx(1 - 0.68)
