# Phase 6.1 Next-Boundary Decision Review Charter

> **This is a docs-only decision/review charter.** It pauses after the ratified minimal B3
> identity/provenance pass-through to decide the next boundary **before** authorizing any output-shape,
> Phase 5, or downstream runtime work. It authorizes NO runtime, NO tests, NO lock-test edits, NO
> B1/B2/B3/Phase 5/Shadow Intent runtime change, NO output-carrier design, NO Phase 5 integration design, NO
> pytest, NO graphify update, NO network/API/env/secret access. It is subordinate to `CLAUDE.md` and the prior
> Phase 6.1 charters; where any conflict arises, those govern.

**Base:** `2159c6ffa96db410d8aa25aa9a15750f1187ea17`

---

## 1. Base / Dependency Chain

**Base commit:** `2159c6ffa96db410d8aa25aa9a15750f1187ea17`.

References:

- `docs/handoff/phase6_1_b3_depth_evidence_mapping_runtime_closeout_ratification.md` — ratified the minimal
  B3 runtime.
- `docs/handoff/phase6_1_b3_depth_evidence_mapping_tdd_slice_charter.md` — governed the B3 first runtime slice.
- `docs/handoff/phase6_1_b3_depth_evidence_mapping_boundary_charter.md` — the B3 negative-boundary charter.
- `docs/handoff/phase6_1_depth_evidence_replay_chain_closeout_ratification.md` — the ratified replay-only
  depth evidence chain.

**This document authorizes no executable work.** It is a decision record only.

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Current Ratified State

- The replay-only depth evidence chain is **complete**.
- The B3 minimal identity/provenance pass-through is **complete**.
- Exactly **one** B3 module / **one** public function.
- **No** imports / classes / dataclasses / output carrier / state / IO.
- B3 returns `material.depth_source_reference` exactly as-is, or `None`.
- Phase 5, Shadow Intent, live reads, and capacity activation remain **blocked**.

---

## 3. Decision Problem

The open question, stated explicitly:

> **Can the current B3 identity pass-through satisfy the next downstream boundary without introducing a B3
> output carrier? Or is a separate output-shape charter required before any Phase 5 integration?**

This review does not answer it — it frames the options and the analysis required before either is chosen.

---

## 4. Option A — Output-Shape Charter (possible future docs-only path)

- Described **only** as a possible future docs-only path; nothing is authorized here.
- Risks to weigh before ever authoring it:
  - double normalization (re-shaping evidence already normalized by B2);
  - schema drift (a new shape diverging from B1/B2 contracts);
  - carrier proliferation (yet another carrier to maintain and lock);
  - accidental Phase 5 coupling (a shape that presumes a Phase 5 sink);
  - actionability leakage (a shape that smuggles in decision semantics).
- **No output-shape design is authorized here.**

---

## 5. Option B — Phase 5 Integration Boundary Charter (possible future docs-only path)

- Described **only** as a possible future docs-only path; nothing is authorized here.
- Risks to weigh before ever authoring it:
  - actionability/capacity coupling;
  - `PassiveShadowInput` / `ShadowObservation` / `NetEdge` construction pressure;
  - `capacity_pass_reference` misuse (being read as "capacity validated");
  - routing/sizing/scoring semantic leakage.
- **No Phase 5 design or integration is authorized here.**

---

## 6. Option C — Pause / Decision Review (current preferred posture)

- Ratify the **pause** as the current preferred posture unless future evidence says otherwise.
- Require a **Phase 5 interface gap analysis** before choosing A or B.
- Preserve the current **low-entropy B3 runtime** (identity pass-through only).

---

## 7. Required Future Analysis Before Choosing A or B

1. **Phase 5 interface sink requirement** — does Phase 5 require a *new* B3 output carrier, or can it consume
   existing B2/B3 identity-reference semantics later?
2. **Contract interface gap** — what *exact* object/protocol would a downstream boundary need?
3. **Provenance continuity** — can identity/provenance be preserved without copying or transforming?
4. **Non-actionability** — can the next boundary avoid capacity/actionability semantics entirely?
5. **Output-shape necessity** — prove necessity **before** authoring any output carrier (no speculative
   carriers).

---

## 8. Hard No-Claims

- **No** output carrier authorized.
- **No** Phase 5 integration authorized.
- **No** Shadow Intent authorized.
- **No** live reads authorized.
- **No** capacity activation authorized.
- **No** actionability/sizing/routing/scoring/trading/candidate/verdict authorized.
- **No** B3 runtime expansion authorized.

---

## 9. Invariants to Preserve

- B3 remains **identity pass-through only**.
- **No** subfield inspection.
- **No** numeric parsing/coercion.
- **No** IO.
- **No** imports.
- **No** state.
- **No** carrier construction.
- **No** `capacity_pass_reference` population.
- Missing depth remains `None`.
- `CapacityConstraintGate` remains deferred / non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred.

---

## 10. Next Safe Step

- A **separate review** to choose exactly one of:
  - **(a)** a docs-only Phase 5 interface gap analysis,
  - **(b)** a docs-only output-shape necessity charter,
  - **(c)** a continued pause / no next boundary selected.
- **No implementation is authorized by this decision review.** Output-carrier design, Phase 5 integration,
  Shadow Intent Envelope, live reads, capacity activation, Phase 6.2 calibration, and 7.x/8.x remain
  separately gated.
