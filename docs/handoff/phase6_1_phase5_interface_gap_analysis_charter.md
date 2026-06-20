# Phase 6.1 Phase 5 Interface Gap Analysis Charter

> **This is a docs-only gap-analysis planning charter.** It defines a *future* read-only analysis of Phase 5
> passive/shadow interface requirements **before** any B3 output carrier or Phase 5 integration is designed.
> It authorizes NO runtime, NO tests, NO lock-test edits, NO B1/B2/B3/Phase 5/Shadow Intent runtime change, NO
> output-carrier design, NO Phase 5 integration design, NO pytest, NO graphify update, NO network/API/env/
> secret access.
>
> **This is NOT an integration charter. This is NOT an output-shape charter. This is NOT a Phase 5 runtime
> authorization.** It is only a boundary/gap-analysis planning document. It is subordinate to `CLAUDE.md` and
> the prior Phase 6.1 charters; where any conflict arises, those govern.

**Base:** `d5037048e5c3684e61169255d236d33d86499126`

---

## 1. Base / Dependency Chain

**Base commit:** `d5037048e5c3684e61169255d236d33d86499126`.

References:

- `docs/handoff/phase6_1_next_boundary_decision_review.md` — the decision review that framed this gap analysis
  as a prerequisite to choosing the next boundary.
- `docs/handoff/phase6_1_b3_depth_evidence_mapping_runtime_closeout_ratification.md` — ratified the minimal B3
  identity/provenance pass-through.
- `docs/handoff/phase6_1_depth_evidence_replay_chain_closeout_ratification.md` — the ratified replay-only depth
  evidence chain.

**This charter authorizes no executable work.**

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Problem Statement

- **Output-shape design is premature** until Phase 5 sink/interface requirements are understood.
- **Phase 5 integration is premature** until the interface gap is characterized.
- The analysis must determine whether a B3 output carrier is **necessary or avoidable**.

The governing question:

> Can the current B3 identity/provenance pass-through — which returns B2 `material.depth_source_reference`
> exactly as-is or `None` — satisfy any future Phase 5 passive/shadow boundary **without** introducing a new
> B3 output carrier?

---

## 3. Gap-Analysis Scope

- **Docs-only / read-only** orientation over existing Phase 5 passive/shadow entry points.
- Candidate concepts may include `PassiveShadowInput`, `ShadowObservation`, `NetEdgeCalculationResult`, or
  existing Phase 5 passive/shadow contracts **only as interface objects to inspect** — never to modify,
  construct, import-wire, or run.
- **No** modification, construction, import wiring, or runtime use is authorized.
- Actionability modules — sizing / routing / execution / live / order / trade / candidate / signal paths — are
  **out of scope**.

---

## 4. Key Questions the Future Analysis Must Answer

1. What exact Phase 5 passive/shadow **sink interfaces** currently exist?
2. What **inputs/types** do they require?
3. Do they require a **new B3 output carrier**, or can existing B2/B3 identity-reference semantics be
   sufficient?
4. Can `PublicDepthSourceRecord` identity/provenance **survive without copying or wrapping**?
5. Is depth evidence **required by Phase 5 at all**, or should it remain deferred?
6. Would any output-shape introduce **double normalization, schema drift, or carrier proliferation**?

---

## 5. No-Output-Carrier Default

- The default posture remains: **no B3 output carrier**.
- Any future output carrier must **prove necessity**.
- Convenience, symmetry, or "nice architecture" is **not enough**.
- **Dead-code / carrier proliferation risk** must be explicitly considered.

---

## 6. No Integration Boundary

- **No** Phase 5 construction.
- **No** `PassiveShadowInput` construction.
- **No** `ShadowObservation` construction.
- **No** `NetEdgeCalculationResult` construction.
- **No** Phase 5 imports/wiring.
- **No** B3-to-Phase 5 call path.
- **No** Shadow Intent Envelope.
- **No** capacity activation.

---

## 7. Non-Actionability Firewall

- **No** sizing.
- **No** allocation.
- **No** routing.
- **No** execution.
- **No** order/trade/candidate/signal.
- **No** score/verdict/threshold.
- **No** capacity PASS.
- **No** `capacity_pass_reference` population.
- **No** liquidity sufficiency/insufficiency conclusion.

---

## 8. Identity / Provenance Preservation Questions

- The future analysis must check whether **identity** (`is`, `id()`) can remain sufficient.
- **No** copying, wrapping, serialization, reconstruction, backfill, or synthetic/default carrier — unless
  separately justified by a later charter.
- Missing depth remains `None`.

---

## 9. Forbidden Work

- **No** runtime.
- **No** tests.
- **No** output-shape design.
- **No** Phase 5 integration design.
- **No** live/network read.
- **No** env/secrets.
- **No** capacity activation.
- **No** actionability.
- **No** graphify.

---

## 10. Future Proof Targets (planning only — NOT performed now)

- If a future read-only gap-analysis slice is authorized, it should produce **evidence about existing Phase 5
  passive/shadow interfaces without changing them**.
- It must keep these four concerns **distinct and un-collapsed**:
  - **interface observation** (what exists);
  - **output-shape necessity** (whether a carrier is required at all);
  - **integration readiness** (whether wiring could ever be safe);
  - **actionability readiness** (explicitly deferred — not a goal of the analysis).
- These must **not** be collapsed into one step.

---

## 11. Capacity Invariant

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 12. Next Safe Step

- A **separate review** to decide whether to authorize a **read-only Phase 5 interface gap-analysis slice**.
- That future slice must inspect **only existing interface contracts** and produce a **report** — no
  modification, construction, wiring, or runtime use.
- **No implementation is authorized by this charter.** Output-carrier design, Phase 5 integration, Shadow
  Intent Envelope, live reads, capacity activation, Phase 6.2 calibration, and 7.x/8.x remain separately
  gated.
