"""execution/executor.py — DRY_RUN order logger."""
import json
import sys
import os
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
        _log("position_skipped", {"reason": "gate_vetoed", "dry_run": config.DRY_RUN}, log_file)
        return None

    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
        _log("position_skipped", {"reason": "max_open_positions", "dry_run": config.DRY_RUN}, log_file)
        return None

    return None  # happy path — Task 3'te tamamlanacak
