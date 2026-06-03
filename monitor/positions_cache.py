"""monitor/positions_cache.py — main_loop ve telegram_commands arasinda paylasilan acik pozisyon listesi."""
import time

_positions: list[dict] = []
_updated_at: float = 0.0


def set_open_positions(positions: list[dict]) -> None:
    global _positions, _updated_at
    _positions = list(positions)
    _updated_at = time.time()


def get_open_positions() -> list[dict]:
    return _positions


def seconds_since_update() -> float:
    if _updated_at == 0.0:
        return float("inf")
    return time.time() - _updated_at
