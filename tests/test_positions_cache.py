"""tests/test_positions_cache.py"""
import time
import pytest
from monitor import positions_cache


def setup_function():
    positions_cache._positions = []
    positions_cache._updated_at = 0.0


def test_initial_state():
    assert positions_cache.get_open_positions() == []
    assert positions_cache.seconds_since_update() == float("inf")


def test_set_and_get():
    pos = [{"slug": "btc-up-5m", "action": "YES", "position_usd": 1.25}]
    positions_cache.set_open_positions(pos)
    assert positions_cache.get_open_positions() == pos


def test_set_returns_copy():
    pos = [{"slug": "btc-up-5m"}]
    positions_cache.set_open_positions(pos)
    pos.append({"slug": "eth-up-5m"})
    assert len(positions_cache.get_open_positions()) == 1


def test_seconds_since_update():
    positions_cache.set_open_positions([])
    assert positions_cache.seconds_since_update() < 2.0


def test_overwrite():
    positions_cache.set_open_positions([{"slug": "a"}])
    positions_cache.set_open_positions([{"slug": "b"}, {"slug": "c"}])
    assert len(positions_cache.get_open_positions()) == 2
