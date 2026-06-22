# Phase 6.2 — Slice-F Reconstruction-Loop Exact-Shape Charter

> **This is a docs-only field-shape / API charter.** It pins the **previously-deferred concrete Slice-F
> reconstruction-fold decisions** — the exact public callable, its two mandatory keyword-only inputs, the exact
> validation order and literal `TypeError` messages, the empty / non-empty result semantics, the identity-pass-through
> rule, the K-based memory model (O(K) evolving payload, O(1) Slice-F overhead), the no-error-class /
> no-`try`/`except` exception discipline, and the
> superseding runtime dependency shape. It **implements nothing and authorizes nothing executable**: no runtime code,
> no tests, no fixtures, no `reconstruction.py`, no stale-lock edits, no prior-charter edits, no generated files, no
> pytest, no graphify, and no commit beyond this single docs file. It defines **no Step algorithm behavior** — the
> entire per-row classification, precedence, duplicate primacy, strict-lazy privacy, classify-all/apply-all atomicity,
> terminal absorption, lifecycle legality, manifest lookup, manifest revalidation, determinism, and closed-error
> surface of **Slice E** are **owned by Slice E and preserved unchanged**; Slice F only sequences. It is subordinate to
> the ratified chain — the Slice-E atomic-replay-step result/publication/input/error exact-shape charter (`cf73e3c`),
> the reconstruction-runtime TDD planning charter (`457d279`), the replay-step atomicity charter (`457d279`), the
> negative-evidence fixture-boundary charter, the predicate-precedence / decimal-source charter (`d7204d6`→`457d279`),
> the duplicate-root-guard / context-first charter (`44791ce`), the lifecycle charter (`e9995e7`), the multi-event
> context charter (`999a109`), the Gate A/B charters (`5dc757c`, `1071067`, `474cc6f`), the sealed Slice-A
> logical-model field-shape chain (`85de568`→`01331ec`), the sealed Slice-B `artifact_verifier.py`, the sealed Slice-C
> `s1_evidence_projection.py`, the sealed Slice-D `classification_predicates.py`, the sealed Slice-E
> `atomic_replay_step.py`, and `CLAUDE.md` — and where any conflict arises, those govern **except** for the concrete
> Slice-F fold decisions this charter is expressly authorized to pin (§3–§11).

**Base:** `cf73e3c7121a29877662a7be3cca4ca4788b4957`

---

## 1. Base / Purpose / Ratification Status

**Base commit:** `cf73e3c7121a29877662a7be3cca4ca4788b4957` (Slice E SEALED + RATIFIED).

The reconstruction-runtime planning charter (`457d279` §4/§5) named Slice F a **"minimal append-order fold over the
verified artifact projection + ordered S1 rows"** and **deferred** its concrete callable, input materialization,
result semantics, and exception discipline to the slice charter. This charter closes exactly those deferred
fold-boundary decisions — the exact public callable, the two mandatory keyword-only inputs, the literal validation
order and `TypeError` messages, empty/non-empty result semantics, the by-identity pass-through rule, the K-based
memory model (O(K) evolving payload, O(1) Slice-F overhead), the no-error-class exception discipline, and the
superseding runtime dependency shape — and
**nothing else**. It defines **no** per-row behavior: every classification decision belongs to the sealed Slice-E
`execute_atomic_replay_step`.

**Slice F runtime remains BLOCKED until this charter is independently reviewed and ratified.** Slice G remains
blocked. **Capacity remains 0.** **Phase 6.2 remains INCOMPLETE and NOT runtime-ready;** execution / routing /
actionability / live / paper / canary behavior remain **forbidden.** Phase 6.1 frozen, COMPLETE + RATIFIED.

---

## 2. Source-Anchoring Map (binding)

| Decision | Ratified anchor | This charter |
|---|---|---|
| "minimal append-order fold"; Slice F deps; excludes sort/filter/parallel/persist/export/source | planning `457d279` §4/§5 | exact callable + fold body (§3–§5); **superseded** dependency shape (§10) |
| `execute_atomic_replay_step` exact callable / result / closed error surface | Slice-E charter `cf73e3c`; `atomic_replay_step.py` | the only per-row step Slice F invokes (§4–§6) |
| `AtomicReplayStepResult` two-field frozen carrier | Slice-E charter `cf73e3c` §4 | the **unwrapped** Slice-F return type (§5) |
| `AtomicReplayStepError` closed ten-reason surface | Slice-E charter `cf73e3c` §8 | propagates unchanged through Slice F (§7) |
| `ShadowLifecycleSnapshot` / `SeenTargetPairsSnapshot` + factories `make_shadow_lifecycle_snapshot` / `make_seen_target_pairs_snapshot` | Slice-A `85de568`→`01331ec`; `logical_model.py` | the factory-fresh empty seed (§5/§10) |
| `ShadowIntentDefinitionArtifact` concrete manifest type | Slice-A `logical_model.py`; Slice-B `verify_artifact` | the exact-type input guard (§3); **Slice-B provenance is an external precondition** (§8) |
| append-order replay-row sequence | planning `457d279` §2; S1 `replay()` | the already-materialized ordered tuple (§3/§9) |
| `Step(RowStartShadowSnapshot, RowStartSeenTargetPairs, CurrentS1Row, FrozenManifestProjection)` law | atomicity `457d279` §3 | folded sequentially, snapshots threaded, artifact constant (§4–§5) |

---

## 3. Exact Public Callable (binding)

```python
def reconstruct_shadow_intent_state(
    *,
    ordered_replay_rows: tuple[object, ...],
    verified_manifest_artifact: ShadowIntentDefinitionArtifact,
) -> AtomicReplayStepResult
```

- **Both parameters are mandatory and keyword-only.** Positional, missing, extra, or misnamed arguments are
  **invalid** and are rejected by the keyword-only signature itself (Python raises `TypeError` at argument binding —
  this is the call-binding contract, distinct from the two contract-invalid **input-value** guards of §4).
- **No alternative callable name, parameter name, or arity is legal.** The exact callable name is
  `reconstruct_shadow_intent_state`; the exact parameter names are `ordered_replay_rows` and
  `verified_manifest_artifact`. No `*args`, no `**kwargs`, no defaults, no optional third parameter, no row iterator,
  no generator, no callback, no sink, no run/replay/loop/driver alias.
- `ordered_replay_rows` is an **already-materialized tuple of opaque rows in S1 append order**. Each element is an
  opaque `object` (the same opaque-row type Slice E receives as `raw_evidence_row`); Slice F treats the elements as
  **opaque and never inspects them** (§9).
- `verified_manifest_artifact` is the **exact** Slice-A `ShadowIntentDefinitionArtifact` produced by the sealed
  Slice-B `verify_artifact`. Slice F **does not** re-verify it (§8).
- **Domain-authored outcome surface (Slice-F-owned):** on success the callable returns an `AtomicReplayStepResult`
  (§5); on a row's contract failure it **propagates** the `AtomicReplayStepError` raised by Slice E (§7); and it raises
  one of the **two exact Slice-F `TypeError` input guards** (§4) for a non-exact-`tuple` rows argument or a
  non-exact-type artifact argument.
- The **Python argument-binding `TypeError`** (positional / missing / extra / misnamed call) belongs to the
  **keyword-only signature contract**, not to the domain-authored surface.
- **Factory / system exceptions, `BaseException`, and any unexpected fault remain OUTSIDE the closed domain surface**
  and **propagate unchanged** (§7); Slice F neither catches nor reclassifies them.
- **`None`, any sentinel, a wrapped error object, and any partial-success return remain FORBIDDEN.**

---

## 4. Exact Validation Order & Literal Guards (binding)

The body executes in **exactly** this fixed order before and during the fold:

1. **Tuple-exactness guard.** `type(ordered_replay_rows) is tuple` — exact `tuple`, not a subclass, not `list`, not a
   generator, iterator, or any other sequence. Otherwise raise native:

   ```python
   raise TypeError("ordered_replay_rows must be an exact tuple")
   ```

2. **Artifact-exactness guard.** `type(verified_manifest_artifact) is ShadowIntentDefinitionArtifact` — exact type,
   not a subclass, not a forgery-by-name, not a duck-typed look-alike. Otherwise raise native:

   ```python
   raise TypeError("verified_manifest_artifact must be an exact ShadowIntentDefinitionArtifact")
   ```

3. **Factory-fresh empty seed.** Construct the empty starting state via the sealed Slice-A factories — **never** by
   direct constructor, `object.__new__`, copy, or cached singleton:

   ```python
   current_lifecycle_snapshot = make_shadow_lifecycle_snapshot(slot_entries=())
   current_seen_pairs = make_seen_target_pairs_snapshot(members=())
   ```

4. **Sequential fold.** Iterate `ordered_replay_rows` **in tuple order, left to right**, calling
   `execute_atomic_replay_step` once per row, threading the carrier's two output snapshots into the next call's two
   input snapshots, and passing the **same** `verified_manifest_artifact` object on every call.

- **The two guards are the ONLY values Slice F may raise itself**, and both are native `TypeError` with **exactly** the
  literal messages above (no added prefix, suffix, reason code, or interpolation). The guard order is
  `ordered_replay_rows` **before** `verified_manifest_artifact`; this order is binding.
- `type(...) is ...` identity checks are mandatory; `isinstance` is **forbidden** for both guards (no subclass
  admission).

---

## 5. Fold Body, Result & Identity Semantics (binding)

The reference shape (illustrative of the pinned contract, not new behavior):

```python
def reconstruct_shadow_intent_state(*, ordered_replay_rows, verified_manifest_artifact):
    if type(ordered_replay_rows) is not tuple:
        raise TypeError("ordered_replay_rows must be an exact tuple")
    if type(verified_manifest_artifact) is not ShadowIntentDefinitionArtifact:
        raise TypeError("verified_manifest_artifact must be an exact ShadowIntentDefinitionArtifact")

    current_lifecycle_snapshot = make_shadow_lifecycle_snapshot(slot_entries=())
    current_seen_pairs = make_seen_target_pairs_snapshot(members=())
    result = None

    for raw_evidence_row in ordered_replay_rows:
        result = execute_atomic_replay_step(
            current_lifecycle_snapshot=current_lifecycle_snapshot,
            current_seen_pairs=current_seen_pairs,
            raw_evidence_row=raw_evidence_row,
            frozen_manifest_projection=verified_manifest_artifact,
        )
        current_lifecycle_snapshot = result.next_lifecycle_snapshot
        current_seen_pairs = result.next_seen_target_pairs

    if result is None:
        result = AtomicReplayStepResult(
            next_lifecycle_snapshot=current_lifecycle_snapshot,
            next_seen_target_pairs=current_seen_pairs,
        )
    return result
```

- **Empty replay (`ordered_replay_rows == ()`)** performs **zero** `execute_atomic_replay_step` calls and returns a
  **fresh** `AtomicReplayStepResult` whose two fields are the **factory-fresh empty** `ShadowLifecycleSnapshot` and
  `SeenTargetPairsSnapshot` seeded in §4 step 3. The empty result is a true empty reconstruction, never `None`, never a
  sentinel, never a tuple.
- **Non-empty replay** returns the **exact final `AtomicReplayStepResult` object produced by the last
  `execute_atomic_replay_step` call**, returned **without wrapping, re-boxing, copying, or reconstruction** — Slice F
  returns Slice E's carrier `is`-identical.
- **By-identity threading.** On each iteration, the next call's `current_lifecycle_snapshot` **is**
  `result.next_lifecycle_snapshot` and its `current_seen_pairs` **is** `result.next_seen_target_pairs` (Slice E's own
  §5 identity/publication postconditions are inherited unchanged: unchanged components preserve `is`, changed
  components are fresh factory-built snapshots). Slice F adds **no** snapshot allocation of its own beyond the single
  empty seed and (empty-replay only) the single empty carrier.
- **Each row is passed to Slice E by exact identity** (`raw_evidence_row is ordered_replay_rows[i]`), in tuple order,
  exactly once; **the same `verified_manifest_artifact` object is passed by identity on every call** (one shared
  constant, never copied, never re-projected, never re-keyed by Slice F).
- **Determinism / idempotency (relational identity).** Repeated identical
  `(ordered_replay_rows, verified_manifest_artifact)` inputs produce **content-equal** results and the **same
  within-execution relational-identity guarantees**. Within a single execution, the row/artifact pass-through identity
  (above) and unchanged-snapshot identity (Slice-E §5) are preserved; **changed snapshots and the seed/result objects
  follow the existing factory and Slice-E freshness contracts**. **No cross-execution object-identity equality is
  claimed** — distinct executions allocate distinct objects. The empty seeds and the empty-replay result carrier are
  **fresh per execution**, and **no cache or singleton is permitted**. Subject to that, re-executing the whole replay
  is a pure function of its two inputs (no clock, no randomness, no global or iteration-order dependence beyond the
  fixed tuple order).

---

## 6. Memory Model (binding)

Let **K** = the number of retained lifecycle-slot entries **plus** seen-target-pair members in the current
reconstruction state, and **N** = the number of rows in `ordered_replay_rows`.

- **Evolving output payload is O(K).** The threaded lifecycle/seen-pairs snapshots (and the result carrier wrapping
  them) grow with the retained slot-entry + seen-pair population, which is **worst-case O(N)** over N rows (every row
  could establish/retain state).
- **The materialized replay tuple is O(N)** — caller-supplied, fully materialized before the call.
- **Slice F adds only O(1) loop / reference / carrier overhead** beyond the input tuple and the evolving output
  payload: the loop variable, the two threaded snapshot references, and the latest result reference. It accumulates
  **no** per-row history, **no** growing list/dict/set, **no** buffer, **no** running log, and **no** index map.
- **No streaming and no globally bounded-memory claim is made.** The input is a fully-materialized tuple supplied by
  the caller; Slice F is **not** a streaming/lazy/generator pipeline and does not promise bounded memory over an
  unbounded source.

---

## 7. Exception Discipline (binding)

- **Slice F defines NO error class.** It introduces no `ReconstructionError`, no fold-level reason vocabulary, and no
  Slice-F exception type of any kind.
- **Slice F contains NO `try` / `except` / `finally` and NO `contextlib.suppress`.** It catches nothing, wraps nothing,
  normalizes nothing, and re-raises nothing.
- **`AtomicReplayStepError` propagates unchanged.** The first row whose step raises `AtomicReplayStepError` (any of the
  closed ten Slice-E reasons, §8 of `cf73e3c`) **terminates the fold immediately**; that exact exception escapes
  `reconstruct_shadow_intent_state` **unmodified** (same type, same `.reason`, same message, same traceback origin).
  **No partial reconstruction is published** — the call raises and returns nothing.
- **All factory/system exceptions propagate unchanged.** Any exception raised inside `make_shadow_lifecycle_snapshot`,
  `make_seen_target_pairs_snapshot`, `AtomicReplayStepResult.__post_init__`, or any sealed callee propagates verbatim;
  Slice F neither catches nor re-labels it.
- **The two §4 input guards are the ONLY exceptions Slice F itself raises**, both native `TypeError` with the exact
  literal messages. The argument-binding `TypeError` (positional/missing/extra/misnamed call) is the keyword-only
  **signature contract**, not a Slice-F-authored raise.
- **`BaseException`, `MemoryError`, `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, and any unrelated fault are
  NEVER caught** (there is no catch site at all).

---

## 8. Slice-B Provenance Boundary (binding)

- **`verified_manifest_artifact` provenance is an EXTERNAL precondition.** Trust in the artifact's canonical bytes /
  detached SHA-256 digest is established **exclusively** by the sealed Slice-B `verify_artifact` **before** Slice F is
  called. Slice F **never** invokes Slice-B verification, never reads bytes/digest, and never re-derives provenance.
- **Slice F's only manifest check is the §4 exact-type guard** (`type(...) is ShadowIntentDefinitionArtifact`). This is
  a shape/type gate, **not** a provenance gate.
- **Explicitly recorded limitation:** an **exact-type forged `ShadowIntentDefinitionArtifact`** (a structurally
  exact-type object that did **not** come from a genuine Slice-B verification) **passes Slice F's type guard and is NOT
  detected by Slice F** — most starkly on **empty replay**, where zero steps run and no manifest lookup or per-step
  manifest revalidation ever occurs, so a forged-but-exact-type artifact produces a clean empty result. Detecting such
  forgery is **out of Slice F's scope and is Slice B's sealed responsibility**; Slice F documents, and does not close,
  this boundary.
- On **non-empty** replay, per-step manifest revalidation and manifest lookup are performed by **Slice E** (`cf73e3c`
  §7/§8 — `STEP_INVALID_MANIFEST_PROJECTION`, `STEP_MANIFEST_DEFINITION_ABSENT`), **not** by Slice F.

---

## 9. Forbidden Row / Fold Operations (binding)

Slice F treats every element of `ordered_replay_rows` as **opaque** and the tuple's order as **authoritative**. The
following are **forbidden** in `reconstruction.py`:

- **Row inspection / parsing:** no type-check, attribute access, `__getitem__`, key/column read, `len`, `repr`,
  iteration *into* a row, normalization, decoding, or any direct inspection of a row's contents (the row is passed only
  to Slice E, which alone routes it to the sealed Slice-C projectors).
- **Reordering / selection:** no `sorted`, `sort`, `reversed`, `filter`, comprehension-with-condition, slicing for
  selection, or any reordering / skipping of rows; tuple order is preserved exactly.
- **Indexing:** no positional indexing / index arithmetic to drive the fold (iterate the tuple directly).
- **Deduplication:** no `set`, `dict`, `seen`-collection, or duplicate suppression (duplicate-root handling is Slice
  E's `STEP_DUPLICATE_ROOT`, not Slice F's).
- **Copying / buffering:** no `tuple(...)`, `list(...)`, `copy`/`deepcopy`, re-materialization, or staging buffer of the
  rows or snapshots.
- **History accumulation:** no per-row result list, running log, audit trail, counter map, or growing accumulator
  (only O(1) Slice-F overhead beyond the input tuple and the evolving output payload, §6).
- **Manifest lookup / projection:** no `definitions_by_silver_pair[...]` read, no manifest keying, no projection, no
  re-keying — manifest access is **exclusively** Slice E's.
- **Slice-B verification:** no canonical-byte / digest / provenance re-verification (§8).
- **Private revalidation calls:** no direct calls into Slice-A/B/C/D/E **private** revalidators, `_slot_value` guards,
  `__post_init__` internals, or any underscore-prefixed callee; Slice F uses **only** the public factories
  (`make_shadow_lifecycle_snapshot`, `make_seen_target_pairs_snapshot`) and the public step
  (`execute_atomic_replay_step`) and reads only the public result fields (`next_lifecycle_snapshot`,
  `next_seen_target_pairs`).
- **Runtime-purity bans (inherited, `457d279` §10):** no `sqlite3` import, file/network I/O, threads/async/
  multiprocessing, clock/timer, randomness, cache/singleton/module-level mutable state, persistence/export/reporting,
  execution/routing/actionability, or capacity/emission.

---

## 10. Superseded Runtime Dependency Shape (binding)

The planning charter (`457d279` §4 DAG) listed Slice F as
`reconstruction → atomic_replay_step, artifact_verifier, s1_evidence_projection, logical_model`. That **planning-time**
edge set is **superseded** for the **runtime** module by this charter:

```
reconstruction  →  atomic_replay_step, logical_model        (runtime imports ONLY)
```

- **`reconstruction.py` runtime imports are exactly two:** `atomic_replay_step` (for `execute_atomic_replay_step` and,
  for the empty-replay carrier, `AtomicReplayStepResult`) and `logical_model` (for the two snapshot factories and the
  `ShadowIntentDefinitionArtifact` type used by the §4 type guard).
- **`artifact_verifier` and `s1_evidence_projection` are OUTSIDE Slice-F runtime ownership.** Slice F does **not**
  import or call either: artifact verification (Slice B) is an external precondition (§8); S1 row projection (Slice C)
  is reached **only** transitively through Slice E, never directly by Slice F.
- This supersession narrows, and never widens, the dependency surface; the one-way acyclic DAG and no-shared-mutable-
  state rule of `457d279` §4 are preserved.

---

## 11. Empty / Non-Empty Result Matrix (binding)

| Input | Steps run | Returned `AtomicReplayStepResult` | `next_lifecycle_snapshot` | `next_seen_target_pairs` |
|---|---|---|---|---|
| `ordered_replay_rows == ()` | 0 | **fresh** carrier built by Slice F | factory-fresh **empty** `ShadowLifecycleSnapshot` (`is` the §4 seed) | factory-fresh **empty** `SeenTargetPairsSnapshot` (`is` the §4 seed) |
| exactly one row, success | 1 | **the** Slice-E carrier, unwrapped (`is` Step output) | per Slice-E §5 identity | per Slice-E §5 identity |
| N rows, all succeed | N | **the final** Slice-E carrier, unwrapped (`is` last Step output) | per Slice-E §5 identity at last row | per Slice-E §5 identity at last row |
| any row raises `AtomicReplayStepError` | up to + incl. failing row | **none** — exception propagates unchanged (§7); no partial result | — | — |
| `ordered_replay_rows` not exact `tuple` | 0 | **none** — `TypeError("ordered_replay_rows must be an exact tuple")` | — | — |
| `verified_manifest_artifact` not exact type | 0 | **none** — `TypeError("verified_manifest_artifact must be an exact ShadowIntentDefinitionArtifact")` | — | — |
| positional / missing / extra / misnamed arg | 0 | **none** — argument-binding `TypeError` (signature contract) | — | — |

---

## 12. Legal / Illegal API Matrix (binding)

| Call | Outcome |
|---|---|
| both valid keyword args, empty tuple | ✅ fresh empty `AtomicReplayStepResult` |
| both valid keyword args, non-empty tuple, all steps succeed | ✅ final Slice-E `AtomicReplayStepResult`, unwrapped |
| non-empty tuple, a step fails | ❌ `AtomicReplayStepError` propagates unchanged (no partial publication) |
| `ordered_replay_rows` is a `list` / generator / tuple subclass | ❌ `TypeError("ordered_replay_rows must be an exact tuple")` |
| `verified_manifest_artifact` wrong / forged-by-name / subclass | ❌ `TypeError("verified_manifest_artifact must be an exact ShadowIntentDefinitionArtifact")` |
| exact-type **forged** artifact, empty replay | ⚠️ ✅ clean empty result — **forgery NOT detected by Slice F** (§8; Slice-B responsibility) |
| any positional argument | ❌ `TypeError` (signature contract) |
| missing either arg / extra / misnamed keyword | ❌ `TypeError` (signature contract) |

---

## 13. Future RED → GREEN Requirements (for the later separately-authorized Slice-F TDD — NOT opened here)

The Slice-F implementation task (separately authorized) must prove, RED→GREEN, at least:

1. **Exact API:** keyword-only acceptance; positional/missing/extra/misnamed → `TypeError`; only the pinned callable
   name `reconstruct_shadow_intent_state` and the two parameter names resolve; no row-iterator/generator/callback/sink
   alias resolves.
2. **Guard order & literals:** `ordered_replay_rows` guard fires **before** the artifact guard; non-exact-`tuple`
   (incl. `list`, generator, tuple subclass) → exactly `TypeError("ordered_replay_rows must be an exact tuple")`;
   non-exact-type artifact (incl. subclass) → exactly
   `TypeError("verified_manifest_artifact must be an exact ShadowIntentDefinitionArtifact")`; both via `type(...) is`,
   never `isinstance`.
3. **Empty replay:** `()` → fresh `AtomicReplayStepResult` with factory-fresh empty snapshots; **zero**
   `execute_atomic_replay_step` calls (e.g. proven via a spy/seam that the step is never invoked); result is never
   `None`/sentinel/tuple.
4. **Non-empty pass-through:** single-row and N-row success returns the **last** Slice-E carrier `is`-identical (no
   wrapping/copy); snapshots threaded by identity between rows; the same `verified_manifest_artifact` object passed by
   identity on every call; each row passed by identity in tuple order exactly once.
5. **Order fidelity:** rows consumed strictly left-to-right; no sort/filter/dedup/reorder/skip (e.g. proven by an
   order-sensitive Slice-E seam recording the row sequence).
6. **Failure propagation:** a mid-replay `AtomicReplayStepError` escapes unchanged (type, `.reason`, message) and **no
   partial result** is returned; the fold stops at the failing row; Slice F contains no `try`/`except` (AST-asserted).
7. **No error class / no catch:** `reconstruction.py` defines no exception type and contains no `try`/`except`/
   `finally`/`suppress` (AST-asserted); the only Slice-F raises are the two native `TypeError` guards.
8. **Memory model:** only O(1) Slice-F loop/reference/carrier overhead beyond the O(N) input tuple and the O(K)
   (worst-case O(N)) evolving output payload — no per-row accumulator/buffer/history (AST-asserted absence of growing
   collections); no streaming / globally bounded-memory claim.
9. **Determinism / idempotency (relational identity):** repeated whole-replay execution of identical inputs yields
   **content-equal** results and the **same within-execution relational-identity guarantees** — within an execution,
   row/artifact pass-through identity and unchanged-snapshot identity are preserved, while changed snapshots and the
   seed/result objects follow the existing factory + Slice-E freshness contracts; **no cross-execution object-identity
   equality** is claimed; the empty seeds and the empty-replay result carrier are **fresh per execution**; **no cache
   or singleton** is permitted; no clock/random/global dependence.
10. **Dependency / purity AST locks:** runtime imports are **exactly** `atomic_replay_step` and `logical_model` (no
    `artifact_verifier`, no `s1_evidence_projection`, no `sqlite3`, no I/O, no clock, no threads, no cache/global, no
    persistence/export/execution/routing/actionability/capacity); no direct row inspection/indexing; no manifest
    lookup/projection; no Slice-B verification; no underscore-prefixed/private callee — only the public factories,
    public step, and public result fields.
11. **Absence-lock transition (singular ownership):** this docs task changes **no** locks. The **future Slice-F
    runtime/TDD task exclusively owns** the surgical relaxation of the two `test_slice_f_target_not_created`
    `reconstruction.py` absence assertions (currently `("reconstruction.py",)` in
    `tests/test_phase6_2_s1_evidence_projection.py` and `tests/test_phase6_2_classification_predicates.py`), performed
    **when `reconstruction.py` is created**, never in this docs task. **Slice G does NOT repeat or own that
    transition;** it owns only its own later closeout/integration locks.

---

## 14. Preserved Unchanged (affirmed)

All ratified behavior stands intact and is **owned by Slice E or earlier**, not redefined here: the exact
`execute_atomic_replay_step` callable / `AtomicReplayStepResult` carrier / closed `AtomicReplayStepError` ten-reason
surface (`cf73e3c`); per-row precedence a–j and classify-all/apply-all atomicity (`457d279` §4/§8); duplicate-root
primacy before terminal handling (`44791ce`/`457d279`); strict-lazy field privacy and the Slice-C whitelist
(`d7204d6`/Slice-C); terminal absorption and at-most-one-terminal / open-frozen-EOF validity (`999a109`); the legal
lifecycle transition table (`e9995e7` §4); manifest-resident orientation/boundary/unit/duration and Slice-E manifest
lookup/revalidation; deterministic, idempotent, side-effect-free replay; and all no-wall-clock / no-S4 / no-mutation /
no-global-state / no-actionability / no-capacity / no-integration provisions. **This charter defines no Step
implementation behavior beyond the fold/sequencing/input/result/exception boundaries above.** The negative-evidence
fixture-boundary charter governs which Slice-F success fixtures must be built through the ratified S1 adapter and which
negative branches remain gated.

---

## 15. Unresolved Items

- **Whole-replay success-fixture provenance (carried, not closed here):** Slice-F multi-row success tests must source
  their `ordered_replay_rows` through the ratified S1 adapter per the negative-evidence fixture-boundary charter (no
  hand-rolled successful rows, no intent-state fabrication). The exact fixture-construction recipe is owned by that
  fixture charter and the future Slice-F TDD task, **not** invented here.
- **Absence-lock relaxation ownership (recorded, not an open item):** the relaxation of the two
  `test_slice_f_target_not_created` `reconstruction.py` absence assertions is **owned exclusively by the future Slice-F
  runtime/TDD task** that creates `reconstruction.py` (§13.11) — **not** by Slice G. Slice G owns only its own later
  closeout/integration lock scope. This docs task changes no locks.
- **No other unresolved items.** The callable, the two keyword-only inputs, the literal guard order/messages, the
  empty/non-empty result semantics, the by-identity pass-through, the K-based memory model (O(K) evolving payload,
  O(1) Slice-F overhead), the no-error-class / no-`try`/`except` discipline, the Slice-B external-precondition
  boundary, and the superseded two-import dependency
  shape are all pinned and source-anchored. No wrapping carrier, fold-level error class, reordering, dedup, buffer, or
  manifest access is invented.

---

## 16. Exclusions / Precise Post-Charter State (ratified)

- Docs-only: no runtime/tests/fixtures/prior-charter/lock edits; `reconstruction.py` **not created**; Slice G not
  opened. The two existing Slice-F-only absence locks (`test_slice_f_target_not_created`, each asserting
  `("reconstruction.py",)` absent) are **kept unchanged**.
- **Slice F runtime remains BLOCKED until this charter is independently reviewed and ratified.** Slice G remains
  blocked. **Capacity remains 0.** **Phase 6.2 remains INCOMPLETE and NOT runtime-ready;** execution / routing /
  actionability / live / paper / canary behavior remain **forbidden.** Phase 6.1 frozen, COMPLETE + RATIFIED.

**Conclusion:** the previously-deferred Slice-F reconstruction fold is pinned (docs-only): the sole public callable
**`reconstruct_shadow_intent_state(*, ordered_replay_rows: tuple[object, ...], verified_manifest_artifact:
ShadowIntentDefinitionArtifact) -> AtomicReplayStepResult`** (two mandatory keyword-only args; no alternative
names/arity) validates in the exact order **(1)** `type(ordered_replay_rows) is tuple` else
`TypeError("ordered_replay_rows must be an exact tuple")`, **(2)** `type(verified_manifest_artifact) is
ShadowIntentDefinitionArtifact` else `TypeError("verified_manifest_artifact must be an exact
ShadowIntentDefinitionArtifact")`, **(3)** seeds factory-fresh empty `ShadowLifecycleSnapshot` /
`SeenTargetPairsSnapshot`, and **(4)** folds rows sequentially through `execute_atomic_replay_step`, preserving tuple
order and passing every row and the single `verified_manifest_artifact` to Slice E **by exact identity**. Slice F is
**DB-agnostic** and **forbids** row inspection, parsing, indexing, sorting, filtering, deduplication, copying,
buffering, history accumulation, manifest lookup, Slice-B verification, and private-revalidation calls; **manifest
lookup and per-step manifest revalidation remain exclusively Slice E's**. **Slice-B provenance is an external
precondition** — an exact-type forged artifact is **not detected by Slice F**, most starkly on empty replay.
Memory is the **O(N)** input tuple plus an **O(K) (worst-case O(N)) evolving output payload**, with Slice F adding
only **O(1)** loop/reference/carrier overhead and making **no streaming or globally bounded-memory claim**. **Empty
replay** returns a **fresh** `AtomicReplayStepResult` of fresh empty snapshots; **non-empty replay** returns the exact
final Slice-E `AtomicReplayStepResult` **unwrapped**. Slice F **defines no error class and contains no
`try`/`except`**: `AtomicReplayStepError` and all factory/system exceptions **propagate unchanged**, and only the two
exact input guards raise native `TypeError`. The old reconstruction dependency shape is **superseded** — runtime
imports are **only** `atomic_replay_step` and `logical_model`; `artifact_verifier` and `s1_evidence_projection` are
**outside** Slice-F runtime ownership. The two Slice-F-only absence locks stay unchanged. **Slice F runtime stays
BLOCKED pending independent review; Slice G blocked; capacity 0; Phase 6.2 INCOMPLETE and NOT runtime-ready. No
executable work is authorized.**
