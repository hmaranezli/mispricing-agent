# Phase 6.1 Depth-Representation Reconciliation Closeout Charter — Option C (Leave Deferred)

> **This is a docs-only closeout/ratification charter.** It ratifies the read-only reconciliation finding and
> selects **Option C: leave deferred / keep disjoint** as the standing posture. It authorizes NO runtime, NO
> tests, NO lock-test edits, NO B1/B2/B3/Phase 5/Shadow Intent runtime change, NO output-carrier design, NO
> Phase 5 integration design, NO canonicalization implementation, NO bridge design, NO pytest, NO graphify
> update, NO network/API/env/secret access.
>
> **This is NOT an integration charter. This is NOT an output-shape charter. This is NOT a canonicalization
> charter.** It is a closeout/ratification document that selects Option C. It is subordinate to `CLAUDE.md`
> and the prior Phase 6.1 charters; where any conflict arises, those govern.

**Base:** `031c8f926380a6e5f4be64b7318a3ccf181af1ce`

---

## 1. Base / Dependency Chain

**Base commit:** `031c8f926380a6e5f4be64b7318a3ccf181af1ce`.

References:

- `docs/handoff/phase6_1_depth_representation_reconciliation_charter.md` — governed how to reason about the two
  representations (non-canonicalization rule, option space A–D).
- `docs/handoff/phase6_1_phase5_interface_gap_analysis_charter.md` — chartered the read-only gap analysis.
- `docs/handoff/phase6_1_b3_depth_evidence_mapping_runtime_closeout_ratification.md` — ratified the minimal B3
  identity pass-through.
- `docs/handoff/phase6_1_depth_evidence_replay_chain_closeout_ratification.md` — ratified the replay-only depth
  evidence chain.

**This closeout authorizes no executable work.**

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Ratified Decision

- **Ratify Option C: leave deferred.**
- Operationally, this means **keep the Phase 5 flat depth strings and the Phase 6.1 `PublicDepthSourceRecord`
  chain disjoint** for now.
- **Explicitly not Option B** (bridge-by-identity).
- **Explicitly not Option D** (replace/align the Phase 5 flat strings).
- **No canonical representation is selected.**

---

## 3. Findings Being Ratified

- The Phase 5 and Phase 6.1 depth fields are **partially aligned by name, not semantically equivalent**.
- **Shared fields** (by name):
  - `observed_size`
  - `size_unit`
  - `depth_source_contract`
  - `depth_source_artifact`
  - `depth_source_field`
- **Phase 6.1 adds** (absent from the Phase 5 depth strings):
  - `depth_snapshot_identity`
  - `depth_observed_at_epoch_ms`
  - `depth_retrieval_epoch_ms`
- Phase 5 has **no depth-specific timestamp pair** and **no `depth_snapshot_identity`**. (Phase 5 additionally
  constrains `observed_size` to a canonical non-negative decimal string, whereas Phase 6.1 carries
  `observed_size` as unconstrained exact string evidence — a semantic divergence, not an equivalence.)
- **No current Phase 5 passive/shadow sink consumes the B3 depth identity pass-through.**
- `NetEdgeCalculationResult` / `PassiveShadowInput` / `ShadowObservation` remain **depth-free**.

---

## 4. Anti-Fabrication Lock

- **No** synthetic `depth_snapshot_identity`.
- **No** synthetic `depth_observed_at_epoch_ms`.
- **No** synthetic `depth_retrieval_epoch_ms`.
- **No** `UNKNOWN`, `None`-fill, null-fill, default-fill, backfill, placeholder, derived, copied, or inferred
  field completion.
- **No** `PublicDepthSourceRecord` construction from Phase 5 flat strings.
- **No** fake provenance.

---

## 5. Anti-Coercion Lock

- Phase 6.1 `observed_size` remains **exact string evidence**.
- It must **not** be parsed/cast/coerced into Phase 5 decimal-string semantics.
- Phase 5 `observed_size` decimal constraints do **not** prove equivalence with Phase 6.1 `observed_size`.
- **No** `Decimal`/`int`/`float`/`complex` parsing.
- **No** numeric comparison, ordering, ranking, thresholding, rounding, scaling, or normalization.

---

## 6. Time-Isolation Lock

- The Phase 5 gross-edge `observed_at_epoch_ms` must **not** be substituted for `depth_observed_at_epoch_ms`.
- `retrieval_epoch_ms` must **not** be substituted for `observed_at_epoch_ms`.
- **No** timestamp merge.
- **No** lookahead-bias-producing time substitution.
- **No** temporal equivalence claim.

---

## 7. Non-Equivalence / No-Source-of-Truth Lock

- **No** claim that the Phase 5 flat strings and the Phase 6.1 `PublicDepthSourceRecord` are the same evidence.
- **No** claim that either representation is canonical.
- **No** source-of-truth claim.
- **No** field-equivalence claim beyond the partial by-name overlap.
- **No** bridge/map/copy/convert/wrap/serialize/reconstruct.

---

## 8. Consumer Requirement

- The disjoint posture may be reconsidered **only if a future Phase 5 sink explicitly requires depth
  evidence**.
- That future sink requirement must be documented in a **separate charter**.
- Convenience, cleanup, symmetry, refactoring, or "nice architecture" is **not enough**.
- **No consumer means no output carrier and no reconciliation implementation.**

---

## 9. Still-Blocked Work

- **No** output carrier.
- **No** bridge.
- **No** canonicalization.
- **No** Phase 5 integration.
- **No** `GrossEdgeObservation` or adapter change.
- **No** `NetEdgeCalculationResult` depth change.
- **No** `PassiveShadowInput` / `ShadowObservation` depth change.
- **No** B3 runtime expansion.
- **No** Shadow Intent Envelope.
- **No** live reads.
- **No** capacity activation.
- **No** actionability/sizing/routing/scoring/trading/candidate/verdict.

---

## 10. Capacity Invariant

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 11. Next Safe Step

- **Separate review only.**
- If future work is ever considered, **first establish an actual depth-consuming sink requirement** (in a
  separate charter).
- Until then, the **standing posture is leave deferred / keep disjoint**.
- **No implementation is authorized by this closeout.** Output-carrier design, bridge, canonicalization,
  Phase 5 integration, Shadow Intent Envelope, live reads, capacity activation, Phase 6.2 calibration, and
  7.x/8.x remain separately gated.
