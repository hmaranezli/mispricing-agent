# Phase 4C — First Public-Data Batch Audit Checkpoint

Repo-durable audit record of the **first controlled public-data batch**. This is a
**public-data sample-only batch observation** — it records mechanical pipeline behavior under
public data. It is not trading, not paper, not readiness, not profitability, not alpha.

## Run identity

- **Batch id:** `phase4c_batch_1781631021`
- **Date:** 2026-06-16
- **Framing:** public-data sample-only batch observation
- **Code state at run time:** `fcd674c` (HEAD == origin/master at run time)
- **Command used (checklist double-lock):**

  ```
  python3 tools/phase4c_batch_orchestrator.py --runs 1 --output-root data/output --live-public-data --enable-real-subprocess
  ```

## Top-level outcome

- **Exit code:** 0
- **run_count / completed_runs / failed_runs:** 1 / 1 / 0
- **aborted / abort_reason:** false / null
- **per_run_max_total_requests:** 20
- **observed request_count 12 <= 20** (within the per-run request cap)
- **official_f1b:** false
- **profitability:** false

## Sampler (3D5) facts

- request_count 12 (= discovery + book)
- **discovery_requests:** 4
- **book_requests:** 8
- **assets:** BTC / ETH / SOL / XRP
- **complement_pairs attempted/written:** 4 / 4
- **pair_books_ok/failed:** 8 / 0
- **failure_modes:** [] (none triggered)

Fail-closed behavior would have been valid evidence if triggered (nonzero exit, missing artifact,
request_count > 20, timeout, or plan warning). None were triggered in this run.

## Stages — exactly 3, in order

1. `phase3d5_sampler`
2. `phase4a_analyzer`
3. `phase4b_aggregator`

### Stage results

| Stage | status | exit_code | stage verdict | summary/aggregate verdict |
|---|---|---|---|---|
| `phase3d5_sampler` | ok | 0 | OK | `PILOT_SAMPLE_ONLY` |
| `phase4a_analyzer` | ok | 0 | OK | `GROSS_EDGE_SAMPLE_ONLY` |
| `phase4b_aggregator` | ok | 0 | OK | `PHASE4B_AGGREGATE_SAMPLE_ONLY` |

All three stages ran as real subprocesses with explicit argv arrays (`shell=False`).
4A reported candidate_pairs 4 / eligible_pairs 4 / ineligible_reasons {}.
4B reported summaries_read 1 / records_read 4 / rejection_rate 0.0.

## Artifacts (under `phase4c_batch_1781631021/run_01`)

- 3D5 snapshots JSONL: `phase3d5_pilot_snapshots_1781631021.jsonl`
- 3D5 summary JSON: `phase3d5_pilot_summary_1781631021.json`
- 4A records JSONL: `phase4a_gross_edge_1781631040.jsonl`
- 4A summary JSON: `phase4a_gross_edge_summary_1781631040.json`
- 4B aggregate JSON: `phase4b_gross_edge_aggregate_1781631040.json`

## Logs (under `run_01/logs`)

6 stdout/stderr files — `phase3d5_sampler`, `phase4a_analyzer`, `phase4b_aggregator`, each with
`.stdout.txt` and `.stderr.txt`.

## Safety confirmations

- **public data only** — public discovery + order-book reads.
- **double-lock was used:** `--live-public-data` + `--enable-real-subprocess`.
- no `--diagnostic-fake-runner`.
- no `--offline-fixture-subprocess`.
- no `--command-plan-only` for the actual batch.
- no private CLOB auth.
- no secrets/.env printing.
- no orders/balances/trading.
- no Telegram/restart.
- generated artifacts are **untracked** and **not staged**; the batch directory
  `data/output/phase4c_batch_1781631021/` is not committed and not staged (no blanket/catch-all
  staging, and no staging of any generated output path).
- `git diff` and `git diff --cached` were empty after the run; HEAD stayed `fcd674c`.

<!-- NO-CLAIMS-START -->
## No-claims statement

This audit records a public-data sample-only batch observation only. It makes **no edge, no PnL,
no paper readiness, no economics readiness, no execution readiness, no profitability, no alpha,
no live readiness, no system-ready, no ready-to-fly, and no ready claim** of any kind. The
verdict labels above (e.g. `GROSS_EDGE_SAMPLE_ONLY`) are sample-only diagnostic labels, not
assertions of any tradeable property.
<!-- NO-CLAIMS-END -->

## Next decision

A future, separately-gated step may pursue either a repeatability observation (re-running the
sample-only public-data batch to observe variance under the same cap) or Phase 5 / net-friction
planning — both without any readiness claims, and each behind its own gate.
