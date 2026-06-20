# Phase 6.1 Live-Public-Read Adapter Planning Charter

> **This is a planning/charter document only.** It authorizes NO runtime implementation, NO tests, NO
> network calls. It scopes the deferred live-public-read adapter (boundary B1) and its dependencies so
> a later, separately authorized TDD slice can begin. It is subordinate to
> `docs/handoff/phase5_to_live_canary_roadmap.md`, `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`,
> and `docs/handoff/phase6_1_shadow_input_wrapper_charter.md`. Where any conflict arises, those govern.

**Base:** `ea0bf0256d6806c7c7fe1f02db484fd52b5bd458`

---

## 1. Phase 6.1 Slice 0 Closeout Status

All Slice 0 components are **complete and green** at base `ea0bf02` (targeted run: **100 passed**):

| Slice | Component | Status |
|-------|-----------|--------|
| 0A | `PassiveShadowInput` | complete |
| 0B | `ShadowObservation` | complete |
| 0C | provenance chain locks (`verify_provenance_chain`) | complete |
| 0D | forbidden-token / import / IO / source locks | complete |
| 0E | diagnostic-value non-actionability locks | complete |

The `phase6_1` runtime is passive, local, replay-first, no-IO, exact-type-only, and non-actionable;
data direction is strictly one-way (no feedback into Phase 5; no downstream action layer).

---

## 2. B1 Live-Public-Read Adapter Boundary

B1 is a **read-only fetch+freeze** step, strictly upstream of Phase 5.

- **Input:** a public, unauthenticated market-data snapshot **or** a local replay artifact.
- **Action:** retrieve, then freeze — capture the bytes/values exactly as read, tagged with
  provenance (source reference, venue, pair, retrieval epoch-ms).
- **Output:** an **immutable, provenance-tagged raw snapshot record only**.

B1 is a fetch+freeze boundary — not a normalizer, gate, scorer, or carrier factory.

---

## 3. B1 Must NOT

- instantiate `PassiveShadowInput`;
- instantiate `ShadowObservation`;
- create evidence contexts;
- normalize;
- gate;
- score;
- write output artifacts (no serializer / output sink / persistence);
- produce verdicts or actionability of any kind.

---

## 4. B2 Readiness Gap (must be scoped before B1 can feed the chain)

The **normalization boundary (B2)** — raw snapshot → Phase-5-compatible evidence input — has **no
runtime and no charter yet**. B1 alone therefore **cannot** reach `PassiveShadowInput`: the carrier's
factory requires an exact `NetEdgeCalculationResult`, which is emitted only by the Phase 5 gate's
by-identity PASS. **B2 must be separately scoped** (its own charter) before B1's output can be wired
into the Phase 6.1 chain. This charter records the gap; it does not fill it.

---

## 5. Only Admissible Future Path

The single permitted data direction into the carriers is:

```
raw snapshot (B1)
  -> normalization (B2)
  -> Phase 5 provenance / evidence / gate chain (B3)
  -> PASS NetEdgeCalculationResult
  -> PassiveShadowInput (0A)
  -> ShadowObservation (0B)
  -> provenance / non-actionability locks (0C / 0D / 0E)
```

B1 terminates at the raw snapshot. Because the carriers' exact-type guards admit only a genuine Phase
5 PASS object, no adapter output can bypass Phase 5 or the Slice 0 locks.

---

## 6. Replay-Artifact-First Mandate

- The **first** adapter TDD slice must use **local replay artifacts only** — deterministic,
  test-scoped, no network.
- **Live public reads are deferred** to a later, separately reviewed slice; they are not authorized
  here.

---

## 7. Hard Barriers

- **public-only** — public market-data routes only;
- **unauthenticated** — no auth headers, keys, signing, sessions, or login;
- **no env / secrets** — no `os.environ`/`getenv`, no secret files;
- **no private / account endpoints** — never wallet/balance/account/order endpoints;
- **endpoint allowlist required** — only allowlisted public routes may be read; reject all others;
- **no feedback into Phase 5** — the adapter never writes into Phase 5;
- **no carrier construction inside the adapter** — B1 never instantiates `PassiveShadowInput` or
  `ShadowObservation`.

---

## 8. Future TDD Proof Targets (to be written later — NOT written now)

1. **no-network replay-first test** — first slice operates on local replay artifacts; zero network.
2. **no-secret / no-env AST locks** — adapter source contains no env/secret access (extends the
   Slice 0D AST import/IO locks to the adapter module).
3. **public endpoint allowlist** — only allowlisted public routes accepted; others rejected.
4. **immutable raw snapshot / provenance carrier** — output is frozen and provenance-tagged.
5. **adapter cannot instantiate `PassiveShadowInput` / `ShadowObservation`**.
6. **adapter cannot bypass Phase 5** — no path from adapter output to the carriers except via B2 + the
   Phase 5 gate PASS.
7. **deterministic replay reproducibility** — identical artifacts yield identical snapshot records.
8. **fail-fast on authenticated / private endpoints** — any credentialed or private route raises.

---

## 9. Planning-Only Authority

- This charter authorizes **no implementation** — no runtime, no tests, no network.
- **B2 normalization**, **Phase 6.2 calibration**, **7.x paper / paper canary**, and **8.x live
  canary** remain **separately gated** and require explicit future authorization.
- The next named step is review of this charter, then — only on explicit authorization — the first
  **replay-artifact-only** adapter TDD slice. No unplanned stop.

---

## Capacity Statement

This charter claims **no capacity validation and no capacity pass**. `CapacityConstraintGate` remains
**deferred / non-activatable** with **0 emit sites**; no capacity PASS token exists, and none is
implied here, until a separately authorized capacity PASS token is created. `capacity_pass_reference`
on `PassiveShadowInput` therefore remains `None` / deferred and must never be read as "capacity
validated."
