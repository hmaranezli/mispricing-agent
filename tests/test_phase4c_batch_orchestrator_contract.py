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
    names = [s["stage_name"] for s in stages]
    assert names == ["phase3d5_sampler"]          # 4A/4B skipped
    assert "phase4a_analyzer" not in names
    assert "phase4b_aggregator" not in names


def test_live_4a_failure_skips_4b(tmp_path):
    rf = C.make_live_run_fn(_fail_executor("phase4a_analyzer"))
    m = C.orchestrate(runs=3, output_root=str(tmp_path), run_fn=rf, timestamp_fn=lambda: 9004)
    assert m["aborted"] is True
    assert m["failed_runs"] == 1
    stages = m["per_run"][0]["stages"]
    names = [s["stage_name"] for s in stages]
    assert names == ["phase3d5_sampler", "phase4a_analyzer"]   # 4B skipped
    assert "phase4b_aggregator" not in names


def test_live_request_cap_violation_fail_closed(tmp_path):
    rf = C.make_live_run_fn(_cap_executor())
    m = C.orchestrate(runs=2, output_root=str(tmp_path), run_fn=rf, timestamp_fn=lambda: 9005)
    assert m["aborted"] is True
    assert m["failed_runs"] == 1
    assert m["per_run"][0]["verdict"] == "RUN_REQUEST_CAP_EXCEEDED"
    # cap detected at sampler stage -> 4A/4B skipped
    assert [s["stage_name"] for s in m["per_run"][0]["stages"]] == ["phase3d5_sampler"]


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
