# Phase 6.1 B2 Passive Cost-Component Provenance Carrier Charter

> **This is a docs-only planning charter.** It plans the *future* B2 passive `cost_component_type` provenance
> carrier/route, following the necessity decision that a **closed cost-component vocabulary is NOT necessary for
> Phase 6.1**. It authorizes NO runtime, NO tests, NO lock-test edits, NO B2 runtime/schema/carrier
> implementation, NO Phase 5 runtime amendment, NO Master B3 wiring, NO Phase 5 integration, NO B4 scoring, NO
> durable logs, NO `edge_direction`, NO `staleness_threshold_ms`, NO Shadow Intent, NO capacity activation, NO
> Phase 6.2 work, NO pytest, NO graphify. **It defines no vocabulary values, designs no final runtime field
> name, and validates nothing.** It is subordinate to
> `docs/handoff/phase6_1_cost_component_vocabulary_necessity_decision_charter.md`,
> `docs/handoff/phase6_1_phase5_cost_component_vocabulary_values_charter.md`,
> `docs/handoff/phase6_1_phase5_cost_component_vocabulary_ownership_mechanism_decision_charter.md`,
> `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md`,
> `docs/handoff/phase6_1_completion_sequencing_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `cc99680dfa801f2e53ccea2a19000e26644f8b97`

---

## 1. Base / Dependency Chain

**Base commit:** `cc99680dfa801f2e53ccea2a19000e26644f8b97`.

References:

- `docs/handoff/phase6_1_cost_component_vocabulary_necessity_decision_charter.md` — verdict **B**
  (CLOSED_VOCAB_NOT_NECESSARY_FOR_PHASE_6_1): `cost_component_type` may remain passive provenance metadata;
  economics carried by signed magnitude; B2 carrier reframed from "needs closed vocabulary" to "needs a
  separately-authorized passive carrier/route charter." **This charter is that next planning step.**
- `docs/handoff/phase6_1_phase5_cost_component_vocabulary_values_charter.md` — values **BLOCKED**.
- `docs/handoff/phase6_1_phase5_cost_component_vocabulary_ownership_mechanism_decision_charter.md` — owner =
  **Phase 5**, mechanism = **M3**, both RATIFIED and preserved.
- `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md` — cells 1/2/4/5 ratified; **Cell 3**
  (cost-component) still gated.
- `docs/handoff/phase6_1_completion_sequencing_charter.md` — Master-B3 critical path.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Why This Carrier Charter Exists

The necessity decision removed the *closed-vocabulary precondition* on a B2 cost-type carrier but explicitly
left the carrier itself **UNBUILT, undesigned, and separately-gated**, and required its own charter under the
passive-provenance / router-only locks. This charter is that planning step: it fixes the **docs-level contract**
the future carrier must obey — passivity, no validation, absence behavior, structural placement, and payload
bounding — so that any later implementation charter is constrained rather than improvised. It implements
nothing, names no final runtime field where the repo does not force one, and validates nothing.

---

## 3. Current Ratified State (carried forward, unchanged)

- **Closed vocabulary NOT necessary for Phase 6.1** — `cost_component_type` is passive provenance metadata;
  economics live in the signed decimal magnitude (necessity charter, verdict B).
- **Owner = Phase 5; mechanism = M3** — preserved. Phase 5 retains the right/duty to close the set later; any
  future closure must proceed under M3 (authoritative values charter → later runtime lock). This charter does
  **not** reverse or weaken either.
- **Vocabulary values — still BLOCKED / not ratified.**
- **B2 cost-type carrier — still UNBUILT** (no field exists today; only `binding_role` and the optional
  carrier-only `zero_cost_evidence` exist in `phase6_1/b2_normalization_contract.py`).
- **Master B3 — still BLOCKED** (Cell 3 has no authorized carrier/route; `edge_direction` /
  `staleness_threshold_ms` remain separate, out-of-scope blockers).

---

## 4. Passive Provenance Contract (binding on any future carrier)

The future B2 cost-type carrier, if and when separately authorized for implementation, MUST obey:

1. **Passive provenance only.** `cost_component_type` is descriptive metadata that labels *what kind of cost a
   magnitude represents*, for human/audit readability. It MUST never control math, branching, scoring, routing,
   sizing, execution, `edge_direction`, verdicts, thresholds, or any Phase 5 gate outcome.
2. **Economics in the signed magnitude.** All cost economics — including fee-vs-rebate polarity — live
   **entirely** in the signed decimal magnitude (negative magnitude = credit/rebate). The label MUST NOT imply
   polarity, sign, scale, unit, or any arithmetic behavior.
3. **Carried verbatim.** When present, the value is carried exactly as supplied by the upstream artifact —
   no parsing, casting, normalizing, trimming-to-meaning, case-folding, or coercion that changes its content.
4. **No semantic authority at B2.** B2 is carrier-only. It does not own, close, default, infer, or interpret
   the vocabulary; it only carries the string.

This contract is consistent with the existing B2 carrier-only precedent `zero_cost_evidence` (optional,
verbatim, `None`-or-non-empty-string, no magnitude parsed at the boundary).

---

## 5. Absence / Nullability Decision — **RATIFIED (docs-level): Optional, `None` = absent**

**Decision:** the future carrier's absence behavior is **Optional with `None` meaning "no cost-type provenance
supplied"**; when present, the value is an **exact non-empty, non-whitespace string**. **Empty string MUST NOT
be used to mean absence.**

**Repo evidence supporting ratification (not invention):** `phase6_1/b2_normalization_contract.py` already
establishes this exact pattern for optional carrier-only metadata via
`_require_optional_zero_cost_evidence`: `None` is always type-valid (the documented "absent" state); a *supplied*
value must be an exact non-empty, non-whitespace `str`; and an empty/whitespace string is **rejected**, never
treated as a value or as absence. The passive cost-type carrier follows this established contract, so the
docs-level absence rule is **ratified by precedent**, not guessed.

**Hard absence locks:**

- **No empty-string-as-absence.** Empty/whitespace strings are invalid input, not a sentinel for "absent."
- **No catch-all absence semantics.** `UNKNOWN` / `OTHER` / `UNSPECIFIED` / `MISC` / `N/A` / `null`-string and
  any garbage-bin token are **forbidden** as absence markers; absence is `None` only.
- **Absence ≠ meaning.** `None` carries no cost meaning and triggers no default; it simply means the artifact
  supplied no cost-type provenance.

**Deferred to a later implementation charter:** the exact runtime field name, its precise type annotation, and
the validation-function shape. The *behavior* (Optional/`None`-absent, non-empty-when-present) is ratified here;
the *runtime form* is not fixed because the repo does not yet pin a specific field name for this carrier.

---

## 6. Structural Placement Decision — **Direction RATIFIED; exact runtime name DEFERRED**

**Direction (evidence-consistent, ratified at docs level):** the passive cost-type provenance string belongs as
an **optional carrier-only descriptor on the per-binding evidence record**, alongside the other provenance
descriptors (`component_name`, `normalized_field_name`, `source_field`, `binding_role`) on
`NormalizedEvidenceFieldBinding`, and **logically isolated from the numeric `unit_bound_magnitude`**.

**Rationale from repo structure:** `NormalizedEvidenceFieldBinding` already separates *naming/provenance*
fields from the single numeric `unit_bound_magnitude`, and already hosts an optional carrier-only metadata field
(`zero_cost_evidence`) of exactly this shape. Placing the cost-type provenance among the descriptor fields keeps
it next to the magnitude it describes **without** entangling it in the numeric value.

**Placement locks:**

- **No calculation implication.** Placement MUST NOT suggest the string participates in or modifies any
  magnitude, sum, or net-edge computation.
- **No normalization implication.** Placement MUST NOT imply the string is normalized, parsed, or reconciled
  against any field; it sits beside the magnitude as provenance, not as input.
- **Isolation from numeric fields.** The provenance string MUST remain a distinct field, never merged into,
  encoded within, or derived from `unit_bound_magnitude` or any numeric carrier.

**Deferred:** the exact runtime field name and record-level wiring are left to a later implementation charter,
because the repo does not yet pin a specific name for this carrier and this charter implements nothing.

---

## 7. Payload Bounding Constraints (docs-level; no validation implemented)

The carrier, if later authorized, MUST be **short, exact, format-uninterpreted provenance text**:

- **Scalar string only.** It is a single `str`. **No** JSON blobs, base64 payloads, nested structures,
  serialized objects, tuples/lists/dicts/sets, byte payloads, or large raw dumps. (Consistent with the existing
  B2 `_REJECTED_CONTAINER_TYPES` posture and tuple-only shape discipline.)
- **Short label, not a document.** It is a compact cost-type label (the kind of short token `TAKER_FEE` /
  `MAKER_REBATE` exemplify *as shape*, **not** as a ratified vocabulary — those remain fixtures, not contract).
  It is not a free-text description, comment field, or payload container.
- **Format-uninterpreted.** "Format-uninterpreted" means B2 does not parse, validate against a grammar, or
  attribute structure to the string's internal characters; it only carries it. Bounding is about size/shape
  (short scalar string, non-empty when present), **not** about meaning.
- **Passive ≠ unbounded.** Keeping the field open/passive does NOT license arbitrary-size or structured
  payloads. The concrete length/charset enforcement, if any, is left to a later implementation charter; this
  charter fixes only the docs-level intent (short scalar provenance string).

---

## 8. No-Validation / No-Inference Locks

- **No closed-set validation in B2.** No enum / `frozenset` / allowed-set / membership check on the cost-type
  string. (Contrast `binding_role`, which *is* a closed vocabulary — the cost-type carrier is **not** modeled
  that way.)
- **No fixture promotion.** `TAKER_FEE` / `MAKER_REBATE` remain **test fixtures**, never promoted to a B2
  contract or allowed-set.
- **No polarity inference.** B2 MUST NOT infer fee/rebate/credit polarity, sign, or any arithmetic behavior
  from the label.
- **No derivation.** The cost-type value MUST NOT be inferred from `normalized_field_name`, `source_field`,
  `binding_role`, unit, magnitude, sign, or tuple position. It is supplied by the artifact or it is `None`.
- **Future M3 closure stays open but separate.** A closed vocabulary remains *possible* only via a future,
  separately-chartered M3 values charter + later Phase 5 runtime lock. This carrier charter neither performs
  nor presupposes that closure, and ratifying this passive carrier does **not** pre-empt or weaken M3.
- **Router-only B3 (forward implication).** If this provenance is later routed through Master B3, B3 may only
  **carry/pass it through verbatim**. B3 MUST NOT parse, validate, normalize, coerce, branch, score, infer, or
  choose any behavior from it. (Stated here as a forward constraint; this charter authorizes no B3 wiring.)

---

## 9. Effect on B2 Cost-Type Carrier Status

- The carrier's **contract is now specified at docs level**: passive provenance, Optional/`None`-absent,
  non-empty-when-present, scalar short string, no validation, no derivation, descriptor-placement isolated from
  the magnitude.
- **Still UNBUILT and separately-gated for implementation.** No field is added, named (finally), typed, or
  implemented; no test or schema change is authorized. A later **implementation charter** (TDD slice) is
  required to add the field under this contract.
- Net status: B2 cost-type carrier moves from *"reframed/undefined"* to *"docs-contract ratified, runtime
  implementation pending a separate slice."*

---

## 10. Effect on Master B3 Status

- **Master B3 remains BLOCKED.** This charter specifies only the *B2* passive carrier contract; it does not
  add a B2 field, does not author any B3 route, and does not wire Cell 3.
- Cell 3's cost-type sub-blocker is further reduced to *"implement the ratified passive B2 carrier (separate
  slice), then separately charter a router-only B3 pass-through"* — but neither is authorized here.
- The separate Master-B3 blockers **`edge_direction`** (Shadow Intent Envelope track) and
  **`staleness_threshold_ms`** remain **untouched and out of scope**.

---

## 11. Still-Forbidden Work

- **No** vocabulary values defined/proposed/endorsed; **no** fixture promotion; **no** fallback/catch-all value.
- **No** B2 runtime/schema/carrier implementation; **no** final field name fixed where the repo does not force
  it; **no** validation function written; **no** test or lock-test edit.
- **No** Phase 5 runtime amendment; **no** Phase 5 integration.
- **No** Master B3 runtime/design/wiring; **no** B3 route authored; **no** B4 scoring; **no** durable logs;
  **no** output carrier; **no** Shadow Intent; **no** live adapter.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.
- **No** touching of `edge_direction` or `staleness_threshold_ms`.
- **No** reversal or weakening of the ratified owner (Phase 5) or mechanism (M3).

---

## 12. Next Safe Step

- A **separate B2 implementation charter / TDD slice** to add the passive cost-type provenance carrier to
  `phase6_1/b2_normalization_contract.py` under §4–§8 — Optional with `None`-absent, non-empty-when-present,
  scalar short string, no closed-set validation, no derivation — modeled on the existing `zero_cost_evidence`
  carrier-only pattern, with its exact runtime field name fixed at that point.
- Only after that may a **router-only Master B3 pass-through** be separately chartered (§8 lock), and only
  alongside independent resolution of the separate `edge_direction` and `staleness_threshold_ms` blockers may
  Master B3 wiring proceed.
- **No implementation is authorized by this charter.** The B2 carrier runtime, any Phase 5 vocabulary closure
  (under M3, if ever needed), Master B3 wiring, B4 scoring, durable logs, the live adapter, Shadow Intent
  Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.
