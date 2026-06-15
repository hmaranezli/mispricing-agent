# scan_perf Offline p95/p99 Parsing Recipe (docs-only)

**Date:** 2026-06-15
**Slice:** offline observability hygiene (post-E12, behavior-neutral)
**Type:** Documentation recipe. No executable parser code, no in-process aggregation, no scan_perf format change.

## Purpose

The `[scan_perf]` line emitted once per `_scan_and_execute` cycle is a point-in-time latency snapshot. To
review latency distribution, jitter, and tail spikes:
**scan_perf is parsed offline from logs, not aggregated in-process**.
This recipe documents how, without adding any runtime code.

## Source contract (pinned by `_format_scan_perf`)

The `[scan_perf]` line is produced by `main_loop._format_scan_perf(...)` and its field contract is pinned
by `tests/test_scan_perf_marker_contract.py`. The
**required fields: total_ms, scan_edges_ms, council_ms, execute_ms, candidates**
appear in that fixed order, with `:.0f` rounded-integer milliseconds and an integer candidate count.
Offline tooling depends on these exact field labels, which is why the marker contract test exists — so
the labels cannot silently drift.

Example line shape (illustrative; values vary):

```
[scan_perf] total_ms=42 scan_edges_ms=12 council_ms=20 execute_ms=8 candidates=3
```

## Derived metrics

From a window of collected `[scan_perf]` lines, compute per field (especially `total_ms` and
`council_ms`) the **derived metrics: count, avg, p50, p95, p99, max**. These summarize typical latency
(avg/p50), the tail (p95/p99/max), and throughput context (candidates per cycle). A **jitter and
tail-spike review** then compares p99/max against p50 to detect cycle-to-cycle variation and outliers
that a single point-in-time line cannot reveal.

## Workflow (manual / scriptable, run OUTSIDE the bot)

This is a future grep/script workflow description only — no parser is added in this slice:

1. Collect the bot's stdout/log lines (e.g. from the process log or a captured run).
2. Filter to scan_perf lines, e.g. `grep '\[scan_perf\]' <logfile>`.
3. Extract the five fields per line by their labels (`total_ms=`, `scan_edges_ms=`, `council_ms=`,
   `execute_ms=`, `candidates=`).
4. For each numeric field, compute count, avg, p50, p95, p99, max with any offline tool (a small
   throwaway script, a spreadsheet, or a stats one-liner). Percentiles use the standard
   nearest-rank/interpolation method of whatever tool is chosen; document which was used alongside the
   numbers.
5. Do the jitter and tail-spike review: flag cycles where total_ms or council_ms p99/max greatly exceeds
   p50, and correlate with candidates to separate "busy cycle" from "slow cycle".

## Why offline, not in-process

**offline parsing is safer than in-process aggregation for this bot**: it adds no state, no new failure
surface, and no extra work to the hot entry loop, whereas an in-process percentile tracker would add
mutable state and complexity to the runtime path. Furthermore:
**offline parsing is non-blocking for the runtime loop because it does not run inside main_loop** —
it operates on already-emitted logs after the fact.

## Scope guarantees

- **this does not change runtime behavior**: no code is added to `main_loop.py`, the scan_perf format is
  unchanged, and no in-process p95/p99/max aggregation, metrics, cache, or live telemetry is introduced.
- **this does not unblock F/live**: this is observability hygiene only. Master F, Paper Soak, canary,
  D#2 (human DRY_RUN gate), and D#7 (phase-2 live balance probe) remain BLOCKED and are unaffected by
  this recipe.

## When to act on the metrics

Per the E12a observation policy (`e12a_latency_cache_observation_policy.md`), optimize only after this
offline analysis shows a measured scan_perf/council_ms regression or genuine tail spikes. Absent that
evidence, no optimization or instrumentation is warranted.
