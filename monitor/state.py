"""monitor/state.py — Paylasilan bot durumu: main_loop ve telegram_commands arasin da ortak flag'ler."""

SOFT_PAUSED: bool = False
HARD_PAUSED: bool = False


def soft_pause() -> None:
    global SOFT_PAUSED
    SOFT_PAUSED = True


def soft_resume() -> None:
    global SOFT_PAUSED
    SOFT_PAUSED = False


def hard_pause() -> None:
    global HARD_PAUSED
    HARD_PAUSED = True


def hard_resume() -> None:
    global HARD_PAUSED
    HARD_PAUSED = False


def is_paused() -> bool:
    return SOFT_PAUSED or HARD_PAUSED
