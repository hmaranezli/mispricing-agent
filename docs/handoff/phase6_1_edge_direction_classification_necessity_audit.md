# Phase 6.1 `edge_direction` Classification & Necessity Audit

> **This is a docs-only classification/necessity audit.** It classifies `edge_direction` architecturally and
> decides whether it is necessary for Phase 6.1 / Master B3 passive shadow scoring — **without solving,
> defining, designing, deriving, or proposing any `edge_direction` mechanism**. It authorizes NO runtime, NO
> tests, NO lock-test edits, NO B2/B3 runtime/schema/carrier changes, NO Master B3 wiring, NO B4 scoring, NO
> durable logs, NO Shadow Intent Envelope design/runtime/schema, NO `staleness_threshold_ms` design/policy, NO
> capacity activation, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_readiness_audit.md`,
> `docs/handoff/phase6_1_b3_phase5_wiring_charter.md`,
> `docs/handoff/phase6_1_shadow_intent_envelope_contract_charter.md`,
> `docs/handoff/phase6_1_structural_boundary_ratification_charter.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `0fcc85fad636f710c6aec47fea0d8587d4f3fe97`

---

## 1. Base / Dependency Chain

**Base commit:** `0fcc85fad636f710c6aec47fea0d8587d4f3fe97`.

References:

- `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_readiness_audit.md` — classified
  `edge_direction` as a **STILL BLOCKED** intent/actionability blocker; recommended this audit as sequencing
  item 1.
- `docs/handoff/phase6_1_b3_phase5_wiring_charter.md` — lists `edge_direction` as a Phase 5 field **not carried
  by B2** (`BLOCKED_NEEDS_B3_MAPPING_EXTRACTION`).
- `docs/handoff/phase6_1_shadow_intent_envelope_contract_charter.md` — ratified **Option B**: direction supplied
  **only** via an explicit typed per-fixture **Shadow Intent Envelope** (external authorship); B1/B2/B3 must
  never infer/compute/default/derive/fabricate it; envelope runtime/schema **BLOCKED**.
- `docs/handoff/phase6_1_structural_boundary_ratification_charter.md` — structural boundary discipline.
- `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md` — B1→B2→B3→**B4 passive shadow scoring**
  (`ShadowObservation`/`ShadowScore`, passive diagnostics only; no actionability/order intent).

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Why This Audit Exists

The Master-B3 readiness audit isolated `edge_direction` as one of two genuinely unresolved Master-B3 blockers,
classified provisionally as intent/actionability. Before any Master-B3 step, that classification must be
**firmly established from evidence**, and the **necessity** of `edge_direction` for the Phase 6.1 passive shadow
path must be examined directly — rather than assumed mandatory because older wiring docs list it. This audit
does that classification and necessity decision. It **solves nothing** and proposes **no mechanism**.

---

## 3. Evidence Inventory Inspected (read-only)

- **Phase 5 runtime** — `phase5/gross_edge_observation_boundary.py`: `make_gross_edge_observation` declares
  `edge_direction` as a **required** field validated against a closed set
  `_ALLOWED_DIRECTIONS = frozenset({"LONG", "SHORT", "CROSS_VENUE"})`, **fail-fast** on out-of-set
  (`"field 'edge_direction' must be one of the allowed direction labels"`). `CROSS_VENUE` additionally requires
  distinct `venue_buy`/`venue_sell`. So the **Phase 5 gross-edge gate cannot be constructed without a valid
  `edge_direction`.**
- **Shadow Intent Envelope charter** — `edge_direction` is the **only** allowed semantic payload of a future,
  externally-authored, replay/shadow-only Shadow Intent Envelope (Option B). It is **not** a
  trade/order/execution/paper/live object. **B1/B2/B3 must never infer, compute, default, derive, or fabricate
  it; no global static dummy is allowed; market provenance and intent provenance must remain disjoint.** The
  envelope runtime/schema is **BLOCKED/deferred**.
- **B2 contract (current)** — `phase6_1/b2_normalization_contract.py` carries market-evidence fields only
  (identity, magnitudes/units, timestamps, depth-by-identity, passive cost-type provenance). It carries **no**
  `edge_direction` and, per the SIE charter, must never carry/derive it as market evidence.
- **Shadow scoring TDD planning** — the B4 passive path produces `ShadowObservation`/`ShadowScore` as **passive
  diagnostics**; EV fields are `diagnostic_`/`passive_`-prefixed and **must not imply actionability,
  recommendation, readiness, or order intent.** The planning does **not** repo-prove that the passive shadow
  path constructs a full Phase 5 gross-edge gate observation (and thus requires `edge_direction`).
- **Master-B3 readiness audit** — records `edge_direction` as unresolved intent; B3 forbidden to solve it.

---

## 4. Current `edge_direction` Mentions & Requirements

- **Phase 5:** required, closed-vocabulary (`LONG`/`SHORT`/`CROSS_VENUE`), fail-fast — a hard prerequisite **to
  construct a Phase 5 `GrossEdgeObservation`.**
- **Wiring charter:** listed among Phase 5 fields not carried by B2 → a Master-B3 schema gap **if** Master B3
  must build that Phase 5 observation.
- **Shadow Intent Envelope charter:** the sole sanctioned **source** is an external, typed, per-fixture
  envelope; the value is **intent**, not observation; derivation is banned; the envelope itself is deferred.
- **Shadow scoring planning:** passive scoring path; **no evidence** that it requires the edge-direction-bearing
  Phase 5 gate.

The mentions establish a **conditional** requirement: `edge_direction` is required **to construct the Phase 5
gross-edge gate**, but whether the Phase 6.1 *passive* path constructs that gate is **not repo-proven**.

---

## 5. Architectural Classification — **INTENT / actionability input (DECIDED)**

`edge_direction` is classified as an **externally-supplied intent / actionability input**, not observation, not
passive metadata, not B2/B3-derivable data.

| Candidate class | Verdict | Why |
|---|---|---|
| **Observation (market fact)** | **Rejected** | B2 observes what the market *is* (prices, depth, magnitudes, venues). A *direction we would take* is not a market fact; B2 "does not know our intent." |
| **Passive provenance metadata** | **Rejected** | Unlike `cost_component_provenance_reference`, `edge_direction` is **semantically consumed** by Phase 5 (closed-set, fail-fast, drives `CROSS_VENUE` venue constraints). It is load-bearing, not a passive label. |
| **External intent input** | **ACCEPTED** | The SIE charter ratifies it as externally-authored intent (Option B), the only allowed envelope payload; values match Phase 5's closed direction set. |
| **Internally derivable (B2/B3)** | **Forbidden** | Deriving it from any field would manufacture a trade-direction decision inside the observation/mapping layers — the actionability Phase 6.1 forbids. |

**Architectural home (if needed at all):** the **deferred Shadow Intent Envelope** (external, typed, per-fixture).
It must **not** be owned by B2 or solved internally by B3. *This audit designs no envelope.*

---

## 6. Necessity Decision for Phase 6.1 / Master B3 — **BLOCKED / DEFERRED**

**Verdict: BLOCKED / DEFERRED.** From current evidence, `edge_direction` can be ratified neither **NECESSARY**
nor **NOT NECESSARY** for the Phase 6.1 passive shadow path, because its necessity is **contingent** on a
question that the repo does not yet answer, and its only sanctioned source is itself deferred:

- **If** the Phase 6.1 passive shadow path constructs a Phase 5 `GrossEdgeObservation` (which requires
  `edge_direction`), **then** `edge_direction` is **necessary** — but only as an **external** value from the
  (deferred) Shadow Intent Envelope, **never** derived by B2/B3.
- **If** the passive shadow path scores `ShadowObservation`/`ShadowScore` **without** invoking the
  edge-direction-bearing Phase 5 gross-edge gate, **then** `edge_direction` may be **not necessary** for Phase
  6.1 — but the planning docs do **not** repo-prove which path is taken.
- The escape hatch is honored: `edge_direction` is **not assumed mandatory** merely because older wiring docs
  list it. But neither can NOT-NECESSARY be asserted without proof that the passive path bypasses the Phase 5
  gross-edge gate.

Therefore the necessity is **DEFERRED** pending a separate, evidence-based decision on **whether the Phase 6.1
passive shadow path invokes the Phase 5 gross-edge gate at all**. Until that is decided (and until the Shadow
Intent Envelope is chartered if it is needed), `edge_direction` remains an **open, externally-sourced blocker**.

---

## 7. Explicit Derivation / Inference Ban

`edge_direction` MUST NEVER be derived, inferred, computed, defaulted, or fabricated from any B2/B3 field or
combination thereof — explicitly including `venue_buy`, `venue_sell`, `venue_scope`, `base_asset`,
`quote_asset`, `pair`, `instrument_id`, observed prices/magnitudes, depth, cost, `cost_component_provenance_reference`,
`zero_cost_evidence`, timestamps, or any provenance field. **No global static dummy direction** is permitted.
**Market provenance and intent provenance must remain disjoint.** B2 observes market facts; it does not know our
intent.

---

## 8. What B2 May / May Not Do

- **May:** continue carrying market-evidence fields exactly as ratified (identity, magnitudes/units, timestamps,
  depth-by-identity, passive cost-type provenance).
- **May not:** carry, own, derive, default, or infer `edge_direction`; **may not** add an `edge_direction`
  field; **may not** reuse market-evidence provenance as intent provenance. The B2 passive-carrier invariants
  are **not weakened** by this audit.

---

## 9. What Master B3 May / May Not Do

- **May:** (only when separately chartered) route ratified, carried observation/provenance fields by explicit
  pass-through.
- **May not:** assign, derive, infer, default, or fabricate `edge_direction`; **may not** invent it to fill the
  Phase 5 gate's required field; **may not** treat any market field as a direction. If `edge_direction` is ever
  required at the B3→Phase 5 seam, B3 may only **carry an externally-supplied value verbatim** from the (future,
  separately-chartered) Shadow Intent Envelope — never produce one. *No such route is authorized here.*

---

## 10. Effect on Master B3 Readiness / Blockers

- **Master B3 remains BLOCKED.** This audit firms the classification (intent, external) and defers necessity; it
  resolves **no** blocker.
- `edge_direction` stays an **open, externally-sourced blocker**, now sharpened: its resolution depends on (a) a
  decision whether the passive path invokes the Phase 5 gross-edge gate, and (b) if so, the deferred Shadow
  Intent Envelope being chartered to supply it.
- `staleness_threshold_ms` remains a **separate** unresolved policy blocker (out of scope here). The Cell-3
  router-only cost-type pass-through remains separately gated. None is unblocked.

---

## 11. Still-Forbidden Work

- **No** solving/defining/designing/deriving/proposing any `edge_direction` mechanism, source, default, or
  value; **no** envelope design.
- **No** assigning `edge_direction` from prices/sign/venue/any field; **no** global/static dummy direction.
- **No** B2/B3 runtime/schema/carrier change; **no** Master B3 wiring; **no** Phase 5 runtime/tests/integration;
  **no** B4 scoring; **no** durable logs; **no** Shadow Intent Envelope design/runtime/schema; **no** live
  adapter.
- **No** `staleness_threshold_ms` design/policy/derivation.
- **No** thresholds, policies, if/else logic, scoring, routing, or actionability introduced anywhere.
- **No** reopening of cost vocabulary values; **no** weakening of the B2 passive cost-type carrier invariants.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Next Safe Step

- A **separate docs-only decision** on **whether the Phase 6.1 passive shadow path invokes the Phase 5
  gross-edge gate** (and therefore whether `edge_direction` is needed at all for Phase 6.1) — read-only,
  evidence-based, designing nothing. That decision converts this DEFERRED verdict into NECESSARY (→ then a
  separately-chartered Shadow Intent Envelope) or NOT NECESSARY (→ `edge_direction` dropped from the Phase 6.1
  Master-B3 surface).
- Independently, the `staleness_threshold_ms` classification/necessity audit and the router-only Cell-3
  pass-through charter may each be separately authorized.
- **No implementation is authorized by this charter.** Master B3 wiring, any B3 route, the Shadow Intent
  Envelope, Phase 5 integration, B4 scoring, durable logs, the live adapter, capacity activation, Phase 6.2, and
  7.x/8.x remain separately gated.
