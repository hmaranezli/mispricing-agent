# Phase 6.1 B3 Depth-Evidence Mapping Runtime — Closeout / Ratification Charter

> **This is a docs-only closeout/ratification charter — a lock document, not a design expansion.** It
> ratifies the first B3 runtime slice as a minimal identity/provenance pass-through boundary and explicitly
> authorizes nothing downstream. It authorizes NO runtime, NO tests, NO lock-test edits, NO
> B1/B2/B3/Phase 5/Shadow Intent runtime change, NO output-carrier design, NO pytest, NO graphify update, NO
> network/API/env/secret access. It is subordinate to `CLAUDE.md` and the prior Phase 6.1 charters; where any
> conflict arises, those govern.

**Base:** `e36c3c22eec4a85aca103dfa55892524e62fc747`

---

## 1. Base / Dependency Chain

**Base commit:** `e36c3c22eec4a85aca103dfa55892524e62fc747`.

Parent chain:

| SHA | Purpose |
|-----|---------|
| `cfc62c6` | B3 TDD slice charter (governor for this slice). |
| `863a4c8` | B3 negative-lock characterization (teeth-proven boundary suite). |
| `3af7c52` | B3 depth-evidence mapping boundary charter (negative-boundary). |
| `192de8d` | Replay-chain closeout ratification (the ratified replay-only depth chain). |

**This closeout authorizes no runtime, no test, no output-carrier, and no downstream work.**

**No capacity validation and no capacity pass is claimed by this charter** (see §12).

---

## 2. Ratified B3 Runtime Shape

- Exactly **one** B3 runtime module: `phase6_1/b3_depth_evidence_mapping.py`.
- Exactly **one** public function: `depth_evidence_reference_from_material`.
- **No** classes.
- **No** dataclasses.
- **No** imports.
- **No** output carrier.
- **No** state.
- **No** side effects.
- **No** IO.

(Verified by AST at this base: public funcs `['depth_evidence_reference_from_material']`, classes `[]`,
imports `[]`.)

---

## 3. Ratified Behavior

- The function accepts a B2 `NormalizedEvidenceMaterial`.
- It returns `material.depth_source_reference` **exactly as-is**.
- If `depth_source_reference` is a `PublicDepthSourceRecord`, **exact identity is preserved**.
- If `depth_source_reference` is `None`, `None` is returned.
- **No** fabrication, **no** default, **no** `UNKNOWN`, **no** synthetic/backfill.
- **No** object creation.

---

## 4. Identity Stability Invariant

- `result is record` and `id(result) == id(record)` are the **governing proofs**.
- **Equality-only proof is insufficient.**
- **No** copy, shallow copy, deepcopy, serialization, tuple/dict conversion, reconstruction, wrapping,
  caching, memoization, normalization, or re-carriage is allowed.
- **No performance optimization may weaken identity stability.**

---

## 5. Module Isolation Invariant

- B3 may **not** import the B1 reader, the B1 depth source contract, B2 runtime, Phase 5, Shadow Intent, IO
  libraries, network libraries, env/secrets libraries, or any downstream runtime.
- B3 **cannot** accept or introduce price/order/trade/order-book/capacity/actionability concepts.
- B3 remains a **pure identity/provenance pass-through boundary only**.

---

## 6. Statelessness Invariant

- **No** module state.
- **No** counters.
- **No** caches.
- **No** previous-record memory.
- **No** accumulation.
- **No** aggregation.
- **No** mutation.
- Each call is **atomic and independent**.

---

## 7. Depth Subfield Firewall

B3 does **not** inspect or name:

- `observed_size`
- `size_unit`
- `depth_source_field`
- `depth_source_artifact`
- `depth_source_contract`
- `depth_snapshot_identity`
- `depth_observed_at_epoch_ms`
- `depth_retrieval_epoch_ms`

Depth remains **sealed evidence**.

---

## 8. Numeric / Actionability Firewall

- **No** `Decimal`/`int`/`float`/`complex` parsing.
- **No** arithmetic, ordering, comparison, ranking, scoring, thresholding.
- **No** capacity PASS.
- **No** `capacity_pass_reference`.
- **No** sizing, allocation, routing, execution, order, trade, candidate, signal, score, verdict.
- **No** liquidity sufficiency/insufficiency conclusion.

---

## 9. Output-Carrier Prohibition

- **No** B3 output carrier.
- **No** bridge object.
- **No** adapter object.
- **No** Phase 5 carrier.
- **No** `PassiveShadowInput`.
- **No** `ShadowObservation`.
- **No** `NetEdgeCalculationResult`.
- **No** Shadow Intent Envelope.
- The output shape remains **deferred** to a separate future charter / review.

---

## 10. Verified Tests and Proof Summary (`e36c3c2`)

- **RED cycle A:** missing module (`ModuleNotFoundError: No module named 'phase6_1.b3_depth_evidence_mapping'`).
- **GREEN cycle A:** 10 B3 mapping tests pass after the minimal function.
- **RED cycle B:** exactly 3 absence tests fail once the module exists (the 14 negative-lock tests pass
  against the real module).
- **GREEN cycle B:** the 3 absence tests converted to a single-basename allowlist; boundary file 17 passed.
- **Targeted suite:** 519 passed in 105.69s.
- **Package-wide lock files untouched** (`forbidden_token_locks`, `diagnostic_ev`).
- **Reader IO exception not broadened** (remains basename-scoped to `b1_replay_depth_artifact_reader.py`).

---

## 11. Still-Blocked Work

- **No** output carrier.
- **No** Phase 5 integration.
- **No** Shadow Intent Envelope.
- **No** live reads.
- **No** capacity activation.
- **No** actionability.
- **No** downstream mapping beyond identity pass-through.
- **No** paper/live/production readiness.

---

## 12. Capacity Invariant

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 13. Next Safe Step

- The next step is a **separate review** to decide whether the next boundary is:
  - **(a)** a docs-only downstream output-shape charter, or
  - **(b)** a docs-only Phase 5 integration boundary charter.
- **No implementation is authorized by this closeout.** Output-carrier design, Phase 5 integration, Shadow
  Intent Envelope, live reads, capacity activation, Phase 6.2 calibration, and 7.x/8.x remain separately
  gated.
- **STOP** after commit and verification.
