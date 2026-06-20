# Phase 6.1 — S1 Durable Passive Shadow Log Boundary & Planning Charter

> **This is a docs-only conceptual boundary/planning charter.** It conceptually designs the **universal sink
> boundary** that will consume the ratified `S2IdentityWiringCandidate` evidence — **without** any field-level,
> persistence, serialization, or storage-medium design. It **designs and builds nothing**. It authorizes NO
> runtime code, NO tests, NO schema implementation, NO persistence implementation, NO serialization design, NO
> storage-engine decision, NO database/file/table/index design, NO B4 scoring arithmetic, NO S4 global halt
> materialization, NO S5 runner, NO Cell-3 route, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_s1_durable_passive_shadow_log_boundary_charter.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_runtime_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_boundary_contract_charter.md`,
> `docs/handoff/phase6_1_s2_provenance_chain_locks_identity_planning_charter.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `1e63c4f8de303046f74bef055e4bf55fe6817bdf`

---

## 1. Base / Dependency Chain

**Base commit:** `1e63c4f8de303046f74bef055e4bf55fe6817bdf`.

References:

- `…_s1_durable_passive_shadow_log_boundary_charter.md` — first pinned S1 as a universal, append-only, passive,
  identity-deferred observation sink accepting both score and materialized-halt events; `observed_at_epoch_ms` is
  a timestamp, not identity. **This planning charter refines that boundary now that identity evidence exists.**
- `…_s2_identity_wiring_runtime_tdd_closeout_ratification.md` — reclassified S2 to **RUNTIME EVIDENCE RATIFIED**:
  the Silver tuple `(artifact_locator, physical_record_position)` is carried by the ratified, frozen
  `S2IdentityWiringCandidate` (immutable, non-dict; payload forwarded by identity; pass/halt symmetric).
- `…_s2_identity_wiring_boundary_contract_charter.md` — single unpacking point; opaque Silver pair; blind
  carriage; "S2 unblock candidate available" → now ratified runtime evidence.
- `…_s2_provenance_chain_locks_identity_planning_charter.md` — synthetic-identity ban; opaque, S2-owned identity
  slot; reference-preservation ≠ durable identity; pass/halt provenance symmetry; no wall-clock enrichment.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Current State

- **S2 identity wiring: RUNTIME EVIDENCE RATIFIED.** `S2IdentityWiringCandidate` carries the opaque Silver pair as
  ratified runtime evidence, available for future S1/S2 consumption.
- **S1 durable passive shadow log: UNBUILT.** No sink exists yet; the opaque identity slot is fed by ratified
  evidence but not yet **consumed** into a durable record.
- The Option-B reader, `S2IdentityWiringCandidate`, the Phase 5 passive socket, the passive producer, and the
  Master B3 client are **BUILT + RATIFIED and frozen**.
- **Slice-0B field-level schema: BLOCKED** (§6). Phase 6.1 incomplete; Phase 6.2 not ready.

---

## 3. S1 Conceptual Sink Boundary

The S1 durable passive shadow log is, at boundary level only:

- A **universal, append-only, passive observation sink** — a **recorder**, not a participant. It **receives**
  discrete observation events and **retains** them durably; it is the terminal record of passive pipeline
  outcomes.
- A **client/consumer** of upstream ratified evidence. It consumes the `S2IdentityWiringCandidate` evidence (and,
  in future, the B4/S4 event producers) **as frozen dependencies**; it never reshapes them.
- **Not** a producer, scorer, decider, router, filter, gate, or normalizer. It has **no opinion** about the events
  it holds.

This charter fixes the sink's **role and contract**, not its fields, persistence, serialization, or storage
medium (all explicitly deferred — §6, §8).

---

## 4. Strict Identity-Consumption Rule

- **S1 MUST consume the ratified `S2IdentityWiringCandidate` evidence** as the source of an event's identity. The
  opaque Silver pair `(artifact_locator, physical_record_position)` is **borrowed**, carried by reference,
  recorded **as-is**.
- **S1 MUST NOT** invent, hash, derive, normalize, concatenate, cast, generate, or reinterpret identity. **No**
  UUID, `event_id`, `log_id`, hash, counter, timestamp-as-ID, fingerprint, or synthetic key. **No** collapsing of
  the Silver pair into a string or durable generated ID.
- **`observed_at_epoch_ms` remains a timestamp only, never identity** — it may be recorded as provenance context,
  but it is **never** repurposed as the event key.
- S1 holds the identity **opaquely**: it does **not** parse, format, compare lexically, or inspect the Silver pair
  for structure. The pair is a name, carried, not a value computed.

---

## 5. Universal Polymorphic Event-Family Boundary

S1's conceptual event-family shape MUST accommodate, as **equal-peer appended observation events**, **both**:

- **Future B4 passive score events** — a recorded valid passive scoring of a pass handoff (designed nowhere here).
- **Future S4 materialized halt events** — a recorded passive-pipeline halt outcome (designed nowhere here).

Boundary rules:

- **No privileging.** Score is **not** privileged over halt, and halt is **not** privileged over score. Both are
  **first-class observation events** of one universal family: *"an observed passive pipeline outcome."* Neither is
  dropped, hidden, ranked, or reclassified.
- **Heterogeneous append.** The sink holds a heterogeneous, append-only sequence of such events without preferring
  one family.
- **Pass/halt identity symmetry.** Both families carry the **same** opaque Silver-pair identity under the **same**
  rules (consistent with the ratified `S2IdentityWiringCandidate` pass/halt symmetry). A halt event is
  identity-anchored exactly like a score event.
- **No B4/S4 design.** This charter designs **neither** B4 scoring **nor** S4 halt materialization; it only fixes
  that, **once produced**, both are accepted as equally valid events. The mechanism that turns a local
  parse-halt / structural halt into an S4 event remains **separately gated**.

---

## 6. Passivity & Immutability Rules

- **Append-only.** Events are added; the historical sequence is never reordered.
- **No mutation / update / delete.** A recorded event is immutable; no field of a prior event may be changed.
- **No reclassification.** A prior event's family (score vs. halt) may **never** be re-labeled after recording.
- **State-free recording.** The act of recording derives nothing from prior events — no rolling aggregate, no
  cross-event mutation, no "latest-wins"/upsert. Append order is preserved; the sink computes no cross-event
  state.
- **Absolute passivity.** S1 performs **no** routing, ranking, filtering, scoring, actionability, execution
  intent, readiness decision, or any decision. It records; it does not judge. Corrections, if ever needed, would
  be **new append-only events** — but designing any correction event is **out of scope** here.
- **No actionability content.** A shadow log event MUST NOT carry (nor the boundary accept): `edge_direction`,
  staleness policy, capacity activation/`capacity` pass tokens, Shadow Intent, execution intent, routing, sizing,
  order intent, paper/live readiness, or any actionability field. Events are passive observations only.

---

## 7. Opaque Context Preservation (incl. Cell-3 cost contexts)

- Cost contexts — **including** the current **zero-valued / deferred Cell-3** context — must be carried and
  recorded **opaquely**, by reference, exactly as received.
- S1 must **not** inspect, interpret, normalize, score, validate, or derive cost semantics. It does not know what
  a cost context "means"; it records it verbatim as part of the observation.
- **Cell-3 remains deferred / parallel.** This charter neither designs nor requires the real-cost route; the
  minimal zero-valued cost context is recorded opaquely like any other carried context.

---

## 8. Medium / Payload Separation

- **Identity evidence remains separate from payload content.** S1 takes identity **only** from the consumed
  `S2IdentityWiringCandidate` evidence (the opaque Silver pair), **never** from inside the forwarded payload.
- **Payload-authored identity fields must not be trusted or promoted.** Any `event_id`/`row_offset`/`uuid`/`hash`
  field appearing inside a payload is **not** identity; the authoritative identity is always the medium-observed
  Silver pair carried by the evidence.
- S1 consumes the `S2IdentityWiringCandidate` **as evidence, not as payload self-claims** — preserving the
  ratified medium/payload separation and blind-carriage invariants end-to-end.

---

## 9. Slice-0B Gate, Storage-Medium Deferral & Spine Isolation

- **Slice-0B field-level schema remains BLOCKED.** This charter may describe **conceptual event families** (score
  vs. halt) and the **boundary contract**, but **MUST NOT** define any final field-level schema, database schema,
  persistence schema, or serialization schema. **No 0B authorization here.**
- **No storage-medium decision.** This charter does **not** choose, compare, or discuss SQLite, Parquet, JSONL,
  files, databases, tables, indexes, serialization, retention, compaction, or storage engines. The **physical
  persistence medium is deferred to a separate future storage charter.** S1 here is **only** the conceptual sink
  boundary and event-family contract.
- **Existing spine isolation (frozen).** This charter does **not** modify or redesign the Option-B reader,
  `S2IdentityWiringCandidate`, B1/B2/B3, the passive producer, the Phase 5 socket, B4, S4, S5, or any S1 runtime
  (none exists). All existing ratified modules remain **frozen clients/dependencies**. **No** B4/S4/S5 runtime
  readiness is implied.

---

## 10. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 11. Still-Forbidden Work

- **No** identity invented/derived by S1 (UUID/hash/counter/concatenation/timestamp-as-ID/fingerprint/synthetic
  key); **no** collapsing of the Silver pair; **no** `observed_at_epoch_ms` as identity.
- **No** field-level schema, database/persistence/serialization schema, or storage-medium choice/comparison.
- **No** privileging/dropping/ranking/reclassifying of score vs. halt events; **no** B4 scoring arithmetic; **no**
  S4 global halt materialization design.
- **No** routing/ranking/filtering/scoring/actionability/execution/readiness/mutation/update/delete in the sink.
- **No** inspection/interpretation/normalization/validation of cost contexts; **no** Cell-3 route.
- **No** reading identity from / trusting identity in the payload (medium/payload separation).
- **No** modification of the Option-B reader / `S2IdentityWiringCandidate` / B1/B2/B3 / producer / Phase 5 socket /
  B4 / S4 / S5.
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/actionability event content.
- **No** Slice-0B authorization; **no** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no**
  7.x/8.x work.

---

## 12. Next Safe Step

- A **separately-authorized docs-only S1 event-family record-model (Slice-0B field-level) charter** — defining,
  **under this boundary**, the conceptual record fields for **both** score and materialized-halt families
  (consuming the opaque Silver-pair identity evidence), still **designing no persistence/serialization/storage
  medium** — followed, separately, by an **S1 storage-medium charter** that chooses the physical persistence
  mechanism. Both are docs-first and separately gated.
- Resolving S1's record model also unblocks the **S4 exception-routing decision** (how structural/semantic halts
  are materialized into the log) and gives **B4** and a future **S5 runner** a sink.
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency).
- **No implementation is authorized by this charter.** The S1 record model, the storage medium, the Slice-0B
  schema, S4 materialization, B4 scoring, the S5 runner, durable persistence, the Cell-3 route, the Shadow Intent
  Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the S1 durable passive shadow log is conceptually pinned as a **universal, append-only, passive,
identity-borrowing observation sink** that **consumes the ratified `S2IdentityWiringCandidate` evidence** —
recording the **opaque Silver pair `(artifact_locator, physical_record_position)` as-is, never minting or
collapsing identity** (`observed_at_epoch_ms` stays a timestamp) — and accepts **future B4 score events and future
S4 materialized-halt events as equal-peer appended observation events** (neither privileged, both identity-
symmetric), carrying cost contexts (including the deferred zero-valued Cell-3 context) **opaquely**, preserving
**medium/payload separation** (payload-authored identity never trusted), under strict **append-only immutability**
and **absolute passivity**. It is **UNBUILT** and **designs no field/persistence/serialization/storage schema or
medium**; **Slice-0B remains BLOCKED**; the existing reader, `S2IdentityWiringCandidate`, and spine remain
**frozen**; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
