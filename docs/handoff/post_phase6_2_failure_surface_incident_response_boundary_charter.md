# Post-Phase 6.2 Failure Surface / Incident Response Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the requirements for future failure-surface classification
  and incident response. It is **not** an incident handler, **not** a monitoring implementation,
  **not** runtime logic. It **implements nothing** and **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** implementation, monitoring, alerting, halt, restart, rollback, S1 append,
  production S1 stream, calibration / trading / actionability, paper / canary / live, routing,
  orders, fills, cancels, sizing, allocation, capital deployment, or capacity.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Operator Authorization / Human Command Boundary Charter: RATIFIED at `1a35aea`.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.** **Paper / canary / live: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `1a35aeafc256811c4849b5b6b46a51508f65461d`.
- Parent chain:
  - `1a35aeafc256811c4849b5b6b46a51508f65461d` = **RATIFIED** Operator Authorization / Human
    Command Boundary Charter.
  - `c1f78f91b0a25295c0093fbc3d3a208eca4a1fdc` = **RATIFIED** Paper / Canary / Live Separation &
    Activation Firewall Boundary Charter.
  - `267e6e05b525f64ccbed442d809f5af8a20e6460` = **RATIFIED** Out-of-Sample / Replay Validation
    TDD Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter.
- This charter defines the cross-cutting **failure-surface / incident-response** boundary. It does
  not supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- This charter draws the **incident boundary**: how failures must be classified, what severity
  bands mean, what conditions force fail-closed, what an incident report may contain, and what
  incident handling may **never** trigger.
- It exists to make **incident-driven activation, retry storms, automatic rollback, and
  "incident⇒capacity" drift structurally impossible**.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only Failure / Incident Boundary

1. This charter defines **requirements only**.
2. It **does not implement** monitoring, alerting, rollback, halt, restart, audit, S1 append,
   trading, or capacity.
3. It **authorizes no runtime behavior.**

### Gate B — Preconditions Before Future Incident-Response Work

Future incident-response work requires:

1. raw-only run **complete or explicitly stopped**;
2. Read-Only Continuous Ledger Audit **CLEAN, or explicitly DIRTY with documented failure**;
3. semantic projection validation **state known**;
4. calibration / validation / risk boundaries **preserved**;
5. paper / canary / live firewall **preserved**;
6. operator authorization boundary **preserved**;
7. an **exact future command naming the incident-response scope**;
8. **DIRTY state blocks implementation** unless the explicit task is **documentation-only failure
   classification**.

### Gate C — Failure Surface Taxonomy

Future classification must define a closed taxonomy covering at least:

- **data acquisition failure** (capture did not occur);
- **HTTP / transport failure** (non-2xx, timeout, transport error);
- **timestamp authority failure** (missing/ambiguous source event time);
- **raw ledger integrity failure** (append-only breach, sequence gap, permission drift);
- **paired-cycle completeness failure** (orphan / lone / duplicate / mismatched legs);
- **semantic projection failure** (ratified `S1_*` literal raised);
- **provenance / source authority failure** (wrong authority / SHA mismatch);
- **replay determinism failure** (non-repeatable result);
- **calibration / validation leakage failure** (lookahead / contamination);
- **risk / capacity boundary failure** (limit / kill-switch input invalid);
- **S1 append authorization failure** (append attempted without authorization);
- **unexpected runtime exception** (unclassified error → fail closed).

Each classified failure must map to exactly one taxonomy class; an unmappable failure is treated as
**unexpected runtime exception** and fails closed.

### Gate D — Severity Levels

Future severity bands only (labels carry **no** trading / actionability / capacity authority):

- **INFO** — non-actionable observation.
- **WARN** — degraded but bounded condition.
- **DIRTY** — audit / validation failure requiring explicit review.
- **HALT_REQUIRED** — future runtime must stop before any further processing.
- **INCIDENT** — operator-facing incident requiring explicit human review.

Severity is a **descriptive label only**; it must never, by itself, initiate a trade, allocation,
capacity change, or any other action.

### Gate E — Fail-Closed Doctrine

Future systems must **fail closed** for:

- missing provenance;
- ambiguous failure class;
- contradictory status;
- unknown severity;
- incomplete raw pair;
- non-2xx capture;
- timestamp mismatch beyond ratified tolerance (`> MAX_CROSS_SOURCE_EVENT_TIME_DELTA_MS`);
- dirty audit;
- S1 append attempt without authorization;
- any attempt to convert incident status into signal / trade / capacity.

The default in every ambiguous or error state is the **safe / blocked** outcome.

### Gate F — Incident Report Boundary

Future incident reports must be:

- **offline / report-only** unless separately authorized;
- **provenance-bound**;
- **timestamped**;
- **commit / base-SHA-bound**;
- **source-authority-bound**;
- **deterministic and reproducible**;
- **non-actionable**;
- **not based on SQLite `rowid` / `append_sequence`** as a domain identity (identity derives from
  content / provenance hashes only).

### Gate G — Halt / Restart / Rollback Separation

1. This charter **does not authorize** halt, restart, rollback, or recovery.
2. Future **halt** policy requires a separate charter.
3. Future **restart** policy requires a separate charter.
4. Future **rollback / recovery** policy requires a separate charter.
5. Any halt / restart / rollback command must satisfy the ratified **Operator Authorization / Human
   Command Boundary Charter** (`1a35aea`).

### Gate H — Forbidden Incident-Response Paths

The following automatic transitions are **explicitly forbidden**:

- `incident ⇒ trade`
- `incident ⇒ capacity`
- `dirty audit ⇒ automatic rollback`
- `dirty audit ⇒ automatic S1 append`
- `warning ⇒ signal`
- `exception ⇒ retry storm`
- `scheduler event ⇒ recovery`
- `model inference ⇒ incident suppression`
- `clean incident report ⇒ operational activation`

Each requires, instead, a separate explicit operator command satisfying the Operator Authorization
boundary.

### Gate I — Output Boundary

1. This charter may only produce **documentation**.
2. **No** alerting implementation.
3. **No** monitoring implementation.
4. **No** runtime halt / restart / rollback implementation.
5. **No** S1 append.
6. **No** production stream.
7. **No** signal / trade / order / routing / capital output.
8. **Capacity remains 0.**

### Gate J — Next Gate / No Auto-Activation

1. Future incident-response TDD or implementation requires a **separate explicit operator command**.
2. Ratifying this charter **does not** make incident-response implementation eligible by itself.
3. **Clean state does not auto-advance.**
4. **Capacity remains 0.**

---

## Section 4 — Failure Classification Ledger (template, to be completed later)

No incident is asserted now. A future incident-response charter / implementation must map each
classified failure into this structure (documentation-only here):

| Failure class | Severity band | Fail-closed action | Provenance bound | Status |
|---------------|---------------|--------------------|------------------|--------|
| data_acquisition | PENDING | PENDING | PENDING | PENDING |
| http_transport | PENDING | PENDING | PENDING | PENDING |
| timestamp_authority | PENDING | PENDING | PENDING | PENDING |
| raw_ledger_integrity | PENDING | PENDING | PENDING | PENDING |
| paired_cycle_completeness | PENDING | PENDING | PENDING | PENDING |
| semantic_projection | PENDING | PENDING | PENDING | PENDING |
| provenance_source_authority | PENDING | PENDING | PENDING | PENDING |
| replay_determinism | PENDING | PENDING | PENDING | PENDING |
| calibration_validation_leakage | PENDING | PENDING | PENDING | PENDING |
| risk_capacity_boundary | PENDING | PENDING | PENDING | PENDING |
| s1_append_authorization | PENDING | PENDING | PENDING | PENDING |
| unexpected_runtime_exception | PENDING | PENDING | PENDING | PENDING |

All rows remain PENDING; none authorizes any action.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this failure-surface / incident-response boundary charter.
2. The full Gate B precondition chain, each step separately ratified.
3. Only after an explicit operator command: a separate incident-response TDD charter, then a
   RED→GREEN implementation.
4. Halt / restart / rollback each remain behind their own separate charters and the Operator
   Authorization boundary.

## Post-state

- Failure Surface / Incident Response Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Capacity: **0**.
