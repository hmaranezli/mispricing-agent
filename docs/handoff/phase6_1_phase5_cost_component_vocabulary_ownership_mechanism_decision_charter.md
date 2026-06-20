# Phase 6.1 Phase 5 Cost-Component Vocabulary — Ownership & Mechanism Decision Charter

> **This is a docs-only decision charter.** It decides exactly two things — **(1) who owns closing
> `cost_component_type`** and **(2) which closure mechanism (M1–M4) governs the future vocabulary** — and
> **nothing about the vocabulary values**. It authorizes NO runtime, NO tests, NO lock-test edits, NO Phase 5
> runtime amendment, NO B2 runtime/schema/carrier amendment, NO Master B3 wiring, NO Phase 5 integration, NO B4
> scoring, NO durable logs, NO `edge_direction`, NO `staleness_threshold_ms`, NO Shadow Intent, NO capacity
> activation, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_phase5_cost_component_vocabulary_decision_charter.md`,
> `docs/handoff/phase6_1_cost_component_vocabulary_ratification_charter.md`,
> `docs/handoff/phase6_1_cost_component_vocabulary_b2_carrier_amendment_charter.md`,
> `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md`,
> `docs/handoff/phase6_1_completion_sequencing_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `53d3e9825d664e5f98cdaef8b314c4712adcc380`

---

## 1. Base / Dependency Chain

**Base commit:** `53d3e9825d664e5f98cdaef8b314c4712adcc380`.

References:

- `docs/handoff/phase6_1_phase5_cost_component_vocabulary_decision_charter.md` — framed ownership (Phase 5
  candidate; final UNRESOLVED) and the closure mechanism option space M1–M4 (none selected).
- `docs/handoff/phase6_1_cost_component_vocabulary_ratification_charter.md` — found no closed authoritative
  vocabulary; vocabulary BLOCKED, ownership UNRESOLVED.
- `docs/handoff/phase6_1_cost_component_vocabulary_b2_carrier_amendment_charter.md` — B2 carrier BLOCKED.
- `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md` — Cell 3 BLOCKED.
- `docs/handoff/phase6_1_completion_sequencing_charter.md` — Master-B3 critical path.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Why This Decision Charter Exists

Ownership and closure-mechanism are logically prior to the vocabulary values: until it is decided **who** may
close the set and **by what mechanism**, no values charter can be authored. The prior framing charter laid out
the option space but selected nothing. This charter makes those two decisions where the evidence/architecture is
sufficient, while keeping the **value space entirely out of scope**.

---

## 3. Scope — Exactly Owner + Mechanism; Value-Space Forbidden

- **In scope:** (1) the owner of closing `cost_component_type`; (2) the governing closure mechanism (one of
  M1–M4).
- **Forbidden (total value-space ban):** defining/proposing/selecting/endorsing **any** vocabulary value,
  initial list, illustrative enum-with-values, or fixture/prose example. All future values remain **opaque /
  placeheld**.
- **Out of scope:** `edge_direction`, `staleness_threshold_ms`, Shadow Intent, capacity, B2 carrier design,
  Master B3 runtime.

---

## 4. Evidence Inventory (carried from prior charters)

- `cost_component_type` is a **Phase 5** field — a parameter of `make_observable_cost_observation`, consumed and
  interpreted within the Phase 5 cost path.
- Phase 5 currently validates it **only** as a free-form non-empty string; **no** closed allowed-set exists in
  runtime, tests-as-contract, or planning prose.
- The only literals (`TAKER_FEE`, `MAKER_REBATE`) are **test fixtures**; planning-doc labels are **unit/scale**,
  not cost-type values. **None is endorsed here.**
- B2 is **carrier-only**; B3 is **router-only**; both are constitutionally barred from owning/inventing the
  vocabulary.

---

## 5. Ownership Decision — **RATIFIED: Phase 5 owns closing `cost_component_type`**

- **Decision:** **Phase 5** is the owner entitled to close (define and enforce) the `cost_component_type` set.
- **Status:** **RATIFIED** (on architectural + by-elimination grounds; see §7). This resolves the prior
  charter's UNRESOLVED ownership.
- This ratifies **ownership of the closure duty only** — it does **not** ratify any values and does **not**
  authorize any Phase 5 runtime change now.

---

## 6. Closure Mechanism Decision — **RATIFIED: M3 (planning-doc contract → future runtime lock)**

- **Decision:** the governing mechanism is **M3** — an authoritative planning/charter doc **ratifies the closed
  set first**, then a **later, separately authorized Phase 5 runtime slice locks/enforces it**.
- **Status:** **RATIFIED** as the governing *policy and sequencing*. **M4 (open free-form string) is explicitly
  rejected** — the field will be closed, not left open.
- **Relationship to M1/M2:** the eventual runtime lock will most naturally take an **M1-style closed-set
  constant** enforced by an **M2-style factory membership check** with fail-fast. M3 governs the *sequencing*
  (doc-ratifies-values → runtime-enforces); the exact M1-vs-M2 runtime representation is deferred to that future
  runtime slice and is **not** chosen here. No values, no runtime, are defined by selecting M3.

---

## 7. Rationale — Ownership

- **Architectural argument:** the consumer/interpreter of a field is the natural owner of its closed domain;
  `cost_component_type` is consumed and interpreted in the Phase 5 cost path, so Phase 5 is the field's home and
  the only layer positioned to give it meaning.
- **By elimination:** B2 (carrier-only) and B3 (router-only) are constitutionally barred from owning or
  inventing the vocabulary; no other layer touches the field. Ownership therefore falls to Phase 5.
- **Preference honored:** the decision inputs prefer Phase 5 ownership where justifiable from the fact that
  Phase 5 consumes/interprets the field — which is exactly the justification above. The prior "not repo-proven"
  caveat concerned whether Phase 5 had *exercised* closure; **the right/duty to close** is established here by
  architecture + elimination, independent of any values.

---

## 8. Rationale — Mechanism

- **Closed over open:** the inputs prefer a closed mechanism over a free-form string and instruct that unknown
  values should block *values*, not force an open-string *policy*. M4 is therefore rejected; the set will be
  closed.
- **Why M3 specifically:** the project is charter-first — values must be ratified in an authoritative document
  **before** any runtime enforces them. M3 is the only mechanism that (a) commits to closure, (b) requires no
  values now, and (c) honors doc-before-runtime sequencing. M1/M2 alone would presuppose readiness to encode a
  set (values are still BLOCKED), and selecting them now would pre-commit the runtime form prematurely.
- **Not by convenience:** M3 is chosen on the constitution's charter-first discipline and the still-blocked
  value space — not for ease. It keeps the runtime representation decision (M1 vs M2) properly deferred.

---

## 9. Value-Space Ban (preserved)

No vocabulary value is defined, proposed, selected, or endorsed. `TAKER_FEE`, `MAKER_REBATE`, `fee`, `rebate`,
`spread`, `slippage`, `gas`, `funding`, and any other token are **not** endorsed as values. No illustrative
enum-with-values appears. All future values remain **opaque / placeheld**, to be ratified only by a future
authoritative values charter under the M3 mechanism.

---

## 10. Downstream Blocked State (unchanged)

- **Vocabulary value ratification:** remains **BLOCKED** (owner + mechanism now decided; values still
  undefined).
- **B2 cost-type carrier:** remains **BLOCKED** (behind the values ratification).
- **Master B3 wiring:** remains **BLOCKED** (Cell 3 unresolved; `edge_direction` / `staleness_threshold_ms`
  remain separate, out-of-scope blockers).

Deciding owner + mechanism unblocks **nothing executable** — it only enables a future values charter to be
authored under a settled owner and mechanism.

---

## 11. Still-Forbidden Work

- **No** vocabulary values defined/proposed/endorsed; **no** fixture/prose promotion; **no** illustrative
  values.
- **No** Phase 5 validation runtime designed/implemented (M3's runtime lock is a future, separate slice).
- **No** B2 carrier field designed/named/typed/implemented.
- **No** Master B3 runtime/design/wiring; **no** Phase 5 integration; **no** B4 scoring; **no** durable logs;
  **no** output carrier; **no** Shadow Intent; **no** live adapter.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.
- **No** touching of `edge_direction` or `staleness_threshold_ms`.

---

## 12. Next Safe Step

- A **separate review** to decide whether to authorize a **docs-only cost-component vocabulary *values*
  charter** — now bounded by a **settled owner (Phase 5)** and a **settled mechanism (M3)** — which would, for
  the first time, ratify the actual allowed values from an authoritative source.
- Only after the values are ratified may a B2 cost-type carrier amendment be chartered; only after that may
  Master B3 wiring be chartered.
- **No implementation is authorized by this charter.** The M3 runtime lock, B2 carrier, Master B3 wiring, B4
  scoring, durable logs, the live adapter, Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x
  remain separately gated.
