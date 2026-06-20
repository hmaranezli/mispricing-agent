# Phase 6.1 Passive Entrypoint / Slice-0A Handoff Pinning — Classification & Sequencing Charter

> **This is a docs-only classification/sequencing charter.** It conceptually pins the **passive entrypoint /
> Slice-0A handoff boundary** that a future passive path would target, at architecture level only. It
> **implements, mocks, codes, and edits nothing**. It authorizes NO runtime, NO tests, NO lock-test edits, NO
> Python code, NO interface implementation, NO schema/runtime file edits, NO B2/B3 runtime/schema/carrier
> changes, NO Master B3 wiring, NO Phase 5 runtime amendment, NO B4 scoring design, NO durable shadow logs, NO
> Shadow Intent Envelope design/runtime/schema, NO `edge_direction` mechanism/design/values/defaults, NO
> `staleness_threshold_ms` design/policy, NO capacity activation, NO Phase 6.2 work, NO pytest, NO graphify. It
> is subordinate to `docs/handoff/phase6_1_phase5_gross_edge_gate_invocation_necessity_decision_charter.md`,
> `docs/handoff/phase6_1_edge_direction_classification_necessity_audit.md`,
> `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_readiness_audit.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`,
> `docs/handoff/phase6_1_shadow_input_wrapper_charter.md`,
> `docs/handoff/phase5_to_live_canary_roadmap.md`, and `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `e87db7127a74c11766654b83c5ad45482f4a3bca`

---

## 1. Base / Dependency Chain

**Base commit:** `e87db7127a74c11766654b83c5ad45482f4a3bca`.

References:

- `docs/handoff/phase6_1_phase5_gross_edge_gate_invocation_necessity_decision_charter.md` — verdict
  **NOT_NECESSARY**: the passive path need not invoke the Phase 5 gross-edge *actionability* gate; net-edge
  arithmetic is `edge_direction`-independent; a **future separate passive entrypoint** would be required
  (recorded, not designed).
- `docs/handoff/phase6_1_shadow_input_wrapper_charter.md` — Slice 0A **RATIFIED**: `PassiveShadowInput`
  references **`NetEdgeCalculationResult` by identity**; `ShadowValidatedObservation` rejected; wrapper must
  carry a `capacity_pass_reference` field that stays deferred/`None`. Implementation **not** authorized there.
- `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md` — B4 consumes the typed passed non-halt handoff only;
  Slice 0A pins the handoff type; B4 scoring deferred.
- `docs/handoff/phase6_1_edge_direction_classification_necessity_audit.md` — `edge_direction` external intent;
  NOT NECESSARY for the passive path.
- `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_readiness_audit.md` — Master B3 BLOCKED.
- `docs/handoff/phase5_to_live_canary_roadmap.md` — governs gating/sequencing.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Why This Charter Exists

Two prior ratified results must be reconciled at the architecture level before any passive runtime can be
planned:

1. The gross-edge gate is **NOT_NECESSARY** for the passive path, and a **future separate passive entrypoint**
   was recorded as required (because today the only producer of `NetEdgeCalculationResult` is bundled behind the
   intent-bearing gross-edge gate).
2. Slice 0A already **ratified** that `PassiveShadowInput` references **`NetEdgeCalculationResult` by identity**.

This charter pins the **conceptual boundary** of the passive entrypoint / Slice-0A handoff so those two facts
fit together — i.e. *what shape* the passive handoff must have and *what it must exclude* — **without** building
the entrypoint, designing the producer, or wiring anything. It is a blueprint classification, not an
implementation.

---

## 3. Evidence Inventory Inspected (read-only)

- **`NetEdgeCalculationResult`** (`phase5/net_edge_calculator_boundary.py`): a frozen, anti-coercion result
  carrier whose payload fields are **magnitude/unit/status only** — `gross_edge_value`, `gross_edge_unit`,
  `total_cost_value`, `total_cost_unit`, `net_edge_value`, plus status/origin provenance. It carries **no
  `edge_direction`** and no venue-scope/intent field. The **result object is itself non-actionable**; "no
  paper/live readiness" is stated in its own docstring.
- **Producer coupling** (`phase5/pre_net_edge_calculation_input_boundary.py`): `calculate_net_edge` requires a
  `PreNetEdgeCalculationInput`, which requires an exact `GrossEdgeObservation` — and *that* construction is what
  mandates `edge_direction`. So actionability lives in the **upstream producer's input**, **not** in the result
  carrier.
- **Slice-0A wrapper charter:** `PassiveShadowInput` holds the pass result **by reference** (identity), never
  re-derived; it must carry `capacity_pass_reference` (deferred/`None`); name fixed; implementation deferred.
- **Net-edge arithmetic:** reads only gross magnitude/unit; `edge_direction`-independent (prior verdict).

**Key reconciliation:** the ratified handoff *shape* (`NetEdgeCalculationResult` — magnitude-only,
`edge_direction`-free) is **already non-actionable**. The only thing the gross-edge verdict requires is a
**parallel passive producer** that yields such a result without the intent gate. Shape and producer are
separable.

---

## 4. Current State After the Gross-Edge Gate NOT_NECESSARY Verdict

- The passive path **must not be required** to pass through the gross-edge actionability gate.
- The economically meaningful computation (net-edge) is `edge_direction`-independent and its **result carrier is
  non-actionable**.
- A **future, separate passive entrypoint** (a Phase-5-owned producer) would be required to emit a non-actionable
  net-edge result **without** invoking the intent gate — **recorded only**, not designed.
- Slice 0A's `PassiveShadowInput → NetEdgeCalculationResult` (by identity) remains the ratified handoff
  *reference*, and is compatible with the above because the referenced object carries no actionability.

---

## 5. Conceptual Classification of the Passive Entrypoint / Slice-0A Handoff

**Classification: a strictly passive, parallel-track observation handoff boundary.** Conceptually it has two
separable parts (neither designed here):

- **The passive entrypoint (producer) — conceptual, future, separate.** A Phase-5-owned, non-actionable producer
  of a net-edge result that does **not** require the gross-edge actionability gate (no `edge_direction`). This
  charter **records its required properties** (§6) and **does not** design, mock, or implement it.
- **The Slice-0A handoff (carrier reference) — already ratified in shape.** `PassiveShadowInput` references a
  frozen, closed, anti-coercion, **magnitude-only / `edge_direction`-free** net-edge result **by identity**
  (today's `NetEdgeCalculationResult`, or a future passive-produced equivalent of the same non-actionable shape).

The boundary may therefore be **conceptually pinned**: *a passive, undirected, frozen-by-identity net-edge result
reference, produced on a parallel passive track isolated from the actionable gross-edge gate.* No runtime
entrypoint is built.

---

## 6. Required Handoff Properties (blueprint only — no implementation)

A future passive handoff/entrypoint, when separately authorized, MUST exhibit these type-signature *properties*
(described, not coded):

1. **Frozen / closed / anti-coercion.** Immutable, slotted, init-blocked carrier with coercion dunders that
   raise — consistent with existing Phase 5 / Phase 6.1 carrier discipline.
2. **Exact-type, identity-referenced.** The pass result is held **by identity** (`type(x) is …`, `is`/`id()`),
   never re-derived, parsed, or copied (consistent with the ratified `PassiveShadowInput` reference rule).
3. **Magnitude/diagnostic payload only.** Carries net-edge magnitude/unit/status provenance (the non-actionable
   `NetEdgeCalculationResult` shape). It carries **no** directional, intent, or actionability field.
4. **Passive / undirected.** Receives and passively carries data only; it makes **no** decision, gate, score,
   ranking, or threshold.
5. **Replay-first / no-network.** No live/private/authenticated reads implied; replay/shadow evidence only.
6. **Capacity-deferred.** Any capacity reference (e.g. `capacity_pass_reference`) stays `None`/deferred; no
   capacity pass is claimed.
7. **Producer-isolated.** Its producer must be a **parallel passive track** that does **not** invoke the
   gross-edge actionability gate (no `edge_direction` upstream).

These are **acceptance properties for a future slice**, not a schema, not code, not an interface.

---

## 7. Explicit Excluded Fields (absolute passivity lock)

The passive entrypoint/handoff MUST NOT accept, require, carry, default, or imply any of:

- **`edge_direction`** (and any LONG/SHORT/CROSS_VENUE/DEFAULT/NONE/synthetic/static/placeholder direction).
- **Shadow Intent** of any kind (intent author/source/record/envelope payload).
- **Capacity activation** (no capacity PASS token; `capacity_pass_reference` stays `None`/deferred).
- **Order intent / sizing intent / execution intent / routing / paper / live / trade / actionability** fields.

It is **undirected, passive observation only**. Any such field appearing in a future design is a contract
violation and must fail fast.

---

## 8. Parallel-Track Boundary vs. the Existing Phase 5 Gross-Edge Gate

- The passive path is a **strictly parallel conceptual track**, **isolated** from the actionable Phase 5
  gross-edge gate. It is **not** a hack, bypass, monkey-patch, or re-implementation of that gate.
- The existing gross-edge actionability gate (`make_gross_edge_observation` → `GrossEdgeObservation`, bundling
  `edge_direction` + venue scope/buy/sell) remains the **actionable** track, **untouched** and unaltered.
- **No legacy-code trap:** the passive entrypoint is **not** forced to fit the `GrossEdgeObservation` shape;
  current code shape is **evidence, not destiny**. The passive handoff targets the **non-actionable net-edge
  result shape**, not the actionable gross-edge observation input.
- The two tracks share **only** the non-actionable net-edge *result shape*; they do **not** share the intent
  gate. This charter draws that boundary; it builds neither side.

---

## 9. What This Does and Does Not Unblock

- **Does:** conceptually **pin** the passive entrypoint / Slice-0A handoff boundary and its required properties,
  reconciling the gross-edge NOT_NECESSARY verdict with the ratified `PassiveShadowInput → NetEdgeCalculationResult`
  reference.
- **Does NOT:** build any runtime entrypoint; design/implement the passive producer; design `PassiveShadowInput`
  internals; design B4 `ShadowScore`/diagnostic-EV math/ranking/thresholds/durable-log schema; wire Master B3
  into anything; amend Phase 5; or resolve `staleness_threshold_ms` or the Cell-3 route.

**Unwired-socket lock:** defining this boundary does **not** wire Master B3 into it. The socket is conceptual and
unwired.

---

## 10. Remaining Blockers for Master B3

**Master B3 remains BLOCKED.** Still outstanding (each separately gated; none authorized here):

1. The **future passive entrypoint/producer slice** (§6 properties), separately authorized and implemented.
2. The **Slice-0A `PassiveShadowInput` wrapper implementation** (decision ratified; implementation deferred).
3. The **router-only Cell-3 cost-type pass-through** charter (separate, unbuilt).
4. **`staleness_threshold_ms`** classification/necessity + resolution (separate, unresolved policy).

`edge_direction` is **not** among the passive-path blockers (NOT NECESSARY for the passive path).

---

## 11. Still-Forbidden Work

- **No** implementation/mock/code/interface/schema/runtime edit of any passive entrypoint, producer, handoff
  type, or wrapper; **no** pinning beyond the conceptual boundary.
- **No** bypass/hack/monkey-patch/re-implementation of the Phase 5 gross-edge gate; **no** Phase 5 amendment.
- **No** `edge_direction` mechanism/source/default/value; **no** Shadow Intent design; **no** sizing/execution/
  order/routing/actionability field.
- **No** B4 scoring, diagnostic-EV math, formulae, ranking, thresholds, or durable-log schema.
- **No** B2/B3 runtime/schema/carrier change; **no** Master B3 wiring; **no** B3 route designed.
- **No** `staleness_threshold_ms` design/policy/derivation.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `capacity_pass_reference` / `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** reopening of cost vocabulary values; **no** weakening of the B2 passive cost-type carrier invariants.
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Next Safe Step

- A **separately-authorized review** to decide whether to charter the **future passive entrypoint/producer
  slice** (under the §6 properties and §7/§8 locks) — still designing nothing executable until that authorization
  — as the prerequisite to any `PassiveShadowInput` implementation.
- Independently, the **`staleness_threshold_ms`** classification/necessity audit and the **router-only Cell-3**
  cost-type pass-through charter may each be separately authorized.
- **No implementation is authorized by this charter.** The passive entrypoint/producer, `PassiveShadowInput`
  implementation, Master B3 wiring, any B3 route, B4 scoring, durable logs, Phase 5 modification, the Shadow
  Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.
