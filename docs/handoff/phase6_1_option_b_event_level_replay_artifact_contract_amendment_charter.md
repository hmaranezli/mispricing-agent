# Phase 6.1 — Option-B Event-Level Replay Artifact Contract Amendment Charter

> **This is a docs-only contract-amendment charter.** It pins the **contract-level invariants** of the new
> Option-B event-level replay artifact family — **without** defining concrete fields, serialization, reader code,
> parser mechanics, storage format, or any runtime behavior. It **designs and builds nothing**. It authorizes NO
> runtime code, NO tests, NO lock-test edits, NO pytest, NO graphify, NO Python, NO imports, NO schema/runtime/
> interface edits, NO concrete field names, NO concrete serialization selection, NO parser/reader implementation
> or mechanics, NO B1 runtime implementation, NO B2 normalization change, NO log field-level schema, NO
> persistence/storage implementation, NO B4 scoring, NO S4 materialization, NO S5 runner, NO Cell-3 route, NO
> Phase 6.2 work. It is subordinate to
> `docs/handoff/phase6_1_replay_artifact_io_contract_amendment_decision_charter.md`,
> `docs/handoff/phase6_1_replay_artifact_venue_origin_identity_evidence_review_charter.md`,
> `docs/handoff/phase6_1_b1_replay_artifact_identity_source_decision_charter.md`,
> `docs/handoff/phase6_1_replay_depth_artifact_reader_charter.md`,
> `docs/handoff/phase6_1_replay_depth_reader_io_lock_exception_amendment_charter.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `dbb24a636b09719288c28dbe35d99df8a2331586`

**External review note:** Gemini Quant/Red-Team verdict — `dbb24a6` **Option B is APPROVED**. The selected
direction is a **separate event-level replay artifact family where one physical record equals one logical event**.
Option A remains rejected because single-artifact JSON array indexing creates runtime-counter ambiguity and
violates the frozen one-snapshot-per-record reader boundary. This charter pins Option B's contract invariants.

---

## 1. Base / Dependency Chain

**Base commit:** `dbb24a636b09719288c28dbe35d99df8a2331586`.

References:

- `…_replay_artifact_io_contract_amendment_decision_charter.md` — **selected Option B**; future identity = Silver
  composite `(artifact_locator, physical_record_position)`; Gold venue id preferred-if-available and
  forward-compatible; Option A rejected; existing single-artifact reader stays frozen.
- `…_replay_artifact_venue_origin_identity_evidence_review_charter.md` — Gold/Silver hierarchy; physical I/O
  evidence standard; 5-criterion minimum evidence standard; snapshot-level disqualified.
- `…_b1_replay_artifact_identity_source_decision_charter.md` — identity lives at the **source contract boundary**;
  **B1 runtime is a blind courier**.
- `…_replay_depth_artifact_reader_charter.md` / `…_replay_depth_reader_io_lock_exception_amendment_charter.md` —
  the existing single-artifact reader: read-only, single-record, decide-nothing, **frozen**.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. What This Charter Pins (and what it does not)

This charter fixes, at **contract/invariant level only**, the shape and identity semantics of the Option-B family
so that a **later, separately-authorized** slice can implement it under fixed constraints. It defines **no** field
names, **no** serialization, **no** parser/reader, **no** storage, **no** runtime. It is architecture
documentation — **zero executive functionality**.

---

## 3. The Option-B Family — Contract-Level Definition

The Option-B family is a **separate** replay artifact family of **physical-record** form, distinct from the
existing single-snapshot artifact. Its defining contract property:

- **One physical replay record = exactly one logical event.** Each physical record in the artifact represents one,
  and only one, replay/loggable event (a future B4 score event or S4 materialized-halt event, symmetrically).
- It is an **event stream**, not a snapshot container. The artifact is an ordered sequence of one-event physical
  records.
- It carries, as an **artifact-origin fact**, the physical position of each record (the basis of Silver identity,
  §5) — defined here **semantically only**, never as a concrete field, format, or extraction step.

---

## 4. 1:1 Physical-Record-to-Event Invariant & INVALID Shapes

**Invariant (binding).** Every physical replay record represents **exactly one** logical event. There is no
"one physical record ≠ one event" ambiguity permitted anywhere in this family.

**INVALID artifact shapes (explicitly forbidden for this family):**

- **Batched records** — a physical record holding more than one event.
- **Nested event arrays** — a physical record containing an array/list of events.
- **Multi-event records** — any record whose payload spans multiple logical events.
- **One-snapshot-containing-many-events** — the snapshot-container model (the existing single-artifact shape, or
  any array-of-events-in-one-object form). This is the Option-A model and is **invalid here**.

Any artifact exhibiting these shapes is **not** a valid Option-B artifact. The 1:1 mapping is the precondition for
event-level identity (a snapshot-level or batched record cannot carry a single event-level coordinate).

---

## 5. Artifact-Origin Silver Identity (abstract tuple only)

Silver identity for the Option-B family is a **pure abstract tuple of inherited origin facts**:

> **( artifact-locator concept, physical-record-position concept )**

Constraints (binding):

- **Abstract only.** Both elements are **concepts**, not concrete fields. **No concrete field names** are defined
  here.
- **Pure inherited facts.** Both are **borrowed** artifact-origin facts — the locator naming the physical
  artifact, the position naming the physical record within it.
- **Tuple, never a key string.** The two facts are held as a **tuple**; they are **never concatenated** into a
  composite string, **never** hashed, UUID'd, randomized, timestamped, counted, or fingerprinted.
- **Composite-required.** A bare physical-record-position alone is **not** globally sufficient; the artifact
  locator is required to disambiguate across artifacts. Neither element alone is the identity.
- **Snapshot-level insufficiency.** Snapshot-level labels (`raw_snapshot_identity`/`depth_snapshot_identity`)
  remain **insufficient as sole identity** and are **not** part of this tuple.

---

## 6. State-Free I/O Exposure (physical-record-position semantics)

The **physical_record_position concept** is defined as an **artifact-origin / I/O-intrinsic** position — a
deterministic, reproducible property of how the artifact **physically stores** the record, existing independently
of any reader.

Binding constraints:

- **Artifact-origin only.** The position is a property of the physical artifact (its physical record ordering),
  reproducible on every replay of the same artifact.
- **Runtime/global/application counters are forbidden** as the position. A process-local counter, application
  state, or global sequence is **not** this position.
- **No `enumerate()` / loop-counter endorsement.** A reader loop variable, `enumerate()` index, or any iteration
  ordinal is **not** authoritative identity and is **not** endorsed by this contract. Coincidence of a loop index
  with physical order does **not** make the loop index the identity.
- **Contract-level semantics only.** Only the **semantic** meaning of "physical, artifact-origin record position"
  is fixed here. **No** extraction mechanics, parsing, offset arithmetic, byte/line strategy, or reader behavior
  is designed.

---

## 7. Blind Carriage Continuity

- **B1 carries the identity tuple opaquely** — by reference, as an inherited artifact-origin fact, once the family
  is implemented.
- **B1 / B2 / B3 / Producer / Phase 5 / B4 / S1 must not** inspect, branch on, cast, normalize, mutate, derive,
  filter, or reinterpret the identity tuple. No `int→str`/`str→int` coercion, no string formatting, no prefixing/
  suffixing, no concatenation. Carriage is opaque and verbatim end-to-end.
- The identity is **never** a decision input: no boundary scores, ranks, routes, or gates on it.

---

## 8. Gold Overlay Forward Compatibility

- A **Gold** venue/exchange `message_id` / `sequence_number`, **if later available**, may be carried as an
  **overlay** alongside the Silver tuple.
- Gold **must not delete, mutate, or replace** the Silver artifact coordinate. The Silver `(artifact-locator,
  physical-record-position)` tuple remains intact and carried even when Gold is present (replay stability).
- **No priority/resolution algorithm is designed here** — only the forward-compatibility constraint that Gold is
  additive (an overlay), never destructive to Silver.

---

## 9. Existing Reader Boundary (frozen)

The existing single-artifact replay reader (`phase6_1/b1_replay_depth_artifact_reader.py`) and its closed 8-field
single-snapshot contract remain **frozen and unmodified**. The Option-B family is **separate**: it does **not**
retrofit, extend, overload, or reshape the existing snapshot reader/contract. No change to the existing reader is
authorized or implied.

---

## 10. S2 / Slice-0B Cascade — Remaining Blockers

- **S2 identity: still BLOCKED.** This charter pins the family's **contract invariants** but **implements nothing**
  and **carries no evidence**. S2 stays BLOCKED until the Option-B family is **later implemented and ratified as
  carried evidence** (the tuple actually present on real Option-B artifacts). The opaque S2-owned slot stays
  **unfilled**.
- **Slice-0B field-level schema: still BLOCKED.** It may not define an event-identity field until S2 holds an
  authoritative **carried** borrowed source.
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.** Unchanged. **This charter authorizes nothing executable.**

---

## 11. Still-Forbidden Work

- **No** concrete field names, serialization format/selection, file format spec, parser/reader implementation or
  mechanics, or storage implementation for the Option-B family.
- **No** minting (generate/calculate/hash/concatenate/increment/count/randomize/fingerprint); **no** `event_id`/
  `log_id` formula; **no** string key from the tuple.
- **No** runtime/global/application counter, `enumerate()`, or loop ordinal as identity.
- **No** batched/nested/multi-event/snapshot-container artifact shape (all INVALID, §4).
- **No** amendment/retrofit/unfreezing of the existing single-artifact reader/contract.
- **No** B2 normalization change/design; **no** mapping/coercion/cost/scoring/Phase-5 behavior.
- **No** timestamp-as-identity; **no** `id()`/memory identity; **no** promotion of snapshot-level labels to sole
  identity.
- **No** Gold/Silver priority/resolution algorithm; **no** Gold overlay that deletes/mutates/replaces Silver.
- **No** downstream inspection/branch/cast/normalize/mutate/derive/filter/reinterpret of the identity tuple (blind
  carriage).
- **No** log field-level schema; **no** persistence/storage implementation; **no** S4 materialization; **no** B4
  scoring; **no** S5 runner; **no** Cell-3 route.
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/actionability content.
- **No** Slice-0B authorization; **no** S2 runtime/schema; **no** Phase 6.1 completion claim; **no** Phase 6.2
  readiness claim; **no** 7.x/8.x work.

---

## 12. Readiness Verdict

- **Option-B family: contract invariants PINNED (docs-only), UNBUILT.** 1:1 physical-record-to-event invariant
  fixed; INVALID shapes enumerated; Silver identity defined as the abstract tuple `(artifact-locator concept,
  physical-record-position concept)`; physical position defined as artifact-origin/I/O-intrinsic (no runtime
  counters); Gold overlay additive-only; existing reader frozen; blind carriage continued.
- **S2 identity: BLOCKED** until the family is implemented and ratified as carried evidence. **Slice-0B field-level
  schema: BLOCKED.**
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.**

---

## 13. Next Safe Step (recommendation only)

- A **separately-authorized docs-only Option-B serialization/field-shape charter** — selecting, at contract level,
  the concrete physical-record form (e.g. which physical-record family realizes "one record = one event") and the
  concrete representation of the `(artifact-locator, physical-record-position)` tuple, **still** designing no
  reader/parser/runtime. *Or*, if preferred, a **reader/IO design charter** for an Option-B reader (separate from
  the frozen snapshot reader) under these invariants. Either is docs-first and separately gated.
- Only after the Option-B family is **implemented and ratified as carrying** the artifact-origin tuple may the
  **S2 identity slice** fill the opaque slot, and only then may a **Slice-0B field-level schema** charter be
  authorized (under the S1 boundary and S2 locks).
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency).
- **No implementation is authorized by this charter.** The serialization/field-shape, the Option-B reader, the S2
  identity fill, the 0B schema, S4 materialization, B4 scoring, S5 runner, durable persistence, the Cell-3 route,
  the Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the Option-B event-level replay artifact family is **pinned at contract-invariant level only** — a
separate family where **one physical record = exactly one logical event** (batched/nested/multi-event/
snapshot-container shapes INVALID), whose **Silver identity** is the abstract inherited-fact tuple
**`(artifact-locator concept, physical-record-position concept)`** (artifact-origin/I/O-intrinsic position, never a
runtime counter, never concatenated/hashed), with **Gold** venue id as an **additive overlay** that never replaces
Silver, the **existing single-artifact reader frozen**, and **blind carriage** continued. It is **UNBUILT** and
**designs no field/serialization/reader/runtime**; **S2 identity remains BLOCKED** and **Slice-0B schema remains
BLOCKED** until the family is implemented and ratified as carried evidence; Phase 6.1 remains **incomplete** and
Phase 6.2 **not ready**. **No executable work is authorized.**
