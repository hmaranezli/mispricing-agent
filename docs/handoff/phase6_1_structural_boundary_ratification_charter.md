# Phase 6.1 Structural Boundary Ratification Charter

> **This is a planning/charter document only.** It records human ratification of the two structural
> decisions raised by `docs/handoff/phase6_1_structural_boundary_resolution_charter.md`, while keeping
> **all implementation and schema work blocked**. It authorizes NO runtime, NO tests, NO B2 schema
> extension, NO B3 wiring, NO Phase 5 runtime change, NO network calls. It is subordinate to
> `docs/handoff/phase5_to_live_canary_roadmap.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`,
> `docs/handoff/phase6_1_shadow_input_wrapper_charter.md`,
> `docs/handoff/phase6_1_live_public_read_adapter_charter.md`,
> `docs/handoff/phase6_1_b2_normalization_boundary_charter.md`,
> `docs/handoff/phase6_1_b3_phase5_wiring_charter.md`, and
> `docs/handoff/phase6_1_structural_boundary_resolution_charter.md`. Where any conflict arises, those
> govern.

**Base:** `738490af864cb14b965fd5c077c92c65c80fee15`

---

## 0. Base and Dependency Chain

| Step | Artifact | SHA |
|------|----------|-----|
| B2 replay-only normalization | `normalize_replay_snapshot_to_evidence_material` | `9cfd1c7` |
| B3 wiring charter | Phase 5 wiring planning charter (grounded mapping matrix) | `d646981` |
| Structural boundary resolution charter | two structural hard gaps recorded, blocked pending ratification | `738490a` |

The resolution charter (`738490a`) surfaced two `HUMAN_RATIFICATION_REQUIRED` hard gaps:
`edge_direction` actionability, and the Phase 5 provenance vocabulary. This charter records the human
ratification of both, **without unblocking any implementation or schema work**.

---

## 1. Ratification — `edge_direction` via Shadow Intent Envelope (Option B, conditional)

The human has ratified **Option B** from the resolution charter, under the following binding conditions:

- `edge_direction` may be supplied **only** through an explicit, typed, **per-fixture Shadow Intent
  Envelope**.
- The envelope **must carry its own provenance and its own identity**, distinct from any market datum.
- The envelope **must be separate** from B1 public reads and from B2 normalized evidence — it is a
  distinct input channel, never folded into the snapshot or the normalized material.
- **B1, B2, and B3 must never infer, compute, default, fabricate, or derive `edge_direction`.** They may
  only carry an externally-provided direction by identity, never originate one.
- **No global static dummy direction** is allowed.
- **No silent default** is allowed (absence of an envelope fails closed; it never resolves to a direction).
- Scope is **replay / shadow only**.
- **No** live, paper, trade, routing, sizing, allocation, signal, candidate, execution, or actionability
  semantics are authorized by this ratification.

**This ratification does not authorize implementation.** It authorizes only **future planning / TDD
design** for the Shadow Intent Envelope contract. Option A (re-targeting away from
`make_gross_edge_observation`) is **not** selected; Option B governs.

---

## 2. Ratification — Phase 5 external-market replay provenance amendment requirement

The human has ratified the **requirement** (not the implementation) that:

- Phase 5 **must receive a formal external-market replay provenance contract amendment** before any B2
  schema extension or B3 implementation may proceed.
- **B2/B3 must not fabricate** `source_contract`, `source_sha256` / `parser_version` / `verifier_result`
  provenance fields, or any internal planning-artifact record identity, to pass the Phase 5 provenance
  gate.
- Public-market replay provenance **must be admitted explicitly by a Phase 5-side contract**, never
  spoofed by B2 or B3.

**This ratification does not modify Phase 5 runtime.** It authorizes only **future docs / TDD planning**
for the amendment. No `phase5/*.py` change is authorized here.

---

## 3. B2 Schema Extension — Remains Blocked

B2 schema extension **remains blocked** until **both** of the following planning steps are completed:

- **(a)** Shadow Intent Envelope contract **planning** is completed; and
- **(b)** Phase 5 external-market replay provenance amendment **planning** is completed.

Until both are complete, **do not add** any of: `base_asset`, `quote_asset`, `venue_scope`,
`venue_buy`, `venue_sell`, `observed_at_epoch_ms`, `instrument_id`, binding `role`/`kind`,
`zero_cost_evidence`, or depth-source carriage. No B2 or B1 schema field may be added yet.

---

## 4. B3 Implementation — Remains Blocked

- **No B3 mapping amendment and no B3 TDD implementation** is authorized by this charter.
- B3 remains **planning-only** until the Shadow Intent Envelope contract and the Phase 5 external-market
  replay provenance amendment are **separately chartered and reviewed**.

---

## 5. Capacity Invariant

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS
token exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and
must never be read as "capacity validated."

---

## 6. Future Next Steps

Exactly one of the following **docs-only** planning charters may be authored next (either may go first;
neither authorizes runtime, schema, or tests):

- a **docs-only Shadow Intent Envelope contract planning charter** — scoping the typed per-fixture
  envelope, its provenance/identity, and its replay/shadow-only boundaries; **no** direction inference,
  default, or computation; or
- a **docs-only Phase 5 external-market replay provenance amendment charter** — scoping how Phase 5
  legitimately admits public-market replay provenance without B2/B3 spoofing.

**No runtime, schema, or test implementation is authorized.** Each next charter is planning-only and
subject to separate review.

---

## 7. Planning-Only Authority

- This charter authorizes **no implementation** — no runtime, no tests, no schema change, no Phase 5
  runtime change, no network.
- It records ratification of the **direction-sourcing architecture (Option B, conditional)** and the
  **Phase 5 provenance amendment requirement**, and keeps **all B2 schema and B3 implementation work
  blocked** pending the two future planning charters named in §6.
- B1 adapter implementation, Phase 6.2 calibration, and 7.x/8.x remain separately gated.
