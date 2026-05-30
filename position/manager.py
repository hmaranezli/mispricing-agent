"""position/manager.py — Açık pozisyon takibi ve çıkış kararı."""
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from data.fair_value import fair_yes

LOG_FILE = Path("logs/dry_run.jsonl")

PROFIT_TARGET_FRACTION = 0.85
NEAR_EXPIRY_SECS       = 90


def _log(event: str, data: dict, log_file: Path = LOG_FILE) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts":    datetime.now(timezone.utc).isoformat(),
        "layer": "position",
        "event": event,
        **data,
    }
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def close_position(
    position:      dict,
    exit_reason:   str,
    pm_exit_price: float | None = None,
    log_file:      Path = LOG_FILE,
) -> dict:
    """Pozisyonu kapatır, JSONL'a yazar, güncellenmiş kaydı döndürür."""
    closed = {
        **position,
        "status":        "closed",
        "exit_reason":   exit_reason,
        "closed_at":     datetime.now(timezone.utc).isoformat(),
        "pm_exit_price": pm_exit_price,
    }
    _log("position_closed", {
        "position_id":    closed["position_id"],
        "asset":          closed["asset"],
        "action":         closed["action"],
        "slug":           closed["slug"],
        "exit_reason":    exit_reason,
        "pm_entry_price": closed["pm_entry_price"],
        "pm_exit_price":  pm_exit_price,
        "fair_value":     closed["fair_value"],
        "closed_at":      closed["closed_at"],
        "dry_run":        closed["dry_run"],
    }, log_file)
    return closed


def check_exit(
    position:            dict,
    hl_price:            float,
    pm_yes_price:        float,
    time_to_expiry_secs: int,
) -> str | None:
    """Placeholder — Task 2'de implemente edilecek."""
    return None
