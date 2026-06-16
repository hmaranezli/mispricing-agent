# Phase 4C — Repeatability Observation #3 Audit Checkpoint

<!-- FRAMING-START -->
## Framing (read first)

This is **observation number: 3** under the
[Phase 4C Controlled Public-Data Repeatability Observation Protocol](../protocols/phase4c_repeatability_observation_protocol.md).
It is a **three-point small-sample observation** of **mechanical behavior observation under public
data**. It records the **observed operational envelope** and **observed request/log/artifact
consistency** across observations #1–#3.

It carries **no economic inference**, **no stationarity proof**, **no statistical significance**,
and **no readiness claim** of any kind. The observations it compares against are themselves
public-data sample-only observations, not edge/profitability/readiness results.
<!-- FRAMING-END -->

## Run identity

- **Observation number:** 3
- **Observation #1 batch id:** `phase4c_batch_1781631021`
- **Observation #2 batch id:** `phase4c_batch_1781636200`
- **New observation #3 batch id:** `phase4c_batch_1781637248`
- **Date:** 2026-06-16
- **Code state at run time:** `71f1308` (HEAD == origin/master at run time)
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
- **complement_pairs attempted/written:** 4 / **2**
- **pair_books_ok/failed:** 8 / 0
- **failure_modes:** [] (none triggered)

## Stages — exactly 3, in order

1. `phase3d5_sampler` — status ok, verdict OK, exit_code 0 (summary verdict `PILOT_SAMPLE_ONLY`)
2. `phase4a_analyzer` — status ok, verdict OK, exit_code 0 (summary verdict
   `GROSS_EDGE_NO_ELIGIBLE_SNAPSHOTS`; candidate_pairs 4 / eligible_pairs 0 /
   ineligible_reasons `{ONE_SIDED_BOOK: 2, SPREAD_TOO_WIDE: 2}`)
3. `phase4b_aggregator` — status ok, verdict OK, exit_code 0 (aggregate verdict
   `PHASE4B_NO_ELIGIBLE_RECORDS`; summaries_read 1 / records_read 0 / eligible_pairs_total 0 /
   rejection_rate 1.0)

All three stages ran as real subprocesses with explicit argv arrays (`shell=False`) and completed
mechanically (status ok / exit_code 0). The "no eligible" 4A/4B outcome is a valid sample-only
result of the observed public-data content for this run, not a stage failure and not an abort.

## Artifact summary (under `phase4c_batch_1781637248/run_01`)

- 3D5 snapshots JSONL: `phase3d5_pilot_snapshots_1781637248.jsonl`
- 3D5 summary JSON: `phase3d5_pilot_summary_1781637248.json`
- 4A records JSONL: `phase4a_gross_edge_1781637266.jsonl` (0 records this run)
- 4A summary JSON: `phase4a_gross_edge_summary_1781637266.json`
- 4B aggregate JSON: `phase4b_gross_edge_aggregate_1781637266.json`

(5 run artifacts.)

## Log summary (under `run_01/logs`)

6 stdout/stderr files — `phase3d5_sampler`, `phase4a_analyzer`, `phase4b_aggregator`, each with
`.stdout.txt` and `.stderr.txt`.

## Cross-Run Comparison (Non-Statistical)

Three-point small-sample observation across observations #1, #2, #3.

| Metric | obs #1 (`…1781631021`) | obs #2 (`…1781636200`) | obs #3 (`…1781637248`) |
|---|---|---|---|
| observation_01/02/03_request_count | 12 | 12 | 12 |
| discovery_requests | 4 | 4 | 4 |
| book_requests | 8 | 8 | 8 |
| assets observed per run | BTC/ETH/SOL/XRP | BTC/ETH/SOL/XRP | BTC/ETH/SOL/XRP |
| complement_pairs_written per run | 4 | 4 | 2 |
| pair_books_ok_failed per run | 8 / 0 | 8 / 0 | 8 / 0 |
| eligible_pairs (4A) | 4 | 4 | 0 |
| 4A verdict | GROSS_EDGE_SAMPLE_ONLY | GROSS_EDGE_SAMPLE_ONLY | GROSS_EDGE_NO_ELIGIBLE_SNAPSHOTS |
| 4B verdict | …AGGREGATE_SAMPLE_ONLY | …AGGREGATE_SAMPLE_ONLY | …NO_ELIGIBLE_RECORDS |
| failure_modes | [] | [] | [] |
| artifact count | 5 | 5 | 5 |
| log count | 6 | 6 | 6 |

### Ranges and observed deltas

- **request_count_min_max:** min 12 / max 12 — **request_count_deltas:** (obs2−obs1)=0, (obs3−obs2)=0.
- **discovery_requests_min_max:** min 4 / max 4 — **discovery_requests_deltas:** 0, 0.
- **book_requests_min_max:** min 8 / max 8 — **book_requests_deltas:** 0, 0.
- **asset overlap across runs:** full (4/4) — same four assets observed in every run.
- **complement_pairs_written per run:** 4, 4, 2 — **complement_pairs_deltas:** (obs2−obs1)=0,
  (obs3−obs2)=−2 (min 2 / max 4).
- **pair_books_ok_failed per run:** 8/0, 8/0, 8/0 — identical.
- **failure_modes comparison:** [] / [] / [] — identical (none in any run).
- **artifact count comparison:** 5 / 5 / 5 — consistent.
- **log count comparison:** 6 / 6 / 6 — consistent.
- **stage order comparison:** all three runs `phase3d5_sampler → phase4a_analyzer →
  phase4b_aggregator`, all status ok / exit_code 0 — identical order.
- **stage duration/runtime comparison:** not available — the manifests do not expose per-stage
  duration/runtime fields (only `timeout_seconds` and a null `timestamp`), so no duration
  comparison is made.

### What this comparison is (and is not)

- This is a **small-sample comparison only** (three-point small-sample observation).
- This is **not a stationarity test** (it **does not prove stationarity**).
- This is **not statistical significance**.
- This is **not an economic inference**.
- The observed obs #3 difference — `complement_pairs_written` 2 vs 4 and `eligible_pairs` 0 vs 4 —
  is an **observed delta** and an **operator attention signal**, not proof of instability and not
  proof of market-dependent behavior. Request/log/artifact consistency and stage order held; the
  difference is confined to how many sampled pairs were eligible under the observed public-data
  content for this run.
- **Zero deltas, where observed (request_count, discovery_requests, book_requests, failure_modes,
  artifact/log counts, stage order), do not prove determinism or stability.** Three runs cannot
  establish stability, instability, drift, or its absence.
- Cross-run averages/ranges, if reported, are **descriptive only** and **not statistical proof**.

<!-- NO-CLAIMS-START -->
## No-claims statement

This audit records a public-data sample-only repeatability observation only. It makes **no edge,
no PnL, no paper readiness, no economics readiness, no execution readiness, no profitability, no
alpha, no live readiness, no system-ready, no ready-to-fly, and no ready claim** of any kind. It
does not prove stationarity and asserts no statistical significance. The verdict labels above
(e.g. `GROSS_EDGE_NO_ELIGIBLE_SNAPSHOTS`) are sample-only diagnostic labels, not assertions of any
tradeable property.
<!-- NO-CLAIMS-END -->

## Safety confirmations

- public data only — public discovery + order-book reads.
- double-lock used: `--live-public-data` + `--enable-real-subprocess`.
- no `--diagnostic-fake-runner`, no `--offline-fixture-subprocess`, no `--command-plan-only` for
  the actual batch.
- no private CLOB auth · no secrets/.env printing · no orders/balances/trading · no Telegram/restart.
- generated artifacts are **untracked** and **not staged**; the batch directory
  `data/output/phase4c_batch_1781637248/` is not committed and not staged (no blanket/catch-all
  staging, no staging of any generated output path).
- `git diff` and `git diff --cached` were empty after the run; HEAD stayed `71f1308`.
- prior batch directories were not deleted or mutated.

## Next decision

Observation #3 can inform Phase 5 planning, but it **does not authorize Phase 5 implementation, trading, paper deployment, or readiness claims**. It is a **Phase 5 planning input, not Phase 5 justification**. The protocol permits 3 to 5 sample-only runs total; this is observation 3. A
future, separately gated step may continue with additional sample-only observations (up to 5) or
move to Phase 5 / net-friction planning — without any readiness claim, and each behind its own gate.
