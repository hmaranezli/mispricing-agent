# Phase 4C — First Public-Data Batch Pre-Flight Checklist

> Repo-durable operator gate. Complete **every** item below, in order, before running the
> first controlled public-data batch. Any unchecked or failed item is a hard stop — do not run.
>
> This checklist authorizes **one** sample-only observation batch. It does not authorize trading,
> and it makes no economic claim. See "No-claims framing" at the end.

This document is offline. Reading or satisfying this checklist runs no batch, fetches no endpoint,
and touches no market data, secrets, or trading path.

---

## 0. Scope of this batch

- Exactly **one** controlled public-data batch (`--runs 1`).
- Purpose: collect a small public-data sample through the existing Phase 3D5 → 4A → 4B pipeline
  using real OS subprocesses, under the request cap, to observe pipeline behavior on public data.
- This is a **sample-only observation** run. It is **not** an edge, PnL, paper, economics,
  execution, profitability, alpha, or live-readiness exercise.

---

## 1. Required repo state (verify before launch)

- [ ] `HEAD == origin/master` at the expected, reviewed commit (record the hash before launch).
- [ ] `git diff` (working tree) is **empty**.
- [ ] `git diff --cached` (staged) is **empty**.
- [ ] Previously generated artifacts under `data/output/` are **untracked** and **not staged**
      (`git status --porcelain data/output` shows only `??` entries; nothing staged).
- [ ] No uncommitted change to any production path (see §7).

Stop if any item fails.

---

## 2. Required flags for the first controlled public-data batch

The batch MUST be launched with exactly these flags (the live double-lock is mandatory):

```
python3 tools/phase4c_batch_orchestrator.py \
  --runs 1 \
  --output-root data/output \
  --live-public-data \
  --enable-real-subprocess
```

- [ ] `--runs 1` present (single batch run only).
- [ ] `--output-root data/output` present (artifacts land under the repo's data/output tree).
- [ ] `--live-public-data` present (first half of the double-lock).
- [ ] `--enable-real-subprocess` present (second half of the double-lock).

Both `--live-public-data` **and** `--enable-real-subprocess` are required; supplying only one
must fail closed and run nothing.

---

## 3. Explicitly forbidden flags / modes

The following must **not** appear when running the actual public-data batch:

- [ ] No `--diagnostic-fake-runner` (that path writes fake artifacts; it is not a real batch).
- [ ] No `--offline-fixture-subprocess` (that path uses synthetic fixture data; it is not public data).
- [ ] No `--command-plan-only` for the actual batch (that path only prints a plan and executes nothing).

Each of the above is a valid offline diagnostic mode, but none of them constitutes the first
controlled public-data batch. Do not substitute one for the batch.

---

## 4. Request cap

- [ ] `per_run_max_total_requests == 20` for the run (the per-run public request budget).
- [ ] If observed `request_count > 20`, the run must surface the cap breach and fail closed
      (`RUN_REQUEST_CAP_EXCEEDED`); it must not silently continue.

---

## 5. Stage expectations

The batch must execute **exactly 3 stages, in this order**:

1. `phase3d5_sampler`
2. `phase4a_analyzer`
3. `phase4b_aggregator`

- [ ] No extra stages, no missing stages, no reordering.
- [ ] Each stage runs as a real subprocess with an explicit argv array (`shell=False`).
- [ ] A stage failure must mark that stage failed and record downstream stages as `SKIPPED`.

---

## 6. Expected artifact & log layout

Under **one** new batch directory `data/output/phase4c_batch_<ts>/`:

- [ ] A batch manifest `phase4c_batch_manifest_<ts>.json` at the batch-dir root.
- [ ] Exactly one run directory `phase4c_batch_<ts>/run_01`.

Inside `phase4c_batch_<ts>/run_01` (the artifact layout under one new
`phase4c_batch_<ts>/run_01`):

- [ ] `phase3d5_pilot_snapshots_<ts>.jsonl` (3D5 snapshots).
- [ ] `phase3d5_pilot_summary_<ts>.json` (3D5 summary; carries `request_count`).
- [ ] `phase4a_gross_edge_<ts>.jsonl` (4A records).
- [ ] `phase4a_gross_edge_summary_<ts>.json` (4A summary).
- [ ] `phase4b_gross_edge_aggregate_<ts>.json` (4B aggregate).

Logs under `run_01/logs`:

- [ ] `run_01/logs/phase3d5_sampler.stdout.txt` and `.stderr.txt`.
- [ ] `run_01/logs/phase4a_analyzer.stdout.txt` and `.stderr.txt`.
- [ ] `run_01/logs/phase4b_aggregator.stdout.txt` and `.stderr.txt`.

---

## 7. Abort / fail-closed expectations

The orchestrator must stop downstream work or abort the batch on any of:

- [ ] A **nonzero exit** from any stage subprocess.
- [ ] A **missing artifact** expected from any stage.
- [ ] An observed `request_count > 20` (request-cap breach).
- [ ] A stage **timeout**.
- [ ] Any **plan warning** (`plan_warnings` non-empty) — investigate and stop; do not proceed.

In every abort case, downstream stages must be recorded `SKIPPED` and the batch marked failed.

---

## 8. Safety boundaries (non-negotiable)

- [ ] **public data only** — public endpoints only; no private/authenticated CLOB access.
- [ ] **no secrets** / no auth / no API keys / no private CLOB credentials are used.
- [ ] **no orders** are placed.
- [ ] **no balances** are read or modified; no funds move.
- [ ] no trading of any kind.
- [ ] **no Telegram** notifications and **no restart** of any service.
- [ ] No change to `main_loop`, to `config`, or to any production path:
      `analysis/`, `execution/`, `council/`, `db/`, `main_loop.py`, `config.py`.

---

## 9. Reporting requirements (after the batch)

Record and report all of:

- [ ] **exit code** of the orchestrator process.
- [ ] **request_count** for the run (confirm `<= 20`).
- [ ] **stage verdict** for each of the 3 stages, in order.
- [ ] **artifact path** for each produced artifact (snapshots, summaries, records, aggregate).
- [ ] **logs**: confirm all 6 stdout/stderr files exist under `run_01/logs`.
- [ ] **git cleanliness**: `git diff` and `git diff --cached` empty; `HEAD == origin/master`
      unchanged at the expected commit.
- [ ] **no generated artifacts staged**: the new `phase4c_batch_<ts>/` directory is untracked and
      not staged; never `git add .`; never commit generated artifacts.

---

## No-claims framing

The first public-data batch is a **sample-only observation**. Its outputs are internal
complement-consistency / pipeline-behavior diagnostics only. Running it is explicitly:

- **not edge** evidence,
- **not PnL**,
- **not profitability** (no alpha claim),
- **not paper readiness**,
- **not economics readiness**,
- **not execution readiness**,
- **not live readiness**, system-ready, or ready-to-fly.

No "ready" claim of any kind follows from completing this batch. Promotion to any later phase
requires its own separately-gated evidence.
