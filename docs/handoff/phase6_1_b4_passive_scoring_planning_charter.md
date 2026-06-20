# Phase 6.1 — B4 Passive Scoring Planning Charter

> **This is a docs-only planning charter.** It conceptually defines the **passive scoring boundary** that will
> transform already-built passive pipeline outputs into `ObservationScoreRecord` records for the S1 in-memory
> reference sink — **without implementing it**. It **designs and builds nothing**: no runtime, no tests, no
> schema, no runner. It authorizes NO runtime code, NO tests, NO schema/runtime/interface edits, NO runner
> implementation, NO S4 halt materialization, NO S5 runner, NO storage-medium/persistence design, NO trade
> execution/routing/sizing/order/readiness/actionability, NO Cell-3 route, NO Phase 6.2 work, NO pytest, NO
> graphify. It is subordinate to
> `docs/handoff/phase6_1_s1_in_memory_reference_sink_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s1_event_family_record_model_slice0b_field_level_charter.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_runtime_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_remaining_runtime_scope_readiness_reclassification_audit.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `48a6ea2ae42c0ebed675c0f85791d22f4e335bd7`

---

## 1. Base / Dependency Chain

**Base commit:** `48a6ea2ae42c0ebed675c0f85791d22f4e335bd7`.

References:

- `…_s1_in_memory_reference_sink_tdd_closeout_ratification.md` — ratified the S1 reference sink and its two
  equal-peer DTO families; B4 is now **architecturally eligible** (a sink target exists) but **not authorized**.
- `…_s1_event_family_record_model_slice0b_field_level_charter.md` — the storage-agnostic logical record model:
  common envelope (`identity_evidence`, `observation_kind`, `provenance_timestamp`, `opaque_cost_context`,
  `family_payload`) + `ObservationScoreRecord` / `ObservationHaltRecord`.
- `…_s2_identity_wiring_runtime_tdd_closeout_ratification.md` — **RUNTIME EVIDENCE RATIFIED**: the opaque Silver
  pair carried by `S2IdentityWiringCandidate`; pass/halt symmetric; identity-blind.
- `…_remaining_runtime_scope_readiness_reclassification_audit.md` — B4 consumes the **pass handoff only**
  (`PassiveShadowInput`), produces passive score observations, **must not** consume halt carriers; **B4 ≠ log**.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Current State

- The passive evaluation spine (Phase 5 passive socket, passive producer, Master B3), the Option-B reader,
  `S2IdentityWiringCandidate`, and the S1 in-memory reference sink are **BUILT + RATIFIED and frozen**.
- **B4 passive scoring: UNBUILT.** No scorer exists. This charter **plans** the B4 boundary; it builds nothing.
- The S1 reference sink is the **contract target** B4 will produce records for. **Slice-0B** logical model exists;
  storage medium undecided. Phase 6.1 incomplete; Phase 6.2 not ready.

---

## 3. B4 Passive Boundary Definition

B4 is, at boundary level only:

- A **passive, recorder-oriented scoring boundary** — it observes an already-evaluated passive pipeline outcome
  and produces a **diagnostic, passive score observation** as an `ObservationScoreRecord`-compatible record for the
  S1 sink. It is a **producer of one record family**, not a participant in execution.
- **Not an execution boundary.** B4 **must never** emit orders, routes, recommendations, readiness decisions,
  verdicts, trade candidates, sizing, allocation, or any actionability. It scores for the **record**, never for a
  decision.
- **B4 ≠ S1 sink.** B4 **produces** a record; **S1 records it.** B4 does not store, retain, append, or own the
  log; it constructs one record and hands it to the sink (the runner/orchestration that wires B4→S1 is **not**
  designed here).

---

## 4. Inputs B4 May Conceptually Consume

B4 consumes **existing passive pipeline output only**, treating all upstream objects as **frozen dependencies**:

- The **pass handoff** — the `PassiveShadowInput` (which references the Phase 5 `NetEdgeCalculationResult` by
  identity), i.e. the already-computed passive net-edge math. B4 **reads** this evaluated outcome; it does **not**
  recompute Phase 5 math.
- The **S2 identity evidence** — the `S2IdentityWiringCandidate` carrying the opaque Silver pair, to be placed
  **opaquely** into `identity_evidence` (§5).
- **Provenance/context already present** in upstream passive data — venue, pair, `observed_at_epoch_ms`
  (timestamp-only), and the **opaque cost context** — carried as passive observation metadata only.

Hard limits on consumption:

- B4 **must not** redesign or reach into B1/B2/B3, the passive producer, the Phase 5 socket, the S2 wiring, or the
  S1 sink. It is a **downstream client**.
- B4 **must not** reach backward into B2 to **perform normalization** — normalization is B2's, already done. B4
  consumes normalized/evaluated outputs; it does not normalize.
- B4 **must not** consume **halt carriers** (`BlockedPacket` / structural halts) — those belong to the future S4
  halt family (§9). B4 scores **valid passive pass results only**.

---

## 5. `ObservationScoreRecord` Output Contract (conceptual)

B4 produces records that populate the ratified common envelope, with the **score family** in `family_payload`:

- **`identity_evidence`** — the `S2IdentityWiringCandidate`, carried **opaquely and by reference**. The opaque
  Silver pair `(artifact_locator, physical_record_position)` remains **indivisible and external to the payload**;
  B4 never reads identity from, or writes identity into, `family_payload`.
- **`observation_kind`** — the neutral SCORE tag (an equal-peer family marker, not a ranking/priority/actionability
  signal).
- **`provenance_timestamp`** — the carried `observed_at_epoch_ms`, **timestamp only, never identity**.
- **`opaque_cost_context`** — the upstream cost context, carried **opaquely** (§6); B4 does not inspect or invent
  it.
- **`family_payload`** — the **passive, diagnostic score content** (conceptual only here). It carries an
  observation of the already-evaluated passive outcome (e.g. a diagnostic passive value derived purely from
  upstream passive math) and **no** actionability, **no** identity, **no** decision.

**Boundary rules:** this charter defines **only conceptual score payload obligations** — it does **NOT** finalize
runtime classes, serialization fields, storage columns, or database schema. B4 builds an `ObservationScoreRecord`;
S1 admits and records it (exact-type). The concrete `family_payload` field shape is a **separate, future**
design (still under the Slice-0B model, no persistence).

---

## 6. Deterministic Math Constraints

Any future B4 score calculation must be **pure, stateless, and deterministic**:

- **Determinism.** The same input *I* must always produce the same score *S*. No input-independent variation.
- **Purity / statelessness.** **No** randomness, clock/`time`/`datetime`, network, filesystem, environment,
  external state, caches, memoization, mutable globals/module state, class-level mutable stores, async/event-loop,
  or any hidden state. One invocation = one isolated, reproducible computation over its inputs.
- **Replay-stable.** Re-scoring the same upstream passive outcome yields the identical score observation
  (consistent with the replay-first discipline of the passive pipeline).
- **No thresholding into actionability.** B4 may produce a diagnostic score *value*; it **must not** threshold,
  rank, gate, or convert that value into a decision, readiness, verdict, or actionability. Any "is this good
  enough" judgment is **out of scope and forbidden** here.
- **Designed nowhere here:** this charter fixes the **constraints**, not the formula. No concrete score arithmetic,
  diagnostic-EV formula, or numeric method is defined.

---

## 7. Identity, Cost & Pair Passivity Rules

### 7a. Identity Blindness
- B4 preserves the S2 identity evidence **opaquely** through `ObservationScoreRecord.identity_evidence`. **No**
  UUID, hash, `event_id`, `log_id`, counter, timestamp-as-ID, fingerprint, string concatenation, synthetic key,
  identity cast, normalization, derivation, or fallback. The Silver pair stays **indivisible and external to the
  payload**.

### 7b. Cost Context Integrity
- Cost context remains **opaque metadata**. **Cell-3 remains deferred / parallel.** B4 may conceptually depend on
  **already-provided numeric cost effects only if** they are present in upstream passive math outputs (i.e. the
  net-edge result already reflects them); B4 **must not** inspect, mutate, normalize, or invent Cell-3 context,
  and **must not** open Cell-3 assembly here.

### 7c. Pair / Venue Agnosticism
- B4 **must not hard-code** BTC/USDT or any single pair, and **must not** design multi-pair orchestration. Pair and
  venue, if present in upstream passive data, are carried as **passive observation metadata only**.
- Pair selection, batching, looping, portfolio routing, and multi-pair scheduling belong to a **future runner /
  orchestration**, **not** B4. B4 scores **one** passive outcome into **one** record.

---

## 8. Score Payload Boundary (restated)

- This charter defines **only conceptual score payload obligations** — passive, diagnostic, identity-blind,
  actionability-free. It does **not** finalize runtime classes, serialization fields, storage columns, or database
  schema.
- **B4 is not the S1 sink.** B4 **produces** a record **for** S1; **S1 records it.** The two boundaries stay
  separate: B4 scores and constructs; S1 admits (exact-type) and retains.

---

## 9. S4 / S5 Isolation

- This charter does **NOT** design S4 exception-routing or global halt materialization, and does **NOT** design
  the S5 runner.
- **Halt records remain an equal-peer future family.** The `ObservationHaltRecord` family stays a first-class peer
  of the score family at the S1 sink; B4 must remain **compatible** with that symmetry (B4 produces score records
  only; halts are S4's), but **no** halt materialization is implemented or planned here beyond preserving
  compatibility. B4 **must not** consume or emit halt carriers.

---

## 10. Pass / Halt & Sink Compatibility

- B4's score records and the future S4 halt records are **equal-peer** observation events at the S1 sink; neither
  is privileged. Both carry the **same** opaque Silver-pair identity under the **same** rules.
- B4 targets the **ratified S1 reference sink** as its contract surface for testing; it relies on the sink's
  **exact-type admission** (a B4-produced `ObservationScoreRecord` is admitted; nothing else is smuggled).

---

## 11. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read
as "capacity validated."

---

## 12. Still-Forbidden Work

- **No** orders/routes/recommendations/readiness/verdicts/trade-candidates/sizing/allocation/actionability; **no**
  thresholding into a decision.
- **No** redesign of / reach-back into B1/B2/B3, the passive producer, the Phase 5 socket, the S2 wiring, or the
  S1 sink; **no** normalization in B4; **no** Phase 5 recomputation.
- **No** consumption of halt carriers (`BlockedPacket`/structural halts) by B4.
- **No** identity minting/derivation/collapse (UUID/hash/counter/concat/timestamp-as-ID/fingerprint/synthetic
  key); **no** identity in/from the payload; **no** `provenance_timestamp` as identity.
- **No** Cell-3 inspection/mutation/invention/assembly; **no** cost-context interpretation.
- **No** randomness/clock/network/filesystem/external-state/cache/global/async/hidden state; **no** non-determinism.
- **No** hard-coded pair/venue; **no** multi-pair orchestration/batching/looping/scheduling/portfolio routing.
- **No** finalized runtime classes / serialization fields / storage columns / database schema; **no** B4-as-sink.
- **No** S4 exception-routing / halt materialization; **no** S5 runner; **no** storage medium / persistence.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 13. Next Safe Step

- A **separately-authorized docs-only B4 score-payload field-shape charter** — defining, **under the Slice-0B
  model and this plan**, the conceptual `family_payload` obligations of the score family (still designing no
  runtime class, serialization, or storage) — followed by a **separately-authorized B4 passive scoring runtime TDD
  slice** that consumes the frozen pass handoff, carries S2 identity opaquely, computes a pure/deterministic
  diagnostic score, and constructs an `ObservationScoreRecord` for the S1 reference sink (no actionability, no S4,
  no runner).
- Independently/subsequently: the **S4 exception-routing decision** (halt → `ObservationHaltRecord`); the **S5
  runner** (orchestration that wires reader → S2 → B4 → S1 and routes both families); the **S1 storage-medium**
  charter; and the **real-cost Cell-3** assembly. Each separately gated.
- **No implementation is authorized by this charter.** The B4 field-shape, the B4 runtime slice, S4
  materialization, the S5 runner, the storage medium, durable persistence, the Cell-3 route, the Shadow Intent
  Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** B4 is conceptually pinned as a **passive, recorder-oriented scoring boundary** that consumes the
**frozen pass handoff** (`PassiveShadowInput` → already-computed Phase 5 net-edge math) and the
`S2IdentityWiringCandidate` identity evidence, and produces **one** `ObservationScoreRecord` (passive, diagnostic
`family_payload`; SCORE `observation_kind`; timestamp-only `provenance_timestamp`; opaque `opaque_cost_context`;
**opaque, indivisible, payload-external** identity) **for** the ratified S1 reference sink — **never** emitting
orders/routes/recommendations/readiness/verdicts/sizing/actionability, **never** thresholding into a decision,
under **pure/stateless/deterministic** math (no randomness/clock/network/filesystem/state), **pair/venue-agnostic**
(no hard-coded pair, no multi-pair orchestration), **identity-blind** (no minting), with **cost context opaque**
(Cell-3 deferred) and **halts left as an equal-peer S4 family** (not consumed or designed here). **B4 ≠ S1 sink**;
it produces, S1 records. It is **UNBUILT** and **designs no class/schema/runtime/storage**; existing modules remain
**frozen**; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
