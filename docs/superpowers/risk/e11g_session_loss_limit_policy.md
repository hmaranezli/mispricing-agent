# E11g — SESSION_LOSS_LIMIT Policy Decision (docs-only)

**Date:** 2026-06-15
**Slice:** E11g (Master E closeout — risk-control hard caps)
**Type:** Policy decision artifact. No enforcement code, no config constant, no schema change.

## VERDICT: DEFERRED

SESSION_LOSS_LIMIT is **DEFERRED** for the current micro-canary. This document records the decision and its rationale so the "remaining Master E item" is closed by an explicit, traceable decision rather than by adding a redundant or restart-evadeable breaker.

The single-line statement of record: **DAILY_LOSS_LIMIT covers session-loss for micro-canary**.

In this slice, **SESSION_LOSS_LIMIT is not implemented as an enforcement breaker**.

## 1. Why deferred

The capital-protection layer already exists and is restart-safe:

- `monitor/circuit_breaker.py::daily_loss_halt(start_of_day_equity, realized_pnl_today)` computes `loss_pct = max(0, -realized_pnl_today / start_of_day_equity)` and returns `"daily_loss_stop"` when `loss_pct >= DAILY_LOSS_LIMIT` (currently `0.35`, NET realized PnL based, E7 micro-canary budget).
- It is **DB-backed** through `RiskStateSnapshot` (`monitor/risk_state_store.py`, sqlite singleton row) and keyed to the **UTC trading day** (`trading_day_utc`), with `rollover_risk_state_if_new_day` resetting daily counters at 00:00 UTC while preserving structural blockers.
- The denominator is locked to `snapshot.start_of_day_equity` (same-day lock), not current equity.
- It maps `daily_loss → "daily_loss" blocker → Exit-Only` mode, consulted by the main-loop entry gate (`_effective_risk_mode() != "Operational" → continue`).

DAILY_LOSS_LIMIT is therefore the restart-safe capital-protection layer, and it already bounds NET realized loss per UTC day. For the micro-canary (approximately one runtime session per UTC day), a separate session-loss cap would measure nearly the same NET realized loss and would be largely redundant, creating double-blocking risk with no marginal protection.

## 2. What "session" means in this codebase today

Current "session" in this codebase means **process-runtime only**: the in-memory counters `_SESSION_TRADE_COUNT` (E10c), `_NO_FILL_STREAK` (E11b), and `_SESSION_SUBMIT_COUNT` (E11e). There is no time-window session, no strategy-level session, and no DB-backed session state. The persisted risk-state is strictly day-level (UTC), never session-level.

Because the only available "session" is process-runtime and in-memory, it is **restart-unsafe**: a crash/restart loop resets the in-memory counters to zero, granting a fresh loss budget on each restart.

## 3. If a session-loss guard is ever built (future, not now)

- **in-memory session-loss is risk-awareness side-car, not capital protection.** Being **restart-unsafe**, an in-memory session-loss guard provides no protection against repeated restarts and must never be presented as a capital-protection control. It is at best a secondary risk-awareness side-car.
- Behavior must be **entry-only BLOCK** (Exit-Only mode), **never full halt**. Mirroring DAILY_LOSS_LIMIT, a session-loss trip must block new entries only; **exit paths remain active** (`_monitor_positions`, `sell_position`, panic-flatten, monitoring). A full process halt that strands open positions is unsafe and is explicitly rejected.
- Config ownership: **SESSION_LOSS_LIMIT config constant is human-owned** and is **not** added in this slice. Claude does not invent, infer, widen, or silently set risk guardrail constants (CLAUDE.md §1 / E1b §12.7).

## 4. Scope guarantees for this slice

- **no schema migration** is performed here.
- **no DB-backed session state** is added here.
- No `session_loss_halt` predicate is added; `monitor/circuit_breaker.py` is unchanged.
- `config.py` is unchanged; no `SESSION_LOSS_LIMIT` constant is added.
- `monitor/risk_state.py`, `monitor/risk_state_store.py`, and `monitor/risk_sync.py` are unchanged.

## 5. Future work (explicitly gated)

Any **future DB-backed session loss requires explicit policy and migration**: new `RiskStateSnapshot` fields (e.g. session id, session-start equity, realized PnL per session), a `schema_version` bump with migration, a defined session-rollover trigger, and a new `session_loss → Exit-Only` blocker. This is high-complexity / low canary value and is not undertaken now.

## 6. Observation note

**DAILY_LOSS_LIMIT config/fallback observation required**: before relying on daily-loss as the sole capital-protection layer for any live canary, confirm by read-only observation that `config.DAILY_LOSS_LIMIT` is set as intended and that the `getattr(config, "DAILY_LOSS_LIMIT", 0.10)` fallback path is not silently active. This is an observation item, not enforcement, and does not unblock canary by itself.

## 7. Closure

This decision closes the remaining Master E SESSION_LOSS_LIMIT item by deferral. Paper Soak, canary, D#2 (human DRY_RUN gate), and D#7 (phase-2 live balance probe) remain BLOCKED and are not affected by this artifact.
