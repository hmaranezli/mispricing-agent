# Phase 6.1 Passive Producer — Implementation Charter

> **This is a docs-only implementation-mapping charter.** It bounds the *future* Phase 6.1 Passive Producer TDD
> slice — a deterministic arranger that consumes typed passive normalized evidence, constructs the **ratified
> frozen Phase 5 passive socket carriers**, calls the **existing** `calculate_net_edge`, and passes the returned
> result into the **already-built** `PassiveShadowInput` handoff. It **implements and designs no runtime, no B3
> wiring, nothing executable.** It authorizes NO runtime, NO tests, NO lock-test edits, NO Python, NO
> interface/schema/runtime edits, NO Phase 5 runtime amendment, NO B2/B3 changes, NO Master B3 wiring, NO passive
> producer implementation, NO B4 scoring design/math, NO durable shadow logs, NO Shadow Intent Envelope, NO
> `edge_direction` reopening, NO `staleness_threshold_ms` reopening, NO capacity activation, NO Phase 6.2 work, NO
> pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_phase5_passive_pre_net_edge_carrier_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_passive_producer_classification_boundary_charter.md`,
> `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_v2_readiness_audit.md`, and `CLAUDE.md`;
> where any conflict arises, those govern.

**Base:** `2d8eb5d62be82eb56663a5be96a6decd2de40d13`

---

## 1. Base / Dependency Chain

**Base commit:** `2d8eb5d62be82eb56663a5be96a6decd2de40d13`.

References:

- `…_phase5_passive_pre_net_edge_carrier_tdd_closeout_ratification.md` — **Frozen Socket Rule**, single-math
  source, exact-typing AST invariant, error-domain isolation, zero-valued cost context (all RATIFIED).
- `…_passive_producer_classification_boundary_charter.md` — producer = non-actionable replay-first arranger;
  reuse existing arithmetic; no actionability.
- `…_master_b3_remaining_blockers_reclassification_v2_readiness_audit.md` — producer UNBUILT (critical path);
  `PassiveShadowInput` BUILT.

**No capacity validation and no capacity pass is claimed by this charter** (see §14).

---

## 2. Why This Charter Exists

With the Phase 5 passive socket BUILT + RATIFIED and the `PassiveShadowInput` handoff already BUILT, the passive
producer is the single critical-path artifact joining them. Before any TDD slice, the producer's exact
boundaries — input contract, construction contract, Phase 5 call contract, handoff contract, and the hard
prohibitions (toxic imports, clock blindness, identity pass-through) — must be **fixed in docs** so the future
slice is fully constrained and cannot drift into actionability, new math, or boundary mutation. This charter
fixes them and implements nothing.

---

## 3. Evidence Inventory Inspected (read-only)

- **Phase 5 socket (ratified)** — `phase5/net_edge_calculator_boundary.py`: `make_passive_gross_edge_magnitude`,
  `make_passive_pre_net_edge_calculation_input`, the frozen `PassiveGrossEdgeMagnitude` /
  `PassivePreNetEdgeCalculationInput`, and the additive exact-typed Union at `calculate_net_edge`. The Union
  returns a `NetEdgeCalculationResult` on a pass or a defensive `BlockedPacket` (and never a
  `NoEligibleHaltPacket`) on malformed/dimensional failure.
- **Handoff (built)** — `phase6_1/passive_shadow_input.py`: `make_passive_shadow_input(*, net_edge_calculation_result,
  source_venue, source_pair, observed_at_epoch_ms, capacity_pass_reference=None)` requires an **exact**
  `NetEdgeCalculationResult` (held by identity), exact non-empty `source_venue`/`source_pair`, an exact
  non-negative `int` `observed_at_epoch_ms` (carried verbatim), and `capacity_pass_reference` deferred to `None`.
  Anything other than an exact `NetEdgeCalculationResult` is rejected.
- **Handoff test (built)** — `tests/test_phase6_1_passive_shadow_input.py` locks the above.

---

## 4. Producer Role / Classification

The Passive Producer is a **deterministic, replay-first, non-actionable arranger**. Its sole job:

1. accept typed passive normalized evidence (+ identity/provenance references);
2. construct the ratified passive socket carriers (`PassiveGrossEdgeMagnitude` →
   `PassivePreNetEdgeCalculationInput`);
3. call the **existing** `calculate_net_edge`;
4. on a `NetEdgeCalculationResult`, pass it **by identity** into `make_passive_shadow_input`; on a defensive
   non-pass carrier, surface that carrier **by identity** (it cannot and must not be wrapped — §8).

It makes **no** decision, score, ranking, threshold, readiness, or directional judgement. It is an **arranger and
conduit**, not a calculator and not a scorer.

---

## 5. Input Contract for the Future TDD Slice

- **Exactly typed / passive / normalized.** Inputs are exactly-typed passive normalized evidence and
  identity/provenance references only — e.g. normalized magnitude/unit evidence for the gross edge, an
  already-typed non-empty sequence of exact `ObservableCostValidityContext`, and passive provenance references
  (`source_venue`, `source_pair`, the provenance `observed_at_epoch_ms` integer) needed solely to populate the
  handoff.
- **No loose inputs.** **No** `*args`, `**kwargs`, `dict`, blob, raw payload, unbounded mapping, or generic
  container input; **no** `Protocol`/`Any`/duck typing/`isinstance` hacks. Exact-type discipline (`type(x) is …`)
  only — inheriting the §7 AST invariant.
- **No actionability inputs.** The producer rejects/ignores `edge_direction`, `staleness_threshold_ms`, capacity
  activation, Shadow Intent, order/sizing/execution intent, and any actionability field (§ tombstone lock). It
  neither requires nor synthesizes a direction.
- The **exact** input field set/signature is left to the future TDD slice to pin under these constraints; this
  charter fixes the constraints, not the signature.

---

## 6. Construction Contract — Passive Carriers Only (Frozen Socket conformance)

- The producer may construct **only** `PassiveGrossEdgeMagnitude` and `PassivePreNetEdgeCalculationInput`, via
  their ratified factories, **conforming exactly** to the Frozen Socket Rule.
- It **must NEVER** construct `GrossEdgeObservation` (or any actionable carrier), and must not request, widen,
  mutate, subclass, or modify the Phase 5 boundary. It is a **conformance client**, never a boundary author.
- It must not require or synthesize `edge_direction` — the passive carriers have no such field, and none is
  invented.
- Cost contexts are passed verbatim into `make_passive_pre_net_edge_calculation_input` (non-empty exact
  `ObservableCostValidityContext` tuple); the producer never sorts/dedups/filters/aggregates them.

---

## 7. Phase 5 Call Contract — `calculate_net_edge` Only

- The producer calls the **existing** `calculate_net_edge(calculation_input=<PassivePreNetEdgeCalculationInput>)`
  and **only** that. **No** new math, **no** `calculate_passive_net_edge`, **no** duplicated gross-minus-cost
  logic — the single math source (RATIFIED) is reused.
- The producer performs **no** arithmetic of its own (no Decimal, no sums, no comparisons of magnitudes).
- **Exact-typing / AST invariant (inherited, RATIFIED).** The future producer file must contain **no**
  `isinstance`/`Protocol`/`Any`/dict-blob/duck typing; exact-type discrimination only; provable by AST test —
  the elevated Phase 6.1 invariant applies to this slice.

---

## 8. Output / Handoff Contract — Identity Pass-Through into `PassiveShadowInput`

- **On a pass (`NetEdgeCalculationResult`):** the producer passes the **exact** result **by reference/identity**
  into `make_passive_shadow_input(net_edge_calculation_result=<result>, source_venue=…, source_pair=…,
  observed_at_epoch_ms=…, capacity_pass_reference=None)`. It performs **no** unpacking, mutating, copying, or
  re-instantiating of the mathematical result object; the result flows through unchanged.
- **On a defensive non-pass (`BlockedPacket`):** because `make_passive_shadow_input` requires an **exact**
  `NetEdgeCalculationResult`, the producer **must NOT** attempt to wrap a blocked/halt carrier. It **surfaces the
  defensive carrier by identity** (emit-not-score), never fabricating a handoff. The malformed/blocked domain
  stays isolated (error-domain isolation, RATIFIED).
- **Emit-not-score.** The producer attaches **no** B4 `ShadowScore`, diagnostic-EV, ranking, threshold, readiness,
  durable log, or calibration. Its output is exactly the handoff (on pass) or the defensive carrier (on non-pass).
- `capacity_pass_reference` stays the deferred `None`; no capacity pass is claimed.

---

## 9. Toxic Import Ban

The future producer file **must not import** actionable or out-of-domain constructs, including: `GrossEdgeObservation`
or its factory, any `edge_direction` symbol/enum/allowed-set, actionable gross-edge gates/adapters, Shadow Intent
constructs, capacity-activation constructs (`CapacityConstraintGate` emit paths), and any
staleness/freshness-policy module. **If actionable constructs cannot be imported, they cannot be accidentally
coupled.** The producer's imports are limited to the ratified passive socket factories/types, the existing
`calculate_net_edge`, the `make_passive_shadow_input` handoff factory, and the exact passive evidence/context
types it must accept. This import ban is to be proven by an AST/import-scan test in the future slice.

---

## 10. Clock Blindness & Temporal Non-Policy

- The producer **must not read system time**: **no** `time.time()`, `datetime.now()`, monotonic/clock deltas,
  temporal branching, freshness checks, or local-time policy.
- Any timestamp present in input provenance (e.g. `observed_at_epoch_ms`) is carried **only as passive evidence**
  into the handoff and is **never interpreted, compared, or policy-checked** — consistent with the tombstoned
  `staleness_threshold_ms` (downstream policy, not producer logic). This is to be proven by an AST/import-scan
  test (no time/datetime imports; no clock calls).

---

## 11. Zero-Cost Behavior

- The zero-cost path uses **zero-valued cost context** formatting — a valid non-empty
  `ObservableCostValidityContext` tuple whose cost observation carries a zero magnitude. An **empty cost tuple
  remains invalid** (the socket rejects it).
- The minimal passive path has **no dependency on the deferred Cell-3 route**; cost-type provenance stays
  optional/deferred and is not required to produce a result.

---

## 12. What This Enables and Does Not Enable

- **Enables (conceptually):** a fully-bounded blueprint for a future, separately-authorized Passive Producer TDD
  slice — input/construction/call/handoff contracts plus the toxic-import, clock-blindness, identity-pass-through,
  and zero-cost locks.
- **Does NOT enable:** any runtime. No producer module, factory, or test is created; no Phase 5/B2/B3 file is
  edited; no B3 wiring; no B4; no logs. **Master B3 is not wired and remains BLOCKED.**

---

## 13. Remaining Blockers

- **Passive producer — UNBUILT.** Now fully bounded by this charter; a separate TDD slice would implement it
  under §5–§11.
- **Master B3 passive wiring — UNBUILT / BLOCKED.** Future B3 must be a **client** of the producer boundary, not
  a modifier of it (§8 separation). Separate authorization required.
- **B3 router-only Cell-3 cost-type pass-through — UNBUILT (separate/parallel).**

Tombstoned: `edge_direction`, `staleness_threshold_ms`. Built: B2 carriers (incl. cost-type provenance),
`PassiveShadowInput` type+factory, mapping cells 1/2/4/5, passive pre-net-edge carrier + Union.

---

## 14. Still-Forbidden Work

- **No** producer implementation/mock/code/test; **no** signature pinned beyond the conceptual contracts.
- **No** construction of `GrossEdgeObservation` or any actionable carrier; **no** `edge_direction`
  default/placeholder/synthetic/mock; **no** Phase 5 boundary widening/mutation.
- **No** new math / `calculate_passive_net_edge` / duplicated algebra; **no** producer-side arithmetic.
- **No** `Protocol`/`Any`/`dict`/blob/duck-typing/`isinstance`; **no** loose/blob/`*args`/`**kwargs` input.
- **No** B4 scoring/diagnostic-EV/ranking/threshold/durable log/calibration; **no** B2/B3 change; **no** Master
  B3 wiring; **no** Shadow Intent Envelope; **no** Cell-3 route.
- **No** clock/time/datetime read; **no** freshness/temporal policy; **no** `staleness_threshold_ms` interpretation.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` / `capacity_pass_reference` stays `None` / deferred).
- **No** reopening of `edge_direction`, `staleness_threshold_ms`, or cost vocabulary values; **no** weakening of
  the B2 passive cost-type carrier or Phase 5 passive socket invariants.
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 15. Next Safe Step

- A **separately-authorized Passive Producer TDD slice** implementing the producer under §5–§11 — a new Phase 6.1
  module + tests, conforming to the Frozen Socket Rule, calling only `calculate_net_edge`, passing the result by
  identity into `make_passive_shadow_input`, with AST/import-scan tests proving the toxic-import ban and clock
  blindness — **requiring its own explicit authorization** before any runtime.
- The B3 router-only Cell-3 cost-type pass-through may be separately authorized at any time (parallel).
- **No implementation is authorized by this charter.** The passive producer, Master B3 wiring, the Cell-3 route,
  B4 scoring, durable logs, Phase 5 modification, the Shadow Intent Envelope, capacity activation, Phase 6.2, and
  7.x/8.x remain separately gated.
