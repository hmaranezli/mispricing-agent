"""tests/test_main_loop_paper_wiring.py — paper-smoke DB-path forwarding seam (TDD).

Wiring-only contract: `main_loop._paper_shadow_scan_loop(conn, db_path=...)` must FORWARD the exact
`db_path` into `paper_tracker.schedule_paper_open(...)`, so an isolated paper-smoke runner can direct
all paper-open writes into a dedicated DB instead of the default `logs/mispricing.db`.

No live API/order/S1/wallet/env/paper-runtime: every network/scan/persistence boundary is mocked, and
`schedule_paper_open` is a spy. The scan loop is `while True`; to avoid hanging, the spy raises a
BaseException sentinel (NOT Exception — the loop's `except Exception` would swallow it) after recording
the call, which cleanly breaks the loop. `asyncio.sleep` is mocked so the 75s startup offset is instant.

First RED: `_paper_shadow_scan_loop` has signature `(conn)` only → calling with `db_path=` raises
TypeError (seam absent) → the expected sentinel is never raised → test fails.
"""
import asyncio
import os
import sys

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main_loop


_SENTINEL_DB = "/tmp/paper_smoke_sentinel_never_opened.db"  # schedule_paper_open is mocked → never opened


class _StopLoopSentinel(BaseException):
    """BaseException so the scan loop's `except Exception` cannot swallow it → breaks `while True`."""


def _finding():
    return {"slug": "btc-up-5m-wiring", "asset": "BTC", "action": "YES",
            "yes_token_id": "yes-tok", "no_token_id": "no-tok",
            "fair_value": 0.55, "best_ask": 0.45, "edge": 0.20, "seconds_remaining": 600}


@pytest.mark.asyncio
async def test_paper_shadow_scan_loop_forwards_db_path_to_schedule_paper_open():
    """db_path passed to _paper_shadow_scan_loop must reach schedule_paper_open(db_path=...) exactly."""
    schedule_spy = MagicMock(side_effect=_StopLoopSentinel())  # record kwargs, then break the loop

    async def _fake_scan(*a, **k):
        return ([_finding()], [])

    with patch("main_loop.asyncio.sleep", new_callable=AsyncMock), \
         patch("council.scout.scan_shadow_edges", new=_fake_scan), \
         patch.object(main_loop.paper_tracker, "build_entry_snapshot",
                      new=AsyncMock(return_value={"signal_timestamp_ms": 1_700_000_000_000})), \
         patch.object(main_loop.paper_tracker, "schedule_paper_open", schedule_spy):
        with pytest.raises(_StopLoopSentinel):
            await main_loop._paper_shadow_scan_loop(object(), db_path=_SENTINEL_DB)

    assert schedule_spy.call_count >= 1, "schedule_paper_open must be called at least once"
    assert schedule_spy.call_args.kwargs.get("db_path") == _SENTINEL_DB, \
        "scan loop must forward the exact db_path into schedule_paper_open"


@pytest.mark.asyncio
async def test_paper_shadow_scan_loop_default_db_path_is_none_when_omitted():
    """Backward compatibility: omitting db_path forwards db_path=None (legacy default DB behavior)."""
    schedule_spy = MagicMock(side_effect=_StopLoopSentinel())

    async def _fake_scan(*a, **k):
        return ([_finding()], [])

    with patch("main_loop.asyncio.sleep", new_callable=AsyncMock), \
         patch("council.scout.scan_shadow_edges", new=_fake_scan), \
         patch.object(main_loop.paper_tracker, "build_entry_snapshot",
                      new=AsyncMock(return_value={"signal_timestamp_ms": 1_700_000_000_000})), \
         patch.object(main_loop.paper_tracker, "schedule_paper_open", schedule_spy):
        with pytest.raises(_StopLoopSentinel):
            await main_loop._paper_shadow_scan_loop(object())

    assert schedule_spy.call_args.kwargs.get("db_path") is None, \
        "omitting db_path must preserve legacy default (None → DB_FILE)"


# ---------------------------------------------------------- telemetry db_path forwarding (isolation)

def _telemetry_candidate(action="YES"):
    # ref_price/cur_price present so the optional hl_drift computation is safe (no error before the
    # telemetry call); other fields are looked up with .get() and may be absent.
    return {"slug": "btc-up-5m-tel", "asset": "BTC", "action": action,
            "fair_value": 0.55, "best_ask": 0.45, "edge": 0.20, "seconds_remaining": 600,
            "yes_token_id": "y", "no_token_id": "n", "cur_price": 1.0, "ref_price": 1.0}


def _telemetry_patches(scan_returns, sched_tel_spy):
    """Patches that drive _paper_shadow_scan_loop to a model_telemetry.schedule_telemetry call."""
    async def _fake_scan(*a, **k):
        return scan_returns
    return [
        patch("main_loop.asyncio.sleep", new_callable=AsyncMock),
        patch("council.scout.scan_shadow_edges", new=_fake_scan),
        patch.object(main_loop.paper_tracker, "build_entry_snapshot",
                     new=AsyncMock(return_value={"signal_timestamp_ms": 1_700_000_000_000})),
        patch.object(main_loop.paper_tracker, "schedule_paper_open", MagicMock()),
        patch.object(main_loop.model_telemetry, "get_raw_vol", new=AsyncMock(return_value=0.5)),
        patch.object(main_loop.model_telemetry, "compute_legacy_telemetry_v2",
                     new=MagicMock(return_value="rec")),
        patch.object(main_loop.model_telemetry, "schedule_telemetry", sched_tel_spy),
    ]


@pytest.mark.asyncio
async def test_scan_loop_forwards_db_path_to_telemetry_findings_site():
    """would_enter=True telemetry (main_loop.py:604) must receive the supplied db_path, never None."""
    import contextlib
    sched_tel_spy = MagicMock(side_effect=_StopLoopSentinel())  # record db_path, then break the loop
    with contextlib.ExitStack() as stack:
        for cm in _telemetry_patches(([_telemetry_candidate()], []), sched_tel_spy):
            stack.enter_context(cm)
        with pytest.raises(_StopLoopSentinel):
            await main_loop._paper_shadow_scan_loop(object(), db_path=_SENTINEL_DB)
    assert sched_tel_spy.call_count >= 1, "findings-site schedule_telemetry must be reached"
    assert sched_tel_spy.call_args.kwargs.get("db_path") == _SENTINEL_DB, \
        "findings-site telemetry must forward the dedicated db_path (not write the default DB)"


@pytest.mark.asyncio
async def test_scan_loop_forwards_db_path_to_telemetry_rejected_site():
    """would_enter=False telemetry (main_loop.py:635) must receive the supplied db_path, never None."""
    import contextlib
    sched_tel_spy = MagicMock(side_effect=_StopLoopSentinel())
    with contextlib.ExitStack() as stack:
        for cm in _telemetry_patches(([], [_telemetry_candidate()]), sched_tel_spy):
            stack.enter_context(cm)
        with pytest.raises(_StopLoopSentinel):
            await main_loop._paper_shadow_scan_loop(object(), db_path=_SENTINEL_DB)
    assert sched_tel_spy.call_count >= 1, "rejected-site schedule_telemetry must be reached"
    assert sched_tel_spy.call_args.kwargs.get("db_path") == _SENTINEL_DB, \
        "rejected-site telemetry must forward the dedicated db_path (not write the default DB)"
