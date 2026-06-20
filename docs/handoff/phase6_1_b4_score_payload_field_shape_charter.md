# Phase 6.1 — B4 Score-Payload Field-Shape Charter

> **This is a docs-only logical field-shape charter.** It conceptually defines the **logical observation
> attributes** inside `ObservationScoreRecord.family_payload` — **conceptual obligations only**, no runtime, no
> schema, no persistence, no arithmetic. It **designs and builds nothing**. It authorizes NO runtime code, NO
> tests, NO schema/runtime/interface edits, NO storage/persistence/serialization design, NO database columns/
> primitive-type schema/JSON keys/tables/indexes/files, NO B4 scoring arithmetic formula, NO thresholds, NO
> actionability, NO S4 halt materialization, NO S5 runner, NO Cell-3 assembly, NO Phase 6.2 work, NO pytest, NO
> graphify. It is subordinate to
> `docs/handoff/phase6_1_b4_passive_scoring_planning_charter.md`,
> `docs/handoff/phase6_1_s1_event_family_record_model_slice0b_field_level_charter.md`,
> `docs/handoff/phase6_1_s1_in_memory_reference_sink_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_runtime_tdd_closeout_ratification.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `1e271c87c0ffba8e19415697b093b71f1ffb824a`

---

## 1. Base / Dependency Chain

**Base commit:** `1e271c87c0ffba8e19415697b093b71f1ffb824a`.

References:

- `…_b4_passive_scoring_planning_charter.md` — pinned B4 as a passive, recorder-oriented scoring boundary that
  consumes the frozen pass handoff + S2 identity evidence and produces **one** `ObservationScoreRecord` for the S1
  reference sink; pure/deterministic; identity-blind; pair/venue-agnostic; cost opaque; **B4 ≠ S1 sink**.
- `…_s1_event_family_record_model_slice0b_field_level_charter.md` — the common envelope (`identity_evidence`,
  `observation_kind`, `provenance_timestamp`, `opaque_cost_context`, `family_payload`); identity is **envelope-
  level**, never in payload.
- `…_s1_in_memory_reference_sink_tdd_closeout_ratification.md` — S1 admits `ObservationScoreRecord` by exact type
  and records it; **S1 records, B4 produces**.
- `…_s2_identity_wiring_runtime_tdd_closeout_ratification.md` — opaque Silver pair carried by
  `S2IdentityWiringCandidate`; identity-blind.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Current State

- B4 boundary is conceptually pinned (planning charter); **B4 score payload field-shape is undefined** — this
  charter defines its **logical observation attributes** only.
- The S1 reference sink, `S2IdentityWiringCandidate`, the passive spine, and the Option-B reader are **BUILT +
  RATIFIED and frozen**. Slice-0B logical model exists; storage medium undecided. Phase 6.1 incomplete; Phase 6.2
  not ready.
- This charter is **non-executable**: it adds no runtime, schema, formula, or persistence.

---

## 3. B4 Score-Payload Purpose

`family_payload` (for the score family) is the **passive, diagnostic observation content** of an
`ObservationScoreRecord` — *what was observed about an already-evaluated passive outcome*. Its purpose is
**diagnostic explainability for replay**, not a decision: it lets a later reader of the S1 log see *what passive
score was observed and on what basis*, with **zero** actionability and **zero** identity. It carries observation,
never instruction.

---

## 4. Logical Observation Attributes (conceptual obligations only)

Defined as **Logical Observation Attributes** — **not** database columns, serialized keys, JSON structure,
dataclass fields, Python types, SQL/Parquet schemas, indexes, primary keys, or persistence formats. The suggested
minimal obligations are **accepted with refinements** (refinement rationale in §4a):

- **`passive_score_magnitude`** — a **passive diagnostic magnitude** observed from the already-evaluated passive
  outcome. It is an *observation of a number*, **not** actionability: no threshold result, no "is-profitable" flag,
  no decision. It does not imply "should trade."
- **`score_basis_reference`** — an **opaque, by-reference** link to the frozen passive input/result used as the
  scoring basis (e.g. the pass handoff / Phase 5 net-edge result referenced by identity). It is **basis
  provenance, not identity** (§5): it points at *what was scored*, never at *which log event this is*, and is
  never parsed/derived/normalized.
- **`score_inputs_summary`** — a **passive diagnostic summary** of the inputs the score was observed over, carrying
  **no identity** and **no actionability**. A human/replay-readable account of *what fed the observation*, never a
  recommendation.
- **`score_unit_context`** — **opaque unit/context metadata** carried from upstream, with **no hard-coded unit**
  (§6). It contextualizes the magnitude passively; it is not interpreted, normalized, or converted here.
- **`score_family_descriptor`** — a **conceptual formula-family descriptor** for **replay explainability** (i.e.
  *which family/shape of passive diagnostic this observation belongs to*). It is **not** a versioned ID, **not** a
  runtime/implementation identifier, and **not** an identity; it is a passive, human-meaningful descriptor only.

### 4a. Refinement Rationale
- All five suggested obligations are **retained**, each **re-scoped to passivity**: every attribute is an
  *observation* of an already-computed passive outcome, never a computation, decision, or instruction.
- **`score_basis_reference` is explicitly classified as basis-provenance, NOT identity** (§5) to prevent it from
  becoming an identity alias — it links to *what was scored*, not *which event this is*.
- **`score_family_descriptor` is explicitly NOT a versioned ID** to avoid it drifting into a synthetic key or a
  runtime/version identifier; it is replay-explainability metadata only.
- No additional attributes are introduced; the set stays **minimal**. No attribute may be added that implies
  actionability, identity, or a decision.

---

## 5. Identity Segregation (No-Bleed)

- The payload **MUST NOT** duplicate, absorb, derive, normalize, copy, or alias identity from
  `S2IdentityWiringCandidate`. Identity remains **envelope-level only**, through `identity_evidence`.
- **Forbidden payload attributes (identity aliases):** `artifact_locator`, `physical_record_position`,
  `row_offset`, `read_index`, `read_offset`, `event_id`, `log_id`, `record_id`, `message_id`, `sequence_number`,
  `uuid`, `hash`, `fingerprint`, `source_id`, or **any equivalent identity alias**.
- `score_basis_reference` (§4) is **basis provenance, not identity**: it references the frozen passive
  input/result that was scored; it is **not** the event's name and is never promoted to, or read as, identity.

---

## 6. Unit, Cost & Pair Passivity Rules

### 6a. Unit-Agnosticism
- **No** hard-coded currencies, pairs, exchanges, tick sizes, lot sizes, or venue-specific units. `score_unit_context`,
  if present, is **opaque/passive metadata carried from upstream**, not interpreted or converted here.
- **Pair / venue** remain **passive observation metadata only** (carried if present upstream); **no** pair
  selection, batching, or multi-pair orchestration (that belongs to a future runner).

### 6b. Opaque Cost Context
- Cost context remains **opaque**; **Cell-3 remains deferred / parallel.** The payload may **acknowledge** that
  cost context can affect future scoring **inputs** *only if already provided upstream* (i.e. reflected in the
  passive math the score observes). It **must not** inspect, normalize, assemble, or invent cost context, and
  **must not** open Cell-3 here. Envelope-level `opaque_cost_context` stays envelope/context-level (§9).

### 6c. Existing-Math Boundary
- The payload may **reference** already-computed passive pipeline outputs (via `score_basis_reference` /
  `score_inputs_summary`). **B4 must not recompute Phase 5 net-edge math.** **No** scoring arithmetic formula,
  threshold, rank, or priority semantics is defined here.

---

## 7. Semantic Passivity (binding)

- All payload attributes are **passive observational diagnostics only.**
- **Forbidden** anywhere in the payload: `verdict`, `decision`, `action_type`, `trade_signal`, `order_size`,
  `recommendation`, `readiness`, `threshold_result`, `route`, `execution`, `allocation`, `priority`, `ranking`,
  `candidate`, `opportunity`, `profit guarantee`, or any actionability field.
- **The payload must not imply "should trade."** A diagnostic magnitude is an observation, never an instruction;
  no attribute may be read as a go/no-go, a ranking, or a profitability promise.

---

## 8. Runtime Name-Lock Warning (docs-only)

- This is **docs-only**. It defines **no** runtime names and **no** lock-test allowlists.
- A future B4 **runtime** slice must **separately** handle any score-name lock collision if it appears (e.g. a
  banned `score`/`rank`/`threshold`/`actionab…` substring in a runtime defined name), via its own
  separately-authorized name-lock exception — exactly as the S1 `ObservationScoreRecord` exception was handled.
  **No** such name or allowlist is created here.

---

## 9. S1 / S2 Compatibility

- The payload must fit **inside** `ObservationScoreRecord.family_payload`. It is **content**, not envelope.
- **`identity_evidence` remains top-level S1 envelope evidence** (the `S2IdentityWiringCandidate`); it is **never**
  duplicated into the payload (§5).
- **`provenance_timestamp` remains timestamp-only** (envelope-level), never identity, never a payload key.
- **`opaque_cost_context` remains envelope/context-level** and opaque; it is **not** moved into the payload unless
  a future charter explicitly justifies a *passive diagnostic* cost-context attribute — and even then only
  opaquely (no inspection/assembly). This charter does **not** authorize that.
- **S1 records; B4 produces.** The payload obligations here constrain what B4 builds; S1 admits the
  `ObservationScoreRecord` by exact type and retains it.

---

## 10. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read
as "capacity validated."

---

## 11. Still-Forbidden Work

- **No** actionability attribute (verdict/decision/action_type/trade_signal/order_size/recommendation/readiness/
  threshold_result/route/execution/allocation/priority/ranking/candidate/opportunity/profit-guarantee); **no**
  "should trade" implication.
- **No** identity in the payload; **no** identity alias (§5); **no** promotion of `score_basis_reference` to
  identity.
- **No** scoring arithmetic formula, threshold, rank/priority semantics; **no** Phase 5 recomputation.
- **No** database columns / serialized keys / JSON structure / dataclass fields / Python types / SQL-Parquet
  schema / indexes / primary keys / persistence format.
- **No** hard-coded currency/pair/exchange/tick/lot/venue unit; **no** pair selection / multi-pair orchestration.
- **No** cost-context inspection/normalization/assembly/invention; **no** Cell-3 assembly.
- **No** runtime name / lock-test allowlist creation here.
- **No** S4 halt materialization; **no** S5 runner; **no** storage medium / persistence.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Next Safe Step

- A **separately-authorized B4 passive scoring runtime TDD slice** — implementing, **under this field-shape and
  the B4 plan**, a pure/deterministic passive scorer that consumes the frozen pass handoff, carries S2 identity
  opaquely at the envelope level, populates a passive `family_payload` honoring these Logical Observation
  Attributes, and constructs an `ObservationScoreRecord` for the S1 reference sink — test-first, no actionability,
  no thresholds, no S4/S5, no storage, and handling any runtime score-name lock collision via its own
  separately-authorized exception (§8).
- Independently/subsequently: the **S4 exception-routing decision** (halt → `ObservationHaltRecord`); the **S5
  runner**; the **S1 storage-medium** charter; and the **real-cost Cell-3** assembly. Each separately gated.
- **No implementation is authorized by this charter.** The B4 runtime slice, S4 materialization, the S5 runner,
  the storage medium, durable persistence, the Cell-3 route, the Shadow Intent Envelope, capacity activation,
  Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the B4 score `family_payload` is defined at **logical-attribute level, storage-agnostically** — a
**passive, diagnostic, replay-explainability** payload carrying `passive_score_magnitude` (an observed magnitude,
never actionability), `score_basis_reference` (opaque by-reference basis provenance, **not identity**),
`score_inputs_summary` (passive diagnostic summary, no identity/actionability), `score_unit_context` (opaque
upstream unit metadata, no hard-coded unit), and `score_family_descriptor` (replay-explainability descriptor,
**not** a versioned/runtime ID). It carries **no identity** (identity stays envelope-level via `identity_evidence`;
all identity aliases forbidden), **no actionability** ("should trade" forbidden), **no formula/threshold/rank**,
**no hard-coded unit/pair/venue**, and **no cost inspection** (cost opaque, Cell-3 deferred). It fits **inside**
`ObservationScoreRecord.family_payload`; `provenance_timestamp` stays timestamp-only and `opaque_cost_context`
envelope-level; **S1 records, B4 produces**. It is **UNBUILT** and **designs no schema/runtime/storage/formula**;
existing modules remain **frozen**; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable
work is authorized.**
