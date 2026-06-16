"""tests/test_phase4c_batch_orchestrator_contract.py — Phase 4C batch orchestration scaffold (TDD, offline).

Phase 4C v0 = OFFLINE batch orchestrator scaffold. Partitions runs into phase4c_batch_<ts>/run_NN/,
writes a manifest, enforces per-run request cap (20) fail-closed, never mutates root artifacts, never
executes live mode in this commit. NO live fetch/endpoints/market-data/trading; NO PnL/net-edge/
slippage/profitability/readiness claims. tmp_path only; injected run_fn fakes (no real subprocess).

İlk RED: tools/phase4c_batch_orchestrator henüz yok → ImportError.
"""
import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO, "tools")
sys.path.insert(0, TOOLS_DIR)

import phase4c_batch_orchestrator as C  # noqa: E402

ENGINE_PATH = os.path.join(TOOLS_DIR, "phase4c_batch_orchestrator.py")


def _good_run_fn(rc=12, buy=None, sell=None, eligible=0, rej=None, verdict="PILOT_SAMPLE_ONLY"):
    def fn(*, run_dir, run_index, max_total_requests):
        p = os.path.join(run_dir, f"fake_run_{run_index}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"run": run_index}, f)
        res = {"verdict": verdict, "request_count": rc, "timestamp": 1000 + run_index,
               "artifacts": {"snapshot": p}, "eligible_pairs": eligible}
        if buy is not None:
            res["buy_samples"] = buy
        if sell is not None:
            res["sell_samples"] = sell
        if rej is not None:
            res["rejection_rate"] = rej
        return res
    return fn


def _cap_violation_run_fn():
    def fn(*, run_dir, run_index, max_total_requests):
        return {"verdict": "PILOT_SAMPLE_ONLY", "request_count": 21 if run_index == 2 else 12,
                "timestamp": 1, "artifacts": {}}
    return fn


def _run(tmp_path, runs=3, run_fn=None):
    return C.orchestrate(runs=runs, output_root=str(tmp_path),
                         run_fn=run_fn if run_fn is not None else _good_run_fn(),
                         timestamp_fn=lambda: 8888)


# ---- partition structure ----

def test_partition_directory_structure(tmp_path):
    m = _run(tmp_path, runs=3)
    batch_dir = m["batch_dir"]
    assert os.path.isdir(batch_dir)
    for i in (1, 2, 3):
        assert os.path.isdir(os.path.join(batch_dir, f"run_{i:02d}")), f"run_{i:02d} missing"
    assert m["batch_id"].startswith("phase4c_batch_")


# ---- manifest fields ----

def test_manifest_fields(tmp_path):
    m = _run(tmp_path, runs=3)
    assert os.path.exists(m["manifest_path"])
    assert m["run_count"] == 3
    assert m["completed_runs"] == 3
    assert m["failed_runs"] == 0
    assert m["per_run_max_total_requests"] == 20
    assert len(m["per_run"]) == 3
    for e in m["per_run"]:
        for k in ("run_index", "run_dir", "artifacts", "request_count", "max_total_requests",
                  "verdict", "timestamp"):
            assert k in e, f"per_run entry missing {k}"
        assert e["max_total_requests"] == 20
    assert m["official_f1b"] is False
    assert m["profitability"] is False
    assert m["phase"] == "4C_batch_orchestration"


# ---- segment metric placeholders incl SEM ----

def test_segment_metrics_placeholder_keys_present_default(tmp_path):
    # default planned run_fn (no live) -> keys exist, values None
    m = C.orchestrate(runs=2, output_root=str(tmp_path), timestamp_fn=lambda: 8889)
    sm = m["segment_metrics"]
    for k in ("eligible_pairs", "rejection_rate",
              "buy_both_gross_edge_mean", "buy_both_gross_edge_stdev", "buy_both_gross_edge_sem",
              "sell_both_gross_edge_mean", "sell_both_gross_edge_stdev", "sell_both_gross_edge_sem"):
        assert k in sm, f"segment_metrics missing {k}"


def test_segment_metrics_sem_computed(tmp_path):
    run_fn = _good_run_fn(buy=None, sell=None)
    # supply per-run buy/sell samples via three distinct runs
    def fn(*, run_dir, run_index, max_total_requests):
        vals = {1: -0.01, 2: -0.02, 3: -0.03}[run_index]
        return {"verdict": "PILOT_SAMPLE_ONLY", "request_count": 12, "timestamp": run_index,
                "artifacts": {}, "buy_samples": [vals], "sell_samples": [vals], "eligible_pairs": 1}
    m = C.orchestrate(runs=3, output_root=str(tmp_path), run_fn=fn, timestamp_fn=lambda: 8890)
    sm = m["segment_metrics"]
    assert sm["buy_both_gross_edge_mean"] == pytest.approx(-0.02)
    assert sm["buy_both_gross_edge_stdev"] == pytest.approx(0.01, abs=1e-6)
    assert sm["buy_both_gross_edge_sem"] == pytest.approx(0.01 / (3 ** 0.5), abs=1e-6)
    assert sm["eligible_pairs"] == 3


# ---- fail-closed cap ----

def test_cap_violation_is_fail_closed(tmp_path):
    m = _run(tmp_path, runs=3, run_fn=_cap_violation_run_fn())
    assert m["aborted"] is True
    assert m["completed_runs"] == 1
    assert m["failed_runs"] == 1
    assert len(m["per_run"]) == 2                       # run_03 never launched
    assert m["per_run"][1]["verdict"] == "RUN_REQUEST_CAP_EXCEEDED"
    # run_03 dir not created
    assert not os.path.isdir(os.path.join(m["batch_dir"], "run_03"))


# ---- no root artifact mutation ----

def test_root_artifacts_not_mutated(tmp_path):
    root_file = tmp_path / "phase4b_gross_edge_aggregate_existing.json"
    root_file.write_text("ORIGINAL_ROOT", encoding="utf-8")
    m = _run(tmp_path, runs=2)
    assert root_file.read_text(encoding="utf-8") == "ORIGINAL_ROOT"   # untouched
    # batch artifacts nested under batch_dir, not at root
    assert os.path.dirname(m["manifest_path"]).rstrip("/") == m["batch_dir"].rstrip("/")
    assert os.path.commonpath([m["batch_dir"], str(tmp_path)]) == str(tmp_path)


# ---- output default ----

def test_output_default_under_data_output():
    assert C.OUT_DIR.replace(os.sep, "/").rstrip("/").endswith("data/output")


# ---- Phase 4C live-mode adapter (injected stage executor; no real subprocess) ----

LIVE_STAGES = ("phase3d5_sampler", "phase4a_analyzer", "phase4b_aggregator")


def _ok_executor():
    def ex(*, stage, run_dir, run_index, max_total_requests):
        p = os.path.join(run_dir, f"{stage}_out_{run_index}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"stage": stage}, f)
        rc = 12 if stage == "phase3d5_sampler" else None
        return {"status": "ok", "verdict": "OK", "exit_code": 0, "artifacts": {stage: p},
                "request_count": rc, "timestamp": run_index}
    return ex


def _fail_executor(fail_stage):
    def ex(*, stage, run_dir, run_index, max_total_requests):
        rc = 12 if stage == "phase3d5_sampler" else None
        if stage == fail_stage:
            return {"status": "error", "verdict": "FAILED", "exit_code": 1, "artifacts": {},
                    "request_count": rc, "timestamp": run_index}
        return {"status": "ok", "verdict": "OK", "exit_code": 0, "artifacts": {},
                "request_count": rc, "timestamp": run_index}
    return ex


def _cap_executor():
    def ex(*, stage, run_dir, run_index, max_total_requests):
        rc = 21 if stage == "phase3d5_sampler" else None
        return {"status": "ok", "verdict": "OK", "exit_code": 0, "artifacts": {},
                "request_count": rc, "timestamp": run_index}
    return ex


def test_no_flag_mode_remains_no_op_planner(tmp_path):
    m = C.orchestrate(runs=2, output_root=str(tmp_path), timestamp_fn=lambda: 9001)
    assert m["completed_runs"] == 2
    for e in m["per_run"]:
        assert e["verdict"] == "PLANNED"
        assert e["request_count"] == 0


def test_live_injected_success_records_all_stages(tmp_path):
    rf = C.make_live_run_fn(_ok_executor())
    m = C.orchestrate(runs=2, output_root=str(tmp_path), run_fn=rf, timestamp_fn=lambda: 9002)
    assert m["completed_runs"] == 2
    assert m["failed_runs"] == 0
    assert m["aborted"] is False
    for e in m["per_run"]:
        assert e["verdict"] == "RUN_COMPLETED"
        names = [s["stage_name"] for s in e["stages"]]
        assert names == list(LIVE_STAGES)
        assert all(s["status"] == "ok" for s in e["stages"])


def test_live_3d5_failure_skips_4a_4b(tmp_path):
    rf = C.make_live_run_fn(_fail_executor("phase3d5_sampler"))
    m = C.orchestrate(runs=3, output_root=str(tmp_path), run_fn=rf, timestamp_fn=lambda: 9003)
    assert m["aborted"] is True
    assert m["failed_runs"] == 1
    assert m["completed_runs"] == 0
    assert len(m["per_run"]) == 1
    stages = m["per_run"][0]["stages"]
    assert [s["stage_name"] for s in stages] == list(LIVE_STAGES)   # all recorded
    byname = {s["stage_name"]: s for s in stages}
    assert byname["phase4a_analyzer"]["status"] == "SKIPPED"
    assert byname["phase4b_aggregator"]["status"] == "SKIPPED"


def test_live_4a_failure_skips_4b(tmp_path):
    rf = C.make_live_run_fn(_fail_executor("phase4a_analyzer"))
    m = C.orchestrate(runs=3, output_root=str(tmp_path), run_fn=rf, timestamp_fn=lambda: 9004)
    assert m["aborted"] is True
    assert m["failed_runs"] == 1
    stages = m["per_run"][0]["stages"]
    byname = {s["stage_name"]: s for s in stages}
    assert [s["stage_name"] for s in stages] == list(LIVE_STAGES)
    assert byname["phase4b_aggregator"]["status"] == "SKIPPED"


def test_live_request_cap_violation_fail_closed(tmp_path):
    rf = C.make_live_run_fn(_cap_executor())
    m = C.orchestrate(runs=2, output_root=str(tmp_path), run_fn=rf, timestamp_fn=lambda: 9005)
    assert m["aborted"] is True
    assert m["failed_runs"] == 1
    assert m["per_run"][0]["verdict"] == "RUN_REQUEST_CAP_EXCEEDED"
    byname = {s["stage_name"]: s for s in m["per_run"][0]["stages"]}
    assert byname["phase4a_analyzer"]["status"] == "SKIPPED"
    assert byname["phase4b_aggregator"]["status"] == "SKIPPED"


# ---- double-lock gate + concrete executor wiring ----

def test_resolve_gate_no_flags_is_planner():
    assert C.resolve_live_run_fn(live_public_data=False, enable_real_subprocess=False) is None


def test_resolve_gate_single_flag_refused():
    with pytest.raises(C.LiveExecutionRefused):
        C.resolve_live_run_fn(live_public_data=True, enable_real_subprocess=False)
    with pytest.raises(C.LiveExecutionRefused):
        C.resolve_live_run_fn(live_public_data=False, enable_real_subprocess=True)


def test_resolve_gate_both_flags_wires_concrete_executor():
    # both flags now WIRE the concrete subprocess executor (no refusal). Returns a callable run_fn.
    # NOTE: not invoked here -- calling it with the default runner would spawn real subprocesses.
    rf = C.resolve_live_run_fn(live_public_data=True, enable_real_subprocess=True, concrete_executor=None)
    assert callable(rf)


def test_both_flags_injected_executor_success(tmp_path):
    rf = C.resolve_live_run_fn(live_public_data=True, enable_real_subprocess=True,
                               concrete_executor=_ok_executor())
    m = C.orchestrate(runs=2, output_root=str(tmp_path), run_fn=rf, timestamp_fn=lambda: 9100)
    assert m["completed_runs"] == 2
    assert m["failed_runs"] == 0
    for e in m["per_run"]:
        assert [s["stage_name"] for s in e["stages"]] == list(LIVE_STAGES)
        assert all(s["status"] == "ok" for s in e["stages"])


def test_cli_only_enable_real_subprocess_fail_closed(tmp_path):
    r = subprocess.run([sys.executable, ENGINE_PATH, "--runs", "1",
                        "--output-root", str(tmp_path), "--enable-real-subprocess"],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert not any(n.startswith("phase4c_batch_") for n in os.listdir(tmp_path))


# NOTE: there is intentionally NO CLI test for "--live-public-data --enable-real-subprocess":
# that path now wires the real subprocess executor and would spawn live stages. The concrete
# executor is exercised ONLY via an injected fake command_runner (no real subprocess) below.


def test_live_manifest_stage_fields(tmp_path):
    rf = C.make_live_run_fn(_ok_executor())
    m = C.orchestrate(runs=1, output_root=str(tmp_path), run_fn=rf, timestamp_fn=lambda: 9006)
    for s in m["per_run"][0]["stages"]:
        for k in ("stage_name", "status", "verdict", "exit_code", "artifacts", "request_count",
                  "timestamp"):
            assert k in s, f"stage entry missing {k}"
    # manifest invariants preserved
    assert m["per_run_max_total_requests"] == 20
    assert m["official_f1b"] is False
    assert m["profitability"] is False
    assert "buy_both_gross_edge_sem" in m["segment_metrics"]


def test_cli_live_flag_fail_closed_creates_nothing(tmp_path):
    r = subprocess.run([sys.executable, ENGINE_PATH, "--runs", "1",
                        "--output-root", str(tmp_path), "--live-public-data"],
                       capture_output=True, text=True)
    assert r.returncode != 0                                   # fail-closed
    assert not any(n.startswith("phase4c_batch_") for n in os.listdir(tmp_path))


# ---- command-plan audit mode ----

def _cmd_plan(tmp_path, runs=1):
    return C.orchestrate(runs=runs, output_root=str(tmp_path),
                         run_fn=C.command_plan_run_fn, timestamp_fn=lambda: 9200)


def test_command_plan_creates_partition_and_manifest(tmp_path):
    m = _cmd_plan(tmp_path, runs=1)
    assert os.path.isdir(m["batch_dir"])
    assert os.path.isdir(os.path.join(m["batch_dir"], "run_01"))
    assert os.path.exists(m["manifest_path"])
    assert m["completed_runs"] == 1


def test_command_plan_records_three_stages_in_order(tmp_path):
    m = _cmd_plan(tmp_path, runs=1)
    stages = m["per_run"][0]["stages"]
    assert [s["stage_name"] for s in stages] == list(LIVE_STAGES)
    for s in stages:
        assert s["status"] == "PLANNED"
        assert s["verdict"] == "COMMAND_PLAN_ONLY"
        assert s["exit_code"] is None
        assert s["request_count"] == 0
        assert s["artifacts"] == []
        assert s["timestamp"] is None
        assert "run_dir" in s and "command_plan" in s


def test_command_plan_uses_argv_arrays_not_shell_strings(tmp_path):
    m = _cmd_plan(tmp_path, runs=1)
    for s in m["per_run"][0]["stages"]:
        cp = s["command_plan"]
        assert isinstance(cp, list), "command_plan must be an argv array, not a shell string"
        assert cp[0] == "python3"
        assert all(isinstance(tok, str) for tok in cp)


def test_request_cap_in_phase3d5_command_plan(tmp_path):
    m = _cmd_plan(tmp_path, runs=1)
    byname = {s["stage_name"]: s for s in m["per_run"][0]["stages"]}
    cp = byname["phase3d5_sampler"]["command_plan"]
    assert "--max-total-requests" in cp
    assert "20" in cp


def test_command_plan_no_warnings_after_cli_alignment(tmp_path):
    # after aligning the tool CLIs, every planned flag is supported -> no plan_warnings
    m = _cmd_plan(tmp_path, runs=1)
    assert m["plan_warnings"] == []
    for s in m["per_run"][0]["stages"]:
        assert "command_plan_notes" in s
        assert s["command_plan_notes"] == []


def test_command_plan_supported_flags_not_flagged(tmp_path):
    m = _cmd_plan(tmp_path, runs=1)
    blob = " ".join(m["plan_warnings"])
    # supported flags must NOT be reported as unsupported
    assert "accept --input " not in blob and "accept --input-dir" not in blob
    assert "--pilot-3d5-complement-pairs" not in blob


def test_command_plan_does_not_invoke_subprocess(monkeypatch, tmp_path):
    # subprocess is now legitimately used in the concrete executor path (double-locked), but the
    # command-plan-only path must NEVER call it. Monkeypatch subprocess.run to raise and prove it.
    import subprocess as _sp

    def _boom(*a, **k):
        raise AssertionError("command-plan mode must not invoke subprocess.run")

    monkeypatch.setattr(_sp, "run", _boom)
    m = _cmd_plan(tmp_path, runs=1)
    assert all(s["status"] == "PLANNED" for s in m["per_run"][0]["stages"])


# ---- concrete subprocess stage executor (injected fake command_runner; NO real subprocess) ----

def _fake_runner(behavior=None):
    """Fake command_runner. behavior maps stage-tool substring -> dict overrides; default success +
    creates the stage's expected artifacts under --output-dir so downstream gating passes."""
    behavior = behavior or {}
    calls = []

    def _outdir(argv):
        return argv[argv.index("--output-dir") + 1]

    def runner(argv, *, timeout_seconds):
        calls.append({"argv": argv, "timeout_seconds": timeout_seconds})
        tool = argv[1]
        rd = _outdir(argv)
        ov = {}
        for key, b in behavior.items():
            if key in tool:
                ov = b
                break
        if ov.get("timed_out"):
            return {"exit_code": None, "stdout": ov.get("stdout", ""), "stderr": "timeout", "timed_out": True}
        exit_code = ov.get("exit_code", 0)
        make_artifacts = ov.get("make_artifacts", exit_code == 0)
        if make_artifacts:
            if "phase3_exec_sampler" in tool:
                with open(os.path.join(rd, "phase3d5_pilot_snapshots_1.jsonl"), "w") as f:
                    f.write(json.dumps({"asset": "BTC", "market_slug": "x", "token_id": "t",
                                        "utc_timestamp_ms": 1, "bids": [[0.49, 1]], "asks": [[0.51, 1]]}) + "\n")
                with open(os.path.join(rd, "phase3d5_pilot_summary_1.json"), "w") as f:
                    json.dump({"request_count": ov.get("request_count", 8)}, f)
            elif "phase4a" in tool:
                with open(os.path.join(rd, "phase4a_gross_edge_1.jsonl"), "w") as f:
                    f.write(json.dumps({"phase": "4A_gross_edge"}) + "\n")
                with open(os.path.join(rd, "phase4a_gross_edge_summary_1.json"), "w") as f:
                    json.dump({"phase": "4A_gross_edge"}, f)
            elif "phase4b" in tool:
                with open(os.path.join(rd, "phase4b_gross_edge_aggregate_1.json"), "w") as f:
                    json.dump({"phase": "4B_gross_edge_aggregate"}, f)
        return {"exit_code": exit_code, "stdout": ov.get("stdout", "ok-" + os.path.basename(tool)),
                "stderr": ov.get("stderr", ""), "timed_out": False}
    runner.calls = calls
    return runner


def _concrete(behavior=None, timeout_seconds=120):
    runner = _fake_runner(behavior)
    ex = C.make_concrete_subprocess_stage_executor(command_runner=runner, timeout_seconds=timeout_seconds)
    return ex, runner


def _run_concrete(tmp_path, behavior=None, timeout_seconds=120, ts=9300):
    ex, runner = _concrete(behavior, timeout_seconds)
    rf = C.resolve_live_run_fn(live_public_data=True, enable_real_subprocess=True, concrete_executor=ex)
    m = C.orchestrate(runs=1, output_root=str(tmp_path), run_fn=rf, timestamp_fn=lambda: ts)
    return m, runner


def test_concrete_uses_argv_arrays_shell_false(tmp_path):
    m, runner = _run_concrete(tmp_path)
    for c in runner.calls:
        assert isinstance(c["argv"], list)
        assert c["argv"][0] == "python3"
    with open(ENGINE_PATH, encoding="utf-8") as f:
        src = f.read()
    assert "shell=False" in src
    assert "shell=True" not in src


def test_concrete_passes_timeout_to_runner(tmp_path):
    m, runner = _run_concrete(tmp_path, timeout_seconds=99)
    assert all(c["timeout_seconds"] == 99 for c in runner.calls)
    for s in m["per_run"][0]["stages"]:
        assert s["timeout_seconds"] == 99


def test_concrete_success_three_stages_in_order(tmp_path):
    m, runner = _run_concrete(tmp_path)
    assert m["completed_runs"] == 1
    assert [s["stage_name"] for s in m["per_run"][0]["stages"]] == list(LIVE_STAGES)
    assert all(s["status"] == "ok" for s in m["per_run"][0]["stages"])


def test_concrete_records_artifacts(tmp_path):
    m, runner = _run_concrete(tmp_path)
    byname = {s["stage_name"]: s for s in m["per_run"][0]["stages"]}
    assert "snapshots" in byname["phase3d5_sampler"]["artifacts"]
    assert "records" in byname["phase4a_analyzer"]["artifacts"]
    assert "aggregate" in byname["phase4b_aggregator"]["artifacts"]


def test_concrete_captures_stdout_stderr(tmp_path):
    m, runner = _run_concrete(tmp_path)
    for s in m["per_run"][0]["stages"]:
        assert s["stdout_path"].endswith(".stdout.txt")
        assert s["stderr_path"].endswith(".stderr.txt")
        assert os.path.exists(s["stdout_path"])
        assert os.path.exists(s["stderr_path"])
        assert os.path.join("run_01", "logs") in s["stdout_path"].replace(os.sep, "/").replace("/", os.sep) \
            or "/logs/" in s["stdout_path"].replace(os.sep, "/")


def test_concrete_3d5_nonzero_skips_4a_4b(tmp_path):
    m, runner = _run_concrete(tmp_path, behavior={"phase3_exec_sampler": {"exit_code": 1}})
    assert m["aborted"] is True and m["failed_runs"] == 1
    byname = {s["stage_name"]: s for s in m["per_run"][0]["stages"]}
    assert byname["phase4a_analyzer"]["status"] == "SKIPPED"
    assert byname["phase4b_aggregator"]["status"] == "SKIPPED"


def test_concrete_4a_nonzero_skips_4b(tmp_path):
    m, runner = _run_concrete(tmp_path, behavior={"phase4a": {"exit_code": 1}})
    assert m["aborted"] is True
    byname = {s["stage_name"]: s for s in m["per_run"][0]["stages"]}
    assert byname["phase3d5_sampler"]["status"] == "ok"
    assert byname["phase4b_aggregator"]["status"] == "SKIPPED"


def test_concrete_timeout_skips_downstream(tmp_path):
    m, runner = _run_concrete(tmp_path, behavior={"phase3_exec_sampler": {"timed_out": True}})
    assert m["aborted"] is True and m["failed_runs"] == 1
    byname = {s["stage_name"]: s for s in m["per_run"][0]["stages"]}
    assert byname["phase3d5_sampler"]["status"] == "timeout"
    assert byname["phase4a_analyzer"]["status"] == "SKIPPED"
    assert byname["phase4b_aggregator"]["status"] == "SKIPPED"


def test_concrete_missing_3d5_artifact_fails_closed(tmp_path):
    # exit 0 but no artifacts produced -> missing-artifact failure, downstream skipped
    m, runner = _run_concrete(tmp_path, behavior={"phase3_exec_sampler": {"exit_code": 0, "make_artifacts": False}})
    assert m["aborted"] is True and m["failed_runs"] == 1
    byname = {s["stage_name"]: s for s in m["per_run"][0]["stages"]}
    assert byname["phase3d5_sampler"]["status"] != "ok"
    assert byname["phase4a_analyzer"]["status"] == "SKIPPED"


def test_concrete_request_cap_exceeded_fails_closed(tmp_path):
    m, runner = _run_concrete(tmp_path, behavior={"phase3_exec_sampler": {"exit_code": 0, "request_count": 21}})
    assert m["aborted"] is True
    assert m["per_run"][0]["verdict"] == "RUN_REQUEST_CAP_EXCEEDED"
    byname = {s["stage_name"]: s for s in m["per_run"][0]["stages"]}
    assert byname["phase4a_analyzer"]["status"] == "SKIPPED"


def test_cli_command_plan_only_creates_batch_no_live_flags(tmp_path):
    r = subprocess.run([sys.executable, ENGINE_PATH, "--runs", "1",
                        "--output-root", str(tmp_path), "--command-plan-only"],
                       capture_output=True, text=True)
    assert r.returncode == 0                                   # no live flags required
    batch_dirs = [n for n in os.listdir(tmp_path) if n.startswith("phase4c_batch_")]
    assert len(batch_dirs) == 1
    manifests = []
    for root, _dirs, files in os.walk(os.path.join(tmp_path, batch_dirs[0])):
        for fn in files:
            if fn.startswith("phase4c_batch_manifest_"):
                manifests.append(os.path.join(root, fn))
    assert len(manifests) == 1
    with open(manifests[0]) as f:
        man = json.load(f)
    stages = man["per_run"][0]["stages"]
    assert [s["stage_name"] for s in stages] == list(LIVE_STAGES)
    assert all(s["verdict"] == "COMMAND_PLAN_ONLY" for s in stages)


# ---- diagnostic fake-runner mode (exercises the concrete path; NO real subprocess) ----

def _diag_run(tmp_path, ts=9400):
    ex = C.make_concrete_subprocess_stage_executor(command_runner=C._diagnostic_fake_command_runner)
    rf = C.resolve_live_run_fn(live_public_data=True, enable_real_subprocess=True, concrete_executor=ex)
    return C.orchestrate(runs=1, output_root=str(tmp_path), run_fn=rf, timestamp_fn=lambda: ts)


def test_diagnostic_runner_never_calls_real_subprocess(monkeypatch, tmp_path):
    import subprocess as _sp
    monkeypatch.setattr(_sp, "run", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("diagnostic fake runner must not call subprocess.run")))
    m = _diag_run(tmp_path)
    assert m["completed_runs"] == 1
    assert [s["stage_name"] for s in m["per_run"][0]["stages"]] == list(LIVE_STAGES)
    assert all(s["status"] == "ok" for s in m["per_run"][0]["stages"])


def test_diagnostic_verdicts_clearly_labeled(tmp_path):
    m = _diag_run(tmp_path)
    for s in m["per_run"][0]["stages"]:
        assert "DIAGNOSTIC" in (s["verdict"] or "")   # cannot be confused with real observations


def test_diagnostic_request_count_le_20(tmp_path):
    m = _diag_run(tmp_path)
    byname = {s["stage_name"]: s for s in m["per_run"][0]["stages"]}
    rc = byname["phase3d5_sampler"]["request_count"]
    assert isinstance(rc, int) and rc <= 20


def test_diagnostic_command_plan_argv_arrays(tmp_path):
    m = _diag_run(tmp_path)
    for s in m["per_run"][0]["stages"]:
        assert isinstance(s["command_plan"], list)
        assert s["command_plan"][0] == "python3"


def test_diagnostic_artifacts_and_logs_under_run_dir(tmp_path):
    m = _diag_run(tmp_path)
    byname = {s["stage_name"]: s for s in m["per_run"][0]["stages"]}
    assert "snapshots" in byname["phase3d5_sampler"]["artifacts"]
    assert "records" in byname["phase4a_analyzer"]["artifacts"]
    assert "aggregate" in byname["phase4b_aggregator"]["artifacts"]
    for s in m["per_run"][0]["stages"]:
        # artifacts + logs live under the run dir, never at output_root
        for p in list(s["artifacts"].values()) + [s["stdout_path"], s["stderr_path"]]:
            assert "/run_01/" in p.replace(os.sep, "/")
            assert os.path.exists(p)


def test_cli_diagnostic_requires_both_locks_fail_closed(tmp_path):
    # diagnostic flag without both locks -> fail-closed, nothing created
    for extra in ([], ["--live-public-data"], ["--enable-real-subprocess"]):
        r = subprocess.run([sys.executable, ENGINE_PATH, "--runs", "1", "--output-root", str(tmp_path),
                            "--diagnostic-fake-runner", *extra], capture_output=True, text=True)
        assert r.returncode != 0
    assert not any(n.startswith("phase4c_batch_") for n in os.listdir(tmp_path))


def test_cli_diagnostic_all_three_flags_runs_fake(tmp_path):
    r = subprocess.run([sys.executable, ENGINE_PATH, "--runs", "1", "--output-root", str(tmp_path),
                        "--live-public-data", "--enable-real-subprocess", "--diagnostic-fake-runner"],
                       capture_output=True, text=True)
    assert r.returncode == 0
    batch_dirs = [n for n in os.listdir(tmp_path) if n.startswith("phase4c_batch_")]
    assert len(batch_dirs) == 1
    manifests = []
    for root, _dirs, files in os.walk(os.path.join(tmp_path, batch_dirs[0])):
        for fn in files:
            if fn.startswith("phase4c_batch_manifest_"):
                manifests.append(os.path.join(root, fn))
    assert len(manifests) == 1
    with open(manifests[0]) as f:
        man = json.load(f)
    stages = man["per_run"][0]["stages"]
    assert [s["stage_name"] for s in stages] == list(LIVE_STAGES)
    assert all(s["status"] == "ok" and "DIAGNOSTIC" in (s["verdict"] or "") for s in stages)
    # logs captured under run_01/logs
    logs_dir = os.path.join(tmp_path, batch_dirs[0], "run_01", "logs")
    assert os.path.isdir(logs_dir) and len(os.listdir(logs_dir)) >= 6


# ---- safety / isolation ----

def test_engine_no_forbidden_literals():
    with open(ENGINE_PATH, encoding="utf-8") as f:
        src = f.read()
    for bad in ("EXECUTION_READY", "ECONOMICS_READY_FOR_PAPER", "net_edge", "api_key", "api_secret",
                "private_key", "place_order", "get_balance", "os.environ", "getenv"):
        assert bad not in src, f"engine must not contain {bad!r}"


def test_engine_not_imported_by_production():
    res = subprocess.run(["grep", "-rIl", "--include=*.py", "phase4c_batch", REPO],
                         capture_output=True, text=True)
    hits = [ln for ln in res.stdout.splitlines()
            if ln.strip() and "/tools/" not in ln and "/tests/" not in ln
            and "/data/output/" not in ln and "/graphify-out/" not in ln and "/.git/" not in ln]
    assert hits == [], f"phase4c orchestrator must not be imported by production: {hits}"
