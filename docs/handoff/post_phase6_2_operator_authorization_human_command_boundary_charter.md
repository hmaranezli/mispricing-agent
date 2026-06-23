# Post-Phase 6.2 Operator Authorization / Human Command Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines what a future explicit human / operator authorization must
  mean, and makes clear that **no** automated result or prior charter can substitute for one. It
  **implements nothing** and **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** implementation, S1 append, production S1 stream, calibration / trading /
  actionability, paper / canary / live, routing, orders, fills, cancels, sizing, allocation,
  capital deployment, or capacity.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Paper / Canary / Live Separation & Activation Firewall Charter: RATIFIED at `c1f78f9`.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.** **Paper / canary / live: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `c1f78f91b0a25295c0093fbc3d3a208eca4a1fdc`.
- Parent chain:
  - `c1f78f91b0a25295c0093fbc3d3a208eca4a1fdc` = **RATIFIED** Paper / Canary / Live Separation &
    Activation Firewall Boundary Charter.
  - `267e6e05b525f64ccbed442d809f5af8a20e6460` = **RATIFIED** Out-of-Sample / Replay Validation
    TDD Charter.
  - `e57e8cfe03a9ac9b3412215f7fd0c8bbce049024` = **RATIFIED** Out-of-Sample / Replay Validation
    Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter (the five-step transition law this charter operationalizes).
- This charter operationalizes the **explicit operator command** requirement that the No-Auto-
  Activation Law (Roadmap Section 4, step 5) depends on. It does not supersede, relax, or accelerate
  any prior gate.

## Section 2 — Constitutional Anchoring (binding floors)

The existing constitution (`CLAUDE.md`) already requires explicit human authorization for the
highest-risk transitions; this charter treats those as binding floors and only tightens them:

- Live (`DRY_RUN=False`) only by **explicit human written command** — never autonomously.
- Positions above `HUMAN_APPROVAL_USD` require **explicit human approval**.
- `config.py` guardrail constants are immutable without human action.
- No price/funding/probability/movement may be written from memory or estimate — every decision is
  data-backed and logged (the same evidentiary discipline applies to authorization records).

## Section 3 — Boundary Gates

### Gate A — Future-Only Operator Authorization Boundary

1. This charter defines **requirements only**.
2. It **does not authorize** tests, implementation, runtime, S1 append, trading, paper / canary /
   live, routing, or capacity.
3. It **only defines what future operator authorization must mean**.

### Gate B — Preconditions Before Any Future Operator-Authorized Work

Future operator-authorized work requires:

1. prior raw-only run **complete / stopped**;
2. Read-Only Continuous Ledger Audit **CLEAN**;
3. semantic projection validation **clean**;
4. calibration / analysis boundary **satisfied**;
5. out-of-sample / replay validation **satisfied**;
6. risk / capacity boundary **satisfied**;
7. paper / canary / live firewall **preserved**;
8. any **DIRTY** state **blocks** all future authorization;
9. an **explicit operator command naming the exact next scope**.

### Gate C — Explicit Command Identity Requirements

A future operator command must specify, unambiguously:

- the **exact target gate**;
- the **exact repository commit / base SHA**;
- the **exact allowed files or allowed subsystem**;
- the **exact forbidden actions**;
- the **exact capacity state**;
- the **exact S1 append state**;
- the **exact runtime / trading mode state**;
- **whether the command is docs-only, test-only, implementation-only, or read-only**.

A command missing any of these fields is **incomplete** and must be treated as **no authorization**.

### Gate D — Non-Substitutability Doctrine

The following must **never** substitute for an explicit operator command:

- a clean raw audit;
- a clean semantic validation;
- a good calibration result;
- a good replay validation;
- a profitable backtest;
- a model confidence score;
- prior charter language;
- passing tests;
- a successful paper result;
- a successful canary result;
- elapsed time or a scheduler event.

None of these, alone or in combination, constitutes authorization. They are **inputs**, never
**triggers**.

### Gate E — Ambiguity Fails Closed

Future systems must **fail closed** (treat as no authorization) if:

- command scope is **ambiguous**;
- commit / base SHA is **missing**;
- capacity state is **missing**;
- S1 append state is **missing**;
- runtime / trading mode is **missing**;
- allowed / forbidden actions **conflict**;
- operator identity / provenance is **missing**;
- the command references **stale state**;
- the command attempts **auto-promotion**.

The default in every ambiguous or incomplete state is **deny**.

### Gate F — Provenance and Auditability Requirements

Future operator authorization must be:

- **attributable** (to a named operator);
- **timestamped**;
- **bound to the exact commit / base SHA**;
- **bound to the exact prior gate state**;
- **reproducible from durable audit artifacts**;
- **not based on SQLite `rowid` / `append_sequence`** as a domain identity (identity derives from
  content / provenance hashes only);
- **stored only in a future separately authorized mechanism** (this charter creates no such store).

### Gate G — Human-in-the-Loop Firewall

A human / operator command is **required** for **every** one of these transitions — none may be
implicit:

- docs → tests;
- tests → implementation;
- implementation → runtime;
- any S1 append;
- any paper / canary / live mode;
- any nonzero capacity.

**No agent, model, scheduler, timer, or background process may self-authorize** any of the above.

### Gate H — Forbidden Authorization Paths

The following automatic transitions are **explicitly forbidden**:

- `audit ⇒ implementation`
- `validation ⇒ implementation`
- `tests ⇒ runtime`
- `calibration ⇒ signal`
- `signal ⇒ trading`
- `paper ⇒ canary`
- `canary ⇒ live`
- `model score ⇒ routing`
- `scheduler event ⇒ capacity`
- `elapsed time ⇒ S1 append`
- `any prior success ⇒ automatic next gate`

Each arrow requires, instead, a separate explicit operator command satisfying Gate C.

### Gate I — Output Boundary

1. This charter may only produce **documentation**.
2. **No** executable policy.
3. **No** authorization token.
4. **No** capacity token.
5. **No** S1 append token.
6. **No** signal / trading / routing / order / capital output.
7. **Capacity remains 0.**

### Gate J — Next Gate / No Auto-Activation

1. This charter **does not make any implementation eligible by itself**.
2. Any next charter, test, implementation, or runtime step requires a **separate explicit operator
   command**.
3. **Clean state does not auto-advance.**
4. **Ratification does not auto-advance.**
5. **Capacity remains 0.**

---

## Section 4 — Operator Command Field Checklist (template, to be completed later)

No command is asserted now. Every future operator command must satisfy this checklist before it is
treated as authorization:

| Field | Requirement | Present? |
|-------|-------------|----------|
| target_gate | exact named gate | PENDING |
| base_sha | exact commit/base SHA | PENDING |
| allowed_scope | exact files/subsystem | PENDING |
| forbidden_actions | exact list | PENDING |
| capacity_state | exact (must be 0 unless a capacity gate authorizes) | PENDING |
| s1_append_state | exact (DENIED unless an S1 charter authorizes) | PENDING |
| runtime_mode | exact (docs/test/impl/read-only) | PENDING |
| operator_identity | attributable + timestamped | PENDING |

Any PENDING / missing / conflicting field ⇒ **no authorization** (Gate E).

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this operator authorization / human command boundary charter.
2. The full Gate B precondition chain, each step separately ratified.
3. Every subsequent transition (docs → tests → implementation → runtime → S1 → paper → canary →
   live → capacity) requires its own explicit operator command satisfying Gate C, plus the
   five-step No-Auto-Activation Law.

## Post-state

- Operator Authorization / Human Command Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Capacity: **0**.
