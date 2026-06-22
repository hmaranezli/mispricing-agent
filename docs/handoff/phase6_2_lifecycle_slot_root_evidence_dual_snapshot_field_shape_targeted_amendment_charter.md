# Phase 6.2 — Lifecycle-Slot, Root-Evidence & Dual-Snapshot Field-Shape Targeted Amendment Charter

> **This is a docs-only targeted field-shape amendment charter.** It pins the **exact Slice-A value-type field
> shapes** for the per-intent lifecycle slot, its closed root-evidence option-sum, and the two immutable replay-local
> snapshot containers that `457d279` §3's atomic `Step` law names but never shaped. It **implements nothing and
> authorizes nothing executable**: no runtime code, no tests, no fixtures, no DTO instance, no loader, no state
> machine, no `Step` algorithm, no replay loop, no SQLite, no artifact read, no persistence, no emission, no Phase
> 6.1 edits, no S1-adapter edits, no Gate A/B edits, no frozen-component edits, no prior-charter file edits, no
> package edits, no generated files, no pytest, no graphify, no commit beyond this single docs file. It corrects /
> concretizes prior charters **only** through the exact relationship/supersession map in §2. It makes **no** Phase
> 6.2 runtime/paper/live/production readiness claim. It is subordinate to the full Phase 6.2 charter chain — the
> Gate A field-shape + predecessor charters (`5dc757c`, `1071067`), the Gate B canonical-encoding charter
> (`474cc6f`), the conceptual field-shape charter (`ef26f59`), the lifecycle / state-transition charter (`e9995e7`),
> the multi-event context-supply / shadow-state boundary charter (`999a109`), the predicate-precedence / decimal-
> source / evidence-consistency charter (`457d279`-chain, base `d7204d6`), the replay-step atomicity / row-start
> snapshot / terminal-relevance charter (`44791ce`→`457d279`), the reconstruction-runtime TDD planning & slice
> charter (`457d279`), the S1 durable-storage charters, and `CLAUDE.md` — and where any conflict arises, those
> govern **except** for the narrow, explicitly-mapped concretizations in §2.

**Base:** `f6c428eb7c475a33e55f1406407b6e16b09628d2`

---

## 1. Base / Purpose

**Base commit:** `f6c428eb7c475a33e55f1406407b6e16b09628d2`.

Slices A–D of the reconstruction runtime are built and ratified (Slice D through `f6c428e`). Slice E (Atomic Replay
Step) is **blocked**: `457d279` §3 defines the step as
`Step(RowStartShadowSnapshot, RowStartSeenTargetPairs, CurrentS1Row, FrozenManifestProjection) → HardFailure |
(NextShadowSnapshot, NextSeenTargetPairs)`, but the current `logical_model.py` deliberately provides only the closed
lifecycle-state **vocabulary** + `validate_lifecycle_state` and **no immutable lifecycle slot, no root-context /
anchor value type, and no shadow-snapshot / seen-pairs value types** — its own docstring records the slot/snapshot
container as deliberately absent, "await[ing] its own field-shape charter." This charter **is** that field-shape
charter. It pins the exact Slice-A value-type shapes so a **later, separately-authorized Slice-A runtime extension**
(not Slice E) can implement them under TDD. It invents nothing: every mandatory field is source-proven from the
chain above; the conceptual fields that do **not** become slot fields are explicitly reconciled (§3), not silently
omitted.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Exact Relationship / Supersession Map (binding)

This charter **concretizes** field shape; it **supersedes no behavioral clause**. All transition, precedence,
atomicity, decimal, timestamp, duplicate-root, HALT, and firewall rules of `e9995e7`/`999a109`/`457d279`-chain/
`44791ce`→`457d279` stand **intact**.

| Charter / § | Identified clause | Precise concretization (this charter) |
|---|---|---|
| `ef26f59` §6 | conceptual key-level shadow-intent fields: `shadow_intent_identity_reference`, `exposure_orientation`, `lifecycle_state`, `hypothetical_outcome_reference`, `evidence_provenance_reference` ("no concrete types … fixed here") | Concretized into Slice-A runtime value types per §3–§5. Each conceptual field is reconciled in §3 (slot field, manifest-resident, established-root-evidence-resident, or firewalled-deferred) — **no silent omission**. |
| `457d279` (atomicity §3) | `Step(RowStartShadowSnapshot, RowStartSeenTargetPairs, …) → (NextShadowSnapshot, NextSeenTargetPairs)` names four snapshot roles but **pins no value-type shape** | This charter supplies **one** `ShadowLifecycleSnapshot` type for both `RowStartShadowSnapshot` and `NextShadowSnapshot` roles (§4), and **one** `SeenTargetPairsSnapshot` type for both `RowStartSeenTargetPairs` and `NextSeenTargetPairs` roles (§5). The `Step` algorithm itself stays **unbuilt and excluded** (§7). |
| `457d279` (planning §4) | `logical_model.py` ownership: "…lifecycle slot/snapshot value types, and closed structural validation only" | Affirmed: these value types belong **exclusively** to Slice A / `logical_model.py`, which remains an intra-package dependency **leaf** (§1 ownership below). |
| `logical_model.py` docstring | "The shadow-intent *slot* / *snapshot* CONTAINER shape is deliberately absent … the container DTO awaits its own field-shape charter." | Resolved by §3–§6. The later Slice-A runtime extension (§9 gate) implements them; this charter does **not** edit `logical_model.py`. |

**Ownership (binding):**

- **All passive lifecycle value carriers** — the slot, the root-evidence option-sum and its context carrier, and
  both snapshot containers — **belong exclusively to Slice A / `logical_model.py`.**
- **Slice E may consume and transform them** (read fields, compute inert proposals, build the next pair) **but MUST
  NOT define replacement DTOs, dict schemas, or unnamed/positional tuples** for any of these shapes.
- `logical_model.py` **remains an intra-package dependency leaf**: it imports nothing from `artifact_verifier`,
  `s1_evidence_projection`, `classification_predicates`, `atomic_replay_step`, `reconstruction`, Phase 6.1, the S1
  storage package, or Phase 5 (stdlib only). The reverse one-way quarantine (`457d279` §3) is preserved.

---

## 3. Conceptual-Field Reconciliation (binding — no silent omission)

Every `ef26f59` §6 conceptual field is resolved exactly once:

| `ef26f59` §6 conceptual field | Resolution | Source proof |
|---|---|---|
| `shadow_intent_identity_reference` | **Slot field** `shadow_intent_identity_reference: OpaqueSilverPairKey` (the existing borrowed identity; never minted). Also the snapshot **map key** (§4); the publication invariant binds key == slot identity. | `OpaqueSilverPairKey` in `logical_model.py`; `999a109` §4 (key strictly by opaque Silver pair, no domain-identity invention, no rowid identity). |
| `exposure_orientation` | **NOT a slot field.** It is **manifest-definition data** owned by `DirectionalShadowIntentDefinition.exposure_orientation` / `InertShadowIntentDefinition.exposure_orientation`, reachable via the **same** `OpaqueSilverPairKey` in the `FrozenManifestProjection`. Duplicating it into the mutable lifecycle slot is forbidden (would be independently-drifting manifest data). | `logical_model.py` definition variants; `457d279` precedence §3/§4 reads orientation from the manifest, not the slot; this charter §3 "do not duplicate manifest definition data." |
| `lifecycle_state` | **Slot field** `lifecycle_state: str`, exactly one of `CLOSED_LIFECYCLE_STATES`. | `e9995e7` §4 closed set + `validate_lifecycle_state` in `logical_model.py`. |
| `evidence_provenance_reference` | **Realized as the established-root-evidence variant** (§4): the by-reference audited evidence the intent was established from **is** its `EstablishedRootContext` (two-scalar context) + `provenance_anchor_timestamp_text`. No separate opaque-provenance slot field is added; a non-established slot carries `NoRootEvidence`. | `ef26f59` §6 (evidence_provenance "carried verbatim"); `999a109` §3 (container holds "by-reference audited evidence links"); `457d279` precedence §5/§6 (context + anchor are exactly the audited establishment evidence). |
| `hypothetical_outcome_reference` | **Explicitly OUTSIDE this minimal slot — deferred, not omitted.** `HYPOTHETICAL_OUTCOME` is a firewalled counterfactual projection computed **only** as an inert projection at condition/terminal states and **does not drive transitions**; no ratified charter pins its concrete value-type shape. Adding it now would be invention. It **awaits its own field-shape charter** and is **not** required by the Slice-E `Step` (which classifies transitions from evidence, not from outcome). | `e9995e7` §6 firewall; `999a109` §7/§11 (outcome never drives transitions, no concrete shape pinned). |

**Result:** the minimal lifecycle slot carries exactly **identity + lifecycle_state + root_evidence** (§4). Nothing
mandatory is unresolved; nothing is silently omitted.

---

## 4. Lifecycle Slot & Closed Root-Evidence Option-Sum (binding field shape)

### 4.1 Root-evidence option-sum (closed; no nullable/optional soup, no sentinel strings)

Exactly two concrete variants; the field is **always present** and is **exactly one** variant (mirroring the
ratified `NoPredecessor | PredecessorReference` discipline in `logical_model.py`):

**`NoRootEvidence`** — `@dataclass(frozen=True, slots=True)`, **zero payload fields** (a genuine slotted variant,
like `NoPredecessor`). Means "no established root for this slot."

**`EstablishedRootEvidence`** — `@dataclass(frozen=True, slots=True, kw_only=True)`, self-validating, exact ordered
fields:

| # | Field | Type | Validation (self + defensive) |
|---|---|---|---|
| 1 | `root_context` | `EstablishedRootContext` | exact type; both nested scalars revalidated |
| 2 | `provenance_anchor_timestamp_text` | `str` | exact `str`; canonical non-negative integer decimal text (the `str(int)` form: `0` or `[1-9]\d*`, no sign, no fraction, no leading zeros) — carried verbatim |

**`EstablishedRootContext`** — `@dataclass(frozen=True, slots=True, kw_only=True)`, the **immutable two-scalar
context**, exact ordered fields:

| # | Field | Type | Validation |
|---|---|---|---|
| 1 | `source_venue_context_text` | `str` | exact `str`, opaque, verbatim (the first of `score_inputs_summary = (source_venue, source_pair)`) |
| 2 | `source_pair_context_text` | `str` | exact `str`, opaque, verbatim (the second of `score_inputs_summary`) |

*Source proof:* `457d279` precedence §5 (`score_inputs_summary = (source_venue, source_pair)`, exactly two text
scalars) + §6 (`provenance_timestamp` is the audited `observed_at_epoch_ms`, and the row text equals the payload
integer's canonical `str(int)` text). These are exactly the two operands later comparisons need — context for exact
context-equality, the anchor for `TIMESTAMP_DELTA` expiry — and **nothing more** is admitted (no orientation, no
boundary, no unit, no window: those are manifest-definition data, §3).

### 4.2 Lifecycle slot

**`ShadowIntentLifecycleSlot`** — `@dataclass(frozen=True, slots=True, kw_only=True)`, methodless,
self-validating, exact ordered fields:

| # | Field | Type | Validation |
|---|---|---|---|
| 1 | `shadow_intent_identity_reference` | `OpaqueSilverPairKey` | exact type; both opaque-text components revalidated (reuses `OpaqueSilverPairKey` — **never** mints another identity) |
| 2 | `lifecycle_state` | `str` | exactly one of `CLOSED_LIFECYCLE_STATES` (`validate_lifecycle_state`) |
| 3 | `root_evidence` | `NoRootEvidence \| EstablishedRootEvidence` | exactly one closed variant (§4.1); type-dispatched defensive revalidation |

### 4.3 Closed lifecycle-state / root-evidence invariant (binding)

Enforced in `__post_init__` **and** re-asserted on every container publication (§6):

- `AUDIT_REPLAYED` ⟺ `NoRootEvidence`.
- Each of `INTENT_RECORDED`, `HYPOTHETICAL_CONDITION_MET`, `INTENT_EXPIRED`, `INTENT_RETIRED` ⟺
  `EstablishedRootEvidence`.

*Source proof:* `e9995e7` §4 — `AUDIT_REPLAYED` is the bootstrap/non-established initial state; establishment is the
`AUDIT_REPLAYED → INTENT_RECORDED` edge; forward/terminal states are reachable **only** after establishment. The
permanently-non-established directional unit-mismatch case **remains `AUDIT_REPLAYED` with `NoRootEvidence`**
(`457d279` atomicity §5; precedence §3 (U)).

**Structural distinction of the three AUDIT_REPLAYED situations** (slot-level state is identical —
`AUDIT_REPLAYED` + `NoRootEvidence` — so the distinction is **structural via the separate seen-target-pair
snapshot**, §5):

| Situation | Slot in `ShadowLifecycleSnapshot`? | Pair in `SeenTargetPairsSnapshot`? |
|---|---|---|
| Never observed / dormant manifest key | absent | absent |
| Permanent root unit-mismatch (committed-seen, non-established) | present: `AUDIT_REPLAYED` + `NoRootEvidence` | **present** |
| (For contrast) established intent | present: forward/terminal + `EstablishedRootEvidence` | present |

This is exactly `457d279` atomicity §5: a valid root unit-mismatch **commits the pair as seen** (so a later
occurrence is a correct duplicate hard-failure) **while leaving its slot permanently `AUDIT_REPLAYED` /
non-established**.

### 4.4 Legal / illegal state-shape matrix (binding)

| `lifecycle_state` | `root_evidence` | Legal? |
|---|---|---|
| `AUDIT_REPLAYED` | `NoRootEvidence` | ✅ legal |
| `AUDIT_REPLAYED` | `EstablishedRootEvidence` | ❌ illegal (reject) |
| `INTENT_RECORDED` | `EstablishedRootEvidence` | ✅ legal |
| `INTENT_RECORDED` | `NoRootEvidence` | ❌ illegal (reject) |
| `HYPOTHETICAL_CONDITION_MET` | `EstablishedRootEvidence` | ✅ legal |
| `HYPOTHETICAL_CONDITION_MET` | `NoRootEvidence` | ❌ illegal (reject) |
| `INTENT_EXPIRED` | `EstablishedRootEvidence` | ✅ legal |
| `INTENT_EXPIRED` | `NoRootEvidence` | ❌ illegal (reject) |
| `INTENT_RETIRED` | `EstablishedRootEvidence` | ✅ legal |
| `INTENT_RETIRED` | `NoRootEvidence` | ❌ illegal (reject) |
| any value ∉ `CLOSED_LIFECYCLE_STATES` | any | ❌ illegal (reject) |
| any | a non-variant / forged `root_evidence` | ❌ illegal (reject) |

### 4.5 Defensive `object.__new__` revalidation (binding)

A `_revalidate_lifecycle_slot` pass (analogous to `_revalidate_silver_pair_key` / `_revalidate_definition`) must,
on every container publication, re-assert: exact slot type; identity-key complete invariants; `lifecycle_state`
membership; `root_evidence` exact-variant + nested-field invariants; and the §4.3 state/root invariant — so an
`object.__new__`-forged slot or nested value (constructed bypassing `__post_init__`) is rejected through the single
closed `LogicalModelError` surface, never leaking a raw `AttributeError`/`TypeError`.

---

## 5. Dual Snapshots (binding field shape)

### 5.1 Shadow snapshot (`ShadowLifecycleSnapshot`)

**One** immutable concrete type used in **both** the `RowStartShadowSnapshot` and `NextShadowSnapshot` roles
(`457d279` §3). It is **factory-only** (direct construction raises `LogicalModelError`), mirroring
`ShadowIntentDefinitionArtifact`.

- **Exact key/value relation:** `OpaqueSilverPairKey → ShadowIntentLifecycleSlot`, and the map **key MUST equal
  `slot.shadow_intent_identity_reference`** (publication invariant; mismatch → reject).
- **Input construction preserves duplicate detection before map construction:** built from an explicit ordered
  tuple of `(OpaqueSilverPairKey, ShadowIntentLifecycleSlot)` entries; a duplicate key is **rejected** (no
  first/last-wins, no merge) — exactly the `make_shadow_intent_definition_artifact` discipline. Ordering carries
  **no** semantic meaning (it exists only so duplicates are detectable). An empty map is valid.
- **Published storage:** an immutable `MappingProxyType` over a **non-retained** local dict — **no mutable alias,
  no caller-owned dict retained, no global registry, no rowid/`append_sequence` identity, and no iteration-order
  semantics** (`999a109` §4/§5; `457d279` atomicity §5).

### 5.2 Seen-target-pairs snapshot (`SeenTargetPairsSnapshot`)

**One** immutable, **replay-local**, instance-scoped concrete type used in **both** the `RowStartSeenTargetPairs`
and `NextSeenTargetPairs` roles. Factory-only.

- **Members are exact `OpaqueSilverPairKey` values only** (each revalidated; non-key/forged member → reject).
  Members are hashable (the key is `frozen, slots`).
- **Duplicate checking reads row-start state:** the membership test for the per-row global guard reads the
  immutable row-start instance; it never reads a mid-row-mutated set (`457d279` atomicity §5/§8).
- **Successful additions publish only in the atomic next pair:** a first targeted occurrence's pair is published
  **only** in the freshly-built `NextSeenTargetPairs` (committed atomically with the shadow proposals by Slice E);
  the slot/snapshot types here expose **no in-place add/mutator**.
- **Published storage:** an immutable members view (e.g. a `frozenset` of `OpaqueSilverPairKey`, or a
  `MappingProxyType`-guarded membership view) — **no module-global, no cache, no singleton, no shared mutable
  state** (`999a109` §4/§5; `457d279` atomicity §5).

### 5.3 Snapshot equality & determinism (binding)

- Both snapshots expose **order-independent structural (content) equality**: two snapshots built from logically
  equal content (same key→slot mapping; same member set) compare **equal**, independent of entry/iteration order
  and of any insertion history. This underwrites the `e9995e7` §3 / `457d279` determinism & idempotency guarantee
  (re-replaying the same fixed input yields equal snapshots).
- Snapshots are **not required to be hashable** (they are values, never map keys).
- `ShadowIntentLifecycleSlot`, `EstablishedRootEvidence`, `EstablishedRootContext`, and `NoRootEvidence` use
  **structural value equality** over their ordered fields (frozen-dataclass default), so slot equality is exact and
  deterministic.

---

## 6. Construction & Hardening (binding)

- **Every value carrier** (`EstablishedRootContext`, `EstablishedRootEvidence`, `NoRootEvidence`,
  `ShadowIntentLifecycleSlot`) is `frozen=True, slots=True` (and `kw_only=True` where it has fields), **methodless**
  (no behavior methods beyond `__post_init__` validation and dataclass-generated dunders), and **directly
  self-validating** in `__post_init__` using the same shared validators its factory/revalidator uses — so direct
  construction can never bypass validation.
- **Both containers** (`ShadowLifecycleSnapshot`, `SeenTargetPairsSnapshot`) are **factory-only** (direct
  construction raises `LogicalModelError`) and built through a maker that performs **complete defensive
  revalidation** in one bounded O(n) pass: nested keys, slot type + slots, root-evidence option variant + nested
  fields, the §4.3 lifecycle/root invariant, the key == slot-identity invariant (shadow), and member type (seen) —
  before the immutable map/members view is published.
- **Direct construction and `object.__new__`-forged nested values are rejected through the single closed Slice-A
  failure surface** `LogicalModelError` — never a leaked `AttributeError`/`TypeError`/`KeyError`, and the
  revalidator never catches `BaseException`/`MemoryError`/`KeyboardInterrupt`.
- **Immutability:** frozen + slotted throughout; published containers wrap a non-retained local; no field exposes a
  mutable alias.
- **Equality:** §5.3 (value-structural for carriers; order-independent content for containers).
- **Deterministic reconstruction:** equal logical inputs ⇒ equal carriers and equal snapshots, with **no** reliance
  on rowid, `append_sequence`, insertion order, address identity, clock, or any hidden/global state.

---

## 7. Explicit Exclusions (binding)

This charter pins **field shape only**. It defines **no**:

- `Step` algorithm, inert **proposals**, classify-all / apply-all ordering, per-row sequence, or any replay-step
  behavior (that is **Slice E**, still blocked);
- replay loop / fold (**Slice F**); SQLite read/write; artifact byte read / digest verification (Slice B already
  built, untouched); S1 projection (Slice C already built, untouched); persistence; emission;
- lifecycle **mutation** (these are immutable snapshots; transitions are Slice E proposals applied atomically into a
  *new* snapshot), execution, routing, order-emission, actionability, capacity, or integration of any kind.

**Slice E / F / G remain blocked.** **Capacity remains DEFERRED at exactly 0 emit sites.** **Phase 6.2 remains
UNBUILT/INCOMPLETE and NOT runtime-ready.** Phase 6.1 stays frozen, COMPLETE + RATIFIED. Production / live / paper /
canary / execution / routing / actionability forbidden. Historical S1 evidence is read verbatim, never censored.

---

## 8. Planned RED → GREEN Test Matrix (for the LATER separately-authorized Slice-A runtime extension only)

These tests belong to a **future** human-authorized Slice-A runtime extension TDD task; **none is authorized or
written here.** They map each pinned shape to its proving test.

| # | RED (must fail before impl) | GREEN (minimal impl satisfies) | Maps to |
|---|---|---|---|
| 1 | `EstablishedRootContext` rejects non-`str` / missing scalar; accepts two verbatim text scalars | self-validating two-field carrier | §4.1 |
| 2 | `EstablishedRootEvidence` rejects non-canonical / signed / fractional / leading-zero anchor text and non-`EstablishedRootContext` context; accepts canonical `str(int)` anchor | self-validating two-field carrier | §4.1 |
| 3 | `NoRootEvidence` is a genuine zero-field slotted variant (no payload, no `__dict__`) | zero-field frozen/slotted dataclass | §4.1 |
| 4 | `ShadowIntentLifecycleSlot` rejects wrong identity type, invalid `lifecycle_state`, non-variant `root_evidence` | self-validating three-field carrier | §4.2 |
| 5 | §4.3 invariant truth table: every illegal (state, root_evidence) pair in §4.4 rejected; every legal pair accepted | invariant check in `__post_init__` + revalidator | §4.3/§4.4 |
| 6 | permanent unit-mismatch shape = `AUDIT_REPLAYED` + `NoRootEvidence` is **legal** and distinct from established | §4.3 invariant admits it | §4.3 |
| 7 | `object.__new__`-forged slot / forged nested context / forged root-evidence variant rejected via `LogicalModelError` on publication | `_revalidate_lifecycle_slot` defensive pass | §4.5/§6 |
| 8 | `ShadowLifecycleSnapshot` direct construction raises; factory builds immutable proxy; duplicate key rejected; key≠slot-identity rejected; empty map valid | factory-only maker + revalidation | §5.1/§6 |
| 9 | `ShadowLifecycleSnapshot` published map has no mutable alias / caller-dict retention / iteration-order semantics; mutation attempt fails | `MappingProxyType` over non-retained local | §5.1 |
| 10 | `SeenTargetPairsSnapshot` direct construction raises; factory builds immutable members; non-`OpaqueSilverPairKey` / forged member rejected; no mutator exposed | factory-only maker + revalidation | §5.2/§6 |
| 11 | order-independent content equality for both snapshots; equal-content ⇒ equal; reordered entries ⇒ equal | structural/content `__eq__` | §5.3 |
| 12 | value-structural equality for slot / root-evidence / context carriers | frozen-dataclass eq | §5.3 |
| 13 | dependency-direction lock: `logical_model` imports no Phase 6.2 sibling / Phase 6.1 / S1-storage / Phase 5 (stdlib only) | leaf preserved | §2 ownership |
| 14 | absence lock: `atomic_replay_step.py` / `reconstruction.py` still absent (Slice E/F not opened by this extension) | unchanged `test_slice_e_f_targets_not_created` | §7 |

**Regression:** the extension must keep the established selected regression
(`-k "lock or forbidden or quarantine or durable_sqlite"`) green and add focused Slice-A tests; **no broad pytest,
no opportunistic refactor, no adjacent-slice implementation.**

---

## 9. Next Gate (ratified)

- **The single eligible next gate is a separately-authorized "Phase 6.2 Slice-A Lifecycle-Slot / Root-Evidence /
  Dual-Snapshot Runtime Extension" TDD task** — RED→GREEN, adding **only** the value types pinned here to
  `logical_model.py` (which **this** charter does not edit), under §8's matrix. **It is NOT Slice E.**
- **Slice E (Atomic Replay Step) stays blocked** until that runtime extension lands and is ratified; only then are
  its `Step` inputs/outputs (the four snapshot roles) concretely typed and constructible.
- This charter **does NOT open, draft, implement, or authorize** that runtime extension, Slice E/F/G, or any
  executable work. **Phase 6.2 remains UNBUILT/INCOMPLETE and NOT runtime-ready; capacity deferred at 0 emit
  sites.**

---

## 10. Precise Post-Charter State (ratified)

- **Phase 6.2: INCOMPLETE and NOT runtime-ready.** This charter pins **only** the Slice-A field shapes (§3–§6),
  their legal/illegal matrix (§4.4), the relationship/supersession map (§2), and the future-extension RED/GREEN
  matrix (§8). It changes no runtime, no test, and no prior charter file.
- **Slices A–D built; Slice D ratified through `f6c428e`.** Slice E/F/G blocked. The Slice-A runtime extension (§9)
  is the named next gate.
- **Phase 6.1:** frozen, COMPLETE + RATIFIED (unchanged). **Capacity:** deferred (0 emit sites). **Production /
  live / paper / canary / execution / routing / actionability:** forbidden.

**Conclusion:** the deliberately-deferred Phase 6.2 lifecycle slot / snapshot container shape is now pinned
(docs-only) as Slice-A-owned value types: a closed root-evidence option-sum **`NoRootEvidence | EstablishedRootEvidence`**
(established = an immutable two-scalar **`EstablishedRootContext(source_venue_context_text, source_pair_context_text)`**
+ a canonical `str(int)` **`provenance_anchor_timestamp_text`**, exactly the operands later comparisons need); a
minimal **`ShadowIntentLifecycleSlot(shadow_intent_identity_reference: OpaqueSilverPairKey, lifecycle_state,
root_evidence)`** under the closed invariant **`AUDIT_REPLAYED ⟺ NoRootEvidence`** / every established/forward/
terminal state **⟺ EstablishedRootEvidence** (permanent unit-mismatch = `AUDIT_REPLAYED` + `NoRootEvidence`,
distinguished structurally by the seen-pair snapshot); and **one** factory-only immutable
**`ShadowLifecycleSnapshot`** (`OpaqueSilverPairKey → ShadowIntentLifecycleSlot`, key == slot identity, duplicate
rejected before map build, `MappingProxyType`, no alias/registry/rowid/order semantics) plus **one** factory-only
immutable replay-local **`SeenTargetPairsSnapshot`** (`OpaqueSilverPairKey` members only, row-start-read duplicate
checking, atomic next-pair publication, no global/cache/singleton) — each serving **both** the row-start and next
roles of `457d279` §3's `Step`. `exposure_orientation` stays manifest-resident (never duplicated into the slot),
`evidence_provenance_reference` is realized as the established-root evidence, and `hypothetical_outcome_reference`
is explicitly **firewalled-deferred** to its own future charter (no silent omission). Every carrier is
frozen/slotted/kw-only/methodless/self-validating, every container is factory-only with complete defensive
`object.__new__`-forgery revalidation through the single closed `LogicalModelError`, equality is
value-structural / order-independent, and reconstruction is deterministic with no rowid/order/clock/global reliance.
`logical_model.py` stays the intra-package **leaf**; Slice E may consume but never re-define these shapes. **No
`Step` algorithm, proposals, classify/apply ordering, replay loop, SQLite, artifact read, persistence, emission,
lifecycle mutation, execution, or actionability is defined here.** The single eligible next gate is a
separately-authorized **Slice-A runtime extension** (RED→GREEN, §8) — **not Slice E**, which stays blocked. **Phase
6.2 remains UNBUILT/INCOMPLETE and NOT runtime-ready; capacity deferred at 0 emit sites; no executable work is
authorized.**
