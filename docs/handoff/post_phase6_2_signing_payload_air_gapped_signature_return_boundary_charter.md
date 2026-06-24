# Post-Phase 6.2 Signing Payload Construction & Air-Gapped Signature Return Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines boundaries for a future canonical **signing payload** and a
  passive **air-gapped signature return**. It **implements nothing**, **builds no payload**,
  **creates no signature**, **creates no verifier**, **renders no UI/CLI**, and **authorizes
  nothing**.
- It edits **no** runtime / code / test / schema / config / lock / generated / tracking file.
- It runs **no** test, performs **no** signing payload generation, **no** signature generation,
  **no** signature verification implementation; inspects **no** private key / wallet / credential /
  secret / env; implements **no** GPG / YubiKey / HSM / Tails / offline-salt.
- It performs **no** S1 DB creation / append / production stream, **no** S1 matrix mutation, **no**
  approval ledger DB mutation, **no** report / export / artifact generation, **no** raw ledger /
  body / payload reads.
- It performs **no** network / API / order-routing / monitoring / tmux / runtime-run interaction,
  **no** paper / dry-run / live / canary, **no** trading / actionability / capacity inference.
- **Core doctrine:** the operator must physically see the **same digest/summary bytes** a future
  signature will bind (anti-blind-signing); signed bytes must be **canonical, non-executable,
  digest-bound, and unable to trigger S1 append by themselves**; a returned signature is **passive
  evidence**, never an execution token, never authorization.
- **S1 Matrix Evaluation & Non-Executable Operator Review Package slice: RATIFIED (non-executable,
  digest-bound, passive review package).**
- **REVIEWABLE is not AUTHORIZED. No execution token exists.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `a376f1db4fae080de03931df2838b28f823e0e99`.
- Parent chain:
  - `a376f1db4fae080de03931df2838b28f823e0e99` = **RATIFIED** S1 Matrix Evaluation &
    Non-Executable Operator Review Package slice (`approval/s1_matrix_review.py` + tests).
  - `0a719a2312dccfa1cdc6f2345b19371862fda2f1` = **RATIFIED** S1 Matrix Evaluation & Non-Executable
    Operator Review Package Boundary Charter.
  - `b46a43991c9e1dc7d0f1a44ca612fec8becc5add` = **RATIFIED** Passive S1 Evidence Matrix
    Construction slice.
- This charter defines the **signing payload construction & air-gapped signature return** boundary,
  addressing three Gemini findings after the review-package slice:
  1. **Presentation-layer fidelity / blind-signing risk** — the operator must physically see the
     same digest/summary bytes that future signing will bind.
  2. **Signing payload bridge** — future signed bytes must be explicitly canonical, non-executable,
     digest-bound, and unable to trigger S1 append by themselves.
  3. **Signature return must be passive evidence only** — never an execution token or authorization.
- It does not supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- This charter draws the **signature non-authority line**: constructing a payload an operator can
  sign, and importing the returned signature, are **evidence at most** — never a command, never an
  S1 append, never capacity.
- It exists to make **"operator signed ⇒ S1 append", "signature return ⇒ execution token", and
  "what is shown ≠ what is signed" drift structurally impossible**. The signature binds to canonical,
  digest-bound, fully-visible bytes; any display/payload mismatch fails closed.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only Boundary

1. This charter creates **no** signing payload, **no** signature, **no** verifier, **no** UI/CLI
   renderer, **no** DB mutation, **no** S1 append, **no** capacity.
2. It **only** defines future boundaries for a canonical signing payload and passive signature
   return.
3. It **authorizes no** runtime, S1 access, trading, paper / canary / live, recovery, routing, or
   capacity.

### Gate B — Current Evidence Basis

- Base commit: `a376f1db4fae080de03931df2838b28f823e0e99`.
- The ReviewPackage slice is **RATIFIED** only as a **non-executable, digest-bound, passive review
  package**.
- **REVIEWABLE is not AUTHORIZED.**
- **No execution token exists.**

### Gate C — Presentation Fidelity / Anti-Blind-Signing Boundary

A future UI / CLI must:

- show the **exact matrix digest, package digest, status, warnings**, and **"REVIEWABLE is not
  AUTHORIZED"**;
- ensure **displayed bytes / summary are bound to the signed bytes**;
- forbid **hidden fields**;
- forbid **truncated digests**;
- forbid **ambiguous formatting**;
- **never ask the operator to sign unseen bytes**;
- **fail closed on any display / payload mismatch**.

### Gate D — Canonical Signing Payload Boundary

A future payload must:

- be **deterministic canonical bytes**;
- be **non-executable**;
- include the **matrix digest** and the **review package digest**;
- include **explicit no-authority flags**;
- include the exact statement: **"signature is evidence, not S1 authorization"**;
- **not** contain an append command, stream command, trading command, wallet command, capacity
  instruction, or execution token;
- **fail closed** on non-canonical formatting, extra fields, missing fields, or digest mismatch.

### Gate E — Air-Gapped Signature Return Boundary

1. Signature return is **passive evidence only**.
2. Signature return **cannot execute anything**.
3. The returned signature / package must be an **inert transfer**.
4. A future import must **verify the canonical payload digest before accepting signature evidence**.
5. **No auto-append, no auto-S1, no auto-capacity** after signature return.
6. A signature-return mismatch, stale signature, wrong digest, wrong signer, or ambiguous package
   **fails closed**.

### Gate F — UI / CLI Renderer Non-Authority Boundary

1. Renderer output is **not authority**.
2. The renderer must **not mutate** the DB or S1.
3. The renderer must **not hide warnings**.
4. The renderer must **not create files** unless separately authorized.
5. The renderer must **not generate QR / clipboard / export / signing request** without a separate
   future command.
6. The renderer **cannot downgrade** warnings or critical blockers.

### Gate G — Fail-Closed Conditions

The following must **fail closed** (at least twenty-six):

1. **displayed digest mismatch**;
2. **truncated digest**;
3. **hidden payload field**;
4. **unseen bytes**;
5. **ambiguous canonicalization**;
6. **payload includes command**;
7. **payload includes execution token**;
8. **payload includes S1 append instruction**;
9. **payload includes trading instruction**;
10. **payload includes capacity instruction**;
11. **payload includes wallet / signing instruction**;
12. **payload extra field**;
13. **payload missing field**;
14. **signature over unknown bytes**;
15. **signature over stale digest**;
16. **returned signature digest mismatch**;
17. **wrong signer identity**;
18. **stale signature**;
19. **duplicate signature ambiguity**;
20. **renderer hides warning**;
21. **renderer mutates data**;
22. **renderer truncates digest**;
23. **UI output treated as authority**;
24. **signature treated as S1 authorization**;
25. **signature return triggers auto-append**;
26. **Gemini / Claude / Codex text treated as command**;
27. **payload non-canonical formatting**;
28. **display / payload mismatch**.

The default in every degraded or ambiguous state is the **safe / blocked** outcome.

### Gate H — Non-Authority Rules

Future systems must prove (at least fourteen rules):

- **signature ≠ authorization.**
- **signing payload ≠ execution token.**
- **ReviewPackage ≠ S1 authorization.**
- **human signature ≠ automatic S1 append.**
- **UI display ≠ authority.**
- **digest match ≠ capacity.**
- **operator review ≠ paper / live / trading permission.**
- **Gemini / Claude / Codex output ≠ operator command.**
- **signature return ≠ execution.**
- **inert transfer ≠ activation.**
- **renderer output ≠ command.**
- **displayed bytes ≠ authority (only evidence).**
- **payload digest ≠ append trigger.**
- **capacity remains 0.**

### Gate I — Required Future Command Shape (descriptive only)

A later implementation command must explicitly define:

- the **exact base SHA**;
- the **exact target module / file**;
- the **canonical payload schema**;
- the **display binding rules**;
- the **anti-blind-signing tests**;
- the **signature return schema**;
- an **explicit no-S1 / no-capacity boundary**;
- **targeted tests only**.

This section grants **no** current authority; absent such a command, no signing payload, renderer, or
signature return is authorized.

### Gate J — No-Auto-Activation Post-State

- Signing Payload Construction & Air-Gapped Signature Return Boundary Charter: **BUILT / RATIFIABLE /
  UNRATIFIED**.
- S1 Matrix Evaluation & Non-Executable Operator Review Package slice: **RATIFIED**.
- Passive S1 Evidence Matrix Construction slice: **RATIFIED**.
- S1 evidence matrix construction: **RATIFIED as REVIEWABLE-only, not AUTHORIZED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper / canary / live / trading / actionability: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.

---

## Section 4 — Signing Payload / Signature Return Requirement Ledger (template, to be completed later)

No payload, renderer, or signature mechanism exists now. A future signing charter / implementation
must satisfy each requirement (documentation-only here; every entry is a future requirement, never an
authorization):

| Requirement | Guarantee | Implemented? | Status |
|-------------|-----------|--------------|--------|
| canonical_payload | deterministic canonical bytes | NO | BLOCKED |
| non_executable_payload | no command / token in payload | NO | BLOCKED |
| digest_bound_payload | matrix + package digest embedded | NO | BLOCKED |
| evidence_statement | "signature is evidence, not S1 authorization" | NO | BLOCKED |
| display_binding | shown bytes == signed bytes | NO | BLOCKED |
| no_truncation | full digest shown, never truncated | NO | BLOCKED |
| no_hidden_field | no hidden payload/display field | NO | BLOCKED |
| inert_transfer | signature return is inert | NO | BLOCKED |
| verify_before_accept | payload digest verified pre-accept | NO | BLOCKED |
| no_auto_append | no auto-S1/append after return | NO | BLOCKED |
| signer_identity_check | wrong/stale signer fails closed | NO | BLOCKED |
| renderer_non_authority | renderer mutates/hides nothing | NO | BLOCKED |

Every unimplemented requirement is **BLOCKED**; satisfying any of them does not auto-enable S1,
stream, paper, live, trading, or capacity.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this signing payload construction & air-gapped signature return boundary
   charter.
2. Only under a **separate explicit operator command of the Section I shape**: a future canonical
   payload + anti-blind-signing renderer + passive signature-return TDD slice.
3. A canonical payload, a faithful display, and a returned signature do **not** auto-enable S1,
   production stream, paper, live, trading, or capacity.

## Post-state

- Signing Payload Construction & Air-Gapped Signature Return Boundary Charter: **BUILT / RATIFIABLE /
  UNRATIFIED**.
- S1 Matrix Evaluation & Non-Executable Operator Review Package slice: **RATIFIED**.
- Passive S1 Evidence Matrix Construction slice: **RATIFIED**.
- Approval Ledger Append Abuse-Resistance preflight slice: **RATIFIED**.
- Human Approval Ledger DB infrastructure slice: **RATIFIED**.
- Day-Zero Trust Anchor / Production Verifier Wiring slice: **RATIFIED**.
- Human Approval Package Verification slice: **RATIFIED**.
- S1 evidence matrix construction: **RATIFIED as REVIEWABLE-only, not AUTHORIZED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper / canary / live / trading / actionability: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.
