# Phase 6.1 Phase 5 Passive Pre-Net-Edge Carrier — Shape & Entry-Mechanism Design Charter

> **This is a docs-only architecture-design charter.** It designs, **at docs level only**, the exact *shape
> class* of the new Phase-5-owned passive pre-net-edge carrier and the *entry mechanism* by which the existing
> net-edge arithmetic could accept it in a future, separately-authorized slice. It **writes no code, no
> signature, no schema, and authorizes nothing executable.** It authorizes NO runtime, NO tests, NO lock-test
> edits, NO Python, NO interface/schema/runtime edits, NO Phase 5 runtime amendment, NO passive producer
> implementation, NO B2/B3 changes, NO Master B3 wiring, NO B4 scoring design/math, NO durable shadow logs, NO
> Shadow Intent Envelope, NO `edge_direction` reopening, NO `staleness_threshold_ms` reopening, NO capacity
> activation, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_phase5_net_edge_arithmetic_passive_access_carrier_reconciliation_charter.md`,
> `docs/handoff/phase6_1_passive_producer_classification_boundary_charter.md`,
> `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_v2_readiness_audit.md`, and `CLAUDE.md`;
> where any conflict arises, those govern.

**Base:** `6daca3326d62aa698ad07f135709bc6b25b6d9e3`

---

## 1. Base / Dependency Chain

**Base commit:** `6daca3326d62aa698ad07f135709bc6b25b6d9e3`.

References:

- `…_phase5_net_edge_arithmetic_passive_access_carrier_reconciliation_charter.md` — selected **Option A** (a new
  Phase-5-owned passive pre-net-edge input carrier feeding the existing arithmetic), **deferring** the exact
  shape and entry mechanism to this charter.
- `…_passive_producer_classification_boundary_charter.md` — passive producer boundary pinned (reuse existing
  arithmetic; no actionability).
- `…_master_b3_remaining_blockers_reclassification_v2_readiness_audit.md` — passive producer UNBUILT;
  `PassiveShadowInput` BUILT.

**No capacity validation and no capacity pass is claimed by this charter** (see §13).

---

## 2. Why This Charter Exists

The reconciliation charter fixed the architectural *class* (Option A) but deferred two concrete questions: **what
exact shape** the passive carrier has, and **by what exact-typed mechanism** the existing `calculate_net_edge`
arithmetic accepts it without faking actionability, duplicating math, or weakening type safety. This charter
answers both **at docs level** so a future, separately-authorized Phase-5 TDD slice is fully constrained. It
designs no runtime.

---

## 3. Evidence Inventory Inspected (read-only)

- **Arithmetic data dependency** — `calculate_net_edge` reads off the gross slot only `gross_edge_value` and
  `gross_edge_unit`, and off each cost context only `cost_observation.signed_decimal_value` and `.unit`. It
  computes `net = gross − Σ cost_i`.
- **Magnitude/unit constraints (actionable side)** — `gross_edge_value` is a **canonical decimal string**
  (`_CANONICAL_DECIMAL = r"-?\d+(\.\d+)?"`), exact non-empty `str`, preserved verbatim; `gross_edge_unit` is an
  exact non-empty `str`. The calculator **re-validates** both defensively (malformed → BlockedPacket).
- **Entry discipline** — `calculate_net_edge` runs `reject_misrouted_halt_carrier(...)` then
  `if type(calculation_input) is not PreNetEdgeCalculationInput: raise NetEdgeCalculatorTypeError` — **strict
  exact-type, no `isinstance`**.
- **Input carrier** — `PreNetEdgeCalculationInput` type-pins `gross_observation` to exact `GrossEdgeObservation`
  and requires a **non-empty** `cost_validity_contexts` tuple of exact `ObservableCostValidityContext`.
- **Actionability bundle** — `GrossEdgeObservation` carries 24 fields (incl. `edge_direction`,
  `venue_scope/buy/sell`, depth provenance, `staleness_threshold_ms`) — none read by the arithmetic.

---

## 4. Non-Negotiable Invariants

1. **Actionable path 100% unchanged.** `GrossEdgeObservation` and `PreNetEdgeCalculationInput` keep their exact
   fields, validation, and semantics; existing actionable producers/consumers need **zero** refactor.
2. **No new math.** The existing `calculate_net_edge` algebra is the **single math source**; no duplication, no
   `calculate_passive_net_edge`, no second engine.
3. **No fake actionability.** No constructed/dummy `GrossEdgeObservation`; no `edge_direction`
   default/placeholder/synthetic/mock.
4. **Exact typing only.** `type(x) is Exact` discipline; **no** `Protocol`/`Any`/`dict`/blob/duck-typing/unbounded
   mapping/generic container.
5. **Magnitude/unit integrity undiminished.** Removing actionability must **not** relax gross magnitude/unit
   validation (§9).
6. **Zero-valued cost context.** Zero cost = a zero-valued cost context, never an empty tuple, never a Cell-3
   dependency (§10).

---

## 5. Passive Carrier Shape Decision — **SELECTED (two exact-typed sibling carriers)**

Two new Phase-5-owned, frozen / slotted / init-blocked / anti-coercion, **exact-typed** carriers (described by
their conceptual field sets — **no code/signature here**):

**(a) Passive gross-edge magnitude carrier** — the non-actionable counterpart of the *magnitude portion only* of
`GrossEdgeObservation`. Conceptual fields:
- `gross_edge_value` — exact non-empty `str`, **canonical decimal** (same `_CANONICAL_DECIMAL` constraint, verbatim).
- `gross_edge_unit` — exact non-empty `str`.
- `boundary_version` / `component_name` — exact non-empty `str` provenance (mirroring existing carrier discipline).
- **Excluded entirely:** `edge_direction`, `venue_scope`/`venue_buy`/`venue_sell`, `observed_at_epoch_ms`,
  `staleness_threshold_ms`, depth provenance, `base_asset`/`quote_asset`/`instrument_id`, `observed_size`/`size_unit`,
  and any actionability/intent field. It carries **only** the two magnitude fields the arithmetic actually reads,
  plus provenance.

**(b) Passive pre-net-edge input carrier** — the sibling of `PreNetEdgeCalculationInput`. Conceptual fields:
- a **passive gross-edge magnitude carrier** (exact type (a)) in place of the actionable `gross_observation`;
- `cost_validity_contexts` — exact, **non-empty** `tuple` of exact `ObservableCostValidityContext` (identical
  constraint to the actionable carrier; preserved verbatim, never copied/sorted/filtered/aggregated);
- `boundary_version` — exact non-empty `str`.

These are **sibling** carriers: they do **not** subclass, wrap, or mutate the actionable carriers, and the
actionable carriers gain **no** awareness of them.

---

## 6. Entry Mechanism Decision — **SELECTED: additive exact-typed Union at the existing arithmetic entry**

The existing `calculate_net_edge` entry is extended **additively** to accept **either** the unchanged exact
`PreNetEdgeCalculationInput` **or** the new exact passive pre-net-edge input carrier, discriminated by **exact
type** (`type(x) is PreNetEdgeCalculationInput` … `or type(x) is <PassivePreNetEdgeCalculationInput>`), never by
`isinstance`/Protocol. Both branches feed the **same** internal algebra, which reads only the two shared
magnitude fields + the cost contexts.

- **Rejected — sibling/separate entry function.** A second entry (e.g. `calculate_passive_net_edge`) is
  **forbidden** (invariant 2 / lock): it would either duplicate the algebra or require faking a
  `GrossEdgeObservation` to delegate. Not selected.
- **Rejected — Union inside `PreNetEdgeCalculationInput.gross_observation`.** Widening the *actionable* carrier's
  gross slot would make the actionable carrier aware of the passive type and change its validation — violating
  invariant 1. Not selected.
- **Selected — Union at the top-level `calculate_net_edge` input type.** Additive; the actionable carriers
  (`GrossEdgeObservation`, `PreNetEdgeCalculationInput`) are byte-for-byte unchanged; the actionable branch is
  unchanged; the passive branch is a new, exact-typed alternative reading the same fields. **Single math source
  preserved.**

**Phase-5-ownership flag (designed nowhere here):** the only modification is the additive exact-type branch at
the shared `calculate_net_edge` entry (and the two new carriers). Because this touches the shared, audited net-
edge entry, the future implementation slice MUST obtain explicit Phase-5-owner ratification and prove the
actionable branch unchanged (§7). No code, signature, or `type(...)` expression is authored here.

---

## 7. Backward-Compatibility Proof (docs level)

- **Actionable carriers unchanged.** No field added/removed/reordered on `GrossEdgeObservation` or
  `PreNetEdgeCalculationInput`; their factories and validation are untouched. Existing construction sites compile
  and behave identically.
- **Actionable consumers need zero refactor.** Any caller passing a `PreNetEdgeCalculationInput` hits the
  **same** first exact-type branch and the **same** algebra and result; the passive branch is unreachable for
  them. No signature change to `calculate_net_edge`'s keyword (`calculation_input`) is required by the design.
- **Additive-only discrimination.** The passive branch is a new `or type(x) is <Passive…>` alternative evaluated
  **after** the actionable check; it cannot alter the actionable outcome. `reject_misrouted_halt_carrier` and the
  malformed→BlockedPacket guards apply unchanged.
- **Single math source.** Both branches converge on the identical gross-minus-cost algebra; there is no second
  computation to drift.
- **No type-safety erosion.** Discrimination stays `type(x) is Exact`; no `isinstance`, `Protocol`, `Any`,
  `dict`, or container widening is introduced.

This proof is **architectural**; the implementing slice must reproduce it as executable tests (separately
authorized).

---

## 8. Naming Constraints & Selected Naming Class

- **Forbidden:** vague/blob/dummy/raw/shadow-style names (`ShadowInput`, `Payload`, `Blob`, `RawInput`,
  `DummyGross`, `GenericInput`), and any name implying actionability, intent, direction, scoring, logging, or B4.
- **Required:** precise, quantitative names that **mirror the actionable counterparts** with an explicit
  non-actionability qualifier, naming exactly what is carried.
- **Selected naming class (final tokens subject to Phase-5-owner confirmation at implementation):**
  - input carrier → mirror `PreNetEdgeCalculationInput` with a passive/non-actionable qualifier, e.g.
    **`PassivePreNetEdgeCalculationInput`**;
  - magnitude carrier → name the exact quantity it holds, e.g. **`PassiveGrossEdgeMagnitude`** (carries
    `gross_edge_value` + `gross_edge_unit` only).
  These are recorded as the **naming class/intent**, not a binding identifier; **no module or symbol is created.**

---

## 9. Magnitude / Unit Integrity Constraints

Removing actionability MUST NOT weaken numeric integrity. The passive magnitude carrier MUST enforce constraints
**equivalent to the actionable counterpart**:

- `gross_edge_value` — exact non-empty `str`, **canonical decimal** per the same `_CANONICAL_DECIMAL` rule,
  preserved verbatim (no parse/coerce/round).
- `gross_edge_unit` — exact non-empty, non-whitespace `str`.
- Cost contexts — exact, non-empty `tuple` of exact `ObservableCostValidityContext`; each
  `cost_observation.signed_decimal_value` canonical decimal and `.unit` exact non-empty `str` (as the arithmetic
  already re-validates).
- The calculator's existing **defensive re-validation** (malformed → BlockedPacket) applies identically to the
  passive branch — integrity is **fail-fast and undiminished**.

---

## 10. Zero-Valued Cost Context Handling

- The passive input carrier requires a **non-empty** `cost_validity_contexts` tuple (identical to the actionable
  carrier). A zero/absent-cost economic scenario is represented by a **zero-valued cost context** — a valid
  `ObservableCostValidityContext` wrapping a zero-magnitude cost observation — **never** an empty tuple.
- This requires **no** cost-type *provenance* (Cell-3 `cost_component_provenance_reference` remains optional/
  deferred). The minimal passive net-edge path does **not** depend on the Cell-3 route.
- No Cell-3 route is designed here.

---

## 11. What This Enables and Does Not Enable

- **Enables (conceptually):** a fully-specified docs blueprint — two exact-typed sibling carriers + an additive
  exact-typed Union entry — that a future, separately-authorized Phase-5 TDD slice could implement to let the
  existing arithmetic produce a non-actionable `NetEdgeCalculationResult` from passive evidence.
- **Does NOT enable:** any runtime. No carrier, factory, Union branch, or test is created; no Phase 5 file is
  edited; the passive producer is not implemented; Master B3 is not wired; B4 is not designed.

---

## 12. Remaining Blockers

Unchanged in count; the passive-carrier blocker is now **fully specified (design-ready), still UNBUILT**:

1. **Passive pre-net-edge carrier + Union entry — design-ready, UNBUILT (Phase-5-owned).** Implementation is a
   separate, owner-ratified Phase-5 TDD slice.
2. **Passive producer — UNBUILT.** Depends on (1).
3. **Master B3 passive wiring — UNBUILT.** Depends on (2).
4. **B3 router-only Cell-3 cost-type pass-through — UNBUILT (separate/parallel).**

Tombstoned: `edge_direction`, `staleness_threshold_ms`. Built: B2 carriers (incl. cost-type provenance),
`PassiveShadowInput` type+factory, mapping cells 1/2/4/5. **Master B3 remains BLOCKED.**

---

## 13. Still-Forbidden Work

- **No** code/signature/schema/module/symbol creation; **no** Phase 5 runtime amendment; **no** Union branch or
  carrier implemented; **no** test.
- **No** new math / `calculate_passive_net_edge` / duplicated algebra.
- **No** fake/dummy `GrossEdgeObservation`; **no** `edge_direction` default/placeholder/synthetic/mock.
- **No** `Protocol`/`Any`/`dict`/blob/duck-typing/unbounded container; **no** weakening of exact-type checks; **no**
  change to the actionable carriers or their consumers.
- **No** passive producer implementation; **no** B2/B3 change; **no** Master B3 wiring; **no** B4 scoring/logging;
  **no** durable logs; **no** Shadow Intent Envelope; **no** Cell-3 route design.
- **No** reopening of `edge_direction`, `staleness_threshold_ms`, or cost vocabulary values; **no** weakening of
  the B2 passive cost-type carrier invariants.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 14. Next Safe Step

- A **separately-authorized Phase-5-owned TDD slice** to implement (1): the two exact-typed sibling carriers and
  the additive exact-typed Union branch at `calculate_net_edge`, under §4–§10, with executable backward-
  compatibility tests proving the actionable path byte-for-byte unchanged — **requiring explicit Phase-5-owner
  ratification** before any edit to the shared net-edge entry.
- The B3 router-only Cell-3 cost-type pass-through may be separately authorized at any time (parallel).
- **No implementation is authorized by this charter.** The passive carrier/Union, the passive producer, Master
  B3 wiring, the Cell-3 route, B4 scoring, durable logs, Phase 5 modification, the Shadow Intent Envelope,
  capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.
