"""
council/gate.py — KATMAN 5: Kapı.

Son karar ve uygulama katmanı. 4 katmandan geçen bulgu için güven
skoru hesaplar, insan onayı yönetir, DRY_RUN'da JSONL'a loglar.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

# ── Skor bileşeni sınırları ───────────────────────────────────────────────────
EDGE_ZERO   = 0.08   # config.MIN_EDGE_PCT eşiği
EDGE_MAX    = 0.15
LIQ_ZERO    = 500    # RedTeam LIQUIDITY_VETO_USD eşiği
LIQ_MAX     = 3000
TIME_ZERO   = 120    # RedTeam MIN_THESIS_SECS eşiği
TIME_MAX    = 300
SPREAD_ZERO = 0.04   # RedTeam SPREAD_VETO eşiği
SPREAD_MAX  = 0.01

APPROVAL_TIMEOUT_SECS = 300
LOG_FILE = Path("logs/dry_run.jsonl")


def _confidence_score(redteam: dict, verification: dict) -> float:
    """0-100 güven skoru. 4 bileşen ağırlıklı toplam."""
    edge   = redteam["fee_adj_edge"]
    liq    = redteam["liquidity_usd"]
    secs   = verification["fresh_seconds"]
    spread = redteam["spread"]

    edge_s   = min(max((edge   - EDGE_ZERO)   / (EDGE_MAX   - EDGE_ZERO),   0.0), 1.0)
    liq_s    = min(max((liq    - LIQ_ZERO)    / (LIQ_MAX    - LIQ_ZERO),    0.0), 1.0)
    time_s   = min(max((secs   - TIME_ZERO)   / (TIME_MAX   - TIME_ZERO),   0.0), 1.0)
    spread_s = min(max((SPREAD_ZERO - spread) / (SPREAD_ZERO - SPREAD_MAX), 0.0), 1.0)

    return round(edge_s * 40 + liq_s * 30 + time_s * 15 + spread_s * 15, 1)


def _gate_decide(finding: dict, verification: dict,
                 redteam: dict, risk_result: dict) -> dict:
    """Güven skoru hesapla, CONFIDENCE_THRESHOLD kontrolü yap."""
    score = _confidence_score(redteam, verification)
    if score < config.CONFIDENCE_THRESHOLD:
        return {
            "pass":             False,
            "confidence_score": score,
            "action_taken":     "vetoed",
            "reason":           "confidence_below_threshold",
        }
    return {
        "pass":             True,
        "confidence_score": score,
        "action_taken":     "pending",
        "reason":           "",
    }


def _log(finding: dict, verification: dict, redteam: dict,
         decision: dict, risk_result: dict) -> None:
    """Kararı LOG_FILE'a yaz. Dizin yoksa oluşturur."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts":                      datetime.now(timezone.utc).isoformat(),
        "dry_run":                 config.DRY_RUN,
        "pass":                    decision["pass"],
        "action":                  finding.get("action", ""),
        "slug":                    finding.get("slug", ""),
        "asset":                   finding.get("asset", ""),
        "position_usd":            risk_result.get("position_usd", 0.0),
        "confidence_score":        decision["confidence_score"],
        "fee_adj_edge":            redteam.get("fee_adj_edge", 0.0),
        "liquidity_usd":           redteam.get("liquidity_usd", 0.0),
        "fresh_seconds":           verification.get("fresh_seconds", 0),
        "spread":                  redteam.get("spread", 0.0),
        "action_taken":            decision["action_taken"],
        "requires_human_approval": risk_result.get("requires_human_approval", False),
        "reason":                  decision["reason"],
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def gate(finding: dict, verification: dict,
               redteam: dict, risk_result: dict) -> dict:
    """
    Son karar: güven skoru → insan onayı → log → aksiyon.

    Returns:
        {pass, confidence_score, action_taken, reason}
    """
    decision = _gate_decide(finding, verification, redteam, risk_result)

    if not decision["pass"]:
        _log(finding, verification, redteam, decision, risk_result)
        return decision

    # İnsan onayı bayrağı
    if risk_result.get("requires_human_approval", False) and not config.DRY_RUN:
        # Canlı modda Telegram + timeout (şimdilik timeout döner)
        decision["action_taken"] = "approval_timeout"
        decision["pass"] = False
        decision["reason"] = "human_approval_timeout"
        _log(finding, verification, redteam, decision, risk_result)
        return decision

    # DRY_RUN: logla ve dön
    decision["action_taken"] = "dry_run_logged"
    _log(finding, verification, redteam, decision, risk_result)
    return decision
