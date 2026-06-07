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
    """NO pozisyonda current_val=1-pm_yes_price doğru hesaplanmalı."""
    pos = _pos(action="NO", entry=0.40, fair=0.25, held_minutes=2)
    # pm_yes_price=0.70 → current_val=1-0.70=0.30 (bizim NO değerimiz)
    result = check_exit(pos, hl_price=60000, pm_yes_price=0.70,
                        time_to_expiry_secs=500)
    assert pos.get("mae_px") == pytest.approx(0.30)  # 1 - 0.70
