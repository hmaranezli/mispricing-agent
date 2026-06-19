# Phase 6.1 TDD Planning Charter — Read-only Shadow Scoring

> **This is a planning/charter document only.** It authorizes NO runtime
> implementation, NO tests, NO live reads, NO paper/live trading, and NO
> wallet/order/routing/execution behavior. It prepares Phase 6.1 TDD; the first
> implementation slice requires separate explicit authorization.

**Base:** `87774ac1abdc74c3782557ba29b178139e4f3595`

---

## 1. Status and Authority

- This document is a **planning/charter only**. It produces no runtime, no tests,
  no live network reads.
- It authorizes **none** of: runtime implementation, test authoring, live/public
  reads, paper trading, live trading, wallet access, order intent, order routing,
  execution.
- It is **subordinate to** `docs/handoff/phase5_to_live_canary_roadmap.md` at
  `87774ac`. Where any conflict arises, the roadmap governs.
- It prepares **Phase 6.1 TDD only**. Implementation — including the first TDD
  slice — requires **separate explicit authorization** after this charter is
  reviewed.

---

## 2. Replay-first Mandate

- **Slice 0 must be replay-artifact-only.**
- No internet, no live public API, no private API, no authenticated endpoint, no
  wallet/balance/order endpoint, no secrets.
- The **live-public-read adapter is deferred** to a later, separately reviewed
  slice (see §8 "Later slice"). It is **not** authorized here.
- Replay fixtures/artifacts must be **deterministic, local, and test-scoped**. They
  must **not** depend on mutable runtime data (e.g. nothing under `data/output/` or
  any live-mutated path). Fixtures live with the tests and are frozen.

---

## 3. Boundary Separation

Phase 6.1 is decomposed into four distinct boundaries. Ingestion + normalization
must remain **separate** from scoring; scoring never consumes raw or normalized
material directly.

| # | Boundary | Consumes | Produces | Must NOT |
|---|----------|----------|----------|----------|
| B1 | **Read-only ingestion** | public/replay snapshot | immutable raw snapshot record + provenance only | derive evidence semantics or verdicts |
| B2 | **Normalization** | raw snapshot (B1) | Phase-5-compatible evidence *material* (with provenance) | emit a pass/halt verdict; reach scoring directly |
| B3 | **Phase 5 evidence/gate validation** | normalized evidence material (B2) | a typed **passed non-halt** result **or** a halt carrier | be bypassed or re-implemented inside Phase 6.1 |
| B4 | **Passive shadow scoring** | the **typed passed non-halt handoff** only (B3) | `ShadowObservation` / `ShadowScore` (durable, passive) | consume raw (B1) or normalized (B2) material directly; consume halt carriers |

B3 reuses the **existing** Phase 5 chain (`evaluate_input_provenance_preflight` →
evidence boundaries → `net_edge_profitability_preflight` /
`CapacityConstraintGate.preflight`). Phase 6.1 does not modify Phase 5.

---

## 4. Typed Handoff Requirement (gating all runtime planning)

- **No runtime planning may proceed until the exact Python type consumed by Shadow
  Scoring (B4) is pinned.**
- The handoff **must** be a concrete Phase-5-approved **non-halt** dataclass/result.
  It must **not** be: `dict`, `Any`, JSON, a raw snapshot, `BlockedPacket`,
  `NoEligibleHaltPacket`, any halt carrier, candidate, signal, order, or
  wallet/balance/private-account payload.
- **Candidate exact type to evaluate:** `NetEdgeCalculationResult` (the identity-pass
  output of `net_edge_profitability_preflight` on a PASS). If existing Phase 5 types
  are insufficient to carry the fields Shadow Scoring needs, then a **separately
  authorized** passive `ShadowInput` / `ShadowValidatedObservation` handoff type is
  defined — but only via Slice 0A, never ad hoc.
- This pinning is performed by **Slice 0A** (§8) if not already pinned. Until pinned,
  Slices 0B–0E remain blocked.

---

## 5. Passive Schema Naming

- **Preferred allowed names:** `ShadowObservation`, `ShadowScore`,
  `ShadowDiagnostics`, `ShadowProvenanceRef`.
- `OpportunityObservation` may be mentioned **only** as optional and **explicitly
  non-actionable**.
- **Forbidden names:** `TradeCandidate`, `Signal`, `OrderIntent`,
  `ExecutableOpportunity`, `Order`, `Route`, `Allocation`, any "actionable
  sizing"/"order quantity" identifier, `live_trade`, `paper_trade`.

---

## 6. Diagnostic EV Contract

- EV fields are **passive diagnostics only**.
- Field names **must** carry a `diagnostic_` or `passive_` prefix —
  e.g. `diagnostic_expected_value` or `passive_diagnostic_ev`.
- The EV formula may be recorded **only** as a diagnostic:

  ```
  diagnostic_expected_value = (P_success * LimitEdge) - (Fee_maker/taker + Slippage_estimated)
  ```

- EV must **not** imply actionability, recommendation, readiness, order intent,
  signal, candidate, route, allocation, or execution. It is an observability number
  for later (Phase 6.2) calibration only.

---

## 7. Forbidden Runtime Set and Fail-fast Policy

**Forbidden tokens/objects:** `wallet`, `balance`, `private account`, `api secret`,
`order intent` / `order`, `routing` / `route`, `execution` / `execute`,
`allocation`, actionable sizing, `TradeCandidate`, `Signal`, `live trade`,
`paper trade`.

- If any such object is supplied to a future Phase 6.1 entrypoint, the entrypoint
  **must fail fast** (no truthiness, no coercion, no silent pass-through).
- A dedicated **`ShadowActionabilityViolationError`** may be planned **only** for
  forbidden actionability/security violations (e.g. an order/candidate/signal/wallet
  object reaching a shadow entrypoint).
- **Do NOT** use `ShadowActionabilityViolationError` for stale/missing/malformed
  *normal* evidence. Those remain handled by the **existing fail-closed/blocked
  semantics** of the Phase 5 chain (`BlockedPacket` / `NoEligibleHaltPacket` and the
  existing `…TypeError` / `MisroutedHaltCarrierError` families). Phase 6.1 inherits,
  never bypasses, those guards.

---

## 8. TDD Slice Plan (ordered, replay-first)

| Slice | Name | Planning purpose | Blocked until |
|-------|------|------------------|---------------|
| **0A** | Typed handoff extraction/decision | Pin the exact B3→B4 handoff type (§4) if not already pinned | — |
| **0B** | Passive replay-artifact schema / `ShadowObservation` carrier | Plan the durable passive shadow artifact + field set | 0A pinned |
| **0C** | Provenance chain locks | Plan locks: replay snapshot → normalized evidence → Phase 5 gate → shadow observation | 0B |
| **0D** | Forbidden-token AST/source locks + actionability fail-fast | Plan structural bans and `ShadowActionabilityViolationError` fail-fast | 0C |
| **0E** | Diagnostic EV non-actionability | Plan EV-as-diagnostic-only contract proof | 0D |
| **Later** | Live-public-read adapter | **Deferred. Separately reviewed. NOT authorized here.** | separate authorization |

All Slice-0 work is replay-artifact-only (§2). Each slice is implemented only after
this charter is reviewed and that slice is separately authorized.

---

## 9. TDD Proof Targets (to be written later — NOT written now)

1. **Passive logging/schema test** — durable passive shadow artifact produced.
2. **Replay-first no-network test** — no internet / live / private / authenticated /
   wallet-balance-order endpoint calls.
3. **Typed handoff exact-type test** — B4 accepts only the pinned exact non-halt
   type; rejects dict/Any/JSON/raw/halt-carrier.
4. **Blocked/halt input rejection test** — `BlockedPacket`/`NoEligibleHaltPacket`/
   halt carriers cannot become scored observations.
5. **Actionability object fail-fast test** — order/candidate/signal/wallet object
   raises `ShadowActionabilityViolationError`.
6. **Forbidden-token AST/source lock** — no forbidden identifiers in Phase 6.1
   runtime except inside the explicit forbidden-list tests.
7. **Diagnostic EV non-actionability test** — EV lives only in passive log/schema,
   not interpretable as a recommendation/order.
8. **Provenance traceability test** — every shadow observation points back to source
   artifact/public snapshot, normalized evidence, and the Phase 5 gate/provenance
   chain.

---

## 10. Roadmap Consistency

- **Phase 6.2** (calibration), **7.1** (paper simulator), **7.2** (paper canary),
  and **8.1** (live canary) remain **separately gated** per the roadmap §2/§6.
- **No downstream readiness is implied** by this charter.
- **No unplanned stop:** the next named step after this planning charter is
  **Phase 6.1 TDD planning review**, then a **separately authorized first TDD slice
  (Slice 0A)**. Work begins only on passing the documented gate and receiving
  explicit user authorization for that slice.
