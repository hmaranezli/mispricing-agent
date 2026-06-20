# Phase 6.1 Passive Producer — Classification & Boundary Charter

> **This is a docs-only classification/boundary charter.** It conceptually defines the boundary of the future,
> still-**unbuilt** Phase 6.1 passive producer — a non-actionable supplier of a `NetEdgeCalculationResult` for
> the already-built `PassiveShadowInput` / `make_passive_shadow_input` handoff, **without** using the gross-edge
> actionability gate. It **designs and builds nothing**. It authorizes NO runtime, NO tests, NO lock-test edits,
> NO Python code, NO interface/schema/runtime edits, NO B2/B3 runtime/schema/carrier changes, NO Master B3
> wiring, NO Phase 5 runtime amendment, NO passive producer implementation, NO B4 scoring design/math, NO durable
> shadow logs, NO Shadow Intent Envelope design/runtime/schema, NO `edge_direction` reopening, NO
> `staleness_threshold_ms` reopening, NO capacity activation, NO Phase 6.2 work, NO pytest, NO graphify. It is
> subordinate to `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_v2_readiness_audit.md`,
> `docs/handoff/phase6_1_passive_entrypoint_slice0a_handoff_pinning_classification_sequencing_charter.md`,
> `docs/handoff/phase6_1_phase5_gross_edge_gate_invocation_necessity_decision_charter.md`,
> `docs/handoff/phase6_1_staleness_threshold_ms_classification_necessity_audit.md`,
> `docs/handoff/phase6_1_edge_direction_classification_necessity_audit.md`,
> `docs/handoff/phase6_1_b2_passive_cost_component_provenance_carrier_closeout_ratification.md`,
> `docs/handoff/phase6_1_shadow_input_wrapper_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `33e8d0f403a9a8c5e92691dd3b897496303b722c`

---

## 1. Base / Dependency Chain

**Base commit:** `33e8d0f403a9a8c5e92691dd3b897496303b722c`.

References:

- `…_master_b3_remaining_blockers_reclassification_v2_readiness_audit.md` — named the **passive producer
  (UNBUILT)** as the Master-B3 critical-path blocker, distinct from the already-built `PassiveShadowInput`.
- `…_passive_entrypoint_slice0a_handoff_pinning_…_charter.md` — pinned the passive handoff boundary
  (magnitude-only `NetEdgeCalculationResult` by identity; parallel track isolated from the intent gate).
- `…_phase5_gross_edge_gate_invocation_necessity_decision_charter.md` — gross-edge actionability gate
  **NOT_NECESSARY**; net-edge arithmetic is `edge_direction`-independent; a future passive producer is required.
- `…_edge_direction_classification_necessity_audit.md` / `…_staleness_threshold_ms_classification_necessity_audit.md`
  — both **tombstoned** out of the passive path.
- `…_b2_passive_cost_component_provenance_carrier_closeout_ratification.md` — B2 cost-type carrier BUILT+RATIFIED.
- `…_shadow_input_wrapper_charter.md` + `phase6_1/passive_shadow_input.py` — `PassiveShadowInput` /
  `make_passive_shadow_input` **BUILT**.

**No capacity validation and no capacity pass is claimed by this charter** (see §11/§12).

---

## 2. Why This Charter Exists

The v2 readiness audit isolated the **passive producer** as the single critical-path blocker for the Phase 6.1
passive path: the built `PassiveShadowInput` carrier is inert until something supplies the
`NetEdgeCalculationResult` it references **by identity**, and the only existing producer of that result is bundled
behind the gross-edge actionability gate (`GrossEdgeObservation` → `edge_direction`). This charter **pins the
conceptual boundary** of that future producer — its classification, forbidden inputs, input/output properties,
and relationships — so a later, separately-authorized implementation slice is fully constrained. It implements
nothing and wires nothing.

---

## 3. Evidence Inventory Inspected (read-only)

- **Net-edge arithmetic** — `phase5/net_edge_calculator_boundary.py::calculate_net_edge(*, calculation_input)`:
  reads only `calculation_input.gross_observation.gross_edge_value`/`gross_edge_unit` and
  `calculation_input.cost_validity_contexts`; computes `net = gross − Σ cost_i`; **never reads `edge_direction`**.
  This is the existing, authoritative net-edge arithmetic boundary.
- **Arithmetic input carrier** — `phase5/pre_net_edge_calculation_input_boundary.py::make_pre_net_edge_calculation_input`:
  currently requires `gross_observation` to be an **exact `GrossEdgeObservation`** (the actionability gate
  carrier, which mandates `edge_direction`) and `cost_validity_contexts` to be an **exact non-empty `tuple`** of
  `ObservableCostValidityContext` (empty tuple rejected — line ~378–380). So the *current* only path into the
  arithmetic is actionability-bundled and requires at least one cost context.
- **Result carrier** — `NetEdgeCalculationResult`: magnitude/unit/status only; `edge_direction`-free;
  non-actionable ("no paper/live readiness").
- **Handoff carrier (built)** — `phase6_1/passive_shadow_input.py`: `PassiveShadowInput` references exactly one
  `NetEdgeCalculationResult` by identity; carries `capacity_pass_reference` that must stay `None`/deferred;
  derives/scores nothing.
- **B2 carriers** — carry normalized magnitudes/units, identity/provenance, `zero_cost_evidence` (optional), and
  the ratified passive `cost_component_provenance_reference`; carry no `edge_direction`/`staleness_threshold_ms`.

**Surfaced tension (recorded, not solved):** the net-edge *arithmetic* is `edge_direction`-free, but its *current
input carrier* mandates a `GrossEdgeObservation`. Reusing the arithmetic without the actionability gate is
therefore an **open reconciliation requirement** for a future slice (see §8) — **not designed here**.

---

## 4. Passive Producer Classification

The passive producer is classified as a **non-actionable, replay-first adapter/arranger** whose sole conceptual
job is to **present already-normalized passive evidence to the existing Phase 5 net-edge arithmetic and surface
its result** for the handoff. It is:

- **An arranger/adapter, not a decision-maker** — it carries/arranges typed evidence and returns an existing
  Phase 5 result carrier; it makes no directional, sizing, routing, scoring, or readiness decision.
- **Undirected / passive** — it neither holds nor requires intent.
- **A reuser, not a re-implementer** — it relies on the existing Phase 5 net-edge arithmetic boundary; it is
  **not** a new math engine (§8).
- **Replay-first** — no network, no clock, no env, no randomness.

It is **UNBUILT**; only its boundary is pinned here.

---

## 5. Explicit Non-Goals & Forbidden Inputs

The future passive producer MUST NOT:

- **Use the gross-edge actionability gate.** It MUST NOT construct, require, or depend on `GrossEdgeObservation`,
  MUST NOT invoke the gross-edge actionability gate, and MUST NOT require `edge_direction`.
- **Accept tombstoned/actionability inputs.** It MUST reject (never accept, default, or imply) `edge_direction`,
  `staleness_threshold_ms`, capacity activation, Shadow Intent, order intent, sizing intent, execution intent,
  routing intent, and any actionability parameter. (Tombstoned items are **cited, not reopened**.)
- **Score or persist.** It MUST NOT perform B4 `ShadowScore`, diagnostic-EV scoring, ranking, thresholds, durable
  logging, calibration, or Phase 6.2 work.
- **Re-implement the carrier.** It MUST NOT re-implement `PassiveShadowInput` / `make_passive_shadow_input`
  (already built) — it is a **distinct** artifact (§9).
- **Wire Master B3.** Defining this boundary does **not** wire Master B3 (§11).
- **Invent arithmetic.** It MUST NOT invent new net-edge math (§8).
- **Take blobs.** No `*args`/`**kwargs`, no vague blob input, no unbounded dict (§6).

---

## 6. Conceptual Input Contract / Properties (pinned, not wired, not implemented)

The producer's eventual input (conceptually arriving from B3) MUST be:

1. **Exact-typed and explicit** — typed, passive, **normalized** observation material and identity/provenance
   references only (e.g. B2 `NormalizedEvidenceMaterial` / its field bindings and identity references), held by
   identity. **No** `*args`/`**kwargs`, **no** loose dict/blob, **no** unbounded container.
2. **Passive / non-actionable** — carries no intent/direction/sizing/execution/routing/capacity field.
3. **Normalized, not raw** — it consumes normalized evidence (B2), never re-derives or re-parses raw artifacts.
4. **Replay-first** — deterministic, no network/clock/env/randomness implied.
5. **Identity-preserving** — references are held by identity (`type(x) is …`, `is`/`id()`), never copied,
   mutated, or coerced.

This is an **acceptance-property list** for a future slice. It is **not** a signature, schema, or code, and it
**does not wire B3**.

---

## 7. Conceptual Output Contract / Properties (pinned, not implemented)

The producer's eventual output MUST be:

1. **An existing Phase 5 result carrier** — on an economic pass, a non-actionable **`NetEdgeCalculationResult`**
   (the exact existing type, magnitude/unit/status only, `edge_direction`-free), suitable to be referenced **by
   identity** by the built `PassiveShadowInput`. On a non-pass, an **existing Phase 5 halt/blocked carrier** —
   never a fabricated verdict.
2. **Emitted, not scored** — provided/surfaced as-is; the producer attaches **no** score, rank, threshold,
   diagnostic-EV, readiness, or actionability.
3. **Identity-held** — the result is surfaced by reference for the carrier to hold; not copied or recomputed.

No durable log, no calibration, no Phase 6.2 output is produced.

---

## 8. Relationship to Existing Phase 5 Net-Edge Arithmetic

- **Reuse, do not duplicate.** Any future producer implementation MUST rely on the **existing** Phase 5 net-edge
  arithmetic boundary (`calculate_net_edge`) and its result type; it MUST NOT invent or re-implement net-edge
  math, cost algebra, or unit handling.
- **Open reconciliation requirement (recorded, not designed).** `calculate_net_edge` is `edge_direction`-free,
  **but** its current input carrier (`make_pre_net_edge_calculation_input`) mandates an exact
  `GrossEdgeObservation` (actionability-bundled). Reusing the arithmetic **without** the gross-edge actionability
  gate therefore requires a future, **separately-authorized, Phase-5-owned** means of presenting gross
  magnitude/unit + cost contexts to that same arithmetic **without** `GrossEdgeObservation`/`edge_direction`.
  This charter **records that prerequisite and designs none of it** — no new carrier, no Phase 5 amendment, no
  arithmetic change is authorized here.

---

## 9. Relationship to `PassiveShadowInput`

- **Distinct artifacts.** The producer **supplies** the `NetEdgeCalculationResult`; the **already-built**
  `PassiveShadowInput` / `make_passive_shadow_input` **references** it by identity. Producer ≠ carrier.
- **No rebuild.** This charter does **not** authorize or imply any re-implementation of `PassiveShadowInput` or
  its factory; their built contract (identity reference, `capacity_pass_reference` deferred/`None`, no scoring)
  is unchanged and not weakened.
- **Composition only (future, separate).** Connecting producer-output → `make_passive_shadow_input(...)` is a
  later, separately-authorized step; it is **not** done or designed here.

---

## 10. Zero-Cost / Deferred Cell-3 Compatibility

- **No Cell-3 prerequisite.** The minimal passive net-edge critical path MUST NOT require the deferred router-only
  Cell-3 cost-type provenance route. Cost-type **provenance** (`cost_component_provenance_reference`) is passive
  metadata and is **not** needed to compute a `NetEdgeCalculationResult`.
- **Zero/absent cost handled gracefully — as a value, not emptiness.** The existing arithmetic input requires a
  **non-empty** `cost_validity_contexts` tuple, so a zero/absent-cost economic scenario is represented by a valid
  **zero-valued cost context** (consistent with B2's existing `zero_cost_evidence` carrier), **not** by an empty
  contexts tuple and **not** by inventing a cost-type label. The producer boundary MUST tolerate the
  zero/absent-cost case via this value-based representation.
- **No Cell-3 design.** This charter neither requires, designs, nor builds the Cell-3 route; it only guarantees
  the producer boundary does not depend on it.

---

## 11. What This Does and Does Not Unblock

- **Does:** pin the passive producer's **conceptual boundary** (classification, forbidden inputs, input/output
  properties, arithmetic-reuse rule, carrier relationship, zero-cost compatibility).
- **Does NOT:** build/implement/mock the producer; design its signature/schema; amend Phase 5; provide a
  non-actionable arithmetic input carrier; wire Master B3; compose producer→`PassiveShadowInput`; design the
  Cell-3 route; or do any B4 scoring/logging.

**Master B3 wiring remains strictly BLOCKED and separately authorized.**

---

## 12. Remaining Master B3 Blockers

Unchanged from the v2 audit (none authorized/designed here):

1. **Passive producer — UNBUILT (critical path).** Boundary pinned by this charter; implementation (and its §8
   reconciliation prerequisite) remain separately gated.
2. **Master B3 passive wiring — UNBUILT.** Depends on (1).
3. **B3 router-only Cell-3 cost-type pass-through — UNBUILT (separate/parallel).** Not on the minimal critical
   path.

Tombstoned/out of scope: `edge_direction`, `staleness_threshold_ms`. Built: B2 carriers (incl. cost-type
provenance), `PassiveShadowInput` type+factory, mapping cells 1/2/4/5.

---

## 13. Next Safe Step

- A **separately-authorized docs-only step** to resolve the §8 **open reconciliation requirement** — i.e. how the
  existing `calculate_net_edge` arithmetic can be fed gross magnitude/unit + cost contexts **without** the
  gross-edge actionability gate (a Phase-5-owned, non-actionable presentation) — still designing nothing
  executable. That is the true prerequisite to any passive producer implementation slice.
- The B3 router-only Cell-3 cost-type pass-through may be separately authorized at any time (parallel).
- **No implementation is authorized by this charter.** The passive producer, the §8 reconciliation,
  `PassiveShadowInput` composition, Master B3 wiring, the Cell-3 route, B4 scoring, durable logs, Phase 5
  modification, the Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.
