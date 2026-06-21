# Phase 6.1 — GrossEdgeBindingLabelContext Field-Shape Charter

> **This is a docs-only logical field-shape charter.** It conceptually defines the **exact field shape** of the
> `GrossEdgeBindingLabelContext` micro-container authorized in `7839de5` — **conceptual obligations only**, no
> runtime, no schema, no persistence, no parsing, no validation algorithm, no helper methods. It **designs and
> builds nothing**. It authorizes NO runtime code, NO tests, NO lock-test edits, NO schema/runtime/interface edits,
> NO edits to the Reader / S2 / B2 / B3 / Producer / Phase 5 / B4 / S4 / S1 / S5 / lock-tests, NO B2 ingestion
> runtime, NO S5 runtime, NO storage, NO Cell-3/cost, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_gross_edge_binding_label_source_decision_charter.md`,
> `docs/handoff/phase6_1_b2_pass_path_ingestion_mapping_contract_charter.md`,
> `docs/handoff/phase6_1_market_provenance_context_field_shape_charter.md`,
> `docs/handoff/phase6_1_market_provenance_context_runtime_dto_closeout_ratification.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `7839de59351f9c745f8a0cf5389a9c2b93c7d04c`

---

## 1. Base / Dependency Chain

**Base commit:** `7839de59351f9c745f8a0cf5389a9c2b93c7d04c`.

References:

- `…_gross_edge_binding_label_source_decision_charter.md` — **decided** that the GROSS_EDGE binding's
  `normalized_field_name` and binding-level `source_field` are **externally-supplied passive provenance** carried by
  a **new, separate, immutable `GrossEdgeBindingLabelContext`** (Option B); `MarketProvenanceContext` stays frozen.
  **This charter fixes that context's field shape.**
- `…_b2_pass_path_ingestion_mapping_contract_charter.md` — the GROSS_EDGE field-entry requires the labels
  `normalized_field_name`, `source_field`, `binding_role`, `magnitude`, `unit` (+ optional `zero_cost_evidence`);
  this context supplies the first two; `binding_role="GROSS_EDGE"` is a structural constant; `magnitude`/`unit` are
  payload values.
- `…_market_provenance_context_field_shape_charter.md` / `…_runtime_dto_closeout_ratification.md` — the **discipline
  template** mirrored here (frozen, methodless, exact-field, structural guard only, verbatim carriage, no
  fabrication).

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Current State

- `GrossEdgeBindingLabelContext` is decided (`7839de5`) but its **field shape is undefined** — this charter defines
  its **logical attributes** only.
- The Option-B reader/payload, S2, B2, `PublicRawSnapshotRecord`, B3, Producer, Phase 5, B4, S4, S1, S5 docs, and the
  ratified `MarketProvenanceContext` DTO remain **BUILT/RATIFIED and frozen**. The pass path is **contract-
  incomplete**; Phase 6.1 incomplete; Phase 6.2 not ready.
- This charter is **non-executable**: it adds no runtime, schema, parser, validator, or persistence.

---

## 3. Micro-DTO Strictness (binding)

`GrossEdgeBindingLabelContext` is defined as a **future frozen, immutable, methodless passive micro-container** with
**exactly two fields** and nothing else:

1. **`normalized_field_name`** — the GROSS_EDGE binding's normalized field name (externally supplied).
2. **`source_field`** — the GROSS_EDGE binding's **binding-level** raw source field (externally supplied, §5).

- **No** third field, **no** catch-all dict / metadata bag / open key-value surface, **no** timestamp, **no** flag,
  **no** fallback label, **no** `binding_role` (that stays the structural constant `"GROSS_EDGE"`), **no**
  magnitude/unit (payload values), **no** cost field, **no** helper/static/class method, **no** computed property,
  **no** convenience surface. The **only** method permitted in a future runtime is `__post_init__` as a structural
  guard (§6).
- These are **Logical Provenance Attributes** — **not** database columns, serialized keys, JSON structure, dataclass
  fields, Python types, SQL/Parquet schemas, indexes, primary keys, or persistence formats. No concrete types,
  formats, ordering, encoding, or serialization are fixed here.

---

## 4. Verbatim String Carriage (binding)

- Both fields are **externally-supplied non-empty strings carried verbatim**. A future runtime performs **no**
  parsing, splitting, trimming, case normalization (upper/lower), vocabulary enforcement, semantic validation,
  defaulting, `UNKNOWN`/empty/synthetic/placeholder substitution, UUID, hash, counter, or generated value.
- A future structural guard may enforce **only** that each is an **exact non-empty `str`** (mirroring the
  `MarketProvenanceContext` discipline; the bool-rejection precedent of `75f53a4` §6 applies: `type(x) is str`,
  never `isinstance`). If a field is absent/non-str/empty, the future runtime **structural-halts** — it never
  fabricates.

---

## 5. Binding-Level Source Isolation (binding)

- **`source_field` means the binding-level `source_field` only** — the raw source field of the GROSS_EDGE *binding*.
  It is **distinct** from `PublicRawSnapshotRecord.source_field` (the record-level provenance, mapped from
  `MarketProvenanceContext.source_field`).
- It **MUST NOT** be copied, reused, inferred, aliased, or defaulted from `MarketProvenanceContext.source_field` or
  any record-level `source_field`. The two `source_field`s are **separate supplied facts** on separate granularities
  (binding vs record); conflating them is forbidden (`7839de5` §3).

---

## 6. Frozen B2 Isolation (binding)

- The context exists **only** to satisfy the frozen B2 `field_payload` binding-label requirements. Both fields
  **conform to** B2's existing contract (each an exact non-empty str passed verbatim to
  `make_normalized_evidence_field_binding`); they **do not alter** the B2 normalizer, `PublicRawSnapshotRecord`,
  the binding contract, B2's vocabulary, or any validator.
- A future `__post_init__` structural guard enforces only the str/non-empty shape (§4); it does **not** re-implement
  or duplicate B2's validation, and it asserts **no** B2 vocabulary for `normalized_field_name` (B2 fixes none).

---

## 7. Semantic Passivity (binding)

- Both labels are **passive structural provenance only.** The context (and any future supplier/consumer) **MUST
  NOT** inspect payload magnitude/unit/value to choose or derive labels, and **MUST NOT** compute edge, score, rank,
  threshold, direction, actionability, or any business meaning. A label names *which field a passive value came
  from*; it asserts nothing about magnitude, sign, or profitability.

---

## 8. Identity / Runner / Storage / Cost Exclusion (binding)

- **Identity isolation.** The context makes **no** reference to `S2IdentityWiringCandidate`, `raw_snapshot_identity`,
  Market Identity, or the Silver tuple, and performs **no** identity derivation/merging. The two labels are
  field-binding provenance, on a plane separate from every identity plane.
- **Runner exclusion.** S5 **MUST NOT** generate, infer, map, or inject these labels; a future S5 may only **pass
  through** a separately-ratified `GrossEdgeBindingLabelContext`. No runner logic is defined here.
- **Storage exclusion.** The context is an **in-memory, ephemeral, per-event** passive shape only — **no** durable
  storage, DB, serialization, indexing, retention, cursor, checkpoint, or run-state.
- **Cost exclusion.** **No** COST/Cell-3/fee/cost-validity field; the context carries **only** GROSS_EDGE binding
  labels (COST and Cell-3 remain separately gated).

---

## 9. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated."

---

## 10. Still-Forbidden Work

- **No** third field / catch-all dict / metadata bag / timestamp / flag / fallback label / helper method / extra
  context field (§3).
- **No** parse/trim/case/vocabulary/semantic-validation/default/`UNKNOWN`/placeholder/UUID/hash/synthetic value
  (§4); **no** `isinstance` (exact-type discipline).
- **No** copy/reuse/inference/alias/default of `source_field` from record-level `MarketProvenanceContext.source_field`
  (§5).
- **No** edit to B2 / `PublicRawSnapshotRecord` / normalizer / vocabulary / validators (§6); the context conforms,
  never alters.
- **No** magnitude/unit/value inspection; **no** edge/score/rank/threshold/direction/actionability/business
  computation (§7).
- **No** S2 identity / `raw_snapshot_identity` / Market Identity / Silver-tuple reference or derivation/merge (§8).
- **No** S5 generation/inference/mapping/injection (§8); **no** storage/cursor/checkpoint/persistence/run-state
  (§8); **no** COST/Cell-3/fee/cost-validity (§8); **no** capacity activation.
- **No** runtime/tests/schema; **no** `GrossEdgeBindingLabelContext` runtime here; **no** B2 ingestion runtime; **no**
  S5 runtime; **no** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 11. Precise State

- This charter may make a **separately-authorized `GrossEdgeBindingLabelContext` runtime DTO TDD slice eligible** (a
  frozen, slotted, methodless **two-field** passive container with a structural guard enforcing exact non-empty str,
  mirroring `MarketProvenanceContext`) — but **authorizes none here**.
- It **does not** authorize the B2 ingestion runtime, S5 runtime, Cell-3, or storage; **does not** complete the pass
  path; **does not** complete Phase 6.1; **does not** ready Phase 6.2.
- Still-separate prerequisites before the pass path is contract-complete: (a) the `GrossEdgeBindingLabelContext`
  runtime DTO; (b) the B2 ingestion runtime (three passive inputs → `PublicRawSnapshotRecord`); (c) a passive
  cost-context (Cell-3) source for B3/Producer. The **S1 storage-medium** charter remains independently gated; the
  S1 sink stays a **test-only reference sink**.

---

## 12. Next Safe Step

- A **separately-authorized `GrossEdgeBindingLabelContext` runtime DTO TDD slice** — implementing, **under this
  field-shape**, a frozen/slotted/immutable/methodless two-field passive container (`normalized_field_name`,
  `source_field`), `__post_init__` structural guard enforcing exact non-empty str for both (bool rejected; no
  `isinstance`), verbatim carriage, no fabrication/parsing/identity/cost/runner logic, test-first — mirroring the
  ratified `MarketProvenanceContext` DTO.
- **Then** the **B2 ingestion runtime TDD slice** consuming the three passive inputs (payload +
  `MarketProvenanceContext` + `GrossEdgeBindingLabelContext`) into an exact `PublicRawSnapshotRecord`.
- Independently: the **passive cost-context (Cell-3)** source; the **S1 storage-medium** charter.
- Only after **both** the pass path (ingestion + labels + cost-context) **and** the halt path are contract-complete
  does an **S5 runtime TDD slice** become eligible.
- **No implementation is authorized by this charter.**

**Conclusion:** `GrossEdgeBindingLabelContext` is fixed at **logical-attribute level** as a **future frozen,
immutable, methodless passive micro-container** with **exactly two** externally-supplied fields —
`normalized_field_name` and the binding-level `source_field` — and **no** third field, catch-all dict, timestamp,
flag, fallback label, helper method, or extra context. Both are **non-empty strings carried verbatim** (no parse/
trim/case/vocabulary/semantic-validation/default/`UNKNOWN`/UUID/hash/synthetic), under a future structural guard that
enforces **only** exact non-empty str (bool rejected, no `isinstance`). **Binding-Level Source Isolation** holds
(`source_field` is binding-level only, never copied/reused/inferred/aliased/defaulted from the record-level
`MarketProvenanceContext.source_field`); **Frozen B2 Isolation** holds (labels conform to, never alter, the B2
contract); **Semantic Passivity** holds (no magnitude inspection, no edge/score/direction/actionability); and
**Identity / Runner / Storage / Cost** are all excluded (no S2/`raw_snapshot_identity`/Market-Identity/Silver-tuple,
no S5 logic, no persistence, no COST/Cell-3). This makes a **future runtime DTO TDD slice eligible** but authorizes
**no** runtime, **no** B2 ingestion, and **no** S5; existing modules remain **frozen**; the pass path is **not**
contract-complete; **S5 runtime remains ineligible**; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**.
**No executable work is authorized.**
