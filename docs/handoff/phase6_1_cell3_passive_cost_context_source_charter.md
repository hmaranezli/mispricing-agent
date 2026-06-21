# Phase 6.1 — Cell-3 Passive Cost-Context Source Charter

> **This is a docs-only design charter.** It conceptually defines the **minimal passive cost-context source**
> needed to satisfy the **existing, frozen** B3/Producer `cost_validity_contexts` contract — **without**
> implementing it and **without** any real cost math. It **designs and builds nothing**: no runtime, no tests,
> no schema, no adapter, no fee table. It authorizes NO runtime code, NO tests, NO lock-test edits, NO
> frozen-component edits, NO Cell-3 runtime, NO real-cost arithmetic, NO S5 runtime, NO S1 storage, NO
> live/paper/canary, NO execution/actionability, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_b2_pass_path_ingestion_runtime_closeout_ratification.md`,
> `docs/handoff/phase6_1_master_b3_client_wiring_charter.md`,
> `docs/handoff/phase6_1_passive_producer_implementation_charter.md`, the Phase 5 cost-boundary charters, and
> `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `32f4732d951867eeb6fed16d984818c93ed23413`

---

## 1. Base / Purpose

**Base commit:** `32f4732d951867eeb6fed16d984818c93ed23413`.

The B2 pass-path ingestion runtime is **BUILT + RATIFIED** (`168949a` / `32f4732`): it produces one exact
`PublicRawSnapshotRecord`, which the frozen `b2_replay_normalization` turns into one `NormalizedEvidenceMaterial`
carrying a single GROSS_EDGE binding. But the B4-consumable pass path also requires a **`cost_validity_contexts`**
argument at the B3/Producer seam, and **no runtime source supplies it** today — only test fixtures do. This
charter defines the **minimal passive substrate** that supplies a contract-valid `cost_validity_contexts` value,
**conforming to the existing frozen contract** and inventing **no** real cost evidence.

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Evidence Inspected (from source, before naming any shape)

The shape was read from source, never assumed:

- **`phase6_1/b3_passive_client_wiring.py:29,69`** — `wire_passive_shadow_input(*, normalized_evidence_material,
  cost_validity_contexts)` **forwards `cost_validity_contexts` verbatim by identity** to the producer; B3
  **constructs none of it** ("the minimal path supplies a zero-valued cost context; real-cost assembly is a
  separate, deferred concern", `:36-37`).
- **`phase6_1/passive_producer.py:32-55`** — `produce_passive_shadow_input(...)` passes `cost_validity_contexts`
  into `make_passive_pre_net_edge_calculation_input(gross_observation=..., cost_validity_contexts=...)`, then
  `calculate_net_edge(...)`. The producer "re-validates nothing, performs no arithmetic of its own."
- **`phase5/pre_net_edge_calculation_input_boundary.py:339-406`** — `cost_validity_contexts` **must be an exact
  non-empty `tuple`** (lists/sets/dicts/frozensets/Mappings/generators/iterators rejected); the **exact tuple is
  preserved verbatim** (no sort/dedup/filter/aggregate); **every item must be an exact
  `ObservableCostValidityContext`**; **no interval comparison and no freshness/TTL computation** are performed.
- **`phase5/pre_net_edge_calculation_input_boundary.py:157-178`** — `make_observable_cost_validity_context(*,
  cost_observation, valid_from_epoch_ms, valid_until_epoch_ms, validity_source_contract,
  validity_source_artifact, validity_source_field, validity_assertion_type, boundary_version)`. `cost_observation`
  must be an **exact `ObservableCostObservation`**; every metadata field an exact non-empty `str`;
  `valid_from/until_epoch_ms` are integer strings **preserved verbatim** (no bound comparison, no TTL).
- **`phase5/observable_cost_friction_boundary.py:145-167`** — `make_observable_cost_observation(*, …,
  cost_component_type, signed_decimal_value, unit, …, zero_cost_evidence, …)`. Every field is an exact non-empty
  `str`; `cost_component_type` is **a non-empty str with no closed vocabulary** (validated uniformly); a
  **numerically-zero `signed_decimal_value` REQUIRES an explicit `zero_cost_evidence` string** (never the
  not-applicable sentinel).
- **`calculate_net_edge`** computes `net = gross − Σcosts`; the existing test
  `test_happy_path_zero_valued_cost_context_keeps_net_equal_gross` proves a **zero-valued** cost context yields
  `net == gross`.

**Conclusion of evidence:** `cost_validity_contexts` is **not** `None` and **not** an opaque scalar — it is an
**exact non-empty tuple of exact `ObservableCostValidityContext`** items, each wrapping an exact
`ObservableCostObservation`. A **zero-valued, explicitly-evidenced** cost context is already the established,
frozen "minimal path" used by the B3/Producer tests.

---

## 3. Selected Conceptual Shape (no blocker)

**Selected: a passive, deterministic, zero-cost TEST-SUBSTRATE source** that **reuses the existing frozen Phase 5
factories** to assemble a contract-valid `cost_validity_contexts` value. No new carrier type, no downstream edit:

- The source returns an **exact non-empty `tuple`** containing **exactly one** exact
  `ObservableCostValidityContext`.
- That context wraps **one** exact `ObservableCostObservation` built via the frozen
  `make_observable_cost_observation(...)` with:
  - `signed_decimal_value` = a **canonical zero** decimal string (e.g. `"0"`), carried verbatim;
  - `zero_cost_evidence` = an **explicit, honest** passive-substrate evidence string declaring the zero as a
    **declared/observed zero-cost passive substrate**, e.g. *"declared zero-cost passive substrate — no real fee
    schedule consulted"* (the frozen factory **requires** explicit zero-cost evidence for a numerically-zero
    value, never the not-applicable sentinel);
  - `cost_component_type` = an **honest passive label** (the field has no closed vocabulary), e.g.
    `"PASSIVE_ZERO_COST_SUBSTRATE"` — **not** `TAKER_FEE`/`MAKER_FEE` or any label implying a real fee was
    measured;
  - `unit` and the `source_*` provenance fields = **verbatim passive provenance strings** naming the substrate
    (no fee schedule, no venue fee table).
- The wrapping `make_observable_cost_validity_context(...)` carries its validity-interval bounds and
  `validity_source_*` / `validity_assertion_type` metadata **verbatim** (the frozen factory performs **no** bound
  comparison and **no** TTL/freshness computation).

Because this matches the **existing frozen contract exactly**, it requires **zero** downstream edits and is a
clean future runtime-slice target — **this is a design selection, not a blocker.**

---

## 4. Absolute Passive Substrate (binding)

The source is the **narrowest possible zero-cost passive substrate**. It contains **NO** real fee schedule, **NO**
maker/taker logic, **NO** VIP tiers, **NO** token/rebate discounts, **NO** venue fee table, and **NO** Cell-3
arithmetic. The zero magnitude is **carried verbatim** as a canonical decimal string with explicit zero-cost
evidence — it is **never computed** from any fee input. The downstream `net = gross − Σcosts` therefore yields
`net == gross` purely as a consequence of a carried zero, not of any cost calculation performed here.

---

## 5. Semantic Starvation (binding)

The cost-context source **must not** evaluate, threshold, rank, score, classify, adjust, recompute, or compare the
edge magnitude or any cost. It carries strings; it makes **no** decision. It creates **no** actionability,
readiness, execution, sizing, routing, or verdict signal, and **no** directional intent. It reads **no** clock and
performs **no** temporal/TTL/freshness policy (the validity-interval bounds are passive carried provenance only).
It is pure passive substrate, consistent with the package-wide forbidden-token / no-actionability locks.

---

## 6. Frozen Downstream Seal (binding)

This charter proposes **no** edit to B3, Producer, Phase 5 (`pre_net_edge_calculation_input_boundary`,
`observable_cost_friction_boundary`, `net_edge_calculator_boundary`), B2 / `PublicRawSnapshotRecord` /
normalizer, B4, S4, S1, or S5. The source **conforms to existing expectations**: it emits exactly the exact
non-empty tuple of exact `ObservableCostValidityContext` the frozen `make_passive_pre_net_edge_calculation_input`
already requires. **No** interface change, widened accept, relaxed validator, or behavior edit is implied. (Had
the evidence shown the contract un-satisfiable without a frozen edit, this charter would have **stopped with a
blocker** instead — it does not, because the zero-cost path is already contract-valid.)

---

## 7. No Cost Smuggling (binding)

The source emits **NO** `COST` binding into any `field_payload` (the B2 GROSS_EDGE binding stays the sole entry,
and its `zero_cost_evidence` label stays `None` per the frozen B2 rule — unchanged by this charter). It fabricates
**no** fee object, **no** venue fee, and **no** placeholder that implies real cost evidence. The chosen zero-cost
context is **explicitly** a declared passive test-substrate (its `zero_cost_evidence` string and
`cost_component_type` label both say so) and is **never marketed as real measured cost**. Real cost economics
(the actual Cell-3 cost route) remain **separately gated and unbuilt**.

---

## 8. Identity Isolation & No Storage/Runner Logic (binding)

- **Identity isolation:** the source performs **no** S2 / Silver / `raw_snapshot_identity` /
  `MarketProvenanceContext` identity merge, derivation, copy, hash, or stringify. Cost-context provenance lives on
  its own plane; it is never crossed with market or system identity.
- **No storage/runner logic:** **no** S5 orchestration, **no** loop / queue / retry / repair / self-heal, **no**
  S1 durable storage, **no** persistence / cursor / checkpoint, **no** serialization. The source is a pure,
  stateless, deterministic substrate assembler — one call returns one contract-valid tuple.

---

## 9. Scope Honesty (binding)

This charter may make a **future, separately-authorized Cell-3 passive cost-context source runtime/source TDD
slice** eligible. It does **NOT** itself:

- complete the pass path;
- authorize any runtime, test, or schema;
- authorize the real Cell-3 cost route or any cost arithmetic;
- authorize S5 runtime, S1 storage, live/paper/canary, or any execution/actionability;
- complete Phase 6.1 or ready Phase 6.2.

**Capacity invariant unchanged:** `CapacityConstraintGate` stays deferred / non-activatable with **0 emit sites**;
`PassiveShadowInput.capacity_pass_reference` stays `None` / deferred and is never read as "capacity validated."

---

## 10. Pathway to S5 (binding)

The pass path becomes **contract-complete enough to revisit S5 Runner runtime eligibility** **only after** the
passive cost-context source is **built AND ratified** (its own RED→GREEN slice + closeout), joining the already-
ratified B2 ingestion runtime so that one `(payload, MarketProvenanceContext, GrossEdgeBindingLabelContext)` plus
one supplied `cost_validity_contexts` can flow end-to-end to a B4-consumable input. Until then: **S5 runtime
remains ineligible**; the halt path stays complete; the S1 sink stays a test-only reference sink. Even after the
cost-context source is ratified, **S5 eligibility is a separate determination**, and **S1 storage** remains an
independent, separately-gated charter.

---

## 11. Still-Forbidden Work

- **No** edit / widen / relax / refactor of any frozen module (§6); **no** boundary-as-S5; **no** loop / queue /
  stream / routing / retry / repair / cursor / storage / trigger (§8).
- **No** real fee schedule, maker/taker logic, VIP tier, token/rebate discount, venue fee table, or Cell-3 / cost
  arithmetic (§4); **no** numeric cost computation — the zero is carried verbatim.
- **No** evaluation / threshold / rank / score / classification / adjustment / recompute of edge or cost; **no**
  actionability / readiness / execution / sizing / routing / verdict / intent (§5).
- **No** `COST` binding in `field_payload`, **no** fake fee object, **no** fabricated venue fee, **no** placeholder
  implying real cost; **no** zero context marketed as real cost (§7).
- **No** S2 / Silver / `raw_snapshot_identity` / `MarketProvenanceContext` identity merge or derivation (§8).
- **No** runtime / tests / schema / serialization; **no** Cell-3 runtime; **no** S5 runtime; **no** S1 storage;
  **no** live/paper/canary; **no** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x
  work.

---

## 12. Precise State

- **Selected conceptual shape:** a passive zero-cost **test-substrate** source emitting an **exact non-empty tuple
  of exactly one exact `ObservableCostValidityContext`** (zero `signed_decimal_value` + explicit
  `zero_cost_evidence` + honest passive `cost_component_type`), assembled from the **existing frozen Phase 5
  factories** with **zero downstream edits**. **Not a blocker.**
- **B2 pass-path ingestion runtime:** BUILT + RATIFIED (unchanged).
- **Pass path:** still **NOT contract-complete** — the cost-context source is **designed (docs-only) but unbuilt**;
  no runtime supplies `cost_validity_contexts` outside tests yet.
- **S5 runtime:** ineligible. **S1 storage:** separately gated. **Phase 6.1:** incomplete. **Phase 6.2:** not
  ready. **No executable work is authorized.**

---

## 13. Next Safe Step

- A **separately-authorized Cell-3 Passive Cost-Context Source field-shape charter and/or runtime TDD slice** —
  implementing the §3 substrate (a deterministic assembler returning the exact non-empty
  `(ObservableCostValidityContext,)` tuple via the frozen factories, zero magnitude + explicit zero-cost evidence,
  honest passive label), under TDD with the package-wide locks intact and **no** frozen-component edit.
- Independently, the **S1 storage-medium** charter remains separately gated.
- Only after **both** the pass path (B2 ingestion + this cost-context source) **and** the halt path are
  contract-complete may an **S5 Runner runtime TDD slice** be (separately) reconsidered for eligibility.
- **No implementation is authorized by this charter.**

**Conclusion:** the minimal passive cost-context source is conceptually defined — a **passive, deterministic,
zero-cost test-substrate** that emits the **exact non-empty tuple of exactly one exact
`ObservableCostValidityContext`** the frozen B3/Producer `cost_validity_contexts` contract already requires
(verified from source: non-empty tuple, exact item type, verbatim preservation, no bound comparison/TTL, and a
zero `signed_decimal_value` requiring explicit `zero_cost_evidence`). It carries a **canonical zero** magnitude
with **honest declared zero-cost evidence** and an honest passive `cost_component_type`, contains **no** real fee
schedule / maker-taker / VIP / venue-table / Cell-3 arithmetic, performs **no** evaluation/threshold/score/verdict
and creates **no** actionability, merges **no** identity, and holds **no** storage/runner logic — conforming to the
**frozen** downstream with **zero edits** (a blocker would have been reported had it not). This is a **design
selection only**: it may make a future cost-context source TDD slice eligible, but it **does not** complete the
pass path, **does not** authorize S5 runtime / S1 storage / Cell-3 runtime / execution, and **does not** complete
Phase 6.1 or ready Phase 6.2. **S5 Runner eligibility may be revisited only after the cost-context source is built
AND ratified.** **No executable work is authorized.**
