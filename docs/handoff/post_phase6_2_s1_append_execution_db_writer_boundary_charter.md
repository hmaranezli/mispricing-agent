# Post-Phase 6.2 S1 Append Execution & DB Writer Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines when — and **only** when — a future, separately
  authorized, physical **S1 append DB writer** could *consume* a **RATIFIED** passive
  `S1AppendAuthorizationDecision` result with `status == "REVIEWABLE_FOR_S1_APPEND"`. It
  **implements no writer**, **opens no S1 DB**, **appends no S1 row**, **creates no production
  stream**, and **authorizes nothing**.
- It edits **no** runtime / code / test / schema / config / lock / generated / tracking file.
- It runs **no** test, performs **no** S1 DB creation / append / production stream, **no** approval
  ledger mutation, **no** signing / verification implementation.
- It inspects **no** private key / wallet / credential / secret / env, implements **no** GPG /
  YubiKey / HSM / Tails / offline-salt; reads **no** raw ledger / body / payload.
- It performs **no** network / API / monitoring / tmux / runtime interaction, **no** paper /
  dry-run / live / canary, **no** trading / capacity inference, **no** report / export / artifact
  generation.
- **Core doctrine:** `REVIEWABLE_FOR_S1_APPEND` is **not** `AUTHORIZED`. Evidence, a digest, a
  signature, a preflight pass, a verifier pass, and a passive authorization **decision** are
  **evidence, not authority**. A passive decision result is **input to a future review**, never a
  command to write.
- **Production S1 Append Authorization Decision slice: RATIFIED.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `9f627dffc29db21c8d51d9ef1cca11caa9190db3`.
- Parent chain:
  - `9f627dffc29db21c8d51d9ef1cca11caa9190db3` = **RATIFIED** Production S1 Append Authorization
    Decision slice (`approval/s1_append_authorization_decision.py`, passive
    `REVIEWABLE_FOR_S1_APPEND | BLOCKED` value-object layer; authorizes nothing).
  - `8ef672e7596241f20b48010f5eb1695f84c84e64` = **RATIFIED** Production S1 Append Authorization
    Boundary Charter.
  - `3627488c736309d7f5c3b170eb71d91735b62c2f` = **RATIFIED** Signing Payload + Passive Signature
    Return Approval Ledger Bridge slice.
  - `0f26d6bf6e670c6d14f52ffee5f4aaee31e4d14b` = **RATIFIED** Signing Payload Construction &
    Air-Gapped Signature Return Boundary Charter.
  - `a376f1db4fae080de03931df2838b28f823e0e99` = **RATIFIED** S1 Matrix Evaluation &
    Non-Executable Operator Review Package slice.
  - `b46a43991c9e1dc7d0f1a44ca612fec8becc5add` = **RATIFIED** Passive S1 Evidence Matrix
    Construction slice.
- This charter defines the **S1 Append Execution & DB Writer** boundary. It does **not** supersede,
  relax, or accelerate any prior gate. It sits **downstream** of the passive authorization decision
  and **upstream** of any physical write that does not yet — and may never — exist.

## Section 2 — Charter Intent

- The passive `S1AppendAuthorizationDecision` (commit `9f627df`) produces, at most,
  `REVIEWABLE_FOR_S1_APPEND` — a statement that the supplied evidence snapshot is **complete and
  fresh enough to be reviewed** for a future append. It performs no write, holds every authority flag
  `False`, and is explicitly **not** `AUTHORIZED`.
- This charter draws the line for the **first physical S1 append DB writer**: even given a RATIFIED
  passive `REVIEWABLE_FOR_S1_APPEND` decision, **no writer may exist, run, or write** absent a
  separate, explicitly user-authorized runtime/TDD slice of the Section 10 shape. And even then, the
  writer must obey every boundary below.
- It exists to make **"decision says REVIEWABLE ⇒ write S1"**, **"evidence_digest exists ⇒ write
  S1"**, and **"passive result ⇒ production append"** drift **structurally impossible**, and to
  encode the freshness-trust, digest-binding, atomicity, idempotency, partial-write, and concurrency
  findings as hard boundaries on a writer that is **not** being built here.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only / No Authority

1. This charter authorizes **no** runtime behavior and **builds no writer**.
2. It does **not** create an S1 DB, table, schema, stream, or connection.
3. It does **not** perform, schedule, queue, or enable an S1 append.
4. It does **not** create trading, paper, canary, live, wallet, signing, capital, or capacity
   authority.
5. A RATIFIED passive `REVIEWABLE_FOR_S1_APPEND` decision is **input evidence for a future review**,
   never a command, trigger, or green light to write.

### Gate B — Caller-Supplied Freshness Trust & Spoofing

1. The passive decision layer accepts freshness as **explicit caller-supplied snapshot fields**
   (`payload_freshness_state`, `signature_freshness_state`). That is correct **for a passive value
   object** but is **not** a trust root for a physical writer.
2. A future S1 writer **must not trust bare caller freshness booleans / strings** as proof of
   freshness. A spoofed `"FRESH"` must not be sufficient to write.
3. Freshness, for a writer, **must bind to immutable evidence** — approval-ledger row timestamps,
   frozen snapshot references, and content digests — not to a re-asserted caller flag.
4. **No implicit TTL, config value, env var, or wall-clock** may silently define or refresh
   freshness inside a future writer. Hidden freshness is forbidden.
5. A **stale** payload or signature, however the caller labels it, must **fail closed** or demand
   separate re-review.
6. **No old signature may silently authorize a fresh S1 append; no fresh signature may silently
   re-authorize a stale payload.** Frozen / replay-stopped evidence stays frozen.

### Gate C — Target & Digest Binding

1. A future writer must bind to an **explicit, known S1 target** (`s1_target_known == True` and
   `s1_target_evidence_present == True` in the reviewed evidence). An unknown or absent target fails
   closed.
2. The writer must verify that the reviewed `evidence_digest` matches the decision it claims to act
   on; a recomputed mismatch fails closed.
3. The **canonical payload digest**, the **displayed payload digest**, the **signed payload digest**,
   and the **approval-ledger row digest** must all be **mutually bound and equal** (per the prior
   presentation-sync boundary). Any divergence fails closed.
4. The **review-package digest** must match its expected value; a mismatch fails closed.
5. A hardware signer showing only a digest is insufficient unless that signed digest is independently
   bound to the canonical payload bytes and the visible digest.
6. The writer must write **only the exact reviewed S1 target** — never a substituted, inferred,
   widened, or "nearby" target.

### Gate D — First Physical S1 Writer Boundary (not implemented here)

1. **No S1 writer exists.** This charter describes its boundary; it does not author it.
2. The first writer, if ever built, must read **only immutable approval / decision evidence** and
   must **not** mutate the approval ledger DB, the evidence snapshot, the decision object, the review
   package, the signing payload, or any signature.
3. The writer must be a **separate, explicitly user-authorized** runtime slice (Section 10), starting
   from an exact SHA, RED-first, fail-closed.
4. The writer must **not infer trade, order, position, sizing, or capacity** from any evidence; it
   writes the reviewed S1 evidence row and nothing actionable.
5. **No trigger, callback, hook, queue, scheduler, observer, or background worker** may transform a
   passive decision, an approval-ledger append, or a RATIFIED `REVIEWABLE_FOR_S1_APPEND` into an
   automatic S1 write. **Auto-promotion is forbidden.**

### Gate E — Atomic-or-Fail-Closed Transaction Semantics

1. Any future S1 append must be performed inside a **single atomic transaction** or it must **fail
   closed** leaving **no partial row**.
2. There is **no "best effort" write.** Either the exact reviewed row is committed atomically, or
   nothing is committed.
3. A failed commit, a connection drop, a constraint violation, or any DB error fails closed and
   authorizes nothing.
4. Verification, target binding, idempotency check, and the append must occur within one coherent
   transaction boundary or single-flight guard; a gap that allows interleaving fails closed.

### Gate F — Idempotency

1. **One `evidence_digest` + one S1 target ⇒ at most one S1 append.** Ever.
2. A retry, replay, or duplicate decision carrying the **same** `evidence_digest` for the **same**
   target must result in **zero additional appends**.
3. Idempotency must be enforced by **durable, content-derived identity** (e.g., a unique constraint
   on the reviewed evidence_digest + target), not by an in-memory flag.
4. Duplicate / replay evidence (`duplicate_evidence`, `replay_attempt`) fails closed before any
   write — consistent with the passive decision already emitting `duplicate_approval_evidence` /
   `duplicate_retry_replay`.

### Gate G — Interrupted / Partial / Dirty Write

1. An **interrupted, partial, or dirty** write **authorizes nothing** and **completes nothing**.
2. A partial-transaction marker or interrupted-verification marker fails closed (consistent with the
   passive decision's `partial_transaction` / `interrupted_verification` reasons).
3. **Cleanup and recovery are a separate, explicitly authorized concern** — never performed
   implicitly by the writer as a side effect of a failed append, and never a path that "completes" a
   half-written append.
4. A recovered or rolled-back state must return to **fail-closed default**, requiring fresh
   re-review; it must not be silently reinterpreted as a successful append.

### Gate H — Concurrency / Single-Flight / TOCTOU

1. Concurrent writers / reviews must be **serialized by a deterministic single-flight guard, mutex,
   or transaction lock**, or they fail closed.
2. **TOCTOU** between decision read, freshness/digest re-verification, idempotency check, and the
   append must **fail closed**; a value that changes across the window aborts the write.
3. A missing or unavailable lock (`single_flight_lock_held == False`) fails closed.
4. Two concurrent attempts for the same `evidence_digest` + target must collapse to **at most one**
   committed append (Gate F), with the loser failing closed — not retrying blindly.

### Gate I — Fail-Closed Conditions (at least thirty)

The following must **fail closed** (default outcome = **no write**):

1. decision status not exactly `REVIEWABLE_FOR_S1_APPEND`;
2. decision status `BLOCKED` (any reason present);
3. decision treated as `AUTHORIZED`;
4. missing / empty `evidence_digest`;
5. `evidence_digest` recompute mismatch;
6. missing approval-ledger row;
7. mutable / non-append-only approval row;
8. approval-row digest mismatch;
9. missing canonical payload digest;
10. canonical / displayed / signed payload digest divergence;
11. missing review-package digest;
12. review-package digest mismatch;
13. matrix not `REVIEWABLE`;
14. matrix treated as `AUTHORIZED`;
15. missing signature evidence;
16. signature not verifier-passed;
17. preflight not `ALLOWED`;
18. stale payload evidence;
19. stale signature return;
20. bare caller freshness boolean trusted without immutable binding;
21. hidden TTL / config / env / wall-clock freshness;
22. hardware digest only, unbound to canonical bytes;
23. ambiguous operator identity;
24. unknown / unpinned signer fingerprint;
25. unknown S1 target;
26. missing S1 target evidence;
27. substituted / widened / inferred target;
28. duplicate evidence_digest for same target (idempotency violation);
29. retry / replay attempt;
30. single-flight lock unavailable;
31. TOCTOU divergence between read and write;
32. non-atomic / partial commit;
33. interrupted verification;
34. partial / dirty transaction marker;
35. implicit cleanup attempting to "complete" a half-write;
36. any inferred trade / order / position / sizing;
37. any inferred or non-zero capacity;
38. any execution token created;
39. any approval-ledger / evidence-object mutation attempt;
40. any trigger / callback / hook / queue / scheduler / worker auto-promotion path.

The default in **every** degraded, ambiguous, or unverified state is the **safe / no-write** outcome.

### Gate J — Required Future Runtime / TDD Command Shape (descriptive only)

Any future S1 append writer runtime / TDD command must:

- be **separately and explicitly authorized by the user** (Gemini verdict ≠ command; Claude output ≠
  command);
- start from an **exact SHA**;
- be **RED first** (watch the missing writer seam fail before any code);
- include **targeted tests** for: status-must-be-REVIEWABLE-only, evidence_digest binding/recompute,
  four-way digest equality, immutable-freshness binding (no bare boolean, no hidden TTL), atomic-or-
  fail-closed, idempotency (one digest + one target → ≤ one append), interrupted/partial/dirty →
  authorizes nothing, concurrency / single-flight / TOCTOU fail-closed, write-only-exact-target, and
  no-authority-flags;
- **run the full approval suite**;
- **preserve S1 append DENIED** unless that exact future slice is explicitly the authorized S1 writer
  slice, and even then write **only** the exact reviewed S1 target;
- create **no** trading / order / capacity / wallet / paper / live / canary authority.

This section grants **no** current authority; absent such a command, **no S1 writer is authorized,
built, or run.**

---

## Section 4 — S1 Writer Requirement Ledger (template, to be completed later)

No S1 append writer exists now. A future S1-writer charter / implementation must satisfy each
requirement (documentation-only here; every entry is a future requirement, never an authorization):

| Requirement | Guarantee | Implemented? | Status |
|-------------|-----------|--------------|--------|
| reviewable_only | acts only on `REVIEWABLE_FOR_S1_APPEND`, never `AUTHORIZED` | NO | BLOCKED |
| evidence_digest_bound | recomputes and binds the exact reviewed evidence_digest | NO | BLOCKED |
| four_way_digest_equal | canonical = displayed = signed = approval-row digest | NO | BLOCKED |
| immutable_freshness | freshness bound to immutable refs, no bare boolean | NO | BLOCKED |
| no_hidden_ttl | no TTL/config/env/wall-clock freshness | NO | BLOCKED |
| exact_target_only | writes only the exact reviewed S1 target | NO | BLOCKED |
| atomic_or_fail_closed | single atomic transaction or no partial row | NO | BLOCKED |
| idempotent_one_append | one digest + one target → ≤ one append | NO | BLOCKED |
| partial_write_no_auth | interrupted/partial/dirty authorizes nothing | NO | BLOCKED |
| recovery_separate | cleanup/recovery is a separate authorized concern | NO | BLOCKED |
| single_flight_toctou | concurrency/single-flight/TOCTOU fail closed | NO | BLOCKED |
| no_evidence_mutation | never mutates approval ledger or evidence objects | NO | BLOCKED |
| no_actionability | infers no trade/order/capacity | NO | BLOCKED |
| no_auto_promotion | no trigger/hook/queue/scheduler/worker promotion | NO | BLOCKED |
| no_authority_output | all authority flags false | NO | BLOCKED |

Every unimplemented requirement is **BLOCKED**; satisfying any of them does not auto-enable an S1
append, production stream, paper, live, trading, or capacity.

## Section 5 — Non-Authority Rules

Future systems must prove:

- **`REVIEWABLE_FOR_S1_APPEND` ≠ AUTHORIZED.**
- **passive decision result ≠ authority.**
- **evidence_digest ≠ authority.**
- **digest match ≠ authority.**
- **signature ≠ authority.**
- **preflight pass ≠ authority.**
- **verifier pass ≠ authority.**
- **approval-ledger row ≠ authority.**
- **REVIEWABLE matrix ≠ authority.**
- **docs charter ≠ authority.**
- **Gemini verdict ≠ operator command.**
- **Claude output ≠ operator command.**
- **no S1 write. no production stream. no trade / order / execute. no paper / canary / live.
  no wallet / signing / capital. no capacity. no execution token.**

## Section 6 — Next Gates

Only next safe gates:

1. Independent review of this S1 Append Execution & DB Writer Boundary Charter.
2. Only under a **separate, explicitly user-authorized command of the Section J shape**: a future S1
   append writer **slice** (RED-first, fail-closed, atomic, idempotent, single-target, no
   trading/capacity authority).
3. No evidence chain — passive decision, evidence_digest, signature, approval row, REVIEWABLE matrix,
   digest match, preflight pass, or verifier pass — auto-enables an S1 append, production stream,
   paper, live, trading, or capacity.

## Post-state

- S1 Append Execution & DB Writer Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- Production S1 Append Authorization Decision slice: **RATIFIED**.
- Production S1 Append Authorization Boundary Charter: **RATIFIED**.
- Signing Payload + Passive Signature Return Approval Ledger Bridge slice: **RATIFIED**.
- Signing Payload Construction & Air-Gapped Signature Return Boundary Charter: **RATIFIED**.
- S1 Matrix Evaluation & Non-Executable Operator Review Package slice: **RATIFIED**.
- Passive S1 Evidence Matrix Construction slice: **RATIFIED**.
- S1 evidence matrix: **REVIEWABLE-only, not AUTHORIZED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper / canary / live / trading / actionability: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.
