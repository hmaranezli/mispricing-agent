# Post-Phase 6.2 Paper / Canary / Live Separation & Activation Firewall Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the firewall and separation requirements for the future
  paper / canary / live operational modes. It is a **firewall, not an activation**. It
  **implements nothing** and **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** implementation, S1 append, production S1 stream, paper trading, canary
  trading, live trading, routing, orders, fills, cancels, sizing, allocation, capital deployment,
  calibration / trading / actionability, or capacity.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Out-of-Sample / Replay Validation TDD Charter: RATIFIED at `267e6e0`.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.** **Paper / canary / live: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `267e6e05b525f64ccbed442d809f5af8a20e6460`.
- Parent chain:
  - `267e6e05b525f64ccbed442d809f5af8a20e6460` = **RATIFIED** Out-of-Sample / Replay Validation
    TDD Charter.
  - `e57e8cfe03a9ac9b3412215f7fd0c8bbce049024` = **RATIFIED** Out-of-Sample / Replay Validation
    Boundary Charter.
  - `dc587fbd22d137ec2094d8d17af727238909c267` = **RATIFIED** Phase G Risk / Capacity Mathematical
    Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter (Phase H: paper → canary → live).
- This charter elaborates **Phase H** (paper / canary / live separation) of the ratified Post-Run
  Roadmap. It does not supersede, relax, or accelerate any prior gate.

## Section 2 — Constitutional Anchoring (binding floors)

The existing constitution (`CLAUDE.md`) governs any future live transition and remains a binding
floor this charter only tightens, never relaxes:

- `DRY_RUN=True` is default; live (`DRY_RUN=False`) only by **explicit human written command** —
  never autonomously.
- Single trade ≤ 5% of max capital; ≤ 5 simultaneous open positions; daily loss 10% → full halt;
  positions above `HUMAN_APPROVAL_USD` require human approval.
- `config.py` guardrail constants are immutable without human action.

## Section 3 — Boundary Gates

### Gate A — Future-Only Operational-Mode Firewall

1. This charter defines **future requirements only**.
2. It **does not authorize** paper / canary / live.
3. It **does not authorize** tests, implementation, runtime, S1 append, trading, routing, or
   capacity.

### Gate B — Preconditions Before Any Future Operational-Mode Work

Future operational-mode work requires **all** prior gates complete and clean, in order:

1. raw-only 24h run **complete / stopped**;
2. Read-Only Continuous Ledger Audit **CLEAN**;
3. semantic projection validation **clean**;
4. calibration / analysis boundary **satisfied**;
5. out-of-sample / replay validation **satisfied**;
6. risk / capacity boundary **satisfied**;
7. an **explicit separate command for the specific mode**;
8. any **DIRTY** state **blocks** all future mode work.

### Gate C — Paper Mode Separation

1. Paper requires its **own future charter**.
2. Paper must use **synthetic / non-executable outputs only** — no order ever reaches a venue.
3. Paper must **not share state** with canary / live.
4. Paper must **not imply** canary / live eligibility.
5. Passing paper must **not unlock capacity**.

### Gate D — Canary Mode Separation

1. Canary requires its **own future charter**.
2. Canary **cannot inherit paper state** as authority.
3. Canary must have **independent kill-switches and capacity boundaries**.
4. Canary must **not imply** live eligibility.
5. Passing canary must **not unlock live**.

### Gate E — Live Mode Separation

1. Live requires its **own future charter**.
2. Live **cannot be reached through automatic promotion**.
3. Live requires **explicit human / operator authorization** in a separate future gate (and, per
   the constitution, an explicit written command to set `DRY_RUN=False`).
4. Live must remain **BLOCKED** here.

### Gate F — State Isolation Requirements

1. **No shared mutable state** across paper / canary / live.
2. **No shared wallet / account balance authority.**
3. **No shared order / routing state.**
4. **No shared realized PnL authority.**
5. **No SQLite `rowid` / `append_sequence` as a domain identity** — identity derives from content /
   provenance hashes only.
6. **Provenance must bind every mode-specific artifact** (commit SHA, config fingerprint, mode id,
   deterministic key).

### Gate G — Kill-Switch and Capacity Firewall

1. Each future mode must have **independent kill-switches** (no shared kill-switch state that could
   mask a trip in one mode).
2. **Capacity remains 0** unless a later explicit capacity gate authorizes otherwise.
3. Any **missing, stale, ambiguous, or contradictory kill-switch input fails closed** (capacity
   forced to 0).
4. **No** profitable backtest, clean validation, or paper result can **bypass capacity**.

### Gate H — Forbidden Activation Paths

The following automatic transitions are **explicitly forbidden**:

- `validation ⇒ paper`
- `paper ⇒ canary`
- `canary ⇒ live`
- `clean audit ⇒ S1 append`
- `clean audit ⇒ capacity`
- `good calibration ⇒ capacity`
- `good replay ⇒ capacity`
- `any model score ⇒ order / routing / actionability`

Each arrow above requires, instead, a separate boundary charter, independent review, a TDD charter
if code is needed, a RED→GREEN implementation, and an explicit operator command (per the ratified
Post-Run Roadmap & No-Auto-Activation Charter).

### Gate I — Output Boundary

1. This charter may only produce **documentation**.
2. **No** signal, ranking, advice, order, route, fill, cancel, sizing, allocation, capital, S1
   append, production stream, or actionable output.
3. **Capacity remains 0.**

### Gate J — Next Gate / No Auto-Activation

1. Future paper / canary / live charters require **separate explicit commands**.
2. This charter **does not make any operational mode eligible by itself**.
3. It only **preserves the firewall** and defines future separation requirements.
4. **Capacity remains 0.**

---

## Section 4 — Mode Separation Ledger (template, to be completed later)

No mode is asserted now. Each future mode charter must populate its row before any work in that
mode may begin:

| Mode | Own charter | Preconditions met | Independent kill-switch | State isolated | Capacity | Status |
|------|-------------|-------------------|-------------------------|----------------|----------|--------|
| paper | PENDING | PENDING | PENDING | PENDING | 0 | BLOCKED |
| canary | PENDING | PENDING | PENDING | PENDING | 0 | BLOCKED |
| live | PENDING | PENDING | PENDING | PENDING | 0 | BLOCKED |

All rows remain BLOCKED at capacity 0 until each mode's own charter is separately ratified and an
explicit operator command is issued.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this paper / canary / live separation & activation firewall charter.
2. The full Gate B precondition chain, each step separately ratified.
3. Only after an explicit operator command for the specific mode: a separate **Paper Mode Charter**,
   then (separately) a **Canary Mode Charter**, then (separately) a **Live Mode Charter** — each
   with its own review, TDD charter, RED→GREEN implementation, and operator command.

## Post-state

- Paper / Canary / Live Separation & Activation Firewall Charter: **BUILT / RATIFIABLE /
  UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Capacity: **0**.
