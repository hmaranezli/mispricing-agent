# Post-Phase 6.2 Human Approval Ledger Append Rate-Limit / Abuse-Resistance Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the abuse-resistance requirements for future approval-ledger
  appends. It **implements nothing**, **builds no rate limiter**, **mutates no DB**, and **authorizes
  nothing**.
- It edits **no** runtime / code / test / schema / config / lock / generated / tracking file.
- It runs **no** test, performs **no** approval ledger DB mutation, **no** S1 access / DB creation /
  append, **no** production stream, **no** S1 evidence matrix construction.
- It reads **no** raw ledger / body / payload; inspects **no** private key / signing / wallet /
  credential / secret / env.
- It performs **no** network / API / order-routing / monitoring / tmux / runtime-run interaction,
  **no** paper / dry-run / live / canary, **no** trading / actionability / capacity inference.
- **Core doctrine:** append-only immutability protects audit integrity, but an **unbounded** append
  path is a disk / inode DoS surface; the remedy is **passive, fail-closed rate-limiting and
  preflight** — never deletion, truncation, compaction, or any escalation. A rate-limit pass is
  **not** an approval.
- **Human Approval Ledger DB infrastructure slice: RATIFIED (isolated passive append-only ledger
  only).**
- **Human approval ledger DB: CREATED ONLY AS ISOLATED PASSIVE APPROVAL LEDGER DB.**
- **S1 evidence matrix construction: BLOCKED / UNSTARTED.** **S1 append: DENIED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `4d803583ee25f6cf88281b42890539082151dc84`.
- Parent chain:
  - `4d803583ee25f6cf88281b42890539082151dc84` = **RATIFIED** Human Approval Ledger DB slice
    (`approval/approval_ledger_db.py` + tests).
  - `48bd548a45f52a1bd20ce5a9ded444ad208bca32` = **RATIFIED** Day-Zero Trust Anchor / Production
    Verifier Wiring slice.
  - `0480e2d9121b507ddbf3ea1cba80f2bb2a6a37c8` = **RATIFIED** Cryptographic Wiring & Trust Anchor
    Boundary Charter.
- This charter defines the **append rate-limit / abuse-resistance** boundary, blocking the remaining
  Gemini concern: an append-only DB can be abused by spam, typo loops, retry storms, or a malicious
  `while(true)` append flood causing **disk / inode exhaustion**.
- It does not supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- This charter draws the **abuse-resistance non-authority line**: bounding the append rate protects
  the ledger from exhaustion, but a successful, rate-limited, disk-healthy append is still **passive
  evidence at most** — never an approval, never S1 authorization, never capacity.
- It exists to make **"append succeeded ⇒ approved", "rate-limit pass ⇒ S1 readiness", and "abuse
  mitigation ⇒ evidence deletion" drift structurally impossible**. Abuse resistance must **fail
  closed** and must **never** mutate, delete, truncate, or compact recorded evidence.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only Boundary

1. This charter creates **no** implementation, **no** DB mutation, **no** rate limiter, **no** S1
   matrix, **no** S1 append, **no** capacity.
2. It **only** defines future abuse-resistance requirements for approval-ledger appends.
3. It **authorizes no** runtime, S1 access, trading, paper / canary / live, recovery, routing, or
   capacity.

### Gate B — Current Evidence Basis

- Base commit: `4d803583ee25f6cf88281b42890539082151dc84`.
- The Human Approval Ledger DB infrastructure slice is **RATIFIED** only as an **isolated passive
  append-only ledger** (no update/delete API, UPDATE/DELETE triggers, constant-False authority
  flags, fail-closed validation).
- **Append-only immutability is good for audit integrity but creates disk / inode DoS risk if append
  attempts are unbounded.** No rate-limit, quota, or disk/inode preflight exists yet.

### Gate C — Abuse Model

Future systems must explicitly account for at least:

- **typo loops**;
- **retry storms**;
- **malicious append flood** (`while(true)`);
- **malformed package spam**;
- **repeated invalid verifier / trust-anchor attempts**;
- **duplicate ceremony claims**;
- **disk exhaustion**;
- **inode exhaustion**;
- **operator fatigue from a noisy ledger**;
- **false sense of approval progress**.

### Gate D — Rate-Limit / Quota Boundary

Future requirements:

- a **deterministic append quota**;
- a **per-source or per-actor append window**;
- **duplicate suppression or duplicate classification**;
- **retry / backoff semantics**;
- **max invalid attempts per bounded window**;
- **no automatic escalation after rate-limit**;
- **rate-limit failure is passive fail-closed only**;
- **no deletion / redaction as a rate-limit response**.

### Gate E — Disk / Inode Safety Boundary

Future requirements:

- **explicit DB path only** (no implicit / live path);
- a **max DB size policy** (future requirement);
- a **free-space preflight** (future requirement);
- **fail closed before disk exhaustion**;
- **no automatic truncation**;
- **no automatic compaction that mutates evidence**;
- **no evidence deletion as recovery**.

### Gate F — Operator Ergonomics / Fatigue Boundary

Future requirements:

- **repeated invalid attempts must not become approval pressure**;
- **summaries may be future-only passive views**;
- **no batch approval**;
- **no rubber-stamp path**;
- **a noisy ledger does not authorize S1**;
- **rate-limit status is not approval status**.

### Gate G — Fail-Closed Conditions

The following must **fail closed** (at least twenty):

1. **append quota exceeded**;
2. **duplicate storm**;
3. **invalid package flood**;
4. **missing actor / source identity**;
5. **unknown append source**;
6. **DB size threshold reached**;
7. **inode / free-space preflight failed**;
8. **ambiguous retry state**;
9. **backoff bypass attempt**;
10. **rate-limit config missing**;
11. **rate-limit config ambiguous**;
12. **automatic deletion requested**;
13. **automatic compaction requested**;
14. **automatic truncation requested**;
15. **max-invalid-attempts window exceeded**;
16. **duplicate ceremony claim**;
17. **retry storm detected**;
18. **malformed-package spam detected**;
19. **S1 append attempted from rate-limit pass**;
20. **matrix construction attempted from rate-limit pass**;
21. **trading / capacity inference attempted from rate-limit pass**;
22. **paper / live inference attempted from rate-limit pass**.

The default in every degraded or ambiguous state is the **safe / blocked** outcome.

### Gate H — Non-Authority Rules

Future systems must prove (at least twelve rules):

- **rate-limit pass ≠ approval.**
- **append success ≠ S1 authorization.**
- **duplicate suppression ≠ deletion.**
- **backoff ≠ recovery.**
- **disk-health pass ≠ S1 readiness.**
- **Gemini / Claude / Codex output ≠ operator command.**
- **approval DB existence ≠ capacity.**
- **quota headroom ≠ trading authority.**
- **passive summary ≠ batch approval.**
- **noisy ledger ≠ approval pressure.**
- **rate-limit status ≠ approval status.**
- **abuse mitigation ≠ evidence mutation.**

### Gate I — Required Future Command Shape (descriptive only)

A future implementation command must explicitly define:

- the **exact base SHA**;
- the **exact target module / file**;
- the **deterministic rate-limit dimensions**;
- the **duplicate classification rule**;
- the **disk / inode preflight rule**;
- the **fail-closed tests**;
- an **explicit no-S1 / no-capacity boundary**;
- **targeted tests only**.

This section grants **no** current authority; absent such a command, no rate-limit / preflight
implementation is authorized.

### Gate J — No-Auto-Activation Post-State

- Human Approval Ledger Append Abuse-Resistance Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- Human Approval Ledger DB infrastructure slice: **RATIFIED**.
- Human approval ledger DB: **CREATED ONLY AS ISOLATED PASSIVE APPROVAL LEDGER DB**.
- S1 evidence matrix construction: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper / canary / live / trading / actionability: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.

---

## Section 4 — Abuse-Resistance Requirement Ledger (template, to be completed later)

No rate-limit or preflight mechanism exists now. A future abuse-resistance charter / implementation
must satisfy each requirement (documentation-only here; every entry is a future requirement, never an
authorization):

| Requirement | Guarantee | Implemented? | Status |
|-------------|-----------|--------------|--------|
| deterministic_quota | bounded appends per window | NO | BLOCKED |
| per_actor_window | per-source/actor append window | NO | BLOCKED |
| duplicate_classification | suppress/classify duplicates (no delete) | NO | BLOCKED |
| retry_backoff | deterministic retry/backoff | NO | BLOCKED |
| max_invalid_window | bounded invalid attempts | NO | BLOCKED |
| no_auto_escalation | no escalation after rate-limit | NO | BLOCKED |
| passive_fail_closed | rate-limit fails closed, passive | NO | BLOCKED |
| no_delete_as_response | never delete/redact as response | NO | BLOCKED |
| explicit_db_path | explicit path only | YES (ledger slice) | RATIFIED (path) |
| max_db_size_policy | bounded DB size | NO | BLOCKED |
| free_space_preflight | preflight before append | NO | BLOCKED |
| no_truncation_compaction | no evidence-mutating recovery | NO | BLOCKED |

Every unimplemented requirement is **BLOCKED**; satisfying any of them does not auto-enable S1,
matrix, paper, live, or capacity.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this approval ledger append abuse-resistance boundary charter.
2. Only under a **separate explicit operator command of the Section I shape**: a future rate-limit /
   disk-preflight TDD slice (passive, fail-closed, no evidence mutation).
3. A rate-limit pass, a disk-health pass, and a successful append do **not** auto-enable S1, matrix
   construction, paper, live, or capacity.

## Post-state

- Human Approval Ledger Append Abuse-Resistance Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- Human Approval Ledger DB infrastructure slice: **RATIFIED**.
- Day-Zero Trust Anchor Provisioning & Production Crypto Verifier Wiring slice: **RATIFIED**.
- Human Approval Package Verification slice: **RATIFIED**.
- Cryptographic Wiring & Trust Anchor Boundary Charter: **RATIFIED**.
- Human approval ledger DB: **CREATED ONLY AS ISOLATED PASSIVE APPROVAL LEDGER DB**.
- S1 evidence matrix construction: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper / canary / live / trading / actionability: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.
