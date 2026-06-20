# Phase 6.1 Cost-Component Vocabulary and B2 Carrier Amendment Charter

> **This is a docs-only planning charter.** It defines the path to unblock the cost-component vocabulary cell
> from the B3 mapping-extraction ratification, addressing **only** the cost-component vocabulary / B2 cost-type
> carrier gap. It authorizes NO runtime, NO tests, NO lock-test edits, NO B2 runtime/schema edit, NO Master B3
> wiring, NO Phase 5 integration, NO B4 scoring, NO durable logs, NO output carrier, NO capacity activation, NO
> Phase 6.2 work, NO pytest, NO graphify. **It invents no vocabulary.** It is subordinate to
> `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md`,
> `docs/handoff/phase6_1_b3_phase5_wiring_charter.md`, `docs/handoff/phase6_1_completion_sequencing_charter.md`,
> and `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `072360db83e3726d596d204b7b500a7c78dcf114`

---

## 1. Base / Dependency Chain

**Base commit:** `072360db83e3726d596d204b7b500a7c78dcf114`.

References:

- `docs/handoff/phase6_1_completion_sequencing_charter.md` — names the cost-vocabulary unblock as a prerequisite
  on the Master-B3 critical path.
- `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md` — ratified cells 1/2/4/5 and kept
  **Cell 3 (cost-component vocabulary) BLOCKED**.
- `docs/handoff/phase6_1_b3_phase5_wiring_charter.md` — the `normalized_field_name → cost_component_type`
  `BLOCKED_NEEDS_B3_MAPPING_EXTRACTION` cell.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Why This Charter Exists

Master B3 wiring needs to populate Phase 5's `make_observable_cost_observation.cost_component_type`. The B3
mapping-extraction ratification kept this BLOCKED because (a) Phase 5 defines no allowed vocabulary for the
field and (b) B2 carries no explicit cost-type source — so any `normalized_field_name → cost_component_type`
rule would be a B3-invented derivation over an undefined vocabulary. This charter records the repo evidence and
defines the docs-only path to resolve it, **without inventing the vocabulary**.

---

## 3. Explicit Split Boundary

- **In scope:** the cost-component vocabulary and the B2 cost-type carrier question **only**.
- **Out of scope:** `edge_direction` (deferred to the Shadow Intent Envelope track) — **not addressed here**.
- **Out of scope:** `staleness_threshold_ms` (temporal/freshness policy) — **not addressed here**.
- **Out of scope:** Shadow Intent Envelope and any temporal policy — **not addressed here**.

These remain separate, separately-gated Master-B3 blockers and are untouched by this charter.

---

## 4. Evidence Inventory Inspected (read-only)

- `phase5/observable_cost_friction_boundary.py` — `make_observable_cost_observation`: `cost_component_type` is
  validated **only** as an exact non-empty, non-whitespace `str` (generic field check); `signed_decimal_value`
  is a canonical decimal string. **No allowed-set, enum, or `frozenset` constrains `cost_component_type`.**
- `phase5/observable_cost_source_result_adapter.py` — passes `cost_component_type` through verbatim; defines no
  vocabulary.
- `phase5/const.py` and all `phase5/*.py` — **no** cost-component vocabulary constant
  (`_ALLOWED_COST_*` / enum) exists. (The only related `frozenset` is
  `_PRE_NET_EDGE_GATE_PROPORTIONAL_UNITS`, a *unit* allow-set, not a cost-type vocabulary.)
- Tests/fixtures — the only literal `cost_component_type` values in the repo are **`"TAKER_FEE"`** and
  **`"MAKER_REBATE"`** (e.g. `tests/test_phase5_observable_cost_friction_boundary.py`,
  `tests/test_phase5_observable_cost_source_result_adapter.py`, `tests/test_phase5_net_edge_calculator_boundary.py`).
  These are **test fixtures only**; no runtime contract enforces or closes this set.
- `phase6_1/b2_normalization_contract.py` — B2 carries **no** explicit `cost_component_type` /
  `cost_component_reference` field; the only cost-related B2 carriers are `binding_role ∈ {GROSS_EDGE, COST}`
  and the optional `zero_cost_evidence`.

---

## 5. Current Repo-Evidenced `cost_component_type` Behavior

- It is a **free-form, exact non-empty string** at the Phase 5 boundary — accepted verbatim, with **no closed
  vocabulary** and **no format constraint** beyond non-emptiness.
- Phase 5 carries and passes it through (observation → source-result adapter); the net-edge calculator does not
  re-derive it.
- The values `"TAKER_FEE"` / `"MAKER_REBATE"` appear **only as test fixtures**; they are **not** an authoritative
  or enforced runtime vocabulary.

---

## 6. Vocabulary Status — **BLOCKED**

**No explicit allowed vocabulary exists in runtime.** Therefore the cost-component vocabulary is **BLOCKED**, not
RATIFIED and not DEFERRED-to-an-owner:

- It cannot be **RATIFIED** — there is no repo-evidenced closed allowed-set to ratify.
- It is not merely **DEFERRED** to an existing owner — no Phase 5 component currently owns/closes the vocabulary
  (the field is open free-form string).
- The two test-fixture literals (`"TAKER_FEE"`, `"MAKER_REBATE"`) are **explicitly NOT ratified** here; treating
  test fixtures as a runtime contract would be inventing a vocabulary, which this charter forbids.

---

## 7. B2 Carrier Amendment Question — **BLOCKED (no design)**

- **Question:** does B2 need an explicit `cost_component_type` (or `cost_component_reference`) field so that B3
  can pass it through by identity rather than deriving it from `normalized_field_name`?
- **What supports it:** B3 must not invent a `normalized_field_name → cost_component_type` derivation; an
  explicit B2 carrier is the only non-derived path, consistent with how cells 1/2/5 were ratified (explicit B2
  fields, no derivation).
- **What blocks it:** the carrier's **domain is undefined** while the vocabulary is BLOCKED. Designing a B2
  cost-type field now would require choosing a value space — i.e. inventing the vocabulary. **No B2 carrier
  field is designed, named, typed, or implemented here.**
- **Conclusion:** the B2 carrier amendment is **BLOCKED behind vocabulary ratification**. Vocabulary first, then
  (separately) the carrier.

---

## 8. Risks If Guessed

- **Arbitrary strings** — an open free-form `cost_component_type` lets inconsistent values flow into Phase 5
  cost identity with no closed contract.
- **Schema drift** — ratifying test fixtures (`TAKER_FEE`/`MAKER_REBATE`) as the vocabulary couples runtime to
  incidental test data that may change.
- **B3 deriving cost meaning** — inventing a `normalized_field_name → cost_component_type` rule makes B3 a
  semantic deriver, violating the no-derivation rule.
- **Hidden actionability / scoring leakage** — a guessed cost taxonomy could smuggle in fee/slippage *modeling*
  or sizing/scoring semantics, which Phase 6.1 forbids.

---

## 9. Future Proof Targets (planning only — before any B2 carrier/runtime slice)

A future, separately authorized resolution must prove:

1. **A ratified closed vocabulary** for `cost_component_type` — its exact allowed value set, ratified from an
   authoritative source (a Phase 5 charter/decision, not test fixtures), or an explicit Phase 5 amendment that
   defines and enforces the set.
2. **An explicit, non-derived B2 carrier** for the cost type (field name/type to be designed only after the
   vocabulary is ratified), proven to be supplied by the artifact and never inferred from `normalized_field_name`,
   `source_field`, unit, magnitude, or tuple position.
3. **Identity/verbatim carriage** — the cost-type value flows B2 → B3 → Phase 5 verbatim, with no derivation,
   coercion, or modeling.
4. **No actionability/scoring** — the cost type carries no fee/slippage model, sizing, allocation, routing,
   score, or verdict semantics.
5. **Fail-fast on out-of-vocabulary** — once a closed set exists, an unknown cost type fails fast (no silent
   pass-through).

---

## 10. Still-Forbidden Work

- **No** vocabulary invented or chosen by assumption (test fixtures are not authoritative).
- **No** B2 carrier field designed, named, typed, or implemented.
- **No** Master B3 runtime/design/wiring.
- **No** Phase 5 integration; **no** parsing/casting/normalizing/bridging.
- **No** B4 scoring, durable logs, output carrier, Shadow Intent runtime/schema, or live adapter runtime.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.
- **No** touching of `edge_direction` or `staleness_threshold_ms`.

---

## 11. Is Master B3 Unblocked?

**No.** This charter cannot repo-ratify the cost-component vocabulary (none exists in runtime) and therefore
cannot ratify the B2 carrier path. **Cell 3 remains BLOCKED**, and `edge_direction` / `staleness_threshold_ms`
remain separate open blockers. Master B3 wiring stays gated.

---

## 12. Next Safe Step

- A **separate review** to decide whether to authorize a **docs-only cost-component vocabulary ratification
  charter** that establishes the closed allowed value set from an authoritative source (or a Phase 5 amendment
  that defines/enforces it) — **before** any B2 cost-type carrier slice.
- Only after the vocabulary is ratified may a B2 carrier amendment be chartered; only after that may Master B3
  wiring be chartered.
- **No implementation is authorized by this charter.** Master B3 wiring, B4 scoring, durable logs, the live
  adapter, Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.
