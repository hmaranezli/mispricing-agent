# Post-Phase 6.2 Post-Run Roadmap & No-Auto-Activation Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only roadmap.** It locks the future phase sequence (A–H) after the raw-only 24h run and
  **explicitly forbids any automatic transition between phases**.
- It **authorizes no** audit implementation, **no** S1 ingestion/append, **no** stream activation,
  **no** calibration, **no** trading, **no** paper/canary/live, **no** capacity increase.
- It implements **nothing**; it edits **no** runtime / test / schema / config / lock / generated /
  tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Continuous Ledger Audit: RATIFIED boundary + TDD; implementation BLOCKED / UNSTARTED.**
- **S1 Stream Authorization / Production Append: BLOCKED / UNSTARTED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `133363cd57735c0de9aff53a1cab1a687476a3a2`.
- Parent chain:
  - `133363cd57735c0de9aff53a1cab1a687476a3a2` = **RATIFIED** S1 Stream Authorization Eligibility
    & Safety Preconditions Charter.
  - `baee0aacc7b7e235e4754792d173b9d0e726e4cb` = **RATIFIED** Read-Only Continuous Ledger Audit
    TDD Charter.
  - `bb7b73b4db4291e96547e72cc9cb332936886ccb` = **RATIFIED** Read-Only Continuous Ledger Audit
    Charter (boundary).
  - `cfd7015585c6a42272861e6f215a5c8e0532f74f` = **RATIFIED** Polymarket User-Agent runtime fix.
- Known run state (from prior operator report — live ledger not read for this charter):
  - 634 paired cycles, 1268 rows, 0 failures, HTTP 200 only, `s1_audit.sqlite3` absent,
    permissions 0700/0600, `stream_authorization=None`, ~7.3% of 8640 cycles.

## Section 2 — Charter Intent

- This charter is a **roadmap and a brake**, not an enabler. It enumerates the only permitted future
  sequence and binds each transition behind explicit, separately-ratified gates.
- It exists to make **drift, scope-creep, and auto-activation structurally impossible**: no phase
  may begin merely because the previous phase finished.

---

## Section 3 — Locked Phase Sequence

### Phase A — Raw Run Completion

1. The bounded raw-only 24h run must **complete or stop within ratified bounds**
   (`max_cycles ≤ 8640`, `sleep_interval = 10s`, `max_duration ≤ 86400s`, `failure_budget = 100`).
2. **Completion alone authorizes nothing** — not audit implementation, not S1, not calibration,
   not trading.
3. The `stop_reason` (`STOP_TIME`, `MAX_CYCLES`, or `SCHED_FAILURE_BUDGET_EXCEEDED`) must be
   **preserved** and recorded.
4. The final ledger must remain **append-only, 0700/0600, S1-absent**.

### Phase B — Read-Only Continuous Ledger Audit Implementation

1. **Only after** the run completes/stops may the ratified **Audit TDD Charter** be implemented.
2. Audit implementation must be strict **RED→GREEN** (initial RED fails because the audit module
   is absent).
3. The audit must open the ledger **read-only** (`file:?mode=ro`).
4. The audit must **not dump raw bodies** (no decoded / printed response payloads).
5. The audit must **not write S1** and must not write to any DB beyond test tmp fixtures.
6. The audit verdict may be **CLEAN** or **DIRTY** — but **cannot activate anything automatically**.

### Phase C — S1 Stream Authorization Eligibility

1. **Only a CLEAN audit** may make an S1 Stream Authorization Charter **eligible**.
2. **Eligibility is not execution.** A `CLEAN` verdict sets `s1_charter_eligible = True` and nothing
   more.
3. A **DIRTY** audit keeps S1 **BLOCKED** and requires a corrective charter.
4. **Raw-vs-semantic separation stays locked:**
   - The raw audit proves **forensic ledger integrity only**.
   - The S1 projection / adapter layer owns **semantic parse, `Decimal`/`int` validation, BID/ASK
     side-axiom, and the `<= 1000ms` cross-source time-boundary logic**
     (`MAX_CROSS_SOURCE_EVENT_TIME_DELTA_MS`).
   - The raw audit must never perform semantic projection; the S1 layer must never bypass the raw
     audit's integrity guarantees.

### Phase D — S1 Stream Authorization / Production Append Charter

1. Must be a **separate docs-only charter first**, independently reviewed.
2. Must authorize **exactly** what S1 append may do — no broader.
3. Must route **only** through the ratified **S1 Production Ingestion Adapter / Durable Writer**
   (`phase6_2_shadow_intent/s1_production_ingestion_adapter.py`). No parallel projection formula.
4. Must preserve **idempotency**, **dual-source SHA provenance**
   (`sha256(poly_sha + "|" + hl_sha)`), and **no rowid / sqlite_sequence as domain identity**.
5. Must **not** authorize calibration / trading / actionability.
6. **Capacity remains 0.**

### Phase E — S1 Append Runtime / Replay

1. **Only after** the S1 authorization charter **and** an S1 TDD charter may runtime append be
   considered.
2. Append must be **bounded, replayable, idempotent, and fail-closed**.
3. S1 database transactions must be **strictly atomic per pair-cycle**.
4. **Partial writes of a paired cycle are forbidden**; **rollback is mandatory** on any failure.
5. Any **rejected pair stays out of S1** (ratified projection failure literals propagate unchanged).
6. **No capital or trading path opens.** Capacity remains 0.

### Phase F — Calibration / Analysis Charter

1. **Only after** S1 append is ratified **and** S1 data is audited may calibration / analysis be
   considered.
2. The calibration charter must remain **offline / read-only at first**.
3. Analysis must use **explicit mathematical isolation** (no shared mutable state with S1).
4. Analysis must **not mutate S1 / audit data under any circumstances**.
5. **No** signal, order, trade, live, paper, canary, or capital activation.
6. Any edge / profit / mispricing analysis must be **explicitly non-actionable** unless later
   separately authorized.

### Phase G — Risk / Capacity Charter

1. **Capacity remains 0** until a separate risk / capacity charter is ratified.
2. Any nonzero capacity requires **explicit limits**: drawdown bounds, max notional, kill switch,
   and enumerated failure modes.
3. Kill-switch and drawdown conditions must be **defined mathematically**.
4. Kill-switch and drawdown conditions must **avoid subjective or discretionary metrics**.
5. **Clean data or calibration does not auto-increase capacity.**
6. The existing constitutional limits (single trade ≤ 5% capital, ≤ 5 open positions, daily loss
   10% → full halt, `HUMAN_APPROVAL_USD` gate) remain binding floors and may only be tightened,
   never relaxed, by a future charter.

### Phase H — Paper / Canary / Live

1. **Paper trading** requires a separate charter.
2. **Canary** requires a separate charter **after** paper.
3. **Live** requires a separate charter **after** canary.
4. **No automatic transition** between paper → canary → live.
5. **No hidden order routing.** Every order path must be explicit, logged, and human-gated where the
   constitution requires.
6. Live activation (`DRY_RUN=False`) remains subject to the constitution: it occurs **only** by the
   human's explicit written command and **never** autonomously.

---

## Section 4 — Global No-Auto-Activation Law

**No phase completion automatically starts the next phase.** Every transition requires, in order:

1. A **docs-only boundary charter** defining the next phase's scope and limits.
2. **Independent review / ratification** of that charter.
3. A **TDD charter** if code is needed.
4. A strict **RED→GREEN implementation** if code is needed.
5. An **explicit operator command** if runtime execution is needed.

Any attempt to skip a step, collapse two steps, or treat a prior ratification as implying the next
is a **hard charter violation** and voids the transition.

## Section 5 — Phase Transition Ledger (template, to be completed later)

No transition is asserted now. Each future transition must be recorded here with the five required
artifacts before it may proceed:

| Transition | Boundary charter | Reviewed | TDD charter | RED→GREEN | Operator cmd |
|------------|------------------|----------|-------------|-----------|--------------|
| A → B | PENDING | PENDING | PENDING | PENDING | n/a |
| B → C | PENDING | PENDING | n/a | n/a | n/a |
| C → D | PENDING | PENDING | PENDING | PENDING | PENDING |
| D → E | PENDING | PENDING | PENDING | PENDING | PENDING |
| E → F | PENDING | PENDING | PENDING | PENDING | PENDING |
| F → G | PENDING | PENDING | PENDING | PENDING | PENDING |
| G → H | PENDING | PENDING | PENDING | PENDING | PENDING |

## Section 6 — Next Gates

Only next safe gates:

1. Independent review of this roadmap charter.
2. Phase A: 24h run completes or stops within ratified bounds (`stop_reason` preserved).
3. Phase B: RED→GREEN audit implementation (per ratified Audit TDD Charter) — separately gated.
4. Each subsequent phase strictly behind the five-step Global No-Auto-Activation Law.

## Post-state

- Post-Run Roadmap & No-Auto-Activation Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit: **RATIFIED** boundary + TDD; implementation **BLOCKED / UNSTARTED**.
- S1 Stream Authorization / Production Append: **BLOCKED / UNSTARTED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
