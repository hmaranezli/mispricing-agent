# Phase 6.1 Master B3 Remaining Blockers — Reclassification v2 & Readiness Audit

> **This is a docs-only state-map audit.** It updates the Master-B3 blocker map after the recent classification
> chain and corrects one inaccurate status claim against repo evidence. It **designs nothing and builds
> nothing**. It authorizes NO runtime, NO tests, NO lock-test edits, NO Python code, NO interface/schema/runtime
> edits, NO B2/B3 runtime/schema/carrier changes, NO Master B3 wiring, NO Phase 5 runtime amendment, NO passive
> producer design, NO B4 scoring design/math, NO durable shadow logs, NO Shadow Intent Envelope
> design/runtime/schema, NO `edge_direction` reopening, NO `staleness_threshold_ms` reopening, NO capacity
> activation, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_staleness_threshold_ms_classification_necessity_audit.md`,
> `docs/handoff/phase6_1_passive_entrypoint_slice0a_handoff_pinning_classification_sequencing_charter.md`,
> `docs/handoff/phase6_1_phase5_gross_edge_gate_invocation_necessity_decision_charter.md`,
> `docs/handoff/phase6_1_edge_direction_classification_necessity_audit.md`,
> `docs/handoff/phase6_1_b2_passive_cost_component_provenance_carrier_closeout_ratification.md`,
> `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_readiness_audit.md`,
> `docs/handoff/phase6_1_shadow_input_wrapper_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `08d2e14feba5fc4e740f34728a5d5253f2a14fbe`

---

## 1. Base / Dependency Chain

**Base commit:** `08d2e14feba5fc4e740f34728a5d5253f2a14fbe`.

References (verdicts cited, not reopened):

- `…_staleness_threshold_ms_classification_necessity_audit.md` — staleness = downstream policy/calibration; **NOT
  NECESSARY for B3 / passive routing**; B3 stays a dumb pipe.
- `…_passive_entrypoint_slice0a_handoff_pinning_…_charter.md` — passive entrypoint/handoff boundary
  **conceptually pinned** (magnitude-only `NetEdgeCalculationResult` by identity); producer unbuilt.
- `…_phase5_gross_edge_gate_invocation_necessity_decision_charter.md` — gross-edge actionability gate
  **NOT_NECESSARY** for the passive path.
- `…_edge_direction_classification_necessity_audit.md` — `edge_direction` external intent; **NOT NECESSARY** for
  the passive path.
- `…_b2_passive_cost_component_provenance_carrier_closeout_ratification.md` — B2 passive cost-type carrier
  **BUILT + RATIFIED**.
- `…_master_b3_remaining_blockers_reclassification_readiness_audit.md` — v1 blocker map.
- `…_shadow_input_wrapper_charter.md` — Slice 0A handoff decision (`PassiveShadowInput`).

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Why v2 Reclassification Exists

Five things changed the Master-B3 picture since v1: `edge_direction` was classified out of the passive path; the
gross-edge actionability gate was ruled NOT_NECESSARY; the passive entrypoint/Slice-0A handoff boundary was
conceptually pinned; `staleness_threshold_ms` was classified out of B3/passive routing; and the B2 passive
cost-type provenance carrier was built and ratified. v2 re-states the blocker map against **current repo
evidence** and **corrects** the loose phrase "PassiveShadowInput impl outstanding" — which the repo contradicts.
This is a **state map**, not a build charter.

---

## 3. Evidence Inventory Inspected (read-only)

- **`phase6_1/passive_shadow_input.py` — BUILT.** Defines the frozen, slotted, anti-coercion carrier
  `PassiveShadowInput` **and** the keyword-only factory `make_passive_shadow_input`. It **references exactly one
  `NetEdgeCalculationResult` by identity** (`type(...) is NetEdgeCalculationResult`, no copy/mutate/recompute),
  carries minimal provenance (venue, pair, one UTC epoch-ms int) and `capacity_pass_reference` that **must be
  `None`/deferred** (non-`None` fails fast). It derives nothing, scores nothing, exposes no actionability.
- **`tests/test_phase6_1_passive_shadow_input.py` — exists** (locks the above).
- **`NetEdgeCalculationResult`** — magnitude/unit/status only; `edge_direction`-free; its **only existing
  producer** is the actionability-bundled net-edge chain (requires `GrossEdgeObservation` → `edge_direction`).
- **B2 contract** — carries the ratified passive `cost_component_provenance_reference`; carries no
  `edge_direction`, no `staleness_threshold_ms`.
- **Mapping cells** — 1/2/4/5 RATIFIED; Cell 3 reduced to a passive router-only pass-through (unbuilt).

---

## 4. Tombstoned / Excluded Blockers (cited, not reopened)

- **`edge_direction` — TOMBSTONED (excluded from the passive-path blocker set).** Classified as external intent
  (Shadow Intent Envelope, deferred); **NOT NECESSARY** for the Phase 6.1 passive path (gross-edge gate
  NOT_NECESSARY). Cited only; **not reopened, redesigned, or revalued.** Derivation ban stands.
- **`staleness_threshold_ms` — TOMBSTONED (excluded from B3/passive routing).** Classified as downstream temporal
  policy / external calibration; **NOT NECESSARY for B3**; B3 stays a passive dumb pipe; any value/diagnostic is
  deferred to B4/calibration. Cited only; **not reopened or revalued.**

Neither is part of the remaining Master-B3 passive blocker set.

---

## 5. `PassiveShadowInput` Truth Reconciliation (correction)

The phrase **"PassiveShadowInput impl outstanding" is INCORRECT** per repo evidence and is retired.

- **BUILT (do not rebuild):** the **data type `PassiveShadowInput`** and its **factory
  `make_passive_shadow_input`** exist in `phase6_1/passive_shadow_input.py` with their validation, and a test
  file locks them. This is the **Slice 0A passive carrier** — complete as a typed handoff carrier.
- **UNBUILT (distinct thing):** the **future passive producer** — a non-actionable emitter that yields the
  `NetEdgeCalculationResult` the carrier references **without** invoking the gross-edge actionability gate. Today
  the only producer of `NetEdgeCalculationResult` is the `edge_direction`-bundled chain; the passive producer
  that the gross-edge-gate charter §7 recorded as "required" does **not** exist.

**These are two separate artifacts.** The carrier (built) *references* a `NetEdgeCalculationResult`; the producer
(unbuilt) would *supply* one passively. This audit **does not authorize or imply any re-implementation of
`PassiveShadowInput`**, and does not collapse the carrier and the producer into one thing.

---

## 6. Current Cell-3 Status

- **B2 passive cost-component provenance carrier — BUILT + RATIFIED** (`cost_component_provenance_reference`;
  optional, `None`-absent, verbatim, passive; closeout frozen).
- **B3 router-only cost-type pass-through — UNBUILT.** No B3 route carries the provenance into the Phase 5 cost
  path yet. It must be a **verbatim-or-`None`, validation-free, inference-free** pass-through when separately
  chartered (forward invariant). **Not designed here.** It is **not** on the critical path for the minimal
  net-edge handoff (cost-type provenance is not required to produce a `NetEdgeCalculationResult`).

---

## 7. Current Passive Producer Status

- **Conceptual boundary — PINNED** (frozen/closed/anti-coercion, identity-referenced, magnitude-only, undirected,
  replay-first, capacity-deferred; parallel track isolated from the intent gate).
- **Producer — UNBUILT.** No runtime entrypoint exists that emits a non-actionable `NetEdgeCalculationResult`
  from B2 evidence without the gross-edge actionability gate.
- **No design authorized.** This audit records status only; it designs no producer, interface, or schema.

---

## 8. Final Master B3 Blocker List

Remaining, evidence-grounded blockers (each separately gated; none authorized/designed here):

1. **Passive producer (UNBUILT) — critical path.** A non-actionable emitter of a `NetEdgeCalculationResult` (or
   equivalent magnitude-only net-edge result) from B2 evidence, **without** the gross-edge actionability gate.
   Without it, the passive path cannot produce the `NetEdgeCalculationResult` that the (built) `PassiveShadowInput`
   must reference.
2. **Master B3 passive wiring (UNBUILT).** The actual connection of B2 normalized evidence through the passive
   producer to the typed handoff. Depends on (1).
3. **B3 router-only Cell-3 cost-type pass-through (UNBUILT) — separate/parallel.** Carries the ratified passive
   cost-type provenance into the Phase 5 cost path; **not** required for the minimal net-edge handoff; can be
   chartered independently.

Resolved / out of scope (for reference): mapping cells 1/2/4/5 (ratified); B2 carriers incl. cost-type provenance
(built); `PassiveShadowInput` type+factory (built); `edge_direction` and `staleness_threshold_ms` (tombstoned).

---

## 9. Readiness Verdict — **BLOCKED**

**Master B3 is BLOCKED** (the remaining blocker list in §8 is non-empty). The blocker surface is now **much
narrower and sharper** than v1: it is no longer about vocabularies, intent, or temporal policy, but about **two
unbuilt runtime artifacts** — the passive producer (critical path) and the Master B3 passive wiring — plus the
optional, parallel Cell-3 route. `edge_direction` and `staleness_threshold_ms` no longer block it. Master B3
becomes chartarable for wiring only once the passive producer exists (and the Cell-3 route is separately handled
if cost-type must flow).

---

## 10. Recommended Sequence for Next Charters / Slices (recommendation only)

One recommended order (others possible; rationale given):

1. **Passive producer — docs planning charter, then a separately-authorized TDD slice.** *Why first:* it is the
   **critical-path prerequisite** — the built `PassiveShadowInput` carrier is inert until something supplies a
   non-actionable `NetEdgeCalculationResult`. Nothing downstream (wiring, B4) can proceed without it.
2. **Master B3 passive wiring — docs charter, then slice.** *Why second:* it connects B2 evidence → passive
   producer → `PassiveShadowInput` handoff; it strictly depends on (1).
3. **B3 router-only Cell-3 cost-type pass-through — separate/parallel track.** *Why last/parallel:* it is **not**
   on the minimal net-edge critical path (cost-type provenance is not needed to form a `NetEdgeCalculationResult`);
   it can be chartered any time under the verbatim-or-`None` forward invariant without blocking (1)/(2).

Rationale for choosing this order over alternatives: putting the passive producer first removes the single
hard dependency that gates everything else; the Cell-3 route is decoupled and therefore deferrable without
stalling the core passive path. **This is sequencing guidance only; it authorizes none of the above.**

---

## 11. Still-Forbidden Work

- **No** reopening/redesign/revaluation of `edge_direction` or `staleness_threshold_ms` (tombstoned; cite only).
- **No** re-implementation of `PassiveShadowInput` / `make_passive_shadow_input` (already BUILT).
- **No** design/implementation of the passive producer, Master B3 wiring, the Cell-3 route, B4 scoring/logging, or
  any runtime entrypoint/interface/schema.
- **No** B2/B3 runtime/schema/carrier change; **no** Phase 5 runtime amendment; **no** Shadow Intent Envelope.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** reopening of cost vocabulary values; **no** weakening of the B2 passive cost-type carrier invariants.
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Next Safe Step

- A **separately-authorized docs-only passive producer planning charter** (sequencing item 1) — establishing the
  required guarantees of a non-actionable `NetEdgeCalculationResult` producer (no `edge_direction`, no
  actionability), still designing nothing executable — as the prerequisite to any Master B3 wiring.
- The B3 router-only Cell-3 cost-type pass-through may be separately authorized at any time (parallel).
- **No implementation is authorized by this charter.** The passive producer, Master B3 wiring, the Cell-3 route,
  B4 scoring, durable logs, Phase 5 modification, the Shadow Intent Envelope, capacity activation, Phase 6.2, and
  7.x/8.x remain separately gated.
