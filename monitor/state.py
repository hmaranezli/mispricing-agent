"""monitor/state.py — Paylasilan bot durumu: main_loop ve telegram_commands arasin da ortak flag'ler."""

SOFT_PAUSED:        bool = False
HARD_PAUSED:        bool = False
FLATTEN_REQUESTED:  bool = False
SHUTDOWN_REQUESTED: bool = False


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


def request_flatten() -> None:
    global FLATTEN_REQUESTED, SOFT_PAUSED
    FLATTEN_REQUESTED = True
    SOFT_PAUSED = True  # önceden pause → yeni entry engellenir


def clear_flatten() -> None:
    global FLATTEN_REQUESTED
    FLATTEN_REQUESTED = False


def request_shutdown() -> None:
    """D#8 graceful shutdown: sinyal handler bunu çağırır (raise değil). main() loop'u flag'i
    kill_switch_check yanında kontrol edip break eder → mevcut finally temizliği çalışır."""
    global SHUTDOWN_REQUESTED
    SHUTDOWN_REQUESTED = True


def is_shutdown_requested() -> bool:
    return SHUTDOWN_REQUESTED


def clear_shutdown() -> None:
    global SHUTDOWN_REQUESTED
    SHUTDOWN_REQUESTED = False
