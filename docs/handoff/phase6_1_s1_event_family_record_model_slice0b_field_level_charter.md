# Phase 6.1 — S1 Event-Family Record-Model / Slice-0B Field-Level Charter

> **This is a docs-only logical-record-model charter (Slice-0B field level).** It defines the **storage-agnostic
> logical record model** the S1 passive sink will accept — **conceptual/logical shapes only**, no persistence,
> serialization, or storage medium. It **designs and builds nothing**. It authorizes NO runtime code, NO tests, NO
> database/storage/persistence implementation, NO serialization format, NO SQLite/Parquet/JSONL/files/tables/
> indexes/primary keys, NO B4 scoring arithmetic, NO S4 global halt materialization, NO S5 runner, NO Cell-3
> route, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_s1_durable_passive_shadow_log_boundary_planning_charter.md`,
> `docs/handoff/phase6_1_s1_durable_passive_shadow_log_boundary_charter.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_runtime_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s2_provenance_chain_locks_identity_planning_charter.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `549893d9b069ddd5bbc0164a61d5467d0bea769c`

---

## 1. Base / Dependency Chain

**Base commit:** `549893d9b069ddd5bbc0164a61d5467d0bea769c`.

References:

- `…_s1_durable_passive_shadow_log_boundary_planning_charter.md` — pinned S1 as a universal, append-only, passive
  sink that **consumes the ratified `S2IdentityWiringCandidate` evidence**, accepts score and halt events as
  equal peers, preserves cost contexts opaquely, and keeps medium/payload separation; **Slice-0B was BLOCKED
  pending this charter**.
- `…_s2_identity_wiring_runtime_tdd_closeout_ratification.md` — **RUNTIME EVIDENCE RATIFIED**: the opaque Silver
  pair `(artifact_locator, physical_record_position)` is carried by the frozen, immutable `S2IdentityWiringCandidate`
  (payload forwarded by identity; pass/halt symmetric).
- `…_s2_provenance_chain_locks_identity_planning_charter.md` — synthetic-identity ban; opaque, S2-owned identity
  slot; `observed_at_epoch_ms` is a timestamp, not identity; no wall-clock enrichment.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Current State

- **S2 identity wiring: RUNTIME EVIDENCE RATIFIED** — the Silver pair is available as ratified runtime evidence.
- **S1 sink: UNBUILT** — boundary pinned (planning charter); this charter adds the **logical record model**.
- **Slice-0B: now in scope at the logical/field level** (this charter). It remains **non-executable**: no runtime,
  no persistence, no storage medium, no serialization.
- The Option-B reader, `S2IdentityWiringCandidate`, the Phase 5 passive socket, the passive producer, and the
  Master B3 client are **BUILT + RATIFIED and frozen**. Phase 6.1 incomplete; Phase 6.2 not ready.

---

## 3. Absolute Storage-Agnosticism (governing principle)

This charter defines **only conceptual/logical record shapes** — the *what is recorded*, never the *how/where it
is stored*. It does **not** discuss, choose, compare, optimize, or imply any storage medium. Explicitly **out of
scope and forbidden**: SQLite, Parquet, JSONL, files, databases, tables, indexes, primary keys, serialization,
encoding, retention, compaction, and storage engines. "Field" here means a **logical observation attribute**, not
a column, key, or serialized field.

---

## 4. Common Passive Observation Envelope (logical)

Both record families share a single **common passive observation envelope** — a logical wrapper carrying the
**identity evidence and provenance context**, kept strictly **external to** the family-specific payload:

- **`identity_evidence`** — the ratified `S2IdentityWiringCandidate`, consumed as the **only** identity source. It
  contributes the **opaque, indivisible Silver pair** `(artifact_locator, physical_record_position)`, held by
  reference, recorded as-is. (Top-level evidence metadata — never inside the payload; §6, §7.)
- **`observation_kind`** — a minimal peer-family discriminator distinguishing **SCORE** vs **HALT** as *equal*
  families (a neutral tag, **not** a ranking, priority, severity, or actionability signal). It exists only so the
  sink can hold a heterogeneous append sequence without reclassifying; it confers no precedence.
- **`provenance_timestamp`** — the carried `observed_at_epoch_ms`, **recorded as a timestamp only, never identity**
  (§6). Provenance context; never the event key; never wall-clock-enriched at record time.
- **`opaque_cost_context`** — the carried cost context (including the deferred **zero-valued Cell-3** context),
  held as an **opaque passive context slot** (§8). Never inspected/normalized/scored/validated.
- **`family_payload`** — exactly one of the two family payloads (§5), carrying **only** score content or halt
  content, and **no identity** (§6, §7).

The envelope is the *common* shell; the two families differ only in `family_payload` and `observation_kind`.

---

## 5. Dual-Family Polymorphism (two equal-peer logical records)

Two logical record families share the common envelope as **equal peers** — neither privileged, ranked, filtered,
or treated as secondary:

### 5a. `ObservationScoreRecord` (future B4 passive score output)
- `family_payload` = a **score-content** payload describing a future B4 passive scoring of a pass handoff
  (diagnostic/passive observation content only).
- **Designed nowhere here:** this charter defines **no** B4 scoring arithmetic, no diagnostic-EV formula, and no
  concrete score fields — only that a score-content payload **slot** exists within the common envelope and carries
  **no identity** and **no actionability**.

### 5b. `ObservationHaltRecord` (future S4 materialized halt output)
- `family_payload` = a **halt-content** payload describing a future S4 materialized halt outcome of the passive
  pipeline (passive observation content only).
- **Designed nowhere here:** this charter defines **no** S4 halt materialization, **no** global halt taxonomy, and
  no concrete halt fields — only that a halt-content payload **slot** exists within the common envelope and
  carries **no identity** and **no actionability**.

**Peer equality:** both families are **first-class** appended observation events of one universal family
(*"an observed passive pipeline outcome"*). The sink holds them in a heterogeneous append-only sequence; it never
prefers, ranks, drops, or reclassifies one family. Both carry the **same** opaque Silver-pair identity under the
**same** rules (pass/halt identity symmetry).

---

## 6. No-Bleed Identity Segregation

- The common envelope **MUST consume the ratified `S2IdentityWiringCandidate` as the only identity evidence
  source.** Identity is **top-level evidence/metadata**, external to the payload.
- **Internal score/halt payloads MUST NOT duplicate, absorb, reinterpret, derive, or invent identity.** A
  `family_payload` describes **content only** (score content or halt content); it holds **no** identity.
- **No** UUID, hash, `event_id`, `log_id`, counter, timestamp-as-ID, fingerprint, string concatenation, synthetic
  key, or **payload-authored identity promotion**. Any identity-looking field appearing inside a payload is **not**
  identity and is **never** promoted to the envelope's identity evidence.
- **`observed_at_epoch_ms` remains a timestamp only, never identity.** It is provenance context in
  `provenance_timestamp` and is never repurposed as the event key.

---

## 7. Medium / Payload Separation

- The Silver pair from `S2IdentityWiringCandidate` must remain **opaque and indivisible** — recorded as the two
  separate inherited facts, by reference, never parsed/formatted/compared/collapsed into a key.
- `family_payload` fields may describe **score content or halt content only**.
- The payload **must not contain**: `artifact_locator`, `physical_record_position`, `row_offset`, `read_index`,
  `read_offset`, `event_id`, `log_id`, `record_id`, `message_id`, `sequence_number`, `uuid`, `hash`, `fingerprint`,
  or **any equivalent identity alias**. Identity lives only in `identity_evidence`.

---

## 8. Opaque Context Preservation

- Cost contexts are represented **only** as an **opaque passive context slot** (`opaque_cost_context`), carried
  by reference exactly as received — including the current **zero-valued / deferred Cell-3** context.
- S1 / the record model must **not** inspect, normalize, score, validate, or interpret cost semantics. The slot is
  recorded verbatim; its meaning is not decoded here.
- **Cell-3 remains deferred / parallel.** No real-cost route is designed or required.

---

## 9. Append-Only Semantics

- The record model supports **append-only passive observation**: each record is added once and retained
  immutably.
- **No** update, delete, mutation, reclassification, upsert, aggregation, rolling/derived state, or stateful
  lifecycle fields. There is no "status that changes," no "version," no "supersedes" link, no cross-record
  derivation. Corrections, if ever needed, would be **new appended records** — but designing any correction record
  is **out of scope** here.

---

## 10. Actionability Exclusion

The record model **explicitly excludes** all actionability/intent content. No record (envelope or payload) may
carry: `edge_direction`, `capacity`/capacity activation, `execution_intent`, `routing_intent`, `sizing_intent`,
`order_intent`, `readiness`, `actionability`, trade recommendation, or live/paper execution fields. These are
**passive archival observation records only**. (Tombstones honored: `edge_direction` and `staleness_threshold_ms`
remain tombstoned; capacity remains non-activatable.)

---

## 11. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 12. Storage / Persistence Deferral & Existing-Boundary Isolation

- **No storage/persistence/serialization here.** The physical persistence medium and any serialization/encoding
  are **deferred to a separate future S1 storage-medium charter**. This charter is **purely the logical record
  model** (storage-agnostic, §3).
- **Existing-boundary isolation (frozen).** This charter does **not** modify or redesign `S2IdentityWiringCandidate`,
  the Option-B reader, B1/B2/B3, the passive producer, the Phase 5 socket, B4, S4, S5, or any S1 runtime (none
  exists). All existing ratified modules remain **frozen clients/dependencies**. **No** B4/S4/S5 runtime readiness
  is implied.

---

## 13. Still-Forbidden Work

- **No** storage medium / persistence / serialization / database / table / index / primary-key / retention /
  compaction discussion or design.
- **No** B4 scoring arithmetic / diagnostic-EV / concrete score fields; **no** S4 halt materialization / global
  halt taxonomy / concrete halt fields.
- **No** identity invented/derived/duplicated in the model (UUID/hash/counter/concatenation/timestamp-as-ID/
  fingerprint/synthetic key); **no** payload-authored identity promotion; **no** collapsing of the Silver pair;
  **no** `observed_at_epoch_ms` as identity.
- **No** identity alias in the payload (§7); **no** reading identity from the payload.
- **No** inspection/normalization/scoring/validation/interpretation of cost contexts; **no** Cell-3 route.
- **No** update/delete/mutation/reclassification/upsert/aggregation/lifecycle fields.
- **No** `edge_direction`/capacity/execution/routing/sizing/order/readiness/actionability/trade/live/paper
  content.
- **No** privileging/ranking/filtering of score vs. halt families.
- **No** modification of `S2IdentityWiringCandidate` / Option-B reader / B1/B2/B3 / producer / Phase 5 socket /
  B4 / S4 / S5.
- **No** runtime/persistence implementation; **no** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim;
  **no** 7.x/8.x work.

---

## 14. Next Safe Step

- A **separately-authorized docs-only S1 storage-medium charter** — choosing the physical persistence mechanism
  and any serialization/encoding for this logical model (storage decisions deliberately excluded here) — **and/or**
  an **S1 runtime sink TDD slice** that, **under this logical model and the S1 boundary**, implements the
  append-only passive sink consuming the ratified `S2IdentityWiringCandidate` evidence (still designing no B4/S4).
  Each is separately gated.
- Resolving the record model also unblocks the **S4 exception-routing decision** (how structural/semantic halts
  become `ObservationHaltRecord` payloads) and gives **B4** a target for `ObservationScoreRecord` payloads — both
  **separately gated**.
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency; would populate `opaque_cost_context` with real cost evidence).
- **No implementation is authorized by this charter.** The storage medium, the S1 runtime sink, S4
  materialization, B4 scoring, the S5 runner, durable persistence, the Cell-3 route, the Shadow Intent Envelope,
  capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the S1 logical record model is defined at **Slice-0B field level, storage-agnostically** — a
**common passive observation envelope** (`identity_evidence` from the ratified `S2IdentityWiringCandidate`, a
neutral SCORE/HALT `observation_kind`, a timestamp-only `provenance_timestamp`, an `opaque_cost_context` slot, and
one `family_payload`) shared by **two equal-peer families**, `ObservationScoreRecord` (future B4 score content) and
`ObservationHaltRecord` (future S4 halt content), **neither privileged**. Identity is **borrowed, opaque,
indivisible, and strictly segregated from payload** (no minting, no payload-authored identity, `observed_at_epoch_ms`
stays a timestamp); cost contexts are **opaque** (Cell-3 deferred); records are **append-only and passive** with
**all actionability excluded**. **No storage/persistence/serialization/medium is designed** (deferred to a separate
storage charter); existing modules remain **frozen**; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**.
**No executable work is authorized.**
