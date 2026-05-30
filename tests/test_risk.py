"""tests/test_risk.py — Katman 4 Risk birim testleri. Sıfır API çağrısı."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from council.risk import risk, _kelly, KELLY_FRACTION, MIN_POSITION_USD


# ── Test fixture'ları ─────────────────────────────────────────────────────────

def _finding(action="YES", best_ask=0.40, best_bid=0.38):
    return {
        "question": "Will BTC go up?",
        "slug": "btc-up-1h",
        "asset": "BTC",
        "action": action,
        "fair": 0.55,
        "best_ask": best_ask,
        "best_bid": best_bid,
        "edge": 0.15,
        "cur_price": 65000.0,
        "ref_price": 64000.0,
        "seconds_remaining": 900,
    }


def _verification(fresh_fair=0.55, fresh_edge=0.15,
                  fresh_best_ask=0.40, fresh_best_bid=0.38,
                  fresh_seconds=300):
    return {
        "pass": True,
        "reason": "ok",
        "halt": False,
        "fresh_cur_price": 65000.0,
        "fresh_best_ask": fresh_best_ask,
        "fresh_best_bid": fresh_best_bid,
        "fresh_fair": fresh_fair,
        "fresh_edge": fresh_edge,
        "fresh_seconds": fresh_seconds,
        "hl_drift_pct": 0.01,
        "pm_drift": 0.005,
    }


def _redteam(fee_adj_edge=0.12):
    return {
        "pass": True,
        "vetoes": [],
        "warnings": [],
        "fee_adj_edge": fee_adj_edge,
        "taker_fee": 0.02,
        "spread": 0.02,
        "liquidity_usd": 5000.0,
    }


BANKROLL = 1000.0


# ── Task 1: output şeması ─────────────────────────────────────────────────────

def test_result_has_required_fields():
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=0.0)
    assert "pass" in r
    assert "position_usd" in r
    assert "kelly_f" in r
    assert "kelly_fraction_applied" in r
    assert "requires_human_approval" in r
    assert "halt" in r
    assert "reason" in r


# ── Task 2: _kelly() hesabı ───────────────────────────────────────────────────

def test_kelly_yes_calculation():
    # edge=0.12, fresh_ask=0.40 → denom=0.60 → kelly=0.12/0.60=0.20
    k = _kelly("YES", fee_adj_edge=0.12, fresh_ask=0.40, fresh_bid=0.38)
    assert abs(k - 0.20) < 1e-6


def test_kelly_no_calculation():
    # edge=0.10, fresh_bid=0.40 → kelly=0.10/0.40=0.25
    k = _kelly("NO", fee_adj_edge=0.10, fresh_ask=0.60, fresh_bid=0.40)
    assert abs(k - 0.25) < 1e-6


# ── Task 3: günlük kayıp limiti ───────────────────────────────────────────────

def test_halt_on_daily_loss_limit():
    # Tam limit: bankroll × DAILY_LOSS_LIMIT_PCT = 1000 × 0.10 = $100
    loss = BANKROLL * config.DAILY_LOSS_LIMIT_PCT
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=loss)
    assert r["pass"] is False
    assert r["halt"] is True
    assert r["reason"] == "daily_loss_limit_hit"


def test_no_halt_below_limit():
    # %9 kayıp → limit altı
    loss = BANKROLL * (config.DAILY_LOSS_LIMIT_PCT - 0.01)
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=loss)
    assert r["halt"] is False


# ── Task 4: açık pozisyon limiti ─────────────────────────────────────────────

def test_veto_max_open_positions():
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL,
             open_positions=config.MAX_OPEN_POSITIONS,
             daily_loss_usd=0.0)
    assert r["pass"] is False
    assert r["reason"] == "max_open_positions_reached"
    assert r["halt"] is False


def test_pass_below_max_positions():
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL,
             open_positions=config.MAX_OPEN_POSITIONS - 1,
             daily_loss_usd=0.0)
    assert r["halt"] is False
    assert r["reason"] != "max_open_positions_reached"


# ── Task 5: edge geçerlilik ───────────────────────────────────────────────────

def test_veto_edge_below_minimum():
    rt = _redteam(fee_adj_edge=config.MIN_EDGE_PCT - 0.001)
    r = risk(_finding(), _verification(), rt,
             bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=0.0)
    assert r["pass"] is False
    assert r["reason"] == "edge_below_minimum"


# ── Task 6: Kelly hesabı + cap + min pozisyon ─────────────────────────────────

def test_kelly_capped_at_max_trade_pct():
    # edge=0.50, fresh_ask=0.10 → kelly=0.50/0.90=0.556
    # × KELLY_FRACTION(0.25) = 0.139 > MAX_TRADE_PCT(0.05) → cap
    # position = 0.05 × 1000 = $50.00
    r = risk(
        _finding(action="YES", best_ask=0.10),
        _verification(fresh_best_ask=0.10, fresh_edge=0.50),
        _redteam(fee_adj_edge=0.50),
        bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=0.0,
    )
    assert r["pass"] is True
    assert abs(r["position_usd"] - BANKROLL * config.MAX_TRADE_PCT) < 0.01


def test_veto_position_too_small():
    # bankroll=$10, edge=MIN_EDGE_PCT=0.08, fresh_ask=0.40
    # kelly = 0.08/0.60 = 0.133 → × 0.25 = 0.033 → $0.33 < MIN_POSITION_USD($5)
    r = risk(
        _finding(action="YES", best_ask=0.40),
        _verification(fresh_best_ask=0.40, fresh_edge=config.MIN_EDGE_PCT),
        _redteam(fee_adj_edge=config.MIN_EDGE_PCT),
        bankroll_usd=10.0, open_positions=0, daily_loss_usd=0.0,
    )
    assert r["pass"] is False
    assert r["reason"] == "position_too_small"


def test_kelly_zero_denom_vetoes():
    # fresh_ask=0.999 → denom=0.001 < 0.01 → kelly=0.0 → position=$0 < $5 → veto
    r = risk(
        _finding(action="YES", best_ask=0.999),
        _verification(fresh_best_ask=0.999, fresh_edge=0.12),
        _redteam(fee_adj_edge=0.12),
        bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=0.0,
    )
    assert r["pass"] is False
    assert r["reason"] == "position_too_small"


# ── Task 7: insan onayı + normal geçiş ───────────────────────────────────────

def test_human_approval_flag_set():
    # bankroll=$10000 → position = 0.05 × 10000 = $500 > HUMAN_APPROVAL_USD($50)
    r = risk(
        _finding(action="YES", best_ask=0.10),
        _verification(fresh_best_ask=0.10, fresh_edge=0.50),
        _redteam(fee_adj_edge=0.50),
        bankroll_usd=10_000.0, open_positions=0, daily_loss_usd=0.0,
    )
    assert r["requires_human_approval"] is True


def test_human_approval_does_not_veto():
    # Büyük pozisyon → bayrak kalkar ama pass=True
    r = risk(
        _finding(action="YES", best_ask=0.10),
        _verification(fresh_best_ask=0.10, fresh_edge=0.50),
        _redteam(fee_adj_edge=0.50),
        bankroll_usd=10_000.0, open_positions=0, daily_loss_usd=0.0,
    )
    assert r["pass"] is True
    assert r["requires_human_approval"] is True


def test_pass_normal_case():
    # bankroll=1000, edge=0.12, ask=0.40
    # kelly=0.20 → ×0.25=0.05 → position=$50.00 (≤ HUMAN_APPROVAL_USD → no flag)
    r = risk(_finding(), _verification(), _redteam(),
             bankroll_usd=BANKROLL, open_positions=0, daily_loss_usd=0.0)
    assert r["pass"] is True
    assert r["position_usd"] > 0
    assert r["kelly_f"] > 0
    assert r["kelly_fraction_applied"] == KELLY_FRACTION
    assert r["halt"] is False
    assert r["reason"] == ""
    assert r["requires_human_approval"] is False
