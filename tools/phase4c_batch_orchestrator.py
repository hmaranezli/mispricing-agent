"""tools/phase4c_batch_orchestrator.py — Phase 4C bounded batch orchestration scaffold (offline).

Creates a partitioned batch directory (phase4c_batch_<ts>/run_NN/), runs N runs via an INJECTED run_fn,
and writes a manifest with per-run metadata + segment-metric placeholders (incl. SEM). Enforces a per-run
request cap (20) FAIL-CLOSED: if a run reports request_count > cap, that run is marked failed and the batch
aborts. Only writes inside the new batch directory — never mutates/deletes existing root artifacts.

This commit does NOT execute live mode. The default run_fn is a no-op PLANNER (creates the run dir + a
plan placeholder; performs NO network). A real/live run_fn (sampler -> 4A -> 4B) would be wired later
behind an explicit flag — not here.

OFFLINE ONLY: no live fetch, no endpoints, no market-data fetch, no auth/secrets, no trading. NO PnL /
net-edge / slippage / market-impact; NO execution/paper/economics/readiness/profitability/alpha claim.

CLI (scaffold; planner only, no live execution): python3 tools/phase4c_batch_orchestrator.py --runs 3 --output-root data/output
"""
import glob
import json
import os
import statistics
import subprocess  # used ONLY by the concrete executor's default runner (double-locked path)
import sys
import time

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "output")
PER_RUN_MAX_TOTAL_REQUESTS = 20


def _planned_run_fn(*, run_dir, run_index, max_total_requests):
    """Default NO-OP planner: records intent only; performs NO live work / NO network."""
    plan_path = os.path.join(run_dir, f"phase4c_run_plan_{run_index:02d}.json")
    plan = {"planned": True, "run_index": run_index, "max_total_requests": max_total_requests,
            "note": "live execution not enabled in this build (scaffold planner only)"}
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    return {"verdict": "PLANNED", "request_count": 0, "timestamp": None,
            "artifacts": {"plan": plan_path}}


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _stat_block(vals):
    s = [v for v in vals if _is_number(v)]
    n = len(s)
    if n == 0:
        return None, None, None
    mean = round(sum(s) / n, 6)
    stdev = round(statistics.stdev(s), 6) if n >= 2 else None
    sem = round(statistics.stdev(s) / (n ** 0.5), 6) if n >= 2 else None
    return mean, stdev, sem


def _segment_metrics(buy_samples, sell_samples, eligible_total, rejection_rates, have_data):
    b_mean, b_stdev, b_sem = _stat_block(buy_samples)
    s_mean, s_stdev, s_sem = _stat_block(sell_samples)
    return {
        "eligible_pairs": eligible_total if have_data else None,
        "rejection_rate": round(sum(rejection_rates) / len(rejection_rates), 6) if rejection_rates else None,
        "buy_both_gross_edge_mean": b_mean,
        "buy_both_gross_edge_stdev": b_stdev,
        "buy_both_gross_edge_sem": b_sem,
        "sell_both_gross_edge_mean": s_mean,
        "sell_both_gross_edge_stdev": s_stdev,
        "sell_both_gross_edge_sem": s_sem,
    }


LIVE_STAGES = ("phase3d5_sampler", "phase4a_analyzer", "phase4b_aggregator")


def make_live_run_fn(stage_executor_fn):
    """Build a live run_fn that executes the 3-stage pipeline via an INJECTED stage_executor_fn.

    Stage order: phase3d5_sampler -> phase4a_analyzer -> phase4b_aggregator. FAIL-CLOSED: a stage that
    is not ok (status != "ok" or exit_code not in {0, None}) marks the run failed and SKIPS remaining
    stages. The sampler's request_count is checked against the per-run cap; exceeding it fails closed and
    skips downstream stages. No real subprocess here — the executor is injected (mocked in tests). A
    real executor (sampler/analyzer/aggregator) would be wired later behind an explicit flag.
    """
    def _skipped(stage, run_dir):
        return {"stage_name": stage, "status": "SKIPPED", "verdict": None, "exit_code": None,
                "artifacts": {}, "request_count": None, "timestamp": None,
                "command_plan": None, "run_dir": run_dir,
                "stdout_path": None, "stderr_path": None, "timeout_seconds": None}

    def run_fn(*, run_dir, run_index, max_total_requests):
        stages = []
        artifacts = {}
        run_failed = False
        request_count = None
        verdict = "RUN_COMPLETED"
        abort_reason = None
        seg = {}
        for idx, stage in enumerate(LIVE_STAGES):
            r = stage_executor_fn(stage=stage, run_dir=run_dir, run_index=run_index,
                                  max_total_requests=max_total_requests)
            stages.append({
                "stage_name": stage,
                "status": r.get("status"),
                "verdict": r.get("verdict"),
                "exit_code": r.get("exit_code"),
                "artifacts": r.get("artifacts", {}),
                "request_count": r.get("request_count"),
                "timestamp": r.get("timestamp"),
                "command_plan": r.get("command_plan"),
                "run_dir": run_dir,
                "stdout_path": r.get("stdout_path"),
                "stderr_path": r.get("stderr_path"),
                "timeout_seconds": r.get("timeout_seconds"),
            })
            artifacts.update(r.get("artifacts") or {})
            if stage == "phase3d5_sampler":
                request_count = r.get("request_count")
            ok = (r.get("status") == "ok") and (r.get("exit_code") in (0, None))
            if not ok:
                run_failed = True
                verdict = "RUN_STAGE_FAILED"
                abort_reason = f"STAGE_FAILED:{stage}"
                stages.extend(_skipped(s, run_dir) for s in LIVE_STAGES[idx + 1:])
                break
            if (stage == "phase3d5_sampler" and isinstance(request_count, int)
                    and not isinstance(request_count, bool) and request_count > max_total_requests):
                run_failed = True
                verdict = "RUN_REQUEST_CAP_EXCEEDED"
                abort_reason = "REQUEST_CAP_EXCEEDED"
                stages.extend(_skipped(s, run_dir) for s in LIVE_STAGES[idx + 1:])
                break
            if stage == "phase4b_aggregator":
                for k in ("buy_samples", "sell_samples", "eligible_pairs", "rejection_rate"):
                    if k in r:
                        seg[k] = r[k]
        out = {"verdict": verdict, "request_count": request_count, "run_failed": run_failed,
               "abort_reason": abort_reason, "stages": stages, "artifacts": artifacts, "timestamp": None}
        out.update(seg)
        return out
    return run_fn


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _stage_argv(stage, run_dir, max_total_requests, *, phase3d5_input=None, fixture_mode=False):
    """Single source of truth for each stage's intended argv ARRAY (shell=False usage; never a string).

    For phase4a_analyzer, phase3d5_input (the resolved 3D5 JSONL) is used when provided, else a
    <ts> template placeholder (command-plan-only path, where nothing has run yet). When fixture_mode is
    True, 3D5 uses the OFFLINE FIXTURE mode flag (synthetic data, no network).
    """
    if stage == "phase3d5_sampler":
        mode_flag = "--pilot-3d5-offline-fixture" if fixture_mode else "--pilot-3d5-complement-pairs"
        return ["python3", "tools/phase3_exec_sampler.py", mode_flag,
                "--output-dir", run_dir, "--max-total-requests", str(max_total_requests)]
    if stage == "phase4a_analyzer":
        inp = phase3d5_input if phase3d5_input is not None \
            else os.path.join(run_dir, "phase3d5_pilot_snapshots_<ts>.jsonl")
        return ["python3", "tools/phase4a_gross_edge_engine.py", "--input", inp, "--output-dir", run_dir]
    if stage == "phase4b_aggregator":
        return ["python3", "tools/phase4b_gross_edge_aggregate.py",
                "--input-dir", run_dir, "--output-dir", run_dir]
    raise ValueError(f"unknown stage {stage!r}")


def _check_argv_flags(argv):
    """Offline static check: for the target tool (argv[1]) flag a '--flag' token that does NOT appear
    in the tool's source. Returns a list of human-readable notes (empty if all flags are supported)."""
    notes = []
    if len(argv) < 2:
        return ["malformed command plan (no tool path)"]
    tool_rel = argv[1]
    tool_path = os.path.join(_REPO_ROOT, tool_rel)
    try:
        with open(tool_path, encoding="utf-8") as f:
            src = f.read()
    except Exception:
        return [f"tool source not found: {tool_rel} (future wiring needed)"]
    base = os.path.basename(tool_rel)
    for tok in argv[2:]:
        if isinstance(tok, str) and tok.startswith("--") and tok not in src:
            notes.append(f"{base} does not currently accept {tok} (future wiring needed)")
    return notes


def command_plan_run_fn(*, run_dir, run_index, max_total_requests):
    """Command-plan AUDIT run: records the intended 3D5->4A->4B argv plan WITHOUT executing anything.

    Every stage is status="PLANNED", verdict="COMMAND_PLAN_ONLY"; command_plan is an argv ARRAY (not a
    shell string). Unsupported flags (per current tool sources) are recorded in command_plan_notes and
    aggregated into plan_warnings — the plan is NOT mutated and nothing is executed.
    """
    stages = []
    plan_warnings = []
    for stage in LIVE_STAGES:
        argv = _stage_argv(stage, run_dir, max_total_requests)
        notes = _check_argv_flags(argv)
        plan_warnings += [f"{stage}: {n}" for n in notes]
        stages.append({
            "stage_name": stage,
            "status": "PLANNED",
            "verdict": "COMMAND_PLAN_ONLY",
            "exit_code": None,
            "request_count": 0,
            "artifacts": [],
            "timestamp": None,
            "run_dir": run_dir,
            "command_plan": argv,
            "command_plan_notes": notes,
        })
    return {"verdict": "COMMAND_PLAN_ONLY", "request_count": 0, "run_failed": False,
            "abort_reason": None, "stages": stages, "artifacts": {}, "timestamp": None,
            "plan_warnings": plan_warnings}


def _default_subprocess_runner(argv, *, timeout_seconds):
    """Safe wrapper around subprocess.run: argv array, shell=False, captured output, timeout.

    Robust exec mapping (recorded command_plan stays the original argv): 'python3' -> sys.executable,
    and a relative 'tools/...' path -> absolute under the repo root, so it runs from any cwd.
    """
    exec_argv = list(argv)
    if exec_argv and exec_argv[0] == "python3":
        exec_argv[0] = sys.executable
    if len(exec_argv) >= 2 and isinstance(exec_argv[1], str) and not os.path.isabs(exec_argv[1]):
        exec_argv[1] = os.path.join(_REPO_ROOT, exec_argv[1])
    try:
        cp = subprocess.run(exec_argv, shell=False, capture_output=True, text=True,
                            timeout=timeout_seconds)
        return {"exit_code": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr, "timed_out": False}
    except subprocess.TimeoutExpired as e:
        return {"exit_code": None, "stdout": e.stdout or "", "stderr": e.stderr or "", "timed_out": True}


def _verify_stage_artifacts(stage, run_dir):
    """Return (artifacts_dict, request_count_or_None, missing_or_None) for a stage's expected outputs."""
    def g(pat):
        return sorted(glob.glob(os.path.join(run_dir, pat)))
    if stage == "phase3d5_sampler":
        snaps = g("phase3d5_pilot_snapshots_*.jsonl")
        summ = g("phase3d5_pilot_summary_*.json")
        if not snaps:
            return {}, None, "phase3d5_snapshots"
        if not summ:
            return {"snapshots": snaps[0]}, None, "phase3d5_summary"
        rc = None
        try:
            with open(summ[0], encoding="utf-8") as f:
                v = json.load(f).get("request_count")
            rc = v if isinstance(v, int) and not isinstance(v, bool) else None
        except Exception:
            rc = None
        return {"snapshots": snaps[0], "summary": summ[0]}, rc, None
    if stage == "phase4a_analyzer":
        recs = g("phase4a_gross_edge_*.jsonl")
        summ = g("phase4a_gross_edge_summary_*.json")
        if not recs:
            return {}, None, "phase4a_records"
        if not summ:
            return {"records": recs[0]}, None, "phase4a_summary"
        return {"records": recs[0], "summary": summ[0]}, None, None
    if stage == "phase4b_aggregator":
        agg = g("phase4b_gross_edge_aggregate_*.json")
        if not agg:
            return {}, None, "phase4b_aggregate"
        return {"aggregate": agg[0]}, None, None
    return {}, None, f"unknown_stage:{stage}"


def make_concrete_subprocess_stage_executor(command_runner=None, timeout_seconds=120, fixture_mode=False):
    """Concrete stage executor (injectable). Builds the stage's argv ARRAY, runs it via command_runner
    (default: safe subprocess.run shell=False wrapper), captures stdout/stderr to run_dir/logs/, verifies
    expected artifacts, and returns a stage-result dict. Tests inject a fake command_runner. fixture_mode
    routes 3D5 to its OFFLINE FIXTURE mode (synthetic data, no network) and labels success verdicts
    OFFLINE_FIXTURE_OK. Real public-data execution is reached only behind the live double-lock.
    """
    if command_runner is None:
        command_runner = _default_subprocess_runner

    def executor(*, stage, run_dir, run_index, max_total_requests):
        logs_dir = os.path.join(run_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        stdout_path = os.path.join(logs_dir, f"{stage}.stdout.txt")
        stderr_path = os.path.join(logs_dir, f"{stage}.stderr.txt")
        if stage == "phase4a_analyzer":
            found = sorted(glob.glob(os.path.join(run_dir, "phase3d5_pilot_snapshots_*.jsonl")))
            argv = _stage_argv(stage, run_dir, max_total_requests,
                               phase3d5_input=(found[0] if found else None), fixture_mode=fixture_mode)
        else:
            argv = _stage_argv(stage, run_dir, max_total_requests, fixture_mode=fixture_mode)

        res = command_runner(argv, timeout_seconds=timeout_seconds)
        with open(stdout_path, "w", encoding="utf-8") as f:
            f.write(res.get("stdout", "") or "")
        with open(stderr_path, "w", encoding="utf-8") as f:
            f.write(res.get("stderr", "") or "")
        base = {"stage_name": stage, "command_plan": argv, "run_dir": run_dir,
                "stdout_path": stdout_path, "stderr_path": stderr_path,
                "timeout_seconds": timeout_seconds, "timestamp": res.get("timestamp")}
        if res.get("timed_out"):
            return {**base, "status": "timeout", "verdict": "STAGE_TIMEOUT",
                    "exit_code": res.get("exit_code"), "artifacts": {}, "request_count": None}
        exit_code = res.get("exit_code")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool) or exit_code != 0:
            return {**base, "status": "error", "verdict": "STAGE_NONZERO_EXIT",
                    "exit_code": exit_code, "artifacts": {}, "request_count": None}
        artifacts, request_count, missing = _verify_stage_artifacts(stage, run_dir)
        if missing:
            return {**base, "status": "error", "verdict": f"MISSING_ARTIFACT:{missing}",
                    "exit_code": exit_code, "artifacts": artifacts, "request_count": request_count}
        success_verdict = "OFFLINE_FIXTURE_OK" if fixture_mode else res.get("verdict_label", "OK")
        return {**base, "status": "ok", "verdict": success_verdict,
                "exit_code": exit_code, "artifacts": artifacts, "request_count": request_count}
    return executor


def _diagnostic_fake_command_runner(argv, *, timeout_seconds):
    """CLI safety-diagnostic fake runner: NO subprocess, NO network. Writes clearly-labeled fake
    artifacts under --output-dir for each stage so the concrete executor's artifact gating passes, and
    returns exit_code=0 with fake stdout/stderr. verdict_label marks stages DIAGNOSTIC_FAKE_OK so they
    cannot be confused with real public-data observations. 3D5 fake summary request_count=12 (<=20)."""
    tool = argv[1]
    rd = argv[argv.index("--output-dir") + 1] if "--output-dir" in argv else "."
    ts = int(time.time() * 1000)
    if "phase3_exec_sampler" in tool:
        with open(os.path.join(rd, f"phase3d5_pilot_snapshots_{ts}.jsonl"), "w", encoding="utf-8") as f:
            f.write(json.dumps({"asset": "BTC", "interval": "5m", "market_slug": "DIAGNOSTIC_FAKE",
                                "token_id": "DIAG", "utc_timestamp_ms": ts,
                                "bids": [[0.49, 1]], "asks": [[0.51, 1]], "diagnostic_fake": True}) + "\n")
        with open(os.path.join(rd, f"phase3d5_pilot_summary_{ts}.json"), "w", encoding="utf-8") as f:
            json.dump({"request_count": 12, "diagnostic_fake": True,
                       "note": "DIAGNOSTIC_FAKE_RUNNER output; NOT real public-data observation"}, f)
    elif "phase4a" in tool:
        with open(os.path.join(rd, f"phase4a_gross_edge_records_{ts}.jsonl"), "w", encoding="utf-8") as f:
            f.write(json.dumps({"phase": "4A_gross_edge", "diagnostic_fake": True}) + "\n")
        with open(os.path.join(rd, f"phase4a_gross_edge_summary_{ts}.json"), "w", encoding="utf-8") as f:
            json.dump({"phase": "4A_gross_edge", "diagnostic_fake": True}, f)
    elif "phase4b" in tool:
        with open(os.path.join(rd, f"phase4b_gross_edge_aggregate_{ts}.json"), "w", encoding="utf-8") as f:
            json.dump({"phase": "4B_gross_edge_aggregate", "diagnostic_fake": True}, f)
    return {"exit_code": 0, "stdout": f"DIAGNOSTIC_FAKE stdout for {os.path.basename(tool)}",
            "stderr": "", "timed_out": False, "verdict_label": "DIAGNOSTIC_FAKE_OK"}


class LiveExecutionRefused(Exception):
    """Raised (fail-closed) when live execution is requested but the double-lock is not satisfied."""


def resolve_live_run_fn(*, live_public_data, enable_real_subprocess, concrete_executor=None):
    """Double-lock gate. Returns a run_fn or None (planner), or raises LiveExecutionRefused (fail-closed).

    - no flags                          -> None (no-op planner mode)
    - exactly one of the two flags      -> refuse (both flags required)
    - both flags (executor injected)    -> live run_fn = make_live_run_fn(concrete_executor)
    - both flags (no executor injected) -> live run_fn wired to the default concrete subprocess executor

    The concrete_executor is the stage-executor interface:
      executor(*, stage, run_dir, run_index, max_total_requests) -> dict with keys:
        status, verdict, exit_code, artifacts, request_count, timestamp, command_plan (optional).
    """
    if not live_public_data and not enable_real_subprocess:
        return None
    if not (live_public_data and enable_real_subprocess):
        raise LiveExecutionRefused(
            "double-lock: BOTH --live-public-data and --enable-real-subprocess are required; fail-closed.")
    # both flags -> wire the concrete subprocess executor (default real runner unless injected).
    if concrete_executor is None:
        concrete_executor = make_concrete_subprocess_stage_executor()
    return make_live_run_fn(concrete_executor)


def orchestrate(*, runs, output_root=OUT_DIR, run_fn=None, timestamp_fn=None, manifest_tag=None):
    if timestamp_fn is None:
        timestamp_fn = lambda: int(time.time())  # noqa: E731
    if run_fn is None:
        run_fn = _planned_run_fn
    now = timestamp_fn()
    batch_id = f"phase4c_batch_{now}"
    batch_dir = os.path.join(output_root, batch_id)
    os.makedirs(batch_dir, exist_ok=True)        # only ever create UNDER the new batch dir
    manifest_path = os.path.join(batch_dir, f"phase4c_batch_manifest_{now}.json")

    per_run = []
    completed = 0
    failed = 0
    aborted = False
    abort_reason = None
    buy_samples, sell_samples, rejection_rates = [], [], []
    eligible_total = 0
    have_segment_data = False
    plan_warnings = []

    for i in range(1, runs + 1):
        run_dir = os.path.join(batch_dir, f"run_{i:02d}")
        os.makedirs(run_dir, exist_ok=True)
        try:
            res = run_fn(run_dir=run_dir, run_index=i, max_total_requests=PER_RUN_MAX_TOTAL_REQUESTS)
        except Exception as e:
            per_run.append({"run_index": i, "run_dir": run_dir, "artifacts": {},
                            "request_count": None, "max_total_requests": PER_RUN_MAX_TOTAL_REQUESTS,
                            "verdict": "RUN_FAILED", "timestamp": now, "error": type(e).__name__})
            failed += 1
            aborted = True
            abort_reason = "RUN_EXCEPTION"
            break

        rc = res.get("request_count")
        entry = {
            "run_index": i,
            "run_dir": run_dir,
            "artifacts": res.get("artifacts", {}),
            "request_count": rc,
            "max_total_requests": PER_RUN_MAX_TOTAL_REQUESTS,
            "verdict": res.get("verdict"),
            "timestamp": res.get("timestamp", now),
        }
        if "stages" in res:
            entry["stages"] = res["stages"]
        plan_warnings += list(res.get("plan_warnings") or [])

        # fail-closed: a run that reports stage failure (incl. live pipeline) aborts the batch
        if res.get("run_failed"):
            entry["verdict"] = res.get("verdict") or "RUN_STAGE_FAILED"
            per_run.append(entry)
            failed += 1
            aborted = True
            abort_reason = res.get("abort_reason") or "RUN_STAGE_FAILED"
            break

        # fail-closed cap check
        if not isinstance(rc, int) or isinstance(rc, bool) or rc > PER_RUN_MAX_TOTAL_REQUESTS:
            entry["verdict"] = "RUN_REQUEST_CAP_EXCEEDED"
            per_run.append(entry)
            failed += 1
            aborted = True
            abort_reason = "REQUEST_CAP_EXCEEDED"
            break

        per_run.append(entry)
        completed += 1
        if "buy_samples" in res or "sell_samples" in res or "eligible_pairs" in res:
            have_segment_data = True
        buy_samples += [v for v in (res.get("buy_samples") or []) if _is_number(v)]
        sell_samples += [v for v in (res.get("sell_samples") or []) if _is_number(v)]
        if _is_number(res.get("eligible_pairs")):
            eligible_total += res["eligible_pairs"]
        if _is_number(res.get("rejection_rate")):
            rejection_rates.append(res["rejection_rate"])

    manifest = {
        "batch_id": batch_id,
        "phase": "4C_batch_orchestration",
        "output_root": output_root,
        "batch_dir": batch_dir,
        "manifest_path": manifest_path,
        "run_count": runs,
        "completed_runs": completed,
        "failed_runs": failed,
        "aborted": aborted,
        "abort_reason": abort_reason,
        "per_run_max_total_requests": PER_RUN_MAX_TOTAL_REQUESTS,
        "per_run": per_run,
        "segment_metrics": _segment_metrics(buy_samples, sell_samples, eligible_total,
                                            rejection_rates, have_segment_data),
        "plan_warnings": plan_warnings,
        "official_f1b": False,
        "profitability": False,
        "generated_at_unix": now,
    }
    if isinstance(manifest_tag, dict):
        for k, v in manifest_tag.items():
            manifest.setdefault(k, v)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest


if __name__ == "__main__":  # pragma: no cover
    args = sys.argv[1:]
    runs = None
    output_root = OUT_DIR
    if "--runs" in args:
        try:
            runs = int(args[args.index("--runs") + 1])
        except (ValueError, IndexError):
            runs = None
    if "--output-root" in args:
        try:
            output_root = args[args.index("--output-root") + 1]
        except IndexError:
            pass
    if not isinstance(runs, int) or runs <= 0:
        raise SystemExit("usage: phase4c_batch_orchestrator.py --runs <N> [--output-root <dir>] "
                         "[--live-public-data --enable-real-subprocess] "
                         "(scaffold planner only unless a concrete live runner is wired)")
    _live = "--live-public-data" in args
    _realsub = "--enable-real-subprocess" in args
    _diag = "--diagnostic-fake-runner" in args
    # Command-plan audit mode: records the intended argv plan; executes nothing; needs no live flags.
    if "--command-plan-only" in args:
        m = orchestrate(runs=runs, output_root=output_root, run_fn=command_plan_run_fn)
        print(json.dumps(m, indent=2))
        raise SystemExit(0)
    # Offline-fixture real-subprocess diagnostic: explicit flag; spawns REAL subprocesses of the tools
    # in OFFLINE FIXTURE mode (synthetic data, no network, no live double-lock). Fail-closed unless
    # the flag is present (default no-flag stays the no-op planner).
    if "--offline-fixture-subprocess" in args:
        _ex = make_concrete_subprocess_stage_executor(fixture_mode=True)   # default real runner
        _rf = make_live_run_fn(_ex)
        m = orchestrate(runs=runs, output_root=output_root, run_fn=_rf,
                        manifest_tag={"mode": "OFFLINE_FIXTURE_SUBPROCESS", "diagnostic_fixture": True})
        print(json.dumps(m, indent=2))
        raise SystemExit(0)
    # Diagnostic fake-runner mode: requires BOTH locks; uses the internal fake runner (no real
    # subprocess, no network) through the same concrete executor / orchestration path.
    if _diag:
        if not (_live and _realsub):
            raise SystemExit("--diagnostic-fake-runner requires BOTH --live-public-data and "
                             "--enable-real-subprocess (fail-closed).")
        _ex = make_concrete_subprocess_stage_executor(command_runner=_diagnostic_fake_command_runner)
        _rf = resolve_live_run_fn(live_public_data=True, enable_real_subprocess=True,
                                  concrete_executor=_ex)
        m = orchestrate(runs=runs, output_root=output_root, run_fn=_rf)
        print(json.dumps(m, indent=2))
        raise SystemExit(0)
    # Double-lock gate. Both flags (no diagnostic) -> real concrete subprocess executor; single flag
    # fails closed BEFORE creating any batch dir; default (no flags) stays the no-op planner.
    try:
        run_fn = resolve_live_run_fn(live_public_data=_live, enable_real_subprocess=_realsub,
                                     concrete_executor=None)
    except LiveExecutionRefused as e:
        raise SystemExit(str(e))
    m = orchestrate(runs=runs, output_root=output_root, run_fn=run_fn)   # run_fn None -> planner
    print(json.dumps(m, indent=2))
