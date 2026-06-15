# E12a — Latency / Cache Observation Policy (docs-only)

**Date:** 2026-06-15
**Slice:** E12a (post-Master-E observation, before Master F / live / Paper Soak)
**Type:** Read-only observation decision artifact. No metrics code, no cache code, no scan_perf format change, no config change.

## VERDICT: NO OPTIMIZATION NOW

This document records the read-only latency/cache observation performed after the E11a–E11g closeout. The decision is to add no optimization at this time and to gather evidence first. It is a decision artifact, not enforcement or instrumentation.

## 1. Gate overhead findings

- **E10/E11 gates are pure in-memory** and negligible: `max_trades_first_session_halt` (E10b), `no_fill_burst_halt` (E11c), and `fill_to_submit_halt` (E11f) each do a pure predicate call plus a `getattr(config, …)` fallback plus in-memory integer reads (`_session_trade_count`, `_no_fill_streak`, `_session_submit_count`). No I/O.
- **E5 _effective_risk_mode sqlite read is the only non-trivial gate cost.** `_effective_risk_mode()` calls `load_risk_state(RISK_STATE_DB_FILE)`, which opens a fresh `sqlite3.connect` and reads the singleton risk-state row per finding that passes council. It is a local sqlite read (microseconds–low-ms), runs after the far more expensive network-bound council, and the per-finding count is bounded because `MAX_OPEN_POSITIONS = 1` breaks the loop early.
- **E5/E6 risk-state layer predates E10/E11**: the sqlite read belongs to the risk-state persistence layer, not to the E10/E11 execution-quality breakers. It is mentioned only because it is the single non-trivial cost on the entry critical path.

## 2. Timing / logging findings

- **scan_perf logs point latency only**: each cycle emits one `[scan_perf]` line with `total_ms`, `scan_edges_ms`, `council_ms`, `execute_ms`, `candidates`. These are point-in-time per-cycle values.
- **no in-process p95/p99/max aggregation today**: there is no rolling distribution, percentile, variance, or tail tracker maintained inside the process.
- **jitter and tail spikes require offline log parsing**: because only point latency is logged, cycle-to-cycle variation and tail spikes can only be reconstructed by parsing many scan_perf lines after the fact.
- **offline p99 log parsing is safer than in-process aggregation**: deriving p95/p99/max from emitted scan_perf logs adds zero runtime code, zero behavior change, and zero new failure surface on the live path, whereas in-process aggregation would add state and complexity to the hot loop.
- **gate sequence is not timed separately today**: the added gate sequence (E5 → E10b → E11c → E11f) sits in the untimed interval between council timing and execute timing; no per-gate or per-finding breakdown and no per-gate short-circuit counts are recorded.

## 3. Config dependency / caching findings

- **config getattr reads are static-per-process**: gate thresholds (`DAILY_LOSS_LIMIT`, `MAX_TRADES_FIRST_SESSION`, `NO_FILL_BURST_LIMIT`, `FILL_TO_SUBMIT_MIN_SUBMISSIONS`, `FILL_TO_SUBMIT_FLOOR_RATIO`) plus `config.NEW_ENTRIES_ENABLED` / `config.MAX_OPEN_POSITIONS` are read via `getattr` on the already-imported `config` module; each read returns the same in-memory module attribute.
- **config.py changes require restart or re-import**: per standard Python import semantics, editing `config.py` is not picked up in-process; a restart (or explicit re-import) is required. The `getattr`-per-finding pattern does not provide hot-reload; it merely re-reads a static attribute. The runtime kill mechanism is the dynamic `_effective_risk_mode` (DB-backed) plus file-based `kill_switch_check()`, not config getattr.
- **config-value caching is not recommended now**: reading an imported module attribute is effectively free; caching would add staleness risk for no measurable gain.

## 4. No expensive reads introduced by E10/E11

No expensive DB/API/live reads were introduced by the E10/E11 gates; they are pure in-memory. The only DB touch on the entry gate is E5/E6's `_effective_risk_mode`, which predates E10/E11.

## 5. Decision

**optimize only after measured scan_perf/council_ms regression** or observed jitter/tail spikes. The added gates are negligible against council (network-bound), so there is no justification to optimize speculatively. Evidence must come first, ideally from offline parsing of existing scan_perf logs.

## 6. Future optional slices (behavior-neutral, none undertaken now)

- **future optional slice: scan_perf marker contract test** — pin the `total_ms/scan_edges_ms/council_ms/execute_ms/candidates` fields so the log contract cannot silently drift before any metrics work.
- **future optional slice: docs-only offline p95/p99 parsing recipe** — a documented recipe to compute p95/p99/max from emitted scan_perf logs without changing runtime behavior.
- **future optional slice: lightweight gate-block counters only if measured tail spikes** — add per-gate short-circuit counters or a rolling max only if offline analysis reveals tail spikes that warrant it.

## 7. Closure

This observation adds no code and changes no behavior. Live, Paper Soak, canary, D#2 (human DRY_RUN gate), and D#7 (phase-2 live balance probe) remain BLOCKED and are not affected by this artifact.
