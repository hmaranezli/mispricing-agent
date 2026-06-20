# Phase 6.1 Phase 5 Cost-Component Vocabulary Values Charter

> **This is a docs-only ratification-attempt charter.** Under the already-ratified **owner (Phase 5)** and
> **mechanism (M3)**, it attempts to ratify the closed allowed `cost_component_type` value set — and, finding the
> evidence insufficient, **returns BLOCKED**. It authorizes NO runtime, NO tests, NO lock-test edits, NO Phase 5
> runtime amendment, NO B2 runtime/schema/carrier amendment, NO Master B3 wiring, NO Phase 5 integration, NO B4
> scoring, NO durable logs, NO `edge_direction`, NO `staleness_threshold_ms`, NO Shadow Intent, NO capacity
> activation, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_phase5_cost_component_vocabulary_ownership_mechanism_decision_charter.md` and the prior
> cost-vocabulary charters; where any conflict arises, those and `CLAUDE.md` govern.

**Base:** `0e26dd9746bab8e6f013c5bcb679a04b60443089`

---

## 1. Base / Dependency Chain

**Base commit:** `0e26dd9746bab8e6f013c5bcb679a04b60443089`.

References:

- `docs/handoff/phase6_1_phase5_cost_component_vocabulary_ownership_mechanism_decision_charter.md` — ratified
  **owner = Phase 5** and **mechanism = M3** (authoritative doc ratifies the closed set → later runtime lock).
- `docs/handoff/phase6_1_phase5_cost_component_vocabulary_decision_charter.md` — framed the ownership/mechanism
  decision and the value-space ban.
- `docs/handoff/phase6_1_cost_component_vocabulary_ratification_charter.md` — vocabulary BLOCKED.
- `docs/handoff/phase6_1_cost_component_vocabulary_b2_carrier_amendment_charter.md` — B2 carrier BLOCKED.
- `docs/handoff/phase6_1_b3_mapping_extraction_ratification_charter.md` — Cell 3 BLOCKED.

**No capacity validation and no capacity pass is claimed by this charter** (see §12).

---

## 2. Why This Values Charter Exists (under M3)

M3 requires an authoritative document to ratify the closed `cost_component_type` set **before** any runtime
lock. This charter is that attempt. It ratifies values **only** if a closed set can be defended from
authoritative evidence and survives the Red-Team locks (no fallback, mutual exclusivity, definable polarity, no
actionability/unit/venue leakage). If not, it must — and does — return **BLOCKED**.

---

## 3. Evidence Inventory Inspected (read-only)

- **Phase 5 runtime — cost observation:** `make_observable_cost_observation` validates `cost_component_type`
  **only** as an exact non-empty string. No closed allowed-set anywhere in `phase5/`.
- **Phase 5 runtime — net-edge calculator (the downstream consumer):** computes
  `net_edge = gross_edge - sum(cost_i)` over **signed decimal magnitudes**; it validates
  `gross_edge_value`/`total_cost_value`/`net_edge_value` as canonical decimals and **never reads, branches on,
  or interprets `cost_component_type`**. The cost-type label is **not semantically consumed** by Phase 5 — only
  the signed magnitude is.
- **Phase 5 planning docs:**
  - cost-friction planning — defers only the **unit/scale** vocabulary; explicitly *not* a fee-schedule parser;
    defines no cost-type set.
  - source-result adapter planning — defers a **source-result state** vocabulary; no cost-type set.
  - net-edge calculator planning — pins a **proportional UNIT** vocabulary (`BPS`, `BASIS_POINTS`, `RATE`,
    `PERCENT`, `PERCENTAGE`); this is **unit/scale**, explicitly **not** `cost_component_type` values.
- **Tests:** the only `cost_component_type` literals are `TAKER_FEE` (6×) and `MAKER_REBATE` (3×) — fixtures.
- **B2:** no cost-type carrier field exists.

---

## 4. Candidate Evidence Table

| Candidate (literal/concept) | Source | Source classification | Evidence strength | Can support ratification? |
|---|---|---|---|---|
| `TAKER_FEE` | Phase 5 tests | test fixture only | **weak** | **No** — fixtures cannot alone authorize |
| `MAKER_REBATE` | Phase 5 tests | test fixture only | **weak** | **No** — fixtures cannot alone authorize |
| `BPS`/`RATE`/`PERCENT`/… | net-edge planning doc | planning prose (UNIT/scale) | n/a | **No** — these are **unit** vocabulary, not cost-type values; out of scope |
| any closed cost-type set | Phase 5 runtime | — | **absent** | **No** — no authoritative closed set exists |
| (cost-type semantic consumption) | net-edge calculator | runtime behavior | n/a | **No** — Phase 5 never interprets the label; signed magnitude carries the economics |

No row provides an authoritative basis for a closed value set.

---

## 5. Proposed Closed Value Set OR Blocked Verdict — **BLOCKED**

**No closed allowed value set is proposed or ratified.** No authoritative source defines one; the only
candidates are fixtures (weak, non-authoritative); and the consumer (net-edge calculator) does not interpret the
label, so even the apparent fee/rebate distinction is carried by the **value sign**, not by a cost-type label.

Per the evidence discipline ("test fixtures cannot alone authorize a value"; "planning prose cannot alone
authorize a value"; "the charter must be allowed to return BLOCKED if no authoritative closed value set can be
defended"), the verdict is **BLOCKED**.

---

## 6. Per-Value Justification — Not Reached (BLOCKED)

Because the verdict is BLOCKED, **no value** is carried into the per-value bar (definition / inclusion rationale
/ exclusion boundary / semantic polarity / mutual-exclusivity proof / evidence source). For completeness, the
fixture candidates fail that bar as follows:

- **`TAKER_FEE` / `MAKER_REBATE`:** **no authoritative evidence source** (fixtures only); **polarity is not
  label-defined** — fee-vs-rebate sign is carried by `signed_decimal_value`, so per-label polarity cannot be
  stated without runtime/branch design (forbidden); **mutual exclusivity is unprovable** against an undefined
  taxonomy (e.g. whether a future `*_SLIPPAGE`/`*_SPREAD` partition would overlap is unknown). They are
  therefore **rejected as authorities**, not ratified.

---

## 7. Explicit Forbidden Fallback Values

The following catch-all/fallback values are **forbidden** in any future closed set: `OTHER`, `UNKNOWN`,
`UNSPECIFIED`, `MISC`, `GENERIC`, `CUSTOM`, `RAW`, `UNCLASSIFIED`, and any other garbage-bin/catch-all token. A
closed set must be exact; an unclear or unrecognized cost must be **rejected/deferred (fail-fast)**, never
bucketed into a fallback.

---

## 8. Unresolved / Rejected Candidates

- **`TAKER_FEE`** — REJECTED as an authority (fixture-only; fails §6 bar). Not ratified.
- **`MAKER_REBATE`** — REJECTED as an authority (fixture-only; fails §6 bar). Not ratified.
- **Unit/scale labels** (`BPS`, `RATE`, `PERCENT`, …) — OUT OF SCOPE (unit vocabulary, not cost-type).
- **Whether a closed cost-type vocabulary is needed by Phase 5 at all** — UNRESOLVED. Red-Team finding: the
  net-edge calculator does not interpret `cost_component_type`; the label may be **passive provenance metadata**
  rather than a semantically consumed contract. This necessity question is flagged for the next step; it is
  **not** resolved here and does **not** re-open the ratified owner/mechanism decision.

---

## 9. Verdict — Vocabulary Values **BLOCKED**

The cost-component vocabulary **values remain BLOCKED**. No closed allowed set is ratified.

---

## 10. B2 Carrier Remains Blocked

The B2 cost-type carrier amendment **remains BLOCKED** — it cannot be chartered until an authoritative closed
value set is ratified (which has not occurred).

---

## 11. Master B3 Remains Blocked

**Master B3 wiring remains BLOCKED.** Cell 3 stays unresolved (no ratified vocabulary), and `edge_direction` /
`staleness_threshold_ms` remain separate, out-of-scope blockers.

---

## 12. Still-Forbidden Work

- **No** value defined/proposed/ratified; **no** fixture/prose promotion; **no** fallback value.
- **No** Phase 5 validation runtime designed/implemented.
- **No** B2 carrier field designed/named/typed/implemented; **no** B2 unblock.
- **No** Master B3 runtime/design/wiring; **no** Phase 5 integration; **no** B4 scoring; **no** durable logs;
  **no** output carrier; **no** Shadow Intent; **no** live adapter.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.
- **No** touching of `edge_direction` or `staleness_threshold_ms`.

---

## 13. Next Safe Step

- A **separate review** to resolve the **necessity question** flagged in §8: decide (docs-only) whether Phase 5
  actually requires a *closed, semantically-consumed* `cost_component_type` vocabulary at all, **or** whether the
  label is **passive provenance metadata** (carried verbatim, economics carried by the signed magnitude). That
  necessity decision should precede any further attempt to ratify values — because if the label is passive
  metadata, a different (carrier-only, non-closed-semantic) treatment may apply, still without B2/B3 inventing
  meaning.
- Only if a closed, consumed vocabulary is shown necessary, and then ratified from an authoritative source under
  M3, may a B2 cost-type carrier amendment and subsequently Master B3 wiring be chartered.
- **No implementation is authorized by this charter.** Phase 5 vocabulary runtime, B2 carrier, Master B3 wiring,
  B4 scoring, durable logs, the live adapter, Shadow Intent Envelope, capacity activation, Phase 6.2, and
  7.x/8.x remain separately gated.
