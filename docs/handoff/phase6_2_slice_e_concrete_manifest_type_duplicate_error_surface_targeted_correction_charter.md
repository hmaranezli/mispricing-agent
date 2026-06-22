# Phase 6.2 — Slice-E Concrete-Manifest-Type / Duplicate-Semantics / Error-Surface Targeted Correction Charter

> **This is a docs-only targeted correction charter.** It marks the prior Slice-E exact-shape charter (`85d1ba6`)
> **historical and UNRATIFIED** and supersedes **only** the five exactness defects enumerated below; every other
> clause of `85d1ba6` stands intact. It **implements nothing and authorizes nothing executable**: no runtime code,
> no tests, no fixtures, no `atomic_replay_step.py`, no `reconstruction.py`, no lock edits, no prior-charter edits,
> no generated files, no pytest, no graphify, and no commit beyond this single docs file. It corrects `85d1ba6`
> **only** through the quote-anchored supersession map in §2. It defines **no Step algorithm behavior** beyond the
> corrected API/publication/input/error boundaries. It is subordinate to the full Phase 6.2 chain — the
> reconstruction-runtime planning charter (`457d279`), the replay-step atomicity charter (`457d279`), the
> predicate-precedence charter (`d7204d6`→`457d279`), the duplicate-root-guard / context-first charter (`44791ce`),
> the lifecycle charter (`e9995e7`), the multi-event context charter (`999a109`), the Gate A/B charters (`5dc757c`,
> `1071067`, `474cc6f`), the sealed Slice-A lifecycle-slot / dual-snapshot chain
> (`85de568`→`38eccce`→`9fc7749`→`01331ec`, runtime at `2f2990a`), the Slice-C `s1_evidence_projection.py` and
> Slice-D `classification_predicates.py` sealed surfaces, and `CLAUDE.md` — and where any conflict arises, those
> govern **except** for the narrow, explicitly-mapped corrections in §2.

**Base:** `85d1ba64866116d777c51d351843ac29b14c04ce`

---

## 1. Base / Purpose / Ratification Status

**Base commit:** `85d1ba64866116d777c51d351843ac29b14c04ce`.

`85d1ba6` pinned the Slice-E API but carried five exactness defects: (1) it annotated the manifest parameter with a
**nonexistent** type `FrozenManifestProjection`; (2) its manifest-lookup ownership prose risked reading as if Slice E
might receive one pre-resolved definition; (3) its `STEP_DUPLICATE_ROOT` description narrowed the duplicate to an
"already-established" target, contradicting the ratified guard that a **committed-seen** pair (incl. a permanent
unit-mismatch `AUDIT_REPLAYED`/`NoRootEvidence` pair) is a duplicate; (4) it left `AtomicReplayStepError` without the
established Slice-C/D constructor/`.reason` shape; (5) it did not pin which reason a direct
`AtomicReplayStepResult.__post_init__` revalidation failure maps to.

**`85d1ba6` is hereby marked historical and UNRATIFIED.** This correction supersedes **only** §3–§7 below; all other
`85d1ba6` clauses (the result two-field shape, identity/publication postconditions, opaque-row strict-lazy rule,
manifest-resident rationale, the ten-reason closed vocabulary set, error precedence, exception discipline, preserved
provisions) stand intact. `85d1ba6` is **not** edited/deleted/amended/rebased/force-pushed.

**No capacity validation and no capacity pass is claimed by this charter.**

---

## 2. Exact Quote-Anchored Supersession Map to `85d1ba6` (binding)

Each row supersedes **only** the quoted/identified clause; everything else in `85d1ba6` stands.

| `85d1ba6` site | Quoted/identified clause | Precise replacement |
|---|---|---|
| §3 signature; §2 anchor row; §8 reason #3; §11 API matrix; §13 future tests; §16 conclusion | `frozen_manifest_projection: FrozenManifestProjection` (and every `FrozenManifestProjection` used as a **type annotation / API symbol**) | `frozen_manifest_projection: ShadowIntentDefinitionArtifact` — the real runtime type (§3). The parameter name `frozen_manifest_projection` is preserved; `"FrozenManifestProjection"` survives **only** as a prose-level semantic role inherited from `457d279`. |
| §6/§8 reason #6 manifest-lookup prose | manifest lookup ownership (under-specified: could read as a pre-resolved definition) | **§4** — Slice E receives the **complete** `ShadowIntentDefinitionArtifact`; performs the single `M[key]` lookup itself; Slice F/G must not pre-resolve/inject one definition; `KeyError` normalized only at that exact site; membership is a branch/no-op. |
| §8 reason #7 row; §9 step 3; §12 matrix; §13 future tests | `STEP_DUPLICATE_ROOT` described/narrowed to a **second occurrence of an already-established** targeted pair | **§5** — applies whenever the current projected Silver pair **is a manifest target AND is already in `current_seen_pairs`**, independent of lifecycle/root/terminal/kind/later-fields, **including** a pair committed-seen after a valid permanent root unit-mismatch (`AUDIT_REPLAYED`+`NoRootEvidence`). Every "already-established" narrowing is removed. |
| §8 `AtomicReplayStepError` class declaration | `class AtomicReplayStepError(ValueError): ...   # carries one reason …` | **§6** — exact `__init__(self, reason, message)` with `self.reason`, matching the sealed Slice-C/D pattern. |
| §4 `AtomicReplayStepResult.__post_init__` revalidation | "surfacing **all** failures through the closed Slice-E error surface `AtomicReplayStepError`" (reason unspecified) | **§7** — a direct-construction revalidation failure maps to `AtomicReplayStepError(STEP_PUBLICATION_INVARIANT_VIOLATION, message)`; input-parameter validation stays mapped to the input reasons. |

All other `85d1ba6` provisions remain in force.

---

## 3. Concrete Manifest Type (binding)

In **every** exact Python signature, return/API matrix, conclusion, and future test requirement, the nonexistent
annotation `FrozenManifestProjection` is replaced with the **real runtime type** `ShadowIntentDefinitionArtifact`
(the Slice-A factory-only, `MappingProxyType`-backed artifact produced by Slice-B `verify_artifact`). The corrected
callable is exactly:

```python
execute_atomic_replay_step(
    *,
    current_lifecycle_snapshot: ShadowLifecycleSnapshot,
    current_seen_pairs: SeenTargetPairsSnapshot,
    raw_evidence_row: object,
    frozen_manifest_projection: ShadowIntentDefinitionArtifact,
) -> AtomicReplayStepResult
```

- The **parameter name `frozen_manifest_projection` is preserved.**
- `"FrozenManifestProjection"` is preserved **only as a prose-level semantic role** inherited from the planning /
  atomicity charters (`457d279`).
- **No `FrozenManifestProjection` class, alias, type alias, `Protocol`, `TypeVar`, or any runtime symbol may be
  created.** The consumer-boundary check is exactly `type(frozen_manifest_projection) is
  ShadowIntentDefinitionArtifact` plus full member revalidation; failure → `STEP_INVALID_MANIFEST_PROJECTION`.

---

## 4. Manifest-Lookup Ownership (binding)

- `STEP_MANIFEST_DEFINITION_ABSENT` **remains** in the closed ten-reason vocabulary (unchanged).
- **Slice E receives the complete `ShadowIntentDefinitionArtifact`**, whose `definitions_by_silver_pair` mapping
  contains **all** manifest definitions. **It does not receive one pre-resolved definition.**
- **Slice E performs the single contract-defined lookup site `M[key]`** (i.e.
  `frozen_manifest_projection.definitions_by_silver_pair[key]`) itself, because **root classification** and
  **one-row multi-intent classification** may require definitions for **multiple keys** within a single step.
- **Slice F/G MUST NOT pre-resolve or inject one definition into Slice E** — Slice E always holds the whole artifact
  and resolves per-key on demand.
- **`KeyError` is normalized to `AtomicReplayStepError(STEP_MANIFEST_DEFINITION_ABSENT, message)` only at this exact
  `M[key]` lookup site** (a key the contract guarantees present, e.g. re-reading the definition for a row-start /
  established targeted slot).
- **Membership checks remain branches / no-ops and are NOT `KeyError` sites** (target-vs-non-target is decided by
  `key in M`/Slice-D `silver_pair_intersects`; a non-target row is an irrelevant no-op, never an error).

**Lookup-ownership proof:** the artifact's `definitions_by_silver_pair` is the immutable `MappingProxyType` keyed by
`OpaqueSilverPairKey` (Slice-A `5dc757c`/`1071067`); a single replay row may establish its own root **and** require
other row-start slots' manifest definitions (atomicity `457d279` §6/§9 multi-intent), so the whole artifact — not a
single resolved definition — is the only shape that satisfies the contract.

---

## 5. Corrected Duplicate Semantics (binding)

- **`STEP_DUPLICATE_ROOT` applies whenever the current projected Silver pair is a manifest target AND is already
  present in `current_seen_pairs`.**
- It is **independent of** lifecycle state, root establishment, terminal state, observation kind, and all later-row
  fields.
- It **explicitly includes** a pair previously **committed as seen after a valid permanent root unit-mismatch** while
  that pair's slot remains `AUDIT_REPLAYED` + `NoRootEvidence` (atomicity `457d279` §5: the unit-mismatch root still
  commits the pair as seen).
- The duplicate failure remains **immediate** and **precedes terminal handling and all later projections**
  (atomicity `457d279` §8 A/B; precedence `457d279` §8).
- **Every "already-established" narrowing is removed** from the duplicate reason description, matrices, precedence
  prose, and future tests.

### 5.1 Corrected duplicate truth table

| Current projected pair | manifest target? | in `current_seen_pairs`? | slot state of that pair | Outcome |
|---|---|---|---|---|
| pair P | **yes** | **yes** | `INTENT_RECORDED` / `HYPOTHETICAL_CONDITION_MET` (established non-terminal) | ❌ `STEP_DUPLICATE_ROOT` (immediate) |
| pair P | **yes** | **yes** | `INTENT_EXPIRED` / `INTENT_RETIRED` (terminal) | ❌ `STEP_DUPLICATE_ROOT` (immediate, precedes terminal handling) |
| pair P | **yes** | **yes** | `AUDIT_REPLAYED` + `NoRootEvidence` (committed-seen unit-mismatch) | ❌ `STEP_DUPLICATE_ROOT` (immediate) |
| pair P | **yes** | no | — | first target → root-establishment path (not a duplicate) |
| pair P | no | (n/a) | — | non-targeted → irrelevant no-op (membership branch, no `KeyError`) |

---

## 6. Exact Error Object API (binding)

```python
class AtomicReplayStepError(ValueError):
    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason
```

- **Exact constructor arguments are `reason` and `message`** (positional, in that order), matching the sealed
  Slice-C `S1EvidenceProjectionError` and Slice-D `ClassificationPredicateError` pattern.
- **The observable attribute is `.reason`.**
- **Every runtime raise site uses exactly one of the ten closed reason constants** (`85d1ba6` §8, unchanged):
  `STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT`, `STEP_INVALID_CURRENT_SEEN_PAIRS`, `STEP_INVALID_MANIFEST_PROJECTION`,
  `STEP_EVIDENCE_PROJECTION_REJECTED`, `STEP_CLASSIFICATION_PREDICATE_REJECTED`, `STEP_MANIFEST_DEFINITION_ABSENT`,
  `STEP_DUPLICATE_ROOT`, `STEP_TARGETED_NON_SCORE_ROOT`, `STEP_INVALID_LIFECYCLE_TRANSITION`,
  `STEP_PUBLICATION_INVARIANT_VIOLATION`.
- **No alternative error class, constructor shape, reason attribute name, tuple, payload object, or raw-message-only
  surface is legal.**

---

## 7. Result-Constructor Failure Mapping (binding)

- **`AtomicReplayStepResult.__post_init__` structurally revalidates both snapshot fields**
  (`next_lifecycle_snapshot`, `next_seen_target_pairs`) — exact carrier type, populated **and** missing-slot
  forgeries, stored representation (`MappingProxyType` / `frozenset`), nested keys/slots/members, and complete
  invariants — reusing the sealed Slice-A revalidators and the guarded `_slot_value` discipline.
- **Any wrong type, populated/missing-slot forgery, wrong representation, malformed nested member, or broken
  snapshot invariant supplied to DIRECT `AtomicReplayStepResult` construction raises
  `AtomicReplayStepError(STEP_PUBLICATION_INVARIANT_VIOLATION, message)`** — the publication-boundary reason, because
  the result is the single atomic publication point.
- **Input-parameter validation remains mapped separately**: a malformed `current_lifecycle_snapshot` →
  `STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT`; a malformed `current_seen_pairs` → `STEP_INVALID_CURRENT_SEEN_PAIRS`
  (these are validated at the Step's consumer boundary, not by the result constructor).
- **Identity preservation remains a Step postcondition and is NOT checked by the result constructor** (`85d1ba6` §5,
  unchanged): the constructor cannot see the inputs and enforces only structural validity.

### 7.1 Result-construction error matrix

| Direct `AtomicReplayStepResult(...)` argument | Outcome |
|---|---|
| two valid snapshot carriers | ✅ constructs |
| `next_lifecycle_snapshot` wrong type / populated forgery / missing-slot / wrong representation / broken invariant | ❌ `AtomicReplayStepError(STEP_PUBLICATION_INVARIANT_VIOLATION, message)` |
| `next_seen_target_pairs` wrong type / forged / non-`frozenset` / forged member | ❌ `AtomicReplayStepError(STEP_PUBLICATION_INVARIANT_VIOLATION, message)` |
| (Step boundary, not the constructor) malformed `current_lifecycle_snapshot` | ❌ `AtomicReplayStepError(STEP_INVALID_CURRENT_LIFECYCLE_SNAPSHOT, message)` |
| (Step boundary) malformed `current_seen_pairs` | ❌ `AtomicReplayStepError(STEP_INVALID_CURRENT_SEEN_PAIRS, message)` |

---

## 8. Corrected Future RED → GREEN Requirements (delta to `85d1ba6` §13; NOT opened here)

The later separately-authorized Slice-E TDD task must reflect these corrections:

1. **Exact API:** the signature uses `frozen_manifest_projection: ShadowIntentDefinitionArtifact`; **no**
   `FrozenManifestProjection` symbol resolves (`assert not hasattr(module, "FrozenManifestProjection")`); only the
   pinned callable/parameter/result/field names resolve.
2. **Manifest ownership:** Slice E accepts the **whole** `ShadowIntentDefinitionArtifact`; `M[key]` `KeyError` →
   `STEP_MANIFEST_DEFINITION_ABSENT` at the single lookup site; membership branches never raise; a single row can
   resolve multiple keys; no pre-resolved single definition is accepted/injected.
3. **Duplicate:** `STEP_DUPLICATE_ROOT` fires for target-in-`current_seen_pairs` regardless of lifecycle/root/
   terminal/kind, **including** the committed-seen `AUDIT_REPLAYED`+`NoRootEvidence` unit-mismatch pair, immediately
   and before terminal handling / later projections; no "already-established" narrowing appears in any test.
4. **Error API:** `AtomicReplayStepError(reason, message)` with `.reason`; every raise uses one of the ten closed
   constants; no alternative class/constructor/attribute/payload.
5. **Result constructor:** direct-construction revalidation failures (incl. missing-slot forgeries) →
   `STEP_PUBLICATION_INVARIANT_VIOLATION`; input-boundary failures stay mapped to the input reasons; identity is a
   Step postcondition, not a constructor check.
6. All other `85d1ba6` §13 requirements (consumer-forgery matrix, precedence/non-inspection matrix, identity/
   atomicity, AST locks, the surgical Slice-E/F→Slice-F-only lock rename) remain, updated only for the above.

---

## 9. Preserved Unchanged (affirmed)

All other `85d1ba6` clauses stand: the `AtomicReplayStepResult` two-field frozen/slots/kw-only no-factory shape;
the §5 identity/publication postconditions and §5.1 no-op/partial truth table; the opaque-`raw_evidence_row`
strict-lazy projection rule (no `sqlite3` import, no direct inspection, reached Slice-C ops only, no
`project_row_envelope`/eager); the manifest-resident orientation/boundary/unit/duration rationale; the closed
ten-reason set; the §9 error-precedence order; the §10 exception discipline (KeyError only at the contract lookup;
no raw `AttributeError`/`TypeError`/`ValueError`/`InvalidOperation`/`KeyError`/foreign-eq-hash escape;
`BaseException`/`MemoryError`/`KeyboardInterrupt`/`SystemExit`/`GeneratorExit`/unrelated never caught); and all
preserved precedence/duplicate-primacy/strict-lazy-privacy/classify-all-apply-all/terminal-absorption/lifecycle-
legality/determinism/passive-only provisions. **No Step implementation behavior is defined beyond these boundaries.**

---

## 10. Unresolved Items

- **None.** Every affected occurrence of `FrozenManifestProjection` (as a type/API symbol), the manifest-lookup
  ownership, the duplicate narrowing, the error-object API, and the result-constructor failure mapping is corrected
  exactly, with no "e.g.", alternative naming, or residual ambiguity. `"FrozenManifestProjection"` survives only as
  an explicitly-labeled prose role.

---

## 11. Exclusions / Precise Post-Charter State (ratified)

- Docs-only: no runtime/tests/fixtures/prior-charter/lock edits; `atomic_replay_step.py` and `reconstruction.py`
  not created; Slice F/G not opened. `85d1ba6` not edited/deleted/amended/rebased/force-pushed.
- **Slice E remains BLOCKED pending independent review and ratification of this correction.** **Slice F/G remain
  blocked.** **Capacity remains 0.** **Phase 6.2 remains INCOMPLETE and NOT runtime-ready;** execution / routing /
  actionability / live / paper / canary behavior remain **forbidden.** Phase 6.1 frozen, COMPLETE + RATIFIED.

**Conclusion:** `85d1ba6` is marked historical and **UNRATIFIED** and corrected on five exactness defects only. The
manifest parameter is annotated with the **real runtime type** —
`execute_atomic_replay_step(*, current_lifecycle_snapshot: ShadowLifecycleSnapshot, current_seen_pairs:
SeenTargetPairsSnapshot, raw_evidence_row: object, frozen_manifest_projection: ShadowIntentDefinitionArtifact) ->
AtomicReplayStepResult` — the parameter name `frozen_manifest_projection` preserved, `"FrozenManifestProjection"`
kept **only** as a prose semantic role, and **no** `FrozenManifestProjection` class/alias/protocol/runtime symbol
created. Slice E receives the **complete** `ShadowIntentDefinitionArtifact` and performs the single contract-defined
`M[key]` lookup itself (multi-key root + one-row multi-intent), Slice F/G never pre-resolving/injecting a single
definition, `KeyError` normalized only at that site, membership remaining a branch/no-op. `STEP_DUPLICATE_ROOT`
fires whenever the projected target pair is already in `current_seen_pairs` — independent of lifecycle/root/terminal/
kind/later-fields, **including** the committed-seen `AUDIT_REPLAYED`+`NoRootEvidence` unit-mismatch pair —
immediately and before terminal handling/later projections, with every "already-established" narrowing removed. The
error surface is exactly `AtomicReplayStepError(ValueError)` with `__init__(self, reason, message)` and `.reason`
(matching the sealed Slice-C/D pattern), every raise using one of the ten closed reasons, no alternative class/
constructor/attribute/payload. A direct `AtomicReplayStepResult.__post_init__` revalidation failure (incl. missing-
slot forgery) maps to `STEP_PUBLICATION_INVARIANT_VIOLATION`, input-parameter validation stays mapped to the input
reasons, and identity preservation remains a Step postcondition not checked by the constructor. All other `85d1ba6`
clauses are **preserved**, **no unresolved items** remain, and **Slice E stays BLOCKED pending independent review;
Slice F/G blocked; capacity 0; Phase 6.2 INCOMPLETE and NOT runtime-ready. No executable work is authorized.**
