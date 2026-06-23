# Post-Phase 6.2 Halt / Restart / Rollback / Recovery Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the requirements for future halt, restart, rollback, and
  recovery actions. It **performs and authorizes no** halt / restart / rollback / recovery. It
  **implements nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** halt, restart, rollback, recover, signal, kill, detach, or mutate any process,
  and does **not** disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** implementation, monitoring, alerting, runtime logic, S1 append, production
  S1 stream, calibration / trading / actionability, paper / canary / live, routing, orders, fills,
  cancels, sizing, allocation, capital deployment, or capacity.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Failure Surface / Incident Response Boundary Charter: RATIFIED at `392cb8c`.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.** **Paper / canary / live: BLOCKED.**
- **Halt / restart / rollback / recovery: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `392cb8cc1fdb943aa671040daeeaf376c230b6a4`.
- Parent chain:
  - `392cb8cc1fdb943aa671040daeeaf376c230b6a4` = **RATIFIED** Failure Surface / Incident Response
    Boundary Charter.
  - `1a35aeafc256811c4849b5b6b46a51508f65461d` = **RATIFIED** Operator Authorization / Human
    Command Boundary Charter.
  - `c1f78f91b0a25295c0093fbc3d3a208eca4a1fdc` = **RATIFIED** Paper / Canary / Live Separation &
    Activation Firewall Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter.
- This charter defines the **halt / restart / rollback / recovery** boundary referenced by the
  ratified Incident Response charter (Gate G). It does not supersede, relax, or accelerate any prior
  gate.

## Section 2 — Charter Intent

- This charter draws the **recovery boundary**: how halt, restart, rollback, and recovery must each
  remain **separately gated, non-automatic, evidence-preserving, and operator-authorized**.
- It exists to make **automatic recovery chains, evidence rewriting, dirty-to-clean laundering, and
  "recovery⇒capacity" drift structurally impossible**.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only Recovery Boundary

1. This charter defines **requirements only**.
2. It **does not implement** halt, restart, rollback, recovery, monitoring, alerting, runtime
   logic, S1 append, trading, or capacity.
3. It **authorizes no runtime behavior.**

### Gate B — Preconditions Before Any Future Halt / Restart / Rollback / Recovery Work

Future work requires:

1. Failure Surface / Incident Response Boundary Charter **ratified**;
2. Operator Authorization / Human Command Boundary Charter **ratified**;
3. an **exact future operator command naming the requested action type** (halt / restart /
   rollback / recovery);
4. the **exact commit / base SHA**;
5. the **exact incident or failure report reference** (if applicable);
6. the **exact allowed files / subsystems**;
7. the **exact forbidden actions**;
8. the **explicit S1 append state**;
9. the **explicit capacity state**;
10. the **explicit paper / canary / live state**;
11. **DIRTY state blocks implementation** unless the explicit task is **documentation-only
    classification**.

### Gate C — Halt Boundary

1. Future halt policy requires its **own separate charter**.
2. Halt must **never imply restart**.
3. Halt must **never imply rollback**.
4. Halt must **never imply S1 append**.
5. Halt must **never imply trading / actionability**.
6. Halt must be **fail-closed and operator-authorized**.
7. A **missing / ambiguous halt reason fails closed**.

### Gate D — Restart Boundary

1. Future restart policy requires its **own separate charter**.
2. Restart must **never be automatic**.
3. Restart must **not** be triggered by scheduler / timer / model / incident severity **alone**.
4. Restart must require an **explicit operator command**.
5. Restart must **not inherit stale state** as valid authority.
6. Restart must **not imply** S1 append, trading, paper / canary / live, or capacity.

### Gate E — Rollback Boundary

1. Future rollback policy requires its **own separate charter**.
2. Rollback must **never mutate raw ledger evidence**.
3. Rollback must **never rewrite append-only audit artifacts**.
4. Rollback must **never erase provenance**.
5. Rollback must require an **exact target commit / artifact reference**.
6. Rollback must **not imply** restart, S1 append, trading, or capacity.

### Gate F — Recovery Boundary

1. Future recovery policy requires its **own separate charter**.
2. Recovery must be **evidence-preserving**.
3. Recovery must be **reproducible**.
4. Recovery must **bind to exact provenance and operator command**.
5. Recovery must **not convert dirty evidence into clean evidence**.
6. Recovery must **not suppress incident reports**.
7. Recovery must **not create actionable trading output**.

### Gate G — Forbidden Automatic Paths

The following automatic transitions are **explicitly forbidden**:

- `incident ⇒ halt`
- `halt ⇒ restart`
- `incident ⇒ restart`
- `dirty audit ⇒ rollback`
- `rollback ⇒ restart`
- `restart ⇒ S1 append`
- `recovery ⇒ capacity`
- `warning ⇒ retry loop`
- `scheduler event ⇒ recovery`
- `model inference ⇒ restart`
- `clean recovery report ⇒ operational activation`

Each requires, instead, a separate explicit operator command satisfying the Operator Authorization
boundary.

### Gate H — Provenance and Audit Requirements

Future halt / restart / rollback / recovery records must be:

- **operator-command-bound**;
- **commit / base-SHA-bound**;
- **incident / failure-reference-bound**;
- **timestamped**;
- **source-authority-bound**;
- **deterministic and reproducible**;
- **evidence-preserving**;
- **not based on SQLite `rowid` / `append_sequence`** as a domain identity (identity derives from
  content / provenance hashes only);
- **stored only in a separately authorized mechanism** (this charter creates no such store).

### Gate I — Output Boundary

1. This charter may only produce **documentation**.
2. **No** halt command.
3. **No** restart command.
4. **No** rollback command.
5. **No** recovery command.
6. **No** monitoring or alerting implementation.
7. **No** S1 append.
8. **No** production stream.
9. **No** signal / trade / order / routing / capital output.
10. **Capacity remains 0.**

### Gate J — Next Gate / No Auto-Activation

1. A future **Halt Policy Charter** requires a separate explicit operator command.
2. A future **Restart Policy Charter** requires a separate explicit operator command.
3. A future **Rollback Policy Charter** requires a separate explicit operator command.
4. A future **Recovery Policy Charter** requires a separate explicit operator command.
5. Ratifying this charter **does not** make implementation eligible by itself.
6. **Clean state does not auto-advance.**
7. **Capacity remains 0.**

---

## Section 4 — Recovery Action Field Checklist (template, to be completed later)

No action is asserted now. Every future halt / restart / rollback / recovery command must satisfy
this checklist before it is treated as authorization:

| Field | Requirement | Present? |
|-------|-------------|----------|
| action_type | exact (halt / restart / rollback / recovery) | PENDING |
| base_sha | exact commit/base SHA | PENDING |
| incident_ref | exact incident/failure report reference (if applicable) | PENDING |
| allowed_scope | exact files/subsystems | PENDING |
| forbidden_actions | exact list | PENDING |
| s1_append_state | exact (DENIED unless an S1 charter authorizes) | PENDING |
| capacity_state | exact (0 unless a capacity gate authorizes) | PENDING |
| pcl_state | exact paper/canary/live state | PENDING |
| operator_identity | attributable + timestamped | PENDING |
| evidence_preserving | true (no raw/audit mutation, no provenance erase) | PENDING |

Any PENDING / missing / conflicting field ⇒ **no authorization** (fail closed).

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this halt / restart / rollback / recovery boundary charter.
2. The full Gate B precondition chain, each step separately ratified.
3. Only after an explicit operator command for the specific action: a separate **Halt Policy
   Charter**, **Restart Policy Charter**, **Rollback Policy Charter**, or **Recovery Policy
   Charter** — each with its own review, TDD charter, RED→GREEN implementation, and operator
   command.

## Post-state

- Halt / Restart / Rollback / Recovery Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Halt / restart / rollback / recovery: **BLOCKED**.
- Capacity: **0**.
