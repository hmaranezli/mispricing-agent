"""monitor/kill_switch.py — Dosya tabanlı kill switch. touch logs/KILL → durur."""
from pathlib import Path

KILL_FILE = Path("logs/KILL")


def check() -> bool:
    return KILL_FILE.exists()


def arm() -> None:
    KILL_FILE.parent.mkdir(parents=True, exist_ok=True)
    KILL_FILE.touch()


def disarm() -> None:
    KILL_FILE.unlink(missing_ok=True)
