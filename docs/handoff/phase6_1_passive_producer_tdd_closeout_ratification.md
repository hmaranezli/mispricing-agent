# Phase 6.1 Passive Producer TDD — Closeout / Ratification Charter

> **This is a docs-only closeout/ratification charter.** It ratifies and freezes the **completed** Phase 6.1
> passive producer TDD slice (commit `fc32b84`) before any Master B3 wiring work. It **builds and designs
> nothing**. It authorizes NO runtime, NO tests, NO lock-test edits, NO Python, NO interface/schema/runtime
> edits, NO Phase 5 runtime amendment, NO passive producer implementation/design change, NO B2/B3 changes, NO
> Master B3 wiring, NO B4 scoring design/math, NO durable shadow logs, NO Shadow Intent Envelope, NO
> `edge_direction` reopening, NO `staleness_threshold_ms` reopening, NO capacity activation, NO Phase 6.2 work,
> NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_passive_producer_implementation_charter.md`,
> `docs/handoff/phase6_1_phase5_passive_pre_net_edge_carrier_tdd_closeout_ratification.md`, and `CLAUDE.md`;
> where any conflict arises, those govern.

**Base:** `fc32b841421cde5a9be3a8dab9cd939eff46c3f3`

---

## 1. Base / Dependency Chain

**Base commit:** `fc32b841421cde5a9be3a8dab9cd939eff46c3f3`.

References:

- `…_passive_producer_implementation_charter.md` — bounded the producer (input/construction/call/handoff
  contracts; toxic-import ban; clock blindness; identity pass-through; zero-cost), implemented by this slice.
- `…_phase5_passive_pre_net_edge_carrier_tdd_closeout_ratification.md` — Frozen Socket Rule, single-math source,
  exact-typing AST invariant, error-domain isolation (all RATIFIED).

**Implemented commit under closeout:** `fc32b84` (parent `303b348`).

**No capacity validation and no capacity pass is claimed by this charter** (see §13).

---

## 2. Why This Closeout Exists

The passive producer is implemented and green; it joins the ratified Phase 5 passive socket to the built
`PassiveShadowInput` handoff. Before Master B3 wiring is chartered, the producer's guarantees must be **frozen as
ratified invariants** so no later step can mutate the producer boundary, smuggle actionability, read a clock, or
break identity pass-through. This charter records the proof and freezes those invariants; it advances nothing
executable.

---

## 3. Evidence Inventory Inspected (read-only)

- **`phase6_1/passive_producer.py`** — defines `produce_passive_shadow_input` (keyword-only, exact-typed). It
  constructs only `PassiveGrossEdgeMagnitude` → `PassivePreNetEdgeCalculationInput` via their Phase 5 factories,
  calls only `calculate_net_edge`, returns the `make_passive_shadow_input` handoff on a
  `NetEdgeCalculationResult`, and surfaces a defensive non-pass carrier by identity (exact-type discrimination,
  no isinstance). No clock, no arithmetic, no scoring; imports limited to the passive socket, `calculate_net_edge`/
  result type, and the handoff factory.
- **`tests/test_phase6_1_passive_producer.py`** — happy + defensive branch coverage, identity pass-through,
  zero-valued cost context, empty-tuple-invalid, and AST locks (keyword-only signature; no isinstance/Protocol/
  Any; clock blindness; toxic-import ban; passive carriers only). Fixtures built from scratch, passive-only.
- **Untouched:** `phase5/net_edge_calculator_boundary.py`, `phase6_1/passive_shadow_input.py`, all B2/B3 files —
  no edits in this slice.

---

## 4. Ratified Producer Surface

**BUILT + RATIFIED at `fc32b84`:** the single public entry `produce_passive_shadow_input(*, gross_edge_value,
gross_edge_unit, cost_validity_contexts, source_venue, source_pair, observed_at_epoch_ms)` in
`phase6_1/passive_producer.py` — a deterministic, replay-first, non-actionable arranger. No further change to
this surface is authorized by this charter.

---

## 5. Ratified Test Proof

- **RED:** `ModuleNotFoundError: No module named 'phase6_1.passive_producer'` — feature genuinely missing.
- **GREEN:** **111 passed** across the targeted suite
  (`tests/test_phase6_1_passive_producer.py`, `tests/test_phase6_1_passive_shadow_input.py`,
  `tests/test_phase5_passive_pre_net_edge_carrier.py`, `tests/test_phase5_net_edge_calculator_boundary.py`).
  **No broad pytest.**
- **Changed-file scope (exactly two):** `phase6_1/passive_producer.py`, `tests/test_phase6_1_passive_producer.py`.
  **No edits** to Phase 5, `passive_shadow_input.py`, or B2/B3.
- **Fixture purity:** all fixtures built from scratch; no `make_gross_edge_observation` import; no actionable
  carrier reused or stripped.
- **AST locks (green):** keyword-only signature (no `*args`/`**kwargs`); no `isinstance`/`Protocol`/`Any`;
  clock-blind (no `time`/`datetime` imports or clock attrs); no toxic actionable imports; constructs only the
  passive carriers.

---

## 6. Frozen Producer Boundary (RATIFIED)

The producer is **BUILT and frozen** as a strict **client** of the Phase 5 passive socket: it conforms to the
ratified `PassivePreNetEdgeCalculationInput` / `PassiveGrossEdgeMagnitude` socket and to the
`make_passive_shadow_input` handoff, and it owns neither. Any change to the producer's signature, behavior, or
boundary requires **separate authorization**.

---

## 7. B3 Client-Only Rule (RATIFIED)

Future Master B3 **may call** `produce_passive_shadow_input`. Future Master B3 is **forbidden** from modifying,
widening, subclassing, reinterpreting, or wrapping the producer boundary **or** the Phase 5 passive socket. B3 is
a **client**, never a boundary author; any boundary change is a separate, explicitly-authorized charter.

---

## 8. Identity Pass-Through / Defensive Surfacing (RATIFIED)

- On a pass, the exact `NetEdgeCalculationResult` is passed **by identity** into `make_passive_shadow_input`
  (no unpack/copy/mutate/re-instantiate); proven by the identity (`is`) assertion.
- On a defensive non-pass (e.g. `BlockedPacket`), the exact carrier is **surfaced by identity and never wrapped**;
  the handoff factory is **not** called; proven by the identity assertion plus a "handoff must not be called"
  guard. Error-domain isolation (RATIFIED) holds: the defensive carrier never degrades any other path.

---

## 9. Downstream AST Invariants (RATIFIED + ELEVATED)

The following producer locks are **elevated to downstream Master-B3/wiring invariants**; any future B3 wiring
slice must preserve them and prove them by AST/import-scan test:

- **Toxic-import ban** — no import of actionable gross-edge gate carriers, directional-intent symbols, Shadow
  Intent, capacity-activation, or freshness-policy modules.
- **Clock blindness** — no `time`/`datetime`/clock reads; provenance timestamps carried verbatim, never
  interpreted.
- **No `isinstance`; no `Protocol`/`Any`/dict-blob/duck typing** — exact-type discrimination only.
- **Exact keyword-only passive input** — no `*args`/`**kwargs`/loose container input.

---

## 10. Anti-Monkeypatch Seal (RATIFIED)

Test-time monkeypatching was used **only** to prove identity pass-through (a controlled return is unavoidable to
assert object identity across an internal call). **No runtime monkeypatching, interceptors, dynamic wrappers,
runtime patching, or import-time substitution is authorized anywhere in the passive pipeline.** The producer and
the entire passive path are **deterministic and statically wired**; determinism is absolute. Any future test may
monkeypatch only within its own process to assert identity/branching, never to alter shipped runtime behavior.

---

## 11. Zero-Cost Extensibility (RATIFIED)

- The zero-valued cost context is a **temporary deferral state**, **not** a permanent economic assumption: it
  represents "zero/absent cost" while the router-only Cell-3 cost route is deferred.
- The producer input signature must remain **ready to accept real B2-originated cost contexts** once the separate
  Cell-3 route is built — no producer change is presumed, but the contract must not harden around zero-cost.
- The **empty cost tuple remains invalid** (the socket rejects it); zero is a value, never emptiness.

---

## 12. Remaining Blockers

- **Passive producer — BUILT + RATIFIED** (this slice). No longer a blocker.
- **Master B3 passive wiring — UNBUILT / BLOCKED.** Now the **next separately-authorized docs/runtime track**; B3
  must be a client (§7) preserving the §9 invariants.
- **B3 router-only Cell-3 cost-type pass-through — UNBUILT (separate/parallel).**

Tombstoned: `edge_direction`, `staleness_threshold_ms`. Built: B2 carriers (incl. cost-type provenance),
`PassiveShadowInput` type+factory, passive pre-net-edge carrier + Union, and the passive producer. **Master B3
remains BLOCKED.**

---

## 13. Still-Forbidden Work

- **No** change to the ratified producer surface (§4) or the Phase 5 passive socket; **no** producer
  boundary widening/mutation/subclassing.
- **No** new math / `calculate_passive_net_edge` / producer-side arithmetic; **no** actionable carrier
  construction; **no** directional-intent default/placeholder/synthetic/mock.
- **No** `isinstance`/`Protocol`/`Any`/dict-blob/duck typing; **no** loose/`*args`/`**kwargs` input; **no**
  clock/time read; **no** freshness/temporal policy.
- **No** B4 scoring/diagnostic-EV/ranking/threshold/durable log/calibration; **no** B2/B3 change; **no** Master
  B3 wiring; **no** Shadow Intent Envelope; **no** Cell-3 route; **no** runtime monkeypatch/interceptor/wrapper.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** reopening of `edge_direction`, `staleness_threshold_ms`, or cost vocabulary values; **no** weakening of
  the B2 passive cost-type carrier, Phase 5 passive socket, or producer invariants.
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 14. Next Safe Step

- A **separately-authorized docs-only Master B3 passive wiring charter** — defining how Master B3, **as a client
  of the producer** (§7) and under the §9 downstream invariants, assembles passive normalized B2 evidence and
  calls `produce_passive_shadow_input`, surfacing the `PassiveShadowInput` (or defensive carrier) onward —
  **designing no runtime** until that authorization. This is the next track; it is docs-first.
- The B3 router-only Cell-3 cost-type pass-through may be separately authorized at any time (parallel).
- **No implementation is authorized by this charter.** Master B3 wiring, the Cell-3 route, B4 scoring, durable
  logs, further Phase 5/producer modification, the Shadow Intent Envelope, capacity activation, Phase 6.2, and
  7.x/8.x remain separately gated.
