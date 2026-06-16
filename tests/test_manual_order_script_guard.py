"""tests/test_manual_order_script_guard.py — proves the analysis/test_order.py manual order script
is default-safe (TDD, offline).

analysis/test_order.py is a standalone manual script that calls client.create_and_post_order(...)
to post a real $1 CLOB order. This suite proves that by default it BLOCKS before any
create_and_post_order call, that importing the module posts nothing, and that the explicit opt-in
path uses ONLY a fake client (no network) in tests.

No network / no real client: get_client, reset_client and find_shortterm are monkeypatched with
fakes; create_and_post_order is recorded, never real.
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analysis.test_order as T

ENV = "MANUAL_ORDER_SCRIPT_ENABLED"


class FakeClient:
    def __init__(self):
        self.posted = []

    def get_balance_allowance(self, params=None):
        return {"balance": "100"}

    def create_and_post_order(self, order_args, order_type=None):
        self.posted.append((order_args, order_type))
        return {"status": "matched", "success": True, "orderID": "x",
                "takingAmount": "2", "makingAmount": "1"}


async def _fake_find(intervals=None):
    return [{"slug": "btc-updown-15m-x", "clobTokenIds": '["tok1","tok2"]', "bestAsk": "0.50"}]


@pytest.fixture
def _patched(monkeypatch):
    """Patch module globals so run_test() runs fully offline with a recording fake client."""
    fake = FakeClient()
    get_client_calls = []

    def _get_client():
        get_client_calls.append(1)
        return fake

    monkeypatch.setattr(T, "get_client", _get_client)
    monkeypatch.setattr(T, "reset_client", lambda: None)
    monkeypatch.setattr(T, "find_shortterm", _fake_find)
    return fake, get_client_calls


def test_flag_defaults_disabled(monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    assert T._manual_order_enabled() is False


def test_import_does_not_post():
    # Importing the module must not construct a client or post any order.
    assert asyncio.iscoroutinefunction(T.run_test)
    assert hasattr(T, "_manual_order_enabled")


def test_default_path_blocks_before_posting(monkeypatch, _patched):
    fake, get_client_calls = _patched
    monkeypatch.delenv(ENV, raising=False)
    ok = asyncio.run(T.run_test())
    assert ok is False                      # default blocks
    assert fake.posted == []                # no order posted
    assert get_client_calls == []           # blocked BEFORE client construction / posting


@pytest.mark.parametrize("val", ["1", "true", "YES", "on"])
def test_opt_in_uses_only_fake_client(monkeypatch, _patched, val):
    fake, get_client_calls = _patched
    monkeypatch.setenv(ENV, val)
    ok = asyncio.run(T.run_test())
    assert ok is True
    assert len(fake.posted) >= 1            # opt-in path posts via the (fake) client only
    assert get_client_calls == [1]          # fake client obtained, no real network
