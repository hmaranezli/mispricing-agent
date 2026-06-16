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
import json
import os
import statistics
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


def orchestrate(*, runs, output_root=OUT_DIR, run_fn=None, timestamp_fn=None):
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
        "official_f1b": False,
        "profitability": False,
        "generated_at_unix": now,
    }
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
                         "(scaffold planner only; live execution not enabled)")
    m = orchestrate(runs=runs, output_root=output_root)
    print(json.dumps(m, indent=2))
