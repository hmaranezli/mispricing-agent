# Post-Phase 6.2 Schema & Journal Unification Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the rules for resolving the **production-blocking seam**
  between the ratified initializer and the ratified writer. It **implements no unification**,
  **performs no DB operation**, **migrates / renames / copies / deletes / checkpoints / vacuums /
  repairs nothing**, and **authorizes nothing**.
- It edits **no** runtime / code / test / schema / config / lock / generated / tracking file.
- It runs **no** test, performs **no** refactor, **no** DB migration, **no** live S1 DB creation /
  modification, **no** S1 append, **no** production stream, **no** writer / circuit / initializer
  execution, **no** approval-ledger mutation.
- It implements **no** CLI / API / auth / network, adds **no** dependency, inspects **no** private
  key / wallet / credential / secret / env.
- It performs **no** paper / dry-run / live / canary, **no** trading / capacity inference, **no**
  report / export / artifact generation.
- **The seam (PRODUCTION BLOCKER, UNSTARTED):** `approval/live_s1_db_initialization.py` provisions
  table **`s1_appends`** under **WAL** mode; `approval/s1_append_execution_db_writer.py` appends to
  table **`s1_append_log`** with its **own** rollback-journal behavior. The circuit composes them in
  **isolated test/temp scope only** and is **not** production-activatable in this split form.
- **Core doctrine:** a **unified schema/journal design is not append authorization.** Unification is
  **not** recovery, **not** ingress/auth, and **not** S1 append.
- **Ingress, Authentication & CLI/API Trigger Boundary Charter: RATIFIED.**
- **Live S1 DB production path: NOT CREATED.** **S1 append: DENIED.** **Production S1 stream:
  BLOCKED.** **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `8ac24d1a440c0f78252701f3c890c276e5dd5106`.
- Parent chain:
  - `8ac24d1a440c0f78252701f3c890c276e5dd5106` = **RATIFIED** Ingress, Authentication & CLI/API
    Trigger Boundary Charter (named this Schema/Journal Unification as a PRODUCTION BLOCKER).
  - `7a9260c6204ced07aa1648a160625d0dc7f0bb1c` = **RATIFIED** Production S1 Append Execution
    Wiring/Circuit runtime slice (isolated test/temp scope).
  - `1514ca847c98127a9448e05d045f7a666c28ccba` = **RATIFIED** Production S1 Append Execution
    Wiring/Circuit Boundary Charter.
  - `cd9027a0b4ef4fa5e4a368790a436a0a56a89f1d` = **RATIFIED** Live S1 DB Initialization & Schema
    Provisioning runtime slice.
  - `d15f908396143768f1024a38385d2845cd7bff66` = **RATIFIED** S1 DB Recovery Protocol Boundary
    Charter.
- This charter defines the **Schema & Journal Unification** boundary. It does **not** supersede,
  relax, or accelerate any prior gate. It is itself a **PRODUCTION BLOCKER** until resolved.

## Section 2 — Charter Intent

- Two ratified slices were built independently and disagree on the two facts that matter most for a
  durable append store: the **table name** (`s1_appends` vs `s1_append_log`) and the **journal mode**
  (WAL vs rollback). The circuit currently verifies the initializer's `s1_appends` container and then
  delegates the append to the writer's `s1_append_log` — coherent **only** in a throwaway test
  container, never for a single durable production append target.
- This charter draws the line for the **future refactor** that unifies them: it pins what must be
  chosen (one table, one journal mode), what must be preserved (every existing safety invariant), and
  what must never happen (silent migration, dual-write, shadow-write, compatibility shims) — without
  performing any of it.
- It exists to make **"design unified ⇒ activate production"** drift **structurally impossible**: a
  unified design is a **precondition for** — never an **authorization of** — DB creation, append,
  stream, or trading.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only / No Authority / No Auto-Activation

1. This charter authorizes **no** runtime behavior and **performs no refactor / migration / DB op**.
2. It creates / opens-for-write / modifies / repairs / deletes **no** DB / WAL / SHM / journal / lock
   artifact.
3. It does **not** execute the circuit, initializer, or writer; performs **no** append; starts **no**
   stream.
4. It does **not** create trading, paper, canary, live, wallet, signing, capital, or capacity
   authority.
5. **No auto-activation.** Any future unification refactor must be **separately and explicitly
   user-authorized** and must never be triggered by import, scheduler, hook, callback, queue, worker,
   observer, stream, or ingress.

### Gate B — Seam Status: UNSTARTED / PRODUCTION BLOCKER

1. The schema/journal unification is **UNSTARTED** and is a **PRODUCTION BLOCKER**.
2. The **circuit runtime remains RATIFIED only in isolated test/temp scope**; it is **not**
   production-activatable while the seam is split.
3. **No ingress / auth / CLI / API trigger may connect to a live circuit** until this unification is
   **implemented and ratified**.
4. Until resolution, every production-activation path is **fail-closed** (Gate H).

### Gate C — One Canonical Live Table (no dual-table production append)

1. Exactly **one canonical live S1 append table** must be selected for production.
2. **No dual-table production append.** The production circuit may not verify one table and append to
   another.
3. **Dual-write / shadow-write is forbidden** in production (Gate G).
4. The table choice must be documented with **explicit risk tradeoffs** (Section 4) before
   ratification; no silent default.

### Gate D — One Canonical Journal Mode (no WAL-vs-rollback split)

1. Exactly **one canonical journal mode** must be selected for production.
2. **No WAL-vs-rollback split** across initializer and writer.
3. The **existing ratified `journal_mode=WAL` and `synchronous=FULL` floor is the current minimum**
   and must not be relaxed unless a **separate ratified change** explicitly upgrades it (e.g. EXTRA +
   directory fsync).
4. The chosen journal mode must be **read back and verified** wherever it is provisioned or
   inspected; assumed pragmas are forbidden.

### Gate E — Invariants the Refactor MUST Preserve

The future refactor must preserve **all** of:

1. **append-only semantics**;
2. **`UNIQUE(evidence_digest, s1_target)`**;
3. **BEFORE UPDATE / DELETE abort triggers** (or equivalent immutable enforcement);
4. **idempotency** (one `evidence_digest` + one `s1_target` ⇒ at most one append);
5. **atomic-or-fail-closed** transaction semantics;
6. **single-flight / TOCTOU protection**;
7. **zero production authority flags** on every result.

Dropping or weakening any invariant **fails closed** and is **not** ratifiable.

### Gate F — No Silent DB Lifecycle Operations

1. The future refactor must **not silently migrate, rename, copy, delete, checkpoint, vacuum, or
   repair** any live DB.
2. Any data-bearing lifecycle operation, if ever needed, requires its **own separate explicit
   authorization** and preservation-first handling (recovery remains separate — Gate I).
3. The refactor operates on **test/temp DBs only** until **separately authorized production
   provisioning** exists (Gate B / Gate H).

### Gate G — Forbidden Compatibility Patterns

1. **Dual-write is forbidden** in production.
2. **Shadow-write is forbidden** in production.
3. **Compatibility shims that write BOTH `s1_appends` and `s1_append_log` are forbidden.**
4. **Cross-table mirroring, triggers that copy rows between tables, and "write here, also write
   there" patterns are forbidden.**
5. The unified design is a **single canonical write path**, not a bridge between two.

### Gate H — Pre-Unification Fail-Closed

1. Any **existing live DB or suspect DB state** encountered before unification **fails closed**.
2. Every production-activation attempt before unification-ratification **fails closed**.
3. Live DB creation, S1 append, production stream, ingress/auth trigger, and trading/capacity each
   remain **separately blocked** and are **not** implied by a unified design.

### Gate I — Separation of Concerns

1. **Recovery remains separate.** Unification is **not** recovery; suspect/`BLOCKED_RECOVERY_REQUIRED`
   handling stays in the ratified S1 DB Recovery Protocol Boundary Charter.
2. **Ingress/auth remains separate.** Unification is **not** external-trigger authorization.
3. **Production append remains separate.** Unification is **not** S1 append authorization.
4. A unified schema/journal is a **precondition**, never a grant.

### Gate J — Deterministic Fingerprints & Circuit Rejection

1. The future unified design must define a **deterministic schema fingerprint** and a **deterministic
   journal-mode fingerprint**.
2. The circuit must **reject** any DB whose schema fingerprint or journal-mode fingerprint does **not
   match** the unified fingerprint.
3. **Writer and initializer must agree** on: table name, schema version, `PRAGMA journal_mode`,
   `synchronous` policy, triggers, indexes, and row-count expectations.
4. Any divergence between the two on any of these **fails closed**.

### Gate K — Fail-Closed Conditions (at least forty-five)

The following must **fail closed** (default = **no unification activation, no production op**):

1. seam unresolved (UNSTARTED);
2. unification not ratified;
3. dual-table production append;
4. dual-write attempted;
5. shadow-write attempted;
6. compatibility shim writing both tables;
7. cross-table mirroring trigger;
8. two journal modes across init/writer;
9. WAL-vs-rollback split unresolved;
10. `journal_mode` below ratified WAL minimum without ratified upgrade;
11. `synchronous` below FULL floor;
12. pragma assumed, not read back;
13. table name disagreement (init vs writer);
14. schema version disagreement;
15. trigger set disagreement;
16. index set disagreement;
17. UNIQUE(evidence_digest, s1_target) missing/changed;
18. append-only enforcement missing/changed;
19. row-count expectation disagreement;
20. schema fingerprint mismatch;
21. journal-mode fingerprint mismatch;
22. circuit not rejecting a non-matching fingerprint;
23. idempotency weakened;
24. atomic-or-fail-closed weakened;
25. single-flight / TOCTOU protection weakened;
26. any production authority flag set true;
27. silent migrate;
28. silent rename;
29. silent copy;
30. silent delete;
31. silent checkpoint;
32. silent vacuum;
33. silent repair;
34. operating on a live (non-test) DB before authorized provisioning;
35. existing live DB reused/overwritten blindly;
36. suspect DB state before unification;
37. recovery folded into unification;
38. ingress/auth folded into unification;
39. production append folded into unification;
40. production stream folded into unification;
41. table chosen without documented risk tradeoffs;
42. dependency/framework added;
43. CLI/API/network/socket introduced;
44. capacity inferred non-zero;
45. trade/order inferred;
46. execution token created;
47. unified design treated as append authorization.

The default in **every** degraded, ambiguous, or unverified state is the **safe / no-activation /
blocked** outcome.

### Gate L — Required Future Unification Refactor Command Shape (unification only)

Any future schema+journal unification runtime / TDD refactor command must:

- be **separately and explicitly authorized by the user** (Gemini verdict ≠ command; Claude output ≠
  command);
- start from an **exact SHA**;
- be **RED first** (watch the unified-fingerprint / agreement tests fail before any code);
- be scoped to **schema + journal unification only** — **no** DB migration of live data, **no**
  append, **no** stream, **no** ingress/auth, **no** trading/capacity;
- operate on **test/temp DBs only** until a separate ratified production-provisioning authorization;
- include **targeted tests** for: single canonical table, single canonical journal mode,
  WAL+`synchronous=FULL` floor preserved, append-only triggers, `UNIQUE(evidence_digest, s1_target)`,
  idempotency, atomic-or-fail-closed, single-flight/TOCTOU, deterministic schema fingerprint,
  deterministic journal-mode fingerprint, circuit-rejects-non-matching-fingerprint, init/writer
  agreement on every field, no-dual-write, no-shadow-write, no-silent-lifecycle-op, and no-authority
  output;
- introduce **no** dependency/framework;
- **run the full approval suite**;
- **preserve S1 append DENIED**, production stream BLOCKED, capacity 0, and Live S1 DB production path
  NOT CREATED;
- create **no** trading / order / capacity / wallet / paper / live / canary authority.

This section grants **no** current authority; absent such a command, **no unification is implemented,
migrated, or activated.**

---

## Section 4 — Canonical Choice Risk-Tradeoff Ledger (template, to be completed later)

No production table/journal is selected now. A future unification charter / implementation must
document the choice with **explicit risk tradeoffs** (documentation-only here; every entry is a future
requirement, never an authorization):

| Option | Pro | Con / Risk | Decision | Status |
|--------|-----|------------|----------|--------|
| canonical table = `s1_appends` | matches initializer-provisioned, locked, WAL container; carries `created_at_utc` | writer currently targets `s1_append_log`; requires writer refactor | UNDECIDED | BLOCKED |
| canonical table = `s1_append_log` | matches writer's existing append path + `result_digest` | initializer currently provisions `s1_appends`; requires initializer refactor; rollback-journal default | UNDECIDED | BLOCKED |
| canonical journal = WAL | concurrent readers + 1 writer; matches initializer + ratified floor | requires writer to stop forcing rollback (DELETE) | UNDECIDED | BLOCKED |
| canonical journal = rollback (DELETE) | matches writer's current behavior | loses WAL concurrency; conflicts with ratified WAL floor | UNDECIDED | BLOCKED |
| synchronous floor = FULL (current) | ratified minimum durability | EXTRA + dir fsync is stricter, needs separate ratification | KEEP FLOOR | BLOCKED |
| dual-write / shadow-write / both-table shim | (none) | explicitly FORBIDDEN (Gate G) | FORBIDDEN | BLOCKED |

Every row is **UNDECIDED / BLOCKED / FORBIDDEN** until a separate ratified unification; a documented
choice does not auto-enable production provisioning, append, stream, or capacity.

## Section 5 — Non-Authority Rules

Future systems must prove:

- **unified design ≠ append authority.**
- **unification ≠ recovery.**
- **unification ≠ ingress/auth authorization.**
- **unification ≠ S1 append authorization.**
- **schema fingerprint match ≠ authority.**
- **journal fingerprint match ≠ authority.**
- **init/writer agreement ≠ authority.**
- **`APPEND_RECORDED_IN_TEST_CONTAINER` ≠ `PRODUCTION_APPEND_AUTHORIZED`.**
- **docs charter ≠ authority.**
- **Gemini verdict ≠ operator command.**
- **Claude output ≠ operator command.**
- **no S1 append. no production stream. no DB creation/modification. no trade / order / execute.
  no paper / canary / live. no wallet / signing / capital. no capacity. no execution token.**

## Section 6 — Next Gates

Only next safe gates:

1. Independent review of this Schema & Journal Unification Boundary Charter.
2. Only under a **separate, explicitly user-authorized command of the Section L shape**: a future
   schema+journal unification refactor slice (RED-first, fail-closed, test/temp only, single canonical
   table + journal, all invariants preserved, no dual/shadow write, no trading/capacity authority).
3. After unification is **implemented and ratified**, the **separately** ratified gates for live DB
   provisioning, production append, ingress/auth, and production stream remain individually required.
4. No artifact — unified design, fingerprint match, init/writer agreement, circuit, or test container
   — auto-enables a DB creation, S1 append, production stream, paper, live, trading, or capacity.

## Post-state

- Schema & Journal Unification Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- Ingress, Authentication & CLI/API Trigger Boundary Charter: **RATIFIED**.
- Production S1 Append Execution Wiring/Circuit runtime slice: **RATIFIED**.
- Production S1 Append Execution Wiring/Circuit Boundary Charter: **RATIFIED**.
- Live S1 DB Initialization & Schema Provisioning runtime slice: **RATIFIED**.
- S1 DB Recovery Protocol Boundary Charter: **RATIFIED**.
- Schema/Journal Unification runtime/refactor: **UNSTARTED / PRODUCTION BLOCKER**.
- Live S1 DB production path: **NOT CREATED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Paper / canary / live / trading / actionability: **BLOCKED**.
- Wallet / signing / capital authority: **BLOCKED**.
- Capacity: **0**.
