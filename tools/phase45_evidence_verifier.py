"""tools/phase45_evidence_verifier.py — deterministic, offline, read-only Phase 4C/5 evidence
verifier harness.

It inspects committed docs and read-only artifact/manifest/log references and returns a deterministic
result of PASS / FAIL / BLOCKED_NEEDS_EVIDENCE:

  - PASS  : every checked invariant matched the verifier's current contract (scoped only to those
            checked invariants).
  - FAIL  : a checked invariant was contradicted (e.g. request_count over cap, wrong stage order,
            a nonzero stage exit, a forbidden claim in a doc body).
  - BLOCKED_NEEDS_EVIDENCE : required evidence was absent or incomplete (e.g. a required doc or an
            artifact directory is missing). This pauses progress; the verifier never fabricates or
            infers missing evidence.

This tool is NOT a trading system, NOT a Phase 5 engine, NOT a data cleaner, and NOT an economic
model. It is offline and read-only: no network, no public-data fetch, no subprocess batch, no
auth/secrets, no mutation/cleaning/transformation/repair of evidence, no staging of artifacts. It
does not clean or transform data, does not authorize Phase 5 implementation, does not authorize
trading or paper deployment, and does not authorize or make economic inference. A no-eligible
observation is valid evidence and is not treated as a stage failure.

CLI: python3 tools/phase45_evidence_verifier.py [--repo-root PATH] [--output-root PATH]
Exit code: 0 for PASS or BLOCKED_NEEDS_EVIDENCE; 1 for FAIL; 2 for invalid invocation.
"""
import glob
import json
import os
import sys

_DEFAULT_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_DOCS = [
    "docs/protocols/phase5_planning_gate.md",
    "docs/protocols/phase5_interface_contract.md",
    "docs/handoff/phase4c_state_pre_phase5.md",
    "docs/handoff/phase4c_first_public_batch_audit.md",
    "docs/handoff/phase4c_repeatability_observation_02_audit.md",
    "docs/handoff/phase4c_repeatability_observation_03_audit.md",
]

# Distinctive facts that must appear somewhere across the committed doc set (case-insensitive).
REQUIRED_DOC_FACTS = [
    "phase4c_batch_1781631021", "phase4c_batch_1781636200", "phase4c_batch_1781637248",
    "4a85ff4", "71f1308", "1504bcb",
    "12/12/12", "4/4/4", "8/8/8", "5/5/5", "6/6/6",
    "eligible_pairs 4", "eligible_pairs 0",
    "no-eligible", "operator-attention signal", "stage order", "identical",
]

REQUIRED_NO_CLAIMS = [
    "no stationarity proof", "no statistical significance",
    "no economic inference", "no readiness claim",
]

# Positive over-claim phrases that must NOT appear in a doc body outside the explicit
# framing / no-claims / prohibited-output blocks.
FORBIDDEN_CLAIM_PHRASES = [
    "ready-to-fly", "ready to fly", "system-ready", "system ready",
    "is ready", "are ready", "production ready", "paper ready",
    "execution ready", "live ready", "economics ready", "ready for live",
    "is profitable", "profit confirmed", "profitable strategy",
    "edge confirmed", "positive edge", "tradeable edge", "alpha confirmed",
]

_BLOCK_MARKERS = [
    ("<!-- FRAMING-START -->", "<!-- FRAMING-END -->"),
    ("<!-- NO-CLAIMS-START -->", "<!-- NO-CLAIMS-END -->"),
    ("<!-- PROHIBITED-OUTPUTS-START -->", "<!-- PROHIBITED-OUTPUTS-END -->"),
]

EXPECTED_OBS = [
    "phase4c_batch_1781631021",
    "phase4c_batch_1781636200",
    "phase4c_batch_1781637248",
]
EXPECTED_STAGE_ORDER = ["phase3d5_sampler", "phase4a_analyzer", "phase4b_aggregator"]
REQUEST_CAP = 20
EXPECTED_LOG_COUNT = 6

SCOPE_NOTE = (
    "PASS is scoped only to checked invariants. This verifier is offline, read-only, and "
    "deterministic; it checks committed docs and available artifacts against explicit contracts "
    "and detects missing or contradictory evidence within its scope. It is not a mathematical "
    "proof, does not guarantee correctness, does not clean or transform data, and does not "
    "authorize Phase 5 implementation, trading, paper deployment, or economic inference."
)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _strip_blocks(text):
    for start, end in _BLOCK_MARKERS:
        while start in text and end in text and text.index(start) < text.index(end):
            s = text.index(start)
            e = text.index(end) + len(end)
            text = text[:s] + text[e:]
    return text


def _first(pattern):
    found = sorted(glob.glob(pattern))
    return found[0] if found else None


def _check_docs(repo_root, blocked, fail, checked):
    doc_checks = {}
    agg = []
    for rel in REQUIRED_DOCS:
        checked.append("doc_exists:" + rel)
        path = os.path.join(repo_root, rel)
        if not os.path.isfile(path):
            blocked.append("missing_doc:" + rel)
            doc_checks[rel] = {"exists": False}
            continue
        text = _read(path)
        doc_checks[rel] = {"exists": True}
        agg.append(text)
        body = _strip_blocks(text).lower()
        hits = [p for p in FORBIDDEN_CLAIM_PHRASES if p in body]
        if hits:
            fail.append("forbidden_claim_in_body:" + rel + ":" + ",".join(hits))
            doc_checks[rel]["forbidden_claim_hits"] = hits
    aggregate = "\n".join(agg).lower()

    checked.append("doc_facts")
    missing_facts = [f for f in REQUIRED_DOC_FACTS if f.lower() not in aggregate]
    if missing_facts:
        blocked.append("missing_doc_facts:" + ",".join(missing_facts))

    checked.append("no_claims_framing")
    missing_nc = [c for c in REQUIRED_NO_CLAIMS if c.lower() not in aggregate]
    if missing_nc:
        blocked.append("missing_no_claims:" + ",".join(missing_nc))

    doc_checks["_missing_facts"] = missing_facts
    doc_checks["_missing_no_claims"] = missing_nc
    return doc_checks


def _check_one_batch(obs, batch_dir, blocked, fail):
    entry = {"present": True}
    man = _first(os.path.join(batch_dir, "phase4c_batch_manifest_*.json"))
    if not man:
        entry["manifest"] = False
        blocked.append("missing_manifest:" + obs)
        return entry
    entry["manifest"] = True
    try:
        m = json.loads(_read(man))
    except Exception as e:  # malformed = uninterpretable = incomplete evidence
        entry["manifest_malformed"] = type(e).__name__
        blocked.append("malformed_manifest:" + obs)
        return entry

    run01 = os.path.join(batch_dir, "run_01")
    logs = os.path.join(run01, "logs")
    entry["run_01"] = os.path.isdir(run01)
    entry["logs"] = os.path.isdir(logs)
    if not os.path.isdir(run01):
        blocked.append("missing_run_01:" + obs)
    if not os.path.isdir(logs):
        blocked.append("missing_logs_dir:" + obs)
    else:
        n = len([x for x in os.listdir(logs) if os.path.isfile(os.path.join(logs, x))])
        entry["log_count"] = n
        if n != EXPECTED_LOG_COUNT:
            blocked.append("unexpected_log_count:" + obs + ":" + str(n))

    if not (m.get("run_count") == 1 and m.get("completed_runs") == 1
            and m.get("failed_runs") == 0):
        fail.append("run_counts:%s:%s/%s/%s" % (obs, m.get("run_count"),
                    m.get("completed_runs"), m.get("failed_runs")))
    if m.get("aborted") is not False:
        fail.append("aborted_not_false:" + obs)
    if m.get("per_run_max_total_requests") != REQUEST_CAP:
        fail.append("cap_not_20:" + obs + ":" + str(m.get("per_run_max_total_requests")))
    if m.get("official_f1b") is not False:
        fail.append("official_f1b_not_false:" + obs)
    if m.get("profitability") is not False:
        fail.append("profitability_not_false:" + obs)

    per = m.get("per_run") or []
    if not per:
        blocked.append("no_per_run:" + obs)
    else:
        run = per[0]
        rc = run.get("request_count")
        entry["request_count"] = rc
        if isinstance(rc, int) and not isinstance(rc, bool) and rc > REQUEST_CAP:
            fail.append("request_count_over_cap:" + obs + ":" + str(rc))
        stages = run.get("stages") or []
        order = [s.get("stage_name") for s in stages]
        entry["stage_order"] = order
        if order != EXPECTED_STAGE_ORDER:
            fail.append("stage_order:" + obs + ":" + ",".join(str(x) for x in order))
        for s in stages:
            if s.get("status") != "ok" or s.get("exit_code") != 0:
                fail.append("stage_not_ok:%s:%s(status=%s,exit=%s)" % (
                    obs, s.get("stage_name"), s.get("status"), s.get("exit_code")))

    # Optional: record eligibility (no-eligible is accepted, never a failure).
    a4 = _first(os.path.join(run01, "phase4a_gross_edge_summary_*.json"))
    if a4:
        try:
            entry["eligible_pairs"] = json.loads(_read(a4)).get("eligible_pairs")
        except Exception:
            pass
    d5 = _first(os.path.join(run01, "phase3d5_pilot_summary_*.json"))
    if d5:
        try:
            entry["complement_pairs_written"] = json.loads(_read(d5)).get(
                "complement_pairs_written")
        except Exception:
            pass
    return entry


def _check_artifacts(output_root, blocked, fail, checked):
    artifact_checks = {}
    for obs in EXPECTED_OBS:
        checked.append("artifact:" + obs)
        batch_dir = os.path.join(output_root, obs)
        if not os.path.isdir(batch_dir):
            artifact_checks[obs] = {"present": False}
            blocked.append("missing_artifact_dir:" + obs)
            continue
        artifact_checks[obs] = _check_one_batch(obs, batch_dir, blocked, fail)
    return artifact_checks


def verify(*, repo_root, output_root=None):
    repo_root = os.path.abspath(repo_root)
    if output_root is None:
        output_root = os.path.join(repo_root, "data", "output")
    output_root = os.path.abspath(output_root)

    blocked, fail, checked = [], [], []
    doc_checks = _check_docs(repo_root, blocked, fail, checked)
    artifact_checks = _check_artifacts(output_root, blocked, fail, checked)

    if fail:
        result = "FAIL"
    elif blocked:
        result = "BLOCKED_NEEDS_EVIDENCE"
    else:
        result = "PASS"

    return {
        "result": result,
        "repo_root": repo_root,
        "output_root": output_root,
        "doc_checks": doc_checks,
        "artifact_checks": artifact_checks,
        "blocked_reasons": blocked,
        "fail_reasons": fail,
        "checked_invariants": checked,
        "scope_note": SCOPE_NOTE,
        "official_f1b": False,
        "profitability": False,
    }


def _parse_argv(argv):
    repo_root = _DEFAULT_REPO_ROOT
    output_root = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--repo-root":
            if i + 1 >= len(argv):
                raise SystemExit(2)
            repo_root = argv[i + 1]; i += 2
        elif a == "--output-root":
            if i + 1 >= len(argv):
                raise SystemExit(2)
            output_root = argv[i + 1]; i += 2
        else:
            sys.stderr.write("unknown argument: %s\n" % a)
            raise SystemExit(2)
    return repo_root, output_root


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    repo_root, output_root = _parse_argv(argv)
    res = verify(repo_root=repo_root, output_root=output_root)
    print(json.dumps(res, indent=2))
    return 1 if res["result"] == "FAIL" else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
