# Phase 6.1 Phase 5 Net-Edge Arithmetic — Passive Access & Carrier Reconciliation Charter

> **This is a docs-only classification/reconciliation charter.** It conceptually resolves the §8 tension from the
> passive producer charter — the net-edge arithmetic is `edge_direction`-free, but its current input carrier path
> requires the actionability-bundled `GrossEdgeObservation`. It **classifies** the legitimate architectural path
> for passive access to the **existing** net-edge arithmetic and **designs/implements nothing**. It authorizes NO
> runtime, NO tests, NO lock-test edits, NO Python code, NO interface/schema/runtime edits, NO Phase 5 runtime
> amendment, NO passive producer implementation, NO B2/B3 runtime/schema/carrier changes, NO Master B3 wiring, NO
> B4 scoring design/math, NO durable shadow logs, NO Shadow Intent Envelope design/runtime/schema, NO
> `edge_direction` reopening, NO `staleness_threshold_ms` reopening, NO capacity activation, NO Phase 6.2 work, NO
> pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_passive_producer_classification_boundary_charter.md`,
> `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_v2_readiness_audit.md`,
> `docs/handoff/phase6_1_phase5_gross_edge_gate_invocation_necessity_decision_charter.md`,
> `docs/handoff/phase6_1_passive_entrypoint_slice0a_handoff_pinning_classification_sequencing_charter.md`,
> `docs/handoff/phase6_1_shadow_input_wrapper_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `aaec029edb65a4e0c2280923cce8d55041068610`

---

## 1. Base / Dependency Chain

**Base commit:** `aaec029edb65a4e0c2280923cce8d55041068610`.

References:

- `…_passive_producer_classification_boundary_charter.md` — recorded the **§8 open reconciliation**: reuse
  `calculate_net_edge` without the gross-edge actionability gate; designed nothing.
- `…_phase5_gross_edge_gate_invocation_necessity_decision_charter.md` — gross-edge gate **NOT_NECESSARY**;
  net-edge arithmetic `edge_direction`-independent.
- `…_passive_entrypoint_slice0a_handoff_pinning_…_charter.md` — passive handoff = magnitude-only
  `NetEdgeCalculationResult` by identity; parallel track isolated from the intent gate.
- `…_master_b3_remaining_blockers_reclassification_v2_readiness_audit.md` — passive producer UNBUILT (critical
  path); `PassiveShadowInput` BUILT.
- `…_shadow_input_wrapper_charter.md` — `PassiveShadowInput` references `NetEdgeCalculationResult`.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Why This Reconciliation Exists

The passive producer cannot reuse `calculate_net_edge` without resolving one tension: the arithmetic never reads
`edge_direction`, yet the *only* current input path into it requires an exact `GrossEdgeObservation`, which
mandates `edge_direction` and a full actionability bundle. The passive producer charter forbade a fake/dummy
`GrossEdgeObservation` and any bypass, and required reuse of the existing arithmetic — leaving the reconciliation
**open**. This charter **classifies** the legitimate Phase-5-owned path to present passive evidence to the
existing arithmetic, **without** inventing math, faking actionability, or designing a runtime carrier.

---

## 3. Evidence Inventory Inspected (read-only)

- **`phase5/net_edge_calculator_boundary.py::calculate_net_edge`** reads from the gross observation **exactly two
  attributes** — `gross.gross_edge_value` and `gross.gross_edge_unit` — and from each cost context only
  `context.cost_observation.signed_decimal_value` and `.unit`. It validates these as canonical decimals/units and
  computes `net = gross − Σ cost_i`. It reads **none** of the actionability fields.
- **`phase5/gross_edge_observation_boundary.py::GrossEdgeObservation`** is a **24-field** frozen carrier bundling
  actionability/identity/provenance — `edge_direction`, `venue_scope`/`venue_buy`/`venue_sell`,
  `observed_at_epoch_ms`, `staleness_threshold_ms`, depth provenance, etc. — alongside the two magnitude fields
  the arithmetic actually uses.
- **`PreNetEdgeCalculationInput`** type-pins `gross_observation` to an **exact `GrossEdgeObservation`** and
  requires a **non-empty** `cost_validity_contexts` tuple of exact `ObservableCostValidityContext` (empty
  rejected).

**Conclusion from evidence:** the arithmetic's real data dependency on the gross observation is **two magnitude
fields**; the actionability is **bundled by the carrier type**, not consumed by the math. The reconciliation
surface is precisely *how a non-actionable gross magnitude/unit (+ cost contexts) reaches the existing arithmetic*.

---

## 4. Current Phase 5 Arithmetic Boundary

`calculate_net_edge(*, calculation_input)` is the **immutable arithmetic core** for this charter: gross-minus-cost
algebra over canonical signed decimals with exact unit-token compatibility, returning a `NetEdgeCalculationResult`
(magnitude/unit/status only, `edge_direction`-free) on a pass or an existing Phase 5 blocked/halt carrier
otherwise. It is Phase-5-owned and **must not be re-implemented or duplicated**.

---

## 5. Current Actionability-Bundled Carrier Problem

To reach `calculate_net_edge` today, one must build a `PreNetEdgeCalculationInput`, whose `gross_observation` must
be an exact `GrossEdgeObservation` — which **cannot be constructed without `edge_direction`** and the full
actionability bundle. Thus the **only** current door into the (non-actionable) arithmetic is **actionability-
gated by carrier type**. A passive path may neither fake that carrier (forbidden) nor bypass it (forbidden) — so
a **legitimate, Phase-5-owned, non-actionable presentation** of the two magnitude fields (+ cost contexts) to the
same arithmetic is required.

---

## 6. Non-Negotiable Invariants

Any legitimate future path MUST preserve all of:

1. **No new math.** The existing `calculate_net_edge` arithmetic core is **immutable** for this charter — no
   `calculate_passive_net_edge`, no second engine, no duplicated gross-minus-cost logic.
2. **No fake/dummy actionability.** No constructed/dummy `GrossEdgeObservation`; no
   DEFAULT/NONE/ALWAYS_LONG/ALWAYS_SHORT/CROSS_VENUE/synthetic `edge_direction`; no actionability mocked to
   satisfy a type checker.
3. **Type safety preserved.** Exact-type discipline (`type(x) is Exact`) is retained; **no** `Any`, `dict`,
   unbounded mapping, blob, generic container, or structural/duck typing is introduced to widen acceptance.
4. **Actionable path untouched.** The existing `GrossEdgeObservation` / `PreNetEdgeCalculationInput` /
   actionable flow remains strictly unchanged in type, validation, and semantics.
5. **Zero-valued cost context preserved.** Zero cost is represented as a **zero-valued cost context** (a valid
   `ObservableCostValidityContext` with a zero-magnitude cost observation), **never** an empty cost tuple, and
   **without** requiring the deferred Cell-3 cost-type provenance route.

---

## 7. Legitimate Architecture Options (compared, not implemented)

- **Option A — New Phase-5-owned passive pre-net-edge input carrier.** A separate, frozen, exact-typed,
  non-actionable Phase-5-owned carrier presenting only `gross_edge_value`/`gross_edge_unit` (+ a non-empty
  cost-context tuple) to the existing arithmetic, as a **sibling** to the actionable `PreNetEdgeCalculationInput`.
  *Pros:* leaves the actionable carrier untouched; Phase-5-owned; reuses the arithmetic; exact-typed.
  *Risk:* requires a future Phase-5-owned amendment so the arithmetic entry recognizes the new exact input type.
- **Option B — Typed Protocol / abstract structural boundary.** Define a Protocol (`has gross_edge_value,
  gross_edge_unit`) both carriers satisfy. **Rejected:** structural/duck typing directly violates the codebase's
  exact-type (`type(x) is …`, no `isinstance`) discipline and would weaken the actionable path's guarantee
  (invariant 3).
- **Option C — Explicit Union of actionable/passive carriers at the entry.** The Phase-5 entry accepts
  `GrossEdgeObservation`-backed input **or** a passive carrier via **exact-type discrimination**
  (`type(x) is A or type(x) is B`), reading only the two shared magnitude fields.
  *Pros:* exact-typed; Phase-5-owned; reuses the arithmetic.
  *Risk:* larger blast radius on the shared entry; must prove the actionable branch is byte-for-byte unchanged.
- **Option D — BLOCKED/DEFERRED.** If evidence is insufficient to choose safely.

---

## 8. Decision / Classification — **SELECTED at class level: Option A (carrier shape DEFERRED)**

**Selected (conceptual, Phase-5-owned): Option A — a new Phase-5-owned, non-actionable passive pre-net-edge input
carrier** (presenting only gross magnitude/unit + a non-empty cost-context tuple) consumed by the **existing**
`calculate_net_edge` arithmetic, with the actionable `GrossEdgeObservation` / `PreNetEdgeCalculationInput` path
**strictly untouched**.

**Why A, on evidence (not convenience):**

- The arithmetic's proven dependency is exactly two magnitude fields (+ cost contexts) — a passive sibling carrier
  can present them with **no** actionability and **no** new math (invariants 1, 2).
- A *separate* passive carrier keeps the actionable path **completely untouched** (invariant 4) — strictly safer
  than mutating the shared entry.
- It is **Phase-5-owned** and exact-typed (invariant 3); it rejects the structural-typing Option B outright.

**Explicitly DEFERRED (not designed here):** the concrete passive carrier's **field set/shape**, and the **exact
mechanism** by which the arithmetic entry accepts it (a new sibling exact input type vs. an exact-type-
discriminated Union, i.e. the A-vs-C entry detail). Both candidate mechanisms preserve exact typing; choosing
between them is a **future Phase-5-owned design decision**. Per the "prefer deferral over inventing a carrier
shape" posture, **no shape, field list, or signature is invented here.** Option D (full BLOCKED) is **not**
required because the architectural *class* is evidence-justified; only the *shape/mechanism* is deferred.

This selection **reduces** the §8 open reconciliation from "unclassified" to "architectural class fixed (Option A,
Phase-5-owned), shape/mechanism deferred to a future Phase-5 design slice." **No runtime is authorized.**

---

## 9. Consequence for the Passive Producer

- The passive producer's §8 prerequisite is now **classified**: it would target a future **Phase-5-owned passive
  pre-net-edge input carrier** (Option A) feeding the existing arithmetic to obtain a non-actionable
  `NetEdgeCalculationResult`, which the built `PassiveShadowInput` references by identity.
- The producer remains **UNBUILT**; its implementation is still gated on the future Phase-5-owned passive carrier
  (shape/mechanism deferred). Nothing about the producer is designed or authorized here.

---

## 10. Consequence for Master B3 Readiness

- **Master B3 remains BLOCKED.** This charter authorizes no runtime and wires nothing.
- It **reduces** one blocker's ambiguity: the §8 reconciliation is no longer open — it is a single, well-scoped,
  Phase-5-owned future design item (the passive pre-net-edge input carrier shape + arithmetic-entry acceptance).
  The remaining Master-B3 blockers are otherwise unchanged: passive carrier shape/mechanism (Phase 5) → passive
  producer → Master B3 passive wiring; plus the separate/parallel router-only Cell-3 route. `edge_direction` and
  `staleness_threshold_ms` remain tombstoned.

---

## 11. Still-Forbidden Work

- **No** new arithmetic / second math engine / duplicated gross-minus-cost logic; the existing
  `calculate_net_edge` core is immutable here.
- **No** fake/dummy `GrossEdgeObservation`; **no** DEFAULT/NONE/ALWAYS_*/synthetic `edge_direction`; **no**
  actionability mocked for a type checker.
- **No** bypass functions, adapter hacks, monkeypatching, or actionability-smuggling wrappers; **no** runtime
  interface.
- **No** Phase 5 runtime amendment; **no** passive carrier shape/field/signature designed; **no** arithmetic-entry
  change implemented.
- **No** weakening of exact-type checks (no `Any`/`dict`/unbounded mapping/blob/Protocol-duck-typing); the
  actionable path stays untouched.
- **No** B2/B3 runtime/schema/carrier change; **no** Master B3 wiring; **no** passive producer implementation;
  **no** B4 scoring/logging/calibration; **no** durable logs; **no** Shadow Intent Envelope; **no** Cell-3 route
  design.
- **No** reopening of `edge_direction`, `staleness_threshold_ms`, or cost vocabulary values; **no** weakening of
  the B2 passive cost-type carrier invariants.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Next Safe Step

- A **separately-authorized docs-only Phase-5-owned design charter** for the **passive pre-net-edge input
  carrier** (Option A) — fixing its exact field set (gross magnitude/unit + non-empty zero-capable cost contexts)
  and the exact-type acceptance mechanism at the arithmetic entry (sibling input vs. exact-typed Union), with the
  actionable path proven untouched — still designing no runtime until that authorization, after which a Phase-5
  TDD slice could be separately chartered.
- The B3 router-only Cell-3 cost-type pass-through may be separately authorized at any time (parallel).
- **No implementation is authorized by this charter.** The passive carrier, the passive producer, Master B3
  wiring, the Cell-3 route, B4 scoring, durable logs, Phase 5 modification, the Shadow Intent Envelope, capacity
  activation, Phase 6.2, and 7.x/8.x remain separately gated.
