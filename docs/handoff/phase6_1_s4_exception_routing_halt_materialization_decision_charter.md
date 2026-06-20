# Phase 6.1 — S4 Exception-Routing / Halt-Materialization Decision Charter

> **This is a docs-only decision charter.** It conceptually decides the **S4 halt-materialization boundary**
> that converts an **already-observed** structural halt into one S1-compatible `ObservationHaltRecord` — **without
> implementing it**. It **designs and builds nothing**: no runtime, no tests, no schema, no runner, no halt-payload
> field shape. It authorizes NO runtime code, NO tests, NO schema/runtime/interface edits, NO edits to the Option-B
> reader / `S2IdentityWiringCandidate` / B3 / B4 / the S1 reference sink, NO S5 runner, NO storage-medium/persistence
> design, NO retry/repair/normalization/enrichment, NO Cell-3 route, NO Phase 6.2 work, NO pytest, NO graphify. It is
> subordinate to
> `docs/handoff/phase6_1_b4_passive_scoring_runtime_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s1_in_memory_reference_sink_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s1_event_family_record_model_slice0b_field_level_charter.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_runtime_tdd_closeout_ratification.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `6b26e0537c4e88e06f75cdf1701bfe8c254cf3bf`

---

## 1. Base / Dependency Chain

**Base commit:** `6b26e0537c4e88e06f75cdf1701bfe8c254cf3bf`.

References:

- `…_b4_passive_scoring_runtime_tdd_closeout_ratification.md` — the **pass path** is green: B4 produces
  `ObservationScoreRecord`s the S1 sink admits by exact type. The **halt path** is its missing equal peer; S4
  materializes it. **B4 ≠ S1 sink; S4 ≠ S1 sink** — each produces, S1 records.
- `…_s1_in_memory_reference_sink_tdd_closeout_ratification.md` — the S1 reference sink admits an exact
  `ObservationHaltRecord` (alongside `ObservationScoreRecord`) whose `identity_evidence` is an exact
  `S2IdentityWiringCandidate`; it records and retains, ranking/deciding/normalizing nothing.
- `…_s1_event_family_record_model_slice0b_field_level_charter.md` — the common storage-agnostic envelope
  (`identity_evidence`, `observation_kind`, `provenance_timestamp`, `opaque_cost_context`, `family_payload`);
  `ObservationScoreRecord` and `ObservationHaltRecord` are **two equal-peer families**; identity is **envelope-level
  only**.
- `…_s2_identity_wiring_runtime_tdd_closeout_ratification.md` — **RUNTIME EVIDENCE RATIFIED**: the opaque Silver
  pair `(artifact_locator, physical_record_position)` carried by `S2IdentityWiringCandidate`; **pass and local-halt
  envelopes are handled by the same wiring** and carry the same identity under the same rules (identity-blind).

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Current State

- The passive evaluation spine (Phase 5 socket, passive producer, Master B3), the Option-B reader,
  `S2IdentityWiringCandidate`, the S1 in-memory reference sink, and the B4 passive scorer are **BUILT + RATIFIED and
  frozen**.
- **The pass path is green** (B4 → `ObservationScoreRecord` → S1). **The halt path is UNBUILT.** No component turns
  an already-observed structural halt into an `ObservationHaltRecord`. This charter **decides** the S4 boundary that
  will; it builds nothing.
- The S1 reference sink is the **contract target** S4 will produce halt records for. Storage medium undecided;
  Phase 6.1 incomplete; Phase 6.2 not ready.

---

## 3. S4 Boundary Definition (the Mortician Rule)

S4 is, at boundary level only:

- A **passive, recorder-oriented halt-materialization boundary** — it takes a halt that **some upstream component
  already observed and emitted** and packages it into one `ObservationHaltRecord` for the S1 sink. It is a
  **producer of one record family** (the halt peer), not a participant in execution or recovery.
- **The Mortician Rule (binding).** S4 **records the death; it does not revive the patient.** S4 **MUST NOT** retry,
  re-run, repair, self-heal, recover, re-attempt, normalize, enrich, back-fill, reconstruct, substitute, default,
  or **synthesize any missing data**. It observes that a halt occurred and materializes that observation faithfully
  and passively. A halt is a terminal, passive fact at this boundary; S4 buries it, it does not resurrect it.
- **Not an execution / control boundary.** S4 **must never** emit retries, routes, recoveries, remediations,
  readiness decisions, verdicts, recommendations, severity rankings, sizing, allocation, or any actionability. It
  materializes for the **record**, never for a decision and never for a re-attempt.
- **S4 ≠ S1 sink.** S4 **produces** one halt record; **S1 records it.** S4 does not store, retain, append, or own
  the log; it constructs one record and hands it to the sink. **The runner/orchestration that wires the halt source
  → S4 → S1 is NOT designed here** (§9).

---

## 4. Inputs S4 May Conceptually Consume

S4 consumes **already-observed structural halts only**, treating every upstream object as a **frozen dependency**
carried **by reference and opaquely**:

- An **already-emitted structural halt carrier** — one of the existing, ratified halt facts the passive pipeline
  already produces, e.g.:
  - `OptionBLocalParseHalt` — the Option-B reader's local parse halt for a malformed physical line (reaching S4 as
    the `forwarded_payload_or_local_halt` an `S2IdentityWiringCandidate` already carries);
  - `B3PassiveClientWiringError` — a structural B3 passive-client wiring halt;
  - `BlockedPacket` — a structural passive-producer block.

  S4 **treats the halt carrier as opaque** — it carries it by reference; it does **not** parse, classify by
  meaning, interpret, or repair it.
- The **S2 identity evidence** — the exact `S2IdentityWiringCandidate` carrying the opaque Silver pair, to be placed
  **opaquely** into `identity_evidence` (§5). For a reader-origin parse halt, this is the **same** candidate that
  already carries the malformed line and preserves its locator + position (the ratified pass/halt symmetry).
- **Provenance/context already present** upstream — `observed_at_epoch_ms` (timestamp-only) and the **opaque cost
  context** — carried as passive observation metadata only, never inspected or invented.

Hard limits on consumption:

- S4 **must not** redesign or reach into the Option-B reader, S2 wiring, B3, B4, the passive producer, the Phase 5
  socket, or the S1 sink. It is a **downstream client** of already-emitted halts.
- S4 **must not** re-derive a halt it was not handed, **must not** manufacture a halt where none was observed, and
  **must not** suppress, merge, or reclassify a halt it was handed.
- S4 **must not** consume the **pass** family (`PassiveShadowInput` / valid score outcomes) — those are B4's. S4
  materializes **observed halts only**.

---

## 5. Strict Lineage / Identity Blindness (No Fallback Identity)

- S4 places the **existing** S2 identity evidence into `ObservationHaltRecord.identity_evidence`, **opaquely and by
  reference**. The opaque Silver pair `(artifact_locator, physical_record_position)` remains **indivisible and
  external to the payload**.
- **No fallback identity, ever.** Even though a halt frequently means data is missing or unparsable, S4 **MUST NOT**
  mint, hash, derive, collapse, concatenate, cast, fingerprint, counter, timestamp-as-ID, or otherwise **synthesize
  a substitute identity** when payload content is absent. Identity comes **only** from the already-existing
  `S2IdentityWiringCandidate`. A missing payload never licenses a manufactured key — the Mortician Rule (§3) forbids
  synthesizing the very thing whose absence defines the halt.
- If (hypothetically) no S2 identity evidence exists for a given halt, S4 **does not invent one** — it has no record
  to produce; how an identity-less halt is handled is **out of scope here** and belongs to a later separately-gated
  decision, never to fabrication.
- `provenance_timestamp` is a **timestamp only, never identity**. S4 reads no clock; it carries an already-observed
  timestamp if upstream provided one, and otherwise carries nothing manufactured.

---

## 6. `ObservationHaltRecord` Output Contract (conceptual)

S4 produces records that populate the **ratified common envelope**, with the **halt family** in `family_payload`:

- **`identity_evidence`** — the existing `S2IdentityWiringCandidate`, carried opaquely and by reference (§5).
- **`observation_kind`** — the neutral **HALT** family marker: an **equal-peer** tag beside SCORE, **not** a
  priority, severity, ranking, or actionability signal (§7).
- **`provenance_timestamp`** — an already-observed timestamp if present, **timestamp only, never identity**.
- **`opaque_cost_context`** — the upstream cost context, carried **opaquely**; S4 does not inspect, assemble, or
  invent it. **Cell-3 remains deferred / parallel.**
- **`family_payload`** — the **passive halt-diagnostic content** (conceptual obligations only here, §6a). It carries
  a faithful, passive description of the **observed** halt and **no** retry/route/readiness/verdict/order/execution
  field, **no** identity, **no** recovery instruction, **no** synthesized data.

### 6a. Halt-Payload Passivity (conceptual obligations only)

This charter defines **only conceptual halt-payload obligations** — it does **NOT** finalize the runtime class,
serialization fields, storage columns, database schema, or a halt taxonomy. At conceptual level the halt
`family_payload`:

- May carry the **already-observed halt carrier opaquely by reference** (e.g. the `OptionBLocalParseHalt` /
  `B3PassiveClientWiringError` / `BlockedPacket` object as handed), so a later replay reader can see *that a halt was
  observed and which opaque carrier it was* — never parsed, normalized, or repaired.
- May carry a **passive, non-versioned halt-family descriptor** for replay explainability (i.e. *which family/shape
  of passive halt diagnostic this is*) — **not** a versioned/runtime ID, **not** identity, and **not** a
  severity/priority ranking.
- **Must not** carry retry counts, retry intent, recovery state, remediation, route, readiness, verdict, decision,
  order, sizing, allocation, priority, ranking, severity-as-priority, "should retry," or any actionability.
- **Must not** carry any identity alias (`artifact_locator`, `physical_record_position`, `row_offset`, `read_index`,
  `event_id`, `log_id`, `record_id`, `message_id`, `sequence_number`, `uuid`, `hash`, `fingerprint`, `source_id`,
  or any equivalent) — identity stays envelope-level (§5).
- **Must not** synthesize, default, or back-fill any value the halt itself lacks (§3). The concrete halt-payload
  field shape is a **separate, future, separately-authorized** design (still under the Slice-0B model, no
  persistence).

---

## 7. Peer Symmetry (Equal-Peer, No Privilege)

- `ObservationHaltRecord` is a **first-class, equal peer** of `ObservationScoreRecord` at the S1 sink. **Neither is
  privileged.** A halt is **not** "more urgent," "higher priority," or "more actionable" than a score, and a score
  is not privileged over a halt; both are passive observation events.
- Both families carry the **same opaque Silver-pair identity** under the **same** rules, populate the **same** common
  envelope, and are admitted by the S1 sink by **exact type** with no ordering, ranking, or precedence between them.
- The **HALT** marker introduces **no** severity scale, priority queue, or triage order. Any halt-family descriptor
  (§6a) is replay-explainability only, never a ranking.

---

## 8. Frozen-Upstream Seal

- The Option-B reader, `OptionBLocalParseHalt`, `S2IdentityWiringCandidate`, B3 (`B3PassiveClientWiringError`,
  `BlockedPacket`), B4, and the S1 reference sink remain **BUILT + RATIFIED and frozen**. S4 is a **pure downstream
  client**: it imports/consumes their outputs as frozen dependencies and **modifies, widens, wraps, or reshapes
  none of them**.
- S4 introduces **no** change to any existing module, contract, signature, or behavior. This decision charter
  changes **no** code at all.

---

## 9. S5 Isolation (Runner NOT Designed Here)

- This charter does **NOT** design or implement the **S5 runner** and decides **no** orchestration. It does not
  decide *how* an upstream halt is detected, dispatched, looped over, batched, or routed to S4, nor how S4's output
  reaches the S1 sink. That wiring (reader → S2 → {B4 | S4} → S1, routing both families) is the S5 runner's job and
  is **separately gated**.
- S4 is defined **only** as the **boundary** that converts one already-observed halt into one `ObservationHaltRecord`.
  Selection, dispatch, looping, scheduling, and pass/halt branching belong to the future runner, **not** S4.

---

## 10. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated." Halts are **not** capacity decisions and confer no capacity meaning.

---

## 11. Still-Forbidden Work

- **No** retry/repair/recovery/self-heal/re-attempt/remediation; **no** normalization/enrichment/back-fill/
  reconstruction/substitution/defaulting; **no** synthesizing missing data (Mortician Rule, §3).
- **No** orders/routes/recommendations/readiness/verdicts/severity-priority/sizing/allocation/ranking/actionability;
  **no** "should retry"/"should trade" implication anywhere in the record.
- **No** identity minting/derivation/collapse/fallback (UUID/hash/counter/concat/timestamp-as-ID/fingerprint/
  synthetic key); **no** identity in/from the payload; **no** `provenance_timestamp` as identity (§5).
- **No** parsing/classifying-by-meaning/interpreting/repairing the opaque halt carrier; **no** halt taxonomy or
  severity scale; **no** manufacturing or suppressing a halt.
- **No** consumption of the pass family / valid score outcomes by S4; **no** B4 overlap.
- **No** redesign of / reach-back into the Option-B reader, S2 wiring, B3, B4, the passive producer, the Phase 5
  socket, or the S1 sink; **no** mutation/widening/wrap of any frozen upstream (§8); **no** S4-as-sink.
- **No** Cell-3 inspection/assembly/invention; **no** cost-context interpretation.
- **No** randomness/clock/network/filesystem/external-state/cache/global/async/hidden state; **no** non-determinism.
- **No** finalized runtime class / serialization fields / storage columns / database schema / persistence format.
- **No** S5 runner / orchestration (§9); **no** storage medium / durable persistence.
- **No** lock-test edit; **no** new allowlist; **no** weakening of any guardrail.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Next Safe Step

- A **separately-authorized docs-only S4 halt-payload field-shape charter** — defining, **under the Slice-0B model
  and this decision**, the conceptual `family_payload` obligations of the halt family (passive halt diagnostics
  only; opaque carrier by reference; non-versioned halt-family descriptor; no retry/route/readiness/identity/
  actionability), still designing no runtime class, serialization, or storage — followed by a
  **separately-authorized S4 halt-materialization runtime TDD slice** that consumes an already-observed halt + the
  existing `S2IdentityWiringCandidate`, carries identity opaquely at the envelope level, and constructs one
  `ObservationHaltRecord` for the S1 reference sink (Mortician Rule honored; no retry/repair; no S5 runner; no
  storage), handling any runtime halt-name lock collision via its own separately-authorized exception if one
  appears.
- Independently/subsequently: the **S5 runner** (orchestration that wires reader → S2 → {B4 | S4} → S1 and routes
  both families); the **S1 storage-medium** charter; and the **real-cost Cell-3** assembly. Each separately gated.
- **No implementation is authorized by this charter.** The S4 field-shape, the S4 runtime slice, the S5 runner, the
  storage medium, durable persistence, the Cell-3 route, the Shadow Intent Envelope, capacity activation, Phase 6.2,
  and 7.x/8.x remain separately gated.

**Conclusion:** S4 is decided as a **passive, recorder-oriented halt-materialization boundary** that takes one
**already-observed** structural halt (`OptionBLocalParseHalt` / `B3PassiveClientWiringError` / `BlockedPacket`,
carried **opaquely by reference**) plus the **existing** `S2IdentityWiringCandidate` identity evidence and produces
**one** `ObservationHaltRecord` (passive halt-diagnostic `family_payload`; neutral **HALT** `observation_kind`;
timestamp-only `provenance_timestamp`; opaque `opaque_cost_context`; **opaque, indivisible, payload-external**
identity) **for** the ratified S1 reference sink — under the **Mortician Rule** (records the halt; **never** retries,
repairs, self-heals, normalizes, enriches, back-fills, or synthesizes missing data), with **strict lineage** (no
minted/fallback identity, ever), **payload passivity** (no retry/route/readiness/verdict/order/execution field),
**equal-peer symmetry** with `ObservationScoreRecord` (no priority/ranking/severity/actionability), and **frozen
upstream** (reader/S2/B3/B4/S1 unchanged). **S4 ≠ S1 sink** — it produces, S1 records. The **S5 runner is NOT
designed here**. It is **UNBUILT** and **designs no class/schema/runtime/storage/field-shape/taxonomy**; existing
modules remain **frozen**; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable work is
authorized.**
