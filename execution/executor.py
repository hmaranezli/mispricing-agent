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


async def execute(finding: dict, gate_result: dict, risk_result: dict) -> dict:
    """Placeholder — Task 2'de implemente edilecek."""
    raise NotImplementedError("execute() henüz implemente edilmedi.")
