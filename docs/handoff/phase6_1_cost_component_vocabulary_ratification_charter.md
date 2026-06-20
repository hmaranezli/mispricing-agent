# Phase 6.1 Cost-Component Vocabulary Ratification Charter

> **This is a docs-only ratification/planning charter.** It determines whether a closed cost-component
> vocabulary can be ratified from existing repo evidence and, finding it cannot, formally keeps it BLOCKED and
> defines the exact future proof required. It authorizes NO runtime, NO tests, NO lock-test edits, NO Phase 5
> runtime amendment, NO B2 runtime/schema/carrier amendment, NO Master B3 wiring, NO Phase 5 integration, NO B4
> scoring, NO durable logs, NO `edge_direction`, NO `staleness_threshold_ms`, NO Shadow Intent, NO capacity
> activation, NO Phase 6.2 work, NO pytest, NO graphify. **It invents no vocabulary** and **promotes no test
> fixture to contract.** It is subordinate to
> `docs/handoff/phase6_1_cost_component_vocabulary_b2_carrier_amendment_charter.md`,
> `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md`,
> `docs/handoff/phase6_1_completion_sequencing_charter.md`,
> `docs/handoff/phase6_1_b3_phase5_wiring_charter.md`, and `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `9082eb0b59c86a585734fc28e83a470f08ec6b29`

---

## 1. Base / Dependency Chain

**Base commit:** `9082eb0b59c86a585734fc28e83a470f08ec6b29`.

References:

- `docs/handoff/phase6_1_cost_component_vocabulary_b2_carrier_amendment_charter.md` — split the cost-vocabulary
  gap out and kept it BLOCKED pending this ratification attempt.
- `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md` — kept Cell 3 (cost-component
  vocabulary) BLOCKED.
- `docs/handoff/phase6_1_completion_sequencing_charter.md` — places this on the Master-B3 critical path.
- `docs/handoff/phase6_1_b3_phase5_wiring_charter.md` — the `normalized_field_name → cost_component_type` cell.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Why This Charter Exists

Master B3 must populate Phase 5's `make_observable_cost_observation.cost_component_type`, but that mapping was
blocked because no closed vocabulary was known to exist. This charter performs an **exhaustive repo evidence
sweep** to decide whether a closed, authoritative vocabulary can be **ratified now** — and, if not, to record
the precise future proof needed so the gap is governed rather than guessed.

---

## 3. Evidence Inventory Inspected (read-only)

- **Phase 5 runtime** — `phase5/observable_cost_friction_boundary.py::make_observable_cost_observation`:
  `cost_component_type` is validated **only** as an exact non-empty, non-whitespace `str`. A whole-`phase5/`
  sweep finds **no** `frozenset` / `_ALLOWED_*` / enum / `in {...}` / `== "..."` constraint on the field.
  `phase5/observable_cost_source_result_adapter.py` passes it through verbatim. `phase5/const.py` defines no
  cost-component vocabulary. (The only nearby allow-set is `_PRE_NET_EDGE_GATE_PROPORTIONAL_UNITS`, a **unit**
  set.)
- **Tests** — the only `cost_component_type` literals in the entire `tests/` tree are `"TAKER_FEE"` (6
  occurrences) and `"MAKER_REBATE"` (3 occurrences), supplied as constructor arguments in Phase 5 tests.
- **Planning docs** — `docs/handoff/phase5_observable_cost_friction_boundary_implementation_planning.md`
  **explicitly declines** to define a closed cost-type vocabulary ("not an exchange parser, fee schedule
  parser, slippage model…"); its sign rule ("negative value = rebate/credit, such as maker rebate") concerns
  the **value sign**, not a `cost_component_type` enum; and its labels (`bps`, `decimal_rate`, `quote_amount`,
  `base_amount`, `fee_rate`, `spread_bps`, `slippage_bps`) are **unit/scale** examples, explicitly *not* a
  cost-type set, with the exact unit/scale vocabulary itself deferred to a later step.
- **B2** — `phase6_1/b2_normalization_contract.py` carries **no** `cost_component_type` / `cost_component_reference`
  field (only `binding_role ∈ {GROSS_EDGE, COST}` and optional `zero_cost_evidence`).

---

## 4. Candidate Literals Found — Source Classification

| Candidate | Where it appears | Classification |
|-----------|------------------|----------------|
| `TAKER_FEE` | Phase 5 tests (6×) | **test fixture only** |
| `MAKER_REBATE` | Phase 5 tests (3×) | **test fixture only** |
| `bps`, `decimal_rate`, `quote_amount`, `base_amount`, `fee_rate`, `spread_bps`, `slippage_bps` | cost-friction planning doc | **planning prose only** — and these are **unit/scale** labels, **NOT** `cost_component_type` values |
| any closed `cost_component_type` allowed set | — | **absent** (no runtime contract) |

No literal is a **runtime contract**. The only cost-type literals (`TAKER_FEE`, `MAKER_REBATE`) are **test
fixtures**, which this charter explicitly does **not** promote to contract.

---

## 5. Vocabulary Ratification Decision — **BLOCKED**

**No closed, authoritative, repo-evidenced cost-component vocabulary exists.** Therefore the vocabulary is
**BLOCKED**:

- Not **RATIFIED** — there is no closed authoritative allowed-set anywhere (runtime, tests-as-contract, or
  planning prose).
- Not cleanly **DEFERRED** to a named owner — no doc assigns a future owner the duty of closing the
  `cost_component_type` set (the planning doc defers only *unit/scale* vocabulary, not the cost-type set).
- `TAKER_FEE` / `MAKER_REBATE` are **NOT ratified** — promoting test fixtures to a runtime contract is forbidden
  by this charter's bounds.

---

## 6. Vocabulary Ownership Decision — **UNRESOLVED**

- **Field home:** `cost_component_type` is a **Phase 5** field (it is a parameter of the Phase 5
  `make_observable_cost_observation` factory). Repo evidence proves the field lives in Phase 5.
- **Vocabulary-definition ownership:** **UNRESOLVED.** No repo evidence proves any layer currently owns
  *closing* the vocabulary — Phase 5 presently accepts it as an open free-form string and its planning doc
  declines to close it.
- **B2 and B3 must not own or invent it.** There is no repo evidence granting B2 or B3 authority over the
  vocabulary, so they may not define, derive, or default it. Because the field's home is Phase 5, any future
  closing amendment would most naturally be a **Phase 5** amendment — but this is **not asserted as a ratified
  ownership decision here** (it is not repo-proven; it is recorded only as the evidence-consistent direction).

---

## 7. Future Proof Required Before Any B2 Cost-Type Carrier Charter

Before a B2 cost-type carrier may be chartered, a future, separately authorized step must establish:

1. **An authoritative closed allowed-set** for `cost_component_type` — its exact value space, ratified from an
   authoritative source: either a ratified Phase 5 charter/decision that **closes** the set, **or** a Phase 5
   runtime amendment that **defines and enforces** it (fail-fast on out-of-set values). Test fixtures do not
   qualify.
2. **A named owning layer** for the vocabulary (evidence-based, not by preference).
3. Only **after** (1) and (2): the **explicit, non-derived B2 carrier** question may be chartered — never
   inferred from `normalized_field_name`, `source_field`, unit, magnitude, or position.
4. **Verbatim, non-actionable carriage** — once a carrier exists, the value flows B2 → B3 → Phase 5 verbatim,
   with no fee/slippage modeling, sizing, scoring, or verdict semantics, and fail-fast on unknown values.

---

## 8. B2 Carrier Amendment Remains Blocked

The B2 cost-type carrier amendment **remains BLOCKED** until the vocabulary is ratified (§5/§6/§7). No B2
carrier field is designed, named, typed, or implemented by this charter.

---

## 9. Master B3 Remains Blocked

**Master B3 wiring remains BLOCKED.** This charter could not repo-ratify the cost-component vocabulary, so
Cell 3 stays BLOCKED; and `edge_direction` / `staleness_threshold_ms` remain separate, out-of-scope blockers.

---

## 10. Still-Forbidden Work

- **No** vocabulary defined/chosen by assumption; **no** promotion of `TAKER_FEE`/`MAKER_REBATE` from fixtures
  to contract.
- **No** vocabulary ownership assigned by preference.
- **No** B2 carrier field designed/named/typed/implemented.
- **No** Phase 5 validation runtime designed/implemented.
- **No** Master B3 runtime/design/wiring; **no** Phase 5 integration; **no** B4 scoring; **no** durable logs;
  **no** output carrier; **no** Shadow Intent; **no** live adapter.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.
- **No** touching of `edge_direction` or `staleness_threshold_ms`.

---

## 11. Next Safe Step

- A **separate review** to decide whether to authorize a **docs-only Phase 5 cost-component vocabulary
  decision** — i.e. whether Phase 5 should close the `cost_component_type` set (and, if so, the authoritative
  allowed values and the owning Phase 5 amendment), since the field's home is Phase 5.
- Only after the vocabulary is ratified and owned may a B2 cost-type carrier amendment be chartered; only after
  that may Master B3 wiring be chartered.
- **No implementation is authorized by this charter.** Phase 5 vocabulary runtime, B2 carrier, Master B3
  wiring, B4 scoring, durable logs, the live adapter, Shadow Intent Envelope, capacity activation, Phase 6.2,
  and 7.x/8.x remain separately gated.
