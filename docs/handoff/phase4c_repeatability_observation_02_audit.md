# Phase 4C — Repeatability Observation #2 Audit Checkpoint

<!-- FRAMING-START -->
## Framing (read first)

This is **observation number: 2** under the
[Phase 4C Controlled Public-Data Repeatability Observation Protocol](../protocols/phase4c_repeatability_observation_protocol.md).
It is a **small-sample repeatability observation** of **mechanical pipeline behavior under public
data**. It carries **no economic inference**, **no stationarity proof**, **no statistical
significance**, and **no readiness claim** of any kind. The baseline it compares against is itself
a public-data sample-only observation, not an edge/profitability/readiness result.
<!-- FRAMING-END -->

## Run identity

- **Observation number:** 2
- **Baseline reference:** `phase4c_batch_1781631021` (see `phase4c_first_public_batch_audit.md`)
- **New batch id:** `phase4c_batch_1781636200`
- **Date:** 2026-06-16
- **Code state at run time:** `bb25d4d` (HEAD == origin/master at run time)
- **Command used (protocol double-lock):**

  ```
  python3 tools/phase4c_batch_orchestrator.py --runs 1 --output-root data/output --live-public-data --enable-real-subprocess
  ```

## Top-level outcome

- **Exit code:** 0
- **run_count / completed_runs / failed_runs:** 1 / 1 / 0
- **aborted / abort_reason:** false / null
- **per_run_max_total_requests:** 20
- **observed request_count 12 <= 20** (within the per-run request cap)
- **official_f1b:** false · **profitability:** false

## Sampler (3D5) facts

- request_count 12 · **discovery_requests:** 4 · **book_requests:** 8
- **assets sampled:** BTC / ETH / SOL / XRP
- **complement_pairs attempted/written:** 4 / 4
- **pair_books_ok/failed:** 8 / 0
- **failure_modes:** [] (none triggered)

## Stages — exactly 3, in order

1. `phase3d5_sampler` — status ok, verdict OK, exit_code 0 (summary verdict `PILOT_SAMPLE_ONLY`)
2. `phase4a_analyzer` — status ok, verdict OK, exit_code 0 (summary verdict `GROSS_EDGE_SAMPLE_ONLY`;
   candidate_pairs 4 / eligible_pairs 4 / ineligible_reasons {})
3. `phase4b_aggregator` — status ok, verdict OK, exit_code 0 (aggregate verdict
   `PHASE4B_AGGREGATE_SAMPLE_ONLY`; summaries_read 1 / records_read 4 / eligible_pairs_total 4 /
   rejection_rate 0.0)

All three ran as real subprocesses with explicit argv arrays (`shell=False`).

## Artifact summary (under `phase4c_batch_1781636200/run_01`)

- 3D5 snapshots JSONL: `phase3d5_pilot_snapshots_1781636201.jsonl`
- 3D5 summary JSON: `phase3d5_pilot_summary_1781636201.json`
- 4A records JSONL: `phase4a_gross_edge_1781636219.jsonl`
- 4A summary JSON: `phase4a_gross_edge_summary_1781636219.json`
- 4B aggregate JSON: `phase4b_gross_edge_aggregate_1781636219.json`

(5 run artifacts.)

## Log summary (under `run_01/logs`)

6 stdout/stderr files — `phase3d5_sampler`, `phase4a_analyzer`, `phase4b_aggregator`, each with
`.stdout.txt` and `.stderr.txt`.

## Baseline Comparison (Non-Statistical)

| Field | Baseline (`phase4c_batch_1781631021`) | Observation 02 (`phase4c_batch_1781636200`) | Delta |
|---|---|---|---|
| baseline_request_count / observation_02_request_count | 12 | 12 | **request_count_delta = 0** |
| baseline_discovery_requests / observation_02_discovery_requests | 4 | 4 | **discovery_requests_delta = 0** |
| baseline_book_requests / observation_02_book_requests | 8 | 8 | **book_requests_delta = 0** |
| baseline_assets / observation_02_assets | BTC/ETH/SOL/XRP | BTC/ETH/SOL/XRP | **asset_overlap = 4/4 (full)** |
| baseline_complement_pairs_written / observation_02_complement_pairs_written | 4 | 4 | **complement_pairs_delta = 0** |
| baseline_pair_books_ok_failed / observation_02_pair_books_ok_failed | 8 / 0 | 8 / 0 | ok delta 0 / failed delta 0 |

- **failure_modes comparison:** baseline [] vs observation 02 [] — identical (none in either).
- **artifact count comparison:** 5 vs 5 — consistent.
- **log count comparison:** 6 vs 6 — consistent.
- **stage order comparison:** both `phase3d5_sampler → phase4a_analyzer → phase4b_aggregator` —
  identical order, all status ok / exit_code 0.
- **stage duration/runtime comparison:** not available — the manifests do not expose per-stage
  duration/runtime fields (only `timeout_seconds` and a null `timestamp`), so no duration
  comparison is made.

### What this comparison is (and is not)

- This is a **baseline comparison only**.
- This is **not a stationarity test** (it **does not prove stationarity**).
- This is **not statistical significance**.
- This is **not an economic inference**.
- Any material drift would be an **operator attention signal**, not proof of instability. Here the
  observed deltas are all zero, which likewise proves nothing about the underlying process — two
  runs cannot establish stability.

## Safety confirmations

- public data only — public discovery + order-book reads.
- double-lock used: `--live-public-data` + `--enable-real-subprocess`.
- no `--diagnostic-fake-runner`, no `--offline-fixture-subprocess`, no `--command-plan-only` for
  the actual batch.
- no private CLOB auth · no secrets/.env printing · no orders/balances/trading · no Telegram/restart.
- generated artifacts are **untracked** and **not staged**; the batch directory
  `data/output/phase4c_batch_1781636200/` is not committed and not staged (no blanket/catch-all
  staging, no staging of any generated output path).
- `git diff` and `git diff --cached` were empty after the run; HEAD stayed `bb25d4d`.
- prior batch directories were not deleted or mutated.

<!-- NO-CLAIMS-START -->
## No-claims statement

This audit records a public-data sample-only repeatability observation only. It makes **no edge,
no PnL, no paper readiness, no economics readiness, no execution readiness, no profitability, no
alpha, no live readiness, no system-ready, no ready-to-fly, and no ready claim** of any kind. It
does not prove stationarity and asserts no statistical significance. The verdict labels above
(e.g. `GROSS_EDGE_SAMPLE_ONLY`) are sample-only diagnostic labels, not assertions of any tradeable
property.
<!-- NO-CLAIMS-END -->

## Next decision

The protocol permits 3 to 5 sample-only runs total; this is observation 2. A future, separately
gated step may continue with additional sample-only observations (3 to 5) or move to Phase 5 /
net-friction planning — without any readiness claim, and each behind its own gate.
