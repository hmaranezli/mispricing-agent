# Phase 6.1 — S4 Halt-Payload Field-Shape Charter

> **This is a docs-only logical field-shape charter.** It conceptually defines the **logical observation
> attributes** inside `ObservationHaltRecord.family_payload` for S4 halt materialization — **conceptual obligations
> only**, no runtime, no schema, no persistence, no arithmetic, no taxonomy. It **designs and builds nothing**. It
> authorizes NO runtime code, NO tests, NO schema/runtime/interface edits, NO storage/persistence/serialization
> design, NO database columns / primitive-type schema / JSON keys / tables / indexes / files, NO halt severity/
> priority/class taxonomy, NO retry/route/recovery field, NO actionability, NO S5 runner, NO Cell-3 assembly, NO
> Phase 6.2 work, NO pytest, NO graphify, NO edits to the Option-B reader / `S2IdentityWiringCandidate` / B3 / B4 /
> the S1 reference sink. It is subordinate to
> `docs/handoff/phase6_1_s4_exception_routing_halt_materialization_decision_charter.md`,
> `docs/handoff/phase6_1_b4_score_payload_field_shape_charter.md`,
> `docs/handoff/phase6_1_s1_event_family_record_model_slice0b_field_level_charter.md`,
> `docs/handoff/phase6_1_s1_in_memory_reference_sink_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_runtime_tdd_closeout_ratification.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `b0ceab47f8b7c750331117b4882f21263ce8f80f`

---

## 1. Base / Dependency Chain

**Base commit:** `b0ceab47f8b7c750331117b4882f21263ce8f80f`.

References:

- `…_s4_exception_routing_halt_materialization_decision_charter.md` — decided S4 as a **passive, recorder-oriented
  halt-materialization boundary** under the **Mortician Rule** (records an already-observed halt; **never** retries,
  repairs, normalizes, enriches, back-fills, or synthesizes missing data); consumes an already-observed structural
  halt (`OptionBLocalParseHalt` / `B3PassiveClientWiringError` / `BlockedPacket`) **opaquely by reference** + the
  **existing** `S2IdentityWiringCandidate`; produces **one** `ObservationHaltRecord`; **S4 ≠ S1 sink**. §6a pinned
  two conceptual obligations: an **opaque halt carrier by reference** and a **non-versioned halt-family descriptor**.
- `…_b4_score_payload_field_shape_charter.md` — the **peer discipline** this charter mirrors: a narrow, closed set
  of passive Logical Observation Attributes (storage-agnostic), identity-blind, actionability-free; basis/origin
  references classified as **provenance, not identity**; descriptors classified as **non-versioned, not identity**.
- `…_s1_event_family_record_model_slice0b_field_level_charter.md` — the common envelope (`identity_evidence`,
  `observation_kind`, `provenance_timestamp`, `opaque_cost_context`, `family_payload`); identity is **envelope-level
  only**, never in payload; `ObservationScoreRecord` / `ObservationHaltRecord` are **two equal-peer families**.
- `…_s1_in_memory_reference_sink_tdd_closeout_ratification.md` — S1 admits an exact `ObservationHaltRecord` by exact
  type and records it; **S1 records, S4 produces**.
- `…_s2_identity_wiring_runtime_tdd_closeout_ratification.md` — opaque Silver pair carried by
  `S2IdentityWiringCandidate`; identity-blind; pass/halt symmetric.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Current State

- S4 boundary is conceptually decided (decision charter); **S4 halt payload field-shape is undefined** — this
  charter defines its **logical observation attributes** only.
- The Option-B reader (`OptionBLocalParseHalt`), `S2IdentityWiringCandidate`, B3 (`B3PassiveClientWiringError`,
  `BlockedPacket`), B4, and the S1 reference sink are **BUILT + RATIFIED and frozen**. Slice-0B logical model exists;
  storage medium undecided. Phase 6.1 incomplete; Phase 6.2 not ready.
- This charter is **non-executable**: it adds no runtime, schema, formula, taxonomy, or persistence.

---

## 3. S4 Halt-Payload Purpose

`family_payload` (for the halt family) is the **passive, diagnostic observation content** of an
`ObservationHaltRecord` — *what was observed about an already-occurred structural halt*. Its purpose is **diagnostic
explainability for replay**, not a decision and not a re-attempt: it lets a later reader of the S1 log see *that a
halt was observed and which opaque origin it came from*, with **zero** actionability, **zero** identity, and **zero**
revival of the halted work. It carries observation, never instruction; it **describes a death, never prescribes a
resurrection** (the Mortician Rule, restated at payload level).

---

## 4. Logical Observation Attributes (narrow, closed set; conceptual obligations only)

Defined as **Logical Observation Attributes** — **not** database columns, serialized keys, JSON structure,
dataclass fields, Python types, SQL/Parquet schemas, indexes, primary keys, or persistence formats. This is a
**narrow, closed set** (no arbitrary/open key-value dictionary surface, §6); it mirrors the B4 score-payload
discipline while dropping the score-specific magnitude/unit obligations (a halt has no measured magnitude or unit):

- **`halt_origin_reference`** — an **opaque, by-reference** link to the **already-observed** halt carrier (e.g. the
  `OptionBLocalParseHalt` / `B3PassiveClientWiringError` / `BlockedPacket` object, as handed). It is **origin
  provenance, not identity** (§5): it points at *which opaque halt was observed*, never at *which log event this is*.
  It is carried **as-is, opaquely** — **never** parsed, stringified, repr'd, normalized, classified by meaning, or
  repaired. It is **not** a stack trace, error message, or traceback (§7a).
- **`halt_inputs_summary`** — a **passive diagnostic summary** of the upstream passive context the halt was observed
  over (e.g. passive venue/pair metadata **only if already present** upstream), carrying **no identity** and **no
  actionability**. It is a replay-readable account of *what context the halt was observed in*, never a
  recommendation, never a remediation, and never fabricated where absent.
- **`halt_family_descriptor`** — a **non-versioned**, passive, human-meaningful descriptor for **replay
  explainability** (i.e. *which family/shape of passive halt observation this is* — the "halt-class descriptor" of
  the decision charter §6a). It is **NOT** a versioned ID, **NOT** a runtime/implementation identifier, **NOT**
  identity, and **NOT** a severity/priority/criticality label or a halt ranking (§7b).

### 4a. Refinement Rationale
- The set is deliberately **smaller than B4's five**: a halt is the observation of a *terminal structural fact*, not
  of a measured outcome, so the score-specific `…_magnitude` and `…_unit_context` obligations are **omitted** (there
  is no number or unit to carry passively). Forcing analogues would invent meaning the halt does not contain.
- **`halt_origin_reference` is explicitly classified as origin-provenance, NOT identity** (§5), exactly as B4's
  `score_basis_reference` is basis-provenance — it links to *what halted*, not *which event this is*, and is never
  promoted to identity.
- **`halt_family_descriptor` is explicitly NOT a versioned ID and NOT a taxonomy/severity label** to keep it from
  drifting into a synthetic key, a runtime/version identifier, or a severity/priority class (§7b).
- The set is **closed**: no additional attribute may be added that implies actionability, identity, severity,
  retry/route/recovery, or a decision. Any future attribute requires a **separate** charter justification.

---

## 5. Identity Segregation (No-Bleed, No Fallback)

- The payload **MUST NOT** duplicate, absorb, derive, normalize, copy, alias, or **replace** identity from
  `S2IdentityWiringCandidate`. Identity remains **envelope-level only**, through `identity_evidence`.
- **No fallback identity, ever.** A halt often means data is missing, but a missing payload **never** licenses a
  manufactured key. The payload synthesizes **no** substitute identity (no UUID/hash/counter/concat/timestamp-as-ID/
  fingerprint/synthetic key) and back-fills nothing (Mortician Rule, decision charter §3/§5).
- **Forbidden payload attributes (identity aliases):** `artifact_locator`, `physical_record_position`, `row_offset`,
  `read_index`, `read_offset`, `event_id`, `log_id`, `record_id`, `message_id`, `sequence_number`, `uuid`, `hash`,
  `fingerprint`, `source_id`, or **any equivalent identity alias**.
- `halt_origin_reference` (§4) is **origin provenance, not identity**: it references the opaque halt carrier that was
  observed; it is **not** the event's name and is never promoted to, or read as, identity.

---

## 6. Closed-Set / No Open Dictionary Surface

- The halt payload is a **narrow, closed set of named logical attributes** (§4) — **not** an arbitrary, open,
  caller-extensible key/value map, free-form `extra`/`metadata`/`details` bag, or schemaless blob into which
  arbitrary halt context could be poured. Sub-field isolation is binding: only the named passive obligations exist.
- **No catch-all attribute.** There is no `details`, `context`, `extra`, `attributes`, `raw`, or `payload`
  free-dictionary attribute that would let stack traces, error strings, or actionability smuggle in (§7a). Each
  attribute has a single, passive, declared purpose.

---

## 7. Semantic Passivity (binding)

### 7a. No Stack-Trace / Error-Text Dumping
- The payload **MUST NOT** contain dynamic error messages, parsed error strings, exception `repr`/`str`, traceback
  text, stack frames, frame locals, source-line snippets, debugger-style logs, or any rendered diagnostic string
  extracted from the halt. `halt_origin_reference` carries the **opaque carrier by reference**, **not** a stringified
  or parsed rendering of it. S4 does **not** read, format, or interpret the carrier's message content.

### 7b. No Taxonomy / Severity / Ranking Invention
- The payload **MUST NOT** invent or carry a halt taxonomy: **no** severity, priority, criticality, urgency,
  `WARNING`/`ERROR`/`CRITICAL`/`FATAL` levels, retry classes, route classes, recoverability flags, or halt rankings/
  ordering. `halt_family_descriptor` is **replay-explainability only** — which passive family/shape — never a graded
  or ranked label.

### 7c. No Actionability
- All payload attributes are **passive observational diagnostics only.** **Forbidden** anywhere in the payload:
  `verdict`, `decision`, `action_type`, `route`, `routing`, `retry`, `retry_count`, `recover`, `recovery`, `repair`,
  `remediation`, `readiness`, `order`, `order_size`, `execution`, `allocation`, `priority`, `ranking`, `severity`,
  `candidate`, `opportunity`, `should_continue`, `should_stop`, `should_retry`, `should_trade`, profit guarantee, or
  any actionability field. **The payload must not imply "should continue / should stop / should retry."** A halt
  observation is a terminal passive fact, never an instruction or a control signal.

---

## 8. Runtime Name-Lock Warning (docs-only)

- This is **docs-only**. It defines **no** runtime names and **no** lock-test allowlists.
- A future S4 **runtime** slice must **separately** handle any halt-name lock collision if it appears (e.g. a banned
  substring such as `route`/`rank`/`score`/`threshold`/`candidate`/`actionab…` arising inside a runtime defined
  name), via its own separately-authorized name-lock exception — exactly as the S1 `ObservationScoreRecord` exception
  was handled, and exactly as B4 avoided the collision by keeping banned substrings out of defined names. **No** such
  name or allowlist is created here.

---

## 9. S1 / S2 / Peer Compatibility

- The payload must fit **inside** `ObservationHaltRecord.family_payload`. It is **content**, not envelope.
- **`identity_evidence` remains top-level S1 envelope evidence** (the `S2IdentityWiringCandidate`); it is **never**
  duplicated into the payload (§5).
- **`observation_kind`** stays the neutral **HALT** family marker — an **equal peer** of SCORE, never a
  severity/priority/ranking signal (§7b).
- **`provenance_timestamp` remains timestamp-only** (envelope-level), never identity, never a payload key; carried
  only if already observed upstream, never manufactured.
- **`opaque_cost_context` remains envelope/context-level** and opaque; it is **not** moved into the payload. **Cell-3
  stays deferred / parallel.**
- **Peer symmetry (binding).** `ObservationHaltRecord` remains a **first-class equal peer** of
  `ObservationScoreRecord` at the S1 sink: same common envelope, same opaque Silver-pair identity rules, same
  exact-type admission, **no** priority/precedence/ranking between the two families. This halt field-shape mirrors
  B4's score field-shape discipline; it neither privileges nor subordinates either family.
- **S1 records; S4 produces.** The payload obligations here constrain what S4 builds; S1 admits the
  `ObservationHaltRecord` by exact type and retains it.

---

## 10. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated." A halt is **not** a capacity decision and confers no capacity meaning.

---

## 11. Still-Forbidden Work

- **No** actionability attribute (verdict/decision/action_type/route/retry/recover/repair/remediation/readiness/
  order/execution/allocation/priority/ranking/severity/candidate/opportunity/should-continue/should-stop/
  should-retry/profit-guarantee); **no** "should continue / should stop / should retry / should trade" implication
  (§7c).
- **No** stack-trace / error-message / traceback / exception-repr / stack-frame / debugger-log dumping; **no**
  parsing, stringifying, or rendering of the opaque halt carrier (§7a).
- **No** severity/priority/criticality/WARNING-CRITICAL-FATAL/retry-class/route-class/recoverability/halt-ranking
  taxonomy (§7b).
- **No** identity in the payload; **no** identity alias (§5); **no** fallback/synthesized identity; **no** promotion
  of `halt_origin_reference` to identity.
- **No** arbitrary/open key-value dictionary, catch-all `details`/`context`/`extra`/`raw` bag, or schemaless blob
  (§6).
- **No** synthesizing/defaulting/back-filling/reconstructing any value the halt lacks (Mortician Rule); **no**
  enrichment/normalization/repair of the carrier.
- **No** database columns / serialized keys / JSON structure / dataclass fields / Python types / SQL-Parquet schema /
  indexes / primary keys / persistence format.
- **No** hard-coded currency/pair/exchange/tick/lot/venue unit; **no** pair selection / multi-pair orchestration.
- **No** cost-context inspection/normalization/assembly/invention; **no** Cell-3 assembly.
- **No** runtime name / lock-test allowlist creation here.
- **No** edits to / reach-back into the Option-B reader, S2 wiring, B3, B4, or the S1 sink; **no** S4-as-sink.
- **No** S5 runner / orchestration; **no** storage medium / persistence.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Next Safe Step

- A **separately-authorized S4 halt-materialization runtime TDD slice** — implementing, **under this field-shape and
  the S4 decision charter**, a pure/deterministic passive materializer that consumes an **already-observed** halt
  carrier (opaquely, by reference) plus the **existing** `S2IdentityWiringCandidate`, carries identity opaquely at
  the envelope level, populates a passive `family_payload` honoring these Logical Observation Attributes
  (`halt_origin_reference`, `halt_inputs_summary`, `halt_family_descriptor`), and constructs one
  `ObservationHaltRecord` for the S1 reference sink — test-first, Mortician Rule honored (no retry/repair/back-fill/
  synthesis), no stack-trace dumping, no taxonomy, no actionability, no S5 runner, no storage, handling any runtime
  halt-name lock collision via its own separately-authorized exception (§8).
- Independently/subsequently: the **S5 runner** (orchestration that wires reader → S2 → {B4 | S4} → S1 and routes
  both families); the **S1 storage-medium** charter; and the **real-cost Cell-3** assembly. Each separately gated.
- **No implementation is authorized by this charter.** The S4 runtime slice, the S5 runner, the storage medium,
  durable persistence, the Cell-3 route, the Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x
  remain separately gated.

**Conclusion:** the S4 halt `family_payload` is defined at **logical-attribute level, storage-agnostically** — a
**narrow, closed, passive, diagnostic, replay-explainability** payload carrying `halt_origin_reference` (an **opaque
by-reference** link to the already-observed halt carrier — **origin provenance, not identity**, never parsed/
stringified/repr'd/repaired), `halt_inputs_summary` (a passive diagnostic summary of upstream context, no identity/
actionability, never fabricated), and `halt_family_descriptor` (a **non-versioned** replay-explainability descriptor
— **not** a versioned/runtime ID, **not** identity, **not** a severity/priority/taxonomy label). It carries **no
identity** (identity stays envelope-level via `identity_evidence`; all aliases and any fallback/synthesized identity
forbidden), **no stack-trace / error-text dump**, **no severity/priority/retry/route taxonomy**, **no
actionability** ("should continue / should stop / should retry" forbidden), and **no open dictionary surface**
(closed named set only). It **mirrors B4's score-payload discipline** and keeps `ObservationHaltRecord` an
**equal peer** of `ObservationScoreRecord`; it fits **inside** `ObservationHaltRecord.family_payload`;
`provenance_timestamp` stays timestamp-only and `opaque_cost_context` envelope-level; **S1 records, S4 produces**.
It is **UNBUILT** and **designs no schema/runtime/storage/formula/taxonomy**; existing modules remain **frozen**;
Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
