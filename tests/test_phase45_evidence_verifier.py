"""tests/test_phase45_evidence_verifier.py — fixture-based offline tests for the deterministic
Phase 4C/5 evidence verifier harness.

All tests build a temporary fake repo (docs + read-only artifact dirs) under tmp_path. No network,
no public-data fetch, no subprocess batch, no trading/auth/secrets. The verifier is read-only and
must not mutate, clean, transform, or repair any fixture file. Result is one of
PASS / FAIL / BLOCKED_NEEDS_EVIDENCE, scoped only to the checked invariants.
"""
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO, "tools")
sys.path.insert(0, TOOLS_DIR)

import phase45_evidence_verifier as V  # noqa: E402


REQUIRED_DOCS = [
    "docs/protocols/phase5_planning_gate.md",
    "docs/protocols/phase5_interface_contract.md",
    "docs/handoff/phase4c_state_pre_phase5.md",
    "docs/handoff/phase4c_first_public_batch_audit.md",
    "docs/handoff/phase4c_repeatability_observation_02_audit.md",
    "docs/handoff/phase4c_repeatability_observation_03_audit.md",
]

EXPECTED_OBS = [
    "phase4c_batch_1781631021",
    "phase4c_batch_1781636200",
    "phase4c_batch_1781637248",
]

STAGES = ["phase3d5_sampler", "phase4a_analyzer", "phase4b_aggregator"]

RICH_DOC = """# Fixture state / evidence doc

<!-- FRAMING-START -->
Fixture framing. sample-only observation. ready-to-fly is only mentioned inside framing.
<!-- FRAMING-END -->

Observations:
- phase4c_batch_1781631021 (audit 4a85ff4)
- phase4c_batch_1781636200 (audit 71f1308)
- phase4c_batch_1781637248 (audit 1504bcb)

Cross-run (non-statistical): request_count 12/12/12; discovery_requests 4/4/4;
book_requests 8/8/8; artifacts 5/5/5; logs 6/6/6. stage order identical across runs.
eligible_pairs 4 for obs#1/#2; eligible_pairs 0 for obs#3 (a no-eligible result).
The obs#3 no-eligible outcome is an operator-attention signal.

<!-- NO-CLAIMS-START -->
No stationarity proof. No statistical significance. No economic inference. No readiness claim.
<!-- NO-CLAIMS-END -->
"""

STUB_DOC = "# stub fixture doc\n\nsample-only fixture; no economic inference here.\n"


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _write_docs(repo, *, omit=None, forbidden_in=None):
    """Write the 6 required docs. omit=relpath to skip one. forbidden_in=relpath to inject a
    forbidden positive claim into that doc's body (outside any block)."""
    for i, rel in enumerate(REQUIRED_DOCS):
        if rel == omit:
            continue
        content = RICH_DOC if rel == "docs/handoff/phase4c_state_pre_phase5.md" else STUB_DOC
        if rel == forbidden_in:
            content = content + "\nThe system is ready to fly now.\n"
        _write(os.path.join(repo, rel), content)


def _manifest(*, request_count=12, order=None, exits=(0, 0, 0), statuses=("ok", "ok", "ok"),
              run_count=1, completed=1, failed=0, aborted=False, cap=20,
              official_f1b=False, profitability=False, extra=None):
    order = order or STAGES
    stages = []
    for name, st, ec in zip(order, statuses, exits):
        stages.append({"stage_name": name, "status": st, "exit_code": ec})
    m = {
        "run_count": run_count, "completed_runs": completed, "failed_runs": failed,
        "aborted": aborted, "per_run_max_total_requests": cap,
        "official_f1b": official_f1b, "profitability": profitability,
        "per_run": [{"run_index": 1, "request_count": request_count, "stages": stages}],
    }
    if extra:
        m.update(extra)
    return m


def _write_batch(output_root, batch_id, *, ts=1000, eligible_pairs=4,
                 complement_pairs_written=4, manifest=None, manifest_text=None):
    d = os.path.join(output_root, batch_id)
    run01 = os.path.join(d, "run_01")
    logs = os.path.join(run01, "logs")
    os.makedirs(logs, exist_ok=True)
    for stage in STAGES:
        for stream in ("stdout", "stderr"):
            _write(os.path.join(logs, f"{stage}.{stream}.txt"), "")
    man_path = os.path.join(d, f"phase4c_batch_manifest_{ts}.json")
    if manifest_text is not None:
        with open(man_path, "w", encoding="utf-8") as f:
            f.write(manifest_text)
    else:
        with open(man_path, "w", encoding="utf-8") as f:
            json.dump(manifest if manifest is not None else _manifest(), f, indent=2)
    _write(os.path.join(run01, f"phase4a_gross_edge_summary_{ts}.json"),
           json.dumps({"eligible_pairs": eligible_pairs,
                       "verdict": "GROSS_EDGE_SAMPLE_ONLY" if eligible_pairs else
                                  "GROSS_EDGE_NO_ELIGIBLE_SNAPSHOTS"}))
    _write(os.path.join(run01, f"phase3d5_pilot_summary_{ts}.json"),
           json.dumps({"complement_pairs_written": complement_pairs_written, "request_count": 12}))
    return d


def _build_pass_repo(tmp_path, *, omit=None, forbidden_in=None, with_artifacts=True,
                     mutate=None):
    repo = os.path.join(str(tmp_path), "repo")
    out = os.path.join(repo, "data", "output")
    os.makedirs(out, exist_ok=True)
    _write_docs(repo, omit=omit, forbidden_in=forbidden_in)
    if with_artifacts:
        cfgs = {
            "phase4c_batch_1781631021": dict(ts=1001, eligible_pairs=4, complement_pairs_written=4),
            "phase4c_batch_1781636200": dict(ts=1002, eligible_pairs=4, complement_pairs_written=4),
            "phase4c_batch_1781637248": dict(ts=1003, eligible_pairs=0, complement_pairs_written=2),
        }
        for bid, cfg in cfgs.items():
            if mutate and bid in mutate:
                cfg = {**cfg, **mutate[bid]}
            _write_batch(out, bid, **cfg)
    return repo, out


def _tree_hashes(root):
    h = {}
    for dirpath, _, files in os.walk(root):
        for fn in files:
            p = os.path.join(dirpath, fn)
            with open(p, "rb") as f:
                h[os.path.relpath(p, root)] = hashlib.sha256(f.read()).hexdigest()
    return h


# ----------------------------------------------------------------------------- tests

def test_pass_path(tmp_path):
    repo, out = _build_pass_repo(tmp_path)
    res = V.verify(repo_root=repo, output_root=out)
    assert res["result"] == "PASS", res


def test_blocked_when_artifact_dirs_absent(tmp_path):
    repo, out = _build_pass_repo(tmp_path, with_artifacts=False)
    res = V.verify(repo_root=repo, output_root=out)
    assert res["result"] == "BLOCKED_NEEDS_EVIDENCE", res
    # docs still verified
    for rel in REQUIRED_DOCS:
        assert res["doc_checks"][rel]["exists"] is True
    assert any("missing_artifact_dir" in r for r in res["blocked_reasons"])


def test_fail_when_request_count_exceeds_cap(tmp_path):
    repo, out = _build_pass_repo(
        tmp_path, mutate={"phase4c_batch_1781631021": {"manifest": _manifest(request_count=21)}})
    res = V.verify(repo_root=repo, output_root=out)
    assert res["result"] == "FAIL", res
    assert any("request_count" in r for r in res["fail_reasons"])


def test_fail_when_stage_order_differs(tmp_path):
    bad = _manifest(order=["phase4a_analyzer", "phase3d5_sampler", "phase4b_aggregator"])
    repo, out = _build_pass_repo(
        tmp_path, mutate={"phase4c_batch_1781636200": {"manifest": bad}})
    res = V.verify(repo_root=repo, output_root=out)
    assert res["result"] == "FAIL", res
    assert any("stage_order" in r for r in res["fail_reasons"])


def test_fail_when_stage_exit_nonzero(tmp_path):
    bad = _manifest(exits=(0, 1, 0))
    repo, out = _build_pass_repo(
        tmp_path, mutate={"phase4c_batch_1781637248": {"manifest": bad, "eligible_pairs": 0,
                                                       "complement_pairs_written": 2}})
    res = V.verify(repo_root=repo, output_root=out)
    assert res["result"] == "FAIL", res
    assert any("stage" in r for r in res["fail_reasons"])


def test_obs3_no_eligible_accepted(tmp_path):
    repo, out = _build_pass_repo(tmp_path)  # obs3 already eligible_pairs=0
    res = V.verify(repo_root=repo, output_root=out)
    assert res["result"] == "PASS", res
    obs3 = res["artifact_checks"]["phase4c_batch_1781637248"]
    assert obs3.get("eligible_pairs") == 0
    # no fail reason mentions obs3
    assert not any("1781637248" in r for r in res["fail_reasons"]), res["fail_reasons"]


def test_missing_required_doc_blocks(tmp_path):
    repo, out = _build_pass_repo(tmp_path, omit="docs/protocols/phase5_interface_contract.md")
    res = V.verify(repo_root=repo, output_root=out)
    assert res["result"] == "BLOCKED_NEEDS_EVIDENCE", res
    assert any("missing_doc" in r for r in res["blocked_reasons"])


def test_forbidden_claim_in_doc_body_fails(tmp_path):
    repo, out = _build_pass_repo(
        tmp_path, forbidden_in="docs/handoff/phase4c_first_public_batch_audit.md")
    res = V.verify(repo_root=repo, output_root=out)
    assert res["result"] == "FAIL", res
    assert any("forbidden_claim" in r for r in res["fail_reasons"])


def test_verifier_does_not_mutate_fixture_files(tmp_path):
    repo, out = _build_pass_repo(tmp_path)
    before = _tree_hashes(repo)
    V.verify(repo_root=repo, output_root=out)
    after = _tree_hashes(repo)
    assert before == after, "verifier mutated or created files"


def test_verifier_does_not_clean_or_transform_evidence(tmp_path):
    # manifest with non-canonical formatting + extra keys must be left byte-for-byte unchanged.
    weird = json.dumps(_manifest(extra={"weird_extra": [3, 2, 1]}), separators=(",", ":"))
    repo, out = _build_pass_repo(
        tmp_path, mutate={"phase4c_batch_1781631021": {"manifest_text": weird}})
    man = os.path.join(out, "phase4c_batch_1781631021", "phase4c_batch_manifest_1001.json")
    before = open(man, "rb").read()
    V.verify(repo_root=repo, output_root=out)
    after = open(man, "rb").read()
    assert before == after, "verifier rewrote/normalized evidence"


def test_pass_is_scoped_to_checked_invariants(tmp_path):
    repo, out = _build_pass_repo(tmp_path)
    res = V.verify(repo_root=repo, output_root=out)
    assert "scoped only to checked invariants" in res["scope_note"].lower()
    assert isinstance(res["checked_invariants"], list) and res["checked_invariants"]


def test_output_contains_result_token(tmp_path, capsys):
    repo, out = _build_pass_repo(tmp_path)
    code = V.main(["--repo-root", repo, "--output-root", out])
    captured = capsys.readouterr().out
    assert code == 0
    assert '"result"' in captured
    assert any(tok in captured for tok in ("PASS", "FAIL", "BLOCKED_NEEDS_EVIDENCE"))


def test_main_exit_code_fail(tmp_path, capsys):
    repo, out = _build_pass_repo(
        tmp_path, mutate={"phase4c_batch_1781631021": {"manifest": _manifest(request_count=99)}})
    code = V.main(["--repo-root", repo, "--output-root", out])
    capsys.readouterr()
    assert code == 1
