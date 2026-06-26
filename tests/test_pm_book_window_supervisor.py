"""tests/test_pm_book_window_supervisor.py — TDD for rotating-window PM book supervisor.

The supervisor collects consecutive BTC 5m PM-book characterization windows by:
  * deriving window slugs from UTC epoch math only,
  * performing INJECTED read-only market/token lookup (discovery lives here, never in the runner),
  * gating each window on a full-target freshness budget,
  * launching the ratified diagnostic runner per window with EXPLICIT slug/tokens only,
  * recording every decision to an append-only JSONL manifest.

All tests use fakes: fake lookup, fake launcher, fake clock, fake sleep, fake child process.
NO live Gamma/CLOB calls, NO real subprocess, NO network, NO real production DB.

First RED: module tools.pm_book_window_supervisor does not exist -> ImportError.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.pm_book_window_supervisor import (
    SKIP_REASONS,
    COOLDOWN_FLOOR_SECONDS,
    CYCLE_SLEEP_FLOOR_SECONDS,
    compute_window_start,
    slug_for_window,
    estimate_run_seconds,
    resolve_window,
    build_runner_argv,
    JsonlManifestWriter,
    _terminate_child,
    run_window_supervisor,
)

_ASSET = "BTC"
_TF = "5m"
_BASE = "https://clob.example.com"


# ===========================================================================
# Fakes
# ===========================================================================

class _Clock:
    """Frozen-by-default fake epoch clock; advance() to move time forward."""
    def __init__(self, t0):
        self.t = float(t0)

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def _sleeps_recorder():
    calls = []
    async def _sleep(s):
        calls.append(s)
    return _sleep, calls


def _auto_valid_lookup(yes="111", no="222", active=True, closed=False, condition_id="0xabc"):
    """Async lookup that returns a valid market for ANY slug (expiry derived from slug window)."""
    seen = []
    async def _f(slug):
        seen.append(slug)
        ws = int(slug.rsplit("-", 1)[1])
        return {"active": active, "closed": closed, "condition_id": condition_id,
                "expiry_epoch": ws + 300,
                "tokens": [{"outcome": "Up", "token_id": yes},
                           {"outcome": "Down", "token_id": no}]}
    _f.seen = seen
    return _f


def _launcher(result=None, result_fn=None):
    """Async launcher recording the exact params dict it received."""
    params_log = []
    async def _f(params):
        params_log.append(params)
        if result_fn is not None:
            return result_fn(params)
        return result or {"exit_code": 0, "captures": 100, "stop_reason": "max_captures",
                          "db_file_exists": True, "db_row_count": 100}
    _f.params_log = params_log
    return _f


def _base_supervisor_kwargs(**over):
    kw = dict(
        asset=_ASSET, timeframe=_TF, base_url=_BASE, db_dir="/tmp/lab",
        cycle_sleep_seconds=1.5, per_window_max_captures=100,
        expiry_buffer_seconds=30.0, inter_window_cooldown_seconds=COOLDOWN_FLOOR_SECONDS,
        expected_capture_span_seconds=0.3, launch_overhead_seconds=2.0,
        max_windows=2,
        run_id="run-test",
    )
    kw.update(over)
    return kw


# A clock value divisible by 300 → window_start == now, remaining(offset0)=300
_T0 = 1_000_000_500  # 300 * 3333335


# ===========================================================================
# 1. UTC epoch-only window math
# ===========================================================================

def test_window_math_exact_boundary():
    assert compute_window_start(1_000_000_500) == 1_000_000_500


def test_window_math_one_sec_before_boundary():
    # 1s before a 300 boundary rounds down to the previous window
    assert compute_window_start(1_000_000_499) == 1_000_000_200


def test_window_math_one_sec_after_boundary():
    assert compute_window_start(1_000_000_501) == 1_000_000_500


def test_window_math_timezone_independent():
    # same epoch under different TZ env → identical slug (epoch math, no local tz)
    saved = os.environ.get("TZ")
    try:
        os.environ["TZ"] = "America/New_York"
        a = slug_for_window(_ASSET, _TF, compute_window_start(_T0))
        os.environ["TZ"] = "Asia/Tokyo"
        b = slug_for_window(_ASSET, _TF, compute_window_start(_T0))
        assert a == b == f"btc-updown-5m-{_T0}"
    finally:
        if saved is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = saved


# ===========================================================================
# 2. Full-target budget policy
# ===========================================================================

def test_estimate_run_seconds_formula():
    # overhead + N*span + (N-1)*sleep
    est = estimate_run_seconds(max_captures=100, cycle_sleep_seconds=1.5,
                               expected_capture_span_seconds=0.3, launch_overhead_seconds=2.0)
    assert est == pytest.approx(2.0 + 100 * 0.3 + 99 * 1.5)


def test_sufficient_budget_resolves_ok():
    look = {"active": True, "closed": False, "condition_id": "0x1",
            "expiry_epoch": _T0 + 300,
            "tokens": [{"outcome": "Up", "token_id": "1"}, {"outcome": "Down", "token_id": "2"}]}
    out = resolve_window(lookup_result=look, computed_expiry_epoch=_T0 + 300,
                         now_epoch=_T0, estimated_run_seconds=10.0, expiry_buffer_seconds=30.0)
    assert out[0] == "ok"
    assert out[1] == "1" and out[2] == "2"


def test_insufficient_budget_skips_with_reason():
    look = {"active": True, "closed": False, "condition_id": "0x1",
            "expiry_epoch": _T0 + 300,
            "tokens": [{"outcome": "Up", "token_id": "1"}, {"outcome": "Down", "token_id": "2"}]}
    # remaining = 50s; estimate 100 + buffer 30 = 130 > 50 -> skip
    out = resolve_window(lookup_result=look, computed_expiry_epoch=_T0 + 300,
                         now_epoch=_T0 + 250, estimated_run_seconds=100.0, expiry_buffer_seconds=30.0)
    assert out == ("skip", "insufficient_freshness_budget")


def test_duration_capped_to_expiry_margin():
    look = {"active": True, "closed": False, "condition_id": "0x1",
            "expiry_epoch": _T0 + 300,
            "tokens": [{"outcome": "Up", "token_id": "1"}, {"outcome": "Down", "token_id": "2"}]}
    # remaining = 300, buffer 30 -> capped duration = 270
    out = resolve_window(lookup_result=look, computed_expiry_epoch=_T0 + 300,
                         now_epoch=_T0, estimated_run_seconds=10.0, expiry_buffer_seconds=30.0)
    assert out[0] == "ok"
    assert out[3] == pytest.approx(270.0)


# ===========================================================================
# 3/4. Mapping + expiry validation skip reasons
# ===========================================================================

def _ok_look(**over):
    look = {"active": True, "closed": False, "condition_id": "0x1",
            "expiry_epoch": _T0 + 300,
            "tokens": [{"outcome": "Up", "token_id": "1"}, {"outcome": "Down", "token_id": "2"}]}
    look.update(over)
    return look


def _resolve(look, **over):
    kw = dict(computed_expiry_epoch=_T0 + 300, now_epoch=_T0,
              estimated_run_seconds=10.0, expiry_buffer_seconds=30.0)
    kw.update(over)
    return resolve_window(lookup_result=look, **kw)


def test_lookup_error_reason_propagates():
    out = _resolve({"skip_reason": "gamma_timeout"})
    assert out == ("skip", "gamma_timeout")


def test_market_inactive_skips():
    assert _resolve(_ok_look(active=False)) == ("skip", "market_inactive")


def test_market_closed_skips():
    assert _resolve(_ok_look(closed=True)) == ("skip", "market_closed")


def test_condition_id_missing_skips():
    assert _resolve(_ok_look(condition_id=None)) == ("skip", "condition_id_missing")


def test_expiry_mismatch_skips():
    assert _resolve(_ok_look(expiry_epoch=_T0 + 999)) == ("skip", "expiry_mismatch")


def test_outcome_missing_skips():
    look = _ok_look(tokens=[{"outcome": "Up", "token_id": "1"}])  # no Down
    assert _resolve(look) == ("skip", "mapping_missing")


def test_mapping_ambiguous_skips():
    look = _ok_look(tokens=[{"outcome": "Up", "token_id": "1"},
                            {"outcome": "Up", "token_id": "9"},
                            {"outcome": "Down", "token_id": "2"}])
    assert _resolve(look) == ("skip", "mapping_ambiguous")


def test_token_id_empty_skips():
    look = _ok_look(tokens=[{"outcome": "Up", "token_id": ""},
                            {"outcome": "Down", "token_id": "2"}])
    assert _resolve(look) == ("skip", "token_id_empty")


def test_token_id_non_numeric_skips():
    look = _ok_look(tokens=[{"outcome": "Up", "token_id": "abc"},
                            {"outcome": "Down", "token_id": "2"}])
    assert _resolve(look) == ("skip", "token_id_non_numeric")


def test_token_ids_equal_skips():
    look = _ok_look(tokens=[{"outcome": "Up", "token_id": "5"},
                            {"outcome": "Down", "token_id": "5"}])
    assert _resolve(look) == ("skip", "token_ids_equal")


def test_skip_reason_taxonomy_is_centralized_constant_set():
    for r in ("gamma_http_error", "gamma_timeout", "gamma_malformed_json", "gamma_market_missing",
              "clob_market_http_error", "clob_market_timeout", "clob_market_malformed_json",
              "market_inactive", "market_closed", "condition_id_missing", "outcome_missing",
              "mapping_missing", "mapping_ambiguous", "token_id_empty", "token_id_non_numeric",
              "token_ids_equal", "insufficient_freshness_budget", "duplicate_window",
              "no_fresh_window", "expiry_mismatch"):
        assert r in SKIP_REASONS


# ===========================================================================
# 5. build_runner_argv — ratified CLI shape, no discovery args
# ===========================================================================

_PARAMS = {
    "market_slug": "btc-updown-5m-123", "yes_token_id": "111", "no_token_id": "222",
    "asset": "BTC", "timeframe": "5m", "db_path": "/tmp/lab/x.db",
    "base_url": _BASE, "cycle_sleep_seconds": 1.5, "max_captures": 100, "duration_seconds": 240.0,
}


def test_build_runner_argv_uses_ratified_cli_shape():
    argv = build_runner_argv(_PARAMS, python_exe="/venv/bin/python3")
    assert argv[:3] == ["/venv/bin/python3", "-m", "tools.pm_book_diag_runner"]
    for flag, val in (("--market-slug", "btc-updown-5m-123"), ("--yes-token-id", "111"),
                      ("--no-token-id", "222"), ("--asset", "BTC"), ("--timeframe", "5m"),
                      ("--db-path", "/tmp/lab/x.db"), ("--base-url", _BASE),
                      ("--cycle-sleep-seconds", "1.5"), ("--max-captures", "100"),
                      ("--duration-seconds", "240.0")):
        assert flag in argv and argv[argv.index(flag) + 1] == val


def test_runner_argv_has_no_discovery_args():
    argv = build_runner_argv(_PARAMS, python_exe="/venv/bin/python3")
    joined = " ".join(argv).lower()
    for banned in ("condition", "gamma", "outcome", "expiry", "/markets"):
        assert banned not in joined


# ===========================================================================
# 6. JSONL manifest
# ===========================================================================

def test_manifest_appends_one_line_per_record(tmp_path):
    path = str(tmp_path / "manifest.jsonl")
    w = JsonlManifestWriter(path)
    w.append({"event_type": "skip", "market_slug": "a"})
    w.append({"event_type": "launch", "market_slug": "b"})
    with open(path) as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    assert len(lines) == 2
    assert json.loads(lines[0])["event_type"] == "skip"


def test_manifest_has_monotonic_event_id(tmp_path):
    path = str(tmp_path / "m.jsonl")
    w = JsonlManifestWriter(path)
    for i in range(3):
        w.append({"event_type": "x"})
    ids = [json.loads(ln)["event_id"] for ln in open(path).read().splitlines() if ln.strip()]
    assert ids == [1, 2, 3]


def test_manifest_never_rewritten(tmp_path):
    path = str(tmp_path / "m.jsonl")
    w = JsonlManifestWriter(path)
    prefixes = []
    for i in range(3):
        w.append({"event_type": "x", "n": i})
        prefixes.append(open(path, "rb").read())
    # each earlier file content is a strict prefix of the later (append-only, never rewritten)
    assert prefixes[0] == prefixes[1][:len(prefixes[0])]
    assert prefixes[1] == prefixes[2][:len(prefixes[1])]


def test_manifest_flush_fsync_called_per_append(tmp_path):
    path = str(tmp_path / "m.jsonl")
    fsync_calls = []
    w = JsonlManifestWriter(path, fsync_fn=lambda fd: fsync_calls.append(fd))
    w.append({"event_type": "x"})
    w.append({"event_type": "y"})
    assert len(fsync_calls) == 2


def test_manifest_survives_simulated_interruption(tmp_path):
    path = str(tmp_path / "m.jsonl")
    w = JsonlManifestWriter(path)
    w.append({"event_type": "a"})
    w.append({"event_type": "b"})
    # simulate interruption: do NOT close w; a fresh reader must still see both flushed records
    lines = [ln for ln in open(path).read().splitlines() if ln.strip()]
    assert len(lines) == 2


# ===========================================================================
# 7. _terminate_child cleanup
# ===========================================================================

class _FakeChild:
    def __init__(self, dies_on_terminate):
        self.returncode = None
        self._dies_on_terminate = dies_on_terminate
        self.terminated = False
        self.killed = False

    def terminate(self):
        self.terminated = True
        if self._dies_on_terminate:
            self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9


@pytest.mark.asyncio
async def test_child_graceful_exit_recorded():
    child = _FakeChild(dies_on_terminate=True)
    clock = _Clock(0.0)
    sleep_fn, _ = _sleeps_recorder()
    status = await _terminate_child(child, cleanup_timeout_seconds=5.0,
                                    sleep_fn=sleep_fn, now_fn=clock)
    assert child.terminated and not child.killed
    assert status["killed"] is False and status["returncode"] == -15


@pytest.mark.asyncio
async def test_child_killed_after_timeout():
    child = _FakeChild(dies_on_terminate=False)  # never dies on terminate

    # clock advances past the cleanup deadline so the wait loop gives up -> kill
    vals = iter([0.0, 1.0, 2.0, 99.0, 99.0, 99.0])
    def now_fn():
        return next(vals)

    async def sleep_fn(_):
        pass

    status = await _terminate_child(child, cleanup_timeout_seconds=5.0,
                                    sleep_fn=sleep_fn, now_fn=now_fn)
    assert child.terminated and child.killed
    assert status["killed"] is True and status["returncode"] == -9


@pytest.mark.asyncio
async def test_no_orphan_after_terminate_both_paths():
    for dies in (True, False):
        child = _FakeChild(dies_on_terminate=dies)
        vals = iter([0.0, 1.0, 99.0, 99.0, 99.0])
        async def sleep_fn(_):
            pass
        await _terminate_child(child, cleanup_timeout_seconds=2.0,
                               sleep_fn=sleep_fn, now_fn=lambda: next(vals))
        assert child.returncode is not None  # never left running


# ===========================================================================
# 8. Supervisor loop behavior
# ===========================================================================

@pytest.mark.asyncio
async def test_programmer_errors_fail_fast(tmp_path):
    manifest = JsonlManifestWriter(str(tmp_path / "m.jsonl"))
    clock = _Clock(_T0)
    sleep_fn, _ = _sleeps_recorder()
    good = _base_supervisor_kwargs(
        lookup_fn=_auto_valid_lookup(), launch_fn=_launcher(),
        manifest=manifest, now_epoch_fn=clock, sleep_fn=sleep_fn)

    bad = [
        {**good, "asset": ""},
        {**good, "timeframe": ""},
        {**good, "base_url": ""},
        {**good, "db_dir": ""},
        {**good, "cycle_sleep_seconds": 0.5},   # < floor 1.0
        {**good, "inter_window_cooldown_seconds": 1.0},  # < floor 5.0
        {**good, "per_window_max_captures": 0},
        {**good, "expiry_buffer_seconds": -1.0},
        {**good, "max_windows": None, "max_total_captures": None, "max_total_duration_seconds": None},
    ]
    for kw in bad:
        with pytest.raises(ValueError):
            await run_window_supervisor(**kw)


@pytest.mark.asyncio
async def test_explicit_tokens_passed_to_runner(tmp_path):
    manifest = JsonlManifestWriter(str(tmp_path / "m.jsonl"))
    clock = _Clock(_T0)
    sleep_fn, _ = _sleeps_recorder()
    launch = _launcher()
    await run_window_supervisor(**_base_supervisor_kwargs(
        max_windows=1, lookup_fn=_auto_valid_lookup(yes="777", no="888"),
        launch_fn=launch, manifest=manifest, now_epoch_fn=clock, sleep_fn=sleep_fn))
    assert len(launch.params_log) == 1
    p = launch.params_log[0]
    assert p["yes_token_id"] == "777" and p["no_token_id"] == "888"
    assert p["asset"] == "BTC" and p["timeframe"] == "5m"


@pytest.mark.asyncio
async def test_runner_receives_no_discovery_args(tmp_path):
    manifest = JsonlManifestWriter(str(tmp_path / "m.jsonl"))
    clock = _Clock(_T0)
    sleep_fn, _ = _sleeps_recorder()
    launch = _launcher()
    await run_window_supervisor(**_base_supervisor_kwargs(
        max_windows=1, lookup_fn=_auto_valid_lookup(),
        launch_fn=launch, manifest=manifest, now_epoch_fn=clock, sleep_fn=sleep_fn))
    p = launch.params_log[0]
    allowed = {"market_slug", "yes_token_id", "no_token_id", "asset", "timeframe",
               "db_path", "base_url", "cycle_sleep_seconds", "max_captures",
               "duration_seconds", "out_path"}
    assert set(p.keys()) <= allowed
    for banned in ("condition_id", "expiry_epoch", "tokens", "outcome"):
        assert banned not in p


@pytest.mark.asyncio
async def test_market_closed_window_skipped(tmp_path):
    manifest = JsonlManifestWriter(str(tmp_path / "m.jsonl"))
    clock = _Clock(_T0)
    sleep_fn, _ = _sleeps_recorder()
    launch = _launcher()
    res = await run_window_supervisor(**_base_supervisor_kwargs(
        max_windows=5, lookup_fn=_auto_valid_lookup(closed=True),
        launch_fn=launch, manifest=manifest, now_epoch_fn=clock, sleep_fn=sleep_fn))
    assert len(launch.params_log) == 0  # nothing launched
    assert res["stop_reason"] == "no_fresh_window"


@pytest.mark.asyncio
async def test_same_window_not_launched_twice_in_one_supervisor_run(tmp_path):
    manifest = JsonlManifestWriter(str(tmp_path / "m.jsonl"))
    clock = _Clock(_T0)  # frozen time -> candidates repeat
    sleep_fn, _ = _sleeps_recorder()
    launch = _launcher()
    await run_window_supervisor(**_base_supervisor_kwargs(
        max_windows=99, max_total_captures=10_000,
        lookup_fn=_auto_valid_lookup(), launch_fn=launch,
        manifest=manifest, now_epoch_fn=clock, sleep_fn=sleep_fn))
    slugs = [p["market_slug"] for p in launch.params_log]
    assert len(slugs) == len(set(slugs)), "no slug may be launched twice"


@pytest.mark.asyncio
async def test_max_windows_bounds_loop(tmp_path):
    manifest = JsonlManifestWriter(str(tmp_path / "m.jsonl"))
    clock = _Clock(_T0)
    sleep_fn, _ = _sleeps_recorder()
    launch = _launcher()
    res = await run_window_supervisor(**_base_supervisor_kwargs(
        max_windows=2, lookup_fn=_auto_valid_lookup(),
        launch_fn=launch, manifest=manifest, now_epoch_fn=clock, sleep_fn=sleep_fn))
    assert len(launch.params_log) == 2
    assert res["windows_launched"] == 2
    assert res["stop_reason"] == "max_windows"


@pytest.mark.asyncio
async def test_max_total_captures_bounds_loop(tmp_path):
    manifest = JsonlManifestWriter(str(tmp_path / "m.jsonl"))
    clock = _Clock(_T0)
    sleep_fn, _ = _sleeps_recorder()
    launch = _launcher(result={"exit_code": 0, "captures": 60, "stop_reason": "max_captures",
                               "db_file_exists": True, "db_row_count": 60})
    res = await run_window_supervisor(**_base_supervisor_kwargs(
        max_windows=99, max_total_captures=100,
        lookup_fn=_auto_valid_lookup(), launch_fn=launch,
        manifest=manifest, now_epoch_fn=clock, sleep_fn=sleep_fn))
    assert len(launch.params_log) == 2   # 60 + 60 = 120 >= 100, stops after 2
    assert res["stop_reason"] == "max_total_captures"


@pytest.mark.asyncio
async def test_inter_window_cooldown_enforced(tmp_path):
    manifest = JsonlManifestWriter(str(tmp_path / "m.jsonl"))
    clock = _Clock(_T0)
    sleep_fn, sleeps = _sleeps_recorder()
    await run_window_supervisor(**_base_supervisor_kwargs(
        max_windows=2, lookup_fn=_auto_valid_lookup(),
        launch_fn=_launcher(), manifest=manifest, now_epoch_fn=clock, sleep_fn=sleep_fn))
    assert sleeps, "cooldown must be applied"
    assert all(s == COOLDOWN_FLOOR_SECONDS for s in sleeps)


@pytest.mark.asyncio
async def test_no_fresh_window_stops_cleanly(tmp_path):
    manifest = JsonlManifestWriter(str(tmp_path / "m.jsonl"))
    clock = _Clock(_T0)  # frozen -> only 3 candidates, all closed
    sleep_fn, _ = _sleeps_recorder()
    res = await run_window_supervisor(**_base_supervisor_kwargs(
        max_windows=99, lookup_fn=_auto_valid_lookup(closed=True),
        launch_fn=_launcher(), manifest=manifest, now_epoch_fn=clock, sleep_fn=sleep_fn))
    assert res["stop_reason"] == "no_fresh_window"


@pytest.mark.asyncio
async def test_nonzero_runner_exit_records_failure_and_continues(tmp_path):
    path = str(tmp_path / "m.jsonl")
    manifest = JsonlManifestWriter(path)
    clock = _Clock(_T0)
    sleep_fn, _ = _sleeps_recorder()

    # first window fails (nonzero exit, partial/missing db), second succeeds
    def rfn(params):
        if params["market_slug"].endswith(str(_T0)):
            return {"exit_code": 1, "captures": 0, "stop_reason": "runner_error",
                    "db_file_exists": False, "db_row_count": None}
        return {"exit_code": 0, "captures": 100, "stop_reason": "max_captures",
                "db_file_exists": True, "db_row_count": 100}

    launch = _launcher(result_fn=rfn)
    res = await run_window_supervisor(**_base_supervisor_kwargs(
        max_windows=2, lookup_fn=_auto_valid_lookup(), launch_fn=launch,
        manifest=manifest, now_epoch_fn=clock, sleep_fn=sleep_fn))
    assert len(launch.params_log) == 2  # did not abort after the failure
    # manifest must record the failure detail
    recs = [json.loads(ln) for ln in open(path).read().splitlines() if ln.strip()]
    results = [r for r in recs if r["event_type"] == "window_result"]
    failed = [r for r in results if r.get("exit_code") == 1]
    assert failed and failed[0]["db_file_exists"] is False
    assert failed[0]["stop_reason"] == "runner_error"


@pytest.mark.asyncio
async def test_manifest_one_jsonl_line_per_decision(tmp_path):
    path = str(tmp_path / "m.jsonl")
    manifest = JsonlManifestWriter(path)
    clock = _Clock(_T0)
    sleep_fn, _ = _sleeps_recorder()
    await run_window_supervisor(**_base_supervisor_kwargs(
        max_windows=1, lookup_fn=_auto_valid_lookup(), launch_fn=_launcher(),
        manifest=manifest, now_epoch_fn=clock, sleep_fn=sleep_fn))
    recs = [json.loads(ln) for ln in open(path).read().splitlines() if ln.strip()]
    types = [r["event_type"] for r in recs]
    assert "launch" in types and "window_result" in types
    assert "supervisor_stop" in types
    # monotonic event_id across all lines
    assert [r["event_id"] for r in recs] == list(range(1, len(recs) + 1))


@pytest.mark.asyncio
async def test_no_live_api_in_tests_requires_injected_seams():
    # run_window_supervisor must REQUIRE lookup_fn and launch_fn (no hidden network default)
    with pytest.raises(TypeError):
        await run_window_supervisor(asset="BTC", timeframe="5m", base_url=_BASE, db_dir="/tmp",
                                    cycle_sleep_seconds=1.5, per_window_max_captures=10,
                                    expiry_buffer_seconds=30.0,
                                    inter_window_cooldown_seconds=COOLDOWN_FLOOR_SECONDS,
                                    expected_capture_span_seconds=0.3, launch_overhead_seconds=2.0,
                                    max_windows=1)  # missing lookup_fn/launch_fn/manifest/clock


# ===========================================================================
# 9. Source-scan policy (asymmetric)
# ===========================================================================

def test_supervisor_allows_lookup_terms():
    import tools.pm_book_window_supervisor as m
    src = open(m.__file__, "r", encoding="utf-8").read().lower()
    # discovery legitimately lives in the supervisor
    assert "gamma" in src or "/markets" in src


def test_runner_remains_discovery_free():
    import tools.pm_book_diag_runner as r
    src = open(r.__file__, "r", encoding="utf-8").read().lower()
    for banned in ("gamma", "metadata", "/markets"):
        assert banned not in src, f"runner must stay discovery-free, found {banned!r}"


def test_supervisor_forbidden_trading_surfaces_absent():
    import tools.pm_book_window_supervisor as m
    src = open(m.__file__, "r", encoding="utf-8").read()
    low = src.lower()
    for banned in ("reference_book_pairs", "stale_lag", "proxy_reference_basket",
                   "math.log", "implied", "candidate", "actionability",
                   "profitability", "profit_", " edge"):
        assert banned not in low, f"forbidden term {banned!r} present"
    # import/surface scan for trading/capital/wallet modules
    import_lines = "\n".join(ln for ln in src.splitlines()
                             if ln.strip().startswith(("import ", "from "))).lower()
    for forbidden in ("wallet", "signing", "execution", "trading", "routing", "capital",
                      "scout", "council"):
        assert forbidden not in import_lines, f"must not import {forbidden!r}"
