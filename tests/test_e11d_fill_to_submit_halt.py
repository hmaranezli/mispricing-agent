"""tests/test_e11d_fill_to_submit_halt.py — E11d fill-to-submit pure predicate (TDD).

Execution-quality breaker #2: çok sayıda submit'e karşı az gerçek açılış (düşük fill-to-submit oranı)
= toksik likidite / sürekli FAK kill → yeni girişler durmalı. E11d YALNIZ saf predicate'i pin'ler —
opened/submitted ENJEKTE; DB COUNT/API/canlı state/main_loop/entry-gate YOK (E11a `no_fill_burst_halt`
/ `max_trades_first_session_halt` / `daily_loss_halt` simetrisi).

Düşük-örneklem koruması: submitted < min_submissions iken oran düşük olsa bile TRIP ETMEZ (gürültü).

Hedef eksik seam:
    from monitor.circuit_breaker import fill_to_submit_halt

İlk RED: `fill_to_submit_halt` yok → ImportError/AttributeError (eksik üretim seam'i; syntax/unrelated
import hatası DEĞİL). config.FILL_TO_SUBMIT_* EKLENMEZ (human-owned, ayrı config-only slice).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from monitor.circuit_breaker import fill_to_submit_halt


# ── Düşük-örneklem koruması ──────────────────────────────────────────────────
def test_below_min_submissions_returns_none_even_if_ratio_low():
    """submitted < min_submissions → oran düşük olsa bile None (gürültü koruması)."""
    assert fill_to_submit_halt(0, 5, min_submissions=6, floor_ratio=0.25) is None


def test_below_min_submissions_zero_submitted_returns_none():
    """submitted 0 (< min) → None (sıfıra bölme yok, henüz veri yok)."""
    assert fill_to_submit_halt(0, 0, min_submissions=6, floor_ratio=0.25) is None


# ── Oran semantiği (submitted >= min_submissions) ────────────────────────────
def test_at_min_ratio_below_floor_returns_stop():
    """submitted == min ve oran < floor → "fill_to_submit_stop" (1/6 ≈ 0.167 < 0.25)."""
    assert fill_to_submit_halt(1, 6, min_submissions=6, floor_ratio=0.25) == "fill_to_submit_stop"


def test_ratio_equal_floor_returns_none():
    """oran == floor → None (sınır izinli; 2/8 = 0.25)."""
    assert fill_to_submit_halt(2, 8, min_submissions=6, floor_ratio=0.25) is None


def test_ratio_above_floor_returns_none():
    """oran > floor → None (4/8 = 0.5 > 0.25)."""
    assert fill_to_submit_halt(4, 8, min_submissions=6, floor_ratio=0.25) is None


def test_zero_opened_at_min_submissions_returns_stop():
    """opened 0, submitted == min → oran 0 < floor → stop."""
    assert fill_to_submit_halt(0, 6, min_submissions=6, floor_ratio=0.25) == "fill_to_submit_stop"


# ── Config okuma / fallback ──────────────────────────────────────────────────
def test_explicit_args_override_config(monkeypatch):
    """explicit min_submissions/floor_ratio, config'ten bağımsız uygulanır."""
    monkeypatch.setattr(config, "FILL_TO_SUBMIT_MIN_SUBMISSIONS", 99, raising=False)
    monkeypatch.setattr(config, "FILL_TO_SUBMIT_FLOOR_RATIO", 0.9, raising=False)
    assert fill_to_submit_halt(1, 6, min_submissions=6, floor_ratio=0.25) == "fill_to_submit_stop"


def test_none_reads_config_when_present(monkeypatch):
    """min_submissions/floor_ratio None → config okunur (monkeypatch ile)."""
    monkeypatch.setattr(config, "FILL_TO_SUBMIT_MIN_SUBMISSIONS", 4, raising=False)
    monkeypatch.setattr(config, "FILL_TO_SUBMIT_FLOOR_RATIO", 0.5, raising=False)
    assert fill_to_submit_halt(1, 3) is None                       # submitted 3 < min 4 → None
    assert fill_to_submit_halt(1, 4) == "fill_to_submit_stop"      # 1/4 = 0.25 < 0.5 → stop
    assert fill_to_submit_halt(2, 4) is None                       # 2/4 = 0.5 == floor → None


def test_none_falls_back_when_config_missing(monkeypatch):
    """config yok → min_submissions fallback 6, floor_ratio fallback 0.25."""
    monkeypatch.delattr(config, "FILL_TO_SUBMIT_MIN_SUBMISSIONS", raising=False)
    monkeypatch.delattr(config, "FILL_TO_SUBMIT_FLOOR_RATIO", raising=False)
    assert fill_to_submit_halt(0, 5) is None                       # submitted 5 < fallback min 6 → None
    assert fill_to_submit_halt(1, 6) == "fill_to_submit_stop"      # 1/6 ≈ 0.167 < 0.25 → stop
    assert fill_to_submit_halt(2, 8) is None                       # 2/8 = 0.25 == 0.25 floor → None


# ── ValueError kuralları ─────────────────────────────────────────────────────
def test_negative_opened_raises():
    with pytest.raises(ValueError):
        fill_to_submit_halt(-1, 6, min_submissions=6, floor_ratio=0.25)


def test_negative_submitted_raises():
    with pytest.raises(ValueError):
        fill_to_submit_halt(0, -1, min_submissions=6, floor_ratio=0.25)


def test_opened_greater_than_submitted_raises():
    with pytest.raises(ValueError):
        fill_to_submit_halt(7, 6, min_submissions=6, floor_ratio=0.25)


def test_non_positive_min_submissions_raises():
    with pytest.raises(ValueError):
        fill_to_submit_halt(0, 0, min_submissions=0, floor_ratio=0.25)


def test_floor_ratio_out_of_range_raises():
    with pytest.raises(ValueError):
        fill_to_submit_halt(0, 6, min_submissions=6, floor_ratio=0.0)
    with pytest.raises(ValueError):
        fill_to_submit_halt(0, 6, min_submissions=6, floor_ratio=1.5)
