# Phase 6.1 S2 — Provenance Chain Locks & Identity Planning Charter

> **This is a docs-only planning charter.** It defines the **provenance and identity locks** that must govern the
> future S1 durable passive shadow log **before** any Slice-0B field-level schema work is allowed. It **designs
> and builds nothing**, and it **invents no identity**. It authorizes NO runtime, NO tests, NO lock-test edits, NO
> Python, NO imports, NO schema/runtime/interface edits, NO log field-level schema, NO persistence/storage/
> serialization design, NO B4 scoring, NO S4 exception-catching/materialization, NO S5 runner, NO Cell-3 route,
> NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_s1_durable_passive_shadow_log_boundary_charter.md`,
> `docs/handoff/phase6_1_remaining_runtime_scope_readiness_reclassification_audit.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `cd8a63c7d29eca3fe40f08b88a88e307b3f34a75`

**External review note:** Gemini Red-Team / Quant Architecture verdict — S1 charter **APPROVED**; immediate
Slice-0B field-level schema **REJECTED**; **re-ordering required** so that S2 provenance/identity locks **precede**
any field-level schema charter. This charter is that S2 step.

---

## 1. Base / Dependency Chain

**Base commit:** `cd8a63c7d29eca3fe40f08b88a88e307b3f34a75`.

References:

- `…_s1_durable_passive_shadow_log_boundary_charter.md` — pinned S1 as a universal, append-only, passive,
  **identity-deferred** sink; required future-compatibility with an **opaque, S2-owned** provenance/event-identity
  reference; **`observed_at_epoch_ms` is a timestamp, NOT identity**.
- `…_remaining_runtime_scope_readiness_reclassification_audit.md` — S1 keystone; S2 provenance chain locks
  (Slice 0C-adjacent) outstanding; B4 ≠ log.
- `…_shadow_scoring_tdd_planning.md` — provenance chain: replay snapshot → normalized evidence → Phase 5 gate →
  shadow record; replay-first.

**No capacity validation and no capacity pass is claimed by this charter** (see §8).

---

## 2. Why S2 Precedes Slice-0B Schema

A field-level shadow-log schema (Slice 0B) cannot be defined responsibly until it is settled **what identity each
log event carries** and **how provenance is preserved unbroken** from the replay source through to the sink. If
0B were designed first, it would be forced to invent an `event_id`/identity field (synthetic identity, §4) or to
mis-promote a timestamp/`id()` into a durable key — exactly the failure mode the S1 identifier-deferral lock
guards against. Identity and chain-of-custody are therefore **logically prior** to fields. Per the external
re-ordering verdict, this charter fixes the **provenance/identity boundary** so the later 0B schema is
constrained, not improvised. It defines locks, not a schema, and **fills no identity slot**.

---

## 3. Provenance vs. Identity — Terminology

Two distinct concepts, deliberately separated:

- **Provenance (chain-of-custody).** The unbroken lineage of *where an observation came from and how it traveled*
  across boundaries (replay snapshot → B2 normalized evidence → B3/Phase-5 gate → producer result → B4 score / S4
  materialized halt → S1 sink). Provenance answers *"what produced this event, through which boundaries."*
- **Identity (the durable event reference).** A single, durable, replay-stable reference that names *which event
  this is*, distinct from any other recorded event. Identity answers *"which event is this."*

These are **not** the same: an event has provenance (a lineage) **and** an identity (a name). This charter governs
the **locks** around both; it **does not derive** either. Critically, **provenance is not a substitute for
identity, and a timestamp/position is not an identity** (§4).

---

## 4. Synthetic Identity Bans

S2 **explicitly bans inventing identity by formula**. The following are **forbidden** as event/log identity,
now and in the future 0B/identity slice, unless a later, separately-authorized identity charter ratifies an
authoritative source:

- **`uuid` / `uuid4` / random UUIDs**, `random`/PRNG numbers, nonces.
- **`hashlib` / SHA / MD5 / any hash** of fields or payloads as an identity key.
- **Counters / sequence numbers / auto-increment** invented at the sink.
- **String concatenation** of fields into a composite key.
- **Timestamps as identity** — `observed_at_epoch_ms` (and any epoch/`retrieval` time) remains a **timestamp,
  NOT identity**; it may never be repurposed as the event key.
- **Any other invented `event_id` / `log_id` uniqueness formula.**

Rationale: a fabricated identity is indistinguishable from a real provenance-anchored one and would silently
corrupt replay determinism and audit truth. Identity must be **deterministic and provenance-anchored**, sourced
from an authoritative upstream chain — **not minted at the sink**. This charter does **not** define that source;
it only forbids the synthetic alternatives.

---

## 5. In-Process Reference Preservation vs. Durable Identity

A sharp distinction, ratified here:

- **Reference preservation (in-process, already ratified).** Within the runtime chain, upstream objects/results
  are passed **by identity/reference** where already ratified (e.g. `PassiveShadowInput` holds the
  `NetEdgeCalculationResult` by identity; B3 forwards the producer output by identity). S2 **ratifies** that this
  in-process reference preservation continues — it is how the chain stays unbroken **at runtime**.
- **Durable identity (NOT memory identity).** Python **`id()` / memory identity MUST NOT** be treated as a
  durable replay identifier or a persisted log ID. `id()` is process-local, non-deterministic across runs, and
  meaningless after the object is gone — it is **reference preservation**, **not** durable identity.
- **The lock:** S2 must keep **"reference preservation"** (a runtime invariant: pass the same object through,
  unchanged) strictly separate from **"durable identity derivation"** (a persisted, replay-stable name). The
  former is ratified and ongoing; the latter is **deferred** to a future authoritative-source identity charter
  and is **not** derived from `id()` or memory.

---

## 6. Opaque S2 Identity Slot

S1 may require a **future-compatible opaque provenance/event-identity reference** slot, **owned by S2**. This
charter defines the **lock around the slot conceptually** and **leaves it unfilled**:

- **Opaque.** The slot is held **by reference**, never parsed, formatted, hashed, concatenated, compared
  lexically, or inspected for structure by S1/B4/S4/the sink.
- **S2-owned.** Only a future, separately-authorized S2 identity slice (sourcing identity from an authoritative,
  deterministic, provenance-anchored upstream chain) may **fill** it. S1 and the 0B schema may **reference** it
  but never **mint** it.
- **Unfilled here.** This charter **MUST NOT** populate the slot with a UUID, hash, `id()`, counter, timestamp,
  or any formula. The slot's *contents* and *derivation* are explicitly **deferred**; only its *boundary* (opaque,
  by-reference, S2-owned, deterministic-and-provenance-anchored when ever filled) is fixed.

---

## 7. Pass / Halt Provenance Symmetry

The provenance and identity locks apply **equally and symmetrically** to:

- **Future B4 score events** (`ShadowObservation`/`ShadowScore` over a pass handoff), and
- **Future S4 materialized halt events** (structural-halt and semantic/math-halt families per the S1 taxonomy).

Both event families must carry an **unbroken provenance chain** and a future **opaque identity reference** under
the same rules — neither family is exempt, privileged, or allowed a weaker chain-of-custody. A halt event's
provenance must be as complete and identity-anchored as a score event's. This charter **does not** design B4
scoring or S4 materialization; it only mandates that, whatever those produce, the **same** provenance/identity
locks bind both.

**Immutability / replay compatibility:** provenance must be compatible with append-only, replay-first logs — **no
wall-clock enrichment**, no mutation, no reclassification, and **no async/event-loop assumptions** in how
provenance or identity is carried. Provenance is recorded as observed, deterministically, once.

---

## 8. Still-Forbidden Work

- **No** identity invented or derived: **no** UUID/hash/random/counter/concatenation/timestamp-as-ID/`id()`-as-ID;
  **no** `event_id`/`log_id` formula; **no** filling of the opaque slot.
- **No** log field-level schema; **no** field names; **no** persistence/storage/serialization/database/file
  design.
- **No** S4 exception-catching/materialization design; **no** B4 scoring/diagnostic-EV; **no** S5 runner; **no**
  Cell-3 route.
- **No** wall-clock enrichment; **no** mutation/update/delete/reclassification; **no** async/event-loop assumption.
- **No** chain-of-custody concretization into fields/serialization (only the *unbroken-across-boundaries* rule is
  governed).
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/actionability content.
- **No** weakening of B3/producer/Phase 5/B2/S1 invariants; **no** treating `id()`/timestamp as durable identity.
- **No** Slice-0B authorization; **no** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no**
  7.x/8.x work.

---

## 9. Readiness Verdict

- **S2 provenance/identity boundary: conceptually pinned, UNBUILT.** The locks (synthetic-identity ban,
  reference-vs-durable-identity separation, opaque S2-owned slot, pass/halt symmetry, replay/immutability
  compatibility) are defined; the **identity source and derivation remain DEFERRED** to a future authoritative
  identity slice — preferred **BLOCKED/DEFERRED** over inventing one.
- **Slice-0B field-level schema: BLOCKED.** It remains blocked until this S2 identity/provenance boundary is
  ratified **and** an authoritative identity source is separately settled. No 0B schema design is authorized
  here.
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.** Unchanged.

---

## 10. Next Safe Step

- A **separately-authorized docs-only S2 Identity Source charter** — establishing the **authoritative,
  deterministic, provenance-anchored** source from which the opaque event-identity reference (§6) is derived (or
  returning **BLOCKED/DEFERRED** if no authoritative source can be evidenced), still **designing no runtime,
  schema, or formula**.
- Only after the S2 identity/provenance boundary **and** identity source are ratified may a **Slice-0B
  field-level schema charter** be authorized (under the S1 boundary).
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency).
- **No implementation is authorized by this charter.** The identity source, the 0B schema, S4 materialization, B4
  scoring, S5 runner, durable persistence, the Cell-3 route, the Shadow Intent Envelope, capacity activation,
  Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** S2 is conceptually pinned but **UNBUILT**; **Slice-0B schema remains BLOCKED** until S2 is
ratified; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
