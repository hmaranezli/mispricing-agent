# Phase 6.1 S1 — Durable Passive Shadow Log Boundary Charter

> **This is a docs-only boundary charter.** It conceptually defines the **structural boundary and event-family
> shape** of the final durable passive shadow log **sink** — **not** a field-level persistence schema, **not** a
> storage/serialization design. It **designs and builds nothing**. It authorizes NO runtime, NO tests, NO
> lock-test edits, NO database/file/storage implementation, NO serialization format, NO schema fields, NO S4
> exception logic, NO B4 scoring, NO S5 runner, NO Cell-3 route, NO Phase 6.2 work, NO pytest, NO graphify. It is
> subordinate to `docs/handoff/phase6_1_remaining_runtime_scope_readiness_reclassification_audit.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`,
> `docs/handoff/phase6_1_master_b3_client_wiring_tdd_closeout_ratification.md`,
> `docs/handoff/phase5_to_live_canary_roadmap.md`, and `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `4a602c668c809e9f7cdfbca6785ac7d987b8ba59`

---

## 1. Base / Dependency Chain

**Base commit:** `4a602c668c809e9f7cdfbca6785ac7d987b8ba59`.

References:

- `…_remaining_runtime_scope_readiness_reclassification_audit.md` — named **S1 (durable passive shadow log)** the
  keystone/completion gate; **S4** halt materialization DEFERRED pending this log architecture; **B4 ≠ log**.
- `…_shadow_scoring_tdd_planning.md` — B4 produces `ShadowObservation`/`ShadowScore` (durable, passive); replay-
  first; Slice 0B = durable passive shadow artifact; Slice 0C = provenance chain locks.
- `…_master_b3_client_wiring_tdd_closeout_ratification.md` — B3 structural halt = typed
  `B3PassiveClientWiringError`; producer semantic/math halt = `BlockedPacket` (forwarded by identity).

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Why This Charter Exists

The remaining-scope audit made the durable passive shadow log the keystone: Phase 6.1 completion is defined by
producing durable, replayable shadow logs, and the S4 exception-routing decision is gated on the log's record
model. This charter fixes, at the **structural-boundary level only**, what kind of **sink** the log is and what
**event families** it must accommodate — so later slices (the field-level 0B schema, S2 identity, S4
materialization, B4 scoring, S5 runner) are constrained without being designed here. It defines a boundary, not a
schema.

---

## 3. Scope — Boundary & Event-Family Only

- **In scope:** the conceptual role of the log as a **universal, append-only, passive sink**; the **event-family
  taxonomy** it must accommodate; the immutability/passivity/identifier-deferral invariants the boundary must
  enforce.
- **Out of scope (designed nowhere here):** concrete schema fields, persistence/storage mechanics, serialization
  format, S4 exception-catching logic, B4 scoring arithmetic, the S5 runner, S2 identity derivation, and the
  Cell-3 route.

---

## 4. Sink Role Classification

The S1 log is classified as a **durable, append-only, passive observation sink** — a **recorder**, not a
participant. It is the terminal record of passive pipeline outcomes; it **receives** discrete observation events
and **retains** them durably and replayably. It is **not** a producer, scorer, decider, router, filter, or gate.
Per **B4/Log Separation**: B4 (and any future producer) **emits** events *to* the sink; the sink itself
**scores/ranks/filters/thresholds/decides nothing** (§8). The sink has no opinion about the events it holds.

---

## 5. Universal Sink — Event-Family Shape

The sink's conceptual event-family shape MUST accommodate, as **equally valid, discrete observation events**,
**both** of the following — neither privileged, neither dropped:

- **Successful passive score events** — the future B4 output (`ShadowObservation`/`ShadowScore`), recording a
  valid passive scoring of a pass handoff.
- **Materialized halt events** — the future S4 output, recording that the passive pipeline produced a halt rather
  than a score.

Both are **first-class observation events** of one universal event family: *"an observed passive pipeline
outcome."* A halt is **not** an error-to-be-hidden at the sink; it is a recorded outcome of equal standing to a
score. The sink must be able to hold a heterogeneous, append-only sequence of such events without reclassifying,
ranking, or preferring one family over another.

---

## 6. Halt Event-Family Taxonomy (conceptual only)

Within the **materialized halt** event family, two **conceptual sub-families** are distinguished (taxonomy only —
**no** catching/materialization mechanism is chosen here):

- **Structural-halt events** — outcomes originating in B3's structural/extraction domain (the typed
  `B3PassiveClientWiringError` domain: non-material input, missing/ambiguous `GROSS_EDGE` binding, non-canonical
  epoch). *Error-domain separation (ratified): these are B3-owned structural halts.*
- **Semantic/math-halt events** — outcomes originating in the producer's Phase 5 math domain (`BlockedPacket` /
  defensive math carriers: e.g. incompatible units). *These are producer-owned semantic/math halts, forwarded by
  B3 by identity.*

**Halt Boundary lock (honored):** S1 may classify these two halt families **conceptually**, but it **MUST NOT**
choose, design, or imply **how** `B3PassiveClientWiringError` is caught, converted, or materialized into a halt
event. That mechanism is S4's, gated on this log architecture and on the S4 exception-routing decision (Option
A/B/C of the remaining-scope audit, still DEFERRED). The sink only specifies that, **once materialized by S4**,
both halt sub-families are accepted as equally valid events.

---

## 7. Immutability / Append-Only Invariant

The boundary must strictly enforce **append-only, state-free** semantics:

- **Append-only.** Events are added; the historical sequence is never reordered.
- **No update / delete / mutation.** A recorded event is immutable; no field of a prior event may be changed.
- **No reclassification.** A prior event's family (score vs. structural-halt vs. semantic-halt) may **never** be
  re-labeled after recording.
- **State-free recording.** The act of recording derives nothing from prior events — no rolling aggregate, no
  cross-event mutation, no "latest-wins"/upsert. (Append order is preserved, but the sink computes no cross-event
  state; consistent with the stateless discipline of the upstream passive pipeline.)

Corrections, if ever needed, are **new append-only events**, never edits — but designing any correction event is
**out of scope** here.

---

## 8. B4 / Log Separation (boundary restatement)

B4 is a **future producer of score events**, **not** the log. The sink **must not** score, rank, filter,
threshold, decide, or gate. It accepts events from producers (B4 for scores; S4 for materialized halts) and
retains them. Any scoring/diagnostic-EV math lives in B4 (designed nowhere here); any halt materialization lives
in S4 (designed nowhere here). The sink is inert with respect to event meaning.

---

## 9. Absolute Passivity — Forbidden Event Content

The event boundary MUST explicitly **reject** any actionability/intent content. A shadow log event MUST NOT carry
(nor the boundary accept): `edge_direction`, capacity activation/`capacity` pass tokens, Shadow Intent, execution
intent, routing, sizing, order intent, paper/live readiness, or any actionability field. Events are **passive
observations only**. (Tombstones honored: `edge_direction` and `staleness_threshold_ms` remain tombstoned;
capacity remains non-activatable; Cell-3 remains deferred/parallel; Phase 6.2 remains not ready.)

---

## 10. Identifier Deferral Lock

S1 **MUST NOT** invent or define: UUIDs, hashes, event IDs, sequence numbers, canonical serialization, or any
uniqueness/identity formula. **`observed_at_epoch_ms` is an observation timestamp, NOT a unique identifier** and
must not be repurposed as one. The boundary may, at most, require **future-compatibility** with an **opaque,
S2-owned deterministic provenance/event-identity reference** — held by reference, never derived, parsed, or
formatted here. **All identity derivation belongs strictly to S2 (Provenance Chain Locks)**; this charter neither
performs nor presupposes it.

---

## 11. Still-Forbidden Work

- **No** concrete schema fields, storage/persistence mechanism, database/file, or serialization format.
- **No** event-ID/UUID/hash/canonical-serialization/uniqueness formula; **no** repurposing of `observed_at_epoch_ms`
  as identity.
- **No** S4 exception-catching/materialization logic; **no** choice of how `B3PassiveClientWiringError` is caught.
- **No** B4 scoring/diagnostic-EV/ranking/threshold; **no** S5 runner; **no** Cell-3 route.
- **No** scoring/filtering/deciding/gating in the sink; **no** mutation/update/delete/reclassification of events.
- **No** `edge_direction`/capacity/Shadow Intent/execution/routing/sizing/actionability event content.
- **No** reopening of `edge_direction`/`staleness_threshold_ms`/cost vocabulary; **no** capacity activation; **no**
  weakening of B3/producer/Phase 5/B2 invariants.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Next Safe Step

- A **separately-authorized docs-only Slice-0B field-level schema charter** — defining, under this boundary, the
  concrete passive shadow event record fields (for both score and materialized-halt families), still **designing
  no persistence/serialization** until separately authorized — and a **separate S2 Provenance Chain Locks**
  charter to own the opaque event-identity reference (§10).
- Only after the record model exists may the **S4 exception-routing decision** (Option A/B/C) and the **B4
  scoring** and **S5 runner** slices be separately chartered.
- The **real-cost Cell-3 cost-context assembly** may be separately authorized at any time (parallel; Phase-6.2
  fidelity dependency).
- **No implementation is authorized by this charter.** The 0B schema, S2 identity, S4 materialization, B4
  scoring, S5 runner, durable persistence, the Cell-3 route, the Shadow Intent Envelope, capacity activation,
  Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** S1 is conceptually pinned as a **universal, append-only, passive, identity-deferred observation
sink** that accepts both score and materialized-halt events as equally valid; it is **UNBUILT** and **designs no
schema/persistence/identity**. Phase 6.1 remains **NOT complete**; Phase 6.2 remains **NOT ready**. No executable
work is authorized.
