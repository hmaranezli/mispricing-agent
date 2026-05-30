"""execution/executor.py — DRY_RUN order logger."""
import json
import sys
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

LOG_FILE = Path("logs/dry_run.jsonl")


def _log(event: str, data: dict, log_file: Path = LOG_FILE) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts":    datetime.now(timezone.utc).isoformat(),
        "layer": "execution",
        "event": event,
        **data,
    }
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def execute(
    finding:        dict,
    gate_result:    dict,
    risk_result:    dict,
    open_positions: list,
    log_file:       Path = LOG_FILE,
) -> dict | None:
    """Gate onaylı bulguyu DRY_RUN'da loglar, pozisyon kaydı döndürür."""
    if not gate_result.get("pass"):
        _log("position_skipped", {
            "reason":   "gate_vetoed",
            "asset":    finding.get("asset"),
            "slug":     finding.get("slug"),
            "dry_run":  config.DRY_RUN,
        }, log_file)
        return None

    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
        _log("position_skipped", {
            "reason":   "max_open_positions",
            "asset":    finding.get("asset"),
            "slug":     finding.get("slug"),
            "dry_run":  config.DRY_RUN,
        }, log_file)
        return None

    # Giriş fiyatı: YES için ask, NO için 1-bid
    if finding["action"] == "YES":
        pm_entry_price = finding["best_ask"]
    else:
        pm_entry_price = round(1 - finding["best_bid"], 4)

    position = {
        "position_id":       str(uuid.uuid4()),
        "asset":             finding["asset"],
        "action":            finding["action"],
        "slug":              finding["slug"],
        "pm_entry_price":    pm_entry_price,
        "fair_value":        finding["fair_value"],
        "ref_price":         finding["ref_price"],
        "edge":              finding["edge"],
        "position_usd":      risk_result["position_usd"],
        "kelly_f":           risk_result["kelly_f"],
        "confidence_score":  gate_result["confidence_score"],
        "seconds_remaining": finding["seconds_remaining"],
        "opened_at":         datetime.now(timezone.utc).isoformat(),
        "status":                  "open",
        "requires_human_approval": risk_result["position_usd"] > config.HUMAN_APPROVAL_USD,
        "dry_run":                 config.DRY_RUN,
        "exit_reason":             None,
        "closed_at":               None,
    }

    _log("position_opened", {
        "position_id":             position["position_id"],
        "asset":                   position["asset"],
        "action":                  position["action"],
        "slug":                    position["slug"],
        "pm_entry_price":          position["pm_entry_price"],
        "fair_value":              position["fair_value"],
        "ref_price":               position["ref_price"],
        "position_usd":            position["position_usd"],
        "kelly_f":                 position["kelly_f"],
        "confidence_score":        position["confidence_score"],
        "seconds_remaining":       position["seconds_remaining"],
        "requires_human_approval": position["requires_human_approval"],
        "opened_at":               position["opened_at"],
        "dry_run":                 position["dry_run"],
    }, log_file)

    return position
