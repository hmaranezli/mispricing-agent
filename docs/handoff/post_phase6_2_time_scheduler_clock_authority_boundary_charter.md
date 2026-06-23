# Post-Phase 6.2 Time / Scheduler / Clock Authority Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the requirements proving that **time, clocks, timers, cron,
  schedulers, elapsed duration, market sessions, polling loops, and wall-clock events are never
  authority**. Time may be **evidence when explicitly scoped**, but must **never substitute** for an
  operator command, a clean audit, validation, S1 append authorization, runtime activation, trading,
  recovery, or capacity.
- It **implements nothing** and **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It **does not inspect or mutate** scheduler / cron / systemd / timer config, and **creates no**
  timers, jobs, schedulers, cron entries, or background services.
- It **does not inspect** secrets, env vars, credentials, tokens, cookies, API keys, or account
  balances.
- It performs **no** network request, **no** external service call, **no** test run.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** implementation, S1 append, production S1 stream, calibration / trading /
  actionability, paper / canary / live, halt / restart / rollback / recovery, routing, orders,
  fills, cancels, sizing, allocation, capital deployment, or capacity.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Configuration / Parameter / Feature-Flag Authority Boundary Charter: RATIFIED at `55e25ae`.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.** **Paper / canary / live: BLOCKED.**
- **Halt / restart / rollback / recovery: BLOCKED.**
- **Secrets / credentials / wallet / signing / capital authority: BLOCKED.**
- **External dependency / third-party service authority: BLOCKED.**
- **Model / agent authority: BLOCKED.** **Configuration / parameter / feature-flag authority:
  BLOCKED.**
- **Time / scheduler / clock authority: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `55e25ae9468f318805e475add6e542c14ab01b10`.
- Parent chain:
  - `55e25ae9468f318805e475add6e542c14ab01b10` = **RATIFIED** Configuration / Parameter /
    Feature-Flag Authority Boundary Charter.
  - `ff0fa0f5306f1dd3acec9a6e7239dd1dc0a36651` = **RATIFIED** Model / Agent Output Non-Authority
    Boundary Charter.
  - `4742d8c70417e67d1888c7394e36a0ae7aed7072` = **RATIFIED** External Dependency / Third-Party
    Service Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter.
- This charter defines the cross-cutting **time / scheduler / clock authority** boundary. It does
  not supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- This charter draws the **temporal non-authority line**: a clock reading, an elapsed duration, a
  scheduler tick, or a run-completion timestamp is **evidence at most**, never a command, never a
  validation result, never an authorization.
- It exists to make **"24h complete ⇒ audit clean", "audit clean ⇒ S1 append", "scheduler tick ⇒
  runtime", and "timeout ⇒ restart" drift structurally impossible**. It is consistent with the
  ratified scheduler runtime's existing discipline (retrieval timestamps are **forensic-only** and
  never substitute source event time).

---

## Section 3 — Boundary Gates

### Gate A — Future-Only Time / Scheduler Authority Boundary

1. This charter defines **requirements only**.
2. It **does not inspect** scheduler config.
3. It **does not create** timers or jobs.
4. It **does not authorize** runtime, S1 append, trading, paper / canary / live, recovery, routing,
   or capacity.

### Gate B — Preconditions Before Future Time / Scheduler Work

Future time / scheduler work requires:

1. Operator Authorization boundary **ratified**;
2. Configuration / Parameter / Feature-Flag boundary **ratified**;
3. Model / Agent Output Non-Authority boundary **ratified**;
4. an **exact future operator command**;
5. the **exact timer / scheduler / clock class**;
6. the **exact allowed files / subsystem**;
7. the **exact forbidden actions**;
8. the **explicit S1 append state**;
9. the **explicit capacity state**;
10. the **explicit paper / canary / live state**;
11. **DIRTY state blocks implementation** unless the task is **documentation-only**.

### Gate C — Time / Scheduler Class Taxonomy

Future classification must define a closed taxonomy covering at least:

- **wall-clock timestamps**;
- **monotonic clocks**;
- **exchange timestamps**;
- **provider timestamps**;
- **ledger commit timestamps**;
- **elapsed duration**;
- **cron / systemd timers**;
- **polling loops**;
- **retry / backoff schedules**;
- **market-session clocks**;
- **timeout / deadline values**;
- **run-completion timestamps**;
- **audit-window timestamps**.

Each time/scheduler item must map to exactly one class; an unclassifiable item is treated as the
most restrictive applicable class and **fails closed**.

### Gate D — Time Is Not Authority

Future systems must prove:

- **elapsed time does not imply authorization.**
- **run completion does not imply audit clean.**
- **audit clean does not imply S1 append.**
- **scheduler tick does not imply runtime permission.**
- **cron / systemd event does not imply execution authority.**
- **market open / close does not imply trading authority.**
- **timeout does not imply restart / recovery authority.**
- **polling interval does not imply external-service authority.**
- **timestamp presence does not imply source validity.**
- **timestamp match does not imply semantic validity.**
- **wall-clock event does not imply capacity.**

### Gate E — Clock Provenance and Timestamp Authority

Future timestamp use must be:

- **source-authority-bound**;
- **clock-class-bound** (which class from Gate C);
- **timezone / UTC policy explicit**;
- **monotonic-vs-wall-clock explicit**;
- **tolerance explicit** where applicable (e.g. the ratified `<= 1000 ms` cross-source delta applies
  to **source event timestamps**, never retrieval timestamps);
- **commit / base-SHA-bound** when used in validation / replay;
- **artifact-hash-bound** when persisted;
- **deterministic where replayed**;
- **not based on SQLite `rowid` / `append_sequence`** as a domain identity (identity derives from
  content / provenance hashes only);
- **rejected or quarantined** if missing, ambiguous, stale, or contradictory.

### Gate F — Scheduler / Polling / Retry Firewall

1. Future scheduler logic requires a **separate future charter**.
2. Future polling logic requires a **separate future charter**.
3. Future retry / backoff logic requires a **separate future charter**.
4. Scheduler / polling / retry must **never auto-enable S1 append**.
5. Scheduler / polling / retry must **never auto-enable trading / actionability**.
6. Scheduler / polling / retry must **never auto-enable recovery / restart**.
7. Scheduler / polling / retry must **never auto-enable capacity**.
8. **Retry storms must fail closed.**
9. **No agent / model / background process may promote scheduler events into authority.**

### Gate G — Run-Completion and Audit-Window Boundary

1. The 24h raw-only run completion is **evidence only**.
2. Run completion **does not prove** audit clean.
3. Run completion **does not authorize** read-only audit implementation unless **separately
   commanded**.
4. Read-only audit clean **does not authorize** S1 append.
5. Audit window selection must be **explicit, provenance-bound, and non-post-hoc**.
6. **Missing / ambiguous audit-window timestamps fail closed.**

### Gate H — Forbidden Paths

The following automatic transitions are **explicitly forbidden**:

- `elapsed time ⇒ authorization`
- `24h complete ⇒ audit clean`
- `audit clean ⇒ S1 append`
- `scheduler tick ⇒ runtime`
- `cron event ⇒ production stream`
- `market session ⇒ trade`
- `timeout ⇒ restart`
- `retry schedule ⇒ recovery`
- `polling loop ⇒ external authority`
- `timestamp match ⇒ semantic validity`
- `wall-clock event ⇒ capacity`
- `model-generated schedule ⇒ execution`

Each requires, instead, a separate explicit operator command satisfying the Operator Authorization
boundary.

### Gate I — Output Boundary

1. This charter may only produce **documentation**.
2. **No** scheduler / timer / cron / systemd config read.
3. **No** scheduler / timer / cron / systemd config write.
4. **No** polling implementation.
5. **No** retry / backoff implementation.
6. **No** S1 append.
7. **No** production stream.
8. **No** signal / trade / order / routing / capital output.
9. **Capacity remains 0.**

### Gate J — Next Gate / No Auto-Activation

1. Future time / scheduler **TDD** requires a separate explicit operator command.
2. Future time / scheduler **implementation** requires a separate explicit operator command.
3. Future **polling / retry / backoff implementation** requires a separate explicit charter and
   command.
4. Ratifying this charter **does not** make implementation eligible by itself.
5. **Clean state does not auto-advance.**
6. **Capacity remains 0.**

---

## Section 4 — Time / Scheduler Class Authority Ledger (template, to be completed later)

No timestamp or scheduler event is asserted as authority now. A future time/scheduler charter /
implementation must map each class into this structure (documentation-only here):

| Class | Role | Provenance-bound | Authority | Status |
|-------|------|------------------|-----------|--------|
| wall_clock_timestamp | forensic | PENDING | none | non-authoritative |
| monotonic_clock | forensic | PENDING | none | non-authoritative |
| exchange_timestamp | source-event | PENDING | none | evidence only |
| provider_timestamp | source-event | PENDING | none | evidence only |
| ledger_commit_timestamp | forensic | PENDING | none | non-authoritative |
| elapsed_duration | forensic | PENDING | none | non-authoritative |
| cron_systemd_timer | n/a | PENDING | none | BLOCKED |
| polling_loop | n/a | PENDING | none | BLOCKED |
| retry_backoff_schedule | n/a | PENDING | none | BLOCKED |
| market_session_clock | n/a | PENDING | none | BLOCKED |
| timeout_deadline | forensic | PENDING | none | non-authoritative |
| run_completion_timestamp | evidence | PENDING | none | evidence only |
| audit_window_timestamp | evidence | PENDING | none | explicit/non-post-hoc only |

Every class is **non-authoritative**; source-event timestamps are evidence only and are never
substituted by retrieval / wall-clock timestamps.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this time / scheduler / clock authority boundary charter.
2. The full Gate B precondition chain, each step separately ratified.
3. Only after an explicit operator command: a separate time/scheduler TDD charter, then a
   RED→GREEN implementation.
4. Polling / retry / backoff implementation each remain behind their **own** separate charters and
   operator commands.

## Post-state

- Time / Scheduler / Clock Authority Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Halt / restart / rollback / recovery: **BLOCKED**.
- Secrets / credentials / wallet / signing / capital authority: **BLOCKED**.
- External dependency / third-party service authority: **BLOCKED**.
- Model / agent authority: **BLOCKED**.
- Configuration / parameter / feature-flag authority: **BLOCKED**.
- Time / scheduler / clock authority: **BLOCKED**.
- Capacity: **0**.
