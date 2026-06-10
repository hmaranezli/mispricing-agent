"""tests/test_reconciliation.py — Faz 2c-1: reconciliation karar fonksiyonu (saf).

get_trades adaylarından intent akıbeti: directional (BUY exec≤limit / SELL exec≥limit) +
aggregate (wallet+token+side+window grupla, weighted-avg) + dedup (matched_trade_ids
double-count önle) + ambiguous→RECOVERY_REQUIRED. Statik ±tick tolerance YASAK.
get_trades şeması ham dict (canlı sample = live-blocker; burada fixture-contract).
"""
import sys
import os
from decimal import Decimal
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _intent(side="TAKER_BUY", price="0.55", size="100", token="tokA", ts=1000, matched=None):
    return {"order_intent_id": "i1", "side": side, "intended_price": Decimal(price),
            "intended_size": Decimal(size), "market_token_id": token,
            "intent_timestamp": ts, "matched_trade_ids": matched or []}


def _trade(tid, asset="tokA", side="BUY", size="100", price="0.54", t=1005):
    return {"trade_id": tid, "asset_id": asset, "side": side,
            "size": str(size), "price": str(price), "match_time": t}


# 1. Tek tam-fill, directional-pass → FILLED
def test_full_fill_directional_pass():
    from execution.reconciliation import reconcile_intent
    r = reconcile_intent(_intent(), [_trade("t1", price="0.54", size="100")],
                         now_ts=1010, window_s=60)
    assert r["state"] == "FILLED"
    assert r["executed_size"] == Decimal("100")
    assert r["matched_trade_ids"] == ["t1"]


# 2. İki kısmi trade toplam=intended → FILLED (aggregate weighted-avg)
def test_aggregate_two_partials_full():
    from execution.reconciliation import reconcile_intent
    trades = [_trade("t1", size="60", price="0.54"), _trade("t2", size="40", price="0.55")]
    r = reconcile_intent(_intent(), trades, now_ts=1010, window_s=60)
    assert r["state"] == "FILLED" and r["executed_size"] == Decimal("100")
    assert set(r["matched_trade_ids"]) == {"t1", "t2"}
    # weighted avg = (60*0.54 + 40*0.55)/100 = 0.544
    assert r["avg_price"] == Decimal("0.544")


# 3. Kısmi toplam < intended → PARTIAL_FILLED
def test_partial_fill():
    from execution.reconciliation import reconcile_intent
    r = reconcile_intent(_intent(), [_trade("t1", size="30")], now_ts=1010, window_s=60)
    assert r["state"] == "PARTIAL_FILLED" and r["executed_size"] == Decimal("30")


# 4. Directional-fail (BUY exec_price > limit) → aday DEĞİL, sayılmaz
def test_directional_fail_buy_excluded():
    from execution.reconciliation import reconcile_intent
    # TAKER_BUY limit 0.55, trade price 0.58 > limit → bizim trade'imiz değil
    r = reconcile_intent(_intent(side="TAKER_BUY", price="0.55"),
                         [_trade("t1", price="0.58", size="100")], now_ts=1010, window_s=60)
    assert r["executed_size"] == Decimal("0")
    assert r["state"] in ("SUBMITTED_UNKNOWN", "CANCELLED")


def test_directional_sell_pass_and_fail():
    from execution.reconciliation import reconcile_intent
    # TAKER_SELL limit 0.50: exec≥0.50 geçer, <0.50 elenir
    trades = [_trade("t1", side="SELL", price="0.52", size="50"),   # pass
              _trade("t2", side="SELL", price="0.48", size="50")]   # fail (bizim değil)
    r = reconcile_intent(_intent(side="TAKER_SELL", price="0.50", size="100"),
                         trades, now_ts=1010, window_s=60)
    assert r["executed_size"] == Decimal("50") and r["matched_trade_ids"] == ["t1"]


# 5. Dedup: önceden matched trade_id tekrar → DOUBLE-COUNT YOK
def test_dedup_already_matched():
    from execution.reconciliation import reconcile_intent
    r = reconcile_intent(_intent(matched=["t1"]),
                         [_trade("t1", size="100"), _trade("t2", size="0.0001")],
                         now_ts=1010, window_s=60)
    # t1 zaten matched → sayılmaz; t2 ~0 → executed yok
    assert "t1" not in [tid for tid in r["matched_trade_ids"] if tid == "t1" and r["executed_size"] >= 100]


# 6. Ambiguous: executed_total > intended (fazla fill) → RECOVERY_REQUIRED
def test_ambiguous_overfill_recovery():
    from execution.reconciliation import reconcile_intent
    # intended 100, adaylar toplam 150 (fazla) → bizim olmayan trade karışmış → RECOVERY
    trades = [_trade("t1", size="100"), _trade("t2", size="50")]
    r = reconcile_intent(_intent(size="100"), trades, now_ts=1010, window_s=60)
    assert r["state"] == "RECOVERY_REQUIRED"
    assert r["emergency_pause"] is True


# 7. Window dışı trade → sayılmaz
def test_outside_time_window_excluded():
    from execution.reconciliation import reconcile_intent
    # intent ts=1000, window 60 → trade t=1100 (>60s sonra) elenir
    r = reconcile_intent(_intent(ts=1000), [_trade("t1", size="100", t=1100)],
                         now_ts=1110, window_s=60)
    assert r["executed_size"] == Decimal("0")


# 8. Zero candidate + window doldu → CANCELLED; window devam → SUBMITTED_UNKNOWN
def test_zero_candidate_window_logic():
    from execution.reconciliation import reconcile_intent
    # window doldu (now - ts > window), aday yok → CANCELLED
    r_done = reconcile_intent(_intent(ts=1000), [], now_ts=1100, window_s=60)
    assert r_done["state"] == "CANCELLED"
    # window devam, aday yok → henüz bekle (SUBMITTED_UNKNOWN)
    r_wait = reconcile_intent(_intent(ts=1000), [], now_ts=1030, window_s=60)
    assert r_wait["state"] == "SUBMITTED_UNKNOWN"
