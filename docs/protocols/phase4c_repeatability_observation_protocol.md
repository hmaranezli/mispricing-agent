# Phase 4C Controlled Public-Data Repeatability Observation Protocol

<!-- FRAMING-START -->
## Framing (read first)

This protocol governs a future **small-sample repeatability observation** of Phase 4C public-data
batch behavior. Its purpose is to observe **mechanical pipeline behavior under public data** across
a handful of identical, controlled, sample-only runs.

It is explicitly:
- a small-sample repeatability observation,
- mechanical pipeline behavior under public data,
- **no economic inference**,
- **no stationarity proof** — 3 to 5 runs **do not prove stationarity**,
- **no readiness claim** of any kind.

The first audited batch (`data/output/phase4c_batch_1781631021`, recorded in
`docs/handoff/phase4c_first_public_batch_audit.md`) was a public-data sample-only observation, not
an edge/profitability/readiness result. This protocol continues in that same sample-only spirit.
<!-- FRAMING-END -->

## Scope

- Future observation **only**. Do not run any batch as part of authoring or reading this protocol.
- **3 to 5 runs maximum**, total, for the whole observation.
- Each run is an identical, controlled, public-data sample-only batch.

## One-run-at-a-time rule

- Each observation run must use **`--runs 1`** only.
- **Do not** use `--runs 3`, `--runs 5`, or any multi-run orchestrator invocation. Multi-run
  invocation is forbidden under this protocol.
- Do **not** begin the next run until the prior run's manifest / log / artifact audit is complete
  (one-run-at-a-time). An unresolved prior-run audit blocks the next run.

## Each run command (exactly)

```
python3 tools/phase4c_batch_orchestrator.py --runs 1 --output-root data/output --live-public-data --enable-real-subprocess
```

No other flags. In particular, no `--diagnostic-fake-runner`, no `--offline-fixture-subprocess`,
no `--command-plan-only` for an actual observation run.

## Pre-run gates (every run)

- [ ] `HEAD == origin/master` at the expected, reviewed commit.
- [ ] `git diff` (working tree) empty.
- [ ] `git diff --cached` (staged) empty.
- [ ] Previous artifacts are **untracked** / **not staged**.
- [ ] The first audit checkpoint exists (`docs/handoff/phase4c_first_public_batch_audit.md`).

Stop if any gate fails.

## Recovery rule (interruption)

If a Claude / API / session interruption occurs, **do not rerun blindly**:

1. First inspect whether a **new `phase4c_batch_*` directory** (a new batch directory) was created.
2. If a new batch directory exists, **inspect / report it only** — do not start another run.
3. Rerun only if **no new batch directory exists** and repo state is clean.

## Artifact policy

- `data/output` generated artifacts remain **untracked** and **must not be committed**.
- Only protocol docs, audit summaries, or variance / repeatability reports may be committed.
- Never stage generated artifacts; never use a blanket/catch-all add.

## Per-run capture fields

For every run, capture and record:

- `batch_id`
- manifest path (and existence)
- exit code
- `run_count` / `completed_runs` / `failed_runs`
- `aborted` / `abort_reason`
- `per_run_max_total_requests`
- `request_count`
- `discovery_requests`
- `book_requests`
- assets sampled
- `complement_pairs_attempted` / `complement_pairs_written`
- `pair_books_ok` / `pair_books_failed`
- `failure_modes`
- per stage: stage names, order, status, verdict, exit_code
- per stage: stdout / stderr log paths and existence
- artifact path(s) and existence
- stage duration / runtime fields if present

## Cross-run comparison fields

Across the 3 to 5 runs, compare:

- request_count min/max
- discovery_requests min/max
- book_requests min/max
- assets observed (union across runs)
- number of successful runs
- number of aborted / fail-closed runs
- artifact count consistency
- log count consistency
- stage order consistency
- failure_modes summary

## Operator attention thresholds (explicitly non-statistical)

These are **non-statistical** operator triggers, not inferential tests:

- `request_count > 20` must stop.
- any nonzero exit must stop.
- missing artifact / missing log must stop.
- an unexpected staged generated artifact must stop.
- material run-to-run drift should trigger review — but **3 to 5 runs do not prove stationarity**,
  so drift or its absence proves nothing about the underlying process.

## Stop conditions

Stop the observation (do not continue to the next run) on any of:

- nonzero exit
- missing artifact
- missing logs
- `request_count > 20`
- timeout
- dirty git state
- unexpected staged generated artifact
- forbidden flags (any flag other than the exact command above)
- attempted multi-run invocation
- unresolved prior-run audit

## Reporting template

Each observation report must contain:

1. **Per-run table** — one row per run, using the per-run capture fields above.
2. **Cross-run summary** — using the cross-run comparison fields above.
3. **Safety confirmations** — public data only; double-lock used; no forbidden flags; no private
   CLOB auth; no secrets/.env printing; no orders/balances/trading; no Telegram/restart; generated
   artifacts untracked and not staged; `git diff` and `git diff --cached` empty; HEAD unchanged.
4. **No-claims statement** (see below).
5. **Next decision** section.

<!-- NO-CLAIMS-START -->
## No-claims statement

A repeatability observation under this protocol makes **no edge, no PnL, no paper readiness, no
economics readiness, no execution readiness, no profitability, no alpha, no live readiness, no
system-ready, no ready-to-fly, and no ready claim** of any kind. It does not prove stationarity.
The verdict labels produced by the pipeline are sample-only diagnostic labels, not assertions of
any tradeable property.
<!-- NO-CLAIMS-END -->

## Next decision

After 3 to 5 sample-only runs are observed and reported, a future separately-gated step may
consider Phase 5 / net-friction planning or a larger observation design — without any readiness
claim, and each behind its own gate. Completing this protocol grants no promotion by itself.
