# Phase 6.1 Depth-Representation Reconciliation Charter

> **This is a docs-only reconciliation planning charter.** It documents and governs the newly discovered
> representation gap between Phase 5's flat depth strings and the Phase 6.1 sealed `PublicDepthSourceRecord`
> chain. It authorizes NO runtime, NO tests, NO lock-test edits, NO B1/B2/B3/Phase 5/Shadow Intent runtime
> change, NO output-carrier design, NO Phase 5 integration design, NO pytest, NO graphify update, NO
> network/API/env/secret access.
>
> **This is NOT an integration charter. This is NOT an output-shape charter. This is NOT a canonicalization
> implementation.** It is only a planning charter to decide how to *reason about* the two existing depth
> representations. It is subordinate to `CLAUDE.md` and the prior Phase 6.1 charters; where any conflict
> arises, those govern.

**Base:** `eb33dd0d8216d56e3e1287e709dfaf0e079745d1`

---

## 1. Base / Dependency Chain

**Base commit:** `eb33dd0d8216d56e3e1287e709dfaf0e079745d1`.

References:

- `docs/handoff/phase6_1_phase5_interface_gap_analysis_charter.md` — chartered the read-only gap analysis.
- `docs/handoff/phase6_1_next_boundary_decision_review.md` — paused to choose the next boundary.
- `docs/handoff/phase6_1_b3_depth_evidence_mapping_runtime_closeout_ratification.md` — ratified the minimal B3
  identity pass-through.
- `docs/handoff/phase6_1_depth_evidence_replay_chain_closeout_ratification.md` — ratified the replay-only depth
  evidence chain.

**The read-only interface gap analysis found no current Phase 5 consumer for B3's depth identity pass-through:**
no passive/shadow sink imports or names `PublicDepthSourceRecord` or `depth_source_reference`; `PassiveShadowInput`
holds only a `NetEdgeCalculationResult` by identity; `NetEdgeCalculationResult` carries no depth.

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Problem Statement

- Phase 5 has a **flat string depth vocabulary** embedded in `GrossEdgeObservation`.
- Phase 6.1 has a **sealed `PublicDepthSourceRecord` identity/provenance chain** (B1 → B2 → B3).
- `NetEdgeCalculationResult` and the passive/shadow sinks **do not currently carry depth**.
- **Output-carrier necessity is not proven.**
- **Phase 5 integration readiness is not proven.**

---

## 3. Representation Inventory

**Phase 5 representation** — flat scalar string fields on `GrossEdgeObservation`:

- `observed_size`
- `size_unit`
- `depth_source_contract`
- `depth_source_artifact`
- `depth_source_field`

(carried inline as strings on the observation carrier; not forwarded into `NetEdgeCalculationResult`.)

**Phase 6.1 representation** — `PublicDepthSourceRecord`, carried by identity through B2/B3:

- `observed_size`
- `size_unit`
- `depth_source_field`
- `depth_source_artifact`
- `depth_source_contract`
- `depth_snapshot_identity`
- `depth_observed_at_epoch_ms`
- `depth_retrieval_epoch_ms`

**These two representations are currently disjoint.** They share some field *names* but are different objects in
different layers, with no wiring between them. Shared names are **not** an equivalence claim (see §4).

---

## 4. Non-Canonicalization Rule

This charter does **not** choose a canonical representation. Specifically:

- **No** bridging.
- **No** mapping.
- **No** copying.
- **No** wrapping.
- **No** conversion.
- **No** field-equivalence claims (shared field names do not imply shared meaning).
- **No** "these are the same evidence" claim.
- **No** source-of-truth claim between the Phase 5 strings and `PublicDepthSourceRecord`.

The two representations remain disjoint until a future, separately authorized charter proves otherwise.

---

## 5. Options to Evaluate Later (none selected here)

- **A)** Keep disjoint.
- **B)** Bridge by identity at a future sink.
- **C)** Leave deferred.
- **D)** Replace/align the Phase 5 flat strings only if a future charter proves necessity.

**None of A–D is selected by this charter.** They are recorded only as the option space for a future review.

---

## 6. Risk Analysis

- **Double normalization** — re-shaping depth already represented in one layer into another.
- **Schema drift** — the two representations diverging silently over time.
- **Provenance loss** — flattening or copying that severs the sealed identity/provenance anchor.
- **Dead output-carrier** — inventing a carrier with no consumer.
- **Accidental capacity/actionability linkage** — depth being read as a capacity/sizing decision.
- **Lookahead / time-substitution** — merging `depth_observed_at_epoch_ms` and `depth_retrieval_epoch_ms`
  (or Phase 5 times) incorrectly, defeating the time-isolation lock.
- **Numeric coercion** — treating `observed_size` as a quantity/number rather than exact string evidence.

---

## 7. Hard Boundaries

- **No** output carrier.
- **No** Phase 5 integration.
- **No** `PassiveShadowInput` / `ShadowObservation` / `NetEdgeCalculationResult` changes.
- **No** `GrossEdgeObservation` changes.
- **No** source-result adapter changes.
- **No** B3 runtime changes.
- **No** live reads.
- **No** capacity activation.
- **No** actionability/sizing/routing/scoring/trading.

---

## 8. Future Proof Targets (planning only — NOT performed now)

If a future read-only reconciliation analysis slice is authorized, it must determine:

1. Whether the two representations can be **related without copying**.
2. Whether **identity** can be preserved.
3. Whether **timestamps remain isolated** (no observed/retrieval substitution).
4. Whether `observed_size` **remains exact string evidence** (no numeric coercion).
5. Whether the Phase 5 flat strings **already satisfy a separate need** (so no bridge is required).
6. Whether **a future sink actually requires depth** at all.
7. Whether **any canonical choice is necessary at all**.

---

## 9. No-Claims State

- **Output-carrier necessity:** not proven.
- **Phase 5 integration readiness:** not proven.
- **B3 pass-through consumer:** absent today.
- **Depth-accepting passive/shadow sink:** absent today.
- **Capacity readiness:** deferred (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS
  token; `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **`edge_direction` / actionability:** deferred.

---

## 10. Next Safe Step

- A **separate review** to decide whether to authorize a **read-only representation reconciliation analysis
  slice** (a report only, changing nothing).
- **No implementation is authorized by this charter.** Output-carrier design, Phase 5 integration, Shadow
  Intent Envelope, live reads, capacity activation, Phase 6.2 calibration, and 7.x/8.x remain separately
  gated.
