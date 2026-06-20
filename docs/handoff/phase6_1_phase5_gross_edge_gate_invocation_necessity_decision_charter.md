# Phase 6.1 Phase 5 Gross-Edge Gate Invocation Necessity Decision Charter

> **This is a docs-only decision charter.** It decides exactly one question — **must the Phase 6.1 passive
> shadow path invoke the existing Phase 5 gross-edge *actionability* gate, or is that gate unnecessary for
> passive observation/scoring?** — and **designs nothing**. It authorizes NO runtime, NO tests, NO lock-test
> edits, NO B2/B3 runtime/schema/carrier changes, NO Master B3 wiring, NO B4 scoring design, NO durable logs, NO
> Shadow Intent Envelope design/runtime/schema, NO `edge_direction` mechanism/design/values/defaults, NO
> `staleness_threshold_ms` design/policy, NO capacity activation, NO Phase 6.2 work, NO pytest, NO graphify. It
> is subordinate to `docs/handoff/phase6_1_edge_direction_classification_necessity_audit.md`,
> `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_readiness_audit.md`,
> `docs/handoff/phase6_1_b3_phase5_wiring_charter.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`,
> `docs/handoff/phase6_1_shadow_intent_envelope_contract_charter.md`,
> `docs/handoff/phase5_to_live_canary_roadmap.md`, and `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `e15ff5e5ce0149e5213c5c049efc92ded015514c`

---

## 1. Base / Dependency Chain

**Base commit:** `e15ff5e5ce0149e5213c5c049efc92ded015514c`.

References:

- `docs/handoff/phase6_1_edge_direction_classification_necessity_audit.md` — classified `edge_direction` as
  external **intent**; necessity **DEFERRED**, contingent on *whether the passive path invokes the Phase 5
  gross-edge gate*. **This charter answers that contingency.**
- `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_readiness_audit.md` — Master B3 BLOCKED;
  `edge_direction` an unresolved blocker.
- `docs/handoff/phase6_1_b3_phase5_wiring_charter.md` — `edge_direction` a Phase 5 field not carried by B2.
- `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md` — B1→B2→B3→**B4 passive shadow scoring**; B4 consumes
  the **typed passed non-halt handoff** only; **candidate handoff = `NetEdgeCalculationResult`**; Slice 0A pins
  the exact handoff type "**if not already pinned**", and a "**newly authorized passive
  `ShadowInput`/`ShadowValidatedObservation` handoff type**" is permitted if existing Phase 5 types are
  insufficient.
- `docs/handoff/phase6_1_shadow_intent_envelope_contract_charter.md` — `edge_direction` external-only (Option B).
- `docs/handoff/phase5_to_live_canary_roadmap.md` — governs gating/sequencing.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Why This Decision Charter Exists

The `edge_direction` audit returned **DEFERRED** because its necessity hinges on a single unanswered question:
does the Phase 6.1 **passive** shadow path have to pass through the Phase 5 **gross-edge actionability gate**
(`make_gross_edge_observation` → `GrossEdgeObservation`, which mandates `edge_direction`)? This charter answers
that question on the merits of the **passive-shadow objective** — not by deferring to current code shape — so
the `edge_direction` blocker can be resolved rather than left open. It **decides only**; it designs no path.

---

## 3. Evidence Inventory Inspected (read-only)

- **Gross-edge gate** — `phase5/gross_edge_observation_boundary.py`: `make_gross_edge_observation` requires
  `edge_direction`, validated against `_ALLOWED_DIRECTIONS = frozenset({"LONG","SHORT","CROSS_VENUE"})`,
  fail-fast; `CROSS_VENUE` requires distinct `venue_buy`/`venue_sell`. The carrier also bundles venue
  scope/buy/sell — i.e. it is an **actionability/intent** construct, not a bare gross-magnitude carrier.
- **Net-edge calculator** — `phase5/net_edge_calculator_boundary.py`: `calculate_net_edge(*, calculation_input)`
  reads **only** `gross.gross_edge_value` and `gross.gross_edge_unit` and computes
  `net_edge = gross_edge − Σ cost_i` over signed decimal magnitudes. It **never reads, branches on, or requires
  `edge_direction`.** The economics are pure magnitude algebra.
- **Net-edge input boundary** — `phase5/pre_net_edge_calculation_input_boundary.py`:
  `make_pre_net_edge_calculation_input` requires `type(gross_observation) is GrossEdgeObservation` (exact). So
  the **only** way to obtain a `PreNetEdgeCalculationInput` (and thus a `NetEdgeCalculationResult`) **through the
  existing code** is to first construct a `GrossEdgeObservation` — which forces an `edge_direction`.
- **Profitability gate** — `phase5/net_edge_profitability_gate_boundary.py`:
  `net_edge_profitability_preflight(*, calculation_result, threshold_policy)` consumes a `calculation_result`
  (the `NetEdgeCalculationResult`).
- **Shadow scoring plan** — B4 consumes the typed passed non-halt handoff; candidate is `NetEdgeCalculationResult`;
  the exact handoff type is **not yet pinned** (Slice 0A) and a newly-authorized passive handoff type is
  permitted if existing types are insufficient.

---

## 4. Existing Phase 5 Gross-Edge Gate Behavior

As coded, the net-edge handoff chain is **strictly ordered and actionability-bundled**:

```
make_gross_edge_observation(edge_direction=…)  →  GrossEdgeObservation   [REQUIRES edge_direction]
        →  make_pre_net_edge_calculation_input(gross_observation: GrossEdgeObservation)
        →  calculate_net_edge → NetEdgeCalculationResult   [arithmetic reads only gross magnitude/unit]
        →  net_edge_profitability_preflight(calculation_result=…)
```

Two facts coexist:

1. The **arithmetic** (`calculate_net_edge`) is **independent of `edge_direction`** — it consumes only the gross
   magnitude and unit.
2. The **only existing producer** of `NetEdgeCalculationResult` requires an exact `GrossEdgeObservation`, whose
   construction **mandates `edge_direction`**. So *the existing code path* cannot reach the candidate handoff
   without supplying intent.

This is precisely the **gross-vs-net separation** the decision must respect: net-edge math does **not** require
the intent-bearing gross-edge actionability gate; only the **current carrier shape** couples them.

---

## 5. Phase 6.1 Passive-Shadow Objective

Phase 6.1 produces **passive, non-actionable diagnostics** (`ShadowObservation`/`ShadowScore`; EV fields
`diagnostic_`/`passive_`-prefixed; no recommendation, readiness, order intent, routing, or execution). Its
purpose is to **observe and score** replay/shadow evidence — explicitly **not** to form a directional trade
intent. An `edge_direction` is a **directional call** (which way we would trade); supplying one is an
**actionability** act, the very thing the passive objective excludes.

Deciding by the **objective** (not by current code shape, per the legacy-code-trap ban): a passive observer has
no business asserting a trade direction, and net-edge arithmetic — the only economically meaningful computation
on the path — does not need one.

---

## 6. Decision Analysis — Must the Passive Path Invoke the Gross-Edge Gate?

- **Against necessity (objective + arithmetic separation):** the passive-shadow objective forbids consuming an
  actionability/intent input as a requirement; and the net-edge arithmetic is provably independent of
  `edge_direction` (calculator reads only gross magnitude/unit). Passing through the **intent-bearing**
  gross-edge gate would inject an actionability prerequisite into a path defined as non-actionable.
- **For necessity (legacy-code trap — explicitly discounted):** the existing code can only produce the candidate
  `NetEdgeCalculationResult` by first building a `GrossEdgeObservation` (→ `edge_direction`). Per the
  legacy-code-trap ban, this is **not** a valid basis to conclude NECESSARY — it reflects current carrier shape,
  not the passive objective. The handoff type is, moreover, **not yet pinned** (Slice 0A), and a newly-authorized
  passive handoff type is expressly permitted.
- **Synthesis:** the gross-edge **actionability** gate is **not conceptually required** for passive
  observation/scoring. Because the existing code bundles `edge_direction` into the sole producer of the candidate
  handoff, the existing code **cannot feed the passive path without actionability** — which, per the hard bound,
  means a **future separate passive entrypoint/slice would be required** (recorded as a requirement only; **not
  designed here**).

---

## 7. Verdict — **NOT_NECESSARY**

**The Phase 6.1 passive shadow path does NOT need to invoke the existing Phase 5 gross-edge *actionability*
gate.** The intent-bearing `GrossEdgeObservation` construction (and therefore `edge_direction`) is **not
conceptually necessary** for passive observation/scoring; the only economically meaningful computation
(net-edge) is separable and `edge_direction`-independent.

**Mandatory qualifier (no design):** because the existing Phase 5 code can only produce the candidate
`NetEdgeCalculationResult` by passing through the actionability-bundled gross-edge gate, the existing code
**cannot support the passive path without actionability**. A **future, separately-authorized passive entrypoint
or slice** — feeding net-edge arithmetic from a gross magnitude **without** the intent-bearing gate — **would be
required**. This charter **records that requirement only**; it designs **no** bypass, interface, function,
handoff type, or alternate implementation, and pins **no** handoff type (Slice 0A remains open).

This verdict is reached against Phase 6.1's passive objective and the gross-vs-net separation — **not** by
deferring to, nor by re-implementing/bypassing, current Phase 5 code.

---

## 8. Consequence for `edge_direction`

- For the **Phase 6.1 passive path**, `edge_direction` is **NOT needed**. The prior audit's **DEFERRED** verdict
  is hereby resolved to **NOT NECESSARY for the Phase 6.1 passive shadow path** (its necessity was contingent on
  invoking the gross-edge gate, which this charter finds unnecessary).
- `edge_direction` remains an **external-intent** field (Option B; Shadow Intent Envelope) relevant **only** to a
  future **actionable** path — **not** to Phase 6.1 passive shadow. It is **not solved, defined, defaulted, or
  supplied** here. The derivation/inference ban stands in full: B1/B2/B3 must never infer, compute, default, or
  fabricate it; **no** DEFAULT/NONE/ALWAYS_LONG/ALWAYS_SHORT/CROSS_VENUE/synthetic/static/placeholder value is
  proposed. Direction is either legitimate external intent or **absent** — and for the passive path it is absent.

---

## 9. Consequence for Master B3 Readiness

- **Master B3 remains BLOCKED.** Removing `edge_direction` from the passive path does **not** unblock Master B3.
  It still requires separately-authorized follow-ups: (a) the **future passive entrypoint/slice** required by §7
  (so a passive handoff can be produced without the actionability gate); (b) the Slice-0A **handoff-type pinning**
  decision; (c) the **router-only Cell-3** cost-type pass-through charter; and (d) resolution of the separate
  **`staleness_threshold_ms`** policy blocker.
- What changed: the `edge_direction` blocker is **downgraded/removed from the passive path**; the gating now
  centers on the future passive entrypoint + handoff-type pinning + Cell-3 route + staleness — none of which is
  authorized or designed here.

---

## 10. Still-Forbidden Work

- **No** design/definition/implementation of any passive entrypoint, bypass, interface, function, handoff type,
  or alternate net-edge path; **no** pinning of the B3→B4 handoff type (Slice 0A stays open).
- **No** `edge_direction` mechanism/source/default/value; **no** DEFAULT/NONE/ALWAYS_*/synthetic/static/
  placeholder direction; **no** global/static dummy.
- **No** B2/B3 runtime/schema/carrier change; **no** Master B3 wiring; **no** Phase 5 runtime/tests/modification;
  **no** B4 scoring design; **no** durable logs; **no** Shadow Intent Envelope design/runtime/schema; **no** live
  adapter.
- **No** `staleness_threshold_ms` design/policy/derivation.
- **No** thresholds, policies, if/else logic, scoring, routing, or actionability introduced anywhere.
- **No** reopening of cost vocabulary values; **no** weakening of the B2 passive cost-type carrier invariants.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 11. Next Safe Step

- A **separate docs-only planning step** for the **future passive net-edge entrypoint requirement** recorded in
  §7 — establishing (still designing nothing executable) what a Phase-5-owned, non-actionable producer of a
  passive net-edge handoff would have to guarantee (no `edge_direction`, no actionability), as the prerequisite
  to pinning the B3→B4 handoff type (Slice 0A).
- Independently, the **`staleness_threshold_ms`** classification/necessity audit and the **router-only Cell-3**
  cost-type pass-through charter may each be separately authorized.
- **No implementation is authorized by this charter.** The passive entrypoint, handoff-type pinning, Master B3
  wiring, any B3 route, the Shadow Intent Envelope, Phase 5 modification, B4 scoring, durable logs, the live
  adapter, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.
