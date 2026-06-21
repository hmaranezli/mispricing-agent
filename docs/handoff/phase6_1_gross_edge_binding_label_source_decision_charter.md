# Phase 6.1 — GROSS_EDGE Binding Label-Source Decision Charter

> **This is a docs-only decision charter.** It conceptually resolves the residual blocker of `75d011b` §6b — how to
> supply the unsourceable `normalized_field_name` and binding-level `source_field` for the GROSS_EDGE binding
> **without fabrication** — by **deciding** the container that supplies them. It **designs and builds nothing**: no
> runtime, no tests, no field-shape, no DTO. It authorizes NO runtime code, NO tests, NO schema/runtime/interface
> edits, NO edits to the Reader / S2 / B2 / B3 / Producer / Phase 5 / B4 / S4 / S1 / S5 / lock-tests, NO B2 ingestion
> runtime, NO S5 runtime, NO storage, NO Cell-3/cost, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_b2_pass_path_ingestion_mapping_contract_charter.md`,
> `docs/handoff/phase6_1_market_provenance_context_runtime_dto_closeout_ratification.md`,
> `docs/handoff/phase6_1_market_provenance_context_field_shape_charter.md`,
> `docs/handoff/phase6_1_d3_non_payload_provenance_supply_contract_charter.md`, and `CLAUDE.md`; where any conflict
> arises, those govern.

**Base:** `75d011bdb794930df4830d1425e52182363d95dd`

---

## 1. Base / Purpose

**Base commit:** `75d011bdb794930df4830d1425e52182363d95dd`.

The B2 ingestion mapping charter (`75d011b`) mapped 13 of 14 `make_public_raw_snapshot_record` caller arguments and
left **one residual blocker** (§6b): the GROSS_EDGE `field_payload` binding requires two labels —
`normalized_field_name` and a binding-level `source_field` — that are **not sourceable** from {Option-B payload,
ratified `MarketProvenanceContext`} and **must not be fabricated, inferred, or reused** from the record-level
`source_field`. This charter **decides where those two labels legitimately originate**.

**Decision (this charter):** the two labels are **externally-supplied passive provenance**, carried by a **new,
separate, immutable `GrossEdgeBindingLabelContext`** (Option B of `75d011b` §6b / this charter §5). The ratified
ten-field `MarketProvenanceContext` stays **frozen and unchanged**.

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. The Two Unresolved Labels (restated from evidence)

From `b2_replay_normalization.py:30-32` and `b2_normalization_contract.py` (frozen), each GROSS_EDGE field-entry
requires the labels `normalized_field_name`, `source_field`, `binding_role`, `magnitude`, `unit` (+ optional
`zero_cost_evidence`). Of these, `75d011b` already resolved four:

- `magnitude`, `unit` ← Option-B payload (verbatim str, precision-safe §5 of `75d011b`);
- `binding_role` ← the structural constant `"GROSS_EDGE"`;
- `zero_cost_evidence` ← absent/`None` (frozen GROSS_EDGE rule).

**Unresolved (this charter resolves the source):**

- **`normalized_field_name`** — the binding's normalized field name (a B2 free-form non-empty str; B2 fixes no
  vocabulary for it).
- **`source_field` (binding-level)** — the binding's **raw source field**, a genuine source-provenance label,
  **distinct** from the record-level `source_field` (`PublicRawSnapshotRecord.source_field`).

---

## 3. Anti-Fabrication & Anti-Reuse Seal (binding)

- Both labels **MUST be externally supplied** as passive provenance. **Forbidden:** reusing the record-level
  `source_field`, inventing defaults, `UNKNOWN`/empty/synthetic values, generic placeholder labels, or hard-coded
  fallback strings. Constraint 2 of this task **forecloses** the "fixed structural constant" reading that `75d011b`
  §6b tentatively floated for `normalized_field_name`: a hard-coded label is a forbidden fabrication, so this label
  is **supplied provenance**, not a constant.
- If either label is absent from its supplied source at runtime, the future ingestion boundary must **structural-halt
  / stop-report a blocker** — never fabricate.

---

## 4. Semantic / Edge-Computation Ban (binding)

- The labels are **passive structural provenance only.** The supplier and any future ingestion boundary **MUST NOT**
  inspect the payload `magnitude`/`unit`/value to guess, derive, or choose labels, and **MUST NOT** compute edge,
  score, ranking, threshold, direction, actionability, or any business meaning. A label names *which field a passive
  value came from*; it asserts nothing about the value's magnitude, sign, or profitability.

---

## 5. Context-Isolation Decision — Option B (separate context), justified

**Decision: Option B — a separate immutable `GrossEdgeBindingLabelContext`.** Option A (extending
`MarketProvenanceContext`) is **rejected**. Justification (smallest responsibility-preserving design):

- **Responsibility separation.** `MarketProvenanceContext` carries **snapshot-record-level** provenance (the
  non-payload fields of the *one* `PublicRawSnapshotRecord`). The two unresolved labels are **field-binding-level**
  provenance (per *binding* inside `field_payload`). These are **different granularities**; folding binding-level
  labels into the snapshot-level container **conflates two responsibility levels** and bloats a carrier that was
  deliberately scoped. A separate two-field context keeps each container's responsibility **minimal and single-
  purpose**.
- **Preserves a ratified seal (constraint 5).** `MarketProvenanceContext` was **ratified at exactly ten fields**
  (`75f53a4` closeout §3/§12: "no field add/remove/rename"). **Option A would violate that ratified closeout.**
  Option B leaves the ten-field DTO **frozen and untouched** — no re-ratification, no seal breach.
- **Future-fit.** A binding-label context naturally generalizes to additional bindings (e.g. a future COST binding's
  labels) **without** disturbing snapshot-level provenance — but **note:** COST bindings remain **separately gated**
  (§8); this charter scopes the context to the **GROSS_EDGE** binding labels **only**.

**`GrossEdgeBindingLabelContext` (conceptual; field-shape NOT fixed here):** a new, immutable, passive, methodless
container carrying **exactly two** externally-supplied labels — `normalized_field_name` and `source_field` (binding-
level) — for the single GROSS_EDGE binding. No third field, no catch-all, no `binding_role` (that stays the
structural constant `"GROSS_EDGE"`, §2), no magnitude/unit (those are payload values), no cost. Its **formal
field-shape and runtime are a separate, future, separately-gated** slice (§10/§11).

---

## 6. Frozen B2 Architecture (binding)

- `PublicRawSnapshotRecord`, `make_public_raw_snapshot_record`, the B2 normalizer
  (`b2_normalization_contract` / `b2_replay_normalization`), and the binding contract remain **untouched**. The two
  labels **conform to** B2's existing requirements (each an exact non-empty str passed verbatim to
  `make_normalized_evidence_field_binding`); they **do not alter** B2's vocabulary, validators, or shape.
- The future ingestion boundary of `75d011b` is conceptually amended to consume **three** passive inputs — Option-B
  `parsed_payload` + `MarketProvenanceContext` + `GrossEdgeBindingLabelContext` — supplying the two binding labels
  from the third context. This is a **planning amendment only**; no runtime exists and no frozen module changes.

---

## 7. Identity Isolation (binding)

- The two labels and the `GrossEdgeBindingLabelContext` **MUST NOT** derive from, inspect, duplicate, or merge with
  `S2IdentityWiringCandidate`, `raw_snapshot_identity` (Market Identity), or the Silver tuple
  `(artifact_locator, physical_record_position)`. They are **field-binding provenance**, on a plane separate from
  every identity plane. S2 System/Silver identity bypasses this context entirely; Market Identity is not a label
  source.

---

## 8. No Storage / Cell-3 / Cost Smuggling (binding)

- This charter authorizes **no** storage, cursor, checkpoint, persistence, or run-state. `GrossEdgeBindingLabelContext`
  is an **in-memory, ephemeral, per-event** passive carrier.
- **No** Cell-3, COST binding, COST label, fee, or cost-validity behavior is defined or implied. The context carries
  **only** GROSS_EDGE binding labels; COST bindings and Cell-3 remain **separately gated** (`75d011b` §6a).

---

## 9. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated."

---

## 10. Runner Exclusion & Precise State (binding)

- **Runner exclusion.** S5 **MUST NOT** generate, infer, map, or inject these labels. A future S5 may only **pass
  through** a separately-ratified `GrossEdgeBindingLabelContext` (and the payload + `MarketProvenanceContext`) to a
  separately-ratified ingestion boundary; it implements **none** of the label sourcing or mapping internally.
- **Precise state.** This charter **resolves the §6b label-source decision** (the two labels are supplied provenance
  via a separate `GrossEdgeBindingLabelContext`). With this decision made, the `75d011b` mapping is **conceptually
  complete** (14/14 sourced: 13 from {payload, `MarketProvenanceContext`}, 2 binding labels from the new context).
  It may make a **future `GrossEdgeBindingLabelContext` field-shape / runtime DTO slice eligible** — but authorizes
  **none** here. It **does not** authorize the B2 ingestion runtime, S5 runtime, Cell-3, or storage; **does not**
  complete the pass path; **does not** complete Phase 6.1; **does not** ready Phase 6.2.

---

## 11. Still-Forbidden Work

- **No** fabrication/inference/reuse/default/`UNKNOWN`/generic/hard-coded value for either label (§3); **no**
  structural-constant `normalized_field_name`.
- **No** payload magnitude/unit/value inspection to choose labels; **no** edge/score/rank/threshold/direction/
  actionability/business computation (§4).
- **No** extension of `MarketProvenanceContext` (Option A rejected, §5); **no** field add/remove/rename to the
  ratified ten-field DTO.
- **No** edit to `PublicRawSnapshotRecord` / B2 / B3 / Producer / Phase 5 / B4 / S4 / S1 / S5 / Reader / lock-tests
  (§6); **no** B2 vocabulary/validator change.
- **No** S2 identity / `raw_snapshot_identity` / Silver-tuple derivation/merge (§7).
- **No** storage/cursor/checkpoint/persistence/run-state; **no** Cell-3 / COST binding/label / fee / cost-validity
  (§8); **no** capacity activation.
- **No** S5 generation/inference/mapping/injection of labels (§10); **no** runner-internal sourcing.
- **No** `GrossEdgeBindingLabelContext` field-shape or runtime here; **no** B2 ingestion runtime; **no** S5 runtime;
  **no** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Next Safe Step

- A **separately-authorized docs-only `GrossEdgeBindingLabelContext` field-shape charter** — fixing, at logical-
  attribute level, the **two** supplied binding labels (`normalized_field_name`, binding-level `source_field`) as
  exact non-empty strings carried verbatim, passive, no fabrication, no identity, no cost — followed by a
  **separately-authorized runtime DTO TDD slice** (frozen/slotted/methodless two-field carrier, structural guard
  only, mirroring the `MarketProvenanceContext` discipline).
- **Then** a **separately-authorized B2 ingestion runtime TDD slice** consuming the three passive inputs (payload +
  `MarketProvenanceContext` + `GrossEdgeBindingLabelContext`) into an exact `PublicRawSnapshotRecord` via the
  `75d011b` mapping.
- Independently: the **passive cost-context (Cell-3)** source for B3/Producer; the **S1 storage-medium** charter.
- Only after **both** the pass path (ingestion + labels + cost-context) **and** the halt path are contract-complete
  does an **S5 runtime TDD slice** become eligible.
- **No implementation is authorized by this charter.**

**Conclusion:** the `75d011b` §6b residual is resolved by **decision**: the GROSS_EDGE binding's
`normalized_field_name` and binding-level `source_field` are **externally-supplied passive provenance**, carried by a
**new, separate, immutable `GrossEdgeBindingLabelContext`** (Option B), **not** by extending the ratified ten-field
`MarketProvenanceContext` (Option A rejected — it would breach the `75f53a4` closeout and conflate snapshot-level with
binding-level provenance). The labels are **never fabricated, defaulted, generic, hard-coded, reused from the
record-level `source_field`, or inferred from the magnitude**; they assert **no** edge/score/direction/actionability;
they **conform to** the frozen B2 binding contract without altering it; and they are **identity-isolated** (no S2 /
`raw_snapshot_identity` / Silver-tuple derivation) and **cost/storage-free** (no Cell-3 / COST / persistence). With
this decision, the `75d011b` mapping is **conceptually 14/14** (a future ingestion boundary consumes three passive
inputs). This charter makes a **future `GrossEdgeBindingLabelContext` field-shape/runtime eligible** but authorizes
**no** runtime, **no** B2 ingestion, and **no** S5; existing modules remain **frozen**; the pass path is **not**
contract-complete; **S5 runtime remains ineligible**; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**.
**No executable work is authorized.**
