# Phase 6.1 — Cell-3 Passive Cost-Context Source Field-Shape Charter

> **This is a docs-only field-shape charter.** It formally fixes the **exact** field shape, the **exact** hermetic
> string constants, the **factory-only** construction path, and the **exact** output shape of the zero-cost passive
> substrate selected in `phase6_1_cell3_passive_cost_context_source_charter.md` (`59f4d33`). It **builds nothing**:
> no runtime code, no tests, no schema module, no adapter. It authorizes NO runtime code, NO tests, NO lock-test
> edits, NO frozen-component edits, NO Cell-3 real-cost runtime/arithmetic, NO S5 runtime, NO S1 storage, NO
> live/paper/canary, NO execution/actionability, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_cell3_passive_cost_context_source_charter.md`,
> `docs/handoff/phase6_1_master_b3_client_wiring_charter.md`,
> `docs/handoff/phase6_1_passive_producer_implementation_charter.md`, the Phase 5 cost-boundary charters, and
> `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `59f4d3332a0fc7510e5ad56b3eecefc9eba381e5`

---

## 1. Base / Purpose

**Base commit:** `59f4d3332a0fc7510e5ad56b3eecefc9eba381e5`.

The Cell-3 passive cost-context **source** was conceptually selected in `59f4d33` as a passive, deterministic,
zero-cost test-substrate emitting an exact non-empty tuple of one `ObservableCostValidityContext` via the existing
frozen Phase 5 factories. This charter **pins its exact field shape**: every constructor argument, the exact
hermetic string constants, the factory-only assembly path, and the exact length-1 tuple output — so that a future,
separately-authorized runtime TDD slice has an unambiguous, fabrication-free target.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Evidence-First (frozen contract cited before naming the shape)

Read from source (unchanged, frozen):

- **Downstream tuple expectation** — `phase5/pre_net_edge_calculation_input_boundary.py:339-406`:
  `cost_validity_contexts` must be an **exact non-empty `tuple`** (lists/sets/dicts/frozensets/Mappings/generators/
  iterators rejected), **preserved verbatim** (no sort/dedup/filter/aggregate), every item an **exact
  `ObservableCostValidityContext`**; **no** bound comparison, **no** TTL/freshness computation.
- **Validity-context factory** — `phase5/pre_net_edge_calculation_input_boundary.py:157-235`:
  `make_observable_cost_validity_context(*, cost_observation, valid_from_epoch_ms, valid_until_epoch_ms,
  validity_source_contract, validity_source_artifact, validity_source_field, validity_assertion_type,
  boundary_version)`. `cost_observation` must be an **exact `ObservableCostObservation`**; the seven metadata
  fields exact non-empty `str`; `valid_from_epoch_ms` / `valid_until_epoch_ms` exact **integer strings** (no sign,
  no decimal, no exponent), carried verbatim; **a reversed or equal interval is accepted** (comparison is gate
  behavior, not done here).
- **Observation factory** — `phase5/observable_cost_friction_boundary.py:145-216`:
  `make_observable_cost_observation(*, component_name, origin_component, origin_result_status, status,
  cost_component_type, signed_decimal_value, unit, source_contract, source_artifact, source_field,
  zero_cost_evidence, boundary_version)`. All twelve fields exact non-empty `str`; `signed_decimal_value` must
  match the **canonical decimal** `-?\d+(\.\d+)?`; **a numerically-zero value REQUIRES `zero_cost_evidence` to be
  an explicit string that is NOT the sentinel** `"OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE"`
  (`:30`, `:206-211`).

These confirm the §3–§6 shape is **directly constructible with zero downstream edits**.

---

## 3. Zero-Argument Generator Seal (binding)

The future source function takes **ZERO input arguments**:

```
def build_passive_zero_cost_validity_contexts():  # no parameters at all
    ...
```

It accepts **no** venue, pair, identity, payload, provenance, context, timestamp, or config input. Its entire
output is a fixed function of the hermetic constants in §4 — fully deterministic, with **no** dynamic generation,
UUID, hash, clock, counter, timestamp, env/config read, randomness, or external parameter. (The recommended name
`build_passive_zero_cost_validity_contexts` is lock-clean: it carries no forbidden token and no banned
name-surface substring; the runtime slice keeps the package-wide locks intact.)

---

## 4. Exact String Constant Hermeticity (binding)

Every constructor argument is a **fixed exact string constant**. The three constants explicitly mandated by this
charter:

| Constant | Exact value |
|----------|-------------|
| `signed_decimal_value` | `"0"` |
| `cost_component_type` | `"PASSIVE_ZERO_COST_SUBSTRATE"` |
| `zero_cost_evidence` | `"DECLARED_ZERO_COST_PASSIVE_SUBSTRATE_NO_REAL_FEE_SCHEDULE_CONSULTED"` |

`signed_decimal_value = "0"` matches the canonical decimal regex and is numerically zero, so the frozen factory
**requires** an explicit non-sentinel `zero_cost_evidence` — the mandated string above satisfies that and is **not**
equal to `"OBSERVABLE_COST_ZERO_EVIDENCE_NOT_APPLICABLE"`. The `cost_component_type` is an **honest passive label**
(the field has no closed vocabulary) that never implies a real maker/taker fee was measured.

### 4a. Full `ObservableCostObservation` field table (all twelve, fixed constants)

| Field | Exact constant value |
|-------|----------------------|
| `component_name` | `"phase6_1_cell3_passive_cost_context_source"` |
| `origin_component` | `"phase6_1_cell3_passive_cost_context_source"` |
| `origin_result_status` | `"OBSERVED"` |
| `status` | `"OBSERVABLE_COST_OBSERVED"` |
| `cost_component_type` | `"PASSIVE_ZERO_COST_SUBSTRATE"` |
| `signed_decimal_value` | `"0"` |
| `unit` | `"proportion"` |
| `source_contract` | `"phase6_1_cell3_passive_cost_context_source_field_shape_charter.md"` |
| `source_artifact` | `"docs/handoff/phase6_1_cell3_passive_cost_context_source_field_shape_charter.md"` |
| `source_field` | `"passive_zero_cost_substrate.signed_decimal_value"` |
| `zero_cost_evidence` | `"DECLARED_ZERO_COST_PASSIVE_SUBSTRATE_NO_REAL_FEE_SCHEDULE_CONSULTED"` |
| `boundary_version` | `"phase6_1.cell3_passive_cost_context_source.v0"` |

### 4b. Full `ObservableCostValidityContext` field table (fixed constants)

| Field | Exact constant value |
|-------|----------------------|
| `cost_observation` | the §4a `ObservableCostObservation` (by identity, factory-built) |
| `valid_from_epoch_ms` | `"0"` |
| `valid_until_epoch_ms` | `"0"` |
| `validity_source_contract` | `"phase6_1_cell3_passive_cost_context_source_field_shape_charter.md"` |
| `validity_source_artifact` | `"docs/handoff/phase6_1_cell3_passive_cost_context_source_field_shape_charter.md"` |
| `validity_source_field` | `"passive_zero_cost_substrate.validity_interval"` |
| `validity_assertion_type` | `"DECLARED_PASSIVE_SUBSTRATE_NO_REAL_VALIDITY_WINDOW"` |
| `boundary_version` | `"phase6_1.cell3_passive_cost_context_source.v0"` |

`valid_from_epoch_ms` and `valid_until_epoch_ms` are both the exact integer string `"0"` — a degenerate, equal
interval explicitly **accepted** by the frozen factory (which performs no bound comparison). They assert **no real
time window** and read **no clock**; the `validity_assertion_type` makes that non-assertion explicit. They are
carried verbatim provenance, never compared, never TTL'd.

---

## 5. Factory-Only Construction (binding)

The runtime MUST assemble the substrate **exclusively** through the existing frozen Phase 5 factories — first
`make_observable_cost_observation(...)` with the §4a constants, then
`make_observable_cost_validity_context(cost_observation=<that observation>, ...)` with the §4b constants. **Direct
`ObservableCostObservation` / `ObservableCostValidityContext` dataclass construction, `object.__new__`, attribute
setting, or any path that bypasses the factory validation is FORBIDDEN.** All field validation (exact-type,
non-empty, canonical decimal, explicit-zero evidence, integer-string bounds) is owned by the frozen factories and
is never re-implemented, relaxed, or duplicated here.

---

## 6. Exact Output Shape (binding)

The function returns an **exact standard Python `tuple` of length 1** containing **exactly one**
`ObservableCostValidityContext`:

```
(observable_cost_validity_context,)
```

**Forbidden:** a `list`, an empty tuple `()`, a `dict`, a `set`/`frozenset`, a generator/iterator, a custom
collection, a nested tuple, or any tuple with zero or more-than-one entries. The single context is the §4b object,
built per §5. This exact shape is precisely what the frozen `make_passive_pre_net_edge_calculation_input` requires
(exact non-empty tuple of exact items), so it threads through B3 → Producer → `calculate_net_edge` unchanged,
yielding `net == gross` purely because the carried cost magnitude is zero.

---

## 7. Passive Zero-Cost Semantics Only (binding)

This is a **test-substrate / passive** context, **not** a real fee model. It contains **NO** maker/taker logic,
VIP tier, fee schedule, venue fee table, discount/rebate, spread, slippage, or Cell-3 arithmetic. The zero is a
**carried constant** with explicit declared evidence — **never computed** from any fee input. Real cost economics
(the actual Cell-3 cost route) remain **separately gated and unbuilt**.

---

## 8. Semantic Starvation (binding)

The source performs **no** edge evaluation, threshold, ranking, score, classification, adjustment, or recompute;
it creates **no** actionability, readiness, routing, sizing, verdict, intent, or execution signal. It carries fixed
strings and returns a tuple — it makes **no** decision. It is consistent with the package-wide forbidden-token /
no-actionability locks.

---

## 9. Isolation & No Storage/Runner Logic (binding)

- **Identity isolation:** **no** S2 / Silver / `raw_snapshot_identity` / `MarketProvenanceContext` /
  `GrossEdgeBindingLabelContext` / B2-ingestion identity merge, derivation, copy, or reference. The substrate is
  self-contained and crosses no identity plane.
- **No storage/runner logic:** **no** S5 orchestration, **no** loop / queue / retry / repair / self-heal, **no**
  persistence / cursor / checkpoint / storage, **no** serialization. One zero-argument call returns one length-1
  tuple — pure, stateless, deterministic.

---

## 10. Scope Honesty (binding)

This charter may make a future, **separately-authorized Cell-3 passive cost-context source runtime TDD slice**
eligible (its constants and construction path are now unambiguous). It does **NOT** itself complete the pass path,
authorize any runtime/test/schema, authorize the real Cell-3 cost route or any cost arithmetic, authorize S5
runtime / S1 storage / live/paper/canary / execution / actionability, complete Phase 6.1, or ready Phase 6.2.

**Capacity invariant unchanged:** `CapacityConstraintGate` stays deferred / non-activatable with **0 emit sites**;
`PassiveShadowInput.capacity_pass_reference` stays `None` / deferred and is never read as "capacity validated."

---

## 11. Still-Forbidden Work

- **No** edit / widen / relax / refactor / bypass of any frozen module or factory (§5); **no** direct dataclass
  construction or validation bypass.
- **No** dynamic generation / UUID / hash / clock / counter / timestamp / env/config read / randomness / external
  parameter (§3, §4); **no** zero-argument violation (any input parameter is forbidden).
- **No** real fee schedule / maker-taker / VIP / discount / spread / slippage / venue fee table / Cell-3
  arithmetic (§7); **no** computed zero — the zero is a carried constant.
- **No** evaluation / threshold / rank / score / classification / adjustment / actionability / readiness / routing
  / sizing / verdict / execution / intent (§8).
- **No** S2 / Silver / `raw_snapshot_identity` / `MarketProvenanceContext` / `GrossEdgeBindingLabelContext` /
  B2-ingestion identity merge or reference (§9).
- **No** S5 orchestration / loop / queue / retry / repair / persistence / cursor / checkpoint / storage /
  serialization (§9).
- **No** output other than the exact length-1 tuple of one exact `ObservableCostValidityContext` (§6).
- **No** runtime / tests / schema; **no** Cell-3 real-cost runtime; **no** S5 runtime; **no** S1 storage; **no**
  live/paper/canary; **no** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Precise State

- **Field shape: PINNED (docs-only), UNBUILT.** Zero-argument generator; the §4a/§4b fixed constants (incl.
  `signed_decimal_value="0"`, `cost_component_type="PASSIVE_ZERO_COST_SUBSTRATE"`,
  `zero_cost_evidence="DECLARED_ZERO_COST_PASSIVE_SUBSTRATE_NO_REAL_FEE_SCHEDULE_CONSULTED"`); factory-only
  construction; exact length-1 tuple output.
- **B2 pass-path ingestion runtime:** BUILT + RATIFIED (unchanged).
- **Pass path:** still **NOT contract-complete** — the cost-context source is now field-shaped (docs-only) but
  **unbuilt**.
- **S5 runtime:** ineligible. **S1 storage:** separately gated. **Phase 6.1:** incomplete. **Phase 6.2:** not
  ready. **No executable work is authorized.**

---

## 13. Next Safe Step

- A **separately-authorized Cell-3 Passive Cost-Context Source runtime TDD slice** — implementing
  `build_passive_zero_cost_validity_contexts()` exactly per §3–§6 (zero-argument; §4a/§4b constants; factory-only;
  length-1 tuple) under RED→GREEN TDD with the package-wide locks intact and **no** frozen-component edit, plus its
  closeout/ratification.
- Independently, the **S1 storage-medium** charter remains separately gated.
- Only after **both** the pass path (B2 ingestion + this cost-context source, built + ratified) **and** the halt
  path are contract-complete may an **S5 Runner runtime TDD slice** be (separately) reconsidered for eligibility.
- **No implementation is authorized by this charter.**

**Conclusion:** the Cell-3 passive cost-context source field shape is **pinned exactly** — a **zero-argument**
deterministic generator that, **only** through the frozen `make_observable_cost_observation` and
`make_observable_cost_validity_context` factories, assembles **one** `ObservableCostValidityContext` from fixed
hermetic constants (`signed_decimal_value="0"`, `cost_component_type="PASSIVE_ZERO_COST_SUBSTRATE"`,
`zero_cost_evidence="DECLARED_ZERO_COST_PASSIVE_SUBSTRATE_NO_REAL_FEE_SCHEDULE_CONSULTED"`, plus the full §4a/§4b
field tables) and returns it as an **exact length-1 tuple** `(context,)`. It carries a **declared** zero with
explicit honest evidence, contains **no** real fee schedule / maker-taker / VIP / venue table / Cell-3 arithmetic /
computed zero, performs **no** evaluation/threshold/score/verdict/actionability, merges **no** identity, holds
**no** storage/runner logic, and reads **no** clock/config. It conforms to the **frozen** downstream tuple contract
with **zero edits**. This is a **field-shape selection only**: it may make a future cost-context source runtime TDD
slice eligible, but it **does not** complete the pass path, authorize S5 runtime / S1 storage / Cell-3 real-cost
runtime / execution, or complete Phase 6.1 / ready Phase 6.2. **No executable work is authorized.**
