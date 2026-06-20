# Phase 6.1 Master B3 Remaining Blockers — Reclassification & Readiness Audit

> **This is a docs-only reclassification/readiness audit.** It re-checks the Master-B3 wiring blockers after the
> B2 passive cost-type carrier was **built and ratified** (commits `c5b842e` / `7471d6a`), reclassifying each
> blocker against current repo/docs evidence **without solving, designing, or deriving any of them**. It
> authorizes NO runtime, NO tests, NO lock-test edits, NO B3 runtime/tests, NO Phase 5 runtime/tests, NO Master
> B3 wiring, NO B4 scoring, NO durable logs, NO `edge_direction` design, NO `staleness_threshold_ms` design, NO
> Shadow Intent design/runtime/schema, NO capacity activation, NO Phase 6.2 work, NO pytest, NO graphify. **It
> designs nothing and authorizes nothing executable.** It is subordinate to
> `docs/handoff/phase6_1_b2_passive_cost_component_provenance_carrier_closeout_ratification.md`,
> `docs/handoff/phase6_1_b2_passive_cost_component_provenance_carrier_charter.md`,
> `docs/handoff/phase6_1_cost_component_vocabulary_necessity_decision_charter.md`,
> `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md`,
> `docs/handoff/phase6_1_b3_phase5_wiring_charter.md`,
> `docs/handoff/phase6_1_completion_sequencing_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `7471d6accd327e038d04e3173b322c4305865dda`

---

## 1. Base / Dependency Chain

**Base commit:** `7471d6accd327e038d04e3173b322c4305865dda`.

References:

- `docs/handoff/phase6_1_b2_passive_cost_component_provenance_carrier_closeout_ratification.md` — froze the
  passive carrier invariants; bound the **router-only B3 forward invariant**.
- `docs/handoff/phase6_1_b2_passive_cost_component_provenance_carrier_charter.md` — specified the passive
  carrier contract.
- `docs/handoff/phase6_1_cost_component_vocabulary_necessity_decision_charter.md` — verdict **B** (closed
  vocabulary NOT necessary for Phase 6.1).
- `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md` — ratified mapping cells 1/2/4/5; kept
  **Cell 3** BLOCKED; named the row-72 gaps.
- `docs/handoff/phase6_1_b3_phase5_wiring_charter.md` — the original `BLOCKED_NEEDS_B3_MAPPING_EXTRACTION` cell
  inventory.
- `docs/handoff/phase6_1_completion_sequencing_charter.md` — Master-B3 critical path.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Why This Reclassification Audit Exists

Building and ratifying the B2 passive cost-type carrier changed the **status of one Master-B3 blocker** (the
cost-component cell) without touching the others. Before any further charter is written, the blocker set must be
**re-stated against current evidence** so the project knows exactly what still gates Master B3 — and so no later
step mistakes the carrier's completion for Master-B3 readiness. This audit **reclassifies**; it does **not**
solve, design, derive, or unblock any remaining blocker.

---

## 3. Evidence Inventory Inspected (read-only)

- **Mapping cells (from `b3_mapping_extraction_ratification`):** Cells 1, 2, 4, 5 **RATIFIED** (explicit
  pass-through / no-coercion / event-time = `observed_at_epoch_ms`); **Cell 3 BLOCKED** at that time.
- **Row-72 gap list (from `b3_phase5_wiring`):** `edge_direction`, `instrument_id`, `staleness_threshold_ms`,
  `observed_size`, `size_unit`, `depth_source_*`, `zero_cost_evidence`, `*_contract`/`boundary_version` — Phase
  5 fields not then carried by the B2 binding schema.
- **B2 contract now (`phase6_1/b2_normalization_contract.py`, this base):** carries explicit `base_asset`,
  `quote_asset`, `instrument_id`, `venue_scope/buy/sell`, `observed_at_epoch_ms` + `retrieval_epoch_ms`,
  `zero_cost_evidence`, the depth chain (`depth_source_reference` → `PublicDepthSourceRecord` with
  `observed_size`/`size_unit`/…), and now the ratified **`cost_component_provenance_reference`** (passive). It
  does **not** carry `edge_direction` or `staleness_threshold_ms`.
- **Passive carrier closeout:** ratified passive-only; bound the forward invariant that any future B3 route may
  only carry the cost-type provenance **verbatim-or-`None`**, never validate/parse/branch/score/route/infer.

---

## 4. Original Master B3 Blocker List

From the wiring + mapping-extraction charters, the Master-B3 gate/mapping wiring was blocked by:

- **Cell 1** — `pair` → `base_asset`/`quote_asset` split.
- **Cell 2** — venue scope/buy/sell semantics.
- **Cell 3** — cost-component vocabulary (`normalized_field_name` → `cost_component_type`).
- **Cell 4** — numeric-coercion boundary.
- **Cell 5** — timestamp / canonical event-time boundary.
- **Row-72 schema gaps** — `edge_direction`, `instrument_id`, `staleness_threshold_ms`, `observed_size`,
  `size_unit`, `depth_source_*`, `zero_cost_evidence`, `*_contract`/`boundary_version` (Phase 5 fields not
  carried by B2 at that time).

---

## 5. Current Reclassification Table

| Blocker | Prior status | Current status | Nature | Evidence | B3 may solve internally? |
|---|---|---|---|---|---|
| Cell 1 `pair`→`base_asset`/`quote_asset` | BLOCKED | **RESOLVED (ratified)** | observation data | explicit B2 fields; pass-through ratified | **No** — pass-through only, no split |
| Cell 2 venue scope/buy/sell | BLOCKED | **RESOLVED (ratified)** | observation data | explicit B2 fields; pass-through ratified | **No** — pass-through only, no inference |
| Cell 4 numeric coercion | BLOCKED | **RESOLVED (ratified)** | policy (carrier discipline) | "B3 is not a coercer" ratified | **No** — B3 must not coerce |
| Cell 5 event-time | BLOCKED | **RESOLVED (ratified)** | observation data | event time = B2 `observed_at_epoch_ms`; retrieval never substituted | **No** — read `observed_at_epoch_ms` verbatim |
| Cell 3 cost-component | BLOCKED (needs closed vocab) | **DOWNGRADED → carrier built; route pending (not blocking on vocabulary)** | passive provenance | B2 `cost_component_provenance_reference` built + ratified; closed vocab NOT necessary (verdict B) | **No** — verbatim-or-`None` route only, no validation/inference |
| `instrument_id` | BLOCKED (schema gap) | **RESOLVED (carried)** | observation data | explicit B2 `instrument_id` field | **No** — pass-through only |
| `observed_size` / `size_unit` / `depth_source_*` | BLOCKED (schema gap) | **RESOLVED (carried)** | observation data | depth chain `depth_source_reference` → `PublicDepthSourceRecord` | **No** — by-identity carry, no parse |
| `zero_cost_evidence` | BLOCKED (schema gap) | **RESOLVED (carried)** | passive provenance | explicit optional B2 carrier | **No** — pass-through only |
| `*_contract` / `boundary_version` | BLOCKED (schema gap) | **RESOLVED (carried)** | passive provenance | component/boundary fields on B2 carriers | **No** — pass-through only |
| **`edge_direction`** | BLOCKED (schema gap) | **STILL BLOCKED** | **intent / actionability** | not carried by B2; tied to **deferred** Shadow Intent Envelope | **No** — see §7.1 |
| **`staleness_threshold_ms`** | BLOCKED (schema gap) | **STILL BLOCKED** | **policy (temporal)** | not carried by B2; no ratified source | **No** — see §7.2 |

Two blockers remain genuinely unresolved: **`edge_direction`** and **`staleness_threshold_ms`**. All other
named blockers are either ratified mapping decisions or now carried by B2 / the depth chain.

---

## 6. Cost-Component Cell 3 — Downgrade / Reframe

Cell 3 is **downgraded**, not solved:

- It **no longer requires a closed `cost_component_type` vocabulary** for Phase 6.1 (necessity verdict B).
- The **B2 passive cost-type carrier is built and ratified** (`cost_component_provenance_reference`).
- Any future Master B3 route may pass this value **verbatim-or-`None` only**.
- B3 is **forbidden** to validate, parse, branch, score, route, infer polarity, or choose behavior from it
  (passive carrier closeout §5 forward invariant — **not weakened here**).
- **What remains for Cell 3:** a separately-authorized **router-only B3 cost-type pass-through charter**. This
  is no longer a *vocabulary* blocker; it is an unbuilt, separately-gated route. It does **not** by itself
  unblock Master B3 (which still depends on §7).

Cost vocabulary **values remain BLOCKED** and are **not reopened** here; the downgrade rests only on the
ratified passive-carrier path, not on any value set.

---

## 7. Remaining Blocker Isolation

### 7.1 — `edge_direction` — STILL BLOCKED (intent / actionability)
- **Classification:** **intent / actionability** field. It expresses a directional call, not a passively
  observed magnitude, and is tied to the **deferred Shadow Intent Envelope** track.
- **Actionability/intent risk:** deriving `edge_direction` from prices, magnitude sign, gross-vs-cost
  comparison, or any field would manufacture a **trade-direction decision** inside B3 — exactly the
  actionability Phase 6.1 forbids. It is not observation data and not passive provenance.
- **B3 may solve internally? NO.** B3 must neither assign nor derive `edge_direction`. **No design, no source,
  no rule is proposed here** — it is recorded as an unresolved intent blocker only.

### 7.2 — `staleness_threshold_ms` — STILL BLOCKED (temporal policy)
- **Classification:** **policy (temporal/freshness)**. A threshold is a chosen policy parameter, not an
  observation.
- **Temporal-policy risk:** deriving it from timestamps (`observed_at`/`retrieval` deltas) or picking any
  numeric bound would invent a freshness policy inside B3 — a threshold/branch Phase 6.1 forbids B3 to own.
- **B3 may solve internally? NO.** B3 must neither derive nor default `staleness_threshold_ms`. **No threshold,
  no derivation, no policy is proposed here** — recorded as an unresolved policy blocker only.

---

## 8. Master B3 Readiness Verdict — **BLOCKED**

**Master B3 is NOT ready to be chartered for wiring.** Per the red-team rule that readiness requires **every**
blocker to be explicitly resolved or externally supplied by a prior ratified contract:

- The mapping cells (1/2/4/5) and the previously-named schema gaps that are now carried (instrument_id, depth
  fields, zero-cost evidence, contract/boundary) are resolved/ratified.
- Cell 3 is downgraded to a pending **router-only route** (no longer vocabulary-blocked) but is **not yet
  built**.
- **`edge_direction`** and **`staleness_threshold_ms`** remain **unresolved** (intent and policy respectively),
  with **no ratified source** and **no permission for B3 to solve them**.

Because two genuine blockers remain unresolved and one cell still lacks its route, the verdict is **BLOCKED**.
(If a narrower label is wanted: the *carry-able observation/provenance surface* is substantially ready, but
**Master B3 as a whole is BLOCKED** — it cannot be chartered until §7 is resolved and the Cell-3 route is
separately authorized.)

---

## 9. Recommended Sequencing (recommendation only — nothing designed)

In dependency order, the next **docs-only** steps (each separately authorized; none designed or implemented
here):

1. **`edge_direction` classification / necessity audit** — a docs-only decision on whether `edge_direction` is
   required for Master B3 at all, and if so where it must originate (almost certainly the deferred Shadow Intent
   Envelope, **not** B3), explicitly **without** assigning or deriving a direction.
2. **`staleness_threshold_ms` classification / necessity audit** — a docs-only decision on whether a freshness
   threshold is required for Master B3 and who owns it, explicitly **without** choosing a value or deriving one
   from timestamps.
3. **Router-only B3 cost-type pass-through charter** (Cell 3) — may proceed independently under the §6 / closeout
   forward invariant (verbatim-or-`None`, no validation/inference), but does **not** unblock Master B3 alone.
4. Only after (1) and (2) are resolved **and** (3) is built may a **Master B3 wiring charter** be considered.

This is sequencing guidance only; it authorizes none of the above.

---

## 10. Still-Forbidden Work

- **No** solving/designing/deriving `edge_direction`; **no** assigning it from prices/sign/magnitude/any field.
- **No** solving/designing/deriving `staleness_threshold_ms`; **no** deriving it from timestamps; **no** chosen
  threshold.
- **No** thresholds, policies, if/else logic, scoring, routing, or actionability introduced anywhere.
- **No** reopening of cost vocabulary **values**; **no** weakening of the B2 passive carrier invariants.
- **No** runtime/tests/lock-test edits; **no** B3 runtime/tests; **no** B3 route designed; **no** Master B3
  wiring; **no** Phase 5 runtime/tests/integration; **no** B4 scoring; **no** durable logs; **no** Shadow Intent
  design/runtime/schema; **no** live adapter.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.
- **No** reversal or weakening of the ratified owner (Phase 5) or mechanism (M3).

---

## 11. Next Safe Step

- A **separate docs-only `edge_direction` classification / necessity audit** (sequencing item 1) — deciding
  whether Master B3 requires `edge_direction` and where it must originate, **without** designing, assigning, or
  deriving it.
- Independently, sequencing items 2 (staleness audit) and 3 (router-only Cell-3 pass-through charter) may each
  be separately authorized.
- **No implementation is authorized by this charter.** Master B3 wiring, any B3 route, Phase 5 integration,
  Phase 5 vocabulary closure (under M3, if ever needed), B4 scoring, durable logs, the live adapter, Shadow
  Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.
