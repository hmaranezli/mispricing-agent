# Phase 6.1 B3 Depth-Evidence Mapping/Wiring TDD Slice Charter

> **This is a docs-only TDD slice charter — a governor, not a runtime design.** It defines the *shape* a
> future B3 depth-evidence mapping/wiring TDD slice must take and the firewalls it must respect. It
> authorizes NO runtime, NO tests, NO B3 runtime module, NO B1/B2/Phase 5/Shadow Intent runtime change, NO
> output carrier design, NO lock-test edits, NO pytest, NO graphify update, NO network/API/env/secret access.
> It is subordinate to `CLAUDE.md`, the B3 boundary charter, and the closeout ratification; where any
> conflict arises, those govern.

**Base:** `863a4c8efa73ed776256384ad938916355256de9`

---

## 1. Base / Dependency Chain

**Base commit:** `863a4c8efa73ed776256384ad938916355256de9`.

References:

- `docs/handoff/phase6_1_b3_depth_evidence_mapping_boundary_charter.md` — the negative-boundary charter that
  defines what B3 must not do.
- `tests/test_phase6_1_b3_depth_evidence_mapping_boundary.py` — the teeth-proven negative-lock characterization
  suite (17 tests) that arms automatically against any future `b3` module.
- `docs/handoff/phase6_1_depth_evidence_replay_chain_closeout_ratification.md` — the ratified replay-only
  depth evidence chain and its invariant proofs.

**B3 runtime remains absent and blocked.** No `b3` module exists in `phase6_1/`. **This charter authorizes no
runtime, no tests, and no output carrier.**

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. TDD Slice Purpose

- A future slice, **if separately authorized later**, may **only** characterize the **minimal B3
  identity/provenance boundary**.
- It must **not** implement actionability, capacity, Phase 5, Shadow Intent, an output carrier, scoring,
  sizing, or routing.
- It must **begin with negative-lock tests and exact identity/provenance tests only** — the smallest possible
  surface, proven red→green only where a true behavioral assertion exists, and characterization-green for the
  inherited negative locks.

---

## 3. Minimal Future B3 Input Boundary

- A future B3 may **only** accept a B2 `NormalizedEvidenceMaterial` that already carries
  `depth_source_reference`.
- B3 may **only** observe whether `depth_source_reference` is `None` or an exact `PublicDepthSourceRecord`
  reference (exact-type check, e.g. `type(x) is PublicDepthSourceRecord`, never `isinstance`).
- B3 must **not** read or parse depth subfields.
- B3 must **not** call the reader (`read_replay_depth_artifact`).
- B3 must **not** load artifacts.
- B3 must **not** fabricate depth.

---

## 4. Identity / Provenance Pass-Through Only

- If any future B3 runtime is later authorized, it may **only preserve identity/provenance**, never transform
  depth.
- Future tests must prove identity with **`is` and `id()`**.
- **Equality-only proof is insufficient.**
- **No** copy, deepcopy, dict-convert, tuple-convert, serialization, normalization, reconstruction, backfill,
  or defaulting of the depth record.

---

## 5. Explicit Output Carrier Prohibition

- This charter **must not** define an output carrier.
- **No** bridge object.
- **No** adapter object.
- **No** B3 carrier.
- **No** Phase 5 carrier.
- **No** `PassiveShadowInput`.
- **No** `ShadowObservation`.
- **No** `NetEdgeCalculationResult`.
- **No** Shadow Intent Envelope.
- The output shape remains **deferred** to a separate future charter / review.

---

## 6. Depth Subfield Firewall

- Future B3 runtime/tests must prove B3 does **not** inspect:
  - `observed_size`
  - `size_unit`
  - `depth_source_field`
  - `depth_source_artifact`
  - `depth_source_contract`
  - `depth_snapshot_identity`
  - `depth_observed_at_epoch_ms`
  - `depth_retrieval_epoch_ms`
- The depth object is **sealed evidence** — carried by identity, never opened.

---

## 7. Numeric / Actionability Firewall

- **No** `Decimal`/`int`/`float`/`complex` parsing.
- **No** arithmetic.
- **No** comparison/ordering.
- **No** threshold/ranking/scoring.
- **No** capacity PASS.
- **No** `capacity_pass_reference` population.
- **No** sizing/allocation/routing/execution/order/trade/candidate/signal/verdict.
- **No** liquidity sufficiency/insufficiency conclusion.

---

## 8. IO / Source Firewall

- **No** `open`/`read`/`json`/`csv`/`pathlib`/`os`/`sys` in B3.
- **No** network/API/live reads.
- **No** env/secrets.
- **No** file/path/artifact access.
- The existing IO exception remains limited to `b1_replay_depth_artifact_reader.py` **only**; B3 receives no
  IO carve-out.

---

## 9. Negative-Lock Inheritance

- The future slice must keep the `863a4c8` negative-lock tests
  (`tests/test_phase6_1_b3_depth_evidence_mapping_boundary.py`) **passing**.
- If a `b3` module is created later, those teeth-proven detectors must apply to it **automatically** (the
  scans are keyed on a `b3` basename).
- **No broadening or weakening** of the existing locks (and no broadening of the reader IO-lock exception).

---

## 10. Still-Blocked Work

- **No B3 runtime.**
- **No B3 tests by this charter.**
- **No output carrier.**
- **No Phase 5 integration.**
- **No Shadow Intent.**
- **No live reads.**
- **No capacity activation.**
- **No actionability implementation.**

---

## 11. Capacity Invariant

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 12. Next Safe Step

- The next step is a **separate review** to decide whether to authorize the actual **B3 TDD implementation
  slice**.
- If authorized later, it must start with the **smallest possible identity/provenance negative-lock tests**.
- **This charter itself authorizes nothing executable.** B3 runtime, output carrier, Phase 5 integration,
  Shadow Intent Envelope, live reads, capacity activation, Phase 6.2 calibration, and 7.x/8.x remain
  separately gated.
