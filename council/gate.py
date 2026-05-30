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
    """Stub — Task 2'de implement edilecek."""
    return {"pass": False, "confidence_score": 0.0,
            "action_taken": "vetoed", "reason": "not_implemented"}


async def gate(finding: dict, verification: dict,
               redteam: dict, risk_result: dict) -> dict:
    """Stub — Task 3'te implement edilecek."""
    return {"pass": False, "confidence_score": 0.0,
            "action_taken": "vetoed", "reason": "not_implemented"}
