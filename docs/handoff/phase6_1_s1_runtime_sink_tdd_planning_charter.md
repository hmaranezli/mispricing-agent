# Phase 6.1 — S1 Runtime Sink TDD Planning Charter (In-Memory Reference)

> **This is a docs-only TDD planning charter.** It conceptually plans a **future in-memory, pure-Python reference
> implementation** of the S1 append-only passive sink — so future B4/S4 contract testing can target S1 behavior
> **without choosing any physical storage medium**. It **designs and builds nothing**: no runtime, no tests, no
> interface code. It authorizes NO runtime code, NO tests, NO schema/runtime/interface edits, NO storage
> implementation, NO database/file/serialization/persistence design, NO B4 scoring arithmetic, NO S4 global halt
> materialization, NO S5 runner, NO Cell-3 route, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_s1_event_family_record_model_slice0b_field_level_charter.md`,
> `docs/handoff/phase6_1_s1_durable_passive_shadow_log_boundary_planning_charter.md`,
> `docs/handoff/phase6_1_s1_durable_passive_shadow_log_boundary_charter.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_runtime_tdd_closeout_ratification.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `4e65f93b68b5ccce72302ba44bb8948faee41541`

---

## 1. Base / Dependency Chain

**Base commit:** `4e65f93b68b5ccce72302ba44bb8948faee41541`.

References:

- `…_s1_event_family_record_model_slice0b_field_level_charter.md` — defined the storage-agnostic logical record
  model: a common passive observation envelope (`identity_evidence` from `S2IdentityWiringCandidate`, neutral
  SCORE/HALT `observation_kind`, timestamp-only `provenance_timestamp`, `opaque_cost_context`, one
  `family_payload`) shared by two equal-peer families **`ObservationScoreRecord`** and **`ObservationHaltRecord`**.
- `…_s1_durable_passive_shadow_log_boundary_planning_charter.md` / `…_boundary_charter.md` — S1 is a universal,
  append-only, passive, identity-borrowing sink; consumes the ratified evidence; storage medium deferred.
- `…_s2_identity_wiring_runtime_tdd_closeout_ratification.md` — **RUNTIME EVIDENCE RATIFIED**: the opaque Silver
  pair is carried by the frozen `S2IdentityWiringCandidate`.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Current State

- **Logical record model: defined** (Slice-0B, storage-agnostic) — two equal-peer families over a common
  envelope.
- **S1 runtime sink: UNBUILT.** No sink exists. This charter **plans** a future in-memory reference sink for
  contract testing; it builds nothing.
- The Option-B reader, `S2IdentityWiringCandidate`, the Phase 5 passive socket, the passive producer, and the
  Master B3 client are **BUILT + RATIFIED and frozen**. Slice-0B logical model exists; **storage medium remains
  undecided**. Phase 6.1 incomplete; Phase 6.2 not ready.

---

## 3. Purpose of the In-Memory Reference Sink

- To give future **B4/S4 contract testing** a concrete S1 **behavioral target** — an executable reference of the
  S1 append-only passive sink **contract** — **without** committing to any physical storage medium.
- It is a **reference/contract double**, not the production durable log. It exists to pin *what S1 does* (accept
  exactly the ratified record families, append-only, immutable readback, identity-borrowing, payload-blind), so
  later producers can be tested against that behavior.
- **Storage-medium decisions remain deferred** to a separate future S1 storage-medium charter. The in-memory
  reference must **not** choose or imply the final medium; an in-memory list is a **test substrate**, never a
  storage-engine choice.

---

## 4. Future Public Interface Constraints (planning only)

When a future TDD slice is authorized, the reference sink's public surface should be **minimal**:

- **One append method** — e.g. `record_observation(record)` — accepting exactly one ratified record (§7) and
  appending it. It returns nothing actionable; it records and is silent about meaning.
- **At most one immutable readback** — e.g. a snapshot accessor returning an immutable copy (§6). Only if tests
  require readback.
- **Nothing else.** No query/filter/search/rank/score/route/decide method; no count-based decisioning; no
  lifecycle/admin surface. The sink is a recorder, not a service.

This charter fixes only the **shape and constraints** of that future surface; it defines **no** signatures, types,
or code.

---

## 5. Append-Only & Anti-Mutation Rules (planning)

- The sink may expose **only a strict append**. **Forbidden:** `pop`, `remove`, `update`, `delete`, `clear`,
  overwrite, arbitrary index assignment, `insert`-at-position, upsert, reclassification, aggregation, sort/reorder,
  or any mutation of already-recorded observations.
- **Append order is preserved** and never reordered. A recorded observation is **immutable**; no field of a prior
  record may be changed.
- **State-free recording.** Appending derives nothing from prior records — no rolling aggregate, no "latest-wins,"
  no cross-record mutation or computed state.
- **Corrections, if ever needed, would be new appended observations** — and remain **out of scope** here (no
  correction/supersession mechanism is designed).

---

## 6. Immutable Readback Lock (planning)

- If the future design needs readback for tests, it may expose **only an immutable snapshot/copy** — e.g.
  `tuple(records)` — never the internal mutable container.
- The sink **must never expose the internal mutable list by reference.** A caller must be unable to append to,
  mutate, reorder, or clear the sink's state via the readback. The snapshot is a detached, immutable view.

---

## 7. Strict Type Enforcement (planning)

- The sink is **not a generic list/collection.** Future `record_observation` must accept **only** the ratified
  passive observation record families from `4e65f93`: **`ObservationScoreRecord`** or **`ObservationHaltRecord`**.
- **Rejected (fail fast):** generic dicts, blobs, payload-only objects, identity-only objects, raw envelopes
  without a family payload, unstructured inputs, and anything that is not one of the two ratified families.
- **Prefer exact type checks** (`type(x) is ObservationScoreRecord` / `type(x) is ObservationHaltRecord`) over
  `isinstance`-style **subclass admission** — consistent with the package's exact-type boundary discipline; a
  subclass of a ratified family is **not** auto-admitted.
- **Equal-peer admission.** Both families are accepted on **equal** footing — neither privileged, ranked, nor
  filtered. The type check **admits**; it does not **judge** content.
- **Designed nowhere here:** **no** B4 score arithmetic and **no** S4 halt taxonomy; the sink only checks *which
  ratified family* a record is, never *what it means*.

---

## 8. Anti-Singleton / Instance Bounding (planning)

- Future sink state must be **instance-bound per pipeline run / per test** — e.g. an instance-bound **private**
  container created fresh per sink instance.
- **Forbidden:** global variables, module-level lists/state, singletons, shared caches, class-level mutable stores,
  or any **cross-test / cross-run state leakage**. Two sink instances share nothing; constructing a new sink yields
  empty, isolated state.

---

## 9. Identity Consumption & Passive Boundary (planning)

### 9a. Identity Consumption
- Future sink records must consume the ratified **`S2IdentityWiringCandidate` evidence through the record
  envelope** (`identity_evidence`). The opaque Silver pair `(artifact_locator, physical_record_position)` is
  recorded **as-is**, by reference.
- The sink must **not** derive, hash, concatenate, cast, normalize, reinterpret, or generate identity. **No**
  UUID, `event_id`, `log_id`, hash, counter, timestamp-as-ID, fingerprint, or synthetic key. **No** collapsing of
  the Silver pair; **`observed_at_epoch_ms` stays a timestamp, never identity.**

### 9b. Passive Boundary
- The sink must **not inspect payload semantics.** **No** B2 normalization, **no** Phase 5 math, **no** B4
  scoring, **no** S4 materialization, **no** routing/actionability/readiness/execution logic.
- **Cost context remains opaque** (recorded verbatim via the envelope's `opaque_cost_context` slot); **Cell-3
  remains deferred / parallel.**
- **Medium/payload separation preserved** — identity comes only from `identity_evidence`; payload-authored
  identity is never trusted or promoted.

---

## 10. Existing-Boundary Isolation

This charter does **not** modify or redesign `S2IdentityWiringCandidate`, the Option-B reader, B1/B2/B3, the
passive producer, the Phase 5 socket, B4, S4, S5, existing docs, or any S1 runtime (none exists). All existing
ratified modules remain **frozen clients/dependencies**. This charter **only plans** the future S1 in-memory sink
TDD slice. **No** B4/S4/S5 runtime readiness is implied.

---

## 11. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 12. Still-Forbidden Work

- **No** runtime/tests/interface code; **no** storage/database/file/serialization/persistence design; **no**
  storage-medium choice or implication.
- **No** sqlite3 / `:memory:` / pandas / numpy / databases / files / `open()` / `os` / `pathlib` / IO libraries /
  storage engines / tables / indexes / serialization mechanics (even for the in-memory reference).
- **No** mutation surface (`pop`/`remove`/`update`/`delete`/`clear`/overwrite/index-assign/upsert/reclassify/
  aggregate); **no** exposure of the internal mutable container.
- **No** admission of non-ratified inputs (dicts/blobs/payload-only/identity-only/unstructured); **no**
  `isinstance` subclass auto-admission; **no** B4 arithmetic / S4 taxonomy.
- **No** global/module/singleton/class-level/shared state; **no** cross-test leakage.
- **No** identity derivation/minting (UUID/hash/counter/concat/timestamp-as-ID/fingerprint/synthetic key); **no**
  Silver-pair collapse; **no** `observed_at_epoch_ms` as identity.
- **No** payload-semantic inspection; **no** B2 normalization / Phase 5 math / B4 / S4 / routing / actionability /
  readiness / execution; **no** cost interpretation; **no** Cell-3 route.
- **No** modification of existing ratified modules/docs.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 13. Next Safe Step

- A **separately-authorized S1 in-memory reference sink TDD slice** — implementing, **strictly under this plan and
  the logical record model**, an instance-bound, pure-Python (native-collection) append-only passive sink that
  accepts only `ObservationScoreRecord` / `ObservationHaltRecord` (exact-type), exposes one append method and at
  most one immutable-snapshot readback, borrows identity from `S2IdentityWiringCandidate` evidence, inspects no
  payload semantics, and shares no global state — test-first, with existing modules frozen, and designing **no**
  storage medium, **no** B4 arithmetic, and **no** S4 materialization.
- Independently/subsequently: a **separate S1 storage-medium charter** (physical persistence/serialization, still
  excluded here); the **S4 exception-routing decision** (how halts become `ObservationHaltRecord`); a **B4 passive
  scoring** slice (producing `ObservationScoreRecord` content); and the **real-cost Cell-3** assembly (populating
  `opaque_cost_context`). Each separately gated.
- **No implementation is authorized by this charter.** The in-memory sink slice, the storage medium, S4
  materialization, B4 scoring, the S5 runner, durable persistence, the Cell-3 route, the Shadow Intent Envelope,
  capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** a future S1 **in-memory, pure-Python reference sink** is planned **for contract testing only** — an
**instance-bound** (no global/singleton/shared state), **native-collection** append-only passive recorder exposing
**one strict append** (`record_observation`) and **at most one immutable-snapshot readback** (never the internal
mutable container), admitting **only** the ratified **`ObservationScoreRecord`/`ObservationHaltRecord`** families by
**exact type** (no dict/blob/identity-only/subclass admission), **borrowing identity** from the
`S2IdentityWiringCandidate` evidence (no minting/collapse; `observed_at_epoch_ms` stays a timestamp), keeping cost
context **opaque** (Cell-3 deferred), and **inspecting no payload semantics** (no B2/Phase 5/B4/S4/actionability).
It **chooses no storage medium** and forbids sqlite/pandas/numpy/files/IO even in-memory; the medium is **deferred**
to a separate storage charter. It is **UNBUILT**; existing modules remain **frozen**; Phase 6.1 remains
**incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
