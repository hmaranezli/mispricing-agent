# Post-Phase 6.2 Human Approval Ledger / Operator Decision Mechanism TDD Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, TDD / planning only, future-only.** It defines the future **test-driven**
  requirements for an isolated Human Approval Ledger / Operator Decision Mechanism. It **implements
  nothing**, **writes no test**, **runs no test**, **creates no ledger / DB**, **generates no key /
  signature**, and **authorizes nothing**.
- It edits **no** runtime / code / test / schema / config / lock / generated / tracking file.
- It performs **no** approval ledger creation, **no** DB creation, **no** cryptographic key
  generation, **no** signature generation, **no** GPG / YubiKey / offline-salt implementation, **no**
  private key handling, **no** secret / env / credential / wallet / signing inspection.
- It performs **no** S1 access, **no** S1 DB creation, **no** S1 append, **no** production stream
  creation, **no** semantic promotion, **no** ledger mutation, **no** raw body / payload reads,
  **no** report / artifact / export generation.
- It performs **no** paper / dry-run / live / canary action, **no** monitoring / notification call,
  **no** network / API / order-routing call, **no** tmux / run interaction, **no** capacity /
  actionability / trading inference.
- **Core doctrine:** writing the TDD plan is **not** the implementation; passing future tests is
  **not** S1 activation; the **private key must never touch the VPS** (public-key verification only);
  and **staleness fails closed**, never auto-expedites.
- **Human Approval Ledger / Operator Decision Mechanism Boundary Charter: RATIFIED.**
- **S1 Stream Authorization Evidence Matrix Construction Boundary Charter: RATIFIED.**
- **S1 Stream Authorization Eligibility Review Charter: RATIFIED.**
- **Post-Run Read-Only Continuous Ledger Audit: PASS / COMPLETE.**
- **Frozen 24h raw ledger: AUDITED CLEAN.**
- **S1 authorization gate: ELIGIBLE FOR SEPARATE REVIEW.**
- **Human approval ledger / operator decision mechanism implementation: BLOCKED / UNSTARTED.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `2d52ed27defa5c4088ab8105adeb6c999c20aa2b`.
- Parent chain:
  - `2d52ed27defa5c4088ab8105adeb6c999c20aa2b` = **RATIFIED** Human Approval Ledger / Operator
    Decision Mechanism Boundary Charter.
  - `1a18097b9b94e95d00c19f07612b6324f5bb6dc8` = **RATIFIED** S1 Stream Authorization Evidence
    Matrix Construction Boundary Charter.
  - `764d4465ce296842afca578bd6de52f25a417cd9` = **RATIFIED** S1 Stream Authorization Eligibility
    Review Charter.
- This charter defines the **TDD / implementation-planning boundary** for the human approval ledger
  mechanism, responding to two Gemini blockers raised at ratification of `2d52ed2`:
  - **Operational friction / data staleness:** anti-fatigue controls may delay approval long enough
    that the frozen 24h ledger becomes stale before S1 matrix construction.
  - **Air-gapped signature bridge:** the private key must never touch the internet-facing VPS; the
    mechanism for physically injecting operator signatures remains undefined.
- It does not supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- This charter draws the **TDD-is-not-implementation line**: it specifies the **future RED tests,
  isolation architecture, air-gapped signature bridge, and staleness controls** that an approval
  mechanism must satisfy — and proves that planning these tests builds nothing and authorizes
  nothing.
- It exists to make **"TDD charter exists ⇒ mechanism exists", "tests pass ⇒ S1 append", and
  "delayed approval ⇒ expedite stale data" drift structurally impossible**. It encodes both Gemini
  blockers as hard boundaries: an **air-gapped signature bridge** (Gate D, public-key verify only)
  and a **stale-data fail-closed** rule (Gate E, never auto-expedite).

---

## Section 3 — Boundary Gates

### Gate A — Future-Only TDD Boundary

1. This charter defines future **TDD requirements** for an isolated Human Approval Ledger / Operator
   Decision Mechanism.
2. It **does not implement** the mechanism.
3. It **does not select** final cryptographic tooling.
4. It **does not authorize** S1 matrix construction or S1 append.

### Gate B — Current Evidence Basis

- **Human Approval Ledger / Operator Decision Mechanism Boundary Charter: RATIFIED at
  `2d52ed27defa5c4088ab8105adeb6c999c20aa2b`.**
- **S1 Stream Authorization Evidence Matrix Construction Boundary Charter: RATIFIED.**
- **S1 Stream Authorization Eligibility Review Charter: RATIFIED.**
- **Post-Run Read-Only Continuous Ledger Audit: PASS / COMPLETE.**
- **Frozen 24h raw ledger: AUDITED CLEAN.**
- **S1 authorization gate: ELIGIBLE FOR SEPARATE REVIEW.**
- **S1 evidence matrix construction: BLOCKED / UNSTARTED.**
- **Human approval ledger / operator decision mechanism implementation: BLOCKED / UNSTARTED.**
- **S1 append: DENIED / NOT PERFORMED.**
- **Production S1 stream: BLOCKED.**
- **Capacity: 0.**

### Gate C — Isolation Architecture Requirements

A future mechanism must satisfy all of:

- approval ledger **isolated from the S1 DB**;
- **no S1 import / dependency**;
- **no production stream dependency**;
- **no trading / capacity dependency**;
- **append-only approval records** in the future mechanism;
- **immutable record semantics**;
- **read-only verification path**;
- **offline signature verification allowed, private key handling forbidden**;
- **public-key-only verification on the VPS**;
- **no private key material on the VPS**;
- **no wallet / signing / capital overlap**;
- **no auto-execution from an approval record**.

### Gate D — Air-Gapped Signature Bridge Requirements (Gemini warning)

A future mechanism must satisfy all of:

- the **private key must never touch the VPS**;
- the future system may verify signatures **using the public key only**;
- the operator **signs the exact command offline / air-gapped**;
- the **signed approval package is transferred as inert text / data**;
- **transfer / import is not execution**;
- **signature verification is not S1 append**;
- the approval package must **bind exact command, target, scope, timestamp, nonce / challenge,
  expiry**;
- **anti-replay** is required;
- **signature freshness** is required;
- a **revocation / void path** is required.

Possible future mechanisms are mentioned **only as examples, never as decisions**: detached GPG
signature, hardware-key signed challenge, QR / manual transfer, append-only signed local ledger.
This charter selects **none**.

### Gate E — Stale-Data / Operational-Friction Boundary (Gemini warning)

Anti-fatigue controls may delay action, and a frozen ledger may become stale; **staleness must
fail-closed, never auto-expedite**. A future mechanism must define at least the following staleness
controls (at least twelve):

- **max review window**;
- **explicit `stale_after` timestamp**;
- **stale ledger blocks S1 matrix construction**;
- **stale ledger blocks S1 append**;
- **re-audit or re-run requirement** when stale;
- **no bypass due to urgency**;
- **no auto-extension**;
- **no silent refresh**;
- **no mixing old audit with new data**;
- **no partial override**;
- **stale reason must be recorded**;
- **human fatigue cannot override staleness**;
- **reviewer delay cannot become authority**;
- **capacity remains 0 on stale**.

The default in every stale or ambiguous state is the **safe / blocked** outcome.

### Gate F — Future RED Tests / Acceptance Criteria

The following future tests must exist and fail first (RED) before any implementation — **none is
implemented now** (at least eighteen):

1. **rejects missing signature**;
2. **rejects unverifiable signature**;
3. **rejects private key path on VPS**;
4. **rejects command text mismatch**;
5. **rejects target commit mismatch**;
6. **rejects ledger identity mismatch**;
7. **rejects stale approval**;
8. **rejects replayed nonce**;
9. **rejects expired approval**;
10. **rejects approve-all language**;
11. **rejects matrix rubber-stamp pattern**;
12. **rejects S1 append implication**;
13. **rejects capacity implication**;
14. **rejects paper / live implication**;
15. **rejects model verdict as approval**;
16. **verifies append-only approval record shape**;
17. **verifies immutable hash chain or equivalent**;
18. **verifies public-key-only verification**;
19. **verifies no S1 dependency / import**;
20. **verifies no network requirement**.

Each test is **future / unimplemented**; this charter writes and runs **none** of them.

### Gate G — Fail-Closed Taxonomy

A future mechanism must **fail closed** for at least the following conditions (at least twenty-two):

- **tooling not selected**;
- **key material ambiguity**;
- **private key touches VPS**;
- **public key missing**;
- **signature missing**;
- **signature unverifiable**;
- **nonce missing**;
- **nonce replayed**;
- **timestamp missing**;
- **approval stale**;
- **command mismatch**;
- **target mismatch**;
- **scope mismatch**;
- **immutable storage missing**;
- **revocation path missing**;
- **S1 dependency introduced**;
- **network dependency introduced**;
- **report / export dependency introduced**;
- **wallet / signing / capital dependency introduced**;
- **capacity / trading implication**;
- **paper / live implication**;
- **rubber-stamp pattern**;
- **operator fatigue unchecked**;
- **stale ledger mixed with fresh evidence**.

The default in every degraded or ambiguous state is the **safe / blocked** outcome.

### Gate H — Non-Authority Rules

Future systems must prove (at least fourteen rules):

- **TDD charter ≠ implementation.**
- **approval ledger implementation ≠ S1 append.**
- **signature verification ≠ execution.**
- **public key presence ≠ authority.**
- **signed package import ≠ execution.**
- **stale data cannot be expedited.**
- **re-audit requirement ≠ failure.**
- **matrix construction remains blocked.**
- **S1 append remains denied.**
- **capacity remains 0.**
- **paper / live remain blocked.**
- **human approval cannot self-trigger.**
- **model / Gemini / Claude cannot approve.**
- **passing future tests cannot auto-activate S1.**

### Gate I — Documentation-Only Output Boundary

1. This is **one markdown file only**.
2. **No** generated artifacts.
3. **No** tracking / memory edits.
4. **No** tests run.
5. **No** ledger access; **no** S1 access; **no** key / signature generation; **no** signal / trade
   / order / routing / capital output. **Capacity remains 0.**

### Gate J — No-Auto-Activation Post-State

- Human Approval Ledger / Operator Decision Mechanism TDD Charter: **BUILT / RATIFIABLE /
  UNRATIFIED**.
- Human Approval Ledger / Operator Decision Mechanism Boundary Charter: **RATIFIED**.
- S1 Stream Authorization Evidence Matrix Construction Boundary Charter: **RATIFIED**.
- S1 Stream Authorization Eligibility Review Charter: **RATIFIED**.
- Post-Run Read-Only Continuous Ledger Audit: **PASS / COMPLETE**.
- Frozen 24h raw ledger: **AUDITED CLEAN**.
- S1 authorization gate: **ELIGIBLE FOR SEPARATE REVIEW**.
- Human approval ledger / operator decision mechanism implementation: **BLOCKED / UNSTARTED**.
- S1 evidence matrix construction: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper mode dry-run readiness: **BLOCKED / UNSTARTED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Halt / restart / rollback / recovery: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.

---

## Section 4 — TDD Requirement Ledger (template, to be completed later)

No test is written or run now. A future TDD step must satisfy each requirement (documentation-only
here; every entry is a future requirement, never an authorization):

| Requirement group | Guarantee | Implemented? | Status |
|-------------------|-----------|--------------|--------|
| isolation_architecture | ledger isolated from S1, no import | NO | BLOCKED |
| append_only_immutable | append-only + immutable records | NO | BLOCKED |
| public_key_only_verify | VPS verifies with public key only | NO | BLOCKED |
| no_private_key_on_vps | private key never on VPS | NO | BLOCKED |
| air_gapped_bridge | offline sign, inert transfer | NO | BLOCKED |
| anti_replay_freshness | nonce + freshness + expiry | NO | BLOCKED |
| revocation_void | revocation / void path | NO | BLOCKED |
| staleness_fail_closed | stale blocks, never expedites | NO | BLOCKED |
| anti_rubber_stamp | fatigue controls enforced | NO | BLOCKED |
| red_tests_present | ≥18 RED tests fail first | NO | BLOCKED |
| no_s1_dependency | no S1 import / dependency | NO | BLOCKED |
| no_network_requirement | verification needs no network | NO | BLOCKED |

Every requirement is **unimplemented and BLOCKED**; passing any future test cannot auto-activate S1,
matrix construction, paper, live, or capacity.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this human approval ledger / operator decision mechanism TDD charter.
2. Only under a **separate explicit operator command**: a future mechanism-design decision that
   selects cryptographic tooling (none chosen here), then a RED→GREEN implementation in an isolated
   subsystem.
3. A clean audit, an eligibility review, a constructed matrix, a recorded approval, and passing
   tests do **not** auto-enable S1, paper, live, or capacity.

## Post-state

- Human Approval Ledger / Operator Decision Mechanism TDD Charter: **BUILT / RATIFIABLE /
  UNRATIFIED**.
- Human Approval Ledger / Operator Decision Mechanism Boundary Charter: **RATIFIED**.
- S1 Stream Authorization Evidence Matrix Construction Boundary Charter: **RATIFIED**.
- S1 Stream Authorization Eligibility Review Charter: **RATIFIED**.
- Post-Run Read-Only Continuous Ledger Audit: **PASS / COMPLETE**.
- Frozen 24h raw ledger: **AUDITED CLEAN**.
- S1 authorization gate: **ELIGIBLE FOR SEPARATE REVIEW**.
- Human approval ledger / operator decision mechanism implementation: **BLOCKED / UNSTARTED**.
- S1 evidence matrix construction: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper mode dry-run readiness: **BLOCKED / UNSTARTED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Halt / restart / rollback / recovery: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.
