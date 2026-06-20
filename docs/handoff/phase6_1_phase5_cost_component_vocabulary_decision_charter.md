# Phase 6.1 Phase 5 Cost-Component Vocabulary Decision Charter

> **This is a docs-only decision/framing charter.** It frames the *ownership* and *closure* decision for
> `cost_component_type` **without inventing or ratifying any vocabulary**. It authorizes NO runtime, NO tests,
> NO lock-test edits, NO Phase 5 runtime amendment, NO B2 runtime/schema/carrier amendment, NO Master B3
> wiring, NO Phase 5 integration, NO B4 scoring, NO durable logs, NO `edge_direction`, NO
> `staleness_threshold_ms`, NO Shadow Intent, NO capacity activation, NO Phase 6.2 work, NO pytest, NO
> graphify. It is subordinate to
> `docs/handoff/phase6_1_cost_component_vocabulary_ratification_charter.md`,
> `docs/handoff/phase6_1_cost_component_vocabulary_b2_carrier_amendment_charter.md`,
> `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md`,
> `docs/handoff/phase6_1_completion_sequencing_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `76bc094388a6570e424683875fe4286d99a8b47f`

---

## 1. Base / Dependency Chain

**Base commit:** `76bc094388a6570e424683875fe4286d99a8b47f`.

References:

- `docs/handoff/phase6_1_cost_component_vocabulary_ratification_charter.md` — swept the repo and found **no**
  closed authoritative vocabulary; left vocabulary **BLOCKED** and ownership **UNRESOLVED**.
- `docs/handoff/phase6_1_cost_component_vocabulary_b2_carrier_amendment_charter.md` — split the cost-vocabulary
  gap out; kept the B2 carrier **BLOCKED** behind vocabulary ratification.
- `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md` — kept Cell 3 **BLOCKED**.
- `docs/handoff/phase6_1_completion_sequencing_charter.md` — places this on the Master-B3 critical path.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Why This Decision Charter Exists

The vocabulary-ratification sweep proved nothing can be ratified from current evidence, and that the **ownership
question** — *which layer is entitled to close the `cost_component_type` set* — is itself unresolved. Resolving
ownership is logically prior to closing any set: a vocabulary cannot be ratified until it is decided **who** may
ratify it. This charter frames that ownership/closure decision and the closure **mechanism options** —
**without proposing any values** — so the decision is governed rather than guessed.

---

## 3. Current Evidence State (carried forward, unchanged)

- **Vocabulary:** BLOCKED — no closed authoritative repo-evidenced allowed-set exists.
- **Ownership:** UNRESOLVED — no layer is repo-proven to own *closing* the set.
- **B2 carrier:** BLOCKED — behind vocabulary ratification; no carrier field designed.
- **Master B3:** BLOCKED — Cell 3 unresolved (and `edge_direction` / `staleness_threshold_ms` remain separate,
  out-of-scope blockers).

---

## 4. Ownership Framing (evidence vs. argument vs. unresolved)

Three layers are distinguished; this charter does **not** assign final ownership by preference.

- **Phase 5 — candidate owner (architectural argument, not yet repo-proven).** `cost_component_type` is a
  parameter of the Phase 5 `make_observable_cost_observation` factory and is consumed/interpreted within the
  Phase 5 cost path. *Evidence:* the field's home is Phase 5. *Argument:* the consumer/interpreter of a field is
  the natural owner of its closed domain. *Caveat:* Phase 5 currently leaves the field open and its planning doc
  declines to close it — so Phase 5 **ownership of closure is not repo-proven**, only architecturally plausible.
- **B2 — must remain carrier-only.** B2 may, at most, *carry* a cost-type value verbatim once a vocabulary and
  carrier are separately ratified. B2 must **never** define, close, or default the vocabulary.
- **B3 — must remain router-only.** B3 may, at most, *route* a carried value into Phase 5. B3 must **never**
  derive, infer, or invent the vocabulary (no `normalized_field_name → cost_component_type` rule).
- **Final ownership status: UNRESOLVED.** Because Phase 5 closure ownership is not repo-proven, this charter
  keeps final ownership unresolved and records Phase 5 only as the evidence-consistent *candidate*.

---

## 5. No-Vocabulary-Proposal Rule

This charter must **not** define the allowed values, and **must not** propose an initial closed set as "the
answer," because:

- A repo with no authoritative set means any proposal here would be an **invention**, not a ratification.
- Proposing even a "starter set" risks **anchoring** the future decision to an unratified guess.
- The only literals in the repo (`TAKER_FEE`, `MAKER_REBATE`) are **test fixtures** and are explicitly **not**
  promoted to contract; the planning-doc labels (`bps`, `fee_rate`, `spread_bps`, …) are **unit/scale**
  examples, not cost-type values, and are **not** endorsed here.

Deciding *who owns* and *by what mechanism* the set is closed is in scope; deciding *what the set is* is not.

---

## 6. Closure Mechanism Options (mechanisms only — NO values chosen)

Recorded as the option space for a future decision; **none is selected**, and none lists values.

- **(M1) Phase 5 enum/constant/`frozenset`** — Phase 5 declares a closed allowed-set constant that the cost
  factory checks membership against. (Mechanism only; the set's contents are not defined here.)
- **(M2) Phase 5 factory validation** — `make_observable_cost_observation` adds a fail-fast membership check
  against a ratified set (whose contents are decided separately).
- **(M3) Planning-doc contract + future runtime lock** — an authoritative planning/charter doc ratifies the set
  first, then a later runtime slice enforces it (doc-then-lock sequencing).
- **(M4) Deferred / no closed set** — explicitly keep `cost_component_type` an open free-form string for now,
  accepting that Master B3 cost mapping stays blocked until a set is closed.

Each option has trade-offs (rigidity vs. flexibility, doc-vs-runtime authority, blast radius on Phase 5). This
charter does **not** weigh or choose among them.

---

## 7. Required Future Proof Before Any Vocabulary Can Be Ratified

1. **Ownership resolved** — a repo-evidenced decision naming the layer entitled to close the set (Phase 5 the
   candidate, but only once proven/ratified).
2. **Authoritative closed set** — the exact allowed values, ratified from an authoritative source (a ratified
   Phase 5 charter/decision, or a Phase 5 runtime amendment that defines+enforces it). Test fixtures do not
   qualify.
3. **Closure mechanism chosen** — one of M1–M4 (or another evidence-justified mechanism) explicitly selected.
4. **Fail-fast semantics** — once closed, out-of-set values fail fast (no silent pass-through).

---

## 8. Required Future Proof Before Any B2 Cost-Type Carrier Amendment

- **Only after §7 is satisfied.** Then: an **explicit, non-derived** B2 carrier (field name/type designed
  separately), proven supplied by the artifact and **never** inferred from `normalized_field_name`,
  `source_field`, unit, magnitude, or tuple position; carried verbatim, with no actionability/scoring.

---

## 9. Required Future Proof Before Master B3 Wiring Can Be Reconsidered

- **Only after §7 and §8.** Then Master B3 may map `cost_component_type` by **identity pass-through** of the
  ratified, carried value into Phase 5 — never by derivation — **and** the separate `edge_direction` /
  `staleness_threshold_ms` blockers must each be independently resolved.

---

## 10. Risks If Guessed

- **Fixture-to-contract leakage** — promoting `TAKER_FEE` / `MAKER_REBATE` (test data) into a runtime contract.
- **Schema drift** — a guessed set diverging from whatever Phase 5 actually needs, requiring later breaking
  changes.
- **Bottom-up schema poisoning** — letting B2/B3 (carrier/router layers) implicitly define a vocabulary that
  only Phase 5 is entitled to close.
- **B3 semantic inference** — a `normalized_field_name → cost_component_type` derivation makes B3 a meaning
  inventor.
- **Hidden scoring/actionability leakage** — a guessed cost taxonomy smuggling in fee/slippage modeling, sizing,
  or scoring semantics that Phase 6.1 forbids.

---

## 11. Still-Forbidden Work

- **No** vocabulary values defined, proposed, or endorsed; **no** fixture promotion; **no** example values
  endorsed.
- **No** ownership assigned by preference (only evidence/argument/unresolved are distinguished).
- **No** Phase 5 validation runtime designed/implemented.
- **No** B2 carrier field designed/named/typed/implemented.
- **No** Master B3 runtime/design/wiring; **no** Phase 5 integration; **no** B4 scoring; **no** durable logs;
  **no** output carrier; **no** Shadow Intent; **no** live adapter.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.
- **No** touching of `edge_direction` or `staleness_threshold_ms`.

---

## 12. Next Safe Step

- A **separate review** to make the **ownership decision** (resolve whether Phase 5 owns closing the
  `cost_component_type` set) and to **select a closure mechanism** (M1–M4) — still **without** defining values.
- Only after ownership + mechanism are decided may a vocabulary-values charter be authorized; then a B2 carrier
  amendment; then Master B3 wiring.
- **No implementation is authorized by this charter.** Phase 5 vocabulary runtime, B2 carrier, Master B3
  wiring, B4 scoring, durable logs, the live adapter, Shadow Intent Envelope, capacity activation, Phase 6.2,
  and 7.x/8.x remain separately gated.
