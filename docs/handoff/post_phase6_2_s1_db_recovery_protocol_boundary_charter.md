# Post-Phase 6.2 S1 DB Recovery Protocol Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the **human recovery protocol boundaries** for a live or
  candidate S1 DB that has entered `BLOCKED_RECOVERY_REQUIRED` or a suspect state. It **performs no
  recovery**, **creates / modifies no DB file**, **deletes nothing**, and **authorizes nothing**.
- It edits **no** runtime / code / test / schema / config / lock / generated / tracking file.
- It runs **no** test, performs **no** live S1 DB creation, **no** S1 append, **no** production
  stream, **no** writer execution, **no** approval-ledger mutation, **no** signing / verification
  implementation.
- It inspects **no** private key / wallet / credential / secret / env, implements **no** GPG /
  YubiKey / HSM / Tails / offline-salt; reads **no** raw ledger / body / payload.
- It performs **no** network / API / monitoring / tmux / runtime interaction, **no** paper /
  dry-run / live / canary, **no** trading / capacity inference, **no** report / export / artifact
  generation.
- **Core doctrine:** `BLOCKED_RECOVERY_REQUIRED` stays **fail-closed** until a **separate, explicitly
  authorized human recovery command** acts. **Recovery is not authorization.** A clean forensic
  classification is **not** S1 append authorization; DB cleanliness **never** implies append, stream,
  or trading authority.
- **Absolute no-delete / no-cleanup law:** nothing in this charter — and nothing it ever describes —
  may delete, truncate, vacuum, checkpoint, rewrite, move, or "fix" any `.db` / `.sqlite3` / `.wal` /
  `.shm` / `.journal` / `.lock` artifact.
- **Live S1 DB Initialization & Schema Provisioning Boundary Charter: RATIFIED** (but **Live S1 DB:
  NOT CREATED**).
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `5b3c1c9cc44c1e4cf52e9147a71a0a3cdefb2222`.
- Parent chain:
  - `5b3c1c9cc44c1e4cf52e9147a71a0a3cdefb2222` = **RATIFIED** Live S1 DB Initialization & Schema
    Provisioning Boundary Charter (recovery explicitly deferred to **this** charter).
  - `3075a4b128bb2668fc26cfa84537aaacd735c6d8` = **RATIFIED** S1 Append Execution & DB Writer runtime
    slice (emits `BLOCKED_RECOVERY_REQUIRED`, performs no cleanup).
  - `33f328057b6d75436b32f6da60de37c6dec56cf9` = **RATIFIED** S1 Append Execution & DB Writer
    Boundary Charter.
  - `9f627dffc29db21c8d51d9ef1cca11caa9190db3` = **RATIFIED** Production S1 Append Authorization
    Decision slice.
- This charter owns the recovery boundary that the writer slice and the initialization charter both
  defer to. It does **not** supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- The ratified writer fails closed with `BLOCKED_RECOVERY_REQUIRED` when it observes a hot rollback
  journal, orphan WAL/SHM, lock residue, or pre-existing suspect DB state — and it performs **no
  cleanup**. The initialization charter likewise fails closed on suspect state and defers recovery
  **here**. This charter draws the line for what a **human** may and may not do next.
- It exists to make **"recovery ran ⇒ DB healthy ⇒ append authorized"** drift **structurally
  impossible**: recovery is a **forensic, preservation-first, human-decision** process that ends in a
  **classification + report + a demand for separate execution authorization** — never in a silent
  transformation of suspect state into healthy state, and never in an inferred append/stream/trading
  authority.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only / No Authority / No Auto-Recovery

1. This charter authorizes **no** runtime behavior and **performs no recovery**.
2. It does **not** create, open for write, modify, repair, or delete any DB / WAL / SHM / journal /
   lock artifact.
3. It does **not** perform, schedule, queue, or enable an S1 append, production stream, or DB
   initialization.
4. It does **not** create trading, paper, canary, live, wallet, signing, capital, or capacity
   authority.
5. **No auto-recovery.** Recovery execution must be a **separate, explicitly user-authorized human
   command**; it must never be triggered by writer import/execution, initialization, review-package
   construction, approval-ledger append, scheduler, hook, callback, queue, worker, observer, or
   stream.

### Gate B — Fail-Closed Persistence of BLOCKED_RECOVERY_REQUIRED

1. `BLOCKED_RECOVERY_REQUIRED` (and any suspect classification) **remains fail-closed** until a
   separate human recovery-execution command is explicitly authorized.
2. No passage of time, retry, restart, re-import, or re-review may silently clear a recovery state.
3. The safe default in every uncertain state is **remain blocked, change nothing on disk**.
4. A recovery state is **not** an error to be swallowed; it is a stop that requires human forensic
   action under this protocol.

### Gate C — Air-Gapped / Read-Only Forensic Inspection

1. All inspection is **read-only** and prefers an **air-gapped** context.
2. Inspection must open artifacts **read-only** (e.g. SQLite immutable / `mode=ro` semantics) and must
   never acquire a write lock or run a write/checkpoint pragma.
3. Inspection must perform **no** network / runtime / monitoring interaction.
4. Inspection must not load, execute, or trust any code or trigger embedded in or referenced by the
   suspect artifacts.
5. If read-only inspection cannot be guaranteed, inspection **does not proceed** and the state
   remains blocked.

### Gate D — Mandatory Forensic Copy Before Any Analysis

1. Before **any** analysis, take a **forensic copy / preservation snapshot** of: the DB file, the WAL,
   the SHM, the rollback journal, any lock / residue files, and the parent directory metadata.
2. Capture **file stats** (size, mtime/ctime, ownership, POSIX permissions, inode) and **content
   hashes** of each artifact, recorded alongside the copy.
3. Analysis is performed **only on the copy**, never on the original.
4. The original artifacts are **preserved byte-for-byte** and left exactly as found.
5. If a faithful forensic copy cannot be made (e.g. capacity/permission failure), analysis **does not
   proceed** and the state remains blocked.

### Gate E — Absolute No-Delete / No-Cleanup Law

1. **Never delete, truncate, vacuum, checkpoint, rewrite, move, rename, or "fix"** any `.db` /
   `.sqlite3` / `.wal` / `.shm` / `.journal` / `.lock` file under this charter.
2. **No** `PRAGMA wal_checkpoint`, `VACUUM`, `REINDEX`, `.recover`, journal replay, or any
   mutation-bearing operation on the original.
3. **No** chmod / chown / touch of the originals.
4. Cleanup, repair, or replay — if ever permitted — belongs to a **separate, explicitly authorized
   recovery-execution** step (Gate J), never to inspection/classification here.

### Gate F — Operator Decision Tree

The operator follows: **inspect → classify → preserve → report → require separate recovery-execution
authorization.**

1. **Inspect** (read-only, on the forensic copy, per Gates C/D).
2. **Classify** into exactly one state (Gate G).
3. **Preserve** originals untouched (Gate E) and retain the forensic copy + hashes + stats.
4. **Report** the classification, evidence, hashes, environment findings, and DoS/capacity risk.
5. **Require separate authorization** for any recovery execution (Gate J). The tree **ends** at a
   report + an authorization request; it never self-escalates into a fix.

### Gate G — Classification States

Exactly one of:

1. **CLEAN_REOPEN_CANDIDATE** — forensics suggest a clean, consistent DB that *could* be a reopen
   candidate. This is a **candidate classification only**, **not** authorization to reopen, append, or
   stream.
2. **SUSPECT_NEEDS_REVIEW** — anomalies that need further human review; remains blocked.
3. **CORRUPT_DO_NOT_USE** — evidence of corruption; the DB must not be used; remains blocked.
4. **PARTIAL_APPEND_UNRESOLVED** — evidence of an interrupted/partial append that cannot be resolved
   by inspection; remains blocked.
5. **BLOCKED_RECOVERY_REQUIRED** — default/fallback; recovery execution required under separate
   authorization.

No classification — including `CLEAN_REOPEN_CANDIDATE` — grants append, stream, initialization, or
trading authority.

### Gate H — Power-Loss / Kernel-Panic / Journal & WAL Handling

1. **Power loss, kernel panic, OOM kill, or abrupt termination** during a write are treated as
   **suspect by default** and preserved, never auto-replayed.
2. A **hot rollback journal**, **orphan WAL**, or **orphan SHM** is **preserved and classified**,
   never deleted or checkpointed.
3. The presence of WAL/SHM is interpreted only against the recorded forensic evidence; a heuristic
   "looks fine" is insufficient to downgrade from suspect.
4. Any uncertainty about whether a journal/WAL represents a committed or partial transaction →
   **PARTIAL_APPEND_UNRESOLVED** or **BLOCKED_RECOVERY_REQUIRED**, blocked.

### Gate I — SQLite Sync / Durability Assumptions

1. **`synchronous=FULL`** is the **current ratified minimum floor** assumed for any live S1 DB.
2. **`synchronous=EXTRA`** and **explicit directory fsync** are **stricter future options** that
   require **separate ratification**; they are **not** authorized or assumed by this charter.
3. Recovery reasoning must not assume durability stronger than the ratified floor, nor weaker.
4. Any evidence that the floor was not actually in effect at write time → classify **SUSPECT** or
   stronger, blocked.

### Gate J — Physical Environment Checks (pre-condition for any future recovery)

Before any **future, separately authorized** recovery execution, the environment must be checked
(documentation-only here):

1. **mount point identity** of the DB path;
2. **dedicated partition** recommendation for the live S1 DB;
3. **filesystem type** and its crash/fsync semantics;
4. **free bytes** headroom;
5. **free inodes** headroom;
6. **disk pressure** / I/O error indicators;
7. **read-only remount** option for forensic safety;
8. **backup target isolation** (separate device/mount from the suspect DB).

These are **gating pre-conditions** for a future recovery command, not authority granted here.

### Gate K — Shared-Root / Capacity-Exhaustion DoS Risk

1. A **shared root / shared mount** for the S1 DB, forensic copies, approval ledger, and unrelated
   data is an explicit **DoS and integrity risk** and must be recognized.
2. **Capacity exhaustion** (bytes or inodes) can itself induce suspect/blocked states and can be
   weaponized; a forensic copy that competes for the same shared root can worsen the failure.
3. The recommendation is **isolated, dedicated storage** for the live S1 DB and a **separate isolated
   target** for forensic copies/backups.
4. Capacity-exhaustion or shared-root contention during inspection → **fail closed**, do not force a
   copy that risks the shared root.

### Gate L — Non-Transformation / Non-Inference Rules

1. Recovery must **not silently transform** suspect state into healthy state.
2. Recovery must **not infer S1 append authorization** from DB cleanliness or a
   `CLEAN_REOPEN_CANDIDATE` classification.
3. Recovery must **not** trigger the writer, a production stream, an approval-ledger mutation, a
   scheduler, hook, callback, queue, worker, or observer.
4. Recovery must **not** access secrets, wallets, private keys, env vars, or implement GPG / YubiKey /
   HSM / Tails / offline-salt access.
5. Recovery must **not** initialize, create, or schema-provision a live S1 DB (that is a separate
   ratified charter, and the DB remains **NOT CREATED**).

### Gate M — Fail-Closed Conditions (at least thirty-five)

The following must **fail closed** (default = **change nothing on disk, remain blocked**):

1. `BLOCKED_RECOVERY_REQUIRED` present;
2. any suspect classification present;
3. read-only inspection not guaranteed;
4. write lock would be required to inspect;
5. air-gap not achievable when required;
6. forensic copy not yet taken;
7. forensic copy incomplete (missing DB/WAL/SHM/journal/lock);
8. parent-directory metadata not captured;
9. file stats not captured;
10. content hashes not captured;
11. analysis attempted on the original instead of the copy;
12. any delete attempted on `.db`/`.sqlite3`;
13. any delete attempted on `.wal`/`.shm`;
14. any delete attempted on `.journal`/`.lock`;
15. truncate attempted;
16. vacuum attempted;
17. checkpoint / `wal_checkpoint` attempted;
18. rewrite / `.recover` / reindex attempted;
19. move / rename of any artifact attempted;
20. chmod / chown / touch of originals attempted;
21. journal replay attempted during inspection;
22. hot journal present;
23. orphan WAL present;
24. orphan SHM present;
25. lock residue present;
26. power-loss / kernel-panic / OOM signature;
27. partial/interrupted append evidence (PARTIAL_APPEND_UNRESOLVED);
28. corruption evidence (CORRUPT_DO_NOT_USE);
29. durability floor (`synchronous=FULL`) not provably in effect;
30. `synchronous=EXTRA` / dir-fsync assumed without ratification;
31. mount point / filesystem unverified;
32. free bytes below safe headroom;
33. free inodes below safe headroom;
34. disk pressure / I/O error indicators;
35. shared-root contention with forensic copy target;
36. backup target not isolated;
37. recovery attempting to mark DB healthy (silent transformation);
38. recovery inferring append authorization from cleanliness;
39. recovery triggering writer / stream / ledger mutation / scheduler / hook / callback / queue /
    worker / observer;
40. recovery accessing secret / wallet / key / env;
41. recovery initializing / creating / provisioning a live S1 DB.

The default in **every** degraded, ambiguous, or unverified state is the **safe / no-change /
blocked** outcome.

### Gate N — Required Future Recovery-Execution Command Shape (recovery execution only)

Any future recovery-execution runtime / TDD slice **or** operator runbook must:

- be **separately and explicitly authorized by the user** (Gemini verdict ≠ command; Claude output ≠
  command);
- start from an **exact SHA** (for code) or an explicit, versioned runbook (for operator steps);
- be **RED first** (for any code seam) and **preservation-first** (forensic copy before action);
- be scoped to **recovery execution only** — **no** DB initialization, **no** append, **no** stream,
  **no** trading/capacity;
- enforce the **absolute no-delete law** on originals unless a *separately, explicitly* authorized,
  logged, reversible-by-preservation step says otherwise on the **copy**, never blindly on the
  original;
- require the **physical-environment pre-conditions** (Gate J) and **DoS/shared-root checks**
  (Gate K) to pass first;
- end in an explicit classification + report; **never** silently transform suspect → healthy;
- **preserve S1 append DENIED**, production stream BLOCKED, capacity 0, and **Live S1 DB NOT CREATED**
  unless a *separate* ratified initialization command applies;
- create **no** trading / order / capacity / wallet / paper / live / canary authority.

This section grants **no** current authority; absent such a command, **no recovery is executed and no
artifact is modified.**

---

## Section 4 — Recovery Requirement Ledger (template, to be completed later)

No recovery-execution mechanism exists now. A future recovery charter / runbook / implementation must
satisfy each requirement (documentation-only here; every entry is a future requirement, never an
authorization):

| Requirement | Guarantee | Implemented? | Status |
|-------------|-----------|--------------|--------|
| fail_closed_persist | blocked state persists until separate authorization | NO | BLOCKED |
| read_only_inspection | inspection is strictly read-only / air-gapped | NO | BLOCKED |
| forensic_copy_first | full forensic copy + stats + hashes before analysis | NO | BLOCKED |
| analyze_copy_only | analysis only on the copy, never the original | NO | BLOCKED |
| absolute_no_delete | never delete/truncate/vacuum/checkpoint/rewrite/move | NO | BLOCKED |
| classify_one_state | exactly one of the five classification states | NO | BLOCKED |
| no_silent_transform | suspect never silently becomes healthy | NO | BLOCKED |
| no_authority_inference | cleanliness never implies append/stream authority | NO | BLOCKED |
| no_auto_trigger | no writer/stream/ledger/scheduler/hook trigger | NO | BLOCKED |
| isolation | no secret/wallet/key/env access; no network/runtime | NO | BLOCKED |
| durability_floor | synchronous=FULL floor; EXTRA needs ratification | NO | BLOCKED |
| env_preconditions | mount/fs/free-bytes/inodes/pressure verified | NO | BLOCKED |
| dos_shared_root | shared-root / capacity-exhaustion risk recognized | NO | BLOCKED |
| backup_target_isolated | forensic/backup target on isolated storage | NO | BLOCKED |
| no_db_init | recovery never initializes/creates a live S1 DB | NO | BLOCKED |
| separate_exec_auth | recovery execution separately authorized | NO | BLOCKED |
| no_authority_output | all authority flags false | NO | BLOCKED |

Every unimplemented requirement is **BLOCKED**; satisfying any of them does not auto-enable a DB
creation, S1 append, production stream, paper, live, trading, or capacity.

## Section 5 — Non-Authority Rules

Future systems must prove:

- **recovery ≠ authorization.**
- **clean forensic classification ≠ S1 append authority.**
- **`CLEAN_REOPEN_CANDIDATE` ≠ reopen/append/stream authority.**
- **DB cleanliness ≠ trading authority.**
- **`REVIEWABLE_FOR_S1_APPEND` ≠ AUTHORIZED.**
- **inspection ≠ repair.**
- **docs charter ≠ authority.**
- **Gemini verdict ≠ operator command.**
- **Claude output ≠ operator command.**
- **no S1 append. no production stream. no DB creation. no trade / order / execute.
  no paper / canary / live. no wallet / signing / capital. no capacity. no execution token.**

## Section 6 — Next Gates

Only next safe gates:

1. Independent review of this S1 DB Recovery Protocol Boundary Charter.
2. Only under a **separate, explicitly user-authorized command of the Section N shape**: a future
   recovery-execution slice / runbook (preservation-first, fail-closed, no DB init, no append, no
   stream, no trading/capacity authority).
3. No artifact — writer, decision, review package, approval row, REVIEWABLE matrix, initialized
   container, or a `CLEAN_REOPEN_CANDIDATE` classification — auto-enables a DB creation, S1 append,
   production stream, paper, live, trading, or capacity.

## Post-state

- S1 DB Recovery Protocol Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- Live S1 DB Initialization & Schema Provisioning Boundary Charter: **RATIFIED**.
- S1 Append Execution & DB Writer runtime slice: **RATIFIED**.
- S1 Append Execution & DB Writer Boundary Charter: **RATIFIED**.
- Production S1 Append Authorization Decision slice: **RATIFIED**.
- Live S1 DB: **NOT CREATED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper / canary / live / trading / actionability: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.
