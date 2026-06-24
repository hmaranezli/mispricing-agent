# Post-Phase 6.2 Human Approval Ledger / Operator Decision Mechanism Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the **requirements** for a future human approval ledger /
  operator decision mechanism. It **implements nothing**, **creates no ledger**, **generates no
  key**, **signs nothing**, and **authorizes nothing**.
- It edits **no** runtime / code / test / schema / config / lock / generated / tracking file.
- It performs **no** approval ledger creation, **no** cryptographic key generation, **no** GPG /
  YubiKey / offline salt implementation, **no** secret / env / credential / wallet / signing
  inspection.
- It performs **no** S1 access, **no** S1 DB creation, **no** S1 append, **no** production stream
  creation, **no** semantic promotion, **no** ledger mutation, **no** raw body / payload reads,
  **no** report / artifact / export generation.
- It performs **no** paper / dry-run / live / canary action, **no** monitoring / notification call,
  **no** network / API / order-routing call, **no** tmux / run interaction, **no** capacity /
  actionability / trading inference.
- **Core doctrine:** an approval mechanism must be **externally verifiable, command-bound,
  target-bound, non-replayable, immutable, and revocable** before any human command can authorize
  anything; matrix scale must not produce **rubber-stamping**; and a charter describing the
  mechanism is **not** the mechanism.
- **S1 Stream Authorization Evidence Matrix Construction Boundary Charter: RATIFIED.**
- **S1 Stream Authorization Eligibility Review Charter: RATIFIED.**
- **Post-Run Read-Only Continuous Ledger Audit: PASS / COMPLETE.**
- **Frozen 24h raw ledger: AUDITED CLEAN.**
- **S1 authorization gate: ELIGIBLE FOR SEPARATE REVIEW.**
- **Human approval ledger / operator decision mechanism: BLOCKED / UNSTARTED.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `1a18097b9b94e95d00c19f07612b6324f5bb6dc8`.
- Parent chain:
  - `1a18097b9b94e95d00c19f07612b6324f5bb6dc8` = **RATIFIED** S1 Stream Authorization Evidence
    Matrix Construction Boundary Charter.
  - `764d4465ce296842afca578bd6de52f25a417cd9` = **RATIFIED** S1 Stream Authorization Eligibility
    Review Charter.
  - `abd6ce6792948189238697108bd092ffcd09e59c` = **RATIFIED** Operator Decision Log / Human Approval
    Ledger Boundary Charter.
- This charter defines the **human approval ledger / operator decision mechanism** boundary,
  responding to two Gemini blockers raised at ratification of `1a18097`:
  - **Matrix combinatorics risk:** 18 columns × 18 row classes may cause operator fatigue and
    rubber-stamping.
  - **`HUMAN_APPROVAL_SPOOFING_BLOCKER` remains conceptual:** the cryptographic / immutable operator
    approval mechanism is not yet mathematically defined.
- It does not supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- This charter draws the **approval-mechanism non-creation line**: it specifies **what a trustworthy
  operator approval mechanism must guarantee** (identity, command binding, anti-replay, immutability,
  revocation, independent auditability, anti-rubber-stamp controls) — and proves that **writing
  these requirements down is not the mechanism** and authorizes nothing.
- It exists to make **"charter exists ⇒ approval mechanism exists", "signed approval ⇒ S1 append",
  and "fast bulk approval ⇒ valid governance" drift structurally impossible**. Until a separately
  ratified, externally verifiable mechanism exists and a future command of the Section H shape is
  issued, **no S1 action of any kind is authorized**.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only Approval Boundary

1. This charter defines **requirements** for a future human approval ledger / operator decision
   mechanism.
2. It **does not create** the mechanism.
3. It **does not authorize** S1 matrix construction, S1 append, paper, live, or capacity.

### Gate B — Current Evidence Basis

- **S1 Stream Authorization Evidence Matrix Construction Boundary Charter: RATIFIED at
  `1a18097b9b94e95d00c19f07612b6324f5bb6dc8`.**
- **S1 Stream Authorization Eligibility Review Charter: RATIFIED at
  `764d4465ce296842afca578bd6de52f25a417cd9`.**
- **Post-Run Read-Only Continuous Ledger Audit: PASS / COMPLETE.**
- **Frozen 24h raw ledger: AUDITED CLEAN.**
- **S1 authorization gate: ELIGIBLE FOR SEPARATE REVIEW.**
- **S1 evidence matrix construction: BLOCKED / UNSTARTED.**
- **Human approval ledger / operator decision mechanism: BLOCKED / UNSTARTED.**
- **S1 append: DENIED / NOT PERFORMED.**
- **Production S1 stream: BLOCKED.**
- **Capacity: 0.**

### Gate C — Approval Record Required Fields

A future approval record must define at least eighteen required fields:

- `approval_record_id`
- `operator_identity_class`
- `operator_identity_reference`
- `exact_command_text`
- `command_scope`
- `target_commit_sha`
- `target_ledger_identity`
- `target_artifact_identity`
- `target_s1_identity`
- `authorization_type`
- `allowed_actions`
- `forbidden_actions`
- `timestamp_utc`
- `nonce_or_challenge_reference`
- `signature_reference`
- `verification_method_reference`
- `immutable_storage_reference`
- `revocation_or_void_reference`
- `expiry_boundary`
- `reviewer_witness_reference`
- `fatigue_check_reference`

Any missing required field ⇒ the approval record **fails closed** and is **invalid**.

### Gate D — Cryptographic / Anti-Spoofing Requirements

A future mechanism must satisfy all of the following (requirements only — **no** tooling is chosen
or implemented here):

- operator identity must be **externally verifiable**;
- approval must **bind exact command text**;
- approval must **bind exact target**;
- approval must **bind exact scope**;
- approval must be **non-replayable** (nonce / challenge bound);
- approval must be **timestamped**;
- approval must be **immutable after recording**;
- approval must be **verifiable without exposing secrets**;
- approval must **support a revocation / void record**;
- approval must be **independently auditable**;
- **model / agent / Gemini / Claude output cannot sign or approve**;
- **screenshots / chat text alone are insufficient** unless bound into the approved mechanism.

Possible future mechanisms are mentioned **only as examples, never as decisions**: GPG signatures,
hardware security keys, YubiKey, offline challenge / response, append-only signed ledger. Selecting
any of these requires a **separate** ratified decision; this charter selects **none**.

### Gate E — Rubber-Stamp / Operator-Fatigue Firewall

Responding to the Gemini concern that an **18 × 18 matrix** scale may cause rubber-stamping, a future
approval mechanism must include at least the following fatigue controls (at least twelve):

- **batch-size limit**;
- **mandatory review pauses**;
- **cell sampling strategy**;
- **independent reviewer option**;
- **high-risk-cell escalation**;
- **explicit "no blanket approval" rule**;
- **reason required for each approved class**;
- **random spot-check requirement**;
- **mismatch acknowledgement**;
- **fatigue self-attestation**;
- **auto-deny on rushed approval**;
- **no approve-all command**;
- **no default-positive state**;
- **blocked-on-ambiguity rule**.

The default in every fatigue-ambiguous state is the **safe / blocked** outcome.

### Gate F — Fail-Closed Taxonomy

A future mechanism must **fail closed** for at least the following conditions (at least twenty):

- **missing exact command**;
- **missing operator identity**;
- **missing signature**;
- **unverifiable signature**;
- **replayed approval**;
- **stale approval**;
- **command text mismatch**;
- **target mismatch**;
- **scope ambiguity**;
- **target S1 ambiguity**;
- **matrix cell ambiguity**;
- **rubber-stamp pattern detected**;
- **approve-all language**;
- **missing immutable storage**;
- **missing revocation path**;
- **secret exposure requirement**;
- **model verdict treated as approval**;
- **screenshot-only approval**;
- **chat-only approval**;
- **missing fatigue check**;
- **capacity / trading implication**;
- **S1 append implied by approval record**.

The default in every degraded or ambiguous state is the **safe / blocked** outcome.

### Gate G — Non-Authority Rules

Future systems must prove (at least fourteen rules):

- **approval ledger charter ≠ approval ledger.**
- **approval record ≠ execution.**
- **signed approval ≠ S1 append** unless a future command explicitly authorizes append.
- **matrix ratification ≠ approval.**
- **PASS audit ≠ approval.**
- **ELIGIBLE ≠ approval.**
- **Gemini / Claude verdict ≠ approval.**
- **screenshot ≠ approval.**
- **chat ≠ approval.**
- **human enthusiasm ≠ approval.**
- **capacity remains 0.**
- **paper / live remain blocked.**
- **S1 target mention ≠ S1 creation.**
- **approval mechanism cannot self-trigger.**

### Gate H — Required Future Command Shape (descriptive only)

A future command, if ever issued, must include (this section grants **no** current authority):

- the **exact approved mechanism version**;
- the **exact approval record id**;
- the **exact operator identity**;
- the **exact signed command text**;
- the **exact target commit**;
- the **exact target ledger**;
- the **exact target matrix**;
- the **exact target S1 path / schema, if any**;
- the **exact allowed writes, if any**;
- the **exact forbidden actions**;
- the **exact abort conditions**.

Until such a command exists, is bound to a separately ratified mechanism, and is separately ratified
itself, **no** S1 action of any kind is authorized.

### Gate I — Documentation-Only Output Boundary

1. This is **one markdown file only**.
2. **No** generated artifacts.
3. **No** tracking / memory edits.
4. **No** audit re-run.
5. **No** ledger access; **no** S1 access; **no** key / signature generation; **no** signal / trade
   / order / routing / capital output. **Capacity remains 0.**

### Gate J — No-Auto-Activation Post-State

- Human Approval Ledger / Operator Decision Mechanism Boundary Charter: **BUILT / RATIFIABLE /
  UNRATIFIED**.
- S1 Stream Authorization Evidence Matrix Construction Boundary Charter: **RATIFIED**.
- S1 Stream Authorization Eligibility Review Charter: **RATIFIED**.
- Post-Run Read-Only Continuous Ledger Audit: **PASS / COMPLETE**.
- Frozen 24h raw ledger: **AUDITED CLEAN**.
- S1 authorization gate: **ELIGIBLE FOR SEPARATE REVIEW**.
- S1 evidence matrix construction: **BLOCKED / UNSTARTED**.
- Human approval ledger / operator decision mechanism: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper mode dry-run readiness: **BLOCKED / UNSTARTED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Halt / restart / rollback / recovery: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.

---

## Section 4 — Approval Mechanism Requirement Ledger (template, to be completed later)

No approval mechanism exists now. A future mechanism charter / implementation must satisfy each
requirement (documentation-only here; every entry is a requirement, never an authorization):

| Requirement | Guarantee | Implemented? | Status |
|-------------|-----------|--------------|--------|
| operator_identity_external_verify | externally verifiable identity | NO | BLOCKED |
| command_text_binding | binds exact command text | NO | BLOCKED |
| target_binding | binds exact target | NO | BLOCKED |
| scope_binding | binds exact scope | NO | BLOCKED |
| anti_replay | nonce / challenge non-replayable | NO | BLOCKED |
| timestamping | UTC forensic timestamp | NO | BLOCKED |
| immutability | immutable after recording | NO | BLOCKED |
| secretless_verification | verify without exposing secrets | NO | BLOCKED |
| revocation_void | revocation / void record | NO | BLOCKED |
| independent_audit | independently auditable | NO | BLOCKED |
| no_model_signing | model/agent cannot sign/approve | NO | BLOCKED |
| screenshot_chat_insufficient | screenshot/chat alone insufficient | NO | BLOCKED |
| fatigue_controls | anti-rubber-stamp controls (Gate E) | NO | BLOCKED |
| future_command_shape | Section H command shape | NO | BLOCKED |

Every requirement is **unimplemented and BLOCKED**; no approval record can be valid, and no S1 action
can be authorized, until a separately ratified mechanism satisfies all of them.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this human approval ledger / operator decision mechanism boundary charter.
2. Only under a **separate explicit decision**: a future mechanism-design charter that selects and
   specifies the cryptographic / immutable approach (none is chosen here).
3. A clean audit, an eligibility review, a constructed matrix, and a recorded approval do **not**
   auto-enable S1, paper, live, or capacity.

## Post-state

- Human Approval Ledger / Operator Decision Mechanism Boundary Charter: **BUILT / RATIFIABLE /
  UNRATIFIED**.
- S1 Stream Authorization Evidence Matrix Construction Boundary Charter: **RATIFIED**.
- S1 Stream Authorization Eligibility Review Charter: **RATIFIED**.
- Post-Run Read-Only Continuous Ledger Audit: **PASS / COMPLETE**.
- Frozen 24h raw ledger: **AUDITED CLEAN**.
- S1 authorization gate: **ELIGIBLE FOR SEPARATE REVIEW**.
- S1 evidence matrix construction: **BLOCKED / UNSTARTED**.
- Human approval ledger / operator decision mechanism: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper mode dry-run readiness: **BLOCKED / UNSTARTED**.
- Calibration / trading / actionability: **BLOCKED**.
- Paper / canary / live: **BLOCKED**.
- Halt / restart / rollback / recovery: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.
