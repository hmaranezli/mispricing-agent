# Phase 5 Passive Pre-Net-Edge Carrier TDD — Closeout / Ratification Charter

> **This is a docs-only closeout/ratification charter.** It ratifies and freezes the **completed** Phase 5
> passive pre-net-edge carrier TDD slice (commit `44c455b`) before any Passive Producer or Master B3 work. It
> **builds and designs nothing**. It authorizes NO runtime, NO tests, NO lock-test edits, NO Python, NO
> interface/schema/runtime edits, NO Phase 5 runtime amendment, NO passive producer implementation/design, NO
> B2/B3 changes, NO Master B3 wiring, NO B4 scoring design/math, NO durable shadow logs, NO Shadow Intent
> Envelope, NO `edge_direction` reopening, NO `staleness_threshold_ms` reopening, NO capacity activation, NO
> Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_phase5_passive_pre_net_edge_carrier_shape_entry_mechanism_design_charter.md`,
> `docs/handoff/phase6_1_phase5_net_edge_arithmetic_passive_access_carrier_reconciliation_charter.md`, and
> `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `44c455b30aed4dfca58d8b18ab9bdd32edf10a96`

---

## 1. Base / Dependency Chain

**Base commit:** `44c455b30aed4dfca58d8b18ab9bdd32edf10a96`.

References:

- `…_phase5_passive_pre_net_edge_carrier_shape_entry_mechanism_design_charter.md` — designed the carrier shape
  (two exact-typed sibling carriers) and the additive exact-typed Union entry, implemented by this slice.
- `…_phase5_net_edge_arithmetic_passive_access_carrier_reconciliation_charter.md` — selected Option A
  (Phase-5-owned passive carrier reusing the existing arithmetic).

**Implemented commit under closeout:** `44c455b` (parent `a630d5d`).

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Why This Closeout Exists

The passive pre-net-edge carrier slice is implemented and green. Before any Passive Producer or Master B3 work is
chartered, its guarantees must be **frozen as ratified invariants** so no later step can silently widen the
Phase 5 boundary, duplicate the math, weaken type safety, or disturb the actionable path. This charter records
the proof, ratifies the invariants (including a **Frozen Socket Rule** and an **AST exact-typing invariant**),
and advances nothing executable.

---

## 3. Evidence Inventory Inspected (read-only)

- **`phase5/net_edge_calculator_boundary.py`** — adds two frozen, anti-coercion, exact-typed sibling carriers
  `PassiveGrossEdgeMagnitude` and `PassivePreNetEdgeCalculationInput` (+ factories
  `make_passive_gross_edge_magnitude`, `make_passive_pre_net_edge_calculation_input` and construction-error
  classes), and an **additive exact-typed Union** at `calculate_net_edge`
  (`type(x) is PreNetEdgeCalculationInput or type(x) is PassivePreNetEdgeCalculationInput`). Both carriers expose
  `.gross_observation` (with `gross_edge_value`/`gross_edge_unit`) and `.cost_validity_contexts`, so the **same**
  algebra reads either. No `calculate_passive_net_edge`; no isinstance/Protocol/Any.
- **`tests/test_phase5_passive_pre_net_edge_carrier.py`** — locks shape/integrity, actionable parity, identical
  math, defensive malformed handling, exact-typing AST locks, no-second-engine, and zero-valued cost context.
- **`tests/test_phase5_net_edge_calculator_boundary.py`** — the existing actionable suite, unchanged, still
  green.

---

## 4. Ratified Runtime Surface

The following surface is **BUILT + RATIFIED** at `44c455b`:

- **`PassiveGrossEdgeMagnitude`** — frozen non-actionable carrier of `gross_edge_value` (exact non-empty
  canonical decimal str, verbatim) + `gross_edge_unit` (exact non-empty str) + provenance. **No**
  `edge_direction`/venue/staleness/actionability field exists on it; its factory accepts no such kwarg.
- **`PassivePreNetEdgeCalculationInput`** — frozen sibling of `PreNetEdgeCalculationInput` holding an exact
  `PassiveGrossEdgeMagnitude` in `gross_observation` and a non-empty exact `ObservableCostValidityContext` tuple,
  preserved verbatim.
- **Additive exact-typed Union at `calculate_net_edge`** — accepts the actionable input (unchanged) **or** the
  passive input, by exact type; both feed the single existing algebra.

No further change to this surface is authorized by this charter.

---

## 5. Ratified Tests / Proof

- **RED:** `ImportError: cannot import name 'PassiveGrossEdgeMagnitude' from
  'phase5.net_edge_calculator_boundary'` — feature genuinely missing (not a typo).
- **GREEN:** **69 passed** for the slice tests + the existing net-edge boundary suite together.
- **Coupled consumers (targeted):** `pre_net_edge_calculation_input`, `net_edge_profitability_gate`,
  `pre_net_edge_calculation_input_gate`, `post_profitability_evidence_envelope_boundary` → **107 passed**.
- **No broad pytest** was run.
- **Intermediate RED note:** one *test-only* flaw — a brittle substring check matched the word "isinstance" in a
  runtime **comment**; replaced with an AST check (the proper AST lock already proved no `isinstance` **call**).
  Documentation/test-assertion fix only; **no runtime logic change**.
- **Changed-file scope (exactly two):** `phase5/net_edge_calculator_boundary.py`,
  `tests/test_phase5_passive_pre_net_edge_carrier.py`.

---

## 6. Ratified Invariants

### 6.1 — Actionable path isolation (RATIFIED)
The existing actionable `PreNetEdgeCalculationInput` / `GrossEdgeObservation` path remains **100% unchanged and
backward-compatible** (no field/validation/semantic change; 107 coupled consumer tests + the actionable suite
green). Future passive work **must not** require actionable consumers to refactor or to know the passive side
exists.

### 6.2 — Frozen Socket Rule (RATIFIED)
The Phase 5 passive input **signature is now frozen** for downstream clients: the exact-typed
`PassivePreNetEdgeCalculationInput` (holding an exact `PassiveGrossEdgeMagnitude` + a non-empty
`ObservableCostValidityContext` tuple), consumed by `calculate_net_edge`, **is the socket**. A future Passive
Producer **must conform to this signature** and is **forbidden** from requesting, widening, mutating, subclassing,
or otherwise altering the Phase 5 boundary (no new fields, no relaxed types, no extra entry). Any boundary change
would require a **separate, Phase-5-owner-ratified** charter.

### 6.3 — Single math source (RATIFIED)
**No `calculate_passive_net_edge` exists or is authorized.** The existing `calculate_net_edge` is the **single**
net-edge arithmetic source; both inputs converge on it. No duplication, no second engine.

### 6.4 — Exact typing / AST lock invariant (RATIFIED + ELEVATED)
The runtime contains **no** `Protocol`, `Any`, `dict`/blob/duck typing, broad `isinstance`, or loose structural
typing; discrimination is exact-type (`type(x) is …`). This **AST-level no-isinstance / no-duck-typing lock is
elevated to a Phase 6.1 invariant** for all passive arithmetic access and downstream producer/wiring work: any
future passive producer or Master B3 wiring slice must preserve it and prove it by AST test.

### 6.5 — No fake actionability (RATIFIED)
**No** fake/dummy `GrossEdgeObservation`; **no** `edge_direction` default/placeholder/synthetic/mock. The passive
carriers carry no direction; an actionable `GrossEdgeObservation` is rejected from the passive gross slot.

### 6.6 — Error-domain isolation (RATIFIED)
A malformed passive carrier is handled **defensively** — the calculator's `_CANONICAL_DECIMAL` re-validation
returns a `BlockedPacket` (fail-closed), exactly as on the actionable path. A malformed passive input **must not**
crash, throw through, or degrade the actionable evaluation path; the two domains are isolated.

### 6.7 — Zero-valued cost context (RATIFIED)
Zero cost is a **zero-valued cost context**, never an empty cost tuple; the **empty tuple remains rejected**. The
minimal passive net-edge path introduces **no Cell-3 route dependency** (cost-type provenance stays optional/
deferred).

---

## 7. Frozen Socket Rule (summary)

The passive socket = `calculate_net_edge` accepting an exact `PassivePreNetEdgeCalculationInput`
(exact `PassiveGrossEdgeMagnitude` + non-empty exact `ObservableCostValidityContext` tuple). Downstream is a
**conformance client**, never a boundary author. See §6.2. (Restated here as the load-bearing rule for the next
slice.)

---

## 8. Exact Typing / AST Lock Invariant (summary)

Phase 6.1 passive arithmetic access and all downstream producer/wiring work inherit the AST exact-typing
invariant: **no** isinstance/Protocol/Any/dict/blob/duck typing; exact-type discrimination only; provable by AST
test. See §6.4.

---

## 9. Error-Domain Isolation & Zero-Valued Cost Context (summary)

Malformed passive carriers → defensive `BlockedPacket`, isolated from the actionable path (§6.6). Zero cost =
zero-valued cost context; empty tuple rejected; no Cell-3 dependency (§6.7).

---

## 10. Still-Forbidden Work

- **No** change to the ratified runtime surface (§4); **no** Phase 5 boundary widening/mutation; **no** new entry
  or field.
- **No** new math / `calculate_passive_net_edge` / duplicated algebra.
- **No** fake/dummy `GrossEdgeObservation`; **no** `edge_direction` default/placeholder/synthetic/mock.
- **No** `Protocol`/`Any`/`dict`/blob/duck-typing/broad-isinstance; **no** weakening of exact-type checks; **no**
  change to actionable carriers/consumers.
- **No** passive producer implementation/design; **no** B2/B3 change; **no** Master B3 wiring; **no** B4
  scoring/logging; **no** durable logs; **no** Shadow Intent Envelope; **no** Cell-3 route.
- **No** reopening of `edge_direction`, `staleness_threshold_ms`, or cost vocabulary values; **no** weakening of
  the B2 passive cost-type carrier invariants.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 11. Remaining Blockers

- **Passive pre-net-edge carrier + Union — BUILT + RATIFIED** (this slice). No longer a blocker.
- **Passive producer — UNBUILT.** Must conform to the Frozen Socket Rule (§6.2); separately authorized.
- **Master B3 passive wiring — UNBUILT.** Depends on the passive producer.
- **B3 router-only Cell-3 cost-type pass-through — UNBUILT (separate/parallel).**

Tombstoned: `edge_direction`, `staleness_threshold_ms`. Built: B2 carriers (incl. cost-type provenance),
`PassiveShadowInput` type+factory, mapping cells 1/2/4/5, and now the passive pre-net-edge carrier + Union.
**Master B3 remains BLOCKED.**

---

## 12. Next Safe Step

- A **separately-authorized docs-only Passive Producer implementation charter** — defining how a non-actionable
  producer assembles a `PassivePreNetEdgeCalculationInput` (conforming to the Frozen Socket Rule) from passive
  evidence and surfaces the resulting `NetEdgeCalculationResult` for the built `PassiveShadowInput` — **designing
  no runtime** until that authorization. **The next step is docs, not runtime.**
- The B3 router-only Cell-3 cost-type pass-through may be separately authorized at any time (parallel).
- **No implementation is authorized by this charter.** The passive producer, Master B3 wiring, the Cell-3 route,
  B4 scoring, durable logs, further Phase 5 modification, the Shadow Intent Envelope, capacity activation, Phase
  6.2, and 7.x/8.x remain separately gated.
