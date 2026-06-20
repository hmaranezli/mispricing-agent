# Phase 6.1 B3 Depth-Evidence Mapping/Wiring Boundary Charter

> **This is a docs-only planning/boundary charter — primarily a NEGATIVE-boundary document.** It defines
> what a future B3 depth-evidence mapping/wiring step **must not do** before any runtime TDD can be
> considered. It authorizes NO runtime, NO tests, NO lock-test edits, NO B1/B2/B3/Phase 5/Shadow Intent
> runtime change, NO pytest, NO graphify update, NO network/API/env/secret access. **It does not design or
> authorize any runtime output carrier.** It is subordinate to `CLAUDE.md` and the prior Phase 6.1 charters;
> where any conflict arises, those govern.

**Base:** `192de8d0bcfc90ecd66ba3ae412cd162560e2caa`

---

## 1. Base / Dependency Chain

**Base commit:** `192de8d0bcfc90ecd66ba3ae412cd162560e2caa`.

The completed, ratified Phase 6.1 replay-only depth evidence chain:

```
replay depth artifact (local, public, immutable)
  -> phase6_1/b1_replay_depth_artifact_reader.py   (read_replay_depth_artifact)
  -> PublicDepthSourceRecord                        (via make_public_depth_source_record)
  -> phase6_1/b2_replay_normalization.py            (normalize_replay_snapshot_to_evidence_material)
  -> NormalizedEvidenceMaterial.depth_source_reference  (optional, by exact identity)
```

- See `docs/handoff/phase6_1_depth_evidence_replay_chain_closeout_ratification.md` — the closeout that
  ratified the chain above and recorded its invariant proofs at this base.

**This B3 charter authorizes no runtime, no tests, no B3 implementation, and no Phase 5 integration.** It is
a boundary document only.

---

## 2. B3 Consumption Boundary

- A future B3 may consume the B2 material's `depth_source_reference` **only** as an exact identity /
  provenance reference.
- B3 must treat the object as **sealed evidence**.
- B3 may **not** parse, inspect, copy, reconstruct, serialize, normalize, coerce, or derive from any depth
  subfield:
  - `observed_size`
  - `size_unit`
  - `depth_source_field`
  - `depth_source_artifact`
  - `depth_source_contract`
  - `depth_snapshot_identity`
  - `depth_observed_at_epoch_ms`
  - `depth_retrieval_epoch_ms`
- Any future B3 TDD must prove **exact identity preservation** with `is` **and** `id()` if it carries the
  reference forward at all.

---

## 3. Runtime Output Prohibition

- This charter **must not** define a B3 runtime output shape.
- **No** `PassiveShadowInput` construction.
- **No** `ShadowObservation` construction.
- **No** `NetEdgeCalculationResult` construction.
- **No** Phase 5 carrier construction.
- **No** Shadow Intent Envelope construction.
- **No** bridge object, adapter object, or output carrier may be invented by this charter.
- The runtime output shape is **deferred** to a separate future charter / review if it is ever needed.

---

## 4. No Capacity / Actionability Linkage

- Depth evidence must remain **provenance-tagged evidence only**.
- **No** capacity PASS claim.
- **No** `CapacityConstraintGate` activation.
- **No** `capacity_pass_reference` population.
- **No** sizing, allocation, routing, threshold, score, verdict, execution, order, trade, candidate, signal,
  exposure, balance, wallet, or paper/live semantics.
- **No** numeric depth decision.
- **No** statement that `observed_size` is sufficient/insufficient liquidity.
- **No** comparison of depth against any requested size or capacity.

---

## 5. No Numeric Parsing / Coercion

- B3 must **not** parse `observed_size` or any depth subfield into `Decimal`, `int`, `float`, `complex`,
  `bool`, quantity, lot, notional, size, or capacity units.
- B3 must **not** compare, rank, score, bucket, clamp, round, scale, sum, subtract, multiply, divide, or
  otherwise compute from depth fields.
- B3 must **not** use depth to infer tradability, capacity, feasibility, or actionability.

---

## 6. Provenance and Identity Rules

- `PublicDepthSourceRecord` remains the **only** ratified B1 depth evidence carrier.
- B2 `depth_source_reference` remains the **only** ratified B2 depth evidence slot.
- B3 may **not** fabricate, backfill, default, or substitute depth provenance.
- Missing depth remains **missing / `None`**.
- **No** `UNKNOWN` / default / synthetic depth carrier.
- **No** mutation of the B1 depth record (it is frozen/slotted/init-blocked and stays so).

---

## 7. IO and Source Boundary

- **No** new IO.
- **No** reader changes.
- **No** lock-test changes.
- **No** network/live/API access.
- **No** env/secrets/private/account/wallet/balance/trading endpoint access.
- The only existing IO exception remains **basename-scoped** to `b1_replay_depth_artifact_reader.py`.
- B3 must **not** read artifacts, paths, files, JSON, CSV, or directories.

---

## 8. Relationship to B1 / B2 / Phase 5

- The B1 reader and `PublicDepthSourceRecord` are **complete** for replay-only evidence.
- B2 material can carry `depth_source_reference` by identity.
- B3 implementation remains **unimplemented and blocked**.
- Phase 5 integration remains **unimplemented and blocked**.
- This charter does **not** authorize B3 runtime or Phase 5 runtime.

---

## 9. Future TDD Proof Targets (planning notes only — NOT written now)

If a future B3 slice is ever authorized, its TDD must prove:

1. **Exact identity preservation** if B3 carries the reference (`is` + `id()`).
2. **No depth subfield access** — none of the 8 subfields named/read.
3. **No numeric parsing/coercion** of any depth field.
4. **No output carrier construction**.
5. **No `PassiveShadowInput` / `ShadowObservation` / `NetEdgeCalculationResult`** construction.
6. **No capacity PASS or `capacity_pass_reference`** population.
7. **No IO / network / env / secrets**.
8. **Missing depth remains `None`** (no fabrication).
9. **No actionability / sizing / routing / scoring / verdict semantics**.

---

## 10. Still-Blocked Work

- **No B3 mapping/wiring runtime** is authorized.
- **No B3 tests** are authorized.
- **No Phase 5 runtime** is authorized.
- **No Shadow Intent Envelope runtime/schema** is authorized.
- **No live/network reads** are authorized.
- **No capacity activation** is authorized.
- **No carrier/output construction** is authorized.

---

## 11. Capacity Invariant

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never
be read as "capacity validated."

---

## 12. Next Safe Step

- The next step is a **separate review** to decide whether to authorize a future **B3 TDD characterization
  slice**.
- That future slice, **if authorized**, must start with **negative-lock tests only**: no subfield access, no
  output construction, no capacity/actionability, no IO.
- **No implementation is authorized by this charter.** B3 mapping/wiring, Phase 5 integration, Shadow Intent
  Envelope, live reads, Phase 6.2 calibration, and 7.x/8.x remain separately gated.
