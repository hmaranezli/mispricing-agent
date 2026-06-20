# Phase 6.1 Completion Sequencing Charter

> **This is a docs-only sequencing/planning charter.** It orders the remaining Phase 6.1 critical path before
> Phase 6.2 Calibration can be considered. It authorizes NO runtime, NO tests, NO lock-test edits, NO Phase 5
> integration, NO B4 scoring runtime, NO durable log writer, NO Shadow Intent runtime/schema, NO live adapter
> runtime, NO capacity activation, NO Phase 6.2 work, NO pytest, NO graphify. **It authorizes nothing
> executable.** It is subordinate to `docs/handoff/phase5_to_live_canary_roadmap.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `7d1d13ca5109a71c7d2f2e9bab5d8d599478cfc4`

---

## 1. Base / Dependency Chain

**Base commit:** `7d1d13ca5109a71c7d2f2e9bab5d8d599478cfc4`.

References:

- `docs/handoff/phase5_to_live_canary_roadmap.md` — fixes the stage order (Phase 6.1 → 6.2 → 7.1 → 7.2 → 8.1)
  and the Phase 6.1 hard barrier; Phase 6.2 calibrates **strictly from Phase 6.1 shadow logs**.
- `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md` — the authoritative boundary model
  **B1 ingestion → B2 normalization → B3 Phase-5 gate validation → B4 passive shadow scoring** and Slices 0A–0E.
- `docs/handoff/phase6_1_b3_phase5_wiring_charter.md` — scopes the deferred Master-B3 wiring and records the
  `BLOCKED_NEEDS_B3_MAPPING_EXTRACTION` cells.
- `docs/handoff/phase6_1_depth_representation_reconciliation_closeout.md` — ratified Option C (keep the two
  depth representations disjoint).

**This charter authorizes no executable work.**

**No capacity validation and no capacity pass is claimed by this charter** (see §6 / §7).

---

## 2. Critical Distinction — Depth B3 is NOT Master B3

- **Depth B3 is complete and ratified as a narrow evidence sub-track only.** `phase6_1/b3_depth_evidence_mapping.py`
  is a pure identity/provenance pass-through (`depth_evidence_reference_from_material`) that returns a B2
  material's `depth_source_reference` exactly as-is or `None`. It runs no Phase 5 gate and decides nothing.
- **Depth B3 is NOT Master B3.** It must not be read as satisfying the boundary-model B3.
- **Master B3 — Phase-5 evidence/gate validation wiring — remains unbuilt and blocked.** Master B3 (normalized
  evidence → `net_edge_profitability_preflight` / `CapacityConstraintGate.preflight` → a typed **passed
  non-halt** result **or** a halt carrier, reusing the existing Phase 5 chain) does not exist, and its standard
  B2→Phase-5 mapping is gated on `BLOCKED_NEEDS_B3_MAPPING_EXTRACTION`.

Conflating the two is the primary sequencing hazard this charter exists to prevent.

---

## 3. Remaining Critical Path (ordered — each step is a *future, separately authorized* docs step, then a
separately authorized TDD slice)

No step may be skipped or reordered. Each step below is named only; **none is authorized or designed here.**

1. **B3 mapping-extraction ratification charter (docs-only, FIRST).** A future docs-only charter that ratifies
   the `BLOCKED_NEEDS_B3_MAPPING_EXTRACTION` cells:
   - `pair` → `base_asset` / `quote_asset` split rule;
   - `venue` → venue scope / `venue_buy` / `venue_sell` semantics;
   - cost-component vocabulary (the `normalized_field_name` → cost-component identity mapping).
   This charter **must not** ratify those cells itself (see §7).
2. **Master B3 Phase-5 gate/mapping wiring charter — only after step 1.** Scopes the runtime that maps B2
   evidence into the existing Phase 5 gate and returns the typed passed-non-halt handoff or halt carrier.
3. **B4 passive shadow scoring charter (`ShadowScore` / diagnostic EV) — only after step 2.** Scopes the
   passive scoring that consumes the typed B3 passed-non-halt handoff and produces a passive `ShadowScore` /
   diagnostic-EV observation (diagnostic-only, per the scoring planning §6).
4. **Durable replayable shadow-log persistence charter — only after step 3.** Scopes the durable, replayable
   shadow-log writer/sink (`ShadowObservation` today has no persistence by design).
5. **Phase 6.2 Calibration — only after durable logs exist.** Calibration may be *considered* only once Phase
   6.1 produces durable replayable shadow logs and the roadmap §5 quantitative-gate categories become
   measurable. **Not authorized here.**

---

## 4. Why This Order

- Phase 6.2 calibrates **from Phase 6.1 shadow logs**; those logs cannot exist until B4 scoring runs and a
  durable writer persists them.
- B4 consumes the **typed B3 passed-non-halt handoff**; that handoff cannot exist until Master B3 wiring runs.
- Master B3 wiring cannot be safely chartered until the `BLOCKED_NEEDS_B3_MAPPING_EXTRACTION` derivation rules
  are ratified (B3 must not invent a pair-split / venue-scope / cost-vocabulary mapping).
- Therefore the mapping-extraction ratification is the single highest-leverage *first* docs step.

---

## 5. Explicit Deferrals

- **Live-public-read adapter** remains deferred (charter exists; runtime not authorized).
- **Shadow Intent Envelope** runtime/schema remains deferred.
- **Capacity activation** remains deferred.
- **Output-carrier design** remains deferred unless a future step separately proves it required.
- **Phase 6.2 Calibration** remains **not authorized**.
- **Phase 7.x / 8.x** remain out of scope.

---

## 6. Current State Snapshot (ratified, for orientation only — claims nothing new)

- **Complete:** Slices 0A–0E scaffolding (`PassiveShadowInput`, `ShadowObservation`, provenance locks,
  forbidden-token/IO/actionability locks, diagnostic-EV non-actionability); the depth B1/B2/B3 replay evidence
  sub-track; depth-representation reconciliation (Option C, disjoint).
- **Blocked / unbuilt:** Master B3 Phase-5 gate/mapping wiring; B4 passive shadow scoring; durable shadow-log
  persistence.
- **Deferred:** live-public-read adapter; Shadow Intent Envelope; capacity activation.
- **Capacity invariant:** `CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred.

---

## 7. No-Claims

- This charter **does not** ratify the mapping-extraction cells themselves.
- This charter **does not** design Master B3 runtime.
- This charter **does not** design `ShadowScore`.
- This charter **does not** design durable log schema/persistence.
- This charter **authorizes nothing executable.**

---

## 8. Next Safe Step

- A **separate review** to decide whether to authorize the **B3 mapping-extraction ratification charter**
  (docs-only, step 1 above).
- **No implementation is authorized by this charter.** Master B3 wiring, B4 scoring, durable log persistence,
  the live adapter, Shadow Intent Envelope, capacity activation, Phase 6.2 calibration, and 7.x/8.x remain
  separately gated.
