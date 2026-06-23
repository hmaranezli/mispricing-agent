# Post-Phase 6.2 Phase G — Risk / Capacity Mathematical Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the **mathematical preconditions** any future nonzero
  capacity must satisfy. It **implements nothing** and **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** S1 append, calibration, signal generation, paper trading, canary, live
  trading, routing, execution, orders, or capital use.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Semantic Projection Validation TDD Charter: RATIFIED at `68b0d9c`.**
- **S1 Stream Authorization / Production Append: BLOCKED / UNSTARTED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `68b0d9c47490a3a208a8735d8ed89e595284b054`.
- Parent chain:
  - `68b0d9c47490a3a208a8735d8ed89e595284b054` = **RATIFIED** Semantic Projection Validation TDD
    Charter.
  - `905ee7591111c45ce501977e1063e3edb2051a30` = **RATIFIED** Semantic Projection Validation
    Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter (Phase G is sequenced there).
- This charter elaborates **Phase G** of the ratified Post-Run Roadmap. It does not supersede,
  relax, or accelerate any prior gate.

## Section 2 — Constitutional Anchoring (binding floors)

The existing constitution (`CLAUDE.md`) already defines **non-negotiable floors** that this charter
treats as **lower bounds** — any future risk/capacity charter may only **tighten**, never relax,
them:

- Single trade ≤ **5%** of max capital.
- At most **5** simultaneous open positions.
- Daily loss reaching **10%** → **full system halt**.
- Positions above `HUMAN_APPROVAL_USD` require **explicit human approval**.
- `DRY_RUN=True` is default; live (`DRY_RUN=False`) only by explicit human written command.
- `config.py` guardrail constants are immutable without human action.

This charter adds **mathematical structure** on top of those floors; it does not redefine them.

---

## Section 3 — Boundary Gates

### Gate A — Phase G Scope

1. This charter is **future-only**.
2. It **does not unlock capacity**.
3. It creates **no** risk runtime, execution runtime, order routing, paper trading, canary, or live
   trading.
4. It **only** defines the mathematical boundary requirements that must **exist and be ratified**
   before any later capacity charter can even be considered.

### Gate B — Precondition Chain

Nonzero capacity can **only** be considered after **all** prior gates are separately complete and
ratified, in order:

1. raw-only 24h run **completed / stopped**;
2. Read-Only Continuous Ledger Audit **CLEAN**;
3. S1 Stream Authorization **separately ratified**;
4. S1 append / projection **separately ratified and clean**;
5. semantic projection validation **separately implemented and clean**;
6. calibration / analysis **separately chartered and completed**;
7. out-of-sample or replay validation **separately ratified**;
8. risk / capacity implementation TDD **separately ratified**.

No step may be skipped, merged, or assumed from a prior ratification.

### Gate C — Capacity Remains Zero

1. Current capacity must remain **exactly 0**.
2. **No** capital, notional, wallet, balance, portfolio, position, order, route, fill, trade, or
   execution authority is created by this charter.
3. Any future nonzero capacity requires a **new explicit user command** and a **separate charter**.

### Gate D — Mathematical Risk Limits (required before any future capacity unlock)

The future system must define **all** of the following as **explicit formulas** (units, source,
and computation pinned). **No subjective or prose-only risk limit may be accepted.**

| Limit | Meaning (future formula must be explicit) |
|-------|-------------------------------------------|
| `max_notional_per_order` | hard cap on a single order's notional |
| `max_notional_per_market` | hard cap on aggregate notional per market |
| `max_total_open_notional` | hard cap on total open notional across all markets |
| `max_daily_loss` | hard cap on realized loss per UTC day → halt |
| `max_session_loss` | hard cap on realized loss per session → halt |
| `max_drawdown` | hard cap on peak-to-trough equity drawdown → halt |
| `max_consecutive_failures` | hard cap on consecutive failed cycles/orders → halt |
| `max_slippage` | hard cap on accepted slippage per fill |
| `max_staleness_ms` | hard cap on input data age (ms) |
| `max_order_age_ms` | hard cap on in-flight order age (ms) |
| `max_unhedged_exposure` | hard cap on net unhedged exposure |
| `max_inventory_imbalance` | hard cap on inventory/leg imbalance |

Each must be a deterministic numeric bound with an explicit comparison operator; no discretionary
"as appropriate" wording.

### Gate E — Kill-Switch Requirements

Future kill-switches must be **mathematical, deterministic, and fail-closed**. Each of the
following conditions, when true, must **force capacity back to 0**:

- `realized_loss >= max_daily_loss`
- `session_loss >= max_session_loss`
- `drawdown >= max_drawdown`
- `consecutive_failures >= max_consecutive_failures`
- `stale_data_ms > max_staleness_ms`
- `missing_required_feed == true`
- `non_idempotent_state_detected == true`
- `unknown_execution_state == true`
- `s1_provenance_mismatch == true`
- `ledger_audit_inconsistency == true`

A kill-switch trigger is **one-way to safe**: it sets capacity to 0 and requires explicit human
re-authorization to leave the halted state. No autonomous re-arm.

### Gate F — Fail-Closed Doctrine

Capacity must be **denied (no capacity)** whenever:

- a required risk value is **missing**;
- a risk value is **invalid**;
- a risk value is **NaN / Inf / negative / overflow**;
- there is **clock ambiguity**;
- there is **unknown position state**;
- there is **partial write or partial fill uncertainty**;
- there is **any unclassified error**.

The default in every ambiguous or error state is **zero capacity** — never a permissive fallback.

### Gate G — Separation from Calibration and Signal Logic

1. Risk / capacity logic **cannot manufacture** edge, signal, ranking, advice, or trade decisions.
2. Calibration **may estimate distributions** but **cannot unlock capacity by itself**.
3. Risk boundaries consume **only separately ratified inputs**.
4. **No "profitable backtest therefore capacity" shortcut.** A favorable analysis result is never,
   on its own, an authorization.

### Gate H — State and Provenance Requirements

Any future capacity calculation must be **tied to**:

- the ratified **commit SHA**;
- **S1 / audit provenance**;
- **calibration artifact provenance**;
- **replay / out-of-sample evidence**;
- an **explicit risk parameter source**;
- a **deterministic idempotency key**.

**SQLite `rowid` / `sqlite_sequence` must never be a domain identity.** Identity derives from
content/provenance hashes only.

### Gate I — Paper / Canary / Live Separation

1. **Paper trading** requires a separate charter.
2. **Canary** requires a separate charter.
3. **Live** requires a separate charter.
4. Passing paper **does not auto-enable** canary.
5. Passing canary **does not auto-enable** live.
6. All three maintain **independent kill-switch and capacity boundaries** — no shared mutable
   capacity state that could cross-contaminate stages.

### Gate J — Next Gate

1. This charter only makes a future **Risk / Capacity TDD Charter** *eligible* — and only after the
   full Gate B precondition chain is separately satisfied and ratified.
2. It **does not authorize** implementation.
3. It **does not authorize** tests.
4. It **does not authorize** S1, trading, paper, canary, live, or capacity.
5. **Capacity remains 0.**

---

## Section 4 — Risk Parameter Provenance Ledger (template, to be completed later)

No value is asserted now. A future Risk / Capacity charter must populate this with explicit
formulas and sources before any capacity may be considered:

| Limit | Formula | Unit | Source | Operator | Status |
|-------|---------|------|--------|----------|--------|
| max_notional_per_order | PENDING | PENDING | PENDING | PENDING | PENDING |
| max_notional_per_market | PENDING | PENDING | PENDING | PENDING | PENDING |
| max_total_open_notional | PENDING | PENDING | PENDING | PENDING | PENDING |
| max_daily_loss | PENDING | PENDING | PENDING | PENDING | PENDING |
| max_session_loss | PENDING | PENDING | PENDING | PENDING | PENDING |
| max_drawdown | PENDING | PENDING | PENDING | PENDING | PENDING |
| max_consecutive_failures | PENDING | PENDING | PENDING | PENDING | PENDING |
| max_slippage | PENDING | PENDING | PENDING | PENDING | PENDING |
| max_staleness_ms | PENDING | PENDING | PENDING | PENDING | PENDING |
| max_order_age_ms | PENDING | PENDING | PENDING | PENDING | PENDING |
| max_unhedged_exposure | PENDING | PENDING | PENDING | PENDING | PENDING |
| max_inventory_imbalance | PENDING | PENDING | PENDING | PENDING | PENDING |

All rows must carry an explicit deterministic formula and a ratified source before a Risk / Capacity
TDD Charter may be drafted.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this Phase G mathematical boundary charter.
2. The full Gate B precondition chain, each step separately ratified.
3. Only then: a separate **Risk / Capacity TDD Charter**.
4. Only after that, separately: paper → canary → live, each behind its own charter and operator
   command (per the ratified Post-Run Roadmap & No-Auto-Activation Charter, Phase H).

## Post-state

- Phase G Risk / Capacity Mathematical Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 Stream Authorization / Production Append: **BLOCKED / UNSTARTED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
