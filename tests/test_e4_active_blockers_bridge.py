"""tests/test_e4_active_blockers_bridge.py — E4 active_blockers bridge (TDD).

Mevcut risk/breaker sinyallerini (daily_loss_halt → "daily_loss_stop"; circuit_breaker → "soft_stop"/
"hard_stop"; kill-switch; manual review) reducer'ın anladığı `active_blockers` listesine çeviren SAF
köprü. YALNIZ caller-verilen sinyal değerlerini dönüştürür: config OKUMAZ, global state YOK,
circuit_breaker fonksiyonlarını ÇAĞIRMAZ, persist YOK.

Kanonik sıra (yalnız aktif olanlar): ["kill_switch","manual_review","halted","daily_loss","cooldown"].
unknown daily_loss_status / circuit_breaker_status → ValueError; pasif: None/""/"ok"/"continue"/"no_stop".

İlk RED: monitor.risk_state.build_active_blockers YOK → ImportError. Canlı API/DB/clock yok.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_no_signals_returns_empty():
    from monitor.risk_state import build_active_blockers
    assert build_active_blockers() == []
    # Pasif statüler de boş döner
    assert build_active_blockers(daily_loss_status="ok", circuit_breaker_status="no_stop") == []
    assert build_active_blockers(daily_loss_status="", circuit_breaker_status="continue") == []
    assert build_active_blockers(daily_loss_status=None, circuit_breaker_status=None) == []


def test_single_signals_map_canonically():
    from monitor.risk_state import build_active_blockers
    assert build_active_blockers(daily_loss_status="daily_loss_stop") == ["daily_loss"]
    assert build_active_blockers(circuit_breaker_status="soft_stop") == ["cooldown"]
    assert build_active_blockers(circuit_breaker_status="hard_stop") == ["halted"]
    assert build_active_blockers(kill_switch_active=True) == ["kill_switch"]
    assert build_active_blockers(manual_review_required=True) == ["manual_review"]


def test_combined_signals_deterministic_order():
    from monitor.risk_state import build_active_blockers
    assert build_active_blockers(
        daily_loss_status="daily_loss_stop", circuit_breaker_status="soft_stop",
        kill_switch_active=True) == ["kill_switch", "daily_loss", "cooldown"]
    assert build_active_blockers(
        manual_review_required=True, circuit_breaker_status="hard_stop") == ["manual_review", "halted"]


def test_max_active_canonical_order_no_duplicates():
    """circuit_breaker_status tek değerli → cooldown VE halted aynı anda olamaz; bu yüzden literal
    5-öğeli 'all active' ULAŞILAMAZ. Kanonik sıra iki ulaşılabilir maksimumla pinlenir:
    - hard_stop dalı (halted): ["kill_switch","manual_review","halted","daily_loss"]
    - soft_stop dalı (cooldown): ["kill_switch","manual_review","daily_loss","cooldown"]
    İkisi birlikte tam kanonik sırayı (kill_switch<manual_review<halted<daily_loss<cooldown) sabitler."""
    from monitor.risk_state import build_active_blockers
    assert build_active_blockers(
        daily_loss_status="daily_loss_stop", circuit_breaker_status="hard_stop",
        kill_switch_active=True, manual_review_required=True) == \
        ["kill_switch", "manual_review", "halted", "daily_loss"]
    assert build_active_blockers(
        daily_loss_status="daily_loss_stop", circuit_breaker_status="soft_stop",
        kill_switch_active=True, manual_review_required=True) == \
        ["kill_switch", "manual_review", "daily_loss", "cooldown"]


def test_unknown_daily_loss_status_rejected():
    from monitor.risk_state import build_active_blockers
    with pytest.raises(ValueError):
        build_active_blockers(daily_loss_status="weird_status")


def test_unknown_circuit_breaker_status_rejected():
    from monitor.risk_state import build_active_blockers
    with pytest.raises(ValueError):
        build_active_blockers(circuit_breaker_status="weird_status")
