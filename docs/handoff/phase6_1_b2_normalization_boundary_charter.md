# Phase 6.1 B2 Normalization Boundary Planning Charter

> **This is a planning/charter document only.** It authorizes NO runtime implementation, NO tests, NO
> network calls. It scopes the deferred B2 normalization boundary so a later, separately authorized TDD
> slice can begin. It is subordinate to `docs/handoff/phase5_to_live_canary_roadmap.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`,
> `docs/handoff/phase6_1_shadow_input_wrapper_charter.md`, and
> `docs/handoff/phase6_1_live_public_read_adapter_charter.md`. Where any conflict arises, those govern.

**Base:** `a12a5f5137aff70f14e3a11dec8c95078b7d45d3`

---

## 1. Dependency

The **B1 live-public-read adapter charter** exists at `a12a5f5`
(`docs/handoff/phase6_1_live_public_read_adapter_charter.md`) and defines **B1 as fetch+freeze only** —
producing an immutable, provenance-tagged raw snapshot record and nothing else.

**B2 is required** because a B1 raw snapshot **cannot reach `PassiveShadowInput` directly**: the
carrier's factory admits only an exact `NetEdgeCalculationResult`, which is emitted only by the Phase 5
gate's by-identity PASS. B2 is the step that turns a raw snapshot into the Phase-5-compatible evidence
material the Phase 5 chain consumes.

---

## 2. B2 Boundary

- **Consumes:** only an immutable, provenance-tagged **raw snapshot record** from B1 (or a local
  replay artifact of the same shape).
- **Produces:** only **Phase-5-compatible normalized evidence material**.
- **Is not:** a gate, a scorer, a carrier factory, or an output writer.

B2 reshapes and validates; it decides nothing and emits no verdict.

---

## 3. Non-Bypass Path

The single permitted data direction is:

```
B1 raw snapshot
  -> B2 normalized evidence material
  -> Phase 5 provenance / evidence / gate chain (B3)
  -> PASS NetEdgeCalculationResult
  -> PassiveShadowInput (0A)
  -> ShadowObservation (0B)
  -> Slice 0 locks (0C / 0D / 0E)
```

B2 terminates at normalized evidence material. It never reaches the carriers; only a genuine Phase 5
PASS object may, via the carriers' exact-type guards.

---

## 4. B2 Must NOT

- instantiate `PassiveShadowInput`;
- instantiate `ShadowObservation`;
- instantiate `NetEdgeCalculationResult` directly;
- call itself a Phase 5 pass;
- claim capacity validation;
- write output artifacts (no serializer / output sink / persistence);
- perform network reads;
- read env / secrets;
- produce verdict or actionability of any kind.

---

## 5. Capacity Statement

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. **No capacity
PASS token exists or is implied** by B2. `PassiveShadowInput.capacity_pass_reference` remains
`None` / deferred and must never be read as "capacity validated." A capacity PASS requires a separately
authorized capacity PASS token that does not exist yet.

---

## 6. Normalization Invariants

- **exact-type discipline only** — `type(value) is ExactType`; **no `isinstance`**;
- **no silent coercion** — never convert across types to "make it fit";
- **no default fallback values** — never substitute a default for a missing/absent field;
- **fail fast** — missing or malformed fields raise immediately;
- **timestamp fields remain UTC epoch-millisecond `int`** where applicable;
- **unit-bearing values keep magnitude and unit atomically bound** — a magnitude is never carried
  apart from its unit;
- **no magnitude comparison is valid without exact unit equality** — case-sensitive exact-token unit
  match, mirroring the Phase 5 net-edge calculator's unit policy;
- **tolerance `0` is a valid strict-match**; a **missing / `None` / negative tolerance is malformed**
  and fails fast.

---

## 7. Provenance Invariants

- every normalized field must **carry or reference**: source artifact, source field, venue, pair,
  retrieval epoch-ms, and raw snapshot identity;
- B2 must **not recompute from live data** and must **not perform any secondary lookup** — it reshapes
  the frozen B1 snapshot only.

---

## 8. Replay-First Mandate

- The **first** B2 TDD slice must use **local replay artifacts only** — deterministic, test-scoped, no
  network.
- **Live public reads remain deferred** through B1's later, separately reviewed slice; they are not
  authorized here.

---

## 9. Future TDD Proof Targets (to be written later — NOT written now)

1. **exact raw-snapshot input type guard** — B2 accepts only the exact B1 raw snapshot type.
2. **malformed / missing field fail-fast** — any missing or malformed field raises.
3. **no silent coercion** — wrong-typed inputs raise rather than convert.
4. **unit / magnitude atomicity** — magnitude and unit stay bound; magnitude alone is rejected.
5. **zero-tolerance strict-match behavior** — tolerance `0` matches exactly; missing/None/negative
   tolerance fails fast.
6. **provenance chain preservation** — every normalized field traces to source artifact/field, venue,
   pair, retrieval epoch-ms, and raw snapshot identity.
7. **no carrier construction** — B2 never instantiates `PassiveShadowInput` / `ShadowObservation` /
   `NetEdgeCalculationResult`.
8. **no Phase 5 bypass** — no path from B2 output to the carriers except via the Phase 5 gate PASS.
9. **no network / env / secret / IO** — AST + runtime locks keep B2 local and passive.
10. **deterministic replay reproducibility** — identical raw snapshots yield identical normalized
    evidence material.

---

## 10. Planning-Only Authority

- This charter authorizes **no implementation** — no runtime, no tests, no network.
- **B2 TDD implementation**, **B1 live adapter implementation**, **Phase 6.2 calibration**, **7.x
  paper / paper canary**, and **8.x live canary** remain **separately gated** and require explicit
  future authorization.
- The next named step is review of this charter, then — only on explicit authorization — the first
  **replay-artifact-only** B2 TDD slice. No unplanned stop.
