# Phase 4C/5 Evidence Verifier Harness

<!-- FRAMING-START -->
## Status and framing

`tools/phase45_evidence_verifier.py` is a **deterministic, offline, read-only** harness. It checks
committed docs and available read-only artifact/manifest/log references against explicit contracts
and returns one of **PASS / FAIL / BLOCKED_NEEDS_EVIDENCE**.

It is **not** a trading system, **not** a Phase 5 engine, **not** a data cleaner, and **not** an
economic model.
<!-- FRAMING-END -->

## What it is

- The verifier is **deterministic and offline**: no network, no public-data fetch, no subprocess
  batch run, no auth/secrets.
- It **checks committed docs and available artifacts against explicit contracts**.
- It **checks evidence consistency within its current scope** and **detects missing or contradictory
  evidence within its scope**.
- It **does not clean or transform data** (no cleaning, transforming, repairing, or normalizing of
  evidence; it reads bytes and leaves them unchanged).
- It **reduces reliance on LLM narrative** for these specific, checkable invariants.

## What it is not / does not do

- It is **not a mathematical proof**.
- It **does not guarantee correctness**.
- It **does not authorize Phase 5 implementation**.
- It **does not authorize trading or paper deployment**.
- It **does not authorize economic inference** and **makes no economic claims**.
- A PASS does **not** mean evidence is complete beyond the checked contract.

## Result semantics

- **PASS** means only that the **checked evidence matched the verifier's current contract**. PASS is
  **scoped only to checked invariants**.
- **FAIL** means **a checked invariant was contradicted** (e.g. request_count over the cap, a stage
  order other than the expected three-stage order, a nonzero stage exit, a manifest that is aborted
  or not 1/1/0, or a forbidden claim found in a doc body outside the explicit framing / no-claims /
  prohibited-output blocks).
- **BLOCKED_NEEDS_EVIDENCE** means **required evidence was absent or incomplete** (e.g. a required
  doc is missing, an artifact directory is missing, a manifest/logs are missing). It
  **pauses progress when required evidence is absent** rather than fabricating or inferring it.

## Checked invariants (current scope)

1. The six required committed docs exist (Phase 5 planning gate, Phase 5 interface contract, Phase
   4C pre-Phase-5 state doc, and the three Phase 4C observation audit docs).
2. Expected observation references (batch ids and the relevant audit commits) appear across the docs.
3. Expected cross-run mechanical facts appear in the docs (request/discovery/book/artifact/log
   tokens, eligible-pairs facts, no-eligible / operator-attention-signal framing, stage-order
   identity). Cross-run numeric sequences that are only emitted by artifacts are confirmed at the
   artifact level rather than by brittle string-match.
4. No-claims framing is present (no stationarity proof, no statistical significance, no economic
   inference, no readiness claim).
5. For each expected batch directory that is present, read-only manifest/log checks: manifest, run_01,
   run_01/logs and six stage logs exist; run_count/completed/failed is 1/1/0; aborted is false;
   per_run_max_total_requests is 20; official_f1b and profitability are false; stage order is exactly
   `phase3d5_sampler, phase4a_analyzer, phase4b_aggregator`; each stage exit code is 0; request_count
   is &lt;= 20 when present.
6. If expected batch directories are missing, artifact-level verification returns
   BLOCKED_NEEDS_EVIDENCE while committed docs are still verified; missing untracked artifacts are
   never fabricated and are not, by themselves, treated as proof of failure unless a checked
   invariant is contradicted.

## No-eligible handling

A **no-eligible observation can be valid evidence** and **must not be treated as a stage failure by
default**. Observation #3 had zero eligible records while its stages still completed (status ok,
exit 0); the verifier records eligibility descriptively and does not fail on it.

## Safety / git boundaries

- The verifier does **not** stage, modify, or delete any file, and does **not** require `data/output`
  artifacts to be tracked. Generated artifacts remain **untracked**.
- It writes no output file; results are returned in-process or printed to stdout only.
- Exit code: 0 for PASS or BLOCKED_NEEDS_EVIDENCE; 1 for FAIL; 2 for invalid invocation. A valid
  no-eligible observation does not cause a nonzero exit.

<!-- NO-CLAIMS-START -->
## No-claims statement

This harness and its protocol make **no edge, no PnL, no paper readiness, no economics readiness, no
execution readiness, no profitability, no alpha, no live readiness, no system-ready, no
ready-to-fly, and no ready claim**. It asserts no statistical significance, no stationarity proof,
and no economic inference. A PASS authorizes nothing; it only states that the checked invariants
matched the current contract.
<!-- NO-CLAIMS-END -->

## Next allowed step

**Future Phase 5 work still requires separate authorization, TDD, and review.** Future Phase 5
implementation must be separately authorized and TDD/offline first. This verifier supports that
review; it does not replace it.
