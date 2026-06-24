# Post-Phase 6.2 Live S1 DB Initialization & Schema Provisioning Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines when — and **only** when — a future, separately authorized
  step could **initialize the live S1 SQLite DB file** and **provision its append-only schema** as a
  passive container. It **creates no DB**, **provisions no schema**, **appends nothing**, **opens no
  production stream**, and **authorizes nothing**.
- It edits **no** runtime / code / test / schema / config / lock / generated / tracking file.
- It runs **no** test, performs **no** live S1 DB creation, **no** production S1 append, **no**
  production stream, **no** approval-ledger mutation, **no** writer execution, **no** signing /
  verification implementation.
- It inspects **no** private key / wallet / credential / secret / env, implements **no** GPG /
  YubiKey / HSM / Tails / offline-salt; reads **no** raw ledger / body / payload.
- It performs **no** network / API / monitoring / tmux / runtime interaction, **no** paper /
  dry-run / live / canary, **no** trading / capacity inference, **no** report / export / artifact
  generation.
- **Core doctrine:** creating a live DB **container** is **not** S1 append authorization; provisioning
  a **schema** is **not** production-stream authorization. `REVIEWABLE_FOR_S1_APPEND` remains **not**
  `AUTHORIZED`. An empty, well-formed container authorizes nothing.
- **Recovery is explicitly OUT OF SCOPE here.** Any `BLOCKED_RECOVERY_REQUIRED` handling is deferred
  to a separate, future **S1 DB Recovery Protocol Boundary Charter**.
- **S1 Append Execution & DB Writer runtime slice: RATIFIED.**
- **Live S1 DB: NOT CREATED.** **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
  **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `3075a4b128bb2668fc26cfa84537aaacd735c6d8`.
- Parent chain:
  - `3075a4b128bb2668fc26cfa84537aaacd735c6d8` = **RATIFIED** S1 Append Execution & DB Writer runtime
    slice (`approval/s1_append_execution_db_writer.py`; isolated, test-path-only, fail-closed,
    atomic-or-fail-closed, `UNIQUE(evidence_digest, s1_target)`; all production authority flags
    `False`).
  - `33f328057b6d75436b32f6da60de37c6dec56cf9` = **RATIFIED** S1 Append Execution & DB Writer
    Boundary Charter.
  - `9f627dffc29db21c8d51d9ef1cca11caa9190db3` = **RATIFIED** Production S1 Append Authorization
    Decision slice.
  - `8ef672e7596241f20b48010f5eb1695f84c84e64` = **RATIFIED** Production S1 Append Authorization
    Boundary Charter.
- This charter defines the **Live S1 DB Initialization & Schema Provisioning** boundary. It does
  **not** supersede, relax, or accelerate any prior gate. It sits **upstream** of any live container
  and provisions nothing.

## Section 2 — Charter Intent

- The ratified writer slice writes only to **caller-supplied tempfile / test SQLite paths**. It has
  **no default path** and **no live container**. Before any live append could ever be reviewed, a
  **live S1 DB file** and its **append-only schema** would have to exist — and that creation is its
  own separately commanded, fail-closed step, not a side effect of importing or running the writer.
- This charter draws the line so that **"writer exists ⇒ create live DB"**, **"schema provisioned ⇒
  stream authorized"**, and **"container present ⇒ append authorized"** drift is **structurally
  impossible**. An initialized, empty, well-formed container is **inert evidence of readiness to be
  reviewed**, never authority to append, stream, or trade.
- It also fixes the durability floor (`journal_mode=WAL`, `synchronous=FULL` minimum), the
  append-only schema shape, and the evidence-binding constraints so that a future live container is
  **compatible with the ratified writer** without re-litigating those guarantees — while keeping
  **recovery** strictly deferred to a separate charter.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only / No Authority / No Auto-Activation

1. This charter authorizes **no** runtime behavior and **provisions nothing**.
2. It does **not** create a live S1 DB file, table, index, or schema.
3. It does **not** perform, schedule, queue, or enable an S1 append or production stream.
4. It does **not** create trading, paper, canary, live, wallet, signing, capital, or capacity
   authority.
5. Initialization, if ever performed, must be **separately and explicitly commanded by the user** and
   must **never** be triggered by writer import, review-package construction, approval-ledger append,
   scheduler, hook, callback, queue, worker, observer, or stream.

### Gate B — Live S1 DB Path Policy

1. The live S1 DB path must be **explicit and caller-supplied** for the initialization command. There
   is **no default / fallback path**, and none may be hard-coded into the writer or any module.
2. The path, its parent directory, and ownership must be **explicitly declared and verified** before
   creation; an unverifiable or ambiguous path fails closed.
3. **POSIX permissions** must be restrictive and explicitly asserted: the DB file and its parent
   directory must not be world-writable; group/other write must be denied unless explicitly ratified
   otherwise. A permissions check that cannot be satisfied fails closed.
4. The parent directory must **exist, be owned as declared, and have restrictive permissions** before
   the file is created; initialization must not silently create or chmod arbitrary parent paths.
5. The live path must be **distinct** from the approval-ledger DB path, any test path, and any
   tempfile path. Path collision with prior evidence artifacts fails closed.
6. A pre-existing file at the live path is **not** silently reused or overwritten; pre-existing state
   triggers the suspect-state / recovery deferral (Gate G), not a blind reuse.

### Gate C — SQLite / WAL Provisioning Floor

1. Journal mode floor: **`journal_mode=WAL`**.
2. Durability floor: **`synchronous=FULL`** is the ratified **minimum floor** and must not be relaxed
   (no `NORMAL`, no `OFF`).
3. **`synchronous=EXTRA`** may be **documented only** as a stricter future option; adopting it
   requires **explicit separate ratification** and is **not** authorized by this charter.
4. Pragmas must be **explicitly asserted after provisioning** (read back and verified), never assumed.
   A mismatch between requested and effective pragmas fails closed.
5. WAL/SHM companion files are a **normal consequence** of WAL mode; their *expected* presence after a
   clean init is distinct from *orphan/suspect* residue (Gate G), and this distinction must be
   explicit, not heuristic guesswork.
6. No pragma may weaken durability, integrity, or append-only guarantees for throughput.

### Gate D — Append-Only Schema Provisioning

1. The schema must define a **passive, append-only S1 record container** — evidence rows only.
2. **In-place UPDATE and DELETE must be forbidden** at the schema level (e.g. `BEFORE UPDATE` /
   `BEFORE DELETE` triggers `RAISE(ABORT)`), consistent with the ratified approval-ledger and writer
   patterns.
3. Columns must carry **evidence and binding fields only** (e.g. evidence_digest, s1_target,
   canonical_payload_digest, approval_row_digest, freshness_binding_digest, immutable_snapshot_ref,
   operator_command_id, result_digest) — and **no** actionable column.
4. Every column must be **NOT NULL** where the writer requires it; a nullable required field fails
   closed at review.
5. Schema provisioning is **idempotent and inert**: creating the schema inserts **zero rows** and
   authorizes nothing.
6. The provisioned schema must be **exactly compatible** with the ratified writer so that no schema
   drift silently changes append semantics.

### Gate E — UNIQUE / Evidence-Binding Requirements

1. The schema must enforce **`UNIQUE(evidence_digest, s1_target)`** so that **one evidence_digest +
   one s1_target ⇒ at most one append**, matching the ratified writer.
2. The UNIQUE constraint is **schema-level and durable**, not an application flag.
3. Evidence-binding columns must be present and constrained so the writer's freshness-binding and
   digest-equality checks remain enforceable.
4. No alternate key, upsert, `INSERT OR REPLACE`, or `ON CONFLICT REPLACE` clause may be provisioned
   that could silently overwrite or de-duplicate-by-mutation an existing evidence row.

### Gate F — No Actionable Semantics

1. The schema must **not** encode trade, order, position, sizing, price, side, fill, PnL, capacity, or
   actionability semantics.
2. The container holds **append evidence**, never an instruction.
3. No column, index, view, or trigger may compute, infer, or expose a trade/order/capacity signal.
4. Creating or provisioning the container grants **no** execution token, stream, paper/live flag, or
   capacity.

### Gate G — Pre-Existing / Suspect State (recovery deferred)

1. **Recovery is OUT OF SCOPE for this charter.** This gate only defines the **fail-closed deferral**.
2. If, during initialization, a **rollback journal**, **orphan/suspect WAL/SHM**, **lock residue**, or
   any **pre-existing suspect DB state** is present at the live path, initialization must **fail
   closed** and perform **no cleanup / no delete / no auto-recovery**.
3. Such a state must surface as a deferral to the future **S1 DB Recovery Protocol Boundary Charter**;
   this charter neither defines nor performs recovery.
4. No journal / WAL / SHM / lock file may be deleted, truncated, moved, or "repaired" by
   initialization.
5. The default in any uncertain pre-existing state is **fail closed**, leaving the on-disk state
   exactly as found.

### Gate H — Isolation of Initialization

1. Initialization must **not** mutate the approval-ledger DB or any prior evidence artifact (review
   package, signing payload, signature, decision object, append-evidence snapshot).
2. Initialization must **not** read secrets, wallets, private keys, env vars, or implement GPG /
   YubiKey / HSM / Tails / offline-salt access.
3. Initialization must **not** open a network/API/monitoring/tmux/runtime interaction.
4. Initialization touches **only** the explicitly declared live S1 DB path and its declared parent
   directory, under the path policy of Gate B.

### Gate I — Fail-Closed Conditions (at least thirty)

The following must **fail closed** (default outcome = **no DB created / no schema provisioned**):

1. missing / empty live path;
2. default / fallback path used;
3. hard-coded path in any module;
4. ambiguous / unresolvable path;
5. live path colliding with approval-ledger DB path;
6. live path colliding with a test / tempfile path;
7. parent directory missing;
8. parent directory ownership mismatch;
9. parent directory world-writable / over-permissive;
10. DB file world-writable / over-permissive;
11. requested POSIX permissions unsatisfiable;
12. pre-existing file at live path (reuse/overwrite refused);
13. rollback journal present at init;
14. orphan / suspect WAL present at init;
15. orphan / suspect SHM present at init;
16. lock residue present at init;
17. any pre-existing suspect DB state;
18. attempt to clean up / delete journal/WAL/SHM/lock;
19. `journal_mode` not WAL;
20. `synchronous` below FULL floor (NORMAL / OFF);
21. `synchronous=EXTRA` adopted without separate ratification;
22. effective pragma mismatch vs requested;
23. UPDATE/DELETE not forbidden at schema level;
24. missing `UNIQUE(evidence_digest, s1_target)`;
25. upsert / `INSERT OR REPLACE` / `ON CONFLICT REPLACE` provisioned;
26. required evidence column nullable / absent;
27. actionable column (trade/order/price/side/capacity) present;
28. schema drift incompatible with ratified writer;
29. initialization triggered by writer import;
30. initialization triggered by review-package construction;
31. initialization triggered by approval-ledger append;
32. initialization triggered by scheduler / hook / callback / queue / worker / observer / stream;
33. initialization mutating approval-ledger DB or prior evidence;
34. initialization reading secret / wallet / key / env;
35. initialization performing network / runtime interaction;
36. any append / row insert during initialization;
37. any production stream / trade / order / capacity side effect;
38. any execution token created.

The default in **every** degraded, ambiguous, or unverified state is the **safe / no-create**
outcome.

### Gate J — Required Future Runtime / TDD Command Shape (initialization/provisioning only)

Any future live S1 DB initialization / schema-provisioning command must:

- be **separately and explicitly authorized by the user** (Gemini verdict ≠ command; Claude output ≠
  command);
- start from an **exact SHA**;
- be **RED first** (watch the missing init/provisioning seam fail before any code);
- be scoped to **initialization & schema provisioning only** — **no** append, **no** stream, **no**
  recovery, **no** trading/capacity;
- include **targeted tests** for: explicit-path-required / no-default-path, path & permission &
  ownership policy, parent-directory policy, `journal_mode=WAL`, `synchronous>=FULL` floor (and
  EXTRA-needs-ratification), pragma read-back assertion, append-only UPDATE/DELETE prohibition,
  `UNIQUE(evidence_digest, s1_target)`, no-actionable-column, zero-rows-on-init, pre-existing/suspect
  state fail-closed with no cleanup, no-auto-activation (no import/append/scheduler trigger), and
  no-authority output;
- **run the full approval suite**;
- **preserve S1 append DENIED**, production stream BLOCKED, and capacity 0;
- **defer all recovery** to the future S1 DB Recovery Protocol Boundary Charter;
- create **no** trading / order / capacity / wallet / paper / live / canary authority.

This section grants **no** current authority; absent such a command, **no live S1 DB is initialized,
provisioned, or created.**

---

## Section 4 — Live S1 DB Initialization Requirement Ledger (template, to be completed later)

No live S1 DB initialization mechanism exists now. A future initialization charter / implementation
must satisfy each requirement (documentation-only here; every entry is a future requirement, never an
authorization):

| Requirement | Guarantee | Implemented? | Status |
|-------------|-----------|--------------|--------|
| explicit_path_only | explicit caller path; no default/fallback | NO | BLOCKED |
| path_permissions_policy | restrictive POSIX perms + ownership verified | NO | BLOCKED |
| parent_dir_policy | parent exists, owned, restrictive, not auto-chmod | NO | BLOCKED |
| no_blind_reuse | pre-existing file not reused/overwritten | NO | BLOCKED |
| journal_mode_wal | journal_mode=WAL | NO | BLOCKED |
| synchronous_full_floor | synchronous>=FULL; EXTRA needs ratification | NO | BLOCKED |
| pragma_readback | effective pragmas asserted, not assumed | NO | BLOCKED |
| append_only_schema | UPDATE/DELETE forbidden at schema level | NO | BLOCKED |
| unique_evidence_target | UNIQUE(evidence_digest, s1_target) | NO | BLOCKED |
| no_upsert_replace | no upsert/INSERT OR REPLACE/ON CONFLICT REPLACE | NO | BLOCKED |
| no_actionable_columns | no trade/order/price/side/capacity columns | NO | BLOCKED |
| zero_rows_on_init | provisioning inserts zero rows | NO | BLOCKED |
| writer_compatible | schema exactly matches ratified writer | NO | BLOCKED |
| no_auto_activation | no import/append/scheduler/hook trigger | NO | BLOCKED |
| isolation | no ledger/evidence mutation, no secret/env/net | NO | BLOCKED |
| suspect_state_fail_closed | pre-existing/suspect state fails closed, no cleanup | NO | BLOCKED |
| recovery_deferred | recovery deferred to separate charter | NO | BLOCKED |
| no_authority_output | all authority flags false | NO | BLOCKED |

Every unimplemented requirement is **BLOCKED**; satisfying any of them does not auto-enable an S1
append, production stream, paper, live, trading, or capacity.

## Section 5 — Non-Authority Rules

Future systems must prove:

- **live DB container ≠ S1 append authority.**
- **schema provisioned ≠ production-stream authority.**
- **empty well-formed container ≠ authority.**
- **`REVIEWABLE_FOR_S1_APPEND` ≠ AUTHORIZED.**
- **writer exists ≠ create live DB.**
- **container present ≠ append authorized.**
- **docs charter ≠ authority.**
- **Gemini verdict ≠ operator command.**
- **Claude output ≠ operator command.**
- **no S1 append. no production stream. no trade / order / execute. no paper / canary / live.
  no wallet / signing / capital. no capacity. no execution token.**

## Section 6 — Next Gates

Only next safe gates:

1. Independent review of this Live S1 DB Initialization & Schema Provisioning Boundary Charter.
2. A separate **S1 DB Recovery Protocol Boundary Charter** to own all `BLOCKED_RECOVERY_REQUIRED`
   handling (explicitly out of scope here).
3. Only under a **separate, explicitly user-authorized command of the Section J shape**: a future live
   S1 DB **initialization & schema-provisioning** slice (RED-first, fail-closed, no append, no stream,
   no recovery, no trading/capacity authority).
4. No artifact — writer, decision, review package, approval row, REVIEWABLE matrix, or an initialized
   empty container — auto-enables an S1 append, production stream, paper, live, trading, or capacity.

## Post-state

- Live S1 DB Initialization & Schema Provisioning Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- S1 Append Execution & DB Writer runtime slice: **RATIFIED**.
- S1 Append Execution & DB Writer Boundary Charter: **RATIFIED**.
- Production S1 Append Authorization Decision slice: **RATIFIED**.
- Live S1 DB: **NOT CREATED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper / canary / live / trading / actionability: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.
