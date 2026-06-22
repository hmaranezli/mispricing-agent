# Phase 6.2 — Slice-E Atomic-Replay-Step Result / Publication / Input / Error Exact-Shape Charter

> **This is a docs-only field-shape / API charter.** It ratifies the **previously-deferred concrete Slice-E API
> decisions** — the exact public callable, the result carrier, identity/publication semantics, the opaque raw-row
> input rule, the mandatory manifest input, and the closed error surface — that the atomicity / planning chain left
> as "deferred to the slice charters." It **implements nothing and authorizes nothing executable**: no runtime code,
> no tests, no fixtures, no `atomic_replay_step.py`, no `reconstruction.py`, no stale-lock edits, no prior-charter
> edits, no generated files, no pytest, no graphify, and no commit beyond this single docs file. It defines **no Step
> algorithm behavior** beyond the API/publication/input/error boundaries below; all precedence, duplicate primacy,
> strict-lazy privacy, classify-all/apply-all atomicity, terminal absorption, lifecycle legality, determinism, and
> passive-only exclusions of the ratified chain are **preserved unchanged**. It is subordinate to that chain — the
> reconstruction-runtime planning charter (`457d279`), the replay-step atomicity / row-start-snapshot / terminal-
> relevance charter (`457d279`), the predicate-precedence / decimal-source / evidence-consistency charter
> (`d7204d6`→`457d279`), the duplicate-root-guard / context-first charter (`44791ce`), the lifecycle charter
> (`e9995e7`), the multi-event context charter (`999a109`), the hypothetical-window-duration charter (`e471f19`),
> the Gate A/B charters (`5dc757c`, `1071067`, `474cc6f`), the evidence-intersection predicate charter (`d7204d6`),
> the sealed Slice-A lifecycle-slot / dual-snapshot field-shape chain (`85de568`→`38eccce`→`9fc7749`→`01331ec`), and
> `CLAUDE.md` — and where any conflict arises, those govern **except** for the concrete API decisions this charter is
> expressly authorized to ratify (§3–§10).

**Base:** `2f2990a98b88f13d618ae22cbacbe3b7c523337c`

---

## 1. Base / Purpose / Ratification Status

**Base commit:** `2f2990a98b88f13d618ae22cbacbe3b7c523337c`.

The Slice-E pre-flight decision gate found that the success **return/publication shape**, the **no-op identity/
equality semantics**, and the exact **`CurrentS1Row` input type** were never pinned: the atomicity charter (`457d279`
§3) describes the step only as the mathematical pair `Step(...) → HardFailure | (NextShadowSnapshot,
NextSeenTargetPairs)`, and the planning (`457d279` §9) and atomicity (`457d279` §9) charters **explicitly defer**
"concrete error-aggregation/exception types … to the slice charters." This charter closes exactly those deferred
API/publication/input/error boundaries — and nothing else.

**Slice E remains BLOCKED until this charter is independently reviewed and ratified.** Slice F/G remain blocked.
Capacity remains 0. Phase 6.2 remains INCOMPLETE and NOT runtime-ready; execution / routing / actionability / live /
paper / canary behavior remain forbidden.

---

## 2. Source-Anchoring Map (binding)

| Decision | Ratified anchor | This charter |
|---|---|---|
| Input roles `RowStartShadowSnapshot`, `RowStartSeenTargetPairs`, `CurrentS1Row`, `FrozenManifestProjection` | atomicity `457d279` §3 | mapped to exact parameters (§3) |
| `ShadowLifecycleSnapshot` / `SeenTargetPairsSnapshot` value types | Slice-A `85de568`→`01331ec` (implemented, `2f2990a`) | the next-state field types (§3–§5) |
| `FrozenManifestProjection` concrete type | Slice-B `verify_artifact` returns the Slice-A `ShadowIntentDefinitionArtifact` (`artifact_verifier.py`); Gate A `5dc757c`/`1071067` | §7 — concrete type is exactly `ShadowIntentDefinitionArtifact` |
| Strict-lazy, field-private S1 projection ops | Slice-C `s1_evidence_projection.py` (`project_silver_pair`, `project_observation_kind`, `project_score_family`, `project_score_context`, `project_score_timestamp`, `project_score_unit`, `project_score_magnitude`; `S1EvidenceProjectionError`) | §6 — raw row passed only to these |
| Pure classifiers | Slice-D `classification_predicates.py` (`silver_pair_intersects`, `context_equals`, `classify_timestamp_window`, `unit_comparable`, `classify_directional_crossing`; `ClassificationPredicateError`) | §8/§9 — never re-implemented |
| Success shape / no-op identity / error type | **deferred** by `457d279` §9 (planning) and `457d279` §9 (atomicity) | **ratified here** (§4–§10) |
| Precedence a–j; per-row order A–J; terminal relevance; duplicate primacy; atomicity | precedence `457d279` §4; atomicity `457d279` §7/§8; `44791ce` | **preserved** (§15) |

---

## 3. Exact Public Callable (binding)

```python
execute_atomic_replay_step(
    *,
    current_lifecycle_snapshot: ShadowLifecycleSnapshot,
    current_seen_pairs: SeenTargetPairsSnapshot,
    raw_evidence_row: object,
    frozen_manifest_projection: FrozenManifestProjection,
) -> AtomicReplayStepResult
```

- **All four parameters are mandatory and keyword-only.** Positional, missing, extra, or misnamed arguments are
  **invalid** and are rejected by the keyword-only signature itself (Python raises `TypeError` at argument binding —
  this is the call-binding contract, distinct from a contract-invalid **input value**, §10).
- **No alternative callable name, parameter name, or arity is legal.** The exact callable name is
  `execute_atomic_replay_step`; the exact parameter names are `current_lifecycle_snapshot`, `current_seen_pairs`,
  `raw_evidence_row`, `frozen_manifest_projection`.
- `current_lifecycle_snapshot` fills the `RowStartShadowSnapshot` role; `current_seen_pairs` fills the
  `RowStartSeenTargetPairs` role; `raw_evidence_row` fills the `CurrentS1Row` role; `frozen_manifest_projection`
  fills the `FrozenManifestProjection` role. **`RowStart*` / `Next*` are semantic roles, never class or parameter
  aliases.**
- The callable returns **exactly one** `AtomicReplayStepResult` on success, or raises **exactly one**
  `AtomicReplayStepError` on any contract failure (§8). **There is no third outcome, no `None`, no sentinel, no
  partial publication.**

---

## 4. `AtomicReplayStepResult` — Exact Shape (binding)

A **Slice-E-owned** carrier:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class AtomicReplayStepResult:
    next_lifecycle_snapshot: ShadowLifecycleSnapshot
    next_seen_target_pairs: SeenTargetPairsSnapshot
```

- `frozen=True, slots=True, kw_only=True`; **methodless except `__post_init__`** and the generated dataclass dunders.
- **Directly constructible by keyword only; there is no factory** (this is the one Slice-E carrier that is *not*
  factory-only — it is built directly by the Step at the single atomic publication point).
- **Exact ordered fields, exactly two:** (1) `next_lifecycle_snapshot: ShadowLifecycleSnapshot`, (2)
  `next_seen_target_pairs: SeenTargetPairsSnapshot`.
- **No `tuple`, `dict`, alias, `Optional`, third field, error/diagnostic field, or any alternative result
  representation is legal.** The mathematical pair `(NextShadowSnapshot, NextSeenTargetPairs)` of `457d279` §3 is
  ratified **as this two-field carrier**, not as a bare tuple.
- **`__post_init__` defensively revalidates** both fields: exact carrier type (`ShadowLifecycleSnapshot` /
  `SeenTargetPairsSnapshot`), populated **and** missing-slot `object.__new__` forgeries, the exact stored
  representation (`MappingProxyType` `slots_by_identity` / `frozenset` `seen_target_pairs`), every nested key/slot,
  and every complete invariant — surfacing **all** failures through the closed Slice-E error surface
  `AtomicReplayStepError` (§8), reusing the sealed Slice-A revalidators (never re-implementing them) and the
  guarded `_slot_value` discipline (no raw `AttributeError`).
- **Identity rules (§5) are Step postconditions, NOT `AtomicReplayStepResult` constructor invariants:** the
  constructor cannot see the inputs and therefore does not (and must not) enforce identity preservation; it enforces
  only structural validity of the two snapshot fields.

---

## 5. Identity / Publication Semantics (binding — Step postconditions)

- **Every successful Step call allocates a fresh `AtomicReplayStepResult`** (the result object is always newly
  constructed, even for a pure no-op).
- **A true no-op returns both original snapshot references by identity:** `result.next_lifecycle_snapshot is
  current_lifecycle_snapshot` **and** `result.next_seen_target_pairs is current_seen_pairs`.
- **For a partially-changing transition, every unchanged snapshot component preserves input object identity**
  (`is`), and **every changed component is a fresh factory-built Slice-A snapshot** (`make_shadow_lifecycle_snapshot`
  / `make_seen_target_pairs_snapshot`).
- **Failure publishes no `AtomicReplayStepResult` and no next snapshot** — the call raises `AtomicReplayStepError`;
  there is never a partial or apparently-successful result on failure (atomicity `457d279` §3/§4).
- **Inputs are never mutated.** `current_lifecycle_snapshot`, `current_seen_pairs`, the raw row, and the manifest
  projection are immutable for the call and identical (by `is` and by value) afterward.
- **Determinism:** identical inputs produce a result whose snapshot components are equal by content and follow the
  identical identity pattern every time (no clock, no randomness, no global/iteration-order dependence).

### 5.1 No-op / partial-change identity truth table

| Scenario (precedence-classified) | `next_lifecycle_snapshot` | `next_seen_target_pairs` | result |
|---|---|---|---|
| terminal-absorption self-loop (row-start slot `INTENT_EXPIRED`/`INTENT_RETIRED`) | **identity** (input) | **identity** (input) | fresh |
| irrelevant non-targeted row, no established non-terminal slot needs it | **identity** | **identity** | fresh |
| well-formed context **inequality** (no-op) | **identity** | **identity** | fresh |
| in-window directional **unit mismatch** (no crossing) | **identity** | **identity** | fresh |
| `INERT_STATE` in-window (no crossing) | **identity** | **identity** | fresh |
| negative-delta passive non-comparability | **identity** | **identity** | fresh |
| sustaining `HYPOTHETICAL_CONDITION_MET` (no transition) | **identity** | **identity** | fresh |
| **first-target establishment** (`AUDIT_REPLAYED→INTENT_RECORDED`) | **fresh** (slot added) | **fresh** (pair added) | fresh |
| valid **root unit-mismatch** (permanent `AUDIT_REPLAYED`, non-established, pair committed) | **fresh** (slot added) | **fresh** (pair added) | fresh |
| later-row transition of an existing slot (`INTENT_RECORDED→HYPOTHETICAL_CONDITION_MET` crossing, or `→INTENT_EXPIRED` expiry) | **fresh** (slot updated) | **identity** (no new target) | fresh |

---

## 6. `raw_evidence_row` — Opaque Object (binding)

- `raw_evidence_row` is an **opaque object**. **Slice E never imports `sqlite3`** and **never** type-checks, indexes,
  iterates, parses, normalizes, copies, length-checks, key-enumerates, `repr`s, or otherwise **directly inspects**
  the row.
- The row is passed **only** to the existing ratified Slice-C strict-lazy projector operations
  (`project_silver_pair`, `project_observation_kind`, `project_score_family`, `project_score_context`,
  `project_score_timestamp`, `project_score_unit`, `project_score_magnitude`), **exactly when reached by
  precedence** (a–j) — each op inspects **only its own whitelisted field**.
- **Forbidden:** `project_row_envelope` (does not exist / removed in Slice C), whole-row validation, eager
  projection, pre-building all projections up front, and any direct column / item / attribute access on the row.
  Projections are invoked **lazily**, only at the precedence step that needs that field, and **never** speculatively.
- **Slice-C projection errors (`S1EvidenceProjectionError`) are normalized to `AtomicReplayStepError`
  (`STEP_EVIDENCE_PROJECTION_REJECTED`) only when the corresponding lazy operation is actually reached** — never
  pre-emptively, never for an unreached field.

---

## 7. `frozen_manifest_projection` — Mandatory (binding)

- `frozen_manifest_projection` is **mandatory**. Its concrete ratified type is the Slice-A
  `ShadowIntentDefinitionArtifact` (the factory-only, `MappingProxyType`-backed `definitions_by_silver_pair` keyed by
  exact `OpaqueSilverPairKey`) as produced by Slice-B `verify_artifact`. The `FrozenManifestProjection` annotation is
  the semantic role for that exact type; **no new manifest class/alias is minted**, and the consumer-boundary check
  is `type(frozen_manifest_projection) is ShadowIntentDefinitionArtifact` plus full member revalidation.
- It is mandatory **because** `exposure_orientation`, `passive_boundary_magnitude`, `boundary_unit_context`,
  `hypothetical_window_duration_ms`, and the definition identity remain **manifest-resident** and are **never**
  duplicated into lifecycle slots (Slice-A `85de568` §3 reconciliation; `999a109` §4). The Step reads them **only**
  from this projection, keyed by the same `OpaqueSilverPairKey`.
- Slice E **does not** re-verify bytes/digest (that is Slice-B's sealed responsibility); it **revalidates the carrier
  shape** at the consumer boundary (§8 `STEP_INVALID_MANIFEST_PROJECTION`).

---

## 8. `AtomicReplayStepError` & Closed Reason Vocabulary (binding)

**Exactly one** Slice-E error class:

```python
class AtomicReplayStepError(ValueError): ...   # carries one reason from the closed vocabulary below
```

Every contract failure surfaces as `AtomicReplayStepError` carrying **exactly one** reason string from this
**exhaustive, closed** table. There is **no** "e.g.", catch-all, optional reason, raw-message-only surface, or
unspecified failure category.

| # | Reason string | Failure site (mapped 1:1) | Source anchor |
|---|---|---|---|
| 1 | `STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT` | consumer-boundary revalidation of `current_lifecycle_snapshot`: not exact `ShadowLifecycleSnapshot`; populated forgery; **missing-slot** `object.__new__` forgery; wrong stored representation; bad nested key/slot; broken slot/snapshot invariant | Slice-A `85de568`/`01331ec`; atomicity §3 |
| 2 | `STEP_INVALID_CURRENT_SEEN_PAIRS` | consumer-boundary revalidation of `current_seen_pairs`: not exact `SeenTargetPairsSnapshot`; forged/missing-slot; non-`frozenset` representation; forged/non-key member | Slice-A `85de568`/`01331ec` |
| 3 | `STEP_INVALID_MANIFEST_PROJECTION` | consumer-boundary revalidation of `frozen_manifest_projection`: not exact `ShadowIntentDefinitionArtifact`; forged/missing-slot; bad nested key/definition; broken envelope invariant | Gate A `5dc757c`/`1071067`; §7 |
| 4 | `STEP_EVIDENCE_PROJECTION_REJECTED` | a **reached** Slice-C lazy projection raises `S1EvidenceProjectionError` (covers malformed silver-pair, observation-kind, **SCORE-family inconsistency**, **malformed/not-two-text context**, timestamp, unit, magnitude/Phase-5 lexis) — normalized only at the reached op | Slice-C; precedence §5/§10 |
| 5 | `STEP_CLASSIFICATION_PREDICATE_REJECTED` | a **reached** Slice-D predicate raises `ClassificationPredicateError` (invalid input to `silver_pair_intersects`, `context_equals`, `classify_timestamp_window`, `unit_comparable`, `classify_directional_crossing`) | Slice-D; precedence §4 |
| 6 | `STEP_MANIFEST_DEFINITION_ABSENT` | `KeyError` normalized **only** at the contract-guaranteed manifest lookup `definitions_by_silver_pair[key]` for an established / row-start targeted key whose presence the contract guarantees | precedence §2(a)/§8; §10 |
| 7 | `STEP_DUPLICATE_ROOT` | a second in-stream occurrence of an already-established targeted Silver pair (duplicate-root hard fail-fast, before any terminal/inspection) | precedence §8; atomicity §8 A/B |
| 8 | `STEP_TARGETED_NON_SCORE_ROOT` | a targeted HALT / non-SCORE observation at an **unestablished** manifest key (hard fail-fast) | precedence §9; atomicity §8 C |
| 9 | `STEP_INVALID_LIFECYCLE_TRANSITION` | a computed transition is not in the closed legal table `e9995e7` §4 (defensive; never expected from correct classification) | lifecycle `e9995e7` §4 |
| 10 | `STEP_PUBLICATION_INVARIANT_VIOLATION` | the atomically-built next snapshot(s) fail their own publication invariants (key ≠ slot identity, duplicate key/member, lifecycle/root invariant) at the single publication point | Slice-A `85de568` §5; atomicity §4 |

**No other reason string exists.** SCORE-family inconsistency and malformed context are **not** separate Slice-E
reasons — they are Slice-C projection rejections folded into `STEP_EVIDENCE_PROJECTION_REJECTED`, so Slice E
**never re-implements** family/context/timestamp/unit/magnitude validation (no duplicated predicate/projection
logic). Well-formed context inequality, in-window unit mismatch, `INERT_STATE`, negative delta, and sustaining
conditions are **no-ops, not errors** (§5.1).

---

## 9. Error-Precedence Order (binding)

The reason that surfaces is the **first** failure encountered in this fixed, iteration-order-independent order
(atomicity `457d279` §8 A–J; precedence `457d279` §4 a–j):

1. **Consumer-boundary input revalidation**, in fixed parameter order: `STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT`
   → `STEP_INVALID_CURRENT_SEEN_PAIRS` → `STEP_INVALID_MANIFEST_PROJECTION` (all before any row logic).
2. **Row silver-pair projection** (`project_silver_pair`) → `STEP_EVIDENCE_PROJECTION_REJECTED`.
3. **Global target / duplicate guard** vs row-start seen-pairs → `STEP_DUPLICATE_ROOT` (immediate; precedes
   terminal handling and all later-observation inspection).
4. **First-target root path**: targeted HALT/non-SCORE at unestablished key → `STEP_TARGETED_NON_SCORE_ROOT`;
   contract-guaranteed manifest lookup → `STEP_MANIFEST_DEFINITION_ABSENT`; reached root SCORE projections →
   `STEP_EVIDENCE_PROJECTION_REJECTED`.
5. **Row-start established non-terminal relevance**: reached context/family/timestamp/unit/magnitude projections →
   `STEP_EVIDENCE_PROJECTION_REJECTED`; reached predicates → `STEP_CLASSIFICATION_PREDICATE_REJECTED` (expiry before
   unit/magnitude per precedence §4 g vs i/j).
6. **Transition legality** of any computed proposal → `STEP_INVALID_LIFECYCLE_TRANSITION`.
7. **Atomic publication** invariants → `STEP_PUBLICATION_INVARIANT_VIOLATION`.

Any failure discards all row proposals (classify-all/apply-all atomicity §4); the first reason in this order is
deterministic and independent of map iteration order.

---

## 10. Exception Discipline (binding)

- **`KeyError` is normalized to `AtomicReplayStepError` (`STEP_MANIFEST_DEFINITION_ABSENT`) ONLY at the one
  contract-defined mapping lookup** whose absence the contract governs (the manifest `definitions_by_silver_pair[key]`
  read for a key the contract guarantees present). Membership decisions (target vs non-target) use `in` and are
  **no-ops/branches, not `KeyError` sites**.
- **No raw `AttributeError`, `TypeError`, `ValueError`, `decimal.InvalidOperation`, `KeyError`, or foreign
  equality/hash exception may escape when it represents contract-invalid input** — each is normalized to the mapped
  reason (via the sealed Slice-A `_slot_value` guard, the Slice-C/Slice-D sealed error surfaces, and the §8 mapping).
- **The argument-binding `TypeError`** for positional/missing/extra/misnamed calls (§3) is the **keyword-only
  signature contract**, not a contract-invalid input value, and is *not* an `AtomicReplayStepError`.
- **`BaseException`, `MemoryError`, `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, and any unrelated fault are
  NEVER caught** — only the exact, narrowly-scoped exceptions named above at their exact sites, never a broad
  `except Exception`/`except BaseException`.

---

## 11. Legal / Illegal API Matrix (binding)

| Call | Outcome |
|---|---|
| all four valid keyword args | ✅ `AtomicReplayStepResult` (or mapped `AtomicReplayStepError`) |
| any positional argument | ❌ `TypeError` (signature contract) |
| missing any of the four | ❌ `TypeError` |
| extra / misnamed keyword | ❌ `TypeError` |
| `current_lifecycle_snapshot` not exact `ShadowLifecycleSnapshot` / forged / missing-slot | ❌ `AtomicReplayStepError(STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT)` |
| `current_seen_pairs` not exact `SeenTargetPairsSnapshot` / forged | ❌ `AtomicReplayStepError(STEP_INVALID_CURRENT_SEEN_PAIRS)` |
| `frozen_manifest_projection` not exact `ShadowIntentDefinitionArtifact` / forged | ❌ `AtomicReplayStepError(STEP_INVALID_MANIFEST_PROJECTION)` |
| `raw_evidence_row` malformed at a **reached** projection | ❌ `AtomicReplayStepError(STEP_EVIDENCE_PROJECTION_REJECTED)` |
| `raw_evidence_row` malformed only in an **unreached** field | ✅ unaffected (lazy: never inspected) |

## 12. Result-Construction Matrix (binding)

| Step classification | result fields built | identities (§5) |
|---|---|---|
| pure no-op | both fields = inputs | both `is` inputs; result fresh |
| establishment / unit-mismatch root | both fields rebuilt | both fresh; result fresh |
| later-row slot transition | lifecycle rebuilt, seen reused | lifecycle fresh, seen `is` input; result fresh |
| any hard failure | **no result** | raises `AtomicReplayStepError`; no publication |

---

## 13. Future RED → GREEN Requirements (for the later separately-authorized Slice-E TDD — NOT opened here)

The Slice-E implementation task (separately authorized) must prove, RED→GREEN, at least:

1. **Exact API:** keyword-only acceptance; positional/missing/extra/misnamed → `TypeError`; only the pinned callable/
   parameter/result/field names resolve; forbidden role aliases (`RowStartShadowSnapshot`, `NextShadowSnapshot`,
   `RowStartSeenTargetPairs`, `NextSeenTargetPairs`) and alternative result carriers/tuples do **not** resolve.
2. **`AtomicReplayStepResult`** exact two-field shape, frozen/slotted/kw-only/no-factory, `__post_init__` revalidation
   incl. populated **and** missing-slot forgeries of both snapshot fields.
3. **Complete consumer-forgery matrix** for every accepted input: all Slice-A lifecycle/root-evidence carriers; both
   row-start snapshots incl. nested keys/slots, `MappingProxyType`/`frozenset` representations, invariants, populated
   forgeries, and missing-slot `object.__new__` forgeries; the manifest projection and all nested entries — each →
   the mapped reason, no raw exception escaping.
4. **Precedence / non-inspection matrix:** duplicate-before-inspection privacy; strict-lazy field inspection (an
   unreached malformed field is never inspected); root/context establishment; timestamp-window classification; unit
   mismatch behavior; directional crossing; legal lifecycle transitions; terminal absorption; atomic publication.
5. **Identity/atomicity:** the §5.1 truth table; inputs unchanged; failure publishes nothing; repeated identical
   inputs deterministic.
6. **Error vocabulary:** every §8 reason reachable and 1:1; §9 precedence order; §10 `KeyError`-only-at-the-lookup
   and no-broad-catch discipline.
7. **AST locks:** (a) no direct unguarded carrier-slot reads at Slice-E trust boundaries (every carrier-field read
   via the guarded `_slot_value`); (b) no duplicated predicate/projection implementation (Slice-C/D are called, never
   re-coded); (c) no forbidden role aliases or alternative result carriers defined; (d) no `sqlite3` import, row
   loop, reconstruction/fold, persistence, clock, registry/cache, execution, routing, actionability, or capacity
   behavior.
8. The surgical **Slice-E/F → Slice-F-only** absence-lock rename (remove `atomic_replay_step.py` from the forbidden
   tuple, keep asserting `reconstruction.py` absent) — authorized only in that implementation task, not here.

---

## 14. Preserved Unchanged (affirmed)

All ratified behavior stands intact: classify-all/apply-all atomicity and the per-row order A–J (`457d279` §8);
duplicate-root primacy before terminal handling (`44791ce`/`457d279`); strict-lazy field privacy and the whitelist
(`d7204d6`/Slice-C); precedence a–j incl. expiry-before-unit/magnitude and the separate Phase-5/Gate-B decimal
contracts (`457d279` §4/§7); terminal absorption and at-most-one-terminal / open-frozen-EOF validity (`999a109`);
the legal lifecycle transition table (`e9995e7` §4); deterministic, idempotent, side-effect-free replay; manifest-
resident orientation/boundary/unit/duration; firewalled, transition-non-driving `HYPOTHETICAL_OUTCOME`; and all
no-wall-clock / no-S4 / no-mutation / no-global-state / no-actionability / no-capacity / no-integration provisions.
**This charter defines no Step implementation behavior beyond the API/publication/input/error boundaries above.**

---

## 15. Unresolved Items

- **None.** The exact callable, result carrier, identity/publication postconditions, opaque-row rule, mandatory
  manifest input, closed error vocabulary, and error precedence are all pinned and source-anchored. No tuple, dict,
  proposal object, alternative result carrier, alias, or identity is invented.

---

## 16. Exclusions / Precise Post-Charter State (ratified)

- Docs-only: no runtime/tests/fixtures/prior-charter/lock edits; `atomic_replay_step.py` and `reconstruction.py`
  not created; Slice F/G not opened.
- **Slice E remains BLOCKED until this charter is independently reviewed and ratified.** Slice F/G remain blocked.
  **Capacity remains 0.** **Phase 6.2 remains INCOMPLETE and NOT runtime-ready;** execution / routing / actionability
  / live / paper / canary behavior remain **forbidden.** Phase 6.1 frozen, COMPLETE + RATIFIED.

**Conclusion:** the previously-deferred Slice-E API is pinned (docs-only): the sole public callable
**`execute_atomic_replay_step(*, current_lifecycle_snapshot: ShadowLifecycleSnapshot, current_seen_pairs:
SeenTargetPairsSnapshot, raw_evidence_row: object, frozen_manifest_projection: FrozenManifestProjection) ->
AtomicReplayStepResult`** (four mandatory keyword-only args; no alternative names/arity); the success shape is the
Slice-E-owned frozen/slotted/kw-only, no-factory two-field **`AtomicReplayStepResult(next_lifecycle_snapshot,
next_seen_target_pairs)`** (no tuple/dict/alias/optional/third-field) whose `__post_init__` defensively revalidates
both snapshot carriers (incl. missing-slot forgeries) through the closed Slice-E surface; **identity/publication
postconditions** require a fresh result every success, both originals by identity on a true no-op, unchanged
components by identity and changed components freshly factory-built on partial change, **nothing** published on
failure, and never-mutated inputs; **`raw_evidence_row` is opaque** — never imported-as-sqlite3, type-checked,
indexed, iterated, parsed, copied, or directly inspected, passed **only** to the reached Slice-C strict-lazy
projectors (no `project_row_envelope`, no eager/whole-row projection, no direct column access), their
`S1EvidenceProjectionError` normalized only when reached; **`frozen_manifest_projection` is mandatory** (concrete
type the Slice-A `ShadowIntentDefinitionArtifact` from Slice-B `verify_artifact`) because orientation/boundary/unit/
duration/identity stay manifest-resident; and the closed **`AtomicReplayStepError`** carries exactly one of ten
mapped reasons (`STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT`, `STEP_INVALID_CURRENT_SEEN_PAIRS`,
`STEP_INVALID_MANIFEST_PROJECTION`, `STEP_EVIDENCE_PROJECTION_REJECTED`, `STEP_CLASSIFICATION_PREDICATE_REJECTED`,
`STEP_MANIFEST_DEFINITION_ABSENT`, `STEP_DUPLICATE_ROOT`, `STEP_TARGETED_NON_SCORE_ROOT`,
`STEP_INVALID_LIFECYCLE_TRANSITION`, `STEP_PUBLICATION_INVARIANT_VIOLATION`) under a fixed precedence, with
`KeyError` normalized **only** at the one contract-defined manifest lookup and **no** raw `AttributeError`/
`TypeError`/`ValueError`/`InvalidOperation`/`KeyError`/foreign-eq-hash escaping for contract-invalid input, while
`BaseException`/`MemoryError`/`KeyboardInterrupt`/`SystemExit`/`GeneratorExit`/unrelated faults are **never** caught.
All precedence/duplicate-primacy/strict-lazy-privacy/atomicity/terminal-absorption/lifecycle-legality/determinism/
passive-only provisions are **preserved**, and **no Step implementation behavior** is defined beyond these
boundaries. **Slice E stays BLOCKED pending independent review; Slice F/G blocked; capacity 0; Phase 6.2 INCOMPLETE
and NOT runtime-ready. No executable work is authorized.**
