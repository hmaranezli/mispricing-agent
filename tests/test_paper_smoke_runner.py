"""tests/test_paper_smoke_runner.py — isolated bounded paper-smoke runner (TDD).

The runner is a PURE CALLER: it starts ONLY `main_loop._paper_shadow_scan_loop(conn, db_path=...)`
and `execution.paper_tracker._paper_monitor_loop(db_path)` against a DEDICATED sqlite db_path for a
bounded window, then prints a read-only summary. It must NOT start main(), Telegram, notifier, the
live monitor, the executor, bankroll, `_scan_and_execute`, or any live/CLOB/S1/wallet path; and every
summary query must hit ONLY the supplied db_path (never the default logs/mispricing.db).

All boundaries are mocked: the two loops are faked coroutines (so nothing real runs), durations are
tiny, and no network/order/S1/wallet/env access occurs.

First RED: `tools.paper_smoke_runner` does not exist → ModuleNotFoundError.
"""
import asyncio
import os
import sys

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import main_loop
from execution import paper_tracker

from tools import paper_smoke_runner as runner


def _fake_forever(record_key, recorded, cancelled):
    async def _fake(*args, **kwargs):
        recorded[record_key] = (args, kwargs)
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            cancelled[record_key] = True
            raise
    return _fake


async def _run_with_fake_loops(db_path, duration=0.05, extra_patches=()):
    recorded, cancelled = {}, {}
    fake_scan = _fake_forever("scan", recorded, cancelled)
    fake_monitor = _fake_forever("monitor", recorded, cancelled)
    import contextlib
    with contextlib.ExitStack() as stack:
        # Pin the paper-safe config the runner requires (conftest autouse flips COUNCIL authority on).
        stack.enter_context(patch.object(config, "DRY_RUN", True))
        stack.enter_context(patch.object(config, "NEW_ENTRIES_ENABLED", False))
        stack.enter_context(patch.object(config, "COUNCIL_DECISION_AUTHORITY_ENABLED", False))
        stack.enter_context(patch.object(main_loop, "_paper_shadow_scan_loop", fake_scan))
        stack.enter_context(patch.object(paper_tracker, "_paper_monitor_loop", fake_monitor))
        for cm in extra_patches:
            stack.enter_context(cm)
        summary = await runner.run_paper_smoke(duration_secs=duration, db_path=str(db_path))
    return recorded, cancelled, summary


# ---------------------------------------------------------------- 1) forbidden surfaces never called

@pytest.mark.asyncio
async def test_no_forbidden_surface_called_and_no_main(tmp_path):
    db = tmp_path / "paper_smoke.db"
    forbidden = ("main", "poll_commands", "notify_restart", "notify_open", "notify_close",
                 "execute", "_clob_execute", "get_effective_bankroll", "_scan_and_execute",
                 "_monitor_positions", "detect_ghosts")
    # Every forbidden surface must actually exist on main_loop (else the guard is vacuous).
    for _n in forbidden:
        assert hasattr(main_loop, _n), f"expected main_loop.{_n} to exist for the no-call guard"
    spies = {name: MagicMock() for name in forbidden}
    patches = [patch.object(main_loop, name, spy) for name, spy in spies.items()]
    recorded, cancelled, _ = await _run_with_fake_loops(db, extra_patches=patches)
    # the two paper loops DID start...
    assert "scan" in recorded and "monitor" in recorded
    # ...and NONE of the forbidden surfaces were called.
    for name, spy in spies.items():
        spy.assert_not_called()


# ------------------------------------------------------------------------------ 2) safety gates

@pytest.mark.parametrize("flag,bad_value", [
    ("DRY_RUN", False),
    ("NEW_ENTRIES_ENABLED", True),
    ("COUNCIL_DECISION_AUTHORITY_ENABLED", True),
])
@pytest.mark.asyncio
async def test_safety_gate_refuses_before_any_db_or_task(tmp_path, flag, bad_value):
    import db.schema as _schema
    db = tmp_path / "paper_smoke.db"
    scan_spy = MagicMock()
    monitor_spy = MagicMock()
    connect_spy = MagicMock()
    init_spy = MagicMock()
    with patch.object(config, flag, bad_value), \
         patch.object(main_loop, "_paper_shadow_scan_loop", scan_spy), \
         patch.object(paper_tracker, "_paper_monitor_loop", monitor_spy), \
         patch("aiosqlite.connect", connect_spy), \
         patch.object(_schema, "init_schema", init_spy):
        with pytest.raises(SystemExit):
            await runner.run_paper_smoke(duration_secs=0.05, db_path=str(db))
    # No task, no DB connection, and no schema init may occur once a gate fails.
    scan_spy.assert_not_called()
    monitor_spy.assert_not_called()
    connect_spy.assert_not_called()
    init_spy.assert_not_called()


# ----------------------------------------------------------------------- 3) db_path reaches loops

@pytest.mark.asyncio
async def test_db_path_reaches_both_loops(tmp_path):
    db = tmp_path / "paper_smoke.db"
    recorded, _, _ = await _run_with_fake_loops(db)
    # scan loop: positional conn + db_path kwarg
    scan_args, scan_kwargs = recorded["scan"]
    assert scan_args and scan_args[0] is not None, "conn must be passed to scan loop"
    assert scan_kwargs.get("db_path") == str(db)
    # monitor loop: db_path positionally
    mon_args, _ = recorded["monitor"]
    assert mon_args and mon_args[0] == str(db)


# ------------------------------------------------------------------------ 4) timebox + cancel + no leak

@pytest.mark.asyncio
async def test_timebox_cancels_both_tasks_without_leak(tmp_path):
    db = tmp_path / "paper_smoke.db"
    before = set(asyncio.all_tasks())
    _, cancelled, _ = await _run_with_fake_loops(db, duration=0.05)
    assert cancelled.get("scan") is True, "scan task must be cancelled"
    assert cancelled.get("monitor") is True, "monitor task must be cancelled"
    leaked = {t for t in asyncio.all_tasks() if t not in before and not t.done()}
    assert leaked == set(), f"runner leaked tasks: {leaked}"


# ----------------------------------------------------------------- 5) only dedicated db path opened

@pytest.mark.asyncio
async def test_only_dedicated_db_path_opened(tmp_path):
    db = tmp_path / "paper_smoke.db"
    import aiosqlite
    real_connect = aiosqlite.connect
    opened = []

    def _spy_connect(path, *a, **k):
        opened.append(str(path))
        return real_connect(path, *a, **k)

    await _run_with_fake_loops(db, extra_patches=[patch("aiosqlite.connect", side_effect=_spy_connect)])
    assert opened, "runner must open the dedicated db"
    assert all(p == str(db) for p in opened), f"only dedicated db allowed; opened={opened}"
    assert all("mispricing.db" not in p for p in opened), "default logs/mispricing.db must NOT be opened"


# --------------------------------------------------------- 6) summary reads only the supplied db_path

@pytest.mark.asyncio
async def test_summary_queries_only_supplied_db_path(tmp_path):
    db = tmp_path / "paper_smoke.db"
    import aiosqlite
    from db.schema import init_schema
    conn = await aiosqlite.connect(str(db))
    await init_schema(conn)
    await conn.close()

    real_connect = aiosqlite.connect
    opened = []

    def _spy_connect(path, *a, **k):
        opened.append(str(path))
        return real_connect(path, *a, **k)

    with patch("aiosqlite.connect", side_effect=_spy_connect):
        summary = await runner.summarize(str(db))

    assert summary["db_path"] == str(db)
    assert "shadow_positions_by_status" in summary
    assert isinstance(summary["paper_entry_events"], int)
    assert opened == [str(db)], f"summary must read only the supplied db; opened={opened}"
    assert all("mispricing.db" not in p for p in opened)


# ----------------------------------------------------------------------- 7) duration guard (positive)

@pytest.mark.asyncio
async def test_nonpositive_duration_refused(tmp_path):
    db = tmp_path / "paper_smoke.db"
    scan_spy = MagicMock()
    # Pin safe flags so the gate passes and the DURATION guard is what refuses.
    with patch.object(config, "DRY_RUN", True), \
         patch.object(config, "NEW_ENTRIES_ENABLED", False), \
         patch.object(config, "COUNCIL_DECISION_AUTHORITY_ENABLED", False), \
         patch.object(main_loop, "_paper_shadow_scan_loop", scan_spy), \
         patch.object(paper_tracker, "_paper_monitor_loop", MagicMock()):
        with pytest.raises(SystemExit):
            await runner.run_paper_smoke(duration_secs=0, db_path=str(db))
    scan_spy.assert_not_called()


def test_cli_rejects_nonpositive_duration():
    with pytest.raises(SystemExit):
        runner.main(["--duration-secs", "0", "--db-path", "/tmp/x.db"])


# ---------------------------------------------------------- 8) fail-fast: scan loop crash propagates

@pytest.mark.asyncio
async def test_scan_loop_crash_propagates_and_cancels_monitor(tmp_path):
    db = tmp_path / "paper_smoke.db"
    cancelled = {}

    async def _boom_scan(*args, **kwargs):
        raise RuntimeError("boom-scan")

    async def _fake_monitor(*args, **kwargs):
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            cancelled["monitor"] = True
            raise

    with patch.object(config, "DRY_RUN", True), \
         patch.object(config, "NEW_ENTRIES_ENABLED", False), \
         patch.object(config, "COUNCIL_DECISION_AUTHORITY_ENABLED", False), \
         patch.object(main_loop, "_paper_shadow_scan_loop", _boom_scan), \
         patch.object(paper_tracker, "_paper_monitor_loop", _fake_monitor):
        # Long timebox: the runner must react to the crash, NOT wait out the duration.
        with pytest.raises(RuntimeError, match="boom-scan"):
            await runner.run_paper_smoke(duration_secs=30, db_path=str(db))
    assert cancelled.get("monitor") is True, "monitor task must be cancelled when scan crashes"


# ------------------------------------------------------- 9) fail-fast: monitor loop crash propagates

@pytest.mark.asyncio
async def test_monitor_loop_crash_propagates_and_cancels_scan(tmp_path):
    db = tmp_path / "paper_smoke.db"
    cancelled = {}

    async def _fake_scan(*args, **kwargs):
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            cancelled["scan"] = True
            raise

    async def _boom_monitor(*args, **kwargs):
        raise RuntimeError("boom-monitor")

    with patch.object(config, "DRY_RUN", True), \
         patch.object(config, "NEW_ENTRIES_ENABLED", False), \
         patch.object(config, "COUNCIL_DECISION_AUTHORITY_ENABLED", False), \
         patch.object(main_loop, "_paper_shadow_scan_loop", _fake_scan), \
         patch.object(paper_tracker, "_paper_monitor_loop", _boom_monitor):
        with pytest.raises(RuntimeError, match="boom-monitor"):
            await runner.run_paper_smoke(duration_secs=30, db_path=str(db))
    assert cancelled.get("scan") is True, "scan task must be cancelled when monitor crashes"
